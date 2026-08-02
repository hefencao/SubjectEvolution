"""Guarded rollback-window live writes for Subject VM Stage 3C-4.

This module is an explicitly opted-in engineering experiment.  A write is
eligible only after Stage 3C-3 proved an exact all-or-none shadow transaction.
The live graph is then mutated through a second exact float32 compare-and-swap,
recorded in a fixed-capacity applied ledger, and automatically rolled back
before activation when the configured short window expires.

No objective event is assigned reward, valence, utility, or causal truth here.
Counted costs remain instrumentation and are not debited from entity energy.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np

from .binding import SubjectVMTargetBindingProposal
from .config import SUBJECT_VM_MODULATION_TARGET_WIDTH, SubjectVMLiveWriteConfig
from .storage import SubjectVMStorage
from .transaction import SubjectVMShadowTransaction
from .update_safety import PARAMETER_ARRAY_BY_FAMILY, SubjectVMUpdateSafetyProposal, target_is_live

LIVE_WRITE_LEDGER_SCHEMA = "se-subject-vm-live-write-ledger-v1"
LIVE_WRITE_STATUS_EMPTY = np.uint8(0)
LIVE_WRITE_STATUS_PENDING = np.uint8(1)
LIVE_WRITE_STATUS_ROLLED_BACK = np.uint8(2)
LIVE_WRITE_STATUS_ROLLBACK_FAILED = np.uint8(3)

LIVE_WRITE_REASON_CODES = {
    "not-enabled": 0,
    "transaction-not-prepared": 1,
    "row-locked": 2,
    "pending-capacity": 3,
    "window-target-budget": 4,
    "window-delta-budget": 5,
    "overlapping-pending-target": 6,
    "stale-target": 7,
    "compare-and-swap-mismatch": 8,
    "ledger-capacity": 9,
    "commit-rollback-failed": 10,
    "committed": 11,
}
LIVE_WRITE_REASON_NAMES = tuple(
    name for name, _ in sorted(LIVE_WRITE_REASON_CODES.items(), key=lambda item: item[1])
)


@dataclass(frozen=True)
class SubjectVMLiveWriteResult:
    requested: bool
    authorized: bool
    committed: bool
    reason: int
    family_committed: np.ndarray
    pre_value: np.ndarray
    post_value: np.ndarray
    ledger_slot: int
    rollback_due_tick: int
    counted_cost_units: int


@dataclass(frozen=True)
class SubjectVMLiveWriteRollbackUsage:
    checked_transactions: int = 0
    rolled_back_transactions: int = 0
    rolled_back_targets: int = 0
    failed_transactions: int = 0
    counted_cost_units: int = 0


class SubjectVMLiveWriteLedger:
    """Fixed-capacity per-subject applied ledger and rollback owner."""

    def __init__(self, cfg: SubjectVMLiveWriteConfig, entity_capacity: int) -> None:
        self.cfg = cfg
        self.entity_capacity = int(entity_capacity)
        self.capacity = int(cfg.ledger_capacity_per_subject)
        self.width = SUBJECT_VM_MODULATION_TARGET_WIDTH
        e, c, w = self.entity_capacity, self.capacity, self.width
        self.write_cursor = np.zeros(e, dtype=np.uint16)
        self.row_locked = np.zeros(e, dtype=bool)
        self.window_start_tick = np.full(e, -1, dtype=np.int64)
        self.window_applied_targets = np.zeros(e, dtype=np.uint32)
        self.window_abs_delta = np.zeros(e, dtype=np.float32)
        self.entry_valid = np.zeros((e, c), dtype=bool)
        self.status = np.zeros((e, c), dtype=np.uint8)
        self.event_id = np.zeros((e, c), dtype=np.uint64)
        self.applied_tick = np.full((e, c), -1, dtype=np.int64)
        self.rollback_due_tick = np.full((e, c), -1, dtype=np.int64)
        self.family_applied = np.zeros((e, c, w), dtype=bool)
        self.target_kind = np.zeros((e, c, w), dtype=np.uint8)
        self.target_index = np.full((e, c, w), -1, dtype=np.int32)
        self.target_id = np.zeros((e, c, w), dtype=np.uint32)
        self.pre_value = np.zeros((e, c, w), dtype=np.float32)
        self.post_value = np.zeros((e, c, w), dtype=np.float32)
        self.commit_cost_units = np.zeros((e, c), dtype=np.uint32)
        self.rollback_cost_units = np.zeros((e, c), dtype=np.uint32)
        self.total_committed_transactions = 0
        self.total_committed_targets = 0
        self.total_rolled_back_transactions = 0
        self.total_rolled_back_targets = 0
        self.total_rollback_failures = 0
        self.total_counted_cost_units = 0

    @staticmethod
    def _float32_bits(value: float | np.float32) -> int:
        return int(np.asarray(np.float32(value)).view(np.uint32))

    def snapshot_array_names(self) -> tuple[str, ...]:
        return (
            "write_cursor", "row_locked", "window_start_tick",
            "window_applied_targets", "window_abs_delta", "entry_valid", "status",
            "event_id", "applied_tick", "rollback_due_tick", "family_applied",
            "target_kind", "target_index", "target_id", "pre_value", "post_value",
            "commit_cost_units", "rollback_cost_units",
        )

    def initialize_rows(self, rows: np.ndarray) -> None:
        self.clear_rows(rows)

    def clear_rows(self, rows: np.ndarray) -> None:
        rows = np.asarray(rows, dtype=np.int32)
        if rows.size == 0:
            return
        for name in self.snapshot_array_names():
            arr = getattr(self, name)
            if name in {"window_start_tick", "applied_tick", "rollback_due_tick", "target_index"}:
                arr[rows] = -1
            else:
                arr[rows] = 0

    def move_rows(self, source_rows: np.ndarray, destination_rows: np.ndarray) -> None:
        src = np.asarray(source_rows, dtype=np.int32)
        dst = np.asarray(destination_rows, dtype=np.int32)
        if src.size != dst.size:
            raise ValueError("subject_vm live-write compaction row count mismatch")
        if src.size == 0:
            return
        copies = {name: getattr(self, name)[src].copy() for name in self.snapshot_array_names()}
        self.clear_rows(dst)
        for name, values in copies.items():
            getattr(self, name)[dst] = values
        vacated = np.setdiff1d(src, dst, assume_unique=False)
        self.clear_rows(vacated)

    def clone(self) -> "SubjectVMLiveWriteLedger":
        result = type(self)(self.cfg, self.entity_capacity)
        for name in self.snapshot_array_names():
            getattr(result, name)[:] = getattr(self, name)
        for name in (
            "total_committed_transactions", "total_committed_targets",
            "total_rolled_back_transactions", "total_rolled_back_targets",
            "total_rollback_failures", "total_counted_cost_units",
        ):
            setattr(result, name, int(getattr(self, name)))
        return result

    def _refresh_window(self, row: int, tick: int) -> None:
        start = int(self.window_start_tick[row])
        if start < 0 or tick - start >= int(self.cfg.window_ticks):
            self.window_start_tick[row] = np.int64(tick)
            self.window_applied_targets[row] = np.uint32(0)
            self.window_abs_delta[row] = np.float32(0.0)

    def _pending_count(self, row: int) -> int:
        return int(np.count_nonzero(self.entry_valid[row] & (self.status[row] == LIVE_WRITE_STATUS_PENDING)))

    def _overlaps_pending(
        self, row: int, binding: SubjectVMTargetBindingProposal, proposed: np.ndarray
    ) -> bool:
        pending = np.flatnonzero(
            self.entry_valid[row] & (self.status[row] == LIVE_WRITE_STATUS_PENDING)
        )
        for family in np.flatnonzero(proposed).tolist():
            kind = int(binding.target_kind[family])
            target_id = int(binding.target_id[family])
            for slot in pending.tolist():
                mask = self.family_applied[row, slot]
                for old_family in np.flatnonzero(mask).tolist():
                    if int(self.target_kind[row, slot, old_family]) == kind and int(
                        self.target_id[row, slot, old_family]
                    ) == target_id:
                        return True
        return False

    def _select_slot(self, row: int) -> int | None:
        start = int(self.write_cursor[row]) % max(1, self.capacity)
        for offset in range(self.capacity):
            slot = (start + offset) % self.capacity
            if not self.entry_valid[row, slot] or self.status[row, slot] != LIVE_WRITE_STATUS_PENDING:
                return slot
        return None

    def commit(
        self,
        storage: SubjectVMStorage,
        *,
        row: int,
        tick: int,
        event_id: int,
        binding: SubjectVMTargetBindingProposal,
        update: SubjectVMUpdateSafetyProposal,
        transaction: SubjectVMShadowTransaction,
    ) -> SubjectVMLiveWriteResult:
        width = self.width
        empty_bool = np.zeros(width, dtype=bool)
        empty_float = np.zeros(width, dtype=np.float32)
        requested = bool(transaction.requested)
        def reject(reason: str) -> SubjectVMLiveWriteResult:
            return SubjectVMLiveWriteResult(
                requested=requested,
                authorized=False,
                committed=False,
                reason=LIVE_WRITE_REASON_CODES[reason],
                family_committed=empty_bool.copy(),
                pre_value=empty_float.copy(),
                post_value=empty_float.copy(),
                ledger_slot=-1,
                rollback_due_tick=-1,
                counted_cost_units=0,
            )
        if not self.cfg.enabled:
            return reject("not-enabled")
        if not transaction.prepared or not transaction.rollback_verified:
            return reject("transaction-not-prepared")
        if self.row_locked[row]:
            return reject("row-locked")
        proposed = np.asarray(transaction.family_prepared, dtype=bool)
        target_count = int(np.count_nonzero(proposed))
        if self._pending_count(row) >= int(self.cfg.max_pending_transactions):
            return reject("pending-capacity")
        self._refresh_window(row, int(tick))
        if int(self.window_applied_targets[row]) + target_count > int(
            self.cfg.max_applied_targets_per_window
        ):
            return reject("window-target-budget")
        abs_delta = float(np.sum(np.abs(update.bounded_delta[proposed]), dtype=np.float64))
        if float(self.window_abs_delta[row]) + abs_delta > float(
            self.cfg.max_abs_delta_per_window
        ) + 1e-12:
            return reject("window-delta-budget")
        if self._overlaps_pending(row, binding, proposed):
            return reject("overlapping-pending-target")
        slot = self._select_slot(row)
        if slot is None:
            return reject("ledger-capacity")

        pre = np.zeros(width, dtype=np.float32)
        post = np.zeros(width, dtype=np.float32)
        valid = True
        reason = "committed"
        for family in np.flatnonzero(proposed).tolist():
            kind = int(binding.target_kind[family])
            index = int(binding.target_index[family])
            target_id = int(binding.target_id[family])
            if not target_is_live(storage, row=row, family=family, target_kind=kind, target_index=index, target_id=target_id):
                valid = False; reason = "stale-target"; break
            array = getattr(storage, PARAMETER_ARRAY_BY_FAMILY[family])
            current = np.float32(array[row, index])
            expected = np.float32(transaction.observed_parameter_value[family])
            projected = np.float32(transaction.shadow_applied_value[family])
            if self._float32_bits(current) != self._float32_bits(expected):
                valid = False; reason = "compare-and-swap-mismatch"; break
            pre[family] = current
            post[family] = projected
        if not valid:
            return reject(reason)

        written: list[int] = []
        try:
            for family in np.flatnonzero(proposed).tolist():
                index = int(binding.target_index[family])
                array = getattr(storage, PARAMETER_ARRAY_BY_FAMILY[family])
                array[row, index] = post[family]
                if self._float32_bits(array[row, index]) != self._float32_bits(post[family]):
                    raise RuntimeError("live write verification failed")
                written.append(family)
        except Exception:
            rollback_ok = True
            for family in written:
                index = int(binding.target_index[family])
                array = getattr(storage, PARAMETER_ARRAY_BY_FAMILY[family])
                array[row, index] = pre[family]
                rollback_ok &= self._float32_bits(array[row, index]) == self._float32_bits(pre[family])
            if not rollback_ok:
                self.row_locked[row] = True
            return reject("commit-rollback-failed")

        due = int(tick) + int(self.cfg.rollback_after_ticks)
        self.entry_valid[row, slot] = True
        self.status[row, slot] = LIVE_WRITE_STATUS_PENDING
        self.event_id[row, slot] = np.uint64(event_id)
        self.applied_tick[row, slot] = np.int64(tick)
        self.rollback_due_tick[row, slot] = np.int64(due)
        self.family_applied[row, slot] = proposed
        self.target_kind[row, slot] = binding.target_kind
        self.target_index[row, slot] = binding.target_index
        self.target_id[row, slot] = binding.target_id
        self.pre_value[row, slot] = pre
        self.post_value[row, slot] = post
        cost = int(self.cfg.commit_base_cost_units) + target_count * int(
            self.cfg.commit_per_target_cost_units
        )
        self.commit_cost_units[row, slot] = np.uint32(cost)
        self.rollback_cost_units[row, slot] = np.uint32(0)
        self.write_cursor[row] = np.uint16((slot + 1) % self.capacity)
        self.window_applied_targets[row] = np.uint32(int(self.window_applied_targets[row]) + target_count)
        self.window_abs_delta[row] = np.float32(float(self.window_abs_delta[row]) + abs_delta)
        self.total_committed_transactions += 1
        self.total_committed_targets += target_count
        self.total_counted_cost_units += cost
        return SubjectVMLiveWriteResult(
            requested=True,
            authorized=True,
            committed=True,
            reason=LIVE_WRITE_REASON_CODES["committed"],
            family_committed=proposed.copy(),
            pre_value=pre,
            post_value=post,
            ledger_slot=slot,
            rollback_due_tick=due,
            counted_cost_units=cost,
        )

    def rollback_due(
        self, storage: SubjectVMStorage, *, rows: np.ndarray, tick: int
    ) -> SubjectVMLiveWriteRollbackUsage:
        checked = rolled_tx = rolled_targets = failed = cost_total = 0
        for row in np.asarray(rows, dtype=np.int32).tolist():
            slots = np.flatnonzero(
                self.entry_valid[row]
                & (self.status[row] == LIVE_WRITE_STATUS_PENDING)
                & (self.rollback_due_tick[row] <= int(tick))
            )
            for slot in slots.tolist():
                checked += 1
                families = np.flatnonzero(self.family_applied[row, slot]).tolist()
                valid = True
                for family in families:
                    kind = int(self.target_kind[row, slot, family])
                    index = int(self.target_index[row, slot, family])
                    target_id = int(self.target_id[row, slot, family])
                    if not target_is_live(storage, row=row, family=family, target_kind=kind, target_index=index, target_id=target_id):
                        valid = False; break
                    array = getattr(storage, PARAMETER_ARRAY_BY_FAMILY[family])
                    if self._float32_bits(array[row, index]) != self._float32_bits(self.post_value[row, slot, family]):
                        valid = False; break
                if not valid:
                    self.status[row, slot] = LIVE_WRITE_STATUS_ROLLBACK_FAILED
                    self.row_locked[row] = True
                    failed += 1
                    self.total_rollback_failures += 1
                    continue
                for family in families:
                    index = int(self.target_index[row, slot, family])
                    array = getattr(storage, PARAMETER_ARRAY_BY_FAMILY[family])
                    array[row, index] = self.pre_value[row, slot, family]
                verified = all(
                    self._float32_bits(getattr(storage, PARAMETER_ARRAY_BY_FAMILY[family])[row, int(self.target_index[row, slot, family])])
                    == self._float32_bits(self.pre_value[row, slot, family])
                    for family in families
                )
                if not verified:
                    self.status[row, slot] = LIVE_WRITE_STATUS_ROLLBACK_FAILED
                    self.row_locked[row] = True
                    failed += 1
                    self.total_rollback_failures += 1
                    continue
                rollback_cost = int(self.cfg.rollback_base_cost_units) + len(families) * int(
                    self.cfg.rollback_per_target_cost_units
                )
                self.rollback_cost_units[row, slot] = np.uint32(rollback_cost)
                self.status[row, slot] = LIVE_WRITE_STATUS_ROLLED_BACK
                rolled_tx += 1
                rolled_targets += len(families)
                cost_total += rollback_cost
                self.total_rolled_back_transactions += 1
                self.total_rolled_back_targets += len(families)
                self.total_counted_cost_units += rollback_cost
        return SubjectVMLiveWriteRollbackUsage(
            checked_transactions=checked,
            rolled_back_transactions=rolled_tx,
            rolled_back_targets=rolled_targets,
            failed_transactions=failed,
            counted_cost_units=cost_total,
        )

    def snapshot_state(self) -> dict[str, Any]:
        return {
            "schema": LIVE_WRITE_LEDGER_SCHEMA,
            "entity_capacity": self.entity_capacity,
            "capacity_per_subject": self.capacity,
            "arrays": {name: getattr(self, name).copy() for name in self.snapshot_array_names()},
            "counters": {
                "total_committed_transactions": self.total_committed_transactions,
                "total_committed_targets": self.total_committed_targets,
                "total_rolled_back_transactions": self.total_rolled_back_transactions,
                "total_rolled_back_targets": self.total_rolled_back_targets,
                "total_rollback_failures": self.total_rollback_failures,
                "total_counted_cost_units": self.total_counted_cost_units,
            },
        }

    @classmethod
    def from_snapshot(
        cls, cfg: SubjectVMLiveWriteConfig, entity_capacity: int, payload: dict[str, Any]
    ) -> "SubjectVMLiveWriteLedger":
        if payload.get("schema") != LIVE_WRITE_LEDGER_SCHEMA:
            raise ValueError("unsupported subject_vm live-write ledger schema")
        result = cls(cfg, entity_capacity)
        if int(payload.get("entity_capacity", -1)) != result.entity_capacity or int(
            payload.get("capacity_per_subject", -1)
        ) != result.capacity:
            raise ValueError("subject_vm live-write ledger shape mismatch")
        arrays = payload.get("arrays", {})
        for name in result.snapshot_array_names():
            source = np.asarray(arrays[name], dtype=getattr(result, name).dtype)
            if source.shape != getattr(result, name).shape:
                raise ValueError(f"subject_vm live-write ledger array {name} shape mismatch")
            getattr(result, name)[:] = source
        counters = payload.get("counters", {})
        for name in (
            "total_committed_transactions", "total_committed_targets",
            "total_rolled_back_transactions", "total_rolled_back_targets",
            "total_rollback_failures", "total_counted_cost_units",
        ):
            setattr(result, name, int(counters.get(name, 0)))
        return result

    def diagnostics(self) -> dict[str, Any]:
        return {
            "configured": True,
            "enabled": bool(self.cfg.enabled),
            "pending_transactions": int(np.count_nonzero(self.status == LIVE_WRITE_STATUS_PENDING)),
            "rolled_back_transactions": int(np.count_nonzero(self.status == LIVE_WRITE_STATUS_ROLLED_BACK)),
            "rollback_failed_transactions": int(np.count_nonzero(self.status == LIVE_WRITE_STATUS_ROLLBACK_FAILED)),
            "locked_rows": int(np.count_nonzero(self.row_locked)),
            "total_committed_transactions": self.total_committed_transactions,
            "total_committed_targets": self.total_committed_targets,
            "total_rolled_back_transactions": self.total_rolled_back_transactions,
            "total_rolled_back_targets": self.total_rolled_back_targets,
            "total_rollback_failures": self.total_rollback_failures,
            "total_counted_cost_units": self.total_counted_cost_units,
        }


__all__ = [
    "LIVE_WRITE_LEDGER_SCHEMA", "LIVE_WRITE_REASON_CODES", "LIVE_WRITE_REASON_NAMES",
    "LIVE_WRITE_STATUS_EMPTY", "LIVE_WRITE_STATUS_PENDING", "LIVE_WRITE_STATUS_ROLLED_BACK",
    "LIVE_WRITE_STATUS_ROLLBACK_FAILED", "SubjectVMLiveWriteLedger",
    "SubjectVMLiveWriteResult", "SubjectVMLiveWriteRollbackUsage",
]
