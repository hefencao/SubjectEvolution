"""Stage 3C-24 rank-two selection coverage and score-margin audit.

The audit reuses the frozen Stage 3C-23 rank-one and rank-two control traces.
It reconstructs the complete bounded candidate opportunity, selected event
identity coverage, reuse concentration and query-level score margins.  It is
strictly read-only and changes no runtime, checkpoint, addressing or update
contract.
"""
from __future__ import annotations

import argparse
from functools import cmp_to_key
import json
from pathlib import Path
from typing import Any

import numpy as np

from .. import __version__
from ..checkpointing import read_checkpoint_bundle
from ..subject_vm.association import _candidate_order
from ..subject_vm.modulation import modulation_control_ports
from .subject_vm_stage3c13_exposure_adequacy import (
    _load_json,
    _source_records,
    _validate_report_set,
)
from .subject_vm_stage3c22_historical_selection import (
    _aggregate_source_metric,
    _canonical_sha256,
    _selection_snapshot,
    _stats,
)
from .subject_vm_stage3c23_dual_readout_rank import (
    STAGE3C23_DUAL_READOUT_RANK_SCHEMA,
    _factor_signature,
    _normalized_profile,
    _validate_study,
)

STAGE3C24_RANK2_SELECTION_SCHEMA = (
    "se-subject-vm-stage3c24-rank2-selection-assessment-v1"
)


def _visible_token(
    token: np.ndarray, *, request_port: int, excluded_ports: tuple[int, ...]
) -> np.ndarray:
    result = np.asarray(token, dtype=np.float64).copy()
    for port in {int(request_port), *(int(value) for value in excluded_ports)}:
        result[port] = 0.0
    return result


def _score_margin_snapshot(checkpoint: str | Path) -> dict[str, Any]:
    _, state = read_checkpoint_bundle(checkpoint)
    subject_vm_cfg = state["config"].subject_vm
    association_cfg = subject_vm_cfg.association
    trace = state["simulation"]["subject_vm"]["trace_storage"]["arrays"]

    valid = np.asarray(trace["event_valid"], dtype=bool)
    event_ids = np.asarray(trace["event_id"], dtype=np.uint64)
    event_ticks = np.asarray(trace["event_tick"], dtype=np.int64)
    tokens = np.asarray(trace["thought_token"], dtype=np.float64)
    requested = np.asarray(trace["association_requested"], dtype=bool) & valid
    assigned = np.asarray(trace["association_assigned"], dtype=bool) & valid
    stored_event_ids = np.asarray(trace["associated_event_id"], dtype=np.uint64)
    stored_similarities = np.asarray(trace["association_similarity"], dtype=np.float64)
    excluded_ports = modulation_control_ports(subject_vm_cfg.modulation)

    selected_scores: list[float] = []
    threshold_margins: list[float] = []
    best_second_margins: list[float] = []
    eligible_score_spreads: list[float] = []
    best_tie_counts: list[int] = []
    assigned_with_multiple = 0
    exact_best_tie_count = 0
    reconstruction_mismatch_count = 0

    for row, slot in zip(*np.nonzero(requested), strict=True):
        current_tick = int(event_ticks[row, slot])
        query = _visible_token(
            tokens[row, slot],
            request_port=int(association_cfg.request_token_port),
            excluded_ports=excluded_ports,
        )
        query_norm = float(np.linalg.norm(query))
        scored: list[tuple[float, int, int, int]] = []
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
                scored.append(
                    (
                        score,
                        historical_tick,
                        int(event_ids[row, historical_slot]),
                        int(historical_slot),
                    )
                )
        scored.sort(key=_candidate_order("latest"))
        eligible = [
            item
            for item in scored
            if float(item[0]) >= float(association_cfg.similarity_threshold)
        ]
        stored_assigned = bool(assigned[row, slot])
        if bool(eligible) != stored_assigned:
            reconstruction_mismatch_count += 1
            continue
        if not eligible:
            continue

        best_score = float(eligible[0][0])
        best_event_id = int(eligible[0][2])
        selected_scores.append(best_score)
        threshold_margins.append(
            best_score - float(association_cfg.similarity_threshold)
        )
        tie_count = sum(
            bool(np.isclose(float(item[0]), best_score, rtol=0.0, atol=1e-12))
            for item in eligible
        )
        best_tie_counts.append(int(tie_count))
        if tie_count > 1:
            exact_best_tie_count += 1
        if len(eligible) > 1:
            assigned_with_multiple += 1
            second_score = float(eligible[1][0])
            best_second_margins.append(best_score - second_score)
            eligible_score_spreads.append(best_score - float(eligible[-1][0]))

        if (
            int(stored_event_ids[row, slot]) != best_event_id
            or not np.isclose(
                float(stored_similarities[row, slot]),
                best_score,
                rtol=0.0,
                atol=1e-6,
            )
        ):
            reconstruction_mismatch_count += 1

    assigned_count = int(np.count_nonzero(assigned))
    return {
        "assigned_query_count": assigned_count,
        "assigned_queries_with_multiple_eligible_candidates": int(
            assigned_with_multiple
        ),
        "reconstructed_score_selection_mismatch_count": int(
            reconstruction_mismatch_count
        ),
        "selected_similarity": _stats(selected_scores),
        "selected_threshold_margin": _stats(threshold_margins),
        "best_second_score_margin": _stats(best_second_margins),
        "eligible_score_spread": _stats(eligible_score_spreads),
        "best_tie_count": _stats(best_tie_counts),
        "exact_best_tie_query_count": int(exact_best_tie_count),
        "exact_best_tie_fraction_of_assigned": float(
            exact_best_tie_count / assigned_count if assigned_count else 0.0
        ),
        "all_selected_scores_above_threshold": bool(
            all(value >= 0.0 for value in threshold_margins)
        ),
    }


def assess_stage3c24_rank2_selection(
    rank1_study: dict[str, Any],
    rank1_component: dict[str, Any],
    rank1_diagnostics: dict[str, Any],
    rank2_study: dict[str, Any],
    rank2_component: dict[str, Any],
    rank2_diagnostics: dict[str, Any],
    stage3c23_assessment: dict[str, Any],
) -> dict[str, Any]:
    """Audit rank-two candidate coverage and margins without runtime changes."""
    if stage3c23_assessment.get("schema") != STAGE3C23_DUAL_READOUT_RANK_SCHEMA:
        raise ValueError("Stage-3C-24 requires a Stage-3C-23 assessment")
    selected_port = int(
        stage3c23_assessment["candidate_screen"]["selected_candidate"]["port"]
    )
    _validate_study(rank1_study, second_port=11)
    _validate_study(rank2_study, second_port=selected_port)
    _validate_report_set(
        rank1_study, rank1_component, rank1_diagnostics, label="rank1"
    )
    _validate_report_set(
        rank2_study, rank2_component, rank2_diagnostics, label="rank2"
    )
    if _factor_signature(rank1_study) != _factor_signature(rank2_study):
        raise ValueError("Stage-3C-24 comparison changed another study factor")
    if _normalized_profile(rank1_study["bootstrap_profile"]) != _normalized_profile(
        rank2_study["bootstrap_profile"]
    ):
        raise ValueError("Stage-3C-24 profiles differ beyond second readout input")
    if stage3c23_assessment.get("rank1_study_sha256") != rank1_study.get(
        "study_sha256"
    ) or stage3c23_assessment.get("rank2_study_sha256") != rank2_study.get(
        "study_sha256"
    ):
        raise ValueError("Stage-3C-24 Stage-3C-23 lineage mismatch")
    required_isolation = (
        "pre_bootstrap_state_hashes_equal",
        "pre_bootstrap_config_hashes_equal",
        "bootstrap_subject_selection_equal",
        "read_only_control_objective_behavior_equal",
        "tokens_equal_except_authorized_port30_input_change",
    )
    if not all(
        bool(stage3c23_assessment["isolation_contract"].get(key))
        for key in required_isolation
    ):
        raise ValueError("Stage-3C-24 requires the complete Stage-3C-23 isolation contract")

    rank1_sources = _source_records(rank1_study)
    rank2_sources = _source_records(rank2_study)
    if set(rank1_sources) != set(rank2_sources):
        raise ValueError("Stage-3C-24 arms use different source panels")

    rank1_rows: list[dict[str, Any]] = []
    rank2_rows: list[dict[str, Any]] = []
    comparisons: list[dict[str, Any]] = []
    opportunity_equal_all = True
    rank2_subset_all = True
    rank2_adds_new = False
    rank2_lower_coverage_all = True
    rank2_higher_gini_all = True
    rank2_lower_effective_all = True
    rank2_eliminates_ties_all = True

    for seed in sorted(rank1_sources):
        rank1 = _selection_snapshot(
            rank1_sources[seed]["read_only_control_checkpoint"]
        )
        rank2 = _selection_snapshot(
            rank2_sources[seed]["read_only_control_checkpoint"]
        )
        rank1["score_margin"] = _score_margin_snapshot(
            rank1_sources[seed]["read_only_control_checkpoint"]
        )
        rank2["score_margin"] = _score_margin_snapshot(
            rank2_sources[seed]["read_only_control_checkpoint"]
        )
        rank1["seed"] = int(seed)
        rank2["seed"] = int(seed)

        for row in (rank1, rank2):
            if row["reconstructed_selection_mismatch_count"] != 0 or row[
                "score_margin"
            ]["reconstructed_score_selection_mismatch_count"] != 0:
                raise ValueError("Stage-3C-24 reconstructed selector mismatch")

        opportunity_equal = bool(
            rank1["candidate_opportunity"] == rank2["candidate_opportunity"]
            and rank1["eligible_event_ids"] == rank2["eligible_event_ids"]
        )
        opportunity_equal_all &= opportunity_equal
        rank1_selected = set(rank1["selected_event_ids"])
        rank2_selected = set(rank2["selected_event_ids"])
        rank2_subset_all &= bool(rank2_selected < rank1_selected)
        rank2_adds_new |= bool(rank2_selected - rank1_selected)

        coverage1 = float(
            rank1["selected_identity_coverage"][
                "selected_unique_fraction_of_eligible_union"
            ]
        )
        coverage2 = float(
            rank2["selected_identity_coverage"][
                "selected_unique_fraction_of_eligible_union"
            ]
        )
        gini1 = float(
            rank1["reuse_concentration"]["eligible_union_selection_gini"]
        )
        gini2 = float(
            rank2["reuse_concentration"]["eligible_union_selection_gini"]
        )
        effective1 = float(
            rank1["reuse_concentration"]
            ["inverse_simpson_effective_fraction_of_eligible_union"]
        )
        effective2 = float(
            rank2["reuse_concentration"]
            ["inverse_simpson_effective_fraction_of_eligible_union"]
        )
        rank2_lower_coverage_all &= coverage2 < coverage1
        rank2_higher_gini_all &= gini2 > gini1
        rank2_lower_effective_all &= effective2 < effective1
        rank2_eliminates_ties_all &= bool(
            rank2["score_margin"]["exact_best_tie_query_count"] == 0
        )

        rank1_by_query = rank1.pop("_selection_by_current_event")
        rank2_by_query = rank2.pop("_selection_by_current_event")
        if set(rank1_by_query) != set(rank2_by_query):
            raise ValueError("Stage-3C-24 assigned current-event keys changed")
        same_count = sum(
            rank1_by_query[key] == rank2_by_query[key] for key in rank1_by_query
        )
        assignments = len(rank1_by_query)
        comparisons.append(
            {
                "seed": int(seed),
                "candidate_opportunity_equal": opportunity_equal,
                "rank1_selected_unique_event_count": len(rank1_selected),
                "rank2_selected_unique_event_count": len(rank2_selected),
                "rank2_new_selected_event_count": len(rank2_selected - rank1_selected),
                "rank1_selected_events_not_selected_by_rank2": len(
                    rank1_selected - rank2_selected
                ),
                "selected_event_set_jaccard": float(
                    len(rank1_selected & rank2_selected)
                    / len(rank1_selected | rank2_selected)
                ),
                "exact_same_query_selection_fraction": float(
                    same_count / assignments if assignments else 0.0
                ),
                "change_in_unique_event_coverage_fraction": coverage2 - coverage1,
                "change_in_selection_gini": gini2 - gini1,
                "change_in_inverse_simpson_effective_fraction": effective2 - effective1,
                "rank1_exact_best_tie_fraction": rank1["score_margin"]
                ["exact_best_tie_fraction_of_assigned"],
                "rank2_exact_best_tie_fraction": rank2["score_margin"]
                ["exact_best_tie_fraction_of_assigned"],
                "rank2_minimum_best_second_margin": rank2["score_margin"]
                ["best_second_score_margin"]["minimum"],
            }
        )
        rank1_rows.append(rank1)
        rank2_rows.append(rank2)

    if not opportunity_equal_all:
        raise ValueError("Stage-3C-24 candidate opportunity changed across arms")

    payload = {
        "schema": STAGE3C24_RANK2_SELECTION_SCHEMA,
        "producer_version": __version__,
        "rank1_study_sha256": rank1_study["study_sha256"],
        "rank2_study_sha256": rank2_study["study_sha256"],
        "stage3c23_assessment_sha256": stage3c23_assessment["assessment_sha256"],
        "analysis_only_factor": (
            "reconstruct complete rank-one/rank-two candidate opportunity, selected "
            "event identity coverage, reuse concentration and score margins"
        ),
        "runtime_experimental_factor_changed": False,
        "isolation_contract": {
            "independent_source_count": len(comparisons),
            "seeds": sorted(rank1_sources),
            "stage3c23_isolation_contract_reused": True,
            "same_candidate_opportunity_in_all_sources": opportunity_equal_all,
            "stored_selections_and_scores_exactly_reconstructed": True,
            "same_similarity_threshold_delay_bounds_candidate_limit_and_tie_break": True,
            "same_target_carrier_delta_exposure_rollback_and_evaluation_contract": True,
            "highest_independent_replicate": "independent-pre-bootstrap-source-checkpoint",
            "events_subjects_or_windows_are_independent_replicates": False,
        },
        "rank1_duplicate_coordinate": {
            "per_source": rank1_rows,
            "selected_unique_fraction_of_eligible_per_source": _aggregate_source_metric(
                rank1_rows,
                (
                    "selected_identity_coverage",
                    "selected_unique_fraction_of_eligible_union",
                ),
            ),
            "selection_gini_per_source": _aggregate_source_metric(
                rank1_rows,
                ("reuse_concentration", "eligible_union_selection_gini"),
            ),
            "inverse_simpson_effective_fraction_per_source": _aggregate_source_metric(
                rank1_rows,
                (
                    "reuse_concentration",
                    "inverse_simpson_effective_fraction_of_eligible_union",
                ),
            ),
            "exact_best_tie_fraction_per_source": _aggregate_source_metric(
                rank1_rows,
                ("score_margin", "exact_best_tie_fraction_of_assigned"),
            ),
            "best_second_margin_median_per_source": _aggregate_source_metric(
                rank1_rows,
                ("score_margin", "best_second_score_margin", "median"),
            ),
        },
        "rank2_selected_coordinate": {
            "per_source": rank2_rows,
            "selected_unique_fraction_of_eligible_per_source": _aggregate_source_metric(
                rank2_rows,
                (
                    "selected_identity_coverage",
                    "selected_unique_fraction_of_eligible_union",
                ),
            ),
            "selection_gini_per_source": _aggregate_source_metric(
                rank2_rows,
                ("reuse_concentration", "eligible_union_selection_gini"),
            ),
            "inverse_simpson_effective_fraction_per_source": _aggregate_source_metric(
                rank2_rows,
                (
                    "reuse_concentration",
                    "inverse_simpson_effective_fraction_of_eligible_union",
                ),
            ),
            "exact_best_tie_fraction_per_source": _aggregate_source_metric(
                rank2_rows,
                ("score_margin", "exact_best_tie_fraction_of_assigned"),
            ),
            "best_second_margin_median_per_source": _aggregate_source_metric(
                rank2_rows,
                ("score_margin", "best_second_score_margin", "median"),
            ),
        },
        "comparison": {
            "per_source": comparisons,
            "candidate_opportunity_equal_in_all_sources": opportunity_equal_all,
            "rank2_selected_set_is_strict_subset_in_all_sources": rank2_subset_all,
            "rank2_adds_any_new_selected_event_identity": rank2_adds_new,
            "rank2_reduces_unique_identity_coverage_in_all_sources": rank2_lower_coverage_all,
            "rank2_increases_selection_gini_in_all_sources": rank2_higher_gini_all,
            "rank2_reduces_inverse_simpson_effective_coverage_in_all_sources": rank2_lower_effective_all,
            "rank2_eliminates_exact_best_ties_in_all_sources": rank2_eliminates_ties_all,
            "exact_same_query_selection_fraction": _stats(
                row["exact_same_query_selection_fraction"] for row in comparisons
            ),
            "selected_event_set_jaccard": _stats(
                row["selected_event_set_jaccard"] for row in comparisons
            ),
        },
        "diagnostic_interpretation": {
            "rank_two_changes_score_ordering_not_candidate_eligibility": True,
            "rank_two_eliminates_exact_best_score_ties": rank2_eliminates_ties_all,
            "rank_two_increases_selected_event_identity_diversity": False,
            "rank_two_selects_new_identity_outside_rank_one_coverage": rank2_adds_new,
            "rank_two_increases_reuse_concentration": bool(
                rank2_higher_gini_all and rank2_lower_effective_all
            ),
            "higher_geometric_rank_has_fixed_value_semantics": False,
            "larger_score_margin_proves_better_causal_credit": False,
            "selection_coverage_or_concentration_proves_learning": False,
            "next_authorized_step": (
                "Hold the Stage-3C-23 rank-two readout, normalized-dot similarity, "
                "threshold, latest/top-1, target/carrier, update scale, exposure and "
                "rollback fixed. Audit whether per-query deterministic winner reuse is "
                "driven by near-zero margins or by repeated geometry before any "
                "addressing change; do not increase top-k or add learned weights."
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
        description="Assess Stage-3C-24 rank-two selection coverage and score margins."
    )
    for prefix in ("rank1", "rank2"):
        parser.add_argument(f"--{prefix}-study-report", required=True)
        parser.add_argument(f"--{prefix}-component", required=True)
        parser.add_argument(f"--{prefix}-diagnostics", required=True)
    parser.add_argument("--stage3c23-assessment", required=True)
    parser.add_argument("--output", required=True)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    result = assess_stage3c24_rank2_selection(
        _load_json(args.rank1_study_report),
        _load_json(args.rank1_component),
        _load_json(args.rank1_diagnostics),
        _load_json(args.rank2_study_report),
        _load_json(args.rank2_component),
        _load_json(args.rank2_diagnostics),
        _load_json(args.stage3c23_assessment),
    )
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result["diagnostic_interpretation"], ensure_ascii=False))


if __name__ == "__main__":
    main()


__all__ = [
    "STAGE3C24_RANK2_SELECTION_SCHEMA",
    "assess_stage3c24_rank2_selection",
]
