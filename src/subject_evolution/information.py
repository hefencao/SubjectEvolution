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
    messages: np.ndarray
    message_mask: np.ndarray
    message_age: np.ndarray
    message_confidence: np.ndarray
    message_source_id: np.ndarray
    message_corruption: np.ndarray
    partner_energy: np.ndarray
    partner_group_match: np.ndarray
    partner_mask: np.ndarray
    uncertainty: np.ndarray


@dataclass(frozen=True)
class PendingMessage:
    """A direct signal kept outside the field until its scheduled reception.

    Slots, unlike stable entity ids, may be reused after death.  The queue
    therefore deliberately stores receiver and sender *stable* ids.
    """

    source_id: int
    receiver_id: int
    payload: tuple[float, float, float]
    confidence: float
    emit_tick: int
    receive_tick: int


class InformationSystem:
    """Three-channel field: resource, danger and social guidance."""

    CHANNELS = 3

    def __init__(self, cfg: SimulationConfig) -> None:
        self.cfg = cfg
        gx, gy = cfg.world.grid_x, cfg.world.grid_y
        self.field = np.zeros((self.CHANNELS, gy, gx), dtype=np.float32)
        self.source = np.zeros_like(self.field)
        self.age = np.zeros_like(self.field, dtype=np.uint16)
        self.pending_messages: list[PendingMessage] = []

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

    def emit_direct(
        self,
        source_ids: np.ndarray,
        receiver_ids: np.ndarray,
        payloads: np.ndarray,
        confidences: np.ndarray,
        run_seed: int,
        tick: int,
    ) -> int:
        """Queue point-to-point messages with keyed source noise and delay.

        A signal emitted after observation cannot influence a decision in the
        same tick.  A configured zero delay consequently becomes available at
        the next observation boundary, while retaining a channel delay of zero
        in the event data.
        """
        if self.cfg.information.direct_message_capacity <= 0 or source_ids.size == 0:
            return 0
        valid = (source_ids != 0) & (receiver_ids != 0) & (source_ids != receiver_ids)
        if not np.any(valid):
            return 0
        source_ids = np.asarray(source_ids[valid], dtype=np.uint64)
        receiver_ids = np.asarray(receiver_ids[valid], dtype=np.uint64)
        values = np.asarray(payloads[valid], dtype=np.float64).copy()
        confidence = np.clip(np.asarray(confidences[valid], dtype=np.float64), 0.0, 1.0)
        channel_ctx = RandomContext(run_seed, tick, phase=31, stream=Stream.SIGNAL_CHANNEL)
        for channel in range(self.CHANNELS):
            values[:, channel] += normal(
                channel_ctx,
                source_ids,
                0.0,
                self.cfg.information.source_noise,
                draw_index=100 + channel * 2,
            )
        values = np.maximum(values, 0.0)
        if self.cfg.information.max_signal_delay:
            delay_u = uniform01(channel_ctx, source_ids, draw_index=110)
            delays = np.floor(delay_u * (self.cfg.information.max_signal_delay + 1)).astype(np.int32)
        else:
            delays = np.zeros(source_ids.size, dtype=np.int32)

        self.pending_messages.extend(
            PendingMessage(
                source_id=int(source_id),
                receiver_id=int(receiver_id),
                payload=tuple(float(v) for v in payload),
                confidence=float(conf),
                emit_tick=tick,
                receive_tick=tick + int(delay),
            )
            for source_id, receiver_id, payload, conf, delay in zip(
                source_ids.tolist(), receiver_ids.tolist(), values.tolist(), confidence.tolist(), delays.tolist()
            )
        )
        return int(source_ids.size)

    def _receive_direct(
        self,
        active: np.ndarray,
        stable_ids: np.ndarray,
        sensor_quality: np.ndarray,
        run_seed: int,
        tick: int,
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        """Consume due direct messages into a fixed, masked observation batch."""
        capacity = self.cfg.information.direct_message_capacity
        payload = np.zeros((active.size, capacity, self.CHANNELS), dtype=np.float32)
        mask = np.zeros((active.size, capacity), dtype=bool)
        age = np.zeros((active.size, capacity), dtype=np.uint32)
        confidence = np.zeros((active.size, capacity), dtype=np.float32)
        source = np.zeros((active.size, capacity), dtype=np.uint64)
        corruption = np.zeros((active.size, capacity), dtype=np.uint8)
        if capacity == 0 or not self.pending_messages:
            return payload, mask, age, confidence, source, corruption

        id_to_row = {int(entity_id): row for row, entity_id in enumerate(stable_ids[active].tolist())}
        due: list[PendingMessage] = []
        remaining: list[PendingMessage] = []
        for message in self.pending_messages:
            if message.receive_tick <= tick:
                due.append(message)
            else:
                remaining.append(message)
        self.pending_messages = remaining
        # Stable ordering keeps attention truncation independent of incidental
        # queue insertion order.
        due.sort(key=lambda event: (event.receiver_id, event.source_id, event.emit_tick))
        next_slot = np.zeros(active.size, dtype=np.int32)
        decode_ctx = RandomContext(run_seed, tick, phase=43, stream=Stream.SIGNAL_DECODING)
        for message in due:
            row = id_to_row.get(message.receiver_id)
            if row is None or next_slot[row] >= capacity:
                continue
            receiver_id = np.asarray([message.receiver_id], dtype=np.uint64)
            quality = float(np.clip(sensor_quality[active[row]], 0.05, 2.0))
            strength = float(np.mean(message.payload) / (1.0 + np.mean(message.payload)))
            detected = bool(
                bernoulli(
                    decode_ctx,
                    receiver_id,
                    np.clip((1.0 - self.cfg.information.channel_loss) * quality * (0.2 + 0.8 * strength), 0.0, 1.0),
                    draw_index=int(message.source_id & 0x7FFFFFFF),
                )[0]
            )
            if not detected:
                continue
            slot = int(next_slot[row])
            next_slot[row] += 1
            decoded = np.asarray(message.payload, dtype=np.float64)
            noise = np.asarray(
                [
                    normal(
                        decode_ctx,
                        receiver_id,
                        0.0,
                        self.cfg.information.receiver_noise / quality,
                        draw_index=int((message.source_id + 1 + channel * 17) & 0x7FFFFFFF),
                    )[0]
                    for channel in range(self.CHANNELS)
                ]
            )
            decoded = np.maximum(decoded + noise, 0.0)
            mistaken = bool(
                bernoulli(
                    decode_ctx,
                    receiver_id,
                    np.clip(self.cfg.information.classification_error / quality, 0.0, 1.0),
                    draw_index=int((message.source_id + 71) & 0x7FFFFFFF),
                )[0]
            )
            if mistaken:
                decoded = np.roll(decoded, 1 + int(message.source_id % (self.CHANNELS - 1)))
                corruption[row, slot] |= np.uint8(1)
            payload[row, slot] = decoded.astype(np.float32)
            mask[row, slot] = True
            age[row, slot] = max(0, tick - message.emit_tick)
            confidence[row, slot] = np.float32(
                np.clip(message.confidence * quality / (1.0 + self.cfg.information.receiver_noise), 0.0, 1.0)
            )
            source[row, slot] = np.uint64(message.source_id)
        return payload, mask, age, confidence, source, corruption

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
        (
            messages,
            message_mask,
            message_age,
            message_confidence,
            message_source_id,
            message_corruption,
        ) = self._receive_direct(active, stable_ids, sensor_quality, run_seed, tick)

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

        noisy = np.where(mask, noisy, 0.0)
        # Direct messages are a distinct observation channel, but their decoded
        # content is also folded into the semantic summary consumed by the
        # existing policy backend.  The mask remains available for policies
        # that need to distinguish field and point-to-point evidence.
        if messages.shape[1]:
            message_sum = (messages * message_mask[:, :, None]).sum(axis=1)
            message_count = np.maximum(message_mask.sum(axis=1, keepdims=True), 1)
            noisy += message_sum / message_count
        noisy = noisy.astype(np.float32)

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

        partner_missing = (
            1.0 - partner_mask.mean(axis=1)
            if partner_mask.shape[1]
            else np.ones(active.size, dtype=np.float32)
        )
        uncertainty = np.stack(
            [
                1.0 - mask.mean(axis=1),
                np.full(active.size, self.cfg.information.receiver_noise, dtype=np.float32),
                partner_missing,
            ],
            axis=1,
        ).astype(np.float32)
        return InformationObservation(
            signals=noisy,
            signal_mask=mask,
            signal_age=raw_age,
            messages=messages,
            message_mask=message_mask,
            message_age=message_age,
            message_confidence=message_confidence,
            message_source_id=message_source_id,
            message_corruption=message_corruption,
            partner_energy=perceived_energy,
            partner_group_match=group_match.astype(np.float32),
            partner_mask=partner_mask,
            uncertainty=uncertainty,
        )
