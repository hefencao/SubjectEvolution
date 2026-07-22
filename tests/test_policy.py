from __future__ import annotations

import numpy as np

from subject_evolution.config import load_config
from subject_evolution.information import InformationObservation
from subject_evolution.policy import Action, ParametricPolicy


def _information(count: int) -> InformationObservation:
    return InformationObservation(
        signals=np.asarray([[0.9, 0.4, 0.7]] * count, dtype=np.float32),
        signal_mask=np.ones((count, 3), dtype=bool),
        signal_age=np.zeros((count, 3), dtype=np.float32),
        messages=np.empty((count, 0, 3), dtype=np.float32),
        message_mask=np.empty((count, 0), dtype=bool),
        message_age=np.empty((count, 0), dtype=np.float32),
        message_confidence=np.empty((count, 0), dtype=np.float32),
        message_source_id=np.empty((count, 0), dtype=np.uint64),
        message_corruption=np.empty((count, 0), dtype=np.uint8),
        partner_energy=np.empty((count, 0), dtype=np.float32),
        partner_group_match=np.empty((count, 0), dtype=bool),
        partner_mask=np.empty((count, 0), dtype=bool),
        uncertainty=np.asarray([[0.2, 0.3, 0.4]] * count, dtype=np.float32),
    )


def test_action_preferences_are_genome_data_not_fixed_policy_coefficients() -> None:
    cfg = load_config("configs/mvp_small.json")
    policy = ParametricPolicy(cfg)
    count = 2
    active = np.arange(count, dtype=np.int32)
    genotype = np.zeros((count, policy.GENOME_SIZE), dtype=np.float32)
    common = dict(
        active=active,
        stable_ids=np.asarray([101, 102], dtype=np.uint64),
        energy=np.full(count, 4.0, dtype=np.float32),
        integrity=np.ones(count, dtype=np.float32),
        fertility=np.ones(count, dtype=np.float32),
        memory=np.asarray([[0.5, 0.1, 0.2, 0.3]] * count, dtype=np.float32),
        local_resources=np.asarray([[2.0, 0.0, 0.0, 0.0]] * count, dtype=np.float32),
        resource_gradient=(np.zeros(count, dtype=np.float32), np.zeros(count, dtype=np.float32)),
        danger_gradient=(np.zeros(count, dtype=np.float32), np.zeros(count, dtype=np.float32)),
        group_direction=(np.zeros(count, dtype=np.float32), np.zeros(count, dtype=np.float32)),
        partners=np.empty((count, 0), dtype=np.int32),
        info=_information(count),
        run_seed=7,
        tick=3,
    )

    neutral = policy.decide(genotype=genotype, **common)
    np.testing.assert_array_equal(neutral.logits, np.zeros((count, len(Action)), dtype=np.float32))

    harvest_bias = (
        policy.MORPHOLOGY_TRAITS
        + int(Action.HARVEST) * policy.STRATEGY_FEATURES
    )
    rest_energy = (
        policy.MORPHOLOGY_TRAITS
        + int(Action.REST) * policy.STRATEGY_FEATURES
        + policy.FEATURE_NAMES.index("energy")
    )
    genotype[0, harvest_bias] = 1.25
    genotype[1, rest_energy] = -0.75
    evolved = policy.decide(genotype=genotype, **common)

    assert evolved.logits[0, Action.HARVEST] == np.float32(1.25)
    assert evolved.logits[1, Action.REST] == np.float32(-0.6)
    unchanged = evolved.logits.copy()
    unchanged[0, Action.HARVEST] = 0.0
    unchanged[1, Action.REST] = 0.0
    np.testing.assert_array_equal(unchanged, np.zeros_like(unchanged))
