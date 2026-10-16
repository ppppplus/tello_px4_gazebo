"""Practice reset must refuse armed, airborne and disconnected states."""
import importlib.util
from pathlib import Path
import unittest

PATH = Path(__file__).resolve().parents[2] / 'tello_control/scripts/reset_start.py'
SPEC = importlib.util.spec_from_file_location('course_reset_start', str(PATH))
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class ResetStartTest(unittest.TestCase):
    def test_accepts_only_connected_disarmed_landed_state(self):
        MODULE.check_safe(dict(armed=False, landed_state=1, connected=True, resetting=False))

    def test_rejects_armed_airborne_missing_and_resetting_state(self):
        for state in ({}, {'armed': True, 'landed_state': 1, 'connected': True},
                      {'armed': False, 'landed_state': 2, 'connected': True},
                      {'armed': False, 'landed_state': 1, 'connected': False},
                      {'armed': False, 'landed_state': 1, 'connected': True, 'resetting': True}):
            with self.subTest(state=state), self.assertRaises(RuntimeError):
                MODULE.check_safe(state)


if __name__ == '__main__':
    unittest.main()
