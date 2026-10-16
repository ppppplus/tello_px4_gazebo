#!/usr/bin/env python3
"""Practice-only reset: place a landed, disarmed Tello at the start; reset scores."""
import json
import math
import time

import rospy
from geometry_msgs.msg import PoseStamped
from std_msgs.msg import String
from std_srvs.srv import Trigger


def check_safe(state):
    if state.get('armed') is not False or state.get('landed_state') != 1:
        raise RuntimeError('Land and disarm first; stop all student control programs before reset')
    if not state.get('connected') or state.get('resetting'):
        raise RuntimeError('Flight controller disconnected or another reset is running')


def reset():
    state = rospy.wait_for_message('/tello/state', String, timeout=10)
    check_safe(json.loads(state.data))
    start = rospy.get_param('/arena/start_pose')
    rospy.wait_for_service('/final/reset', timeout=10)
    answer = rospy.ServiceProxy('/final/reset', Trigger)()
    if not answer.success:
        raise RuntimeError(answer.message)
    # Verify the public truth pose, not PX4's possibly settling estimate.
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        pose = rospy.wait_for_message('/tello/pose', PoseStamped, timeout=3).pose.position
        if math.dist((pose.x, pose.y, pose.z), start) < 0.06:
            rospy.loginfo('Returned to start. New round: %s; score cleared. '
                          'Wait for PX4 initialization before flying again.', answer.message)
            return
    raise RuntimeError('Reset service returned success but the start pose was not confirmed')


if __name__ == '__main__':
    rospy.init_node('tello_reset_start')
    try:
        reset()
    except (RuntimeError, rospy.ROSException, rospy.ServiceException) as error:
        rospy.logerr('Reset failed: %s', error)
        raise SystemExit(1)
