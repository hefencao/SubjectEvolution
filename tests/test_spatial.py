from __future__ import annotations

import numpy as np
import pytest

from subject_evolution.backend import BackendUnavailableError, cupy_available
from subject_evolution.spatial import SpatialIndex


def _inputs():
    # Include tied cell IDs, an inactive slot, and positions near periodic
    # boundaries so CPU/GPU sorting and cell wrapping are both exercised.
    x = np.asarray([0.1, 1.2, 1.8, 7.9, 8.1, -0.2, 4.4, 4.5], dtype=np.float32)
    y = np.asarray([0.1, 1.1, 1.2, 7.9, 0.1, 3.9, 4.4, 4.5], dtype=np.float32)
    alive = np.asarray([True, True, False, True, True, True, True, True])
    stable_ids = np.asarray([101, 103, 107, 109, 113, 127, 131, 137], dtype=np.uint64)
    return x, y, alive, stable_ids


def test_cpu_spatial_build_uses_cell_then_entity_order():
    x, y, alive, _ = _inputs()
    index = SpatialIndex(grid_x=4, grid_y=4, width=8.0, height=8.0)
    active = index.build(x, y, alive)

    np.testing.assert_array_equal(active, np.asarray([0, 1, 3, 4, 5, 6, 7], dtype=np.int32))
    expected_cells = index.cell_ids(x[active], y[active])
    np.testing.assert_array_equal(index.entity_cells[active], expected_cells)
    np.testing.assert_array_equal(index.sorted_entity_indices, np.asarray([0, 1, 4, 5, 6, 7, 3], dtype=np.int32))
    np.testing.assert_array_equal(index.cell_sizes, np.asarray([3, 0, 0, 0, 0, 0, 0, 1, 0, 0, 2, 0, 0, 0, 0, 1], dtype=np.int32))
    np.testing.assert_array_equal(index.cell_starts, np.asarray([0, 3, 3, 3, 3, 3, 3, 3, 4, 4, 4, 6, 6, 6, 6, 6], dtype=np.int64))


def test_cpu_partner_sampling_is_repeatable_and_never_returns_self():
    x, y, alive, stable_ids = _inputs()
    index = SpatialIndex(grid_x=4, grid_y=4, width=8.0, height=8.0)
    active = index.build(x, y, alive)
    first = index.sample_partners(active, stable_ids, run_seed=43, tick=9, samples=5)
    second = index.sample_partners(active, stable_ids, run_seed=43, tick=9, samples=5)

    np.testing.assert_array_equal(first, second)
    assert first.dtype == np.int32
    assert np.all((first == -1) | (first != active[:, None]))

    selected = first >= 0
    own_cells = index.entity_cells[active]
    partner_cells = index.entity_cells[np.where(selected, first, 0)]
    own_x, own_y = own_cells % index.grid_x, own_cells // index.grid_x
    partner_x, partner_y = partner_cells % index.grid_x, partner_cells // index.grid_x
    dx = np.minimum((own_x[:, None] - partner_x) % index.grid_x, (partner_x - own_x[:, None]) % index.grid_x)
    dy = np.minimum((own_y[:, None] - partner_y) % index.grid_y, (partner_y - own_y[:, None]) % index.grid_y)
    assert np.all((dx <= 1) | ~selected)
    assert np.all((dy <= 1) | ~selected)


@pytest.mark.skipif(not cupy_available(), reason="CuPy with a CUDA device is not available")
def test_gpu_spatial_matches_cpu_reference_for_fixed_seed():
    import cupy as cp

    x, y, alive, stable_ids = _inputs()
    cpu = SpatialIndex(grid_x=4, grid_y=4, width=8.0, height=8.0, backend="cpu")
    cpu_active = cpu.build(x, y, alive)
    cpu_partners = cpu.sample_partners(cpu_active, stable_ids, run_seed=43, tick=9, samples=5)

    try:
        gpu = SpatialIndex(grid_x=4, grid_y=4, width=8.0, height=8.0, backend="gpu")
    except BackendUnavailableError as exc:
        pytest.skip(str(exc))
    gpu_active = gpu.build(cp.asarray(x), cp.asarray(y), cp.asarray(alive))
    gpu_partners = gpu.sample_partners(gpu_active, cp.asarray(stable_ids), run_seed=43, tick=9, samples=5)
    gpu.backend.synchronize()

    np.testing.assert_array_equal(gpu.backend.to_numpy(gpu_active), cpu_active)
    np.testing.assert_array_equal(gpu.backend.to_numpy(gpu.entity_cells), cpu.entity_cells)
    np.testing.assert_array_equal(gpu.backend.to_numpy(gpu.sorted_entity_indices), cpu.sorted_entity_indices)
    np.testing.assert_array_equal(gpu.backend.to_numpy(gpu.cell_sizes), cpu.cell_sizes)
    np.testing.assert_array_equal(gpu.backend.to_numpy(gpu.cell_starts), cpu.cell_starts)
    np.testing.assert_array_equal(gpu.backend.to_numpy(gpu_partners), cpu_partners)
