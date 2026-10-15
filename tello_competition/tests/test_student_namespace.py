"""Public namespace regression checks, independent of a running ROS master."""
import ast
from pathlib import Path
import shlex
import unittest
from xml.etree import ElementTree as ET

PACKAGE = Path(__file__).resolve().parents[1]
COURSE = PACKAGE.parent


def strings(path):
    return {node.value for node in ast.walk(ast.parse(path.read_text()))
            if isinstance(node, ast.Constant) and isinstance(node.value, str)}


class StudentNamespaceTest(unittest.TestCase):
    def test_package_names_and_dependencies(self):
        control = COURSE / 'tello_control'
        self.assertEqual(ET.parse(str(PACKAGE / 'package.xml')).findtext('name'),
                         'tello_competition')
        self.assertEqual(ET.parse(str(control / 'package.xml')).findtext('name'),
                         'tello_control')
        self.assertIn('tello_competition', [item.text for item in
                      ET.parse(str(control / 'package.xml')).findall('depend')])
        self.assertTrue((PACKAGE / 'src/tello_competition/__init__.py').is_file())
        self.assertIn('project(tello_competition)', (PACKAGE / 'CMakeLists.txt').read_text())
        self.assertIn('project(tello_control)', (control / 'CMakeLists.txt').read_text())
        for path in COURSE.rglob('*'):
            if path.is_file() and path.suffix in ('.py', '.xml', '.launch', '.md', '.txt'):
                contents = path.read_text()
                self.assertNotIn('px4_' + 'competition', contents, str(path))
                self.assertNotIn('student_' + 'solution', contents, str(path))

    def test_bridge_and_student_agree(self):
        bridge = strings(PACKAGE / 'scripts/student_bridge.py')
        student = strings(COURSE / 'tello_control/scripts/demo.py')
        for topic in ('cmd_vel', 'state', 'takeoff', 'land'):
            name = '/tello/' + topic
            self.assertIn(name, bridge)
            self.assertIn(name, student)
        self.assertIn('/tello/judge', student)
        self.assertIn('/tello/pose', student)
        self.assertIn('/tello/pose', strings(PACKAGE / 'scripts/gazebo_truth.py'))
        self.assertIn('/tello/cmd_vel', strings(PACKAGE / 'scripts/final_scene.py'))
        launch = ET.parse(str(PACKAGE / 'launch/tello.launch')).getroot()
        self.assertEqual(launch.find("param[@name='/final/drone_name']").get('value'), 'tello')

    def test_native_camera_and_tf_agree(self):
        model = ET.parse(str(PACKAGE / 'models/tello_training/model_camera.sdf'))
        camera = model.find(".//plugin[@name='front_camera_ros']")
        self.assertEqual(camera.findtext('cameraName'), '/tello/front_cam/camera')
        self.assertEqual(camera.findtext('imageTopicName'), 'image')
        self.assertEqual(camera.findtext('cameraInfoTopicName'), 'camera_info')
        self.assertEqual(camera.findtext('frameName'), 'tello/front_camera_optical')
        launch = ET.parse(str(PACKAGE / 'launch/tello.launch')).getroot()
        tf_args = shlex.split(launch.find("node[@name='tello_camera_tf']").get('args'))
        self.assertEqual(tf_args[6:8], ['tello/base_link', 'tello/front_camera_optical'])
        self.assertIn('tello/base_link', strings(PACKAGE / 'scripts/student_bridge.py'))

    def test_all_camera_consumers_use_tello_namespace(self):
        consumers = [COURSE / 'tello_control/scripts/demo.py']
        consumers += [PACKAGE / 'scripts/camera_preview.py']
        for path in consumers:
            self.assertIn('/tello/front_cam/camera/image', strings(path), str(path))

    def test_no_legacy_public_names_in_code_or_docs(self):
        paths = list((PACKAGE / 'scripts').glob('*.py'))
        paths += list((COURSE / 'tello_control/scripts').glob('*.py'))
        paths += list((COURSE / 'docs').glob('*.md')) + [COURSE / 'README.md']
        for path in paths:
            text = path.read_text()
            self.assertNotIn('/quad' + 'rotor/', text, str(path))
            self.assertNotIn('/front_cam/', text.replace('/tello/front_cam/', ''), str(path))


if __name__ == '__main__':
    unittest.main()
