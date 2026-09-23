#!/usr/bin/env python3
"""Non-mutating host/build/render diagnostics. Does not start or stop simulations."""
import argparse
import importlib.util
import os
from pathlib import Path
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parents[1]


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--build-only', action='store_true')
    args=parser.parse_args()
    failures=[]
    def check(label, passed, hint=''):
        print(('OK   ' if passed else 'FAIL ')+label+(' — '+hint if not passed else ''))
        if not passed: failures.append(label)
    release=Path('/etc/os-release').read_text()
    check('Ubuntu 20.04 x86_64', 'VERSION_ID="20.04"' in release and os.uname().machine=='x86_64')
    for command in ('git','cmake','ninja','gz','roslaunch'):
        check(command, shutil.which(command) is not None, 'Install system packages; source /opt/ros/noetic/setup.bash')
    for module in ('numpy','yaml','cv2'):
        check('Python '+module, importlib.util.find_spec(module) is not None)
    check('ROS Noetic', Path('/opt/ros/noetic/setup.bash').is_file())
    check('ROS workspace', (ROOT/'devel_isolated/setup.bash').is_file(), 'Run ./setup.sh')
    px4=ROOT/'vendor/PX4-Autopilot/build/px4_sitl_default'
    check('PX4 SITL', os.access(px4/'bin/px4', os.X_OK))
    for name in ('libgazebo_mavlink_interface.so','libgazebo_motor_model.so','libgazebo_imu_plugin.so','libgazebo_gps_plugin.so'):
        file=px4/'build_gazebo-classic'/name
        check(name, file.is_file())
        if file.is_file():
            env=dict(os.environ,LD_LIBRARY_PATH=str(file.parent)+':/opt/ros/noetic/lib:'+os.environ.get('LD_LIBRARY_PATH',''))
            result=subprocess.run(['ldd',str(file)],env=env,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
            check(name+' dependencies', result.returncode==0 and 'not found' not in result.stdout)
    model=ROOT/'src/px4_competition/models/tello_training/model_camera.sdf'
    check('Distributable model',model.is_file() and not ET.parse(model).findall('.//mesh'))
    deps=subprocess.run([sys.executable,str(ROOT/'scripts/fetch_dependencies.py'),'--check'])
    check('Pinned sources/patches/geoid',deps.returncode==0)
    if not args.build_only:
        display=os.environ.get('DISPLAY')
        check('DISPLAY',bool(display),'Run in an active desktop session')
        if display and shutil.which('xdpyinfo'):
            connection=subprocess.run(['xdpyinfo'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=10)
            check('Desktop access',connection.returncode==0,'Check XAUTHORITY / desktop access')
        print('NOTE Desktop access does not prove OpenGL camera rendering; run the native-camera smoke test.')
    for name in ('px4','gzserver','rosmaster'):
        if subprocess.run(['pgrep','-x',name],stdout=subprocess.DEVNULL).returncode==0:
            print('WARN '+name+' is running; stop the other simulation normally before ./run.sh')
    return bool(failures)


if __name__=='__main__':
    sys.exit(main())
