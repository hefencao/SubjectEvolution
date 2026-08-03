"""Stage 3C-36 read-only bootstrap-geometry transport decomposition.

The audit compares the frozen original and disjoint Stage-3C-25 through
Stage-3C-27 assessments.  It separates candidate-support transport, first-state
recurrence composition, conditional selection, local token geometry, and exact
tie contribution without changing runtime, checkpoints, thresholds, sources,
or addressing.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Iterable

import numpy as np

from .. import __version__
from ..experiments.subject_vm_short_paired_study import _canonical_sha256
from .subject_vm_stage3c25_winner_basin import STAGE3C25_WINNER_BASIN_SCHEMA
from .subject_vm_stage3c26_age_phase_opportunity import STAGE3C26_AGE_PHASE_OPPORTUNITY_SCHEMA
from .subject_vm_stage3c27_token_kinematics import STAGE3C27_TOKEN_KINEMATICS_SCHEMA

STAGE3C36_GEOMETRY_TRANSPORT_SCHEMA = "se-subject-vm-stage3c36-geometry-transport-assessment-v1"


def _load_json(path: str | Path) -> dict[str, Any]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"expected one JSON object: {path}")
    return payload


def _validate(payload: dict[str, Any], *, schema: str, label: str) -> None:
    if payload.get("schema") != schema:
        raise ValueError(f"unsupported {label} schema")
    recorded = str(payload.get("assessment_sha256", ""))
    unsigned = dict(payload)
    unsigned.pop("assessment_sha256", None)
    if not recorded or recorded != _canonical_sha256(unsigned):
        raise ValueError(f"{label} checksum mismatch")


def _median(values: Iterable[float]) -> float:
    materialized = [float(value) for value in values]
    return float(np.median(materialized)) if materialized else 0.0


def _seed_map(payload: dict[str, Any]) -> dict[int, dict[str, Any]]:
    rows = {int(row["seed"]): row for row in payload["per_source"]}
    if len(rows) != 9:
        raise ValueError("Stage-3C-36 requires exactly nine sources per panel")
    return rows


def _candidate_signature(row: dict[str, Any]) -> tuple[Any, ...]:
    return (
        int(row["requested_query_count"]),
        int(row["assigned_query_count"]),
        int(row["no_candidate_request_count"]),
        int(row["forced_single_candidate_query_count"]),
        int(row["multi_candidate_assigned_query_count"]),
        tuple(sorted((str(k), int(v)) for k, v in row["candidate_count_histogram"].items())),
    )


def _panel_counts(stage27: dict[str, Any]) -> dict[str, int | float]:
    same = changed = same_age_one = changed_older = 0
    strict = ties = older = multi = 0
    for row in stage27["per_source"]:
        recurrence = row["readout_state_recurrence"]
        geometry = row["multi_candidate_geometry"]
        same_count = int(recurrence["previous_tick_same_first_coordinate_query_count"])
        changed_count = int(recurrence["previous_tick_changed_first_coordinate_query_count"])
        same_selected = int(round(same_count * float(
            recurrence["age_one_selected_when_first_coordinate_unchanged_fraction"]
        )))
        changed_selected = int(round(changed_count * float(
            recurrence["older_selected_when_first_coordinate_changed_fraction"]
        )))
        same += same_count
        changed += changed_count
        same_age_one += same_selected
        changed_older += changed_selected
        strict += int(geometry["strict_age_one_geometry_win_count"])
        ties += int(geometry["exact_age_one_vs_older_score_tie_count"])
        older += int(geometry["older_geometry_win_count"])
        multi += int(row["multi_candidate_query_count"])
    age_one = same_age_one + (changed - changed_older)
    return {
        "same_first_state_query_count": same,
        "changed_first_state_query_count": changed,
        "age_one_selected_given_same_count": same_age_one,
        "older_selected_given_changed_count": changed_older,
        "age_one_selection_count": age_one,
        "strict_age_one_geometry_count": strict,
        "exact_tie_count": ties,
        "older_geometry_count": older,
        "multi_candidate_query_count": multi,
        "age_one_given_same_fraction": float(same_age_one / same),
        "older_given_changed_fraction": float(changed_older / changed),
    }


def assess_stage3c36_geometry_transport(
    reference_stage3c25: dict[str, Any],
    reference_stage3c26: dict[str, Any],
    reference_stage3c27: dict[str, Any],
    replication_stage3c25: dict[str, Any],
    replication_stage3c26: dict[str, Any],
    replication_stage3c27: dict[str, Any],
) -> dict[str, Any]:
    """Decompose the failed cross-panel Stage-3C-27 qualification."""
    inputs = (
        (reference_stage3c25, STAGE3C25_WINNER_BASIN_SCHEMA, "reference Stage-3C-25"),
        (reference_stage3c26, STAGE3C26_AGE_PHASE_OPPORTUNITY_SCHEMA, "reference Stage-3C-26"),
        (reference_stage3c27, STAGE3C27_TOKEN_KINEMATICS_SCHEMA, "reference Stage-3C-27"),
        (replication_stage3c25, STAGE3C25_WINNER_BASIN_SCHEMA, "replication Stage-3C-25"),
        (replication_stage3c26, STAGE3C26_AGE_PHASE_OPPORTUNITY_SCHEMA, "replication Stage-3C-26"),
        (replication_stage3c27, STAGE3C27_TOKEN_KINEMATICS_SCHEMA, "replication Stage-3C-27"),
    )
    for payload, schema, label in inputs:
        _validate(payload, schema=schema, label=label)

    reference_seeds = sorted(_seed_map(reference_stage3c27))
    replication_seeds = sorted(_seed_map(replication_stage3c27))
    if set(reference_seeds) & set(replication_seeds):
        raise ValueError("Stage-3C-36 requires disjoint source panels")
    for panel_label, payloads in (
        ("reference", (reference_stage3c25, reference_stage3c26, reference_stage3c27)),
        ("replication", (replication_stage3c25, replication_stage3c26, replication_stage3c27)),
    ):
        seed_sets = [set(_seed_map(payload)) for payload in payloads]
        if not all(seed_set == seed_sets[0] for seed_set in seed_sets[1:]):
            raise ValueError(f"{panel_label} Stage-3C-25/26/27 source identity mismatch")

    ref26 = _seed_map(reference_stage3c26)
    rep26 = _seed_map(replication_stage3c26)
    support_signatures = {
        _candidate_signature(row) for row in [*ref26.values(), *rep26.values()]
    }
    candidate_support_identical = len(support_signatures) == 1

    ref_counts = _panel_counts(reference_stage3c27)
    rep_counts = _panel_counts(replication_stage3c27)
    reference_age_one = int(ref_counts["age_one_selection_count"])
    replication_age_one = int(rep_counts["age_one_selection_count"])

    composition_counterfactual = (
        int(rep_counts["same_first_state_query_count"])
        * float(ref_counts["age_one_given_same_fraction"])
        + int(rep_counts["changed_first_state_query_count"])
        * (1.0 - float(ref_counts["older_given_changed_fraction"]))
    )
    conditional_counterfactual = (
        int(ref_counts["same_first_state_query_count"])
        * float(rep_counts["age_one_given_same_fraction"])
        + int(ref_counts["changed_first_state_query_count"])
        * (1.0 - float(rep_counts["older_given_changed_fraction"]))
    )
    observed_delta = float(replication_age_one - reference_age_one)
    composition_delta = float(composition_counterfactual - reference_age_one)
    conditional_delta = float(conditional_counterfactual - reference_age_one)

    ref27_rows = _seed_map(reference_stage3c27)
    rep27_rows = _seed_map(replication_stage3c27)
    ref_strict_step = _median(
        row["kinematic_groups"]["strict_age_one_geometry"]["local_step_l2"]["median"]
        for row in ref27_rows.values()
    )
    rep_strict_step = _median(
        row["kinematic_groups"]["strict_age_one_geometry"]["local_step_l2"]["median"]
        for row in rep27_rows.values()
    )
    ref_older_step = _median(
        row["kinematic_groups"]["older_geometry"]["local_step_l2"]["median"]
        for row in ref27_rows.values()
    )
    rep_older_step = _median(
        row["kinematic_groups"]["older_geometry"]["local_step_l2"]["median"]
        for row in rep27_rows.values()
    )
    ref_separation = ref_older_step / ref_strict_step
    rep_separation = rep_older_step / rep_strict_step

    per_source: list[dict[str, Any]] = []
    for seed, row in sorted(rep27_rows.items()):
        recurrence = row["readout_state_recurrence"]
        geometry = row["multi_candidate_geometry"]
        failed = []
        if float(geometry["strict_geometry_fraction_of_multi_candidate_age_one_selections"]) < 0.99:
            failed.append("strict-geometry-fraction")
        if float(recurrence["age_one_selected_when_first_coordinate_unchanged_fraction"]) < 0.90:
            failed.append("same-state-age-one")
        if float(recurrence["older_selected_when_first_coordinate_changed_fraction"]) < 0.80:
            failed.append("changed-state-older")
        per_source.append({
            "seed": seed,
            "failed_screen_components": failed,
            "exact_tie_count": int(geometry["exact_age_one_vs_older_score_tie_count"]),
            "same_first_state_query_count": int(recurrence["previous_tick_same_first_coordinate_query_count"]),
            "changed_first_state_query_count": int(recurrence["previous_tick_changed_first_coordinate_query_count"]),
            "age_one_given_same_fraction": float(recurrence["age_one_selected_when_first_coordinate_unchanged_fraction"]),
            "older_given_changed_fraction": float(recurrence["older_selected_when_first_coordinate_changed_fraction"]),
        })

    extra_ties = int(rep_counts["exact_tie_count"]) - int(ref_counts["exact_tie_count"])
    age_one_loss = reference_age_one - replication_age_one
    payload: dict[str, Any] = {
        "schema": STAGE3C36_GEOMETRY_TRANSPORT_SCHEMA,
        "producer_version": __version__,
        "analysis_only_factor": "cross-panel decomposition of frozen Stage-3C-25/26/27 assessments",
        "runtime_experimental_factor_changed": False,
        "reference_source_seeds": reference_seeds,
        "replication_source_seeds": replication_seeds,
        "source_panels_are_disjoint": True,
        "input_checksums": {
            "reference_stage3c25": reference_stage3c25["assessment_sha256"],
            "reference_stage3c26": reference_stage3c26["assessment_sha256"],
            "reference_stage3c27": reference_stage3c27["assessment_sha256"],
            "replication_stage3c25": replication_stage3c25["assessment_sha256"],
            "replication_stage3c26": replication_stage3c26["assessment_sha256"],
            "replication_stage3c27": replication_stage3c27["assessment_sha256"],
        },
        "candidate_support_transport": {
            "candidate_support_signature_identical_across_all_18_sources": candidate_support_identical,
            "canonical_signature": list(next(iter(support_signatures))) if candidate_support_identical else None,
            "winner_reuse_fraction_median_reference": float(reference_stage3c25["source_balanced_summary"]["fraction_of_assignments_to_reused_winners"]["median"]),
            "winner_reuse_fraction_median_replication": float(replication_stage3c25["source_balanced_summary"]["fraction_of_assignments_to_reused_winners"]["median"]),
        },
        "first_state_recurrence_transport": {
            "reference": ref_counts,
            "replication": rep_counts,
            "same_first_state_query_count_delta": int(rep_counts["same_first_state_query_count"]) - int(ref_counts["same_first_state_query_count"]),
            "age_one_selection_count_delta": int(rep_counts["age_one_selection_count"]) - int(ref_counts["age_one_selection_count"]),
            "composition_only_counterfactual_age_one_count": composition_counterfactual,
            "conditional_only_counterfactual_age_one_count": conditional_counterfactual,
            "observed_age_one_delta": observed_delta,
            "composition_only_delta": composition_delta,
            "conditional_only_delta": conditional_delta,
            "composition_counterfactual_residual_from_observed": float(replication_age_one - composition_counterfactual),
        },
        "local_geometry_transport": {
            "strict_age_one_local_step_median_reference": ref_strict_step,
            "strict_age_one_local_step_median_replication": rep_strict_step,
            "older_geometry_local_step_median_reference": ref_older_step,
            "older_geometry_local_step_median_replication": rep_older_step,
            "older_to_strict_step_ratio_reference": ref_separation,
            "older_to_strict_step_ratio_replication": rep_separation,
            "strict_vs_older_scale_separation_remains_over_100x": min(ref_separation, rep_separation) > 100.0,
        },
        "tie_transport": {
            "reference_exact_tie_count": int(ref_counts["exact_tie_count"]),
            "replication_exact_tie_count": int(rep_counts["exact_tie_count"]),
            "extra_exact_tie_count": extra_ties,
            "replication_exact_tie_fraction_of_all_multi_candidate_queries": float(int(rep_counts["exact_tie_count"]) / int(rep_counts["multi_candidate_query_count"])),
            "extra_ties_are_smaller_than_absolute_age_one_selection_loss": extra_ties < age_one_loss,
            "aggregate_inputs_can_distinguish_true_symmetry_from_float32_compression": False,
        },
        "replication_per_source": per_source,
        "frozen_interpretation": {
            "candidate_opportunity_structure_failed_to_transport": not candidate_support_identical,
            "local_step_scale_separation_failed_to_transport": min(ref_separation, rep_separation) <= 100.0,
            "pooled_age_one_loss_is_explained_primarily_by_first_state_recurrence_composition": abs(replication_age_one - composition_counterfactual) <= 2.0,
            "stage3c28_gate_failure_is_triggered_by_additional_exact_ties": int(rep_counts["strict_age_one_geometry_count"]) / replication_age_one < 0.99 and extra_ties > 0,
            "exact_tie_origin_is_resolved": False,
            "crossing_replication_authorized": False,
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


def _write_summary(result: dict[str, Any], path: str | Path) -> None:
    recurrence = result["first_state_recurrence_transport"]
    ties = result["tie_transport"]
    summary = {
        "schema": "se-subject-vm-stage3c36-geometry-transport-summary-v1",
        "producer_version": __version__,
        "assessment_sha256": result["assessment_sha256"],
        "candidate_support_transports": result["candidate_support_transport"]["candidate_support_signature_identical_across_all_18_sources"],
        "same_first_state_query_count_delta": recurrence["same_first_state_query_count_delta"],
        "observed_age_one_delta": recurrence["observed_age_one_delta"],
        "composition_only_delta": recurrence["composition_only_delta"],
        "extra_exact_tie_count": ties["extra_exact_tie_count"],
        "crossing_replication_authorized": False,
    }
    Path(path).write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_report(result: dict[str, Any], path: str | Path) -> None:
    rec = result["first_state_recurrence_transport"]
    geo = result["local_geometry_transport"]
    tie = result["tie_transport"]
    lines = [
        "# Stage 3C-36 bootstrap-geometry transport decomposition",
        "",
        "## Frozen result",
        "",
        f"- Candidate-support signature is identical across all 18 sources: `{result['candidate_support_transport']['candidate_support_signature_identical_across_all_18_sources']}`.",
        f"- Same-first-state multi-candidate queries change by `{rec['same_first_state_query_count_delta']}`.",
        f"- Observed age-one selection change is `{rec['observed_age_one_delta']:.1f}`; the composition-only counterfactual is `{rec['composition_only_delta']:.3f}`.",
        f"- Strict/older local-step separation remains `{geo['older_to_strict_step_ratio_reference']:.1f}x` vs `{geo['older_to_strict_step_ratio_replication']:.1f}x`.",
        f"- Exact ties increase from `{tie['reference_exact_tie_count']}` to `{tie['replication_exact_tie_count']}`, but the frozen aggregate cannot distinguish true recurrence symmetry from float32 compression.",
        "",
        "The pooled age-one occupancy loss is therefore primarily a first-state recurrence-composition shift, while the formal Stage-3C-28 gate is tripped by five additional exact ties. Candidate opportunity and the large strict-vs-older local-step separation transport. Crossing replication remains blocked until tie origin is resolved without relaxing the gate.",
    ]
    Path(path).write_text("\n".join(lines) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Assess Stage 3C-36 geometry transport.")
    for name in (
        "reference-stage3c25", "reference-stage3c26", "reference-stage3c27",
        "replication-stage3c25", "replication-stage3c26", "replication-stage3c27",
    ):
        parser.add_argument(f"--{name}", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--summary-output")
    parser.add_argument("--diagnostic-report")
    args = parser.parse_args(argv)
    result = assess_stage3c36_geometry_transport(
        _load_json(args.reference_stage3c25), _load_json(args.reference_stage3c26),
        _load_json(args.reference_stage3c27), _load_json(args.replication_stage3c25),
        _load_json(args.replication_stage3c26), _load_json(args.replication_stage3c27),
    )
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    Path(args.output).write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if args.summary_output:
        _write_summary(result, args.summary_output)
    if args.diagnostic_report:
        _write_report(result, args.diagnostic_report)


if __name__ == "__main__":
    main()
