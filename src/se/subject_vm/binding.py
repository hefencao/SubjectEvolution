"""Bootstrap exact-target binding proposals for Subject VM Stage 3C-1.

The binding layer is deliberately conservative.  It snapshots at most one
still-valid pre-activation local eligibility carrier for each generic parameter
family, then binds an already-produced family proposal to that stable graph
slot.  It does not write any parameter, retained state, topology, eligibility,
or physical cost.

The fixed single-winner selector is an explicit bootstrap bias used to shorten
network-shaping search.  It is not claimed to be a universal attention model and
may later be replaced or compared with more general candidate allocators.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from .config import (
    SUBJECT_VM_MODULATION_TARGET_WIDTH,
    SubjectVMTargetBindingConfig,
)
from .modulation import SubjectVMModulationProposal
from .storage import LOCAL_ELIGIBILITY_FLAG, SubjectVMStorage

TARGET_KIND_NONE = np.uint8(0)
TARGET_KIND_NODE = np.uint8(1)
TARGET_KIND_EDGE = np.uint8(2)
TARGET_KIND_BY_FAMILY = np.asarray(
    [
        TARGET_KIND_NODE,
        TARGET_KIND_NODE,
        TARGET_KIND_NODE,
        TARGET_KIND_NODE,
        TARGET_KIND_EDGE,
        TARGET_KIND_EDGE,
    ],
    dtype=np.uint8,
)

BINDING_REASON_CODES = {
    "modulation-not-proposed": 0,
    "zero-family-proposal": 1,
    "no-valid-local-carrier": 2,
    "bound": 3,
}
BINDING_REASON_NAMES = tuple(
    name for name, _ in sorted(BINDING_REASON_CODES.items(), key=lambda item: item[1])
)


@dataclass(frozen=True)
class SubjectVMTargetCandidateBatch:
    """Compact pre-activation target candidates aligned to active rows."""

    tick: int
    rows: np.ndarray
    target_kind: np.ndarray
    target_index: np.ndarray
    target_id: np.ndarray
    eligibility_value: np.ndarray
    eligibility_age: np.ndarray


@dataclass(frozen=True)
class SubjectVMTargetBindingProposal:
    """Exact-slot proposal metadata with no graph write authority."""

    requested: bool
    bound_any: bool
    family_bound: np.ndarray
    reason: np.ndarray
    target_kind: np.ndarray
    target_index: np.ndarray
    target_id: np.ndarray
    eligibility_value: np.ndarray
    family_proposal: np.ndarray
    eligibility_age: np.ndarray = field(
        default_factory=lambda: np.zeros(
            SUBJECT_VM_MODULATION_TARGET_WIDTH, dtype=np.uint16
        )
    )


def _best_candidate(
    *,
    valid: np.ndarray,
    values: np.ndarray,
    ages: np.ndarray,
    stable_ids: np.ndarray,
    min_abs: float,
) -> tuple[int, int, float, int] | None:
    eligible = np.asarray(valid, dtype=bool).copy()
    eligible &= np.isfinite(values)
    eligible &= np.abs(values) >= float(min_abs)
    # age==0 can contain activity from the current activation tick.  Stage 3C-1
    # binds only the decayed carrier snapshot taken before those marks.
    eligible &= ages > 0
    slots = np.flatnonzero(eligible)
    if slots.size == 0:
        return None
    magnitudes = np.abs(values[slots])
    best_magnitude = float(np.max(magnitudes))
    tied = slots[np.isclose(magnitudes, best_magnitude, rtol=0.0, atol=1e-12)]
    ids = stable_ids[tied]
    best = int(tied[int(np.argmin(ids))])
    return best, int(stable_ids[best]), float(values[best]), int(ages[best])


def snapshot_pre_activation_target_candidates(
    storage: SubjectVMStorage,
    *,
    rows: np.ndarray,
    tick: int,
    cfg: SubjectVMTargetBindingConfig,
) -> SubjectVMTargetCandidateBatch:
    """Select one deterministic pre-activation carrier per parameter family."""
    normalized = storage._rows(rows)
    count = int(normalized.size)
    width = SUBJECT_VM_MODULATION_TARGET_WIDTH
    kind = np.zeros((count, width), dtype=np.uint8)
    index = np.full((count, width), -1, dtype=np.int32)
    target_id = np.zeros((count, width), dtype=np.uint32)
    value = np.zeros((count, width), dtype=np.float32)
    age = np.zeros((count, width), dtype=np.uint16)

    for batch_index, row in enumerate(normalized.tolist()):
        node_base = (
            storage.node_expressed[row]
            & ((storage.node_plasticity_flags[row] & LOCAL_ELIGIBILITY_FLAG) != 0)
        )
        node_masks = (
            node_base,
            node_base & (storage.node_input_port[row] >= 0),
            node_base & (storage.node_output_port[row] >= 0),
            node_base & (storage.node_trace_port[row] >= 0),
        )
        for family, mask in enumerate(node_masks):
            selected = _best_candidate(
                valid=mask,
                values=storage.node_eligibility_value[row],
                ages=storage.node_eligibility_age[row],
                stable_ids=storage.node_id[row],
                min_abs=float(cfg.min_abs_eligibility),
            )
            if selected is None:
                continue
            slot, stable_id, carrier, carrier_age = selected
            kind[batch_index, family] = TARGET_KIND_NODE
            index[batch_index, family] = slot
            target_id[batch_index, family] = np.uint32(stable_id)
            value[batch_index, family] = np.float32(carrier)
            age[batch_index, family] = np.uint16(carrier_age)

        edge_base = (
            storage.edge_expressed[row]
            & ((storage.plasticity_flags[row] & LOCAL_ELIGIBILITY_FLAG) != 0)
        )
        for family in (4, 5):
            selected = _best_candidate(
                valid=edge_base,
                values=storage.eligibility_value[row],
                ages=storage.eligibility_age[row],
                stable_ids=storage.edge_id[row],
                min_abs=float(cfg.min_abs_eligibility),
            )
            if selected is None:
                continue
            slot, stable_id, carrier, carrier_age = selected
            kind[batch_index, family] = TARGET_KIND_EDGE
            index[batch_index, family] = slot
            target_id[batch_index, family] = np.uint32(stable_id)
            value[batch_index, family] = np.float32(carrier)
            age[batch_index, family] = np.uint16(carrier_age)

    return SubjectVMTargetCandidateBatch(
        tick=int(tick),
        rows=normalized.copy(),
        target_kind=kind,
        target_index=index,
        target_id=target_id,
        eligibility_value=value,
        eligibility_age=age,
    )


def bind_modulation_targets(
    *,
    modulation: SubjectVMModulationProposal,
    candidates: SubjectVMTargetCandidateBatch,
    candidate_row: int,
) -> SubjectVMTargetBindingProposal:
    """Bind family proposals to compact candidates without applying updates."""
    width = SUBJECT_VM_MODULATION_TARGET_WIDTH
    family_bound = np.zeros(width, dtype=bool)
    reason = np.full(
        width,
        BINDING_REASON_CODES["modulation-not-proposed"],
        dtype=np.uint8,
    )
    kind = np.zeros(width, dtype=np.uint8)
    index = np.full(width, -1, dtype=np.int32)
    target_id = np.zeros(width, dtype=np.uint32)
    eligibility = np.zeros(width, dtype=np.float32)
    eligibility_age = np.zeros(width, dtype=np.uint16)
    family_proposal = np.zeros(width, dtype=np.float32)
    if not modulation.proposed:
        return SubjectVMTargetBindingProposal(
            requested=False,
            bound_any=False,
            family_bound=family_bound,
            reason=reason,
            target_kind=kind,
            target_index=index,
            target_id=target_id,
            eligibility_value=eligibility,
            eligibility_age=np.zeros(width, dtype=np.uint16),
            family_proposal=family_proposal,
        )

    vector = np.asarray(modulation.vector, dtype=np.float32)
    if vector.shape != (width,):
        raise ValueError("subject_vm target binding modulation width mismatch")
    if not 0 <= int(candidate_row) < np.asarray(candidates.rows).size:
        raise ValueError("subject_vm target binding candidate row is invalid")

    for family in range(width):
        proposal = float(vector[family])
        family_proposal[family] = np.float32(proposal)
        if proposal == 0.0:
            reason[family] = np.uint8(BINDING_REASON_CODES["zero-family-proposal"])
            continue
        candidate_kind = int(candidates.target_kind[candidate_row, family])
        candidate_index = int(candidates.target_index[candidate_row, family])
        candidate_id = int(candidates.target_id[candidate_row, family])
        carrier = float(candidates.eligibility_value[candidate_row, family])
        carrier_age = int(candidates.eligibility_age[candidate_row, family])
        if (
            candidate_kind != int(TARGET_KIND_BY_FAMILY[family])
            or candidate_index < 0
            or candidate_id <= 0
            or carrier == 0.0
            or carrier_age <= 0
        ):
            reason[family] = np.uint8(
                BINDING_REASON_CODES["no-valid-local-carrier"]
            )
            continue
        family_bound[family] = True
        reason[family] = np.uint8(BINDING_REASON_CODES["bound"])
        kind[family] = np.uint8(candidate_kind)
        index[family] = np.int32(candidate_index)
        target_id[family] = np.uint32(candidate_id)
        eligibility[family] = np.float32(carrier)
        eligibility_age[family] = np.uint16(carrier_age)

    return SubjectVMTargetBindingProposal(
        requested=True,
        bound_any=bool(np.any(family_bound)),
        family_bound=family_bound,
        reason=reason,
        target_kind=kind,
        target_index=index,
        target_id=target_id,
        eligibility_value=eligibility,
        eligibility_age=eligibility_age,
        family_proposal=family_proposal,
    )


__all__ = [
    "BINDING_REASON_CODES",
    "BINDING_REASON_NAMES",
    "TARGET_KIND_BY_FAMILY",
    "TARGET_KIND_EDGE",
    "TARGET_KIND_NODE",
    "TARGET_KIND_NONE",
    "SubjectVMTargetBindingProposal",
    "SubjectVMTargetCandidateBatch",
    "bind_modulation_targets",
    "snapshot_pre_activation_target_candidates",
]
