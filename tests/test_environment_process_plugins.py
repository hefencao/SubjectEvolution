from __future__ import annotations

from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any, Mapping

import numpy as np
import pytest

from subject_evolution.config import load_config, validate_config
from subject_evolution.environment import Environment
from subject_evolution.environment_process import (
    EnvironmentProcessDescriptor,
    LEGACY_MOVING_GAUSSIAN_SCHEMA,
    environment_process_metadata,
    register_environment_process,
    unregister_environment_process,
)
from subject_evolution.gpu_environment import DeviceEnvironment
from subject_evolution.simulation import Simulation


ROOT = Path(__file__).resolve().parents[1]
BASE = (
    ROOT
    / "configs"
    / "mvp_short_latent_l2_memory_topk_inherited_heterogeneous_budget_matched_costed_transfer_mortality_trace_adaptive_groups_longrun.json"
)


def base_config():
    return load_config(BASE)


def legacy_moving_config():
    cfg = base_config()
    return replace(
        cfg,
        environment=replace(
            cfg.environment,
            environment_process_schema="disabled",
            environment_process_parameters={},
            moving_hazard_schema=LEGACY_MOVING_GAUSSIAN_SCHEMA,
            moving_hazard_source_count=3,
            moving_hazard_amplitude=0.3,
            moving_hazard_radius=0.1,
            moving_hazard_speed=0.002,
            moving_hazard_phase_offset=0.37,
        ),
    )


def generic_moving_config():
    cfg = base_config()
    return replace(
        cfg,
        environment=replace(
            cfg.environment,
            environment_process_schema=LEGACY_MOVING_GAUSSIAN_SCHEMA,
            environment_process_parameters={
                "source_count": 3,
                "amplitude": 0.3,
                "radius": 0.1,
                "speed": 0.002,
                "phase_offset": 0.37,
            },
            moving_hazard_schema="disabled",
            moving_hazard_source_count=0,
            moving_hazard_amplitude=0.0,
        ),
    )


def test_generic_plugin_matches_v022_legacy_adapter() -> None:
    legacy_cfg = legacy_moving_config()
    generic_cfg = generic_moving_config()
    validate_config(legacy_cfg)
    validate_config(generic_cfg)
    legacy = Environment(legacy_cfg)
    generic = Environment(generic_cfg)
    np.testing.assert_array_equal(generic.hazard, legacy.hazard)
    for tick in (1, 37, 91):
        legacy.update(tick)
        generic.update(tick)
        np.testing.assert_array_equal(generic.hazard, legacy.hazard)
    assert legacy.environment_process_metadata["origin"] == "v0.22-moving-hazard-adapter"
    assert generic.environment_process_metadata["origin"] == "generic-plugin-config"
    assert generic.environment_process_metadata["mechanism_class"] == (
        "abiotic-additive-scalar-field"
    )


def test_generic_plugin_matches_numpy_device_backend() -> None:
    cfg = generic_moving_config()
    cpu = Environment(cfg)
    device = DeviceEnvironment(cfg, backend="cpu")
    for tick in (0, 17, 53):
        if tick:
            cpu.update(tick)
            device.update(tick)
        np.testing.assert_allclose(device.hazard, cpu.hazard, atol=3e-6, rtol=3e-6)


def test_core_accepts_registered_scalar_field_without_entity_hooks() -> None:
    schema = "test-constant-abiotic-field-v1"
    descriptor = EnvironmentProcessDescriptor(
        schema=schema,
        mechanism_class="abiotic-additive-scalar-field",
        interpretation="test-only",
        description="constant scalar field for extension-boundary validation",
    )
    descriptor_value = descriptor

    @dataclass(frozen=True)
    class ConstantField:
        value: float
        descriptor: EnvironmentProcessDescriptor = descriptor_value

        def hazard_delta(self, *, tick: int, xnorm: Any, ynorm: Any, xp: Any) -> Any:
            del tick, ynorm
            return xp.full_like(xnorm, self.value, dtype=xp.float64)

    def factory(parameters: Mapping[str, Any]) -> ConstantField:
        return ConstantField(float(parameters["value"]))

    register_environment_process(descriptor, factory)
    try:
        base = base_config()
        cfg = replace(
            base,
            environment=replace(
                base.environment,
                environment_process_schema=schema,
                environment_process_parameters={"value": 0.05},
            ),
        )
        validate_config(cfg)
        baseline = Environment(base_config())
        extended = Environment(cfg)
        expected = np.clip(baseline.hazard.astype(np.float64) + 0.05, 0.0, 1.0)
        np.testing.assert_allclose(extended.hazard, expected.astype(np.float32), atol=1e-7, rtol=1e-7)
        metadata = environment_process_metadata(cfg.environment)
        assert metadata["schema"] == schema
        assert metadata["parameter_names"] == ["value"]
    finally:
        unregister_environment_process(schema)


def test_plugin_output_must_be_finite_nonnegative_and_grid_shaped() -> None:
    schema = "test-invalid-field-v1"
    descriptor = EnvironmentProcessDescriptor(
        schema=schema,
        mechanism_class="abiotic-additive-scalar-field",
        interpretation="test-only",
        description="invalid output test",
    )
    descriptor_value = descriptor

    @dataclass(frozen=True)
    class InvalidField:
        descriptor: EnvironmentProcessDescriptor = descriptor_value

        def hazard_delta(self, *, tick: int, xnorm: Any, ynorm: Any, xp: Any) -> Any:
            del tick, ynorm
            return xp.asarray([-1.0], dtype=xp.float64)

    register_environment_process(descriptor, lambda parameters: InvalidField())
    try:
        base = base_config()
        cfg = replace(
            base,
            environment=replace(
                base.environment,
                environment_process_schema=schema,
                environment_process_parameters={},
            ),
        )
        validate_config(cfg)
        with pytest.raises(ValueError, match="grid shape"):
            Environment(cfg)
    finally:
        unregister_environment_process(schema)


def test_synthetic_plugin_is_not_a_scientific_ecology_baseline(tmp_path: Path) -> None:
    cfg = generic_moving_config()
    cfg = replace(
        cfg,
        run=replace(cfg.run, ticks=1, metrics_period=1, checkpoint_period=1),
        world=replace(cfg.world, initial_entities=24, max_entities=32),
    )
    simulation = Simulation(cfg, tmp_path, backend="cpu")
    validity = simulation.scientific_validity()
    assert not validity["structural_evolution_provenance_valid"]
    assert any("synthetic environment process" in item for item in validity["violations"])
    simulation.metrics.close()
    simulation.evolution_progress.close()
    simulation.knowledge.close()


def test_generic_and_legacy_process_configuration_are_mutually_exclusive() -> None:
    cfg = generic_moving_config()
    cfg = replace(
        cfg,
        environment=replace(
            cfg.environment,
            moving_hazard_schema=LEGACY_MOVING_GAUSSIAN_SCHEMA,
            moving_hazard_source_count=1,
            moving_hazard_amplitude=0.1,
        ),
    )
    with pytest.raises(ValueError, match="either environment.environment_process_schema"):
        validate_config(cfg)
