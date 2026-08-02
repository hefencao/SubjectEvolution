from __future__ import annotations

import json
from pathlib import Path

import pytest

from se import __version__
from se.analysis.subject_vm_stage3c12_horizon_adequacy import (
    STAGE3C12_HORIZON_ADEQUACY_SCHEMA,
    assess_stage3c12_horizon_adequacy,
)
from se.experiments.subject_vm_short_paired_study import (
    ShortPairedStudyParameters,
    run_short_paired_study,
)


def _run(tmp_path: Path, *, horizon: int) -> tuple[dict, dict, dict]:
    report = run_short_paired_study(
        "configs/mvp_short_subject_vm_stage3c8_paired_study.json",
        parameters=ShortPairedStudyParameters(
            seeds=(12301, 12302, 12303),
            source_ticks=2,
            horizon_ticks=horizon,
            bootstrap_subjects=8,
            backend="cpu",
        ),
        output_dir=tmp_path / f"h{horizon}",
    )
    component = json.loads(
        Path(report["component_reproducibility"]).read_text(encoding="utf-8")
    )
    diagnostics = json.loads(
        Path(report["stage3c10_diagnostics"]).read_text(encoding="utf-8")
    )
    return report, component, diagnostics


def test_stage3c12_compares_trace_safe_horizon_only(tmp_path: Path) -> None:
    baseline, baseline_component, baseline_diagnostics = _run(tmp_path, horizon=5)
    extended, extended_component, extended_diagnostics = _run(tmp_path, horizon=8)
    result = assess_stage3c12_horizon_adequacy(
        baseline,
        extended,
        baseline_component=baseline_component,
        extended_component=extended_component,
        baseline_diagnostics=baseline_diagnostics,
        extended_diagnostics=extended_diagnostics,
    )
    assert result["schema"] == STAGE3C12_HORIZON_ADEQUACY_SCHEMA
    assert result["producer_version"] == __version__
    assert result["single_changed_experimental_factor"] == (
        "branch horizon ticks: 5 -> 8"
    )
    assert result["source_panel_identity"]["source_state_hashes_equal"] is True
    assert result["source_panel_identity"]["windows_are_independent_replicates"] is False
    assert result["trace_and_prefix_integrity"][
        "baseline_and_extended_trace_complete_for_all_sources"
    ] is True
    assert result["trace_and_prefix_integrity"][
        "all_sources_have_exact_semantic_prefix_identity"
    ] is True
    assert all(item["all_branch_prefixes_identical"] for item in result["per_source"])
    assert result["comparison"]["additional_completed_paired_windows"] >= 0
    assert result["adequacy_interpretation"][
        "five_tick_horizon_is_universally_sufficient"
    ] is False
    assert result["automatic_keep_or_revert_decision"] is False
    assert result["permanent_parameter_retention_authorized"] is False
    assert len(result["semantic_reproducibility"]["semantic_result_sha256"]) == 64


def test_stage3c12_rejects_non_horizon_factor_change(tmp_path: Path) -> None:
    baseline, baseline_component, baseline_diagnostics = _run(tmp_path, horizon=5)
    extended, extended_component, extended_diagnostics = _run(tmp_path, horizon=8)
    extended["parameters"]["bootstrap_subjects"] = 7
    unsigned = dict(extended)
    unsigned.pop("study_sha256")
    from se.analysis.subject_vm_stage3c12_horizon_adequacy import _canonical_sha256

    extended["study_sha256"] = _canonical_sha256(unsigned)
    with pytest.raises(ValueError, match="non-horizon"):
        assess_stage3c12_horizon_adequacy(
            baseline,
            extended,
            baseline_component=baseline_component,
            extended_component=extended_component,
            baseline_diagnostics=baseline_diagnostics,
            extended_diagnostics=extended_diagnostics,
        )
