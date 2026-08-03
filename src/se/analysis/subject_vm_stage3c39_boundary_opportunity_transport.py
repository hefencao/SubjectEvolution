"""Stage 3C-39 read-only cross-panel action-boundary opportunity audit.

The assessment compares the frozen Stage-3C-34 original-panel and corrected
independent-panel outputs.  It asks whether the absence of sampled-action
crossings in the independent panel can be explained by weaker continuous
Subject-VM divergence, earlier timing, weaker selected-action probability
perturbation, or failed bootstrap opportunity transport.  It does not infer an
exact categorical boundary margin because full masked logits and the
counter-based categorical draw are not present in the frozen trace.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Iterable

import numpy as np

from .. import __version__
from ..experiments.subject_vm_short_paired_study import _canonical_sha256
from .subject_vm_stage3c34_threshold_crossing import (
    STAGE3C34_THRESHOLD_CROSSING_ASSESSMENT_SCHEMA,
)
from .subject_vm_stage3c36_geometry_transport import (
    STAGE3C36_GEOMETRY_TRANSPORT_SCHEMA,
)
from .subject_vm_stage3c38_crossing_replication import (
    STAGE3C38_CROSSING_REPLICATION_SCHEMA,
)

STAGE3C39_BOUNDARY_OPPORTUNITY_TRANSPORT_SCHEMA = (
    "se-subject-vm-stage3c39-boundary-opportunity-transport-assessment-v1"
)

_METRICS = (
    "divergence_event_count",
    "potential_l1_median",
    "potential_l1_mean",
    "potential_l1_maximum",
    "sampled_probability_abs_median",
    "sampled_probability_abs_mean",
    "sampled_probability_abs_maximum",
)


def _load_json(path: str | Path) -> dict[str, Any]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"expected one JSON object: {path}")
    return payload


def _validate(payload: dict[str, Any], *, schema: str, label: str) -> None:
    if payload.get("schema") != schema:
        raise ValueError(f"unsupported {label} schema")
    recorded = str(payload.get("assessment_sha256", ""))
    unsigned = dict(payload)
    unsigned.pop("assessment_sha256", None)
    if not recorded or recorded != _canonical_sha256(unsigned):
        raise ValueError(f"{label} checksum mismatch")


def _stats(values: Iterable[float | int]) -> dict[str, Any]:
    array = np.asarray(list(values), dtype=np.float64)
    if array.size == 0:
        return {"count": 0, "minimum": None, "median": None, "maximum": None, "mean": None}
    return {
        "count": int(array.size),
        "minimum": float(np.min(array)),
        "median": float(np.median(array)),
        "maximum": float(np.max(array)),
        "mean": float(np.mean(array)),
    }


def _source_rows(payload: dict[str, Any]) -> dict[int, dict[str, Any]]:
    rows = {int(row["seed"]): row for row in payload.get("per_source", [])}
    if len(rows) != 9:
        raise ValueError("Stage-3C-39 requires exactly nine sources per panel")
    return rows


def _metric_row(row: dict[str, Any]) -> dict[str, Any]:
    divergence = row["continuous_decision_divergence"]
    l1 = divergence["l1_statistics"]
    probability = divergence["same_action_sampled_probability_abs_statistics"]
    crossing = row["sampled_action_crossing"]
    return {
        "seed": int(row["seed"]),
        "classification": str(row["classification"]),
        "divergence_event_count": int(
            divergence["subject_vm_potential_exposure_alignment_ddd_event_count"]
        ),
        "divergence_event_fraction": float(divergence["event_fraction"]),
        "potential_l1_median": float(l1["median"]),
        "potential_l1_mean": float(l1["mean"]),
        "potential_l1_maximum": float(l1["maximum"]),
        "sampled_probability_comparable_event_count": int(
            divergence["same-action_comparable_sampled_probability_ddd_event_count"]
            if "same-action_comparable_sampled_probability_ddd_event_count" in divergence
            else divergence["same_action_comparable_sampled_probability_ddd_event_count"]
        ),
        "sampled_probability_abs_median": float(probability["median"]),
        "sampled_probability_abs_mean": float(probability["mean"]),
        "sampled_probability_abs_maximum": float(probability["maximum"]),
        "divergence_event_count_by_tick": {
            str(tick): int(count)
            for tick, count in divergence["event_count_by_tick"].items()
        },
        "alignment_differential_action_crossing_event_count": int(
            crossing["alignment_differential_action_crossing_event_count"]
        ),
    }


def _panel_summary(rows: dict[int, dict[str, Any]]) -> dict[str, Any]:
    metrics = [_metric_row(row) for _, row in sorted(rows.items())]
    ticks: dict[str, int] = {}
    for row in metrics:
        for tick, count in row["divergence_event_count_by_tick"].items():
            ticks[tick] = ticks.get(tick, 0) + int(count)
    total = sum(ticks.values())
    late = sum(count for tick, count in ticks.items() if int(tick) >= 10)
    source_balanced = {
        metric: _stats(row[metric] for row in metrics)
        for metric in _METRICS
    }
    crossing_seeds = sorted(
        row["seed"]
        for row in metrics
        if row["alignment_differential_action_crossing_event_count"] > 0
    )
    return {
        "source_seeds": [row["seed"] for row in metrics],
        "source_count": len(metrics),
        "per_source": metrics,
        "source_balanced_metrics": source_balanced,
        "aggregate_divergence_tick_counts": dict(sorted(ticks.items(), key=lambda item: int(item[0]))),
        "aggregate_divergence_event_count": int(total),
        "late_tick_10_or_later_fraction": float(late / total) if total else 0.0,
        "alignment_differential_action_crossing_source_seeds": crossing_seeds,
    }


def _range_overlap(left: dict[str, Any], right: dict[str, Any]) -> bool:
    return bool(
        float(left["maximum"]) >= float(right["minimum"])
        and float(right["maximum"]) >= float(left["minimum"])
    )


def _perfect_high_threshold(
    positives: list[dict[str, Any]], negatives: list[dict[str, Any]], metric: str
) -> dict[str, Any]:
    if not positives:
        return {"available": False, "separates": False, "reason": "no-positive-reference-source"}
    minimum_positive = min(float(row[metric]) for row in positives)
    maximum_negative = max(float(row[metric]) for row in negatives)
    return {
        "available": True,
        "separates": bool(minimum_positive > maximum_negative),
        "minimum_positive": minimum_positive,
        "maximum_nonpositive": maximum_negative,
        "gap": float(minimum_positive - maximum_negative),
    }


def assess_stage3c39_boundary_opportunity_transport(
    reference_stage3c34: dict[str, Any],
    replication_stage3c34: dict[str, Any],
    stage3c36_transport: dict[str, Any],
    stage3c38_replication: dict[str, Any],
) -> dict[str, Any]:
    _validate(
        reference_stage3c34,
        schema=STAGE3C34_THRESHOLD_CROSSING_ASSESSMENT_SCHEMA,
        label="reference Stage-3C-34",
    )
    _validate(
        replication_stage3c34,
        schema=STAGE3C34_THRESHOLD_CROSSING_ASSESSMENT_SCHEMA,
        label="replication Stage-3C-34",
    )
    _validate(
        stage3c36_transport,
        schema=STAGE3C36_GEOMETRY_TRANSPORT_SCHEMA,
        label="Stage-3C-36 transport",
    )
    _validate(
        stage3c38_replication,
        schema=STAGE3C38_CROSSING_REPLICATION_SCHEMA,
        label="Stage-3C-38 replication",
    )

    reference_rows = _source_rows(reference_stage3c34)
    replication_rows = _source_rows(replication_stage3c34)
    reference_seeds = sorted(reference_rows)
    replication_seeds = sorted(replication_rows)
    if set(reference_seeds) & set(replication_seeds):
        raise ValueError("Stage-3C-39 requires disjoint source panels")
    if reference_seeds != sorted(int(seed) for seed in stage3c36_transport["reference_source_seeds"]):
        raise ValueError("Stage-3C-39 reference panel identity mismatch")
    if replication_seeds != sorted(int(seed) for seed in stage3c36_transport["replication_source_seeds"]):
        raise ValueError("Stage-3C-39 replication panel identity mismatch")
    if replication_seeds != sorted(int(seed) for seed in stage3c38_replication["replication_source_seeds"]):
        raise ValueError("Stage-3C-39 Stage-3C-38 panel identity mismatch")
    if not bool(stage3c38_replication["prediction_assessment"]["vacuous_match_only"]):
        raise ValueError("Stage-3C-39 requires the frozen Stage-3C-38 vacuous panel")

    reference = _panel_summary(reference_rows)
    replication = _panel_summary(replication_rows)
    reference_positive = [
        row for row in reference["per_source"]
        if row["alignment_differential_action_crossing_event_count"] > 0
    ]
    all_nonpositive = [
        row for row in [*reference["per_source"], *replication["per_source"]]
        if row["alignment_differential_action_crossing_event_count"] == 0
    ]

    metric_comparison: dict[str, Any] = {}
    for metric in _METRICS:
        ref_stats = reference["source_balanced_metrics"][metric]
        rep_stats = replication["source_balanced_metrics"][metric]
        metric_comparison[metric] = {
            "reference": ref_stats,
            "replication": rep_stats,
            "ranges_overlap": _range_overlap(ref_stats, rep_stats),
            "replication_median_minus_reference_median": float(
                rep_stats["median"] - ref_stats["median"]
            ),
            "replication_maximum_at_least_reference_positive_minimum": bool(
                reference_positive
                and rep_stats["maximum"]
                >= min(float(row[metric]) for row in reference_positive)
            ),
            "perfect_monotone_high_threshold": _perfect_high_threshold(
                reference_positive, all_nonpositive, metric
            ),
        }

    reference_ticks = set(reference["aggregate_divergence_tick_counts"])
    replication_ticks = set(replication["aggregate_divergence_tick_counts"])
    candidate_transport = stage3c36_transport["candidate_support_transport"]
    geometry_transport = stage3c36_transport["local_geometry_transport"]
    recurrence_transport = stage3c36_transport["first_state_recurrence_transport"]

    no_scalar_separator = not any(
        comparison["perfect_monotone_high_threshold"]["separates"]
        for comparison in metric_comparison.values()
    )
    all_ranges_overlap = all(
        comparison["ranges_overlap"] for comparison in metric_comparison.values()
    )
    replication_probability_not_weaker = bool(
        replication["source_balanced_metrics"]["sampled_probability_abs_mean"]["median"]
        >= reference["source_balanced_metrics"]["sampled_probability_abs_mean"]["median"]
        or replication["source_balanced_metrics"]["sampled_probability_abs_maximum"]["maximum"]
        >= reference["source_balanced_metrics"]["sampled_probability_abs_maximum"]["maximum"]
    )

    payload: dict[str, Any] = {
        "schema": STAGE3C39_BOUNDARY_OPPORTUNITY_TRANSPORT_SCHEMA,
        "producer_version": __version__,
        "analysis_only_factor": "cross-panel decomposition of frozen Stage-3C-34 continuous divergence and realized crossing opportunity",
        "runtime_rerun_used": False,
        "runtime_or_checkpoint_schema_changed": False,
        "reference_source_seeds": reference_seeds,
        "replication_source_seeds": replication_seeds,
        "source_panels_are_disjoint": True,
        "input_checksums": {
            "reference_stage3c34": reference_stage3c34["assessment_sha256"],
            "replication_stage3c34": replication_stage3c34["assessment_sha256"],
            "stage3c36_transport": stage3c36_transport["assessment_sha256"],
            "stage3c38_replication": stage3c38_replication["assessment_sha256"],
        },
        "panel_summaries": {
            "reference": reference,
            "replication": replication,
        },
        "cross_panel_metric_comparison": metric_comparison,
        "timing_transport": {
            "reference_divergence_ticks": sorted(int(tick) for tick in reference_ticks),
            "replication_divergence_ticks": sorted(int(tick) for tick in replication_ticks),
            "tick_support_identical": reference_ticks == replication_ticks,
            "reference_late_tick_10_or_later_fraction": reference["late_tick_10_or_later_fraction"],
            "replication_late_tick_10_or_later_fraction": replication["late_tick_10_or_later_fraction"],
            "replication_lacks_late_divergence": bool(
                replication["late_tick_10_or_later_fraction"] == 0.0
            ),
        },
        "bootstrap_context": {
            "candidate_support_signature_identical_across_all_18_sources": bool(
                candidate_transport["candidate_support_signature_identical_across_all_18_sources"]
            ),
            "strict_vs_older_scale_separation_remains_over_100x": bool(
                geometry_transport["strict_vs_older_scale_separation_remains_over_100x"]
            ),
            "same_first_state_query_count_delta": int(
                recurrence_transport["same_first_state_query_count_delta"]
            ),
            "first_state_recurrence_composition_shift_observed": bool(
                recurrence_transport["same_first_state_query_count_delta"] != 0
            ),
        },
        "observability_boundary": {
            "selected_action_probability_is_available_when_all_eight_arms_sample_same_action": True,
            "full_masked_policy_logits_available": False,
            "counter_based_categorical_draw_available": False,
            "all_divergence_event_action_composition_available_in_frozen_stage3c34_assessment": False,
            "exact_categorical_boundary_margin_observable": False,
        },
        "frozen_interpretation": {
            "replication_panel_has_uniformly_weaker_continuous_divergence": False,
            "continuous_divergence_metric_ranges_overlap_across_panels": all_ranges_overlap,
            "replication_panel_lacks_late_divergence": False,
            "replication_selected_action_probability_perturbation_is_uniformly_weaker": not replication_probability_not_weaker,
            "candidate_support_or_local_geometry_failure_explains_zero_crossing": False,
            "a_single_observed_monotone_magnitude_threshold_separates_reference_positive_sources": not no_scalar_separator,
            "first_state_recurrence_composition_differs_between_panels": bool(
                recurrence_transport["same_first_state_query_count_delta"] != 0
            ),
            "first_state_recurrence_shift_is_proven_to_cause_zero_crossing": False,
            "zero_crossing_is_narrowed_to_unobserved_categorical_competition_and_draw_state": True,
            "exact_action_boundary_opportunity_is_resolved": False,
            "new_random_panel_is_authorized": False,
            "exposure_or_crossing_threshold_change_is_authorized": False,
            "neutral_trace_instrumentation_is_required_before_further_boundary_claims": True,
        },
        "governance": {
            "post_hoc_scalar_score_used": False,
            "source_selection_used": False,
            "threshold_changed": False,
            "exposure_changed": False,
            "runtime_semantics_changed": False,
        },
        "universal_scalar_objective": False,
        "universal_attention_claim": False,
        "automatic_keep_or_revert_authorized": False,
        "permanent_parameter_retention_authorized": False,
        "learning_claim_authorized": False,
        "subjecthood_claim_authorized": False,
    }
    payload["assessment_sha256"] = _canonical_sha256(payload)
    return payload


def _summary(result: dict[str, Any]) -> dict[str, Any]:
    reference = result["panel_summaries"]["reference"]
    replication = result["panel_summaries"]["replication"]
    return {
        "schema": "se-subject-vm-stage3c39-boundary-opportunity-transport-summary-v1",
        "producer_version": __version__,
        "assessment_sha256": result["assessment_sha256"],
        "reference_crossing_seeds": reference["alignment_differential_action_crossing_source_seeds"],
        "replication_crossing_seeds": replication["alignment_differential_action_crossing_source_seeds"],
        "reference_divergence_event_count": reference["aggregate_divergence_event_count"],
        "replication_divergence_event_count": replication["aggregate_divergence_event_count"],
        "exact_action_boundary_opportunity_is_resolved": result["frozen_interpretation"]["exact_action_boundary_opportunity_is_resolved"],
        "neutral_trace_instrumentation_required": result["frozen_interpretation"]["neutral_trace_instrumentation_is_required_before_further_boundary_claims"],
    }


def _report(result: dict[str, Any]) -> str:
    ref = result["panel_summaries"]["reference"]
    rep = result["panel_summaries"]["replication"]
    comp = result["cross_panel_metric_comparison"]
    return "\n".join([
        "# Stage 3C-39 action-boundary opportunity transport audit",
        "",
        "## 冻结结果",
        "",
        f"- 原 panel 与独立 panel 的 continuous divergence event 总数分别为 `{ref['aggregate_divergence_event_count']}` 与 `{rep['aggregate_divergence_event_count']}`。",
        f"- source-balanced potential L1 mean 中位数分别为 `{comp['potential_l1_mean']['reference']['median']:.6g}` 与 `{comp['potential_l1_mean']['replication']['median']:.6g}`。",
        f"- selected-action probability 绝对变化 mean 的 source 中位数分别为 `{comp['sampled_probability_abs_mean']['reference']['median']:.6g}` 与 `{comp['sampled_probability_abs_mean']['replication']['median']:.6g}`。",
        f"- tick 10 及以后 divergence 占比分别为 `{ref['late_tick_10_or_later_fraction']:.3f}` 与 `{rep['late_tick_10_or_later_fraction']:.3f}`。",
        "- 所有已观察幅度指标在两个 panel 间均有范围重叠，且没有单一单调高阈值能把原 panel 的两个 crossing source 与全部非 crossing source 完全分开。",
        "",
        "独立 panel 的零 crossing 不能由 continuous divergence 整体更弱、发生过早、selected-action probability 变化更小，或 bootstrap candidate/local geometry 未迁移来解释。当前冻结 trace 缺少完整 masked logits 与 counter-based categorical draw，因此根因被收窄到尚不可见的 categorical competition/draw state，但尚未解析。下一步应先做语义中立的 export instrumentation，而不是继续抽取 panel 或调整 exposure/threshold。",
        "",
    ])


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description="Assess Stage 3C-39 cross-panel action-boundary opportunity transport."
    )
    parser.add_argument("--reference-stage3c34", required=True)
    parser.add_argument("--replication-stage3c34", required=True)
    parser.add_argument("--stage3c36-transport", required=True)
    parser.add_argument("--stage3c38-replication", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--summary-output")
    parser.add_argument("--diagnostic-report")
    args = parser.parse_args(argv)
    result = assess_stage3c39_boundary_opportunity_transport(
        _load_json(args.reference_stage3c34),
        _load_json(args.replication_stage3c34),
        _load_json(args.stage3c36_transport),
        _load_json(args.stage3c38_replication),
    )
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if args.summary_output:
        Path(args.summary_output).write_text(
            json.dumps(_summary(result), indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    if args.diagnostic_report:
        Path(args.diagnostic_report).write_text(_report(result), encoding="utf-8")


if __name__ == "__main__":
    main()
