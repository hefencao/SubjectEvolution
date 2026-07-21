"""Device-ready environment and information-field stages.

This module deliberately mirrors only stages B and C of the execution
pipeline: dynamic resource fields and the grid-backed information field.  It
does not expose any extra world state to a policy and can run with the NumPy
backend for CPU/GPU parity tests when CuPy is unavailable.
"""

from __future__ import annotations

from typing import Any

from .backend import Backend, resolve_backend
from .config import SimulationConfig
from .information import InformationObservation
from .random_api import RandomContext, Stream, bernoulli, normal, uniform01
from .reductions import stable_segmented_sum, validate_cell_ids


class DeviceEnvironment:
    """SoA resource/hazard fields stored entirely on a selected backend."""

    RESOURCE_CHANNELS = 4

    def __init__(self, cfg: SimulationConfig, backend: Backend | str = "gpu") -> None:
        self.cfg = cfg
        self.backend = resolve_backend(backend) if isinstance(backend, str) else backend
        xp = self.backend.xp
        gx, gy = cfg.world.grid_x, cfg.world.grid_y
        yy, xx = xp.mgrid[0:gy, 0:gx]
        capacities = xp.asarray(cfg.environment.resource_capacity, dtype=xp.float32)[:, None, None]
        frequencies_x = xp.asarray([0.11, 0.07, 0.05, 0.09], dtype=xp.float64)[:, None, None]
        frequencies_y = xp.asarray([0.08, 0.13, 0.06, 0.10], dtype=xp.float64)[:, None, None]
        base_pattern = 0.55 + 0.20 * xp.sin(xx[None, :, :] * frequencies_x)
        base_pattern += 0.15 * xp.cos(yy[None, :, :] * frequencies_y)
        self.resources = xp.clip(capacities * base_pattern, 0.0, capacities).astype(xp.float32)
        self.capacity = capacities.astype(xp.float32)
        self.regeneration = xp.asarray(cfg.environment.resource_regeneration, dtype=xp.float32)[:, None, None]
        self.hazard = self._hazard_pattern(0)

    def _hazard_pattern(self, tick: int) -> Any:
        xp = self.backend.xp
        gx, gy = self.cfg.world.grid_x, self.cfg.world.grid_y
        yy, xx = xp.mgrid[0:gy, 0:gx]
        phase = 2.0 * xp.pi * tick / max(self.cfg.environment.season_period, 1)
        hazard = 0.5 + 0.25 * xp.sin(xx * 0.045 + phase) + 0.25 * xp.cos(yy * 0.037 - 0.7 * phase)
        return xp.clip(hazard, 0.0, 1.0).astype(xp.float32)

    def update(self, tick: int) -> None:
        xp = self.backend.xp
        phase = 2.0 * xp.pi * tick / max(self.cfg.environment.season_period, 1)
        seasonal = 1.0 + self.cfg.environment.season_amplitude * xp.sin(
            phase + xp.arange(self.RESOURCE_CHANNELS)[:, None, None] * 1.3
        )
        growth = self.regeneration * seasonal * (1.0 - self.resources / xp.maximum(self.capacity, 1e-6))
        self.resources = xp.clip(self.resources + growth, 0.0, self.capacity).astype(xp.float32)
        self.hazard = self._hazard_pattern(tick)

    def cell_values(self, cell_ids: Any) -> Any:
        xp = self.backend.xp
        cells = validate_cell_ids(
            cell_ids,
            self.cfg.world.grid_x * self.cfg.world.grid_y,
            backend=self.backend,
        )
        return self.resources.reshape(self.RESOURCE_CHANNELS, -1)[:, cells].T.astype(xp.float32)

    def gradients_for_entities(self, entity_cells: Any, capacity: int) -> tuple[tuple[Any, Any], tuple[Any, Any]]:
        xp = self.backend.xp
        cells = validate_cell_ids(
            entity_cells,
            self.cfg.world.grid_x * self.cfg.world.grid_y,
            backend=self.backend,
            allow_missing=True,
        )
        resource = self.resources[0]
        resource_x = 0.5 * (xp.roll(resource, -1, axis=1) - xp.roll(resource, 1, axis=1))
        resource_y = 0.5 * (xp.roll(resource, -1, axis=0) - xp.roll(resource, 1, axis=0))
        hazard_x = 0.5 * (xp.roll(self.hazard, -1, axis=1) - xp.roll(self.hazard, 1, axis=1))
        hazard_y = 0.5 * (xp.roll(self.hazard, -1, axis=0) - xp.roll(self.hazard, 1, axis=0))
        safe_cells = xp.where(cells >= 0, cells, 0)

        def gather(values: Any) -> Any:
            result = values.reshape(-1)[safe_cells]
            return xp.where(cells >= 0, result, 0.0).astype(xp.float32)

        return (gather(resource_x), gather(resource_y)), (gather(hazard_x), gather(hazard_y))

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
        messages: Any,
        message_mask: Any,
        message_age: Any,
        message_confidence: Any,
        message_source_id: Any,
        message_corruption: Any,
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
        quality = xp.clip(xp.asarray(sensor_quality, dtype=xp.float64), 0.05, 2.0)
        raw, raw_age = self.sample(cells)
        raw = raw.astype(xp.float64)
        raw_age = raw_age.astype(xp.float32)
        direct_messages = xp.asarray(messages, dtype=xp.float32)
        direct_mask = xp.asarray(message_mask, dtype=bool)
        direct_age = xp.asarray(message_age, dtype=xp.uint32)
        direct_confidence = xp.asarray(message_confidence, dtype=xp.float32)
        direct_source = xp.asarray(message_source_id, dtype=xp.uint64)
        direct_corruption = xp.asarray(message_corruption, dtype=xp.uint8)

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

        if direct_messages.shape[1]:
            message_sum = (direct_messages * direct_mask[:, :, None]).sum(axis=1)
            message_count = xp.maximum(direct_mask.sum(axis=1, keepdims=True), 1)
            noisy += message_sum / message_count
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
            messages=direct_messages,
            message_mask=direct_mask,
            message_age=direct_age,
            message_confidence=direct_confidence,
            message_source_id=direct_source,
            message_corruption=direct_corruption,
            partner_energy=perceived_energy,
            partner_group_match=group_match.astype(xp.float32),
            partner_mask=partner_mask,
            uncertainty=uncertainty,
        )

    def to_numpy(self, value: Any) -> Any:
        return self.backend.to_numpy(value)
