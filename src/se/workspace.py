"""Portable workspace paths, artifact identities, and operator settings.

Runtime plans store paths relative to an explicit workspace root. This keeps
plans movable between checkouts and versions while preserving content hashes as
the authoritative identity of frozen evidence. Operator-specific external
result and patch directories are stored separately in the ignored
``.se-workspace.toml`` file.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import tomllib
from typing import Any

WORKSPACE_LAYOUT_SCHEMA = "se-workspace-layout-v1"
WORKSPACE_SETTINGS_SCHEMA = "se-workspace-v1"
WORKSPACE_CONFIG_NAME = ".se-workspace.toml"
_WORKSPACE_SETTING_FIELDS = ("result_bundle_dir", "patch_dir")


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


def find_project_root(start: str | Path = ".") -> Path:
    current = Path(start).resolve()
    for candidate in (current, *current.parents):
        if (candidate / "pyproject.toml").is_file() and (candidate / "studies").is_dir():
            return candidate
    raise FileNotFoundError(f"could not locate project root from {current}")


def workspace_config_path(project_root: str | Path) -> Path:
    return Path(project_root).resolve() / WORKSPACE_CONFIG_NAME


def _external_workspace_dir(
    root: Path,
    data: dict[str, Any],
    *,
    field: str,
    label: str,
) -> Path | None:
    raw = data.get(field)
    if raw is None:
        return None
    if not isinstance(raw, str) or not raw.strip():
        raise ValueError(f"workspace settings {field} must be a non-empty string")
    destination = Path(raw).expanduser().resolve()
    try:
        destination.relative_to(root)
    except ValueError:
        return destination
    raise ValueError(f"{label} directory must be outside the project tree")


def _read_raw_settings(root: Path) -> dict[str, Any]:
    path = workspace_config_path(root)
    if not path.is_file():
        return {"schema": WORKSPACE_SETTINGS_SCHEMA}
    data = tomllib.loads(path.read_text(encoding="utf-8"))
    if data.get("schema") != WORKSPACE_SETTINGS_SCHEMA:
        raise ValueError(
            f"unsupported workspace settings schema: {data.get('schema')!r}"
        )
    return data


def load_workspace_settings(project_root: str | Path) -> dict[str, Any]:
    root = Path(project_root).resolve()
    path = workspace_config_path(root)
    data = _read_raw_settings(root)
    result_dir = _external_workspace_dir(
        root, data, field="result_bundle_dir", label="result bundle"
    )
    patch_dir = _external_workspace_dir(root, data, field="patch_dir", label="patch")
    return {
        "schema": WORKSPACE_SETTINGS_SCHEMA,
        "project_root": str(root),
        "config_path": str(path),
        # Backward-compatible meaning used by study result-path resolution.
        "configured": result_dir is not None,
        "result_bundle_configured": result_dir is not None,
        "patch_dir_configured": patch_dir is not None,
        "result_bundle_dir": str(result_dir) if result_dir is not None else None,
        "patch_dir": str(patch_dir) if patch_dir is not None else None,
    }


def _configure_workspace_dir(
    project_root: str | Path,
    destination_dir: str | Path,
    *,
    field: str,
    label: str,
) -> dict[str, Any]:
    root = Path(project_root).resolve()
    destination = Path(destination_dir).expanduser().resolve()
    try:
        destination.relative_to(root)
    except ValueError:
        pass
    else:
        raise ValueError(f"{label} directory must be outside the project tree")
    destination.mkdir(parents=True, exist_ok=True)

    existing = _read_raw_settings(root)
    existing[field] = str(destination)
    lines = [f'schema = {json.dumps(WORKSPACE_SETTINGS_SCHEMA)}']
    for name in _WORKSPACE_SETTING_FIELDS:
        value = existing.get(name)
        if isinstance(value, str) and value.strip():
            lines.append(f'{name} = {json.dumps(value)}')
    workspace_config_path(root).write_text("\n".join(lines) + "\n", encoding="utf-8")
    return load_workspace_settings(root)


def configure_result_bundle_dir(
    project_root: str | Path, result_dir: str | Path
) -> dict[str, Any]:
    return _configure_workspace_dir(
        project_root,
        result_dir,
        field="result_bundle_dir",
        label="result bundle",
    )


def configure_patch_dir(
    project_root: str | Path, patch_dir: str | Path
) -> dict[str, Any]:
    return _configure_workspace_dir(
        project_root,
        patch_dir,
        field="patch_dir",
        label="patch",
    )


def configured_path(project_root: str | Path, kind: str) -> Path:
    field_by_kind = {"result": "result_bundle_dir", "patch": "patch_dir"}
    try:
        field = field_by_kind[kind]
    except KeyError as exc:
        raise ValueError(f"unsupported workspace path kind: {kind!r}") from exc
    settings = load_workspace_settings(project_root)
    raw = settings[field]
    if raw is None:
        raise ValueError(f"workspace {kind} directory is not configured")
    return Path(str(raw))
