#!/usr/bin/env python3

import argparse
import shutil
import subprocess
import sys
from pathlib import Path


def parse_args():
    parser = argparse.ArgumentParser(
        description="Build a Windows bundle for Mercury QT with pyside6-deploy."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the pyside6-deploy command without running it.",
    )
    parser.add_argument(
        "deploy_args",
        nargs=argparse.REMAINDER,
        help="Additional arguments forwarded to pyside6-deploy. Prefix them with '--'.",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    repo_root = Path(__file__).resolve().parent.parent
    entry_file = repo_root / "windows_bundle_entry.py"

    if not entry_file.exists():
        raise FileNotFoundError(f"Windows entry file not found: {entry_file}")

    deploy_executable = shutil.which("pyside6-deploy")
    if not deploy_executable:
        raise RuntimeError(
            "pyside6-deploy was not found on PATH. Install PySide6 tooling before bundling."
        )

    forwarded_args = list(args.deploy_args)
    if forwarded_args[:1] == ["--"]:
        forwarded_args = forwarded_args[1:]

    command = [deploy_executable, str(entry_file)] + forwarded_args

    if sys.platform != "win32":
        print("Warning: this script is intended to produce a Windows bundle on Windows.")

    print("Running from:", repo_root)
    print("Command:", " ".join(command))
    print(
        "Note: the first run generates pysidedeploy.spec in the repository root; "
        "subsequent runs reuse it."
    )

    if args.dry_run:
        return 0

    completed = subprocess.run(command, cwd=repo_root, check=False)
    return completed.returncode


if __name__ == "__main__":
    raise SystemExit(main())
