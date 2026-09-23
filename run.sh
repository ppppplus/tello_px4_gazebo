#!/usr/bin/env bash
set -euo pipefail
workspace="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [[ ! -f "$workspace/devel_isolated/setup.bash" ]]; then
  echo 'Run ./setup_workspace.sh first.' >&2
  exit 2
fi
exec "$workspace/run_tello_scaled.sh" "$@"
