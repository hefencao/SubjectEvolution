"""Inherited spatial scale for role-free resource-gradient sensing.

V1 applies one inherited radius to every resource channel. V2 routes that reach
to the strongest inherited affinity channel. V3 preserves the same inherited
capacity and costs while apportioning the fixed extra-radius budget across all
channels by inherited affinity. V4 keeps that budget and cost contract, but
expresses it through current conservative storage demand: affinity supplies the
heritable channel bias, while open store room gates which channels currently
receive non-local observation capacity.
"""
from __future__ import annotations

from typing import Any

import numpy as np

from se.cfg import SimulationConfig

RESOURCE_SENSING_GENE_INDEX = 7
RESOURCE_SENSING_SCHEMA = "inherited-discrete-gradient-radius-v1"
RESOURCE_SENSING_CHANNEL_SCHEMA = "inherited-affinity-routed-gradient-radius-v2"
RESOURCE_SENSING_BUDGET_SCHEMA = "inherited-affinity-budgeted-gradient-radius-v3"
RESOURCE_SENSING_DEMAND_SCHEMA = (
    "inherited-demand-gated-affinity-budgeted-gradient-radius-v4"
)
RESOURCE_CHANNELS = 4
DEMAND_QUANTIZATION_SCALE = 4096


def resource_sensing_enabled(cfg: SimulationConfig) -> bool:
    return cfg.entities.resource_sensing_schema in {
        RESOURCE_SENSING_SCHEMA,
        RESOURCE_SENSING_CHANNEL_SCHEMA,
        RESOURCE_SENSING_BUDGET_SCHEMA,
        RESOURCE_SENSING_DEMAND_SCHEMA,
    }


def channel_routed_resource_sensing_enabled(cfg: SimulationConfig) -> bool:
    """Return whether the world-facing radius is channel-specific."""

    return cfg.entities.resource_sensing_schema in {
        RESOURCE_SENSING_CHANNEL_SCHEMA,
        RESOURCE_SENSING_BUDGET_SCHEMA,
        RESOURCE_SENSING_DEMAND_SCHEMA,
    }


def budgeted_resource_sensing_enabled(cfg: SimulationConfig) -> bool:
    return cfg.entities.resource_sensing_schema in {
        RESOURCE_SENSING_BUDGET_SCHEMA,
        RESOURCE_SENSING_DEMAND_SCHEMA,
    }


def demand_gated_resource_sensing_enabled(cfg: SimulationConfig) -> bool:
    return cfg.entities.resource_sensing_schema == RESOURCE_SENSING_DEMAND_SCHEMA


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


def _hamilton_apportion(weights: np.ndarray, budget: np.ndarray) -> np.ndarray:
    """Deterministically apportion each integer row budget across four columns."""

    values = np.asarray(weights, dtype=np.int64)
    target = np.asarray(budget, dtype=np.int64)
    if values.ndim != 2 or values.shape[1] != RESOURCE_CHANNELS:
        raise ValueError("apportionment weights must be shaped [N, 4]")
    if target.shape != (values.shape[0],):
        raise ValueError("apportionment budget must be shaped [N]")
    totals = values.sum(axis=1, dtype=np.int64)
    if np.any(totals <= 0) or np.any(values < 0) or np.any(target < 0):
        raise ValueError("apportionment requires positive weights and non-negative budgets")
    numerator = values * target[:, None]
    allocation = numerator // totals[:, None]
    remainder = numerator % totals[:, None]
    missing = target - allocation.sum(axis=1, dtype=np.int64)
    rows = np.arange(values.shape[0])
    for _ in range(RESOURCE_CHANNELS - 1):
        selected = np.argmax(remainder, axis=1)
        active = missing > 0
        if not np.any(active):
            break
        active_rows = rows[active]
        active_selected = selected[active]
        allocation[active_rows, active_selected] += 1
        remainder[active_rows, active_selected] = -1
        missing[active] -= 1
    if np.any(missing != 0):
        raise RuntimeError("integer apportionment did not close")
    return allocation


def resource_sensing_observation_weights_q(
    resource_affinity_q: Any,
    cfg: SimulationConfig,
    *,
    storage_room_fraction: Any | None = None,
) -> np.ndarray:
    """Return fixed-budget channel weights used by both range and gradient.

    V1--V3 return inherited affinity unchanged. V4 multiplies affinity by a
    deterministic quantization of current open storage room, then re-apportions
    the original affinity total. Signal scale therefore remains invariant while
    channels with no current storage demand receive no weight. If every store is
    full, inherited affinity is used as a deterministic fallback; the policy can
    still choose not to move because its local resource coordinate is room-gated.
    """

    affinity = np.asarray(resource_affinity_q, dtype=np.int64)
    if affinity.ndim != 2 or affinity.shape[1] != RESOURCE_CHANNELS:
        raise ValueError("resource affinity must be shaped [N, 4]")
    totals = affinity.sum(axis=1, dtype=np.int64)
    if np.any(affinity < 0) or np.any(totals <= 0):
        raise ValueError("resource affinity must contain a positive non-negative budget")
    if not demand_gated_resource_sensing_enabled(cfg):
        return affinity.astype(np.int32, copy=False)
    if storage_room_fraction is None:
        raise ValueError("demand-gated resource sensing requires storage room fractions")
    room = np.asarray(storage_room_fraction, dtype=np.float64)
    if room.shape != affinity.shape:
        raise ValueError("storage room fraction must be shaped [N, 4]")
    if not np.all(np.isfinite(room)) or np.any(room < 0.0):
        raise ValueError("storage room fraction must be finite and non-negative")
    demand_q = np.floor(
        np.clip(room, 0.0, 1.0) * DEMAND_QUANTIZATION_SCALE + 0.5
    ).astype(np.int64)
    weighted = affinity * demand_q
    empty = weighted.sum(axis=1, dtype=np.int64) <= 0
    if np.any(empty):
        weighted[empty] = affinity[empty]
    normalized = _hamilton_apportion(weighted, totals)
    return normalized.astype(np.int32)


def resource_sensing_channel_radii(
    genotype: Any,
    cfg: SimulationConfig,
    *,
    resource_affinity_q: Any | None = None,
    storage_room_fraction: Any | None = None,
) -> np.ndarray:
    """Return inherited/expressed radius for each resource channel."""

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

    weights = resource_sensing_observation_weights_q(
        affinity,
        cfg,
        storage_room_fraction=storage_room_fraction,
    ).astype(np.int64, copy=False)
    budget = np.maximum(base.astype(np.int64) - 1, 0)
    allocation = _hamilton_apportion(weights, budget)
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
    storage_room_fraction: Any | None = None,
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
            "resource_sensing_open_storage_channel_count_mean": 0.0,
            "resource_sensing_demand_fallback_fraction": 0.0,
        }
    values = np.asarray(genotype, dtype=np.float32)[active]
    affinity = None
    if resource_affinity_q is not None:
        affinity = np.asarray(resource_affinity_q, dtype=np.int32)[active]
    room = None
    if storage_room_fraction is not None:
        raw_room = np.asarray(storage_room_fraction, dtype=np.float32)
        room = raw_room if raw_room.shape[0] == active.size else raw_room[active]
    radius = resource_sensing_radius(values, cfg).astype(np.float64)
    channel_radii = resource_sensing_channel_radii(
        values,
        cfg,
        resource_affinity_q=affinity,
        storage_room_fraction=room,
    ).astype(np.float64)
    open_count = 0.0 if room is None else float((room > 0.0).sum(axis=1).mean())
    fallback = (
        0.0
        if room is None or not demand_gated_resource_sensing_enabled(cfg)
        else float((room.sum(axis=1) <= 0.0).mean())
    )
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
        "resource_sensing_open_storage_channel_count_mean": open_count,
        "resource_sensing_demand_fallback_fraction": fallback,
    }


__all__ = [
    "DEMAND_QUANTIZATION_SCALE",
    "RESOURCE_SENSING_BUDGET_SCHEMA",
    "RESOURCE_SENSING_CHANNEL_SCHEMA",
    "RESOURCE_SENSING_DEMAND_SCHEMA",
    "RESOURCE_SENSING_GENE_INDEX",
    "RESOURCE_SENSING_SCHEMA",
    "budgeted_resource_sensing_enabled",
    "channel_routed_resource_sensing_enabled",
    "demand_gated_resource_sensing_enabled",
    "effective_resource_sensing_radius_levels",
    "resource_sensing_channel_radii",
    "resource_sensing_diagnostics",
    "resource_sensing_enabled",
    "resource_sensing_energy",
    "resource_sensing_observation_weights_q",
    "resource_sensing_radius",
]
