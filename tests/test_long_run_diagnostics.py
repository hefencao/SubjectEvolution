from __future__ import annotations

from dataclasses import replace
import json
from pathlib import Path

import numpy as np

from subject_evolution.config import load_config, validate_config
from subject_evolution.evolution import _categorical_alignment, lineage_group_diagnostics
from subject_evolution.long_run_analysis import analyze, render_markdown
from subject_evolution.simulation import Simulation


ROOT = Path(__file__).resolve().parents[1]


def test_categorical_alignment_is_exact_for_identical_partitions() -> None:
    labels = np.asarray([1, 1, 2, 2, 3, 3], dtype=np.uint64)
    result = _categorical_alignment(labels, labels)
    assert np.isclose(result["normalized_mutual_information"], 1.0)
    assert result["left_given_right_purity"] == 1.0
    assert result["right_given_left_purity"] == 1.0
    assert result["same_left_given_same_right"] == 1.0
    assert result["same_right_given_same_left"] == 1.0


def test_lineage_group_diagnostics_excludes_ungrouped_entities() -> None:
    alive = np.ones(6, dtype=bool)
    lineages = np.asarray([1, 1, 2, 2, 3, 3], dtype=np.uint64)
    groups = np.asarray([10, 10, 20, 20, 0, 0], dtype=np.uint64)
    result = lineage_group_diagnostics(alive, lineages, groups)
    assert result["grouped_entity_count"] == 4
    assert result["group_count"] == 2
    assert np.isclose(result["lineage_group_nmi"], 1.0)
    assert result["same_lineage_given_same_group"] == 1.0


def test_long_run_diagnostics_are_opt_in_and_checkpointed(tmp_path: Path) -> None:
    cfg = load_config(ROOT / "configs" / "heterogeneous_smoke.json")
    cfg = replace(
        cfg,
        run=replace(
            cfg.run,
            ticks=6,
            checkpoint_period=3,
            evolution_evaluation_period=3,
            full_checkpoint_enabled=True,
            long_run_diagnostics_enabled=True,
            long_run_diagnostics_schema="long-run-evolution-diagnostics-v1",
        ),
        world=replace(cfg.world, initial_entities=64, max_entities=96),
    )
    validate_config(cfg)
    simulation = Simulation(cfg, tmp_path / "run", backend="cpu")
    simulation.run(until_tick=3)
    record = simulation.evolution_progress.records[-1]
    assert record["long_run_diagnostics_schema"] == "long-run-evolution-diagnostics-v1"
    assert "lineage_group_nmi" in record
    assert record["selection_trait_names"] == [
        "sensor_quality",
        "resource_affinity_0",
        "resource_affinity_1",
        "resource_affinity_2",
        "resource_affinity_3",
        "movement_speed",
    ]
    assert record["knowledge_lineage_diagnostics_schema"] == "knowledge-root-lineage-v1"

    restored = Simulation.from_checkpoint(
        tmp_path / "run" / "checkpoint_00000003.sechk",
        tmp_path / "restored",
        backend="cpu",
        until_tick=6,
    )
    restored.run(until_tick=6)
    assert restored.evolution_progress.records[-1]["tick"] == 6
    assert "selection_differential_parent_minus_eligible" in restored.evolution_progress.records[-1]


def test_disabled_long_run_diagnostics_do_not_change_progress_schema(tmp_path: Path) -> None:
    cfg = load_config(ROOT / "configs" / "heterogeneous_smoke.json")
    cfg = replace(
        cfg,
        run=replace(cfg.run, ticks=1, checkpoint_period=999, evolution_evaluation_period=1),
        world=replace(cfg.world, initial_entities=16, max_entities=24),
    )
    simulation = Simulation(cfg, tmp_path / "run", backend="cpu")
    simulation.run(until_tick=1)
    assert "long_run_diagnostics_schema" not in simulation.evolution_progress.records[-1]
    assert "lineage_group_nmi" not in simulation.evolution_progress.records[-1]


def test_offline_multi_seed_analysis_marks_correlations_observational(tmp_path: Path) -> None:
    paths = []
    for seed in (1, 2):
        path = tmp_path / f"seed_{seed}.jsonl"
        rows = []
        for tick, death, cohesion in ((30, 1, 0.2), (60, 5, 0.4), (90, 2, 0.3)):
            rows.append(
                {
                    "tick": tick,
                    "alive": 100 + seed,
                    "deaths_window": death,
                    "effective_lineages": 10.0 - tick / 30,
                    "largest_lineage_fraction": 0.1 + tick / 1000,
                    "strategy_effective_dimensions": 20.0 - tick / 10,
                    "window_action_entropy": 1.9 - tick / 1000,
                    "benefit_boundary_cohesion": cohesion,
                }
            )
        path.write_text("\n".join(json.dumps(row) for row in rows) + "\n")
        paths.append(path)
    report = analyze(paths)
    assert report["run_count"] == 2
    assert report["schema"] == "multi-seed-long-run-analysis-v8"
    assert "correlations_first_difference" in report["runs"][0]
    assert "correlations_partial" in report["runs"][0]
    assert "observational" in render_markdown(report).lower()


def test_multi_seed_analysis_distinguishes_raw_trend_from_first_difference(
    tmp_path: Path,
) -> None:
    paths = []
    for seed in (1, 2, 3):
        path = tmp_path / f"seed_{seed}" / "evolution_progress.jsonl"
        path.parent.mkdir()
        rows = []
        for index in range(12):
            tick = (index + 1) * 30
            # Both series have a shared trend, while their step-to-step changes
            # alternate independently enough that the raw correlation should be
            # much stronger than the first-difference correlation.
            rows.append(
                {
                    "tick": tick,
                    "alive": 100 + index,
                    "deaths_window": 5 + index + (index % 2),
                    "mortality_pressure_window": 0.05 + 0.005 * index + 0.002 * (index % 2),
                    "effective_lineages": 30.0 - index,
                    "largest_lineage_fraction": 0.05 + index * 0.01,
                    "strategy_effective_dimensions": 40.0 - index,
                    "window_action_entropy": 1.9 - index * 0.01,
                    "benefit_boundary_cohesion": 0.2 + index * 0.02 + 0.01 * ((index + seed) % 3),
                    "lineage_group_pair_enrichment": 1.0 + index * 0.1,
                }
            )
        path.write_text("\n".join(json.dumps(row) for row in rows) + "\n")
        paths.append(path)
    report = analyze(paths)
    raw = report["runs"][0]["correlations_observational"]
    diff = report["runs"][0]["correlations_first_difference"]
    assert abs(raw["mortality_vs_same_window_cohesion"]) > 0.8
    assert abs(diff["delta_mortality_vs_delta_cohesion"]) < abs(
        raw["mortality_vs_same_window_cohesion"]
    )
    consistency = report["cross_seed_sign_consistency"]
    assert (
        consistency[
            "correlations_observational.strategy_dimensions_vs_action_entropy"
        ]["available_runs"]
        == 3
    )


def test_analysis_warns_when_knowledge_transfer_is_not_active(tmp_path: Path) -> None:
    run_dir = tmp_path / "seed_1"
    run_dir.mkdir()
    rows = []
    for index in range(8):
        rows.append(
            {
                "tick": (index + 1) * 30,
                "alive": 100,
                "deaths_window": index + 1,
                "effective_lineages": 20.0 - index,
                "largest_lineage_fraction": 0.1 + index * 0.01,
                "strategy_effective_dimensions": 30.0 - index,
                "window_action_entropy": 1.8 - index * 0.01,
                "benefit_boundary_cohesion": 0.2 + index * 0.01,
                "knowledge_effective_root_contents": 100.0 + index,
                "knowledge_transfer_committed_total": 0,
            }
        )
    progress = run_dir / "evolution_progress.jsonl"
    progress.write_text("\n".join(json.dumps(row) for row in rows) + "\n")
    (run_dir / "resolved_config.json").write_text(
        json.dumps({"knowledge": {"transfer_probability": 0.0}})
    )
    run = analyze([progress])["runs"][0]
    assert run["knowledge_cultural_spread_interpretable"] is False
    assert run["analysis_warnings"]


def test_multi_seed_parser_rejects_duplicates() -> None:
    from subject_evolution.multi_seed import parse_seeds

    assert parse_seeds("10001,10002") == [10001, 10002]
    try:
        parse_seeds("1,1")
    except ValueError as exc:
        assert "unique" in str(exc)
    else:
        raise AssertionError("duplicate seeds were accepted")


def test_multi_seed_completed_tick_uses_progress(tmp_path: Path) -> None:
    from subject_evolution.multi_seed import _completed_tick

    run_dir = tmp_path / "seed_1"
    run_dir.mkdir()
    (run_dir / "evolution_progress.jsonl").write_text(
        json.dumps({"tick": 10, "alive": 2}) + "\n"
        + json.dumps({"tick": 20, "alive": 3}) + "\n",
        encoding="utf-8",
    )
    assert _completed_tick(run_dir) == 20


def test_analysis_requires_committed_transfer_for_cultural_interpretation(tmp_path: Path) -> None:
    run_dir = tmp_path / "configured_but_uncommitted"
    run_dir.mkdir()
    rows = []
    for index in range(8):
        rows.append({
            "tick": (index + 1) * 30,
            "alive": 100,
            "deaths_window": index + 1,
            "effective_lineages": 20.0 - index,
            "largest_lineage_fraction": 0.1 + index * 0.01,
            "strategy_effective_dimensions": 30.0 - index,
            "window_action_entropy": 1.8 - index * 0.01,
            "benefit_boundary_cohesion": 0.2 + index * 0.01,
            "knowledge_transfer_attempts_total": 0,
            "knowledge_transfer_committed_total": 0,
        })
    progress = run_dir / "evolution_progress.jsonl"
    progress.write_text("\n".join(json.dumps(row) for row in rows) + "\n")
    (run_dir / "resolved_config.json").write_text(
        json.dumps({"knowledge": {"transfer_probability": 0.1, "transfer_period": 1}})
    )
    run = analyze([progress])["runs"][0]
    assert run["knowledge_cultural_spread_interpretable"] is False
    assert any("configured" in warning.lower() for warning in run["analysis_warnings"])


def test_analysis_reports_committed_cultural_transfer(tmp_path: Path) -> None:
    run_dir = tmp_path / "committed"
    run_dir.mkdir()
    rows = []
    attempts = 0
    committed = 0
    for index in range(8):
        attempts += 10
        committed += 6
        rows.append({
            "tick": (index + 1) * 30,
            "alive": 100 + index,
            "births_window": 5,
            "deaths_window": 3,
            "effective_lineages": 20.0 - index,
            "largest_lineage_fraction": 0.1 + index * 0.01,
            "strategy_effective_dimensions": 30.0 - index,
            "window_action_entropy": 1.8 - index * 0.01,
            "benefit_boundary_cohesion": 0.2 + index * 0.01,
            "knowledge_transfer_attempts_total": attempts,
            "knowledge_transfer_committed_total": committed,
            "knowledge_transfer_committed_bytes_total": committed * 64,
            "knowledge_transfer_attempts_window": 10,
            "knowledge_transfer_committed_window": 6,
            "knowledge_transfer_cross_lineage_committed_window": 2,
            "knowledge_effective_transferred_roots": 4.0 + index,
        })
    progress = run_dir / "evolution_progress.jsonl"
    progress.write_text("\n".join(json.dumps(row) for row in rows) + "\n")
    run = analyze([progress])["runs"][0]
    assert run["knowledge_cultural_spread_interpretable"] is True
    assert run["knowledge_transfer_committed_final"] == 48
    assert run["knowledge_transfer_commit_rate_after_attention_final"] == 0.6
    assert run["knowledge_transfer_phase_summary"]["rise"]["committed"] > 0
