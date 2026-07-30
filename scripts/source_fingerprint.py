#!/usr/bin/env python3
"""Stable source-tree fingerprints that ignore generated build metadata."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Iterable


FINGERPRINT_ROOT_FILES = ("Makefile", "pyproject.toml")
FINGERPRINT_ROOT_DIRS = ("src", "scripts", "tests", "configs")
_GENERATED_PARTS = {
    "__pycache__",
    ".pytest_cache",
    ".validation",
    "build",
    "dist",
}
_GENERATED_SUFFIXES = (".egg-info",)
_GENERATED_FILE_SUFFIXES = (".pyc", ".pyo")


def _is_generated(path: Path, *, project: Path) -> bool:
    relative = path.relative_to(project)
    if any(part in _GENERATED_PARTS for part in relative.parts):
        return True
    if any(
        part.endswith(suffix)
        for part in relative.parts
        for suffix in _GENERATED_SUFFIXES
    ):
        return True
    return path.suffix in _GENERATED_FILE_SUFFIXES


def source_files(project: Path) -> Iterable[Path]:
    """Yield deterministic, reviewable source inputs for release freshness checks."""

    project = project.resolve()
    candidates = [project / name for name in FINGERPRINT_ROOT_FILES]
    for root_name in FINGERPRINT_ROOT_DIRS:
        root = project / root_name
        if root.exists():
            candidates.extend(sorted(root.rglob("*")))
    for path in candidates:
        if path.is_file() and not _is_generated(path, project=project):
            yield path


def source_tree_fingerprint(project: Path) -> str:
    """Hash source inputs while excluding ignored generated metadata."""

    project = project.resolve()
    digest = hashlib.sha256()
    for path in source_files(project):
        digest.update(path.relative_to(project).as_posix().encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()
