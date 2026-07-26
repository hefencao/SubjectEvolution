"""Audit partial natural-event intervention results and preregister follow-ups.

The audit consumes immutable result, execution-plan, and optional manifest files.
It does not rerun trajectories or change the world.  Its purpose is to separate
manipulation checks, mechanism-proximal outcomes, measurement-coupled metrics,
and downstream regional state before scheduling the next paired branches.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from .natural_event_execution import (
    RESULT_SCHEMA,
    audit_outcomes,
    build_execution_plan,
    load_execution_plan,
    render_execution_plan_markdown,
)
from .natural_event_matrix import load_manifest


AUDIT_SCHEMA = "natural-event-result-audit-v1"
SUPPORTED_RESULT_SCHEMAS = {
    "natural-event-paired-intervention-results-v2",
    "natural-event-paired-intervention-results-v3",
    RESULT_SCHEMA,
}


def load_results(path: str | Path) -> dict[str, Any]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("natural-event results must be a JSON object")
    if payload.get("schema") not in SUPPORTED_RESULT_SCHEMAS:
        raise ValueError(f"unsupported natural-event result schema {payload.get('schema')!r}")
    return payload


def _eligible_manifest_interventions(manifest: dict[str, Any]) -> list[str]:
    result: list[str] = []
    for anchor in manifest.get("anchors", []):
        for entry in anchor.get("interventions", []):
            name = str(entry.get("intervention"))
            if bool(entry.get("eligible")) and name not in result:
                result.append(name)
    return result


def _result_coverage(report: dict[str, Any]) -> tuple[list[str], list[int], list[str], list[str]]:
    anchors = sorted(
        str(item.get("anchor", {}).get("anchor_id")) for item in report.get("results", [])
    )
    seeds = sorted(
        {int(item.get("anchor", {}).get("seed", 0)) for item in report.get("results", [])}
    )
    event_kinds = sorted(
        {
            str(item.get("anchor", {}).get("event_kind"))
            for item in report.get("results", [])
        }
    )
    interventions = sorted(
        {
            str(branch.get("intervention"))
            for item in report.get("results", [])
            for branch in item.get("branches", [])
            if branch.get("eligible")
        }
    )
    return anchors, seeds, event_kinds, interventions


def _direction(
    outcome_audit: dict[str, Any], intervention: str, metric: str
) -> dict[str, Any] | None:
    for row in outcome_audit.get("repeated_seed_directions", []):
        if row.get("intervention") == intervention and row.get("metric") == metric:
            return row
    return None


def build_result_audit(
    report: dict[str, Any],
    plan: dict[str, Any],
    manifest: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if str(report.get("execution_plan_sha256")) != str(plan.get("execution_plan_sha256")):
        raise ValueError("result and execution-plan SHA-256 values do not match")
    if str(report.get("manifest_sha256")) != str(plan.get("manifest_sha256")):
        raise ValueError("result and execution-plan manifest hashes do not match")
    if manifest is not None and str(manifest.get("plan_sha256")) != str(
        plan.get("manifest_sha256")
    ):
        raise ValueError("manifest and execution-plan hashes do not match")

    anchor_ids, seeds, event_kinds, interventions = _result_coverage(report)
    planned_anchor_ids = sorted(
        str(item.get("anchor_id")) for item in plan.get("selected_anchors", [])
    )
    result_complete_for_plan = anchor_ids == planned_anchor_ids
    outcome_report = dict(report)
    outcome_report.setdefault(
        "diagnostics",
        {
            "common_boundary_audit": False,
            "common_boundary_schema": None,
            "event_cohort_audit": False,
            "event_cohort_schema": None,
            "feedback_to_world": False,
        },
    )
    outcome = audit_outcomes(outcome_report)

    findings: list[dict[str, Any]] = []
    transfer_roots = _direction(
        outcome,
        "disable-knowledge-transfer",
        "final_active_transferred_roots_region",
    )
    if transfer_roots is not None:
        findings.append(
            {
                "id": "TRANSFER-MAINTAINS-LOCAL-CULTURAL-STATE",
                "status": "supported-mechanism-proximal",
                "evidence": transfer_roots,
                "interpretation": (
                    "Disabling future transfer reduced active transferred roots in the "
                    "selected regions in the same direction across seeds. This establishes "
                    "short-horizon maintenance of cultural state, not demographic benefit."
                ),
            }
        )
    transfer_alive = _direction(
        outcome, "disable-knowledge-transfer", "final_alive_region"
    )
    findings.append(
        {
            "id": "TRANSFER-DEMOGRAPHIC-BENEFIT",
            "status": (
                "cohort-decomposed-not-established"
                if outcome["event_cohort"]["observed"]
                else "event-cohort-rerun-required"
            ),
            "evidence": transfer_alive,
            "interpretation": (
                "Regional alive alone does not identify survival, endpoint absence, migration, "
                "or post-event births. Stable-ID event-cohort decomposition is required before "
                "any demographic interpretation."
            ),
        }
    )
    freeze_current = _direction(
        outcome, "freeze-group-refresh", "final_cohesion_region"
    )
    findings.append(
        {
            "id": "GROUP-REFRESH-COHESION",
            "status": (
                "common-boundary-evaluable"
                if outcome["common_boundary"]["observed"]
                else "measurement-entangled"
            ),
            "evidence": freeze_current,
            "interpretation": (
                "Current-label cohesion uses the labels modified by the intervention. "
                "A checkpoint-common boundary is required before attributing the repeated "
                "direction to social flow rather than boundary definition."
            ),
        }
    )
    affinity_alive = _direction(
        outcome, "neutralize-resource-affinity", "final_alive_region"
    )
    findings.append(
        {
            "id": "RESOURCE-AFFINITY-CROWDED-REGION-ALIVE",
            "status": (
                "cohort-decomposition-available"
                if outcome["event_cohort"]["observed"]
                else "event-cohort-rerun-required"
            ),
            "evidence": affinity_alive,
            "interpretation": (
                "The crowded-region alive count moved in one direction across seeds, but "
                "the metric mixes survival, births, deaths, and migration. Replicate in "
                "scarcity and mortality events and add cohort/retention outcomes before "
                "claiming an adaptive cost."
            ),
        }
    )

    audit: dict[str, Any] = {
        "schema": AUDIT_SCHEMA,
        "result_schema": str(report.get("schema")),
        "manifest_sha256": str(report.get("manifest_sha256")),
        "execution_plan_sha256": str(report.get("execution_plan_sha256")),
        "result_complete_for_execution_plan": result_complete_for_plan,
        "coverage": {
            "anchor_count": len(anchor_ids),
            "anchor_ids": anchor_ids,
            "seeds": seeds,
            "event_kinds": event_kinds,
            "interventions": interventions,
            "trajectory_count": int(report.get("trajectory_count", 0)),
            "executed_trajectory_count": int(
                report.get("executed_trajectory_count", 0)
            ),
            "resumed_trajectory_count": int(report.get("resumed_trajectory_count", 0)),
        },
        "outcome_audit": outcome,
        "findings": findings,
        "followup_plans": {},
        "interpretation_boundary": (
            "The supplied result covers only its selected execution plan. Directional "
            "agreement across three seeds is descriptive. Naturally occurring event "
            "exposures are not randomized. Region-level outcomes require stable-ID endpoint "
            "cohort decomposition before demographic interpretation."
        ),
    }

    if manifest is not None:
        path_prefixes = tuple(
            (Path(item["from"]), Path(item["to"]))
            for item in plan.get("path_prefixes", [])
        )
        all_events = sorted({str(anchor["event_kind"]) for anchor in manifest.get("anchors", [])})
        all_interventions = _eligible_manifest_interventions(manifest)
        if "freeze-group-refresh" in interventions and not outcome["common_boundary"]["observed"]:
            common_plan = build_execution_plan(
                manifest,
                path_prefixes=path_prefixes,
                anchor_ids=anchor_ids,
                interventions=("freeze-group-refresh",),
                common_boundary_audit=True,
                event_cohort_audit=True,
            )
            audit["followup_plans"]["common_boundary_rerun"] = common_plan
        if not outcome["event_cohort"]["observed"] and interventions:
            audit["followup_plans"]["event_cohort_rerun"] = build_execution_plan(
                manifest,
                path_prefixes=path_prefixes,
                anchor_ids=anchor_ids,
                interventions=interventions,
                common_boundary_audit=True,
                event_cohort_audit=True,
            )
        remaining_events = [event for event in all_events if event not in event_kinds]
        if remaining_events and interventions:
            audit["followup_plans"]["remaining_event_replication"] = build_execution_plan(
                manifest,
                path_prefixes=path_prefixes,
                event_kinds=remaining_events,
                interventions=interventions,
                common_boundary_audit=True,
                event_cohort_audit=True,
            )
        remaining_interventions = [
            name for name in all_interventions if name not in interventions
        ]
        if event_kinds and remaining_interventions:
            audit["followup_plans"]["remaining_mechanism_ablation"] = build_execution_plan(
                manifest,
                path_prefixes=path_prefixes,
                event_kinds=event_kinds,
                interventions=remaining_interventions,
                common_boundary_audit=True,
                event_cohort_audit=True,
            )
    return audit


def render_audit_markdown(audit: dict[str, Any]) -> str:
    coverage = audit["coverage"]
    lines = [
        "# Natural-event result audit",
        "",
        f"Result schema: `{audit['result_schema']}`",
        f"Execution-plan SHA-256: `{audit['execution_plan_sha256']}`",
        "",
        f"- Anchors: {coverage['anchor_count']}",
        f"- Seeds: {', '.join(str(value) for value in coverage['seeds'])}",
        f"- Events: {', '.join(coverage['event_kinds'])}",
        f"- Interventions: {', '.join(coverage['interventions'])}",
        f"- Complete for selected plan: {audit['result_complete_for_execution_plan']}",
        f"- Common boundary observed: {audit['outcome_audit']['common_boundary']['observed']}",
        f"- Event cohort observed: {audit['outcome_audit']['event_cohort']['observed']}",
        "",
        "## Findings",
        "",
    ]
    for finding in audit["findings"]:
        lines.extend(
            [
                f"### {finding['id']}",
                "",
                f"Status: **{finding['status']}**",
                "",
                finding["interpretation"],
                "",
            ]
        )
    lines.extend(["## Follow-up plans", ""])
    if not audit["followup_plans"]:
        lines.append("No follow-up execution plan was generated.")
    else:
        for name, plan in audit["followup_plans"].items():
            lines.append(
                f"- `{name}`: {plan['selected_anchor_count']} anchors, "
                f"{plan['trajectory_count']} shared trajectories, "
                f"{plan['deduplicated_branch_count']} deduplicated branches."
            )
    lines.extend(["", "## Interpretation boundary", "", audit["interpretation_boundary"], ""])
    return "\n".join(lines)


def write_audit_outputs(audit: dict[str, Any], output_dir: str | Path) -> None:
    root = Path(output_dir)
    root.mkdir(parents=True, exist_ok=True)
    serializable = dict(audit)
    plans = serializable.pop("followup_plans", {})
    plan_summaries = {
        name: {
            "schema": plan["schema"],
            "execution_plan_sha256": plan["execution_plan_sha256"],
            "selected_anchor_count": plan["selected_anchor_count"],
            "trajectory_count": plan["trajectory_count"],
            "deduplicated_branch_count": plan["deduplicated_branch_count"],
        }
        for name, plan in plans.items()
    }
    serializable["followup_plan_summaries"] = plan_summaries
    (root / "natural_event_result_audit.json").write_text(
        json.dumps(serializable, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (root / "natural_event_result_audit.md").write_text(
        render_audit_markdown(audit), encoding="utf-8"
    )
    for name, plan in plans.items():
        (root / f"{name}_execution_plan.json").write_text(
            json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        (root / f"{name}_execution_plan.md").write_text(
            render_execution_plan_markdown(plan), encoding="utf-8"
        )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Audit natural-event results and generate preregistered follow-up plans"
    )
    parser.add_argument("--results", required=True)
    parser.add_argument("--execution-plan", required=True)
    parser.add_argument("--manifest")
    parser.add_argument("--output", required=True)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    report = load_results(args.results)
    plan = load_execution_plan(args.execution_plan)
    manifest = load_manifest(args.manifest) if args.manifest else None
    audit = build_result_audit(report, plan, manifest)
    write_audit_outputs(audit, args.output)


if __name__ == "__main__":
    main()
