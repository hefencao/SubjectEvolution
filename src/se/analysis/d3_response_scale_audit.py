"""Audit D3-G acute response panels across map scales without pseudoreplication.

The independent replication unit is the seed. Checkpoints are retained as
nested repeated panels. A reversed active branch is causally interpretable only
when a reversed-and-neutral branch is present under the same checkpoint and
observation orientation.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Iterable

import numpy as np

SCHEMA = "d3-response-scale-audit-v1"
SUPPORTED_RESULTS = {
    "d3-processing-response-panel-results-v1",
    "d3-processing-response-panel-results-v2",
}
METRICS = {
    "resource_move_mean_support_gain": "mean_support_gain",
    "resource_move_mean_alignment_cosine": "mean_alignment_cosine",
    "resource_move_positive_support_gain_fraction": "positive_gain_fraction",
}


def parse_result_spec(value: str) -> tuple[str, Path]:
    if "=" not in value:
        path = Path(value)
        return path.stem, path
    label, raw_path = value.split("=", 1)
    if not label.strip():
        raise ValueError("result label cannot be empty")
    return label.strip(), Path(raw_path)


def _branch_map(panel: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {row["branch"]: row for row in panel.get("branches", [])}


def _eligible(panel: dict[str, Any]) -> bool:
    return bool(
        panel.get(
            "acute_quartet_analysis_eligible",
            panel.get("acute_triplet_analysis_eligible", False),
        )
    )


def _effect(
    branches: dict[str, dict[str, Any]], active: str, neutral: str, metric: str
) -> float:
    return float(
        branches[active]["response_summary"][metric]
        - branches[neutral]["response_summary"][metric]
    )


def _seed_summary(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for seed in sorted({int(row["seed"]) for row in rows}):
        selected = [row for row in rows if int(row["seed"]) == seed]
        payload: dict[str, Any] = {
            "seed": seed,
            "eligible_checkpoint_count": len(selected),
        }
        for output_key in METRICS.values():
            for orientation in ("original", "reversed"):
                values = [
                    row["matched_effects"][output_key][orientation]
                    for row in selected
                    if row["matched_effects"][output_key].get(orientation) is not None
                ]
                payload[f"{orientation}_{output_key}_mean"] = (
                    float(np.mean(values)) if values else None
                )
        result.append(payload)
    return result


def audit_result(label: str, path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    schema = payload.get("schema")
    if schema not in SUPPORTED_RESULTS:
        raise ValueError(f"unsupported D3-G result schema {schema!r}: {path}")
    panel_rows: list[dict[str, Any]] = []
    matched_complete_count = 0
    for panel in payload.get("panels", []):
        if panel.get("status") != "completed":
            continue
        branches = _branch_map(panel)
        names = set(branches)
        matched_complete = {
            "original-support",
            "neutral-support",
            "reversed-support",
            "reversed-neutral-support",
        }.issubset(names)
        matched_complete_count += int(matched_complete)
        effects: dict[str, dict[str, float | None]] = {}
        for metric, output_key in METRICS.items():
            original = (
                _effect(branches, "original-support", "neutral-support", metric)
                if {"original-support", "neutral-support"}.issubset(names)
                else None
            )
            reversed_effect = (
                _effect(
                    branches,
                    "reversed-support",
                    "reversed-neutral-support",
                    metric,
                )
                if matched_complete
                else None
            )
            effects[output_key] = {
                "original": original,
                "reversed": reversed_effect,
                "reversed_minus_original": (
                    reversed_effect - original
                    if reversed_effect is not None and original is not None
                    else None
                ),
            }
        panel_rows.append(
            {
                "seed": int(panel["seed"]),
                "checkpoint_tick": int(panel["checkpoint_tick"]),
                "acute_analysis_eligible": _eligible(panel),
                "evolutionary_analysis_eligible": bool(
                    panel.get("evolutionary_checkpoint_analysis_eligible", False)
                ),
                "matched_orientation_controls_complete": matched_complete,
                "matched_effects": effects,
                "branch_metrics": {
                    name: {
                        output_key: float(row["response_summary"][metric])
                        for metric, output_key in METRICS.items()
                    }
                    for name, row in branches.items()
                },
            }
        )
    eligible = [row for row in panel_rows if row["acute_analysis_eligible"]]
    matched_eligible = [
        row for row in eligible if row["matched_orientation_controls_complete"]
    ]
    original_gain = [
        row["matched_effects"]["mean_support_gain"]["original"]
        for row in eligible
        if row["matched_effects"]["mean_support_gain"]["original"] is not None
    ]
    original_values = [
        row["branch_metrics"]["original-support"]["mean_support_gain"]
        for row in eligible
        if "original-support" in row["branch_metrics"]
    ]
    neutral_values = [
        row["branch_metrics"]["neutral-support"]["mean_support_gain"]
        for row in eligible
        if "neutral-support" in row["branch_metrics"]
    ]
    tracking_correlation = None
    if len(original_values) >= 2 and len(original_values) == len(neutral_values):
        candidate = float(np.corrcoef(original_values, neutral_values)[0, 1])
        tracking_correlation = candidate if np.isfinite(candidate) else None
    return {
        "label": label,
        "path": str(path),
        "result_schema": schema,
        "panel_count": len(payload.get("panels", [])),
        "completed_panel_count": len(panel_rows),
        "acute_analysis_eligible_panel_count": len(eligible),
        "evolutionary_analysis_eligible_checkpoint_count": sum(
            row["evolutionary_analysis_eligible"] for row in panel_rows
        ),
        "matched_orientation_control_panel_count": matched_complete_count,
        "matched_orientation_control_eligible_panel_count": len(matched_eligible),
        "original_active_neutral_gain_mean_across_eligible_panels": (
            float(np.mean(original_gain)) if original_gain else None
        ),
        "original_active_neutral_gain_max_abs_across_eligible_panels": (
            float(np.max(np.abs(original_gain))) if original_gain else None
        ),
        "original_neutral_gain_tracking_correlation_across_eligible_panels": (
            tracking_correlation
        ),
        "panels": panel_rows,
        "seed_summaries": _seed_summary(matched_eligible),
    }


def build_audit(specs: Iterable[tuple[str, Path]]) -> dict[str, Any]:
    scales = [audit_result(label, path) for label, path in specs]
    if not scales:
        raise ValueError("at least one result file is required")
    completed = sum(row["completed_panel_count"] for row in scales)
    eligible = sum(row["acute_analysis_eligible_panel_count"] for row in scales)
    matched = sum(
        row["matched_orientation_control_eligible_panel_count"] for row in scales
    )
    all_matched = matched == eligible and eligible > 0
    if eligible == 0:
        recommendation = "increase-unprotected-scale-or-revise-preregistered-checkpoints"
    elif not all_matched:
        recommendation = "rerun-eligible-panels-with-matched-orientation-neutral-controls"
    else:
        recommendation = "analyze-seed-level-matched-orientation-effects"
    return {
        "schema": SCHEMA,
        "scales": scales,
        "completed_panel_count": completed,
        "acute_analysis_eligible_panel_count": eligible,
        "matched_orientation_control_eligible_panel_count": matched,
        "all_eligible_panels_have_matched_orientation_controls": all_matched,
        "independent_replication_unit": "seed",
        "checkpoints_within_seed": "nested-repeated-panels",
        "movement_events_independent_replicates": False,
        "recommendation": recommendation,
        "interpretation_boundary": (
            "Only active-minus-neutral contrasts under the same support observation "
            "orientation isolate support execution. Three-arm v1 panels do not identify "
            "the reversed-support effect because their neutral branch is observed against "
            "the original orientation. No result here establishes evolutionary adaptation, "
            "migration, specialization, coexistence, or ecological roles."
        ),
    }


def render_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# D3-G cross-scale matched-control audit",
        "",
        f"Schema: `{payload['schema']}`",
        "",
        "| Scale | Result schema | Completed panels | Acute eligible | Matched eligible | Evolutionary eligible | Original active-neutral mean gain |",
        "|---|---|---:|---:|---:|---:|---:|",
    ]
    for row in payload["scales"]:
        lines.append(
            f"| {row['label']} | {row['result_schema']} | "
            f"{row['completed_panel_count']} | "
            f"{row['acute_analysis_eligible_panel_count']} | "
            f"{row['matched_orientation_control_eligible_panel_count']} | "
            f"{row['evolutionary_analysis_eligible_checkpoint_count']} | "
            f"{row['original_active_neutral_gain_mean_across_eligible_panels']} | "
            f"{row['original_neutral_gain_tracking_correlation_across_eligible_panels']} |"
        )
    lines += [
        "",
        f"All eligible panels have matched orientation controls: `{payload['all_eligible_panels_have_matched_orientation_controls']}`",
        "",
        f"Recommendation: `{payload['recommendation']}`",
        "",
        payload["interpretation_boundary"],
        "",
    ]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--result",
        action="append",
        required=True,
        help="LABEL=path/to/d3_processing_response_panel_results.json",
    )
    parser.add_argument("--output", required=True)
    args = parser.parse_args(argv)
    audit = build_audit(parse_result_spec(value) for value in args.result)
    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=True)
    (output / "d3_response_scale_audit.json").write_text(
        json.dumps(audit, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    (output / "d3_response_scale_audit.md").write_text(
        render_markdown(audit), encoding="utf-8"
    )
    print(json.dumps({"recommendation": audit["recommendation"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
