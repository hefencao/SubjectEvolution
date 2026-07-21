"""End-to-end CPU/GPU checks for the hybrid simulation runtime."""

from __future__ import annotations

from dataclasses import replace

import numpy as np
import pytest

from subject_evolution.backend import cupy_available
from subject_evolution.config import load_config
from subject_evolution.simulation import Simulation


@pytest.mark.skipif(not cupy_available(), reason="CuPy with a usable CUDA device is unavailable")
def test_gpu_runtime_preserves_small_world_actions_and_state(tmp_path):
    cfg = load_config("configs/mvp_small.json")
    cfg = replace(cfg, run=replace(cfg.run, ticks=3, metrics_period=99, checkpoint_period=99))
    cpu = Simulation(cfg, tmp_path / "cpu", backend="cpu")
    gpu = Simulation(cfg, tmp_path / "gpu", backend="gpu")
    try:
        for _ in range(3):
            cpu.step()
            gpu.step()

        assert gpu.execution_backend == "gpu"
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
