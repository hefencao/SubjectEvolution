from __future__ import annotations

from dataclasses import replace
import json
from pathlib import Path

import numpy as np

from se.analysis.selection_validity import (
    SelectionValidityThresholds,
    audit_run,
    build_audit,
    main,
)
from se.cfg import load_config, validate_config
from se.runtime.sim import Simulation


ROOT = Path(__file__).resolve().parents[1]


def _write_run(path: Path, rows: list[dict[str, object]]) -> None:
    path.mkdir(parents=True)
    (path / "evolution_progress.jsonl").write_text(
        "\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8"
    )
    final = rows[-1]
    (path / "summary.json").write_text(
        json.dumps(
            {
                "tick": final["tick"],
                "reporting_state_tick": final["tick"],
                "alive": final["alive"],
            }
        )
        + "\n",
        encoding="utf-8",
    )


def _row(
    tick: int,
    *,
    alive: int,
    mean_generation: float,
    max_generation: int,
    births_per_initial: float,
    parents: int,
    births: int,
    deaths: int,
) -> dict[str, object]:
    return {
        "tick": tick,
        "window_ticks": 100,
        "initial_population": 8000,
        "alive": alive,
        "alive_fraction_to_initial": alive / 8000,
        "effective_lineages": 400.0,
        "largest_lineage_fraction": 0.02,
        "selection_successful_parent_samples_window": parents,
        "mean_generation": mean_generation,
        "max_generation": max_generation,
        "cumulative_births_per_initial": births_per_initial,
        "births_window": births,
        "deaths_window": deaths,
        "death_cause_code_counts_window": [0, deaths, 0, 0, 0, 0, 0, 0],
    }


def test_audit_marks_early_population_collapse_before_turnover(tmp_path: Path) -> None:
    run = tmp_path / "scale4"
    _write_run(
        run,
        [
            _row(
                100,
                alive=1000,
                mean_generation=0.05,
                max_generation=1,
                births_per_initial=0.02,
                parents=40,
                births=160,
                deaths=7160,
            ),
            _row(
                200,
                alive=950,
                mean_generation=0.08,
                max_generation=1,
                births_per_initial=0.03,
                parents=30,
                births=80,
                deaths=130,
            ),
        ],
    )
    report = audit_run(
        "scale4", run, thresholds=SelectionValidityThresholds()
    )
    assert report["population_collapse_before_turnover"] is True
    assert report["first_tick_below_population_floor"] == 100
    assert report["selection_inference_supported_within_run"] is False
    assert report["recommendation"].startswith("bottleneck-dominated")
    assert report["death_causes"]["energy_depleted_count"] == 7290


def test_audit_requires_demography_and_generation_turnover(tmp_path: Path) -> None:
    run = tmp_path / "supported"
    _write_run(
        run,
        [
            _row(
                100,
                alive=6000,
                mean_generation=0.4,
                max_generation=2,
                births_per_initial=0.3,
                parents=180,
                births=2400,
                deaths=4400,
            ),
            _row(
                200,
                alive=5900,
                mean_generation=1.2,
                max_generation=4,
                births_per_initial=1.1,
                parents=220,
                births=6400,
                deaths=6500,
            ),
        ],
    )
    report = build_audit([("supported", run)])
    item = report["runs"][0]
    assert item["population_collapse_before_turnover"] is False
    assert item["evolutionary_supported_window_count"] == 1
    assert item["selection_inference_supported_within_run"] is True
    assert report["cross_seed_selection_inference_supported"] is False


def test_cli_writes_fixed_plan_and_keeps_failed_run(tmp_path: Path) -> None:
    run = tmp_path / "run"
    _write_run(
        run,
        [
            _row(
                100,
                alive=900,
                mean_generation=0.0,
                max_generation=0,
                births_per_initial=0.01,
                parents=5,
                births=80,
                deaths=7180,
            )
        ],
    )
    output = tmp_path / "audit"
    assert main(["--run", f"seed= {run}".replace("= ", "="), "--output", str(output)]) == 0
    plan = json.loads((output / "selection_validity_plan.json").read_text())
    result = json.loads((output / "selection_validity_audit.json").read_text())
    assert plan["failed_runs_or_windows_replaced"] is False
    assert plan["feedback_to_world"] is False
    assert result["run_count"] == 1
    assert result["runs"][0]["population_collapse_before_turnover"] is True


def test_runtime_records_canonical_death_causes_and_checkpoints_them(
    tmp_path: Path,
) -> None:
    cfg = load_config(ROOT / "configs" / "heterogeneous_smoke.json")
    cfg = replace(
        cfg,
        run=replace(
            cfg.run,
            ticks=1,
            metrics_period=1,
            checkpoint_period=1,
            evolution_evaluation_period=1,
            full_checkpoint_enabled=True,
            long_run_diagnostics_enabled=True,
            long_run_diagnostics_schema="long-run-evolution-diagnostics-v1",
        ),
        world=replace(cfg.world, initial_entities=16, max_entities=24),
        entities=replace(cfg.entities, max_age=10_000),
    )
    validate_config(cfg)
    sim = Simulation(cfg, tmp_path / "run", backend="cpu")
    active = np.flatnonzero(sim.entities.alive)
    sim.entities.energy[active[0]] = 0.0
    sim.entities.integrity[active[1]] = 0.0
    sim.entities.age[active[2]] = np.uint32(cfg.entities.max_age - 1)
    sim.run(until_tick=1)
    assert sim.total_deaths >= 3
    assert int(sim.total_death_cause_counts[1:].sum()) == sim.total_deaths
    assert sim.total_death_cause_counts[1] >= 1
    assert sim.total_death_cause_counts[2] >= 1
    assert sim.total_death_cause_counts[4] >= 1
    record = sim.evolution_progress.records[-1]
    assert record["initial_population"] == 16
    assert "alive_fraction_to_initial" in record
    assert "descendant_alive_fraction" in record
    assert "selection_unique_successful_parents_window" in record
    assert "selection_effective_successful_parents_window" in record
    assert "selection_largest_parent_contribution_fraction_window" in record
    assert sum(record["death_cause_code_counts_window"][1:]) == record["deaths_window"]

    restored = Simulation.from_checkpoint(
        tmp_path / "run" / "checkpoint_00000001.sechk",
        tmp_path / "restored",
        backend="cpu",
        until_tick=1,
    )
    assert np.array_equal(
        restored.total_death_cause_counts, sim.total_death_cause_counts
    )


def _source_ready_row(
    tick: int,
    *,
    alive: int,
    births: int,
    deaths: int,
    births_per_initial: float,
    mean_generation: float,
    max_generation: int,
) -> dict[str, object]:
    row = _row(
        tick,
        alive=alive,
        mean_generation=mean_generation,
        max_generation=max_generation,
        births_per_initial=births_per_initial,
        parents=220,
        births=births,
        deaths=deaths,
    )
    row.update(
        {
            "descendant_alive_fraction": 0.82,
            "generation_zero_alive": int(alive * 0.18),
            "descendant_alive": int(alive * 0.82),
            "selection_unique_successful_parents_window": 180,
            "selection_effective_successful_parents_window": 150.0,
            "selection_largest_parent_contribution_fraction_window": 0.02,
        }
    )
    return row


def test_audit_distinguishes_rebound_from_source_readiness(tmp_path: Path) -> None:
    run = tmp_path / "rebound"
    rows = [
        _row(
            100,
            alive=1400,
            mean_generation=0.1,
            max_generation=1,
            births_per_initial=0.05,
            parents=40,
            births=400,
            deaths=7000,
        ),
        _row(
            200,
            alive=900,
            mean_generation=0.2,
            max_generation=1,
            births_per_initial=0.1,
            parents=60,
            births=400,
            deaths=900,
        ),
        _row(
            300,
            alive=1050,
            mean_generation=0.4,
            max_generation=2,
            births_per_initial=0.2,
            parents=80,
            births=250,
            deaths=100,
        ),
        _row(
            400,
            alive=1100,
            mean_generation=0.5,
            max_generation=2,
            births_per_initial=0.3,
            parents=90,
            births=150,
            deaths=100,
        ),
    ]
    _write_run(run, rows)
    report = audit_run("rebound", run, thresholds=SelectionValidityThresholds())
    regime = report["post_bottleneck_regime"]
    assert regime["post_trough_rebound_fraction"] > 0.1
    assert regime["source_ready_for_future_independent_runs"] is False
    assert regime["classification"] == (
        "post-bottleneck-active-rebound"
    )


def test_audit_does_not_call_monotonic_rebound_settled(tmp_path: Path) -> None:
    run = tmp_path / "active_rebound"
    rows = [
        _source_ready_row(
            100,
            alive=1000,
            births=100,
            deaths=7100,
            births_per_initial=0.1,
            mean_generation=0.2,
            max_generation=1,
        ),
        *[
            _source_ready_row(
                tick,
                alive=alive,
                births=900,
                deaths=100,
                births_per_initial=1.2,
                mean_generation=2.0,
                max_generation=6,
            )
            for tick, alive in ((200, 1800), (300, 2800), (400, 4000))
        ],
    ]
    _write_run(run, rows)
    report = audit_run("active", run, thresholds=SelectionValidityThresholds())
    regime = report["post_bottleneck_regime"]
    assert regime["active_rebound"] is True
    assert regime["settled_population_supported"] is False
    assert regime["classification"] == "post-bottleneck-active-rebound"


def test_runtime_records_founder_lineage_concentration_profile(tmp_path: Path) -> None:
    cfg = load_config(ROOT / "configs" / "heterogeneous_smoke.json")
    cfg = replace(
        cfg,
        run=replace(
            cfg.run,
            ticks=1,
            metrics_period=1,
            evolution_evaluation_period=1,
            long_run_diagnostics_enabled=True,
            long_run_diagnostics_schema="long-run-evolution-diagnostics-v1",
        ),
        world=replace(cfg.world, initial_entities=16, max_entities=24),
    )
    sim = Simulation(cfg, tmp_path / "lineages", backend="cpu")
    sim.run(until_tick=1)
    row = sim.evolution_progress.records[-1]
    assert row["effective_lineages_shannon"] + 1e-12 >= row["effective_lineages"]
    assert row["top_5_lineage_fraction"] >= row["largest_lineage_fraction"]
    assert row["top_10_lineage_fraction"] >= row["top_5_lineage_fraction"]
    assert 0.0 <= row["effective_lineages_fraction_to_initial"] <= 1.0


def test_source_ready_rule_requires_all_independent_seeds(tmp_path: Path) -> None:
    runs: list[tuple[str, Path]] = []
    for seed in (1, 2, 3):
        run = tmp_path / f"seed_{seed}"
        rows = [
            _source_ready_row(
                100,
                alive=1500,
                births=500,
                deaths=7000,
                births_per_initial=0.1,
                mean_generation=0.2,
                max_generation=1,
            ),
            _source_ready_row(
                200,
                alive=1200,
                births=400,
                deaths=450,
                births_per_initial=1.05,
                mean_generation=1.1,
                max_generation=4,
            ),
            _source_ready_row(
                300,
                alive=1220,
                births=180,
                deaths=160,
                births_per_initial=1.08,
                mean_generation=1.2,
                max_generation=4,
            ),
            _source_ready_row(
                400,
                alive=1210,
                births=170,
                deaths=180,
                births_per_initial=1.1,
                mean_generation=1.3,
                max_generation=5,
            ),
        ]
        _write_run(run, rows)
        runs.append((f"seed_{seed}", run))
    report = build_audit(runs)
    assert report["post_bottleneck_source_ready_run_count"] == 3
    assert report["future_fixed_burn_in_rule_supported"] is True
    assert report["future_fixed_burn_in_tick"] == 200
    assert report["plan"]["source_rule_applies_only_to_future_independent_runs"] is True


def test_multi_seed_writes_plan_before_first_simulation_and_auto_audit(
    tmp_path: Path, monkeypatch
) -> None:
    from dataclasses import asdict
    import sys

    from se.cmd import multi_seed

    cfg = load_config(ROOT / "configs" / "heterogeneous_smoke.json")
    cfg = replace(
        cfg,
        run=replace(
            cfg.run,
            ticks=1,
            metrics_period=1,
            checkpoint_period=1,
            evolution_evaluation_period=1,
            full_checkpoint_enabled=True,
            long_run_diagnostics_enabled=True,
            long_run_diagnostics_schema="long-run-evolution-diagnostics-v1",
        ),
        world=replace(cfg.world, initial_entities=16, max_entities=24),
    )
    config_path = tmp_path / "config.json"
    config_path.write_text(json.dumps(asdict(cfg)), encoding="utf-8")
    output = tmp_path / "multi"
    original_simulation = multi_seed.Simulation

    def checked_simulation(*args, **kwargs):
        assert (output / "multi_seed_plan.json").is_file()
        return original_simulation(*args, **kwargs)

    monkeypatch.setattr(multi_seed, "Simulation", checked_simulation)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "se-multi",
            "--config",
            str(config_path),
            "--seeds",
            "68001",
            "--output",
            str(output),
            "--backend",
            "cpu",
        ],
    )
    multi_seed.main()
    plan = json.loads((output / "multi_seed_plan.json").read_text())
    audit = json.loads((output / "selection_validity_audit.json").read_text())
    long_run = json.loads((output / "long_run_analysis.json").read_text())
    assert plan["schema"] == "multi-seed-run-plan-v3"
    assert plan["automatic_selection_validity_audit"] is True
    assert audit["schema"] == "demographic-selection-validity-audit-v3"
    assert long_run["automatic_selection_validity_audit"]["run_count"] == 1


def test_reproductive_contributor_state_uses_stable_ids_and_clones(
    tmp_path: Path,
) -> None:
    cfg = load_config(ROOT / "configs" / "heterogeneous_smoke.json")
    cfg = replace(
        cfg,
        run=replace(
            cfg.run,
            long_run_diagnostics_enabled=True,
            long_run_diagnostics_schema="long-run-evolution-diagnostics-v1",
        ),
        world=replace(cfg.world, initial_entities=8, max_entities=12),
    )
    sim = Simulation(cfg, tmp_path / "run", backend="cpu")
    tracker = sim.evolution_progress
    active = np.flatnonzero(sim.entities.alive).astype(np.int32)
    accepted = np.asarray([active[0], active[0], active[1]], dtype=np.int32)
    tracker.observe_reproduction_traits(
        sim.entities.genotype,
        sim.entities.entity_id,
        eligible_indices=active[:2],
        accepted_parent_indices=accepted,
        newborn_indices=np.empty(0, dtype=np.int32),
    )
    first_id = int(sim.entities.entity_id[active[0]])
    second_id = int(sim.entities.entity_id[active[1]])
    assert tracker.reproduction_parent_stable_id_counts == {
        first_id: 2,
        second_id: 1,
    }
    clone = tracker.clone(tmp_path / "clone")
    clone.reproduction_parent_stable_id_counts[first_id] += 1
    assert tracker.reproduction_parent_stable_id_counts[first_id] == 2
    restored_state = tracker.snapshot_state()
    tracker.reproduction_parent_stable_id_counts.clear()
    tracker.restore_state(restored_state)
    assert tracker.reproduction_parent_stable_id_counts[first_id] == 2
