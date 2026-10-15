#!/usr/bin/env python3
"""Create, randomize and reset the competition objects in Gazebo Classic."""

import json
import math
import random
import threading

import rospy
from gazebo_msgs.msg import ModelState
from gazebo_msgs.srv import DeleteModel, SetModelState, SpawnModel
from geometry_msgs.msg import Pose, Twist
from std_msgs.msg import Bool, String
from std_srvs.srv import Trigger, TriggerResponse
from tf.transformations import quaternion_from_euler

from tello_competition import models
from tello_competition.geometry import Arena


class FinalScene:
    def __init__(self):
        self.arena = Arena.from_dict(rospy.get_param('/arena'))
        self.seed = int(rospy.get_param('/final/seed', 1))
        self.vehicle_model = rospy.get_param('/final/vehicle_model', 'iris')
        self.epoch = self.progress = self.animation_ticks = 0
        self.round = None
        self.started_at = rospy.Time(0)
        self.lock = threading.RLock()
        rospy.wait_for_service('/gazebo/spawn_sdf_model')
        rospy.wait_for_service('/gazebo/delete_model')
        rospy.wait_for_service('/gazebo/set_model_state')
        self.spawn = rospy.ServiceProxy('/gazebo/spawn_sdf_model', SpawnModel)
        self.delete = rospy.ServiceProxy('/gazebo/delete_model', DeleteModel)
        self.set_state = rospy.ServiceProxy('/gazebo/set_model_state', SetModelState)
        self.round_pub = rospy.Publisher('/teacher/final/round', String,
                                         queue_size=1, latch=True)
        self.reset_pub = rospy.Publisher('/teacher/final/resetting', Bool,
                                         queue_size=1, latch=True)
        self.stop_pub = rospy.Publisher('/tello/cmd_vel', Twist, queue_size=1)
        rospy.Subscriber('/teacher/final/light_progress', String,
                         self.light_callback, queue_size=10)
        rospy.Service('/final/reset', Trigger, self.reset_callback)
        rospy.Service('/final/randomize', Trigger, self.randomize_callback)
        self.start_round(reset_vehicle=False)
        rospy.Timer(rospy.Duration(0.05), self.animate)

    @staticmethod
    def pose(x, y, z, yaw=0.0):
        result = Pose()
        result.position.x, result.position.y, result.position.z = x, y, z
        quaternion = quaternion_from_euler(0, 0, yaw)
        result.orientation.x, result.orientation.y = quaternion[0], quaternion[1]
        result.orientation.z, result.orientation.w = quaternion[2], quaternion[3]
        return result

    def spawn_checked(self, name, sdf, position):
        answer = self.spawn(name, sdf, '', self.pose(*position), 'world')
        if not answer.success:
            raise RuntimeError(f'Gazebo could not spawn {name}: {answer.status_message}')

    def remove(self, name):
        answer = self.delete(name)
        if not answer.success:
            rospy.logwarn('Could not delete %s: %s', name, answer.status_message)

    @staticmethod
    def dynamic_names():
        return ['final_rotating_cabinet', 'final_fixed_cabinet', 'final_window_marker',
                'final_lamp_1', 'final_lamp_2', 'final_lamp_3',
                'final_lamp_1_lit', 'final_lamp_2_lit', 'final_lamp_3_lit']

    def move_lit_lamp(self, index, visible):
        state = ModelState()
        state.model_name = f'final_lamp_{index + 1}_lit'
        state.reference_frame = 'world'
        x, y, z = self.arena.lamp_position(self.round['lamp_indices'][index])
        state.pose = self.pose(x, y - 0.007 if visible else self.arena.board_y + 0.04, z)
        answer = self.set_state(state)
        if not answer.success:
            raise RuntimeError(f'Could not update lamp {index + 1}: {answer.status_message}')

    def reset_vehicle(self):
        self.reset_pub.publish(True)
        self.stop_pub.publish(Twist())
        try:
            from mavros_msgs.srv import CommandBool
            rospy.wait_for_service('/mavros/cmd/arming', timeout=3)
            rospy.ServiceProxy('/mavros/cmd/arming', CommandBool)(False)
        except (ImportError, rospy.ROSException, rospy.ServiceException) as error:
            rospy.logwarn('PX4 disarm during reset was unavailable: %s', error)
        state = ModelState()
        state.model_name = self.vehicle_model
        state.reference_frame = 'world'
        state.pose = self.pose(*self.arena.start_pose, self.arena.start_yaw)
        state.twist = Twist()
        answer = self.set_state(state)
        if not answer.success:
            raise RuntimeError(f'Could not reset {self.vehicle_model}: {answer.status_message}')
        rospy.sleep(0.5)
        self.reset_pub.publish(False)

    def start_round(self, reset_vehicle):
        with self.lock:
            if self.round is not None:
                for name in self.dynamic_names():
                    self.remove(name)
            if reset_vehicle:
                self.reset_vehicle()
            randomizer = random.Random(self.seed)
            self.epoch += 1
            self.round = {
                'round_id': f'{self.seed}:{self.epoch}',
                'seed': self.seed,
                'colors': randomizer.choice('rgb') + randomizer.choice('rgb'),
                'active_window': randomizer.randrange(3),
                'lamp_indices': randomizer.sample(range(9), 3),
            }
            self.progress = 0
            arena = self.arena
            self.spawn_checked('final_rotating_cabinet',
                               models.cabinet(arena, self.round['colors'][0], True),
                               (arena.cabinet_centers_x[0], arena.cabinet_y, 0))
            self.spawn_checked('final_fixed_cabinet',
                               models.cabinet(arena, self.round['colors'][1], False),
                               (arena.cabinet_centers_x[1], arena.cabinet_y, 0))
            self.spawn_checked('final_window_marker', models.marker(arena),
                               (arena.window_centers_x[self.round['active_window']],
                                -arena.wall_thickness / 2 - 0.006,
                                arena.marker_center_height))
            for index, is_on in enumerate(models.lamp_states(0)):
                position = arena.lamp_position(self.round['lamp_indices'][index])
                self.spawn_checked(f'final_lamp_{index + 1}',
                                   models.lamp(arena, index + 1, False), position)
                lit_position = ((position[0], position[1] - 0.007, position[2])
                                if is_on else
                                (position[0], arena.board_y + 0.04, position[2]))
                self.spawn_checked(f'final_lamp_{index + 1}_lit',
                                   models.lamp(arena, index + 1, True), lit_position)
            self.started_at = rospy.Time.now()
            self.round_pub.publish(json.dumps(self.round, ensure_ascii=False))
            rospy.loginfo('Round %s initialized', self.round['round_id'])

    def light_callback(self, message):
        with self.lock:
            if self.round is None:
                return
            try:
                value = json.loads(message.data)
                stage = int(value['progress'])
            except (ValueError, KeyError, TypeError):
                return
            if (value.get('round_id') != self.round['round_id']
                    or stage != self.progress + 1 or stage > 3):
                return
            self.move_lit_lamp(self.progress, False)
            if stage < 3:
                self.move_lit_lamp(stage, True)
            self.progress = stage

    def animate(self, _event):
        with self.lock:
            if self.round is None or rospy.is_shutdown():
                return
            elapsed = (rospy.Time.now() - self.started_at).to_sec()
            if elapsed < 0:
                self.started_at = rospy.Time.now()
                return
            state = ModelState()
            state.model_name = 'final_rotating_cabinet'
            state.reference_frame = 'world'
            state.pose = self.pose(self.arena.cabinet_centers_x[0], self.arena.cabinet_y,
                                   0, math.radians(self.arena.rotation_speed_deg) * elapsed)
            self.set_state(state)
            self.animation_ticks += 1
            if self.animation_ticks % 5 == 0:
                for index in range(3):
                    self.move_lit_lamp(index,
                                       self.progress < 3 and index == self.progress)

    def reset_callback(self, _request):
        try:
            self.start_round(reset_vehicle=True)
            return TriggerResponse(success=True, message=self.round['round_id'])
        except Exception as error:  # ROS service boundary
            self.reset_pub.publish(False)
            rospy.logerr('Round reset failed: %s', error)
            return TriggerResponse(success=False, message=str(error))

    def randomize_callback(self, request):
        self.seed += 1
        return self.reset_callback(request)


if __name__ == '__main__':
    rospy.init_node('final_scene')
    FinalScene()
    rospy.spin()
