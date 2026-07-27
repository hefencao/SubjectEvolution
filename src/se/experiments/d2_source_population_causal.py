"""D2-H phase-specific module-3 re-audit in redesigned source populations.

D2-G may qualify a phase for an exploratory next step without establishing a
general source-population conclusion.  D2-H freezes only the preregistered
qualified equal-lineage checkpoints and reuses the existing lineage-targeted
three-branch intervention:

* baseline;
* output-neutral with expression cost retained;
* expression-neutral with output and expression cost removed.

The experiment does not select lineages by their D2-G response.  Every lineage
that satisfies the preregistered member and expression floors at the frozen
checkpoint is retained.  It does not alter copy number or world rules.
"""

from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass, replace
import hashlib
import json
from pathlib import Path
from typing import Any, Iterable

from se.analysis.d2_source_population_effects import (
    ASSESSMENT_SCHEMA as SOURCE_ASSESSMENT_SCHEMA,
    SUPPORTED_ASSESSMENT_SCHEMAS,
)
from se.experiments.d2_lineage_pairs import (
    BRANCHES,
    PLAN_SCHEMA as LINEAGE_PLAN_SCHEMA,
    LineagePairCheckpoint,
    LineagePairPlan,
    LineageSelection,
    execute_lineage_pair_plan,
    render_plan_markdown as render_lineage_plan_markdown,
)
from se.experiments.d2_source_population import RESULT_SCHEMA as SOURCE_RESULT_SCHEMA

PLAN_SCHEMA = "d2-source-population-causal-plan-v1"
RESULT_SCHEMA = "d2-source-population-causal-results-v1"
DEFAULT_HORIZON_TICKS = 120
DEFAULT_MODULE_INDICES = (3,)
DEFAULT_MIN_LINEAGE_MEMBERS = 8
DEFAULT_MIN_LINEAGES_PER_CHECKPOINT = 4
DEFAULT_MAX_LINEAGES_PER_CHECKPOINT = 6
EXPRESSION_FRACTION_FLOOR = 0.5


@dataclass(frozen=True)
class SourcePopulationCausalPlan:
    schema: str
    stage: str
    source_assessment_schema: str
    source_assessment_sha256: str | None
    source_result_schema: str
    source_result_sha256: str | None
    evidence_scope: str
    selected_phases: tuple[str, ...]
    selected_panel_seeds: tuple[int, ...]
    horizon_ticks: int
    module_indices: tuple[int, ...]
    min_lineage_members: int
    min_lineages_per_checkpoint: int
    max_lineages_per_checkpoint: int
    lineage_pair_plan: LineagePairPlan
    selection_rule: str = (
        "phase-qualified-equal-lineage-final-checkpoints; preserve-all-member-and-expression-eligible-lineages-v1"
    )
    response_conditioned_panel_selection: bool = False
    response_conditioned_lineage_selection: bool = False
    general_source_population_claim: bool = False
    module_copy_number_changed: bool = False
    routing_vocabulary_changed: bool = False


def _sha256(path: str | Path | None) -> str | None:
    if path is None:
        return None
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _normalize_modules(values: Iterable[int]) -> tuple[int, ...]:
    modules: list[int] = []
    for value in values:
        index = int(value)
        if index < 0:
            raise ValueError("module indices must be non-negative")
        if index not in modules:
            modules.append(index)
    if not modules:
        raise ValueError("at least one module index is required")
    return tuple(modules)


def _final_snapshot(arm: dict[str, Any], final_offset: int) -> dict[str, Any]:
    rows = [
        row
        for row in arm.get("trajectory", ())
        if int(row.get("offset_ticks", -1)) == int(final_offset)
    ]
    if len(rows) != 1:
        raise ValueError("each selected source-population arm must have one final snapshot")
    return rows[0]


def _assessment_panel_map(assessment: dict[str, Any]) -> dict[str, dict[str, Any]]:
    rows: dict[str, dict[str, Any]] = {}
    for row in assessment.get("panels", ()):
        name = str(row["panel_name"])
        if name in rows:
            raise ValueError(f"duplicate source-population assessment panel: {name}")
        rows[name] = row
    return rows


def _result_panel_map(results: dict[str, Any]) -> dict[str, dict[str, Any]]:
    rows: dict[str, dict[str, Any]] = {}
    for row in results.get("panels", ()):
        name = str(row["panel_name"])
        if name in rows:
            raise ValueError(f"duplicate source-population result panel: {name}")
        rows[name] = row
    return rows


def _eligible_lineages(
    final: dict[str, Any],
    *,
    module_index: int,
    min_members: int,
    max_lineages: int,
) -> tuple[LineageSelection, ...]:
    expression_rows = {
        int(row["panel_lineage_id"]): row
        for row in final.get("candidate_module_expression", {})
        .get(f"module_{module_index}", {})
        .get("lineages", ())
    }
    counts = [
        (int(row["panel_lineage_id"]), int(row["members"]))
        for row in final.get("panel_lineage_counts", ())
    ]
    total = int(final.get("alive", sum(value for _, value in counts)))
    ordered = sorted(counts, key=lambda item: (-item[1], item[0]))
    selections: list[LineageSelection] = []
    for rank, (lineage_id, members) in enumerate(ordered, start=1):
        expression = expression_rows.get(lineage_id, {})
        expressed_fraction = float(expression.get("expressed_fraction", 0.0))
        if members < min_members or expressed_fraction < EXPRESSION_FRACTION_FLOOR:
            continue
        selections.append(
            LineageSelection(
                lineage_id=lineage_id,
                members=members,
                member_fraction=(float(members) / total if total else 0.0),
                abundance_rank=rank,
            )
        )
        if len(selections) >= max_lineages:
            break
    return tuple(selections)


def build_source_population_causal_plan(
    assessment: dict[str, Any],
    results: dict[str, Any],
    *,
    horizon_ticks: int = DEFAULT_HORIZON_TICKS,
    module_indices: Iterable[int] = DEFAULT_MODULE_INDICES,
    min_lineage_members: int = DEFAULT_MIN_LINEAGE_MEMBERS,
    min_lineages_per_checkpoint: int = DEFAULT_MIN_LINEAGES_PER_CHECKPOINT,
    max_lineages_per_checkpoint: int = DEFAULT_MAX_LINEAGES_PER_CHECKPOINT,
    assessment_path: str | Path | None = None,
    results_path: str | Path | None = None,
) -> SourcePopulationCausalPlan:
    if assessment.get("schema") not in SUPPORTED_ASSESSMENT_SCHEMAS:
        raise ValueError(
            f"unsupported source-population assessment: {assessment.get('schema')!r}"
        )
    if results.get("schema") != SOURCE_RESULT_SCHEMA:
        raise ValueError(
            f"unsupported source-population results: {results.get('schema')!r}"
        )
    if horizon_ticks <= 0:
        raise ValueError("horizon_ticks must be positive")
    if min_lineage_members <= 0:
        raise ValueError("min_lineage_members must be positive")
    if min_lineages_per_checkpoint < 2:
        raise ValueError("min_lineages_per_checkpoint must be at least two")
    if max_lineages_per_checkpoint < min_lineages_per_checkpoint:
        raise ValueError(
            "max_lineages_per_checkpoint must be >= min_lineages_per_checkpoint"
        )

    modules = _normalize_modules(module_indices)
    if modules != (3,):
        raise ValueError(
            "D2-H is preregistered for module 3 only; other modules require a new plan schema"
        )

    qualified_phases = tuple(
        str(value)
        for value in (
            assessment.get("exploratory_qualified_phases")
            or assessment.get("qualified_phases")
            or ()
        )
    )
    if not qualified_phases:
        raise ValueError("source-population assessment contains no qualified phase")
    if assessment.get("schema") == SOURCE_ASSESSMENT_SCHEMA and not bool(
        assessment.get("exploratory_causal_reaudit_ready")
    ):
        raise ValueError("source-population assessment does not authorize exploratory re-audit")

    assessment_panels = _assessment_panel_map(assessment)
    result_panels = _result_panel_map(results)
    final_offset = int(results["plan"]["burn_in_ticks"])
    checkpoints: list[LineagePairCheckpoint] = []
    selected_seeds: list[int] = []

    for panel_name, assessment_row in sorted(assessment_panels.items()):
        phase = str(assessment_row["phase"])
        if phase not in qualified_phases:
            continue
        equal_assessment = assessment_row.get("arms", {}).get(
            "equal-lineage-reconstitution", {}
        )
        if not bool(equal_assessment.get("qualified")):
            continue
        panel = result_panels.get(panel_name)
        if panel is None:
            raise ValueError(f"assessment panel missing from source results: {panel_name}")
        equal_arm = panel.get("arms", {}).get("equal-lineage-reconstitution")
        if equal_arm is None:
            raise ValueError(f"panel has no equal-lineage arm: {panel_name}")
        final = _final_snapshot(equal_arm, final_offset)
        lineages = _eligible_lineages(
            final,
            module_index=modules[0],
            min_members=min_lineage_members,
            max_lineages=max_lineages_per_checkpoint,
        )
        if len(lineages) < min_lineages_per_checkpoint:
            raise ValueError(
                f"qualified panel {panel_name} has only {len(lineages)} eligible lineages"
            )
        checkpoint_path = str(equal_arm["final_checkpoint"])
        panel_seed = int(panel["panel_seed"])
        selected_seeds.append(panel_seed)
        checkpoints.append(
            LineagePairCheckpoint(
                run_name=panel_name,
                phase=phase,
                checkpoint_tick=final_offset,
                checkpoint_path=checkpoint_path,
                until_tick=final_offset + int(horizon_ticks),
                active_entities=int(final["alive"]),
                effective_lineages=float(final["effective_lineages"]),
                dominant_lineage_fraction=float(final["dominant_lineage_fraction"]),
                eligible=True,
                ineligible_reason=None,
                lineages=lineages,
            )
        )

    if len(checkpoints) < 2:
        raise ValueError(
            "D2-H requires at least two independently qualified fresh-world checkpoints"
        )

    lineage_plan = LineagePairPlan(
        schema=LINEAGE_PLAN_SCHEMA,
        horizon_ticks=int(horizon_ticks),
        module_indices=modules,
        min_lineage_members=int(min_lineage_members),
        min_lineages_per_checkpoint=int(min_lineages_per_checkpoint),
        max_lineages_per_checkpoint=int(max_lineages_per_checkpoint),
        checkpoints=tuple(checkpoints),
        lineage_selection_rule=(
            "all-final-checkpoint-lineages-passing-preregistered-member-and-expression-floors-v1"
        ),
        paired_randomness=True,
        genotype_preserved=True,
        lineage_membership_preserved=True,
        abundance_weighted_inference=False,
        branches=BRANCHES,
        effect_decomposition_schema="output-cost-total-additive-v1",
        confirmation_source_result_schema=None,
        confirmation_source_horizon_ticks=None,
        confirmation_selection_rule=None,
        outcome_conditioned_pair_selection=False,
    )
    return SourcePopulationCausalPlan(
        schema=PLAN_SCHEMA,
        stage="120-tick-exploratory-screen" if horizon_ticks == 120 else "paired-causal-audit",
        source_assessment_schema=str(assessment["schema"]),
        source_assessment_sha256=_sha256(assessment_path),
        source_result_schema=str(results["schema"]),
        source_result_sha256=_sha256(results_path),
        evidence_scope="phase-specific-exploratory-causal-reaudit",
        selected_phases=tuple(sorted({row.phase for row in checkpoints})),
        selected_panel_seeds=tuple(sorted(set(selected_seeds))),
        horizon_ticks=int(horizon_ticks),
        module_indices=modules,
        min_lineage_members=int(min_lineage_members),
        min_lineages_per_checkpoint=int(min_lineages_per_checkpoint),
        max_lineages_per_checkpoint=int(max_lineages_per_checkpoint),
        lineage_pair_plan=lineage_plan,
    )


def _lineage_plan_from_payload(payload: dict[str, Any]) -> LineagePairPlan:
    checkpoints: list[LineagePairCheckpoint] = []
    for item in payload.get("checkpoints", ()):
        lineages = tuple(LineageSelection(**row) for row in item.get("lineages", ()))
        checkpoints.append(LineagePairCheckpoint(**{**item, "lineages": lineages}))
    if not checkpoints:
        raise ValueError("D2-H plan contains no lineage-pair checkpoints")
    return LineagePairPlan(
        schema=str(payload["schema"]),
        horizon_ticks=int(payload["horizon_ticks"]),
        module_indices=tuple(int(value) for value in payload["module_indices"]),
        min_lineage_members=int(payload["min_lineage_members"]),
        min_lineages_per_checkpoint=int(payload["min_lineages_per_checkpoint"]),
        max_lineages_per_checkpoint=int(payload["max_lineages_per_checkpoint"]),
        checkpoints=tuple(checkpoints),
        lineage_selection_rule=str(payload.get("lineage_selection_rule", "")),
        paired_randomness=bool(payload.get("paired_randomness", True)),
        genotype_preserved=bool(payload.get("genotype_preserved", True)),
        lineage_membership_preserved=bool(
            payload.get("lineage_membership_preserved", True)
        ),
        abundance_weighted_inference=bool(
            payload.get("abundance_weighted_inference", False)
        ),
        branches=tuple(payload.get("branches", BRANCHES)),
        effect_decomposition_schema=str(
            payload.get("effect_decomposition_schema", "output-cost-total-additive-v1")
        ),
        confirmation_source_result_schema=payload.get(
            "confirmation_source_result_schema"
        ),
        confirmation_source_horizon_ticks=(
            int(payload["confirmation_source_horizon_ticks"])
            if payload.get("confirmation_source_horizon_ticks") is not None
            else None
        ),
        confirmation_selection_rule=payload.get("confirmation_selection_rule"),
        outcome_conditioned_pair_selection=bool(
            payload.get("outcome_conditioned_pair_selection", False)
        ),
    )


def load_source_population_causal_plan(path: str | Path) -> SourcePopulationCausalPlan:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if payload.get("schema") != PLAN_SCHEMA:
        raise ValueError(f"unsupported D2-H plan: {payload.get('schema')!r}")
    lineage_plan = _lineage_plan_from_payload(payload["lineage_pair_plan"])
    return SourcePopulationCausalPlan(
        schema=str(payload["schema"]),
        stage=str(payload["stage"]),
        source_assessment_schema=str(payload["source_assessment_schema"]),
        source_assessment_sha256=payload.get("source_assessment_sha256"),
        source_result_schema=str(payload["source_result_schema"]),
        source_result_sha256=payload.get("source_result_sha256"),
        evidence_scope=str(payload["evidence_scope"]),
        selected_phases=tuple(str(value) for value in payload["selected_phases"]),
        selected_panel_seeds=tuple(
            int(value) for value in payload["selected_panel_seeds"]
        ),
        horizon_ticks=int(payload["horizon_ticks"]),
        module_indices=tuple(int(value) for value in payload["module_indices"]),
        min_lineage_members=int(payload["min_lineage_members"]),
        min_lineages_per_checkpoint=int(payload["min_lineages_per_checkpoint"]),
        max_lineages_per_checkpoint=int(payload["max_lineages_per_checkpoint"]),
        lineage_pair_plan=lineage_plan,
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
        module_copy_number_changed=bool(
            payload.get("module_copy_number_changed", False)
        ),
        routing_vocabulary_changed=bool(
            payload.get("routing_vocabulary_changed", False)
        ),
    )


def build_confirmation_source_population_causal_plan(
    short_plan: SourcePopulationCausalPlan,
    confirmation_lineage_plan: LineagePairPlan,
) -> SourcePopulationCausalPlan:
    return replace(
        short_plan,
        stage="300-tick-confirmation",
        horizon_ticks=int(confirmation_lineage_plan.horizon_ticks),
        module_indices=tuple(confirmation_lineage_plan.module_indices),
        lineage_pair_plan=confirmation_lineage_plan,
    )


def execute_source_population_causal_plan(
    plan: SourcePopulationCausalPlan,
    output_dir: str | Path,
    *,
    backend: str = "cpu",
    gpu_semantics_mode: str | None = None,
) -> dict[str, Any]:
    if plan.general_source_population_claim:
        raise ValueError("D2-H exploratory plan cannot claim general source-population validity")
    if plan.module_copy_number_changed or plan.routing_vocabulary_changed:
        raise ValueError("D2-H cannot alter module copy number or routing vocabulary")
    root = Path(output_dir)
    root.mkdir(parents=True, exist_ok=True)
    lineage_results = execute_lineage_pair_plan(
        plan.lineage_pair_plan,
        root / "lineage_pairs",
        backend=backend,
        gpu_semantics_mode=gpu_semantics_mode,
    )
    report = {
        "schema": RESULT_SCHEMA,
        "plan": asdict(plan),
        "backend": backend,
        "gpu_semantics_mode": gpu_semantics_mode,
        "lineage_pair_results": lineage_results,
        "executed_checkpoint_count": int(
            lineage_results["eligible_checkpoint_count"]
        ),
        "executed_pair_count": int(lineage_results["executed_pair_count"]),
        "module_copy_number_ready": False,
        "interpretation_boundary": (
            "This is a phase-specific exploratory causal re-audit in frozen D2-G "
            "checkpoints. It can determine whether module 3 still has routed-output or "
            "retained-cost effects after source-population redesign. It does not convert "
            "three D2-G seeds into a general source-population conclusion and cannot "
            "authorize copy-number changes."
        ),
    }
    (root / "d2_source_population_causal_results.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (root / "d2_source_population_causal_results.md").write_text(
        render_results_markdown(report), encoding="utf-8"
    )
    return report


def render_plan_markdown(plan: SourcePopulationCausalPlan) -> str:
    lines = [
        "# D2-H source-population module-3 causal re-audit plan",
        "",
        f"Schema: `{plan.schema}`",
        f"Stage: `{plan.stage}`",
        f"Evidence scope: `{plan.evidence_scope}`",
        f"Horizon: **{plan.horizon_ticks} ticks**",
        f"Selected phases: `{', '.join(plan.selected_phases)}`",
        f"Selected fresh-world seeds: `{', '.join(map(str, plan.selected_panel_seeds))}`",
        f"Modules: `{', '.join(map(str, plan.module_indices))}`",
        "",
        "The panel selection uses only the preregistered D2-G qualification guards. "
        "Every eligible lineage in each frozen checkpoint is retained; no D2-G response "
        "magnitude is used to select a lineage.",
        "",
        render_lineage_plan_markdown(plan.lineage_pair_plan),
        "",
    ]
    return "\n".join(lines)


def render_results_markdown(report: dict[str, Any]) -> str:
    plan = report["plan"]
    return "\n".join(
        [
            "# D2-H source-population module-3 causal re-audit results",
            "",
            f"Schema: `{report['schema']}`",
            f"Stage: `{plan['stage']}`",
            f"Horizon: `{plan['horizon_ticks']}` ticks",
            f"Selected phases: `{', '.join(plan['selected_phases'])}`",
            f"Executed checkpoints: `{report['executed_checkpoint_count']}`",
            f"Executed lineage pairs: `{report['executed_pair_count']}`",
            f"Module copy number ready: `{report['module_copy_number_ready']}`",
            "",
            report["interpretation_boundary"],
            "",
        ]
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Build or execute D2-H source-population module-3 causal re-audit"
    )
    parser.add_argument("--assessment")
    parser.add_argument("--results")
    parser.add_argument("--plan")
    parser.add_argument("--output", required=True)
    parser.add_argument("--horizon-ticks", type=int, default=DEFAULT_HORIZON_TICKS)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--backend", choices=("cpu", "gpu", "auto"), default="cpu")
    parser.add_argument("--gpu-semantics-mode")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=True)
    if args.plan:
        if args.assessment or args.results:
            raise ValueError("--plan cannot be combined with --assessment/--results")
        plan = load_source_population_causal_plan(args.plan)
    else:
        if not args.assessment or not args.results:
            raise ValueError("provide both --assessment and --results, or --plan")
        assessment = json.loads(Path(args.assessment).read_text(encoding="utf-8"))
        results = json.loads(Path(args.results).read_text(encoding="utf-8"))
        plan = build_source_population_causal_plan(
            assessment,
            results,
            horizon_ticks=args.horizon_ticks,
            assessment_path=args.assessment,
            results_path=args.results,
        )
        (output / "d2_source_population_causal_plan.json").write_text(
            json.dumps(asdict(plan), ensure_ascii=False, indent=2), encoding="utf-8"
        )
        (output / "d2_source_population_causal_plan.md").write_text(
            render_plan_markdown(plan), encoding="utf-8"
        )
    report = None
    if args.execute:
        report = execute_source_population_causal_plan(
            plan,
            output,
            backend=args.backend,
            gpu_semantics_mode=args.gpu_semantics_mode,
        )
    print(
        json.dumps(
            {
                "passed": True,
                "plan_schema": plan.schema,
                "stage": plan.stage,
                "selected_phases": list(plan.selected_phases),
                "selected_panel_seed_count": len(plan.selected_panel_seeds),
                "checkpoint_count": len(plan.lineage_pair_plan.checkpoints),
                "executed": report is not None,
            }
        )
    )


if __name__ == "__main__":
    main()
