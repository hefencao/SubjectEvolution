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


def test_channel_routed_sensing_extends_only_strongest_affinity_channel() -> None:
    from se.env.niches import AFFINITY_SCALE
    from se.env.resource_sensing import resource_sensing_channel_radii

    cfg = replace(
        sensing_cfg(),
        environment=replace(
            sensing_cfg().environment,
            schema="orthogonal-four-resource-niche-v1",
        ),
        entities=replace(
            sensing_cfg().entities,
            resource_affinity_schema="normalized-four-resource-affinity-v1",
            resource_affinity_strength=0.75,
            resource_affinity_min_efficiency=0.25,
            resource_affinity_max_efficiency=1.75,
            resource_sensing_schema="inherited-affinity-routed-gradient-radius-v2",
        ),
    )
    validate_config(cfg)
    genotype = np.zeros((3, ParametricPolicy.genome_size_for_config(cfg)), dtype=np.float32)
    genotype[:, 7] = 1.0
    affinity = np.asarray(
        [
            [2 * AFFINITY_SCALE, AFFINITY_SCALE, AFFINITY_SCALE, 0],
            [AFFINITY_SCALE, 3 * AFFINITY_SCALE, 0, 0],
            [AFFINITY_SCALE, AFFINITY_SCALE, AFFINITY_SCALE, AFFINITY_SCALE],
        ],
        dtype=np.int32,
    )
    radii = resource_sensing_channel_radii(
        genotype, cfg, resource_affinity_q=affinity
    )
    assert radii.tolist() == [[4, 1, 1, 1], [1, 4, 1, 1], [4, 1, 1, 1]]
    assert resource_sensing_energy(genotype, cfg).tolist() == pytest.approx(
        [0.004, 0.004, 0.004]
    )


def test_channel_routed_gradient_preserves_local_other_channels() -> None:
    cfg = replace(
        sensing_cfg(),
        environment=replace(
            sensing_cfg().environment,
            schema="orthogonal-four-resource-niche-v1",
        ),
        entities=replace(
            sensing_cfg().entities,
            resource_affinity_schema="normalized-four-resource-affinity-v1",
            resource_affinity_strength=0.75,
            resource_affinity_min_efficiency=0.25,
            resource_affinity_max_efficiency=1.75,
            resource_sensing_schema="inherited-affinity-routed-gradient-radius-v2",
        ),
    )
    host = Environment(cfg)
    yy, xx = np.mgrid[0 : cfg.world.grid_y, 0 : cfg.world.grid_x]
    for channel in range(4):
        host.resources[channel] = (
            (channel + 1) * xx.astype(np.float32) ** 2
            + yy.astype(np.float32)
        )
    cells = np.full(cfg.world.max_entities, -1, dtype=np.int32)
    cells[0] = 8 * cfg.world.grid_x + 8
    affinity = np.full((cfg.world.max_entities, 4), 4096, dtype=np.int32)
    affinity[0] = np.asarray([8192, 4096, 4096, 0], dtype=np.int32)
    radii = np.ones((cfg.world.max_entities, 4), dtype=np.int16)
    radii[0] = np.asarray([4, 1, 1, 1], dtype=np.int16)
    gradient, _ = host.gradients_for_entities(
        cells,
        cfg.world.max_entities,
        resource_affinity_q=affinity,
        resource_sensing_radius=radii,
    )
    assert np.isfinite(gradient[0][0])
    with pytest.raises(ValueError, match="shaped"):
        host.gradients_for_entities(
            cells,
            cfg.world.max_entities,
            resource_affinity_q=affinity,
            resource_sensing_radius=np.ones((cfg.world.max_entities, 3), dtype=np.int16),
        )


def test_affinity_budgeted_sensing_distributes_fixed_extra_radius_budget() -> None:
    from se.env.niches import AFFINITY_SCALE
    from se.env.resource_sensing import resource_sensing_channel_radii
    from se.gpu_runtime import device_resource_sensing_channel_radii

    cfg = replace(
        sensing_cfg(),
        environment=replace(
            sensing_cfg().environment,
            schema="orthogonal-four-resource-niche-v1",
        ),
        entities=replace(
            sensing_cfg().entities,
            resource_affinity_schema="normalized-four-resource-affinity-v1",
            resource_affinity_strength=0.75,
            resource_affinity_min_efficiency=0.25,
            resource_affinity_max_efficiency=1.75,
            resource_sensing_schema="inherited-affinity-budgeted-gradient-radius-v3",
        ),
    )
    validate_config(cfg)
    genotype = np.zeros((3, ParametricPolicy.genome_size_for_config(cfg)), dtype=np.float32)
    genotype[:, 7] = 1.0  # inherited capacity radius four => three extra units
    affinity = np.asarray(
        [
            [2 * AFFINITY_SCALE, AFFINITY_SCALE, AFFINITY_SCALE, 0],
            [AFFINITY_SCALE, 3 * AFFINITY_SCALE, 0, 0],
            [AFFINITY_SCALE, AFFINITY_SCALE, AFFINITY_SCALE, AFFINITY_SCALE],
        ],
        dtype=np.int32,
    )
    radii = resource_sensing_channel_radii(
        genotype, cfg, resource_affinity_q=affinity
    )
    assert radii.tolist() == [[2, 2, 2, 1], [2, 3, 1, 1], [2, 2, 2, 1]]
    assert np.array_equal((radii - 1).sum(axis=1), np.asarray([3, 3, 3]))
    assert np.array_equal(
        radii,
        device_resource_sensing_channel_radii(
            genotype, cfg, resource_affinity_q=affinity, xp=np
        ),
    )
    assert resource_sensing_energy(genotype, cfg).tolist() == pytest.approx(
        [0.004, 0.004, 0.004]
    )


def test_affinity_budgeted_sensing_keeps_radius_one_capacity_local() -> None:
    from se.env.niches import AFFINITY_SCALE
    from se.env.resource_sensing import resource_sensing_channel_radii

    cfg = replace(
        sensing_cfg(),
        environment=replace(
            sensing_cfg().environment,
            schema="orthogonal-four-resource-niche-v1",
        ),
        entities=replace(
            sensing_cfg().entities,
            resource_affinity_schema="normalized-four-resource-affinity-v1",
            resource_affinity_strength=0.75,
            resource_affinity_min_efficiency=0.25,
            resource_affinity_max_efficiency=1.75,
            resource_sensing_schema="inherited-affinity-budgeted-gradient-radius-v3",
        ),
    )
    genotype = np.zeros((1, ParametricPolicy.genome_size_for_config(cfg)), dtype=np.float32)
    genotype[:, 7] = -1.0
    affinity = np.full((1, 4), AFFINITY_SCALE, dtype=np.int32)
    assert resource_sensing_channel_radii(
        genotype, cfg, resource_affinity_q=affinity
    ).tolist() == [[1, 1, 1, 1]]


def test_demand_gated_budget_preserves_weight_and_radius_budgets() -> None:
    from se.cfg import load_config
    from se.env.niches import AFFINITY_SCALE
    from se.env.resource_sensing import (
        resource_sensing_channel_radii,
        resource_sensing_observation_weights_q,
    )
    from se.gpu_runtime import (
        device_resource_sensing_channel_radii,
        device_resource_sensing_observation_weights_q,
    )

    cfg = load_config(
        "studies/d1h_demand_gated_resource_sensing_v1/protocol/source_pilot.json"
    )
    genotype = np.zeros((3, ParametricPolicy.genome_size_for_config(cfg)), dtype=np.float32)
    genotype[:, 7] = 1.0  # capacity eight => seven extra radius units
    affinity = np.asarray(
        [
            [2 * AFFINITY_SCALE, AFFINITY_SCALE, AFFINITY_SCALE, 0],
            [AFFINITY_SCALE, 3 * AFFINITY_SCALE, 0, 0],
            [AFFINITY_SCALE, AFFINITY_SCALE, AFFINITY_SCALE, AFFINITY_SCALE],
        ],
        dtype=np.int32,
    )
    room = np.asarray(
        [
            [1.0, 0.0, 0.0, 0.0],
            [0.0, 1.0, 0.5, 0.0],
            [0.0, 0.0, 0.0, 0.0],
        ],
        dtype=np.float32,
    )
    weights = resource_sensing_observation_weights_q(
        affinity, cfg, storage_room_fraction=room
    )
    radii = resource_sensing_channel_radii(
        genotype,
        cfg,
        resource_affinity_q=affinity,
        storage_room_fraction=room,
    )
    assert np.array_equal(weights.sum(axis=1), affinity.sum(axis=1))
    assert weights[0].tolist() == [int(affinity[0].sum()), 0, 0, 0]
    assert weights[2].tolist() == affinity[2].tolist()  # all-full fallback
    assert np.array_equal((radii - 1).sum(axis=1), np.asarray([7, 7, 7]))
    assert np.array_equal(
        weights,
        device_resource_sensing_observation_weights_q(
            affinity, cfg, storage_room_fraction=room, xp=np
        ),
    )
    assert np.array_equal(
        radii,
        device_resource_sensing_channel_radii(
            genotype,
            cfg,
            resource_affinity_q=affinity,
            storage_room_fraction=room,
            xp=np,
        ),
    )


def test_demand_gated_sensing_requires_conservative_storage() -> None:
    cfg = replace(
        sensing_cfg(),
        environment=replace(
            sensing_cfg().environment,
            schema="orthogonal-four-resource-niche-v1",
        ),
        entities=replace(
            sensing_cfg().entities,
            resource_affinity_schema="normalized-four-resource-affinity-v1",
            resource_affinity_strength=0.75,
            resource_affinity_min_efficiency=0.25,
            resource_affinity_max_efficiency=1.75,
            resource_sensing_schema=(
                "inherited-demand-gated-affinity-budgeted-gradient-radius-v4"
            ),
        ),
    )
    with pytest.raises(ValueError, match="conservative per-channel storage"):
        validate_config(cfg)
