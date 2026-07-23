"""High-throughput, latest-frame-only bridge for subject_evolution.

The bridge is intentionally one-way.  Python remains authoritative.
C++ may drop frames without blocking or changing simulation semantics.
"""

from __future__ import annotations

from dataclasses import dataclass
import mmap
from pathlib import Path
import struct
import time
from types import MethodType
from typing import Any, Callable

import numpy as np


MAGIC = b"ECOGAME1"
VERSION = 1
HEADER_SIZE = 256
SLOT_HEADER_SIZE = 64
SLOT_COUNT = 3

HEADER = struct.Struct("<8sIIIIIIfffIQQQIIQ168x")
SLOT_HEADER = struct.Struct("<IIQIIQ32x")

PUBLISHED_META_OFFSET = 72

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


class SharedFramePublisher:
    """Publish stable post-step frames through a triple-buffered mmap file."""

    def __init__(
        self,
        layout: BridgeLayout,
        *,
        path: str | Path = "eco_live.bin",
        every_ticks: int = 2,
    ) -> None:
        if every_ticks <= 0:
            raise ValueError("every_ticks must be positive")
        if ENTITY_DTYPE.itemsize != 72:
            raise RuntimeError(
                f"Entity layout mismatch: {ENTITY_DTYPE.itemsize} != 72"
            )

        self.layout = layout
        self.path = Path(path)
        self.every_ticks = int(every_ticks)
        self.path.parent.mkdir(parents=True, exist_ok=True)

        self._file = self.path.open("w+b")
        self._file.truncate(layout.file_size)
        self._file.flush()

        self._map = mmap.mmap(
            self._file.fileno(),
            layout.file_size,
            access=mmap.ACCESS_WRITE,
        )

        self._sequence = 0
        self._published_slot = 0
        self._closed = False

        self._records = np.empty(
            layout.max_entities,
            dtype=ENTITY_DTYPE,
        )
        self._action_by_slot = np.full(
            layout.max_entities,
            NO_ACTION,
            dtype=np.uint8,
        )
        self._success_by_slot = np.zeros(
            layout.max_entities,
            dtype=np.uint8,
        )
        self._target_by_slot = np.zeros(
            layout.max_entities,
            dtype=np.uint64,
        )

        self._write_initial_header()

    @classmethod
    def from_simulation(
        cls,
        simulation: Any,
        *,
        path: str | Path = "eco_live.bin",
        every_ticks: int = 2,
    ) -> "SharedFramePublisher":
        cfg = simulation.cfg
        return cls(
            BridgeLayout(
                grid_x=int(cfg.world.grid_x),
                grid_y=int(cfg.world.grid_y),
                max_entities=int(cfg.world.max_entities),
                world_width=float(cfg.world.width),
                world_height=float(cfg.world.height),
                max_energy=float(cfg.entities.max_energy),
            ),
            path=path,
            every_ticks=every_ticks,
        )

    def _write_initial_header(self) -> None:
        header = HEADER.pack(
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
        self._map[:HEADER_SIZE] = header

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
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

    def _environment_arrays(
        self,
        simulation: Any,
    ) -> tuple[np.ndarray, np.ndarray]:
        if getattr(simulation, "gpu_runtime", None) is None:
            resources = simulation.environment.resources
            hazard = simulation.environment.hazard
        else:
            runtime = simulation.gpu_runtime
            resources = runtime.backend.to_numpy(
                runtime.environment.resources
            )
            hazard = runtime.backend.to_numpy(
                runtime.environment.hazard
            )

        resources_array = np.ascontiguousarray(
            resources,
            dtype="<f4",
        )
        hazard_array = np.ascontiguousarray(
            hazard,
            dtype="<f4",
        )

        expected_resources = (
            4,
            self.layout.grid_y,
            self.layout.grid_x,
        )
        expected_hazard = (
            self.layout.grid_y,
            self.layout.grid_x,
        )

        if resources_array.shape != expected_resources:
            raise ValueError(
                "resource shape mismatch: "
                f"{resources_array.shape} != {expected_resources}"
            )
        if hazard_array.shape != expected_hazard:
            raise ValueError(
                "hazard shape mismatch: "
                f"{hazard_array.shape} != {expected_hazard}"
            )

        return resources_array, hazard_array

    def _fill_action_fields(self, simulation: Any) -> None:
        self._action_by_slot.fill(NO_ACTION)
        self._success_by_slot.fill(0)
        self._target_by_slot.fill(0)

        intents = getattr(simulation, "last_intents", None)
        resolutions = getattr(
            simulation,
            "last_resolutions",
            None,
        )

        if intents is None:
            return

        entities = simulation.entities
        carriers = np.asarray(
            intents.carrier_index,
            dtype=np.int32,
        )

        valid_carriers = (
            (carriers >= 0)
            & (carriers < self.layout.max_entities)
        )

        carriers = carriers[valid_carriers]
        if carriers.size == 0:
            return

        actions = np.asarray(
            intents.action,
            dtype=np.uint8,
        )[valid_carriers]
        self._action_by_slot[carriers] = actions

        targets = np.asarray(
            intents.target_index,
            dtype=np.int64,
        )[valid_carriers]

        valid_targets = (
            (targets >= 0)
            & (targets < self.layout.max_entities)
        )
        safe_targets = np.where(valid_targets, targets, 0)
        target_ids = np.asarray(
            entities.entity_id,
            dtype=np.uint64,
        )[safe_targets]
        self._target_by_slot[carriers] = np.where(
            valid_targets,
            target_ids,
            np.uint64(0),
        )

        if resolutions is not None:
            success = np.asarray(
                resolutions.success,
                dtype=np.uint8,
            )[valid_carriers]
            self._success_by_slot[carriers] = success

    def publish(self, simulation: Any) -> None:
        if self._closed:
            raise RuntimeError("publisher is closed")

        resources, hazard = self._environment_arrays(
            simulation
        )

        entities = simulation.entities
        active = np.flatnonzero(
            np.asarray(entities.alive, dtype=bool)
        ).astype(np.int32, copy=False)

        count = int(active.size)
        if count > self.layout.max_entities:
            raise ValueError(
                f"active entity count {count} exceeds capacity"
            )

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

        max_age = max(
            float(simulation.cfg.entities.max_age),
            1.0,
        )
        records["age_fraction"] = np.minimum(
            np.asarray(
                entities.age[active],
                dtype=np.float32,
            )
            / max_age,
            1.0,
        )

        records["generation"] = entities.generation[active]
        records["action"] = self._action_by_slot[active]
        records["action_success"] = self._success_by_slot[active]
        records["flags"] = np.uint16(1)

        self._sequence = (
            self._sequence + 1
        ) & 0xFFFFFFFF
        if self._sequence == 0:
            self._sequence = 1

        slot = (
            self._published_slot + 1
        ) % SLOT_COUNT

        slot_base = (
            HEADER_SIZE
            + slot * self.layout.slot_size
        )

        # Mark slot as not committed while the payload is changing.
        struct.pack_into("<II", self._map, slot_base, 0, 0)

        resource_offset = slot_base + SLOT_HEADER_SIZE
        hazard_offset = (
            resource_offset
            + self.layout.resource_bytes
        )
        entity_offset = (
            hazard_offset
            + self.layout.hazard_bytes
        )

        self._map[
            resource_offset:
            resource_offset + self.layout.resource_bytes
        ] = memoryview(resources).cast("B")

        self._map[
            hazard_offset:
            hazard_offset + self.layout.hazard_bytes
        ] = memoryview(hazard).cast("B")

        entity_bytes = count * ENTITY_DTYPE.itemsize
        self._map[
            entity_offset:
            entity_offset + entity_bytes
        ] = memoryview(records).cast("B")

        tick = int(simulation.tick)
        monotonic_ns = time.monotonic_ns()

        SLOT_HEADER.pack_into(
            self._map,
            slot_base,
            self._sequence,
            self._sequence,
            tick,
            count,
            1,
            monotonic_ns,
        )

        # Publish globally only after the slot is complete.
        struct.pack_into(
            "<IIQ",
            self._map,
            PUBLISHED_META_OFFSET,
            slot,
            self._sequence,
            tick,
        )

        self._published_slot = slot


def attach_realtime_publisher(
    simulation: Any,
    publisher: SharedFramePublisher,
    *,
    publish_initial: bool = True,
) -> Callable[[], None]:
    """Wrap one Simulation instance without modifying its class definition."""

    original_step = simulation.step

    if publish_initial:
        publisher.publish(simulation)

    def wrapped_step(self: Any) -> Any:
        stats = original_step()
        publisher.maybe_publish(self)
        return stats

    simulation.step = MethodType(
        wrapped_step,
        simulation,
    )

    def detach() -> None:
        simulation.step = original_step

    return detach


__all__ = [
    "BridgeLayout",
    "ENTITY_DTYPE",
    "SharedFramePublisher",
    "attach_realtime_publisher",
]
