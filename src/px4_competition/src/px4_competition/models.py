"""SDF snippets for objects that change between rounds."""

from xml.etree import ElementTree as ET

BALL_COLORS = {'r': (0.95, 0.025, 0.025), 'g': (0.02, 0.72, 0.17),
               'b': (0.025, 0.16, 0.95)}


def add(parent, tag, value=None, **attrs):
    child = ET.SubElement(parent, tag, attrs)
    if value is not None:
        child.text = str(value)
    return child


def xyz(values):
    return ' '.join(f'{value:.6f}' for value in values)


def color(visual, rgb, glowing=False):
    material = add(visual, 'material')
    rgba = xyz((*rgb, 1.0))
    add(material, 'ambient', rgba)
    add(material, 'diffuse', rgba)
    add(material, 'emissive', rgba if glowing else '0 0 0 1')


def shape(link, name, kind, measurements, pose, rgb, collision=True, glowing=False):
    def geometry(parent):
        geom = add(parent, 'geometry')
        if kind == 'box':
            add(add(geom, 'box'), 'size', xyz(measurements))
        elif kind == 'sphere':
            add(add(geom, 'sphere'), 'radius', measurements[0])
        elif kind == 'cylinder':
            cylinder = add(geom, 'cylinder')
            add(cylinder, 'radius', measurements[0])
            add(cylinder, 'length', measurements[1])
        else:
            raise ValueError(kind)
    if collision:
        collision_node = add(link, 'collision', name=f'{name}_collision')
        add(collision_node, 'pose', xyz(pose))
        geometry(collision_node)
    visual = add(link, 'visual', name=f'{name}_visual')
    add(visual, 'pose', xyz(pose))
    geometry(visual)
    color(visual, rgb, glowing)


def sdf(name, content, static=True):
    root = ET.Element('sdf', version='1.6')
    model = add(root, 'model', name=name)
    add(model, 'static', 'true' if static else 'false')
    link = add(model, 'link', name='body')
    if not static:
        add(link, 'gravity', 'false')
    content(link)
    return ET.tostring(root, encoding='unicode')


def cabinet(arena, color_code, rotating):
    if color_code not in BALL_COLORS:
        raise ValueError(f'Unsupported ball color code: {color_code!r}')
    name = 'final_rotating_cabinet' if rotating else 'final_fixed_cabinet'

    def fill(link):
        wood, inside = (0.56, 0.38, 0.20), (0.17, 0.10, 0.055)
        width, depth, height = arena.cabinet_width, arena.cabinet_depth, arena.cabinet_height
        panel = arena.cabinet_panel_thickness
        lower = arena.cabinet_hole_center_height - arena.cabinet_hole_height / 2
        upper = arena.cabinet_hole_center_height + arena.cabinet_hole_height / 2
        side_width = (width - arena.cabinet_hole_width) / 2
        body_depth, body_y = depth - panel, -panel / 2
        shape(link, 'back', 'box', (width, panel, height),
              (0, depth / 2 - panel / 2, height / 2, 0, 0, 0), wood)
        shape(link, 'lower_body', 'box', (width, body_depth, lower),
              (0, body_y, lower / 2, 0, 0, 0), wood)
        shape(link, 'top', 'box', (width, body_depth, height - upper),
              (0, body_y, upper + (height - upper) / 2, 0, 0, 0), wood)
        for side, x in (('left', -(arena.cabinet_hole_width + side_width) / 2),
                        ('right', (arena.cabinet_hole_width + side_width) / 2)):
            shape(link, f'{side}_side', 'box',
                  (side_width, body_depth, arena.cabinet_hole_height),
                  (x, body_y, arena.cabinet_hole_center_height, 0, 0, 0), wood)
        shape(link, 'cavity_back', 'box',
              (arena.cabinet_hole_width, 0.004, arena.cabinet_hole_height),
              (0, depth / 2 - panel - 0.003, arena.cabinet_hole_center_height, 0, 0, 0),
              inside, collision=False)
        shape(link, 'ball', 'sphere', (arena.ball_radius,),
              (0, -depth / 2 + arena.ball_radius * 0.35,
               arena.cabinet_hole_center_height, 0, 0, 0), BALL_COLORS[color_code])

    return sdf(name, fill)


def marker(arena):
    def fill(link):
        shape(link, 'red_marker', 'cylinder', (arena.marker_radius, 0.004),
              (0, 0, 0, 1.5707963267948966, 0, 0), (0.95, 0.01, 0.01),
              collision=False, glowing=True)
    return sdf('final_window_marker', fill)


def lamp(arena, number, is_on):
    def fill(link):
        shape(link, f'lamp_{number}', 'cylinder', (arena.lamp_radius, 0.006),
              (0, 0, 0, 1.5707963267948966, 0, 0),
              (1.0, 0.02, 0.02) if is_on else (0.10, 0.12, 0.13),
              collision=False, glowing=is_on)
    return sdf(f'final_lamp_{number}', fill, static=not is_on)


def lamp_states(progress, count=3):
    return tuple(i == progress for i in range(count)) if progress < count else (False,) * count
