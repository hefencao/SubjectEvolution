from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
import pytest

from se.analysis import subject_vm_stage3c34_threshold_crossing as analysis
from se.experiments.subject_vm_short_paired_study import _canonical_sha256


def _trace(event_count: int = 2) -> dict[str, np.ndarray]:
    shape = (1, event_count)
    return {
        "action_potentials": np.zeros((*shape, 8), dtype=np.float32),
        "action_id": np.zeros(shape, dtype=np.int16),
        "sampled_probability": np.full(shape, 0.25, dtype=np.float32),
        "target_subject_id": np.zeros(shape, dtype=np.uint64),
        "success": np.ones(shape, dtype=bool),
        "failure_reason": np.zeros(shape, dtype=np.uint8),
        "objective_delta": np.zeros((*shape, 12), dtype=np.float32),
        "resolution_resource_delta": np.zeros((*shape, 4), dtype=np.float32),
        "resolution_internal_resource_delta": np.zeros(
            (*shape, 4), dtype=np.float32
        ),
        "resolution_energy_cost": np.zeros(shape, dtype=np.float32),
    }


def _eight_arm_fixture() -> tuple[
    dict[tuple[str, str, str], dict[str, np.ndarray]],
    dict[tuple[str, str, str], dict[tuple[int, int, int], tuple[int, int]]],
]:
    traces = {
        (condition, mode, role): _trace()
        for condition in analysis._CONDITIONS
        for mode in analysis._MODES
        for role in analysis._ROLES
    }
    keys = [(101, 8, 1), (101, 9, 2)]
    index = {key: (0, slot) for slot, key in enumerate(keys)}
    indexes = {arm: dict(index) for arm in traces}
    return traces, indexes


def test_stage3c34_localizes_differential_action_and_objective_crossing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    traces, indexes = _eight_arm_fixture()
    traces["extended-exposure", "alignment-ablated", "guarded-live"][
        "action_potentials"
    ][0, 0, 0] = 0.5
    traces["extended-exposure", "alignment-ablated", "guarded-live"][
        "action_potentials"
    ][0, 1, 0] = 0.1
    traces["extended-exposure", "alignment-ablated", "guarded-live"][
        "action_id"
    ][0, 0] = 1
    traces["extended-exposure", "alignment-ablated", "guarded-live"][
        "objective_delta"
    ][0, 0, 0] = 1.0

    monkeypatch.setattr(
        analysis,
        "_checkpoint_traces_for_seed",
        lambda studies, seed: (traces, indexes, "source-state"),
    )
    reference = np.zeros(21, dtype=np.float64)
    reference[0] = 1.0
    result = analysis._source_crossing_audit(
        seed=12301,
        studies={},
        reference_fact_sum=reference,
    )

    assert result["continuous_decision_divergence"][
        "subject_vm_potential_exposure_alignment_ddd_event_count"
    ] == 2
    assert result["sampled_action_crossing"][
        "alignment_differential_action_crossing_event_count"
    ] == 1
    assert result["objective_event_crossing"][
        "alignment_differential_objective_fact_crossing_event_count"
    ] == 1
    assert result["objective_event_crossing"][
        "survives_subject_balanced_aggregation"
    ] is True
    assert (
        result["classification"]
        == "differential-objective-crossing-survives-aggregation"
    )


def test_stage3c34_separates_alignment_common_action_crossing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    traces, indexes = _eight_arm_fixture()
    for mode in analysis._MODES:
        traces["extended-exposure", mode, "guarded-live"]["action_id"][0, 0] = 2

    monkeypatch.setattr(
        analysis,
        "_checkpoint_traces_for_seed",
        lambda studies, seed: (traces, indexes, "source-state"),
    )
    result = analysis._source_crossing_audit(
        seed=12301,
        studies={},
        reference_fact_sum=np.zeros(21, dtype=np.float64),
    )

    assert result["sampled_action_crossing"][
        "any_exposure_action_crossing_event_count"
    ] == 1
    assert result["sampled_action_crossing"][
        "alignment_differential_action_crossing_event_count"
    ] == 0
    assert result["sampled_action_crossing"][
        "alignment_common_action_crossing_event_count"
    ] == 1
    assert (
        result["classification"]
        == "alignment-common-action-crossing-removed-by-cross-mode-contrast"
    )


def test_stage3c34_requires_frozen_stage3c33_checksum(tmp_path: Path) -> None:
    payload: dict[str, Any] = {
        "schema": analysis.STAGE3C33_EXPOSURE_PROPAGATION_ASSESSMENT_SCHEMA,
        "fixed_common_horizon_trajectory": {
            "exposure_only_contrast": {"per_source": []}
        },
        "assessment_sha256": "stale",
    }
    with pytest.raises(ValueError, match="checksum mismatch"):
        analysis._stage3c33_reference_by_seed(payload)

    payload["assessment_sha256"] = _canonical_sha256(
        {key: value for key, value in payload.items() if key != "assessment_sha256"}
    )
    assert analysis._stage3c33_reference_by_seed(payload) == {}


def test_stage3c34_cli_writes_summary_and_diagnostic(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    result = {
        "schema": analysis.STAGE3C34_THRESHOLD_CROSSING_ASSESSMENT_SCHEMA,
        "producer_version": "0.test",
        "assessment_sha256": "assessment",
        "source_level_independent_replication_count": 1,
        "cross_source_findings": {
            "sources_with_subject_vm_potential_divergence": [12301],
            "sources_with_any_exposure_action_crossing": [],
            "sources_with_alignment_differential_action_crossing": [],
            "sources_with_alignment_common_action_crossing": [],
            "sources_with_alignment_differential_objective_fact_crossing": [],
            "sources_with_surviving_subject_balanced_fact_effect": [],
            "total_alignment_differential_action_crossing_events": 0,
            "total_alignment_differential_objective_fact_crossing_events": 0,
            "total_delayed_objective_fact_crossing_events": 0,
        },
        "per_source": [
            {
                "seed": 12301,
                "classification": "continuous-decision-divergence-below-realized-action-boundary",
            }
        ],
    }
    study = tmp_path / "study.json"
    assessment = tmp_path / "assessment.json"
    study.write_text("{}", encoding="utf-8")
    assessment.write_text("{}", encoding="utf-8")
    monkeypatch.setattr(
        analysis, "assess_stage3c34_threshold_crossing", lambda *_: result
    )
    output = tmp_path / "result.json"
    summary = tmp_path / "summary.json"
    report = tmp_path / "report.md"
    monkeypatch.setattr(
        "sys.argv",
        [
            "stage3c34",
            "--stage3c33-study-report",
            str(study),
            "--stage3c33-assessment",
            str(assessment),
            "--output",
            str(output),
            "--summary-output",
            str(summary),
            "--diagnostic-report",
            str(report),
        ],
    )
    analysis.main()
    assert json.loads(summary.read_text(encoding="utf-8"))["source_count"] == 1
    assert "Stage 3C-34" in report.read_text(encoding="utf-8")
