"""Stage 3C-27 read-only token-trajectory kinematics audit.

The audit reuses the frozen Stage 3C-23 rank-two read-only control traces and
separates three causes that can otherwise all look like a short-age addressing
bias:

* source-boundary requests with only one eligible historical event;
* an exact latest-on-tie choice among equal-scoring candidates;
* strict normalized-dot geometry produced by the local visible-token path.

For every multi-candidate query the analysis compares the age-one candidate
with the best older candidate, measures the local normalized-token step and
turn, and records whether the selected event is the nearest previous recurrence
of the first readout coordinate.  It changes no runtime, addressing, update,
rollback, checkpoint or retention contract.
"""
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
from typing import Any, Iterable

import numpy as np

from .. import __version__
from ..checkpointing import read_checkpoint_bundle
from ..subject_vm.modulation import modulation_control_ports
from .subject_vm_stage3c13_exposure_adequacy import (
    _load_json,
    _source_records,
    _validate_report_set,
)
from .subject_vm_stage3c22_historical_selection import (
    _aggregate_source_metric,
    _canonical_sha256,
    _stats,
)
from .subject_vm_stage3c23_dual_readout_rank import _validate_study
from .subject_vm_stage3c25_winner_basin import _visible_token
from .subject_vm_stage3c26_age_phase_opportunity import (
    STAGE3C26_AGE_PHASE_OPPORTUNITY_SCHEMA,
)

STAGE3C27_TOKEN_KINEMATICS_SCHEMA = (
    "se-subject-vm-stage3c27-token-kinematics-assessment-v1"
)
_SCORE_TIE_ATOL = 1e-8
_COORDINATE_ATOL = 1e-8


def _histogram(values: Iterable[int]) -> dict[str, int]:
    return {str(key): int(value) for key, value in sorted(Counter(values).items())}


def _safe_ratio(numerator: int | float, denominator: int | float) -> float:
    return float(numerator / denominator) if denominator else 0.0


def _median(values: Iterable[float]) -> float:
    materialized = [float(value) for value in values]
    return float(np.median(materialized)) if materialized else 0.0


def _kinematic_rows(checkpoint: str | Path, *, source_tick: int) -> dict[str, Any]:
    _, state = read_checkpoint_bundle(checkpoint)
    subject_vm_cfg = state["config"].subject_vm
    association_cfg = subject_vm_cfg.association
    trace = state["simulation"]["subject_vm"]["trace_storage"]["arrays"]

    valid = np.asarray(trace["event_valid"], dtype=bool)
    requested = np.asarray(trace["association_requested"], dtype=bool) & valid
    assigned = np.asarray(trace["association_assigned"], dtype=bool) & valid
    event_ids = np.asarray(trace["event_id"], dtype=np.uint64)
    event_ticks = np.asarray(trace["event_tick"], dtype=np.int64)
    subject_ids = np.asarray(trace["subject_id"], dtype=np.uint64)
    tokens = np.asarray(trace["thought_token"], dtype=np.float64)
    stored_event_ids = np.asarray(trace["associated_event_id"], dtype=np.uint64)
    stored_similarities = np.asarray(
        trace["association_similarity"], dtype=np.float64
    )
    excluded_ports = modulation_control_ports(subject_vm_cfg.modulation)
    visible_ports = tuple(
        port
        for port in range(tokens.shape[-1])
        if port
        not in {
            int(association_cfg.request_token_port),
            *(int(value) for value in excluded_ports),
        }
    )
    if len(visible_ports) != 3:
        raise ValueError(
            "Stage-3C-27 requires the frozen three-coordinate association-visible token"
        )
    first_readout_port, second_readout_port, constant_port = visible_ports

    rows: list[dict[str, Any]] = []
    forced_rows: list[dict[str, Any]] = []
    reconstruction_mismatch_count = 0
    no_candidate_request_count = 0

    for row, slot in zip(*np.nonzero(requested), strict=True):
        current_tick = int(event_ticks[row, slot])
        query_raw = _visible_token(
            tokens[row, slot],
            request_port=int(association_cfg.request_token_port),
            excluded_ports=excluded_ports,
        )
        query_norm = float(np.linalg.norm(query_raw))
        candidates: list[tuple[float, int, int, int, int, np.ndarray, np.ndarray]] = []
        if query_norm > 0.0:
            for historical_slot in np.flatnonzero(valid[row]).tolist():
                if int(historical_slot) == int(slot):
                    continue
                historical_tick = int(event_ticks[row, historical_slot])
                delay = current_tick - historical_tick
                if delay < int(association_cfg.min_delay_ticks) or delay > int(
                    association_cfg.max_delay_ticks
                ):
                    continue
                candidate_raw = _visible_token(
                    tokens[row, historical_slot],
                    request_port=int(association_cfg.request_token_port),
                    excluded_ports=excluded_ports,
                )
                candidate_norm = float(np.linalg.norm(candidate_raw))
                if candidate_norm == 0.0:
                    continue
                score = float(
                    np.clip(
                        np.dot(query_raw, candidate_raw)
                        / (query_norm * candidate_norm),
                        -1.0,
                        1.0,
                    )
                )
                if score < float(association_cfg.similarity_threshold):
                    continue
                candidates.append(
                    (
                        score,
                        historical_tick,
                        int(event_ids[row, historical_slot]),
                        int(historical_slot),
                        int(delay),
                        candidate_raw,
                        candidate_raw / candidate_norm,
                    )
                )

        candidates.sort(key=lambda item: (-item[0], -item[1], -item[2], item[3]))
        stored_assigned = bool(assigned[row, slot])
        if bool(candidates) != stored_assigned:
            reconstruction_mismatch_count += 1
            continue
        if not candidates:
            no_candidate_request_count += 1
            continue

        best = candidates[0]
        if (
            int(stored_event_ids[row, slot]) != int(best[2])
            or not np.isclose(
                float(stored_similarities[row, slot]),
                float(best[0]),
                rtol=0.0,
                atol=1e-6,
            )
        ):
            reconstruction_mismatch_count += 1

        base = {
            "stable_subject_id": int(subject_ids[row, slot]),
            "query_event_id": int(event_ids[row, slot]),
            "query_tick": current_tick,
            "query_phase": current_tick - int(source_tick),
            "selected_event_id": int(best[2]),
            "selected_event_tick": int(best[1]),
            "selected_age_ticks": int(best[4]),
            "selected_similarity": float(best[0]),
            "eligible_candidate_count": len(candidates),
        }
        if len(candidates) == 1:
            forced_rows.append(base)
            continue

        age_one = next((candidate for candidate in candidates if candidate[4] == 1), None)
        if age_one is None:
            raise ValueError("Stage-3C-27 multi-candidate query lacks an age-one candidate")
        older_best = max(
            (candidate for candidate in candidates if candidate[4] > 1),
            key=lambda item: (item[0], item[1], item[2], -item[3]),
        )
        age_one_gap = float(age_one[0] - older_best[0])
        if age_one_gap > _SCORE_TIE_ATOL:
            age_one_relation = "strict-geometry-win"
        elif age_one_gap < -_SCORE_TIE_ATOL:
            age_one_relation = "older-geometry-win"
        else:
            age_one_relation = "exact-score-tie"

        normalized_query = query_raw / query_norm
        normalized_by_tick: dict[int, np.ndarray] = {}
        raw_by_tick: dict[int, np.ndarray] = {}
        for historical_slot in np.flatnonzero(valid[row]).tolist():
            tick = int(event_ticks[row, historical_slot])
            raw = _visible_token(
                tokens[row, historical_slot],
                request_port=int(association_cfg.request_token_port),
                excluded_ports=excluded_ports,
            )
            norm = float(np.linalg.norm(raw))
            if norm > 0.0:
                raw_by_tick[tick] = raw
                normalized_by_tick[tick] = raw / norm

        previous_tick = current_tick - 1
        previous_raw = raw_by_tick[previous_tick]
        previous_normalized = normalized_by_tick[previous_tick]
        step = normalized_query - previous_normalized
        local_step_l2 = float(np.linalg.norm(step))
        local_angular_distance = float(
            1.0 - np.clip(np.dot(normalized_query, previous_normalized), -1.0, 1.0)
        )
        second_difference_l2 = None
        turn_cosine = None
        if current_tick - 2 in normalized_by_tick:
            previous_step = (
                previous_normalized - normalized_by_tick[current_tick - 2]
            )
            second_difference_l2 = float(np.linalg.norm(step - previous_step))
            previous_step_norm = float(np.linalg.norm(previous_step))
            if local_step_l2 > 0.0 and previous_step_norm > 0.0:
                turn_cosine = float(
                    np.clip(
                        np.dot(previous_step, step)
                        / (previous_step_norm * local_step_l2),
                        -1.0,
                        1.0,
                    )
                )

        first_coordinate_unchanged = bool(
            np.isclose(
                query_raw[first_readout_port],
                previous_raw[first_readout_port],
                rtol=0.0,
                atol=_COORDINATE_ATOL,
            )
        )
        nearest_same_first_coordinate_age = None
        for candidate in sorted(candidates, key=lambda item: item[4]):
            if np.isclose(
                query_raw[first_readout_port],
                candidate[5][first_readout_port],
                rtol=0.0,
                atol=_COORDINATE_ATOL,
            ):
                nearest_same_first_coordinate_age = int(candidate[4])
                break

        row_payload = dict(base)
        row_payload.update(
            {
                "age_one_similarity": float(age_one[0]),
                "best_older_similarity": float(older_best[0]),
                "age_one_minus_best_older_similarity": age_one_gap,
                "age_one_relation": age_one_relation,
                "local_step_l2": local_step_l2,
                "local_angular_distance": local_angular_distance,
                "local_second_difference_l2": second_difference_l2,
                "local_turn_cosine": turn_cosine,
                "first_readout_coordinate_unchanged_from_previous_tick": first_coordinate_unchanged,
                "first_readout_coordinate_delta": float(
                    query_raw[first_readout_port] - previous_raw[first_readout_port]
                ),
                "second_readout_coordinate_delta": float(
                    query_raw[second_readout_port] - previous_raw[second_readout_port]
                ),
                "nearest_same_first_coordinate_age": nearest_same_first_coordinate_age,
                "selected_age_matches_nearest_same_first_coordinate": bool(
                    nearest_same_first_coordinate_age is not None
                    and int(best[4]) == nearest_same_first_coordinate_age
                ),
                "constant_coordinate_unchanged": bool(
                    np.isclose(
                        query_raw[constant_port],
                        previous_raw[constant_port],
                        rtol=0.0,
                        atol=_COORDINATE_ATOL,
                    )
                ),
            }
        )
        rows.append(row_payload)

    strict_age_one = [row for row in rows if row["age_one_relation"] == "strict-geometry-win"]
    exact_ties = [row for row in rows if row["age_one_relation"] == "exact-score-tie"]
    older_geometry = [row for row in rows if row["age_one_relation"] == "older-geometry-win"]
    age_one_selected = [row for row in rows if int(row["selected_age_ticks"]) == 1]
    same_first = [
        row
        for row in rows
        if row["first_readout_coordinate_unchanged_from_previous_tick"]
    ]
    changed_first = [
        row
        for row in rows
        if not row["first_readout_coordinate_unchanged_from_previous_tick"]
    ]

    def _category(group: list[dict[str, Any]]) -> dict[str, Any]:
        return {
            "query_count": len(group),
            "selected_age_histogram": _histogram(
                int(row["selected_age_ticks"]) for row in group
            ),
            "age_one_minus_best_older_similarity": _stats(
                float(row["age_one_minus_best_older_similarity"]) for row in group
            ),
            "local_step_l2": _stats(float(row["local_step_l2"]) for row in group),
            "local_angular_distance": _stats(
                float(row["local_angular_distance"]) for row in group
            ),
            "local_second_difference_l2": _stats(
                float(row["local_second_difference_l2"])
                for row in group
                if row["local_second_difference_l2"] is not None
            ),
            "local_turn_cosine": _stats(
                float(row["local_turn_cosine"])
                for row in group
                if row["local_turn_cosine"] is not None
            ),
        }

    strict_metrics = _category(strict_age_one)
    older_metrics = _category(older_geometry)
    exact_tie_age_one_count = sum(
        int(row["selected_age_ticks"] == 1) for row in exact_ties
    )
    strict_age_one_selected_count = sum(
        int(row["selected_age_ticks"] == 1) for row in strict_age_one
    )
    age_one_multi_count = len(age_one_selected)

    same_first_age_one_count = sum(
        int(row["selected_age_ticks"] == 1) for row in same_first
    )
    changed_first_older_count = sum(
        int(row["selected_age_ticks"] > 1) for row in changed_first
    )
    nearest_same_available = [
        row for row in rows if row["nearest_same_first_coordinate_age"] is not None
    ]
    nearest_same_match_count = sum(
        int(row["selected_age_matches_nearest_same_first_coordinate"])
        for row in nearest_same_available
    )

    phase_records: dict[str, Any] = {}
    for phase in sorted({int(row["query_phase"]) for row in rows}):
        phase_rows = [row for row in rows if int(row["query_phase"]) == phase]
        phase_records[str(phase)] = {
            "multi_candidate_query_count": len(phase_rows),
            "strict_age_one_geometry_win_count": sum(
                int(row["age_one_relation"] == "strict-geometry-win")
                for row in phase_rows
            ),
            "exact_score_tie_count": sum(
                int(row["age_one_relation"] == "exact-score-tie")
                for row in phase_rows
            ),
            "older_geometry_win_count": sum(
                int(row["age_one_relation"] == "older-geometry-win")
                for row in phase_rows
            ),
            "selected_age_histogram": _histogram(
                int(row["selected_age_ticks"]) for row in phase_rows
            ),
            "local_step_l2": _stats(
                float(row["local_step_l2"]) for row in phase_rows
            ),
        }

    return {
        "requested_query_count": int(np.count_nonzero(requested)),
        "assigned_query_count": len(rows) + len(forced_rows),
        "no_candidate_request_count": int(no_candidate_request_count),
        "forced_single_candidate_query_count": len(forced_rows),
        "multi_candidate_query_count": len(rows),
        "reconstructed_score_selection_mismatch_count": int(
            reconstruction_mismatch_count
        ),
        "visible_ports": {
            "first_readout_port": int(first_readout_port),
            "second_readout_port": int(second_readout_port),
            "constant_port": int(constant_port),
        },
        "selected_age_histogram": _histogram(
            [int(row["selected_age_ticks"]) for row in forced_rows]
            + [int(row["selected_age_ticks"]) for row in rows]
        ),
        "multi_candidate_geometry": {
            "strict_age_one_geometry_win_count": len(strict_age_one),
            "exact_age_one_vs_older_score_tie_count": len(exact_ties),
            "older_geometry_win_count": len(older_geometry),
            "age_one_selected_count": age_one_multi_count,
            "strict_geometry_age_one_selected_count": strict_age_one_selected_count,
            "latest_tie_break_age_one_selected_count": exact_tie_age_one_count,
            "strict_geometry_fraction_of_multi_candidate_age_one_selections": _safe_ratio(
                strict_age_one_selected_count, age_one_multi_count
            ),
            "latest_tie_break_fraction_of_multi_candidate_queries": _safe_ratio(
                len(exact_ties), len(rows)
            ),
        },
        "kinematic_groups": {
            "strict_age_one_geometry": strict_metrics,
            "older_geometry": older_metrics,
            "strict_age_one_local_step_median_less_than_older": bool(
                strict_metrics["local_step_l2"]["median"]
                < older_metrics["local_step_l2"]["median"]
            ),
            "older_geometry_turn_cosine_median_less_than_strict_age_one": bool(
                older_metrics["local_turn_cosine"]["median"]
                < strict_metrics["local_turn_cosine"]["median"]
            ),
            "older_to_strict_age_one_local_step_median_ratio": float(
                older_metrics["local_step_l2"]["median"]
                / strict_metrics["local_step_l2"]["median"]
                if strict_metrics["local_step_l2"]["median"] > 0.0
                else 0.0
            ),
        },
        "readout_state_recurrence": {
            "previous_tick_same_first_coordinate_query_count": len(same_first),
            "previous_tick_changed_first_coordinate_query_count": len(changed_first),
            "age_one_selected_when_first_coordinate_unchanged_count": same_first_age_one_count,
            "older_selected_when_first_coordinate_changed_count": changed_first_older_count,
            "age_one_selected_when_first_coordinate_unchanged_fraction": _safe_ratio(
                same_first_age_one_count, len(same_first)
            ),
            "older_selected_when_first_coordinate_changed_fraction": _safe_ratio(
                changed_first_older_count, len(changed_first)
            ),
            "nearest_same_first_coordinate_available_query_count": len(
                nearest_same_available
            ),
            "selected_age_matches_nearest_same_first_coordinate_count": nearest_same_match_count,
            "selected_age_matches_nearest_same_first_coordinate_fraction": _safe_ratio(
                nearest_same_match_count, len(nearest_same_available)
            ),
        },
        "query_phase": phase_records,
        "all_constant_coordinates_unchanged": bool(
            all(row["constant_coordinate_unchanged"] for row in rows)
        ),
    }


def assess_stage3c27_token_kinematics(
    rank2_study: dict[str, Any],
    rank2_component: dict[str, Any],
    rank2_diagnostics: dict[str, Any],
    stage3c26_assessment: dict[str, Any],
) -> dict[str, Any]:
    """Audit strict geometry, tie-break and local token-path contributions."""
    if stage3c26_assessment.get("schema") != STAGE3C26_AGE_PHASE_OPPORTUNITY_SCHEMA:
        raise ValueError("Stage-3C-27 requires a Stage-3C-26 assessment")
    selected_port = int(
        rank2_study.get("parameters", {}).get(
            "bootstrap_second_readout_input_port", -1
        )
    )
    if selected_port in {0, 11} or selected_port < 0:
        raise ValueError("Stage-3C-27 rank-two readout port is invalid")
    _validate_study(rank2_study, second_port=selected_port)
    _validate_report_set(
        rank2_study, rank2_component, rank2_diagnostics, label="rank2"
    )
    if stage3c26_assessment.get("rank2_study_sha256") != rank2_study.get(
        "study_sha256"
    ):
        raise ValueError("Stage-3C-27 Stage-3C-26 lineage mismatch")
    if not bool(
        stage3c26_assessment["isolation_contract"].get(
            "stored_winner_ids_and_scores_exactly_reconstructed"
        )
    ):
        raise ValueError("Stage-3C-27 requires the complete Stage-3C-26 screen")

    source_records = _source_records(rank2_study)
    per_source: list[dict[str, Any]] = []
    all_reconstructed = True
    forced_count_all = True
    speed_order_all = True
    turn_order_all = True
    same_coordinate_age_one_all = True
    changed_coordinate_older_all = True
    strict_geometry_age_one_total = 0
    tie_break_age_one_total = 0
    multi_age_one_total = 0
    multi_query_total = 0

    for seed in sorted(source_records):
        source = source_records[seed]
        row = _kinematic_rows(
            source["read_only_control_checkpoint"],
            source_tick=int(source["source_tick"]),
        )
        row["seed"] = int(seed)
        all_reconstructed &= row["reconstructed_score_selection_mismatch_count"] == 0
        forced_count_all &= row["forced_single_candidate_query_count"] == 16
        speed_order_all &= bool(
            row["kinematic_groups"][
                "strict_age_one_local_step_median_less_than_older"
            ]
        )
        turn_order_all &= bool(
            row["kinematic_groups"][
                "older_geometry_turn_cosine_median_less_than_strict_age_one"
            ]
        )
        same_coordinate_age_one_all &= (
            float(
                row["readout_state_recurrence"][
                    "age_one_selected_when_first_coordinate_unchanged_fraction"
                ]
            )
            >= 0.9
        )
        changed_coordinate_older_all &= (
            float(
                row["readout_state_recurrence"][
                    "older_selected_when_first_coordinate_changed_fraction"
                ]
            )
            >= 0.8
        )
        geometry = row["multi_candidate_geometry"]
        strict_geometry_age_one_total += int(
            geometry["strict_geometry_age_one_selected_count"]
        )
        tie_break_age_one_total += int(
            geometry["latest_tie_break_age_one_selected_count"]
        )
        multi_age_one_total += int(geometry["age_one_selected_count"])
        multi_query_total += int(row["multi_candidate_query_count"])
        per_source.append(row)

    if not all_reconstructed:
        raise ValueError("Stage-3C-27 reconstructed selector mismatch")

    strict_fraction = _safe_ratio(strict_geometry_age_one_total, multi_age_one_total)
    tie_query_fraction = _safe_ratio(tie_break_age_one_total, multi_query_total)
    payload = {
        "schema": STAGE3C27_TOKEN_KINEMATICS_SCHEMA,
        "producer_version": __version__,
        "rank2_study_sha256": rank2_study["study_sha256"],
        "stage3c26_assessment_sha256": stage3c26_assessment["assessment_sha256"],
        "analysis_only_factor": (
            "separate source-boundary single-candidate assignment, exact latest-on-tie "
            "selection and strict local token-geometry wins in the frozen Stage-3C-23 "
            "rank-two read-only control traces"
        ),
        "runtime_experimental_factor_changed": False,
        "isolation_contract": {
            "independent_source_count": len(per_source),
            "seeds": sorted(source_records),
            "stage3c26_lineage_reused": True,
            "stored_winner_ids_and_scores_exactly_reconstructed": True,
            "same_rank2_readout_similarity_threshold_latest_top1_target_carrier_delta_exposure_and_rollback": True,
            "highest_independent_replicate": "independent-pre-bootstrap-source-checkpoint",
            "queries_events_subjects_or_windows_are_independent_replicates": False,
        },
        "per_source": per_source,
        "source_balanced_summary": {
            "strict_age_one_geometry_win_count": _aggregate_source_metric(
                per_source,
                (
                    "multi_candidate_geometry",
                    "strict_age_one_geometry_win_count",
                ),
            ),
            "exact_age_one_vs_older_score_tie_count": _aggregate_source_metric(
                per_source,
                (
                    "multi_candidate_geometry",
                    "exact_age_one_vs_older_score_tie_count",
                ),
            ),
            "strict_age_one_local_step_l2_median": _aggregate_source_metric(
                per_source,
                (
                    "kinematic_groups",
                    "strict_age_one_geometry",
                    "local_step_l2",
                    "median",
                ),
            ),
            "older_geometry_local_step_l2_median": _aggregate_source_metric(
                per_source,
                (
                    "kinematic_groups",
                    "older_geometry",
                    "local_step_l2",
                    "median",
                ),
            ),
            "older_to_strict_age_one_local_step_median_ratio": _aggregate_source_metric(
                per_source,
                (
                    "kinematic_groups",
                    "older_to_strict_age_one_local_step_median_ratio",
                ),
            ),
            "age_one_selected_when_first_coordinate_unchanged_fraction": _aggregate_source_metric(
                per_source,
                (
                    "readout_state_recurrence",
                    "age_one_selected_when_first_coordinate_unchanged_fraction",
                ),
            ),
            "older_selected_when_first_coordinate_changed_fraction": _aggregate_source_metric(
                per_source,
                (
                    "readout_state_recurrence",
                    "older_selected_when_first_coordinate_changed_fraction",
                ),
            ),
            "selected_age_matches_nearest_same_first_coordinate_fraction": _aggregate_source_metric(
                per_source,
                (
                    "readout_state_recurrence",
                    "selected_age_matches_nearest_same_first_coordinate_fraction",
                ),
            ),
        },
        "cross_source_findings": {
            "sixteen_source_boundary_assignments_are_forced_in_all_sources": forced_count_all,
            "strict_geometry_accounts_for_at_least_99_percent_of_multi_candidate_age_one_selections": bool(
                strict_fraction >= 0.99
            ),
            "exact_latest_tie_break_contributes_less_than_one_percent_of_multi_candidate_queries": bool(
                tie_query_fraction < 0.01
            ),
            "strict_age_one_local_step_median_is_lower_than_older_geometry_in_all_sources": speed_order_all,
            "older_geometry_turn_cosine_median_is_lower_than_strict_age_one_in_all_sources": turn_order_all,
            "unchanged_first_readout_coordinate_predicts_age_one_selection_at_least_90_percent_in_all_sources": same_coordinate_age_one_all,
            "changed_first_readout_coordinate_predicts_older_selection_at_least_80_percent_in_all_sources": changed_coordinate_older_all,
            "strict_geometry_age_one_selection_total": strict_geometry_age_one_total,
            "latest_tie_break_age_one_selection_total": tie_break_age_one_total,
            "multi_candidate_age_one_selection_total": multi_age_one_total,
            "multi_candidate_query_total": multi_query_total,
        },
        "diagnostic_interpretation": {
            "latest_tie_break_is_the_primary_age_one_basin_driver": False,
            "source_boundary_forcing_contributes_to_total_age_one_selection": forced_count_all,
            "local_token_geometry_is_the_primary_multi_candidate_age_one_driver": bool(
                strict_fraction >= 0.99
            ),
            "first_readout_state_persistence_and_recurrence_contribute_to_selected_age": bool(
                same_coordinate_age_one_all and changed_coordinate_older_all
            ),
            "local_speed_or_curvature_has_fixed_value_semantics": False,
            "trajectory_kinematics_proves_causal_credit_quality": False,
            "next_authorized_step": (
                "Hold the Stage-3C-23 rank-two readout, normalized-dot similarity, threshold, "
                "latest/top-1, target/carrier, update scale, exposure and rollback fixed. "
                "Read-only audit whether the first-coordinate state transitions and the slowly "
                "moving second coordinate form discrete sampling phases or recurrent geometric "
                "basins across subjects before any age penalty, opportunity normalization, "
                "random tie-break, learned weight or permanent retention change."
            ),
        },
        "fixed_cognition_engineering_shaping_aid": True,
        "evolved_topology": False,
        "universal_attention_claim": False,
        "universal_scalar_objective": False,
        "permanent_parameter_retention_authorized": False,
        "automatic_keep_or_revert_authorized": False,
        "causal_effect_authorized": False,
        "learning_claim_authorized": False,
        "subjecthood_claim_authorized": False,
        "runtime_or_checkpoint_schema_changed": False,
        "runtime_memory_growth_bytes": 0,
    }
    payload["assessment_sha256"] = _canonical_sha256(payload)
    return payload


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Assess Stage-3C-27 local visible-token kinematics and tie-break contribution."
    )
    parser.add_argument("--rank2-study-report", required=True)
    parser.add_argument("--rank2-component", required=True)
    parser.add_argument("--rank2-diagnostics", required=True)
    parser.add_argument("--stage3c26-assessment", required=True)
    parser.add_argument("--output", required=True)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    result = assess_stage3c27_token_kinematics(
        _load_json(args.rank2_study_report),
        _load_json(args.rank2_component),
        _load_json(args.rank2_diagnostics),
        _load_json(args.stage3c26_assessment),
    )
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result["diagnostic_interpretation"], ensure_ascii=False))


if __name__ == "__main__":
    main()


__all__ = [
    "STAGE3C27_TOKEN_KINEMATICS_SCHEMA",
    "assess_stage3c27_token_kinematics",
]
