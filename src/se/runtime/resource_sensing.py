"""Runtime integration helpers for inherited resource-sensing capacity."""

from __future__ import annotations

from typing import Any

import numpy as np

from se.env.resource_sensing import resource_sensing_energy, resource_sensing_radius


def effective_resource_sensing_radius(simulation: Any) -> np.ndarray:
    """Return the world-facing radius while preserving inherited capacity state."""

    if simulation.resource_sensing_ablation_enabled:
        return np.ones(simulation.entities.alive.size, dtype=np.int16)
    return resource_sensing_radius(simulation.entities.genotype, simulation.cfg)


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
    """Charge structure and active-use costs without depending on effective radius."""

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
