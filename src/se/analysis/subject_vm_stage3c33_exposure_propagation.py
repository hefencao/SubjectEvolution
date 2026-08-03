"""Stage 3C-33 exposure-length propagation assessment.

The assessment reuses the complete Stage-3C-32 engineering analysis for each
predeclared condition, verifies the live-ledger dose, and audits evaluation
support before estimating propagation. Rollback-complete one-tick windows are
retained as auxiliary diagnostics because changing exposure changes their
completion set. The primary exposure contrast uses identical full-event support
at the matched eleven-tick horizon.

No objective coordinate is scalarized and no result authorizes retention.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
import json
from pathlib import Path
from typing import Any, Iterable

import numpy as np

from .. import __version__
from ..experiments.subject_vm_short_paired_study import _canonical_sha256
from ..subject_vm.modulation import objective_fact_vector
from ..experiments.subject_vm_stage3c33_exposure_propagation import (
    STAGE3C33_EXPOSURE_PROPAGATION_STUDY_SCHEMA,
)
from .subject_vm_component_reproducibility import OBJECTIVE_FACT_COORDINATE_NAMES
from .subject_vm_stage3c32_alignment_intervention import (
    STAGE3C32_ALIGNMENT_INTERVENTION_ASSESSMENT_SCHEMA,
    _coordinate_summary,
    _event_index,
    _read_checkpoint,
    _trace_arrays,
    assess_stage3c32_alignment_intervention,
)

STAGE3C33_EXPOSURE_PROPAGATION_ASSESSMENT_SCHEMA = (
    "se-subject-vm-stage3c33-exposure-propagation-assessment-v1"
)
_TOL = 1.0e-12
_EXPOSURE_IDENTITY_ARRAYS = (
    "entry_valid",
    "event_id",
    "applied_tick",
    "family_applied",
    "target_kind",
    "target_index",
    "target_id",
    "pre_value",
    "post_value",
    "commit_cost_units",
    "rollback_cost_units",
)
_CONTROL_BEHAVIOR_ARRAYS = (
    "thought_token",
    "action_potentials",
    "sampled_probability",
    "action_id",
    "success",
    "objective_delta",
    "resolution_resource_delta",
    "resolution_internal_resource_delta",
    "resolution_energy_cost",
)
_CONDITION_NAMES = ("frozen-baseline", "horizon-control", "extended-exposure")


def _load_json(path: str | Path) -> dict[str, Any]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"expected one JSON object: {path}")
    return payload


def _validate_checksum(
    payload: dict[str, Any], *, field: str, label: str
) -> None:
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


def _per_source(assessment: dict[str, Any]) -> dict[int, dict[str, Any]]:
    result = {int(item["seed"]): item for item in assessment.get("per_source", [])}
    if len(result) != len(assessment.get("per_source", [])):
        raise ValueError("Stage-3C-33 condition assessment contains duplicate seeds")
    return result


def _condition_summary(assessment: dict[str, Any]) -> dict[str, Any]:
    findings = assessment["cross_source_findings"]
    return {
        "source_count": int(assessment["source_level_independent_replication_count"]),
        "sources_with_nonzero_componentwise_live_control_effect": int(
            findings["sources_with_nonzero_componentwise_live_control_effect"]
        ),
        "stable_fact_sum_coordinate_count": int(
            findings["stable_fact_sum_coordinate_count"]
        ),
        "stable_fact_abs_sum_coordinate_count": int(
            findings["stable_fact_abs_sum_coordinate_count"]
        ),
        "selector_identity_change_fraction_statistics": findings[
            "selector_identity_change_fraction_statistics"
        ],
        "update_route_change_fraction_statistics": findings[
            "update_route_change_fraction_statistics"
        ],
        "changed_bounded_delta_count_statistics": findings[
            "changed_bounded_delta_count_statistics"
        ],
        "aligned_total_paired_window_count": int(
            findings["aligned_total_paired_window_count"]
        ),
        "alignment_ablated_total_paired_window_count": int(
            findings["alignment_ablated_total_paired_window_count"]
        ),
        "manipulation_integrity_passes_in_all_sources": bool(
            findings["manipulation_integrity_passes_in_all_sources"]
        ),
        "compute_and_storage_costs_match_in_all_sources": bool(
            findings["compute_and_storage_costs_match_in_all_sources"]
        ),
        "forced_rollback_restores_graph_parameters_in_all_sources": bool(
            findings["forced_rollback_restores_graph_parameters_in_all_sources"]
        ),
    }


def _cross_mode_vector(source: dict[str, Any], field: str) -> np.ndarray:
    return np.asarray(
        source["cross_mode_ablation_minus_aligned_live_control_effect"][field],
        dtype=np.float64,
    )


def _contrast_summary(
    *,
    left: dict[str, Any],
    right: dict[str, Any],
    label: str,
) -> dict[str, Any]:
    left_by_seed = _per_source(left)
    right_by_seed = _per_source(right)
    if set(left_by_seed) != set(right_by_seed):
        raise ValueError(f"Stage-3C-33 {label} source panel mismatch")

    fact_vectors: list[np.ndarray] = []
    abs_vectors: list[np.ndarray] = []
    count_vectors: list[np.ndarray] = []
    per_source: list[dict[str, Any]] = []
    for seed in sorted(left_by_seed):
        left_source = left_by_seed[seed]
        right_source = right_by_seed[seed]
        if str(left_source["source_checkpoint_state_sha256"]) != str(
            right_source["source_checkpoint_state_sha256"]
        ):
            raise ValueError(f"Stage-3C-33 {label} source checkpoint mismatch")
        fact = _cross_mode_vector(right_source, "fact_sum") - _cross_mode_vector(
            left_source, "fact_sum"
        )
        absolute = _cross_mode_vector(
            right_source, "fact_abs_sum"
        ) - _cross_mode_vector(left_source, "fact_abs_sum")
        count = _cross_mode_vector(
            right_source, "count_difference"
        ) - _cross_mode_vector(left_source, "count_difference")
        fact_vectors.append(fact)
        abs_vectors.append(absolute)
        count_vectors.append(count)
        per_source.append(
            {
                "seed": seed,
                "source_checkpoint_state_sha256": str(
                    left_source["source_checkpoint_state_sha256"]
                ),
                "fact_sum": [float(value) for value in fact.tolist()],
                "fact_abs_sum": [float(value) for value in absolute.tolist()],
                "count_difference": [float(value) for value in count.tolist()],
                "fact_sum_l1": float(np.sum(np.abs(fact))),
                "fact_abs_sum_l1": float(np.sum(np.abs(absolute))),
                "has_nonzero_fact_sum": bool(np.any(np.abs(fact) > _TOL)),
            }
        )

    fact_coordinates, fact_positive, fact_negative = _coordinate_summary(
        fact_vectors, names=OBJECTIVE_FACT_COORDINATE_NAMES
    )
    abs_coordinates, abs_positive, abs_negative = _coordinate_summary(
        abs_vectors, names=OBJECTIVE_FACT_COORDINATE_NAMES
    )
    count_coordinates, count_positive, count_negative = _coordinate_summary(
        count_vectors,
        names=(
            "observation_count_difference",
            "success_count_difference",
            "failure_count_difference",
        ),
    )
    return {
        "label": label,
        "per_source": per_source,
        "sources_with_nonzero_fact_sum_contrast": int(
            sum(item["has_nonzero_fact_sum"] for item in per_source)
        ),
        "fact_sum_l1_statistics": _stats(item["fact_sum_l1"] for item in per_source),
        "fact_abs_sum_l1_statistics": _stats(
            item["fact_abs_sum_l1"] for item in per_source
        ),
        "componentwise": {
            "fact_sum": {
                "coordinates": fact_coordinates,
                "stable_positive_coordinate_names": fact_positive,
                "stable_negative_coordinate_names": fact_negative,
            },
            "fact_abs_sum": {
                "coordinates": abs_coordinates,
                "stable_positive_coordinate_names": abs_positive,
                "stable_negative_coordinate_names": abs_negative,
            },
            "count_difference": {
                "coordinates": count_coordinates,
                "stable_positive_coordinate_names": count_positive,
                "stable_negative_coordinate_names": count_negative,
            },
        },
        "stable_fact_sum_coordinate_count": int(
            len(fact_positive) + len(fact_negative)
        ),
        "stable_fact_abs_sum_coordinate_count": int(
            len(abs_positive) + len(abs_negative)
        ),
    }


def _compare_control_behavior(
    left_checkpoint: str | Path, right_checkpoint: str | Path
) -> dict[str, Any]:
    left_meta, left_state = _read_checkpoint(left_checkpoint)
    right_meta, right_state = _read_checkpoint(right_checkpoint)
    left_trace = _trace_arrays(left_state)
    right_trace = _trace_arrays(right_state)
    left_index = _event_index(left_trace)
    right_index = _event_index(right_trace)
    keys_equal = set(left_index) == set(right_index)
    mismatched_events = 0
    mismatched_arrays: dict[str, int] = {name: 0 for name in _CONTROL_BEHAVIOR_ARRAYS}
    if keys_equal:
        for key in sorted(left_index):
            left_row = left_index[key]
            right_row = right_index[key]
            event_mismatch = False
            for name in _CONTROL_BEHAVIOR_ARRAYS:
                if not np.array_equal(
                    left_trace[name][left_row], right_trace[name][right_row]
                ):
                    mismatched_arrays[name] += 1
                    event_mismatch = True
            mismatched_events += int(event_mismatch)
    return {
        "left_tick": int(left_meta["tick"]),
        "right_tick": int(right_meta["tick"]),
        "event_keys_equal": bool(keys_equal),
        "mismatched_event_count": int(mismatched_events),
        "mismatched_array_event_counts": {
            key: int(value) for key, value in mismatched_arrays.items() if value
        },
        "control_behavior_semantically_identical": bool(
            keys_equal and mismatched_events == 0
        ),
    }


def _compare_exposure_dose(
    baseline_checkpoint: str | Path,
    extended_checkpoint: str | Path,
    *,
    baseline_exposure_ticks: int,
    extended_exposure_ticks: int,
) -> dict[str, Any]:
    baseline_meta, baseline_runtime = _read_checkpoint(baseline_checkpoint)
    extended_meta, extended_runtime = _read_checkpoint(extended_checkpoint)
    baseline_ledger = baseline_runtime.get("live_write_ledger", {})
    extended_ledger = extended_runtime.get("live_write_ledger", {})
    baseline_arrays = baseline_ledger.get("arrays")
    extended_arrays = extended_ledger.get("arrays")
    if not isinstance(baseline_arrays, dict) or not isinstance(extended_arrays, dict):
        raise ValueError("Stage-3C-33 checkpoint lacks live-write ledger arrays")
    identity_arrays_equal = all(
        np.array_equal(
            np.asarray(baseline_arrays[name]), np.asarray(extended_arrays[name])
        )
        for name in _EXPOSURE_IDENTITY_ARRAYS
    )
    baseline_valid = np.asarray(baseline_arrays["entry_valid"], dtype=bool)
    extended_valid = np.asarray(extended_arrays["entry_valid"], dtype=bool)
    valid_equal = np.array_equal(baseline_valid, extended_valid)
    baseline_duration = (
        np.asarray(baseline_arrays["rollback_due_tick"], dtype=np.int64)
        - np.asarray(baseline_arrays["applied_tick"], dtype=np.int64)
    )
    extended_duration = (
        np.asarray(extended_arrays["rollback_due_tick"], dtype=np.int64)
        - np.asarray(extended_arrays["applied_tick"], dtype=np.int64)
    )
    baseline_duration_values = sorted(
        {int(value) for value in baseline_duration[baseline_valid].tolist()}
    )
    extended_duration_values = sorted(
        {int(value) for value in extended_duration[extended_valid].tolist()}
    )
    baseline_family = np.asarray(
        baseline_arrays["family_applied"], dtype=bool
    )[baseline_valid]
    extended_family = np.asarray(
        extended_arrays["family_applied"], dtype=bool
    )[extended_valid]
    baseline_target_ticks = int(
        np.sum(baseline_duration[baseline_valid] * np.sum(baseline_family, axis=1))
    )
    extended_target_ticks = int(
        np.sum(extended_duration[extended_valid] * np.sum(extended_family, axis=1))
    )
    baseline_counters = baseline_ledger.get("counters", {})
    extended_counters = extended_ledger.get("counters", {})
    transaction_count_equal = int(
        baseline_counters.get("total_committed_transactions", -1)
    ) == int(extended_counters.get("total_committed_transactions", -2))
    target_count_equal = int(
        baseline_counters.get("total_committed_targets", -1)
    ) == int(extended_counters.get("total_committed_targets", -2))
    expected_ratio = float(extended_exposure_ticks) / float(baseline_exposure_ticks)
    observed_ratio = (
        float(extended_target_ticks) / float(baseline_target_ticks)
        if baseline_target_ticks
        else None
    )
    return {
        "baseline_final_tick": int(baseline_meta["tick"]),
        "extended_final_tick": int(extended_meta["tick"]),
        "valid_entry_count": int(np.count_nonzero(baseline_valid)),
        "valid_entry_identity_equal": bool(valid_equal and identity_arrays_equal),
        "committed_transaction_count_equal": bool(transaction_count_equal),
        "committed_target_count_equal": bool(target_count_equal),
        "baseline_exposure_duration_values": baseline_duration_values,
        "extended_exposure_duration_values": extended_duration_values,
        "baseline_target_tick_exposure": baseline_target_ticks,
        "extended_target_tick_exposure": extended_target_ticks,
        "expected_target_tick_exposure_ratio": expected_ratio,
        "observed_target_tick_exposure_ratio": observed_ratio,
        "baseline_duration_matches_declaration": baseline_duration_values
        == [int(baseline_exposure_ticks)],
        "extended_duration_matches_declaration": extended_duration_values
        == [int(extended_exposure_ticks)],
        "target_tick_exposure_matches_declared_ratio": bool(
            observed_ratio is not None
            and abs(observed_ratio - expected_ratio) <= _TOL
        ),
    }



def _event_fact_vector(
    trace: dict[str, np.ndarray], location: tuple[int, int]
) -> np.ndarray:
    row, slot = location
    return objective_fact_vector(
        objective_delta=trace["objective_delta"][row, slot],
        resource_delta=trace["resolution_resource_delta"][row, slot],
        internal_resource_delta=trace["resolution_internal_resource_delta"][row, slot],
        energy_cost=float(trace["resolution_energy_cost"][row, slot]),
    )


def _trajectory_live_control_source(
    live_checkpoint: str | Path, control_checkpoint: str | Path
) -> dict[str, Any]:
    live_meta, live_runtime = _read_checkpoint(live_checkpoint)
    control_meta, control_runtime = _read_checkpoint(control_checkpoint)
    live_trace = _trace_arrays(live_runtime)
    control_trace = _trace_arrays(control_runtime)
    live_index = _event_index(live_trace)
    control_index = _event_index(control_trace)
    keys_equal = set(live_index) == set(control_index)
    if not keys_equal:
        raise ValueError("Stage-3C-33 fixed-horizon live/control event support mismatch")
    if int(live_meta["tick"]) != int(control_meta["tick"]):
        raise ValueError("Stage-3C-33 fixed-horizon live/control final tick mismatch")

    fact_by_subject: dict[int, list[np.ndarray]] = defaultdict(list)
    abs_by_subject: dict[int, list[np.ndarray]] = defaultdict(list)
    count_by_subject: dict[int, list[np.ndarray]] = defaultdict(list)
    ticks: list[int] = []
    for key in sorted(live_index):
        subject_id, event_tick, _event_id = key
        live_location = live_index[key]
        control_location = control_index[key]
        live_fact = _event_fact_vector(live_trace, live_location)
        control_fact = _event_fact_vector(control_trace, control_location)
        fact_by_subject[subject_id].append(live_fact - control_fact)
        abs_by_subject[subject_id].append(np.abs(live_fact) - np.abs(control_fact))
        live_success = float(bool(live_trace["success"][live_location]))
        control_success = float(bool(control_trace["success"][control_location]))
        count_by_subject[subject_id].append(
            np.asarray(
                [
                    0.0,
                    live_success - control_success,
                    (1.0 - live_success) - (1.0 - control_success),
                ],
                dtype=np.float64,
            )
        )
        ticks.append(int(event_tick))

    if not fact_by_subject:
        raise ValueError("Stage-3C-33 fixed-horizon trajectory contains no events")
    fact = np.mean(
        [np.sum(np.stack(values, axis=0), axis=0) for values in fact_by_subject.values()],
        axis=0,
    )
    absolute = np.mean(
        [np.sum(np.stack(values, axis=0), axis=0) for values in abs_by_subject.values()],
        axis=0,
    )
    count = np.mean(
        [np.sum(np.stack(values, axis=0), axis=0) for values in count_by_subject.values()],
        axis=0,
    )
    key_payload = {
        "events": [list(key) for key in sorted(live_index)],
    }
    return {
        "final_tick": int(live_meta["tick"]),
        "event_count": int(len(live_index)),
        "stable_subject_count": int(len(fact_by_subject)),
        "minimum_event_tick": int(min(ticks)),
        "maximum_event_tick": int(max(ticks)),
        "event_identity_sha256": _canonical_sha256(key_payload),
        "event_identity_sets_match": True,
        "subject_balanced_trajectory_fact_sum_difference": fact,
        "subject_balanced_trajectory_fact_abs_sum_difference": absolute,
        "subject_balanced_trajectory_count_difference": count,
    }


def _trajectory_condition(study: dict[str, Any]) -> dict[str, Any]:
    records_by_mode = {
        mode: _study_seed_records(study, mode)
        for mode in ("aligned", "alignment-ablated")
    }
    if set(records_by_mode["aligned"]) != set(records_by_mode["alignment-ablated"]):
        raise ValueError("Stage-3C-33 fixed-horizon trajectory source panel mismatch")

    fact_vectors: list[np.ndarray] = []
    abs_vectors: list[np.ndarray] = []
    count_vectors: list[np.ndarray] = []
    per_source: list[dict[str, Any]] = []
    for seed in sorted(records_by_mode["aligned"]):
        aligned_record = records_by_mode["aligned"][seed]
        ablated_record = records_by_mode["alignment-ablated"][seed]
        if str(aligned_record["source_checkpoint_state_sha256"]) != str(
            ablated_record["source_checkpoint_state_sha256"]
        ):
            raise ValueError("Stage-3C-33 fixed-horizon source checkpoint mismatch")
        aligned = _trajectory_live_control_source(
            aligned_record["guarded_live_checkpoint"],
            aligned_record["read_only_control_checkpoint"],
        )
        ablated = _trajectory_live_control_source(
            ablated_record["guarded_live_checkpoint"],
            ablated_record["read_only_control_checkpoint"],
        )
        if (
            aligned["event_count"] != ablated["event_count"]
            or aligned["stable_subject_count"] != ablated["stable_subject_count"]
            or aligned["minimum_event_tick"] != ablated["minimum_event_tick"]
            or aligned["maximum_event_tick"] != ablated["maximum_event_tick"]
        ):
            raise ValueError("Stage-3C-33 alignment modes have different trajectory support")
        fact = (
            ablated["subject_balanced_trajectory_fact_sum_difference"]
            - aligned["subject_balanced_trajectory_fact_sum_difference"]
        )
        absolute = (
            ablated["subject_balanced_trajectory_fact_abs_sum_difference"]
            - aligned["subject_balanced_trajectory_fact_abs_sum_difference"]
        )
        count = (
            ablated["subject_balanced_trajectory_count_difference"]
            - aligned["subject_balanced_trajectory_count_difference"]
        )
        fact_vectors.append(fact)
        abs_vectors.append(absolute)
        count_vectors.append(count)
        per_source.append(
            {
                "seed": int(seed),
                "source_checkpoint_state_sha256": str(
                    aligned_record["source_checkpoint_state_sha256"]
                ),
                "aligned": {
                    "event_count": int(aligned["event_count"]),
                    "stable_subject_count": int(aligned["stable_subject_count"]),
                    "minimum_event_tick": int(aligned["minimum_event_tick"]),
                    "maximum_event_tick": int(aligned["maximum_event_tick"]),
                    "event_identity_sha256": str(aligned["event_identity_sha256"]),
                    "fact_sum": [
                        float(value)
                        for value in aligned[
                            "subject_balanced_trajectory_fact_sum_difference"
                        ].tolist()
                    ],
                    "fact_abs_sum": [
                        float(value)
                        for value in aligned[
                            "subject_balanced_trajectory_fact_abs_sum_difference"
                        ].tolist()
                    ],
                    "count_difference": [
                        float(value)
                        for value in aligned[
                            "subject_balanced_trajectory_count_difference"
                        ].tolist()
                    ],
                },
                "alignment_ablated": {
                    "event_count": int(ablated["event_count"]),
                    "stable_subject_count": int(ablated["stable_subject_count"]),
                    "minimum_event_tick": int(ablated["minimum_event_tick"]),
                    "maximum_event_tick": int(ablated["maximum_event_tick"]),
                    "event_identity_sha256": str(ablated["event_identity_sha256"]),
                    "fact_sum": [
                        float(value)
                        for value in ablated[
                            "subject_balanced_trajectory_fact_sum_difference"
                        ].tolist()
                    ],
                    "fact_abs_sum": [
                        float(value)
                        for value in ablated[
                            "subject_balanced_trajectory_fact_abs_sum_difference"
                        ].tolist()
                    ],
                    "count_difference": [
                        float(value)
                        for value in ablated[
                            "subject_balanced_trajectory_count_difference"
                        ].tolist()
                    ],
                },
                "cross_mode_ablation_minus_aligned_live_control_effect": {
                    "fact_sum": [float(value) for value in fact.tolist()],
                    "fact_abs_sum": [float(value) for value in absolute.tolist()],
                    "count_difference": [float(value) for value in count.tolist()],
                },
            }
        )

    fact_coordinates, fact_positive, fact_negative = _coordinate_summary(
        fact_vectors, names=OBJECTIVE_FACT_COORDINATE_NAMES
    )
    abs_coordinates, abs_positive, abs_negative = _coordinate_summary(
        abs_vectors, names=OBJECTIVE_FACT_COORDINATE_NAMES
    )
    count_coordinates, count_positive, count_negative = _coordinate_summary(
        count_vectors,
        names=(
            "observation_count_difference",
            "success_count_difference",
            "failure_count_difference",
        ),
    )
    nonzero_seeds = [
        int(item["seed"])
        for item in per_source
        if np.any(
            np.abs(
                np.asarray(
                    item["cross_mode_ablation_minus_aligned_live_control_effect"][
                        "fact_sum"
                    ],
                    dtype=np.float64,
                )
            )
            > _TOL
        )
    ]
    return {
        "per_source": per_source,
        "cross_source_findings": {
            "source_count": int(len(per_source)),
            "nonzero_cross_mode_fact_sum_source_count": int(len(nonzero_seeds)),
            "nonzero_cross_mode_fact_sum_source_seeds": nonzero_seeds,
            "stable_fact_sum_coordinate_count": int(
                len(fact_positive) + len(fact_negative)
            ),
            "stable_fact_abs_sum_coordinate_count": int(
                len(abs_positive) + len(abs_negative)
            ),
            "componentwise": {
                "fact_sum": {
                    "coordinates": fact_coordinates,
                    "stable_positive_coordinate_names": fact_positive,
                    "stable_negative_coordinate_names": fact_negative,
                },
                "fact_abs_sum": {
                    "coordinates": abs_coordinates,
                    "stable_positive_coordinate_names": abs_positive,
                    "stable_negative_coordinate_names": abs_negative,
                },
                "count_difference": {
                    "coordinates": count_coordinates,
                    "stable_positive_coordinate_names": count_positive,
                    "stable_negative_coordinate_names": count_negative,
                },
            },
        },
    }


def _trajectory_contrast(
    *, left: dict[str, Any], right: dict[str, Any], label: str
) -> dict[str, Any]:
    return _contrast_summary(left=left, right=right, label=label)


def _checkpoint_event_support(checkpoint: str | Path) -> dict[str, Any]:
    metadata, runtime = _read_checkpoint(checkpoint)
    index = _event_index(_trace_arrays(runtime))
    if not index:
        raise ValueError("Stage-3C-33 fixed-horizon checkpoint contains no events")
    ticks = [key[1] for key in index]
    subjects = {key[0] for key in index}
    return {
        "final_tick": int(metadata["tick"]),
        "event_count": int(len(index)),
        "stable_subject_count": int(len(subjects)),
        "minimum_event_tick": int(min(ticks)),
        "maximum_event_tick": int(max(ticks)),
        "event_identity_sha256": _canonical_sha256(
            {"events": [list(key) for key in sorted(index)]}
        ),
    }


def _common_horizon_trajectory_support(
    left_study: dict[str, Any], right_study: dict[str, Any]
) -> dict[str, Any]:
    comparisons: list[dict[str, Any]] = []
    for mode in ("aligned", "alignment-ablated"):
        left_records = _study_seed_records(left_study, mode)
        right_records = _study_seed_records(right_study, mode)
        if set(left_records) != set(right_records):
            raise ValueError("Stage-3C-33 common-horizon trajectory panel mismatch")
        for seed in sorted(left_records):
            for role, key in (
                ("guarded-live", "guarded_live_checkpoint"),
                ("read-only-control", "read_only_control_checkpoint"),
            ):
                left = _checkpoint_event_support(left_records[seed][key])
                right = _checkpoint_event_support(right_records[seed][key])
                comparisons.append(
                    {
                        "seed": int(seed),
                        "alignment_mode": mode,
                        "branch_role": role,
                        "left": left,
                        "right": right,
                        "support_matches": bool(left == right),
                    }
                )
    return {
        "comparisons": comparisons,
        "all_support_matches": bool(
            all(item["support_matches"] for item in comparisons)
        ),
    }


def _paired_window_diagnostic(
    studies: dict[str, dict[str, Any]],
    *,
    horizon_contrast: dict[str, Any],
    exposure_contrast: dict[str, Any],
) -> dict[str, Any]:
    observation_ticks: set[int] = set()
    common_horizon_support: list[dict[str, Any]] = []
    for condition in _CONDITION_NAMES:
        study = studies[condition]
        for mode in ("aligned", "alignment-ablated"):
            for record in study["modes"][mode]["seed_records"]:
                export = _load_json(record["export"])
                pairs = list(export.get("window_evidence", {}).get("pairs", ()))
                for pair in pairs:
                    live = pair["guarded_live"]
                    control = pair["read_only_control"]
                    observation_ticks.add(int(live["end_tick"]) - int(live["start_tick"]))
                    observation_ticks.add(
                        int(control["end_tick"]) - int(control["start_tick"])
                    )

    for mode in ("aligned", "alignment-ablated"):
        left_records = _study_seed_records(studies["horizon-control"], mode)
        right_records = _study_seed_records(studies["extended-exposure"], mode)
        for seed in sorted(left_records):
            left_export = _load_json(left_records[seed]["export"])
            right_export = _load_json(right_records[seed]["export"])
            def support_key(pair: dict[str, Any]) -> tuple[int, int, int, int]:
                live = pair["guarded_live"]
                return (
                    int(live["stable_subject_id"]),
                    int(live["source_event_id"]),
                    int(live["start_tick"]),
                    int(live["end_tick"]),
                )

            left_keys = {
                support_key(pair)
                for pair in left_export.get("window_evidence", {}).get("pairs", ())
            }
            right_keys = {
                support_key(pair)
                for pair in right_export.get("window_evidence", {}).get("pairs", ())
            }
            common_horizon_support.append(
                {
                    "seed": int(seed),
                    "alignment_mode": mode,
                    "horizon_control_pair_count": int(len(left_keys)),
                    "extended_exposure_pair_count": int(len(right_keys)),
                    "pair_key_sets_match": bool(left_keys == right_keys),
                }
            )

    support_matches = all(
        item["pair_key_sets_match"] for item in common_horizon_support
    )
    observation_values = sorted(observation_ticks)
    return {
        "observation_tick_values": observation_values,
        "common_horizon_pair_support": common_horizon_support,
        "common_horizon_pair_support_matches_in_all_sources_and_modes": bool(
            support_matches
        ),
        "horizon_only_contrast": horizon_contrast,
        "exposure_only_contrast": exposure_contrast,
        "valid_for_primary_exposure_propagation_inference": bool(
            support_matches and observation_values != [1]
        ),
        "limitation": (
            "rollback-complete paired windows observe one subsequent tick and "
            "their completed support differs when rollback duration changes"
        ),
    }

def _study_seed_records(study: dict[str, Any], mode: str) -> dict[int, dict[str, Any]]:
    records = {
        int(item["seed"]): item for item in study["modes"][mode]["seed_records"]
    }
    if len(records) != len(study["modes"][mode]["seed_records"]):
        raise ValueError("Stage-3C-33 nested study contains duplicate seed records")
    return records


def assess_stage3c33_exposure_propagation(
    study_report: dict[str, Any],
) -> dict[str, Any]:
    if study_report.get("schema") != STAGE3C33_EXPOSURE_PROPAGATION_STUDY_SCHEMA:
        raise ValueError("unsupported Stage-3C-33 exposure propagation study schema")
    _validate_checksum(study_report, field="study_sha256", label="Stage-3C-33 study")
    parameters = study_report.get("parameters", {})
    expected = {
        "frozen-baseline": (
            int(parameters["frozen_baseline_horizon_ticks"]),
            int(parameters["baseline_exposure_ticks"]),
        ),
        "horizon-control": (
            int(parameters["common_horizon_ticks"]),
            int(parameters["baseline_exposure_ticks"]),
        ),
        "extended-exposure": (
            int(parameters["common_horizon_ticks"]),
            int(parameters["extended_exposure_ticks"]),
        ),
    }
    if set(study_report.get("conditions", {})) != set(_CONDITION_NAMES):
        raise ValueError("Stage-3C-33 requires all three predeclared conditions")
    if bool(study_report.get("adaptive_exposure_extension")):
        raise ValueError("Stage-3C-33 cannot adapt exposure after observing results")
    if bool(study_report.get("permanent_parameter_retention_authorized")):
        raise ValueError("Stage-3C-33 cannot authorize permanent retention")

    studies: dict[str, dict[str, Any]] = {}
    assessments: dict[str, dict[str, Any]] = {}
    for name in _CONDITION_NAMES:
        record = study_report["conditions"][name]
        if (int(record["horizon_ticks"]), int(record["exposure_ticks"])) != expected[name]:
            raise ValueError(f"Stage-3C-33 {name} parameters differ from declaration")
        nested = _load_json(record["study_report"])
        _validate_checksum(nested, field="study_sha256", label=f"Stage-3C-33 {name}")
        if str(nested["study_sha256"]) != str(record["study_sha256"]):
            raise ValueError(f"Stage-3C-33 {name} identity mismatch")
        nested_parameters = nested["parameters"]
        if int(nested_parameters["horizon_ticks"]) != expected[name][0] or int(
            nested_parameters["rollback_after_ticks"]
        ) != expected[name][1]:
            raise ValueError(f"Stage-3C-33 {name} nested parameter mismatch")
        assessment = assess_stage3c32_alignment_intervention(nested)
        if assessment.get("schema") != STAGE3C32_ALIGNMENT_INTERVENTION_ASSESSMENT_SCHEMA:
            raise ValueError("Stage-3C-33 nested assessment schema mismatch")
        studies[name] = nested
        assessments[name] = assessment

    source_signatures = [
        study_report["conditions"][name]["source_signature"]
        for name in _CONDITION_NAMES
    ]
    if source_signatures[1:] != source_signatures[:-1]:
        raise ValueError("Stage-3C-33 source identity differs across conditions")

    control_checks: list[dict[str, Any]] = []
    exposure_dose_checks: list[dict[str, Any]] = []
    for mode in ("aligned", "alignment-ablated"):
        horizon_records = _study_seed_records(studies["horizon-control"], mode)
        extended_records = _study_seed_records(studies["extended-exposure"], mode)
        if set(horizon_records) != set(extended_records):
            raise ValueError("Stage-3C-33 common-horizon source panel mismatch")
        for seed in sorted(horizon_records):
            comparison = _compare_control_behavior(
                horizon_records[seed]["read_only_control_checkpoint"],
                extended_records[seed]["read_only_control_checkpoint"],
            )
            control_checks.append({"seed": seed, "alignment_mode": mode, **comparison})
            dose = _compare_exposure_dose(
                horizon_records[seed]["guarded_live_checkpoint"],
                extended_records[seed]["guarded_live_checkpoint"],
                baseline_exposure_ticks=int(parameters["baseline_exposure_ticks"]),
                extended_exposure_ticks=int(parameters["extended_exposure_ticks"]),
            )
            exposure_dose_checks.append(
                {"seed": seed, "alignment_mode": mode, **dose}
            )

    paired_horizon_contrast = _contrast_summary(
        left=assessments["frozen-baseline"],
        right=assessments["horizon-control"],
        label="paired-window-horizon-control-minus-frozen-baseline",
    )
    paired_exposure_contrast = _contrast_summary(
        left=assessments["horizon-control"],
        right=assessments["extended-exposure"],
        label="paired-window-extended-exposure-minus-horizon-control",
    )
    paired_window_diagnostic = _paired_window_diagnostic(
        studies,
        horizon_contrast=paired_horizon_contrast,
        exposure_contrast=paired_exposure_contrast,
    )

    horizon_trajectory = _trajectory_condition(studies["horizon-control"])
    extended_trajectory = _trajectory_condition(studies["extended-exposure"])
    trajectory_exposure_contrast = _trajectory_contrast(
        left=horizon_trajectory,
        right=extended_trajectory,
        label="fixed-horizon-trajectory-extended-exposure-minus-horizon-control",
    )
    trajectory_support = _common_horizon_trajectory_support(
        studies["horizon-control"], studies["extended-exposure"]
    )

    all_condition_engineering = all(
        summary["manipulation_integrity_passes_in_all_sources"]
        and summary["compute_and_storage_costs_match_in_all_sources"]
        and summary["forced_rollback_restores_graph_parameters_in_all_sources"]
        for summary in (
            _condition_summary(assessments[name]) for name in _CONDITION_NAMES
        )
    )
    controls_equal = all(
        item["control_behavior_semantically_identical"] for item in control_checks
    )
    exposure_dose_valid = all(
        item["valid_entry_identity_equal"]
        and item["committed_transaction_count_equal"]
        and item["committed_target_count_equal"]
        and item["baseline_duration_matches_declaration"]
        and item["extended_duration_matches_declaration"]
        and item["target_tick_exposure_matches_declared_ratio"]
        for item in exposure_dose_checks
    )

    horizon_trajectory_nonzero_seeds = set(
        horizon_trajectory["cross_source_findings"][
            "nonzero_cross_mode_fact_sum_source_seeds"
        ]
    )
    extended_trajectory_nonzero_seeds = set(
        extended_trajectory["cross_source_findings"][
            "nonzero_cross_mode_fact_sum_source_seeds"
        ]
    )
    trajectory_exposure_nonzero_seeds = {
        int(item["seed"])
        for item in trajectory_exposure_contrast["per_source"]
        if bool(item["has_nonzero_fact_sum"])
    }
    trajectory_stable_count = int(
        trajectory_exposure_contrast["stable_fact_sum_coordinate_count"]
        + trajectory_exposure_contrast["stable_fact_abs_sum_coordinate_count"]
    )
    fixed_trajectory_support_valid = bool(
        trajectory_support["all_support_matches"]
    )
    source_replicated_trajectory_propagation = bool(
        all_condition_engineering
        and controls_equal
        and exposure_dose_valid
        and fixed_trajectory_support_valid
        and len(trajectory_exposure_nonzero_seeds) >= 3
        and trajectory_stable_count > 0
    )

    payload = {
        "schema": STAGE3C33_EXPOSURE_PROPAGATION_ASSESSMENT_SCHEMA,
        "producer_version": __version__,
        "study_sha256": str(study_report["study_sha256"]),
        "experimental_factor": (
            "temporary exposure duration at matched 11-tick horizon, assessed "
            "over fixed common-horizon event trajectories"
        ),
        "condition_summaries": {
            name: _condition_summary(assessments[name]) for name in _CONDITION_NAMES
        },
        "common_horizon_control_behavior": {
            "comparisons": control_checks,
            "all_read_only_control_behavior_identical": bool(controls_equal),
        },
        "exposure_dose_integrity": {
            "comparisons": exposure_dose_checks,
            "same_transaction_and_update_identity_with_declared_duration_change": bool(
                exposure_dose_valid
            ),
        },
        "paired_window_diagnostic": paired_window_diagnostic,
        "fixed_common_horizon_trajectory": {
            "aggregation": (
                "event-level live-minus-control facts summed within stable subject, "
                "then balanced across subjects and independent sources"
            ),
            "horizon_control": horizon_trajectory,
            "extended_exposure": extended_trajectory,
            "exposure_only_contrast": trajectory_exposure_contrast,
            "support_integrity": trajectory_support,
            "primary_exposure_propagation_estimator": True,
        },
        "cross_source_findings": {
            "all_condition_engineering_contracts_pass": bool(all_condition_engineering),
            "common_horizon_read_only_controls_are_identical": bool(controls_equal),
            "exposure_dose_integrity_passes_in_all_sources_and_modes": bool(
                exposure_dose_valid
            ),
            "paired_window_observation_tick_values": list(
                paired_window_diagnostic["observation_tick_values"]
            ),
            "paired_window_completion_support_matches_between_common_horizon_conditions": bool(
                paired_window_diagnostic[
                    "common_horizon_pair_support_matches_in_all_sources_and_modes"
                ]
            ),
            "paired_window_estimator_valid_for_primary_exposure_inference": bool(
                paired_window_diagnostic[
                    "valid_for_primary_exposure_propagation_inference"
                ]
            ),
            "fixed_horizon_trajectory_support_matches_in_all_sources_modes_and_roles": bool(
                fixed_trajectory_support_valid
            ),
            "horizon_control_trajectory_nonzero_source_count": int(
                len(horizon_trajectory_nonzero_seeds)
            ),
            "horizon_control_trajectory_nonzero_source_seeds": sorted(
                horizon_trajectory_nonzero_seeds
            ),
            "extended_exposure_trajectory_nonzero_source_count": int(
                len(extended_trajectory_nonzero_seeds)
            ),
            "extended_exposure_trajectory_nonzero_source_seeds": sorted(
                extended_trajectory_nonzero_seeds
            ),
            "extended_exposure_adds_new_trajectory_nonzero_sources": int(
                len(
                    extended_trajectory_nonzero_seeds
                    - horizon_trajectory_nonzero_seeds
                )
            ),
            "trajectory_exposure_only_nonzero_source_count": int(
                len(trajectory_exposure_nonzero_seeds)
            ),
            "trajectory_exposure_only_nonzero_source_seeds": sorted(
                trajectory_exposure_nonzero_seeds
            ),
            "trajectory_exposure_only_stable_fact_sum_coordinate_count": int(
                trajectory_exposure_contrast["stable_fact_sum_coordinate_count"]
            ),
            "trajectory_exposure_only_stable_fact_abs_sum_coordinate_count": int(
                trajectory_exposure_contrast[
                    "stable_fact_abs_sum_coordinate_count"
                ]
            ),
        },
        "diagnostic_interpretation": {
            "ledger_exposure_dose_intervention_is_valid": bool(exposure_dose_valid),
            "fixed_common_horizon_trajectory_is_valid_primary_estimator": bool(
                fixed_trajectory_support_valid
            ),
            "rollback_complete_paired_window_estimator_is_primary": False,
            "any_exposure_dependent_downstream_trajectory_effect_observed": bool(
                trajectory_exposure_nonzero_seeds
            ),
            "sparse_trajectory_propagation_without_stable_coordinate": bool(
                0 < len(trajectory_exposure_nonzero_seeds) < 3
                and trajectory_stable_count == 0
            ),
            "source_replicated_exposure_propagation_supported": bool(
                source_replicated_trajectory_propagation
            ),
            "longer_exposure_produces_a_cross_source_stable_componentwise_propagation_coordinate": bool(
                trajectory_stable_count > 0
            ),
            "objective_coordinates_have_value_semantics": False,
            "alignment_intervention_proves_credit_quality": False,
            "automatic_keep_or_revert_authorized": False,
            "permanent_retention_authorized": False,
        },
        "governance": {
            "exposure_propagation_requires_ledger_dose_verification": True,
            "exposure_propagation_requires_fixed_common_trajectory_support": True,
            "evaluation_observation_coverage_must_be_audited_separately": True,
            "rollback_complete_windows_may_be_auxiliary_when_support_changes": True,
            "adaptive_exposure_extension_used": False,
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


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Assess Stage-3C-33 horizon-only and exposure-only propagation "
            "contrasts without scalarizing objective facts."
        )
    )
    parser.add_argument("--study-report", required=True)
    parser.add_argument("--output", required=True)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    study = _load_json(args.study_report)
    result = assess_stage3c33_exposure_propagation(study)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
