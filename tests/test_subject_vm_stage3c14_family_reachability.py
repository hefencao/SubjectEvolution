from __future__ import annotations

import json
from pathlib import Path

import pytest

from se import __version__
from se.analysis.subject_vm_stage3c14_family_reachability import (
    STAGE3C14_FAMILY_REACHABILITY_SCHEMA,
    assess_stage3c14_family_reachability,
)
from se.experiments.subject_vm_short_paired_study import (
    ShortPairedStudyParameters,
    bootstrap_profile,
    run_short_paired_study,
)


def _run(tmp_path: Path, *, family: str) -> tuple[dict, dict, dict]:
    report = run_short_paired_study(
        "configs/mvp_short_subject_vm_stage3c8_paired_study.json",
        parameters=ShortPairedStudyParameters(
            seeds=(12301, 12302, 12303),
            source_ticks=2,
            horizon_ticks=8,
            bootstrap_subjects=8,
            backend="cpu",
            rollback_after_ticks=3,
            bootstrap_target_family=family,
        ),
        output_dir=tmp_path / family,
    )
    component = json.loads(
        Path(report["component_reproducibility"]).read_text(encoding="utf-8")
    )
    diagnostics = json.loads(
        Path(report["stage3c10_diagnostics"]).read_text(encoding="utf-8")
    )
    return report, component, diagnostics


def test_bootstrap_profile_routes_only_the_requested_family() -> None:
    bias = bootstrap_profile(target_family="node_bias")
    output = bootstrap_profile(target_family="node_output_gate")
    assert bias["target_family_shaping"]["token_port"] == 23
    assert output["target_family_shaping"]["token_port"] == 25
    assert bias["nodes"][7]["trace_port"] == 23
    assert output["nodes"][7]["trace_port"] == 25
    assert bias["profile_sha256"] != output["profile_sha256"]
    assert bias["evolved_topology"] is False
    assert output["universal_attention_claim"] is False
    with pytest.raises(ValueError, match="unsupported"):
        bootstrap_profile(target_family="edge_bandwidth")


def test_stage3c14_compares_isolated_family_routing(tmp_path: Path) -> None:
    baseline, baseline_component, baseline_diagnostics = _run(
        tmp_path, family="node_bias"
    )
    alternative, alternative_component, alternative_diagnostics = _run(
        tmp_path, family="node_output_gate"
    )
    result = assess_stage3c14_family_reachability(
        baseline,
        baseline_component,
        baseline_diagnostics,
        alternative,
        alternative_component,
        alternative_diagnostics,
    )
    assert result["schema"] == STAGE3C14_FAMILY_REACHABILITY_SCHEMA
    assert result["producer_version"] == __version__
    isolation = result["isolation_contract"]
    assert isolation["pre_bootstrap_state_hashes_equal"] is True
    assert isolation["pre_bootstrap_config_hashes_equal"] is True
    assert isolation["bootstrap_subject_selection_equal"] is True
    assert isolation["read_only_control_behavior_equal"] is True
    assert isolation["control_upstream_pipeline_equal"] is True
    reachability = result["target_family_reachability"]
    assert reachability["baseline_family"] == "node_bias"
    assert reachability["alternative_family"] == "node_output_gate"
    assert reachability["both_families_reached_and_committed"] is True
    assert result["rejected_pilot_design"]["reported_as_scientific_arm"] is False
    assert result["permanent_parameter_retention_authorized"] is False
    assert result["learning_claim_authorized"] is False
    assert len(result["assessment_sha256"]) == 64


def test_stage3c14_rejects_a_changed_non_family_factor(tmp_path: Path) -> None:
    baseline, baseline_component, baseline_diagnostics = _run(
        tmp_path, family="node_bias"
    )
    alternative, alternative_component, alternative_diagnostics = _run(
        tmp_path, family="node_output_gate"
    )
    alternative["parameters"]["horizon_ticks"] = 7
    from se.analysis.subject_vm_stage3c13_exposure_adequacy import _canonical_sha256

    unsigned = dict(alternative)
    unsigned.pop("study_sha256")
    alternative["study_sha256"] = _canonical_sha256(unsigned)
    with pytest.raises(ValueError, match="another study factor"):
        assess_stage3c14_family_reachability(
            baseline,
            baseline_component,
            baseline_diagnostics,
            alternative,
            alternative_component,
            alternative_diagnostics,
        )
