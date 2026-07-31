from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest

from se.cfg import load_config, validate_config
from se.differentiation.physiology import (
    fixed_budget_resource_conversion_enabled,
    neutral_resource_conversion_capacity,
    physiology_genome_energy,
    physiology_phenotype,
)
from se.policy import ParametricPolicy
from se.runtime.resource_metabolism import settle_resource_metabolism
from se.runtime.sim import Simulation
from se.runtime.state import EntityState

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "studies" / "d1i_fixed_budget_resource_conversion_v1" / "protocol" / "source_pilot.json"


def test_fixed_budget_conversion_is_inherited_and_total_closes() -> None:
    cfg = load_config(CONFIG)
    assert fixed_budget_resource_conversion_enabled(cfg)
    start = ParametricPolicy.physiology_gene_start(cfg)
    genes = np.zeros((4, ParametricPolicy.genome_size_for_config(cfg)), dtype=np.float32)
    genes[:, start + 19 : start + 23] = np.asarray(
        [[1, -1, -1, -1], [-1, 1, -1, -1], [-1, -1, 1, -1], [-1, -1, -1, 1]],
        dtype=np.float32,
    )
    phenotype = physiology_phenotype(genes, cfg, gene_start=start)
    capacity = phenotype.resource_conversion_capacity
    assert np.allclose(capacity.sum(axis=1), 0.16, atol=1e-12, rtol=0.0)
    assert np.argmax(capacity, axis=1).tolist() == [0, 1, 2, 3]
    assert np.allclose(neutral_resource_conversion_capacity(4, cfg), 0.04)


def test_neutral_allocation_preserves_total_and_physio_cost() -> None:
    cfg = load_config(CONFIG)
    start = ParametricPolicy.physiology_gene_start(cfg)
    entities = EntityState(cfg)
    rows = np.arange(4, dtype=np.int32)
    entities.resource_store[rows] = 0.2
    inherited_cost = physiology_genome_energy(
        entities.genotype[rows], cfg, gene_start=start
    )
    inherited = settle_resource_metabolism(
        entities,
        rows,
        cfg,
        genotype=entities.genotype[rows],
        gene_start=start,
    )
    entities.resource_store[rows] = 0.2
    neutral = settle_resource_metabolism(
        entities,
        rows,
        cfg,
        genotype=entities.genotype[rows],
        gene_start=start,
        neutralize_conversion_allocation=True,
    )
    assert inherited.converted.sum() == pytest.approx(neutral.converted.sum())
    assert np.all(inherited_cost > 0.0)


def test_conversion_allocation_intervention_round_trips_checkpoint(tmp_path: Path) -> None:
    cfg = load_config(CONFIG)
    cfg = replace(
        cfg,
        run=replace(cfg.run, ticks=2, metrics_period=1, checkpoint_period=1),
        world=replace(cfg.world, initial_entities=16, max_entities=32),
    )
    validate_config(cfg)
    sim = Simulation(cfg, tmp_path / "source", backend="cpu")
    genotype = sim.entities.genotype.copy()
    stores = sim.entities.resource_store.copy()
    cost = physiology_genome_energy(
        sim.entities.genotype[sim.entities.alive],
        cfg,
        gene_start=ParametricPolicy.physiology_gene_start(cfg),
    )
    sim.apply_intervention("neutralize-resource-conversion-allocation")
    assert sim.resource_conversion_allocation_ablation_enabled
    assert np.array_equal(sim.entities.genotype, genotype)
    assert np.array_equal(sim.entities.resource_store, stores)
    assert np.array_equal(
        physiology_genome_energy(
            sim.entities.genotype[sim.entities.alive],
            cfg,
            gene_start=ParametricPolicy.physiology_gene_start(cfg),
        ),
        cost,
    )
    checkpoint = sim.save_full_checkpoint(tmp_path / "conversion.sechk")
    sim.metrics.close(); sim.evolution_progress.close(); sim.knowledge.close()
    restored = Simulation.from_checkpoint(
        checkpoint, tmp_path / "restored", backend="cpu", until_tick=2
    )
    assert restored.resource_conversion_allocation_ablation_enabled
    restored.metrics.close(); restored.evolution_progress.close(); restored.knowledge.close()


def test_v8_rejects_spatial_processing_energy_without_v7() -> None:
    cfg = load_config(CONFIG)
    invalid = replace(
        cfg,
        physiology=replace(
            cfg.physiology,
            resource_processing_energy_per_unit=(0.01, 0.01, 0.01, 0.01),
        ),
    )
    with pytest.raises(ValueError, match="resource processing execution costs"):
        validate_config(invalid)
