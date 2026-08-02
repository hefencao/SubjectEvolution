from __future__ import annotations

import json
from pathlib import Path

import pytest

from se import __version__
from se.analysis.subject_vm_stage3c16_edge_carrier_reachability import (
    STAGE3C16_EDGE_CARRIER_REACHABILITY_SCHEMA,
    assess_stage3c16_edge_carrier_reachability,
)
from se.experiments.subject_vm_short_paired_study import (
    ShortPairedStudyParameters,
    bootstrap_profile,
    run_short_paired_study,
)


def _run(tmp_path: Path, *, carrier_enabled: bool) -> tuple[dict, dict, dict | None]:
    label = "carrier_on" if carrier_enabled else "carrier_off"
    report = run_short_paired_study(
        "configs/mvp_short_subject_vm_stage3c8_paired_study.json",
        parameters=ShortPairedStudyParameters(
            seeds=(12301, 12302, 12303),
            source_ticks=2,
            horizon_ticks=8,
            bootstrap_subjects=8,
            backend="cpu",
            rollback_after_ticks=3,
            bootstrap_target_family="edge_forward_gate",
            bootstrap_edge_carrier_enabled=carrier_enabled,
        ),
        output_dir=tmp_path / label,
    )
    diagnostics = json.loads(
        Path(report["stage3c10_diagnostics"]).read_text(encoding="utf-8")
    )
    component = None
    if report["component_reproducibility"]:
        component = json.loads(
            Path(report["component_reproducibility"]).read_text(encoding="utf-8")
        )
    return report, diagnostics, component


def test_edge_forward_bootstrap_profile_isolates_carrier_flag() -> None:
    carrier_off = bootstrap_profile(
        target_family="edge_forward_gate", edge_carrier_enabled=False
    )
    carrier_on = bootstrap_profile(
        target_family="edge_forward_gate", edge_carrier_enabled=True
    )
    assert carrier_off["target_family_shaping"]["token_port"] == 27
    assert carrier_on["nodes"][7]["trace_port"] == 27
    assert carrier_off["edges"][0]["local_eligibility"] is False
    assert carrier_on["edges"][0]["local_eligibility"] is True
    assert carrier_off["edges"][0]["eligibility_gate"] == 0.0
    assert carrier_on["edges"][0]["eligibility_gate"] == 1.0
    assert carrier_off["profile_sha256"] != carrier_on["profile_sha256"]
    with pytest.raises(ValueError, match="only valid for edge_forward_gate"):
        ShortPairedStudyParameters(
            seeds=(1, 2, 3),
            bootstrap_target_family="node_bias",
            bootstrap_edge_carrier_enabled=True,
        ).validate()


def test_stage3c16_isolates_edge_carrier_reachability(tmp_path: Path) -> None:
    off, off_diagnostics, off_component = _run(tmp_path, carrier_enabled=False)
    on, on_diagnostics, on_component = _run(tmp_path, carrier_enabled=True)
    assert off_component is None
    assert on_component is not None
    result = assess_stage3c16_edge_carrier_reachability(
        off, off_diagnostics, on, on_diagnostics, on_component
    )
    assert result["schema"] == STAGE3C16_EDGE_CARRIER_REACHABILITY_SCHEMA
    assert result["producer_version"] == __version__
    isolation = result["isolation_contract"]
    assert isolation["pre_bootstrap_state_hashes_equal"] is True
    assert isolation["read_only_control_behavior_equal"] is True
    assert isolation["read_only_control_token_association_modulation_upstream_equal"] is True
    assert isolation["same_target_family"] == "edge_forward_gate"
    assert result["carrier_off"]["stage_event_totals"][
        "target_binding_event_count"
    ] == 0
    assert result["carrier_off"]["stage_event_totals"][
        "guarded_live_commit_count"
    ] == 0
    assert result["carrier_on"]["stage_event_totals"][
        "target_binding_event_count"
    ] > 0
    assert result["carrier_on"]["stage_event_totals"][
        "guarded_live_commit_count"
    ] > 0
    assert result["permanent_parameter_retention_authorized"] is False
    assert result["learning_claim_authorized"] is False
    assert len(result["assessment_sha256"]) == 64


def test_stage3c16_rejects_a_changed_non_carrier_factor(tmp_path: Path) -> None:
    off, off_diagnostics, _ = _run(tmp_path, carrier_enabled=False)
    on, on_diagnostics, on_component = _run(tmp_path, carrier_enabled=True)
    assert on_component is not None
    on["parameters"]["horizon_ticks"] = 7
    unsigned = dict(on)
    unsigned.pop("study_sha256")
    from se.analysis.subject_vm_stage3c13_exposure_adequacy import _canonical_sha256

    on["study_sha256"] = _canonical_sha256(unsigned)
    with pytest.raises(ValueError, match="another study factor"):
        assess_stage3c16_edge_carrier_reachability(
            off, off_diagnostics, on, on_diagnostics, on_component
        )
