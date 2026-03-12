#!/usr/bin/env bash

set -euo pipefail

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(cd -- "${script_dir}/.." && pwd)"

bundle_dir="${MERCURY_QT_BUNDLE_DIR:-${repo_root}/deployment}"
mercury_dir="${MERCURY_QT_MERCURY_DIR:-${repo_root}/../mercury}"
wine_prefix="${MERCURY_QT_WINE_PREFIX:-${WINEPREFIX:-${repo_root}/../wine-python312}}"
wine_python="${MERCURY_QT_WINE_PYTHON:-${wine_prefix}/drive_c/Python312/python.exe}"

usage() {
    cat <<EOF
Usage: $(basename "$0") [build_windows_bundle.py options] [-- deploy options]

Build the Windows mercury-qt bundle from Linux and stage mercury.exe from the
sibling mercury checkout.

Defaults:
  bundle dir:   ${bundle_dir}
  mercury dir:  ${mercury_dir}
  wine prefix:  ${wine_prefix}
  wine python:  ${wine_python}

Environment overrides:
  MERCURY_QT_BUNDLE_DIR
  MERCURY_QT_MERCURY_DIR
  MERCURY_QT_WINE_PREFIX
  MERCURY_QT_WINE_PYTHON
  WINEPREFIX

Examples:
  $(basename "$0") -- --force --keep-deployment-files
  MERCURY_QT_WINE_PREFIX=/path/to/wine-python312 \\
    $(basename "$0") --skip-mercury-build -- --force

This wrapper reuses scripts/build_windows_bundle.py, so any extra arguments are
forwarded to that helper unchanged. Provision the Wine prefix first with:
  python3 scripts/setup_wine_python.py /path/to/python-3.12.x-amd64.exe --wine-prefix /path/to/wine-python312
EOF
}

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
    usage
    exit 0
fi

build_script="${repo_root}/scripts/build_windows_bundle.py"
if [[ ! -f "${build_script}" ]]; then
    echo "Missing build helper: ${build_script}" >&2
    exit 1
fi

cmd=(
    python3
    "${build_script}"
    --bundle-dir "${bundle_dir}"
    --mercury-dir "${mercury_dir}"
    --wine-prefix "${wine_prefix}"
    --wine-python "${wine_python}"
    "$@"
)

printf 'Command:'
printf ' %q' "${cmd[@]}"
printf '\n'

"${cmd[@]}"
