from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest

from se.analysis.protocol_audit import build_protocol_audit
from se.cfg import load_config, validate_config
from se.differentiation.physiology import spatial_processing_enabled
from se.env.world import Environment
from se.experiments.d3_spatial_processing import execute_spatial_processing
from se.policy import ParametricPolicy
from se.runtime.resource_metabolism import settle_resource_metabolism
from se.runtime.sim import Simulation
from se.runtime.state import EntityState

ROOT = Path(__file__).resolve().parents[1]
D3E = ROOT / "configs" / "mvp_short_d3e_spatial_processing_longrun.json"
D3D = ROOT / "configs" / "mvp_short_d3d_persistent_resource_renewal_longrun.json"


def _small_cfg(*, ticks: int = 6):
    cfg = load_config(D3E)
    return replace(
        cfg,
        run=replace(
            cfg.run,
            ticks=ticks,
            metrics_period=max(1, ticks // 2),
            checkpoint_period=max(1, ticks // 2),
            evolution_evaluation_period=max(1, ticks // 2),
            full_checkpoint_enabled=False,
            long_run_diagnostics_enabled=False,
            long_run_diagnostics_schema="disabled",
            spatial_stress_diagnostics_enabled=False,
            spatial_stress_diagnostics_schema="disabled",
            subject_structure_diagnostics_enabled=False,
            subject_structure_diagnostics_schema="disabled",
            environment_atlas_diagnostics_enabled=False,
            environment_atlas_diagnostics_schema="disabled",
            environment_atlas_scales=(),
        ),
        world=replace(cfg.world, initial_entities=48, max_entities=96),
    )


def test_processing_support_is_positive_nonuniform_and_reversible() -> None:
    cfg = load_config(D3E)
    assert spatial_processing_enabled(cfg)
    environment = Environment(cfg)
    field = environment.resource_processing_support_field(17)
    assert field.shape == (4, cfg.world.grid_y, cfg.world.grid_x)
    assert np.all(np.isfinite(field))
    assert np.all(field > 0.0)
    assert np.ptp(field) > 0.1
    original = field.copy()
    environment.reverse_resource_spatial_orientation()
    reversed_field = environment.resource_processing_support_field(17)
    assert np.array_equal(reversed_field, original[:, ::-1, ::-1])


def test_processing_support_constrains_and_accelerates_with_explicit_cost() -> None:
    cfg = load_config(D3E)
    entities = EntityState(cfg)
    rows = np.array([0, 1], dtype=np.int32)
    entities.resource_store[rows] = 0.5
    entities.energy[rows] = 1.5
    genotype = entities.genotype[rows]
    support = np.array(
        [[0.5, 1.0, 1.5, 2.0], [0.75, 1.25, 0.6, 1.8]], dtype=np.float32
    )
    before_store = entities.resource_store[rows].astype(np.float64).copy()
    before_energy = entities.energy[rows].astype(np.float64).copy()
    step = settle_resource_metabolism(
        entities,
        rows,
        cfg,
        genotype=genotype,
        gene_start=ParametricPolicy.physiology_gene_start(cfg),
        processing_support=support,
    )
    assert np.any(step.processing_support_limited > 0.0)
    assert np.any(step.processing_support_accelerated > 0.0)
    assert step.processing_energy_cost > 0.0
    rates = np.asarray(cfg.physiology.resource_processing_energy_per_unit)
    assert step.processing_energy_cost == pytest.approx(float(step.converted @ rates))
    after_store = entities.resource_store[rows].astype(np.float64)
    decay = step.decayed_by_entity
    converted_total = step.converted
    assert np.allclose(
        before_store.sum(axis=0),
        converted_total + decay.sum(axis=0) + after_store.sum(axis=0),
        atol=5.0e-7,
        rtol=0.0,
    )
    # Channel zero returns some energy, but cost is charged before outcomes and
    # must be finite and no greater than the available pre-conversion energy.
    assert step.processing_energy_cost <= float(before_energy.sum())


def test_v7_requires_support_and_non_v7_rejects_processing_cost() -> None:
    cfg = load_config(D3E)
    with pytest.raises(ValueError, match="requires phase-shifted"):
        validate_config(
            replace(
                cfg,
                environment=replace(
                    cfg.environment,
                    resource_processing_schema="disabled",
                    resource_processing_support_amplitude=0.0,
                ),
            )
        )
    legacy = load_config(D3D)
    with pytest.raises(ValueError, match="require physiology resource-v7"):
        validate_config(
            replace(
                legacy,
                physiology=replace(
                    legacy.physiology,
                    resource_processing_energy_per_unit=(0.002,) * 4,
                ),
            )
        )


def test_processing_ablation_survives_clone_and_checkpoint(tmp_path: Path) -> None:
    cfg = _small_cfg(ticks=2)
    simulation = Simulation(cfg, tmp_path / "source", backend="cpu")
    genotype = simulation.entities.genotype.copy()
    resources = simulation.environment.resources.copy()
    simulation.apply_intervention("neutralize-spatial-processing-support")
    assert simulation.resource_processing_support_ablation_enabled
    assert np.array_equal(simulation.entities.genotype, genotype)
    assert np.array_equal(simulation.environment.resources, resources)
    clone = simulation.clone(tmp_path / "clone")
    assert clone.resource_processing_support_ablation_enabled
    checkpoint = simulation.save_full_checkpoint(tmp_path / "support.sechk")
    restored = Simulation.from_checkpoint(
        checkpoint, tmp_path / "restored", backend="cpu", until_tick=2
    )
    assert restored.resource_processing_support_ablation_enabled
    assert restored.cfg.physiology.resource_processing_energy_per_unit == (0.002,) * 4


def test_d3e_shared_checkpoint_pair_and_protocol(tmp_path: Path) -> None:
    cfg = _small_cfg(ticks=6)
    payload = execute_spatial_processing(
        cfg,
        (58001,),
        tmp_path / "run",
        backend="cpu",
        until_tick=6,
    )
    assert payload["schema"] == "d3-spatial-collection-processing-results-v2"
    pair = payload["pairs"][0]
    assert pair["shared_checkpoint_state"]
    branches = {row["branch"]: row for row in pair["branches"]}
    assert branches["spatial-support"]["interventions"] == []
    assert branches["neutral-support"]["interventions"] == [
        "neutralize-spatial-processing-support"
    ]
    assert branches["spatial-support"]["final"][
        "resource_processing_energy_cost_total"
    ] > 0.0
    assert branches["neutral-support"]["final"][
        "resource_processing_energy_cost_total"
    ] > 0.0
    assert np.allclose(
        branches["neutral-support"]["final"][
            "resource_processing_support_weighted_mean"
        ],
        np.ones(4),
        atol=1.0e-12,
        rtol=0.0,
    )
    assert all(row["valid"] for row in payload["external_resource_ledger"])
    assert all(row["valid"] for row in payload["external_recycling_ledger"])
    audit = build_protocol_audit(D3E)
    assert audit["schema"] == "structural-measurement-protocol-audit-v43"
    protocol = audit["functional_module_protocol"]["spatial_processing_experiment"]
    assert protocol["shared_checkpoint_tick"] == 0
    assert protocol["processing_execution_cost_preserved_in_ablation"]
    assert not protocol["stable_migration_or_ecotype_claim"]
