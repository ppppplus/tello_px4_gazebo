#!/usr/bin/env bash
set -euo pipefail
source /etc/os-release
if [[ "$ID" != ubuntu || "$VERSION_ID" != 20.04 || "$(uname -m)" != x86_64 ]]; then
  echo 'Use Ubuntu 20.04 x86_64 with ROS Noetic for this course distribution.' >&2
  exit 2
fi
if [[ ! -f /opt/ros/noetic/setup.bash ]]; then
  echo 'Install ROS Noetic and configure its apt repository first; see README.md.' >&2
  exit 2
fi
if [[ $EUID == 0 ]]; then elevate=(); else elevate=(sudo); fi
"${elevate[@]}" apt-get update
"${elevate[@]}" apt-get install --yes --no-remove \
  build-essential cmake python3-catkin-pkg python3-rospkg python3-empy \
  python3-nose python3-yaml python3-numpy python3-opencv \
  ros-noetic-catkin ros-noetic-rospy ros-noetic-actionlib ros-noetic-actionlib-msgs \
  ros-noetic-message-generation ros-noetic-message-runtime ros-noetic-tf \
  ros-noetic-geometry-msgs ros-noetic-nav-msgs ros-noetic-sensor-msgs ros-noetic-cv-bridge \
  ros-noetic-std-msgs ros-noetic-std-srvs ros-noetic-gazebo-ros \
  ros-noetic-gazebo-plugins ros-noetic-gazebo-msgs \
  ros-noetic-mavros ros-noetic-mavros-extras gazebo11
echo 'Dependencies ready. Run catkin_make from your workspace root.'
