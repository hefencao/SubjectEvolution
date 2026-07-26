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



class KnowledgeDiagnosticsMixin:
    """Aggregated metrics, validation, and checkpoint publication."""

    def accumulate(self, step: KnowledgeStepStats) -> None:
        for name in KnowledgeStepStats.__dataclass_fields__:
            if name == "policy_latent_max_width":
                self.totals.policy_latent_max_width = max(
                    self.totals.policy_latent_max_width,
                    step.policy_latent_max_width,
                )
                continue
            setattr(self.totals, name, getattr(self.totals, name) + getattr(step, name))


    def summary(self) -> dict[str, int | float | str | bool]:
        active_rows = np.flatnonzero(self.arena.active[: self.arena.size])
        holders = (
            int(np.unique(self.arena.holder_subject_id[active_rows]).size)
            if active_rows.size
            else 0
        )
        variants = int(np.count_nonzero(self.catalog.parent_content_id[: self.catalog.size]))
        summary = {
            "enabled": self.kcfg.enabled,
            "schema": self.kcfg.schema,
            "outcome_schema": (
                self.kcfg.outcome_schema if self.kcfg.learning_enabled else None
            ),
            "learning_enabled": self.kcfg.learning_enabled,
            "policy_influence": self.kcfg.policy_influence_enabled,
            "policy_residual_schema": (
                self.kcfg.policy_residual_schema
                if self.kcfg.policy_influence_enabled
                else None
            ),
            "content_count": self.catalog.size,
            "variant_content_count": variants,
            "copy_count": self.arena.active_count,
            "holder_count": holders,
            "active_encoded_bytes": self.arena.active_bytes,
            "maintenance_energy_total": self.totals.maintenance_energy,
            "sender_energy_total": self.totals.sender_energy,
            "receiver_energy_total": self.totals.receiver_energy,
            "transfer_attempts_total": self.totals.transfer_attempts,
            "transfer_delivered_total": self.totals.transfer_delivered,
            "transfer_lost_total": self.totals.transfer_lost,
            "transfer_corrupted_total": self.totals.transfer_corrupted,
            "transfer_committed_total": self.totals.transfer_committed,
            "transfer_committed_bytes_total": self.totals.transfer_committed_bytes,
            "transfer_same_lineage_committed_total": self.totals.transfer_same_lineage_committed,
            "transfer_cross_lineage_committed_total": self.totals.transfer_cross_lineage_committed,
            "transfer_unknown_lineage_committed_total": self.totals.transfer_unknown_lineage_committed,
            "transfer_same_group_committed_total": self.totals.transfer_same_group_committed,
            "transfer_cross_group_committed_total": self.totals.transfer_cross_group_committed,
            "transfer_unknown_group_committed_total": self.totals.transfer_unknown_group_committed,
            "transfer_duplicate_rejected_total": self.totals.transfer_duplicate_rejected,
            "transfer_capacity_rejected_total": self.totals.transfer_capacity_rejected,
            "transfer_energy_rejected_total": self.totals.transfer_energy_rejected,
            "attention_rejected_total": self.totals.attention_rejected,
            "forgotten_total": self.totals.forgotten,
            "evicted_capacity_total": self.totals.evicted_capacity,
            "evicted_maintenance_total": self.totals.evicted_maintenance,
            "removed_dead_holder_total": self.totals.removed_dead_holder,
            "learning_energy_total": self.totals.learning_energy,
            "outcome_records_total": self.totals.outcome_records,
            "outcome_success_total": self.totals.outcome_success,
            "outcome_failed_total": self.totals.outcome_failed,
            "outcome_partial_total": self.totals.outcome_partial,
            "outcome_updates_total": self.totals.outcome_updates,
            "private_experiences_created_total": (
                self.totals.private_experiences_created
            ),
            "private_experience_updates_total": (
                self.totals.private_experience_updates
            ),
            "transferred_copies_verified_total": (
                self.totals.transferred_copies_verified
            ),
            "outcome_unmatched_total": self.totals.outcome_unmatched,
            "learning_energy_rejected_total": (
                self.totals.learning_energy_rejected
            ),
            "learning_capacity_rejected_total": (
                self.totals.learning_capacity_rejected
            ),
            "learning_match_limit_skipped_total": (
                self.totals.learning_match_limit_skipped
            ),
            "confidence_decayed_total": self.totals.confidence_decayed,
            "policy_influenced_entities_total": self.totals.policy_influenced_entities,
            "policy_influenced_actions_total": self.totals.policy_influenced_actions,
            "policy_support_copies_total": self.totals.policy_support_copies,
            "policy_private_support_copies_total": self.totals.policy_private_support_copies,
            "policy_transfer_support_copies_total": self.totals.policy_transfer_support_copies,
            "policy_unverified_transfer_support_copies_total": (
                self.totals.policy_unverified_transfer_support_copies
            ),
            "policy_changed_actions_total": self.totals.policy_changed_actions,
            "policy_residual_abs_sum_total": self.totals.policy_residual_abs_sum,
            "policy_latent_dimensions_total": self.totals.policy_latent_dimensions,
            "policy_latent_max_width": self.totals.policy_latent_max_width,
            "policy_quantized_residual_abs_sum_total": (
                self.totals.policy_quantized_residual_abs_sum
            ),
            "policy_linear_shadow_changed_actions_total": (
                self.totals.policy_linear_shadow_changed_actions
            ),
            "policy_router_saturation_units_total": (
                self.totals.policy_router_saturation_units
            ),
            "policy_router_clipped_outputs_total": (
                self.totals.policy_router_clipped_outputs
            ),
            "policy_router_hidden_abs_sum_total": (
                self.totals.policy_router_hidden_abs_sum
            ),
            "policy_router_hidden_active_units_total": (
                self.totals.policy_router_hidden_active_units
            ),
            "routing_cost_enabled": self.kcfg.routing_cost_enabled,
            "routing_cost_schema": (
                self.kcfg.routing_cost_schema if self.kcfg.routing_cost_enabled else None
            ),
            "routing_requested_energy_total": self.totals.routing_requested_energy,
            "routing_committed_energy_total": self.totals.routing_committed_energy,
            "routing_rejected_energy_total": self.totals.routing_rejected_energy,
            "routing_requested_entities_total": self.totals.routing_requested_entities,
            "routing_committed_entities_total": self.totals.routing_committed_entities,
            "routing_rejected_entities_total": self.totals.routing_rejected_entities,
            "routing_accepted_actions_total": self.totals.routing_accepted_actions,
            "routing_rejected_actions_total": self.totals.routing_rejected_actions,
            "routing_latent_dimensions_total": self.totals.routing_latent_dimensions,
            "routing_mac_count_total": self.totals.routing_mac_count,
            "routing_active_hidden_units_total": self.totals.routing_active_hidden_units,
            "routing_saturation_count_total": self.totals.routing_saturation_count,
            "routing_clipped_output_count_total": self.totals.routing_clipped_output_count,
            "routing_cost_induced_action_changes_total": (
                self.totals.routing_cost_induced_action_changes
            ),
            "selection_schema": (
                self.kcfg.sparse_selection_schema
                if self.kcfg.sparse_selection_enabled else None
            ),
            "selection_candidate_copies_total": self.totals.selection_candidate_copies,
            "selection_selected_copies_total": self.totals.selection_selected_copies,
            "selection_requested_top_k_sum_total": (
                self.totals.selection_requested_top_k_sum
            ),
            "selection_zero_capacity_entities_total": (
                self.totals.selection_zero_capacity_entities
            ),
            "selection_tie_count_total": self.totals.selection_tie_count,
            "selection_committed_energy_total": self.totals.selection_committed_energy,
            "working_memory_schema": (
                self.kcfg.working_memory_schema
                if self.kcfg.working_memory_enabled else None
            ),
            "working_memory_requested_energy_total": (
                self.totals.working_memory_requested_energy
            ),
            "working_memory_committed_energy_total": (
                self.totals.working_memory_committed_energy
            ),
            "working_memory_rejected_energy_total": (
                self.totals.working_memory_rejected_energy
            ),
            "working_memory_requested_entities_total": (
                self.totals.working_memory_requested_entities
            ),
            "working_memory_committed_entities_total": (
                self.totals.working_memory_committed_entities
            ),
            "working_memory_rejected_entities_total": (
                self.totals.working_memory_rejected_entities
            ),
            "working_memory_saturation_units_total": (
                self.totals.working_memory_saturation_units
            ),
            "working_memory_active_dimensions_total": (
                self.totals.working_memory_active_dimensions
            ),
            "working_memory_induced_action_changes_total": (
                self.totals.working_memory_induced_action_changes
            ),
        }
        if self.latent_store is not None:
            summary.update(self.latent_store.summary())
        summary.update(self.candidates.summary())
        return summary


    def root_content_id(self, content_id: int) -> int:
        """Return the immutable root content for a content/variant id."""
        current = int(content_id)
        if current <= 0:
            raise ValueError("content id must be positive")
        while True:
            row = self.catalog.row(current)
            parent = int(self.catalog.parent_content_id[row])
            if parent == 0:
                return current
            current = parent


    def active_transferred_root_presence(
        self,
        *,
        alive: np.ndarray,
        primary_subject_ids: np.ndarray,
    ) -> tuple[np.ndarray, np.ndarray]:
        """Deduplicated ``(entity_index, root_id)`` for active transfer copies."""
        subject_to_entity = {
            int(subject): int(index)
            for index, subject in enumerate(np.asarray(primary_subject_ids, dtype=np.uint64))
            if bool(np.asarray(alive, dtype=bool)[index]) and int(subject) != 0
        }
        pairs: set[tuple[int, int]] = set()
        rows = np.flatnonzero(self.arena.active[: self.arena.size])
        for row in rows.tolist():
            if int(self.arena.acquisition_kind[row]) != ACQUISITION_TRANSFER:
                continue
            holder = int(self.arena.holder_subject_id[row])
            entity = subject_to_entity.get(holder)
            if entity is None:
                continue
            pairs.add((entity, self.root_content_id(int(self.arena.content_id[row]))))
        if not pairs:
            return (
                np.empty(0, dtype=np.int32),
                np.empty(0, dtype=np.uint64),
            )
        ordered = sorted(pairs)
        return (
            np.asarray([item[0] for item in ordered], dtype=np.int32),
            np.asarray([item[1] for item in ordered], dtype=np.uint64),
        )


    def long_run_diagnostics(
        self,
        *,
        alive: np.ndarray,
        primary_subject_ids: np.ndarray,
        lineage_ids: np.ndarray,
        group_ids: np.ndarray,
    ) -> dict[str, int | float | str]:
        """Return observational knowledge-lineage diagnostics.

        Counts are based on active holder/root-content presences so a holder
        carrying several variants of one root does not artificially multiply
        that root's cultural prevalence.
        """
        base: dict[str, int | float | str] = {
            "knowledge_lineage_diagnostics_schema": "knowledge-root-lineage-v1",
            "knowledge_active_root_content_count": 0,
            "knowledge_effective_root_contents": 0.0,
            "knowledge_largest_root_holder_fraction": 0.0,
            "knowledge_root_multi_genetic_lineage_fraction": 0.0,
            "knowledge_root_multi_group_fraction": 0.0,
            "knowledge_root_genetic_lineage_nmi": 0.0,
            "knowledge_root_group_nmi": 0.0,
            "knowledge_same_genetic_lineage_given_same_root": 0.0,
            "knowledge_same_root_given_same_genetic_lineage": 0.0,
            "knowledge_root_genetic_lineage_pair_enrichment": 0.0,
            "knowledge_same_group_given_same_root": 0.0,
            "knowledge_same_root_given_same_group": 0.0,
            "knowledge_root_group_pair_enrichment": 0.0,
            "knowledge_holder_root_presence_count": 0,
            "knowledge_transfer_trigger_schema": "signal-action-partner-v1",
            "knowledge_transfer_configured_probability": float(self.kcfg.transfer_probability),
            "knowledge_transfer_configured_period": int(self.kcfg.transfer_period),
            "knowledge_transfer_effective_enabled": int(
                bool(self.kcfg.enabled and self.kcfg.transfer_probability > 0.0)
            ),
            "knowledge_transfer_proposals_total": int(
                self.totals.transfer_attempts + self.totals.attention_rejected
            ),
            "knowledge_transfer_attempts_total": int(self.totals.transfer_attempts),
            "knowledge_transfer_delivered_total": int(self.totals.transfer_delivered),
            "knowledge_transfer_lost_total": int(self.totals.transfer_lost),
            "knowledge_transfer_corrupted_total": int(self.totals.transfer_corrupted),
            "knowledge_transfer_committed_total": int(self.totals.transfer_committed),
            "knowledge_transfer_committed_bytes_total": int(
                self.totals.transfer_committed_bytes
            ),
            "knowledge_transfer_duplicate_rejected_total": int(
                self.totals.transfer_duplicate_rejected
            ),
            "knowledge_transfer_capacity_rejected_total": int(
                self.totals.transfer_capacity_rejected
            ),
            "knowledge_transfer_energy_rejected_total": int(
                self.totals.transfer_energy_rejected
            ),
            "knowledge_transfer_attention_rejected_total": int(
                self.totals.attention_rejected
            ),
            "knowledge_transfer_same_lineage_committed_total": int(
                self.totals.transfer_same_lineage_committed
            ),
            "knowledge_transfer_cross_lineage_committed_total": int(
                self.totals.transfer_cross_lineage_committed
            ),
            "knowledge_transfer_unknown_lineage_committed_total": int(
                self.totals.transfer_unknown_lineage_committed
            ),
            "knowledge_transfer_same_group_committed_total": int(
                self.totals.transfer_same_group_committed
            ),
            "knowledge_transfer_cross_group_committed_total": int(
                self.totals.transfer_cross_group_committed
            ),
            "knowledge_transfer_unknown_group_committed_total": int(
                self.totals.transfer_unknown_group_committed
            ),
            "knowledge_transfer_sender_energy_total": float(self.totals.sender_energy),
            "knowledge_transfer_receiver_energy_total": float(self.totals.receiver_energy),
            "knowledge_cultural_spread_interpretable": int(
                self.totals.transfer_committed > 0
            ),
            "knowledge_active_transferred_copy_count": 0,
            "knowledge_active_transferred_root_count": 0,
            "knowledge_effective_transferred_roots": 0.0,
            "knowledge_largest_transferred_root_holder_fraction": 0.0,
            "knowledge_transferred_root_multi_genetic_lineage_fraction": 0.0,
            "knowledge_transferred_root_multi_group_fraction": 0.0,
            "knowledge_transferred_root_genetic_lineage_pair_enrichment": 0.0,
            "knowledge_transferred_root_group_pair_enrichment": 0.0,
            "knowledge_transferred_holder_root_presence_count": 0,
        }
        if not self.kcfg.enabled or self.catalog.size == 0 or self.arena.active_count == 0:
            return base

        root_by_content = np.zeros(self.catalog.size + 1, dtype=np.uint64)
        for row in range(self.catalog.size):
            content_id = int(self.catalog.content_id[row])
            parent_id = int(self.catalog.parent_content_id[row])
            root_by_content[content_id] = (
                np.uint64(content_id) if parent_id == 0 else root_by_content[parent_id]
            )

        active_entities = np.flatnonzero(np.asarray(alive, dtype=bool)).astype(np.int32)
        subject_to_entity = {
            int(primary_subject_ids[index]): int(index) for index in active_entities
        }
        rows = np.flatnonzero(self.arena.active[: self.arena.size]).astype(np.int32)
        holder_root: set[tuple[int, int]] = set()
        for row in rows.tolist():
            holder = int(self.arena.holder_subject_id[row])
            if holder not in subject_to_entity:
                continue
            content = int(self.arena.content_id[row])
            holder_root.add((holder, int(root_by_content[content])))
        if not holder_root:
            return base

        ordered = sorted(holder_root)
        holders = np.asarray([item[0] for item in ordered], dtype=np.uint64)
        roots = np.asarray([item[1] for item in ordered], dtype=np.uint64)
        entities = np.asarray([subject_to_entity[int(holder)] for holder in holders], dtype=np.int32)
        genetic = np.asarray(lineage_ids, dtype=np.uint64)[entities]
        groups = np.asarray(group_ids, dtype=np.uint64)[entities]
        unique_roots, root_counts = np.unique(roots, return_counts=True)
        shares = root_counts.astype(np.float64) / max(float(root_counts.sum()), 1.0)

        def alignment(left: np.ndarray, right: np.ndarray) -> dict[str, float]:
            if left.size == 0:
                return {
                    "nmi": 0.0,
                    "same_left_given_same_right": 0.0,
                    "same_right_given_same_left": 0.0,
                    "pair_enrichment": 0.0,
                }
            _, li = np.unique(left, return_inverse=True)
            _, ri = np.unique(right, return_inverse=True)
            joint = np.zeros((int(li.max()) + 1, int(ri.max()) + 1), dtype=np.int64)
            np.add.at(joint, (li, ri), 1)
            pxy = joint.astype(np.float64) / float(left.size)
            px = pxy.sum(axis=1)
            py = pxy.sum(axis=0)
            expected = px[:, None] * py[None, :]
            valid = pxy > 0.0
            mi = float(np.sum(pxy[valid] * np.log(pxy[valid] / expected[valid])))
            hx = float(-np.sum(px[px > 0.0] * np.log(px[px > 0.0])))
            hy = float(-np.sum(py[py > 0.0] * np.log(py[py > 0.0])))
            pair_total = int(left.size * (left.size - 1) // 2)
            left_sizes = joint.sum(axis=1)
            right_sizes = joint.sum(axis=0)
            left_pairs = int(np.sum(left_sizes * (left_sizes - 1) // 2))
            right_pairs = int(np.sum(right_sizes * (right_sizes - 1) // 2))
            both_pairs = int(np.sum(joint * (joint - 1) // 2))
            baseline_left = left_pairs / pair_total if pair_total else 0.0
            baseline_right = right_pairs / pair_total if pair_total else 0.0
            return {
                "nmi": float(mi / max((max(hx, 0.0) * max(hy, 0.0)) ** 0.5, 1e-30)),
                "same_left_given_same_right": float(
                    both_pairs / right_pairs if right_pairs else 0.0
                ),
                "same_right_given_same_left": float(
                    both_pairs / left_pairs if left_pairs else 0.0
                ),
                "pair_enrichment": float(
                    (both_pairs / pair_total) / (baseline_left * baseline_right)
                    if pair_total and baseline_left > 0.0 and baseline_right > 0.0
                    else 0.0
                ),
            }

        multi_lineage = 0
        multi_group = 0
        for root in unique_roots.tolist():
            mask = roots == np.uint64(root)
            if np.unique(genetic[mask]).size > 1:
                multi_lineage += 1
            root_groups = groups[mask]
            root_groups = root_groups[root_groups != 0]
            if np.unique(root_groups).size > 1:
                multi_group += 1
        transferred_holder_root: set[tuple[int, int]] = set()
        transferred_active_copy_count = 0
        for row in rows.tolist():
            if int(self.arena.acquisition_kind[row]) != ACQUISITION_TRANSFER:
                continue
            holder = int(self.arena.holder_subject_id[row])
            if holder not in subject_to_entity:
                continue
            content = int(self.arena.content_id[row])
            transferred_holder_root.add((holder, int(root_by_content[content])))
            transferred_active_copy_count += 1

        transferred_metrics: dict[str, int | float] = {}
        if transferred_holder_root:
            transferred_ordered = sorted(transferred_holder_root)
            transferred_holders = np.asarray(
                [item[0] for item in transferred_ordered], dtype=np.uint64
            )
            transferred_roots = np.asarray(
                [item[1] for item in transferred_ordered], dtype=np.uint64
            )
            transferred_entities = np.asarray(
                [subject_to_entity[int(holder)] for holder in transferred_holders],
                dtype=np.int32,
            )
            transferred_genetic = np.asarray(lineage_ids, dtype=np.uint64)[
                transferred_entities
            ]
            transferred_groups = np.asarray(group_ids, dtype=np.uint64)[
                transferred_entities
            ]
            unique_transferred_roots, transferred_counts = np.unique(
                transferred_roots, return_counts=True
            )
            transferred_shares = transferred_counts.astype(np.float64) / max(
                float(transferred_counts.sum()), 1.0
            )
            transferred_multi_lineage = 0
            transferred_multi_group = 0
            for root in unique_transferred_roots.tolist():
                mask = transferred_roots == np.uint64(root)
                if np.unique(transferred_genetic[mask]).size > 1:
                    transferred_multi_lineage += 1
                root_groups = transferred_groups[mask]
                root_groups = root_groups[root_groups != 0]
                if np.unique(root_groups).size > 1:
                    transferred_multi_group += 1
            transferred_genetic_alignment = alignment(
                transferred_roots, transferred_genetic
            )
            transferred_grouped = transferred_groups != 0
            transferred_group_alignment = (
                alignment(
                    transferred_roots[transferred_grouped],
                    transferred_groups[transferred_grouped],
                )
                if np.any(transferred_grouped)
                else alignment(
                    np.empty(0, dtype=np.uint64), np.empty(0, dtype=np.uint64)
                )
            )
            transferred_metrics = {
                "knowledge_active_transferred_copy_count": int(
                    transferred_active_copy_count
                ),
                "knowledge_active_transferred_root_count": int(
                    unique_transferred_roots.size
                ),
                "knowledge_effective_transferred_roots": float(
                    1.0 / np.sum(transferred_shares * transferred_shares)
                ),
                "knowledge_largest_transferred_root_holder_fraction": float(
                    transferred_shares.max()
                ),
                "knowledge_transferred_root_multi_genetic_lineage_fraction": float(
                    transferred_multi_lineage / unique_transferred_roots.size
                ),
                "knowledge_transferred_root_multi_group_fraction": float(
                    transferred_multi_group / unique_transferred_roots.size
                ),
                "knowledge_transferred_root_genetic_lineage_pair_enrichment": float(
                    transferred_genetic_alignment["pair_enrichment"]
                ),
                "knowledge_transferred_root_group_pair_enrichment": float(
                    transferred_group_alignment["pair_enrichment"]
                ),
                "knowledge_transferred_holder_root_presence_count": int(
                    transferred_roots.size
                ),
            }

        grouped = groups != 0
        root_genetic = alignment(roots, genetic)
        root_group = (
            alignment(roots[grouped], groups[grouped])
            if np.any(grouped)
            else alignment(np.empty(0, dtype=np.uint64), np.empty(0, dtype=np.uint64))
        )
        base.update(
            {
                "knowledge_active_root_content_count": int(unique_roots.size),
                "knowledge_effective_root_contents": float(
                    1.0 / np.sum(shares * shares)
                ),
                "knowledge_largest_root_holder_fraction": float(shares.max()),
                "knowledge_root_multi_genetic_lineage_fraction": float(
                    multi_lineage / unique_roots.size
                ),
                "knowledge_root_multi_group_fraction": float(
                    multi_group / unique_roots.size
                ),
                "knowledge_root_genetic_lineage_nmi": root_genetic["nmi"],
                "knowledge_root_group_nmi": root_group["nmi"],
                "knowledge_same_genetic_lineage_given_same_root": (
                    root_genetic["same_right_given_same_left"]
                ),
                "knowledge_same_root_given_same_genetic_lineage": (
                    root_genetic["same_left_given_same_right"]
                ),
                "knowledge_root_genetic_lineage_pair_enrichment": (
                    root_genetic["pair_enrichment"]
                ),
                "knowledge_same_group_given_same_root": (
                    root_group["same_right_given_same_left"]
                ),
                "knowledge_same_root_given_same_group": (
                    root_group["same_left_given_same_right"]
                ),
                "knowledge_root_group_pair_enrichment": (
                    root_group["pair_enrichment"]
                ),
                "knowledge_holder_root_presence_count": int(roots.size),
                **transferred_metrics,
            }
        )
        return base


    def validate(self, alive: np.ndarray, primary_subject_ids: np.ndarray) -> None:
        if not self.kcfg.enabled:
            return
        active = np.flatnonzero(self.arena.active[: self.arena.size])
        if active.size:
            if np.unique(self.arena.copy_id[active]).size != active.size:
                raise AssertionError("active knowledge copy IDs must be unique")
            if np.any(self.arena.content_id[active] > self.catalog.size):
                raise AssertionError("knowledge copy references missing content")
            living_subjects = set(int(value) for value in primary_subject_ids[alive])
            if any(
                int(holder) not in living_subjects
                for holder in self.arena.holder_subject_id[active]
            ):
                raise AssertionError("knowledge copy belongs to a dead holder")
            if (
                np.any(~np.isfinite(self.arena.outcome_mean[active]))
                or np.any(~np.isfinite(self.arena.outcome_m2[active]))
                or np.any(self.arena.outcome_m2[active] < 0.0)
                or np.any((self.arena.confidence[active] < 0.0) | (self.arena.confidence[active] > 1.0))
            ):
                raise AssertionError("knowledge local outcome-state invariant failed")
            for holder in np.unique(self.arena.holder_subject_id[active]):
                if self.arena.holder_bytes(int(holder)) > self.kcfg.holder_capacity_bytes:
                    raise AssertionError("knowledge holder exceeds byte capacity")
        if self.catalog.size and (
            np.unique(self.catalog.content_id[: self.catalog.size]).size != self.catalog.size
            or np.any(self.catalog.encoded_bytes[: self.catalog.size] == 0)
            or np.any(~np.isfinite(self.catalog.outcome_vector[: self.catalog.size]))
        ):
            raise AssertionError("knowledge catalog invariant failed")
        if self.latent_store is not None:
            self.latent_store.ensure_catalog(self.catalog)
            if self.latent_store.size != self.catalog.size:
                raise AssertionError("latent knowledge store is missing catalog contents")
            if any(
                int(value) not in set(self.kcfg.latent_length_levels)
                for value in self.latent_store.length[: self.latent_store.size]
            ):
                raise AssertionError("latent knowledge length level invariant failed")
        self.candidates.validate(self.catalog, self.arena)


    def checkpoint_arrays(self) -> dict[str, np.ndarray]:
        active = np.flatnonzero(self.arena.active[: self.arena.size])
        catalog = self.catalog.arrays()
        arrays = {
            "knowledge_content_id": catalog["content_id"],
            "knowledge_parent_content_id": catalog["parent_content_id"],
            "knowledge_context_key": catalog["context_key"],
            "knowledge_action_id": catalog["action_id"],
            "knowledge_outcome_vector": catalog["outcome_vector"],
            "knowledge_content_encoded_bytes": catalog["encoded_bytes"],
            "knowledge_content_created_tick": catalog["created_tick"],
            "knowledge_content_source_subject_id": catalog["source_subject_id"],
            "knowledge_copy_id": self.arena.copy_id[active],
            "knowledge_holder_subject_id": self.arena.holder_subject_id[active],
            "knowledge_copy_content_id": self.arena.content_id[active],
            "knowledge_copy_source_subject_id": self.arena.source_subject_id[active],
            "knowledge_confidence": self.arena.confidence[active],
            "knowledge_sample_count": self.arena.sample_count[active],
            "knowledge_copy_created_tick": self.arena.created_tick[active],
            "knowledge_last_verified_tick": self.arena.last_verified_tick[active],
            "knowledge_copy_encoded_bytes": self.arena.encoded_bytes[active],
            "knowledge_copy_outcome_mean": self.arena.outcome_mean[active],
            "knowledge_copy_outcome_m2": self.arena.outcome_m2[active],
            "knowledge_copy_acquisition_kind": self.arena.acquisition_kind[active],
        }
        if self.latent_store is not None:
            latent = self.latent_store.arrays()
            arrays.update(
                {
                    "knowledge_latent_length": latent["length"],
                    "knowledge_latent_offset": latent["offset"],
                    "knowledge_latent_values": latent["values"],
                }
            )
        arrays.update(self.candidates.checkpoint_arrays())
        return arrays

