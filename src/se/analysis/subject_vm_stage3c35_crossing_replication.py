"""Stage 3C-35 disjoint-source crossing-taxonomy replication.

This assessment consumes a Stage-3C-34 crossing audit produced from a source
panel disjoint from the frozen Stage-3C-34 panel.  It evaluates the preregistered
source-level classifier without changing runtime state, exposure, addressing,
or Objective-Fact semantics.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from .. import __version__
from ..experiments.subject_vm_short_paired_study import _canonical_sha256
from .subject_vm_stage3c27_token_kinematics import STAGE3C27_TOKEN_KINEMATICS_SCHEMA
from .subject_vm_stage3c34_threshold_crossing import (
    STAGE3C34_THRESHOLD_CROSSING_ASSESSMENT_SCHEMA,
)

STAGE3C35_CROSSING_REPLICATION_ASSESSMENT_SCHEMA = (
    "se-subject-vm-stage3c35-crossing-replication-assessment-v1"
)


def _load_json(path: str | Path) -> dict[str, Any]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"expected one JSON object: {path}")
    return payload


def _validate_checksum(payload: dict[str, Any], *, field: str, label: str) -> None:
    recorded = str(payload.get(field, ""))
    unsigned = dict(payload)
    unsigned.pop(field, None)
    if not recorded or recorded != _canonical_sha256(unsigned):
        raise ValueError(f"{label} checksum mismatch")



def assess_stage3c35_source_qualification(
    reference_decision: dict[str, Any],
    reference_stage3c27_assessment: dict[str, Any],
    stage3c27_assessment: dict[str, Any],
) -> dict[str, Any]:
    """Freeze a preregistered stop when the upstream geometry does not replicate."""
    if reference_decision.get("schema") != (
        "se-subject-vm-stage3c34-threshold-crossing-decision-v1"
    ):
        raise ValueError("unsupported Stage-3C-34 reference decision schema")
    for label, assessment in (
        ("reference", reference_stage3c27_assessment),
        ("replication", stage3c27_assessment),
    ):
        if assessment.get("schema") != STAGE3C27_TOKEN_KINEMATICS_SCHEMA:
            raise ValueError(f"unsupported {label} Stage-3C-27 qualification schema")
        _validate_checksum(
            assessment,
            field="assessment_sha256",
            label=f"Stage-3C-35 {label} Stage-3C-27 qualification",
        )
    reference_seeds = sorted(
        int(seed) for seed in reference_decision["input_identity"]["source_seeds"]
    )
    replication_seeds = sorted(int(item["seed"]) for item in stage3c27_assessment["per_source"])
    if len(replication_seeds) != 9 or len(replication_seeds) != len(set(replication_seeds)):
        raise ValueError("Stage-3C-35 requires nine unique replication sources")
    if set(reference_seeds) & set(replication_seeds):
        raise ValueError("Stage-3C-35 requires a source panel disjoint from Stage-3C-34")

    per_source: list[dict[str, Any]] = []
    complete_source_seeds: list[int] = []
    for source in stage3c27_assessment["per_source"]:
        seed = int(source["seed"])
        geometry = source["multi_candidate_geometry"]
        recurrence = source["readout_state_recurrence"]
        strict_geometry = float(
            geometry["strict_geometry_fraction_of_multi_candidate_age_one_selections"]
        )
        unchanged_predicts_age_one = float(
            recurrence["age_one_selected_when_first_coordinate_unchanged_fraction"]
        )
        changed_predicts_older = float(
            recurrence["older_selected_when_first_coordinate_changed_fraction"]
        )
        checks = {
            "strict_geometry_at_least_0_99": strict_geometry >= 0.99,
            "unchanged_first_state_predicts_age_one_at_least_0_90": unchanged_predicts_age_one >= 0.90,
            "changed_first_state_predicts_older_at_least_0_80": changed_predicts_older >= 0.80,
        }
        complete = all(checks.values())
        if complete:
            complete_source_seeds.append(seed)
        per_source.append(
            {
                "seed": seed,
                "strict_geometry_fraction": strict_geometry,
                "unchanged_first_state_age_one_fraction": unchanged_predicts_age_one,
                "changed_first_state_older_fraction": changed_predicts_older,
                "checks": checks,
                "complete_stage3c27_source_screen": complete,
            }
        )

    findings = stage3c27_assessment["cross_source_findings"]
    reference_findings = reference_stage3c27_assessment["cross_source_findings"]
    reference_strict_fraction = (
        float(reference_findings["strict_geometry_age_one_selection_total"])
        / float(reference_findings["multi_candidate_age_one_selection_total"])
    )
    replication_strict_fraction = (
        float(findings["strict_geometry_age_one_selection_total"])
        / float(findings["multi_candidate_age_one_selection_total"])
    )
    reference_tie_fraction = (
        float(reference_findings["latest_tie_break_age_one_selection_total"])
        / float(reference_findings["multi_candidate_query_total"])
    )
    replication_tie_fraction = (
        float(findings["latest_tie_break_age_one_selection_total"])
        / float(findings["multi_candidate_query_total"])
    )
    complete_panel_screen = bool(
        stage3c27_assessment["diagnostic_interpretation"][
            "local_token_geometry_is_the_primary_multi_candidate_age_one_driver"
        ]
        and stage3c27_assessment["diagnostic_interpretation"][
            "first_readout_state_persistence_and_recurrence_contribute_to_selected_age"
        ]
    )
    # The Stage-3C-28 gate requires the first diagnostic; preserve the exact gate result.
    stage3c28_gate_passed = bool(
        stage3c27_assessment["diagnostic_interpretation"][
            "local_token_geometry_is_the_primary_multi_candidate_age_one_driver"
        ]
    )
    payload: dict[str, Any] = {
        "schema": STAGE3C35_CROSSING_REPLICATION_ASSESSMENT_SCHEMA,
        "producer_version": __version__,
        "assessment_mode": "preregistered-upstream-qualification",
        "reference_stage3c34_decision_id": str(reference_decision["decision_id"]),
        "reference_source_seeds": reference_seeds,
        "replication_source_seeds": replication_seeds,
        "source_panels_are_disjoint": True,
        "reference_stage3c27_assessment_sha256": str(
            reference_stage3c27_assessment["assessment_sha256"]
        ),
        "stage3c27_assessment_sha256": str(stage3c27_assessment["assessment_sha256"]),
        "reference_comparison": {
            "reference_stage3c28_gate_passed": bool(
                reference_stage3c27_assessment["diagnostic_interpretation"][
                    "local_token_geometry_is_the_primary_multi_candidate_age_one_driver"
                ]
            ),
            "replication_stage3c28_gate_passed": stage3c28_gate_passed,
            "reference_strict_geometry_fraction": reference_strict_fraction,
            "replication_strict_geometry_fraction": replication_strict_fraction,
            "strict_geometry_fraction_delta": (
                replication_strict_fraction - reference_strict_fraction
            ),
            "reference_latest_tie_break_fraction": reference_tie_fraction,
            "replication_latest_tie_break_fraction": replication_tie_fraction,
            "latest_tie_break_fraction_delta": (
                replication_tie_fraction - reference_tie_fraction
            ),
            "reference_strict_geometry_total": int(
                reference_findings["strict_geometry_age_one_selection_total"]
            ),
            "reference_age_one_selection_total": int(
                reference_findings["multi_candidate_age_one_selection_total"]
            ),
            "replication_strict_geometry_total": int(
                findings["strict_geometry_age_one_selection_total"]
            ),
            "replication_age_one_selection_total": int(
                findings["multi_candidate_age_one_selection_total"]
            ),
        },
        "preregistered_prediction": (
            "alignment-differential sampled-action crossing identifies every and "
            "only source with a nonzero exposure-only subject-balanced Objective-Fact effect"
        ),
        "qualification": {
            "stage3c28_gate_passed": stage3c28_gate_passed,
            "complete_panel_stage3c27_screen": complete_panel_screen,
            "complete_source_screen_seeds": complete_source_seeds,
            "complete_source_screen_count": len(complete_source_seeds),
            "strict_geometry_all_sources": bool(
                findings[
                    "strict_geometry_accounts_for_at_least_99_percent_of_multi_candidate_age_one_selections"
                ]
            ),
            "unchanged_first_state_prediction_all_sources": bool(
                findings[
                    "unchanged_first_readout_coordinate_predicts_age_one_selection_at_least_90_percent_in_all_sources"
                ]
            ),
            "changed_first_state_prediction_all_sources": bool(
                findings[
                    "changed_first_readout_coordinate_predicts_older_selection_at_least_80_percent_in_all_sources"
                ]
            ),
            "per_source": per_source,
        },
        "prediction_assessment": {
            "crossing_prediction_tested": False,
            "prediction_supported_nonvacuously": False,
            "prediction_refuted": False,
            "reason_not_tested": (
                "the disjoint panel failed the frozen Stage-3C-27 geometry prerequisite, "
                "so Stage-3C-28 correctly blocked the unchanged Stage-3C-33/34 chain"
            ),
        },
        "frozen_interpretation": {
            "upstream_geometry_transports_to_disjoint_panel": False,
            "crossing_taxonomy_can_be_evaluated_under_unchanged_chain": False,
            "failure_is_a_runtime_or_export_error": False,
            "failure_is_a_preregistered_scientific_qualification_result": True,
            "selected_seed_replacement_authorized": False,
            "gate_relaxation_authorized": False,
        },
        "governance": {
            "selected_seed_rerun_used": False,
            "source_panel_replaced_after_observation": False,
            "stage3c27_gate_relaxed": False,
            "stage3c28_or_later_executed_after_failed_gate": False,
            "exposure_changed": False,
            "addressing_changed": False,
            "scalar_objective_used": False,
        },
        "objective_coordinates_have_value_semantics": False,
        "causal_credit_quality_is_proven": False,
        "automatic_keep_or_revert_authorized": False,
        "permanent_parameter_retention_authorized": False,
        "learning_claim_authorized": False,
        "subjecthood_claim_authorized": False,
    }
    payload["assessment_sha256"] = _canonical_sha256(payload)
    return payload

def assess_stage3c35_crossing_replication(
    reference_decision: dict[str, Any],
    replication_crossing: dict[str, Any],
) -> dict[str, Any]:
    if reference_decision.get("schema") != (
        "se-subject-vm-stage3c34-threshold-crossing-decision-v1"
    ):
        raise ValueError("unsupported Stage-3C-34 reference decision schema")
    if replication_crossing.get("schema") != (
        STAGE3C34_THRESHOLD_CROSSING_ASSESSMENT_SCHEMA
    ):
        raise ValueError("unsupported replication crossing assessment schema")
    _validate_checksum(
        replication_crossing,
        field="assessment_sha256",
        label="Stage-3C-35 replication crossing assessment",
    )

    reference_seeds = sorted(
        int(seed) for seed in reference_decision["input_identity"]["source_seeds"]
    )
    replication_seeds = sorted(
        int(item["seed"]) for item in replication_crossing["per_source"]
    )
    if len(replication_seeds) != len(set(replication_seeds)):
        raise ValueError("Stage-3C-35 replication contains duplicate source seeds")
    if set(reference_seeds) & set(replication_seeds):
        raise ValueError("Stage-3C-35 requires a source panel disjoint from Stage-3C-34")
    if len(replication_seeds) != 9:
        raise ValueError("Stage-3C-35 requires the preregistered nine-source panel")

    findings = replication_crossing["cross_source_findings"]
    predictor = set(
        int(seed)
        for seed in findings[
            "sources_with_alignment_differential_action_crossing"
        ]
    )
    outcome = set(
        int(seed)
        for seed in findings[
            "sources_with_surviving_subject_balanced_fact_effect"
        ]
    )
    objective_crossing = set(
        int(seed)
        for seed in findings[
            "sources_with_alignment_differential_objective_fact_crossing"
        ]
    )
    panel = set(replication_seeds)
    if not predictor <= panel or not outcome <= panel or not objective_crossing <= panel:
        raise ValueError("Stage-3C-35 source classification leaves the panel")

    true_positive = sorted(predictor & outcome)
    false_positive = sorted(predictor - outcome)
    false_negative = sorted(outcome - predictor)
    true_negative = sorted(panel - predictor - outcome)
    exact_identity = predictor == outcome
    objective_chain_identity = predictor == objective_crossing == outcome
    nonvacuous = bool(outcome)

    payload: dict[str, Any] = {
        "schema": STAGE3C35_CROSSING_REPLICATION_ASSESSMENT_SCHEMA,
        "producer_version": __version__,
        "reference_stage3c34_decision_id": str(reference_decision["decision_id"]),
        "reference_source_seeds": reference_seeds,
        "replication_stage3c34_assessment_sha256": str(
            replication_crossing["assessment_sha256"]
        ),
        "replication_source_seeds": replication_seeds,
        "source_panels_are_disjoint": True,
        "preregistered_prediction": (
            "alignment-differential sampled-action crossing identifies every and "
            "only source with a nonzero exposure-only subject-balanced Objective-Fact effect"
        ),
        "source_level_confusion_matrix": {
            "true_positive_seeds": true_positive,
            "false_positive_seeds": false_positive,
            "false_negative_seeds": false_negative,
            "true_negative_seeds": true_negative,
            "true_positive_count": len(true_positive),
            "false_positive_count": len(false_positive),
            "false_negative_count": len(false_negative),
            "true_negative_count": len(true_negative),
        },
        "replication_findings": {
            "potential_divergence_source_seeds": list(
                findings["sources_with_subject_vm_potential_divergence"]
            ),
            "any_action_crossing_source_seeds": list(
                findings["sources_with_any_exposure_action_crossing"]
            ),
            "alignment_differential_action_crossing_source_seeds": sorted(predictor),
            "alignment_common_action_crossing_source_seeds": list(
                findings["sources_with_alignment_common_action_crossing"]
            ),
            "alignment_differential_objective_crossing_source_seeds": sorted(
                objective_crossing
            ),
            "surviving_fact_effect_source_seeds": sorted(outcome),
            "classification_counts": dict(findings["classification_counts"]),
            "differential_action_crossing_event_count": int(
                findings["total_alignment_differential_action_crossing_events"]
            ),
            "differential_objective_crossing_event_count": int(
                findings[
                    "total_alignment_differential_objective_fact_crossing_events"
                ]
            ),
            "delayed_objective_crossing_event_count": int(
                findings["total_delayed_objective_fact_crossing_events"]
            ),
        },
        "prediction_assessment": {
            "source_classifier_exact_identity": exact_identity,
            "event_chain_source_identity": objective_chain_identity,
            "nonvacuous_positive_source_support": nonvacuous,
            "prediction_supported_nonvacuously": bool(
                exact_identity and objective_chain_identity and nonvacuous
            ),
            "prediction_not_refuted": bool(exact_identity),
            "vacuous_match_only": bool(exact_identity and not nonvacuous),
        },
        "governance": {
            "disjoint_source_panel_required": True,
            "selected_seed_rerun_used": False,
            "exposure_changed": False,
            "addressing_changed": False,
            "crossing_definition_changed": False,
            "scalar_objective_used": False,
            "automatic_keep_or_revert_authorized": False,
            "permanent_retention_authorized": False,
        },
        "objective_coordinates_have_value_semantics": False,
        "causal_credit_quality_is_proven": False,
        "automatic_keep_or_revert_authorized": False,
        "permanent_parameter_retention_authorized": False,
        "learning_claim_authorized": False,
        "subjecthood_claim_authorized": False,
    }
    payload["assessment_sha256"] = _canonical_sha256(payload)
    return payload


def _summary(result: dict[str, Any]) -> dict[str, Any]:
    payload = {
        "schema": "se-subject-vm-stage3c35-crossing-replication-summary-v1",
        "producer_version": result["producer_version"],
        "assessment_sha256": result["assessment_sha256"],
        "assessment_mode": result.get("assessment_mode", "crossing-classifier"),
        "replication_source_seeds": result["replication_source_seeds"],
        "prediction_assessment": result["prediction_assessment"],
        "retention_authorized": False,
    }
    if "source_level_confusion_matrix" in result:
        payload["source_level_confusion_matrix"] = result["source_level_confusion_matrix"]
    if "qualification" in result:
        payload["qualification"] = {
            "stage3c28_gate_passed": result["qualification"]["stage3c28_gate_passed"],
            "complete_source_screen_seeds": result["qualification"]["complete_source_screen_seeds"],
            "complete_source_screen_count": result["qualification"]["complete_source_screen_count"],
        }
    return payload


def _diagnostic(result: dict[str, Any]) -> str:
    if "qualification" in result:
        qualification = result["qualification"]
        lines = [
            "# Stage 3C-35 disjoint-source qualification",
            "",
            "The panel is disjoint from Stage 3C-34, but the frozen Stage 3C-27 geometry prerequisite did not reproduce.",
            "",
            f"- Stage 3C-28 gate passed: `{qualification['stage3c28_gate_passed']}`.",
            f"- Individually complete source screens: `{qualification['complete_source_screen_seeds']}` ({qualification['complete_source_screen_count']}/9).",
            "- Stage 3C-28 and later stages were not executed after the failed gate.",
            "- The preregistered crossing classifier is not tested, not refuted and not supported.",
            "- No seed replacement, gate relaxation, value, keep/revert or retention is authorized.",
            "",
        ]
        return "\n".join(lines)
    findings = result["replication_findings"]
    prediction = result["prediction_assessment"]
    cm = result["source_level_confusion_matrix"]
    lines = [
        "# Stage 3C-35 disjoint-source crossing replication",
        "",
        "The source panel is disjoint from the frozen Stage 3C-34 panel. Runtime, exposure, addressing and crossing definitions are unchanged.",
        "",
        "## Preregistered source-level classifier",
        "",
        f"- Differential-action crossing sources: {findings['alignment_differential_action_crossing_source_seeds']}",
        f"- Surviving fact-effect sources: {findings['surviving_fact_effect_source_seeds']}",
        f"- True positives: {cm['true_positive_seeds']}",
        f"- False positives: {cm['false_positive_seeds']}",
        f"- False negatives: {cm['false_negative_seeds']}",
        f"- True negatives: {cm['true_negative_seeds']}",
        "",
        "## Frozen interpretation",
        "",
        f"- Exact source identity: `{prediction['source_classifier_exact_identity']}`.",
        f"- Non-vacuous positive support: `{prediction['nonvacuous_positive_source_support']}`.",
        f"- Prediction supported non-vacuously: `{prediction['prediction_supported_nonvacuously']}`.",
        "- No value, learned-weight, keep/revert or permanent-retention claim is authorized.",
        "",
    ]
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Assess Stage 3C-35 disjoint-source crossing replication."
    )
    parser.add_argument("--reference-stage3c34-decision", required=True)
    parser.add_argument("--replication-stage3c34-assessment")
    parser.add_argument("--stage3c27-assessment")
    parser.add_argument("--reference-stage3c27-assessment")
    parser.add_argument("--output", required=True)
    parser.add_argument("--summary-output")
    parser.add_argument("--diagnostic-report")
    args = parser.parse_args()

    reference = _load_json(args.reference_stage3c34_decision)
    if bool(args.stage3c27_assessment) == bool(args.replication_stage3c34_assessment):
        parser.error(
            "provide exactly one of --stage3c27-assessment or "
            "--replication-stage3c34-assessment"
        )
    if args.stage3c27_assessment:
        if not args.reference_stage3c27_assessment:
            parser.error(
                "--reference-stage3c27-assessment is required with "
                "--stage3c27-assessment"
            )
        result = assess_stage3c35_source_qualification(
            reference,
            _load_json(args.reference_stage3c27_assessment),
            _load_json(args.stage3c27_assessment),
        )
    else:
        result = assess_stage3c35_crossing_replication(
            reference,
            _load_json(args.replication_stage3c34_assessment),
        )
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if args.summary_output:
        summary = Path(args.summary_output)
        summary.parent.mkdir(parents=True, exist_ok=True)
        summary.write_text(json.dumps(_summary(result), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if args.diagnostic_report:
        diagnostic = Path(args.diagnostic_report)
        diagnostic.parent.mkdir(parents=True, exist_ok=True)
        diagnostic.write_text(_diagnostic(result), encoding="utf-8")
    print(json.dumps(_summary(result), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
