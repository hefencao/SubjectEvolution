"""Bounded delayed content-address candidates for Subject VM Stage 3B-2."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

import numpy as np

from .config import SubjectVMAssociationConfig

ASSOCIATION_REASON_CODES = {
    "not-requested": 0,
    "zero-query": 1,
    "no-candidate": 2,
    "zero-candidate": 3,
    "below-threshold": 4,
    "assigned": 5,
}
ASSOCIATION_REASON_NAMES = tuple(
    name for name, _ in sorted(ASSOCIATION_REASON_CODES.items(), key=lambda item: item[1])
)

@dataclass(frozen=True)
class SubjectVMDelayedAssociationCandidate:
    requested: bool
    assigned: bool
    associated_event_id: int = 0
    associated_event_tick: int = -1
    delay_ticks: int = 0
    similarity: float = 0.0
    reason: str = "not-requested"


def _query_without_control_coordinates(
    token: np.ndarray,
    *,
    request_port: int,
    excluded_ports: Iterable[int] = (),
) -> np.ndarray:
    query = np.asarray(token, dtype=np.float64).copy()
    if query.ndim != 1:
        raise ValueError("subject_vm association token must be one-dimensional")
    controls = {int(request_port), *(int(value) for value in excluded_ports)}
    if any(port < 0 or port >= query.size for port in controls):
        raise ValueError("subject_vm association excluded port is outside token width")
    for port in controls:
        query[port] = 0.0
    return query


def select_delayed_association_candidate(
    *,
    cfg: SubjectVMAssociationConfig,
    current_tick: int,
    current_token: np.ndarray,
    event_valid: np.ndarray,
    event_ids: np.ndarray,
    event_ticks: np.ndarray,
    historical_tokens: np.ndarray,
    excluded_slot: int,
    excluded_token_ports: Iterable[int] = (),
) -> SubjectVMDelayedAssociationCandidate:
    """Select one deterministic historical-token candidate or remain unassigned.

    Request and optional downstream-control coordinates are excluded from both
    query and candidate vectors.  Therefore a request/proposal gate cannot
    improve its own content-address score.  Similarity remains only an address
    criterion; it is never used as value or modulation strength.
    """
    token = np.asarray(current_token, dtype=np.float64)
    if np.any(~np.isfinite(token)):
        raise ValueError("subject_vm association token must be finite")
    request = float(token[int(cfg.request_token_port)])
    if request < float(cfg.request_threshold):
        return SubjectVMDelayedAssociationCandidate(requested=False, assigned=False)

    query = _query_without_control_coordinates(
        token,
        request_port=int(cfg.request_token_port),
        excluded_ports=excluded_token_ports,
    )
    query_norm = float(np.linalg.norm(query))
    if query_norm == 0.0:
        return SubjectVMDelayedAssociationCandidate(
            requested=True, assigned=False, reason="zero-query"
        )

    valid = np.asarray(event_valid, dtype=bool).copy()
    ticks = np.asarray(event_ticks, dtype=np.int64)
    ids = np.asarray(event_ids, dtype=np.uint64)
    candidates = np.asarray(historical_tokens, dtype=np.float64)
    if valid.ndim != 1 or ticks.shape != valid.shape or ids.shape != valid.shape:
        raise ValueError("subject_vm association event metadata shape mismatch")
    if candidates.shape != (valid.size, token.size):
        raise ValueError("subject_vm association historical token shape mismatch")
    if 0 <= int(excluded_slot) < valid.size:
        valid[int(excluded_slot)] = False
    delays = int(current_tick) - ticks
    valid &= delays >= int(cfg.min_delay_ticks)
    valid &= delays <= int(cfg.max_delay_ticks)
    candidate_slots = np.flatnonzero(valid)
    if candidate_slots.size == 0:
        return SubjectVMDelayedAssociationCandidate(
            requested=True, assigned=False, reason="no-candidate"
        )

    best_slot = -1
    best_score = -np.inf
    best_tick = -1
    best_event_id = np.iinfo(np.uint64).max
    for slot in candidate_slots.tolist():
        candidate = _query_without_control_coordinates(
            candidates[slot],
            request_port=int(cfg.request_token_port),
            excluded_ports=excluded_token_ports,
        )
        candidate_norm = float(np.linalg.norm(candidate))
        if candidate_norm == 0.0:
            continue
        score = float(np.dot(query, candidate) / (query_norm * candidate_norm))
        score = float(np.clip(score, -1.0, 1.0))
        event_tick = int(ticks[slot])
        event_id = int(ids[slot])
        if (
            score > best_score
            or (
                np.isclose(score, best_score, rtol=0.0, atol=1e-12)
                and (
                    event_tick > best_tick
                    or (event_tick == best_tick and event_id < best_event_id)
                )
            )
        ):
            best_slot = int(slot)
            best_score = score
            best_tick = event_tick
            best_event_id = event_id

    if best_slot < 0:
        return SubjectVMDelayedAssociationCandidate(
            requested=True, assigned=False, reason="zero-candidate"
        )
    if best_score < float(cfg.similarity_threshold):
        return SubjectVMDelayedAssociationCandidate(
            requested=True,
            assigned=False,
            similarity=best_score,
            reason="below-threshold",
        )
    return SubjectVMDelayedAssociationCandidate(
        requested=True,
        assigned=True,
        associated_event_id=best_event_id,
        associated_event_tick=best_tick,
        delay_ticks=int(current_tick) - best_tick,
        similarity=best_score,
        reason="assigned",
    )


__all__ = [
    "ASSOCIATION_REASON_CODES",
    "ASSOCIATION_REASON_NAMES",
    "SubjectVMDelayedAssociationCandidate",
    "select_delayed_association_candidate",
]
