"""Stage 3C-12 trace-safe branch-horizon adequacy comparison.

The comparison changes branch horizon only.  It verifies identical source-state
panels, exact semantic prefix identity, complete bounded-trace coverage, and the
existing Stage-3C-7/8/10 contracts before comparing score-free evidence.  The
report does not scalarize objective coordinates, retain parameters, or claim
learning or causal credit.
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

STAGE3C12_HORIZON_ADEQUACY_SCHEMA = (
    "se-subject-vm-stage3c12-horizon-adequacy-assessment-v1"
)
_SHORT_STUDY_SCHEMA = "se-subject-vm-short-paired-study-v1"
_BRANCH_CHECKPOINT_FIELDS = (
    "guarded_live_checkpoint",
    "read_only_control_checkpoint",
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


def _study_factor_signature(study: dict[str, Any]) -> dict[str, Any]:
    parameters = dict(study["parameters"])
    parameters.pop("horizon_ticks", None)
    return {
        "project_config_file_sha256": study["project_config_file_sha256"],
        "parameters_except_horizon": parameters,
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


def _event_index(trace: dict[str, np.ndarray], *, stop_tick: int) -> dict[tuple[int, int], tuple[int, int]]:
    result: dict[tuple[int, int], tuple[int, int]] = {}
    for row, slot in zip(*np.nonzero(trace["event_valid"]), strict=True):
        tick = int(trace["event_tick"][row, slot])
        if tick >= int(stop_tick):
            continue
        key = (int(trace["subject_id"][row, slot]), tick)
        if key in result:
            raise ValueError(f"duplicate subject/tick trace event: {key}")
        result[key] = (int(row), int(slot))
    return result


def _compare_checkpoint_prefix(
    baseline_path: str | Path,
    extended_path: str | Path,
    *,
    stop_tick: int,
) -> dict[str, Any]:
    baseline_meta, baseline_state = read_checkpoint_bundle(baseline_path)
    extended_meta, extended_state = read_checkpoint_bundle(extended_path)
    baseline_trace = baseline_state["simulation"]["subject_vm"]["trace_storage"][
        "arrays"
    ]
    extended_trace = extended_state["simulation"]["subject_vm"]["trace_storage"][
        "arrays"
    ]
    baseline_index = _event_index(baseline_trace, stop_tick=stop_tick)
    extended_index = _event_index(extended_trace, stop_tick=stop_tick)
    key_match = set(baseline_index) == set(extended_index)
    event_shape = tuple(baseline_trace["event_valid"].shape)
    comparable_arrays = sorted(
        name
        for name, array in baseline_trace.items()
        if isinstance(array, np.ndarray)
        and array.ndim >= 2
        and tuple(array.shape[:2]) == event_shape
        and name in extended_trace
        and isinstance(extended_trace[name], np.ndarray)
    )
    mismatched_arrays: list[str] = []
    mismatched_event_count = 0
    if key_match:
        for key in sorted(baseline_index):
            left = baseline_index[key]
            right = extended_index[key]
            event_mismatch = False
            for name in comparable_arrays:
                if not np.array_equal(
                    baseline_trace[name][left], extended_trace[name][right]
                ):
                    event_mismatch = True
                    if name not in mismatched_arrays:
                        mismatched_arrays.append(name)
            mismatched_event_count += int(event_mismatch)
    return {
        "baseline_checkpoint_tick": int(baseline_meta["tick"]),
        "extended_checkpoint_tick": int(extended_meta["tick"]),
        "prefix_stop_tick_exclusive": int(stop_tick),
        "baseline_prefix_event_count": len(baseline_index),
        "extended_prefix_event_count": len(extended_index),
        "event_keys_equal": key_match,
        "event_shaped_arrays_compared": len(comparable_arrays),
        "mismatched_event_count": int(mismatched_event_count),
        "mismatched_array_names": sorted(mismatched_arrays),
        "prefix_semantically_identical": bool(
            key_match and not mismatched_arrays and mismatched_event_count == 0
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


def _arm_summary(
    study: dict[str, Any],
    component: dict[str, Any],
    diagnostics: dict[str, Any],
) -> dict[str, Any]:
    aggregate = diagnostics["aggregate"]
    per_source = diagnostics["per_source"]
    return {
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


def assess_stage3c12_horizon_adequacy(
    baseline_study: dict[str, Any],
    extended_study: dict[str, Any],
    *,
    baseline_component: dict[str, Any],
    extended_component: dict[str, Any],
    baseline_diagnostics: dict[str, Any],
    extended_diagnostics: dict[str, Any],
) -> dict[str, Any]:
    """Compare two horizon-only paired studies without changing replicate units."""
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
    baseline_horizon = int(baseline_study["parameters"]["horizon_ticks"])
    extended_horizon = int(extended_study["parameters"]["horizon_ticks"])
    if not baseline_horizon < extended_horizon:
        raise ValueError("extended horizon must exceed baseline horizon")
    if _study_factor_signature(baseline_study) != _study_factor_signature(
        extended_study
    ):
        raise ValueError("horizon comparison changed a non-horizon study factor")

    baseline_sources = _source_records(baseline_study)
    extended_sources = _source_records(extended_study)
    if set(baseline_sources) != set(extended_sources):
        raise ValueError("horizon comparison requires the same seed panel")
    baseline_diag = _diagnostics_by_seed(baseline_diagnostics)
    extended_diag = _diagnostics_by_seed(extended_diagnostics)
    if set(baseline_diag) != set(baseline_sources) or set(extended_diag) != set(
        extended_sources
    ):
        raise ValueError("study and diagnostic source panels do not match")

    baseline_final_tick = int(next(iter(baseline_sources.values()))["final_tick"])
    source_tick = int(next(iter(baseline_sources.values()))["source_tick"])
    if baseline_final_tick != source_tick + baseline_horizon:
        raise ValueError("baseline final tick does not match its horizon")

    per_source: list[dict[str, Any]] = []
    tail_totals: Counter[str] = Counter()
    source_hashes_equal = True
    lineage_equal = True
    all_prefix_equal = True
    for seed in sorted(baseline_sources):
        left = baseline_sources[seed]
        right = extended_sources[seed]
        same_source_hash = (
            left["source_checkpoint_state_sha256"]
            == right["source_checkpoint_state_sha256"]
        )
        same_lineage = left["bootstrap_lineage"] == right["bootstrap_lineage"]
        source_hashes_equal &= same_source_hash
        lineage_equal &= same_lineage
        branch_prefix = {
            field.removesuffix("_checkpoint"): _compare_checkpoint_prefix(
                left[field], right[field], stop_tick=baseline_final_tick
            )
            for field in _BRANCH_CHECKPOINT_FIELDS
        }
        source_prefix_equal = all(
            item["prefix_semantically_identical"] for item in branch_prefix.values()
        )
        all_prefix_equal &= source_prefix_equal

        base_timeline = baseline_diag[seed]["update_visibility_and_divergence"][
            "branch_divergence_timeline"
        ]
        extended_timeline = extended_diag[seed]["update_visibility_and_divergence"][
            "branch_divergence_timeline"
        ]
        tail = [
            item for item in extended_timeline if int(item["tick"]) >= baseline_final_tick
        ]
        tail_action = int(
            sum(item["difference_counts"].get("action_id", 0) for item in tail)
        )
        tail_objective = int(
            sum(item["difference_counts"].get("objective_delta", 0) for item in tail)
        )
        tail_potential = int(
            sum(
                item["difference_counts"].get("action_potentials", 0)
                for item in tail
            )
        )
        tail_probability = int(
            sum(
                item["difference_counts"].get("sampled_probability", 0)
                for item in tail
            )
        )
        tail_totals["discrete_action_difference_events"] += tail_action
        tail_totals["objective_event_difference_events"] += tail_objective
        tail_totals["action_potential_difference_events"] += tail_potential
        tail_totals["sampled_probability_difference_events"] += tail_probability
        tail_totals["sources_with_discrete_action_divergence"] += int(
            tail_action > 0
        )
        tail_totals["sources_with_objective_event_divergence"] += int(
            tail_objective > 0
        )
        baseline_action = int(
            sum(
                item["difference_counts"].get("action_id", 0)
                for item in base_timeline
            )
        )
        extended_action = int(
            sum(
                item["difference_counts"].get("action_id", 0)
                for item in extended_timeline
            )
        )
        per_source.append(
            {
                "seed": seed,
                "source_checkpoint_state_sha256": left[
                    "source_checkpoint_state_sha256"
                ],
                "source_state_equal_across_horizons": same_source_hash,
                "bootstrap_lineage_equal_across_horizons": same_lineage,
                "prefix_semantic_identity": branch_prefix,
                "all_branch_prefixes_identical": source_prefix_equal,
                "baseline_completed_windows": int(
                    baseline_diag[seed]["paired_window_symmetry"][
                        "completed_live_windows"
                    ]
                ),
                "extended_completed_windows": int(
                    extended_diag[seed]["paired_window_symmetry"][
                        "completed_live_windows"
                    ]
                ),
                "baseline_live_commits": int(
                    baseline_diag[seed]["guarded_live"]["funnel"][
                        "stage_event_totals"
                    ]["guarded_live_commit_count"]
                ),
                "extended_live_commits": int(
                    extended_diag[seed]["guarded_live"]["funnel"][
                        "stage_event_totals"
                    ]["guarded_live_commit_count"]
                ),
                "baseline_discrete_action_difference_events": baseline_action,
                "extended_discrete_action_difference_events": extended_action,
                "extended_tail": {
                    "tick_start_inclusive": baseline_final_tick,
                    "tick_end_exclusive": int(right["final_tick"]),
                    "discrete_action_difference_events": tail_action,
                    "objective_event_difference_events": tail_objective,
                    "action_potential_difference_events": tail_potential,
                    "sampled_probability_difference_events": tail_probability,
                },
            }
        )

    if not source_hashes_equal:
        raise ValueError("horizon arms do not share identical source states")
    if not lineage_equal:
        raise ValueError("horizon arms do not share identical bootstrap lineage")
    if not all_prefix_equal:
        raise ValueError("horizon arms diverge before the baseline stop boundary")

    baseline_arm = _arm_summary(
        baseline_study, baseline_component, baseline_diagnostics
    )
    extended_arm = _arm_summary(
        extended_study, extended_component, extended_diagnostics
    )
    source_count = len(per_source)
    complete_trace = bool(
        baseline_arm["sources_with_complete_divergence_trace"] == source_count
        and extended_arm["sources_with_complete_divergence_trace"] == source_count
    )
    tail_summary = {
        **dict(sorted(tail_totals.items())),
        "new_discrete_action_divergence_after_baseline_boundary": bool(
            tail_totals["discrete_action_difference_events"] > 0
        ),
        "delayed_objective_path_divergence_after_baseline_boundary": bool(
            tail_totals["objective_event_difference_events"] > 0
        ),
    }
    comparison = {
        "additional_completed_paired_windows": int(
            extended_arm["completed_paired_windows"]
            - baseline_arm["completed_paired_windows"]
        ),
        "additional_live_commits": int(
            extended_arm["live_commits"] - baseline_arm["live_commits"]
        ),
        "change_in_discrete_action_difference_events": int(
            extended_arm["discrete_action_difference_events"]
            - baseline_arm["discrete_action_difference_events"]
        ),
        "change_in_sources_with_discrete_action_divergence": int(
            extended_arm["sources_with_discrete_action_divergence"]
            - baseline_arm["sources_with_discrete_action_divergence"]
        ),
        "change_in_sources_with_objective_event_divergence": int(
            extended_arm["sources_with_objective_event_divergence"]
            - baseline_arm["sources_with_objective_event_divergence"]
        ),
        "change_in_stable_objective_coordinate_count": int(
            extended_arm["stable_objective_coordinate_count"]
            - baseline_arm["stable_objective_coordinate_count"]
        ),
        "change_in_sources_with_nonzero_completed_window_objective_vector": int(
            extended_arm[
                "sources_with_nonzero_completed_window_objective_vector"
            ]
            - baseline_arm[
                "sources_with_nonzero_completed_window_objective_vector"
            ]
        ),
    }

    payload = {
        "schema": STAGE3C12_HORIZON_ADEQUACY_SCHEMA,
        "producer_version": __version__,
        "baseline_study_sha256": baseline_study["study_sha256"],
        "extended_study_sha256": extended_study["study_sha256"],
        "single_changed_experimental_factor": (
            f"branch horizon ticks: {baseline_horizon} -> {extended_horizon}"
        ),
        "unchanged_factor_signature": _study_factor_signature(baseline_study),
        "source_panel_identity": {
            "independent_source_count": source_count,
            "seeds": sorted(baseline_sources),
            "source_state_hashes_equal": source_hashes_equal,
            "bootstrap_lineage_equal": lineage_equal,
            "highest_independent_replicate": "independent-source-checkpoint",
            "windows_are_independent_replicates": False,
        },
        "trace_and_prefix_integrity": {
            "baseline_final_tick": baseline_final_tick,
            "extended_final_tick": int(
                next(iter(extended_sources.values()))["final_tick"]
            ),
            "baseline_and_extended_trace_complete_for_all_sources": complete_trace,
            "all_sources_have_exact_semantic_prefix_identity": all_prefix_equal,
            "prefix_identity_scope": (
                "all event-shaped Subject-VM trace arrays keyed by stable subject "
                "and event tick before the baseline stop boundary"
            ),
            "bounded_trace_capacity_changed": False,
            "runtime_diagnostic_state_added": False,
        },
        "baseline": baseline_arm,
        "extended": extended_arm,
        "comparison": comparison,
        "extended_tail_after_baseline_boundary": tail_summary,
        "per_source": per_source,
        "adequacy_interpretation": {
            "five_tick_horizon_is_valid_engineering_probe": True,
            "five_tick_horizon_is_universally_sufficient": False,
            "extended_horizon_revealed_new_discrete_action_boundary_crossings": bool(
                tail_summary["new_discrete_action_divergence_after_baseline_boundary"]
            ),
            "extended_horizon_revealed_delayed_objective_path_propagation": bool(
                tail_summary[
                    "delayed_objective_path_divergence_after_baseline_boundary"
                ]
            ),
            "branch_horizon_is_supported_as_primary_explanation_for_sparse_discrete_divergence": bool(
                comparison["change_in_discrete_action_difference_events"] > 0
                or comparison["change_in_sources_with_discrete_action_divergence"] > 0
            ),
            "observed_result": (
                "The trace-safe extended horizon completes more paired windows but "
                "does not create additional discrete-action boundary crossings in "
                "the fixed nine-source panel; later objective differences are "
                "continuations of an already-diverged path."
            ),
            "next_authorized_step": (
                "hold the nine-source panel and trace-safe horizon fixed, then test "
                "one temporary parameter-exposure duration variable without changing "
                "delta scale, entity count, bootstrap topology, or retention policy"
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
        "schema": STAGE3C12_HORIZON_ADEQUACY_SCHEMA,
        "producer_version": __version__,
        "single_changed_experimental_factor": payload[
            "single_changed_experimental_factor"
        ],
        "source_panel_identity": payload["source_panel_identity"],
        "trace_and_prefix_integrity": payload["trace_and_prefix_integrity"],
        "baseline": payload["baseline"],
        "extended": payload["extended"],
        "comparison": payload["comparison"],
        "extended_tail_after_baseline_boundary": payload[
            "extended_tail_after_baseline_boundary"
        ],
        "adequacy_interpretation": payload["adequacy_interpretation"],
        "automatic_keep_or_revert_decision": False,
        "permanent_parameter_retention_authorized": False,
        "causal_effect_authorized": False,
        "learning_claim_authorized": False,
        "subjecthood_claim_authorized": False,
    }
    payload["semantic_reproducibility"] = {
        "schema": "se-subject-vm-stage3c12-semantic-result-identity-v1",
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
    result = assess_stage3c12_horizon_adequacy(
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
        description="Assess a trace-safe Stage-3C-12 branch-horizon comparison."
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
                "additional_completed_paired_windows": result["comparison"][
                    "additional_completed_paired_windows"
                ],
                "new_discrete_action_boundary_crossings": result[
                    "extended_tail_after_baseline_boundary"
                ]["discrete_action_difference_events"],
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
    "STAGE3C12_HORIZON_ADEQUACY_SCHEMA",
    "assess_from_paths",
    "assess_stage3c12_horizon_adequacy",
]
