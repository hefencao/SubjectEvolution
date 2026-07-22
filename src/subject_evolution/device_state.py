"""Backend-neutral plans for keeping an accelerator observation mirror current.

The CPU world remains authoritative.  After a successful world commit it
publishes the exact final values needed by the next observation pass.  A GPU,
distributed replica, or replay checker can consume the same versioned plan
without learning how the CPU containers implement actions or lifecycle.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np


def _canonical_indices(value: np.ndarray) -> np.ndarray:
    """Copy an already canonical producer array without paying for a sort."""
    result = np.asarray(value, dtype=np.int32)
    if result.ndim != 1:
        raise ValueError("entity device commit indices must be one-dimensional")
    if result.size < 2 or np.all(result[1:] > result[:-1]):
        return result.copy()
    return np.unique(result)


@dataclass(frozen=True)
class EntityDeviceCommitPlan:
    """Canonical final-state patches for one persistent entity mirror.

    Dynamic, position, lifecycle/static, and social patches use independent
    density decisions.  A dense patch copies contiguous host arrays directly
    into persistent buffers; a sparse patch carries canonical row indices.
    """

    dynamic_full: bool
    dynamic_indices: np.ndarray
    dynamic_energy: np.ndarray
    dynamic_integrity: np.ndarray
    dynamic_fertility: np.ndarray
    dynamic_memory: np.ndarray
    dynamic_sensor_quality: np.ndarray
    position_full: bool
    position_indices: np.ndarray
    position_x: np.ndarray
    position_y: np.ndarray
    lifecycle_indices: np.ndarray
    lifecycle_alive: np.ndarray
    lifecycle_entity_ids: np.ndarray
    lifecycle_genotype: np.ndarray
    social_full: bool
    social_indices: np.ndarray
    social_group_ids: np.ndarray
    social_direction_x: np.ndarray
    social_direction_y: np.ndarray
    base_version: int
    next_version: int
    tick: int

    DENSE_PATCH_FRACTION = 0.5

    @property
    def semantic_transfer_nbytes(self) -> int:
        arrays = (
            self.dynamic_indices,
            self.dynamic_energy,
            self.dynamic_integrity,
            self.dynamic_fertility,
            self.dynamic_memory,
            self.dynamic_sensor_quality,
            self.position_indices,
            self.position_x,
            self.position_y,
            self.lifecycle_indices,
            self.lifecycle_alive,
            self.lifecycle_entity_ids,
            self.lifecycle_genotype,
            self.social_indices,
            self.social_group_ids,
            self.social_direction_x,
            self.social_direction_y,
        )
        return int(sum(value.nbytes for value in arrays))

    def validate(self, capacity: int, genotype_width: int) -> None:
        """Reject stale, malformed, or non-canonical patches before mutation."""
        index_sets = (
            self.dynamic_indices,
            self.position_indices,
            self.lifecycle_indices,
            self.social_indices,
        )
        if any(value.ndim != 1 for value in index_sets):
            raise ValueError("entity device commit indices must be one-dimensional")
        for indices in index_sets:
            if not np.issubdtype(indices.dtype, np.integer):
                raise ValueError("entity device commit indices must use integer dtypes")
            if indices.size and (
                np.any(indices < 0)
                or np.any(indices >= capacity)
                or np.any(indices[1:] <= indices[:-1])
            ):
                raise ValueError("entity device commit indices must be valid and strictly ordered")
        dynamic_size = capacity if self.dynamic_full else self.dynamic_indices.size
        if self.dynamic_full and self.dynamic_indices.size:
            raise ValueError("dense entity dynamic patch must not carry indices")
        if any(
            value.shape != (dynamic_size,)
            for value in (
                self.dynamic_energy,
                self.dynamic_integrity,
                self.dynamic_fertility,
                self.dynamic_sensor_quality,
            )
        ) or self.dynamic_memory.shape != (dynamic_size, 4):
            raise ValueError("entity dynamic patch shape is invalid")
        position_size = capacity if self.position_full else self.position_indices.size
        if self.position_full and self.position_indices.size:
            raise ValueError("dense entity position patch must not carry indices")
        if self.position_x.shape != (position_size,) or self.position_y.shape != (
            position_size,
        ):
            raise ValueError("entity position patch shape is invalid")
        lifecycle_size = self.lifecycle_indices.size
        if self.lifecycle_alive.shape != (lifecycle_size,):
            raise ValueError("entity lifecycle occupancy shape is invalid")
        if self.lifecycle_entity_ids.shape != (lifecycle_size,):
            raise ValueError("entity lifecycle ID shape is invalid")
        if self.lifecycle_genotype.shape != (lifecycle_size, genotype_width):
            raise ValueError("entity lifecycle genotype shape is invalid")
        social_size = capacity if self.social_full else self.social_indices.size
        if self.social_full and self.social_indices.size:
            raise ValueError("dense entity social patch must not carry indices")
        if self.social_group_ids.shape != (social_size,):
            raise ValueError("entity social group shape is invalid")
        if self.social_direction_x.shape != (social_size,) or self.social_direction_y.shape != (
            social_size,
        ):
            raise ValueError("entity social direction shape is invalid")
        float_values = (
            self.dynamic_energy,
            self.dynamic_integrity,
            self.dynamic_fertility,
            self.dynamic_memory,
            self.dynamic_sensor_quality,
            self.position_x,
            self.position_y,
            self.lifecycle_genotype,
            self.social_direction_x,
            self.social_direction_y,
        )
        if any(not np.all(np.isfinite(value)) for value in float_values):
            raise ValueError("entity device commit contains non-finite values")
        if self.base_version < 0 or self.next_version != self.base_version + 1:
            raise ValueError("entity device commit version transition is invalid")
        if self.tick < 0:
            raise ValueError("entity device commit tick must be non-negative")


def build_entity_device_commit_plan(
    entity: Any,
    social: Any,
    *,
    dynamic_indices: np.ndarray,
    position_indices: np.ndarray,
    lifecycle_indices: np.ndarray,
    social_indices: np.ndarray,
    base_version: int,
    tick: int,
) -> EntityDeviceCommitPlan:
    """Capture canonical final CPU values after one authoritative commit."""

    dynamic = _canonical_indices(dynamic_indices)
    positions = _canonical_indices(position_indices)
    lifecycle = _canonical_indices(lifecycle_indices)
    social_rows = _canonical_indices(social_indices)

    capacity = int(entity.alive.size)
    dynamic_full = dynamic.size >= capacity * EntityDeviceCommitPlan.DENSE_PATCH_FRACTION
    position_full = positions.size >= capacity * EntityDeviceCommitPlan.DENSE_PATCH_FRACTION
    social_full = social_rows.size >= capacity * EntityDeviceCommitPlan.DENSE_PATCH_FRACTION
    dynamic_source: Any = slice(None) if dynamic_full else dynamic
    position_source: Any = slice(None) if position_full else positions
    social_source: Any = slice(None) if social_full else social_rows
    sensor_quality = entity.sensor_quality()

    plan = EntityDeviceCommitPlan(
        dynamic_full=dynamic_full,
        dynamic_indices=(
            np.empty(0, dtype=np.int32) if dynamic_full else dynamic
        ),
        dynamic_energy=np.asarray(
            entity.energy[dynamic_source], dtype=np.float32
        ).copy(),
        dynamic_integrity=np.asarray(
            entity.integrity[dynamic_source], dtype=np.float32
        ).copy(),
        dynamic_fertility=np.asarray(
            entity.fertility[dynamic_source], dtype=np.float32
        ).copy(),
        dynamic_memory=np.asarray(
            entity.memory[dynamic_source], dtype=np.float32
        ).copy(),
        dynamic_sensor_quality=np.asarray(
            sensor_quality[dynamic_source], dtype=np.float32
        ).copy(),
        position_full=position_full,
        position_indices=(
            np.empty(0, dtype=np.int32) if position_full else positions
        ),
        position_x=np.asarray(entity.x[position_source], dtype=np.float32).copy(),
        position_y=np.asarray(entity.y[position_source], dtype=np.float32).copy(),
        lifecycle_indices=lifecycle,
        lifecycle_alive=np.asarray(entity.alive[lifecycle], dtype=bool).copy(),
        lifecycle_entity_ids=np.asarray(
            entity.entity_id[lifecycle], dtype=np.uint64
        ).copy(),
        lifecycle_genotype=np.asarray(
            entity.genotype[lifecycle], dtype=np.float32
        ).copy(),
        social_full=social_full,
        social_indices=(
            np.empty(0, dtype=np.int32) if social_full else social_rows
        ),
        social_group_ids=np.asarray(
            social.group_id[social_source], dtype=np.uint64
        ).copy(),
        social_direction_x=np.asarray(
            social.group_dir_x[social_source], dtype=np.float32
        ).copy(),
        social_direction_y=np.asarray(
            social.group_dir_y[social_source], dtype=np.float32
        ).copy(),
        base_version=int(base_version),
        next_version=int(base_version) + 1,
        tick=int(tick),
    )
    return plan


__all__ = ["EntityDeviceCommitPlan", "build_entity_device_commit_plan"]
