#!/usr/bin/env python3
"""Prune old iteration notes from a release-tree copy only.

Local checkouts may retain every file under ``docs/迭代``.  Release packaging
calls this script on a disposable copy and keeps only the requested version;
normal version checks and ``conda-sync`` never inspect or delete local history.
"""
from __future__ import annotations
import argparse
from pathlib import Path


def prune(project: Path, version: str) -> list[str]:
    root = project / "docs" / "迭代"
    if not root.exists():
        return []
    prefix = f"v{version}_"
    removed: list[str] = []
    for path in sorted(root.iterdir()):
        if path.is_file() and not path.name.startswith(prefix):
            removed.append(path.relative_to(project).as_posix())
            path.unlink()
    return removed


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project", default=".")
    parser.add_argument("--version", required=True)
    args = parser.parse_args()
    removed = prune(Path(args.project), args.version)
    print("\n".join(removed))

if __name__ == "__main__":
    main()
