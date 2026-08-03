"""Stage 3C-31 subject-time alignment and objective-fact contrast audit.

The audit reuses the frozen Stage-3C-23 rank-two read-only control traces and
Stage-3C-30 lineage.  It preserves the authoritative raw-threshold candidate
opportunity and isolates within-first-state competitions.  The only analysis
factor is a deterministic tick-wise cyclic permutation of the second visible
coordinate across subjects.  This preserves the exact per-tick marginal
multiset and evaluation count while removing the coordinate's alignment with a
subject's own history.

Winner identity is assessed together with the unchanged objective-fact vectors
that the modulation path would consume.  Objective coordinates remain
component-wise evidence; they are not scalarized into value, reward or an
automatic keep/revert decision.  No runtime or checkpoint state is changed.
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
from ..subject_vm.modulation import modulation_control_ports, objective_fact_vector
from ..subject_vm.trace import OBJECTIVE_EVENT_DELTA_NAMES
from .subject_vm_stage3c13_exposure_adequacy import (
    _load_json,
    _source_records,
    _validate_report_set,
)
from .subject_vm_stage3c22_historical_selection import (
    _aggregate_source_metric,
    _canonical_sha256,
    _gini,
    _stats,
)
from .subject_vm_stage3c23_dual_readout_rank import _validate_study
from .subject_vm_stage3c25_winner_basin import _visible_token
from .subject_vm_stage3c30_weight_robustness import (
    STAGE3C30_WEIGHT_ROBUSTNESS_SCHEMA,
)

STAGE3C31_ALIGNMENT_ABLATION_SCHEMA = (
    "se-subject-vm-stage3c31-alignment-ablation-assessment-v1"
)
_COORDINATE_ATOL = 1e-8
_PAIR_ATOL = 1e-12


def _safe_ratio(numerator: int | float, denominator: int | float) -> float:
    return float(numerator / denominator) if denominator else 0.0


def _finite_stats(values: Iterable[float]) -> dict[str, Any]:
    return _stats(float(value) for value in values if np.isfinite(value))


def _validate_assessment_checksum(payload: dict[str, Any], *, label: str) -> None:
    recorded = str(payload.get("assessment_sha256", ""))
    unsigned = dict(payload)
    unsigned.pop("assessment_sha256", None)
    if not recorded or recorded != _canonical_sha256(unsigned):
        raise ValueError(f"Stage-3C-31 {label} checksum mismatch")


def _fact_coordinate_names() -> tuple[str, ...]:
    return (
        *(f"objective_delta.{name}" for name in OBJECTIVE_EVENT_DELTA_NAMES),
        *(f"resolution_resource_delta.{index}" for index in range(4)),
        *(f"resolution_internal_resource_delta.{index}" for index in range(4)),
        "resolution_energy_cost",
    )


def _objective_facts(trace: dict[str, Any], row: int, slot: int) -> np.ndarray:
    return objective_fact_vector(
        objective_delta=trace["objective_delta"][row, slot],
        resource_delta=trace["resolution_resource_delta"][row, slot],
        internal_resource_delta=trace["resolution_internal_resource_delta"][
            row, slot
        ],
        energy_cost=float(trace["resolution_energy_cost"][row, slot]),
    )


def _tickwise_subject_permutation(
    *,
    valid: np.ndarray,
    subject_ids: np.ndarray,
    event_ticks: np.ndarray,
    tokens: np.ndarray,
    second_port: int,
) -> tuple[dict[tuple[int, int], float], dict[str, Any]]:
    """Build a deterministic per-tick cyclic donor permutation.

    The donor offset advances by one for each successive tick.  Every active
    row receives another subject's exact second-coordinate value, so the
    per-tick multiset is unchanged while no subject retains its own value.
    """

    by_tick: dict[int, list[tuple[int, int, int]]] = {}
    for row, slot in zip(*np.nonzero(valid), strict=True):
        tick = int(event_ticks[row, slot])
        by_tick.setdefault(tick, []).append(
            (int(subject_ids[row, slot]), int(row), int(slot))
        )
    if not by_tick:
        raise ValueError("Stage-3C-31 requires non-empty trace events")

    transformed: dict[tuple[int, int], float] = {}
    marginal_preserved = True
    self_donor_assignment_count = 0
    donor_assignment_count = 0
    shift_by_tick: dict[str, int] = {}
    minimum_tick = min(by_tick)

    for tick in sorted(by_tick):
        events = sorted(by_tick[tick])
        if len(events) < 2:
            raise ValueError(
                "Stage-3C-31 requires at least two subjects at every analyzed tick"
            )
        shift = 1 + ((int(tick) - int(minimum_tick)) % (len(events) - 1))
        shift_by_tick[str(int(tick))] = int(shift)
        original_values = [
            float(tokens[row, slot, second_port]) for _, row, slot in events
        ]
        permuted_values: list[float] = []
        for index, (subject_id, row, _slot) in enumerate(events):
            donor_subject_id, donor_row, donor_slot = events[
                (index + shift) % len(events)
            ]
            donor_assignment_count += 1
            self_donor_assignment_count += int(donor_subject_id == subject_id)
            value = float(tokens[donor_row, donor_slot, second_port])
            transformed[(int(row), int(tick))] = value
            permuted_values.append(value)
        marginal_preserved &= bool(
            np.array_equal(
                np.sort(np.asarray(original_values, dtype=np.float32)),
                np.sort(np.asarray(permuted_values, dtype=np.float32)),
            )
        )

    return transformed, {
        "scheme": "tickwise-cyclic-subject-donor-offset-v1",
        "shift_by_tick": shift_by_tick,
        "tick_count": int(len(by_tick)),
        "donor_assignment_count": int(donor_assignment_count),
        "self_donor_assignment_count": int(self_donor_assignment_count),
        "per_tick_second_coordinate_multiset_preserved_exactly": bool(
            marginal_preserved
        ),
    }


def _rescore_same_state_candidates(
    query: np.ndarray,
    candidates: list[tuple[float, int, int, int, int, np.ndarray]],
    *,
    row: int,
    current_tick: int,
    second_port: int,
    transformed_second: dict[tuple[int, int], float],
) -> list[tuple[float, int, int, int, int, np.ndarray]]:
    transformed_query = np.asarray(query, dtype=np.float64).copy()
    transformed_query[second_port] = transformed_second[(row, current_tick)]
    query_norm = float(np.linalg.norm(transformed_query))
    rescored: list[tuple[float, int, int, int, int, np.ndarray]] = []
    for _, tick, event_id, delay, slot, candidate in candidates:
        transformed_candidate = np.asarray(candidate, dtype=np.float64).copy()
        transformed_candidate[second_port] = transformed_second[(row, int(tick))]
        candidate_norm = float(np.linalg.norm(transformed_candidate))
        score = (
            -2.0
            if query_norm == 0.0 or candidate_norm == 0.0
            else float(
                np.clip(
                    np.dot(transformed_query, transformed_candidate)
                    / (query_norm * candidate_norm),
                    -1.0,
                    1.0,
                )
            )
        )
        rescored.append(
            (
                score,
                int(tick),
                int(event_id),
                int(delay),
                int(slot),
                transformed_candidate,
            )
        )
    rescored.sort(key=lambda item: (-item[0], -item[1], -item[2]))
    return rescored


def _coordinate_evidence(
    baseline: np.ndarray,
    ablation: np.ndarray,
) -> list[dict[str, Any]]:
    names = _fact_coordinate_names()
    if baseline.ndim != 2 or ablation.shape != baseline.shape:
        raise ValueError("Stage-3C-31 objective-fact contrast shape mismatch")
    if baseline.shape[1] != len(names):
        raise ValueError("Stage-3C-31 objective-fact width mismatch")
    result: list[dict[str, Any]] = []
    for index, name in enumerate(names):
        before = np.asarray(baseline[:, index], dtype=np.float64)
        after = np.asarray(ablation[:, index], dtype=np.float64)
        paired = after - before
        positive = int(np.count_nonzero(paired > _PAIR_ATOL))
        negative = int(np.count_nonzero(paired < -_PAIR_ATOL))
        equal = int(paired.size - positive - negative)
        result.append(
            {
                "index": int(index),
                "name": name,
                "baseline_absolute_contrast": _finite_stats(before.tolist()),
                "alignment_ablated_absolute_contrast": _finite_stats(after.tolist()),
                "paired_ablation_minus_baseline": _finite_stats(paired.tolist()),
                "ablation_higher_fraction": _safe_ratio(positive, paired.size),
                "ablation_lower_fraction": _safe_ratio(negative, paired.size),
                "equal_fraction": _safe_ratio(equal, paired.size),
            }
        )
    return result


def _source_alignment_ablation(checkpoint: str | Path) -> dict[str, Any]:
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
            "Stage-3C-31 requires the frozen three-coordinate association-visible token"
        )
    first_port, second_port, constant_port = visible_ports
    transformed_second, permutation = _tickwise_subject_permutation(
        valid=valid,
        subject_ids=subject_ids,
        event_ticks=event_ticks,
        tokens=tokens,
        second_port=second_port,
    )

    requested_query_count = int(np.count_nonzero(requested))
    assigned_query_count = 0
    forced_single_candidate_query_count = 0
    multi_candidate_query_count = 0
    same_state_competition_query_count = 0
    reconstruction_mismatch_count = 0
    baseline_candidate_evaluation_count = 0
    ablation_candidate_evaluation_count = 0
    ablation_threshold_survival_count = 0
    winner_agreement_count = 0
    age_one_baseline_count = 0
    age_one_ablation_count = 0
    baseline_margins: list[float] = []
    ablation_margins: list[float] = []
    baseline_selected_counts: Counter[int] = Counter()
    ablation_selected_counts: Counter[int] = Counter()
    baseline_fact_contrasts: list[np.ndarray] = []
    ablation_fact_contrasts: list[np.ndarray] = []

    for row, slot in zip(*np.nonzero(requested), strict=True):
        current_tick = int(event_ticks[row, slot])
        query = _visible_token(
            tokens[row, slot],
            request_port=int(association_cfg.request_token_port),
            excluded_ports=excluded_ports,
        )
        query_norm = float(np.linalg.norm(query))
        candidates: list[tuple[float, int, int, int, int, np.ndarray]] = []
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
                candidate = _visible_token(
                    tokens[row, historical_slot],
                    request_port=int(association_cfg.request_token_port),
                    excluded_ports=excluded_ports,
                )
                candidate_norm = float(np.linalg.norm(candidate))
                if candidate_norm == 0.0:
                    continue
                score = float(
                    np.clip(
                        np.dot(query, candidate) / (query_norm * candidate_norm),
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
                        int(delay),
                        int(historical_slot),
                        candidate,
                    )
                )
        candidates.sort(key=lambda item: (-item[0], -item[1], -item[2]))
        if bool(candidates) != bool(assigned[row, slot]):
            reconstruction_mismatch_count += 1
            continue
        if not candidates:
            continue

        assigned_query_count += 1
        baseline_winner = candidates[0]
        if (
            int(stored_event_ids[row, slot]) != int(baseline_winner[2])
            or not np.isclose(
                float(stored_similarities[row, slot]),
                float(baseline_winner[0]),
                rtol=0.0,
                atol=1e-6,
            )
        ):
            reconstruction_mismatch_count += 1
        if len(candidates) == 1:
            forced_single_candidate_query_count += 1
            continue
        multi_candidate_query_count += 1

        same_state_candidates = [
            candidate
            for candidate in candidates
            if np.isclose(
                candidate[5][first_port],
                query[first_port],
                rtol=0.0,
                atol=_COORDINATE_ATOL,
            )
        ]
        baseline_is_same_state = bool(
            np.isclose(
                baseline_winner[5][first_port],
                query[first_port],
                rtol=0.0,
                atol=_COORDINATE_ATOL,
            )
        )
        if not baseline_is_same_state or len(same_state_candidates) < 2:
            continue

        same_state_competition_query_count += 1
        baseline_within_state_winner = same_state_candidates[0]
        if int(baseline_within_state_winner[2]) != int(baseline_winner[2]):
            reconstruction_mismatch_count += 1
            continue

        rescored = _rescore_same_state_candidates(
            query,
            same_state_candidates,
            row=int(row),
            current_tick=current_tick,
            second_port=second_port,
            transformed_second=transformed_second,
        )
        ablation_winner = rescored[0]
        baseline_candidate_evaluation_count += len(same_state_candidates)
        ablation_candidate_evaluation_count += len(rescored)
        ablation_threshold_survival_count += sum(
            float(candidate[0]) >= float(association_cfg.similarity_threshold)
            for candidate in rescored
        )
        winner_agreement_count += int(
            int(ablation_winner[2]) == int(baseline_winner[2])
        )
        age_one_baseline_count += int(int(baseline_winner[3]) == 1)
        age_one_ablation_count += int(int(ablation_winner[3]) == 1)
        if len(same_state_candidates) > 1:
            baseline_margins.append(
                float(
                    same_state_candidates[0][0] - same_state_candidates[1][0]
                )
            )
            ablation_margins.append(float(rescored[0][0] - rescored[1][0]))
        baseline_selected_counts[int(baseline_winner[2])] += 1
        ablation_selected_counts[int(ablation_winner[2])] += 1

        current_facts = _objective_facts(trace, int(row), int(slot))
        baseline_fact_contrasts.append(
            np.abs(
                current_facts
                - _objective_facts(trace, int(row), int(baseline_winner[4]))
            )
        )
        ablation_fact_contrasts.append(
            np.abs(
                current_facts
                - _objective_facts(trace, int(row), int(ablation_winner[4]))
            )
        )

    if same_state_competition_query_count == 0:
        raise ValueError("Stage-3C-31 found no within-state candidate competitions")
    baseline_fact_matrix = np.asarray(baseline_fact_contrasts, dtype=np.float64)
    ablation_fact_matrix = np.asarray(ablation_fact_contrasts, dtype=np.float64)
    coordinate_evidence = _coordinate_evidence(
        baseline_fact_matrix, ablation_fact_matrix
    )
    positive_mean_names = [
        item["name"]
        for item in coordinate_evidence
        if float(item["paired_ablation_minus_baseline"]["mean"]) > _PAIR_ATOL
    ]
    negative_mean_names = [
        item["name"]
        for item in coordinate_evidence
        if float(item["paired_ablation_minus_baseline"]["mean"]) < -_PAIR_ATOL
    ]
    zero_mean_names = [
        item["name"]
        for item in coordinate_evidence
        if abs(float(item["paired_ablation_minus_baseline"]["mean"])) <= _PAIR_ATOL
    ]

    return {
        "requested_query_count": requested_query_count,
        "assigned_query_count": assigned_query_count,
        "forced_single_candidate_query_count": forced_single_candidate_query_count,
        "multi_candidate_query_count": multi_candidate_query_count,
        "same_state_competition_query_count": same_state_competition_query_count,
        "reconstructed_score_selection_mismatch_count": int(
            reconstruction_mismatch_count
        ),
        "visible_ports": [int(value) for value in visible_ports],
        "first_coordinate_port": int(first_port),
        "second_coordinate_port": int(second_port),
        "constant_coordinate_port": int(constant_port),
        "permutation": permutation,
        "candidate_evaluation": {
            "baseline_count": int(baseline_candidate_evaluation_count),
            "alignment_ablated_count": int(ablation_candidate_evaluation_count),
            "counts_match": bool(
                baseline_candidate_evaluation_count
                == ablation_candidate_evaluation_count
            ),
            "alignment_ablated_threshold_survival_fraction": _safe_ratio(
                ablation_threshold_survival_count,
                ablation_candidate_evaluation_count,
            ),
        },
        "selection": {
            "winner_agreement_fraction": _safe_ratio(
                winner_agreement_count, same_state_competition_query_count
            ),
            "changed_winner_count": int(
                same_state_competition_query_count - winner_agreement_count
            ),
            "changed_winner_fraction": _safe_ratio(
                same_state_competition_query_count - winner_agreement_count,
                same_state_competition_query_count,
            ),
            "baseline_age_one_fraction": _safe_ratio(
                age_one_baseline_count, same_state_competition_query_count
            ),
            "alignment_ablated_age_one_fraction": _safe_ratio(
                age_one_ablation_count, same_state_competition_query_count
            ),
            "baseline_unique_selected_event_count": int(
                len(baseline_selected_counts)
            ),
            "alignment_ablated_unique_selected_event_count": int(
                len(ablation_selected_counts)
            ),
            "baseline_selection_gini": float(
                _gini(baseline_selected_counts.values())
            ),
            "alignment_ablated_selection_gini": float(
                _gini(ablation_selected_counts.values())
            ),
            "baseline_winner_margin": _finite_stats(baseline_margins),
            "alignment_ablated_winner_margin": _finite_stats(ablation_margins),
        },
        "objective_fact_contrast": {
            "coordinate_count": int(len(coordinate_evidence)),
            "coordinates": coordinate_evidence,
            "positive_mean_paired_delta_names": positive_mean_names,
            "negative_mean_paired_delta_names": negative_mean_names,
            "zero_mean_paired_delta_names": zero_mean_names,
            "mixed_coordinate_directions": bool(
                positive_mean_names and negative_mean_names
            ),
        },
        "source_summary": {
            "changed_winner_fraction": _safe_ratio(
                same_state_competition_query_count - winner_agreement_count,
                same_state_competition_query_count,
            ),
            "positive_objective_fact_coordinate_count": int(
                len(positive_mean_names)
            ),
            "negative_objective_fact_coordinate_count": int(
                len(negative_mean_names)
            ),
            "zero_objective_fact_coordinate_count": int(len(zero_mean_names)),
        },
    }


def assess_stage3c31_alignment_ablation(
    rank2_study: dict[str, Any],
    rank2_component: dict[str, Any],
    rank2_diagnostics: dict[str, Any],
    stage3c30_assessment: dict[str, Any],
) -> dict[str, Any]:
    """Audit subject-time alignment with component-wise objective facts."""
    if stage3c30_assessment.get("schema") != STAGE3C30_WEIGHT_ROBUSTNESS_SCHEMA:
        raise ValueError("Stage-3C-31 requires a Stage-3C-30 assessment")
    _validate_assessment_checksum(
        stage3c30_assessment, label="Stage-3C-30 assessment"
    )
    selected_port = int(
        rank2_study.get("parameters", {}).get(
            "bootstrap_second_readout_input_port", -1
        )
    )
    if selected_port in {0, 11} or selected_port < 0:
        raise ValueError("Stage-3C-31 rank-two readout port is invalid")
    _validate_study(rank2_study, second_port=selected_port)
    _validate_report_set(
        rank2_study, rank2_component, rank2_diagnostics, label="rank2"
    )
    if stage3c30_assessment.get("rank2_study_sha256") != rank2_study.get(
        "study_sha256"
    ):
        raise ValueError("Stage-3C-31 Stage-3C-30 lineage mismatch")
    if not bool(
        stage3c30_assessment["diagnostic_interpretation"].get(
            "second_coordinate_is_required_to_resolve_within_state_winner_identity"
        )
    ):
        raise ValueError("Stage-3C-31 requires the complete Stage-3C-30 screen")

    source_records = _source_records(rank2_study)
    per_source: list[dict[str, Any]] = []
    all_reconstructed = True
    marginal_preserved_all = True
    no_self_donor_all = True
    evaluation_count_matched_all = True
    winner_changed_all = True
    source_positive_sets: list[set[str]] = []
    source_negative_sets: list[set[str]] = []

    for seed in sorted(source_records):
        source = source_records[seed]
        row = _source_alignment_ablation(source["read_only_control_checkpoint"])
        row["seed"] = int(seed)
        all_reconstructed &= (
            row["reconstructed_score_selection_mismatch_count"] == 0
        )
        marginal_preserved_all &= bool(
            row["permutation"][
                "per_tick_second_coordinate_multiset_preserved_exactly"
            ]
        )
        no_self_donor_all &= (
            int(row["permutation"]["self_donor_assignment_count"]) == 0
        )
        evaluation_count_matched_all &= bool(
            row["candidate_evaluation"]["counts_match"]
        )
        winner_changed_all &= (
            float(row["selection"]["changed_winner_fraction"]) > 0.0
        )
        source_positive_sets.append(
            set(
                row["objective_fact_contrast"][
                    "positive_mean_paired_delta_names"
                ]
            )
        )
        source_negative_sets.append(
            set(
                row["objective_fact_contrast"][
                    "negative_mean_paired_delta_names"
                ]
            )
        )
        per_source.append(row)

    if not all_reconstructed:
        raise ValueError("Stage-3C-31 reconstructed selector mismatch")
    stable_positive = sorted(set.intersection(*source_positive_sets))
    stable_negative = sorted(set.intersection(*source_negative_sets))
    any_fact_change_all = all(
        bool(
            row["objective_fact_contrast"]["positive_mean_paired_delta_names"]
            or row["objective_fact_contrast"]["negative_mean_paired_delta_names"]
        )
        for row in per_source
    )

    payload = {
        "schema": STAGE3C31_ALIGNMENT_ABLATION_SCHEMA,
        "producer_version": __version__,
        "rank2_study_sha256": rank2_study["study_sha256"],
        "stage3c30_assessment_sha256": stage3c30_assessment[
            "assessment_sha256"
        ],
        "analysis_only_factor": (
            "deterministically permute only the second visible coordinate across "
            "subjects within each tick, with a changing cyclic donor offset, while "
            "preserving its exact tickwise marginal multiset"
        ),
        "runtime_experimental_factor_changed": False,
        "isolation_contract": {
            "independent_source_count": len(per_source),
            "seeds": sorted(source_records),
            "stage3c30_checksum_and_lineage_verified": True,
            "stored_winner_ids_and_scores_exactly_reconstructed": True,
            "forced_single_candidate_queries_excluded": True,
            "within_first_state_competitions_only": True,
            "authoritative_raw_threshold_candidate_opportunity_reused": True,
            "same_candidate_evaluation_count_in_baseline_and_ablation": bool(
                evaluation_count_matched_all
            ),
            "per_tick_second_coordinate_marginal_preserved": bool(
                marginal_preserved_all
            ),
            "objective_fact_vectors_unchanged_and_evaluated_componentwise": True,
            "same_first_coordinate_constant_coordinate_delay_threshold_latest_top1_target_carrier_delta_exposure_and_rollback": True,
            "highest_independent_replicate": "independent-pre-bootstrap-source-checkpoint",
            "queries_events_subjects_or_windows_are_independent_replicates": False,
        },
        "per_source": per_source,
        "source_balanced_summary": {
            "same_state_competition_query_count": _aggregate_source_metric(
                per_source, ("same_state_competition_query_count",)
            ),
            "changed_winner_fraction": _aggregate_source_metric(
                per_source, ("selection", "changed_winner_fraction")
            ),
            "baseline_age_one_fraction": _aggregate_source_metric(
                per_source, ("selection", "baseline_age_one_fraction")
            ),
            "alignment_ablated_age_one_fraction": _aggregate_source_metric(
                per_source,
                ("selection", "alignment_ablated_age_one_fraction"),
            ),
            "positive_objective_fact_coordinate_count": _aggregate_source_metric(
                per_source,
                ("source_summary", "positive_objective_fact_coordinate_count"),
            ),
            "negative_objective_fact_coordinate_count": _aggregate_source_metric(
                per_source,
                ("source_summary", "negative_objective_fact_coordinate_count"),
            ),
        },
        "cross_source_findings": {
            "tickwise_second_coordinate_marginal_is_preserved_in_all_sources": bool(
                marginal_preserved_all
            ),
            "permutation_assigns_no_subject_its_own_second_coordinate_in_all_sources": bool(
                no_self_donor_all
            ),
            "candidate_evaluation_count_is_matched_in_all_sources": bool(
                evaluation_count_matched_all
            ),
            "subject_time_alignment_ablation_changes_within_state_winner_identity_in_all_sources": bool(
                winner_changed_all
            ),
            "objective_fact_contrast_changes_in_at_least_one_coordinate_in_all_sources": bool(
                any_fact_change_all
            ),
            "stable_positive_mean_paired_delta_coordinate_names": stable_positive,
            "stable_negative_mean_paired_delta_coordinate_names": stable_negative,
        },
        "diagnostic_interpretation": {
            "nonzero_second_coordinate_ordering_depends_on_subject_time_alignment": bool(
                winner_changed_all and marginal_preserved_all and no_self_donor_all
            ),
            "alignment_ablation_preserves_only_a_coordinate_distribution_not_its_subject_history_binding": True,
            "objective_fact_evidence_is_uniformly_better_or_worse_across_all_coordinates": False,
            "selector_agreement_alone_is_sufficient_credit_evidence": False,
            "objective_fact_coordinate_directions_have_value_semantics": False,
            "alignment_ablation_proves_causal_credit_quality": False,
            "next_authorized_step": (
                "Treat subject-time alignment as a mechanically relevant part of "
                "the fixed rank-two address, but retain the mixed component-wise "
                "objective-fact result. Any runtime intervention must use shared "
                "source checkpoints, an exact alignment ablation, matched compute "
                "and storage cost, forced rollback, and score-free component-wise "
                "evaluation; selector agreement cannot authorize learned weighting "
                "or permanent retention."
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
        description=(
            "Assess Stage-3C-31 subject-time alignment and component-wise "
            "objective-fact contrast under a tickwise subject permutation."
        )
    )
    parser.add_argument("--rank2-study-report", required=True)
    parser.add_argument("--rank2-component", required=True)
    parser.add_argument("--rank2-diagnostics", required=True)
    parser.add_argument("--stage3c30-assessment", required=True)
    parser.add_argument("--output", required=True)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    result = assess_stage3c31_alignment_ablation(
        _load_json(args.rank2_study_report),
        _load_json(args.rank2_component),
        _load_json(args.rank2_diagnostics),
        _load_json(args.stage3c30_assessment),
    )
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(result["diagnostic_interpretation"], ensure_ascii=False))


if __name__ == "__main__":
    main()


__all__ = [
    "STAGE3C31_ALIGNMENT_ABLATION_SCHEMA",
    "assess_stage3c31_alignment_ablation",
]
