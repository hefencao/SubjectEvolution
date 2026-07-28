#!/usr/bin/env python3
"""Run the complete pytest file set in deterministic isolated subprocesses."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time


def run(project: Path, shards: int, report: Path | None) -> int:
    project = project.resolve()
    files = sorted((project / "tests").glob("test_*.py"))
    if not files:
        raise RuntimeError("no tests/test_*.py files found")
    shard_count = max(1, min(int(shards), len(files)))
    groups = [files[index::shard_count] for index in range(shard_count)]
    started = time.perf_counter()
    processes: list[tuple[int, list[Path], subprocess.Popen[str]]] = []
    for index, group in enumerate(groups):
        command = [sys.executable, "-m", "pytest", "-q", *map(str, group)]
        process = subprocess.Popen(
            command,
            cwd=project,
            env=os.environ.copy(),
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
        processes.append((index, group, process))

    results: list[dict[str, object]] = []
    passed = True
    for index, group, process in processes:
        stdout, _ = process.communicate()
        print(f"\n===== pytest shard {index + 1}/{shard_count} =====")
        print(stdout, end="" if stdout.endswith("\n") else "\n")
        if process.returncode != 0:
            passed = False
        results.append(
            {
                "shard": index + 1,
                "returncode": process.returncode,
                "test_file_count": len(group),
                "test_files": [str(path.relative_to(project)) for path in group],
                "stdout_tail": stdout.splitlines()[-8:],
            }
        )
    digest = hashlib.sha256()
    fingerprint_paths = [project / "Makefile", project / "pyproject.toml"]
    for root_name in ("src", "scripts", "tests", "configs"):
        fingerprint_paths.extend(sorted((project / root_name).rglob("*")))
    for path in fingerprint_paths:
        if not path.is_file() or "__pycache__" in path.parts:
            continue
        digest.update(str(path.relative_to(project)).encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    payload = {
        "passed": passed,
        "schema": "deterministic-pytest-file-shards-v1",
        "source_tree_sha256": digest.hexdigest(),
        "python": sys.executable,
        "shard_count": shard_count,
        "test_file_count": len(files),
        "elapsed_seconds": time.perf_counter() - started,
        "shards": results,
    }
    print(json.dumps(payload, ensure_ascii=False))
    if report is not None:
        report.parent.mkdir(parents=True, exist_ok=True)
        report.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return 0 if passed else 1


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", default=".")
    parser.add_argument("--shards", type=int, default=3)
    parser.add_argument("--report")
    args = parser.parse_args()
    raise SystemExit(
        run(
            Path(args.project),
            args.shards,
            Path(args.report) if args.report else None,
        )
    )


if __name__ == "__main__":
    main()
