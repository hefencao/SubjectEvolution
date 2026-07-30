"""Audit whether run outputs are suitable for paired exploration or confirmation.

The audit separates three evidence questions that were previously conflated:

* whether one fixed checkpoint has enough living, diverse state for a short
  paired intervention panel;
* whether a free-running trajectory has completed enough demographic turnover
  for long-horizon selection interpretation;
* whether enough independent seeds exist for confirmation.

Repeated windows, entities, births, and actions remain nested observations.
The audit never changes simulation state or selects a favourable checkpoint.
"""
from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
import json
import math
from pathlib import Path
from statistics import fmean, pstdev
from typing import Any, Sequence

SCHEMA = "exploration-readiness-audit-v2"
PLAN_SCHEMA = "tiered-paired-exploration-protocol-v2"


@dataclass(frozen=True)
class ExplorationReadinessThresholds:
    minimum_independent_seeds_for_confirmation: int = 8
    minimum_acute_alive_absolute: int = 64
    minimum_acute_alive_fraction_to_initial: float = 0.08
    minimum_acute_effective_lineages_absolute: float = 32.0
    minimum_acute_effective_lineages_fraction_to_initial: float = 0.04
    maximum_acute_largest_lineage_fraction: float = 0.25
    minimum_strategy_effective_dimensions: float = 4.0
    minimum_descendant_alive_fraction_for_long_horizon: float = 0.75
    minimum_effective_successful_parents_for_long_horizon: float = 80.0
    maximum_largest_parent_contribution_fraction: float = 0.05
    startup_transient_maximum_alive_fraction: float = 0.25
    startup_transient_maximum_cross_seed_alive_cv: float = 0.15
    startup_transient_minimum_energy_death_fraction: float = 0.90

    def validate(self) -> None:
        if self.minimum_independent_seeds_for_confirmation < 3:
            raise ValueError("confirmation requires at least three independent seeds")
        if self.minimum_acute_alive_absolute < 1:
            raise ValueError("minimum acute alive must be positive")
        if not 0.0 < self.minimum_acute_alive_fraction_to_initial <= 1.0:
            raise ValueError("minimum acute alive fraction must be in (0, 1]")
        if self.minimum_acute_effective_lineages_absolute < 1.0:
            raise ValueError("minimum acute effective lineages must be at least one")
        if not 0.0 < self.minimum_acute_effective_lineages_fraction_to_initial <= 1.0:
            raise ValueError("minimum acute lineage fraction must be in (0, 1]")
        if not 0.0 < self.maximum_acute_largest_lineage_fraction <= 1.0:
            raise ValueError("largest lineage threshold must be in (0, 1]")
        if self.minimum_strategy_effective_dimensions < 1.0:
            raise ValueError("strategy dimension threshold must be at least one")
        if not 0.0 <= self.minimum_descendant_alive_fraction_for_long_horizon <= 1.0:
            raise ValueError("descendant fraction must be in [0, 1]")
        if self.minimum_effective_successful_parents_for_long_horizon < 1.0:
            raise ValueError("effective parent threshold must be at least one")
        if not 0.0 < self.maximum_largest_parent_contribution_fraction <= 1.0:
            raise ValueError("largest parent contribution threshold must be in (0, 1]")


def _read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"expected an object in {path}")
    return payload


def _float_or_none(value: Any) -> float | None:
    return None if value is None else float(value)


def _run_assessment(
    run: dict[str, Any], thresholds: ExplorationReadinessThresholds
) -> dict[str, Any]:
    final = run.get("final_population") or {}
    regime = run.get("post_bottleneck_regime") or {}
    death_causes = run.get("death_causes") or {}
    initial_population = int(run.get("initial_population", 0))
    alive = int(final.get("alive", 0))
    alive_fraction = (
        float(final.get("alive_fraction_to_initial"))
        if final.get("alive_fraction_to_initial") is not None
        else (float(alive) / float(initial_population) if initial_population else None)
    )
    effective_lineages = float(final.get("effective_lineages", 0.0))
    largest_lineage = float(final.get("largest_lineage_fraction", 1.0))
    strategy_dimensions = _float_or_none(final.get("strategy_effective_dimensions"))
    descendant = _float_or_none(final.get("descendant_alive_fraction"))
    effective_parents = _float_or_none(
        final.get("effective_successful_parents_window")
    )
    largest_parent = _float_or_none(
        final.get("largest_parent_contribution_fraction_window")
    )

    required_alive = max(
        int(thresholds.minimum_acute_alive_absolute),
        int(math.ceil(initial_population * thresholds.minimum_acute_alive_fraction_to_initial)),
    )
    required_lineages = max(
        float(thresholds.minimum_acute_effective_lineages_absolute),
        float(initial_population)
        * thresholds.minimum_acute_effective_lineages_fraction_to_initial,
    )
    acute_checks = {
        "alive_support": alive >= required_alive,
        "effective_lineage_support": effective_lineages >= required_lineages,
        "largest_lineage_support": (
            largest_lineage <= thresholds.maximum_acute_largest_lineage_fraction
        ),
        "current_strategy_variation_support": bool(
            strategy_dimensions is not None
            and strategy_dimensions >= thresholds.minimum_strategy_effective_dimensions
        ),
    }
    acute_source_support = all(acute_checks.values())

    long_horizon_checks = {
        "descendant_turnover_support": bool(
            descendant is not None
            and descendant
            >= thresholds.minimum_descendant_alive_fraction_for_long_horizon
        ),
        "reproductive_contributor_support": bool(
            effective_parents is not None
            and effective_parents
            >= thresholds.minimum_effective_successful_parents_for_long_horizon
            and largest_parent is not None
            and largest_parent
            <= thresholds.maximum_largest_parent_contribution_fraction
        ),
        "settled_population_support": bool(
            regime.get("settled_population_supported", False)
        ),
    }
    long_horizon_support = acute_source_support and all(long_horizon_checks.values())
    source_ready = bool(regime.get("source_ready_for_future_independent_runs", False))
    energy_death_fraction = _float_or_none(death_causes.get("energy_depleted_fraction"))
    return {
        "label": str(run.get("label", "run")),
        "summary_tick": int(run.get("summary_tick", final.get("tick", 0))),
        "initial_population": initial_population,
        "final_alive": alive,
        "alive_fraction_to_initial": alive_fraction,
        "required_acute_alive": required_alive,
        "effective_founder_lineages": effective_lineages,
        "required_acute_effective_lineages": required_lineages,
        "largest_lineage_fraction": largest_lineage,
        "strategy_effective_dimensions": strategy_dimensions,
        "acute_paired_source_support": acute_source_support,
        "acute_paired_source_checks": acute_checks,
        "descendant_alive_fraction": descendant,
        "effective_successful_parents": effective_parents,
        "largest_parent_contribution_fraction": largest_parent,
        "long_horizon_selection_support": long_horizon_support,
        "long_horizon_checks": long_horizon_checks,
        "future_source_ready": source_ready,
        "classification": regime.get("classification"),
        "energy_depleted_death_fraction": energy_death_fraction,
    }


def _startup_transient_diagnosis(
    assessed: list[dict[str, Any]], thresholds: ExplorationReadinessThresholds
) -> dict[str, Any]:
    fractions = [
        float(run["alive_fraction_to_initial"])
        for run in assessed
        if run["alive_fraction_to_initial"] is not None
    ]
    energy_fractions = [
        float(run["energy_depleted_death_fraction"])
        for run in assessed
        if run["energy_depleted_death_fraction"] is not None
    ]
    classifications = [str(run.get("classification") or "") for run in assessed]
    mean_fraction = fmean(fractions) if fractions else None
    cv = (
        pstdev(fractions) / abs(mean_fraction)
        if fractions and mean_fraction not in (None, 0.0)
        else None
    )
    common_decline = bool(
        classifications
        and all(value == "post-bottleneck-active-decline" for value in classifications)
    )
    low_common_endpoint = bool(
        mean_fraction is not None
        and mean_fraction <= thresholds.startup_transient_maximum_alive_fraction
        and cv is not None
        and cv <= thresholds.startup_transient_maximum_cross_seed_alive_cv
    )
    energy_dominated = bool(
        energy_fractions
        and len(energy_fractions) == len(assessed)
        and min(energy_fractions)
        >= thresholds.startup_transient_minimum_energy_death_fraction
    )
    return {
        "common_active_decline": common_decline,
        "mean_final_alive_fraction": mean_fraction,
        "cross_seed_final_alive_fraction_cv": cv,
        "energy_depletion_death_dominant": energy_dominated,
        "common_startup_transient_supported": bool(
            common_decline and low_common_endpoint and energy_dominated
        ),
        "interpretation": (
            "A repeatable startup collapse can be a shared source trajectory for a "
            "predeclared paired acute panel, but free-running endpoints from that "
            "transient are not candidate-effect measurements."
        ),
    }


def build_audit(
    selection_audit: dict[str, Any],
    *,
    thresholds: ExplorationReadinessThresholds | None = None,
    long_run_analysis: dict[str, Any] | None = None,
) -> dict[str, Any]:
    thresholds = thresholds or ExplorationReadinessThresholds()
    thresholds.validate()
    runs = selection_audit.get("runs")
    if not isinstance(runs, list) or not runs:
        raise ValueError("selection audit must contain at least one run")
    assessed = [_run_assessment(run, thresholds) for run in runs]
    run_count = len(assessed)
    acute_count = sum(bool(run["acute_paired_source_support"]) for run in assessed)
    long_count = sum(bool(run["long_horizon_selection_support"]) for run in assessed)
    source_count = sum(bool(run["future_source_ready"]) for run in assessed)
    independent_confirmation = (
        run_count >= thresholds.minimum_independent_seeds_for_confirmation
    )
    startup = _startup_transient_diagnosis(assessed, thresholds)
    all_acute = acute_count == run_count

    sample_diagnosis = {
        "independent_unit": "run-seed",
        "event_or_window_pseudoreplication_allowed": False,
        "independent_seed_count": run_count,
        "independent_seed_count_meets_confirmation_floor": independent_confirmation,
        "acute_paired_source_support_count": acute_count,
        "all_runs_support_fixed_checkpoint_paired_panel": all_acute,
        "long_horizon_selection_support_count": long_count,
        "future_source_ready_count": source_count,
        "free_run_endpoint_is_candidate_effect_measurement": False,
        "startup_transient": startup,
        "sample_issue": bool(not independent_confirmation or not all_acute),
        "sample_issue_reasons": [
            reason
            for condition, reason in (
                (
                    not independent_confirmation,
                    "independent-seed count is below the confirmation threshold",
                ),
                (
                    not all_acute,
                    "not every fixed checkpoint has enough acute paired-panel support",
                ),
            )
            if condition
        ],
    }

    protocol = {
        "schema": PLAN_SCHEMA,
        "independent_unit": "seed",
        "windows_entities_and_events_are_nested_observations": True,
        "large_long_run_required_for_exploration": False,
        "large_long_run_reserved_for_confirmation": True,
        "free_run_screen_endpoint_allowed_as_candidate_effect": False,
        "screen_requires_shared_checkpoint_matched_branches": True,
        "source_checkpoint_requirements_are_scale_normalized": True,
        "stages": {
            "smoke": {
                "purpose": "mechanism, schema, ledger, checkpoint, and parity validation",
                "minimum_seeds": 2,
                "selection_claim_allowed": False,
            },
            "screen": {
                "purpose": "paired acute effect screening from fixed checkpoints",
                "minimum_seeds": 8,
                "selection_claim_allowed": False,
            },
            "replication": {
                "purpose": "repeat a promoted paired screen on disjoint seeds",
                "minimum_seeds": 8,
                "selection_claim_allowed": False,
            },
            "confirmation": {
                "purpose": "confirm only candidates that pass screen and replication",
                "minimum_seeds": thresholds.minimum_independent_seeds_for_confirmation,
                "requires_disjoint_prior_stage_seeds": True,
                "requires_explicit_large_long_authorization": True,
                "selection_claim_allowed": True,
            },
        },
        "failed_runs_replaced": False,
        "promotion_based_on_same_seed_reuse": False,
        "feedback_to_world": False,
    }

    if all_acute and startup["common_startup_transient_supported"]:
        recommendation = (
            "reuse-fixed-checkpoints-for-paired-acute-screen-do-not-promote-free-run-endpoints"
        )
    elif all_acute and independent_confirmation:
        recommendation = "fixed-checkpoint-paired-screen-ready"
    elif all_acute:
        recommendation = "add-independent-seeds-before-paired-screen"
    else:
        recommendation = "repair-fixed-checkpoint-acute-support"

    return {
        "schema": SCHEMA,
        "thresholds": asdict(thresholds),
        "selection_audit_schema": selection_audit.get("schema"),
        "long_run_analysis_schema": (
            long_run_analysis.get("schema") if long_run_analysis else None
        ),
        "run_count": run_count,
        "runs": assessed,
        "sample_diagnosis": sample_diagnosis,
        "exploration_protocol": protocol,
        "recommendation": recommendation,
        "interpretation_boundary": (
            "A fixed checkpoint may support a short paired mechanism panel even when the "
            "free-running trajectory has not completed demographic turnover. The paired seed "
            "is the independent unit. Free-running endpoints, repeated windows, entities, "
            "births, and moves do not become candidate-effect replicates."
        ),
    }


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Exploration readiness and sample adequacy",
        "",
        f"Schema: `{report['schema']}`",
        "",
        "| Run | Initial | Final alive | Alive fraction | Effective lineages | Strategy dimensions | Paired source support | Long-horizon support |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for run in report["runs"]:
        lines.append(
            "| {label} | {initial} | {alive} | {fraction} | {lineages} | {dims} | {paired} | {long} |".format(
                label=run["label"],
                initial=run["initial_population"],
                alive=run["final_alive"],
                fraction=run["alive_fraction_to_initial"],
                lineages=run["effective_founder_lineages"],
                dims=run["strategy_effective_dimensions"],
                paired=run["acute_paired_source_support"],
                long=run["long_horizon_selection_support"],
            )
        )
    diagnosis = report["sample_diagnosis"]
    startup = diagnosis["startup_transient"]
    lines.extend(
        [
            "",
            "## Diagnosis",
            "",
            f"- independent seed count: `{diagnosis['independent_seed_count']}`",
            f"- acute paired source checkpoints: `{diagnosis['acute_paired_source_support_count']}`",
            f"- long-horizon supported runs: `{diagnosis['long_horizon_selection_support_count']}`",
            f"- common startup transient: `{startup['common_startup_transient_supported']}`",
            f"- free-run endpoint is a candidate-effect measurement: `{diagnosis['free_run_endpoint_is_candidate_effect_measurement']}`",
            "",
            "## Exploration policy",
            "",
            "- source checkpoint tick is fixed before branch outcomes are observed",
            "- baseline and intervention start from the same full checkpoint",
            "- screen and replication use disjoint independent seeds",
            "- demographic turnover is not required for an acute paired mechanism screen",
            "- large long runs remain confirmation-only",
            "",
            f"Recommendation: `{report['recommendation']}`",
            "",
            report["interpretation_boundary"],
            "",
        ]
    )
    return "\n".join(lines)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Audit fixed-checkpoint paired-panel and confirmation readiness."
    )
    parser.add_argument("--selection-audit", required=True)
    parser.add_argument("--long-run-analysis")
    parser.add_argument("--output", required=True)
    args = parser.parse_args(argv)
    selection = _read_json(Path(args.selection_audit))
    long_run = _read_json(Path(args.long_run_analysis)) if args.long_run_analysis else None
    report = build_audit(selection, long_run_analysis=long_run)
    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=True)
    (output / "exploration_readiness_audit.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    (output / "exploration_readiness_audit.md").write_text(
        render_markdown(report), encoding="utf-8"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
