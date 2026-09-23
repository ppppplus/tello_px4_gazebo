#!/usr/bin/env python3
"""Original primitive-based appearance; no third-party mesh is read or copied."""
import math
from pathlib import Path
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
MODEL = ROOT/'src/px4_competition/models/tello_training'
ROTORS = ((.0425,-.05,.0183182),(-.0425,.05,.0183182),(.0425,.05,.0183182),(-.0425,-.05,.0183182))
BLACK = '.025 .028 .032 1'
WHITE = '.88 .89 .90 1'


def put(parent, path, value):
    node = parent
    for tag in path.split('/'):
        child = node.find(tag)
        if child is None:
            child = ET.SubElement(node, tag)
        node = child
    node.text = str(value)
    return node


def box(link, name, position, size, color, yaw=0):
    v = ET.SubElement(link, 'visual', name=name)
    put(v, 'pose', ' '.join(map(str, (*position,0,0,yaw))))
    put(v, 'geometry/box/size', ' '.join(map(str, size)))
    put(v, 'material/ambient', color)
    put(v, 'material/diffuse', color)


def cylinder(link, name, position, radius, length, color, pitch=0):
    v = ET.SubElement(link, 'visual', name=name)
    put(v, 'pose', ' '.join(map(str, (*position,0,pitch,0))))
    put(v, 'geometry/cylinder/radius', radius)
    put(v, 'geometry/cylinder/length', length)
    put(v, 'material/ambient', color)
    put(v, 'material/diffuse', color)


def build(camera):
    root = ET.parse(Path(__file__).with_name('training_dynamics.sdf')).getroot()
    m = root.find('model')
    base = m.find("link[@name='base_link']")
    box(base, 'body', (0,0,-.004), (.071,.041,.029), BLACK)
    box(base, 'white_cover', (0,0,.012), (.071,.043,.006), WHITE)
    cylinder(base, 'front_lens', (.036,0,.005), .004,.002,BLACK,math.pi/2)
    for i,(x,y,z) in enumerate(ROTORS):
        box(base, 'arm_'+str(i), (x/2,y/2,.002), (math.hypot(x,y),.007,.006), BLACK, math.atan2(y,x))
        cylinder(base, 'motor_'+str(i), (x,y,.009), .008,.022,'.30 .32 .34 1')
        cylinder(base, 'foot_'+str(i), (x,y,-.009), .005,.022,BLACK)
        # Open outward-facing guard, within the existing 46.5 mm collision radius.
        start = math.atan2(y,x)-math.pi*.65
        for j in range(20):
            a,b = start+j*math.pi*1.3/20, start+(j+1)*math.pi*1.3/20
            x1,y1 = x+.0445*math.cos(a),y+.0445*math.sin(a)
            x2,y2 = x+.0445*math.cos(b),y+.0445*math.sin(b)
            box(base,f'guard_{i}_{j}',((x1+x2)/2,(y1+y2)/2,.018),
                (math.hypot(x2-x1,y2-y1)+.001,.003,.009),BLACK,math.atan2(y2-y1,x2-x1))
        rotor=m.find("link[@name='rotor_%d']"%i)
        box(rotor,'propeller',(0,0,0),(.0762,.007,.0018),BLACK,yaw=i*.7)
        cylinder(rotor,'hub',(0,0,0),.004,.004,BLACK)
    if camera:
        sensor=ET.SubElement(base,'sensor',name='front_camera',type='camera')
        for path,value in {'pose':'.036 0 .005 0 0 0','always_on':'true','update_rate':20,
            'camera/horizontal_fov':1.0471975512,'camera/image/width':320,'camera/image/height':240,
            'camera/image/format':'R8G8B8','camera/clip/near':.01,'camera/clip/far':30}.items():
            put(sensor,path,value)
        plugin=ET.SubElement(sensor,'plugin',name='front_camera_ros',filename='libgazebo_ros_camera.so')
        for key,value in dict(cameraName='front_cam/camera',imageTopicName='image',
            cameraInfoTopicName='camera_info',frameName='front_camera_optical',updateRate=20).items():
            put(plugin,key,value)
    MODEL.mkdir(parents=True,exist_ok=True)
    target=MODEL/('model_camera.sdf' if camera else 'model.sdf')
    ET.ElementTree(root).write(target,encoding='utf-8',xml_declaration=True)
    return target


if __name__=='__main__':
    print(build(False))
    print(build(True))
