#!/usr/bin/env bash
set -euo pipefail
workspace="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
px4_root="$workspace/vendor/PX4-Autopilot"
package="$workspace/src/px4_competition"

# This entry is sequential with Iris: the shared ROS names and SITL ports must
# not have a live owner. Never kill another simulation to make room.
if pgrep -x px4 >/dev/null || pgrep -x gzserver >/dev/null || pgrep -x rosmaster >/dev/null; then
  echo 'A PX4/Gazebo/ROS master is already running. Stop it before starting Tello.' >&2
  exit 2
fi
for argument in "$@"; do
  case "$argument" in runtime:=*|vehicle_sdf:=*)
    echo 'Tello runtime/model are selected together; do not override them.' >&2; exit 2;;
  esac
done
gui_requested=false
real_camera=false
for argument in "$@"; do
  case "$argument" in
    gui:=true) gui_requested=true;; gui:=false) gui_requested=false;;
    software_camera:=false) real_camera=true;; software_camera:=true) real_camera=false;;
  esac
done
if [[ "$real_camera" == true && -z "${DISPLAY:-}" ]]; then
  echo 'Real Gazebo camera needs a working DISPLAY (or virtual X server).' >&2
  exit 2
fi
if [[ "$gui_requested" == false && "$real_camera" == false ]]; then
  unset DISPLAY
fi
if [[ ! -x "$px4_root/build/px4_sitl_default/bin/px4" || ! -f "$package/models/tello_training/model.sdf" ]]; then
  echo 'Run ./setup.sh to fetch and build the complete environment.' >&2
  exit 2
fi

# Copy the *built* ROMFS, then add an independent airframe. No upstream source,
# built Iris airframe, .ros directory or persisted Iris parameters are changed.
mkdir -p "$workspace/.tello_runtime"
tello_runtime="$(mktemp -d "$workspace/.tello_runtime/run.XXXXXX")"
cp -aL "$px4_root/build/px4_sitl_default/etc" "$tello_runtime/etc"
cp "$workspace/tools/tello/10420_gazebo-classic_tello" "$tello_runtime/etc/init.d-posix/airframes/"
export ROS_HOME="$tello_runtime/ros"
export ROS_LOG_DIR="$ROS_HOME/log"
mkdir -p "$ROS_LOG_DIR"
source /opt/ros/noetic/setup.bash
set +u
source /usr/share/gazebo/setup.sh
source "$workspace/devel_isolated/setup.bash"
set -u
export ROS_PACKAGE_PATH="$px4_root:$px4_root/Tools/simulation/gazebo-classic/sitl_gazebo-classic:${ROS_PACKAGE_PATH:-}"
export GAZEBO_MODEL_PATH="$package/models:$px4_root/Tools/simulation/gazebo-classic/sitl_gazebo-classic/models:${GAZEBO_MODEL_PATH:-}"
export GAZEBO_PLUGIN_PATH="$px4_root/build/px4_sitl_default/build_gazebo-classic:${GAZEBO_PLUGIN_PATH:-}"
export LD_LIBRARY_PATH="$px4_root/build/px4_sitl_default/build_gazebo-classic:${LD_LIBRARY_PATH:-}"
export GEOGRAPHICLIB_DATA="$workspace/geographiclib"
echo "Tello isolated runtime: $tello_runtime"
exec roslaunch px4_competition tello.launch runtime:="$tello_runtime" "$@"
