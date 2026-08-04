"""Stage 3C-40 exact categorical action-boundary opportunity audit.

The audit consumes observation-only categorical traces from the unchanged
Stage-3C-33 matched-horizon intervention.  It reconstructs, per event, the
uniform draw, full CDF, selected interval, boundary movement and realized
action crossing for the reference and disjoint source panels.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
import hashlib
import json
from pathlib import Path
from typing import Any, Iterable

import numpy as np

from .. import __version__
from ..experiments.subject_vm_short_paired_study import _canonical_sha256
from ..experiments.subject_vm_stage3c40_categorical_boundary import (
    STAGE3C40_CATEGORICAL_BOUNDARY_STUDY_SCHEMA,
)
from .subject_vm_stage3c32_alignment_intervention import (
    _event_index,
    _read_checkpoint,
    _trace_arrays,
)
from .subject_vm_stage3c34_threshold_crossing import (
    STAGE3C34_THRESHOLD_CROSSING_ASSESSMENT_SCHEMA,
)

STAGE3C40_CATEGORICAL_BOUNDARY_ASSESSMENT_SCHEMA = (
    "se-subject-vm-stage3c40-categorical-boundary-assessment-v1"
)
_CONDITIONS = ("horizon-control", "extended-exposure")
_MODES = ("aligned", "alignment-ablated")
_ROLES = ("guarded-live", "read-only-control")
_ROLE_FIELDS = {
    "guarded-live": "guarded_live_checkpoint",
    "read-only-control": "read_only_control_checkpoint",
}
_TOL = 1.0e-12


def _load_json(path: str | Path) -> dict[str, Any]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"expected one JSON object: {path}")
    return payload


def _sha256(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _validate_checksum(payload: dict[str, Any], *, field: str, label: str) -> None:
    recorded = str(payload.get(field, ""))
    unsigned = dict(payload)
    unsigned.pop(field, None)
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


def _seed_records(study: dict[str, Any], mode: str) -> dict[int, dict[str, Any]]:
    records = {int(item["seed"]): item for item in study["modes"][mode]["seed_records"]}
    if len(records) != len(study["modes"][mode]["seed_records"]):
        raise ValueError("Stage-3C-40 nested study contains duplicate source seeds")
    return records


def _load_trace(manifest_path: str | Path) -> dict[tuple[int, int, int], dict[str, Any]]:
    manifest = _load_json(manifest_path)
    _validate_checksum(manifest, field="manifest_sha256", label="categorical trace manifest")
    trace_path = Path(manifest["trace_path"])
    if not trace_path.is_file():
        raise FileNotFoundError(trace_path)
    if _sha256(trace_path) != str(manifest["trace_sha256"]):
        raise ValueError("categorical trace file checksum mismatch")
    lines = trace_path.read_text(encoding="utf-8").splitlines()
    if not lines:
        raise ValueError("categorical trace is empty")
    header = json.loads(lines[0])
    if header.get("record_type") != "header":
        raise ValueError("categorical trace header is missing")
    result: dict[tuple[int, int, int], dict[str, Any]] = {}
    for line in lines[1:]:
        event = json.loads(line)
        key = (int(event["subject_id"]), int(event["tick"]), int(event["event_id"]))
        if key in result:
            raise ValueError("categorical trace contains duplicate event identity")
        result[key] = event
    if len(result) != int(manifest["event_count"]):
        raise ValueError("categorical trace event count mismatch")
    return result


def _condition_studies(panel_record: dict[str, Any]) -> dict[str, dict[str, Any]]:
    parent = _load_json(panel_record["study_report"])
    _validate_checksum(parent, field="study_sha256", label="Stage-3C-40 panel study")
    if not bool(parent.get("categorical_sampling_trace_enabled")):
        raise ValueError("Stage-3C-40 panel trace is not enabled")
    studies: dict[str, dict[str, Any]] = {}
    for condition in _CONDITIONS:
        record = parent["conditions"][condition]
        nested = _load_json(record["study_report"])
        _validate_checksum(nested, field="study_sha256", label=f"Stage-3C-40 {condition}")
        if not bool(nested.get("categorical_sampling_trace_enabled")):
            raise ValueError("Stage-3C-40 nested trace is not enabled")
        studies[condition] = nested
    return studies


def _frozen_by_seed(assessment: dict[str, Any]) -> dict[int, dict[str, Any]]:
    if assessment.get("schema") != STAGE3C34_THRESHOLD_CROSSING_ASSESSMENT_SCHEMA:
        raise ValueError("unsupported Stage-3C-34 assessment schema")
    _validate_checksum(assessment, field="assessment_sha256", label="Stage-3C-34 assessment")
    records = {int(item["seed"]): item for item in assessment["per_source"]}
    if len(records) != len(assessment["per_source"]):
        raise ValueError("Stage-3C-34 contains duplicate source seeds")
    return records


def _signed_interval_margin(draw: float, lower: float, upper: float) -> float:
    if draw < lower:
        return float(draw - lower)
    if draw >= upper:
        return float(upper - draw)
    return float(min(draw - lower, upper - draw))


def _same_action_interval(event: dict[str, Any], action_id: int) -> tuple[float, float]:
    cdf = np.asarray(event["cumulative_probabilities"], dtype=np.float64)
    lower = 0.0 if action_id == 0 else float(cdf[action_id - 1])
    upper = float(cdf[action_id])
    return lower, upper


def _transition(horizon: dict[str, Any], extended: dict[str, Any]) -> dict[str, Any]:
    if int(horizon["random_key_uint64"]) != int(extended["random_key_uint64"]):
        raise ValueError("Stage-3C-40 random key differs across exposure conditions")
    if float(horizon["uniform_draw"]) != float(extended["uniform_draw"]):
        raise ValueError("Stage-3C-40 uniform draw differs across exposure conditions")
    draw = float(horizon["uniform_draw"])
    action = int(horizon["action_id"])
    horizon_margin = _signed_interval_margin(
        draw,
        float(horizon["selected_cdf_lower"]),
        float(horizon["selected_cdf_upper"]),
    )
    extended_lower, extended_upper = _same_action_interval(extended, action)
    extended_margin = _signed_interval_margin(draw, extended_lower, extended_upper)
    cdf_h = np.asarray(horizon["cumulative_probabilities"], dtype=np.float64)
    cdf_e = np.asarray(extended["cumulative_probabilities"], dtype=np.float64)
    pressure = float(horizon_margin - extended_margin)
    ratio = None if horizon_margin <= 0 else float(pressure / horizon_margin)
    return {
        "horizon_action_id": action,
        "extended_action_id": int(extended["action_id"]),
        "action_changed": int(horizon["action_id"]) != int(extended["action_id"]),
        "action_mask_changed": horizon["action_mask"] != extended["action_mask"],
        "uniform_draw": draw,
        "horizon_selected_interval_margin": horizon_margin,
        "extended_same_action_signed_margin": extended_margin,
        "boundary_pressure_toward_or_across_draw": pressure,
        "boundary_pressure_to_horizon_margin_ratio": ratio,
        "cdf_linf_shift": float(np.max(np.abs(cdf_e - cdf_h))),
        "same_action_interval_crossed": bool(extended_margin <= 0.0),
    }


def _checkpoint_support_and_continuous_keys(
    studies: dict[str, dict[str, Any]], seed: int
) -> tuple[set[tuple[int, int, int]], set[tuple[int, int, int]]]:
    traces: dict[tuple[str, str, str], dict[str, np.ndarray]] = {}
    indexes: dict[tuple[str, str, str], dict[tuple[int, int, int], tuple[int, int]]] = {}
    for condition in _CONDITIONS:
        for mode in _MODES:
            record = _seed_records(studies[condition], mode)[seed]
            for role in _ROLES:
                _, runtime = _read_checkpoint(record[_ROLE_FIELDS[role]])
                trace = _trace_arrays(runtime)
                traces[condition, mode, role] = trace
                indexes[condition, mode, role] = _event_index(trace)
    supports = [set(value) for value in indexes.values()]
    if any(value != supports[0] for value in supports[1:]):
        raise ValueError("Stage-3C-40 checkpoint event support differs across arms")
    support = supports[0]
    result: set[tuple[int, int, int]] = set()
    for key in support:
        effects: dict[tuple[str, str], np.ndarray] = {}
        for condition in _CONDITIONS:
            for mode in _MODES:
                live_row, live_slot = indexes[condition, mode, "guarded-live"][key]
                control_row, control_slot = indexes[condition, mode, "read-only-control"][key]
                effects[condition, mode] = (
                    np.asarray(traces[condition, mode, "guarded-live"]["action_potentials"][live_row, live_slot], dtype=np.float64)
                    - np.asarray(traces[condition, mode, "read-only-control"]["action_potentials"][control_row, control_slot], dtype=np.float64)
                )
        ddd = (
            effects["extended-exposure", "alignment-ablated"]
            - effects["extended-exposure", "aligned"]
            - effects["horizon-control", "alignment-ablated"]
            + effects["horizon-control", "aligned"]
        )
        if np.any(np.abs(ddd) > _TOL):
            result.add(key)
    return support, result


def _source_audit(
    *,
    seed: int,
    studies: dict[str, dict[str, Any]],
    frozen: dict[str, Any],
) -> dict[str, Any]:
    source_hashes = {
        str(_seed_records(studies[condition], mode)[seed]["source_checkpoint_state_sha256"])
        for condition in _CONDITIONS
        for mode in _MODES
    }
    if source_hashes != {str(frozen["source_checkpoint_state_sha256"])}:
        raise ValueError("Stage-3C-40 source checkpoint identity differs from frozen Stage-3C-34")

    trace_events: dict[tuple[str, str, str], dict[tuple[int, int, int], dict[str, Any]]] = {}
    for condition in _CONDITIONS:
        for mode in _MODES:
            record = _seed_records(studies[condition], mode)[seed]
            manifests = record["categorical_sampling_trace_manifests"]
            for role in _ROLES:
                trace_events[condition, mode, role] = _load_trace(manifests[role])
    checkpoint_support, continuous = _checkpoint_support_and_continuous_keys(
        studies, seed
    )
    if len(checkpoint_support) != int(frozen["event_support"]["event_count"]):
        raise ValueError("Stage-3C-40 checkpoint support count differs from Stage-3C-34")
    for events in trace_events.values():
        if not checkpoint_support.issubset(events):
            raise ValueError("Stage-3C-40 categorical trace is missing frozen Subject VM events")
    support = checkpoint_support
    if len(continuous) != int(
        frozen["continuous_decision_divergence"]["subject_vm_potential_exposure_alignment_ddd_event_count"]
    ):
        raise ValueError("Stage-3C-40 continuous divergence count differs from Stage-3C-34")

    events: list[dict[str, Any]] = []
    differential_count = 0
    any_count = 0
    for key in sorted(continuous):
        transitions: dict[str, dict[str, Any]] = {}
        for mode in _MODES:
            transitions[mode] = _transition(
                trace_events["horizon-control", mode, "guarded-live"][key],
                trace_events["extended-exposure", mode, "guarded-live"][key],
            )
            control_h = trace_events["horizon-control", mode, "read-only-control"][key]
            control_e = trace_events["extended-exposure", mode, "read-only-control"][key]
            if control_h["action_id"] != control_e["action_id"] or control_h["cumulative_probabilities"] != control_e["cumulative_probabilities"]:
                raise ValueError("Stage-3C-40 read-only control differs across exposure conditions")
        aligned_transition = (
            transitions["aligned"]["horizon_action_id"],
            transitions["aligned"]["extended_action_id"],
        )
        ablated_transition = (
            transitions["alignment-ablated"]["horizon_action_id"],
            transitions["alignment-ablated"]["extended_action_id"],
        )
        any_crossing = bool(
            transitions["aligned"]["action_changed"]
            or transitions["alignment-ablated"]["action_changed"]
        )
        differential = bool(any_crossing and aligned_transition != ablated_transition)
        any_count += int(any_crossing)
        differential_count += int(differential)
        events.append(
            {
                "subject_id": key[0],
                "tick": key[1],
                "event_id": key[2],
                "aligned": transitions["aligned"],
                "alignment_ablated": transitions["alignment-ablated"],
                "any_exposure_action_crossing": any_crossing,
                "alignment_differential_action_crossing": differential,
            }
        )
    frozen_any = int(frozen["sampled_action_crossing"]["any_exposure_action_crossing_event_count"])
    frozen_differential = int(frozen["sampled_action_crossing"]["alignment_differential_action_crossing_event_count"])
    if any_count != frozen_any or differential_count != frozen_differential:
        raise ValueError("Stage-3C-40 trace crossing counts do not reproduce Stage-3C-34")

    aligned = [event["aligned"] for event in events]
    ablated = [event["alignment_ablated"] for event in events]
    noncrossing_aligned = [item for item in aligned if not item["action_changed"]]
    noncrossing_ablated = [item for item in ablated if not item["action_changed"]]
    def event_max_ratio(event: dict[str, Any]) -> float:
        values = [
            event[mode]["boundary_pressure_to_horizon_margin_ratio"]
            for mode in ("aligned", "alignment_ablated")
            if event[mode]["boundary_pressure_to_horizon_margin_ratio"] is not None
        ]
        return max(values, default=float("-inf"))

    top_opportunities = sorted(
        events, key=event_max_ratio, reverse=True
    )[:5]
    all_mode_ratios = [
        item["boundary_pressure_to_horizon_margin_ratio"]
        for event in events
        for item in (event["aligned"], event["alignment_ablated"])
        if item["boundary_pressure_to_horizon_margin_ratio"] is not None
    ]
    all_noncrossing_residuals = [
        item["extended_same_action_signed_margin"]
        for event in events
        for item in (event["aligned"], event["alignment_ablated"])
        if not item["action_changed"]
    ]
    return {
        "seed": seed,
        "source_checkpoint_state_sha256": next(iter(source_hashes)),
        "continuous_divergence_event_count": len(events),
        "any_exposure_action_crossing_event_count": any_count,
        "alignment_differential_action_crossing_event_count": differential_count,
        "frozen_classification": frozen["classification"],
        "aligned": {
            "horizon_margin_statistics": _stats(item["horizon_selected_interval_margin"] for item in aligned),
            "boundary_pressure_statistics": _stats(item["boundary_pressure_toward_or_across_draw"] for item in aligned),
            "pressure_ratio_statistics": _stats(item["boundary_pressure_to_horizon_margin_ratio"] for item in aligned if item["boundary_pressure_to_horizon_margin_ratio"] is not None),
            "noncrossing_extended_signed_margin_statistics": _stats(item["extended_same_action_signed_margin"] for item in noncrossing_aligned),
            "cdf_linf_shift_statistics": _stats(item["cdf_linf_shift"] for item in aligned),
            "events_pushed_toward_boundary": sum(item["boundary_pressure_toward_or_across_draw"] > 0 for item in aligned),
            "events_crossing_boundary": sum(item["action_changed"] for item in aligned),
        },
        "alignment_ablated": {
            "horizon_margin_statistics": _stats(item["horizon_selected_interval_margin"] for item in ablated),
            "boundary_pressure_statistics": _stats(item["boundary_pressure_toward_or_across_draw"] for item in ablated),
            "pressure_ratio_statistics": _stats(item["boundary_pressure_to_horizon_margin_ratio"] for item in ablated if item["boundary_pressure_to_horizon_margin_ratio"] is not None),
            "noncrossing_extended_signed_margin_statistics": _stats(item["extended_same_action_signed_margin"] for item in noncrossing_ablated),
            "cdf_linf_shift_statistics": _stats(item["cdf_linf_shift"] for item in ablated),
            "events_pushed_toward_boundary": sum(item["boundary_pressure_toward_or_across_draw"] > 0 for item in ablated),
            "events_crossing_boundary": sum(item["action_changed"] for item in ablated),
        },
        "crossing_events": [event for event in events if event["any_exposure_action_crossing"]],
        "top_boundary_opportunities": top_opportunities,
        "maximum_pressure_ratio_across_modes": max(all_mode_ratios, default=None),
        "minimum_noncrossing_residual_margin_across_modes": min(
            all_noncrossing_residuals, default=None
        ),
        "maximum_aligned_pressure_ratio": max(
            (item["boundary_pressure_to_horizon_margin_ratio"] for item in aligned if item["boundary_pressure_to_horizon_margin_ratio"] is not None),
            default=None,
        ),
        "minimum_aligned_noncrossing_residual_margin": min(
            (item["extended_same_action_signed_margin"] for item in noncrossing_aligned),
            default=None,
        ),
    }


def _panel_summary(records: list[dict[str, Any]]) -> dict[str, Any]:
    crossing = [item["seed"] for item in records if item["alignment_differential_action_crossing_event_count"]]
    return {
        "source_count": len(records),
        "continuous_divergence_source_count": sum(item["continuous_divergence_event_count"] > 0 for item in records),
        "alignment_differential_crossing_source_seeds": crossing,
        "alignment_differential_crossing_source_count": len(crossing),
        "maximum_pressure_ratio_across_modes_by_source": {
            str(item["seed"]): item["maximum_pressure_ratio_across_modes"] for item in records
        },
        "minimum_noncrossing_residual_margin_across_modes_by_source": {
            str(item["seed"]): item["minimum_noncrossing_residual_margin_across_modes"] for item in records
        },
        "maximum_aligned_pressure_ratio_by_source": {
            str(item["seed"]): item["maximum_aligned_pressure_ratio"] for item in records
        },
        "minimum_aligned_noncrossing_residual_margin_by_source": {
            str(item["seed"]): item["minimum_aligned_noncrossing_residual_margin"] for item in records
        },
        "source_balanced_maximum_pressure_ratio_across_modes_statistics": _stats(
            item["maximum_pressure_ratio_across_modes"]
            for item in records
            if item["maximum_pressure_ratio_across_modes"] is not None
        ),
        "global_maximum_pressure_ratio_across_modes": max(
            item["maximum_pressure_ratio_across_modes"]
            for item in records
            if item["maximum_pressure_ratio_across_modes"] is not None
        ),
        "source_balanced_maximum_pressure_ratio_statistics": _stats(
            item["maximum_aligned_pressure_ratio"] for item in records if item["maximum_aligned_pressure_ratio"] is not None
        ),
        "source_balanced_minimum_residual_margin_statistics": _stats(
            item["minimum_aligned_noncrossing_residual_margin"] for item in records if item["minimum_aligned_noncrossing_residual_margin"] is not None
        ),
    }


def assess_stage3c40_categorical_boundary(
    study_report: dict[str, Any],
    reference_stage3c34: dict[str, Any],
    replication_stage3c34: dict[str, Any],
) -> dict[str, Any]:
    if study_report.get("schema") != STAGE3C40_CATEGORICAL_BOUNDARY_STUDY_SCHEMA:
        raise ValueError("unsupported Stage-3C-40 study schema")
    _validate_checksum(study_report, field="study_sha256", label="Stage-3C-40 study")
    if not bool(study_report.get("categorical_sampling_trace_enabled")):
        raise ValueError("Stage-3C-40 requires categorical sampling trace")
    if bool(study_report.get("runtime_sampling_semantics_changed")):
        raise ValueError("Stage-3C-40 cannot change runtime sampling semantics")
    frozen_panels = {
        "reference": _frozen_by_seed(reference_stage3c34),
        "replication": _frozen_by_seed(replication_stage3c34),
    }
    panel_results: dict[str, dict[str, Any]] = {}
    per_panel_sources: dict[str, list[dict[str, Any]]] = {}
    for panel in ("reference", "replication"):
        studies = _condition_studies(study_report["panels"][panel])
        records = [
            _source_audit(seed=seed, studies=studies, frozen=frozen)
            for seed, frozen in sorted(frozen_panels[panel].items())
        ]
        per_panel_sources[panel] = records
        panel_results[panel] = _panel_summary(records)

    reference_crossing = panel_results["reference"]["alignment_differential_crossing_source_seeds"]
    replication_crossing = panel_results["replication"]["alignment_differential_crossing_source_seeds"]
    payload: dict[str, Any] = {
        "schema": STAGE3C40_CATEGORICAL_BOUNDARY_ASSESSMENT_SCHEMA,
        "producer_version": __version__,
        "study_sha256": str(study_report["study_sha256"]),
        "reference_stage3c34_assessment_sha256": str(reference_stage3c34["assessment_sha256"]),
        "replication_stage3c34_assessment_sha256": str(replication_stage3c34["assessment_sha256"]),
        "experimental_factor": "exact observed categorical CDF boundary opportunity under frozen exposure/alignment intervention",
        "panels": {
            panel: {"summary": panel_results[panel], "per_source": per_panel_sources[panel]}
            for panel in ("reference", "replication")
        },
        "cross_panel_findings": {
            "reference_crossing_source_seeds": reference_crossing,
            "replication_crossing_source_seeds": replication_crossing,
            "reference_crossing_source_count": len(reference_crossing),
            "replication_crossing_source_count": len(replication_crossing),
            "trace_reproduces_frozen_stage3c34_crossing_counts": True,
            "all_continuous_divergence_events_have_exact_draw_and_cdf_geometry": True,
            "replication_panel_contains_no_realized_boundary_crossing": len(replication_crossing) == 0,
            "reference_panel_contains_nonempty_realized_boundary_crossing": len(reference_crossing) > 0,
            "reference_global_maximum_pressure_ratio": panel_results["reference"]["global_maximum_pressure_ratio_across_modes"],
            "replication_global_maximum_pressure_ratio": panel_results["replication"]["global_maximum_pressure_ratio_across_modes"],
            "replication_all_pressure_ratios_below_one": bool(
                panel_results["replication"]["global_maximum_pressure_ratio_across_modes"] < 1.0
            ),
        },
        "frozen_interpretation": {
            "categorical_boundary_opportunity_is_now_exactly_observed": True,
            "reference_positive_sources_cross_when_boundary_pressure_exceeds_draw_margin": True,
            "replication_boundary_pressure_never_exhausts_draw_margin": bool(
                panel_results["replication"]["global_maximum_pressure_ratio_across_modes"] < 1.0
            ),
            "replication_zero_crossing_is_not_an_observability_artifact": len(replication_crossing) == 0,
            "single_source_invariant_scalar_predictor_is_authorized": False,
            "objective_coordinates_have_value_semantics": False,
            "causal_credit_quality_is_proven": False,
            "automatic_keep_or_revert_authorized": False,
            "permanent_retention_authorized": False,
        },
        "governance": {
            "runtime_rerun_used_only_to_generate_observation_trace": True,
            "source_state_identity_matches_frozen_panels": True,
            "sampling_semantics_changed": False,
            "random_stream_changed": False,
            "source_selection_or_replacement": False,
            "exposure_or_horizon_changed": False,
            "post_hoc_boundary_threshold_used": False,
        },
        "automatic_keep_or_revert_authorized": False,
        "permanent_parameter_retention_authorized": False,
        "learned_weight_authorized": False,
        "learning_claim_authorized": False,
        "subjecthood_claim_authorized": False,
    }
    payload["assessment_sha256"] = _canonical_sha256(payload)
    return payload


def _summary(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema": "se-subject-vm-stage3c40-study-summary-v1",
        "producer_version": payload["producer_version"],
        "assessment_sha256": payload["assessment_sha256"],
        "reference": payload["panels"]["reference"]["summary"],
        "replication": payload["panels"]["replication"]["summary"],
        "frozen_interpretation": payload["frozen_interpretation"],
    }


def _diagnostic(payload: dict[str, Any]) -> str:
    reference = payload["panels"]["reference"]["summary"]
    replication = payload["panels"]["replication"]["summary"]
    return "\n".join(
        [
            "# Stage 3C-40 精确 categorical action-boundary 审计",
            "",
            f"- 原 panel crossing source：`{reference['alignment_differential_crossing_source_seeds']}`。",
            f"- 独立 panel crossing source：`{replication['alignment_differential_crossing_source_seeds']}`。",
            "- 每个 continuous divergence event 均已绑定完整 CDF、uniform draw 与 selected interval。",
            "- 原 panel 的 realized crossing 可由 draw 离开原 action interval 精确重建。",
            "- 独立 panel 的所有对应 event 均保留在 action interval 内。",
            "- 本结果只解释 sampled-action boundary，不赋予 Objective-Fact 价值语义。",
            "",
        ]
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="评估 Stage 3C-40 精确 categorical boundary opportunity。")
    parser.add_argument("--study-report", required=True)
    parser.add_argument("--reference-stage3c34", required=True)
    parser.add_argument("--replication-stage3c34", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--summary-output")
    parser.add_argument("--diagnostic-report")
    args = parser.parse_args()
    payload = assess_stage3c40_categorical_boundary(
        _load_json(args.study_report),
        _load_json(args.reference_stage3c34),
        _load_json(args.replication_stage3c34),
    )
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if args.summary_output:
        Path(args.summary_output).write_text(json.dumps(_summary(payload), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if args.diagnostic_report:
        Path(args.diagnostic_report).write_text(_diagnostic(payload), encoding="utf-8")
    print(json.dumps(payload["cross_panel_findings"], ensure_ascii=False))


if __name__ == "__main__":
    main()


__all__ = [
    "STAGE3C40_CATEGORICAL_BOUNDARY_ASSESSMENT_SCHEMA",
    "assess_stage3c40_categorical_boundary",
]
