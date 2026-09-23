#!/usr/bin/env python3
"""Generate the static Gazebo Classic world from arena.yaml."""

import sys
from pathlib import Path
from xml.dom import minidom
from xml.etree import ElementTree as ET

import yaml

PACKAGE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PACKAGE / 'src'))
from px4_competition.geometry import Arena  # noqa: E402


def sub(parent, tag, value=None, **attributes):
    element = ET.SubElement(parent, tag, attributes)
    if value is not None:
        element.text = str(value)
    return element


def vector(values):
    return ' '.join(f'{value:.6f}' for value in values)


def material(parent, rgb, alpha=1.0):
    node = sub(parent, 'material')
    rgba = vector((*rgb, alpha))
    sub(node, 'ambient', rgba)
    sub(node, 'diffuse', rgba)


def box(world, name, position, size, rgb, collision=True, transparency=0.0):
    model = sub(world, 'model', name=name)
    sub(model, 'static', 'true')
    sub(model, 'pose', vector((*position, 0, 0, 0)))
    link = sub(model, 'link', name='body')
    if collision:
        collision_node = sub(link, 'collision', name='collision')
        sub(sub(sub(collision_node, 'geometry'), 'box'), 'size', vector(size))
    visual = sub(link, 'visual', name='visual')
    sub(sub(sub(visual, 'geometry'), 'box'), 'size', vector(size))
    if transparency:
        sub(visual, 'transparency', transparency)
    material(visual, rgb, 1.0 - transparency)


def disc(world, name, position, radius, rgb):
    model = sub(world, 'model', name=name)
    sub(model, 'static', 'true')
    sub(model, 'pose', vector((*position, 1.57079632679, 0, 0)))
    link = sub(model, 'link', name='body')
    visual = sub(link, 'visual', name='visual')
    cylinder = sub(sub(visual, 'geometry'), 'cylinder')
    sub(cylinder, 'radius', radius)
    sub(cylinder, 'length', 0.002)
    material(visual, rgb)


def generate(arena):
    root = ET.Element('sdf', version='1.6')
    world = sub(root, 'world', name='final_arena')
    sub(world, 'gravity', '0 0 -9.80665')
    physics = sub(world, 'physics', name='ode', type='ode')
    sub(physics, 'max_step_size', 0.001)
    sub(physics, 'real_time_update_rate', 1000)
    sun = sub(world, 'include')
    sub(sun, 'uri', 'model://sun')
    box(world, 'floor', (0, 0, -0.025), (arena.size, arena.size, 0.05),
        (0.84, 0.86, 0.85))
    thickness, height = arena.boundary_wall_thickness, arena.boundary_wall_height
    span, offset = arena.size + thickness, arena.size / 2 + thickness / 2
    for name, position, size in (
            ('boundary_south', (0, -offset, height / 2), (span, thickness, height)),
            ('boundary_north', (0, offset, height / 2), (span, thickness, height)),
            ('boundary_west', (-offset, 0, height / 2), (thickness, span, height)),
            ('boundary_east', (offset, 0, height / 2), (thickness, span, height))):
        box(world, name, position, size, (0.58, 0.61, 0.63), transparency=0.45)
    for name, center, color in (
            ('takeoff', arena.start_pad, (0.19, 0.48, 0.82)),
            ('landing', arena.land_pad, (0.15, 0.69, 0.48))):
        box(world, f'{name}_pad', (*center, 0.001),
            (arena.pad_size, arena.pad_size, 0.002), color, collision=False)
    half_wall, wall_color = arena.wall_length / 2, (0.93, 0.93, 0.91)
    box(world, 'window_wall_bottom', (0, 0, arena.window_bottom / 2),
        (arena.wall_length, arena.wall_thickness, arena.window_bottom), wall_color)
    top_height = arena.wall_height - arena.window_top
    box(world, 'window_wall_top', (0, 0, arena.window_top + top_height / 2),
        (arena.wall_length, arena.wall_thickness, top_height), wall_color)
    edges = [-half_wall]
    for center in arena.window_centers_x:
        edges.extend((center - arena.window_width / 2, center + arena.window_width / 2))
    edges.append(half_wall)
    for index in range(0, len(edges), 2):
        left, right = edges[index], edges[index + 1]
        if right <= left:
            raise ValueError('Window bays overlap or escape the wall')
        box(world, f'window_post_{index // 2}',
            ((left + right) / 2, 0, arena.window_center_height),
            (right - left, arena.wall_thickness, arena.window_height), wall_color)
    board_z = arena.board_top - arena.board_height / 2
    box(world, 'whiteboard', (0, arena.board_y, board_z),
        (arena.board_width, 0.03, arena.board_height), (0.96, 0.96, 0.94))
    for x in (-0.75, 0.75):
        box(world, f'board_leg_{x}',
            (x, arena.board_y, (arena.board_top - arena.board_height) / 2),
            (0.03, 0.03, arena.board_top - arena.board_height), (0.22, 0.25, 0.29))
    for index in range(9):
        x, y, z = arena.lamp_position(index)
        disc(world, f'lamp_socket_{index}', (x, y + 0.008, z),
             arena.lamp_radius * 1.5, (0.25, 0.27, 0.29))
    return minidom.parseString(ET.tostring(root)).toprettyxml(indent='  ')


if __name__ == '__main__':
    with (PACKAGE / 'config' / 'arena.yaml').open(encoding='utf-8') as stream:
        arena_config = Arena.from_dict(yaml.safe_load(stream)['arena'])
    target = PACKAGE / 'worlds' / 'final.world'
    target.parent.mkdir(exist_ok=True)
    target.write_text(generate(arena_config), encoding='utf-8')
    print(target)
