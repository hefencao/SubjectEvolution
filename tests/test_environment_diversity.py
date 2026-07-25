from __future__ import annotations

from dataclasses import replace
import json
from pathlib import Path

import numpy as np

from subject_evolution.config import load_config, validate_config
from subject_evolution.environment import Environment
from subject_evolution.gpu_environment import DeviceEnvironment
from subject_evolution.niches import (
    AFFINITY_SCALE,
    apply_harvest_effects,
    policy_resource_view,
    resource_affinity_quantized,
)
from subject_evolution.simulation import Simulation


ROOT = Path(__file__).resolve().parents[1]


def hetero_config():
    return load_config(
        ROOT / "configs" / "mvp_short_latent_l2_memory_topk_inherited_heterogeneous.json"
    )


def test_legacy_environment_and_resource_view_are_inert() -> None:
    cfg = load_config(ROOT / "configs" / "mvp_short_latent_l2_memory_topk_inherited.json")
    genotype = np.zeros((3, 16), dtype=np.float32)
    affinity = resource_affinity_quantized(genotype, cfg)
    np.testing.assert_array_equal(
        affinity, np.full((3, 4), AFFINITY_SCALE, dtype=np.int32)
    )
    local = np.arange(12, dtype=np.float32).reshape(3, 4)
    np.testing.assert_array_equal(policy_resource_view(local, genotype, cfg), local)


def test_resource_affinity_has_exact_fixed_budget_and_tradeoff() -> None:
    cfg = hetero_config()
    genotype = np.zeros((4, 16), dtype=np.float32)
    for row in range(4):
        genotype[row, 1 + row] = 1.0
        genotype[row, 1 + ((row + 1) % 4)] = -1.0
    affinity = resource_affinity_quantized(genotype, cfg)
    np.testing.assert_array_equal(
        affinity.sum(axis=1), np.full(4, 4 * AFFINITY_SCALE, dtype=np.int64)
    )
    for row in range(4):
        assert affinity[row, row] > AFFINITY_SCALE
        assert affinity[row, (row + 1) % 4] < AFFINITY_SCALE


def test_policy_resource_utility_depends_on_local_niche_without_mutating_raw() -> None:
    cfg = hetero_config()
    raw = np.asarray([[0.0, 0.0, 0.0, 8.0]], dtype=np.float32)
    channel3 = np.zeros((1, 16), dtype=np.float32)
    channel0 = np.zeros((1, 16), dtype=np.float32)
    channel3[0, 4] = 1.0
    channel3[0, 1] = -1.0
    channel0[0, 1] = 1.0
    channel0[0, 4] = -1.0
    view3 = policy_resource_view(raw, channel3, cfg)
    view0 = policy_resource_view(raw, channel0, cfg)
    np.testing.assert_array_equal(raw, np.asarray([[0.0, 0.0, 0.0, 8.0]], dtype=np.float32))
    assert view3[0, 0] > view0[0, 0]
    np.testing.assert_array_equal(view3[:, 1:], raw[:, 1:])


def test_harvest_effects_use_affinity_and_public_effect_matrix() -> None:
    cfg = hetero_config()
    gathered = np.ones((2, 4), dtype=np.float32)
    genotype = np.zeros((2, 16), dtype=np.float32)
    genotype[0, 1] = 1.0
    genotype[0, 2] = -1.0
    genotype[1, 2] = 1.0
    genotype[1, 1] = -1.0
    assimilated, body = apply_harvest_effects(gathered, genotype, cfg)
    assert assimilated[0, 0] > assimilated[1, 0]
    assert assimilated[1, 1] > assimilated[0, 1]
    assert body[0, 0] != body[1, 0]
    assert np.all(body >= 0.0)


def test_spatially_asynchronous_season_has_local_phase_variation() -> None:
    cfg = hetero_config()
    env = Environment(cfg)
    seasonal = env._seasonal_multiplier(30)
    assert seasonal.shape == (4, cfg.world.grid_y, cfg.world.grid_x)
    assert all(float(np.std(seasonal[channel])) > 0.05 for channel in range(4))


def test_cpu_and_numpy_device_environment_match_heterogeneous_fields() -> None:
    cfg = hetero_config()
    cpu = Environment(cfg)
    device = DeviceEnvironment(cfg, backend="cpu")
    np.testing.assert_allclose(device.resources, cpu.resources, atol=1e-6, rtol=1e-6)
    np.testing.assert_allclose(device.hazard, cpu.hazard, atol=1e-6, rtol=1e-6)
    for tick in (1, 7, 31):
        cpu.update(tick)
        device.update(tick)
    np.testing.assert_allclose(device.resources, cpu.resources, atol=2e-6, rtol=2e-6)
    np.testing.assert_allclose(device.hazard, cpu.hazard, atol=2e-6, rtol=2e-6)
    cells = np.arange(cfg.world.max_entities, dtype=np.int32) % (
        cfg.world.grid_x * cfg.world.grid_y
    )
    genotype = np.zeros((cfg.world.max_entities, 16), dtype=np.float32)
    genotype[:, 1:5] = np.linspace(-0.8, 0.8, cfg.world.max_entities)[:, None]
    affinity = resource_affinity_quantized(genotype, cfg)
    cpu_grad = cpu.gradients_for_entities(cells, cfg.world.max_entities, affinity)
    dev_grad = device.gradients_for_entities(cells, cfg.world.max_entities, affinity)
    for cpu_pair, dev_pair in zip(cpu_grad, dev_grad):
        for cpu_value, dev_value in zip(cpu_pair, dev_pair):
            np.testing.assert_allclose(dev_value, cpu_value, atol=2e-6, rtol=2e-6)


def test_heterogeneous_checkpoint_restores_harvest_totals(tmp_path: Path) -> None:
    cfg = load_config(ROOT / "configs" / "heterogeneous_smoke.json")
    cfg = replace(
        cfg,
        run=replace(cfg.run, ticks=6, checkpoint_period=3, evolution_evaluation_period=3, full_checkpoint_enabled=True),
        world=replace(cfg.world, initial_entities=64, max_entities=96),
    )
    run = Simulation(cfg, tmp_path / "source", backend="cpu")
    run.run(until_tick=3)
    checkpoint = tmp_path / "source" / "checkpoint_00000003.sechk"
    restored = Simulation.from_checkpoint(
        checkpoint, tmp_path / "restored", backend="cpu", until_tick=6
    )
    restored.run(until_tick=6)
    continuous = Simulation(cfg, tmp_path / "continuous", backend="cpu")
    continuous.run(until_tick=6)
    np.testing.assert_array_equal(
        restored.total_harvested_resources, continuous.total_harvested_resources
    )
    assert restored.evolution_progress.records[-1]["action_names"][3] == "HARVEST"
    assert restored.evolution_progress.records[-1]["active_morphology_gene_count"] == 6


def test_affinity_requires_heterogeneous_environment() -> None:
    cfg = load_config(ROOT / "configs" / "mvp_short_latent_l2_memory_topk_inherited.json")
    invalid = replace(
        cfg,
        entities=replace(
            cfg.entities,
            resource_affinity_schema="normalized-four-resource-affinity-v1",
            resource_affinity_strength=0.5,
        ),
    )
    try:
        validate_config(invalid)
    except ValueError as exc:
        assert "heterogeneous environment" in str(exc)
    else:
        raise AssertionError("invalid affinity/environment combination was accepted")


def test_run_manifest_records_environment_and_affinity_schema(tmp_path: Path) -> None:
    cfg = load_config(ROOT / "configs" / "heterogeneous_smoke.json")
    cfg = replace(
        cfg,
        run=replace(cfg.run, ticks=1, checkpoint_period=0, evolution_evaluation_period=1),
        world=replace(cfg.world, initial_entities=16, max_entities=24),
    )
    Simulation(cfg, tmp_path / "run", backend="cpu")
    manifest = json.loads((tmp_path / "run" / "run_manifest.json").read_text())
    assert manifest["environment_schema"] == "spatially-asynchronous-multiniche-v1"
    assert manifest["environment_spatially_asynchronous"] is True
    assert manifest["resource_affinity_enabled"] is True
    assert manifest["resource_affinity_gene_indices"] == [1, 2, 3, 4]
    assert manifest["resource_affinity_fixed_budget_q"] == 4 * AFFINITY_SCALE
