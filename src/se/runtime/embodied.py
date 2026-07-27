"""Conserved physical semantics for v3 functional-module output primitives."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np

from se.cfg import SimulationConfig
from se.differentiation.functional import Q


@dataclass(frozen=True)
class EmbodiedRepairStats:
    energy: float = 0.0
    material: float = 0.0
    integrity: float = 0.0


def embodied_power_multipliers(
    output_q: np.ndarray,
    cfg: SimulationConfig,
) -> tuple[np.ndarray, np.ndarray]:
    """Map bounded locomotion/signal ports to positive physical multipliers."""

    output = np.asarray(output_q, dtype=np.int32)
    if output.ndim != 2 or output.shape[1] < 2:
        raise ValueError("embodied output must be [N, >=2]")
    normalized = output.astype(np.float64) / Q
    movement_limit = float(cfg.functional_modules.max_movement_speed_fraction)
    signal_limit = float(cfg.functional_modules.max_signal_strength_fraction)
    movement = np.clip(
        1.0 + movement_limit * normalized[:, 0],
        1.0 - movement_limit,
        1.0 + movement_limit,
    ).astype(np.float32)
    signal = np.clip(
        1.0 + signal_limit * normalized[:, 1],
        1.0 - signal_limit,
        1.0 + signal_limit,
    ).astype(np.float32)
    return movement, signal


def apply_material_repair(
    entities: Any,
    active: np.ndarray,
    output_q: np.ndarray,
    cfg: SimulationConfig,
) -> EmbodiedRepairStats:
    """Debit material and energy before restoring integrity."""

    indices = np.asarray(active, dtype=np.int32)
    output = np.asarray(output_q, dtype=np.int32)
    if indices.size == 0:
        return EmbodiedRepairStats()
    if output.shape != (indices.size, 3):
        raise ValueError("embodied repair output must be [active, 3]")
    drive = np.clip(output[:, 2].astype(np.float64) / Q, 0.0, 1.0)
    requested = drive * float(cfg.functional_modules.repair_material_per_tick)
    integrity_per_material = float(cfg.functional_modules.repair_integrity_per_material)
    energy_per_material = float(cfg.functional_modules.repair_energy_per_material)
    used = np.minimum(requested, entities.material[indices].astype(np.float64))
    used = np.minimum(used, entities.energy[indices].astype(np.float64) / energy_per_material)
    used = np.minimum(
        used,
        np.maximum(1.0 - entities.integrity[indices].astype(np.float64), 0.0)
        / integrity_per_material,
    )
    used = np.maximum(used, 0.0)
    if not np.any(used):
        return EmbodiedRepairStats()

    repair_energy = used * energy_per_material
    repair_integrity = used * integrity_per_material
    entities.material[indices] = np.maximum(
        entities.material[indices].astype(np.float64) - used, 0.0
    ).astype(np.float32)
    entities.energy[indices] = np.maximum(
        entities.energy[indices].astype(np.float64) - repair_energy, 0.0
    ).astype(np.float32)
    entities.integrity[indices] = np.minimum(
        entities.integrity[indices].astype(np.float64) + repair_integrity, 1.0
    ).astype(np.float32)
    return EmbodiedRepairStats(
        energy=float(repair_energy.sum(dtype=np.float64)),
        material=float(used.sum(dtype=np.float64)),
        integrity=float(repair_integrity.sum(dtype=np.float64)),
    )


def movement_cost_with_power(
    moved: np.ndarray,
    multiplier: np.ndarray,
    base_cost: float,
) -> tuple[np.ndarray, float]:
    """Return per-entity movement cost and the delta from legacy movement cost."""

    moved_values = np.asarray(moved, dtype=np.float64)
    power = np.asarray(multiplier, dtype=np.float64)
    if moved_values.shape != power.shape:
        raise ValueError("movement mask and multiplier must have matching shapes")
    baseline = moved_values * float(base_cost)
    actual = baseline * np.square(power)
    return actual, float((actual - baseline).sum(dtype=np.float64))


__all__ = [
    "EmbodiedRepairStats",
    "apply_material_repair",
    "embodied_power_multipliers",
    "movement_cost_with_power",
]
