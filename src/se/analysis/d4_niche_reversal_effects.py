"""Assess D4-A resource-geography × inherited-affinity factorial effects."""

from __future__ import annotations

import argparse
from dataclasses import asdict
import json
from pathlib import Path
from typing import Any

import numpy as np

from se.experiments.d4_niche_reversal import (
    PLAN_SCHEMA,
    RESULT_SCHEMA,
    NicheReversalPlan,
    build_confirmation_plan,
    load_niche_reversal_plan,
    render_plan_markdown,
)

ASSESSMENT_SCHEMA = "d4-niche-reversal-assessment-v2"
INTERACTION = "affinity_environment_interaction"
EXPOSURE_THRESHOLD = 0.01

EFFECT_RULES: dict[str, dict[str, float | str]] = {
    "world.alive": {"role": "ecological", "absolute": 2.0, "relative": 0.005},
    "world.mean_energy": {"role": "process", "absolute": 0.01, "relative": 0.0},
    "target_lineage.alive": {"role": "ecological", "absolute": 1.0, "relative": 0.005},
    "target_lineage.world_share": {"role": "ecological", "absolute": 0.005, "relative": 0.0},
    "target_lineage.mean_energy": {"role": "process", "absolute": 0.01, "relative": 0.0},
    "target_lineage.total_energy": {"role": "ecological", "absolute": 1.0, "relative": 0.005},
    "evolution.environment_resource_effective_dimensions": {
        "role": "ecological",
        "absolute": 0.02,
        "relative": 0.0,
    },
    "derived.harvest_extraction_efficiency_window": {
        "role": "mechanistic",
        "absolute": 0.005,
        "relative": 0.0,
    },
    "evolution.effective_lineages": {
        "role": "ecological",
        "absolute": 0.05,
        "relative": 0.0,
    },
    "evolution.functional_harvest_preference_effective_dimensions": {
        "role": "mechanistic",
        "absolute": 0.02,
        "relative": 0.0,
    },
}
PRIMARY_OUTCOMES = (
    "target_lineage.alive",
    "target_lineage.world_share",
    "target_lineage.total_energy",
    "target_lineage.mean_energy",
)
ECOLOGICAL_PRIMARY = (
    "target_lineage.alive",
    "target_lineage.world_share",
    "target_lineage.total_energy",
)


def _load(path: str | Path) -> dict[str, Any]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if payload.get("schema") != RESULT_SCHEMA:
        raise ValueError(f"unsupported D4-A result schema: {payload.get('schema')!r}")
    if payload.get("plan", {}).get("schema") != PLAN_SCHEMA:
        raise ValueError("D4-A result has no supported embedded plan")
    return payload


def _sign(value: float) -> int:
    return 1 if value > 0.0 else (-1 if value < 0.0 else 0)


def _threshold(baseline: float, rule: dict[str, float | str]) -> float:
    return max(float(rule["absolute"]), abs(float(baseline)) * float(rule["relative"]))


def _row_key(row: dict[str, Any]) -> tuple[str, int, int, str]:
    return (
        str(row["run_name"]),
        int(row["checkpoint_tick"]),
        int(row["lineage_id"]),
        str(row["outcome"]),
    )


def _extract_rows(result: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for checkpoint in result.get("checkpoints", ()):
        for lineage_row in checkpoint.get("lineages", ()):
            meta = lineage_row["lineage"]
            exposure = float(
                meta["source_diagnostics"][
                    "source_affinity_specific_exposure_advantage_mean"
                ]
            )
            dominant_channel = int(
                meta["source_diagnostics"]["source_affinity_dominant_channel"]
            )
            effects = lineage_row["effects"][INTERACTION]
            baseline = lineage_row["branch_outcomes"]["baseline"]
            for outcome, rule in EFFECT_RULES.items():
                if outcome not in effects or outcome not in baseline:
                    continue
                value = float(effects[outcome])
                baseline_value = float(baseline[outcome])
                threshold = _threshold(baseline_value, rule)
                material = abs(value) >= threshold
                exposure_material = abs(exposure) >= EXPOSURE_THRESHOLD
                rows.append(
                    {
                        "run_name": str(meta["run_name"]),
                        "phase": str(meta["phase"]),
                        "panel_seed": int(meta["panel_seed"]),
                        "checkpoint_tick": int(meta["checkpoint_tick"]),
                        "lineage_id": int(meta["lineage_id"]),
                        "source_members": int(meta["members"]),
                        "source_member_fraction": float(meta["member_fraction"]),
                        "source_abundance_rank": int(meta["abundance_rank"]),
                        "non_dominant": bool(meta["non_dominant"]),
                        "source_affinity_dominant_channel": dominant_channel,
                        "source_affinity_specific_exposure_advantage_mean": exposure,
                        "source_exposure_material": exposure_material,
                        "outcome": outcome,
                        "role": str(rule["role"]),
                        "baseline": baseline_value,
                        "effect": value,
                        "threshold": threshold,
                        "sign": _sign(value),
                        "material": material,
                        "exposure_aligned": bool(
                            material
                            and exposure_material
                            and _sign(value) == _sign(exposure)
                        ),
                    }
                )
    return rows


def _replication(rows: list[dict[str, Any]]) -> dict[str, Any]:
    non_dominant = [row for row in rows if row["non_dominant"] and row["material"]]
    candidates: list[dict[str, Any]] = []
    for sign in (-1, 1):
        signed = [row for row in non_dominant if row["sign"] == sign]
        seeds = {row["panel_seed"] for row in signed}
        identities = {(row["run_name"], row["lineage_id"]) for row in signed}
        candidates.append(
            {
                "sign": sign,
                "rows": signed,
                "seed_count": len(seeds),
                "lineage_identity_count": len(identities),
                "replicated": len(seeds) >= 2 and len(identities) >= 2,
            }
        )
    selected = max(
        candidates,
        key=lambda item: (
            bool(item["replicated"]),
            int(item["seed_count"]),
            int(item["lineage_identity_count"]),
        ),
    )
    aligned = [row for row in non_dominant if row["exposure_aligned"]]
    aligned_seeds = {row["panel_seed"] for row in aligned}
    aligned_identities = {(row["run_name"], row["lineage_id"]) for row in aligned}
    aligned_channels = {row["source_affinity_dominant_channel"] for row in aligned}
    return {
        "material_count": len([row for row in rows if row["material"]]),
        "material_seed_count": len({row["panel_seed"] for row in rows if row["material"]}),
        "non_dominant_material_count": len(non_dominant),
        "non_dominant_material_seed_count": len({row["panel_seed"] for row in non_dominant}),
        "non_dominant_lineage_identity_count": len(
            {(row["run_name"], row["lineage_id"]) for row in non_dominant}
        ),
        "replicated_non_dominant": bool(selected["replicated"]),
        "replicated_sign": int(selected["sign"]) if selected["replicated"] else 0,
        "replicated_seed_count": int(selected["seed_count"]) if selected["replicated"] else 0,
        "replicated_lineage_identity_count": (
            int(selected["lineage_identity_count"]) if selected["replicated"] else 0
        ),
        "exposure_aligned_count": len(aligned),
        "exposure_aligned_seed_count": len(aligned_seeds),
        "exposure_aligned_lineage_identity_count": len(aligned_identities),
        "exposure_aligned_dominant_channel_count": len(aligned_channels),
        "exposure_aligned_replicated": bool(
            len(aligned_seeds) >= 2
            and len(aligned_identities) >= 2
            and len(aligned_channels) >= 2
        ),
    }


def _with_persistence(
    current_rows: list[dict[str, Any]],
    short_rows: list[dict[str, Any]] | None,
) -> list[dict[str, Any]]:
    if short_rows is None:
        return current_rows
    short_by_key = {_row_key(row): row for row in short_rows}
    result: list[dict[str, Any]] = []
    for row in current_rows:
        previous = short_by_key.get(_row_key(row))
        persistent = bool(
            previous is not None
            and row["material"]
            and previous["material"]
            and row["sign"] != 0
            and row["sign"] == previous["sign"]
        )
        result.append(
            {
                **row,
                "short_effect": previous["effect"] if previous is not None else None,
                "short_material": previous["material"] if previous is not None else False,
                "same_sign_across_horizons": bool(
                    previous is not None
                    and row["sign"] != 0
                    and row["sign"] == previous["sign"]
                ),
                "persistent": persistent,
            }
        )
    return result


def _persistent_replication(rows: list[dict[str, Any]]) -> dict[str, Any]:
    candidates = [row for row in rows if row.get("persistent") and row["non_dominant"]]
    for sign in (-1, 1):
        signed = [row for row in candidates if row["sign"] == sign]
        seeds = {row["panel_seed"] for row in signed}
        identities = {(row["run_name"], row["lineage_id"]) for row in signed}
        if len(seeds) >= 2 and len(identities) >= 2:
            return {
                "persistent_non_dominant": True,
                "persistent_sign": sign,
                "persistent_seed_count": len(seeds),
                "persistent_lineage_identity_count": len(identities),
            }
    return {
        "persistent_non_dominant": False,
        "persistent_sign": 0,
        "persistent_seed_count": 0,
        "persistent_lineage_identity_count": 0,
    }


def assess_niche_reversal_results(
    current: dict[str, Any],
    *,
    short: dict[str, Any] | None = None,
) -> dict[str, Any]:
    current_rows = _extract_rows(current)
    short_rows = _extract_rows(short) if short is not None else None
    current_rows = _with_persistence(current_rows, short_rows)
    outcomes: dict[str, Any] = {}
    for outcome in EFFECT_RULES:
        subset = [row for row in current_rows if row["outcome"] == outcome]
        if not subset:
            continue
        summary = _replication(subset)
        summary.update(_persistent_replication(subset))
        outcomes[outcome] = {
            "role": EFFECT_RULES[outcome]["role"],
            "rule": EFFECT_RULES[outcome],
            "rows": subset,
            **summary,
        }
    screen_outcomes = [
        outcome
        for outcome in PRIMARY_OUTCOMES
        if outcomes.get(outcome, {}).get("replicated_non_dominant")
    ]
    exposure_aligned_outcomes = [
        outcome
        for outcome in PRIMARY_OUTCOMES
        if outcomes.get(outcome, {}).get("exposure_aligned_replicated")
    ]
    persistent_outcomes = [
        outcome
        for outcome in PRIMARY_OUTCOMES
        if outcomes.get(outcome, {}).get("persistent_non_dominant")
    ]
    screen_pass = bool(screen_outcomes)
    confirmation_pass = bool(persistent_outcomes) if short is not None else None
    ecological_screen = [outcome for outcome in screen_outcomes if outcome in ECOLOGICAL_PRIMARY]
    ecological_persistent = [
        outcome for outcome in persistent_outcomes if outcome in ECOLOGICAL_PRIMARY
    ]
    exposures = [
        row["source_affinity_specific_exposure_advantage_mean"]
        for row in current_rows
        if row["outcome"] == "target_lineage.alive"
    ]
    dominant_channels = {
        row["source_affinity_dominant_channel"]
        for row in current_rows
        if row["outcome"] == "target_lineage.alive"
    }
    exposure_range = (
        float(max(exposures) - min(exposures)) if exposures else 0.0
    )
    exposure_material_count = sum(abs(value) >= EXPOSURE_THRESHOLD for value in exposures)
    confirmation_eligible = bool(
        screen_pass
        and exposure_aligned_outcomes
        and exposure_material_count >= 2
        and len(dominant_channels) >= 2
    )
    if short is None:
        if confirmation_eligible:
            recommendation = "run-300-tick-d4a-niche-reversal-confirmation"
        elif screen_pass:
            recommendation = (
                "causal-interaction-without-realized-differentiation-"
                "redesign-functional-substrate"
            )
        elif exposure_material_count < 2 or len(dominant_channels) < 2:
            recommendation = "resource-affinity-or-geography-contrast-too-weak-redesign-d4-source"
        else:
            recommendation = "no-replicated-affinity-environment-interaction-stop-d4a"
    elif confirmation_pass:
        recommendation = "environment-matching-causality-confirmed-proceed-to-d4b-coexistence-removal"
    else:
        recommendation = "environment-matching-not-persistent-stop-before-niche-claim"
    return {
        "schema": ASSESSMENT_SCHEMA,
        "current_result_schema": current.get("schema"),
        "short_result_schema": short.get("schema") if short is not None else None,
        "current_horizon_ticks": int(current["plan"]["horizon_ticks"]),
        "short_horizon_ticks": (
            int(short["plan"]["horizon_ticks"]) if short is not None else None
        ),
        "effect": INTERACTION,
        "effect_rules": EFFECT_RULES,
        "source_exposure_threshold": EXPOSURE_THRESHOLD,
        "source_exposure_range": exposure_range,
        "source_exposure_material_lineage_count": exposure_material_count,
        "source_affinity_dominant_channel_count": len(dominant_channels),
        "outcomes": outcomes,
        "screen_outcomes": screen_outcomes,
        "exposure_aligned_outcomes": exposure_aligned_outcomes,
        "persistent_outcomes": persistent_outcomes,
        "screen_pass": screen_pass,
        "confirmation_eligible": confirmation_eligible,
        "confirmation_pass": confirmation_pass,
        "ecological_screen_outcomes": ecological_screen,
        "ecological_persistent_outcomes": ecological_persistent,
        "causal_environment_matching_signal": screen_pass,
        "exposure_aligned_differentiation_signal": bool(exposure_aligned_outcomes),
        "stable_ecological_niche_claim": False,
        "module_copy_number_ready": False,
        "recommendation": recommendation,
        "interpretation_boundary": (
            "The affinity-environment interaction is causal because all four branches "
            "share a checkpoint and keyed random streams. Replication is counted across "
            "independent panel seeds, not across lineages or outcomes. Source exposure "
            "alignment links the intervention to preregistered phenotype-environment "
            "structure but is not an independent causal intervention. A generic factorial "
            "interaction without exposure alignment is not evidence that evolved lineages "
            "occupy distinct resource niches and does not justify a longer confirmation. "
            "Even a persistent "
            "D4-A result establishes environment matching only; stable coexistence, "
            "ecotype removal, and map-scale checks are still required before a niche claim."
        ),
    }


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# D4-A resource-geography × inherited-affinity assessment",
        "",
        f"Schema: `{report['schema']}`",
        f"Current horizon: `{report['current_horizon_ticks']}` ticks",
        f"Short horizon: `{report['short_horizon_ticks']}`",
        "",
        f"Screen pass: `{report['screen_pass']}`",
        f"Confirmation eligible: `{report['confirmation_eligible']}`",
        f"Confirmation pass: `{report['confirmation_pass']}`",
        f"Causal environment matching: `{report['causal_environment_matching_signal']}`",
        f"Exposure-aligned differentiation: `{report['exposure_aligned_differentiation_signal']}`",
        f"Stable ecological niche claim: `{report['stable_ecological_niche_claim']}`",
        f"Source exposure range: `{report['source_exposure_range']:.6f}`",
        f"Source affinity dominant channels: `{report['source_affinity_dominant_channel_count']}`",
        "",
        "## Repeated interaction outcomes",
        "",
    ]
    if report["screen_outcomes"]:
        for outcome in report["screen_outcomes"]:
            summary = report["outcomes"][outcome]
            lines.append(
                f"- `{outcome}`: sign {summary['replicated_sign']:+d}; "
                f"{summary['replicated_seed_count']} seeds; "
                f"{summary['replicated_lineage_identity_count']} non-dominant lineage identities"
            )
    else:
        lines.append("- none")
    lines.extend(["", "## Exposure-aligned outcomes", ""])
    if report["exposure_aligned_outcomes"]:
        for outcome in report["exposure_aligned_outcomes"]:
            summary = report["outcomes"][outcome]
            lines.append(
                f"- `{outcome}`: {summary['exposure_aligned_seed_count']} seeds; "
                f"{summary['exposure_aligned_lineage_identity_count']} lineages; "
                f"{summary['exposure_aligned_dominant_channel_count']} dominant affinity channels"
            )
    else:
        lines.append("- none")
    lines.extend(
        [
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
    parser = argparse.ArgumentParser(description="Assess D4-A niche reversal factorial")
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
            raise ValueError("provide --results, or both --short-results and --long-results")
        short = _load(args.short_results)
        current = _load(args.long_results)
    report = assess_niche_reversal_results(current, short=short)
    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=True)
    (output / "d4_niche_reversal_assessment.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (output / "d4_niche_reversal_assessment.md").write_text(
        render_markdown(report), encoding="utf-8"
    )
    confirmation_written = False
    if short is None and report["confirmation_eligible"]:
        plan_path = output / "_embedded_screen_plan.json"
        plan_path.write_text(
            json.dumps(current["plan"], ensure_ascii=False, indent=2), encoding="utf-8"
        )
        try:
            screen_plan = load_niche_reversal_plan(plan_path)
        finally:
            plan_path.unlink(missing_ok=True)
        confirmation = build_confirmation_plan(
            screen_plan,
            horizon_ticks=args.confirmation_horizon,
            source_result_schema=RESULT_SCHEMA,
        )
        (output / "d4_niche_reversal_confirmation_plan.json").write_text(
            json.dumps(asdict(confirmation), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        (output / "d4_niche_reversal_confirmation_plan.md").write_text(
            render_plan_markdown(confirmation), encoding="utf-8"
        )
        confirmation_written = True
    print(
        json.dumps(
            {
                "passed": True,
                "recommendation": report["recommendation"],
                "confirmation_plan_written": confirmation_written,
                "stable_ecological_niche_claim": False,
                "module_copy_number_ready": False,
            }
        )
    )


if __name__ == "__main__":
    main()
