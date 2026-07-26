from __future__ import annotations

import hashlib
import json
from pathlib import Path

from subject_evolution import natural_event_execution as execution
from subject_evolution.natural_event_matrix import SCHEMA, SELECTION_SCHEMA, _canonical_sha256


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _manifest(tmp_path: Path) -> tuple[dict[str, object], Path]:
    actual_root = tmp_path / "new_root"
    run_dir = actual_root / "seed_10001"
    run_dir.mkdir(parents=True)
    progress = run_dir / "evolution_progress.jsonl"
    progress.write_text('{"tick": 30}\n', encoding="utf-8")
    config = run_dir / "resolved_config.json"
    config.write_text('{"run":{"seed":10001}}', encoding="utf-8")
    checkpoint = run_dir / "checkpoint_00000060.sechk"
    checkpoint.write_bytes(b"trusted-checkpoint")
    old_root = Path("/old/machine/runs")
    old_run = old_root / "seed_10001"
    interventions = [
        {"intervention": "disable-knowledge-policy", "eligible": True, "reason": None},
        {"intervention": "freeze-group-refresh", "eligible": True, "reason": None},
        {"intervention": "neutralize-danger-evidence", "eligible": False, "reason": "disabled"},
    ]
    anchors = []
    for index, event_tick in enumerate((90, 120)):
        anchors.append(
            {
                "anchor_id": f"seed_10001-crowding-r{index}-t{event_tick}",
                "run_name": "seed_10001",
                "seed": 10001,
                "run_dir": str(old_run),
                "event_kind": "crowding",
                "exposure_field": "spatial_local_region_crowding",
                "region_id": index,
                "event_tick": event_tick,
                "event_value": 3.0 + index,
                "region_threshold": 2.0,
                "standardized_score": 3.5,
                "alive_region": 20,
                "checkpoint_tick": 60,
                "checkpoint_path": str(old_run / checkpoint.name),
                "checkpoint_sha256": _sha(checkpoint),
                "until_tick": event_tick + 30,
                "selection_record_index": index,
                "interventions": interventions,
            }
        )
    payload: dict[str, object] = {
        "schema": SCHEMA,
        "selection_schema": SELECTION_SCHEMA,
        "selection_protocol": {
            "post_event_outcomes_used_for_selection": False,
            "analysis_summary_used_for_selection": False,
        },
        "paired_randomness": True,
        "baseline_and_intervention_share_checkpoint": True,
        "horizon_ticks": 30,
        "source_runs": [
            {
                "run_name": "seed_10001",
                "seed": 10001,
                "run_dir": str(old_run),
                "progress_path": str(old_run / progress.name),
                "progress_sha256": _sha(progress),
                "config_path": str(old_run / config.name),
                "config_sha256": _sha(config),
                "final_tick": 120,
                "record_count": 4,
            }
        ],
        "analysis_context": None,
        "anchors": anchors,
        "interpretation_boundary": "test boundary",
    }
    payload["plan_sha256"] = _canonical_sha256(payload)
    return payload, actual_root


def test_execution_plan_remaps_and_deduplicates(tmp_path: Path) -> None:
    manifest, actual_root = _manifest(tmp_path)
    plan = execution.build_execution_plan(
        manifest,
        path_prefixes=((Path("/old/machine/runs"), actual_root),),
        interventions=("disable-knowledge-policy", "freeze-group-refresh"),
    )
    execution.validate_execution_plan(plan)
    assert plan["selected_anchor_count"] == 2
    assert plan["naive_branch_count"] == 6
    assert plan["trajectory_count"] == 3
    assert plan["deduplicated_branch_count"] == 3
    assert {item["until_tick"] for item in plan["trajectories"]} == {150}
    preflight = execution.preflight_execution_plan(plan)
    assert preflight["execution_ready"] is True
    assert preflight["full_audit_ready"] is True
    assert all(item["hash_match"] for item in preflight["checks"])


def test_execute_plan_resumes_shared_trajectories(tmp_path: Path, monkeypatch) -> None:
    manifest, actual_root = _manifest(tmp_path)
    plan = execution.build_execution_plan(
        manifest,
        path_prefixes=((Path("/old/machine/runs"), actual_root),),
        interventions=("disable-knowledge-policy",),
    )
    calls: list[tuple[str | None, int]] = []

    def fake_run_branch(checkpoint, output_dir, *, until_tick, backend, gpu_semantics_mode, intervention):
        calls.append((intervention, until_tick))
        output = Path(output_dir)
        output.mkdir(parents=True, exist_ok=True)
        records = []
        for tick in (90, 120, 150):
            value = 1 if intervention is None else 2
            records.append(
                {
                    "tick": tick,
                    "spatial_local_region_alive": [10 + value, 20 + value],
                    "spatial_local_region_boundary_cohesion": [0.2 * value, 0.3 * value],
                    "spatial_local_region_resource_scarcity": [0.8, 0.7],
                    "spatial_local_region_mortality_pressure": [0.1, 0.2],
                    "spatial_local_region_active_transferred_roots": [5 * value, 6 * value],
                    "spatial_local_region_transfer_committed_outgoing": [value, value],
                    "spatial_local_region_transfer_committed_incoming": [value, value],
                    "spatial_local_region_new_transferred_roots": [value, value],
                    "spatial_local_region_lost_transferred_roots": [0, 0],
                }
            )
        (output / "evolution_progress.jsonl").write_text(
            "".join(json.dumps(item) + "\n" for item in records), encoding="utf-8"
        )
        return {
            "records": records,
            "scientific_validity": {"valid": True},
            "intervention_history": [] if intervention is None else [intervention],
        }

    monkeypatch.setattr(execution, "_run_branch", fake_run_branch)
    output = tmp_path / "output"
    first = execution.execute_plan(plan, output)
    assert len(calls) == 2
    assert first["executed_trajectory_count"] == 2
    assert first["resumed_trajectory_count"] == 0
    assert first["deduplicated_branch_count"] == 2
    assert len(first["results"]) == 2
    assert first["results"][0]["baseline_region_summary"]["final_tick"] == 120
    assert first["results"][1]["baseline_region_summary"]["final_tick"] == 150
    assert first["results"][0]["branches"][0]["delta"]["final_alive_region"] == 1.0

    second = execution.execute_plan(plan, output)
    assert len(calls) == 2
    assert second["executed_trajectory_count"] == 0
    assert second["resumed_trajectory_count"] == 2


def test_seed_level_aggregation_averages_anchors_before_sign_count() -> None:
    results = []
    values = {10001: (2.0, 4.0), 10002: (-1.0, -3.0), 10003: (1.0, -1.0)}
    for seed, pair in values.items():
        for index, value in enumerate(pair):
            results.append(
                {
                    "anchor": {
                        "seed": seed,
                        "event_kind": "crowding",
                        "anchor_id": f"a-{seed}-{index}",
                    },
                    "branches": [
                        {
                            "intervention": "freeze-group-refresh",
                            "eligible": True,
                            "delta": {"final_cohesion_region": value},
                        }
                    ],
                }
            )
    report = execution.aggregate_results(results)
    group = report["groups"][0]
    assert group["anchor_level"]["count"] == 6
    assert group["seed_level"]["count"] == 3
    assert group["seed_level"]["positive"] == 1
    assert group["seed_level"]["negative"] == 1
    assert group["seed_level"]["zero"] == 1
