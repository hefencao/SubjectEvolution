from __future__ import annotations

import numpy as np
import pytest

from subject_evolution.backend import BackendUnavailableError, cupy_available
from subject_evolution.config import load_config
from subject_evolution.environment import Environment
from subject_evolution.gpu_environment import DeviceEnvironment, DeviceInformationField
from subject_evolution.information import InformationSystem


def _cfg():
    return load_config("configs/mvp_small.json")


def test_device_environment_cpu_backend_matches_reference():
    cfg = _cfg()
    reference = Environment(cfg)
    device = DeviceEnvironment(cfg, "cpu")
    np.testing.assert_array_equal(device.resources, reference.resources)
    np.testing.assert_array_equal(device.hazard, reference.hazard)

    reference.update(7)
    device.update(7)
    np.testing.assert_allclose(device.resources, reference.resources, rtol=0.0, atol=1e-7)
    np.testing.assert_allclose(device.hazard, reference.hazard, rtol=0.0, atol=1e-7)

    cells = np.asarray([0, 2, 2, 11], dtype=np.int32)
    rates = np.asarray([[0.2, 0.1, 0.05, 0.02]] * len(cells), dtype=np.float32)
    np.testing.assert_allclose(device.cell_values(cells), reference.cell_values(cells))
    entity_cells = np.asarray([0, -1, 2, 11], dtype=np.int32)
    device_gradients = device.gradients_for_entities(entity_cells, capacity=entity_cells.size)
    reference_gradients = reference.gradients_for_entities(entity_cells, capacity=entity_cells.size)
    for device_pair, reference_pair in zip(device_gradients, reference_gradients):
        for actual, expected in zip(device_pair, reference_pair):
            np.testing.assert_allclose(actual, expected, rtol=0.0, atol=1e-7)
    np.testing.assert_allclose(device.resolve_harvest(cells, rates), reference.resolve_harvest(cells, rates))
    gathered = reference.resolve_harvest(cells, rates)
    reference.commit_harvest(cells, gathered)
    device.commit_harvest(cells, gathered)
    np.testing.assert_allclose(device.resources, reference.resources, rtol=0.0, atol=1e-7)


def test_device_information_field_cpu_backend_matches_reference():
    cfg = _cfg()
    reference = InformationSystem(cfg)
    device = DeviceInformationField(cfg, "cpu")
    cells = np.asarray([0, 2, 2, 11] + [2] * 100, dtype=np.int32)
    values = np.asarray([0.1, 0.2, 0.4, 0.6] + [0.01] * 100, dtype=np.float32)
    reference.emit(1, cells, values)
    device.emit(1, cells, values)
    np.testing.assert_allclose(device.source, reference.source, rtol=0.0, atol=1e-7)
    reference.propagate()
    device.propagate()
    np.testing.assert_allclose(device.field, reference.field, rtol=0.0, atol=1e-7)
    np.testing.assert_array_equal(device.age, reference.age)
    field, age = device.sample(cells)
    np.testing.assert_allclose(field, reference.field.reshape(3, -1)[:, cells].T)
    np.testing.assert_allclose(age, reference.age.reshape(3, -1)[:, cells].T)


def test_device_fields_reject_invalid_cell_ids():
    cfg = _cfg()
    reference = Environment(cfg)
    device = DeviceEnvironment(cfg, "cpu")
    field = DeviceInformationField(cfg, "cpu")
    for invalid in (
        np.asarray([-1], dtype=np.int32),
        np.asarray([2**32], dtype=np.uint64),
        np.asarray([1.5], dtype=np.float32),
    ):
        with pytest.raises(ValueError, match="cell ids"):
            reference.cell_values(invalid)
        with pytest.raises(ValueError, match="cell ids"):
            device.cell_values(invalid)
        with pytest.raises(ValueError, match="cell ids"):
            field.sample(invalid)


@pytest.mark.skipif(not cupy_available(), reason="CuPy is not installed")
def test_gpu_environment_matches_cpu_within_float32_tolerance():
    cfg = _cfg()
    reference = Environment(cfg)
    try:
        device = DeviceEnvironment(cfg, "gpu")
    except BackendUnavailableError as exc:
        pytest.skip(str(exc))
    device.update(11)
    reference.update(11)
    np.testing.assert_allclose(device.to_numpy(device.resources), reference.resources, rtol=2e-6, atol=2e-6)
    np.testing.assert_allclose(device.to_numpy(device.hazard), reference.hazard, rtol=2e-6, atol=2e-6)
    cells = np.asarray([0, 2, 2, 11], dtype=np.int32)
    rates = np.asarray([[0.2, 0.1, 0.05, 0.02]] * len(cells), dtype=np.float32)
    gpu_gathered = device.to_numpy(device.resolve_harvest(cells, rates))
    cpu_gathered = reference.resolve_harvest(cells, rates)
    np.testing.assert_allclose(gpu_gathered, cpu_gathered, rtol=2e-6, atol=2e-6)
    device.commit_harvest(cells, gpu_gathered)
    reference.commit_harvest(cells, cpu_gathered)
    np.testing.assert_allclose(device.to_numpy(device.resources), reference.resources, rtol=2e-6, atol=2e-6)


@pytest.mark.skipif(not cupy_available(), reason="CuPy with a CUDA device is unavailable")
def test_gpu_information_field_matches_cpu_for_duplicate_emissions():
    cfg = _cfg()
    reference = InformationSystem(cfg)
    try:
        device = DeviceInformationField(cfg, "gpu")
    except BackendUnavailableError as exc:
        pytest.skip(str(exc))
    cells = np.asarray([0, 2, 2, 2, 11] + [2] * 100, dtype=np.int32)
    values = np.asarray([0.1, 0.2, 0.4, 0.8, 0.6] + [0.01] * 100, dtype=np.float32)
    reference.emit(2, cells, values)
    device.emit(2, cells, values)
    device.backend.synchronize()
    np.testing.assert_allclose(device.to_numpy(device.source), reference.source, rtol=2e-6, atol=2e-6)

    reference.propagate()
    device.propagate()
    device.backend.synchronize()
    np.testing.assert_allclose(device.to_numpy(device.field), reference.field, rtol=2e-6, atol=2e-6)
    np.testing.assert_array_equal(device.to_numpy(device.age), reference.age)
    field, age = device.sample(cells)
    np.testing.assert_allclose(
        device.to_numpy(field), reference.field.reshape(3, -1)[:, cells].T, rtol=2e-6, atol=2e-6
    )
    np.testing.assert_array_equal(device.to_numpy(age), reference.age.reshape(3, -1)[:, cells].T)
