"""Reference reader used to validate native GUI protocol implementations."""

from __future__ import annotations

from dataclasses import dataclass
import mmap
from pathlib import Path
import struct

import numpy as np

from .protocol import (
    BridgeLayout,
    ENTITY_DTYPE,
    HEADER,
    HEADER_SIZE,
    MAGIC,
    PUBLISHED_META_OFFSET,
    SLOT_COUNT,
    SLOT_HEADER,
    SLOT_HEADER_SIZE,
    VERSION,
)


class SharedFrameError(RuntimeError):
    """Raised when a stream is incompatible or no stable frame can be read."""


@dataclass(frozen=True, slots=True)
class FrameSnapshot:
    sequence: int
    tick: int
    monotonic_ns: int
    resources: np.ndarray
    hazard: np.ndarray
    entities: np.ndarray


class SharedFrameReader:
    """Read committed frames with a double-checked sequence protocol."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self._file = self.path.open("rb")
        self._map = mmap.mmap(self._file.fileno(), 0, access=mmap.ACCESS_READ)
        self.layout = self._read_layout()
        if len(self._map) != self.layout.file_size:
            self.close()
            raise SharedFrameError(
                f"stream size mismatch: {len(self._map)} != {self.layout.file_size}"
            )

    def _read_layout(self) -> BridgeLayout:
        if len(self._map) < HEADER_SIZE:
            raise SharedFrameError("stream is smaller than the protocol header")
        fields = HEADER.unpack_from(self._map, 0)
        (
            magic,
            version,
            header_size,
            slot_count,
            max_entities,
            grid_x,
            grid_y,
            world_width,
            world_height,
            max_energy,
            entity_record_size,
            slot_size,
            resource_bytes,
            hazard_bytes,
            _published_slot,
            _published_sequence,
            _published_tick,
        ) = fields
        if magic != MAGIC or version != VERSION:
            raise SharedFrameError(
                f"unsupported stream protocol magic/version: {magic!r}/{version}"
            )
        if header_size != HEADER_SIZE or slot_count != SLOT_COUNT:
            raise SharedFrameError("stream header or slot count mismatch")
        if entity_record_size != ENTITY_DTYPE.itemsize:
            raise SharedFrameError("entity record size mismatch")
        layout = BridgeLayout(
            grid_x=int(grid_x),
            grid_y=int(grid_y),
            max_entities=int(max_entities),
            world_width=float(world_width),
            world_height=float(world_height),
            max_energy=float(max_energy),
        )
        if (
            int(slot_size) != layout.slot_size
            or int(resource_bytes) != layout.resource_bytes
            or int(hazard_bytes) != layout.hazard_bytes
        ):
            raise SharedFrameError("stream payload layout mismatch")
        return layout

    def close(self) -> None:
        mapping = getattr(self, "_map", None)
        if mapping is not None:
            mapping.close()
            self._map = None
        file_obj = getattr(self, "_file", None)
        if file_obj is not None:
            file_obj.close()
            self._file = None

    def __enter__(self) -> "SharedFrameReader":
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def read_latest(self, *, retries: int = 8) -> FrameSnapshot:
        if retries <= 0:
            raise ValueError("retries must be positive")
        for _ in range(retries):
            slot, sequence, published_tick = struct.unpack_from(
                "<IIQ", self._map, PUBLISHED_META_OFFSET
            )
            if sequence == 0 or slot >= SLOT_COUNT:
                continue
            slot_base = HEADER_SIZE + slot * self.layout.slot_size
            before = SLOT_HEADER.unpack_from(self._map, slot_base)
            begin, end, tick, count, flags, monotonic_ns = before
            if begin != sequence or end != sequence or flags & 1 == 0:
                continue
            if count > self.layout.max_entities:
                raise SharedFrameError("published entity count exceeds stream capacity")

            resource_offset = slot_base + SLOT_HEADER_SIZE
            hazard_offset = resource_offset + self.layout.resource_bytes
            entity_offset = hazard_offset + self.layout.hazard_bytes
            resource_payload = bytes(
                self._map[
                    resource_offset : resource_offset + self.layout.resource_bytes
                ]
            )
            hazard_payload = bytes(
                self._map[hazard_offset : hazard_offset + self.layout.hazard_bytes]
            )
            entity_payload = bytes(
                self._map[
                    entity_offset : entity_offset + count * ENTITY_DTYPE.itemsize
                ]
            )

            after = SLOT_HEADER.unpack_from(self._map, slot_base)
            slot_after, sequence_after, tick_after = struct.unpack_from(
                "<IIQ", self._map, PUBLISHED_META_OFFSET
            )
            if (
                before != after
                or slot != slot_after
                or sequence != sequence_after
                or published_tick != tick_after
            ):
                continue

            resources = np.frombuffer(resource_payload, dtype="<f4").reshape(
                4, self.layout.grid_y, self.layout.grid_x
            )
            hazard = np.frombuffer(hazard_payload, dtype="<f4").reshape(
                self.layout.grid_y, self.layout.grid_x
            )
            entities = np.frombuffer(entity_payload, dtype=ENTITY_DTYPE, count=count)
            return FrameSnapshot(
                sequence=int(sequence),
                tick=int(tick),
                monotonic_ns=int(monotonic_ns),
                resources=resources.copy(),
                hazard=hazard.copy(),
                entities=entities.copy(),
            )
        raise SharedFrameError("no stable committed frame was available")


__all__ = ["FrameSnapshot", "SharedFrameError", "SharedFrameReader"]
