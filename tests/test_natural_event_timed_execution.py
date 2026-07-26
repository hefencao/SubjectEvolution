from __future__ import annotations

import json
from pathlib import Path

from se.experiments import natural_event_timed_execution as timed
from tests.test_natural_event_execution import _manifest


def test_timed_plan_separates_different_event_ticks(tmp_path: Path) -> None:
    manifest, actual_root = _manifest(tmp_path)
    plan = timed.build_timed_execution_plan(
        manifest,
        path_prefixes=((Path("/old/machine/runs"), actual_root),),
        interventions=("disable-knowledge-policy", "freeze-group-refresh"),
    )
    timed.validate_timed_execution_plan(plan)
    assert plan["intervention_timing"] == timed.INTERVENTION_TIMING
    assert plan["selected_anchor_count"] == 2
    assert plan["prefix_count"] == 2
    assert plan["naive_branch_count"] == 6
    assert plan["trajectory_count"] == 6
    assert plan["deduplicated_branch_count"] == 0
    assert {item["event_tick"] for item in plan["prefixes"]} == {90, 120}
    assert all(
        item["intervention_tick"] in {None, item["event_tick"]}
        for item in plan["trajectories"]
    )
    preflight = timed.preflight_timed_execution_plan(plan)
    assert preflight["execution_ready"] is True
    assert preflight["full_audit_ready"] is True


def test_timed_execution_proves_common_event_identity(tmp_path: Path, monkeypatch) -> None:
    manifest, actual_root = _manifest(tmp_path)
    plan = timed.build_timed_execution_plan(
        manifest,
        path_prefixes=((Path("/old/machine/runs"), actual_root),),
        interventions=("disable-knowledge-policy",),
    )

    def fake_prefix(prefix, output_dir, *, plan, backend, gpu_semantics_mode, overwrite_existing):
        output = Path(output_dir)
        output.mkdir(parents=True, exist_ok=True)
        event_checkpoint = output / "event.sechk"
        event_checkpoint.write_bytes(b"event")
        return {
            "schema": timed.PREFIX_MARKER_SCHEMA,
            "execution_plan_sha256": plan["execution_plan_sha256"],
            "manifest_sha256": plan["manifest_sha256"],
            "prefix_id": prefix["prefix_id"],
            "source_checkpoint_sha256": prefix["source_checkpoint_sha256"],
            "source_checkpoint_tick": prefix["source_checkpoint_tick"],
            "event_tick": prefix["event_tick"],
            "event_checkpoint_path": str(event_checkpoint),
            "event_checkpoint_file_sha256": "file",
            "event_checkpoint_state_sha256": f"state-{prefix['event_tick']}",
            "backend": backend,
            "gpu_semantics_mode": gpu_semantics_mode,
            "resumed": False,
        }

    def fake_branch(
        checkpoint,
        output_dir,
        *,
        until_tick,
        backend,
        gpu_semantics_mode,
        intervention,
        common_boundary_audit,
        cohort_requests,
    ):
        output = Path(output_dir)
        output.mkdir(parents=True, exist_ok=True)
        value = 1 if intervention is None else 2
        records = []
        for request in cohort_requests:
            tick = int(request["until_tick"])
            records.append(
                {
                    "tick": tick,
                    "spatial_local_region_alive": [10 + value, 20 + value],
                    "spatial_local_region_boundary_cohesion": [0.2, 0.3],
                    "spatial_local_reference_boundary_schema": "event-frozen",
                    "spatial_local_reference_boundary_snapshot_tick": int(request["event_tick"]),
                    "spatial_local_region_reference_boundary_cohesion": [0.2, 0.3],
                    "spatial_local_region_boundary_definition_gap": [0.0, 0.0],
                    "spatial_local_region_benefit_internal": [1.0, 1.0],
                    "spatial_local_region_benefit_cross_boundary": [1.0, 1.0],
                    "spatial_local_region_reference_benefit_internal": [1.0, 1.0],
                    "spatial_local_region_reference_benefit_cross_boundary": [1.0, 1.0],
                    "spatial_local_region_resource_scarcity": [0.8, 0.7],
                    "spatial_local_region_mortality_pressure": [0.1, 0.2],
                    "spatial_local_region_active_transferred_roots": [5.0, 6.0],
                    "spatial_local_region_transfer_committed_outgoing": [value, value],
                    "spatial_local_region_transfer_committed_incoming": [value, value],
                    "spatial_local_region_new_transferred_roots": [value, value],
                    "spatial_local_region_lost_transferred_roots": [0, 0],
                }
            )
        output.joinpath("evolution_progress.jsonl").write_text(
            "".join(json.dumps(item) + "\n" for item in records), encoding="utf-8"
        )
        summaries = {}
        for request in cohort_requests:
            summaries[str(request["anchor_id"])] = {
                "event_cohort_schema": timed.EVENT_COHORT_AUDIT_SCHEMA,
                "event_alive_region": 10,
                "event_global_ids_sha256": f"global-{request['event_tick']}",
                "event_region_ids_sha256": f"region-{request['anchor_id']}",
                "final_alive_region_from_cohort_audit": 10 + value,
                "final_event_cohort_retained_region": 7 + value,
                "final_event_cohort_survived_outside_region": 1,
                "final_event_cohort_absent": 2 - value,
                "final_existing_in_migrants_region": 2,
                "final_post_event_born_region": 1,
                "endpoint_population_change_region": value,
                "endpoint_population_change_reconstructed": value,
                "endpoint_population_balance_residual": 0,
                "event_cohort_survival_fraction": 0.8,
                "event_cohort_region_retention_fraction": 0.7,
            }
        return {
            "records": records,
            "scientific_validity": {"valid": True},
            "intervention_history": (
                []
                if intervention is None
                else [{"type": intervention, "tick": cohort_requests[0]["event_tick"]}]
            ),
            "event_cohort_summaries": summaries,
        }

    monkeypatch.setattr(timed, "_materialize_prefix_checkpoint", fake_prefix)
    monkeypatch.setattr(timed, "_run_branch", fake_branch)
    report = timed.execute_timed_plan(plan, tmp_path / "output")
    assert report["pre_event_pairing"]["all_valid"] is True
    assert report["pre_event_pairing"]["failure_count"] == 0
    assert len(report["results"]) == 2
    for item in report["results"]:
        branch = item["branches"][0]
        assert branch["pre_event_pairing"]["valid"] is True
        assert branch["delta"]["final_event_cohort_retained_region"] == 1.0
