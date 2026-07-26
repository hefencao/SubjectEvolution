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


from .diagnostics import KnowledgeDiagnosticsMixin
from .logging import KnowledgeLoggingMixin


class KnowledgeSystem(KnowledgeLoggingMixin, KnowledgeDiagnosticsMixin):
    """K1/K2 knowledge lifecycle, local learning, costs, and metrics."""

    def __init__(
        self,
        cfg: SimulationConfig,
        output_dir: str | Path,
        *,
        initial_entity_ids: np.ndarray,
        initial_subject_ids: np.ndarray,
        initial_knowledge_capacities: np.ndarray | None = None,
    ) -> None:
        self.cfg = cfg
        self.kcfg: KnowledgeConfig = cfg.knowledge
        self.catalog = KnowledgeCatalog()
        if self.kcfg.latent_policy_enabled:
            from .latent import VariableLatentContentStore
        self.latent_store = (
            VariableLatentContentStore(self.kcfg, cfg.run.seed)
            if self.kcfg.latent_policy_enabled
            else None
        )
        self.arena = KnowledgeArena()
        self.last_transfer_plan = KnowledgeTransferPlan.empty(0)
        self.last_transfer_commit_audit = KnowledgeTransferCommitAudit.empty(0)
        self.last_outcome_plan = KnowledgeOutcomePlan.empty(0)
        self.observation = KnowledgeObservationPlan.empty(0)
        self.totals = KnowledgeStepStats()
        # Runtime causal-ablation flags.  They are world state and therefore
        # checkpointed/cloned, but remain false for ordinary runs.
        self.working_memory_ablation_enabled = False
        self.sparse_selection_ablation_enabled = False
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.candidates = KnowledgeCandidateTracker(self.kcfg, self.output_dir)
        self._event_file = None
        self._transfer_file = None
        self._transfer_writer = None
        self._outcome_file = None
        self._outcome_writer = None
        self._policy_file = None
        self._policy_writer = None
        self._routing_cost_file = None
        self._routing_cost_writer = None
        self._working_memory_file = None
        self._working_memory_writer = None
        self._selection_file = None
        self._selection_writer = None
        if self.kcfg.enabled:
            self._event_file = (self.output_dir / "knowledge_events.jsonl").open(
                "w", encoding="utf-8"
            )
            if self.kcfg.log_transfer_events:
                self._transfer_file = (self.output_dir / "knowledge_transfers.csv").open(
                    "w", newline="", encoding="utf-8"
                )
                self._transfer_writer = csv.DictWriter(
                    self._transfer_file,
                    fieldnames=[
                        "tick", "sender_entity_index", "receiver_entity_index",
                        "sender_subject_id", "receiver_subject_id",
                        "sender_lineage_id", "receiver_lineage_id",
                        "sender_group_id", "receiver_group_id",
                        "source_subject_id", "source_copy_id", "content_id",
                        "committed_content_id", "encoded_bytes", "delivered",
                        "corrupted", "status", "sender_cost_charged",
                        "receiver_cost_charged",
                    ],
                )
                self._transfer_writer.writeheader()
            if self.kcfg.log_outcome_updates:
                self._outcome_file = (
                    self.output_dir / "knowledge_outcome_updates.csv"
                ).open("w", newline="", encoding="utf-8")
                self._outcome_writer = csv.DictWriter(
                    self._outcome_file,
                    fieldnames=[
                        "tick", "entity_id", "holder_subject_id", "context_key",
                        "action_id", "status", "failure_reason", "update_kind",
                        "copy_id", "content_id", "sample_count_before",
                        "sample_count_after", "confidence_before",
                        "confidence_after", "energy_delta", "integrity_delta",
                        "material_delta", "information_delta",
                        "reproduction_opportunity_delta",
                    ],
                )
                self._outcome_writer.writeheader()
            if self.kcfg.log_policy_contributions:
                self._policy_file = (
                    self.output_dir / "knowledge_policy_contributions.csv"
                ).open("w", newline="", encoding="utf-8")
                self._policy_writer = csv.DictWriter(
                    self._policy_file,
                    fieldnames=[
                        "tick", "entity_id", "holder_subject_id", "context_key",
                        "action_id", "logit_residual", "support_copy_count",
                        "private_support_count", "transfer_support_count",
                        "unverified_transfer_support_count", "reliability_mass",
                        "energy_outcome", "integrity_outcome", "material_outcome",
                        "information_outcome", "reproduction_opportunity_outcome",
                        "router_schema", "latent_dimension_count",
                        "latent_max_width", "quantized_residual",
                        "linear_shadow_logit_residual",
                        "linear_shadow_quantized_residual",
                        "router_saturation_count", "router_clipping_count",
                        "router_hidden_abs_sum", "router_hidden_active_count",
                        "selection_schema", "selection_candidate_count",
                        "selection_selected_count", "selection_requested_top_k",
                        "selection_tie_count",
                        "selection_score_threshold_q",
                    ],
                )
                self._policy_writer.writeheader()
            if self.kcfg.routing_cost_enabled:
                self._routing_cost_file = (
                    self.output_dir / "knowledge_routing_costs.csv"
                ).open("w", newline="", encoding="utf-8")
                self._routing_cost_writer = csv.DictWriter(
                    self._routing_cost_file,
                    fieldnames=[
                        "tick", "entity_id", "holder_subject_id", "accepted",
                        "requested_energy", "committed_energy",
                        "latent_dimensions", "mac_count",
                        "active_hidden_units", "saturation_count",
                        "clipped_output_count", "emitted_action_count",
                        "selection_candidate_count", "selection_selected_count",
                        "selection_requested_top_k", "selection_energy",
                    ],
                )
                self._routing_cost_writer.writeheader()
            if self.kcfg.working_memory_enabled:
                self._working_memory_file = (
                    self.output_dir / "knowledge_working_memory.csv"
                ).open("w", newline="", encoding="utf-8")
                self._working_memory_writer = csv.DictWriter(
                    self._working_memory_file,
                    fieldnames=[
                        "tick", "entity_id", "accepted", "requested_energy",
                        "committed_energy", "saturation_count",
                        "active_dimension_count", "previous_q", "proposed_q",
                        "committed_q", "observation_delta_q",
                        "prediction_error_q",
                    ],
                )
                self._working_memory_writer.writeheader()
            if self.kcfg.sparse_selection_enabled:
                self._selection_file = (
                    self.output_dir / "knowledge_selection_events.csv"
                ).open("w", newline="", encoding="utf-8")
                self._selection_writer = csv.DictWriter(
                    self._selection_file,
                    fieldnames=[
                        "tick", "active_row", "entity_id", "holder_subject_id",
                        "copy_id", "content_id", "score_q", "rank_within_entity",
                        "requested_top_k",
                    ],
                )
                self._selection_writer.writeheader()
            self._seed(
                initial_entity_ids,
                initial_subject_ids,
                initial_knowledge_capacities,
            )
            self.candidates.ensure_catalog(self.catalog)
            self.observation = self.arena.publish(self.catalog, tick=0)

    def _encoded_bytes_for_new_content(
        self,
        *,
        parent_content_id: int,
        context_key: int,
        action_id: int,
        source_subject_id: int,
    ) -> int:
        if self.latent_store is None:
            return int(self.kcfg.encoded_bytes_per_copy)
        return self.latent_store.encoded_bytes_for_next(
            parent_content_id=parent_content_id,
            context_key=context_key,
            action_id=action_id,
            source_subject_id=source_subject_id,
        )

    def _seed(
        self,
        entity_ids: np.ndarray,
        subject_ids: np.ndarray,
        knowledge_capacities: np.ndarray | None = None,
    ) -> None:
        if self.kcfg.initial_content_count <= 0 or self.kcfg.initial_holders_fraction <= 0.0:
            return
        ids = np.asarray(entity_ids, dtype=np.uint64)
        subjects = np.asarray(subject_ids, dtype=np.uint64)
        if ids.shape != subjects.shape:
            raise ValueError("knowledge seed IDs and subjects must align")
        capacities = (
            np.full(ids.shape, int(self.kcfg.holder_capacity_bytes), dtype=np.int64)
            if knowledge_capacities is None
            else np.asarray(knowledge_capacities, dtype=np.int64)
        )
        if capacities.shape != ids.shape or np.any(capacities < 0):
            raise ValueError("initial knowledge capacities must align with entities")
        source_subject = int(subjects[0]) if subjects.size else 1
        contents: list[int] = []
        for index in range(self.kcfg.initial_content_count):
            context_key = index + 1
            action_id = index % 8
            encoded_bytes = self._encoded_bytes_for_new_content(
                parent_content_id=0,
                context_key=context_key,
                action_id=action_id,
                source_subject_id=source_subject,
            )
            contents.append(
                self.catalog.append(
                    parent_content_id=0,
                    context_key=context_key,
                    action_id=action_id,
                    outcome_vector=np.zeros(OUTCOME_WIDTH, dtype=np.float32),
                    encoded_bytes=encoded_bytes,
                    created_tick=0,
                    source_subject_id=source_subject,
                )
            )
            if self.latent_store is not None:
                self.latent_store.ensure_catalog(self.catalog)
        ctx = RandomContext(
            self.cfg.run.seed, 0, phase=90, stream=Stream.KNOWLEDGE_SEED
        )
        selected = bernoulli(
            ctx, ids, self.kcfg.initial_holders_fraction, draw_index=0
        )
        for entity_id, subject_id, holder_capacity in zip(
            ids[selected], subjects[selected], capacities[selected], strict=True
        ):
            content_id = contents[(int(entity_id) - 1) % len(contents)]
            copy_bytes = int(self.catalog.encoded_bytes[content_id - 1])
            if int(holder_capacity) < copy_bytes:
                continue
            self.arena.append(
                holder_subject_id=int(subject_id),
                content_id=content_id,
                source_subject_id=source_subject,
                confidence=1.0,
                sample_count=0,
                created_tick=0,
                last_verified_tick=0,
                encoded_bytes=copy_bytes,
                outcome_mean=self.catalog.outcome_vector[content_id - 1],
                acquisition_kind=ACQUISITION_SEED,
            )

    def snapshot_state(self) -> dict[str, Any]:
        """Return all semantic knowledge state without open output handles."""
        return {
            "catalog": copy.deepcopy(self.catalog),
            "latent_store": copy.deepcopy(self.latent_store),
            "arena": copy.deepcopy(self.arena),
            "last_transfer_plan": copy.deepcopy(self.last_transfer_plan),
            "last_outcome_plan": copy.deepcopy(self.last_outcome_plan),
            "observation": copy.deepcopy(self.observation),
            "totals": copy.deepcopy(self.totals),
            "working_memory_ablation_enabled": bool(
                self.working_memory_ablation_enabled
            ),
            "sparse_selection_ablation_enabled": bool(
                self.sparse_selection_ablation_enabled
            ),
            "candidates": self.candidates.snapshot_state(),
        }

    def restore_state(self, state: dict[str, Any]) -> None:
        """Restore semantic state while retaining this run's output writers."""
        self.catalog = copy.deepcopy(state["catalog"])
        self.latent_store = copy.deepcopy(state.get("latent_store"))
        self.arena = copy.deepcopy(state["arena"])
        self.last_transfer_plan = copy.deepcopy(state["last_transfer_plan"])
        self.last_transfer_commit_audit = KnowledgeTransferCommitAudit.empty(
            int(self.last_transfer_plan.tick)
        )
        self.last_outcome_plan = copy.deepcopy(state["last_outcome_plan"])
        self.observation = copy.deepcopy(state["observation"])
        self.totals = copy.deepcopy(state["totals"])
        self.working_memory_ablation_enabled = bool(
            state.get("working_memory_ablation_enabled", False)
        )
        self.sparse_selection_ablation_enabled = bool(
            state.get("sparse_selection_ablation_enabled", False)
        )
        # Trusted checkpoints from earlier schemas unpickle the historical
        # dataclass without fields introduced later.  Initialize only missing
        # cumulative diagnostics; existing values remain untouched.
        defaults = KnowledgeStepStats()
        for name in KnowledgeStepStats.__dataclass_fields__:
            if not hasattr(self.totals, name):
                setattr(self.totals, name, copy.deepcopy(getattr(defaults, name)))
        self.candidates.restore_state(state["candidates"])

    def clone(self, output_dir: str | Path) -> "KnowledgeSystem":
        result = object.__new__(KnowledgeSystem)
        result.cfg = self.cfg
        result.kcfg = self.kcfg
        result.catalog = copy.deepcopy(self.catalog)
        result.latent_store = copy.deepcopy(self.latent_store)
        result.arena = copy.deepcopy(self.arena)
        result.last_transfer_plan = copy.deepcopy(self.last_transfer_plan)
        result.last_transfer_commit_audit = copy.deepcopy(
            self.last_transfer_commit_audit
        )
        result.last_outcome_plan = copy.deepcopy(self.last_outcome_plan)
        result.observation = copy.deepcopy(self.observation)
        result.totals = copy.deepcopy(self.totals)
        result.working_memory_ablation_enabled = bool(
            self.working_memory_ablation_enabled
        )
        result.sparse_selection_ablation_enabled = bool(
            self.sparse_selection_ablation_enabled
        )
        result.output_dir = Path(output_dir)
        result.output_dir.mkdir(parents=True, exist_ok=True)
        result.candidates = self.candidates.clone(result.output_dir)
        result._event_file = None
        result._transfer_file = None
        result._transfer_writer = None
        result._outcome_file = None
        result._outcome_writer = None
        result._policy_file = None
        result._policy_writer = None
        result._routing_cost_file = None
        result._routing_cost_writer = None
        result._working_memory_file = None
        result._working_memory_writer = None
        result._selection_file = None
        result._selection_writer = None
        if self.kcfg.enabled:
            result._event_file = (result.output_dir / "knowledge_events.jsonl").open(
                "w", encoding="utf-8"
            )
            if self.kcfg.log_transfer_events:
                result._transfer_file = (result.output_dir / "knowledge_transfers.csv").open(
                    "w", newline="", encoding="utf-8"
                )
                result._transfer_writer = csv.DictWriter(
                    result._transfer_file,
                    fieldnames=[
                        "tick", "sender_entity_index", "receiver_entity_index",
                        "sender_subject_id", "receiver_subject_id",
                        "sender_lineage_id", "receiver_lineage_id",
                        "sender_group_id", "receiver_group_id",
                        "source_subject_id", "source_copy_id", "content_id",
                        "committed_content_id", "encoded_bytes", "delivered",
                        "corrupted", "status", "sender_cost_charged",
                        "receiver_cost_charged",
                    ],
                )
                result._transfer_writer.writeheader()
            if self.kcfg.log_outcome_updates:
                result._outcome_file = (
                    result.output_dir / "knowledge_outcome_updates.csv"
                ).open("w", newline="", encoding="utf-8")
                result._outcome_writer = csv.DictWriter(
                    result._outcome_file,
                    fieldnames=[
                        "tick", "entity_id", "holder_subject_id", "context_key",
                        "action_id", "status", "failure_reason", "update_kind",
                        "copy_id", "content_id", "sample_count_before",
                        "sample_count_after", "confidence_before",
                        "confidence_after", "energy_delta", "integrity_delta",
                        "material_delta", "information_delta",
                        "reproduction_opportunity_delta",
                    ],
                )
                result._outcome_writer.writeheader()
            if self.kcfg.log_policy_contributions:
                result._policy_file = (
                    result.output_dir / "knowledge_policy_contributions.csv"
                ).open("w", newline="", encoding="utf-8")
                result._policy_writer = csv.DictWriter(
                    result._policy_file,
                    fieldnames=[
                        "tick", "entity_id", "holder_subject_id", "context_key",
                        "action_id", "logit_residual", "support_copy_count",
                        "private_support_count", "transfer_support_count",
                        "unverified_transfer_support_count", "reliability_mass",
                        "energy_outcome", "integrity_outcome", "material_outcome",
                        "information_outcome", "reproduction_opportunity_outcome",
                        "router_schema", "latent_dimension_count",
                        "latent_max_width", "quantized_residual",
                        "linear_shadow_logit_residual",
                        "linear_shadow_quantized_residual",
                        "router_saturation_count", "router_clipping_count",
                        "router_hidden_abs_sum", "router_hidden_active_count",
                        "selection_schema", "selection_candidate_count",
                        "selection_selected_count", "selection_requested_top_k",
                        "selection_tie_count",
                        "selection_score_threshold_q",
                    ],
                )
                result._policy_writer.writeheader()
            if self.kcfg.routing_cost_enabled:
                result._routing_cost_file = (
                    result.output_dir / "knowledge_routing_costs.csv"
                ).open("w", newline="", encoding="utf-8")
                result._routing_cost_writer = csv.DictWriter(
                    result._routing_cost_file,
                    fieldnames=[
                        "tick", "entity_id", "holder_subject_id", "accepted",
                        "requested_energy", "committed_energy",
                        "latent_dimensions", "mac_count",
                        "active_hidden_units", "saturation_count",
                        "clipped_output_count", "emitted_action_count",
                        "selection_candidate_count", "selection_selected_count",
                        "selection_requested_top_k", "selection_energy",
                    ],
                )
                result._routing_cost_writer.writeheader()
            if self.kcfg.working_memory_enabled:
                result._working_memory_file = (
                    result.output_dir / "knowledge_working_memory.csv"
                ).open("w", newline="", encoding="utf-8")
                result._working_memory_writer = csv.DictWriter(
                    result._working_memory_file,
                    fieldnames=[
                        "tick", "entity_id", "accepted", "requested_energy",
                        "committed_energy", "saturation_count",
                        "active_dimension_count", "previous_q", "proposed_q",
                        "committed_q", "observation_delta_q",
                        "prediction_error_q",
                    ],
                )
                result._working_memory_writer.writeheader()
            if self.kcfg.sparse_selection_enabled:
                result._selection_file = (
                    result.output_dir / "knowledge_selection_events.csv"
                ).open("w", newline="", encoding="utf-8")
                result._selection_writer = csv.DictWriter(
                    result._selection_file,
                    fieldnames=[
                        "tick", "active_row", "entity_id", "holder_subject_id",
                        "copy_id", "content_id", "score_q", "rank_within_entity",
                        "requested_top_k",
                    ],
                )
                result._selection_writer.writeheader()
        return result




    def _forget(self, tick: int) -> int:
        if self.kcfg.forget_probability <= 0.0 or self.arena.active_count == 0:
            return 0
        rows = np.flatnonzero(self.arena.active)
        ctx = RandomContext(
            self.cfg.run.seed, tick, phase=91, stream=Stream.KNOWLEDGE_FORGET
        )
        forgotten = bernoulli(
            ctx,
            self.arena.copy_id[rows],
            self.kcfg.forget_probability,
            draw_index=0,
        )
        removed = self.arena.deactivate(rows[forgotten])
        if removed:
            self._write_event({"tick": tick, "type": "forget", "copies": removed})
        return removed

    def enforce_capacities(
        self,
        *,
        alive: np.ndarray,
        primary_subject_id: np.ndarray,
        knowledge_capacities: np.ndarray,
    ) -> int:
        """Immediately evict copies above effective per-entity storage limits."""
        if not self.kcfg.enabled:
            return 0
        capacities = np.asarray(knowledge_capacities, dtype=np.int64)
        alive_array = np.asarray(alive, dtype=bool)
        subjects = np.asarray(primary_subject_id, dtype=np.uint64)
        if capacities.shape != alive_array.shape or subjects.shape != alive_array.shape:
            raise ValueError("knowledge capacity enforcement arrays must align")
        if np.any(capacities < 0):
            raise ValueError("knowledge capacities must be non-negative")
        active_entities = np.flatnonzero(alive_array)
        subject_to_entity = {
            int(subjects[index]): int(index) for index in active_entities
        }
        evicted = 0
        active_holders = np.unique(self.arena.holder_subject_id[self.arena.active])
        for holder in active_holders:
            holder_id = int(holder)
            entity_index = subject_to_entity.get(holder_id)
            if entity_index is None:
                continue
            excess = self.arena.holder_bytes(holder_id) - int(capacities[entity_index])
            if excess > 0:
                evicted += self.arena.evict_oldest(holder_id, excess)
        self.observation = self.arena.publish(self.catalog, tick=self.observation.tick)
        return int(evicted)

    def charge_maintenance(
        self,
        *,
        energy: np.ndarray,
        alive: np.ndarray,
        primary_subject_id: np.ndarray,
        tick: int,
        knowledge_capacities: np.ndarray | None = None,
    ) -> KnowledgeStepStats:
        stats = KnowledgeStepStats()
        if not self.kcfg.enabled:
            return stats
        stats.forgotten = self._forget(tick)
        if (
            self.kcfg.learning_enabled
            and self.kcfg.confidence_decay_per_tick > 0.0
            and self.arena.active_count
        ):
            rows = np.flatnonzero(self.arena.active[: self.arena.size])
            before = self.arena.confidence[rows].copy()
            self.arena.confidence[rows] *= np.float32(
                1.0 - self.kcfg.confidence_decay_per_tick
            )
            stats.confidence_decayed = int(
                np.count_nonzero(self.arena.confidence[rows] != before)
            )
        capacities = (
            np.full(alive.shape, int(self.kcfg.holder_capacity_bytes), dtype=np.int64)
            if knowledge_capacities is None
            else np.asarray(knowledge_capacities, dtype=np.int64)
        )
        if capacities.shape != alive.shape or np.any(capacities < 0):
            raise ValueError("knowledge capacities must align with entity state")
        active_entities = np.flatnonzero(alive)
        subject_to_entity = {
            int(primary_subject_id[index]): int(index) for index in active_entities
        }
        active_holders = np.unique(self.arena.holder_subject_id[self.arena.active])
        for holder in active_holders:
            holder_id = int(holder)
            entity_index = subject_to_entity.get(holder_id)
            if entity_index is None:
                rows = self.arena.rows_for_holder(holder_id)
                stats.removed_dead_holder += self.arena.deactivate(rows)
                continue
            holder_capacity = int(capacities[entity_index])
            bytes_held = self.arena.holder_bytes(holder_id)
            if bytes_held > holder_capacity:
                stats.evicted_capacity += self.arena.evict_oldest(
                    holder_id, bytes_held - holder_capacity
                )
                bytes_held = self.arena.holder_bytes(holder_id)
            cost = bytes_held * self.kcfg.maintenance_energy_per_byte
            if cost > float(energy[entity_index]) + 1e-12:
                affordable_bytes = int(
                    float(energy[entity_index])
                    / max(self.kcfg.maintenance_energy_per_byte, 1e-30)
                )
                bytes_to_release = max(bytes_held - affordable_bytes, 0)
                stats.evicted_maintenance += self.arena.evict_oldest(
                    holder_id, bytes_to_release
                )
                bytes_held = self.arena.holder_bytes(holder_id)
                cost = bytes_held * self.kcfg.maintenance_energy_per_byte
            charged = min(float(energy[entity_index]), cost)
            energy[entity_index] = np.float32(float(energy[entity_index]) - charged)
            stats.maintenance_energy += charged
            if charged and self.kcfg.candidate_tracking_enabled:
                rows = np.asarray(self.arena.rows_for_holder(holder_id), dtype=np.int64)
                if rows.size:
                    self.candidates.record_maintenance(
                        content_ids=self.arena.content_id[rows],
                        holder_subject_id=holder_id,
                        encoded_bytes=self.arena.encoded_bytes[rows],
                        charged=charged,
                        tick=tick,
                    )
        return stats

    def plan_transfers(
        self,
        *,
        sender_entity_indices: np.ndarray,
        receiver_entity_indices: np.ndarray,
        entity_ids: np.ndarray,
        primary_subject_ids: np.ndarray,
        alive: np.ndarray,
        tick: int,
        attention_capacities: np.ndarray | None = None,
    ) -> KnowledgeTransferPlan:
        if (
            not self.kcfg.enabled
            or self.kcfg.transfer_probability <= 0.0
            or (tick + 1) % self.kcfg.transfer_period != 0
        ):
            return KnowledgeTransferPlan.empty(tick)
        senders = np.asarray(sender_entity_indices, dtype=np.int32)
        receivers = np.asarray(receiver_entity_indices, dtype=np.int32)
        if senders.shape != receivers.shape:
            raise ValueError("knowledge sender and receiver rows must align")
        valid = (
            (senders >= 0)
            & (senders < alive.size)
            & (receivers >= 0)
            & (receivers < alive.size)
        )
        senders = senders[valid]
        receivers = receivers[valid]
        if senders.size == 0:
            return KnowledgeTransferPlan.empty(tick)
        valid = alive[senders] & alive[receivers] & (senders != receivers)
        senders = senders[valid]
        receivers = receivers[valid]
        if senders.size == 0:
            return KnowledgeTransferPlan.empty(tick)
        sender_entity_ids = entity_ids[senders]
        gate_ctx = RandomContext(
            self.cfg.run.seed, tick, phase=92, stream=Stream.KNOWLEDGE_TRANSFER
        )
        selected = bernoulli(
            gate_ctx,
            sender_entity_ids,
            self.kcfg.transfer_probability,
            draw_index=0,
        )
        senders = senders[selected]
        receivers = receivers[selected]
        sender_entity_ids = sender_entity_ids[selected]
        if senders.size == 0:
            return KnowledgeTransferPlan.empty(tick)

        # Canonical receiver/sender order makes attention arbitration independent
        # of input batch order.
        order = np.lexsort((entity_ids[senders], entity_ids[receivers]))
        senders = senders[order]
        receivers = receivers[order]
        sender_entity_ids = sender_entity_ids[order]
        attention_rejected = 0
        attention = (
            np.full(alive.shape, int(self.kcfg.attention_slots_per_tick), dtype=np.int32)
            if attention_capacities is None
            else np.asarray(attention_capacities, dtype=np.int32)
        )
        if attention.shape != alive.shape or np.any(attention < 0):
            raise ValueError("knowledge attention capacities must align with entity state")
        if self.kcfg.attention_slots_per_tick >= 0:
            keep = np.zeros(senders.size, dtype=bool)
            seen: dict[int, int] = {}
            for row, receiver in enumerate(receivers):
                count = seen.get(int(receiver), 0)
                if count < int(attention[int(receiver)]):
                    keep[row] = True
                    seen[int(receiver)] = count + 1
            attention_rejected = int(np.count_nonzero(~keep))
            senders = senders[keep]
            receivers = receivers[keep]
            sender_entity_ids = sender_entity_ids[keep]
        if senders.size == 0:
            return KnowledgeTransferPlan.empty(tick, attention_rejected)

        selected_sender: list[int] = []
        selected_receiver: list[int] = []
        source_rows: list[int] = []
        for ordinal, (sender, receiver, entity_id) in enumerate(
            zip(senders, receivers, sender_entity_ids, strict=True)
        ):
            holder = int(primary_subject_ids[sender])
            rows = self.arena.rows_for_holder(holder)
            if not rows:
                continue
            choice = int(
                uniform01(gate_ctx, np.asarray([entity_id], dtype=np.uint64), ordinal + 1)[0]
                * len(rows)
            ) % len(rows)
            selected_sender.append(int(sender))
            selected_receiver.append(int(receiver))
            source_rows.append(rows[choice])
        if not source_rows:
            return KnowledgeTransferPlan.empty(tick, attention_rejected)

        senders = np.asarray(selected_sender, dtype=np.int32)
        receivers = np.asarray(selected_receiver, dtype=np.int32)
        rows = np.asarray(source_rows, dtype=np.int64)
        sender_ids = entity_ids[senders]
        delivery_ctx = RandomContext(
            self.cfg.run.seed, tick, phase=94, stream=Stream.KNOWLEDGE_CHANNEL
        )
        delivered = bernoulli(
            delivery_ctx,
            sender_ids,
            1.0 - self.cfg.information.channel_loss,
            draw_index=0,
        )
        corrupted = delivered & bernoulli(
            delivery_ctx,
            sender_ids,
            self.cfg.information.classification_error,
            draw_index=1,
        )
        plan = KnowledgeTransferPlan(
            tick=int(tick),
            sender_entity_indices=senders,
            receiver_entity_indices=receivers,
            sender_subject_ids=primary_subject_ids[senders].astype(np.uint64, copy=True),
            receiver_subject_ids=primary_subject_ids[receivers].astype(np.uint64, copy=True),
            source_subject_ids=self.arena.source_subject_id[rows].astype(np.uint64, copy=True),
            source_copy_ids=self.arena.copy_id[rows].astype(np.uint64, copy=True),
            content_ids=self.arena.content_id[rows].astype(np.uint64, copy=True),
            source_outcome_vectors=self.arena.outcome_mean[rows].astype(
                np.float32, copy=True
            ),
            source_confidences=self.arena.confidence[rows].astype(
                np.float32, copy=True
            ),
            source_sample_counts=self.arena.sample_count[rows].astype(
                np.uint32, copy=True
            ),
            encoded_bytes=self.arena.encoded_bytes[rows].astype(np.uint32, copy=True),
            delivered=delivered.astype(bool, copy=True),
            corrupted=corrupted.astype(bool, copy=True),
            attention_rejected=attention_rejected,
        )
        plan.validate(alive.size)
        return plan

    def commit_transfers(
        self,
        plan: KnowledgeTransferPlan,
        *,
        energy: np.ndarray,
        alive: np.ndarray,
        group_ids: np.ndarray | None = None,
        lineage_subject_ids: np.ndarray | None = None,
        x: np.ndarray | None = None,
        y: np.ndarray | None = None,
        world_width: float | None = None,
        world_height: float | None = None,
        knowledge_capacities: np.ndarray | None = None,
    ) -> KnowledgeStepStats:
        stats = KnowledgeStepStats(
            transfer_attempts=plan.size, attention_rejected=plan.attention_rejected
        )
        if not self.kcfg.enabled or plan.size == 0:
            self.last_transfer_plan = plan
            self.last_transfer_commit_audit = KnowledgeTransferCommitAudit.empty(plan.tick)
            return stats
        plan.validate(alive.size)
        capacities = (
            np.full(alive.shape, int(self.kcfg.holder_capacity_bytes), dtype=np.int64)
            if knowledge_capacities is None
            else np.asarray(knowledge_capacities, dtype=np.int64)
        )
        if capacities.shape != alive.shape or np.any(capacities < 0):
            raise ValueError("knowledge capacities must align with entity state")

        def region_for(entity_index: int) -> int:
            if (
                x is None
                or y is None
                or world_width is None
                or world_height is None
            ):
                return 0
            gx = max(int(self.kcfg.candidate_region_grid_x), 1)
            gy = max(int(self.kcfg.candidate_region_grid_y), 1)
            rx = min(max(int(float(x[entity_index]) / float(world_width) * gx), 0), gx - 1)
            ry = min(max(int(float(y[entity_index]) / float(world_height) * gy), 0), gy - 1)
            return 1 + rx + gx * ry

        def record(
            row: int,
            status: str,
            *,
            committed_content_id: int | None = None,
            sender_cost_charged: float = 0.0,
            receiver_cost_charged: float = 0.0,
        ) -> None:
            if self._transfer_writer is not None:
                self._transfer_writer.writerow(
                    {
                        "tick": plan.tick,
                        "sender_entity_index": int(plan.sender_entity_indices[row]),
                        "receiver_entity_index": int(plan.receiver_entity_indices[row]),
                        "sender_subject_id": int(plan.sender_subject_ids[row]),
                        "receiver_subject_id": int(plan.receiver_subject_ids[row]),
                        "sender_lineage_id": (
                            int(lineage_subject_ids[int(plan.sender_entity_indices[row])])
                            if lineage_subject_ids is not None else 0
                        ),
                        "receiver_lineage_id": (
                            int(lineage_subject_ids[int(plan.receiver_entity_indices[row])])
                            if lineage_subject_ids is not None else 0
                        ),
                        "sender_group_id": (
                            int(group_ids[int(plan.sender_entity_indices[row])])
                            if group_ids is not None else 0
                        ),
                        "receiver_group_id": (
                            int(group_ids[int(plan.receiver_entity_indices[row])])
                            if group_ids is not None else 0
                        ),
                        "source_subject_id": int(plan.source_subject_ids[row]),
                        "source_copy_id": int(plan.source_copy_ids[row]),
                        "content_id": int(plan.content_ids[row]),
                        "committed_content_id": (
                            int(committed_content_id) if committed_content_id is not None else 0
                        ),
                        "encoded_bytes": int(plan.encoded_bytes[row]),
                        "delivered": int(bool(plan.delivered[row])),
                        "corrupted": int(bool(plan.corrupted[row])),
                        "status": status,
                        "sender_cost_charged": float(sender_cost_charged),
                        "receiver_cost_charged": float(receiver_cost_charged),
                    }
                )
            if self.kcfg.candidate_tracking_enabled:
                sender = int(plan.sender_entity_indices[row])
                receiver = int(plan.receiver_entity_indices[row])
                self.candidates.record_transfer(
                    catalog=self.catalog,
                    tick=plan.tick,
                    source_content_id=int(plan.content_ids[row]),
                    committed_content_id=(
                        int(plan.content_ids[row])
                        if committed_content_id is None
                        else int(committed_content_id)
                    ),
                    sender_subject_id=int(plan.sender_subject_ids[row]),
                    receiver_subject_id=int(plan.receiver_subject_ids[row]),
                    status=status,
                    sender_cost=sender_cost_charged,
                    receiver_cost=receiver_cost_charged,
                    sender_group=(int(group_ids[sender]) if group_ids is not None else 0),
                    receiver_group=(int(group_ids[receiver]) if group_ids is not None else 0),
                    sender_lineage=(
                        int(lineage_subject_ids[sender])
                        if lineage_subject_ids is not None
                        else 0
                    ),
                    receiver_lineage=(
                        int(lineage_subject_ids[receiver])
                        if lineage_subject_ids is not None
                        else 0
                    ),
                    sender_region=region_for(sender),
                    receiver_region=region_for(receiver),
                )

        committed_senders: list[int] = []
        committed_receivers: list[int] = []
        committed_contents: list[int] = []
        committed_roots: list[int] = []
        committed_bytes: list[int] = []

        for row in range(plan.size):
            sender = int(plan.sender_entity_indices[row])
            receiver = int(plan.receiver_entity_indices[row])
            encoded_bytes = int(plan.encoded_bytes[row])
            send_cost = (
                self.kcfg.transfer_base_energy_cost
                + encoded_bytes * self.kcfg.transfer_energy_per_byte
            )
            if not alive[sender] or float(energy[sender]) + 1e-12 < send_cost:
                stats.transfer_energy_rejected += 1
                record(row, "sender-energy-rejected")
                continue
            energy[sender] = np.float32(float(energy[sender]) - send_cost)
            stats.sender_energy += send_cost
            if not bool(plan.delivered[row]):
                stats.transfer_lost += 1
                record(row, "lost", sender_cost_charged=send_cost)
                continue
            stats.transfer_delivered += 1
            if not alive[receiver]:
                record(row, "receiver-dead", sender_cost_charged=send_cost)
                continue
            receive_cost = encoded_bytes * self.kcfg.receive_energy_per_byte
            if float(energy[receiver]) + 1e-12 < receive_cost:
                stats.transfer_energy_rejected += 1
                record(row, "receiver-energy-rejected", sender_cost_charged=send_cost)
                continue
            receiver_subject = int(plan.receiver_subject_ids[row])
            content_id = int(plan.content_ids[row])
            storage_encoded_bytes = encoded_bytes
            if bool(plan.corrupted[row]) and self.latent_store is not None:
                source_catalog_row = content_id - 1
                storage_encoded_bytes = self.latent_store.encoded_bytes_for_next(
                    parent_content_id=content_id,
                    context_key=int(self.catalog.context_key[source_catalog_row]),
                    action_id=int(self.catalog.action_id[source_catalog_row]),
                    source_subject_id=int(plan.sender_subject_ids[row]),
                )
            if self.arena.has_content(receiver_subject, content_id):
                stats.transfer_duplicate_rejected += 1
                record(row, "duplicate-rejected", sender_cost_charged=send_cost)
                continue
            receiver_capacity = int(capacities[receiver])
            if storage_encoded_bytes > receiver_capacity:
                stats.transfer_capacity_rejected += 1
                record(row, "oversize-rejected", sender_cost_charged=send_cost)
                continue
            required = max(
                self.arena.holder_bytes(receiver_subject)
                + storage_encoded_bytes
                - receiver_capacity,
                0,
            )
            if required:
                stats.evicted_capacity += self.arena.evict_oldest(
                    receiver_subject, required
                )
            if (
                self.arena.holder_bytes(receiver_subject) + storage_encoded_bytes
                > receiver_capacity
            ):
                stats.transfer_capacity_rejected += 1
                record(row, "capacity-rejected", sender_cost_charged=send_cost)
                continue
            energy[receiver] = np.float32(float(energy[receiver]) - receive_cost)
            stats.receiver_energy += receive_cost
            if bool(plan.corrupted[row]):
                transmitted_outcome = (
                    plan.source_outcome_vectors[row]
                    if plan.source_outcome_vectors.shape == (plan.size, OUTCOME_WIDTH)
                    else None
                )
                content_id = self.catalog.create_corrupted_variant(
                    content_id,
                    tick=plan.tick,
                    source_subject_id=int(plan.sender_subject_ids[row]),
                    run_seed=self.cfg.run.seed,
                    outcome_vector=transmitted_outcome,
                )
                if self.latent_store is not None:
                    self.latent_store.ensure_catalog(self.catalog)
                    encoded_bytes = int(self.catalog.encoded_bytes[content_id - 1])
                    if encoded_bytes != storage_encoded_bytes:
                        raise AssertionError(
                            "latent variant byte preview disagrees with committed content"
                        )
                stats.transfer_corrupted += 1
            if plan.source_confidences.size == plan.size:
                source_confidence = float(plan.source_confidences[row])
            else:
                source_row = int(plan.source_copy_ids[row]) - 1
                source_confidence = (
                    float(self.arena.confidence[source_row])
                    if 0 <= source_row < self.arena.size
                    else 0.5
                )
            confidence = float(
                np.clip(
                    source_confidence * (1.0 - self.cfg.information.receiver_noise),
                    0.0,
                    1.0,
                )
            )
            if bool(plan.corrupted[row]):
                local_outcome = self.catalog.outcome_vector[content_id - 1].copy()
            elif plan.source_outcome_vectors.shape == (plan.size, OUTCOME_WIDTH):
                local_outcome = plan.source_outcome_vectors[row].copy()
            else:
                source_row = int(plan.source_copy_ids[row]) - 1
                local_outcome = (
                    self.arena.outcome_mean[source_row].copy()
                    if 0 <= source_row < self.arena.size
                    else self.catalog.outcome_vector[content_id - 1].copy()
                )
            self.arena.append(
                holder_subject_id=receiver_subject,
                content_id=content_id,
                source_subject_id=int(plan.sender_subject_ids[row]),
                confidence=confidence,
                sample_count=0,
                created_tick=plan.tick,
                last_verified_tick=(0 if self.kcfg.learning_enabled else plan.tick),
                encoded_bytes=encoded_bytes,
                outcome_mean=local_outcome,
                acquisition_kind=ACQUISITION_TRANSFER,
            )
            stats.transfer_committed += 1
            stats.transfer_committed_bytes += int(storage_encoded_bytes)
            committed_senders.append(sender)
            committed_receivers.append(receiver)
            committed_contents.append(int(content_id))
            committed_roots.append(int(self.root_content_id(content_id)))
            committed_bytes.append(int(storage_encoded_bytes))
            sender_lineage = (
                int(lineage_subject_ids[sender]) if lineage_subject_ids is not None else 0
            )
            receiver_lineage = (
                int(lineage_subject_ids[receiver]) if lineage_subject_ids is not None else 0
            )
            if sender_lineage and receiver_lineage:
                if sender_lineage == receiver_lineage:
                    stats.transfer_same_lineage_committed += 1
                else:
                    stats.transfer_cross_lineage_committed += 1
            else:
                stats.transfer_unknown_lineage_committed += 1
            sender_group = int(group_ids[sender]) if group_ids is not None else 0
            receiver_group = int(group_ids[receiver]) if group_ids is not None else 0
            if sender_group and receiver_group:
                if sender_group == receiver_group:
                    stats.transfer_same_group_committed += 1
                else:
                    stats.transfer_cross_group_committed += 1
            else:
                stats.transfer_unknown_group_committed += 1
            record(
                row,
                "committed-corrupted" if bool(plan.corrupted[row]) else "committed",
                committed_content_id=content_id,
                sender_cost_charged=send_cost,
                receiver_cost_charged=receive_cost,
            )
        self.last_transfer_plan = plan
        self.last_transfer_commit_audit = KnowledgeTransferCommitAudit(
            tick=int(plan.tick),
            sender_entity_indices=np.asarray(committed_senders, dtype=np.int32),
            receiver_entity_indices=np.asarray(committed_receivers, dtype=np.int32),
            committed_content_ids=np.asarray(committed_contents, dtype=np.uint64),
            committed_root_ids=np.asarray(committed_roots, dtype=np.uint64),
            committed_bytes=np.asarray(committed_bytes, dtype=np.uint32),
        )
        if plan.size:
            self._write_event(
                {
                    "tick": plan.tick,
                    "type": "transfer-summary",
                    "attempts": stats.transfer_attempts,
                    "attention_rejected": stats.attention_rejected,
                    "delivered": stats.transfer_delivered,
                    "lost": stats.transfer_lost,
                    "corrupted": stats.transfer_corrupted,
                    "committed": stats.transfer_committed,
                    "duplicate_rejected": stats.transfer_duplicate_rejected,
                    "capacity_rejected": stats.transfer_capacity_rejected,
                    "energy_rejected": stats.transfer_energy_rejected,
                    "sender_energy": stats.sender_energy,
                    "receiver_energy": stats.receiver_energy,
                }
            )
        return stats

    def commit_outcomes(
        self,
        plan: KnowledgeOutcomePlan,
        *,
        energy: np.ndarray,
        alive: np.ndarray,
        knowledge_capacities: np.ndarray | None = None,
    ) -> KnowledgeStepStats:
        """Update local copy statistics from committed current-tick outcomes.

        Matching and capacity rules are content-neutral.  The method never
        chooses actions and never exposes a scalar reward; it only updates the
        holder's local multi-dimensional consequence statistics.
        """
        stats = KnowledgeStepStats(
            outcome_records=plan.size,
            outcome_success=int(
                np.count_nonzero(plan.statuses == OUTCOME_STATUS_SUCCESS)
            ),
            outcome_failed=int(
                np.count_nonzero(plan.statuses == OUTCOME_STATUS_FAILED)
            ),
            outcome_partial=int(
                np.count_nonzero(plan.statuses == OUTCOME_STATUS_PARTIAL)
            ),
        )
        self.last_outcome_plan = plan
        if not self.kcfg.enabled or not self.kcfg.learning_enabled or plan.size == 0:
            return stats
        plan.validate(alive.size)
        capacities = (
            np.full(alive.shape, int(self.kcfg.holder_capacity_bytes), dtype=np.int64)
            if knowledge_capacities is None
            else np.asarray(knowledge_capacities, dtype=np.int64)
        )
        if capacities.shape != alive.shape or np.any(capacities < 0):
            raise ValueError("knowledge capacities must align with entity state")

        # Build one canonical index for this tick.  The hot path remains SoA;
        # no per-copy Python object graph is stored between ticks.
        match_index: dict[tuple[int, int, int], list[int]] = {}
        active_rows = np.flatnonzero(self.arena.active[: self.arena.size])
        if active_rows.size:
            content_rows = self.arena.content_id[active_rows].astype(np.int64) - 1
            order = np.argsort(self.arena.copy_id[active_rows], kind="stable")
            for row, content_row in zip(
                active_rows[order], content_rows[order], strict=True
            ):
                if (
                    int(self.arena.acquisition_kind[row]) == ACQUISITION_TRANSFER
                    and int(self.arena.created_tick[row]) >= plan.tick
                ):
                    # A copy received during this same commit cannot validate
                    # itself using the action that caused its receipt.
                    continue
                key = (
                    int(self.arena.holder_subject_id[row]),
                    int(self.catalog.context_key[content_row]),
                    int(self.catalog.action_id[content_row]),
                )
                match_index.setdefault(key, []).append(int(row))

        def record(
            plan_row: int,
            *,
            update_kind: str,
            copy_row: int,
            sample_before: int,
            confidence_before: float,
        ) -> None:
            if self._outcome_writer is None:
                return
            outcome = plan.outcome_vectors[plan_row]
            self._outcome_writer.writerow(
                {
                    "tick": plan.tick,
                    "entity_id": int(plan.entity_ids[plan_row]),
                    "holder_subject_id": int(plan.holder_subject_ids[plan_row]),
                    "context_key": int(plan.context_keys[plan_row]),
                    "action_id": int(plan.action_ids[plan_row]),
                    "status": int(plan.statuses[plan_row]),
                    "failure_reason": int(plan.failure_reasons[plan_row]),
                    "update_kind": update_kind,
                    "copy_id": int(self.arena.copy_id[copy_row]),
                    "content_id": int(self.arena.content_id[copy_row]),
                    "sample_count_before": sample_before,
                    "sample_count_after": int(self.arena.sample_count[copy_row]),
                    "confidence_before": confidence_before,
                    "confidence_after": float(self.arena.confidence[copy_row]),
                    "energy_delta": float(outcome[OUTCOME_ENERGY]),
                    "integrity_delta": float(outcome[OUTCOME_INTEGRITY]),
                    "material_delta": float(outcome[OUTCOME_MATERIAL]),
                    "information_delta": float(outcome[OUTCOME_INFORMATION]),
                    "reproduction_opportunity_delta": float(
                        outcome[OUTCOME_REPRODUCTION_OPPORTUNITY]
                    ),
                }
            )

        canonical = np.lexsort((plan.entity_ids, plan.holder_subject_ids))
        verification_cost = float(self.kcfg.verification_energy_cost)
        for plan_row in canonical:
            carrier = int(plan.carrier_indices[plan_row])
            if not bool(alive[carrier]):
                continue
            holder = int(plan.holder_subject_ids[plan_row])
            context = int(plan.context_keys[plan_row])
            action = int(plan.action_ids[plan_row])
            outcome = np.asarray(plan.outcome_vectors[plan_row], dtype=np.float32)
            key = (holder, context, action)
            matches = match_index.get(key, ())
            if matches:
                selected = list(matches[: self.kcfg.max_updates_per_outcome])
                stats.learning_match_limit_skipped += max(
                    len(matches) - len(selected), 0
                )
                for copy_row in selected:
                    if float(energy[carrier]) + 1e-12 < verification_cost:
                        stats.learning_energy_rejected += 1
                        continue
                    if verification_cost:
                        energy[carrier] = np.float32(
                            float(energy[carrier]) - verification_cost
                        )
                        stats.learning_energy += verification_cost
                    sample_before = int(self.arena.sample_count[copy_row])
                    confidence_before = float(self.arena.confidence[copy_row])
                    mean_before = self.arena.outcome_mean[copy_row].copy()
                    next_sample = sample_before + 1
                    delta = outcome - mean_before
                    mean_after = mean_before + delta / np.float32(next_sample)
                    m2_after = (
                        self.arena.outcome_m2[copy_row]
                        + delta * (outcome - mean_after)
                    )
                    self.arena.outcome_mean[copy_row] = mean_after.astype(
                        np.float32, copy=False
                    )
                    self.arena.outcome_m2[copy_row] = np.maximum(
                        m2_after, 0.0
                    ).astype(np.float32, copy=False)
                    self.arena.sample_count[copy_row] = np.uint32(next_sample)
                    self.arena.confidence[copy_row] = np.float32(
                        confidence_before
                        + self.kcfg.confidence_learning_rate
                        * (1.0 - confidence_before)
                    )
                    was_unverified_transfer = (
                        int(self.arena.acquisition_kind[copy_row])
                        == ACQUISITION_TRANSFER
                        and int(self.arena.last_verified_tick[copy_row]) == 0
                    )
                    self.arena.last_verified_tick[copy_row] = np.uint64(plan.tick)
                    stats.outcome_updates += 1
                    if (
                        int(self.arena.acquisition_kind[copy_row])
                        == ACQUISITION_PRIVATE_EXPERIENCE
                    ):
                        stats.private_experience_updates += 1
                    if was_unverified_transfer:
                        stats.transferred_copies_verified += 1
                    if self.kcfg.candidate_tracking_enabled:
                        self.candidates.record_verification(
                            content_id=int(self.arena.content_id[copy_row]),
                            holder_subject_id=holder,
                            cost=verification_cost,
                            transferred_copy_verified=was_unverified_transfer,
                            tick=plan.tick,
                        )
                    record(
                        int(plan_row),
                        update_kind=(
                            "verify-transfer"
                            if was_unverified_transfer
                            else "update-copy"
                        ),
                        copy_row=copy_row,
                        sample_before=sample_before,
                        confidence_before=confidence_before,
                    )
                continue

            stats.outcome_unmatched += 1
            if not self.kcfg.experience_creation_enabled:
                continue
            encoded_bytes = self._encoded_bytes_for_new_content(
                parent_content_id=0,
                context_key=context,
                action_id=action,
                source_subject_id=holder,
            )
            holder_capacity = int(capacities[carrier])
            if encoded_bytes > holder_capacity:
                stats.learning_capacity_rejected += 1
                continue
            held_bytes = self.arena.holder_bytes(holder)
            required = max(
                held_bytes + encoded_bytes - holder_capacity, 0
            )
            if required and self.kcfg.experience_creation_requires_free_capacity:
                stats.learning_capacity_rejected += 1
                continue
            if required:
                stats.evicted_capacity += self.arena.evict_oldest(holder, required)
            if self.arena.holder_bytes(holder) + encoded_bytes > holder_capacity:
                stats.learning_capacity_rejected += 1
                continue
            if float(energy[carrier]) + 1e-12 < verification_cost:
                stats.learning_energy_rejected += 1
                continue
            if verification_cost:
                energy[carrier] = np.float32(
                    float(energy[carrier]) - verification_cost
                )
                stats.learning_energy += verification_cost
            content_id = self.catalog.append(
                parent_content_id=0,
                context_key=context,
                action_id=action,
                outcome_vector=outcome,
                encoded_bytes=encoded_bytes,
                created_tick=plan.tick,
                source_subject_id=holder,
            )
            if self.latent_store is not None:
                self.latent_store.ensure_catalog(self.catalog)
                encoded_bytes = int(self.catalog.encoded_bytes[content_id - 1])
            if self.kcfg.candidate_tracking_enabled:
                self.candidates.ensure_catalog(self.catalog)
            copy_id = self.arena.append(
                holder_subject_id=holder,
                content_id=content_id,
                source_subject_id=holder,
                confidence=self.kcfg.initial_experience_confidence,
                sample_count=1,
                created_tick=plan.tick,
                last_verified_tick=plan.tick,
                encoded_bytes=encoded_bytes,
                outcome_mean=outcome,
                acquisition_kind=ACQUISITION_PRIVATE_EXPERIENCE,
            )
            copy_row = copy_id - 1
            match_index.setdefault(key, []).append(copy_row)
            stats.outcome_updates += 1
            stats.private_experiences_created += 1
            if self.kcfg.candidate_tracking_enabled:
                self.candidates.record_verification(
                    content_id=content_id,
                    holder_subject_id=holder,
                    cost=verification_cost,
                    transferred_copy_verified=False,
                    tick=plan.tick,
                )
            record(
                int(plan_row),
                update_kind="create-private",
                copy_row=copy_row,
                sample_before=0,
                confidence_before=0.0,
            )

        self._write_event(
            {
                "tick": plan.tick,
                "type": "outcome-summary",
                "schema": self.kcfg.outcome_schema,
                "records": stats.outcome_records,
                "success": stats.outcome_success,
                "failed": stats.outcome_failed,
                "partial": stats.outcome_partial,
                "updates": stats.outcome_updates,
                "private_created": stats.private_experiences_created,
                "private_updates": stats.private_experience_updates,
                "transferred_verified": stats.transferred_copies_verified,
                "unmatched": stats.outcome_unmatched,
                "energy_rejected": stats.learning_energy_rejected,
                "capacity_rejected": stats.learning_capacity_rejected,
                "verification_energy": stats.learning_energy,
                "outcome_sum": np.asarray(
                    plan.outcome_vectors, dtype=np.float64
                ).sum(axis=0).tolist(),
            }
        )
        return stats

    def remove_dead_holders(
        self, alive: np.ndarray, primary_subject_ids: np.ndarray
    ) -> int:
        if not self.kcfg.enabled or self.arena.active_count == 0:
            return 0
        living_subjects = set(int(value) for value in primary_subject_ids[alive])
        rows = np.flatnonzero(self.arena.active[: self.arena.size])
        remove = [
            int(row)
            for row in rows
            if int(self.arena.holder_subject_id[row]) not in living_subjects
        ]
        return self.arena.deactivate(remove)




    def publish(self, tick: int) -> KnowledgeObservationPlan:
        if self.latent_store is not None:
            self.latent_store.ensure_catalog(self.catalog)
        self.observation = self.arena.publish(self.catalog, tick)
        return self.observation

    def update_candidates(
        self,
        *,
        tick: int,
        alive: np.ndarray,
        primary_subject_ids: np.ndarray,
        lineage_subject_ids: np.ndarray,
        group_ids: np.ndarray,
        x: np.ndarray,
        y: np.ndarray,
        world_width: float,
        world_height: float,
        energy: np.ndarray,
        integrity: np.ndarray,
        harvested_material: np.ndarray,
        information_store: np.ndarray,
        fertility: np.ndarray,
        reproduction_threshold: float,
    ) -> Any:
        """Publish one K4 diagnostic snapshot after all world commits."""
        return self.candidates.observe(
            catalog=self.catalog,
            arena=self.arena,
            tick=tick,
            alive=alive,
            primary_subject_ids=primary_subject_ids,
            lineage_subject_ids=lineage_subject_ids,
            group_ids=group_ids,
            x=x,
            y=y,
            world_width=world_width,
            world_height=world_height,
            energy=energy,
            integrity=integrity,
            harvested_material=harvested_material,
            information_store=information_store,
            fertility=fertility,
            reproduction_threshold=reproduction_threshold,
        )









__all__ = ["KnowledgeSystem"]
