#!/usr/bin/env bash
# Bounded CI check using only the public student API; schematic camera only.
set -euo pipefail
root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$root"
mkdir -p .validation
for name in px4 gzserver rosmaster; do
  if pgrep -x "$name" >/dev/null; then
    echo "Existing $name process; refusing to run a second simulation" >&2; exit 2
  fi
done
./run.sh gui:=false software_camera:=true seed:=11 >.validation/headless.log 2>&1 &
launch_pid=$!
cleanup() {
  if kill -0 "$launch_pid" 2>/dev/null; then
    kill -INT "$launch_pid"
    wait "$launch_pid" || true
  fi
}
trap cleanup EXIT
source scripts/env.sh
# Wall-clock timeout also covers ROS master/action startup failures.
timeout 150 rosrun student_solution student_node.py --smoke
