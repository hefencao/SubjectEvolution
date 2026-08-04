"""Unified, bounded ThoughtEvent arena for Subject VM T1.

T1 stores the same graph-produced continuous token used by the existing
Subject VM trace, but keeps an immutable pre-action event core separate from
Objective-Fact, action, value, and modulation records.  The arena is not read
by activation in T1 and therefore cannot affect policy, random draws, or world
state.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

import numpy as np

from .config import SubjectVMConfig

THOUGHT_EVENT_ARENA_SCHEMA = "se-subject-vm-thought-event-arena-t1-v1"


@dataclass(frozen=True)
class SubjectVMThoughtEventAppendBatch:
    """One committed batch of immutable ThoughtEvent cores.

    Parent arrays use a fixed-width prefix.  Zero IDs after ``parent_count``
    are padding, not parents.  T1 runtime emissions use zero parents; the
    explicit contract is present so later recall stages do not need a second
    event representation.
    """

    tick: int
    rows: np.ndarray
    event_ids: np.ndarray
    entity_ids: np.ndarray
    subject_ids: np.ndarray
    emitted: np.ndarray
    tokens: np.ndarray
    parent_count: np.ndarray
    parent_event_ids: np.ndarray
    parent_weights: np.ndarray


@dataclass(frozen=True)
class SubjectVMThoughtEventRecallSelectionBatch:
    """One deterministic latest-prior-event selection aligned with rows."""

    tick: int
    rows: np.ndarray
    selected: np.ndarray
    event_ids: np.ndarray
    event_ticks: np.ndarray
    raw_tokens: np.ndarray
    recalled_tokens: np.ndarray
    content_mode: str


@dataclass
class SubjectVMThoughtEventRecallAccounting:
    recall_calls: int = 0
    requested_rows: int = 0
    candidate_slots_scanned: int = 0
    selected_events: int = 0
    read_coordinates: int = 0
    ingress_paths: int = 0
    counted_search_cost_units: int = 0
    counted_read_cost_units: int = 0
    counted_ingress_cost_units: int = 0
    last_recall_tick: int = -1


@dataclass
class SubjectVMThoughtEventAccounting:
    emitted_events: int = 0
    expired_events: int = 0
    overwritten_events: int = 0
    parent_links: int = 0
    reactivation_events: int = 0
    counted_emission_cost_units: int = 0
    counted_parent_link_cost_units: int = 0
    counted_retention_cost_units: int = 0
    last_advance_tick: int = -1
    last_event_tick: int = -1


class SubjectVMThoughtEventArena:
    """Per-subject bounded arena with immutable token cores and parent DAG IDs."""

    def __init__(self, cfg: SubjectVMConfig, entity_capacity: int) -> None:
        if not cfg.thought_event_enabled:
            raise ValueError("SubjectVMThoughtEventArena requires enabled T1 config")
        self.cfg = cfg
        self.entity_capacity = int(entity_capacity)
        self.capacity = int(cfg.thought_event.capacity_per_subject)
        self.token_width = int(cfg.trace.token_width)
        self.max_parent_count = int(cfg.thought_event.max_parent_count)
        self.retention_ticks = int(cfg.thought_event.retention_ticks)
        e, c, w, p = (
            self.entity_capacity,
            self.capacity,
            self.token_width,
            self.max_parent_count,
        )

        self.write_cursor = np.zeros(e, dtype=np.uint32)
        self.event_count = np.zeros(e, dtype=np.uint32)
        self.last_accounted_tick = np.full(e, -1, dtype=np.int64)
        self.event_valid = np.zeros((e, c), dtype=bool)
        self.event_id = np.zeros((e, c), dtype=np.uint64)
        self.event_tick = np.full((e, c), -1, dtype=np.int64)
        self.expiry_tick = np.full((e, c), -1, dtype=np.int64)
        self.entity_id = np.zeros((e, c), dtype=np.uint64)
        self.subject_id = np.zeros((e, c), dtype=np.uint64)
        self.token = np.zeros((e, c, w), dtype=np.float32)
        self.parent_count = np.zeros((e, c), dtype=np.uint8)
        self.parent_event_id = np.zeros((e, c, p), dtype=np.uint64)
        self.parent_weight = np.zeros((e, c, p), dtype=np.float32)
        self.child_reference_count = np.zeros((e, c), dtype=np.uint32)
        self.reactivation_count = np.zeros((e, c), dtype=np.uint32)
        self.last_reactivated_tick = np.full((e, c), -1, dtype=np.int64)

    @staticmethod
    def snapshot_array_names() -> tuple[str, ...]:
        return (
            "write_cursor",
            "event_count",
            "last_accounted_tick",
            "event_valid",
            "event_id",
            "event_tick",
            "expiry_tick",
            "entity_id",
            "subject_id",
            "token",
            "parent_count",
            "parent_event_id",
            "parent_weight",
            "child_reference_count",
            "reactivation_count",
            "last_reactivated_tick",
        )

    def allocated_nbytes(self) -> int:
        return int(sum(getattr(self, name).nbytes for name in self.snapshot_array_names()))

    def _rows(self, rows: np.ndarray) -> np.ndarray:
        normalized = np.asarray(rows, dtype=np.int32)
        if normalized.ndim != 1:
            raise ValueError("subject_vm ThoughtEvent rows must be one-dimensional")
        if normalized.size and (
            np.any(normalized < 0)
            or np.any(normalized >= self.entity_capacity)
            or np.unique(normalized).size != normalized.size
        ):
            raise ValueError(
                "subject_vm ThoughtEvent rows must be unique in-capacity indices"
            )
        return normalized

    def clear_rows(self, rows: np.ndarray) -> None:
        normalized = self._rows(rows)
        if normalized.size == 0:
            return
        for name in self.snapshot_array_names():
            array = getattr(self, name)
            if name in {
                "last_accounted_tick",
                "event_tick",
                "expiry_tick",
                "last_reactivated_tick",
            }:
                array[normalized] = -1
            else:
                array[normalized] = 0

    initialize_rows = clear_rows

    def move_rows(self, source_rows: np.ndarray, destination_rows: np.ndarray) -> None:
        sources = self._rows(source_rows)
        destinations = self._rows(destination_rows)
        if sources.shape != destinations.shape:
            raise ValueError("subject_vm ThoughtEvent compaction rows must match")
        if sources.size == 0:
            return
        if np.intersect1d(sources, destinations).size:
            raise ValueError("subject_vm ThoughtEvent compaction rows must be disjoint")
        for name in self.snapshot_array_names():
            array = getattr(self, name)
            array[destinations] = array[sources]
        self.clear_rows(sources)

    def _clear_slot(self, row: int, slot: int) -> None:
        self.event_valid[row, slot] = False
        self.event_id[row, slot] = 0
        self.event_tick[row, slot] = -1
        self.expiry_tick[row, slot] = -1
        self.entity_id[row, slot] = 0
        self.subject_id[row, slot] = 0
        self.token[row, slot] = 0.0
        self.parent_count[row, slot] = 0
        self.parent_event_id[row, slot] = 0
        self.parent_weight[row, slot] = 0.0
        self.child_reference_count[row, slot] = 0
        self.reactivation_count[row, slot] = 0
        self.last_reactivated_tick[row, slot] = -1

    def _event_slot(self, row: int, event_id: int) -> int | None:
        matches = np.flatnonzero(
            self.event_valid[int(row)]
            & (self.event_id[int(row)] == np.uint64(event_id))
        )
        if matches.size == 0:
            return None
        if matches.size != 1:
            raise ValueError("subject_vm ThoughtEvent identity is duplicated within a subject")
        return int(matches[0])

    def advance_rows(
        self,
        rows: np.ndarray,
        *,
        tick: int,
        accounting: SubjectVMThoughtEventAccounting,
    ) -> None:
        """Accrue count-only retention cost and enforce the hard age ceiling."""
        normalized = self._rows(rows)
        now = int(tick)
        for row in normalized.tolist():
            previous = int(self.last_accounted_tick[row])
            if previous > now:
                raise ValueError("subject_vm ThoughtEvent tick moved backwards")
            if previous >= 0 and now > previous:
                valid = self.event_valid[row]
                if np.any(valid):
                    billable_end = np.minimum(
                        now,
                        self.expiry_tick[row, valid].astype(np.int64) + 1,
                    )
                    durations = np.maximum(0, billable_end - previous)
                    event_ticks = int(np.sum(durations, dtype=np.int64))
                    accounting.counted_retention_cost_units += event_ticks * int(
                        self.cfg.thought_event.retention_per_event_tick_cost_units
                    )
            expired_slots = np.flatnonzero(
                self.event_valid[row] & (now > self.expiry_tick[row])
            )
            for slot in expired_slots.tolist():
                self._clear_slot(row, int(slot))
            if expired_slots.size:
                accounting.expired_events += int(expired_slots.size)
                self.event_count[row] = np.uint32(
                    np.count_nonzero(self.event_valid[row])
                )
            self.last_accounted_tick[row] = np.int64(now)
        if normalized.size:
            accounting.last_advance_tick = now

    def _validate_batch(self, batch: SubjectVMThoughtEventAppendBatch) -> int:
        rows = self._rows(batch.rows)
        count = int(rows.size)
        for value in (
            batch.event_ids,
            batch.entity_ids,
            batch.subject_ids,
            batch.emitted,
            batch.parent_count,
        ):
            if np.asarray(value).shape != (count,):
                raise ValueError("subject_vm ThoughtEvent vectors must align with rows")
        if np.asarray(batch.tokens).shape != (count, self.token_width):
            raise ValueError("subject_vm ThoughtEvent token width mismatch")
        parent_shape = (count, self.max_parent_count)
        if np.asarray(batch.parent_event_ids).shape != parent_shape:
            raise ValueError("subject_vm ThoughtEvent parent identity width mismatch")
        if np.asarray(batch.parent_weights).shape != parent_shape:
            raise ValueError("subject_vm ThoughtEvent parent weight width mismatch")
        if np.any(~np.isfinite(np.asarray(batch.tokens, dtype=np.float64))):
            raise ValueError("subject_vm ThoughtEvent tokens must be finite")
        if np.any(
            np.abs(np.asarray(batch.tokens, dtype=np.float64))
            > float(self.cfg.trace.token_clip) + 1e-6
        ):
            raise ValueError("subject_vm ThoughtEvent token exceeds trace clip")
        if np.any(~np.isfinite(np.asarray(batch.parent_weights, dtype=np.float64))):
            raise ValueError("subject_vm ThoughtEvent parent weights must be finite")
        parent_count = np.asarray(batch.parent_count, dtype=np.int64)
        if np.any(parent_count < 0) or np.any(parent_count > self.max_parent_count):
            raise ValueError("subject_vm ThoughtEvent parent count exceeds capacity")
        return count

    def append(
        self,
        batch: SubjectVMThoughtEventAppendBatch,
        *,
        owner_entity_ids: np.ndarray,
        owner_subject_ids: np.ndarray,
        accounting: SubjectVMThoughtEventAccounting,
    ) -> None:
        count = self._validate_batch(batch)
        rows = self._rows(batch.rows)
        self.advance_rows(rows, tick=int(batch.tick), accounting=accounting)
        emitted = np.asarray(batch.emitted, dtype=bool)
        event_ids = np.asarray(batch.event_ids, dtype=np.uint64)
        entity_ids = np.asarray(batch.entity_ids, dtype=np.uint64)
        subject_ids = np.asarray(batch.subject_ids, dtype=np.uint64)
        tokens = np.asarray(batch.tokens, dtype=np.float32)
        parent_counts = np.asarray(batch.parent_count, dtype=np.int64)
        parent_ids = np.asarray(batch.parent_event_ids, dtype=np.uint64)
        parent_weights = np.asarray(batch.parent_weights, dtype=np.float32)

        emitted_ids = event_ids[emitted]
        if emitted_ids.size and (
            np.any(emitted_ids == 0) or np.unique(emitted_ids).size != emitted_ids.size
        ):
            raise ValueError("subject_vm ThoughtEvent IDs must be unique and non-zero")
        existing_ids = self.event_id[self.event_valid]
        if emitted_ids.size and np.intersect1d(existing_ids, emitted_ids).size:
            raise ValueError("subject_vm ThoughtEvent ID was already committed")

        owner_entities = np.asarray(owner_entity_ids, dtype=np.uint64)
        owner_subjects = np.asarray(owner_subject_ids, dtype=np.uint64)
        for index in range(count):
            if not emitted[index]:
                continue
            row = int(rows[index])
            if entity_ids[index] != owner_entities[row]:
                raise ValueError("subject_vm ThoughtEvent entity owner mismatch")
            if subject_ids[index] != owner_subjects[row]:
                raise ValueError("subject_vm ThoughtEvent subject owner mismatch")
            parent_count = int(parent_counts[index])
            active_parent_ids = parent_ids[index, :parent_count]
            active_parent_weights = parent_weights[index, :parent_count]
            if np.any(parent_ids[index, parent_count:] != 0):
                raise ValueError("subject_vm ThoughtEvent parent IDs must use a prefix")
            if np.any(parent_weights[index, parent_count:] != 0.0):
                raise ValueError("subject_vm ThoughtEvent parent weights must use a prefix")
            if parent_count and (
                np.any(active_parent_ids == 0)
                or np.unique(active_parent_ids).size != parent_count
                or np.any(active_parent_weights == 0.0)
                or np.any(np.abs(active_parent_weights) > 64.0)
            ):
                raise ValueError("subject_vm ThoughtEvent parent prefix is invalid")

            parent_slots: list[int] = []
            for parent_id in active_parent_ids.tolist():
                if int(parent_id) == int(event_ids[index]):
                    raise ValueError("subject_vm ThoughtEvent cannot reference itself")
                parent_slot = self._event_slot(row, int(parent_id))
                if parent_slot is None:
                    raise ValueError(
                        "subject_vm ThoughtEvent parent must be a retained event of the same subject"
                    )
                if int(self.event_tick[row, parent_slot]) >= int(batch.tick):
                    raise ValueError(
                        "subject_vm ThoughtEvent parent must predate the child tick"
                    )
                parent_slots.append(parent_slot)

            # A child may not evict a parent it references in the same append.
            # Search deterministically from the ring cursor for a non-parent slot.
            start_slot = int(self.write_cursor[row] % self.capacity)
            parent_slot_set = set(parent_slots)
            slot = next(
                (
                    (start_slot + offset) % self.capacity
                    for offset in range(self.capacity)
                    if (start_slot + offset) % self.capacity not in parent_slot_set
                ),
                None,
            )
            if slot is None:
                raise ValueError(
                    "subject_vm ThoughtEvent capacity cannot preserve all active parents"
                )
            slot = int(slot)
            if self.event_valid[row, slot]:
                accounting.overwritten_events += 1
            self._clear_slot(row, slot)
            self.event_valid[row, slot] = True
            self.event_id[row, slot] = event_ids[index]
            self.event_tick[row, slot] = np.int64(batch.tick)
            self.expiry_tick[row, slot] = np.int64(
                int(batch.tick) + self.retention_ticks
            )
            self.entity_id[row, slot] = entity_ids[index]
            self.subject_id[row, slot] = subject_ids[index]
            self.token[row, slot] = tokens[index]
            self.parent_count[row, slot] = np.uint8(parent_count)
            if parent_count:
                self.parent_event_id[row, slot, :parent_count] = active_parent_ids
                self.parent_weight[row, slot, :parent_count] = active_parent_weights
                for parent_slot in parent_slots:
                    self.child_reference_count[row, parent_slot] += np.uint32(1)
                    self.reactivation_count[row, parent_slot] += np.uint32(1)
                    self.last_reactivated_tick[row, parent_slot] = np.int64(batch.tick)
                accounting.parent_links += parent_count
                accounting.reactivation_events += len(parent_slots)
                accounting.counted_parent_link_cost_units += parent_count * int(
                    self.cfg.thought_event.parent_link_cost_units
                )
            self.write_cursor[row] = np.uint32((slot + 1) % self.capacity)
            self.event_count[row] = np.uint32(np.count_nonzero(self.event_valid[row]))
            accounting.emitted_events += 1
            accounting.counted_emission_cost_units += int(
                self.cfg.thought_event.emission_base_cost_units
            ) + self.token_width * int(
                self.cfg.thought_event.emission_per_coordinate_cost_units
            )
            accounting.last_event_tick = int(batch.tick)

    def select_latest_prior(
        self,
        rows: np.ndarray,
        *,
        tick: int,
        accounting: SubjectVMThoughtEventRecallAccounting,
    ) -> SubjectVMThoughtEventRecallSelectionBatch:
        """Select one latest retained event from a strictly earlier tick.

        T3 deliberately has no learned query and consumes no random numbers.
        Two non-identity content modes are declared experimental controls; the
        selected parent identity and age stay unchanged.
        """
        recall_cfg = self.cfg.thought_event.recall
        if not recall_cfg.enabled:
            raise RuntimeError("subject_vm ThoughtEvent forward recall is not enabled")
        normalized = self._rows(rows)
        now = int(tick)
        count = int(normalized.size)
        selected = np.zeros(count, dtype=bool)
        event_ids = np.zeros(count, dtype=np.uint64)
        event_ticks = np.full(count, -1, dtype=np.int64)
        raw_tokens = np.zeros((count, self.token_width), dtype=np.float32)
        latest_allowed_tick = now - int(recall_cfg.min_age_ticks)
        for index, row in enumerate(normalized.tolist()):
            candidates = np.flatnonzero(
                self.event_valid[row]
                & (self.event_tick[row] <= np.int64(latest_allowed_tick))
            )
            if candidates.size == 0:
                continue
            ticks = self.event_tick[row, candidates]
            newest_tick = np.max(ticks)
            newest = candidates[ticks == newest_tick]
            ids = self.event_id[row, newest]
            slot = int(newest[int(np.argmax(ids))])
            selected[index] = True
            event_ids[index] = self.event_id[row, slot]
            event_ticks[index] = self.event_tick[row, slot]
            raw_tokens[index] = self.token[row, slot]

        mode = str(recall_cfg.content_mode)
        if mode == "identity":
            recalled = raw_tokens.copy()
        elif mode == "rotate-one-coordinate-control":
            recalled = np.roll(raw_tokens, shift=1, axis=1)
        elif mode == "zero-content-control":
            recalled = np.zeros_like(raw_tokens)
        else:  # configuration validation should make this unreachable
            raise ValueError("unsupported subject_vm ThoughtEvent recall content mode")
        recalled[~selected] = 0.0

        accounting.recall_calls += 1
        accounting.requested_rows += count
        accounting.candidate_slots_scanned += count * self.capacity
        accounting.selected_events += int(np.count_nonzero(selected))
        accounting.read_coordinates += int(np.count_nonzero(selected)) * self.token_width
        accounting.counted_search_cost_units += (
            count
            * self.capacity
            * int(recall_cfg.search_per_slot_cost_units)
        )
        accounting.counted_read_cost_units += int(np.count_nonzero(selected)) * (
            int(recall_cfg.read_base_cost_units)
            + self.token_width * int(recall_cfg.read_per_coordinate_cost_units)
        )
        accounting.last_recall_tick = now
        return SubjectVMThoughtEventRecallSelectionBatch(
            tick=now,
            rows=normalized.copy(),
            selected=selected,
            event_ids=event_ids,
            event_ticks=event_ticks,
            raw_tokens=raw_tokens,
            recalled_tokens=recalled,
            content_mode=mode,
        )

    def latest_slot(self, row: int) -> int | None:
        normalized = self._rows(np.asarray([row], dtype=np.int32))
        valid = np.flatnonzero(self.event_valid[int(normalized[0])])
        if valid.size == 0:
            return None
        ticks = self.event_tick[int(normalized[0]), valid]
        newest_tick = np.max(ticks)
        newest = valid[ticks == newest_tick]
        ids = self.event_id[int(normalized[0]), newest]
        return int(newest[int(np.argmax(ids))])

    def validate_owners(
        self,
        alive: np.ndarray,
        entity_ids: np.ndarray,
        subject_ids: np.ndarray,
    ) -> None:
        alive_mask = np.asarray(alive, dtype=bool)
        for row in np.flatnonzero(np.any(self.event_valid, axis=1)).tolist():
            if not alive_mask[row]:
                raise ValueError("dead row retained subject_vm ThoughtEvents")
            valid = self.event_valid[row]
            if np.any(self.entity_id[row, valid] != np.uint64(entity_ids[row])):
                raise ValueError("subject_vm ThoughtEvent entity identity drift")
            if np.any(self.subject_id[row, valid] != np.uint64(subject_ids[row])):
                raise ValueError("subject_vm ThoughtEvent subject identity drift")

    def validate_internal(self) -> None:
        valid = self.event_valid
        if np.any(self.event_id[valid] == 0):
            raise ValueError("valid subject_vm ThoughtEvent requires non-zero identity")
        if np.any(self.event_tick[valid] < 0):
            raise ValueError("valid subject_vm ThoughtEvent requires a tick")
        if np.any(
            self.expiry_tick[valid]
            != self.event_tick[valid] + np.int64(self.retention_ticks)
        ):
            raise ValueError("subject_vm ThoughtEvent expiry contract drifted")
        if np.any(~np.isfinite(self.token[valid])):
            raise ValueError("subject_vm ThoughtEvent token contains non-finite values")
        counts = self.parent_count.astype(np.int64)
        if np.any(counts > self.max_parent_count):
            raise ValueError("subject_vm ThoughtEvent parent count drifted")
        for row, slot in zip(*np.nonzero(valid), strict=True):
            count = int(counts[row, slot])
            if np.any(self.parent_event_id[row, slot, :count] == 0):
                raise ValueError("subject_vm ThoughtEvent active parent ID is zero")
            if np.any(self.parent_event_id[row, slot, count:] != 0):
                raise ValueError("subject_vm ThoughtEvent parent padding is non-zero")
            if np.any(self.parent_weight[row, slot, count:] != 0.0):
                raise ValueError("subject_vm ThoughtEvent weight padding is non-zero")
            if np.any(~np.isfinite(self.parent_weight[row, slot, :count])):
                raise ValueError("subject_vm ThoughtEvent parent weight is non-finite")
        invalid = ~valid
        if np.any(self.event_id[invalid] != 0):
            raise ValueError("invalid subject_vm ThoughtEvent retained identity")
        expected_counts = valid.sum(axis=1, dtype=np.uint32)
        if not np.array_equal(self.event_count, expected_counts):
            raise ValueError("subject_vm ThoughtEvent event_count drifted")

    def snapshot_state(self) -> dict[str, Any]:
        self.validate_internal()
        return {
            "schema": THOUGHT_EVENT_ARENA_SCHEMA,
            "entity_capacity": self.entity_capacity,
            "capacity_per_subject": self.capacity,
            "token_width": self.token_width,
            "max_parent_count": self.max_parent_count,
            "retention_ticks": self.retention_ticks,
            "arrays": {
                name: getattr(self, name).copy() for name in self.snapshot_array_names()
            },
        }

    @classmethod
    def from_snapshot(
        cls,
        cfg: SubjectVMConfig,
        entity_capacity: int,
        payload: dict[str, Any],
    ) -> "SubjectVMThoughtEventArena":
        if payload.get("schema") != THOUGHT_EVENT_ARENA_SCHEMA:
            raise ValueError("unsupported subject_vm ThoughtEvent arena schema")
        result = cls(cfg, entity_capacity)
        expected = (
            result.entity_capacity,
            result.capacity,
            result.token_width,
            result.max_parent_count,
            result.retention_ticks,
        )
        actual = (
            int(payload.get("entity_capacity", -1)),
            int(payload.get("capacity_per_subject", -1)),
            int(payload.get("token_width", -1)),
            int(payload.get("max_parent_count", -1)),
            int(payload.get("retention_ticks", -1)),
        )
        if actual != expected:
            raise ValueError("subject_vm ThoughtEvent checkpoint capacity mismatch")
        arrays = payload.get("arrays")
        if not isinstance(arrays, dict):
            raise ValueError("subject_vm ThoughtEvent checkpoint arrays are missing")
        for name in result.snapshot_array_names():
            if name not in arrays:
                raise ValueError(
                    f"subject_vm ThoughtEvent checkpoint is missing array {name}"
                )
            expected_array = getattr(result, name)
            restored = np.asarray(arrays[name], dtype=expected_array.dtype)
            if restored.shape != expected_array.shape:
                raise ValueError(
                    f"subject_vm ThoughtEvent checkpoint shape mismatch for {name}"
                )
            setattr(result, name, restored.copy())
        result.validate_internal()
        return result

    def clone(self) -> "SubjectVMThoughtEventArena":
        return type(self).from_snapshot(
            self.cfg, self.entity_capacity, self.snapshot_state()
        )

    def diagnostics(self) -> dict[str, Any]:
        return {
            "schema": THOUGHT_EVENT_ARENA_SCHEMA,
            "capacity_per_subject": self.capacity,
            "token_width": self.token_width,
            "max_parent_count": self.max_parent_count,
            "retention_ticks": self.retention_ticks,
            "allocated_nbytes": self.allocated_nbytes(),
            "stored_events": int(np.count_nonzero(self.event_valid)),
            "stored_parent_links": int(np.sum(self.parent_count, dtype=np.uint64)),
            "objective_fact_fields": False,
            "action_fields": False,
            "forward_recall_enabled": bool(self.cfg.thought_event_recall_enabled),
            "runtime_feedback_enabled": bool(self.cfg.thought_event_recall_enabled),
            "recall_schema": self.cfg.thought_event.recall.schema,
            "recall_content_mode": self.cfg.thought_event.recall.content_mode,
            "counted_cost_only": True,
        }


__all__ = [
    "THOUGHT_EVENT_ARENA_SCHEMA",
    "SubjectVMThoughtEventAccounting",
    "SubjectVMThoughtEventAppendBatch",
    "SubjectVMThoughtEventArena",
    "SubjectVMThoughtEventRecallAccounting",
    "SubjectVMThoughtEventRecallSelectionBatch",
]
