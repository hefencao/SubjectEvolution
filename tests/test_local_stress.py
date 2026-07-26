from __future__ import annotations

from dataclasses import replace
import json
from pathlib import Path

import numpy as np

from subject_evolution.config import load_config, validate_config
from subject_evolution.local_stress import LocalStressDiagnostics
from subject_evolution.long_run_analysis import analyze
from subject_evolution.simulation import Simulation


ROOT = Path(__file__).resolve().parents[1]


def test_local_stress_tracker_accounts_regions_and_benefits() -> None:
    tracker = LocalStressDiagnostics(
        world_width=8.0,
        world_height=8.0,
        regions_x=2,
        regions_y=2,
        resource_capacity=(1.0, 1.0, 1.0, 1.0),
        world_grid_x=4,
        world_grid_y=4,
    )
    x = np.asarray([1.0, 2.0, 6.0, 6.5], dtype=np.float32)
    y = np.asarray([1.0, 2.0, 1.0, 6.0], dtype=np.float32)
    cells = np.asarray([0, 0, 3, 15], dtype=np.int32)
    resources = np.asarray(
        [[0.0] * 4, [0.5] * 4, [1.0] * 4, [0.25] * 4], dtype=np.float32
    )
    hazard = np.asarray([0.1, 0.3, 0.2, 0.8], dtype=np.float32)
    tracker.observe_population(
        x=x, y=y, cell_ids=cells, local_resources=resources, local_hazard=hazard
    )
    tracker.observe_births(np.asarray([2], dtype=np.int32), x, y)
    tracker.observe_deaths(np.asarray([1], dtype=np.int32), x, y)
    groups = np.asarray([10, 10, 20, 30], dtype=np.uint64)
    tracker.observe_benefits(
        owner_indices=np.asarray([0, 2], dtype=np.int32),
        target_indices=np.asarray([1, 3], dtype=np.int32),
        group_ids=groups,
        amounts=np.asarray([1.0, 2.0]),
        x=x,
        y=y,
    )
    result = tracker.consume_window()
    assert result["spatial_local_region_alive"] == [2, 1, 0, 1]
    assert sum(result["spatial_local_region_deaths"]) == 1
    assert sum(result["spatial_local_region_births"]) == 1
    assert result["spatial_local_region_boundary_cohesion"][0] == 1.0
    assert result["spatial_local_region_boundary_cohesion"][1] == 0.0
    assert result["spatial_local_observed_ticks"] == 1


def test_reference_boundary_uses_checkpoint_groups_and_stable_ids() -> None:
    tracker = LocalStressDiagnostics(
        world_width=8.0,
        world_height=8.0,
        regions_x=2,
        regions_y=2,
        resource_capacity=(1.0, 1.0, 1.0, 1.0),
        world_grid_x=4,
        world_grid_y=4,
    )
    x = np.asarray([1.0, 2.0, 6.0], dtype=np.float32)
    y = np.asarray([1.0, 2.0, 1.0], dtype=np.float32)
    stable = np.asarray([11, 12, 13], dtype=np.uint64)
    checkpoint_groups = np.asarray([7, 7, 9], dtype=np.uint64)
    tracker.freeze_reference_boundary(
        tick=30,
        alive=np.asarray([True, True, True]),
        stable_ids=stable,
        group_tokens=checkpoint_groups,
    )
    current_groups = np.asarray([100, 200, 200], dtype=np.uint64)
    # Slot 2 is reused by a new entity and must not inherit checkpoint group 9.
    current_stable = np.asarray([11, 12, 99], dtype=np.uint64)
    tracker.observe_benefits(
        owner_indices=np.asarray([0, 2], dtype=np.int32),
        target_indices=np.asarray([1, 1], dtype=np.int32),
        group_ids=current_groups,
        stable_ids=current_stable,
        amounts=np.asarray([1.0, 2.0]),
        x=x,
        y=y,
    )
    result = tracker.consume_window()
    assert result["spatial_local_reference_boundary_snapshot_tick"] == 30
    assert result["spatial_local_region_boundary_cohesion"][0] == 0.0
    assert result["spatial_local_region_reference_boundary_cohesion"][0] == 1.0
    # Reused slot 2 is ungrouped under the reference boundary, so its transfer
    # to checkpoint member slot 1 is cross-boundary rather than inherited-internal.
    assert result["spatial_local_region_reference_benefit_cross_boundary"][1] == 2.0


def test_spatial_stress_config_is_opt_in() -> None:
    cfg = load_config(ROOT / "configs" / "heterogeneous_smoke.json")
    bad = replace(
        cfg,
        run=replace(
            cfg.run,
            spatial_stress_diagnostics_enabled=True,
            spatial_stress_diagnostics_schema="disabled",
        ),
    )
    try:
        validate_config(bad)
    except ValueError as exc:
        assert "spatial stress diagnostics" in str(exc)
    else:
        raise AssertionError("mismatched spatial diagnostic schema was accepted")


def test_spatial_stress_progress_and_checkpoint_restore(tmp_path: Path) -> None:
    cfg = load_config(ROOT / "configs" / "heterogeneous_smoke.json")
    cfg = replace(
        cfg,
        run=replace(
            cfg.run,
            ticks=6,
            checkpoint_period=3,
            evolution_evaluation_period=3,
            full_checkpoint_enabled=True,
            long_run_diagnostics_enabled=True,
            long_run_diagnostics_schema="long-run-evolution-diagnostics-v1",
            spatial_stress_diagnostics_enabled=True,
            spatial_stress_diagnostics_schema="spatial-local-stress-diagnostics-v1",
            spatial_stress_regions_x=2,
            spatial_stress_regions_y=2,
        ),
        world=replace(cfg.world, initial_entities=64, max_entities=96),
    )
    simulation = Simulation(cfg, tmp_path / "run", backend="cpu")
    simulation.run(until_tick=3)
    record = simulation.evolution_progress.records[-1]
    assert record["spatial_local_stress_schema"] == "spatial-local-stress-diagnostics-v1"
    assert len(record["spatial_local_region_alive"]) == 4
    restored = Simulation.from_checkpoint(
        tmp_path / "run" / "checkpoint_00000003.sechk",
        tmp_path / "restored",
        backend="cpu",
        until_tick=6,
    )
    restored.run(until_tick=6)
    assert restored.evolution_progress.records[-1]["spatial_local_observed_ticks"] == 3


def test_checkpoint_common_boundary_emits_reference_metrics(tmp_path: Path) -> None:
    cfg = load_config(ROOT / "configs" / "heterogeneous_smoke.json")
    cfg = replace(
        cfg,
        run=replace(
            cfg.run,
            ticks=6,
            checkpoint_period=3,
            evolution_evaluation_period=3,
            full_checkpoint_enabled=True,
            spatial_stress_diagnostics_enabled=True,
            spatial_stress_diagnostics_schema="spatial-local-stress-diagnostics-v1",
            spatial_stress_regions_x=2,
            spatial_stress_regions_y=2,
        ),
        world=replace(cfg.world, initial_entities=64, max_entities=96),
    )
    source = Simulation(cfg, tmp_path / "source", backend="cpu")
    source.run(until_tick=3)
    restored = Simulation.from_checkpoint(
        tmp_path / "source" / "checkpoint_00000003.sechk",
        tmp_path / "paired",
        backend="cpu",
        until_tick=6,
    )
    restored.freeze_local_reference_boundary()
    restored.run(until_tick=6)
    record = restored.evolution_progress.records[-1]
    assert record["spatial_local_reference_boundary_snapshot_tick"] == 3
    assert len(record["spatial_local_region_reference_boundary_cohesion"]) == 4
    assert len(record["spatial_local_region_boundary_definition_gap"]) == 4


def test_long_run_analysis_builds_local_spatial_panel(tmp_path: Path) -> None:
    path = tmp_path / "run" / "evolution_progress.jsonl"
    path.parent.mkdir()
    rows = []
    for index in range(8):
        mortality = [0.01 + index * 0.002, 0.04 + index * 0.003]
        cohesion = [0.2 + index * 0.01, 0.5 + index * 0.015]
        rows.append(
            {
                "tick": (index + 1) * 30,
                "alive": 100,
                "deaths_window": 5,
                "mortality_pressure_window": 0.05,
                "effective_lineages": 20 - index,
                "largest_lineage_fraction": 0.1 + index * 0.01,
                "strategy_effective_dimensions": 30 - index,
                "window_action_entropy": 1.8 - index * 0.01,
                "benefit_boundary_cohesion": 0.3 + index * 0.01,
                "spatial_local_stress_schema": "spatial-local-stress-diagnostics-v1",
                "spatial_local_region_mortality_pressure": mortality,
                "spatial_local_region_boundary_cohesion": cohesion,
                "spatial_local_region_cohesion_valid": [True, True],
                "spatial_local_region_resource_scarcity": [0.2, 0.7],
                "spatial_local_region_hazard_exposure": [0.1, 0.5],
                "spatial_local_region_crowding": [2.0, 5.0],
                "spatial_local_region_alive_change_rate": [0.01, -0.02],
                "spatial_local_region_entity_ticks": [1000, 1000],
                "spatial_local_population_cv": 0.2,
                "spatial_local_mortality_pressure_cv": 0.5,
                "spatial_local_resource_scarcity_cv": 0.4,
                "spatial_local_cohesion_cv": 0.3,
            }
        )
    path.write_text("\n".join(json.dumps(row) for row in rows) + "\n")
    report = analyze([path])
    spatial = report["runs"][0]["spatial_local_analysis"]
    assert report["schema"] == "multi-seed-long-run-analysis-v8"
    assert spatial["available"] is True
    assert spatial["region_count"] == 2
    assert spatial["max_local_to_global_mortality_ratio"] > 1.0


def test_knowledge_alignment_small_sample_entropy_roundoff_is_safe(tmp_path: Path) -> None:
    cfg = load_config(ROOT / "configs" / "mvp_short_latent_l2_memory_topk_inherited_heterogeneous_budget_matched_costed_transfer_local_stress_validation.json")
    cfg = replace(cfg, run=replace(cfg.run, ticks=60, checkpoint_period=999))
    simulation = Simulation(cfg, tmp_path / "small", backend="cpu")
    simulation.run(until_tick=60)
    assert simulation.evolution_progress.records[-1]["tick"] == 60


def test_local_culture_tracker_accounts_transfer_flows_and_roots() -> None:
    from subject_evolution.knowledge import (
        KnowledgeTransferCommitAudit,
        KnowledgeTransferPlan,
    )

    tracker = LocalStressDiagnostics(
        world_width=8.0,
        world_height=8.0,
        regions_x=2,
        regions_y=2,
        resource_capacity=(1.0, 1.0, 1.0, 1.0),
        world_grid_x=4,
        world_grid_y=4,
        schema="spatial-local-stress-culture-diagnostics-v2",
    )
    x = np.asarray([1.0, 6.0, 1.0], dtype=np.float32)
    y = np.asarray([1.0, 1.0, 6.0], dtype=np.float32)
    plan = KnowledgeTransferPlan(
        tick=1,
        sender_entity_indices=np.asarray([0, 1], dtype=np.int32),
        receiver_entity_indices=np.asarray([1, 2], dtype=np.int32),
        sender_subject_ids=np.asarray([1, 2], dtype=np.uint64),
        receiver_subject_ids=np.asarray([2, 3], dtype=np.uint64),
        source_subject_ids=np.asarray([1, 2], dtype=np.uint64),
        source_copy_ids=np.asarray([1, 2], dtype=np.uint64),
        content_ids=np.asarray([1, 2], dtype=np.uint64),
        encoded_bytes=np.asarray([10, 20], dtype=np.uint32),
        delivered=np.asarray([True, True]),
        corrupted=np.asarray([False, False]),
    )
    audit = KnowledgeTransferCommitAudit(
        tick=1,
        sender_entity_indices=np.asarray([0], dtype=np.int32),
        receiver_entity_indices=np.asarray([1], dtype=np.int32),
        committed_content_ids=np.asarray([1], dtype=np.uint64),
        committed_root_ids=np.asarray([1], dtype=np.uint64),
        committed_bytes=np.asarray([10], dtype=np.uint32),
    )
    tracker.observe_transfers(plan=plan, audit=audit, x=x, y=y)
    tracker.observe_transferred_roots(
        entity_indices=np.asarray([1, 2], dtype=np.int32),
        root_ids=np.asarray([1, 1], dtype=np.uint64),
        x=x,
        y=y,
    )
    result = tracker.consume_window()
    assert result["spatial_local_transfer_cross_region_attempts"] == 2
    assert result["spatial_local_transfer_cross_region_committed"] == 1
    assert result["spatial_local_region_transfer_committed_outgoing"][0] == 1
    assert result["spatial_local_region_transfer_committed_incoming"][1] == 1
    assert result["spatial_local_multi_region_transferred_root_count"] == 1
    assert sum(result["spatial_local_region_new_transferred_roots"]) == 2


def test_long_run_analysis_builds_local_cultural_panel(tmp_path: Path) -> None:
    path = tmp_path / "run" / "evolution_progress.jsonl"
    path.parent.mkdir()
    rows = []
    for index in range(10):
        scarcity = [0.2 + 0.01 * index, 0.5 + 0.02 * (index % 3)]
        cohesion = [0.3 + 0.02 * index, 0.4 + 0.01 * index]
        rows.append(
            {
                "tick": (index + 1) * 30,
                "alive": 100,
                "deaths_window": 5,
                "mortality_pressure_window": 0.05,
                "effective_lineages": 20 - index * 0.1,
                "largest_lineage_fraction": 0.1 + index * 0.001,
                "strategy_effective_dimensions": 30 - index * 0.1,
                "window_action_entropy": 1.8 - index * 0.001,
                "benefit_boundary_cohesion": 0.3 + index * 0.01,
                "spatial_local_stress_schema": "spatial-local-stress-culture-diagnostics-v2",
                "spatial_local_region_mortality_pressure": [0.02, 0.05],
                "spatial_local_region_boundary_cohesion": cohesion,
                "spatial_local_region_cohesion_valid": [True, True],
                "spatial_local_region_resource_scarcity": scarcity,
                "spatial_local_region_hazard_exposure": [0.1, 0.2],
                "spatial_local_region_crowding": [2.0, 3.0],
                "spatial_local_region_alive_change_rate": [0.01, -0.01],
                "spatial_local_region_entity_ticks": [1000, 1000],
                "spatial_local_population_cv": 0.1,
                "spatial_local_mortality_pressure_cv": 0.2,
                "spatial_local_resource_scarcity_cv": 0.3,
                "spatial_local_cohesion_cv": 0.2,
                "spatial_local_region_transfer_attempts_outgoing": [10, 8],
                "spatial_local_region_transfer_attempts_incoming": [8, 10],
                "spatial_local_region_transfer_committed_outgoing": [8, 6],
                "spatial_local_region_transfer_committed_incoming": [6, 8],
                "spatial_local_region_new_transferred_roots": [index + 1, 2],
                "spatial_local_region_lost_transferred_roots": [1, 1],
                "spatial_local_region_active_transferred_roots": [10 + index, 9],
                "spatial_local_transfer_commit_rate_by_source": [0.8, 0.75],
                "spatial_local_transfer_commit_flow": [[4, 4], [2, 4]],
                "spatial_local_transfer_same_region_committed": 8,
                "spatial_local_transfer_cross_region_committed": 6,
                "spatial_local_active_transferred_root_count": 15 + index,
                "spatial_local_multi_region_transferred_root_count": 4,
            }
        )
    path.write_text("\n".join(json.dumps(row) for row in rows) + "\n")
    report = analyze([path])
    cultural = report["runs"][0]["spatial_local_analysis"][
        "local_cultural_transfer_analysis"
    ]
    assert cultural["available"] is True
    assert cultural["total_cross_region_committed"] == 60
    assert cultural["high_scarcity_event_study"]["event_count"] >= 1


def test_event_cohort_diagnostics_integrate_with_checkpoint_branch(tmp_path: Path) -> None:
    cfg = load_config(ROOT / "configs" / "heterogeneous_smoke.json")
    cfg = replace(
        cfg,
        run=replace(
            cfg.run,
            ticks=6,
            checkpoint_period=3,
            evolution_evaluation_period=3,
            full_checkpoint_enabled=True,
            spatial_stress_diagnostics_enabled=True,
            spatial_stress_diagnostics_schema="spatial-local-stress-diagnostics-v1",
            spatial_stress_regions_x=2,
            spatial_stress_regions_y=2,
        ),
        world=replace(cfg.world, initial_entities=64, max_entities=96),
    )
    source = Simulation(cfg, tmp_path / "source", backend="cpu")
    source.run(until_tick=3)
    branch = Simulation.from_checkpoint(
        tmp_path / "source" / "checkpoint_00000003.sechk",
        tmp_path / "branch",
        backend="cpu",
        until_tick=6,
    )
    branch.configure_event_cohort_diagnostics(
        [
            {
                "anchor_id": "integration-anchor",
                "region_id": 0,
                "event_tick": 4,
                "until_tick": 6,
            }
        ]
    )
    branch.run(until_tick=6)
    summary = branch.event_cohort_summaries()["integration-anchor"]
    assert summary["endpoint_population_balance_residual"] == 0
    assert summary["event_cohort_feedback_to_world"] is False
    assert summary["final_alive_region_from_cohort_audit"] >= 0
