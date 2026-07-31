from __future__ import annotations

from pathlib import Path

import pytest

from se.analysis.candidate_ledger import (
    LEDGER_SCHEMA,
    family_revision_statuses,
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
    with pytest.raises(ValueError, match="family_revision_interface"):
        validate_candidate_for_plan(
            ledger,
            candidate_id="revised",
            signature="9" * 64,
            stage="screen",
            mechanism_family="family-a",
            mechanism_family_revision=2,
            family_revision_rationale="A new directly measured causal interface is available.",
        )
    validate_candidate_for_plan(
        ledger,
        candidate_id="revised",
        signature="9" * 64,
        stage="screen",
        mechanism_family="family-a",
        mechanism_family_revision=2,
        family_revision_rationale="A new directly measured causal interface is available.",
        family_revision_interface="measured-new-causal-residual-v1",
    )


def test_bounded_negative_requires_aggregate_gate_before_another_bounded_path(
    tmp_path: Path,
) -> None:
    assessment = _assessment(candidate_id="bounded-a")
    assessment.update(
        {
            "candidate_signature_sha256": "a" * 64,
            "mechanism_family": "functional-modules",
            "mechanism_family_revision": 1,
            "family_role": "bounded-physiology-output-path",
            "terminal_negative_closes_family": False,
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
    _, entry = record_assessment(path, assessment)
    assert entry["family_gate_class"] == "bounded"
    ledger = load_ledger(path)

    with pytest.raises(ValueError, match="requires an aggregate family gate"):
        validate_candidate_for_plan(
            ledger,
            candidate_id="bounded-b",
            signature="b" * 64,
            stage="screen",
            mechanism_family="functional-modules",
            mechanism_family_revision=1,
            family_role="bounded-coupling-path",
        )

    validate_candidate_for_plan(
        ledger,
        candidate_id="aggregate",
        signature="c" * 64,
        stage="screen",
        mechanism_family="functional-modules",
        mechanism_family_revision=1,
        family_role="aggregate-path",
    )


def test_non_aggregate_candidate_cannot_declare_family_closure(tmp_path: Path) -> None:
    assessment = _assessment(candidate_id="invalid-closure")
    assessment.update(
        {
            "candidate_signature_sha256": "d" * 64,
            "mechanism_family": "family-b",
            "mechanism_family_revision": 1,
            "family_role": "bounded-output-path",
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
    with pytest.raises(ValueError, match="only for an aggregate family gate"):
        record_assessment(tmp_path / "ledger.json", assessment)


def test_ledger_publishes_family_revision_statuses(tmp_path: Path) -> None:
    assessment = _assessment(candidate_id="aggregate-status")
    assessment.update(
        {
            "candidate_signature_sha256": "e" * 64,
            "mechanism_family": "family-c",
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
            "manipulation_supported_seed_count": 8,
            "manipulation_supported_seed_fraction": 1.0,
        }
    )
    ledger, _ = record_assessment(tmp_path / "ledger.json", assessment)
    assert ledger["family_revision_statuses"] == [
        {
            "mechanism_family": "family-c",
            "mechanism_family_revision": 1,
            "status": "closed",
            "candidate_ids": ["aggregate-status"],
            "bounded_negative_candidate_ids": [],
            "aggregate_candidate_ids": ["aggregate-status"],
            "closed_by_candidate_ids": ["aggregate-status"],
        }
    ]
    assert ledger["family_closure_requires_aggregate_gate"] is True
    assert ledger["family_reopening_requires_new_interface"] is True



def test_family_revision_statuses_deduplicate_multistage_candidate_ids() -> None:
    entries = [
        {
            "candidate_id": "aggregate-multistage",
            "mechanism_family": "family-m",
            "mechanism_family_revision": 1,
            "family_role": "aggregate-path-gate",
            "stage": stage,
            "terminal": stage == "confirmation",
            "family_terminal": False,
        }
        for stage in ("screen", "replication", "confirmation")
    ]
    assert family_revision_statuses(entries) == [
        {
            "mechanism_family": "family-m",
            "mechanism_family_revision": 1,
            "status": "aggregate-gate-recorded",
            "candidate_ids": ["aggregate-multistage"],
            "bounded_negative_candidate_ids": [],
            "aggregate_candidate_ids": ["aggregate-multistage"],
            "closed_by_candidate_ids": [],
        }
    ]

def test_builtin_decision_baseline_matches_repository_protocol() -> None:
    import json

    from se.analysis.candidate_ledger import load_builtin_decision_baseline

    builtin = load_builtin_decision_baseline()
    repository = json.loads(
        Path("protocols/decisions/exploration_candidate_ledger.json").read_text(
            encoding="utf-8"
        )
    )
    assert builtin == load_ledger(
        Path("protocols/decisions/exploration_candidate_ledger.json")
    )
    assert repository["schema"] == LEDGER_SCHEMA


def test_effective_ledger_restores_missing_builtin_history(tmp_path: Path) -> None:
    import json

    from se.analysis.candidate_ledger import load_effective_ledger

    canonical = load_ledger("protocols/decisions/exploration_candidate_ledger.json")
    partial = {
        **canonical,
        "entries": [
            entry
            for entry in canonical["entries"]
            if entry["candidate_id"]
            in {
                "functional-regulatory-oxygen-uptake-acute-effect-v1",
                "functional-modules-harvest-acute-effect-v1",
            }
        ],
    }
    partial.pop("family_revision_statuses", None)
    path = tmp_path / "partial.json"
    path.write_text(json.dumps(partial), encoding="utf-8")

    effective, metadata = load_effective_ledger(
        path, include_builtin_baseline=True
    )
    assert len(effective["entries"]) == 8
    assert metadata["workspace_ledger_entry_count"] == 2
    assert metadata["decision_baseline_entry_count"] == 8
    assert metadata["workspace_hydration_required"] is True
    statuses = {
        (item["mechanism_family"], item["mechanism_family_revision"]): item["status"]
        for item in effective["family_revision_statuses"]
    }
    assert statuses[("knowledge-policy", 1)] == "closed"
    assert statuses[("functional-modules", 1)] == "closed"


def test_recording_duplicate_hydrates_partial_workspace(tmp_path: Path) -> None:
    import json

    from se.analysis.candidate_ledger import load_builtin_decision_baseline

    canonical = load_builtin_decision_baseline()
    d3s = next(
        entry
        for entry in canonical["entries"]
        if entry["candidate_id"] == "functional-modules-harvest-acute-effect-v1"
    )
    partial = {**canonical, "entries": [d3s]}
    partial.pop("family_revision_statuses", None)
    path = tmp_path / "partial.json"
    path.write_text(json.dumps(partial), encoding="utf-8")

    assessment = json.loads(
        Path("tests/fixtures/d3s_supplied_assessment.json").read_text(encoding="utf-8")
    )
    record_assessment(path, assessment, include_builtin_baseline=True)
    hydrated = load_ledger(path)
    assert len(hydrated["entries"]) == 8


def test_effective_ledger_rejects_conflicting_workspace_history(tmp_path: Path) -> None:
    import json

    from se.analysis.candidate_ledger import load_builtin_decision_baseline, load_effective_ledger

    canonical = load_builtin_decision_baseline()
    conflict = dict(canonical["entries"][0])
    conflict["assessment_sha256"] = "f" * 64
    conflict["equal_seed_median_relative_effect"] = 999.0
    workspace = {**canonical, "entries": [conflict]}
    workspace.pop("family_revision_statuses", None)
    path = tmp_path / "conflict.json"
    path.write_text(json.dumps(workspace), encoding="utf-8")

    with pytest.raises(ValueError, match="conflicting assessments"):
        load_effective_ledger(path, include_builtin_baseline=True)


def test_hydrate_ledger_writes_complete_builtin_history(tmp_path: Path) -> None:
    import json

    from se.analysis.candidate_ledger import hydrate_ledger, load_builtin_decision_baseline

    canonical = load_builtin_decision_baseline()
    partial = {**canonical, "entries": canonical["entries"][-2:]}
    partial.pop("family_revision_statuses", None)
    path = tmp_path / "ledger.json"
    path.write_text(json.dumps(partial), encoding="utf-8")

    hydrated, metadata = hydrate_ledger(path, include_builtin_baseline=True)
    assert len(hydrated["entries"]) == 8
    assert len(load_ledger(path)["entries"]) == 8
    assert path.with_suffix(".md").is_file()
    assert metadata["workspace_hydration_required"] is True
