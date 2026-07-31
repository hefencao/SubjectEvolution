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


def resource_recycling_runtime_enabled(environment: Any) -> bool:
    """Return whether configured recycling is active for this runtime branch."""

    return bool(
        external_resource_recycling_enabled(environment.cfg)
        and not bool(getattr(environment, "resource_recycling_ablation_enabled", False))
    )


def initialize_resource_residue(environment: Any) -> None:
    if not external_resource_recycling_enabled(environment.cfg):
        return
    xp = environment.backend.xp if hasattr(environment, "backend") else np
    gy, gx = environment.cfg.world.grid_y, environment.cfg.world.grid_x
    environment.resource_residue = xp.zeros((RESOURCE_CHANNELS, gy, gx), dtype=xp.float32)
    environment.last_resource_residue_released = xp.zeros(RESOURCE_CHANNELS, dtype=xp.float64)
    # Physical residue fluxes remain separate from finite-precision settlement.
    # These counters make short checkpoint-relative ledgers authoritative even
    # when a large float32 field is diffused, released, or sparsely updated.
    environment.resource_residue_field_roundoff_step = np.zeros(
        RESOURCE_CHANNELS, dtype=np.float64
    )
    environment.total_resource_residue_field_roundoff = np.zeros(
        RESOURCE_CHANNELS, dtype=np.float64
    )
    environment.resource_residue_deposit_roundoff_step = np.zeros(
        RESOURCE_CHANNELS, dtype=np.float64
    )
    environment.total_resource_residue_deposit_roundoff = np.zeros(
        RESOURCE_CHANNELS, dtype=np.float64
    )


def _ensure_settlement_counters(environment: Any) -> None:
    """Backfill v0.61 counters when restoring an older full-world checkpoint."""
    for name in (
        "resource_residue_field_roundoff_step",
        "total_resource_residue_field_roundoff",
        "resource_residue_deposit_roundoff_step",
        "total_resource_residue_deposit_roundoff",
    ):
        if not hasattr(environment, name):
            setattr(environment, name, np.zeros(RESOURCE_CHANNELS, dtype=np.float64))


def _channel_totals(environment: Any, values: Any) -> np.ndarray:
    """Return stable host float64 channel totals for a backend field."""
    xp = environment.backend.xp if hasattr(environment, "backend") else np
    totals = values.sum(axis=(1, 2), dtype=xp.float64)
    if hasattr(environment, "backend"):
        totals = environment.backend.to_numpy(totals)
    return np.asarray(totals, dtype=np.float64)


def deposit_resource_residue(
    environment: Any, cell_ids: Any, amounts: Any
) -> np.ndarray:
    """Deposit non-negative channel-preserving material at source cells."""
    if not resource_recycling_runtime_enabled(environment):
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
    _ensure_settlement_counters(environment)
    before = _channel_totals(environment, environment.resource_residue)
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
        host_values = environment.backend.to_numpy(values[:, channel]) if backend else values[:, channel]
        totals.append(float(np.asarray(host_values, dtype=np.float64).sum()))
    requested = np.asarray(totals, dtype=np.float64)
    after = _channel_totals(environment, environment.resource_residue)
    settlement = after - before - requested
    environment.resource_residue_deposit_roundoff_step += settlement
    environment.total_resource_residue_deposit_roundoff += settlement
    return requested


def update_resource_recycling(environment: Any) -> np.ndarray:
    """Diffuse residue and release it into same-channel resource capacity."""
    if not resource_recycling_runtime_enabled(environment):
        return np.zeros(RESOURCE_CHANNELS, dtype=np.float64)
    xp = environment.backend.xp if hasattr(environment, "backend") else np
    _ensure_settlement_counters(environment)
    environment.resource_residue_field_roundoff_step.fill(0.0)
    environment.resource_residue_deposit_roundoff_step.fill(0.0)
    before = _channel_totals(environment, environment.resource_residue)
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
    released_totals = (
        np.asarray(environment.backend.to_numpy(totals_backend), dtype=np.float64)
        if hasattr(environment, "backend")
        else np.asarray(totals_backend, dtype=np.float64)
    )
    after = _channel_totals(environment, environment.resource_residue)
    settlement = after + released_totals - before
    environment.resource_residue_field_roundoff_step += settlement
    environment.total_resource_residue_field_roundoff += settlement
    return released_totals


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
    _ensure_settlement_counters(environment)
    return {
        "resource_recycling_configured": True,
        "resource_recycling_ablation_enabled": bool(
            getattr(environment, "resource_recycling_ablation_enabled", False)
        ),
        "resource_recycling_effective_enabled": resource_recycling_runtime_enabled(environment),
        "resource_residue_total": values.sum(axis=(1, 2)).tolist(),
        "resource_residue_mean": values.mean(axis=(1, 2)).tolist(),
        "resource_residue_std": values.std(axis=(1, 2)).tolist(),
        "resource_residue_field_roundoff_total": np.asarray(
            environment.total_resource_residue_field_roundoff, dtype=np.float64
        ).tolist(),
        "resource_residue_deposit_roundoff_total": np.asarray(
            environment.total_resource_residue_deposit_roundoff, dtype=np.float64
        ).tolist(),
        "resource_residue_numerical_adjustment_total": (
            np.asarray(environment.total_resource_residue_field_roundoff, dtype=np.float64)
            + np.asarray(environment.total_resource_residue_deposit_roundoff, dtype=np.float64)
        ).tolist(),
    }


__all__ = [
    "deposit_resource_residue",
    "initialize_resource_residue",
    "resource_recycling_diagnostics",
    "resource_recycling_runtime_enabled",
    "update_resource_recycling",
]
