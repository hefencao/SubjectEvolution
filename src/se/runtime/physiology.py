"""Conserved lower-level physiology for versioned functional modules."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np

from se.cfg import SimulationConfig
from se.differentiation.functional import PHYSIOLOGICAL_OUTPUT_COUNT, Q
from se.differentiation.physiology import (
    PhysiologyPhenotype,
    conservative_regulatory_physiology_enabled,
    physiology_phenotype,
    regulatory_physiology_enabled,
)


@dataclass(frozen=True)
class PhysiologyMultipliers:
    movement: np.ndarray
    signal: np.ndarray
    sensor: np.ndarray
    perfusion: np.ndarray
    contractile: np.ndarray
    sensory: np.ndarray
    repair: np.ndarray


@dataclass(frozen=True)
class RegulatoryMultipliers:
    movement: np.ndarray
    signal: np.ndarray
    sensor: np.ndarray
    uptake_drive: np.ndarray
    mobilization_drive: np.ndarray
    maintenance_drive: np.ndarray
    sensory_attention_drive: np.ndarray


@dataclass(frozen=True)
class PhysiologyStepStats:
    oxygen_uptake: float = 0.0
    oxygen_use: float = 0.0
    perfusion_energy: float = 0.0
    repair_energy: float = 0.0
    repair_material: float = 0.0
    repair_oxygen: float = 0.0
    repair_tissue: float = 0.0
    repair_structure: float = 0.0
    repair_integrity: float = 0.0
    hypoxia_tissue_damage: float = 0.0
    wear_tissue_damage: float = 0.0
    wear_structure_damage: float = 0.0
    integrity_damage: float = 0.0
    messenger_synthesis: float = 0.0
    messenger_decay: float = 0.0
    messenger_precursor_used: float = 0.0
    messenger_precursor_recovered: float = 0.0
    messenger_energy: float = 0.0
    computation_energy: float = 0.0
    computation_oxygen: float = 0.0
    fatigue_generated: float = 0.0
    fatigue_cleared: float = 0.0


_CONSERVATIVE_FLOW_FIELDS = (
    "oxygen_uptake",
    "oxygen_use",
    "perfusion_energy",
    "repair_energy",
    "repair_material",
    "repair_oxygen",
    "repair_tissue",
    "repair_structure",
    "repair_integrity",
    "hypoxia_tissue_damage",
    "wear_tissue_damage",
    "wear_structure_damage",
    "integrity_damage",
    "messenger_synthesis",
    "messenger_decay",
    "messenger_precursor_used",
    "messenger_precursor_recovered",
    "messenger_energy",
    "computation_energy",
    "computation_oxygen",
    "fatigue_generated",
    "fatigue_cleared",
)


def validate_conservative_flow_ledger(stats: PhysiologyStepStats) -> None:
    """Reject negative or non-finite v3 flow entries before they reach reports."""

    invalid = {
        name: float(getattr(stats, name))
        for name in _CONSERVATIVE_FLOW_FIELDS
        if not np.isfinite(float(getattr(stats, name)))
        or float(getattr(stats, name)) < -1.0e-12
    }
    if invalid:
        raise RuntimeError(f"invalid conservative physiology flow ledger: {invalid}")


def _drive01(output_q: np.ndarray) -> np.ndarray:
    output = np.asarray(output_q, dtype=np.int32)
    if output.ndim != 2 or output.shape[1] != PHYSIOLOGICAL_OUTPUT_COUNT:
        raise ValueError("physiology output must be [N, 4]")
    return np.clip(0.5 + 0.5 * output.astype(np.float64) / Q, 0.0, 1.0)


def _signed_drive(output_q: np.ndarray) -> np.ndarray:
    output = np.asarray(output_q, dtype=np.int32)
    if output.ndim != 2 or output.shape[1] != PHYSIOLOGICAL_OUTPUT_COUNT:
        raise ValueError("regulatory output must be [N, 4]")
    return np.clip(output.astype(np.float64) / Q, -1.0, 1.0)


def physiology_multipliers(
    output_q: np.ndarray,
    oxygenation: np.ndarray,
    tissue_condition: np.ndarray,
    structure_condition: np.ndarray,
    local_terrain: np.ndarray,
    cfg: SimulationConfig,
) -> PhysiologyMultipliers:
    """Archived v4 coarse-drive execution semantics."""

    drives = _drive01(output_q)
    oxygen = np.clip(np.asarray(oxygenation, dtype=np.float64), 0.0, 1.0)
    tissue = np.clip(np.asarray(tissue_condition, dtype=np.float64), 0.0, 1.0)
    structure = np.clip(np.asarray(structure_condition, dtype=np.float64), 0.0, 1.0)
    terrain = np.clip(np.asarray(local_terrain, dtype=np.float64), 0.0, 1.0)
    if any(values.shape != oxygen.shape for values in (tissue, structure, terrain)):
        raise ValueError("physiology body/environment vectors must align")
    perfusion, contractile, sensory, repair = (drives[:, i] for i in range(4))
    oxygen_support = np.sqrt(np.clip(oxygen, 0.0, 1.0))
    body_support = np.sqrt(np.clip(tissue * structure, 0.0, 1.0))
    locomotor_capacity = perfusion * contractile * oxygen_support * body_support
    locomotor_gain = 1.0 + float(cfg.physiology.max_movement_speed_fraction) * (
        2.0 * locomotor_capacity - 1.0
    )
    terrain_penalty = 1.0 - float(cfg.physiology.terrain_speed_penalty_fraction) * terrain
    movement = np.clip(locomotor_gain * terrain_penalty, 0.1, 2.5)
    sensory_capacity = perfusion * sensory * oxygen_support * np.sqrt(tissue)
    signal = np.clip(
        1.0
        + float(cfg.physiology.max_signal_strength_fraction)
        * (2.0 * sensory_capacity - 1.0),
        0.1,
        2.5,
    )
    sensor = np.clip(0.25 + 1.5 * sensory_capacity, 0.1, 2.0)
    return PhysiologyMultipliers(
        movement=movement.astype(np.float32),
        signal=signal.astype(np.float32),
        sensor=sensor.astype(np.float32),
        perfusion=perfusion.astype(np.float32),
        contractile=contractile.astype(np.float32),
        sensory=sensory.astype(np.float32),
        repair=repair.astype(np.float32),
    )


def regulatory_multipliers(
    output_q: np.ndarray,
    *,
    oxygenation: np.ndarray,
    metabolic_fatigue: np.ndarray,
    tissue_condition: np.ndarray,
    structure_condition: np.ndarray,
    mobilization_messenger: np.ndarray,
    maintenance_messenger: np.ndarray,
    local_terrain: np.ndarray,
    phenotype: PhysiologyPhenotype,
    cfg: SimulationConfig,
    receptor_blocked: bool = False,
) -> RegulatoryMultipliers:
    """Translate v5 regulatory requests through inherited body capacities."""

    drives = _signed_drive(output_q)
    uptake_modulation, mobilization_stimulus, maintenance_stimulus, sensory_attention = (
        drives[:, i] for i in range(4)
    )
    uptake_drive = np.clip(1.0 + uptake_modulation, 0.0, 2.0)
    mobilization_drive = np.clip(mobilization_stimulus, 0.0, 1.0)
    maintenance_drive = np.clip(maintenance_stimulus, 0.0, 1.0)
    oxygen = np.clip(np.asarray(oxygenation, dtype=np.float64), 0.0, 1.0)
    fatigue = np.clip(np.asarray(metabolic_fatigue, dtype=np.float64), 0.0, 1.0)
    tissue = np.clip(np.asarray(tissue_condition, dtype=np.float64), 0.0, 1.0)
    structure = np.clip(np.asarray(structure_condition, dtype=np.float64), 0.0, 1.0)
    mobilization = np.clip(np.asarray(mobilization_messenger, dtype=np.float64), 0.0, 1.0)
    maintenance = np.clip(np.asarray(maintenance_messenger, dtype=np.float64), 0.0, 1.0)
    terrain = np.clip(np.asarray(local_terrain, dtype=np.float64), 0.0, 1.0)
    expected = oxygen.shape
    arrays = (fatigue, tissue, structure, mobilization, maintenance, terrain)
    if any(values.shape != expected for values in arrays):
        raise ValueError("regulatory physiology state vectors must align")

    mobilization_receptor_gain = (
        np.zeros_like(phenotype.mobilization_receptor_gain, dtype=np.float64)
        if receptor_blocked
        else phenotype.mobilization_receptor_gain
    )
    maintenance_receptor_gain = (
        np.zeros_like(phenotype.maintenance_receptor_gain, dtype=np.float64)
        if receptor_blocked
        else phenotype.maintenance_receptor_gain
    )
    receptor = np.clip(mobilization_receptor_gain * mobilization, 0.0, 1.5)
    maintenance_effect = np.clip(
        maintenance_receptor_gain * maintenance, 0.0, 1.5
    )
    oxygen_support = (
        phenotype.anaerobic_tolerance
        + (1.0 - phenotype.anaerobic_tolerance) * oxygen
    )
    body_support = np.sqrt(np.clip(tissue * structure, 0.0, 1.0))
    fatigue_support = np.clip(1.0 - fatigue, 0.05, 1.0)
    aerobic_support = np.sqrt(
        np.clip(phenotype.aerobic_conversion_efficiency, 0.25, 2.0)
    )
    mobilization_gain = 1.0 + float(cfg.physiology.mobilization_speed_gain) * receptor
    maintenance_penalty = 1.0 - float(cfg.physiology.maintenance_speed_penalty) * np.clip(
        maintenance_effect, 0.0, 1.0
    )
    terrain_penalty = 1.0 - float(cfg.physiology.terrain_speed_penalty_fraction) * terrain
    movement_capacity = np.clip(
        body_support
        * oxygen_support
        * fatigue_support
        * aerobic_support
        * np.sqrt(np.clip(phenotype.mechanical_power_capacity, 0.25, 2.0))
        * mobilization_gain
        * maintenance_penalty,
        0.0,
        2.0,
    )
    movement = np.clip(
        (
            1.0
            + float(cfg.physiology.max_movement_speed_fraction)
            * (movement_capacity - 1.0)
        )
        * terrain_penalty,
        0.1,
        2.5,
    )

    attention = np.clip(1.0 + sensory_attention, 0.0, 2.0)
    sensory_body = (
        np.sqrt(np.clip(tissue, 0.0, 1.0))
        * oxygen_support
        * fatigue_support
        * np.sqrt(np.clip(phenotype.information_transduction_capacity, 0.25, 2.0))
    )
    signal_capacity = np.clip(
        sensory_body
        * attention
        * (1.0 + float(cfg.physiology.mobilization_signal_gain) * receptor),
        0.0,
        2.0,
    )
    signal = np.clip(
        1.0
        + float(cfg.physiology.max_signal_strength_fraction)
        * (signal_capacity - 1.0),
        0.1,
        2.5,
    )
    sensor = np.clip(sensory_body * attention, 0.1, 2.0)
    return RegulatoryMultipliers(
        movement=movement.astype(np.float32),
        signal=signal.astype(np.float32),
        sensor=sensor.astype(np.float32),
        uptake_drive=uptake_drive.astype(np.float32),
        mobilization_drive=mobilization_drive.astype(np.float32),
        maintenance_drive=maintenance_drive.astype(np.float32),
        sensory_attention_drive=sensory_attention.astype(np.float32),
    )


def _apply_v4_physiology_step(
    entities: Any,
    rows: np.ndarray,
    *,
    output: np.ndarray,
    local_o2: np.ndarray,
    terrain: np.ndarray,
    wear: np.ndarray,
    moved_values: np.ndarray,
    signal_values: np.ndarray,
    cfg: SimulationConfig,
) -> PhysiologyStepStats:
    multipliers = physiology_multipliers(
        output,
        entities.oxygenation[rows],
        entities.tissue_condition[rows],
        entities.structure_condition[rows],
        terrain,
        cfg,
    )
    oxygen_before = entities.oxygenation[rows].astype(np.float64)
    uptake = (
        float(cfg.physiology.oxygen_uptake_per_tick)
        * local_o2
        * multipliers.perfusion.astype(np.float64)
        * np.maximum(1.0 - oxygen_before, 0.0)
    )
    basal_use = np.full(rows.size, float(cfg.physiology.basal_oxygen_use_per_tick))
    movement_use = (
        moved_values.astype(np.float64)
        * float(cfg.physiology.movement_oxygen_use_per_tick)
        * np.square(multipliers.movement.astype(np.float64))
    )
    signal_use = (
        signal_values.astype(np.float64)
        * float(cfg.physiology.signal_oxygen_use_per_tick)
        * np.square(multipliers.signal.astype(np.float64))
    )
    perfusion_energy = (
        float(cfg.physiology.perfusion_energy_per_tick)
        * multipliers.perfusion.astype(np.float64)
    )
    affordable_fraction = np.ones(rows.size, dtype=np.float64)
    positive = perfusion_energy > 0.0
    affordable_fraction[positive] = np.minimum(
        entities.energy[rows][positive].astype(np.float64) / perfusion_energy[positive],
        1.0,
    )
    perfusion_energy *= affordable_fraction
    uptake *= affordable_fraction
    entities.energy[rows] = np.maximum(
        entities.energy[rows].astype(np.float64) - perfusion_energy, 0.0
    ).astype(np.float32)

    oxygen_available = np.maximum(
        oxygen_before + uptake - basal_use - movement_use - signal_use, 0.0
    )
    repair_drive = multipliers.repair.astype(np.float64)
    requested_material = repair_drive * float(cfg.physiology.repair_material_per_tick)
    material_use = np.minimum(requested_material, entities.material[rows].astype(np.float64))
    energy_per_material = float(cfg.physiology.repair_energy_per_material)
    oxygen_per_material = float(cfg.physiology.repair_oxygen_use_per_material)
    if energy_per_material > 0.0:
        material_use = np.minimum(
            material_use,
            entities.energy[rows].astype(np.float64) / energy_per_material,
        )
    if oxygen_per_material > 0.0:
        material_use = np.minimum(material_use, oxygen_available / oxygen_per_material)
    tissue_gap = np.maximum(1.0 - entities.tissue_condition[rows].astype(np.float64), 0.0)
    structure_gap = np.maximum(1.0 - entities.structure_condition[rows].astype(np.float64), 0.0)
    integrity_gap = np.maximum(1.0 - entities.integrity[rows].astype(np.float64), 0.0)
    total_repair_capacity = (
        tissue_gap / max(float(cfg.physiology.repair_tissue_per_material), 1.0e-12)
        + structure_gap / max(float(cfg.physiology.repair_structure_per_material), 1.0e-12)
        + integrity_gap
        / max(
            float(cfg.physiology.repair_tissue_per_material)
            * float(cfg.physiology.tissue_damage_integrity_fraction)
            + float(cfg.physiology.repair_structure_per_material)
            * float(cfg.physiology.structure_damage_integrity_fraction),
            1.0e-12,
        )
    )
    material_use = np.maximum(np.minimum(material_use, total_repair_capacity), 0.0)
    repair_energy = material_use * energy_per_material
    repair_oxygen = material_use * oxygen_per_material
    oxygen_available = np.maximum(oxygen_available - repair_oxygen, 0.0)
    entities.material[rows] = np.maximum(
        entities.material[rows].astype(np.float64) - material_use, 0.0
    ).astype(np.float32)
    entities.energy[rows] = np.maximum(
        entities.energy[rows].astype(np.float64) - repair_energy, 0.0
    ).astype(np.float32)

    threshold = float(cfg.physiology.hypoxia_threshold)
    hypoxia = np.maximum(threshold - oxygen_available, 0.0) / max(threshold, 1.0e-12)
    hypoxia_tissue = hypoxia * float(cfg.physiology.hypoxia_tissue_damage_per_tick)
    wear_load = wear * (1.0 + moved_values.astype(np.float64) * terrain)
    wear_tissue = wear_load * float(cfg.physiology.wear_tissue_damage_per_tick)
    wear_structure = wear_load * float(cfg.physiology.wear_structure_damage_per_tick)
    tissue_repair = material_use * float(cfg.physiology.repair_tissue_per_material)
    structure_repair = material_use * float(cfg.physiology.repair_structure_per_material)
    tissue = np.clip(
        entities.tissue_condition[rows].astype(np.float64)
        - hypoxia_tissue
        - wear_tissue
        + tissue_repair,
        0.0,
        1.0,
    )
    structure = np.clip(
        entities.structure_condition[rows].astype(np.float64)
        - wear_structure
        + structure_repair,
        0.0,
        1.0,
    )
    integrity_damage = (
        (hypoxia_tissue + wear_tissue)
        * float(cfg.physiology.tissue_damage_integrity_fraction)
        + wear_structure * float(cfg.physiology.structure_damage_integrity_fraction)
    )
    integrity_repair = (
        tissue_repair * float(cfg.physiology.tissue_damage_integrity_fraction)
        + structure_repair * float(cfg.physiology.structure_damage_integrity_fraction)
    )
    entities.integrity[rows] = np.clip(
        entities.integrity[rows].astype(np.float64) - integrity_damage + integrity_repair,
        0.0,
        1.0,
    ).astype(np.float32)
    entities.oxygenation[rows] = np.clip(oxygen_available, 0.0, 1.0).astype(np.float32)
    entities.tissue_condition[rows] = tissue.astype(np.float32)
    entities.structure_condition[rows] = structure.astype(np.float32)
    return PhysiologyStepStats(
        oxygen_uptake=float(uptake.sum(dtype=np.float64)),
        oxygen_use=float((basal_use + movement_use + signal_use + repair_oxygen).sum(dtype=np.float64)),
        perfusion_energy=float(perfusion_energy.sum(dtype=np.float64)),
        repair_energy=float(repair_energy.sum(dtype=np.float64)),
        repair_material=float(material_use.sum(dtype=np.float64)),
        repair_oxygen=float(repair_oxygen.sum(dtype=np.float64)),
        repair_tissue=float(tissue_repair.sum(dtype=np.float64)),
        repair_structure=float(structure_repair.sum(dtype=np.float64)),
        repair_integrity=float(integrity_repair.sum(dtype=np.float64)),
        hypoxia_tissue_damage=float(hypoxia_tissue.sum(dtype=np.float64)),
        wear_tissue_damage=float(wear_tissue.sum(dtype=np.float64)),
        wear_structure_damage=float(wear_structure.sum(dtype=np.float64)),
        integrity_damage=float(integrity_damage.sum(dtype=np.float64)),
    )


def _proportional_limit(
    requests: np.ndarray,
    limit: np.ndarray,
    *,
    conservative: bool = False,
) -> np.ndarray:
    values = np.asarray(requests, dtype=np.float64)
    available = np.asarray(limit, dtype=np.float64)
    if conservative:
        values = np.maximum(values, 0.0)
        available = np.maximum(available, 0.0)
    total = values.sum(axis=1, dtype=np.float64)
    scale = np.ones(values.shape[0], dtype=np.float64)
    positive = total > 0.0
    scale[positive] = np.minimum(available[positive] / total[positive], 1.0)
    if conservative:
        scale = np.clip(scale, 0.0, 1.0)
    return values * scale[:, None]


def _apply_v5_physiology_step(
    entities: Any,
    rows: np.ndarray,
    *,
    genotype: np.ndarray,
    gene_start: int,
    output: np.ndarray,
    local_o2: np.ndarray,
    terrain: np.ndarray,
    wear: np.ndarray,
    moved_values: np.ndarray,
    signal_values: np.ndarray,
    computation_load: np.ndarray,
    cfg: SimulationConfig,
    receptor_blocked: bool = False,
    state_clamps: dict[str, float] | None = None,
    conservative: bool = False,
) -> PhysiologyStepStats:
    phenotype = physiology_phenotype(genotype, cfg, gene_start=gene_start)
    multipliers = regulatory_multipliers(
        output,
        oxygenation=entities.oxygenation[rows],
        metabolic_fatigue=entities.metabolic_fatigue[rows],
        tissue_condition=entities.tissue_condition[rows],
        structure_condition=entities.structure_condition[rows],
        mobilization_messenger=entities.mobilization_messenger[rows],
        maintenance_messenger=entities.maintenance_messenger[rows],
        local_terrain=terrain,
        phenotype=phenotype,
        cfg=cfg,
        receptor_blocked=receptor_blocked,
    )

    energy = entities.energy[rows].astype(np.float64)
    material = entities.material[rows].astype(np.float64)
    precursor = np.clip(entities.messenger_precursor[rows].astype(np.float64), 0.0, 1.0)
    mobilization = np.clip(entities.mobilization_messenger[rows].astype(np.float64), 0.0, 1.0)
    maintenance = np.clip(entities.maintenance_messenger[rows].astype(np.float64), 0.0, 1.0)

    requested_synthesis = (
        float(cfg.physiology.messenger_synthesis_per_tick)
        * np.column_stack(
            (
                phenotype.mobilization_synthesis_capacity,
                phenotype.maintenance_synthesis_capacity,
            )
        )
        * np.column_stack(
            (
                multipliers.mobilization_drive.astype(np.float64),
                multipliers.maintenance_drive.astype(np.float64),
            )
        )
    )
    precursor_per_unit = float(cfg.physiology.messenger_precursor_use_per_unit)
    energy_per_unit = float(cfg.physiology.messenger_energy_per_unit)
    synthesis = np.maximum(requested_synthesis, 0.0) if conservative else requested_synthesis
    if precursor_per_unit > 0.0:
        synthesis = _proportional_limit(
            synthesis,
            precursor / precursor_per_unit,
            conservative=conservative,
        )
    if energy_per_unit > 0.0:
        synthesis = _proportional_limit(
            synthesis,
            energy / energy_per_unit,
            conservative=conservative,
        )
    synthesized_total = synthesis.sum(axis=1, dtype=np.float64)
    precursor_used = synthesized_total * precursor_per_unit
    messenger_energy = synthesized_total * energy_per_unit
    precursor = np.maximum(precursor - precursor_used, 0.0)
    energy = (
        energy - messenger_energy
        if conservative
        else np.maximum(energy - messenger_energy, 0.0)
    )

    mobilization_decay_fraction = np.clip(
        float(cfg.physiology.messenger_decay_per_tick)
        * phenotype.mobilization_decay_capacity,
        0.0,
        1.0,
    )
    maintenance_decay_fraction = np.clip(
        float(cfg.physiology.messenger_decay_per_tick)
        * phenotype.maintenance_decay_capacity,
        0.0,
        1.0,
    )
    mobilization_decay = mobilization * mobilization_decay_fraction
    maintenance_decay = maintenance * maintenance_decay_fraction
    mobilization = np.clip(mobilization - mobilization_decay + synthesis[:, 0], 0.0, 1.0)
    maintenance = np.clip(maintenance - maintenance_decay + synthesis[:, 1], 0.0, 1.0)

    precursor_gap = np.maximum(1.0 - precursor, 0.0)
    precursor_request = (
        precursor_gap
        * float(cfg.physiology.messenger_precursor_recovery_per_tick)
        * (0.25 + 0.75 * maintenance)
    )
    material_per_precursor = float(cfg.physiology.messenger_precursor_material_per_unit)
    precursor_recovery = precursor_request.copy()
    if material_per_precursor > 0.0:
        precursor_recovery = np.minimum(
            precursor_recovery,
            (np.maximum(material, 0.0) if conservative else material)
            / material_per_precursor,
        )
    precursor_material = precursor_recovery * material_per_precursor
    material = (
        material - precursor_material
        if conservative
        else np.maximum(material - precursor_material, 0.0)
    )
    precursor = np.clip(precursor + precursor_recovery, 0.0, 1.0)

    oxygen_capacity = np.clip(phenotype.oxygen_reserve_capacity, 0.25, 2.0)
    oxygen_amount = (
        np.clip(entities.oxygenation[rows].astype(np.float64), 0.0, 1.0)
        * oxygen_capacity
    )
    oxygen_gap = np.maximum(oxygen_capacity - oxygen_amount, 0.0)
    uptake = (
        float(cfg.physiology.oxygen_uptake_per_tick)
        * local_o2
        * phenotype.oxygen_transport_capacity
        * multipliers.uptake_drive.astype(np.float64)
        * oxygen_gap
    )
    oxygen_amount += uptake

    aerobic_efficiency = np.clip(
        phenotype.aerobic_conversion_efficiency, 0.25, 2.0
    )
    mobilization_receptor_gain = (
        np.zeros_like(phenotype.mobilization_receptor_gain, dtype=np.float64)
        if receptor_blocked
        else phenotype.mobilization_receptor_gain
    )
    maintenance_receptor_gain = (
        np.zeros_like(phenotype.maintenance_receptor_gain, dtype=np.float64)
        if receptor_blocked
        else phenotype.maintenance_receptor_gain
    )
    receptor_mobilization = np.clip(
        mobilization * mobilization_receptor_gain, 0.0, 1.5
    )
    basal_use = np.full(rows.size, float(cfg.physiology.basal_oxygen_use_per_tick))
    movement_use = (
        moved_values.astype(np.float64)
        * float(cfg.physiology.movement_oxygen_use_per_tick)
        * np.square(multipliers.movement.astype(np.float64))
        / aerobic_efficiency
        * (
            1.0
            + float(cfg.physiology.mobilization_oxygen_cost_gain)
            * receptor_mobilization
        )
    )
    signal_use = (
        signal_values.astype(np.float64)
        * float(cfg.physiology.signal_oxygen_use_per_tick)
        * np.square(multipliers.signal.astype(np.float64))
        / aerobic_efficiency
    )
    computation = np.clip(np.asarray(computation_load, dtype=np.float64), 0.0, None)
    computation_energy = computation * float(cfg.physiology.computation_energy_per_load)
    computation_oxygen = computation * float(cfg.physiology.computation_oxygen_per_load)
    energy = (
        energy - computation_energy
        if conservative
        else np.maximum(energy - computation_energy, 0.0)
    )
    oxygen_demand = basal_use + movement_use + signal_use + computation_oxygen
    oxygen_shortfall = np.maximum(oxygen_demand - oxygen_amount, 0.0)
    oxygen_amount = np.maximum(oxygen_amount - oxygen_demand, 0.0)
    oxygen_saturation = np.clip(oxygen_amount / oxygen_capacity, 0.0, 1.0)

    work_load = (
        moved_values.astype(np.float64) * np.square(multipliers.movement.astype(np.float64))
        + signal_values.astype(np.float64) * np.square(multipliers.signal.astype(np.float64))
        + computation
    )
    fatigue_generated = (
        float(cfg.physiology.fatigue_gain_per_work) * work_load
        + float(cfg.physiology.fatigue_gain_per_hypoxia)
        * oxygen_shortfall
        * (1.25 - 0.75 * phenotype.anaerobic_tolerance)
    )
    maintenance_effect = np.clip(
        maintenance * maintenance_receptor_gain, 0.0, 1.5
    )
    fatigue_cleared = (
        float(cfg.physiology.fatigue_clearance_per_tick)
        * phenotype.fatigue_clearance_capacity
        * oxygen_saturation
        * (
            1.0
            + float(cfg.physiology.maintenance_clearance_gain)
            * maintenance_effect
        )
    )
    fatigue_before = np.clip(entities.metabolic_fatigue[rows].astype(np.float64), 0.0, 1.0)
    fatigue_cleared = np.minimum(fatigue_cleared, fatigue_before + fatigue_generated)
    fatigue = np.clip(fatigue_before + fatigue_generated - fatigue_cleared, 0.0, 1.0)

    threshold = float(cfg.physiology.hypoxia_threshold)
    hypoxia = np.maximum(threshold - oxygen_saturation, 0.0) / max(threshold, 1.0e-12)
    hypoxia *= 1.0 - 0.75 * phenotype.anaerobic_tolerance
    hypoxia_tissue = hypoxia * float(cfg.physiology.hypoxia_tissue_damage_per_tick)
    wear_load = wear * (1.0 + moved_values.astype(np.float64) * terrain)
    wear_tissue = wear_load * float(cfg.physiology.wear_tissue_damage_per_tick)
    wear_structure = wear_load * float(cfg.physiology.wear_structure_damage_per_tick)

    tissue_gap = np.maximum(1.0 - entities.tissue_condition[rows].astype(np.float64), 0.0)
    structure_gap = np.maximum(1.0 - entities.structure_condition[rows].astype(np.float64), 0.0)
    integrity_gap = np.maximum(1.0 - entities.integrity[rows].astype(np.float64), 0.0)
    repair_demand = np.clip((tissue_gap + structure_gap + integrity_gap) / 3.0, 0.0, 1.0)
    requested_material = (
        float(cfg.physiology.repair_material_per_tick)
        * phenotype.repair_conversion_efficiency
        * repair_demand
        * (
            0.25
            + float(cfg.physiology.maintenance_repair_gain) * maintenance_effect
        )
    )
    material_use = np.minimum(
        requested_material, np.maximum(material, 0.0) if conservative else material
    )
    repair_energy_per_material = float(cfg.physiology.repair_energy_per_material)
    repair_oxygen_per_material = float(cfg.physiology.repair_oxygen_use_per_material)
    if repair_energy_per_material > 0.0:
        material_use = np.minimum(
            material_use,
            (np.maximum(energy, 0.0) if conservative else energy)
            / repair_energy_per_material,
        )
    if repair_oxygen_per_material > 0.0:
        material_use = np.minimum(material_use, oxygen_amount / repair_oxygen_per_material)
    repair_energy = material_use * repair_energy_per_material
    repair_oxygen = material_use * repair_oxygen_per_material
    material = (
        material - material_use
        if conservative
        else np.maximum(material - material_use, 0.0)
    )
    energy = (
        energy - repair_energy
        if conservative
        else np.maximum(energy - repair_energy, 0.0)
    )
    oxygen_amount = np.maximum(oxygen_amount - repair_oxygen, 0.0)
    oxygen_saturation = np.clip(oxygen_amount / oxygen_capacity, 0.0, 1.0)

    structure_share = np.clip(phenotype.structure_repair_allocation, 0.0, 1.0)
    tissue_repair = (
        material_use
        * (1.0 - structure_share)
        * 2.0
        * float(cfg.physiology.repair_tissue_per_material)
    )
    structure_repair = (
        material_use
        * structure_share
        * 2.0
        * float(cfg.physiology.repair_structure_per_material)
    )
    tissue = np.clip(
        entities.tissue_condition[rows].astype(np.float64)
        - hypoxia_tissue
        - wear_tissue
        + tissue_repair,
        0.0,
        1.0,
    )
    structure = np.clip(
        entities.structure_condition[rows].astype(np.float64)
        - wear_structure
        + structure_repair,
        0.0,
        1.0,
    )
    integrity_damage = (
        (hypoxia_tissue + wear_tissue)
        * float(cfg.physiology.tissue_damage_integrity_fraction)
        + wear_structure * float(cfg.physiology.structure_damage_integrity_fraction)
    )
    integrity_repair = (
        tissue_repair * float(cfg.physiology.tissue_damage_integrity_fraction)
        + structure_repair * float(cfg.physiology.structure_damage_integrity_fraction)
    )

    entities.energy[rows] = energy.astype(np.float32)
    entities.material[rows] = material.astype(np.float32)
    entities.integrity[rows] = np.clip(
        entities.integrity[rows].astype(np.float64) - integrity_damage + integrity_repair,
        0.0,
        1.0,
    ).astype(np.float32)
    entities.oxygenation[rows] = oxygen_saturation.astype(np.float32)
    entities.tissue_condition[rows] = tissue.astype(np.float32)
    entities.structure_condition[rows] = structure.astype(np.float32)
    entities.metabolic_fatigue[rows] = fatigue.astype(np.float32)
    entities.mobilization_messenger[rows] = mobilization.astype(np.float32)
    entities.maintenance_messenger[rows] = maintenance.astype(np.float32)
    entities.messenger_precursor[rows] = precursor.astype(np.float32)

    clamp_targets = {
        "oxygenation": entities.oxygenation,
        "tissue_condition": entities.tissue_condition,
        "structure_condition": entities.structure_condition,
        "metabolic_fatigue": entities.metabolic_fatigue,
        "mobilization_messenger": entities.mobilization_messenger,
        "maintenance_messenger": entities.maintenance_messenger,
        "messenger_precursor": entities.messenger_precursor,
    }
    for name, value in (state_clamps or {}).items():
        if name not in clamp_targets:
            raise ValueError(f"unsupported physiology state clamp: {name}")
        clamp_targets[name][rows] = np.float32(np.clip(float(value), 0.0, 1.0))

    oxygen_saturation = entities.oxygenation[rows].astype(np.float64)
    tissue = entities.tissue_condition[rows].astype(np.float64)
    structure = entities.structure_condition[rows].astype(np.float64)
    fatigue = entities.metabolic_fatigue[rows].astype(np.float64)
    mobilization = entities.mobilization_messenger[rows].astype(np.float64)
    maintenance = entities.maintenance_messenger[rows].astype(np.float64)

    next_multipliers = regulatory_multipliers(
        output,
        oxygenation=oxygen_saturation,
        metabolic_fatigue=fatigue,
        tissue_condition=tissue,
        structure_condition=structure,
        mobilization_messenger=mobilization,
        maintenance_messenger=maintenance,
        local_terrain=terrain,
        phenotype=phenotype,
        cfg=cfg,
        receptor_blocked=receptor_blocked,
    )
    entities.physiology_sensor_multiplier[rows] = next_multipliers.sensor

    stats = PhysiologyStepStats(
        oxygen_uptake=float(uptake.sum(dtype=np.float64)),
        oxygen_use=float((oxygen_demand + repair_oxygen).sum(dtype=np.float64)),
        repair_energy=float(repair_energy.sum(dtype=np.float64)),
        repair_material=float(material_use.sum(dtype=np.float64)),
        repair_oxygen=float(repair_oxygen.sum(dtype=np.float64)),
        repair_tissue=float(tissue_repair.sum(dtype=np.float64)),
        repair_structure=float(structure_repair.sum(dtype=np.float64)),
        repair_integrity=float(integrity_repair.sum(dtype=np.float64)),
        hypoxia_tissue_damage=float(hypoxia_tissue.sum(dtype=np.float64)),
        wear_tissue_damage=float(wear_tissue.sum(dtype=np.float64)),
        wear_structure_damage=float(wear_structure.sum(dtype=np.float64)),
        integrity_damage=float(integrity_damage.sum(dtype=np.float64)),
        messenger_synthesis=float(synthesized_total.sum(dtype=np.float64)),
        messenger_decay=float((mobilization_decay + maintenance_decay).sum(dtype=np.float64)),
        messenger_precursor_used=float(precursor_used.sum(dtype=np.float64)),
        messenger_precursor_recovered=float(precursor_recovery.sum(dtype=np.float64)),
        messenger_energy=float(messenger_energy.sum(dtype=np.float64)),
        computation_energy=float(computation_energy.sum(dtype=np.float64)),
        computation_oxygen=float(computation_oxygen.sum(dtype=np.float64)),
        fatigue_generated=float(fatigue_generated.sum(dtype=np.float64)),
        fatigue_cleared=float(fatigue_cleared.sum(dtype=np.float64)),
    )
    if conservative:
        validate_conservative_flow_ledger(stats)
    return stats


def apply_physiology_step(
    entities: Any,
    active: np.ndarray,
    *,
    output_q: np.ndarray,
    local_oxygen: np.ndarray,
    local_terrain: np.ndarray,
    local_wear: np.ndarray,
    moved: np.ndarray,
    signaled: np.ndarray,
    cfg: SimulationConfig,
    genotype: np.ndarray | None = None,
    gene_start: int | None = None,
    computation_load: np.ndarray | None = None,
    receptor_blocked: bool = False,
    state_clamps: dict[str, float] | None = None,
) -> PhysiologyStepStats:
    """Advance versioned physiology with explicit resource conservation."""

    rows = np.asarray(active, dtype=np.int32)
    if rows.size == 0:
        return PhysiologyStepStats()
    output = np.asarray(output_q, dtype=np.int32)
    if output.shape != (rows.size, PHYSIOLOGICAL_OUTPUT_COUNT):
        raise ValueError("active physiology output shape mismatch")
    moved_values = np.asarray(moved, dtype=bool)
    signal_values = np.asarray(signaled, dtype=bool)
    if moved_values.shape != (rows.size,) or signal_values.shape != (rows.size,):
        raise ValueError("physiology activity masks must align with active rows")
    local_o2 = np.clip(np.asarray(local_oxygen, dtype=np.float64), 0.0, 1.0)
    terrain = np.clip(np.asarray(local_terrain, dtype=np.float64), 0.0, 1.0)
    wear = np.clip(np.asarray(local_wear, dtype=np.float64), 0.0, 1.0)
    if any(values.shape != (rows.size,) for values in (local_o2, terrain, wear)):
        raise ValueError("physiology environment vectors must align")

    if regulatory_physiology_enabled(cfg):
        if genotype is None or gene_start is None:
            raise ValueError("v5 regulatory physiology requires genotype and gene_start")
        load = (
            np.zeros(rows.size, dtype=np.float64)
            if computation_load is None
            else np.asarray(computation_load, dtype=np.float64)
        )
        if load.shape != (rows.size,):
            raise ValueError("computation load must align with active rows")
        return _apply_v5_physiology_step(
            entities,
            rows,
            genotype=np.asarray(genotype, dtype=np.float32),
            gene_start=int(gene_start),
            output=output,
            local_o2=local_o2,
            terrain=terrain,
            wear=wear,
            moved_values=moved_values,
            signal_values=signal_values,
            computation_load=load,
            cfg=cfg,
            receptor_blocked=bool(receptor_blocked),
            state_clamps=state_clamps,
            conservative=conservative_regulatory_physiology_enabled(cfg),
        )
    return _apply_v4_physiology_step(
        entities,
        rows,
        output=output,
        local_o2=local_o2,
        terrain=terrain,
        wear=wear,
        moved_values=moved_values,
        signal_values=signal_values,
        cfg=cfg,
    )


__all__ = [
    "PhysiologyMultipliers",
    "PhysiologyStepStats",
    "RegulatoryMultipliers",
    "apply_physiology_step",
    "physiology_multipliers",
    "regulatory_multipliers",
    "validate_conservative_flow_ledger",
]
