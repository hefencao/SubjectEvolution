from dataclasses import replace
import copy

import numpy as np
import pytest

from subject_evolution.config import load_config
from subject_evolution.simulation import Simulation
from subject_evolution.social import DeterministicGroupLabelPlanner, SocialSystem
from subject_evolution.subjects import CandidateSubjectGraph, SubjectEdgeType


def _social(capacity: int = 6) -> tuple[SocialSystem, np.ndarray, np.ndarray, np.ndarray]:
    cfg = load_config("configs/mvp_small.json")
    cfg = replace(
        cfg,
        social=replace(
            cfg.social,
            group_min_members=2,
            trust_group_threshold=0.5,
        ),
    )
    social = SocialSystem(cfg, capacity)
    alive = np.asarray([True, True, True, True, True, False])
    stable_ids = np.asarray([101, 102, 103, 104, 105, 0], dtype=np.uint64)
    energy = np.asarray([1.0, 3.0, 2.0, 6.0, 9.0, 0.0], dtype=np.float32)
    social.target[0, 0] = 1
    social.target[1, 0] = 0
    social.target[2, 0] = 3
    social.target[3, 0] = 2
    social.trust[:4, 0] = 0.8
    return social, alive, stable_ids, energy


def test_group_planner_is_pure_and_emits_canonical_segments() -> None:
    social, alive, stable_ids, energy = _social()
    grad_x = np.asarray([1.0, 1.0, 0.0, 0.0, 5.0, 0.0], dtype=np.float32)
    grad_y = np.asarray([0.0, 0.0, 2.0, 2.0, 5.0, 0.0], dtype=np.float32)
    snapshot = social.group_detection_snapshot(
        alive, stable_ids, energy, grad_x, grad_y, tick=4
    )
    target_before = social.target.copy()
    trust_before = social.trust.copy()
    assert not snapshot.relation_targets.flags.writeable
    assert not snapshot.relation_trust.flags.writeable
    with pytest.raises(ValueError):
        snapshot.relation_trust[0, 0] = 0.0

    plan = DeterministicGroupLabelPlanner().plan(snapshot)

    np.testing.assert_array_equal(social.target, target_before)
    np.testing.assert_array_equal(social.trust, trust_before)
    np.testing.assert_array_equal(plan.active_indices, np.arange(5, dtype=np.int32))
    np.testing.assert_array_equal(
        plan.entity_group_ids,
        np.asarray([101, 101, 103, 103, 0], dtype=np.uint64),
    )
    np.testing.assert_array_equal(plan.group_tokens, np.asarray([101, 103], dtype=np.uint64))
    np.testing.assert_array_equal(plan.member_starts, np.asarray([0, 2], dtype=np.int64))
    np.testing.assert_array_equal(plan.member_counts, np.asarray([2, 2], dtype=np.int32))
    np.testing.assert_array_equal(plan.member_indices, np.asarray([0, 1, 2, 3], dtype=np.int32))
    np.testing.assert_allclose(plan.group_direction_x, np.asarray([1.0, 0.0], dtype=np.float32))
    np.testing.assert_allclose(plan.group_direction_y, np.asarray([0.0, 1.0], dtype=np.float32))
    np.testing.assert_allclose(plan.mean_energy, np.asarray([2.0, 4.0], dtype=np.float32))


def test_explicit_group_plan_commit_matches_compatibility_wrapper() -> None:
    planned, alive, stable_ids, energy = _social()
    wrapped = copy.deepcopy(planned)
    grad_x = np.linspace(-1.0, 1.0, alive.size, dtype=np.float32)
    grad_y = grad_x[::-1].copy()

    snapshot = planned.group_detection_snapshot(
        alive, stable_ids, energy, grad_x, grad_y, tick=7
    )
    plan = DeterministicGroupLabelPlanner().plan(snapshot)
    planned_summary = planned.commit_group_plan(plan, alive, stable_ids)
    wrapped_summary = wrapped.update_groups(
        alive, stable_ids, energy, grad_x, grad_y, tick=7
    )

    np.testing.assert_array_equal(planned.group_id, wrapped.group_id)
    np.testing.assert_array_equal(planned.group_age, wrapped.group_age)
    np.testing.assert_array_equal(planned.group_dir_x, wrapped.group_dir_x)
    np.testing.assert_array_equal(planned.group_dir_y, wrapped.group_dir_y)
    np.testing.assert_array_equal(planned_summary.group_ids, wrapped_summary.group_ids)
    np.testing.assert_array_equal(planned_summary.counts, wrapped_summary.counts)
    np.testing.assert_array_equal(planned_summary.mean_energy, wrapped_summary.mean_energy)


def test_group_commit_rejects_stale_entity_identity() -> None:
    social, alive, stable_ids, energy = _social()
    gradient = np.zeros(alive.size, dtype=np.float32)
    plan = DeterministicGroupLabelPlanner().plan(
        social.group_detection_snapshot(
            alive, stable_ids, energy, gradient, gradient, tick=1
        )
    )
    changed_ids = stable_ids.copy()
    changed_ids[0] = 999

    with pytest.raises(ValueError, match="identity is stale"):
        social.commit_group_plan(plan, alive, changed_ids)


def test_candidate_graph_consumes_segments_and_tracks_summary_incrementally() -> None:
    graph = CandidateSubjectGraph(capacity=6)
    indices = np.arange(4, dtype=np.int32)
    lineages = np.arange(11, 17, dtype=np.uint64)
    graph.register_bodies(indices, lineages, tick=0)
    graph.commit_group_membership(
        group_tokens=np.asarray([101, 202], dtype=np.uint64),
        member_starts=np.asarray([0, 2], dtype=np.int64),
        member_counts=np.asarray([2, 2], dtype=np.int32),
        member_indices=np.asarray([0, 1, 2, 3], dtype=np.int32),
        tick=2,
    )

    summary = graph.summary()
    assert summary["body_subjects"] == 4
    assert summary["lineage_subjects"] == 4
    assert summary["social_subjects"] == 2
    assert summary["candidate_subjects"] == 10
    member_edges = [edge for edge in graph.edges if edge.edge_type == SubjectEdgeType.MEMBER_OF]
    assert len(member_edges) == 4

    graph.mark_dead(np.asarray([3], dtype=np.int32), tick=3)
    graph.commit_group_membership(
        group_tokens=np.asarray([202], dtype=np.uint64),
        member_starts=np.asarray([0], dtype=np.int64),
        member_counts=np.asarray([1], dtype=np.int32),
        member_indices=np.asarray([2], dtype=np.int32),
        tick=4,
    )
    summary = graph.summary()
    assert summary["body_subjects"] == 3
    assert summary["social_subjects"] == 1
    assert summary["candidate_subjects"] == 8


def test_candidate_subject_graph_exposes_benefit_boundary_cohesion() -> None:
    graph = CandidateSubjectGraph(4)
    graph.register_bodies(
        np.arange(4, dtype=np.int32),
        np.asarray([1, 2, 3, 4], dtype=np.uint64),
        tick=0,
    )
    graph.update_groups(
        np.ones(4, dtype=bool),
        np.asarray([10, 10, 20, 20], dtype=np.uint64),
        tick=1,
    )

    graph.record_benefit_flows(
        np.asarray([10, 10, 20, 0], dtype=np.uint64),
        np.asarray([10, 20, 0, 10], dtype=np.uint64),
        np.asarray([2.0, 1.0, 3.0, 4.0], dtype=np.float32),
        tick=2,
    )

    summary = graph.summary()
    assert summary["benefit_boundary_subjects"] == 2
    assert summary["benefit_boundary_internal_total"] == 2.0
    assert summary["benefit_boundary_external_out_total"] == 4.0
    assert np.isclose(summary["benefit_boundary_weighted_cohesion"], 1.0 / 3.0)
    assert np.isclose(summary["benefit_boundary_mean_cohesion"], 1.0 / 3.0)


def test_simulation_accepts_a_pluggable_group_label_planner(tmp_path) -> None:
    class RecordingPlanner:
        scientific_safe = True

        def __init__(self) -> None:
            self.calls = 0

        def plan(self, snapshot):
            self.calls += 1
            return DeterministicGroupLabelPlanner().plan(snapshot)

    cfg = load_config("configs/mvp_small.json")
    planner = RecordingPlanner()
    sim = Simulation(cfg, tmp_path / "group-planner", group_label_planner=planner)
    try:
        sim.step()
        assert planner.calls == 1
        assert sim.last_group_plan.tick == 0
        np.testing.assert_array_equal(
            sim.last_group_plan.entity_group_ids,
            sim.social.group_id[sim.last_group_plan.active_indices],
        )
    finally:
        sim.metrics.close()
