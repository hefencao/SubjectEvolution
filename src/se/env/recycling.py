"""Identity-preserving external residue pool for D3-C.

Internal raw-store decay and raw material carried by dead entities enter a
four-channel spatial residue field.  The field diffuses with the existing
per-channel resource diffusion rates and releases material back into the same
resource channel only when environmental capacity is available.  No channel
is assigned a named trophic or metabolic role.
"""
from __future__ import annotations
from typing import Any
import numpy as np

from se.differentiation.physiology import external_resource_recycling_enabled
from se.env.diversity import diffuse_resource_fields
from se.reductions import stable_segmented_sum, validate_cell_ids

RESOURCE_CHANNELS = 4


def initialize_resource_residue(environment: Any) -> None:
    if not external_resource_recycling_enabled(environment.cfg):
        return
    xp = environment.backend.xp if hasattr(environment, "backend") else np
    gy, gx = environment.cfg.world.grid_y, environment.cfg.world.grid_x
    environment.resource_residue = xp.zeros((RESOURCE_CHANNELS, gy, gx), dtype=xp.float32)
    environment.last_resource_residue_released = xp.zeros(RESOURCE_CHANNELS, dtype=xp.float64)


def deposit_resource_residue(
    environment: Any, cell_ids: Any, amounts: Any
) -> np.ndarray:
    """Deposit non-negative channel-preserving material at source cells."""
    if not external_resource_recycling_enabled(environment.cfg):
        return np.zeros(RESOURCE_CHANNELS, dtype=np.float64)
    xp = environment.backend.xp if hasattr(environment, "backend") else np
    backend = environment.backend if hasattr(environment, "backend") else None
    cells = validate_cell_ids(
        cell_ids,
        environment.cfg.world.grid_x * environment.cfg.world.grid_y,
        backend=backend,
    )
    values = xp.asarray(amounts, dtype=xp.float32)
    if values.shape != (int(cells.size), RESOURCE_CHANNELS):
        raise ValueError("resource residue deposits must be shaped [N, 4]")
    if int(cells.size) == 0:
        return np.zeros(RESOURCE_CHANNELS, dtype=np.float64)
    if bool(xp.any(~xp.isfinite(values))) or bool(xp.any(values < 0.0)):
        raise ValueError("resource residue deposits must be finite and non-negative")
    flat = environment.resource_residue.reshape(RESOURCE_CHANNELS, -1)
    cell_count = environment.cfg.world.grid_x * environment.cfg.world.grid_y
    totals: list[float] = []
    for channel in range(RESOURCE_CHANNELS):
        deposited = stable_segmented_sum(
            cells,
            values[:, channel],
            cell_count,
            backend=backend,
            dtype=xp.float32,
        )
        flat[channel] = flat[channel] + deposited
        totals.append(float(np.asarray(environment.backend.to_numpy(values[:, channel]) if backend else values[:, channel], dtype=np.float64).sum()))
    return np.asarray(totals, dtype=np.float64)


def update_resource_recycling(environment: Any) -> np.ndarray:
    """Diffuse residue and release it into same-channel resource capacity."""
    if not external_resource_recycling_enabled(environment.cfg):
        return np.zeros(RESOURCE_CHANNELS, dtype=np.float64)
    xp = environment.backend.xp if hasattr(environment, "backend") else np
    residue = diffuse_resource_fields(
        environment.resource_residue,
        environment.cfg.environment.resource_diffusion_rates,
        xp=xp,
    )
    residue = xp.maximum(residue, xp.float32(0.0)).astype(xp.float32)
    rate = xp.asarray(
        environment.cfg.physiology.resource_store_decay_per_tick,
        dtype=xp.float32,
    )[:, None, None]
    potential = residue * rate
    room = xp.maximum(environment.capacity - environment.resources, xp.float32(0.0))
    released = xp.minimum(potential, room).astype(xp.float32)
    environment.resource_residue = xp.maximum(residue - released, xp.float32(0.0)).astype(xp.float32)
    environment.resources = xp.minimum(environment.resources + released, environment.capacity).astype(xp.float32)
    totals_backend = released.sum(axis=(1, 2), dtype=xp.float64)
    environment.last_resource_residue_released = totals_backend
    if hasattr(environment, "backend"):
        return np.asarray(environment.backend.to_numpy(totals_backend), dtype=np.float64)
    return np.asarray(totals_backend, dtype=np.float64)


def resource_recycling_diagnostics(environment: Any) -> dict[str, object]:
    if not external_resource_recycling_enabled(environment.cfg):
        return {
            "resource_residue_total": [0.0] * RESOURCE_CHANNELS,
            "resource_residue_mean": [0.0] * RESOURCE_CHANNELS,
            "resource_residue_std": [0.0] * RESOURCE_CHANNELS,
        }
    values = (
        environment.backend.to_numpy(environment.resource_residue)
        if hasattr(environment, "backend")
        else environment.resource_residue
    )
    values = np.asarray(values, dtype=np.float64)
    return {
        "resource_residue_total": values.sum(axis=(1, 2)).tolist(),
        "resource_residue_mean": values.mean(axis=(1, 2)).tolist(),
        "resource_residue_std": values.std(axis=(1, 2)).tolist(),
    }


__all__ = [
    "deposit_resource_residue",
    "initialize_resource_residue",
    "resource_recycling_diagnostics",
    "update_resource_recycling",
]
