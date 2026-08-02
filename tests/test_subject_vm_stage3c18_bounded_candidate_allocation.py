from __future__ import annotations

import json
from pathlib import Path

import pytest

from se import __version__
from se.analysis.subject_vm_stage3c18_bounded_candidate_allocation import (
    STAGE3C18_BOUNDED_CANDIDATE_ALLOCATION_SCHEMA,
    assess_stage3c18_bounded_candidate_allocation,
)
from se.experiments.subject_vm_short_paired_study import (
    ShortPairedStudyParameters,
    run_short_paired_study,
)


def _run(tmp_path: Path, limit: int):
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
            association_tie_break="latest",
            association_candidate_limit=limit,
        ),
        output_dir=tmp_path / f"top{limit}",
    )
    diagnostics = json.loads(
        Path(report["stage3c10_diagnostics"]).read_text(encoding="utf-8")
    )
    component = json.loads(
        Path(report["component_reproducibility"]).read_text(encoding="utf-8")
    )
    return report, diagnostics, component


def test_stage3c18_isolates_bounded_candidate_limit(tmp_path: Path) -> None:
    top1 = _run(tmp_path, 1)
    top2 = _run(tmp_path, 2)
    result = assess_stage3c18_bounded_candidate_allocation(*top1, *top2)
    assert result["schema"] == STAGE3C18_BOUNDED_CANDIDATE_ALLOCATION_SCHEMA
    assert result["producer_version"] == __version__
    assert result["isolation_contract"]["source_checkpoint_state_hashes_equal"]
    assert result["isolation_contract"]["read_only_control_behavior_equal"]
    assert result["isolation_contract"]["only_candidate_limit_changed"]
    assert result["top1"]["association_allocation"]["selected_reference_count"] == 168
    assert result["top2"]["association_allocation"]["selected_reference_count"] == 312
    assert result["top2"]["association_allocation"][
        "events_with_two_selected_candidates"
    ] == 144
    assert result["top2"]["association_allocation"][
        "secondary_delay_histogram"
    ] == {"2": 144}
    assert result["permanent_parameter_retention_authorized"] is False
    assert result["learning_claim_authorized"] is False


def test_stage3c18_rejects_an_additional_changed_factor(tmp_path: Path) -> None:
    top1 = _run(tmp_path, 1)
    top2 = _run(tmp_path, 2)
    top2[0]["parameters"]["bootstrap_subjects"] = 7
    with pytest.raises(ValueError, match="another study factor"):
        assess_stage3c18_bounded_candidate_allocation(*top1, *top2)
