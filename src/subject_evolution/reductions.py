"""Deterministic segmented reductions shared by CPU and GPU world stages."""

from __future__ import annotations

from typing import Any

import numpy as np

from .backend import Backend, backend_from_array, resolve_backend


def _selected_backend(value: Any, backend: Backend | str | None) -> Backend:
    if backend is None:
        return backend_from_array(value)
    return resolve_backend(backend) if isinstance(backend, str) else backend


def validate_cell_ids(
    cell_ids: Any,
    cell_count: int,
    *,
    backend: Backend | str | None = None,
    allow_missing: bool = False,
) -> Any:
    """Move cell ids to ``backend`` and reject invalid device indices.

    CuPy permits negative advanced indices, which can silently address the
    final element instead of surfacing a world-state bug.  Validate at the
    public stage boundary so CPU and GPU fail identically.
    """
    selected = _selected_backend(cell_ids, backend)
    xp = selected.xp
    raw_cells = selected.asarray(cell_ids)
    if not np.issubdtype(raw_cells.dtype, np.integer):
        raise ValueError("cell ids must use an integer dtype")
    if cell_count <= 0 or cell_count > np.iinfo(np.int32).max:
        raise ValueError("cell_count must fit in a positive int32 index range")
    lower_bound = -1 if allow_missing else 0
    # Validate before narrowing to int32: CuPy/NumPy would otherwise wrap a
    # large uint64 value (for example 2**32) into an apparently valid cell.
    invalid = (raw_cells < lower_bound) | (raw_cells >= cell_count)
    if bool(xp.any(invalid).item()):
        missing_note = " or -1" if allow_missing else ""
        raise ValueError(f"cell ids must be in [0, {cell_count}){missing_note}")
    return raw_cells.astype(xp.int32, copy=False)


def stable_segmented_sum(
    cell_ids: Any,
    values: Any,
    cell_count: int,
    *,
    backend: Backend | str | None = None,
    dtype: Any | None = None,
) -> Any:
    """Sum scalar contributions by cell without scatter-add atomics.

    The reduction uses an explicit ``(cell_id, original_order)`` sort followed
    by one segmented reduction and one unique write per output cell.  It is
    the strict-mode reference for field emissions and resource commits;
    GPU/CPU floating results may still differ at normal FP32 tolerance, but a
    GPU run does not depend on arbitrary atomic update order.
    """
    selected = _selected_backend(cell_ids, backend)
    xp = selected.xp
    cells = validate_cell_ids(cell_ids, cell_count, backend=selected)
    data = selected.asarray(values)
    if data.ndim != 1 or data.shape[0] != cells.shape[0]:
        raise ValueError("values must be a 1-D array with one value per cell id")
    output_dtype = data.dtype if dtype is None else dtype
    output = xp.zeros(cell_count, dtype=output_dtype)
    if int(cells.size) == 0:
        return output

    original_order = xp.arange(cells.size, dtype=xp.int64)
    # CuPy requires an explicit ``(keys, items)`` device array here, unlike
    # NumPy which also accepts a tuple of key arrays.  The last row remains
    # the primary cell key and the first row is the stable original-order tie
    # breaker on both backends.
    order = xp.lexsort(xp.stack((original_order, cells)))
    sorted_cells = cells[order]
    sorted_values = data[order]
    starts = xp.concatenate(
        (
            xp.asarray([0], dtype=xp.int64),
            xp.flatnonzero(sorted_cells[1:] != sorted_cells[:-1]).astype(xp.int64) + 1,
        )
    )
    totals = xp.add.reduceat(sorted_values, starts)
    output[sorted_cells[starts]] = totals.astype(output_dtype, copy=False)
    return output
