from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest

from se.cfg import load_config, validate_config
from se.env.gpu import DeviceEnvironment
from se.env.resource_sensing import (
    resource_sensing_energy,
    resource_sensing_radius,
)
from se.env.world import Environment
from se.policy import ParametricPolicy
from se.runtime.sim import Simulation


ROOT = Path(__file__).resolve().parents[1]


def sensing_cfg():
    base = load_config(ROOT / "configs" / "smoke_cpu.json")
    return replace(
        base,
        run=replace(
            base.run,
            ticks=2,
            metrics_period=1,
            checkpoint_period=2,
            evolution_evaluation_period=10,
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


def test_inherited_radius_mapping_and_costs_are_explicit() -> None:
    cfg = sensing_cfg()
    validate_config(cfg)
    genotype = np.zeros((5, ParametricPolicy.genome_size_for_config(cfg)), dtype=np.float32)
    genotype[:, 7] = np.asarray([-1.0, -0.2, 0.0, 0.8, 1.0], dtype=np.float32)
    assert resource_sensing_radius(genotype, cfg).tolist() == [1, 2, 2, 4, 4]
    assert resource_sensing_energy(genotype, cfg).tolist() == pytest.approx(
        [0.001, 0.002, 0.002, 0.004, 0.004]
    )
    assert resource_sensing_energy(genotype, cfg, use=True).tolist() == pytest.approx(
        [0.002, 0.004, 0.004, 0.008, 0.008]
    )
    assert resource_sensing_energy(
        genotype, cfg, development=True
    ).tolist() == pytest.approx([0.01, 0.02, 0.02, 0.04, 0.04])


def test_resource_gradient_uses_per_entity_radius_and_matches_device_cpu() -> None:
    cfg = sensing_cfg()
    host = Environment(cfg)
    device = DeviceEnvironment(cfg, backend="cpu")
    yy, xx = np.mgrid[0 : cfg.world.grid_y, 0 : cfg.world.grid_x]
    field = (xx.astype(np.float32) ** 3 + 0.5 * yy.astype(np.float32) ** 2).astype(
        np.float32
    )
    host.resources[0] = field
    device.resources[0] = field.copy()
    cells = np.full(cfg.world.max_entities, -1, dtype=np.int32)
    coordinates = ((8, 8), (7, 9), (6, 10))
    for index, (x, y) in enumerate(coordinates):
        cells[index] = y * cfg.world.grid_x + x
    radii = np.ones(cfg.world.max_entities, dtype=np.int16)
    radii[:3] = np.asarray([1, 2, 4], dtype=np.int16)

    host_gradient, _ = host.gradients_for_entities(
        cells, cfg.world.max_entities, resource_sensing_radius=radii
    )
    device_gradient, _ = device.gradients_for_entities(
        cells, cfg.world.max_entities, resource_sensing_radius=radii
    )
    assert np.array_equal(host_gradient[0], device_gradient[0])
    assert np.array_equal(host_gradient[1], device_gradient[1])

    expected_x = []
    expected_y = []
    for (x, y), radius in zip(coordinates, (1, 2, 4), strict=True):
        expected_x.append(
            (field[y, (x + radius) % 16] - field[y, (x - radius) % 16])
            / (2.0 * radius)
        )
        expected_y.append(
            (field[(y + radius) % 16, x] - field[(y - radius) % 16, x])
            / (2.0 * radius)
        )
    assert host_gradient[0][:3] == pytest.approx(expected_x)
    assert host_gradient[1][:3] == pytest.approx(expected_y)
    assert len(set(np.round(host_gradient[0][:3], 5).tolist())) == 3


def test_simulation_reports_sensing_capacity_and_energy_costs(tmp_path: Path) -> None:
    cfg = sensing_cfg()
    simulation = Simulation(cfg, tmp_path / "run", backend="cpu")
    try:
        simulation.entities.genotype[: cfg.world.initial_entities, 7] = np.linspace(
            -0.8, 0.8, cfg.world.initial_entities, dtype=np.float32
        )
        stats = simulation.step()
        row = simulation.metric_row(stats, elapsed=0.0)
        assert stats.resource_sensing_maintenance_energy > 0.0
        assert stats.resource_sensing_use_energy > 0.0
        assert row["resource_sensing_schema"] == (
            "inherited-discrete-gradient-radius-v1"
        )
        assert 1.0 <= row["resource_sensing_radius_mean"] <= 4.0
        assert row["resource_sensing_radius_max"] == 4
    finally:
        simulation.metrics.close()
        simulation.evolution_progress.close()
        simulation.knowledge.close()


def test_disabled_sensing_rejects_hidden_costs() -> None:
    base = load_config(ROOT / "configs" / "smoke_cpu.json")
    invalid = replace(
        base,
        entities=replace(
            base.entities,
            resource_sensing_maintenance_energy_per_radius=0.001,
        ),
    )
    with pytest.raises(ValueError, match="disabled resource sensing"):
        validate_config(invalid)


def test_sensing_ablation_preserves_genotype_costs_and_checkpoint_state(
    tmp_path: Path,
) -> None:
    cfg = sensing_cfg()
    simulation = Simulation(cfg, tmp_path / "source", backend="cpu")
    try:
        simulation.entities.genotype[: cfg.world.initial_entities, 7] = 1.0
        genotype_before = simulation.entities.genotype.copy()
        expected_maintenance = float(
            resource_sensing_energy(
                simulation.entities.genotype[simulation.entities.alive], cfg
            ).sum()
        )
        simulation.apply_intervention("neutralize-resource-sensing-radius")
        assert simulation.resource_sensing_ablation_enabled
        assert np.array_equal(simulation.entities.genotype, genotype_before)
        stats = simulation.step()
        row = simulation.metric_row(stats, elapsed=0.0)
        assert stats.resource_sensing_maintenance_energy == pytest.approx(
            expected_maintenance
        )
        assert row["resource_sensing_radius_mean"] == pytest.approx(4.0)
        assert row["resource_sensing_effective_radius_mean"] == pytest.approx(1.0)
        checkpoint = simulation.save_full_checkpoint(tmp_path / "sensing.sechk")
    finally:
        simulation.metrics.close()
        simulation.evolution_progress.close()
        simulation.knowledge.close()

    restored = Simulation.from_checkpoint(
        checkpoint, tmp_path / "restored", backend="cpu", until_tick=2
    )
    try:
        assert restored.resource_sensing_ablation_enabled
        clone = restored.clone(tmp_path / "clone")
        try:
            assert clone.resource_sensing_ablation_enabled
            assert np.array_equal(clone.entities.genotype, restored.entities.genotype)
        finally:
            clone.metrics.close()
            clone.evolution_progress.close()
            clone.knowledge.close()
    finally:
        restored.metrics.close()
        restored.evolution_progress.close()
        restored.knowledge.close()


def test_sensing_ablation_requires_enabled_capacity(tmp_path: Path) -> None:
    cfg = load_config(ROOT / "configs" / "smoke_cpu.json")
    simulation = Simulation(cfg, tmp_path / "disabled", backend="cpu")
    try:
        with pytest.raises(ValueError, match="requires inherited resource sensing"):
            simulation.apply_intervention("neutralize-resource-sensing-radius")
    finally:
        simulation.metrics.close()
        simulation.evolution_progress.close()
        simulation.knowledge.close()
