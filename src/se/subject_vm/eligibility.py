"""Short-lived local eligibility carriers for Subject VM Stage 3B-1.

Eligibility is local graph state, not a persistent execution log.  It records
only graph-selected signed node activity and bounded edge transmission, decays
by elapsed ticks, and expires at a fixed horizon.  Objective events do not
change eligibility in this stage, and eligibility changes no graph parameter.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .storage import LOCAL_ELIGIBILITY_FLAG, SubjectVMStorage


@dataclass
class SubjectVMLocalEligibilityUsage:
    tick: int
    active_rows: int
    decay_calls: int = 0
    decayed_nodes: int = 0
    decayed_edges: int = 0
    expired_nodes: int = 0
    expired_edges: int = 0
    node_marks: int = 0
    edge_marks: int = 0


def _advance_values(
    values: np.ndarray,
    ages: np.ndarray,
    *,
    elapsed: int,
    decay: float,
    max_age: int,
) -> tuple[int, int]:
    active = values != 0.0
    count = int(np.count_nonzero(active))
    if count == 0:
        return 0, 0
    values[active] *= np.float32(decay**elapsed)
    current_age = ages[active].astype(np.uint32) + np.uint32(elapsed)
    expired_active = (current_age > np.uint32(max_age)) | (values[active] == 0.0)
    ages[active] = np.minimum(current_age, np.iinfo(np.uint16).max).astype(np.uint16)
    if np.any(expired_active):
        active_indices = np.flatnonzero(active)
        expired_indices = active_indices[expired_active]
        values[expired_indices] = 0.0
        ages[expired_indices] = 0
    return count, int(np.count_nonzero(expired_active))


def advance_local_eligibility(
    storage: SubjectVMStorage, *, rows: np.ndarray, tick: int
) -> SubjectVMLocalEligibilityUsage | None:
    """Decay local carriers by elapsed ticks without reading world outcomes."""
    if not storage.cfg.eligibility_enabled:
        return None
    normalized = storage._rows(rows)
    usage = SubjectVMLocalEligibilityUsage(
        tick=int(tick), active_rows=int(normalized.size)
    )
    cfg = storage.cfg.eligibility
    for row in normalized.tolist():
        previous_tick = int(storage.eligibility_last_tick[row])
        if previous_tick > int(tick):
            raise ValueError("subject_vm eligibility tick cannot move backwards")
        elapsed = 0 if previous_tick < 0 else int(tick) - previous_tick
        storage.eligibility_last_tick[row] = int(tick)
        if elapsed <= 0:
            continue
        usage.decay_calls += 1
        node_count, node_expired = _advance_values(
            storage.node_eligibility_value[row],
            storage.node_eligibility_age[row],
            elapsed=elapsed,
            decay=float(cfg.decay),
            max_age=int(cfg.max_age_ticks),
        )
        edge_count, edge_expired = _advance_values(
            storage.eligibility_value[row],
            storage.eligibility_age[row],
            elapsed=elapsed,
            decay=float(cfg.decay),
            max_age=int(cfg.max_age_ticks),
        )
        usage.decayed_nodes += node_count
        usage.decayed_edges += edge_count
        usage.expired_nodes += node_expired
        usage.expired_edges += edge_expired
    return usage


def _mark(
    values: np.ndarray,
    ages: np.ndarray,
    index: int,
    *,
    local_activity: float,
    gate: float,
    clip: float,
) -> bool:
    mark = float(local_activity) * float(gate)
    if mark == 0.0:
        return False
    if not np.isfinite(mark):
        raise ValueError("subject_vm local eligibility mark must be finite")
    updated = float(np.clip(float(values[index]) + mark, -clip, clip))
    values[index] = np.float32(updated)
    ages[index] = np.uint16(0)
    return True


def mark_node_eligibility(
    storage: SubjectVMStorage, *, row: int, node: int, local_activity: float
) -> bool:
    if not storage.cfg.eligibility_enabled:
        return False
    if (
        storage.node_plasticity_flags[row, node] & LOCAL_ELIGIBILITY_FLAG
    ) == 0:
        return False
    return _mark(
        storage.node_eligibility_value[row],
        storage.node_eligibility_age[row],
        node,
        local_activity=local_activity,
        gate=float(storage.node_eligibility_gate[row, node]),
        clip=float(storage.cfg.eligibility.clip),
    )


def mark_edge_eligibility(
    storage: SubjectVMStorage, *, row: int, edge: int, local_activity: float
) -> bool:
    if not storage.cfg.eligibility_enabled:
        return False
    if (storage.plasticity_flags[row, edge] & LOCAL_ELIGIBILITY_FLAG) == 0:
        return False
    return _mark(
        storage.eligibility_value[row],
        storage.eligibility_age[row],
        edge,
        local_activity=local_activity,
        gate=float(storage.edge_eligibility_gate[row, edge]),
        clip=float(storage.cfg.eligibility.clip),
    )


__all__ = [
    "SubjectVMLocalEligibilityUsage",
    "advance_local_eligibility",
    "mark_edge_eligibility",
    "mark_node_eligibility",
]
