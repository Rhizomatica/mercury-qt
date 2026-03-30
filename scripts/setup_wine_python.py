#!/usr/bin/env python3

from __future__ import annotations

import argparse
import os
import shlex
import shutil
import subprocess
import tarfile
import tempfile
import urllib.request
from pathlib import Path

DEFAULT_TARGET_DIR = r"C:\Python312"
DEFAULT_PACKAGES = [
    "PySide6==6.8.3",
    "numpy",
    "ordered-set",
    "packaging",
    "setuptools",
    "websockets",
    "wheel",
    "zstandard",
    "Nuitka==2.7.11",
]
CYGWIN_SETUP_INI = (
    "https://ftp-stud.hs-esslingen.de/pub/Mirrors/sources.redhat.com/cygwin/x86_64/setup.ini"
)
CYGWIN_BASE_URL = "https://ftp-stud.hs-esslingen.de/pub/Mirrors/sources.redhat.com/cygwin/"
CYGWIN_ICU_PACKAGE = "@ mingw64-x86_64-icu"
ICU_DLLS = {
    "icudata57.dll": "icudt.dll",
    "icui18n57.dll": "icuin.dll",
    "icuuc57.dll": "icuuc.dll",
}
MINGW_RUNTIME_DLLS = [
    "libgcc_s_seh-1.dll",
    "libstdc++-6.dll",
]


def parse_args():
    parser = argparse.ArgumentParser(
        description="Install a Windows Python 3.12 + PySide6 + Nuitka toolchain under Wine."
    )
    parser.add_argument(
        "installer",
        type=Path,
        help="Path to the official python-3.12.x-amd64.exe installer.",
    )
    parser.add_argument(
        "--wine-prefix",
        type=Path,
        required=True,
        help="Wine prefix that should hold the Windows Python installation.",
    )
    parser.add_argument(
        "--target-dir",
        default=DEFAULT_TARGET_DIR,
        help=r"Windows target directory passed to the installer, e.g. C:\Python312.",
    )
    parser.add_argument(
        "--wheelhouse",
        type=Path,
        help="Optional host directory of pre-downloaded Windows wheels.",
    )
    parser.add_argument(
        "--package",
        dest="packages",
        action="append",
        help="Additional package to install with pip. Can be passed multiple times.",
    )
    parser.add_argument(
        "--reset-prefix",
        action="store_true",
        help="Remove the target Wine prefix before installing.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the commands without running them.",
    )
    parser.add_argument(
        "--skip-cygwin-icu",
        action="store_true",
        default=True,
        help="Skip staging ICU DLLs from the Cygwin mingw64-x86_64-icu package (default: skip).",
    )
    parser.add_argument(
        "--cygwin-icu",
        action="store_false",
        dest="skip_cygwin_icu",
        help="Stage ICU DLLs from Cygwin (needed for PySide6 6.10+ / Qt 6.10+).",
    )
    return parser.parse_args()


def to_wine_path(path: Path) -> str:
    resolved = path.resolve()
    return "Z:" + str(resolved).replace("/", "\\")


def windows_dir_to_host(wine_prefix: Path, windows_dir: str) -> Path:
    if len(windows_dir) < 3 or windows_dir[1:3] != ":\\":
        raise ValueError(f"Unsupported Windows directory: {windows_dir}")

    drive_letter = windows_dir[0].lower()
    relative = windows_dir[3:].replace("\\", "/").strip("/")
    host_path = wine_prefix / f"drive_{drive_letter}"
    if relative:
        host_path = host_path / relative
    return host_path


def wine_environment(wine_prefix: Path) -> dict[str, str]:
    env = os.environ.copy()
    env.setdefault("WINEDEBUG", "-all")
    env["WINEPREFIX"] = str(wine_prefix.resolve())
    return env


def run_command(
    command: list[str],
    *,
    env: dict[str, str],
    cwd: Path,
    dry_run: bool,
) -> int:
    print("Command:", shlex.join(command))
    if dry_run:
        return 0
    completed = subprocess.run(command, cwd=cwd, env=env, check=False)
    return completed.returncode


def fetch_cygwin_icu_archive_url() -> str:
    text = urllib.request.urlopen(CYGWIN_SETUP_INI, timeout=60).read().decode(
        "utf-8",
        "replace",
    )
    in_package = False
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if line.startswith("@ "):
            in_package = line == CYGWIN_ICU_PACKAGE
            continue
        if in_package and line.startswith("install: "):
            archive_path = line.split()[1]
            return CYGWIN_BASE_URL + archive_path

    raise RuntimeError(f"Unable to locate {CYGWIN_ICU_PACKAGE} in Cygwin setup.ini")


def find_mingw_runtime_dll(dll_name: str) -> Path:
    search_root = Path("/usr/lib/gcc/x86_64-w64-mingw32")
    if not search_root.exists():
        raise FileNotFoundError(
            "MinGW runtime directory not found under /usr/lib/gcc/x86_64-w64-mingw32"
        )

    candidates = sorted(search_root.glob(f"*/{dll_name}"))
    if not candidates:
        raise FileNotFoundError(f"Unable to find host MinGW runtime DLL: {dll_name}")

    for candidate in candidates:
        if "win32" in candidate.parts[-2]:
            return candidate
    return candidates[0]


def stage_cygwin_icu_runtime(pyside_dir: Path, *, dry_run: bool) -> None:
    archive_url = fetch_cygwin_icu_archive_url()
    print("Cygwin ICU archive:", archive_url)

    if dry_run:
        return

    pyside_dir.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="cygwin-icu-") as temp_dir:
        temp_path = Path(temp_dir)
        archive_path = temp_path / "mingw64-x86_64-icu.tar.xz"
        urllib.request.urlretrieve(archive_url, archive_path)

        with tarfile.open(archive_path) as archive:
            members = {
                Path(member.name).name: member
                for member in archive.getmembers()
                if Path(member.name).name in ICU_DLLS
            }

            missing = sorted(set(ICU_DLLS) - set(members))
            if missing:
                raise RuntimeError(
                    "Cygwin ICU archive is missing expected DLLs: "
                    + ", ".join(missing)
                )

            for dll_name, alias_name in ICU_DLLS.items():
                member = members[dll_name]
                extracted = archive.extractfile(member)
                if extracted is None:
                    raise RuntimeError(f"Unable to extract {dll_name} from Cygwin ICU archive")

                dll_bytes = extracted.read()
                (pyside_dir / dll_name).write_bytes(dll_bytes)
                (pyside_dir / alias_name).write_bytes(dll_bytes)

    for runtime_dll in MINGW_RUNTIME_DLLS:
        runtime_path = find_mingw_runtime_dll(runtime_dll)
        shutil.copy2(runtime_path, pyside_dir / runtime_dll)

    print("Staged ICU runtime into:", pyside_dir)


def main():
    args = parse_args()
    repo_root = Path(__file__).resolve().parent.parent
    installer = args.installer.expanduser().resolve()
    wine_prefix = args.wine_prefix.expanduser().resolve()
    wheelhouse = args.wheelhouse.expanduser().resolve() if args.wheelhouse else None

    if not installer.exists():
        raise FileNotFoundError(f"Installer not found: {installer}")

    if args.reset_prefix and not args.dry_run and wine_prefix.exists():
        shutil.rmtree(wine_prefix)

    packages = list(DEFAULT_PACKAGES)
    if args.packages:
        packages.extend(args.packages)

    env = wine_environment(wine_prefix)
    installer_command = [
        "wine",
        str(installer),
        "/quiet",
        "InstallAllUsers=0",
        f"TargetDir={args.target_dir}",
        "Include_dev=1",
        "Include_pip=1",
        "Include_test=0",
        "Include_launcher=0",
        "Include_tcltk=0",
        "SimpleInstall=1",
    ]

    print("Wine prefix:", wine_prefix)
    print("Windows target dir:", args.target_dir)

    install_status = run_command(
        installer_command,
        env=env,
        cwd=repo_root,
        dry_run=args.dry_run,
    )
    if install_status != 0:
        return install_status

    python_host = windows_dir_to_host(wine_prefix, args.target_dir) / "python.exe"
    python_runtime = args.target_dir.rstrip("\\") + r"\python.exe"
    pyside_dir = python_host.parent / "Lib" / "site-packages" / "PySide6"

    pip_command = [
        "wine",
        python_runtime,
        "-m",
        "pip",
        "install",
        "--prefer-binary",
    ]
    if wheelhouse is not None:
        pip_command.extend(["--find-links", to_wine_path(wheelhouse)])
    pip_command.extend(packages)

    pip_status = run_command(
        pip_command,
        env=env,
        cwd=repo_root,
        dry_run=args.dry_run,
    )
    if pip_status != 0:
        return pip_status

    if not args.skip_cygwin_icu:
        stage_cygwin_icu_runtime(pyside_dir, dry_run=args.dry_run)

    verify_command = [
        "wine",
        python_runtime,
        "-c",
        "import sys; import PySide6; import nuitka; from PySide6 import QtWidgets; "
        "print(sys.version); print('PySide6', PySide6.__version__); "
        "print('Nuitka', nuitka.__version__); print('QtWidgets', QtWidgets.__name__)",
    ]
    verify_status = run_command(
        verify_command,
        env=env,
        cwd=repo_root,
        dry_run=args.dry_run,
    )
    if verify_status != 0:
        return verify_status

    print()
    print("Wine Python ready at:", python_host)
    print("Suggested bundle command:")
    print(
        " ".join(
            [
                "python3",
                "scripts/build_windows_bundle.py",
                f"--wine-python {python_host}",
                f"--wine-prefix {wine_prefix}",
                "-- --force --keep-deployment-files",
            ]
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
