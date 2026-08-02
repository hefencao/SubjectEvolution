from __future__ import annotations

import json
from pathlib import Path

from se import __version__
from se.analysis.subject_vm_stage3c10_diagnostics import _trace_tick_coverage
from se.analysis.subject_vm_stage3c11_sample_adequacy import (
    STAGE3C11_SAMPLE_ADEQUACY_SCHEMA,
    assess_stage3c11_sample_adequacy,
)
from se.experiments.subject_vm_short_paired_study import (
    ShortPairedStudyParameters,
    run_short_paired_study,
)


def test_trace_tick_coverage_marks_retention_limited_prefix() -> None:
    complete = _trace_tick_coverage(source_tick=2, final_tick=7, observed_ticks=range(2, 7))
    assert complete["complete"] is True
    assert complete["coverage_fraction"] == 1.0
    truncated = _trace_tick_coverage(source_tick=2, final_tick=18, observed_ticks=range(9, 18))
    assert truncated["complete"] is False
    assert truncated["retention_limited"] is True
    assert truncated["missing_event_ticks"] == list(range(2, 9))
    assert truncated["observed_divergence_counts_are_lower_bounds_when_incomplete"] is True


def test_stage3c11_expands_independent_sources_without_promoting_windows(
    tmp_path: Path,
) -> None:
    report = run_short_paired_study(
        "configs/mvp_short_subject_vm_stage3c8_paired_study.json",
        parameters=ShortPairedStudyParameters(
            seeds=(12301, 12302, 12303, 12304),
            source_ticks=2,
            horizon_ticks=5,
            bootstrap_subjects=8,
            backend="cpu",
        ),
        output_dir=tmp_path / "study",
    )
    component = json.loads(
        Path(report["component_reproducibility"]).read_text(encoding="utf-8")
    )
    diagnostics = json.loads(
        Path(report["stage3c10_diagnostics"]).read_text(encoding="utf-8")
    )
    assessment = assess_stage3c11_sample_adequacy(
        report,
        component_reproducibility=component,
        stage3c10_diagnostics=diagnostics,
        pilot_source_count=3,
    )
    assert report["producer_version"] == __version__
    assert assessment["schema"] == STAGE3C11_SAMPLE_ADEQUACY_SCHEMA
    assert assessment["producer_version"] == __version__
    assert assessment["replicate_accounting"]["independent_source_count"] == 4
    assert assessment["replicate_accounting"]["entities_are_independent_replicates"] is False
    assert assessment["replicate_accounting"]["windows_are_independent_replicates"] is False
    assert assessment["prefix_sensitivity"][0]["independent_source_count"] == 3
    assert assessment["prefix_sensitivity"][-1]["independent_source_count"] == 4
    assert assessment["adequacy_interpretation"]["three_source_pilot_was_scientifically_sufficient"] is False
    assert assessment["adequacy_interpretation"]["expanded_panel_authorizes_scientific_sufficiency"] is False
    assert all(
        source["admission_and_counted_cost_symmetry"]["paired_admission_contract_pass"]
        for source in diagnostics["per_source"]
    )
    assert any(
        not source["admission_and_counted_cost_symmetry"]["pre_admission_transaction_path_equal"]
        for source in diagnostics["per_source"]
    )
    assert diagnostics["diagnostic_interpretation"]["paired_contract_error_detected"] is False
    semantic = assessment["semantic_reproducibility"]
    assert semantic["artifact_file_checksums_excluded"] is True
    assert semantic["artifact_integrity_checksums_still_verified_per_run"] is True
    assert len(semantic["semantic_result_sha256"]) == 64
    assert [item["seed"] for item in semantic["source_panel"]] == [
        12301,
        12302,
        12303,
        12304,
    ]
    assert assessment["automatic_keep_or_revert_decision"] is False
    assert assessment["permanent_parameter_retention_authorized"] is False
