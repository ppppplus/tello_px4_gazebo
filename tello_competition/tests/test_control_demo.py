"""Check demo control intent with mocked ROS actions; not a flight test."""
import importlib.util
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
        return demo

    @patch.object(DEMO.rospy, 'loginfo')
    def test_flight_sequence_and_one_report(self, _log):
        demo = self.make_demo()
        events = []
        demo.wait_action.side_effect = lambda client, *args: events.append(
            'takeoff' if client is demo.takeoff else 'land')
        demo.move.side_effect = lambda **kwargs: events.append(kwargs)
        demo.judge.publish.side_effect = lambda msg: events.append(msg.data)
        with patch.object(DEMO.rospy.Time, 'now'):
            demo.run()
        self.assertEqual(events, ['takeoff', {'left': -0.10}, {'seconds': 1.0},
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
        pose.header.frame_id = 'world'
        with patch.object(DEMO.rospy, 'loginfo_throttle') as log:
            demo.on_pose(pose)
        demo.on_image(image)
        self.assertIs(demo.pose, pose)
        self.assertEqual(demo.pose.pose.position.x, -1.13)
        self.assertIs(demo.image, image)
        log.assert_called_once()

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
