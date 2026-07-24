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

    @property
    def total_energy_cost(self) -> float:
        return (
            self.maintenance_energy
            + self.sender_energy
            + self.receiver_energy
            + self.learning_energy
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
        self.arena = KnowledgeArena()
        self.last_transfer_plan = KnowledgeTransferPlan.empty(0)
        self.last_outcome_plan = KnowledgeOutcomePlan.empty(0)
        self.observation = KnowledgeObservationPlan.empty(0)
        self.totals = KnowledgeStepStats()
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
                        "tick", "sender_subject_id", "receiver_subject_id",
                        "source_subject_id", "source_copy_id", "content_id",
                        "encoded_bytes", "delivered", "corrupted", "status",
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
                    ],
                )
                self._policy_writer.writeheader()
            self._seed(initial_entity_ids, initial_subject_ids)
            self.candidates.ensure_catalog(self.catalog)
            self.observation = self.arena.publish(self.catalog, tick=0)

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
            contents.append(
                self.catalog.append(
                    parent_content_id=0,
                    context_key=index + 1,
                    action_id=index % 8,
                    outcome_vector=np.zeros(OUTCOME_WIDTH, dtype=np.float32),
                    encoded_bytes=self.kcfg.encoded_bytes_per_copy,
                    created_tick=0,
                    source_subject_id=source_subject,
                )
            )
        ctx = RandomContext(
            self.cfg.run.seed, 0, phase=90, stream=Stream.KNOWLEDGE_SEED
        )
        selected = bernoulli(
            ctx, ids, self.kcfg.initial_holders_fraction, draw_index=0
        )
        for entity_id, subject_id in zip(ids[selected], subjects[selected], strict=True):
            content_id = contents[(int(entity_id) - 1) % len(contents)]
            if self.kcfg.holder_capacity_bytes < self.kcfg.encoded_bytes_per_copy:
                continue
            self.arena.append(
                holder_subject_id=int(subject_id),
                content_id=content_id,
                source_subject_id=source_subject,
                confidence=1.0,
                sample_count=0,
                created_tick=0,
                last_verified_tick=0,
                encoded_bytes=self.kcfg.encoded_bytes_per_copy,
                outcome_mean=self.catalog.outcome_vector[content_id - 1],
                acquisition_kind=ACQUISITION_SEED,
            )

    def snapshot_state(self) -> dict[str, Any]:
        """Return all semantic knowledge state without open output handles."""
        return {
            "catalog": copy.deepcopy(self.catalog),
            "arena": copy.deepcopy(self.arena),
            "last_transfer_plan": copy.deepcopy(self.last_transfer_plan),
            "last_outcome_plan": copy.deepcopy(self.last_outcome_plan),
            "observation": copy.deepcopy(self.observation),
            "totals": copy.deepcopy(self.totals),
            "candidates": self.candidates.snapshot_state(),
        }

    def restore_state(self, state: dict[str, Any]) -> None:
        """Restore semantic state while retaining this run's output writers."""
        self.catalog = copy.deepcopy(state["catalog"])
        self.arena = copy.deepcopy(state["arena"])
        self.last_transfer_plan = copy.deepcopy(state["last_transfer_plan"])
        self.last_outcome_plan = copy.deepcopy(state["last_outcome_plan"])
        self.observation = copy.deepcopy(state["observation"])
        self.totals = copy.deepcopy(state["totals"])
        self.candidates.restore_state(state["candidates"])

    def clone(self, output_dir: str | Path) -> "KnowledgeSystem":
        result = object.__new__(KnowledgeSystem)
        result.cfg = self.cfg
        result.kcfg = self.kcfg
        result.catalog = copy.deepcopy(self.catalog)
        result.arena = copy.deepcopy(self.arena)
        result.last_transfer_plan = copy.deepcopy(self.last_transfer_plan)
        result.last_outcome_plan = copy.deepcopy(self.last_outcome_plan)
        result.observation = copy.deepcopy(self.observation)
        result.totals = copy.deepcopy(self.totals)
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
                        "tick", "sender_subject_id", "receiver_subject_id",
                        "source_subject_id", "source_copy_id", "content_id",
                        "encoded_bytes", "delivered", "corrupted", "status",
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
                    ],
                )
                result._policy_writer.writeheader()
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
                        "sender_subject_id": int(plan.sender_subject_ids[row]),
                        "receiver_subject_id": int(plan.receiver_subject_ids[row]),
                        "source_subject_id": int(plan.source_subject_ids[row]),
                        "source_copy_id": int(plan.source_copy_ids[row]),
                        "content_id": int(plan.content_ids[row]),
                        "encoded_bytes": int(plan.encoded_bytes[row]),
                        "delivered": int(bool(plan.delivered[row])),
                        "corrupted": int(bool(plan.corrupted[row])),
                        "status": status,
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
            if self.arena.has_content(receiver_subject, content_id):
                stats.transfer_duplicate_rejected += 1
                record(row, "duplicate-rejected", sender_cost_charged=send_cost)
                continue
            if encoded_bytes > self.kcfg.holder_capacity_bytes:
                stats.transfer_capacity_rejected += 1
                record(row, "oversize-rejected", sender_cost_charged=send_cost)
                continue
            required = max(
                self.arena.holder_bytes(receiver_subject)
                + encoded_bytes
                - self.kcfg.holder_capacity_bytes,
                0,
            )
            if required:
                stats.evicted_capacity += self.arena.evict_oldest(
                    receiver_subject, required
                )
            if self.arena.holder_bytes(receiver_subject) + encoded_bytes > self.kcfg.holder_capacity_bytes:
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
        encoded_bytes = int(self.kcfg.encoded_bytes_per_copy)
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

    def record_policy_plan(
        self,
        plan: Any,
        *,
        changed_actions: int = 0,
        changed_active_rows: np.ndarray | None = None,
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
        stats.policy_residual_abs_sum = float(
            np.abs(plan.residuals).sum(dtype=np.float64)
        )
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
                    }
                )
        return stats

    def publish(self, tick: int) -> KnowledgeObservationPlan:
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
        }
        summary.update(self.candidates.summary())
        return summary

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
