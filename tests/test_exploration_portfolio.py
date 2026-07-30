from __future__ import annotations

import json
from pathlib import Path

from se.analysis.candidate_ledger import record_assessment
from se.analysis.exploration_portfolio import build_portfolio_audit, render_markdown


def _candidate(path: Path, *, candidate_id: str, family: str = "family-a") -> dict:
    payload = {
        "schema": "paired-exploration-candidate-v1",
        "candidate_id": candidate_id,
        "intervention": "neutralize-resource-affinity",
        "primary_metric": "harvested-resource-total",
        "metric_mode": "cumulative",
        "direction": "two-sided",
        "minimum_relative_effect": 0.02,
        "response_ticks": 120,
        "mechanism_family": family,
        "mechanism_family_revision": 1,
        "family_role": "aggregate-path",
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
    }
    path.write_text(json.dumps(payload), encoding="utf-8")
    return payload


def _assessment(candidate: dict) -> dict:
    return {
        "schema": "tiered-paired-exploration-assessment-v2",
        "stage": "screen",
        "candidate_id": candidate["candidate_id"],
        "intervention": candidate["intervention"],
        "primary_metric": candidate["primary_metric"],
        "metric_mode": candidate["metric_mode"],
        "direction": candidate["direction"],
        "minimum_relative_effect": candidate["minimum_relative_effect"],
        "response_ticks": candidate["response_ticks"],
        "mechanism_family": candidate["mechanism_family"],
        "mechanism_family_revision": 1,
        "family_role": "aggregate-path",
        "terminal_negative_closes_family": True,
        "manipulation_checks": candidate["manipulation_checks"],
        "eligible_seed_count": 8,
        "eligible_seed_fraction": 1.0,
        "manipulation_supported_seed_count": 8,
        "manipulation_supported_seed_fraction": 1.0,
        "positive_seed_count": 7,
        "negative_seed_count": 1,
        "direction_consistency": 0.875,
        "equal_seed_median_relative_effect": 0.001,
        "practical_effect_threshold_met": False,
        "all_stage_seeds": list(range(8)),
        "recommendation": "stop-effect-below-preregistered-practical-threshold",
        "decision": {
            "outcome": "stop",
            "terminal": True,
            "reason_codes": ["effect-below-preregistered-practical-threshold"],
        },
    }


def test_portfolio_audit_requires_scientific_revision_after_all_specs_terminal(
    tmp_path: Path,
) -> None:
    candidate_dir = tmp_path / "candidates"
    candidate_dir.mkdir()
    candidate = _candidate(candidate_dir / "candidate.json", candidate_id="aggregate-a")
    ledger_path = tmp_path / "ledger.json"
    record_assessment(ledger_path, _assessment(candidate))

    report = build_portfolio_audit(ledger_path, candidate_dir)
    assert report["portfolio_state"] == "scientific-revision-required"
    assert report["open_candidate_ids"] == []
    assert report["unrecorded_candidate_spec_ids"] == []
    assert report["family_revision_statuses"][0]["status"] == "closed"
    assert "new directly measurable interface" in report["next_action"]
    assert "scientific-revision-required" in render_markdown(report)


def test_portfolio_audit_reports_unrecorded_candidate_spec(tmp_path: Path) -> None:
    candidate_dir = tmp_path / "candidates"
    candidate_dir.mkdir()
    _candidate(candidate_dir / "candidate.json", candidate_id="pending-a")
    report = build_portfolio_audit(tmp_path / "missing-ledger.json", candidate_dir)
    assert report["portfolio_state"] == "candidate-specs-awaiting-assessment"
    assert report["unrecorded_candidate_spec_ids"] == ["pending-a"]


def test_portfolio_audit_uses_builtin_history_for_partial_workspace(
    tmp_path: Path,
) -> None:
    canonical = json.loads(
        Path("protocols/decisions/exploration_candidate_ledger.json").read_text(
            encoding="utf-8"
        )
    )
    partial_entries = [
        entry
        for entry in canonical["entries"]
        if entry["candidate_id"]
        in {
            "functional-regulatory-oxygen-uptake-acute-effect-v1",
            "functional-modules-harvest-acute-effect-v1",
        }
    ]
    ledger_path = tmp_path / "partial.json"
    ledger_path.write_text(
        json.dumps({**canonical, "entries": partial_entries}), encoding="utf-8"
    )

    report = build_portfolio_audit(
        ledger_path,
        "protocols/candidates",
        include_builtin_baseline=True,
    )
    assert report["portfolio_state"] == "candidate-specs-awaiting-assessment"
    assert report["unrecorded_candidate_spec_ids"] == [
        "spatial-processing-conversion-acute-effect-v1"
    ]
    assert report["workspace_ledger_entry_count"] == 2
    assert report["decision_baseline_entry_count"] == 5
    assert report["workspace_hydration_required"] is True
    assert "immutable baseline entries: 5" in render_markdown(report)
