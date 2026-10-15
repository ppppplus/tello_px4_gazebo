import unittest

from tello_competition.geometry import Arena, Rules
from tello_competition.rules import FlightSample, Scorekeeper


def keeper(window=1, colors='rb', lamps=(0, 4, 8)):
    return Scorekeeper(Arena(), Rules(),
                       {'round_id': 'test:1', 'seed': 1, 'active_window': window,
                        'colors': colors, 'lamp_indices': lamps})


def ready(k):
    k.update(FlightSample(0, -2.05, -2.05, 0.2))
    k.update(FlightSample(1, -2.05, -2.05, 0.65))
    k.update(FlightSample(1.6, -2.05, -2.05, 0.65))


class RuleTest(unittest.TestCase):
    def test_all_ball_combinations_and_single_submission(self):
        for first in 'rgb':
            for second in 'rgb':
                value = first + second
                score = keeper(colors=value)
                ready(score)
                self.assertEqual(score.submit(value)['score_delta'], 20)
                self.assertEqual(score.submit(value)['score_delta'], 0)

    def test_public_status_does_not_reveal_seed_or_answers(self):
        status = keeper().status()
        self.assertNotIn('seed', status)
        self.assertNotIn('colors', status)
        self.assertNotIn('active_window', status)
        self.assertNotIn('lamp_indices', status)

    def test_lamps_require_order_and_strict_distance(self):
        score = keeper()
        ready(score)
        self.assertEqual(score.submit('target2')['reason'], 'wrong_lamp_order')
        x, y, z = score.arena.lamp_position(0)
        score.update(FlightSample(2, x, y - 0.5, z))
        self.assertEqual(score.submit('target1')['reason'], 'too_far_from_lamp')
        score.update(FlightSample(3, x, y - 0.49, z))
        self.assertEqual(score.submit('target1')['progress'], 1)

    def test_correct_full_body_window_and_landing(self):
        score = keeper(window=1)
        ready(score)
        for index, y in enumerate((-0.6, -0.4, -0.2, 0, 0.2, 0.4, 0.6)):
            score.update(FlightSample(2 + index * 0.2, 0, y, 1.55))
        self.assertEqual(score.scores['window'], 20)
        score.update(FlightSample(5, 2.2, 2.2, 0.2))
        score.update(FlightSample(6.1, 2.2, 2.2, 0.2))
        self.assertEqual(score.scores['landing'], 15)

    def test_teleport_does_not_score_window(self):
        score = keeper()
        ready(score)
        score.update(FlightSample(2, 0, -0.6, 1.55))
        score.update(FlightSample(2.1, 0, 0.6, 1.55))
        self.assertEqual(score.scores['window'], 0)


if __name__ == '__main__':
    unittest.main()
