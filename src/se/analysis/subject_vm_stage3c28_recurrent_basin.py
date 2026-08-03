"""Stage 3C-28 read-only discrete-state and subject-anchored basin audit.

The audit keeps the frozen Stage-3C-23 rank-two addressing contract and asks
whether the recurrent winner basin diagnosed in Stage 3C-27 is a globally
synchronised sampling phase, an exact-token recurrence, or a within-subject
geometric basin formed by a shared discrete first-coordinate codebook and a
slow subject-specific second coordinate.

No runtime, addressing, checkpoint, update, rollback or retention contract is
changed.
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
from .subject_vm_stage3c27_token_kinematics import (
    STAGE3C27_TOKEN_KINEMATICS_SCHEMA,
)

STAGE3C28_RECURRENT_BASIN_SCHEMA = (
    "se-subject-vm-stage3c28-recurrent-basin-assessment-v1"
)
_COORDINATE_ATOL = 1e-8


def _safe_ratio(numerator: int | float, denominator: int | float) -> float:
    return float(numerator / denominator) if denominator else 0.0


def _histogram(values: Iterable[float]) -> dict[str, int]:
    rounded = (f"{float(value):.9f}" for value in values)
    return {key: int(value) for key, value in sorted(Counter(rounded).items())}


def _source_basin(checkpoint: str | Path) -> dict[str, Any]:
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
            "Stage-3C-28 requires the frozen three-coordinate association-visible token"
        )
    first_port, second_port, constant_port = visible_ports

    trajectories: dict[int, list[tuple[int, np.ndarray]]] = {}
    first_values: list[float] = []
    second_steps: list[float] = []
    subject_second_means: list[float] = []
    subject_second_variances: list[float] = []
    for row in range(valid.shape[0]):
        slots = np.flatnonzero(valid[row])
        if slots.size == 0:
            continue
        ordered = slots[np.argsort(event_ticks[row, slots])]
        subject_id = int(subject_ids[row, ordered[0]])
        trajectory = [
            (
                int(event_ticks[row, slot]),
                np.asarray(tokens[row, slot, list(visible_ports)], dtype=np.float64),
            )
            for slot in ordered
        ]
        trajectories[subject_id] = trajectory
        first_values.extend(float(value[1][0]) for value in trajectory)
        second_series = np.asarray([value[1][1] for value in trajectory], dtype=float)
        subject_second_means.append(float(np.mean(second_series)))
        subject_second_variances.append(float(np.var(second_series)))
        second_steps.extend(float(value) for value in np.diff(second_series))

    same_phase_transition_agreements: list[float] = []
    transition_sequences: list[list[tuple[float, float]]] = []
    for trajectory in trajectories.values():
        transition_sequences.append(
            [
                (
                    round(float(trajectory[index - 1][1][0]), 9),
                    round(float(trajectory[index][1][0]), 9),
                )
                for index in range(1, len(trajectory))
            ]
        )
    if transition_sequences:
        phase_count = len(transition_sequences[0])
        for phase in range(phase_count):
            phase_transitions = [sequence[phase] for sequence in transition_sequences]
            agreements = [
                int(phase_transitions[left] == phase_transitions[right])
                for left in range(len(phase_transitions))
                for right in range(left + 1, len(phase_transitions))
            ]
            same_phase_transition_agreements.append(float(np.mean(agreements)))

    cross_phase_agreements: list[int] = []
    for left in range(len(transition_sequences)):
        for right in range(left + 1, len(transition_sequences)):
            for left_phase, left_transition in enumerate(transition_sequences[left]):
                for right_phase, right_transition in enumerate(
                    transition_sequences[right]
                ):
                    if left_phase == right_phase:
                        continue
                    cross_phase_agreements.append(
                        int(left_transition == right_transition)
                    )

    candidate_count = 0
    same_first_candidate_count = 0
    queries_with_different_first_candidate = 0
    winner_same_first_count = 0
    winner_exact_visible_repeat_count = 0
    same_first_winner_count = 0
    same_first_winner_nearest_second_count = 0
    globally_nearest_second_winner_count = 0
    reconstruction_mismatch_count = 0
    assigned_query_count = 0

    for row, slot in zip(*np.nonzero(requested), strict=True):
        current_tick = int(event_ticks[row, slot])
        query = _visible_token(
            tokens[row, slot],
            request_port=int(association_cfg.request_token_port),
            excluded_ports=excluded_ports,
        )
        query_norm = float(np.linalg.norm(query))
        candidates: list[tuple[float, int, int, int, np.ndarray]] = []
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
                        candidate,
                    )
                )
        candidates.sort(key=lambda item: (-item[0], -item[1], -item[2]))
        if bool(candidates) != bool(assigned[row, slot]):
            reconstruction_mismatch_count += 1
            continue
        if not candidates:
            continue
        winner = candidates[0]
        assigned_query_count += 1
        if (
            int(stored_event_ids[row, slot]) != int(winner[2])
            or not np.isclose(
                float(stored_similarities[row, slot]),
                float(winner[0]),
                rtol=0.0,
                atol=1e-6,
            )
        ):
            reconstruction_mismatch_count += 1

        same_first = [
            candidate
            for candidate in candidates
            if np.isclose(
                candidate[4][first_port],
                query[first_port],
                rtol=0.0,
                atol=_COORDINATE_ATOL,
            )
        ]
        candidate_count += len(candidates)
        same_first_candidate_count += len(same_first)
        queries_with_different_first_candidate += int(
            len(same_first) < len(candidates)
        )

        winner_same_first = bool(
            np.isclose(
                winner[4][first_port],
                query[first_port],
                rtol=0.0,
                atol=_COORDINATE_ATOL,
            )
        )
        winner_same_first_count += int(winner_same_first)
        winner_exact_visible_repeat_count += int(
            np.allclose(
                winner[4][list(visible_ports)],
                query[list(visible_ports)],
                rtol=0.0,
                atol=_COORDINATE_ATOL,
            )
        )
        globally_nearest = min(
            candidates,
            key=lambda item: (
                abs(float(item[4][second_port] - query[second_port])),
                -item[1],
                -item[2],
            ),
        )
        globally_nearest_second_winner_count += int(globally_nearest[2] == winner[2])
        if winner_same_first:
            same_first_winner_count += 1
            nearest_same_first = min(
                same_first,
                key=lambda item: (
                    abs(float(item[4][second_port] - query[second_port])),
                    -item[1],
                    -item[2],
                ),
            )
            same_first_winner_nearest_second_count += int(
                nearest_same_first[2] == winner[2]
            )

    between_subject_variance = float(np.var(subject_second_means))
    mean_within_subject_variance = float(np.mean(subject_second_variances))
    second_coordinate_icc = _safe_ratio(
        between_subject_variance,
        between_subject_variance + mean_within_subject_variance,
    )
    same_phase_transition_agreement = float(
        np.mean(same_phase_transition_agreements)
    )
    cross_phase_transition_agreement = float(np.mean(cross_phase_agreements))
    same_first_candidate_fraction = _safe_ratio(
        same_first_candidate_count, candidate_count
    )
    winner_same_first_fraction = _safe_ratio(
        winner_same_first_count, assigned_query_count
    )

    return {
        "requested_query_count": int(np.count_nonzero(requested)),
        "assigned_query_count": assigned_query_count,
        "reconstructed_score_selection_mismatch_count": reconstruction_mismatch_count,
        "visible_ports": {
            "first_readout_port": int(first_port),
            "second_readout_port": int(second_port),
            "constant_port": int(constant_port),
        },
        "shared_discrete_codebook": {
            "first_coordinate_value_histogram": _histogram(first_values),
            "unique_first_coordinate_values": sorted(
                {round(float(value), 9) for value in first_values}
            ),
            "same_phase_transition_pair_agreement": same_phase_transition_agreement,
            "cross_phase_transition_pair_agreement": cross_phase_transition_agreement,
            "same_minus_cross_phase_transition_agreement": float(
                same_phase_transition_agreement - cross_phase_transition_agreement
            ),
        },
        "subject_anchored_second_coordinate": {
            "between_subject_variance": between_subject_variance,
            "mean_within_subject_temporal_variance": mean_within_subject_variance,
            "intraclass_correlation": second_coordinate_icc,
            "absolute_step": _stats(abs(value) for value in second_steps),
            "exact_zero_step_fraction": _safe_ratio(
                sum(
                    int(np.isclose(value, 0.0, rtol=0.0, atol=_COORDINATE_ATOL))
                    for value in second_steps
                ),
                len(second_steps),
            ),
        },
        "recurrent_geometric_basin": {
            "eligible_candidate_count": candidate_count,
            "same_first_coordinate_candidate_count": same_first_candidate_count,
            "same_first_coordinate_candidate_fraction": same_first_candidate_fraction,
            "queries_with_different_first_coordinate_candidate_count": queries_with_different_first_candidate,
            "queries_with_different_first_coordinate_candidate_fraction": _safe_ratio(
                queries_with_different_first_candidate, assigned_query_count
            ),
            "winner_same_first_coordinate_count": winner_same_first_count,
            "winner_same_first_coordinate_fraction": winner_same_first_fraction,
            "winner_same_first_coordinate_enrichment_over_candidate_fraction": _safe_ratio(
                winner_same_first_fraction, same_first_candidate_fraction
            ),
            "same_first_winner_count": same_first_winner_count,
            "same_first_winner_is_nearest_second_within_state_count": same_first_winner_nearest_second_count,
            "same_first_winner_is_nearest_second_within_state_fraction": _safe_ratio(
                same_first_winner_nearest_second_count, same_first_winner_count
            ),
            "winner_is_globally_nearest_second_coordinate_count": globally_nearest_second_winner_count,
            "winner_is_globally_nearest_second_coordinate_fraction": _safe_ratio(
                globally_nearest_second_winner_count, assigned_query_count
            ),
            "exact_full_visible_vector_winner_repeat_count": winner_exact_visible_repeat_count,
            "exact_full_visible_vector_winner_repeat_fraction": _safe_ratio(
                winner_exact_visible_repeat_count, assigned_query_count
            ),
        },
    }


def assess_stage3c28_recurrent_basin(
    rank2_study: dict[str, Any],
    rank2_component: dict[str, Any],
    rank2_diagnostics: dict[str, Any],
    stage3c27_assessment: dict[str, Any],
) -> dict[str, Any]:
    """Audit shared codebook, synchrony and subject-anchored recurrent basins."""
    if stage3c27_assessment.get("schema") != STAGE3C27_TOKEN_KINEMATICS_SCHEMA:
        raise ValueError("Stage-3C-28 requires a Stage-3C-27 assessment")
    selected_port = int(
        rank2_study.get("parameters", {}).get(
            "bootstrap_second_readout_input_port", -1
        )
    )
    if selected_port in {0, 11} or selected_port < 0:
        raise ValueError("Stage-3C-28 rank-two readout port is invalid")
    _validate_study(rank2_study, second_port=selected_port)
    _validate_report_set(
        rank2_study, rank2_component, rank2_diagnostics, label="rank2"
    )
    if stage3c27_assessment.get("rank2_study_sha256") != rank2_study.get(
        "study_sha256"
    ):
        raise ValueError("Stage-3C-28 Stage-3C-27 lineage mismatch")
    if not bool(
        stage3c27_assessment["diagnostic_interpretation"].get(
            "local_token_geometry_is_the_primary_multi_candidate_age_one_driver"
        )
    ):
        raise ValueError("Stage-3C-28 requires the complete Stage-3C-27 screen")

    source_records = _source_records(rank2_study)
    per_source: list[dict[str, Any]] = []
    all_reconstructed = True
    common_codebook: set[float] | None = None
    no_global_transition_phase_all = True
    subject_anchor_all = True
    basin_enrichment_all = True
    alternatives_present_all = True
    nearest_within_state_all = True
    no_exact_repeat_all = True

    for seed in sorted(source_records):
        source = source_records[seed]
        row = _source_basin(source["read_only_control_checkpoint"])
        row["seed"] = int(seed)
        values = set(
            float(value)
            for value in row["shared_discrete_codebook"][
                "unique_first_coordinate_values"
            ]
        )
        common_codebook = values if common_codebook is None else common_codebook & values
        all_reconstructed &= row["reconstructed_score_selection_mismatch_count"] == 0
        no_global_transition_phase_all &= (
            abs(
                float(
                    row["shared_discrete_codebook"]['same_minus_cross_phase_transition_agreement']
                )
            )
            < 0.05
        )
        subject_anchor_all &= (
            float(
                row["subject_anchored_second_coordinate"]["intraclass_correlation"]
            )
            >= 0.99
        )
        basin = row["recurrent_geometric_basin"]
        basin_enrichment_all &= (
            float(basin["winner_same_first_coordinate_fraction"])
            > float(basin["same_first_coordinate_candidate_fraction"])
        )
        alternatives_present_all &= (
            float(
                basin["queries_with_different_first_coordinate_candidate_fraction"]
            )
            >= 0.85
        )
        nearest_within_state_all &= bool(np.isclose(
            float(
                basin[
                    "same_first_winner_is_nearest_second_within_state_fraction"
                ]
            ),
            1.0,
            rtol=0.0,
            atol=1e-12,
        ))
        no_exact_repeat_all &= int(
            basin["exact_full_visible_vector_winner_repeat_count"]
        ) == 0
        per_source.append(row)

    if not all_reconstructed:
        raise ValueError("Stage-3C-28 reconstructed selector mismatch")

    common_values = sorted(common_codebook or set())
    payload = {
        "schema": STAGE3C28_RECURRENT_BASIN_SCHEMA,
        "producer_version": __version__,
        "rank2_study_sha256": rank2_study["study_sha256"],
        "stage3c27_assessment_sha256": stage3c27_assessment["assessment_sha256"],
        "analysis_only_factor": (
            "separate a shared discrete first-coordinate codebook, cross-subject "
            "transition synchrony, subject-anchored second-coordinate drift and "
            "within-subject recurrent winner basins in the frozen Stage-3C-23 "
            "rank-two read-only control traces"
        ),
        "runtime_experimental_factor_changed": False,
        "isolation_contract": {
            "independent_source_count": len(per_source),
            "seeds": sorted(source_records),
            "stage3c27_lineage_reused": True,
            "stored_winner_ids_and_scores_exactly_reconstructed": True,
            "same_rank2_readout_similarity_threshold_latest_top1_target_carrier_delta_exposure_and_rollback": True,
            "highest_independent_replicate": "independent-pre-bootstrap-source-checkpoint",
            "queries_events_subjects_or_windows_are_independent_replicates": False,
        },
        "per_source": per_source,
        "source_balanced_summary": {
            "same_minus_cross_phase_transition_agreement": _aggregate_source_metric(
                per_source,
                (
                    "shared_discrete_codebook",
                    "same_minus_cross_phase_transition_agreement",
                ),
            ),
            "second_coordinate_intraclass_correlation": _aggregate_source_metric(
                per_source,
                (
                    "subject_anchored_second_coordinate",
                    "intraclass_correlation",
                ),
            ),
            "second_coordinate_absolute_step_median": _aggregate_source_metric(
                per_source,
                (
                    "subject_anchored_second_coordinate",
                    "absolute_step",
                    "median",
                ),
            ),
            "same_first_candidate_fraction": _aggregate_source_metric(
                per_source,
                (
                    "recurrent_geometric_basin",
                    "same_first_coordinate_candidate_fraction",
                ),
            ),
            "winner_same_first_fraction": _aggregate_source_metric(
                per_source,
                (
                    "recurrent_geometric_basin",
                    "winner_same_first_coordinate_fraction",
                ),
            ),
            "winner_same_first_enrichment": _aggregate_source_metric(
                per_source,
                (
                    "recurrent_geometric_basin",
                    "winner_same_first_coordinate_enrichment_over_candidate_fraction",
                ),
            ),
            "queries_with_different_first_candidate_fraction": _aggregate_source_metric(
                per_source,
                (
                    "recurrent_geometric_basin",
                    "queries_with_different_first_coordinate_candidate_fraction",
                ),
            ),
        },
        "cross_source_findings": {
            "common_first_coordinate_codebook_values": common_values,
            "at_least_three_first_coordinate_values_are_shared_by_all_sources": bool(
                len(common_values) >= 3
            ),
            "same_tick_transition_agreement_has_no_consistent_large_excess_over_cross_tick_baseline": no_global_transition_phase_all,
            "second_coordinate_is_subject_anchored_in_all_sources": subject_anchor_all,
            "winner_same_first_state_is_enriched_over_candidate_availability_in_all_sources": basin_enrichment_all,
            "different_first_state_candidates_remain_available_for_at_least_85_percent_of_queries_in_all_sources": alternatives_present_all,
            "same_state_winner_is_nearest_second_coordinate_within_that_state_in_all_sources": nearest_within_state_all,
            "no_selected_winner_is_an_exact_full_visible_vector_repeat": no_exact_repeat_all,
        },
        "diagnostic_interpretation": {
            "shared_discrete_codebook_is_globally_synchronized_sampling_phase": False,
            "cross_subject_phase_synchrony_is_supported": False,
            "second_coordinate_is_a_slow_subject_specific_anchor": subject_anchor_all,
            "winner_reuse_is_consistent_with_within_subject_recurrent_geometric_basins": bool(
                basin_enrichment_all and nearest_within_state_all
            ),
            "winner_reuse_is_explained_by_exact_token_duplication": False,
            "discrete_state_or_subject_anchor_has_fixed_value_semantics": False,
            "recurrent_basin_proves_causal_credit_quality": False,
            "next_authorized_step": (
                "Hold the Stage-3C-23 rank-two readout, normalized-dot similarity, "
                "threshold, latest/top-1, target/carrier, update scale, exposure and "
                "rollback fixed. Read-only audit whether first-state transition classes "
                "and subject-anchored second-coordinate drift predict basin occupancy "
                "after conditioning on candidate opportunity; do not add age penalties, "
                "randomization, learned weights or permanent retention."
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
            "Assess Stage-3C-28 shared discrete codebook, transition synchrony "
            "and subject-anchored recurrent token basins."
        )
    )
    parser.add_argument("--rank2-study-report", required=True)
    parser.add_argument("--rank2-component", required=True)
    parser.add_argument("--rank2-diagnostics", required=True)
    parser.add_argument("--stage3c27-assessment", required=True)
    parser.add_argument("--output", required=True)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    result = assess_stage3c28_recurrent_basin(
        _load_json(args.rank2_study_report),
        _load_json(args.rank2_component),
        _load_json(args.rank2_diagnostics),
        _load_json(args.stage3c27_assessment),
    )
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result["diagnostic_interpretation"], ensure_ascii=False))


if __name__ == "__main__":
    main()


__all__ = [
    "STAGE3C28_RECURRENT_BASIN_SCHEMA",
    "assess_stage3c28_recurrent_basin",
]
