#!/usr/bin/env bash
set -euo pipefail
course="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
while IFS='=' read -r key value; do
  case "$key" in
    PX4_TAG) tello_px4_tag="$value";;
    PX4_COMMIT) tello_px4_commit="$value";;
    PX4_GAZEBO_CLASSIC_COMMIT) tello_gazebo_commit="$value";;
  esac
done < "$course/tello_px4_runtime/versions.lock"
jobs="${JOBS:-2}"
[[ "$jobs" =~ ^[1-9][0-9]*$ ]] || { echo 'JOBS must be a positive integer' >&2; exit 2; }
build_root="$(mktemp -d "${TMPDIR:-/tmp}/tello-px4-build.XXXXXX")"
echo "Build directory: $build_root"
git clone --branch "$tello_px4_tag" --depth 1 https://github.com/PX4/PX4-Autopilot.git "$build_root/PX4-Autopilot"
px4="$build_root/PX4-Autopilot"
[[ "$(git -C "$px4" rev-parse HEAD)" == "$tello_px4_commit" ]]
git -C "$px4" submodule update --init --recursive
gazebo="$px4/Tools/simulation/gazebo-classic/sitl_gazebo-classic"
[[ "$(git -C "$gazebo" rev-parse HEAD)" == "$tello_gazebo_commit" ]]
git -C "$px4" apply "$course/tello_px4_runtime/patches/px4-no-gstreamer.patch"
git -C "$gazebo" apply "$course/tello_px4_runtime/patches/gazebo-qt.patch"
env -u PYTHONPATH PYTHONNOUSERSITE=1 /usr/bin/python3 -m venv "$build_root/venv"
env -u PYTHONPATH PYTHONNOUSERSITE=1 "$build_root/venv/bin/pip" install -r "$course/tools/requirements-build.txt"
export PATH="$build_root/venv/bin:$PATH"
unset PYTHONPATH VIRTUAL_ENV
cmake -S "$px4" -B "$px4/build/px4_sitl_default" -G Ninja \
  -DCONFIG=px4_sitl_default -DPYTHON_EXECUTABLE="$build_root/venv/bin/python3"
cmake --build "$px4/build/px4_sitl_default" --target px4 -- -j"$jobs"
cmake --build "$px4/build/px4_sitl_default" --target sitl_gazebo-classic -- -j"$jobs"
/usr/bin/python3 "$course/tools/pack_runtime.py" --px4-source "$px4" \
  --geoid "$course/tello_px4_runtime/runtime/geographiclib/geoids/egm96-5.pgm" \
  --output "$build_root/runtime"
echo "New runtime ready for validation: $build_root/runtime"
