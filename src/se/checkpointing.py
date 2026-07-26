"""Portable project-generated full-world checkpoint bundles.

The bundle is a ZIP container with human-readable metadata and a Python pickle
payload.  Pickle is used only for trusted checkpoints produced by this project;
loading arbitrary third-party checkpoint files is unsafe and intentionally not
supported as a secure interchange format.
"""

from __future__ import annotations

from dataclasses import asdict, fields, is_dataclass
from datetime import datetime, timezone
import hashlib
import io
import json
import os
from pathlib import Path
import pickle
import sys
import zipfile
from typing import Any

import numpy as np

from . import __version__


CHECKPOINT_SCHEMA = "se-full-checkpoint-v1"
_METADATA_NAME = "metadata.json"
_STATE_NAME = "state.pkl"


class CheckpointError(RuntimeError):
    """Raised when a full-world checkpoint is missing, corrupt, or incompatible."""


def _config_sha256(config: Any) -> str:
    payload = json.dumps(asdict(config), ensure_ascii=False, sort_keys=True).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _stored_dataclass_payload(value: Any) -> Any:
    """Reconstruct the dataclass payload that was physically stored in pickle.

    When an older checkpoint is unpickled against a newer dataclass, newly
    added fields are visible through class-level defaults even though they were
    not present when the checkpoint hash was created.  Walking ``__dict__``
    membership lets us reproduce the older ``asdict`` payload without
    weakening the state-payload checksum.
    """
    if is_dataclass(value) and not isinstance(value, type):
        stored = vars(value)
        return {
            field.name: _stored_dataclass_payload(stored[field.name])
            for field in fields(value)
            if field.name in stored
        }
    if isinstance(value, dict):
        return {key: _stored_dataclass_payload(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return tuple(_stored_dataclass_payload(item) for item in value)
    if isinstance(value, list):
        return [_stored_dataclass_payload(item) for item in value]
    return value


def _stored_config_sha256(config: Any) -> str:
    payload = json.dumps(
        _stored_dataclass_payload(config), ensure_ascii=False, sort_keys=True
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def write_checkpoint_bundle(
    path: str | Path,
    *,
    config: Any,
    tick: int,
    state: dict[str, Any],
    execution_backend: str,
    requested_backend: str,
) -> Path:
    """Atomically write one trusted full-world checkpoint bundle."""
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    state_payload = pickle.dumps(state, protocol=pickle.HIGHEST_PROTOCOL)
    metadata = {
        "schema": CHECKPOINT_SCHEMA,
        "project_version": __version__,
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "tick": int(tick),
        "config_sha256": _config_sha256(config),
        "state_sha256": hashlib.sha256(state_payload).hexdigest(),
        "execution_backend": str(execution_backend),
        "requested_backend": str(requested_backend),
        "python": sys.version,
        "numpy": np.__version__,
        "trusted_pickle_payload": True,
    }
    temporary = destination.with_name(destination.name + ".tmp")
    with zipfile.ZipFile(temporary, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(
            _METADATA_NAME,
            json.dumps(metadata, ensure_ascii=False, indent=2).encode("utf-8"),
        )
        archive.writestr(_STATE_NAME, state_payload)
    os.replace(temporary, destination)
    return destination


def read_checkpoint_bundle(path: str | Path) -> tuple[dict[str, Any], dict[str, Any]]:
    """Read and verify a trusted project-generated checkpoint bundle."""
    source = Path(path)
    if not source.is_file():
        raise CheckpointError(f"checkpoint does not exist: {source}")
    try:
        with zipfile.ZipFile(source, "r") as archive:
            metadata = json.loads(archive.read(_METADATA_NAME).decode("utf-8"))
            state_payload = archive.read(_STATE_NAME)
    except (KeyError, OSError, ValueError, zipfile.BadZipFile) as exc:
        raise CheckpointError(f"invalid checkpoint bundle: {source}") from exc
    if metadata.get("schema") != CHECKPOINT_SCHEMA:
        raise CheckpointError(
            f"unsupported checkpoint schema {metadata.get('schema')!r}; "
            f"expected {CHECKPOINT_SCHEMA!r}"
        )
    actual_hash = hashlib.sha256(state_payload).hexdigest()
    if actual_hash != metadata.get("state_sha256"):
        raise CheckpointError("checkpoint state checksum mismatch")
    try:
        state = pickle.load(io.BytesIO(state_payload))
    except Exception as exc:  # trusted project file, but report version/corruption clearly
        raise CheckpointError("checkpoint state payload could not be loaded") from exc
    if not isinstance(state, dict) or "config" not in state or "simulation" not in state:
        raise CheckpointError("checkpoint state payload is missing required sections")
    expected_config_hash = metadata.get("config_sha256")
    current_config_hash = _config_sha256(state["config"])
    if current_config_hash != expected_config_hash:
        stored_config_hash = _stored_config_sha256(state["config"])
        if stored_config_hash != expected_config_hash:
            raise CheckpointError("checkpoint embedded configuration checksum mismatch")
    if int(state["simulation"].get("tick", -1)) != int(metadata.get("tick", -2)):
        raise CheckpointError("checkpoint tick metadata does not match state payload")
    return metadata, state


__all__ = [
    "CHECKPOINT_SCHEMA",
    "CheckpointError",
    "read_checkpoint_bundle",
    "write_checkpoint_bundle",
]
