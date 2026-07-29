"""Audit matched D3 acute-response panels across scales without pseudoreplication.

The independent replication unit is the seed. Checkpoints are nested repeated
panels and observation windows are repeated measurements within a checkpoint.
Movement events are never treated as independent replicates. A reversed active
branch is causally interpretable only when a reversed-and-neutral branch exists
under the same checkpoint and observation orientation.
"""
from __future__ import annotations

import argparse
import itertools
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable, Sequence

import numpy as np

SCHEMA = "d3-response-scale-audit-v2"
SUPPORTED_RESULTS = {
    "d3-processing-response-panel-results-v1",
    "d3-processing-response-panel-results-v2",
}
METRICS = {
    "resource_move_mean_support_gain": "mean_support_gain",
    "resource_move_mean_alignment_cosine": "mean_alignment_cosine",
    "resource_move_positive_support_gain_fraction": "positive_gain_fraction",
}
WINDOW_ACCUMULATORS = {
    "mean_support_gain": (
        "resource_move_support_gain_sum",
        "resource_move_count",
    ),
    "mean_alignment_cosine": (
        "resource_move_alignment_cosine_sum",
        "resource_move_alignment_cosine_count",
    ),
    "positive_gain_fraction": (
        "resource_move_support_gain_positive",
        "resource_move_count",
    ),
}
ORIENTATIONS = ("original", "reversed")


@dataclass(frozen=True)
class ReplicationRequirements:
    """Interpretation gates that never feed back into the simulated world."""

    minimum_independent_seeds: int = 8
    minimum_positive_seed_fraction: float = 0.75
    minimum_both_orientation_positive_seed_fraction: float = 0.75

    def validate(self) -> None:
        if self.minimum_independent_seeds <= 0:
            raise ValueError("minimum_independent_seeds must be positive")
        for name, value in (
            ("minimum_positive_seed_fraction", self.minimum_positive_seed_fraction),
            (
                "minimum_both_orientation_positive_seed_fraction",
                self.minimum_both_orientation_positive_seed_fraction,
            ),
        ):
            if not 0.0 < value <= 1.0:
                raise ValueError(f"{name} must be in (0, 1]")


def parse_result_spec(value: str) -> tuple[str, Path]:
    if "=" not in value:
        path = Path(value)
        return path.stem, path
    label, raw_path = value.split("=", 1)
    if not label.strip():
        raise ValueError("result label cannot be empty")
    return label.strip(), Path(raw_path)


def _branch_map(panel: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {row["branch"]: row for row in panel.get("branches", [])}


def _eligible(panel: dict[str, Any]) -> bool:
    return bool(
        panel.get(
            "acute_quartet_analysis_eligible",
            panel.get("acute_triplet_analysis_eligible", False),
        )
    )


def _effect(
    branches: dict[str, dict[str, Any]], active: str, neutral: str, metric: str
) -> float:
    return float(
        branches[active]["response_summary"][metric]
        - branches[neutral]["response_summary"][metric]
    )


def _safe_mean(values: Sequence[float]) -> float | None:
    return float(np.mean(values)) if values else None


def _safe_median(values: Sequence[float]) -> float | None:
    return float(np.median(values)) if values else None


def _positive_fraction(values: Sequence[float]) -> float | None:
    return float(np.mean(np.asarray(values, dtype=np.float64) > 0.0)) if values else None


def _leave_one_out_range(values: Sequence[float]) -> dict[str, float | None]:
    array = np.asarray(values, dtype=np.float64)
    if array.size < 2:
        return {"minimum": None, "maximum": None}
    candidates = [float(np.mean(np.delete(array, index))) for index in range(array.size)]
    return {"minimum": min(candidates), "maximum": max(candidates)}


def _exact_sign_flip_p(values: Sequence[float]) -> dict[str, Any]:
    """Return an exact two-sided seed-level sign-flip diagnostic.

    This is descriptive only. It is never the sole interpretation gate and is
    deliberately omitted above 20 independent seeds to avoid exponential work.
    """

    array = np.asarray(values, dtype=np.float64)
    if array.size == 0:
        return {"value": None, "method": "not-computed-no-seeds"}
    if array.size > 20:
        return {"value": None, "method": "not-computed-more-than-20-seeds"}
    observed = abs(float(np.mean(array)))
    exceed = 0
    total = 0
    tolerance = np.finfo(np.float64).eps * max(1.0, observed) * 16.0
    for signs in itertools.product((-1.0, 1.0), repeat=int(array.size)):
        candidate = abs(float(np.mean(array * np.asarray(signs, dtype=np.float64))))
        exceed += int(candidate + tolerance >= observed)
        total += 1
    return {
        "value": float(exceed / total),
        "method": "exact-two-sided-seed-sign-flip-v1",
        "enumerated_assignments": total,
    }


def _trajectory_windows(branch: dict[str, Any]) -> list[dict[str, Any]]:
    trajectory = branch.get("response_trajectory") or []
    if len(trajectory) < 2:
        return []
    result: list[dict[str, Any]] = []
    ordered = sorted(trajectory, key=lambda row: int(row["tick"]))
    for previous, current in zip(ordered, ordered[1:], strict=False):
        before = previous.get("cumulative", {})
        after = current.get("cumulative", {})
        metrics: dict[str, float | None] = {}
        for output_key, (numerator_key, denominator_key) in WINDOW_ACCUMULATORS.items():
            if not {
                numerator_key,
                denominator_key,
            }.issubset(before) or not {numerator_key, denominator_key}.issubset(after):
                metrics[output_key] = None
                continue
            numerator = float(after[numerator_key]) - float(before[numerator_key])
            denominator = float(after[denominator_key]) - float(before[denominator_key])
            metrics[output_key] = numerator / denominator if denominator > 0.0 else None
        result.append(
            {
                "start_tick": int(previous["tick"]),
                "end_tick": int(current["tick"]),
                "metrics": metrics,
            }
        )
    return result


def _matched_window_effects(
    branches: dict[str, dict[str, Any]], matched_complete: bool
) -> list[dict[str, Any]]:
    required = {"original-support", "neutral-support"}
    if not required.issubset(branches):
        return []
    branch_windows = {
        name: {
            (row["start_tick"], row["end_tick"]): row["metrics"]
            for row in _trajectory_windows(branch)
        }
        for name, branch in branches.items()
    }
    common = set(branch_windows["original-support"]) & set(
        branch_windows["neutral-support"]
    )
    if matched_complete:
        common &= set(branch_windows["reversed-support"])
        common &= set(branch_windows["reversed-neutral-support"])
    rows: list[dict[str, Any]] = []
    for start_tick, end_tick in sorted(common):
        metrics: dict[str, dict[str, float | None]] = {}
        for output_key in WINDOW_ACCUMULATORS:
            original_active = branch_windows["original-support"][(start_tick, end_tick)][
                output_key
            ]
            original_neutral = branch_windows["neutral-support"][(start_tick, end_tick)][
                output_key
            ]
            original = (
                original_active - original_neutral
                if original_active is not None and original_neutral is not None
                else None
            )
            reversed_effect = None
            if matched_complete:
                reversed_active = branch_windows["reversed-support"][(
                    start_tick,
                    end_tick,
                )][output_key]
                reversed_neutral = branch_windows["reversed-neutral-support"][(
                    start_tick,
                    end_tick,
                )][output_key]
                if reversed_active is not None and reversed_neutral is not None:
                    reversed_effect = reversed_active - reversed_neutral
            metrics[output_key] = {
                "original": original,
                "reversed": reversed_effect,
                "reversed_minus_original": (
                    reversed_effect - original
                    if reversed_effect is not None and original is not None
                    else None
                ),
            }
        rows.append(
            {
                "start_tick": start_tick,
                "end_tick": end_tick,
                "matched_effects": metrics,
            }
        )
    return rows


def _stored_contrast_integrity(
    panel: dict[str, Any], effects: dict[str, dict[str, float | None]]
) -> bool | None:
    stored = panel.get("matched_orientation_contrasts")
    if stored is None:
        return None
    for output_key in METRICS.values():
        stored_metric = stored.get(output_key)
        if not isinstance(stored_metric, dict):
            return False
        for orientation in (*ORIENTATIONS, "reversed_minus_original"):
            expected = effects[output_key].get(orientation)
            actual = stored_metric.get(orientation)
            if expected is None and actual is None:
                continue
            if expected is None or actual is None:
                return False
            if not np.isclose(
                float(expected), float(actual), rtol=1e-9, atol=1e-12
            ):
                return False
    return True


def _metric_values(
    rows: Sequence[dict[str, Any]], output_key: str, orientation: str
) -> list[float]:
    return [
        float(row["matched_effects"][output_key][orientation])
        for row in rows
        if row["matched_effects"][output_key].get(orientation) is not None
    ]


def _window_metric_values(
    rows: Sequence[dict[str, Any]], output_key: str, orientation: str
) -> list[float]:
    values: list[float] = []
    for row in rows:
        for window in row.get("window_effects", []):
            value = window["matched_effects"][output_key].get(orientation)
            if value is not None:
                values.append(float(value))
    return values


def _seed_summary(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for seed in sorted({int(row["seed"]) for row in rows}):
        selected = [row for row in rows if int(row["seed"]) == seed]
        payload: dict[str, Any] = {
            "seed": seed,
            "eligible_checkpoint_count": len(selected),
            "checkpoint_ticks": sorted(int(row["checkpoint_tick"]) for row in selected),
            "metrics": {},
        }
        for output_key in METRICS.values():
            metric_payload: dict[str, Any] = {}
            for orientation in ORIENTATIONS:
                checkpoint_values = _metric_values(selected, output_key, orientation)
                window_values = _window_metric_values(selected, output_key, orientation)
                metric_payload[orientation] = {
                    "equal_checkpoint_mean": _safe_mean(checkpoint_values),
                    "checkpoint_median": _safe_median(checkpoint_values),
                    "positive_checkpoint_fraction": _positive_fraction(checkpoint_values),
                    "checkpoint_count": len(checkpoint_values),
                    "leave_one_checkpoint_out_mean_range": _leave_one_out_range(
                        checkpoint_values
                    ),
                    "equal_window_mean": _safe_mean(window_values),
                    "positive_window_fraction": _positive_fraction(window_values),
                    "window_count": len(window_values),
                }
                # Retain v1 flat names for callers that only consume means.
                payload[f"{orientation}_{output_key}_mean"] = _safe_mean(
                    checkpoint_values
                )
            original = metric_payload["original"]["equal_checkpoint_mean"]
            reversed_effect = metric_payload["reversed"]["equal_checkpoint_mean"]
            metric_payload["both_orientations_positive"] = bool(
                original is not None
                and reversed_effect is not None
                and original > 0.0
                and reversed_effect > 0.0
            )
            payload["metrics"][output_key] = metric_payload
        result.append(payload)
    return result


def _scale_inference(
    seed_summaries: Sequence[dict[str, Any]], requirements: ReplicationRequirements
) -> dict[str, Any]:
    requirements.validate()
    metric_payload: dict[str, Any] = {}
    for output_key in METRICS.values():
        summary: dict[str, Any] = {}
        for orientation in ORIENTATIONS:
            values = [
                float(row["metrics"][output_key][orientation]["equal_checkpoint_mean"])
                for row in seed_summaries
                if row["metrics"][output_key][orientation]["equal_checkpoint_mean"]
                is not None
            ]
            summary[orientation] = {
                "equal_seed_mean": _safe_mean(values),
                "seed_median": _safe_median(values),
                "positive_seed_count": int(sum(value > 0.0 for value in values)),
                "positive_seed_fraction": _positive_fraction(values),
                "independent_seed_count": len(values),
                "seed_mean_minimum": min(values) if values else None,
                "seed_mean_maximum": max(values) if values else None,
                "leave_one_seed_out_mean_range": _leave_one_out_range(values),
                "exact_sign_flip": _exact_sign_flip_p(values),
            }
        both = [
            bool(row["metrics"][output_key]["both_orientations_positive"])
            for row in seed_summaries
        ]
        summary["both_orientations_positive_seed_count"] = int(sum(both))
        summary["both_orientations_positive_seed_fraction"] = (
            float(np.mean(both)) if both else None
        )
        original_mean = summary["original"]["equal_seed_mean"]
        reversed_mean = summary["reversed"]["equal_seed_mean"]
        summary["orientation_common_effect"] = (
            min(float(original_mean), float(reversed_mean))
            if original_mean is not None and reversed_mean is not None
            else None
        )
        metric_payload[output_key] = summary

    seed_count = len(seed_summaries)
    gain = metric_payload["mean_support_gain"]
    independent_seed_requirement_met = seed_count >= requirements.minimum_independent_seeds
    original_positive_fraction = gain["original"]["positive_seed_fraction"]
    reversed_positive_fraction = gain["reversed"]["positive_seed_fraction"]
    both_positive_fraction = gain["both_orientations_positive_seed_fraction"]
    directional_gate = {
        "minimum_independent_seeds_met": independent_seed_requirement_met,
        "original_equal_seed_mean_positive": bool(
            gain["original"]["equal_seed_mean"] is not None
            and gain["original"]["equal_seed_mean"] > 0.0
        ),
        "reversed_equal_seed_mean_positive": bool(
            gain["reversed"]["equal_seed_mean"] is not None
            and gain["reversed"]["equal_seed_mean"] > 0.0
        ),
        "original_positive_seed_fraction_met": bool(
            original_positive_fraction is not None
            and original_positive_fraction
            >= requirements.minimum_positive_seed_fraction
        ),
        "reversed_positive_seed_fraction_met": bool(
            reversed_positive_fraction is not None
            and reversed_positive_fraction
            >= requirements.minimum_positive_seed_fraction
        ),
        "both_orientation_positive_seed_fraction_met": bool(
            both_positive_fraction is not None
            and both_positive_fraction
            >= requirements.minimum_both_orientation_positive_seed_fraction
        ),
    }
    directional_gate["eligible"] = all(directional_gate.values())
    return {
        "schema": "nested-seed-checkpoint-matched-effect-inference-v1",
        "requirements": asdict(requirements),
        "independent_seed_count": seed_count,
        "checkpoint_weighting_within_seed": "equal-checkpoint-v1",
        "seed_weighting_within_scale": "equal-seed-v1",
        "movement_event_weighting_across_panels": False,
        "metrics": metric_payload,
        "directional_replication_gate": directional_gate,
        "exact_sign_flip_is_descriptive_only": True,
    }


def audit_result(
    label: str,
    path: Path,
    *,
    requirements: ReplicationRequirements | None = None,
) -> dict[str, Any]:
    requirements = requirements or ReplicationRequirements()
    payload = json.loads(path.read_text(encoding="utf-8"))
    schema = payload.get("schema")
    if schema not in SUPPORTED_RESULTS:
        raise ValueError(f"unsupported D3 response result schema {schema!r}: {path}")
    panel_rows: list[dict[str, Any]] = []
    matched_complete_count = 0
    for panel in payload.get("panels", []):
        if panel.get("status") != "completed":
            continue
        branches = _branch_map(panel)
        names = set(branches)
        matched_complete = {
            "original-support",
            "neutral-support",
            "reversed-support",
            "reversed-neutral-support",
        }.issubset(names)
        matched_complete_count += int(matched_complete)
        effects: dict[str, dict[str, float | None]] = {}
        for metric, output_key in METRICS.items():
            original = (
                _effect(branches, "original-support", "neutral-support", metric)
                if {"original-support", "neutral-support"}.issubset(names)
                else None
            )
            reversed_effect = (
                _effect(
                    branches,
                    "reversed-support",
                    "reversed-neutral-support",
                    metric,
                )
                if matched_complete
                else None
            )
            effects[output_key] = {
                "original": original,
                "reversed": reversed_effect,
                "reversed_minus_original": (
                    reversed_effect - original
                    if reversed_effect is not None and original is not None
                    else None
                ),
            }
        branch_metrics = {
            name: {
                output_key: float(row["response_summary"][metric])
                for metric, output_key in METRICS.items()
            }
            for name, row in branches.items()
            if "response_summary" in row
        }
        interval_ledgers_valid = all(
            bool(row.get("interval_ledgers", {}).get("external_resource", {}).get("valid", True))
            and bool(
                row.get("interval_ledgers", {})
                .get("external_recycling", {})
                .get("valid", True)
            )
            for row in branches.values()
        )
        panel_rows.append(
            {
                "seed": int(panel["seed"]),
                "checkpoint_tick": int(panel["checkpoint_tick"]),
                "acute_analysis_eligible": _eligible(panel),
                "evolutionary_analysis_eligible": bool(
                    panel.get("evolutionary_checkpoint_analysis_eligible", False)
                ),
                "matched_orientation_controls_complete": matched_complete,
                "interval_ledgers_valid": interval_ledgers_valid,
                "stored_contrasts_match_recomputed": _stored_contrast_integrity(
                    panel, effects
                ),
                "matched_effects": effects,
                "window_effects": _matched_window_effects(branches, matched_complete),
                "branch_metrics": branch_metrics,
            }
        )
    eligible = [row for row in panel_rows if row["acute_analysis_eligible"]]
    matched_eligible = [
        row
        for row in eligible
        if row["matched_orientation_controls_complete"]
        and row["interval_ledgers_valid"]
        and row["stored_contrasts_match_recomputed"] is not False
    ]
    original_gain = _metric_values(eligible, "mean_support_gain", "original")
    original_values = [
        row["branch_metrics"]["original-support"]["mean_support_gain"]
        for row in eligible
        if "original-support" in row["branch_metrics"]
    ]
    neutral_values = [
        row["branch_metrics"]["neutral-support"]["mean_support_gain"]
        for row in eligible
        if "neutral-support" in row["branch_metrics"]
    ]
    tracking_correlation = None
    if len(original_values) >= 2 and len(original_values) == len(neutral_values):
        original_array = np.asarray(original_values, dtype=np.float64)
        neutral_array = np.asarray(neutral_values, dtype=np.float64)
        if float(np.std(original_array)) > 0.0 and float(np.std(neutral_array)) > 0.0:
            candidate = float(np.corrcoef(original_array, neutral_array)[0, 1])
            tracking_correlation = candidate if np.isfinite(candidate) else None
    seed_summaries = _seed_summary(matched_eligible)
    return {
        "label": label,
        "path": str(path),
        "result_schema": schema,
        "panel_count": len(payload.get("panels", [])),
        "completed_panel_count": len(panel_rows),
        "acute_analysis_eligible_panel_count": len(eligible),
        "evolutionary_analysis_eligible_checkpoint_count": sum(
            row["evolutionary_analysis_eligible"] for row in panel_rows
        ),
        "matched_orientation_control_panel_count": matched_complete_count,
        "matched_orientation_control_eligible_panel_count": len(matched_eligible),
        "original_active_neutral_gain_mean_across_eligible_panels": (
            _safe_mean(original_gain)
        ),
        "original_active_neutral_gain_max_abs_across_eligible_panels": (
            float(np.max(np.abs(original_gain))) if original_gain else None
        ),
        "original_neutral_gain_tracking_correlation_across_eligible_panels": (
            tracking_correlation
        ),
        "panels": panel_rows,
        "seed_summaries": seed_summaries,
        "matched_effect_inference": _scale_inference(seed_summaries, requirements),
    }


def build_audit(
    specs: Iterable[tuple[str, Path]],
    *,
    requirements: ReplicationRequirements | None = None,
) -> dict[str, Any]:
    requirements = requirements or ReplicationRequirements()
    requirements.validate()
    scales = [
        audit_result(label, path, requirements=requirements) for label, path in specs
    ]
    if not scales:
        raise ValueError("at least one result file is required")
    completed = sum(row["completed_panel_count"] for row in scales)
    eligible = sum(row["acute_analysis_eligible_panel_count"] for row in scales)
    matched = sum(
        row["matched_orientation_control_eligible_panel_count"] for row in scales
    )
    all_matched = matched == eligible and eligible > 0
    replicated_scales = [
        row
        for row in scales
        if row["matched_effect_inference"]["directional_replication_gate"]["eligible"]
    ]
    if eligible == 0:
        recommendation = "increase-unprotected-scale-or-revise-preregistered-checkpoints"
    elif not all_matched:
        recommendation = "rerun-eligible-panels-with-matched-orientation-neutral-controls"
    elif any(
        row["matched_effect_inference"]["independent_seed_count"]
        < requirements.minimum_independent_seeds
        for row in scales
        if row["matched_orientation_control_eligible_panel_count"] > 0
    ):
        recommendation = "collect-more-independent-seeds-with-fixed-v2-protocol"
    elif len(replicated_scales) != len(scales):
        recommendation = (
            "matched-effect-not-directionally-replicated-do-not-add-response-mechanism"
        )
    elif len(scales) < 2:
        recommendation = "repeat-matched-effect-audit-at-independent-map-scale"
    else:
        recommendation = "run-read-only-processing-opportunity-observability-audit"
    return {
        "schema": SCHEMA,
        "requirements": asdict(requirements),
        "scales": scales,
        "completed_panel_count": completed,
        "acute_analysis_eligible_panel_count": eligible,
        "matched_orientation_control_eligible_panel_count": matched,
        "all_eligible_panels_have_matched_orientation_controls": all_matched,
        "directionally_replicated_scale_count": len(replicated_scales),
        "independent_replication_unit": "seed-within-scale",
        "checkpoints_within_seed": "nested-repeated-panels",
        "observation_windows_within_checkpoint": "nested-repeated-measurements",
        "movement_events_independent_replicates": False,
        "recommendation": recommendation,
        "interpretation_boundary": (
            "Only active-minus-neutral contrasts under the same support observation "
            "orientation isolate support execution. Seed means use equal checkpoint "
            "weighting and scale means use equal seed weighting; movement counts do not "
            "increase the independent sample size. Exact sign-flip values are descriptive. "
            "No result here establishes evolutionary adaptation, migration, specialization, "
            "coexistence, or ecological roles."
        ),
    }


def render_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# D3-I nested matched-response effect audit",
        "",
        f"Schema: `{payload['schema']}`",
        "",
        "| Scale | Result schema | Panels | Acute eligible | Matched eligible | Seeds | Original gain | Reversed gain | Both-positive seed fraction | Replication gate |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in payload["scales"]:
        inference = row["matched_effect_inference"]
        gain = inference["metrics"]["mean_support_gain"]
        lines.append(
            f"| {row['label']} | {row['result_schema']} | "
            f"{row['completed_panel_count']} | "
            f"{row['acute_analysis_eligible_panel_count']} | "
            f"{row['matched_orientation_control_eligible_panel_count']} | "
            f"{inference['independent_seed_count']} | "
            f"{gain['original']['equal_seed_mean']} | "
            f"{gain['reversed']['equal_seed_mean']} | "
            f"{gain['both_orientations_positive_seed_fraction']} | "
            f"{inference['directional_replication_gate']['eligible']} |"
        )
    lines += [
        "",
        "## Replication contract",
        "",
        f"- minimum independent seeds per scale: `{payload['requirements']['minimum_independent_seeds']}`",
        f"- minimum positive seed fraction per orientation: `{payload['requirements']['minimum_positive_seed_fraction']}`",
        f"- minimum both-orientation-positive seed fraction: `{payload['requirements']['minimum_both_orientation_positive_seed_fraction']}`",
        "- checkpoints are equally weighted within each seed",
        "- seeds are equally weighted within each scale",
        "- windows and movement events are not independent replicates",
        "",
    ]
    for row in payload["scales"]:
        lines += [
            f"## {row['label']} seed summaries",
            "",
            "| Seed | Checkpoints | Original gain | Reversed gain | Original positive checkpoints | Reversed positive checkpoints | Both positive |",
            "|---:|---:|---:|---:|---:|---:|---:|",
        ]
        for seed in row["seed_summaries"]:
            metric = seed["metrics"]["mean_support_gain"]
            lines.append(
                f"| {seed['seed']} | {seed['eligible_checkpoint_count']} | "
                f"{metric['original']['equal_checkpoint_mean']} | "
                f"{metric['reversed']['equal_checkpoint_mean']} | "
                f"{metric['original']['positive_checkpoint_fraction']} | "
                f"{metric['reversed']['positive_checkpoint_fraction']} | "
                f"{metric['both_orientations_positive']} |"
            )
        lines.append("")
    lines += [
        f"Recommendation: `{payload['recommendation']}`",
        "",
        payload["interpretation_boundary"],
        "",
    ]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--result",
        action="append",
        required=True,
        help="LABEL=path/to/d3_processing_response_panel_results.json",
    )
    parser.add_argument("--output", required=True)
    parser.add_argument("--minimum-independent-seeds", type=int, default=8)
    parser.add_argument("--minimum-positive-seed-fraction", type=float, default=0.75)
    parser.add_argument(
        "--minimum-both-orientation-positive-seed-fraction",
        type=float,
        default=0.75,
    )
    args = parser.parse_args(argv)
    requirements = ReplicationRequirements(
        minimum_independent_seeds=args.minimum_independent_seeds,
        minimum_positive_seed_fraction=args.minimum_positive_seed_fraction,
        minimum_both_orientation_positive_seed_fraction=(
            args.minimum_both_orientation_positive_seed_fraction
        ),
    )
    audit = build_audit(
        (parse_result_spec(value) for value in args.result),
        requirements=requirements,
    )
    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=True)
    (output / "d3_response_scale_audit.json").write_text(
        json.dumps(audit, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    (output / "d3_response_scale_audit.md").write_text(
        render_markdown(audit), encoding="utf-8"
    )
    print(json.dumps({"recommendation": audit["recommendation"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
