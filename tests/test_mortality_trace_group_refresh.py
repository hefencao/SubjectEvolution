from __future__ import annotations

from dataclasses import replace
from pathlib import Path
import tempfile

import numpy as np

from subject_evolution.config import load_config, validate_config
from subject_evolution.environment import Environment
from subject_evolution.gpu_environment import DeviceEnvironment
from subject_evolution.social import SocialSystem, ungrouped_group_label_plan
from subject_evolution.simulation import Simulation


ROOT = Path(__file__).resolve().parents[1]


def base_config():
    return load_config(
        ROOT
        / "configs"
        / "mvp_short_latent_l2_memory_topk_inherited_heterogeneous_budget_matched_costed_transfer_local_culture_120.json"
    )


def trace_config():
    cfg = base_config()
    return replace(
        cfg,
        environment=replace(
            cfg.environment,
            mortality_trace_schema="local-decaying-mortality-trace-v1",
            mortality_trace_decay=0.1,
            mortality_trace_diffusion=0.05,
            mortality_trace_deposit=0.4,
            mortality_trace_max=2.0,
            mortality_trace_observation_weight=0.5,
        ),
    )


def test_mortality_trace_is_local_decaying_and_observable() -> None:
    cfg = trace_config()
    env = Environment(cfg)
    cell = np.asarray([5], dtype=np.int32)
    base = float(env.hazard.reshape(-1)[5])
    env.deposit_mortality_trace(cell)
    assert float(env.mortality_trace.reshape(-1)[5]) == np.float32(0.4)
    assert float(env.danger_for_cells(cell)[0]) > base
    before = env.mortality_trace.copy()
    env.update(1)
    assert float(env.mortality_trace.max()) < float(before.max())
    assert np.count_nonzero(env.mortality_trace > 0.0) >= 5


def test_disabled_mortality_trace_is_semantically_inert() -> None:
    cfg = base_config()
    env = Environment(cfg)
    cell = np.asarray([7], dtype=np.int32)
    hazard = env.hazard.copy()
    env.deposit_mortality_trace(cell)
    np.testing.assert_array_equal(env.mortality_trace, 0.0)
    np.testing.assert_array_equal(env.public_danger_field(), hazard)


def test_cpu_and_numpy_device_mortality_trace_match() -> None:
    cfg = trace_config()
    cpu = Environment(cfg)
    dev = DeviceEnvironment(cfg, backend="cpu")
    cells = np.asarray([1, 1, 8, 13], dtype=np.int32)
    weights = np.asarray([1.0, 0.5, 2.0, 1.0], dtype=np.float32)
    cpu.deposit_mortality_trace(cells, weights)
    dev.deposit_mortality_trace(cells, weights)
    np.testing.assert_array_equal(dev.mortality_trace, cpu.mortality_trace)
    for tick in range(1, 5):
        cpu.update(tick)
        dev.update(tick)
    np.testing.assert_allclose(dev.mortality_trace, cpu.mortality_trace, atol=1e-7, rtol=1e-7)
    np.testing.assert_allclose(dev.public_danger_field(), cpu.public_danger_field(), atol=2e-6, rtol=2e-6)


def test_adaptive_group_refresh_uses_dirty_decay_and_max_staleness() -> None:
    cfg = base_config()
    cfg = replace(
        cfg,
        social=replace(
            cfg.social,
            group_update_mode="adaptive-topology-v1",
            group_update_min_period=3,
            group_update_max_period=9,
            relation_decay=0.1,
            trust_group_threshold=0.5,
        ),
        world=replace(cfg.world, initial_entities=2, max_entities=4),
    )
    validate_config(cfg)
    social = SocialSystem(cfg, 4)
    alive = np.asarray([True, True, False, False])
    ids = np.asarray([1, 2, 0, 0], dtype=np.uint64)
    plan = ungrouped_group_label_plan(np.asarray([0, 1], dtype=np.int32), ids[:2], 0)
    social.target[0, 0] = 1
    social.trust[0, 0] = np.float32(0.55)
    social.commit_group_plan(plan, alive, ids)
    assert social.group_update_due(0) == (False, "adaptive-skip")
    assert social.group_update_due(1) == (False, "adaptive-skip")
    due, reason = social.group_update_due(3)
    assert due and reason == "trust-decay-threshold"

    # A lifecycle/topology dirty flag obeys the minimum refresh period.
    social.last_group_update_tick = 3
    social.next_group_decay_due_tick = np.iinfo(np.int64).max
    social.mark_group_labels_dirty("test")
    assert social.group_update_due(4) == (False, "adaptive-skip")
    assert social.group_update_due(6) == (True, "topology-dirty")

    social.group_labels_dirty = False
    social.last_group_update_tick = 6
    assert social.group_update_due(15) == (True, "max-staleness")


def test_periodic_group_refresh_keeps_legacy_schedule() -> None:
    cfg = base_config()
    social = SocialSystem(cfg, cfg.world.max_entities)
    for tick in range(0, 101):
        due, _ = social.group_update_due(tick)
        assert due == (tick % cfg.social.group_update_period == 0)


def test_trace_and_adaptive_group_checkpoint_replay(tmp_path: Path) -> None:
    cfg = trace_config()
    cfg = replace(
        cfg,
        run=replace(
            cfg.run,
            ticks=8,
            metrics_period=4,
            checkpoint_period=4,
            evolution_evaluation_period=4,
            full_checkpoint_enabled=True,
            validation_mode=True,
        ),
        world=replace(cfg.world, initial_entities=48, max_entities=72),
        social=replace(
            cfg.social,
            group_update_mode="adaptive-topology-v1",
            group_update_min_period=2,
            group_update_max_period=6,
        ),
    )
    continuous = Simulation(cfg, tmp_path / "continuous", backend="cpu")
    for _ in range(4):
        continuous.step()
    checkpoint = continuous.save_full_checkpoint(
        tmp_path / "continuous" / "checkpoint_00000004.sechk"
    )
    restored = Simulation.from_checkpoint(
        checkpoint, tmp_path / "restored", backend="cpu", until_tick=8
    )
    for _ in range(4):
        continuous.step()
        restored.step()
    np.testing.assert_array_equal(
        restored.environment.mortality_trace,
        continuous.environment.mortality_trace,
    )
    np.testing.assert_array_equal(restored.social.group_id, continuous.social.group_id)
    assert restored.social.last_group_update_tick == continuous.social.last_group_update_tick
    assert restored.social.group_update_count == continuous.social.group_update_count
    for simulation in (continuous, restored):
        simulation.metrics.close()
        simulation.evolution_progress.close()
        simulation.knowledge.close()


def test_v020_checkpoint_config_hash_accepts_physically_stored_fields(tmp_path: Path) -> None:
    """New dataclass defaults must not invalidate a trusted older bundle."""
    from dataclasses import asdict
    import hashlib
    import json
    import pickle
    import zipfile

    from subject_evolution.checkpointing import (
        CHECKPOINT_SCHEMA,
        read_checkpoint_bundle,
    )

    cfg = base_config()
    legacy_payload = asdict(cfg)
    for name in (
        "mortality_trace_schema",
        "mortality_trace_decay",
        "mortality_trace_diffusion",
        "mortality_trace_deposit",
        "mortality_trace_max",
        "mortality_trace_observation_weight",
    ):
        legacy_payload["environment"].pop(name)
        vars(cfg.environment).pop(name)
    for name in (
        "group_update_mode",
        "group_update_min_period",
        "group_update_max_period",
    ):
        legacy_payload["social"].pop(name)
        vars(cfg.social).pop(name)

    state = {
        "config": cfg,
        "simulation": {"tick": 0},
        "checkpoint_lineage": [],
    }
    state_payload = pickle.dumps(state, protocol=pickle.HIGHEST_PROTOCOL)
    config_payload = json.dumps(
        legacy_payload, ensure_ascii=False, sort_keys=True
    ).encode("utf-8")
    metadata = {
        "schema": CHECKPOINT_SCHEMA,
        "project_version": "0.20.0",
        "tick": 0,
        "config_sha256": hashlib.sha256(config_payload).hexdigest(),
        "state_sha256": hashlib.sha256(state_payload).hexdigest(),
    }
    path = tmp_path / "legacy.sechk"
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("metadata.json", json.dumps(metadata).encode("utf-8"))
        archive.writestr("state.pkl", state_payload)

    loaded_metadata, loaded_state = read_checkpoint_bundle(path)
    assert loaded_metadata["project_version"] == "0.20.0"
    assert loaded_state["simulation"]["tick"] == 0


def test_long_run_record_exposes_trace_and_group_refresh_audit(tmp_path: Path) -> None:
    cfg = trace_config()
    cfg = replace(
        cfg,
        run=replace(
            cfg.run,
            ticks=4,
            metrics_period=2,
            evolution_evaluation_period=2,
            checkpoint_period=4,
            full_checkpoint_enabled=False,
            validation_mode=True,
        ),
        social=replace(
            cfg.social,
            group_update_mode="adaptive-topology-v1",
            group_update_min_period=3,
            group_update_max_period=6,
        ),
    )
    sim = Simulation(cfg, tmp_path, backend="cpu")
    sim.run()
    record = sim.evolution_progress.records[-1]
    assert record["mortality_trace_schema"] == "local-decaying-mortality-trace-v1"
    assert record["group_update_mode"] == "adaptive-topology-v1"
    assert "environment_mortality_trace_max" in record
    assert "group_update_count_total" in record
    assert "group_last_dirty_reason" in record
