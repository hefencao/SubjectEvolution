"""Role-neutral mobility burden from carried raw resources.

The mechanism is opt-in and contains no role, group, lineage or gene-specific
reward.  It only turns already-conserved internal raw stores into a physical
movement trade-off.
"""
from __future__ import annotations

from typing import Any

import numpy as np

from se.cfg import SimulationConfig
from se.differentiation.physiology import resource_metabolism_enabled
from .resource_metabolism import resource_store_capacity_and_room

LOAD_SCHEMA = "raw-store-mobility-burden-v1"


def resource_load_enabled(cfg: SimulationConfig) -> bool:
    return cfg.entities.resource_load_schema == LOAD_SCHEMA


def raw_resource_load_fraction(
    entities: Any,
    rows: np.ndarray,
    cfg: SimulationConfig,
    *,
    genotype: np.ndarray,
    gene_start: int,
    neutralize_store_allocation: bool = False,
) -> np.ndarray:
    """Return total carried raw material divided by total effective capacity."""

    indices = np.asarray(rows, dtype=np.int32)
    if indices.size == 0:
        return np.zeros(0, dtype=np.float32)
    if not resource_load_enabled(cfg) or not resource_metabolism_enabled(cfg):
        return np.zeros(indices.size, dtype=np.float32)
    capacity, _ = resource_store_capacity_and_room(
        entities,
        indices,
        cfg,
        genotype=np.asarray(genotype, dtype=np.float32),
        gene_start=gene_start,
        neutralize_store_allocation=neutralize_store_allocation,
    )
    carried = np.asarray(entities.resource_store[indices], dtype=np.float64)
    fraction = carried.sum(axis=1) / np.maximum(capacity.sum(axis=1), 1.0e-12)
    return np.clip(fraction, 0.0, 1.0).astype(np.float32)


def load_speed_multiplier(load_fraction: np.ndarray, cfg: SimulationConfig) -> np.ndarray:
    values = np.asarray(load_fraction, dtype=np.float32)
    if not resource_load_enabled(cfg):
        return np.ones(values.shape, dtype=np.float32)
    penalty = float(cfg.entities.resource_load_speed_penalty_fraction)
    return np.clip(1.0 - penalty * values, 0.05, 1.0).astype(np.float32)


def load_movement_energy(
    moved: np.ndarray,
    load_fraction: np.ndarray,
    cfg: SimulationConfig,
) -> np.ndarray:
    moving = np.asarray(moved, dtype=bool)
    load = np.asarray(load_fraction, dtype=np.float64)
    if moving.shape != load.shape:
        raise ValueError("movement and load vectors must have the same shape")
    if not resource_load_enabled(cfg):
        return np.zeros(load.shape, dtype=np.float64)
    return (
        moving.astype(np.float64)
        * load
        * float(cfg.entities.movement_cost)
        * float(cfg.entities.resource_load_movement_energy_fraction)
    )


__all__ = [
    "LOAD_SCHEMA",
    "load_movement_energy",
    "load_speed_multiplier",
    "raw_resource_load_fraction",
    "resource_load_enabled",
]
