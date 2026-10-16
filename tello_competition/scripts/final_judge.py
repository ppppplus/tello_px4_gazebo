#!/usr/bin/env python3
"""ROS adapter for the deterministic competition scorekeeper."""

import json
import collections
import sys
import threading
import time

import rospy
from nav_msgs.msg import Odometry
from std_msgs.msg import String
from tf.transformations import euler_from_quaternion

from tello_competition.geometry import Arena, Rules
from tello_competition.rules import FlightSample, Scorekeeper
from tello_competition.judge_display import run_dashboard


class FinalJudge:
    def __init__(self, dashboard=False):
        self.dashboard = dashboard
        self.history = collections.deque(maxlen=2000)
        self.last_sample_wall = time.monotonic()
        self.arena = Arena.from_dict(rospy.get_param('/arena'))
        self.rules = Rules.from_dict(rospy.get_param('/rules'))
        self.name = rospy.get_param('/final/drone_name', 'tello').strip('/')
        self.lock = threading.RLock()
        self.scorekeeper = None
        self.status_pub = rospy.Publisher('/final/status', String, queue_size=5, latch=True)
        self.events_pub = rospy.Publisher('/final/events', String, queue_size=30)
        self.light_pub = rospy.Publisher('/teacher/final/light_progress', String,
                                         queue_size=5, latch=True)
        rospy.Subscriber('/teacher/final/round', String, self.round_callback, queue_size=1)
        rospy.Subscriber('/teacher/ground_truth/odom', Odometry,
                         self.odometry_callback, queue_size=30)
        rospy.Subscriber(f'/{self.name}/judge', String, self.message_callback, queue_size=30)
        rospy.Timer(rospy.Duration(0.25), self.publish_status)

    def round_callback(self, message):
        with self.lock:
            try:
                data = json.loads(message.data)
                self.scorekeeper = Scorekeeper(self.arena, self.rules, data)
                self.history.clear()
                self.emit_event({'kind': 'round_started'})
                self.publish_status()
            except (ValueError, KeyError, TypeError) as error:
                rospy.logerr('Invalid round configuration: %s', error)

    def odometry_callback(self, message):
        with self.lock:
            if self.scorekeeper is None:
                return
            position, orientation = message.pose.pose.position, message.pose.pose.orientation
            roll, pitch, _ = euler_from_quaternion(
                (orientation.x, orientation.y, orientation.z, orientation.w))
            velocity = message.twist.twist.linear
            now = message.header.stamp.to_sec() or rospy.Time.now().to_sec()
            sample = FlightSample(now, position.x, position.y, position.z,
                                  velocity.x, velocity.y, velocity.z, roll, pitch)
            self.last_sample_wall = time.monotonic()
            for event in self.scorekeeper.update(sample):
                self.emit_event(event)
            if self.scorekeeper.phase == 'finished':
                self.publish_status()

    def message_callback(self, message):
        with self.lock:
            if self.scorekeeper is None:
                return
            result = self.scorekeeper.submit(message.data.strip())
            result.update({'kind': 'judge_message', 'message': message.data,
                           'round_id': self.scorekeeper.round['round_id']})
            self.emit_event(result)
            if result.get('progress'):
                self.light_pub.publish(json.dumps(
                    {'round_id': self.scorekeeper.round['round_id'],
                     'progress': result['progress']}))
            self.publish_status()

    def emit_event(self, event):
        # Called with the judge lock held. Extra public fields are additive;
        # no target answers or scoring conditions are exposed or changed.
        event.update(round_id=self.scorekeeper.round['round_id'],
                     elapsed=round(self.scorekeeper.elapsed, 3),
                     score=self.scorekeeper.score)
        self.history.append(dict(event))
        self.events_pub.publish(json.dumps(event, ensure_ascii=False))
        if not self.dashboard:
            rospy.loginfo('Judge event: %s', event)

    def snapshot(self):
        with self.lock:
            status = self.scorekeeper.status() if self.scorekeeper is not None else None
            return status, list(self.history), time.monotonic()-self.last_sample_wall

    def publish_status(self, _event=None):
        with self.lock:
            if self.scorekeeper is not None:
                self.status_pub.publish(json.dumps(
                    self.scorekeeper.status(), ensure_ascii=False))


if __name__ == '__main__':
    rospy.init_node('final_judge', disable_signals=True)
    dashboard = rospy.get_param('~dashboard', sys.stdout.isatty() and sys.stdin.isatty())
    if dashboard and not (sys.stdout.isatty() and sys.stdin.isatty()):
        rospy.logwarn('Dashboard requires a terminal; using ordinary ROS logs.')
        dashboard = False
    judge = FinalJudge(dashboard=dashboard)
    try:
        if dashboard:
            run_dashboard(judge.snapshot, rospy.is_shutdown)
        else:
            rospy.spin()
    except KeyboardInterrupt:
        pass
    finally:
        rospy.signal_shutdown('judge stopped')
