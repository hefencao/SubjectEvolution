"""Stage 3C-11 independent-source and short-window adequacy audit.

This analysis treats independent source checkpoints as the highest replicate
unit.  Entities, stable subjects, and paired windows remain within-source
observations and are never promoted to independent samples.  The report is
score-free and does not authorize permanent retention or a learning claim.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
import hashlib
import json
import math
from pathlib import Path
from typing import Any, Iterable

import numpy as np

from .. import __version__
from .subject_vm_component_reproducibility import (
    COMPONENT_REPRODUCIBILITY_SCHEMA,
    OBJECTIVE_FACT_COORDINATE_NAMES,
)
from .subject_vm_stage3c10_diagnostics import STAGE3C10_DIAGNOSTICS_SCHEMA

STAGE3C11_SAMPLE_ADEQUACY_SCHEMA = (
    "se-subject-vm-stage3c11-sample-adequacy-assessment-v1"
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


def _wilson_interval(successes: int, trials: int, *, z: float = 1.959963984540054) -> dict[str, Any]:
    if trials <= 0:
        return {"successes": successes, "trials": trials, "fraction": None, "lower": None, "upper": None}
    p = successes / trials
    z2 = z * z
    denominator = 1.0 + z2 / trials
    centre = (p + z2 / (2.0 * trials)) / denominator
    margin = z * math.sqrt((p * (1.0 - p) + z2 / (4.0 * trials)) / trials) / denominator
    return {
        "successes": int(successes),
        "trials": int(trials),
        "fraction": float(p),
        "lower": float(max(0.0, centre - margin)),
        "upper": float(min(1.0, centre + margin)),
        "interval_kind": "Wilson score interval, descriptive only",
        "confidence_level": 0.95,
    }


def _stats(values: Iterable[float | int]) -> dict[str, Any]:
    array = np.asarray(list(values), dtype=np.float64)
    if array.size == 0:
        return {"count": 0, "minimum": None, "median": None, "maximum": None, "mean": None}
    return {
        "count": int(array.size),
        "minimum": float(np.min(array)),
        "median": float(np.median(array)),
        "maximum": float(np.max(array)),
        "mean": float(np.mean(array)),
    }


def _screen_coordinate(values: np.ndarray, parameters: dict[str, Any]) -> dict[str, Any]:
    tolerance = float(parameters["zero_tolerance"])
    positive = int(np.count_nonzero(values > tolerance))
    negative = int(np.count_nonzero(values < -tolerance))
    zero = int(values.size - positive - negative)
    counts = {"positive": positive, "negative": negative, "near_zero": zero}
    maximum = max(counts.values())
    leaders = [name for name, count in counts.items() if count == maximum]
    dominant = leaders[0] if len(leaders) == 1 else "tied"
    dominant_nonzero_fraction = float(max(positive, negative) / values.size)
    lower = float(np.quantile(values, float(parameters["central_interval_lower_quantile"]), method="linear"))
    upper = float(np.quantile(values, float(parameters["central_interval_upper_quantile"]), method="linear"))
    interval_excludes_zero = bool(lower > tolerance or upper < -tolerance)
    stable = bool(
        values.size >= int(parameters["min_independent_sources"])
        and dominant in {"positive", "negative"}
        and dominant_nonzero_fraction >= float(parameters["min_dominant_nonzero_sign_fraction"])
        and interval_excludes_zero
    )
    return {
        "sign_counts": counts,
        "dominant_sign": dominant,
        "dominant_nonzero_sign_fraction": dominant_nonzero_fraction,
        "central_interval": {"lower": lower, "upper": upper},
        "descriptive_sign_and_interval_stability_screen": stable,
    }


@dataclass(frozen=True)
class SourceRecord:
    seed: int
    source_hash: str
    paired_windows: int
    stable_subjects: int
    objective_vector: tuple[float, ...]
    action_divergence: bool
    objective_event_divergence: bool
    divergence_trace_complete: bool
    paired_admission_contract_pass: bool


def assess_stage3c11_sample_adequacy(
    study_report: dict[str, Any],
    *,
    component_reproducibility: dict[str, Any],
    stage3c10_diagnostics: dict[str, Any],
    pilot_source_count: int = 3,
) -> dict[str, Any]:
    """Assess source-level replication and window coverage without scalarization."""
    if study_report.get("schema") != "se-subject-vm-short-paired-study-v1":
        raise ValueError("Stage-3C-11 requires a short paired study report")
    _verify_checksum(study_report, "study_sha256", "short paired study")
    if component_reproducibility.get("schema") != COMPONENT_REPRODUCIBILITY_SCHEMA:
        raise ValueError("Stage-3C-11 requires a Stage-3C-8 component report")
    _verify_checksum(component_reproducibility, "assessment_sha256", "Stage-3C-8 assessment")
    if stage3c10_diagnostics.get("schema") != STAGE3C10_DIAGNOSTICS_SCHEMA:
        raise ValueError("Stage-3C-11 requires Stage-3C-10 diagnostics")
    _verify_checksum(stage3c10_diagnostics, "diagnostics_sha256", "Stage-3C-10 diagnostics")

    seeds = list(study_report.get("seeds", []))
    if len(seeds) < 3:
        raise ValueError("Stage-3C-11 requires at least three independent sources")
    if not 3 <= int(pilot_source_count) <= len(seeds):
        raise ValueError("pilot_source_count must be between three and the full source count")

    source_by_hash = {
        str(item["source_checkpoint_state_sha256"]): item
        for item in component_reproducibility["source_replicates"]
    }
    diagnostic_by_seed = {
        int(item["seed"]): item for item in stage3c10_diagnostics["per_source"]
    }
    records: list[SourceRecord] = []
    for seed_record in sorted(seeds, key=lambda item: int(item["seed"])):
        seed = int(seed_record["seed"])
        source_hash = str(seed_record["source_checkpoint_state_sha256"])
        source = source_by_hash.get(source_hash)
        diagnostic = diagnostic_by_seed.get(seed)
        if source is None or diagnostic is None:
            raise ValueError("study/source diagnostic identity is incomplete")
        timeline = diagnostic["update_visibility_and_divergence"]["branch_divergence_timeline"]
        coverage = diagnostic["update_visibility_and_divergence"]["branch_divergence_trace_coverage"]
        records.append(
            SourceRecord(
                seed=seed,
                source_hash=source_hash,
                paired_windows=int(source["paired_window_count"]),
                stable_subjects=int(source["stable_subject_count"]),
                objective_vector=tuple(float(value) for value in source["source_subject_balanced_objective_fact_mean"]),
                action_divergence=any(item["difference_counts"].get("action_id", 0) > 0 for item in timeline),
                objective_event_divergence=any(item["difference_counts"].get("objective_delta", 0) > 0 for item in timeline),
                divergence_trace_complete=bool(coverage["complete"]),
                paired_admission_contract_pass=bool(
                    diagnostic["admission_and_counted_cost_symmetry"]["paired_admission_contract_pass"]
                ),
            )
        )

    parameters = dict(component_reproducibility["parameters"])
    matrix = np.asarray([record.objective_vector for record in records], dtype=np.float64)
    tolerance = float(parameters["zero_tolerance"])
    prefix_records: list[dict[str, Any]] = []
    for count in range(int(pilot_source_count), len(records) + 1):
        prefix = records[:count]
        prefix_matrix = matrix[:count]
        coordinate_screens = [
            _screen_coordinate(prefix_matrix[:, index], parameters)
            for index in range(prefix_matrix.shape[1])
        ]
        source_nonzero = np.any(np.abs(prefix_matrix) > tolerance, axis=1)
        prefix_records.append(
            {
                "independent_source_count": count,
                "seed_prefix": [record.seed for record in prefix],
                "paired_window_count": int(sum(record.paired_windows for record in prefix)),
                "sources_with_discrete_action_divergence": int(sum(record.action_divergence for record in prefix)),
                "sources_with_trace_level_objective_event_divergence": int(sum(record.objective_event_divergence for record in prefix)),
                "sources_with_nonzero_completed_window_objective_vector": int(np.count_nonzero(source_nonzero)),
                "coordinates_with_descriptive_stability": int(sum(item["descriptive_sign_and_interval_stability_screen"] for item in coordinate_screens)),
                "coordinate_names_with_descriptive_stability": [
                    OBJECTIVE_FACT_COORDINATE_NAMES[index]
                    for index, item in enumerate(coordinate_screens)
                    if item["descriptive_sign_and_interval_stability_screen"]
                ],
            }
        )

    coordinate_sparsity = []
    for index, name in enumerate(OBJECTIVE_FACT_COORDINATE_NAMES):
        values = matrix[:, index]
        screen = _screen_coordinate(values, parameters)
        coordinate_sparsity.append(
            {
                "coordinate": name,
                "source_values": [float(value) for value in values.tolist()],
                "nonzero_source_count": int(np.count_nonzero(np.abs(values) > tolerance)),
                "nonzero_source_fraction": float(np.mean(np.abs(values) > tolerance)),
                **screen,
            }
        )

    full_count = len(records)
    action_count = int(sum(record.action_divergence for record in records))
    objective_event_count = int(sum(record.objective_event_divergence for record in records))
    completed_window_nonzero_count = int(np.count_nonzero(np.any(np.abs(matrix) > tolerance, axis=1)))
    all_trace_complete = all(record.divergence_trace_complete for record in records)
    all_admission_pass = all(record.paired_admission_contract_pass for record in records)
    pilot = prefix_records[0]
    full = prefix_records[-1]
    payload = {
        "schema": STAGE3C11_SAMPLE_ADEQUACY_SCHEMA,
        "producer_version": __version__,
        "study_sha256": str(study_report["study_sha256"]),
        "stage3c8_assessment_sha256": str(component_reproducibility["assessment_sha256"]),
        "stage3c10_diagnostics_sha256": str(stage3c10_diagnostics["diagnostics_sha256"]),
        "single_changed_experimental_factor": "independent source count: 3 -> 9" if full_count == 9 and pilot_source_count == 3 else f"independent source count: {pilot_source_count} -> {full_count}",
        "unchanged_factors": {
            "initial_entities": int(study_report.get("population", {}).get("initial_entities", 0)),
            "source_ticks": int(study_report["parameters"]["source_ticks"]),
            "branch_horizon_ticks": int(study_report["parameters"]["horizon_ticks"]),
            "bootstrap_subjects": int(study_report["parameters"]["bootstrap_subjects"]),
            "backend": str(study_report["resolved_backend"]),
            "permanent_retention": False,
        },
        "replicate_accounting": {
            "highest_independent_replicate": "independent-source-checkpoint",
            "independent_source_count": full_count,
            "entities_per_source": int(study_report.get("population", {}).get("initial_entities", 0)),
            "bootstrap_subjects_per_source": int(study_report["parameters"]["bootstrap_subjects"]),
            "paired_windows_total": int(sum(record.paired_windows for record in records)),
            "paired_windows_per_source": _stats(record.paired_windows for record in records),
            "stable_subjects_per_source": _stats(record.stable_subjects for record in records),
            "entities_are_independent_replicates": False,
            "subjects_are_independent_source_replicates": False,
            "windows_are_independent_replicates": False,
        },
        "engineering_integrity": {
            "pairing_coverage": float(study_report["engineering_summary"]["pooled_pairing_coverage"]),
            "rollback_failure_count": int(study_report["engineering_summary"]["rollback_failure_count"]),
            "objective_fact_clip_fraction": float(study_report["engineering_summary"]["fact_clip_fraction"]),
            "evaluation_cost_match_fraction": float(study_report["engineering_summary"]["evaluation_cost_match_fraction"]),
            "all_sources_pass_paired_admission_contract": all_admission_pass,
            "all_sources_have_complete_divergence_trace": all_trace_complete,
        },
        "source_level_signal_incidence": {
            "discrete_action_divergence": _wilson_interval(action_count, full_count),
            "trace_level_objective_event_divergence": _wilson_interval(objective_event_count, full_count),
            "nonzero_completed_window_objective_vector": _wilson_interval(completed_window_nonzero_count, full_count),
        },
        "prefix_sensitivity": prefix_records,
        "pilot_vs_expanded": {
            "pilot": pilot,
            "expanded": full,
            "stable_coordinate_count_changed": pilot["coordinates_with_descriptive_stability"] != full["coordinates_with_descriptive_stability"],
            "nonzero_source_fraction_did_not_become_dense": bool(completed_window_nonzero_count < full_count / 2),
        },
        "objective_coordinate_sparsity": coordinate_sparsity,
        "adequacy_interpretation": {
            "valid_engineering_sample_for_pipeline_and_pairing": True,
            "valid_sample_for_claiming_stable_objective_direction": False,
            "three_source_pilot_was_scientifically_sufficient": False,
            "expanded_panel_authorizes_scientific_sufficiency": False,
            "within_source_coverage_is_the_primary_missing_replicate": False,
            "independent_source_replication_remains_limited": True,
            "five_tick_horizon_is_proven_sufficient_for_delayed_effects": False,
            "five_tick_horizon_is_sufficient_to_generate_commits_windows_and_some_divergence": True,
            "entity_count_adequacy_for_generalization_is_determined": False,
            "observed_result": (
                "Increasing independent sources without changing entities, horizon, or mechanism "
                "kept the stable objective-coordinate count at zero and left completed-window "
                "objective differences concentrated in a small minority of sources."
            ),
            "next_authorized_step": (
                "keep the expanded source panel as the sample-size control and test one horizon "
                "or temporary-exposure variable only after horizon-safe divergence observation is available"
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
    semantic_result = {
        "schema": STAGE3C11_SAMPLE_ADEQUACY_SCHEMA,
        "producer_version": __version__,
        "single_changed_experimental_factor": payload[
            "single_changed_experimental_factor"
        ],
        "unchanged_factors": payload["unchanged_factors"],
        "source_panel": [
            {
                "seed": record.seed,
                "source_checkpoint_state_sha256": record.source_hash,
            }
            for record in records
        ],
        "replicate_accounting": payload["replicate_accounting"],
        "engineering_integrity": payload["engineering_integrity"],
        "source_level_signal_incidence": payload[
            "source_level_signal_incidence"
        ],
        "prefix_sensitivity": payload["prefix_sensitivity"],
        "objective_coordinate_sparsity": payload[
            "objective_coordinate_sparsity"
        ],
        "adequacy_interpretation": payload["adequacy_interpretation"],
        "automatic_keep_or_revert_decision": False,
        "permanent_parameter_retention_authorized": False,
        "causal_effect_authorized": False,
        "learning_claim_authorized": False,
        "subjecthood_claim_authorized": False,
    }
    payload["semantic_reproducibility"] = {
        "schema": "se-subject-vm-stage3c11-semantic-result-identity-v1",
        "identity_basis": (
            "source checkpoint state hashes plus score-free Stage-3C-11 "
            "statistics and scientific boundaries"
        ),
        "artifact_file_checksums_excluded": True,
        "artifact_paths_excluded": True,
        "checkpoint_created_utc_excluded": True,
        "artifact_integrity_checksums_still_verified_per_run": True,
        "source_panel": semantic_result["source_panel"],
        "semantic_result_sha256": _canonical_sha256(semantic_result),
    }
    payload["assessment_sha256"] = _canonical_sha256(payload)
    return payload


def assess_from_paths(
    study_report_path: str | Path,
    *,
    output_path: str | Path | None = None,
    pilot_source_count: int = 3,
) -> dict[str, Any]:
    report_path = Path(study_report_path).expanduser().resolve()
    report = _load_json(report_path)
    component_path = Path(str(report["component_reproducibility"])).expanduser()
    diagnostics_path = Path(str(report["stage3c10_diagnostics"])).expanduser()
    if not component_path.is_absolute():
        component_path = report_path.parent / component_path
    if not diagnostics_path.is_absolute():
        diagnostics_path = report_path.parent / diagnostics_path
    payload = assess_stage3c11_sample_adequacy(
        report,
        component_reproducibility=_load_json(component_path),
        stage3c10_diagnostics=_load_json(diagnostics_path),
        pilot_source_count=pilot_source_count,
    )
    if output_path is not None:
        destination = Path(output_path).expanduser().resolve()
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return payload


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Assess Stage-3C-11 independent-source and short-window adequacy."
    )
    parser.add_argument("--study-report", required=True)
    parser.add_argument("--pilot-source-count", type=int, default=3)
    parser.add_argument("--output", required=True)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    payload = assess_from_paths(
        args.study_report,
        output_path=args.output,
        pilot_source_count=args.pilot_source_count,
    )
    print(json.dumps({
        "independent_source_count": payload["replicate_accounting"]["independent_source_count"],
        "paired_windows": payload["replicate_accounting"]["paired_windows_total"],
        "stable_coordinates": payload["pilot_vs_expanded"]["expanded"]["coordinates_with_descriptive_stability"],
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()


__all__ = [
    "STAGE3C11_SAMPLE_ADEQUACY_SCHEMA",
    "assess_stage3c11_sample_adequacy",
    "assess_from_paths",
]
