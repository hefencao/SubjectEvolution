from __future__ import annotations

import json
from pathlib import Path

import pytest

from se.analysis.subject_vm_stage3c21_subject_event_readout import (
    STAGE3C21_SUBJECT_EVENT_READOUT_SCHEMA,
    assess_stage3c21_subject_event_readout,
)
from se.experiments.subject_vm_short_paired_study import (
    ShortPairedStudyParameters,
    bootstrap_profile,
    run_short_paired_study,
)

CONFIG = "configs/mvp_short_subject_vm_stage3c21_subject_event_readout_study.json"


def _run(tmp_path: Path, *, input_port: int):
    report = run_short_paired_study(
        CONFIG,
        parameters=ShortPairedStudyParameters(
            seeds=(12301, 12302, 12303),
            source_ticks=2,
            horizon_ticks=8,
            bootstrap_subjects=16,
            backend="cpu",
            rollback_after_ticks=3,
            bootstrap_target_family="edge_forward_gate",
            bootstrap_edge_carrier_enabled=True,
            bootstrap_readout_input_port=input_port,
            association_tie_break="latest",
            association_candidate_limit=1,
        ),
        output_dir=tmp_path / f"port_{input_port}",
    )
    diagnostics = json.loads(
        Path(report["stage3c10_diagnostics"]).read_text(encoding="utf-8")
    )
    component = json.loads(
        Path(report["component_reproducibility"]).read_text(encoding="utf-8")
    )
    return report, component, diagnostics


def test_bootstrap_profile_adds_readout_only_node_without_action_output() -> None:
    profile = bootstrap_profile(
        target_family="edge_forward_gate",
        edge_carrier_enabled=True,
        readout_input_port=11,
    )
    node = next(item for item in profile["nodes"] if item["index"] == 8)
    assert profile["node_count"] == 9
    assert node["input_port"] == 11
    assert node["trace_port"] == 29
    assert node["trace_gate"] == 1.0
    assert node["output_port"] == -1
    assert node["output_gate"] == 0.0
    assert node["local_eligibility"] is False
    shaping = profile["association_visible_readout_shaping"]["readout_only_node"]
    assert shaping["changes_action_output"] is False
    assert shaping["value_semantics"] is None
    assert profile["evolved_topology"] is False
    assert profile["universal_attention_claim"] is False


def test_readout_only_node_requires_capacity_and_excludes_node0_readout(
    tmp_path: Path,
) -> None:
    with pytest.raises(ValueError, match="at least nine node slots"):
        run_short_paired_study(
            "configs/mvp_short_subject_vm_stage3c8_paired_study.json",
            parameters=ShortPairedStudyParameters(
                seeds=(1, 2, 3),
                source_ticks=0,
                horizon_ticks=3,
                bootstrap_subjects=1,
                backend="cpu",
                bootstrap_readout_input_port=11,
            ),
            output_dir=tmp_path / "insufficient",
        )
    with pytest.raises(ValueError, match="mutually exclusive"):
        ShortPairedStudyParameters(
            seeds=(1, 2, 3),
            bootstrap_node0_visible_readout_enabled=True,
            bootstrap_readout_input_port=11,
        ).validate()


def test_stage3c21_establishes_subject_and_event_specific_geometry(
    tmp_path: Path,
) -> None:
    constant = _run(tmp_path, input_port=0)
    uncertainty = _run(tmp_path, input_port=11)
    result = assess_stage3c21_subject_event_readout(*constant, *uncertainty)

    assert result["schema"] == STAGE3C21_SUBJECT_EVENT_READOUT_SCHEMA
    assert result["isolation_contract"]["pre_bootstrap_state_hashes_equal"]
    assert result["isolation_contract"]["pre_bootstrap_config_hashes_equal"]
    assert result["isolation_contract"]["read_only_control_objective_behavior_equal"]
    assert result["isolation_contract"][
        "tokens_equal_except_authorized_port29_input_change"
    ]

    baseline = result["constant_readout"]["token_geometry"]
    readout = result["uncertainty_readout"]["token_geometry"]
    assert baseline["centered_covariance_rank_per_source"] == [0, 0, 0]
    assert all(rank == 1 for rank in readout["centered_covariance_rank_per_source"])
    assert readout["all_sources_have_within_tick_subject_variance"]
    assert readout["all_sources_have_within_subject_temporal_variance"]
    assert readout["all_sources_have_multiple_values_on_both_axes"]
    assert readout["all_sources_share_identical_subject_event_matrix"] is False
    assert all(
        not identical
        for identical in readout["all_eligible_scores_identical_per_source"]
    )
    assert result["diagnostic_interpretation"][
        "objective_input_readout_creates_subject_specific_geometry"
    ]
    assert result["diagnostic_interpretation"][
        "objective_input_readout_creates_within_subject_event_time_variation"
    ]
    assert result["permanent_parameter_retention_authorized"] is False
    assert result["learning_claim_authorized"] is False


def test_stage3c21_rejects_an_additional_changed_factor(tmp_path: Path) -> None:
    constant = _run(tmp_path, input_port=0)
    uncertainty = _run(tmp_path, input_port=11)
    uncertainty[0]["parameters"]["association_candidate_limit"] = 2
    with pytest.raises(ValueError, match="frozen factor mismatch|another study factor"):
        assess_stage3c21_subject_event_readout(*constant, *uncertainty)
