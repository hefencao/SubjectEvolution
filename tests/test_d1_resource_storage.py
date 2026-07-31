from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import numpy as np

from se.cfg import load_config, validate_config
from se.differentiation.physiology import (
    fixed_budget_resource_conversion_enabled,
    fixed_budget_resource_storage_enabled,
    neutral_resource_store_capacity,
    physiology_genome_energy,
    physiology_phenotype,
)
from se.policy import ParametricPolicy
from se.runtime.resource_metabolism import resource_store_capacity_and_room
from se.runtime.sim import Simulation
from se.runtime.state import EntityState

ROOT = Path(__file__).resolve().parents[1]
CONFIG = (
    ROOT
    / "studies"
    / "d1j_fixed_budget_resource_storage_v1"
    / "protocol"
    / "source_pilot.json"
)


def test_fixed_budget_storage_is_inherited_and_total_closes() -> None:
    cfg = load_config(CONFIG)
    assert fixed_budget_resource_storage_enabled(cfg)
    assert fixed_budget_resource_conversion_enabled(cfg)
    start = ParametricPolicy.physiology_gene_start(cfg)
    genes = np.zeros((4, ParametricPolicy.genome_size_for_config(cfg)), dtype=np.float32)
    genes[:, start + 15 : start + 19] = np.asarray(
        [[1, -1, -1, -1], [-1, 1, -1, -1], [-1, -1, 1, -1], [-1, -1, -1, 1]],
        dtype=np.float32,
    )
    phenotype = physiology_phenotype(genes, cfg, gene_start=start)
    capacity = phenotype.resource_store_capacity
    assert np.allclose(capacity.sum(axis=1), 4.8, atol=1e-12, rtol=0.0)
    assert np.argmax(capacity, axis=1).tolist() == [0, 1, 2, 3]
    assert np.allclose(neutral_resource_store_capacity(4, cfg), 1.2)


def test_storage_neutralization_preserves_contents_conversion_and_cost() -> None:
    cfg = load_config(CONFIG)
    start = ParametricPolicy.physiology_gene_start(cfg)
    entities = EntityState(cfg)
    rows = np.arange(4, dtype=np.int32)
    entities.resource_store[rows] = np.asarray(
        [[0.2, 0.3, 0.4, 0.5]] * 4, dtype=np.float32
    )
    stores_before = entities.resource_store.copy()
    phenotype = physiology_phenotype(entities.genotype[rows], cfg, gene_start=start)
    conversion_before = phenotype.resource_conversion_capacity.copy()
    cost_before = physiology_genome_energy(
        entities.genotype[rows], cfg, gene_start=start
    )
    capacity, room = resource_store_capacity_and_room(
        entities,
        rows,
        cfg,
        genotype=entities.genotype[rows],
        gene_start=start,
        neutralize_store_allocation=True,
    )
    assert np.allclose(capacity, 1.2)
    assert np.all(room >= 0.0)
    assert np.array_equal(entities.resource_store, stores_before)
    phenotype_after = physiology_phenotype(entities.genotype[rows], cfg, gene_start=start)
    assert np.array_equal(phenotype_after.resource_conversion_capacity, conversion_before)
    assert np.array_equal(
        physiology_genome_energy(entities.genotype[rows], cfg, gene_start=start),
        cost_before,
    )


def test_storage_allocation_intervention_round_trips_checkpoint(tmp_path: Path) -> None:
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
    sim.apply_intervention("neutralize-resource-store-allocation")
    assert sim.resource_store_allocation_ablation_enabled
    assert np.array_equal(sim.entities.genotype, genotype)
    assert np.array_equal(sim.entities.resource_store, stores)
    checkpoint = sim.save_full_checkpoint(tmp_path / "storage.sechk")
    sim.metrics.close(); sim.evolution_progress.close(); sim.knowledge.close()
    restored = Simulation.from_checkpoint(
        checkpoint, tmp_path / "restored", backend="cpu", until_tick=2
    )
    assert restored.resource_store_allocation_ablation_enabled
    branch = restored.clone(tmp_path / "branch")
    assert branch.resource_store_allocation_ablation_enabled
    branch.metrics.close(); branch.evolution_progress.close(); branch.knowledge.close()
    restored.metrics.close(); restored.evolution_progress.close(); restored.knowledge.close()
