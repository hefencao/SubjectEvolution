from __future__ import annotations

from pathlib import Path

from se.analysis.integrated_retention_audit import build_report

ROOT = Path("studies/d1q_integrated_equilibrium_retention_v1/frozen/d1p")


def test_d1p_relative_retention_exposes_contraction_and_demographic_confound() -> None:
    report = build_report(
        gene_persistence=ROOT / "gene_persistence.json",
        long_run_analysis=ROOT / "long_run_analysis.json",
        health_report=ROOT / "panel_health.json",
        config=ROOT / "source_config.json",
    )
    assert report["genome_size"] == 704
    assert report["status_counts"] == {
        "lost": 0,
        "strong_thinning": 6,
        "moderate_thinning": 66,
        "concentrated": 112,
        "retained": 520,
    }
    assert report["demographic_confound"]["active_expansion_seed_count"] == 3
    assert report["adjustment_authorized"] is False
    assert report["per_gene_experiment_generation_authorized"] is False
    severe = {row["name"] for row in report["severe_coordinates"]}
    assert "strategy.rest.fertility" in severe
    assert "functional.module_2.input_21" in severe


def test_missing_equilibrium_report_never_authorizes_adjustment() -> None:
    report = build_report(
        gene_persistence=ROOT / "gene_persistence.json",
        long_run_analysis=ROOT / "long_run_analysis.json",
        health_report=ROOT / "panel_health.json",
        config=ROOT / "source_config.json",
    )
    assert report["equilibrium_report_present"] is False
    assert report["explicit_equilibrium_ready"] is False
    assert report["adjustment_authorized"] is False
