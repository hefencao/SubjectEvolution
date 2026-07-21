"""The explicit proposal -> intent -> resolution boundary for world actions."""

from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum
import numpy as np

from .policy import Action, PolicyDecision


class FailureReason(IntEnum):
    NONE = 0
    INVALID_TARGET = 1
    INSUFFICIENT_CAPACITY = 2
    INSUFFICIENT_RESOURCE = 3
    DISABLED_BY_INTERVENTION = 4


@dataclass(frozen=True)
class ActionIntentBatch:
    """Read-only action requests produced from a stable observation snapshot."""

    intent_id: np.ndarray
    carrier_index: np.ndarray
    carrier_id: np.ndarray
    action: np.ndarray
    target_index: np.ndarray
    direction_x: np.ndarray
    direction_y: np.ndarray
    sampled_probability: np.ndarray
    submit_tick: int
    proposer_subject_id: np.ndarray | None = None
    controller_kind: np.ndarray | None = None
    contributor_subject_ids: np.ndarray | None = None
    contribution_weights: np.ndarray | None = None
    heuristic_control: np.ndarray | None = None


@dataclass
class ActionResolutionBatch:
    """The sole input accepted by the world-commit phase."""

    intent_id: np.ndarray
    success: np.ndarray
    failure_reason: np.ndarray
    resource_delta: np.ndarray
    energy_cost: np.ndarray


def build_intents(
    active: np.ndarray,
    stable_ids: np.ndarray,
    decision: PolicyDecision,
    tick: int,
    *,
    proposer_subject_id: np.ndarray | None = None,
    controller_kind: np.ndarray | None = None,
    contributor_subject_ids: np.ndarray | None = None,
    contribution_weights: np.ndarray | None = None,
    heuristic_control: np.ndarray | None = None,
) -> ActionIntentBatch:
    """Turn policy output into stable, auditable action intents.

    Intent IDs use the carrier's stable ID plus the tick context.  They are
    never derived from the temporary dense array position.
    """
    carriers = np.asarray(active, dtype=np.int32)
    carrier_id = stable_ids[carriers].astype(np.uint64, copy=True)
    tick_bits = np.uint64((int(tick) << 32) & 0xFFFFFFFFFFFFFFFF)
    proposer = (
        np.asarray(proposer_subject_id, dtype=np.uint64)
        if proposer_subject_id is not None
        else None
    )
    kind = np.asarray(controller_kind, dtype=np.uint8) if controller_kind is not None else None
    contributors = (
        np.asarray(contributor_subject_ids, dtype=np.uint64)
        if contributor_subject_ids is not None
        else None
    )
    weights = (
        np.asarray(contribution_weights, dtype=np.float32)
        if contribution_weights is not None
        else None
    )
    heuristic = np.asarray(heuristic_control, dtype=bool) if heuristic_control is not None else None
    if proposer is not None and proposer.shape != carrier_id.shape:
        raise ValueError("proposer subject ids must align with active carriers")
    if kind is not None and kind.shape != carrier_id.shape:
        raise ValueError("controller kinds must align with active carriers")
    if contributors is not None and (contributors.ndim != 2 or contributors.shape[0] != carrier_id.size):
        raise ValueError("control contributors must have one row per active carrier")
    if weights is not None and (weights.ndim != 2 or weights.shape != (carrier_id.size, contributors.shape[1] if contributors is not None else 0)):
        raise ValueError("control contribution weights must align with contributors")
    if (contributors is None) != (weights is None):
        raise ValueError("control contributors and weights must be supplied together")
    if heuristic is not None and heuristic.shape != carrier_id.shape:
        raise ValueError("heuristic control flags must align with active carriers")
    return ActionIntentBatch(
        intent_id=carrier_id ^ tick_bits,
        carrier_index=carriers,
        carrier_id=carrier_id,
        action=decision.action.astype(np.int16, copy=True),
        target_index=decision.selected_partner.astype(np.int32, copy=True),
        direction_x=decision.direction_x.astype(np.float32, copy=True),
        direction_y=decision.direction_y.astype(np.float32, copy=True),
        sampled_probability=decision.probability.astype(np.float32, copy=True),
        submit_tick=tick,
        proposer_subject_id=proposer,
        controller_kind=kind,
        contributor_subject_ids=contributors,
        contribution_weights=weights,
        heuristic_control=heuristic,
    )


def empty_resolutions(intents: ActionIntentBatch) -> ActionResolutionBatch:
    return ActionResolutionBatch(
        intent_id=intents.intent_id.copy(),
        success=np.ones(intents.intent_id.size, dtype=bool),
        failure_reason=np.full(intents.intent_id.size, FailureReason.NONE, dtype=np.uint8),
        resource_delta=np.zeros((intents.intent_id.size, 4), dtype=np.float32),
        energy_cost=np.zeros(intents.intent_id.size, dtype=np.float32),
    )


def action_rows(intents: ActionIntentBatch, action: Action) -> np.ndarray:
    return np.flatnonzero(intents.action == int(action)).astype(np.int32)
