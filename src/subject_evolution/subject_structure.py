"""Diagnostic-only social-subject succession from stable membership overlap.

The candidate subject graph stores currently observed body, lineage, and social
nodes.  This module adds a separate observational succession layer across group
refreshes.  It never assigns group labels, changes graph identity, or feeds any
measurement back into the simulated world.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

import numpy as np


SUBJECT_STRUCTURE_SCHEMA = "stable-membership-subject-succession-v1"


def _effective_count(counts: np.ndarray) -> float:
    values = np.asarray(counts, dtype=np.float64)
    values = values[values > 0.0]
    if values.size == 0:
        return 0.0
    shares = values / values.sum()
    return float(1.0 / np.sum(shares * shares))


class SubjectStructureDiagnostics:
    """Track formations, dissolutions, splits, merges, and membership persistence."""

    def __init__(self, output_dir: str | Path, *, schema: str = SUBJECT_STRUCTURE_SCHEMA) -> None:
        if schema != SUBJECT_STRUCTURE_SCHEMA:
            raise ValueError(f"unsupported subject structure schema {schema!r}")
        self.output_dir = Path(output_dir)
        self.schema = schema
        self.previous_memberships: dict[int, np.ndarray] = {}
        self.ever_seen_tokens: set[int] = set()
        self.first_seen_tick: dict[int, int] = {}
        self.last_seen_tick: dict[int, int] = {}
        self.observation_count_by_token: dict[int, int] = {}
        self.records: list[dict[str, Any]] = []
        self.total_refreshes = 0
        self.total_formations = 0
        self.total_dissolutions = 0
        self.total_splits = 0
        self.total_merges = 0
        self.total_reactivations = 0
        self.total_overlap_edges = 0

    def clone(self, output_dir: str | Path) -> "SubjectStructureDiagnostics":
        result = copy.deepcopy(self)
        result.output_dir = Path(output_dir)
        return result

    def snapshot_state(self) -> dict[str, Any]:
        state = copy.deepcopy(self.__dict__)
        state.pop("output_dir", None)
        return state

    def restore_state(self, state: dict[str, Any]) -> None:
        output_dir = self.output_dir
        for key, value in state.items():
            setattr(self, key, copy.deepcopy(value))
        self.output_dir = output_dir
        self.previous_memberships = {
            int(token): np.asarray(ids, dtype=np.uint64).copy()
            for token, ids in self.previous_memberships.items()
        }
        self.ever_seen_tokens = {int(value) for value in self.ever_seen_tokens}

    @staticmethod
    def _memberships(
        *,
        group_tokens: np.ndarray,
        member_starts: np.ndarray,
        member_counts: np.ndarray,
        member_indices: np.ndarray,
        stable_ids: np.ndarray,
    ) -> dict[int, np.ndarray]:
        tokens = np.asarray(group_tokens, dtype=np.uint64)
        starts = np.asarray(member_starts, dtype=np.int64)
        counts = np.asarray(member_counts, dtype=np.int32)
        members = np.asarray(member_indices, dtype=np.int32)
        identities = np.asarray(stable_ids, dtype=np.uint64)
        if tokens.ndim != 1 or starts.ndim != 1 or counts.ndim != 1 or members.ndim != 1:
            raise ValueError("subject structure group plan arrays must be one-dimensional")
        if tokens.size != starts.size or tokens.size != counts.size:
            raise ValueError("subject structure group segments must be aligned")
        if members.size != int(counts.astype(np.int64).sum()):
            raise ValueError("subject structure group member counts do not match rows")
        if members.size and (np.any(members < 0) or np.any(members >= identities.size)):
            raise ValueError("subject structure group member index is outside stable-ID state")
        result: dict[int, np.ndarray] = {}
        for token_value, start_value, count_value in zip(
            tokens.tolist(), starts.tolist(), counts.tolist()
        ):
            token = int(token_value)
            if token == 0:
                raise ValueError("subject structure groups cannot use token zero")
            start = int(start_value)
            count = int(count_value)
            ids = identities[members[start : start + count]]
            if np.any(ids == 0) or np.unique(ids).size != ids.size:
                raise ValueError("subject structure memberships require unique non-zero stable IDs")
            result[token] = np.sort(ids.astype(np.uint64, copy=False))
        return result

    def observe_group_refresh(
        self,
        *,
        tick: int,
        group_tokens: np.ndarray,
        member_starts: np.ndarray,
        member_counts: np.ndarray,
        member_indices: np.ndarray,
        stable_ids: np.ndarray,
    ) -> dict[str, Any]:
        if int(tick) < 0:
            raise ValueError("subject structure observation tick must be non-negative")
        current = self._memberships(
            group_tokens=group_tokens,
            member_starts=member_starts,
            member_counts=member_counts,
            member_indices=member_indices,
            stable_ids=stable_ids,
        )
        previous = self.previous_memberships
        previous_sets = {token: set(ids.tolist()) for token, ids in previous.items()}
        current_sets = {token: set(ids.tolist()) for token, ids in current.items()}

        edge_rows: list[dict[str, Any]] = []
        outgoing: dict[int, int] = {token: 0 for token in previous}
        incoming: dict[int, int] = {token: 0 for token in current}
        best_predecessor: dict[int, tuple[int, int, float]] = {}
        for source_token in sorted(previous):
            source = previous_sets[source_token]
            for target_token in sorted(current):
                target = current_sets[target_token]
                overlap = len(source.intersection(target))
                if overlap <= 0:
                    continue
                outgoing[source_token] += 1
                incoming[target_token] += 1
                union = len(source.union(target))
                jaccard = float(overlap / union) if union else 0.0
                edge_rows.append(
                    {
                        "source_token": source_token,
                        "target_token": target_token,
                        "overlap_members": overlap,
                        "source_retention": float(overlap / len(source)),
                        "target_inheritance": float(overlap / len(target)),
                        "jaccard": jaccard,
                    }
                )
                candidate = (overlap, -source_token, jaccard)
                incumbent = best_predecessor.get(target_token)
                if incumbent is None or candidate > incumbent:
                    best_predecessor[target_token] = candidate

        formations = sum(1 for token in current if incoming[token] == 0)
        dissolutions = sum(1 for token in previous if outgoing[token] == 0)
        splits = sum(1 for token in previous if outgoing[token] > 1)
        merges = sum(1 for token in current if incoming[token] > 1)
        reactivations = sum(
            1 for token in current if token not in previous and token in self.ever_seen_tokens
        )
        same_token = sorted(set(previous).intersection(current))
        exact_membership = sum(
            1 for token in same_token if np.array_equal(previous[token], current[token])
        )

        weighted_jaccard_numerator = 0.0
        weighted_target_inheritance_numerator = 0.0
        current_member_total = 0
        for target_token, target_ids in current.items():
            weight = int(target_ids.size)
            current_member_total += weight
            candidate = best_predecessor.get(target_token)
            if candidate is None:
                continue
            overlap, neg_source, jaccard = candidate
            weighted_jaccard_numerator += weight * jaccard
            weighted_target_inheritance_numerator += overlap

        for token in current:
            if token not in self.first_seen_tick:
                self.first_seen_tick[token] = int(tick)
            self.last_seen_tick[token] = int(tick)
            self.observation_count_by_token[token] = (
                self.observation_count_by_token.get(token, 0) + 1
            )

        group_sizes = np.asarray([ids.size for ids in current.values()], dtype=np.float64)
        active_ages = np.asarray(
            [int(tick) - self.first_seen_tick[token] for token in current],
            dtype=np.float64,
        )
        record = {
            "schema": self.schema,
            "tick": int(tick),
            "refresh_index": self.total_refreshes + 1,
            "previous_group_count": len(previous),
            "current_group_count": len(current),
            "current_group_members": int(group_sizes.sum()) if group_sizes.size else 0,
            "current_group_effective_count": _effective_count(group_sizes),
            "same_token_groups": len(same_token),
            "exact_membership_groups": exact_membership,
            "formation_count": formations,
            "dissolution_count": dissolutions,
            "split_source_count": splits,
            "merge_target_count": merges,
            "reactivation_count": reactivations,
            "overlap_edge_count": len(edge_rows),
            "member_weighted_predecessor_jaccard": (
                weighted_jaccard_numerator / current_member_total
                if current_member_total
                else 0.0
            ),
            "member_weighted_predecessor_inheritance": (
                weighted_target_inheritance_numerator / current_member_total
                if current_member_total
                else 0.0
            ),
            "active_group_age_ticks_mean": (
                float(active_ages.mean()) if active_ages.size else 0.0
            ),
            "active_group_age_ticks_max": (
                int(active_ages.max()) if active_ages.size else 0
            ),
            "transition_edges": edge_rows,
            "interpretation_boundary": (
                "Transitions are overlap relations between observed candidate-group "
                "memberships. They do not establish ontological subject identity."
            ),
        }
        self.records.append(record)
        self.total_refreshes += 1
        self.total_formations += formations
        self.total_dissolutions += dissolutions
        self.total_splits += splits
        self.total_merges += merges
        self.total_reactivations += reactivations
        self.total_overlap_edges += len(edge_rows)
        self.ever_seen_tokens.update(current)
        self.previous_memberships = {
            token: ids.copy() for token, ids in current.items()
        }
        return record

    def latest_metrics(self) -> dict[str, Any]:
        latest = self.records[-1] if self.records else None
        return {
            "subject_structure_schema": self.schema,
            "subject_structure_refresh_count": int(self.total_refreshes),
            "subject_structure_active_groups": int(
                latest["current_group_count"] if latest else 0
            ),
            "subject_structure_effective_groups": float(
                latest["current_group_effective_count"] if latest else 0.0
            ),
            "subject_structure_weighted_jaccard": float(
                latest["member_weighted_predecessor_jaccard"] if latest else 0.0
            ),
            "subject_structure_weighted_inheritance": float(
                latest["member_weighted_predecessor_inheritance"] if latest else 0.0
            ),
            "subject_structure_split_count_total": int(self.total_splits),
            "subject_structure_merge_count_total": int(self.total_merges),
            "subject_structure_formation_count_total": int(self.total_formations),
            "subject_structure_dissolution_count_total": int(self.total_dissolutions),
            "subject_structure_reactivation_count_total": int(self.total_reactivations),
        }

    def summary(self) -> dict[str, Any]:
        latest = self.records[-1] if self.records else None
        return {
            "schema": self.schema,
            "refresh_count": int(self.total_refreshes),
            "observed_token_count": len(self.ever_seen_tokens),
            "formation_count_total": int(self.total_formations),
            "dissolution_count_total": int(self.total_dissolutions),
            "split_source_count_total": int(self.total_splits),
            "merge_target_count_total": int(self.total_merges),
            "reactivation_count_total": int(self.total_reactivations),
            "overlap_edge_count_total": int(self.total_overlap_edges),
            "latest": latest,
            "interpretation_boundary": (
                "This is diagnostic succession of candidate social structures, "
                "not a complete arbitrary-nesting subject graph or subjecthood score."
            ),
        }

    def close(self) -> None:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        event_path = self.output_dir / "subject_structure_transitions.jsonl"
        with event_path.open("w", encoding="utf-8") as stream:
            for record in self.records:
                stream.write(json.dumps(record, sort_keys=True) + "\n")
        (self.output_dir / "subject_structure_summary.json").write_text(
            json.dumps(self.summary(), indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )


__all__ = ["SUBJECT_STRUCTURE_SCHEMA", "SubjectStructureDiagnostics"]
