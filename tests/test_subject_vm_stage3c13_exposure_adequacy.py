from __future__ import annotations

import json
from pathlib import Path

import pytest

from se import __version__
from se.analysis.subject_vm_stage3c13_exposure_adequacy import (
    STAGE3C13_EXPOSURE_ADEQUACY_SCHEMA,
    _canonical_sha256,
    assess_stage3c13_exposure_adequacy,
)
from se.experiments.subject_vm_short_paired_study import (
    ShortPairedStudyParameters,
    run_short_paired_study,
)


def _run(tmp_path: Path, *, exposure: int) -> tuple[dict, dict, dict]:
    report = run_short_paired_study(
        "configs/mvp_short_subject_vm_stage3c8_paired_study.json",
        parameters=ShortPairedStudyParameters(
            seeds=(12301, 12302, 12303),
            source_ticks=2,
            horizon_ticks=8,
            bootstrap_subjects=8,
            backend="cpu",
            rollback_after_ticks=exposure,
        ),
        output_dir=tmp_path / f"exposure_{exposure}",
    )
    component = json.loads(
        Path(report["component_reproducibility"]).read_text(encoding="utf-8")
    )
    diagnostics = json.loads(
        Path(report["stage3c10_diagnostics"]).read_text(encoding="utf-8")
    )
    return report, component, diagnostics


def test_stage3c13_compares_exposure_only_from_identical_sources(
    tmp_path: Path,
) -> None:
    baseline, baseline_component, baseline_diagnostics = _run(
        tmp_path, exposure=2
    )
    extended, extended_component, extended_diagnostics = _run(
        tmp_path, exposure=3
    )
    result = assess_stage3c13_exposure_adequacy(
        baseline,
        extended,
        baseline_component=baseline_component,
        extended_component=extended_component,
        baseline_diagnostics=baseline_diagnostics,
        extended_diagnostics=extended_diagnostics,
    )
    assert result["schema"] == STAGE3C13_EXPOSURE_ADEQUACY_SCHEMA
    assert result["producer_version"] == __version__
    assert result["baseline"]["rollback_after_ticks"] == 2
    assert result["extended"]["rollback_after_ticks"] == 3
    integrity = result["source_panel_and_contract_integrity"]
    assert integrity["source_state_hashes_equal"] is True
    assert integrity["source_config_hashes_equal"] is True
    assert integrity["bootstrap_lineage_equal"] is True
    assert integrity["read_only_control_behavior_equal"] is True
    assert integrity["only_exposure_fields_overridden"] is True
    assert integrity["windows_are_independent_replicates"] is False
    assert result["comparison"][
        "change_in_weighted_mean_effective_semantic_ticks_per_commit"
    ] > 0
    assert result["automatic_keep_or_revert_decision"] is False
    assert result["permanent_parameter_retention_authorized"] is False
    assert len(result["semantic_reproducibility"]["semantic_result_sha256"]) == 64


def test_stage3c13_rejects_non_exposure_factor_change(tmp_path: Path) -> None:
    baseline, baseline_component, baseline_diagnostics = _run(
        tmp_path, exposure=2
    )
    extended, extended_component, extended_diagnostics = _run(
        tmp_path, exposure=3
    )
    extended["parameters"]["bootstrap_subjects"] = 7
    unsigned = dict(extended)
    unsigned.pop("study_sha256")
    extended["study_sha256"] = _canonical_sha256(unsigned)
    with pytest.raises(ValueError, match="non-exposure"):
        assess_stage3c13_exposure_adequacy(
            baseline,
            extended,
            baseline_component=baseline_component,
            extended_component=extended_component,
            baseline_diagnostics=baseline_diagnostics,
            extended_diagnostics=extended_diagnostics,
        )
