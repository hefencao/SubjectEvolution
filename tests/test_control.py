from dataclasses import replace

import numpy as np
import pytest

from subject_evolution.control import (
    ArbitrationResult,
    AutonomyRecoveryArbiter,
    ControllerKind,
    HeuristicSocialGuidanceArbiter,
    SingleProposalControlArbiter,
    autonomy_recovery_control_proposal,
    body_control_proposal,
    social_guidance_control_proposal,
)
from subject_evolution.config import load_config
from subject_evolution.policy import Action, PolicyDecision
from subject_evolution.simulation import Simulation


def _decision(count: int) -> PolicyDecision:
    return PolicyDecision(
        action=np.zeros(count, dtype=np.int16),
        probability=np.ones(count, dtype=np.float32),
        entropy=np.zeros(count, dtype=np.float32),
        direction_x=np.zeros(count, dtype=np.float32),
        direction_y=np.zeros(count, dtype=np.float32),
        selected_partner=np.full(count, -1, dtype=np.int32),
        logits=np.zeros((count, 8), dtype=np.float32),
    )


def test_single_body_control_proposal_preserves_decision_and_provenance() -> None:
    proposal = body_control_proposal(
        np.asarray([4, 2], dtype=np.int32),
        np.asarray([901, 902], dtype=np.uint64),
        _decision(2),
        tick=7,
    )

    result = SingleProposalControlArbiter().arbitrate((proposal,))

    assert result.decision is proposal.decision
    np.testing.assert_array_equal(result.proposer_subject_id, np.asarray([901, 902], dtype=np.uint64))
    np.testing.assert_array_equal(
        result.controller_kind,
        np.asarray([ControllerKind.BODY, ControllerKind.BODY], dtype=np.uint8),
    )
    np.testing.assert_array_equal(result.contributor_subject_ids[:, 0], result.proposer_subject_id)
    np.testing.assert_array_equal(
        result.contributor_controller_kinds[:, 0],
        result.controller_kind,
    )
    np.testing.assert_array_equal(result.contribution_weights, np.ones((2, 1), dtype=np.float32))


def test_single_control_arbiter_rejects_duplicate_carrier_proposals() -> None:
    proposal = body_control_proposal(
        np.asarray([4, 4], dtype=np.int32),
        np.asarray([901, 902], dtype=np.uint64),
        _decision(2),
        tick=7,
    )

    with pytest.raises(ValueError, match="one proposal per carrier"):
        SingleProposalControlArbiter(validate_unique_carriers=True).arbitrate((proposal,))


def test_heuristic_social_guidance_only_blends_resource_move_direction() -> None:
    decision = _decision(2)
    decision.action[:] = np.asarray([Action.MOVE_RESOURCE, Action.HARVEST], dtype=np.int16)
    decision.direction_x[:] = 1.0
    body = body_control_proposal(
        np.asarray([4, 2], dtype=np.int32),
        np.asarray([901, 902], dtype=np.uint64),
        decision,
        tick=7,
    )
    social = social_guidance_control_proposal(
        body,
        np.asarray([801, 802], dtype=np.uint64),
        (np.asarray([0.0, 0.0], dtype=np.float32), np.asarray([1.0, 1.0], dtype=np.float32)),
        guidance_weight=0.25,
    )

    result = HeuristicSocialGuidanceArbiter().arbitrate((body, social))

    np.testing.assert_allclose(result.decision.direction_x, np.asarray([0.9486833, 1.0], dtype=np.float32))
    np.testing.assert_allclose(result.decision.direction_y, np.asarray([0.31622776, 0.0], dtype=np.float32))
    np.testing.assert_array_equal(result.heuristic_applied, np.asarray([True, False]))
    np.testing.assert_array_equal(
        result.contributor_subject_ids,
        np.asarray([[901, 801], [902, 802]], dtype=np.uint64),
    )
    np.testing.assert_array_equal(
        result.contributor_controller_kinds,
        np.asarray(
            [[ControllerKind.BODY, ControllerKind.SOCIAL]] * 2,
            dtype=np.uint8,
        ),
    )
    np.testing.assert_allclose(
        result.contribution_weights,
        np.asarray([[0.75, 0.25], [1.0, 0.0]], dtype=np.float32),
    )


def test_autonomy_recovery_overlays_only_eligible_restored_rows() -> None:
    decision = _decision(4)
    decision.action[:] = np.asarray(
        [Action.MOVE_SOCIAL, Action.FLEE, Action.REST, Action.REST],
        dtype=np.int16,
    )
    body = body_control_proposal(
        np.asarray([4, 2, 7, 9], dtype=np.int32),
        np.asarray([901, 902, 903, 904], dtype=np.uint64),
        decision,
        tick=7,
    )
    autonomy = autonomy_recovery_control_proposal(
        body,
        np.asarray([41, 22, 73, 94], dtype=np.uint64),
        np.ones(4, dtype=bool),
        np.asarray([4.0, 0.2, 0.2, 4.0], dtype=np.float32),
        np.asarray([1.0, 1.0, 0.0, 0.0], dtype=np.float32),
        (
            np.asarray([1.0, 0.0, 0.0, 1.0], dtype=np.float32),
            np.asarray([0.0, 1.0, 0.0, 0.0], dtype=np.float32),
        ),
        run_seed=42,
        max_energy=5.0,
        activation_energy_fraction=0.35,
        harvest_threshold=0.05,
    )

    result = AutonomyRecoveryArbiter(SingleProposalControlArbiter()).arbitrate(
        (body, autonomy)
    )

    np.testing.assert_array_equal(
        result.autonomy_applied,
        np.asarray([True, False, True, False]),
    )
    np.testing.assert_array_equal(
        result.decision.action,
        np.asarray([Action.HARVEST, Action.FLEE, Action.MOVE_RESOURCE, Action.REST]),
    )
    np.testing.assert_array_equal(
        result.controller_kind,
        np.asarray(
            [ControllerKind.AUTONOMY, ControllerKind.BODY, ControllerKind.AUTONOMY, ControllerKind.BODY],
            dtype=np.uint8,
        ),
    )
    np.testing.assert_array_equal(
        result.contributor_controller_kinds,
        np.asarray(
            [[ControllerKind.BODY, ControllerKind.AUTONOMY]] * 4,
            dtype=np.uint8,
        ),
    )
    np.testing.assert_allclose(
        result.contribution_weights,
        np.asarray(
            [[0.0, 1.0], [1.0, 0.0], [0.0, 1.0], [1.0, 0.0]],
            dtype=np.float32,
        ),
    )


def test_simulation_wires_opt_in_social_guidance_to_stable_social_subjects(tmp_path) -> None:
    cfg = load_config("configs/mvp_small.json")
    cfg = replace(
        cfg,
        control=replace(
            cfg.control,
            heuristic_social_guidance=True,
            heuristic_social_guidance_weight=0.25,
        ),
    )
    sim = Simulation(cfg, tmp_path / "heuristic-guidance")
    active = np.flatnonzero(sim.entities.alive).astype(np.int32)
    group_token = sim.entities.entity_id[active[0]]
    sim.social.group_id[active] = group_token
    sim.social.group_dir_x[active] = 0.0
    sim.social.group_dir_y[active] = 1.0
    sim.subjects.update_groups(sim.entities.alive, sim.social.group_id, tick=0)

    def resource_moves(**kwargs):
        decision = _decision(kwargs["active"].size)
        decision.action.fill(Action.MOVE_RESOURCE)
        decision.direction_x.fill(1.0)
        return decision

    sim.policy.decide = resource_moves
    try:
        sim.step()
        assert sim.last_intents is not None
        assert sim.last_intents.heuristic_control is not None
        assert np.all(sim.last_intents.heuristic_control)
        assert sim.last_intents.contributor_subject_ids is not None
        assert np.all(sim.last_intents.contributor_subject_ids[:, 1] != 0)
        assert sim.heuristic_guidance_actions == active.size
    finally:
        sim.metrics.close()


def test_simulation_accepts_a_pluggable_control_arbiter(tmp_path) -> None:
    class RecordingArbiter:
        calls = 0

        def arbitrate(self, proposals):
            self.calls += 1
            assert len(proposals) == 1
            proposal = proposals[0]
            return ArbitrationResult(
                decision=proposal.decision,
                proposer_subject_id=proposal.proposer_subject_id,
                controller_kind=proposal.controller_kind,
            )

    arbiter = RecordingArbiter()
    sim = Simulation(load_config("configs/mvp_small.json"), tmp_path / "custom-arbiter", control_arbiter=arbiter)
    try:
        sim.step()
        assert arbiter.calls == 1
        assert sim.last_intents is not None
        np.testing.assert_array_equal(
            sim.last_intents.proposer_subject_id,
            sim.entities.primary_subject_id[sim.last_intents.carrier_index],
        )
    finally:
        sim.metrics.close()
