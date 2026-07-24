"""K4 knowledge-content candidate subject diagnostics.

The tracker is deliberately observational.  It reads already committed K1-K3
state at an explicit low-frequency boundary and never feeds values back into
policy, conflict resolution, or world commits.  Scores are reported as
separate diagnostic components; no scalar "subjecthood truth" is produced.
"""

from __future__ import annotations

from dataclasses import dataclass
import copy
import csv
import json
from pathlib import Path
from typing import Any

import numpy as np

from .config import KnowledgeConfig

CANDIDATE_SCHEMA = "knowledge-subject-candidate-v1"
GRAPH_SCHEMA = "candidate-subject-graph-v1"
KNOWLEDGE_SUBJECT_NAMESPACE = 2_000_000_000
OUTCOME_WIDTH = 5


@dataclass(frozen=True)
class KnowledgeCandidateGraphPlan:
    """Immutable low-frequency knowledge-content graph snapshot."""

    tick: int
    content_ids: np.ndarray
    knowledge_subject_ids: np.ndarray
    parent_content_ids: np.ndarray
    root_content_ids: np.ndarray
    variant_depths: np.ndarray
    active_copy_counts: np.ndarray
    current_unique_holder_counts: np.ndarray

    @classmethod
    def empty(cls, tick: int = 0) -> "KnowledgeCandidateGraphPlan":
        return cls(
            tick=int(tick),
            content_ids=np.empty(0, dtype=np.uint64),
            knowledge_subject_ids=np.empty(0, dtype=np.uint64),
            parent_content_ids=np.empty(0, dtype=np.uint64),
            root_content_ids=np.empty(0, dtype=np.uint64),
            variant_depths=np.empty(0, dtype=np.uint16),
            active_copy_counts=np.empty(0, dtype=np.uint32),
            current_unique_holder_counts=np.empty(0, dtype=np.uint32),
        )

    @property
    def size(self) -> int:
        return int(self.content_ids.size)


class KnowledgeCandidateTracker:
    """Cumulative K4 diagnostics over append-only contents and dynamic copies."""

    def __init__(self, config: KnowledgeConfig, output_dir: str | Path) -> None:
        self.config = config
        self.enabled = bool(config.candidate_tracking_enabled)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self._capacity = 64
        self._size = 0
        self.root_content_id = np.zeros(self._capacity, dtype=np.uint64)
        self.variant_depth = np.zeros(self._capacity, dtype=np.uint16)
        self.first_seen_tick = np.zeros(self._capacity, dtype=np.uint64)
        self.last_seen_tick = np.zeros(self._capacity, dtype=np.uint64)
        self.active_copy_count = np.zeros(self._capacity, dtype=np.uint32)
        self.total_copy_count = np.zeros(self._capacity, dtype=np.uint64)
        self.current_unique_holder_count = np.zeros(self._capacity, dtype=np.uint32)
        self.cumulative_unique_holder_count = np.zeros(self._capacity, dtype=np.uint32)
        self.current_verified_copy_count = np.zeros(self._capacity, dtype=np.uint32)
        self.current_verified_transfer_copy_count = np.zeros(self._capacity, dtype=np.uint32)
        self.current_unique_group_count = np.zeros(self._capacity, dtype=np.uint32)
        self.current_unique_lineage_count = np.zeros(self._capacity, dtype=np.uint32)
        self.current_unique_region_count = np.zeros(self._capacity, dtype=np.uint32)
        self.descendant_variant_count = np.zeros(self._capacity, dtype=np.uint32)
        self.transfer_attempt_count = np.zeros(self._capacity, dtype=np.uint64)
        self.transfer_commit_count = np.zeros(self._capacity, dtype=np.uint64)
        self.transfer_verified_count = np.zeros(self._capacity, dtype=np.uint64)
        self.sender_cost = np.zeros(self._capacity, dtype=np.float64)
        self.receiver_cost = np.zeros(self._capacity, dtype=np.float64)
        self.maintenance_cost = np.zeros(self._capacity, dtype=np.float64)
        self.verification_cost = np.zeros(self._capacity, dtype=np.float64)
        self.routing_cost = np.zeros(self._capacity, dtype=np.float64)
        self.policy_influence_events = np.zeros(self._capacity, dtype=np.uint64)
        self.policy_changed_action_events = np.zeros(self._capacity, dtype=np.uint64)
        self.policy_residual_abs_sum = np.zeros(self._capacity, dtype=np.float64)
        self.holder_state_mean = np.full((self._capacity, OUTCOME_WIDTH), np.nan, dtype=np.float64)
        self.nonholder_state_mean = np.full((self._capacity, OUTCOME_WIDTH), np.nan, dtype=np.float64)
        self.holder_state_count = np.zeros(self._capacity, dtype=np.uint32)
        self.nonholder_state_count = np.zeros(self._capacity, dtype=np.uint32)
        # Boundary counters: same, cross, unknown for group/lineage/region.
        self.group_flow = np.zeros((self._capacity, 3), dtype=np.uint64)
        self.lineage_flow = np.zeros((self._capacity, 3), dtype=np.uint64)
        self.region_flow = np.zeros((self._capacity, 3), dtype=np.uint64)
        self.group_commit_flow = np.zeros((self._capacity, 3), dtype=np.uint64)
        self.lineage_commit_flow = np.zeros((self._capacity, 3), dtype=np.uint64)
        self.region_commit_flow = np.zeros((self._capacity, 3), dtype=np.uint64)
        self._ever_holder_pairs: set[tuple[int, int]] = set()
        self._ever_holder_count: dict[int, int] = {}
        self._current_holder_pairs: set[tuple[int, int]] = set()
        # edge value: [count, amount, last_tick]
        self._edges: dict[tuple[str, int, int, int], list[float]] = {}
        self.last_plan = KnowledgeCandidateGraphPlan.empty(0)
        self.last_update_tick = -1
        self._candidate_file = None
        self._candidate_writer = None
        self._boundary_file = None
        self._boundary_writer = None
        if self.enabled:
            self._open_streams()

    def _open_streams(self) -> None:
        self._candidate_file = (self.output_dir / "knowledge_subject_candidates.csv").open(
            "w", newline="", encoding="utf-8"
        )
        candidate_fields = [
            "tick", "schema", "candidate_subject_id", "content_id", "parent_content_id",
            "root_content_id", "variant_depth", "active", "first_seen_tick",
            "last_seen_tick", "persistence_ticks", "persistence_fraction",
            "active_copy_count", "total_copy_count", "surviving_copy_fraction",
            "current_unique_holder_count", "cumulative_unique_holder_count",
            "current_verified_copy_count", "current_verified_transfer_copy_count",
            "transfer_attempt_count", "transfer_commit_count", "effective_replication_rate",
            "descendant_variant_count", "current_unique_group_count",
            "current_unique_lineage_count", "current_unique_region_count",
            "sender_cost", "receiver_cost", "maintenance_cost", "verification_cost",
            "routing_cost", "host_cost_total", "holder_state_count", "nonholder_state_count",
            "holder_energy_mean", "nonholder_energy_mean", "energy_association",
            "holder_integrity_mean", "nonholder_integrity_mean", "integrity_association",
            "holder_material_mean", "nonholder_material_mean", "material_association",
            "holder_information_mean", "nonholder_information_mean", "information_association",
            "holder_reproduction_mean", "nonholder_reproduction_mean", "reproduction_association",
            "host_outcome_association_valid", "policy_influence_events",
            "policy_changed_action_events", "policy_residual_abs_sum",
            "group_internal_commits", "group_cross_commits", "group_unknown_commits",
            "boundary_cohesion", "boundary_cohesion_denominator",
            "boundary_cohesion_valid", "autonomy_caution_flag",
        ]
        self._candidate_writer = csv.DictWriter(self._candidate_file, fieldnames=candidate_fields)
        self._candidate_writer.writeheader()
        self._boundary_file = (self.output_dir / "knowledge_boundary_flows.csv").open(
            "w", newline="", encoding="utf-8"
        )
        boundary_fields = [
            "tick", "content_id", "candidate_subject_id", "dimension",
            "attempt_same", "attempt_cross", "attempt_unknown",
            "commit_same", "commit_cross", "commit_unknown",
            "cohesion", "denominator", "valid",
        ]
        self._boundary_writer = csv.DictWriter(self._boundary_file, fieldnames=boundary_fields)
        self._boundary_writer.writeheader()

    def clone(self, output_dir: str | Path) -> "KnowledgeCandidateTracker":
        result = object.__new__(KnowledgeCandidateTracker)
        for name, value in self.__dict__.items():
            if name in {
                "output_dir", "_candidate_file", "_candidate_writer",
                "_boundary_file", "_boundary_writer",
            }:
                continue
            setattr(result, name, copy.deepcopy(value))
        result.output_dir = Path(output_dir)
        result.output_dir.mkdir(parents=True, exist_ok=True)
        result._candidate_file = None
        result._candidate_writer = None
        result._boundary_file = None
        result._boundary_writer = None
        if result.enabled:
            result._open_streams()
        return result

    def snapshot_state(self) -> dict[str, Any]:
        """Return writer-free K4 state suitable for a trusted checkpoint."""
        excluded = {
            "output_dir", "_candidate_file", "_candidate_writer",
            "_boundary_file", "_boundary_writer",
        }
        return {
            name: copy.deepcopy(value)
            for name, value in self.__dict__.items()
            if name not in excluded
        }

    def restore_state(self, state: dict[str, Any]) -> None:
        """Replace diagnostic state while retaining this run's output streams."""
        for name, value in state.items():
            setattr(self, name, copy.deepcopy(value))


    def _ensure_capacity(self, required: int) -> None:
        if required <= self._capacity:
            self._size = max(self._size, required)
            return
        new_capacity = self._capacity
        while new_capacity < required:
            new_capacity *= 2
        vector_names = (
            "root_content_id", "variant_depth", "first_seen_tick", "last_seen_tick",
            "active_copy_count", "total_copy_count", "current_unique_holder_count",
            "cumulative_unique_holder_count", "current_verified_copy_count",
            "current_verified_transfer_copy_count", "current_unique_group_count",
            "current_unique_lineage_count", "current_unique_region_count",
            "descendant_variant_count", "transfer_attempt_count", "transfer_commit_count",
            "transfer_verified_count", "sender_cost", "receiver_cost", "maintenance_cost",
            "verification_cost", "routing_cost", "policy_influence_events", "policy_changed_action_events",
            "policy_residual_abs_sum", "holder_state_count", "nonholder_state_count",
        )
        for name in vector_names:
            value = getattr(self, name)
            expanded = np.zeros(new_capacity, dtype=value.dtype)
            expanded[: self._size] = value[: self._size]
            setattr(self, name, expanded)
        for name in ("holder_state_mean", "nonholder_state_mean"):
            value = getattr(self, name)
            expanded = np.full((new_capacity, OUTCOME_WIDTH), np.nan, dtype=value.dtype)
            expanded[: self._size] = value[: self._size]
            setattr(self, name, expanded)
        for name in ("group_flow", "lineage_flow", "region_flow", "group_commit_flow", "lineage_commit_flow", "region_commit_flow"):
            value = getattr(self, name)
            expanded = np.zeros((new_capacity, 3), dtype=value.dtype)
            expanded[: self._size] = value[: self._size]
            setattr(self, name, expanded)
        self._capacity = new_capacity
        self._size = required

    @staticmethod
    def subject_id(content_id: int) -> int:
        return KNOWLEDGE_SUBJECT_NAMESPACE + int(content_id)

    def ensure_catalog(self, catalog: Any) -> None:
        if not self.enabled:
            return
        size = int(catalog.size)
        old_size = self._size
        self._ensure_capacity(size)
        for row in range(old_size, size):
            content_id = int(catalog.content_id[row])
            parent = int(catalog.parent_content_id[row])
            self.first_seen_tick[row] = np.uint64(catalog.created_tick[row])
            self.last_seen_tick[row] = np.uint64(catalog.created_tick[row])
            if parent == 0:
                self.root_content_id[row] = np.uint64(content_id)
                self.variant_depth[row] = np.uint16(0)
            else:
                parent_row = parent - 1
                self.root_content_id[row] = self.root_content_id[parent_row]
                self.variant_depth[row] = np.uint16(int(self.variant_depth[parent_row]) + 1)
                self.descendant_variant_count[parent_row] += np.uint32(1)
                self._add_edge("variant_of", content_id, self.subject_id(content_id), self.subject_id(parent), 1.0, int(catalog.created_tick[row]))

    def _add_edge(
        self,
        edge_type: str,
        content_id: int,
        source_subject_id: int,
        target_subject_id: int,
        amount: float,
        tick: int,
    ) -> None:
        key = (edge_type, int(content_id), int(source_subject_id), int(target_subject_id))
        value = self._edges.setdefault(key, [0.0, 0.0, float(tick)])
        value[0] += 1.0
        value[1] += float(amount)
        value[2] = float(tick)

    @staticmethod
    def _boundary_bucket(left: int, right: int) -> int:
        if left <= 0 or right <= 0:
            return 2
        return 0 if left == right else 1

    def record_transfer(
        self,
        *,
        catalog: Any,
        tick: int,
        source_content_id: int,
        committed_content_id: int,
        sender_subject_id: int,
        receiver_subject_id: int,
        status: str,
        sender_cost: float,
        receiver_cost: float,
        sender_group: int = 0,
        receiver_group: int = 0,
        sender_lineage: int = 0,
        receiver_lineage: int = 0,
        sender_region: int = 0,
        receiver_region: int = 0,
    ) -> None:
        if not self.enabled:
            return
        self.ensure_catalog(catalog)
        source_row = int(source_content_id) - 1
        self.transfer_attempt_count[source_row] += np.uint64(1)
        self.sender_cost[source_row] += float(sender_cost)
        group_bucket = self._boundary_bucket(sender_group, receiver_group)
        lineage_bucket = self._boundary_bucket(sender_lineage, receiver_lineage)
        region_bucket = self._boundary_bucket(sender_region, receiver_region)
        self.group_flow[source_row, group_bucket] += np.uint64(1)
        self.lineage_flow[source_row, lineage_bucket] += np.uint64(1)
        self.region_flow[source_row, region_bucket] += np.uint64(1)
        committed = status.startswith("committed")
        if committed:
            row = int(committed_content_id) - 1
            self.transfer_commit_count[row] += np.uint64(1)
            self.receiver_cost[row] += float(receiver_cost)
            self.group_commit_flow[row, group_bucket] += np.uint64(1)
            self.lineage_commit_flow[row, lineage_bucket] += np.uint64(1)
            self.region_commit_flow[row, region_bucket] += np.uint64(1)
            self._add_edge(
                "transferred_to", committed_content_id,
                self.subject_id(committed_content_id), receiver_subject_id, 0.0, tick,
            )
        if sender_cost:
            self._add_edge(
                "cost_attributed_to", source_content_id,
                self.subject_id(source_content_id), sender_subject_id, sender_cost, tick,
            )
        if receiver_cost and committed:
            self._add_edge(
                "cost_attributed_to", committed_content_id,
                self.subject_id(committed_content_id), receiver_subject_id, receiver_cost, tick,
            )

    def record_maintenance(
        self,
        *,
        content_ids: np.ndarray,
        holder_subject_id: int,
        encoded_bytes: np.ndarray,
        charged: float,
        tick: int,
    ) -> None:
        if not self.enabled or charged <= 0.0 or np.asarray(content_ids).size == 0:
            return
        ids = np.asarray(content_ids, dtype=np.uint64)
        weights = np.asarray(encoded_bytes, dtype=np.float64)
        denominator = float(weights.sum())
        if denominator <= 0.0:
            return
        for content_id, amount in zip(ids.tolist(), charged * weights / denominator, strict=True):
            row = int(content_id) - 1
            self.maintenance_cost[row] += float(amount)
            self._add_edge(
                "cost_attributed_to", int(content_id), self.subject_id(int(content_id)),
                int(holder_subject_id), float(amount), int(tick),
            )

    def record_verification(
        self,
        *,
        content_id: int,
        holder_subject_id: int,
        cost: float,
        transferred_copy_verified: bool,
        tick: int,
    ) -> None:
        if not self.enabled:
            return
        row = int(content_id) - 1
        self.verification_cost[row] += float(cost)
        if transferred_copy_verified:
            self.transfer_verified_count[row] += np.uint64(1)
        if cost:
            self._add_edge(
                "cost_attributed_to", int(content_id), self.subject_id(int(content_id)),
                int(holder_subject_id), float(cost), int(tick),
            )

    def record_routing_cost(self, *, observation: Any, result: Any) -> None:
        if not self.enabled or np.asarray(result.active_rows).size == 0:
            return
        copy_holders = np.repeat(
            observation.holder_subject_ids,
            observation.holder_counts.astype(np.int64, copy=False),
        )
        for result_row in range(result.active_rows.size):
            charged = float(result.committed_energy[result_row])
            if charged <= 0.0:
                continue
            holder = int(result.holder_subject_ids[result_row])
            # Routing considers copies matching the current holder/context.
            # Allocate the host computation cost by encoded bytes so the
            # content-level attribution sums exactly to the world charge.
            plan_mask = result.plan.holder_subject_ids == holder
            contexts = np.unique(result.plan.context_keys[plan_mask])
            mask = copy_holders == holder
            if contexts.size:
                mask &= np.isin(observation.context_keys, contexts)
            rows = np.flatnonzero(mask)
            if rows.size == 0:
                continue
            content_ids = observation.content_ids[rows].astype(np.uint64)
            weights = observation.encoded_bytes[rows].astype(np.float64)
            unique, inverse = np.unique(content_ids, return_inverse=True)
            content_weights = np.bincount(inverse, weights=weights, minlength=unique.size)
            total = float(content_weights.sum())
            if total <= 0.0:
                content_weights = np.ones(unique.size, dtype=np.float64)
                total = float(unique.size)
            for content_id, weight in zip(unique.tolist(), content_weights.tolist(), strict=True):
                row = int(content_id) - 1
                amount = charged * float(weight) / total
                self.routing_cost[row] += amount
                self._add_edge(
                    "routing_cost_attributed_to", int(content_id),
                    self.subject_id(int(content_id)), holder, amount,
                    int(result.plan.tick),
                )

    def record_policy_plan(
        self,
        *,
        observation: Any,
        plan: Any,
        changed_active_rows: np.ndarray,
        acquisition_transfer: int,
    ) -> None:
        if not self.enabled or int(getattr(plan, "size", 0)) == 0:
            return
        copy_holders = np.repeat(
            observation.holder_subject_ids,
            observation.holder_counts.astype(np.int64, copy=False),
        )
        changed = set(int(value) for value in np.asarray(changed_active_rows, dtype=np.int32).tolist())
        for plan_row in range(plan.size):
            holder = int(plan.holder_subject_ids[plan_row])
            context = int(plan.context_keys[plan_row])
            action = int(plan.action_ids[plan_row])
            mask = (
                (copy_holders == holder)
                & (observation.context_keys == context)
                & (observation.action_ids == action)
            )
            rows = np.flatnonzero(mask)
            if rows.size == 0:
                continue
            sample = observation.sample_counts[rows].astype(np.float64)
            confidence = observation.confidences[rows].astype(np.float64)
            local = sample >= float(self.config.policy_min_local_samples)
            evidence = sample / (sample + max(float(self.config.policy_sample_saturation), 1e-12))
            unverified_transfer = (
                (observation.acquisition_kinds[rows] == int(acquisition_transfer)) & ~local
            )
            evidence = np.where(
                local,
                evidence,
                np.where(unverified_transfer, float(self.config.policy_unverified_transfer_weight), 0.0),
            )
            reliability = confidence * evidence
            keep = reliability > 0.0
            rows = rows[keep]
            reliability = reliability[keep]
            if rows.size == 0:
                continue
            content_ids = observation.content_ids[rows].astype(np.uint64)
            unique, inverse = np.unique(content_ids, return_inverse=True)
            content_weight = np.bincount(inverse, weights=reliability, minlength=unique.size)
            total = float(content_weight.sum())
            if total <= 0.0:
                continue
            changed_action = int(plan.active_rows[plan_row]) in changed
            residual_abs = abs(float(plan.residuals[plan_row]))
            for content_id, weight in zip(unique.tolist(), content_weight.tolist(), strict=True):
                row = int(content_id) - 1
                share = float(weight) / total
                self.policy_influence_events[row] += np.uint64(1)
                self.policy_residual_abs_sum[row] += residual_abs * share
                if changed_action:
                    self.policy_changed_action_events[row] += np.uint64(1)
                self._add_edge(
                    "policy_influence", int(content_id), self.subject_id(int(content_id)),
                    holder, residual_abs * share, int(plan.tick),
                )

    def _write_boundary_rows(self, tick: int, content_ids: np.ndarray) -> None:
        if self._boundary_writer is None:
            return
        for content_id in content_ids.tolist():
            row = int(content_id) - 1
            for dimension, attempts, commits in (
                ("group", self.group_flow[row], self.group_commit_flow[row]),
                ("lineage", self.lineage_flow[row], self.lineage_commit_flow[row]),
                ("region", self.region_flow[row], self.region_commit_flow[row]),
            ):
                denominator = int(commits[0] + commits[1])
                cohesion = float(commits[0] / denominator) if denominator else float("nan")
                self._boundary_writer.writerow(
                    {
                        "tick": int(tick),
                        "content_id": int(content_id),
                        "candidate_subject_id": self.subject_id(int(content_id)),
                        "dimension": dimension,
                        "attempt_same": int(attempts[0]),
                        "attempt_cross": int(attempts[1]),
                        "attempt_unknown": int(attempts[2]),
                        "commit_same": int(commits[0]),
                        "commit_cross": int(commits[1]),
                        "commit_unknown": int(commits[2]),
                        "cohesion": cohesion,
                        "denominator": denominator,
                        "valid": int(denominator > 0),
                    }
                )

    def observe(
        self,
        *,
        catalog: Any,
        arena: Any,
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
    ) -> KnowledgeCandidateGraphPlan:
        if not self.enabled:
            return KnowledgeCandidateGraphPlan.empty(tick)
        self.ensure_catalog(catalog)
        size = int(catalog.size)
        if size == 0:
            self.last_plan = KnowledgeCandidateGraphPlan.empty(tick)
            self.last_update_tick = int(tick)
            return self.last_plan
        active_rows = np.flatnonzero(arena.active[: arena.size]).astype(np.int64)
        all_content = arena.content_id[: arena.size].astype(np.int64, copy=False)
        total_counts = np.bincount(all_content, minlength=size + 1)[1:]
        active_content = arena.content_id[active_rows].astype(np.int64, copy=False)
        active_counts = np.bincount(active_content, minlength=size + 1)[1:]
        self.total_copy_count[:size] = total_counts.astype(np.uint64, copy=False)
        self.active_copy_count[:size] = active_counts.astype(np.uint32, copy=False)
        self.current_unique_holder_count[:size] = 0
        self.current_verified_copy_count[:size] = 0
        self.current_verified_transfer_copy_count[:size] = 0
        self.current_unique_group_count[:size] = 0
        self.current_unique_lineage_count[:size] = 0
        self.current_unique_region_count[:size] = 0
        self.holder_state_mean[:size] = np.nan
        self.nonholder_state_mean[:size] = np.nan
        self.holder_state_count[:size] = 0
        self.nonholder_state_count[:size] = 0

        living_slots = np.flatnonzero(np.asarray(alive, dtype=bool)).astype(np.int32)
        living_subjects = primary_subject_ids[living_slots].astype(np.uint64)
        subject_order = np.argsort(living_subjects, kind="stable")
        sorted_subjects = living_subjects[subject_order]
        sorted_slots = living_slots[subject_order]
        reproduction = np.minimum(
            np.clip(energy[living_slots] / max(float(reproduction_threshold), 1e-12), 0.0, 1.0),
            np.clip(fertility[living_slots] / 0.5, 0.0, 1.0),
        )
        living_state = np.column_stack(
            (
                energy[living_slots], integrity[living_slots], harvested_material[living_slots],
                information_store[living_slots], reproduction,
            )
        ).astype(np.float64, copy=False)
        global_sum = living_state.sum(axis=0, dtype=np.float64) if living_slots.size else np.zeros(OUTCOME_WIDTH)

        region_x = max(int(self.config.candidate_region_grid_x), 1)
        region_y = max(int(self.config.candidate_region_grid_y), 1)
        living_region = (
            np.minimum((x[living_slots] / float(world_width) * region_x).astype(np.int32), region_x - 1)
            + region_x * np.minimum((y[living_slots] / float(world_height) * region_y).astype(np.int32), region_y - 1)
            + 1
        ) if living_slots.size else np.empty(0, dtype=np.int32)

        self._current_holder_pairs = set()
        if active_rows.size:
            pairs = np.column_stack((active_content, arena.holder_subject_id[active_rows].astype(np.int64)))
            pairs = np.unique(pairs, axis=0)
            for content_value, holder_value in pairs.tolist():
                pair = (int(content_value), int(holder_value))
                self._current_holder_pairs.add(pair)
                if pair not in self._ever_holder_pairs:
                    self._ever_holder_pairs.add(pair)
                    self._ever_holder_count[pair[0]] = (
                        self._ever_holder_count.get(pair[0], 0) + 1
                    )
            pair_content = pairs[:, 0].astype(np.int64)
            pair_holder = pairs[:, 1].astype(np.uint64)
            positions = np.searchsorted(sorted_subjects, pair_holder)
            valid = (positions < sorted_subjects.size)
            safe = np.minimum(positions, max(sorted_subjects.size - 1, 0))
            valid &= sorted_subjects[safe] == pair_holder
            pair_slots = np.full(pair_holder.size, -1, dtype=np.int32)
            if np.any(valid):
                pair_slots[valid] = sorted_slots[positions[valid]]
            starts = np.r_[0, np.flatnonzero(pair_content[1:] != pair_content[:-1]) + 1]
            ends = np.r_[starts[1:], pair_content.size]
            for start, end in zip(starts.tolist(), ends.tolist(), strict=True):
                content_id = int(pair_content[start])
                row = content_id - 1
                holders = pair_holder[start:end]
                slots = pair_slots[start:end]
                slots = slots[slots >= 0]
                self.current_unique_holder_count[row] = np.uint32(holders.size)
                self.cumulative_unique_holder_count[row] = np.uint32(
                    self._ever_holder_count.get(content_id, 0)
                )
                self.last_seen_tick[row] = np.uint64(tick)
                for holder in holders.tolist():
                    self._add_edge("held_by", content_id, self.subject_id(content_id), int(holder), 0.0, tick)
                if slots.size:
                    holder_rows = np.searchsorted(living_slots, np.sort(slots))
                    # living_slots is sorted; holder_rows maps to living_state.
                    state = living_state[holder_rows]
                    holder_sum = state.sum(axis=0, dtype=np.float64)
                    holder_count = int(state.shape[0])
                    nonholder_count = int(living_slots.size - holder_count)
                    self.holder_state_mean[row] = holder_sum / max(holder_count, 1)
                    self.holder_state_count[row] = np.uint32(holder_count)
                    if nonholder_count > 0:
                        self.nonholder_state_mean[row] = (global_sum - holder_sum) / nonholder_count
                        self.nonholder_state_count[row] = np.uint32(nonholder_count)
                    self.current_unique_group_count[row] = np.uint32(np.unique(group_ids[slots][group_ids[slots] != 0]).size)
                    self.current_unique_lineage_count[row] = np.uint32(np.unique(lineage_subject_ids[slots][lineage_subject_ids[slots] != 0]).size)
                    region_positions = np.searchsorted(living_slots, slots)
                    self.current_unique_region_count[row] = np.uint32(np.unique(living_region[region_positions]).size)
            verified = arena.sample_count[active_rows] > 0
            verified_counts = np.bincount(active_content[verified], minlength=size + 1)[1:]
            self.current_verified_copy_count[:size] = verified_counts.astype(np.uint32, copy=False)
            transferred_verified = verified & (arena.acquisition_kind[active_rows] == 2)
            transferred_counts = np.bincount(active_content[transferred_verified], minlength=size + 1)[1:]
            self.current_verified_transfer_copy_count[:size] = transferred_counts.astype(np.uint32, copy=False)

        content_ids = catalog.content_id[:size].astype(np.uint64, copy=True)
        plan = KnowledgeCandidateGraphPlan(
            tick=int(tick),
            content_ids=content_ids,
            knowledge_subject_ids=(content_ids + np.uint64(KNOWLEDGE_SUBJECT_NAMESPACE)),
            parent_content_ids=catalog.parent_content_id[:size].astype(np.uint64, copy=True),
            root_content_ids=self.root_content_id[:size].copy(),
            variant_depths=self.variant_depth[:size].copy(),
            active_copy_counts=self.active_copy_count[:size].copy(),
            current_unique_holder_counts=self.current_unique_holder_count[:size].copy(),
        )
        self.last_plan = plan
        self.last_update_tick = int(tick)
        self._write_candidate_rows(catalog, tick)
        self._write_boundary_rows(tick, content_ids)
        return plan

    def _write_candidate_rows(self, catalog: Any, tick: int) -> None:
        if self._candidate_writer is None:
            return
        for row in range(int(catalog.size)):
            content_id = int(catalog.content_id[row])
            active = int(self.active_copy_count[row] > 0)
            persistence_ticks = int(self.last_seen_tick[row]) - int(self.first_seen_tick[row]) + 1
            total_copies = int(self.total_copy_count[row])
            active_copies = int(self.active_copy_count[row])
            surviving = active_copies / total_copies if total_copies else 0.0
            commits = int(self.transfer_commit_count[row])
            effective = int(self.current_verified_transfer_copy_count[row]) / commits if commits else 0.0
            holder_mean = self.holder_state_mean[row]
            nonholder_mean = self.nonholder_state_mean[row]
            association_valid = bool(np.all(np.isfinite(holder_mean)) and np.all(np.isfinite(nonholder_mean)))
            association = holder_mean - nonholder_mean if association_valid else np.full(OUTCOME_WIDTH, np.nan)
            group_commits = self.group_commit_flow[row]
            denominator = int(group_commits[0] + group_commits[1])
            cohesion = float(group_commits[0] / denominator) if denominator else float("nan")
            costs = (
                self.sender_cost[row] + self.receiver_cost[row]
                + self.maintenance_cost[row] + self.verification_cost[row]
                + self.routing_cost[row]
            )
            self._candidate_writer.writerow(
                {
                    "tick": int(tick), "schema": CANDIDATE_SCHEMA,
                    "candidate_subject_id": self.subject_id(content_id), "content_id": content_id,
                    "parent_content_id": int(catalog.parent_content_id[row]),
                    "root_content_id": int(self.root_content_id[row]),
                    "variant_depth": int(self.variant_depth[row]), "active": active,
                    "first_seen_tick": int(self.first_seen_tick[row]),
                    "last_seen_tick": int(self.last_seen_tick[row]),
                    "persistence_ticks": persistence_ticks,
                    "persistence_fraction": persistence_ticks / max(int(tick) + 1, 1),
                    "active_copy_count": active_copies, "total_copy_count": total_copies,
                    "surviving_copy_fraction": surviving,
                    "current_unique_holder_count": int(self.current_unique_holder_count[row]),
                    "cumulative_unique_holder_count": int(self.cumulative_unique_holder_count[row]),
                    "current_verified_copy_count": int(self.current_verified_copy_count[row]),
                    "current_verified_transfer_copy_count": int(self.current_verified_transfer_copy_count[row]),
                    "transfer_attempt_count": int(self.transfer_attempt_count[row]),
                    "transfer_commit_count": commits, "effective_replication_rate": effective,
                    "descendant_variant_count": int(self.descendant_variant_count[row]),
                    "current_unique_group_count": int(self.current_unique_group_count[row]),
                    "current_unique_lineage_count": int(self.current_unique_lineage_count[row]),
                    "current_unique_region_count": int(self.current_unique_region_count[row]),
                    "sender_cost": float(self.sender_cost[row]),
                    "receiver_cost": float(self.receiver_cost[row]),
                    "maintenance_cost": float(self.maintenance_cost[row]),
                    "verification_cost": float(self.verification_cost[row]),
                    "routing_cost": float(self.routing_cost[row]),
                    "host_cost_total": float(costs),
                    "holder_state_count": int(self.holder_state_count[row]),
                    "nonholder_state_count": int(self.nonholder_state_count[row]),
                    "holder_energy_mean": float(holder_mean[0]), "nonholder_energy_mean": float(nonholder_mean[0]), "energy_association": float(association[0]),
                    "holder_integrity_mean": float(holder_mean[1]), "nonholder_integrity_mean": float(nonholder_mean[1]), "integrity_association": float(association[1]),
                    "holder_material_mean": float(holder_mean[2]), "nonholder_material_mean": float(nonholder_mean[2]), "material_association": float(association[2]),
                    "holder_information_mean": float(holder_mean[3]), "nonholder_information_mean": float(nonholder_mean[3]), "information_association": float(association[3]),
                    "holder_reproduction_mean": float(holder_mean[4]), "nonholder_reproduction_mean": float(nonholder_mean[4]), "reproduction_association": float(association[4]),
                    "host_outcome_association_valid": int(association_valid),
                    "policy_influence_events": int(self.policy_influence_events[row]),
                    "policy_changed_action_events": int(self.policy_changed_action_events[row]),
                    "policy_residual_abs_sum": float(self.policy_residual_abs_sum[row]),
                    "group_internal_commits": int(group_commits[0]),
                    "group_cross_commits": int(group_commits[1]),
                    "group_unknown_commits": int(group_commits[2]),
                    "boundary_cohesion": cohesion,
                    "boundary_cohesion_denominator": denominator,
                    "boundary_cohesion_valid": int(denominator > 0),
                    "autonomy_caution_flag": 1,
                }
            )

    def summary(self) -> dict[str, int | float | str | bool]:
        if not self.enabled:
            return {
                "candidate_tracking_enabled": False,
                "candidate_schema": None,
                "candidate_graph_schema": None,
            }
        size = self._size
        active = self.active_copy_count[:size] > 0
        group_commits = self.group_commit_flow[:size]
        denominator = int(group_commits[:, 0].sum() + group_commits[:, 1].sum()) if size else 0
        return {
            "candidate_tracking_enabled": True,
            "candidate_schema": CANDIDATE_SCHEMA,
            "candidate_graph_schema": GRAPH_SCHEMA,
            "knowledge_candidate_count": int(size),
            "knowledge_candidate_active_count": int(np.count_nonzero(active)),
            "knowledge_candidate_inactive_count": int(size - np.count_nonzero(active)),
            "knowledge_candidate_root_count": int(np.count_nonzero(self.variant_depth[:size] == 0)),
            "knowledge_candidate_variant_count": int(np.count_nonzero(self.variant_depth[:size] > 0)),
            "knowledge_candidate_multi_holder_count": int(np.count_nonzero(self.current_unique_holder_count[:size] > 1)),
            "knowledge_candidate_policy_influence_events": int(self.policy_influence_events[:size].sum(dtype=np.uint64)),
            "knowledge_candidate_policy_changed_actions": int(self.policy_changed_action_events[:size].sum(dtype=np.uint64)),
            "knowledge_candidate_host_cost_total": float(
                self.sender_cost[:size].sum() + self.receiver_cost[:size].sum()
                + self.maintenance_cost[:size].sum() + self.verification_cost[:size].sum()
                + self.routing_cost[:size].sum()
            ),
            "knowledge_candidate_routing_cost_total": float(self.routing_cost[:size].sum()),
            "knowledge_boundary_group_internal_commits": int(group_commits[:, 0].sum()) if size else 0,
            "knowledge_boundary_group_cross_commits": int(group_commits[:, 1].sum()) if size else 0,
            "knowledge_boundary_group_unknown_commits": int(group_commits[:, 2].sum()) if size else 0,
            "knowledge_boundary_group_cohesion": (
                float(group_commits[:, 0].sum() / denominator) if denominator else float("nan")
            ),
            "knowledge_boundary_group_cohesion_valid": bool(denominator > 0),
            "knowledge_candidate_autonomy_caution": True,
            "knowledge_candidate_last_update_tick": int(self.last_update_tick),
        }

    def validate(self, catalog: Any, arena: Any) -> None:
        if not self.enabled:
            return
        if self._size != int(catalog.size):
            raise AssertionError("knowledge candidate catalog size is stale")
        if self._size and (
            np.any(self.root_content_id[: self._size] == 0)
            or np.any(self.last_seen_tick[: self._size] < self.first_seen_tick[: self._size])
            or np.any(~np.isfinite(self.sender_cost[: self._size]))
            or np.any(~np.isfinite(self.receiver_cost[: self._size]))
            or np.any(~np.isfinite(self.maintenance_cost[: self._size]))
            or np.any(~np.isfinite(self.verification_cost[: self._size]))
            or np.any(~np.isfinite(self.routing_cost[: self._size]))
        ):
            raise AssertionError("knowledge candidate diagnostic invariant failed")
        active_counts = np.bincount(
            arena.content_id[np.flatnonzero(arena.active[: arena.size])].astype(np.int64),
            minlength=self._size + 1,
        )[1:]
        if self.last_update_tick >= 0 and np.any(active_counts != self.active_copy_count[: self._size]):
            # The tracker may intentionally be stale between configured update periods.
            if self.last_update_tick == int(getattr(arena, "last_candidate_update_tick", -2)):
                raise AssertionError("knowledge candidate active-copy snapshot is inconsistent")

    def checkpoint_arrays(self) -> dict[str, np.ndarray]:
        if not self.enabled:
            return {}
        size = self._size
        return {
            "knowledge_candidate_root_content_id": self.root_content_id[:size].copy(),
            "knowledge_candidate_variant_depth": self.variant_depth[:size].copy(),
            "knowledge_candidate_first_seen_tick": self.first_seen_tick[:size].copy(),
            "knowledge_candidate_last_seen_tick": self.last_seen_tick[:size].copy(),
            "knowledge_candidate_transfer_attempt_count": self.transfer_attempt_count[:size].copy(),
            "knowledge_candidate_transfer_commit_count": self.transfer_commit_count[:size].copy(),
            "knowledge_candidate_transfer_verified_count": self.transfer_verified_count[:size].copy(),
            "knowledge_candidate_sender_cost": self.sender_cost[:size].copy(),
            "knowledge_candidate_receiver_cost": self.receiver_cost[:size].copy(),
            "knowledge_candidate_maintenance_cost": self.maintenance_cost[:size].copy(),
            "knowledge_candidate_verification_cost": self.verification_cost[:size].copy(),
            "knowledge_candidate_routing_cost": self.routing_cost[:size].copy(),
            "knowledge_candidate_policy_influence_events": self.policy_influence_events[:size].copy(),
            "knowledge_candidate_policy_changed_action_events": self.policy_changed_action_events[:size].copy(),
            "knowledge_candidate_policy_residual_abs_sum": self.policy_residual_abs_sum[:size].copy(),
            "knowledge_candidate_group_flow": self.group_flow[:size].copy(),
            "knowledge_candidate_group_commit_flow": self.group_commit_flow[:size].copy(),
            "knowledge_candidate_lineage_flow": self.lineage_flow[:size].copy(),
            "knowledge_candidate_lineage_commit_flow": self.lineage_commit_flow[:size].copy(),
            "knowledge_candidate_region_flow": self.region_flow[:size].copy(),
            "knowledge_candidate_region_commit_flow": self.region_commit_flow[:size].copy(),
        }

    def flush(self) -> None:
        for value in (self._candidate_file, self._boundary_file):
            if value is not None and not value.closed:
                value.flush()

    def close(self, catalog: Any | None = None) -> None:
        if not self.enabled:
            return
        self.flush()
        for value in (self._candidate_file, self._boundary_file):
            if value is not None and not value.closed:
                value.close()
        if catalog is not None:
            self._write_final_files(catalog)

    def _write_final_files(self, catalog: Any) -> None:
        lineage_path = self.output_dir / "knowledge_content_lineage.csv"
        with lineage_path.open("w", newline="", encoding="utf-8") as handle:
            fields = [
                "schema", "content_id", "candidate_subject_id", "parent_content_id",
                "parent_candidate_subject_id", "root_content_id", "root_candidate_subject_id",
                "variant_depth", "created_tick", "source_subject_id", "context_key",
                "action_id", "encoded_bytes", "active_copy_count", "total_copy_count",
                "cumulative_unique_holder_count", "descendant_variant_count",
            ]
            writer = csv.DictWriter(handle, fieldnames=fields)
            writer.writeheader()
            for row in range(int(catalog.size)):
                content_id = int(catalog.content_id[row])
                parent = int(catalog.parent_content_id[row])
                root = int(self.root_content_id[row])
                writer.writerow(
                    {
                        "schema": CANDIDATE_SCHEMA, "content_id": content_id,
                        "candidate_subject_id": self.subject_id(content_id),
                        "parent_content_id": parent,
                        "parent_candidate_subject_id": self.subject_id(parent) if parent else 0,
                        "root_content_id": root, "root_candidate_subject_id": self.subject_id(root),
                        "variant_depth": int(self.variant_depth[row]),
                        "created_tick": int(catalog.created_tick[row]),
                        "source_subject_id": int(catalog.source_subject_id[row]),
                        "context_key": int(catalog.context_key[row]),
                        "action_id": int(catalog.action_id[row]),
                        "encoded_bytes": int(catalog.encoded_bytes[row]),
                        "active_copy_count": int(self.active_copy_count[row]),
                        "total_copy_count": int(self.total_copy_count[row]),
                        "cumulative_unique_holder_count": int(self.cumulative_unique_holder_count[row]),
                        "descendant_variant_count": int(self.descendant_variant_count[row]),
                    }
                )
        edge_path = self.output_dir / "knowledge_subject_edges.csv"
        with edge_path.open("w", newline="", encoding="utf-8") as handle:
            fields = [
                "schema", "edge_type", "content_id", "knowledge_subject_id",
                "source_subject_id", "target_subject_id", "event_count",
                "amount", "last_tick", "currently_held",
            ]
            writer = csv.DictWriter(handle, fieldnames=fields)
            writer.writeheader()
            for key in sorted(self._edges):
                edge_type, content_id, source, target = key
                count, amount, last_tick = self._edges[key]
                writer.writerow(
                    {
                        "schema": GRAPH_SCHEMA, "edge_type": edge_type,
                        "content_id": content_id, "knowledge_subject_id": self.subject_id(content_id),
                        "source_subject_id": source, "target_subject_id": target,
                        "event_count": int(count), "amount": float(amount),
                        "last_tick": int(last_tick),
                        "currently_held": int(
                            edge_type == "held_by" and (content_id, target) in self._current_holder_pairs
                        ),
                    }
                )
        summary = self.summary()
        summary.update(
            {
                "schema": CANDIDATE_SCHEMA,
                "graph_schema": GRAPH_SCHEMA,
                "diagnostic_only": True,
                "subjecthood_truth_claimed": False,
                "host_outcome_association_causal": False,
                "autonomy_caution": (
                    "Knowledge contents have no independent actuator and remain dependent on host copies."
                ),
            }
        )
        def json_safe(value: Any) -> Any:
            if isinstance(value, dict):
                return {key: json_safe(item) for key, item in value.items()}
            if isinstance(value, (list, tuple)):
                return [json_safe(item) for item in value]
            if isinstance(value, (float, np.floating)) and not np.isfinite(value):
                return None
            if isinstance(value, np.generic):
                return value.item()
            return value
        (self.output_dir / "knowledge_candidate_summary.json").write_text(
            json.dumps(json_safe(summary), ensure_ascii=False, indent=2, allow_nan=False),
            encoding="utf-8",
        )


__all__ = [
    "CANDIDATE_SCHEMA",
    "GRAPH_SCHEMA",
    "KnowledgeCandidateGraphPlan",
    "KnowledgeCandidateTracker",
]
