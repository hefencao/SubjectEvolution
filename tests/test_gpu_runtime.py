"""End-to-end CPU/GPU checks for the hybrid simulation runtime."""

from __future__ import annotations

from dataclasses import replace

import numpy as np
import pytest

from subject_evolution.backend import cupy_available
from subject_evolution.config import load_config
from subject_evolution.environment import Environment
from subject_evolution.execution import (
    ActionResolutionSnapshot,
    DeterministicActionConflictResolver,
    GpuActionConflictResolver,
)
from subject_evolution.gpu_runtime import HybridGpuRuntime
from subject_evolution.information import InformationSystem
from subject_evolution.intents import ActionIntentBatch
from subject_evolution.policy import Action
from subject_evolution.simulation import Simulation


@pytest.mark.skipif(not cupy_available(), reason="CuPy with a usable CUDA device is unavailable")
def test_gpu_runtime_preserves_small_world_actions_and_state(tmp_path):
    cfg = load_config("configs/mvp_small.json")
    cfg = replace(
        cfg,
        run=replace(
            cfg.run,
            ticks=3,
            metrics_period=99,
            checkpoint_period=99,
            gpu_harvest_conflict_planner=True,
        ),
    )
    cpu = Simulation(cfg, tmp_path / "cpu", backend="cpu")
    gpu = Simulation(cfg, tmp_path / "gpu", backend="gpu")
    try:
        for _ in range(3):
            cpu.step()
            gpu_stats = gpu.step()
            assert gpu_stats.gpu_h2d_bytes > 0
            assert gpu_stats.gpu_d2h_bytes > 0
            assert gpu_stats.gpu_direct_dense_bytes_avoided > 0

        assert gpu.execution_backend == "gpu"
        assert isinstance(gpu.conflict_resolver, GpuActionConflictResolver)
        assert np.array_equal(cpu.entities.alive, gpu.entities.alive)
        assert np.array_equal(cpu.entities.entity_id, gpu.entities.entity_id)
        assert np.array_equal(cpu.action_counts, gpu.action_counts)
        np.testing.assert_allclose(cpu.entities.x, gpu.entities.x, rtol=0.0, atol=5e-4)
        np.testing.assert_allclose(cpu.entities.y, gpu.entities.y, rtol=0.0, atol=5e-4)
        np.testing.assert_allclose(cpu.entities.energy, gpu.entities.energy, rtol=0.0, atol=2e-5)
        np.testing.assert_allclose(cpu.environment.resources, gpu.environment.resources, rtol=0.0, atol=2e-4)
        np.testing.assert_allclose(cpu.information.field, gpu.information.field, rtol=0.0, atol=3e-5)
    finally:
        cpu.metrics.close()
        gpu.metrics.close()


@pytest.mark.skipif(not cupy_available(), reason="CuPy with a usable CUDA device is unavailable")
def test_persistent_entity_mirror_matches_every_authoritative_commit(tmp_path):
    cfg = load_config("configs/mvp_small.json")
    cfg = replace(
        cfg,
        run=replace(cfg.run, ticks=4, metrics_period=99, checkpoint_period=99),
    )
    sim = Simulation(cfg, tmp_path / "persistent-entity", backend="gpu")
    try:
        for expected_version in range(1, 5):
            stats = sim.step()
            state = sim.gpu_runtime.entity_state
            assert state is not None
            assert state.version == expected_version
            assert sim.entity_device_version == expected_version
            assert stats.gpu_entity_commit_bytes > 0
            assert sim.last_entity_device_commit is not None
            assert (
                stats.gpu_entity_commit_bytes
                == sim.last_entity_device_commit.semantic_transfer_nbytes
            )
            to_host = sim.gpu_runtime.backend.to_numpy
            np.testing.assert_array_equal(to_host(state.x), sim.entities.x)
            np.testing.assert_array_equal(to_host(state.y), sim.entities.y)
            np.testing.assert_array_equal(to_host(state.alive), sim.entities.alive)
            np.testing.assert_array_equal(to_host(state.stable_ids), sim.entities.entity_id)
            np.testing.assert_array_equal(to_host(state.energy), sim.entities.energy)
            np.testing.assert_array_equal(to_host(state.integrity), sim.entities.integrity)
            np.testing.assert_array_equal(to_host(state.fertility), sim.entities.fertility)
            np.testing.assert_array_equal(to_host(state.genotype), sim.entities.genotype)
            np.testing.assert_array_equal(to_host(state.memory), sim.entities.memory)
            np.testing.assert_array_equal(
                to_host(state.sensor_quality), sim.entities.sensor_quality()
            )
            np.testing.assert_array_equal(to_host(state.group_ids), sim.social.group_id)
            np.testing.assert_array_equal(to_host(state.group_dir_x), sim.social.group_dir_x)
            np.testing.assert_array_equal(to_host(state.group_dir_y), sim.social.group_dir_y)

        assert sim.last_entity_device_commit is not None
        with pytest.raises(ValueError, match="commit is stale"):
            sim.gpu_runtime.apply_entity_commit(sim.last_entity_device_commit)
    finally:
        sim.metrics.close()


@pytest.mark.skipif(not cupy_available(), reason="CuPy with a usable CUDA device is unavailable")
def test_entity_commit_is_smaller_than_a_full_observation_mirror(tmp_path):
    cfg = load_config("configs/mvp_small.json")
    sim = Simulation(cfg, tmp_path / "entity-transfer", backend="gpu")
    try:
        sim.step()
        stats = sim.step()
        entity = sim.entities
        social = sim.social
        full_mirror_bytes = sum(
            value.nbytes
            for value in (
                entity.x,
                entity.y,
                entity.alive,
                entity.entity_id,
                entity.energy,
                entity.integrity,
                entity.fertility,
                entity.genotype,
                entity.memory,
                entity.sensor_quality(),
                social.group_id,
                social.group_dir_x,
                social.group_dir_y,
            )
        )
        assert 0 < stats.gpu_entity_commit_bytes < full_mirror_bytes
    finally:
        sim.metrics.close()


@pytest.mark.skipif(not cupy_available(), reason="CuPy with a usable CUDA device is unavailable")
def test_gpu_harvest_resolver_matches_reference_plan_without_mutating_fields():
    cfg = load_config("configs/mvp_small.json")
    environment = Environment(cfg)
    runtime = HybridGpuRuntime(cfg, backend="gpu")
    runtime.sync_from_host(environment, InformationSystem(cfg))
    entity_id = np.asarray([30, 10, 20, 0], dtype=np.uint64)
    snapshot = ActionResolutionSnapshot(
        active=np.asarray([0, 1, 2], dtype=np.int32),
        cells=np.asarray([5, 1, 5], dtype=np.int32),
        entity_id=entity_id,
        alive=np.asarray([True, True, True, False]),
        energy=np.asarray([1.8, 1.0, 1.4, 0.0], dtype=np.float32),
        fertility=np.asarray([1.0, 1.0, 1.0, 0.0], dtype=np.float32),
        primary_subject_id=np.asarray([300, 100, 200, 0], dtype=np.uint64),
        free_slot_count=0,
    )
    intents = ActionIntentBatch(
        intent_id=np.asarray([1, 2, 3], dtype=np.uint64),
        carrier_index=np.asarray([0, 1, 2], dtype=np.int32),
        carrier_id=entity_id[:3].copy(),
        action=np.asarray([Action.HARVEST, Action.HARVEST, Action.SHARE], dtype=np.int16),
        target_index=np.asarray([-1, -1, 1], dtype=np.int32),
        direction_x=np.zeros(3, dtype=np.float32),
        direction_y=np.zeros(3, dtype=np.float32),
        sampled_probability=np.ones(3, dtype=np.float32),
        submit_tick=7,
    )
    reference = DeterministicActionConflictResolver(cfg).resolve(
        snapshot, intents, environment.resolve_harvest
    )
    fields_before = runtime.backend.to_numpy(runtime.environment.resources).copy()
    resolver = GpuActionConflictResolver(cfg)
    resolver.bind_harvest_planner(runtime)
    allocator_calls = 0

    def unexpected_cpu_allocator(cells, rates):
        nonlocal allocator_calls
        allocator_calls += 1
        return environment.resolve_harvest(cells, rates)

    actual = resolver.resolve(snapshot, intents, unexpected_cpu_allocator)

    assert allocator_calls == 0
    np.testing.assert_array_equal(actual.harvest_rows, reference.harvest_rows)
    np.testing.assert_array_equal(actual.harvest_cells, reference.harvest_cells)
    np.testing.assert_allclose(actual.gathered, reference.gathered, rtol=0.0, atol=2e-6)
    np.testing.assert_array_equal(actual.resolutions.success, reference.resolutions.success)
    np.testing.assert_array_equal(actual.resolutions.failure_reason, reference.resolutions.failure_reason)
    np.testing.assert_allclose(actual.resolutions.resource_delta, reference.resolutions.resource_delta)
    np.testing.assert_allclose(runtime.backend.to_numpy(runtime.environment.resources), fields_before)


@pytest.mark.skipif(not cupy_available(), reason="CuPy with a usable CUDA device is unavailable")
def test_gpu_harvest_resolver_clone_rebinds_to_branch_runtime(tmp_path):
    cfg = load_config("configs/mvp_small.json")
    cfg = replace(cfg, run=replace(cfg.run, ticks=2, metrics_period=99, checkpoint_period=99))
    source = Simulation(cfg, tmp_path / "source", backend="gpu")
    branch = source.clone(tmp_path / "branch")
    try:
        assert isinstance(source.conflict_resolver, GpuActionConflictResolver)
        assert isinstance(branch.conflict_resolver, GpuActionConflictResolver)
        assert branch.conflict_resolver is not source.conflict_resolver

        source.step()
        branch.step()
        np.testing.assert_allclose(branch.entities.energy, source.entities.energy, rtol=0.0, atol=2e-5)
        np.testing.assert_allclose(branch.environment.resources, source.environment.resources, rtol=0.0, atol=2e-4)
    finally:
        source.metrics.close()
        branch.metrics.close()


@pytest.mark.skipif(not cupy_available(), reason="CuPy with a usable CUDA device is unavailable")
def test_gpu_run_syncs_deferred_fields_before_returning(tmp_path):
    cfg = load_config("configs/mvp_small.json")
    cfg = replace(cfg, run=replace(cfg.run, ticks=3, metrics_period=99, checkpoint_period=99))
    cpu = Simulation(cfg, tmp_path / "cpu-run", backend="cpu")
    gpu = Simulation(cfg, tmp_path / "gpu-run", backend="gpu")

    cpu.run()
    gpu.run()

    assert gpu.execution_backend == "gpu"
    assert np.array_equal(cpu.entities.alive, gpu.entities.alive)
    np.testing.assert_allclose(cpu.environment.resources, gpu.environment.resources, rtol=0.0, atol=2e-4)
    np.testing.assert_allclose(cpu.information.field, gpu.information.field, rtol=0.0, atol=3e-5)


@pytest.mark.skipif(not cupy_available(), reason="CuPy with a usable CUDA device is unavailable")
def test_gpu_runtime_matches_cpu_with_delayed_signal_channel_flushes(tmp_path):
    cfg = load_config("configs/mvp_small.json")
    cfg = replace(
        cfg,
        run=replace(cfg.run, ticks=4, metrics_period=99, checkpoint_period=99),
        information=replace(cfg.information, signal_flush_periods=(1, 3, 2)),
    )
    cpu = Simulation(cfg, tmp_path / "cpu-delayed-signals", backend="cpu")
    gpu = Simulation(cfg, tmp_path / "gpu-delayed-signals", backend="gpu")
    try:
        for _ in range(4):
            cpu.step()
            gpu.step()

        assert np.array_equal(cpu.action_counts, gpu.action_counts)
        np.testing.assert_allclose(cpu.entities.energy, gpu.entities.energy, rtol=0.0, atol=2e-5)
        np.testing.assert_allclose(cpu.information.field, gpu.information.field, rtol=0.0, atol=3e-5)
    finally:
        cpu.metrics.close()
        gpu.metrics.close()
