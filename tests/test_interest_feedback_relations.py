from __future__ import annotations

from dataclasses import asdict, replace
from pathlib import Path

import numpy as np

from se.cfg import load_config, validate_config
from se.config_identity import strip_inactive_extensions
from se.subjects.social import SocialSystem, build_share_relation_update_plan

ROOT = Path(__file__).resolve().parents[1]


def base_config():
    return load_config(ROOT / "configs" / "d1_elastic_capacities_smoke.json")


def feedback_config():
    cfg = base_config()
    cfg = replace(
        cfg,
        social=replace(
            cfg.social,
            relation_update_schema="delayed-material-interest-v1",
            interest_feedback_window_ticks=4,
            interest_feedback_learning_rate=0.2,
            interest_feedback_min_material=0.5,
        ),
    )
    validate_config(cfg)
    return cfg


def test_legacy_relation_schema_keeps_fixed_share_gain() -> None:
    cfg = base_config()
    plan = build_share_relation_update_plan(
        cfg,
        rows=np.asarray([0], dtype=np.int32),
        owners=np.asarray([0], dtype=np.int32),
        targets=np.asarray([1], dtype=np.int32),
        success=np.asarray([True]),
        eligible=np.asarray([True]),
        tick=1,
    )
    assert plan.size == 2
    assert float(plan.trust_delta[0]) == np.float32(cfg.social.trust_gain_share)
    assert float(plan.trust_delta[1]) == np.float32(cfg.social.trust_gain_share * 0.5)


def test_delayed_material_interest_has_no_immediate_trust_gain() -> None:
    cfg = feedback_config()
    social = SocialSystem(cfg, 4)
    social.set_effective_capacities(
        np.asarray([0, 1], dtype=np.int32), np.asarray([2, 2], dtype=np.int32)
    )
    plan = build_share_relation_update_plan(
        cfg,
        rows=np.asarray([0], dtype=np.int32),
        owners=np.asarray([0], dtype=np.int32),
        targets=np.asarray([1], dtype=np.int32),
        success=np.asarray([True]),
        eligible=np.asarray([True]),
        tick=1,
    )
    np.testing.assert_array_equal(plan.trust_delta, 0.0)
    social.apply_relation_updates(plan)
    social.record_material_interest_feedback(
        np.asarray([0], dtype=np.int32),
        np.asarray([1], dtype=np.int32),
        np.asarray([cfg.entities.share_amount], dtype=np.float32),
        np.zeros((1, 4), dtype=np.float32),
        np.asarray([True]),
        tick=1,
    )
    np.testing.assert_array_equal(social.trust[:2], 0.0)
    assert social.settle_interest_feedback(3) == 0
    assert social.settle_interest_feedback(4) == 2
    forward = social._relation_slot(0, 1)
    reverse = social._relation_slot(1, 0)
    assert forward >= 0 and reverse >= 0
    assert float(social.trust[0, forward]) == 0.0
    assert float(social.trust[1, reverse]) > 0.0
    assert social.interest_feedback_positive == 1
    assert social.interest_feedback_negative == 0
    assert social.interest_feedback_neutral == 1
    assert social.group_labels_dirty


def test_reciprocal_material_balance_settles_neutral_without_fixed_reward() -> None:
    cfg = feedback_config()
    social = SocialSystem(cfg, 4)
    social.set_effective_capacities(
        np.asarray([0, 1], dtype=np.int32), np.asarray([2, 2], dtype=np.int32)
    )
    plan = build_share_relation_update_plan(
        cfg,
        rows=np.asarray([0, 1], dtype=np.int32),
        owners=np.asarray([0, 1], dtype=np.int32),
        targets=np.asarray([1, 0], dtype=np.int32),
        success=np.asarray([True, True]),
        eligible=np.asarray([True, True]),
        tick=1,
    )
    social.apply_relation_updates(plan)
    social.record_material_interest_feedback(
        np.asarray([0, 1], dtype=np.int32),
        np.asarray([1, 0], dtype=np.int32),
        np.asarray([cfg.entities.share_amount, cfg.entities.share_amount], dtype=np.float32),
        np.zeros((2, 4), dtype=np.float32),
        np.asarray([True, True]),
        tick=1,
    )
    assert social.settle_interest_feedback(4) == 2
    assert float(social.trust[0, social._relation_slot(0, 1)]) > 0.0
    assert float(social.trust[1, social._relation_slot(1, 0)]) > 0.0
    assert social.interest_feedback_positive == 2


def test_inactive_interest_feedback_fields_do_not_change_frozen_identity() -> None:
    cfg = base_config()
    payload = asdict(cfg)
    stripped = strip_inactive_extensions(payload)
    social = stripped["social"]
    assert "relation_update_schema" not in social
    assert "interest_feedback_window_ticks" not in social
    assert "interest_feedback_learning_rate" not in social
    assert "interest_feedback_min_material" not in social


def test_interest_feedback_checkpoint_round_trip(tmp_path: Path) -> None:
    from se.runtime.sim import Simulation

    cfg = feedback_config()
    cfg = replace(
        cfg,
        run=replace(
            cfg.run,
            ticks=4,
            metrics_period=4,
            checkpoint_period=99,
            full_checkpoint_enabled=False,
            validation_mode=False,
        ),
        world=replace(cfg.world, initial_entities=16, max_entities=24),
    )
    simulation = Simulation(cfg, tmp_path / "source", backend="cpu")
    simulation.run(until_tick=4)
    checkpoint = tmp_path / "feedback.sechk"
    simulation.save_full_checkpoint(checkpoint)
    restored = Simulation.from_checkpoint(checkpoint, tmp_path / "restored", backend="cpu")
    np.testing.assert_array_equal(restored.social.interest_given, simulation.social.interest_given)
    np.testing.assert_array_equal(restored.social.interest_received, simulation.social.interest_received)
    np.testing.assert_array_equal(
        restored.social.interest_window_start, simulation.social.interest_window_start
    )
    assert restored.social.interest_feedback_settlements == simulation.social.interest_feedback_settlements
