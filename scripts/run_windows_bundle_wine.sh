#!/usr/bin/env bash

set -euo pipefail

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(cd -- "${script_dir}/.." && pwd)"

bundle_dir="${MERCURY_QT_BUNDLE_DIR:-${repo_root}/deployment/mercury-qt.dist}"
wine_prefix="${WINEPREFIX:-/home/rafael2k/files/rhizomatica/hermes/ai/wine-python312}"
wine_debug="${WINEDEBUG:--all}"
ui_port="${MERCURY_UI_BASE_PORT:-10000}"

mercury_exe="${bundle_dir}/mercury.exe"
gui_exe="${bundle_dir}/mercury-qt.exe"

for required_file in "${mercury_exe}" "${gui_exe}"; do
    if [[ ! -f "${required_file}" ]]; then
        echo "Missing required bundle file: ${required_file}" >&2
        exit 1
    fi
done

mercury_pid=""

cleanup() {
    if [[ -n "${mercury_pid}" ]] && kill -0 "${mercury_pid}" 2>/dev/null; then
        kill "${mercury_pid}" 2>/dev/null || true
        wait "${mercury_pid}" 2>/dev/null || true
    fi
}

trap cleanup EXIT INT TERM

echo "Using WINEPREFIX: ${wine_prefix}"
echo "Using bundle dir: ${bundle_dir}"
echo "Starting mercury.exe with UI bridge enabled..."

WINEPREFIX="${wine_prefix}" WINEDEBUG="${wine_debug}" \
    wine "${mercury_exe}" -G -U "${ui_port}" &
mercury_pid=$!

sleep 3

if ! kill -0 "${mercury_pid}" 2>/dev/null; then
    echo "mercury.exe exited before the GUI was launched." >&2
    wait "${mercury_pid}"
fi

echo "Starting mercury-qt.exe..."
WINEPREFIX="${wine_prefix}" WINEDEBUG="${wine_debug}" wine "${gui_exe}" "$@"
