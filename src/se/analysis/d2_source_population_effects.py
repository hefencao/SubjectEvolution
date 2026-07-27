"""Qualification of D2-G source-population burn-in results."""

from __future__ import annotations

import argparse
from collections import defaultdict
import json
from pathlib import Path
from typing import Any

from se.experiments.d2_source_population import RESULT_SCHEMA

ASSESSMENT_SCHEMA = "d2-source-population-assessment-v1"
EFFECTIVE_LINEAGE_THRESHOLD = 4.0
MAX_DOMINANT_LINEAGE_FRACTION = 0.5
MIN_QUALIFIED_PANEL_SEEDS_PER_PHASE = 2
MIN_QUALIFIED_PHASES = 2


def _final_snapshot(arm: dict[str, Any], final_offset: int) -> dict[str, Any]:
    rows = [
        row
        for row in arm.get("trajectory", ())
        if int(row.get("offset_ticks", -1)) == int(final_offset)
    ]
    if len(rows) != 1:
        raise ValueError("each source-population arm must have one final snapshot")
    return rows[0]


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
    for panel in results.get("panels", ()):
        phase = str(panel["phase"])
        seed = int(panel["panel_seed"])
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
    for phase in sorted(set(qualified_by_phase) | set(natural_by_phase) | set(plan["phases"])):
        equal_seeds = sorted(qualified_by_phase.get(phase, set()))
        natural_seeds = sorted(natural_by_phase.get(phase, set()))
        phase_rows[phase] = {
            "equal_lineage_qualified_seeds": equal_seeds,
            "natural_abundance_qualified_seeds": natural_seeds,
            "equal_lineage_seed_count": len(equal_seeds),
            "natural_abundance_seed_count": len(natural_seeds),
            "phase_qualified": len(equal_seeds) >= MIN_QUALIFIED_PANEL_SEEDS_PER_PHASE,
        }
    qualified_phases = sorted(
        phase for phase, row in phase_rows.items() if row["phase_qualified"]
    )
    ready = len(qualified_phases) >= MIN_QUALIFIED_PHASES
    if ready:
        recommendation = (
            "source-population-qualified-freeze-checkpoints-before-copy-number-audit"
        )
    elif qualified_phases:
        recommendation = (
            "source-population-partially-qualified-expand-independent-panels"
        )
    else:
        recommendation = "source-population-redesign-failed-do-not-test-copy-number"
    return {
        "schema": ASSESSMENT_SCHEMA,
        "result_schema": results.get("schema"),
        "burn_in_ticks": final_offset,
        "candidate_module_indices": list(candidate_modules),
        "qualification_rule": {
            "minimum_effective_lineages": EFFECTIVE_LINEAGE_THRESHOLD,
            "maximum_dominant_lineage_fraction": MAX_DOMINANT_LINEAGE_FRACTION,
            "minimum_lineages_above_member_floor": 4,
            "lineage_member_floor": min_members,
            "minimum_expressed_lineages_per_candidate_module": 4,
            "minimum_qualified_panel_seeds_per_phase": MIN_QUALIFIED_PANEL_SEEDS_PER_PHASE,
            "minimum_qualified_phases": MIN_QUALIFIED_PHASES,
            "equalization_at_tick_zero_is_not_evidence": True,
            "ongoing_lineage_protection_allowed": False,
        },
        "panels": rows,
        "phases": phase_rows,
        "qualified_phases": qualified_phases,
        "source_population_ready": ready,
        "module_copy_number_ready": False,
        "recommendation": recommendation,
        "interpretation_boundary": (
            "Qualification concerns only whether a fresh genotype-only founder panel "
            "retains at least four expressed lineages after unprotected burn-in. It does "
            "not establish that module 3 remains causal in the redesigned population and "
            "does not authorize module copy-number changes. A later experiment must freeze "
            "qualified checkpoints and re-estimate the baseline module effect first."
        ),
    }


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# D2-G source-population qualification",
        "",
        f"Schema: `{report['schema']}`",
        f"Burn-in: `{report['burn_in_ticks']}` ticks",
        "",
        "| Phase | Equal-lineage qualified seeds | Natural-control qualified seeds | Qualified |",
        "|---|---:|---:|---:|",
    ]
    for phase, row in report["phases"].items():
        lines.append(
            f"| {phase} | {row['equal_lineage_seed_count']} | "
            f"{row['natural_abundance_seed_count']} | {row['phase_qualified']} |"
        )
    lines.extend(
        [
            "",
            f"Qualified phases: `{', '.join(report['qualified_phases']) or 'none'}`",
            f"Source population ready: `{report['source_population_ready']}`",
            f"Module copy number ready: `{report['module_copy_number_ready']}`",
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
        description="Assess D2-G source-population burn-in qualification"
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
                "source_population_ready": report["source_population_ready"],
                "recommendation": report["recommendation"],
            }
        )
    )


if __name__ == "__main__":
    main()
