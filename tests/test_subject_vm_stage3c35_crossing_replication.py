from __future__ import annotations

from copy import deepcopy

import pytest

from se.analysis.subject_vm_stage3c35_crossing_replication import (
    assess_stage3c35_crossing_replication,
    assess_stage3c35_source_qualification,
)
from se.experiments.subject_vm_short_paired_study import _canonical_sha256


def _reference() -> dict:
    return {
        "schema": "se-subject-vm-stage3c34-threshold-crossing-decision-v1",
        "decision_id": "subject-graph-vm-stage3c34-threshold-crossing-v1",
        "input_identity": {"source_seeds": list(range(12301, 12310))},
    }


def _replication(*, predictor=(12402, 12408), outcome=(12402, 12408)) -> dict:
    seeds = list(range(12401, 12410))
    payload = {
        "schema": "se-subject-vm-stage3c34-threshold-crossing-assessment-v1",
        "per_source": [{"seed": seed} for seed in seeds],
        "cross_source_findings": {
            "sources_with_subject_vm_potential_divergence": seeds,
            "sources_with_any_exposure_action_crossing": sorted(set(predictor) | {12407}),
            "sources_with_alignment_differential_action_crossing": list(predictor),
            "sources_with_alignment_common_action_crossing": [12407],
            "sources_with_alignment_differential_objective_fact_crossing": list(outcome),
            "sources_with_surviving_subject_balanced_fact_effect": list(outcome),
            "classification_counts": {"below-action-boundary": 6, "differential-crossing": 2, "alignment-common-crossing": 1},
            "total_alignment_differential_action_crossing_events": 4,
            "total_alignment_differential_objective_fact_crossing_events": 8,
            "total_delayed_objective_fact_crossing_events": 5,
        },
    }
    payload["assessment_sha256"] = _canonical_sha256(payload)
    return payload


def test_stage3c35_supports_nonvacuous_exact_replication() -> None:
    result = assess_stage3c35_crossing_replication(_reference(), _replication())
    assert result["source_panels_are_disjoint"] is True
    assert result["prediction_assessment"]["prediction_supported_nonvacuously"] is True
    assert result["source_level_confusion_matrix"]["false_positive_count"] == 0
    assert result["source_level_confusion_matrix"]["false_negative_count"] == 0


def test_stage3c35_reports_false_positive_without_rewriting_prediction() -> None:
    result = assess_stage3c35_crossing_replication(
        _reference(), _replication(predictor=(12402, 12408), outcome=(12402,))
    )
    assert result["prediction_assessment"]["prediction_not_refuted"] is False
    assert result["source_level_confusion_matrix"]["false_positive_seeds"] == [12408]


def test_stage3c35_rejects_overlapping_source_panel() -> None:
    replication = _replication()
    replication["per_source"][0]["seed"] = 12301
    replication["assessment_sha256"] = _canonical_sha256(
        {key: value for key, value in replication.items() if key != "assessment_sha256"}
    )
    with pytest.raises(ValueError, match="disjoint"):
        assess_stage3c35_crossing_replication(_reference(), replication)


def test_stage3c35_rejects_checksum_mismatch() -> None:
    replication = deepcopy(_replication())
    replication["cross_source_findings"]["sources_with_alignment_common_action_crossing"] = []
    with pytest.raises(ValueError, match="checksum mismatch"):
        assess_stage3c35_crossing_replication(_reference(), replication)


def _stage3c27_qualification() -> dict:
    seeds = list(range(12401, 12410))
    rows = []
    for seed in seeds:
        rows.append(
            {
                "seed": seed,
                "multi_candidate_geometry": {
                    "strict_geometry_fraction_of_multi_candidate_age_one_selections": 1.0 if seed in {12402, 12408} else 0.95
                },
                "readout_state_recurrence": {
                    "age_one_selected_when_first_coordinate_unchanged_fraction": 0.95 if seed in {12402, 12408} else 0.85,
                    "older_selected_when_first_coordinate_changed_fraction": 0.90,
                },
            }
        )
    payload = {
        "schema": "se-subject-vm-stage3c27-token-kinematics-assessment-v1",
        "per_source": rows,
        "cross_source_findings": {
            "strict_geometry_accounts_for_at_least_99_percent_of_multi_candidate_age_one_selections": False,
            "strict_geometry_age_one_selection_total": 363,
            "latest_tie_break_age_one_selection_total": 6,
            "multi_candidate_age_one_selection_total": 369,
            "multi_candidate_query_total": 864,
            "unchanged_first_readout_coordinate_predicts_age_one_selection_at_least_90_percent_in_all_sources": False,
            "changed_first_readout_coordinate_predicts_older_selection_at_least_80_percent_in_all_sources": True,
        },
        "diagnostic_interpretation": {
            "local_token_geometry_is_the_primary_multi_candidate_age_one_driver": False,
            "first_readout_state_persistence_and_recurrence_contribute_to_selected_age": False,
        },
    }
    payload["assessment_sha256"] = _canonical_sha256(payload)
    return payload


def test_stage3c35_freezes_failed_upstream_qualification_without_testing_prediction() -> None:
    reference = _stage3c27_qualification()
    reference["diagnostic_interpretation"]["local_token_geometry_is_the_primary_multi_candidate_age_one_driver"] = True
    reference["cross_source_findings"]["strict_geometry_age_one_selection_total"] = 386
    reference["cross_source_findings"]["latest_tie_break_age_one_selection_total"] = 1
    reference["cross_source_findings"]["multi_candidate_age_one_selection_total"] = 387
    reference["cross_source_findings"]["multi_candidate_query_total"] = 864
    reference["assessment_sha256"] = _canonical_sha256({k: v for k, v in reference.items() if k != "assessment_sha256"})
    replication = _stage3c27_qualification()
    replication["cross_source_findings"]["strict_geometry_age_one_selection_total"] = 363
    replication["cross_source_findings"]["latest_tie_break_age_one_selection_total"] = 6
    replication["cross_source_findings"]["multi_candidate_age_one_selection_total"] = 369
    replication["cross_source_findings"]["multi_candidate_query_total"] = 864
    replication["assessment_sha256"] = _canonical_sha256({k: v for k, v in replication.items() if k != "assessment_sha256"})
    result = assess_stage3c35_source_qualification(_reference(), reference, replication)
    assert result["source_panels_are_disjoint"] is True
    assert result["qualification"]["stage3c28_gate_passed"] is False
    assert result["qualification"]["complete_source_screen_seeds"] == [12402, 12408]
    assert result["prediction_assessment"]["crossing_prediction_tested"] is False
    assert result["frozen_interpretation"]["failure_is_a_preregistered_scientific_qualification_result"] is True
