from __future__ import annotations

from dataclasses import replace
import json
from pathlib import Path

import pytest

from subject_evolution.config import load_config
from subject_evolution.natural_event_matrix import (
    build_manifest,
    detect_exposure_events,
    load_manifest,
    validate_manifest,
)
from subject_evolution.simulation import Simulation


ROOT = Path(__file__).resolve().parents[1]


def _records() -> list[dict[str, object]]:
    records: list[dict[str, object]] = []
    for index in range(10):
        scarcity = [0.2, 0.25]
        crowding = [0.3, 0.35]
        mortality = [0.1, 0.12]
        if index == 5:
            scarcity[0] = 0.9
            crowding[1] = 0.95
            mortality[0] = 0.8
        if index == 7:
            scarcity[1] = 0.85
            crowding[0] = 0.9
            mortality[1] = 0.75
        records.append(
            {
                "tick": (index + 1) * 30,
                "alive": 100,
                "spatial_local_region_alive": [20, 20],
                "spatial_local_region_resource_scarcity": scarcity,
                "spatial_local_region_crowding": crowding,
                "spatial_local_region_mortality_pressure": mortality,
                # Deliberately unusable outcome validity. Exposure-only selection
                # must not consult this field.
                "spatial_local_region_cohesion_valid": [False, False],
                "knowledge_transfer_committed_total": index * 10,
                "group_update_count_total": 1 + index,
            }
        )
    return records


def _write_run(run_dir: Path, seed: int = 10001) -> None:
    run_dir.mkdir(parents=True)
    records = _records()
    (run_dir / "evolution_progress.jsonl").write_text(
        "".join(json.dumps(record) + "\n" for record in records),
        encoding="utf-8",
    )
    config = {
        "run": {"seed": seed},
        "entities": {
            "resource_affinity_schema": "normalized-four-resource-affinity-v1"
        },
        "social": {"group_update_mode": "adaptive-topology-v1"},
        "knowledge": {
            "enabled": True,
            "transfer_probability": 0.1,
            "policy_influence_enabled": True,
            "working_memory_enabled": True,
            "sparse_selection_enabled": True,
        },
    }
    (run_dir / "resolved_config.json").write_text(
        json.dumps(config), encoding="utf-8"
    )
    for tick in (60, 120, 180, 240):
        (run_dir / f"checkpoint_{tick:08d}.sechk").write_bytes(
            f"checkpoint-{tick}".encode()
        )


def test_exposure_selection_does_not_require_cohesion_outcomes() -> None:
    events = detect_exposure_events(
        _records(),
        event_kind="scarcity",
        quantile=0.75,
        max_events=2,
        min_tick=None,
        min_gap_windows=2,
        min_region_alive=5,
    )
    assert len(events) == 2
    assert {int(event["event_tick"]) for event in events} == {180, 240}


def test_manifest_is_hashed_and_marks_ineligible_mechanisms(tmp_path: Path) -> None:
    run_dir = tmp_path / "seed_10001"
    _write_run(run_dir)
    analysis = tmp_path / "analysis.json"
    analysis.write_text(
        json.dumps(
            {
                "schema": "multi-seed-long-run-analysis-v7",
                "run_count": 1,
                "repeated_local_directional_patterns": [
                    "local_culture.local_scarcity_vs_local_new_transferred_roots_within_region"
                ],
            }
        ),
        encoding="utf-8",
    )
    manifest = build_manifest(
        [run_dir],
        event_kinds=("scarcity", "crowding", "mortality"),
        quantile=0.75,
        max_events_per_kind=1,
        horizon_ticks=120,
        analysis_json=analysis,
    )
    validate_manifest(manifest)
    assert manifest["schema"] == "natural-event-paired-intervention-matrix-v2"
    assert manifest["selection_schema"] == "exposure-only-local-peak-selection-v2"
    assert manifest["region_partition_audit"]["physical_geometry_known"] is False
    assert manifest["selection_protocol"]["post_event_outcomes_used_for_selection"] is False
    assert len(manifest["anchors"]) == 3
    assert manifest["analysis_context"]["used_for_anchor_selection"] is False
    for anchor in manifest["anchors"]:
        assert anchor["candidate_rank"] >= anchor["selection_rank"] >= 1
        assert anchor["run_candidate_count"] >= 1
        assert "region_bounds" in anchor
        eligibility = {
            item["intervention"]: item for item in anchor["interventions"]
        }
        assert eligibility["freeze-group-refresh"]["eligible"] is True
        assert eligibility["neutralize-danger-evidence"]["eligible"] is False
        assert eligibility["disable-knowledge-transfer"]["eligible"] is True

    path = tmp_path / "manifest.json"
    path.write_text(json.dumps(manifest), encoding="utf-8")
    assert load_manifest(path)["plan_sha256"] == manifest["plan_sha256"]
    tampered = dict(manifest)
    tampered["horizon_ticks"] = 121
    with pytest.raises(ValueError, match="checksum mismatch"):
        validate_manifest(tampered)


def test_freeze_group_refresh_is_checkpointable(tmp_path: Path) -> None:
    base = load_config(ROOT / "configs" / "smoke_cpu.json")
    cfg = replace(
        base,
        run=replace(
            base.run,
            ticks=4,
            metrics_period=1,
            checkpoint_period=10,
            full_checkpoint_enabled=True,
        ),
        social=replace(
            base.social,
            group_update_mode="periodic-v1",
            group_update_period=1,
        ),
    )
    simulation = Simulation(cfg, tmp_path / "source", backend="cpu")
    simulation.apply_intervention("freeze-group-refresh")
    simulation.run(until_tick=4)
    assert simulation.social.group_update_count == 0
    assert simulation.social.group_update_skipped_count == 4
    assert simulation.social.last_group_update_reason == "intervention-frozen"
    checkpoint = simulation.save_full_checkpoint(tmp_path / "frozen.sechk")

    restored = Simulation.from_checkpoint(
        checkpoint,
        tmp_path / "restored",
        backend="cpu",
        until_tick=5,
    )
    assert restored.group_refresh_ablation_enabled is True
    restored.run(until_tick=5)
    assert restored.social.group_update_count == 0
    assert restored.social.last_group_update_reason == "intervention-frozen"
