from pathlib import Path
import json
import numpy as np

from subject_evolution import __version__
from subject_evolution.config import load_config
from subject_evolution.counterfactual import run_paired
from subject_evolution.information import InformationSystem
from subject_evolution.simulation import Simulation


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
    assert metadata["version"] == __version__
