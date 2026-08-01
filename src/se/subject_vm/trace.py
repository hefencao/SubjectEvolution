"""Compact graph-produced tokens and objective event facts for Subject VM.

Stage 3A deliberately stores no persistent node/edge execution path.  The graph
may emit a bounded continuous token through generic readout ports; the runtime
pairs that token with objective post-commit facts.  No value, credit,
eligibility, plasticity, or random draw is introduced here.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

import numpy as np

from .association import select_delayed_association_candidate
from .binding import (
    BINDING_REASON_CODES,
    SubjectVMTargetCandidateBatch,
    bind_modulation_targets,
)
from .config import (
    SUBJECT_VM_MODULATION_TARGET_NAMES,
    SUBJECT_VM_MODULATION_TARGET_WIDTH,
    SubjectVMConfig,
)
from .modulation import (
    MODULATION_REASON_CODES,
    modulation_control_ports,
    objective_fact_vector,
    propose_modulation,
)

TRACE_STORAGE_SCHEMA_V1 = "se-subject-vm-token-event-storage-v1"
TRACE_STORAGE_SCHEMA_V2 = "se-subject-vm-token-event-storage-v2"
TRACE_STORAGE_SCHEMA_V3 = "se-subject-vm-token-event-storage-v3"
TRACE_STORAGE_SCHEMA = "se-subject-vm-token-event-storage-v4"
ACTION_PORT_WIDTH = 8
RESOURCE_DELTA_WIDTH = 4
OBJECTIVE_EVENT_DELTA_NAMES = (
    "energy",
    "integrity",
    "fertility",
    "position_x",
    "position_y",
    "velocity_x",
    "velocity_y",
    "information_store",
    "resource_store_0",
    "resource_store_1",
    "resource_store_2",
    "resource_store_3",
)
OBJECTIVE_EVENT_DELTA_WIDTH = len(OBJECTIVE_EVENT_DELTA_NAMES)


@dataclass(frozen=True)
class SubjectVMThoughtTokenBatch:
    """Transient graph-produced token batch for one activation tick."""

    tick: int
    rows: np.ndarray
    emitted: np.ndarray
    tokens: np.ndarray
    action_potentials: np.ndarray


@dataclass(frozen=True)
class SubjectVMObjectiveEventBatch:
    """Objective world facts aligned to the activation rows for one tick."""

    tick: int
    rows: np.ndarray
    event_ids: np.ndarray
    entity_ids: np.ndarray
    subject_ids: np.ndarray
    action_ids: np.ndarray
    target_subject_ids: np.ndarray
    success: np.ndarray
    failure_reason: np.ndarray
    sampled_probability: np.ndarray
    objective_delta: np.ndarray
    resolution_resource_delta: np.ndarray
    resolution_internal_resource_delta: np.ndarray
    resolution_energy_cost: np.ndarray


@dataclass
class SubjectVMTraceAccounting:
    recorded_events: int = 0
    expired_events: int = 0
    overwritten_events: int = 0
    emitted_tokens: int = 0
    association_requests: int = 0
    association_assignments: int = 0
    association_unassigned_no_request: int = 0
    association_unassigned_zero_query: int = 0
    association_unassigned_no_candidate: int = 0
    association_unassigned_below_threshold: int = 0
    modulation_requests: int = 0
    modulation_proposals: int = 0
    modulation_rejected_no_association: int = 0
    modulation_rejected_missing_history: int = 0
    modulation_rejected_zero_fact_weights: int = 0
    modulation_rejected_zero_fact_contrast: int = 0
    modulation_rejected_zero_target_weights: int = 0
    modulation_rejected_zero_signal: int = 0
    modulation_not_requested: int = 0
    binding_requests: int = 0
    binding_bound_events: int = 0
    binding_bound_targets: int = 0
    binding_rejected_no_modulation: int = 0
    binding_rejected_zero_family: int = 0
    binding_rejected_no_carrier: int = 0
    last_event_tick: int = -1


class SubjectVMTraceStorage:
    """Per-subject bounded ring independent of graph node/edge capacity."""

    def __init__(self, cfg: SubjectVMConfig, entity_capacity: int) -> None:
        if not cfg.trace_enabled:
            raise ValueError("SubjectVMTraceStorage requires Stage-3 trace config")
        self.cfg = cfg
        self.entity_capacity = int(entity_capacity)
        self.capacity = int(cfg.trace.capacity_per_subject)
        self.retention_ticks = int(cfg.trace.retention_ticks)
        self.token_width = int(cfg.trace.token_width)
        e, c, w = self.entity_capacity, self.capacity, self.token_width

        self.write_cursor = np.zeros(e, dtype=np.uint32)
        self.event_count = np.zeros(e, dtype=np.uint32)
        self.event_valid = np.zeros((e, c), dtype=bool)
        self.event_id = np.zeros((e, c), dtype=np.uint64)
        self.event_tick = np.full((e, c), -1, dtype=np.int64)
        self.entity_id = np.zeros((e, c), dtype=np.uint64)
        self.subject_id = np.zeros((e, c), dtype=np.uint64)
        self.action_id = np.full((e, c), -1, dtype=np.int16)
        self.target_subject_id = np.zeros((e, c), dtype=np.uint64)
        self.success = np.zeros((e, c), dtype=bool)
        self.failure_reason = np.zeros((e, c), dtype=np.uint8)
        self.sampled_probability = np.zeros((e, c), dtype=np.float32)
        self.thought_token = np.zeros((e, c, w), dtype=np.float32)
        self.action_potentials = np.zeros(
            (e, c, ACTION_PORT_WIDTH), dtype=np.float32
        )
        self.objective_delta = np.zeros(
            (e, c, OBJECTIVE_EVENT_DELTA_WIDTH), dtype=np.float32
        )
        self.resolution_resource_delta = np.zeros(
            (e, c, RESOURCE_DELTA_WIDTH), dtype=np.float32
        )
        self.resolution_internal_resource_delta = np.zeros(
            (e, c, RESOURCE_DELTA_WIDTH), dtype=np.float32
        )
        self.resolution_energy_cost = np.zeros((e, c), dtype=np.float32)
        self.association_requested = (
            np.zeros((e, c), dtype=bool) if cfg.association_enabled else None
        )
        self.association_assigned = (
            np.zeros((e, c), dtype=bool) if cfg.association_enabled else None
        )
        self.associated_event_id = (
            np.zeros((e, c), dtype=np.uint64) if cfg.association_enabled else None
        )
        self.associated_event_tick = (
            np.full((e, c), -1, dtype=np.int64) if cfg.association_enabled else None
        )
        self.association_delay_ticks = (
            np.zeros((e, c), dtype=np.uint32) if cfg.association_enabled else None
        )
        self.association_similarity = (
            np.zeros((e, c), dtype=np.float32) if cfg.association_enabled else None
        )
        self.modulation_requested = (
            np.zeros((e, c), dtype=bool) if cfg.modulation_enabled else None
        )
        self.modulation_proposed = (
            np.zeros((e, c), dtype=bool) if cfg.modulation_enabled else None
        )
        self.modulation_reason = (
            np.zeros((e, c), dtype=np.uint8) if cfg.modulation_enabled else None
        )
        self.modulation_signal = (
            np.zeros((e, c), dtype=np.float32) if cfg.modulation_enabled else None
        )
        self.modulation_vector = (
            np.zeros((e, c, SUBJECT_VM_MODULATION_TARGET_WIDTH), dtype=np.float32)
            if cfg.modulation_enabled
            else None
        )
        self.binding_requested = (
            np.zeros((e, c), dtype=bool) if cfg.target_binding_enabled else None
        )
        self.binding_bound_any = (
            np.zeros((e, c), dtype=bool) if cfg.target_binding_enabled else None
        )
        self.binding_family_bound = (
            np.zeros((e, c, SUBJECT_VM_MODULATION_TARGET_WIDTH), dtype=bool)
            if cfg.target_binding_enabled
            else None
        )
        self.binding_reason = (
            np.zeros((e, c, SUBJECT_VM_MODULATION_TARGET_WIDTH), dtype=np.uint8)
            if cfg.target_binding_enabled
            else None
        )
        self.binding_target_kind = (
            np.zeros((e, c, SUBJECT_VM_MODULATION_TARGET_WIDTH), dtype=np.uint8)
            if cfg.target_binding_enabled
            else None
        )
        self.binding_target_index = (
            np.full((e, c, SUBJECT_VM_MODULATION_TARGET_WIDTH), -1, dtype=np.int32)
            if cfg.target_binding_enabled
            else None
        )
        self.binding_target_id = (
            np.zeros((e, c, SUBJECT_VM_MODULATION_TARGET_WIDTH), dtype=np.uint32)
            if cfg.target_binding_enabled
            else None
        )
        self.binding_eligibility_value = (
            np.zeros((e, c, SUBJECT_VM_MODULATION_TARGET_WIDTH), dtype=np.float32)
            if cfg.target_binding_enabled
            else None
        )
        self.binding_family_proposal = (
            np.zeros((e, c, SUBJECT_VM_MODULATION_TARGET_WIDTH), dtype=np.float32)
            if cfg.target_binding_enabled
            else None
        )

    @staticmethod
    def base_snapshot_array_names() -> tuple[str, ...]:
        return (
            "write_cursor",
            "event_count",
            "event_valid",
            "event_id",
            "event_tick",
            "entity_id",
            "subject_id",
            "action_id",
            "target_subject_id",
            "success",
            "failure_reason",
            "sampled_probability",
            "thought_token",
            "action_potentials",
            "objective_delta",
            "resolution_resource_delta",
            "resolution_internal_resource_delta",
            "resolution_energy_cost",
        )

    @staticmethod
    def association_snapshot_array_names() -> tuple[str, ...]:
        return (
            "association_requested",
            "association_assigned",
            "associated_event_id",
            "associated_event_tick",
            "association_delay_ticks",
            "association_similarity",
        )

    @staticmethod
    def modulation_snapshot_array_names() -> tuple[str, ...]:
        return (
            "modulation_requested",
            "modulation_proposed",
            "modulation_reason",
            "modulation_signal",
            "modulation_vector",
        )

    @staticmethod
    def binding_snapshot_array_names() -> tuple[str, ...]:
        return (
            "binding_requested",
            "binding_bound_any",
            "binding_family_bound",
            "binding_reason",
            "binding_target_kind",
            "binding_target_index",
            "binding_target_id",
            "binding_eligibility_value",
            "binding_family_proposal",
        )

    def snapshot_array_names(self) -> tuple[str, ...]:
        names = self.base_snapshot_array_names()
        if self.cfg.association_enabled:
            names += self.association_snapshot_array_names()
        if self.cfg.modulation_enabled:
            names += self.modulation_snapshot_array_names()
        if self.cfg.target_binding_enabled:
            names += self.binding_snapshot_array_names()
        return names

    def allocated_nbytes(self) -> int:
        return int(
            sum(getattr(self, name).nbytes for name in self.snapshot_array_names())
        )

    def _rows(self, rows: np.ndarray) -> np.ndarray:
        normalized = np.asarray(rows, dtype=np.int32)
        if normalized.ndim != 1:
            raise ValueError("subject_vm trace rows must be one-dimensional")
        if normalized.size and (
            np.any(normalized < 0)
            or np.any(normalized >= self.entity_capacity)
            or np.unique(normalized).size != normalized.size
        ):
            raise ValueError("subject_vm trace rows must be unique in-capacity indices")
        return normalized

    def clear_rows(self, rows: np.ndarray) -> None:
        rows = self._rows(rows)
        if rows.size == 0:
            return
        for name in self.snapshot_array_names():
            array = getattr(self, name)
            if name in {"event_tick", "action_id", "associated_event_tick"}:
                array[rows] = -1
            else:
                array[rows] = 0

    initialize_rows = clear_rows

    def move_rows(self, source_rows: np.ndarray, destination_rows: np.ndarray) -> None:
        sources = self._rows(source_rows)
        destinations = self._rows(destination_rows)
        if sources.shape != destinations.shape:
            raise ValueError("subject_vm trace compaction rows must match")
        if sources.size == 0:
            return
        if np.intersect1d(sources, destinations).size:
            raise ValueError("subject_vm trace compaction rows must be disjoint")
        for name in self.snapshot_array_names():
            array = getattr(self, name)
            array[destinations] = array[sources]
        self.clear_rows(sources)

    def _clear_slot(self, row: int, slot: int) -> None:
        self.event_valid[row, slot] = False
        self.event_id[row, slot] = 0
        self.event_tick[row, slot] = -1
        self.entity_id[row, slot] = 0
        self.subject_id[row, slot] = 0
        self.action_id[row, slot] = -1
        self.target_subject_id[row, slot] = 0
        self.success[row, slot] = False
        self.failure_reason[row, slot] = 0
        self.sampled_probability[row, slot] = 0.0
        self.thought_token[row, slot] = 0.0
        self.action_potentials[row, slot] = 0.0
        self.objective_delta[row, slot] = 0.0
        self.resolution_resource_delta[row, slot] = 0.0
        self.resolution_internal_resource_delta[row, slot] = 0.0
        self.resolution_energy_cost[row, slot] = 0.0
        if self.cfg.association_enabled:
            assert self.association_requested is not None
            assert self.association_assigned is not None
            assert self.associated_event_id is not None
            assert self.associated_event_tick is not None
            assert self.association_delay_ticks is not None
            assert self.association_similarity is not None
            self.association_requested[row, slot] = False
            self.association_assigned[row, slot] = False
            self.associated_event_id[row, slot] = 0
            self.associated_event_tick[row, slot] = -1
            self.association_delay_ticks[row, slot] = 0
            self.association_similarity[row, slot] = 0.0
        if self.cfg.modulation_enabled:
            assert self.modulation_requested is not None
            assert self.modulation_proposed is not None
            assert self.modulation_reason is not None
            assert self.modulation_signal is not None
            assert self.modulation_vector is not None
            self.modulation_requested[row, slot] = False
            self.modulation_proposed[row, slot] = False
            self.modulation_reason[row, slot] = 0
            self.modulation_signal[row, slot] = 0.0
            self.modulation_vector[row, slot] = 0.0
        if self.cfg.target_binding_enabled:
            assert self.binding_requested is not None
            assert self.binding_bound_any is not None
            assert self.binding_family_bound is not None
            assert self.binding_reason is not None
            assert self.binding_target_kind is not None
            assert self.binding_target_index is not None
            assert self.binding_target_id is not None
            assert self.binding_eligibility_value is not None
            assert self.binding_family_proposal is not None
            self.binding_requested[row, slot] = False
            self.binding_bound_any[row, slot] = False
            self.binding_family_bound[row, slot] = False
            self.binding_reason[row, slot] = 0
            self.binding_target_kind[row, slot] = 0
            self.binding_target_index[row, slot] = -1
            self.binding_target_id[row, slot] = 0
            self.binding_eligibility_value[row, slot] = 0.0
            self.binding_family_proposal[row, slot] = 0.0

    def expire(self, tick: int) -> int:
        expired = self.event_valid & (
            (int(tick) - self.event_tick) > self.retention_ticks
        )
        rows, slots = np.nonzero(expired)
        for row, slot in zip(rows.tolist(), slots.tolist(), strict=True):
            self._clear_slot(row, slot)
        if rows.size:
            self.event_count = self.event_valid.sum(axis=1, dtype=np.uint32)
        return int(rows.size)

    @staticmethod
    def _validate_event_batch(batch: SubjectVMObjectiveEventBatch) -> int:
        rows = np.asarray(batch.rows)
        if rows.ndim != 1:
            raise ValueError("subject_vm objective event rows must be one-dimensional")
        count = int(rows.size)
        vectors = (
            batch.event_ids,
            batch.entity_ids,
            batch.subject_ids,
            batch.action_ids,
            batch.target_subject_ids,
            batch.success,
            batch.failure_reason,
            batch.sampled_probability,
            batch.resolution_energy_cost,
        )
        if any(np.asarray(value).shape != (count,) for value in vectors):
            raise ValueError("subject_vm objective event vectors must align with rows")
        if np.asarray(batch.objective_delta).shape != (
            count,
            OBJECTIVE_EVENT_DELTA_WIDTH,
        ):
            raise ValueError("subject_vm objective delta has an invalid shape")
        for value in (
            batch.resolution_resource_delta,
            batch.resolution_internal_resource_delta,
        ):
            if np.asarray(value).shape != (count, RESOURCE_DELTA_WIDTH):
                raise ValueError("subject_vm resource delta has an invalid shape")
        return count

    def append(
        self,
        batch: SubjectVMObjectiveEventBatch,
        tokens: SubjectVMThoughtTokenBatch,
        *,
        owner_entity_ids: np.ndarray,
        owner_subject_ids: np.ndarray,
        accounting: SubjectVMTraceAccounting,
        target_candidates: SubjectVMTargetCandidateBatch | None = None,
    ) -> None:
        count = self._validate_event_batch(batch)
        rows = self._rows(batch.rows)
        token_rows = self._rows(tokens.rows)
        if int(batch.tick) != int(tokens.tick) or not np.array_equal(rows, token_rows):
            raise ValueError("subject_vm token/event batches do not align")
        if np.asarray(tokens.emitted).shape != (count,):
            raise ValueError("subject_vm token emitted mask has an invalid shape")
        if np.asarray(tokens.tokens).shape != (count, self.token_width):
            raise ValueError("subject_vm thought token has an invalid shape")
        if np.asarray(tokens.action_potentials).shape != (count, ACTION_PORT_WIDTH):
            raise ValueError("subject_vm action potentials have an invalid shape")
        if self.cfg.target_binding_enabled:
            if target_candidates is None:
                raise ValueError("subject_vm target binding requires pre-activation candidates")
            if int(target_candidates.tick) != int(batch.tick):
                raise ValueError("subject_vm target candidates tick does not align")
            candidate_rows = self._rows(target_candidates.rows)
            if not np.array_equal(candidate_rows, rows):
                raise ValueError("subject_vm target candidates rows do not align")
            expected_shape = (count, SUBJECT_VM_MODULATION_TARGET_WIDTH)
            for value in (
                target_candidates.target_kind,
                target_candidates.target_index,
                target_candidates.target_id,
                target_candidates.eligibility_value,
                target_candidates.eligibility_age,
            ):
                if np.asarray(value).shape != expected_shape:
                    raise ValueError("subject_vm target candidates have an invalid shape")
        elif target_candidates is not None:
            raise ValueError("inactive subject_vm target binding cannot accept candidates")
        if not np.array_equal(owner_entity_ids[rows], batch.entity_ids):
            raise ValueError("subject_vm trace entity ownership is stale")
        if not np.array_equal(owner_subject_ids[rows], batch.subject_ids):
            raise ValueError("subject_vm trace subject ownership is stale")
        finite_values = (
            tokens.tokens,
            tokens.action_potentials,
            batch.objective_delta,
            batch.resolution_resource_delta,
            batch.resolution_internal_resource_delta,
            batch.resolution_energy_cost,
            batch.sampled_probability,
        )
        if any(np.any(~np.isfinite(value)) for value in finite_values):
            raise ValueError("subject_vm token/event values must be finite")

        accounting.expired_events += self.expire(batch.tick)
        emitted = np.asarray(tokens.emitted, dtype=bool)
        for index in np.flatnonzero(emitted).tolist():
            row = int(rows[index])
            slot = int(self.write_cursor[row] % self.capacity)
            association = None
            if self.cfg.association_enabled:
                association = select_delayed_association_candidate(
                    cfg=self.cfg.association,
                    current_tick=int(batch.tick),
                    current_token=np.asarray(tokens.tokens[index], dtype=np.float32),
                    event_valid=self.event_valid[row],
                    event_ids=self.event_id[row],
                    event_ticks=self.event_tick[row],
                    historical_tokens=self.thought_token[row],
                    excluded_slot=slot,
                    excluded_token_ports=(
                        modulation_control_ports(self.cfg.modulation)
                        if self.cfg.modulation_enabled
                        else ()
                    ),
                )
                if association.requested:
                    accounting.association_requests += 1
                else:
                    accounting.association_unassigned_no_request += 1
                if association.assigned:
                    accounting.association_assignments += 1
                elif association.reason in {"zero-query", "zero-candidate"}:
                    accounting.association_unassigned_zero_query += 1
                elif association.reason == "no-candidate":
                    accounting.association_unassigned_no_candidate += 1
                elif association.reason == "below-threshold":
                    accounting.association_unassigned_below_threshold += 1
            modulation = None
            if self.cfg.modulation_enabled:
                assert association is not None
                current_facts = objective_fact_vector(
                    objective_delta=batch.objective_delta[index],
                    resource_delta=batch.resolution_resource_delta[index],
                    internal_resource_delta=batch.resolution_internal_resource_delta[index],
                    energy_cost=float(batch.resolution_energy_cost[index]),
                )
                historical_facts = None
                if association.assigned:
                    matches = np.flatnonzero(
                        self.event_valid[row]
                        & (self.event_id[row] == np.uint64(association.associated_event_id))
                        & (self.event_tick[row] == int(association.associated_event_tick))
                    )
                    if matches.size == 1:
                        historical_slot = int(matches[0])
                        historical_facts = objective_fact_vector(
                            objective_delta=self.objective_delta[row, historical_slot],
                            resource_delta=self.resolution_resource_delta[row, historical_slot],
                            internal_resource_delta=self.resolution_internal_resource_delta[row, historical_slot],
                            energy_cost=float(self.resolution_energy_cost[row, historical_slot]),
                        )
                modulation = propose_modulation(
                    cfg=self.cfg.modulation,
                    current_token=np.asarray(tokens.tokens[index], dtype=np.float32),
                    association=association,
                    current_facts=current_facts,
                    historical_facts=historical_facts,
                )
                if modulation.requested:
                    accounting.modulation_requests += 1
                else:
                    accounting.modulation_not_requested += 1
                if modulation.proposed:
                    accounting.modulation_proposals += 1
                elif modulation.reason == "no-association":
                    accounting.modulation_rejected_no_association += 1
                elif modulation.reason == "missing-historical-event":
                    accounting.modulation_rejected_missing_history += 1
                elif modulation.reason == "zero-fact-weights":
                    accounting.modulation_rejected_zero_fact_weights += 1
                elif modulation.reason == "zero-fact-contrast":
                    accounting.modulation_rejected_zero_fact_contrast += 1
                elif modulation.reason == "zero-target-weights":
                    accounting.modulation_rejected_zero_target_weights += 1
                elif modulation.reason == "zero-signal":
                    accounting.modulation_rejected_zero_signal += 1
            binding = None
            if self.cfg.target_binding_enabled:
                assert modulation is not None and target_candidates is not None
                binding = bind_modulation_targets(
                    modulation=modulation,
                    candidates=target_candidates,
                    candidate_row=index,
                )
                if binding.requested:
                    accounting.binding_requests += 1
                else:
                    accounting.binding_rejected_no_modulation += 1
                if binding.bound_any:
                    accounting.binding_bound_events += 1
                accounting.binding_bound_targets += int(np.count_nonzero(binding.family_bound))
                accounting.binding_rejected_zero_family += int(
                    np.count_nonzero(
                        binding.reason == BINDING_REASON_CODES["zero-family-proposal"]
                    )
                )
                accounting.binding_rejected_no_carrier += int(
                    np.count_nonzero(
                        binding.reason == BINDING_REASON_CODES["no-valid-local-carrier"]
                    )
                )
            if self.event_valid[row, slot]:
                accounting.overwritten_events += 1
            self._clear_slot(row, slot)
            self.event_valid[row, slot] = True
            self.event_id[row, slot] = np.uint64(batch.event_ids[index])
            self.event_tick[row, slot] = int(batch.tick)
            self.entity_id[row, slot] = np.uint64(batch.entity_ids[index])
            self.subject_id[row, slot] = np.uint64(batch.subject_ids[index])
            self.action_id[row, slot] = np.int16(batch.action_ids[index])
            self.target_subject_id[row, slot] = np.uint64(batch.target_subject_ids[index])
            self.success[row, slot] = bool(batch.success[index])
            self.failure_reason[row, slot] = np.uint8(batch.failure_reason[index])
            self.sampled_probability[row, slot] = np.float32(
                batch.sampled_probability[index]
            )
            self.thought_token[row, slot] = np.asarray(
                tokens.tokens[index], dtype=np.float32
            )
            self.action_potentials[row, slot] = np.asarray(
                tokens.action_potentials[index], dtype=np.float32
            )
            self.objective_delta[row, slot] = np.asarray(
                batch.objective_delta[index], dtype=np.float32
            )
            self.resolution_resource_delta[row, slot] = np.asarray(
                batch.resolution_resource_delta[index], dtype=np.float32
            )
            self.resolution_internal_resource_delta[row, slot] = np.asarray(
                batch.resolution_internal_resource_delta[index], dtype=np.float32
            )
            self.resolution_energy_cost[row, slot] = np.float32(
                batch.resolution_energy_cost[index]
            )
            if association is not None:
                assert self.association_requested is not None
                assert self.association_assigned is not None
                assert self.associated_event_id is not None
                assert self.associated_event_tick is not None
                assert self.association_delay_ticks is not None
                assert self.association_similarity is not None
                self.association_requested[row, slot] = association.requested
                self.association_assigned[row, slot] = association.assigned
                self.associated_event_id[row, slot] = np.uint64(
                    association.associated_event_id
                )
                self.associated_event_tick[row, slot] = int(
                    association.associated_event_tick
                )
                self.association_delay_ticks[row, slot] = np.uint32(
                    association.delay_ticks
                )
                self.association_similarity[row, slot] = np.float32(
                    association.similarity
                )
            if modulation is not None:
                assert self.modulation_requested is not None
                assert self.modulation_proposed is not None
                assert self.modulation_reason is not None
                assert self.modulation_signal is not None
                assert self.modulation_vector is not None
                self.modulation_requested[row, slot] = modulation.requested
                self.modulation_proposed[row, slot] = modulation.proposed
                self.modulation_reason[row, slot] = np.uint8(
                    MODULATION_REASON_CODES[modulation.reason]
                )
                self.modulation_signal[row, slot] = np.float32(modulation.signal)
                self.modulation_vector[row, slot] = np.asarray(
                    modulation.vector, dtype=np.float32
                )
            if binding is not None:
                assert self.binding_requested is not None
                assert self.binding_bound_any is not None
                assert self.binding_family_bound is not None
                assert self.binding_reason is not None
                assert self.binding_target_kind is not None
                assert self.binding_target_index is not None
                assert self.binding_target_id is not None
                assert self.binding_eligibility_value is not None
                assert self.binding_family_proposal is not None
                self.binding_requested[row, slot] = binding.requested
                self.binding_bound_any[row, slot] = binding.bound_any
                self.binding_family_bound[row, slot] = binding.family_bound
                self.binding_reason[row, slot] = binding.reason
                self.binding_target_kind[row, slot] = binding.target_kind
                self.binding_target_index[row, slot] = binding.target_index
                self.binding_target_id[row, slot] = binding.target_id
                self.binding_eligibility_value[row, slot] = binding.eligibility_value
                self.binding_family_proposal[row, slot] = binding.family_proposal
            self.write_cursor[row] = np.uint32((slot + 1) % self.capacity)
            self.event_count[row] = np.uint32(np.count_nonzero(self.event_valid[row]))
            accounting.recorded_events += 1
            accounting.emitted_tokens += 1
            accounting.last_event_tick = int(batch.tick)

    def latest_slot(self, row: int) -> int | None:
        if not 0 <= int(row) < self.entity_capacity:
            raise ValueError("subject_vm trace row is outside capacity")
        valid = np.flatnonzero(self.event_valid[int(row)])
        if valid.size == 0:
            return None
        ticks = self.event_tick[int(row), valid]
        return int(valid[int(np.argmax(ticks))])

    def snapshot_state(self) -> dict[str, Any]:
        return {
            "schema": TRACE_STORAGE_SCHEMA,
            "entity_capacity": self.entity_capacity,
            "capacity_per_subject": self.capacity,
            "retention_ticks": self.retention_ticks,
            "token_width": self.token_width,
            "objective_delta_names": list(OBJECTIVE_EVENT_DELTA_NAMES),
            "arrays": {
                name: getattr(self, name).copy() for name in self.snapshot_array_names()
            },
        }

    @classmethod
    def from_snapshot(
        cls, cfg: SubjectVMConfig, entity_capacity: int, payload: dict[str, Any]
    ) -> "SubjectVMTraceStorage":
        schema = payload.get("schema")
        if schema not in {
            TRACE_STORAGE_SCHEMA,
            TRACE_STORAGE_SCHEMA_V3,
            TRACE_STORAGE_SCHEMA_V2,
            TRACE_STORAGE_SCHEMA_V1,
        }:
            raise ValueError("unsupported subject_vm trace snapshot schema")
        result = cls(cfg, entity_capacity)
        expected = (
            result.entity_capacity,
            result.capacity,
            result.retention_ticks,
            result.token_width,
        )
        actual = (
            int(payload.get("entity_capacity", -1)),
            int(payload.get("capacity_per_subject", -1)),
            int(payload.get("retention_ticks", -1)),
            int(payload.get("token_width", -1)),
        )
        if actual != expected:
            raise ValueError("subject_vm trace checkpoint capacity mismatch")
        if tuple(payload.get("objective_delta_names", ())) != OBJECTIVE_EVENT_DELTA_NAMES:
            raise ValueError("subject_vm trace objective delta schema mismatch")
        arrays = payload.get("arrays")
        if not isinstance(arrays, dict):
            raise ValueError("subject_vm trace checkpoint arrays are missing")
        if schema == TRACE_STORAGE_SCHEMA_V1:
            names = result.base_snapshot_array_names()
        elif schema == TRACE_STORAGE_SCHEMA_V2:
            names = result.base_snapshot_array_names()
            if result.cfg.association_enabled:
                names += result.association_snapshot_array_names()
        elif schema == TRACE_STORAGE_SCHEMA_V3:
            names = result.base_snapshot_array_names()
            if result.cfg.association_enabled:
                names += result.association_snapshot_array_names()
            if result.cfg.modulation_enabled:
                names += result.modulation_snapshot_array_names()
        else:
            names = result.snapshot_array_names()
        for name in names:
            if name not in arrays:
                raise ValueError(f"subject_vm trace checkpoint is missing array {name}")
            expected_array = getattr(result, name)
            restored = np.asarray(arrays[name], dtype=expected_array.dtype)
            if restored.shape != expected_array.shape:
                raise ValueError(f"subject_vm trace checkpoint shape mismatch for {name}")
            setattr(result, name, restored.copy())
        return result

    def clone(self) -> "SubjectVMTraceStorage":
        return type(self).from_snapshot(
            self.cfg, self.entity_capacity, self.snapshot_state()
        )

    def diagnostics(self) -> dict[str, Any]:
        return {
            "schema": TRACE_STORAGE_SCHEMA,
            "capacity_per_subject": self.capacity,
            "retention_ticks": self.retention_ticks,
            "token_width": self.token_width,
            "allocated_nbytes": self.allocated_nbytes(),
            "stored_events": int(np.count_nonzero(self.event_valid)),
            "association_enabled": self.cfg.association_enabled,
            "assigned_associations": (
                0
                if self.association_assigned is None
                else int(np.count_nonzero(self.association_assigned))
            ),
            "modulation_enabled": self.cfg.modulation_enabled,
            "proposed_modulations": (
                0
                if self.modulation_proposed is None
                else int(np.count_nonzero(self.modulation_proposed))
            ),
            "modulation_target_names": list(SUBJECT_VM_MODULATION_TARGET_NAMES),
            "target_binding_enabled": self.cfg.target_binding_enabled,
            "bound_target_events": (
                0
                if self.binding_bound_any is None
                else int(np.count_nonzero(self.binding_bound_any))
            ),
            "bound_targets": (
                0
                if self.binding_family_bound is None
                else int(np.count_nonzero(self.binding_family_bound))
            ),
        }


__all__ = [
    "ACTION_PORT_WIDTH",
    "OBJECTIVE_EVENT_DELTA_NAMES",
    "OBJECTIVE_EVENT_DELTA_WIDTH",
    "RESOURCE_DELTA_WIDTH",
    "TRACE_STORAGE_SCHEMA",
    "TRACE_STORAGE_SCHEMA_V1",
    "TRACE_STORAGE_SCHEMA_V2",
    "TRACE_STORAGE_SCHEMA_V3",
    "SubjectVMObjectiveEventBatch",
    "SubjectVMThoughtTokenBatch",
    "SubjectVMTraceAccounting",
    "SubjectVMTraceStorage",
]
