"""Check demo control intent with mocked ROS actions; not a flight test."""
import importlib.util
import math
from pathlib import Path
import unittest
from unittest.mock import Mock, patch

from geometry_msgs.msg import PoseStamped
from sensor_msgs.msg import Image

PATH = Path(__file__).resolve().parents[2] / 'tello_control/scripts/demo.py'
SPEC = importlib.util.spec_from_file_location('tello_control_demo', str(PATH))
DEMO = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(DEMO)


class ControlDemoTest(unittest.TestCase):
    def make_demo(self):
        demo = DEMO.Demo.__new__(DEMO.Demo)
        demo.command, demo.judge = Mock(), Mock()
        demo.takeoff, demo.land = Mock(), Mock()
        demo.state = {'ready': True, 'armed': False}
        demo.wait_until, demo.wait_action, demo.move = Mock(), Mock(), Mock()
        demo.rotate_ccw = Mock()
        return demo

    @patch.object(DEMO.rospy, 'loginfo')
    def test_flight_sequence_and_one_report(self, _log):
        demo = self.make_demo()
        events = []
        demo.wait_action.side_effect = lambda client, *args: events.append(
            'takeoff' if client is demo.takeoff else 'land')
        demo.move.side_effect = lambda **kwargs: events.append(kwargs)
        demo.rotate_ccw.side_effect = lambda degrees: events.append(('rotate_ccw', degrees))
        demo.judge.publish.side_effect = lambda msg: events.append(msg.data)
        with patch.object(DEMO.rospy.Time, 'now'):
            demo.run()
        self.assertEqual(events, ['takeoff', {'left': -0.10}, {'seconds': 1.0},
                                  ('rotate_ccw', 90.0), {'seconds': 1.0},
                                  {'forward': 0.10}, 'land', 'rg'])
        demo.judge.publish.assert_called_once()
        self.assertEqual(demo.wait_action.call_args_list[0][0][1].height, 0.48)

    @patch.object(DEMO.rospy, 'loginfo')
    def test_movement_failure_still_requests_landing(self, _log):
        demo = self.make_demo()
        demo.move.side_effect = RuntimeError('lost pose')
        with patch.object(DEMO.rospy.Time, 'now'), self.assertRaises(RuntimeError):
            demo.run()
        self.assertIs(demo.wait_action.call_args[0][0], demo.land)
        demo.takeoff.cancel_all_goals.assert_called_once()
        demo.judge.publish.assert_not_called()
        self.assertEqual(demo.command.publish.call_args[0][0].linear.y, 0)

    def test_callbacks_store_absolute_pose_and_image(self):
        demo = self.make_demo()
        pose, image = PoseStamped(), Image()
        pose.pose.position.x = -1.13
        pose.pose.orientation.w = 1.0
        pose.header.frame_id = 'world'
        with patch.object(DEMO.rospy, 'loginfo_throttle') as log:
            demo.on_pose(pose)
        demo.on_image(image)
        self.assertIs(demo.pose, pose)
        self.assertEqual(demo.pose.pose.position.x, -1.13)
        self.assertIs(demo.image, image)
        log.assert_called_once()
        self.assertIn('roll=', log.call_args[0][1])
        self.assertNotIn('quaternion', log.call_args[0][1])
        self.assertEqual(log.call_args[0][-3:], (0.0, 0.0, 0.0))

    def test_quaternion_conversion_and_normalization(self):
        self.assertEqual(DEMO.quaternion_to_euler(0, 0, 0, 1), (0, 0, 0))
        roll, pitch, yaw = DEMO.quaternion_to_euler(0, 0, math.sqrt(2), math.sqrt(2))
        self.assertAlmostEqual(roll, 0)
        self.assertAlmostEqual(pitch, 0)
        self.assertAlmostEqual(math.degrees(yaw), 90)
        from tf.transformations import quaternion_from_euler
        angles = tuple(map(math.radians, (30, 20, -170)))
        actual = DEMO.quaternion_to_euler(*quaternion_from_euler(*angles))
        for expected, value in zip(angles, actual):
            self.assertAlmostEqual(expected, value)

    def test_invalid_quaternion_rejected(self):
        for q in [(0, 0, 0, 0), (float('nan'), 0, 0, 1)]:
            with self.assertRaises(ValueError):
                DEMO.quaternion_to_euler(*q)

    @patch.object(DEMO.rospy, 'loginfo')
    def test_rotation_crosses_yaw_wrap_and_stops(self, _log):
        demo = self.make_demo()
        demo.pose_received = DEMO.time.monotonic()
        demo.tick = Mock()
        demo.yaw = Mock(side_effect=[math.radians(v) for v in
                                    (170, 170, -170, -101, -100, -100)])
        now = Mock()
        now.to_sec.side_effect = [0, .1, .2, .8]
        with patch.object(DEMO.rospy.Time, 'now', return_value=now):
            DEMO.Demo.rotate_ccw(demo, 90)
        commands = [call[0][0] for call in demo.command.publish.call_args_list]
        self.assertGreater(commands[0].angular.z, 0)
        self.assertTrue(all(0 <= c.angular.z <= .45 for c in commands))
        self.assertTrue(all(c.linear.x == c.linear.y == c.linear.z == 0 for c in commands))
        self.assertEqual(commands[-1].angular.z, 0)

    def test_rotation_stale_pose_stops(self):
        demo = self.make_demo()
        demo.yaw = Mock(return_value=0)
        demo.pose_received = DEMO.time.monotonic()-3
        with self.assertRaises(RuntimeError):
            DEMO.Demo.rotate_ccw(demo)
        self.assertEqual(demo.command.publish.call_args[0][0].angular.z, 0)

    @patch.object(DEMO.rospy, 'loginfo')
    def test_rotation_failure_still_lands(self, _log):
        demo = self.make_demo()
        demo.rotate_ccw.side_effect = RuntimeError('lost pose during turn')
        with patch.object(DEMO.rospy.Time, 'now'), self.assertRaises(RuntimeError):
            demo.run()
        self.assertIs(demo.wait_action.call_args[0][0], demo.land)
        demo.judge.publish.assert_not_called()

    def test_right_velocity_and_final_stop(self):
        demo = self.make_demo()
        demo.pose_received = DEMO.time.monotonic()
        demo.tick = Mock()
        times = [Mock(), Mock(), Mock()]
        for obj, value in zip(times, [10.0, 10.1, 12.1]):
            obj.to_sec.return_value = value
        with patch.object(DEMO.rospy.Time, 'now', side_effect=times):
            DEMO.Demo.move(demo, left=-0.10)
        messages = [call[0][0] for call in demo.command.publish.call_args_list]
        self.assertEqual(messages[0].linear.y, -0.10)
        self.assertEqual(messages[0].linear.x, 0.0)
        self.assertEqual(messages[-1].linear.y, 0.0)

    def test_camera_is_converted_and_displayed_on_tick(self):
        demo = self.make_demo()
        demo.image, demo.bridge = Image(), Mock()
        with patch.object(DEMO.rospy, 'is_shutdown', return_value=False), \
                patch.object(DEMO.cv2, 'imshow') as show, \
                patch.object(DEMO.cv2, 'waitKey'), patch.object(DEMO.time, 'sleep'):
            demo.tick()
        demo.bridge.imgmsg_to_cv2.assert_called_once_with(demo.image, desired_encoding='bgr8')
        show.assert_called_once_with('Tello front camera', demo.bridge.imgmsg_to_cv2.return_value)


if __name__ == '__main__':
    unittest.main()
