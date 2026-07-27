"""Qualification of D2-G source-population burn-in results.

D2-G is an exploratory source-population redesign gate.  The project charter's
10-seed language applies to *major conclusions*, not to every exploratory audit.
This module therefore separates three questions that were previously conflated:

* did a phase produce enough guarded panels to justify the next paired causal
  experiment?;
* is the evidence precise enough for a general source-population conclusion?;
* is module copy number ready to change?

Three fresh-world seeds can answer the first question when the design is paired,
the hard guards are preregistered, and at least two seeds agree.  They cannot
answer the second question with high confidence, and never answer the third.
"""

from __future__ import annotations

import argparse
from collections import defaultdict
import json
import math
from pathlib import Path
from typing import Any

from se.experiments.d2_source_population import RESULT_SCHEMA

ASSESSMENT_SCHEMA = "d2-source-population-assessment-v2"
SUPPORTED_ASSESSMENT_SCHEMAS = frozenset(
    {"d2-source-population-assessment-v1", ASSESSMENT_SCHEMA}
)
EFFECTIVE_LINEAGE_THRESHOLD = 4.0
MAX_DOMINANT_LINEAGE_FRACTION = 0.5
MIN_QUALIFIED_PANEL_SEEDS_PER_PHASE = 2
MIN_PANEL_SEEDS_FOR_EXPLORATORY_DECISION = 3
MIN_PHASES_FOR_GENERAL_SOURCE_POPULATION = 2
CHARTER_MAJOR_CONCLUSION_MIN_SEEDS = 10
WILSON_Z_95 = 1.959963984540054


def _final_snapshot(arm: dict[str, Any], final_offset: int) -> dict[str, Any]:
    rows = [
        row
        for row in arm.get("trajectory", ())
        if int(row.get("offset_ticks", -1)) == int(final_offset)
    ]
    if len(rows) != 1:
        raise ValueError("each source-population arm must have one final snapshot")
    return rows[0]


def _wilson_interval(successes: int, trials: int, *, z: float = WILSON_Z_95) -> tuple[float, float]:
    """Two-sided Wilson score interval for a binomial proportion."""

    if trials <= 0:
        return 0.0, 1.0
    p = float(successes) / float(trials)
    z2 = z * z
    denominator = 1.0 + z2 / trials
    center = (p + z2 / (2.0 * trials)) / denominator
    radius = (
        z
        * math.sqrt((p * (1.0 - p) + z2 / (4.0 * trials)) / trials)
        / denominator
    )
    return max(0.0, center - radius), min(1.0, center + radius)


def assess_source_population_results(results: dict[str, Any]) -> dict[str, Any]:
    if results.get("schema") != RESULT_SCHEMA:
        raise ValueError(
            f"unsupported source-population results: {results.get('schema')!r}"
        )
    plan = results.get("plan", {})
    final_offset = int(plan["burn_in_ticks"])
    candidate_modules = tuple(int(value) for value in plan["candidate_module_indices"])
    min_members = int(plan["min_lineage_members"])
    rows: list[dict[str, Any]] = []
    qualified_by_phase: dict[str, set[int]] = defaultdict(set)
    natural_by_phase: dict[str, set[int]] = defaultdict(set)
    observed_by_phase: dict[str, set[int]] = defaultdict(set)

    for panel in results.get("panels", ()):
        phase = str(panel["phase"])
        seed = int(panel["panel_seed"])
        observed_by_phase[phase].add(seed)
        arms: dict[str, Any] = {}
        for arm_name, arm in panel["arms"].items():
            final = _final_snapshot(arm, final_offset)
            expression_counts = {
                f"module_{module}": int(
                    final.get("candidate_module_expression", {})
                    .get(f"module_{module}", {})
                    .get("expressed_eligible_lineage_count", 0)
                )
                for module in candidate_modules
            }
            pass_effective = (
                float(final["effective_lineages"]) >= EFFECTIVE_LINEAGE_THRESHOLD
            )
            pass_dominant = (
                float(final["dominant_lineage_fraction"])
                <= MAX_DOMINANT_LINEAGE_FRACTION
            )
            pass_members = int(final["eligible_panel_lineage_count"]) >= 4
            pass_expression = all(value >= 4 for value in expression_counts.values())
            qualified = bool(
                pass_effective and pass_dominant and pass_members and pass_expression
            )
            if arm_name == "equal-lineage-reconstitution" and qualified:
                qualified_by_phase[phase].add(seed)
            if arm_name == "natural-abundance-control" and qualified:
                natural_by_phase[phase].add(seed)
            arms[arm_name] = {
                "final_snapshot": final,
                "module_expressed_eligible_lineage_counts": expression_counts,
                "passes_effective_lineage_guard": pass_effective,
                "passes_dominant_share_guard": pass_dominant,
                "passes_member_floor": pass_members,
                "passes_module_expression_floor": pass_expression,
                "qualified": qualified,
            }
        rows.append(
            {
                "panel_name": str(panel["panel_name"]),
                "phase": phase,
                "panel_seed": seed,
                "arms": arms,
            }
        )

    phase_rows: dict[str, Any] = {}
    phases = sorted(
        set(qualified_by_phase)
        | set(natural_by_phase)
        | set(observed_by_phase)
        | set(plan["phases"])
    )
    for phase in phases:
        observed_seeds = sorted(observed_by_phase.get(phase, set()))
        equal_seeds = sorted(qualified_by_phase.get(phase, set()))
        natural_seeds = sorted(natural_by_phase.get(phase, set()))
        observed_count = len(observed_seeds)
        equal_count = len(equal_seeds)
        natural_count = len(natural_seeds)
        equal_interval = _wilson_interval(equal_count, observed_count)
        natural_interval = _wilson_interval(natural_count, observed_count)
        exploratory_ready = bool(
            observed_count >= MIN_PANEL_SEEDS_FOR_EXPLORATORY_DECISION
            and equal_count >= MIN_QUALIFIED_PANEL_SEEDS_PER_PHASE
        )
        phase_rows[phase] = {
            "observed_panel_seeds": observed_seeds,
            "observed_panel_seed_count": observed_count,
            "equal_lineage_qualified_seeds": equal_seeds,
            "natural_abundance_qualified_seeds": natural_seeds,
            "equal_lineage_seed_count": equal_count,
            "natural_abundance_seed_count": natural_count,
            "equal_lineage_pass_fraction": (
                float(equal_count) / observed_count if observed_count else 0.0
            ),
            "natural_abundance_pass_fraction": (
                float(natural_count) / observed_count if observed_count else 0.0
            ),
            "equal_lineage_wilson_95_interval": list(equal_interval),
            "natural_abundance_wilson_95_interval": list(natural_interval),
            "paired_equalization_advantage_seed_count": len(
                set(equal_seeds) - set(natural_seeds)
            ),
            "exploratory_phase_ready": exploratory_ready,
            "major_conclusion_seed_floor_met": (
                observed_count >= CHARTER_MAJOR_CONCLUSION_MIN_SEEDS
            ),
        }

    exploratory_phases = sorted(
        phase
        for phase, row in phase_rows.items()
        if row["exploratory_phase_ready"]
    )
    all_phases_exploratory = bool(
        len(exploratory_phases) >= MIN_PHASES_FOR_GENERAL_SOURCE_POPULATION
    )
    major_conclusion_seed_floor_met = bool(
        phases
        and all(
            row["major_conclusion_seed_floor_met"]
            for row in phase_rows.values()
        )
    )

    # A general source-population conclusion is deliberately withheld at n=3.
    # This does not block a phase-specific exploratory paired causal re-audit.
    # This assessor is an exploratory gate.  Meeting a seed-count floor alone is
    # not a preregistered major-conclusion test, so it never certifies a general
    # source population.
    source_population_ready = False
    exploratory_causal_reaudit_ready = bool(exploratory_phases)

    if exploratory_causal_reaudit_ready:
        recommendation = (
            "freeze-qualified-phase-checkpoints-for-exploratory-module-3-reaudit"
        )
    else:
        recommendation = "source-population-redesign-insufficient-for-causal-reaudit"

    return {
        "schema": ASSESSMENT_SCHEMA,
        "result_schema": results.get("schema"),
        "burn_in_ticks": final_offset,
        "candidate_module_indices": list(candidate_modules),
        "evidence_scope": "exploratory-stage-gate",
        "charter_interpretation": {
            "major_conclusions_require_at_least_ten_seeds": True,
            "every_exploratory_audit_requires_ten_seeds": False,
            "three_seed_paired_audit_can_gate_next_experiment": True,
            "generalization_claim_allowed_at_current_sample_size": False,
        },
        "qualification_rule": {
            "minimum_effective_lineages": EFFECTIVE_LINEAGE_THRESHOLD,
            "maximum_dominant_lineage_fraction": MAX_DOMINANT_LINEAGE_FRACTION,
            "minimum_lineages_above_member_floor": 4,
            "lineage_member_floor": min_members,
            "minimum_expressed_lineages_per_candidate_module": 4,
            "minimum_observed_panel_seeds_for_exploratory_decision": (
                MIN_PANEL_SEEDS_FOR_EXPLORATORY_DECISION
            ),
            "minimum_qualified_panel_seeds_per_exploratory_phase": (
                MIN_QUALIFIED_PANEL_SEEDS_PER_PHASE
            ),
            "minimum_phases_for_general_source_population": (
                MIN_PHASES_FOR_GENERAL_SOURCE_POPULATION
            ),
            "major_conclusion_minimum_seeds_per_phase": (
                CHARTER_MAJOR_CONCLUSION_MIN_SEEDS
            ),
            "uncertainty_interval": "two-sided-wilson-95-v1",
            "equalization_at_tick_zero_is_not_evidence": True,
            "ongoing_lineage_protection_allowed": False,
        },
        "panels": rows,
        "phases": phase_rows,
        "qualified_phases": exploratory_phases,
        "exploratory_qualified_phases": exploratory_phases,
        "exploratory_causal_reaudit_ready": exploratory_causal_reaudit_ready,
        "all_phases_exploratory_ready": all_phases_exploratory,
        "major_conclusion_seed_floor_met": major_conclusion_seed_floor_met,
        "major_conclusion_evaluated": False,
        "source_population_ready": source_population_ready,
        "module_copy_number_ready": False,
        "recommendation": recommendation,
        "interpretation_boundary": (
            "D2-G asks whether a genotype-only founder redesign can produce guarded "
            "multi-lineage checkpoints worth another causal experiment. Three paired "
            "fresh-world seeds can support that exploratory gate when at least two agree, "
            "but the wide binomial interval is retained and no general source-population "
            "claim is made. Only phase-qualified equal-lineage checkpoints may enter the "
            "next shared-checkpoint module-3 re-audit. Module copy number remains blocked."
        ),
    }


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# D2-G source-population exploratory qualification",
        "",
        f"Schema: `{report['schema']}`",
        f"Burn-in: `{report['burn_in_ticks']}` ticks",
        f"Evidence scope: `{report['evidence_scope']}`",
        "",
        "| Phase | Equal qualified | Natural qualified | Equal 95% Wilson | Exploratory ready | 10-seed major floor |",
        "|---|---:|---:|---|---:|---:|",
    ]
    for phase, row in report["phases"].items():
        interval = row["equal_lineage_wilson_95_interval"]
        lines.append(
            f"| {phase} | {row['equal_lineage_seed_count']}/{row['observed_panel_seed_count']} | "
            f"{row['natural_abundance_seed_count']}/{row['observed_panel_seed_count']} | "
            f"[{interval[0]:.3f}, {interval[1]:.3f}] | "
            f"{row['exploratory_phase_ready']} | {row['major_conclusion_seed_floor_met']} |"
        )
    lines.extend(
        [
            "",
            f"Exploratory qualified phases: `{', '.join(report['exploratory_qualified_phases']) or 'none'}`",
            f"Exploratory causal re-audit ready: `{report['exploratory_causal_reaudit_ready']}`",
            f"General source population ready: `{report['source_population_ready']}`",
            f"Module copy number ready: `{report['module_copy_number_ready']}`",
            "",
            "## Charter interpretation",
            "",
            "The charter's ten-seed floor applies to major conclusions. It is not a mandatory "
            "minimum for every exploratory audit. The present three-seed result may route a "
            "phase-specific next experiment, but may not be presented as a general source-"
            "population conclusion.",
            "",
            "## Recommendation",
            "",
            f"`{report['recommendation']}`",
            "",
            report["interpretation_boundary"],
            "",
        ]
    )
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Assess D2-G source-population exploratory qualification"
    )
    parser.add_argument("--results", required=True)
    parser.add_argument("--output", required=True)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    results = json.loads(Path(args.results).read_text(encoding="utf-8"))
    report = assess_source_population_results(results)
    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=True)
    (output / "d2_source_population_assessment.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (output / "d2_source_population_assessment.md").write_text(
        render_markdown(report), encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "passed": True,
                "exploratory_causal_reaudit_ready": report[
                    "exploratory_causal_reaudit_ready"
                ],
                "source_population_ready": report["source_population_ready"],
                "recommendation": report["recommendation"],
            }
        )
    )


if __name__ == "__main__":
    main()
