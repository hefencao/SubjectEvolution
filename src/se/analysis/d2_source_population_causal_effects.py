"""Assess D2-H module-3 effects in redesigned source-population checkpoints."""

from __future__ import annotations

import argparse
from dataclasses import asdict
import json
from pathlib import Path
from typing import Any

from se.analysis.d2_lineage_effects import (
    assess_lineage_pair_results,
    build_confirmation_plan,
)
from se.experiments.d2_source_population_causal import (
    PLAN_SCHEMA,
    RESULT_SCHEMA,
    SourcePopulationCausalPlan,
    _lineage_plan_from_payload,
    build_confirmation_source_population_causal_plan,
    render_plan_markdown,
)

ASSESSMENT_SCHEMA = "d2-source-population-causal-assessment-v1"
TARGET_MODULE = 3


def _load(path: str | Path) -> dict[str, Any]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if payload.get("schema") != RESULT_SCHEMA:
        raise ValueError(f"unsupported D2-H result schema: {payload.get('schema')!r}")
    if payload.get("lineage_pair_results", {}).get("schema") is None:
        raise ValueError("D2-H result has no embedded lineage-pair result")
    return payload


def _plan_from_payload(payload: dict[str, Any]) -> SourcePopulationCausalPlan:
    if payload.get("schema") != PLAN_SCHEMA:
        raise ValueError(f"unsupported D2-H plan schema: {payload.get('schema')!r}")
    return SourcePopulationCausalPlan(
        schema=str(payload["schema"]),
        stage=str(payload["stage"]),
        source_assessment_schema=str(payload["source_assessment_schema"]),
        source_assessment_sha256=payload.get("source_assessment_sha256"),
        source_result_schema=str(payload["source_result_schema"]),
        source_result_sha256=payload.get("source_result_sha256"),
        evidence_scope=str(payload["evidence_scope"]),
        selected_phases=tuple(str(value) for value in payload["selected_phases"]),
        selected_panel_seeds=tuple(int(value) for value in payload["selected_panel_seeds"]),
        horizon_ticks=int(payload["horizon_ticks"]),
        module_indices=tuple(int(value) for value in payload["module_indices"]),
        min_lineage_members=int(payload["min_lineage_members"]),
        min_lineages_per_checkpoint=int(payload["min_lineages_per_checkpoint"]),
        max_lineages_per_checkpoint=int(payload["max_lineages_per_checkpoint"]),
        lineage_pair_plan=_lineage_plan_from_payload(payload["lineage_pair_plan"]),
        selection_rule=str(payload.get("selection_rule", "")),
        response_conditioned_panel_selection=bool(
            payload.get("response_conditioned_panel_selection", False)
        ),
        response_conditioned_lineage_selection=bool(
            payload.get("response_conditioned_lineage_selection", False)
        ),
        general_source_population_claim=bool(
            payload.get("general_source_population_claim", False)
        ),
        module_copy_number_changed=bool(payload.get("module_copy_number_changed", False)),
        routing_vocabulary_changed=bool(payload.get("routing_vocabulary_changed", False)),
    )


def assess_source_population_causal_results(
    current: dict[str, Any],
    *,
    short: dict[str, Any] | None = None,
) -> dict[str, Any]:
    current_raw = current["lineage_pair_results"]
    short_raw = short["lineage_pair_results"] if short is not None else None
    lineage_report = assess_lineage_pair_results(
        current_raw,
        short_results=short_raw,
    )
    module = lineage_report["modules"].get(f"module_{TARGET_MODULE}", {})
    screen_pass = bool(module.get("screen_pass"))
    confirmation_pass = (
        bool(module.get("confirmation_pass")) if short is not None else None
    )
    positive_ecological = bool(module.get("positive_ecological_output"))
    if short is None:
        recommendation = (
            "run-300-tick-source-population-causal-confirmation"
            if screen_pass
            else "module-3-not-replicated-in-redesigned-source-population-stop-before-copy-number"
        )
    elif confirmation_pass:
        recommendation = (
            "phase-specific-module-3-causality-confirmed-expand-confidence-before-copy-number"
        )
    else:
        recommendation = (
            "module-3-causality-not-confirmed-in-redesigned-source-population"
        )
    plan = current["plan"]
    return {
        "schema": ASSESSMENT_SCHEMA,
        "current_result_schema": current.get("schema"),
        "short_result_schema": short.get("schema") if short is not None else None,
        "current_horizon_ticks": int(plan["horizon_ticks"]),
        "short_horizon_ticks": (
            int(short["plan"]["horizon_ticks"]) if short is not None else None
        ),
        "evidence_scope": "phase-specific-exploratory-causal-reaudit",
        "selected_phases": list(plan["selected_phases"]),
        "selected_panel_seeds": list(plan["selected_panel_seeds"]),
        "lineage_pair_assessment": lineage_report,
        "module_3_screen_pass": screen_pass,
        "module_3_confirmation_pass": confirmation_pass,
        "positive_ecological_output": positive_ecological,
        "general_source_population_claim": False,
        "module_copy_number_ready": False,
        "recommendation": recommendation,
        "interpretation_boundary": (
            "A repeated module-3 effect in two independently qualified peak checkpoints "
            "is sufficient to continue this exploratory causal chain, not to claim a "
            "general source-population construction. The result remains phase-specific "
            "and low-n. Copy-number manipulation requires additional confidence, a stable "
            "ecological effect, and a separately preregistered copy-number experiment."
        ),
    }


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# D2-H source-population module-3 causal assessment",
        "",
        f"Schema: `{report['schema']}`",
        f"Current horizon: `{report['current_horizon_ticks']}` ticks",
        f"Short horizon: `{report['short_horizon_ticks']}`",
        f"Selected phases: `{', '.join(report['selected_phases'])}`",
        f"Selected fresh-world seeds: `{', '.join(map(str, report['selected_panel_seeds']))}`",
        "",
        f"Module 3 screen pass: `{report['module_3_screen_pass']}`",
        f"Module 3 confirmation pass: `{report['module_3_confirmation_pass']}`",
        f"Positive ecological output: `{report['positive_ecological_output']}`",
        f"General source-population claim: `{report['general_source_population_claim']}`",
        f"Module copy number ready: `{report['module_copy_number_ready']}`",
        "",
        "## Recommendation",
        "",
        f"`{report['recommendation']}`",
        "",
        report["interpretation_boundary"],
        "",
    ]
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Assess D2-H source-population module-3 causal re-audit"
    )
    parser.add_argument("--results")
    parser.add_argument("--short-results")
    parser.add_argument("--long-results")
    parser.add_argument("--output", required=True)
    parser.add_argument("--confirmation-horizon", type=int, default=300)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    if args.results and (args.short_results or args.long_results):
        raise ValueError("--results cannot be combined with --short-results/--long-results")
    if args.results:
        current = _load(args.results)
        short = None
    else:
        if not args.short_results or not args.long_results:
            raise ValueError(
                "provide --results, or both --short-results and --long-results"
            )
        short = _load(args.short_results)
        current = _load(args.long_results)
    report = assess_source_population_causal_results(current, short=short)
    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=True)
    (output / "d2_source_population_causal_assessment.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (output / "d2_source_population_causal_assessment.md").write_text(
        render_markdown(report), encoding="utf-8"
    )

    confirmation_written = False
    if short is None and report["module_3_screen_pass"]:
        raw_report = current["lineage_pair_results"]
        confirmation_lineage_plan = build_confirmation_plan(
            raw_report,
            report["lineage_pair_assessment"],
            horizon_ticks=args.confirmation_horizon,
        )
        if confirmation_lineage_plan is not None:
            short_plan = _plan_from_payload(current["plan"])
            confirmation_plan = build_confirmation_source_population_causal_plan(
                short_plan,
                confirmation_lineage_plan,
            )
            (output / "d2_source_population_causal_confirmation_plan.json").write_text(
                json.dumps(asdict(confirmation_plan), ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            (output / "d2_source_population_causal_confirmation_plan.md").write_text(
                render_plan_markdown(confirmation_plan), encoding="utf-8"
            )
            confirmation_written = True
    print(
        json.dumps(
            {
                "passed": True,
                "recommendation": report["recommendation"],
                "confirmation_plan_written": confirmation_written,
                "module_copy_number_ready": False,
            }
        )
    )


if __name__ == "__main__":
    main()
