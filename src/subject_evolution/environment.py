from __future__ import annotations

import numpy as np

from .config import SimulationConfig
from .niches import AFFINITY_SCALE, RESOURCE_CHANNELS
from .reductions import stable_segmented_sum, validate_cell_ids


class Environment:
    RESOURCE_CHANNELS = RESOURCE_CHANNELS

    def __init__(self, cfg: SimulationConfig) -> None:
        self.cfg = cfg
        self.spatial_reversed = False
        gx, gy = cfg.world.grid_x, cfg.world.grid_y
        yy, xx = np.mgrid[0:gy, 0:gx]
        capacities = np.asarray(cfg.environment.resource_capacity, dtype=np.float32)[:, None, None]
        if cfg.environment.schema == "legacy-four-channel-v1":
            base_pattern = 0.55 + 0.20 * np.sin(
                xx[None, :, :]
                * np.asarray([0.11, 0.07, 0.05, 0.09])[:, None, None]
            )
            base_pattern += 0.15 * np.cos(
                yy[None, :, :]
                * np.asarray([0.08, 0.13, 0.06, 0.10])[:, None, None]
            )
        else:
            base_pattern = self._heterogeneous_base_pattern(xx, yy)
        self.resources = np.clip(capacities * base_pattern, 0.0, capacities).astype(np.float32)
        self.capacity = capacities.astype(np.float32)
        self.regeneration = np.asarray(
            cfg.environment.resource_regeneration, dtype=np.float32
        )[:, None, None]
        self.hazard = self._hazard_pattern(0)
        self.mortality_trace = np.zeros((gy, gx), dtype=np.float32)

    def _normalized_grid(self, xx: np.ndarray, yy: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        xnorm = xx.astype(np.float64) / max(self.cfg.world.grid_x - 1, 1)
        ynorm = yy.astype(np.float64) / max(self.cfg.world.grid_y - 1, 1)
        return xnorm, ynorm

    def _heterogeneous_phase_grid(self, xx: np.ndarray, yy: np.ndarray) -> np.ndarray:
        xnorm, ynorm = self._normalized_grid(xx, yy)
        phase_x = np.asarray(
            self.cfg.environment.resource_spatial_phase_x, dtype=np.float64
        )[:, None, None]
        phase_y = np.asarray(
            self.cfg.environment.resource_spatial_phase_y, dtype=np.float64
        )[:, None, None]
        offsets = np.asarray(
            self.cfg.environment.resource_temporal_phase_offsets, dtype=np.float64
        )[:, None, None]
        return offsets + 2.0 * np.pi * (
            phase_x * xnorm[None, :, :] + phase_y * ynorm[None, :, :]
        )

    def _heterogeneous_base_pattern(
        self, xx: np.ndarray, yy: np.ndarray
    ) -> np.ndarray:
        phase = self._heterogeneous_phase_grid(xx, yy)
        frequencies_x = np.asarray([0.11, 0.07, 0.05, 0.09], dtype=np.float64)[:, None, None]
        frequencies_y = np.asarray([0.08, 0.13, 0.06, 0.10], dtype=np.float64)[:, None, None]
        cross = np.asarray([0.035, 0.027, 0.043, 0.031], dtype=np.float64)[:, None, None]
        pattern = 0.50
        pattern += 0.18 * np.sin(xx[None, :, :] * frequencies_x + phase)
        pattern += 0.16 * np.cos(yy[None, :, :] * frequencies_y - 0.7 * phase)
        pattern += 0.10 * np.sin((xx + yy)[None, :, :] * cross + 0.5 * phase)
        return np.clip(pattern, 0.05, 0.95)

    def _seasonal_multiplier(self, tick: int) -> np.ndarray:
        phase = 2.0 * np.pi * tick / max(self.cfg.environment.season_period, 1)
        if self.cfg.environment.schema == "legacy-four-channel-v1":
            return 1.0 + self.cfg.environment.season_amplitude * np.sin(
                phase + np.arange(self.RESOURCE_CHANNELS)[:, None, None] * 1.3
            )
        gx, gy = self.cfg.world.grid_x, self.cfg.world.grid_y
        yy, xx = np.mgrid[0:gy, 0:gx]
        local_phase = phase + self._heterogeneous_phase_grid(xx, yy)
        return 1.0 + self.cfg.environment.season_amplitude * np.sin(local_phase)

    def _hazard_pattern(self, tick: int) -> np.ndarray:
        gx, gy = self.cfg.world.grid_x, self.cfg.world.grid_y
        yy, xx = np.mgrid[0:gy, 0:gx]
        phase = (
            2.0
            * np.pi
            * tick
            * self.cfg.environment.hazard_temporal_multiplier
            / max(self.cfg.environment.season_period, 1)
        )
        if self.cfg.environment.schema == "legacy-four-channel-v1":
            h = (
                0.5
                + 0.25 * np.sin(xx * 0.045 + phase)
                + 0.25 * np.cos(yy * 0.037 - 0.7 * phase)
            )
        else:
            xnorm, ynorm = self._normalized_grid(xx, yy)
            spatial = 2.0 * np.pi * (
                self.cfg.environment.hazard_spatial_phase_x * xnorm
                + self.cfg.environment.hazard_spatial_phase_y * ynorm
            )
            h = (
                0.45
                + 0.22 * np.sin(xx * 0.045 + phase + spatial)
                + 0.20 * np.cos(yy * 0.037 - 0.7 * phase - 0.5 * spatial)
                + self.cfg.environment.hazard_secondary_amplitude
                * np.sin((xx + yy) * 0.025 + 1.7 * phase)
            )
        result = np.clip(h, 0.0, 1.0).astype(np.float32)
        return result[::-1, ::-1].copy() if self.spatial_reversed else result

    def reverse_spatial_orientation(self) -> None:
        """Rotate resource and hazard geography by 180 degrees persistently."""
        self.resources = self.resources[:, ::-1, ::-1].copy()
        self.hazard = self.hazard[::-1, ::-1].copy()
        self.mortality_trace = self.mortality_trace[::-1, ::-1].copy()
        self.spatial_reversed = not self.spatial_reversed

    @property
    def mortality_trace_enabled(self) -> bool:
        return (
            self.cfg.environment.mortality_trace_schema
            == "local-decaying-mortality-trace-v1"
        )

    def public_danger_field(self) -> np.ndarray:
        if not self.mortality_trace_enabled:
            return self.hazard
        return (
            self.hazard
            + np.float32(self.cfg.environment.mortality_trace_observation_weight)
            * self.mortality_trace
        ).astype(np.float32)

    def danger_for_cells(self, cell_ids: np.ndarray) -> np.ndarray:
        cells = validate_cell_ids(
            cell_ids, self.cfg.world.grid_x * self.cfg.world.grid_y
        )
        return self.public_danger_field().reshape(-1)[cells].astype(np.float32)

    def deposit_mortality_trace(
        self, cell_ids: np.ndarray, weights: np.ndarray | None = None
    ) -> None:
        if not self.mortality_trace_enabled:
            return
        cells = validate_cell_ids(
            cell_ids, self.cfg.world.grid_x * self.cfg.world.grid_y
        )
        if cells.size == 0:
            return
        values = (
            np.ones(cells.size, dtype=np.float32)
            if weights is None
            else np.asarray(weights, dtype=np.float32)
        )
        if values.ndim != 1 or values.size != cells.size:
            raise ValueError("mortality trace weights must align with cell IDs")
        contribution = stable_segmented_sum(
            cells,
            values * np.float32(self.cfg.environment.mortality_trace_deposit),
            self.cfg.world.grid_x * self.cfg.world.grid_y,
            dtype=np.float32,
        )
        flat = self.mortality_trace.reshape(-1)
        flat[:] = np.minimum(
            flat + contribution,
            np.float32(self.cfg.environment.mortality_trace_max),
        )

    def _update_mortality_trace(self) -> None:
        if not self.mortality_trace_enabled:
            if np.any(self.mortality_trace):
                self.mortality_trace.fill(0.0)
            return
        decay = np.float32(1.0 - self.cfg.environment.mortality_trace_decay)
        trace = self.mortality_trace * decay
        diffusion = np.float32(self.cfg.environment.mortality_trace_diffusion)
        if diffusion > 0.0:
            trace = (
                (np.float32(1.0) - np.float32(4.0) * diffusion) * trace
                + diffusion
                * (
                    np.roll(trace, 1, axis=0)
                    + np.roll(trace, -1, axis=0)
                    + np.roll(trace, 1, axis=1)
                    + np.roll(trace, -1, axis=1)
                )
            )
        self.mortality_trace = np.clip(
            trace, 0.0, self.cfg.environment.mortality_trace_max
        ).astype(np.float32)

    def update(self, tick: int) -> None:
        seasonal = self._seasonal_multiplier(tick)
        growth = self.regeneration * seasonal * (
            1.0 - self.resources / np.maximum(self.capacity, 1e-6)
        )
        self.resources = np.clip(
            self.resources + growth, 0.0, self.capacity
        ).astype(np.float32)
        self.hazard = self._hazard_pattern(tick)
        self._update_mortality_trace()

    def cell_values(self, cell_ids: np.ndarray) -> np.ndarray:
        cells = validate_cell_ids(
            cell_ids, self.cfg.world.grid_x * self.cfg.world.grid_y
        )
        return self.resources.reshape(self.RESOURCE_CHANNELS, -1)[:, cells].T.astype(
            np.float32
        )

    def gradients_for_entities(
        self,
        entity_cells: np.ndarray,
        capacity: int,
        resource_affinity_q: np.ndarray | None = None,
    ) -> tuple[tuple[np.ndarray, np.ndarray], tuple[np.ndarray, np.ndarray]]:
        """Return per-entity resource-utility and hazard gradients.

        Legacy mode uses channel zero exactly.  Heterogeneous mode combines
        normalized per-channel gradients with each entity's fixed-budget
        inherited affinity vector.
        """

        cells = validate_cell_ids(
            entity_cells,
            self.cfg.world.grid_x * self.cfg.world.grid_y,
            allow_missing=True,
        )
        safe_cells = np.where(cells >= 0, cells, 0)

        def gather(values: np.ndarray) -> np.ndarray:
            result = values.reshape(-1)[safe_cells]
            return np.where(cells >= 0, result, 0.0).astype(np.float32)

        if (
            self.cfg.environment.schema == "legacy-four-channel-v1"
            or resource_affinity_q is None
        ):
            resource = self.resources[0]
            resource_x = 0.5 * (
                np.roll(resource, -1, axis=1) - np.roll(resource, 1, axis=1)
            )
            resource_y = 0.5 * (
                np.roll(resource, -1, axis=0) - np.roll(resource, 1, axis=0)
            )
            rgx = gather(resource_x)
            rgy = gather(resource_y)
        else:
            affinity = np.asarray(resource_affinity_q, dtype=np.int32)
            if affinity.shape != (capacity, self.RESOURCE_CHANNELS):
                raise ValueError("resource affinity must match world capacity and four channels")
            rgx64 = np.zeros(capacity, dtype=np.float64)
            rgy64 = np.zeros(capacity, dtype=np.float64)
            for channel in range(self.RESOURCE_CHANNELS):
                normalized = self.resources[channel] / max(
                    float(self.cfg.environment.resource_capacity[channel]), 1e-6
                )
                channel_x = 0.5 * (
                    np.roll(normalized, -1, axis=1)
                    - np.roll(normalized, 1, axis=1)
                )
                channel_y = 0.5 * (
                    np.roll(normalized, -1, axis=0)
                    - np.roll(normalized, 1, axis=0)
                )
                weight = affinity[:, channel].astype(np.float64) / (
                    self.RESOURCE_CHANNELS * AFFINITY_SCALE
                )
                rgx64 += gather(channel_x).astype(np.float64) * weight
                rgy64 += gather(channel_y).astype(np.float64) * weight
            rgx = rgx64.astype(np.float32)
            rgy = rgy64.astype(np.float32)

        public_danger = self.public_danger_field()
        hazard_x = 0.5 * (
            np.roll(public_danger, -1, axis=1)
            - np.roll(public_danger, 1, axis=1)
        )
        hazard_y = 0.5 * (
            np.roll(public_danger, -1, axis=0)
            - np.roll(public_danger, 1, axis=0)
        )
        return (rgx, rgy), (gather(hazard_x), gather(hazard_y))

    def resolve_harvest(self, cell_ids: np.ndarray, rates: np.ndarray) -> np.ndarray:
        """Compute a fair harvest allocation without mutating world state."""
        cells = validate_cell_ids(
            cell_ids, self.cfg.world.grid_x * self.cfg.world.grid_y
        )
        if cells.size == 0:
            return np.empty((0, self.RESOURCE_CHANNELS), dtype=np.float32)
        cell_count = self.cfg.world.grid_x * self.cfg.world.grid_y
        requested_rates = np.asarray(rates, dtype=np.float32)
        requests = stable_segmented_sum(
            cells,
            np.ones(cells.size, dtype=np.float32),
            cell_count,
            dtype=np.float32,
        )
        requested = np.maximum(requests[cells], 1.0)
        result = np.empty((cells.size, self.RESOURCE_CHANNELS), dtype=np.float32)
        flat = self.resources.reshape(self.RESOURCE_CHANNELS, -1)
        for channel in range(self.RESOURCE_CHANNELS):
            available = flat[channel, cells]
            per_entity = np.minimum(
                requested_rates[:, channel], available / requested
            )
            result[:, channel] = per_entity
        return result

    def commit_harvest(self, cell_ids: np.ndarray, gathered: np.ndarray) -> None:
        """Apply a previously resolved harvest allocation exactly once."""
        cells = validate_cell_ids(
            cell_ids, self.cfg.world.grid_x * self.cfg.world.grid_y
        )
        if cells.size == 0:
            return
        cell_count = self.cfg.world.grid_x * self.cfg.world.grid_y
        flat = self.resources.reshape(self.RESOURCE_CHANNELS, -1)
        for channel in range(self.RESOURCE_CHANNELS):
            total_taken = stable_segmented_sum(
                cells, gathered[:, channel], cell_count, dtype=np.float32
            )
            flat[channel] = np.maximum(flat[channel] - total_taken, 0.0)

    def harvest(self, cell_ids: np.ndarray, rates: np.ndarray) -> np.ndarray:
        """Backward-compatible resolve-and-commit convenience method."""
        result = self.resolve_harvest(cell_ids, rates)
        self.commit_harvest(cell_ids, result)
        return result
