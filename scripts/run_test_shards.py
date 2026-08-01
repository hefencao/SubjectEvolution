#!/usr/bin/env python3
"""Run the complete pytest file set in deterministic isolated subprocesses."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time

try:
    from .source_fingerprint import source_tree_fingerprint
except ImportError:  # direct script execution
    from source_fingerprint import source_tree_fingerprint


def run(project: Path, shards: int, report: Path | None) -> int:
    project = project.resolve()
    files = sorted((project / "tests").glob("test_*.py"))
    if not files:
        raise RuntimeError("no tests/test_*.py files found")
    shard_count = max(1, min(int(shards), len(files)))
    groups = [files[index::shard_count] for index in range(shard_count)]
    started = time.perf_counter()
    results: list[dict[str, object]] = []
    passed = True
    # Do not keep multiple concurrent pytest processes connected to unread
    # PIPEs. A verbose shard can fill its pipe while the parent waits for an
    # earlier shard, deadlocking the complete release gate. Per-shard files
    # preserve concurrent execution without a bounded pipe buffer.
    with tempfile.TemporaryDirectory(prefix="se-test-shards-") as temporary:
        log_dir = Path(temporary)
        processes: list[tuple[int, list[Path], Path, subprocess.Popen[bytes]]] = []
        for index, group in enumerate(groups):
            command = [sys.executable, "-m", "pytest", "-q", *map(str, group)]
            log_path = log_dir / f"shard-{index + 1}.log"
            with log_path.open("wb") as stream:
                process = subprocess.Popen(
                    command,
                    cwd=project,
                    env=os.environ.copy(),
                    stdout=stream,
                    stderr=subprocess.STDOUT,
                )
            processes.append((index, group, log_path, process))

        for index, group, log_path, process in processes:
            returncode = process.wait()
            stdout = log_path.read_text(encoding="utf-8", errors="replace")
            print(f"\n===== pytest shard {index + 1}/{shard_count} =====")
            print(stdout, end="" if stdout.endswith("\n") else "\n")
            if returncode != 0:
                passed = False
            results.append(
                {
                    "shard": index + 1,
                    "returncode": returncode,
                    "test_file_count": len(group),
                    "test_files": [str(path.relative_to(project)) for path in group],
                    "stdout_tail": stdout.splitlines()[-8:],
                }
            )
    payload = {
        "passed": passed,
        "schema": "deterministic-pytest-file-shards-v1",
        "source_tree_sha256": source_tree_fingerprint(project),
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
