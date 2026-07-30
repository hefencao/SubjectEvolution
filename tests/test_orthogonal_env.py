from __future__ import annotations

from dataclasses import replace
import json
from pathlib import Path

import numpy as np
import pytest

from se.cfg import load_config, validate_config
from se.env.world import Environment
from se.env.atlas import EnvironmentAtlasDiagnostics
from se.env.diversity import (
    ORTHOGONAL_ENVIRONMENT_SCHEMA,
    build_resource_diversity_audit,
    main as diversity_main,
)
from se.env.gpu import DeviceEnvironment
from se.analysis.protocol_audit import build_protocol_audit
from se.runtime.sim import Simulation


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "configs" / "d0_orthogonal_env_smoke.json"


def test_orthogonal_config_has_independent_resource_axes() -> None:
    cfg = load_config(CONFIG)
    assert cfg.environment.schema == ORTHOGONAL_ENVIRONMENT_SCHEMA
    environment = Environment(cfg)
    metrics = environment.resource_diversity_metrics()
    assert metrics["resource_effective_dimensions"] > 3.5
    assert metrics["resource_channel_max_abs_correlation"] < 0.1


def test_orthogonal_config_rejects_duplicate_primary_modes() -> None:
    cfg = load_config(CONFIG)
    invalid = replace(
        cfg,
        environment=replace(
            cfg.environment,
            resource_primary_wave_vectors=((1.0, 0.0),) * 4,
        ),
    )
    with pytest.raises(ValueError, match="four distinct non-zero modes"):
        validate_config(invalid)


def test_orthogonal_temporal_audit_retains_multiple_dimensions() -> None:
    cfg = load_config(CONFIG)
    report = build_resource_diversity_audit(cfg, ticks=60, sample_period=5)
    assert report["spatial_effective_dimensions_min"] > 3.5
    assert report["resource_temporal_effective_dimensions"] > 3.5
    assert report["resource_temporal_max_abs_correlation"] < 0.15
    assert "does not prove ecological differentiation" in report["interpretation_boundary"]


def test_cpu_and_simulated_device_resource_fields_match() -> None:
    cfg = load_config(CONFIG)
    cpu = Environment(cfg)
    device = DeviceEnvironment(cfg, backend="cpu")
    assert np.array_equal(cpu.resources, device.resources)
    for tick in range(1, 25):
        cpu.update(tick)
        device.update(tick)
        assert np.allclose(cpu.resources, device.resources, atol=1e-7, rtol=1e-7)
        assert np.allclose(cpu.hazard, device.hazard, atol=1e-7, rtol=1e-7)


def test_environment_atlas_v2_reports_resource_only_metrics(tmp_path: Path) -> None:
    cfg = load_config(CONFIG)
    environment = Environment(cfg)
    atlas = EnvironmentAtlasDiagnostics(
        tmp_path,
        world_width=cfg.world.width,
        world_height=cfg.world.height,
        world_grid_x=cfg.world.grid_x,
        world_grid_y=cfg.world.grid_y,
        resource_capacity=cfg.environment.resource_capacity,
        scales=((2, 2), (4, 4)),
        schema="multiscale-subject-environment-atlas-v2",
    )
    alive = np.ones(8, dtype=bool)
    x = np.linspace(0.5, cfg.world.width - 0.5, 8, dtype=np.float32)
    y = np.linspace(cfg.world.height - 0.5, 0.5, 8, dtype=np.float32)
    compact = atlas.observe(
        tick=10,
        resources=environment.resources,
        hazard=environment.hazard,
        mortality_trace=environment.mortality_trace,
        alive=alive,
        x=x,
        y=y,
        lineage_ids=np.arange(8, dtype=np.uint64),
        group_ids=np.asarray([1, 1, 2, 2, 3, 3, 4, 4], dtype=np.uint64),
    )
    assert compact["environment_atlas_2x2_resource_effective_dimensions"] > 1.0
    assert 0.0 <= compact["environment_atlas_2x2_resource_mean_abs_correlation"] <= 1.0
    record = atlas.records[-1]
    scale = record["scales"][0]
    assert len(scale["resource_channel_correlation"]) == 4


def test_simulation_publishes_orthogonal_environment_provenance(tmp_path: Path) -> None:
    cfg = load_config(CONFIG)
    cfg = replace(
        cfg,
        run=replace(
            cfg.run,
            ticks=6,
            metrics_period=3,
            checkpoint_period=3,
            evolution_evaluation_period=3,
            full_checkpoint_enabled=True,
        ),
        world=replace(cfg.world, initial_entities=48, max_entities=64),
    )
    validate_config(cfg)
    run_dir = tmp_path / "run"
    simulation = Simulation(cfg, run_dir, backend="cpu")
    simulation.run(until_tick=6)
    manifest = json.loads((run_dir / "run_manifest.json").read_text())
    assert manifest["environment_resource_dynamics"]["schema"] == ORTHOGONAL_ENVIRONMENT_SCHEMA
    assert manifest["environment_resource_diversity_initial"]["resource_effective_dimensions"] > 3.5
    progress = [json.loads(line) for line in (run_dir / "evolution_progress.jsonl").read_text().splitlines()]
    assert progress[-1]["environment_resource_effective_dimensions"] > 1.0
    assert "environment_resource_channel_mean_abs_correlation" in progress[-1]


def test_legacy_manifest_does_not_gain_orthogonal_fields(tmp_path: Path) -> None:
    cfg = load_config(ROOT / "configs" / "heterogeneous_smoke.json")
    cfg = replace(
        cfg,
        run=replace(cfg.run, ticks=1, metrics_period=1, checkpoint_period=1),
        world=replace(cfg.world, initial_entities=24, max_entities=32),
    )
    simulation = Simulation(cfg, tmp_path / "legacy", backend="cpu")
    simulation.run(until_tick=1)
    manifest = json.loads((tmp_path / "legacy" / "run_manifest.json").read_text())
    assert "environment_resource_dynamics" not in manifest
    assert "environment_resource_diversity_initial" not in manifest


def test_resource_diversity_cli_and_protocol_audit(tmp_path: Path) -> None:
    out = tmp_path / "audit"
    assert diversity_main([
        "--config", str(CONFIG),
        "--output", str(out),
        "--ticks", "20",
        "--sample-period", "5",
    ]) == 0
    report = json.loads((out / "resource_environment_diversity_audit.json").read_text())
    assert report["environment_schema"] == ORTHOGONAL_ENVIRONMENT_SCHEMA
    assert (out / "resource_environment_diversity_audit.md").exists()

    protocol = build_protocol_audit(CONFIG)
    assert protocol["schema"] == "structural-measurement-protocol-audit-v46"
    resource = protocol["resource_environment_protocol"]
    assert resource["schema"] == ORTHOGONAL_ENVIRONMENT_SCHEMA
    assert resource["entity_aware"] is False
    assert len(resource["primary_wave_vectors"]) == 4
    assert len(protocol["audit_sha256"]) == 64
