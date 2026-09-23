#!/usr/bin/env python3
"""Stable student API backed by PX4 Offboard control through MAVROS."""

import copy
import json
import math
import threading

import actionlib
import rospy
from geometry_msgs.msg import Twist, TwistStamped
from mavros_msgs.msg import ExtendedState, State
from mavros_msgs.srv import CommandBool, SetMode
from nav_msgs.msg import Odometry
from std_msgs.msg import Bool, String
from tf.transformations import euler_from_quaternion

from px4_competition.msg import (LandAction, LandFeedback, LandResult,
                                 TakeoffAction, TakeoffFeedback, TakeoffResult)


def clamp(value, limit):
    return max(-limit, min(limit, value))


class StudentBridge:
    def __init__(self):
        self.arena = rospy.get_param('/arena')
        config = rospy.get_param('/student_interface')
        self.command_timeout = float(config['command_timeout'])
        self.max_xy = float(config['max_xy_speed'])
        self.max_z = float(config['max_z_speed'])
        self.max_yaw_rate = float(config['max_yaw_rate'])
        self.takeoff_speed = float(config['takeoff_speed'])
        self.takeoff_tolerance = float(config['takeoff_tolerance'])
        self.takeoff_timeout = float(config['takeoff_timeout'])
        self.land_timeout = float(config['land_timeout'])
        self.lock = threading.RLock()
        self.fc_state = State()
        self.extended_state = ExtendedState()
        self.local_odom = None
        self.last_command = Twist()
        self.last_command_time = rospy.Time(0)
        self.resetting = False
        self.takeoff_target = None
        self.setpoint_pub = rospy.Publisher('/mavros/setpoint_velocity/cmd_vel',
                                            TwistStamped, queue_size=10)
        self.odom_pub = rospy.Publisher('/quadrotor/odom', Odometry, queue_size=20)
        self.state_pub = rospy.Publisher('/quadrotor/state', String,
                                         queue_size=5, latch=True)
        rospy.Subscriber('/mavros/state', State, self.state_callback, queue_size=5)
        rospy.Subscriber('/mavros/extended_state', ExtendedState,
                         self.extended_callback, queue_size=5)
        rospy.Subscriber('/mavros/local_position/odom', Odometry,
                         self.odom_callback, queue_size=20)
        rospy.Subscriber('/quadrotor/cmd_vel', Twist, self.command_callback, queue_size=5)
        rospy.Subscriber('/teacher/final/resetting', Bool,
                         self.reset_callback, queue_size=1)
        self.takeoff_server = actionlib.SimpleActionServer(
            '/quadrotor/takeoff', TakeoffAction, execute_cb=self.takeoff, auto_start=False)
        self.land_server = actionlib.SimpleActionServer(
            '/quadrotor/land', LandAction, execute_cb=self.land, auto_start=False)
        self.takeoff_server.start()
        self.land_server.start()
        rospy.Timer(rospy.Duration(0.05), self.control_tick)
        rospy.Timer(rospy.Duration(0.25), self.publish_state)

    def state_callback(self, message):
        with self.lock:
            self.fc_state = message

    def extended_callback(self, message):
        with self.lock:
            self.extended_state = message

    def odom_callback(self, message):
        with self.lock:
            self.local_odom = message
        result = copy.deepcopy(message)
        start = self.arena['start_pose']
        result.header.frame_id = 'world'
        result.child_frame_id = 'quadrotor/base_link'
        result.pose.pose.position.x += start[0]
        result.pose.pose.position.y += start[1]
        result.pose.pose.position.z += start[2]
        self.odom_pub.publish(result)

    def command_callback(self, message):
        with self.lock:
            self.last_command = message
            self.last_command_time = rospy.Time.now()

    def reset_callback(self, message):
        with self.lock:
            self.resetting = message.data
            self.takeoff_target = None
            self.last_command = Twist()
            self.last_command_time = rospy.Time(0)

    def desired_command(self):
        with self.lock:
            command = copy.deepcopy(self.last_command)
            odometry = self.local_odom
            target = self.takeoff_target
            stale = (rospy.Time.now() - self.last_command_time).to_sec() > self.command_timeout
            if self.resetting or stale:
                command = Twist()
            if target is not None and odometry is not None:
                error = target - odometry.pose.pose.position.z
                command = Twist()
                command.linear.z = clamp(1.2 * error, self.takeoff_speed)
            return command, odometry

    def control_tick(self, _event):
        command, odometry = self.desired_command()
        setpoint = TwistStamped()
        setpoint.header.stamp = rospy.Time.now()
        if odometry is not None:
            q = odometry.pose.pose.orientation
            _, _, yaw = euler_from_quaternion((q.x, q.y, q.z, q.w))
            body_x = clamp(command.linear.x, self.max_xy)
            body_y = clamp(command.linear.y, self.max_xy)
            setpoint.twist.linear.x = math.cos(yaw) * body_x - math.sin(yaw) * body_y
            setpoint.twist.linear.y = math.sin(yaw) * body_x + math.cos(yaw) * body_y
        setpoint.twist.linear.z = clamp(command.linear.z, self.max_z)
        setpoint.twist.angular.z = clamp(command.angular.z, self.max_yaw_rate)
        self.setpoint_pub.publish(setpoint)

    def publish_state(self, _event=None):
        with self.lock:
            data = {
                'connected': bool(self.fc_state.connected),
                'armed': bool(self.fc_state.armed),
                'mode': self.fc_state.mode,
                'landed_state': int(self.extended_state.landed_state),
                'local_position_valid': self.local_odom is not None,
                'resetting': self.resetting,
                'ready': bool(self.fc_state.connected and self.local_odom is not None
                              and not self.resetting),
            }
        self.state_pub.publish(json.dumps(data))

    @staticmethod
    def call_service(name, service_type, *arguments):
        rospy.wait_for_service(name, timeout=5)
        return rospy.ServiceProxy(name, service_type)(*arguments)

    def takeoff(self, goal):
        height = float(goal.height)
        if not 0.3 <= height <= 2.0:
            self.takeoff_server.set_aborted(TakeoffResult(False, 'height must be 0.3..2.0 m'))
            return
        with self.lock:
            if not self.fc_state.connected or self.local_odom is None or self.resetting:
                self.takeoff_server.set_aborted(TakeoffResult(False, 'PX4 interface is not ready'))
                return
            start_height = self.local_odom.pose.pose.position.z
            self.takeoff_target = start_height
        # PX4 requires a setpoint stream before accepting OFFBOARD.
        rospy.sleep(1.0)
        try:
            mode = self.call_service('/mavros/set_mode', SetMode, 0, 'OFFBOARD')
            armed = self.call_service('/mavros/cmd/arming', CommandBool, True)
            if not mode.mode_sent or not armed.success:
                raise RuntimeError('PX4 rejected OFFBOARD or arm command')
        except (rospy.ROSException, rospy.ServiceException, RuntimeError) as error:
            with self.lock:
                self.takeoff_target = None
            self.takeoff_server.set_aborted(TakeoffResult(False, str(error)))
            return
        with self.lock:
            self.takeoff_target = start_height + height
        deadline = rospy.Time.now() + rospy.Duration(self.takeoff_timeout)
        rate = rospy.Rate(10)
        while not rospy.is_shutdown() and rospy.Time.now() < deadline:
            if self.takeoff_server.is_preempt_requested():
                with self.lock:
                    self.takeoff_target = None
                self.takeoff_server.set_preempted(TakeoffResult(False, 'preempted'))
                return
            with self.lock:
                current = self.local_odom.pose.pose.position.z if self.local_odom else start_height
            self.takeoff_server.publish_feedback(TakeoffFeedback(current - start_height))
            if abs(current - start_height - height) <= self.takeoff_tolerance:
                with self.lock:
                    self.takeoff_target = None
                    self.last_command = Twist()
                    self.last_command_time = rospy.Time.now()
                self.takeoff_server.set_succeeded(TakeoffResult(True, 'takeoff complete'))
                return
            rate.sleep()
        with self.lock:
            self.takeoff_target = None
        self.takeoff_server.set_aborted(TakeoffResult(False, 'takeoff timed out'))

    def land(self, _goal):
        try:
            answer = self.call_service('/mavros/set_mode', SetMode, 0, 'AUTO.LAND')
            if not answer.mode_sent:
                raise RuntimeError('PX4 rejected AUTO.LAND')
        except (rospy.ROSException, rospy.ServiceException, RuntimeError) as error:
            self.land_server.set_aborted(LandResult(False, str(error)))
            return
        deadline = rospy.Time.now() + rospy.Duration(self.land_timeout)
        rate = rospy.Rate(5)
        while not rospy.is_shutdown() and rospy.Time.now() < deadline:
            if self.land_server.is_preempt_requested():
                self.land_server.set_preempted(LandResult(False, 'preempted'))
                return
            with self.lock:
                landed = self.extended_state.landed_state
            state_name = 'on_ground' if landed == ExtendedState.LANDED_STATE_ON_GROUND else 'landing'
            self.land_server.publish_feedback(LandFeedback(state_name))
            if landed == ExtendedState.LANDED_STATE_ON_GROUND:
                try:
                    self.call_service('/mavros/cmd/arming', CommandBool, False)
                except (rospy.ROSException, rospy.ServiceException):
                    pass
                self.land_server.set_succeeded(LandResult(True, 'landing complete'))
                return
            rate.sleep()
        self.land_server.set_aborted(LandResult(False, 'landing timed out'))


if __name__ == '__main__':
    rospy.init_node('student_bridge')
    StudentBridge()
    rospy.spin()
