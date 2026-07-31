from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import numpy as np

from se.cfg import load_config, validate_config
from se.differentiation.physiology import (
    external_resource_recycling_enabled,
    fixed_budget_resource_conversion_enabled,
    fixed_budget_resource_storage_enabled,
)
from se.env.recycling import deposit_resource_residue, resource_recycling_diagnostics
from se.runtime.sim import Simulation

ROOT = Path(__file__).resolve().parents[1]
CONFIG = (
    ROOT
    / "studies"
    / "d1k_conservative_reproductive_investment_v1"
    / "protocol"
    / "source_pilot.json"
)


def _close(sim: Simulation) -> None:
    sim.metrics.close()
    sim.evolution_progress.close()
    sim.knowledge.close()
    if sim.subject_structure_diagnostics is not None:
        sim.subject_structure_diagnostics.close()
    if sim.environment_atlas_diagnostics is not None:
        sim.environment_atlas_diagnostics.close()


def test_v10_composes_fixed_internal_budgets_and_external_recycling() -> None:
    cfg = load_config(CONFIG)
    assert fixed_budget_resource_storage_enabled(cfg)
    assert fixed_budget_resource_conversion_enabled(cfg)
    assert external_resource_recycling_enabled(cfg)
    validate_config(cfg)


def test_recycling_neutralization_preserves_inventory_and_round_trips(
    tmp_path: Path,
) -> None:
    cfg = load_config(CONFIG)
    cfg = replace(
        cfg,
        run=replace(cfg.run, ticks=2, metrics_period=1, checkpoint_period=1),
        world=replace(cfg.world, initial_entities=16, max_entities=32),
    )
    sim = Simulation(cfg, tmp_path / "source", backend="cpu")
    cells = np.array([0, 1], dtype=np.int32)
    amounts = np.asarray(
        [[1.0, 0.5, 0.25, 0.125], [0.5, 0.25, 0.125, 0.0625]],
        dtype=np.float32,
    )
    deposit_resource_residue(sim.environment, cells, amounts)
    genotype = sim.entities.genotype.copy()
    stores = sim.entities.resource_store.copy()
    fields = sim.environment.resources.copy()
    residue = sim.environment.resource_residue.copy()

    sim.apply_intervention("neutralize-external-resource-recycling")
    assert sim.resource_recycling_ablation_enabled
    assert sim.environment.resource_recycling_ablation_enabled
    assert np.array_equal(sim.entities.genotype, genotype)
    assert np.array_equal(sim.entities.resource_store, stores)
    assert np.array_equal(sim.environment.resources, fields)
    assert np.array_equal(sim.environment.resource_residue, residue)
    assert not resource_recycling_diagnostics(sim.environment)[
        "resource_recycling_effective_enabled"
    ]

    blocked = deposit_resource_residue(sim.environment, cells, amounts)
    assert np.array_equal(blocked, np.zeros(4, dtype=np.float64))
    before_update = sim.environment.resource_residue.copy()
    sim.environment.update(1)
    assert np.array_equal(sim.environment.resource_residue, before_update)
    assert np.array_equal(
        np.asarray(sim.environment.last_resource_residue_released),
        np.zeros(4, dtype=np.float64),
    )

    checkpoint = sim.save_full_checkpoint(tmp_path / "recycling.sechk")
    _close(sim)
    restored = Simulation.from_checkpoint(
        checkpoint, tmp_path / "restored", backend="cpu", until_tick=2
    )
    assert restored.resource_recycling_ablation_enabled
    assert restored.environment.resource_recycling_ablation_enabled
    branch = restored.clone(tmp_path / "branch")
    assert branch.resource_recycling_ablation_enabled
    assert branch.environment.resource_recycling_ablation_enabled
    _close(branch)
    _close(restored)


def test_summary_reports_generational_turnover_fields(tmp_path: Path) -> None:
    cfg = load_config(CONFIG)
    cfg = replace(
        cfg,
        run=replace(cfg.run, ticks=1, metrics_period=1, checkpoint_period=1),
        world=replace(cfg.world, initial_entities=12, max_entities=24),
    )
    sim = Simulation(cfg, tmp_path / "run", backend="cpu")
    active = np.flatnonzero(sim.entities.alive)
    sim.entities.generation[active[:3]] = 1
    sim.run(until_tick=1)
    import json

    summary = json.loads((tmp_path / "run" / "summary.json").read_text())
    assert summary["max_generation"] >= 1
    assert summary["descendant_alive_count"] >= 3
    assert 0.0 <= summary["founder_alive_fraction"] <= 1.0
    assert 0.0 <= summary["descendant_alive_fraction"] <= 1.0
    assert "cumulative_births_per_initial" in summary
    assert "living_descendants_per_initial" in summary
