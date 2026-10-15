#!/usr/bin/env python3
"""Synchronize shipped static geometry with tello_arena.yaml; preserve materials."""
import argparse
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
import sys
from xml.etree import ElementTree as ET

import yaml

PACKAGE = Path(__file__).resolve().parents[1] / 'tello_competition'
sys.path.insert(0, str(PACKAGE / 'src'))
from tello_competition.geometry import Arena


def vector(values):
    return ' '.join('%.6f' % value for value in values)


def sync(root, arena):
    world = root.find('world')

    def box(name, position, size):
        model = world.find("model[@name='%s']" % name)
        if model is None:
            raise ValueError('Missing model: ' + name)
        model.find('pose').text = vector((*position, 0, 0, 0))
        for node in model.findall('.//geometry/box/size'):
            node.text = vector(size)

    box('floor', (0, 0, -.025), (arena.size, arena.size, .05))
    thickness, height = arena.boundary_wall_thickness, arena.boundary_wall_height
    span, offset = arena.size + thickness, (arena.size + thickness) / 2
    for name, position, size in (
        ('boundary_south', (0, -offset, height / 2), (span, thickness, height)),
        ('boundary_north', (0, offset, height / 2), (span, thickness, height)),
        ('boundary_west', (-offset, 0, height / 2), (thickness, span, height)),
        ('boundary_east', (offset, 0, height / 2), (thickness, span, height)),
    ):
        box(name, position, size)
    for name, center in [('takeoff_pad', arena.start_pad), ('landing_pad', arena.land_pad)]:
        box(name, (*center, .001), (arena.pad_size, arena.pad_size, .002))
    box('window_wall_bottom', (0, 0, arena.window_bottom / 2),
        (arena.wall_length, arena.wall_thickness, arena.window_bottom))
    box('window_wall_top', (0, 0, (arena.window_top + arena.wall_height) / 2),
        (arena.wall_length, arena.wall_thickness, arena.wall_height - arena.window_top))
    edges = [-arena.wall_length / 2]
    for center in arena.window_centers_x:
        edges.extend([center - arena.window_width / 2, center + arena.window_width / 2])
    edges.append(arena.wall_length / 2)
    for index in range(4):
        left, right = edges[2 * index:2 * index + 2]
        if right <= left:
            raise ValueError('Windows overlap or extend beyond the wall')
        box('window_post_%d' % index, ((left + right) / 2, 0, arena.window_center_height),
            (right - left, arena.wall_thickness, arena.window_height))
    box('whiteboard', (0, arena.board_y, arena.board_top - arena.board_height / 2),
        (arena.board_width, .03, arena.board_height))
    # Preserve the original 3/8-board-width support placement, rounded to cm.
    leg_x = float(Decimal(str(arena.board_width * 3 / 8)).quantize(Decimal('.01'), rounding=ROUND_HALF_UP))
    leg_height = arena.board_top - arena.board_height
    for name, x in [('board_leg_-0.75', -leg_x), ('board_leg_0.75', leg_x)]:
        box(name, (x, arena.board_y, leg_height / 2), (.03, .03, leg_height))
    for index in range(9):
        model = world.find("model[@name='lamp_socket_%d']" % index)
        x, y, z = arena.lamp_position(index)
        model.find('pose').text = vector((x, y + .008, z, 1.57079632679, 0, 0))
        model.find('.//cylinder/radius').text = '%.6f' % (arena.lamp_radius * 1.5)
    return root


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true', help='Fail if committed world is stale; do not write')
    args = parser.parse_args()
    arena = Arena.from_dict(yaml.safe_load((PACKAGE / 'config/tello_arena.yaml').read_text())['arena'])
    path = PACKAGE / 'worlds/tello_final.world'
    root = ET.parse(str(path)).getroot()
    before = ET.tostring(root)
    sync(root, arena)
    if args.check:
        if ET.tostring(root) != before:
            raise SystemExit('World is stale. Run tools/sync_world.py.')
        print('World geometry matches arena configuration.')
    else:
        ET.ElementTree(root).write(str(path), encoding='utf-8', xml_declaration=True)
        print(path)


if __name__ == '__main__':
    main()
