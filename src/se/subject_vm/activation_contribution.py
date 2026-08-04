"""Observation-only execution decomposition for Subject VM activation.

The records produced here describe values already used by the authoritative
activation executor.  They are not graph state, causal attribution, reward,
value, or a parameter-update signal.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np

from .config import SUBJECT_VM_MODULATION_TARGET_NAMES
from .live_write import (
    LIVE_WRITE_STATUS_CONTROL_PENDING,
    LIVE_WRITE_STATUS_PENDING,
    SubjectVMLiveWriteLedger,
)
from .storage import SubjectVMStorage
from .update_safety import PARAMETER_ARRAY_BY_FAMILY

SUBJECT_VM_ACTIVATION_CONTRIBUTION_SCHEMA = (
    "se-subject-vm-activation-contribution-v1"
)

_STATUS_NAMES = {
    int(LIVE_WRITE_STATUS_PENDING): "guarded-live-pending",
    int(LIVE_WRITE_STATUS_CONTROL_PENDING): "read-only-control-pending",
}


@dataclass(frozen=True)
class SubjectVMActivationContributionBatch:
    """Per-row activation records captured from one authoritative execution."""

    tick: int
    rows: np.ndarray
    records: tuple[dict[str, Any], ...]


def _float32_bits(value: float | np.float32) -> int:
    return int(np.asarray(np.float32(value)).view(np.uint32))


def snapshot_temporary_write_lineage(
    storage: SubjectVMStorage,
    ledger: SubjectVMLiveWriteLedger | None,
    *,
    rows: np.ndarray,
) -> dict[int, list[dict[str, Any]]]:
    """Return active temporary-write/control-reservation identities by row.

    The snapshot is taken after due rollback processing and immediately before
    activation.  It reads the ledger and current parameter values without
    mutating either.
    """
    normalized = storage._rows(rows)
    result: dict[int, list[dict[str, Any]]] = {
        int(row): [] for row in normalized.tolist()
    }
    if ledger is None or normalized.size == 0:
        return result

    for row in normalized.tolist():
        pending = (
            ledger.entry_valid[row]
            & ledger._pending_status_mask(ledger.status[row])
        )
        for slot in np.flatnonzero(pending).tolist():
            status = int(ledger.status[row, slot])
            targets: list[dict[str, Any]] = []
            for family in np.flatnonzero(ledger.family_applied[row, slot]).tolist():
                target_index = int(ledger.target_index[row, slot, family])
                array_name = PARAMETER_ARRAY_BY_FAMILY[family]
                current = np.float32(getattr(storage, array_name)[row, target_index])
                pre = np.float32(ledger.pre_value[row, slot, family])
                post = np.float32(ledger.post_value[row, slot, family])
                targets.append(
                    {
                        "family_index": int(family),
                        "family_name": SUBJECT_VM_MODULATION_TARGET_NAMES[family],
                        "parameter_array": array_name,
                        "target_kind": int(ledger.target_kind[row, slot, family]),
                        "target_index": target_index,
                        "target_id": int(ledger.target_id[row, slot, family]),
                        "pre_value": float(pre),
                        "post_value": float(post),
                        "current_value": float(current),
                        "current_matches_pre": _float32_bits(current)
                        == _float32_bits(pre),
                        "current_matches_post": _float32_bits(current)
                        == _float32_bits(post),
                    }
                )
            result[int(row)].append(
                {
                    "ledger_slot": int(slot),
                    "status_code": status,
                    "status_name": _STATUS_NAMES.get(status, f"status-{status}"),
                    "source_event_id": int(ledger.event_id[row, slot]),
                    "applied_tick": int(ledger.applied_tick[row, slot]),
                    "rollback_due_tick": int(ledger.rollback_due_tick[row, slot]),
                    "targets": targets,
                }
            )
    return result


__all__ = [
    "SUBJECT_VM_ACTIVATION_CONTRIBUTION_SCHEMA",
    "SubjectVMActivationContributionBatch",
    "snapshot_temporary_write_lineage",
]
