from __future__ import annotations

import json
from pathlib import Path

import pytest

from se.analysis.subject_vm_stage3c23_dual_readout_rank import (
    STAGE3C23_DUAL_READOUT_RANK_SCHEMA,
    assess_stage3c23_dual_readout_rank,
)
from se.experiments.subject_vm_short_paired_study import (
    ShortPairedStudyParameters,
    bootstrap_profile,
    run_short_paired_study,
)

CONFIG = "configs/mvp_short_subject_vm_stage3c23_dual_readout_rank_study.json"


def _run(root: Path, *, second_port: int):
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
            bootstrap_readout_input_port=11,
            bootstrap_second_readout_input_port=second_port,
            association_tie_break="latest",
            association_candidate_limit=1,
        ),
        output_dir=root / f"port_{second_port}",
    )
    component = json.loads(
        Path(report["component_reproducibility"]).read_text(encoding="utf-8")
    )
    diagnostics = json.loads(
        Path(report["stage3c10_diagnostics"]).read_text(encoding="utf-8")
    )
    return report, component, diagnostics


@pytest.fixture(scope="module")
def stage3c23_inputs(tmp_path_factory: pytest.TempPathFactory):
    root = tmp_path_factory.mktemp("stage3c23")
    rank1 = _run(root, second_port=11)
    # On the three-source test panel the frozen screen selects port 5.  The
    # authoritative nine-source workflow selects port 7.
    rank2 = _run(root, second_port=5)
    return rank1, rank2


def test_dual_readout_profile_is_readout_only_and_bounded() -> None:
    profile = bootstrap_profile(
        target_family="edge_forward_gate",
        edge_carrier_enabled=True,
        readout_input_port=11,
        second_readout_input_port=7,
    )
    assert profile["node_count"] == 10
    node8 = next(node for node in profile["nodes"] if node["index"] == 8)
    node9 = next(node for node in profile["nodes"] if node["index"] == 9)
    assert (node8["input_port"], node8["trace_port"]) == (11, 29)
    assert (node9["input_port"], node9["trace_port"]) == (7, 30)
    assert node8["output_port"] == node9["output_port"] == -1
    assert node8["local_eligibility"] is False
    assert node9["local_eligibility"] is False
    shaping = profile["association_visible_readout_shaping"]
    assert shaping["readout_only_node"]["value_semantics"] is None
    assert shaping["second_readout_only_node"]["value_semantics"] is None
    assert profile["evolved_topology"] is False
    assert profile["universal_attention_claim"] is False


def test_second_readout_requires_primary_and_capacity(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="requires the primary"):
        ShortPairedStudyParameters(
            seeds=(1, 2, 3),
            bootstrap_second_readout_input_port=7,
        ).validate()
    with pytest.raises(ValueError, match="at least 10 node slots"):
        run_short_paired_study(
            "configs/mvp_short_subject_vm_stage3c21_subject_event_readout_study.json",
            parameters=ShortPairedStudyParameters(
                seeds=(1, 2, 3),
                source_ticks=0,
                horizon_ticks=3,
                bootstrap_subjects=1,
                backend="cpu",
                bootstrap_readout_input_port=11,
                bootstrap_second_readout_input_port=7,
            ),
            output_dir=tmp_path / "insufficient",
        )


def test_stage3c23_reaches_rank_two_without_action_output_change(stage3c23_inputs) -> None:
    rank1, rank2 = stage3c23_inputs
    result = assess_stage3c23_dual_readout_rank(*rank1, *rank2)

    assert result["schema"] == STAGE3C23_DUAL_READOUT_RANK_SCHEMA
    assert result["candidate_screen"]["selected_candidate"]["port"] == 5
    assert result["isolation_contract"]["pre_bootstrap_state_hashes_equal"]
    assert result["isolation_contract"]["pre_bootstrap_config_hashes_equal"]
    assert result["isolation_contract"]["read_only_control_objective_behavior_equal"]
    assert result["isolation_contract"][
        "tokens_equal_except_authorized_port30_input_change"
    ]
    assert result["rank1_duplicate_uncertainty_control"]["token_geometry"][
        "centered_covariance_rank_per_source"
    ] == [1, 1, 1]
    assert result["rank2_selected_coordinate"]["token_geometry"][
        "centered_covariance_rank_per_source"
    ] == [2, 2, 2]
    assert result["permanent_parameter_retention_authorized"] is False
    assert result["learning_claim_authorized"] is False
    assert result["runtime_or_checkpoint_schema_changed"] is False


def test_stage3c23_rejects_an_additional_changed_factor(stage3c23_inputs) -> None:
    rank1, rank2 = stage3c23_inputs
    rank2[0]["parameters"]["association_candidate_limit"] = 2
    with pytest.raises(ValueError, match="frozen factor mismatch|another study factor"):
        assess_stage3c23_dual_readout_rank(*rank1, *rank2)
