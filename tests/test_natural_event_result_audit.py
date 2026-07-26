from __future__ import annotations

from pathlib import Path

from se.experiments import natural_event_execution as execution
from se.analysis.natural_event_result_audit import build_result_audit
from tests.test_natural_event_execution import _manifest


def test_partial_v2_result_generates_common_boundary_followup(tmp_path: Path) -> None:
    manifest, actual_root = _manifest(tmp_path)
    plan = execution.build_execution_plan(
        manifest,
        path_prefixes=((Path("/old/machine/runs"), actual_root),),
        interventions=("freeze-group-refresh",),
        common_boundary_audit=False,
    )
    results = []
    for anchor in plan["selected_anchors"]:
        results.append(
            {
                "anchor": anchor,
                "baseline_region_summary": {},
                "branches": [
                    {
                        "intervention": "freeze-group-refresh",
                        "eligible": True,
                        "region_summary": {"final_cohesion_region": 0.1},
                        "delta": {"final_cohesion_region": -0.2},
                        "intervention_history": [
                            {
                                "type": "freeze-group-refresh",
                                "existing_group_labels_modified": False,
                            }
                        ],
                    }
                ],
            }
        )
    report = {
        "schema": "natural-event-paired-intervention-results-v2",
        "manifest_sha256": plan["manifest_sha256"],
        "execution_plan_sha256": plan["execution_plan_sha256"],
        "trajectory_count": plan["trajectory_count"],
        "executed_trajectory_count": plan["trajectory_count"],
        "resumed_trajectory_count": 0,
        "results": results,
        "aggregation": execution.aggregate_results(results),
    }
    audit = build_result_audit(report, plan, manifest)
    assert audit["outcome_audit"]["common_boundary"]["observed"] is False
    assert "common_boundary_rerun" in audit["followup_plans"]
    followup = audit["followup_plans"]["common_boundary_rerun"]
    assert followup["diagnostics"]["common_boundary_audit"] is True
    assert followup["trajectory_count"] == 2
