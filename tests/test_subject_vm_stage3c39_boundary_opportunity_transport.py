from __future__ import annotations

from copy import deepcopy

import pytest

from se.analysis.subject_vm_stage3c39_boundary_opportunity_transport import (
    assess_stage3c39_boundary_opportunity_transport,
)
from se.experiments.subject_vm_short_paired_study import _canonical_sha256


def _seal(payload: dict) -> dict:
    unsigned = dict(payload)
    unsigned.pop("assessment_sha256", None)
    payload["assessment_sha256"] = _canonical_sha256(unsigned)
    return payload


def _stage34(seeds: range, *, crossing_seed: int | None = None, scale: float = 1.0) -> dict:
    rows = []
    for index, seed in enumerate(seeds):
        crossing = 1 if seed == crossing_seed else 0
        value = scale * (index + 1) / 100.0
        rows.append(
            {
                "seed": seed,
                "classification": (
                    "differential-objective-crossing-survives-aggregation"
                    if crossing
                    else "continuous-decision-divergence-below-realized-action-boundary"
                ),
                "continuous_decision_divergence": {
                    "subject_vm_potential_exposure_alignment_ddd_event_count": 8 + index,
                    "event_fraction": (8 + index) / 144.0,
                    "l1_statistics": {
                        "count": 8 + index,
                        "minimum": value / 2,
                        "median": value,
                        "maximum": value * 2,
                        "mean": value * 1.1,
                    },
                    "event_count_by_tick": {"8": 4, "10": 3, "12": 1 + index},
                    "same_action_comparable_sampled_probability_ddd_event_count": 8 + index,
                    "same_action_sampled_probability_abs_statistics": {
                        "count": 8 + index,
                        "minimum": value / 100,
                        "median": value / 20,
                        "maximum": value / 5,
                        "mean": value / 15,
                    },
                },
                "sampled_action_crossing": {
                    "alignment_differential_action_crossing_event_count": crossing,
                },
            }
        )
    return _seal(
        {
            "schema": "se-subject-vm-stage3c34-threshold-crossing-assessment-v1",
            "per_source": rows,
        }
    )


def _stage36() -> dict:
    return _seal(
        {
            "schema": "se-subject-vm-stage3c36-geometry-transport-assessment-v1",
            "reference_source_seeds": list(range(12301, 12310)),
            "replication_source_seeds": list(range(12401, 12410)),
            "candidate_support_transport": {
                "candidate_support_signature_identical_across_all_18_sources": True,
            },
            "local_geometry_transport": {
                "strict_vs_older_scale_separation_remains_over_100x": True,
            },
            "first_state_recurrence_transport": {
                "same_first_state_query_count_delta": -24,
            },
        }
    )


def _stage38() -> dict:
    return _seal(
        {
            "schema": "se-subject-vm-stage3c38-crossing-replication-assessment-v1",
            "replication_source_seeds": list(range(12401, 12410)),
            "prediction_assessment": {"vacuous_match_only": True},
        }
    )


def test_stage3c39_narrows_zero_crossing_without_scalar_threshold() -> None:
    reference = _stage34(range(12301, 12310), crossing_seed=12305)
    replication = _stage34(range(12401, 12410), scale=1.2)
    result = assess_stage3c39_boundary_opportunity_transport(
        reference, replication, _stage36(), _stage38()
    )
    frozen = result["frozen_interpretation"]
    assert frozen["replication_panel_has_uniformly_weaker_continuous_divergence"] is False
    assert frozen["a_single_observed_monotone_magnitude_threshold_separates_reference_positive_sources"] is False
    assert frozen["zero_crossing_is_narrowed_to_unobserved_categorical_competition_and_draw_state"] is True
    assert frozen["exact_action_boundary_opportunity_is_resolved"] is False
    assert result["observability_boundary"]["full_masked_policy_logits_available"] is False


def test_stage3c39_rejects_overlapping_panels() -> None:
    replication = _stage34(range(12301, 12310))
    with pytest.raises(ValueError, match="disjoint source panels"):
        assess_stage3c39_boundary_opportunity_transport(
            _stage34(range(12301, 12310), crossing_seed=12305),
            replication,
            _stage36(),
            _stage38(),
        )


def test_stage3c39_rejects_modified_input_checksum() -> None:
    replication = deepcopy(_stage34(range(12401, 12410)))
    replication["per_source"][0]["classification"] = "modified"
    with pytest.raises(ValueError, match="checksum mismatch"):
        assess_stage3c39_boundary_opportunity_transport(
            _stage34(range(12301, 12310), crossing_seed=12305),
            replication,
            _stage36(),
            _stage38(),
        )
