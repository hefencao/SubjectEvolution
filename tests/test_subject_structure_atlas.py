from __future__ import annotations

from dataclasses import replace
import json
from pathlib import Path

import numpy as np

from subject_evolution.config import load_config, validate_config
from subject_evolution.environment_atlas import EnvironmentAtlasDiagnostics
from subject_evolution.simulation import Simulation
from subject_evolution.subject_structure import SubjectStructureDiagnostics


ROOT = Path(__file__).resolve().parents[1]


def test_subject_structure_detects_split_and_merge_from_stable_memberships(tmp_path: Path) -> None:
    tracker = SubjectStructureDiagnostics(tmp_path)
    stable_ids = np.arange(1, 9, dtype=np.uint64)
    first = tracker.observe_group_refresh(
        tick=10,
        group_tokens=np.asarray([10, 20], dtype=np.uint64),
        member_starts=np.asarray([0, 4], dtype=np.int64),
        member_counts=np.asarray([4, 2], dtype=np.int32),
        member_indices=np.asarray([0, 1, 2, 3, 4, 5], dtype=np.int32),
        stable_ids=stable_ids,
    )
    assert first["formation_count"] == 2
    second = tracker.observe_group_refresh(
        tick=20,
        group_tokens=np.asarray([10, 30], dtype=np.uint64),
        member_starts=np.asarray([0, 2], dtype=np.int64),
        member_counts=np.asarray([2, 4], dtype=np.int32),
        member_indices=np.asarray([0, 1, 2, 3, 4, 5], dtype=np.int32),
        stable_ids=stable_ids,
    )
    assert second["split_source_count"] == 1
    assert second["merge_target_count"] == 1
    assert second["same_token_groups"] == 1
    assert second["exact_membership_groups"] == 0
    assert second["overlap_edge_count"] == 3
    assert 0.0 < second["member_weighted_predecessor_jaccard"] < 1.0


def test_subject_structure_uses_stable_ids_not_reused_slots(tmp_path: Path) -> None:
    tracker = SubjectStructureDiagnostics(tmp_path)
    tracker.observe_group_refresh(
        tick=1,
        group_tokens=np.asarray([10], dtype=np.uint64),
        member_starts=np.asarray([0], dtype=np.int64),
        member_counts=np.asarray([2], dtype=np.int32),
        member_indices=np.asarray([0, 1], dtype=np.int32),
        stable_ids=np.asarray([101, 102], dtype=np.uint64),
    )
    record = tracker.observe_group_refresh(
        tick=2,
        group_tokens=np.asarray([10], dtype=np.uint64),
        member_starts=np.asarray([0], dtype=np.int64),
        member_counts=np.asarray([2], dtype=np.int32),
        member_indices=np.asarray([0, 1], dtype=np.int32),
        stable_ids=np.asarray([201, 202], dtype=np.uint64),
    )
    assert record["same_token_groups"] == 1
    assert record["exact_membership_groups"] == 0
    assert record["formation_count"] == 1
    assert record["dissolution_count"] == 1
    assert record["overlap_edge_count"] == 0


def test_environment_atlas_reports_multiscale_heterogeneity_and_association(tmp_path: Path) -> None:
    atlas = EnvironmentAtlasDiagnostics(
        tmp_path,
        world_width=4.0,
        world_height=4.0,
        world_grid_x=4,
        world_grid_y=4,
        resource_capacity=(1.0, 1.0, 1.0, 1.0),
        scales=((2, 2), (4, 4)),
    )
    resources = np.zeros((4, 4, 4), dtype=np.float32)
    resources[0, :, :2] = 1.0
    resources[1, :, 2:] = 1.0
    resources[2] = 0.25
    resources[3] = 0.5
    x = np.asarray([0.5, 1.5, 2.5, 3.5], dtype=np.float32)
    y = np.asarray([0.5, 2.5, 0.5, 2.5], dtype=np.float32)
    compact = atlas.observe(
        tick=10,
        resources=resources,
        hazard=np.zeros((4, 4), dtype=np.float32),
        mortality_trace=np.zeros((4, 4), dtype=np.float32),
        alive=np.ones(4, dtype=bool),
        x=x,
        y=y,
        lineage_ids=np.asarray([1, 1, 2, 2], dtype=np.uint64),
        group_ids=np.asarray([10, 10, 20, 20], dtype=np.uint64),
    )
    assert compact["environment_atlas_scale_count"] == 2
    assert compact["environment_atlas_2x2_signature_mean_distance"] > 0.0
    assert compact["environment_atlas_2x2_lineage_association"] > 0.5
    assert compact["environment_atlas_2x2_social_association"] > 0.5
    assert atlas.metadata()["scales"][0]["partition_sha256"]

    changed = resources.copy()
    changed[0] *= 0.5
    second = atlas.observe(
        tick=20,
        resources=changed,
        hazard=np.zeros((4, 4), dtype=np.float32),
        mortality_trace=np.zeros((4, 4), dtype=np.float32),
        alive=np.ones(4, dtype=bool),
        x=x,
        y=y,
        lineage_ids=np.asarray([1, 1, 2, 2], dtype=np.uint64),
        group_ids=np.asarray([10, 10, 20, 20], dtype=np.uint64),
    )
    assert second["environment_atlas_2x2_temporal_turnover"] > 0.0


def test_diagnostic_config_validation_and_simulation_outputs(tmp_path: Path) -> None:
    cfg = load_config(ROOT / "configs" / "heterogeneous_smoke.json")
    cfg = replace(
        cfg,
        run=replace(
            cfg.run,
            ticks=6,
            metrics_period=6,
            checkpoint_period=3,
            evolution_evaluation_period=3,
            full_checkpoint_enabled=True,
            subject_structure_diagnostics_enabled=True,
            subject_structure_diagnostics_schema="stable-membership-subject-succession-v1",
            environment_atlas_diagnostics_enabled=True,
            environment_atlas_diagnostics_schema="multiscale-subject-environment-atlas-v1",
            environment_atlas_scales=((2, 2), (4, 4)),
        ),
        world=replace(cfg.world, initial_entities=48, max_entities=64),
        social=replace(
            cfg.social,
            group_update_mode="periodic-v1",
            group_update_period=1,
            group_min_members=2,
        ),
    )
    validate_config(cfg)
    simulation = Simulation(cfg, tmp_path / "run", backend="cpu")
    simulation.run(until_tick=6)
    assert (tmp_path / "run" / "subject_structure_summary.json").exists()
    assert (tmp_path / "run" / "environment_atlas_summary.json").exists()
    manifest = json.loads((tmp_path / "run" / "run_manifest.json").read_text())
    assert manifest["subject_structure_diagnostics_enabled"] is True
    assert manifest["environment_atlas_diagnostics_enabled"] is True
    assert len(manifest["environment_atlas"]["scales"]) == 2
    checkpoint = tmp_path / "run" / "checkpoint_00000006.sechk"
    restored = Simulation.from_checkpoint(
        checkpoint,
        tmp_path / "restored",
        backend="cpu",
        until_tick=6,
    )
    assert restored.subject_structure_diagnostics is not None
    assert restored.environment_atlas_diagnostics is not None
    assert restored.subject_structure_diagnostics.total_refreshes == simulation.subject_structure_diagnostics.total_refreshes
    assert len(restored.environment_atlas_diagnostics.records) == len(simulation.environment_atlas_diagnostics.records)
