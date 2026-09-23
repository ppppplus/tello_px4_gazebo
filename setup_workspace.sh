#!/usr/bin/env bash
# Rebuild local ROS interfaces after setup.sh has built PX4 from pinned source.
set -euo pipefail
workspace="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
px4_root="$workspace/vendor/PX4-Autopilot"
if [[ ! -x "$px4_root/build/px4_sitl_default/bin/px4" ]]; then
  echo 'PX4 runtime missing. Run ./setup.sh for a complete source build.' >&2
  exit 2
fi
while IFS= read -r cache; do
  if ! grep -Fq "CMAKE_HOME_DIRECTORY:INTERNAL=$workspace/src/" "$cache"; then
    echo "Foreign build cache: $cache" >&2
    echo 'Preserve/rename build_isolated and devel_isolated, then retry.' >&2
    exit 2
  fi
done < <(find "$workspace/build_isolated" -name CMakeCache.txt 2>/dev/null || true)
source /opt/ros/noetic/setup.bash
export CMAKE_PREFIX_PATH=/opt/ros/noetic
export ROS_PACKAGE_PATH=/opt/ros/noetic/share
export ROS_HOME="$workspace/.ros"
export ROS_LOG_DIR="$ROS_HOME/log"
mkdir -p "$ROS_LOG_DIR"
[[ -x "$workspace/.venv-build/bin/python3" ]] || { echo 'Run ./setup.sh first' >&2; exit 2; }
# ROS uses system Python. MAVLink's standalone header generator needs future/lxml
# and uses the private build interpreter via FindPython3 instead.
catkin_make_isolated -C "$workspace" -j"${JOBS:-2}" --cmake-args -DPYTHON_EXECUTABLE=/usr/bin/python3 -DPython3_EXECUTABLE="$workspace/.venv-build/bin/python3"
echo "Ready: $workspace/run.sh seed:=11"
