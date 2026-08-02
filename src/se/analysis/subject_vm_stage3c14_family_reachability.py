"""Stage 3C-14 fixed-bootstrap parameter-family reachability audit.

The comparison changes only the token coordinate used by the fixed bootstrap to
route a one-hot modulation proposal from ``node_bias`` to ``node_output_gate``.
Both arms use the same pre-bootstrap source states, selected subjects, graph
size, association controls, bounded delta, exposure duration, branch horizon,
and automatic rollback.  No parameter is retained and no objective coordinate
is assigned value semantics.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np

from .. import __version__
from ..checkpointing import read_checkpoint_bundle
from .subject_vm_stage3c13_exposure_adequacy import (
    _arm_summary,
    _canonical_sha256,
    _diagnostics_by_seed,
    _load_json,
    _source_records,
    _validate_report_set,
)

STAGE3C14_FAMILY_REACHABILITY_SCHEMA = (
    "se-subject-vm-stage3c14-family-reachability-assessment-v1"
)
_ALLOWED_FAMILIES = {"node_bias": 23, "node_output_gate": 25}


def _factor_signature(study: dict[str, Any]) -> dict[str, Any]:
    parameters = dict(study["parameters"])
    parameters.pop("bootstrap_target_family", None)
    return {
        "project_config_file_sha256": study["project_config_file_sha256"],
        "parameters_except_target_family": parameters,
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


def _target_family(study: dict[str, Any]) -> str:
    parameter = str(study["parameters"].get("bootstrap_target_family", ""))
    profile = study["bootstrap_profile"]["target_family_shaping"]
    family = str(profile["family"])
    port = int(profile["token_port"])
    if parameter != family or family not in _ALLOWED_FAMILIES:
        raise ValueError("study target-family parameter/profile mismatch")
    if port != _ALLOWED_FAMILIES[family]:
        raise ValueError("study target-family token port mismatch")
    return family


def _normalized_profile(profile: dict[str, Any]) -> dict[str, Any]:
    payload = deepcopy(profile)
    payload.pop("profile_sha256", None)
    family = str(payload["target_family_shaping"]["family"])
    port = int(payload["target_family_shaping"]["token_port"])
    if family not in _ALLOWED_FAMILIES or port != _ALLOWED_FAMILIES[family]:
        raise ValueError("unsupported bootstrap target-family profile")
    payload["target_family_shaping"]["family"] = "<target-family>"
    payload["target_family_shaping"]["token_port"] = "<target-port>"
    nodes = payload.get("nodes", [])
    node0 = next(item for item in nodes if int(item["index"]) == 0)
    node7 = next(item for item in nodes if int(item["index"]) == 7)
    node0["target_family"] = "<target-family-via-target-port>"
    node7["trace_port"] = "<target-port>"
    return payload




def _event_index(trace: dict[str, np.ndarray]) -> dict[tuple[int, int], tuple[int, int]]:
    result: dict[tuple[int, int], tuple[int, int]] = {}
    for row, slot in zip(*np.nonzero(trace["event_valid"]), strict=True):
        key = (int(trace["subject_id"][row, slot]), int(trace["event_tick"][row, slot]))
        if key in result:
            raise ValueError(f"duplicate subject/tick trace event: {key}")
        result[key] = (int(row), int(slot))
    return result


def _compare_read_only_control(
    baseline_checkpoint: str | Path, alternative_checkpoint: str | Path
) -> dict[str, Any]:
    baseline_meta, baseline_state = read_checkpoint_bundle(baseline_checkpoint)
    alternative_meta, alternative_state = read_checkpoint_bundle(alternative_checkpoint)
    left_trace = baseline_state["simulation"]["subject_vm"]["trace_storage"]["arrays"]
    right_trace = alternative_state["simulation"]["subject_vm"]["trace_storage"]["arrays"]
    left_index = _event_index(left_trace)
    right_index = _event_index(right_trace)
    keys_equal = set(left_index) == set(right_index)
    arrays = (
        "action_potentials", "sampled_probability", "action_id", "success",
        "objective_delta", "resolution_resource_delta",
        "resolution_internal_resource_delta", "resolution_energy_cost",
    )
    mismatched_events = 0
    mismatched_arrays: dict[str, int] = {}
    token_routing_mismatch = 0
    if keys_equal:
        for key in sorted(left_index):
            left = left_index[key]
            right = right_index[key]
            event_mismatch = False
            for name in arrays:
                if not np.array_equal(left_trace[name][left], right_trace[name][right]):
                    mismatched_arrays[name] = mismatched_arrays.get(name, 0) + 1
                    event_mismatch = True
            left_token = np.asarray(left_trace["thought_token"][left])
            right_token = np.asarray(right_trace["thought_token"][right])
            mask = np.ones(left_token.shape, dtype=bool)
            mask[[23, 25]] = False
            routing_ok = bool(
                np.array_equal(left_token[mask], right_token[mask])
                and left_token[23] == right_token[25]
                and left_token[25] == 0.0
                and right_token[23] == 0.0
            )
            if not routing_ok:
                token_routing_mismatch += 1
                event_mismatch = True
            mismatched_events += int(event_mismatch)
    return {
        "baseline_checkpoint_tick": int(baseline_meta["tick"]),
        "alternative_checkpoint_tick": int(alternative_meta["tick"]),
        "event_keys_equal": keys_equal,
        "behavior_arrays_compared": list(arrays),
        "mismatched_event_count": int(mismatched_events),
        "mismatched_array_event_counts": dict(sorted(mismatched_arrays.items())),
        "target_token_routing_mismatch_count": int(token_routing_mismatch),
        "control_behavior_semantically_identical_except_authorized_token_route": bool(
            keys_equal and mismatched_events == 0
        ),
    }

def _control_upstream_signature(source: dict[str, Any]) -> dict[str, Any]:
    control = source["read_only_control"]
    funnel = control["funnel"]
    association = control["association_and_eligibility"]
    return {
        "bootstrap_subject_count": funnel["bootstrap_subject_count"],
        "subjects_with_graph_expression": funnel["subjects_with_graph_expression"],
        "subjects_with_tokens": funnel["subjects_with_tokens"],
        "subjects_with_association_candidate": funnel[
            "subjects_with_association_candidate"
        ],
        "subjects_with_modulation_proposal": funnel[
            "subjects_with_modulation_proposal"
        ],
        "subjects_with_target_binding": funnel["subjects_with_target_binding"],
        "subjects_with_safe_update": funnel["subjects_with_safe_update"],
        "association_delay_ticks": association["association_delay_ticks"],
        "token_similarity": association["token_similarity"],
        "historical_event_reuse": association["historical_event_reuse"],
        "eligibility_age_at_binding": association["eligibility_age_at_binding"],
        "eligibility_value_abs_at_binding": association[
            "eligibility_value_abs_at_binding"
        ],
    }


def _family_counts(diagnostics: dict[str, Any], family: str) -> dict[str, int]:
    label = family.replace("_", "-")
    aggregate = diagnostics["aggregate"]
    proposals = aggregate["parameter_family_proposal_counts"]
    commits = aggregate["parameter_family_commit_counts"]
    return {
        "proposal_count": int(proposals.get(label, 0)),
        "commit_count": int(commits.get(label, 0)),
    }


def assess_stage3c14_family_reachability(
    baseline_study: dict[str, Any],
    baseline_component: dict[str, Any],
    baseline_diagnostics: dict[str, Any],
    alternative_study: dict[str, Any],
    alternative_component: dict[str, Any],
    alternative_diagnostics: dict[str, Any],
) -> dict[str, Any]:
    """Compare node-bias and node-output-gate fixed-bootstrap routing."""
    _validate_report_set(
        baseline_study, baseline_component, baseline_diagnostics, label="baseline"
    )
    _validate_report_set(
        alternative_study,
        alternative_component,
        alternative_diagnostics,
        label="alternative",
    )
    if _factor_signature(baseline_study) != _factor_signature(alternative_study):
        raise ValueError("family reachability comparison changed another study factor")

    baseline_family = _target_family(baseline_study)
    alternative_family = _target_family(alternative_study)
    if (baseline_family, alternative_family) != ("node_bias", "node_output_gate"):
        raise ValueError("Stage-3C-14 requires node_bias -> node_output_gate")
    if _normalized_profile(baseline_study["bootstrap_profile"]) != _normalized_profile(
        alternative_study["bootstrap_profile"]
    ):
        raise ValueError("bootstrap profiles differ beyond target-family routing")

    baseline_sources = _source_records(baseline_study)
    alternative_sources = _source_records(alternative_study)
    baseline_diag = _diagnostics_by_seed(baseline_diagnostics)
    alternative_diag = _diagnostics_by_seed(alternative_diagnostics)
    if not (
        set(baseline_sources)
        == set(alternative_sources)
        == set(baseline_diag)
        == set(alternative_diag)
    ):
        raise ValueError("family reachability arms use different source panels")

    per_source: list[dict[str, Any]] = []
    pre_state_equal = True
    pre_config_equal = True
    subject_selection_equal = True
    control_behavior_equal = True
    upstream_equal = True
    for seed in sorted(baseline_sources):
        left = baseline_sources[seed]
        right = alternative_sources[seed]
        state_equal = bool(
            left["pre_bootstrap_checkpoint_state_sha256"]
            == right["pre_bootstrap_checkpoint_state_sha256"]
        )
        config_equal = bool(
            left["pre_bootstrap_checkpoint_config_sha256"]
            == right["pre_bootstrap_checkpoint_config_sha256"]
        )
        selected_equal = bool(
            left["bootstrap_lineage"]["primed_tick"]
            == right["bootstrap_lineage"]["primed_tick"]
            and left["bootstrap_lineage"]["primed_subject_ids"]
            == right["bootstrap_lineage"]["primed_subject_ids"]
        )
        control = _compare_read_only_control(
            left["read_only_control_checkpoint"],
            right["read_only_control_checkpoint"],
        )
        upstream_left = _control_upstream_signature(baseline_diag[seed])
        upstream_right = _control_upstream_signature(alternative_diag[seed])
        source_upstream_equal = upstream_left == upstream_right
        pre_state_equal &= state_equal
        pre_config_equal &= config_equal
        subject_selection_equal &= selected_equal
        control_behavior_equal &= bool(
            control["control_behavior_semantically_identical_except_authorized_token_route"]
        )
        upstream_equal &= source_upstream_equal
        per_source.append(
            {
                "seed": seed,
                "pre_bootstrap_state_hash_equal": state_equal,
                "pre_bootstrap_config_hash_equal": config_equal,
                "bootstrap_subject_selection_equal": selected_equal,
                "post_bootstrap_source_state_hashes_differ": bool(
                    left["source_checkpoint_state_sha256"]
                    != right["source_checkpoint_state_sha256"]
                ),
                "read_only_control_behavior": control,
                "control_upstream_pipeline_equal": source_upstream_equal,
                "baseline_source_checkpoint_state_sha256": left[
                    "source_checkpoint_state_sha256"
                ],
                "alternative_source_checkpoint_state_sha256": right[
                    "source_checkpoint_state_sha256"
                ],
            }
        )

    if not all(
        (
            pre_state_equal,
            pre_config_equal,
            subject_selection_equal,
            control_behavior_equal,
            upstream_equal,
        )
    ):
        raise ValueError("Stage-3C-14 isolation or read-only invariance check failed")

    baseline_arm = _arm_summary(
        baseline_study, baseline_component, baseline_diagnostics
    )
    alternative_arm = _arm_summary(
        alternative_study, alternative_component, alternative_diagnostics
    )
    baseline_counts = _family_counts(baseline_diagnostics, baseline_family)
    alternative_counts = _family_counts(alternative_diagnostics, alternative_family)
    if baseline_counts["proposal_count"] <= 0 or baseline_counts["commit_count"] <= 0:
        raise ValueError("baseline target family was not reached")
    if alternative_counts["proposal_count"] <= 0 or alternative_counts["commit_count"] <= 0:
        raise ValueError("alternative target family was not reached")
    if baseline_diagnostics["aggregate"]["nonzero_proposal_parameter_families"] != ["node-bias"]:
        raise ValueError("baseline proposal routing is not family-exclusive")
    if alternative_diagnostics["aggregate"]["nonzero_proposal_parameter_families"] != [
        "node-output-gate"
    ]:
        raise ValueError("alternative proposal routing is not family-exclusive")

    comparison_fields = (
        "completed_paired_windows",
        "live_commits",
        "action_potential_difference_events",
        "sampled_probability_difference_events",
        "discrete_action_difference_events",
        "sources_with_discrete_action_divergence",
        "sources_with_objective_event_divergence",
        "sources_with_nonzero_completed_window_objective_vector",
        "stable_objective_coordinate_count",
    )
    comparison = {
        f"change_in_{field}": int(alternative_arm[field] - baseline_arm[field])
        for field in comparison_fields
    }
    payload = {
        "schema": STAGE3C14_FAMILY_REACHABILITY_SCHEMA,
        "producer_version": __version__,
        "baseline_study_sha256": baseline_study["study_sha256"],
        "alternative_study_sha256": alternative_study["study_sha256"],
        "single_changed_experimental_factor": (
            "fixed-bootstrap one-hot target-family routing: "
            "node_bias token port 23 -> node_output_gate token port 25"
        ),
        "unchanged_factor_signature": _factor_signature(baseline_study),
        "isolation_contract": {
            "independent_source_count": len(per_source),
            "seeds": sorted(baseline_sources),
            "pre_bootstrap_state_hashes_equal": pre_state_equal,
            "pre_bootstrap_config_hashes_equal": pre_config_equal,
            "bootstrap_subject_selection_equal": subject_selection_equal,
            "bootstrap_profiles_differ_only_in_target_family_routing": True,
            "read_only_control_behavior_equal": control_behavior_equal,
            "control_upstream_pipeline_equal": upstream_equal,
            "association_similarity_excludes_both_target_control_ports": True,
            "same_local_eligibility_carrier_class": True,
            "highest_independent_replicate": "independent-pre-bootstrap-source-checkpoint",
            "windows_are_independent_replicates": False,
        },
        "baseline": baseline_arm,
        "alternative": alternative_arm,
        "target_family_reachability": {
            "baseline_family": baseline_family,
            "baseline_token_port": _ALLOWED_FAMILIES[baseline_family],
            "baseline_counts": baseline_counts,
            "alternative_family": alternative_family,
            "alternative_token_port": _ALLOWED_FAMILIES[alternative_family],
            "alternative_counts": alternative_counts,
            "both_families_reached_and_committed": True,
        },
        "comparison": comparison,
        "per_source": per_source,
        "adequacy_interpretation": {
            "parameter_family_routing_changes_continuous_visibility": bool(
                comparison["change_in_action_potential_difference_events"] != 0
                or comparison["change_in_sampled_probability_difference_events"] != 0
            ),
            "parameter_family_routing_increases_discrete_crossings": bool(
                comparison["change_in_discrete_action_difference_events"] > 0
                or comparison["change_in_sources_with_discrete_action_divergence"] > 0
            ),
            "cross_source_objective_stability_observed": bool(
                alternative_arm["stable_objective_coordinate_count"] > 0
            ),
            "observed_result": (
                "The alternative fixed-bootstrap route reaches and commits "
                "node-output-gate updates under an otherwise isolated panel. "
                "Differences between arms describe parameter-role visibility only; "
                "they do not identify value, causal credit, learning, or a preferred family."
            ),
            "next_authorized_step": (
                "Use the audit to decide whether target-family role is a material "
                "visibility bottleneck. Do not enable permanent retention or combine "
                "family routing with delta, horizon, topology, or objective changes."
            ),
        },
        "rejected_pilot_design": {
            "comparison": "node_bias -> node_input_gate on input port 0",
            "reason": (
                "input port 0 is constant-one, so node_bias and node_input_gate "
                "changes are algebraically equivalent for the targeted node"
            ),
            "reported_as_scientific_arm": False,
        },
        "objective_coordinate_value_interpretation": None,
        "universal_scalar_objective": False,
        "automatic_keep_or_revert_decision": False,
        "permanent_parameter_retention_authorized": False,
        "causal_effect_authorized": False,
        "learning_claim_authorized": False,
        "subjecthood_claim_authorized": False,
        "universal_attention_claim": False,
    }
    payload["assessment_sha256"] = _canonical_sha256(payload)
    return payload


def assess_from_paths(
    *, baseline_study_report: str | Path, alternative_study_report: str | Path
) -> dict[str, Any]:
    baseline_study = _load_json(baseline_study_report)
    alternative_study = _load_json(alternative_study_report)

    def related(study: dict[str, Any], key: str) -> dict[str, Any]:
        value = study.get(key)
        if not value:
            raise ValueError(f"study report lacks {key}")
        return _load_json(value)

    return assess_stage3c14_family_reachability(
        baseline_study,
        related(baseline_study, "component_reproducibility"),
        related(baseline_study, "stage3c10_diagnostics"),
        alternative_study,
        related(alternative_study, "component_reproducibility"),
        related(alternative_study, "stage3c10_diagnostics"),
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Assess Stage-3C-14 fixed-bootstrap family reachability."
    )
    parser.add_argument("--baseline-study-report", required=True)
    parser.add_argument("--alternative-study-report", required=True)
    parser.add_argument("--output", required=True)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    result = assess_from_paths(
        baseline_study_report=args.baseline_study_report,
        alternative_study_report=args.alternative_study_report,
    )
    path = Path(args.output)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({
        "assessment_sha256": result["assessment_sha256"],
        "comparison": result["comparison"],
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()


__all__ = [
    "STAGE3C14_FAMILY_REACHABILITY_SCHEMA",
    "assess_stage3c14_family_reachability",
    "assess_from_paths",
]
