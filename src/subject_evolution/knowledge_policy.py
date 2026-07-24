"""Sparse K3 knowledge-to-policy residual plans.

K3 keeps the inherited linear policy intact and adds a separately versioned,
auditable residual.  Local outcome vectors remain five-dimensional; each
carrier's inherited K3 preference traits decide how those dimensions are
weighted.  No global reward or optimizer is introduced.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np

from .config import KnowledgeConfig
from .knowledge import (
    ACQUISITION_PRIVATE_EXPERIENCE,
    ACQUISITION_TRANSFER,
    KnowledgeObservationPlan,
    OUTCOME_WIDTH,
)
from .latent_knowledge import (
    LATENT_MLP_ROUTER_SCHEMA,
    LATENT_ROUTER_SCHEMA,
    LatentRouterBatch,
    VariableLatentContentStore,
    build_latent_router_batch,
    route_latent_router_batch,
    select_latent_router_batch,
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
    latent_dimension_counts: np.ndarray = field(
        default_factory=lambda: np.empty(0, dtype=np.uint32)
    )
    latent_max_widths: np.ndarray = field(
        default_factory=lambda: np.empty(0, dtype=np.uint16)
    )
    quantized_residuals: np.ndarray = field(
        default_factory=lambda: np.empty(0, dtype=np.int32)
    )
    # Optional L1 shadow residuals carried by the L2 schema.  These use their
    # own sparse keys because an action can be zero in L2 but nonzero in L1.
    comparison_active_rows: np.ndarray = field(
        default_factory=lambda: np.empty(0, dtype=np.int32)
    )
    comparison_action_ids: np.ndarray = field(
        default_factory=lambda: np.empty(0, dtype=np.int16)
    )
    comparison_residuals: np.ndarray = field(
        default_factory=lambda: np.empty(0, dtype=np.float32)
    )
    comparison_quantized_residuals: np.ndarray = field(
        default_factory=lambda: np.empty(0, dtype=np.int32)
    )
    router_saturation_counts: np.ndarray = field(
        default_factory=lambda: np.empty(0, dtype=np.uint32)
    )
    router_clipping_counts: np.ndarray = field(
        default_factory=lambda: np.empty(0, dtype=np.uint32)
    )
    router_hidden_abs_sums: np.ndarray = field(
        default_factory=lambda: np.empty(0, dtype=np.uint64)
    )
    router_hidden_active_counts: np.ndarray = field(
        default_factory=lambda: np.empty(0, dtype=np.uint32)
    )
    selection_candidate_counts: np.ndarray = field(
        default_factory=lambda: np.empty(0, dtype=np.uint16)
    )
    selection_selected_counts: np.ndarray = field(
        default_factory=lambda: np.empty(0, dtype=np.uint16)
    )
    selection_tie_counts: np.ndarray = field(
        default_factory=lambda: np.empty(0, dtype=np.uint16)
    )
    selection_score_thresholds_q: np.ndarray = field(
        default_factory=lambda: np.empty(0, dtype=np.int64)
    )
    selection_active_rows: np.ndarray = field(
        default_factory=lambda: np.empty(0, dtype=np.int32)
    )
    selection_copy_ids: np.ndarray = field(
        default_factory=lambda: np.empty(0, dtype=np.uint64)
    )
    selection_content_ids: np.ndarray = field(
        default_factory=lambda: np.empty(0, dtype=np.uint64)
    )
    selection_scores_q: np.ndarray = field(
        default_factory=lambda: np.empty(0, dtype=np.int64)
    )
    # Per-entity work diagnostics are independent of nonzero published action
    # cells.  They preserve selection and compute costs even when Top-k is zero
    # or the selected router happens to emit an all-zero residual.
    work_active_rows: np.ndarray = field(
        default_factory=lambda: np.empty(0, dtype=np.int32)
    )
    work_entity_ids: np.ndarray = field(
        default_factory=lambda: np.empty(0, dtype=np.uint64)
    )
    work_holder_subject_ids: np.ndarray = field(
        default_factory=lambda: np.empty(0, dtype=np.uint64)
    )
    work_context_keys: np.ndarray = field(
        default_factory=lambda: np.empty(0, dtype=np.uint64)
    )
    work_support_copy_counts: np.ndarray = field(
        default_factory=lambda: np.empty(0, dtype=np.uint16)
    )
    work_latent_dimension_counts: np.ndarray = field(
        default_factory=lambda: np.empty(0, dtype=np.uint32)
    )
    work_latent_max_widths: np.ndarray = field(
        default_factory=lambda: np.empty(0, dtype=np.uint16)
    )
    work_router_saturation_counts: np.ndarray = field(
        default_factory=lambda: np.empty(0, dtype=np.uint32)
    )
    work_router_clipping_counts: np.ndarray = field(
        default_factory=lambda: np.empty(0, dtype=np.uint32)
    )
    work_router_hidden_active_counts: np.ndarray = field(
        default_factory=lambda: np.empty(0, dtype=np.uint32)
    )
    work_selection_candidate_counts: np.ndarray = field(
        default_factory=lambda: np.empty(0, dtype=np.uint16)
    )
    work_selection_selected_counts: np.ndarray = field(
        default_factory=lambda: np.empty(0, dtype=np.uint16)
    )
    work_selection_tie_counts: np.ndarray = field(
        default_factory=lambda: np.empty(0, dtype=np.uint16)
    )
    work_selection_score_thresholds_q: np.ndarray = field(
        default_factory=lambda: np.empty(0, dtype=np.int64)
    )
    router_schema: str | None = None
    selection_schema: str | None = None

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
            latent_dimension_counts=np.empty(0, dtype=np.uint32),
            latent_max_widths=np.empty(0, dtype=np.uint16),
            quantized_residuals=np.empty(0, dtype=np.int32),
            comparison_active_rows=np.empty(0, dtype=np.int32),
            comparison_action_ids=np.empty(0, dtype=np.int16),
            comparison_residuals=np.empty(0, dtype=np.float32),
            comparison_quantized_residuals=np.empty(0, dtype=np.int32),
            router_saturation_counts=np.empty(0, dtype=np.uint32),
            router_clipping_counts=np.empty(0, dtype=np.uint32),
            router_hidden_abs_sums=np.empty(0, dtype=np.uint64),
            router_hidden_active_counts=np.empty(0, dtype=np.uint32),
            selection_candidate_counts=np.empty(0, dtype=np.uint16),
            selection_selected_counts=np.empty(0, dtype=np.uint16),
            selection_tie_counts=np.empty(0, dtype=np.uint16),
            selection_score_thresholds_q=np.empty(0, dtype=np.int64),
            selection_active_rows=np.empty(0, dtype=np.int32),
            selection_copy_ids=np.empty(0, dtype=np.uint64),
            selection_content_ids=np.empty(0, dtype=np.uint64),
            selection_scores_q=np.empty(0, dtype=np.int64),
            work_active_rows=np.empty(0, dtype=np.int32),
            work_entity_ids=np.empty(0, dtype=np.uint64),
            work_holder_subject_ids=np.empty(0, dtype=np.uint64),
            work_context_keys=np.empty(0, dtype=np.uint64),
            work_support_copy_counts=np.empty(0, dtype=np.uint16),
            work_latent_dimension_counts=np.empty(0, dtype=np.uint32),
            work_latent_max_widths=np.empty(0, dtype=np.uint16),
            work_router_saturation_counts=np.empty(0, dtype=np.uint32),
            work_router_clipping_counts=np.empty(0, dtype=np.uint32),
            work_router_hidden_active_counts=np.empty(0, dtype=np.uint32),
            work_selection_candidate_counts=np.empty(0, dtype=np.uint16),
            work_selection_selected_counts=np.empty(0, dtype=np.uint16),
            work_selection_tie_counts=np.empty(0, dtype=np.uint16),
            work_selection_score_thresholds_q=np.empty(0, dtype=np.int64),
            router_schema=None,
            selection_schema=None,
        )

    @property
    def size(self) -> int:
        return int(self.residuals.size)

    @property
    def comparison_size(self) -> int:
        return int(self.comparison_residuals.size)

    @property
    def influenced_entity_count(self) -> int:
        return int(np.unique(self.active_rows).size) if self.size else 0

    @property
    def semantic_transfer_nbytes(self) -> int:
        return int(
            self.active_rows.nbytes
            + self.action_ids.nbytes
            + self.residuals.nbytes
            + self.latent_dimension_counts.nbytes
            + self.latent_max_widths.nbytes
            + self.quantized_residuals.nbytes
            + self.comparison_active_rows.nbytes
            + self.comparison_action_ids.nbytes
            + self.comparison_residuals.nbytes
            + self.comparison_quantized_residuals.nbytes
            + self.router_saturation_counts.nbytes
            + self.router_clipping_counts.nbytes
            + self.router_hidden_abs_sums.nbytes
            + self.router_hidden_active_counts.nbytes
            + self.selection_candidate_counts.nbytes
            + self.selection_selected_counts.nbytes
            + self.selection_tie_counts.nbytes
            + self.selection_score_thresholds_q.nbytes
            + self.selection_active_rows.nbytes
            + self.selection_copy_ids.nbytes
            + self.selection_content_ids.nbytes
            + self.selection_scores_q.nbytes
            + self.work_active_rows.nbytes
            + self.work_entity_ids.nbytes
            + self.work_holder_subject_ids.nbytes
            + self.work_context_keys.nbytes
            + self.work_support_copy_counts.nbytes
            + self.work_latent_dimension_counts.nbytes
            + self.work_latent_max_widths.nbytes
            + self.work_router_saturation_counts.nbytes
            + self.work_router_clipping_counts.nbytes
            + self.work_router_hidden_active_counts.nbytes
            + self.work_selection_candidate_counts.nbytes
            + self.work_selection_selected_counts.nbytes
            + self.work_selection_tie_counts.nbytes
            + self.work_selection_score_thresholds_q.nbytes
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
        for name, value in (
            ("latent_dimension_counts", self.latent_dimension_counts),
            ("latent_max_widths", self.latent_max_widths),
            ("quantized_residuals", self.quantized_residuals),
            ("router_saturation_counts", self.router_saturation_counts),
            ("router_clipping_counts", self.router_clipping_counts),
            ("router_hidden_abs_sums", self.router_hidden_abs_sums),
            ("router_hidden_active_counts", self.router_hidden_active_counts),
            ("selection_candidate_counts", self.selection_candidate_counts),
            ("selection_selected_counts", self.selection_selected_counts),
            ("selection_tie_counts", self.selection_tie_counts),
            ("selection_score_thresholds_q", self.selection_score_thresholds_q),
        ):
            if np.asarray(value).size not in {0, count}:
                raise ValueError(f"knowledge policy {name} must be empty or align with residuals")
        selection_count = int(self.selection_copy_ids.size)
        for name, value in (
            ("selection_active_rows", self.selection_active_rows),
            ("selection_content_ids", self.selection_content_ids),
            ("selection_scores_q", self.selection_scores_q),
        ):
            if np.asarray(value).shape != (selection_count,):
                raise ValueError(f"knowledge policy {name} must align with selected copies")
        if selection_count and (
            np.any(self.selection_active_rows < 0)
            or np.any(self.selection_active_rows >= active_count)
            or np.any(self.selection_copy_ids == 0)
            or np.any(self.selection_content_ids == 0)
        ):
            raise ValueError("knowledge policy selection diagnostics are invalid")
        work_count = int(self.work_active_rows.size)
        for name, value in (
            ("work_entity_ids", self.work_entity_ids),
            ("work_holder_subject_ids", self.work_holder_subject_ids),
            ("work_context_keys", self.work_context_keys),
            ("work_support_copy_counts", self.work_support_copy_counts),
            ("work_latent_dimension_counts", self.work_latent_dimension_counts),
            ("work_latent_max_widths", self.work_latent_max_widths),
            ("work_router_saturation_counts", self.work_router_saturation_counts),
            ("work_router_clipping_counts", self.work_router_clipping_counts),
            ("work_router_hidden_active_counts", self.work_router_hidden_active_counts),
            ("work_selection_candidate_counts", self.work_selection_candidate_counts),
            ("work_selection_selected_counts", self.work_selection_selected_counts),
            ("work_selection_tie_counts", self.work_selection_tie_counts),
            ("work_selection_score_thresholds_q", self.work_selection_score_thresholds_q),
        ):
            if np.asarray(value).shape != (work_count,):
                raise ValueError(f"knowledge policy {name} must align with work rows")
        if work_count and (
            np.any(self.work_active_rows < 0)
            or np.any(self.work_active_rows >= active_count)
            or np.any(self.work_entity_ids == 0)
            or np.any(self.work_holder_subject_ids == 0)
            or np.any(self.work_context_keys == 0)
            or np.any(self.work_active_rows[1:] <= self.work_active_rows[:-1])
            or np.any(self.work_selection_selected_counts > self.work_selection_candidate_counts)
        ):
            raise ValueError("knowledge policy per-entity work diagnostics are invalid")
        comparison_count = self.comparison_size
        for name, value in (
            ("comparison_active_rows", self.comparison_active_rows),
            ("comparison_action_ids", self.comparison_action_ids),
            ("comparison_quantized_residuals", self.comparison_quantized_residuals),
        ):
            if np.asarray(value).shape != (comparison_count,):
                raise ValueError(f"knowledge policy {name} must align with comparison residuals")
        if comparison_count and (
            np.any(self.comparison_active_rows < 0)
            or np.any(self.comparison_active_rows >= active_count)
            or np.any(self.comparison_action_ids < 0)
            or np.any(self.comparison_action_ids >= action_count)
            or np.any(~np.isfinite(self.comparison_residuals))
        ):
            raise ValueError("knowledge policy comparison plan contains invalid values")
        if comparison_count:
            comparison_flat = (
                self.comparison_active_rows.astype(np.int64) * action_count
                + self.comparison_action_ids.astype(np.int64)
            )
            if np.any(comparison_flat[1:] <= comparison_flat[:-1]):
                raise ValueError("knowledge policy comparison keys must be unique and ordered")
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

    def materialize_comparison(
        self, xp: Any, active_count: int, action_count: int
    ) -> Any:
        dense = xp.zeros((active_count, action_count), dtype=xp.float32)
        if self.comparison_size:
            rows = xp.asarray(self.comparison_active_rows, dtype=xp.int32)
            actions = xp.asarray(self.comparison_action_ids, dtype=xp.int32)
            values = xp.asarray(self.comparison_residuals, dtype=xp.float32)
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


def build_latent_knowledge_policy_plan(
    observation: KnowledgeObservationPlan,
    latent_store: VariableLatentContentStore,
    *,
    tick: int,
    entity_ids: np.ndarray,
    holder_subject_ids: np.ndarray,
    context_keys: np.ndarray,
    genotype: Any,
    router_gene_start: int,
    selection_gene_start: int | None = None,
    working_memory_q: np.ndarray | None = None,
    use_strength: Any = None,
    state_features: Any = None,
    config: KnowledgeConfig,
    action_count: int,
) -> KnowledgePolicyPlan:
    """Build a sparse residual through the variable-length latent router.

    Matching and final aggregation use the CPU reference ordering.  The
    variable-width projection and inherited router execute on the backend that
    owns ``genotype``; their published contributions are quantized integers.
    """
    ids = np.asarray(entity_ids, dtype=np.uint64)
    holders = np.asarray(holder_subject_ids, dtype=np.uint64)
    contexts = np.asarray(context_keys, dtype=np.uint64)
    active_count = ids.size
    if not config.latent_policy_enabled or active_count == 0 or observation.copy_count == 0:
        return KnowledgePolicyPlan.empty(tick)
    batch = build_latent_router_batch(
        observation,
        latent_store,
        tick=tick,
        entity_ids=ids,
        holder_subject_ids=holders,
        context_keys=contexts,
        config=config,
    )
    if batch.size == 0:
        return KnowledgePolicyPlan.empty(tick)
    if config.sparse_selection_enabled:
        if selection_gene_start is None or working_memory_q is None:
            raise ValueError("sparse selection requires genes and working memory")
        selection = select_latent_router_batch(
            batch,
            genotype=genotype,
            selection_gene_start=int(selection_gene_start),
            state_features=state_features,
            working_memory_q=np.asarray(working_memory_q, dtype=np.int16),
            config=config,
        )
        batch = selection.batch
    else:
        from .latent_knowledge import SparseSelectionResult
        selection = SparseSelectionResult.passthrough(batch)
    if batch.size:
        published_q, diagnostics = route_latent_router_batch(
            batch,
            genotype=genotype,
            router_gene_start=router_gene_start,
            use_strength=use_strength,
            state_features=state_features,
            config=config,
            action_count=action_count,
        )
    else:
        published_q = np.zeros((active_count, action_count), dtype=np.int32)
        diagnostics = {
            "linear_shadow_published_q": np.zeros(
                (active_count, action_count), dtype=np.int32
            ),
            "copy_mlp_saturation_count": np.empty(0, dtype=np.uint32),
            "copy_mlp_hidden_abs_sum": np.empty(0, dtype=np.uint64),
            "copy_mlp_hidden_active_count": np.empty(0, dtype=np.uint32),
            "copy_mlp_output_clip_mask": np.empty(
                (0, action_count), dtype=bool
            ),
        }
    rows, actions = np.nonzero(published_q)
    rows = rows.astype(np.int32, copy=False)
    actions = actions.astype(np.int16, copy=False)
    shadow_q = np.asarray(
        diagnostics.get(
            "linear_shadow_published_q",
            np.zeros((active_count, action_count), dtype=np.int32),
        ),
        dtype=np.int32,
    )
    comparison_rows, comparison_actions = np.nonzero(shadow_q)
    comparison_rows = comparison_rows.astype(np.int32, copy=False)
    comparison_actions = comparison_actions.astype(np.int16, copy=False)
    q = float(config.latent_value_quantization_scale)
    reliability = batch.reliability_q.astype(np.float64) / q
    row_count = np.bincount(batch.copy_active_rows, minlength=active_count).astype(np.uint16)
    private_count = np.bincount(
        batch.copy_active_rows,
        weights=(batch.acquisition_kinds == ACQUISITION_PRIVATE_EXPERIENCE).astype(np.int64),
        minlength=active_count,
    ).astype(np.uint16)
    transfer_count = np.bincount(
        batch.copy_active_rows,
        weights=(batch.acquisition_kinds == ACQUISITION_TRANSFER).astype(np.int64),
        minlength=active_count,
    ).astype(np.uint16)
    unverified_count = np.bincount(
        batch.copy_active_rows,
        weights=batch.unverified_transfer.astype(np.int64),
        minlength=active_count,
    ).astype(np.uint16)
    reliability_mass = np.bincount(
        batch.copy_active_rows,
        weights=reliability,
        minlength=active_count,
    ).astype(np.float64)
    weighted_outcome_sum = np.zeros((active_count, OUTCOME_WIDTH), dtype=np.float64)
    for coordinate in range(OUTCOME_WIDTH):
        weighted_outcome_sum[:, coordinate] = np.bincount(
            batch.copy_active_rows,
            weights=reliability * batch.outcome_vectors[:, coordinate],
            minlength=active_count,
        )
    weighted_outcomes = np.divide(
        weighted_outcome_sum,
        np.maximum(reliability_mass[:, None], 1e-30),
        out=np.zeros_like(weighted_outcome_sum),
        where=reliability_mass[:, None] > 0.0,
    )
    dimension_sum = np.bincount(
        batch.copy_active_rows,
        weights=batch.latent_lengths.astype(np.int64),
        minlength=active_count,
    ).astype(np.uint32)
    max_width = np.zeros(active_count, dtype=np.uint16)
    np.maximum.at(max_width, batch.copy_active_rows, batch.latent_lengths)

    copy_saturation = np.asarray(
        diagnostics.get("copy_mlp_saturation_count", np.zeros(batch.size)),
        dtype=np.int64,
    )
    copy_hidden_abs = np.asarray(
        diagnostics.get("copy_mlp_hidden_abs_sum", np.zeros(batch.size)),
        dtype=np.int64,
    )
    copy_hidden_active = np.asarray(
        diagnostics.get("copy_mlp_hidden_active_count", np.zeros(batch.size)),
        dtype=np.int64,
    )
    saturation_by_row = np.bincount(
        batch.copy_active_rows,
        weights=copy_saturation,
        minlength=active_count,
    ).astype(np.uint32)
    hidden_abs_by_row = np.bincount(
        batch.copy_active_rows,
        weights=copy_hidden_abs,
        minlength=active_count,
    ).astype(np.uint64)
    hidden_active_by_row = np.bincount(
        batch.copy_active_rows,
        weights=copy_hidden_active,
        minlength=active_count,
    ).astype(np.uint32)
    clipping_by_cell = np.zeros((active_count, action_count), dtype=np.uint32)
    copy_clip = np.asarray(
        diagnostics.get(
            "copy_mlp_output_clip_mask",
            np.zeros((batch.size, action_count), dtype=bool),
        ),
        dtype=bool,
    )
    for action_index in range(action_count):
        np.add.at(
            clipping_by_cell[:, action_index],
            batch.copy_active_rows,
            copy_clip[:, action_index].astype(np.uint32),
        )

    selection_candidate_count = selection.candidate_count
    selection_selected_count = selection.selected_count
    selection_tie_count = selection.tie_count
    selection_threshold = selection.threshold_q
    # Work rows include every entity for which selection inspected at least one
    # candidate.  This is deliberately independent of emitted residual cells.
    work_rows = np.flatnonzero(selection_candidate_count > 0).astype(
        np.int32, copy=False
    )
    residual_q = published_q[rows, actions].astype(np.int32, copy=False)
    residuals = (residual_q.astype(np.float64) / q).astype(np.float32)
    comparison_q = shadow_q[comparison_rows, comparison_actions].astype(
        np.int32, copy=False
    )
    comparison_residuals = (
        comparison_q.astype(np.float64) / q
    ).astype(np.float32)
    plan = KnowledgePolicyPlan(
        tick=int(tick),
        active_rows=rows,
        entity_ids=ids[rows].copy(),
        holder_subject_ids=holders[rows].copy(),
        context_keys=contexts[rows].copy(),
        action_ids=actions,
        residuals=residuals,
        support_copy_counts=row_count[rows],
        private_support_counts=private_count[rows],
        transfer_support_counts=transfer_count[rows],
        unverified_transfer_support_counts=unverified_count[rows],
        reliability_mass=reliability_mass[rows].astype(np.float32),
        weighted_outcome_vectors=weighted_outcomes[rows].astype(np.float32),
        latent_dimension_counts=dimension_sum[rows],
        latent_max_widths=max_width[rows],
        quantized_residuals=residual_q,
        comparison_active_rows=comparison_rows,
        comparison_action_ids=comparison_actions,
        comparison_residuals=comparison_residuals,
        comparison_quantized_residuals=comparison_q,
        router_saturation_counts=saturation_by_row[rows],
        router_clipping_counts=clipping_by_cell[rows, actions],
        router_hidden_abs_sums=hidden_abs_by_row[rows],
        router_hidden_active_counts=hidden_active_by_row[rows],
        selection_candidate_counts=selection_candidate_count[rows],
        selection_selected_counts=selection_selected_count[rows],
        selection_tie_counts=selection_tie_count[rows],
        selection_score_thresholds_q=selection_threshold[rows],
        selection_active_rows=batch.copy_active_rows.copy(),
        selection_copy_ids=batch.copy_ids.copy(),
        selection_content_ids=batch.content_ids.copy(),
        selection_scores_q=selection.selected_scores_q.copy(),
        work_active_rows=work_rows.copy(),
        work_entity_ids=ids[work_rows].copy(),
        work_holder_subject_ids=holders[work_rows].copy(),
        work_context_keys=contexts[work_rows].copy(),
        work_support_copy_counts=row_count[work_rows],
        work_latent_dimension_counts=dimension_sum[work_rows],
        work_latent_max_widths=max_width[work_rows],
        work_router_saturation_counts=saturation_by_row[work_rows],
        work_router_clipping_counts=clipping_by_cell[work_rows].sum(
            axis=1, dtype=np.uint64
        ).astype(np.uint32),
        work_router_hidden_active_counts=hidden_active_by_row[work_rows],
        work_selection_candidate_counts=selection_candidate_count[work_rows],
        work_selection_selected_counts=selection_selected_count[work_rows],
        work_selection_tie_counts=selection_tie_count[work_rows],
        work_selection_score_thresholds_q=selection_threshold[work_rows],
        router_schema=config.latent_router_schema,
        selection_schema=(config.sparse_selection_schema if config.sparse_selection_enabled else None),
    )
    plan.validate(active_count, action_count)
    return plan


__all__ = [
    "KnowledgePolicyPlan",
    "build_knowledge_policy_plan",
    "build_latent_knowledge_policy_plan",
]
