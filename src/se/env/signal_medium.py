"""Independent physical medium for signal transport.

Locomotion terrain and communication conditions are distinct fields.  A ridge
may be hard to traverse but optically open; a flat corridor may be easy to
cross while canopy, fog, walls, or acoustic masking make communication poor.
The field is role-neutral and does not inspect messages, entities, groups, or
genes.
"""
from __future__ import annotations

from typing import Any

import numpy as np

from se.cfg import SimulationConfig

INDEPENDENT_SIGNAL_MEDIUM_SCHEMA = "independent-openness-mosaic-v1"


def _wave(
    xnorm: Any,
    ynorm: Any,
    *,
    wave_x: float,
    wave_y: float,
    phase: float,
    xp: Any,
) -> Any:
    primary = xp.sin(2.0 * xp.pi * (wave_x * xnorm + wave_y * ynorm) + phase)
    secondary = xp.cos(
        2.0 * xp.pi * ((wave_y + 0.5) * xnorm - (wave_x - 0.25) * ynorm)
        - 0.7 * phase
    )
    return xp.clip(0.5 + 0.32 * primary + 0.18 * secondary, 0.0, 1.0)


def signal_openness_field(
    cfg: SimulationConfig,
    tick: int,
    *,
    xp: Any = np,
) -> Any:
    """Return normalized communication openness in ``[0, 1]``.

    ``1`` means the configured carrier crosses the cell with minimal medium
    attenuation; ``0`` means strongly obstructed.  This is not movement
    terrain, elevation, reward, or a semantic message route.
    """

    gy, gx = cfg.world.grid_y, cfg.world.grid_x
    if cfg.environment.signal_medium_schema != INDEPENDENT_SIGNAL_MEDIUM_SCHEMA:
        return xp.ones((gy, gx), dtype=xp.float32)
    yy, xx = xp.mgrid[0:gy, 0:gx]
    xnorm = xx.astype(xp.float64) / max(gx - 1, 1)
    ynorm = yy.astype(xp.float64) / max(gy - 1, 1)
    period = int(cfg.environment.signal_openness_period)
    phase = float(cfg.environment.signal_openness_phase_offset)
    if period > 0:
        phase += 2.0 * xp.pi * tick / period
    openness = (
        float(cfg.environment.signal_openness_floor)
        + float(cfg.environment.signal_openness_amplitude)
        * _wave(
            xnorm,
            ynorm,
            wave_x=float(cfg.environment.signal_openness_wave_x),
            wave_y=float(cfg.environment.signal_openness_wave_y),
            phase=phase,
            xp=xp,
        )
    )
    return xp.clip(openness, 0.0, 1.0).astype(xp.float32)


def medium_metrics(openness: Any, movement_resistance: Any) -> dict[str, float]:
    open_values = np.asarray(openness, dtype=np.float64).reshape(-1)
    movement = np.asarray(movement_resistance, dtype=np.float64).reshape(-1)
    if open_values.shape != movement.shape:
        raise ValueError("signal openness and movement resistance must align")
    open_std = float(open_values.std())
    movement_std = float(movement.std())
    correlation = 0.0
    if open_std > 1.0e-12 and movement_std > 1.0e-12:
        correlation = float(np.corrcoef(open_values, movement)[0, 1])
    return {
        "signal_openness_mean": float(open_values.mean()),
        "signal_openness_std": open_std,
        "movement_resistance_mean": float(movement.mean()),
        "movement_resistance_std": movement_std,
        "movement_signal_correlation": correlation,
    }


__all__ = [
    "INDEPENDENT_SIGNAL_MEDIUM_SCHEMA",
    "medium_metrics",
    "signal_openness_field",
]
