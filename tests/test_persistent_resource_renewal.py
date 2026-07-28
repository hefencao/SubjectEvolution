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
    RESULT_SCHEMA,
    _resource_ledger,
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
    corrected = residual + environment.total_resource_field_roundoff
    assert np.max(np.abs(corrected) / scale) < 5.0e-10
    assert np.any(np.abs(environment.total_resource_field_roundoff) > 0.0)
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
    assert np.allclose(
        cpu.total_resource_field_roundoff,
        device.total_resource_field_roundoff,
        atol=1.0e-10,
        rtol=1.0e-10,
    )
    assert np.allclose(
        cpu.total_resource_harvest_roundoff,
        device.total_resource_harvest_roundoff,
        atol=1.0e-12,
        rtol=0.0,
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
    assert plan["float32_inventory_roundoff_recorded_separately"] is True
    payload = execute_persistent_resource_renewal(
        cfg,
        [56001, 56002],
        tmp_path / "d3d",
        backend="cpu",
        until_tick=20,
    )
    assert payload["schema"] == RESULT_SCHEMA
    assert payload["completed_seed_count"] == 2
    assert all(row["valid"] for row in payload["external_resource_ledger"])
    for row in payload["external_resource_ledger"]:
        assert max(row["relative_error"]) < 5.0e-10
        assert max(row["unadjusted_relative_error"]) >= max(row["relative_error"])
        assert max(row["numerical_adjustment_fraction"]) < 2.0e-5
    assert all(row["valid"] for row in payload["external_recycling_ledger"])
    assert payload["stable_trend_summary"]["renewal_source_observed_in_every_seed"]
    assert payload["stable_trend_summary"]["renewal_sink_observed_in_every_seed"]


def test_harvest_commit_records_signed_float32_inventory_settlement() -> None:
    cfg = load_config(NEW_CONFIG)
    environment = Environment(cfg)
    cells = np.asarray([0, 0, 0, 1, 1, 7, 7, 7, 7], dtype=np.int32)
    gathered = np.asarray(
        [
            [0.013, 0.017, 0.019, 0.023],
            [0.029, 0.031, 0.037, 0.041],
            [0.043, 0.047, 0.053, 0.059],
            [0.061, 0.067, 0.071, 0.073],
            [0.079, 0.083, 0.089, 0.097],
            [0.101, 0.103, 0.107, 0.109],
            [0.113, 0.127, 0.131, 0.137],
            [0.139, 0.149, 0.151, 0.157],
            [0.163, 0.167, 0.173, 0.179],
        ],
        dtype=np.float32,
    )
    before = environment.resources.sum(axis=(1, 2), dtype=np.float64)
    intended = gathered.astype(np.float64).sum(axis=0)
    environment.commit_harvest(cells, gathered)
    after = environment.resources.sum(axis=(1, 2), dtype=np.float64)
    expected = before - after - intended
    assert np.allclose(
        environment.resource_harvest_roundoff_step, expected, atol=0.0, rtol=0.0
    )
    assert np.allclose(
        environment.total_resource_harvest_roundoff, expected, atol=0.0, rtol=0.0
    )
    assert np.any(np.abs(expected) > 0.0)


def test_v1_result_without_settlement_fields_is_not_retroactively_reclassified() -> None:
    run = {
        "seed": 56001,
        "final": {
            "resource_initial_total": [100.0] * 4,
            "resource_renewal_source_total": [20.0] * 4,
            "resource_residue_released_total": [10.0] * 4,
            "resource_harvested_total": [25.0] * 4,
            "resource_renewal_sink_total": [5.0] * 4,
            "resource_final_total": [99.999] * 4,
        },
    }
    ledger = _resource_ledger(run)
    assert ledger["field_roundoff"] == [0.0] * 4
    assert ledger["harvest_roundoff"] == [0.0] * 4
    assert ledger["residual"] == ledger["unadjusted_residual"]
    assert ledger["valid"] is False
