"""Synthesize multiple signed natural-event result sets without pooling anchors.

The synthesizer validates a shared manifest hash, prefers diagnostically richer
reruns for duplicate anchor/intervention pairs, recomputes seed-first
aggregation, reports coverage against the immutable manifest, and identifies
cross-event directional replication.  It never executes trajectories or
changes the simulated world.
"""

from __future__ import annotations

import argparse
from collections import defaultdict
import json
from pathlib import Path
from typing import Any, Iterable

from .natural_event_execution import (
    EVENT_COHORT_AUDIT_SCHEMA,
    RESULT_SCHEMA,
    aggregate_results,
    audit_outcomes,
    build_execution_plan,
    load_execution_plan,
    render_execution_plan_markdown,
)
from .natural_event_matrix import load_manifest


SYNTHESIS_SCHEMA = "natural-event-result-synthesis-v1"
SUPPORTED_RESULT_SCHEMAS = {
    "natural-event-paired-intervention-results-v2",
    "natural-event-paired-intervention-results-v3",
    RESULT_SCHEMA,
}
CORE_WORLD_KEYS = (
    "final_alive_region",
    "final_scarcity_region",
    "final_mortality_region",
    "final_active_transferred_roots_region",
    "post_event_outgoing_commits",
    "post_event_incoming_commits",
    "post_event_new_transferred_roots",
    "post_event_lost_transferred_roots",
)
PRIMARY_INTERVENTIONS = (
    "disable-knowledge-transfer",
    "freeze-group-refresh",
    "neutralize-resource-affinity",
)
REMAINING_KNOWLEDGE_INTERVENTIONS = (
    "disable-knowledge-policy",
    "ablate-working-memory",
    "bypass-sparse-selection",
)


def load_result(path: str | Path) -> dict[str, Any]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or payload.get("schema") not in SUPPORTED_RESULT_SCHEMAS:
        raise ValueError(f"unsupported natural-event result file: {path}")
    return payload


def _summary_quality(summary: dict[str, Any]) -> tuple[int, int]:
    return (
        int(summary.get("event_cohort_schema") == EVENT_COHORT_AUDIT_SCHEMA) * 100
        + int(bool(summary.get("reference_boundary_available"))) * 10,
        len(summary),
    )


def _assert_core_compatible(left: dict[str, Any], right: dict[str, Any], label: str) -> None:
    for key in CORE_WORLD_KEYS:
        a = left.get(key)
        b = right.get(key)
        if a is None or b is None:
            continue
        if abs(float(a) - float(b)) > 1e-9:
            raise ValueError(f"duplicate result mismatch for {label}: {key}: {a} != {b}")


def merge_reports(reports: Iterable[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    report_list = list(reports)
    if not report_list:
        raise ValueError("at least one result report is required")
    manifest_hashes = {str(item.get("manifest_sha256")) for item in report_list}
    if len(manifest_hashes) != 1:
        raise ValueError("result reports do not share one manifest SHA-256")

    anchors: dict[str, dict[str, Any]] = {}
    branch_sources: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for report in report_list:
        source = {
            "schema": str(report.get("schema")),
            "execution_plan_sha256": str(report.get("execution_plan_sha256")),
            "backend": report.get("backend"),
            "gpu_semantics_mode": report.get("gpu_semantics_mode"),
        }
        for item in report.get("results", []):
            anchor = dict(item.get("anchor", {}))
            anchor_id = str(anchor.get("anchor_id"))
            if not anchor_id:
                raise ValueError("result anchor is missing anchor_id")
            current = anchors.get(anchor_id)
            if current is None:
                current = {
                    "anchor": anchor,
                    "baseline_region_summary": dict(item.get("baseline_region_summary", {})),
                    "baseline_scientific_validity": item.get("baseline_scientific_validity", {}),
                    "baseline_trajectory_resumed": bool(item.get("baseline_trajectory_resumed", False)),
                    "branches_by_name": {},
                    "source_execution_plan_sha256": [],
                }
                anchors[anchor_id] = current
            elif current["anchor"] != anchor:
                # Ignore execution-only resolved fields when comparing immutable anchors.
                immutable = {k: v for k, v in anchor.items() if k not in {"checkpoint_path_resolved", "interventions_selected"}}
                existing = {k: v for k, v in current["anchor"].items() if k not in {"checkpoint_path_resolved", "interventions_selected"}}
                if immutable != existing:
                    raise ValueError(f"duplicate anchor metadata mismatch: {anchor_id}")
            baseline = dict(item.get("baseline_region_summary", {}))
            _assert_core_compatible(current["baseline_region_summary"], baseline, f"{anchor_id}/baseline")
            if _summary_quality(baseline) > _summary_quality(current["baseline_region_summary"]):
                current["baseline_region_summary"] = baseline
                current["baseline_scientific_validity"] = item.get("baseline_scientific_validity", {})
                current["baseline_trajectory_resumed"] = bool(item.get("baseline_trajectory_resumed", False))
            if source["execution_plan_sha256"] not in current["source_execution_plan_sha256"]:
                current["source_execution_plan_sha256"].append(source["execution_plan_sha256"])
            for branch in item.get("branches", []):
                name = str(branch.get("intervention"))
                key = (anchor_id, name)
                branch_sources[key].append(source)
                existing_branch = current["branches_by_name"].get(name)
                if existing_branch is None:
                    current["branches_by_name"][name] = dict(branch)
                    continue
                if bool(existing_branch.get("eligible")) != bool(branch.get("eligible")):
                    raise ValueError(f"duplicate intervention eligibility mismatch: {anchor_id}/{name}")
                if not branch.get("eligible"):
                    continue
                left_summary = dict(existing_branch.get("region_summary", {}))
                right_summary = dict(branch.get("region_summary", {}))
                _assert_core_compatible(left_summary, right_summary, f"{anchor_id}/{name}")
                if _summary_quality(right_summary) > _summary_quality(left_summary):
                    current["branches_by_name"][name] = dict(branch)

    merged: list[dict[str, Any]] = []
    for anchor_id, item in sorted(anchors.items()):
        merged.append(
            {
                "anchor": item["anchor"],
                "baseline_region_summary": item["baseline_region_summary"],
                "baseline_scientific_validity": item["baseline_scientific_validity"],
                "baseline_trajectory_resumed": item["baseline_trajectory_resumed"],
                "source_execution_plan_sha256": sorted(item["source_execution_plan_sha256"]),
                "branches": [item["branches_by_name"][name] for name in sorted(item["branches_by_name"])],
            }
        )
    provenance = [
        {
            "anchor_id": anchor_id,
            "intervention": intervention,
            "sources": values,
        }
        for (anchor_id, intervention), values in sorted(branch_sources.items())
    ]
    return merged, provenance


def _expected_pairs(manifest: dict[str, Any]) -> set[tuple[str, str]]:
    return {
        (str(anchor["anchor_id"]), str(entry["intervention"]))
        for anchor in manifest.get("anchors", [])
        for entry in anchor.get("interventions", [])
        if bool(entry.get("eligible"))
    }


def _observed_pairs(results: list[dict[str, Any]]) -> set[tuple[str, str]]:
    return {
        (str(item["anchor"]["anchor_id"]), str(branch["intervention"]))
        for item in results
        for branch in item.get("branches", [])
        if bool(branch.get("eligible"))
    }


def _diagnostic_coverage(results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    buckets: dict[tuple[str, str], dict[str, int]] = defaultdict(
        lambda: {"pairs": 0, "common_boundary": 0, "event_cohort": 0}
    )
    for item in results:
        event = str(item["anchor"]["event_kind"])
        for branch in item.get("branches", []):
            if not branch.get("eligible"):
                continue
            name = str(branch["intervention"])
            summary = branch.get("region_summary", {})
            bucket = buckets[(event, name)]
            bucket["pairs"] += 1
            bucket["common_boundary"] += int(bool(summary.get("reference_boundary_available")))
            bucket["event_cohort"] += int(summary.get("event_cohort_schema") == EVENT_COHORT_AUDIT_SCHEMA)
    return [
        {"event_kind": event, "intervention": name, **counts}
        for (event, name), counts in sorted(buckets.items())
    ]


def _cross_event_replication(aggregation: dict[str, Any]) -> list[dict[str, Any]]:
    rows: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for group in aggregation.get("groups", []):
        stat = group.get("seed_level", {})
        count = int(stat.get("count", 0))
        if count < 3:
            continue
        positive = int(stat.get("positive", 0))
        negative = int(stat.get("negative", 0))
        direction = "positive" if positive == count else "negative" if negative == count else None
        if direction is None:
            continue
        rows[(str(group["intervention"]), str(group["metric"]))].append(
            {
                "event_kind": str(group["event_kind"]),
                "direction": direction,
                "mean": stat.get("mean"),
                "seed_count": count,
            }
        )
    result = []
    for (intervention, metric), events in sorted(rows.items()):
        directions = {item["direction"] for item in events}
        if len(events) >= 2 and len(directions) == 1:
            result.append(
                {
                    "intervention": intervention,
                    "metric": metric,
                    "direction": next(iter(directions)),
                    "event_count": len(events),
                    "events": events,
                }
            )
    return result


def build_synthesis(
    reports: Iterable[dict[str, Any]],
    *,
    manifest: dict[str, Any] | None = None,
) -> dict[str, Any]:
    report_list = list(reports)
    merged, provenance = merge_reports(report_list)
    manifest_sha = str(report_list[0]["manifest_sha256"])
    if manifest is not None and str(manifest.get("plan_sha256")) != manifest_sha:
        raise ValueError("manifest SHA-256 does not match synthesized results")
    aggregation = aggregate_results(merged)
    diagnostic_coverage = _diagnostic_coverage(merged)
    synthetic_report = {
        "diagnostics": {
            "common_boundary_audit": all(
                row["common_boundary"] == row["pairs"] for row in diagnostic_coverage
            ),
            "common_boundary_schema": "checkpoint-frozen-stable-entity-boundary-v1",
            "event_cohort_audit": all(row["event_cohort"] == row["pairs"] for row in diagnostic_coverage),
            "event_cohort_schema": EVENT_COHORT_AUDIT_SCHEMA,
            "feedback_to_world": False,
        },
        "results": merged,
        "aggregation": aggregation,
    }
    outcome = audit_outcomes(synthetic_report)
    expected = _expected_pairs(manifest) if manifest is not None else set()
    observed = _observed_pairs(merged)
    missing = sorted(expected - observed)
    extra = sorted(observed - expected) if expected else []
    cross_event = _cross_event_replication(aggregation)

    findings: list[dict[str, Any]] = []
    transfer_roots = [
        row for row in cross_event
        if row["intervention"] == "disable-knowledge-transfer"
        and row["metric"] == "final_active_transferred_roots_region"
    ]
    if transfer_roots:
        findings.append(
            {
                "id": "TRANSFER-MAINTAINS-CULTURAL-STATE-ACROSS-EVENTS",
                "status": "replicated-mechanism-proximal",
                "evidence": transfer_roots[0],
                "interpretation": (
                    "Disabling future transfer reduces active transferred roots in the same "
                    "seed-level direction across multiple natural-event classes. This is a "
                    "cultural-state maintenance result, not a demographic benefit claim."
                ),
            }
        )
    freeze_current = [
        row for row in cross_event
        if row["intervention"] == "freeze-group-refresh"
        and row["metric"] == "post_event_cohesion_region"
    ]
    freeze_reference = [
        row for row in cross_event
        if row["intervention"] == "freeze-group-refresh"
        and row["metric"] == "post_event_reference_cohesion_region"
    ]
    findings.append(
        {
            "id": "GROUP-REFRESH-CURRENT-LABEL-COHESION",
            "status": "boundary-definition-dominated" if freeze_current and not freeze_reference else "unresolved",
            "evidence": {
                "current_label": freeze_current,
                "checkpoint_common": freeze_reference,
            },
            "interpretation": (
                "A repeated current-label cohesion direction without the same checkpoint-common "
                "direction indicates that most of the apparent effect is produced by changing "
                "the evaluation partition rather than stable common-boundary benefit flow."
            ),
        }
    )
    findings.append(
        {
            "id": "REGIONAL-DEMOGRAPHIC-MECHANISM",
            "status": "endpoint-cohort-rerun-required" if not outcome["event_cohort"]["observed"] else "decomposed",
            "evidence": {"event_cohort_observed": outcome["event_cohort"]["observed"]},
            "interpretation": (
                "Regional alive cannot identify survival, migration, or post-event birth components "
                "until stable-ID event-cohort endpoint decomposition is present."
            ),
        }
    )

    synthesis: dict[str, Any] = {
        "schema": SYNTHESIS_SCHEMA,
        "manifest_sha256": manifest_sha,
        "source_reports": [
            {
                "schema": str(report.get("schema")),
                "execution_plan_sha256": str(report.get("execution_plan_sha256")),
                "result_count": len(report.get("results", [])),
                "trajectory_count": int(report.get("trajectory_count", 0)),
            }
            for report in report_list
        ],
        "merged_anchor_count": len(merged),
        "merged_pair_count": len(observed),
        "coverage": {
            "expected_eligible_pair_count": len(expected) if manifest is not None else None,
            "observed_pair_count": len(observed),
            "complete": bool(manifest is not None and not missing and not extra),
            "missing_pairs": [
                {"anchor_id": anchor, "intervention": intervention}
                for anchor, intervention in missing
            ],
            "unexpected_pairs": [
                {"anchor_id": anchor, "intervention": intervention}
                for anchor, intervention in extra
            ],
        },
        "diagnostic_coverage": diagnostic_coverage,
        "aggregation": aggregation,
        "outcome_audit": outcome,
        "cross_event_replication": cross_event,
        "findings": findings,
        "result_provenance": provenance,
        "followup_plans": {},
        "interpretation_boundary": (
            "Reports are merged by immutable anchor and intervention identity. Anchor rows are "
            "never treated as independent replicates; seed-level values average anchors first. "
            "Cross-event agreement remains conditional on naturally occurring, non-randomized events."
        ),
    }
    if manifest is not None and not outcome["event_cohort"]["observed"]:
        manifest_anchors = list(manifest.get("anchors", []))

        def add_followup(
            name: str,
            *,
            event_kinds: tuple[str, ...] | None,
            interventions: tuple[str, ...],
        ) -> None:
            event_filter = set(event_kinds or ())
            matching = [
                anchor
                for anchor in manifest_anchors
                if not event_filter or str(anchor.get("event_kind")) in event_filter
            ]
            if not matching:
                return
            requested = set(interventions)
            if not any(
                bool(entry.get("eligible"))
                and str(entry.get("intervention")) in requested
                for anchor in matching
                for entry in anchor.get("interventions", [])
            ):
                return
            synthesis["followup_plans"][name] = build_execution_plan(
                manifest,
                event_kinds=event_kinds,
                interventions=interventions,
                common_boundary_audit=True,
                event_cohort_audit=True,
            )

        add_followup(
            "primary_event_cohort_rerun",
            event_kinds=None,
            interventions=PRIMARY_INTERVENTIONS,
        )
        add_followup(
            "crowding_knowledge_cohort_rerun",
            event_kinds=("crowding",),
            interventions=REMAINING_KNOWLEDGE_INTERVENTIONS,
        )
        add_followup(
            "remaining_event_knowledge_cohort_rerun",
            event_kinds=("mortality", "scarcity"),
            interventions=REMAINING_KNOWLEDGE_INTERVENTIONS,
        )
    return synthesis


def render_markdown(synthesis: dict[str, Any]) -> str:
    coverage = synthesis["coverage"]
    lines = [
        "# Natural-event result synthesis",
        "",
        f"Manifest SHA-256: `{synthesis['manifest_sha256']}`",
        "",
        f"- Source reports: {len(synthesis['source_reports'])}",
        f"- Merged anchors: {synthesis['merged_anchor_count']}",
        f"- Merged eligible pairs: {synthesis['merged_pair_count']}",
        f"- Manifest coverage complete: {coverage['complete']}",
        f"- Event cohort diagnostics observed: {synthesis['outcome_audit']['event_cohort']['observed']}",
        "",
        "## Findings",
        "",
    ]
    for finding in synthesis["findings"]:
        lines.extend(
            [
                f"### {finding['id']}",
                "",
                f"Status: **{finding['status']}**",
                "",
                str(finding["interpretation"]),
                "",
            ]
        )
    lines.extend(
        [
            "## Diagnostic coverage",
            "",
            "| Event | Intervention | Pairs | Common boundary | Event cohort |",
            "|---|---|---:|---:|---:|",
        ]
    )
    for row in synthesis["diagnostic_coverage"]:
        lines.append(
            f"| {row['event_kind']} | {row['intervention']} | {row['pairs']} | "
            f"{row['common_boundary']} | {row['event_cohort']} |"
        )
    lines.extend(
        [
            "",
            "## Cross-event repeated directions",
            "",
            "| Intervention | Metric | Direction | Events |",
            "|---|---|---|---:|",
        ]
    )
    for row in synthesis["cross_event_replication"]:
        lines.append(
            f"| {row['intervention']} | {row['metric']} | {row['direction']} | {row['event_count']} |"
        )
    lines.extend(["", "## Follow-up plans", ""])
    if not synthesis["followup_plans"]:
        lines.append("No follow-up plan was generated.")
    else:
        for name, plan in synthesis["followup_plans"].items():
            lines.append(
                f"- `{name}`: {plan['selected_anchor_count']} anchors, "
                f"{plan['trajectory_count']} shared trajectories."
            )
    lines.extend(["", "## Interpretation boundary", "", synthesis["interpretation_boundary"], ""])
    return "\n".join(lines)


def write_outputs(synthesis: dict[str, Any], output_dir: str | Path) -> None:
    root = Path(output_dir)
    root.mkdir(parents=True, exist_ok=True)
    serializable = dict(synthesis)
    plans = serializable.pop("followup_plans", {})
    serializable["followup_plan_summaries"] = {
        name: {
            "schema": plan["schema"],
            "execution_plan_sha256": plan["execution_plan_sha256"],
            "selected_anchor_count": plan["selected_anchor_count"],
            "trajectory_count": plan["trajectory_count"],
            "deduplicated_branch_count": plan["deduplicated_branch_count"],
        }
        for name, plan in plans.items()
    }
    (root / "natural_event_result_synthesis.json").write_text(
        json.dumps(serializable, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (root / "natural_event_result_synthesis.md").write_text(
        render_markdown(synthesis), encoding="utf-8"
    )
    for name, plan in plans.items():
        (root / f"{name}_execution_plan.json").write_text(
            json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        (root / f"{name}_execution_plan.md").write_text(
            render_execution_plan_markdown(plan), encoding="utf-8"
        )


def _discover_results(values: Iterable[str]) -> list[Path]:
    paths: list[Path] = []
    for raw in values:
        path = Path(raw)
        if path.is_dir():
            paths.extend(sorted(path.rglob("natural_event_matrix_results.json")))
        elif path.is_file():
            paths.append(path)
        else:
            raise FileNotFoundError(path)
    unique = []
    seen = set()
    for path in paths:
        resolved = path.resolve()
        if resolved not in seen:
            seen.add(resolved)
            unique.append(path)
    if not unique:
        raise ValueError("no natural_event_matrix_results.json files were found")
    return unique


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Synthesize multiple natural-event result sets")
    parser.add_argument("--results", action="append", required=True, help="Result JSON or directory; repeatable")
    parser.add_argument("--manifest")
    parser.add_argument("--output", required=True)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    paths = _discover_results(args.results)
    reports = [load_result(path) for path in paths]
    manifest = load_manifest(args.manifest) if args.manifest else None
    synthesis = build_synthesis(reports, manifest=manifest)
    write_outputs(synthesis, args.output)


if __name__ == "__main__":
    main()
