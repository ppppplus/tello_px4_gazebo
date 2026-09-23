#!/usr/bin/env bash
# Source this file from any directory. ROS runtime uses system Python.
_tello_workspace="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source /opt/ros/noetic/setup.bash
source "$_tello_workspace/devel_isolated/setup.bash"
export ROS_HOME="$_tello_workspace/.ros"
export ROS_LOG_DIR="$ROS_HOME/log"
export GEOGRAPHICLIB_DATA="$_tello_workspace/geographiclib"
mkdir -p "$ROS_LOG_DIR"
unset _tello_workspace
