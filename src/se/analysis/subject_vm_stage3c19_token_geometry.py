"""Stage 3C-19 external association-visible token-geometry diagnostic.

The frozen Stage-3C-16 reachable edge-carrier baseline is analysed without
changing runtime state, candidate allocation, similarity, update, rollback or
retention contracts.  Only coordinates that the association scorer can see
are included.  Similarity remains address evidence and is not interpreted as
value, causal quality or credit strength.
"""
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
from typing import Any

import numpy as np

from .. import __version__
from ..checkpointing import read_checkpoint_bundle
from ..subject_vm.modulation import modulation_control_ports
from .subject_vm_stage3c13_exposure_adequacy import _canonical_sha256, _load_json

STAGE3C19_TOKEN_GEOMETRY_SCHEMA = (
    "se-subject-vm-stage3c19-token-geometry-separability-assessment-v1"
)


def _validate_study(study: dict[str, Any]) -> None:
    if study.get("schema") != "se-subject-vm-short-paired-study-v1":
        raise ValueError("Stage-3C-19 requires a short paired study report")
    parameters = study.get("parameters", {})
    expected = {
        "source_ticks": 2,
        "horizon_ticks": 8,
        "bootstrap_subjects": 16,
        "backend": "cpu",
        "rollback_after_ticks": 3,
        "bootstrap_target_family": "edge_forward_gate",
        "bootstrap_edge_carrier_enabled": True,
        "association_tie_break": "latest",
        "association_candidate_limit": 1,
        "association_candidate_aggregation": "equal-weight-mean",
    }
    for key, value in expected.items():
        if parameters.get(key) != value:
            raise ValueError(f"Stage-3C-19 frozen baseline mismatch: {key}")
    if len(study.get("seeds", ())) < 3:
        raise ValueError("Stage-3C-19 requires at least three independent sources")
    if not bool(study["engineering_summary"]["stage3c7_engineering_screen_passed"]):
        raise ValueError("Stage-3C-19 requires a passing Stage-3C-7 panel")
    if bool(study.get("permanent_parameter_retention_authorized")):
        raise ValueError("Stage-3C-19 cannot use permanent parameter retention")


def _spectrum(matrix: np.ndarray, *, centered: bool) -> dict[str, Any]:
    data = np.asarray(matrix, dtype=np.float64)
    if data.ndim != 2 or data.shape[0] == 0:
        raise ValueError("token geometry requires a non-empty matrix")
    working = data - data.mean(axis=0, keepdims=True) if centered else data
    gram = (working.T @ working) / float(data.shape[0])
    values = np.linalg.eigvalsh(gram)[::-1]
    values[np.abs(values) < 1e-15] = 0.0
    maximum = float(values[0]) if values.size else 0.0
    tolerance = max(data.shape) * np.finfo(np.float64).eps * max(maximum, 1.0)
    positive = values[values > tolerance]
    numerical_rank = int(positive.size)
    if positive.size:
        probability = positive / positive.sum()
        effective_rank = float(np.exp(-np.sum(probability * np.log(probability))))
        participation_ratio = float(positive.sum() ** 2 / np.square(positive).sum())
    else:
        effective_rank = 0.0
        participation_ratio = 0.0
    return {
        "eigenvalues_descending": [float(value) for value in values.tolist()],
        "numerical_rank": numerical_rank,
        "rank_tolerance": float(tolerance),
        "effective_rank": effective_rank,
        "participation_ratio": participation_ratio,
    }


def _stats(values: list[float]) -> dict[str, Any]:
    if not values:
        return {"count": 0, "min": None, "max": None, "mean": None, "median": None, "variance": None}
    array = np.asarray(values, dtype=np.float64)
    return {
        "count": int(array.size),
        "min": float(array.min()),
        "max": float(array.max()),
        "mean": float(array.mean()),
        "median": float(np.median(array)),
        "variance": float(array.var()),
    }


def _source_geometry(record: dict[str, Any]) -> dict[str, Any]:
    _, state = read_checkpoint_bundle(record["read_only_control_checkpoint"])
    cfg = state["config"].subject_vm
    trace_state = state["simulation"]["subject_vm"]["trace_storage"]
    arrays = trace_state["arrays"]
    valid = np.asarray(arrays["event_valid"], dtype=bool)
    tokens = np.asarray(arrays["thought_token"], dtype=np.float64)
    ticks = np.asarray(arrays["event_tick"], dtype=np.int64)
    subject_ids = np.asarray(arrays["subject_id"], dtype=np.uint64)

    excluded = sorted(
        {
            int(cfg.association.request_token_port),
            *(int(value) for value in modulation_control_ports(cfg.modulation)),
        }
    )
    visible = [port for port in range(int(cfg.trace.token_width)) if port not in excluded]
    token_matrix = tokens[valid][:, visible]
    if token_matrix.size == 0:
        raise ValueError("Stage-3C-19 found no association-visible tokens")
    bootstrap_ids = set(int(value) for value in record["bootstrap_lineage"]["primed_subject_ids"])
    traced_ids = set(int(value) for value in subject_ids[valid].tolist())
    if traced_ids != bootstrap_ids:
        raise ValueError("Stage-3C-19 trace subjects do not match bootstrap lineage")

    coordinate_stats: list[dict[str, Any]] = []
    for index, port in enumerate(visible):
        column = token_matrix[:, index]
        coordinate_stats.append(
            {
                "port": int(port),
                "min": float(column.min()),
                "max": float(column.max()),
                "mean": float(column.mean()),
                "variance": float(column.var()),
                "nonzero_fraction": float(np.count_nonzero(column) / column.size),
                "exact_unique_value_count": int(np.unique(column).size),
            }
        )

    norms = np.linalg.norm(token_matrix, axis=1)
    nonzero = norms > 0.0
    normalized = np.zeros_like(token_matrix)
    normalized[nonzero] = token_matrix[nonzero] / norms[nonzero, None]
    exact_unique = np.unique(token_matrix, axis=0)
    direction_unique = np.unique(normalized[nonzero], axis=0)

    all_scores: list[float] = []
    threshold_margins: list[float] = []
    best_second_spreads: list[float] = []
    eligible_counts: list[int] = []
    best_tie_counts: list[int] = []
    exact_equal_pairs = 0
    pair_count = 0
    requested_query_count = 0
    queries_with_candidate = 0
    zero_query_count = 0
    zero_candidate_pair_count = 0
    delay_histogram: Counter[int] = Counter()

    for row in range(valid.shape[0]):
        slots = np.flatnonzero(valid[row])
        slots = slots[np.argsort(ticks[row, slots], kind="stable")]
        for slot in slots.tolist():
            current = tokens[row, slot, visible]
            request = float(tokens[row, slot, int(cfg.association.request_token_port)])
            if request < float(cfg.association.request_threshold):
                continue
            requested_query_count += 1
            current_norm = float(np.linalg.norm(current))
            if current_norm == 0.0:
                zero_query_count += 1
                continue
            scores: list[float] = []
            for historical_slot in slots.tolist():
                delay = int(ticks[row, slot] - ticks[row, historical_slot])
                if delay < int(cfg.association.min_delay_ticks) or delay > int(cfg.association.max_delay_ticks):
                    continue
                candidate = tokens[row, historical_slot, visible]
                candidate_norm = float(np.linalg.norm(candidate))
                if candidate_norm == 0.0:
                    zero_candidate_pair_count += 1
                    continue
                score = float(np.dot(current, candidate) / (current_norm * candidate_norm))
                score = float(np.clip(score, -1.0, 1.0))
                scores.append(score)
                all_scores.append(score)
                delay_histogram[delay] += 1
                pair_count += 1
                if np.array_equal(current, candidate):
                    exact_equal_pairs += 1
            if not scores:
                continue
            queries_with_candidate += 1
            scores.sort(reverse=True)
            eligible_counts.append(sum(score >= float(cfg.association.similarity_threshold) for score in scores))
            threshold_margins.append(scores[0] - float(cfg.association.similarity_threshold))
            best_tie_counts.append(sum(np.isclose(score, scores[0], rtol=0.0, atol=1e-12) for score in scores))
            if len(scores) >= 2:
                best_second_spreads.append(scores[0] - scores[1])

    payload = {
        "seed": int(record["seed"]),
        "checkpoint_tick": int(state["simulation"]["tick"]),
        "bootstrap_subject_count": len(bootstrap_ids),
        "token_count": int(token_matrix.shape[0]),
        "token_width": int(cfg.trace.token_width),
        "excluded_control_ports": excluded,
        "association_visible_ports": visible,
        "coordinate_statistics": coordinate_stats,
        "exact_unique_visible_token_count": int(exact_unique.shape[0]),
        "exact_duplicate_token_fraction": float(1.0 - exact_unique.shape[0] / token_matrix.shape[0]),
        "nonzero_visible_token_count": int(np.count_nonzero(nonzero)),
        "unique_normalized_direction_count": int(direction_unique.shape[0]),
        "normalized_direction_duplicate_fraction": float(1.0 - direction_unique.shape[0] / np.count_nonzero(nonzero)),
        "visible_token_norm": _stats([float(value) for value in norms.tolist()]),
        "centered_covariance": _spectrum(token_matrix, centered=True),
        "uncentered_second_moment": _spectrum(token_matrix, centered=False),
        "score_separability": {
            "requested_query_count": requested_query_count,
            "queries_with_at_least_one_candidate": queries_with_candidate,
            "eligible_query_candidate_pair_count": pair_count,
            "delay_histogram": {str(key): int(value) for key, value in sorted(delay_histogram.items())},
            "zero_query_count": zero_query_count,
            "zero_candidate_pair_count": zero_candidate_pair_count,
            "exact_query_candidate_vector_equality_count": exact_equal_pairs,
            "exact_query_candidate_vector_equality_fraction": float(exact_equal_pairs / pair_count) if pair_count else 0.0,
            "all_pairwise_normalized_dot_scores": _stats(all_scores),
            "best_score_threshold_margin": _stats(threshold_margins),
            "best_minus_second_score_spread": _stats(best_second_spreads),
            "eligible_candidates_per_query": _stats([float(value) for value in eligible_counts]),
            "best_score_tie_count_per_query": _stats([float(value) for value in best_tie_counts]),
            "all_eligible_scores_identical": bool(all_scores and np.allclose(all_scores, all_scores[0], rtol=0.0, atol=1e-12)),
            "all_best_second_spreads_zero": bool(best_second_spreads and np.allclose(best_second_spreads, 0.0, rtol=0.0, atol=1e-12)),
        },
    }
    payload["source_geometry_sha256"] = _canonical_sha256(payload)
    return payload


def assess_stage3c19_token_geometry(study: dict[str, Any]) -> dict[str, Any]:
    _validate_study(study)
    per_source = [_source_geometry(record) for record in study["seeds"]]
    visible_sets = {tuple(item["association_visible_ports"]) for item in per_source}
    excluded_sets = {tuple(item["excluded_control_ports"]) for item in per_source}
    if len(visible_sets) != 1 or len(excluded_sets) != 1:
        raise ValueError("Stage-3C-19 token coordinate contract differs across sources")

    all_coordinate_variances = [
        stat["variance"] for item in per_source for stat in item["coordinate_statistics"]
    ]
    score_stats = [item["score_separability"]["all_pairwise_normalized_dot_scores"] for item in per_source]
    total_tokens = sum(item["token_count"] for item in per_source)
    total_pairs = sum(item["score_separability"]["eligible_query_candidate_pair_count"] for item in per_source)
    total_equal_pairs = sum(item["score_separability"]["exact_query_candidate_vector_equality_count"] for item in per_source)
    all_scores_identical = all(item["score_separability"]["all_eligible_scores_identical"] for item in per_source)
    all_spreads_zero = all(item["score_separability"]["all_best_second_spreads_zero"] for item in per_source)
    centered_ranks = [item["centered_covariance"]["numerical_rank"] for item in per_source]
    uncentered_ranks = [item["uncentered_second_moment"]["numerical_rank"] for item in per_source]

    payload = {
        "schema": STAGE3C19_TOKEN_GEOMETRY_SCHEMA,
        "producer_version": __version__,
        "study_sha256": study["study_sha256"],
        "diagnostic_scope": "read-only-control association-visible token geometry on frozen nine-source baseline",
        "runtime_state_changed": False,
        "runtime_or_checkpoint_schema_changed": False,
        "isolation_contract": {
            "independent_source_count": len(per_source),
            "seeds": [int(item["seed"]) for item in per_source],
            "highest_independent_replicate": "independent-source-checkpoint",
            "windows_or_tokens_are_independent_replicates": False,
            "candidate_limit_fixed": 1,
            "tie_break_fixed": "latest",
            "target_family_fixed": "edge_forward_gate",
            "edge_local_eligibility_carrier_fixed": True,
            "similarity_metric_fixed": "normalized-dot",
            "similarity_threshold_fixed": 0.8,
            "token_production_changed": False,
            "update_or_rollback_contract_changed": False,
        },
        "geometry_summary": {
            "token_width": per_source[0]["token_width"],
            "excluded_control_ports": list(next(iter(excluded_sets))),
            "association_visible_ports": list(next(iter(visible_sets))),
            "total_visible_token_count": total_tokens,
            "per_source_visible_token_counts": [item["token_count"] for item in per_source],
            "all_association_visible_coordinate_variances_zero": bool(np.allclose(all_coordinate_variances, 0.0, rtol=0.0, atol=0.0)),
            "all_association_visible_tokens_identical_within_each_source": all(item["exact_unique_visible_token_count"] == 1 for item in per_source),
            "all_normalized_visible_directions_identical_within_each_source": all(item["unique_normalized_direction_count"] == 1 for item in per_source),
            "centered_covariance_rank_per_source": centered_ranks,
            "uncentered_second_moment_rank_per_source": uncentered_ranks,
            "centered_effective_rank_per_source": [item["centered_covariance"]["effective_rank"] for item in per_source],
            "uncentered_effective_rank_per_source": [item["uncentered_second_moment"]["effective_rank"] for item in per_source],
        },
        "score_separability": {
            "eligible_query_candidate_pair_count": total_pairs,
            "exact_query_candidate_vector_equality_count": total_equal_pairs,
            "exact_query_candidate_vector_equality_fraction": float(total_equal_pairs / total_pairs) if total_pairs else 0.0,
            "per_source_score_statistics": score_stats,
            "all_eligible_scores_identical": all_scores_identical,
            "all_eligible_scores_equal_one": all(
                item["score_separability"]["all_pairwise_normalized_dot_scores"]["min"] == 1.0
                and item["score_separability"]["all_pairwise_normalized_dot_scores"]["max"] == 1.0
                for item in per_source
            ),
            "all_best_second_score_spreads_zero": all_spreads_zero,
            "threshold_margin_constant": all(
                np.isclose(item["score_separability"]["best_score_threshold_margin"]["variance"], 0.0, rtol=0.0, atol=1e-15)
                for item in per_source
            ),
            "threshold_rejects_any_nonzero_candidate_at_this_working_point": False,
        },
        "per_source": per_source,
        "diagnostic_interpretation": {
            "current_score_has_content_discriminative_power": False,
            "temporal_tie_break_currently_determines_rank_order_after_score": True,
            "increasing_top_k_before_geometry_changes_adds_distinct_token_directions": False,
            "zero_centered_rank_proves_general_token_mechanism_incapable": False,
            "constant_geometry_proves_learning_impossible": False,
            "similarity_has_value_or_causal_semantics": False,
            "next_authorized_step": (
                "Diagnose which existing graph readout or operating context could produce role-neutral variance in the three association-visible ports. "
                "Do not change similarity, top-k, learned weights, update scale, retention or universal-attention architecture in the same experiment."
            ),
        },
        "fixed_cognition_engineering_shaping_aid": True,
        "evolved_topology": False,
        "universal_attention_claim": False,
        "universal_scalar_objective": False,
        "permanent_parameter_retention_authorized": False,
        "causal_effect_authorized": False,
        "learning_claim_authorized": False,
        "subjecthood_claim_authorized": False,
        "runtime_memory_growth_bytes": 0,
    }
    payload["assessment_sha256"] = _canonical_sha256(payload)
    return payload


def assess_from_path(study_report: str | Path) -> dict[str, Any]:
    return assess_stage3c19_token_geometry(_load_json(study_report))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Assess association-visible token geometry separability.")
    parser.add_argument("--study-report", required=True)
    parser.add_argument("--output", required=True)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    result = assess_from_path(args.study_report)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"assessment_sha256": result["assessment_sha256"], "geometry_summary": result["geometry_summary"], "score_separability": result["score_separability"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()


__all__ = [
    "STAGE3C19_TOKEN_GEOMETRY_SCHEMA",
    "assess_from_path",
    "assess_stage3c19_token_geometry",
]
