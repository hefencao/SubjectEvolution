from __future__ import annotations

from dataclasses import asdict, replace
import json
from pathlib import Path

from se.cfg import load_config
from se.experiments.d1_resource_sensing import build_plan, execute_plan
from se.runtime.sim import Simulation


ROOT = Path(__file__).resolve().parents[1]


def _cfg():
    base = load_config(ROOT / "configs/smoke_cpu.json")
    return replace(
        base,
        run=replace(
            base.run,
            seed=831,
            ticks=2,
            metrics_period=1,
            checkpoint_period=1,
            evolution_evaluation_period=10,
            full_checkpoint_enabled=True,
            validation_mode=True,
        ),
        world=replace(
            base.world,
            width=16.0,
            height=16.0,
            grid_x=16,
            grid_y=16,
            initial_entities=12,
            max_entities=16,
        ),
        entities=replace(
            base.entities,
            resource_sensing_schema="inherited-discrete-gradient-radius-v1",
            resource_sensing_radius_levels=(1, 2, 4),
            resource_sensing_maintenance_energy_per_radius=0.001,
            resource_sensing_use_energy_per_radius=0.002,
            resource_sensing_development_energy_per_radius=0.01,
        ),
    )


def test_shared_checkpoint_resource_sensing_calibration(tmp_path: Path) -> None:
    source_root = tmp_path / "runs/base/capability/pilot"
    run_dir = source_root / "seed_831"
    run_dir.mkdir(parents=True)
    cfg = _cfg()
    (run_dir / "resolved_config.json").write_text(
        json.dumps(asdict(cfg), ensure_ascii=False, indent=2), encoding="utf-8"
    )
    simulation = Simulation(cfg, run_dir, backend="cpu")
    try:
        simulation.step()
        simulation.save_full_checkpoint(run_dir / "checkpoint_00000001.sechk")
    finally:
        simulation.metrics.close()
        simulation.evolution_progress.close()
        simulation.knowledge.close()

    plan = build_plan(
        source_root,
        checkpoint_tick=1,
        horizon_ticks=1,
        runtime_root=tmp_path / "runs/interventions/capability/pilot",
    )
    result = execute_plan(plan, backend="cpu")
    assert result["completed_seed_count"] == 1
    assert all(result["contract"].values())
    pair = result["pairs"][0]
    assert pair["shared_checkpoint_state"] is True
    branches = {row["branch"]: row for row in pair["branches"]}
    assert branches["radius-one-neutral"]["effective_radius_mean_at_branch"] == 1.0
    assert branches["radius-one-neutral"]["maintenance_energy_per_tick_at_branch"] > 0
    assert branches["inherited-radius"]["checkpoint_state_sha256"] == branches[
        "radius-one-neutral"
    ]["checkpoint_state_sha256"]
    import pytest

    with pytest.raises(RuntimeError, match="non-empty branch output"):
        execute_plan(plan, backend="cpu")
