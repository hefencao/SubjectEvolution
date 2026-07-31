"""Inherited spatial scale for role-free resource-gradient sensing.

The v1 capability applies one inherited radius to every resource channel.  The
v2 capability retains the same inherited reach capacity and costs, but routes
that reach to the entity's strongest inherited resource-affinity channel while
keeping the other channels at radius one.  The v3 capability keeps the same
fixed total extra-radius budget and distributes it across channels in proportion
to inherited resource affinity.  It therefore expands carrier capability
without creating free sensing range or naming ecological roles.
"""
from __future__ import annotations

from typing import Any

import numpy as np

from se.cfg import SimulationConfig

RESOURCE_SENSING_GENE_INDEX = 7
RESOURCE_SENSING_SCHEMA = "inherited-discrete-gradient-radius-v1"
RESOURCE_SENSING_CHANNEL_SCHEMA = "inherited-affinity-routed-gradient-radius-v2"
RESOURCE_SENSING_BUDGET_SCHEMA = "inherited-affinity-budgeted-gradient-radius-v3"
RESOURCE_CHANNELS = 4


def resource_sensing_enabled(cfg: SimulationConfig) -> bool:
    return cfg.entities.resource_sensing_schema in {
        RESOURCE_SENSING_SCHEMA,
        RESOURCE_SENSING_CHANNEL_SCHEMA,
        RESOURCE_SENSING_BUDGET_SCHEMA,
    }


def channel_routed_resource_sensing_enabled(cfg: SimulationConfig) -> bool:
    """Return whether the world-facing radius is channel-specific."""

    return cfg.entities.resource_sensing_schema in {
        RESOURCE_SENSING_CHANNEL_SCHEMA,
        RESOURCE_SENSING_BUDGET_SCHEMA,
    }


def budgeted_resource_sensing_enabled(cfg: SimulationConfig) -> bool:
    return cfg.entities.resource_sensing_schema == RESOURCE_SENSING_BUDGET_SCHEMA



def effective_resource_sensing_radius_levels(cfg: SimulationConfig) -> tuple[int, ...]:
    """Return world-facing radius levels allowed by the configured schema."""

    configured = tuple(int(value) for value in cfg.entities.resource_sensing_radius_levels)
    if budgeted_resource_sensing_enabled(cfg):
        return tuple(range(1, max(configured) + 1))
    return configured

def resource_sensing_radius(genotype: Any, cfg: SimulationConfig) -> np.ndarray:
    """Return one inherited reach-capacity radius per entity."""

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


def resource_sensing_channel_radii(
    genotype: Any,
    cfg: SimulationConfig,
    *,
    resource_affinity_q: Any | None = None,
) -> np.ndarray:
    """Return the effective inherited radius for each resource channel.

    V1 repeats the same capacity across all channels.  V2 assigns the extended
    reach to exactly one strongest-affinity channel and leaves all other
    channels at radius one.  ``argmax`` provides a deterministic lowest-index
    tie break.  The capacity gene and all registered costs remain unchanged.
    """

    base = resource_sensing_radius(genotype, cfg)
    rows = int(base.shape[0])
    if not channel_routed_resource_sensing_enabled(cfg):
        return np.repeat(base[:, None], RESOURCE_CHANNELS, axis=1)
    if resource_affinity_q is None:
        raise ValueError("channel-routed resource sensing requires resource affinity")
    affinity = np.asarray(resource_affinity_q, dtype=np.int32)
    if affinity.shape != (rows, RESOURCE_CHANNELS):
        raise ValueError("resource affinity must be shaped [N, 4]")
    if not budgeted_resource_sensing_enabled(cfg):
        result = np.ones((rows, RESOURCE_CHANNELS), dtype=np.int16)
        preferred = np.argmax(affinity, axis=1)
        result[np.arange(rows), preferred] = base
        return result

    # The carrier owns exactly ``base - 1`` units of extra radius beyond the
    # four local radius-one channels.  Hamilton apportionment assigns that
    # integer budget in proportion to inherited affinity.  The sum of effective
    # extra radii is therefore invariant across v2 and v3 for a given genotype,
    # while v3 can preserve information from several resource channels.
    weights = affinity.astype(np.int64, copy=False)
    totals = weights.sum(axis=1, dtype=np.int64)
    if np.any(totals <= 0) or np.any(weights < 0):
        raise ValueError("resource affinity must contain a positive non-negative budget")
    budget = np.maximum(base.astype(np.int64) - 1, 0)
    numerator = weights * budget[:, None]
    allocation = numerator // totals[:, None]
    remainder = numerator % totals[:, None]
    missing = budget - allocation.sum(axis=1, dtype=np.int64)
    row_indices = np.arange(rows)
    for _ in range(RESOURCE_CHANNELS - 1):
        selected = np.argmax(remainder, axis=1)
        active = missing > 0
        if not np.any(active):
            break
        active_rows = row_indices[active]
        active_selected = selected[active]
        allocation[active_rows, active_selected] += 1
        remainder[active_rows, active_selected] = -1
        missing[active] -= 1
    if np.any(missing != 0):
        raise RuntimeError("resource-sensing radius budget apportionment did not close")
    return (allocation + 1).astype(np.int16)


def resource_sensing_energy(
    genotype: Any,
    cfg: SimulationConfig,
    *,
    development: bool = False,
    use: bool = False,
) -> np.ndarray:
    """Return per-entity energy charged for inherited reach capacity."""

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
    *,
    resource_affinity_q: Any | None = None,
) -> dict[str, Any]:
    active = np.flatnonzero(np.asarray(alive, dtype=bool)).astype(np.int32)
    if active.size == 0:
        return {
            "resource_sensing_schema": cfg.entities.resource_sensing_schema,
            "resource_sensing_radius_mean": 1.0,
            "resource_sensing_radius_std": 0.0,
            "resource_sensing_radius_min": 1,
            "resource_sensing_radius_max": 1,
            "resource_sensing_channel_radius_mean": 1.0,
            "resource_sensing_channel_radius_means": [1.0] * RESOURCE_CHANNELS,
            "resource_sensing_extended_channel_fractions": [0.0] * RESOURCE_CHANNELS,
            "resource_sensing_extended_channel_count_mean": 0.0,
            "resource_sensing_allocated_extra_radius_mean": 0.0,
        }
    values = np.asarray(genotype, dtype=np.float32)[active]
    affinity = None
    if resource_affinity_q is not None:
        affinity = np.asarray(resource_affinity_q, dtype=np.int32)[active]
    radius = resource_sensing_radius(values, cfg).astype(np.float64)
    channel_radii = resource_sensing_channel_radii(
        values, cfg, resource_affinity_q=affinity
    ).astype(np.float64)
    return {
        "resource_sensing_schema": cfg.entities.resource_sensing_schema,
        "resource_sensing_radius_mean": float(radius.mean()),
        "resource_sensing_radius_std": float(radius.std()),
        "resource_sensing_radius_min": int(radius.min()),
        "resource_sensing_radius_max": int(radius.max()),
        "resource_sensing_channel_radius_mean": float(channel_radii.mean()),
        "resource_sensing_channel_radius_means": channel_radii.mean(axis=0).tolist(),
        "resource_sensing_extended_channel_fractions": (
            channel_radii > 1.0
        ).mean(axis=0).tolist(),
        "resource_sensing_extended_channel_count_mean": float(
            (channel_radii > 1.0).sum(axis=1).mean()
        ),
        "resource_sensing_allocated_extra_radius_mean": float(
            np.maximum(channel_radii - 1.0, 0.0).sum(axis=1).mean()
        ),
    }


__all__ = [
    "RESOURCE_SENSING_BUDGET_SCHEMA",
    "RESOURCE_SENSING_CHANNEL_SCHEMA",
    "RESOURCE_SENSING_GENE_INDEX",
    "RESOURCE_SENSING_SCHEMA",
    "budgeted_resource_sensing_enabled",
    "channel_routed_resource_sensing_enabled",
    "effective_resource_sensing_radius_levels",
    "resource_sensing_channel_radii",
    "resource_sensing_diagnostics",
    "resource_sensing_enabled",
    "resource_sensing_energy",
    "resource_sensing_radius",
]
