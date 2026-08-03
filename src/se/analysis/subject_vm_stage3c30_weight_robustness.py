"""Stage 3C-30 read-only second-coordinate weight robustness audit.

The audit keeps the frozen Stage-3C-23 rank-two read-only control traces and
re-scores the *same authoritative eligible candidate set* after multiplying the
second visible coordinate by a predeclared bounded weight.  Weight zero is the
rank-collapse ablation; positive weights test whether the Stage-3C-29 basin is
fine-tuned to one exact coordinate scale or whether any non-zero contribution
stably resolves within-state ordering.

Candidate opportunity, delay bounds, baseline threshold admission, latest/top-1
tie-break, target family, carrier, rollback and retention contracts are fixed.
No runtime or checkpoint field is changed.
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
    _gini,
    _stats,
)
from .subject_vm_stage3c23_dual_readout_rank import _validate_study
from .subject_vm_stage3c25_winner_basin import _visible_token
from .subject_vm_stage3c29_transition_occupancy import (
    STAGE3C29_TRANSITION_OCCUPANCY_SCHEMA,
)

STAGE3C30_WEIGHT_ROBUSTNESS_SCHEMA = (
    "se-subject-vm-stage3c30-weight-robustness-assessment-v1"
)
SECOND_COORDINATE_WEIGHT_PANEL = (0.0, 0.1, 0.25, 0.5, 1.0, 2.0, 4.0, 10.0)
_BASELINE_WEIGHT = 1.0
_COORDINATE_ATOL = 1e-8


def _factor_key(value: float) -> str:
    return f"{float(value):g}"


def _safe_ratio(numerator: int | float, denominator: int | float) -> float:
    return float(numerator / denominator) if denominator else 0.0


def _finite_stats(values: Iterable[float]) -> dict[str, Any]:
    return _stats(float(value) for value in values if np.isfinite(value))


def _validate_assessment_checksum(payload: dict[str, Any], *, label: str) -> None:
    recorded = str(payload.get("assessment_sha256", ""))
    unsigned = dict(payload)
    unsigned.pop("assessment_sha256", None)
    if not recorded or recorded != _canonical_sha256(unsigned):
        raise ValueError(f"Stage-3C-30 {label} checksum mismatch")


def _rescore(
    query: np.ndarray,
    candidates: list[tuple[float, int, int, int, int, np.ndarray]],
    *,
    second_port: int,
    weight: float,
) -> list[tuple[float, int, int, int, int, np.ndarray]]:
    weighted_query = np.asarray(query, dtype=np.float64).copy()
    weighted_query[second_port] *= float(weight)
    query_norm = float(np.linalg.norm(weighted_query))
    rescored: list[tuple[float, int, int, int, int, np.ndarray]] = []
    for _, tick, event_id, delay, slot, candidate in candidates:
        weighted_candidate = np.asarray(candidate, dtype=np.float64).copy()
        weighted_candidate[second_port] *= float(weight)
        candidate_norm = float(np.linalg.norm(weighted_candidate))
        score = (
            -2.0
            if query_norm == 0.0 or candidate_norm == 0.0
            else float(
                np.clip(
                    np.dot(weighted_query, weighted_candidate)
                    / (query_norm * candidate_norm),
                    -1.0,
                    1.0,
                )
            )
        )
        rescored.append((score, tick, event_id, delay, slot, weighted_candidate))
    rescored.sort(key=lambda item: (-item[0], -item[1], -item[2]))
    return rescored


def _source_weight_robustness(checkpoint: str | Path) -> dict[str, Any]:
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
            "Stage-3C-30 requires the frozen three-coordinate association-visible token"
        )
    first_port, second_port, _constant_port = visible_ports

    requested_query_count = int(np.count_nonzero(requested))
    assigned_query_count = 0
    forced_single_candidate_query_count = 0
    multi_candidate_query_count = 0
    reconstruction_mismatch_count = 0
    total_baseline_candidate_evaluations = 0

    factor_state: dict[float, dict[str, Any]] = {
        factor: {
            "winner_agreement_count": 0,
            "same_state_winner_count": 0,
            "age_one_winner_count": 0,
            "nearest_same_state_winner_count": 0,
            "same_state_winner_count_for_nearest_screen": 0,
            "threshold_survival_count": 0,
            "candidate_evaluation_count": 0,
            "winner_margins": [],
            "selected_event_counts": Counter(),
        }
        for factor in SECOND_COORDINATE_WEIGHT_PANEL
    }

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
        total_baseline_candidate_evaluations += len(candidates)
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
        nearest_same_state_ids: set[int] = set()
        if same_state_candidates:
            nearest_distance = min(
                abs(float(candidate[5][second_port] - query[second_port]))
                for candidate in same_state_candidates
            )
            nearest_same_state_ids = {
                int(candidate[2])
                for candidate in same_state_candidates
                if np.isclose(
                    abs(float(candidate[5][second_port] - query[second_port])),
                    nearest_distance,
                    rtol=0.0,
                    atol=1e-12,
                )
            }

        for factor, current in factor_state.items():
            rescored = _rescore(
                query,
                candidates,
                second_port=second_port,
                weight=factor,
            )
            winner = rescored[0]
            current["winner_agreement_count"] += int(
                int(winner[2]) == int(baseline_winner[2])
            )
            current["same_state_winner_count"] += int(
                np.isclose(
                    winner[5][first_port],
                    query[first_port],
                    rtol=0.0,
                    atol=_COORDINATE_ATOL,
                )
            )
            current["age_one_winner_count"] += int(int(winner[3]) == 1)
            winner_is_same_state = bool(
                np.isclose(
                    winner[5][first_port],
                    query[first_port],
                    rtol=0.0,
                    atol=_COORDINATE_ATOL,
                )
            )
            if winner_is_same_state and nearest_same_state_ids:
                current["same_state_winner_count_for_nearest_screen"] += 1
                current["nearest_same_state_winner_count"] += int(
                    int(winner[2]) in nearest_same_state_ids
                )
            current["threshold_survival_count"] += sum(
                float(candidate[0])
                >= float(association_cfg.similarity_threshold)
                for candidate in rescored
            )
            current["candidate_evaluation_count"] += len(rescored)
            if len(rescored) > 1:
                current["winner_margins"].append(
                    float(rescored[0][0] - rescored[1][0])
                )
            current["selected_event_counts"][int(winner[2])] += 1

    factors: dict[str, dict[str, Any]] = {}
    for factor in SECOND_COORDINATE_WEIGHT_PANEL:
        current = factor_state[factor]
        selected_counts = current["selected_event_counts"]
        same_state_screen_count = int(
            current["same_state_winner_count_for_nearest_screen"]
        )
        factors[_factor_key(factor)] = {
            "second_coordinate_weight": float(factor),
            "rank_collapsed": bool(factor == 0.0),
            "baseline_weight": bool(factor == _BASELINE_WEIGHT),
            "candidate_evaluation_count": int(current["candidate_evaluation_count"]),
            "candidate_evaluation_count_matches_baseline_opportunity": bool(
                int(current["candidate_evaluation_count"])
                == total_baseline_candidate_evaluations
            ),
            "candidate_threshold_survival_fraction": _safe_ratio(
                int(current["threshold_survival_count"]),
                int(current["candidate_evaluation_count"]),
            ),
            "winner_agreement_with_baseline_fraction": _safe_ratio(
                int(current["winner_agreement_count"]), multi_candidate_query_count
            ),
            "changed_winner_count": int(
                multi_candidate_query_count - int(current["winner_agreement_count"])
            ),
            "same_state_winner_fraction": _safe_ratio(
                int(current["same_state_winner_count"]), multi_candidate_query_count
            ),
            "age_one_winner_fraction": _safe_ratio(
                int(current["age_one_winner_count"]), multi_candidate_query_count
            ),
            "nearest_second_coordinate_fraction_among_same_state_winners": _safe_ratio(
                int(current["nearest_same_state_winner_count"]),
                same_state_screen_count,
            ),
            "same_state_winner_count_for_nearest_screen": same_state_screen_count,
            "unique_selected_event_count": int(len(selected_counts)),
            "selection_gini": float(_gini(selected_counts.values())),
            "winner_margin": _finite_stats(current["winner_margins"]),
        }

    baseline = factors[_factor_key(_BASELINE_WEIGHT)]
    rank_collapse = factors[_factor_key(0.0)]
    positive_keys = [
        _factor_key(value)
        for value in SECOND_COORDINATE_WEIGHT_PANEL
        if value > 0.0
    ]
    positive_agreements = [
        float(factors[key]["winner_agreement_with_baseline_fraction"])
        for key in positive_keys
    ]
    positive_same_state_deviations = [
        abs(
            float(factors[key]["same_state_winner_fraction"])
            - float(baseline["same_state_winner_fraction"])
        )
        for key in positive_keys
    ]
    positive_nearest = [
        float(
            factors[key][
                "nearest_second_coordinate_fraction_among_same_state_winners"
            ]
        )
        for key in positive_keys
    ]

    return {
        "requested_query_count": requested_query_count,
        "assigned_query_count": assigned_query_count,
        "forced_single_candidate_query_count": forced_single_candidate_query_count,
        "multi_candidate_query_count": multi_candidate_query_count,
        "reconstructed_score_selection_mismatch_count": reconstruction_mismatch_count,
        "visible_ports": [int(value) for value in visible_ports],
        "first_coordinate_port": int(first_port),
        "second_coordinate_port": int(second_port),
        "constant_coordinate_port": int(_constant_port),
        "baseline_candidate_evaluation_count": int(
            total_baseline_candidate_evaluations
        ),
        "weight_factors": factors,
        "source_summary": {
            "rank_collapse_winner_agreement_fraction": float(
                rank_collapse["winner_agreement_with_baseline_fraction"]
            ),
            "rank_collapse_changed_winner_fraction": 1.0
            - float(rank_collapse["winner_agreement_with_baseline_fraction"]),
            "rank_collapse_same_state_fraction_absolute_change": abs(
                float(rank_collapse["same_state_winner_fraction"])
                - float(baseline["same_state_winner_fraction"])
            ),
            "rank_collapse_age_one_fraction_change": float(
                rank_collapse["age_one_winner_fraction"]
            )
            - float(baseline["age_one_winner_fraction"]),
            "positive_weight_minimum_winner_agreement_fraction": float(
                min(positive_agreements)
            ),
            "positive_weight_maximum_same_state_fraction_absolute_change": float(
                max(positive_same_state_deviations)
            ),
            "positive_weight_minimum_nearest_second_coordinate_fraction": float(
                min(positive_nearest)
            ),
        },
    }


def assess_stage3c30_weight_robustness(
    rank2_study: dict[str, Any],
    rank2_component: dict[str, Any],
    rank2_diagnostics: dict[str, Any],
    stage3c29_assessment: dict[str, Any],
) -> dict[str, Any]:
    """Audit rank collapse and bounded positive second-coordinate weights."""
    if stage3c29_assessment.get("schema") != STAGE3C29_TRANSITION_OCCUPANCY_SCHEMA:
        raise ValueError("Stage-3C-30 requires a Stage-3C-29 assessment")
    _validate_assessment_checksum(
        stage3c29_assessment, label="Stage-3C-29 assessment"
    )
    selected_port = int(
        rank2_study.get("parameters", {}).get(
            "bootstrap_second_readout_input_port", -1
        )
    )
    if selected_port in {0, 11} or selected_port < 0:
        raise ValueError("Stage-3C-30 rank-two readout port is invalid")
    _validate_study(rank2_study, second_port=selected_port)
    _validate_report_set(
        rank2_study, rank2_component, rank2_diagnostics, label="rank2"
    )
    if stage3c29_assessment.get("rank2_study_sha256") != rank2_study.get(
        "study_sha256"
    ):
        raise ValueError("Stage-3C-30 Stage-3C-29 lineage mismatch")
    if not bool(
        stage3c29_assessment["diagnostic_interpretation"].get(
            "subject_anchored_second_coordinate_locality_remains_predictive_after_opportunity_conditioning"
        )
    ):
        raise ValueError("Stage-3C-30 requires the complete Stage-3C-29 screen")

    source_records = _source_records(rank2_study)
    per_source: list[dict[str, Any]] = []
    all_reconstructed = True
    rank_collapse_changes_all = True
    rank_collapse_state_fraction_preserved_all = True
    positive_nearest_all = True
    positive_min_exceeds_rank_collapse_all = True
    rank_collapse_age_one_increases_all = True

    for seed in sorted(source_records):
        source = source_records[seed]
        row = _source_weight_robustness(source["read_only_control_checkpoint"])
        row["seed"] = int(seed)
        all_reconstructed &= row["reconstructed_score_selection_mismatch_count"] == 0
        summary = row["source_summary"]
        rank_collapse_changes_all &= (
            float(summary["rank_collapse_changed_winner_fraction"]) > 0.0
        )
        rank_collapse_state_fraction_preserved_all &= (
            float(summary["rank_collapse_same_state_fraction_absolute_change"])
            <= 1e-12
        )
        positive_nearest_all &= (
            float(summary["positive_weight_minimum_nearest_second_coordinate_fraction"])
            == 1.0
        )
        positive_min_exceeds_rank_collapse_all &= (
            float(summary["positive_weight_minimum_winner_agreement_fraction"])
            > float(summary["rank_collapse_winner_agreement_fraction"])
        )
        rank_collapse_age_one_increases_all &= (
            float(summary["rank_collapse_age_one_fraction_change"]) > 0.0
        )
        per_source.append(row)

    if not all_reconstructed:
        raise ValueError("Stage-3C-30 reconstructed selector mismatch")

    payload = {
        "schema": STAGE3C30_WEIGHT_ROBUSTNESS_SCHEMA,
        "producer_version": __version__,
        "rank2_study_sha256": rank2_study["study_sha256"],
        "stage3c29_assessment_sha256": stage3c29_assessment[
            "assessment_sha256"
        ],
        "analysis_only_factor": (
            "multiply only the frozen rank-two second visible coordinate by a "
            "predeclared bounded weight while preserving the authoritative raw "
            "candidate opportunity set"
        ),
        "second_coordinate_weight_panel": [
            float(value) for value in SECOND_COORDINATE_WEIGHT_PANEL
        ],
        "runtime_experimental_factor_changed": False,
        "isolation_contract": {
            "independent_source_count": len(per_source),
            "seeds": sorted(source_records),
            "stage3c29_checksum_and_lineage_verified": True,
            "stored_winner_ids_and_scores_exactly_reconstructed": True,
            "forced_single_candidate_queries_excluded_from_weight_screen": True,
            "authoritative_raw_threshold_candidate_set_reused_for_every_weight": True,
            "same_candidate_evaluation_count_in_every_weight_arm": True,
            "same_first_coordinate_constant_coordinate_delay_latest_top1_target_carrier_delta_exposure_and_rollback": True,
            "highest_independent_replicate": "independent-pre-bootstrap-source-checkpoint",
            "queries_events_subjects_or_windows_are_independent_replicates": False,
        },
        "per_source": per_source,
        "source_balanced_summary": {
            "rank_collapse_winner_agreement_fraction": _aggregate_source_metric(
                per_source,
                ("source_summary", "rank_collapse_winner_agreement_fraction"),
            ),
            "rank_collapse_changed_winner_fraction": _aggregate_source_metric(
                per_source,
                ("source_summary", "rank_collapse_changed_winner_fraction"),
            ),
            "rank_collapse_same_state_fraction_absolute_change": _aggregate_source_metric(
                per_source,
                (
                    "source_summary",
                    "rank_collapse_same_state_fraction_absolute_change",
                ),
            ),
            "rank_collapse_age_one_fraction_change": _aggregate_source_metric(
                per_source,
                ("source_summary", "rank_collapse_age_one_fraction_change"),
            ),
            "positive_weight_minimum_winner_agreement_fraction": _aggregate_source_metric(
                per_source,
                (
                    "source_summary",
                    "positive_weight_minimum_winner_agreement_fraction",
                ),
            ),
            "positive_weight_maximum_same_state_fraction_absolute_change": _aggregate_source_metric(
                per_source,
                (
                    "source_summary",
                    "positive_weight_maximum_same_state_fraction_absolute_change",
                ),
            ),
            "positive_weight_minimum_nearest_second_coordinate_fraction": _aggregate_source_metric(
                per_source,
                (
                    "source_summary",
                    "positive_weight_minimum_nearest_second_coordinate_fraction",
                ),
            ),
        },
        "cross_source_findings": {
            "rank_collapse_changes_selected_identity_in_all_sources": rank_collapse_changes_all,
            "rank_collapse_preserves_same_state_winner_fraction_exactly_in_all_sources": rank_collapse_state_fraction_preserved_all,
            "rank_collapse_increases_age_one_winner_fraction_in_all_sources": rank_collapse_age_one_increases_all,
            "every_positive_weight_preserves_nearest_second_coordinate_ordering_in_all_sources": positive_nearest_all,
            "minimum_positive_weight_agreement_exceeds_rank_collapse_agreement_in_all_sources": positive_min_exceeds_rank_collapse_all,
        },
        "diagnostic_interpretation": {
            "first_coordinate_state_basin_persists_after_second_coordinate_rank_collapse": rank_collapse_state_fraction_preserved_all,
            "second_coordinate_is_required_to_resolve_within_state_winner_identity": bool(
                rank_collapse_changes_all and positive_nearest_all
            ),
            "exact_positive_second_coordinate_weight_is_fine_tuned": not bool(
                positive_min_exceeds_rank_collapse_all and positive_nearest_all
            ),
            "weight_robustness_proves_value_or_causal_credit_quality": False,
            "next_authorized_step": (
                "Treat the first coordinate as the state-basin owner and the "
                "non-zero second coordinate as a robust within-state ordering "
                "dimension in this fixed bootstrap. Do not infer a beneficial "
                "weight, add learned weighting or authorize retention without a "
                "separate costed shared-checkpoint intervention and objective-fact "
                "ablation."
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
            "Assess Stage-3C-30 rank collapse and bounded positive "
            "second-coordinate weight robustness."
        )
    )
    parser.add_argument("--rank2-study-report", required=True)
    parser.add_argument("--rank2-component", required=True)
    parser.add_argument("--rank2-diagnostics", required=True)
    parser.add_argument("--stage3c29-assessment", required=True)
    parser.add_argument("--output", required=True)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    result = assess_stage3c30_weight_robustness(
        _load_json(args.rank2_study_report),
        _load_json(args.rank2_component),
        _load_json(args.rank2_diagnostics),
        _load_json(args.stage3c29_assessment),
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
    "SECOND_COORDINATE_WEIGHT_PANEL",
    "STAGE3C30_WEIGHT_ROBUSTNESS_SCHEMA",
    "assess_stage3c30_weight_robustness",
]
