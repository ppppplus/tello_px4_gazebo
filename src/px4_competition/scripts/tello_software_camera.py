#!/usr/bin/env python3
"""Tello extrinsics for the optional, schematic CPU camera; Iris is unchanged."""
import math

import rospy
from px4_competition.software_camera import SoftwareCamera


class TelloSoftwareCamera(SoftwareCamera):
    def project(self, point, position, yaw):
        # Same yaw-only approximation as the original fallback camera, but
        # measured from the Tello front sensor rather than the Iris offset.
        dx, dy = point[0] - position.x, point[1] - position.y
        dz = point[2] - position.z - .005
        forward = math.cos(yaw) * dx + math.sin(yaw) * dy - .036
        left = -math.sin(yaw) * dx + math.cos(yaw) * dy
        if forward <= .01:
            return None
        return (int(round(self.width / 2 - self.focal * left / forward)),
                int(round(self.height / 2 - self.focal * dz / forward)), forward)


if __name__ == '__main__':
    rospy.init_node('software_camera')
    TelloSoftwareCamera()
    rospy.spin()
