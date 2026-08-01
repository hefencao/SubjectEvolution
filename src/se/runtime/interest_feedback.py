"""Commit delayed partner consequences into the fixed-capacity social store."""

from __future__ import annotations

import numpy as np

from ..knowledge.types import KnowledgeVerificationCreditAudit
from ..subjects.social import SocialSystem


def commit_knowledge_verification_interest(
    social: SocialSystem,
    audit: KnowledgeVerificationCreditAudit,
    *,
    alive: np.ndarray,
    primary_subject_ids: np.ndarray,
    tick: int,
) -> int:
    """Map stable knowledge-source subjects back to living relationship rows.

    Credits from a source that is no longer represented by a living entity are
    retained in diagnostics as orphaned historical evidence.  The current
    relation table is row-addressed and therefore must not silently attach that
    evidence to a recycled entity row.
    """
    if social.cfg.social.relation_update_schema != "delayed-multichannel-interest-v2":
        return 0
    audit.validate(np.asarray(alive).size)
    if audit.size == 0:
        return 0
    living_rows = np.flatnonzero(np.asarray(alive, dtype=bool)).astype(np.int32)
    subject_values = np.asarray(primary_subject_ids, dtype=np.uint64)
    subject_to_row = {
        int(subject_values[row]): int(row)
        for row in living_rows.tolist()
        if int(subject_values[row]) > 0
    }
    owners: list[int] = []
    targets: list[int] = []
    quality: list[float] = []
    evidence: list[float] = []
    delays: list[int] = []
    orphaned = 0
    for index in range(audit.size):
        owner = int(audit.receiver_entity_indices[index])
        receiver_subject = int(audit.receiver_subject_ids[index])
        source_subject = int(audit.source_subject_ids[index])
        if (
            owner < 0
            or owner >= subject_values.size
            or not bool(alive[owner])
            or int(subject_values[owner]) != receiver_subject
        ):
            orphaned += 1
            continue
        target = subject_to_row.get(source_subject)
        if target is None or target == owner:
            orphaned += 1
            continue
        owners.append(owner)
        targets.append(target)
        quality.append(float(audit.signed_quality[index]))
        evidence.append(float(audit.evidence[index]))
        delays.append(int(audit.delay_ticks[index]))
    social.note_orphaned_knowledge_interest(orphaned)
    if not owners:
        return 0
    social.record_knowledge_interest_feedback(
        np.asarray(owners, dtype=np.int32),
        np.asarray(targets, dtype=np.int32),
        np.asarray(quality, dtype=np.float32),
        np.asarray(evidence, dtype=np.float32),
        np.asarray(delays, dtype=np.uint32),
        int(tick),
    )
    return len(owners)


__all__ = ["commit_knowledge_verification_interest"]
