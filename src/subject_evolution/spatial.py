from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .backend import Backend, resolve_backend
from .random_api import RandomContext, Stream, uniform01


@dataclass
class SpatialIndex:
    grid_x: int
    grid_y: int
    width: float
    height: float
    periodic: bool = True
    backend: Backend | str = "cpu"

    def __post_init__(self) -> None:
        """Create a regular-grid index on an explicitly selected backend.

        The default stays NumPy so constructing the CPU reference simulation
        has exactly the same execution path as before.  A device caller opts
        in with ``SpatialIndex(..., backend="gpu")``; CuPy is then imported by
        :func:`resolve_backend` only when it is actually requested.
        """
        self.backend = resolve_backend(self.backend) if isinstance(self.backend, str) else self.backend
        if not isinstance(self.backend, Backend):
            raise TypeError("backend must be a Backend or one of: 'auto', 'cpu', or 'gpu'")
        xp = self.backend.xp
        self.cell_count = self.grid_x * self.grid_y
        self.sorted_entity_indices = xp.empty(0, dtype=xp.int32)
        self.cell_starts = xp.zeros(self.cell_count, dtype=xp.int64)
        self.cell_sizes = xp.zeros(self.cell_count, dtype=xp.int32)
        self.entity_cells = xp.empty(0, dtype=xp.int32)

    def cell_ids(self, x: Any, y: Any) -> Any:
        """Return regular-grid cell IDs, preserving the selected array backend."""
        xp = self.backend.xp
        x_values = self.backend.asarray(x)
        y_values = self.backend.asarray(y)
        cx = xp.floor(x_values / self.width * self.grid_x).astype(xp.int64)
        cy = xp.floor(y_values / self.height * self.grid_y).astype(xp.int64)
        if self.periodic:
            cx %= self.grid_x
            cy %= self.grid_y
        else:
            cx = xp.clip(cx, 0, self.grid_x - 1)
            cy = xp.clip(cy, 0, self.grid_y - 1)
        return (cy * self.grid_x + cx).astype(xp.int32)

    def build(self, x: Any, y: Any, alive: Any) -> Any:
        """Build ``(cell_id, entity_index)`` buckets on the selected backend.

        A packed ``(cell_id, entity_index)`` key makes the entity index an
        explicit secondary key.  The CPU reference used a stable cell sort
        over ascending active indices; this is the same ordering while also
        making the GPU tie ordering independent of a device sort
        implementation's stability guarantee.
        """
        xp = self.backend.xp
        x_values = self.backend.asarray(x)
        y_values = self.backend.asarray(y)
        alive_values = self.backend.asarray(alive)
        active = xp.flatnonzero(alive_values).astype(xp.int32)
        cells = self.cell_ids(x_values[active], y_values[active])
        entity_stride = max(int(alive_values.size), 1)
        sort_keys = cells.astype(xp.int64) * entity_stride + active.astype(xp.int64)
        order = xp.argsort(sort_keys)
        self.sorted_entity_indices = active[order]
        sorted_cells = cells[order]
        self.cell_sizes = xp.bincount(sorted_cells, minlength=self.cell_count).astype(xp.int32)
        self.cell_starts = xp.cumsum(self.cell_sizes, dtype=xp.int64) - self.cell_sizes
        self.entity_cells = xp.full(alive_values.shape[0], -1, dtype=xp.int32)
        self.entity_cells[active] = cells
        return active

    def sample_partners(
        self,
        active: Any,
        stable_ids: Any,
        run_seed: int,
        tick: int,
        samples: int,
    ) -> Any:
        """Sample local partners in O(N*K), on CPU or GPU without all-pairs search.

        The index's backend owns every returned buffer.  For GPU use, pass
        ``backend="gpu"`` at construction and keep the entity arrays on that
        backend; the stateless random API derives the same keys from stable
        IDs as the CPU implementation.
        """
        xp = self.backend.xp
        active_indices = self.backend.asarray(active, dtype=xp.int32)
        if samples <= 0:
            return xp.empty((active_indices.size, 0), dtype=xp.int32)
        own_cells = self.entity_cells[active_indices]
        own_cx = own_cells % self.grid_x
        own_cy = own_cells // self.grid_x
        output = xp.full((active_indices.size, samples), -1, dtype=xp.int32)
        ids = self.backend.asarray(stable_ids, dtype=xp.uint64)[active_indices]
        ctx = RandomContext(run_seed, tick, phase=20, stream=Stream.NEIGHBOR_SAMPLE)
        offsets = xp.asarray(
            [(-1, -1), (0, -1), (1, -1), (-1, 0), (0, 0), (1, 0), (-1, 1), (0, 1), (1, 1)],
            dtype=xp.int32,
        )
        for draw in range(samples):
            u_cell = uniform01(ctx, ids, draw_index=draw * 3)
            offset_index = xp.minimum((u_cell * 9).astype(xp.int32), 8)
            cx = own_cx + offsets[offset_index, 0]
            cy = own_cy + offsets[offset_index, 1]
            if self.periodic:
                cx %= self.grid_x
                cy %= self.grid_y
            else:
                cx = xp.clip(cx, 0, self.grid_x - 1)
                cy = xp.clip(cy, 0, self.grid_y - 1)
            target_cells = cy * self.grid_x + cx
            sizes = self.cell_sizes[target_cells]
            valid = sizes > 0
            u_member = uniform01(ctx, ids, draw_index=draw * 3 + 1)
            local_offset = xp.floor(u_member * xp.maximum(sizes, 1)).astype(xp.int64)
            positions = self.cell_starts[target_cells] + local_offset
            # Empty cells can begin at ``active.size``, which is outside the
            # sorted entity array.  Mask before the gather so the GPU path
            # never evaluates such an index; it also removes a host-syncing
            # ``any(valid)`` branch from the device hot path.
            safe_positions = xp.where(valid, positions, 0)
            selected = self.sorted_entity_indices[safe_positions]
            selected = xp.where(valid, selected, -1).astype(xp.int32, copy=False)
            # One deterministic retry when self is sampled.
            retry = valid & (selected == active_indices)
            u_retry = uniform01(ctx, ids, draw_index=draw * 3 + 2)
            retry_offset = xp.floor(u_retry * xp.maximum(sizes, 1)).astype(xp.int64)
            retry_pos = self.cell_starts[target_cells] + retry_offset
            safe_retry_pos = xp.where(retry, retry_pos, 0)
            retry_selected = self.sorted_entity_indices[safe_retry_pos]
            selected = xp.where(retry, retry_selected, selected)
            selected = xp.where(selected == active_indices, -1, selected).astype(xp.int32, copy=False)
            output[:, draw] = selected
        return output
