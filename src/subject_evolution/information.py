from __future__ import annotations

from dataclasses import dataclass
import numpy as np

from .config import SimulationConfig
from .random_api import RandomContext, Stream, bernoulli, normal, uniform01


@dataclass
class InformationObservation:
    signals: np.ndarray
    signal_mask: np.ndarray
    signal_age: np.ndarray
    partner_energy: np.ndarray
    partner_group_match: np.ndarray
    partner_mask: np.ndarray
    uncertainty: np.ndarray


class InformationSystem:
    """Three-channel field: resource, danger and social guidance."""

    CHANNELS = 3

    def __init__(self, cfg: SimulationConfig) -> None:
        self.cfg = cfg
        gx, gy = cfg.world.grid_x, cfg.world.grid_y
        self.field = np.zeros((self.CHANNELS, gy, gx), dtype=np.float32)
        self.source = np.zeros_like(self.field)
        self.age = np.zeros_like(self.field, dtype=np.uint16)

    def propagate(self) -> None:
        decay = self.cfg.environment.signal_decay
        diffusion = self.cfg.environment.signal_diffusion
        center = self.field
        neighbor_mean = (
            np.roll(center, 1, axis=1)
            + np.roll(center, -1, axis=1)
            + np.roll(center, 1, axis=2)
            + np.roll(center, -1, axis=2)
        ) * 0.25
        self.field = ((1.0 - decay - diffusion) * center + diffusion * neighbor_mean + self.source).astype(np.float32)
        self.field = np.maximum(self.field, 0.0)
        active = self.field > 1e-6
        self.age = np.where(active, np.minimum(self.age.astype(np.uint32) + 1, 65535), 0).astype(np.uint16)
        self.source.fill(0.0)

    def emit(self, channel: int, cell_ids: np.ndarray, strengths: np.ndarray) -> None:
        if not 0 <= channel < self.CHANNELS:
            raise ValueError(f"invalid signal channel {channel}")
        flat = self.source[channel].reshape(-1)
        np.add.at(flat, cell_ids.astype(np.int64), strengths.astype(np.float32))

    def observe(
        self,
        active: np.ndarray,
        stable_ids: np.ndarray,
        cell_ids: np.ndarray,
        partners: np.ndarray,
        energy: np.ndarray,
        group_id: np.ndarray,
        sensor_quality: np.ndarray,
        run_seed: int,
        tick: int,
    ) -> InformationObservation:
        ids = stable_ids[active]
        raw = self.field.reshape(self.CHANNELS, -1)[:, cell_ids].T.astype(np.float64)
        raw_age = self.age.reshape(self.CHANNELS, -1)[:, cell_ids].T.astype(np.float32)
        quality = np.clip(sensor_quality[active], 0.05, 2.0)

        detect_ctx = RandomContext(run_seed, tick, phase=40, stream=Stream.SIGNAL_DETECTION)
        strength = raw / (1.0 + raw)
        detection_p = np.clip((1.0 - self.cfg.information.channel_loss) * quality[:, None] * (0.2 + 0.8 * strength), 0.0, 1.0)
        mask = np.empty_like(raw, dtype=bool)
        for channel in range(self.CHANNELS):
            mask[:, channel] = bernoulli(detect_ctx, ids, detection_p[:, channel], draw_index=channel)

        decode_ctx = RandomContext(run_seed, tick, phase=41, stream=Stream.SIGNAL_DECODING)
        noisy = raw.copy()
        for channel in range(self.CHANNELS):
            noise_scale = self.cfg.information.receiver_noise / quality
            noisy[:, channel] += normal(decode_ctx, ids, 0.0, noise_scale, draw_index=channel * 2)
        noisy = np.maximum(noisy, 0.0)

        # Classification mistakes rotate the three semantic channels.
        misclassified = bernoulli(
            decode_ctx,
            ids,
            self.cfg.information.classification_error / quality,
            draw_index=20,
        )
        if np.any(misclassified):
            shift = 1 + (uniform01(decode_ctx, ids, draw_index=21) * 2).astype(np.int32)
            rows = np.flatnonzero(misclassified)
            old = noisy[rows].copy()
            old_mask = mask[rows].copy()
            for row_pos, row in enumerate(rows):
                noisy[row] = np.roll(old[row_pos], int(shift[row]))
                mask[row] = np.roll(old_mask[row_pos], int(shift[row]))

        noisy = np.where(mask, noisy, 0.0).astype(np.float32)

        partner_mask = partners >= 0
        safe_partners = np.where(partner_mask, partners, 0)
        actual_partner_energy = energy[safe_partners]
        partner_detect_ctx = RandomContext(run_seed, tick, phase=42, stream=Stream.SIGNAL_CHANNEL)
        for draw in range(partners.shape[1]):
            received = bernoulli(
                partner_detect_ctx,
                ids,
                np.clip((1.0 - self.cfg.information.channel_loss) * quality, 0.0, 1.0),
                draw_index=draw,
            )
            partner_mask[:, draw] &= received
        partner_noise = np.zeros_like(actual_partner_energy, dtype=np.float64)
        for draw in range(partners.shape[1]):
            partner_noise[:, draw] = normal(
                decode_ctx,
                ids,
                0.0,
                self.cfg.information.receiver_noise / quality,
                draw_index=40 + draw * 2,
            )
        perceived_energy = np.maximum(actual_partner_energy + partner_noise, 0.0)
        perceived_energy = np.where(partner_mask, perceived_energy, 0.0).astype(np.float32)
        own_groups = group_id[active, None]
        partner_groups = group_id[safe_partners]
        group_match = (own_groups != 0) & (own_groups == partner_groups) & partner_mask

        uncertainty = np.stack(
            [
                1.0 - mask.mean(axis=1),
                np.full(active.size, self.cfg.information.receiver_noise, dtype=np.float32),
                1.0 - partner_mask.mean(axis=1),
            ],
            axis=1,
        ).astype(np.float32)
        return InformationObservation(
            signals=noisy,
            signal_mask=mask,
            signal_age=raw_age,
            partner_energy=perceived_energy,
            partner_group_match=group_match.astype(np.float32),
            partner_mask=partner_mask,
            uncertainty=uncertainty,
        )
