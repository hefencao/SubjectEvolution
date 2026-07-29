from __future__ import annotations

from dataclasses import replace
from types import SimpleNamespace
from pathlib import Path

import numpy as np

from se.backend import resolve_backend
from se.cfg import load_config
from se.env.danger_evidence import danger_evidence_quantized
from se.env.gpu import DeviceEnvironment
from se.env.niches import policy_resource_view, resource_affinity_quantized
from se.env.world import Environment
from se.gpu_runtime import (
    GpuTransferStats,
    device_danger_evidence_quantized,
    device_policy_resource_view,
    device_resource_affinity_quantized,
)
from se.policy import ParametricPolicy
from se.runtime.functional_execution import (
    add_physiology_terrain_cost,
    physiology_checkpoint_arrays,
)
from se.runtime.resource_metabolism import storage_room_fraction
from se.runtime.sim import Simulation


ROOT = Path(__file__).resolve().parents[1]


def _cfg():
    base = load_config(ROOT / "configs" / "mvp_short_d3g_spatial_processing_scale1p5_longrun.json")
    return replace(
        base,
        run=replace(
            base.run,
            ticks=3,
            metrics_period=3,
            checkpoint_period=3,
            validation_mode=False,
        ),
        world=replace(
            base.world,
            width=48.0,
            height=48.0,
            grid_x=12,
            grid_y=12,
            initial_entities=64,
            max_entities=96,
        ),
    )


def test_device_preprocessing_matches_reference_bitwise(tmp_path: Path) -> None:
    cfg = _cfg()
    simulation = Simulation(cfg, tmp_path / "simulation", backend="cpu")
    try:
        entity = simulation.entities
        active = np.flatnonzero(entity.alive).astype(np.int32)
        cells = simulation.spatial.build(entity.x, entity.y, entity.alive)
        cell_ids = simulation.spatial.entity_cells[cells]
        local = simulation.environment.cell_values(cell_ids)
        room = storage_room_fraction(
            entity,
            active,
            cfg,
            genotype=entity.genotype[active],
            gene_start=ParametricPolicy.physiology_gene_start(cfg),
        )

        affinity = resource_affinity_quantized(entity.genotype, cfg)
        candidate_affinity = device_resource_affinity_quantized(
            entity.genotype,
            cfg,
            xp=np,
        )
        assert np.array_equal(candidate_affinity, affinity)

        evidence = danger_evidence_quantized(entity.genotype, cfg)
        candidate_evidence = device_danger_evidence_quantized(
            entity.genotype,
            cfg,
            xp=np,
        )
        assert np.array_equal(candidate_evidence, evidence)

        expected_view = policy_resource_view(
            local,
            entity.genotype[active],
            cfg,
            resource_affinity_q=affinity[active],
            storage_room_fraction=room,
        )
        candidate_view = device_policy_resource_view(
            local,
            cfg,
            resource_affinity_q=candidate_affinity[active],
            storage_room_fraction=room,
            xp=np,
        )
        assert np.array_equal(candidate_view, expected_view)
    finally:
        simulation.metrics.close()
        simulation.evolution_progress.close()
        simulation.knowledge.close()


def test_device_physiology_fields_and_gradients_match_reference() -> None:
    cfg = _cfg()
    cpu = Environment(cfg)
    device = DeviceEnvironment(cfg, backend=resolve_backend("cpu"))
    for name in ("oxygen", "terrain", "wear"):
        assert np.array_equal(getattr(device, name), getattr(cpu, name))

    for tick in (0, 1, 17):
        cpu.update(tick)
        device.update(tick)
        for name in ("oxygen", "terrain", "wear"):
            assert np.array_equal(getattr(device, name), getattr(cpu, name))

    cells = np.asarray([0, 1, 11, 12, 143, -1], dtype=np.int32)
    expected_x, expected_y = cpu.oxygen_gradient_for_entities(cells, cells.size)
    candidate_x, candidate_y = device.oxygen_gradient_for_entities(cells, cells.size)
    assert np.array_equal(candidate_x, expected_x)
    assert np.array_equal(candidate_y, expected_y)


def test_gpu_transfer_stats_expose_device_preprocessing_telemetry() -> None:
    stats = GpuTransferStats(
        host_to_device_bytes=128,
        device_to_host_bytes=64,
        device_preprocess_rows=32,
        device_resident_host_bytes_avoided=1024,
    )
    assert stats.device_preprocess_rows == 32
    assert stats.device_resident_host_bytes_avoided == 1024

def test_deferred_gpu_physiology_reads_current_device_cells() -> None:
    cfg = _cfg()
    current = np.asarray(
        [[0.8, 0.25, 0.1], [0.7, 0.75, 0.2]], dtype=np.float32
    )

    class FakeGpuRuntime:
        def physiology_for_cells(self, cell_ids: np.ndarray) -> np.ndarray:
            assert np.array_equal(cell_ids, np.asarray([3, 7], dtype=np.int32))
            return current.copy()

    stale_environment = SimpleNamespace(
        physiology_for_cells=lambda cells: np.zeros((len(cells), 3), dtype=np.float32)
    )
    simulation = SimpleNamespace(
        cfg=cfg,
        gpu_runtime=FakeGpuRuntime(),
        environment=stale_environment,
    )
    cost, observed, moved = add_physiology_terrain_cost(
        simulation,
        current_active=np.asarray([0, 1], dtype=np.int32),
        current_cells=np.asarray([3, 7], dtype=np.int32),
        moved_now=np.asarray([True, False]),
        cost=np.asarray([1.0, 1.0], dtype=np.float64),
    )
    expected_extra = (
        cfg.entities.movement_cost
        * cfg.physiology.terrain_energy_cost_fraction
        * float(current[0, 1])
    )
    assert np.array_equal(observed, current)
    assert np.array_equal(moved, np.asarray([True, False]))
    assert np.allclose(cost, np.asarray([1.0 + expected_extra, 1.0]))


def test_checkpoint_physiology_materializes_device_owned_fields(tmp_path: Path) -> None:
    cfg = _cfg()
    simulation = Simulation(cfg, tmp_path / "checkpoint-fields", backend="cpu")
    fields = tuple(
        np.full((cfg.world.grid_y, cfg.world.grid_x), value, dtype=np.float32)
        for value in (0.2, 0.4, 0.6)
    )

    class FakeGpuRuntime:
        def physiology_fields_to_host(self):
            return tuple(field.copy() for field in fields)

    try:
        simulation.gpu_runtime = FakeGpuRuntime()
        arrays = physiology_checkpoint_arrays(simulation)
        assert np.array_equal(arrays["environment_oxygen"], fields[0])
        assert np.array_equal(arrays["environment_terrain"], fields[1])
        assert np.array_equal(arrays["environment_wear"], fields[2])
    finally:
        simulation.metrics.close()
        simulation.evolution_progress.close()
        simulation.knowledge.close()

def test_large_gpu_presets_preserve_density_and_cell_scale() -> None:
    reference = load_config(
        ROOT / "configs" / "mvp_short_d3g_spatial_processing_scale1p5_longrun.json"
    )
    reference_initial_density = (
        reference.world.initial_entities / (reference.world.width * reference.world.height)
    )
    reference_max_density = (
        reference.world.max_entities / (reference.world.width * reference.world.height)
    )
    reference_cell_width = reference.world.width / reference.world.grid_x
    reference_cell_height = reference.world.height / reference.world.grid_y

    for filename, initial, maximum in (
        ("mvp_d3i_gpu_scale4_longrun.json", 8000, 32768),
        ("mvp_d3i_gpu_scale8_longrun.json", 32000, 131072),
    ):
        cfg = load_config(ROOT / "configs" / filename)
        assert cfg.world.initial_entities == initial
        assert cfg.world.max_entities == maximum
        assert np.isclose(
            cfg.world.initial_entities / (cfg.world.width * cfg.world.height),
            reference_initial_density,
        )
        assert np.isclose(
            cfg.world.max_entities / (cfg.world.width * cfg.world.height),
            reference_max_density,
        )
        assert np.isclose(cfg.world.width / cfg.world.grid_x, reference_cell_width)
        assert np.isclose(cfg.world.height / cfg.world.grid_y, reference_cell_height)
        assert cfg.run.gpu_semantics_mode == "hybrid-accelerated"
        assert cfg.run.validation_mode is False

