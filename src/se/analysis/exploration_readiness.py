"""Audit whether existing runs are adequate for cheap exploration or confirmation.

The audit separates within-run observational support from independent-seed
replication and stable-source support.  It never changes simulation state and
never turns repeated windows, entities, or events into independent replicates.
"""
from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
import json
from pathlib import Path
from typing import Any, Sequence

SCHEMA = "exploration-readiness-audit-v1"
PLAN_SCHEMA = "tiered-exploration-protocol-v1"


@dataclass(frozen=True)
class ExplorationReadinessThresholds:
    minimum_independent_seeds_for_confirmation: int = 8
    minimum_final_alive: int = 1000
    minimum_descendant_alive_fraction: float = 0.75
    minimum_effective_successful_parents: float = 80.0
    maximum_largest_parent_contribution_fraction: float = 0.05
    minimum_strategy_effective_dimensions: float = 4.0
    minimum_effective_founder_lineages_for_source: float = 100.0

    def validate(self) -> None:
        if self.minimum_independent_seeds_for_confirmation < 3:
            raise ValueError("confirmation requires at least three independent seeds")
        if self.minimum_final_alive < 1:
            raise ValueError("minimum final alive must be positive")
        if not 0.0 <= self.minimum_descendant_alive_fraction <= 1.0:
            raise ValueError("descendant fraction must be in [0, 1]")
        if self.minimum_effective_successful_parents < 1.0:
            raise ValueError("effective parent threshold must be at least one")
        if not 0.0 < self.maximum_largest_parent_contribution_fraction <= 1.0:
            raise ValueError("largest parent contribution threshold must be in (0, 1]")
        if self.minimum_strategy_effective_dimensions < 1.0:
            raise ValueError("strategy dimension threshold must be at least one")
        if self.minimum_effective_founder_lineages_for_source < 1.0:
            raise ValueError("founder lineage threshold must be at least one")


def _read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"expected an object in {path}")
    return payload


def _run_assessment(
    run: dict[str, Any], thresholds: ExplorationReadinessThresholds
) -> dict[str, Any]:
    final = run.get("final_population") or {}
    regime = run.get("post_bottleneck_regime") or {}
    alive = int(final.get("alive", 0))
    descendant = final.get("descendant_alive_fraction")
    effective_parents = final.get("effective_successful_parents_window")
    largest_parent = final.get("largest_parent_contribution_fraction_window")
    strategy_dimensions = final.get("strategy_effective_dimensions")
    effective_lineages = float(final.get("effective_lineages", 0.0))
    checks = {
        "population_support": alive >= thresholds.minimum_final_alive,
        "descendant_turnover_support": bool(
            descendant is not None
            and float(descendant) >= thresholds.minimum_descendant_alive_fraction
        ),
        "reproductive_contributor_support": bool(
            effective_parents is not None
            and float(effective_parents)
            >= thresholds.minimum_effective_successful_parents
            and largest_parent is not None
            and float(largest_parent)
            <= thresholds.maximum_largest_parent_contribution_fraction
        ),
        "current_strategy_variation_support": bool(
            strategy_dimensions is not None
            and float(strategy_dimensions)
            >= thresholds.minimum_strategy_effective_dimensions
        ),
    }
    within_run = all(checks.values())
    founder_source = bool(
        effective_lineages >= thresholds.minimum_effective_founder_lineages_for_source
    )
    settled_population = bool(regime.get("settled_population_supported", False))
    source_ready = bool(regime.get("source_ready_for_future_independent_runs", False))
    return {
        "label": str(run.get("label", "run")),
        "summary_tick": int(run.get("summary_tick", final.get("tick", 0))),
        "final_alive": alive,
        "descendant_alive_fraction": (
            float(descendant) if descendant is not None else None
        ),
        "effective_successful_parents": (
            float(effective_parents) if effective_parents is not None else None
        ),
        "largest_parent_contribution_fraction": (
            float(largest_parent) if largest_parent is not None else None
        ),
        "effective_founder_lineages": effective_lineages,
        "strategy_effective_dimensions": (
            float(strategy_dimensions) if strategy_dimensions is not None else None
        ),
        "within_run_observational_support": within_run,
        "within_run_checks": checks,
        "founder_lineage_source_support": founder_source,
        "settled_population_support": settled_population,
        "future_source_ready": source_ready,
        "classification": regime.get("classification"),
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
    within_count = sum(bool(run["within_run_observational_support"]) for run in assessed)
    founder_count = sum(bool(run["founder_lineage_source_support"]) for run in assessed)
    settled_count = sum(bool(run["settled_population_support"]) for run in assessed)
    source_count = sum(bool(run["future_source_ready"]) for run in assessed)
    independent_confirmation = (
        run_count >= thresholds.minimum_independent_seeds_for_confirmation
    )
    within_run_support = within_count == run_count
    source_support = source_count == run_count
    sample_diagnosis = {
        "within_run_observational_support": within_run_support,
        "independent_seed_count": run_count,
        "independent_seed_confirmation_support": independent_confirmation,
        "founder_lineage_source_support_count": founder_count,
        "settled_population_support_count": settled_count,
        "future_source_ready_count": source_count,
        "event_or_window_pseudoreplication_allowed": False,
        "independent_unit": "run-seed",
        "sample_issue": bool(not independent_confirmation or not source_support),
        "sample_issue_reasons": [
            reason
            for condition, reason in (
                (
                    not independent_confirmation,
                    "independent-seed count is below the confirmation threshold",
                ),
                (
                    founder_count < run_count,
                    "founder-lineage breadth is insufficient for a stable source claim",
                ),
                (
                    settled_count < run_count,
                    "not every run demonstrates a settled population regime",
                ),
                (
                    source_count < run_count,
                    "no common future source rule is supported across runs",
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
        "stages": {
            "smoke": {
                "purpose": "mechanism, schema, ledger, and parity validation",
                "minimum_seeds": 2,
                "maximum_initial_entities": 512,
                "maximum_ticks": 180,
                "selection_claim_allowed": False,
            },
            "screen": {
                "purpose": "cheap directional screening across independent seeds",
                "minimum_seeds": 8,
                "maximum_initial_entities": 2048,
                "maximum_ticks": 600,
                "selection_claim_allowed": False,
            },
            "replication": {
                "purpose": "repeat a promoted screen on disjoint independent seeds",
                "minimum_seeds": 8,
                "maximum_initial_entities": 4096,
                "maximum_ticks": 900,
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
    if within_run_support and not independent_confirmation:
        recommendation = (
            "use-tiered-small-panel-exploration-add-independent-seeds-before-confirmation"
        )
    elif within_run_support and independent_confirmation and not source_support:
        recommendation = "use-tiered-small-panel-exploration-source-regime-unresolved"
    elif within_run_support and independent_confirmation and source_support:
        recommendation = "small-panel-exploration-ready-reserve-large-long-for-confirmation"
    else:
        recommendation = "repair-within-run-sample-support-before-effect-screening"
    result: dict[str, Any] = {
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
            "Large trajectories may establish demographic and runtime behavior, but repeated "
            "windows, entities, births, and moves are not independent confirmation samples. "
            "Exploration should use cheaper independent-seed panels; large long runs are "
            "reserved for promoted candidates on new seeds."
        ),
    }
    return result


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Exploration readiness and sample adequacy",
        "",
        f"Schema: `{report['schema']}`",
        "",
        "| Run | Final alive | Descendants | Effective parents | Founder lineages | Strategy dimensions | Within-run support | Source ready |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for run in report["runs"]:
        lines.append(
            "| {label} | {final_alive} | {descendant} | {parents} | {lineages} | {dims} | {within} | {source} |".format(
                label=run["label"],
                final_alive=run["final_alive"],
                descendant=run["descendant_alive_fraction"],
                parents=run["effective_successful_parents"],
                lineages=run["effective_founder_lineages"],
                dims=run["strategy_effective_dimensions"],
                within=run["within_run_observational_support"],
                source=run["future_source_ready"],
            )
        )
    diagnosis = report["sample_diagnosis"]
    lines.extend(
        [
            "",
            "## Diagnosis",
            "",
            f"- within-run observational support: `{diagnosis['within_run_observational_support']}`",
            f"- independent seed count: `{diagnosis['independent_seed_count']}`",
            f"- confirmation-level independent replication: `{diagnosis['independent_seed_confirmation_support']}`",
            f"- sample issue present: `{diagnosis['sample_issue']}`",
        ]
    )
    for reason in diagnosis["sample_issue_reasons"]:
        lines.append(f"- {reason}")
    lines.extend(
        [
            "",
            "## Exploration policy",
            "",
            "- smoke: 2 seeds, at most 512 initial entities and 180 ticks",
            "- screen: at least 8 seeds, at most 2048 initial entities and 600 ticks",
            "- replication: at least 8 disjoint seeds, at most 4096 initial entities and 900 ticks",
            "- large long runs: confirmation only, after screen and replication",
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
        description="Audit sample adequacy and choose a tiered exploration stage."
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
