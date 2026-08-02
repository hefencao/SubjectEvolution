"""Stage 3C-18 bounded association candidate-allocation audit.

The frozen Stage-3C-16 carrier-on ``edge_forward_gate`` baseline and the
Stage-3C-17 latest tie-break are held fixed. The only experimental factor is
whether one or at most two highest-ranked address candidates contribute to the
single historical objective-fact reference used by one modulation proposal.
When two candidates are available their fact vectors are combined with an
equal-weight arithmetic mean before the existing normalized contrast. This is
an engineering addressing diagnostic, not value weighting or causal credit.
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
from .subject_vm_stage3c17_temporal_tie_break import _arm_summary

STAGE3C18_BOUNDED_CANDIDATE_ALLOCATION_SCHEMA = (
    "se-subject-vm-stage3c18-bounded-candidate-allocation-assessment-v1"
)


def _validate_study(study: dict[str, Any], *, candidate_limit: int) -> None:
    if study.get("schema") != "se-subject-vm-short-paired-study-v1":
        raise ValueError("Stage-3C-18 requires short paired study reports")
    parameters = study.get("parameters", {})
    if int(parameters.get("association_candidate_limit", -1)) != candidate_limit:
        raise ValueError("Stage-3C-18 association candidate limit does not match arm")
    if parameters.get("association_candidate_aggregation") != "equal-weight-mean":
        raise ValueError("Stage-3C-18 requires equal-weight candidate aggregation")
    if parameters.get("association_tie_break") != "latest":
        raise ValueError("Stage-3C-18 keeps the Stage-3C-17 latest ordering fixed")
    if parameters.get("bootstrap_target_family") != "edge_forward_gate":
        raise ValueError("Stage-3C-18 requires edge_forward_gate")
    if not bool(parameters.get("bootstrap_edge_carrier_enabled")):
        raise ValueError("Stage-3C-18 requires the carrier-on baseline")
    if int(parameters.get("horizon_ticks", -1)) != 8:
        raise ValueError("Stage-3C-18 requires the frozen eight-tick branch horizon")
    if int(parameters.get("rollback_after_ticks", -1)) != 3:
        raise ValueError("Stage-3C-18 requires the frozen exposure duration three")
    if len(study.get("seeds", ())) < 3:
        raise ValueError("Stage-3C-18 requires at least three independent sources")
    if not bool(study["engineering_summary"]["stage3c7_engineering_screen_passed"]):
        raise ValueError("Stage-3C-18 arms must pass Stage-3C-7")
    if bool(study.get("permanent_parameter_retention_authorized")):
        raise ValueError("Stage-3C-18 cannot use permanent parameter retention")


def _factor_signature(study: dict[str, Any]) -> dict[str, Any]:
    parameters = dict(study["parameters"])
    parameters.pop("association_candidate_limit", None)
    return {
        "project_config_file_sha256": study["project_config_file_sha256"],
        "parameters_except_candidate_limit": parameters,
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


def _plan_candidate_limit(source: dict[str, Any]) -> int:
    plan = _load_json(source["plan"])
    overrides = plan.get("branch_runtime_overrides")
    if overrides is None:
        return 1
    if set(overrides) != {"subject_vm.association.candidate_limit"}:
        raise ValueError("Stage-3C-18 plan contains an unauthorized runtime override")
    return int(overrides["subject_vm.association.candidate_limit"])


def _association_snapshot(checkpoint: str | Path) -> dict[str, Any]:
    _, state = read_checkpoint_bundle(checkpoint)
    arrays = state["simulation"]["subject_vm"]["trace_storage"]["arrays"]
    valid = np.asarray(arrays["event_valid"], dtype=bool)
    assigned = np.asarray(arrays["association_assigned"], dtype=bool)
    mask = valid & assigned
    selected_count = np.asarray(
        arrays["association_selected_count"], dtype=np.uint8
    )[mask]
    primary_ids = np.asarray(arrays["associated_event_id"], dtype=np.uint64)[mask]
    primary_delays = np.asarray(
        arrays["association_delay_ticks"], dtype=np.int64
    )[mask]
    primary_similarity = np.asarray(
        arrays["association_similarity"], dtype=np.float64
    )[mask]
    two_mask = mask & (
        np.asarray(arrays["association_selected_count"], dtype=np.uint8) > 1
    )
    secondary_ids = np.asarray(
        arrays["secondary_associated_event_id"], dtype=np.uint64
    )[two_mask]
    secondary_delays = np.asarray(
        arrays["secondary_association_delay_ticks"], dtype=np.int64
    )[two_mask]
    secondary_similarity = np.asarray(
        arrays["secondary_association_similarity"], dtype=np.float64
    )[two_mask]

    all_ids = [int(value) for value in primary_ids.tolist()]
    all_ids.extend(int(value) for value in secondary_ids.tolist())
    reuse = Counter(all_ids)
    primary_hist = Counter(int(value) for value in primary_delays.tolist())
    secondary_hist = Counter(int(value) for value in secondary_delays.tolist())
    all_delay_hist = primary_hist + secondary_hist
    similarities = np.concatenate((primary_similarity, secondary_similarity))
    return {
        "assigned_event_count": int(selected_count.size),
        "selected_reference_count": int(selected_count.sum()),
        "events_with_one_selected_candidate": int(np.count_nonzero(selected_count == 1)),
        "events_with_two_selected_candidates": int(np.count_nonzero(selected_count == 2)),
        "primary_delay_histogram": {
            str(key): int(value) for key, value in sorted(primary_hist.items())
        },
        "secondary_delay_histogram": {
            str(key): int(value) for key, value in sorted(secondary_hist.items())
        },
        "all_selected_delay_histogram": {
            str(key): int(value) for key, value in sorted(all_delay_hist.items())
        },
        "all_selected_similarities_one": bool(
            similarities.size
            and np.allclose(similarities, 1.0, rtol=0.0, atol=1e-7)
        ),
        "unique_selected_historical_event_count": len(reuse),
        "maximum_reuse_of_one_historical_event": max(reuse.values(), default=0),
        "historical_events_reused_more_than_once": int(
            sum(value > 1 for value in reuse.values())
        ),
    }


def _aggregate_association(per_source: list[dict[str, Any]]) -> dict[str, Any]:
    totals = Counter()
    primary = Counter()
    secondary = Counter()
    combined = Counter()
    unique_counts: list[int] = []
    maximum_reuse: list[int] = []
    reused_counts: list[int] = []
    all_one = True
    for item in per_source:
        snap = item["association_snapshot"]
        for key in (
            "assigned_event_count",
            "selected_reference_count",
            "events_with_one_selected_candidate",
            "events_with_two_selected_candidates",
        ):
            totals[key] += int(snap[key])
        primary.update(
            {int(key): int(value) for key, value in snap["primary_delay_histogram"].items()}
        )
        secondary.update(
            {int(key): int(value) for key, value in snap["secondary_delay_histogram"].items()}
        )
        combined.update(
            {int(key): int(value) for key, value in snap["all_selected_delay_histogram"].items()}
        )
        all_one &= bool(snap["all_selected_similarities_one"])
        unique_counts.append(int(snap["unique_selected_historical_event_count"]))
        maximum_reuse.append(int(snap["maximum_reuse_of_one_historical_event"]))
        reused_counts.append(int(snap["historical_events_reused_more_than_once"]))
    return {
        **{key: int(value) for key, value in totals.items()},
        "primary_delay_histogram": {
            str(key): int(value) for key, value in sorted(primary.items())
        },
        "secondary_delay_histogram": {
            str(key): int(value) for key, value in sorted(secondary.items())
        },
        "all_selected_delay_histogram": {
            str(key): int(value) for key, value in sorted(combined.items())
        },
        "all_selected_similarities_one": all_one,
        "per_source_unique_selected_historical_event_counts": unique_counts,
        "per_source_maximum_historical_event_reuse": maximum_reuse,
        "per_source_historical_events_reused_more_than_once": reused_counts,
    }


def assess_stage3c18_bounded_candidate_allocation(
    top1_study: dict[str, Any],
    top1_diagnostics: dict[str, Any],
    top1_component: dict[str, Any],
    top2_study: dict[str, Any],
    top2_diagnostics: dict[str, Any],
    top2_component: dict[str, Any],
) -> dict[str, Any]:
    _validate_study(top1_study, candidate_limit=1)
    _validate_study(top2_study, candidate_limit=2)
    if _factor_signature(top1_study) != _factor_signature(top2_study):
        raise ValueError("bounded candidate comparison changed another study factor")

    top1_sources = _source_records(top1_study)
    top2_sources = _source_records(top2_study)
    top1_diag = _diagnostics_by_seed(top1_diagnostics)
    top2_diag = _diagnostics_by_seed(top2_diagnostics)
    if not (
        set(top1_sources) == set(top2_sources) == set(top1_diag) == set(top2_diag)
    ):
        raise ValueError("bounded candidate arms use different source panels")

    state_equal = True
    config_equal = True
    subjects_equal = True
    control_equal = True
    per_source: list[dict[str, Any]] = []
    for seed in sorted(top1_sources):
        left = top1_sources[seed]
        right = top2_sources[seed]
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
        if _plan_candidate_limit(left) != 1 or _plan_candidate_limit(right) != 2:
            raise ValueError("bounded candidate plan limit mismatch")
        top1_snapshot = _association_snapshot(left["read_only_control_checkpoint"])
        top2_snapshot = _association_snapshot(right["read_only_control_checkpoint"])
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
                "top1": {"association_snapshot": top1_snapshot},
                "top2": {"association_snapshot": top2_snapshot},
            }
        )

    if not all((state_equal, config_equal, subjects_equal, control_equal)):
        raise ValueError("bounded candidate comparison failed isolation contract")

    top1_assoc = _aggregate_association([item["top1"] for item in per_source])
    top2_assoc = _aggregate_association([item["top2"] for item in per_source])
    if top1_assoc["assigned_event_count"] != top2_assoc["assigned_event_count"]:
        raise ValueError("candidate limit changed the assigned current-event count")
    if top1_assoc["selected_reference_count"] != top1_assoc["assigned_event_count"]:
        raise ValueError("top-1 arm does not contain one reference per assigned event")
    if top2_assoc["selected_reference_count"] <= top1_assoc["selected_reference_count"]:
        raise ValueError("top-2 arm did not increase bounded candidate references")
    if top2_assoc["events_with_two_selected_candidates"] <= 0:
        raise ValueError("top-2 arm never selected a second candidate")
    if not top1_assoc["all_selected_similarities_one"]:
        raise ValueError("top-1 arm is not the frozen equal-similarity panel")
    if not top2_assoc["all_selected_similarities_one"]:
        raise ValueError("top-2 arm is not the frozen equal-similarity panel")

    top1 = _arm_summary(top1_study, top1_diagnostics, top1_component)
    top2 = _arm_summary(top2_study, top2_diagnostics, top2_component)
    payload = {
        "schema": STAGE3C18_BOUNDED_CANDIDATE_ALLOCATION_SCHEMA,
        "producer_version": __version__,
        "top1_study_sha256": top1_study["study_sha256"],
        "top2_study_sha256": top2_study["study_sha256"],
        "single_changed_experimental_factor": (
            "bounded association candidate limit: one -> two; equal-weight historical-fact mean"
        ),
        "unchanged_factor_signature": _factor_signature(top1_study),
        "isolation_contract": {
            "independent_source_count": len(per_source),
            "seeds": sorted(top1_sources),
            "source_checkpoint_state_hashes_equal": state_equal,
            "pre_bootstrap_config_hashes_equal": config_equal,
            "bootstrap_subject_selection_equal": subjects_equal,
            "read_only_control_behavior_equal": control_equal,
            "same_latest_tie_break": True,
            "same_candidate_delay_bounds": True,
            "same_normalized_dot_similarity": True,
            "same_similarity_threshold": True,
            "same_edge_forward_gate_target_and_carrier": True,
            "same_one_modulation_proposal_per_current_event_contract": True,
            "same_update_safety_and_event_delta_budget": True,
            "only_candidate_limit_changed": True,
            "highest_independent_replicate": "independent-source-checkpoint",
            "windows_are_independent_replicates": False,
        },
        "top1": {**top1, "association_allocation": top1_assoc},
        "top2": {**top2, "association_allocation": top2_assoc},
        "comparison": {
            "change_in_selected_historical_references": int(
                top2_assoc["selected_reference_count"]
                - top1_assoc["selected_reference_count"]
            ),
            "change_in_events_with_two_candidates": int(
                top2_assoc["events_with_two_selected_candidates"]
                - top1_assoc["events_with_two_selected_candidates"]
            ),
            "change_in_modulation_proposals": int(
                top2["stage_event_totals"]["modulation_proposal_count"]
                - top1["stage_event_totals"]["modulation_proposal_count"]
            ),
            "change_in_live_commits": int(
                top2["stage_event_totals"]["guarded_live_commit_count"]
                - top1["stage_event_totals"]["guarded_live_commit_count"]
            ),
            "change_in_completed_paired_windows": int(
                top2["stage_event_totals"]["completed_evaluation_window_count"]
                - top1["stage_event_totals"]["completed_evaluation_window_count"]
            ),
            "change_in_discrete_action_difference_events": int(
                top2["discrete_action_difference_events"]
                - top1["discrete_action_difference_events"]
            ),
            "change_in_sources_with_objective_event_divergence": int(
                top2["sources_with_objective_event_divergence"]
                - top1["sources_with_objective_event_divergence"]
            ),
        },
        "per_source": per_source,
        "diagnostic_interpretation": {
            "bounded_top2_increases_addressed_historical_reference_count": True,
            "candidate_similarity_is_not_used_as_value_or_weight": True,
            "historical_fact_vectors_use_equal_weight_mean": True,
            "top2_preserves_one_proposal_and_one_event_delta_budget": True,
            "more_candidates_prove_better_credit": False,
            "more_candidates_prove_learning": False,
            "next_authorized_step": (
                "Interpret the nine-source result before any additional addressing or update change. "
                "Do not increase candidate count, retain parameters, or add learned weights unless "
                "the bounded top-2 audit identifies a specific remaining bottleneck."
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
        "runtime_memory_growth_formula_bytes": (
            "25 * entity_capacity * trace_capacity_per_subject when association is enabled"
        ),
        "checkpoint_compatibility": (
            "v8 and older trace checkpoints restore new bounded-candidate fields to empty defaults"
        ),
    }
    payload["assessment_sha256"] = _canonical_sha256(payload)
    return payload


def assess_from_paths(
    *, top1_study_report: str | Path, top2_study_report: str | Path
) -> dict[str, Any]:
    top1_study = _load_json(top1_study_report)
    top2_study = _load_json(top2_study_report)
    top1_component = top1_study.get("component_reproducibility")
    top2_component = top2_study.get("component_reproducibility")
    if not top1_component or not top2_component:
        raise ValueError("Stage-3C-18 requires Stage-3C-8 reports for both arms")
    return assess_stage3c18_bounded_candidate_allocation(
        top1_study,
        _load_json(top1_study["stage3c10_diagnostics"]),
        _load_json(top1_component),
        top2_study,
        _load_json(top2_study["stage3c10_diagnostics"]),
        _load_json(top2_component),
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Assess bounded one-versus-two association candidate allocation."
    )
    parser.add_argument("--top1-study-report", required=True)
    parser.add_argument("--top2-study-report", required=True)
    parser.add_argument("--output", required=True)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    result = assess_from_paths(
        top1_study_report=args.top1_study_report,
        top2_study_report=args.top2_study_report,
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
    "STAGE3C18_BOUNDED_CANDIDATE_ALLOCATION_SCHEMA",
    "assess_from_paths",
    "assess_stage3c18_bounded_candidate_allocation",
]
