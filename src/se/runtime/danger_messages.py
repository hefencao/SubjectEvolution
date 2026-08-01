"""Directional use of source-bearing direct danger messages.

The message does not prescribe a role or action.  It supplies a physical
bearing: when a receiver chooses FLEE, the policy can move away from the
current position of a detected danger-message source.  Disabled defaults leave
all archived policies unchanged.
"""
from __future__ import annotations

from typing import Any

from se.backend import backend_from_array
from se.cfg import SimulationConfig
from se.information import InformationObservation

DIRECTION_SCHEMA = "source-bearing-direct-message-v1"


def _periodic_delta(delta: Any, extent: float, xp: Any) -> Any:
    half = float(extent) * 0.5
    return (delta + half) % float(extent) - half


def direct_danger_bearing(
    *,
    active: Any,
    stable_ids: Any,
    x: Any,
    y: Any,
    info: InformationObservation,
    cfg: SimulationConfig,
) -> tuple[Any, Any]:
    """Return active-row unit vectors pointing toward danger-message sources."""
    xp = backend_from_array(active).xp
    rows = xp.asarray(active, dtype=xp.int32)
    zero = xp.zeros(rows.size, dtype=xp.float32)
    if cfg.entities.danger_message_direction_schema != DIRECTION_SCHEMA:
        return zero, zero
    source_ids = xp.asarray(info.message_source_id, dtype=xp.uint64)
    if source_ids.ndim != 2 or int(source_ids.shape[1]) == 0:
        return zero, zero
    ids = xp.asarray(stable_ids, dtype=xp.uint64)
    living_slots = xp.flatnonzero(ids != 0)
    if int(living_slots.size) == 0:
        return zero, zero
    order = xp.argsort(ids[living_slots])
    sorted_slots = living_slots[order]
    sorted_ids = ids[sorted_slots]
    flat_sources = source_ids.reshape(-1)
    positions = xp.searchsorted(sorted_ids, flat_sources)
    safe_positions = xp.minimum(positions, max(int(sorted_ids.size) - 1, 0))
    source_slots = sorted_slots[safe_positions].reshape(source_ids.shape)
    exact = (positions < int(sorted_ids.size)) & (
        sorted_ids[safe_positions] == flat_sources
    )
    exact = exact.reshape(source_ids.shape)
    messages = xp.asarray(info.messages, dtype=xp.float32)
    message_mask = xp.asarray(info.message_mask, dtype=bool)
    confidence = xp.asarray(info.message_confidence, dtype=xp.float32)
    danger = messages[:, :, 1]
    valid = message_mask & exact & (flat_sources.reshape(source_ids.shape) != 0) & (danger > 0.02)

    receiver_x = xp.asarray(x, dtype=xp.float32)[rows][:, None]
    receiver_y = xp.asarray(y, dtype=xp.float32)[rows][:, None]
    source_x = xp.asarray(x, dtype=xp.float32)[source_slots]
    source_y = xp.asarray(y, dtype=xp.float32)[source_slots]
    dx = source_x - receiver_x
    dy = source_y - receiver_y
    if cfg.world.periodic:
        dx = _periodic_delta(dx, cfg.world.width, xp)
        dy = _periodic_delta(dy, cfg.world.height, xp)
    magnitude = xp.maximum(xp.hypot(dx, dy), xp.float32(1.0e-6))
    weights = xp.where(valid, danger * confidence, xp.float32(0.0))
    total = weights.sum(axis=1)
    bearing_x = xp.where(
        total > 0.0,
        (weights * (dx / magnitude)).sum(axis=1) / xp.maximum(total, 1.0e-6),
        0.0,
    )
    bearing_y = xp.where(
        total > 0.0,
        (weights * (dy / magnitude)).sum(axis=1) / xp.maximum(total, 1.0e-6),
        0.0,
    )
    return bearing_x.astype(xp.float32), bearing_y.astype(xp.float32)


__all__ = ["DIRECTION_SCHEMA", "direct_danger_bearing"]
