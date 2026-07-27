"""Assess temporal mediation of lineage-conditioned D2 module output effects."""

from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
import json
from pathlib import Path
from typing import Any, Iterable

import numpy as np

from se.experiments.d2_lineage_mediation import RESULT_SCHEMA

ASSESSMENT_SCHEMA = "d2-lineage-mediation-assessment-v1"
NUMERICAL_TOLERANCE = 1e-12
MIN_SEEDS = 2
MIN_NON_DOMINANT_LINEAGE_IDENTITIES = 2
LINEAGE_GUARD_EFFECTIVE_COUNT = 4.0


@dataclass(frozen=True)
class MediationEffectRule:
    role: str
    absolute: float
    relative: float = 0.0


EFFECT_RULES: dict[str, MediationEffectRule] = {
    "world.alive": MediationEffectRule("ecological", 2.0, 0.005),
    "world.mean_energy": MediationEffectRule("process", 0.01),
    "world.total_energy": MediationEffectRule("process", 2.0, 0.005),
    "target_lineage.alive": MediationEffectRule("ecological", 1.0, 0.005),
    "target_lineage.source_survivors": MediationEffectRule("ecological", 1.0, 0.005),
    "target_lineage.descendants_alive": MediationEffectRule("ecological", 1.0, 0.005),
    "target_lineage.births_since_intervention": MediationEffectRule("ecological", 1.0),
    "target_lineage.deaths_since_intervention": MediationEffectRule("ecological", 1.0),
    "target_lineage.energy_deaths_since_intervention": MediationEffectRule("ecological", 1.0),
    "target_lineage.integrity_deaths_since_intervention": MediationEffectRule("ecological", 1.0),
    "target_lineage.age_deaths_since_intervention": MediationEffectRule("ecological", 1.0),
    "target_lineage.net_population_change": MediationEffectRule("ecological", 1.0),
    "target_lineage.total_energy": MediationEffectRule("process", 1.0, 0.005),
    "target_lineage.mean_energy": MediationEffectRule("process", 0.01),
    "target_lineage.energy_q25": MediationEffectRule("process", 0.01),
    "target_lineage.energy_median": MediationEffectRule("process", 0.01),
    "target_lineage.energy_q75": MediationEffectRule("process", 0.01),
    "target_lineage.total_fertility": MediationEffectRule("process", 0.5, 0.005),
    "target_lineage.mean_fertility": MediationEffectRule("process", 0.01),
    "target_lineage.reproduction_ready_count": MediationEffectRule("ecological", 1.0),
    "target_lineage.reproduction_ready_fraction": MediationEffectRule("process", 0.01),
    "target_lineage.mean_age": MediationEffectRule("process", 0.25),
    "target_lineage.mean_generation": MediationEffectRule("process", 0.05),
    "target_lineage.max_generation": MediationEffectRule("process", 1.0),
    "target_lineage.total_material": MediationEffectRule("process", 1.0, 0.005),
    "target_lineage.total_information_store": MediationEffectRule("process", 1.0, 0.005),
    "target_lineage.harvested_energy_since_intervention": MediationEffectRule(
        "mechanistic", 1.0, 0.005
    ),
    "target_lineage.shared_energy_received_since_intervention": MediationEffectRule(
        "mechanistic", 0.5, 0.005
    ),
}

EFFECT_NAMES = (
    "output_routing_effect",
    "retained_expression_cost_effect",
    "total_expression_effect",
)


def _load_results(path: str | Path) -> dict[str, Any]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if payload.get("schema") != RESULT_SCHEMA:
        raise ValueError(f"unsupported D2 mediation results: {payload.get('schema')!r}")
    if not payload.get("checkpoints"):
        raise ValueError("D2 mediation result contains no checkpoints")
    return payload


def _threshold(rule: MediationEffectRule, baseline: float) -> float:
    return max(float(rule.absolute), float(rule.relative) * abs(float(baseline)))


def _sign(value: float) -> int:
    if value > NUMERICAL_TOLERANCE:
        return 1
    if value < -NUMERICAL_TOLERANCE:
        return -1
    return 0


def _seed_count(rows: Iterable[dict[str, Any]]) -> int:
    return len({str(row["run_name"]) for row in rows})


def _lineage_identity_count(rows: Iterable[dict[str, Any]]) -> int:
    return len({(str(row["run_name"]), int(row["lineage_id"])) for row in rows})


def _replicated_sign(rows: list[dict[str, Any]]) -> tuple[int, list[dict[str, Any]]]:
    qualified: list[tuple[int, list[dict[str, Any]]]] = []
    for sign in (1, -1):
        same = [row for row in rows if int(row["sign"]) == sign]
        if (
            _seed_count(same) >= MIN_SEEDS
            and _lineage_identity_count(same) >= MIN_NON_DOMINANT_LINEAGE_IDENTITIES
        ):
            qualified.append((sign, same))
    # Opposing directions that independently satisfy the gate are heterogeneous,
    # not a replicated common direction.
    return qualified[0] if len(qualified) == 1 else (0, [])


def _baseline_by_offset(row: dict[str, Any]) -> dict[int, dict[str, float]]:
    return {
        int(item["offset_ticks"]): {
            str(key): float(value) for key, value in item["outcomes"].items()
        }
        for item in row["branches"]["baseline"]["trajectory"]
    }


def _iter_pairs(results: dict[str, Any]) -> Iterable[dict[str, Any]]:
    for checkpoint in results.get("checkpoints", ()):
        for row in checkpoint.get("pairs", ()):
            yield row


def _metric_assessment(
    results: dict[str, Any],
    *,
    module_index: int,
    effect_name: str,
    outcome: str,
) -> dict[str, Any]:
    rule = EFFECT_RULES[outcome]
    by_offset: dict[int, list[dict[str, Any]]] = {}
    for row in _iter_pairs(results):
        if int(row["module_index"]) != module_index:
            continue
        baseline = _baseline_by_offset(row)
        pair = row["pair"]
        for offset_text, effects in row.get("effects", {}).get(effect_name, {}).items():
            if outcome not in effects:
                continue
            offset = int(offset_text)
            base = float(baseline[offset][outcome])
            effect = float(effects[outcome])
            threshold = _threshold(rule, base)
            by_offset.setdefault(offset, []).append(
                {
                    "run_name": str(pair["run_name"]),
                    "phase": str(pair["phase"]),
                    "checkpoint_tick": int(pair["checkpoint_tick"]),
                    "lineage_id": int(pair["lineage_id"]),
                    "source_members": int(pair["source_members"]),
                    "source_member_fraction": float(pair["source_member_fraction"]),
                    "source_abundance_rank": int(pair["source_abundance_rank"]),
                    "non_dominant": int(pair["source_abundance_rank"]) > 1,
                    "offset_ticks": offset,
                    "baseline": base,
                    "effect": effect,
                    "threshold": threshold,
                    "sign": _sign(effect),
                    "numerically_nonzero": abs(effect) > NUMERICAL_TOLERANCE,
                    "material": abs(effect) >= threshold,
                }
            )
    offsets: dict[str, Any] = {}
    repeated_positive: list[int] = []
    repeated_negative: list[int] = []
    for offset, rows in sorted(by_offset.items()):
        material = [row for row in rows if row["material"]]
        non_dominant = [row for row in material if row["non_dominant"]]
        replicated_sign, replicated_rows = _replicated_sign(non_dominant)
        if replicated_sign > 0:
            repeated_positive.append(offset)
        elif replicated_sign < 0:
            repeated_negative.append(offset)
        offsets[str(offset)] = {
            "rows": rows,
            "material_count": len(material),
            "material_seed_count": _seed_count(material),
            "non_dominant_material_count": len(non_dominant),
            "non_dominant_material_seed_count": _seed_count(non_dominant),
            "non_dominant_lineage_identity_count": _lineage_identity_count(non_dominant),
            "replicated_non_dominant": replicated_sign != 0,
            "replicated_sign": replicated_sign,
            "replicated_seed_count": _seed_count(replicated_rows),
            "replicated_lineage_identity_count": _lineage_identity_count(
                replicated_rows
            ),
        }
    return {
        "role": rule.role,
        "rule": asdict(rule),
        "offsets": offsets,
        "repeated_positive_offsets": repeated_positive,
        "repeated_negative_offsets": repeated_negative,
        "earliest_repeated_positive_offset": (
            min(repeated_positive) if repeated_positive else None
        ),
        "earliest_repeated_negative_offset": (
            min(repeated_negative) if repeated_negative else None
        ),
        "sign_reversal_across_offsets": bool(repeated_positive and repeated_negative),
    }


def _module_indices(results: dict[str, Any]) -> tuple[int, ...]:
    embedded = results.get("plan", {}).get("module_indices", ())
    if embedded:
        return tuple(sorted({int(value) for value in embedded}))
    return tuple(sorted({int(row["module_index"]) for row in _iter_pairs(results)}))


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
    median = float(np.median(effective))
    return {
        "available": True,
        "median_effective_lineages": median,
        "minimum_effective_lineages": float(np.min(effective)),
        "median_dominant_lineage_fraction": float(np.median(dominant)),
        "dominant_lineage_risk": median < LINEAGE_GUARD_EFFECTIVE_COUNT,
        "effective_lineage_threshold": LINEAGE_GUARD_EFFECTIVE_COUNT,
    }


def _positive(metric: dict[str, Any]) -> list[int]:
    return list(metric.get("repeated_positive_offsets", ()))


def _negative(metric: dict[str, Any]) -> list[int]:
    return list(metric.get("repeated_negative_offsets", ()))


def _earliest(values: Iterable[int]) -> int | None:
    values = tuple(int(value) for value in values)
    return min(values) if values else None


def _after(values: Iterable[int], start: int | None) -> bool:
    if start is None:
        return False
    return any(int(value) >= start for value in values)


def _classify_module(metrics: dict[str, dict[str, Any]]) -> dict[str, Any]:
    mean_energy = metrics["target_lineage.mean_energy"]
    total_energy = metrics["target_lineage.total_energy"]
    harvested = metrics["target_lineage.harvested_energy_since_intervention"]
    shared = metrics["target_lineage.shared_energy_received_since_intervention"]
    energy_start = _earliest(_positive(mean_energy))
    total_energy_support = bool(_positive(total_energy))
    harvest_start = _earliest(_positive(harvested))
    shared_start = _earliest(_positive(shared))
    harvest_precedes_or_matches = bool(
        energy_start is not None and harvest_start is not None and harvest_start <= energy_start
    )
    sharing_precedes_or_matches = bool(
        energy_start is not None and shared_start is not None and shared_start <= energy_start
    )

    positive_demography_offsets: list[int] = []
    negative_demography_offsets: list[int] = []
    for outcome in (
        "target_lineage.alive",
        "target_lineage.source_survivors",
        "target_lineage.descendants_alive",
        "target_lineage.births_since_intervention",
        "target_lineage.net_population_change",
        "target_lineage.reproduction_ready_count",
    ):
        positive_demography_offsets.extend(_positive(metrics[outcome]))
        negative_demography_offsets.extend(_negative(metrics[outcome]))
    # More deaths are adverse; fewer deaths are favorable.
    for outcome in (
        "target_lineage.deaths_since_intervention",
        "target_lineage.energy_deaths_since_intervention",
        "target_lineage.integrity_deaths_since_intervention",
        "target_lineage.age_deaths_since_intervention",
    ):
        positive_demography_offsets.extend(_negative(metrics[outcome]))
        negative_demography_offsets.extend(_positive(metrics[outcome]))
    demographic_conversion = _after(positive_demography_offsets, energy_start)
    demographic_cost = _after(negative_demography_offsets, energy_start)
    survivor_mean_only = bool(
        energy_start is not None
        and not total_energy_support
        and harvest_start is None
        and shared_start is None
    )
    sign_reversals = sorted(
        outcome
        for outcome, metric in metrics.items()
        if metric.get("sign_reversal_across_offsets")
    )
    if energy_start is None:
        classification = "mean-energy-effect-not-reproduced"
        recommendation = "stop-temporal-mediation-claim"
    elif survivor_mean_only:
        classification = "survivor-conditioned-mean-energy-signal"
        recommendation = "mean-energy-effect-remains-survivor-conditioned"
    elif demographic_cost:
        classification = "energy-demography-tradeoff"
        recommendation = "flow-energy-demography-tradeoff-confirmed"
    elif demographic_conversion:
        classification = "energy-to-demography-conversion"
        recommendation = "causal-chain-supported-but-copy-number-still-guarded"
    elif harvest_precedes_or_matches or sharing_precedes_or_matches:
        classification = "flow-to-energy-without-demographic-conversion"
        recommendation = "flow-energy-mediation-supported-no-demographic-conversion"
    elif total_energy_support:
        classification = "energy-stock-effect-with-unresolved-input-flow"
        recommendation = "energy-stock-effect-supported-mediator-unresolved"
    else:
        classification = "temporal-mediation-unresolved"
        recommendation = "temporal-mediation-unresolved"
    return {
        "classification": classification,
        "recommendation": recommendation,
        "mean_energy_earliest_positive_offset": energy_start,
        "total_energy_positive_offsets": _positive(total_energy),
        "harvest_positive_offsets": _positive(harvested),
        "shared_energy_positive_offsets": _positive(shared),
        "harvest_precedes_or_matches_mean_energy": harvest_precedes_or_matches,
        "sharing_precedes_or_matches_mean_energy": sharing_precedes_or_matches,
        "demographic_conversion_after_energy": demographic_conversion,
        "demographic_cost_after_energy": demographic_cost,
        "survivor_mean_only": survivor_mean_only,
        "sign_reversal_outcomes": sign_reversals,
    }


def assess_mediation_results(results: dict[str, Any]) -> dict[str, Any]:
    if results.get("schema") != RESULT_SCHEMA:
        raise ValueError(f"unsupported D2 mediation results: {results.get('schema')!r}")
    modules: dict[str, Any] = {}
    for module_index in _module_indices(results):
        effects: dict[str, Any] = {}
        for effect_name in EFFECT_NAMES:
            effects[effect_name] = {
                outcome: _metric_assessment(
                    results,
                    module_index=module_index,
                    effect_name=effect_name,
                    outcome=outcome,
                )
                for outcome in EFFECT_RULES
            }
        routed = effects["output_routing_effect"]
        temporal = _classify_module(routed)
        module_name = f"module_{module_index}"
        expected = (
            results.get("plan", {})
            .get("source_persistent_output_expectations", {})
            .get(module_name, {})
        )
        final_offset = max(int(value) for value in results["plan"]["observation_offsets"])
        expectation_rows: dict[str, Any] = {}
        for outcome, expected_sign in expected.items():
            metric = routed.get(outcome, {})
            offset = metric.get("offsets", {}).get(str(final_offset), {})
            observed_sign = int(offset.get("replicated_sign", 0))
            expectation_rows[str(outcome)] = {
                "expected_sign": int(expected_sign),
                "observed_final_offset_sign": observed_sign,
                "reproduced": observed_sign == int(expected_sign),
            }
        source_expectation_reproduced = bool(expectation_rows) and all(
            value["reproduced"] for value in expectation_rows.values()
        )
        if expectation_rows and not source_expectation_reproduced:
            temporal = {
                **temporal,
                "classification": "source-endpoint-effect-not-reproduced",
                "recommendation": "stop-and-audit-endpoint-reproducibility",
            }
        modules[module_name] = {
            "effects": effects,
            "source_persistent_output_expectations": expectation_rows,
            "source_expectation_reproduced_at_final_offset": source_expectation_reproduced,
            "temporal_mediation": temporal,
            "copy_number_ready": False,
        }
    guard = _lineage_guard(results)
    recommendations = sorted(
        {value["temporal_mediation"]["recommendation"] for value in modules.values()}
    )
    if guard["dominant_lineage_risk"] and any(
        value["temporal_mediation"]["demographic_conversion_after_energy"]
        for value in modules.values()
    ):
        overall = "causal-chain-supported-redesign-source-population-before-copy-number"
    elif len(recommendations) == 1:
        overall = recommendations[0]
    else:
        overall = "module-specific-temporal-mediation-outcomes"
    return {
        "schema": ASSESSMENT_SCHEMA,
        "result_schema": results.get("schema"),
        "observation_offsets": list(results["plan"]["observation_offsets"]),
        "effect_rules": {key: asdict(value) for key, value in EFFECT_RULES.items()},
        "replication_rule": {
            "effect_required": "output_routing_effect",
            "minimum_seeds": MIN_SEEDS,
            "minimum_non_dominant_lineage_identities": MIN_NON_DOMINANT_LINEAGE_IDENTITIES,
            "same_material_direction_within_offset_required": True,
            "offsets_are_not_independent_replicates": True,
            "mean_energy_requires_stock_flow_and_demography_context": True,
        },
        "modules": modules,
        "lineage_guard": guard,
        "duplication_ready_modules": [],
        "recommendation": overall,
        "interpretation_boundary": (
            "Observation offsets are repeated measurements of the same checkpoint-lineage "
            "pair and cannot inflate the replicate count. A target-lineage mean-energy "
            "difference is not interpreted as ecological improvement unless total energy, "
            "input flows and demographic conversion are reported alongside it. Copy number "
            "remains blocked independently by the source-lineage guard."
        ),
    }


def _format_offsets(values: Iterable[int]) -> str:
    values = tuple(int(value) for value in values)
    return ", ".join(map(str, values)) if values else "none"


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# D2 lineage temporal mediation assessment",
        "",
        f"Schema: `{report['schema']}`",
        f"Observation offsets: `{_format_offsets(report['observation_offsets'])}` ticks",
        "",
        "## Decision standard",
        "",
        "1. Offsets are repeated observations, not independent replicates.",
        "2. Replication is counted across seeds and non-dominant lineage identities within each offset.",
        "3. Mean energy is interpreted with total energy, harvest/share flows and demography.",
        "4. Routed-output effects qualify; retained-cost and total-expression effects remain separate.",
        "5. Module copy number remains blocked by the source-lineage guard.",
        "",
        "| Module | Source endpoint reproduced | Classification | Mean-energy onset | Harvest onset | Shared-energy onset | Demographic conversion | Demographic cost |",
        "|---:|---:|---|---:|---:|---:|---:|---:|",
    ]
    for name, value in report["modules"].items():
        module_index = int(name.split("_")[-1])
        temporal = value["temporal_mediation"]
        lines.append(
            f"| {module_index} | {value['source_expectation_reproduced_at_final_offset']} | "
            f"`{temporal['classification']}` | "
            f"{temporal['mean_energy_earliest_positive_offset']} | "
            f"{_earliest(temporal['harvest_positive_offsets'])} | "
            f"{_earliest(temporal['shared_energy_positive_offsets'])} | "
            f"{temporal['demographic_conversion_after_energy']} | "
            f"{temporal['demographic_cost_after_energy']} |"
        )
        lines.extend(
            [
                "",
                f"- `{name}` total-energy support: `{_format_offsets(temporal['total_energy_positive_offsets'])}`",
                f"- `{name}` sign reversals: `{', '.join(temporal['sign_reversal_outcomes']) or 'none'}`",
                f"- `{name}` recommendation: `{temporal['recommendation']}`",
            ]
        )
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
            report["interpretation_boundary"],
            "",
        ]
    )
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Assess temporal mediation in D2 lineage-paired module trajectories"
    )
    parser.add_argument("--results", required=True)
    parser.add_argument("--output", required=True)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    results = _load_results(args.results)
    report = assess_mediation_results(results)
    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=True)
    (output / "d2_lineage_mediation_assessment.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (output / "d2_lineage_mediation_assessment.md").write_text(
        render_markdown(report), encoding="utf-8"
    )
    print(json.dumps({"passed": True, "recommendation": report["recommendation"]}))


if __name__ == "__main__":
    main()
