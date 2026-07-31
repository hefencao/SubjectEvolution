"""Inherited, explicitly costed reproduction-investment semantics."""

from __future__ import annotations

from typing import Any

import numpy as np

from ..backend import backend_from_array
from ..cfg import SimulationConfig


LEGACY_REPRODUCTION_SCHEMA = "legacy-fixed-threshold-loss-v1"
INHERITED_REPRODUCTION_INVESTMENT_SCHEMA = (
    "inherited-conservative-offspring-investment-v2"
)
REPRODUCTION_INVESTMENT_GENE_INDEX = 6


def inherited_reproduction_investment_enabled(cfg: SimulationConfig) -> bool:
    return cfg.entities.reproduction_schema == INHERITED_REPRODUCTION_INVESTMENT_SCHEMA


def reproduction_investment(genotype: Any, cfg: SimulationConfig) -> Any:
    """Return the parent-to-offspring energy transfer selected by morphology gene 6."""

    backend = backend_from_array(genotype)
    xp = backend.xp
    values = xp.asarray(genotype, dtype=xp.float32)
    if values.ndim != 2 or values.shape[1] <= REPRODUCTION_INVESTMENT_GENE_INDEX:
        raise ValueError("genotype does not contain the reproduction-investment trait")
    if not inherited_reproduction_investment_enabled(cfg):
        return xp.full(
            values.shape[0],
            float(cfg.entities.reproduction_cost) * 0.45,
            dtype=xp.float32,
        )
    levels = xp.asarray(
        cfg.entities.reproduction_investment_levels, dtype=xp.float32
    )
    trait = xp.clip(
        values[:, REPRODUCTION_INVESTMENT_GENE_INDEX], -1.0, 1.0
    ).astype(xp.float64, copy=False)
    scaled = 0.5 * (trait + 1.0) * float(levels.size)
    indices = xp.minimum(xp.floor(scaled).astype(xp.int64), levels.size - 1)
    return levels[indices].astype(xp.float32, copy=False)


def reproduction_energy_cost(genotype: Any, cfg: SimulationConfig) -> Any:
    """Return the complete parent energy debit for each potential birth."""

    investment = reproduction_investment(genotype, cfg)
    if not inherited_reproduction_investment_enabled(cfg):
        return investment * 0.0 + float(cfg.entities.reproduction_cost)
    return investment + float(cfg.entities.reproduction_cost)


def reproduction_energy_requirement(genotype: Any, cfg: SimulationConfig) -> Any:
    """Return the energy required before reproduction for each entity."""

    cost = reproduction_energy_cost(genotype, cfg)
    if not inherited_reproduction_investment_enabled(cfg):
        return cost * 0.0 + float(cfg.entities.reproduction_threshold)
    return cost + float(cfg.entities.reproduction_parent_reserve)


def offspring_energy_endowment(
    parent_genotype: Any,
    cfg: SimulationConfig,
    *,
    neutralized: bool = False,
) -> Any:
    """Return newborn energy while preserving the parent's registered debit.

    The neutralized branch dissipates the inherited transfer but leaves parent
    eligibility and debit untouched.  It therefore removes only the offspring
    return of the costed capability.
    """

    investment = reproduction_investment(parent_genotype, cfg)
    if inherited_reproduction_investment_enabled(cfg) and neutralized:
        return investment * 0.0
    return investment


def reproduction_reference_energy(cfg: SimulationConfig) -> float:
    """Stable scalar reference for diagnostics that cannot consume per-row traits."""

    if not inherited_reproduction_investment_enabled(cfg):
        return float(cfg.entities.reproduction_threshold)
    levels = np.asarray(cfg.entities.reproduction_investment_levels, dtype=np.float64)
    return float(
        cfg.entities.reproduction_cost
        + cfg.entities.reproduction_parent_reserve
        + levels.mean()
    )


__all__ = [
    "INHERITED_REPRODUCTION_INVESTMENT_SCHEMA",
    "LEGACY_REPRODUCTION_SCHEMA",
    "REPRODUCTION_INVESTMENT_GENE_INDEX",
    "inherited_reproduction_investment_enabled",
    "offspring_energy_endowment",
    "reproduction_energy_cost",
    "reproduction_energy_requirement",
    "reproduction_investment",
    "reproduction_reference_energy",
]
