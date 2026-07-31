from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest

from se.cfg import load_config, validate_config
from se.env.diversity import (
    MULTISCALE_PERSISTENT_ENVIRONMENT_SCHEMA,
    configured_resource_scale_metrics,
    persistent_orthogonal_renewal_enabled,
)
from se.env.gpu import DeviceEnvironment
from se.env.world import Environment


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "studies/d1e_persistent_multiscale_resources_v1/protocol/source_pilot.json"


def test_d1e_config_has_four_persistent_spatial_scales() -> None:
    cfg = load_config(CONFIG)
    assert cfg.environment.schema == MULTISCALE_PERSISTENT_ENVIRONMENT_SCHEMA
    assert persistent_orthogonal_renewal_enabled(cfg)
    metrics = configured_resource_scale_metrics(
        cfg.environment, grid_x=cfg.world.grid_x, grid_y=cfg.world.grid_y
    )
    assert metrics["channel_scale_count"] == 4
    assert metrics["primary_wavelength_separation_ratio"] > 3.0


def test_multiscale_schema_rejects_duplicate_primary_scale() -> None:
    cfg = load_config(CONFIG)
    invalid = replace(
        cfg,
        environment=replace(
            cfg.environment,
            resource_primary_wave_vectors=((1.0, 0.0), (0.0, 1.0), (2.0, 1.0), (4.0, -1.0)),
        ),
    )
    with pytest.raises(ValueError, match="four distinct primary spatial scales"):
        validate_config(invalid)


def test_cpu_and_numpy_device_multiscale_fields_match() -> None:
    cfg = load_config(CONFIG)
    host = Environment(cfg)
    device = DeviceEnvironment(cfg, backend="cpu")
    assert np.array_equal(host.resources, device.resources)
    for tick in (1, 17, 63):
        host.update(tick)
        device.update(tick)
        assert np.array_equal(host.resources, device.resources)
