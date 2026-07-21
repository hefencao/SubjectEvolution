"""Controller proposals and arbitration before action intents."""

from __future__ import annotations

from dataclasses import dataclass, replace
from enum import IntEnum
from typing import Any, Protocol

import numpy as np

from .policy import Action, PolicyDecision


class ControllerKind(IntEnum):
    BODY = 0
    SOCIAL = 1
    LINEAGE = 2
    INSTITUTION = 3
    HERO = 4
    EXTERNAL = 5


@dataclass(frozen=True)
class ControlProposalBatch:
    """One controller's proposals for a batch of physical carriers."""

    carrier_index: np.ndarray
    proposer_subject_id: np.ndarray
    controller_kind: np.ndarray
    decision: PolicyDecision
    submit_tick: int
    # A controller's requested influence.  The default preserves the original
    # single-controller contract for adapters written before weighted
    # arbitration was added.
    weight: np.ndarray | None = None


@dataclass(frozen=True)
class ArbitrationResult:
    """The single decision and provenance permitted to create intents."""

    decision: PolicyDecision
    proposer_subject_id: np.ndarray
    controller_kind: np.ndarray
    # Optional complete attribution for multi-controller experiments.  The
    # primary proposer above remains the dominant contributor for consumers
    # that only understand one controlling subject.
    contributor_subject_ids: np.ndarray | None = None
    contribution_weights: np.ndarray | None = None
    heuristic_applied: np.ndarray | None = None


class ControlArbiter(Protocol):
    """Pluggable controller arbitration before world intent creation."""

    def arbitrate(self, proposals: tuple[ControlProposalBatch, ...]) -> ArbitrationResult:
        """Return one decision per carrier without mutating world state."""


class SingleProposalControlArbiter:
    """Strict reference arbiter for the current one-body-controller model.

    Multi-controller arbiters may merge or resample proposals later, but must
    return this same provenance-bearing result shape.
    """

    def __init__(self, *, validate_unique_carriers: bool = False) -> None:
        # Simulation active rows come from a unique spatial index.  Keep the
        # O(N log N) duplicate assertion opt-in for tests and third-party
        # controller adapters rather than charging it every production tick.
        self.validate_unique_carriers = validate_unique_carriers

    def arbitrate(self, proposals: tuple[ControlProposalBatch, ...]) -> ArbitrationResult:
        if len(proposals) != 1:
            raise ValueError("single-proposal arbitration requires exactly one proposal batch")
        proposal = proposals[0]
        count = proposal.carrier_index.size
        if proposal.carrier_index.ndim != 1:
            raise ValueError("control carrier indices must be one-dimensional")
        if self.validate_unique_carriers and np.unique(proposal.carrier_index).size != count:
            raise ValueError("single-proposal arbitration requires one proposal per carrier")
        if proposal.proposer_subject_id.shape != (count,):
            raise ValueError("control proposer subjects must align with carriers")
        if proposal.controller_kind.shape != (count,):
            raise ValueError("controller kinds must align with carriers")
        if proposal.decision.action.shape != (count,):
            raise ValueError("control decisions must align with carriers")
        if proposal.weight is not None and proposal.weight.shape != (count,):
            raise ValueError("control weights must align with carriers")
        return ArbitrationResult(
            decision=proposal.decision,
            proposer_subject_id=proposal.proposer_subject_id,
            controller_kind=proposal.controller_kind,
            contributor_subject_ids=proposal.proposer_subject_id[:, None],
            contribution_weights=np.ones((count, 1), dtype=np.float32),
            heuristic_applied=np.zeros(count, dtype=bool),
        )


def body_control_proposal(
    carrier_index: Any,
    primary_subject_id: Any,
    decision: PolicyDecision,
    tick: int,
) -> ControlProposalBatch:
    """Adapt the current body policy to the general controller boundary."""
    carriers = np.asarray(carrier_index, dtype=np.int32)
    subjects = np.asarray(primary_subject_id, dtype=np.uint64)
    return ControlProposalBatch(
        carrier_index=carriers,
        proposer_subject_id=subjects,
        controller_kind=np.full(carriers.size, ControllerKind.BODY, dtype=np.uint8),
        decision=decision,
        submit_tick=tick,
        weight=np.ones(carriers.size, dtype=np.float32),
    )


def social_guidance_control_proposal(
    body_proposal: ControlProposalBatch,
    social_subject_id: Any,
    group_direction: tuple[Any, Any],
    guidance_weight: float,
) -> ControlProposalBatch:
    """Create an optional, explicitly heuristic social-direction proposal.

    The proposal only sees the already-published group direction and body
    policy result.  It neither reads world fields nor commits an action.  A
    zero-weight row is a no-op, which keeps one aligned proposal per carrier
    without special-case queueing for non-members.
    """
    count = body_proposal.carrier_index.size
    social_ids = np.asarray(social_subject_id, dtype=np.uint64)
    direction_x = np.asarray(group_direction[0], dtype=np.float32)
    direction_y = np.asarray(group_direction[1], dtype=np.float32)
    if social_ids.shape != (count,) or direction_x.shape != (count,) or direction_y.shape != (count,):
        raise ValueError("social guidance must align with body proposal carriers")
    valid_direction = np.hypot(direction_x, direction_y) > 1e-6
    weight = np.where((social_ids != 0) & valid_direction, guidance_weight, 0.0).astype(np.float32)
    social_decision = replace(
        body_proposal.decision,
        direction_x=direction_x,
        direction_y=direction_y,
    )
    return ControlProposalBatch(
        carrier_index=body_proposal.carrier_index,
        proposer_subject_id=social_ids,
        controller_kind=np.full(count, ControllerKind.SOCIAL, dtype=np.uint8),
        decision=social_decision,
        submit_tick=body_proposal.submit_tick,
        weight=weight,
    )


class HeuristicSocialGuidanceArbiter:
    """Blend a social group's direction into a body resource-move proposal.

    This is deliberately *not* a validated subjecthood or causal-control
    model.  It is an opt-in experimental heuristic that changes directions
    only for existing ``MOVE_RESOURCE`` actions.  It never resamples actions,
    so action masks, random streams, and the GPU policy boundary stay intact.
    """

    is_heuristic = True

    def arbitrate(self, proposals: tuple[ControlProposalBatch, ...]) -> ArbitrationResult:
        if len(proposals) != 2:
            raise ValueError("heuristic social guidance requires body and social proposal batches")
        body, social = proposals
        SingleProposalControlArbiter().arbitrate((body,))
        SingleProposalControlArbiter().arbitrate((social,))
        if not np.array_equal(body.carrier_index, social.carrier_index):
            raise ValueError("social guidance carriers must match body proposal carriers")
        if body.submit_tick != social.submit_tick:
            raise ValueError("social guidance proposals must share a submit tick")

        count = body.carrier_index.size
        weight = (
            np.asarray(social.weight, dtype=np.float32)
            if social.weight is not None
            else np.ones(count, dtype=np.float32)
        )
        if np.any(~np.isfinite(weight)) or np.any((weight < 0.0) | (weight > 1.0)):
            raise ValueError("social guidance weights must be finite values in [0, 1]")
        action = np.asarray(body.decision.action)
        body_x = np.asarray(body.decision.direction_x, dtype=np.float32)
        body_y = np.asarray(body.decision.direction_y, dtype=np.float32)
        social_x = np.asarray(social.decision.direction_x, dtype=np.float32)
        social_y = np.asarray(social.decision.direction_y, dtype=np.float32)
        blended_x = (1.0 - weight) * body_x + weight * social_x
        blended_y = (1.0 - weight) * body_y + weight * social_y
        magnitude = np.hypot(blended_x, blended_y)
        guided = (
            (action == int(Action.MOVE_RESOURCE))
            & (weight > 0.0)
            & (np.hypot(social_x, social_y) > 1e-6)
            & (magnitude > 1e-6)
        )
        direction_x = body_x.copy()
        direction_y = body_y.copy()
        direction_x[guided] = (blended_x[guided] / magnitude[guided]).astype(np.float32)
        direction_y[guided] = (blended_y[guided] / magnitude[guided]).astype(np.float32)
        decision = replace(body.decision, direction_x=direction_x, direction_y=direction_y)

        contributor_subject_ids = np.column_stack((body.proposer_subject_id, social.proposer_subject_id))
        contribution_weights = np.zeros((count, 2), dtype=np.float32)
        contribution_weights[:, 0] = 1.0
        contribution_weights[guided, 0] = 1.0 - weight[guided]
        contribution_weights[guided, 1] = weight[guided]
        # Retain body provenance on ties: action selection remains its policy
        # output, while the complete contribution arrays expose the guidance.
        social_primary = guided & (weight > 0.5)
        proposer_subject_id = np.where(
            social_primary, social.proposer_subject_id, body.proposer_subject_id
        ).astype(np.uint64, copy=False)
        controller_kind = np.where(
            social_primary, social.controller_kind, body.controller_kind
        ).astype(np.uint8, copy=False)
        return ArbitrationResult(
            decision=decision,
            proposer_subject_id=proposer_subject_id,
            controller_kind=controller_kind,
            contributor_subject_ids=contributor_subject_ids,
            contribution_weights=contribution_weights,
            heuristic_applied=guided,
        )


__all__ = [
    "ArbitrationResult",
    "body_control_proposal",
    "ControlArbiter",
    "ControllerKind",
    "ControlProposalBatch",
    "HeuristicSocialGuidanceArbiter",
    "SingleProposalControlArbiter",
    "social_guidance_control_proposal",
]
