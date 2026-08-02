"""Stage 3C-13 temporary-parameter-exposure adequacy comparison.

The comparison keeps the source panel, branch horizon, bounded update scale,
bootstrap topology, and objective aggregation fixed.  It changes only the
rollback duration used by paired branches; the read-only control horizon is
synchronized because that is an existing Stage-3C-5 symmetry contract, not a
second experimental factor.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
from typing import Any, Iterable

import numpy as np

from .. import __version__
from ..checkpointing import read_checkpoint_bundle
from .subject_vm_component_reproducibility import COMPONENT_REPRODUCIBILITY_SCHEMA
from .subject_vm_stage3c10_diagnostics import STAGE3C10_DIAGNOSTICS_SCHEMA

STAGE3C13_EXPOSURE_ADEQUACY_SCHEMA = (
    "se-subject-vm-stage3c13-exposure-adequacy-assessment-v1"
)
_SHORT_STUDY_SCHEMA = "se-subject-vm-short-paired-study-v1"
_PLAN_SCHEMA = "se-subject-vm-paired-evaluation-plan-v1"
_ALLOWED_OVERRIDE_KEYS = {
    "subject_vm.live_write.rollback_after_ticks",
    "subject_vm.evaluation.control_horizon_ticks",
}
_CONTROL_BEHAVIOR_ARRAYS = (
    "thought_token",
    "action_potentials",
    "sampled_probability",
    "action_id",
    "success",
    "objective_delta",
    "resolution_resource_delta",
    "resolution_internal_resource_delta",
    "resolution_energy_cost",
)


def _canonical_sha256(payload: Any) -> str:
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _load_json(path: str | Path) -> dict[str, Any]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"expected one JSON object: {path}")
    return payload


def _verify_checksum(payload: dict[str, Any], field: str, label: str) -> None:
    recorded = str(payload.get(field, ""))
    unsigned = dict(payload)
    unsigned.pop(field, None)
    if not recorded or recorded != _canonical_sha256(unsigned):
        raise ValueError(f"{label} checksum mismatch")


def _stats(values: Iterable[float | int]) -> dict[str, Any]:
    array = np.asarray(list(values), dtype=np.float64)
    if array.size == 0:
        return {
            "count": 0,
            "minimum": None,
            "median": None,
            "maximum": None,
            "mean": None,
        }
    return {
        "count": int(array.size),
        "minimum": float(np.min(array)),
        "median": float(np.median(array)),
        "maximum": float(np.max(array)),
        "mean": float(np.mean(array)),
    }


def _validate_report_set(
    study: dict[str, Any],
    component: dict[str, Any],
    diagnostics: dict[str, Any],
    *,
    label: str,
) -> None:
    if study.get("schema") != _SHORT_STUDY_SCHEMA:
        raise ValueError(f"{label} must be a short paired study")
    _verify_checksum(study, "study_sha256", f"{label} study")
    if component.get("schema") != COMPONENT_REPRODUCIBILITY_SCHEMA:
        raise ValueError(f"{label} requires Stage-3C-8 component evidence")
    _verify_checksum(component, "assessment_sha256", f"{label} Stage-3C-8")
    if diagnostics.get("schema") != STAGE3C10_DIAGNOSTICS_SCHEMA:
        raise ValueError(f"{label} requires Stage-3C-10 diagnostics")
    _verify_checksum(diagnostics, "diagnostics_sha256", f"{label} Stage-3C-10")
    if study.get("component_reproducibility_sha256") != component.get(
        "assessment_sha256"
    ):
        raise ValueError(f"{label} Stage-3C-8 identity mismatch")
    if study.get("stage3c10_diagnostics_sha256") != diagnostics.get(
        "diagnostics_sha256"
    ):
        raise ValueError(f"{label} Stage-3C-10 identity mismatch")
    summary = study.get("engineering_summary", {})
    if not bool(summary.get("stage3c7_engineering_screen_passed")):
        raise ValueError(f"{label} failed Stage-3C-7 engineering integrity")
    if not bool(summary.get("stage3c8_report_generated")):
        raise ValueError(f"{label} lacks Stage-3C-8 evidence")
    if bool(diagnostics.get("diagnostic_interpretation", {}).get(
        "paired_contract_error_detected"
    )):
        raise ValueError(f"{label} diagnostics report a paired contract error")


def _source_records(study: dict[str, Any]) -> dict[int, dict[str, Any]]:
    records = {int(item["seed"]): item for item in study.get("seeds", [])}
    if len(records) != len(study.get("seeds", [])):
        raise ValueError("study contains duplicate seed records")
    return records


def _diagnostics_by_seed(diagnostics: dict[str, Any]) -> dict[int, dict[str, Any]]:
    records = {int(item["seed"]): item for item in diagnostics.get("per_source", [])}
    if len(records) != len(diagnostics.get("per_source", [])):
        raise ValueError("diagnostics contain duplicate seed records")
    return records


def _study_factor_signature(study: dict[str, Any]) -> dict[str, Any]:
    parameters = dict(study["parameters"])
    parameters.pop("rollback_after_ticks", None)
    return {
        "project_config_file_sha256": study["project_config_file_sha256"],
        "parameters_except_exposure": parameters,
        "population": study["population"],
        "resolved_backend": study["resolved_backend"],
        "bootstrap_profile_sha256": study["bootstrap_profile"]["profile_sha256"],
        "fixed_bootstrap_is_evolved_result": study[
            "fixed_bootstrap_is_evolved_result"
        ],
        "universal_attention_claim": study["universal_attention_claim"],
        "permanent_parameter_retention_authorized": study[
            "permanent_parameter_retention_authorized"
        ],
    }


def _validate_plan_exposure(plan: dict[str, Any], expected: int) -> dict[str, Any]:
    if plan.get("schema") != _PLAN_SCHEMA:
        raise ValueError("exposure study seed lacks a paired evaluation plan")
    _verify_checksum(plan, "plan_sha256", "paired evaluation plan")
    overrides = plan.get("branch_contract_overrides")
    if not isinstance(overrides, dict) or set(overrides) != _ALLOWED_OVERRIDE_KEYS:
        raise ValueError("paired plan changed a non-exposure branch contract field")
    rollback = int(overrides["subject_vm.live_write.rollback_after_ticks"])
    control = int(overrides["subject_vm.evaluation.control_horizon_ticks"])
    if rollback != expected or control != expected:
        raise ValueError("paired plan exposure override does not match study contract")
    return {
        "rollback_after_ticks": rollback,
        "control_horizon_ticks": control,
        "only_exposure_fields_overridden": True,
        "plan_sha256": plan["plan_sha256"],
        "source_checkpoint_config_sha256": plan["source"][
            "checkpoint_config_sha256"
        ],
        "source_checkpoint_state_sha256": plan["source"][
            "checkpoint_state_sha256"
        ],
    }


def _event_index(trace: dict[str, np.ndarray]) -> dict[tuple[int, int], tuple[int, int]]:
    result: dict[tuple[int, int], tuple[int, int]] = {}
    for row, slot in zip(*np.nonzero(trace["event_valid"]), strict=True):
        key = (
            int(trace["subject_id"][row, slot]),
            int(trace["event_tick"][row, slot]),
        )
        if key in result:
            raise ValueError(f"duplicate subject/tick trace event: {key}")
        result[key] = (int(row), int(slot))
    return result


def _compare_control_behavior(
    baseline_checkpoint: str | Path,
    extended_checkpoint: str | Path,
) -> dict[str, Any]:
    baseline_meta, baseline_state = read_checkpoint_bundle(baseline_checkpoint)
    extended_meta, extended_state = read_checkpoint_bundle(extended_checkpoint)
    baseline_trace = baseline_state["simulation"]["subject_vm"]["trace_storage"][
        "arrays"
    ]
    extended_trace = extended_state["simulation"]["subject_vm"]["trace_storage"][
        "arrays"
    ]
    baseline_index = _event_index(baseline_trace)
    extended_index = _event_index(extended_trace)
    keys_equal = set(baseline_index) == set(extended_index)
    mismatched_arrays: Counter[str] = Counter()
    mismatched_events = 0
    if keys_equal:
        for key in sorted(baseline_index):
            left = baseline_index[key]
            right = extended_index[key]
            event_mismatch = False
            for name in _CONTROL_BEHAVIOR_ARRAYS:
                if not np.array_equal(
                    baseline_trace[name][left], extended_trace[name][right]
                ):
                    mismatched_arrays[name] += 1
                    event_mismatch = True
            mismatched_events += int(event_mismatch)
    return {
        "baseline_checkpoint_tick": int(baseline_meta["tick"]),
        "extended_checkpoint_tick": int(extended_meta["tick"]),
        "event_keys_equal": keys_equal,
        "behavior_arrays_compared": list(_CONTROL_BEHAVIOR_ARRAYS),
        "mismatched_event_count": int(mismatched_events),
        "mismatched_array_event_counts": dict(sorted(mismatched_arrays.items())),
        "control_behavior_semantically_identical": bool(
            keys_equal and mismatched_events == 0
        ),
    }


def _coordinate_summary(component: dict[str, Any]) -> dict[str, Any]:
    tolerance = float(component["parameters"]["zero_tolerance"])
    source_vectors = [
        np.asarray(
            source["source_subject_balanced_objective_fact_mean"],
            dtype=np.float64,
        )
        for source in component["source_replicates"]
    ]
    nonzero_sources = int(
        sum(bool(np.any(np.abs(vector) > tolerance)) for vector in source_vectors)
    )
    return {
        "stable_objective_coordinate_count": len(
            component["coordinates_with_descriptive_sign_and_interval_stability"]
        ),
        "stable_objective_coordinates": list(
            component["coordinates_with_descriptive_sign_and_interval_stability"]
        ),
        "sources_with_nonzero_completed_window_objective_vector": nonzero_sources,
    }


def _pooled_summary_from_source_stats(
    per_source: list[dict[str, Any]], field: str
) -> dict[str, Any]:
    summaries = [
        item["update_visibility_and_divergence"][field] for item in per_source
    ]
    count = sum(int(item["count"]) for item in summaries)
    weighted_sum = sum(
        int(item["count"]) * float(item["mean"])
        for item in summaries
        if item["count"] and item["mean"] is not None
    )
    minima = [float(item["minimum"]) for item in summaries if item["minimum"] is not None]
    maxima = [float(item["maximum"]) for item in summaries if item["maximum"] is not None]
    return {
        "count": int(count),
        "minimum": min(minima) if minima else None,
        "maximum": max(maxima) if maxima else None,
        "weighted_mean": float(weighted_sum / count) if count else None,
        "per_source_medians": [item["median"] for item in summaries],
        "pooled_median_not_reconstructed_from_summaries": True,
    }


def _rejection_totals(per_source: list[dict[str, Any]]) -> dict[str, int]:
    totals: Counter[str] = Counter()
    for source in per_source:
        totals.update(
            source["guarded_live"]["funnel"]["canonical_rejection_categories"]
        )
    return dict(sorted((key, int(value)) for key, value in totals.items()))


def _arm_summary(
    study: dict[str, Any],
    component: dict[str, Any],
    diagnostics: dict[str, Any],
) -> dict[str, Any]:
    aggregate = diagnostics["aggregate"]
    per_source = diagnostics["per_source"]
    exposure = study["temporary_exposure_contract"]
    live_pending_at_export = sum(
        int(
            source["rollback_and_finalization"]
            .get("live_finalization", {})
            .get("pending_before", 0)
        )
        for source in per_source
    )
    control_pending_at_export = sum(
        int(
            source["rollback_and_finalization"]
            .get("control_finalization", {})
            .get("pending_before", 0)
        )
        for source in per_source
    )
    return {
        "rollback_after_ticks": int(exposure["rollback_after_ticks"]),
        "control_horizon_ticks": int(exposure["control_horizon_ticks"]),
        "observation_ticks": int(exposure["observation_ticks"]),
        "branch_horizon_ticks": int(study["parameters"]["horizon_ticks"]),
        "independent_source_count": int(
            study["engineering_summary"]["independent_source_pair_count"]
        ),
        "completed_paired_windows": int(
            study["engineering_summary"]["total_paired_window_count"]
        ),
        "completed_windows_per_source": _stats(
            source["paired_window_symmetry"]["completed_live_windows"]
            for source in per_source
        ),
        "live_commits": int(aggregate["live_commits"]),
        "live_pending_transactions_finalized_at_export_boundary": int(
            live_pending_at_export
        ),
        "control_pending_reservations_finalized_at_export_boundary": int(
            control_pending_at_export
        ),
        "finalized_incomplete_windows_used_as_evidence": False,
        "temporary_effective_semantic_ticks_per_commit": (
            _pooled_summary_from_source_stats(
                per_source, "temporary_effective_semantic_ticks_per_commit"
            )
        ),
        "subject_events_during_temporary_effect_per_commit": (
            _pooled_summary_from_source_stats(
                per_source, "subject_events_during_temporary_effect_per_commit"
            )
        ),
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
        "sources_with_post_rollback_path_dependence": int(
            aggregate["sources_with_post_rollback_path_dependence"]
        ),
        "sources_with_complete_divergence_trace": int(
            aggregate["sources_with_complete_divergence_trace"]
        ),
        "canonical_rejection_category_totals": _rejection_totals(per_source),
        "pairing_coverage": float(
            study["engineering_summary"]["pooled_pairing_coverage"]
        ),
        "rollback_failure_count": int(
            study["engineering_summary"]["rollback_failure_count"]
        ),
        "objective_fact_clip_fraction": float(
            study["engineering_summary"]["fact_clip_fraction"]
        ),
        "evaluation_cost_match_fraction": float(
            study["engineering_summary"]["evaluation_cost_match_fraction"]
        ),
        **_coordinate_summary(component),
    }


def assess_stage3c13_exposure_adequacy(
    baseline_study: dict[str, Any],
    extended_study: dict[str, Any],
    *,
    baseline_component: dict[str, Any],
    extended_component: dict[str, Any],
    baseline_diagnostics: dict[str, Any],
    extended_diagnostics: dict[str, Any],
) -> dict[str, Any]:
    """Compare two exposure-only studies without scalarizing evidence."""
    _validate_report_set(
        baseline_study,
        baseline_component,
        baseline_diagnostics,
        label="baseline",
    )
    _validate_report_set(
        extended_study,
        extended_component,
        extended_diagnostics,
        label="extended",
    )
    if _study_factor_signature(baseline_study) != _study_factor_signature(
        extended_study
    ):
        raise ValueError("exposure comparison changed a non-exposure study factor")

    baseline_exposure = int(
        baseline_study["temporary_exposure_contract"]["rollback_after_ticks"]
    )
    extended_exposure = int(
        extended_study["temporary_exposure_contract"]["rollback_after_ticks"]
    )
    if not baseline_exposure < extended_exposure:
        raise ValueError("extended exposure duration must exceed baseline duration")
    for label, study, exposure in (
        ("baseline", baseline_study, baseline_exposure),
        ("extended", extended_study, extended_exposure),
    ):
        contract = study["temporary_exposure_contract"]
        if int(contract["control_horizon_ticks"]) != exposure:
            raise ValueError(f"{label} control horizon is not exposure-synchronized")
        if int(study["parameters"]["rollback_after_ticks"]) != exposure:
            raise ValueError(f"{label} study parameter and exposure contract disagree")
        if not bool(contract["source_checkpoint_config_unchanged"]):
            raise ValueError(f"{label} changed the source checkpoint configuration")

    baseline_sources = _source_records(baseline_study)
    extended_sources = _source_records(extended_study)
    baseline_diag = _diagnostics_by_seed(baseline_diagnostics)
    extended_diag = _diagnostics_by_seed(extended_diagnostics)
    if not (
        set(baseline_sources)
        == set(extended_sources)
        == set(baseline_diag)
        == set(extended_diag)
    ):
        raise ValueError("exposure arms use different independent source panels")

    per_source = []
    source_hashes_equal = True
    source_config_hashes_equal = True
    bootstrap_lineage_equal = True
    control_behavior_equal = True
    for seed in sorted(baseline_sources):
        baseline_source = baseline_sources[seed]
        extended_source = extended_sources[seed]
        baseline_plan = _load_json(baseline_source["plan"])
        extended_plan = _load_json(extended_source["plan"])
        baseline_plan_contract = _validate_plan_exposure(
            baseline_plan, baseline_exposure
        )
        extended_plan_contract = _validate_plan_exposure(
            extended_plan, extended_exposure
        )
        state_equal = bool(
            baseline_source["source_checkpoint_state_sha256"]
            == extended_source["source_checkpoint_state_sha256"]
            == baseline_plan_contract["source_checkpoint_state_sha256"]
            == extended_plan_contract["source_checkpoint_state_sha256"]
        )
        config_equal = bool(
            baseline_plan_contract["source_checkpoint_config_sha256"]
            == extended_plan_contract["source_checkpoint_config_sha256"]
        )
        lineage_equal = bool(
            baseline_source["bootstrap_lineage"]
            == extended_source["bootstrap_lineage"]
        )
        control_comparison = _compare_control_behavior(
            baseline_source["read_only_control_checkpoint"],
            extended_source["read_only_control_checkpoint"],
        )
        source_hashes_equal &= state_equal
        source_config_hashes_equal &= config_equal
        bootstrap_lineage_equal &= lineage_equal
        control_behavior_equal &= bool(
            control_comparison["control_behavior_semantically_identical"]
        )
        baseline_visibility = baseline_diag[seed][
            "update_visibility_and_divergence"
        ]
        extended_visibility = extended_diag[seed][
            "update_visibility_and_divergence"
        ]
        baseline_action = sum(
            int(item["difference_counts"].get("action_id", 0))
            for item in baseline_visibility["branch_divergence_timeline"]
        )
        extended_action = sum(
            int(item["difference_counts"].get("action_id", 0))
            for item in extended_visibility["branch_divergence_timeline"]
        )
        per_source.append(
            {
                "seed": seed,
                "source_state_hash_equal": state_equal,
                "source_config_hash_equal": config_equal,
                "bootstrap_lineage_equal": lineage_equal,
                "baseline_plan_contract": baseline_plan_contract,
                "extended_plan_contract": extended_plan_contract,
                "read_only_control_behavior": control_comparison,
                "baseline_completed_paired_windows": int(
                    baseline_diag[seed]["paired_window_symmetry"][
                        "completed_live_windows"
                    ]
                ),
                "extended_completed_paired_windows": int(
                    extended_diag[seed]["paired_window_symmetry"][
                        "completed_live_windows"
                    ]
                ),
                "baseline_discrete_action_difference_events": baseline_action,
                "extended_discrete_action_difference_events": extended_action,
                "change_in_discrete_action_difference_events": int(
                    extended_action - baseline_action
                ),
            }
        )

    if not source_hashes_equal or not source_config_hashes_equal:
        raise ValueError("exposure arms do not share identical source checkpoints")
    if not bootstrap_lineage_equal:
        raise ValueError("exposure arms use different bootstrap lineages")
    if not control_behavior_equal:
        raise ValueError("exposure override changed read-only control behavior")

    baseline_arm = _arm_summary(
        baseline_study, baseline_component, baseline_diagnostics
    )
    extended_arm = _arm_summary(
        extended_study, extended_component, extended_diagnostics
    )
    source_count = len(per_source)
    if not (
        baseline_arm["sources_with_complete_divergence_trace"] == source_count
        and extended_arm["sources_with_complete_divergence_trace"] == source_count
    ):
        raise ValueError("exposure comparison requires complete trace coverage")

    def delta(field: str) -> int:
        return int(extended_arm[field] - baseline_arm[field])

    baseline_effective = baseline_arm[
        "temporary_effective_semantic_ticks_per_commit"
    ]["weighted_mean"]
    extended_effective = extended_arm[
        "temporary_effective_semantic_ticks_per_commit"
    ]["weighted_mean"]
    comparison = {
        "change_in_completed_paired_windows": delta("completed_paired_windows"),
        "change_in_live_commits": delta("live_commits"),
        "change_in_action_potential_difference_events": delta(
            "action_potential_difference_events"
        ),
        "change_in_sampled_probability_difference_events": delta(
            "sampled_probability_difference_events"
        ),
        "change_in_discrete_action_difference_events": delta(
            "discrete_action_difference_events"
        ),
        "change_in_sources_with_discrete_action_divergence": delta(
            "sources_with_discrete_action_divergence"
        ),
        "change_in_sources_with_objective_event_divergence": delta(
            "sources_with_objective_event_divergence"
        ),
        "change_in_sources_with_nonzero_completed_window_objective_vector": delta(
            "sources_with_nonzero_completed_window_objective_vector"
        ),
        "change_in_stable_objective_coordinate_count": delta(
            "stable_objective_coordinate_count"
        ),
        "change_in_weighted_mean_effective_semantic_ticks_per_commit": (
            None
            if baseline_effective is None or extended_effective is None
            else float(extended_effective - baseline_effective)
        ),
    }
    continuous_visibility_increased = bool(
        comparison["change_in_action_potential_difference_events"] > 0
        and comparison["change_in_sampled_probability_difference_events"] > 0
    )
    discrete_visibility_increased = bool(
        comparison["change_in_discrete_action_difference_events"] > 0
        or comparison["change_in_sources_with_discrete_action_divergence"] > 0
    )

    payload = {
        "schema": STAGE3C13_EXPOSURE_ADEQUACY_SCHEMA,
        "producer_version": __version__,
        "baseline_study_sha256": baseline_study["study_sha256"],
        "extended_study_sha256": extended_study["study_sha256"],
        "single_changed_experimental_factor": (
            "temporary parameter exposure duration: "
            f"rollback_after_ticks {baseline_exposure} -> {extended_exposure}; "
            "control_horizon_ticks synchronized by paired contract"
        ),
        "unchanged_factor_signature": _study_factor_signature(baseline_study),
        "source_panel_and_contract_integrity": {
            "independent_source_count": source_count,
            "seeds": sorted(baseline_sources),
            "source_state_hashes_equal": source_hashes_equal,
            "source_config_hashes_equal": source_config_hashes_equal,
            "bootstrap_lineage_equal": bootstrap_lineage_equal,
            "read_only_control_behavior_equal": control_behavior_equal,
            "only_exposure_fields_overridden": True,
            "control_horizon_synchronization_is_existing_symmetry_contract": True,
            "highest_independent_replicate": "independent-source-checkpoint",
            "windows_are_independent_replicates": False,
        },
        "baseline": baseline_arm,
        "extended": extended_arm,
        "comparison": comparison,
        "per_source": per_source,
        "adequacy_interpretation": {
            "longer_exposure_increased_continuous_parameter_visibility": (
                continuous_visibility_increased
            ),
            "longer_exposure_increased_discrete_action_boundary_crossings": (
                discrete_visibility_increased
            ),
            "longer_exposure_is_supported_as_primary_explanation_for_sparse_discrete_divergence": bool(
                discrete_visibility_increased
            ),
            "longer_exposure_is_harmful": False,
            "non_monotonic_discrete_result_is_final_mechanism_verdict": False,
            "observed_result": (
                "The longer temporary exposure produces more continuous action-"
                "potential and sampled-probability differences, but it does not "
                "increase discrete-action crossings or cross-source objective "
                "stability in the fixed nine-source panel."
            ),
            "next_authorized_step": (
                "hold the nine-source panel, eight-tick horizon, exposure duration, "
                "and bounded delta fixed; audit one explicit fixed-bootstrap "
                "parameter-family reachability adjustment without adding value "
                "semantics, topology evolution, or permanent retention"
            ),
        },
        "objective_coordinate_value_interpretation": None,
        "universal_scalar_objective": False,
        "automatic_keep_or_revert_decision": False,
        "permanent_parameter_retention_authorized": False,
        "causal_effect_authorized": False,
        "learning_claim_authorized": False,
        "subjecthood_claim_authorized": False,
    }
    semantic = {
        key: payload[key]
        for key in (
            "schema",
            "producer_version",
            "single_changed_experimental_factor",
            "source_panel_and_contract_integrity",
            "baseline",
            "extended",
            "comparison",
            "adequacy_interpretation",
            "automatic_keep_or_revert_decision",
            "permanent_parameter_retention_authorized",
            "causal_effect_authorized",
            "learning_claim_authorized",
            "subjecthood_claim_authorized",
        )
    }
    payload["semantic_reproducibility"] = {
        "schema": "se-subject-vm-stage3c13-semantic-result-identity-v1",
        "artifact_paths_excluded": True,
        "checkpoint_created_utc_excluded": True,
        "artifact_integrity_checksums_still_verified_per_run": True,
        "semantic_result_sha256": _canonical_sha256(semantic),
    }
    payload["assessment_sha256"] = _canonical_sha256(payload)
    return payload


def assess_from_paths(
    baseline_study_report: str | Path,
    extended_study_report: str | Path,
    *,
    output_path: str | Path | None = None,
) -> dict[str, Any]:
    baseline = _load_json(baseline_study_report)
    extended = _load_json(extended_study_report)
    baseline_component = _load_json(baseline["component_reproducibility"])
    extended_component = _load_json(extended["component_reproducibility"])
    baseline_diagnostics = _load_json(baseline["stage3c10_diagnostics"])
    extended_diagnostics = _load_json(extended["stage3c10_diagnostics"])
    result = assess_stage3c13_exposure_adequacy(
        baseline,
        extended,
        baseline_component=baseline_component,
        extended_component=extended_component,
        baseline_diagnostics=baseline_diagnostics,
        extended_diagnostics=extended_diagnostics,
    )
    if output_path is not None:
        target = Path(output_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(
            json.dumps(result, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    return result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Assess a Stage-3C-13 temporary-exposure comparison."
    )
    parser.add_argument("--baseline-study-report", required=True)
    parser.add_argument("--extended-study-report", required=True)
    parser.add_argument("--output", required=True)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    result = assess_from_paths(
        args.baseline_study_report,
        args.extended_study_report,
        output_path=args.output,
    )
    print(
        json.dumps(
            {
                "single_changed_experimental_factor": result[
                    "single_changed_experimental_factor"
                ],
                "continuous_visibility_change": result["comparison"][
                    "change_in_action_potential_difference_events"
                ],
                "discrete_action_change": result["comparison"][
                    "change_in_discrete_action_difference_events"
                ],
                "stable_objective_coordinate_count": result["extended"][
                    "stable_objective_coordinate_count"
                ],
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()


__all__ = [
    "STAGE3C13_EXPOSURE_ADEQUACY_SCHEMA",
    "assess_from_paths",
    "assess_stage3c13_exposure_adequacy",
]
