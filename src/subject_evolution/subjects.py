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
        return subject_id

    def _lineage_node(self, lineage_id: int, tick: int) -> int:
        node = self._lineage_nodes.get(lineage_id)
        if node is None:
            node = self._allocate(SubjectKind.GENE_LINEAGE, tick, lineage_id)
            self._lineage_nodes[lineage_id] = node
        return node

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
            if subject_id and subject_id in self.nodes:
                self.nodes[subject_id].active = False
                self.nodes[subject_id].last_update_tick = tick
                changed = True
        if changed:
            self.version += 1

    def update_groups(self, alive: np.ndarray, group_ids: np.ndarray, tick: int) -> None:
        """Commit group membership at a graph-version boundary.

        ``group_ids`` are the social detector's internal component tokens;
        graph nodes receive independent IDs and may persist when the component
        is observed again in a later update.
        """
        active_slots = np.flatnonzero(alive)
        observed_groups = {int(group) for group in group_ids[active_slots].tolist() if group}
        changed = False
        for token in observed_groups:
            if token not in self._group_nodes:
                self._group_nodes[token] = self._allocate(SubjectKind.SOCIAL_GROUP, tick)
                changed = True
            node = self.nodes[self._group_nodes[token]]
            node.active = True
            node.last_update_tick = tick
            node.member_count = int(np.count_nonzero(group_ids[active_slots] == token))
            members = active_slots[group_ids[active_slots] == token]
            for slot in members.tolist():
                body = int(self.body_subject_id[slot])
                if body:
                    self._edges[(body, node.subject_id, SubjectEdgeType.MEMBER_OF)] = SubjectEdge(
                        body, node.subject_id, SubjectEdgeType.MEMBER_OF, 1.0, tick
                    )
        for token, subject_id in self._group_nodes.items():
            if token not in observed_groups:
                node = self.nodes[subject_id]
                if node.active:
                    node.active = False
                    node.last_update_tick = tick
                    node.member_count = 0
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

    @property
    def edges(self) -> tuple[SubjectEdge, ...]:
        return tuple(self._edges.values())

    def summary(self) -> dict[str, int]:
        active = [node for node in self.nodes.values() if node.active]
        return {
            "candidate_subjects": len(active),
            "body_subjects": sum(node.kind == SubjectKind.BODY for node in active),
            "lineage_subjects": sum(node.kind == SubjectKind.GENE_LINEAGE for node in active),
            "social_subjects": sum(node.kind == SubjectKind.SOCIAL_GROUP for node in active),
            "subject_edges": len(self._edges),
            "subject_graph_version": self.version,
        }
