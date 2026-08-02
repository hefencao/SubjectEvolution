"""Stage 3C-21 subject/event-specific visible-readout audit.

The paired arms use the same readout-only bootstrap node and differ only in
which already-approved objective input port feeds that node.  The constant-one
arm preserves rank-zero addressing geometry; the uncertainty-mean arm tests
whether a role-neutral observation-state readout can introduce both within-tick
subject variance and within-subject temporal variance without changing action
output, similarity, candidate cardinality, update scale, or retention policy.
"""
from __future__ import annotations

import argparse
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
    _load_json,
    _source_records,
    _validate_report_set,
)
from .subject_vm_stage3c19_token_geometry import _source_geometry
from .subject_vm_stage3c20_readout_reachability import (
    _aggregate_association,
    _event_index,
    _stage_totals,
)

STAGE3C21_SUBJECT_EVENT_READOUT_SCHEMA = (
    "se-subject-vm-stage3c21-subject-event-readout-assessment-v1"
)

_FROZEN_PARAMETERS = {
    "source_ticks": 2,
    "horizon_ticks": 8,
    "bootstrap_subjects": 16,
    "backend": "cpu",
    "rollback_after_ticks": 3,
    "bootstrap_target_family": "edge_forward_gate",
    "bootstrap_edge_carrier_enabled": True,
    "bootstrap_node0_visible_readout_enabled": False,
    "association_tie_break": "latest",
    "association_candidate_limit": 1,
    "association_candidate_aggregation": "equal-weight-mean",
}


def _validate_study(study: dict[str, Any], *, input_port: int) -> None:
    if study.get("schema") != "se-subject-vm-short-paired-study-v1":
        raise ValueError("Stage-3C-21 requires short paired study reports")
    parameters = study.get("parameters", {})
    for key, value in _FROZEN_PARAMETERS.items():
        if parameters.get(key) != value:
            raise ValueError(f"Stage-3C-21 frozen factor mismatch: {key}")
    if int(parameters.get("bootstrap_readout_input_port", -1)) != int(input_port):
        raise ValueError("Stage-3C-21 readout input arm mismatch")
    if len(study.get("seeds", ())) < 3:
        raise ValueError("Stage-3C-21 requires at least three independent sources")
    if not bool(study["engineering_summary"]["stage3c7_engineering_screen_passed"]):
        raise ValueError("Stage-3C-21 arms must pass Stage-3C-7")
    if bool(study.get("permanent_parameter_retention_authorized")):
        raise ValueError("Stage-3C-21 cannot use permanent parameter retention")

    profile = study["bootstrap_profile"]
    if int(profile.get("node_count", -1)) != 9:
        raise ValueError("Stage-3C-21 requires the common nine-node bootstrap")
    shaping = profile.get("association_visible_readout_shaping", {})
    readout = shaping.get("readout_only_node", {})
    if not bool(readout.get("enabled")):
        raise ValueError("Stage-3C-21 readout-only node is not enabled")
    if (
        int(readout.get("node_index", -1)) != 8
        or int(readout.get("input_port", -1)) != int(input_port)
        or int(readout.get("token_port", -1)) != 29
    ):
        raise ValueError("Stage-3C-21 readout-only node target mismatch")
    if bool(readout.get("changes_action_output")):
        raise ValueError("Stage-3C-21 readout-only node cannot alter action output")
    if readout.get("value_semantics") is not None:
        raise ValueError("Stage-3C-21 readout cannot carry fixed value semantics")
    node8 = next(item for item in profile["nodes"] if int(item["index"]) == 8)
    if (
        int(node8.get("input_port", -1)) != int(input_port)
        or int(node8.get("trace_port", -1)) != 29
        or int(node8.get("output_port", -2)) != -1
    ):
        raise ValueError("Stage-3C-21 node-8 profile mismatch")


def _factor_signature(study: dict[str, Any]) -> dict[str, Any]:
    parameters = dict(study["parameters"])
    parameters.pop("bootstrap_readout_input_port", None)
    return {
        "project_config_file_sha256": study["project_config_file_sha256"],
        "parameters_except_readout_input_port": parameters,
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
    readout = payload["association_visible_readout_shaping"]["readout_only_node"]
    node8 = next(item for item in payload["nodes"] if int(item["index"]) == 8)
    readout["input_port"] = "<readout-input-port>"
    node8["input_port"] = "<readout-input-port>"
    return payload


def _compare_authorized_port29(
    constant_checkpoint: str | Path,
    uncertainty_checkpoint: str | Path,
) -> dict[str, Any]:
    _, left_state = read_checkpoint_bundle(constant_checkpoint)
    _, right_state = read_checkpoint_bundle(uncertainty_checkpoint)
    left = left_state["simulation"]["subject_vm"]["trace_storage"]["arrays"]
    right = right_state["simulation"]["subject_vm"]["trace_storage"]["arrays"]
    left_index = _event_index(left)
    right_index = _event_index(right)
    keys_equal = set(left_index) == set(right_index)
    non_port29_mismatch = 0
    port29_equal = 0
    port29_different = 0
    if keys_equal:
        for key in sorted(left_index):
            li = left_index[key]
            ri = right_index[key]
            left_token = np.asarray(left["thought_token"][li])
            right_token = np.asarray(right["thought_token"][ri])
            mask = np.ones(left_token.shape, dtype=bool)
            mask[29] = False
            non_port29_mismatch += int(
                not np.array_equal(left_token[mask], right_token[mask])
            )
            equal = bool(left_token[29] == right_token[29])
            port29_equal += int(equal)
            port29_different += int(not equal)
    return {
        "event_keys_equal": keys_equal,
        "non_port29_token_mismatch_count": int(non_port29_mismatch),
        "port29_equal_event_count": int(port29_equal),
        "port29_different_event_count": int(port29_different),
        "tokens_equal_except_authorized_port29_input_change": bool(
            keys_equal and non_port29_mismatch == 0 and port29_different > 0
        ),
    }


def _specificity(record: dict[str, Any]) -> dict[str, Any]:
    _, state = read_checkpoint_bundle(record["read_only_control_checkpoint"])
    arrays = state["simulation"]["subject_vm"]["trace_storage"]["arrays"]
    valid = np.asarray(arrays["event_valid"], dtype=bool)
    ticks = np.asarray(arrays["event_tick"], dtype=np.int64)
    subjects = np.asarray(arrays["subject_id"], dtype=np.uint64)
    values = np.asarray(arrays["thought_token"], dtype=np.float64)[..., 29]

    per_tick: list[dict[str, Any]] = []
    for tick in sorted(int(item) for item in np.unique(ticks[valid]).tolist()):
        current = values[valid & (ticks == tick)]
        per_tick.append(
            {
                "tick": tick,
                "subject_count": int(current.size),
                "exact_unique_value_count": int(np.unique(current).size),
                "subject_variance": float(np.var(current)),
                "minimum": float(np.min(current)),
                "maximum": float(np.max(current)),
            }
        )

    per_subject: list[dict[str, Any]] = []
    for subject in sorted(int(item) for item in np.unique(subjects[valid]).tolist()):
        current = values[valid & (subjects == subject)]
        per_subject.append(
            {
                "subject_id": subject,
                "event_count": int(current.size),
                "exact_unique_value_count": int(np.unique(current).size),
                "temporal_variance": float(np.var(current)),
            }
        )
    temporally_varying_subject_count = sum(
        row["temporal_variance"] > 0.0 for row in per_subject
    )

    matrix_signature = tuple(
        tuple(float(value) for value in values[valid & (ticks == row["tick"])].tolist())
        for row in per_tick
    )
    return {
        "per_tick": per_tick,
        "per_subject": per_subject,
        "all_ticks_have_subject_variance": bool(
            per_tick and all(row["subject_variance"] > 0.0 for row in per_tick)
        ),
        "all_ticks_have_multiple_subject_values": bool(
            per_tick and all(row["exact_unique_value_count"] > 1 for row in per_tick)
        ),
        "all_subjects_have_temporal_variance": bool(
            per_subject and all(row["temporal_variance"] > 0.0 for row in per_subject)
        ),
        "source_has_within_subject_temporal_variance": bool(
            temporally_varying_subject_count > 0
        ),
        "temporally_varying_subject_count": int(
            temporally_varying_subject_count
        ),
        "temporally_varying_subject_fraction": float(
            temporally_varying_subject_count / len(per_subject)
            if per_subject
            else 0.0
        ),
        "all_subjects_have_multiple_event_values": bool(
            per_subject
            and all(row["exact_unique_value_count"] > 1 for row in per_subject)
        ),
        "maximum_within_tick_subject_variance": max(
            (row["subject_variance"] for row in per_tick), default=0.0
        ),
        "minimum_within_tick_subject_variance": min(
            (row["subject_variance"] for row in per_tick), default=0.0
        ),
        "minimum_within_subject_temporal_variance": min(
            (row["temporal_variance"] for row in per_subject), default=0.0
        ),
        "matrix_signature": matrix_signature,
    }


def _geometry_summary(study: dict[str, Any]) -> dict[str, Any]:
    geometry = [_source_geometry(record) for record in study["seeds"]]
    specificity = [_specificity(record) for record in study["seeds"]]
    signatures = {item["matrix_signature"] for item in specificity}
    return {
        "association_visible_ports": [29, 30, 31],
        "exact_unique_visible_token_count_per_source": [
            int(item["exact_unique_visible_token_count"]) for item in geometry
        ],
        "centered_covariance_rank_per_source": [
            int(item["centered_covariance"]["numerical_rank"]) for item in geometry
        ],
        "uncentered_second_moment_rank_per_source": [
            int(item["uncentered_second_moment"]["numerical_rank"])
            for item in geometry
        ],
        "all_pairwise_score_statistics_per_source": [
            item["score_separability"]["all_pairwise_normalized_dot_scores"]
            for item in geometry
        ],
        "best_minus_second_score_spread_per_source": [
            item["score_separability"]["best_minus_second_score_spread"]
            for item in geometry
        ],
        "all_eligible_scores_identical_per_source": [
            bool(item["score_separability"]["all_eligible_scores_identical"])
            for item in geometry
        ],
        "specificity_per_source": specificity,
        "all_sources_have_within_tick_subject_variance": all(
            item["all_ticks_have_subject_variance"] for item in specificity
        ),
        "all_sources_have_within_subject_temporal_variance": all(
            item["source_has_within_subject_temporal_variance"]
            for item in specificity
        ),
        "total_temporally_varying_subject_count": int(
            sum(item["temporally_varying_subject_count"] for item in specificity)
        ),
        "total_subject_count": int(
            sum(len(item["per_subject"]) for item in specificity)
        ),
        "minimum_temporally_varying_subject_fraction": min(
            (
                item["temporally_varying_subject_fraction"]
                for item in specificity
            ),
            default=0.0,
        ),
        "all_sources_have_multiple_values_on_both_axes": all(
            item["all_ticks_have_multiple_subject_values"]
            and item["all_subjects_have_multiple_event_values"]
            for item in specificity
        ),
        "all_sources_share_identical_subject_event_matrix": len(signatures) == 1,
        "per_source": geometry,
    }


def assess_stage3c21_subject_event_readout(
    constant_study: dict[str, Any],
    constant_component: dict[str, Any],
    constant_diagnostics: dict[str, Any],
    uncertainty_study: dict[str, Any],
    uncertainty_component: dict[str, Any],
    uncertainty_diagnostics: dict[str, Any],
) -> dict[str, Any]:
    _validate_study(constant_study, input_port=0)
    _validate_study(uncertainty_study, input_port=11)
    _validate_report_set(
        constant_study, constant_component, constant_diagnostics, label="constant"
    )
    _validate_report_set(
        uncertainty_study,
        uncertainty_component,
        uncertainty_diagnostics,
        label="uncertainty",
    )
    if _factor_signature(constant_study) != _factor_signature(uncertainty_study):
        raise ValueError("Stage-3C-21 comparison changed another study factor")
    if _normalized_profile(constant_study["bootstrap_profile"]) != _normalized_profile(
        uncertainty_study["bootstrap_profile"]
    ):
        raise ValueError("Stage-3C-21 profiles differ beyond the input readout")

    left_sources = _source_records(constant_study)
    right_sources = _source_records(uncertainty_study)
    if set(left_sources) != set(right_sources):
        raise ValueError("Stage-3C-21 arms use different source panels")

    per_source: list[dict[str, Any]] = []
    checks = {
        "pre_bootstrap_state_hashes_equal": True,
        "pre_bootstrap_config_hashes_equal": True,
        "bootstrap_subject_selection_equal": True,
        "read_only_control_objective_behavior_equal": True,
        "tokens_equal_except_authorized_port29_input_change": True,
    }
    for seed in sorted(left_sources):
        left = left_sources[seed]
        right = right_sources[seed]
        same_state = (
            left["pre_bootstrap_checkpoint_state_sha256"]
            == right["pre_bootstrap_checkpoint_state_sha256"]
        )
        same_config = (
            left["pre_bootstrap_checkpoint_config_sha256"]
            == right["pre_bootstrap_checkpoint_config_sha256"]
        )
        same_subjects = (
            left["bootstrap_lineage"]["primed_tick"]
            == right["bootstrap_lineage"]["primed_tick"]
            and left["bootstrap_lineage"]["primed_subject_ids"]
            == right["bootstrap_lineage"]["primed_subject_ids"]
        )
        control = _compare_control_behavior(
            left["read_only_control_checkpoint"],
            right["read_only_control_checkpoint"],
        )
        objective_equal = bool(
            control["event_keys_equal"]
            and set(control["mismatched_array_event_counts"]) <= {"thought_token"}
        )
        token = _compare_authorized_port29(
            left["read_only_control_checkpoint"],
            right["read_only_control_checkpoint"],
        )
        checks["pre_bootstrap_state_hashes_equal"] &= bool(same_state)
        checks["pre_bootstrap_config_hashes_equal"] &= bool(same_config)
        checks["bootstrap_subject_selection_equal"] &= bool(same_subjects)
        checks["read_only_control_objective_behavior_equal"] &= objective_equal
        checks["tokens_equal_except_authorized_port29_input_change"] &= bool(
            token["tokens_equal_except_authorized_port29_input_change"]
        )
        per_source.append(
            {
                "seed": int(seed),
                "pre_bootstrap_state_hash_equal": bool(same_state),
                "pre_bootstrap_config_hash_equal": bool(same_config),
                "bootstrap_subject_selection_equal": bool(same_subjects),
                "read_only_control_behavior": control,
                "read_only_control_objective_behavior_equal": objective_equal,
                "authorized_port29_comparison": token,
            }
        )
    if not all(checks.values()):
        raise ValueError("Stage-3C-21 isolation or read-only invariance check failed")

    constant_geometry = _geometry_summary(constant_study)
    uncertainty_geometry = _geometry_summary(uncertainty_study)
    source_count = len(per_source)
    if constant_geometry["centered_covariance_rank_per_source"] != [0] * source_count:
        raise ValueError("Stage-3C-21 constant readout did not reproduce rank zero")
    if not all(
        rank >= 1 for rank in uncertainty_geometry["centered_covariance_rank_per_source"]
    ):
        raise ValueError("Stage-3C-21 uncertainty readout did not create variance")
    if not uncertainty_geometry["all_sources_have_within_tick_subject_variance"]:
        raise ValueError("Stage-3C-21 uncertainty readout lacks subject variance")
    if not uncertainty_geometry["all_sources_have_within_subject_temporal_variance"]:
        raise ValueError("Stage-3C-21 uncertainty readout lacks event-time variance")
    if uncertainty_geometry["all_sources_share_identical_subject_event_matrix"]:
        raise ValueError("Stage-3C-21 uncertainty readout remained source-global")
    if any(uncertainty_geometry["all_eligible_scores_identical_per_source"]):
        raise ValueError("Stage-3C-21 uncertainty readout did not separate scores")

    constant_association = _aggregate_association(constant_study)
    uncertainty_association = _aggregate_association(uncertainty_study)
    constant_arm = {
        **_arm_summary(constant_study, constant_component, constant_diagnostics),
        "stage_event_totals": _stage_totals(constant_diagnostics),
        "association_allocation": constant_association,
        "token_geometry": constant_geometry,
    }
    uncertainty_arm = {
        **_arm_summary(
            uncertainty_study, uncertainty_component, uncertainty_diagnostics
        ),
        "stage_event_totals": _stage_totals(uncertainty_diagnostics),
        "association_allocation": uncertainty_association,
        "token_geometry": uncertainty_geometry,
    }

    payload = {
        "schema": STAGE3C21_SUBJECT_EVENT_READOUT_SCHEMA,
        "producer_version": __version__,
        "constant_study_sha256": constant_study["study_sha256"],
        "uncertainty_study_sha256": uncertainty_study["study_sha256"],
        "single_changed_experimental_factor": (
            "readout-only node-8 objective input: constant-one port 0 -> "
            "uncertainty-mean port 11"
        ),
        "unchanged_factor_signature": _factor_signature(constant_study),
        "isolation_contract": {
            **checks,
            "bootstrap_profiles_differ_only_in_readout_input_port": True,
            "same_readout_node_trace_port_and_gate": True,
            "same_action_outputs": True,
            "same_similarity_threshold_delay_bounds_candidate_limit_and_tie_break": True,
            "same_edge_forward_gate_target_and_carrier": True,
            "same_delta_exposure_rollback_and_evaluation_contract": True,
            "highest_independent_replicate": "independent-pre-bootstrap-source-checkpoint",
            "tokens_windows_or_subjects_are_independent_replicates": False,
        },
        "constant_readout": constant_arm,
        "uncertainty_readout": uncertainty_arm,
        "comparison": {
            "change_in_assigned_associations": int(
                uncertainty_association["assigned_association_count"]
                - constant_association["assigned_association_count"]
            ),
            "change_in_modulation_proposals": int(
                uncertainty_arm["stage_event_totals"]["modulation_proposal_count"]
                - constant_arm["stage_event_totals"]["modulation_proposal_count"]
            ),
            "change_in_live_commits": int(
                uncertainty_arm["live_commits"] - constant_arm["live_commits"]
            ),
            "change_in_completed_paired_windows": int(
                uncertainty_arm["completed_paired_windows"]
                - constant_arm["completed_paired_windows"]
            ),
            "change_in_discrete_action_difference_events": int(
                uncertainty_arm["discrete_action_difference_events"]
                - constant_arm["discrete_action_difference_events"]
            ),
            "change_in_sources_with_objective_event_divergence": int(
                uncertainty_arm["sources_with_objective_event_divergence"]
                - constant_arm["sources_with_objective_event_divergence"]
            ),
            "change_in_stable_objective_coordinate_count": int(
                uncertainty_arm["stable_objective_coordinate_count"]
                - constant_arm["stable_objective_coordinate_count"]
            ),
        },
        "per_source": per_source,
        "diagnostic_interpretation": {
            "objective_input_readout_creates_subject_specific_geometry": True,
            "objective_input_readout_creates_within_subject_event_time_variation": True,
            "objective_input_readout_creates_source_specific_geometry": True,
            "objective_input_readout_creates_nontrivial_score_spread": True,
            "uncertainty_sign_or_magnitude_has_fixed_value_semantics": False,
            "readout_proves_causal_credit": False,
            "readout_proves_learning": False,
            "next_authorized_step": (
                "Hold the subject/event-specific readout, similarity, candidate limit, "
                "update scale and retention fixed; diagnose whether selected historical "
                "events are more diverse rather than merely differently weighted before "
                "changing addressing or enabling permanent retention."
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
        description="Assess Stage-3C-21 subject/event-specific visible readout."
    )
    for prefix in ("constant", "uncertainty"):
        parser.add_argument(f"--{prefix}-study-report", required=True)
        parser.add_argument(f"--{prefix}-component", required=True)
        parser.add_argument(f"--{prefix}-diagnostics", required=True)
    parser.add_argument("--output", required=True)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    result = assess_stage3c21_subject_event_readout(
        _load_json(args.constant_study_report),
        _load_json(args.constant_component),
        _load_json(args.constant_diagnostics),
        _load_json(args.uncertainty_study_report),
        _load_json(args.uncertainty_component),
        _load_json(args.uncertainty_diagnostics),
    )
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result["diagnostic_interpretation"], ensure_ascii=False))


if __name__ == "__main__":
    main()


__all__ = [
    "STAGE3C21_SUBJECT_EVENT_READOUT_SCHEMA",
    "assess_stage3c21_subject_event_readout",
]
