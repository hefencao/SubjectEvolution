from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import numpy as np

from se.cfg import load_config, validate_config
from se.env.danger_evidence import (
    DANGER_EVIDENCE_SCALE,
    DANGER_EVIDENCE_TOTAL,
    danger_evidence_quantized,
)
from se.env.world import Environment
from se.env.gpu import DeviceEnvironment
from se.env.niches import active_morphology_traits
from se.runtime.sim import Simulation


ROOT = Path(__file__).resolve().parents[1]


def base_config():
    return load_config(
        ROOT
        / "configs"
        / "mvp_short_latent_l2_memory_topk_inherited_heterogeneous_budget_matched_costed_transfer_mortality_trace_adaptive_groups_longrun.json"
    )


def enabled_config():
    cfg = base_config()
    cfg = replace(
        cfg,
        environment=replace(
            cfg.environment,
            moving_hazard_schema="moving-gaussian-hazard-sources-v1",
            moving_hazard_source_count=3,
            moving_hazard_amplitude=0.3,
            moving_hazard_radius=0.1,
            moving_hazard_speed=0.002,
            moving_hazard_phase_offset=0.37,
        ),
        entities=replace(
            cfg.entities,
            danger_evidence_schema="inherited-direct-trace-mixture-v1",
            danger_evidence_strength=0.75,
            danger_evidence_min_efficiency=0.25,
            danger_evidence_max_efficiency=1.75,
        ),
    )
    validate_config(cfg)
    return cfg


def test_danger_evidence_uses_fixed_budget_and_gene_six() -> None:
    cfg = enabled_config()
    genotype = np.zeros((3, 8), dtype=np.float32)
    genotype[:, 6] = np.asarray([-1.0, 0.0, 1.0], dtype=np.float32)
    weights = danger_evidence_quantized(genotype, cfg)
    np.testing.assert_array_equal(weights.sum(axis=1), DANGER_EVIDENCE_TOTAL)
    assert weights[0, 0] < DANGER_EVIDENCE_SCALE < weights[2, 0]
    assert weights[0, 1] > DANGER_EVIDENCE_SCALE > weights[2, 1]
    indices, names = active_morphology_traits(cfg)
    assert indices[-1] == 6
    assert names[-1] == "danger_direct_trace_mixture"


def test_entity_specific_danger_mixture_changes_local_evidence() -> None:
    cfg = enabled_config()
    env = Environment(cfg)
    cell = np.asarray([5, 5], dtype=np.int32)
    env.deposit_mortality_trace(np.asarray([5], dtype=np.int32), np.asarray([3.0], dtype=np.float32))
    genotype = np.zeros((2, 8), dtype=np.float32)
    genotype[:, 6] = np.asarray([1.0, -1.0], dtype=np.float32)
    weights = danger_evidence_quantized(genotype, cfg)
    danger = env.danger_for_cells(cell, weights)
    direct, trace = env.danger_components_for_cells(cell)
    assert float(trace[0]) > 0.0
    assert not np.isclose(float(danger[0]), float(danger[1]))
    expected = (
        direct.astype(np.float64) * weights[:, 0]
        + trace.astype(np.float64) * weights[:, 1]
    ) / DANGER_EVIDENCE_SCALE
    np.testing.assert_allclose(danger, expected.astype(np.float32), atol=1e-7, rtol=1e-7)


def test_moving_hazard_sources_move_and_match_numpy_device() -> None:
    cfg = enabled_config()
    cpu = Environment(cfg)
    dev = DeviceEnvironment(cfg, backend="cpu")
    initial = cpu.hazard.copy()
    np.testing.assert_allclose(dev.hazard, initial, atol=2e-6, rtol=2e-6)
    cpu.update(37)
    dev.update(37)
    assert not np.array_equal(cpu.hazard, initial)
    np.testing.assert_allclose(dev.hazard, cpu.hazard, atol=3e-6, rtol=3e-6)


def test_disabled_new_schemas_preserve_neutral_danger() -> None:
    cfg = base_config()
    env = Environment(cfg)
    cells = np.asarray([1, 7, 13], dtype=np.int32)
    genotype = np.zeros((3, 8), dtype=np.float32)
    weights = danger_evidence_quantized(genotype, cfg)
    np.testing.assert_array_equal(weights, DANGER_EVIDENCE_SCALE)
    np.testing.assert_array_equal(
        env.danger_for_cells(cells, weights), env.danger_for_cells(cells)
    )


def test_moving_hazard_and_evidence_checkpoint_replay(tmp_path: Path) -> None:
    cfg = enabled_config()
    cfg = replace(
        cfg,
        run=replace(
            cfg.run,
            ticks=12,
            metrics_period=4,
            checkpoint_period=6,
            evolution_evaluation_period=4,
            full_checkpoint_enabled=True,
            validation_mode=True,
        ),
        world=replace(cfg.world, initial_entities=48, max_entities=72),
    )
    continuous = Simulation(cfg, tmp_path / "continuous", backend="cpu")
    for _ in range(6):
        continuous.step()
    checkpoint = continuous.save_full_checkpoint(
        tmp_path / "continuous" / "checkpoint_00000006.sechk"
    )
    restored = Simulation.from_checkpoint(
        checkpoint, tmp_path / "restored", backend="cpu", until_tick=12
    )
    for _ in range(6):
        continuous.step()
        restored.step()
    np.testing.assert_array_equal(restored.environment.hazard, continuous.environment.hazard)
    np.testing.assert_array_equal(
        restored.environment.mortality_trace, continuous.environment.mortality_trace
    )
    np.testing.assert_array_equal(restored.entities.genotype, continuous.entities.genotype)
    for simulation in (continuous, restored):
        simulation.metrics.close()
        simulation.evolution_progress.close()
        simulation.knowledge.close()


def test_neutralize_danger_evidence_intervention_preserves_genotype(tmp_path: Path) -> None:
    cfg = enabled_config()
    cfg = replace(
        cfg,
        run=replace(cfg.run, ticks=2, metrics_period=1, checkpoint_period=2),
        world=replace(cfg.world, initial_entities=24, max_entities=32),
    )
    sim = Simulation(cfg, tmp_path, backend="cpu")
    before = sim.entities.genotype.copy()
    sim.apply_intervention("neutralize-danger-evidence")
    assert sim.intervention_history[-1]["type"] == "neutralize-danger-evidence"
    assert sim.danger_evidence_ablation_enabled
    np.testing.assert_array_equal(sim.entities.genotype, before)
    sim.metrics.close()
    sim.evolution_progress.close()
    sim.knowledge.close()
