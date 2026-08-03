from __future__ import annotations

from copy import deepcopy

import pytest

from se.analysis.subject_vm_stage3c36_geometry_transport import assess_stage3c36_geometry_transport
from se.experiments.subject_vm_short_paired_study import _canonical_sha256


def _seal(payload: dict) -> dict:
    payload["assessment_sha256"] = _canonical_sha256(payload)
    return payload


def _stage25(seeds: range) -> dict:
    return _seal({
        "schema": "se-subject-vm-stage3c25-winner-basin-assessment-v1",
        "per_source": [{"seed": seed} for seed in seeds],
        "source_balanced_summary": {"fraction_of_assignments_to_reused_winners": {"median": 0.46}},
    })


def _stage26(seeds: range) -> dict:
    rows = []
    for seed in seeds:
        rows.append({
            "seed": seed,
            "requested_query_count": 128,
            "assigned_query_count": 112,
            "no_candidate_request_count": 16,
            "forced_single_candidate_query_count": 16,
            "multi_candidate_assigned_query_count": 96,
            "candidate_count_histogram": {"0": 16, "1": 16, "2": 16, "3": 16, "4": 16, "5": 16, "6": 32},
        })
    return _seal({"schema": "se-subject-vm-stage3c26-age-phase-opportunity-assessment-v1", "per_source": rows})


def _stage27(seeds: range, *, same: int, strict: int, ties: int, same_acc: float, changed_acc: float) -> dict:
    rows = []
    for seed in seeds:
        changed = 96 - same
        rows.append({
            "seed": seed,
            "multi_candidate_query_count": 96,
            "multi_candidate_geometry": {
                "strict_age_one_geometry_win_count": strict,
                "exact_age_one_vs_older_score_tie_count": ties,
                "older_geometry_win_count": 96 - strict - ties,
                "strict_geometry_fraction_of_multi_candidate_age_one_selections": strict / (strict + ties),
            },
            "readout_state_recurrence": {
                "previous_tick_same_first_coordinate_query_count": same,
                "previous_tick_changed_first_coordinate_query_count": changed,
                "age_one_selected_when_first_coordinate_unchanged_fraction": same_acc,
                "older_selected_when_first_coordinate_changed_fraction": changed_acc,
            },
            "kinematic_groups": {
                "strict_age_one_geometry": {"local_step_l2": {"median": 0.0004}},
                "older_geometry": {"local_step_l2": {"median": 0.075}},
            },
        })
    return _seal({"schema": "se-subject-vm-stage3c27-token-kinematics-assessment-v1", "per_source": rows})


def test_stage3c36_separates_support_recurrence_and_ties() -> None:
    ref_seeds = range(12301, 12310)
    rep_seeds = range(12401, 12410)
    result = assess_stage3c36_geometry_transport(
        _stage25(ref_seeds), _stage26(ref_seeds),
        _stage27(ref_seeds, same=38, strict=43, ties=0, same_acc=0.94, changed_acc=0.87),
        _stage25(rep_seeds), _stage26(rep_seeds),
        _stage27(rep_seeds, same=35, strict=40, ties=1, same_acc=0.91, changed_acc=0.86),
    )
    assert result["candidate_support_transport"]["candidate_support_signature_identical_across_all_18_sources"] is True
    assert result["local_geometry_transport"]["strict_vs_older_scale_separation_remains_over_100x"] is True
    assert result["tie_transport"]["extra_exact_tie_count"] == 9
    assert result["frozen_interpretation"]["crossing_replication_authorized"] is False


def test_stage3c36_rejects_overlapping_panels() -> None:
    seeds = range(12301, 12310)
    with pytest.raises(ValueError, match="disjoint"):
        assess_stage3c36_geometry_transport(
            _stage25(seeds), _stage26(seeds), _stage27(seeds, same=38, strict=43, ties=0, same_acc=0.94, changed_acc=0.87),
            _stage25(seeds), _stage26(seeds), _stage27(seeds, same=35, strict=40, ties=1, same_acc=0.91, changed_acc=0.86),
        )


def test_stage3c36_rejects_checksum_mismatch() -> None:
    ref25 = _stage25(range(12301, 12310))
    ref25["source_balanced_summary"]["fraction_of_assignments_to_reused_winners"]["median"] = 0.5
    with pytest.raises(ValueError, match="checksum mismatch"):
        assess_stage3c36_geometry_transport(
            ref25, _stage26(range(12301, 12310)), _stage27(range(12301, 12310), same=38, strict=43, ties=0, same_acc=0.94, changed_acc=0.87),
            _stage25(range(12401, 12410)), _stage26(range(12401, 12410)), _stage27(range(12401, 12410), same=35, strict=40, ties=1, same_acc=0.91, changed_acc=0.86),
        )


def test_stage3c36_rejects_cross_stage_source_mismatch() -> None:
    ref26 = _stage26(range(12301, 12310))
    ref26 = deepcopy(ref26)
    ref26["per_source"][0]["seed"] = 12999
    ref26["assessment_sha256"] = _canonical_sha256({k: v for k, v in ref26.items() if k != "assessment_sha256"})
    with pytest.raises(ValueError, match="source identity mismatch"):
        assess_stage3c36_geometry_transport(
            _stage25(range(12301, 12310)), ref26, _stage27(range(12301, 12310), same=38, strict=43, ties=0, same_acc=0.94, changed_acc=0.87),
            _stage25(range(12401, 12410)), _stage26(range(12401, 12410)), _stage27(range(12401, 12410), same=35, strict=40, ties=1, same_acc=0.91, changed_acc=0.86),
        )
