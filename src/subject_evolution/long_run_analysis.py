"""Offline, non-causal analysis for periodic evolution_progress JSONL files."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any, Iterable

import numpy as np


def load_progress(path: str | Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    with Path(path).open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            value = json.loads(line)
            if not isinstance(value, dict) or "tick" not in value:
                raise ValueError(f"{path}:{line_number} is not an evolution record")
            records.append(value)
    records.sort(key=lambda item: int(item["tick"]))
    return records


def _pearson(x: Iterable[float], y: Iterable[float]) -> float | None:
    a = np.asarray(list(x), dtype=np.float64)
    b = np.asarray(list(y), dtype=np.float64)
    valid = np.isfinite(a) & np.isfinite(b)
    a = a[valid]
    b = b[valid]
    if a.size < 5 or float(np.std(a)) == 0.0 or float(np.std(b)) == 0.0:
        return None
    return float(np.corrcoef(a, b)[0, 1])


def summarize_run(path: str | Path, records: list[dict[str, Any]]) -> dict[str, Any]:
    if not records:
        raise ValueError(f"{path} contains no records")
    final = records[-1]
    alive = np.asarray([record.get("alive", 0) for record in records], dtype=np.int64)
    mortality = np.asarray(
        [
            record.get(
                "mortality_pressure_window",
                record.get("deaths_window", 0)
                / max(record.get("alive", 0) + record.get("deaths_window", 0), 1),
            )
            for record in records
        ],
        dtype=np.float64,
    )
    cohesion = np.asarray(
        [record.get("benefit_boundary_cohesion", math.nan) for record in records],
        dtype=np.float64,
    )
    effective_lineages = np.asarray(
        [record.get("effective_lineages", math.nan) for record in records],
        dtype=np.float64,
    )
    largest_lineage = np.asarray(
        [record.get("largest_lineage_fraction", math.nan) for record in records],
        dtype=np.float64,
    )
    strategy_dims = np.asarray(
        [record.get("strategy_effective_dimensions", math.nan) for record in records],
        dtype=np.float64,
    )
    action_entropy = np.asarray(
        [record.get("window_action_entropy", math.nan) for record in records],
        dtype=np.float64,
    )
    lineage_group_nmi = np.asarray(
        [record.get("lineage_group_nmi", math.nan) for record in records],
        dtype=np.float64,
    )
    lineage_group_pair_enrichment = np.asarray(
        [record.get("lineage_group_pair_enrichment", math.nan) for record in records],
        dtype=np.float64,
    )
    knowledge_effective_roots = np.asarray(
        [record.get("knowledge_effective_root_contents", math.nan) for record in records],
        dtype=np.float64,
    )
    path_obj = Path(path)
    return {
        "path": str(path),
        "run_name": (
            path_obj.parent.name if path_obj.name == "evolution_progress.jsonl" else path_obj.name
        ),
        "record_count": len(records),
        "first_tick": int(records[0]["tick"]),
        "final_tick": int(final["tick"]),
        "alive_final": int(final.get("alive", 0)),
        "alive_peak": int(alive.max()),
        "alive_peak_tick": int(records[int(np.argmax(alive))]["tick"]),
        "alive_trough": int(alive.min()),
        "alive_trough_tick": int(records[int(np.argmin(alive))]["tick"]),
        "effective_lineages_final": float(final.get("effective_lineages", 0.0)),
        "largest_lineage_fraction_final": float(
            final.get("largest_lineage_fraction", 0.0)
        ),
        "strategy_effective_dimensions_final": float(
            final.get("strategy_effective_dimensions", 0.0)
        ),
        "window_action_entropy_final": float(final.get("window_action_entropy", 0.0)),
        "benefit_boundary_cohesion_final": float(
            final.get("benefit_boundary_cohesion", 0.0)
        ),
        "lineage_group_nmi_final": (
            float(final["lineage_group_nmi"])
            if "lineage_group_nmi" in final
            else None
        ),
        "lineage_group_pair_enrichment_final": (
            float(final["lineage_group_pair_enrichment"])
            if "lineage_group_pair_enrichment" in final
            else None
        ),
        "same_lineage_given_same_group_final": (
            float(final["same_lineage_given_same_group"])
            if "same_lineage_given_same_group" in final
            else None
        ),
        "knowledge_effective_root_contents_final": (
            float(final["knowledge_effective_root_contents"])
            if "knowledge_effective_root_contents" in final
            else None
        ),
        "knowledge_largest_root_holder_fraction_final": (
            float(final["knowledge_largest_root_holder_fraction"])
            if "knowledge_largest_root_holder_fraction" in final
            else None
        ),
        "knowledge_root_genetic_lineage_pair_enrichment_final": (
            float(final["knowledge_root_genetic_lineage_pair_enrichment"])
            if "knowledge_root_genetic_lineage_pair_enrichment" in final
            else None
        ),
        "correlations_observational": {
            "mortality_vs_same_window_cohesion": _pearson(mortality, cohesion),
            "mortality_vs_next_window_cohesion": _pearson(
                mortality[:-1], cohesion[1:]
            ),
            "effective_lineages_vs_cohesion": _pearson(
                effective_lineages, cohesion
            ),
            "largest_lineage_fraction_vs_cohesion": _pearson(
                largest_lineage, cohesion
            ),
            "strategy_dimensions_vs_action_entropy": _pearson(
                strategy_dims, action_entropy
            ),
            "lineage_group_nmi_vs_cohesion": _pearson(
                lineage_group_nmi, cohesion
            ),
            "lineage_group_pair_enrichment_vs_cohesion": _pearson(
                lineage_group_pair_enrichment, cohesion
            ),
            "knowledge_effective_roots_vs_effective_lineages": _pearson(
                knowledge_effective_roots, effective_lineages
            ),
        },
        "causal_caution": (
            "All correlations are descriptive. Cohesion, mortality, lineage "
            "concentration and group alignment may share environmental causes."
        ),
    }


def analyze(paths: list[str | Path]) -> dict[str, Any]:
    runs = [summarize_run(path, load_progress(path)) for path in paths]
    endpoints = {
        key: [run[key] for run in runs]
        for key in (
            "alive_final",
            "effective_lineages_final",
            "largest_lineage_fraction_final",
            "strategy_effective_dimensions_final",
            "window_action_entropy_final",
            "benefit_boundary_cohesion_final",
        )
    }
    aggregate: dict[str, Any] = {}
    for key, values in endpoints.items():
        array = np.asarray(values, dtype=np.float64)
        aggregate[key] = {
            "mean": float(array.mean()),
            "min": float(array.min()),
            "max": float(array.max()),
            "std": float(array.std()),
        }
    return {
        "schema": "multi-seed-long-run-analysis-v1",
        "run_count": len(runs),
        "runs": runs,
        "endpoint_aggregate": aggregate,
        "interpretation_boundary": (
            "A repeated directional trend across seeds supports robustness, not "
            "necessity. Divergent lineage outcomes are expected evidence of path "
            "dependence until controlled checkpoint interventions are run."
        ),
    }


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Multi-seed long-run analysis",
        "",
        f"Schema: `{report['schema']}`",
        f"Runs: **{report['run_count']}**",
        "",
        "> This report is observational. Correlation does not identify an in-world causal mechanism.",
        "",
        "| Run | Final tick | Alive | Effective lineages | Largest lineage | Strategy dims | Action entropy | Cohesion | Lineage-group NMI | Pair enrichment |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for run in report["runs"]:
        nmi = run["lineage_group_nmi_final"]
        enrichment = run["lineage_group_pair_enrichment_final"]
        lines.append(
            "| {name} | {tick} | {alive} | {effective:.4f} | {largest:.4f} | "
            "{dims:.4f} | {entropy:.4f} | {cohesion:.4f} | {nmi} | {enrichment} |".format(
                name=run["run_name"],
                tick=run["final_tick"],
                alive=run["alive_final"],
                effective=run["effective_lineages_final"],
                largest=run["largest_lineage_fraction_final"],
                dims=run["strategy_effective_dimensions_final"],
                entropy=run["window_action_entropy_final"],
                cohesion=run["benefit_boundary_cohesion_final"],
                nmi="—" if nmi is None else f"{nmi:.4f}",
                enrichment=(
                    "—" if enrichment is None else f"{enrichment:.4f}"
                ),
            )
        )
    lines.extend(["", "## Within-run observational correlations", ""])
    for run in report["runs"]:
        lines.append(f"### {run['run_name']}")
        for key, value in run["correlations_observational"].items():
            lines.append(f"- `{key}`: {'insufficient data' if value is None else f'{value:.4f}' }")
        lines.append("")
    lines.extend(["## Interpretation boundary", "", report["interpretation_boundary"], ""])
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Analyze one or more evolution_progress JSONL files"
    )
    parser.add_argument("inputs", nargs="+", help="Evolution progress JSONL files")
    parser.add_argument("--output", required=True, help="Output directory")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=True)
    report = analyze(args.inputs)
    (output / "long_run_analysis.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (output / "long_run_analysis.md").write_text(
        render_markdown(report), encoding="utf-8"
    )


if __name__ == "__main__":
    main()
