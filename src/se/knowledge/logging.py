"""Knowledge lifecycle orchestration, costs, logs, and diagnostics."""

from __future__ import annotations

import copy
import csv
import json
from pathlib import Path
from typing import Any

import numpy as np

from ..backend import backend_from_array
from ..cfg import KnowledgeConfig, SimulationConfig
from .subjects import KnowledgeCandidateTracker
from ..random_api import RandomContext, Stream, bernoulli, uniform01
from .storage import KnowledgeArena, KnowledgeCatalog
from .types import (
    ACQUISITION_PRIVATE_EXPERIENCE, ACQUISITION_SEED, ACQUISITION_TRANSFER,
    KnowledgeObservationPlan, KnowledgeOutcomePlan, KnowledgeStepStats,
    KnowledgeTransferCommitAudit, KnowledgeTransferPlan,
    OUTCOME_ENERGY, OUTCOME_INFORMATION, OUTCOME_INTEGRITY, OUTCOME_MATERIAL,
    OUTCOME_REPRODUCTION_OPPORTUNITY, OUTCOME_STATUS_FAILED,
    OUTCOME_STATUS_PARTIAL, OUTCOME_STATUS_SUCCESS, OUTCOME_WIDTH, _readonly,
)



class KnowledgeLoggingMixin:
    """Event and high-volume audit log publication."""

    def _write_event(self, event: dict[str, object]) -> None:
        if self._event_file is None:
            return
        self._event_file.write(json.dumps(event, ensure_ascii=False) + "\n")


    def flush(self) -> None:
        if self._event_file is not None and not self._event_file.closed:
            self._event_file.flush()
        if self._transfer_file is not None and not self._transfer_file.closed:
            self._transfer_file.flush()
        if self._outcome_file is not None and not self._outcome_file.closed:
            self._outcome_file.flush()
        if self._policy_file is not None and not self._policy_file.closed:
            self._policy_file.flush()
        if self._routing_cost_file is not None and not self._routing_cost_file.closed:
            self._routing_cost_file.flush()
        if self._working_memory_file is not None and not self._working_memory_file.closed:
            self._working_memory_file.flush()
        if self._selection_file is not None and not self._selection_file.closed:
            self._selection_file.flush()
        self.candidates.flush()


    def close(self) -> None:
        if self._event_file is not None and not self._event_file.closed:
            self._event_file.close()
        if self._transfer_file is not None and not self._transfer_file.closed:
            self._transfer_file.close()
        if self._outcome_file is not None and not self._outcome_file.closed:
            self._outcome_file.close()
        if self._policy_file is not None and not self._policy_file.closed:
            self._policy_file.close()
        if self._routing_cost_file is not None and not self._routing_cost_file.closed:
            self._routing_cost_file.close()
        if self._working_memory_file is not None and not self._working_memory_file.closed:
            self._working_memory_file.close()
        if self._selection_file is not None and not self._selection_file.closed:
            self._selection_file.close()
        self.candidates.close(self.catalog)


    def record_routing_cost(
        self,
        result: Any,
        *,
        cost_induced_action_changes: int = 0,
    ) -> KnowledgeStepStats:
        stats = KnowledgeStepStats()
        if result is None or np.asarray(result.active_rows).size == 0:
            return stats
        stats.routing_requested_energy = float(result.requested_total)
        stats.routing_committed_energy = float(result.committed_total)
        stats.routing_rejected_energy = float(result.rejected_total)
        stats.routing_requested_entities = int(result.active_rows.size)
        stats.routing_committed_entities = int(np.count_nonzero(result.accepted))
        stats.routing_rejected_entities = int(result.active_rows.size - stats.routing_committed_entities)
        stats.routing_accepted_actions = int(result.accepted_action_count)
        stats.routing_rejected_actions = int(result.rejected_action_count)
        stats.routing_latent_dimensions = int(np.asarray(result.latent_dimensions, dtype=np.uint64).sum())
        stats.routing_mac_count = int(np.asarray(result.mac_count, dtype=np.uint64).sum())
        stats.routing_active_hidden_units = int(np.asarray(result.active_hidden_units, dtype=np.uint64).sum())
        stats.routing_saturation_count = int(np.asarray(result.saturation_count, dtype=np.uint64).sum())
        stats.routing_clipped_output_count = int(np.asarray(result.clipped_output_count, dtype=np.uint64).sum())
        stats.routing_cost_induced_action_changes = int(cost_induced_action_changes)
        if getattr(result.plan, "selection_schema", None) is not None:
            stats.selection_candidate_copies = int(
                np.asarray(result.selection_candidate_count, dtype=np.uint64).sum()
            )
            stats.selection_selected_copies = int(
                np.asarray(result.selection_selected_count, dtype=np.uint64).sum()
            )
            stats.selection_requested_top_k_sum = int(
                np.asarray(result.selection_requested_top_k, dtype=np.uint64).sum()
            )
            stats.selection_zero_capacity_entities = int(
                np.count_nonzero(np.asarray(result.selection_requested_top_k) == 0)
            )
            stats.selection_committed_energy = float(
                np.asarray(result.selection_energy, dtype=np.float64)[result.accepted].sum()
            )
        if self.kcfg.candidate_tracking_enabled:
            self.candidates.record_routing_cost(
                observation=self.observation,
                result=result,
            )
        if self._routing_cost_writer is not None:
            for row in range(result.active_rows.size):
                self._routing_cost_writer.writerow({
                    "tick": int(result.plan.tick),
                    "entity_id": int(result.entity_ids[row]),
                    "holder_subject_id": int(result.holder_subject_ids[row]),
                    "accepted": int(bool(result.accepted[row])),
                    "requested_energy": float(result.requested_energy[row]),
                    "committed_energy": float(result.committed_energy[row]),
                    "latent_dimensions": int(result.latent_dimensions[row]),
                    "mac_count": int(result.mac_count[row]),
                    "active_hidden_units": int(result.active_hidden_units[row]),
                    "saturation_count": int(result.saturation_count[row]),
                    "clipped_output_count": int(result.clipped_output_count[row]),
                    "emitted_action_count": int(result.emitted_action_count[row]),
                    "selection_candidate_count": int(result.selection_candidate_count[row]),
                    "selection_selected_count": int(result.selection_selected_count[row]),
                    "selection_requested_top_k": int(result.selection_requested_top_k[row]),
                    "selection_energy": float(result.selection_energy[row]),
                })
        return stats


    def record_working_memory(
        self,
        result: Any,
        *,
        holder_subject_ids: np.ndarray | None = None,
        action_changes: int = 0,
    ) -> KnowledgeStepStats:
        stats = KnowledgeStepStats()
        if result is None or np.asarray(result.active_rows).size == 0:
            return stats
        stats.working_memory_requested_energy = float(result.requested_total)
        stats.working_memory_committed_energy = float(result.committed_total)
        stats.working_memory_rejected_energy = float(result.rejected_total)
        stats.working_memory_requested_entities = int(result.active_rows.size)
        stats.working_memory_committed_entities = int(np.count_nonzero(result.accepted))
        stats.working_memory_rejected_entities = int(
            result.active_rows.size - stats.working_memory_committed_entities
        )
        stats.working_memory_saturation_units = int(
            np.asarray(result.saturation_count, dtype=np.uint64).sum()
        )
        stats.working_memory_active_dimensions = int(
            np.asarray(result.active_dimension_count, dtype=np.uint64).sum()
        )
        stats.working_memory_induced_action_changes = int(action_changes)
        if self.kcfg.candidate_tracking_enabled and holder_subject_ids is not None:
            self.candidates.record_working_memory_cost(
                observation=self.observation,
                result=result,
                holder_subject_ids=np.asarray(holder_subject_ids, dtype=np.uint64),
            )
        if self._working_memory_writer is not None:
            for row in range(result.active_rows.size):
                self._working_memory_writer.writerow({
                    "tick": int(result.tick),
                    "entity_id": int(result.entity_ids[row]),
                    "accepted": int(bool(result.accepted[row])),
                    "requested_energy": float(result.requested_energy[row]),
                    "committed_energy": float(result.committed_energy[row]),
                    "saturation_count": int(result.saturation_count[row]),
                    "active_dimension_count": int(result.active_dimension_count[row]),
                    "previous_q": " ".join(map(str, result.previous_q[row].tolist())),
                    "proposed_q": " ".join(map(str, result.proposed_q[row].tolist())),
                    "committed_q": " ".join(map(str, result.committed_q[row].tolist())),
                    "observation_delta_q": " ".join(
                        map(str, result.observation_delta_q[row].tolist())
                    ),
                    "prediction_error_q": " ".join(
                        map(str, result.prediction_error_q[row].tolist())
                    ),
                })
        self._write_event({
            "tick": int(result.tick),
            "type": "working-memory-summary",
            "schema": self.kcfg.working_memory_schema,
            "requested_energy": stats.working_memory_requested_energy,
            "committed_energy": stats.working_memory_committed_energy,
            "rejected_entities": stats.working_memory_rejected_entities,
            "saturation_units": stats.working_memory_saturation_units,
            "action_changes": stats.working_memory_induced_action_changes,
        })
        return stats


    def record_policy_plan(
        self,
        plan: Any,
        *,
        changed_actions: int = 0,
        changed_active_rows: np.ndarray | None = None,
        comparison_changed_actions: int = 0,
    ) -> KnowledgeStepStats:
        """Record one K3 sparse residual plan without mutating knowledge state."""
        stats = KnowledgeStepStats()
        if not self.kcfg.policy_influence_enabled:
            return stats
        stats.policy_influenced_entities = int(plan.influenced_entity_count)
        stats.policy_influenced_actions = int(plan.size)
        stats.policy_support_copies = int(plan.support_copy_counts.sum(dtype=np.int64))
        stats.policy_private_support_copies = int(plan.private_support_counts.sum(dtype=np.int64))
        stats.policy_transfer_support_copies = int(plan.transfer_support_counts.sum(dtype=np.int64))
        stats.policy_unverified_transfer_support_copies = int(
            plan.unverified_transfer_support_counts.sum(dtype=np.int64)
        )
        stats.policy_changed_actions = int(changed_actions)
        stats.policy_linear_shadow_changed_actions = int(comparison_changed_actions)
        stats.policy_residual_abs_sum = float(
            np.abs(plan.residuals).sum(dtype=np.float64)
        )
        if getattr(plan, "latent_dimension_counts", np.empty(0)).size:
            stats.policy_latent_dimensions = int(
                np.asarray(plan.latent_dimension_counts, dtype=np.uint64).sum()
            )
            stats.policy_latent_max_width = int(
                np.asarray(plan.latent_max_widths, dtype=np.uint16).max(initial=0)
            )
        if getattr(plan, "quantized_residuals", np.empty(0)).size:
            stats.policy_quantized_residual_abs_sum = int(
                np.abs(np.asarray(plan.quantized_residuals, dtype=np.int64)).sum()
            )
        if getattr(plan, "router_saturation_counts", np.empty(0)).size:
            stats.policy_router_saturation_units = int(
                np.asarray(plan.router_saturation_counts, dtype=np.uint64).sum()
            )
            stats.policy_router_clipped_outputs = int(
                np.asarray(plan.router_clipping_counts, dtype=np.uint64).sum()
            )
            stats.policy_router_hidden_abs_sum = int(
                np.asarray(plan.router_hidden_abs_sums, dtype=np.uint64).sum()
            )
            stats.policy_router_hidden_active_units = int(
                np.asarray(plan.router_hidden_active_counts, dtype=np.uint64).sum()
            )
        if (
            self.kcfg.sparse_selection_enabled
            and getattr(plan, "selection_candidate_counts", np.empty(0)).size
        ):
            # Selection diagnostics are repeated for each nonzero action cell.
            # Count each active entity once rather than inflating totals by the
            # number of emitted residual actions.
            _, first_rows = np.unique(
                np.asarray(plan.active_rows, dtype=np.int32), return_index=True
            )
            stats.selection_candidate_copies = int(
                np.asarray(plan.selection_candidate_counts, dtype=np.uint64)[first_rows].sum()
            )
            stats.selection_selected_copies = int(
                np.asarray(plan.selection_selected_counts, dtype=np.uint64)[first_rows].sum()
            )
            if not self.kcfg.routing_cost_enabled:
                stats.selection_requested_top_k_sum = int(
                    np.asarray(plan.selection_requested_top_k, dtype=np.uint64)[first_rows].sum()
                )
                stats.selection_zero_capacity_entities = int(
                    np.count_nonzero(
                        np.asarray(plan.selection_requested_top_k, dtype=np.uint16)[first_rows] == 0
                    )
                )
            stats.selection_tie_count = int(
                np.asarray(plan.selection_tie_counts, dtype=np.uint64)[first_rows].sum()
            )
        if self._selection_writer is not None and getattr(
            plan, "selection_copy_ids", np.empty(0)
        ).size:
            work_map = {
                int(active_row): (int(entity_id), int(holder_id))
                for active_row, entity_id, holder_id in zip(
                    np.asarray(plan.work_active_rows, dtype=np.int32).tolist(),
                    np.asarray(plan.work_entity_ids, dtype=np.uint64).tolist(),
                    np.asarray(plan.work_holder_subject_ids, dtype=np.uint64).tolist(),
                    strict=True,
                )
            }
            requested_top_k_map = {
                int(active_row): int(requested_top_k)
                for active_row, requested_top_k in zip(
                    np.asarray(plan.work_active_rows, dtype=np.int32).tolist(),
                    np.asarray(plan.work_selection_requested_top_k, dtype=np.uint16).tolist(),
                    strict=True,
                )
            }
            selection_rows = np.asarray(plan.selection_active_rows, dtype=np.int32)
            copy_ids = np.asarray(plan.selection_copy_ids, dtype=np.uint64)
            content_ids = np.asarray(plan.selection_content_ids, dtype=np.uint64)
            scores = np.asarray(plan.selection_scores_q, dtype=np.int64)
            order = np.lexsort((content_ids, copy_ids, -scores, selection_rows))
            previous_row = -1
            rank = 0
            for index in order.tolist():
                active_row = int(selection_rows[index])
                if active_row != previous_row:
                    previous_row = active_row
                    rank = 1
                else:
                    rank += 1
                entity_id, holder_id = work_map.get(active_row, (0, 0))
                self._selection_writer.writerow({
                    "tick": int(plan.tick),
                    "active_row": active_row,
                    "entity_id": entity_id,
                    "holder_subject_id": holder_id,
                    "copy_id": int(copy_ids[index]),
                    "content_id": int(content_ids[index]),
                    "score_q": int(scores[index]),
                    "rank_within_entity": rank,
                    "requested_top_k": requested_top_k_map.get(active_row, 0),
                })
        if self.kcfg.candidate_tracking_enabled:
            self.candidates.record_policy_plan(
                observation=self.observation,
                plan=plan,
                changed_active_rows=(
                    np.empty(0, dtype=np.int32)
                    if changed_active_rows is None
                    else np.asarray(changed_active_rows, dtype=np.int32)
                ),
                acquisition_transfer=ACQUISITION_TRANSFER,
            )
        if self._policy_writer is not None:
            shadow_lookup = {
                (int(active_row), int(action_id)): (float(residual), int(residual_q))
                for active_row, action_id, residual, residual_q in zip(
                    getattr(plan, "comparison_active_rows", np.empty(0, dtype=np.int32)),
                    getattr(plan, "comparison_action_ids", np.empty(0, dtype=np.int16)),
                    getattr(plan, "comparison_residuals", np.empty(0, dtype=np.float32)),
                    getattr(plan, "comparison_quantized_residuals", np.empty(0, dtype=np.int32)),
                )
            }
            for row in range(plan.size):
                outcome = plan.weighted_outcome_vectors[row]
                self._policy_writer.writerow(
                    {
                        "tick": int(plan.tick),
                        "entity_id": int(plan.entity_ids[row]),
                        "holder_subject_id": int(plan.holder_subject_ids[row]),
                        "context_key": int(plan.context_keys[row]),
                        "action_id": int(plan.action_ids[row]),
                        "logit_residual": float(plan.residuals[row]),
                        "support_copy_count": int(plan.support_copy_counts[row]),
                        "private_support_count": int(plan.private_support_counts[row]),
                        "transfer_support_count": int(plan.transfer_support_counts[row]),
                        "unverified_transfer_support_count": int(
                            plan.unverified_transfer_support_counts[row]
                        ),
                        "reliability_mass": float(plan.reliability_mass[row]),
                        "energy_outcome": float(outcome[0]),
                        "integrity_outcome": float(outcome[1]),
                        "material_outcome": float(outcome[2]),
                        "information_outcome": float(outcome[3]),
                        "reproduction_opportunity_outcome": float(outcome[4]),
                        "router_schema": getattr(plan, "router_schema", None),
                        "latent_dimension_count": (
                            int(plan.latent_dimension_counts[row])
                            if getattr(plan, "latent_dimension_counts", np.empty(0)).size
                            else 0
                        ),
                        "latent_max_width": (
                            int(plan.latent_max_widths[row])
                            if getattr(plan, "latent_max_widths", np.empty(0)).size
                            else 0
                        ),
                        "quantized_residual": (
                            int(plan.quantized_residuals[row])
                            if getattr(plan, "quantized_residuals", np.empty(0)).size
                            else 0
                        ),
                        "linear_shadow_logit_residual": shadow_lookup.get(
                            (int(plan.active_rows[row]), int(plan.action_ids[row])),
                            (0.0, 0),
                        )[0],
                        "linear_shadow_quantized_residual": shadow_lookup.get(
                            (int(plan.active_rows[row]), int(plan.action_ids[row])),
                            (0.0, 0),
                        )[1],
                        "router_saturation_count": (
                            int(plan.router_saturation_counts[row])
                            if getattr(plan, "router_saturation_counts", np.empty(0)).size
                            else 0
                        ),
                        "router_clipping_count": (
                            int(plan.router_clipping_counts[row])
                            if getattr(plan, "router_clipping_counts", np.empty(0)).size
                            else 0
                        ),
                        "router_hidden_abs_sum": (
                            int(plan.router_hidden_abs_sums[row])
                            if getattr(plan, "router_hidden_abs_sums", np.empty(0)).size
                            else 0
                        ),
                        "router_hidden_active_count": (
                            int(plan.router_hidden_active_counts[row])
                            if getattr(plan, "router_hidden_active_counts", np.empty(0)).size
                            else 0
                        ),
                        "selection_schema": getattr(plan, "selection_schema", None),
                        "selection_candidate_count": (
                            int(plan.selection_candidate_counts[row])
                            if getattr(plan, "selection_candidate_counts", np.empty(0)).size else 0
                        ),
                        "selection_selected_count": (
                            int(plan.selection_selected_counts[row])
                            if getattr(plan, "selection_selected_counts", np.empty(0)).size else 0
                        ),
                        "selection_requested_top_k": (
                            int(plan.selection_requested_top_k[row])
                            if getattr(plan, "selection_requested_top_k", np.empty(0)).size else 0
                        ),
                        "selection_tie_count": (
                            int(plan.selection_tie_counts[row])
                            if getattr(plan, "selection_tie_counts", np.empty(0)).size else 0
                        ),
                        "selection_score_threshold_q": (
                            int(plan.selection_score_thresholds_q[row])
                            if getattr(plan, "selection_score_thresholds_q", np.empty(0)).size else 0
                        ),
                    }
                )
        return stats

