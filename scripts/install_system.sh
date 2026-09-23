#!/usr/bin/env bash
set -euo pipefail
root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source /etc/os-release
[[ "$ID" == ubuntu && "$VERSION_ID" == 20.04 && "$(uname -m)" == x86_64 ]] || {
  echo 'Supported baseline: Ubuntu 20.04 x86_64 only.' >&2; exit 2;
}
# Do not silently modify apt sources or trust unknown keys.
apt-cache show ros-noetic-ros-base >/dev/null 2>&1 || {
  echo 'Configure the official ROS Noetic apt repository first; see docs/INSTALL.md.' >&2; exit 2;
}
mapfile -t packages < <(sed '/^#/d; /^$/d' "$root/config/system-packages.txt")
if [[ $EUID == 0 ]]; then elevate=(); else elevate=(sudo); fi
"${elevate[@]}" apt-get update
"${elevate[@]}" apt-get install --yes --no-remove --no-install-recommends "${packages[@]}"
