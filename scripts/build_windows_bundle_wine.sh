#!/usr/bin/env bash

set -euo pipefail

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(cd -- "${script_dir}/.." && pwd)"

bundle_dir="${MERCURY_QT_BUNDLE_DIR:-${repo_root}/deployment}"
mercury_dir="${MERCURY_QT_MERCURY_DIR:-${repo_root}/../mercury}"
wine_prefix="${MERCURY_QT_WINE_PREFIX:-${WINEPREFIX:-${repo_root}/../wine-python312}}"
wine_python="${MERCURY_QT_WINE_PYTHON:-${wine_prefix}/drive_c/Python312/python.exe}"
app_title="${MERCURY_QT_APP_TITLE:-mercury-qt}"

PYTHON_VERSION="3.12.10"
PYTHON_INSTALLER_URL="https://www.python.org/ftp/python/${PYTHON_VERSION}/python-${PYTHON_VERSION}-amd64.exe"
PYTHON_INSTALLER="python-${PYTHON_VERSION}-amd64.exe"

resolve_path() {
    local path="$1"

    if [[ "${path}" = /* ]]; then
        printf '%s\n' "${path}"
        return
    fi

    printf '%s\n' "${repo_root}/${path}"
}

usage() {
    cat <<EOF
Usage: $(basename "$0") [options] [-- build_windows_bundle.py options]

Build the Windows mercury-qt bundle from Linux using Wine + Nuitka.

If the Wine prefix does not exist, it is created automatically by
downloading the CPython ${PYTHON_VERSION} installer and running
setup_wine_python.py.

Options:
  --setup-only            Set up the Wine prefix and exit (no build)
  --skip-setup            Skip Wine prefix setup even if missing
  --skip-mercury-build    Reuse existing mercury.exe
  --reset-prefix          Wipe and recreate the Wine prefix
  -h, --help              Show this help

Defaults:
  bundle dir:   ${bundle_dir}
  mercury dir:  ${mercury_dir}
  wine prefix:  ${wine_prefix}
  wine python:  ${wine_python}
  app title:    ${app_title}

Environment overrides:
  MERCURY_QT_BUNDLE_DIR
  MERCURY_QT_MERCURY_DIR
  MERCURY_QT_WINE_PREFIX
  MERCURY_QT_WINE_PYTHON
  MERCURY_QT_APP_TITLE
  WINEPREFIX

Examples:
  $(basename "$0")                         # full build (setup if needed + bundle + zip)
  $(basename "$0") --setup-only            # just set up Wine prefix
  $(basename "$0") --reset-prefix          # wipe prefix and rebuild everything
  $(basename "$0") --skip-mercury-build    # reuse existing mercury.exe
EOF
}

setup_only=0
skip_setup=0
reset_prefix=0
forwarded_args=()

while [[ $# -gt 0 ]]; do
    case "$1" in
        --setup-only)
            setup_only=1
            shift
            ;;
        --skip-setup)
            skip_setup=1
            shift
            ;;
        --reset-prefix)
            reset_prefix=1
            shift
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        --)
            shift
            forwarded_args+=("$@")
            break
            ;;
        *)
            forwarded_args+=("$1")
            shift
            ;;
    esac
done

# ---- Ensure Wine prefix exists ----
setup_wine_prefix() {
    local installer_path="${repo_root}/${PYTHON_INSTALLER}"

    if [[ ! -f "${installer_path}" ]]; then
        echo "Downloading CPython ${PYTHON_VERSION} Windows installer..."
        wget -q --show-progress -O "${installer_path}" "${PYTHON_INSTALLER_URL}"
    fi

    local setup_args=(
        python3
        "${script_dir}/setup_wine_python.py"
        "${installer_path}"
        --wine-prefix "${wine_prefix}"
    )

    if [[ "${reset_prefix}" -eq 1 ]]; then
        setup_args+=(--reset-prefix)
    fi

    echo "Setting up Wine prefix at ${wine_prefix}..."
    "${setup_args[@]}"
}

if [[ "${reset_prefix}" -eq 1 ]] || { [[ "${skip_setup}" -eq 0 ]] && [[ ! -f "${wine_python}" ]]; }; then
    setup_wine_prefix
fi

if [[ "${setup_only}" -eq 1 ]]; then
    echo "Wine prefix ready. Skipping build."
    exit 0
fi

# ---- Check prerequisites ----
build_script="${repo_root}/scripts/build_windows_bundle.py"
if [[ ! -f "${build_script}" ]]; then
    echo "Missing build helper: ${build_script}" >&2
    exit 1
fi

if ! command -v zip >/dev/null 2>&1; then
    echo "Missing required tool: zip" >&2
    exit 1
fi

if [[ ! -f "${wine_python}" ]]; then
    echo "Wine Python not found at: ${wine_python}" >&2
    echo "Run: $(basename "$0") --setup-only" >&2
    exit 1
fi

bundle_dir_abs="$(resolve_path "${bundle_dir}")"
mercury_dir_abs="$(resolve_path "${mercury_dir}")"

# ---- Build the Nuitka bundle ----
# Nuitka output directory (used by the Python helper)
nuitka_dist_dir="${bundle_dir_abs}/${app_title}.dist"
bundle_executable="${nuitka_dist_dir}/${app_title}.exe"
bundle_mercury="${nuitka_dist_dir}/mercury.exe"

cmd=(
    python3
    "${build_script}"
    --bundle-dir "${bundle_dir}"
    --mercury-dir "${mercury_dir}"
    --wine-prefix "${wine_prefix}"
    --wine-python "${wine_python}"
    "${forwarded_args[@]}"
)

printf 'Command:'
printf ' %q' "${cmd[@]}"
printf '\n'

"${cmd[@]}"

if [[ ! -d "${nuitka_dist_dir}" ]]; then
    echo "Expected runtime directory not found: ${nuitka_dist_dir}" >&2
    exit 1
fi

for required_file in "${bundle_executable}" "${bundle_mercury}"; do
    if [[ ! -f "${required_file}" ]]; then
        echo "Expected bundled file not found: ${required_file}" >&2
        exit 1
    fi
done

# ---- Rename and zip ----
qt_version="$(head -1 "${repo_root}/debian/changelog" | sed 's/.*(\(.*\)).*/\1/')"
bundle_runtime_dir="${bundle_dir_abs}/${app_title}-${qt_version}"

# Rename Nuitka's .dist directory to the versioned name
if [[ "${nuitka_dist_dir}" != "${bundle_runtime_dir}" ]]; then
    rm -rf "${bundle_runtime_dir}"
    mv "${nuitka_dist_dir}" "${bundle_runtime_dir}"
fi

mercury_version="$(grep 'define VERSION__' "${mercury_dir_abs}/main.c" | head -1 | sed 's/.*"\(.*\)".*/\1/')"
archive_name="${app_title}-${qt_version}-mercury-${mercury_version}.zip"
archive_path="${bundle_dir_abs}/${archive_name}"

rm -f "${archive_path}"
(
    cd "${bundle_dir_abs}"
    zip -qr "${archive_name}" "$(basename "${bundle_runtime_dir}")"
)

echo "Publish this file: ${archive_path}"
