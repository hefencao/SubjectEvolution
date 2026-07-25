"""Offline, non-causal analysis for periodic evolution_progress JSONL files."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any, Iterable

import numpy as np


MIN_CORRELATION_SAMPLES = 5
MIN_PARTIAL_SAMPLES = 8


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
    if (
        a.size < MIN_CORRELATION_SAMPLES
        or float(np.std(a)) == 0.0
        or float(np.std(b)) == 0.0
    ):
        return None
    return float(np.corrcoef(a, b)[0, 1])


def _partial_pearson(
    x: Iterable[float],
    y: Iterable[float],
    controls: Iterable[Iterable[float]],
) -> float | None:
    a = np.asarray(list(x), dtype=np.float64)
    b = np.asarray(list(y), dtype=np.float64)
    control_columns = [np.asarray(list(column), dtype=np.float64) for column in controls]
    if any(column.shape != a.shape for column in control_columns) or b.shape != a.shape:
        raise ValueError("partial-correlation arrays must have matching shapes")
    valid = np.isfinite(a) & np.isfinite(b)
    for column in control_columns:
        valid &= np.isfinite(column)
    a = a[valid]
    b = b[valid]
    matrix = np.column_stack([column[valid] for column in control_columns])
    if a.size < MIN_PARTIAL_SAMPLES:
        return None
    # Intercept plus standardized controls keeps tick magnitude numerically tame.
    standardized: list[np.ndarray] = []
    for column in matrix.T:
        std = float(np.std(column))
        standardized.append(
            np.zeros_like(column) if std == 0.0 else (column - column.mean()) / std
        )
    design = np.column_stack([np.ones(a.size), *standardized])
    residual_a = a - design @ np.linalg.lstsq(design, a, rcond=None)[0]
    residual_b = b - design @ np.linalg.lstsq(design, b, rcond=None)[0]
    return _pearson(residual_a, residual_b)


def _slope_per_1000_ticks(ticks: np.ndarray, values: np.ndarray) -> float | None:
    valid = np.isfinite(ticks) & np.isfinite(values)
    x = ticks[valid]
    y = values[valid]
    if x.size < MIN_CORRELATION_SAMPLES or float(np.std(x)) == 0.0:
        return None
    centered = x - x.mean()
    slope = float(np.dot(centered, y - y.mean()) / np.dot(centered, centered))
    return slope * 1000.0


def _cross_lag_correlations(
    x: np.ndarray,
    y: np.ndarray,
    *,
    max_lag: int = 3,
) -> dict[str, float | None]:
    """Return correlations where positive lag means x leads y by that many windows."""
    result: dict[str, float | None] = {}
    for lag in range(-max_lag, max_lag + 1):
        if lag > 0:
            left, right = x[:-lag], y[lag:]
        elif lag < 0:
            left, right = x[-lag:], y[:lag]
        else:
            left, right = x, y
        result[str(lag)] = _pearson(left, right)
    return result


def _best_lag(values: dict[str, float | None]) -> dict[str, float | int] | None:
    available = [(int(key), value) for key, value in values.items() if value is not None]
    if not available:
        return None
    lag, value = max(available, key=lambda item: abs(float(item[1])))
    return {"lag_windows": lag, "correlation": float(value)}


def _array(records: list[dict[str, Any]], key: str) -> np.ndarray:
    return np.asarray([record.get(key, math.nan) for record in records], dtype=np.float64)


def _resolved_config_context(path: str | Path) -> dict[str, Any]:
    progress = Path(path)
    resolved = progress.parent / "resolved_config.json"
    if not resolved.is_file():
        return {}
    try:
        config = json.loads(resolved.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    knowledge = config.get("knowledge", {}) if isinstance(config, dict) else {}
    environment = config.get("environment", {}) if isinstance(config, dict) else {}
    entities = config.get("entities", {}) if isinstance(config, dict) else {}
    return {
        "knowledge_transfer_probability": knowledge.get("transfer_probability"),
        "knowledge_transfer_period": knowledge.get("transfer_period"),
        "environment_schema": environment.get("schema"),
        "resource_affinity_schema": entities.get("resource_affinity_schema"),
    }


def summarize_run(path: str | Path, records: list[dict[str, Any]]) -> dict[str, Any]:
    if not records:
        raise ValueError(f"{path} contains no records")
    final = records[-1]
    ticks = _array(records, "tick")
    alive = _array(records, "alive")
    deaths = _array(records, "deaths_window")
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
    cohesion = _array(records, "benefit_boundary_cohesion")
    effective_lineages = _array(records, "effective_lineages")
    largest_lineage = _array(records, "largest_lineage_fraction")
    strategy_dims = _array(records, "strategy_effective_dimensions")
    action_entropy = _array(records, "window_action_entropy")
    lineage_group_nmi = _array(records, "lineage_group_nmi")
    lineage_group_pair_enrichment = _array(records, "lineage_group_pair_enrichment")
    knowledge_effective_roots = _array(records, "knowledge_effective_root_contents")
    affinity_dims = _array(records, "resource_affinity_effective_dimensions")

    raw_correlations = {
        "mortality_vs_same_window_cohesion": _pearson(mortality, cohesion),
        "mortality_vs_next_window_cohesion": _pearson(mortality[:-1], cohesion[1:]),
        "effective_lineages_vs_cohesion": _pearson(effective_lineages, cohesion),
        "largest_lineage_fraction_vs_cohesion": _pearson(largest_lineage, cohesion),
        "strategy_dimensions_vs_action_entropy": _pearson(strategy_dims, action_entropy),
        "lineage_group_nmi_vs_cohesion": _pearson(lineage_group_nmi, cohesion),
        "lineage_group_pair_enrichment_vs_cohesion": _pearson(
            lineage_group_pair_enrichment, cohesion
        ),
        "knowledge_effective_roots_vs_effective_lineages": _pearson(
            knowledge_effective_roots, effective_lineages
        ),
    }
    first_difference = {
        "delta_mortality_vs_delta_cohesion": _pearson(
            np.diff(mortality), np.diff(cohesion)
        ),
        "mortality_vs_next_delta_cohesion": _pearson(
            mortality[:-1], np.diff(cohesion)
        ),
        "delta_effective_lineages_vs_delta_cohesion": _pearson(
            np.diff(effective_lineages), np.diff(cohesion)
        ),
        "delta_largest_lineage_fraction_vs_delta_cohesion": _pearson(
            np.diff(largest_lineage), np.diff(cohesion)
        ),
        "delta_strategy_dimensions_vs_delta_action_entropy": _pearson(
            np.diff(strategy_dims), np.diff(action_entropy)
        ),
        "delta_lineage_group_pair_enrichment_vs_delta_cohesion": _pearson(
            np.diff(lineage_group_pair_enrichment), np.diff(cohesion)
        ),
    }
    partial = {
        "mortality_vs_cohesion_controlling_tick_alive": _partial_pearson(
            mortality, cohesion, (ticks, alive)
        ),
        "effective_lineages_vs_cohesion_controlling_tick_alive": _partial_pearson(
            effective_lineages, cohesion, (ticks, alive)
        ),
        "largest_lineage_fraction_vs_cohesion_controlling_tick_alive": _partial_pearson(
            largest_lineage, cohesion, (ticks, alive)
        ),
        "lineage_group_pair_enrichment_vs_cohesion_controlling_tick_alive": (
            _partial_pearson(lineage_group_pair_enrichment, cohesion, (ticks, alive))
        ),
    }
    lag_correlations = _cross_lag_correlations(mortality, cohesion, max_lag=3)
    config_context = _resolved_config_context(path)
    transfer_committed = int(final.get("knowledge_transfer_committed_total", 0))
    transfer_probability = config_context.get("knowledge_transfer_probability")
    cultural_spread_interpretable = transfer_committed > 0 or (
        isinstance(transfer_probability, (int, float)) and transfer_probability > 0.0
    )
    warnings: list[str] = []
    if not cultural_spread_interpretable:
        warnings.append(
            "No committed or configured knowledge transfer was detected; root-content "
            "spread metrics describe mostly private experience creation, not cultural transmission."
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
        "alive_peak": int(np.nanmax(alive)),
        "alive_peak_tick": int(records[int(np.nanargmax(alive))]["tick"]),
        "alive_trough": int(np.nanmin(alive)),
        "alive_trough_tick": int(records[int(np.nanargmin(alive))]["tick"]),
        "effective_lineages_final": float(final.get("effective_lineages", 0.0)),
        "largest_lineage_fraction_final": float(final.get("largest_lineage_fraction", 0.0)),
        "strategy_effective_dimensions_final": float(
            final.get("strategy_effective_dimensions", 0.0)
        ),
        "window_action_entropy_final": float(final.get("window_action_entropy", 0.0)),
        "benefit_boundary_cohesion_final": float(
            final.get("benefit_boundary_cohesion", 0.0)
        ),
        "resource_affinity_effective_dimensions_final": (
            float(final["resource_affinity_effective_dimensions"])
            if "resource_affinity_effective_dimensions" in final
            else None
        ),
        "lineage_group_nmi_final": (
            float(final["lineage_group_nmi"]) if "lineage_group_nmi" in final else None
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
        "knowledge_transfer_committed_final": transfer_committed,
        "knowledge_cultural_spread_interpretable": cultural_spread_interpretable,
        "config_context": config_context,
        "trends_per_1000_ticks": {
            "alive": _slope_per_1000_ticks(ticks, alive),
            "effective_lineages": _slope_per_1000_ticks(ticks, effective_lineages),
            "largest_lineage_fraction": _slope_per_1000_ticks(ticks, largest_lineage),
            "strategy_effective_dimensions": _slope_per_1000_ticks(ticks, strategy_dims),
            "window_action_entropy": _slope_per_1000_ticks(ticks, action_entropy),
            "benefit_boundary_cohesion": _slope_per_1000_ticks(ticks, cohesion),
            "resource_affinity_effective_dimensions": _slope_per_1000_ticks(
                ticks, affinity_dims
            ),
        },
        "correlations_observational": raw_correlations,
        "correlations_first_difference": first_difference,
        "correlations_partial": partial,
        "mortality_to_cohesion_cross_lag": lag_correlations,
        "mortality_to_cohesion_best_lag": _best_lag(lag_correlations),
        "analysis_warnings": warnings,
        "causal_caution": (
            "All correlations are descriptive. Raw correlations can be dominated by "
            "shared time trends; first differences and partial correlations reduce, "
            "but do not eliminate, confounding."
        ),
    }


def _aggregate_numeric(values: list[float | int]) -> dict[str, float]:
    array = np.asarray(values, dtype=np.float64)
    return {
        "mean": float(array.mean()),
        "min": float(array.min()),
        "max": float(array.max()),
        "std": float(array.std()),
    }


def _sign_consistency(runs: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for section in (
        "correlations_observational",
        "correlations_first_difference",
        "correlations_partial",
    ):
        keys = sorted({key for run in runs for key in run[section]})
        for key in keys:
            values = [run[section].get(key) for run in runs]
            available = [float(value) for value in values if value is not None]
            positive = sum(value > 0.0 for value in available)
            negative = sum(value < 0.0 for value in available)
            zero = sum(value == 0.0 for value in available)
            result[f"{section}.{key}"] = {
                "available_runs": len(available),
                "positive_runs": positive,
                "negative_runs": negative,
                "zero_runs": zero,
                "same_nonzero_sign": bool(available) and (positive == len(available) or negative == len(available)),
                "mean": float(np.mean(available)) if available else None,
                "min": float(np.min(available)) if available else None,
                "max": float(np.max(available)) if available else None,
            }
    return result


def analyze(paths: list[str | Path]) -> dict[str, Any]:
    runs = [summarize_run(path, load_progress(path)) for path in paths]
    endpoint_keys = (
        "alive_final",
        "effective_lineages_final",
        "largest_lineage_fraction_final",
        "strategy_effective_dimensions_final",
        "window_action_entropy_final",
        "benefit_boundary_cohesion_final",
    )
    aggregate = {
        key: _aggregate_numeric([run[key] for run in runs]) for key in endpoint_keys
    }
    consistency = _sign_consistency(runs)
    robust = [
        key
        for key, value in consistency.items()
        if value["available_runs"] >= 3 and value["same_nonzero_sign"]
    ]
    return {
        "schema": "multi-seed-long-run-analysis-v2",
        "run_count": len(runs),
        "runs": runs,
        "endpoint_aggregate": aggregate,
        "cross_seed_sign_consistency": consistency,
        "repeated_directional_patterns": robust,
        "interpretation_boundary": (
            "Repeated signs across seeds support robustness, not necessity. Raw "
            "within-run correlations may reflect shared temporal drift. Controlled "
            "checkpoint interventions are required for phase-specific causal claims."
        ),
    }


def _format(value: Any, digits: int = 4) -> str:
    return "—" if value is None else f"{float(value):.{digits}f}"


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Multi-seed long-run analysis",
        "",
        f"Schema: `{report['schema']}`",
        f"Runs: **{report['run_count']}**",
        "",
        "> This report is observational. Raw correlations, first differences and partial correlations do not identify an in-world causal mechanism.",
        "",
        "| Run | Final tick | Alive | Effective lineages | Largest lineage | Strategy dims | Action entropy | Cohesion | Affinity dims | Pair enrichment |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for run in report["runs"]:
        lines.append(
            "| {name} | {tick} | {alive} | {effective:.4f} | {largest:.4f} | "
            "{dims:.4f} | {entropy:.4f} | {cohesion:.4f} | {affinity} | {enrichment} |".format(
                name=run["run_name"],
                tick=run["final_tick"],
                alive=run["alive_final"],
                effective=run["effective_lineages_final"],
                largest=run["largest_lineage_fraction_final"],
                dims=run["strategy_effective_dimensions_final"],
                entropy=run["window_action_entropy_final"],
                cohesion=run["benefit_boundary_cohesion_final"],
                affinity=_format(run["resource_affinity_effective_dimensions_final"]),
                enrichment=_format(run["lineage_group_pair_enrichment_final"]),
            )
        )
    lines.extend(["", "## Within-run raw observational correlations", ""])
    for run in report["runs"]:
        lines.append(f"### {run['run_name']}")
        for key, value in run["correlations_observational"].items():
            lines.append(f"- `{key}`: {_format(value)}")
        lines.append("")
    lines.extend(["## First-difference checks", ""])
    for run in report["runs"]:
        lines.append(f"### {run['run_name']}")
        for key, value in run["correlations_first_difference"].items():
            lines.append(f"- `{key}`: {_format(value)}")
        lines.append("")
    lines.extend(["## Partial correlations controlling tick and alive", ""])
    for run in report["runs"]:
        lines.append(f"### {run['run_name']}")
        for key, value in run["correlations_partial"].items():
            lines.append(f"- `{key}`: {_format(value)}")
        best = run["mortality_to_cohesion_best_lag"]
        if best is not None:
            lines.append(
                "- strongest mortality→cohesion cross-lag: "
                f"lag `{best['lag_windows']}` windows, r={best['correlation']:.4f}"
            )
        for warning in run["analysis_warnings"]:
            lines.append(f"- warning: {warning}")
        lines.append("")
    lines.extend(["## Repeated directional patterns", ""])
    if report["repeated_directional_patterns"]:
        lines.extend(f"- `{key}`" for key in report["repeated_directional_patterns"])
    else:
        lines.append("- No metric had the same non-zero sign in at least three runs.")
    lines.extend(["", "## Interpretation boundary", "", report["interpretation_boundary"], ""])
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
