"""Runtime integration helpers for inherited resource-sensing capacity."""
from __future__ import annotations

from typing import Any

import numpy as np

from se.env.resource_sensing import (
    channel_routed_resource_sensing_enabled,
    resource_sensing_channel_radii,
    resource_sensing_energy,
)
from se.env.niches import resource_affinity_quantized


def effective_resource_sensing_radius(
    simulation: Any,
    resource_affinity_q: np.ndarray | None = None,
) -> np.ndarray:
    """Return world-facing per-channel radii while preserving capacity state."""

    rows = simulation.entities.alive.size
    if simulation.resource_sensing_ablation_enabled:
        if channel_routed_resource_sensing_enabled(simulation.cfg):
            return np.ones((rows, 4), dtype=np.int16)
        return np.ones(rows, dtype=np.int16)
    affinity = resource_affinity_q
    if affinity is None and channel_routed_resource_sensing_enabled(simulation.cfg):
        affinity = resource_affinity_quantized(
            simulation.entities.genotype, simulation.cfg
        )
    channel_radii = resource_sensing_channel_radii(
        simulation.entities.genotype,
        simulation.cfg,
        resource_affinity_q=affinity,
    )
    if channel_routed_resource_sensing_enabled(simulation.cfg):
        return channel_radii
    return channel_radii[:, 0]


def record_resource_sensing_development_cost(
    simulation: Any, newborns: np.ndarray, stats: Any
) -> None:
    stats.resource_sensing_development_energy = float(
        resource_sensing_energy(
            simulation.entities.genotype[newborns],
            simulation.cfg,
            development=True,
        ).sum(dtype=np.float64)
    )


def add_resource_sensing_operating_cost(
    simulation: Any,
    current_active: np.ndarray,
    preexisting_active: np.ndarray,
    cost: np.ndarray,
    stats: Any,
) -> np.ndarray:
    """Charge structure and use costs from inherited capacity, not ablation."""

    genotype = simulation.entities.genotype[current_active]
    maintenance = resource_sensing_energy(genotype, simulation.cfg)
    use = resource_sensing_energy(genotype, simulation.cfg, use=True)
    use *= np.isin(current_active, preexisting_active, assume_unique=True)
    stats.resource_sensing_maintenance_energy = float(
        maintenance.sum(dtype=np.float64)
    )
    stats.resource_sensing_use_energy = float(use.sum(dtype=np.float64))
    return np.asarray(cost, dtype=np.float64) + maintenance + use


__all__ = [
    "add_resource_sensing_operating_cost",
    "effective_resource_sensing_radius",
    "record_resource_sensing_development_cost",
]
