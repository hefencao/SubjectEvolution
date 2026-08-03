"""Stage 3C-32 runtime alignment intervention and four-arm assessment.

This assessment compares two guarded-live/read-only-control pairs generated
from each identical rank-two source checkpoint.  Both alignment modes execute
the same token-copy/sort path and differ only in whether association-visible
port 30 remains attached to its own stable subject or is cyclically donated by
another subject at the same tick.

The report verifies manipulation, compute/storage matching and rollback before
summarizing live-minus-control objective facts within each mode.  Cross-mode
contrasts are balanced first by stable subject and then by independent source.
No objective coordinate is scalarized or assigned value semantics.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
import json
from pathlib import Path
from typing import Any, Iterable

import numpy as np

from .. import __version__
from ..checkpointing import read_checkpoint_bundle
from ..subject_vm.trace import (
    ASSOCIATION_ALIGNMENT_CYCLIC_DONOR,
    ASSOCIATION_ALIGNMENT_IDENTITY,
    OBJECTIVE_EVENT_DELTA_NAMES,
)
from .subject_vm_component_reproducibility import OBJECTIVE_FACT_COORDINATE_NAMES
from .subject_vm_stage3c22_historical_selection import _canonical_sha256, _stats
from ..experiments.subject_vm_stage3c32_alignment_intervention import (
    STAGE3C32_ALIGNMENT_INTERVENTION_STUDY_SCHEMA,
)

STAGE3C32_ALIGNMENT_INTERVENTION_ASSESSMENT_SCHEMA = (
    "se-subject-vm-stage3c32-alignment-intervention-assessment-v1"
)
_TOL = 1.0e-9


def _load_json(path: str | Path) -> dict[str, Any]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"expected one JSON object: {path}")
    return payload


def _validate_checksum(payload: dict[str, Any], *, field: str, label: str) -> None:
    recorded = str(payload.get(field, ""))
    unsigned = dict(payload)
    unsigned.pop(field, None)
    if not recorded or recorded != _canonical_sha256(unsigned):
        raise ValueError(f"Stage-3C-32 {label} checksum mismatch")


def _runtime_payload(state: dict[str, Any]) -> dict[str, Any]:
    payload = state.get("simulation", {}).get("subject_vm")
    if not isinstance(payload, dict):
        raise ValueError("Stage-3C-32 checkpoint lacks Subject VM runtime")
    return payload


def _trace_arrays(runtime: dict[str, Any]) -> dict[str, np.ndarray]:
    raw = runtime.get("trace_storage", {}).get("arrays")
    if not isinstance(raw, dict):
        raise ValueError("Stage-3C-32 checkpoint lacks trace arrays")
    return {name: np.asarray(value) for name, value in raw.items()}


def _trace_policies(runtime: dict[str, Any]) -> dict[str, Any]:
    raw = runtime.get("trace_storage", {}).get("runtime_policies")
    if not isinstance(raw, dict):
        raise ValueError("Stage-3C-32 checkpoint lacks trace runtime policies")
    return raw


def _array_nbytes(value: Any) -> int:
    if isinstance(value, dict):
        return sum(_array_nbytes(item) for item in value.values())
    if isinstance(value, (list, tuple)):
        return sum(_array_nbytes(item) for item in value)
    if isinstance(value, np.ndarray):
        return int(value.nbytes)
    return 0


def _event_index(trace: dict[str, np.ndarray]) -> dict[tuple[int, int, int], tuple[int, int]]:
    valid = np.asarray(trace["event_valid"], dtype=bool)
    index: dict[tuple[int, int, int], tuple[int, int]] = {}
    for row, slot in zip(*np.nonzero(valid), strict=True):
        key = (
            int(trace["subject_id"][row, slot]),
            int(trace["event_tick"][row, slot]),
            int(trace["event_id"][row, slot]),
        )
        if key in index:
            raise ValueError("Stage-3C-32 duplicate stable event identity")
        index[key] = (int(row), int(slot))
    return index


def _read_checkpoint(path: str | Path) -> tuple[dict[str, Any], dict[str, Any]]:
    metadata, state = read_checkpoint_bundle(Path(path).resolve())
    return metadata, _runtime_payload(state)


def _control_alignment_integrity(
    aligned_runtime: dict[str, Any], ablated_runtime: dict[str, Any], *, port: int
) -> dict[str, Any]:
    aligned = _trace_arrays(aligned_runtime)
    ablated = _trace_arrays(ablated_runtime)
    left_index = _event_index(aligned)
    right_index = _event_index(ablated)
    keys_equal = set(left_index) == set(right_index)
    non_alignment_coordinate_mismatches = 0
    tick_values: dict[int, tuple[list[float], list[float]]] = defaultdict(
        lambda: ([], [])
    )
    assignment_comparisons = 0
    changed_association_identity = 0
    common_assigned = 0
    proposed_update_comparisons = 0
    changed_update_route = 0
    changed_update_delta = 0
    if keys_equal:
        for key in sorted(left_index):
            li = left_index[key]
            ri = right_index[key]
            left_token = np.asarray(aligned["thought_token"][li], dtype=np.float32)
            right_token = np.asarray(ablated["thought_token"][ri], dtype=np.float32)
            mask = np.ones(left_token.shape, dtype=bool)
            mask[int(port)] = False
            non_alignment_coordinate_mismatches += int(
                not np.array_equal(left_token[mask], right_token[mask])
            )
            tick_values[int(key[1])][0].append(float(left_token[int(port)]))
            tick_values[int(key[1])][1].append(float(right_token[int(port)]))

            left_assigned = bool(aligned["association_assigned"][li])
            right_assigned = bool(ablated["association_assigned"][ri])
            assignment_comparisons += 1
            if left_assigned and right_assigned:
                common_assigned += 1
                changed_association_identity += int(
                    int(aligned["associated_event_id"][li])
                    != int(ablated["associated_event_id"][ri])
                )
            elif left_assigned != right_assigned:
                changed_association_identity += 1

            left_update = bool(aligned["update_proposed_any"][li])
            right_update = bool(ablated["update_proposed_any"][ri])
            proposed_update_comparisons += 1
            if left_update != right_update:
                changed_update_route += 1
            elif left_update and right_update:
                left_targets = np.asarray(aligned["binding_target_id"][li])
                right_targets = np.asarray(ablated["binding_target_id"][ri])
                left_family = np.asarray(aligned["update_family_proposed"][li])
                right_family = np.asarray(ablated["update_family_proposed"][ri])
                changed_update_route += int(
                    not np.array_equal(left_targets, right_targets)
                    or not np.array_equal(left_family, right_family)
                )
                changed_update_delta += int(
                    not np.allclose(
                        np.asarray(aligned["update_bounded_delta"][li]),
                        np.asarray(ablated["update_bounded_delta"][ri]),
                        rtol=0.0,
                        atol=1.0e-8,
                    )
                )

    per_tick_marginal_preserved = bool(keys_equal)
    marginal_mismatch_ticks: list[int] = []
    if keys_equal:
        for tick, (left_values, right_values) in sorted(tick_values.items()):
            if not np.array_equal(
                np.sort(np.asarray(left_values, dtype=np.float32)),
                np.sort(np.asarray(right_values, dtype=np.float32)),
            ):
                marginal_mismatch_ticks.append(int(tick))
                per_tick_marginal_preserved = False

    return {
        "event_identity_sets_match": bool(keys_equal),
        "event_count": int(len(left_index)) if keys_equal else 0,
        "non_alignment_coordinate_mismatch_count": int(
            non_alignment_coordinate_mismatches
        ),
        "per_tick_alignment_coordinate_marginal_preserved": bool(
            per_tick_marginal_preserved
        ),
        "marginal_mismatch_ticks": marginal_mismatch_ticks,
        "association_assignment_comparison_count": int(assignment_comparisons),
        "common_assigned_count": int(common_assigned),
        "changed_association_identity_count": int(changed_association_identity),
        "changed_association_identity_fraction": float(
            changed_association_identity / assignment_comparisons
            if assignment_comparisons
            else 0.0
        ),
        "update_route_comparison_count": int(proposed_update_comparisons),
        "changed_update_route_count": int(changed_update_route),
        "changed_update_route_fraction": float(
            changed_update_route / proposed_update_comparisons
            if proposed_update_comparisons
            else 0.0
        ),
        "changed_bounded_delta_count": int(changed_update_delta),
    }


def _window_source_summary(export: dict[str, Any]) -> dict[str, Any]:
    pairs = list(export.get("window_evidence", {}).get("pairs", ()))
    if not pairs:
        raise ValueError("Stage-3C-32 mode export contains no paired windows")
    by_subject: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for pair in pairs:
        live = pair.get("guarded_live", {})
        control = pair.get("read_only_control", {})
        subject_id = int(live.get("stable_subject_id", 0))
        if subject_id <= 0 or subject_id != int(control.get("stable_subject_id", 0)):
            raise ValueError("Stage-3C-32 paired window subject identity mismatch")
        by_subject[subject_id].append(pair)

    subject_fact: list[np.ndarray] = []
    subject_abs: list[np.ndarray] = []
    subject_counts: list[np.ndarray] = []
    for subject_pairs in by_subject.values():
        facts = np.asarray(
            [
                pair["objective_fact_sum_difference_live_minus_control"]
                for pair in subject_pairs
            ],
            dtype=np.float64,
        )
        abs_facts = np.asarray(
            [
                pair["objective_fact_abs_sum_difference_live_minus_control"]
                for pair in subject_pairs
            ],
            dtype=np.float64,
        )
        counts = np.asarray(
            [
                [
                    pair["observation_count_difference_live_minus_control"],
                    pair["success_count_difference_live_minus_control"],
                    pair["failure_count_difference_live_minus_control"],
                ]
                for pair in subject_pairs
            ],
            dtype=np.float64,
        )
        subject_fact.append(np.mean(facts, axis=0))
        subject_abs.append(np.mean(abs_facts, axis=0))
        subject_counts.append(np.mean(counts, axis=0))

    return {
        "paired_window_count": int(len(pairs)),
        "stable_subject_count": int(len(by_subject)),
        "subject_balanced_fact_sum_difference": np.mean(
            np.stack(subject_fact, axis=0), axis=0
        ),
        "subject_balanced_fact_abs_sum_difference": np.mean(
            np.stack(subject_abs, axis=0), axis=0
        ),
        "subject_balanced_count_difference": np.mean(
            np.stack(subject_counts, axis=0), axis=0
        ),
    }


def _coordinate_summary(
    per_source_vectors: list[np.ndarray], *, names: Iterable[str]
) -> tuple[list[dict[str, Any]], list[str], list[str]]:
    matrix = np.stack(per_source_vectors, axis=0)
    coordinate_names = tuple(names)
    if matrix.shape[1] != len(coordinate_names):
        raise ValueError("Stage-3C-32 coordinate width mismatch")
    reports: list[dict[str, Any]] = []
    stable_positive: list[str] = []
    stable_negative: list[str] = []
    for index, name in enumerate(coordinate_names):
        values = np.asarray(matrix[:, index], dtype=np.float64)
        positive = int(np.count_nonzero(values > _TOL))
        negative = int(np.count_nonzero(values < -_TOL))
        zero = int(values.size - positive - negative)
        if positive == values.size:
            stable_positive.append(str(name))
        if negative == values.size:
            stable_negative.append(str(name))
        reports.append(
            {
                "index": int(index),
                "name": str(name),
                "source_values": [float(value) for value in values.tolist()],
                "source_statistics": _stats(values.tolist()),
                "positive_source_count": positive,
                "negative_source_count": negative,
                "zero_source_count": zero,
            }
        )
    return reports, stable_positive, stable_negative


def _graph_storage_arrays(runtime: dict[str, Any]) -> dict[str, np.ndarray]:
    raw = runtime.get("storage", {}).get("arrays")
    if not isinstance(raw, dict):
        raise ValueError("Stage-3C-32 checkpoint lacks graph storage arrays")
    return {name: np.asarray(value) for name, value in raw.items()}


def _graph_parameters_equal(left: dict[str, Any], right: dict[str, Any]) -> bool:
    left_arrays = _graph_storage_arrays(left)
    right_arrays = _graph_storage_arrays(right)
    keys = {
        "node_bias",
        "node_input_gate",
        "node_output_gate",
        "node_trace_gate",
        "edge_forward_gate",
        "edge_eligibility_gate",
    }
    return all(
        name in left_arrays
        and name in right_arrays
        and np.array_equal(left_arrays[name], right_arrays[name])
        for name in keys
    )


def assess_stage3c32_alignment_intervention(
    study_report: dict[str, Any],
) -> dict[str, Any]:
    if study_report.get("schema") != STAGE3C32_ALIGNMENT_INTERVENTION_STUDY_SCHEMA:
        raise ValueError("unsupported Stage-3C-32 intervention study schema")
    _validate_checksum(study_report, field="study_sha256", label="study")
    if not bool(study_report.get("shared_source_checkpoint_across_all_four_arms")):
        raise ValueError("Stage-3C-32 requires one shared checkpoint per source")
    if not bool(study_report.get("forced_rollback")):
        raise ValueError("Stage-3C-32 requires forced rollback")
    if bool(study_report.get("permanent_parameter_retention_authorized")):
        raise ValueError("Stage-3C-32 cannot authorize permanent retention")

    modes = study_report.get("modes", {})
    aligned_mode = modes.get("aligned")
    ablated_mode = modes.get("alignment-ablated")
    if not isinstance(aligned_mode, dict) or not isinstance(ablated_mode, dict):
        raise ValueError("Stage-3C-32 study lacks both alignment modes")
    if aligned_mode.get("runtime_alignment_mode") != ASSOCIATION_ALIGNMENT_IDENTITY:
        raise ValueError("Stage-3C-32 aligned mode identity mismatch")
    if (
        ablated_mode.get("runtime_alignment_mode")
        != ASSOCIATION_ALIGNMENT_CYCLIC_DONOR
    ):
        raise ValueError("Stage-3C-32 ablated mode identity mismatch")
    if not bool(aligned_mode.get("engineering_screen_passed")) or not bool(
        ablated_mode.get("engineering_screen_passed")
    ):
        raise ValueError("Stage-3C-32 requires both mode engineering screens")

    aligned_records = {
        int(item["seed"]): item for item in aligned_mode.get("seed_records", ())
    }
    ablated_records = {
        int(item["seed"]): item for item in ablated_mode.get("seed_records", ())
    }
    seeds = sorted(set(aligned_records) & set(ablated_records))
    if len(seeds) < 3 or set(aligned_records) != set(ablated_records):
        raise ValueError("Stage-3C-32 mode source panels do not match")

    per_source: list[dict[str, Any]] = []
    fact_cross_mode_vectors: list[np.ndarray] = []
    abs_cross_mode_vectors: list[np.ndarray] = []
    count_cross_mode_vectors: list[np.ndarray] = []

    for seed in seeds:
        aligned_record = aligned_records[seed]
        ablated_record = ablated_records[seed]
        if str(aligned_record["source_checkpoint_state_sha256"]) != str(
            ablated_record["source_checkpoint_state_sha256"]
        ):
            raise ValueError("Stage-3C-32 source checkpoint identity differs by mode")

        branch_data: dict[str, dict[str, tuple[dict[str, Any], dict[str, Any]]]] = {
            "aligned": {},
            "alignment-ablated": {},
        }
        for mode_name, record in (
            ("aligned", aligned_record),
            ("alignment-ablated", ablated_record),
        ):
            for role, key in (
                ("guarded-live", "guarded_live_checkpoint"),
                ("read-only-control", "read_only_control_checkpoint"),
            ):
                branch_data[mode_name][role] = _read_checkpoint(record[key])

        aligned_control = branch_data["aligned"]["read-only-control"][1]
        ablated_control = branch_data["alignment-ablated"]["read-only-control"][1]
        aligned_live = branch_data["aligned"]["guarded-live"][1]
        ablated_live = branch_data["alignment-ablated"]["guarded-live"][1]

        aligned_policy = _trace_policies(aligned_control)
        ablated_policy = _trace_policies(ablated_control)
        port = int(study_report["alignment_port"])
        if (
            aligned_policy.get("association_coordinate_alignment_mode")
            != ASSOCIATION_ALIGNMENT_IDENTITY
            or ablated_policy.get("association_coordinate_alignment_mode")
            != ASSOCIATION_ALIGNMENT_CYCLIC_DONOR
            or int(aligned_policy.get("association_coordinate_alignment_port", -1))
            != port
            or int(ablated_policy.get("association_coordinate_alignment_port", -1))
            != port
        ):
            raise ValueError("Stage-3C-32 final checkpoint alignment policy mismatch")

        manipulation = _control_alignment_integrity(
            aligned_control, ablated_control, port=port
        )
        aligned_accounting = aligned_control.get("trace_accounting", {})
        ablated_accounting = ablated_control.get("trace_accounting", {})
        if not isinstance(aligned_accounting, dict) or not isinstance(
            ablated_accounting, dict
        ):
            raise ValueError("Stage-3C-32 trace accounting is missing")
        compute_storage = {
            "aligned_alignment_assignments": int(
                aligned_accounting.get("association_alignment_assignments", -1)
            ),
            "ablated_alignment_assignments": int(
                ablated_accounting.get("association_alignment_assignments", -1)
            ),
            "aligned_evaluated_candidates": int(
                aligned_accounting.get("association_evaluated_candidates", -1)
            ),
            "ablated_evaluated_candidates": int(
                ablated_accounting.get("association_evaluated_candidates", -1)
            ),
            "aligned_self_donor_assignments": int(
                aligned_accounting.get(
                    "association_alignment_self_donor_assignments", -1
                )
            ),
            "ablated_self_donor_assignments": int(
                ablated_accounting.get(
                    "association_alignment_self_donor_assignments", -1
                )
            ),
            "aligned_marginal_mismatches": int(
                aligned_accounting.get("association_alignment_marginal_mismatches", -1)
            ),
            "ablated_marginal_mismatches": int(
                ablated_accounting.get("association_alignment_marginal_mismatches", -1)
            ),
            "aligned_runtime_array_nbytes": int(_array_nbytes(aligned_control)),
            "ablated_runtime_array_nbytes": int(_array_nbytes(ablated_control)),
        }
        compute_storage["alignment_assignment_count_matched"] = bool(
            compute_storage["aligned_alignment_assignments"]
            == compute_storage["ablated_alignment_assignments"]
        )
        compute_storage["candidate_evaluation_count_matched"] = bool(
            compute_storage["aligned_evaluated_candidates"]
            == compute_storage["ablated_evaluated_candidates"]
        )
        compute_storage["runtime_storage_bytes_matched"] = bool(
            compute_storage["aligned_runtime_array_nbytes"]
            == compute_storage["ablated_runtime_array_nbytes"]
        )
        compute_storage["cyclic_donor_has_no_self_assignment"] = bool(
            compute_storage["ablated_self_donor_assignments"] == 0
        )
        compute_storage["both_modes_preserve_tickwise_marginal"] = bool(
            compute_storage["aligned_marginal_mismatches"] == 0
            and compute_storage["ablated_marginal_mismatches"] == 0
        )

        rollback = {
            "aligned_graph_parameters_restored": _graph_parameters_equal(
                aligned_live, aligned_control
            ),
            "ablated_graph_parameters_restored": _graph_parameters_equal(
                ablated_live, ablated_control
            ),
            "aligned_rollback_failures": int(
                aligned_live.get("trace_accounting", {}).get(
                    "transaction_rollback_failures", -1
                )
            ),
            "ablated_rollback_failures": int(
                ablated_live.get("trace_accounting", {}).get(
                    "transaction_rollback_failures", -1
                )
            ),
        }

        aligned_export = _load_json(aligned_record["export"])
        ablated_export = _load_json(ablated_record["export"])
        aligned_summary = _window_source_summary(aligned_export)
        ablated_summary = _window_source_summary(ablated_export)
        fact_cross_mode = (
            ablated_summary["subject_balanced_fact_sum_difference"]
            - aligned_summary["subject_balanced_fact_sum_difference"]
        )
        abs_cross_mode = (
            ablated_summary["subject_balanced_fact_abs_sum_difference"]
            - aligned_summary["subject_balanced_fact_abs_sum_difference"]
        )
        count_cross_mode = (
            ablated_summary["subject_balanced_count_difference"]
            - aligned_summary["subject_balanced_count_difference"]
        )
        fact_cross_mode_vectors.append(fact_cross_mode)
        abs_cross_mode_vectors.append(abs_cross_mode)
        count_cross_mode_vectors.append(count_cross_mode)

        per_source.append(
            {
                "seed": int(seed),
                "source_checkpoint_state_sha256": str(
                    aligned_record["source_checkpoint_state_sha256"]
                ),
                "manipulation": manipulation,
                "compute_and_storage": compute_storage,
                "rollback": rollback,
                "aligned": {
                    "paired_window_count": aligned_summary["paired_window_count"],
                    "stable_subject_count": aligned_summary["stable_subject_count"],
                    "subject_balanced_fact_sum_difference": [
                        float(value)
                        for value in aligned_summary[
                            "subject_balanced_fact_sum_difference"
                        ].tolist()
                    ],
                    "subject_balanced_fact_abs_sum_difference": [
                        float(value)
                        for value in aligned_summary[
                            "subject_balanced_fact_abs_sum_difference"
                        ].tolist()
                    ],
                },
                "alignment_ablated": {
                    "paired_window_count": ablated_summary["paired_window_count"],
                    "stable_subject_count": ablated_summary["stable_subject_count"],
                    "subject_balanced_fact_sum_difference": [
                        float(value)
                        for value in ablated_summary[
                            "subject_balanced_fact_sum_difference"
                        ].tolist()
                    ],
                    "subject_balanced_fact_abs_sum_difference": [
                        float(value)
                        for value in ablated_summary[
                            "subject_balanced_fact_abs_sum_difference"
                        ].tolist()
                    ],
                },
                "cross_mode_ablation_minus_aligned_live_control_effect": {
                    "fact_sum": [float(value) for value in fact_cross_mode.tolist()],
                    "fact_abs_sum": [
                        float(value) for value in abs_cross_mode.tolist()
                    ],
                    "count_difference": [
                        float(value) for value in count_cross_mode.tolist()
                    ],
                },
            }
        )

    fact_coordinates, fact_positive, fact_negative = _coordinate_summary(
        fact_cross_mode_vectors, names=OBJECTIVE_FACT_COORDINATE_NAMES
    )
    abs_coordinates, abs_positive, abs_negative = _coordinate_summary(
        abs_cross_mode_vectors, names=OBJECTIVE_FACT_COORDINATE_NAMES
    )
    count_coordinates, count_positive, count_negative = _coordinate_summary(
        count_cross_mode_vectors,
        names=(
            "observation_count_difference",
            "success_count_difference",
            "failure_count_difference",
        ),
    )

    all_manipulation = all(
        item["manipulation"]["event_identity_sets_match"]
        and item["manipulation"][
            "per_tick_alignment_coordinate_marginal_preserved"
        ]
        and item["manipulation"]["non_alignment_coordinate_mismatch_count"] == 0
        for item in per_source
    )
    all_compute = all(
        item["compute_and_storage"]["alignment_assignment_count_matched"]
        and item["compute_and_storage"]["candidate_evaluation_count_matched"]
        and item["compute_and_storage"]["runtime_storage_bytes_matched"]
        and item["compute_and_storage"]["cyclic_donor_has_no_self_assignment"]
        and item["compute_and_storage"]["both_modes_preserve_tickwise_marginal"]
        for item in per_source
    )
    all_rollback = all(
        item["rollback"]["aligned_graph_parameters_restored"]
        and item["rollback"]["ablated_graph_parameters_restored"]
        and item["rollback"]["aligned_rollback_failures"] == 0
        and item["rollback"]["ablated_rollback_failures"] == 0
        for item in per_source
    )
    changed_selector_all = all(
        item["manipulation"]["changed_association_identity_count"] > 0
        for item in per_source
    )
    changed_update_route_all = all(
        item["manipulation"]["changed_update_route_count"] > 0
        for item in per_source
    )
    objective_effect_source_flags = [
        bool(np.any(np.abs(vector) > _TOL)) for vector in fact_cross_mode_vectors
    ]
    objective_effect_changed_all = all(objective_effect_source_flags)
    selector_change_fractions = [
        float(item["manipulation"]["changed_association_identity_fraction"])
        for item in per_source
    ]
    update_route_change_fractions = [
        float(item["manipulation"]["changed_update_route_fraction"])
        for item in per_source
    ]
    changed_bounded_delta_counts = [
        float(item["manipulation"]["changed_bounded_delta_count"])
        for item in per_source
    ]

    payload = {
        "schema": STAGE3C32_ALIGNMENT_INTERVENTION_ASSESSMENT_SCHEMA,
        "producer_version": __version__,
        "study_sha256": str(study_report["study_sha256"]),
        "stage3c31_assessment_sha256": str(
            study_report["stage3c31_assessment_sha256"]
        ),
        "experimental_factor": (
            "runtime association-visible port-30 subject-time alignment"
        ),
        "four_arm_difference_in_differences": True,
        "source_level_independent_replication_count": int(len(per_source)),
        "per_source": per_source,
        "cross_source_componentwise_effect": {
            "fact_sum_ablation_minus_aligned_live_control": {
                "coordinates": fact_coordinates,
                "stable_positive_coordinate_names": fact_positive,
                "stable_negative_coordinate_names": fact_negative,
            },
            "fact_abs_sum_ablation_minus_aligned_live_control": {
                "coordinates": abs_coordinates,
                "stable_positive_coordinate_names": abs_positive,
                "stable_negative_coordinate_names": abs_negative,
            },
            "count_ablation_minus_aligned_live_control": {
                "coordinates": count_coordinates,
                "stable_positive_coordinate_names": count_positive,
                "stable_negative_coordinate_names": count_negative,
            },
        },
        "cross_source_findings": {
            "manipulation_integrity_passes_in_all_sources": bool(all_manipulation),
            "compute_and_storage_costs_match_in_all_sources": bool(all_compute),
            "forced_rollback_restores_graph_parameters_in_all_sources": bool(
                all_rollback
            ),
            "runtime_alignment_ablation_changes_association_identity_in_all_sources": bool(
                changed_selector_all
            ),
            "runtime_alignment_ablation_changes_update_route_in_all_sources": bool(
                changed_update_route_all
            ),
            "runtime_alignment_ablation_changes_at_least_one_componentwise_live_control_effect_in_all_sources": bool(
                objective_effect_changed_all
            ),
            "sources_with_nonzero_componentwise_live_control_effect": int(
                sum(objective_effect_source_flags)
            ),
            "selector_identity_change_fraction_statistics": _stats(
                selector_change_fractions
            ),
            "update_route_change_fraction_statistics": _stats(
                update_route_change_fractions
            ),
            "changed_bounded_delta_count_statistics": _stats(
                changed_bounded_delta_counts
            ),
            "aligned_total_paired_window_count": int(
                sum(item["aligned"]["paired_window_count"] for item in per_source)
            ),
            "alignment_ablated_total_paired_window_count": int(
                sum(
                    item["alignment_ablated"]["paired_window_count"]
                    for item in per_source
                )
            ),
            "stable_fact_sum_coordinate_count": int(
                len(fact_positive) + len(fact_negative)
            ),
            "stable_fact_abs_sum_coordinate_count": int(
                len(abs_positive) + len(abs_negative)
            ),
        },
        "diagnostic_interpretation": {
            "subject_time_alignment_is_runtime_causal_for_selector_identity_under_this_fixed_bootstrap": bool(
                all_manipulation and all_compute and changed_selector_all
            ),
            "subject_time_alignment_is_runtime_causal_for_update_routing_under_this_fixed_bootstrap": bool(
                all_manipulation and all_compute and changed_update_route_all
            ),
            "componentwise_objective_effect_is_uniformly_signed": bool(
                len(fact_positive) == len(OBJECTIVE_FACT_COORDINATE_NAMES)
                or len(fact_negative) == len(OBJECTIVE_FACT_COORDINATE_NAMES)
            ),
            "current_exposure_supports_source_replicated_objective_fact_causality": bool(
                sum(objective_effect_source_flags) >= 3
            ),
            "objective_coordinates_have_value_semantics": False,
            "alignment_intervention_proves_credit_quality": False,
            "automatic_keep_or_revert_authorized": False,
            "permanent_retention_authorized": False,
            "next_authorized_step": (
                "Run a separately declared longer matched exposure with the same "
                "four-arm source checkpoints, alignment manipulation, compute/storage "
                "contract and forced rollback. The current 3-tick exposure establishes "
                "selector/update-route causality but has objective-fact support in only "
                "one source; do not scalarize or authorize retention."
            ),
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
            "Assess Stage-3C-32 four-arm runtime alignment intervention with "
            "source-balanced component-wise evidence."
        )
    )
    parser.add_argument("--study-report", required=True)
    parser.add_argument("--output", required=True)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    study = _load_json(args.study_report)
    result = assess_stage3c32_alignment_intervention(study)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
