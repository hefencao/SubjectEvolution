from __future__ import annotations

from pathlib import Path

import pytest

from se import __version__
from se.analysis.subject_vm_stage3c19_token_geometry import (
    STAGE3C19_TOKEN_GEOMETRY_SCHEMA,
    assess_stage3c19_token_geometry,
)
from se.experiments.subject_vm_short_paired_study import (
    ShortPairedStudyParameters,
    run_short_paired_study,
)


def _run(tmp_path: Path):
    return run_short_paired_study(
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
            association_tie_break="latest",
            association_candidate_limit=1,
        ),
        output_dir=tmp_path / "baseline",
    )


def test_stage3c19_reports_degenerate_visible_geometry(tmp_path: Path) -> None:
    result = assess_stage3c19_token_geometry(_run(tmp_path))
    assert result["schema"] == STAGE3C19_TOKEN_GEOMETRY_SCHEMA
    assert result["producer_version"] == __version__
    assert result["geometry_summary"]["association_visible_ports"] == [29, 30, 31]
    assert result["geometry_summary"]["total_visible_token_count"] == 384
    assert result["geometry_summary"]["all_association_visible_coordinate_variances_zero"]
    assert result["geometry_summary"]["centered_covariance_rank_per_source"] == [0, 0, 0]
    assert result["geometry_summary"]["uncentered_second_moment_rank_per_source"] == [1, 1, 1]
    assert result["score_separability"]["eligible_query_candidate_pair_count"] == 1296
    assert result["score_separability"]["exact_query_candidate_vector_equality_fraction"] == 1.0
    assert result["score_separability"]["all_eligible_scores_equal_one"]
    assert result["score_separability"]["all_best_second_score_spreads_zero"]
    assert result["runtime_state_changed"] is False
    assert result["permanent_parameter_retention_authorized"] is False
    assert result["learning_claim_authorized"] is False


def test_stage3c19_rejects_non_frozen_candidate_limit(tmp_path: Path) -> None:
    report = _run(tmp_path)
    report["parameters"]["association_candidate_limit"] = 2
    with pytest.raises(ValueError, match="association_candidate_limit"):
        assess_stage3c19_token_geometry(report)
