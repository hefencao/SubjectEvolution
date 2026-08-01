#!/usr/bin/env python3
"""Verify size and SHA-256 entries in a frozen evidence lock."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


def verify_lock(lock_path: str | Path, *, project_root: str | Path = ".") -> dict[str, Any]:
    root = Path(project_root).resolve()
    lock = Path(lock_path).resolve()
    payload = json.loads(lock.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("frozen evidence lock must be a JSON object")
    files = payload.get("files")
    if not isinstance(files, list) or not files:
        raise ValueError("frozen evidence lock must contain a non-empty files list")

    checked: list[dict[str, Any]] = []
    failures: list[str] = []
    for row in files:
        if not isinstance(row, dict):
            raise ValueError("frozen evidence file entries must be JSON objects")
        relative = Path(str(row.get("path", "")))
        if relative.is_absolute() or ".." in relative.parts:
            raise ValueError(f"unsafe frozen evidence path: {relative}")
        path = (root / relative).resolve()
        try:
            path.relative_to(root)
        except ValueError as exc:
            raise ValueError(f"frozen evidence path escapes project root: {relative}") from exc
        expected_size = int(row.get("size", -1))
        expected_sha = str(row.get("sha256", ""))
        if not path.is_file():
            failures.append(f"missing:{relative.as_posix()}")
            continue
        data = path.read_bytes()
        actual_sha = hashlib.sha256(data).hexdigest()
        if len(data) != expected_size:
            failures.append(
                f"size:{relative.as_posix()}:{len(data)}!={expected_size}"
            )
        if actual_sha != expected_sha:
            failures.append(
                f"sha256:{relative.as_posix()}:{actual_sha}!={expected_sha}"
            )
        checked.append(
            {
                "path": relative.as_posix(),
                "size": len(data),
                "sha256": actual_sha,
            }
        )
    try:
        lock_label = lock.relative_to(root).as_posix()
    except ValueError:
        lock_label = str(lock)
    report = {
        "schema": "frozen-file-verification-v1",
        "lock": lock_label,
        "checked_file_count": len(checked),
        "passed": not failures,
        "failures": failures,
        "files": checked,
    }
    if failures:
        raise RuntimeError(json.dumps(report, ensure_ascii=False, indent=2))
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--lock", required=True)
    parser.add_argument("--project-root", default=".")
    parser.add_argument("--output")
    args = parser.parse_args()
    report = verify_lock(args.lock, project_root=args.project_root)
    if args.output:
        destination = Path(args.output)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(
            json.dumps(report, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
