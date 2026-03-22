#!/usr/bin/env bash

set -euo pipefail

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(cd -- "${script_dir}/.." && pwd)"

bundle_dir="${MERCURY_QT_BUNDLE_DIR:-${repo_root}/deployment}"
mercury_dir="${MERCURY_QT_MERCURY_DIR:-${repo_root}/../mercury}"
wine_prefix="${MERCURY_QT_WINE_PREFIX:-${WINEPREFIX:-${repo_root}/../wine-python312}}"
wine_python="${MERCURY_QT_WINE_PYTHON:-${wine_prefix}/drive_c/Python312/python.exe}"
app_title="${MERCURY_QT_APP_TITLE:-mercury-qt}"

resolve_path() {
    local path="$1"

    if [[ "${path}" = /* ]]; then
        printf '%s\n' "${path}"
        return
    fi

    printf '%s\n' "${repo_root}/${path}"
}

git_short_hash() {
    local checkout_dir="$1"
    local checkout_name="$2"
    local hash

    if ! hash="$(git -C "${checkout_dir}" rev-parse --short=8 HEAD 2>/dev/null)"; then
        echo "Expected ${checkout_name} git checkout at ${checkout_dir}" >&2
        exit 1
    fi

    printf '%s\n' "${hash}"
}

effective_bundle_dir="${bundle_dir}"
effective_mercury_dir="${mercury_dir}"
effective_app_title="${app_title}"

args=("$@")
arg_index=0
while ((arg_index < ${#args[@]})); do
    case "${args[arg_index]}" in
        --)
            break
            ;;
        --bundle-dir)
            arg_index=$((arg_index + 1))
            if ((arg_index >= ${#args[@]})); then
                echo "Missing value for --bundle-dir" >&2
                exit 1
            fi
            effective_bundle_dir="${args[arg_index]}"
            ;;
        --bundle-dir=*)
            effective_bundle_dir="${args[arg_index]#*=}"
            ;;
        --mercury-dir)
            arg_index=$((arg_index + 1))
            if ((arg_index >= ${#args[@]})); then
                echo "Missing value for --mercury-dir" >&2
                exit 1
            fi
            effective_mercury_dir="${args[arg_index]}"
            ;;
        --mercury-dir=*)
            effective_mercury_dir="${args[arg_index]#*=}"
            ;;
        --app-title)
            arg_index=$((arg_index + 1))
            if ((arg_index >= ${#args[@]})); then
                echo "Missing value for --app-title" >&2
                exit 1
            fi
            effective_app_title="${args[arg_index]}"
            ;;
        --app-title=*)
            effective_app_title="${args[arg_index]#*=}"
            ;;
    esac

    arg_index=$((arg_index + 1))
done

bundle_dir_abs="$(resolve_path "${effective_bundle_dir}")"
mercury_dir_abs="$(resolve_path "${effective_mercury_dir}")"
# Nuitka output directory (used by the Python helper)
nuitka_dist_dir="${bundle_dir_abs}/${effective_app_title}.dist"
bundle_executable="${nuitka_dist_dir}/${effective_app_title}.exe"
bundle_mercury="${nuitka_dist_dir}/mercury.exe"

# Extract version from debian/changelog for the final directory name
qt_version="$(head -1 "${repo_root}/debian/changelog" | sed 's/.*(\(.*\)).*/\1/')"
bundle_runtime_dir="${bundle_dir_abs}/${effective_app_title}-${qt_version}"

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
  app title:    ${app_title}

Environment overrides:
  MERCURY_QT_BUNDLE_DIR
  MERCURY_QT_MERCURY_DIR
  MERCURY_QT_WINE_PREFIX
  MERCURY_QT_WINE_PYTHON
  MERCURY_QT_APP_TITLE
  WINEPREFIX

Examples:
  $(basename "$0") -- --force --keep-deployment-files
  MERCURY_QT_WINE_PREFIX=/path/to/wine-python312 \\
    $(basename "$0") --skip-mercury-build -- --force

This wrapper reuses scripts/build_windows_bundle.py, so any extra arguments are
forwarded to that helper unchanged. Provision the Wine prefix first with:
  python3 scripts/setup_wine_python.py /path/to/python-3.12.x-amd64.exe --wine-prefix /path/to/wine-python312

On success the wrapper creates a publishable zip archive in the bundle
directory named like:
  mercury-qt-windows-gui-<gui_hash>-mercury-<mercury_hash>.zip
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

if ! command -v zip >/dev/null 2>&1; then
    echo "Missing required tool: zip" >&2
    exit 1
fi

cmd=(
    python3
    "${build_script}"
    --bundle-dir "${bundle_dir}"
    --mercury-dir "${mercury_dir}"
    --wine-prefix "${wine_prefix}"
    --wine-python "${wine_python}"
    "${args[@]}"
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

# Rename Nuitka's .dist directory to the versioned name
if [[ "${nuitka_dist_dir}" != "${bundle_runtime_dir}" ]]; then
    rm -rf "${bundle_runtime_dir}"
    mv "${nuitka_dist_dir}" "${bundle_runtime_dir}"
fi

mercury_version="$(grep 'define VERSION__' "${mercury_dir_abs}/main.c" | head -1 | sed 's/.*"\(.*\)".*/\1/')"
archive_name="${effective_app_title}-${qt_version}-mercury-${mercury_version}.zip"
archive_path="${bundle_dir_abs}/${archive_name}"

rm -f "${archive_path}"
(
    cd "${bundle_dir_abs}"
    zip -qr "${archive_name}" "$(basename "${bundle_runtime_dir}")"
)

echo "Publish this file: ${archive_path}"
