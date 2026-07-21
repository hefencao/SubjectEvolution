from __future__ import annotations

import numpy as np

from .config import SimulationConfig


class Environment:
    RESOURCE_CHANNELS = 4

    def __init__(self, cfg: SimulationConfig) -> None:
        self.cfg = cfg
        gx, gy = cfg.world.grid_x, cfg.world.grid_y
        yy, xx = np.mgrid[0:gy, 0:gx]
        capacities = np.asarray(cfg.environment.resource_capacity, dtype=np.float32)[:, None, None]
        base_pattern = 0.55 + 0.20 * np.sin(xx[None, :, :] * np.asarray([0.11, 0.07, 0.05, 0.09])[:, None, None])
        base_pattern += 0.15 * np.cos(yy[None, :, :] * np.asarray([0.08, 0.13, 0.06, 0.10])[:, None, None])
        self.resources = np.clip(capacities * base_pattern, 0.0, capacities).astype(np.float32)
        self.capacity = capacities.astype(np.float32)
        self.regeneration = np.asarray(cfg.environment.resource_regeneration, dtype=np.float32)[:, None, None]
        self.hazard = self._hazard_pattern(0)

    def _hazard_pattern(self, tick: int) -> np.ndarray:
        gx, gy = self.cfg.world.grid_x, self.cfg.world.grid_y
        yy, xx = np.mgrid[0:gy, 0:gx]
        phase = 2.0 * np.pi * tick / max(self.cfg.environment.season_period, 1)
        h = 0.5 + 0.25 * np.sin(xx * 0.045 + phase) + 0.25 * np.cos(yy * 0.037 - 0.7 * phase)
        return np.clip(h, 0.0, 1.0).astype(np.float32)

    def update(self, tick: int) -> None:
        phase = 2.0 * np.pi * tick / max(self.cfg.environment.season_period, 1)
        seasonal = 1.0 + self.cfg.environment.season_amplitude * np.sin(phase + np.arange(4)[:, None, None] * 1.3)
        growth = self.regeneration * seasonal * (1.0 - self.resources / np.maximum(self.capacity, 1e-6))
        self.resources = np.clip(self.resources + growth, 0.0, self.capacity).astype(np.float32)
        self.hazard = self._hazard_pattern(tick)

    def cell_values(self, cell_ids: np.ndarray) -> np.ndarray:
        return self.resources.reshape(4, -1)[:, cell_ids].T.astype(np.float32)

    def gradients_for_entities(self, entity_cells: np.ndarray, capacity: int) -> tuple[tuple[np.ndarray, np.ndarray], tuple[np.ndarray, np.ndarray]]:
        """Return per-entity gradients for energy resource and hazard."""
        res = self.resources[0]
        res_gx = 0.5 * (np.roll(res, -1, axis=1) - np.roll(res, 1, axis=1))
        res_gy = 0.5 * (np.roll(res, -1, axis=0) - np.roll(res, 1, axis=0))
        haz = self.hazard
        haz_gx = 0.5 * (np.roll(haz, -1, axis=1) - np.roll(haz, 1, axis=1))
        haz_gy = 0.5 * (np.roll(haz, -1, axis=0) - np.roll(haz, 1, axis=0))
        safe_cells = np.where(entity_cells >= 0, entity_cells, 0)
        rgx = res_gx.reshape(-1)[safe_cells]
        rgy = res_gy.reshape(-1)[safe_cells]
        hgx = haz_gx.reshape(-1)[safe_cells]
        hgy = haz_gy.reshape(-1)[safe_cells]
        rgx = np.where(entity_cells >= 0, rgx, 0.0).astype(np.float32)
        rgy = np.where(entity_cells >= 0, rgy, 0.0).astype(np.float32)
        hgx = np.where(entity_cells >= 0, hgx, 0.0).astype(np.float32)
        hgy = np.where(entity_cells >= 0, hgy, 0.0).astype(np.float32)
        return (rgx, rgy), (hgx, hgy)

    def resolve_harvest(self, cell_ids: np.ndarray, rates: np.ndarray) -> np.ndarray:
        """Compute a fair harvest allocation without mutating world state."""
        if cell_ids.size == 0:
            return np.empty((0, 4), dtype=np.float32)
        cell_count = self.cfg.world.grid_x * self.cfg.world.grid_y
        requests = np.bincount(cell_ids, minlength=cell_count).astype(np.float32)
        requested = np.maximum(requests[cell_ids], 1.0)
        result = np.empty((cell_ids.size, 4), dtype=np.float32)
        flat = self.resources.reshape(4, -1)
        for channel in range(4):
            available = flat[channel, cell_ids]
            per_entity = np.minimum(rates[:, channel], available / requested)
            result[:, channel] = per_entity
        return result

    def commit_harvest(self, cell_ids: np.ndarray, gathered: np.ndarray) -> None:
        """Apply a previously resolved harvest allocation exactly once."""
        if cell_ids.size == 0:
            return
        cell_count = self.cfg.world.grid_x * self.cfg.world.grid_y
        flat = self.resources.reshape(4, -1)
        for channel in range(4):
            total_taken = np.bincount(
                cell_ids, weights=gathered[:, channel], minlength=cell_count
            ).astype(np.float32)
            flat[channel] = np.maximum(flat[channel] - total_taken, 0.0)

    def harvest(self, cell_ids: np.ndarray, rates: np.ndarray) -> np.ndarray:
        """Backward-compatible resolve-and-commit convenience method."""
        result = self.resolve_harvest(cell_ids, rates)
        self.commit_harvest(cell_ids, result)
        return result
