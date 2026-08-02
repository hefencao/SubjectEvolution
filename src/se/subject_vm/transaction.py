"""Atomic shadow apply and rollback validation for Subject VM Stage 3C-3.

The transaction is deliberately shadow-only.  It performs exact float32
compare-and-swap checks against the live graph, validates all proposed targets
as one all-or-none set, applies projected values to a private fixed-width
shadow vector, and proves that the vector can be restored to the captured
pre-state.  No SubjectVMStorage array is mutated and permanent write authority
is always false.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .binding import SubjectVMTargetBindingProposal
from .config import SUBJECT_VM_MODULATION_TARGET_WIDTH, SubjectVMTransactionConfig
from .storage import SubjectVMStorage
from .update_safety import (
    PARAMETER_ARRAY_BY_FAMILY,
    SubjectVMUpdateSafetyProposal,
    target_is_live,
)

TRANSACTION_REASON_CODES = {
    "update-not-requested": 0,
    "family-not-proposed": 1,
    "too-many-targets": 2,
    "stale-target": 3,
    "compare-and-swap-mismatch": 4,
    "projected-value-mismatch": 5,
    "nonfinite-shadow-value": 6,
    "transaction-aborted": 7,
    "prepared": 8,
    "rollback-mismatch": 9,
}
TRANSACTION_REASON_NAMES = tuple(
    name for name, _ in sorted(TRANSACTION_REASON_CODES.items(), key=lambda item: item[1])
)


@dataclass(frozen=True)
class SubjectVMShadowTransaction:
    """All-or-none shadow transaction with exact CAS and rollback evidence."""

    requested: bool
    prepared: bool
    shadow_applied: bool
    rollback_verified: bool
    family_prepared: np.ndarray
    reason: np.ndarray
    cas_match: np.ndarray
    observed_parameter_value: np.ndarray
    shadow_applied_value: np.ndarray
    shadow_rollback_value: np.ndarray
    counted_cost_units: int
    permanent_write_authorized: bool = False


def _float32_bits(value: float | np.float32) -> int:
    return int(np.asarray(np.float32(value)).view(np.uint32))


def prepare_shadow_transaction(
    storage: SubjectVMStorage,
    *,
    row: int,
    binding: SubjectVMTargetBindingProposal,
    update: SubjectVMUpdateSafetyProposal,
    cfg: SubjectVMTransactionConfig,
) -> SubjectVMShadowTransaction:
    """Validate, shadow-apply, and shadow-rollback one atomic event transaction.

    Exact CAS uses float32 bit identity because graph parameter arrays and the
    update proposal guard are float32.  Any failing proposed family aborts the
    complete transaction.  The shadow vector is local to this call; storage is
    read-only throughout.
    """
    width = SUBJECT_VM_MODULATION_TARGET_WIDTH
    if not 0 <= int(row) < storage.entity_capacity:
        raise ValueError("subject_vm shadow transaction row is outside capacity")

    proposed = np.asarray(update.family_proposed, dtype=bool)
    requested = bool(update.requested)
    family_prepared = np.zeros(width, dtype=bool)
    cas_match = np.zeros(width, dtype=bool)
    reason = np.full(
        width,
        TRANSACTION_REASON_CODES[
            "update-not-requested" if not requested else "family-not-proposed"
        ],
        dtype=np.uint8,
    )
    observed = np.zeros(width, dtype=np.float32)
    applied = np.zeros(width, dtype=np.float32)
    rolled_back = np.zeros(width, dtype=np.float32)
    target_count = int(np.count_nonzero(proposed))

    if not requested or target_count == 0:
        return SubjectVMShadowTransaction(
            requested=requested,
            prepared=False,
            shadow_applied=False,
            rollback_verified=False,
            family_prepared=family_prepared,
            reason=reason,
            cas_match=cas_match,
            observed_parameter_value=observed,
            shadow_applied_value=applied,
            shadow_rollback_value=rolled_back,
            counted_cost_units=0,
        )

    if target_count > int(cfg.max_targets_per_event):
        reason[proposed] = np.uint8(TRANSACTION_REASON_CODES["too-many-targets"])
        return SubjectVMShadowTransaction(
            requested=True,
            prepared=False,
            shadow_applied=False,
            rollback_verified=False,
            family_prepared=family_prepared,
            reason=reason,
            cas_match=cas_match,
            observed_parameter_value=observed,
            shadow_applied_value=applied,
            shadow_rollback_value=rolled_back,
            counted_cost_units=0,
        )

    valid = True
    for family in np.flatnonzero(proposed).tolist():
        target_kind = int(binding.target_kind[family])
        target_index = int(binding.target_index[family])
        target_id = int(binding.target_id[family])
        if not target_is_live(
            storage,
            row=int(row),
            family=family,
            target_kind=target_kind,
            target_index=target_index,
            target_id=target_id,
        ):
            reason[family] = np.uint8(TRANSACTION_REASON_CODES["stale-target"])
            valid = False
            continue
        array = getattr(storage, PARAMETER_ARRAY_BY_FAMILY[family])
        current = np.float32(array[int(row), target_index])
        expected = np.float32(update.expected_parameter_value[family])
        projected = np.float32(update.projected_parameter_value[family])
        bounded_delta = np.float32(update.bounded_delta[family])
        observed[family] = current
        if _float32_bits(current) != _float32_bits(expected):
            reason[family] = np.uint8(
                TRANSACTION_REASON_CODES["compare-and-swap-mismatch"]
            )
            valid = False
            continue
        cas_match[family] = True
        recomputed = np.float32(current + bounded_delta)
        if _float32_bits(recomputed) != _float32_bits(projected):
            reason[family] = np.uint8(
                TRANSACTION_REASON_CODES["projected-value-mismatch"]
            )
            valid = False
            continue
        if not np.isfinite(projected):
            reason[family] = np.uint8(
                TRANSACTION_REASON_CODES["nonfinite-shadow-value"]
            )
            valid = False
            continue
        family_prepared[family] = True
        reason[family] = np.uint8(TRANSACTION_REASON_CODES["prepared"])
        applied[family] = projected
        rolled_back[family] = current

    if not valid or int(np.count_nonzero(family_prepared)) != target_count:
        for family in np.flatnonzero(proposed & family_prepared).tolist():
            family_prepared[family] = False
            reason[family] = np.uint8(TRANSACTION_REASON_CODES["transaction-aborted"])
        return SubjectVMShadowTransaction(
            requested=True,
            prepared=False,
            shadow_applied=False,
            rollback_verified=False,
            family_prepared=family_prepared,
            reason=reason,
            cas_match=cas_match,
            observed_parameter_value=observed,
            shadow_applied_value=applied,
            shadow_rollback_value=rolled_back,
            counted_cost_units=0,
        )

    rollback_verified = all(
        _float32_bits(rolled_back[family])
        == _float32_bits(update.expected_parameter_value[family])
        for family in np.flatnonzero(proposed).tolist()
    )
    if not rollback_verified:
        reason[proposed] = np.uint8(TRANSACTION_REASON_CODES["rollback-mismatch"])
        family_prepared[:] = False
        return SubjectVMShadowTransaction(
            requested=True,
            prepared=False,
            shadow_applied=True,
            rollback_verified=False,
            family_prepared=family_prepared,
            reason=reason,
            cas_match=cas_match,
            observed_parameter_value=observed,
            shadow_applied_value=applied,
            shadow_rollback_value=rolled_back,
            counted_cost_units=0,
        )

    counted_cost_units = int(cfg.base_cost_units) + target_count * int(
        cfg.per_target_cost_units
    )
    return SubjectVMShadowTransaction(
        requested=True,
        prepared=True,
        shadow_applied=True,
        rollback_verified=True,
        family_prepared=family_prepared,
        reason=reason,
        cas_match=cas_match,
        observed_parameter_value=observed,
        shadow_applied_value=applied,
        shadow_rollback_value=rolled_back,
        counted_cost_units=counted_cost_units,
    )


__all__ = [
    "TRANSACTION_REASON_CODES",
    "TRANSACTION_REASON_NAMES",
    "SubjectVMShadowTransaction",
    "prepare_shadow_transaction",
]
