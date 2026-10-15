"""Ground-truth public interface tests without a running ROS master."""
import importlib.util
from pathlib import Path
import unittest
from unittest.mock import patch

import rospy
from gazebo_msgs.msg import ModelStates
from geometry_msgs.msg import Pose, PoseStamped, Twist
from nav_msgs.msg import Odometry

SCRIPT = Path(__file__).resolve().parents[1] / 'scripts/gazebo_truth.py'
SPEC = importlib.util.spec_from_file_location('course_gazebo_truth', str(SCRIPT))
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class GazeboTruthTest(unittest.TestCase):
    def setUp(self):
        self.patches = [patch.object(MODULE.rospy, 'get_param', return_value='tello'),
                        patch.object(MODULE.rospy, 'Publisher'),
                        patch.object(MODULE.rospy, 'Subscriber'),
                        patch.object(MODULE.rospy.Time, 'now', return_value=rospy.Time(42, 123))]
        self.mocks = [p.start() for p in self.patches]
        for p in self.patches:
            self.addCleanup(p.stop)
        # Each topic must have a separate publisher mock.
        from unittest.mock import Mock
        self.mocks[1].side_effect = lambda *args, **kwargs: Mock()
        self.node = MODULE.GazeboTruth()

    def test_public_and_teacher_types(self):
        self.mocks[0].assert_called_once_with('~model', 'tello')
        self.mocks[1].assert_any_call('/tello/pose', PoseStamped, queue_size=20)
        self.mocks[1].assert_any_call('/teacher/ground_truth/odom', Odometry, queue_size=20)
        self.mocks[2].assert_called_once_with('/gazebo/model_states', ModelStates,
                                            self.node.callback, queue_size=5)

    def test_exact_world_pose_and_shared_timestamp(self):
        pose = Pose()
        pose.position.x, pose.position.y, pose.position.z = -1.13, 0.52, 0.82
        pose.orientation.z, pose.orientation.w = 0.6, 0.8
        twist = Twist()
        twist.linear.x = 0.12
        states = ModelStates(name=['ground_plane', 'tello'],
                             pose=[Pose(), pose], twist=[Twist(), twist])
        self.node.callback(states)
        public = self.node.pose_publisher.publish.call_args[0][0]
        teacher = self.node.publisher.publish.call_args[0][0]
        self.assertIsInstance(public, PoseStamped)
        self.assertEqual(public.pose, pose)
        self.assertEqual(public.header.frame_id, 'world')
        self.assertEqual(public.header.stamp, rospy.Time(42, 123))
        self.assertEqual(public.header, teacher.header)
        self.assertEqual(public.pose, teacher.pose.pose)
        self.assertEqual(teacher.twist.twist, twist)
        self.assertEqual(teacher.child_frame_id, 'tello/base_link')

    def test_missing_model_does_not_publish(self):
        self.node.callback(ModelStates(name=['other'], pose=[Pose()], twist=[Twist()]))
        self.node.publisher.publish.assert_not_called()
        self.node.pose_publisher.publish.assert_not_called()


if __name__ == '__main__':
    unittest.main()
