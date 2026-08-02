"""Stage 3C-16 fixed-bootstrap edge eligibility-carrier reachability audit.

Both study arms route the same one-hot modulation coordinate to
``edge_forward_gate``.  The only bootstrap intervention is whether edge 0 owns
one bounded local eligibility carrier.  The baseline therefore establishes the
unreachable funnel, while the alternative establishes whether the same family
can bind, commit, roll back and produce score-free paired evidence once that
single carrier is exposed.

The audit does not assign value to the edge family, retain a parameter, alter
association/addressing, or treat windows as independent source replicates.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
import json
from pathlib import Path
from typing import Any

from .. import __version__
from .subject_vm_stage3c13_exposure_adequacy import (
    _canonical_sha256,
    _compare_control_behavior,
    _diagnostics_by_seed,
    _load_json,
    _source_records,
)

STAGE3C16_EDGE_CARRIER_REACHABILITY_SCHEMA = (
    "se-subject-vm-stage3c16-edge-carrier-reachability-assessment-v1"
)


def _validate_study(study: dict[str, Any], *, carrier_enabled: bool) -> None:
    if study.get("schema") != "se-subject-vm-short-paired-study-v1":
        raise ValueError("Stage-3C-16 requires short paired study reports")
    parameters = study.get("parameters", {})
    if parameters.get("bootstrap_target_family") != "edge_forward_gate":
        raise ValueError("Stage-3C-16 requires edge_forward_gate in both arms")
    if bool(parameters.get("bootstrap_edge_carrier_enabled")) != carrier_enabled:
        raise ValueError("Stage-3C-16 carrier parameter does not match arm")
    profile = study.get("bootstrap_profile", {})
    shaping = profile.get("eligibility_carrier_shaping", {})
    if bool(shaping.get("edge_0_local_carrier_enabled")) != carrier_enabled:
        raise ValueError("Stage-3C-16 carrier profile does not match arm")
    target = profile.get("target_family_shaping", {})
    if target.get("family") != "edge_forward_gate" or int(target.get("token_port", -1)) != 27:
        raise ValueError("Stage-3C-16 requires token port 27 edge-forward routing")
    if bool(study.get("permanent_parameter_retention_authorized")):
        raise ValueError("Stage-3C-16 cannot use permanent parameter retention")
    if bool(study.get("fixed_bootstrap_is_evolved_result")):
        raise ValueError("Stage-3C-16 requires an explicit fixed bootstrap")
    if len(study.get("seeds", ())) < 3:
        raise ValueError("Stage-3C-16 requires at least three independent sources")


def _factor_signature(study: dict[str, Any]) -> dict[str, Any]:
    parameters = dict(study["parameters"])
    parameters.pop("bootstrap_edge_carrier_enabled", None)
    return {
        "project_config_file_sha256": study["project_config_file_sha256"],
        "parameters_except_edge_carrier": parameters,
        "population": study["population"],
        "resolved_backend": study["resolved_backend"],
        "temporary_exposure_contract": study["temporary_exposure_contract"],
        "fixed_bootstrap_is_evolved_result": study["fixed_bootstrap_is_evolved_result"],
        "universal_attention_claim": study["universal_attention_claim"],
        "permanent_parameter_retention_authorized": study[
            "permanent_parameter_retention_authorized"
        ],
    }


def _normalized_profile(profile: dict[str, Any]) -> dict[str, Any]:
    payload = deepcopy(profile)
    payload.pop("profile_sha256", None)
    carrier = payload["eligibility_carrier_shaping"]
    carrier["edge_0_local_carrier_enabled"] = "<edge-carrier-enabled>"
    edge0 = next(item for item in payload["edges"] if int(item["index"]) == 0)
    edge0["local_eligibility"] = "<edge-carrier-enabled>"
    edge0["eligibility_gate"] = "<edge-carrier-gate>"
    return payload


def _control_upstream_signature(source: dict[str, Any]) -> dict[str, Any]:
    funnel = source["read_only_control"]["funnel"]
    association = source["read_only_control"]["association_and_eligibility"]
    totals = funnel["stage_event_totals"]
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
        "token_event_count": totals["token_event_count"],
        "association_candidate_count": totals["association_candidate_count"],
        "modulation_proposal_count": totals["modulation_proposal_count"],
        "association_delay_ticks": association["association_delay_ticks"],
        "token_similarity": association["token_similarity"],
        "historical_event_reuse": association["historical_event_reuse"],
    }


def _arm_summary(
    study: dict[str, Any], diagnostics: dict[str, Any], component: dict[str, Any] | None
) -> dict[str, Any]:
    per_source = diagnostics["per_source"]
    stage_totals = {
        key: sum(
            int(item["guarded_live"]["funnel"]["stage_event_totals"].get(key, 0))
            for item in per_source
        )
        for key in (
            "token_event_count",
            "association_candidate_count",
            "modulation_proposal_count",
            "target_binding_event_count",
            "safe_update_event_count",
            "shadow_transaction_count",
            "guarded_live_commit_count",
            "completed_evaluation_window_count",
        )
    }
    subjects = {
        key: sum(int(item["guarded_live"]["funnel"].get(key, 0)) for item in per_source)
        for key in (
            "subjects_with_tokens",
            "subjects_with_association_candidate",
            "subjects_with_modulation_proposal",
            "subjects_with_target_binding",
            "subjects_with_safe_update",
            "subjects_with_shadow_transaction",
            "subjects_with_live_or_control_admission",
            "subjects_with_completed_window",
        )
    }
    rejection = {}
    for item in per_source:
        for key, value in item["guarded_live"]["funnel"][
            "canonical_rejection_categories"
        ].items():
            rejection[key] = rejection.get(key, 0) + int(value)
    aggregate = diagnostics["aggregate"]
    stable = (
        len(component["coordinates_with_descriptive_sign_and_interval_stability"])
        if component is not None
        else None
    )
    return {
        "engineering_summary": study["engineering_summary"],
        "stage_event_totals": stage_totals,
        "subject_stage_coverage_sum_across_sources": subjects,
        "canonical_rejection_totals": dict(sorted(rejection.items())),
        "parameter_family_proposal_counts": aggregate[
            "parameter_family_proposal_counts"
        ],
        "parameter_family_commit_counts": aggregate[
            "parameter_family_commit_counts"
        ],
        "action_potential_difference_events": int(
            aggregate["action_potential_difference_events"]
        ),
        "sampled_probability_difference_events": int(
            aggregate["sampled_probability_difference_events"]
        ),
        "discrete_action_difference_events": int(
            aggregate["discrete_action_difference_events"]
        ),
        "sources_with_discrete_action_divergence": int(
            aggregate["sources_with_discrete_action_divergence"]
        ),
        "sources_with_objective_event_divergence": int(
            aggregate["sources_with_objective_event_divergence"]
        ),
        "stable_objective_coordinate_count": stable,
    }


def assess_stage3c16_edge_carrier_reachability(
    carrier_off_study: dict[str, Any],
    carrier_off_diagnostics: dict[str, Any],
    carrier_on_study: dict[str, Any],
    carrier_on_diagnostics: dict[str, Any],
    carrier_on_component: dict[str, Any],
) -> dict[str, Any]:
    """Assess one fixed edge carrier without changing the target family."""
    _validate_study(carrier_off_study, carrier_enabled=False)
    _validate_study(carrier_on_study, carrier_enabled=True)
    if _factor_signature(carrier_off_study) != _factor_signature(carrier_on_study):
        raise ValueError("edge carrier comparison changed another study factor")
    if _normalized_profile(carrier_off_study["bootstrap_profile"]) != _normalized_profile(
        carrier_on_study["bootstrap_profile"]
    ):
        raise ValueError("bootstrap profiles differ beyond edge carrier shaping")
    if carrier_on_component.get("schema") != "se-subject-vm-component-reproducibility-assessment-v1":
        raise ValueError("carrier-on arm requires Stage-3C-8 component assessment")
    if not bool(
        carrier_on_study["engineering_summary"]["stage3c7_engineering_screen_passed"]
    ):
        raise ValueError("carrier-on arm must pass Stage-3C-7")

    off_sources = _source_records(carrier_off_study)
    on_sources = _source_records(carrier_on_study)
    off_diag = _diagnostics_by_seed(carrier_off_diagnostics)
    on_diag = _diagnostics_by_seed(carrier_on_diagnostics)
    if not (set(off_sources) == set(on_sources) == set(off_diag) == set(on_diag)):
        raise ValueError("edge carrier arms use different source panels")

    pre_state_equal = True
    pre_config_equal = True
    subject_selection_equal = True
    control_behavior_equal = True
    upstream_equal = True
    per_source: list[dict[str, Any]] = []
    for seed in sorted(off_sources):
        left = off_sources[seed]
        right = on_sources[seed]
        state_equal = bool(
            left["pre_bootstrap_checkpoint_state_sha256"]
            == right["pre_bootstrap_checkpoint_state_sha256"]
        )
        config_equal = bool(
            left["pre_bootstrap_checkpoint_config_sha256"]
            == right["pre_bootstrap_checkpoint_config_sha256"]
        )
        subjects_equal = bool(
            left["bootstrap_lineage"]["primed_subject_ids"]
            == right["bootstrap_lineage"]["primed_subject_ids"]
            and left["bootstrap_lineage"]["primed_tick"]
            == right["bootstrap_lineage"]["primed_tick"]
        )
        control = _compare_control_behavior(
            left["read_only_control_checkpoint"], right["read_only_control_checkpoint"]
        )
        upstream = _control_upstream_signature(off_diag[seed]) == _control_upstream_signature(on_diag[seed])
        pre_state_equal &= state_equal
        pre_config_equal &= config_equal
        subject_selection_equal &= subjects_equal
        control_behavior_equal &= bool(control["control_behavior_semantically_identical"])
        upstream_equal &= upstream
        off_funnel = off_diag[seed]["guarded_live"]["funnel"]
        on_funnel = on_diag[seed]["guarded_live"]["funnel"]
        per_source.append(
            {
                "seed": int(seed),
                "pre_bootstrap_state_hash_equal": state_equal,
                "pre_bootstrap_config_hash_equal": config_equal,
                "bootstrap_subject_selection_equal": subjects_equal,
                "read_only_control_behavior": control,
                "read_only_control_token_association_modulation_upstream_equal": upstream,
                "carrier_off_target_binding_events": int(
                    off_funnel["stage_event_totals"]["target_binding_event_count"]
                ),
                "carrier_on_target_binding_events": int(
                    on_funnel["stage_event_totals"]["target_binding_event_count"]
                ),
                "carrier_off_completed_windows": int(
                    off_funnel["stage_event_totals"]["completed_evaluation_window_count"]
                ),
                "carrier_on_completed_windows": int(
                    on_funnel["stage_event_totals"]["completed_evaluation_window_count"]
                ),
            }
        )

    if not all(
        (pre_state_equal, pre_config_equal, subject_selection_equal, control_behavior_equal, upstream_equal)
    ):
        raise ValueError("edge carrier comparison failed isolation contract")

    off = _arm_summary(carrier_off_study, carrier_off_diagnostics, None)
    on = _arm_summary(carrier_on_study, carrier_on_diagnostics, carrier_on_component)
    off_bind = off["stage_event_totals"]["target_binding_event_count"]
    off_commit = off["stage_event_totals"]["guarded_live_commit_count"]
    on_bind = on["stage_event_totals"]["target_binding_event_count"]
    on_commit = on["stage_event_totals"]["guarded_live_commit_count"]
    if off_bind != 0 or off_commit != 0:
        raise ValueError("carrier-off arm unexpectedly reached edge updates")
    if on_bind <= 0 or on_commit <= 0:
        raise ValueError("carrier-on arm did not reach edge updates")

    payload = {
        "schema": STAGE3C16_EDGE_CARRIER_REACHABILITY_SCHEMA,
        "producer_version": __version__,
        "carrier_off_study_sha256": carrier_off_study["study_sha256"],
        "carrier_on_study_sha256": carrier_on_study["study_sha256"],
        "single_changed_experimental_factor": (
            "fixed bootstrap edge-0 local eligibility carrier: disabled -> enabled"
        ),
        "unchanged_factor_signature": _factor_signature(carrier_off_study),
        "isolation_contract": {
            "independent_source_count": len(per_source),
            "seeds": sorted(off_sources),
            "pre_bootstrap_state_hashes_equal": pre_state_equal,
            "pre_bootstrap_config_hashes_equal": pre_config_equal,
            "bootstrap_subject_selection_equal": subject_selection_equal,
            "read_only_control_behavior_equal": control_behavior_equal,
            "read_only_control_token_association_modulation_upstream_equal": upstream_equal,
            "same_target_family": "edge_forward_gate",
            "same_target_token_port": 27,
            "only_edge_carrier_flag_and_gate_changed": True,
            "highest_independent_replicate": "independent-source-checkpoint",
            "windows_are_independent_replicates": False,
        },
        "carrier_off": off,
        "carrier_on": on,
        "comparison": {
            "change_in_target_binding_events": int(on_bind - off_bind),
            "change_in_live_commits": int(on_commit - off_commit),
            "change_in_completed_paired_windows": int(
                on["stage_event_totals"]["completed_evaluation_window_count"]
                - off["stage_event_totals"]["completed_evaluation_window_count"]
            ),
            "change_in_discrete_action_difference_events": int(
                on["discrete_action_difference_events"]
                - off["discrete_action_difference_events"]
            ),
            "change_in_sources_with_objective_event_divergence": int(
                on["sources_with_objective_event_divergence"]
                - off["sources_with_objective_event_divergence"]
            ),
        },
        "per_source": per_source,
        "diagnostic_interpretation": {
            "edge_forward_gate_mechanically_sensitive_in_stage3c15": True,
            "carrier_is_necessary_for_current_exact_target_binding": True,
            "carrier_enabled_arm_reached_guarded_live_write": True,
            "carrier_off_zero_windows_is_an_expected_unreachable_baseline": True,
            "carrier_off_is_a_stage3c8_scientific_replicate": False,
            "carrier_on_stable_objective_direction_observed": bool(
                on["stable_objective_coordinate_count"]
            ),
            "eligibility_carrier_is_value_semantics": False,
            "eligibility_carrier_proves_credit_quality": False,
            "eligibility_carrier_proves_learning": False,
            "next_authorized_step": (
                "retain automatic rollback and the frozen panel; use the carrier-on "
                "arm only as a newly reachable engineering baseline before any "
                "separate comparison of addressing or multi-family allocation"
            ),
        },
        "fixed_cognition_engineering_shaping_aid": True,
        "evolved_topology": False,
        "universal_attention_claim": False,
        "universal_scalar_objective": False,
        "automatic_keep_or_revert_decision": False,
        "permanent_parameter_retention_authorized": False,
        "causal_effect_authorized": False,
        "learning_claim_authorized": False,
        "subjecthood_claim_authorized": False,
    }
    payload["assessment_sha256"] = _canonical_sha256(payload)
    return payload


def assess_from_paths(
    *, carrier_off_study_report: str | Path, carrier_on_study_report: str | Path
) -> dict[str, Any]:
    off_study = _load_json(carrier_off_study_report)
    on_study = _load_json(carrier_on_study_report)
    off_diagnostics = _load_json(off_study["stage3c10_diagnostics"])
    on_diagnostics = _load_json(on_study["stage3c10_diagnostics"])
    component_path = on_study.get("component_reproducibility")
    if not component_path:
        raise ValueError("carrier-on study lacks Stage-3C-8 component report")
    return assess_stage3c16_edge_carrier_reachability(
        off_study,
        off_diagnostics,
        on_study,
        on_diagnostics,
        _load_json(component_path),
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Assess fixed edge-forward eligibility-carrier reachability."
    )
    parser.add_argument("--carrier-off-study-report", required=True)
    parser.add_argument("--carrier-on-study-report", required=True)
    parser.add_argument("--output", required=True)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    result = assess_from_paths(
        carrier_off_study_report=args.carrier_off_study_report,
        carrier_on_study_report=args.carrier_on_study_report,
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
    "STAGE3C16_EDGE_CARRIER_REACHABILITY_SCHEMA",
    "assess_from_paths",
    "assess_stage3c16_edge_carrier_reachability",
]
