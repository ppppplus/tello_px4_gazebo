import unittest
from xml.etree import ElementTree as ET

from tello_competition import models
from tello_competition.geometry import Arena


class ModelTest(unittest.TestCase):
    def test_three_ball_colors_are_distinct(self):
        colors = set()
        for code in 'rgb':
            root = ET.fromstring(models.cabinet(Arena(), code, False))
            colors.add(root.find(".//visual[@name='ball_visual']/material/diffuse").text)
        self.assertEqual(len(colors), 3)

    def test_cabinet_contains_real_recess(self):
        root = ET.fromstring(models.cabinet(Arena(), 'r', False))
        names = {node.attrib['name'] for node in root.findall('.//link/visual')}
        self.assertIn('cavity_back_visual', names)
        self.assertIn('ball_visual', names)

    def test_lamp_sequence(self):
        self.assertEqual(models.lamp_states(0), (True, False, False))
        self.assertEqual(models.lamp_states(1), (False, True, False))
        self.assertEqual(models.lamp_states(3), (False, False, False))
        lit = ET.fromstring(models.lamp(Arena(), 1, True))
        self.assertEqual(lit.find('.//model/static').text, 'false')


if __name__ == '__main__':
    unittest.main()
