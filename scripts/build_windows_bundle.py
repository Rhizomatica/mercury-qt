#!/usr/bin/env python3

from __future__ import annotations

import argparse
import configparser
import os
import shlex
import shutil
import subprocess
import sys
import time
from pathlib import Path

APP_TITLE = "mercury-qt"
DEFAULT_DEPLOY_CONFIG = "pyside6-windows.spec"
DEFAULT_NUITKA_PACKAGES = "Nuitka==2.7.11"
DEFAULT_NUITKA_ARGS = [
    "--quiet",
    "--noinclude-qt-translations",
]
WINDOWS_DATA_DIRS = [
    ("assets", "assets"),
    ("apps/mercury_qt/assets", "apps/mercury_qt/assets"),
]
MERCURY_RUNTIME_DLL_SKIP_IF_PRESENT = {"libgcc_s_seh-1.dll"}


def parse_args():
    parser = argparse.ArgumentParser(
        description=(
            "Build a Windows bundle for Mercury QT, optionally driving a Windows "
            "PySide6 toolchain under Wine from Linux."
        )
    )
    parser.add_argument(
        "--bundle-dir",
        type=Path,
        default=Path("deployment"),
        help="Directory that should receive the final Windows bundle.",
    )
    parser.add_argument(
        "--app-title",
        default=APP_TITLE,
        help="Executable name for the generated Windows launcher without the .exe suffix.",
    )
    parser.add_argument(
        "--mercury-dir",
        type=Path,
        default=Path("../mercury"),
        help="Path to the Mercury checkout used for `make windows`.",
    )
    parser.add_argument(
        "--mercury-executable",
        type=Path,
        help="Path to an existing mercury.exe to stage into the bundle.",
    )
    parser.add_argument(
        "--skip-mercury-build",
        action="store_true",
        help="Reuse an existing mercury.exe instead of rebuilding it.",
    )
    parser.add_argument(
        "--skip-deploy",
        action="store_true",
        help="Only build and stage mercury.exe without invoking the GUI bundler.",
    )
    parser.add_argument(
        "--wine-python",
        type=Path,
        help="Path to the Windows python.exe inside the Wine prefix.",
    )
    parser.add_argument(
        "--wine-prefix",
        type=Path,
        help="Optional Wine prefix to use while invoking the Windows toolchain.",
    )
    parser.add_argument(
        "--wine-deploy",
        type=Path,
        help="Override the PySide6 deploy entry point under Wine (deploy.py or .exe).",
    )
    parser.add_argument(
        "--deploy-config",
        type=Path,
        default=Path(DEFAULT_DEPLOY_CONFIG),
        help="Path where the generated Windows-specific pysidedeploy spec is written.",
    )
    parser.add_argument(
        "--nuitka-extra-args",
        default="",
        help="Additional arguments appended to the generated Nuitka extra_args.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the commands and generated config path without running them.",
    )
    parser.add_argument(
        "deploy_args",
        nargs=argparse.REMAINDER,
        help="Additional arguments forwarded to pyside6-deploy. Prefix them with '--'.",
    )
    return parser.parse_args()


def resolve_from_repo(repo_root: Path, path: Path | None) -> Path | None:
    if path is None:
        return None
    expanded = path.expanduser()
    if expanded.is_absolute():
        return expanded.resolve()
    return (repo_root / expanded).resolve()


def normalize_args(forwarded_args: list[str]) -> list[str]:
    if forwarded_args[:1] == ["--"]:
        return forwarded_args[1:]
    return forwarded_args


def build_drive_path(letter: str, parts: tuple[str, ...] | list[str]) -> str:
    joined = "\\".join(parts)
    if not joined:
        return f"{letter.upper()}:\\"
    return f"{letter.upper()}:\\{joined}"


def to_wine_path(path: Path) -> str:
    resolved = path.resolve()
    return "Z:" + str(resolved).replace("/", "\\")


def to_windows_runtime_path(path: Path, wine_prefix: Path | None = None) -> str:
    resolved = path.resolve()

    if wine_prefix is not None:
        prefix = wine_prefix.resolve()
        for drive_dir in prefix.iterdir():
            if not drive_dir.is_dir() or not drive_dir.name.startswith("drive_"):
                continue
            if len(drive_dir.name) != 7:
                continue
            try:
                relative = resolved.relative_to(drive_dir)
            except ValueError:
                continue
            return build_drive_path(drive_dir.name[-1], relative.parts)

    for index, part in enumerate(resolved.parts):
        if part.startswith("drive_") and len(part) == 7:
            return build_drive_path(part[-1], list(resolved.parts[index + 1 :]))

    return to_wine_path(resolved)


def wine_environment(wine_prefix: Path | None = None) -> dict[str, str]:
    env = os.environ.copy()
    env.setdefault("WINEDEBUG", "-all")
    if wine_prefix is not None:
        env["WINEPREFIX"] = str(wine_prefix.resolve())
    return env


def print_command(command: list[str]) -> None:
    print("Command:", shlex.join(command))


def run_command(
    command: list[str],
    *,
    cwd: Path,
    env: dict[str, str] | None = None,
    dry_run: bool = False,
) -> int:
    print_command(command)
    if dry_run:
        return 0
    completed = subprocess.run(command, cwd=cwd, env=env, check=False)
    return completed.returncode


def detect_wine_python_version(
    wine_python: Path,
    wine_prefix: Path | None,
    *,
    dry_run: bool = False,
) -> tuple[int, int]:
    if dry_run:
        return (3, 12)

    command = [
        "wine",
        to_windows_runtime_path(wine_python, wine_prefix),
        "-c",
        "import sys; print(f'{sys.version_info[0]}.{sys.version_info[1]}')",
    ]
    completed = subprocess.run(
        command,
        capture_output=True,
        text=True,
        env=wine_environment(wine_prefix),
        check=False,
    )
    if completed.returncode != 0:
        raise RuntimeError(
            "Unable to query the Wine Python version.\n"
            f"Command: {shlex.join(command)}\n"
            f"stderr: {completed.stderr.strip()}"
        )

    version_text = completed.stdout.strip()
    major, minor = version_text.split(".", maxsplit=1)
    return int(major), int(minor)


def verify_pyside6_runtime(
    repo_root: Path,
    wine_python: Path,
    wine_prefix: Path | None,
    *,
    dry_run: bool = False,
) -> None:
    if dry_run:
        return

    command = [
        "wine",
        to_windows_runtime_path(wine_python, wine_prefix),
        "-c",
        "import windows_bundle_entry; print('windows_bundle_entry ok')",
    ]
    completed = subprocess.run(
        command,
        capture_output=True,
        text=True,
        cwd=repo_root,
        env=wine_environment(wine_prefix),
        check=False,
    )
    if completed.returncode != 0:
        raise RuntimeError(
            "The Wine Python runtime could not import windows_bundle_entry.\n"
            "Run scripts/setup_wine_python.py to provision the Wine prefix with the "
            "required app dependencies, or install the missing packages manually.\n"
            f"Command: {shlex.join(command)}\n"
            f"stderr: {completed.stderr.strip()}"
        )


def infer_wine_deploy(wine_python: Path) -> Path:
    python_dir = wine_python.resolve().parent
    candidates = [
        python_dir / "Lib" / "site-packages" / "PySide6" / "scripts" / "deploy.py",
        python_dir / "Scripts" / "pyside6-deploy.exe",
    ]

    for candidate in candidates:
        if candidate.exists():
            return candidate

    raise FileNotFoundError(
        "Could not find PySide6 deploy tooling next to the Wine Python installation. "
        "Expected either Lib/site-packages/PySide6/scripts/deploy.py or "
        "Scripts/pyside6-deploy.exe."
    )


def infer_pyside_icon(wine_python: Path) -> Path | None:
    candidate = (
        wine_python.resolve().parent
        / "Lib"
        / "site-packages"
        / "PySide6"
        / "scripts"
        / "deploy_lib"
        / "pyside_icon.ico"
    )
    if candidate.exists():
        return candidate
    return None


def get_pyside_package_dir(wine_python: Path) -> Path:
    return (
        wine_python.resolve().parent
        / "Lib"
        / "site-packages"
        / "PySide6"
    )


def collect_wine_support_files(wine_python: Path) -> list[Path]:
    pyside_dir = get_pyside_package_dir(wine_python)

    # MinGW runtime DLLs (always required for the cross-compiled bundle)
    required_files = [
        pyside_dir / "libgcc_s_seh-1.dll",
        pyside_dir / "libstdc++-6.dll",
    ]

    # ICU DLLs: only needed if Qt was built with external ICU (Qt 6.10+).
    # Qt 6.8 LTS uses Windows built-in Unicode support and has no ICU dependency.
    icu_files = [
        pyside_dir / "icuuc.dll",
        pyside_dir / "icuin.dll",
        pyside_dir / "icudt.dll",
        pyside_dir / "icuuc57.dll",
        pyside_dir / "icui18n57.dll",
        pyside_dir / "icudata57.dll",
    ]
    icu_present = [f for f in icu_files if f.exists()]
    if icu_present:
        required_files.extend(icu_present)

    missing = [path.name for path in required_files if not path.exists()]
    if missing:
        raise RuntimeError(
            "The Wine PySide6 runtime is missing support DLLs needed for the Windows bundle: "
            + ", ".join(missing)
        )

    return required_files


def infer_default_spec(wine_python: Path, wine_deploy: Path) -> Path:
    candidates = []
    if wine_deploy.suffix.lower() == ".py":
        candidates.append(wine_deploy.parent / "deploy_lib" / "default.spec")
    candidates.append(
        wine_python.resolve().parent
        / "Lib"
        / "site-packages"
        / "PySide6"
        / "scripts"
        / "deploy_lib"
        / "default.spec"
    )

    for candidate in candidates:
        if candidate.exists():
            return candidate

    raise FileNotFoundError("Could not locate PySide6's default.spec template.")


def build_nuitka_extra_args(
    *,
    wine_python: Path | None,
    wine_prefix: Path | None,
    extra_args: str,
) -> str:
    nuitka_args = list(DEFAULT_NUITKA_ARGS)

    if wine_python is not None:
        wine_python_runtime = to_windows_runtime_path(wine_python, wine_prefix).replace(
            "\\",
            "/",
        )
        nuitka_args.extend(
            [
                "--experimental=force-dependencies-pefile",
                "--mingw64",
                f"--python-for-scons={wine_python_runtime}",
                "--assume-yes-for-downloads",
            ]
        )

    for source_dir, dest_dir in WINDOWS_DATA_DIRS:
        nuitka_args.append(f"--include-data-dir={source_dir}={dest_dir}")

    if extra_args:
        nuitka_args.extend(shlex.split(extra_args))

    return " ".join(nuitka_args)


def write_windows_deploy_config(
    *,
    repo_root: Path,
    entry_file: Path,
    bundle_dir: Path,
    wine_python: Path,
    wine_prefix: Path | None,
    wine_deploy: Path,
    deploy_config: Path,
    app_title: str,
    nuitka_extra_args: str,
    dry_run: bool,
) -> None:
    default_spec = infer_default_spec(wine_python, wine_deploy)
    config = configparser.ConfigParser()
    config.read(default_spec)

    for section in ("app", "python", "qt", "nuitka"):
        if not config.has_section(section):
            config.add_section(section)

    config["app"]["title"] = app_title
    config["app"]["project_dir"] = to_windows_runtime_path(repo_root, wine_prefix)
    config["app"]["input_file"] = to_windows_runtime_path(entry_file, wine_prefix)
    config["app"]["exec_directory"] = to_windows_runtime_path(bundle_dir, wine_prefix)
    config["app"]["icon"] = ""

    config["python"]["python_path"] = to_windows_runtime_path(wine_python, wine_prefix)
    config["python"]["packages"] = DEFAULT_NUITKA_PACKAGES

    config["nuitka"]["mode"] = "onefile"
    config["nuitka"]["extra_args"] = build_nuitka_extra_args(
        wine_python=wine_python,
        wine_prefix=wine_prefix,
        extra_args=nuitka_extra_args,
    )

    print("Generated config:", deploy_config)
    if dry_run:
        return

    deploy_config.parent.mkdir(parents=True, exist_ok=True)
    with deploy_config.open("w", encoding="utf-8") as config_file:
        config.write(config_file)


def build_deploy_command(
    *,
    wine_python: Path | None,
    wine_prefix: Path | None,
    wine_deploy: Path | None,
    deploy_config: Path | None,
    forwarded_args: list[str],
    entry_file: Path,
) -> list[str]:
    if wine_python is None:
        deploy_executable = shutil.which("pyside6-deploy")
        if not deploy_executable:
            raise RuntimeError(
                "pyside6-deploy was not found on PATH. Install PySide6 tooling or "
                "pass --wine-python for the Wine-hosted Windows toolchain."
            )
        return [deploy_executable, str(entry_file)] + forwarded_args

    if wine_deploy is None or deploy_config is None:
        raise RuntimeError("Wine deployment requires both a deploy entry point and config.")

    deploy_runtime = to_windows_runtime_path(wine_deploy, wine_prefix)
    config_runtime = to_windows_runtime_path(deploy_config, wine_prefix)

    if wine_deploy.suffix.lower() == ".py":
        bootstrap = (
            "import runpy, sys; from pathlib import Path; "
            "sys.path.insert(0, str(Path(sys.argv[1]).parent)); "
            "sys.argv = sys.argv[1:]; "
            "runpy.run_path(sys.argv[0], run_name='__main__')"
        )
        return [
            "wine",
            to_windows_runtime_path(wine_python, wine_prefix),
            "-c",
            bootstrap,
            deploy_runtime,
            "-c",
            config_runtime,
            *forwarded_args,
        ]

    return ["wine", deploy_runtime, "-c", config_runtime, *forwarded_args]


def normalize_wine_nuitka_args(forwarded_args: list[str]) -> list[str]:
    normalized = []

    for arg in forwarded_args:
        if arg == "--force":
            normalized.append("--remove-output")
        elif arg == "--keep-deployment-files":
            continue
        else:
            normalized.append(arg)

    return normalized


def build_wine_nuitka_command(
    *,
    entry_file: Path,
    bundle_dir: Path,
    wine_python: Path,
    wine_prefix: Path | None,
    nuitka_extra_args: str,
    forwarded_args: list[str],
) -> list[str]:
    command = [
        "wine",
        to_windows_runtime_path(wine_python, wine_prefix),
        "-m",
        "nuitka",
        to_windows_runtime_path(entry_file, wine_prefix),
        "--follow-imports",
        "--enable-plugin=pyside6",
        f"--output-dir={to_windows_runtime_path(bundle_dir, wine_prefix)}",
        *shlex.split(
            build_nuitka_extra_args(
                wine_python=wine_python,
                wine_prefix=wine_prefix,
                extra_args=nuitka_extra_args,
            )
        ),
        "--standalone",
        "--noinclude-dlls=*.cpp.o",
        "--noinclude-dlls=*.qsb",
        "--include-qt-plugins=networkinformation,platforminputcontexts",
        *normalize_wine_nuitka_args(forwarded_args),
    ]

    for support_file in collect_wine_support_files(wine_python):
        runtime_path = to_windows_runtime_path(support_file, wine_prefix).replace("\\", "/")
        command.append(f"--include-data-file={runtime_path}={support_file.name}")

    icon_path = infer_pyside_icon(wine_python)
    if icon_path is not None:
        command.append(
            f"--windows-icon-from-ico={to_windows_runtime_path(icon_path, wine_prefix).replace('\\', '/')}"
        )

    return command


def stage_mercury_executable(
    mercury_dir: Path,
    mercury_executable: Path,
    bundle_dir: Path,
    *,
    dry_run: bool,
) -> None:
    stage_mercury_runtime(mercury_dir, mercury_executable, bundle_dir, dry_run=dry_run)


def collect_mercury_runtime_dlls(mercury_dir: Path) -> list[Path]:
    runtime_dir = mercury_dir / "radio_io" / "hamlib-w64" / "bin"
    runtime_dlls = sorted(runtime_dir.glob("*.dll"))
    if not runtime_dlls:
        raise FileNotFoundError(
            "Mercury Windows runtime DLLs were not found. "
            f"Expected *.dll under {runtime_dir}. "
            "This should match the files staged by `make windows-zip`."
        )
    return runtime_dlls


def stage_mercury_runtime(
    mercury_dir: Path,
    mercury_executable: Path,
    bundle_dir: Path,
    *,
    dry_run: bool,
) -> None:
    runtime_files = [mercury_executable, *collect_mercury_runtime_dlls(mercury_dir)]
    if dry_run:
        for runtime_file in runtime_files:
            destination = bundle_dir / runtime_file.name
            print(f"Staging Mercury runtime: {runtime_file} -> {destination}")
        return

    bundle_dir.mkdir(parents=True, exist_ok=True)
    for runtime_file in runtime_files:
        destination = bundle_dir / runtime_file.name
        if runtime_file.name in MERCURY_RUNTIME_DLL_SKIP_IF_PRESENT and destination.exists():
            print(f"Keeping existing runtime DLL: {destination}")
            continue
        print(f"Staging Mercury runtime: {runtime_file} -> {destination}")
        shutil.copy2(runtime_file, destination)


def expected_bundle_runtime_dir(
    bundle_dir: Path,
    app_title: str,
    *,
    wine_python: Path | None,
) -> Path:
    if wine_python is None:
        return bundle_dir
    return bundle_dir / f"{app_title}.dist"


def expected_bundle_executable(
    bundle_dir: Path,
    app_title: str,
    *,
    wine_python: Path | None,
) -> Path:
    runtime_dir = expected_bundle_runtime_dir(
        bundle_dir,
        app_title,
        wine_python=wine_python,
    )
    return runtime_dir / f"{app_title}.exe"


def finalize_wine_bundle_output(
    bundle_dir: Path,
    source_stem: str,
    app_title: str,
    *,
    dry_run: bool,
) -> None:
    source_runtime_dir = bundle_dir / f"{source_stem}.dist"
    source_executable = source_runtime_dir / f"{source_stem}.exe"
    target_runtime_dir = bundle_dir / f"{app_title}.dist"
    target_executable = target_runtime_dir / f"{app_title}.exe"

    if dry_run:
        return

    for _ in range(30):
        if source_runtime_dir.exists() and source_executable.exists():
            break
        if target_executable.exists():
            return
        time.sleep(1)
    else:
        return

    renamed_executable = source_runtime_dir / f"{app_title}.exe"
    if source_executable.exists() and source_executable != renamed_executable:
        if renamed_executable.exists():
            renamed_executable.unlink()
        source_executable.replace(renamed_executable)

    if source_runtime_dir != target_runtime_dir:
        if target_runtime_dir.exists():
            shutil.rmtree(target_runtime_dir)
        source_runtime_dir.replace(target_runtime_dir)

    for stale_path in (bundle_dir / f"{app_title}.exe", bundle_dir / "mercury.exe"):
        if stale_path.exists():
            stale_path.unlink()

    # Copy MSVC runtime DLLs from subdirectories (shiboken6/, PySide6/, etc.) to
    # the bundle root so that all modules can find them.  Nuitka places some MSVC
    # DLLs only next to the shiboken6 bindings, but Qt6Core.dll in the root also
    # needs them.  Wine provides these built-in; real Windows does not.
    promote_msvc_runtime_dlls(target_runtime_dir)


MSVC_RUNTIME_PATTERNS = (
    "msvcp140*.dll",
    "vcruntime140*.dll",
    "concrt140*.dll",
    "ucrtbase*.dll",
)


def promote_msvc_runtime_dlls(runtime_dir: Path) -> None:
    """Copy MSVC runtime DLLs from PySide6/shiboken6 subdirectories to the
    bundle root.  PySide6's copies must win because they match the Visual
    Studio version that Qt and the PySide6 bindings were built with.  Nuitka
    may have already placed CPython's copies (a different VS version) in the
    root, so we overwrite unconditionally."""
    if not runtime_dir.is_dir():
        return
    for pattern in MSVC_RUNTIME_PATTERNS:
        for dll in runtime_dir.rglob(pattern):
            if dll.parent == runtime_dir:
                continue
            target = runtime_dir / dll.name
            if target.exists() and target.stat().st_size != dll.stat().st_size:
                print(f"Replacing MSVC runtime DLL: {dll.relative_to(runtime_dir)} -> {dll.name} "
                      f"(root={target.stat().st_size}B, pyside={dll.stat().st_size}B)")
            elif not target.exists():
                print(f"Promoting MSVC runtime DLL: {dll.relative_to(runtime_dir)} -> {dll.name}")
            else:
                continue
            shutil.copy2(dll, target)


def main():
    args = parse_args()
    repo_root = Path(__file__).resolve().parent.parent
    entry_file = repo_root / "windows_bundle_entry.py"

    if not entry_file.exists():
        raise FileNotFoundError(f"Windows entry file not found: {entry_file}")

    bundle_dir = resolve_from_repo(repo_root, args.bundle_dir)
    mercury_dir = resolve_from_repo(repo_root, args.mercury_dir)
    mercury_executable = resolve_from_repo(
        repo_root,
        args.mercury_executable or args.mercury_dir / "mercury.exe",
    )
    wine_prefix = resolve_from_repo(repo_root, args.wine_prefix)
    wine_python = resolve_from_repo(repo_root, args.wine_python)
    deploy_config = resolve_from_repo(repo_root, args.deploy_config)
    forwarded_args = normalize_args(list(args.deploy_args))
    bundle_runtime_dir = expected_bundle_runtime_dir(
        bundle_dir,
        args.app_title,
        wine_python=wine_python,
    )

    wine_deploy = None
    deploy_command: list[str] | None = None
    if not args.skip_deploy:
        if wine_python is not None:
            python_version = detect_wine_python_version(
                wine_python,
                wine_prefix,
                dry_run=args.dry_run,
            )
            if python_version >= (3, 13):
                raise RuntimeError(
                    "The Wine cross-build helper currently supports Windows Python 3.12.x. "
                    "PySide6's pinned Nuitka flow loses --mingw64 on Python 3.13+ and the "
                    "Python 3.14 Zig path currently fails under Wine in this environment."
                )
            verify_pyside6_runtime(
                repo_root,
                wine_python,
                wine_prefix,
                dry_run=args.dry_run,
            )
            deploy_command = build_wine_nuitka_command(
                entry_file=entry_file,
                bundle_dir=bundle_dir,
                wine_python=wine_python,
                wine_prefix=wine_prefix,
                nuitka_extra_args=args.nuitka_extra_args,
                forwarded_args=forwarded_args,
            )
        elif sys.platform != "win32":
            raise RuntimeError(
                "On Linux, pass --wine-python pointing at the Windows python.exe inside a "
                "Wine prefix so pyside6-deploy can run under Wine."
            )
        else:
            deploy_command = build_deploy_command(
                wine_python=wine_python,
                wine_prefix=wine_prefix,
                wine_deploy=wine_deploy,
                deploy_config=deploy_config if wine_python is not None else None,
                forwarded_args=forwarded_args,
                entry_file=entry_file,
            )

    print("Repository root:", repo_root)
    print("Bundle directory:", bundle_dir)
    print("Mercury checkout:", mercury_dir)
    if wine_python is not None:
        print("Wine Python:", wine_python)
        if wine_prefix is not None:
            print("Wine prefix:", wine_prefix)

    if not args.skip_mercury_build:
        mercury_build_command = ["make", "windows"]
        build_status = run_command(
            mercury_build_command,
            cwd=mercury_dir,
            dry_run=args.dry_run,
        )
        if build_status != 0:
            return build_status

    if not args.dry_run and not mercury_executable.exists():
        raise FileNotFoundError(f"Mercury executable not found: {mercury_executable}")

    deploy_status = 0
    if not args.skip_deploy:
        deploy_status = run_command(
            deploy_command,
            cwd=repo_root,
            env=wine_environment(wine_prefix) if wine_python is not None else None,
            dry_run=args.dry_run,
        )

    if wine_python is not None and deploy_status == 0:
        finalize_wine_bundle_output(
            bundle_dir,
            entry_file.stem,
            args.app_title,
            dry_run=args.dry_run,
        )

    stage_mercury_executable(
        mercury_dir,
        mercury_executable,
        bundle_runtime_dir,
        dry_run=args.dry_run,
    )
    if not args.skip_deploy and not args.dry_run:
        bundle_executable = expected_bundle_executable(
            bundle_dir,
            args.app_title,
            wine_python=wine_python,
        )
        if not bundle_executable.exists():
            print(f"Expected bundle executable was not created: {bundle_executable}")
            return deploy_status or 1
    return deploy_status


if __name__ == "__main__":
    raise SystemExit(main())
