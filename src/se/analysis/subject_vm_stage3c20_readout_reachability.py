"""Stage 3C-20 fixed-bootstrap visible-readout reachability audit.

The frozen reachable ``edge_forward_gate`` panel is held fixed.  The only
experimental factor is whether the already action-producing node 0 also emits
its current scalar state into association-visible token port 29.  This is an
explicit fixed-bootstrap readout shaping aid.  It does not assign value to the
node state, change normalized-dot similarity, alter candidate limits, retain a
parameter write, or claim a general attention mechanism.
"""
from __future__ import annotations

import argparse
from collections import Counter
from copy import deepcopy
import json
from pathlib import Path
from typing import Any

import numpy as np

from .. import __version__
from ..checkpointing import read_checkpoint_bundle
from .subject_vm_stage3c13_exposure_adequacy import (
    _arm_summary,
    _canonical_sha256,
    _compare_control_behavior,
    _diagnostics_by_seed,
    _load_json,
    _source_records,
    _validate_report_set,
)
from .subject_vm_stage3c17_temporal_tie_break import _association_snapshot
from .subject_vm_stage3c19_token_geometry import _source_geometry

STAGE3C20_READOUT_REACHABILITY_SCHEMA = (
    "se-subject-vm-stage3c20-visible-readout-reachability-assessment-v1"
)

_FROZEN_PARAMETERS = {
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


def _validate_study(study: dict[str, Any], *, readout_enabled: bool) -> None:
    if study.get("schema") != "se-subject-vm-short-paired-study-v1":
        raise ValueError("Stage-3C-20 requires short paired study reports")
    parameters = study.get("parameters", {})
    for key, value in _FROZEN_PARAMETERS.items():
        if parameters.get(key) != value:
            raise ValueError(f"Stage-3C-20 frozen factor mismatch: {key}")
    if parameters.get("bootstrap_node0_visible_readout_enabled") is not readout_enabled:
        raise ValueError("Stage-3C-20 visible readout arm mismatch")
    if len(study.get("seeds", ())) < 3:
        raise ValueError("Stage-3C-20 requires at least three independent sources")
    if not bool(study["engineering_summary"]["stage3c7_engineering_screen_passed"]):
        raise ValueError("Stage-3C-20 arms must pass Stage-3C-7")
    if bool(study.get("permanent_parameter_retention_authorized")):
        raise ValueError("Stage-3C-20 cannot use permanent parameter retention")

    profile = study["bootstrap_profile"]
    shaping = profile.get("association_visible_readout_shaping", {})
    if bool(shaping.get("node_0_state_to_port_29_enabled")) is not readout_enabled:
        raise ValueError("Stage-3C-20 readout parameter/profile mismatch")
    if int(shaping.get("node_index", -1)) != 0 or int(shaping.get("token_port", -1)) != 29:
        raise ValueError("Stage-3C-20 readout target mismatch")
    if shaping.get("value_semantics") is not None:
        raise ValueError("Stage-3C-20 readout cannot carry fixed value semantics")
    node0 = next(
        item for item in profile.get("nodes", ()) if int(item.get("index", -1)) == 0
    )
    expected_port = 29 if readout_enabled else -1
    expected_gate = 1.0 if readout_enabled else 0.0
    if int(node0.get("trace_port", -999)) != expected_port:
        raise ValueError("Stage-3C-20 node-0 trace port mismatch")
    if not np.isclose(float(node0.get("trace_gate", -999.0)), expected_gate):
        raise ValueError("Stage-3C-20 node-0 trace gate mismatch")


def _factor_signature(study: dict[str, Any]) -> dict[str, Any]:
    parameters = dict(study["parameters"])
    parameters.pop("bootstrap_node0_visible_readout_enabled", None)
    return {
        "project_config_file_sha256": study["project_config_file_sha256"],
        "parameters_except_visible_readout": parameters,
        "population": study["population"],
        "resolved_backend": study["resolved_backend"],
        "temporary_exposure_contract": study["temporary_exposure_contract"],
        "fixed_bootstrap_is_evolved_result": study[
            "fixed_bootstrap_is_evolved_result"
        ],
        "universal_attention_claim": study["universal_attention_claim"],
        "permanent_parameter_retention_authorized": study[
            "permanent_parameter_retention_authorized"
        ],
    }


def _normalized_profile(profile: dict[str, Any]) -> dict[str, Any]:
    payload = deepcopy(profile)
    payload.pop("profile_sha256", None)
    shaping = payload["association_visible_readout_shaping"]
    node0 = next(item for item in payload["nodes"] if int(item["index"]) == 0)
    if int(shaping["node_index"]) != 0 or int(shaping["token_port"]) != 29:
        raise ValueError("unsupported Stage-3C-20 readout profile")
    node0["trace_port"] = "<visible-readout-port>"
    node0["trace_gate"] = "<visible-readout-gate>"
    shaping["node_0_state_to_port_29_enabled"] = "<visible-readout-enabled>"
    shaping["trace_gate"] = "<visible-readout-gate>"
    return payload


def _event_index(trace: dict[str, np.ndarray]) -> dict[tuple[int, int], tuple[int, int]]:
    result: dict[tuple[int, int], tuple[int, int]] = {}
    for row, slot in zip(*np.nonzero(trace["event_valid"]), strict=True):
        key = (int(trace["subject_id"][row, slot]), int(trace["event_tick"][row, slot]))
        if key in result:
            raise ValueError(f"duplicate subject/tick trace event: {key}")
        result[key] = (int(row), int(slot))
    return result


def _compare_authorized_token_readout(
    baseline_checkpoint: str | Path,
    readout_checkpoint: str | Path,
) -> dict[str, Any]:
    _, baseline_state = read_checkpoint_bundle(baseline_checkpoint)
    _, readout_state = read_checkpoint_bundle(readout_checkpoint)
    left = baseline_state["simulation"]["subject_vm"]["trace_storage"]["arrays"]
    right = readout_state["simulation"]["subject_vm"]["trace_storage"]["arrays"]
    left_index = _event_index(left)
    right_index = _event_index(right)
    keys_equal = set(left_index) == set(right_index)
    non_port29_mismatch = 0
    baseline_nonzero_port29 = 0
    readout_nonzero_port29 = 0
    readout_unique_values: set[float] = set()
    if keys_equal:
        for key in sorted(left_index):
            li = left_index[key]
            ri = right_index[key]
            left_token = np.asarray(left["thought_token"][li])
            right_token = np.asarray(right["thought_token"][ri])
            mask = np.ones(left_token.shape, dtype=bool)
            mask[29] = False
            non_port29_mismatch += int(not np.array_equal(left_token[mask], right_token[mask]))
            baseline_nonzero_port29 += int(left_token[29] != 0.0)
            readout_nonzero_port29 += int(right_token[29] != 0.0)
            readout_unique_values.add(float(right_token[29]))
    return {
        "event_keys_equal": keys_equal,
        "non_port29_token_mismatch_count": int(non_port29_mismatch),
        "baseline_nonzero_port29_event_count": int(baseline_nonzero_port29),
        "readout_nonzero_port29_event_count": int(readout_nonzero_port29),
        "readout_port29_exact_unique_value_count": len(readout_unique_values),
        "tokens_equal_except_authorized_port29_readout": bool(
            keys_equal
            and non_port29_mismatch == 0
            and baseline_nonzero_port29 == 0
            and readout_nonzero_port29 > 0
            and len(readout_unique_values) > 1
        ),
    }


def _axis_decomposition(record: dict[str, Any]) -> dict[str, Any]:
    _, state = read_checkpoint_bundle(record["read_only_control_checkpoint"])
    arrays = state["simulation"]["subject_vm"]["trace_storage"]["arrays"]
    valid = np.asarray(arrays["event_valid"], dtype=bool)
    ticks = np.asarray(arrays["event_tick"], dtype=np.int64)
    values = np.asarray(arrays["thought_token"], dtype=np.float64)[..., 29]
    tick_rows: list[dict[str, Any]] = []
    means: list[float] = []
    variances: list[float] = []
    for tick in sorted(int(value) for value in np.unique(ticks[valid]).tolist()):
        mask = valid & (ticks == tick)
        current = values[mask]
        means.append(float(current.mean()))
        variances.append(float(current.var()))
        tick_rows.append(
            {
                "tick": tick,
                "subject_count": int(current.size),
                "minimum": float(current.min()),
                "maximum": float(current.max()),
                "mean": float(current.mean()),
                "subject_variance": float(current.var()),
                "exact_unique_value_count": int(np.unique(current).size),
            }
        )
    return {
        "per_tick": tick_rows,
        "all_subjects_equal_within_each_tick": bool(
            variances and np.allclose(variances, 0.0, rtol=0.0, atol=0.0)
        ),
        "maximum_within_tick_subject_variance": max(variances, default=0.0),
        "between_tick_mean_variance": float(np.var(means)) if means else 0.0,
        "exact_unique_tick_mean_count": int(np.unique(np.asarray(means)).size),
    }


def _geometry_summary(study: dict[str, Any]) -> dict[str, Any]:
    per_source = [_source_geometry(record) for record in study["seeds"]]
    axis = [_axis_decomposition(record) for record in study["seeds"]]
    visible = {tuple(item["association_visible_ports"]) for item in per_source}
    if visible != {(29, 30, 31)}:
        raise ValueError("Stage-3C-20 association-visible port contract changed")
    score_stats = [
        item["score_separability"]["all_pairwise_normalized_dot_scores"]
        for item in per_source
    ]
    spread_stats = [
        item["score_separability"]["best_minus_second_score_spread"]
        for item in per_source
    ]
    tick_mean_trajectories = [
        tuple(row["mean"] for row in item["per_tick"]) for item in axis
    ]
    return {
        "association_visible_ports": [29, 30, 31],
        "total_visible_token_count": int(sum(item["token_count"] for item in per_source)),
        "exact_unique_visible_token_count_per_source": [
            int(item["exact_unique_visible_token_count"]) for item in per_source
        ],
        "unique_normalized_direction_count_per_source": [
            int(item["unique_normalized_direction_count"]) for item in per_source
        ],
        "centered_covariance_rank_per_source": [
            int(item["centered_covariance"]["numerical_rank"]) for item in per_source
        ],
        "uncentered_second_moment_rank_per_source": [
            int(item["uncentered_second_moment"]["numerical_rank"]) for item in per_source
        ],
        "all_pairwise_score_statistics_per_source": score_stats,
        "best_minus_second_score_spread_per_source": spread_stats,
        "all_eligible_scores_identical_per_source": [
            bool(item["score_separability"]["all_eligible_scores_identical"])
            for item in per_source
        ],
        "all_best_second_spreads_zero_per_source": [
            bool(item["score_separability"]["all_best_second_spreads_zero"])
            for item in per_source
        ],
        "queries_with_candidate_per_source": [
            int(item["score_separability"]["queries_with_at_least_one_candidate"])
            for item in per_source
        ],
        "eligible_query_candidate_pair_count_per_source": [
            int(item["score_separability"]["eligible_query_candidate_pair_count"])
            for item in per_source
        ],
        "port29_axis_decomposition_per_source": axis,
        "all_subjects_equal_within_tick_in_all_sources": all(
            item["all_subjects_equal_within_each_tick"] for item in axis
        ),
        "between_tick_port29_variance_positive_in_all_sources": all(
            item["between_tick_mean_variance"] > 0.0 for item in axis
        ),
        "all_sources_share_same_port29_tick_mean_trajectory": len(
            set(tick_mean_trajectories)
        )
        == 1,
        "per_source": per_source,
    }


def _aggregate_association(study: dict[str, Any]) -> dict[str, Any]:
    snapshots = [
        _association_snapshot(record["read_only_control_checkpoint"])
        for record in study["seeds"]
    ]
    delays: Counter[int] = Counter()
    assigned = 0
    unique_events: list[int] = []
    max_reuse: list[int] = []
    similarity_minima: list[float] = []
    similarity_maxima: list[float] = []
    for snapshot in snapshots:
        assigned += int(snapshot["assigned_association_count"])
        delays.update(
            {int(key): int(value) for key, value in snapshot["delay_histogram"].items()}
        )
        unique_events.append(int(snapshot["unique_associated_event_count"]))
        max_reuse.append(int(snapshot["maximum_reuse_of_one_historical_event"]))
        if snapshot["similarity_minimum"] is not None:
            similarity_minima.append(float(snapshot["similarity_minimum"]))
        if snapshot["similarity_maximum"] is not None:
            similarity_maxima.append(float(snapshot["similarity_maximum"]))
    return {
        "assigned_association_count": int(assigned),
        "delay_histogram": {
            str(key): int(value) for key, value in sorted(delays.items())
        },
        "similarity_minimum": min(similarity_minima) if similarity_minima else None,
        "similarity_maximum": max(similarity_maxima) if similarity_maxima else None,
        "all_assigned_similarities_one": all(
            bool(item["all_assigned_similarities_one"]) for item in snapshots
        ),
        "per_source_unique_associated_event_count": unique_events,
        "per_source_maximum_historical_event_reuse": max_reuse,
        "per_source": snapshots,
    }


def _stage_totals(diagnostics: dict[str, Any]) -> dict[str, int]:
    keys = (
        "association_candidate_count",
        "modulation_proposal_count",
        "target_binding_event_count",
        "safe_update_event_count",
        "shadow_transaction_count",
        "guarded_live_commit_count",
        "completed_evaluation_window_count",
    )
    return {
        key: int(
            sum(
                source["guarded_live"]["funnel"]["stage_event_totals"].get(key, 0)
                for source in diagnostics["per_source"]
            )
        )
        for key in keys
    }


def assess_stage3c20_readout_reachability(
    baseline_study: dict[str, Any],
    baseline_component: dict[str, Any],
    baseline_diagnostics: dict[str, Any],
    readout_study: dict[str, Any],
    readout_component: dict[str, Any],
    readout_diagnostics: dict[str, Any],
) -> dict[str, Any]:
    _validate_study(baseline_study, readout_enabled=False)
    _validate_study(readout_study, readout_enabled=True)
    _validate_report_set(
        baseline_study, baseline_component, baseline_diagnostics, label="baseline"
    )
    _validate_report_set(
        readout_study, readout_component, readout_diagnostics, label="readout"
    )
    if _factor_signature(baseline_study) != _factor_signature(readout_study):
        raise ValueError("readout reachability comparison changed another study factor")
    if _normalized_profile(baseline_study["bootstrap_profile"]) != _normalized_profile(
        readout_study["bootstrap_profile"]
    ):
        raise ValueError("bootstrap profiles differ beyond the authorized readout")

    baseline_sources = _source_records(baseline_study)
    readout_sources = _source_records(readout_study)
    if set(baseline_sources) != set(readout_sources):
        raise ValueError("readout reachability arms use different source panels")

    pre_state_equal = True
    pre_config_equal = True
    subject_selection_equal = True
    control_behavior_equal = True
    token_route_equal = True
    per_source: list[dict[str, Any]] = []
    for seed in sorted(baseline_sources):
        left = baseline_sources[seed]
        right = readout_sources[seed]
        same_state = bool(
            left["pre_bootstrap_checkpoint_state_sha256"]
            == right["pre_bootstrap_checkpoint_state_sha256"]
        )
        same_config = bool(
            left["pre_bootstrap_checkpoint_config_sha256"]
            == right["pre_bootstrap_checkpoint_config_sha256"]
        )
        same_subjects = bool(
            left["bootstrap_lineage"]["primed_tick"]
            == right["bootstrap_lineage"]["primed_tick"]
            and left["bootstrap_lineage"]["primed_subject_ids"]
            == right["bootstrap_lineage"]["primed_subject_ids"]
        )
        control = _compare_control_behavior(
            left["read_only_control_checkpoint"],
            right["read_only_control_checkpoint"],
        )
        objective_behavior_equal = bool(
            control["event_keys_equal"]
            and set(control["mismatched_array_event_counts"]) <= {"thought_token"}
        )
        token = _compare_authorized_token_readout(
            left["read_only_control_checkpoint"],
            right["read_only_control_checkpoint"],
        )
        pre_state_equal &= same_state
        pre_config_equal &= same_config
        subject_selection_equal &= same_subjects
        control_behavior_equal &= objective_behavior_equal
        token_route_equal &= bool(token["tokens_equal_except_authorized_port29_readout"])
        per_source.append(
            {
                "seed": int(seed),
                "pre_bootstrap_state_hash_equal": same_state,
                "pre_bootstrap_config_hash_equal": same_config,
                "bootstrap_subject_selection_equal": same_subjects,
                "post_bootstrap_source_state_hashes_differ": bool(
                    left["source_checkpoint_state_sha256"]
                    != right["source_checkpoint_state_sha256"]
                ),
                "read_only_control_behavior": control,
                "read_only_control_objective_behavior_equal": objective_behavior_equal,
                "authorized_token_readout_comparison": token,
            }
        )
    if not all(
        (
            pre_state_equal,
            pre_config_equal,
            subject_selection_equal,
            control_behavior_equal,
            token_route_equal,
        )
    ):
        raise ValueError("Stage-3C-20 isolation or read-only invariance check failed")

    baseline_geometry = _geometry_summary(baseline_study)
    readout_geometry = _geometry_summary(readout_study)
    if baseline_geometry["centered_covariance_rank_per_source"] != [
        0
    ] * len(per_source):
        raise ValueError("Stage-3C-20 baseline did not reproduce rank-zero geometry")
    if not all(
        rank >= 1 for rank in readout_geometry["centered_covariance_rank_per_source"]
    ):
        raise ValueError("Stage-3C-20 readout did not create visible centered variance")
    if not all(baseline_geometry["all_eligible_scores_identical_per_source"]):
        raise ValueError("Stage-3C-20 baseline did not reproduce score degeneracy")
    if any(readout_geometry["all_eligible_scores_identical_per_source"]):
        raise ValueError("Stage-3C-20 readout did not create score separability")
    if not readout_geometry["all_subjects_equal_within_tick_in_all_sources"]:
        raise ValueError("Stage-3C-20 readout unexpectedly introduced subject-specific geometry")
    if not readout_geometry["between_tick_port29_variance_positive_in_all_sources"]:
        raise ValueError("Stage-3C-20 readout lacks temporal variation")

    baseline_association = _aggregate_association(baseline_study)
    readout_association = _aggregate_association(readout_study)
    baseline_arm = {
        **_arm_summary(baseline_study, baseline_component, baseline_diagnostics),
        "stage_event_totals": _stage_totals(baseline_diagnostics),
        "association_allocation": baseline_association,
        "token_geometry": baseline_geometry,
    }
    readout_arm = {
        **_arm_summary(readout_study, readout_component, readout_diagnostics),
        "stage_event_totals": _stage_totals(readout_diagnostics),
        "association_allocation": readout_association,
        "token_geometry": readout_geometry,
    }

    payload = {
        "schema": STAGE3C20_READOUT_REACHABILITY_SCHEMA,
        "producer_version": __version__,
        "baseline_study_sha256": baseline_study["study_sha256"],
        "readout_study_sha256": readout_study["study_sha256"],
        "single_changed_experimental_factor": (
            "fixed-bootstrap graph readout: node 0 state absent from visible token "
            "-> node 0 state emitted to association-visible port 29 with gate 1.0"
        ),
        "unchanged_factor_signature": _factor_signature(baseline_study),
        "isolation_contract": {
            "independent_source_count": len(per_source),
            "seeds": sorted(baseline_sources),
            "pre_bootstrap_state_hashes_equal": pre_state_equal,
            "pre_bootstrap_config_hashes_equal": pre_config_equal,
            "bootstrap_subject_selection_equal": subject_selection_equal,
            "bootstrap_profiles_differ_only_in_node0_visible_readout": True,
            "read_only_control_objective_behavior_equal": control_behavior_equal,
            "thought_tokens_equal_except_authorized_port29_readout": token_route_equal,
            "same_similarity_metric_threshold_and_delay_bounds": True,
            "same_candidate_limit_and_tie_break": True,
            "same_edge_forward_gate_target_and_carrier": True,
            "same_delta_exposure_rollback_and_evaluation_contract": True,
            "highest_independent_replicate": "independent-pre-bootstrap-source-checkpoint",
            "tokens_windows_or_subjects_are_independent_replicates": False,
        },
        "baseline": baseline_arm,
        "readout": readout_arm,
        "comparison": {
            "change_in_assigned_associations": int(
                readout_association["assigned_association_count"]
                - baseline_association["assigned_association_count"]
            ),
            "change_in_modulation_proposals": int(
                readout_arm["stage_event_totals"]["modulation_proposal_count"]
                - baseline_arm["stage_event_totals"]["modulation_proposal_count"]
            ),
            "change_in_live_commits": int(
                readout_arm["live_commits"] - baseline_arm["live_commits"]
            ),
            "change_in_completed_paired_windows": int(
                readout_arm["completed_paired_windows"]
                - baseline_arm["completed_paired_windows"]
            ),
            "change_in_discrete_action_difference_events": int(
                readout_arm["discrete_action_difference_events"]
                - baseline_arm["discrete_action_difference_events"]
            ),
            "change_in_sources_with_objective_event_divergence": int(
                readout_arm["sources_with_objective_event_divergence"]
                - baseline_arm["sources_with_objective_event_divergence"]
            ),
            "change_in_stable_objective_coordinate_count": int(
                readout_arm["stable_objective_coordinate_count"]
                - baseline_arm["stable_objective_coordinate_count"]
            ),
        },
        "per_source": per_source,
        "diagnostic_interpretation": {
            "readout_creates_association_visible_centered_variance": True,
            "readout_creates_nontrivial_normalized_dot_score_spread": True,
            "readout_removes_exact_similarity_ties_at_current_working_point": all(
                not item
                for item in readout_geometry[
                    "all_best_second_spreads_zero_per_source"
                ]
            ),
            "readout_changes_selected_historical_delay": bool(
                baseline_association["delay_histogram"]
                != readout_association["delay_histogram"]
            ),
            "readout_creates_subject_specific_geometry": False,
            "readout_creates_source_specific_geometry": False,
            "current_readout_is_shared_temporal_phase_not_event_identity": True,
            "readout_increases_cross_source_objective_stability": bool(
                readout_arm["stable_objective_coordinate_count"]
                > baseline_arm["stable_objective_coordinate_count"]
            ),
            "readout_validates_causal_credit": False,
            "readout_has_value_semantics": False,
            "next_authorized_step": (
                "Keep the visible node-0 readout as an explicit fixed-bootstrap arm and diagnose one existing objective or internal readout that can add subject/event-specific variance without changing similarity, candidate limit, update scale, retention or permanent writes in the same experiment."
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


def assess_from_paths(
    *,
    baseline_study_report: str | Path,
    baseline_component: str | Path,
    baseline_diagnostics: str | Path,
    readout_study_report: str | Path,
    readout_component: str | Path,
    readout_diagnostics: str | Path,
) -> dict[str, Any]:
    return assess_stage3c20_readout_reachability(
        _load_json(baseline_study_report),
        _load_json(baseline_component),
        _load_json(baseline_diagnostics),
        _load_json(readout_study_report),
        _load_json(readout_component),
        _load_json(readout_diagnostics),
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Assess fixed-bootstrap association-visible readout reachability."
    )
    parser.add_argument("--baseline-study-report", required=True)
    parser.add_argument("--baseline-component", required=True)
    parser.add_argument("--baseline-diagnostics", required=True)
    parser.add_argument("--readout-study-report", required=True)
    parser.add_argument("--readout-component", required=True)
    parser.add_argument("--readout-diagnostics", required=True)
    parser.add_argument("--output", required=True)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    result = assess_from_paths(
        baseline_study_report=args.baseline_study_report,
        baseline_component=args.baseline_component,
        baseline_diagnostics=args.baseline_diagnostics,
        readout_study_report=args.readout_study_report,
        readout_component=args.readout_component,
        readout_diagnostics=args.readout_diagnostics,
    )
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(
        json.dumps(
            {
                "assessment_sha256": result["assessment_sha256"],
                "comparison": result["comparison"],
                "diagnostic_interpretation": result["diagnostic_interpretation"],
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()


__all__ = [
    "STAGE3C20_READOUT_REACHABILITY_SCHEMA",
    "assess_from_paths",
    "assess_stage3c20_readout_reachability",
]
