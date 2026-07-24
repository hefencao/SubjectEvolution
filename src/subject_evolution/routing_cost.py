"""Deterministic physical cost for latent knowledge routing.

The router may be evaluated to construct an immutable proposal, but only
entities that can pay the preflight cost publish that proposal to the policy
boundary.  The budget rule is deliberately all-or-none per entity: it avoids
backend-dependent partial scaling and keeps discrete action parity auditable.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
import numpy as np

from .config import KnowledgeConfig
from .knowledge_policy import KnowledgePolicyPlan
from .latent_knowledge import (
    LATENT_MLP_ROUTER_SCHEMA,
    LATENT_ROUTER_METADATA_WIDTH,
    LATENT_ROUTER_SCHEMA,
    LATENT_STATE_WIDTH,
)


@dataclass(frozen=True)
class RoutingCostBudgetResult:
    plan: KnowledgePolicyPlan
    active_rows: np.ndarray
    entity_ids: np.ndarray
    holder_subject_ids: np.ndarray
    requested_energy: np.ndarray
    committed_energy: np.ndarray
    accepted: np.ndarray
    latent_dimensions: np.ndarray
    mac_count: np.ndarray
    active_hidden_units: np.ndarray
    saturation_count: np.ndarray
    clipped_output_count: np.ndarray
    emitted_action_count: np.ndarray
    selection_candidate_count: np.ndarray
    selection_selected_count: np.ndarray
    selection_requested_top_k: np.ndarray
    selection_energy: np.ndarray
    accepted_action_count: int
    rejected_action_count: int

    @classmethod
    def empty(cls, plan: KnowledgePolicyPlan) -> "RoutingCostBudgetResult":
        return cls(
            plan=plan,
            active_rows=np.empty(0, dtype=np.int32),
            entity_ids=np.empty(0, dtype=np.uint64),
            holder_subject_ids=np.empty(0, dtype=np.uint64),
            requested_energy=np.empty(0, dtype=np.float64),
            committed_energy=np.empty(0, dtype=np.float64),
            accepted=np.empty(0, dtype=bool),
            latent_dimensions=np.empty(0, dtype=np.uint64),
            mac_count=np.empty(0, dtype=np.uint64),
            active_hidden_units=np.empty(0, dtype=np.uint64),
            saturation_count=np.empty(0, dtype=np.uint64),
            clipped_output_count=np.empty(0, dtype=np.uint64),
            emitted_action_count=np.empty(0, dtype=np.uint32),
            selection_candidate_count=np.empty(0, dtype=np.uint32),
            selection_selected_count=np.empty(0, dtype=np.uint32),
            selection_requested_top_k=np.empty(0, dtype=np.uint32),
            selection_energy=np.empty(0, dtype=np.float64),
            accepted_action_count=0,
            rejected_action_count=0,
        )

    @property
    def requested_total(self) -> float:
        return float(self.requested_energy.sum(dtype=np.float64))

    @property
    def committed_total(self) -> float:
        return float(self.committed_energy.sum(dtype=np.float64))

    @property
    def rejected_total(self) -> float:
        return float(self.requested_total - self.committed_total)


def _filter_plan(plan: KnowledgePolicyPlan, accepted_rows: np.ndarray) -> KnowledgePolicyPlan:
    accepted_rows = np.asarray(accepted_rows, dtype=np.int32)
    primary_keep = np.isin(plan.active_rows, accepted_rows, assume_unique=False)
    comparison_keep = np.isin(
        plan.comparison_active_rows, accepted_rows, assume_unique=False
    )
    work_keep = np.isin(plan.work_active_rows, accepted_rows, assume_unique=False)

    def optional(value: np.ndarray, mask: np.ndarray) -> np.ndarray:
        array = np.asarray(value)
        return array[mask].copy() if array.size else array.copy()

    return replace(
        plan,
        active_rows=plan.active_rows[primary_keep].copy(),
        entity_ids=plan.entity_ids[primary_keep].copy(),
        holder_subject_ids=plan.holder_subject_ids[primary_keep].copy(),
        context_keys=plan.context_keys[primary_keep].copy(),
        action_ids=plan.action_ids[primary_keep].copy(),
        residuals=plan.residuals[primary_keep].copy(),
        support_copy_counts=plan.support_copy_counts[primary_keep].copy(),
        private_support_counts=plan.private_support_counts[primary_keep].copy(),
        transfer_support_counts=plan.transfer_support_counts[primary_keep].copy(),
        unverified_transfer_support_counts=(
            plan.unverified_transfer_support_counts[primary_keep].copy()
        ),
        reliability_mass=plan.reliability_mass[primary_keep].copy(),
        weighted_outcome_vectors=plan.weighted_outcome_vectors[primary_keep].copy(),
        latent_dimension_counts=optional(plan.latent_dimension_counts, primary_keep),
        latent_max_widths=optional(plan.latent_max_widths, primary_keep),
        quantized_residuals=optional(plan.quantized_residuals, primary_keep),
        comparison_active_rows=plan.comparison_active_rows[comparison_keep].copy(),
        comparison_action_ids=plan.comparison_action_ids[comparison_keep].copy(),
        comparison_residuals=plan.comparison_residuals[comparison_keep].copy(),
        comparison_quantized_residuals=(
            plan.comparison_quantized_residuals[comparison_keep].copy()
        ),
        router_saturation_counts=optional(plan.router_saturation_counts, primary_keep),
        router_clipping_counts=optional(plan.router_clipping_counts, primary_keep),
        router_hidden_abs_sums=optional(plan.router_hidden_abs_sums, primary_keep),
        router_hidden_active_counts=optional(
            plan.router_hidden_active_counts, primary_keep
        ),
        selection_candidate_counts=optional(plan.selection_candidate_counts, primary_keep),
        selection_selected_counts=optional(plan.selection_selected_counts, primary_keep),
        selection_requested_top_k=optional(plan.selection_requested_top_k, primary_keep),
        selection_tie_counts=optional(plan.selection_tie_counts, primary_keep),
        selection_score_thresholds_q=optional(
            plan.selection_score_thresholds_q, primary_keep
        ),
        selection_active_rows=plan.selection_active_rows[
            np.isin(plan.selection_active_rows, accepted_rows, assume_unique=False)
        ].copy(),
        selection_copy_ids=plan.selection_copy_ids[
            np.isin(plan.selection_active_rows, accepted_rows, assume_unique=False)
        ].copy(),
        selection_content_ids=plan.selection_content_ids[
            np.isin(plan.selection_active_rows, accepted_rows, assume_unique=False)
        ].copy(),
        selection_scores_q=plan.selection_scores_q[
            np.isin(plan.selection_active_rows, accepted_rows, assume_unique=False)
        ].copy(),
        work_active_rows=plan.work_active_rows[work_keep].copy(),
        work_entity_ids=plan.work_entity_ids[work_keep].copy(),
        work_holder_subject_ids=plan.work_holder_subject_ids[work_keep].copy(),
        work_context_keys=plan.work_context_keys[work_keep].copy(),
        work_support_copy_counts=plan.work_support_copy_counts[work_keep].copy(),
        work_latent_dimension_counts=(
            plan.work_latent_dimension_counts[work_keep].copy()
        ),
        work_latent_max_widths=plan.work_latent_max_widths[work_keep].copy(),
        work_router_saturation_counts=(
            plan.work_router_saturation_counts[work_keep].copy()
        ),
        work_router_clipping_counts=(
            plan.work_router_clipping_counts[work_keep].copy()
        ),
        work_router_hidden_active_counts=(
            plan.work_router_hidden_active_counts[work_keep].copy()
        ),
        work_selection_candidate_counts=(
            plan.work_selection_candidate_counts[work_keep].copy()
        ),
        work_selection_selected_counts=(
            plan.work_selection_selected_counts[work_keep].copy()
        ),
        work_selection_requested_top_k=optional(
            plan.work_selection_requested_top_k, work_keep
        ),
        work_selection_tie_counts=(
            plan.work_selection_tie_counts[work_keep].copy()
        ),
        work_selection_score_thresholds_q=(
            plan.work_selection_score_thresholds_q[work_keep].copy()
        ),
    )


def apply_routing_cost_budget(
    plan: KnowledgePolicyPlan,
    *,
    active_energy: np.ndarray,
    config: KnowledgeConfig,
    action_count: int,
) -> RoutingCostBudgetResult:
    """Return the affordable plan and per-entity deterministic cost diagnostics.

    ``active_energy`` is the pre-routing observation energy for active rows.  It
    is not mutated here; the caller commits ``committed_energy`` to the world
    after the plan has been accepted or rejected.
    """
    if not config.routing_cost_enabled or not config.latent_policy_enabled:
        return RoutingCostBudgetResult.empty(plan)

    energy = np.asarray(active_energy, dtype=np.float64)
    unique_rows = (
        np.asarray(plan.work_active_rows, dtype=np.int32)
        if np.asarray(plan.work_active_rows).size
        else np.unique(plan.active_rows).astype(np.int32, copy=False)
    )
    if unique_rows.size == 0:
        return RoutingCostBudgetResult.empty(plan)
    entity_ids = np.empty(unique_rows.size, dtype=np.uint64)
    holder_ids = np.empty(unique_rows.size, dtype=np.uint64)
    requested = np.zeros(unique_rows.size, dtype=np.float64)
    dimensions = np.zeros(unique_rows.size, dtype=np.uint64)
    macs = np.zeros(unique_rows.size, dtype=np.uint64)
    active_hidden = np.zeros(unique_rows.size, dtype=np.uint64)
    saturation = np.zeros(unique_rows.size, dtype=np.uint64)
    clipping = np.zeros(unique_rows.size, dtype=np.uint64)
    emitted = np.zeros(unique_rows.size, dtype=np.uint32)
    selection_candidates = np.zeros(unique_rows.size, dtype=np.uint32)
    selection_selected = np.zeros(unique_rows.size, dtype=np.uint32)
    selection_requested_top_k = np.zeros(unique_rows.size, dtype=np.uint32)
    selection_energy = np.zeros(unique_rows.size, dtype=np.float64)

    projection_width = int(config.latent_router_hidden_width)
    mlp_width = int(config.latent_router_mlp_hidden_width)
    work_index = {
        int(row): index for index, row in enumerate(
            np.asarray(plan.work_active_rows, dtype=np.int32).tolist()
        )
    }
    for output_row, active_row in enumerate(unique_rows.tolist()):
        mask = plan.active_rows == active_row
        emitted_count = int(np.count_nonzero(mask))
        if active_row in work_index:
            wi = work_index[active_row]
            entity_ids[output_row] = plan.work_entity_ids[wi]
            holder_ids[output_row] = plan.work_holder_subject_ids[wi]
            copy_count = int(plan.work_support_copy_counts[wi])
            dimension_count = int(plan.work_latent_dimension_counts[wi])
            hidden_count = int(plan.work_router_hidden_active_counts[wi])
            saturation_count = int(plan.work_router_saturation_counts[wi])
            clipping_count = int(plan.work_router_clipping_counts[wi])
            candidate_count = int(plan.work_selection_candidate_counts[wi])
            selected_count = int(plan.work_selection_selected_counts[wi])
            requested_top_k = int(
                plan.work_selection_requested_top_k[wi]
                if plan.work_selection_requested_top_k.size
                else selected_count
            )
        else:
            first = int(np.flatnonzero(mask)[0])
            entity_ids[output_row] = plan.entity_ids[first]
            holder_ids[output_row] = plan.holder_subject_ids[first]
            copy_count = int(np.max(plan.support_copy_counts[mask], initial=0))
            dimension_count = int(
                np.max(plan.latent_dimension_counts[mask], initial=0)
                if plan.latent_dimension_counts.size else 0
            )
            hidden_count = int(
                np.max(plan.router_hidden_active_counts[mask], initial=0)
                if plan.router_hidden_active_counts.size else 0
            )
            saturation_count = int(
                np.max(plan.router_saturation_counts[mask], initial=0)
                if plan.router_saturation_counts.size else 0
            )
            clipping_count = int(
                np.sum(plan.router_clipping_counts[mask], dtype=np.uint64)
                if plan.router_clipping_counts.size else 0
            )
            candidate_count = int(
                np.max(plan.selection_candidate_counts[mask], initial=copy_count)
                if plan.selection_candidate_counts.size else copy_count
            )
            selected_count = int(
                np.max(plan.selection_selected_counts[mask], initial=copy_count)
                if plan.selection_selected_counts.size else copy_count
            )
            requested_top_k = int(
                np.max(plan.selection_requested_top_k[mask], initial=selected_count)
                if plan.selection_requested_top_k.size else selected_count
            )

        # Shared latent projection plus five-dimensional local-outcome injection.
        mac_count = dimension_count * projection_width
        mac_count += copy_count * 5 * projection_width
        if plan.router_schema == LATENT_ROUTER_SCHEMA:
            mac_count += copy_count * action_count * (
                projection_width + LATENT_STATE_WIDTH
            )
        elif plan.router_schema == LATENT_MLP_ROUTER_SCHEMA:
            input_width = (
                projection_width + LATENT_STATE_WIDTH + LATENT_ROUTER_METADATA_WIDTH
            )
            mac_count += copy_count * (
                input_width * mlp_width + mlp_width * action_count
            )
        else:
            raise ValueError("routing compute cost requires a known latent router schema")
        # Reliability-weighted copy aggregation performs one multiply per
        # copy/action cell.  Integer divisions and bias additions are included
        # in the base invocation term rather than pretending to be MACs.
        mac_count += copy_count * action_count

        dimensions[output_row] = np.uint64(dimension_count)
        macs[output_row] = np.uint64(mac_count)
        active_hidden[output_row] = np.uint64(hidden_count)
        saturation[output_row] = np.uint64(saturation_count)
        clipping[output_row] = np.uint64(clipping_count)
        emitted[output_row] = np.uint32(emitted_count)
        selection_candidates[output_row] = np.uint32(candidate_count)
        selection_selected[output_row] = np.uint32(selected_count)
        selection_requested_top_k[output_row] = np.uint32(requested_top_k)
        selection_energy[output_row] = (
            float(config.sparse_selection_base_energy_cost)
            + candidate_count * float(config.sparse_selection_energy_per_candidate)
            + selected_count * float(config.sparse_selection_energy_per_selected_copy)
            if plan.selection_schema is not None else 0.0
        )
        requested[output_row] = (
            float(config.routing_base_energy_cost)
            + dimension_count * float(config.routing_energy_per_latent_dimension)
            + mac_count * float(config.routing_energy_per_mac)
            + hidden_count * float(config.routing_energy_per_active_hidden_unit)
            + emitted_count * float(config.routing_energy_per_emitted_action)
            + saturation_count * float(config.routing_energy_per_saturation)
            + clipping_count * float(config.routing_energy_per_clipped_output)
            + selection_energy[output_row]
        )

    available = energy[unique_rows]
    accepted = available + 1e-12 >= requested
    committed = np.where(accepted, requested, 0.0)
    accepted_rows = unique_rows[accepted]
    filtered = _filter_plan(plan, accepted_rows)
    filtered.validate(active_count=energy.size, action_count=action_count)
    accepted_action_count = int(filtered.size)
    return RoutingCostBudgetResult(
        plan=filtered,
        active_rows=unique_rows,
        entity_ids=entity_ids,
        holder_subject_ids=holder_ids,
        requested_energy=requested,
        committed_energy=committed,
        accepted=accepted,
        latent_dimensions=dimensions,
        mac_count=macs,
        active_hidden_units=active_hidden,
        saturation_count=saturation,
        clipped_output_count=clipping,
        emitted_action_count=emitted,
        selection_candidate_count=selection_candidates,
        selection_selected_count=selection_selected,
        selection_requested_top_k=selection_requested_top_k,
        selection_energy=selection_energy,
        accepted_action_count=accepted_action_count,
        rejected_action_count=int(plan.size - accepted_action_count),
    )


__all__ = ["RoutingCostBudgetResult", "apply_routing_cost_budget"]
