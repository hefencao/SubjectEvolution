"""Dynamic, costly knowledge copies and local consequence learning.

K1 establishes immutable content records, independently degradable holder
copies, explicit transfer plans, capacity arbitration, and auditable physical
costs.  K2 adds current-tick local context-action-outcome statistics and local
verification.  K3 may publish a separately versioned sparse policy residual;
the legacy ``inherited-linear-policy-v1`` coefficients retain their meaning.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import copy
import csv
import json
from pathlib import Path
from typing import Any

import numpy as np

from .backend import backend_from_array
from .config import KnowledgeConfig, SimulationConfig
from .random_api import RandomContext, Stream, bernoulli, uniform01
from .knowledge_subjects import KnowledgeCandidateTracker


OUTCOME_WIDTH = 5
OUTCOME_ENERGY = 0
OUTCOME_INTEGRITY = 1
OUTCOME_MATERIAL = 2
OUTCOME_INFORMATION = 3
OUTCOME_REPRODUCTION_OPPORTUNITY = 4

OUTCOME_STATUS_FAILED = 0
OUTCOME_STATUS_SUCCESS = 1
OUTCOME_STATUS_PARTIAL = 2

ACQUISITION_SEED = 0
ACQUISITION_PRIVATE_EXPERIENCE = 1
ACQUISITION_TRANSFER = 2


def encode_local_context(
    resource: np.ndarray,
    hazard: np.ndarray,
    energy: np.ndarray,
    integrity: np.ndarray,
    grouped: np.ndarray,
    *,
    max_energy: float,
) -> np.ndarray:
    """Encode a small local observation into ``local-context-v1`` keys.

    The bins are deliberately coarse and use only the carrier's current local
    observation.  No future state, global fitness, or population statistic is
    available to this encoder.
    """
    xp = backend_from_array(resource).xp
    resource = xp.asarray(resource, dtype=xp.float32)
    hazard = xp.asarray(hazard, dtype=xp.float32)
    energy = xp.asarray(energy, dtype=xp.float32)
    integrity = xp.asarray(integrity, dtype=xp.float32)
    grouped = xp.asarray(grouped, dtype=bool)
    shape = resource.shape
    if any(value.shape != shape for value in (hazard, energy, integrity, grouped)):
        raise ValueError("local knowledge context inputs must align")
    resource_bin = xp.where(resource < 0.05, 0, xp.where(resource < 0.5, 1, 2))
    hazard_bin = xp.where(hazard < 0.25, 0, xp.where(hazard < 0.6, 1, 2))
    energy_fraction = energy / max(float(max_energy), 1e-12)
    energy_bin = xp.where(energy_fraction < 0.35, 0, xp.where(energy_fraction < 0.7, 1, 2))
    integrity_bin = xp.where(integrity < 0.5, 0, xp.where(integrity < 0.85, 1, 2))
    keys = (
        1
        + resource_bin
        + 3 * hazard_bin
        + 9 * energy_bin
        + 27 * integrity_bin
        + 81 * grouped.astype(xp.int16)
    )
    return keys.astype(xp.uint64, copy=False)


def _readonly(value: np.ndarray, dtype: Any | None = None) -> np.ndarray:
    result = np.asarray(value, dtype=dtype).copy()
    result.setflags(write=False)
    return result


@dataclass(frozen=True)
class KnowledgeObservationPlan:
    """Immutable holder-segmented knowledge snapshot published for one tick."""

    tick: int
    holder_subject_ids: np.ndarray
    holder_starts: np.ndarray
    holder_counts: np.ndarray
    copy_ids: np.ndarray
    content_ids: np.ndarray
    context_keys: np.ndarray
    action_ids: np.ndarray
    outcome_vectors: np.ndarray
    confidences: np.ndarray
    sample_counts: np.ndarray
    acquisition_kinds: np.ndarray
    encoded_bytes: np.ndarray

    @classmethod
    def empty(cls, tick: int = 0) -> "KnowledgeObservationPlan":
        return cls(
            tick=int(tick),
            holder_subject_ids=_readonly(np.empty(0), np.uint64),
            holder_starts=_readonly(np.empty(0), np.int32),
            holder_counts=_readonly(np.empty(0), np.int32),
            copy_ids=_readonly(np.empty(0), np.uint64),
            content_ids=_readonly(np.empty(0), np.uint64),
            context_keys=_readonly(np.empty(0), np.uint64),
            action_ids=_readonly(np.empty(0), np.int16),
            outcome_vectors=_readonly(np.empty((0, OUTCOME_WIDTH)), np.float32),
            confidences=_readonly(np.empty(0), np.float32),
            sample_counts=_readonly(np.empty(0), np.uint32),
            acquisition_kinds=_readonly(np.empty(0), np.uint8),
            encoded_bytes=_readonly(np.empty(0), np.uint32),
        )

    @property
    def copy_count(self) -> int:
        return int(self.copy_ids.size)


@dataclass(frozen=True)
class KnowledgeOutcomePlan:
    """Immutable local action consequence records for one completed commit.

    Outcome coordinates are ordered as energy, integrity, material/resource,
    information, and reproduction opportunity.  The plan contains no scalar
    reward and is generated only from the current tick's observation and
    committed physical state.
    """

    tick: int
    carrier_indices: np.ndarray
    entity_ids: np.ndarray
    holder_subject_ids: np.ndarray
    context_keys: np.ndarray
    action_ids: np.ndarray
    statuses: np.ndarray
    failure_reasons: np.ndarray
    outcome_vectors: np.ndarray

    @classmethod
    def empty(cls, tick: int = 0) -> "KnowledgeOutcomePlan":
        return cls(
            tick=int(tick),
            carrier_indices=np.empty(0, dtype=np.int32),
            entity_ids=np.empty(0, dtype=np.uint64),
            holder_subject_ids=np.empty(0, dtype=np.uint64),
            context_keys=np.empty(0, dtype=np.uint64),
            action_ids=np.empty(0, dtype=np.int16),
            statuses=np.empty(0, dtype=np.uint8),
            failure_reasons=np.empty(0, dtype=np.uint8),
            outcome_vectors=np.empty((0, OUTCOME_WIDTH), dtype=np.float32),
        )

    @property
    def size(self) -> int:
        return int(self.entity_ids.size)

    def validate(self, entity_capacity: int) -> None:
        count = self.size
        vectors = (
            self.carrier_indices,
            self.entity_ids,
            self.holder_subject_ids,
            self.context_keys,
            self.action_ids,
            self.statuses,
            self.failure_reasons,
        )
        if any(np.asarray(value).shape != (count,) for value in vectors):
            raise ValueError("knowledge outcome plan vectors must align")
        if np.asarray(self.outcome_vectors).shape != (count, OUTCOME_WIDTH):
            raise ValueError("knowledge outcome vectors must have width five")
        if self.tick < 0:
            raise ValueError("knowledge outcome tick must be non-negative")
        if count and (
            np.any(self.carrier_indices < 0)
            or np.any(self.carrier_indices >= entity_capacity)
            or np.any(self.entity_ids == 0)
            or np.any(self.holder_subject_ids == 0)
            or np.any(self.context_keys == 0)
            or np.any(self.action_ids < 0)
            or np.any(self.statuses > OUTCOME_STATUS_PARTIAL)
            or np.any(~np.isfinite(self.outcome_vectors))
        ):
            raise ValueError("knowledge outcome plan contains invalid values")


@dataclass(frozen=True)
class KnowledgeTransferPlan:
    """Explicit transfer attempts produced before any knowledge state mutation."""

    tick: int
    sender_entity_indices: np.ndarray
    receiver_entity_indices: np.ndarray
    sender_subject_ids: np.ndarray
    receiver_subject_ids: np.ndarray
    source_subject_ids: np.ndarray
    source_copy_ids: np.ndarray
    content_ids: np.ndarray
    encoded_bytes: np.ndarray
    delivered: np.ndarray
    corrupted: np.ndarray
    source_outcome_vectors: np.ndarray = field(
        default_factory=lambda: np.empty((0, OUTCOME_WIDTH), dtype=np.float32)
    )
    source_confidences: np.ndarray = field(
        default_factory=lambda: np.empty(0, dtype=np.float32)
    )
    source_sample_counts: np.ndarray = field(
        default_factory=lambda: np.empty(0, dtype=np.uint32)
    )
    attention_rejected: int = 0

    @classmethod
    def empty(
        cls, tick: int, attention_rejected: int = 0
    ) -> "KnowledgeTransferPlan":
        return cls(
            tick=int(tick),
            sender_entity_indices=np.empty(0, dtype=np.int32),
            receiver_entity_indices=np.empty(0, dtype=np.int32),
            sender_subject_ids=np.empty(0, dtype=np.uint64),
            receiver_subject_ids=np.empty(0, dtype=np.uint64),
            source_subject_ids=np.empty(0, dtype=np.uint64),
            source_copy_ids=np.empty(0, dtype=np.uint64),
            content_ids=np.empty(0, dtype=np.uint64),
            source_outcome_vectors=np.empty((0, OUTCOME_WIDTH), dtype=np.float32),
            source_confidences=np.empty(0, dtype=np.float32),
            source_sample_counts=np.empty(0, dtype=np.uint32),
            encoded_bytes=np.empty(0, dtype=np.uint32),
            delivered=np.empty(0, dtype=bool),
            corrupted=np.empty(0, dtype=bool),
            attention_rejected=int(attention_rejected),
        )

    @property
    def size(self) -> int:
        return int(self.source_copy_ids.size)

    def validate(self, entity_capacity: int) -> None:
        count = self.size
        vectors = (
            self.sender_entity_indices,
            self.receiver_entity_indices,
            self.sender_subject_ids,
            self.receiver_subject_ids,
            self.source_subject_ids,
            self.source_copy_ids,
            self.content_ids,
            self.encoded_bytes,
            self.delivered,
            self.corrupted,
        )
        if any(np.asarray(value).shape != (count,) for value in vectors):
            raise ValueError("knowledge transfer plan vectors must align")
        legacy_source_state = (
            np.asarray(self.source_outcome_vectors).size == 0
            and np.asarray(self.source_confidences).size == 0
            and np.asarray(self.source_sample_counts).size == 0
        )
        if not legacy_source_state and (
            np.asarray(self.source_outcome_vectors).shape != (count, OUTCOME_WIDTH)
            or np.asarray(self.source_confidences).shape != (count,)
            or np.asarray(self.source_sample_counts).shape != (count,)
        ):
            raise ValueError("knowledge transfer source-state vectors must align")
        if self.tick < 0 or self.attention_rejected < 0:
            raise ValueError("knowledge transfer tick/attention count is invalid")
        if count and (
            np.any(self.sender_entity_indices < 0)
            or np.any(self.sender_entity_indices >= entity_capacity)
            or np.any(self.receiver_entity_indices < 0)
            or np.any(self.receiver_entity_indices >= entity_capacity)
            or np.any(self.sender_subject_ids == 0)
            or np.any(self.receiver_subject_ids == 0)
            or np.any(self.source_copy_ids == 0)
            or np.any(self.content_ids == 0)
            or np.any(self.encoded_bytes == 0)
            or np.any(self.corrupted & ~self.delivered)
            or (
                not legacy_source_state
                and (
                    np.any(~np.isfinite(self.source_outcome_vectors))
                    or np.any(~np.isfinite(self.source_confidences))
                    or np.any(
                        (self.source_confidences < 0.0)
                        | (self.source_confidences > 1.0)
                    )
                )
            )
        ):
            raise ValueError("knowledge transfer plan contains invalid values")


@dataclass
class KnowledgeStepStats:
    maintenance_energy: float = 0.0
    sender_energy: float = 0.0
    receiver_energy: float = 0.0
    transfer_attempts: int = 0
    transfer_delivered: int = 0
    transfer_lost: int = 0
    transfer_corrupted: int = 0
    transfer_committed: int = 0
    transfer_committed_bytes: int = 0
    transfer_same_lineage_committed: int = 0
    transfer_cross_lineage_committed: int = 0
    transfer_unknown_lineage_committed: int = 0
    transfer_same_group_committed: int = 0
    transfer_cross_group_committed: int = 0
    transfer_unknown_group_committed: int = 0
    transfer_duplicate_rejected: int = 0
    transfer_capacity_rejected: int = 0
    transfer_energy_rejected: int = 0
    attention_rejected: int = 0
    forgotten: int = 0
    evicted_capacity: int = 0
    evicted_maintenance: int = 0
    removed_dead_holder: int = 0
    learning_energy: float = 0.0
    outcome_records: int = 0
    outcome_success: int = 0
    outcome_failed: int = 0
    outcome_partial: int = 0
    outcome_updates: int = 0
    private_experiences_created: int = 0
    private_experience_updates: int = 0
    transferred_copies_verified: int = 0
    outcome_unmatched: int = 0
    learning_energy_rejected: int = 0
    learning_capacity_rejected: int = 0
    learning_match_limit_skipped: int = 0
    confidence_decayed: int = 0
    policy_influenced_entities: int = 0
    policy_influenced_actions: int = 0
    policy_support_copies: int = 0
    policy_private_support_copies: int = 0
    policy_transfer_support_copies: int = 0
    policy_unverified_transfer_support_copies: int = 0
    policy_changed_actions: int = 0
    policy_residual_abs_sum: float = 0.0
    policy_latent_dimensions: int = 0
    policy_latent_max_width: int = 0
    policy_quantized_residual_abs_sum: int = 0
    policy_linear_shadow_changed_actions: int = 0
    policy_router_saturation_units: int = 0
    policy_router_clipped_outputs: int = 0
    policy_router_hidden_abs_sum: int = 0
    policy_router_hidden_active_units: int = 0
    routing_requested_energy: float = 0.0
    routing_committed_energy: float = 0.0
    routing_rejected_energy: float = 0.0
    routing_requested_entities: int = 0
    routing_committed_entities: int = 0
    routing_rejected_entities: int = 0
    routing_accepted_actions: int = 0
    routing_rejected_actions: int = 0
    routing_latent_dimensions: int = 0
    routing_mac_count: int = 0
    routing_active_hidden_units: int = 0
    routing_saturation_count: int = 0
    routing_clipped_output_count: int = 0
    routing_cost_induced_action_changes: int = 0
    selection_candidate_copies: int = 0
    selection_selected_copies: int = 0
    selection_requested_top_k_sum: int = 0
    selection_zero_capacity_entities: int = 0
    selection_tie_count: int = 0
    selection_committed_energy: float = 0.0
    working_memory_requested_energy: float = 0.0
    working_memory_committed_energy: float = 0.0
    working_memory_rejected_energy: float = 0.0
    working_memory_requested_entities: int = 0
    working_memory_committed_entities: int = 0
    working_memory_rejected_entities: int = 0
    working_memory_saturation_units: int = 0
    working_memory_active_dimensions: int = 0
    working_memory_induced_action_changes: int = 0

    @property
    def total_energy_cost(self) -> float:
        return (
            self.maintenance_energy
            + self.sender_energy
            + self.receiver_energy
            + self.learning_energy
            + self.routing_committed_energy
            + self.working_memory_committed_energy
        )


class KnowledgeCatalog:
    """Append-only immutable content directory with amortized O(1) growth."""

    def __init__(self, initial_capacity: int = 64) -> None:
        self._size = 0
        self._capacity = max(int(initial_capacity), 1)
        self.content_id = np.zeros(self._capacity, dtype=np.uint64)
        self.parent_content_id = np.zeros(self._capacity, dtype=np.uint64)
        self.context_key = np.zeros(self._capacity, dtype=np.uint64)
        self.action_id = np.zeros(self._capacity, dtype=np.int16)
        self.outcome_vector = np.zeros((self._capacity, OUTCOME_WIDTH), dtype=np.float32)
        self.encoded_bytes = np.zeros(self._capacity, dtype=np.uint32)
        self.created_tick = np.zeros(self._capacity, dtype=np.uint64)
        self.source_subject_id = np.zeros(self._capacity, dtype=np.uint64)
        self.next_content_id = np.uint64(1)

    @property
    def size(self) -> int:
        return self._size

    def _ensure_capacity(self, required: int) -> None:
        if required <= self._capacity:
            return
        new_capacity = self._capacity
        while new_capacity < required:
            new_capacity *= 2
        for name in (
            "content_id",
            "parent_content_id",
            "context_key",
            "action_id",
            "encoded_bytes",
            "created_tick",
            "source_subject_id",
        ):
            value = getattr(self, name)
            expanded = np.zeros(new_capacity, dtype=value.dtype)
            expanded[: self._size] = value[: self._size]
            setattr(self, name, expanded)
        expanded_outcome = np.zeros((new_capacity, OUTCOME_WIDTH), dtype=np.float32)
        expanded_outcome[: self._size] = self.outcome_vector[: self._size]
        self.outcome_vector = expanded_outcome
        self._capacity = new_capacity

    def append(
        self,
        *,
        parent_content_id: int,
        context_key: int,
        action_id: int,
        outcome_vector: np.ndarray,
        encoded_bytes: int,
        created_tick: int,
        source_subject_id: int,
    ) -> int:
        outcome = np.asarray(outcome_vector, dtype=np.float32)
        if outcome.shape != (OUTCOME_WIDTH,) or np.any(~np.isfinite(outcome)):
            raise ValueError("knowledge outcome vector must contain five finite values")
        if encoded_bytes <= 0 or created_tick < 0 or source_subject_id <= 0:
            raise ValueError("knowledge content metadata is invalid")
        self._ensure_capacity(self._size + 1)
        row = self._size
        content_id = int(self.next_content_id)
        self.next_content_id = np.uint64(content_id + 1)
        self.content_id[row] = np.uint64(content_id)
        self.parent_content_id[row] = np.uint64(parent_content_id)
        self.context_key[row] = np.uint64(context_key)
        self.action_id[row] = np.int16(action_id)
        self.outcome_vector[row] = outcome
        self.encoded_bytes[row] = np.uint32(encoded_bytes)
        self.created_tick[row] = np.uint64(created_tick)
        self.source_subject_id[row] = np.uint64(source_subject_id)
        self._size += 1
        return content_id

    def row(self, content_id: int) -> int:
        row = int(content_id) - 1
        if row < 0 or row >= self._size or int(self.content_id[row]) != int(content_id):
            raise KeyError(f"unknown knowledge content id {content_id}")
        return row

    def create_corrupted_variant(
        self,
        content_id: int,
        *,
        tick: int,
        source_subject_id: int,
        run_seed: int,
        outcome_vector: np.ndarray | None = None,
    ) -> int:
        row = self.row(content_id)
        # Damage is explicit but does not invent a scalar utility.  One outcome
        # coordinate receives a bounded perturbation and context/action may be
        # misclassified.  K1/K2 still never consume these fields in policy.
        key = np.asarray([np.uint64(content_id)], dtype=np.uint64)
        ctx = RandomContext(run_seed, tick, phase=93, stream=Stream.KNOWLEDGE_DAMAGE)
        coordinate = int(uniform01(ctx, key, 0)[0] * OUTCOME_WIDTH) % OUTCOME_WIDTH
        delta = float(uniform01(ctx, key, 1)[0] * 0.5 - 0.25)
        outcome = (
            self.outcome_vector[row].copy()
            if outcome_vector is None
            else np.asarray(outcome_vector, dtype=np.float32).copy()
        )
        if outcome.shape != (OUTCOME_WIDTH,) or np.any(~np.isfinite(outcome)):
            raise ValueError("corrupted knowledge source outcome must have width five")
        outcome[coordinate] = np.float32(outcome[coordinate] + delta)
        context_key = int(self.context_key[row])
        if bool(bernoulli(ctx, key, 0.5, 2)[0]):
            context_key ^= int(1 << (int(uniform01(ctx, key, 3)[0] * 31) % 31))
        action_id = int(self.action_id[row])
        if bool(bernoulli(ctx, key, 0.25, 4)[0]):
            action_id = int((action_id + 1 + int(uniform01(ctx, key, 5)[0] * 3)) % 8)
        return self.append(
            parent_content_id=content_id,
            context_key=context_key,
            action_id=action_id,
            outcome_vector=outcome,
            encoded_bytes=int(self.encoded_bytes[row]),
            created_tick=tick,
            source_subject_id=source_subject_id,
        )

    def arrays(self) -> dict[str, np.ndarray]:
        stop = self._size
        return {
            "content_id": self.content_id[:stop],
            "parent_content_id": self.parent_content_id[:stop],
            "context_key": self.context_key[:stop],
            "action_id": self.action_id[:stop],
            "outcome_vector": self.outcome_vector[:stop],
            "encoded_bytes": self.encoded_bytes[:stop],
            "created_tick": self.created_tick[:stop],
            "source_subject_id": self.source_subject_id[:stop],
        }


class KnowledgeArena:
    """Dynamic SoA arena with capacity doubling and independent copy state."""

    def __init__(self, initial_capacity: int = 1024) -> None:
        self._size = 0
        self._capacity = max(int(initial_capacity), 1)
        self.copy_id = np.zeros(self._capacity, dtype=np.uint64)
        self.holder_subject_id = np.zeros(self._capacity, dtype=np.uint64)
        self.content_id = np.zeros(self._capacity, dtype=np.uint64)
        self.source_subject_id = np.zeros(self._capacity, dtype=np.uint64)
        self.confidence = np.zeros(self._capacity, dtype=np.float32)
        self.sample_count = np.zeros(self._capacity, dtype=np.uint32)
        self.outcome_mean = np.zeros((self._capacity, OUTCOME_WIDTH), dtype=np.float32)
        self.outcome_m2 = np.zeros((self._capacity, OUTCOME_WIDTH), dtype=np.float32)
        self.acquisition_kind = np.zeros(self._capacity, dtype=np.uint8)
        self.created_tick = np.zeros(self._capacity, dtype=np.uint64)
        self.last_verified_tick = np.zeros(self._capacity, dtype=np.uint64)
        self.encoded_bytes = np.zeros(self._capacity, dtype=np.uint32)
        self.active = np.zeros(self._capacity, dtype=bool)
        self.next_copy_id = np.uint64(1)
        self._holder_rows: dict[int, list[int]] = {}
        self._index_dirty = False

    @property
    def size(self) -> int:
        return self._size

    @property
    def active_count(self) -> int:
        return int(np.count_nonzero(self.active[: self._size]))

    @property
    def active_bytes(self) -> int:
        stop = self._size
        return int(self.encoded_bytes[:stop][self.active[:stop]].sum(dtype=np.uint64))

    def _ensure_capacity(self, required: int) -> None:
        if required <= self._capacity:
            return
        new_capacity = self._capacity
        while new_capacity < required:
            new_capacity *= 2
        for name in (
            "copy_id",
            "holder_subject_id",
            "content_id",
            "source_subject_id",
            "confidence",
            "sample_count",
            "acquisition_kind",
            "created_tick",
            "last_verified_tick",
            "encoded_bytes",
            "active",
        ):
            value = getattr(self, name)
            expanded = np.zeros(new_capacity, dtype=value.dtype)
            expanded[: self._size] = value[: self._size]
            setattr(self, name, expanded)
        for name in ("outcome_mean", "outcome_m2"):
            value = getattr(self, name)
            expanded = np.zeros((new_capacity, OUTCOME_WIDTH), dtype=value.dtype)
            expanded[: self._size] = value[: self._size]
            setattr(self, name, expanded)
        self._capacity = new_capacity

    def _ensure_index(self) -> None:
        if not self._index_dirty:
            return
        self._holder_rows = {}
        for row in np.flatnonzero(self.active[: self._size]):
            self._holder_rows.setdefault(int(self.holder_subject_id[row]), []).append(int(row))
        self._index_dirty = False

    def rows_for_holder(self, holder_subject_id: int) -> list[int]:
        self._ensure_index()
        return list(self._holder_rows.get(int(holder_subject_id), ()))

    def holder_bytes(self, holder_subject_id: int) -> int:
        rows = self.rows_for_holder(holder_subject_id)
        return int(self.encoded_bytes[rows].sum(dtype=np.uint64)) if rows else 0

    def has_content(self, holder_subject_id: int, content_id: int) -> bool:
        rows = self.rows_for_holder(holder_subject_id)
        return any(int(self.content_id[row]) == int(content_id) for row in rows)

    def append(
        self,
        *,
        holder_subject_id: int,
        content_id: int,
        source_subject_id: int,
        confidence: float,
        sample_count: int,
        created_tick: int,
        last_verified_tick: int,
        encoded_bytes: int,
        outcome_mean: np.ndarray | None = None,
        outcome_m2: np.ndarray | None = None,
        acquisition_kind: int = ACQUISITION_SEED,
    ) -> int:
        if holder_subject_id <= 0 or content_id <= 0 or source_subject_id <= 0:
            raise ValueError("knowledge copy subject/content IDs must be positive")
        if not 0.0 <= confidence <= 1.0 or encoded_bytes <= 0:
            raise ValueError("knowledge copy confidence/size is invalid")
        mean = (
            np.zeros(OUTCOME_WIDTH, dtype=np.float32)
            if outcome_mean is None
            else np.asarray(outcome_mean, dtype=np.float32)
        )
        m2 = (
            np.zeros(OUTCOME_WIDTH, dtype=np.float32)
            if outcome_m2 is None
            else np.asarray(outcome_m2, dtype=np.float32)
        )
        if mean.shape != (OUTCOME_WIDTH,) or m2.shape != (OUTCOME_WIDTH,):
            raise ValueError("knowledge copy outcome statistics must have width five")
        if np.any(~np.isfinite(mean)) or np.any(~np.isfinite(m2)) or np.any(m2 < 0.0):
            raise ValueError("knowledge copy outcome statistics are invalid")
        if acquisition_kind not in {
            ACQUISITION_SEED,
            ACQUISITION_PRIVATE_EXPERIENCE,
            ACQUISITION_TRANSFER,
        }:
            raise ValueError("unknown knowledge acquisition kind")
        self._ensure_capacity(self._size + 1)
        row = self._size
        copy_id = int(self.next_copy_id)
        self.next_copy_id = np.uint64(copy_id + 1)
        self.copy_id[row] = np.uint64(copy_id)
        self.holder_subject_id[row] = np.uint64(holder_subject_id)
        self.content_id[row] = np.uint64(content_id)
        self.source_subject_id[row] = np.uint64(source_subject_id)
        self.confidence[row] = np.float32(confidence)
        self.sample_count[row] = np.uint32(sample_count)
        self.outcome_mean[row] = mean
        self.outcome_m2[row] = m2
        self.acquisition_kind[row] = np.uint8(acquisition_kind)
        self.created_tick[row] = np.uint64(created_tick)
        self.last_verified_tick[row] = np.uint64(last_verified_tick)
        self.encoded_bytes[row] = np.uint32(encoded_bytes)
        self.active[row] = True
        self._size += 1
        if not self._index_dirty:
            self._holder_rows.setdefault(int(holder_subject_id), []).append(row)
        return copy_id

    def deactivate(self, rows: np.ndarray | list[int]) -> int:
        idx = np.asarray(rows, dtype=np.int64)
        if idx.size == 0:
            return 0
        valid = idx[(idx >= 0) & (idx < self._size)]
        live_rows = valid[self.active[valid]]
        count = int(live_rows.size)
        if count and not self._index_dirty:
            by_holder: dict[int, set[int]] = {}
            for row in live_rows:
                by_holder.setdefault(int(self.holder_subject_id[row]), set()).add(int(row))
            for holder, removed in by_holder.items():
                remaining = [
                    row for row in self._holder_rows.get(holder, ()) if row not in removed
                ]
                if remaining:
                    self._holder_rows[holder] = remaining
                else:
                    self._holder_rows.pop(holder, None)
        self.active[live_rows] = False
        return count

    def evict_oldest(self, holder_subject_id: int, bytes_needed: int) -> int:
        """Evict by oldest copy ID only; never inspect content or outcomes."""
        if bytes_needed <= 0:
            return 0
        rows = self.rows_for_holder(holder_subject_id)
        rows.sort(key=lambda row: int(self.copy_id[row]))
        released = 0
        evicted: list[int] = []
        for row in rows:
            released += int(self.encoded_bytes[row])
            evicted.append(row)
            if released >= bytes_needed:
                break
        self.deactivate(evicted)
        return len(evicted)

    def publish(self, catalog: KnowledgeCatalog, tick: int) -> KnowledgeObservationPlan:
        rows = np.flatnonzero(self.active[: self._size])
        if rows.size == 0:
            return KnowledgeObservationPlan.empty(tick)
        order = np.lexsort((self.copy_id[rows], self.holder_subject_id[rows]))
        rows = rows[order]
        holders, starts, counts = np.unique(
            self.holder_subject_id[rows], return_index=True, return_counts=True
        )
        catalog_rows = self.content_id[rows].astype(np.int64) - 1
        return KnowledgeObservationPlan(
            tick=int(tick),
            holder_subject_ids=_readonly(holders, np.uint64),
            holder_starts=_readonly(starts, np.int32),
            holder_counts=_readonly(counts, np.int32),
            copy_ids=_readonly(self.copy_id[rows], np.uint64),
            content_ids=_readonly(self.content_id[rows], np.uint64),
            context_keys=_readonly(catalog.context_key[catalog_rows], np.uint64),
            action_ids=_readonly(catalog.action_id[catalog_rows], np.int16),
            outcome_vectors=_readonly(self.outcome_mean[rows], np.float32),
            confidences=_readonly(self.confidence[rows], np.float32),
            sample_counts=_readonly(self.sample_count[rows], np.uint32),
            acquisition_kinds=_readonly(self.acquisition_kind[rows], np.uint8),
            encoded_bytes=_readonly(self.encoded_bytes[rows], np.uint32),
        )

class KnowledgeSystem:
    """K1/K2 knowledge lifecycle, local learning, costs, and metrics."""

    def __init__(
        self,
        cfg: SimulationConfig,
        output_dir: str | Path,
        *,
        initial_entity_ids: np.ndarray,
        initial_subject_ids: np.ndarray,
    ) -> None:
        self.cfg = cfg
        self.kcfg: KnowledgeConfig = cfg.knowledge
        self.catalog = KnowledgeCatalog()
        if self.kcfg.latent_policy_enabled:
            from .latent_knowledge import VariableLatentContentStore
        self.latent_store = (
            VariableLatentContentStore(self.kcfg, cfg.run.seed)
            if self.kcfg.latent_policy_enabled
            else None
        )
        self.arena = KnowledgeArena()
        self.last_transfer_plan = KnowledgeTransferPlan.empty(0)
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
            self._seed(initial_entity_ids, initial_subject_ids)
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

    def _seed(self, entity_ids: np.ndarray, subject_ids: np.ndarray) -> None:
        if self.kcfg.initial_content_count <= 0 or self.kcfg.initial_holders_fraction <= 0.0:
            return
        ids = np.asarray(entity_ids, dtype=np.uint64)
        subjects = np.asarray(subject_ids, dtype=np.uint64)
        if ids.shape != subjects.shape:
            raise ValueError("knowledge seed IDs and subjects must align")
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
        for entity_id, subject_id in zip(ids[selected], subjects[selected], strict=True):
            content_id = contents[(int(entity_id) - 1) % len(contents)]
            copy_bytes = int(self.catalog.encoded_bytes[content_id - 1])
            if self.kcfg.holder_capacity_bytes < copy_bytes:
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

    def charge_maintenance(
        self,
        *,
        energy: np.ndarray,
        alive: np.ndarray,
        primary_subject_id: np.ndarray,
        tick: int,
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
        if self.kcfg.attention_slots_per_tick >= 0:
            keep = np.zeros(senders.size, dtype=bool)
            seen: dict[int, int] = {}
            for row, receiver in enumerate(receivers):
                count = seen.get(int(receiver), 0)
                if count < self.kcfg.attention_slots_per_tick:
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
    ) -> KnowledgeStepStats:
        stats = KnowledgeStepStats(
            transfer_attempts=plan.size, attention_rejected=plan.attention_rejected
        )
        if not self.kcfg.enabled or plan.size == 0:
            self.last_transfer_plan = plan
            return stats
        plan.validate(alive.size)

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
            if storage_encoded_bytes > self.kcfg.holder_capacity_bytes:
                stats.transfer_capacity_rejected += 1
                record(row, "oversize-rejected", sender_cost_charged=send_cost)
                continue
            required = max(
                self.arena.holder_bytes(receiver_subject)
                + storage_encoded_bytes
                - self.kcfg.holder_capacity_bytes,
                0,
            )
            if required:
                stats.evicted_capacity += self.arena.evict_oldest(
                    receiver_subject, required
                )
            if (
                self.arena.holder_bytes(receiver_subject) + storage_encoded_bytes
                > self.kcfg.holder_capacity_bytes
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
            if encoded_bytes > self.kcfg.holder_capacity_bytes:
                stats.learning_capacity_rejected += 1
                continue
            held_bytes = self.arena.holder_bytes(holder)
            required = max(
                held_bytes + encoded_bytes - self.kcfg.holder_capacity_bytes, 0
            )
            if required and self.kcfg.experience_creation_requires_free_capacity:
                stats.learning_capacity_rejected += 1
                continue
            if required:
                stats.evicted_capacity += self.arena.evict_oldest(holder, required)
            if self.arena.holder_bytes(holder) + encoded_bytes > self.kcfg.holder_capacity_bytes:
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
                "nmi": float(mi / max((hx * hy) ** 0.5, 1e-30)),
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


__all__ = [
    "KnowledgeArena",
    "KnowledgeCatalog",
    "KnowledgeObservationPlan",
    "KnowledgeOutcomePlan",
    "KnowledgeStepStats",
    "KnowledgeSystem",
    "KnowledgeTransferPlan",
    "encode_local_context",
    "OUTCOME_WIDTH",
    "OUTCOME_STATUS_FAILED",
    "OUTCOME_STATUS_SUCCESS",
    "OUTCOME_STATUS_PARTIAL",
    "ACQUISITION_SEED",
    "ACQUISITION_PRIVATE_EXPERIENCE",
    "ACQUISITION_TRANSFER",
]
