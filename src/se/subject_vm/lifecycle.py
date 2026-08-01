"""Narrow lifecycle hooks for inert Subject Graph VM state."""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .storage import SubjectVMStorage


@dataclass(frozen=True)
class SubjectVMMutationPlan:
    """Frozen Stage-1 mutation boundary; only the no-op schema is authorized."""

    schema: str = "none-v1"


def inherit_birth_rows(
    storage: SubjectVMStorage,
    *,
    parent_rows: np.ndarray,
    child_rows: np.ndarray,
    child_entity_ids: np.ndarray,
    child_subject_ids: np.ndarray,
    mutation: SubjectVMMutationPlan | None = None,
) -> None:
    plan = mutation or SubjectVMMutationPlan()
    if plan.schema != "none-v1":
        raise ValueError("Subject VM mutation is not authorized in Stage 1")
    storage.inherit_structure(
        parent_rows,
        child_rows,
        child_entity_ids,
        child_subject_ids,
    )


def release_dead_rows(
    storage: SubjectVMStorage,
    *,
    rows: np.ndarray,
    expected_entity_ids: np.ndarray,
    expected_subject_ids: np.ndarray,
) -> None:
    normalized = np.asarray(rows, dtype=np.int32)
    if normalized.size == 0:
        return
    if not np.array_equal(
        storage.owner_entity_id[normalized],
        np.asarray(expected_entity_ids, dtype=np.uint64),
    ):
        raise ValueError("Subject VM death hook received stale entity IDs")
    if not np.array_equal(
        storage.owner_subject_id[normalized],
        np.asarray(expected_subject_ids, dtype=np.uint64),
    ):
        raise ValueError("Subject VM death hook received stale subject IDs")
    storage.clear_rows(normalized)


def compact_rows(
    storage: SubjectVMStorage,
    *,
    source_rows: np.ndarray,
    destination_rows: np.ndarray,
) -> None:
    storage.move_rows(source_rows, destination_rows)


__all__ = [
    "SubjectVMMutationPlan",
    "compact_rows",
    "inherit_birth_rows",
    "release_dead_rows",
]
