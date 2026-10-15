"""Deterministic scoring core with no ROS or Gazebo dependency."""

import math
from dataclasses import dataclass


@dataclass(frozen=True)
class FlightSample:
    time: float
    x: float
    y: float
    z: float
    vx: float = 0.0
    vy: float = 0.0
    vz: float = 0.0
    roll: float = 0.0
    pitch: float = 0.0


class Scorekeeper:
    def __init__(self, arena, rules, round_data):
        colors = round_data.get('colors', '')
        if len(colors) != 2 or any(letter not in 'rgb' for letter in colors):
            raise ValueError('Round ball colors must be two r/g/b codes')
        self.arena, self.rules, self.round = arena, rules, round_data
        self.phase = 'ready'
        self.scores = {'takeoff': 0, 'rotating_ball': 0, 'fixed_ball': 0,
                       'window': 0, 'lamp1': 0, 'lamp2': 0, 'lamp3': 0, 'landing': 0}
        self.ball_submitted = False
        self.lamp_progress = 0
        self.start_height = self.takeoff_pending = self.landing_pending = None
        self.start_time = self.end_time = self.last = None
        self.crossing = self.crossing_valid = False

    @property
    def score(self):
        return sum(self.scores.values())

    @property
    def elapsed(self):
        if self.start_time is None:
            return 0.0
        end = self.end_time if self.end_time is not None else (
            self.last.time if self.last else self.start_time)
        return max(0.0, end - self.start_time)

    def status(self):
        return {'round_id': self.round['round_id'], 'phase': self.phase,
                'score': self.score, 'scores': dict(self.scores),
                'elapsed': round(self.elapsed, 3),
                'ball_submitted': self.ball_submitted,
                'lamp_progress': self.lamp_progress}

    def _window_clear(self, sample):
        center = self.arena.window_centers_x[self.round['active_window']]
        lateral = self.arena.window_width / 2 - self.rules.drone_half_width - 0.005
        return (lateral > 0 and abs(sample.x - center) < lateral
                and self.arena.window_bottom - self.rules.drone_bottom_offset + 0.01 < sample.z
                and sample.z < self.arena.window_top - self.rules.drone_top_offset - 0.01)

    def _window_transit(self, previous, current):
        if self.scores['window'] or self.phase != 'running':
            return False
        reach = self.rules.drone_half_width + self.arena.wall_thickness / 2
        if previous is not None and math.dist((previous.x, previous.y, previous.z),
                                              (current.x, current.y, current.z)) > 0.25:
            self.crossing = self.crossing_valid = False
            return False
        if current.y <= -reach:
            self.crossing = self.crossing_valid = False
            return False
        if previous is not None and previous.y <= -reach < current.y:
            self.crossing = True
            self.crossing_valid = self._window_clear(previous) and self._window_clear(current)
        elif self.crossing and -reach < current.y < reach:
            self.crossing_valid = self.crossing_valid and self._window_clear(current)
        if self.crossing and previous is not None and previous.y < reach <= current.y:
            valid = self.crossing_valid and self._window_clear(current)
            self.crossing = self.crossing_valid = False
            return valid
        return False

    def update(self, sample):
        events = []
        if self.last is not None and sample.time < self.last.time:
            self.last = sample
            self.crossing = self.crossing_valid = False
            return [{'kind': 'clock_reset', 'score_delta': 0}]
        previous, self.last = self.last, sample
        if self.phase == 'ready':
            if self.start_height is None and self.arena.on_pad(sample.x, sample.y, self.arena.start_pad):
                self.start_height = sample.z
            if self.start_height is not None and sample.z > self.start_height + self.rules.takeoff_rise:
                if self.takeoff_pending is None:
                    self.takeoff_pending = sample.time
                if sample.time - self.takeoff_pending >= self.rules.takeoff_hold:
                    self.phase, self.start_time = 'running', self.takeoff_pending
                    self.scores['takeoff'] = 15
                    events.append({'kind': 'takeoff', 'score_delta': 15})
            else:
                self.takeoff_pending = None
        if self.phase == 'running':
            if self._window_transit(previous, sample):
                self.scores['window'] = 20
                events.append({'kind': 'window', 'score_delta': 20})
            speed = math.sqrt(sample.vx ** 2 + sample.vy ** 2 + sample.vz ** 2)
            landed = (self.arena.on_pad(sample.x, sample.y, self.arena.land_pad)
                      and sample.z <= self.rules.landing_height
                      and speed < self.rules.landing_speed
                      and abs(sample.roll) < math.radians(self.rules.landing_tilt_deg)
                      and abs(sample.pitch) < math.radians(self.rules.landing_tilt_deg))
            if landed:
                if self.landing_pending is None:
                    self.landing_pending = sample.time
                if sample.time - self.landing_pending >= self.rules.landing_hold:
                    self.phase, self.end_time = 'finished', self.landing_pending
                    self.scores['landing'] = 15
                    events.append({'kind': 'landing', 'score_delta': 15})
            else:
                self.landing_pending = None
        return events

    def submit(self, message):
        if self.phase != 'running' or self.last is None:
            return {'accepted': False, 'reason': 'competition_not_running', 'score_delta': 0}
        if len(message) == 2 and all(letter in 'rgb' for letter in message):
            if self.ball_submitted:
                return {'accepted': False, 'reason': 'ball_result_already_submitted', 'score_delta': 0}
            self.ball_submitted, delta = True, 0
            for index, key in enumerate(('rotating_ball', 'fixed_ball')):
                if message[index] == self.round['colors'][index]:
                    self.scores[key], delta = 10, delta + 10
            return {'accepted': True, 'reason': 'ball_result_recorded', 'score_delta': delta}
        if message.startswith('target') and message[6:].isdigit():
            number = int(message[6:])
            if number != self.lamp_progress + 1 or number > 3:
                return {'accepted': False, 'reason': 'wrong_lamp_order', 'score_delta': 0}
            point = self.arena.lamp_position(self.round['lamp_indices'][self.lamp_progress])
            distance = math.dist((self.last.x, self.last.y, self.last.z), point)
            if distance >= self.rules.lamp_distance:
                return {'accepted': False, 'reason': 'too_far_from_lamp',
                        'distance': round(distance, 4), 'score_delta': 0}
            self.scores[f'lamp{number}'] = 10
            self.lamp_progress += 1
            return {'accepted': True, 'reason': 'lamp_confirmed', 'score_delta': 10,
                    'distance': round(distance, 4), 'progress': self.lamp_progress}
        return {'accepted': False, 'reason': 'invalid_message', 'score_delta': 0}
