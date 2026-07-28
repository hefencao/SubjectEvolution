#!/usr/bin/env python3
"""Run editable-install verification and the full test suite concurrently."""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import subprocess
import sys


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", default=".")
    parser.add_argument("--shards", type=int, default=5)
    parser.add_argument("--docs-dir", required=True)
    args = parser.parse_args()
    project = Path(args.project).resolve()
    docs = (project / args.docs_dir).resolve()
    docs.mkdir(parents=True, exist_ok=True)
    commands = [
        [
            sys.executable,
            "scripts/run_test_shards.py",
            "--project",
            ".",
            "--shards",
            str(args.shards),
            "--report",
            str(docs / "FINAL_TEST_REPORT.json"),
        ],
        [
            sys.executable,
            "scripts/verify_conda_editable.py",
            "--project",
            ".",
            "--require-conda",
            "--smoke",
            "--report",
            str(docs / "CONDA_EDITABLE_VALIDATION_REPORT.json"),
        ],
    ]
    processes = [
        subprocess.Popen(
            command,
            cwd=project,
            env=os.environ.copy(),
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
        for command in commands
    ]
    failed = False
    labels = ("full tests", "editable verification")
    for label, command, process in zip(labels, commands, processes, strict=True):
        stdout, _ = process.communicate()
        print(f"\n===== {label} =====")
        print(stdout, end="" if stdout.endswith("\n") else "\n")
        if process.returncode != 0:
            failed = True
            print(f"FAILED: {' '.join(command)}", file=sys.stderr)
    raise SystemExit(1 if failed else 0)


if __name__ == "__main__":
    main()
