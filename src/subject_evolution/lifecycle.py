"""Backend-neutral birth allocation and death-event planning.

Lifecycle planners read immutable array snapshots and return auditable plans.
They never mutate entity arrays, the free-slot pool, or the candidate-subject
graph; one later world-commit phase remains responsible for those writes.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from enum import IntFlag

import numpy as np


class DeathCause(IntFlag):
    """Composable reasons recorded for one end-of-tick death."""

    NONE = 0
    ENERGY_DEPLETED = 1
    INTEGRITY_DEPLETED = 2
    MAX_AGE = 4


@dataclass(frozen=True)
class BirthRequestPlan:
    """Accepted reproduction intents before physical slots are reserved."""

    source_rows: np.ndarray
    parent_indices: np.ndarray
    parent_entity_ids: np.ndarray
    parent_subject_ids: np.ndarray
    tick: int

    @property
    def size(self) -> int:
        return int(self.source_rows.size)


@dataclass(frozen=True)
class BirthAllocationPlan:
    """Birth requests paired with deterministic slots and stable entity IDs."""

    requests: BirthRequestPlan
    slots: np.ndarray
    offspring_entity_ids: np.ndarray
    free_pool_version: int

    @property
    def size(self) -> int:
        return int(self.slots.size)


@dataclass(frozen=True)
class DeathEventPlan:
    """Canonical end-of-tick deaths captured before any slot is reclaimed."""

    entity_indices: np.ndarray
    entity_ids: np.ndarray
    primary_subject_ids: np.ndarray
    cause_code: np.ndarray
    final_energy: np.ndarray
    final_integrity: np.ndarray
    tick: int

    @property
    def size(self) -> int:
        return int(self.entity_indices.size)


def empty_birth_request_plan(tick: int) -> BirthRequestPlan:
    return BirthRequestPlan(
        source_rows=np.empty(0, dtype=np.int32),
        parent_indices=np.empty(0, dtype=np.int32),
        parent_entity_ids=np.empty(0, dtype=np.uint64),
        parent_subject_ids=np.empty(0, dtype=np.uint64),
        tick=int(tick),
    )


def empty_birth_allocation_plan(tick: int, free_pool_version: int = 0) -> BirthAllocationPlan:
    return BirthAllocationPlan(
        requests=empty_birth_request_plan(tick),
        slots=np.empty(0, dtype=np.int32),
        offspring_entity_ids=np.empty(0, dtype=np.uint64),
        free_pool_version=int(free_pool_version),
    )


def empty_death_event_plan(tick: int) -> DeathEventPlan:
    return DeathEventPlan(
        entity_indices=np.empty(0, dtype=np.int32),
        entity_ids=np.empty(0, dtype=np.uint64),
        primary_subject_ids=np.empty(0, dtype=np.uint64),
        cause_code=np.empty(0, dtype=np.uint8),
        final_energy=np.empty(0, dtype=np.float32),
        final_integrity=np.empty(0, dtype=np.float32),
        tick=int(tick),
    )


def plan_birth_allocations(
    requests: BirthRequestPlan,
    free_slots: Sequence[int] | np.ndarray,
    next_entity_id: int,
    free_pool_version: int = 0,
) -> BirthAllocationPlan:
    """Pair accepted requests with a versioned LIFO slot-pool view.

    Only the suffix needed by this allocation is copied.  This keeps planning
    proportional to the accepted birth count even when the CPU pool is a large
    Python list; device and distributed adapters can provide an integer array
    with the same read-only sequence contract.
    """
    if int(free_pool_version) < 0:
        raise ValueError("free-slot pool version must be non-negative")
    request_arrays = (
        requests.source_rows,
        requests.parent_indices,
        requests.parent_entity_ids,
        requests.parent_subject_ids,
    )
    request_values = tuple(np.asarray(value) for value in request_arrays)
    if any(value.ndim != 1 for value in request_values):
        raise ValueError("birth request arrays must be one-dimensional")
    if len({value.size for value in request_values}) != 1:
        raise ValueError("birth request arrays must have the same length")
    if any(not np.issubdtype(value.dtype, np.integer) for value in request_values):
        raise ValueError("birth request arrays must use integer dtypes")
    if int(requests.tick) < 0:
        raise ValueError("birth request tick must be non-negative")
    if requests.size and (
        np.any(request_values[0] < 0)
        or np.any(request_values[1] < 0)
        or np.any(request_values[2] <= 0)
        or np.any(request_values[3] <= 0)
    ):
        raise ValueError("birth requests require non-negative rows and positive stable IDs")
    if requests.size == 0:
        return empty_birth_allocation_plan(requests.tick, free_pool_version)
    try:
        available_count = len(free_slots)
        selected = np.asarray(free_slots[-requests.size :])
    except (TypeError, ValueError) as exc:
        raise ValueError("free-slot pool must be a one-dimensional integer sequence") from exc
    if requests.size > available_count:
        raise ValueError("birth request plan exceeds the free-slot snapshot")
    if selected.ndim != 1 or not np.issubdtype(selected.dtype, np.integer):
        raise ValueError("free-slot pool must be a one-dimensional integer sequence")
    if np.any(selected < 0) or np.any(selected > np.iinfo(np.int32).max):
        raise ValueError("allocated free slots must fit the non-negative int32 range")
    first_id = int(next_entity_id)
    final_id = first_id + requests.size - 1
    if first_id <= 0 or final_id > np.iinfo(np.uint64).max:
        raise OverflowError("offspring entity IDs exceed the uint64 stable-ID range")

    # EntityState historically uses list.pop(), so the final pool element is
    # allocated first.  Encode that policy explicitly in the immutable plan;
    # alternative pool adapters only need to preserve this sequence contract.
    slots = selected[::-1].astype(np.int32, copy=True)
    if np.unique(slots).size != slots.size:
        raise ValueError("allocated free slots must be unique")
    offspring_ids = np.arange(first_id, first_id + requests.size, dtype=np.uint64)
    return BirthAllocationPlan(
        requests=requests,
        slots=slots,
        offspring_entity_ids=offspring_ids,
        free_pool_version=int(free_pool_version),
    )


def plan_death_events(
    *,
    active: np.ndarray,
    entity_ids: np.ndarray,
    primary_subject_ids: np.ndarray,
    energy: np.ndarray,
    integrity: np.ndarray,
    age: np.ndarray,
    max_age: int,
    tick: int,
) -> DeathEventPlan:
    """Build stable slot-ordered death events from an end-of-tick snapshot."""
    active_snapshot = np.asarray(active)
    if active_snapshot.ndim != 1 or not np.issubdtype(active_snapshot.dtype, np.integer):
        raise ValueError("active entity indices must be a one-dimensional integer array")
    active_values = active_snapshot.astype(np.int32, copy=False)
    snapshots = tuple(
        np.asarray(value)
        for value in (entity_ids, primary_subject_ids, energy, integrity, age)
    )
    if any(value.ndim != 1 for value in snapshots):
        raise ValueError("death lifecycle snapshots must be one-dimensional")
    if len({value.size for value in snapshots}) != 1:
        raise ValueError("death lifecycle snapshots must have the same capacity")
    if (
        not np.issubdtype(snapshots[0].dtype, np.integer)
        or not np.issubdtype(snapshots[1].dtype, np.integer)
        or not np.issubdtype(snapshots[2].dtype, np.number)
        or not np.issubdtype(snapshots[3].dtype, np.number)
        or not np.issubdtype(snapshots[4].dtype, np.integer)
    ):
        raise ValueError("death lifecycle snapshots use incompatible dtypes")
    if int(tick) < 0:
        raise ValueError("death event tick must be non-negative")
    if active_values.size == 0:
        return empty_death_event_plan(tick)
    capacity = snapshots[0].size
    if np.any(active_values < 0) or np.any(active_values >= capacity):
        raise ValueError("active entity index is outside the lifecycle snapshot")
    if np.any(active_values[1:] <= active_values[:-1]):
        raise ValueError("active entity indices must be unique and slot ordered")
    if np.any(snapshots[0][active_values] <= 0) or np.any(
        snapshots[1][active_values] <= 0
    ):
        raise ValueError("active death snapshots require positive stable IDs")
    if max_age <= 0:
        raise ValueError("max_age must be positive")

    energy_dead = snapshots[2][active_values] <= 0.0
    integrity_dead = snapshots[3][active_values] <= 0.0
    age_dead = snapshots[4][active_values] >= max_age
    dead_mask = energy_dead | integrity_dead | age_dead
    if not np.any(dead_mask):
        return empty_death_event_plan(tick)
    indices = active_values[dead_mask]
    cause = (
        energy_dead[dead_mask].astype(np.uint8) * int(DeathCause.ENERGY_DEPLETED)
        | integrity_dead[dead_mask].astype(np.uint8) * int(DeathCause.INTEGRITY_DEPLETED)
        | age_dead[dead_mask].astype(np.uint8) * int(DeathCause.MAX_AGE)
    ).astype(np.uint8)
    return DeathEventPlan(
        entity_indices=indices.astype(np.int32, copy=False),
        entity_ids=np.asarray(snapshots[0], dtype=np.uint64)[indices].copy(),
        primary_subject_ids=np.asarray(snapshots[1], dtype=np.uint64)[indices].copy(),
        cause_code=cause,
        final_energy=np.asarray(snapshots[2], dtype=np.float32)[indices].copy(),
        final_integrity=np.asarray(snapshots[3], dtype=np.float32)[indices].copy(),
        tick=int(tick),
    )


__all__ = [
    "BirthAllocationPlan",
    "BirthRequestPlan",
    "DeathCause",
    "DeathEventPlan",
    "empty_birth_allocation_plan",
    "empty_birth_request_plan",
    "empty_death_event_plan",
    "plan_birth_allocations",
    "plan_death_events",
]
