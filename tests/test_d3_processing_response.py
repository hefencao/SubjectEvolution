from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import numpy as np

from se.analysis.protocol_audit import build_protocol_audit
from se.cfg import load_config
from se.experiments.d3_processing_response import execute_processing_response
from se.runtime.sim import Simulation

ROOT = Path(__file__).resolve().parents[1]
D3E = ROOT / "configs" / "mvp_short_d3e_spatial_processing_longrun.json"


def _small_cfg(*, ticks: int = 8):
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
        world=replace(cfg.world, initial_entities=64, max_entities=128),
    )


def test_support_orientation_intervention_changes_only_support(tmp_path: Path) -> None:
    cfg = _small_cfg(ticks=2)
    simulation = Simulation(cfg, tmp_path / "source", backend="cpu")
    resources = simulation.environment.resources.copy()
    residue = simulation.environment.resource_residue.copy()
    genotype = simulation.entities.genotype.copy()
    original = simulation.environment.resource_processing_support_field(17)
    simulation.apply_intervention("reverse-spatial-processing-support")
    reversed_support = simulation.environment.resource_processing_support_field(17)
    assert np.array_equal(reversed_support, original[:, ::-1, ::-1])
    assert np.array_equal(simulation.environment.resources, resources)
    assert np.array_equal(simulation.environment.resource_residue, residue)
    assert np.array_equal(simulation.entities.genotype, genotype)
    checkpoint = simulation.save_full_checkpoint(tmp_path / "response.sechk")
    restored = Simulation.from_checkpoint(
        checkpoint, tmp_path / "restored", backend="cpu", until_tick=2
    )
    assert restored.environment.resource_processing_support_reversed
    assert np.array_equal(
        restored.environment.resource_processing_support_field(17), reversed_support
    )


def test_d3f_shared_checkpoint_triplet_and_response_trajectory(tmp_path: Path) -> None:
    cfg = _small_cfg(ticks=8)
    payload = execute_processing_response(
        cfg,
        (59001,),
        tmp_path / "run",
        backend="cpu",
        until_tick=8,
        observation_period=4,
    )
    assert payload["schema"] == "d3-spatial-processing-response-results-v2"
    pair = payload["pairs"][0]
    assert pair["shared_checkpoint_state"]
    branches = {row["branch"]: row for row in pair["branches"]}
    assert branches["original-support"]["interventions"] == []
    assert branches["reversed-support"]["interventions"] == [
        "reverse-spatial-processing-support"
    ]
    assert branches["neutral-support"]["interventions"] == [
        "neutralize-spatial-processing-support"
    ]
    assert not branches["original-support"]["final"][
        "resource_processing_support_orientation_reversed"
    ]
    assert branches["reversed-support"]["final"][
        "resource_processing_support_orientation_reversed"
    ] == 1
    assert not branches["neutral-support"]["final"][
        "resource_processing_support_orientation_reversed"
    ]
    assert branches["reversed-support"]["scientific_validity"]["strategy"][
        "resource_processing_support_orientation_reversed"
    ]
    for branch in branches.values():
        assert [row["tick"] for row in branch["response_trajectory"]] == [0, 4, 8]
        assert branch["response_summary"]["eligible_entity_ticks"] > 0.0
    assert all(row["valid"] for row in payload["external_resource_ledger"])
    assert all(row["valid"] for row in payload["external_recycling_ledger"])
    audit = build_protocol_audit(D3E)
    assert audit["schema"] == "structural-measurement-protocol-audit-v29"
    protocol = audit["functional_module_protocol"][
        "spatial_processing_response_audit"
    ]
    assert protocol["read_only_tick_observer"]
    assert not protocol["movement_reward_or_controller_added"]
    assert not protocol["support_sensor_added"]
    assert not protocol["stable_migration_or_ecotype_claim"]
