from __future__ import annotations

from pathlib import Path

import pytest

from se.analysis.candidate_ledger import (
    LEDGER_SCHEMA,
    load_ledger,
    record_assessment,
    validate_candidate_for_plan,
)


def _assessment(*, candidate_id: str = "candidate-a", recommendation: str = "stop-direction-not-replicated-across-seeds") -> dict:
    return {
        "schema": "tiered-paired-exploration-assessment-v2",
        "stage": "screen",
        "candidate_id": candidate_id,
        "candidate_signature_sha256": "1" * 64,
        "intervention": "neutralize-resource-affinity",
        "primary_metric": "harvested-resource-total",
        "metric_mode": "cumulative",
        "direction": "two-sided",
        "minimum_relative_effect": 0.01,
        "response_ticks": 120,
        "manipulation_checks": [],
        "eligible_seed_count": 8,
        "eligible_seed_fraction": 1.0,
        "direction_consistency": 0.625,
        "equal_seed_median_relative_effect": 0.003,
        "all_stage_seeds": list(range(8)),
        "recommendation": recommendation,
        "decision": {
            "outcome": "stop",
            "terminal": True,
            "reason_codes": ["direction-not-replicated-across-seeds"],
        },
    }


def test_stopped_candidate_is_persisted_and_cannot_be_reopened(tmp_path: Path) -> None:
    path = tmp_path / "ledger.json"
    ledger, entry = record_assessment(path, _assessment())
    assert ledger["schema"] == LEDGER_SCHEMA
    assert entry["decision"] == "stop"
    loaded = load_ledger(path)
    with pytest.raises(ValueError, match="terminal"):
        validate_candidate_for_plan(
            loaded,
            candidate_id="candidate-a",
            signature="1" * 64,
            stage="replication",
        )
    with pytest.raises(ValueError, match="terminal"):
        validate_candidate_for_plan(
            loaded,
            candidate_id="renamed-candidate",
            signature="1" * 64,
            stage="screen",
        )


def test_candidate_id_cannot_change_specification(tmp_path: Path) -> None:
    path = tmp_path / "ledger.json"
    record_assessment(path, _assessment())
    with pytest.raises(ValueError, match="different scientific specification"):
        validate_candidate_for_plan(
            load_ledger(path),
            candidate_id="candidate-a",
            signature="2" * 64,
            stage="screen",
        )


def test_legacy_ledger_is_upgraded_with_explicit_evidence_class(tmp_path: Path) -> None:
    import json

    path = tmp_path / "ledger.json"
    path.write_text(
        json.dumps(
            {
                "schema": "paired-exploration-candidate-ledger-v1",
                "entries": [
                    {
                        "candidate_id": "legacy",
                        "candidate_signature_sha256": "3" * 64,
                        "candidate_spec": {
                            "intervention": "neutralize-resource-affinity",
                            "primary_metric": "harvested-resource-total",
                            "metric_mode": "cumulative",
                            "direction": "two-sided",
                            "minimum_relative_effect": 0.01,
                            "response_ticks": 120,
                            "manipulation_checks": [],
                        },
                        "stage": "screen",
                        "decision": "stop",
                        "terminal": True,
                        "recommendation": "stop-direction-not-replicated-across-seeds",
                        "reason_codes": ["direction-not-replicated-across-seeds"],
                        "assessment_schema": "tiered-paired-exploration-assessment-v1",
                        "assessment_sha256": "4" * 64,
                        "eligible_seed_count": 8,
                        "eligible_seed_fraction": 1.0,
                        "direction_consistency": 0.625,
                        "equal_seed_median_relative_effect": 0.003,
                        "all_stage_seeds": list(range(8)),
                        "selection_claim_allowed": False,
                    }
                ],
                "world_feedback": False,
                "failed_candidates_reopened_automatically": False,
            }
        ),
        encoding="utf-8",
    )
    ledger = load_ledger(path)
    assert ledger["schema"] == LEDGER_SCHEMA
    assert ledger["entries"][0]["evidence_class"] == (
        "promotion-negative-without-direct-manipulation-contract"
    )


def test_manipulation_confirmed_negative_is_distinguished(tmp_path: Path) -> None:
    assessment = _assessment(candidate_id="capacity")
    assessment.update(
        {
            "candidate_signature_sha256": "5" * 64,
            "intervention": "neutralize-elastic-capacities",
            "primary_metric": "knowledge-working-memory-active-dimensions-total",
            "minimum_relative_effect": 0.05,
            "manipulation_checks": [
                {
                    "metric": "capacity_effective_dimensions",
                    "metric_mode": "endpoint",
                    "branch": "intervention",
                    "operator": "==",
                    "value": 0.0,
                }
            ],
            "manipulation_supported_seed_count": 8,
            "manipulation_supported_seed_fraction": 1.0,
            "positive_seed_count": 4,
            "negative_seed_count": 4,
            "exact_two_sided_sign_flip_p": 0.625,
            "practical_effect_threshold_met": False,
        }
    )
    _, entry = record_assessment(tmp_path / "ledger.json", assessment)
    assert entry["manipulation_confirmed"] is True
    assert entry["evidence_class"] == "manipulation-confirmed-promotion-negative"


def test_terminal_aggregate_gate_closes_mechanism_family(tmp_path: Path) -> None:
    assessment = _assessment(candidate_id="knowledge-aggregate")
    assessment.update(
        {
            "candidate_signature_sha256": "6" * 64,
            "mechanism_family": "knowledge-policy",
            "mechanism_family_revision": 1,
            "family_role": "aggregate-path-gate",
            "terminal_negative_closes_family": True,
            "manipulation_checks": [
                {
                    "metric": "knowledge_policy_effective_enabled",
                    "metric_mode": "endpoint",
                    "branch": "intervention",
                    "operator": "==",
                    "value": 0.0,
                }
            ],
            "manipulation_supported_seed_count": 8,
            "manipulation_supported_seed_fraction": 1.0,
            "practical_effect_threshold_met": False,
        }
    )
    path = tmp_path / "ledger.json"
    _, entry = record_assessment(path, assessment)
    assert entry["family_terminal"] is True

    with pytest.raises(ValueError, match="mechanism family is terminal"):
        validate_candidate_for_plan(
            load_ledger(path),
            candidate_id="knowledge-child",
            signature="7" * 64,
            stage="screen",
            mechanism_family="knowledge-policy",
            mechanism_family_revision=1,
        )


def test_terminal_family_requires_higher_revision_and_rationale(tmp_path: Path) -> None:
    assessment = _assessment(candidate_id="aggregate")
    assessment.update(
        {
            "candidate_signature_sha256": "8" * 64,
            "mechanism_family": "family-a",
            "mechanism_family_revision": 1,
            "terminal_negative_closes_family": True,
            "manipulation_checks": [
                {
                    "metric": "target",
                    "metric_mode": "endpoint",
                    "branch": "intervention",
                    "operator": "==",
                    "value": 0.0,
                }
            ],
            "manipulation_supported_seed_count": 8,
            "manipulation_supported_seed_fraction": 1.0,
        }
    )
    path = tmp_path / "ledger.json"
    record_assessment(path, assessment)
    ledger = load_ledger(path)
    with pytest.raises(ValueError, match="family_revision_rationale"):
        validate_candidate_for_plan(
            ledger,
            candidate_id="revised",
            signature="9" * 64,
            stage="screen",
            mechanism_family="family-a",
            mechanism_family_revision=2,
        )
    validate_candidate_for_plan(
        ledger,
        candidate_id="revised",
        signature="9" * 64,
        stage="screen",
        mechanism_family="family-a",
        mechanism_family_revision=2,
        family_revision_rationale="A new directly measured causal interface is available.",
    )
