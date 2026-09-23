#!/usr/bin/env python3
"""Small CPU-only forward camera for machines where Gazebo/OGRE cannot render."""

import json
import math
import threading

import numpy as np
import rospy
from nav_msgs.msg import Odometry
from sensor_msgs.msg import CameraInfo, Image
from std_msgs.msg import String
from tf.transformations import euler_from_quaternion

from px4_competition.geometry import Arena


COLORS = {'r': (242, 6, 6), 'g': (5, 184, 43), 'b': (6, 41, 242)}


class SoftwareCamera:
    def __init__(self):
        self.arena = Arena.from_dict(rospy.get_param('/arena'))
        self.width, self.height, self.focal = 320, 240, 277.0
        self.lock = threading.RLock()
        self.odom = self.round = None
        self.lamp_progress = 0
        self.image_pub = rospy.Publisher('/front_cam/camera/image', Image, queue_size=1)
        self.info_pub = rospy.Publisher('/front_cam/camera/camera_info', CameraInfo,
                                        queue_size=1)
        rospy.Subscriber('/teacher/ground_truth/odom', Odometry,
                         self.odom_callback, queue_size=1)
        rospy.Subscriber('/teacher/final/round', String, self.round_callback, queue_size=1)
        rospy.Subscriber('/final/status', String, self.status_callback, queue_size=1)
        rospy.Timer(rospy.Duration(0.1), self.render)

    def odom_callback(self, message):
        with self.lock:
            self.odom = message

    def round_callback(self, message):
        try:
            value = json.loads(message.data)
        except ValueError:
            return
        with self.lock:
            self.round = value
            self.lamp_progress = 0

    def status_callback(self, message):
        try:
            value = json.loads(message.data)
        except ValueError:
            return
        with self.lock:
            self.lamp_progress = int(value.get('lamp_progress', 0))

    def project(self, point, position, yaw):
        dx, dy, dz = (point[0] - position.x, point[1] - position.y,
                      point[2] - position.z - 0.05)
        forward = math.cos(yaw) * dx + math.sin(yaw) * dy
        left = -math.sin(yaw) * dx + math.cos(yaw) * dy
        if forward <= 0.08:
            return None
        u = self.width / 2 - self.focal * left / forward
        v = self.height / 2 - self.focal * dz / forward
        return int(round(u)), int(round(v)), forward

    @staticmethod
    def circle(image, x, y, radius, color):
        if radius <= 0:
            return
        yy, xx = np.ogrid[:image.shape[0], :image.shape[1]]
        mask = (xx - x) ** 2 + (yy - y) ** 2 <= radius ** 2
        image[mask] = color

    def render(self, _event):
        with self.lock:
            odom, round_data, progress = self.odom, self.round, self.lamp_progress
        if odom is None or round_data is None:
            return
        pose = odom.pose.pose
        q = pose.orientation
        _, _, yaw = euler_from_quaternion((q.x, q.y, q.z, q.w))
        image = np.empty((self.height, self.width, 3), dtype=np.uint8)
        image[:self.height // 2] = (155, 190, 220)
        image[self.height // 2:] = (90, 95, 88)

        objects = []
        for index, x in enumerate(self.arena.cabinet_centers_x):
            objects.append(((x, self.arena.cabinet_y,
                             self.arena.cabinet_hole_center_height),
                            self.arena.ball_radius, COLORS[round_data['colors'][index]]))
        marker_x = self.arena.window_centers_x[round_data['active_window']]
        objects.append(((marker_x, -self.arena.wall_thickness / 2 - 0.01,
                         self.arena.marker_center_height),
                        self.arena.marker_radius, (250, 0, 0)))
        for index, lamp_index in enumerate(round_data['lamp_indices']):
            objects.append((self.arena.lamp_position(lamp_index),
                            self.arena.lamp_radius * 2.2,
                            (255, 20, 20) if index == progress else (45, 50, 55)))
        projected = []
        for point, radius, color in objects:
            value = self.project(point, pose.position, yaw)
            if value is not None:
                projected.append((value[2], value[0], value[1], radius, color))
        for depth, u, v, radius, color in sorted(projected, reverse=True):
            pixel_radius = max(2, min(45, int(self.focal * radius / depth)))
            if -pixel_radius < u < self.width + pixel_radius and -pixel_radius < v < self.height + pixel_radius:
                self.circle(image, u, v, pixel_radius, color)

        stamp = rospy.Time.now()
        message = Image()
        message.header.stamp = stamp
        message.header.frame_id = 'front_camera_link'
        message.height, message.width = self.height, self.width
        message.encoding, message.is_bigendian = 'rgb8', 0
        message.step = self.width * 3
        message.data = image.tobytes()
        info = CameraInfo()
        info.header = message.header
        info.height, info.width = self.height, self.width
        info.distortion_model = 'plumb_bob'
        info.K = [self.focal, 0, self.width / 2, 0, self.focal,
                  self.height / 2, 0, 0, 1]
        info.P = [self.focal, 0, self.width / 2, 0, 0, self.focal,
                  self.height / 2, 0, 0, 0, 1, 0]
        self.image_pub.publish(message)
        self.info_pub.publish(info)


if __name__ == '__main__':
    rospy.init_node('software_camera')
    SoftwareCamera()
    rospy.spin()
