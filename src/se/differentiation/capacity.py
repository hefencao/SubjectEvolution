"""Inherited elastic capacities over fixed physical tensor limits.

D1 does not introduce predefined ecological roles.  Four independent genes
control how much of already-existing mechanisms an entity can use:
working-memory dimensions, knowledge bytes, relationship slots, and incoming
knowledge-attention slots.  Arrays retain fixed maxima for deterministic CPU/GPU
layouts; effective capacities are integer masks derived from inherited genes.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np

from ..backend import backend_from_array
from ..cfg import DifferentiationConfig, SimulationConfig

CAPACITY_SCHEMA = "inherited-elastic-capacities-v1"
CAPACITY_GENE_COUNT = 4
CAPACITY_TRAIT_NAMES = (
    "working_memory_dimensions",
    "knowledge_capacity_bytes",
    "relation_slots",
    "knowledge_attention_slots",
)


def capacity_schema_enabled(cfg: SimulationConfig) -> bool:
    return bool(
        cfg.differentiation.enabled
        and cfg.differentiation.schema == CAPACITY_SCHEMA
    )


def capacity_gene_count(cfg: SimulationConfig) -> int:
    return CAPACITY_GENE_COUNT if capacity_schema_enabled(cfg) else 0


def _map_gene(
    raw: Any,
    *,
    minimum: int,
    maximum: int,
    quantum: int = 1,
) -> Any:
    if minimum < 0 or maximum < minimum or quantum <= 0:
        raise ValueError("invalid elastic-capacity bounds")
    xp = backend_from_array(raw).xp
    clipped = xp.clip(raw, -1.0, 1.0)
    normalized = (clipped + xp.float32(1.0)) * xp.float32(0.5)
    steps = (maximum - minimum) // quantum
    if steps <= 0:
        return xp.full(raw.shape, minimum, dtype=xp.int32)
    index = xp.floor(normalized * xp.float32(steps + 1)).astype(xp.int32)
    index = xp.clip(index, 0, steps)
    return (minimum + index * quantum).astype(xp.int32, copy=False)


@dataclass(frozen=True)
class CapacityPhenotype:
    working_memory_dimensions: Any
    knowledge_capacity_bytes: Any
    relation_slots: Any
    knowledge_attention_slots: Any

    def as_matrix(self) -> Any:
        xp = backend_from_array(self.working_memory_dimensions).xp
        return xp.stack(
            (
                self.working_memory_dimensions,
                self.knowledge_capacity_bytes,
                self.relation_slots,
                self.knowledge_attention_slots,
            ),
            axis=1,
        )


def capacity_phenotype(
    genotype: Any,
    cfg: SimulationConfig,
    *,
    gene_start: int,
) -> CapacityPhenotype:
    values = genotype
    if values.ndim != 2:
        raise ValueError("genotype must be a two-dimensional matrix")
    rows = int(values.shape[0])
    dcfg = cfg.differentiation
    if not capacity_schema_enabled(cfg):
        xp = backend_from_array(values).xp
        return CapacityPhenotype(
            working_memory_dimensions=xp.full(
                rows, int(cfg.knowledge.working_memory_width), dtype=xp.int32
            ),
            knowledge_capacity_bytes=xp.full(
                rows, int(cfg.knowledge.holder_capacity_bytes), dtype=xp.int32
            ),
            relation_slots=xp.full(
                rows, int(cfg.entities.relation_slots), dtype=xp.int32
            ),
            knowledge_attention_slots=xp.full(
                rows, int(cfg.knowledge.attention_slots_per_tick), dtype=xp.int32
            ),
        )
    stop = int(gene_start) + CAPACITY_GENE_COUNT
    if values.shape[1] < stop:
        raise ValueError("genotype does not contain D1 capacity genes")
    genes = values[:, int(gene_start):stop]
    return CapacityPhenotype(
        working_memory_dimensions=_map_gene(
            genes[:, 0],
            minimum=int(dcfg.working_memory_min_dimensions),
            maximum=int(dcfg.working_memory_max_dimensions),
        ),
        knowledge_capacity_bytes=_map_gene(
            genes[:, 1],
            minimum=int(dcfg.knowledge_min_bytes),
            maximum=int(dcfg.knowledge_max_bytes),
            quantum=int(dcfg.knowledge_quantum_bytes),
        ),
        relation_slots=_map_gene(
            genes[:, 2],
            minimum=int(dcfg.relation_min_slots),
            maximum=int(dcfg.relation_max_slots),
        ),
        knowledge_attention_slots=_map_gene(
            genes[:, 3],
            minimum=int(dcfg.attention_min_slots),
            maximum=int(dcfg.attention_max_slots),
        ),
    )


def neutral_capacity_phenotype(
    rows: int,
    config: DifferentiationConfig,
) -> CapacityPhenotype:
    """Return the fixed midpoint expression used by causal neutralization.

    The intervention changes phenotype only: inherited genes and mutation remain
    untouched.  Knowledge capacity is rounded to the nearest valid configured
    quantum by choosing the midpoint discrete level.
    """
    count = int(rows)
    if count < 0:
        raise ValueError("capacity phenotype row count must be non-negative")
    quantum = int(config.knowledge_quantum_bytes)
    knowledge_steps = (
        int(config.knowledge_max_bytes) - int(config.knowledge_min_bytes)
    ) // quantum
    knowledge_mid = int(config.knowledge_min_bytes) + (knowledge_steps // 2) * quantum
    return CapacityPhenotype(
        working_memory_dimensions=np.full(
            count,
            (int(config.working_memory_min_dimensions) + int(config.working_memory_max_dimensions)) // 2,
            dtype=np.int32,
        ),
        knowledge_capacity_bytes=np.full(count, knowledge_mid, dtype=np.int32),
        relation_slots=np.full(
            count,
            (int(config.relation_min_slots) + int(config.relation_max_slots)) // 2,
            dtype=np.int32,
        ),
        knowledge_attention_slots=np.full(
            count,
            (int(config.attention_min_slots) + int(config.attention_max_slots)) // 2,
            dtype=np.int32,
        ),
    )


def capacity_maintenance_energy(
    phenotype: CapacityPhenotype,
    config: DifferentiationConfig,
) -> Any:
    xp = backend_from_array(phenotype.working_memory_dimensions).xp
    return (
        phenotype.working_memory_dimensions.astype(xp.float64)
        * float(config.maintenance_energy_per_working_memory_dimension)
        + phenotype.knowledge_capacity_bytes.astype(xp.float64)
        * float(config.maintenance_energy_per_knowledge_byte)
        + phenotype.relation_slots.astype(xp.float64)
        * float(config.maintenance_energy_per_relation_slot)
        + phenotype.knowledge_attention_slots.astype(xp.float64)
        * float(config.maintenance_energy_per_attention_slot)
    )


def capacity_development_energy(
    phenotype: CapacityPhenotype,
    config: DifferentiationConfig,
) -> Any:
    xp = backend_from_array(phenotype.working_memory_dimensions).xp
    return (
        phenotype.working_memory_dimensions.astype(xp.float64)
        * float(config.development_energy_per_working_memory_dimension)
        + phenotype.knowledge_capacity_bytes.astype(xp.float64)
        * float(config.development_energy_per_knowledge_byte)
        + phenotype.relation_slots.astype(xp.float64)
        * float(config.development_energy_per_relation_slot)
        + phenotype.knowledge_attention_slots.astype(xp.float64)
        * float(config.development_energy_per_attention_slot)
    )


def _effective_dimensions(matrix: np.ndarray) -> float:
    if matrix.shape[0] <= 1 or matrix.shape[1] == 0:
        return 0.0
    standardized = matrix.astype(np.float64, copy=False)
    std = standardized.std(axis=0)
    active = std > 1e-12
    if not np.any(active):
        return 0.0
    standardized = (standardized[:, active] - standardized[:, active].mean(axis=0)) / std[active]
    covariance = np.cov(standardized, rowvar=False)
    eigenvalues = np.atleast_1d(np.linalg.eigvalsh(np.atleast_2d(covariance)))
    eigenvalues = np.clip(eigenvalues, 0.0, None)
    total = float(eigenvalues.sum())
    return 0.0 if total <= 0.0 else float(total * total / np.square(eigenvalues).sum())


def capacity_diagnostics(
    phenotype: CapacityPhenotype,
    *,
    alive: Any,
    config: DifferentiationConfig,
) -> dict[str, Any]:
    active = np.flatnonzero(np.asarray(alive, dtype=bool))
    matrix = np.asarray(phenotype.as_matrix(), dtype=np.int64)
    selected = matrix[active] if active.size else np.empty((0, 4), dtype=np.int64)
    result: dict[str, Any] = {
        "differentiation_schema": str(config.schema),
        "capacity_active_entities": int(active.size),
        "capacity_effective_dimensions": _effective_dimensions(selected),
    }
    for column, name in enumerate(CAPACITY_TRAIT_NAMES):
        values = selected[:, column] if selected.size else np.empty(0, dtype=np.int64)
        result[f"capacity_{name}_mean"] = float(values.mean()) if values.size else 0.0
        result[f"capacity_{name}_std"] = float(values.std()) if values.size else 0.0
        result[f"capacity_{name}_min"] = int(values.min()) if values.size else 0
        result[f"capacity_{name}_max"] = int(values.max()) if values.size else 0
        result[f"capacity_{name}_unique"] = int(np.unique(values).size) if values.size else 0
    return result


__all__ = [
    "CAPACITY_GENE_COUNT",
    "CAPACITY_SCHEMA",
    "CAPACITY_TRAIT_NAMES",
    "CapacityPhenotype",
    "capacity_development_energy",
    "capacity_diagnostics",
    "capacity_gene_count",
    "capacity_maintenance_energy",
    "neutral_capacity_phenotype",
    "capacity_phenotype",
    "capacity_schema_enabled",
]
