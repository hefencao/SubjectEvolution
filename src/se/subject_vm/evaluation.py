"""Objective, score-free evaluation windows for Subject VM Stage 3C-5.

A prepared Stage 3C transaction may open one bounded observation window.  The
same contract supports a guarded-live arm and a read-only control arm.  The
runtime stores objective fact aggregates and rollback integrity only; it never
reduces them to reward, valence, utility, a keep/revert decision, or a permanent
parameter authorization.
"""
from __future__ import annotations

from typing import Any

import numpy as np

from .binding import SubjectVMTargetBindingProposal
from .config import (
    SUBJECT_VM_MODULATION_FACT_WIDTH,
    SUBJECT_VM_MODULATION_TARGET_WIDTH,
    SubjectVMEvaluationConfig,
)
from .live_write import (
    LIVE_WRITE_REASON_CODES,
    LIVE_WRITE_STATUS_ROLLED_BACK,
    LIVE_WRITE_STATUS_ROLLBACK_FAILED,
    LIVE_WRITE_STATUS_CONTROL_RELEASED,
    SubjectVMLiveWriteLedger,
    SubjectVMLiveWriteResult,
)
from .modulation import objective_fact_vector
from .transaction import SubjectVMShadowTransaction
from .update_safety import SubjectVMUpdateSafetyProposal

EVALUATION_LEDGER_SCHEMA = "se-subject-vm-evaluation-ledger-v1"
EVALUATION_MODE_NONE = np.uint8(0)
EVALUATION_MODE_READ_ONLY_CONTROL = np.uint8(1)
EVALUATION_MODE_GUARDED_LIVE = np.uint8(2)
EVALUATION_STATUS_EMPTY = np.uint8(0)
EVALUATION_STATUS_ACTIVE = np.uint8(1)
EVALUATION_STATUS_OBSERVED = np.uint8(2)
EVALUATION_STATUS_COMPLETE_CONTROL = np.uint8(3)
EVALUATION_STATUS_COMPLETE_LIVE_ROLLED_BACK = np.uint8(4)
EVALUATION_STATUS_ROLLBACK_FAILED = np.uint8(5)


class SubjectVMEvaluationLedger:
    """Fixed-capacity objective evidence ledger, independent of graph capacity."""

    def __init__(self, cfg: SubjectVMEvaluationConfig, entity_capacity: int) -> None:
        self.cfg = cfg
        self.entity_capacity = int(entity_capacity)
        self.capacity = int(cfg.capacity_per_subject)
        e, c = self.entity_capacity, self.capacity
        w = SUBJECT_VM_MODULATION_TARGET_WIDTH
        f = SUBJECT_VM_MODULATION_FACT_WIDTH
        self.write_cursor = np.zeros(e, dtype=np.uint16)
        self.entry_valid = np.zeros((e, c), dtype=bool)
        self.status = np.zeros((e, c), dtype=np.uint8)
        self.mode = np.zeros((e, c), dtype=np.uint8)
        self.source_event_id = np.zeros((e, c), dtype=np.uint64)
        self.start_tick = np.full((e, c), -1, dtype=np.int64)
        self.end_tick = np.full((e, c), -1, dtype=np.int64)
        self.rollback_due_tick = np.full((e, c), -1, dtype=np.int64)
        self.live_write_ledger_slot = np.full((e, c), -1, dtype=np.int16)
        self.family_observed = np.zeros((e, c, w), dtype=bool)
        self.target_kind = np.zeros((e, c, w), dtype=np.uint8)
        self.target_index = np.full((e, c, w), -1, dtype=np.int32)
        self.target_id = np.zeros((e, c, w), dtype=np.uint32)
        self.pre_value = np.zeros((e, c, w), dtype=np.float32)
        self.projected_value = np.zeros((e, c, w), dtype=np.float32)
        self.bounded_delta = np.zeros((e, c, w), dtype=np.float32)
        self.observation_count = np.zeros((e, c), dtype=np.uint16)
        self.success_count = np.zeros((e, c), dtype=np.uint16)
        self.failure_count = np.zeros((e, c), dtype=np.uint16)
        self.fact_sum = np.zeros((e, c, f), dtype=np.float32)
        self.fact_abs_sum = np.zeros((e, c, f), dtype=np.float32)
        self.fact_max_abs = np.zeros((e, c, f), dtype=np.float32)
        self.fact_clip_count = np.zeros((e, c), dtype=np.uint32)
        self.rollback_verified = np.zeros((e, c), dtype=bool)
        self.row_locked_after_window = np.zeros((e, c), dtype=bool)
        self.counted_cost_units = np.zeros((e, c), dtype=np.uint32)
        self.total_registered_control_windows = 0
        self.total_registered_live_windows = 0
        self.total_observations = 0
        self.total_completed_control_windows = 0
        self.total_completed_live_windows = 0
        self.total_rollback_failures = 0
        self.total_fact_clips = 0
        self.total_registration_capacity_rejections = 0
        self.total_counted_cost_units = 0

    def snapshot_array_names(self) -> tuple[str, ...]:
        return (
            "write_cursor", "entry_valid", "status", "mode", "source_event_id",
            "start_tick", "end_tick", "rollback_due_tick", "live_write_ledger_slot",
            "family_observed", "target_kind", "target_index", "target_id", "pre_value",
            "projected_value", "bounded_delta", "observation_count", "success_count",
            "failure_count", "fact_sum", "fact_abs_sum", "fact_max_abs",
            "fact_clip_count", "rollback_verified", "row_locked_after_window", "counted_cost_units",
        )

    def initialize_rows(self, rows: np.ndarray) -> None:
        self.clear_rows(rows)

    def clear_rows(self, rows: np.ndarray) -> None:
        rows = np.asarray(rows, dtype=np.int32)
        if rows.size == 0:
            return
        for name in self.snapshot_array_names():
            array = getattr(self, name)
            if name in {
                "start_tick", "end_tick", "rollback_due_tick",
                "live_write_ledger_slot", "target_index",
            }:
                array[rows] = -1
            else:
                array[rows] = 0

    def move_rows(self, source_rows: np.ndarray, destination_rows: np.ndarray) -> None:
        src = np.asarray(source_rows, dtype=np.int32)
        dst = np.asarray(destination_rows, dtype=np.int32)
        if src.size != dst.size:
            raise ValueError("subject_vm evaluation compaction row count mismatch")
        if src.size == 0:
            return
        copies = {name: getattr(self, name)[src].copy() for name in self.snapshot_array_names()}
        self.clear_rows(dst)
        for name, values in copies.items():
            getattr(self, name)[dst] = values
        self.clear_rows(np.setdiff1d(src, dst, assume_unique=False))

    def clone(self) -> "SubjectVMEvaluationLedger":
        result = type(self)(self.cfg, self.entity_capacity)
        for name in self.snapshot_array_names():
            getattr(result, name)[:] = getattr(self, name)
        for name in (
            "total_registered_control_windows", "total_registered_live_windows",
            "total_observations", "total_completed_control_windows",
            "total_completed_live_windows", "total_rollback_failures",
            "total_fact_clips", "total_registration_capacity_rejections",
            "total_counted_cost_units",
        ):
            setattr(result, name, int(getattr(self, name)))
        return result

    def has_active_windows(self) -> bool:
        return bool(np.any((self.status == EVALUATION_STATUS_ACTIVE) | (self.status == EVALUATION_STATUS_OBSERVED)))

    def _select_slot(self, row: int) -> int | None:
        start = int(self.write_cursor[row]) % max(1, self.capacity)
        active = (self.status[row] == EVALUATION_STATUS_ACTIVE) | (
            self.status[row] == EVALUATION_STATUS_OBSERVED
        )
        for offset in range(self.capacity):
            slot = (start + offset) % self.capacity
            if not self.entry_valid[row, slot] or not active[slot]:
                return slot
        return None

    def register(
        self,
        *,
        row: int,
        tick: int,
        event_id: int,
        binding: SubjectVMTargetBindingProposal,
        update: SubjectVMUpdateSafetyProposal,
        transaction: SubjectVMShadowTransaction,
        live_write: SubjectVMLiveWriteResult,
    ) -> int:
        """Register one live or read-only window; return ledger slot or -1."""
        if not transaction.prepared or not transaction.rollback_verified:
            return -1
        if live_write.committed:
            mode = EVALUATION_MODE_GUARDED_LIVE
            rollback_due = int(live_write.rollback_due_tick)
            live_slot = int(live_write.ledger_slot)
        elif live_write.control_reserved:
            mode = EVALUATION_MODE_READ_ONLY_CONTROL
            rollback_due = int(live_write.rollback_due_tick)
            live_slot = int(live_write.ledger_slot)
        else:
            return -1
        slot = self._select_slot(int(row))
        if slot is None:
            self.total_registration_capacity_rejections += 1
            return -1
        self.entry_valid[row, slot] = True
        self.status[row, slot] = EVALUATION_STATUS_ACTIVE
        self.mode[row, slot] = mode
        self.source_event_id[row, slot] = np.uint64(event_id)
        self.start_tick[row, slot] = np.int64(tick)
        self.end_tick[row, slot] = np.int64(int(tick) + int(self.cfg.observation_ticks))
        self.rollback_due_tick[row, slot] = np.int64(rollback_due)
        self.live_write_ledger_slot[row, slot] = np.int16(live_slot)
        self.family_observed[row, slot] = transaction.family_prepared
        self.target_kind[row, slot] = binding.target_kind
        self.target_index[row, slot] = binding.target_index
        self.target_id[row, slot] = binding.target_id
        self.pre_value[row, slot] = transaction.observed_parameter_value
        self.projected_value[row, slot] = transaction.shadow_applied_value
        self.bounded_delta[row, slot] = update.bounded_delta
        self.observation_count[row, slot] = 0
        self.success_count[row, slot] = 0
        self.failure_count[row, slot] = 0
        self.fact_sum[row, slot] = 0.0
        self.fact_abs_sum[row, slot] = 0.0
        self.fact_max_abs[row, slot] = 0.0
        self.fact_clip_count[row, slot] = 0
        self.rollback_verified[row, slot] = False
        self.row_locked_after_window[row, slot] = False
        cost = int(self.cfg.registration_cost_units)
        self.counted_cost_units[row, slot] = np.uint32(cost)
        self.write_cursor[row] = np.uint16((slot + 1) % self.capacity)
        self.total_counted_cost_units += cost
        if mode == EVALUATION_MODE_GUARDED_LIVE:
            self.total_registered_live_windows += 1
        else:
            self.total_registered_control_windows += 1
        return slot

    def observe(self, batch: Any) -> None:
        """Accumulate objective facts for active windows, without scoring them."""
        tick = int(batch.tick)
        rows = np.asarray(batch.rows, dtype=np.int32)
        clip = float(self.cfg.fact_clip)
        for index, row_value in enumerate(rows.tolist()):
            row = int(row_value)
            slots = np.flatnonzero(
                self.entry_valid[row]
                & (self.status[row] == EVALUATION_STATUS_ACTIVE)
                & (self.start_tick[row] < tick)
                & (self.end_tick[row] >= tick)
            )
            if slots.size == 0:
                continue
            facts = objective_fact_vector(
                objective_delta=batch.objective_delta[index],
                resource_delta=batch.resolution_resource_delta[index],
                internal_resource_delta=batch.resolution_internal_resource_delta[index],
                energy_cost=float(batch.resolution_energy_cost[index]),
            )
            if np.any(~np.isfinite(facts)):
                raise ValueError("subject_vm evaluation facts must be finite")
            clipped_components = int(np.count_nonzero(np.abs(facts) > clip))
            bounded = np.clip(facts, -clip, clip).astype(np.float32, copy=False)
            absolute = np.abs(bounded).astype(np.float32, copy=False)
            for slot in slots.tolist():
                self.fact_sum[row, slot] = np.asarray(
                    self.fact_sum[row, slot] + bounded, dtype=np.float32
                )
                self.fact_abs_sum[row, slot] = np.asarray(
                    self.fact_abs_sum[row, slot] + absolute, dtype=np.float32
                )
                self.fact_max_abs[row, slot] = np.maximum(
                    self.fact_max_abs[row, slot], absolute
                )
                self.observation_count[row, slot] = np.uint16(
                    int(self.observation_count[row, slot]) + 1
                )
                self.fact_clip_count[row, slot] = np.uint32(
                    int(self.fact_clip_count[row, slot]) + clipped_components
                )
                self.total_fact_clips += clipped_components
                if bool(batch.success[index]):
                    self.success_count[row, slot] = np.uint16(
                        int(self.success_count[row, slot]) + 1
                    )
                else:
                    self.failure_count[row, slot] = np.uint16(
                        int(self.failure_count[row, slot]) + 1
                    )
                cost = int(self.cfg.per_observation_cost_units)
                self.counted_cost_units[row, slot] = np.uint32(
                    int(self.counted_cost_units[row, slot]) + cost
                )
                self.total_observations += 1
                self.total_counted_cost_units += cost
                if tick >= int(self.end_tick[row, slot]):
                    self.status[row, slot] = EVALUATION_STATUS_OBSERVED

    def finalize(
        self,
        *,
        rows: np.ndarray,
        tick: int,
        live_write_ledger: SubjectVMLiveWriteLedger,
    ) -> None:
        """Finalize completed windows after due rollbacks have been attempted."""
        for row in np.asarray(rows, dtype=np.int32).tolist():
            finalizable = (
                (self.status[row] == EVALUATION_STATUS_ACTIVE)
                | (self.status[row] == EVALUATION_STATUS_OBSERVED)
            )
            slots = np.flatnonzero(
                self.entry_valid[row]
                & finalizable
                & (self.end_tick[row] < int(tick))
            )
            for slot in slots.tolist():
                mode = int(self.mode[row, slot])
                if mode == int(EVALUATION_MODE_READ_ONLY_CONTROL):
                    if int(tick) < int(self.rollback_due_tick[row, slot]):
                        continue
                    control_slot = int(self.live_write_ledger_slot[row, slot])
                    if control_slot < 0 or control_slot >= live_write_ledger.capacity:
                        self.status[row, slot] = EVALUATION_STATUS_ROLLBACK_FAILED
                        self.total_rollback_failures += 1
                        continue
                    matching_event = int(
                        live_write_ledger.event_id[row, control_slot]
                    ) == int(self.source_event_id[row, slot])
                    control_status = int(live_write_ledger.status[row, control_slot])
                    if not matching_event:
                        self.status[row, slot] = EVALUATION_STATUS_ROLLBACK_FAILED
                        self.total_rollback_failures += 1
                        continue
                    if control_status != int(LIVE_WRITE_STATUS_CONTROL_RELEASED):
                        continue
                    self.status[row, slot] = EVALUATION_STATUS_COMPLETE_CONTROL
                    self.rollback_verified[row, slot] = True
                    self.total_completed_control_windows += 1
                    continue
                if int(tick) < int(self.rollback_due_tick[row, slot]):
                    continue
                live_slot = int(self.live_write_ledger_slot[row, slot])
                if live_slot < 0 or live_slot >= live_write_ledger.capacity:
                    self.status[row, slot] = EVALUATION_STATUS_ROLLBACK_FAILED
                    self.total_rollback_failures += 1
                    continue
                matching_event = int(live_write_ledger.event_id[row, live_slot]) == int(
                    self.source_event_id[row, slot]
                )
                live_status = int(live_write_ledger.status[row, live_slot])
                if matching_event and live_status == int(LIVE_WRITE_STATUS_ROLLED_BACK):
                    self.status[row, slot] = EVALUATION_STATUS_COMPLETE_LIVE_ROLLED_BACK
                    self.rollback_verified[row, slot] = True
                    self.total_completed_live_windows += 1
                elif matching_event and live_status == int(LIVE_WRITE_STATUS_ROLLBACK_FAILED):
                    self.status[row, slot] = EVALUATION_STATUS_ROLLBACK_FAILED
                    self.total_rollback_failures += 1
                else:
                    continue
                self.row_locked_after_window[row, slot] = bool(
                    live_write_ledger.row_locked[row]
                )

    def snapshot_state(self) -> dict[str, Any]:
        return {
            "schema": EVALUATION_LEDGER_SCHEMA,
            "entity_capacity": self.entity_capacity,
            "capacity_per_subject": self.capacity,
            "arrays": {name: getattr(self, name).copy() for name in self.snapshot_array_names()},
            "counters": {
                name: int(getattr(self, name))
                for name in (
                    "total_registered_control_windows", "total_registered_live_windows",
                    "total_observations", "total_completed_control_windows",
                    "total_completed_live_windows", "total_rollback_failures",
                    "total_fact_clips", "total_registration_capacity_rejections",
                    "total_counted_cost_units",
                )
            },
        }

    @classmethod
    def from_snapshot(
        cls, cfg: SubjectVMEvaluationConfig, entity_capacity: int, payload: dict[str, Any]
    ) -> "SubjectVMEvaluationLedger":
        if payload.get("schema") != EVALUATION_LEDGER_SCHEMA:
            raise ValueError("unsupported subject_vm evaluation ledger schema")
        result = cls(cfg, entity_capacity)
        if int(payload.get("entity_capacity", -1)) != result.entity_capacity or int(
            payload.get("capacity_per_subject", -1)
        ) != result.capacity:
            raise ValueError("subject_vm evaluation ledger shape mismatch")
        arrays = payload.get("arrays", {})
        for name in result.snapshot_array_names():
            target = getattr(result, name)
            source = np.asarray(arrays[name], dtype=target.dtype)
            if source.shape != target.shape:
                raise ValueError(f"subject_vm evaluation ledger shape mismatch for {name}")
            target[:] = source
        for name, value in payload.get("counters", {}).items():
            if hasattr(result, name):
                setattr(result, name, int(value))
        return result

    def diagnostics(self) -> dict[str, Any]:
        return {
            "configured": True,
            "active_windows": int(np.count_nonzero(
                (self.status == EVALUATION_STATUS_ACTIVE)
                | (self.status == EVALUATION_STATUS_OBSERVED)
            )),
            "completed_control_windows": int(np.count_nonzero(
                self.status == EVALUATION_STATUS_COMPLETE_CONTROL
            )),
            "completed_live_windows": int(np.count_nonzero(
                self.status == EVALUATION_STATUS_COMPLETE_LIVE_ROLLED_BACK
            )),
            "rollback_failed_windows": int(np.count_nonzero(
                self.status == EVALUATION_STATUS_ROLLBACK_FAILED
            )),
            "total_registered_control_windows": self.total_registered_control_windows,
            "total_registered_live_windows": self.total_registered_live_windows,
            "total_observations": self.total_observations,
            "total_fact_clips": self.total_fact_clips,
            "total_registration_capacity_rejections": (
                self.total_registration_capacity_rejections
            ),
            "total_counted_cost_units": self.total_counted_cost_units,
            "automatic_keep_or_revert_decision": False,
            "objective_scalar_score": False,
        }


__all__ = [
    "EVALUATION_LEDGER_SCHEMA", "EVALUATION_MODE_NONE",
    "EVALUATION_MODE_READ_ONLY_CONTROL", "EVALUATION_MODE_GUARDED_LIVE",
    "EVALUATION_STATUS_EMPTY", "EVALUATION_STATUS_ACTIVE",
    "EVALUATION_STATUS_OBSERVED", "EVALUATION_STATUS_COMPLETE_CONTROL",
    "EVALUATION_STATUS_COMPLETE_LIVE_ROLLED_BACK",
    "EVALUATION_STATUS_ROLLBACK_FAILED", "SubjectVMEvaluationLedger",
]
