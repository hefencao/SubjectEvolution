"""Conserved resource buffering and delayed conversion for physiology resource-v4.

External resource channels are first assimilated into bounded internal stores.
Inherited storage and conversion capacities then determine how much of each raw
channel can be retained and processed per tick.  The existing versioned
resource-effect matrix remains the world-level conversion vocabulary; this
module only delays and capacity-limits its application.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np

from se.cfg import SimulationConfig
from se.differentiation.physiology import (
    physiology_phenotype,
    resource_metabolism_enabled,
    storage_constrained_intake_enabled,
    external_resource_recycling_enabled,
)
from se.env.niches import AFFINITY_SCALE
from se.env.recycling import deposit_resource_residue

RESOURCE_CHANNELS = 4
BODY_OUTCOMES = 5


@dataclass(frozen=True)
class ResourceMetabolismStep:
    stored: np.ndarray
    overflow: np.ndarray
    converted: np.ndarray
    decayed: np.ndarray
    body_realized: np.ndarray
    decayed_by_entity: np.ndarray

    @classmethod
    def empty(cls) -> "ResourceMetabolismStep":
        return cls(
            stored=np.zeros(RESOURCE_CHANNELS, dtype=np.float64),
            overflow=np.zeros(RESOURCE_CHANNELS, dtype=np.float64),
            converted=np.zeros(RESOURCE_CHANNELS, dtype=np.float64),
            decayed=np.zeros(RESOURCE_CHANNELS, dtype=np.float64),
            body_realized=np.zeros(BODY_OUTCOMES, dtype=np.float64),
            decayed_by_entity=np.zeros((0, RESOURCE_CHANNELS), dtype=np.float64),
        )


def _check_non_negative_finite(name: str, values: np.ndarray) -> None:
    array = np.asarray(values, dtype=np.float64)
    if not np.all(np.isfinite(array)) or np.any(array < -1.0e-12):
        raise RuntimeError(f"resource metabolism {name} must be finite and non-negative")




def resource_store_capacity_and_room(
    entities: Any,
    rows: np.ndarray,
    cfg: SimulationConfig,
    *,
    genotype: np.ndarray,
    gene_start: int,
) -> tuple[np.ndarray, np.ndarray]:
    """Return inherited store capacity and current non-negative room."""

    indices = np.asarray(rows, dtype=np.int32)
    if indices.size == 0 or not resource_metabolism_enabled(cfg):
        empty = np.zeros((indices.size, RESOURCE_CHANNELS), dtype=np.float64)
        return empty, empty.copy()
    phenotype = physiology_phenotype(genotype, cfg, gene_start=gene_start)
    capacity = np.asarray(phenotype.resource_store_capacity, dtype=np.float64)
    current = np.asarray(entities.resource_store[indices], dtype=np.float64)
    room = np.maximum(capacity - current, 0.0)
    _check_non_negative_finite("store capacity", capacity)
    _check_non_negative_finite("store room", room)
    return capacity, room


def raw_harvest_room(
    entities: Any,
    rows: np.ndarray,
    cfg: SimulationConfig,
    *,
    genotype: np.ndarray,
    gene_start: int,
    resource_affinity_q: np.ndarray,
) -> np.ndarray | None:
    """Return maximum raw extraction that can be assimilated without overflow.

    Affinity scales raw extraction before storage.  The v5 intake contract caps
    the pre-harvest request in raw units, so the later assimilated amount fits
    the inherited store exactly instead of removing unusable material from the
    environment.  Legacy resource-v4 returns ``None`` and preserves archived
    post-harvest overflow semantics.
    """

    if not storage_constrained_intake_enabled(cfg):
        return None
    indices = np.asarray(rows, dtype=np.int32)
    affinity = np.asarray(resource_affinity_q, dtype=np.int64)
    if affinity.shape != (indices.size, RESOURCE_CHANNELS):
        raise ValueError("resource affinity must align with storage-room rows")
    _, room = resource_store_capacity_and_room(
        entities,
        indices,
        cfg,
        genotype=genotype,
        gene_start=gene_start,
    )
    raw_room = room * float(AFFINITY_SCALE) / np.maximum(affinity, 1)
    _check_non_negative_finite("raw harvest room", raw_room)
    return raw_room.astype(np.float32)


def storage_room_fraction(
    entities: Any,
    rows: np.ndarray,
    cfg: SimulationConfig,
    *,
    genotype: np.ndarray,
    gene_start: int,
) -> np.ndarray | None:
    """Return per-channel room fraction for the v5 policy resource view."""

    if not storage_constrained_intake_enabled(cfg):
        return None
    capacity, room = resource_store_capacity_and_room(
        entities, rows, cfg, genotype=genotype, gene_start=gene_start
    )
    fraction = np.clip(room / np.maximum(capacity, 1.0e-12), 0.0, 1.0)
    fraction = np.where(room <= np.maximum(capacity, 1.0) * 1.0e-7, 0.0, fraction)
    return fraction.astype(np.float32)


def store_assimilated_resources(
    entities: Any,
    rows: np.ndarray,
    assimilated: np.ndarray,
    cfg: SimulationConfig,
    *,
    genotype: np.ndarray,
    gene_start: int,
) -> tuple[np.ndarray, np.ndarray]:
    """Place assimilated raw channels into inherited bounded stores."""

    indices = np.asarray(rows, dtype=np.int32)
    values = np.asarray(assimilated, dtype=np.float64)
    if indices.size == 0:
        return (
            np.zeros((0, RESOURCE_CHANNELS), dtype=np.float64),
            np.zeros((0, RESOURCE_CHANNELS), dtype=np.float64),
        )
    if values.shape != (indices.size, RESOURCE_CHANNELS):
        raise ValueError("assimilated resources must be shaped [N, 4]")
    if not resource_metabolism_enabled(cfg):
        raise ValueError("resource buffering requires physiology resource-v4")
    capacity, room = resource_store_capacity_and_room(
        entities, indices, cfg, genotype=genotype, gene_start=gene_start
    )
    current = np.asarray(entities.resource_store[indices], dtype=np.float64)
    stored = np.minimum(np.maximum(values, 0.0), room)
    overflow = np.maximum(values - stored, 0.0)
    entities.resource_store[indices] = (current + stored).astype(np.float32)
    _check_non_negative_finite("stored flow", stored)
    _check_non_negative_finite("overflow flow", overflow)
    if storage_constrained_intake_enabled(cfg) and np.any(overflow > 2.0e-6):
        raise RuntimeError("storage-constrained intake produced post-harvest overflow")
    return stored, overflow


def settle_resource_metabolism(
    entities: Any,
    active: np.ndarray,
    cfg: SimulationConfig,
    *,
    genotype: np.ndarray,
    gene_start: int,
) -> ResourceMetabolismStep:
    """Convert bounded raw stores and decay the unprocessed remainder."""

    rows = np.asarray(active, dtype=np.int32)
    if rows.size == 0 or not resource_metabolism_enabled(cfg):
        return ResourceMetabolismStep.empty()
    phenotype = physiology_phenotype(genotype, cfg, gene_start=gene_start)
    store_before = np.asarray(entities.resource_store[rows], dtype=np.float64)
    conversion_capacity = np.asarray(
        phenotype.resource_conversion_capacity, dtype=np.float64
    )
    converted = np.minimum(np.maximum(store_before, 0.0), conversion_capacity)
    after_conversion = np.maximum(store_before - converted, 0.0)
    decay_rate = np.asarray(
        cfg.physiology.resource_store_decay_per_tick, dtype=np.float64
    )[None, :]
    decayed = np.minimum(after_conversion, after_conversion * decay_rate)
    store_after = np.maximum(after_conversion - decayed, 0.0)
    entities.resource_store[rows] = store_after.astype(np.float32)

    effects = np.asarray(cfg.environment.resource_effect_matrix, dtype=np.float64)
    potential = converted @ effects
    body_before = np.column_stack(
        (
            np.asarray(entities.energy[rows], dtype=np.float64),
            np.asarray(entities.integrity[rows], dtype=np.float64),
            np.asarray(entities.material[rows], dtype=np.float64),
            np.asarray(entities.information_store[rows], dtype=np.float64),
            np.asarray(entities.fertility[rows], dtype=np.float64),
        )
    )
    body_after = body_before.copy()
    body_after[:, 0] = np.minimum(
        body_before[:, 0] + potential[:, 0], float(cfg.entities.max_energy)
    )
    body_after[:, 1] = np.minimum(body_before[:, 1] + potential[:, 1], 1.0)
    body_after[:, 2] = np.maximum(body_before[:, 2] + potential[:, 2], 0.0)
    body_after[:, 3] = np.minimum(body_before[:, 3] + potential[:, 3], 3.0)
    body_after[:, 4] = np.minimum(body_before[:, 4] + potential[:, 4], 3.0)
    realized = np.maximum(body_after - body_before, 0.0)

    entities.energy[rows] = body_after[:, 0].astype(np.float32)
    entities.integrity[rows] = body_after[:, 1].astype(np.float32)
    entities.material[rows] = body_after[:, 2].astype(np.float32)
    entities.information_store[rows] = body_after[:, 3].astype(np.float32)
    entities.fertility[rows] = body_after[:, 4].astype(np.float32)
    entities.harvested_energy_total[rows] += realized[:, 0].astype(np.float32)

    for name, value in (
        ("converted flow", converted),
        ("decay flow", decayed),
        ("store state", store_after),
        ("realized body flow", realized),
    ):
        _check_non_negative_finite(name, value)
    ledger_error = store_before - converted - decayed - store_after
    if not np.allclose(ledger_error, 0.0, atol=2.0e-7, rtol=0.0):
        raise RuntimeError("resource store ledger failed to close")
    return ResourceMetabolismStep(
        stored=np.zeros(RESOURCE_CHANNELS, dtype=np.float64),
        overflow=np.zeros(RESOURCE_CHANNELS, dtype=np.float64),
        converted=converted.sum(axis=0, dtype=np.float64),
        decayed=decayed.sum(axis=0, dtype=np.float64),
        body_realized=realized.sum(axis=0, dtype=np.float64),
        decayed_by_entity=decayed,
    )


def resource_metabolism_diagnostics(
    entities: Any,
    cfg: SimulationConfig,
    *,
    gene_start: int,
) -> dict[str, object]:
    active = np.flatnonzero(np.asarray(entities.alive, dtype=bool)).astype(np.int32)
    if active.size == 0 or not resource_metabolism_enabled(cfg):
        return {
            "resource_metabolism_schema": cfg.physiology.schema,
            "resource_store_mean": [0.0] * RESOURCE_CHANNELS,
            "resource_store_std": [0.0] * RESOURCE_CHANNELS,
            "resource_store_total": [0.0] * RESOURCE_CHANNELS,
            "resource_store_occupancy_mean": [0.0] * RESOURCE_CHANNELS,
            "resource_store_capacity_mean": [0.0] * RESOURCE_CHANNELS,
            "resource_conversion_capacity_mean": [0.0] * RESOURCE_CHANNELS,
            "resource_metabolism_genetic_effective_dimensions": 0.0,
        }
    phenotype = physiology_phenotype(
        entities.genotype[active], cfg, gene_start=gene_start
    )
    stores = np.asarray(entities.resource_store[active], dtype=np.float64)
    capacity = np.asarray(phenotype.resource_store_capacity, dtype=np.float64)
    conversion = np.asarray(phenotype.resource_conversion_capacity, dtype=np.float64)
    normalized = np.column_stack(
        (
            capacity
            / np.maximum(
                np.asarray(cfg.physiology.resource_store_base_capacity, dtype=np.float64)[None, :],
                1.0e-12,
            ),
            conversion
            / np.maximum(
                np.asarray(cfg.physiology.resource_conversion_per_tick, dtype=np.float64)[None, :],
                1.0e-12,
            ),
        )
    )
    centered = normalized - normalized.mean(axis=0, keepdims=True)
    if active.size > 1 and np.any(centered):
        singular = np.linalg.svd(centered, compute_uv=False)
        spectrum = singular * singular
        effective = float(
            spectrum.sum() ** 2 / max(float(np.dot(spectrum, spectrum)), 1.0e-30)
        )
    else:
        effective = 0.0
    return {
        "resource_metabolism_schema": cfg.physiology.schema,
        "resource_store_mean": stores.mean(axis=0).tolist(),
        "resource_store_std": stores.std(axis=0).tolist(),
        "resource_store_total": stores.sum(axis=0).tolist(),
        "resource_store_occupancy_mean": (
            stores / np.maximum(capacity, 1.0e-12)
        ).mean(axis=0).tolist(),
        "resource_store_capacity_mean": capacity.mean(axis=0).tolist(),
        "resource_conversion_capacity_mean": conversion.mean(axis=0).tolist(),
        "resource_metabolism_genetic_effective_dimensions": effective,
    }


def initialize_resource_metabolism_state(simulation: Any) -> None:
    """Initialize cumulative D3-A ledgers without touching legacy schemas."""
    simulation.total_resource_stored = np.zeros(RESOURCE_CHANNELS, dtype=np.float64)
    simulation.total_resource_store_overflow = np.zeros(RESOURCE_CHANNELS, dtype=np.float64)
    simulation.total_resource_intake_capacity_rejected = np.zeros(RESOURCE_CHANNELS, dtype=np.float64)
    simulation.total_resource_converted = np.zeros(RESOURCE_CHANNELS, dtype=np.float64)
    simulation.total_resource_store_decay = np.zeros(RESOURCE_CHANNELS, dtype=np.float64)
    simulation.total_resource_store_death_loss = np.zeros(RESOURCE_CHANNELS, dtype=np.float64)
    simulation.total_resource_body_realized = np.zeros(BODY_OUTCOMES, dtype=np.float64)
    if external_resource_recycling_enabled(simulation.cfg):
        simulation.total_resource_residue_deposited = np.zeros(RESOURCE_CHANNELS, dtype=np.float64)
        simulation.total_resource_residue_released = np.zeros(RESOURCE_CHANNELS, dtype=np.float64)
        simulation.pending_resource_residue_cells = np.zeros(0, dtype=np.int32)
        simulation.pending_resource_residue_amounts = np.zeros((0, RESOURCE_CHANNELS), dtype=np.float32)


def settle_resource_metabolism_before_step(simulation: Any, stats: Any) -> None:
    """Process stores before observation so current actions cannot receive credit."""
    if not resource_metabolism_enabled(simulation.cfg):
        return
    rows = np.flatnonzero(simulation.entities.alive).astype(np.int32)
    step = settle_resource_metabolism(
        simulation.entities,
        rows,
        simulation.cfg,
        genotype=simulation.entities.genotype[rows],
        gene_start=simulation.policy.physiology_gene_start(simulation.cfg),
    )
    stats.resource_converted = step.converted
    stats.resource_store_decay = step.decayed
    stats.resource_body_realized = step.body_realized
    simulation.total_resource_converted += step.converted
    simulation.total_resource_store_decay += step.decayed
    simulation.total_resource_body_realized += step.body_realized
    if external_resource_recycling_enabled(simulation.cfg) and rows.size:
        cells = np.asarray(
            simulation.spatial.cell_ids(
                simulation.entities.x[rows], simulation.entities.y[rows]
            ),
            dtype=np.int32,
        )
        positive = np.any(step.decayed_by_entity > 0.0, axis=1)
        simulation.pending_resource_residue_cells = cells[positive]
        simulation.pending_resource_residue_amounts = step.decayed_by_entity[positive].astype(np.float32)
    stats.harvested_energy = float(step.body_realized[0])
    if simulation.gpu_runtime is not None and rows.size:
        # Delayed conversion mutates authoritative host body state before GPU
        # observation construction.  Advance the version and refresh the mirror
        # so strict-reference and hybrid GPU paths observe the same state.
        simulation.entity_device_version += 1
        simulation.gpu_runtime.sync_entity_from_host(
            simulation.entities,
            simulation.social,
            simulation.entity_device_version,
        )


def commit_assimilated_harvest(
    simulation: Any,
    harvesters: np.ndarray,
    assimilated: np.ndarray,
    stats: Any,
) -> None:
    """Store current harvest for later conversion and update cumulative ledgers."""
    stored, overflow = store_assimilated_resources(
        simulation.entities,
        harvesters,
        assimilated,
        simulation.cfg,
        genotype=simulation.entities.genotype[harvesters],
        gene_start=simulation.policy.physiology_gene_start(simulation.cfg),
    )
    stats.resource_stored = stored.sum(axis=0, dtype=np.float64)
    stats.resource_store_overflow = overflow.sum(axis=0, dtype=np.float64)
    simulation.total_resource_stored += stats.resource_stored
    simulation.total_resource_store_overflow += stats.resource_store_overflow



def record_resource_recycling_after_environment_update(simulation: Any, stats: Any) -> None:
    """Record released residue, then deposit current-tick decay for next tick."""
    if not external_resource_recycling_enabled(simulation.cfg):
        return
    environment = (
        simulation.gpu_runtime.environment
        if simulation.gpu_runtime is not None
        else simulation.environment
    )
    released_raw = environment.last_resource_residue_released
    if hasattr(environment, "backend"):
        released = np.asarray(environment.backend.to_numpy(released_raw), dtype=np.float64)
    else:
        released = np.asarray(released_raw, dtype=np.float64)
    stats.resource_residue_released = released
    simulation.total_resource_residue_released += released
    flush_pending_resource_residue(simulation, stats)

def flush_pending_resource_residue(simulation: Any, stats: Any) -> None:
    """Deposit current-tick store decay only after the environment update."""
    if not external_resource_recycling_enabled(simulation.cfg):
        return
    cells = simulation.pending_resource_residue_cells
    amounts = simulation.pending_resource_residue_amounts
    if cells.size:
        deposited = (
            simulation.gpu_runtime.deposit_resource_residue(cells, amounts)
            if simulation.gpu_runtime is not None
            else deposit_resource_residue(simulation.environment, cells, amounts)
        )
        stats.resource_residue_deposited += deposited
        simulation.total_resource_residue_deposited += deposited
    simulation.pending_resource_residue_cells = np.zeros(0, dtype=np.int32)
    simulation.pending_resource_residue_amounts = np.zeros((0, RESOURCE_CHANNELS), dtype=np.float32)


def record_resource_store_death_loss(simulation: Any, dead: np.ndarray, stats: Any) -> None:
    """Account for and optionally externalize raw stores carried at death."""
    if not resource_metabolism_enabled(simulation.cfg) or dead.size == 0:
        return
    amounts = np.asarray(simulation.entities.resource_store[dead], dtype=np.float64)
    loss = amounts.sum(axis=0)
    stats.resource_store_death_loss = loss
    simulation.total_resource_store_death_loss += loss
    if external_resource_recycling_enabled(simulation.cfg):
        cells = np.asarray(
            simulation.spatial.cell_ids(
                simulation.entities.x[dead], simulation.entities.y[dead]
            ),
            dtype=np.int32,
        )
        deposited = (
            simulation.gpu_runtime.deposit_resource_residue(cells, amounts.astype(np.float32))
            if simulation.gpu_runtime is not None
            else deposit_resource_residue(simulation.environment, cells, amounts)
        )
        stats.resource_residue_deposited += deposited
        simulation.total_resource_residue_deposited += deposited



__all__ = [
    "ResourceMetabolismStep",
    "commit_assimilated_harvest",
    "flush_pending_resource_residue",
    "initialize_resource_metabolism_state",
    "raw_harvest_room",
    "record_resource_recycling_after_environment_update",
    "record_resource_store_death_loss",
    "resource_store_capacity_and_room",
    "resource_metabolism_diagnostics",
    "settle_resource_metabolism",
    "settle_resource_metabolism_before_step",
    "storage_room_fraction",
    "store_assimilated_resources",
]
