"""Audit whether a long run supports evolutionary-selection inference.

The audit is deliberately observational.  It never changes simulation state,
never rescues a shrinking population, and never drops a run because it fails a
population or turnover threshold.  Its independent unit is the run/seed; JSONL
windows are repeated observations within that run.
"""
from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
import json
from pathlib import Path
from typing import Any, Iterable

import numpy as np

SCHEMA = "demographic-selection-validity-audit-v1"
PLAN_SCHEMA = "demographic-selection-validity-plan-v1"


@dataclass(frozen=True)
class SelectionValidityThresholds:
    minimum_alive_fraction_to_initial: float = 0.25
    minimum_effective_lineages: float = 100.0
    maximum_largest_lineage_fraction: float = 0.25
    minimum_successful_parent_samples_per_window: int = 100
    minimum_mean_generation: float = 1.0
    minimum_max_generation: int = 3
    minimum_cumulative_births_per_initial: float = 1.0

    def validate(self) -> None:
        if not 0.0 < self.minimum_alive_fraction_to_initial <= 1.0:
            raise ValueError("minimum alive fraction must be in (0, 1]")
        if self.minimum_effective_lineages < 1.0:
            raise ValueError("minimum effective lineages must be at least one")
        if not 0.0 < self.maximum_largest_lineage_fraction <= 1.0:
            raise ValueError("maximum largest-lineage fraction must be in (0, 1]")
        if self.minimum_successful_parent_samples_per_window < 1:
            raise ValueError("minimum parent samples must be positive")
        if self.minimum_mean_generation < 0.0:
            raise ValueError("minimum mean generation cannot be negative")
        if self.minimum_max_generation < 0:
            raise ValueError("minimum maximum-generation cannot be negative")
        if self.minimum_cumulative_births_per_initial < 0.0:
            raise ValueError("minimum births per initial cannot be negative")


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"invalid JSONL at {path}:{line_number}") from exc
        if not isinstance(row, dict):
            raise ValueError(f"JSONL row {line_number} is not an object")
        rows.append(row)
    rows.sort(key=lambda row: int(row.get("tick", 0)))
    return rows


def _first_tick(rows: Iterable[dict[str, Any]], predicate) -> int | None:
    for row in rows:
        if predicate(row):
            return int(row["tick"])
    return None


def _death_cause_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    available = bool(rows) and all(
        "death_cause_code_counts_window" in row for row in rows
    )
    if not available:
        return {
            "available": False,
            "reason": "run predates per-window canonical death-cause accounting",
        }
    signatures = np.zeros(8, dtype=np.int64)
    for row in rows:
        counts = np.asarray(row["death_cause_code_counts_window"], dtype=np.int64)
        if counts.shape != (8,) or np.any(counts < 0):
            raise ValueError("death-cause windows must contain eight non-negative buckets")
        signatures += counts
    events = int(signatures[1:].sum())
    energy = int(signatures[[1, 3, 5, 7]].sum())
    integrity = int(signatures[[2, 3, 6, 7]].sum())
    age = int(signatures[[4, 5, 6, 7]].sum())
    return {
        "available": True,
        "death_event_count": events,
        "signature_counts": signatures.tolist(),
        "energy_depleted_count": energy,
        "integrity_depleted_count": integrity,
        "max_age_count": age,
        "energy_depleted_fraction": energy / events if events else 0.0,
        "integrity_depleted_fraction": integrity / events if events else 0.0,
        "max_age_fraction": age / events if events else 0.0,
        "overlap_note": (
            "Cause-presence fractions can sum above one because a death event may "
            "simultaneously satisfy energy, integrity, and age conditions."
        ),
    }


def _window_assessment(
    row: dict[str, Any], thresholds: SelectionValidityThresholds
) -> dict[str, Any]:
    alive_fraction = float(row.get("alive_fraction_to_initial", 0.0))
    effective_lineages = float(row.get("effective_lineages", 0.0))
    largest_lineage = float(row.get("largest_lineage_fraction", 1.0))
    parent_samples = int(row.get("selection_successful_parent_samples_window", 0))
    mean_generation = float(row.get("mean_generation", 0.0))
    max_generation = int(row.get("max_generation", 0))
    births_per_initial = float(row.get("cumulative_births_per_initial", 0.0))
    demographic_checks = {
        "alive_fraction_met": (
            alive_fraction >= thresholds.minimum_alive_fraction_to_initial
        ),
        "effective_lineages_met": (
            effective_lineages >= thresholds.minimum_effective_lineages
        ),
        "largest_lineage_fraction_met": (
            largest_lineage <= thresholds.maximum_largest_lineage_fraction
        ),
        "successful_parent_samples_met": (
            parent_samples >= thresholds.minimum_successful_parent_samples_per_window
        ),
    }
    turnover_checks = {
        "mean_generation_met": mean_generation >= thresholds.minimum_mean_generation,
        "max_generation_met": max_generation >= thresholds.minimum_max_generation,
        "cumulative_births_per_initial_met": (
            births_per_initial >= thresholds.minimum_cumulative_births_per_initial
        ),
    }
    demographic_supported = all(demographic_checks.values())
    evolutionary_supported = demographic_supported and all(turnover_checks.values())
    return {
        "tick": int(row.get("tick", 0)),
        "window_ticks": int(row.get("window_ticks", 0)),
        "alive": int(row.get("alive", 0)),
        "alive_fraction_to_initial": alive_fraction,
        "effective_lineages": effective_lineages,
        "largest_lineage_fraction": largest_lineage,
        "successful_parent_samples_window": parent_samples,
        "births_window": int(row.get("births_window", 0)),
        "deaths_window": int(row.get("deaths_window", 0)),
        "net_growth_window": int(row.get("births_window", 0))
        - int(row.get("deaths_window", 0)),
        "mean_generation": mean_generation,
        "max_generation": max_generation,
        "cumulative_births_per_initial": births_per_initial,
        "demographic_checks": demographic_checks,
        "turnover_checks": turnover_checks,
        "demographic_selection_window_supported": demographic_supported,
        "evolutionary_selection_window_supported": evolutionary_supported,
    }


def audit_run(
    label: str,
    run_dir: Path,
    *,
    thresholds: SelectionValidityThresholds,
) -> dict[str, Any]:
    run_dir = run_dir.resolve()
    progress_path = run_dir / "evolution_progress.jsonl"
    summary_path = run_dir / "summary.json"
    plan_path = run_dir / "run_plan.json"
    if not progress_path.is_file():
        raise FileNotFoundError(f"missing evolution progress: {progress_path}")
    if not summary_path.is_file():
        raise FileNotFoundError(f"missing summary: {summary_path}")
    rows = _read_jsonl(progress_path)
    if not rows:
        raise ValueError(f"evolution progress is empty: {progress_path}")
    summary = _read_json(summary_path)
    plan = _read_json(plan_path) if plan_path.is_file() else None
    resolved_config_path = run_dir / "resolved_config.json"
    resolved_config = (
        _read_json(resolved_config_path) if resolved_config_path.is_file() else None
    )
    initial_population = int(
        rows[0].get(
            "initial_population",
            (resolved_config or {}).get("world", {}).get(
                "initial_entities",
                (plan or {}).get("world", {}).get("initial_entities", 0),
            ),
        )
    )
    if initial_population <= 0:
        fraction = float(rows[0].get("alive_fraction_to_initial", 0.0))
        if fraction > 0.0:
            initial_population = int(round(int(rows[0].get("alive", 0)) / fraction))
        else:
            raise ValueError(
                "cannot determine initial population; provide resolved_config.json or "
                "v0.67 evolution progress fields"
            )
    normalized_rows: list[dict[str, Any]] = []
    cumulative_births = 0
    cumulative_deaths = 0
    for source in rows:
        row = dict(source)
        cumulative_births += int(row.get("births_window", 0))
        cumulative_deaths += int(row.get("deaths_window", 0))
        row.setdefault("initial_population", initial_population)
        row.setdefault(
            "alive_fraction_to_initial",
            float(int(row.get("alive", 0)) / initial_population),
        )
        row.setdefault(
            "cumulative_births_per_initial",
            float(cumulative_births / initial_population),
        )
        row.setdefault(
            "cumulative_deaths_per_initial",
            float(cumulative_deaths / initial_population),
        )
        normalized_rows.append(row)
    assessments = [_window_assessment(row, thresholds) for row in normalized_rows]
    population_floor = thresholds.minimum_alive_fraction_to_initial
    first_below_population_floor = _first_tick(
        assessments,
        lambda row: row["alive_fraction_to_initial"] < population_floor,
    )
    first_turnover_supported = _first_tick(
        assessments,
        lambda row: all(row["turnover_checks"].values()),
    )
    collapse_before_turnover = (
        first_below_population_floor is not None
        and (
            first_turnover_supported is None
            or first_below_population_floor < first_turnover_supported
        )
    )
    supported_windows = [
        row for row in assessments if row["evolutionary_selection_window_supported"]
    ]
    demographic_windows = [
        row for row in assessments if row["demographic_selection_window_supported"]
    ]
    minimum_alive_fraction = min(
        float(row["alive_fraction_to_initial"]) for row in assessments
    )
    final = assessments[-1]
    if collapse_before_turnover:
        recommendation = "bottleneck-dominated-do-not-interpret-as-effective-selection"
    elif not supported_windows:
        recommendation = "selection-inference-insufficient-retain-run-without-selection-claim"
    else:
        recommendation = "selection-supported-windows-present-require-independent-seed-replication"
    return {
        "label": label,
        "run_dir": str(run_dir),
        "summary_tick": int(summary.get("tick", 0)),
        "reporting_state_tick": int(summary.get("reporting_state_tick", summary.get("tick", 0))),
        "initial_population": initial_population,
        "window_count": len(assessments),
        "minimum_alive_fraction_to_initial": minimum_alive_fraction,
        "first_tick_below_population_floor": first_below_population_floor,
        "first_tick_with_turnover_support": first_turnover_supported,
        "population_collapse_before_turnover": collapse_before_turnover,
        "demographic_supported_window_count": len(demographic_windows),
        "evolutionary_supported_window_count": len(supported_windows),
        "final_population": final,
        "death_causes": _death_cause_summary(normalized_rows),
        "windows": assessments,
        "selection_inference_supported_within_run": bool(supported_windows),
        "recommendation": recommendation,
        "interpretation_boundary": (
            "This is a within-run adequacy audit. Windows are repeated observations, "
            "not independent replicates. Passing windows still require independent seeds; "
            "failing windows remain in the record and are never replaced by outcome."
        ),
    }


def parse_run_spec(value: str) -> tuple[str, Path]:
    if "=" not in value:
        path = Path(value)
        return path.name, path
    label, raw = value.split("=", 1)
    if not label.strip():
        raise ValueError("run label cannot be empty")
    return label.strip(), Path(raw)


def build_audit(
    runs: Iterable[tuple[str, Path]],
    *,
    thresholds: SelectionValidityThresholds | None = None,
) -> dict[str, Any]:
    thresholds = thresholds or SelectionValidityThresholds()
    thresholds.validate()
    rows = [audit_run(label, path, thresholds=thresholds) for label, path in runs]
    supported = [row for row in rows if row["selection_inference_supported_within_run"]]
    bottlenecked = [row for row in rows if row["population_collapse_before_turnover"]]
    return {
        "schema": SCHEMA,
        "plan": {
            "schema": PLAN_SCHEMA,
            "thresholds": asdict(thresholds),
            "independent_unit": "run-seed",
            "windows_are_independent_replicates": False,
            "failed_runs_or_windows_replaced": False,
            "feedback_to_world": False,
            "population_rescue_or_diversity_protection": False,
        },
        "runs": rows,
        "run_count": len(rows),
        "bottleneck_dominated_run_count": len(bottlenecked),
        "within_run_selection_supported_count": len(supported),
        "cross_seed_selection_inference_supported": False,
        "recommendation": (
            "bottleneck-dominated-source-redesign-before-selection-claims"
            if bottlenecked
            else (
                "collect-independent-seed-replication"
                if supported
                else "retain-runs-and-redesign-source-before-selection-claims"
            )
        ),
        "interpretation_boundary": (
            "No cross-seed effect is estimated here. The audit separates demographic "
            "support and generation turnover from mere tick duration, and never changes "
            "the simulated world or filters results by outcome."
        ),
    }


def render_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# Demographic selection validity audit",
        "",
        f"Schema: `{payload['schema']}`",
        "",
        "| Run | Initial | Min alive fraction | First below floor | First turnover support | Demographic windows | Evolutionary windows | Bottleneck before turnover |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in payload["runs"]:
        lines.append(
            f"| {row['label']} | {row['initial_population']} | "
            f"{row['minimum_alive_fraction_to_initial']} | "
            f"{row['first_tick_below_population_floor']} | "
            f"{row['first_tick_with_turnover_support']} | "
            f"{row['demographic_supported_window_count']} | "
            f"{row['evolutionary_supported_window_count']} | "
            f"{row['population_collapse_before_turnover']} |"
        )
    lines += [
        "",
        f"Recommendation: `{payload['recommendation']}`",
        "",
        payload["interpretation_boundary"],
        "",
        "A rapid population collapse before generation turnover is classified as a "
        "bottleneck-dominated trajectory. It may still be useful for mechanism, accounting, "
        "or failure-mode analysis, but it is not treated as effective evolutionary-selection evidence.",
        "",
    ]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", action="append", required=True, help="LABEL=run/output/directory")
    parser.add_argument("--output", required=True)
    parser.add_argument("--minimum-alive-fraction", type=float, default=0.25)
    parser.add_argument("--minimum-effective-lineages", type=float, default=100.0)
    parser.add_argument("--maximum-largest-lineage-fraction", type=float, default=0.25)
    parser.add_argument("--minimum-parent-samples", type=int, default=100)
    parser.add_argument("--minimum-mean-generation", type=float, default=1.0)
    parser.add_argument("--minimum-max-generation", type=int, default=3)
    parser.add_argument("--minimum-births-per-initial", type=float, default=1.0)
    args = parser.parse_args(argv)
    thresholds = SelectionValidityThresholds(
        minimum_alive_fraction_to_initial=args.minimum_alive_fraction,
        minimum_effective_lineages=args.minimum_effective_lineages,
        maximum_largest_lineage_fraction=args.maximum_largest_lineage_fraction,
        minimum_successful_parent_samples_per_window=args.minimum_parent_samples,
        minimum_mean_generation=args.minimum_mean_generation,
        minimum_max_generation=args.minimum_max_generation,
        minimum_cumulative_births_per_initial=args.minimum_births_per_initial,
    )
    payload = build_audit(
        (parse_run_spec(value) for value in args.run), thresholds=thresholds
    )
    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=True)
    (output / "selection_validity_plan.json").write_text(
        json.dumps(payload["plan"], ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (output / "selection_validity_audit.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (output / "selection_validity_audit.md").write_text(
        render_markdown(payload), encoding="utf-8"
    )
    print(json.dumps({"recommendation": payload["recommendation"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
