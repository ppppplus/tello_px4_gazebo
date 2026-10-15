#!/usr/bin/env python3
"""Check the distributed runtime without importing ROS or starting a master."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess
import sys


def package_dir():
    source = Path(__file__).resolve().parents[1]
    if (source / 'runtime/manifest.json').is_file():
        return source
    import rospkg
    return Path(rospkg.RosPack().get_path('tello_px4_runtime'))


def validate(root, integrity=False, libraries=False):
    release = dict(line.split('=', 1) for line in Path('/etc/os-release').read_text().splitlines()
                   if '=' in line)
    if (release.get('ID', '').strip('"') != 'ubuntu'
            or release.get('VERSION_ID', '').strip('"') != '20.04'
            or platform.machine() != 'x86_64'):
        raise RuntimeError('This runtime requires Ubuntu 20.04 x86_64, ROS Noetic and Gazebo 11. '
                           'Use the course VM on other platforms.')
    runtime = root / 'runtime'
    manifest = json.loads((runtime / 'manifest.json').read_text())
    for name, expected in manifest['files'].items():
        path = runtime / name
        if not path.is_file():
            raise RuntimeError('Missing runtime file: ' + name)
        if integrity and hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            raise RuntimeError('Runtime checksum mismatch: ' + name)
    for name, target in manifest['symlinks'].items():
        path = runtime / name
        if not path.is_symlink() or os.readlink(path) != target or not path.is_file():
            raise RuntimeError('Broken runtime symlink: ' + name)
    if not os.access(runtime / 'bin/px4', os.X_OK):
        raise RuntimeError('PX4 is not executable. Preserve Linux file permissions when extracting.')
    if libraries:
        env = dict(os.environ)
        env['LD_LIBRARY_PATH'] = str(runtime / 'lib') + ':' + env.get('LD_LIBRARY_PATH', '')
        for path in [runtime / 'bin/px4', *sorted((runtime / 'lib').glob('*.so'))]:
            result = subprocess.run(['ldd', str(path)], env=env, text=True,
                                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            missing = [line.strip() for line in result.stdout.splitlines() if 'not found' in line]
            if result.returncode or missing:
                raise RuntimeError(str(path.name) + ': ' + ('; '.join(missing) or result.stdout))
    print('Tello runtime: Ubuntu 20.04 x86_64, PX4 v1.14.3; checks passed.', flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--integrity', action='store_true')
    parser.add_argument('--libraries', action='store_true')
    args = parser.parse_args()
    try:
        validate(package_dir(), args.integrity, args.libraries)
    except (OSError, ValueError, RuntimeError) as error:
        sys.exit('Tello runtime check failed: ' + str(error))
