#!/usr/bin/env bash
set -euo pipefail
root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
jobs="${JOBS:-2}"
[[ "$jobs" =~ ^[1-9][0-9]*$ ]] || { echo 'JOBS must be positive' >&2; exit 2; }
px4="$root/vendor/PX4-Autopilot"
/usr/bin/python3 "$root/scripts/fetch_dependencies.py" --check
for cache in "$px4/build/px4_sitl_default/CMakeCache.txt"; do
  if [[ -f "$cache" ]] && ! grep -Fxq "CMAKE_HOME_DIRECTORY:INTERNAL=$px4" "$cache"; then
    echo "Foreign PX4 build cache: $cache. Rename its build directory, then retry." >&2
    exit 2
  fi
done
[[ -x "$root/.venv-build/bin/python3" ]] || { echo 'Run ./setup.sh first' >&2; exit 2; }
(
  export PATH="$root/.venv-build/bin:$PATH"
  unset PYTHONPATH VIRTUAL_ENV
  # Fresh configure explicitly selects the private build interpreter.
  cmake -S "$px4" -B "$px4/build/px4_sitl_default" -G Ninja \
    -DCONFIG=px4_sitl_default -DPYTHON_EXECUTABLE="$root/.venv-build/bin/python3"
  cmake --build "$px4/build/px4_sitl_default" --target px4 -- -j"$jobs"
  cmake --build "$px4/build/px4_sitl_default" --target sitl_gazebo-classic -- -j"$jobs"
)
"$root/setup_workspace.sh"
