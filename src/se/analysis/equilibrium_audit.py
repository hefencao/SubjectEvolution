"""Qualify a multi-seed source for cycle-aware demographic equilibrium.

The gate is intentionally narrower than a selection audit.  It asks whether an
integrated subject/environment system remains bounded, turns over generations,
retains multiple founder lineages and preserves broad heritable variation over
at least one complete configured environmental forcing cycle.  It never
estimates fitness, authorizes a gene-specific intervention, or treats repeated
windows as independent replicates.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from statistics import median
from typing import Any, Iterable

import numpy as np

from se.analysis.selection_validity import SelectionValidityThresholds, audit_run

SCHEMA = "integrated-equilibrium-qualification-v2"

# These thresholds retain the D1 health/turnover and lineage requirements.  The
# generic selection audit's three-window settled-population decision is exposed
# only as an advisory diagnostic below; qualification uses a cycle-aware window.
THRESHOLDS = SelectionValidityThresholds(
    minimum_alive_fraction_to_initial=0.50,
    minimum_effective_lineages=16.0,
    maximum_largest_lineage_fraction=0.20,
    minimum_successful_parent_samples_per_window=1,
    minimum_mean_generation=1.0,
    minimum_max_generation=3,
    minimum_cumulative_births_per_initial=1.0,
    settled_window_count=3,
    minimum_settled_alive=64,
    maximum_settled_alive_cv=0.15,
    maximum_settled_net_growth_fraction=0.15,
    maximum_settled_alive_slope_fraction_per_window=0.02,
    maximum_settled_span_change_fraction=0.10,
    minimum_descendant_alive_fraction=0.50,
    minimum_unique_successful_parents_per_window=1,
    minimum_effective_successful_parents_per_window=1.0,
    maximum_largest_parent_contribution_fraction=1.0,
    minimum_source_ready_seed_count=2,
)

CYCLE_MAXIMUM_ALIVE_CV = 0.15
CYCLE_MAXIMUM_ABS_SLOPE_FRACTION_PER_SAMPLE = 0.02
CYCLE_MAXIMUM_ALIVE_ENVELOPE_FRACTION_OF_MEAN = 0.50
CYCLE_MINIMUM_ALIVE_FRACTION_TO_INITIAL = 0.50
CYCLE_MAXIMUM_ALIVE_FRACTION_TO_INITIAL = 2.00


def _read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"expected JSON object: {path}")
    return payload


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        payload = json.loads(line)
        if not isinstance(payload, dict):
            raise ValueError(f"expected JSON object at {path}:{line_number}")
        rows.append(payload)
    rows.sort(key=lambda row: int(row.get("tick", 0)))
    if not rows:
        raise ValueError(f"empty evolution progress: {path}")
    return rows


def _positive_periods(value: Any, *, key: str = "") -> Iterable[tuple[str, int]]:
    """Yield positive environmental forcing periods from a config subtree."""
    if isinstance(value, dict):
        for child_key, child_value in value.items():
            child_path = f"{key}.{child_key}" if key else child_key
            if child_key.endswith("_period") and isinstance(child_value, (int, float)):
                period = int(child_value)
                if period > 0:
                    yield child_path, period
            elif child_key.endswith("_periods") and isinstance(child_value, list):
                for index, item in enumerate(child_value):
                    if isinstance(item, (int, float)) and int(item) > 0:
                        yield f"{child_path}[{index}]", int(item)
            elif isinstance(child_value, (dict, list)):
                yield from _positive_periods(child_value, key=child_path)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            if isinstance(child, (dict, list)):
                yield from _positive_periods(child, key=f"{key}[{index}]")


def _sampling_interval(rows: list[dict[str, Any]]) -> int:
    ticks = [int(row["tick"]) for row in rows]
    deltas = [later - earlier for earlier, later in zip(ticks, ticks[1:]) if later > earlier]
    if not deltas:
        raise ValueError("equilibrium qualification requires at least two progress samples")
    interval = int(round(median(deltas)))
    if interval <= 0:
        raise ValueError("invalid progress sampling interval")
    return interval


def _cycle_aware_regime(run_dir: Path, initial_population: int) -> dict[str, Any]:
    rows = _read_jsonl(run_dir / "evolution_progress.jsonl")
    config = _read_json(run_dir / "resolved_config.json")
    periods = sorted(_positive_periods(config.get("environment", {})), key=lambda item: item[1])
    if not periods:
        raise ValueError("resolved config has no explicit environmental forcing period")
    longest_path, longest_period = periods[-1]
    interval = _sampling_interval(rows)

    # One more observation than ceil(period/interval) makes the first-to-last
    # span cover at least one complete forcing period.
    required_samples = int(math.ceil(longest_period / interval) + 1)
    recent = rows[-required_samples:] if len(rows) >= required_samples else rows
    first_tick = int(recent[0]["tick"])
    final_tick = int(recent[-1]["tick"])
    observation_span = final_tick - first_tick
    alive = np.asarray([float(row.get("alive", 0)) for row in recent], dtype=np.float64)
    mean_alive = float(np.mean(alive)) if alive.size else 0.0
    if mean_alive > 0.0 and alive.size >= 2:
        cv = float(np.std(alive) / mean_alive)
        slope = float(np.polyfit(np.arange(alive.size, dtype=np.float64), alive, 1)[0])
        slope_fraction = slope / mean_alive
        envelope_fraction = float((np.max(alive) - np.min(alive)) / mean_alive)
    else:
        cv = float("inf")
        slope_fraction = float("inf")
        envelope_fraction = float("inf")

    minimum_alive = float(np.min(alive)) if alive.size else 0.0
    maximum_alive = float(np.max(alive)) if alive.size else 0.0
    checks = {
        "environmental_periods_declared": bool(periods),
        "cycle_coverage": bool(
            len(rows) >= required_samples and observation_span >= longest_period
        ),
        "minimum_population_bounded": bool(
            minimum_alive / initial_population >= CYCLE_MINIMUM_ALIVE_FRACTION_TO_INITIAL
        ),
        "maximum_population_bounded": bool(
            maximum_alive / initial_population <= CYCLE_MAXIMUM_ALIVE_FRACTION_TO_INITIAL
        ),
        "cycle_alive_cv_bounded": cv <= CYCLE_MAXIMUM_ALIVE_CV,
        "cycle_trend_bounded": abs(slope_fraction)
        <= CYCLE_MAXIMUM_ABS_SLOPE_FRACTION_PER_SAMPLE,
        "cycle_envelope_bounded": envelope_fraction
        <= CYCLE_MAXIMUM_ALIVE_ENVELOPE_FRACTION_OF_MEAN,
    }
    return {
        "schema": "cycle-aware-bounded-demographic-regime-v1",
        "ready": all(checks.values()),
        "checks": checks,
        "environmental_periods": [
            {"path": path, "ticks": ticks} for path, ticks in periods
        ],
        "longest_environmental_period_path": longest_path,
        "longest_environmental_period_ticks": longest_period,
        "progress_sampling_interval_ticks": interval,
        "required_sample_count": required_samples,
        "available_sample_count": len(rows),
        "assessed_sample_count": len(recent),
        "assessment_start_tick": first_tick,
        "assessment_final_tick": final_tick,
        "assessment_span_ticks": observation_span,
        "alive_mean": mean_alive,
        "alive_minimum": int(minimum_alive),
        "alive_maximum": int(maximum_alive),
        "alive_minimum_fraction_to_initial": minimum_alive / initial_population,
        "alive_maximum_fraction_to_initial": maximum_alive / initial_population,
        "alive_cv": cv,
        "alive_slope_fraction_per_sample": slope_fraction,
        "alive_envelope_fraction_of_mean": envelope_fraction,
        "thresholds": {
            "maximum_alive_cv": CYCLE_MAXIMUM_ALIVE_CV,
            "maximum_abs_slope_fraction_per_sample": CYCLE_MAXIMUM_ABS_SLOPE_FRACTION_PER_SAMPLE,
            "maximum_alive_envelope_fraction_of_mean": CYCLE_MAXIMUM_ALIVE_ENVELOPE_FRACTION_OF_MEAN,
            "minimum_alive_fraction_to_initial": CYCLE_MINIMUM_ALIVE_FRACTION_TO_INITIAL,
            "maximum_alive_fraction_to_initial": CYCLE_MAXIMUM_ALIVE_FRACTION_TO_INITIAL,
        },
        "interpretation": (
            "Qualification spans at least one complete configured environmental forcing "
            "cycle. Shorter-window rebounds or declines are retained as advisory phase "
            "diagnostics and do not override this cycle-aware decision."
        ),
    }


def build_report(source_root: str | Path, *, required_seed_count: int) -> dict[str, Any]:
    root = Path(source_root)
    seed_dirs = sorted(path for path in root.glob("seed_*") if path.is_dir())
    if not seed_dirs:
        raise ValueError(f"no seed directories under {root}")
    rows = []
    for path in seed_dirs:
        audit = audit_run(path.name, path, thresholds=THRESHOLDS)
        final = audit["final_population"]
        advisory = audit["post_bottleneck_regime"]
        initial_population = int(audit["initial_population"])
        cycle_regime = _cycle_aware_regime(path, initial_population)
        final_multiple = float(final["alive_fraction_to_initial"])
        checks = {
            "completed_turnover": bool(all(final["turnover_checks"].values())),
            "descendant_replacement": float(final.get("descendant_alive_fraction") or 0.0) >= 0.50,
            "final_population_scale_bounded": 0.50 <= final_multiple <= 2.00,
            "cycle_aware_population_regime": bool(cycle_regime["ready"]),
            "effective_lineages": float(final["effective_lineages"]) >= 16.0,
            "largest_lineage_bounded": float(final["largest_lineage_fraction"]) <= 0.20,
            "canonical_diversity_retained": float(final.get("canonical_diversity_ratio_to_initial") or 0.0) >= 0.50,
            "policy_diversity_retained": float(final.get("policy_diversity_ratio_to_initial") or 0.0) >= 0.50,
        }
        rows.append({
            "seed": int(path.name.split("_", 1)[1]),
            "ready": all(checks.values()),
            "checks": checks,
            "final": {
                "tick": final["tick"],
                "alive": final["alive"],
                "alive_fraction_to_initial": final_multiple,
                "cumulative_births_per_initial": final["cumulative_births_per_initial"],
                "descendant_alive_fraction": final.get("descendant_alive_fraction"),
                "mean_generation": final["mean_generation"],
                "max_generation": final["max_generation"],
                "effective_lineages": final["effective_lineages"],
                "largest_lineage_fraction": final["largest_lineage_fraction"],
                "canonical_diversity_ratio_to_initial": final.get("canonical_diversity_ratio_to_initial"),
                "policy_diversity_ratio_to_initial": final.get("policy_diversity_ratio_to_initial"),
            },
            "cycle_aware_regime": cycle_regime,
            "short_window_advisory": {
                key: advisory[key] for key in (
                    "settled_window_count_required",
                    "settled_window_count_available",
                    "settled_window_start_tick",
                    "settled_alive_cv",
                    "settled_maximum_abs_net_growth_fraction",
                    "settled_alive_slope_fraction_per_window",
                    "settled_span_change_fraction",
                    "active_rebound",
                    "active_decline",
                )
            },
        })
    ready_count = sum(int(row["ready"]) for row in rows)
    exact_seed_count = len(rows) == required_seed_count
    ready = exact_seed_count and ready_count == required_seed_count
    return {
        "schema": SCHEMA,
        "source_root": str(root),
        "required_seed_count": required_seed_count,
        "seed_count": len(rows),
        "exact_seed_count": exact_seed_count,
        "ready_seed_count": ready_count,
        "ready": ready,
        "independent_unit": "seed",
        "windows_are_independent_replicates": False,
        "seeds": rows,
        "authorization": {
            "integrated_retention_interpretation_authorized": ready,
            "gene_specific_adjustment_authorized": False,
            "selection_claim_authorized": False,
            "paired_experiment_authorized": False,
        },
        "interpretation": (
            "Cycle-aware equilibrium qualification establishes a bounded, multi-lineage "
            "substrate for integrated retention screening only. It does not estimate "
            "fitness or selection, and it does not authorize one experiment per gene."
        ),
    }


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Cycle-aware integrated equilibrium qualification",
        "",
        f"Ready: **{report['ready']}**",
        "",
        "| seed | ready | alive | alive/initial | births/initial | descendants | mean gen | max gen | effective lineages | largest lineage | cycle span | cycle slope | cycle CV |",
        "|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in report["seeds"]:
        final = row["final"]
        regime = row["cycle_aware_regime"]
        lines.append(
            f"| {row['seed']} | {row['ready']} | {final['alive']} | "
            f"{final['alive_fraction_to_initial']:.3f} | "
            f"{final['cumulative_births_per_initial']:.3f} | "
            f"{final['descendant_alive_fraction']:.3f} | "
            f"{final['mean_generation']:.3f} | {final['max_generation']} | "
            f"{final['effective_lineages']:.3f} | "
            f"{final['largest_lineage_fraction']:.3f} | "
            f"{regime['assessment_span_ticks']} | "
            f"{regime['alive_slope_fraction_per_sample']:.5f} | "
            f"{regime['alive_cv']:.5f} |"
        )
    lines += [
        "",
        "> The qualification window covers at least one complete configured environmental forcing cycle. Three-window rebound/decline remains advisory only.",
        "",
        "> This gate authorizes integrated retention screening, not selection claims or per-gene experiment generation.",
        "",
    ]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", required=True)
    parser.add_argument("--required-seed-count", type=int, default=3)
    parser.add_argument("--output", required=True)
    parser.add_argument("--allow-not-ready", action="store_true")
    args = parser.parse_args(argv)
    report = build_report(args.source_root, required_seed_count=args.required_seed_count)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    output.with_suffix(".md").write_text(render_markdown(report), encoding="utf-8")
    print(json.dumps({"ready": report["ready"], "ready_seed_count": report["ready_seed_count"], "output": str(output)}))
    if not report["ready"] and not args.allow_not_ready:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
