#!/usr/bin/env python3
"""Give the PX4 FPV camera the stable topic names used by students."""

import rospy
from sensor_msgs.msg import CameraInfo, Image


class CameraRelay:
    def __init__(self):
        self.image_pub = rospy.Publisher('/front_cam/camera/image', Image, queue_size=1)
        self.info_pub = rospy.Publisher('/front_cam/camera/camera_info', CameraInfo,
                                        queue_size=1)
        rospy.Subscriber('/usb_cam/image_raw', Image, self.image_pub.publish, queue_size=1)
        rospy.Subscriber('/usb_cam/camera_info', CameraInfo, self.info_pub.publish, queue_size=1)


if __name__ == '__main__':
    rospy.init_node('front_camera_relay')
    CameraRelay()
    rospy.spin()
