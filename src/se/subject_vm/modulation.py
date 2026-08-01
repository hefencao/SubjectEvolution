"""Rejectable parameter-family modulation proposals for Subject VM Stage 3B-3.

This module performs no graph update.  It combines graph-produced token
coordinates with a current-versus-historical objective fact contrast and emits a
bounded vector over generic parameter families.  The association score is not
used as proposal strength, and no objective coordinate has engine-defined
positive or negative value.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .association import SubjectVMDelayedAssociationCandidate
from .config import (
    SUBJECT_VM_MODULATION_FACT_WIDTH,
    SUBJECT_VM_MODULATION_TARGET_NAMES,
    SUBJECT_VM_MODULATION_TARGET_WIDTH,
    SubjectVMModulationConfig,
)

MODULATION_REASON_CODES = {
    "not-requested": 0,
    "no-association": 1,
    "missing-historical-event": 2,
    "zero-fact-weights": 3,
    "zero-fact-contrast": 4,
    "zero-target-weights": 5,
    "zero-signal": 6,
    "proposed": 7,
}
MODULATION_REASON_NAMES = tuple(
    name for name, _ in sorted(MODULATION_REASON_CODES.items(), key=lambda item: item[1])
)


@dataclass(frozen=True)
class SubjectVMModulationProposal:
    requested: bool
    proposed: bool
    signal: float
    vector: np.ndarray
    reason: str


def modulation_control_ports(cfg: SubjectVMModulationConfig) -> tuple[int, ...]:
    """Return token coordinates excluded from association similarity."""
    return (
        int(cfg.request_token_port),
        *range(
            int(cfg.fact_weight_start_port),
            int(cfg.fact_weight_start_port) + SUBJECT_VM_MODULATION_FACT_WIDTH,
        ),
        *range(
            int(cfg.target_weight_start_port),
            int(cfg.target_weight_start_port) + SUBJECT_VM_MODULATION_TARGET_WIDTH,
        ),
    )


def objective_fact_vector(
    *,
    objective_delta: np.ndarray,
    resource_delta: np.ndarray,
    internal_resource_delta: np.ndarray,
    energy_cost: float,
) -> np.ndarray:
    """Build the frozen continuous objective-fact vector without valuation."""
    result = np.concatenate(
        (
            np.asarray(objective_delta, dtype=np.float64).reshape(-1),
            np.asarray(resource_delta, dtype=np.float64).reshape(-1),
            np.asarray(internal_resource_delta, dtype=np.float64).reshape(-1),
            np.asarray([energy_cost], dtype=np.float64),
        )
    )
    if result.shape != (SUBJECT_VM_MODULATION_FACT_WIDTH,):
        raise ValueError("subject_vm modulation objective fact width mismatch")
    if np.any(~np.isfinite(result)):
        raise ValueError("subject_vm modulation objective facts must be finite")
    return result


def propose_modulation(
    *,
    cfg: SubjectVMModulationConfig,
    current_token: np.ndarray,
    association: SubjectVMDelayedAssociationCandidate,
    current_facts: np.ndarray,
    historical_facts: np.ndarray | None,
) -> SubjectVMModulationProposal:
    """Produce one bounded generic proposal or an explicit no-proposal outcome.

    The graph controls request, fact projection and target-family coordinates via
    its continuous token.  Objective facts enter only as a normalized contrast.
    Association similarity and delay do not scale the signal.
    """
    token = np.asarray(current_token, dtype=np.float64)
    if token.ndim != 1 or np.any(~np.isfinite(token)):
        raise ValueError("subject_vm modulation token must be a finite vector")
    zero = np.zeros(SUBJECT_VM_MODULATION_TARGET_WIDTH, dtype=np.float32)
    request = float(token[int(cfg.request_token_port)])
    if request < float(cfg.request_threshold):
        return SubjectVMModulationProposal(False, False, 0.0, zero, "not-requested")
    if not association.assigned:
        return SubjectVMModulationProposal(True, False, 0.0, zero, "no-association")
    if historical_facts is None:
        return SubjectVMModulationProposal(
            True, False, 0.0, zero, "missing-historical-event"
        )

    fact_start = int(cfg.fact_weight_start_port)
    fact_weights = token[fact_start : fact_start + SUBJECT_VM_MODULATION_FACT_WIDTH]
    fact_norm = float(np.linalg.norm(fact_weights))
    if fact_norm == 0.0:
        return SubjectVMModulationProposal(
            True, False, 0.0, zero, "zero-fact-weights"
        )

    current = np.asarray(current_facts, dtype=np.float64)
    historical = np.asarray(historical_facts, dtype=np.float64)
    if current.shape != (SUBJECT_VM_MODULATION_FACT_WIDTH,) or historical.shape != (
        SUBJECT_VM_MODULATION_FACT_WIDTH,
    ):
        raise ValueError("subject_vm modulation fact vector shape mismatch")
    if np.any(~np.isfinite(current)) or np.any(~np.isfinite(historical)):
        raise ValueError("subject_vm modulation fact vectors must be finite")
    contrast = current - historical
    contrast_norm = float(np.linalg.norm(contrast))
    if contrast_norm == 0.0:
        return SubjectVMModulationProposal(
            True, False, 0.0, zero, "zero-fact-contrast"
        )

    target_start = int(cfg.target_weight_start_port)
    target_weights = token[
        target_start : target_start + SUBJECT_VM_MODULATION_TARGET_WIDTH
    ]
    target_norm = float(np.linalg.norm(target_weights))
    if target_norm == 0.0:
        return SubjectVMModulationProposal(
            True, False, 0.0, zero, "zero-target-weights"
        )

    signal = float(
        np.clip(
            np.dot(fact_weights / fact_norm, contrast / contrast_norm),
            -1.0,
            1.0,
        )
    )
    if signal == 0.0:
        return SubjectVMModulationProposal(True, False, 0.0, zero, "zero-signal")
    vector = np.clip(
        signal * (target_weights / target_norm),
        -float(cfg.proposal_clip),
        float(cfg.proposal_clip),
    ).astype(np.float32)
    if not np.any(vector):
        return SubjectVMModulationProposal(True, False, 0.0, zero, "zero-signal")
    return SubjectVMModulationProposal(True, True, signal, vector, "proposed")


__all__ = [
    "MODULATION_REASON_CODES",
    "MODULATION_REASON_NAMES",
    "SUBJECT_VM_MODULATION_TARGET_NAMES",
    "SubjectVMModulationProposal",
    "modulation_control_ports",
    "objective_fact_vector",
    "propose_modulation",
]
