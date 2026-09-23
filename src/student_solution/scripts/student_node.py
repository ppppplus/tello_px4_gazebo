#!/usr/bin/env python3
"""Read public inputs by default; --smoke explicitly authorizes takeoff/land."""
import argparse
import json
import time

import actionlib
import rospy
from geometry_msgs.msg import Twist
from nav_msgs.msg import Odometry
from sensor_msgs.msg import Image
from std_msgs.msg import String
from px4_competition.msg import TakeoffAction, TakeoffGoal, LandAction, LandGoal


class Student:
    def __init__(self):
        self.state = {}
        self.odom = None
        self.image = None
        self.frames = 0
        self.command = rospy.Publisher('/quadrotor/cmd_vel', Twist, queue_size=1)
        self.judge = rospy.Publisher('/quadrotor/judge', String, queue_size=1)
        rospy.Subscriber('/quadrotor/state', String, self.on_state, queue_size=1)
        rospy.Subscriber('/quadrotor/odom', Odometry, self.on_odom, queue_size=1)
        rospy.Subscriber('/front_cam/camera/image', Image, self.on_image, queue_size=1, buff_size=2**22)
        self.takeoff = actionlib.SimpleActionClient('/quadrotor/takeoff', TakeoffAction)
        self.land = actionlib.SimpleActionClient('/quadrotor/land', LandAction)

    def on_state(self, msg):
        self.state = json.loads(msg.data)

    def on_odom(self, msg):
        self.odom = msg

    def on_image(self, msg):
        self.image = msg
        self.frames += 1
        # TODO: recognize cabinet colors, window marker and newly lit lamp.
        # Do not read /teacher, /gazebo or /mavros state.

    def smoke(self):
        deadline = time.monotonic()+60
        ready_since = None
        while not rospy.is_shutdown():
            if self.state.get('ready') and self.odom and self.frames >= 5:
                ready_since = ready_since or rospy.Time.now()
                # The public ready flag means connection/odometry, not PX4's
                # full pre-arm checks. Allow estimator initialization first.
                if (rospy.Time.now()-ready_since).to_sec() >= 8:
                    break
            else:
                ready_since = None
            if time.monotonic() > deadline:
                raise RuntimeError('Public state, odometry or camera not ready')
            time.sleep(.1)
        if self.state.get('armed'):
            raise RuntimeError('Smoke test requires a disarmed aircraft at the start pad')
        for client in (self.takeoff, self.land):
            if not client.wait_for_server(rospy.Duration(10)):
                raise RuntimeError('Action server missing')
        attempted = False
        try:
            attempted = True
            self.takeoff.send_goal(TakeoffGoal(height=.48))
            if not self.takeoff.wait_for_result(rospy.Duration(40)) or not self.takeoff.get_result().success:
                raise RuntimeError('Takeoff failed')
            # Publish zero velocity at 20 Hz for three wall-clock seconds.
            # A student algorithm should actively correct position while observing.
            deadline = time.monotonic()+3
            while time.monotonic() < deadline and not rospy.is_shutdown():
                self.command.publish(Twist())
                time.sleep(.05)
        finally:
            if attempted:
                self.command.publish(Twist())
                self.land.send_goal(LandGoal())
                if not self.land.wait_for_result(rospy.Duration(50)) or not self.land.get_result().success:
                    raise RuntimeError('Landing was not confirmed; inspect the simulator')
        deadline=time.monotonic()+5
        while self.state.get('armed') and time.monotonic()<deadline:
            time.sleep(.1)
        if self.state.get('armed'):
            raise RuntimeError('Still armed after landing')
        print(json.dumps(dict(passed=True, camera=[self.image.width,self.image.height],
                              frames=self.frames, state=self.state)),flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--smoke', action='store_true')
    args=parser.parse_args(rospy.myargv()[1:])
    rospy.init_node('student_solution')
    student=Student()
    if args.smoke:
        student.smoke()
    else:
        rospy.loginfo('Student template listening. Use --smoke only to test takeoff and landing.')
        rospy.spin()
