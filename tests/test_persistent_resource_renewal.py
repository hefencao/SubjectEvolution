from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import numpy as np

from se.cfg import load_config, validate_config
from se.env.diversity import (
    PERSISTENT_ORTHOGONAL_ENVIRONMENT_SCHEMA,
    orthogonal_base_pattern,
    orthogonal_renewal_target_fraction,
    normalized_grid,
)
from se.env.gpu import DeviceEnvironment
from se.env.world import Environment
from se.experiments.d3_persistent_resource_renewal import (
    build_plan,
    execute_persistent_resource_renewal,
)

ROOT = Path(__file__).resolve().parents[1]
BASE_CONFIG = ROOT / "configs" / "mvp_short_d3c_external_recycling_longrun.json"
NEW_CONFIG = ROOT / "configs" / "mvp_short_d3d_persistent_resource_renewal_longrun.json"


def test_tick_zero_renewal_target_matches_existing_orthogonal_initial_pattern() -> None:
    cfg = load_config(NEW_CONFIG)
    yy, xx = np.mgrid[0 : cfg.world.grid_y, 0 : cfg.world.grid_x]
    xnorm, ynorm = normalized_grid(
        xx,
        yy,
        grid_x=cfg.world.grid_x,
        grid_y=cfg.world.grid_y,
        xp=np,
    )
    base = orthogonal_base_pattern(cfg.environment, xnorm, ynorm, xp=np)
    target = orthogonal_renewal_target_fraction(
        cfg.environment, xnorm, ynorm, tick=0, xp=np
    )
    assert np.allclose(base, target, atol=1.0e-12, rtol=0.0)


def test_persistent_renewal_records_explicit_source_and_sink_ledger() -> None:
    cfg = load_config(NEW_CONFIG)
    environment = Environment(cfg)
    initial = environment.resources.sum(axis=(1, 2), dtype=np.float64)
    for tick in range(1, 301):
        environment.update(tick)
    final = environment.resources.sum(axis=(1, 2), dtype=np.float64)
    residual = (
        initial
        + environment.total_resource_renewal_source
        - environment.total_resource_renewal_sink
        - final
    )
    scale = np.maximum(1.0, np.maximum(np.abs(initial), np.abs(final)))
    assert np.max(np.abs(residual) / scale) < 1.0e-5
    assert np.all(environment.total_resource_renewal_source > 0.0)
    assert np.all(environment.total_resource_renewal_sink > 0.0)
    metrics = environment.resource_diversity_metrics()
    assert metrics["resource_effective_dimensions"] > 3.0
    assert metrics["resource_channel_mean_abs_correlation"] < 0.2


def test_cpu_and_simulated_device_persistent_renewal_match() -> None:
    cfg = load_config(NEW_CONFIG)
    cpu = Environment(cfg)
    device = DeviceEnvironment(cfg, backend="cpu")
    for tick in range(1, 80):
        cpu.update(tick)
        device.update(tick)
    assert np.allclose(cpu.resources, device.resources, atol=1.0e-7, rtol=1.0e-7)
    assert np.allclose(
        cpu.total_resource_renewal_source,
        device.total_resource_renewal_source,
        atol=1.0e-8,
        rtol=1.0e-8,
    )
    assert np.allclose(
        cpu.total_resource_renewal_sink,
        device.total_resource_renewal_sink,
        atol=1.0e-8,
        rtol=1.0e-8,
    )


def test_new_environment_schema_is_opt_in() -> None:
    legacy = load_config(BASE_CONFIG)
    assert legacy.environment.schema != PERSISTENT_ORTHOGONAL_ENVIRONMENT_SCHEMA
    assert not hasattr(Environment(legacy), "total_resource_renewal_source")
    current = load_config(NEW_CONFIG)
    validate_config(current)
    assert current.environment.schema == PERSISTENT_ORTHOGONAL_ENVIRONMENT_SCHEMA
    assert hasattr(Environment(current), "total_resource_renewal_source")


def test_d3d_plan_and_small_execution_close_external_ledger(tmp_path: Path) -> None:
    cfg = load_config(NEW_CONFIG)
    cfg = replace(
        cfg,
        run=replace(
            cfg.run,
            ticks=20,
            metrics_period=10,
            checkpoint_period=10,
            evolution_evaluation_period=10,
        ),
        world=replace(cfg.world, initial_entities=48, max_entities=96),
    )
    plan = build_plan([56001, 56002], 20)
    assert plan["renewal_schema"] == "moving-target-source-sink-v2"
    payload = execute_persistent_resource_renewal(
        cfg,
        [56001, 56002],
        tmp_path / "d3d",
        backend="cpu",
        until_tick=20,
    )
    assert payload["completed_seed_count"] == 2
    assert all(row["valid"] for row in payload["external_resource_ledger"])
    assert all(row["valid"] for row in payload["external_recycling_ledger"])
    assert payload["stable_trend_summary"]["renewal_source_observed_in_every_seed"]
    assert payload["stable_trend_summary"]["renewal_sink_observed_in_every_seed"]
