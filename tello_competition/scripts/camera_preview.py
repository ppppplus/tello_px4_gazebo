#!/usr/bin/env python3
"""Show the public student camera as a framed desktop picture-in-picture."""

import threading

import cv2
import numpy as np
import rospy
from sensor_msgs.msg import Image


class CameraPreview:
    def __init__(self):
        self.title = rospy.get_param('~title', 'Student FPV')
        self.lock = threading.Lock()
        self.image = None
        rospy.Subscriber('/tello/front_cam/camera/image', Image, self.callback,
                         queue_size=1, buff_size=2 ** 20)

    def callback(self, message):
        if message.encoding not in ('rgb8', 'bgr8'):
            return
        image = np.frombuffer(message.data, dtype=np.uint8)
        image = image.reshape(message.height, message.width, 3)
        bgr = image[:, :, ::-1].copy() if message.encoding == 'rgb8' else image.copy()
        with self.lock:
            self.image = bgr

    def frame(self):
        canvas = np.full((405, 500, 3), (20, 24, 28), dtype=np.uint8)
        with self.lock:
            image = None if self.image is None else self.image.copy()
        if image is None:
            cv2.putText(canvas, 'Waiting for /tello/front_cam/camera/image', (48, 210),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.55, (180, 185, 190), 1,
                        cv2.LINE_AA)
        else:
            view = cv2.resize(image, (480, 360), interpolation=cv2.INTER_NEAREST)
            canvas[35:395, 10:490] = view
        cv2.rectangle(canvas, (7, 32), (492, 398), (40, 205, 255), 3)
        cv2.putText(canvas, 'STUDENT FPV', (12, 24), cv2.FONT_HERSHEY_SIMPLEX,
                    0.62, (255, 255, 255), 2, cv2.LINE_AA)
        cv2.putText(canvas, '320x240 / sim', (330, 23),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.42, (150, 200, 255), 1,
                    cv2.LINE_AA)
        return canvas

    def run(self):
        cv2.namedWindow(self.title, cv2.WINDOW_NORMAL)
        cv2.resizeWindow(self.title, 500, 405)
        rate = rospy.Rate(30)
        while not rospy.is_shutdown():
            cv2.imshow(self.title, self.frame())
            if cv2.waitKey(1) in (27, ord('q')):
                break
            rate.sleep()
        cv2.destroyAllWindows()


if __name__ == '__main__':
    rospy.init_node('camera_preview')
    CameraPreview().run()
