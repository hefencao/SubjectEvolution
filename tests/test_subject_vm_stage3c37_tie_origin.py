from __future__ import annotations

from copy import deepcopy

import numpy as np
import pytest

import se.analysis.subject_vm_stage3c37_tie_origin as stage37
from se.experiments.subject_vm_short_paired_study import _canonical_sha256


def _seal(payload: dict) -> dict:
    payload["assessment_sha256"] = _canonical_sha256(payload)
    return payload


def _panel(label: str, *, diagnostic: int, runtime: int, strict_fraction: float) -> dict:
    return {
        "panel": label,
        "seeds": list(range(1, 10)) if label == "reference" else list(range(11, 20)),
        "independent_source_count": 9,
        "per_source": [],
        "multi_candidate_query_count": 864,
        "stage3c27_diagnostic_near_tie_count": diagnostic,
        "runtime_top_tie_query_count": runtime,
        "runtime_tie_changes_exact_score_winner_count": 0,
        "selector_consistent_strict_age_one_count": 100,
        "selector_consistent_runtime_tie_age_one_count": 0,
        "selector_consistent_strict_fraction_of_multi_candidate_age_one_selections": strict_fraction,
        "stage3c27_diagnostic_strict_fraction_of_multi_candidate_age_one_selections": 0.98,
        "near_tie_score_gap_float64": {},
        "near_tie_second_coordinate_delta_ulp_count": {},
        "near_tie_origin_counts": {
            "runtime-comparator-tie": 0,
            "stored-normalized-direction-duplicate": 0,
            "stage3c27-diagnostic-tolerance-only": diagnostic,
        },
        "direct_float32_recomputation": {},
        "near_tie_records": [
            {
                "runtime_comparator_tie": False,
                "normalized_visible_float64_exactly_equal": False,
                "origin_classification": "stage3c27-diagnostic-tolerance-only",
                "latest_tie_break_changes_winner": False,
                "age_one_minus_best_older_score_float64": 5e-9,
                "second_coordinate_delta_ulp_count": 1800,
            }
            for _ in range(diagnostic)
        ],
    }


def test_stage3c37_distinguishes_diagnostic_bin_from_runtime_tie(monkeypatch: pytest.MonkeyPatch) -> None:
    stage36 = _seal({
        "schema": "se-subject-vm-stage3c36-geometry-transport-assessment-v1",
        "input_checksums": {"reference_stage3c27": "ref27", "replication_stage3c27": "rep27"},
    })
    ref27 = {"assessment_sha256": "ref27"}
    rep27 = {"assessment_sha256": "rep27"}
    source_calls = iter(({seed: {} for seed in range(1, 10)}, {seed: {} for seed in range(11, 20)}))
    monkeypatch.setattr(stage37, "_validate_frozen_and_replay", lambda *args, **kwargs: next(source_calls))
    monkeypatch.setattr(
        stage37,
        "_audit_panel",
        lambda sources, assessment, label: _panel(
            label,
            diagnostic=1 if label == "reference" else 6,
            runtime=0,
            strict_fraction=1.0,
        ),
    )
    frozen_ref = {"study_sha256": "frozen-ref"}
    replay_ref = {"study_sha256": "replay-ref"}
    frozen_rep = {"study_sha256": "frozen-rep"}
    replay_rep = {"study_sha256": "replay-rep"}
    result = stage37.assess_stage3c37_tie_origin(
        frozen_ref, replay_ref, ref27, frozen_rep, replay_rep, rep27, stage36
    )
    resolved = result["cross_panel_resolution"]
    assert resolved["stage3c27_diagnostic_near_tie_count"] == 7
    assert resolved["runtime_comparator_tie_count"] == 0
    assert resolved["latest_tie_break_changed_winner_count"] == 0
    assert resolved["selector_consistent_stage3c28_prerequisite_passed_in_both_panels"] is True
    assert result["frozen_interpretation"]["corrected_crossing_replication_authorized_next"] is True


def test_float32_counterfactual_is_not_runtime_score_contract() -> None:
    query = np.asarray([0.7, 0.8845276, 1.0], dtype=np.float32)
    age_one = np.asarray([0.7, 0.8845276, 1.0], dtype=np.float32)
    older = np.asarray([0.7, 0.8844141, 1.0], dtype=np.float32)
    score_age = stage37._float32_cosine(query, age_one)
    score_older = stage37._float32_cosine(query, older)
    assert np.isfinite(score_age)
    assert np.isfinite(score_older)
    assert stage37._RUNTIME_SCORE_ATOL == 1e-12
    assert stage37._STAGE3C27_DIAGNOSTIC_ATOL == 1e-8


def test_ulp_distance_resolves_distinct_float32_coordinates() -> None:
    left = np.float32(0.8845276236534119)
    right = np.float32(0.8844141364097595)
    assert stage37._ulp_distance(left, right) > 1000
    assert stage37._ulp_distance(left, left) == 0


def test_stage3c37_rejects_stage3c36_checksum_mismatch() -> None:
    payload = _seal({
        "schema": "se-subject-vm-stage3c36-geometry-transport-assessment-v1",
        "input_checksums": {},
    })
    payload["input_checksums"]["reference_stage3c27"] = "changed"
    with pytest.raises(ValueError, match="checksum mismatch"):
        stage37.assess_stage3c37_tie_origin({}, {}, {}, {}, {}, {}, payload)
