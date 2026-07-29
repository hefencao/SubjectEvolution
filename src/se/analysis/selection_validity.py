"""Audit whether demographic trajectories can support selection inference.

The audit is observational. It never changes simulation state, rescues a
shrinking population, protects diversity, or replaces a failed run. Windows
are repeated measurements within a run; the independent unit is the seed.
A post-bottleneck source recommendation is only a preregistration candidate
for future independent runs and never retroactively validates the pilot used
to derive it.
"""
from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
import json
from pathlib import Path
from typing import Any, Iterable, Sequence

import numpy as np

SCHEMA = "demographic-selection-validity-audit-v2"
PLAN_SCHEMA = "demographic-selection-validity-plan-v2"


@dataclass(frozen=True)
class SelectionValidityThresholds:
    minimum_alive_fraction_to_initial: float = 0.25
    minimum_effective_lineages: float = 100.0
    maximum_largest_lineage_fraction: float = 0.25
    minimum_successful_parent_samples_per_window: int = 100
    minimum_mean_generation: float = 1.0
    minimum_max_generation: int = 3
    minimum_cumulative_births_per_initial: float = 1.0
    settled_window_count: int = 3
    minimum_settled_alive: int = 1000
    maximum_settled_alive_cv: float = 0.15
    maximum_settled_net_growth_fraction: float = 0.15
    minimum_descendant_alive_fraction: float = 0.75
    minimum_unique_successful_parents_per_window: int = 100
    minimum_effective_successful_parents_per_window: float = 80.0
    maximum_largest_parent_contribution_fraction: float = 0.05
    minimum_source_ready_seed_count: int = 3

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
        if self.settled_window_count < 2:
            raise ValueError("settled window count must be at least two")
        if self.minimum_settled_alive < 1:
            raise ValueError("minimum settled alive must be positive")
        if self.maximum_settled_alive_cv < 0.0:
            raise ValueError("maximum settled alive CV cannot be negative")
        if self.maximum_settled_net_growth_fraction < 0.0:
            raise ValueError("maximum settled net growth fraction cannot be negative")
        if not 0.0 <= self.minimum_descendant_alive_fraction <= 1.0:
            raise ValueError("minimum descendant fraction must be in [0, 1]")
        if self.minimum_unique_successful_parents_per_window < 1:
            raise ValueError("minimum unique parent count must be positive")
        if self.minimum_effective_successful_parents_per_window < 1.0:
            raise ValueError("minimum effective parent count must be at least one")
        if not 0.0 < self.maximum_largest_parent_contribution_fraction <= 1.0:
            raise ValueError("maximum parent contribution fraction must be in (0, 1]")
        if self.minimum_source_ready_seed_count < 2:
            raise ValueError("source readiness requires at least two seeds")


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


def _normalize_rows(
    rows: Sequence[dict[str, Any]], initial_population: int
) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
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
        normalized.append(row)
    return normalized


def _death_cause_summary(rows: Sequence[dict[str, Any]]) -> dict[str, Any]:
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
    unique_parents = row.get("selection_unique_successful_parents_window")
    effective_parents = row.get("selection_effective_successful_parents_window")
    largest_parent = row.get(
        "selection_largest_parent_contribution_fraction_window"
    )
    descendant_fraction = row.get("descendant_alive_fraction")
    births_window = int(row.get("births_window", 0))
    deaths_window = int(row.get("deaths_window", 0))
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
    contributor_metrics_available = all(
        value is not None for value in (unique_parents, effective_parents, largest_parent)
    )
    contributor_checks = {
        "unique_successful_parents_met": bool(
            contributor_metrics_available
            and int(unique_parents)
            >= thresholds.minimum_unique_successful_parents_per_window
        ),
        "effective_successful_parents_met": bool(
            contributor_metrics_available
            and float(effective_parents)
            >= thresholds.minimum_effective_successful_parents_per_window
        ),
        "largest_parent_contribution_met": bool(
            contributor_metrics_available
            and float(largest_parent)
            <= thresholds.maximum_largest_parent_contribution_fraction
        ),
    }
    descendant_metric_available = descendant_fraction is not None
    descendant_check = bool(
        descendant_metric_available
        and float(descendant_fraction) >= thresholds.minimum_descendant_alive_fraction
    )
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
        "unique_successful_parents_window": (
            int(unique_parents) if unique_parents is not None else None
        ),
        "effective_successful_parents_window": (
            float(effective_parents) if effective_parents is not None else None
        ),
        "largest_parent_contribution_fraction_window": (
            float(largest_parent) if largest_parent is not None else None
        ),
        "contributor_metrics_available": contributor_metrics_available,
        "births_window": births_window,
        "deaths_window": deaths_window,
        "net_growth_window": births_window - deaths_window,
        "mean_generation": mean_generation,
        "max_generation": max_generation,
        "generation_zero_alive": row.get("generation_zero_alive"),
        "descendant_alive": row.get("descendant_alive"),
        "descendant_alive_fraction": (
            float(descendant_fraction) if descendant_fraction is not None else None
        ),
        "descendant_metric_available": descendant_metric_available,
        "descendant_fraction_met": descendant_check,
        "cumulative_births_per_initial": births_per_initial,
        "demographic_checks": demographic_checks,
        "turnover_checks": turnover_checks,
        "contributor_checks": contributor_checks,
        "demographic_selection_window_supported": demographic_supported,
        "evolutionary_selection_window_supported": evolutionary_supported,
    }


def _settled_regime(
    assessments: Sequence[dict[str, Any]],
    *,
    thresholds: SelectionValidityThresholds,
    collapse_before_turnover: bool,
) -> dict[str, Any]:
    alive = np.asarray([row["alive"] for row in assessments], dtype=np.float64)
    trough_index = int(np.argmin(alive))
    trough = assessments[trough_index]
    final = assessments[-1]
    required = thresholds.settled_window_count
    recent = list(assessments[-required:]) if len(assessments) >= required else []
    if recent:
        recent_alive = np.asarray([row["alive"] for row in recent], dtype=np.float64)
        alive_mean = float(recent_alive.mean())
        alive_cv = float(recent_alive.std() / alive_mean) if alive_mean > 0.0 else float("inf")
        growth_fraction = np.asarray(
            [abs(float(row["net_growth_window"])) / max(float(row["alive"]), 1.0) for row in recent],
            dtype=np.float64,
        )
        maximum_growth_fraction = float(growth_fraction.max(initial=0.0))
        settled_population_supported = bool(
            int(recent_alive.min()) >= thresholds.minimum_settled_alive
            and alive_cv <= thresholds.maximum_settled_alive_cv
            and maximum_growth_fraction
            <= thresholds.maximum_settled_net_growth_fraction
        )
        settled_lineage_supported = bool(
            min(float(row["effective_lineages"]) for row in recent)
            >= thresholds.minimum_effective_lineages
            and max(float(row["largest_lineage_fraction"]) for row in recent)
            <= thresholds.maximum_largest_lineage_fraction
        )
        contributor_available = all(
            bool(row["contributor_metrics_available"]) for row in recent
        )
        contributor_supported = bool(
            contributor_available
            and all(all(row["contributor_checks"].values()) for row in recent)
        )
    else:
        alive_cv = None
        maximum_growth_fraction = None
        settled_population_supported = False
        settled_lineage_supported = False
        contributor_available = False
        contributor_supported = False
    turnover_supported = all(final["turnover_checks"].values())
    descendant_supported = bool(final["descendant_fraction_met"])
    source_ready = bool(
        recent
        and settled_population_supported
        and settled_lineage_supported
        and turnover_supported
        and descendant_supported
        and contributor_supported
    )
    rebound_fraction = float(
        (float(final["alive"]) - float(trough["alive"])) / max(float(trough["alive"]), 1.0)
    )
    if source_ready:
        classification = "settled-source-ready-for-future-independent-runs"
    elif collapse_before_turnover and rebound_fraction >= 0.10:
        classification = "post-bottleneck-rebound-insufficient-source-readiness"
    elif collapse_before_turnover:
        classification = "bottleneck-dominated"
    elif settled_population_supported and not turnover_supported:
        classification = "settled-demography-insufficient-turnover"
    else:
        classification = "selection-source-insufficient-observation"
    return {
        "schema": "post-bottleneck-demographic-regime-v1",
        "trough_tick": int(trough["tick"]),
        "trough_alive": int(trough["alive"]),
        "final_alive": int(final["alive"]),
        "post_trough_rebound_fraction": rebound_fraction,
        "settled_window_count_required": required,
        "settled_window_count_available": len(recent),
        "settled_window_start_tick": int(recent[0]["tick"]) if recent else None,
        "settled_alive_cv": alive_cv,
        "settled_maximum_abs_net_growth_fraction": maximum_growth_fraction,
        "settled_population_supported": settled_population_supported,
        "settled_lineage_supported": settled_lineage_supported,
        "turnover_supported": turnover_supported,
        "descendant_metric_available": bool(final["descendant_metric_available"]),
        "descendant_supported": descendant_supported,
        "contributor_metrics_available": contributor_available,
        "reproductive_contributor_supported": contributor_supported,
        "source_ready_for_future_independent_runs": source_ready,
        "candidate_future_burn_in_tick": (
            int(recent[0]["tick"]) if source_ready and recent else None
        ),
        "classification": classification,
        "interpretation_boundary": (
            "A source-ready classification only proposes a fixed burn-in rule for new "
            "independent runs. The pilot windows used to derive it cannot be reused as "
            "confirmatory selection evidence."
        ),
    }


def audit_progress_records(
    label: str,
    rows: Sequence[dict[str, Any]],
    *,
    initial_population: int,
    thresholds: SelectionValidityThresholds,
    run_dir: str | None = None,
    summary_tick: int | None = None,
    reporting_state_tick: int | None = None,
) -> dict[str, Any]:
    if not rows:
        raise ValueError("evolution progress is empty")
    if initial_population <= 0:
        raise ValueError("initial population must be positive")
    normalized = _normalize_rows(rows, initial_population)
    assessments = [_window_assessment(row, thresholds) for row in normalized]
    population_floor = thresholds.minimum_alive_fraction_to_initial
    first_below_population_floor = _first_tick(
        assessments,
        lambda row: row["alive_fraction_to_initial"] < population_floor,
    )
    first_turnover_supported = _first_tick(
        assessments,
        lambda row: all(row["turnover_checks"].values()),
    )
    collapse_before_turnover = bool(
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
    regime = _settled_regime(
        assessments,
        thresholds=thresholds,
        collapse_before_turnover=collapse_before_turnover,
    )
    if regime["source_ready_for_future_independent_runs"]:
        recommendation = "preregister-fixed-burn-in-on-new-independent-seeds"
    elif collapse_before_turnover:
        recommendation = "bottleneck-dominated-continue-demographic-source-audit"
    elif not supported_windows:
        recommendation = "selection-inference-insufficient-retain-run"
    else:
        recommendation = "selection-supported-windows-present-require-seed-replication"
    return {
        "label": label,
        "run_dir": run_dir,
        "summary_tick": int(summary_tick if summary_tick is not None else final["tick"]),
        "reporting_state_tick": int(
            reporting_state_tick if reporting_state_tick is not None else final["tick"]
        ),
        "initial_population": initial_population,
        "window_count": len(assessments),
        "minimum_alive_fraction_to_initial": minimum_alive_fraction,
        "first_tick_below_population_floor": first_below_population_floor,
        "first_tick_with_turnover_support": first_turnover_supported,
        "population_collapse_before_turnover": collapse_before_turnover,
        "demographic_supported_window_count": len(demographic_windows),
        "evolutionary_supported_window_count": len(supported_windows),
        "final_population": final,
        "death_causes": _death_cause_summary(normalized),
        "post_bottleneck_regime": regime,
        "windows": assessments,
        "selection_inference_supported_within_run": bool(supported_windows),
        "recommendation": recommendation,
        "interpretation_boundary": (
            "This is a within-run adequacy audit. Windows are repeated observations, "
            "not independent replicates. Failed windows remain in the record. A future "
            "burn-in candidate is a design output, not evidence from the current run."
        ),
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
    summary = _read_json(summary_path)
    plan = _read_json(plan_path) if plan_path.is_file() else None
    resolved_config_path = run_dir / "resolved_config.json"
    resolved_config = _read_json(resolved_config_path) if resolved_config_path.is_file() else None
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
                "v0.67+ evolution progress fields"
            )
    return audit_progress_records(
        label,
        rows,
        initial_population=initial_population,
        thresholds=thresholds,
        run_dir=str(run_dir),
        summary_tick=int(summary.get("tick", 0)),
        reporting_state_tick=int(
            summary.get("reporting_state_tick", summary.get("tick", 0))
        ),
    )


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
    source_ready = [
        row
        for row in rows
        if row["post_bottleneck_regime"]["source_ready_for_future_independent_runs"]
    ]
    source_rule_supported = bool(
        len(rows) >= thresholds.minimum_source_ready_seed_count
        and len(source_ready) == len(rows)
    )
    fixed_burn_in = (
        max(
            int(row["post_bottleneck_regime"]["candidate_future_burn_in_tick"])
            for row in source_ready
        )
        if source_rule_supported
        else None
    )
    if source_rule_supported:
        recommendation = "preregister-fixed-burn-in-and-test-new-independent-seeds"
    elif bottlenecked:
        recommendation = "bottleneck-dominated-extend-observation-before-selection-claims"
    elif supported:
        recommendation = "collect-independent-seed-replication"
    else:
        recommendation = "retain-runs-and-redesign-source-before-selection-claims"
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
            "source_rule_applies_only_to_future_independent_runs": True,
            "pilot_runs_reused_as_confirmatory_effect_evidence": False,
        },
        "runs": rows,
        "run_count": len(rows),
        "bottleneck_dominated_run_count": len(bottlenecked),
        "within_run_selection_supported_count": len(supported),
        "post_bottleneck_source_ready_run_count": len(source_ready),
        "future_fixed_burn_in_rule_supported": source_rule_supported,
        "future_fixed_burn_in_tick": fixed_burn_in,
        "cross_seed_selection_inference_supported": False,
        "recommendation": recommendation,
        "interpretation_boundary": (
            "No cross-seed selection effect is estimated here. The audit separates "
            "population support, descendant turnover, and reproductive-contributor "
            "breadth from mere tick duration. Any burn-in rule derived from these pilots "
            "must be tested on new independent seeds."
        ),
    }


def render_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# Demographic selection validity audit",
        "",
        f"Schema: `{payload['schema']}`",
        "",
        "| Run | Initial | Min alive fraction | Trough tick | Final alive | Mean gen | Descendant fraction | Effective parents | Source ready | Classification |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---|",
    ]
    for row in payload["runs"]:
        final = row["final_population"]
        regime = row["post_bottleneck_regime"]
        lines.append(
            f"| {row['label']} | {row['initial_population']} | "
            f"{row['minimum_alive_fraction_to_initial']:.6f} | "
            f"{regime['trough_tick']} | {regime['final_alive']} | "
            f"{final['mean_generation']:.6f} | "
            f"{final['descendant_alive_fraction']} | "
            f"{final['effective_successful_parents_window']} | "
            f"{regime['source_ready_for_future_independent_runs']} | "
            f"{regime['classification']} |"
        )
    lines += [
        "",
        f"Future fixed burn-in supported: `{payload['future_fixed_burn_in_rule_supported']}`",
        f"Future fixed burn-in tick: `{payload['future_fixed_burn_in_tick']}`",
        f"Recommendation: `{payload['recommendation']}`",
        "",
        payload["interpretation_boundary"],
        "",
        "A rapid initial collapse is not automatically equivalent to effective selection. "
        "A later rebound can only become a candidate source regime after population "
        "stability, descendant replacement, lineage breadth, and independent reproductive "
        "contributor breadth are all observed.",
        "",
    ]
    return "\n".join(lines)


def _thresholds_from_args(args: argparse.Namespace) -> SelectionValidityThresholds:
    return SelectionValidityThresholds(
        minimum_alive_fraction_to_initial=args.minimum_alive_fraction,
        minimum_effective_lineages=args.minimum_effective_lineages,
        maximum_largest_lineage_fraction=args.maximum_largest_lineage_fraction,
        minimum_successful_parent_samples_per_window=args.minimum_parent_samples,
        minimum_mean_generation=args.minimum_mean_generation,
        minimum_max_generation=args.minimum_max_generation,
        minimum_cumulative_births_per_initial=args.minimum_births_per_initial,
        settled_window_count=args.settled_window_count,
        minimum_settled_alive=args.minimum_settled_alive,
        maximum_settled_alive_cv=args.maximum_settled_alive_cv,
        maximum_settled_net_growth_fraction=args.maximum_settled_net_growth_fraction,
        minimum_descendant_alive_fraction=args.minimum_descendant_fraction,
        minimum_unique_successful_parents_per_window=args.minimum_unique_parents,
        minimum_effective_successful_parents_per_window=args.minimum_effective_parents,
        maximum_largest_parent_contribution_fraction=args.maximum_parent_fraction,
        minimum_source_ready_seed_count=args.minimum_source_ready_seeds,
    )


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
    parser.add_argument("--settled-window-count", type=int, default=3)
    parser.add_argument("--minimum-settled-alive", type=int, default=1000)
    parser.add_argument("--maximum-settled-alive-cv", type=float, default=0.15)
    parser.add_argument("--maximum-settled-net-growth-fraction", type=float, default=0.15)
    parser.add_argument("--minimum-descendant-fraction", type=float, default=0.75)
    parser.add_argument("--minimum-unique-parents", type=int, default=100)
    parser.add_argument("--minimum-effective-parents", type=float, default=80.0)
    parser.add_argument("--maximum-parent-fraction", type=float, default=0.05)
    parser.add_argument("--minimum-source-ready-seeds", type=int, default=3)
    args = parser.parse_args(argv)
    payload = build_audit(
        (parse_run_spec(value) for value in args.run),
        thresholds=_thresholds_from_args(args),
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
