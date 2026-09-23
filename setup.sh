#!/usr/bin/env bash
set -euo pipefail
root="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
install=false
fetch=true
build=true
for arg in "$@"; do
  case "$arg" in
    --install-system) install=true;;
    --no-fetch) fetch=false;;
    --fetch-only) build=false;;
    *) echo 'Usage: ./setup.sh [--install-system] [--no-fetch] [--fetch-only]' >&2; exit 2;;
  esac
done
source /etc/os-release
[[ "$ID" == ubuntu && "$VERSION_ID" == 20.04 && "$(uname -m)" == x86_64 ]] || {
  echo 'Use Ubuntu 20.04 x86_64 or the documented container.' >&2; exit 2;
}
if "$install"; then "$root/scripts/install_system.sh"; fi
if "$fetch"; then /usr/bin/python3 "$root/scripts/fetch_dependencies.py"; fi
if "$build"; then
  if [[ ! -x "$root/.venv-build/bin/python3" ]]; then
    env -u PYTHONPATH PYTHONNOUSERSITE=1 /usr/bin/python3 -m venv "$root/.venv-build"
  fi
  # Repair environments previously created while a global PYTHONPATH leaked pip.
  env -u PYTHONPATH PYTHONNOUSERSITE=1 "$root/.venv-build/bin/python3" -m ensurepip --upgrade
  env -u PYTHONPATH PYTHONNOUSERSITE=1 "$root/.venv-build/bin/python3" -m pip install --disable-pip-version-check --progress-bar off -r "$root/requirements-build.txt"
  "$root/scripts/build_all.sh"
  "$root/run_tests.sh"
  "$root/doctor.sh" --build-only
fi
