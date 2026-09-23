"""Offline student-release contracts; no private mesh or old workspace required."""
import copy
import importlib.util
import math
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET
from unittest.mock import patch
import yaml

ROOT=Path(__file__).resolve().parents[2]
PKG=ROOT/'src/px4_competition'
sys.path.insert(0,str(PKG/'src'))
from px4_competition.geometry import Arena, Rules
from px4_competition.rules import FlightSample, Scorekeeper
import build_training_model as builder
sys.path.insert(0,str(ROOT/'scripts'))
import fetch_dependencies as fetch


class ReleaseTest(unittest.TestCase):
    def test_original_primitive_visuals_only(self):
        for filename in ('model.sdf','model_camera.sdf'):
            root=ET.parse(PKG/'models/tello_training'/filename)
            self.assertFalse(root.findall('.//mesh'))
            self.assertFalse(root.findall('.//uri'))
            self.assertGreater(len(root.findall('.//visual')),80)
            self.assertTrue(all(v.find('material/diffuse') is not None for v in root.findall('.//visual')))

    def test_appearance_preserves_dynamics(self):
        expected=ET.parse(ROOT/'tools/tello/training_dynamics.sdf').getroot()
        with tempfile.TemporaryDirectory() as temp, patch.object(builder,'MODEL',Path(temp)):
            for camera in (False,True):
                result=ET.parse(builder.build(camera)).getroot()
                for link in result.findall('model/link'):
                    for visual in link.findall('visual'): link.remove(visual)
                    for sensor in link.findall('sensor[@type="camera"]'): link.remove(sensor)
                self.assertEqual(ET.tostring(result),ET.tostring(expected))

    def test_mass_and_camera(self):
        root=ET.parse(PKG/'models/tello_training/model_camera.sdf')
        self.assertAlmostEqual(sum(float(x.text) for x in root.findall('.//inertial/mass')),.085)
        c=root.find('.//sensor[@type="camera"]')
        self.assertEqual(c.findtext('update_rate'),'20')
        self.assertEqual(c.findtext('camera/image/width'),'320')
        self.assertEqual(c.findtext('camera/image/height'),'240')
        self.assertEqual(len(root.findall('model/plugin[@filename="libgazebo_motor_model.so"]')),4)

    def test_scaled_final_full_score(self):
        a=Arena.from_dict(yaml.safe_load((PKG/'config/tello_arena.yaml').read_text())['arena'])
        r=Rules.from_dict(yaml.safe_load((PKG/'config/tello_scaled_rules.yaml').read_text())['rules'])
        self.assertAlmostEqual(a.size,2.75)
        self.assertAlmostEqual(r.lamp_distance,.275)
        k=Scorekeeper(a,r,dict(round_id='test',colors='gb',active_window=1,lamp_indices=[0,4,8]))
        for t,z in ((0,.02),(1,.48),(2,.48)): k.update(FlightSample(t,*a.start_pad,z))
        self.assertEqual(k.submit('gb')['score_delta'],20)
        self.assertFalse(k.submit('gb')['accepted'])
        for i,y in enumerate((-.4,-.2,-.1,0,.1,.2,.4)): k.update(FlightSample(3+i*.1,0,y,a.window_center_height))
        self.assertEqual(k.scores['window'],20)
        self.assertFalse(k.submit('target2')['accepted'])
        for stage,index in enumerate((0,4,8),1):
            x,y,z=a.lamp_position(index)
            k.update(FlightSample(4+stage,x,y-.30,z))
            self.assertFalse(k.submit('target'+str(stage))['accepted'])
            k.update(FlightSample(4+stage+.1,x,y-.20,z))
            self.assertTrue(k.submit('target'+str(stage))['accepted'])
        for t in (9,10.1): k.update(FlightSample(t,*a.land_pad,.02))
        self.assertEqual(k.score,100)

    def test_student_starter_has_no_private_inputs(self):
        import ast
        source=ast.parse((ROOT/'src/student_solution/scripts/student_node.py').read_text())
        strings=[n.value for n in ast.walk(source) if isinstance(n,ast.Constant) and isinstance(n.value,str)]
        self.assertFalse(any(s.startswith(('/teacher/','/mavros/','/gazebo/')) for s in strings))

    def test_docs_match_runtime(self):
        docs=(ROOT/'docs/student_api.md').read_text()
        for text in ('0.275 m','0.04 m','0.35 m/s','0.8 rad/s','20 Hz'):
            self.assertIn(text,docs)
        self.assertIn('models/tello_training/',(PKG/'launch/tello.launch').read_text())

    def test_cpu_camera_uses_importable_package(self):
        source=(PKG/'scripts/tello_software_camera.py').read_text()
        self.assertIn('from px4_competition.software_camera import SoftwareCamera',source)
        self.assertTrue((PKG/'src/px4_competition/software_camera.py').is_file())

    def test_dependency_checkout_refuses_unmanaged_directory(self):
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)
            sentinel=path/'student_work.txt'
            sentinel.write_text('keep me')
            with self.assertRaises(RuntimeError):
                fetch.checkout(path,'unused-url','0'*40)
            self.assertEqual(sentinel.read_text(),'keep me')

    def test_corrupt_geoid_is_not_overwritten(self):
        with tempfile.TemporaryDirectory() as temp, patch.object(fetch,'ROOT',Path(temp)):
            target=Path(temp)/'geographiclib/geoids/egm96-5.pgm'
            target.parent.mkdir(parents=True)
            target.write_bytes(b'preserve unexpected data')
            with self.assertRaises(RuntimeError): fetch.geoid()
            self.assertEqual(target.read_bytes(),b'preserve unexpected data')

    def test_patch_is_idempotent(self):
        with tempfile.TemporaryDirectory() as temp, patch.object(fetch,'ROOT',Path(temp)):
            root=Path(temp)
            repo=root/'repo'
            repo.mkdir()
            subprocess.run(['git','init','-q',str(repo)],check=True)
            (repo/'a').write_text('before\n')
            (root/'patches').mkdir()
            (root/'patches/test.patch').write_text('diff --git a/a b/a\n--- a/a\n+++ b/a\n@@ -1 +1 @@\n-before\n+after\n')
            fetch.patch(repo,'test.patch')
            fetch.patch(repo,'test.patch')
            fetch.patch(repo,'test.patch',check=True)
            self.assertEqual((repo/'a').read_text(),'after\n')

    def test_published_files_exclude_private_assets_and_gitlinks(self):
        if not (ROOT/'.git').exists(): self.skipTest('export without git index')
        out=subprocess.check_output(['git','-C',str(ROOT),'ls-files','--stage'],text=True)
        self.assertNotIn('160000 ',out)
        for line in out.splitlines():
            path=line.split('\t')[-1]
            self.assertFalse(path.startswith(('vendor/','build','devel','artifacts/','src/mavros/','src/mavlink/')))
            self.assertNotIn('models/tello_competition/',path)
            self.assertNotIn('fly_scaled_final.py',path)


if __name__=='__main__': unittest.main(verbosity=2)
