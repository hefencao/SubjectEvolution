"""Assess lineage-conditioned D2 module effects and plan confirmation runs.

The 120-tick lineage-pair screen is intentionally not interpreted from raw
non-zero endpoint divergence.  This module applies practical thresholds,
separates routed-output effects from retained expression-cost effects, requires
same-direction evidence in multiple non-dominant lineages across seeds, and
creates a 300-tick plan without selecting individual pairs by their response.
"""

from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass, replace
import json
from pathlib import Path
from typing import Any, Iterable

import numpy as np

from se.experiments.d2_lineage_pairs import (
    PLAN_SCHEMA,
    RESULT_SCHEMAS,
    LineagePairCheckpoint,
    LineagePairPlan,
    LineageSelection,
    render_plan_markdown,
)

ASSESSMENT_SCHEMA = "d2-lineage-paired-assessment-v1"
NUMERICAL_TOLERANCE = 1e-12
MIN_SEEDS = 2
MIN_NON_DOMINANT_LINEAGE_IDENTITIES = 2
LINEAGE_GUARD_EFFECTIVE_COUNT = 4.0
CONFIRMATION_SELECTION_RULE = (
    "module-level-screen-preserve-all-preselected-checkpoint-lineage-pairs-v1"
)


@dataclass(frozen=True)
class PairEffectRule:
    role: str
    absolute: float
    relative: float = 0.0


# These thresholds inherit the already registered D2-C world/evolution rules.
# Target-lineage outcomes use the same energy threshold and a one-entity floor
# because the intervention scope is one lineage rather than the whole world.
PAIR_EFFECT_RULES: dict[str, PairEffectRule] = {
    "world.alive": PairEffectRule("ecological", 2.0, 0.005),
    "world.mean_energy": PairEffectRule("process", 0.01),
    "target_lineage.alive": PairEffectRule("ecological", 1.0, 0.005),
    "target_lineage.mean_energy": PairEffectRule("process", 0.01),
    "evolution.environment_resource_effective_dimensions": PairEffectRule(
        "ecological", 0.02
    ),
    "derived.harvest_extraction_efficiency_window": PairEffectRule(
        "mechanistic", 0.005
    ),
    "evolution.knowledge_effective_transferred_roots": PairEffectRule(
        "ecological", 2.0, 0.01
    ),
    "evolution.effective_lineages": PairEffectRule("ecological", 0.05),
    "evolution.functional_harvest_preference_effective_dimensions": PairEffectRule(
        "mechanistic", 0.02
    ),
}

EFFECT_NAMES = (
    "output_routing_effect",
    "retained_expression_cost_effect",
    "total_expression_effect",
)


def _load_results(path: str | Path) -> dict[str, Any]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if payload.get("schema") not in RESULT_SCHEMAS:
        raise ValueError(
            f"unsupported D2 lineage-pair result schema: {payload.get('schema')!r}"
        )
    if not payload.get("checkpoints"):
        raise ValueError("D2 lineage-pair result contains no checkpoints")
    return payload


def _threshold(rule: PairEffectRule, baseline: float) -> float:
    return max(float(rule.absolute), float(rule.relative) * abs(float(baseline)))


def _sign(value: float) -> int:
    if value > NUMERICAL_TOLERANCE:
        return 1
    if value < -NUMERICAL_TOLERANCE:
        return -1
    return 0


def _pair_key(row: dict[str, Any]) -> tuple[str, str, int, int, int]:
    pair = row["pair"]
    return (
        str(pair["run_name"]),
        str(pair["phase"]),
        int(pair["checkpoint_tick"]),
        int(row["module_index"]),
        int(pair["lineage_id"]),
    )


def _rows_by_key(results: dict[str, Any]) -> dict[tuple[str, str, int, int, int], dict[str, Any]]:
    rows: dict[tuple[str, str, int, int, int], dict[str, Any]] = {}
    for checkpoint in results["checkpoints"]:
        for row in checkpoint.get("pairs", ()):
            key = _pair_key(row)
            if key in rows:
                raise ValueError(f"duplicate D2 lineage-pair row: {key!r}")
            rows[key] = row
    if not rows:
        raise ValueError("D2 lineage-pair result contains no executed pairs")
    return rows


def _seed_count(rows: Iterable[dict[str, Any]]) -> int:
    return len({str(row["run_name"]) for row in rows})


def _lineage_identity_count(rows: Iterable[dict[str, Any]]) -> int:
    return len(
        {(str(row["run_name"]), int(row["lineage_id"])) for row in rows}
    )


def _replicated_sign(rows: list[dict[str, Any]]) -> tuple[int, list[dict[str, Any]]]:
    for sign in (1, -1):
        same = [row for row in rows if int(row["sign"]) == sign]
        if (
            _seed_count(same) >= MIN_SEEDS
            and _lineage_identity_count(same) >= MIN_NON_DOMINANT_LINEAGE_IDENTITIES
        ):
            return sign, same
    return 0, []


def _metric_assessment(
    *,
    module_index: int,
    effect_name: str,
    outcome: str,
    current_rows: dict[tuple[str, str, int, int, int], dict[str, Any]],
    short_rows: dict[tuple[str, str, int, int, int], dict[str, Any]] | None,
) -> dict[str, Any]:
    rule = PAIR_EFFECT_RULES[outcome]
    rows: list[dict[str, Any]] = []
    for key, row in sorted(current_rows.items()):
        if int(row["module_index"]) != module_index:
            continue
        effects = row.get("effects", {}).get(effect_name, {})
        if outcome not in effects:
            continue
        pair = row["pair"]
        baseline = float(row["branches"]["baseline"]["outcomes"][outcome])
        effect = float(effects[outcome])
        threshold = _threshold(rule, baseline)
        short_effect = None
        short_material = None
        same_sign_across_horizons = None
        if short_rows is not None and key in short_rows:
            short_row = short_rows[key]
            short_effects = short_row.get("effects", {}).get(effect_name, {})
            if outcome in short_effects:
                short_baseline = float(
                    short_row["branches"]["baseline"]["outcomes"][outcome]
                )
                short_effect = float(short_effects[outcome])
                short_material = abs(short_effect) >= _threshold(rule, short_baseline)
                same_sign_across_horizons = bool(
                    _sign(short_effect) != 0 and _sign(short_effect) == _sign(effect)
                )
        rows.append(
            {
                "run_name": str(pair["run_name"]),
                "phase": str(pair["phase"]),
                "checkpoint_tick": int(pair["checkpoint_tick"]),
                "lineage_id": int(pair["lineage_id"]),
                "source_members": int(pair["source_members"]),
                "source_member_fraction": float(pair["source_member_fraction"]),
                "source_abundance_rank": int(pair["source_abundance_rank"]),
                "non_dominant": int(pair["source_abundance_rank"]) > 1,
                "baseline": baseline,
                "effect": effect,
                "threshold": threshold,
                "sign": _sign(effect),
                "numerically_nonzero": abs(effect) > NUMERICAL_TOLERANCE,
                "material": abs(effect) >= threshold,
                "short_effect": short_effect,
                "short_sign": _sign(short_effect) if short_effect is not None else None,
                "short_material": short_material,
                "same_sign_across_horizons": same_sign_across_horizons,
            }
        )

    material = [row for row in rows if row["material"]]
    non_dominant_material = [
        row for row in material if bool(row["non_dominant"])
    ]
    replicated_sign, replicated_rows = _replicated_sign(non_dominant_material)

    short_non_dominant_material = [
        {**row, "sign": int(row["short_sign"])}
        for row in rows
        if row["non_dominant"] and row["short_material"]
    ]
    short_replicated_sign, short_replicated_rows = _replicated_sign(
        short_non_dominant_material
    )
    paired_horizon_rows = [
        row
        for row in non_dominant_material
        if row["short_material"] and row["same_sign_across_horizons"]
    ]
    persistent_sign, persistent_rows = _replicated_sign(paired_horizon_rows)

    return {
        "role": rule.role,
        "rule": asdict(rule),
        "rows": rows,
        "material_count": len(material),
        "material_seed_count": _seed_count(material),
        "non_dominant_material_count": len(non_dominant_material),
        "non_dominant_material_seed_count": _seed_count(non_dominant_material),
        "non_dominant_lineage_identity_count": _lineage_identity_count(
            non_dominant_material
        ),
        "replicated_non_dominant": replicated_sign != 0,
        "replicated_sign": replicated_sign,
        "replicated_seed_count": _seed_count(replicated_rows),
        "replicated_lineage_identity_count": _lineage_identity_count(
            replicated_rows
        ),
        "dominant_only_material": bool(material) and not non_dominant_material,
        "short_replicated_non_dominant": short_replicated_sign != 0,
        "short_replicated_sign": short_replicated_sign,
        "short_replicated_seed_count": _seed_count(short_replicated_rows),
        "short_replicated_lineage_identity_count": _lineage_identity_count(
            short_replicated_rows
        ),
        "paired_horizon_material_same_sign_count": len(paired_horizon_rows),
        "persistent_non_dominant": persistent_sign != 0,
        "persistent_sign": persistent_sign,
        "persistent_seed_count": _seed_count(persistent_rows),
        "persistent_lineage_identity_count": _lineage_identity_count(
            persistent_rows
        ),
    }


def _module_indices(results: dict[str, Any]) -> tuple[int, ...]:
    embedded = results.get("plan", {}).get("module_indices")
    if embedded:
        return tuple(sorted({int(value) for value in embedded}))
    return tuple(
        sorted(
            {
                int(row["module_index"])
                for checkpoint in results["checkpoints"]
                for row in checkpoint.get("pairs", ())
            }
        )
    )


def _lineage_guard(results: dict[str, Any]) -> dict[str, Any]:
    checkpoints = results.get("plan", {}).get("checkpoints", ())
    effective = [float(item["effective_lineages"]) for item in checkpoints]
    dominant = [float(item["dominant_lineage_fraction"]) for item in checkpoints]
    if not effective:
        return {
            "available": False,
            "median_effective_lineages": None,
            "minimum_effective_lineages": None,
            "median_dominant_lineage_fraction": None,
            "dominant_lineage_risk": True,
            "effective_lineage_threshold": LINEAGE_GUARD_EFFECTIVE_COUNT,
        }
    return {
        "available": True,
        "median_effective_lineages": float(np.median(effective)),
        "minimum_effective_lineages": float(np.min(effective)),
        "median_dominant_lineage_fraction": float(np.median(dominant)),
        "dominant_lineage_risk": bool(
            float(np.median(effective)) < LINEAGE_GUARD_EFFECTIVE_COUNT
        ),
        "effective_lineage_threshold": LINEAGE_GUARD_EFFECTIVE_COUNT,
    }


def assess_lineage_pair_results(
    current_results: dict[str, Any],
    *,
    short_results: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if current_results.get("schema") not in RESULT_SCHEMAS:
        raise ValueError(
            f"unsupported D2 lineage-pair result schema: {current_results.get('schema')!r}"
        )
    if short_results is not None and short_results.get("schema") not in RESULT_SCHEMAS:
        raise ValueError(
            f"unsupported short D2 lineage-pair result schema: {short_results.get('schema')!r}"
        )
    current_rows = _rows_by_key(current_results)
    short_rows = _rows_by_key(short_results) if short_results is not None else None
    modules: dict[str, Any] = {}
    long_candidates: list[int] = []
    confirmed_modules: list[int] = []
    positive_ecological_modules: list[int] = []

    for module_index in _module_indices(current_results):
        effects: dict[str, Any] = {}
        for effect_name in EFFECT_NAMES:
            metrics: dict[str, Any] = {}
            for outcome in PAIR_EFFECT_RULES:
                assessment = _metric_assessment(
                    module_index=module_index,
                    effect_name=effect_name,
                    outcome=outcome,
                    current_rows=current_rows,
                    short_rows=short_rows,
                )
                if assessment["rows"]:
                    metrics[outcome] = assessment
            effects[effect_name] = metrics

        output_metrics = effects["output_routing_effect"]
        repeated_output = {
            outcome: metric
            for outcome, metric in output_metrics.items()
            if metric["replicated_non_dominant"]
        }
        screen_output = (
            {
                outcome: metric
                for outcome, metric in output_metrics.items()
                if metric["short_replicated_non_dominant"]
            }
            if short_results is not None
            else repeated_output
        )
        persistent_output = {
            outcome: metric
            for outcome, metric in output_metrics.items()
            if metric["persistent_non_dominant"]
        }
        repeated_cost = {
            outcome: metric
            for outcome, metric in effects["retained_expression_cost_effect"].items()
            if metric["replicated_non_dominant"]
        }
        cost_only = bool(repeated_cost) and not repeated_output

        if short_results is None and screen_output:
            long_candidates.append(module_index)
        if short_results is not None and persistent_output:
            confirmed_modules.append(module_index)
        decision_output = persistent_output if short_results is not None else screen_output
        positive_ecological = any(
            metric["role"] == "ecological"
            and (
                metric["persistent_sign"] > 0
                if short_results is not None
                else metric["replicated_sign"] > 0
            )
            for metric in decision_output.values()
        )
        if positive_ecological:
            positive_ecological_modules.append(module_index)

        modules[f"module_{module_index}"] = {
            "effects": effects,
            "screen_output_outcomes": sorted(screen_output),
            "repeated_output_outcomes": sorted(repeated_output),
            "persistent_output_outcomes": sorted(persistent_output),
            "repeated_cost_outcomes": sorted(repeated_cost),
            "screen_pass": bool(screen_output),
            "confirmation_pass": bool(persistent_output)
            if short_results is not None
            else None,
            "cost_only_signal": cost_only,
            "positive_ecological_output": positive_ecological,
        }

    guard = _lineage_guard(current_results)
    if short_results is None:
        if long_candidates:
            recommendation = "run-300-tick-lineage-pair-confirmation"
        elif any(value["cost_only_signal"] for value in modules.values()):
            recommendation = "output-not-replicated-audit-expression-cost-and-cancellation"
        else:
            recommendation = "stop-before-longer-lineage-pair-audit"
    else:
        if confirmed_modules and positive_ecological_modules:
            recommendation = (
                "causal-persistence-confirmed-redesign-source-population-before-copy-number"
                if guard["dominant_lineage_risk"]
                else "positive-cross-lineage-persistence-confirmed"
            )
        elif confirmed_modules:
            recommendation = "causal-output-confirmed-but-copy-number-not-justified"
        else:
            recommendation = "lineage-pair-effect-not-confirmed"

    return {
        "schema": ASSESSMENT_SCHEMA,
        "current_result_schema": current_results.get("schema"),
        "short_result_schema": short_results.get("schema") if short_results else None,
        "current_horizon_ticks": int(current_results["plan"]["horizon_ticks"]),
        "short_horizon_ticks": (
            int(short_results["plan"]["horizon_ticks"]) if short_results else None
        ),
        "effect_rules": {
            outcome: asdict(rule) for outcome, rule in PAIR_EFFECT_RULES.items()
        },
        "replication_rule": {
            "effect_required": "output_routing_effect",
            "minimum_seeds": MIN_SEEDS,
            "minimum_non_dominant_lineage_identities": MIN_NON_DOMINANT_LINEAGE_IDENTITIES,
            "dominant_lineage_rank": 1,
            "same_material_direction_required": True,
            "exact_nonzero_is_insufficient": True,
        },
        "modules": modules,
        "long_horizon_candidate_modules": sorted(long_candidates),
        "confirmed_modules": sorted(confirmed_modules),
        "positive_ecological_output_modules": sorted(
            set(positive_ecological_modules)
        ),
        "lineage_guard": guard,
        "duplication_ready_modules": [],
        "recommendation": recommendation,
        "interpretation_boundary": (
            "A checkpoint-lineage pair is a paired causal unit, not an independent "
            "population replicate. Continuation requires a practical routed-output "
            "effect with the same direction in at least two seeds and at least two "
            "non-dominant lineage identities. Retained-cost or total-expression effects "
            "alone do not qualify a module. A confirmation plan may select modules, but "
            "must preserve every preselected checkpoint-lineage pair for each selected "
            "module; it must not cherry-pick responsive pairs. Module copy number remains "
            "blocked while the source lineage guard fails."
        ),
    }


def _plan_from_payload(payload: dict[str, Any]) -> LineagePairPlan:
    checkpoints: list[LineagePairCheckpoint] = []
    for item in payload.get("checkpoints", ()):
        lineages = tuple(LineageSelection(**value) for value in item.get("lineages", ()))
        checkpoints.append(LineagePairCheckpoint(**{**item, "lineages": lineages}))
    if not checkpoints:
        raise ValueError("embedded D2 lineage-pair plan contains no checkpoints")
    return LineagePairPlan(
        schema=str(payload.get("schema", PLAN_SCHEMA)),
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
        branches=tuple(payload.get("branches", ())),
        effect_decomposition_schema=str(
            payload.get("effect_decomposition_schema", "output-cost-total-additive-v1")
        ),
        confirmation_source_result_schema=payload.get(
            "confirmation_source_result_schema"
        ),
        confirmation_source_horizon_ticks=payload.get(
            "confirmation_source_horizon_ticks"
        ),
        confirmation_selection_rule=payload.get("confirmation_selection_rule"),
        outcome_conditioned_pair_selection=bool(
            payload.get("outcome_conditioned_pair_selection", False)
        ),
    )


def build_confirmation_plan(
    short_results: dict[str, Any],
    assessment: dict[str, Any],
    *,
    horizon_ticks: int = 300,
) -> LineagePairPlan | None:
    candidates = tuple(int(value) for value in assessment["long_horizon_candidate_modules"])
    if not candidates:
        return None
    source = _plan_from_payload(short_results["plan"])
    if horizon_ticks <= int(source.horizon_ticks):
        raise ValueError("confirmation horizon must exceed the screen horizon")
    checkpoints = tuple(
        replace(
            checkpoint,
            until_tick=int(checkpoint.checkpoint_tick) + int(horizon_ticks),
        )
        for checkpoint in source.checkpoints
    )
    return replace(
        source,
        schema=PLAN_SCHEMA,
        horizon_ticks=int(horizon_ticks),
        module_indices=candidates,
        checkpoints=checkpoints,
        confirmation_source_result_schema=str(short_results["schema"]),
        confirmation_source_horizon_ticks=int(source.horizon_ticks),
        confirmation_selection_rule=CONFIRMATION_SELECTION_RULE,
        outcome_conditioned_pair_selection=False,
    )


def _direction(value: int) -> str:
    return "positive" if value > 0 else "negative"


def render_assessment_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# D2 lineage-pair effect assessment",
        "",
        f"Schema: `{report['schema']}`",
        f"Current horizon: **{report['current_horizon_ticks']} ticks**",
        f"Paired short horizon: `{report['short_horizon_ticks']}`",
        "",
        "## Decision standard",
        "",
        "1. Exact non-zero divergence is not a practical effect.",
        "2. Only `output_routing_effect` can pass the continuation gate; cost-refund and total-expression contrasts are reported separately.",
        "3. The same material direction must occur in at least two seeds and two non-dominant lineage identities.",
        "4. A generated confirmation plan selects modules only and preserves all preselected checkpoint-lineage pairs for those modules.",
        "5. Copy number remains blocked while the source lineage guard fails.",
        "",
        "## Module decisions",
        "",
        "| Module | 120-screen | 300-confirmed | Positive ecological output | Repeated output outcomes | Cost-only |",
        "|---:|---:|---:|---:|---|---:|",
    ]
    for name, value in report["modules"].items():
        module_index = int(name.split("_")[-1])
        outcomes = (
            value["persistent_output_outcomes"]
            if report["short_horizon_ticks"] is not None
            else value["screen_output_outcomes"]
        )
        lines.append(
            f"| {module_index} | {value['screen_pass']} | {value['confirmation_pass']} | "
            f"{value['positive_ecological_output']} | "
            f"{', '.join(f'`{item}`' for item in outcomes) or 'none'} | "
            f"{value['cost_only_signal']} |"
        )
    lines.extend(["", "## Repeated routed-output evidence", ""])
    for name, value in report["modules"].items():
        findings: list[str] = []
        metrics = value["effects"]["output_routing_effect"]
        for outcome, metric in metrics.items():
            sign_key = (
                "persistent_sign"
                if report["short_horizon_ticks"] is not None
                else "replicated_sign"
            )
            passed_key = (
                "persistent_non_dominant"
                if report["short_horizon_ticks"] is not None
                else "replicated_non_dominant"
            )
            if metric[passed_key]:
                seed_key = (
                    "persistent_seed_count"
                    if report["short_horizon_ticks"] is not None
                    else "replicated_seed_count"
                )
                lineage_key = (
                    "persistent_lineage_identity_count"
                    if report["short_horizon_ticks"] is not None
                    else "replicated_lineage_identity_count"
                )
                findings.append(
                    f"`{outcome}` {_direction(int(metric[sign_key]))} "
                    f"({metric[seed_key]} seeds, "
                    f"{metric[lineage_key]} non-dominant lineage identities)"
                )
        lines.append(f"- `{name}`: " + ("; ".join(findings) if findings else "none"))
    guard = report["lineage_guard"]
    lines.extend(
        [
            "",
            "## Lineage guard",
            "",
            f"- median effective lineages: `{guard['median_effective_lineages']}`",
            f"- minimum effective lineages: `{guard['minimum_effective_lineages']}`",
            f"- median dominant share: `{guard['median_dominant_lineage_fraction']}`",
            f"- dominant-lineage risk: `{guard['dominant_lineage_risk']}`",
            "",
            "## Recommendation",
            "",
            f"`{report['recommendation']}`",
            "",
            f"300-tick candidate modules: `{', '.join(map(str, report['long_horizon_candidate_modules'])) or 'none'}`",
            "",
            report["interpretation_boundary"],
            "",
        ]
    )
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Assess lineage-paired D2 module effects and generate a non-cherry-picked "
            "300-tick confirmation plan"
        )
    )
    parser.add_argument("--results", help="Single result, normally the 120-tick screen")
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
        short = _load_results(args.results)
        current = short
        paired_short = None
    else:
        if not args.short_results or not args.long_results:
            raise ValueError(
                "provide --results for a single screen, or both --short-results and --long-results"
            )
        current = _load_results(args.long_results)
        paired_short = _load_results(args.short_results)
        short = paired_short
    report = assess_lineage_pair_results(current, short_results=paired_short)
    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=True)
    (output / "d2_lineage_pair_assessment.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (output / "d2_lineage_pair_assessment.md").write_text(
        render_assessment_markdown(report), encoding="utf-8"
    )
    confirmation_plan = None
    if paired_short is None and short is not None:
        confirmation_plan = build_confirmation_plan(
            short,
            report,
            horizon_ticks=args.confirmation_horizon,
        )
    if confirmation_plan is not None:
        (output / "d2_lineage_pair_confirmation_plan.json").write_text(
            json.dumps(asdict(confirmation_plan), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        (output / "d2_lineage_pair_confirmation_plan.md").write_text(
            render_plan_markdown(confirmation_plan), encoding="utf-8"
        )
    print(
        json.dumps(
            {
                "passed": True,
                "recommendation": report["recommendation"],
                "confirmation_plan_written": confirmation_plan is not None,
            }
        )
    )


if __name__ == "__main__":
    main()
