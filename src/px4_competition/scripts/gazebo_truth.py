#!/usr/bin/env python3
"""Publish authoritative odometry for the referee from Gazebo ModelStates."""

import rospy
from gazebo_msgs.msg import ModelStates
from nav_msgs.msg import Odometry


class GazeboTruth:
    def __init__(self):
        self.model = rospy.get_param('~model', 'iris')
        self.publisher = rospy.Publisher('/teacher/ground_truth/odom', Odometry,
                                         queue_size=20)
        rospy.Subscriber('/gazebo/model_states', ModelStates, self.callback, queue_size=5)

    def callback(self, message):
        try:
            index = message.name.index(self.model)
        except ValueError:
            return
        result = Odometry()
        result.header.stamp = rospy.Time.now()
        result.header.frame_id = 'world'
        result.child_frame_id = f'{self.model}/base_link'
        result.pose.pose = message.pose[index]
        result.twist.twist = message.twist[index]
        self.publisher.publish(result)


if __name__ == '__main__':
    rospy.init_node('gazebo_truth')
    GazeboTruth()
    rospy.spin()
