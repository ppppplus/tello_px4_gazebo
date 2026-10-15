"""Shared geometric definitions for the arena, scene and referee."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Arena:
    size: float = 5.0
    boundary_wall_height: float = 2.5
    boundary_wall_thickness: float = 0.10
    wall_length: float = 3.0
    wall_height: float = 2.0
    wall_thickness: float = 0.05
    window_width: float = 0.95
    window_height: float = 0.60
    window_center_height: float = 1.48
    window_centers_x: tuple = (-1.0, 0.0, 1.0)
    marker_radius: float = 0.10
    marker_center_height: float = 1.89
    cabinet_centers_x: tuple = (-0.76, 0.76)
    cabinet_y: float = -1.30
    cabinet_width: float = 0.40
    cabinet_depth: float = 0.28
    cabinet_height: float = 1.0
    cabinet_hole_width: float = 0.26
    cabinet_hole_height: float = 0.28
    cabinet_hole_center_height: float = 0.78
    cabinet_panel_thickness: float = 0.035
    ball_radius: float = 0.10
    rotation_speed_deg: float = 15.0
    board_y: float = 2.47
    board_width: float = 2.0
    board_height: float = 1.0
    board_top: float = 1.64
    lamp_radius: float = 0.025
    lamp_columns_u: tuple = (0.25, 1.0, 1.75)
    lamp_rows_v: tuple = (0.125, 0.5, 0.875)
    pad_size: float = 0.6
    start_pad: tuple = (-2.2, -2.2)
    land_pad: tuple = (2.2, 2.2)
    start_pose: tuple = (-2.05, -2.05, 0.20)
    start_yaw: float = 1.5707963267948966

    @classmethod
    def from_dict(cls, values):
        values = dict(values)
        sequence_fields = ('window_centers_x', 'cabinet_centers_x', 'lamp_columns_u',
                           'lamp_rows_v', 'start_pad', 'land_pad', 'start_pose')
        for key in sequence_fields:
            if key in values:
                values[key] = tuple(values[key])
        result = cls(**values)
        result.validate()
        return result

    @property
    def window_bottom(self):
        return self.window_center_height - self.window_height / 2.0

    @property
    def window_top(self):
        return self.window_center_height + self.window_height / 2.0

    @property
    def board_front(self):
        return self.board_y - 0.015

    @property
    def lamp_face(self):
        return self.board_front - 0.02

    def lamp_position(self, index):
        col, row = divmod(index, 3)
        return (self.lamp_columns_u[col] - self.board_width / 2.0,
                self.lamp_face, self.board_top - self.lamp_rows_v[row])

    def on_pad(self, x, y, pad):
        half = self.pad_size / 2.0
        return abs(x - pad[0]) <= half and abs(y - pad[1]) <= half

    def validate(self):
        if self.size <= 0 or self.boundary_wall_height <= 0:
            raise ValueError('Arena dimensions must be positive')
        if len(self.window_centers_x) != 3 or len(self.cabinet_centers_x) != 2:
            raise ValueError('The arena requires three windows and two cabinets')
        if len(self.lamp_columns_u) != 3 or len(self.lamp_rows_v) != 3:
            raise ValueError('The board requires a 3 by 3 grid')
        if not (0 < self.window_bottom < self.window_top < self.wall_height):
            raise ValueError('Window opening must fit inside the wall')
        if not (0 < self.window_width < 1.0):
            raise ValueError('A window must fit within its 1 m wall bay')
        if self.marker_center_height + self.marker_radius > self.wall_height:
            raise ValueError('Red marker must fit above the window')


@dataclass(frozen=True)
class Rules:
    takeoff_rise: float = 0.30
    takeoff_hold: float = 0.5
    landing_height: float = 0.24
    landing_speed: float = 0.10
    landing_tilt_deg: float = 10.0
    landing_hold: float = 1.0
    lamp_distance: float = 0.5
    drone_half_width: float = 0.396
    drone_top_offset: float = 0.040
    drone_bottom_offset: float = -0.182
    wall_crossing_margin: float = 0.03

    @classmethod
    def from_dict(cls, values):
        return cls(**values)
