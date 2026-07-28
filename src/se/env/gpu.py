"""Device-ready environment and information-field stages.

This module deliberately mirrors only stages B and C of the execution
pipeline: dynamic resource fields and the grid-backed information field.  It
does not expose any extra world state to a policy and can run with the NumPy
backend for CPU/GPU parity tests when CuPy is unavailable.
"""

from __future__ import annotations

from typing import Any

import numpy as np

from ..backend import Backend, resolve_backend
from ..cfg import SimulationConfig
from .danger_evidence import DANGER_EVIDENCE_SCALE
from .process import build_environment_process, environment_process_metadata
from .recycling import initialize_resource_residue, update_resource_recycling
from .diversity import (
    ORTHOGONAL_ENVIRONMENT_SCHEMA,
    PERSISTENT_ORTHOGONAL_ENVIRONMENT_SCHEMA,
    diffuse_resource_fields,
    normalized_grid as diversity_normalized_grid,
    orthogonal_base_pattern,
    orthogonal_seasonal_multiplier,
    orthogonal_renewal_target_fraction,
    persistent_orthogonal_renewal_enabled,
    resource_field_diversity_metrics,
)
from ..information import (
    DirectMessageObservationPlan,
    InformationObservation,
    SignalEmissionPlan,
)
from ..random_api import RandomContext, Stream, bernoulli, normal, uniform01
from ..reductions import stable_segmented_sum, validate_cell_ids


class DeviceEnvironment:
    """SoA resource/hazard fields stored entirely on a selected backend."""

    RESOURCE_CHANNELS = 4

    def __init__(self, cfg: SimulationConfig, backend: Backend | str = "gpu") -> None:
        self.cfg = cfg
        self.backend = resolve_backend(backend) if isinstance(backend, str) else backend
        self.spatial_reversed = False
        self.resource_spatial_reversed = False
        self.environment_process = build_environment_process(cfg.environment)
        self.environment_process_metadata = environment_process_metadata(cfg.environment)
        xp = self.backend.xp
        gx, gy = cfg.world.grid_x, cfg.world.grid_y
        yy, xx = xp.mgrid[0:gy, 0:gx]
        capacities = xp.asarray(cfg.environment.resource_capacity, dtype=xp.float32)[:, None, None]
        if cfg.environment.schema == "legacy-four-channel-v1":
            frequencies_x = xp.asarray([0.11, 0.07, 0.05, 0.09], dtype=xp.float64)[:, None, None]
            frequencies_y = xp.asarray([0.08, 0.13, 0.06, 0.10], dtype=xp.float64)[:, None, None]
            base_pattern = 0.55 + 0.20 * xp.sin(xx[None, :, :] * frequencies_x)
            base_pattern += 0.15 * xp.cos(yy[None, :, :] * frequencies_y)
        elif cfg.environment.schema in {
            ORTHOGONAL_ENVIRONMENT_SCHEMA,
            PERSISTENT_ORTHOGONAL_ENVIRONMENT_SCHEMA,
        }:
            xnorm, ynorm = self._normalized_grid(xx, yy)
            base_pattern = orthogonal_base_pattern(
                cfg.environment, xnorm, ynorm, xp=xp
            )
        else:
            base_pattern = self._heterogeneous_base_pattern(xx, yy)
        self.resources = xp.clip(capacities * base_pattern, 0.0, capacities).astype(xp.float32)
        self.capacity = capacities.astype(xp.float32)
        self.regeneration = xp.asarray(cfg.environment.resource_regeneration, dtype=xp.float32)[:, None, None]
        if persistent_orthogonal_renewal_enabled(cfg):
            self.initial_resource_total = self.backend.to_numpy(
                self.resources.sum(axis=(1, 2), dtype=xp.float64)
            ).astype(np.float64)
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
        self.hazard = self._hazard_pattern(0)
        self.mortality_trace = xp.zeros((gy, gx), dtype=xp.float32)
        initialize_resource_residue(self)

    def _normalized_grid(self, xx: Any, yy: Any) -> tuple[Any, Any]:
        return diversity_normalized_grid(
            xx,
            yy,
            grid_x=self.cfg.world.grid_x,
            grid_y=self.cfg.world.grid_y,
            xp=self.backend.xp,
        )

    def _heterogeneous_phase_grid(self, xx: Any, yy: Any) -> Any:
        xp = self.backend.xp
        xnorm, ynorm = self._normalized_grid(xx, yy)
        phase_x = xp.asarray(self.cfg.environment.resource_spatial_phase_x, dtype=xp.float64)[:, None, None]
        phase_y = xp.asarray(self.cfg.environment.resource_spatial_phase_y, dtype=xp.float64)[:, None, None]
        offsets = xp.asarray(self.cfg.environment.resource_temporal_phase_offsets, dtype=xp.float64)[:, None, None]
        return offsets + 2.0 * xp.pi * (
            phase_x * xnorm[None, :, :] + phase_y * ynorm[None, :, :]
        )

    def _heterogeneous_base_pattern(self, xx: Any, yy: Any) -> Any:
        xp = self.backend.xp
        phase = self._heterogeneous_phase_grid(xx, yy)
        frequencies_x = xp.asarray([0.11, 0.07, 0.05, 0.09], dtype=xp.float64)[:, None, None]
        frequencies_y = xp.asarray([0.08, 0.13, 0.06, 0.10], dtype=xp.float64)[:, None, None]
        cross = xp.asarray([0.035, 0.027, 0.043, 0.031], dtype=xp.float64)[:, None, None]
        pattern = 0.50
        pattern += 0.18 * xp.sin(xx[None, :, :] * frequencies_x + phase)
        pattern += 0.16 * xp.cos(yy[None, :, :] * frequencies_y - 0.7 * phase)
        pattern += 0.10 * xp.sin((xx + yy)[None, :, :] * cross + 0.5 * phase)
        return xp.clip(pattern, 0.05, 0.95)

    def _seasonal_multiplier(self, tick: int) -> Any:
        xp = self.backend.xp
        phase = 2.0 * xp.pi * tick / max(self.cfg.environment.season_period, 1)
        if self.cfg.environment.schema == "legacy-four-channel-v1":
            result = 1.0 + self.cfg.environment.season_amplitude * xp.sin(
                phase + xp.arange(self.RESOURCE_CHANNELS)[:, None, None] * 1.3
            )
        else:
            gx, gy = self.cfg.world.grid_x, self.cfg.world.grid_y
            yy, xx = xp.mgrid[0:gy, 0:gx]
            if self.cfg.environment.schema == ORTHOGONAL_ENVIRONMENT_SCHEMA:
                xnorm, ynorm = self._normalized_grid(xx, yy)
                result = orthogonal_seasonal_multiplier(
                    self.cfg.environment,
                    xnorm,
                    ynorm,
                    tick=tick,
                    xp=xp,
                )
            else:
                result = 1.0 + self.cfg.environment.season_amplitude * xp.sin(
                    phase + self._heterogeneous_phase_grid(xx, yy)
                )
        return (
            result[:, ::-1, ::-1].copy()
            if self.resource_spatial_reversed
            else result
        )

    def _resource_renewal_target(self, tick: int) -> Any:
        xp = self.backend.xp
        gx, gy = self.cfg.world.grid_x, self.cfg.world.grid_y
        yy, xx = xp.mgrid[0:gy, 0:gx]
        xnorm, ynorm = self._normalized_grid(xx, yy)
        fraction = orthogonal_renewal_target_fraction(
            self.cfg.environment, xnorm, ynorm, tick=tick, xp=xp
        )
        if self.resource_spatial_reversed:
            fraction = fraction[:, ::-1, ::-1].copy()
        return (self.capacity * fraction).astype(xp.float32)

    def _update_persistent_resource_renewal(self, tick: int) -> Any:
        xp = self.backend.xp
        target = self._resource_renewal_target(tick)
        delta = self.regeneration * (target - self.resources)
        source = xp.maximum(delta, xp.float32(0.0)).astype(xp.float32)
        sink = xp.maximum(-delta, xp.float32(0.0)).astype(xp.float32)
        self.resource_renewal_source_step = self.backend.to_numpy(
            source.sum(axis=(1, 2), dtype=xp.float64)
        ).astype(np.float64)
        self.resource_renewal_sink_step = self.backend.to_numpy(
            sink.sum(axis=(1, 2), dtype=xp.float64)
        ).astype(np.float64)
        self.total_resource_renewal_source += self.resource_renewal_source_step
        self.total_resource_renewal_sink += self.resource_renewal_sink_step
        return xp.clip(
            self.resources + source - sink, xp.float32(0.0), self.capacity
        ).astype(xp.float32)

    def _hazard_pattern(self, tick: int) -> Any:
        xp = self.backend.xp
        gx, gy = self.cfg.world.grid_x, self.cfg.world.grid_y
        yy, xx = xp.mgrid[0:gy, 0:gx]
        phase = (
            2.0
            * xp.pi
            * tick
            * self.cfg.environment.hazard_temporal_multiplier
            / max(self.cfg.environment.season_period, 1)
        )
        if self.cfg.environment.schema == "legacy-four-channel-v1":
            hazard = 0.5 + 0.25 * xp.sin(xx * 0.045 + phase) + 0.25 * xp.cos(yy * 0.037 - 0.7 * phase)
        else:
            xnorm, ynorm = self._normalized_grid(xx, yy)
            spatial = 2.0 * xp.pi * (
                self.cfg.environment.hazard_spatial_phase_x * xnorm
                + self.cfg.environment.hazard_spatial_phase_y * ynorm
            )
            hazard = (
                0.45
                + 0.22 * xp.sin(xx * 0.045 + phase + spatial)
                + 0.20 * xp.cos(yy * 0.037 - 0.7 * phase - 0.5 * spatial)
                + self.cfg.environment.hazard_secondary_amplitude
                * xp.sin((xx + yy) * 0.025 + 1.7 * phase)
            )
        if self.environment_process is not None:
            xnorm, ynorm = self._normalized_grid(xx, yy)
            extension = self.environment_process.hazard_delta(
                tick=tick,
                xnorm=xnorm,
                ynorm=ynorm,
                xp=xp,
            )
            extension = xp.asarray(extension, dtype=xp.float64)
            if extension.shape != hazard.shape:
                raise ValueError(
                    "environment process hazard_delta must match the hazard grid shape"
                )
            if bool(xp.any(~xp.isfinite(extension))) or bool(xp.any(extension < 0.0)):
                raise ValueError(
                    "environment process hazard_delta must be finite and non-negative"
                )
            hazard = hazard + extension
        result = xp.clip(hazard, 0.0, 1.0).astype(xp.float32)
        return result[::-1, ::-1].copy() if self.spatial_reversed else result

    def reverse_resource_spatial_orientation(self) -> None:
        """Rotate only resource geography by 180 degrees persistently."""
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

    def weighted_mortality_trace_field(self) -> Any:
        xp = self.backend.xp
        if not self.mortality_trace_enabled:
            return xp.zeros_like(self.hazard, dtype=xp.float32)
        return (
            xp.float32(self.cfg.environment.mortality_trace_observation_weight)
            * self.mortality_trace
        ).astype(xp.float32)

    def public_danger_field(self) -> Any:
        return (self.hazard + self.weighted_mortality_trace_field()).astype(
            self.backend.xp.float32
        )

    def danger_components_for_cells(self, cell_ids: Any) -> tuple[Any, Any]:
        xp = self.backend.xp
        cells = validate_cell_ids(
            cell_ids,
            self.cfg.world.grid_x * self.cfg.world.grid_y,
            backend=self.backend,
        )
        return (
            self.hazard.reshape(-1)[cells].astype(xp.float32),
            self.weighted_mortality_trace_field().reshape(-1)[cells].astype(xp.float32),
        )

    def danger_for_cells(self, cell_ids: Any, evidence_q: Any | None = None) -> Any:
        xp = self.backend.xp
        direct, trace = self.danger_components_for_cells(cell_ids)
        if evidence_q is None:
            return (direct + trace).astype(xp.float32)
        weights = xp.asarray(evidence_q, dtype=xp.int32)
        if weights.shape != (int(direct.size), 2):
            raise ValueError("danger evidence weights must be shaped [N, 2]")
        return (
            (direct.astype(xp.float64) * weights[:, 0]
             + trace.astype(xp.float64) * weights[:, 1])
            / DANGER_EVIDENCE_SCALE
        ).astype(xp.float32)

    def deposit_mortality_trace(self, cell_ids: Any, weights: Any | None = None) -> None:
        if not self.mortality_trace_enabled:
            return
        xp = self.backend.xp
        cells = validate_cell_ids(
            cell_ids,
            self.cfg.world.grid_x * self.cfg.world.grid_y,
            backend=self.backend,
        )
        if int(cells.size) == 0:
            return
        values = (
            xp.ones(cells.size, dtype=xp.float32)
            if weights is None
            else xp.asarray(weights, dtype=xp.float32)
        )
        if values.ndim != 1 or int(values.size) != int(cells.size):
            raise ValueError("mortality trace weights must align with cell IDs")
        contribution = stable_segmented_sum(
            cells,
            values * xp.float32(self.cfg.environment.mortality_trace_deposit),
            self.cfg.world.grid_x * self.cfg.world.grid_y,
            backend=self.backend,
            dtype=xp.float32,
        )
        flat = self.mortality_trace.reshape(-1)
        flat[:] = xp.minimum(
            flat + contribution,
            xp.float32(self.cfg.environment.mortality_trace_max),
        )

    def _update_mortality_trace(self) -> None:
        xp = self.backend.xp
        if not self.mortality_trace_enabled:
            self.mortality_trace.fill(0.0)
            return
        decay = xp.float32(1.0 - self.cfg.environment.mortality_trace_decay)
        trace = self.mortality_trace * decay
        diffusion = xp.float32(self.cfg.environment.mortality_trace_diffusion)
        if float(self.cfg.environment.mortality_trace_diffusion) > 0.0:
            trace = (
                (xp.float32(1.0) - xp.float32(4.0) * diffusion) * trace
                + diffusion
                * (
                    xp.roll(trace, 1, axis=0)
                    + xp.roll(trace, -1, axis=0)
                    + xp.roll(trace, 1, axis=1)
                    + xp.roll(trace, -1, axis=1)
                )
            )
        self.mortality_trace = xp.clip(
            trace, 0.0, self.cfg.environment.mortality_trace_max
        ).astype(xp.float32)

    def update(self, tick: int) -> None:
        xp = self.backend.xp
        persistent = persistent_orthogonal_renewal_enabled(self.cfg)
        if persistent:
            resource_total_before = np.asarray(
                self.backend.to_numpy(
                    self.resources.sum(axis=(1, 2), dtype=xp.float64)
                ),
                dtype=np.float64,
            )
            self.resource_harvest_roundoff_step.fill(0.0)
        update_resource_recycling(self)
        if persistent:
            resources = self._update_persistent_resource_renewal(tick)
        else:
            seasonal = self._seasonal_multiplier(tick)
            growth = self.regeneration * seasonal * (1.0 - self.resources / xp.maximum(self.capacity, 1e-6))
            resources = xp.clip(self.resources + growth, 0.0, self.capacity).astype(xp.float32)
        if self.cfg.environment.schema in {
            ORTHOGONAL_ENVIRONMENT_SCHEMA,
            PERSISTENT_ORTHOGONAL_ENVIRONMENT_SCHEMA,
        }:
            resources = diffuse_resource_fields(
                resources, self.cfg.environment.resource_diffusion_rates, xp=xp
            )
        self.resources = xp.clip(resources, 0.0, self.capacity).astype(xp.float32)
        if persistent:
            resource_total_after = np.asarray(
                self.backend.to_numpy(
                    self.resources.sum(axis=(1, 2), dtype=xp.float64)
                ),
                dtype=np.float64,
            )
            released = np.asarray(
                self.backend.to_numpy(self.last_resource_residue_released),
                dtype=np.float64,
            )
            self.resource_field_roundoff_step = (
                resource_total_after
                - resource_total_before
                - released
                - self.resource_renewal_source_step
                + self.resource_renewal_sink_step
            )
            self.total_resource_field_roundoff += self.resource_field_roundoff_step
        self.hazard = self._hazard_pattern(tick)
        self._update_mortality_trace()

    def resource_diversity_metrics(self) -> dict[str, Any]:
        return resource_field_diversity_metrics(
            self.backend.to_numpy(self.resources),
            self.cfg.environment.resource_capacity,
        )

    def cell_values(self, cell_ids: Any) -> Any:
        xp = self.backend.xp
        cells = validate_cell_ids(
            cell_ids,
            self.cfg.world.grid_x * self.cfg.world.grid_y,
            backend=self.backend,
        )
        return self.resources.reshape(self.RESOURCE_CHANNELS, -1)[:, cells].T.astype(xp.float32)

    def gradients_for_entities(
        self,
        entity_cells: Any,
        capacity: int,
        resource_affinity_q: Any | None = None,
        danger_evidence_q: Any | None = None,
    ) -> tuple[tuple[Any, Any], tuple[Any, Any]]:
        xp = self.backend.xp
        cells = validate_cell_ids(
            entity_cells,
            self.cfg.world.grid_x * self.cfg.world.grid_y,
            backend=self.backend,
            allow_missing=True,
        )
        safe_cells = xp.where(cells >= 0, cells, 0)

        def gather(values: Any) -> Any:
            result = values.reshape(-1)[safe_cells]
            return xp.where(cells >= 0, result, 0.0).astype(xp.float32)

        if self.cfg.environment.schema == "legacy-four-channel-v1" or resource_affinity_q is None:
            resource = self.resources[0]
            resource_x = 0.5 * (xp.roll(resource, -1, axis=1) - xp.roll(resource, 1, axis=1))
            resource_y = 0.5 * (xp.roll(resource, -1, axis=0) - xp.roll(resource, 1, axis=0))
            rgx = gather(resource_x)
            rgy = gather(resource_y)
        else:
            affinity = xp.asarray(resource_affinity_q, dtype=xp.int32)
            if affinity.shape != (capacity, self.RESOURCE_CHANNELS):
                raise ValueError("resource affinity must match world capacity and four channels")
            rgx = xp.zeros(capacity, dtype=xp.float64)
            rgy = xp.zeros(capacity, dtype=xp.float64)
            for channel in range(self.RESOURCE_CHANNELS):
                normalized = self.resources[channel] / max(
                    float(self.cfg.environment.resource_capacity[channel]), 1e-6
                )
                channel_x = 0.5 * (xp.roll(normalized, -1, axis=1) - xp.roll(normalized, 1, axis=1))
                channel_y = 0.5 * (xp.roll(normalized, -1, axis=0) - xp.roll(normalized, 1, axis=0))
                weight = affinity[:, channel].astype(xp.float64) / (
                    self.RESOURCE_CHANNELS * 4096
                )
                rgx += gather(channel_x).astype(xp.float64) * weight
                rgy += gather(channel_y).astype(xp.float64) * weight
            rgx = rgx.astype(xp.float32)
            rgy = rgy.astype(xp.float32)

        if danger_evidence_q is None:
            public_danger = self.public_danger_field()
            hazard_x = 0.5 * (
                xp.roll(public_danger, -1, axis=1)
                - xp.roll(public_danger, 1, axis=1)
            )
            hazard_y = 0.5 * (
                xp.roll(public_danger, -1, axis=0)
                - xp.roll(public_danger, 1, axis=0)
            )
            return (rgx, rgy), (gather(hazard_x), gather(hazard_y))

        direct_x = 0.5 * (
            xp.roll(self.hazard, -1, axis=1) - xp.roll(self.hazard, 1, axis=1)
        )
        direct_y = 0.5 * (
            xp.roll(self.hazard, -1, axis=0) - xp.roll(self.hazard, 1, axis=0)
        )
        trace_field = self.weighted_mortality_trace_field()
        trace_x = 0.5 * (
            xp.roll(trace_field, -1, axis=1) - xp.roll(trace_field, 1, axis=1)
        )
        trace_y = 0.5 * (
            xp.roll(trace_field, -1, axis=0) - xp.roll(trace_field, 1, axis=0)
        )
        gathered_direct_x = gather(direct_x)
        gathered_direct_y = gather(direct_y)
        gathered_trace_x = gather(trace_x)
        gathered_trace_y = gather(trace_y)
        weights = xp.asarray(danger_evidence_q, dtype=xp.int32)
        if weights.shape != (capacity, 2):
            raise ValueError("danger evidence must match world capacity and two sources")
        dgx = (
            gathered_direct_x.astype(xp.float64) * weights[:, 0]
            + gathered_trace_x.astype(xp.float64) * weights[:, 1]
        ) / DANGER_EVIDENCE_SCALE
        dgy = (
            gathered_direct_y.astype(xp.float64) * weights[:, 0]
            + gathered_trace_y.astype(xp.float64) * weights[:, 1]
        ) / DANGER_EVIDENCE_SCALE
        return (rgx, rgy), (dgx.astype(xp.float32), dgy.astype(xp.float32))

    def resolve_harvest(self, cell_ids: Any, rates: Any) -> Any:
        xp = self.backend.xp
        cells = validate_cell_ids(
            cell_ids,
            self.cfg.world.grid_x * self.cfg.world.grid_y,
            backend=self.backend,
        )
        requested_rates = xp.asarray(rates, dtype=xp.float32)
        if int(cells.size) == 0:
            return xp.empty((0, self.RESOURCE_CHANNELS), dtype=xp.float32)
        cell_count = self.cfg.world.grid_x * self.cfg.world.grid_y
        requests = stable_segmented_sum(
            cells,
            xp.ones(cells.size, dtype=xp.float32),
            cell_count,
            backend=self.backend,
            dtype=xp.float32,
        )
        divisors = xp.maximum(requests[cells], 1.0)
        result = xp.empty((cells.size, self.RESOURCE_CHANNELS), dtype=xp.float32)
        flat = self.resources.reshape(self.RESOURCE_CHANNELS, -1)
        for channel in range(self.RESOURCE_CHANNELS):
            result[:, channel] = xp.minimum(requested_rates[:, channel], flat[channel, cells] / divisors)
        return result

    def commit_harvest(self, cell_ids: Any, gathered: Any) -> None:
        xp = self.backend.xp
        cells = validate_cell_ids(
            cell_ids,
            self.cfg.world.grid_x * self.cfg.world.grid_y,
            backend=self.backend,
        )
        amounts = xp.asarray(gathered, dtype=xp.float32)
        if int(cells.size) == 0:
            return
        persistent = persistent_orthogonal_renewal_enabled(self.cfg)
        if persistent:
            resource_total_before = np.asarray(
                self.backend.to_numpy(
                    self.resources.sum(axis=(1, 2), dtype=xp.float64)
                ),
                dtype=np.float64,
            )
            intended = np.asarray(
                self.backend.to_numpy(amounts), dtype=np.float64
            ).sum(axis=0)
        cell_count = self.cfg.world.grid_x * self.cfg.world.grid_y
        flat = self.resources.reshape(self.RESOURCE_CHANNELS, -1)
        for channel in range(self.RESOURCE_CHANNELS):
            total_taken = stable_segmented_sum(
                cells,
                amounts[:, channel],
                cell_count,
                backend=self.backend,
                dtype=xp.float32,
            )
            flat[channel] = xp.maximum(flat[channel] - total_taken, 0.0)
        if persistent:
            resource_total_after = np.asarray(
                self.backend.to_numpy(
                    self.resources.sum(axis=(1, 2), dtype=xp.float64)
                ),
                dtype=np.float64,
            )
            roundoff = resource_total_before - resource_total_after - intended
            self.resource_harvest_roundoff_step += roundoff
            self.total_resource_harvest_roundoff += roundoff

    def to_numpy(self, value: Any) -> Any:
        return self.backend.to_numpy(value)


class DeviceInformationField:
    """Three-channel GPU field with a separate source buffer and field age."""

    CHANNELS = 3

    def __init__(self, cfg: SimulationConfig, backend: Backend | str = "gpu") -> None:
        self.cfg = cfg
        self.backend = resolve_backend(backend) if isinstance(backend, str) else backend
        xp = self.backend.xp
        shape = (self.CHANNELS, cfg.world.grid_y, cfg.world.grid_x)
        self.field = xp.zeros(shape, dtype=xp.float32)
        self.source = xp.zeros_like(self.field)
        self.age = xp.zeros(shape, dtype=xp.uint16)

    def propagate(self) -> None:
        xp = self.backend.xp
        decay = self.cfg.environment.signal_decay
        diffusion = self.cfg.environment.signal_diffusion
        center = self.field
        neighbor_mean = (
            xp.roll(center, 1, axis=1)
            + xp.roll(center, -1, axis=1)
            + xp.roll(center, 1, axis=2)
            + xp.roll(center, -1, axis=2)
        ) * 0.25
        self.field = xp.maximum((1.0 - decay - diffusion) * center + diffusion * neighbor_mean + self.source, 0.0).astype(
            xp.float32
        )
        active = self.field > 1e-6
        self.age = xp.where(active, xp.minimum(self.age.astype(xp.uint32) + 1, 65535), 0).astype(xp.uint16)
        self.source.fill(0.0)

    def emit(self, channel: int, cell_ids: Any, strengths: Any) -> None:
        if not 0 <= channel < self.CHANNELS:
            raise ValueError(f"invalid signal channel {channel}")
        xp = self.backend.xp
        cells = validate_cell_ids(
            cell_ids,
            self.cfg.world.grid_x * self.cfg.world.grid_y,
            backend=self.backend,
        )
        values = xp.asarray(strengths, dtype=xp.float32)
        if int(cells.size) == 0:
            return
        if values.ndim != 1 or values.shape[0] != cells.shape[0]:
            raise ValueError("strengths must contain one value per cell id")
        # The strict path makes a deterministic cell/id sort then writes one
        # aggregate per cell, avoiding floating scatter-add atomics.
        cell_count = self.cfg.world.grid_x * self.cfg.world.grid_y
        contribution = stable_segmented_sum(
            cells, values, cell_count, backend=self.backend, dtype=xp.float32
        )
        self.source[channel].reshape(-1)[:] += contribution

    def emit_plan(self, plan: SignalEmissionPlan) -> None:
        """Commit the due channel batches without creating dense zero columns."""
        for batch in plan.batches:
            self.emit(batch.channel, batch.cell_ids, batch.strengths)

    def sample(self, cell_ids: Any) -> tuple[Any, Any]:
        xp = self.backend.xp
        cells = validate_cell_ids(
            cell_ids,
            self.cfg.world.grid_x * self.cfg.world.grid_y,
            backend=self.backend,
        )
        return (
            self.field.reshape(self.CHANNELS, -1)[:, cells].T.astype(xp.float32),
            self.age.reshape(self.CHANNELS, -1)[:, cells].T.astype(xp.float32),
        )

    def observe(
        self,
        *,
        stable_ids: Any,
        cell_ids: Any,
        partners: Any,
        energy: Any,
        group_id: Any,
        own_group_id: Any,
        sensor_quality: Any,
        direct_message_plan: DirectMessageObservationPlan,
        run_seed: int,
        tick: int,
    ) -> InformationObservation:
        """Build the policy observation batch entirely on this backend.

        Direct-message queue ownership remains with the CPU world during the
        hybrid migration.  Its already-decoded fixed observation buffers are
        uploaded as ordinary inputs; all field sampling, perception noise,
        partner perception and aggregate observation construction execute on
        the selected device.
        """
        xp = self.backend.xp
        ids = xp.asarray(stable_ids, dtype=xp.uint64)
        cells = validate_cell_ids(
            cell_ids,
            self.cfg.world.grid_x * self.cfg.world.grid_y,
            backend=self.backend,
        )
        partner_indices = xp.asarray(partners, dtype=xp.int32)
        energies = xp.asarray(energy, dtype=xp.float32)
        groups = xp.asarray(group_id, dtype=xp.uint64)
        own_groups = xp.asarray(own_group_id, dtype=xp.uint64)
        # Match the CPU reference dtype exactly.  Promoting sensor quality to
        # float64 here changes receiver-noise division before the shared
        # stateless draws are applied; the resulting few ulps can cross a
        # categorical decision boundary later in the policy.
        quality = xp.clip(xp.asarray(sensor_quality, dtype=xp.float32), 0.05, 2.0)
        raw, raw_age = self.sample(cells)
        raw = raw.astype(xp.float64)
        raw_age = raw_age.astype(xp.float32)
        if direct_message_plan.row_count != int(ids.size):
            raise ValueError("direct-message plan rows must align with active entities")
        direct_rows = xp.asarray(direct_message_plan.receiver_rows, dtype=xp.int32)
        direct_slots = xp.asarray(direct_message_plan.slots, dtype=xp.int32)
        direct_payloads = xp.asarray(direct_message_plan.payloads, dtype=xp.float32)

        detect_ctx = RandomContext(run_seed, tick, phase=40, stream=Stream.SIGNAL_DETECTION)
        strength = raw / (1.0 + raw)
        detection_p = xp.clip(
            (1.0 - self.cfg.information.channel_loss) * quality[:, None] * (0.2 + 0.8 * strength),
            0.0,
            1.0,
        )
        mask = xp.empty_like(raw, dtype=bool)
        for channel in range(self.CHANNELS):
            mask[:, channel] = bernoulli(
                detect_ctx,
                ids,
                detection_p[:, channel],
                draw_index=channel,
                validate_probability=False,
            )

        decode_ctx = RandomContext(run_seed, tick, phase=41, stream=Stream.SIGNAL_DECODING)
        noisy = raw.copy()
        noise_scale = self.cfg.information.receiver_noise / quality
        for channel in range(self.CHANNELS):
            noisy[:, channel] += normal(
                decode_ctx,
                ids,
                0.0,
                noise_scale,
                draw_index=channel * 2,
                validate_stddev=False,
            )
        noisy = xp.maximum(noisy, 0.0)

        misclassified = bernoulli(
            decode_ctx,
            ids,
            self.cfg.information.classification_error / quality,
            draw_index=20,
            validate_probability=False,
        )
        shifts = 1 + (uniform01(decode_ctx, ids, draw_index=21) * 2).astype(xp.int32)
        channels = (xp.arange(self.CHANNELS, dtype=xp.int32)[None, :] - shifts[:, None]) % self.CHANNELS
        rotated = xp.take_along_axis(noisy, channels, axis=1)
        rotated_mask = xp.take_along_axis(mask, channels, axis=1)
        noisy = xp.where(misclassified[:, None], rotated, noisy)
        mask = xp.where(misclassified[:, None], rotated_mask, mask)
        noisy = xp.where(mask, noisy, 0.0)

        if int(direct_rows.size):
            # The plan is already stable-sorted by receiver row and retains
            # legacy slot order within a receiver.  Materialize fixed slots
            # only for rows that actually received a message.  Keeping the
            # original capacity-wide ``sum(axis=1)`` reduction shape is
            # necessary for long-run floating/discrete replay equivalence;
            # the compact first dimension still avoids active-row padding.
            starts = xp.concatenate(
                (
                    xp.asarray([0], dtype=xp.int64),
                    xp.flatnonzero(direct_rows[1:] != direct_rows[:-1]).astype(xp.int64) + 1,
                )
            )
            ends = xp.concatenate((starts[1:], xp.asarray([direct_rows.size], dtype=xp.int64)))
            group_start = xp.empty(direct_rows.size, dtype=bool)
            group_start[0] = True
            group_start[1:] = direct_rows[1:] != direct_rows[:-1]
            compact_rows = xp.cumsum(group_start, dtype=xp.int32) - 1
            compact = xp.zeros(
                (int(starts.size), direct_message_plan.capacity, self.CHANNELS),
                dtype=xp.float32,
            )
            compact[compact_rows, direct_slots] = direct_payloads
            message_sum = compact.sum(axis=1)
            message_count = xp.maximum((ends - starts)[:, None], 1)
            noisy[direct_rows[starts]] += message_sum / message_count
        noisy = noisy.astype(xp.float32)

        partner_mask = partner_indices >= 0
        safe_partners = xp.where(partner_mask, partner_indices, 0)
        actual_partner_energy = energies[safe_partners]
        partner_detect_ctx = RandomContext(run_seed, tick, phase=42, stream=Stream.SIGNAL_CHANNEL)
        for draw in range(partner_indices.shape[1]):
            received = bernoulli(
                partner_detect_ctx,
                ids,
                xp.clip((1.0 - self.cfg.information.channel_loss) * quality, 0.0, 1.0),
                draw_index=draw,
                validate_probability=False,
            )
            partner_mask[:, draw] &= received
        partner_noise = xp.zeros_like(actual_partner_energy, dtype=xp.float64)
        for draw in range(partner_indices.shape[1]):
            partner_noise[:, draw] = normal(
                decode_ctx,
                ids,
                0.0,
                noise_scale,
                draw_index=40 + draw * 2,
                validate_stddev=False,
            )
        perceived_energy = xp.maximum(actual_partner_energy + partner_noise, 0.0)
        perceived_energy = xp.where(partner_mask, perceived_energy, 0.0).astype(xp.float32)
        partner_groups = groups[safe_partners]
        group_match = (own_groups[:, None] != 0) & (own_groups[:, None] == partner_groups) & partner_mask
        partner_missing = (
            1.0 - partner_mask.mean(axis=1)
            if partner_mask.shape[1]
            else xp.ones(ids.size, dtype=xp.float32)
        )
        uncertainty = xp.stack(
            [
                1.0 - mask.mean(axis=1),
                xp.full(ids.size, self.cfg.information.receiver_noise, dtype=xp.float32),
                partner_missing,
            ],
            axis=1,
        ).astype(xp.float32)
        return InformationObservation(
            signals=noisy,
            signal_mask=mask,
            signal_age=raw_age,
            messages=xp.empty((ids.size, 0, self.CHANNELS), dtype=xp.float32),
            message_mask=xp.empty((ids.size, 0), dtype=bool),
            message_age=xp.empty((ids.size, 0), dtype=xp.uint32),
            message_confidence=xp.empty((ids.size, 0), dtype=xp.float32),
            message_source_id=xp.empty((ids.size, 0), dtype=xp.uint64),
            message_corruption=xp.empty((ids.size, 0), dtype=xp.uint8),
            partner_energy=perceived_energy,
            partner_group_match=group_match.astype(xp.float32),
            partner_mask=partner_mask,
            uncertainty=uncertainty,
        )

    def to_numpy(self, value: Any) -> Any:
        return self.backend.to_numpy(value)
