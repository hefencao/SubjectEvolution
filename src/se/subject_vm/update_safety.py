"""Bounded, rejectable candidate deltas for Subject VM Stage 3C-2.

Stage 3C-2 is still audit-only.  It revalidates the exact target selected by
Stage 3C-1, combines the graph-produced family proposal with the historical
local eligibility carrier, and produces a bounded compare-and-swap style delta
proposal.  No graph parameter, eligibility state, retained state, topology,
world state, action output, or physical cost is written here.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .binding import (
    TARGET_KIND_EDGE,
    TARGET_KIND_NODE,
    SubjectVMTargetBindingProposal,
)
from .config import (
    SUBJECT_VM_MODULATION_TARGET_WIDTH,
    SubjectVMUpdateSafetyConfig,
)
from .storage import SubjectVMStorage

UPDATE_REASON_CODES = {
    "binding-not-requested": 0,
    "family-not-bound": 1,
    "stale-target": 2,
    "nonfinite-current-parameter": 3,
    "nonfinite-candidate-delta": 4,
    "candidate-below-minimum": 5,
    "parameter-bound-no-room": 6,
    "proposed": 7,
}
UPDATE_REASON_NAMES = tuple(
    name for name, _ in sorted(UPDATE_REASON_CODES.items(), key=lambda item: item[1])
)

PARAMETER_ARRAY_BY_FAMILY = (
    "node_bias",
    "node_input_gate",
    "node_output_gate",
    "node_trace_gate",
    "edge_forward_gate",
    "edge_bandwidth",
)


@dataclass(frozen=True)
class SubjectVMUpdateSafetyProposal:
    """Audit-only candidate deltas guarded by exact current parameter values."""

    requested: bool
    proposed_any: bool
    family_proposed: np.ndarray
    reason: np.ndarray
    expected_parameter_value: np.ndarray
    raw_delta: np.ndarray
    bounded_delta: np.ndarray
    projected_parameter_value: np.ndarray
    family_clip_applied: np.ndarray
    parameter_bound_applied: np.ndarray
    event_budget_scale: float
    write_authorized: bool = False


def _target_is_live(
    storage: SubjectVMStorage,
    *,
    row: int,
    family: int,
    target_kind: int,
    target_index: int,
    target_id: int,
) -> bool:
    if family < 4:
        if target_kind != int(TARGET_KIND_NODE):
            return False
        if not 0 <= target_index < storage.node_capacity:
            return False
        if not bool(storage.node_expressed[row, target_index]):
            return False
        if int(storage.node_id[row, target_index]) != target_id:
            return False
        if family == 1 and int(storage.node_input_port[row, target_index]) < 0:
            return False
        if family == 2 and int(storage.node_output_port[row, target_index]) < 0:
            return False
        if family == 3 and int(storage.node_trace_port[row, target_index]) < 0:
            return False
        return True
    if target_kind != int(TARGET_KIND_EDGE):
        return False
    if not 0 <= target_index < storage.edge_capacity:
        return False
    return bool(
        storage.edge_expressed[row, target_index]
        and int(storage.edge_id[row, target_index]) == target_id
    )


def _current_parameter(
    storage: SubjectVMStorage, *, row: int, family: int, target_index: int
) -> float:
    array = getattr(storage, PARAMETER_ARRAY_BY_FAMILY[family])
    return float(array[row, target_index])


def propose_safe_parameter_deltas(
    storage: SubjectVMStorage,
    *,
    row: int,
    binding: SubjectVMTargetBindingProposal,
    cfg: SubjectVMUpdateSafetyConfig,
) -> SubjectVMUpdateSafetyProposal:
    """Form bounded candidate deltas without granting graph write authority.

    The candidate formula is a role-neutral three-factor bootstrap:

        family proposal × historical local eligibility × configured step scale

    Per-family clips are applied first.  If the surviving candidates exceed the
    per-event L1 envelope, all are scaled proportionally so family ordering does
    not decide which proposal survives.  Finally, projected parameter bounds are
    applied.  The captured current parameter value is a future compare-and-swap
    and rollback guard; this stage never consumes it to mutate storage.
    """
    width = SUBJECT_VM_MODULATION_TARGET_WIDTH
    if not 0 <= int(row) < storage.entity_capacity:
        raise ValueError("subject_vm update safety row is outside capacity")

    family_proposed = np.zeros(width, dtype=bool)
    reason = np.full(
        width,
        UPDATE_REASON_CODES[
            "binding-not-requested" if not binding.requested else "family-not-bound"
        ],
        dtype=np.uint8,
    )
    expected = np.zeros(width, dtype=np.float32)
    raw = np.zeros(width, dtype=np.float32)
    bounded = np.zeros(width, dtype=np.float32)
    projected = np.zeros(width, dtype=np.float32)
    family_clipped = np.zeros(width, dtype=bool)
    parameter_bounded = np.zeros(width, dtype=bool)

    if not binding.requested:
        return SubjectVMUpdateSafetyProposal(
            requested=False,
            proposed_any=False,
            family_proposed=family_proposed,
            reason=reason,
            expected_parameter_value=expected,
            raw_delta=raw,
            bounded_delta=bounded,
            projected_parameter_value=projected,
            family_clip_applied=family_clipped,
            parameter_bound_applied=parameter_bounded,
            event_budget_scale=1.0,
        )

    preliminary = np.zeros(width, dtype=np.float64)
    live = np.zeros(width, dtype=bool)
    for family in range(width):
        if not bool(binding.family_bound[family]):
            continue
        target_kind = int(binding.target_kind[family])
        target_index = int(binding.target_index[family])
        target_id = int(binding.target_id[family])
        if not _target_is_live(
            storage,
            row=int(row),
            family=family,
            target_kind=target_kind,
            target_index=target_index,
            target_id=target_id,
        ):
            reason[family] = np.uint8(UPDATE_REASON_CODES["stale-target"])
            continue
        current = _current_parameter(
            storage, row=int(row), family=family, target_index=target_index
        )
        if not np.isfinite(current):
            reason[family] = np.uint8(
                UPDATE_REASON_CODES["nonfinite-current-parameter"]
            )
            continue
        expected[family] = np.float32(current)
        candidate = (
            float(binding.family_proposal[family])
            * float(binding.eligibility_value[family])
            * float(cfg.step_scale)
        )
        if not np.isfinite(candidate):
            reason[family] = np.uint8(
                UPDATE_REASON_CODES["nonfinite-candidate-delta"]
            )
            continue
        raw[family] = np.float32(candidate)
        if abs(candidate) < float(cfg.min_abs_delta):
            reason[family] = np.uint8(
                UPDATE_REASON_CODES["candidate-below-minimum"]
            )
            continue
        clip = float(cfg.family_delta_clip[family])
        clipped = float(np.clip(candidate, -clip, clip))
        family_clipped[family] = not np.isclose(
            clipped, candidate, rtol=0.0, atol=1e-12
        )
        preliminary[family] = clipped
        live[family] = True

    l1 = float(np.sum(np.abs(preliminary[live])))
    budget_scale = (
        1.0
        if l1 == 0.0 or l1 <= float(cfg.event_l1_budget)
        else float(cfg.event_l1_budget) / l1
    )

    for family in np.flatnonzero(live).tolist():
        candidate = float(preliminary[family]) * budget_scale
        current = float(expected[family])
        low = float(cfg.parameter_lower_bounds[family])
        high = float(cfg.parameter_upper_bounds[family])
        next_value = float(np.clip(current + candidate, low, high))
        final_delta = next_value - current
        parameter_bounded[family] = not np.isclose(
            final_delta, candidate, rtol=0.0, atol=1e-12
        )
        projected[family] = np.float32(next_value)
        if abs(final_delta) < float(cfg.min_abs_delta):
            reason[family] = np.uint8(
                UPDATE_REASON_CODES["parameter-bound-no-room"]
            )
            continue
        bounded[family] = np.float32(final_delta)
        family_proposed[family] = True
        reason[family] = np.uint8(UPDATE_REASON_CODES["proposed"])

    return SubjectVMUpdateSafetyProposal(
        requested=True,
        proposed_any=bool(np.any(family_proposed)),
        family_proposed=family_proposed,
        reason=reason,
        expected_parameter_value=expected,
        raw_delta=raw,
        bounded_delta=bounded,
        projected_parameter_value=projected,
        family_clip_applied=family_clipped,
        parameter_bound_applied=parameter_bounded,
        event_budget_scale=float(budget_scale),
    )


__all__ = [
    "PARAMETER_ARRAY_BY_FAMILY",
    "UPDATE_REASON_CODES",
    "UPDATE_REASON_NAMES",
    "SubjectVMUpdateSafetyProposal",
    "propose_safe_parameter_deltas",
]
