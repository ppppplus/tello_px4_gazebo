#!/usr/bin/env python3
"""ROS executable wrapper for the schematic CPU camera."""
import rospy
from px4_competition.software_camera import SoftwareCamera

if __name__ == '__main__':
    rospy.init_node('software_camera')
    SoftwareCamera()
    rospy.spin()
