from pathlib import Path
from dataclasses import replace
import json
import numpy as np

from subject_evolution import __version__
from subject_evolution.config import load_config
from subject_evolution.counterfactual import run_paired
from subject_evolution.information import InformationSystem
from subject_evolution.random_api import RandomContext, Stream, uniform01
from subject_evolution.simulation import Simulation
from subject_evolution.social import SocialSystem


def _config(tmp_path: Path) -> Path:
    raw = {
        "run": {"seed": 42, "ticks": 4, "metrics_period": 1, "checkpoint_period": 100},
        "world": {"width": 32.0, "height": 32.0, "grid_x": 8, "grid_y": 8, "initial_entities": 64, "max_entities": 96, "periodic": True},
        "environment": {"resource_regeneration": [0.03, 0.01, 0.01, 0.005], "resource_capacity": [10.0, 7.0, 5.0, 3.0], "season_period": 100, "season_amplitude": 0.2, "signal_decay": 0.08, "signal_diffusion": 0.1},
        "entities": {"relation_slots": 4, "maintenance_cost": 0.01, "movement_cost": 0.005, "signal_cost": 0.01, "share_amount": 0.1, "harvest_rate": 0.2, "reproduction_threshold": 2.8, "reproduction_cost": 1.4, "initial_energy": 1.8, "max_energy": 5.0, "max_age": 500},
        "information": {"channel_loss": 0.1, "receiver_noise": 0.05, "classification_error": 0.02, "memory_decay": 0.01, "max_signal_delay": 2, "direct_message_capacity": 3, "source_noise": 0.0},
        "policy": {"temperature": 0.8, "partner_samples": 2, "mutation_std": 0.03, "group_influence": 0.3},
        "social": {"group_update_period": 2, "trust_group_threshold": 0.5, "group_min_members": 3, "relation_decay": 0.001, "trust_gain_share": 0.1, "trust_loss_failed": 0.02}
    }
    path = tmp_path / "config.json"
    path.write_text(json.dumps(raw), encoding="utf-8")
    return path


def test_world_invariants(tmp_path):
    cfg = load_config(_config(tmp_path))
    sim = Simulation(cfg, tmp_path / "run")
    for _ in range(4):
        sim.step()
        alive = sim.entities.alive
        assert np.all(sim.entities.energy[alive] >= 0.0)
        assert np.all(sim.environment.resources >= 0.0)
        assert np.all(sim.environment.resources <= sim.environment.capacity + 1e-5)
        assert np.all(sim.entities.x[alive] >= 0.0)
        assert np.all(sim.entities.x[alive] < cfg.world.width)
        assert np.all(sim.entities.y[alive] >= 0.0)
        assert np.all(sim.entities.y[alive] < cfg.world.height)
    sim.metrics.close()


def test_reproducible_first_steps(tmp_path):
    cfg = load_config(_config(tmp_path))
    sim_a = Simulation(cfg, tmp_path / "a")
    sim_b = Simulation(cfg, tmp_path / "b")
    for _ in range(3):
        sim_a.step()
        sim_b.step()
    assert np.array_equal(sim_a.entities.alive, sim_b.entities.alive)
    assert np.allclose(sim_a.entities.x, sim_b.entities.x)
    assert np.allclose(sim_a.entities.energy, sim_b.entities.energy)
    sim_a.metrics.close()
    sim_b.metrics.close()


def test_candidate_subjects_are_distinct_from_entities(tmp_path):
    cfg = load_config(_config(tmp_path))
    sim = Simulation(cfg, tmp_path / "run")
    active = np.flatnonzero(sim.entities.alive)
    assert np.all(sim.entities.primary_subject_id[active] != sim.entities.entity_id[active])
    assert sim.subjects.summary()["body_subjects"] == active.size
    sim.metrics.close()


def test_direct_messages_have_fixed_masked_observation(tmp_path):
    cfg = load_config(_config(tmp_path))
    information = InformationSystem(cfg)
    information.emit_direct(
        source_ids=np.asarray([11], dtype=np.uint64),
        receiver_ids=np.asarray([22], dtype=np.uint64),
        payloads=np.asarray([[10.0, 2.0, 1.0]], dtype=np.float32),
        confidences=np.asarray([1.0], dtype=np.float32),
        run_seed=cfg.run.seed,
        tick=0,
    )
    observed = information.observe(
        active=np.asarray([1], dtype=np.int32),
        stable_ids=np.asarray([11, 22], dtype=np.uint64),
        cell_ids=np.asarray([0], dtype=np.int32),
        partners=np.empty((1, 0), dtype=np.int32),
        energy=np.asarray([1.0, 1.0], dtype=np.float32),
        group_id=np.zeros(2, dtype=np.uint64),
        sensor_quality=np.asarray([1.0, 2.0], dtype=np.float32),
        run_seed=cfg.run.seed,
        tick=0,
    )
    assert observed.message_mask.shape == (1, cfg.information.direct_message_capacity)
    assert observed.message_mask[0, 0]
    assert observed.message_source_id[0, 0] == 11
    assert np.all(observed.messages[0, 0] >= 0.0)


def test_batched_direct_message_receipt_is_reproducible_and_capacity_limited(tmp_path):
    cfg = load_config(_config(tmp_path))
    cfg = replace(
        cfg,
        information=replace(cfg.information, direct_message_capacity=3, max_signal_delay=0),
    )
    source_ids = np.arange(100, 116, dtype=np.uint64)
    receiver_ids = np.full(source_ids.size, 22, dtype=np.uint64)
    payloads = np.tile(np.asarray([[0.8, 0.4, 0.2]], dtype=np.float32), (source_ids.size, 1))
    confidences = np.ones(source_ids.size, dtype=np.float32)
    active = np.asarray([0, 1], dtype=np.int32)
    stable_ids = np.asarray([11, 22], dtype=np.uint64)
    quality = np.ones(2, dtype=np.float32)

    systems = [InformationSystem(cfg), InformationSystem(cfg)]
    received = []
    for system in systems:
        system.emit_direct(source_ids, receiver_ids, payloads, confidences, cfg.run.seed, tick=0)
        assert len(system.pending_messages) == 1
        assert system.pending_messages[0].source_ids.size == source_ids.size
        received.append(system._receive_direct(active, stable_ids, quality, cfg.run.seed, tick=1))

    for left, right in zip(received[0], received[1]):
        np.testing.assert_array_equal(left, right)
    message_mask = received[0][1]
    message_sources = received[0][4]
    assert int(message_mask[1].sum()) <= cfg.information.direct_message_capacity
    accepted_sources = message_sources[1, message_mask[1]]
    assert np.all(np.diff(accepted_sources.astype(np.int64)) >= 0)


def test_direct_message_queue_buckets_by_receive_tick(tmp_path):
    cfg = load_config(_config(tmp_path))
    cfg = replace(cfg, information=replace(cfg.information, max_signal_delay=2))
    information = InformationSystem(cfg)
    source_ids = np.arange(100, 124, dtype=np.uint64)
    receiver_ids = np.full(source_ids.size, 22, dtype=np.uint64)
    payloads = np.ones((source_ids.size, 3), dtype=np.float32)
    confidences = np.ones(source_ids.size, dtype=np.float32)
    information.emit_direct(source_ids, receiver_ids, payloads, confidences, cfg.run.seed, tick=0)

    delay_ctx = RandomContext(cfg.run.seed, 0, phase=31, stream=Stream.SIGNAL_CHANNEL)
    expected_delays = np.floor(
        uniform01(delay_ctx, source_ids, draw_index=110) * (cfg.information.max_signal_delay + 1)
    ).astype(np.int32)
    assert sum(batch.source_ids.size for batch in information.pending_messages) == source_ids.size
    assert len(information.pending_messages) == np.unique(expected_delays).size
    for batch in information.pending_messages:
        positions = (batch.source_ids - source_ids[0]).astype(np.int32)
        assert np.all(expected_delays[positions] == batch.receive_tick)

    active = np.asarray([0], dtype=np.int32)
    stable_ids = np.asarray([22], dtype=np.uint64)
    quality = np.ones(1, dtype=np.float32)
    for observation_tick in range(cfg.information.max_signal_delay + 1):
        information._receive_direct(active, stable_ids, quality, cfg.run.seed, observation_tick)
        assert all(batch.receive_tick > observation_tick for batch in information.pending_messages)
    assert not information.pending_messages


def test_batched_share_relations_match_scalar_reference(tmp_path):
    cfg = load_config(_config(tmp_path))
    actual = SocialSystem(cfg, capacity=16)
    expected = SocialSystem(cfg, capacity=16)

    # Exercise existing links, first-empty insertion, and weakest-slot
    # replacement while several owners receive multiple ordered updates.
    seed_targets = np.asarray(
        [
            [1, 2, 3, 4],
            [0, 2, 3, 4],
            [0, 1, 3, 4],
        ],
        dtype=np.int32,
    )
    seed_trust = np.asarray(
        [
            [0.8, 0.1, 0.4, 0.2],
            [0.3, 0.9, 0.2, 0.1],
            [0.7, 0.2, 0.6, 0.1],
        ],
        dtype=np.float32,
    )
    for system in (actual, expected):
        system.target[:3] = seed_targets
        system.trust[:3] = seed_trust
        system.familiarity[:3] = 0.15
        system.last_interaction[:3] = 6

    owners = np.asarray([0, 5, 0, 2, 7, 0, 5, -1, 3], dtype=np.int32)
    targets = np.asarray([5, 0, 2, 0, 0, 6, 1, 3, 3], dtype=np.int32)
    success = np.asarray([True, False, True, True, False, True, True, True, False])
    tick = 17

    gain = cfg.social.trust_gain_share
    loss = cfg.social.trust_loss_failed
    for owner, target, ok in zip(owners, targets, success):
        expected._update_one(int(owner), int(target), gain if ok else -loss, tick)
        if ok:
            expected._update_one(int(target), int(owner), gain * 0.5, tick)

    actual.record_shares(owners, targets, success, tick)

    np.testing.assert_array_equal(actual.target, expected.target)
    np.testing.assert_array_equal(actual.last_interaction, expected.last_interaction)
    np.testing.assert_allclose(actual.trust, expected.trust, rtol=0.0, atol=0.0)
    np.testing.assert_allclose(actual.familiarity, expected.familiarity, rtol=0.0, atol=0.0)


def test_lazy_relation_decay_matches_eager_tick_schedule(tmp_path):
    cfg = load_config(_config(tmp_path))
    cfg = replace(cfg, social=replace(cfg.social, relation_decay=0.04, group_min_members=2))
    actual = SocialSystem(cfg, capacity=8)
    expected = SocialSystem(cfg, capacity=8)
    alive = np.ones(8, dtype=bool)
    stable_ids = np.arange(1, 9, dtype=np.uint64)
    energy = np.ones(8, dtype=np.float32)
    gradient = np.zeros(8, dtype=np.float32)

    def scalar_share(system: SocialSystem, owners, targets, success, tick: int) -> None:
        for owner, target, ok in zip(owners, targets, success):
            system._update_one(
                int(owner),
                int(target),
                cfg.social.trust_gain_share if ok else -cfg.social.trust_loss_failed,
                tick,
            )
            if ok:
                system._update_one(int(target), int(owner), cfg.social.trust_gain_share * 0.5, tick)

    first_owners = np.asarray([0, 2], dtype=np.int32)
    first_targets = np.asarray([1, 3], dtype=np.int32)
    first_success = np.asarray([True, False])
    actual.record_shares(first_owners, first_targets, first_success, tick=0)
    scalar_share(expected, first_owners, first_targets, first_success, tick=0)
    expected.decay(alive)  # End of tick 0.
    expected.decay(alive)  # End of tick 1.
    expected.decay(alive)  # End of tick 2.

    second_owners = np.asarray([0, 3], dtype=np.int32)
    second_targets = np.asarray([1, 2], dtype=np.int32)
    second_success = np.asarray([True, True])
    actual.record_shares(second_owners, second_targets, second_success, tick=3)
    scalar_share(expected, second_owners, second_targets, second_success, tick=3)
    expected.decay(alive)  # End of tick 3.

    # The group boundary materializes the deferred value through tick 3.
    actual.update_groups(alive, stable_ids, energy, gradient, gradient, tick=3)
    expected.update_groups(alive, stable_ids, energy, gradient, gradient, tick=3)
    np.testing.assert_array_equal(actual.target, expected.target)
    np.testing.assert_allclose(actual.trust, expected.trust, rtol=0.0, atol=2e-7)
    np.testing.assert_allclose(actual.familiarity, expected.familiarity, rtol=0.0, atol=2e-7)
    np.testing.assert_array_equal(actual.group_id, expected.group_id)


def test_paired_counterfactual_uses_same_initial_snapshot(tmp_path):
    cfg = load_config(_config(tmp_path))
    sim = Simulation(cfg, tmp_path / "paired" / "baseline")
    identical_branch = sim.clone(tmp_path / "paired" / "identical")
    sim.step()
    identical_branch.step()
    assert np.array_equal(sim.entities.alive, identical_branch.entities.alive)
    assert np.allclose(sim.entities.energy, identical_branch.entities.energy)
    sim.metrics.close()
    identical_branch.metrics.close()

    sim = Simulation(cfg, tmp_path / "paired" / "baseline-run")
    result = run_paired(sim, "disable-social-control", tmp_path / "paired")
    summary = tmp_path / "paired" / "counterfactual_summary.json"
    assert summary.exists()
    assert result.baseline["tick"] == cfg.run.ticks
    assert result.intervention["tick"] == cfg.run.ticks


def test_run_metadata_uses_package_version(tmp_path):
    cfg = load_config(_config(tmp_path))
    output = tmp_path / "run"
    Simulation(cfg, output).run()
    metadata = json.loads((output / "run_metadata.json").read_text(encoding="utf-8"))
    summary = json.loads((output / "summary.json").read_text(encoding="utf-8"))
    assert metadata["version"] == __version__
    assert metadata["execution_backend"] == "cpu"
    assert metadata["control"]["arbiter"] == "SingleProposalControlArbiter"
    assert metadata["control"]["heuristic_social_guidance_enabled"] is False
    assert metadata["control"]["heuristic_guidance_actions"] == 0
    assert summary["window_seconds_per_tick"] >= 0.0


def test_run_writes_a_final_metric_outside_the_reporting_period(tmp_path):
    cfg = load_config(_config(tmp_path))
    cfg = replace(cfg, run=replace(cfg.run, ticks=3, metrics_period=2))
    output = tmp_path / "final-metric"

    result = Simulation(cfg, output).run()

    summary = json.loads((output / "summary.json").read_text(encoding="utf-8"))
    metadata = json.loads((output / "run_metadata.json").read_text(encoding="utf-8"))
    assert result["tick"] == cfg.run.ticks
    assert summary["tick"] == cfg.run.ticks
    assert metadata["ticks_completed"] == cfg.run.ticks
    assert metadata["final"]["tick"] == cfg.run.ticks
