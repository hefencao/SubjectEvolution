"""Stage 3C-29 read-only transition-class and basin-occupancy audit.

The audit keeps the frozen Stage-3C-23 rank-two addressing contract and asks
whether recurrent winner occupancy is explained by replay of the same discrete
first-coordinate transition class, or by subject-anchored second-coordinate
locality after candidate opportunity and source-boundary forcing are separated.

Only multi-candidate queries are used for the opportunity-conditioned screens.
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
from .subject_vm_stage3c28_recurrent_basin import (
    STAGE3C28_RECURRENT_BASIN_SCHEMA,
)

STAGE3C29_TRANSITION_OCCUPANCY_SCHEMA = (
    "se-subject-vm-stage3c29-transition-occupancy-assessment-v1"
)
_COORDINATE_ATOL = 1e-8
_TRANSITION_CLASSES = ("boundary", "down", "stay", "up")


def _safe_ratio(numerator: int | float, denominator: int | float) -> float:
    return float(numerator / denominator) if denominator else 0.0


def _transition_class(previous: float | None, current: float) -> str:
    if previous is None:
        return "boundary"
    if np.isclose(current, previous, rtol=0.0, atol=_COORDINATE_ATOL):
        return "stay"
    return "up" if current > previous else "down"


def _class_rates(
    opportunities: Counter[str], selections: Counter[str]
) -> dict[str, dict[str, int | float]]:
    return {
        name: {
            "opportunity_count": int(opportunities[name]),
            "selection_count": int(selections[name]),
            "selection_rate_given_opportunity": _safe_ratio(
                selections[name], opportunities[name]
            ),
        }
        for name in _TRANSITION_CLASSES
    }


def _finite_stats(values: Iterable[float]) -> dict[str, float | int]:
    finite = [float(value) for value in values if np.isfinite(value)]
    return _stats(finite)


def _validate_assessment_checksum(payload: dict[str, Any], *, label: str) -> None:
    recorded = str(payload.get("assessment_sha256", ""))
    unsigned = dict(payload)
    unsigned.pop("assessment_sha256", None)
    if not recorded or recorded != _canonical_sha256(unsigned):
        raise ValueError(f"Stage-3C-29 {label} checksum mismatch")


def _source_transition_occupancy(checkpoint: str | Path) -> dict[str, Any]:
    _, state = read_checkpoint_bundle(checkpoint)
    subject_vm_cfg = state["config"].subject_vm
    association_cfg = subject_vm_cfg.association
    trace = state["simulation"]["subject_vm"]["trace_storage"]["arrays"]

    valid = np.asarray(trace["event_valid"], dtype=bool)
    requested = np.asarray(trace["association_requested"], dtype=bool) & valid
    assigned = np.asarray(trace["association_assigned"], dtype=bool) & valid
    event_ids = np.asarray(trace["event_id"], dtype=np.uint64)
    event_ticks = np.asarray(trace["event_tick"], dtype=np.int64)
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
            "Stage-3C-29 requires the frozen three-coordinate association-visible token"
        )
    first_port, second_port, constant_port = visible_ports

    event_meta: dict[tuple[int, int], dict[str, Any]] = {}
    for row in range(valid.shape[0]):
        slots = np.flatnonzero(valid[row])
        if slots.size == 0:
            continue
        ordered = slots[np.argsort(event_ticks[row, slots])]
        previous_first: float | None = None
        previous_second: float | None = None
        for slot in ordered.tolist():
            token = _visible_token(
                tokens[row, slot],
                request_port=int(association_cfg.request_token_port),
                excluded_ports=excluded_ports,
            )
            first = float(token[first_port])
            second = float(token[second_port])
            event_meta[(row, int(slot))] = {
                "transition_class": _transition_class(previous_first, first),
                "first_coordinate": first,
                "second_coordinate": second,
                "second_coordinate_step": (
                    None if previous_second is None else second - previous_second
                ),
            }
            previous_first = first
            previous_second = second

    reconstruction_mismatch_count = 0
    assigned_query_count = 0
    forced_single_candidate_query_count = 0
    multi_candidate_query_count = 0

    query_transition_counts: Counter[str] = Counter()
    candidate_transition_opportunities: Counter[str] = Counter()
    candidate_transition_selections: Counter[str] = Counter()
    same_state_transition_opportunities: Counter[str] = Counter()
    same_state_transition_selections: Counter[str] = Counter()

    transition_match_opportunities = 0
    transition_match_selections = 0
    transition_comparable_opportunities = 0
    transition_comparable_selections = 0
    same_state_transition_match_opportunities = 0
    same_state_transition_match_selections = 0
    same_state_transition_comparable_opportunities = 0
    same_state_transition_comparable_selections = 0

    same_state_candidate_opportunities = 0
    same_state_winner_selections = 0
    nearest_same_state_opportunities = 0
    nearest_same_state_selections = 0
    non_nearest_same_state_opportunities = 0
    non_nearest_same_state_selections = 0
    same_state_winner_second_distance_ranks: list[int] = []

    selected_second_position_distances: list[float] = []
    unselected_second_position_distances: list[float] = []
    selected_second_step_mismatches: list[float] = []
    unselected_second_step_mismatches: list[float] = []

    same_state_winner_by_query_transition: Counter[str] = Counter()
    assigned_by_query_transition: Counter[str] = Counter()

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
        if len(candidates) == 1:
            forced_single_candidate_query_count += 1
            continue

        multi_candidate_query_count += 1
        query_meta = event_meta[(int(row), int(slot))]
        query_class = str(query_meta["transition_class"])
        query_transition_counts[query_class] += 1
        assigned_by_query_transition[query_class] += 1

        same_state_candidates = [
            candidate
            for candidate in candidates
            if np.isclose(
                float(candidate[5][first_port]),
                float(query[first_port]),
                rtol=0.0,
                atol=_COORDINATE_ATOL,
            )
        ]
        winner_same_state = winner in same_state_candidates
        same_state_winner_selections += int(winner_same_state)
        same_state_candidate_opportunities += len(same_state_candidates)
        same_state_winner_by_query_transition[query_class] += int(winner_same_state)

        nearest_same_state_id: int | None = None
        if same_state_candidates:
            ordered_same_state = sorted(
                same_state_candidates,
                key=lambda item: (
                    abs(float(item[5][second_port] - query[second_port])),
                    -item[1],
                    -item[2],
                ),
            )
            nearest_same_state_id = int(ordered_same_state[0][2])
            nearest_same_state_opportunities += 1
            non_nearest_same_state_opportunities += max(
                0, len(ordered_same_state) - 1
            )
            nearest_same_state_selections += int(winner[2] == nearest_same_state_id)
            non_nearest_same_state_selections += int(
                winner_same_state and winner[2] != nearest_same_state_id
            )
            if winner_same_state:
                same_state_winner_second_distance_ranks.append(
                    next(
                        index
                        for index, candidate in enumerate(ordered_same_state, start=1)
                        if candidate[2] == winner[2]
                    )
                )

        for candidate in candidates:
            selected = candidate[2] == winner[2]
            candidate_meta = event_meta[(int(row), int(candidate[4]))]
            candidate_class = str(candidate_meta["transition_class"])
            same_state = candidate in same_state_candidates

            candidate_transition_opportunities[candidate_class] += 1
            candidate_transition_selections[candidate_class] += int(selected)
            if same_state:
                same_state_transition_opportunities[candidate_class] += 1
                same_state_transition_selections[candidate_class] += int(selected)

            if query_class != "boundary" and candidate_class != "boundary":
                transition_comparable_opportunities += 1
                transition_match_opportunities += int(candidate_class == query_class)
                if selected:
                    transition_comparable_selections += 1
                    transition_match_selections += int(candidate_class == query_class)
                if same_state:
                    same_state_transition_comparable_opportunities += 1
                    same_state_transition_match_opportunities += int(
                        candidate_class == query_class
                    )
                    if selected:
                        same_state_transition_comparable_selections += 1
                        same_state_transition_match_selections += int(
                            candidate_class == query_class
                        )

            position_distance = abs(
                float(candidate_meta["second_coordinate"])
                - float(query_meta["second_coordinate"])
            )
            (selected_second_position_distances if selected else unselected_second_position_distances).append(
                position_distance
            )
            query_step = query_meta["second_coordinate_step"]
            candidate_step = candidate_meta["second_coordinate_step"]
            if query_step is not None and candidate_step is not None:
                step_mismatch = abs(float(query_step) - float(candidate_step))
                (selected_second_step_mismatches if selected else unselected_second_step_mismatches).append(
                    step_mismatch
                )

    transition_match_candidate_fraction = _safe_ratio(
        transition_match_opportunities, transition_comparable_opportunities
    )
    transition_match_winner_fraction = _safe_ratio(
        transition_match_selections, transition_comparable_selections
    )
    same_state_transition_match_candidate_fraction = _safe_ratio(
        same_state_transition_match_opportunities,
        same_state_transition_comparable_opportunities,
    )
    same_state_transition_match_winner_fraction = _safe_ratio(
        same_state_transition_match_selections,
        same_state_transition_comparable_selections,
    )
    nearest_rate = _safe_ratio(
        nearest_same_state_selections, nearest_same_state_opportunities
    )
    non_nearest_rate = _safe_ratio(
        non_nearest_same_state_selections, non_nearest_same_state_opportunities
    )
    selected_step_median = float(
        np.median(selected_second_step_mismatches)
        if selected_second_step_mismatches
        else 0.0
    )
    unselected_step_median = float(
        np.median(unselected_second_step_mismatches)
        if unselected_second_step_mismatches
        else 0.0
    )

    return {
        "requested_query_count": int(np.count_nonzero(requested)),
        "assigned_query_count": assigned_query_count,
        "forced_single_candidate_query_count": forced_single_candidate_query_count,
        "multi_candidate_query_count": multi_candidate_query_count,
        "reconstructed_score_selection_mismatch_count": reconstruction_mismatch_count,
        "visible_ports": {
            "first_readout_port": int(first_port),
            "second_readout_port": int(second_port),
            "constant_port": int(constant_port),
        },
        "transition_class_opportunity": {
            "query_transition_class_counts": {
                name: int(query_transition_counts[name])
                for name in _TRANSITION_CLASSES
            },
            "candidate_transition_class_rates": _class_rates(
                candidate_transition_opportunities, candidate_transition_selections
            ),
            "same_current_state_candidate_transition_class_rates": _class_rates(
                same_state_transition_opportunities, same_state_transition_selections
            ),
            "transition_comparable_candidate_opportunity_count": transition_comparable_opportunities,
            "transition_comparable_winner_count": transition_comparable_selections,
            "exact_transition_match_candidate_fraction": transition_match_candidate_fraction,
            "exact_transition_match_winner_fraction": transition_match_winner_fraction,
            "exact_transition_match_enrichment_over_opportunity": _safe_ratio(
                transition_match_winner_fraction,
                transition_match_candidate_fraction,
            ),
            "same_state_transition_comparable_candidate_opportunity_count": same_state_transition_comparable_opportunities,
            "same_state_transition_comparable_winner_count": same_state_transition_comparable_selections,
            "same_state_exact_transition_match_candidate_fraction": same_state_transition_match_candidate_fraction,
            "same_state_exact_transition_match_winner_fraction": same_state_transition_match_winner_fraction,
            "same_state_exact_transition_match_enrichment_over_opportunity": _safe_ratio(
                same_state_transition_match_winner_fraction,
                same_state_transition_match_candidate_fraction,
            ),
            "same_state_winner_fraction_by_query_transition_class": {
                name: _safe_ratio(
                    same_state_winner_by_query_transition[name],
                    assigned_by_query_transition[name],
                )
                for name in _TRANSITION_CLASSES
            },
        },
        "opportunity_conditioned_basin": {
            "same_state_candidate_opportunity_count": same_state_candidate_opportunities,
            "same_state_winner_selection_count": same_state_winner_selections,
            "same_state_winner_fraction_per_multi_candidate_query": _safe_ratio(
                same_state_winner_selections, multi_candidate_query_count
            ),
            "nearest_same_state_opportunity_count": nearest_same_state_opportunities,
            "nearest_same_state_selection_count": nearest_same_state_selections,
            "nearest_same_state_selection_rate_given_opportunity": nearest_rate,
            "non_nearest_same_state_opportunity_count": non_nearest_same_state_opportunities,
            "non_nearest_same_state_selection_count": non_nearest_same_state_selections,
            "non_nearest_same_state_selection_rate_given_opportunity": non_nearest_rate,
            "nearest_vs_non_nearest_same_state_selection_rate_ratio": (
                None
                if non_nearest_rate == 0.0
                else _safe_ratio(nearest_rate, non_nearest_rate)
            ),
            "nearest_vs_non_nearest_same_state_selection_rate_ratio_is_unbounded": bool(
                nearest_rate > 0.0 and non_nearest_rate == 0.0
            ),
            "same_state_winner_second_distance_rank": _finite_stats(
                same_state_winner_second_distance_ranks
            ),
        },
        "subject_anchor_drift": {
            "selected_second_coordinate_position_distance": _finite_stats(
                selected_second_position_distances
            ),
            "unselected_second_coordinate_position_distance": _finite_stats(
                unselected_second_position_distances
            ),
            "selected_second_coordinate_step_mismatch": _finite_stats(
                selected_second_step_mismatches
            ),
            "unselected_second_coordinate_step_mismatch": _finite_stats(
                unselected_second_step_mismatches
            ),
            "selected_to_unselected_step_mismatch_median_ratio": _safe_ratio(
                selected_step_median, unselected_step_median
            ),
        },
    }


def assess_stage3c29_transition_occupancy(
    rank2_study: dict[str, Any],
    rank2_component: dict[str, Any],
    rank2_diagnostics: dict[str, Any],
    stage3c28_assessment: dict[str, Any],
) -> dict[str, Any]:
    """Audit transition replay and opportunity-conditioned basin occupancy."""
    if stage3c28_assessment.get("schema") != STAGE3C28_RECURRENT_BASIN_SCHEMA:
        raise ValueError("Stage-3C-29 requires a Stage-3C-28 assessment")
    _validate_assessment_checksum(stage3c28_assessment, label="Stage-3C-28 assessment")
    selected_port = int(
        rank2_study.get("parameters", {}).get(
            "bootstrap_second_readout_input_port", -1
        )
    )
    if selected_port in {0, 11} or selected_port < 0:
        raise ValueError("Stage-3C-29 rank-two readout port is invalid")
    _validate_study(rank2_study, second_port=selected_port)
    _validate_report_set(
        rank2_study, rank2_component, rank2_diagnostics, label="rank2"
    )
    if stage3c28_assessment.get("rank2_study_sha256") != rank2_study.get(
        "study_sha256"
    ):
        raise ValueError("Stage-3C-29 Stage-3C-28 lineage mismatch")
    if not bool(
        stage3c28_assessment["diagnostic_interpretation"].get(
            "winner_reuse_is_consistent_with_within_subject_recurrent_geometric_basins"
        )
    ):
        raise ValueError("Stage-3C-29 requires the complete Stage-3C-28 screen")

    source_records = _source_records(rank2_study)
    per_source: list[dict[str, Any]] = []
    all_reconstructed = True
    transition_match_enrichments: list[float] = []
    same_state_transition_match_enrichments: list[float] = []
    nearest_dominates_all = True
    selected_drift_closer_all = True
    dominant_transition_classes: list[str] = []

    for seed in sorted(source_records):
        source = source_records[seed]
        row = _source_transition_occupancy(source["read_only_control_checkpoint"])
        row["seed"] = int(seed)
        all_reconstructed &= row["reconstructed_score_selection_mismatch_count"] == 0
        transition = row["transition_class_opportunity"]
        transition_match_enrichments.append(
            float(transition["exact_transition_match_enrichment_over_opportunity"])
        )
        same_state_transition_match_enrichments.append(
            float(
                transition[
                    "same_state_exact_transition_match_enrichment_over_opportunity"
                ]
            )
        )
        rates = transition["candidate_transition_class_rates"]
        dominant_transition_classes.append(
            max(
                _TRANSITION_CLASSES,
                key=lambda name: (
                    float(rates[name]["selection_rate_given_opportunity"]),
                    name,
                ),
            )
        )
        basin = row["opportunity_conditioned_basin"]
        nearest_dominates_all &= (
            float(basin["nearest_same_state_selection_rate_given_opportunity"])
            > float(basin["non_nearest_same_state_selection_rate_given_opportunity"])
        )
        drift = row["subject_anchor_drift"]
        selected_drift_closer_all &= (
            float(drift["selected_second_coordinate_step_mismatch"]["median"])
            < float(drift["unselected_second_coordinate_step_mismatch"]["median"])
        )
        per_source.append(row)

    if not all_reconstructed:
        raise ValueError("Stage-3C-29 reconstructed selector mismatch")

    transition_above_one = sum(value > 1.0 for value in transition_match_enrichments)
    transition_below_one = sum(value < 1.0 for value in transition_match_enrichments)
    same_state_above_one = sum(
        value > 1.0 for value in same_state_transition_match_enrichments
    )
    same_state_below_one = sum(
        value < 1.0 for value in same_state_transition_match_enrichments
    )
    dominant_counts = Counter(dominant_transition_classes)
    stable_transition_replay = bool(
        transition_match_enrichments
        and all(value > 1.0 for value in transition_match_enrichments)
        and all(value > 1.0 for value in same_state_transition_match_enrichments)
    )

    payload = {
        "schema": STAGE3C29_TRANSITION_OCCUPANCY_SCHEMA,
        "producer_version": __version__,
        "rank2_study_sha256": rank2_study["study_sha256"],
        "stage3c28_assessment_sha256": stage3c28_assessment["assessment_sha256"],
        "analysis_only_factor": (
            "separate exact first-state transition-class replay from candidate "
            "opportunity and subject-anchored second-coordinate locality in the "
            "frozen Stage-3C-23 rank-two read-only control traces"
        ),
        "runtime_experimental_factor_changed": False,
        "isolation_contract": {
            "independent_source_count": len(per_source),
            "seeds": sorted(source_records),
            "stage3c28_checksum_and_lineage_verified": True,
            "stored_winner_ids_and_scores_exactly_reconstructed": True,
            "forced_single_candidate_queries_excluded_from_conditioned_screens": True,
            "same_rank2_readout_similarity_threshold_latest_top1_target_carrier_delta_exposure_and_rollback": True,
            "highest_independent_replicate": "independent-pre-bootstrap-source-checkpoint",
            "queries_events_subjects_or_windows_are_independent_replicates": False,
        },
        "per_source": per_source,
        "source_balanced_summary": {
            "exact_transition_match_enrichment_over_opportunity": _aggregate_source_metric(
                per_source,
                (
                    "transition_class_opportunity",
                    "exact_transition_match_enrichment_over_opportunity",
                ),
            ),
            "same_state_exact_transition_match_enrichment_over_opportunity": _aggregate_source_metric(
                per_source,
                (
                    "transition_class_opportunity",
                    "same_state_exact_transition_match_enrichment_over_opportunity",
                ),
            ),
            "same_state_winner_fraction_per_multi_candidate_query": _aggregate_source_metric(
                per_source,
                (
                    "opportunity_conditioned_basin",
                    "same_state_winner_fraction_per_multi_candidate_query",
                ),
            ),
            "nearest_same_state_selection_rate_given_opportunity": _aggregate_source_metric(
                per_source,
                (
                    "opportunity_conditioned_basin",
                    "nearest_same_state_selection_rate_given_opportunity",
                ),
            ),
            "non_nearest_same_state_selection_rate_given_opportunity": _aggregate_source_metric(
                per_source,
                (
                    "opportunity_conditioned_basin",
                    "non_nearest_same_state_selection_rate_given_opportunity",
                ),
            ),
            "selected_to_unselected_step_mismatch_median_ratio": _aggregate_source_metric(
                per_source,
                (
                    "subject_anchor_drift",
                    "selected_to_unselected_step_mismatch_median_ratio",
                ),
            ),
        },
        "cross_source_findings": {
            "transition_match_enrichment_source_count_above_one": transition_above_one,
            "transition_match_enrichment_source_count_below_one": transition_below_one,
            "same_state_transition_match_enrichment_source_count_above_one": same_state_above_one,
            "same_state_transition_match_enrichment_source_count_below_one": same_state_below_one,
            "candidate_transition_class_with_highest_opportunity_conditioned_selection_rate_counts": {
                name: int(dominant_counts[name]) for name in _TRANSITION_CLASSES
            },
            "exact_transition_class_replay_is_consistently_enriched_in_all_sources": stable_transition_replay,
            "nearest_second_coordinate_within_state_has_higher_opportunity_conditioned_selection_rate_in_all_sources": nearest_dominates_all,
            "selected_candidate_has_lower_second_coordinate_step_mismatch_median_in_all_sources": selected_drift_closer_all,
        },
        "diagnostic_interpretation": {
            "basin_occupancy_is_explained_by_stable_exact_transition_class_replay": stable_transition_replay,
            "transition_class_has_fixed_value_or_causal_credit_semantics": False,
            "subject_anchored_second_coordinate_locality_remains_predictive_after_opportunity_conditioning": bool(
                nearest_dominates_all and selected_drift_closer_all
            ),
            "opportunity_conditioned_locality_proves_causal_credit_quality": False,
            "next_authorized_step": (
                "Freeze the Stage-3C-23 through Stage-3C-29 run chain and summarize "
                "the complete addressing diagnosis before considering another mechanism. "
                "Do not add age penalties, randomized allocation, learned weights or "
                "permanent retention from this engineering locality result."
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
            "Assess Stage-3C-29 transition-class replay and opportunity-conditioned "
            "subject-anchored basin occupancy."
        )
    )
    parser.add_argument("--rank2-study-report", required=True)
    parser.add_argument("--rank2-component", required=True)
    parser.add_argument("--rank2-diagnostics", required=True)
    parser.add_argument("--stage3c28-assessment", required=True)
    parser.add_argument("--output", required=True)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    result = assess_stage3c29_transition_occupancy(
        _load_json(args.rank2_study_report),
        _load_json(args.rank2_component),
        _load_json(args.rank2_diagnostics),
        _load_json(args.stage3c28_assessment),
    )
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result["diagnostic_interpretation"], ensure_ascii=False))


if __name__ == "__main__":
    main()


__all__ = [
    "STAGE3C29_TRANSITION_OCCUPANCY_SCHEMA",
    "assess_stage3c29_transition_occupancy",
]
