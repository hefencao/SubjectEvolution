"""Sparse K3 knowledge-to-policy residual plans.

K3 keeps the inherited linear policy intact and adds a separately versioned,
auditable residual.  Local outcome vectors remain five-dimensional; each
carrier's inherited K3 preference traits decide how those dimensions are
weighted.  No global reward or optimizer is introduced.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np

from .config import KnowledgeConfig
from .knowledge import (
    ACQUISITION_PRIVATE_EXPERIENCE,
    ACQUISITION_TRANSFER,
    KnowledgeObservationPlan,
    OUTCOME_WIDTH,
)


@dataclass(frozen=True)
class KnowledgePolicyPlan:
    """Sparse action-logit residuals for one immutable policy observation."""

    tick: int
    active_rows: np.ndarray
    entity_ids: np.ndarray
    holder_subject_ids: np.ndarray
    context_keys: np.ndarray
    action_ids: np.ndarray
    residuals: np.ndarray
    support_copy_counts: np.ndarray
    private_support_counts: np.ndarray
    transfer_support_counts: np.ndarray
    unverified_transfer_support_counts: np.ndarray
    reliability_mass: np.ndarray
    weighted_outcome_vectors: np.ndarray

    @classmethod
    def empty(cls, tick: int = 0) -> "KnowledgePolicyPlan":
        return cls(
            tick=int(tick),
            active_rows=np.empty(0, dtype=np.int32),
            entity_ids=np.empty(0, dtype=np.uint64),
            holder_subject_ids=np.empty(0, dtype=np.uint64),
            context_keys=np.empty(0, dtype=np.uint64),
            action_ids=np.empty(0, dtype=np.int16),
            residuals=np.empty(0, dtype=np.float32),
            support_copy_counts=np.empty(0, dtype=np.uint16),
            private_support_counts=np.empty(0, dtype=np.uint16),
            transfer_support_counts=np.empty(0, dtype=np.uint16),
            unverified_transfer_support_counts=np.empty(0, dtype=np.uint16),
            reliability_mass=np.empty(0, dtype=np.float32),
            weighted_outcome_vectors=np.empty((0, OUTCOME_WIDTH), dtype=np.float32),
        )

    @property
    def size(self) -> int:
        return int(self.residuals.size)

    @property
    def influenced_entity_count(self) -> int:
        return int(np.unique(self.active_rows).size) if self.size else 0

    @property
    def semantic_transfer_nbytes(self) -> int:
        return int(
            self.active_rows.nbytes
            + self.action_ids.nbytes
            + self.residuals.nbytes
        )

    def validate(self, active_count: int, action_count: int) -> None:
        count = self.size
        vectors = (
            self.active_rows,
            self.entity_ids,
            self.holder_subject_ids,
            self.context_keys,
            self.action_ids,
            self.residuals,
            self.support_copy_counts,
            self.private_support_counts,
            self.transfer_support_counts,
            self.unverified_transfer_support_counts,
            self.reliability_mass,
        )
        if any(np.asarray(value).shape != (count,) for value in vectors):
            raise ValueError("knowledge policy plan vectors must align")
        if self.weighted_outcome_vectors.shape != (count, OUTCOME_WIDTH):
            raise ValueError("knowledge policy outcome diagnostics must have width five")
        if count and (
            np.any(self.active_rows < 0)
            or np.any(self.active_rows >= active_count)
            or np.any(self.entity_ids == 0)
            or np.any(self.holder_subject_ids == 0)
            or np.any(self.context_keys == 0)
            or np.any(self.action_ids < 0)
            or np.any(self.action_ids >= action_count)
            or np.any(~np.isfinite(self.residuals))
            or np.any(~np.isfinite(self.reliability_mass))
            or np.any(~np.isfinite(self.weighted_outcome_vectors))
            or np.any(self.support_copy_counts == 0)
        ):
            raise ValueError("knowledge policy plan contains invalid values")
        if count:
            flat = self.active_rows.astype(np.int64) * action_count + self.action_ids
            if np.any(flat[1:] <= flat[:-1]):
                raise ValueError("knowledge policy plan keys must be unique and ordered")

    def materialize(self, xp: Any, active_count: int, action_count: int) -> Any:
        """Materialize the sparse plan on NumPy or CuPy without changing order."""
        dense = xp.zeros((active_count, action_count), dtype=xp.float32)
        if self.size:
            rows = xp.asarray(self.active_rows, dtype=xp.int32)
            actions = xp.asarray(self.action_ids, dtype=xp.int32)
            values = xp.asarray(self.residuals, dtype=xp.float32)
            dense[rows, actions] = values
        return dense


def build_knowledge_policy_plan(
    observation: KnowledgeObservationPlan,
    *,
    tick: int,
    entity_ids: np.ndarray,
    holder_subject_ids: np.ndarray,
    context_keys: np.ndarray,
    outcome_preferences: np.ndarray,
    use_strength: np.ndarray,
    config: KnowledgeConfig,
    action_count: int,
) -> KnowledgePolicyPlan:
    """Build deterministic sparse residuals from published holder copies.

    Duplicate copies do not add unbounded influence: each holder/action cell is
    a reliability-weighted mean, then multiplied by that carrier's inherited
    use-strength trait and the configured residual bound.
    """
    ids = np.asarray(entity_ids, dtype=np.uint64)
    holders = np.asarray(holder_subject_ids, dtype=np.uint64)
    contexts = np.asarray(context_keys, dtype=np.uint64)
    preferences = np.asarray(outcome_preferences, dtype=np.float32)
    strengths = np.asarray(use_strength, dtype=np.float32)
    active_count = ids.size
    if holders.shape != (active_count,) or contexts.shape != (active_count,):
        raise ValueError("knowledge policy active IDs and contexts must align")
    if preferences.shape != (active_count, OUTCOME_WIDTH):
        raise ValueError("knowledge outcome preferences must have width five")
    if strengths.shape != (active_count,):
        raise ValueError("knowledge use strengths must align with active rows")
    if not config.policy_influence_enabled or observation.copy_count == 0 or active_count == 0:
        return KnowledgePolicyPlan.empty(tick)

    # Expand holder segments once.  The observation itself remains the compact,
    # holder-segmented public boundary used by K1/K2.
    copy_holders = np.repeat(
        observation.holder_subject_ids,
        observation.holder_counts.astype(np.int64, copy=False),
    )
    if copy_holders.shape != observation.copy_ids.shape:
        raise ValueError("knowledge observation holder segments are malformed")

    holder_order = np.argsort(holders, kind="stable")
    sorted_holders = holders[holder_order]
    positions = np.searchsorted(sorted_holders, copy_holders)
    in_range = positions < sorted_holders.size
    safe_positions = np.minimum(positions, max(sorted_holders.size - 1, 0))
    matched_holder = in_range & (sorted_holders[safe_positions] == copy_holders)
    if not np.any(matched_holder):
        return KnowledgePolicyPlan.empty(tick)
    copy_rows = np.flatnonzero(matched_holder)
    active_rows = holder_order[positions[copy_rows]].astype(np.int32, copy=False)

    sample_counts = observation.sample_counts[copy_rows].astype(np.float64)
    confidences = observation.confidences[copy_rows].astype(np.float64)
    acquisition = observation.acquisition_kinds[copy_rows]
    action_ids = observation.action_ids[copy_rows]
    valid = (
        (observation.context_keys[copy_rows] == contexts[active_rows])
        & (action_ids >= 0)
        & (action_ids < action_count)
        & (confidences >= float(config.policy_min_confidence))
    )
    if not np.any(valid):
        return KnowledgePolicyPlan.empty(tick)
    copy_rows = copy_rows[valid]
    active_rows = active_rows[valid]
    sample_counts = sample_counts[valid]
    confidences = confidences[valid]
    acquisition = acquisition[valid]
    action_ids = action_ids[valid].astype(np.int16, copy=False)

    saturation = max(float(config.policy_sample_saturation), 1e-12)
    locally_verified = sample_counts >= float(config.policy_min_local_samples)
    local_evidence = sample_counts / (sample_counts + saturation)
    unverified_transfer = (
        (acquisition == ACQUISITION_TRANSFER) & ~locally_verified
    )
    evidence = np.where(
        locally_verified,
        local_evidence,
        np.where(
            unverified_transfer,
            float(config.policy_unverified_transfer_weight),
            0.0,
        ),
    )
    reliability = confidences * evidence
    keep = reliability > 0.0
    if not np.any(keep):
        return KnowledgePolicyPlan.empty(tick)
    copy_rows = copy_rows[keep]
    active_rows = active_rows[keep]
    sample_counts = sample_counts[keep]
    acquisition = acquisition[keep]
    action_ids = action_ids[keep]
    reliability = reliability[keep]
    unverified_transfer = unverified_transfer[keep]

    scales = np.asarray(config.policy_outcome_scales, dtype=np.float64)
    outcomes = observation.outcome_vectors[copy_rows].astype(np.float64)
    normalized = np.clip(
        outcomes / scales[None, :],
        -float(config.policy_outcome_clip),
        float(config.policy_outcome_clip),
    )
    preference = preferences[active_rows].astype(np.float64)
    # Division by width bounds the dot product when both explicit components
    # lie in [-1, 1].  It does not impose a universal sign or scalar reward.
    copy_value = np.sum(preference * normalized, axis=1) / float(OUTCOME_WIDTH)
    flat_key = active_rows.astype(np.int64) * int(action_count) + action_ids.astype(np.int64)
    order = np.argsort(flat_key, kind="stable")
    flat_key = flat_key[order]
    active_rows = active_rows[order]
    action_ids = action_ids[order]
    reliability = reliability[order]
    normalized = normalized[order]
    copy_value = copy_value[order]
    acquisition = acquisition[order]
    unverified_transfer = unverified_transfer[order]

    starts = np.r_[0, np.flatnonzero(flat_key[1:] != flat_key[:-1]) + 1]
    unique_key = flat_key[starts]
    weight_sum = np.add.reduceat(reliability, starts)
    weighted_value = np.add.reduceat(reliability * copy_value, starts)
    weighted_outcomes = np.stack(
        [np.add.reduceat(reliability * normalized[:, dim], starts) for dim in range(OUTCOME_WIDTH)],
        axis=1,
    ) / weight_sum[:, None]
    support = np.diff(np.r_[starts, flat_key.size]).astype(np.uint16)
    private_support = np.add.reduceat(
        (acquisition == ACQUISITION_PRIVATE_EXPERIENCE).astype(np.uint16), starts
    ).astype(np.uint16)
    transfer_support = np.add.reduceat(
        (acquisition == ACQUISITION_TRANSFER).astype(np.uint16), starts
    ).astype(np.uint16)
    unverified_support = np.add.reduceat(
        unverified_transfer.astype(np.uint16), starts
    ).astype(np.uint16)

    out_rows = (unique_key // action_count).astype(np.int32)
    out_actions = (unique_key % action_count).astype(np.int16)
    mean_value = weighted_value / weight_sum
    residual = (
        float(config.policy_max_abs_logit_residual)
        * strengths[out_rows].astype(np.float64)
        * mean_value
    )
    residual = np.clip(
        residual,
        -float(config.policy_max_abs_logit_residual),
        float(config.policy_max_abs_logit_residual),
    ).astype(np.float32)
    nonzero = residual != 0.0
    plan = KnowledgePolicyPlan(
        tick=int(tick),
        active_rows=out_rows[nonzero],
        entity_ids=ids[out_rows[nonzero]].copy(),
        holder_subject_ids=holders[out_rows[nonzero]].copy(),
        context_keys=contexts[out_rows[nonzero]].copy(),
        action_ids=out_actions[nonzero],
        residuals=residual[nonzero],
        support_copy_counts=support[nonzero],
        private_support_counts=private_support[nonzero],
        transfer_support_counts=transfer_support[nonzero],
        unverified_transfer_support_counts=unverified_support[nonzero],
        reliability_mass=weight_sum[nonzero].astype(np.float32),
        weighted_outcome_vectors=weighted_outcomes[nonzero].astype(np.float32),
    )
    plan.validate(active_count, action_count)
    return plan


__all__ = ["KnowledgePolicyPlan", "build_knowledge_policy_plan"]
