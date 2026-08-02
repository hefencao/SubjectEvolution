from __future__ import annotations

import json
from pathlib import Path

import pytest

from se import __version__
from se.analysis.subject_vm_stage3c17_temporal_tie_break import (
    STAGE3C17_TEMPORAL_TIE_BREAK_SCHEMA,
    assess_stage3c17_temporal_tie_break,
)
from se.experiments.subject_vm_short_paired_study import (
    ShortPairedStudyParameters,
    run_short_paired_study,
)


def _run(tmp_path: Path, policy: str):
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
            bootstrap_edge_carrier_enabled=True,
            association_tie_break=policy,
        ),
        output_dir=tmp_path / policy,
    )
    diagnostics = json.loads(
        Path(report["stage3c10_diagnostics"]).read_text(encoding="utf-8")
    )
    component = json.loads(
        Path(report["component_reproducibility"]).read_text(encoding="utf-8")
    )
    return report, diagnostics, component


def test_stage3c17_isolates_equal_similarity_temporal_tie_break(tmp_path: Path) -> None:
    latest = _run(tmp_path, "latest")
    oldest = _run(tmp_path, "oldest")
    result = assess_stage3c17_temporal_tie_break(*latest, *oldest)
    assert result["schema"] == STAGE3C17_TEMPORAL_TIE_BREAK_SCHEMA
    assert result["producer_version"] == __version__
    assert result["isolation_contract"]["source_checkpoint_state_hashes_equal"]
    assert result["isolation_contract"]["read_only_control_behavior_equal"]
    assert result["latest"]["association_allocation"]["delay_histogram"] == {
        "1": 168
    }
    oldest_histogram = result["oldest"]["association_allocation"][
        "delay_histogram"
    ]
    assert any(int(key) > 1 for key in oldest_histogram)
    assert result["oldest"]["association_allocation"][
        "all_assigned_similarities_one"
    ]
    assert result["diagnostic_interpretation"][
        "oldest_policy_increases_historical_event_reuse_concentration"
    ]
    assert result["permanent_parameter_retention_authorized"] is False
    assert result["learning_claim_authorized"] is False


def test_stage3c17_rejects_an_additional_changed_factor(tmp_path: Path) -> None:
    latest = _run(tmp_path, "latest")
    oldest = _run(tmp_path, "oldest")
    oldest[0]["parameters"]["bootstrap_subjects"] = 7
    with pytest.raises(ValueError, match="another study factor"):
        assess_stage3c17_temporal_tie_break(*latest, *oldest)
