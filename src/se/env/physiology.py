"""Independent abiotic fields used by the opt-in physiological ecology model."""

from __future__ import annotations

from dataclasses import dataclass
import numpy as np

from se.cfg import SimulationConfig

PHYSIOLOGY_ENVIRONMENT_SCHEMA = "oxygen-terrain-wear-mosaic-v1"


@dataclass(frozen=True)
class PhysiologyFieldMetrics:
    effective_dimensions: float
    correlations: list[list[float]]
    means: list[float]
    standard_deviations: list[float]


def _wave(
    xnorm: object,
    ynorm: object,
    *,
    wave_x: float,
    wave_y: float,
    phase: float,
    xp: object = np,
) -> object:
    primary = xp.sin(2.0 * xp.pi * (wave_x * xnorm + wave_y * ynorm) + phase)
    secondary = xp.cos(
        2.0 * xp.pi * ((wave_y + 0.5) * xnorm - (wave_x - 0.25) * ynorm)
        - 0.7 * phase
    )
    return xp.clip(0.5 + 0.32 * primary + 0.18 * secondary, 0.0, 1.0)


def physiology_fields(
    cfg: SimulationConfig,
    tick: int,
    *,
    xp: object = np,
) -> tuple[object, object, object]:
    """Return normalized oxygen availability, terrain resistance, and wear."""

    gy, gx = cfg.world.grid_y, cfg.world.grid_x
    if cfg.environment.physiology_environment_schema != PHYSIOLOGY_ENVIRONMENT_SCHEMA:
        return (
            xp.ones((gy, gx), dtype=xp.float32),
            xp.zeros((gy, gx), dtype=xp.float32),
            xp.zeros((gy, gx), dtype=xp.float32),
        )
    yy, xx = xp.mgrid[0:gy, 0:gx]
    xnorm = xx.astype(xp.float64) / max(gx - 1, 1)
    ynorm = yy.astype(xp.float64) / max(gy - 1, 1)
    oxygen_phase = (
        2.0 * xp.pi * tick / max(cfg.environment.oxygen_period, 1)
        + cfg.environment.oxygen_phase_offset
    )
    wear_phase = (
        2.0 * xp.pi * tick / max(cfg.environment.wear_period, 1)
        + cfg.environment.wear_phase_offset
    )
    oxygen = cfg.environment.oxygen_floor + cfg.environment.oxygen_amplitude * _wave(
        xnorm,
        ynorm,
        wave_x=cfg.environment.oxygen_wave_x,
        wave_y=cfg.environment.oxygen_wave_y,
        phase=oxygen_phase,
        xp=xp,
    )
    terrain = cfg.environment.terrain_floor + cfg.environment.terrain_amplitude * _wave(
        xnorm,
        ynorm,
        wave_x=cfg.environment.terrain_wave_x,
        wave_y=cfg.environment.terrain_wave_y,
        phase=cfg.environment.terrain_phase_offset,
        xp=xp,
    )
    wear = cfg.environment.wear_floor + cfg.environment.wear_amplitude * _wave(
        xnorm,
        ynorm,
        wave_x=cfg.environment.wear_wave_x,
        wave_y=cfg.environment.wear_wave_y,
        phase=wear_phase,
        xp=xp,
    )
    return tuple(
        xp.clip(field, 0.0, 1.0).astype(xp.float32)
        for field in (oxygen, terrain, wear)
    )


def field_metrics(oxygen: np.ndarray, terrain: np.ndarray, wear: np.ndarray) -> PhysiologyFieldMetrics:
    values = np.column_stack(
        [np.asarray(field, dtype=np.float64).reshape(-1) for field in (oxygen, terrain, wear)]
    )
    centered = values - values.mean(axis=0, keepdims=True)
    covariance = centered.T @ centered / max(values.shape[0] - 1, 1)
    eigenvalues = np.clip(np.linalg.eigvalsh(covariance), 0.0, None)
    total = float(eigenvalues.sum())
    squared = float(np.square(eigenvalues).sum())
    effective = total * total / squared if squared > 0.0 else 0.0
    std = values.std(axis=0)
    correlations_array = np.zeros((3, 3), dtype=np.float64)
    for left in range(3):
        for right in range(3):
            if std[left] > 1.0e-12 and std[right] > 1.0e-12:
                correlations_array[left, right] = float(
                    np.mean(centered[:, left] * centered[:, right])
                    / (std[left] * std[right])
                )
            elif left == right:
                correlations_array[left, right] = 1.0
    correlations = correlations_array.tolist()
    return PhysiologyFieldMetrics(
        effective_dimensions=effective,
        correlations=correlations,
        means=values.mean(axis=0).tolist(),
        standard_deviations=std.tolist(),
    )


__all__ = [
    "PHYSIOLOGY_ENVIRONMENT_SCHEMA",
    "PhysiologyFieldMetrics",
    "field_metrics",
    "physiology_fields",
]
