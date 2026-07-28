#!/usr/bin/env python3
"""Remove project-local Python bytecode that can shadow edited source.

Timestamp-based ``.pyc`` files are considered valid when the source size and
integer-second modification time match.  Version-only edits such as 0.53.0 ->
0.55.0 preserve file length, and patch/extraction workflows can also preserve
the same mtime.  In that case Python may execute stale bytecode while reporting
the current ``__file__`` path.  Editable installation should therefore clear
source bytecode before verifying the checkout.
"""
from __future__ import annotations

import argparse
import importlib
import json
import shutil
from pathlib import Path


def clean(project: Path) -> dict[str, object]:
    project = project.resolve()
    roots = [project / "src", project / "scripts", project / "tests"]
    removed_dirs: list[str] = []
    removed_files: list[str] = []
    for root in roots:
        if not root.exists():
            continue
        for cache in sorted(root.rglob("__pycache__"), reverse=True):
            if cache.is_dir():
                removed_dirs.append(str(cache.relative_to(project)))
                shutil.rmtree(cache)
        for pattern in ("*.pyc", "*.pyo"):
            for compiled in root.rglob(pattern):
                if compiled.is_file():
                    removed_files.append(str(compiled.relative_to(project)))
                    compiled.unlink()
    importlib.invalidate_caches()
    return {
        "passed": True,
        "project": str(project),
        "removed_cache_directories": len(removed_dirs),
        "removed_compiled_files": len(removed_files),
        "removed_paths": removed_dirs + removed_files,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project", default=".")
    parser.add_argument("--report")
    args = parser.parse_args()
    report = clean(Path(args.project))
    text = json.dumps(report, ensure_ascii=False, indent=2)
    if args.report:
        Path(args.report).write_text(text + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False))


if __name__ == "__main__":
    main()
