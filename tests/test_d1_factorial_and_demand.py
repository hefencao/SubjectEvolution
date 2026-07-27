from __future__ import annotations

from dataclasses import replace
import json
from pathlib import Path

import numpy as np

from se.analysis.long_run import _resource_demand_analysis, analyze
from se.cfg import load_config
from se.experiments.d1_factorial import (
    build_factorial_plan,
    execute_factorial_plan,
    factorial_effects,
    load_factorial_plan,
)
from se.runtime.sim import Simulation


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "configs" / "d1b_selective_harvest_smoke.json"


def _small_cfg(*, ticks: int = 20):
    cfg = load_config(CONFIG)
    return replace(
        cfg,
        run=replace(
            cfg.run,
            ticks=ticks,
            metrics_period=5,
            checkpoint_period=10,
            evolution_evaluation_period=5,
            full_checkpoint_enabled=True,
        ),
        world=replace(
            cfg.world,
            initial_entities=32,
            max_entities=48,
            width=32.0,
            height=32.0,
            grid_x=8,
            grid_y=8,
        ),
    )


def test_requested_harvest_is_published_and_analyzed(tmp_path: Path) -> None:
    cfg = _small_cfg(ticks=10)
    out = tmp_path / "run"
    Simulation(cfg, out, backend="cpu").run(until_tick=10)
    rows = [json.loads(line) for line in (out / "evolution_progress.jsonl").read_text().splitlines()]
    assert rows
    final = rows[-1]
    requested = np.asarray(final["requested_harvest_resources_window"], dtype=np.float64)
    realized = np.asarray(final["harvested_resources_window"], dtype=np.float64)
    assert requested.shape == (4,)
    assert realized.shape == (4,)
    assert requested.sum() >= realized.sum() - 1e-6
    assert np.isclose(
        final["harvest_extraction_efficiency_window"],
        realized.sum() / requested.sum() if requested.sum() else 0.0,
    )

    report = analyze([out / "evolution_progress.jsonl"])
    demand = report["runs"][0]["resource_demand_analysis"]
    assert demand["request_observation_schema"] == "explicit-requested-harvest-window-v1"
    assert len(demand["requested_harvest_channel_shares"]) == 4
    assert "requested_harvest_share_temporal_effective_dimensions" in demand


def test_demand_analysis_separates_common_volume_from_composition() -> None:
    records = []
    fixed_share = np.asarray([0.1, 0.2, 0.3, 0.4], dtype=np.float64)
    for tick, scale in enumerate((1.0, 2.0, 3.0, 4.0, 5.0), start=1):
        requested = fixed_share * scale
        records.append(
            {
                "tick": tick,
                "requested_harvest_resources_window": requested.tolist(),
                "harvested_resources_window": (requested * 0.8).tolist(),
                "environment_resource_effective_dimensions": 2.0,
            }
        )
    result = _resource_demand_analysis(records, {"harvest_request_budget": 1.0})
    assert result["requested_harvest_temporal_effective_dimensions"] > 0.9
    assert result["requested_harvest_share_temporal_effective_dimensions"] == 0.0
    assert result["requested_harvest_channel_mean_abs_correlation"] > 0.99

    varying = []
    shares = (
        [0.7, 0.1, 0.1, 0.1],
        [0.1, 0.7, 0.1, 0.1],
        [0.1, 0.1, 0.7, 0.1],
        [0.1, 0.1, 0.1, 0.7],
        [0.4, 0.3, 0.2, 0.1],
    )
    for tick, share in enumerate(shares, start=1):
        requested = np.asarray(share, dtype=np.float64) * 10.0
        varying.append(
            {
                "tick": tick,
                "requested_harvest_resources_window": requested.tolist(),
                "harvested_resources_window": (requested * 0.8).tolist(),
                "environment_resource_effective_dimensions": 2.0,
            }
        )
    result = _resource_demand_analysis(varying, {"harvest_request_budget": 1.0})
    assert result["requested_harvest_share_temporal_effective_dimensions"] > 2.0



def test_selective_legacy_records_do_not_invent_requested_composition() -> None:
    records = [
        {
            "tick": tick,
            "harvested_resources_window": [1.0, 2.0, 3.0, 4.0],
            "environment_resource_effective_dimensions": 2.0,
            "action_names": ["HARVEST"],
            "window_action_counts": [10],
        }
        for tick in range(1, 6)
    ]
    result = _resource_demand_analysis(
        records,
        {
            "harvest_allocation_schema": "affinity-sampled-exclusive-harvest-v1",
            "harvest_request_budget": 0.78,
            "harvest_rate": 0.3,
            "harvest_channel_multipliers": [0.65, 0.65, 0.65, 0.65],
        },
    )
    assert result["request_observation_schema"] == (
        "requested-channel-composition-unavailable-v1"
    )
    assert result["request_channel_metrics_available"] is False
    assert result["requested_harvest_channel_shares"] == []


def test_progress_restore_defaults_new_request_counter(tmp_path: Path) -> None:
    cfg = _small_cfg(ticks=5)
    sim = Simulation(cfg, tmp_path / "run", backend="cpu")
    state = sim.evolution_progress.snapshot_state()
    state.pop("previous_requested_harvest_resources", None)
    sim.evolution_progress.restore_state(state)
    assert np.array_equal(
        sim.evolution_progress.previous_requested_harvest_resources,
        np.zeros(4, dtype=np.float64),
    )

def test_factorial_effect_definition() -> None:
    effects = factorial_effects(
        {
            "baseline": {"x": 10.0},
            "affinity-neutral": {"x": 7.0},
            "capacity-neutral": {"x": 8.0},
            "combined-neutral": {"x": 4.0},
        }
    )
    assert effects["affinity_expression_effect"]["x"] == 3.0
    assert effects["capacity_expression_effect"]["x"] == 2.0
    assert effects["interaction_effect"]["x"] == -1.0


def test_factorial_plan_executes_four_paired_branches(tmp_path: Path) -> None:
    cfg = _small_cfg(ticks=20)
    source = tmp_path / "source"
    Simulation(cfg, source, backend="cpu").run(until_tick=20)
    plan = build_factorial_plan(
        [source],
        horizon_ticks=5,
        phases=("peak",),
        allow_incomplete_cycle=True,
    )
    assert len(plan.checkpoints) == 1
    report = execute_factorial_plan(plan, tmp_path / "factorial", backend="cpu")
    checkpoint = report["checkpoints"][0]
    assert set(checkpoint["branches"]) == {
        "baseline",
        "affinity-neutral",
        "capacity-neutral",
        "combined-neutral",
    }
    for branch in checkpoint["branches"].values():
        assert branch["world"]["tick"] == plan.checkpoints[0].until_tick
    assert "affinity_expression_effect" in checkpoint["effects"]
    assert (tmp_path / "factorial" / "d1_factorial_results.json").is_file()


def test_factorial_plan_can_be_reused_without_phase_redetection(tmp_path: Path) -> None:
    cfg = _small_cfg(ticks=20)
    source = tmp_path / "source-reuse"
    Simulation(cfg, source, backend="cpu").run(until_tick=20)
    plan = build_factorial_plan(
        [source],
        horizon_ticks=5,
        phases=("peak",),
        allow_incomplete_cycle=True,
    )
    path = tmp_path / "plan.json"
    path.write_text(json.dumps(__import__("dataclasses").asdict(plan)), encoding="utf-8")
    loaded = load_factorial_plan(path)
    assert loaded == plan
