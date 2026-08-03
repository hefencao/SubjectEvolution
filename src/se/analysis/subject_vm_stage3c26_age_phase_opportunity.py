"""Stage 3C-26 historical-age and query-phase opportunity audit.

This analysis reuses the frozen Stage-3C-23 rank-two read-only control traces.
It reconstructs all eligible candidates and separates:

* source-boundary queries that have exactly one eligible historical event;
* age-conditioned winner occupancy after those forced queries are removed;
* historical-event birth phase, raw opportunity and selection rate conditional
  on eligibility; and
* query-phase winner-age distributions.

The analysis is read-only and changes no runtime, checkpoint, addressing,
update, rollback or retention contract.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
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
from .subject_vm_stage3c25_winner_basin import (
    STAGE3C25_WINNER_BASIN_SCHEMA,
    _visible_token,
)

STAGE3C26_AGE_PHASE_OPPORTUNITY_SCHEMA = (
    "se-subject-vm-stage3c26-age-phase-opportunity-assessment-v1"
)


def _histogram(values: Iterable[int]) -> dict[str, int]:
    return {str(key): int(value) for key, value in sorted(Counter(values).items())}


def _phase_rows(checkpoint: str | Path, *, source_tick: int) -> dict[str, Any]:
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
    stored_similarities = np.asarray(trace["association_similarity"], dtype=np.float64)
    excluded_ports = modulation_control_ports(subject_vm_cfg.modulation)

    event_metadata: dict[int, dict[str, int]] = {}
    for row, slot in zip(*np.nonzero(valid), strict=True):
        event_metadata[int(event_ids[row, slot])] = {
            "event_tick": int(event_ticks[row, slot]),
            "historical_phase": int(event_ticks[row, slot]) - int(source_tick),
            "stable_subject_id": int(subject_ids[row, slot]),
        }

    opportunities: list[dict[str, Any]] = []
    selections: list[dict[str, Any]] = []
    request_candidate_counts: list[int] = []
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
        candidates: list[tuple[float, int, int, int, dict[str, Any]]] = []
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
                historical_event_id = int(event_ids[row, historical_slot])
                candidate = {
                    "stable_subject_id": int(subject_ids[row, slot]),
                    "query_event_id": int(event_ids[row, slot]),
                    "query_tick": current_tick,
                    "query_phase": current_tick - int(source_tick),
                    "historical_event_id": historical_event_id,
                    "historical_event_tick": historical_tick,
                    "historical_phase": historical_tick - int(source_tick),
                    "historical_age_ticks": int(delay),
                    "similarity": score,
                }
                opportunities.append(candidate)
                candidates.append(
                    (
                        score,
                        historical_tick,
                        historical_event_id,
                        int(historical_slot),
                        candidate,
                    )
                )

        candidates.sort(key=lambda item: (-item[0], -item[1], -item[2], item[3]))
        request_candidate_counts.append(len(candidates))
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
        selected = dict(best[4])
        selected["eligible_candidate_count"] = len(candidates)
        selected["forced_single_candidate"] = len(candidates) == 1
        selections.append(selected)

    opportunity_counts = Counter(
        int(row["historical_event_id"]) for row in opportunities
    )
    selection_counts = Counter(int(row["historical_event_id"]) for row in selections)
    selected_event_ids = set(selection_counts)
    reused_event_ids = {event_id for event_id, count in selection_counts.items() if count > 1}
    single_event_ids = {event_id for event_id, count in selection_counts.items() if count == 1}
    unselected_event_ids = set(opportunity_counts) - selected_event_ids

    by_age_opportunity = Counter(int(row["historical_age_ticks"]) for row in opportunities)
    by_age_selection = Counter(int(row["historical_age_ticks"]) for row in selections)
    # The candidate count is constant for every candidate of one query. Build a
    # direct lookup instead of preserving a runtime field in the checkpoint.
    query_candidate_count = Counter(int(row["query_event_id"]) for row in opportunities)
    multi_opportunities = [
        row
        for row in opportunities
        if query_candidate_count[int(row["query_event_id"])] > 1
    ]
    multi_selections = [row for row in selections if not row["forced_single_candidate"]]
    multi_age_opportunity = Counter(
        int(row["historical_age_ticks"]) for row in multi_opportunities
    )
    multi_age_selection = Counter(
        int(row["historical_age_ticks"]) for row in multi_selections
    )

    phase_records: dict[int, dict[str, Any]] = {}
    all_phases = sorted(
        {int(item["historical_phase"]) for item in opportunities}
    )
    for phase in all_phases:
        event_ids_at_phase = {
            event_id
            for event_id, metadata in event_metadata.items()
            if int(metadata["historical_phase"]) == phase
            and event_id in opportunity_counts
        }
        phase_opportunities = sum(opportunity_counts[event_id] for event_id in event_ids_at_phase)
        phase_selections = sum(selection_counts[event_id] for event_id in event_ids_at_phase)
        selected_id_count = sum(event_id in selected_event_ids for event_id in event_ids_at_phase)
        phase_records[phase] = {
            "eligible_event_count": len(event_ids_at_phase),
            "selected_event_count": int(selected_id_count),
            "opportunity_count": int(phase_opportunities),
            "selection_count": int(phase_selections),
            "selection_rate_given_eligibility": float(
                phase_selections / phase_opportunities if phase_opportunities else 0.0
            ),
        }

    query_phase_records: dict[int, dict[str, Any]] = {}
    for phase in sorted({int(row["query_phase"]) for row in selections}):
        phase_selections = [row for row in selections if int(row["query_phase"]) == phase]
        phase_opportunities = [
            row for row in opportunities if int(row["query_phase"]) == phase
        ]
        age_hist = Counter(int(row["historical_age_ticks"]) for row in phase_selections)
        query_phase_records[phase] = {
            "assigned_query_count": len(phase_selections),
            "candidate_reference_count": len(phase_opportunities),
            "eligible_candidate_count_per_query": int(
                len(phase_opportunities) / len(phase_selections)
                if phase_selections
                else 0
            ),
            "selected_age_histogram": {
                str(key): int(value) for key, value in sorted(age_hist.items())
            },
            "age_one_winner_fraction": float(
                age_hist.get(1, 0) / len(phase_selections) if phase_selections else 0.0
            ),
        }

    def _event_group(event_id_set: set[int]) -> dict[str, Any]:
        return {
            "event_count": len(event_id_set),
            "historical_phase": _stats(
                event_metadata[event_id]["historical_phase"]
                for event_id in event_id_set
            ),
            "eligible_opportunity_count": _stats(
                opportunity_counts[event_id] for event_id in event_id_set
            ),
            "selection_rate_given_eligibility": _stats(
                selection_counts[event_id] / opportunity_counts[event_id]
                for event_id in event_id_set
            ),
        }

    multi_age_rates = {
        age: float(multi_age_selection[age] / multi_age_opportunity[age])
        for age in sorted(multi_age_opportunity)
    }
    age_one_rate = multi_age_rates.get(1, 0.0)
    older_rates = [rate for age, rate in multi_age_rates.items() if age > 1]
    forced = [row for row in selections if row["forced_single_candidate"]]
    forced_historical_ids = {int(row["historical_event_id"]) for row in forced}
    phase_zero_ids = {
        event_id
        for event_id, metadata in event_metadata.items()
        if int(metadata["historical_phase"]) == 0 and event_id in opportunity_counts
    }

    return {
        "assigned_query_count": len(selections),
        "requested_query_count": int(np.count_nonzero(requested)),
        "no_candidate_request_count": int(no_candidate_request_count),
        "forced_single_candidate_query_count": len(forced),
        "multi_candidate_assigned_query_count": len(multi_selections),
        "forced_assignment_fraction": float(len(forced) / len(selections) if selections else 0.0),
        "candidate_count_histogram": _histogram(request_candidate_counts),
        "reconstructed_score_selection_mismatch_count": int(reconstruction_mismatch_count),
        "source_boundary": {
            "forced_query_phase_histogram": _histogram(
                int(row["query_phase"]) for row in forced
            ),
            "forced_historical_phase_histogram": _histogram(
                int(row["historical_phase"]) for row in forced
            ),
            "forced_historical_age_histogram": _histogram(
                int(row["historical_age_ticks"]) for row in forced
            ),
            "all_phase_zero_events_receive_a_forced_selection": bool(
                phase_zero_ids == forced_historical_ids
            ),
        },
        "historical_age": {
            "all_query_opportunity_count": {
                str(age): int(by_age_opportunity[age]) for age in sorted(by_age_opportunity)
            },
            "all_query_selection_count": {
                str(age): int(by_age_selection[age]) for age in sorted(by_age_selection)
            },
            "multi_candidate_opportunity_count": {
                str(age): int(multi_age_opportunity[age]) for age in sorted(multi_age_opportunity)
            },
            "multi_candidate_selection_count": {
                str(age): int(multi_age_selection[age]) for age in sorted(multi_age_selection)
            },
            "multi_candidate_selection_rate_given_opportunity": {
                str(age): float(rate) for age, rate in sorted(multi_age_rates.items())
            },
            "age_one_rate_is_at_least_every_older_age": bool(
                not older_rates or age_one_rate >= max(older_rates)
            ),
            "age_one_rate_strictly_exceeds_every_older_age": bool(
                not older_rates or age_one_rate > max(older_rates)
            ),
        },
        "historical_birth_phase": {
            str(phase): record for phase, record in sorted(phase_records.items())
        },
        "query_phase": {
            str(phase): record for phase, record in sorted(query_phase_records.items())
        },
        "winner_groups": {
            "reused": _event_group(reused_event_ids),
            "single_use": _event_group(single_event_ids),
            "unselected": _event_group(unselected_event_ids),
            "reused_phase_median_precedes_single_use": bool(
                float(_event_group(reused_event_ids)["historical_phase"]["median"])
                < float(_event_group(single_event_ids)["historical_phase"]["median"])
            ),
            "single_use_phase_median_not_after_unselected": bool(
                float(_event_group(single_event_ids)["historical_phase"]["median"])
                <= float(_event_group(unselected_event_ids)["historical_phase"]["median"])
            ),
            "reused_opportunity_normalized_rate_median_at_least_single_use": bool(
                float(
                    _event_group(reused_event_ids)["selection_rate_given_eligibility"]["median"]
                )
                >= float(
                    _event_group(single_event_ids)["selection_rate_given_eligibility"]["median"]
                )
            ),
            "reused_opportunity_normalized_rate_median_strictly_exceeds_single_use": bool(
                float(
                    _event_group(reused_event_ids)["selection_rate_given_eligibility"]["median"]
                )
                > float(
                    _event_group(single_event_ids)["selection_rate_given_eligibility"]["median"]
                )
            ),
        },
    }


def assess_stage3c26_age_phase_opportunity(
    rank2_study: dict[str, Any],
    rank2_component: dict[str, Any],
    rank2_diagnostics: dict[str, Any],
    stage3c25_assessment: dict[str, Any],
) -> dict[str, Any]:
    """Audit age, phase and opportunity-normalized winner occupancy."""
    if stage3c25_assessment.get("schema") != STAGE3C25_WINNER_BASIN_SCHEMA:
        raise ValueError("Stage-3C-26 requires a Stage-3C-25 assessment")
    selected_port = int(
        rank2_study.get("parameters", {}).get("bootstrap_second_readout_input_port", -1)
    )
    if selected_port in {0, 11} or selected_port < 0:
        raise ValueError("Stage-3C-26 rank-two readout port is invalid")
    _validate_study(rank2_study, second_port=selected_port)
    _validate_report_set(rank2_study, rank2_component, rank2_diagnostics, label="rank2")
    if stage3c25_assessment.get("rank2_study_sha256") != rank2_study.get("study_sha256"):
        raise ValueError("Stage-3C-26 Stage-3C-25 lineage mismatch")
    if not bool(
        stage3c25_assessment["isolation_contract"].get(
            "stored_winner_ids_and_scores_exactly_reconstructed"
        )
    ):
        raise ValueError("Stage-3C-26 requires the complete Stage-3C-25 screen")

    source_records = _source_records(rank2_study)
    per_source: list[dict[str, Any]] = []
    all_reconstructed = True
    forced_boundary_all = True
    age_one_at_least_all = True
    age_one_strict_count = 0
    phase_order_all = True
    normalized_rate_at_least_all = True
    normalized_rate_strict_count = 0

    for seed in sorted(source_records):
        source = source_records[seed]
        row = _phase_rows(
            source["read_only_control_checkpoint"],
            source_tick=int(source["source_tick"]),
        )
        row["seed"] = int(seed)
        all_reconstructed &= row["reconstructed_score_selection_mismatch_count"] == 0
        forced_boundary_all &= bool(
            row["source_boundary"]["all_phase_zero_events_receive_a_forced_selection"]
            and row["forced_single_candidate_query_count"] == 16
        )
        age_one_at_least_all &= bool(
            row["historical_age"]["age_one_rate_is_at_least_every_older_age"]
        )
        age_one_strict_count += int(
            row["historical_age"]["age_one_rate_strictly_exceeds_every_older_age"]
        )
        phase_order_all &= bool(
            row["winner_groups"]["reused_phase_median_precedes_single_use"]
            and row["winner_groups"]["single_use_phase_median_not_after_unselected"]
        )
        normalized_rate_at_least_all &= bool(
            row["winner_groups"][
                "reused_opportunity_normalized_rate_median_at_least_single_use"
            ]
        )
        normalized_rate_strict_count += int(
            row["winner_groups"][
                "reused_opportunity_normalized_rate_median_strictly_exceeds_single_use"
            ]
        )
        per_source.append(row)

    if not all_reconstructed:
        raise ValueError("Stage-3C-26 reconstructed selector mismatch")

    payload = {
        "schema": STAGE3C26_AGE_PHASE_OPPORTUNITY_SCHEMA,
        "producer_version": __version__,
        "rank2_study_sha256": rank2_study["study_sha256"],
        "stage3c25_assessment_sha256": stage3c25_assessment["assessment_sha256"],
        "analysis_only_factor": (
            "separate source-boundary forced assignments, historical age, query phase, "
            "raw opportunity and opportunity-normalized winner occupancy in the frozen "
            "Stage-3C-23 rank-two arm"
        ),
        "runtime_experimental_factor_changed": False,
        "isolation_contract": {
            "independent_source_count": len(per_source),
            "seeds": sorted(source_records),
            "stage3c25_lineage_reused": True,
            "stored_winner_ids_and_scores_exactly_reconstructed": True,
            "same_rank2_readout_similarity_threshold_latest_top1_target_carrier_delta_exposure_and_rollback": True,
            "highest_independent_replicate": "independent-pre-bootstrap-source-checkpoint",
            "queries_events_subjects_or_windows_are_independent_replicates": False,
        },
        "per_source": per_source,
        "source_balanced_summary": {
            "forced_assignment_fraction": _aggregate_source_metric(
                per_source, ("forced_assignment_fraction",)
            ),
            "age_one_multi_candidate_selection_rate": _aggregate_source_metric(
                per_source,
                (
                    "historical_age",
                    "multi_candidate_selection_rate_given_opportunity",
                    "1",
                ),
            ),
            "age_two_multi_candidate_selection_rate": _aggregate_source_metric(
                per_source,
                (
                    "historical_age",
                    "multi_candidate_selection_rate_given_opportunity",
                    "2",
                ),
            ),
            "reused_winner_historical_phase_median": _aggregate_source_metric(
                per_source,
                ("winner_groups", "reused", "historical_phase", "median"),
            ),
            "single_use_winner_historical_phase_median": _aggregate_source_metric(
                per_source,
                ("winner_groups", "single_use", "historical_phase", "median"),
            ),
            "unselected_event_historical_phase_median": _aggregate_source_metric(
                per_source,
                ("winner_groups", "unselected", "historical_phase", "median"),
            ),
            "reused_winner_selection_rate_given_eligibility_median": _aggregate_source_metric(
                per_source,
                (
                    "winner_groups",
                    "reused",
                    "selection_rate_given_eligibility",
                    "median",
                ),
            ),
            "single_use_winner_selection_rate_given_eligibility_median": _aggregate_source_metric(
                per_source,
                (
                    "winner_groups",
                    "single_use",
                    "selection_rate_given_eligibility",
                    "median",
                ),
            ),
        },
        "cross_source_findings": {
            "sixteen_source_boundary_assignments_are_forced_in_all_sources": forced_boundary_all,
            "age_one_has_the_highest_or_tied_multi_candidate_selection_rate_in_all_sources": age_one_at_least_all,
            "age_one_strictly_has_the_highest_multi_candidate_selection_rate_source_count": age_one_strict_count,
            "reused_winners_are_earlier_than_single_use_and_unselected_events_in_all_sources": phase_order_all,
            "reused_winner_opportunity_normalized_rate_is_at_least_single_use_in_all_sources": normalized_rate_at_least_all,
            "reused_winner_opportunity_normalized_rate_strictly_exceeds_single_use_source_count": normalized_rate_strict_count,
        },
        "diagnostic_interpretation": {
            "source_boundary_forcing_contributes_to_phase_zero_coverage_and_reuse": forced_boundary_all,
            "raw_opportunity_count_alone_fully_explains_winner_reuse": False,
            "recency_preference_persists_after_forced_queries_are_removed": age_one_at_least_all,
            "historical_age_or_query_phase_has_fixed_value_semantics": False,
            "age_conditioned_selection_proves_causal_credit_quality": False,
            "next_authorized_step": (
                "Hold the Stage-3C-23 rank-two readout, normalized-dot similarity, threshold, "
                "latest/top-1, target/carrier, update scale, exposure and rollback fixed. "
                "Audit whether the age-one basin is explained by score geometry versus the "
                "latest tie-break and branch-boundary support before any opportunity or age "
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
        description="Assess Stage-3C-26 age, phase and opportunity-conditioned winner occupancy."
    )
    parser.add_argument("--rank2-study-report", required=True)
    parser.add_argument("--rank2-component", required=True)
    parser.add_argument("--rank2-diagnostics", required=True)
    parser.add_argument("--stage3c25-assessment", required=True)
    parser.add_argument("--output", required=True)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    result = assess_stage3c26_age_phase_opportunity(
        _load_json(args.rank2_study_report),
        _load_json(args.rank2_component),
        _load_json(args.rank2_diagnostics),
        _load_json(args.stage3c25_assessment),
    )
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result["diagnostic_interpretation"], ensure_ascii=False))


if __name__ == "__main__":
    main()


__all__ = [
    "STAGE3C26_AGE_PHASE_OPPORTUNITY_SCHEMA",
    "assess_stage3c26_age_phase_opportunity",
]
