"""Dashboard and ROS event publication share the same scoring snapshot."""
import collections
import importlib.util
import json
from pathlib import Path
import threading
import time
import unittest
from unittest.mock import Mock, patch

from std_msgs.msg import String
from tello_competition.geometry import Arena, Rules
from tello_competition.rules import Scorekeeper

SPEC = importlib.util.spec_from_file_location('judge_adapter_under_test', str(
    Path(__file__).resolve().parents[1] / 'scripts/final_judge.py'))
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class JudgeAdapterTest(unittest.TestCase):
    def setUp(self):
        self.judge = MODULE.FinalJudge.__new__(MODULE.FinalJudge)
        j = self.judge
        j.dashboard = True
        j.lock = threading.RLock()
        j.history = collections.deque(maxlen=2000)
        j.last_sample_wall = time.monotonic()
        j.arena, j.rules = Arena(), Rules()
        j.scorekeeper = Scorekeeper(j.arena, j.rules, dict(
            round_id='test:1', colors='gr', active_window=1, lamp_indices=[0, 4, 8]))
        j.events_pub, j.status_pub = Mock(), Mock()

    def test_additive_fields_and_snapshot_match_public_event(self):
        j = self.judge
        event = dict(kind='judge_message', message='target1', accepted=False,
                     reason='too_far_from_lamp', score_delta=0)
        j.emit_event(event)
        published = json.loads(j.events_pub.publish.call_args[0][0])
        self.assertEqual(published['reason'], 'too_far_from_lamp')
        self.assertEqual(published['score'], 0)
        self.assertEqual(published['elapsed'], 0)
        self.assertEqual(published['round_id'], 'test:1')
        status, history, age = j.snapshot()
        self.assertEqual(history, [published])
        self.assertEqual(status['score'], published['score'])
        self.assertGreaterEqual(age, 0)
        self.assertNotIn('colors', published)
        self.assertNotIn('lamp_indices', published)

    def test_reset_clears_old_history_and_score(self):
        j = self.judge
        j.emit_event(dict(kind='takeoff'))
        j.scorekeeper.scores['takeoff'] = 15
        j.round_callback(String(data=json.dumps(dict(
            round_id='test:2', colors='rb', active_window=0, lamp_indices=[8, 4, 0]))))
        status, history, _ = j.snapshot()
        self.assertEqual(status['score'], 0)
        self.assertEqual(status['round_id'], 'test:2')
        self.assertEqual([e['kind'] for e in history], ['round_started'])

    def test_plain_logs_include_submissions_but_tui_does_not_scroll(self):
        with patch.object(MODULE.rospy, 'loginfo') as logger:
            self.judge.emit_event(dict(kind='takeoff'))
            logger.assert_not_called()
            self.judge.dashboard = False
            self.judge.emit_event(dict(kind='judge_message', message='gr'))
            logger.assert_called_once()
