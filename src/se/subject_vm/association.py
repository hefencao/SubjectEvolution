"""Bounded delayed content-address candidates for Subject VM Stage 3B-2."""
from __future__ import annotations

from dataclasses import dataclass
from functools import cmp_to_key
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
    """One bounded association result with up to two selected references.

    The scalar ``associated_*`` fields remain the primary reference used by
    legacy readers. ``selected_*`` records the complete bounded allocation for
    experiment-only multi-candidate studies. Similarity is address evidence
    only and is never interpreted as value or used as proposal strength.
    """

    requested: bool
    assigned: bool
    associated_event_id: int = 0
    associated_event_tick: int = -1
    delay_ticks: int = 0
    similarity: float = 0.0
    reason: str = "not-requested"
    selected_event_ids: tuple[int, ...] = ()
    selected_event_ticks: tuple[int, ...] = ()
    selected_delay_ticks: tuple[int, ...] = ()
    selected_similarities: tuple[float, ...] = ()

    @property
    def selected_count(self) -> int:
        return len(self.selected_event_ids)


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


def _candidate_order(tie_break: str):
    def compare(
        left: tuple[float, int, int, int],
        right: tuple[float, int, int, int],
    ) -> int:
        left_score, left_tick, left_event_id, _ = left
        right_score, right_tick, right_event_id, _ = right
        if not np.isclose(left_score, right_score, rtol=0.0, atol=1e-12):
            return -1 if left_score > right_score else 1
        if left_tick != right_tick:
            if tie_break == "latest":
                return -1 if left_tick > right_tick else 1
            return -1 if left_tick < right_tick else 1
        if left_event_id != right_event_id:
            return -1 if left_event_id < right_event_id else 1
        return 0

    return cmp_to_key(compare)


def select_delayed_association_candidate(
    *,
    cfg: SubjectVMAssociationConfig,
    tie_break: str = "latest",
    candidate_limit: int = 1,
    current_tick: int,
    current_token: np.ndarray,
    event_valid: np.ndarray,
    event_ids: np.ndarray,
    event_ticks: np.ndarray,
    historical_tokens: np.ndarray,
    excluded_slot: int,
    excluded_token_ports: Iterable[int] = (),
) -> SubjectVMDelayedAssociationCandidate:
    """Select a deterministic bounded historical-token allocation.

    Request and optional downstream-control coordinates are excluded from both
    query and candidate vectors. Therefore a request/proposal gate cannot
    improve its own content-address score. ``candidate_limit=1`` preserves the
    historical single-winner contract. ``candidate_limit=2`` selects at most
    the first two address candidates under the same score and time ordering;
    downstream code combines their objective facts with equal weights into one
    proposal, preserving the one-proposal and one-event-delta budget.
    """
    if tie_break not in {"latest", "oldest"}:
        raise ValueError("subject_vm association tie_break must be latest or oldest")
    if int(candidate_limit) not in {1, 2}:
        raise ValueError("subject_vm association candidate_limit must be one or two")
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

    scored: list[tuple[float, int, int, int]] = []
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
        scored.append((score, int(ticks[slot]), int(ids[slot]), int(slot)))

    if not scored:
        return SubjectVMDelayedAssociationCandidate(
            requested=True, assigned=False, reason="zero-candidate"
        )
    scored.sort(key=_candidate_order(tie_break))
    best_score = float(scored[0][0])
    if best_score < float(cfg.similarity_threshold):
        return SubjectVMDelayedAssociationCandidate(
            requested=True,
            assigned=False,
            similarity=best_score,
            reason="below-threshold",
        )

    eligible = [
        item for item in scored if float(item[0]) >= float(cfg.similarity_threshold)
    ]
    selected = eligible[: int(candidate_limit)]
    primary_score, primary_tick, primary_event_id, _ = selected[0]
    selected_event_ids = tuple(int(item[2]) for item in selected)
    selected_event_ticks = tuple(int(item[1]) for item in selected)
    selected_delays = tuple(int(current_tick) - int(item[1]) for item in selected)
    selected_similarities = tuple(float(item[0]) for item in selected)
    return SubjectVMDelayedAssociationCandidate(
        requested=True,
        assigned=True,
        associated_event_id=primary_event_id,
        associated_event_tick=primary_tick,
        delay_ticks=int(current_tick) - primary_tick,
        similarity=primary_score,
        reason="assigned",
        selected_event_ids=selected_event_ids,
        selected_event_ticks=selected_event_ticks,
        selected_delay_ticks=selected_delays,
        selected_similarities=selected_similarities,
    )


__all__ = [
    "ASSOCIATION_REASON_CODES",
    "ASSOCIATION_REASON_NAMES",
    "SubjectVMDelayedAssociationCandidate",
    "select_delayed_association_candidate",
]
