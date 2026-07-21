from __future__ import annotations

from dataclasses import dataclass
import numpy as np

from .config import SimulationConfig
from .random_api import RandomContext, Stream, bernoulli, normal, uniform01
from .reductions import stable_segmented_sum, validate_cell_ids


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
        cells = validate_cell_ids(cell_ids, self.cfg.world.grid_x * self.cfg.world.grid_y)
        values = np.asarray(strengths, dtype=np.float32)
        if values.ndim != 1 or values.shape[0] != cells.shape[0]:
            raise ValueError("strengths must contain one value per cell id")
        flat = self.source[channel].reshape(-1)
        flat += stable_segmented_sum(
            cells,
            values,
            self.cfg.world.grid_x * self.cfg.world.grid_y,
            dtype=np.float32,
        )

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

        due: list[PendingMessage] = []
        remaining: list[PendingMessage] = []
        for message in self.pending_messages:
            if message.receive_tick <= tick:
                due.append(message)
            else:
                remaining.append(message)
        self.pending_messages = remaining
        if not due:
            return payload, mask, age, confidence, source, corruption

        # Stable ordering keeps attention truncation independent of incidental
        # queue insertion order.
        source_ids = np.fromiter((event.source_id for event in due), dtype=np.uint64, count=len(due))
        receiver_ids = np.fromiter((event.receiver_id for event in due), dtype=np.uint64, count=len(due))
        emit_ticks = np.fromiter((event.emit_tick for event in due), dtype=np.int64, count=len(due))
        payloads = np.asarray([event.payload for event in due], dtype=np.float64)
        confidences = np.fromiter((event.confidence for event in due), dtype=np.float64, count=len(due))
        order = np.lexsort((emit_ticks, source_ids, receiver_ids))
        source_ids = source_ids[order]
        receiver_ids = receiver_ids[order]
        emit_ticks = emit_ticks[order]
        payloads = payloads[order]
        confidences = confidences[order]

        # Entity slots are not ordered by stable ID after births and deaths.
        # Resolve every receiver to its dense active row with one stable sort
        # and binary lookup rather than a Python dictionary lookup per event.
        active_ids = stable_ids[active].astype(np.uint64, copy=False)
        id_order = np.argsort(active_ids, kind="stable")
        sorted_ids = active_ids[id_order]
        location = np.searchsorted(sorted_ids, receiver_ids)
        in_range = location < sorted_ids.size
        safe_location = np.where(in_range, location, 0)
        valid = in_range & (sorted_ids[safe_location] == receiver_ids)
        if not np.any(valid):
            return payload, mask, age, confidence, source, corruption

        rows = id_order[safe_location[valid]].astype(np.int32, copy=False)
        source_ids = source_ids[valid]
        receiver_ids = receiver_ids[valid]
        emit_ticks = emit_ticks[valid]
        payloads = payloads[valid]
        confidences = confidences[valid]
        quality = np.clip(sensor_quality[active[rows]], 0.05, 2.0).astype(np.float64)
        decode_ctx = RandomContext(run_seed, tick, phase=43, stream=Stream.SIGNAL_DECODING)

        strength = payloads.mean(axis=1)
        strength = strength / (1.0 + strength)
        detected = bernoulli(
            decode_ctx,
            receiver_ids,
            np.clip(
                (1.0 - self.cfg.information.channel_loss) * quality * (0.2 + 0.8 * strength),
                0.0,
                1.0,
            ),
            draw_index=source_ids & np.uint64(0x7FFFFFFF),
        )

        # The reference semantics keep the first ``capacity`` successfully
        # detected messages per receiver in the stable order above.  Prefix
        # sums reproduce that exact attention allocation without per-message
        # Python state.
        group_start = np.empty(receiver_ids.size, dtype=bool)
        group_start[0] = True
        group_start[1:] = receiver_ids[1:] != receiver_ids[:-1]
        cumulative = np.cumsum(detected, dtype=np.int32)
        group_base = np.where(group_start, cumulative - detected.astype(np.int32), 0)
        group_base = np.maximum.accumulate(group_base)
        slots = cumulative - group_base - 1
        accepted = detected & (slots < capacity)
        if not np.any(accepted):
            return payload, mask, age, confidence, source, corruption

        rows = rows[accepted]
        slots = slots[accepted].astype(np.int32, copy=False)
        source_ids = source_ids[accepted]
        receiver_ids = receiver_ids[accepted]
        emit_ticks = emit_ticks[accepted]
        payloads = payloads[accepted]
        confidences = confidences[accepted]
        quality = quality[accepted]

        decoded = payloads.copy()
        draw_base = (source_ids + np.uint64(1)) & np.uint64(0x7FFFFFFF)
        for channel in range(self.CHANNELS):
            decoded[:, channel] += normal(
                decode_ctx,
                receiver_ids,
                0.0,
                self.cfg.information.receiver_noise / quality,
                draw_index=(draw_base + np.uint64(channel * 17)) & np.uint64(0x7FFFFFFF),
            )
        decoded = np.maximum(decoded, 0.0)
        mistaken = bernoulli(
            decode_ctx,
            receiver_ids,
            np.clip(self.cfg.information.classification_error / quality, 0.0, 1.0),
            draw_index=(source_ids + np.uint64(71)) & np.uint64(0x7FFFFFFF),
        )
        if np.any(mistaken):
            shift = 1 + (source_ids[mistaken] % np.uint64(self.CHANNELS - 1)).astype(np.int32)
            columns = (np.arange(self.CHANNELS)[None, :] - shift[:, None]) % self.CHANNELS
            decoded[mistaken] = np.take_along_axis(decoded[mistaken], columns, axis=1)
            corruption[rows[mistaken], slots[mistaken]] = np.uint8(1)

        payload[rows, slots] = decoded.astype(np.float32)
        mask[rows, slots] = True
        age[rows, slots] = np.maximum(tick - emit_ticks, 0).astype(np.uint32)
        confidence[rows, slots] = np.clip(
            confidences * quality / (1.0 + self.cfg.information.receiver_noise), 0.0, 1.0
        ).astype(np.float32)
        source[rows, slots] = source_ids
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
