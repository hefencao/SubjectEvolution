#!/usr/bin/env python3
"""Build a clean deterministic project archive from a disposable tree.

Local iteration history is never inspected or deleted in place.  The archive
copy keeps only the current version note under ``docs/迭代`` and excludes
runtime/build/cache state.
"""
from __future__ import annotations

import argparse
import fnmatch
import json
from pathlib import Path
import shutil
import stat
import tempfile
import tomllib
import zipfile



def _prune_iteration_docs(project: Path, version: str) -> list[str]:
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

EXCLUDED_DIR_NAMES = {
    ".git", ".hg", ".svn", ".validation", "__pycache__", ".pytest_cache",
    "build", "dist", ".release-env",
}
EXCLUDED_FILE_PATTERNS = ("*.pyc", "*.pyo", "*.egg-info", "*.zip", "*.patch")


def _copy_project(source: Path, destination: Path) -> None:
    def ignore(directory: str, names: list[str]) -> set[str]:
        base = Path(directory)
        excluded: set[str] = set()
        for name in names:
            path = base / name
            if name in EXCLUDED_DIR_NAMES or name.endswith(".egg-info"):
                excluded.add(name)
            elif any(fnmatch.fnmatch(name, pattern) for pattern in EXCLUDED_FILE_PATTERNS):
                excluded.add(name)
            elif path.is_dir() and base == source and name in {"runs", "analyses"}:
                # Keep the directory role README only; runtime results belong in result bundles.
                pass
        return excluded
    shutil.copytree(source, destination, ignore=ignore)
    for role in ("runs", "analyses"):
        root = destination / role
        if root.exists():
            for path in sorted(root.iterdir()):
                if path.name != "README.md":
                    if path.is_dir():
                        shutil.rmtree(path)
                    else:
                        path.unlink()
    state = destination / "state"
    if state.exists():
        for path in sorted(state.rglob("*"), reverse=True):
            if path.is_file() and path.name != "README.md":
                path.unlink()
            elif path.is_dir() and not any(path.iterdir()):
                path.rmdir()


def build_archive(project: Path, output: Path) -> dict[str, object]:
    project = project.resolve()
    metadata = tomllib.loads((project / "pyproject.toml").read_text(encoding="utf-8"))
    version = str(metadata["project"]["version"])
    major, minor, *_ = version.split(".")
    iteration_version = f"{major}.{minor}"
    output = output.resolve()
    with tempfile.TemporaryDirectory(prefix="se-project-archive-") as temp_name:
        temp = Path(temp_name)
        archive_root = temp / f"se_v{major}{minor.replace('.', '')}_project"
        # Preserve the established user-facing root naming with zero-padded minor.
        archive_root = temp / f"se_v{int(major):01d}{int(minor):02d}_project"
        _copy_project(project, archive_root)
        removed = _prune_iteration_docs(archive_root, iteration_version)
        current = sorted((archive_root / "docs" / "迭代").glob(f"v{iteration_version}_*"))
        if len(current) != 1:
            raise RuntimeError(
                f"release tree must contain exactly one current iteration note for v{iteration_version}: {current}"
            )
        files = sorted(path for path in archive_root.rglob("*") if path.is_file())
        output.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
            for path in files:
                relative = Path(archive_root.name) / path.relative_to(archive_root)
                info = zipfile.ZipInfo(relative.as_posix(), date_time=(1980, 1, 1, 0, 0, 0))
                info.compress_type = zipfile.ZIP_DEFLATED
                info.external_attr = (stat.S_IFREG | 0o644) << 16
                archive.writestr(info, path.read_bytes())
    return {
        "schema": "se-project-archive-v1",
        "version": version,
        "output": str(output),
        "current_iteration_doc": current[0].name,
        "pruned_iteration_docs": removed,
        "file_count": len(files),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project", default=".")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    print(json.dumps(build_archive(Path(args.project), Path(args.output)), ensure_ascii=False))

if __name__ == "__main__":
    main()
