from __future__ import annotations

from copy import deepcopy
from pathlib import Path

import pytest

from se import __version__
from se.analysis.subject_vm_stage3c15_local_sensitivity import (
    STAGE3C15_LOCAL_SENSITIVITY_SCHEMA,
    assess_stage3c15_local_sensitivity,
)
from se.experiments.subject_vm_short_paired_study import (
    ShortPairedStudyParameters,
    run_short_paired_study,
)


@pytest.fixture(scope="module")
def baseline_study(tmp_path_factory: pytest.TempPathFactory) -> dict:
    root = tmp_path_factory.mktemp("stage3c15-source")
    return run_short_paired_study(
        "configs/mvp_short_subject_vm_stage3c8_paired_study.json",
        parameters=ShortPairedStudyParameters(
            seeds=(12301, 12302, 12303),
            source_ticks=2,
            horizon_ticks=8,
            bootstrap_subjects=4,
            backend="cpu",
            rollback_after_ticks=3,
            bootstrap_target_family="node_bias",
        ),
        output_dir=root / "study",
    )


def test_stage3c15_distinguishes_sensitivity_reachability_and_degeneracy(
    baseline_study: dict, tmp_path: Path
) -> None:
    result = assess_stage3c15_local_sensitivity(
        baseline_study, probe_delta=0.05, work_root=tmp_path / "work"
    )
    assert result["schema"] == STAGE3C15_LOCAL_SENSITIVITY_SCHEMA
    assert result["producer_version"] == __version__
    assert result["independent_source_count"] == 3
    assert result["probe_contract"]["external_finite_difference_only"] is True
    assert result["probe_contract"]["writes_persisted_to_source_checkpoint"] is False

    degeneracy = result["algebraic_degeneracy"]
    assert (
        degeneracy[
            "node_bias_vs_node_input_gate_numerically_equivalent_within_float32_tolerance"
        ]
        is True
    )
    assert degeneracy["general_graph_equivalence_claim"] is False

    findings = result["diagnostic_findings"]
    assert findings["node_bias_and_input_gate_degenerate_in_this_bootstrap"] is True
    assert findings["edge_forward_gate_requires_warmed_delayed_context"] is True
    assert findings["node_trace_gate_is_token_channel_only_at_probe_horizon"] is True
    assert findings["edge_bandwidth_clamp_inactive_in_both_contexts"] is True
    assert findings["edge_bandwidth_locally_zero_at_current_operating_points"] is True
    assert findings["sensitive_but_not_currently_eligibility_reachable_families"] == [
        "edge_forward_gate",
        "node_trace_gate",
    ]

    reachability = result["reachability_vs_sensitivity"]
    assert reachability["node_bias"]["local_eligibility_reachable"] is True
    assert reachability["node_input_gate"]["local_eligibility_reachable"] is True
    assert reachability["node_output_gate"]["local_eligibility_reachable"] is True
    assert reachability["node_trace_gate"]["local_eligibility_reachable"] is False
    assert reachability["edge_forward_gate"]["local_eligibility_reachable"] is False
    assert reachability["edge_forward_gate"]["first_context_action_sensitive"] is False
    assert reachability["edge_forward_gate"]["warmed_context_action_sensitive"] is True
    assert result["interpretation_boundary"]["learning_claim_authorized"] is False
    assert (
        result["interpretation_boundary"][
            "permanent_parameter_retention_authorized"
        ]
        is False
    )
    assert len(result["assessment_sha256"]) == 64


def test_stage3c15_is_path_independent_and_reproducible(
    baseline_study: dict, tmp_path: Path
) -> None:
    first = assess_stage3c15_local_sensitivity(
        baseline_study, probe_delta=0.05, work_root=tmp_path / "first"
    )
    second = assess_stage3c15_local_sensitivity(
        baseline_study, probe_delta=0.05, work_root=tmp_path / "second"
    )
    assert first == second


def test_stage3c15_rejects_nonbaseline_family(baseline_study: dict) -> None:
    changed = deepcopy(baseline_study)
    changed["parameters"]["bootstrap_target_family"] = "node_output_gate"
    with pytest.raises(ValueError, match="node-bias baseline"):
        assess_stage3c15_local_sensitivity(changed)


def test_stage3c15_rejects_probe_larger_than_family_clip(
    baseline_study: dict,
) -> None:
    with pytest.raises(ValueError, match="probe_delta"):
        assess_stage3c15_local_sensitivity(baseline_study, probe_delta=0.1001)


def test_stage3c15_workflow_packages_only_declared_evidence() -> None:
    from se.cmd.study import load_workflow, resolve_step

    path, workflow = load_workflow(
        "studies/d1z_subject_vm_stage3c15_local_sensitivity_v1"
    )
    command, _ = resolve_step(
        path, workflow, "pack-results", allow_unconfigured_result=True
    )
    assert "--analysis-root" not in command
    assert command.count("--required-file") == 6
    assert "--include-checkpoints" not in command
