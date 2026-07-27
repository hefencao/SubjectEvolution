"""D2 module effect qualification across paired audit horizons.

The assessment separates exact numerical divergence, practical downstream
magnitude, checkpoint replication, phase-conditioned effects, and immediate
causal footprint at the fixed harvest interface.  It deliberately does not
turn endpoint chaos into a claim of module function or duplication readiness.
"""

from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
import json
import math
from pathlib import Path
from typing import Any, Iterable

import numpy as np

from se.experiments.d2_module_audit import (
    MODULE_COUNT,
    RESULT_SCHEMAS,
    checkpoint_functional_footprint,
)

ASSESSMENT_SCHEMA = "d2-module-effect-assessment-v2"


@dataclass(frozen=True)
class EffectRule:
    role: str
    absolute: float
    relative: float = 0.0


# Practical thresholds are intentionally larger than the exact deterministic
# comparison tolerance.  They identify effects worth a longer paired branch;
# they are not biological universal constants.
EFFECT_RULES: dict[str, EffectRule] = {
    "world.alive": EffectRule("ecological", 2.0, 0.005),
    "world.mean_energy": EffectRule("process", 0.01),
    "evolution.environment_resource_effective_dimensions": EffectRule(
        "ecological", 0.02
    ),
    "derived.harvest_extraction_efficiency_window": EffectRule("mechanistic", 0.005),
    "evolution.knowledge_effective_transferred_roots": EffectRule(
        "ecological", 2.0, 0.01
    ),
    "evolution.effective_lineages": EffectRule("ecological", 0.05),
    "evolution.functional_harvest_preference_effective_dimensions": EffectRule(
        "mechanistic", 0.02
    ),
}

NUMERICAL_TOLERANCE = 1e-12
MIN_DIRECTIONAL_REPLICATES = 4
MIN_CONTEXT_REPLICATES = 2
MIN_SEEDS = 2
FOOTPRINT_CHANGED_FRACTION = 0.01
FOOTPRINT_CHANNEL_CHANGED_FRACTION = 0.005
FOOTPRINT_LINEAGE_CHANGED_FRACTION = 0.05
MIN_LINEAGE_MEMBERS = 8


def _load_results(path: str | Path) -> dict[str, Any]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if payload.get("schema") not in RESULT_SCHEMAS:
        raise ValueError(f"unsupported D2 audit result schema: {payload.get('schema')!r}")
    if not payload.get("checkpoints"):
        raise ValueError("D2 audit result contains no checkpoints")
    return payload


def _checkpoint_key(item: dict[str, Any]) -> tuple[str, str, int]:
    meta = item["checkpoint"]
    return str(meta["run_name"]), str(meta["phase"]), int(meta["checkpoint_tick"])


def _effect_names() -> tuple[str, ...]:
    return (
        "all_module_expression_effect",
        *(f"module_{index}_expression_effect" for index in range(MODULE_COUNT)),
    )


def _threshold(rule: EffectRule, baseline: float) -> float:
    return max(float(rule.absolute), float(rule.relative) * abs(float(baseline)))


def _sign(value: float) -> int:
    if value > NUMERICAL_TOLERANCE:
        return 1
    if value < -NUMERICAL_TOLERANCE:
        return -1
    return 0


def _seed_count(rows: Iterable[dict[str, Any]], sign: int | None = None) -> int:
    names = {
        str(row["run_name"])
        for row in rows
        if sign is None or int(row["sign"]) == sign
    }
    return len(names)


def _metric_assessment(
    effect_name: str,
    metric: str,
    short_by_key: dict[tuple[str, str, int], dict[str, Any]] | None,
    long_items: list[dict[str, Any]],
) -> dict[str, Any]:
    rule = EFFECT_RULES[metric]
    rows: list[dict[str, Any]] = []
    for checkpoint in long_items:
        key = _checkpoint_key(checkpoint)
        baseline = float(checkpoint["branches"]["baseline"]["outcomes"][metric])
        value = float(checkpoint["effects"][effect_name][metric])
        threshold = _threshold(rule, baseline)
        short_value = None
        short_material = None
        same_sign_across_horizons = None
        if short_by_key is not None and key in short_by_key:
            short_checkpoint = short_by_key[key]
            if metric in short_checkpoint["effects"][effect_name]:
                short_value = float(short_checkpoint["effects"][effect_name][metric])
                short_baseline = float(
                    short_checkpoint["branches"]["baseline"]["outcomes"][metric]
                )
                short_threshold = _threshold(rule, short_baseline)
                short_material = abs(short_value) >= short_threshold
                same_sign_across_horizons = bool(
                    _sign(short_value) != 0 and _sign(short_value) == _sign(value)
                )
        rows.append(
            {
                "run_name": key[0],
                "phase": key[1],
                "checkpoint_tick": key[2],
                "baseline": baseline,
                "effect": value,
                "threshold": threshold,
                "sign": _sign(value),
                "numerically_nonzero": abs(value) > NUMERICAL_TOLERANCE,
                "material": abs(value) >= threshold,
                "short_effect": short_value,
                "short_material": short_material,
                "same_sign_across_horizons": same_sign_across_horizons,
            }
        )

    material = [row for row in rows if row["material"]]
    positive = [row for row in material if row["sign"] > 0]
    negative = [row for row in material if row["sign"] < 0]
    directional_sign = 0
    directional_rows: list[dict[str, Any]] = []
    if len(positive) >= MIN_DIRECTIONAL_REPLICATES and _seed_count(positive, 1) >= MIN_SEEDS:
        directional_sign = 1
        directional_rows = positive
    elif len(negative) >= MIN_DIRECTIONAL_REPLICATES and _seed_count(negative, -1) >= MIN_SEEDS:
        directional_sign = -1
        directional_rows = negative

    phase_replication: dict[str, Any] = {}
    for phase in sorted({str(row["phase"]) for row in rows}):
        phase_rows = [row for row in material if row["phase"] == phase]
        pos = [row for row in phase_rows if row["sign"] > 0]
        neg = [row for row in phase_rows if row["sign"] < 0]
        phase_sign = 0
        if len(pos) >= MIN_CONTEXT_REPLICATES and _seed_count(pos, 1) >= MIN_SEEDS:
            phase_sign = 1
        elif len(neg) >= MIN_CONTEXT_REPLICATES and _seed_count(neg, -1) >= MIN_SEEDS:
            phase_sign = -1
        phase_replication[phase] = {
            "material_count": len(phase_rows),
            "positive_count": len(pos),
            "negative_count": len(neg),
            "replicated_sign": phase_sign,
        }
    replicated_phase_signs = {
        data["replicated_sign"]
        for data in phase_replication.values()
        if data["replicated_sign"] != 0
    }
    phase_conditioned = bool(replicated_phase_signs)
    phase_reversal = replicated_phase_signs == {-1, 1}

    horizon_pairs = [
        row
        for row in rows
        if row["short_effect"] is not None
        and row["material"]
        and row["short_material"]
    ]
    same_horizon_sign = sum(bool(row["same_sign_across_horizons"]) for row in horizon_pairs)
    grown = sum(
        abs(float(row["effect"])) >= abs(float(row["short_effect"]))
        for row in rows
        if row["short_effect"] is not None and row["material"]
    )

    return {
        "role": rule.role,
        "rule": asdict(rule),
        "rows": rows,
        "numerically_nonzero_count": sum(row["numerically_nonzero"] for row in rows),
        "material_count": len(material),
        "positive_material_count": len(positive),
        "negative_material_count": len(negative),
        "material_seed_count": _seed_count(material),
        "directionally_replicated": directional_sign != 0,
        "directional_sign": directional_sign,
        "directional_seed_count": _seed_count(directional_rows, directional_sign)
        if directional_rows
        else 0,
        "phase_replication": phase_replication,
        "phase_conditioned": phase_conditioned,
        "phase_reversal": phase_reversal,
        "paired_horizon_material_count": len(horizon_pairs),
        "paired_horizon_same_sign_count": same_horizon_sign,
        "longer_horizon_growth_count": grown,
    }


def _embedded_or_refreshed_footprints(
    long_results: dict[str, Any],
    *,
    refresh: bool,
) -> dict[tuple[str, str, int], dict[str, Any]]:
    footprints: dict[tuple[str, str, int], dict[str, Any]] = {}
    for checkpoint in long_results["checkpoints"]:
        key = _checkpoint_key(checkpoint)
        embedded = checkpoint.get("checkpoint_footprint")
        if embedded is not None and not refresh:
            footprints[key] = embedded
            continue
        if refresh:
            meta = checkpoint["checkpoint"]
            footprints[key] = checkpoint_functional_footprint(meta["checkpoint_path"])
    return footprints


def _footprint_assessment(
    effect_name: str,
    footprints: dict[tuple[str, str, int], dict[str, Any]],
) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    for key, footprint in sorted(footprints.items()):
        effect = footprint.get("effects", {}).get(effect_name)
        if effect is None:
            continue
        lineage_rows = [
            item
            for item in effect.get("lineages", ())
            if int(item.get("members", 0)) >= MIN_LINEAGE_MEMBERS
            and (
                float(item.get("preference_changed_fraction", 0.0))
                >= FOOTPRINT_LINEAGE_CHANGED_FRACTION
                or float(item.get("conditional_harvest_channel_changed_fraction", 0.0))
                >= FOOTPRINT_CHANNEL_CHANGED_FRACTION
            )
        ]
        material = bool(
            float(effect.get("preference_changed_fraction", 0.0))
            >= FOOTPRINT_CHANGED_FRACTION
            or float(effect.get("conditional_harvest_channel_changed_fraction", 0.0))
            >= FOOTPRINT_CHANNEL_CHANGED_FRACTION
        )
        rows.append(
            {
                "run_name": key[0],
                "phase": key[1],
                "checkpoint_tick": key[2],
                "active_entities": int(footprint.get("active_entities", 0)),
                "preference_changed_fraction": float(
                    effect.get("preference_changed_fraction", 0.0)
                ),
                "preference_total_variation_mean": float(
                    effect.get("preference_total_variation_mean", 0.0)
                ),
                "conditional_harvest_channel_changed_fraction": float(
                    effect.get("conditional_harvest_channel_changed_fraction", 0.0)
                ),
                "material": material,
                "material_lineage_count": len(lineage_rows),
            }
        )
    return {
        "available": bool(rows),
        "rows": rows,
        "material_checkpoint_count": sum(row["material"] for row in rows),
        "cross_lineage_checkpoint_count": sum(
            row["material_lineage_count"] >= 2 for row in rows
        ),
        "material_seed_count": len(
            {row["run_name"] for row in rows if row["material"]}
        ),
        "thresholds": {
            "preference_changed_fraction": FOOTPRINT_CHANGED_FRACTION,
            "conditional_harvest_channel_changed_fraction": (
                FOOTPRINT_CHANNEL_CHANGED_FRACTION
            ),
            "lineage_changed_fraction": FOOTPRINT_LINEAGE_CHANGED_FRACTION,
            "min_lineage_members": MIN_LINEAGE_MEMBERS,
        },
    }


def assess_module_audits(
    long_results: dict[str, Any],
    *,
    short_results: dict[str, Any] | None = None,
    refresh_footprints: bool = False,
) -> dict[str, Any]:
    long_items = list(long_results["checkpoints"])
    short_by_key = None
    if short_results is not None:
        short_by_key = {_checkpoint_key(item): item for item in short_results["checkpoints"]}
        long_keys = {_checkpoint_key(item) for item in long_items}
        if set(short_by_key) != long_keys:
            raise ValueError("short and long D2 audits do not contain the same checkpoints")

    footprints = _embedded_or_refreshed_footprints(
        long_results, refresh=refresh_footprints
    )
    module_results: dict[str, Any] = {}
    duplication_candidates: list[str] = []
    lineage_pair_candidates: list[str] = []
    long_horizon_candidates: list[str] = []
    for effect_name in _effect_names():
        metrics = {
            metric: _metric_assessment(
                effect_name, metric, short_by_key, long_items
            )
            for metric in EFFECT_RULES
            if all(
                metric in item["effects"].get(effect_name, {})
                and metric in item["branches"]["baseline"]["outcomes"]
                for item in long_items
            )
        }
        footprint = _footprint_assessment(effect_name, footprints)
        robust_mechanistic = any(
            value["role"] == "mechanistic" and value["directionally_replicated"]
            for value in metrics.values()
        )
        robust_ecological = any(
            value["role"] == "ecological" and value["directionally_replicated"]
            for value in metrics.values()
        )
        contextual_ecological = any(
            value["role"] == "ecological" and value["phase_conditioned"]
            for value in metrics.values()
        )
        local_material = any(value["material_count"] >= 2 for value in metrics.values())
        footprint_ready = bool(
            footprint["available"]
            and footprint["material_checkpoint_count"] >= 2
            and footprint["material_seed_count"] >= MIN_SEEDS
        )
        cross_lineage = bool(
            footprint_ready and footprint["cross_lineage_checkpoint_count"] >= 2
        )
        positive_persistence = any(
            value["role"] == "ecological"
            and value["positive_material_count"] >= MIN_CONTEXT_REPLICATES
            and value["material_seed_count"] >= MIN_SEEDS
            for value in metrics.values()
        )
        duplication_ready = bool(
            effect_name != "all_module_expression_effect"
            and cross_lineage
            and positive_persistence
            and (robust_ecological or contextual_ecological)
        )
        if duplication_ready:
            duplication_candidates.append(effect_name)
        lineage_pair_ready = bool(
            effect_name != "all_module_expression_effect"
            and cross_lineage
            and robust_mechanistic
            and positive_persistence
            and (robust_ecological or contextual_ecological)
        )
        if lineage_pair_ready:
            lineage_pair_candidates.append(effect_name)

        if robust_ecological:
            classification = "replicated-ecological-effect"
        elif contextual_ecological:
            classification = "replicated-context-dependent-effect"
        elif robust_mechanistic:
            classification = "replicated-mechanistic-only"
        elif local_material:
            classification = "local-or-path-dependent-effect"
        else:
            classification = "no-practical-effect-detected"
        if not footprint["available"]:
            classification = f"provisional-{classification}"

        short_screen = any(
            value["material_count"] >= 2 for value in metrics.values()
        )
        if short_results is not None and short_screen:
            long_horizon_candidates.append(effect_name)

        module_results[effect_name] = {
            "classification": classification,
            "metrics": metrics,
            "checkpoint_footprint": footprint,
            "robust_mechanistic": robust_mechanistic,
            "robust_ecological": robust_ecological,
            "contextual_ecological": contextual_ecological,
            "footprint_ready": footprint_ready,
            "cross_lineage_footprint": cross_lineage,
            "positive_ecological_persistence": positive_persistence,
            "lineage_pair_ready": lineage_pair_ready,
            "duplication_ready": duplication_ready,
        }

    baseline_lineages = [
        float(
            item["branches"]["baseline"]["outcomes"].get(
                "evolution.effective_lineages", 0.0
            )
        )
        for item in long_items
    ]
    lineage_guard = {
        "median_effective_lineages": float(np.median(baseline_lineages)),
        "minimum_effective_lineages": float(np.min(baseline_lineages)),
        "dominant_lineage_risk": bool(np.median(baseline_lineages) < 4.0),
        "threshold": 4.0,
    }
    if lineage_guard["dominant_lineage_risk"]:
        duplication_candidates = []
        for value in module_results.values():
            value["duplication_ready"] = False

    long_horizon = int(long_results["plan"]["horizon_ticks"])
    if short_results is None and long_horizon < 300:
        any_screen = any(
            any(metric["material_count"] >= 2 for metric in value["metrics"].values())
            for value in module_results.values()
        )
        recommendation = (
            "run-300-tick-confirmation"
            if any_screen
            else "stop-and-redesign-before-longer-audit"
        )
    elif not footprints:
        recommendation = "refresh-immediate-footprints-before-duplication-decision"
    elif lineage_guard["dominant_lineage_risk"] and lineage_pair_candidates:
        recommendation = "run-lineage-balanced-paired-audit-before-duplication"
    else:
        recommendation = (
            "module-duplication-remains-blocked"
            if not duplication_candidates
            else "module-specific-copy-number-experiment-may-be-preregistered"
        )
    report = {
        "schema": ASSESSMENT_SCHEMA,
        "short_result_schema": short_results.get("schema") if short_results else None,
        "long_result_schema": long_results.get("schema"),
        "short_horizon_ticks": (
            int(short_results["plan"]["horizon_ticks"]) if short_results else None
        ),
        "long_horizon_ticks": long_horizon,
        "checkpoint_count": len(long_items),
        "effect_rules": {key: asdict(value) for key, value in EFFECT_RULES.items()},
        "module_effects": module_results,
        "lineage_guard": lineage_guard,
        "short_screen_long_horizon_candidates": sorted(set(long_horizon_candidates)),
        "lineage_pair_candidates": sorted(set(lineage_pair_candidates)),
        "duplication_candidates": duplication_candidates,
        "recommendation": recommendation,
        "interpretation_boundary": (
            "A numerical difference is not automatically a practical effect. Practical "
            "thresholds screen deterministic paired branches; replication and direct "
            "checkpoint footprint are separate requirements. Endpoint sign changes may "
            "reflect genuine context dependence or amplified trajectory divergence. "
            "Duplication remains blocked when footprint is unavailable, effects are not "
            "cross-lineage, or the source population is lineage-dominated. When direct "
            "cross-lineage effects exist but the lineage guard fails, the next admissible "
            "step is a lineage-balanced paired audit, not module copy-number expansion."
        ),
    }
    return report


def render_assessment_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# D2 module effect assessment",
        "",
        f"Schema: `{report['schema']}`",
        f"Short / long horizon: `{report.get('short_horizon_ticks')}` / `{report['long_horizon_ticks']}` ticks",
        f"Checkpoint conditions: **{report['checkpoint_count']}**",
        "",
        "## Decision standard",
        "",
        "1. Exact non-zero values only establish deterministic branch divergence.",
        "2. Practical thresholds identify effects large enough to interpret.",
        "3. A repeated effect requires the same material direction in at least four checkpoint conditions and at least two seeds, or a phase-specific direction in at least two seeds.",
        "4. Direct footprint requires a material immediate change at the fixed harvest interface.",
        "5. Module duplication additionally requires cross-lineage footprint, positive ecological persistence in at least two seeds, and no dominant-lineage guard failure.",
        "",
        "### Practical effect thresholds",
        "",
        "| Outcome | Role | Absolute threshold | Relative threshold |",
        "|---|---|---:|---:|",
    ]
    for metric, rule in EFFECT_RULES.items():
        lines.append(
            f"| `{metric}` | {rule.role} | {rule.absolute:.6g} | {rule.relative:.4%} |"
        )
    lines.extend(
        [
            "",
            "| Effect | Classification | Mechanistic | Ecological | Contextual | Footprint | Cross-lineage | Lineage-pair | Duplication |",
            "|---|---|---:|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for name, value in report["module_effects"].items():
        lines.append(
            f"| `{name}` | {value['classification']} | "
            f"{value['robust_mechanistic']} | {value['robust_ecological']} | "
            f"{value['contextual_ecological']} | {value['footprint_ready']} | "
            f"{value['cross_lineage_footprint']} | {value['lineage_pair_ready']} | "
            f"{value['duplication_ready']} |"
        )
    lines.extend(["", "## Replicated outcome directions", ""] )
    for name, value in report["module_effects"].items():
        findings: list[str] = []
        for metric, metric_value in value["metrics"].items():
            if metric_value["directionally_replicated"]:
                direction = "positive" if metric_value["directional_sign"] > 0 else "negative"
                findings.append(
                    f"`{metric}` {direction} ({max(metric_value['positive_material_count'], metric_value['negative_material_count'])}/{len(metric_value['rows'])} same-direction; {metric_value['material_count']}/{len(metric_value['rows'])} material)"
                )
            elif metric_value["phase_conditioned"]:
                findings.append(f"`{metric}` phase/context dependent")
        lines.append(
            f"- `{name}`: " + ("; ".join(findings) if findings else "no replicated practical outcome")
        )
    lines.extend(
        [
            "",
            "## Lineage guard",
            "",
            f"- median effective lineages: `{report['lineage_guard']['median_effective_lineages']:.4f}`",
            f"- minimum effective lineages: `{report['lineage_guard']['minimum_effective_lineages']:.4f}`",
            f"- dominant-lineage risk: `{report['lineage_guard']['dominant_lineage_risk']}`",
            "",
            "## Recommendation",
            "",
            f"`{report['recommendation']}`",
            "",
            f"Lineage-pair candidates: `{', '.join(report.get('lineage_pair_candidates', ())) or 'none'}`",
            "",
            report["interpretation_boundary"],
            "",
        ]
    )
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Assess short/long D2 module audits with explicit effect thresholds"
    )
    parser.add_argument("--results", help="Assess a single audit result, typically the initial 120-tick screen.")
    parser.add_argument("--short-results")
    parser.add_argument("--long-results")
    parser.add_argument("--output", required=True)
    parser.add_argument(
        "--refresh-footprints",
        action="store_true",
        help="Load referenced source checkpoints and compute immediate lineage-resolved harvest footprints without rerunning branches.",
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    if args.results and (args.short_results or args.long_results):
        raise ValueError("--results cannot be combined with --short-results/--long-results")
    if args.results:
        short = None
        long = _load_results(args.results)
    else:
        if not args.long_results:
            raise ValueError("provide --results or --long-results")
        short = _load_results(args.short_results) if args.short_results else None
        long = _load_results(args.long_results)
    report = assess_module_audits(
        long,
        short_results=short,
        refresh_footprints=args.refresh_footprints,
    )
    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=True)
    (output / "d2_module_effect_assessment.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (output / "d2_module_effect_assessment.md").write_text(
        render_assessment_markdown(report), encoding="utf-8"
    )
    print(json.dumps({"passed": True, "recommendation": report["recommendation"]}))


if __name__ == "__main__":
    main()
