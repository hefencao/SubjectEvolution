from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from se.analysis.subject_vm_component_reproducibility import (
    COMPONENT_REPRODUCIBILITY_SCHEMA,
    ComponentReproducibilityParameters,
    assess_component_reproducibility,
)
from se.analysis.subject_vm_paired_evaluation import PAIRED_EVALUATION_EXPORT_SCHEMA
from se.analysis.subject_vm_paired_evidence import PAIRED_EVIDENCE_ASSESSMENT_SCHEMA
from se.subject_vm.config import SUBJECT_VM_MODULATION_FACT_WIDTH
from se.subject_vm.evaluation_export import PAIRED_WINDOW_EXPORT_SCHEMA


def _sha(payload):
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _record(subject_id: int):
    return {
        "stable_subject_id": subject_id,
        "objective_scalar_score": False,
        "automatic_keep_or_revert_decision": False,
    }


def _pair(subject_id: int, energy: float, integrity: float = 0.0):
    vector = [0.0] * SUBJECT_VM_MODULATION_FACT_WIDTH
    vector[0] = energy
    vector[1] = integrity
    absolute = [abs(value) for value in vector]
    return {
        "guarded_live": _record(subject_id),
        "read_only_control": _record(subject_id),
        "objective_fact_sum_difference_live_minus_control": vector,
        "objective_fact_abs_sum_difference_live_minus_control": absolute,
        "observation_count_difference_live_minus_control": 0,
        "success_count_difference_live_minus_control": 1,
        "failure_count_difference_live_minus_control": -1,
        "scalar_score": None,
        "keep_or_revert_decision": None,
        "causal_effect_authorized": False,
    }


def _export(path: Path, *, source_hash: str, pairs):
    payload = {
        "schema": PAIRED_EVALUATION_EXPORT_SCHEMA,
        "plan_sha256": f"plan-{source_hash}",
        "source": {"checkpoint_state_sha256": source_hash},
        "shared_checkpoint_verified": True,
        "branch_identity_verified": True,
        "componentwise_differences_only": True,
        "scalar_score": False,
        "automatic_keep_or_revert_decision": False,
        "causal_effect_authorized": False,
        "branches": {},
        "window_evidence": {
            "schema": PAIRED_WINDOW_EXPORT_SCHEMA,
            "pairs": list(pairs),
            "unpaired_guarded_live": [],
            "unpaired_read_only_control": [],
            "paired_window_count": len(pairs),
            "scalar_score": False,
            "automatic_keep_or_revert_decision": False,
            "causal_effect_authorized": False,
        },
    }
    payload["export_sha256"] = _sha(payload)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return payload


def _assessment(path: Path, exports):
    runs = [
        {
            "export_path": str(export_path),
            "export_sha256": payload["export_sha256"],
            "plan_sha256": payload["plan_sha256"],
            "source_checkpoint_state_sha256": payload["source"][
                "checkpoint_state_sha256"
            ],
            "hard_integrity_pass": True,
            "scalar_score": False,
            "automatic_keep_or_revert_decision": False,
            "causal_effect_authorized": False,
        }
        for export_path, payload in exports
    ]
    payload = {
        "schema": PAIRED_EVIDENCE_ASSESSMENT_SCHEMA,
        "runs": runs,
        "aggregate": {"independent_source_pair_count": len(runs)},
        "adequacy_screen": {
            "passed": True,
            "scientific_sufficiency_authorized": False,
        },
        "objective_coordinate_weighting": None,
        "scalar_score": False,
        "automatic_keep_or_revert_decision": False,
        "causal_effect_authorized": False,
        "permanent_parameter_retention_authorized": False,
    }
    payload["assessment_sha256"] = _sha(payload)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return payload


def test_stage3c8_balances_subjects_before_independent_sources(tmp_path: Path):
    exports = []
    values = (
        ("source-a", [_pair(10, 10.0)] * 9 + [_pair(20, -2.0)]),
        ("source-b", [_pair(10, 4.0), _pair(20, 2.0)]),
        ("source-c", [_pair(10, 6.0), _pair(20, 2.0)]),
    )
    for name, pairs in values:
        path = tmp_path / f"{name}.json"
        exports.append((path, _export(path, source_hash=name, pairs=pairs)))
    assessment = tmp_path / "integrity.json"
    _assessment(assessment, exports)

    report = assess_component_reproducibility([assessment])
    assert report["schema"] == COMPONENT_REPRODUCIBILITY_SCHEMA
    assert report["independent_source_count"] == 3
    source_a = report["source_replicates"][0]
    assert source_a["source_subject_balanced_objective_fact_mean"][0] == 4.0
    assert source_a["diagnostic_window_weighted_objective_fact_mean"][0] == 8.8
    energy = report["objective_fact_sum_reproducibility"][0]
    assert energy["source_replicate_values"] == [4.0, 3.0, 4.0]
    assert energy["dominant_sign"] == "positive"
    assert energy["descriptive_sign_and_interval_stability_screen"] is True
    assert report["universal_scalar_objective"] is False
    assert report["overall_benefit_score"] is None
    assert report["automatic_keep_or_revert_decision"] is False
    assert report["causal_effect_authorized"] is False


def test_stage3c8_reports_mixed_coordinate_without_value_interpretation(tmp_path: Path):
    exports = []
    for index, integrity in enumerate((-1.0, 0.0, 1.0)):
        path = tmp_path / f"export-{index}.json"
        payload = _export(
            path,
            source_hash=f"source-{index}",
            pairs=[_pair(10, 1.0, integrity)],
        )
        exports.append((path, payload))
    assessment = tmp_path / "integrity.json"
    _assessment(assessment, exports)
    report = assess_component_reproducibility([assessment])
    integrity = report["objective_fact_sum_reproducibility"][1]
    assert integrity["dominant_sign"] == "tied"
    assert integrity["descriptive_sign_and_interval_stability_screen"] is False
    assert integrity["coordinate_value_interpretation"] is None


def test_stage3c8_deduplicates_identical_source_but_rejects_conflict(tmp_path: Path):
    first_path = tmp_path / "first.json"
    first = _export(first_path, source_hash="same", pairs=[_pair(10, 1.0)])
    duplicate_path = tmp_path / "duplicate.json"
    duplicate = _export(duplicate_path, source_hash="same", pairs=[_pair(10, 1.0)])
    others = []
    for index in range(2):
        path = tmp_path / f"other-{index}.json"
        others.append((path, _export(path, source_hash=f"other-{index}", pairs=[_pair(10, 1.0)])))
    assessment = tmp_path / "integrity.json"
    _assessment(
        assessment,
        [(first_path, first), (duplicate_path, duplicate), *others],
    )
    report = assess_component_reproducibility([assessment])
    assert report["independent_source_count"] == 3
    assert report["duplicate_source_state_hash_counts"] == {"same": 2}

    conflict_path = tmp_path / "conflict.json"
    conflict = _export(conflict_path, source_hash="same", pairs=[_pair(10, 9.0)])
    conflict_assessment = tmp_path / "conflict-assessment.json"
    _assessment(
        conflict_assessment,
        [(first_path, first), (conflict_path, conflict), *others],
    )
    with pytest.raises(ValueError, match="conflicting reproducibility data"):
        assess_component_reproducibility([conflict_assessment])


def test_stage3c8_requires_passed_integrity_and_enough_independent_sources(tmp_path: Path):
    export_path = tmp_path / "one.json"
    export = _export(export_path, source_hash="one", pairs=[_pair(10, 1.0)])
    assessment_path = tmp_path / "integrity.json"
    payload = _assessment(assessment_path, [(export_path, export)])
    with pytest.raises(ValueError, match="insufficient independent"):
        assess_component_reproducibility([assessment_path])

    payload["adequacy_screen"]["passed"] = False
    payload["assessment_sha256"] = _sha({k: v for k, v in payload.items() if k != "assessment_sha256"})
    assessment_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    with pytest.raises(ValueError, match="requires a Stage-3C-7 assessment that passed"):
        assess_component_reproducibility(
            [assessment_path],
            parameters=ComponentReproducibilityParameters(min_independent_sources=2),
        )
