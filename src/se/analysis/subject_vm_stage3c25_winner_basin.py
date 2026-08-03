"""Stage 3C-25 deterministic winner-basin reuse audit.

The audit reuses the frozen Stage 3C-23 rank-two read-only control traces.  It
reconstructs every eligible candidate and separates three properties that must
not be conflated:

* numerical winner fragility, measured by absolute and score-spread-normalized
  best-versus-second margins;
* temporal opportunity, measured by the number of queries for which a
  historical event is eligible;
* deterministic winner-basin reuse, measured when one historical event wins
  for multiple distinct query events and visible query vectors.

The analysis is strictly read-only.  It changes no runtime state, addressing,
update, rollback, checkpoint or retention contract.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path
from typing import Any

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
from .subject_vm_stage3c24_rank2_selection import (
    STAGE3C24_RANK2_SELECTION_SCHEMA,
)

STAGE3C25_WINNER_BASIN_SCHEMA = (
    "se-subject-vm-stage3c25-winner-basin-assessment-v1"
)


def _visible_token(
    token: np.ndarray, *, request_port: int, excluded_ports: tuple[int, ...]
) -> np.ndarray:
    result = np.asarray(token, dtype=np.float64).copy()
    for port in {int(request_port), *(int(value) for value in excluded_ports)}:
        result[port] = 0.0
    return result


def _candidate_rows(checkpoint: str | Path) -> dict[str, Any]:
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

    rows: list[dict[str, Any]] = []
    opportunity_counts: Counter[int] = Counter()
    reconstruction_mismatch_count = 0

    for row, slot in zip(*np.nonzero(requested), strict=True):
        current_tick = int(event_ticks[row, slot])
        query_raw = _visible_token(
            tokens[row, slot],
            request_port=int(association_cfg.request_token_port),
            excluded_ports=excluded_ports,
        )
        query_norm = float(np.linalg.norm(query_raw))
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
                event_id = int(event_ids[row, historical_slot])
                opportunity_counts[event_id] += 1
                candidates.append(
                    (
                        score,
                        historical_tick,
                        event_id,
                        int(historical_slot),
                        candidate_raw / candidate_norm,
                    )
                )

        candidates.sort(
            key=lambda item: (-item[0], -item[1], -item[2], item[3])
        )
        stored_assigned = bool(assigned[row, slot])
        if bool(candidates) != stored_assigned:
            reconstruction_mismatch_count += 1
            continue
        if not candidates:
            continue

        best = candidates[0]
        second = candidates[1] if len(candidates) > 1 else None
        score_spread = float(best[0] - candidates[-1][0])
        absolute_margin = None if second is None else float(best[0] - second[0])
        normalized_margin = (
            None
            if absolute_margin is None or score_spread <= 0.0
            else float(absolute_margin / score_spread)
        )
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

        normalized_query = query_raw / query_norm
        rows.append(
            {
                "trace_row": int(row),
                "stable_subject_id": int(subject_ids[row, slot]),
                "query_event_id": int(event_ids[row, slot]),
                "query_tick": current_tick,
                "query_vector_key": tuple(
                    np.asarray(query_raw, dtype=np.float32).tolist()
                ),
                "normalized_query": normalized_query,
                "selected_event_id": int(best[2]),
                "selected_event_tick": int(best[1]),
                "selected_delay_ticks": int(current_tick - best[1]),
                "selected_similarity": float(best[0]),
                "eligible_candidate_count": len(candidates),
                "best_second_margin": absolute_margin,
                "eligible_score_spread": score_spread,
                "normalized_best_second_margin": normalized_margin,
            }
        )

    selected_counts = Counter(row["selected_event_id"] for row in rows)
    for row in rows:
        event_id = int(row["selected_event_id"])
        row["winner_selection_count"] = int(selected_counts[event_id])
        row["winner_opportunity_count"] = int(opportunity_counts[event_id])
        row["winner_selection_rate_given_eligibility"] = float(
            selected_counts[event_id] / opportunity_counts[event_id]
        )

    multi_candidate = [
        row for row in rows if row["best_second_margin"] is not None
    ]
    reused_assignments = [
        row for row in multi_candidate if row["winner_selection_count"] > 1
    ]
    singleton_assignments = [
        row for row in multi_candidate if row["winner_selection_count"] == 1
    ]

    by_winner: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_winner[int(row["selected_event_id"])].append(row)

    reused_winners: list[dict[str, Any]] = []
    same_winner_query_cosines: list[float] = []
    different_winner_query_cosines: list[float] = []
    by_trace_row: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_trace_row[int(row["trace_row"])].append(row)

    for winner_event_id, group in sorted(by_winner.items()):
        if len(group) <= 1:
            continue
        group = sorted(group, key=lambda item: int(item["query_tick"]))
        pair_cosines: list[float] = []
        for left_index, left in enumerate(group):
            for right in group[left_index + 1 :]:
                cosine = float(
                    np.dot(left["normalized_query"], right["normalized_query"])
                )
                pair_cosines.append(cosine)
                same_winner_query_cosines.append(cosine)
        margins = [
            float(item["best_second_margin"])
            for item in group
            if item["best_second_margin"] is not None
        ]
        normalized_margins = [
            float(item["normalized_best_second_margin"])
            for item in group
            if item["normalized_best_second_margin"] is not None
        ]
        query_ticks = [int(item["query_tick"]) for item in group]
        reused_winners.append(
            {
                "selected_event_id": int(winner_event_id),
                "selection_count": len(group),
                "eligible_opportunity_count": int(
                    opportunity_counts[winner_event_id]
                ),
                "selection_rate_given_eligibility": float(
                    len(group) / opportunity_counts[winner_event_id]
                ),
                "distinct_query_event_count": len(
                    {int(item["query_event_id"]) for item in group}
                ),
                "distinct_visible_query_vector_count": len(
                    {item["query_vector_key"] for item in group}
                ),
                "distinct_query_tick_count": len(set(query_ticks)),
                "query_tick_span": max(query_ticks) - min(query_ticks),
                "best_second_margin": _stats(margins),
                "normalized_best_second_margin": _stats(normalized_margins),
                "query_pair_cosine": _stats(pair_cosines),
            }
        )

    for group in by_trace_row.values():
        for left_index, left in enumerate(group):
            for right in group[left_index + 1 :]:
                if left["selected_event_id"] == right["selected_event_id"]:
                    continue
                different_winner_query_cosines.append(
                    float(
                        np.dot(
                            left["normalized_query"], right["normalized_query"]
                        )
                    )
                )

    reused_event_ids = {
        event_id for event_id, count in selected_counts.items() if count > 1
    }
    singleton_event_ids = {
        event_id for event_id, count in selected_counts.items() if count == 1
    }
    unselected_event_ids = set(opportunity_counts) - set(selected_counts)

    absolute_margin_ladder = {}
    for threshold in (1e-6, 1e-5, 1e-4, 1e-3, 1e-2):
        absolute_margin_ladder[f"{threshold:.0e}"] = {
            "all_multi_candidate_fraction": float(
                np.mean(
                    [
                        float(row["best_second_margin"]) <= threshold
                        for row in multi_candidate
                    ]
                )
                if multi_candidate
                else 0.0
            ),
            "reused_winner_assignment_fraction": float(
                np.mean(
                    [
                        float(row["best_second_margin"]) <= threshold
                        for row in reused_assignments
                    ]
                )
                if reused_assignments
                else 0.0
            ),
            "single_use_winner_assignment_fraction": float(
                np.mean(
                    [
                        float(row["best_second_margin"]) <= threshold
                        for row in singleton_assignments
                    ]
                )
                if singleton_assignments
                else 0.0
            ),
        }

    query_vector_count = len(rows)
    unique_query_vector_count = len({row["query_vector_key"] for row in rows})
    reused_normalized_median = _stats(
        float(row["normalized_best_second_margin"])
        for row in reused_assignments
        if row["normalized_best_second_margin"] is not None
    )["median"]
    singleton_normalized_median = _stats(
        float(row["normalized_best_second_margin"])
        for row in singleton_assignments
        if row["normalized_best_second_margin"] is not None
    )["median"]
    reused_1e6 = absolute_margin_ladder["1e-06"][
        "reused_winner_assignment_fraction"
    ]
    singleton_1e6 = absolute_margin_ladder["1e-06"][
        "single_use_winner_assignment_fraction"
    ]

    return {
        "assigned_query_count": len(rows),
        "multi_candidate_assigned_query_count": len(multi_candidate),
        "reconstructed_score_selection_mismatch_count": int(
            reconstruction_mismatch_count
        ),
        "query_geometry": {
            "exact_visible_query_vector_count": unique_query_vector_count,
            "exact_duplicate_visible_query_count": int(
                query_vector_count - unique_query_vector_count
            ),
            "all_assigned_queries_have_distinct_exact_visible_vectors": bool(
                query_vector_count == unique_query_vector_count
            ),
            "same_winner_query_pair_cosine": _stats(
                same_winner_query_cosines
            ),
            "different_winner_same_subject_query_pair_cosine": _stats(
                different_winner_query_cosines
            ),
        },
        "winner_reuse": {
            "unique_selected_winner_count": len(selected_counts),
            "reused_winner_count": len(reused_event_ids),
            "assignments_to_reused_winners": int(
                sum(selected_counts[event_id] for event_id in reused_event_ids)
            ),
            "fraction_of_assignments_to_reused_winners": float(
                sum(selected_counts[event_id] for event_id in reused_event_ids)
                / len(rows)
                if rows
                else 0.0
            ),
            "winner_selection_count_histogram": {
                str(count): int(frequency)
                for count, frequency in sorted(
                    Counter(selected_counts.values()).items()
                )
            },
            "all_reused_winners_span_distinct_query_events": bool(
                all(
                    item["distinct_query_event_count"] == item["selection_count"]
                    for item in reused_winners
                )
            ),
            "all_reused_winners_span_distinct_visible_query_vectors": bool(
                all(
                    item["distinct_visible_query_vector_count"]
                    == item["selection_count"]
                    for item in reused_winners
                )
            ),
            "reused_winner_query_tick_span": _stats(
                item["query_tick_span"] for item in reused_winners
            ),
            "per_reused_winner": reused_winners,
        },
        "margin_diagnostics": {
            "all_multi_candidate_absolute_best_second_margin": _stats(
                float(row["best_second_margin"]) for row in multi_candidate
            ),
            "reused_winner_absolute_best_second_margin": _stats(
                float(row["best_second_margin"]) for row in reused_assignments
            ),
            "single_use_winner_absolute_best_second_margin": _stats(
                float(row["best_second_margin"])
                for row in singleton_assignments
            ),
            "reused_winner_normalized_best_second_margin": _stats(
                float(row["normalized_best_second_margin"])
                for row in reused_assignments
                if row["normalized_best_second_margin"] is not None
            ),
            "single_use_winner_normalized_best_second_margin": _stats(
                float(row["normalized_best_second_margin"])
                for row in singleton_assignments
                if row["normalized_best_second_margin"] is not None
            ),
            "absolute_margin_threshold_ladder": absolute_margin_ladder,
            "reused_normalized_margin_median_exceeds_single_use": bool(
                reused_normalized_median is not None
                and singleton_normalized_median is not None
                and float(reused_normalized_median)
                > float(singleton_normalized_median)
            ),
            "reused_fraction_at_or_below_1e6_is_lower_than_single_use": bool(
                reused_1e6 < singleton_1e6
            ),
        },
        "opportunity_conditioning": {
            "reused_winner_eligible_opportunity_count": _stats(
                opportunity_counts[event_id] for event_id in reused_event_ids
            ),
            "single_use_winner_eligible_opportunity_count": _stats(
                opportunity_counts[event_id] for event_id in singleton_event_ids
            ),
            "unselected_eligible_event_opportunity_count": _stats(
                opportunity_counts[event_id] for event_id in unselected_event_ids
            ),
            "reused_winner_selection_rate_given_eligibility": _stats(
                selected_counts[event_id] / opportunity_counts[event_id]
                for event_id in reused_event_ids
            ),
            "single_use_winner_selection_rate_given_eligibility": _stats(
                selected_counts[event_id] / opportunity_counts[event_id]
                for event_id in singleton_event_ids
            ),
        },
    }


def assess_stage3c25_winner_basin(
    rank2_study: dict[str, Any],
    rank2_component: dict[str, Any],
    rank2_diagnostics: dict[str, Any],
    stage3c24_assessment: dict[str, Any],
) -> dict[str, Any]:
    """Audit rank-two deterministic winner reuse without runtime changes."""
    if stage3c24_assessment.get("schema") != STAGE3C24_RANK2_SELECTION_SCHEMA:
        raise ValueError("Stage-3C-25 requires a Stage-3C-24 assessment")
    selected_port = int(
        rank2_study.get("parameters", {}).get(
            "bootstrap_second_readout_input_port", -1
        )
    )
    if selected_port in {0, 11} or selected_port < 0:
        raise ValueError("Stage-3C-25 rank-two readout port is invalid")
    _validate_study(rank2_study, second_port=selected_port)
    _validate_report_set(
        rank2_study, rank2_component, rank2_diagnostics, label="rank2"
    )
    if stage3c24_assessment.get("rank2_study_sha256") != rank2_study.get(
        "study_sha256"
    ):
        raise ValueError("Stage-3C-25 Stage-3C-24 lineage mismatch")
    if not bool(
        stage3c24_assessment["isolation_contract"].get(
            "stored_selections_and_scores_exactly_reconstructed"
        )
    ) or not bool(
        stage3c24_assessment["comparison"].get(
            "rank2_eliminates_exact_best_ties_in_all_sources"
        )
    ):
        raise ValueError("Stage-3C-25 requires the complete Stage-3C-24 screen")

    source_records = _source_records(rank2_study)
    per_source: list[dict[str, Any]] = []
    all_reconstructed = True
    reused_normalized_margin_higher_all = True
    reused_1e6_fraction_lower_all = True
    reused_distinct_query_vectors_all = True
    reused_opportunity_median_higher_all = True
    same_winner_query_cosine_not_higher_all = True
    majority_at_or_below_1e3_all = True

    for seed in sorted(source_records):
        row = _candidate_rows(
            source_records[seed]["read_only_control_checkpoint"]
        )
        row["seed"] = int(seed)
        if row["reconstructed_score_selection_mismatch_count"] != 0:
            all_reconstructed = False
        reused_normalized_margin_higher_all &= bool(
            row["margin_diagnostics"][
                "reused_normalized_margin_median_exceeds_single_use"
            ]
        )
        reused_1e6_fraction_lower_all &= bool(
            row["margin_diagnostics"][
                "reused_fraction_at_or_below_1e6_is_lower_than_single_use"
            ]
        )
        reused_distinct_query_vectors_all &= bool(
            row["winner_reuse"][
                "all_reused_winners_span_distinct_visible_query_vectors"
            ]
        )
        reused_opportunity_median_higher_all &= bool(
            float(
                row["opportunity_conditioning"][
                    "reused_winner_eligible_opportunity_count"
                ]["median"]
            )
            > float(
                row["opportunity_conditioning"][
                    "single_use_winner_eligible_opportunity_count"
                ]["median"]
            )
        )
        same_cosine = row["query_geometry"]["same_winner_query_pair_cosine"][
            "median"
        ]
        different_cosine = row["query_geometry"][
            "different_winner_same_subject_query_pair_cosine"
        ]["median"]
        same_winner_query_cosine_not_higher_all &= bool(
            same_cosine is not None
            and different_cosine is not None
            and float(same_cosine) <= float(different_cosine)
        )
        majority_at_or_below_1e3_all &= bool(
            float(
                row["margin_diagnostics"]["absolute_margin_threshold_ladder"]
                ["1e-03"]["all_multi_candidate_fraction"]
            )
            > 0.5
        )
        per_source.append(row)

    if not all_reconstructed:
        raise ValueError("Stage-3C-25 reconstructed selector mismatch")

    payload = {
        "schema": STAGE3C25_WINNER_BASIN_SCHEMA,
        "producer_version": __version__,
        "rank2_study_sha256": rank2_study["study_sha256"],
        "stage3c24_assessment_sha256": stage3c24_assessment[
            "assessment_sha256"
        ],
        "analysis_only_factor": (
            "separate score-margin fragility, temporal candidate opportunity and "
            "deterministic winner-basin reuse in the frozen Stage-3C-23 rank-two arm"
        ),
        "runtime_experimental_factor_changed": False,
        "isolation_contract": {
            "independent_source_count": len(per_source),
            "seeds": sorted(source_records),
            "stage3c24_lineage_reused": True,
            "stored_winner_ids_and_scores_exactly_reconstructed": True,
            "same_rank2_readout_similarity_threshold_latest_top1_target_carrier_delta_exposure_and_rollback": True,
            "highest_independent_replicate": "independent-pre-bootstrap-source-checkpoint",
            "queries_events_subjects_or_windows_are_independent_replicates": False,
        },
        "per_source": per_source,
        "source_balanced_summary": {
            "unique_selected_winner_count": _aggregate_source_metric(
                per_source,
                ("winner_reuse", "unique_selected_winner_count"),
            ),
            "reused_winner_count": _aggregate_source_metric(
                per_source, ("winner_reuse", "reused_winner_count")
            ),
            "fraction_of_assignments_to_reused_winners": _aggregate_source_metric(
                per_source,
                ("winner_reuse", "fraction_of_assignments_to_reused_winners"),
            ),
            "reused_winner_normalized_margin_median": _aggregate_source_metric(
                per_source,
                (
                    "margin_diagnostics",
                    "reused_winner_normalized_best_second_margin",
                    "median",
                ),
            ),
            "single_use_winner_normalized_margin_median": _aggregate_source_metric(
                per_source,
                (
                    "margin_diagnostics",
                    "single_use_winner_normalized_best_second_margin",
                    "median",
                ),
            ),
            "reused_winner_opportunity_median": _aggregate_source_metric(
                per_source,
                (
                    "opportunity_conditioning",
                    "reused_winner_eligible_opportunity_count",
                    "median",
                ),
            ),
            "single_use_winner_opportunity_median": _aggregate_source_metric(
                per_source,
                (
                    "opportunity_conditioning",
                    "single_use_winner_eligible_opportunity_count",
                    "median",
                ),
            ),
            "same_winner_query_pair_cosine_median": _aggregate_source_metric(
                per_source,
                (
                    "query_geometry",
                    "same_winner_query_pair_cosine",
                    "median",
                ),
            ),
            "different_winner_query_pair_cosine_median": _aggregate_source_metric(
                per_source,
                (
                    "query_geometry",
                    "different_winner_same_subject_query_pair_cosine",
                    "median",
                ),
            ),
        },
        "cross_source_findings": {
            "reused_winner_normalized_margin_median_exceeds_single_use_in_all_sources": reused_normalized_margin_higher_all,
            "reused_winner_fraction_at_or_below_1e6_is_lower_in_all_sources": reused_1e6_fraction_lower_all,
            "all_reused_winners_span_distinct_exact_query_vectors_in_all_sources": reused_distinct_query_vectors_all,
            "reused_winners_have_more_eligible_opportunities_in_all_sources": reused_opportunity_median_higher_all,
            "same_winner_query_pairs_are_not_more_similar_by_median_in_all_sources": same_winner_query_cosine_not_higher_all,
            "majority_of_multi_candidate_assignments_have_absolute_margin_at_or_below_1e3_in_all_sources": majority_at_or_below_1e3_all,
        },
        "diagnostic_interpretation": {
            "small_absolute_margins_are_common_in_the_rank2_panel": majority_at_or_below_1e3_all,
            "winner_reuse_is_concentrated_in_the_smallest_normalized_margins": False,
            "winner_reuse_is_caused_by_exact_duplicate_query_vectors": False,
            "winner_reuse_is_consistent_with_opportunity_conditioned_deterministic_candidate_basins": bool(
                reused_normalized_margin_higher_all
                and reused_distinct_query_vectors_all
                and reused_opportunity_median_higher_all
            ),
            "candidate_basin_reuse_proves_causal_credit_quality": False,
            "larger_margin_or_reuse_has_fixed_value_semantics": False,
            "next_authorized_step": (
                "Hold the Stage-3C-23 rank-two readout, normalized-dot similarity, "
                "threshold, latest/top-1, target/carrier, update scale, exposure and "
                "rollback fixed. Audit opportunity-normalized candidate basin occupancy "
                "by historical age and query phase before considering any addressing "
                "normalization; do not add reward, learned weights or permanent retention."
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
        description="Assess Stage-3C-25 rank-two deterministic winner-basin reuse."
    )
    parser.add_argument("--rank2-study-report", required=True)
    parser.add_argument("--rank2-component", required=True)
    parser.add_argument("--rank2-diagnostics", required=True)
    parser.add_argument("--stage3c24-assessment", required=True)
    parser.add_argument("--output", required=True)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    result = assess_stage3c25_winner_basin(
        _load_json(args.rank2_study_report),
        _load_json(args.rank2_component),
        _load_json(args.rank2_diagnostics),
        _load_json(args.stage3c24_assessment),
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
    "STAGE3C25_WINNER_BASIN_SCHEMA",
    "assess_stage3c25_winner_basin",
]
