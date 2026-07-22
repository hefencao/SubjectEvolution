"""Controller proposals and arbitration before action intents."""

from __future__ import annotations

from dataclasses import dataclass, replace
from enum import IntEnum
from typing import Any, Protocol

import numpy as np

from .policy import Action, PolicyDecision
from .random_api import RandomContext, Stream, uniform01


class ControllerKind(IntEnum):
    BODY = 0
    SOCIAL = 1
    LINEAGE = 2
    INSTITUTION = 3
    HERO = 4
    EXTERNAL = 5
    AUTONOMY = 6


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
    contributor_controller_kinds: np.ndarray | None = None
    contribution_weights: np.ndarray | None = None
    heuristic_applied: np.ndarray | None = None
    autonomy_applied: np.ndarray | None = None


class ControlArbiter(Protocol):
    """Pluggable controller arbitration before world intent creation."""

    def arbitrate(self, proposals: tuple[ControlProposalBatch, ...]) -> ArbitrationResult:
        """Return one decision per carrier without mutating world state."""


class SingleProposalControlArbiter:
    """Strict reference arbiter for the current one-body-controller model.

    Multi-controller arbiters may merge or resample proposals later, but must
    return this same provenance-bearing result shape.
    """

    scientific_safe = True

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
            contributor_controller_kinds=proposal.controller_kind[:, None],
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


def autonomy_recovery_control_proposal(
    body_proposal: ControlProposalBatch,
    stable_entity_id: Any,
    restored: Any,
    energy: Any,
    local_resource: Any,
    resource_gradient: tuple[Any, Any],
    *,
    run_seed: int,
    max_energy: float,
    activation_energy_fraction: float,
    harvest_threshold: float,
) -> ControlProposalBatch:
    """Build the first explicit, heuristic independent-foraging module.

    The replacement decision sees only carrier energy, local physical
    resource and its gradient.  It deliberately excludes message contents,
    group direction, partners and memory, but uses the body's already chosen
    action category as an activation trigger.  Restored rows activate when a
    social action was selected or energy is low; fleeing is never overridden
    by the current foraging-only module.
    """
    count = body_proposal.carrier_index.size
    stable_ids = np.asarray(stable_entity_id, dtype=np.uint64)
    restored_rows = np.asarray(restored, dtype=bool)
    current_energy = np.asarray(energy, dtype=np.float32)
    resource = np.asarray(local_resource, dtype=np.float32)
    gradient_x = np.asarray(resource_gradient[0], dtype=np.float32)
    gradient_y = np.asarray(resource_gradient[1], dtype=np.float32)
    expected_shape = (count,)
    if any(
        value.shape != expected_shape
        for value in (
            stable_ids,
            restored_rows,
            current_energy,
            resource,
            gradient_x,
            gradient_y,
        )
    ):
        raise ValueError("autonomy recovery inputs must align with body proposal carriers")

    body_action = np.asarray(body_proposal.decision.action, dtype=np.int16)
    social_action = np.isin(
        body_action,
        (int(Action.MOVE_SOCIAL), int(Action.SHARE), int(Action.SIGNAL)),
    )
    low_energy = current_energy < max_energy * activation_energy_fraction
    activated = restored_rows & (social_action | (low_energy & (body_action != int(Action.FLEE))))
    harvest = (resource > harvest_threshold) & (current_energy < max_energy - 1e-6)
    action = np.where(harvest, int(Action.HARVEST), int(Action.MOVE_RESOURCE)).astype(
        np.int16
    )

    magnitude = np.hypot(gradient_x, gradient_y)
    fallback = magnitude < 1e-6
    angle = uniform01(
        RandomContext(
            run_seed,
            body_proposal.submit_tick,
            phase=52,
            stream=Stream.AUTONOMY_RECOVERY,
        ),
        stable_ids,
        draw_index=0,
    ) * (2.0 * np.pi)
    direction_x = np.where(fallback, np.cos(angle), gradient_x)
    direction_y = np.where(fallback, np.sin(angle), gradient_y)
    direction_norm = np.maximum(np.hypot(direction_x, direction_y), 1e-6)
    direction_x = (direction_x / direction_norm).astype(np.float32)
    direction_y = (direction_y / direction_norm).astype(np.float32)
    autonomous_decision = replace(
        body_proposal.decision,
        action=action,
        probability=np.ones(count, dtype=np.float32),
        entropy=np.zeros(count, dtype=np.float32),
        direction_x=direction_x,
        direction_y=direction_y,
        selected_partner=np.full(count, -1, dtype=np.int32),
    )
    return ControlProposalBatch(
        carrier_index=body_proposal.carrier_index,
        proposer_subject_id=body_proposal.proposer_subject_id,
        controller_kind=np.full(count, ControllerKind.AUTONOMY, dtype=np.uint8),
        decision=autonomous_decision,
        submit_tick=body_proposal.submit_tick,
        weight=activated.astype(np.float32),
    )


class AutonomyRecoveryArbiter:
    """Overlay a restored module on any existing controller arbitration.

    This decorator leaves the base arbiter extensible: body-only and
    body/social arbitration keep their own semantics, then an active restored
    module becomes the sole recorded controller for that row.
    """

    is_heuristic = True
    scientific_safe = False

    def __init__(self, base: ControlArbiter) -> None:
        self.base = base

    def arbitrate(self, proposals: tuple[ControlProposalBatch, ...]) -> ArbitrationResult:
        autonomy_positions = [
            index
            for index, proposal in enumerate(proposals)
            if proposal.controller_kind.size
            and np.all(proposal.controller_kind == int(ControllerKind.AUTONOMY))
        ]
        if len(autonomy_positions) != 1:
            raise ValueError("autonomy recovery requires exactly one autonomy proposal batch")
        autonomy_index = autonomy_positions[0]
        autonomy = proposals[autonomy_index]
        base_proposals = proposals[:autonomy_index] + proposals[autonomy_index + 1 :]
        base = self.base.arbitrate(base_proposals)
        if not np.array_equal(base_proposals[0].carrier_index, autonomy.carrier_index):
            raise ValueError("autonomy recovery carriers must match base control carriers")
        if autonomy.weight is None:
            raise ValueError("autonomy recovery proposal requires an activation mask")
        applied = np.asarray(autonomy.weight, dtype=np.float32) > 0.0
        count = applied.size
        if autonomy.weight.shape != (count,):
            raise ValueError("autonomy recovery weights must align with carriers")

        def choose(base_value: Any, autonomy_value: Any) -> np.ndarray:
            original = np.asarray(base_value)
            replacement = np.asarray(autonomy_value)
            if original.shape != replacement.shape:
                raise ValueError("autonomy decision shape must match base decision")
            selector = applied.reshape((count,) + (1,) * (original.ndim - 1))
            return np.where(selector, replacement, original)

        decision = PolicyDecision(
            action=choose(base.decision.action, autonomy.decision.action),
            probability=choose(base.decision.probability, autonomy.decision.probability),
            entropy=choose(base.decision.entropy, autonomy.decision.entropy),
            direction_x=choose(base.decision.direction_x, autonomy.decision.direction_x),
            direction_y=choose(base.decision.direction_y, autonomy.decision.direction_y),
            selected_partner=choose(
                base.decision.selected_partner,
                autonomy.decision.selected_partner,
            ),
            # Body logits remain an audit of the displaced policy proposal;
            # module application is carried by ``autonomy_applied``.
            logits=np.asarray(base.decision.logits),
        )
        base_subjects = (
            np.asarray(base.contributor_subject_ids, dtype=np.uint64)
            if base.contributor_subject_ids is not None
            else np.asarray(base.proposer_subject_id, dtype=np.uint64)[:, None]
        )
        base_weights = (
            np.asarray(base.contribution_weights, dtype=np.float32)
            if base.contribution_weights is not None
            else np.ones((count, 1), dtype=np.float32)
        )
        base_kinds = (
            np.asarray(base.contributor_controller_kinds, dtype=np.uint8)
            if base.contributor_controller_kinds is not None
            else np.asarray(base.controller_kind, dtype=np.uint8)[:, None]
        )
        contributor_subject_ids = np.column_stack(
            (base_subjects, autonomy.proposer_subject_id)
        )
        contributor_controller_kinds = np.column_stack(
            (base_kinds, autonomy.controller_kind)
        )
        contribution_weights = np.column_stack(
            (base_weights, np.zeros(count, dtype=np.float32))
        )
        contribution_weights[applied, :-1] = 0.0
        contribution_weights[applied, -1] = 1.0
        heuristic_applied = (
            np.asarray(base.heuristic_applied, dtype=bool).copy()
            if base.heuristic_applied is not None
            else np.zeros(count, dtype=bool)
        )
        heuristic_applied[applied] = False
        return ArbitrationResult(
            decision=decision,
            proposer_subject_id=np.where(
                applied,
                autonomy.proposer_subject_id,
                base.proposer_subject_id,
            ).astype(np.uint64, copy=False),
            controller_kind=np.where(
                applied,
                autonomy.controller_kind,
                base.controller_kind,
            ).astype(np.uint8, copy=False),
            contributor_subject_ids=contributor_subject_ids,
            contributor_controller_kinds=contributor_controller_kinds,
            contribution_weights=contribution_weights,
            heuristic_applied=heuristic_applied,
            autonomy_applied=applied,
        )


class HeuristicSocialGuidanceArbiter:
    """Blend a social group's direction into a body resource-move proposal.

    This is deliberately *not* a validated subjecthood or causal-control
    model.  It is an opt-in experimental heuristic that changes directions
    only for existing ``MOVE_RESOURCE`` actions.  It never resamples actions,
    so action masks, random streams, and the GPU policy boundary stay intact.
    """

    is_heuristic = True
    scientific_safe = False

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
        contributor_controller_kinds = np.column_stack(
            (body.controller_kind, social.controller_kind)
        )
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
            contributor_controller_kinds=contributor_controller_kinds,
            contribution_weights=contribution_weights,
            heuristic_applied=guided,
        )


__all__ = [
    "ArbitrationResult",
    "AutonomyRecoveryArbiter",
    "autonomy_recovery_control_proposal",
    "body_control_proposal",
    "ControlArbiter",
    "ControllerKind",
    "ControlProposalBatch",
    "HeuristicSocialGuidanceArbiter",
    "SingleProposalControlArbiter",
    "social_guidance_control_proposal",
]
