#!/usr/bin/env python3
"""Pinned dependencies; never reset an existing checkout or overwrite user edits."""
import argparse
import hashlib
from pathlib import Path
import subprocess
import tempfile
import urllib.request
import tarfile
import shutil

ROOT = Path(__file__).resolve().parents[1]
LOCK = dict(line.split('=', 1) for line in (ROOT/'versions.lock').read_text().splitlines() if '=' in line)
GAZEBO = 'Tools/simulation/gazebo-classic/sitl_gazebo-classic'


def git(path, *args, capture=False):
    return subprocess.run(['git', '-C', str(path), *args], check=True,
                          stdout=subprocess.PIPE if capture else None, text=True).stdout


def checkout(path, url, commit, check=False):
    if not (path/'.git').exists():
        if check or path.exists():
            raise RuntimeError('Missing or unmanaged dependency: '+str(path))
        path.parent.mkdir(parents=True, exist_ok=True)
        path.mkdir()
        git(path, 'init')
        git(path, 'remote', 'add', 'origin', url)
        git(path, 'fetch', '--depth', '1', 'origin', commit)
        git(path, 'checkout', '--detach', commit)
    if git(path, 'rev-parse', 'HEAD', capture=True).strip() != commit:
        raise RuntimeError('Unexpected revision; preserve your changes and resolve manually: '+str(path))


def patch(path, filename, check=False):
    patchfile = str(ROOT/'patches'/filename)
    reverse = subprocess.run(['git', '-C', str(path), 'apply', '--reverse', '--check', patchfile],
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if reverse.returncode == 0:
        return
    if check:
        raise RuntimeError('Required patch is missing: '+filename)
    git(path, 'apply', '--check', patchfile)
    git(path, 'apply', patchfile)


def geoid(check=False):
    target = ROOT/'geographiclib/geoids/egm96-5.pgm'
    expected = LOCK['GEOGRAPHICLIB_EGM96_5_PGM_SHA256']
    if target.exists():
        if hashlib.sha256(target.read_bytes()).hexdigest() != expected:
            raise RuntimeError('Existing geoid checksum mismatch; refusing overwrite')
        return
    if check:
        raise RuntimeError('Missing EGM96-5 geoid data')
    url = 'https://downloads.sourceforge.net/project/geographiclib/geoids-distrib/egm96-5.tar.bz2'
    with tempfile.TemporaryDirectory(prefix='tello-geoid-') as temp:
        archive = Path(temp)/'geoid.tar.bz2'
        with urllib.request.urlopen(url, timeout=90) as response, archive.open('wb') as stream:
            shutil.copyfileobj(response, stream)
        with tarfile.open(archive) as tar:
            # Extract only the expected regular file, never arbitrary archive paths.
            members = [m for m in tar.getmembers() if m.isfile() and Path(m.name).name == 'egm96-5.pgm']
            if len(members) != 1:
                raise RuntimeError('Unexpected geoid archive layout')
            data = tar.extractfile(members[0]).read()
        if hashlib.sha256(data).hexdigest() != expected:
            raise RuntimeError('Downloaded geoid checksum mismatch')
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--check', action='store_true', help='read-only/offline validation')
    args = parser.parse_args()
    px4 = ROOT/'vendor/PX4-Autopilot'
    repos = [(px4, 'https://github.com/PX4/PX4-Autopilot.git', LOCK['PX4_COMMIT']),
             (ROOT/'src/mavros', 'https://github.com/mavlink/mavros.git', LOCK['MAVROS_COMMIT']),
             (ROOT/'src/mavlink', 'https://github.com/mavlink/mavlink-gbp-release.git', LOCK['MAVLINK_ROS_COMMIT'])]
    for path, url, commit in repos:
        checkout(path, url, commit, args.check)
        if not args.check:
            # Only initialize missing modules; do not reset populated user modules.
            status = git(path, 'submodule', 'status', '--recursive', capture=True)
            missing = [line.split()[1] for line in status.splitlines() if line.startswith('-')]
            for module in missing:
                git(path, 'submodule', 'update', '--init', '--recursive', '--', module)
    gazebo = px4/GAZEBO
    if git(gazebo, 'rev-parse', 'HEAD', capture=True).strip() != LOCK['PX4_GAZEBO_CLASSIC_COMMIT']:
        raise RuntimeError('Gazebo plugin revision mismatch')
    patch(px4, 'px4-no-gstreamer.patch', args.check)
    patch(gazebo, 'gazebo-qt.patch', args.check)
    if not args.check and subprocess.run(['git', '-C', str(px4), 'rev-parse', '--verify', 'refs/tags/'+LOCK['PX4_TAG']],
                                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode:
        git(px4, 'fetch', '--depth', '1', 'origin', 'tag', LOCK['PX4_TAG'])
    geoid(args.check)
    print('Pinned source revisions, compatibility patches and EGM96-5: OK')


if __name__ == '__main__':
    main()
