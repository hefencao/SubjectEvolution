from __future__ import annotations

import numpy as np
import pytest

from subject_evolution.backend import BackendUnavailableError, cupy_available
from subject_evolution.config import load_config
from subject_evolution.environment import Environment
from subject_evolution.gpu_environment import DeviceEnvironment, DeviceInformationField
from subject_evolution.information import (
    DirectMessageObservationPlan,
    InformationSystem,
    SignalEmissionBatch,
    SignalEmissionPlan,
)


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


def test_environment_reversal_is_persistent_and_device_backend_neutral():
    cfg = _cfg()
    reference = Environment(cfg)
    reversed_environment = Environment(cfg)
    device = DeviceEnvironment(cfg, "cpu")
    original_resources = reference.resources.copy()
    original_hazard = reference.hazard.copy()

    reversed_environment.reverse_spatial_orientation()
    device.reverse_spatial_orientation()
    assert reversed_environment.spatial_reversed
    assert device.spatial_reversed
    np.testing.assert_array_equal(
        reversed_environment.resources,
        original_resources[:, ::-1, ::-1],
    )
    np.testing.assert_array_equal(
        reversed_environment.hazard,
        original_hazard[::-1, ::-1],
    )
    np.testing.assert_array_equal(device.resources, reversed_environment.resources)
    np.testing.assert_array_equal(device.hazard, reversed_environment.hazard)

    reference.update(7)
    reversed_environment.update(7)
    device.update(7)
    np.testing.assert_allclose(
        reversed_environment.resources,
        reference.resources[:, ::-1, ::-1],
        rtol=0.0,
        atol=1e-7,
    )
    np.testing.assert_allclose(
        reversed_environment.hazard,
        reference.hazard[::-1, ::-1],
        rtol=0.0,
        atol=1e-7,
    )
    np.testing.assert_allclose(device.resources, reversed_environment.resources)
    np.testing.assert_allclose(device.hazard, reversed_environment.hazard)

    reversed_environment.reverse_spatial_orientation()
    device.reverse_spatial_orientation()
    assert not reversed_environment.spatial_reversed
    assert not device.spatial_reversed
    np.testing.assert_allclose(reversed_environment.resources, reference.resources)
    np.testing.assert_allclose(reversed_environment.hazard, reference.hazard)
    np.testing.assert_allclose(device.resources, reference.resources, rtol=0.0, atol=1e-7)
    np.testing.assert_allclose(device.hazard, reference.hazard, rtol=0.0, atol=1e-7)


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


def test_device_information_field_consumes_sparse_direct_message_plan_on_cpu():
    cfg = _cfg()
    reference_messages = InformationSystem(cfg)
    planned_messages = InformationSystem(cfg)
    source_ids = np.asarray([101, 102, 103], dtype=np.uint64)
    receiver_ids = np.asarray([22, 22, 44], dtype=np.uint64)
    payloads = np.asarray([[0.8, 0.4, 0.2], [0.6, 0.3, 0.1], [0.2, 0.5, 0.7]], dtype=np.float32)
    confidence = np.ones(3, dtype=np.float32)
    for information in (reference_messages, planned_messages):
        information.emit_direct(
            source_ids,
            receiver_ids,
            payloads,
            confidence,
            cfg.run.seed,
            tick=0,
        )
    active = np.asarray([0, 1, 2], dtype=np.int32)
    stable_ids = np.asarray([11, 22, 44], dtype=np.uint64)
    cells = np.asarray([0, 1, 2], dtype=np.int32)
    partners = np.empty((3, 0), dtype=np.int32)
    energy = np.ones(3, dtype=np.float32)
    groups = np.zeros(3, dtype=np.uint64)
    quality = np.ones(3, dtype=np.float32)
    reference = reference_messages.observe(
        active, stable_ids, cells, partners, energy, groups, quality, cfg.run.seed, tick=1
    )
    plan = planned_messages._receive_direct_plan(
        active, stable_ids, quality, cfg.run.seed, tick=1
    )
    device = DeviceInformationField(cfg, "cpu")
    actual = device.observe(
        stable_ids=stable_ids,
        cell_ids=cells,
        partners=partners,
        energy=energy,
        group_id=groups,
        own_group_id=groups,
        sensor_quality=quality,
        direct_message_plan=plan,
        run_seed=cfg.run.seed,
        tick=1,
    )

    np.testing.assert_allclose(actual.signals, reference.signals, rtol=0.0, atol=2e-7)
    np.testing.assert_array_equal(actual.signal_mask, reference.signal_mask)
    assert actual.messages.shape == (active.size, 0, 3)


@pytest.mark.skipif(not cupy_available(), reason="CuPy with a CUDA device is unavailable")
def test_gpu_sparse_direct_message_reduction_matches_cpu_backend():
    cfg = _cfg()
    plan = DirectMessageObservationPlan(
        row_count=3,
        capacity=4,
        receiver_rows=np.asarray([0, 0, 2], dtype=np.int32),
        slots=np.asarray([0, 1, 0], dtype=np.int32),
        payloads=np.asarray(
            [[0.8, 0.4, 0.2], [0.6, 0.3, 0.1], [0.2, 0.5, 0.7]], dtype=np.float32
        ),
        ages=np.asarray([1, 1, 2], dtype=np.uint32),
        confidences=np.asarray([0.9, 0.8, 0.7], dtype=np.float32),
        source_ids=np.asarray([101, 102, 103], dtype=np.uint64),
        corruption=np.asarray([0, 1, 0], dtype=np.uint8),
    )
    cpu = DeviceInformationField(cfg, "cpu")
    try:
        gpu = DeviceInformationField(cfg, "gpu")
    except BackendUnavailableError as exc:
        pytest.skip(str(exc))
    stable_ids = np.asarray([11, 22, 44], dtype=np.uint64)
    cells = np.asarray([0, 1, 2], dtype=np.int32)
    partners = np.empty((3, 0), dtype=np.int32)
    energy = np.ones(3, dtype=np.float32)
    groups = np.zeros(3, dtype=np.uint64)
    quality = np.ones(3, dtype=np.float32)
    arguments = dict(
        stable_ids=stable_ids,
        cell_ids=cells,
        partners=partners,
        energy=energy,
        group_id=groups,
        own_group_id=groups,
        sensor_quality=quality,
        direct_message_plan=plan,
        run_seed=cfg.run.seed,
        tick=3,
    )

    expected = cpu.observe(**arguments)
    actual = gpu.observe(**arguments)
    np.testing.assert_allclose(gpu.to_numpy(actual.signals), expected.signals, rtol=2e-6, atol=2e-6)
    np.testing.assert_array_equal(gpu.to_numpy(actual.signal_mask), expected.signal_mask)


def test_signal_emission_plan_matches_ordered_scalar_channels_on_cpu():
    cfg = _cfg()
    scalar_reference = InformationSystem(cfg)
    planned_reference = InformationSystem(cfg)
    device = DeviceInformationField(cfg, "cpu")
    resource_cells = np.asarray([0, 2, 2, 11] + [2] * 100, dtype=np.int32)
    danger_cells = np.asarray([1, 1, 7, 11], dtype=np.int32)
    social_cells = np.asarray([2, 5, 5], dtype=np.int32)
    resource_strengths = np.asarray([0.1, 0.2, 0.4, 0.6] + [0.01] * 100, dtype=np.float32)
    danger_strengths = np.asarray([0.3, 0.7, 0.2, 0.1], dtype=np.float32)
    social_strengths = np.asarray([0.8, 0.1, 0.5], dtype=np.float32)
    later_danger_strengths = np.asarray([0.05, 0.03], dtype=np.float32)
    plan = SignalEmissionPlan(
        batches=(
            SignalEmissionBatch(0, resource_cells, resource_strengths, emitter="resource"),
            SignalEmissionBatch(1, danger_cells, danger_strengths, emitter="danger"),
            SignalEmissionBatch(2, social_cells, social_strengths, emitter="social"),
        )
    ).append(SignalEmissionBatch(1, np.asarray([1, 7], dtype=np.int32), later_danger_strengths, emitter="alarm"))
    for batch in plan.batches:
        scalar_reference.emit(batch.channel, batch.cell_ids, batch.strengths)
    planned_reference.emit_plan(plan)
    device.emit_plan(plan)
    np.testing.assert_array_equal(planned_reference.source, scalar_reference.source)
    np.testing.assert_array_equal(device.source, scalar_reference.source)


def test_signal_emission_plan_omits_channels_that_are_not_due():
    cfg = _cfg()
    information = InformationSystem(cfg)
    plan = SignalEmissionPlan(
        batches=(
            SignalEmissionBatch(
                0,
                np.asarray([0, 2, 2], dtype=np.int32),
                np.asarray([0.1, 0.2, 0.4], dtype=np.float32),
                emitter="high-frequency-resource",
            ),
        )
    )
    information.emit_plan(plan)
    assert np.all(information.source[1:] == 0.0)


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


@pytest.mark.skipif(not cupy_available(), reason="CuPy with a CUDA device is unavailable")
def test_gpu_information_field_sparse_plan_matches_cpu_channels():
    cfg = _cfg()
    reference = InformationSystem(cfg)
    try:
        device = DeviceInformationField(cfg, "gpu")
    except BackendUnavailableError as exc:
        pytest.skip(str(exc))
    plan = SignalEmissionPlan(
        batches=(
            SignalEmissionBatch(
                0,
                np.asarray([0, 2, 2, 2, 11] + [2] * 100, dtype=np.int32),
                np.asarray([0.1, 0.2, 0.4, 0.8, 0.6] + [0.01] * 100, dtype=np.float32),
                emitter="resource",
            ),
            SignalEmissionBatch(
                2,
                np.asarray([1, 1, 11], dtype=np.int32),
                np.asarray([0.3, 0.5, 0.7], dtype=np.float32),
                emitter="social",
            ),
        )
    )
    reference.emit_plan(plan)
    device.emit_plan(plan)
    device.backend.synchronize()
    np.testing.assert_allclose(device.to_numpy(device.source), reference.source, rtol=2e-6, atol=2e-6)
