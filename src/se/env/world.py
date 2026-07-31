from __future__ import annotations

from typing import Any

import numpy as np

from ..cfg import SimulationConfig
from .danger_evidence import DANGER_EVIDENCE_SCALE
from .process import build_environment_process, environment_process_metadata
from .recycling import initialize_resource_residue, update_resource_recycling
from .diversity import (
    ORTHOGONAL_ENVIRONMENT_SCHEMA,
    PERSISTENT_ORTHOGONAL_ENVIRONMENT_SCHEMA,
    MULTISCALE_PERSISTENT_ENVIRONMENT_SCHEMA,
    diffuse_resource_fields,
    normalized_grid as diversity_normalized_grid,
    orthogonal_base_pattern,
    orthogonal_processing_support_multiplier,
    orthogonal_seasonal_multiplier,
    orthogonal_renewal_target_fraction,
    persistent_orthogonal_renewal_enabled,
    resource_field_diversity_metrics,
)
from .niches import AFFINITY_SCALE, RESOURCE_CHANNELS
from .physiology import physiology_fields
from ..reductions import stable_segmented_sum, validate_cell_ids


class Environment:
    RESOURCE_CHANNELS = RESOURCE_CHANNELS

    def __init__(self, cfg: SimulationConfig) -> None:
        self.cfg = cfg
        self.spatial_reversed = False
        self.resource_spatial_reversed = False
        self.resource_processing_support_reversed = False
        self.environment_process = build_environment_process(cfg.environment)
        self.environment_process_metadata = environment_process_metadata(cfg.environment)
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
        elif cfg.environment.schema in {
            ORTHOGONAL_ENVIRONMENT_SCHEMA,
            PERSISTENT_ORTHOGONAL_ENVIRONMENT_SCHEMA,
            MULTISCALE_PERSISTENT_ENVIRONMENT_SCHEMA,
        }:
            xnorm, ynorm = self._normalized_grid(xx, yy)
            base_pattern = orthogonal_base_pattern(
                cfg.environment, xnorm, ynorm, xp=np
            )
        else:
            base_pattern = self._heterogeneous_base_pattern(xx, yy)
        self.resources = np.clip(capacities * base_pattern, 0.0, capacities).astype(np.float32)
        self.capacity = capacities.astype(np.float32)
        self.regeneration = np.asarray(
            cfg.environment.resource_regeneration, dtype=np.float32
        )[:, None, None]
        if persistent_orthogonal_renewal_enabled(cfg):
            self.initial_resource_total = self.resources.sum(
                axis=(1, 2), dtype=np.float64
            )
            self.resource_renewal_source_step = np.zeros(
                self.RESOURCE_CHANNELS, dtype=np.float64
            )
            self.resource_renewal_sink_step = np.zeros(
                self.RESOURCE_CHANNELS, dtype=np.float64
            )
            self.total_resource_renewal_source = np.zeros(
                self.RESOURCE_CHANNELS, dtype=np.float64
            )
            self.total_resource_renewal_sink = np.zeros(
                self.RESOURCE_CHANNELS, dtype=np.float64
            )
            self.resource_field_roundoff_step = np.zeros(
                self.RESOURCE_CHANNELS, dtype=np.float64
            )
            self.total_resource_field_roundoff = np.zeros(
                self.RESOURCE_CHANNELS, dtype=np.float64
            )
            self.resource_harvest_roundoff_step = np.zeros(
                self.RESOURCE_CHANNELS, dtype=np.float64
            )
            self.total_resource_harvest_roundoff = np.zeros(
                self.RESOURCE_CHANNELS, dtype=np.float64
            )
            self.last_resource_residue_released = np.zeros(
                self.RESOURCE_CHANNELS, dtype=np.float64
            )
        self.hazard = self._hazard_pattern(0)
        self.mortality_trace = np.zeros((gy, gx), dtype=np.float32)
        initialize_resource_residue(self)
        self.oxygen, self.terrain, self.wear = physiology_fields(cfg, 0)

    def _normalized_grid(self, xx: np.ndarray, yy: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        return diversity_normalized_grid(
            xx,
            yy,
            grid_x=self.cfg.world.grid_x,
            grid_y=self.cfg.world.grid_y,
            xp=np,
        )

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
            result = 1.0 + self.cfg.environment.season_amplitude * np.sin(
                phase + np.arange(self.RESOURCE_CHANNELS)[:, None, None] * 1.3
            )
        else:
            gx, gy = self.cfg.world.grid_x, self.cfg.world.grid_y
            yy, xx = np.mgrid[0:gy, 0:gx]
            if self.cfg.environment.schema == ORTHOGONAL_ENVIRONMENT_SCHEMA:
                xnorm, ynorm = self._normalized_grid(xx, yy)
                result = orthogonal_seasonal_multiplier(
                    self.cfg.environment,
                    xnorm,
                    ynorm,
                    tick=tick,
                    xp=np,
                )
            else:
                local_phase = phase + self._heterogeneous_phase_grid(xx, yy)
                result = 1.0 + self.cfg.environment.season_amplitude * np.sin(local_phase)
        return (
            result[:, ::-1, ::-1].copy()
            if self.resource_spatial_reversed
            else result
        )

    def _resource_renewal_target(self, tick: int) -> np.ndarray:
        gx, gy = self.cfg.world.grid_x, self.cfg.world.grid_y
        yy, xx = np.mgrid[0:gy, 0:gx]
        xnorm, ynorm = self._normalized_grid(xx, yy)
        fraction = orthogonal_renewal_target_fraction(
            self.cfg.environment, xnorm, ynorm, tick=tick, xp=np
        )
        if self.resource_spatial_reversed:
            fraction = fraction[:, ::-1, ::-1].copy()
        return (self.capacity * fraction).astype(np.float32)

    def resource_processing_support_field(self, tick: int) -> np.ndarray:
        """Return the current four-channel D3-E abiotic support multiplier."""

        gx, gy = self.cfg.world.grid_x, self.cfg.world.grid_y
        yy, xx = np.mgrid[0:gy, 0:gx]
        xnorm, ynorm = self._normalized_grid(xx, yy)
        support = orthogonal_processing_support_multiplier(
            self.cfg.environment,
            xnorm,
            ynorm,
            tick=tick,
            xp=np,
        )
        if self.resource_spatial_reversed ^ self.resource_processing_support_reversed:
            support = support[:, ::-1, ::-1].copy()
        return np.asarray(support, dtype=np.float32)

    def resource_processing_support_for_cells(
        self, cell_ids: np.ndarray, *, tick: int
    ) -> np.ndarray:
        cells = validate_cell_ids(
            cell_ids, self.cfg.world.grid_x * self.cfg.world.grid_y
        )
        field = self.resource_processing_support_field(tick)
        return field.reshape(self.RESOURCE_CHANNELS, -1)[:, cells].T.astype(
            np.float32
        )

    def _update_persistent_resource_renewal(self, tick: int) -> np.ndarray:
        target = self._resource_renewal_target(tick)
        delta = self.regeneration * (target - self.resources)
        source = np.maximum(delta, 0.0).astype(np.float32)
        sink = np.maximum(-delta, 0.0).astype(np.float32)
        self.resource_renewal_source_step = source.sum(
            axis=(1, 2), dtype=np.float64
        )
        self.resource_renewal_sink_step = sink.sum(
            axis=(1, 2), dtype=np.float64
        )
        self.total_resource_renewal_source += self.resource_renewal_source_step
        self.total_resource_renewal_sink += self.resource_renewal_sink_step
        return np.clip(
            self.resources + source - sink, 0.0, self.capacity
        ).astype(np.float32)

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
        if self.environment_process is not None:
            xnorm, ynorm = self._normalized_grid(xx, yy)
            extension = self.environment_process.hazard_delta(
                tick=tick,
                xnorm=xnorm,
                ynorm=ynorm,
                xp=np,
            )
            extension = np.asarray(extension, dtype=np.float64)
            if extension.shape != h.shape:
                raise ValueError(
                    "environment process hazard_delta must match the hazard grid shape"
                )
            if not np.all(np.isfinite(extension)) or np.any(extension < 0.0):
                raise ValueError(
                    "environment process hazard_delta must be finite and non-negative"
                )
            h = h + extension
        result = np.clip(h, 0.0, 1.0).astype(np.float32)
        return result[::-1, ::-1].copy() if self.spatial_reversed else result

    @property
    def physiology_environment_enabled(self) -> bool:
        return self.cfg.environment.physiology_environment_schema == "oxygen-terrain-wear-mosaic-v1"

    def update_physiology_fields(self, tick: int) -> None:
        self.oxygen, self.terrain, self.wear = physiology_fields(self.cfg, tick)
        if self.spatial_reversed:
            self.oxygen = self.oxygen[::-1, ::-1].copy()
            self.terrain = self.terrain[::-1, ::-1].copy()
            self.wear = self.wear[::-1, ::-1].copy()

    def physiology_for_cells(self, cell_ids: np.ndarray) -> np.ndarray:
        cells = validate_cell_ids(cell_ids, self.cfg.world.grid_x * self.cfg.world.grid_y)
        return np.column_stack((
            self.oxygen.reshape(-1)[cells],
            self.terrain.reshape(-1)[cells],
            self.wear.reshape(-1)[cells],
        )).astype(np.float32)

    def oxygen_gradient_for_entities(
        self, entity_cells: np.ndarray, entity_count: int
    ) -> tuple[np.ndarray, np.ndarray]:
        cells = np.asarray(entity_cells, dtype=np.int32)
        gx = self.cfg.world.grid_x
        gy = self.cfg.world.grid_y
        valid = (cells >= 0) & (cells < gx * gy)
        grad_x = np.zeros(entity_count, dtype=np.float32)
        grad_y = np.zeros(entity_count, dtype=np.float32)
        if not np.any(valid):
            return grad_x, grad_y
        yy, xx = np.divmod(cells[valid], gx)
        left = self.oxygen[yy, (xx - 1) % gx]
        right = self.oxygen[yy, (xx + 1) % gx]
        down = self.oxygen[(yy - 1) % gy, xx]
        up = self.oxygen[(yy + 1) % gy, xx]
        rows = np.flatnonzero(valid)
        grad_x[rows] = right - left
        grad_y[rows] = up - down
        return grad_x, grad_y

    def reverse_resource_processing_support_orientation(self) -> None:
        """Rotate only the non-material D3-E processing-support surface.

        Resource fields, residue, renewal targets, hazard, entity state, genotype,
        and processing costs remain unchanged.  This is an experiment-only
        orientation intervention used to distinguish support-aligned response
        from generic shared-checkpoint trajectory sensitivity.
        """

        self.resource_processing_support_reversed = (
            not self.resource_processing_support_reversed
        )

    def reverse_resource_spatial_orientation(self) -> None:
        """Rotate only resource geography by 180 degrees persistently.

        Resource identity, channel effects, capacities, regeneration rates, hazard,
        mortality trace, entities, and inherited affinity remain unchanged.  Future
        seasonal regeneration is rotated with the current field so the intervention
        does not decay back toward the original template.
        """

        self.resources = self.resources[:, ::-1, ::-1].copy()
        if hasattr(self, "resource_residue"):
            self.resource_residue = self.resource_residue[:, ::-1, ::-1].copy()
        self.resource_spatial_reversed = not self.resource_spatial_reversed

    def reverse_spatial_orientation(self) -> None:
        """Rotate resource and hazard geography by 180 degrees persistently."""
        self.reverse_resource_spatial_orientation()
        self.hazard = self.hazard[::-1, ::-1].copy()
        self.mortality_trace = self.mortality_trace[::-1, ::-1].copy()
        self.spatial_reversed = not self.spatial_reversed

    @property
    def mortality_trace_enabled(self) -> bool:
        return (
            self.cfg.environment.mortality_trace_schema
            == "local-decaying-mortality-trace-v1"
        )

    def weighted_mortality_trace_field(self) -> np.ndarray:
        if not self.mortality_trace_enabled:
            return np.zeros_like(self.hazard, dtype=np.float32)
        return (
            np.float32(self.cfg.environment.mortality_trace_observation_weight)
            * self.mortality_trace
        ).astype(np.float32)

    def public_danger_field(self) -> np.ndarray:
        return (self.hazard + self.weighted_mortality_trace_field()).astype(np.float32)

    def danger_components_for_cells(
        self, cell_ids: np.ndarray
    ) -> tuple[np.ndarray, np.ndarray]:
        cells = validate_cell_ids(
            cell_ids, self.cfg.world.grid_x * self.cfg.world.grid_y
        )
        return (
            self.hazard.reshape(-1)[cells].astype(np.float32),
            self.weighted_mortality_trace_field().reshape(-1)[cells].astype(np.float32),
        )

    def danger_for_cells(
        self, cell_ids: np.ndarray, evidence_q: np.ndarray | None = None
    ) -> np.ndarray:
        direct, trace = self.danger_components_for_cells(cell_ids)
        if evidence_q is None:
            return (direct + trace).astype(np.float32)
        weights = np.asarray(evidence_q, dtype=np.int32)
        if weights.shape != (direct.size, 2):
            raise ValueError("danger evidence weights must be shaped [N, 2]")
        return (
            (direct.astype(np.float64) * weights[:, 0]
             + trace.astype(np.float64) * weights[:, 1])
            / DANGER_EVIDENCE_SCALE
        ).astype(np.float32)

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
        persistent = persistent_orthogonal_renewal_enabled(self.cfg)
        if persistent:
            resource_total_before = self.resources.sum(axis=(1, 2), dtype=np.float64)
            self.resource_harvest_roundoff_step.fill(0.0)
        update_resource_recycling(self)
        if persistent:
            resources = self._update_persistent_resource_renewal(tick)
        else:
            seasonal = self._seasonal_multiplier(tick)
            growth = self.regeneration * seasonal * (
                1.0 - self.resources / np.maximum(self.capacity, 1e-6)
            )
            resources = np.clip(
                self.resources + growth, 0.0, self.capacity
            ).astype(np.float32)
        if self.cfg.environment.schema in {
            ORTHOGONAL_ENVIRONMENT_SCHEMA,
            PERSISTENT_ORTHOGONAL_ENVIRONMENT_SCHEMA,
            MULTISCALE_PERSISTENT_ENVIRONMENT_SCHEMA,
        }:
            resources = diffuse_resource_fields(
                resources, self.cfg.environment.resource_diffusion_rates, xp=np
            )
        self.resources = np.clip(resources, 0.0, self.capacity).astype(np.float32)
        if persistent:
            resource_total_after = self.resources.sum(axis=(1, 2), dtype=np.float64)
            released = np.asarray(self.last_resource_residue_released, dtype=np.float64)
            self.resource_field_roundoff_step = (
                resource_total_after
                - resource_total_before
                - released
                - self.resource_renewal_source_step
                + self.resource_renewal_sink_step
            )
            self.total_resource_field_roundoff += self.resource_field_roundoff_step
        self.hazard = self._hazard_pattern(tick)
        self.update_physiology_fields(tick)
        self._update_mortality_trace()

    def resource_diversity_metrics(self) -> dict[str, Any]:
        return resource_field_diversity_metrics(
            self.resources, self.cfg.environment.resource_capacity
        )

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
        danger_evidence_q: np.ndarray | None = None,
        resource_sensing_radius: np.ndarray | None = None,
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

        sensing_radius: np.ndarray | None = None
        if resource_sensing_radius is not None:
            sensing_radius = np.asarray(resource_sensing_radius, dtype=np.int16)
            if sensing_radius.shape != (capacity,):
                raise ValueError("resource sensing radius must match world capacity")
            allowed = np.asarray(
                self.cfg.entities.resource_sensing_radius_levels, dtype=np.int16
            )
            if np.any(~np.isin(sensing_radius, allowed)):
                raise ValueError("resource sensing radius contains an unconfigured level")

        def resource_gradient_components(values: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
            if sensing_radius is None:
                return (
                    0.5 * (np.roll(values, -1, axis=1) - np.roll(values, 1, axis=1)),
                    0.5 * (np.roll(values, -1, axis=0) - np.roll(values, 1, axis=0)),
                )
            gx = np.zeros(capacity, dtype=np.float32)
            gy = np.zeros(capacity, dtype=np.float32)
            for raw_radius in self.cfg.entities.resource_sensing_radius_levels:
                radius = int(raw_radius)
                scale = np.float32(0.5 / radius)
                field_x = scale * (
                    np.roll(values, -radius, axis=1)
                    - np.roll(values, radius, axis=1)
                )
                field_y = scale * (
                    np.roll(values, -radius, axis=0)
                    - np.roll(values, radius, axis=0)
                )
                selected = sensing_radius == radius
                gathered_x = gather(field_x)
                gathered_y = gather(field_y)
                gx[selected] = gathered_x[selected]
                gy[selected] = gathered_y[selected]
            return gx, gy

        if (
            self.cfg.environment.schema == "legacy-four-channel-v1"
            or resource_affinity_q is None
        ):
            resource = self.resources[0]
            resource_x, resource_y = resource_gradient_components(resource)
            if sensing_radius is None:
                rgx = gather(resource_x)
                rgy = gather(resource_y)
            else:
                rgx = resource_x
                rgy = resource_y
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
                channel_x, channel_y = resource_gradient_components(normalized)
                weight = affinity[:, channel].astype(np.float64) / (
                    self.RESOURCE_CHANNELS * AFFINITY_SCALE
                )
                gathered_x = gather(channel_x) if sensing_radius is None else channel_x
                gathered_y = gather(channel_y) if sensing_radius is None else channel_y
                rgx64 += gathered_x.astype(np.float64) * weight
                rgy64 += gathered_y.astype(np.float64) * weight
            rgx = rgx64.astype(np.float32)
            rgy = rgy64.astype(np.float32)

        if danger_evidence_q is None:
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

        direct_x = 0.5 * (
            np.roll(self.hazard, -1, axis=1) - np.roll(self.hazard, 1, axis=1)
        )
        direct_y = 0.5 * (
            np.roll(self.hazard, -1, axis=0) - np.roll(self.hazard, 1, axis=0)
        )
        trace_field = self.weighted_mortality_trace_field()
        trace_x = 0.5 * (
            np.roll(trace_field, -1, axis=1) - np.roll(trace_field, 1, axis=1)
        )
        trace_y = 0.5 * (
            np.roll(trace_field, -1, axis=0) - np.roll(trace_field, 1, axis=0)
        )
        gathered_direct_x = gather(direct_x)
        gathered_direct_y = gather(direct_y)
        gathered_trace_x = gather(trace_x)
        gathered_trace_y = gather(trace_y)
        weights = np.asarray(danger_evidence_q, dtype=np.int32)
        if weights.shape != (capacity, 2):
            raise ValueError("danger evidence must match world capacity and two sources")
        dgx = (
            gathered_direct_x.astype(np.float64) * weights[:, 0]
            + gathered_trace_x.astype(np.float64) * weights[:, 1]
        ) / DANGER_EVIDENCE_SCALE
        dgy = (
            gathered_direct_y.astype(np.float64) * weights[:, 0]
            + gathered_trace_y.astype(np.float64) * weights[:, 1]
        ) / DANGER_EVIDENCE_SCALE
        return (rgx, rgy), (dgx.astype(np.float32), dgy.astype(np.float32))

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
        persistent = persistent_orthogonal_renewal_enabled(self.cfg)
        if persistent:
            resource_total_before = self.resources.sum(axis=(1, 2), dtype=np.float64)
            intended = np.asarray(gathered, dtype=np.float64).sum(axis=0)
        flat = self.resources.reshape(self.RESOURCE_CHANNELS, -1)
        for channel in range(self.RESOURCE_CHANNELS):
            total_taken = stable_segmented_sum(
                cells, gathered[:, channel], cell_count, dtype=np.float32
            )
            flat[channel] = np.maximum(flat[channel] - total_taken, 0.0)
        if persistent:
            resource_total_after = self.resources.sum(axis=(1, 2), dtype=np.float64)
            roundoff = resource_total_before - resource_total_after - intended
            self.resource_harvest_roundoff_step += roundoff
            self.total_resource_harvest_roundoff += roundoff

    def harvest(self, cell_ids: np.ndarray, rates: np.ndarray) -> np.ndarray:
        """Backward-compatible resolve-and-commit convenience method."""
        result = self.resolve_harvest(cell_ids, rates)
        self.commit_harvest(cell_ids, result)
        return result
