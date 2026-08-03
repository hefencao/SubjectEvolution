from __future__ import annotations

from copy import deepcopy

import pytest

from se.analysis.subject_vm_stage3c28_recurrent_basin import (
    _validate_stage3c37_qualification_overlay,
)
from se.analysis.subject_vm_stage3c38_crossing_replication import (
    assess_stage3c38_crossing_replication,
)
from se.experiments.subject_vm_short_paired_study import _canonical_sha256


def _seal(payload: dict) -> dict:
    unsigned = dict(payload)
    unsigned.pop("assessment_sha256", None)
    payload["assessment_sha256"] = _canonical_sha256(unsigned)
    return payload


def _reference() -> dict:
    return {
        "schema": "se-subject-vm-stage3c34-threshold-crossing-decision-v1",
        "decision_id": "subject-graph-vm-stage3c34-threshold-crossing-v1",
        "input_identity": {"source_seeds": list(range(12301, 12310))},
    }


def _historical_stage35() -> dict:
    return _seal(
        {
            "schema": "se-subject-vm-stage3c35-crossing-replication-assessment-v1",
            "replication_source_seeds": list(range(12401, 12410)),
            "prediction_assessment": {"crossing_prediction_tested": False},
        }
    )


def _qualification(*, study_sha: str = "rank2", stage27_sha: str = "stage27") -> dict:
    return _seal(
        {
            "schema": "se-subject-vm-stage3c37-tie-origin-assessment-v1",
            "input_checksums": {
                "replication_replay_study": study_sha,
                "replication_frozen_study": "frozen-rank2",
                "replication_stage3c27": stage27_sha,
            },
            "replay_identity": {
                "replication_source_state_hashes_match_frozen_report": True,
                "stored_winner_ids_exactly_reconstructed": True,
            },
            "cross_panel_resolution": {
                "selector_consistent_stage3c28_prerequisite_passed_in_both_panels": True,
            },
            "frozen_interpretation": {
                "corrected_crossing_replication_authorized_next": True,
                "stage3c35_crossing_prediction_was_tested": False,
            },
        }
    )


def _crossing(*, predictor=(12402, 12408), outcome=(12402, 12408)) -> dict:
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
    return _seal(payload)


def test_stage3c28_overlay_accepts_checksum_bound_selector_qualification() -> None:
    overlay = _qualification()
    _validate_stage3c37_qualification_overlay(
        overlay,
        rank2_study={"study_sha256": "rank2"},
        stage3c27_assessment={"assessment_sha256": "stage27", "rank2_study_sha256": "frozen-rank2"},
    )


def test_stage3c28_overlay_rejects_rank2_lineage_mismatch() -> None:
    with pytest.raises(ValueError, match="rank-two lineage"):
        _validate_stage3c37_qualification_overlay(
            _qualification(study_sha="other"),
            rank2_study={"study_sha256": "rank2"},
            stage3c27_assessment={"assessment_sha256": "stage27", "rank2_study_sha256": "frozen-rank2"},
        )


def test_stage3c38_freezes_nonvacuous_exact_replication() -> None:
    result = assess_stage3c38_crossing_replication(
        _reference(), _historical_stage35(), _qualification(), _crossing()
    )
    assert result["frozen_status"] == "replicated-nonvacuously"
    assert result["prediction_assessment"]["prediction_supported_nonvacuously"] is True
    assert result["source_level_confusion_matrix"]["false_positive_count"] == 0
    assert result["source_level_confusion_matrix"]["false_negative_count"] == 0


def test_stage3c38_freezes_refutation_without_changing_prediction() -> None:
    result = assess_stage3c38_crossing_replication(
        _reference(),
        _historical_stage35(),
        _qualification(),
        _crossing(predictor=(12402, 12408), outcome=(12402,)),
    )
    assert result["frozen_status"] == "refuted-on-disjoint-panel"
    assert result["source_level_confusion_matrix"]["false_positive_seeds"] == [12408]


def test_stage3c38_rejects_modified_qualification_checksum() -> None:
    qualification = deepcopy(_qualification())
    qualification["frozen_interpretation"]["corrected_crossing_replication_authorized_next"] = False
    with pytest.raises(ValueError, match="checksum mismatch"):
        assess_stage3c38_crossing_replication(
            _reference(), _historical_stage35(), qualification, _crossing()
        )
