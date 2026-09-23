#!/usr/bin/env bash
set -euo pipefail
workspace="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
package="$workspace/src/px4_competition"
exec "$workspace/run_tello.sh" gui:=true software_camera:=false \
  arena_file:="$package/config/tello_arena.yaml" \
  rules_file:="$package/config/tello_scaled_rules.yaml" \
  world_file:="$package/worlds/tello_final.world" \
  spawn_x:=-1.1275 spawn_y:=-1.1275 "$@"
