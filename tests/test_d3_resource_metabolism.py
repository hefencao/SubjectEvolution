from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import numpy as np

from se.analysis.protocol_audit import build_protocol_audit
from se.cfg import load_config
from se.differentiation.functional import (
    RESOURCE_METABOLISM_FUNCTIONAL_MODULE_SCHEMA,
    RESOURCE_METABOLISM_INPUT_COUNT,
    functional_module_input_count,
)
from se.differentiation.physiology import (
    PHYSIOLOGY_GENE_COUNT,
    RESOURCE_METABOLISM_GENE_COUNT,
    RESOURCE_METABOLISM_PHYSIOLOGY_SCHEMA,
    physiology_gene_count,
    physiology_phenotype,
    resource_metabolism_enabled,
)
from se.evolution.lifecycle import plan_death_events
from se.experiments.d3_resource_metabolism import execute_resource_metabolism
from se.policy import ParametricPolicy
from se.runtime.resource_metabolism import (
    record_resource_store_death_loss,
    settle_resource_metabolism,
    settle_resource_metabolism_before_step,
    store_assimilated_resources,
)
from se.runtime.sim import Simulation
from se.runtime.state import EntityState, StepStats

ROOT = Path(__file__).resolve().parents[1]
D3_CONFIG = ROOT / "configs" / "d3a_resource_metabolism_smoke.json"
D2_CONFIG = ROOT / "configs" / "d2l_regulatory_physiology_smoke.json"


def test_v4_resource_metabolism_extends_genome_and_inputs() -> None:
    cfg = load_config(D3_CONFIG)
    legacy = load_config(D2_CONFIG)
    assert cfg.functional_modules.schema == RESOURCE_METABOLISM_FUNCTIONAL_MODULE_SCHEMA
    assert cfg.physiology.schema == RESOURCE_METABOLISM_PHYSIOLOGY_SCHEMA
    assert resource_metabolism_enabled(cfg)
    assert physiology_gene_count(cfg) == PHYSIOLOGY_GENE_COUNT + RESOURCE_METABOLISM_GENE_COUNT
    assert physiology_gene_count(legacy) == PHYSIOLOGY_GENE_COUNT
    assert functional_module_input_count(cfg) == RESOURCE_METABOLISM_INPUT_COUNT
    assert ParametricPolicy.genome_size_for_config(cfg) > ParametricPolicy.genome_size_for_config(legacy)


def test_assimilated_resource_is_stored_before_later_conversion() -> None:
    cfg = load_config(D3_CONFIG)
    entities = EntityState(cfg)
    row = np.array([0], dtype=np.int32)
    genotype = entities.genotype[row]
    start = ParametricPolicy.physiology_gene_start(cfg)
    energy_before = entities.energy[row].copy()
    material_before = entities.material[row].copy()
    stored, overflow = store_assimilated_resources(
        entities,
        row,
        np.array([[0.2, 0.2, 0.2, 0.2]], dtype=np.float32),
        cfg,
        genotype=genotype,
        gene_start=start,
    )
    assert np.all(stored > 0.0)
    assert np.all(overflow == 0.0)
    assert np.array_equal(entities.energy[row], energy_before)
    assert np.array_equal(entities.material[row], material_before)

    step = settle_resource_metabolism(
        entities,
        row,
        cfg,
        genotype=genotype,
        gene_start=start,
    )
    assert np.all(step.converted > 0.0)
    assert step.body_realized[0] > 0.0
    assert entities.energy[0] > energy_before[0]
    assert np.all(entities.resource_store[0] >= 0.0)


def test_store_capacity_and_conversion_are_inherited_per_channel() -> None:
    cfg = load_config(D3_CONFIG)
    entities = EntityState(cfg)
    rows = np.arange(12, dtype=np.int32)
    phenotype = physiology_phenotype(
        entities.genotype[rows],
        cfg,
        gene_start=ParametricPolicy.physiology_gene_start(cfg),
    )
    assert phenotype.resource_store_capacity.shape == (12, 4)
    assert phenotype.resource_conversion_capacity.shape == (12, 4)
    assert np.all(phenotype.resource_store_capacity > 0.0)
    assert np.all(phenotype.resource_conversion_capacity > 0.0)
    assert np.any(np.std(phenotype.resource_store_capacity, axis=0) > 0.0)
    assert np.any(np.std(phenotype.resource_conversion_capacity, axis=0) > 0.0)


def test_resource_store_survives_clone_and_ledger_totals_clone(tmp_path: Path) -> None:
    cfg = load_config(D3_CONFIG)
    cfg = replace(cfg, run=replace(cfg.run, ticks=6, metrics_period=3, checkpoint_period=3))
    simulation = Simulation(cfg, tmp_path / "source", backend="cpu")
    simulation.run(until_tick=6)
    clone = simulation.clone(tmp_path / "clone")
    assert np.array_equal(clone.entities.resource_store, simulation.entities.resource_store)
    assert np.array_equal(clone.total_resource_stored, simulation.total_resource_stored)
    assert np.array_equal(clone.total_resource_converted, simulation.total_resource_converted)
    assert np.array_equal(clone.total_resource_store_decay, simulation.total_resource_store_decay)
    assert np.array_equal(
        clone.total_resource_store_death_loss,
        simulation.total_resource_store_death_loss,
    )


def test_d3_experiment_reports_closed_store_ledger(tmp_path: Path) -> None:
    cfg = load_config(D3_CONFIG)
    result = execute_resource_metabolism(
        cfg,
        (53001, 53002),
        tmp_path / "run",
        backend="cpu",
        until_tick=8,
    )
    assert result["schema"] == "d3-resource-metabolism-results-v1"
    assert result["completed_seed_count"] == 2
    assert result["stable_trend_summary"]["storage_used_in_every_seed"]
    assert result["stable_trend_summary"]["conversion_used_in_every_seed"]
    assert result["stable_trend_summary"]["store_ledger_valid_in_every_seed"]
    assert result["recommendation"] == (
        "retain-buffered-resource-substrate-and-continue-spatiotemporal-ecology"
    )
    assert not result["ecological_differentiation_claim"]
    assert not result["module_copy_number_ready"]


def test_legacy_v3_does_not_allocate_resource_store() -> None:
    cfg = load_config(D2_CONFIG)
    entities = EntityState(cfg)
    assert not resource_metabolism_enabled(cfg)
    assert not hasattr(entities, "resource_store")


def test_protocol_audit_records_delayed_resource_metabolism() -> None:
    audit = build_protocol_audit(D3_CONFIG)
    assert audit["schema"] == "structural-measurement-protocol-audit-v43"
    functional = audit["functional_module_protocol"]
    semantics = functional["resource_metabolism_semantics"]
    experiment = functional["resource_metabolism_experiment"]
    assert semantics["enabled"]
    assert semantics["minimum_conversion_delay_ticks"] == 1
    assert not semantics["same_tick_harvest_body_effect"]
    assert semantics["store_occupancy_visible_to_operators"]
    assert semantics["equal_channel_base_parameters"]
    assert experiment["strict_raw_store_ledger"]
    assert not experiment["stable_niche_claim"]


def test_death_loss_is_explicit_and_cleared_with_carrier(tmp_path: Path) -> None:
    cfg = load_config(D3_CONFIG)
    simulation = Simulation(cfg, tmp_path / "death-loss", backend="cpu")
    dead = np.array([0, 1], dtype=np.int32)
    simulation.entities.resource_store[dead] = np.array(
        [[0.1, 0.2, 0.3, 0.4], [0.4, 0.3, 0.2, 0.1]],
        dtype=np.float32,
    )
    stats = StepStats()
    record_resource_store_death_loss(simulation, dead, stats)
    assert np.allclose(stats.resource_store_death_loss, [0.5, 0.5, 0.5, 0.5])
    simulation.entities.energy[dead] = 0.0
    plan = plan_death_events(
        active=dead,
        entity_ids=simulation.entities.entity_id,
        primary_subject_ids=simulation.entities.primary_subject_id,
        energy=simulation.entities.energy,
        integrity=simulation.entities.integrity,
        age=simulation.entities.age,
        max_age=simulation.cfg.entities.max_age,
        tick=simulation.tick,
    )
    simulation.entities.commit_deaths(plan)
    assert np.all(simulation.entities.resource_store[dead] == 0.0)


def test_delayed_conversion_refreshes_gpu_entity_mirror(tmp_path: Path) -> None:
    cfg = load_config(D3_CONFIG)
    simulation = Simulation(cfg, tmp_path / "gpu-mirror", backend="cpu")
    active = np.flatnonzero(simulation.entities.alive).astype(np.int32)
    simulation.entities.resource_store[active[:2]] = 0.2

    class Mirror:
        def __init__(self) -> None:
            self.calls: list[int] = []

        def sync_entity_from_host(self, entity, social, version: int) -> None:
            self.calls.append(version)

    mirror = Mirror()
    simulation.gpu_runtime = mirror  # type: ignore[assignment]
    version_before = simulation.entity_device_version
    settle_resource_metabolism_before_step(simulation, StepStats())
    assert simulation.entity_device_version == version_before + 1
    assert mirror.calls == [version_before + 1]


def test_resource_store_full_checkpoint_round_trip(tmp_path: Path) -> None:
    cfg = load_config(D3_CONFIG)
    cfg = replace(cfg, run=replace(cfg.run, ticks=6, checkpoint_period=3, full_checkpoint_enabled=True))
    source = Simulation(cfg, tmp_path / "checkpoint-source", backend="cpu")
    source.run(until_tick=6)
    checkpoint = source.save_full_checkpoint(tmp_path / "resource-v4.sechk")
    restored = Simulation.from_checkpoint(
        checkpoint,
        tmp_path / "checkpoint-restored",
        backend="cpu",
        until_tick=6,
    )
    assert restored.cfg.physiology.resource_store_base_capacity == (1.2, 1.2, 1.2, 1.2)
    assert np.array_equal(restored.entities.resource_store, source.entities.resource_store)
    assert np.array_equal(restored.total_resource_stored, source.total_resource_stored)
    assert np.array_equal(restored.total_resource_converted, source.total_resource_converted)
