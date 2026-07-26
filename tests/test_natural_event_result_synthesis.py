from __future__ import annotations

from pathlib import Path

from subject_evolution import natural_event_execution as execution
from subject_evolution.natural_event_result_synthesis import build_synthesis
from tests.test_natural_event_execution import _manifest


def _report(plan, *, common: bool) -> dict:
    results = []
    for anchor in plan["selected_anchors"]:
        baseline = {
            "final_alive_region": 10.0,
            "final_scarcity_region": 0.8,
            "final_mortality_region": 0.1,
            "final_active_transferred_roots_region": 5.0,
            "post_event_outgoing_commits": 1,
            "post_event_incoming_commits": 1,
            "post_event_new_transferred_roots": 1,
            "post_event_lost_transferred_roots": 0,
        }
        branch_summary = dict(baseline)
        branch_summary["final_alive_region"] = 11.0
        branch_summary["reference_boundary_available"] = common
        if common:
            branch_summary["post_event_reference_cohesion_region"] = 0.3
        results.append(
            {
                "anchor": anchor,
                "baseline_region_summary": baseline,
                "branches": [
                    {
                        "intervention": "freeze-group-refresh",
                        "eligible": True,
                        "region_summary": branch_summary,
                        "delta": execution._numeric_delta(branch_summary, baseline),
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
    return {
        "schema": "natural-event-paired-intervention-results-v3",
        "manifest_sha256": plan["manifest_sha256"],
        "execution_plan_sha256": plan["execution_plan_sha256"],
        "trajectory_count": plan["trajectory_count"],
        "results": results,
        "aggregation": execution.aggregate_results(results),
    }


def test_synthesis_prefers_richer_duplicate_and_generates_cohort_plan(tmp_path: Path) -> None:
    manifest, actual_root = _manifest(tmp_path)
    plan = execution.build_execution_plan(
        manifest,
        path_prefixes=((Path("/old/machine/runs"), actual_root),),
        interventions=("freeze-group-refresh",),
        event_cohort_audit=False,
    )
    plain = _report(plan, common=False)
    richer = _report(plan, common=True)
    synthesis = build_synthesis([plain, richer], manifest=manifest)
    assert synthesis["merged_anchor_count"] == 2
    assert synthesis["merged_pair_count"] == 2
    assert synthesis["coverage"]["complete"] is False
    assert synthesis["diagnostic_coverage"][0]["common_boundary"] == 2
    assert synthesis["intervention_timing_audit"]["common_pre_event_identity_proven"] is False
    assert "event_timed_primary" in synthesis["followup_plans"]
    assert synthesis["followup_plans"]["event_timed_primary"]["intervention_timing"] == "anchor-event-tick-v1"
    assert synthesis["followup_plans"]["event_timed_primary"]["diagnostics"][
        "event_cohort_audit"
    ] is True
