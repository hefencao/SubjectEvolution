"""Inherited parameters for the bounded regulatory physiology substrate.

The v5 physiology layer deliberately avoids named organs or hormones.  Fifteen
fixed genes parameterize transport, storage, conversion, clearance, repair,
and two decaying whole-body messenger buses.  The genes do not create new
world actions: they constrain how functional-module regulatory drives become
actual movement, sensing, signaling, maintenance, and damage.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np

from se.cfg import SimulationConfig

LEGACY_REGULATORY_PHYSIOLOGY_SCHEMA = "transport-metabolism-messenger-tissue-v2"
CONSERVATIVE_REGULATORY_PHYSIOLOGY_SCHEMA = "transport-metabolism-messenger-tissue-v3"
RESOURCE_METABOLISM_PHYSIOLOGY_SCHEMA = "transport-metabolism-messenger-tissue-resource-v4"
CONSERVATIVE_INTAKE_PHYSIOLOGY_SCHEMA = "transport-metabolism-messenger-tissue-resource-v5"
RESOURCE_RECYCLING_PHYSIOLOGY_SCHEMA = "transport-metabolism-messenger-tissue-resource-v6"
REGULATORY_PHYSIOLOGY_SCHEMA = CONSERVATIVE_REGULATORY_PHYSIOLOGY_SCHEMA
REGULATORY_PHYSIOLOGY_SCHEMAS = frozenset(
    {
        LEGACY_REGULATORY_PHYSIOLOGY_SCHEMA,
        CONSERVATIVE_REGULATORY_PHYSIOLOGY_SCHEMA,
        RESOURCE_METABOLISM_PHYSIOLOGY_SCHEMA,
        CONSERVATIVE_INTAKE_PHYSIOLOGY_SCHEMA,
        RESOURCE_RECYCLING_PHYSIOLOGY_SCHEMA,
    }
)
PHYSIOLOGY_GENE_NAMES = (
    "oxygen_transport_capacity",
    "oxygen_reserve_capacity",
    "aerobic_conversion_efficiency",
    "anaerobic_tolerance",
    "mechanical_power_capacity",
    "information_transduction_capacity",
    "fatigue_clearance_capacity",
    "repair_conversion_efficiency",
    "structure_repair_allocation",
    "mobilization_synthesis_capacity",
    "maintenance_synthesis_capacity",
    "mobilization_decay_capacity",
    "maintenance_decay_capacity",
    "mobilization_receptor_gain",
    "maintenance_receptor_gain",
)
PHYSIOLOGY_GENE_COUNT = len(PHYSIOLOGY_GENE_NAMES)
RESOURCE_METABOLISM_GENE_NAMES = tuple(
    [f"resource_store_capacity_{index}" for index in range(4)]
    + [f"resource_conversion_capacity_{index}" for index in range(4)]
)
RESOURCE_METABOLISM_GENE_COUNT = len(RESOURCE_METABOLISM_GENE_NAMES)


@dataclass(frozen=True)
class PhysiologyPhenotype:
    oxygen_transport_capacity: np.ndarray
    oxygen_reserve_capacity: np.ndarray
    aerobic_conversion_efficiency: np.ndarray
    anaerobic_tolerance: np.ndarray
    mechanical_power_capacity: np.ndarray
    information_transduction_capacity: np.ndarray
    fatigue_clearance_capacity: np.ndarray
    repair_conversion_efficiency: np.ndarray
    structure_repair_allocation: np.ndarray
    mobilization_synthesis_capacity: np.ndarray
    maintenance_synthesis_capacity: np.ndarray
    mobilization_decay_capacity: np.ndarray
    maintenance_decay_capacity: np.ndarray
    mobilization_receptor_gain: np.ndarray
    maintenance_receptor_gain: np.ndarray
    resource_store_capacity: np.ndarray
    resource_conversion_capacity: np.ndarray


def regulatory_physiology_enabled(cfg: SimulationConfig) -> bool:
    return bool(cfg.physiology.enabled and cfg.physiology.schema in REGULATORY_PHYSIOLOGY_SCHEMAS)




def conservative_regulatory_physiology_enabled(cfg: SimulationConfig) -> bool:
    """Return whether strict non-negative flow-ledger semantics are active."""

    return bool(
        cfg.physiology.enabled
        and cfg.physiology.schema
        in {
            CONSERVATIVE_REGULATORY_PHYSIOLOGY_SCHEMA,
            RESOURCE_METABOLISM_PHYSIOLOGY_SCHEMA,
            CONSERVATIVE_INTAKE_PHYSIOLOGY_SCHEMA,
            RESOURCE_RECYCLING_PHYSIOLOGY_SCHEMA,
        }
    )

def resource_metabolism_enabled(cfg: SimulationConfig) -> bool:
    return bool(
        cfg.physiology.enabled
        and cfg.physiology.schema in {
            RESOURCE_METABOLISM_PHYSIOLOGY_SCHEMA,
            CONSERVATIVE_INTAKE_PHYSIOLOGY_SCHEMA,
            RESOURCE_RECYCLING_PHYSIOLOGY_SCHEMA,
        }
    )


def storage_constrained_intake_enabled(cfg: SimulationConfig) -> bool:
    return bool(
        cfg.physiology.enabled
        and cfg.physiology.schema in {
            CONSERVATIVE_INTAKE_PHYSIOLOGY_SCHEMA,
            RESOURCE_RECYCLING_PHYSIOLOGY_SCHEMA,
        }
    )



def external_resource_recycling_enabled(cfg: SimulationConfig) -> bool:
    """Return whether identity-preserving external residue recycling is active."""

    return bool(
        cfg.physiology.enabled
        and cfg.physiology.schema == RESOURCE_RECYCLING_PHYSIOLOGY_SCHEMA
    )


def physiology_gene_count(cfg: SimulationConfig) -> int:
    if not regulatory_physiology_enabled(cfg):
        return 0
    return PHYSIOLOGY_GENE_COUNT + (
        RESOURCE_METABOLISM_GENE_COUNT if resource_metabolism_enabled(cfg) else 0
    )


def physiology_gene_names(cfg: SimulationConfig) -> tuple[str, ...]:
    return PHYSIOLOGY_GENE_NAMES + (
        RESOURCE_METABOLISM_GENE_NAMES if resource_metabolism_enabled(cfg) else ()
    )


def _bounded_symmetric(raw: np.ndarray, half_span: float = 0.5) -> np.ndarray:
    return 1.0 + half_span * np.tanh(raw.astype(np.float64))


def _bounded_unit(raw: np.ndarray) -> np.ndarray:
    return 0.5 + 0.5 * np.tanh(raw.astype(np.float64))


def physiology_phenotype(
    genotype: Any,
    cfg: SimulationConfig,
    *,
    gene_start: int,
) -> PhysiologyPhenotype:
    values = np.asarray(genotype, dtype=np.float32)
    if not regulatory_physiology_enabled(cfg):
        ones = np.ones(values.shape[0], dtype=np.float64)
        halves = np.full(values.shape[0], 0.5, dtype=np.float64)
        return PhysiologyPhenotype(
            oxygen_transport_capacity=ones,
            oxygen_reserve_capacity=ones,
            aerobic_conversion_efficiency=ones,
            anaerobic_tolerance=halves,
            mechanical_power_capacity=ones,
            information_transduction_capacity=ones,
            fatigue_clearance_capacity=ones,
            repair_conversion_efficiency=ones,
            structure_repair_allocation=halves,
            mobilization_synthesis_capacity=ones,
            maintenance_synthesis_capacity=ones,
            mobilization_decay_capacity=ones,
            maintenance_decay_capacity=ones,
            mobilization_receptor_gain=ones,
            maintenance_receptor_gain=ones,
            resource_store_capacity=np.zeros((values.shape[0], 4), dtype=np.float64),
            resource_conversion_capacity=np.zeros((values.shape[0], 4), dtype=np.float64),
        )
    configured_count = physiology_gene_count(cfg)
    raw = values[:, gene_start : gene_start + configured_count]
    if raw.shape != (values.shape[0], configured_count):
        raise ValueError("genotype does not contain the configured physiology genes")
    resource_raw = (
        raw[:, PHYSIOLOGY_GENE_COUNT : PHYSIOLOGY_GENE_COUNT + RESOURCE_METABOLISM_GENE_COUNT]
        if resource_metabolism_enabled(cfg)
        else np.zeros((values.shape[0], RESOURCE_METABOLISM_GENE_COUNT), dtype=np.float32)
    )
    store_base = np.asarray(cfg.physiology.resource_store_base_capacity, dtype=np.float64)[None, :]
    conversion_base = np.asarray(cfg.physiology.resource_conversion_per_tick, dtype=np.float64)[None, :]
    return PhysiologyPhenotype(
        oxygen_transport_capacity=_bounded_symmetric(raw[:, 0]),
        oxygen_reserve_capacity=_bounded_symmetric(raw[:, 1]),
        aerobic_conversion_efficiency=_bounded_symmetric(raw[:, 2]),
        anaerobic_tolerance=_bounded_unit(raw[:, 3]),
        mechanical_power_capacity=_bounded_symmetric(raw[:, 4]),
        information_transduction_capacity=_bounded_symmetric(raw[:, 5]),
        fatigue_clearance_capacity=_bounded_symmetric(raw[:, 6]),
        repair_conversion_efficiency=_bounded_symmetric(raw[:, 7]),
        structure_repair_allocation=_bounded_unit(raw[:, 8]),
        mobilization_synthesis_capacity=_bounded_symmetric(raw[:, 9]),
        maintenance_synthesis_capacity=_bounded_symmetric(raw[:, 10]),
        mobilization_decay_capacity=_bounded_symmetric(raw[:, 11]),
        maintenance_decay_capacity=_bounded_symmetric(raw[:, 12]),
        mobilization_receptor_gain=_bounded_symmetric(raw[:, 13]),
        maintenance_receptor_gain=_bounded_symmetric(raw[:, 14]),
        resource_store_capacity=(
            store_base * _bounded_symmetric(resource_raw[:, :4])
            if resource_metabolism_enabled(cfg)
            else np.zeros((values.shape[0], 4), dtype=np.float64)
        ),
        resource_conversion_capacity=(
            conversion_base * _bounded_symmetric(resource_raw[:, 4:8])
            if resource_metabolism_enabled(cfg)
            else np.zeros((values.shape[0], 4), dtype=np.float64)
        ),
    )



def physiology_diagnostics(
    genotype: Any,
    alive: Any,
    cfg: SimulationConfig,
    *,
    gene_start: int,
) -> dict[str, object]:
    mask = np.asarray(alive, dtype=bool)
    rows = np.flatnonzero(mask)
    if not regulatory_physiology_enabled(cfg) or rows.size == 0:
        return {
            "schema": cfg.physiology.schema,
            "gene_names": list(physiology_gene_names(cfg)),
            "means": [0.0] * physiology_gene_count(cfg),
            "standard_deviations": [0.0] * physiology_gene_count(cfg),
            "effective_dimensions": 0.0,
        }
    phenotype = physiology_phenotype(
        np.asarray(genotype, dtype=np.float32)[rows], cfg, gene_start=gene_start
    )
    scalar_values = [
        np.asarray(getattr(phenotype, name), dtype=np.float64)
        for name in PHYSIOLOGY_GENE_NAMES
    ]
    if resource_metabolism_enabled(cfg):
        scalar_values.extend(
            [phenotype.resource_store_capacity[:, index] for index in range(4)]
        )
        scalar_values.extend(
            [phenotype.resource_conversion_capacity[:, index] for index in range(4)]
        )
    values = np.column_stack(scalar_values)
    centered = values - values.mean(axis=0, keepdims=True)
    covariance = centered.T @ centered / max(values.shape[0] - 1, 1)
    eigenvalues = np.clip(np.linalg.eigvalsh(covariance), 0.0, None)
    total = float(eigenvalues.sum())
    squared = float(np.square(eigenvalues).sum())
    effective = total * total / squared if squared > 0.0 else 0.0
    return {
        "schema": cfg.physiology.schema,
        "gene_names": list(physiology_gene_names(cfg)),
        "means": values.mean(axis=0).tolist(),
        "standard_deviations": values.std(axis=0).tolist(),
        "effective_dimensions": effective,
    }

def physiology_genome_energy(
    genotype: Any,
    cfg: SimulationConfig,
    *,
    gene_start: int,
    development: bool = False,
) -> np.ndarray:
    """Structural cost of inherited physiological capacities.

    This is distinct from per-tick transport, messenger synthesis, computation,
    and repair use costs, which are settled from actual runtime flows.
    """

    values = np.asarray(genotype, dtype=np.float32)
    if not regulatory_physiology_enabled(cfg):
        return np.zeros(values.shape[0], dtype=np.float64)
    phenotype = physiology_phenotype(values, cfg, gene_start=gene_start)
    capacity_load = (
        phenotype.oxygen_transport_capacity
        + phenotype.oxygen_reserve_capacity
        + phenotype.aerobic_conversion_efficiency
        + phenotype.mechanical_power_capacity
        + phenotype.information_transduction_capacity
        + phenotype.fatigue_clearance_capacity
        + phenotype.repair_conversion_efficiency
        + phenotype.mobilization_synthesis_capacity
        + phenotype.maintenance_synthesis_capacity
        + phenotype.mobilization_receptor_gain
        + phenotype.maintenance_receptor_gain
    ) / 11.0
    if resource_metabolism_enabled(cfg):
        store_base = np.maximum(
            np.asarray(cfg.physiology.resource_store_base_capacity, dtype=np.float64),
            1.0e-12,
        )
        conversion_base = np.maximum(
            np.asarray(cfg.physiology.resource_conversion_per_tick, dtype=np.float64),
            1.0e-12,
        )
        resource_load = 0.5 * (
            (phenotype.resource_store_capacity / store_base[None, :]).mean(axis=1)
            + (phenotype.resource_conversion_capacity / conversion_base[None, :]).mean(axis=1)
        )
        capacity_load = 0.75 * capacity_load + 0.25 * resource_load
    rate = (
        cfg.physiology.development_energy_per_capacity
        if development
        else cfg.physiology.maintenance_energy_per_capacity
    )
    return capacity_load * float(rate)


__all__ = [
    "CONSERVATIVE_INTAKE_PHYSIOLOGY_SCHEMA",
    "RESOURCE_RECYCLING_PHYSIOLOGY_SCHEMA",
    "CONSERVATIVE_REGULATORY_PHYSIOLOGY_SCHEMA",
    "LEGACY_REGULATORY_PHYSIOLOGY_SCHEMA",
    "PHYSIOLOGY_GENE_COUNT",
    "PHYSIOLOGY_GENE_NAMES",
    "REGULATORY_PHYSIOLOGY_SCHEMA",
    "RESOURCE_METABOLISM_PHYSIOLOGY_SCHEMA",
    "RESOURCE_METABOLISM_GENE_COUNT",
    "RESOURCE_METABOLISM_GENE_NAMES",
    "REGULATORY_PHYSIOLOGY_SCHEMAS",
    "PhysiologyPhenotype",
    "conservative_regulatory_physiology_enabled",
    "physiology_diagnostics",
    "physiology_gene_count",
    "physiology_gene_names",
    "physiology_genome_energy",
    "physiology_phenotype",
    "regulatory_physiology_enabled",
    "external_resource_recycling_enabled",
    "resource_metabolism_enabled",
    "storage_constrained_intake_enabled",
]
