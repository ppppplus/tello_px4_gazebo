#!/usr/bin/env python3
"""Start PX4 with fresh parameters and ROMFS in a private per-launch directory."""
import fcntl
import os
from pathlib import Path
import shutil
import socket
import sys
import tempfile
import rospkg


def main():
    package = Path(rospkg.RosPack().get_path('tello_px4_runtime'))
    runtime = package / 'runtime'
    state = Path(os.environ.get('ROS_HOME', str(Path.home() / '.ros'))) / 'tello_sim'
    state.mkdir(parents=True, exist_ok=True)
    lock = (state / 'sitl.lock').open('a+')
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        sys.exit('Another tello_sim instance is running. Stop its roslaunch first.')
    os.set_inheritable(lock.fileno(), True)
    with socket.socket() as probe:
        probe.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            probe.bind(('127.0.0.1', 4560))
        except OSError:
            sys.exit('PX4 simulator port 4560 is occupied. Stop the previous simulation first.')
    run = Path(tempfile.mkdtemp(prefix='run-', dir=str(state)))
    shutil.copytree(runtime / 'etc', run / 'etc')
    for airframe in (package / 'airframes').iterdir():
        shutil.copy2(airframe, run / 'etc/init.d-posix/airframes' / airframe.name)
    env = dict(os.environ)
    env['PX4_SIM_MODEL'] = 'gazebo-classic_tello'
    env['PATH'] = str(runtime / 'bin') + ':' + env.get('PATH', '')
    print('Tello PX4 parameters/logs: ' + str(run), flush=True)
    os.chdir(run)
    os.execve(str(runtime / 'bin/px4'),
              ['px4', str(run / 'etc'), '-w', str(run), '-s', 'etc/init.d-posix/rcS', '-d'], env)


if __name__ == '__main__':
    main()
