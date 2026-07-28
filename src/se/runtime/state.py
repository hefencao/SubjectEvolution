"""Entity storage and per-step result types for the simulation runtime."""

from __future__ import annotations

from dataclasses import dataclass, field
import numpy as np

from ..cfg import SimulationConfig
from ..differentiation.capacity import (
    CapacityPhenotype,
    capacity_development_energy,
    capacity_gene_count,
    capacity_phenotype,
    neutral_capacity_phenotype,
)
from ..differentiation.functional import (
    functional_module_energy,
    functional_module_gene_count,
)
from ..differentiation.physiology import (
    physiology_gene_count,
    physiology_genome_energy,
    resource_metabolism_enabled,
)
from se.evolution.progress import BENEFIT_FLOW_COUNT, BenefitFlowKind
from se.knowledge import KnowledgeStepStats
from se.evolution.lifecycle import BirthAllocationPlan, DeathCause, DeathEventPlan
from ..policy import ParametricPolicy
from ..random_api import RandomContext, Stream, bernoulli, normal, uniform01

def _wrap_periodic_float32(values: np.ndarray, extent: float) -> np.ndarray:
    """Canonicalize float32 coordinates to the half-open interval ``[0, extent)``.

    ``numpy.remainder`` can round a tiny negative float32 coordinate to exactly
    ``extent`` (for example ``-1e-7 % 256 == 256.0``).  That value is
    topologically equivalent to zero in a periodic world but violates the
    world's half-open coordinate invariant and can produce an invalid spatial
    cell before the next repair.  Perform the ordinary remainder first, then
    map the rounded upper endpoint back to zero.  NaNs are deliberately left
    untouched so validation still reports them.
    """

    array = np.asarray(values)
    if array.dtype != np.float32:
        raise TypeError("periodic position buffers must use float32")
    extent32 = np.float32(extent)
    if not np.isfinite(extent32) or extent32 <= 0.0:
        raise ValueError("periodic extent must be finite and positive")
    wrapped = np.remainder(array, extent32).astype(np.float32, copy=False)
    rounded_upper = wrapped >= extent32
    if np.any(rounded_upper):
        wrapped = wrapped.copy()
        wrapped[rounded_upper] = np.float32(0.0)
    return wrapped


@dataclass
class StepStats:
    births: int = 0
    deaths: int = 0
    harvested_energy: float = 0.0
    harvested_resources: np.ndarray = field(
        default_factory=lambda: np.zeros(4, dtype=np.float64)
    )
    requested_harvest_resources: np.ndarray = field(
        default_factory=lambda: np.zeros(4, dtype=np.float64)
    )
    unconstrained_harvest_requests: np.ndarray = field(
        default_factory=lambda: np.zeros(4, dtype=np.float64)
    )
    resource_intake_capacity_rejected: np.ndarray = field(
        default_factory=lambda: np.zeros(4, dtype=np.float64)
    )
    resource_stored: np.ndarray = field(
        default_factory=lambda: np.zeros(4, dtype=np.float64)
    )
    resource_store_overflow: np.ndarray = field(
        default_factory=lambda: np.zeros(4, dtype=np.float64)
    )
    resource_converted: np.ndarray = field(
        default_factory=lambda: np.zeros(4, dtype=np.float64)
    )
    resource_store_decay: np.ndarray = field(
        default_factory=lambda: np.zeros(4, dtype=np.float64)
    )
    resource_store_death_loss: np.ndarray = field(
        default_factory=lambda: np.zeros(4, dtype=np.float64)
    )
    resource_residue_deposited: np.ndarray = field(
        default_factory=lambda: np.zeros(4, dtype=np.float64)
    )
    resource_residue_released: np.ndarray = field(
        default_factory=lambda: np.zeros(4, dtype=np.float64)
    )
    resource_body_realized: np.ndarray = field(
        default_factory=lambda: np.zeros(5, dtype=np.float64)
    )
    shared_energy: float = 0.0
    capacity_maintenance_energy: float = 0.0
    capacity_development_energy: float = 0.0
    functional_module_maintenance_energy: float = 0.0
    functional_module_development_energy: float = 0.0
    functional_module_movement_energy: float = 0.0
    functional_module_signal_energy: float = 0.0
    functional_module_repair_energy: float = 0.0
    functional_module_repair_material: float = 0.0
    functional_module_repair_integrity: float = 0.0
    physiology_capacity_maintenance_energy: float = 0.0
    physiology_capacity_development_energy: float = 0.0
    physiology_oxygen_uptake: float = 0.0
    physiology_oxygen_use: float = 0.0
    physiology_perfusion_energy: float = 0.0
    physiology_repair_energy: float = 0.0
    physiology_repair_material: float = 0.0
    physiology_repair_oxygen: float = 0.0
    physiology_repair_tissue: float = 0.0
    physiology_repair_structure: float = 0.0
    physiology_repair_integrity: float = 0.0
    physiology_hypoxia_tissue_damage: float = 0.0
    physiology_wear_tissue_damage: float = 0.0
    physiology_wear_structure_damage: float = 0.0
    physiology_integrity_damage: float = 0.0
    physiology_messenger_synthesis: float = 0.0
    physiology_messenger_decay: float = 0.0
    physiology_messenger_precursor_used: float = 0.0
    physiology_messenger_precursor_recovered: float = 0.0
    physiology_messenger_energy: float = 0.0
    physiology_computation_energy: float = 0.0
    physiology_computation_oxygen: float = 0.0
    physiology_fatigue_generated: float = 0.0
    physiology_fatigue_cleared: float = 0.0
    benefit_flow_energy: np.ndarray = field(
        default_factory=lambda: np.zeros(BENEFIT_FLOW_COUNT, dtype=np.float64)
    )
    lagged_benefit_flow_energy: np.ndarray = field(
        default_factory=lambda: np.zeros(BENEFIT_FLOW_COUNT, dtype=np.float64)
    )
    reproduction_eligible: int = 0
    reproduction_proposals: int = 0
    reproduction_accepted: int = 0
    reproduction_rejected_capacity: int = 0
    reproduction_rejected_resource: int = 0
    reproduction_rejected_other: int = 0
    signals: int = 0
    group_count: int = 0
    mean_group_size: float = 0.0
    group_updated: int = 0
    action_entropy: float = 0.0
    signal_detection_rate: float = 0.0
    partner_detection_rate: float = 0.0
    move_social_fraction: float = 0.0
    heuristic_guidance_actions: int = 0
    direct_messages: int = 0
    environment_seconds: float = 0.0
    spatial_seconds: float = 0.0
    observation_seconds: float = 0.0
    policy_seconds: float = 0.0
    conflict_seconds: float = 0.0
    graph_seconds: float = 0.0
    device_commit_seconds: float = 0.0
    evolution_evaluation_seconds: float = 0.0
    gpu_h2d_bytes: int = 0
    gpu_d2h_bytes: int = 0
    gpu_direct_message_events: int = 0
    gpu_direct_dense_bytes_avoided: int = 0
    gpu_entity_commit_bytes: int = 0
    autonomy_module_actions: int = 0
    autonomy_restored_active: int = 0
    autonomy_harvest_attempts: int = 0
    autonomy_harvest_successes: int = 0
    knowledge: KnowledgeStepStats = field(default_factory=KnowledgeStepStats)
    validation_seconds: float = 0.0
    knowledge_policy_max_abs_residual: float = 0.0

    @property
    def benefit_internal_energy(self) -> float:
        return float(self.benefit_flow_energy[BenefitFlowKind.INTERNAL])

    @property
    def benefit_cross_boundary_energy(self) -> float:
        return float(
            self.benefit_flow_energy[BenefitFlowKind.GROUP_TO_GROUP]
            + self.benefit_flow_energy[BenefitFlowKind.GROUP_TO_UNGROUPED]
            + self.benefit_flow_energy[BenefitFlowKind.UNGROUPED_TO_GROUP]
        )

    @property
    def benefit_unbounded_energy(self) -> float:
        return float(self.benefit_flow_energy[BenefitFlowKind.UNBOUNDED])


class EntityState:
    MEMORY_SIZE = 4

    def __init__(self, cfg: SimulationConfig) -> None:
        self.cfg = cfg
        cap = cfg.world.max_entities
        initial = cfg.world.initial_entities
        self.entity_id = np.zeros(cap, dtype=np.uint64)
        self.alive = np.zeros(cap, dtype=bool)
        self.x = np.zeros(cap, dtype=np.float32)
        self.y = np.zeros(cap, dtype=np.float32)
        self.vx = np.zeros(cap, dtype=np.float32)
        self.vy = np.zeros(cap, dtype=np.float32)
        self.energy = np.zeros(cap, dtype=np.float32)
        self.integrity = np.zeros(cap, dtype=np.float32)
        self.oxygenation = np.ones(cap, dtype=np.float32)
        self.tissue_condition = np.ones(cap, dtype=np.float32)
        self.structure_condition = np.ones(cap, dtype=np.float32)
        self.metabolic_fatigue = np.zeros(cap, dtype=np.float32)
        self.mobilization_messenger = np.zeros(cap, dtype=np.float32)
        self.maintenance_messenger = np.zeros(cap, dtype=np.float32)
        self.messenger_precursor = np.ones(cap, dtype=np.float32)
        self.physiology_sensor_multiplier = np.ones(cap, dtype=np.float32)
        if resource_metabolism_enabled(cfg):
            self.resource_store = np.zeros((cap, 4), dtype=np.float32)
        self.material = np.zeros(cap, dtype=np.float32)
        self.information_store = np.zeros(cap, dtype=np.float32)
        self.fertility = np.zeros(cap, dtype=np.float32)
        self.age = np.zeros(cap, dtype=np.uint32)
        self.generation = np.zeros(cap, dtype=np.uint32)
        self.lineage_id = np.zeros(cap, dtype=np.uint64)
        self.primary_subject_id = np.zeros(cap, dtype=np.uint64)
        self.lineage_subject_id = np.zeros(cap, dtype=np.uint64)
        self.genotype_size = ParametricPolicy.genome_size_for_config(cfg)
        self.genotype = np.zeros((cap, self.genotype_size), dtype=np.float32)
        self.working_memory_capacity = np.zeros(cap, dtype=np.uint16)
        self.knowledge_capacity_bytes = np.zeros(cap, dtype=np.uint32)
        self.relation_capacity = np.zeros(cap, dtype=np.uint16)
        self.knowledge_attention_capacity = np.zeros(cap, dtype=np.uint16)
        self.memory = np.zeros((cap, self.MEMORY_SIZE), dtype=np.float32)
        self.working_memory_q = np.zeros(
            (cap, int(cfg.knowledge.working_memory_width)), dtype=np.int16
        )
        self.working_memory_previous_observation_q = np.zeros(
            (cap, 4), dtype=np.int16
        )
        self.harvested_energy_total = np.zeros(cap, dtype=np.float32)
        self.shared_energy_received_total = np.zeros(cap, dtype=np.float32)
        self.next_entity_id = np.uint64(initial + 1)
        self.free_slots = list(range(cap - 1, initial - 1, -1))
        self.free_slot_version = 0

        ids = np.arange(1, initial + 1, dtype=np.uint64)
        idx = np.arange(initial, dtype=np.int32)
        self.entity_id[idx] = ids
        self.lineage_id[idx] = ids
        self.alive[idx] = True
        init_ctx = RandomContext(cfg.run.seed, 0, phase=0, stream=Stream.ENV_RESOURCE)
        self.x[idx] = (uniform01(init_ctx, ids, 0) * cfg.world.width).astype(np.float32)
        self.y[idx] = (uniform01(init_ctx, ids, 1) * cfg.world.height).astype(np.float32)
        if cfg.world.periodic:
            self.x[idx] = _wrap_periodic_float32(self.x[idx], cfg.world.width)
            self.y[idx] = _wrap_periodic_float32(self.y[idx], cfg.world.height)
        self.energy[idx] = np.clip(
            cfg.entities.initial_energy + normal(init_ctx, ids, 0.0, 0.15, 2),
            0.5,
            cfg.entities.max_energy,
        ).astype(np.float32)
        self.integrity[idx] = 1.0
        self.oxygenation[idx] = np.float32(cfg.physiology.initial_oxygenation)
        self.tissue_condition[idx] = np.float32(cfg.physiology.initial_tissue_condition)
        self.structure_condition[idx] = np.float32(cfg.physiology.initial_structure_condition)
        self.metabolic_fatigue[idx] = np.float32(cfg.physiology.initial_metabolic_fatigue)
        self.mobilization_messenger[idx] = np.float32(cfg.physiology.initial_mobilization_messenger)
        self.maintenance_messenger[idx] = np.float32(cfg.physiology.initial_maintenance_messenger)
        self.messenger_precursor[idx] = np.float32(cfg.physiology.initial_messenger_precursor)
        self.physiology_sensor_multiplier[idx] = 1.0
        self.fertility[idx] = 0.25
        for trait in range(self.genotype_size):
            self.genotype[idx, trait] = np.clip(
                normal(init_ctx, ids, 0.0, 0.25, 10 + trait * 2), -0.8, 0.8
            ).astype(np.float32)
        self.refresh_capacity_phenotype(idx)

    def capacity_phenotype(self, indices: np.ndarray | None = None) -> CapacityPhenotype:
        rows = (
            np.arange(self.alive.size, dtype=np.int32)
            if indices is None
            else np.asarray(indices, dtype=np.int32)
        )
        return CapacityPhenotype(
            working_memory_dimensions=self.working_memory_capacity[rows].astype(np.int32),
            knowledge_capacity_bytes=self.knowledge_capacity_bytes[rows].astype(np.int32),
            relation_slots=self.relation_capacity[rows].astype(np.int32),
            knowledge_attention_slots=self.knowledge_attention_capacity[rows].astype(np.int32),
        )

    def refresh_capacity_phenotype(self, indices: np.ndarray) -> CapacityPhenotype:
        rows = np.asarray(indices, dtype=np.int32)
        if rows.size == 0:
            return self.capacity_phenotype(rows)
        phenotype = capacity_phenotype(
            self.genotype[rows],
            self.cfg,
            gene_start=ParametricPolicy.capacity_gene_start(self.cfg),
        )
        self.working_memory_capacity[rows] = np.asarray(
            phenotype.working_memory_dimensions, dtype=np.uint16
        )
        self.knowledge_capacity_bytes[rows] = np.asarray(
            phenotype.knowledge_capacity_bytes, dtype=np.uint32
        )
        self.relation_capacity[rows] = np.asarray(
            phenotype.relation_slots, dtype=np.uint16
        )
        self.knowledge_attention_capacity[rows] = np.asarray(
            phenotype.knowledge_attention_slots, dtype=np.uint16
        )
        return self.capacity_phenotype(rows)

    def neutralize_capacity_phenotype(self, indices: np.ndarray) -> CapacityPhenotype:
        """Replace effective capacities by configured midpoint levels without editing genes."""
        rows = np.asarray(indices, dtype=np.int32)
        if rows.size == 0:
            return self.capacity_phenotype(rows)
        phenotype = neutral_capacity_phenotype(rows.size, self.cfg.differentiation)
        self.working_memory_capacity[rows] = np.asarray(
            phenotype.working_memory_dimensions, dtype=np.uint16
        )
        self.knowledge_capacity_bytes[rows] = np.asarray(
            phenotype.knowledge_capacity_bytes, dtype=np.uint32
        )
        self.relation_capacity[rows] = np.asarray(
            phenotype.relation_slots, dtype=np.uint16
        )
        self.knowledge_attention_capacity[rows] = np.asarray(
            phenotype.knowledge_attention_slots, dtype=np.uint16
        )
        width = int(self.working_memory_q.shape[1])
        capacity = self.working_memory_capacity[rows].astype(np.int32)
        if width:
            invalid = np.arange(width, dtype=np.int32)[None, :] >= capacity[:, None]
            current = self.working_memory_q[rows].copy()
            previous = self.working_memory_previous_observation_q[rows].copy()
            current[invalid] = 0
            previous[invalid] = 0
            self.working_memory_q[rows] = current
            self.working_memory_previous_observation_q[rows] = previous
        return self.capacity_phenotype(rows)

    def sensor_quality(self) -> np.ndarray:
        quality = np.clip(
            1.0 + 0.35 * self.genotype[:, 0] + 0.15 * self.information_store,
            0.1,
            2.0,
        )
        if self.cfg.physiology.enabled:
            support = np.sqrt(
                np.clip(
                    self.oxygenation.astype(np.float64)
                    * self.tissue_condition.astype(np.float64)
                    * self.structure_condition.astype(np.float64),
                    0.0,
                    1.0,
                )
            )
            quality = (
                quality
                * np.clip(0.25 + 0.75 * support, 0.25, 1.0)
                * np.clip(self.physiology_sensor_multiplier, 0.1, 2.0)
            )
        return np.clip(quality, 0.1, 2.0).astype(np.float32)

    def commit_births(
        self,
        plan: BirthAllocationPlan,
        mutation_std: float | None = None,
    ) -> tuple[np.ndarray, np.ndarray]:
        """Validate and commit one preallocated birth plan exactly once."""
        requests = plan.requests
        arrays = (
            requests.source_rows,
            requests.parent_indices,
            requests.parent_entity_ids,
            requests.parent_subject_ids,
            plan.slots,
            plan.offspring_entity_ids,
        )
        values = tuple(np.asarray(value) for value in arrays)
        if any(value.ndim != 1 for value in values):
            raise ValueError("birth allocation arrays must be one-dimensional")
        count = plan.size
        if requests.size != count or any(value.size != count for value in values):
            raise ValueError("birth allocation arrays must have the same length")
        if any(not np.issubdtype(value.dtype, np.integer) for value in values):
            raise ValueError("birth allocation arrays must use integer dtypes")
        if int(requests.tick) < 0:
            raise ValueError("birth allocation tick must be non-negative")
        if requests.capacity_arbitration not in {
            "unspecified",
            self.cfg.entities.reproduction_capacity_arbitration,
        }:
            raise ValueError(
                "birth allocation capacity arbitration does not match world model rule"
            )
        if count <= 0:
            return np.empty(0, dtype=np.int32), np.empty(0, dtype=np.int32)
        if int(plan.free_pool_version) != self.free_slot_version:
            raise ValueError("birth allocation free-slot pool version is stale")
        parents = values[1].astype(np.int32, copy=False)
        slots = values[4].astype(np.int32, copy=False)
        ids = values[5].astype(np.uint64, copy=False)
        capacity = self.alive.size
        if (
            np.any(parents < 0)
            or np.any(parents >= capacity)
            or np.any(slots < 0)
            or np.any(slots >= capacity)
            or np.unique(slots).size != count
        ):
            raise ValueError("birth allocation contains an invalid parent or slot")
        if not np.all(self.alive[parents]) or np.any(self.alive[slots]):
            raise ValueError("birth allocation does not match current entity occupancy")
        if not np.array_equal(self.entity_id[parents], requests.parent_entity_ids):
            raise ValueError("birth allocation parent entity IDs are stale")
        if not np.array_equal(self.primary_subject_id[parents], requests.parent_subject_ids):
            raise ValueError("birth allocation parent subject IDs are stale")
        expected_slots = np.asarray(self.free_slots[-count:][::-1], dtype=np.int32)
        expected_ids = np.arange(
            int(self.next_entity_id), int(self.next_entity_id) + count, dtype=np.uint64
        )
        if not np.array_equal(slots, expected_slots):
            raise ValueError("birth allocation no longer matches the free-slot pool")
        if not np.array_equal(ids, expected_ids):
            raise ValueError("birth allocation no longer matches the stable-ID counter")
        del self.free_slots[-count:]
        self.free_slot_version += 1
        self.next_entity_id = np.uint64(int(self.next_entity_id) + count)
        self.entity_id[slots] = ids
        self.lineage_id[slots] = self.lineage_id[parents]
        self.alive[slots] = True
        self.age[slots] = 0
        self.generation[slots] = self.generation[parents] + np.uint32(1)
        self.integrity[slots] = 1.0
        self.oxygenation[slots] = np.float32(self.cfg.physiology.initial_oxygenation)
        self.tissue_condition[slots] = np.float32(self.cfg.physiology.initial_tissue_condition)
        self.structure_condition[slots] = np.float32(self.cfg.physiology.initial_structure_condition)
        self.metabolic_fatigue[slots] = np.float32(self.cfg.physiology.initial_metabolic_fatigue)
        self.mobilization_messenger[slots] = np.float32(self.cfg.physiology.initial_mobilization_messenger)
        self.maintenance_messenger[slots] = np.float32(self.cfg.physiology.initial_maintenance_messenger)
        self.messenger_precursor[slots] = np.float32(self.cfg.physiology.initial_messenger_precursor)
        self.physiology_sensor_multiplier[slots] = 1.0
        if resource_metabolism_enabled(self.cfg):
            self.resource_store[slots] = 0.0
        self.material[slots] = 0.0
        self.information_store[slots] = 0.0
        self.fertility[slots] = 0.05
        self.memory[slots] = 0.0
        self.working_memory_q[slots] = 0
        self.working_memory_previous_observation_q[slots] = 0
        self.harvested_energy_total[slots] = 0.0
        self.shared_energy_received_total[slots] = 0.0
        self.primary_subject_id[slots] = 0
        self.lineage_subject_id[slots] = 0

        tick = int(requests.tick)
        ctx = RandomContext(self.cfg.run.seed, tick, phase=70, stream=Stream.REPRODUCTION)
        self.x[slots] = self.x[parents] + normal(ctx, ids, 0.0, 0.35, 0).astype(np.float32)
        self.y[slots] = self.y[parents] + normal(ctx, ids, 0.0, 0.35, 2).astype(np.float32)
        if self.cfg.world.periodic:
            self.x[slots] = _wrap_periodic_float32(self.x[slots], self.cfg.world.width)
            self.y[slots] = _wrap_periodic_float32(self.y[slots], self.cfg.world.height)
        else:
            self.x[slots] = np.clip(self.x[slots], 0.0, self.cfg.world.width)
            self.y[slots] = np.clip(self.y[slots], 0.0, self.cfg.world.height)
        self.vx[slots] = 0.0
        self.vy[slots] = 0.0
        self.energy[slots] = self.cfg.entities.reproduction_cost * 0.45

        mut_ctx = RandomContext(self.cfg.run.seed, tick, phase=71, stream=Stream.MUTATION)
        mutation_stddev = (
            self.cfg.policy.mutation_std if mutation_std is None else mutation_std
        )
        capacity_start = ParametricPolicy.capacity_gene_start(self.cfg)
        capacity_stop = capacity_start + capacity_gene_count(self.cfg)
        functional_start = ParametricPolicy.functional_module_gene_start(self.cfg)
        functional_stop = functional_start + functional_module_gene_count(self.cfg)
        physiology_start = ParametricPolicy.physiology_gene_start(self.cfg)
        physiology_stop = physiology_start + physiology_gene_count(self.cfg)
        for trait in range(self.genotype_size):
            capacity_trait = capacity_start <= trait < capacity_stop
            functional_trait = functional_start <= trait < functional_stop
            physiology_trait = physiology_start <= trait < physiology_stop
            if capacity_trait:
                mutation_probability = self.cfg.differentiation.mutation_probability
                trait_mutation_std = (
                    0.0 if mutation_std is not None else self.cfg.differentiation.mutation_std
                )
            elif functional_trait:
                mutation_probability = self.cfg.functional_modules.mutation_probability
                trait_mutation_std = (
                    0.0 if mutation_std is not None else self.cfg.functional_modules.mutation_std
                )
            elif physiology_trait:
                mutation_probability = self.cfg.physiology.gene_mutation_probability
                trait_mutation_std = (
                    0.0 if mutation_std is not None else self.cfg.physiology.gene_mutation_std
                )
            else:
                mutation_probability = self.cfg.policy.mutation_probability
                trait_mutation_std = mutation_stddev
            mutate = bernoulli(
                mut_ctx,
                ids,
                mutation_probability,
                draw_index=trait * 3,
                validate_probability=False,
            )
            mutation = normal(
                mut_ctx,
                ids,
                0.0,
                trait_mutation_std,
                draw_index=trait * 3 + 1,
                validate_stddev=False,
            )
            self.genotype[slots, trait] = np.clip(
                self.genotype[parents, trait] + np.where(mutate, mutation, 0.0),
                -1.5,
                1.5,
            ).astype(np.float32)
        phenotype = self.refresh_capacity_phenotype(slots)
        if self.cfg.differentiation.enabled:
            development_cost = np.asarray(
                capacity_development_energy(phenotype, self.cfg.differentiation),
                dtype=np.float64,
            )
            self.energy[slots] = np.maximum(
                self.energy[slots].astype(np.float64) - development_cost,
                0.0,
            ).astype(np.float32)
        if self.cfg.functional_modules.enabled:
            module_cost = functional_module_energy(
                self.genotype[slots],
                self.cfg,
                gene_start=ParametricPolicy.functional_module_gene_start(self.cfg),
                development=True,
            )
            self.energy[slots] = np.maximum(
                self.energy[slots].astype(np.float64) - module_cost,
                0.0,
            ).astype(np.float32)
        physiology_cost = physiology_genome_energy(
            self.genotype[slots],
            self.cfg,
            gene_start=ParametricPolicy.physiology_gene_start(self.cfg),
            development=True,
        )
        if np.any(physiology_cost):
            self.energy[slots] = np.maximum(
                self.energy[slots].astype(np.float64) - physiology_cost,
                0.0,
            ).astype(np.float32)
        return parents, slots

    def commit_deaths(self, plan: DeathEventPlan) -> np.ndarray:
        """Commit canonical death events and reclaim their slots at phase end."""
        indices = np.asarray(plan.entity_indices, dtype=np.int32)
        arrays = (
            indices,
            plan.entity_ids,
            plan.primary_subject_ids,
            plan.cause_code,
            plan.final_energy,
            plan.final_integrity,
        )
        if any(np.asarray(value).ndim != 1 for value in arrays):
            raise ValueError("death event arrays must be one-dimensional")
        if len({np.asarray(value).size for value in arrays}) != 1:
            raise ValueError("death event arrays must have the same length")
        if indices.size == 0:
            return indices
        if (
            np.any(indices < 0)
            or np.any(indices >= self.alive.size)
            or np.any(indices[1:] <= indices[:-1])
            or not np.all(self.alive[indices])
        ):
            raise ValueError("death event plan does not match current occupancy")
        if not np.array_equal(self.entity_id[indices], plan.entity_ids):
            raise ValueError("death event entity IDs are stale")
        if not np.array_equal(self.primary_subject_id[indices], plan.primary_subject_ids):
            raise ValueError("death event subject IDs are stale")
        cause = np.asarray(plan.cause_code, dtype=np.uint8)
        expected_cause = (
            (self.energy[indices] <= 0.0).astype(np.uint8)
            * int(DeathCause.ENERGY_DEPLETED)
            | (self.integrity[indices] <= 0.0).astype(np.uint8)
            * int(DeathCause.INTEGRITY_DEPLETED)
            | (self.age[indices] >= self.cfg.entities.max_age).astype(np.uint8)
            * int(DeathCause.MAX_AGE)
        ).astype(np.uint8)
        if not np.array_equal(cause, expected_cause) or np.any(cause == 0):
            raise ValueError("death event cause does not match current entity state")
        if not np.array_equal(self.energy[indices], plan.final_energy) or not np.array_equal(
            self.integrity[indices], plan.final_integrity
        ):
            raise ValueError("death event final state is stale")
        self.alive[indices] = False
        if resource_metabolism_enabled(self.cfg):
            self.resource_store[indices] = 0.0
        self.memory[indices] = 0.0
        self.working_memory_q[indices] = 0
        self.working_memory_previous_observation_q[indices] = 0
        self.working_memory_capacity[indices] = 0
        self.knowledge_capacity_bytes[indices] = 0
        self.relation_capacity[indices] = 0
        self.knowledge_attention_capacity[indices] = 0
        self.free_slots.extend(indices.tolist())
        self.free_slot_version += 1
        self.entity_id[indices] = 0
        self.oxygenation[indices] = 0.0
        self.tissue_condition[indices] = 0.0
        self.structure_condition[indices] = 0.0
        self.metabolic_fatigue[indices] = 0.0
        self.mobilization_messenger[indices] = 0.0
        self.maintenance_messenger[indices] = 0.0
        self.messenger_precursor[indices] = 0.0
        self.physiology_sensor_multiplier[indices] = 1.0
        self.vx[indices] = 0.0
        self.vy[indices] = 0.0
        return indices




# Preserve the historical pickle/import identity used by trusted checkpoints.

__all__ = ["EntityState", "StepStats", "_wrap_periodic_float32"]
