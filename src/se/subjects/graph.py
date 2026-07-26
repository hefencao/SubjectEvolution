"""Candidate-subject graph kept separate from physical entity slots.

The graph is intentionally small and CPU-friendly: the high-frequency world
uses dense arrays, while this structure tracks the lower-frequency candidate
nodes and their membership/lineage edges.  It is therefore also the schema
that a GPU implementation can snapshot without exposing analysis state to a
policy.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum
import copy
import numpy as np


class SubjectKind(IntEnum):
    BODY = 1
    GENE_LINEAGE = 2
    SOCIAL_GROUP = 3


class SubjectEdgeType(IntEnum):
    MEMBER_OF = 1
    DESCENDS_FROM = 2
    CONTROLS = 3


@dataclass
class CandidateSubject:
    subject_id: int
    kind: SubjectKind
    created_tick: int
    last_update_tick: int
    active: bool = True
    lineage_id: int = 0
    member_count: int = 0
    benefit_internal: float = 0.0
    benefit_external_out: float = 0.0
    benefit_external_in: float = 0.0


@dataclass(frozen=True)
class SubjectEdge:
    source_subject_id: int
    target_subject_id: int
    edge_type: SubjectEdgeType
    weight: float
    last_update_tick: int


class CandidateSubjectGraph:
    """Stable subject IDs, body/lineage/group nodes and versioned snapshots."""

    # A deliberately separate namespace avoids the tempting entity_id ==
    # subject_id shortcut even in the initial population.
    _FIRST_SUBJECT_ID = 1_000_000_000

    def __init__(self, capacity: int) -> None:
        self.body_subject_id = np.zeros(capacity, dtype=np.uint64)
        self.lineage_subject_id = np.zeros(capacity, dtype=np.uint64)
        self._next_subject_id = self._FIRST_SUBJECT_ID
        self.nodes: dict[int, CandidateSubject] = {}
        self._lineage_nodes: dict[int, int] = {}
        self._group_nodes: dict[int, int] = {}
        self._edges: dict[tuple[int, int, SubjectEdgeType], SubjectEdge] = {}
        self._active_kind_counts = np.zeros(max(SubjectKind) + 1, dtype=np.int64)
        self._active_benefit_internal = 0.0
        self._active_benefit_external_out = 0.0
        self._active_benefit_subjects = 0
        self._active_benefit_cohesion_sum = 0.0
        self.version = 0

    def clone(self) -> "CandidateSubjectGraph":
        return copy.deepcopy(self)

    def _allocate(self, kind: SubjectKind, tick: int, lineage_id: int = 0) -> int:
        subject_id = self._next_subject_id
        self._next_subject_id += 1
        self.nodes[subject_id] = CandidateSubject(
            subject_id=subject_id,
            kind=kind,
            created_tick=tick,
            last_update_tick=tick,
            lineage_id=lineage_id,
        )
        self._active_kind_counts[int(kind)] += 1
        return subject_id

    def _lineage_node(self, lineage_id: int, tick: int) -> int:
        node = self._lineage_nodes.get(lineage_id)
        if node is None:
            node = self._allocate(SubjectKind.GENE_LINEAGE, tick, lineage_id)
            self._lineage_nodes[lineage_id] = node
        return node

    def _adjust_active_benefit_summary(
        self, node: CandidateSubject, direction: int
    ) -> None:
        if node.kind != SubjectKind.SOCIAL_GROUP or not node.active:
            return
        internal = float(node.benefit_internal)
        external = float(node.benefit_external_out)
        self._active_benefit_internal += direction * internal
        self._active_benefit_external_out += direction * external
        denominator = internal + external
        if denominator > 0.0:
            self._active_benefit_subjects += direction
            self._active_benefit_cohesion_sum += direction * (
                internal / denominator
            )

    def register_bodies(
        self,
        indices: np.ndarray,
        lineage_ids: np.ndarray,
        tick: int,
    ) -> tuple[np.ndarray, np.ndarray]:
        """Register bodies allocated in physical slots and their lineages."""
        indices = np.asarray(indices, dtype=np.int32)
        if indices.size == 0:
            return np.empty(0, dtype=np.uint64), np.empty(0, dtype=np.uint64)
        bodies = np.empty(indices.size, dtype=np.uint64)
        lineages = np.empty(indices.size, dtype=np.uint64)
        for row, (slot, lineage) in enumerate(zip(indices.tolist(), lineage_ids[indices].tolist())):
            body = self._allocate(SubjectKind.BODY, tick, int(lineage))
            lineage_subject = self._lineage_node(int(lineage), tick)
            self.body_subject_id[slot] = body
            self.lineage_subject_id[slot] = lineage_subject
            bodies[row] = body
            lineages[row] = lineage_subject
            self._edges[(body, lineage_subject, SubjectEdgeType.DESCENDS_FROM)] = SubjectEdge(
                body, lineage_subject, SubjectEdgeType.DESCENDS_FROM, 1.0, tick
            )
        self.version += 1
        return bodies, lineages

    def mark_dead(self, indices: np.ndarray, tick: int) -> None:
        changed = False
        for slot in np.asarray(indices, dtype=np.int32).tolist():
            subject_id = int(self.body_subject_id[slot])
            if subject_id and subject_id in self.nodes and self.nodes[subject_id].active:
                node = self.nodes[subject_id]
                node.active = False
                node.last_update_tick = tick
                self._active_kind_counts[int(node.kind)] -= 1
                changed = True
        if changed:
            self.version += 1

    def update_groups(self, alive: np.ndarray, group_ids: np.ndarray, tick: int) -> None:
        """Build canonical membership segments and commit them.

        ``group_ids`` are the social detector's internal component tokens;
        graph nodes receive independent IDs and may persist when the component
        is observed again in a later update.
        """
        alive_values = np.asarray(alive, dtype=bool)
        group_values = np.asarray(group_ids, dtype=np.uint64)
        if (
            alive_values.ndim != 1
            or group_values.ndim != 1
            or alive_values.size != self.body_subject_id.size
            or group_values.size != self.body_subject_id.size
        ):
            raise ValueError("group graph inputs must match graph capacity")
        active_slots = np.flatnonzero(alive_values).astype(np.int32)
        active_groups = group_values[active_slots]
        grouped = active_groups != 0
        if not np.any(grouped):
            self.commit_group_membership(
                np.empty(0, dtype=np.uint64),
                np.empty(0, dtype=np.int64),
                np.empty(0, dtype=np.int32),
                np.empty(0, dtype=np.int32),
                tick,
            )
            return
        tokens, inverse = np.unique(active_groups[grouped], return_inverse=True)
        counts = np.bincount(inverse, minlength=tokens.size).astype(np.int32)
        order = np.argsort(inverse, kind="stable")
        members = active_slots[grouped][order]
        starts = np.empty(tokens.size, dtype=np.int64)
        starts[0] = 0
        if tokens.size > 1:
            np.cumsum(counts[:-1], out=starts[1:])
        self.commit_group_membership(tokens, starts, counts, members, tick)

    def commit_group_membership(
        self,
        group_tokens: np.ndarray,
        member_starts: np.ndarray,
        member_counts: np.ndarray,
        member_indices: np.ndarray,
        tick: int,
    ) -> None:
        """Commit pre-segmented membership without repeated active-row scans."""
        tokens = np.asarray(group_tokens, dtype=np.uint64)
        starts = np.asarray(member_starts, dtype=np.int64)
        counts = np.asarray(member_counts, dtype=np.int32)
        members = np.asarray(member_indices, dtype=np.int32)
        if any(value.ndim != 1 for value in (tokens, starts, counts, members)):
            raise ValueError("group membership plan arrays must be one-dimensional")
        if starts.size != tokens.size or counts.size != tokens.size:
            raise ValueError("group membership segment arrays must be aligned")
        if tokens.size:
            expected_starts = np.empty(tokens.size, dtype=np.int64)
            expected_starts[0] = 0
            if tokens.size > 1:
                np.cumsum(counts[:-1], out=expected_starts[1:])
            if (
                np.any(tokens == 0)
                or np.any(tokens[1:] <= tokens[:-1])
                or np.any(counts <= 0)
                or not np.array_equal(starts, expected_starts)
            ):
                raise ValueError("group membership segments are not canonical")
        if int(counts.astype(np.int64).sum()) != members.size:
            raise ValueError("group membership counts do not match member rows")
        if members.size and (
            np.any(members < 0)
            or np.any(members >= self.body_subject_id.size)
            or np.unique(members).size != members.size
        ):
            raise ValueError("group membership contains an invalid or duplicate slot")
        if members.size:
            member_groups = np.repeat(tokens, counts)
            same_group = member_groups[1:] == member_groups[:-1]
            if np.any(same_group & (members[1:] <= members[:-1])):
                raise ValueError("group members must keep ascending slot order per segment")
        if int(tick) < 0:
            raise ValueError("group membership tick must be non-negative")

        observed_groups = {int(token) for token in tokens.tolist()}
        changed = False
        for group_row, token_value in enumerate(tokens.tolist()):
            token = int(token_value)
            if token not in self._group_nodes:
                self._group_nodes[token] = self._allocate(SubjectKind.SOCIAL_GROUP, tick)
                changed = True
            node = self.nodes[self._group_nodes[token]]
            if not node.active:
                node.active = True
                self._active_kind_counts[int(node.kind)] += 1
                self._adjust_active_benefit_summary(node, 1)
                changed = True
            node.last_update_tick = tick
            start = int(starts[group_row])
            count = int(counts[group_row])
            node.member_count = count
            for slot in members[start : start + count].tolist():
                body = int(self.body_subject_id[slot])
                if body:
                    self._edges[(body, node.subject_id, SubjectEdgeType.MEMBER_OF)] = SubjectEdge(
                        body, node.subject_id, SubjectEdgeType.MEMBER_OF, 1.0, tick
                    )
        for token, subject_id in self._group_nodes.items():
            if token not in observed_groups:
                node = self.nodes[subject_id]
                if node.active:
                    self._adjust_active_benefit_summary(node, -1)
                    node.active = False
                    node.last_update_tick = tick
                    node.member_count = 0
                    self._active_kind_counts[int(node.kind)] -= 1
                    changed = True
        if changed or observed_groups:
            self.version += 1

    def social_subject_ids(self, group_tokens: np.ndarray) -> np.ndarray:
        """Resolve detector component tokens to stable social-subject IDs.

        Group tokens are implementation details of ``SocialSystem``.  The
        controller boundary must instead record the candidate graph node that
        supplied guidance, preserving the separation of social and physical
        identity even when detection is recomputed.
        """
        tokens = np.asarray(group_tokens, dtype=np.uint64)
        result = np.zeros(tokens.shape, dtype=np.uint64)
        if tokens.size == 0:
            return result
        for token in np.unique(tokens[tokens != 0]).tolist():
            subject_id = self._group_nodes.get(int(token))
            if subject_id is not None:
                result[tokens == token] = np.uint64(subject_id)
        return result

    def record_benefit_flows(
        self,
        owner_group_tokens: np.ndarray,
        target_group_tokens: np.ndarray,
        amounts: np.ndarray,
        tick: int,
    ) -> None:
        """Attach realized benefit retention/leakage to candidate boundaries.

        Only already-detected social subjects receive measurements.  A flow
        inside one non-zero group is retained benefit; a flow from that group
        to another or to an ungrouped target is outgoing boundary leakage.
        External incoming benefit is tracked separately and does not inflate
        the group's retention numerator.
        """
        owners = np.asarray(owner_group_tokens, dtype=np.uint64)
        targets = np.asarray(target_group_tokens, dtype=np.uint64)
        values = np.asarray(amounts, dtype=np.float64)
        if any(value.ndim != 1 for value in (owners, targets, values)) or not (
            owners.size == targets.size == values.size
        ):
            raise ValueError("benefit flow arrays must be aligned and one-dimensional")
        if np.any(~np.isfinite(values)) or np.any(values < 0.0):
            raise ValueError("benefit flow amounts must be finite and non-negative")
        if values.size == 0:
            return

        changed = False

        def add_by_token(tokens: np.ndarray, selected: np.ndarray, field: str) -> None:
            nonlocal changed
            selected_tokens = tokens[selected]
            selected_values = values[selected]
            if selected_tokens.size == 0:
                return
            unique, inverse = np.unique(selected_tokens, return_inverse=True)
            totals = np.bincount(inverse, weights=selected_values)
            for token, total in zip(unique.tolist(), totals.tolist()):
                subject_id = self._group_nodes.get(int(token))
                if subject_id is None or total <= 0.0:
                    continue
                node = self.nodes[subject_id]
                self._adjust_active_benefit_summary(node, -1)
                setattr(node, field, float(getattr(node, field)) + float(total))
                node.last_update_tick = int(tick)
                self._adjust_active_benefit_summary(node, 1)
                changed = True

        internal = (owners != 0) & (owners == targets)
        external_out = (owners != 0) & (owners != targets)
        external_in = (targets != 0) & (owners != targets)
        add_by_token(owners, internal, "benefit_internal")
        add_by_token(owners, external_out, "benefit_external_out")
        add_by_token(targets, external_in, "benefit_external_in")
        if changed:
            self.version += 1

    @property
    def edges(self) -> tuple[SubjectEdge, ...]:
        return tuple(self._edges.values())

    def summary(self) -> dict[str, int | float]:
        body_count = int(self._active_kind_counts[int(SubjectKind.BODY)])
        lineage_count = int(self._active_kind_counts[int(SubjectKind.GENE_LINEAGE)])
        social_count = int(self._active_kind_counts[int(SubjectKind.SOCIAL_GROUP)])
        internal = max(float(self._active_benefit_internal), 0.0)
        external_out = max(float(self._active_benefit_external_out), 0.0)
        mean_cohesion = (
            self._active_benefit_cohesion_sum / self._active_benefit_subjects
            if self._active_benefit_subjects
            else 0.0
        )
        return {
            "candidate_subjects": body_count + lineage_count + social_count,
            "body_subjects": body_count,
            "lineage_subjects": lineage_count,
            "social_subjects": social_count,
            "subject_edges": len(self._edges),
            "subject_graph_version": self.version,
            "benefit_boundary_subjects": int(self._active_benefit_subjects),
            "benefit_boundary_internal_total": internal,
            "benefit_boundary_external_out_total": external_out,
            "benefit_boundary_weighted_cohesion": (
                internal / (internal + external_out)
                if internal + external_out > 0.0
                else 0.0
            ),
            # Incremental subtraction can leave a few ulps outside the
            # mathematical probability interval after very long runs.
            "benefit_boundary_mean_cohesion": float(np.clip(mean_cohesion, 0.0, 1.0)),
        }
