import unittest

from tello_competition.judge_display import clock_text, fit_text, event_text, dashboard_rows


class JudgeDisplayTest(unittest.TestCase):
    def test_clock(self):
        self.assertEqual(clock_text(0), '00:00.0')
        self.assertEqual(clock_text(141.735), '02:21.7')
        self.assertEqual(clock_text(3601.2), '60:01.2')

    def test_chinese_width_and_control_sanitization(self):
        self.assertEqual(fit_text('起飞 abc', 6), '起飞 a')
        self.assertEqual(fit_text('a\x1b\nb', 10), 'a  b')

    def test_takeoff_window_and_landing(self):
        for kind, word, score in [('takeoff', '起飞', 15), ('window', '穿越', 20),
                                  ('landing', '降落', 15)]:
            text = event_text({'kind': kind, 'score_delta': score})
            self.assertIn(word, text)
            self.assertIn('+%d 分' % score, text)

    def test_ball_reports_submission_not_hidden_answer(self):
        text = event_text(dict(kind='judge_message', accepted=True,
            reason='ball_result_recorded', message='gr', score_delta=10))
        self.assertIn('旋转柜绿 / 固定柜红', text)
        self.assertIn('+10 分', text)

    def test_lamp_confirmation(self):
        text = event_text(dict(kind='judge_message', accepted=True,
            reason='lamp_confirmed', message='target2', distance=.2163, score_delta=10))
        self.assertIn('到达 target2 前', text)
        self.assertIn('0.216 m', text)

    def test_rejection_not_reported_as_success(self):
        text = event_text(dict(kind='judge_message', accepted=False,
            reason='too_far_from_lamp', message='target1', distance=.5))
        self.assertIn('拒绝', text)
        self.assertIn('距离红点过远', text)
        self.assertNotIn('+10', text)

    def test_status_timer_score_and_staleness(self):
        state = dict(phase='running', elapsed=65.4, score=35, scores={})
        header, _ = dashboard_rows(state, [], 3)
        self.assertIn('01:05.4', header[2])
        self.assertIn('35 / 100', header[2])
        self.assertIn('已中断', header[7])
        state.update(phase='finished', elapsed=141.735, score=100)
        header, _ = dashboard_rows(state, [], 0)
        self.assertIn('比赛结束', header[1])
        self.assertIn('02:21.7', header[2])
        self.assertIn('100 / 100', header[2])

    def test_event_timestamp_and_order_preserved(self):
        _, lines = dashboard_rows({}, [dict(kind='takeoff', elapsed=.5),
                                      dict(kind='window', elapsed=42)], 0)
        self.assertTrue(lines[0].startswith('[00:00.5]'))
        self.assertTrue(lines[1].startswith('[00:42.0]'))

    def test_waiting_without_data(self):
        header, lines = dashboard_rows(None, [], 0)
        self.assertIn('等待场景', header[1])
        self.assertEqual(lines, [])
