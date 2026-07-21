import copy

import numpy as np
import pytest

from subject_evolution.backend import (
    CPU_BACKEND,
    BackendUnavailableError,
    backend_from_array,
    cupy_available,
    is_cupy_array,
    resolve_backend,
    to_backend,
    to_numpy,
)


def test_cpu_backend_exposes_numpy_and_synchronizes() -> None:
    backend = resolve_backend("cpu")

    assert backend is CPU_BACKEND
    assert backend.xp is np
    assert not backend.is_gpu
    backend.synchronize()
    assert np.array_equal(backend.to_numpy([1, 2]), np.asarray([1, 2]))
    assert copy.deepcopy(backend) is backend


def test_auto_backend_has_a_usable_selection() -> None:
    backend = resolve_backend("auto")

    assert backend.is_gpu is cupy_available()
    assert backend.name == ("gpu" if backend.is_gpu else "cpu")


def test_unknown_backend_is_rejected() -> None:
    with pytest.raises(ValueError, match="Unknown backend"):
        resolve_backend("metal")


def test_explicit_gpu_request_reports_unavailable_backend() -> None:
    if cupy_available():
        assert resolve_backend("gpu").is_gpu
    else:
        with pytest.raises(BackendUnavailableError):
            resolve_backend("gpu")


def test_cpu_conversion_and_backend_inference() -> None:
    source = [1, 2, 3]
    device_value = to_backend(source, "cpu", dtype=np.float32)

    assert isinstance(device_value, np.ndarray)
    assert device_value.dtype == np.float32
    assert backend_from_array(device_value) is CPU_BACKEND
    assert not is_cupy_array(device_value)
    assert np.array_equal(to_numpy(device_value), np.asarray(source, dtype=np.float32))


@pytest.mark.skipif(not cupy_available(), reason="CuPy with a usable CUDA device is unavailable")
def test_gpu_conversion_round_trip_and_synchronization() -> None:
    backend = resolve_backend("gpu")
    source = np.asarray([1.0, 2.0, 3.0], dtype=np.float32)
    device_value = to_backend(source, backend)

    assert backend.is_gpu
    assert is_cupy_array(device_value)
    assert backend_from_array(device_value).is_gpu
    backend.synchronize()
    assert np.array_equal(backend.to_numpy(device_value), source)
