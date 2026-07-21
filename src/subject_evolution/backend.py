"""Optional array-backend selection and host/device conversion helpers.

The CPU reference implementation remains NumPy-first.  This module provides
an intentionally small boundary for GPU migration: callers can request a
NumPy or CuPy namespace without making CuPy a required dependency.  It does
not select algorithms or alter any simulation semantics.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

import numpy as np


BackendName = Literal["cpu", "gpu"]
BackendRequest = Literal["auto", "cpu", "gpu"]


class BackendUnavailableError(RuntimeError):
    """Raised when a requested optional execution backend cannot be used."""


@dataclass(frozen=True, slots=True)
class Backend:
    """A selected array namespace and its execution-device metadata.

    ``xp`` is either :mod:`numpy` or :mod:`cupy`.  Keeping the namespace on
    the selected backend lets migration stages use familiar array operations
    while making all host/device transfers explicit at their boundaries.
    """

    name: BackendName
    xp: Any
    is_gpu: bool

    def asarray(self, value: Any, *, dtype: Any | None = None, copy: bool = False) -> Any:
        """Convert ``value`` to an array owned by this backend."""
        if copy:
            return self.xp.array(value, dtype=dtype, copy=True)
        return self.xp.asarray(value, dtype=dtype)

    def synchronize(self) -> None:
        """Wait for queued work on this backend's current execution stream.

        It is a no-op for NumPy.  GPU callers should use it around timing or
        CPU/GPU validation boundaries, rather than adding synchronization to
        ordinary simulation phases.
        """
        if self.is_gpu:
            self.xp.cuda.get_current_stream().synchronize()

    def __copy__(self) -> "Backend":
        """Backends are immutable handles around a module namespace."""
        return self

    def __deepcopy__(self, memo: dict[int, Any]) -> "Backend":
        """Keep snapshot cloning from attempting to pickle NumPy/CuPy modules."""
        memo[id(self)] = self
        return self

    def to_numpy(self, value: Any) -> np.ndarray:
        """Copy a backend-owned array to host NumPy when necessary."""
        return to_numpy(value)


CPU_BACKEND = Backend(name="cpu", xp=np, is_gpu=False)


def _load_cupy() -> Any | None:
    """Import CuPy lazily so CPU installations never require it."""
    try:
        import cupy  # type: ignore[import-not-found]
    except Exception:
        # CuPy can fail during import when its optional CUDA runtime is absent
        # or incompatible.  Treat that exactly like an unavailable optional
        # backend; an explicit ``gpu`` request receives a clear public error.
        return None
    return cupy


def _gpu_backend() -> Backend:
    cupy = _load_cupy()
    if cupy is None:
        raise BackendUnavailableError(
            "GPU backend requires an importable CuPy installation. "
            "Install a CuPy >= 12 build matching the CUDA runtime on this host."
        )
    # The strict field path relies on these device operations instead of
    # floating atomic scatters.  Older CuPy releases can import successfully
    # yet fail only after a simulation starts, so reject them at selection.
    if not callable(getattr(cupy, "lexsort", None)) or not callable(getattr(cupy.add, "reduceat", None)):
        raise BackendUnavailableError(
            "GPU foundation requires CuPy >= 12 with lexsort and ufunc.reduceat support."
        )
    try:
        from cupy.cuda import thrust  # type: ignore[import-not-found]

        thrust_available = bool(thrust.available)
    except Exception as exc:
        raise BackendUnavailableError(
            "GPU foundation requires a CuPy build with Thrust support for deterministic lexsort."
        ) from exc
    if not thrust_available:
        raise BackendUnavailableError(
            "GPU foundation requires a CuPy build with Thrust support for deterministic lexsort."
        )
    try:
        device_count = int(cupy.cuda.runtime.getDeviceCount())
    except Exception as exc:
        raise BackendUnavailableError(
            "CuPy is installed, but no usable CUDA device/runtime was found."
        ) from exc
    if device_count < 1:
        raise BackendUnavailableError("CuPy is installed, but no CUDA device is available.")
    return Backend(name="gpu", xp=cupy, is_gpu=True)


def cupy_available() -> bool:
    """Return whether CuPy and at least one CUDA device are usable now."""
    try:
        _gpu_backend()
    except BackendUnavailableError:
        return False
    return True


def resolve_backend(requested: BackendRequest | str = "auto") -> Backend:
    """Resolve ``'cpu'``, ``'gpu'``, or ``'auto'`` to an array backend.

    ``auto`` prefers CuPy only when its CUDA runtime and a device are usable;
    otherwise it falls back to the NumPy CPU backend.  Code that must preserve
    the CPU reference path should request ``'cpu'`` explicitly.
    """
    if not isinstance(requested, str):
        raise TypeError("backend request must be one of: 'auto', 'cpu', or 'gpu'")
    normalized = requested.strip().lower()
    if normalized == "cpu":
        return CPU_BACKEND
    if normalized == "gpu":
        return _gpu_backend()
    if normalized == "auto":
        try:
            return _gpu_backend()
        except BackendUnavailableError:
            return CPU_BACKEND
    raise ValueError(
        f"Unknown backend {requested!r}; expected one of: 'auto', 'cpu', or 'gpu'."
    )


def is_cupy_array(value: Any) -> bool:
    """Return whether ``value`` is a CuPy ndarray without requiring CuPy."""
    cupy = _load_cupy()
    return bool(cupy is not None and isinstance(value, cupy.ndarray))


def backend_from_array(value: Any) -> Backend:
    """Infer the owning backend of an existing NumPy or CuPy array.

    Non-array inputs and NumPy-compatible arrays are treated as CPU values.
    This is useful for low-level utilities that must preserve the backend of
    their input without choosing a device independently.
    """
    if is_cupy_array(value):
        cupy = _load_cupy()
        assert cupy is not None  # Narrowed by is_cupy_array above.
        return Backend(name="gpu", xp=cupy, is_gpu=True)
    return CPU_BACKEND


def to_numpy(value: Any) -> np.ndarray:
    """Return a host NumPy array, explicitly copying CuPy arrays when needed."""
    if is_cupy_array(value):
        cupy = _load_cupy()
        assert cupy is not None
        return cupy.asnumpy(value)
    return np.asarray(value)


def to_backend(
    value: Any,
    backend: Backend | BackendRequest | str = "auto",
    *,
    dtype: Any | None = None,
    copy: bool = False,
) -> Any:
    """Convert an array-like value to the selected backend's array type."""
    selected = resolve_backend(backend) if isinstance(backend, str) else backend
    if not isinstance(selected, Backend):
        raise TypeError("backend must be a Backend or one of: 'auto', 'cpu', or 'gpu'")
    return selected.asarray(value, dtype=dtype, copy=copy)


__all__ = [
    "Backend",
    "BackendName",
    "BackendRequest",
    "BackendUnavailableError",
    "CPU_BACKEND",
    "backend_from_array",
    "cupy_available",
    "is_cupy_array",
    "resolve_backend",
    "to_backend",
    "to_numpy",
]
