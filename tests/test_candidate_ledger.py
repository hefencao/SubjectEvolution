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
