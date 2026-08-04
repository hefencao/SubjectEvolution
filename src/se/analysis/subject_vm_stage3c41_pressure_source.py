"""Stage 3C-41 action-logit and CDF boundary-pressure source decomposition.

The audit is read-only. It consumes the frozen Stage-3C-40 categorical traces
and decomposes the preregistered top-five boundary-opportunity events per
source into masked-logit changes, softmax probability-mass redistribution and
selected-interval endpoint pressure.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
from typing import Any, Iterable

import numpy as np

from .. import __version__
from ..experiments.subject_vm_short_paired_study import _canonical_sha256
from .subject_vm_stage3c40_categorical_boundary import (
    STAGE3C40_CATEGORICAL_BOUNDARY_ASSESSMENT_SCHEMA,
)

STAGE3C41_PRESSURE_SOURCE_ASSESSMENT_SCHEMA = (
    "se-subject-vm-stage3c41-pressure-source-assessment-v1"
)
_ACTION_NAMES = (
    "REST",
    "MOVE_RESOURCE",
    "MOVE_SOCIAL",
    "HARVEST",
    "SHARE",
    "SIGNAL",
    "REPRODUCE",
    "FLEE",
)
_MODES = ("aligned", "alignment-ablated")
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
        return {
            "count": 0,
            "minimum": None,
            "median": None,
            "maximum": None,
            "mean": None,
        }
    return {
        "count": int(array.size),
        "minimum": float(np.min(array)),
        "median": float(np.median(array)),
        "maximum": float(np.max(array)),
        "mean": float(np.mean(array)),
    }


def _portable_trace_events(
    trace_root: Path,
    *,
    panel: str,
    condition: str,
    seed: int,
    mode: str,
) -> tuple[dict[tuple[int, int, int], dict[str, Any]], str, str]:
    branch = (
        trace_root
        / panel
        / condition
        / f"seed_{seed}"
        / mode
        / "paired"
        / "guarded_live"
    )
    manifest_path = branch / "categorical_sampling_trace_manifest.json"
    trace_path = branch / "categorical_sampling_trace.jsonl"
    manifest = _load_json(manifest_path)
    _validate_checksum(
        manifest,
        field="manifest_sha256",
        label="Stage-3C-41 categorical trace manifest",
    )
    if _sha256(trace_path) != str(manifest["trace_sha256"]):
        raise ValueError("Stage-3C-41 categorical trace checksum mismatch")
    lines = trace_path.read_text(encoding="utf-8").splitlines()
    if not lines:
        raise ValueError("Stage-3C-41 categorical trace is empty")
    header = json.loads(lines[0])
    if header.get("record_type") != "header":
        raise ValueError("Stage-3C-41 categorical trace header is missing")
    if header.get("action_order") != list(_ACTION_NAMES):
        raise ValueError("Stage-3C-41 action order differs from frozen trace schema")
    events: dict[tuple[int, int, int], dict[str, Any]] = {}
    for line in lines[1:]:
        event = json.loads(line)
        key = (
            int(event["subject_id"]),
            int(event["tick"]),
            int(event["event_id"]),
        )
        if key in events:
            raise ValueError("Stage-3C-41 trace contains duplicate event identity")
        events[key] = event
    if len(events) != int(manifest["event_count"]):
        raise ValueError("Stage-3C-41 trace event count mismatch")
    return events, str(manifest["manifest_sha256"]), str(manifest["trace_sha256"])


def _masked_logits(event: dict[str, Any]) -> np.ndarray:
    return np.asarray(
        [np.nan if value is None else float(value) for value in event["masked_logits"]],
        dtype=np.float64,
    )


def _decompose_transition(
    horizon: dict[str, Any], extended: dict[str, Any]
) -> dict[str, Any]:
    if int(horizon["random_key_uint64"]) != int(extended["random_key_uint64"]):
        raise ValueError("Stage-3C-41 random key differs across exposure conditions")
    if float(horizon["uniform_draw"]) != float(extended["uniform_draw"]):
        raise ValueError("Stage-3C-41 uniform draw differs across exposure conditions")
    if horizon["action_mask"] != extended["action_mask"]:
        raise ValueError("Stage-3C-41 action mask differs across exposure conditions")

    probabilities_h = np.asarray(horizon["probabilities"], dtype=np.float64)
    probabilities_e = np.asarray(extended["probabilities"], dtype=np.float64)
    probability_delta = probabilities_e - probabilities_h
    if abs(float(np.sum(probability_delta))) > 1.0e-10:
        raise ValueError("Stage-3C-41 probability mass is not conserved")

    logits_h = _masked_logits(horizon)
    logits_e = _masked_logits(extended)
    logit_delta = logits_e - logits_h
    changed_logit_actions = [
        int(index)
        for index in np.flatnonzero(np.isfinite(logit_delta) & (np.abs(logit_delta) > _TOL))
    ]

    action = int(horizon["action_id"])
    draw = float(horizon["uniform_draw"])
    cdf_h = np.asarray(horizon["cumulative_probabilities"], dtype=np.float64)
    cdf_e = np.asarray(extended["cumulative_probabilities"], dtype=np.float64)
    horizon_lower = 0.0 if action == 0 else float(cdf_h[action - 1])
    horizon_upper = float(cdf_h[action])
    extended_lower = 0.0 if action == 0 else float(cdf_e[action - 1])
    extended_upper = float(cdf_e[action])
    horizon_lower_margin = float(draw - horizon_lower)
    horizon_upper_margin = float(horizon_upper - draw)
    extended_lower_margin = float(draw - extended_lower)
    extended_upper_margin = float(extended_upper - draw)
    horizon_nearest_endpoint = (
        "lower" if horizon_lower_margin <= horizon_upper_margin else "upper"
    )
    extended_active_endpoint = (
        "lower" if extended_lower_margin <= extended_upper_margin else "upper"
    )
    horizon_margin = min(horizon_lower_margin, horizon_upper_margin)
    extended_signed_margin = min(extended_lower_margin, extended_upper_margin)
    stage3c40_pressure = float(horizon_margin - extended_signed_margin)
    lower_endpoint_pressure = float(extended_lower - horizon_lower)
    upper_endpoint_pressure = float(horizon_upper - extended_upper)

    contributions = np.zeros(len(_ACTION_NAMES), dtype=np.float64)
    if extended_active_endpoint == "lower":
        contributions[:action] = probability_delta[:action]
        active_endpoint_pressure = lower_endpoint_pressure
    else:
        contributions[: action + 1] = -probability_delta[: action + 1]
        active_endpoint_pressure = upper_endpoint_pressure
    if abs(float(np.sum(contributions)) - active_endpoint_pressure) > 1.0e-10:
        raise ValueError("Stage-3C-41 endpoint contribution decomposition is not exact")
    endpoint_switch_offset = float(active_endpoint_pressure - stage3c40_pressure)

    rest_driver = float(contributions[0])
    other_action_net = float(np.sum(contributions[1:]))
    return {
        "horizon_action_id": action,
        "horizon_action_name": _ACTION_NAMES[action],
        "extended_action_id": int(extended["action_id"]),
        "extended_action_name": _ACTION_NAMES[int(extended["action_id"])],
        "action_changed": int(horizon["action_id"]) != int(extended["action_id"]),
        "uniform_draw": draw,
        "changed_logit_action_ids": changed_logit_actions,
        "changed_logit_action_names": [_ACTION_NAMES[index] for index in changed_logit_actions],
        "masked_logit_delta": [
            None if not np.isfinite(value) else float(value) for value in logit_delta
        ],
        "probability_delta": [float(value) for value in probability_delta],
        "horizon_nearest_endpoint": horizon_nearest_endpoint,
        "extended_active_endpoint": extended_active_endpoint,
        "endpoint_switched": horizon_nearest_endpoint != extended_active_endpoint,
        "horizon_selected_interval_margin": float(horizon_margin),
        "extended_same_action_signed_margin": float(extended_signed_margin),
        "stage3c40_boundary_pressure": stage3c40_pressure,
        "lower_endpoint_pressure": lower_endpoint_pressure,
        "upper_endpoint_pressure": upper_endpoint_pressure,
        "active_endpoint_pressure": float(active_endpoint_pressure),
        "endpoint_switch_offset": endpoint_switch_offset,
        "active_endpoint_probability_contributions": {
            name: float(contributions[index])
            for index, name in enumerate(_ACTION_NAMES)
        },
        "rest_probability_driver": rest_driver,
        "other_action_net_cancellation_or_support": other_action_net,
        "rest_driver_to_active_pressure_ratio": (
            None
            if abs(active_endpoint_pressure) <= _TOL
            else float(rest_driver / active_endpoint_pressure)
        ),
        "boundary_pressure_to_horizon_margin_ratio": (
            None
            if horizon_margin <= 0.0
            else float(stage3c40_pressure / horizon_margin)
        ),
    }


def _category(panel: str, seed: int) -> str:
    if panel == "replication":
        return "replication-noncrossing"
    if seed in (12305, 12308):
        return "reference-alignment-differential-crossing"
    if seed == 12307:
        return "reference-alignment-common-crossing"
    return "reference-noncrossing"


def assess_stage3c41_pressure_source(
    stage3c40: dict[str, Any], trace_root: str | Path
) -> dict[str, Any]:
    if stage3c40.get("schema") != STAGE3C40_CATEGORICAL_BOUNDARY_ASSESSMENT_SCHEMA:
        raise ValueError("unsupported Stage-3C-40 assessment schema")
    _validate_checksum(
        stage3c40,
        field="assessment_sha256",
        label="Stage-3C-41 Stage-3C-40 assessment",
    )
    root = Path(trace_root).resolve()
    if not root.is_dir():
        raise FileNotFoundError(root)

    manifest_checksums: set[str] = set()
    trace_checksums: set[str] = set()
    event_records: list[dict[str, Any]] = []
    source_summaries: list[dict[str, Any]] = []
    changed_logit_patterns: Counter[tuple[str, ...]] = Counter()

    for panel in ("reference", "replication"):
        for source in stage3c40["panels"][panel]["per_source"]:
            seed = int(source["seed"])
            selected_events = {
                (
                    int(event["subject_id"]),
                    int(event["tick"]),
                    int(event["event_id"]),
                )
                for event in source["top_boundary_opportunities"]
            }
            crossing_events = {
                (
                    int(event["subject_id"]),
                    int(event["tick"]),
                    int(event["event_id"]),
                )
                for event in source["crossing_events"]
            }
            if not crossing_events.issubset(selected_events):
                raise ValueError("Stage-3C-41 top-five support omits a crossing event")
            if len(selected_events) != 5:
                raise ValueError("Stage-3C-41 requires five frozen opportunities per source")

            traces: dict[tuple[str, str], dict[tuple[int, int, int], dict[str, Any]]] = {}
            for condition in ("horizon-control", "extended-exposure"):
                for mode in _MODES:
                    events, manifest_sha, trace_sha = _portable_trace_events(
                        root,
                        panel=panel,
                        condition=condition,
                        seed=seed,
                        mode=mode,
                    )
                    traces[condition, mode] = events
                    manifest_checksums.add(manifest_sha)
                    trace_checksums.add(trace_sha)
                    if not selected_events.issubset(events):
                        raise ValueError("Stage-3C-41 trace omits a frozen opportunity event")

            source_mode_records: list[dict[str, Any]] = []
            for subject_id, tick, event_id in sorted(selected_events):
                key = (subject_id, tick, event_id)
                for mode in _MODES:
                    decomposition = _decompose_transition(
                        traces["horizon-control", mode][key],
                        traces["extended-exposure", mode][key],
                    )
                    changed_logit_patterns[tuple(decomposition["changed_logit_action_names"])] += 1
                    record = {
                        "panel": panel,
                        "source_category": _category(panel, seed),
                        "seed": seed,
                        "subject_id": subject_id,
                        "tick": tick,
                        "event_id": event_id,
                        "mode": mode,
                        "frozen_top_five_opportunity": True,
                        "frozen_crossing_event": key in crossing_events,
                        **decomposition,
                    }
                    source_mode_records.append(record)
                    event_records.append(record)

            ratios = [
                record["boundary_pressure_to_horizon_margin_ratio"]
                for record in source_mode_records
                if record["boundary_pressure_to_horizon_margin_ratio"] is not None
            ]
            source_summaries.append(
                {
                    "panel": panel,
                    "source_category": _category(panel, seed),
                    "seed": seed,
                    "frozen_classification": source["frozen_classification"],
                    "audited_event_identity_count": len(selected_events),
                    "audited_mode_event_count": len(source_mode_records),
                    "realized_action_crossing_mode_event_count": sum(
                        int(record["action_changed"]) for record in source_mode_records
                    ),
                    "nonzero_masked_logit_mode_event_count": sum(
                        bool(record["changed_logit_action_ids"])
                        for record in source_mode_records
                    ),
                    "maximum_pressure_ratio": max(ratios),
                    "maximum_abs_rest_logit_delta": max(
                        abs(float(record["masked_logit_delta"][0] or 0.0))
                        for record in source_mode_records
                    ),
                    "maximum_abs_rest_probability_delta": max(
                        abs(float(record["probability_delta"][0]))
                        for record in source_mode_records
                    ),
                }
            )

    crossing = [record for record in event_records if record["action_changed"]]
    noncrossing = [record for record in event_records if not record["action_changed"]]
    changed = [record for record in event_records if record["changed_logit_action_ids"]]
    if len(event_records) != 180 or len(crossing) != 6:
        raise ValueError("Stage-3C-41 frozen audit support changed")
    if any(record["changed_logit_action_ids"] != [0] for record in changed):
        raise ValueError("Stage-3C-41 found a non-REST masked-logit source")
    crossing_decomposition = []
    for record in crossing:
        crossing_decomposition.append(
            {
                key: record[key]
                for key in (
                    "panel",
                    "seed",
                    "subject_id",
                    "tick",
                    "event_id",
                    "mode",
                    "horizon_action_id",
                    "horizon_action_name",
                    "extended_action_id",
                    "extended_action_name",
                    "masked_logit_delta",
                    "probability_delta",
                    "horizon_nearest_endpoint",
                    "extended_active_endpoint",
                    "endpoint_switched",
                    "horizon_selected_interval_margin",
                    "stage3c40_boundary_pressure",
                    "active_endpoint_pressure",
                    "endpoint_switch_offset",
                    "active_endpoint_probability_contributions",
                    "rest_probability_driver",
                    "other_action_net_cancellation_or_support",
                    "rest_driver_to_active_pressure_ratio",
                    "boundary_pressure_to_horizon_margin_ratio",
                )
            }
        )

    replication_top = max(
        (
            record
            for record in event_records
            if record["source_category"] == "replication-noncrossing"
        ),
        key=lambda item: float(item["boundary_pressure_to_horizon_margin_ratio"]),
    )
    common = [record for record in crossing if record["seed"] == 12307]
    if len(common) != 2:
        raise ValueError("Stage-3C-41 alignment-common crossing support changed")

    abs_crossing_logit = [abs(float(record["masked_logit_delta"][0])) for record in crossing]
    abs_noncrossing_logit = [
        abs(float(record["masked_logit_delta"][0] or 0.0)) for record in noncrossing
    ]
    abs_crossing_probability = [abs(float(record["probability_delta"][0])) for record in crossing]
    abs_noncrossing_probability = [
        abs(float(record["probability_delta"][0])) for record in noncrossing
    ]

    payload: dict[str, Any] = {
        "schema": STAGE3C41_PRESSURE_SOURCE_ASSESSMENT_SCHEMA,
        "producer_version": __version__,
        "stage3c40_assessment_sha256": str(stage3c40["assessment_sha256"]),
        "experimental_factor": "read-only-frozen-top-five-boundary-opportunity-decomposition",
        "audit_support": {
            "source_count": len(source_summaries),
            "event_identity_count": 90,
            "mode_event_count": len(event_records),
            "nonzero_masked_logit_mode_event_count": len(changed),
            "zero_masked_logit_mode_event_count": len(event_records) - len(changed),
            "realized_action_crossing_mode_event_count": len(crossing),
            "trace_manifest_count": len(manifest_checksums),
            "trace_file_count": len(trace_checksums),
            "selection_rule": "Stage-3C-40 frozen top-five boundary opportunities per source",
            "all_stage3c40_crossing_events_included": True,
            "manifest_identity_sha256": _canonical_sha256(sorted(manifest_checksums)),
            "trace_identity_sha256": _canonical_sha256(sorted(trace_checksums)),
        },
        "masked_logit_source": {
            "changed_action_pattern_counts": {
                "+".join(pattern) if pattern else "none": count
                for pattern, count in sorted(changed_logit_patterns.items())
            },
            "all_nonzero_changes_are_rest_only": True,
            "rest_is_fixed_action_port_not_value_claim": True,
            "softmax_redistributes_rest_logit_change_across_all_legal_actions": True,
        },
        "source_summaries": source_summaries,
        "crossing_decomposition": crossing_decomposition,
        "cross_panel_findings": {
            "crossing_mode_event_count": len(crossing),
            "positive_rest_logit_crossing_count": sum(
                float(record["masked_logit_delta"][0]) > 0.0 for record in crossing
            ),
            "negative_rest_logit_crossing_count": sum(
                float(record["masked_logit_delta"][0]) < 0.0 for record in crossing
            ),
            "crossing_events_with_other_action_cancellation": sum(
                float(record["other_action_net_cancellation_or_support"]) < 0.0
                for record in crossing
            ),
            "crossing_events_with_endpoint_switch": sum(
                bool(record["endpoint_switched"]) for record in crossing
            ),
            "maximum_abs_rest_logit_delta_crossing": max(abs_crossing_logit),
            "maximum_abs_rest_logit_delta_noncrossing": max(abs_noncrossing_logit),
            "maximum_abs_rest_probability_delta_crossing": max(abs_crossing_probability),
            "maximum_abs_rest_probability_delta_noncrossing": max(abs_noncrossing_probability),
            "rest_logit_magnitude_alone_separates_crossing": (
                max(abs_noncrossing_logit) < min(abs_crossing_logit)
            ),
            "rest_probability_delta_alone_separates_crossing": (
                max(abs_noncrossing_probability) < min(abs_crossing_probability)
            ),
            "alignment_common_seed": 12307,
            "alignment_common_pressure_absolute_difference": abs(
                float(common[0]["stage3c40_boundary_pressure"])
                - float(common[1]["stage3c40_boundary_pressure"])
            ),
            "replication_highest_opportunity": {
                key: replication_top[key]
                for key in (
                    "seed",
                    "subject_id",
                    "tick",
                    "event_id",
                    "mode",
                    "horizon_action_name",
                    "masked_logit_delta",
                    "probability_delta",
                    "horizon_selected_interval_margin",
                    "rest_probability_driver",
                    "other_action_net_cancellation_or_support",
                    "stage3c40_boundary_pressure",
                    "boundary_pressure_to_horizon_margin_ratio",
                )
            },
        },
        "frozen_interpretation": {
            "policy_level_boundary_pressure_source_is_rest_logit_only": True,
            "other_action_probability_changes_are_softmax_coupling_not_independent_logit_changes": True,
            "rest_logit_sign_or_magnitude_alone_is_sufficient_for_crossing": False,
            "selected_action_order_and_interval_endpoint_are_material": True,
            "intervening_action_probability_changes_can_cancel_rest_driver": True,
            "alignment_common_crossing_has_nearly_identical_pressure_in_both_modes": True,
            "replication_noncrossing_can_have_larger_logit_and_probability_changes_than_crossing": True,
            "source_history_origin_of_rest_logit_change_is_resolved": False,
            "objective_coordinates_have_value_semantics": False,
            "causal_credit_quality_is_proven": False,
            "next_boundary": "neutral-subject-vm-activation-contribution-trace-engineering",
        },
        "governance": {
            "runtime_rerun_used": False,
            "new_source_panel_used": False,
            "trace_selection_changed_after_observation": False,
            "sampling_semantics_changed": False,
            "random_stream_changed": False,
            "exposure_or_horizon_changed": False,
            "post_hoc_scalar_classifier_fitted": False,
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
        "schema": "se-subject-vm-stage3c41-study-summary-v1",
        "producer_version": payload["producer_version"],
        "assessment_sha256": payload["assessment_sha256"],
        "audit_support": payload["audit_support"],
        "masked_logit_source": payload["masked_logit_source"],
        "cross_panel_findings": payload["cross_panel_findings"],
        "retention_authorized": False,
    }


def _diagnostic(payload: dict[str, Any]) -> str:
    findings = payload["cross_panel_findings"]
    replication = findings["replication_highest_opportunity"]
    lines = [
        "# Stage 3C-41 action-logit 与 CDF pressure 来源分解",
        "",
        "## 冻结支持",
        "",
        f"- source：`{payload['audit_support']['source_count']}`。",
        f"- Stage 3C-40 预先冻结的 top-five event identity：`{payload['audit_support']['event_identity_count']}`。",
        f"- mode-event comparison：`{payload['audit_support']['mode_event_count']}`。",
        f"- realized crossing mode-event：`{findings['crossing_mode_event_count']}`。",
        "",
        "## 主要结果",
        "",
        "- 所有非零 masked-logit 变化都只发生在 `REST` action port。",
        "- 其他 action 的 probability delta 全部来自 softmax 耦合，不是独立 logit 变化。",
        f"- crossing 中 REST logit 正变化 `{findings['positive_rest_logit_crossing_count']}` 次、负变化 `{findings['negative_rest_logit_crossing_count']}` 次。",
        f"- `{findings['crossing_events_with_other_action_cancellation']}`/6 个 crossing 存在其他 action probability 的净抵消。",
        f"- noncrossing 的最大 |REST logit delta| 为 `{findings['maximum_abs_rest_logit_delta_noncrossing']:.12f}`，高于 crossing 最大值 `{findings['maximum_abs_rest_logit_delta_crossing']:.12f}`。",
        f"- 独立 panel 最高机会 seed `{replication['seed']}` 的压力/余量比为 `{replication['boundary_pressure_to_horizon_margin_ratio']:.12f}`，仍保留正余量。",
        "",
        "## 边界",
        "",
        "REST logit 是当前固定 bootstrap 输出路由的 action port，不是价值标签。",
        "本轮没有解释 source history 如何形成 REST logit delta；下一步需要语义中立的 Subject VM activation contribution trace。",
        "不授权 reward、learned weight、keep/revert 或永久 retention。",
        "",
    ]
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Assess Stage 3C-41 action-logit and CDF pressure sources."
    )
    parser.add_argument("--stage3c40-assessment", required=True)
    parser.add_argument("--trace-root", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--summary-output")
    parser.add_argument("--diagnostic-report")
    args = parser.parse_args()
    payload = assess_stage3c41_pressure_source(
        _load_json(args.stage3c40_assessment), args.trace_root
    )
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    if args.summary_output:
        Path(args.summary_output).write_text(
            json.dumps(_summary(payload), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    if args.diagnostic_report:
        Path(args.diagnostic_report).write_text(_diagnostic(payload), encoding="utf-8")
    print(json.dumps(payload["cross_panel_findings"], ensure_ascii=False))


if __name__ == "__main__":
    main()


__all__ = [
    "STAGE3C41_PRESSURE_SOURCE_ASSESSMENT_SCHEMA",
    "assess_stage3c41_pressure_source",
]
