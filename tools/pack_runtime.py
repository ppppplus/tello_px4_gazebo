#!/usr/bin/env python3
"""Teacher tool: package an existing pinned PX4 build; never alter that build."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / 'tello_px4_runtime'
LOCK = dict(line.split('=', 1) for line in (PACKAGE / 'versions.lock').read_text().splitlines())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--px4-source', type=Path, required=True)
    parser.add_argument('--geoid', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True, help='New or empty destination')
    args = parser.parse_args()
    source, output = args.px4_source.resolve(), args.output.resolve()
    gazebo = source / 'Tools/simulation/gazebo-classic/sitl_gazebo-classic'
    for repo, key in [(source, 'PX4_COMMIT'), (gazebo, 'PX4_GAZEBO_CLASSIC_COMMIT')]:
        revision = subprocess.check_output(['git', '-C', str(repo), 'rev-parse', 'HEAD'], text=True).strip()
        if revision != LOCK[key]:
            raise RuntimeError('Unexpected source revision: ' + str(repo))
    if output.exists() and any(output.iterdir()):
        raise RuntimeError('Output must be new or empty; existing data will not be overwritten')
    if hashlib.sha256(args.geoid.read_bytes()).hexdigest() != LOCK['GEOGRAPHICLIB_EGM96_5_PGM_SHA256']:
        raise RuntimeError('Unexpected EGM96-5 geoid checksum')
    build = source / 'build/px4_sitl_default'
    output.mkdir(parents=True, exist_ok=True)
    shutil.copytree(build / 'bin', output / 'bin', symlinks=True)
    shutil.copytree(build / 'etc', output / 'etc', symlinks=False)
    (output / 'lib').mkdir()
    model = ET.parse(ROOT / 'tello_competition/models/tello_training/model_camera.sdf')
    required = {p.attrib['filename'] for p in model.findall('.//plugin')
                if not p.attrib['filename'].startswith('libgazebo_ros_')}
    # Transitive protobuf message libraries used by the Gazebo plugins.
    required.update(['libmav_msgs.so', 'libnav_msgs.so', 'libsensor_msgs.so',
                     'libphysics_msgs.so', 'libstd_msgs.so'])
    for name in sorted(required):
        shutil.copy2(build / 'build_gazebo-classic' / name, output / 'lib' / name)
    for binary in [output / 'bin/px4', *sorted((output / 'lib').glob('*.so'))]:
        subprocess.run(['strip', '--strip-unneeded', str(binary)], check=True)
        subprocess.run(['cmake', '-DBINARY=' + str(binary), '-P',
                        str(ROOT / 'tools/remove_rpath.cmake')], check=True)
    geoid_dir = output / 'geographiclib/geoids'
    geoid_dir.mkdir(parents=True)
    shutil.copy2(args.geoid, geoid_dir / 'egm96-5.pgm')
    # Keep all upstream source/header notices from the plugin tree for binary redistribution.
    notices = []
    for folder in ['src', 'include', 'msgs']:
        for path in sorted((gazebo / folder).rglob('*')):
            if not path.is_file():
                continue
            content = path.read_text(errors='replace')
            if content.startswith('/*') and '*/' in content:
                notices.append(str(path.relative_to(gazebo)) + '\n' + content.split('*/', 1)[0] + '*/\n')
    (output / 'GAZEBO_NOTICES.txt').write_text('\n'.join(notices))
    shutil.copy2(source / 'LICENSE', output / 'PX4_LICENSE.txt')
    manifest = {'platform': 'ubuntu-20.04-x86_64', 'px4_commit': LOCK['PX4_COMMIT'],
                'gazebo_commit': LOCK['PX4_GAZEBO_CLASSIC_COMMIT'], 'files': {}, 'symlinks': {}}
    for path in sorted(output.rglob('*')):
        name = str(path.relative_to(output))
        if path.is_symlink():
            target = os.readlink(path)
            if Path(target).is_absolute() or output not in path.resolve().parents:
                raise RuntimeError('Non-relocatable symlink: ' + name)
            manifest['symlinks'][name] = target
        elif path.is_file():
            manifest['files'][name] = hashlib.sha256(path.read_bytes()).hexdigest()
    (output / 'manifest.json').write_text(json.dumps(manifest, indent=2, sort_keys=True) + '\n')
    print('Runtime packed at ' + str(output))


if __name__ == '__main__':
    main()
