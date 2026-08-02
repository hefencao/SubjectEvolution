"""Narrow world-phase adapter for Subject VM token/objective-event records."""
from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

import numpy as np

from ..intents import ActionIntentBatch, ActionResolutionBatch
from ..subject_vm import SubjectVMObjectiveEventBatch

if TYPE_CHECKING:
    from .sim import Simulation


@dataclass(frozen=True)
class SubjectVMObjectiveSnapshot:
    tick: int
    rows: np.ndarray
    event_ids: np.ndarray
    entity_ids: np.ndarray
    subject_ids: np.ndarray
    target_subject_ids: np.ndarray
    action_ids: np.ndarray
    sampled_probability: np.ndarray
    state: np.ndarray


def _state(simulation: "Simulation", rows: np.ndarray) -> np.ndarray:
    ent = simulation.entities
    resource_store = getattr(ent, "resource_store", None)
    store = (
        np.zeros((rows.size, 4), dtype=np.float32)
        if resource_store is None
        else np.asarray(resource_store[rows], dtype=np.float32)
    )
    return np.column_stack(
        (
            ent.energy[rows],
            ent.integrity[rows],
            ent.fertility[rows],
            ent.x[rows],
            ent.y[rows],
            ent.vx[rows],
            ent.vy[rows],
            ent.information_store[rows],
            store,
        )
    ).astype(np.float32, copy=False)


def capture_subject_vm_objective_snapshot(
    simulation: "Simulation", intents: ActionIntentBatch
) -> SubjectVMObjectiveSnapshot | None:
    """Capture facts for a new token event or an active evaluation window."""
    if not (
        simulation.subject_vm.has_pending_thought_tokens
        or simulation.subject_vm.has_active_evaluation_windows
    ):
        return None
    rows = np.asarray(intents.carrier_index, dtype=np.int32)
    targets = np.asarray(intents.target_index, dtype=np.int32)
    target_subject_ids = np.zeros(rows.size, dtype=np.uint64)
    valid = (targets >= 0) & (targets < simulation.entities.alive.size)
    if np.any(valid):
        valid_rows = np.flatnonzero(valid)
        target_rows = targets[valid_rows]
        alive = simulation.entities.alive[target_rows]
        valid_rows = valid_rows[alive]
        target_rows = targets[valid_rows]
        target_subject_ids[valid_rows] = simulation.entities.primary_subject_id[
            target_rows
        ]
    return SubjectVMObjectiveSnapshot(
        tick=int(simulation.tick),
        rows=rows.copy(),
        event_ids=np.asarray(intents.intent_id, dtype=np.uint64).copy(),
        entity_ids=simulation.entities.entity_id[rows].astype(np.uint64, copy=True),
        subject_ids=simulation.entities.primary_subject_id[rows].astype(
            np.uint64, copy=True
        ),
        target_subject_ids=target_subject_ids,
        action_ids=np.asarray(intents.action, dtype=np.int16).copy(),
        sampled_probability=np.asarray(
            intents.sampled_probability, dtype=np.float32
        ).copy(),
        state=_state(simulation, rows).copy(),
    )


def _periodic_delta(after: np.ndarray, before: np.ndarray, extent: float) -> np.ndarray:
    raw = np.asarray(after, dtype=np.float64) - np.asarray(before, dtype=np.float64)
    if extent <= 0.0:
        raise ValueError("subject_vm objective trace extent must be positive")
    return ((raw + 0.5 * extent) % extent - 0.5 * extent).astype(np.float32)


def commit_subject_vm_objective_events(
    simulation: "Simulation",
    snapshot: SubjectVMObjectiveSnapshot | None,
    resolutions: ActionResolutionBatch,
) -> None:
    """Record token events and/or score-free evaluation-window facts."""
    if snapshot is None:
        return
    if int(snapshot.tick) != int(simulation.tick):
        raise ValueError("subject_vm objective snapshot tick mismatch")
    after = _state(simulation, snapshot.rows)
    delta = after - snapshot.state
    if simulation.cfg.world.periodic:
        delta[:, 3] = _periodic_delta(
            after[:, 3], snapshot.state[:, 3], simulation.cfg.world.width
        )
        delta[:, 4] = _periodic_delta(
            after[:, 4], snapshot.state[:, 4], simulation.cfg.world.height
        )
    simulation.subject_vm.commit_objective_events(
        SubjectVMObjectiveEventBatch(
            tick=int(simulation.tick),
            rows=snapshot.rows,
            event_ids=snapshot.event_ids,
            entity_ids=snapshot.entity_ids,
            subject_ids=snapshot.subject_ids,
            action_ids=snapshot.action_ids,
            target_subject_ids=snapshot.target_subject_ids,
            success=np.asarray(resolutions.success, dtype=bool).copy(),
            failure_reason=np.asarray(
                resolutions.failure_reason, dtype=np.uint8
            ).copy(),
            sampled_probability=snapshot.sampled_probability,
            objective_delta=np.asarray(delta, dtype=np.float32),
            resolution_resource_delta=np.asarray(
                resolutions.resource_delta, dtype=np.float32
            ).copy(),
            resolution_internal_resource_delta=np.asarray(
                resolutions.internal_resource_delta, dtype=np.float32
            ).copy(),
            resolution_energy_cost=np.asarray(
                resolutions.energy_cost, dtype=np.float32
            ).copy(),
        )
    )


__all__ = [
    "SubjectVMObjectiveSnapshot",
    "capture_subject_vm_objective_snapshot",
    "commit_subject_vm_objective_events",
]
