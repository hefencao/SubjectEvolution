"""Offline multi-seed analysis for candidate-subject succession and environment atlases."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any

import numpy as np


SCHEMA = "multi-seed-subject-environment-analysis-v1"
MIN_SAMPLES = 5


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    if not path.is_file():
        return records
    with path.open("r", encoding="utf-8") as stream:
        for line_number, line in enumerate(stream, start=1):
            if not line.strip():
                continue
            value = json.loads(line)
            if not isinstance(value, dict) or "tick" not in value:
                raise ValueError(f"{path}:{line_number} is not a diagnostic record")
            records.append(value)
    records.sort(key=lambda value: int(value["tick"]))
    return records


def _pearson(left: list[float], right: list[float]) -> float | None:
    a = np.asarray(left, dtype=np.float64)
    b = np.asarray(right, dtype=np.float64)
    valid = np.isfinite(a) & np.isfinite(b)
    a = a[valid]
    b = b[valid]
    if a.size < MIN_SAMPLES or float(np.std(a)) == 0.0 or float(np.std(b)) == 0.0:
        return None
    return float(np.corrcoef(a, b)[0, 1])


def _slope(ticks: list[float], values: list[float]) -> float | None:
    x = np.asarray(ticks, dtype=np.float64)
    y = np.asarray(values, dtype=np.float64)
    valid = np.isfinite(x) & np.isfinite(y)
    x = x[valid]
    y = y[valid]
    if x.size < MIN_SAMPLES or float(np.std(x)) == 0.0:
        return None
    centered = x - x.mean()
    return float(np.dot(centered, y - y.mean()) / np.dot(centered, centered) * 1000.0)


def _latest_structure(
    records: list[dict[str, Any]], tick: int, start_index: int
) -> tuple[dict[str, Any] | None, int]:
    index = start_index
    while index + 1 < len(records) and int(records[index + 1]["tick"]) <= tick:
        index += 1
    if not records or int(records[0]["tick"]) > tick:
        return None, start_index
    return records[index], index


def summarize_run(run_dir: str | Path) -> dict[str, Any]:
    root = Path(run_dir)
    structure = _load_jsonl(root / "subject_structure_transitions.jsonl")
    atlas = _load_jsonl(root / "environment_atlas.jsonl")
    panels: dict[str, list[dict[str, float | int]]] = {}
    structure_index = 0
    for atlas_record in atlas:
        tick = int(atlas_record["tick"])
        matched, structure_index = _latest_structure(structure, tick, structure_index)
        for scale in atlas_record.get("scales", []):
            key = str(scale["scale"])
            row: dict[str, float | int] = {
                "tick": tick,
                "environment_signature_effective_dimensions": float(
                    scale.get("region_signature_effective_dimensions", math.nan)
                ),
                "environment_signature_mean_distance": float(
                    scale.get("region_signature_mean_pairwise_distance", math.nan)
                ),
                "environment_temporal_turnover": float(
                    scale.get("region_signature_temporal_turnover", math.nan)
                ),
                "resource_spatial_cv_mean": float(
                    scale.get("resource_spatial_cv_mean", math.nan)
                ),
                "lineage_environment_association": float(
                    scale.get("lineage_environment_association_fraction", math.nan)
                ),
                "lineage_environment_covered_fraction": float(
                    scale.get("lineage_subject_covered_fraction", math.nan)
                ),
                "lineage_region_span": float(
                    scale.get("lineage_mean_region_span_fraction", math.nan)
                ),
                "social_environment_association": float(
                    scale.get("social_environment_association_fraction", math.nan)
                ),
                "social_environment_covered_fraction": float(
                    scale.get("social_subject_covered_fraction", math.nan)
                ),
                "social_region_span": float(
                    scale.get("social_mean_region_span_fraction", math.nan)
                ),
            }
            if matched is not None:
                row.update(
                    {
                        "structure_tick": int(matched["tick"]),
                        "active_groups": int(matched.get("current_group_count", 0)),
                        "effective_groups": float(
                            matched.get("current_group_effective_count", 0.0)
                        ),
                        "weighted_predecessor_jaccard": float(
                            matched.get("member_weighted_predecessor_jaccard", 0.0)
                        ),
                        "weighted_predecessor_inheritance": float(
                            matched.get(
                                "member_weighted_predecessor_inheritance", 0.0
                            )
                        ),
                        "split_merge_count": int(
                            matched.get("split_source_count", 0)
                            + matched.get("merge_target_count", 0)
                        ),
                    }
                )
            else:
                row.update(
                    {
                        "structure_tick": -1,
                        "active_groups": 0,
                        "effective_groups": 0.0,
                        "weighted_predecessor_jaccard": math.nan,
                        "weighted_predecessor_inheritance": math.nan,
                        "split_merge_count": 0,
                    }
                )
            panels.setdefault(key, []).append(row)

    scale_summaries: dict[str, Any] = {}
    for scale, rows in panels.items():
        ticks = [float(row["tick"]) for row in rows]
        turnover = [float(row["environment_temporal_turnover"]) for row in rows]
        jaccard = [float(row["weighted_predecessor_jaccard"]) for row in rows]
        association = [float(row["social_environment_association"]) for row in rows]
        span = [float(row["social_region_span"]) for row in rows]
        split_merge = [float(row["split_merge_count"]) for row in rows]
        scale_summaries[scale] = {
            "record_count": len(rows),
            "final": rows[-1] if rows else None,
            "slopes_per_1000_ticks": {
                "environment_temporal_turnover": _slope(ticks, turnover),
                "weighted_predecessor_jaccard": _slope(ticks, jaccard),
                "social_environment_association": _slope(ticks, association),
                "social_region_span": _slope(ticks, span),
            },
            "correlations": {
                "environment_turnover_vs_subject_jaccard": _pearson(
                    turnover, jaccard
                ),
                "environment_turnover_vs_split_merge": _pearson(
                    turnover, split_merge
                ),
                "social_environment_association_vs_subject_jaccard": _pearson(
                    association, jaccard
                ),
                "social_region_span_vs_subject_jaccard": _pearson(span, jaccard),
            },
            "causal_caution": (
                "Atlas evaluations are aligned to the latest observed group refresh. "
                "Correlations may reflect common population and temporal changes."
            ),
        }
    return {
        "run_name": root.name,
        "run_dir": str(root),
        "subject_refresh_count": len(structure),
        "environment_evaluation_count": len(atlas),
        "scale_summaries": scale_summaries,
        "available": bool(structure and atlas),
    }


def _cross_seed_consistency(runs: list[dict[str, Any]]) -> dict[str, Any]:
    keys: set[tuple[str, str, str]] = set()
    for run in runs:
        for scale, summary in run["scale_summaries"].items():
            for section in ("slopes_per_1000_ticks", "correlations"):
                for metric in summary[section]:
                    keys.add((scale, section, metric))
    result: dict[str, Any] = {}
    for scale, section, metric in sorted(keys):
        values: list[float] = []
        for run in runs:
            value = (
                run.get("scale_summaries", {})
                .get(scale, {})
                .get(section, {})
                .get(metric)
            )
            if isinstance(value, (int, float)) and math.isfinite(float(value)):
                values.append(float(value))
        positive = sum(value > 0.0 for value in values)
        negative = sum(value < 0.0 for value in values)
        zero = len(values) - positive - negative
        result[f"{scale}.{section}.{metric}"] = {
            "available_runs": len(values),
            "mean": float(np.mean(values)) if values else None,
            "minimum": float(np.min(values)) if values else None,
            "maximum": float(np.max(values)) if values else None,
            "positive_runs": positive,
            "negative_runs": negative,
            "zero_runs": zero,
            "same_nonzero_sign": bool(
                len(values) >= 3 and (positive == len(values) or negative == len(values))
            ),
        }
    return result


def analyze(run_dirs: list[str | Path]) -> dict[str, Any]:
    runs = [summarize_run(path) for path in run_dirs]
    consistency = _cross_seed_consistency(runs)
    return {
        "schema": SCHEMA,
        "run_count": len(runs),
        "available_run_count": sum(bool(run["available"]) for run in runs),
        "runs": runs,
        "cross_seed_directional_consistency": consistency,
        "repeated_directions": [
            key for key, value in consistency.items() if value["same_nonzero_sign"]
        ],
        "interpretation_boundary": (
            "Candidate-group succession and subject–environment association are "
            "observational measurements. Repeated directions motivate matched "
            "interventions but do not establish subject identity or environmental causation."
        ),
    }


def _format(value: Any) -> str:
    return "—" if value is None else f"{float(value):.4f}"


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Multi-seed subject structure and environment analysis",
        "",
        f"Schema: `{report['schema']}`",
        f"Runs: **{report['run_count']}**; available: **{report['available_run_count']}**",
        "",
        "> This report is observational. Candidate-group succession is not an ontological identity claim, and exposure association is not environmental causation.",
        "",
    ]
    for run in report["runs"]:
        lines.extend(
            [
                f"## {run['run_name']}",
                "",
                f"- subject refreshes: {run['subject_refresh_count']}",
                f"- environment evaluations: {run['environment_evaluation_count']}",
            ]
        )
        if not run["available"]:
            lines.extend(["- paired diagnostics unavailable", ""])
            continue
        for scale, summary in run["scale_summaries"].items():
            final = summary.get("final") or {}
            lines.extend(
                [
                    f"### Scale {scale}",
                    f"- final active/effective groups: {final.get('active_groups', 0)} / {_format(final.get('effective_groups'))}",
                    f"- final Jaccard/inheritance: {_format(final.get('weighted_predecessor_jaccard'))} / {_format(final.get('weighted_predecessor_inheritance'))}",
                    f"- final signature dims/distance/turnover: {_format(final.get('environment_signature_effective_dimensions'))} / {_format(final.get('environment_signature_mean_distance'))} / {_format(final.get('environment_temporal_turnover'))}",
                    f"- final lineage association/coverage/span: {_format(final.get('lineage_environment_association'))} / {_format(final.get('lineage_environment_covered_fraction'))} / {_format(final.get('lineage_region_span'))}",
                    f"- final social association/coverage/span: {_format(final.get('social_environment_association'))} / {_format(final.get('social_environment_covered_fraction'))} / {_format(final.get('social_region_span'))}",
                    "- correlations:",
                ]
            )
            for key, value in summary["correlations"].items():
                lines.append(f"  - `{key}`: {_format(value)}")
            lines.append("")
    lines.extend(["## Repeated cross-seed directions", ""])
    if report["repeated_directions"]:
        for key in report["repeated_directions"]:
            value = report["cross_seed_directional_consistency"][key]
            lines.append(
                f"- `{key}`: mean={_format(value['mean'])}, "
                f"range=[{_format(value['minimum'])}, {_format(value['maximum'])}]"
            )
    else:
        lines.append("- No direction had the same non-zero sign in at least three runs.")
    lines.extend(["", "## Interpretation boundary", "", report["interpretation_boundary"], ""])
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description="Analyze subject succession and multiscale environment atlas outputs"
    )
    parser.add_argument("run_dirs", nargs="+")
    parser.add_argument("--output", required=True)
    args = parser.parse_args(argv)
    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=True)
    report = analyze(args.run_dirs)
    (output / "structure_environment_analysis.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    (output / "structure_environment_analysis.md").write_text(
        render_markdown(report), encoding="utf-8"
    )


if __name__ == "__main__":
    main()
