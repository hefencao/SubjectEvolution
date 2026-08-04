from __future__ import annotations

import json
from pathlib import Path

from se.analysis.subject_vm_thought_event_t2_degradation import assess
from se.cfg import load_config
from se.experiments.subject_vm_thought_event_t2_degradation import (
    ThoughtEventT2Parameters,
    run_thought_event_t2_study,
)


def test_t2_config_enables_only_t1_arena() -> None:
    cfg = load_config("configs/mvp_short_subject_vm_thought_event_t2_audit.json")
    assert cfg.subject_vm.thought_event_enabled
    assert cfg.subject_vm.thought_event.capacity_per_subject == 16
    assert cfg.subject_vm.thought_event.retention_ticks == 8
    assert not cfg.subject_vm.live_write.enabled


def test_t2_three_seed_smoke_detects_rank_control_without_recall(tmp_path: Path) -> None:
    study_root = tmp_path / "study"
    report = run_thought_event_t2_study(
        "configs/mvp_short_subject_vm_thought_event_t2_audit.json",
        output_dir=study_root,
        overwrite=True,
        parameters=ThoughtEventT2Parameters(seeds=(12501, 12502, 12503)),
    )
    assert report["forward_recall_enabled"] is False
    assert all(
        all(item["identity"].values())
        for item in report["cross_arm_identity"]
    )
    assessment = assess(
        study_root / "study_report.json",
        output=tmp_path / "assessment.json",
        summary_output=tmp_path / "summary.json",
        diagnostic_report=tmp_path / "diagnostic.md",
    )
    findings = assessment["cross_arm_findings"]
    assert findings["duplicate_coordinate_control_is_rank_one_in_all_seeds"]
    assert findings["rank_two_candidate_is_rank_two_in_all_seeds"]
    assert findings["rank_two_candidate_events_are_exactly_distinct"]
    assert findings["rank_two_candidate_remains_low_rank_fixed_bootstrap"]
    qualification = assessment["qualification"]
    assert qualification["arena_lifecycle_and_identity_qualified"]
    assert qualification["degeneration_diagnostic_control_qualified"]
    assert qualification["formal_nine_seed_panel"] is False
    assert qualification["t3_mechanism_smoke_authorized"] is False
    assert qualification["thought_chain_claim_authorized"] is False
    summary = json.loads((tmp_path / "summary.json").read_text(encoding="utf-8"))
    assert summary["candidate_centered_rank_all_seeds"] == 2


def test_t2_formal_fixture_freezes_nine_seed_qualification() -> None:
    fixture_path = Path("tests/fixtures/thought_event_t2_degradation.json")
    payload = json.loads(fixture_path.read_text(encoding="utf-8"))
    assert payload["assessment_sha256"] == "fd553555909435de069067ea95c06baefa060e25a66d2de386be2c4e32374f7a"
    assert payload["design"]["seeds"] == list(range(12501, 12510))
    assert payload["cross_arm_findings"]["all_action_event_and_probability_fields_identical"]
    assert payload["cross_arm_findings"]["arms_differ_only_at_second_readout_coordinate_30"]
    control = payload["arms"]["duplicate-coordinate-control"]
    candidate = payload["arms"]["rank-two-candidate"]
    assert control["centered_numerical_rank"]["min"] == 1
    assert control["centered_numerical_rank"]["max"] == 1
    assert candidate["centered_numerical_rank"]["min"] == 2
    assert candidate["centered_numerical_rank"]["max"] == 2
    assert candidate["exact_unique_token_count"]["min"] == 192
    assert candidate["exact_duplicate_fraction"]["max"] == 0
    qualification = payload["qualification"]
    assert qualification["formal_nine_seed_panel"] is True
    assert qualification["t3_mechanism_smoke_authorized"] is True
    assert qualification["thought_chain_claim_authorized"] is False
    assert qualification["distributed_cognitive_representation_claim_authorized"] is False
