"""Regression for the actual scaled course configuration shipped to students."""
from pathlib import Path
import shlex
import subprocess
import sys
import unittest
from xml.etree import ElementTree as ET
import yaml
from tello_competition.geometry import Arena, Rules
from tello_competition.rules import FlightSample, Scorekeeper


class CourseRulesTest(unittest.TestCase):
    def setUp(self):
        config = Path(__file__).resolve().parents[1] / 'config'
        self.arena = Arena.from_dict(yaml.safe_load((config / 'tello_arena.yaml').read_text())['arena'])
        self.rules = Rules.from_dict(yaml.safe_load((config / 'tello_scaled_rules.yaml').read_text())['rules'])
        self.score = Scorekeeper(self.arena, self.rules,
                                dict(round_id='test', colors='rg', active_window=1, lamp_indices=[0, 4, 8]))
        x, y, z = self.arena.start_pose
        for t, height in [(0, z), (1, z + .4), (1.6, z + .4)]:
            self.score.update(FlightSample(t, x, y, height))

    def test_scaled_full_round(self):
        score = self.score
        self.assertEqual(score.scores['takeoff'], 15)
        self.assertEqual(score.submit('rg')['score_delta'], 20)
        for i, y in enumerate([-.3, -.2, -.1, 0, .1, .2, .3]):
            score.update(FlightSample(2 + i * .2, 0, y, self.arena.window_center_height))
        self.assertEqual(score.scores['window'], 20)
        self.assertEqual(score.submit('target2')['reason'], 'wrong_lamp_order')
        for i, lamp in enumerate([0, 4, 8]):
            x, y, z = self.arena.lamp_position(lamp)
            score.update(FlightSample(4 + i, x, y - .25, z))
            self.assertEqual(score.submit('target' + str(i + 1))['score_delta'], 10)
        x, y = self.arena.land_pad
        for t in [8, 9.1]:
            score.update(FlightSample(t, x, y, .03))
        self.assertEqual(sum(score.scores.values()), 100)
        self.assertEqual(score.phase, 'finished')

    def test_scaled_lamp_distance(self):
        x, y, z = self.arena.lamp_position(0)
        self.score.update(FlightSample(2, x, y - .276, z))
        self.assertEqual(self.score.submit('target1')['reason'], 'too_far_from_lamp')
        self.score.update(FlightSample(3, x, y - .274, z))
        self.assertEqual(self.score.submit('target1')['score_delta'], 10)

    def test_window_scoring_clearance(self):
        z = self.arena.window_center_height
        self.assertAlmostEqual(self.arena.window_width, .35)
        self.assertAlmostEqual(self.arena.window_height, .25)
        self.assertAlmostEqual(z, .82)
        for x in (-.0349, 0, .0349):
            self.assertTrue(self.score._window_clear(FlightSample(2, x, 0, z)))
        for x in (-.0351, .0351):
            self.assertFalse(self.score._window_clear(FlightSample(2, x, 0, z)))
        for dz in (-.0699, .0699):
            self.assertTrue(self.score._window_clear(FlightSample(2, 0, 0, z + dz)))
        for dz in (-.0701, .0701):
            self.assertFalse(self.score._window_clear(FlightSample(2, 0, 0, z + dz)))

    def test_world_windows_match_configuration(self):
        path = Path(__file__).resolve().parents[1] / 'worlds/tello_final.world'
        world = ET.parse(str(path)).getroot().find('world')

        def box(name):
            model = world.find("model[@name='%s']" % name)
            pose = tuple(map(float, model.findtext('pose').split()))
            visual = tuple(map(float, model.findtext('link/visual/geometry/box/size').split()))
            collision = tuple(map(float, model.findtext('link/collision/geometry/box/size').split()))
            self.assertEqual(visual, collision)
            self.assertAlmostEqual(visual[1], self.arena.wall_thickness)
            return pose, visual

        bottom, bottom_size = box('window_wall_bottom')
        top, top_size = box('window_wall_top')
        self.assertAlmostEqual(bottom[2] - bottom_size[2] / 2, 0)
        self.assertAlmostEqual(bottom[2] + bottom_size[2] / 2, self.arena.window_bottom)
        self.assertAlmostEqual(top[2] - top_size[2] / 2, self.arena.window_top)
        self.assertAlmostEqual(top[2] + top_size[2] / 2, self.arena.wall_height)
        posts = [box('window_post_%d' % i) for i in range(4)]
        for pose, size in posts:
            self.assertAlmostEqual(pose[2], self.arena.window_center_height)
            self.assertAlmostEqual(size[2], self.arena.window_height)
        for index, center in enumerate(self.arena.window_centers_x):
            left_pose, left_size = posts[index]
            right_pose, right_size = posts[index + 1]
            left = left_pose[0] + left_size[0] / 2
            right = right_pose[0] - right_size[0] / 2
            self.assertAlmostEqual(right - left, self.arena.window_width)
            self.assertAlmostEqual((left + right) / 2, center)

    def test_arena_parameters_use_whole_centimeters(self):
        for name, value in vars(self.arena).items():
            if name in ('start_yaw', 'rotation_speed_deg'):
                continue
            for component in value if isinstance(value, tuple) else (value,):
                self.assertAlmostEqual(component * 100, round(component * 100), msg=name)
        self.assertAlmostEqual(self.arena.window_bottom, .695)
        self.assertAlmostEqual(self.arena.window_top, .945)

    def test_entire_static_world_is_synchronized(self):
        tool = Path(__file__).resolve().parents[2] / 'tools/sync_world.py'
        result = subprocess.run([sys.executable, str(tool), '--check'],
                                stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        self.assertEqual(result.returncode, 0, result.stdout)

    def test_launch_spawn_matches_reset_pose(self):
        launch = Path(__file__).resolve().parents[1] / 'launch/tello.launch'
        node = ET.parse(str(launch)).getroot().find("node[@name='tello_spawn']")
        args = shlex.split(node.get('args'))
        for flag, value in zip(('-x', '-y', '-z', '-Y'), (*self.arena.start_pose, self.arena.start_yaw)):
            self.assertAlmostEqual(float(args[args.index(flag) + 1]), value)

    def test_rounded_cabinet_still_fits_ball(self):
        a = self.arena
        self.assertLess(2 * a.ball_radius, min(a.cabinet_hole_width, a.cabinet_hole_height))
        self.assertLess(a.cabinet_hole_width, a.cabinet_width)
        self.assertLess(a.cabinet_panel_thickness, a.cabinet_depth)
        self.assertGreater(a.cabinet_hole_center_height - a.cabinet_hole_height / 2, 0)
        self.assertLess(a.cabinet_hole_center_height + a.cabinet_hole_height / 2, a.cabinet_height)
