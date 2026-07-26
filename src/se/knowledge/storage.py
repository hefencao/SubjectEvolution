"""Append-only content catalog and holder-copy arena storage."""

from __future__ import annotations

import numpy as np

from ..random_api import RandomContext, Stream, bernoulli, uniform01
from .types import (
    ACQUISITION_PRIVATE_EXPERIENCE, ACQUISITION_SEED, ACQUISITION_TRANSFER,
    KnowledgeObservationPlan, OUTCOME_WIDTH, _readonly,
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


__all__ = ["KnowledgeCatalog", "KnowledgeArena"]
