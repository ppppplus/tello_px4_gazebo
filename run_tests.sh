#!/usr/bin/env bash
set -euo pipefail

workspace="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export ROS_HOME="$workspace/.ros"
export ROS_LOG_DIR="$ROS_HOME/log"
mkdir -p "$ROS_LOG_DIR"
export PYTHONPATH="$workspace/src/px4_competition/src:${PYTHONPATH:-}"
python3 -m unittest discover -s "$workspace/src/px4_competition/tests" -v
/usr/bin/python3 "$workspace/tools/tello/test_release.py"

if [[ -f "$workspace/devel_isolated/setup.bash" ]]; then
  source /opt/ros/noetic/setup.bash
  source "$workspace/devel_isolated/setup.bash"
  rospack find px4_competition >/dev/null
fi
