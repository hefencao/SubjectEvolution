from __future__ import annotations

from typing import Any

import numpy as np

from se.differentiation.functional import (
    embodied_outputs_enabled,
    evaluate_contextual_harvest_modules_q,
    functional_module_diagnostics,
    physiological_outputs_enabled,
    regulatory_outputs_enabled,
)
from se.policy import ParametricPolicy
from se.runtime.embodied import embodied_power_multipliers
from se.differentiation.physiology import (
    physiology_genome_energy,
    physiology_phenotype,
    resource_metabolism_enabled,
)
from se.runtime.physiology import (
    apply_physiology_step,
    physiology_multipliers,
    regulatory_multipliers,
)


_PHYSIOLOGY_STAT_FIELDS = (
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


def evaluate_functional_outputs(
    simulation: Any,
    *,
    active: np.ndarray,
    effective_resource_affinity_q: np.ndarray,
    local_resources: np.ndarray,
    local_physiology: np.ndarray,
    evaluation_due: bool,
    effective_harvest_preference_q: np.ndarray,
    effective_embodied_output_q: np.ndarray,
    effective_physiology_output_q: np.ndarray,
    functional_computation_load: np.ndarray,
    movement_speed_multiplier: np.ndarray,
    signal_strength_multiplier: np.ndarray,
) -> dict[str, object]:
    """Evaluate versioned functional modules and write their runtime outputs.

    This helper deliberately mutates the preallocated step arrays supplied by
    ``Simulation.step``.  Keeping the orchestration here prevents the main
    world loop from regrowing while preserving the exact ordering of the v1-v4
    phenotype path.
    """
    cfg = simulation.cfg
    ent = simulation.entities
    if not cfg.functional_modules.enabled:
        return {}

    physiology_phenotype_value = (
        physiology_phenotype(
            ent.genotype[active],
            cfg,
            gene_start=ParametricPolicy.physiology_gene_start(cfg),
        )
        if regulatory_outputs_enabled(cfg)
        else None
    )
    resource_store = (
        ent.resource_store[active] if resource_metabolism_enabled(cfg) else None
    )
    resource_store_capacity = (
        physiology_phenotype_value.resource_store_capacity
        if resource_metabolism_enabled(cfg) and physiology_phenotype_value is not None
        else None
    )

    evaluation = evaluate_contextual_harvest_modules_q(
        ent.genotype[active],
        effective_resource_affinity_q[active],
        energy=ent.energy[active],
        integrity=ent.integrity[active],
        material=ent.material[active],
        information_store=ent.information_store[active],
        fertility=ent.fertility[active],
        local_resources=local_resources,
        oxygenation=ent.oxygenation[active],
        tissue_condition=ent.tissue_condition[active],
        structure_condition=ent.structure_condition[active],
        metabolic_fatigue=ent.metabolic_fatigue[active],
        mobilization_messenger=ent.mobilization_messenger[active],
        maintenance_messenger=ent.maintenance_messenger[active],
        messenger_precursor=ent.messenger_precursor[active],
        resource_store=resource_store,
        resource_store_capacity=resource_store_capacity,
        local_oxygen=local_physiology[:, 0],
        local_terrain=local_physiology[:, 1],
        local_wear=local_physiology[:, 2],
        cfg=cfg,
        gene_start=ParametricPolicy.functional_module_gene_start(cfg),
        ablated=simulation.functional_modules_ablation_enabled,
        ablated_modules=simulation.functional_module_ablation_mask,
        row_ablated_modules=simulation.functional_module_lineage_ablation_mask(
            active, cost=False
        ),
        coupling_ablated=simulation.functional_module_coupling_ablation_enabled,
        embodied_ablated=simulation.functional_module_embodied_output_ablation_enabled,
        physiology_ablated=simulation.functional_module_physiology_output_ablation_enabled,
    )
    active_preference = evaluation.preference_q
    effective_harvest_preference_q[active] = active_preference
    if evaluation.computation_load is not None:
        functional_computation_load[active] = np.asarray(
            evaluation.computation_load, dtype=np.float32
        )

    if evaluation.embodied_output_q is not None:
        active_embodied_q = np.asarray(evaluation.embodied_output_q, dtype=np.int32)
        effective_embodied_output_q[active] = active_embodied_q
        if embodied_outputs_enabled(cfg):
            movement, signal = embodied_power_multipliers(active_embodied_q, cfg)
            movement_speed_multiplier[active] = movement
            signal_strength_multiplier[active] = signal

    if evaluation.physiology_output_q is not None:
        active_physiology_q = np.asarray(evaluation.physiology_output_q, dtype=np.int32)
        effective_physiology_output_q[active] = active_physiology_q
        if physiological_outputs_enabled(cfg):
            multipliers = physiology_multipliers(
                active_physiology_q,
                ent.oxygenation[active],
                ent.tissue_condition[active],
                ent.structure_condition[active],
                local_physiology[:, 1],
                cfg,
            )
            movement_speed_multiplier[active] = multipliers.movement
            signal_strength_multiplier[active] = multipliers.signal
            ent.physiology_sensor_multiplier[active] = multipliers.sensor
        elif regulatory_outputs_enabled(cfg):
            if physiology_phenotype_value is None:
                raise RuntimeError("regulatory physiology phenotype was not prepared")
            multipliers = regulatory_multipliers(
                active_physiology_q,
                oxygenation=ent.oxygenation[active],
                metabolic_fatigue=ent.metabolic_fatigue[active],
                tissue_condition=ent.tissue_condition[active],
                structure_condition=ent.structure_condition[active],
                mobilization_messenger=ent.mobilization_messenger[active],
                maintenance_messenger=ent.maintenance_messenger[active],
                local_terrain=local_physiology[:, 1],
                phenotype=physiology_phenotype_value,
                cfg=cfg,
                receptor_blocked=simulation.physiology_messenger_receptor_blockade_enabled,
            )
            movement_speed_multiplier[active] = multipliers.movement
            signal_strength_multiplier[active] = multipliers.signal
            ent.physiology_sensor_multiplier[active] = multipliers.sensor

    if not evaluation_due:
        return {}
    diagnostics = functional_module_diagnostics(
        ent.genotype[active],
        active_preference,
        effective_resource_affinity_q[active],
        cfg,
        gene_start=ParametricPolicy.functional_module_gene_start(cfg),
        evaluation=evaluation,
    )
    simulation.last_functional_module_changed_entity_fraction = float(
        diagnostics.get("functional_module_changed_entity_fraction", 0.0)
    )
    simulation.last_functional_module_residual_effective_dimensions = float(
        diagnostics.get("functional_module_residual_effective_dimensions", 0.0)
    )
    simulation.last_functional_physiology_output_changed_entity_fraction = float(
        diagnostics.get("functional_physiology_output_changed_entity_fraction", 0.0)
    )
    simulation.last_functional_physiology_output_effective_dimensions = float(
        diagnostics.get("functional_physiology_output_effective_dimensions", 0.0)
    )
    return diagnostics


def record_physiology_capacity_development_cost(
    simulation: Any, newborns: np.ndarray, stats: Any
) -> None:
    """Record newborn v5 structural cost already charged by ``EntityState``."""

    rows = np.asarray(newborns, dtype=np.int32)
    if rows.size == 0:
        return
    cfg = simulation.cfg
    cost = physiology_genome_energy(
        simulation.entities.genotype[rows],
        cfg,
        gene_start=ParametricPolicy.physiology_gene_start(cfg),
        development=True,
    )
    if np.any(cost):
        stats.physiology_capacity_development_energy = float(
            cost.sum(dtype=np.float64)
        )


def add_physiology_capacity_maintenance_cost(
    simulation: Any, active: np.ndarray, cost: np.ndarray, stats: Any
) -> np.ndarray:
    """Add inherited v5 transport/metabolism capacity maintenance cost."""

    rows = np.asarray(active, dtype=np.int32)
    if rows.size == 0:
        return np.asarray(cost, dtype=np.float64)
    cfg = simulation.cfg
    capacity_cost = physiology_genome_energy(
        simulation.entities.genotype[rows],
        cfg,
        gene_start=ParametricPolicy.physiology_gene_start(cfg),
        development=False,
    )
    if np.any(capacity_cost):
        stats.physiology_capacity_maintenance_energy = float(
            capacity_cost.sum(dtype=np.float64)
        )
        return np.asarray(cost, dtype=np.float64) + capacity_cost
    return np.asarray(cost, dtype=np.float64)

def add_physiology_terrain_cost(
    simulation: Any,
    *,
    current_active: np.ndarray,
    current_cells: np.ndarray,
    moved_now: np.ndarray,
    cost: np.ndarray | float,
) -> tuple[np.ndarray | float, np.ndarray, np.ndarray]:
    """Add the movement cost imposed by local terrain resistance."""
    cfg = simulation.cfg
    if not cfg.physiology.enabled:
        return cost, np.zeros((0, 3), dtype=np.float32), np.zeros(0, dtype=bool)
    current_physiology = (
        simulation.gpu_runtime.physiology_for_cells(current_cells)
        if simulation.gpu_runtime is not None
        else simulation.environment.physiology_for_cells(current_cells)
    )
    moved_current = moved_now[current_active]
    terrain_extra = (
        moved_current.astype(np.float64)
        * float(cfg.entities.movement_cost)
        * float(cfg.physiology.terrain_energy_cost_fraction)
        * current_physiology[:, 1].astype(np.float64)
    )
    return (
        np.asarray(cost, dtype=np.float64) + terrain_extra,
        current_physiology,
        moved_current,
    )


def apply_physiology_settlement(
    simulation: Any,
    *,
    current_active: np.ndarray,
    current_physiology: np.ndarray,
    moved_current: np.ndarray,
    signal_rows: np.ndarray,
    intents: Any,
    effective_physiology_output_q: np.ndarray,
    functional_computation_load: np.ndarray,
    stats: Any,
) -> None:
    """Settle oxygen, wear and repair after ordinary maintenance and hazard."""
    cfg = simulation.cfg
    if not cfg.physiology.enabled:
        return
    ent = simulation.entities
    signaled_now = np.zeros(ent.alive.size, dtype=bool)
    if signal_rows.size:
        signaled_now[intents.carrier_index[signal_rows]] = True
    physiology_stats = apply_physiology_step(
        ent,
        current_active,
        output_q=effective_physiology_output_q[current_active],
        local_oxygen=current_physiology[:, 0],
        local_terrain=current_physiology[:, 1],
        local_wear=current_physiology[:, 2],
        moved=moved_current,
        signaled=signaled_now[current_active],
        cfg=cfg,
        genotype=ent.genotype[current_active],
        gene_start=ParametricPolicy.physiology_gene_start(cfg),
        computation_load=functional_computation_load[current_active],
        receptor_blocked=simulation.physiology_messenger_receptor_blockade_enabled,
        state_clamps=simulation.physiology_state_clamps,
    )
    for field_name in _PHYSIOLOGY_STAT_FIELDS:
        value = float(getattr(physiology_stats, field_name))
        setattr(stats, f"physiology_{field_name}", value)
        total_name = f"total_physiology_{field_name}"
        setattr(
            simulation,
            total_name,
            float(getattr(simulation, total_name)) + value,
        )


def initialize_functional_runtime_state(simulation: Any) -> None:
    """Initialize cumulative functional/physiology flows and opt-in ablations."""
    for name in (
        "functional_module_movement_energy_delta",
        "functional_module_signal_energy_delta",
        "functional_module_repair_energy",
        "functional_module_repair_material",
        "functional_module_repair_integrity",
        "physiology_oxygen_uptake",
        "physiology_oxygen_use",
        "physiology_perfusion_energy",
        "physiology_repair_energy",
        "physiology_repair_material",
        "physiology_repair_oxygen",
        "physiology_repair_tissue",
        "physiology_repair_structure",
        "physiology_repair_integrity",
        "physiology_hypoxia_tissue_damage",
        "physiology_wear_tissue_damage",
        "physiology_wear_structure_damage",
        "physiology_integrity_damage",
        "physiology_messenger_synthesis",
        "physiology_messenger_decay",
        "physiology_messenger_precursor_used",
        "physiology_messenger_precursor_recovered",
        "physiology_messenger_energy",
        "physiology_computation_energy",
        "physiology_computation_oxygen",
        "physiology_fatigue_generated",
        "physiology_fatigue_cleared",
    ):
        setattr(simulation, f"total_{name}", 0.0)
    simulation.functional_module_embodied_output_ablation_enabled = False
    simulation.functional_module_physiology_output_ablation_enabled = False
    simulation.last_functional_module_changed_entity_fraction = 0.0
    simulation.last_functional_module_residual_effective_dimensions = 0.0
    simulation.last_functional_physiology_output_changed_entity_fraction = 0.0
    simulation.last_functional_physiology_output_effective_dimensions = 0.0
    simulation.physiology_messenger_receptor_blockade_enabled = False
    simulation.physiology_state_clamps = {}


def physiology_checkpoint_arrays(simulation: Any) -> dict[str, np.ndarray]:
    """Return the thin-checkpoint physiology state without bloating the loop."""
    active = np.flatnonzero(simulation.entities.alive)
    ent = simulation.entities
    environment = simulation.environment
    if simulation.gpu_runtime is None:
        environment_oxygen = environment.oxygen
        environment_terrain = environment.terrain
        environment_wear = environment.wear
    else:
        (
            environment_oxygen,
            environment_terrain,
            environment_wear,
        ) = simulation.gpu_runtime.physiology_fields_to_host()
    arrays = {
        "oxygenation": ent.oxygenation[active],
        "tissue_condition": ent.tissue_condition[active],
        "structure_condition": ent.structure_condition[active],
        "metabolic_fatigue": ent.metabolic_fatigue[active],
        "mobilization_messenger": ent.mobilization_messenger[active],
        "maintenance_messenger": ent.maintenance_messenger[active],
        "messenger_precursor": ent.messenger_precursor[active],
        "physiology_sensor_multiplier": ent.physiology_sensor_multiplier[active],
        "environment_oxygen": environment_oxygen,
        "environment_terrain": environment_terrain,
        "environment_wear": environment_wear,
    }
    if resource_metabolism_enabled(simulation.cfg):
        arrays["resource_store"] = ent.resource_store[active]
    return arrays


def augment_gradient_with_oxygen(
    simulation: Any,
    resource_gradient: tuple[np.ndarray, np.ndarray],
) -> tuple[np.ndarray, np.ndarray]:
    """Add oxygen-seeking pressure to the ordinary CPU resource gradient."""
    cfg = simulation.cfg
    if not cfg.physiology.enabled or cfg.physiology.oxygen_gradient_weight <= 0.0:
        return resource_gradient
    ent = simulation.entities
    oxygen_gx, oxygen_gy = simulation.environment.oxygen_gradient_for_entities(
        simulation.spatial.entity_cells, ent.alive.size
    )
    oxygen_need = np.clip(1.0 - ent.oxygenation, 0.0, 1.0)
    sensory_support = np.clip(ent.physiology_sensor_multiplier, 0.1, 2.0)
    weight = (
        np.float32(cfg.physiology.oxygen_gradient_weight)
        * oxygen_need
        * sensory_support
    )
    return (
        resource_gradient[0] + weight * oxygen_gx,
        resource_gradient[1] + weight * oxygen_gy,
    )


__all__ = [
    "add_physiology_terrain_cost",
    "augment_gradient_with_oxygen",
    "apply_physiology_settlement",
    "evaluate_functional_outputs",
    "initialize_functional_runtime_state",
    "physiology_checkpoint_arrays",
]
