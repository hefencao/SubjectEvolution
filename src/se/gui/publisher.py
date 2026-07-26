"""Non-blocking latest-frame publisher for the native GUI."""

from __future__ import annotations

import mmap
import os
from pathlib import Path
import platform
import struct
import time
from typing import Any

import numpy as np

from .. import __version__
from .protocol import (
    BridgeLayout,
    ENTITY_DTYPE,
    HEADER,
    HEADER_SIZE,
    MAGIC,
    NO_ACTION,
    PUBLISHED_META_OFFSET,
    SLOT_COUNT,
    SLOT_HEADER,
    SLOT_HEADER_SIZE,
    VERSION,
    build_manifest,
    write_manifest,
)


class SharedFramePublisher:
    """Publish stable post-step frames through a triple-buffered mmap file.

    Python remains authoritative.  Publishing is observation-only and a native
    client may skip frames without blocking or changing simulation semantics.
    """

    def __init__(
        self,
        layout: BridgeLayout,
        *,
        path: str | Path = "eco_live.bin",
        every_ticks: int = 2,
        manifest_path: str | Path | None = None,
    ) -> None:
        if every_ticks <= 0:
            raise ValueError("every_ticks must be positive")
        if ENTITY_DTYPE.itemsize != 72:
            raise RuntimeError(f"entity layout mismatch: {ENTITY_DTYPE.itemsize} != 72")

        self.layout = layout
        self.path = Path(path)
        self.every_ticks = int(every_ticks)
        self.manifest_path = (
            Path(manifest_path)
            if manifest_path is not None
            else self.path.with_name(self.path.name + ".json")
        )
        self.path.parent.mkdir(parents=True, exist_ok=True)

        self._file = self.path.open("w+b")
        self._file.truncate(layout.file_size)
        self._file.flush()
        self._map = mmap.mmap(self._file.fileno(), layout.file_size, access=mmap.ACCESS_WRITE)
        self._sequence = 0
        self._published_slot = 0
        self._last_tick = 0
        self._closed = False

        self._records = np.empty(layout.max_entities, dtype=ENTITY_DTYPE)
        self._action_by_slot = np.full(layout.max_entities, NO_ACTION, dtype=np.uint8)
        self._success_by_slot = np.zeros(layout.max_entities, dtype=np.uint8)
        self._target_by_slot = np.zeros(layout.max_entities, dtype=np.uint64)

        self._write_initial_header()
        self._write_protocol_manifest("running")

    @classmethod
    def from_simulation(
        cls,
        simulation: Any,
        *,
        path: str | Path = "eco_live.bin",
        every_ticks: int = 2,
        manifest_path: str | Path | None = None,
    ) -> "SharedFramePublisher":
        return cls(
            BridgeLayout.from_simulation(simulation),
            path=path,
            every_ticks=every_ticks,
            manifest_path=manifest_path,
        )

    @property
    def closed(self) -> bool:
        return self._closed

    @property
    def sequence(self) -> int:
        return self._sequence

    @property
    def last_tick(self) -> int:
        return self._last_tick

    def _write_protocol_manifest(self, state: str) -> None:
        payload = build_manifest(
            self.layout,
            stream_path=self.path,
            publish_every=self.every_ticks,
            state=state,
            sequence=self._sequence,
            tick=self._last_tick,
            producer={
                "project_version": __version__,
                "python": platform.python_version(),
                "numpy": np.__version__,
                "pid": os.getpid(),
            },
        )
        write_manifest(self.manifest_path, payload)

    def _write_initial_header(self) -> None:
        self._map[:HEADER_SIZE] = HEADER.pack(
            MAGIC,
            VERSION,
            HEADER_SIZE,
            SLOT_COUNT,
            self.layout.max_entities,
            self.layout.grid_x,
            self.layout.grid_y,
            self.layout.world_width,
            self.layout.world_height,
            self.layout.max_energy,
            ENTITY_DTYPE.itemsize,
            self.layout.slot_size,
            self.layout.resource_bytes,
            self.layout.hazard_bytes,
            0,
            0,
            0,
        )

    def close(self) -> None:
        if self._closed:
            return
        self._write_protocol_manifest("closed")
        self._closed = True
        self._map.flush()
        self._map.close()
        self._file.close()

    def __enter__(self) -> "SharedFramePublisher":
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def maybe_publish(self, simulation: Any) -> bool:
        if int(simulation.tick) % self.every_ticks != 0:
            return False
        self.publish(simulation)
        return True

    def _environment_arrays(self, simulation: Any) -> tuple[np.ndarray, np.ndarray]:
        if getattr(simulation, "gpu_runtime", None) is None:
            resources = simulation.environment.resources
            hazard = simulation.environment.hazard
        else:
            runtime = simulation.gpu_runtime
            resources = runtime.backend.to_numpy(runtime.environment.resources)
            hazard = runtime.backend.to_numpy(runtime.environment.hazard)

        resources_array = np.ascontiguousarray(resources, dtype="<f4")
        hazard_array = np.ascontiguousarray(hazard, dtype="<f4")
        expected_resources = (4, self.layout.grid_y, self.layout.grid_x)
        expected_hazard = (self.layout.grid_y, self.layout.grid_x)
        if resources_array.shape != expected_resources:
            raise ValueError(
                f"resource shape mismatch: {resources_array.shape} != {expected_resources}"
            )
        if hazard_array.shape != expected_hazard:
            raise ValueError(f"hazard shape mismatch: {hazard_array.shape} != {expected_hazard}")
        return resources_array, hazard_array

    def _fill_action_fields(self, simulation: Any) -> None:
        self._action_by_slot.fill(NO_ACTION)
        self._success_by_slot.fill(0)
        self._target_by_slot.fill(0)

        intents = getattr(simulation, "last_intents", None)
        resolutions = getattr(simulation, "last_resolutions", None)
        if intents is None:
            return

        entities = simulation.entities
        carriers_all = np.asarray(intents.carrier_index, dtype=np.int32)
        valid_carriers = (carriers_all >= 0) & (carriers_all < self.layout.max_entities)
        carriers = carriers_all[valid_carriers]
        if carriers.size == 0:
            return

        self._action_by_slot[carriers] = np.asarray(
            intents.action, dtype=np.uint8
        )[valid_carriers]
        targets = np.asarray(intents.target_index, dtype=np.int64)[valid_carriers]
        valid_targets = (targets >= 0) & (targets < self.layout.max_entities)
        safe_targets = np.where(valid_targets, targets, 0)
        target_ids = np.asarray(entities.entity_id, dtype=np.uint64)[safe_targets]
        self._target_by_slot[carriers] = np.where(
            valid_targets, target_ids, np.uint64(0)
        )
        if resolutions is not None:
            self._success_by_slot[carriers] = np.asarray(
                resolutions.success, dtype=np.uint8
            )[valid_carriers]

    def publish(self, simulation: Any) -> None:
        if self._closed:
            raise RuntimeError("publisher is closed")

        resources, hazard = self._environment_arrays(simulation)
        entities = simulation.entities
        active = np.flatnonzero(np.asarray(entities.alive, dtype=bool)).astype(
            np.int32, copy=False
        )
        count = int(active.size)
        if count > self.layout.max_entities:
            raise ValueError(f"active entity count {count} exceeds capacity")

        self._fill_action_fields(simulation)
        records = self._records[:count]
        records["entity_id"] = entities.entity_id[active]
        records["group_id"] = simulation.social.group_id[active]
        records["lineage_id"] = entities.lineage_id[active]
        records["target_id"] = self._target_by_slot[active]
        records["x"] = entities.x[active]
        records["y"] = entities.y[active]
        records["vx"] = entities.vx[active]
        records["vy"] = entities.vy[active]
        records["energy"] = entities.energy[active]
        records["integrity"] = entities.integrity[active]
        records["fertility"] = entities.fertility[active]
        max_age = max(float(simulation.cfg.entities.max_age), 1.0)
        records["age_fraction"] = np.minimum(
            np.asarray(entities.age[active], dtype=np.float32) / max_age, 1.0
        )
        records["generation"] = entities.generation[active]
        records["action"] = self._action_by_slot[active]
        records["action_success"] = self._success_by_slot[active]
        records["flags"] = np.uint16(1)

        self._sequence = (self._sequence + 1) & 0xFFFFFFFF
        if self._sequence == 0:
            self._sequence = 1
        slot = (self._published_slot + 1) % SLOT_COUNT
        slot_base = HEADER_SIZE + slot * self.layout.slot_size

        struct.pack_into("<II", self._map, slot_base, 0, 0)
        resource_offset = slot_base + SLOT_HEADER_SIZE
        hazard_offset = resource_offset + self.layout.resource_bytes
        entity_offset = hazard_offset + self.layout.hazard_bytes
        self._map[resource_offset : resource_offset + self.layout.resource_bytes] = (
            memoryview(resources).cast("B")
        )
        self._map[hazard_offset : hazard_offset + self.layout.hazard_bytes] = (
            memoryview(hazard).cast("B")
        )
        entity_bytes = count * ENTITY_DTYPE.itemsize
        self._map[entity_offset : entity_offset + entity_bytes] = memoryview(records).cast(
            "B"
        )

        tick = int(simulation.tick)
        SLOT_HEADER.pack_into(
            self._map,
            slot_base,
            self._sequence,
            self._sequence,
            tick,
            count,
            1,
            time.monotonic_ns(),
        )
        struct.pack_into(
            "<IIQ", self._map, PUBLISHED_META_OFFSET, slot, self._sequence, tick
        )
        self._published_slot = slot
        self._last_tick = tick


__all__ = ["SharedFramePublisher"]
