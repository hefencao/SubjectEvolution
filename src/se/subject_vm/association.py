"""Bounded delayed token-association candidates for Subject VM Stage 3B-2.

Association is content addressing, not credit assignment.  A current graph token
may request a deterministic lookup among older bounded-ring tokens.  The result
is only a stable event reference, delay and continuous similarity score.  No
objective event coordinate is interpreted, no eligibility is changed and no
graph parameter is updated here.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .config import SubjectVMAssociationConfig


@dataclass(frozen=True)
class SubjectVMDelayedAssociationCandidate:
    requested: bool
    assigned: bool
    associated_event_id: int = 0
    associated_event_tick: int = -1
    delay_ticks: int = 0
    similarity: float = 0.0
    reason: str = "not-requested"


def _query_without_request_coordinate(
    token: np.ndarray, *, request_port: int
) -> np.ndarray:
    query = np.asarray(token, dtype=np.float64).copy()
    if query.ndim != 1:
        raise ValueError("subject_vm association token must be one-dimensional")
    if not 0 <= int(request_port) < query.size:
        raise ValueError("subject_vm association request port is outside token width")
    query[int(request_port)] = 0.0
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
) -> SubjectVMDelayedAssociationCandidate:
    """Select one deterministic historical-token candidate or remain unassigned.

    The request strength is read from one graph-produced token coordinate.  That
    coordinate is excluded from similarity, so a routing gate cannot improve its
    own match score.  Candidates must be strictly older than the configured
    minimum delay and remain inside both the bounded ring and maximum delay.
    """
    token = np.asarray(current_token, dtype=np.float64)
    if np.any(~np.isfinite(token)):
        raise ValueError("subject_vm association token must be finite")
    request = float(token[int(cfg.request_token_port)])
    if request < float(cfg.request_threshold):
        return SubjectVMDelayedAssociationCandidate(requested=False, assigned=False)

    query = _query_without_request_coordinate(
        token, request_port=int(cfg.request_token_port)
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
        candidate = _query_without_request_coordinate(
            candidates[slot], request_port=int(cfg.request_token_port)
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
    "SubjectVMDelayedAssociationCandidate",
    "select_delayed_association_candidate",
]
