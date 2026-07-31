"""Runtime integration helpers for inherited resource-sensing capacity."""
from __future__ import annotations

from typing import Any

import numpy as np

from se.env.resource_sensing import (
    channel_routed_resource_sensing_enabled,
    demand_gated_resource_sensing_enabled,
    resource_sensing_channel_radii,
    resource_sensing_energy,
    resource_sensing_observation_weights_q,
)
from se.env.niches import resource_affinity_quantized


def _full_storage_room_fraction(
    simulation: Any,
    *,
    active: np.ndarray | None,
    storage_room_fraction: np.ndarray | None,
) -> np.ndarray | None:
    if not demand_gated_resource_sensing_enabled(simulation.cfg):
        return None
    if active is None or storage_room_fraction is None:
        raise ValueError("demand-gated resource sensing requires active storage room")
    rows = simulation.entities.alive.size
    indices = np.asarray(active, dtype=np.int32)
    room = np.asarray(storage_room_fraction, dtype=np.float32)
    if room.shape != (indices.size, 4):
        raise ValueError("active storage room fraction must be shaped [active, 4]")
    full = np.zeros((rows, 4), dtype=np.float32)
    full[indices] = room
    return full


def effective_resource_sensing_weights(
    simulation: Any,
    resource_affinity_q: np.ndarray,
    *,
    active: np.ndarray | None = None,
    storage_room_fraction: np.ndarray | None = None,
) -> np.ndarray:
    """Return fixed-budget channel weights for world-gradient aggregation."""

    full_room = _full_storage_room_fraction(
        simulation,
        active=active,
        storage_room_fraction=storage_room_fraction,
    )
    return resource_sensing_observation_weights_q(
        resource_affinity_q,
        simulation.cfg,
        storage_room_fraction=full_room,
    )


def effective_resource_sensing_radius(
    simulation: Any,
    resource_affinity_q: np.ndarray | None = None,
    *,
    active: np.ndarray | None = None,
    storage_room_fraction: np.ndarray | None = None,
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
    full_room = _full_storage_room_fraction(
        simulation,
        active=active,
        storage_room_fraction=storage_room_fraction,
    )
    channel_radii = resource_sensing_channel_radii(
        simulation.entities.genotype,
        simulation.cfg,
        resource_affinity_q=affinity,
        storage_room_fraction=full_room,
    )
    if channel_routed_resource_sensing_enabled(simulation.cfg):
        return channel_radii
    return channel_radii[:, 0]


def effective_resource_sensing_observation(
    simulation: Any,
    resource_affinity_q: np.ndarray,
    *,
    active: np.ndarray | None = None,
    storage_room_fraction: np.ndarray | None = None,
) -> tuple[np.ndarray, np.ndarray]:
    """Return fixed-budget gradient weights and matching world-facing radii."""

    return (
        effective_resource_sensing_weights(
            simulation,
            resource_affinity_q,
            active=active,
            storage_room_fraction=storage_room_fraction,
        ),
        effective_resource_sensing_radius(
            simulation,
            resource_affinity_q,
            active=active,
            storage_room_fraction=storage_room_fraction,
        ),
    )


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
    "effective_resource_sensing_observation",
    "effective_resource_sensing_radius",
    "effective_resource_sensing_weights",
    "record_resource_sensing_development_cost",
]
