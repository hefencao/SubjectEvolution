from __future__ import annotations

from dataclasses import dataclass
import numpy as np

from .random_api import RandomContext, Stream, uniform01


@dataclass
class SpatialIndex:
    grid_x: int
    grid_y: int
    width: float
    height: float
    periodic: bool = True

    def __post_init__(self) -> None:
        self.cell_count = self.grid_x * self.grid_y
        self.sorted_entity_indices = np.empty(0, dtype=np.int32)
        self.cell_starts = np.zeros(self.cell_count, dtype=np.int64)
        self.cell_sizes = np.zeros(self.cell_count, dtype=np.int32)
        self.entity_cells = np.empty(0, dtype=np.int32)

    def cell_ids(self, x: np.ndarray, y: np.ndarray) -> np.ndarray:
        cx = np.floor(x / self.width * self.grid_x).astype(np.int64)
        cy = np.floor(y / self.height * self.grid_y).astype(np.int64)
        if self.periodic:
            cx %= self.grid_x
            cy %= self.grid_y
        else:
            cx = np.clip(cx, 0, self.grid_x - 1)
            cy = np.clip(cy, 0, self.grid_y - 1)
        return (cy * self.grid_x + cx).astype(np.int32)

    def build(self, x: np.ndarray, y: np.ndarray, alive: np.ndarray) -> np.ndarray:
        active = np.flatnonzero(alive).astype(np.int32)
        cells = self.cell_ids(x[active], y[active])
        order = np.argsort(cells, kind="stable")
        self.sorted_entity_indices = active[order]
        sorted_cells = cells[order]
        self.cell_sizes = np.bincount(sorted_cells, minlength=self.cell_count).astype(np.int32)
        self.cell_starts = np.cumsum(self.cell_sizes, dtype=np.int64) - self.cell_sizes
        self.entity_cells = np.full(alive.shape[0], -1, dtype=np.int32)
        self.entity_cells[active] = cells
        return active

    def sample_partners(
        self,
        active: np.ndarray,
        stable_ids: np.ndarray,
        run_seed: int,
        tick: int,
        samples: int,
    ) -> np.ndarray:
        """Sample local partners from adjacent cells in O(N*K), without all-pairs search."""
        if samples <= 0:
            return np.empty((active.size, 0), dtype=np.int32)
        own_cells = self.entity_cells[active]
        own_cx = own_cells % self.grid_x
        own_cy = own_cells // self.grid_x
        output = np.full((active.size, samples), -1, dtype=np.int32)
        ids = stable_ids[active]
        ctx = RandomContext(run_seed, tick, phase=20, stream=Stream.NEIGHBOR_SAMPLE)
        offsets = np.asarray(
            [(-1, -1), (0, -1), (1, -1), (-1, 0), (0, 0), (1, 0), (-1, 1), (0, 1), (1, 1)],
            dtype=np.int32,
        )
        for draw in range(samples):
            u_cell = uniform01(ctx, ids, draw_index=draw * 3)
            offset_index = np.minimum((u_cell * 9).astype(np.int32), 8)
            cx = own_cx + offsets[offset_index, 0]
            cy = own_cy + offsets[offset_index, 1]
            if self.periodic:
                cx %= self.grid_x
                cy %= self.grid_y
            else:
                cx = np.clip(cx, 0, self.grid_x - 1)
                cy = np.clip(cy, 0, self.grid_y - 1)
            target_cells = cy * self.grid_x + cx
            sizes = self.cell_sizes[target_cells]
            valid = sizes > 0
            if not np.any(valid):
                continue
            u_member = uniform01(ctx, ids, draw_index=draw * 3 + 1)
            local_offset = np.floor(u_member * np.maximum(sizes, 1)).astype(np.int64)
            positions = self.cell_starts[target_cells] + local_offset
            selected = np.full(active.size, -1, dtype=np.int32)
            selected[valid] = self.sorted_entity_indices[positions[valid]]
            # One deterministic retry when self is sampled.
            retry = valid & (selected == active)
            if np.any(retry):
                u_retry = uniform01(ctx, ids, draw_index=draw * 3 + 2)
                retry_offset = np.floor(u_retry * np.maximum(sizes, 1)).astype(np.int64)
                retry_pos = self.cell_starts[target_cells] + retry_offset
                selected[retry] = self.sorted_entity_indices[retry_pos[retry]]
                selected[selected == active] = -1
            output[:, draw] = selected
        return output
