#!/usr/bin/env python3
"""Camera + Euler pose + takeoff/right/90-degree CCW/forward/land/report."""
import json
import math
import os
import time

import actionlib
import cv2
import rospy
from cv_bridge import CvBridge
from geometry_msgs.msg import PoseStamped, Twist
from sensor_msgs.msg import Image
from std_msgs.msg import String
from tello_competition.msg import TakeoffAction, TakeoffGoal, LandAction, LandGoal


def quaternion_to_euler(x, y, z, w):
    """ROS quaternion (x,y,z,w) -> roll, pitch, yaw in radians (ZYX convention).

    Roll is about X, pitch about Y, yaw about Z; positive yaw is counterclockwise
    viewed from above. Normalize first to tolerate floating-point roundoff.
    """
    norm = math.sqrt(x*x + y*y + z*z + w*w)
    if not math.isfinite(norm) or norm < 1e-12:
        raise ValueError('Invalid orientation quaternion')
    x, y, z, w = x/norm, y/norm, z/norm, w/norm
    roll = math.atan2(2*(w*x + y*z), 1 - 2*(x*x + y*y))
    pitch = math.asin(max(-1.0, min(1.0, 2*(w*y - z*x))))
    yaw = math.atan2(2*(w*z + x*y), 1 - 2*(y*y + z*z))
    return roll, pitch, yaw


def wrap_angle(angle):
    """Signed shortest angle in [-pi, pi], including the yaw wrap boundary."""
    return math.atan2(math.sin(angle), math.cos(angle))


class Demo:
    def __init__(self):
        self.pose = None
        self.image = None
        self.state = {}
        self.pose_received = 0.0
        self.bridge = CvBridge()
        self.command = rospy.Publisher('/tello/cmd_vel', Twist, queue_size=1)
        self.judge = rospy.Publisher('/tello/judge', String, queue_size=1)
        rospy.Subscriber('/tello/pose', PoseStamped, self.on_pose, queue_size=1)
        rospy.Subscriber('/tello/front_cam/camera/image', Image, self.on_image,
                         queue_size=1, buff_size=2**22)
        rospy.Subscriber('/tello/state', String, self.on_state, queue_size=1)
        self.takeoff = actionlib.SimpleActionClient('/tello/takeoff', TakeoffAction)
        self.land = actionlib.SimpleActionClient('/tello/land', LandAction)

    def on_pose(self, msg):
        p, q = msg.pose.position, msg.pose.orientation
        try:
            roll, pitch, yaw = quaternion_to_euler(q.x, q.y, q.z, q.w)
        except ValueError as error:
            rospy.logwarn_throttle(1.0, str(error))
            return
        self.pose = msg
        self.pose_received = time.monotonic()
        rospy.loginfo_throttle(1.0, 'world pose: x=%.3f y=%.3f z=%.3f m; '
                              'roll=%.1f pitch=%.1f yaw=%.1f deg',
                              p.x, p.y, p.z, math.degrees(roll),
                              math.degrees(pitch), math.degrees(yaw))

    def on_image(self, msg):
        # Convert/display on the main thread, not in the ROS callback thread.
        self.image = msg

    def on_state(self, msg):
        self.state = json.loads(msg.data)

    def tick(self):
        if rospy.is_shutdown():
            raise RuntimeError('ROS has stopped')
        if self.image is not None:
            frame = self.bridge.imgmsg_to_cv2(self.image, desired_encoding='bgr8')
            cv2.imshow('Tello front camera', frame)
        cv2.waitKey(1)
        time.sleep(0.05)

    def wait_until(self, condition, timeout, description):
        deadline = time.monotonic() + timeout
        while not condition():
            if time.monotonic() > deadline:
                raise RuntimeError('Timed out: ' + description)
            self.tick()

    def wait_action(self, client, goal, timeout, description):
        client.send_goal(goal)
        self.wait_until(lambda: client.get_result() is not None, timeout, description)
        if not client.get_result().success:
            raise RuntimeError(description + ' failed: ' + str(client.get_result()))

    def move(self, forward=0.0, left=0.0, seconds=2.0):
        """Body-frame velocity: +x forward, +y left; right means negative y."""
        command = Twist()
        command.linear.x, command.linear.y = forward, left
        start = rospy.Time.now().to_sec()
        deadline = time.monotonic() + 20.0
        try:
            while rospy.Time.now().to_sec() - start < seconds:
                if time.monotonic() > deadline or time.monotonic() - self.pose_received > 2:
                    raise RuntimeError('Simulation paused or absolute pose is stale')
                self.command.publish(command)
                self.tick()
        finally:
            self.command.publish(Twist())

    def yaw(self):
        q = self.pose.pose.orientation
        return quaternion_to_euler(q.x, q.y, q.z, q.w)[2]

    def rotate_ccw(self, degrees=90.0):
        """Turn CCW using absolute-pose feedback; stop within 2 degrees.

        This simple example accepts turns below 180 degrees. Twist.angular.z
        remains rad/s, even though terminal output uses degrees.
        """
        if not 0 < degrees < 180:
            raise ValueError('Use a CCW angle between 0 and 180 degrees')
        target = wrap_angle(self.yaw() + math.radians(degrees))
        deadline, stable = time.monotonic() + 40.0, None
        try:
            while True:
                if time.monotonic() > deadline or time.monotonic()-self.pose_received > 2:
                    raise RuntimeError('Rotation timed out or absolute pose is stale')
                error = wrap_angle(target - self.yaw())
                command = Twist()
                now = rospy.Time.now().to_sec()
                if abs(error) <= math.radians(2):
                    stable = now if stable is None else stable
                    if now-stable >= 0.5:
                        rospy.loginfo('Rotation complete: yaw=%.1f deg, error=%.1f deg',
                                      math.degrees(self.yaw()), math.degrees(error))
                        return
                else:
                    stable = None
                    command.angular.z = max(-0.45, min(0.45, 1.3*error))
                self.command.publish(command)
                self.tick()
        finally:
            self.command.publish(Twist())

    def run(self):
        self.wait_until(lambda: self.state.get('ready') and self.pose is not None
                        and self.image is not None and self.command.get_num_connections() > 0
                        and self.judge.get_num_connections() > 0, 60, 'public interfaces')
        if self.state.get('armed'):
            raise RuntimeError('Start with a fresh scene and a disarmed Tello on the start pad')
        for client in (self.takeoff, self.land):
            if not client.wait_for_server(rospy.Duration(10)):
                raise RuntimeError('Takeoff/land action server missing')
        # ready indicates connectivity; allow PX4 pre-arm checks to settle.
        start = rospy.Time.now().to_sec()
        self.wait_until(lambda: rospy.Time.now().to_sec() - start >= 8, 60, 'PX4 warm-up')
        try:
            rospy.loginfo('Taking off 0.48 m')
            self.wait_action(self.takeoff, TakeoffGoal(height=0.48), 60, 'takeoff')
            rospy.loginfo('Moving right: 0.10 m/s for 2 simulation seconds')
            self.move(left=-0.10)
            self.move(seconds=1.0)  # Brief stop between movements.
            rospy.loginfo('Rotating counterclockwise 90 degrees (viewed from above)')
            self.rotate_ccw(90.0)
            self.move(seconds=1.0)
            rospy.loginfo('Moving forward along NEW heading: 0.10 m/s for 2 simulation seconds')
            self.move(forward=0.10)
        finally:
            self.command.publish(Twist())
            self.takeoff.cancel_all_goals()
            rospy.loginfo('Landing')
            self.wait_action(self.land, LandGoal(), 90, 'landing')
        # Example only: rotating cabinet red, fixed cabinet green. No recognition!
        # This consumes the round's first ball-color submission; restart for competition.
        self.judge.publish(String(data='rg'))
        rospy.loginfo('Sent example judge message: rg (not a vision result)')
        end = time.monotonic() + 1.0
        self.wait_until(lambda: time.monotonic() >= end, 3, 'message delivery')
        rospy.loginfo('Demo finished')


if __name__ == '__main__':
    # Keep ROS alive on Ctrl+C long enough for the finally block to request landing.
    rospy.init_node('tello_demo', disable_signals=True)
    try:
        if not os.environ.get('DISPLAY'):
            raise RuntimeError('A desktop DISPLAY is required for the camera window')
        cv2.namedWindow('Tello front camera', cv2.WINDOW_NORMAL)
        Demo().run()
    except (KeyboardInterrupt, RuntimeError, rospy.ROSException, cv2.error) as error:
        rospy.logerr('Demo stopped: %s. If landing was not confirmed, check the simulator.', error)
        raise SystemExit(1)
    finally:
        cv2.destroyAllWindows()
        rospy.signal_shutdown('demo exited')
