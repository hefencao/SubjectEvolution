"""Portable workspace paths and artifact identities.

Runtime plans store paths relative to an explicit workspace root.  This keeps
plans movable between checkouts and versions while preserving content hashes as
the authoritative identity of frozen evidence.
"""
from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

WORKSPACE_LAYOUT_SCHEMA = "se-workspace-layout-v1"


def workspace_root(path: str | Path | None = None) -> Path:
    return Path(path or ".").resolve()


def portable_path(path: str | Path, *, root: str | Path | None = None) -> str:
    base = workspace_root(root)
    resolved = Path(path)
    if not resolved.is_absolute():
        resolved = base / resolved
    resolved = resolved.resolve()
    try:
        return resolved.relative_to(base).as_posix()
    except ValueError as exc:
        raise ValueError(f"path must be inside workspace root {base}: {resolved}") from exc



def portable_or_absolute(
    path: str | Path,
    *,
    root: str | Path | None = None,
    strict: bool = False,
) -> str:
    try:
        return portable_path(path, root=root)
    except ValueError:
        if strict:
            raise
        return str(resolve_path(path, root=root))


def resolve_path(value: str | Path, *, root: str | Path | None = None) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path.resolve()
    return (workspace_root(root) / path).resolve()


def sha256_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def artifact_ref(
    path: str | Path,
    *,
    root: str | Path | None = None,
    schema: str | None = None,
    role: str | None = None,
) -> dict[str, Any]:
    resolved = resolve_path(path, root=root)
    payload: dict[str, Any] = {
        "path": portable_path(resolved, root=root),
        "sha256": sha256_file(resolved),
    }
    if schema is not None:
        payload["schema"] = schema
    if role is not None:
        payload["role"] = role
    return payload
