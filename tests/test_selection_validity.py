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
