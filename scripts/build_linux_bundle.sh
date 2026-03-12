#!/usr/bin/env bash

set -euo pipefail

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(cd -- "${script_dir}/.." && pwd)"

resolve_path() {
    python3 - "$repo_root" "$1" <<'PY'
from pathlib import Path
import sys

base = Path(sys.argv[1])
raw = Path(sys.argv[2]).expanduser()
if raw.is_absolute():
    print(raw.resolve())
else:
    print((base / raw).resolve())
PY
}

bundle_dir_default="${repo_root}/deployment-linux"
bundle_dir="${MERCURY_QT_LINUX_BUNDLE_DIR:-${MERCURY_QT_BUNDLE_DIR:-${bundle_dir_default}}}"
mercury_dir="${MERCURY_QT_MERCURY_DIR:-${repo_root}/../mercury}"
python_bin="${MERCURY_QT_PYTHON:-python3}"
app_title="${MERCURY_QT_APP_TITLE:-mercury-qt}"
bundle_mode="${MERCURY_QT_LINUX_BUNDLE_MODE:-auto}"

skip_mercury_build=0
skip_deploy=0
deploy_args=()

usage() {
    cat <<EOF
Usage: $(basename "$0") [wrapper options] [-- pyside6-deploy options]

Build the Linux mercury-qt bundle and stage the sibling mercury backend next to it.

Wrapper options:
  --bundle-dir PATH        Bundle output directory (default: ${bundle_dir})
  --mercury-dir PATH       mercury checkout to build/stage (default: ${mercury_dir})
  --python PATH            Python interpreter for the Linux bundle tools (default: ${python_bin})
  --mode MODE              Bundle mode: auto, standalone, source (default: ${bundle_mode})
  --skip-mercury-build     Reuse an existing mercury binary instead of running 'make clean && make -j4'
  --skip-deploy            Only stage mercury into an existing Linux bundle
  -h, --help               Show this help text

Environment overrides:
  MERCURY_QT_LINUX_BUNDLE_DIR
  MERCURY_QT_BUNDLE_DIR
  MERCURY_QT_MERCURY_DIR
  MERCURY_QT_PYTHON
  MERCURY_QT_APP_TITLE
  MERCURY_QT_LINUX_BUNDLE_MODE

Modes:
  auto        Prefer a native standalone build via pyside6-deploy when Nuitka and
              patchelf are already available in the selected Python environment.
              Otherwise fall back to a runnable source bundle.
  standalone  Require pyside6-deploy + Nuitka + patchelf and build a standalone
              Linux bundle.
  source      Create a runnable source bundle with a local launcher script that
              uses the selected Python interpreter.

Examples:
  $(basename "$0")
  $(basename "$0") --mode standalone -- --verbose
  $(basename "$0") --skip-mercury-build --mode source
EOF
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --bundle-dir)
            bundle_dir="$2"
            shift 2
            ;;
        --mercury-dir)
            mercury_dir="$2"
            shift 2
            ;;
        --python)
            python_bin="$2"
            shift 2
            ;;
        --mode)
            bundle_mode="$2"
            shift 2
            ;;
        --skip-mercury-build)
            skip_mercury_build=1
            shift
            ;;
        --skip-deploy)
            skip_deploy=1
            shift
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        --)
            shift
            deploy_args+=("$@")
            break
            ;;
        *)
            deploy_args+=("$1")
            shift
            ;;
    esac
done

case "$bundle_mode" in
    auto|standalone|source)
        ;;
    *)
        echo "Unsupported bundle mode: ${bundle_mode}" >&2
        exit 1
        ;;
esac

bundle_dir="$(resolve_path "$bundle_dir")"
mercury_dir="$(resolve_path "$mercury_dir")"

if [[ "$python_bin" == */* ]]; then
    python_bin="$(resolve_path "$python_bin")"
else
    python_bin="$(command -v "$python_bin")"
fi

main_file="${repo_root}/app.py"
requirements_file="${repo_root}/requirements.txt"
mercury_binary="${mercury_dir}/mercury"
runtime_dir=""
bundle_executable=""

if [[ ! -f "$main_file" ]]; then
    echo "Missing main file: $main_file" >&2
    exit 1
fi

if [[ ! -d "$mercury_dir" ]]; then
    echo "Missing mercury checkout: $mercury_dir" >&2
    exit 1
fi

if ! "$python_bin" - <<'PY' >/dev/null 2>&1
import PySide6
import numpy
PY
then
    echo "The selected Python interpreter must be able to import PySide6 and numpy: ${python_bin}" >&2
    exit 1
fi

have_standalone_toolchain() {
    command -v pyside6-deploy >/dev/null 2>&1 || return 1
    "$python_bin" -m nuitka --version >/dev/null 2>&1 || return 1
    command -v patchelf >/dev/null 2>&1 || return 1
}

source_bundle_runtime_dir() {
    printf '%s\n' "${bundle_dir}/${app_title}"
}

standalone_bundle_runtime_dir() {
    printf '%s\n' "${bundle_dir}/${app_title}.dist"
}

find_standalone_executable() {
    find "$bundle_dir" -maxdepth 2 -type f \( -name "${app_title}.bin" -o -name "app.bin" -o -name "*.bin" \) | sort | head -n 1
}

build_source_bundle() {
    runtime_dir="$(source_bundle_runtime_dir)"
    rm -rf "$runtime_dir"
    mkdir -p "$runtime_dir"

    for entry in app.py requirements.txt apps assets core modules; do
        cp -a "${repo_root}/${entry}" "$runtime_dir/"
    done

    find "$runtime_dir" -type d -name '__pycache__' -prune -exec rm -rf {} +

    cat >"${runtime_dir}/${app_title}" <<EOF
#!/usr/bin/env bash
set -euo pipefail
script_dir="\$(cd -- "\$(dirname -- "\${BASH_SOURCE[0]}")" && pwd)"
python_bin="\${MERCURY_QT_PYTHON:-${python_bin}}"
export PYTHONPATH="\${script_dir}"
exec "\${python_bin}" "\${script_dir}/app.py" mercury "\$@"
EOF
    chmod +x "${runtime_dir}/${app_title}"

    bundle_executable="${runtime_dir}/${app_title}"
}

build_standalone_bundle() {
    local spec_dir spec_file
    spec_dir="$(mktemp -d "${TMPDIR:-/tmp}/mercury-qt-linux-deploy.XXXXXX")"
    spec_file="${spec_dir}/pysidedeploy.spec"
    trap 'rm -rf "'"${spec_dir}"'"' RETURN

    cat >"$spec_file" <<EOF
[app]
title = ${app_title}
project_dir = ${repo_root}
input_file = ${main_file}
exec_directory = ${bundle_dir}
project_file =
icon =

[python]
python_path = ${python_bin}
packages = Nuitka==2.5.1

[qt]
qml_files =
excluded_qml_plugins =
modules = Network,Widgets,Gui,Core,Charts
plugins =

[nuitka]
macos.permissions =
mode = standalone
extra_args = --quiet --noinclude-qt-translations
EOF

    cmd=(
        pyside6-deploy
        -c "$spec_file"
        -f
        --keep-deployment-files
        "${deploy_args[@]}"
    )
    printf 'Command:'
    printf ' %q' "${cmd[@]}"
    printf '\n'
    "${cmd[@]}"

    bundle_executable="$(find_standalone_executable || true)"
    if [[ -z "$bundle_executable" ]]; then
        echo "Unable to locate the Linux standalone bundle executable under ${bundle_dir}" >&2
        exit 1
    fi

    runtime_dir="$(dirname "$bundle_executable")"
}

echo "Repository root: ${repo_root}"
echo "Bundle directory: ${bundle_dir}"
echo "Mercury checkout: ${mercury_dir}"
echo "Python: ${python_bin}"
echo "Requested mode: ${bundle_mode}"

if [[ "$skip_mercury_build" -eq 0 ]]; then
    echo "Running: make clean && make -j4"
    (
        cd "$mercury_dir"
        make clean
        make -j4
    )
fi

if [[ ! -x "$mercury_binary" ]]; then
    echo "Mercury binary not found after build: ${mercury_binary}" >&2
    exit 1
fi

actual_mode="$bundle_mode"
if [[ "$actual_mode" == "auto" ]]; then
    if have_standalone_toolchain; then
        actual_mode="standalone"
    else
        actual_mode="source"
    fi
fi

echo "Selected mode: ${actual_mode}"

if [[ "$skip_deploy" -eq 0 ]]; then
    if [[ "$actual_mode" == "standalone" ]]; then
        if ! have_standalone_toolchain; then
            echo "Standalone mode requires pyside6-deploy, python -m nuitka, and patchelf." >&2
            exit 1
        fi
        build_standalone_bundle
    else
        build_source_bundle
    fi
else
    if [[ "$actual_mode" == "standalone" ]]; then
        runtime_dir="$(standalone_bundle_runtime_dir)"
        bundle_executable="$(find_standalone_executable || true)"
    else
        runtime_dir="$(source_bundle_runtime_dir)"
        bundle_executable="${runtime_dir}/${app_title}"
    fi
fi

if [[ -z "$runtime_dir" || ! -d "$runtime_dir" ]]; then
    echo "Bundle runtime directory not found: ${runtime_dir}" >&2
    exit 1
fi

install -m 755 "$mercury_binary" "${runtime_dir}/mercury"

echo "Bundle executable: ${bundle_executable}"
echo "Staged mercury: ${runtime_dir}/mercury"
