from __future__ import annotations

import json
from pathlib import Path

import pytest

from se import __version__
from se.analysis.subject_vm_stage3c20_readout_reachability import (
    STAGE3C20_READOUT_REACHABILITY_SCHEMA,
    assess_stage3c20_readout_reachability,
)
from se.experiments.subject_vm_short_paired_study import (
    ShortPairedStudyParameters,
    bootstrap_profile,
    run_short_paired_study,
)


def _run(tmp_path: Path, *, readout: bool):
    report = run_short_paired_study(
        "configs/mvp_short_subject_vm_stage3c8_paired_study.json",
        parameters=ShortPairedStudyParameters(
            seeds=(12301, 12302, 12303),
            source_ticks=2,
            horizon_ticks=8,
            bootstrap_subjects=16,
            backend="cpu",
            rollback_after_ticks=3,
            bootstrap_target_family="edge_forward_gate",
            bootstrap_edge_carrier_enabled=True,
            bootstrap_node0_visible_readout_enabled=readout,
            association_tie_break="latest",
            association_candidate_limit=1,
        ),
        output_dir=tmp_path / ("readout" if readout else "baseline"),
    )
    diagnostics = json.loads(
        Path(report["stage3c10_diagnostics"]).read_text(encoding="utf-8")
    )
    component = json.loads(
        Path(report["component_reproducibility"]).read_text(encoding="utf-8")
    )
    return report, component, diagnostics


def test_bootstrap_profile_exposes_only_authorized_node0_readout() -> None:
    baseline = bootstrap_profile(
        target_family="edge_forward_gate", edge_carrier_enabled=True
    )
    readout = bootstrap_profile(
        target_family="edge_forward_gate",
        edge_carrier_enabled=True,
        node0_visible_readout_enabled=True,
    )
    baseline_node0 = next(item for item in baseline["nodes"] if item["index"] == 0)
    readout_node0 = next(item for item in readout["nodes"] if item["index"] == 0)
    assert baseline_node0["trace_port"] == -1
    assert baseline_node0["trace_gate"] == 0.0
    assert readout_node0["trace_port"] == 29
    assert readout_node0["trace_gate"] == 1.0
    assert readout["association_visible_readout_shaping"]["value_semantics"] is None
    assert readout["evolved_topology"] is False
    assert readout["universal_attention_claim"] is False


def test_stage3c20_isolates_visible_readout_and_reports_temporal_geometry(
    tmp_path: Path,
) -> None:
    baseline = _run(tmp_path, readout=False)
    readout = _run(tmp_path, readout=True)
    result = assess_stage3c20_readout_reachability(*baseline, *readout)
    assert result["schema"] == STAGE3C20_READOUT_REACHABILITY_SCHEMA
    assert result["producer_version"] == __version__
    isolation = result["isolation_contract"]
    assert isolation["pre_bootstrap_state_hashes_equal"]
    assert isolation["pre_bootstrap_config_hashes_equal"]
    assert isolation["bootstrap_subject_selection_equal"]
    assert isolation["read_only_control_objective_behavior_equal"]
    assert isolation["thought_tokens_equal_except_authorized_port29_readout"]

    baseline_geometry = result["baseline"]["token_geometry"]
    readout_geometry = result["readout"]["token_geometry"]
    assert baseline_geometry["exact_unique_visible_token_count_per_source"] == [1, 1, 1]
    assert baseline_geometry["centered_covariance_rank_per_source"] == [0, 0, 0]
    assert readout_geometry["exact_unique_visible_token_count_per_source"] == [7, 7, 7]
    assert readout_geometry["centered_covariance_rank_per_source"] == [1, 1, 1]
    assert readout_geometry["all_subjects_equal_within_tick_in_all_sources"]
    assert readout_geometry["between_tick_port29_variance_positive_in_all_sources"]
    assert readout_geometry["all_sources_share_same_port29_tick_mean_trajectory"]
    assert result["baseline"]["association_allocation"]["delay_histogram"] == {"1": 336}
    assert result["readout"]["association_allocation"]["delay_histogram"] == {"2": 288}
    assert result["readout"]["association_allocation"]["all_assigned_similarities_one"] is False
    assert result["diagnostic_interpretation"][
        "current_readout_is_shared_temporal_phase_not_event_identity"
    ]
    assert result["permanent_parameter_retention_authorized"] is False
    assert result["learning_claim_authorized"] is False


def test_stage3c20_rejects_an_additional_changed_factor(tmp_path: Path) -> None:
    baseline = _run(tmp_path, readout=False)
    readout = _run(tmp_path, readout=True)
    readout[0]["parameters"]["association_candidate_limit"] = 2
    with pytest.raises(ValueError, match="frozen factor mismatch|another study factor"):
        assess_stage3c20_readout_reachability(*baseline, *readout)
