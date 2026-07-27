"""Versioned shared-frame protocol used by native GUI clients."""

from __future__ import annotations

from dataclasses import dataclass
import json
import os
from pathlib import Path
import struct
from typing import Any

import numpy as np


PROTOCOL_SCHEMA = "se-gui-shared-frame-v1"
MANIFEST_SCHEMA = "se-gui-interface-manifest-v1"
MAGIC = b"ECOGAME1"
VERSION = 1
HEADER_SIZE = 256
SLOT_HEADER_SIZE = 64
SLOT_COUNT = 3
PUBLISHED_META_OFFSET = 72

HEADER = struct.Struct("<8sIIIIIIfffIQQQIIQ168x")
SLOT_HEADER = struct.Struct("<IIQIIQ32x")

ENTITY_DTYPE = np.dtype(
    [
        ("entity_id", "<u8"),
        ("group_id", "<u8"),
        ("lineage_id", "<u8"),
        ("target_id", "<u8"),
        ("x", "<f4"),
        ("y", "<f4"),
        ("vx", "<f4"),
        ("vy", "<f4"),
        ("energy", "<f4"),
        ("integrity", "<f4"),
        ("fertility", "<f4"),
        ("age_fraction", "<f4"),
        ("generation", "<u4"),
        ("action", "u1"),
        ("action_success", "u1"),
        ("flags", "<u2"),
    ],
    align=False,
)
NO_ACTION = np.uint8(255)


def _align_up(value: int, alignment: int = 64) -> int:
    return (value + alignment - 1) // alignment * alignment


@dataclass(frozen=True, slots=True)
class BridgeLayout:
    grid_x: int
    grid_y: int
    max_entities: int
    world_width: float
    world_height: float
    max_energy: float

    def __post_init__(self) -> None:
        if self.grid_x <= 0 or self.grid_y <= 0:
            raise ValueError("grid dimensions must be positive")
        if self.max_entities <= 0:
            raise ValueError("max_entities must be positive")
        if self.world_width <= 0.0 or self.world_height <= 0.0:
            raise ValueError("world dimensions must be positive")
        if self.max_energy <= 0.0:
            raise ValueError("max_energy must be positive")

    @property
    def cell_count(self) -> int:
        return self.grid_x * self.grid_y

    @property
    def resource_bytes(self) -> int:
        return 4 * self.cell_count * np.dtype("<f4").itemsize

    @property
    def hazard_bytes(self) -> int:
        return self.cell_count * np.dtype("<f4").itemsize

    @property
    def entity_capacity_bytes(self) -> int:
        return self.max_entities * ENTITY_DTYPE.itemsize

    @property
    def slot_size(self) -> int:
        return _align_up(
            SLOT_HEADER_SIZE
            + self.resource_bytes
            + self.hazard_bytes
            + self.entity_capacity_bytes
        )

    @property
    def file_size(self) -> int:
        return HEADER_SIZE + SLOT_COUNT * self.slot_size

    @classmethod
    def from_simulation(cls, simulation: Any) -> "BridgeLayout":
        cfg = simulation.cfg
        return cls(
            grid_x=int(cfg.world.grid_x),
            grid_y=int(cfg.world.grid_y),
            max_entities=int(cfg.world.max_entities),
            world_width=float(cfg.world.width),
            world_height=float(cfg.world.height),
            max_energy=float(cfg.entities.max_energy),
        )


def default_manifest_path(stream_path: str | Path) -> Path:
    """Return the canonical protocol sidecar path for one stream file."""
    stream = Path(stream_path)
    return stream.with_name(stream.name + ".json")


def entity_field_manifest() -> list[dict[str, object]]:
    fields: list[dict[str, object]] = []
    for name in ENTITY_DTYPE.names or ():
        field_dtype, offset = ENTITY_DTYPE.fields[name][:2]
        fields.append(
            {
                "name": name,
                "dtype": field_dtype.str,
                "offset": int(offset),
                "bytes": int(field_dtype.itemsize),
            }
        )
    return fields


def build_manifest(
    layout: BridgeLayout,
    *,
    stream_path: str | Path,
    publish_every: int,
    state: str,
    sequence: int = 0,
    tick: int = 0,
    producer: dict[str, object] | None = None,
) -> dict[str, object]:
    return {
        "schema": MANIFEST_SCHEMA,
        "protocol_schema": PROTOCOL_SCHEMA,
        "protocol_version": VERSION,
        "state": str(state),
        "stream_path": str(Path(stream_path).resolve()),
        "endianness": "little",
        "slot_count": SLOT_COUNT,
        "header_bytes": HEADER_SIZE,
        "slot_header_bytes": SLOT_HEADER_SIZE,
        "published_meta_offset": PUBLISHED_META_OFFSET,
        "publish_every_ticks": int(publish_every),
        "last_sequence": int(sequence),
        "last_tick": int(tick),
        "layout": {
            "grid_x": layout.grid_x,
            "grid_y": layout.grid_y,
            "max_entities": layout.max_entities,
            "world_width": layout.world_width,
            "world_height": layout.world_height,
            "max_energy": layout.max_energy,
            "resource_channels": 4,
            "resource_bytes": layout.resource_bytes,
            "hazard_bytes": layout.hazard_bytes,
            "entity_record_bytes": ENTITY_DTYPE.itemsize,
            "entity_capacity_bytes": layout.entity_capacity_bytes,
            "slot_bytes": layout.slot_size,
            "file_bytes": layout.file_size,
        },
        "entity_fields": entity_field_manifest(),
        "publication_semantics": {
            "direction": "python-authoritative-one-way",
            "buffering": "triple-buffer-latest-frame-only",
            "consumer_may_drop_frames": True,
            "consumer_must_not_modify_stream": True,
            "scientific_feedback": False,
        },
        "producer": dict(producer or {}),
    }


def write_manifest(path: str | Path, payload: dict[str, object]) -> Path:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_name(destination.name + ".tmp")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    os.replace(temporary, destination)
    return destination


__all__ = [
    "BridgeLayout",
    "ENTITY_DTYPE",
    "HEADER",
    "HEADER_SIZE",
    "MAGIC",
    "MANIFEST_SCHEMA",
    "NO_ACTION",
    "PROTOCOL_SCHEMA",
    "PUBLISHED_META_OFFSET",
    "SLOT_COUNT",
    "SLOT_HEADER",
    "SLOT_HEADER_SIZE",
    "VERSION",
    "build_manifest",
    "default_manifest_path",
    "entity_field_manifest",
    "write_manifest",
]
