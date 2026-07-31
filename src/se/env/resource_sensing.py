"""Inherited spatial scale for role-free resource-gradient sensing.

The capability changes only the distance over which the existing resource
utility gradient is measured.  It does not reveal a preferred direction,
create a new action, or alter resource fields.  Larger radii bridge broader
spatial structure but average over fine local variation and pay explicit
structure, use, and development energy costs.
"""

from __future__ import annotations

from typing import Any

import numpy as np

from se.cfg import SimulationConfig

RESOURCE_SENSING_GENE_INDEX = 7
RESOURCE_SENSING_SCHEMA = "inherited-discrete-gradient-radius-v1"


def resource_sensing_enabled(cfg: SimulationConfig) -> bool:
    return cfg.entities.resource_sensing_schema == RESOURCE_SENSING_SCHEMA


def resource_sensing_radius(genotype: Any, cfg: SimulationConfig) -> np.ndarray:
    """Return one inherited integer gradient radius per entity.

    The fixed morphology gene is mapped to configured discrete radius levels.
    The mapping is monotonic and deterministic; gene value zero selects the
    midpoint level.  Disabled configurations retain the historical one-cell
    central difference exactly.
    """

    values = np.asarray(genotype, dtype=np.float32)
    if values.ndim != 2 or values.shape[1] <= RESOURCE_SENSING_GENE_INDEX:
        raise ValueError("genotype does not contain the resource-sensing trait")
    if not resource_sensing_enabled(cfg):
        return np.ones(values.shape[0], dtype=np.int16)
    levels = np.asarray(cfg.entities.resource_sensing_radius_levels, dtype=np.int16)
    trait = np.clip(
        values[:, RESOURCE_SENSING_GENE_INDEX], -1.0, 1.0
    ).astype(np.float64, copy=False)
    scaled = 0.5 * (trait + 1.0) * float(levels.size)
    indices = np.minimum(np.floor(scaled).astype(np.int64), levels.size - 1)
    return levels[indices].astype(np.int16, copy=False)


def resource_sensing_energy(
    genotype: Any,
    cfg: SimulationConfig,
    *,
    development: bool = False,
    use: bool = False,
) -> np.ndarray:
    """Return per-entity energy charged for the configured sensing capacity."""

    values = np.asarray(genotype, dtype=np.float32)
    if not resource_sensing_enabled(cfg):
        return np.zeros(values.shape[0], dtype=np.float64)
    if development and use:
        raise ValueError("resource sensing energy cannot be development and use together")
    rate = (
        cfg.entities.resource_sensing_development_energy_per_radius
        if development
        else cfg.entities.resource_sensing_use_energy_per_radius
        if use
        else cfg.entities.resource_sensing_maintenance_energy_per_radius
    )
    return resource_sensing_radius(values, cfg).astype(np.float64) * float(rate)


def resource_sensing_diagnostics(
    alive: Any,
    genotype: Any,
    cfg: SimulationConfig,
) -> dict[str, Any]:
    active = np.flatnonzero(np.asarray(alive, dtype=bool)).astype(np.int32)
    if active.size == 0:
        return {
            "resource_sensing_schema": cfg.entities.resource_sensing_schema,
            "resource_sensing_radius_mean": 1.0,
            "resource_sensing_radius_std": 0.0,
            "resource_sensing_radius_min": 1,
            "resource_sensing_radius_max": 1,
        }
    radius = resource_sensing_radius(
        np.asarray(genotype, dtype=np.float32)[active], cfg
    ).astype(np.float64)
    return {
        "resource_sensing_schema": cfg.entities.resource_sensing_schema,
        "resource_sensing_radius_mean": float(radius.mean()),
        "resource_sensing_radius_std": float(radius.std()),
        "resource_sensing_radius_min": int(radius.min()),
        "resource_sensing_radius_max": int(radius.max()),
    }


__all__ = [
    "RESOURCE_SENSING_GENE_INDEX",
    "RESOURCE_SENSING_SCHEMA",
    "resource_sensing_diagnostics",
    "resource_sensing_enabled",
    "resource_sensing_energy",
    "resource_sensing_radius",
]
