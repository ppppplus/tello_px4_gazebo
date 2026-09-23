#!/usr/bin/env python3
"""ROS adapter for the deterministic competition scorekeeper."""

import json
import threading

import rospy
from nav_msgs.msg import Odometry
from std_msgs.msg import String
from tf.transformations import euler_from_quaternion

from px4_competition.geometry import Arena, Rules
from px4_competition.rules import FlightSample, Scorekeeper


class FinalJudge:
    def __init__(self):
        self.arena = Arena.from_dict(rospy.get_param('/arena'))
        self.rules = Rules.from_dict(rospy.get_param('/rules'))
        self.name = rospy.get_param('/final/drone_name', 'quadrotor').strip('/')
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
                self.events_pub.publish(json.dumps(
                    {'kind': 'round_started', 'round_id': data['round_id']}))
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
            for event in self.scorekeeper.update(sample):
                event['round_id'] = self.scorekeeper.round['round_id']
                self.events_pub.publish(json.dumps(event))
                rospy.loginfo('Judge event: %s', event)
            if self.scorekeeper.phase == 'finished':
                self.publish_status()

    def message_callback(self, message):
        with self.lock:
            if self.scorekeeper is None:
                return
            result = self.scorekeeper.submit(message.data.strip())
            result.update({'kind': 'judge_message', 'message': message.data,
                           'round_id': self.scorekeeper.round['round_id']})
            self.events_pub.publish(json.dumps(result, ensure_ascii=False))
            if result.get('progress'):
                self.light_pub.publish(json.dumps(
                    {'round_id': self.scorekeeper.round['round_id'],
                     'progress': result['progress']}))
            self.publish_status()

    def publish_status(self, _event=None):
        with self.lock:
            if self.scorekeeper is not None:
                self.status_pub.publish(json.dumps(
                    self.scorekeeper.status(), ensure_ascii=False))


if __name__ == '__main__':
    rospy.init_node('final_judge')
    FinalJudge()
    rospy.spin()
