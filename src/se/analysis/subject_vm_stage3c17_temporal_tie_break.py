"""Stage 3C-17 equal-similarity temporal tie-break audit.

The frozen carrier-on ``edge_forward_gate`` baseline is held fixed.  The only
experimental factor is how the existing normalized-dot selector resolves an
exact similarity tie: prefer the latest eligible historical token or the
oldest eligible historical token.  Candidate eligibility, similarity,
thresholds, parameter family, carrier, bounded delta, automatic rollback and
score-free evaluation remain unchanged.

This is a fixed-cognition engineering comparison.  It does not treat recency
or age as value, causal quality, utility or trust.
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
from .subject_vm_stage3c13_exposure_adequacy import (
    _canonical_sha256,
    _compare_control_behavior,
    _diagnostics_by_seed,
    _load_json,
    _source_records,
)

STAGE3C17_TEMPORAL_TIE_BREAK_SCHEMA = (
    "se-subject-vm-stage3c17-temporal-tie-break-assessment-v1"
)


def _validate_study(study: dict[str, Any], *, policy: str) -> None:
    if study.get("schema") != "se-subject-vm-short-paired-study-v1":
        raise ValueError("Stage-3C-17 requires short paired study reports")
    parameters = study.get("parameters", {})
    if parameters.get("association_tie_break") != policy:
        raise ValueError("Stage-3C-17 association tie-break does not match arm")
    if parameters.get("bootstrap_target_family") != "edge_forward_gate":
        raise ValueError("Stage-3C-17 requires edge_forward_gate")
    if not bool(parameters.get("bootstrap_edge_carrier_enabled")):
        raise ValueError("Stage-3C-17 requires the Stage-3C-16 carrier-on baseline")
    if int(parameters.get("horizon_ticks", -1)) != 8:
        raise ValueError("Stage-3C-17 requires the frozen eight-tick branch horizon")
    if int(parameters.get("rollback_after_ticks", -1)) != 3:
        raise ValueError("Stage-3C-17 requires the frozen exposure duration three")
    if len(study.get("seeds", ())) < 3:
        raise ValueError("Stage-3C-17 requires at least three independent sources")
    if not bool(study["engineering_summary"]["stage3c7_engineering_screen_passed"]):
        raise ValueError("Stage-3C-17 arms must pass Stage-3C-7")
    if bool(study.get("permanent_parameter_retention_authorized")):
        raise ValueError("Stage-3C-17 cannot use permanent parameter retention")


def _factor_signature(study: dict[str, Any]) -> dict[str, Any]:
    parameters = dict(study["parameters"])
    parameters.pop("association_tie_break", None)
    return {
        "project_config_file_sha256": study["project_config_file_sha256"],
        "parameters_except_temporal_tie_break": parameters,
        "population": study["population"],
        "resolved_backend": study["resolved_backend"],
        "temporary_exposure_contract": study["temporary_exposure_contract"],
        "bootstrap_profile_sha256": study["bootstrap_profile"]["profile_sha256"],
        "fixed_bootstrap_is_evolved_result": study[
            "fixed_bootstrap_is_evolved_result"
        ],
        "universal_attention_claim": study["universal_attention_claim"],
        "permanent_parameter_retention_authorized": study[
            "permanent_parameter_retention_authorized"
        ],
    }


def _plan_policy(source: dict[str, Any]) -> str:
    plan = _load_json(source["plan"])
    overrides = plan.get("branch_runtime_overrides")
    if overrides is None:
        return "latest"
    if set(overrides) != {"subject_vm.association.tie_break"}:
        raise ValueError("Stage-3C-17 plan contains an unauthorized runtime override")
    return str(overrides["subject_vm.association.tie_break"])


def _association_snapshot(checkpoint: str | Path) -> dict[str, Any]:
    _, state = read_checkpoint_bundle(checkpoint)
    arrays = state["simulation"]["subject_vm"]["trace_storage"]["arrays"]
    valid = np.asarray(arrays["event_valid"], dtype=bool)
    assigned = np.asarray(arrays["association_assigned"], dtype=bool)
    mask = valid & assigned
    delays = np.asarray(arrays["association_delay_ticks"], dtype=np.int64)[mask]
    similarities = np.asarray(arrays["association_similarity"], dtype=np.float64)[mask]
    event_ids = np.asarray(arrays["associated_event_id"], dtype=np.uint64)[mask]
    delay_counts = Counter(int(value) for value in delays.tolist())
    event_reuse = Counter(int(value) for value in event_ids.tolist())
    return {
        "assigned_association_count": int(delays.size),
        "delay_histogram": {
            str(key): int(value) for key, value in sorted(delay_counts.items())
        },
        "delay_minimum": int(delays.min()) if delays.size else None,
        "delay_median": float(np.median(delays)) if delays.size else None,
        "delay_maximum": int(delays.max()) if delays.size else None,
        "delay_mean": float(delays.mean()) if delays.size else None,
        "similarity_minimum": float(similarities.min()) if similarities.size else None,
        "similarity_maximum": float(similarities.max()) if similarities.size else None,
        "all_assigned_similarities_one": bool(
            similarities.size and np.allclose(similarities, 1.0, rtol=0.0, atol=1e-7)
        ),
        "unique_associated_event_count": len(event_reuse),
        "maximum_reuse_of_one_historical_event": max(event_reuse.values(), default=0),
        "historical_events_reused_more_than_once": int(
            sum(value > 1 for value in event_reuse.values())
        ),
    }


def _aggregate_association(per_source: list[dict[str, Any]]) -> dict[str, Any]:
    delay_counts: Counter[int] = Counter()
    assigned = 0
    all_one = True
    unique_counts: list[int] = []
    max_reuse: list[int] = []
    reused_counts: list[int] = []
    for item in per_source:
        snap = item["association_snapshot"]
        assigned += int(snap["assigned_association_count"])
        delay_counts.update(
            {int(key): int(value) for key, value in snap["delay_histogram"].items()}
        )
        all_one &= bool(snap["all_assigned_similarities_one"])
        unique_counts.append(int(snap["unique_associated_event_count"]))
        max_reuse.append(int(snap["maximum_reuse_of_one_historical_event"]))
        reused_counts.append(int(snap["historical_events_reused_more_than_once"]))
    weighted_delay = sum(key * value for key, value in delay_counts.items())
    return {
        "assigned_association_count": assigned,
        "delay_histogram": {
            str(key): int(value) for key, value in sorted(delay_counts.items())
        },
        "delay_mean": float(weighted_delay / assigned) if assigned else None,
        "all_assigned_similarities_one": all_one,
        "per_source_unique_associated_event_counts": unique_counts,
        "per_source_maximum_historical_event_reuse": max_reuse,
        "per_source_historical_events_reused_more_than_once": reused_counts,
    }


def _arm_summary(
    study: dict[str, Any], diagnostics: dict[str, Any], component: dict[str, Any]
) -> dict[str, Any]:
    aggregate = diagnostics["aggregate"]
    per_source = diagnostics["per_source"]
    totals = {
        key: sum(
            int(item["guarded_live"]["funnel"]["stage_event_totals"].get(key, 0))
            for item in per_source
        )
        for key in (
            "association_candidate_count",
            "modulation_proposal_count",
            "target_binding_event_count",
            "safe_update_event_count",
            "shadow_transaction_count",
            "guarded_live_commit_count",
            "completed_evaluation_window_count",
        )
    }
    rejection: Counter[str] = Counter()
    for item in per_source:
        rejection.update(
            item["guarded_live"]["funnel"]["canonical_rejection_categories"]
        )
    return {
        "engineering_summary": study["engineering_summary"],
        "stage_event_totals": totals,
        "canonical_rejection_totals": dict(
            sorted((key, int(value)) for key, value in rejection.items())
        ),
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
        "stable_objective_coordinate_count": len(
            component["coordinates_with_descriptive_sign_and_interval_stability"]
        ),
    }


def assess_stage3c17_temporal_tie_break(
    latest_study: dict[str, Any],
    latest_diagnostics: dict[str, Any],
    latest_component: dict[str, Any],
    oldest_study: dict[str, Any],
    oldest_diagnostics: dict[str, Any],
    oldest_component: dict[str, Any],
) -> dict[str, Any]:
    _validate_study(latest_study, policy="latest")
    _validate_study(oldest_study, policy="oldest")
    if _factor_signature(latest_study) != _factor_signature(oldest_study):
        raise ValueError("temporal tie-break comparison changed another study factor")

    latest_sources = _source_records(latest_study)
    oldest_sources = _source_records(oldest_study)
    latest_diag = _diagnostics_by_seed(latest_diagnostics)
    oldest_diag = _diagnostics_by_seed(oldest_diagnostics)
    if not (
        set(latest_sources)
        == set(oldest_sources)
        == set(latest_diag)
        == set(oldest_diag)
    ):
        raise ValueError("temporal tie-break arms use different source panels")

    state_equal = True
    config_equal = True
    subjects_equal = True
    control_equal = True
    per_source: list[dict[str, Any]] = []
    for seed in sorted(latest_sources):
        left = latest_sources[seed]
        right = oldest_sources[seed]
        same_state = bool(
            left["source_checkpoint_state_sha256"]
            == right["source_checkpoint_state_sha256"]
        )
        same_config = bool(
            left["pre_bootstrap_checkpoint_config_sha256"]
            == right["pre_bootstrap_checkpoint_config_sha256"]
        )
        same_subjects = bool(
            left["bootstrap_lineage"]["primed_subject_ids"]
            == right["bootstrap_lineage"]["primed_subject_ids"]
        )
        control = _compare_control_behavior(
            left["read_only_control_checkpoint"],
            right["read_only_control_checkpoint"],
        )
        if _plan_policy(left) != "latest" or _plan_policy(right) != "oldest":
            raise ValueError("temporal tie-break plan policy mismatch")
        latest_snapshot = _association_snapshot(left["read_only_control_checkpoint"])
        oldest_snapshot = _association_snapshot(right["read_only_control_checkpoint"])
        state_equal &= same_state
        config_equal &= same_config
        subjects_equal &= same_subjects
        control_equal &= bool(control["control_behavior_semantically_identical"])
        per_source.append(
            {
                "seed": int(seed),
                "source_checkpoint_state_hash_equal": same_state,
                "pre_bootstrap_config_hash_equal": same_config,
                "bootstrap_subject_selection_equal": same_subjects,
                "read_only_control_behavior": control,
                "latest": {"association_snapshot": latest_snapshot},
                "oldest": {"association_snapshot": oldest_snapshot},
            }
        )

    if not all((state_equal, config_equal, subjects_equal, control_equal)):
        raise ValueError("temporal tie-break comparison failed isolation contract")

    latest_assoc = _aggregate_association(
        [item["latest"] for item in per_source]
    )
    oldest_assoc = _aggregate_association(
        [item["oldest"] for item in per_source]
    )
    if not latest_assoc["all_assigned_similarities_one"]:
        raise ValueError("latest arm is not an exact-similarity tie panel")
    if not oldest_assoc["all_assigned_similarities_one"]:
        raise ValueError("oldest arm is not an exact-similarity tie panel")
    if set(latest_assoc["delay_histogram"]) != {"1"}:
        raise ValueError("latest arm did not reproduce delay-one concentration")
    if not any(int(key) > 1 for key in oldest_assoc["delay_histogram"]):
        raise ValueError("oldest arm did not change temporal candidate allocation")

    latest = _arm_summary(latest_study, latest_diagnostics, latest_component)
    oldest = _arm_summary(oldest_study, oldest_diagnostics, oldest_component)
    payload = {
        "schema": STAGE3C17_TEMPORAL_TIE_BREAK_SCHEMA,
        "producer_version": __version__,
        "latest_study_sha256": latest_study["study_sha256"],
        "oldest_study_sha256": oldest_study["study_sha256"],
        "single_changed_experimental_factor": (
            "equal-similarity temporal tie-break: latest eligible token -> oldest eligible token"
        ),
        "unchanged_factor_signature": _factor_signature(latest_study),
        "isolation_contract": {
            "independent_source_count": len(per_source),
            "seeds": sorted(latest_sources),
            "source_checkpoint_state_hashes_equal": state_equal,
            "pre_bootstrap_config_hashes_equal": config_equal,
            "bootstrap_subject_selection_equal": subjects_equal,
            "read_only_control_behavior_equal": control_equal,
            "same_candidate_delay_bounds": True,
            "same_normalized_dot_similarity": True,
            "same_similarity_threshold": True,
            "same_edge_forward_gate_target_and_carrier": True,
            "only_equal_similarity_time_tie_break_changed": True,
            "highest_independent_replicate": "independent-source-checkpoint",
            "windows_are_independent_replicates": False,
        },
        "latest": {**latest, "association_allocation": latest_assoc},
        "oldest": {**oldest, "association_allocation": oldest_assoc},
        "comparison": {
            "change_in_mean_association_delay": float(
                oldest_assoc["delay_mean"] - latest_assoc["delay_mean"]
            ),
            "change_in_modulation_proposals": int(
                oldest["stage_event_totals"]["modulation_proposal_count"]
                - latest["stage_event_totals"]["modulation_proposal_count"]
            ),
            "change_in_live_commits": int(
                oldest["stage_event_totals"]["guarded_live_commit_count"]
                - latest["stage_event_totals"]["guarded_live_commit_count"]
            ),
            "change_in_completed_paired_windows": int(
                oldest["stage_event_totals"]["completed_evaluation_window_count"]
                - latest["stage_event_totals"]["completed_evaluation_window_count"]
            ),
            "change_in_discrete_action_difference_events": int(
                oldest["discrete_action_difference_events"]
                - latest["discrete_action_difference_events"]
            ),
            "change_in_sources_with_objective_event_divergence": int(
                oldest["sources_with_objective_event_divergence"]
                - latest["sources_with_objective_event_divergence"]
            ),
        },
        "per_source": per_source,
        "diagnostic_interpretation": {
            "latest_policy_collapses_exact_ties_to_delay_one": True,
            "oldest_policy_changes_temporal_allocation_without_changing_similarity": True,
            "oldest_policy_increases_historical_event_reuse_concentration": bool(
                max(oldest_assoc["per_source_maximum_historical_event_reuse"])
                > max(latest_assoc["per_source_maximum_historical_event_reuse"])
            ),
            "temporal_tie_break_is_material_to_short_update_visibility": bool(
                oldest["stage_event_totals"] != latest["stage_event_totals"]
                or oldest["discrete_action_difference_events"]
                != latest["discrete_action_difference_events"]
            ),
            "recency_or_age_has_value_semantics": False,
            "tie_break_proves_credit_quality": False,
            "tie_break_proves_learning": False,
            "next_authorized_step": (
                "retain rollback and the frozen panel; do not prefer latest or oldest by value. "
                "Use this audit to decide whether a bounded multi-candidate allocation diagnostic "
                "is needed before any learning-mechanism change."
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
    *, latest_study_report: str | Path, oldest_study_report: str | Path
) -> dict[str, Any]:
    latest_study = _load_json(latest_study_report)
    oldest_study = _load_json(oldest_study_report)
    latest_component = latest_study.get("component_reproducibility")
    oldest_component = oldest_study.get("component_reproducibility")
    if not latest_component or not oldest_component:
        raise ValueError("Stage-3C-17 requires Stage-3C-8 reports for both arms")
    return assess_stage3c17_temporal_tie_break(
        latest_study,
        _load_json(latest_study["stage3c10_diagnostics"]),
        _load_json(latest_component),
        oldest_study,
        _load_json(oldest_study["stage3c10_diagnostics"]),
        _load_json(oldest_component),
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Assess equal-similarity temporal association tie-break allocation."
    )
    parser.add_argument("--latest-study-report", required=True)
    parser.add_argument("--oldest-study-report", required=True)
    parser.add_argument("--output", required=True)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    result = assess_from_paths(
        latest_study_report=args.latest_study_report,
        oldest_study_report=args.oldest_study_report,
    )
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(
        json.dumps(
            {
                "assessment_sha256": result["assessment_sha256"],
                "comparison": result["comparison"],
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()


__all__ = [
    "STAGE3C17_TEMPORAL_TIE_BREAK_SCHEMA",
    "assess_from_paths",
    "assess_stage3c17_temporal_tie_break",
]
