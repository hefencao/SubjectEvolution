from __future__ import annotations

import json
from pathlib import Path

from subject_evolution.structure_environment_analysis import analyze, render_markdown


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")


def test_analysis_aligns_latest_structure_refresh_to_atlas_ticks(tmp_path: Path) -> None:
    run = tmp_path / "seed_1"
    run.mkdir()
    _write_jsonl(
        run / "subject_structure_transitions.jsonl",
        [
            {"tick": 10, "current_group_count": 2, "current_group_effective_count": 1.8, "member_weighted_predecessor_jaccard": 0.4, "member_weighted_predecessor_inheritance": 0.6, "split_source_count": 1, "merge_target_count": 0},
            {"tick": 30, "current_group_count": 3, "current_group_effective_count": 2.5, "member_weighted_predecessor_jaccard": 0.7, "member_weighted_predecessor_inheritance": 0.8, "split_source_count": 0, "merge_target_count": 1},
        ],
    )
    atlas_rows = []
    for tick, turnover, association in [(20, 0.1, 0.2), (40, 0.2, 0.4), (50, 0.3, 0.6), (60, 0.4, 0.8), (70, 0.5, 1.0)]:
        atlas_rows.append({
            "tick": tick,
            "scales": [{
                "scale": "4x4",
                "region_signature_effective_dimensions": 2.0,
                "region_signature_mean_pairwise_distance": 0.5,
                "region_signature_temporal_turnover": turnover,
                "resource_spatial_cv_mean": 0.2,
                "lineage_environment_association_fraction": association,
                "lineage_subject_covered_fraction": 0.8,
                "lineage_mean_region_span_fraction": 0.3,
                "social_environment_association_fraction": association,
                "social_subject_covered_fraction": 0.9,
                "social_mean_region_span_fraction": 0.4,
            }],
        })
    _write_jsonl(run / "environment_atlas.jsonl", atlas_rows)
    report = analyze([run])
    summary = report["runs"][0]["scale_summaries"]["4x4"]
    assert summary["final"]["structure_tick"] == 30
    assert summary["final"]["active_groups"] == 3
    assert summary["correlations"]["environment_turnover_vs_subject_jaccard"] is not None
    assert "Scale 4x4" in render_markdown(report)


def test_analysis_handles_missing_diagnostics(tmp_path: Path) -> None:
    run = tmp_path / "empty"
    run.mkdir()
    report = analyze([run])
    assert report["available_run_count"] == 0
    assert report["runs"][0]["available"] is False
