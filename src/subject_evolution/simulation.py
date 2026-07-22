from __future__ import annotations

from dataclasses import dataclass, field
import copy
import json
from pathlib import Path
import time
import numpy as np

from . import __version__
from .backend import BackendUnavailableError
from .config import SimulationConfig
from .control import (
    AutonomyRecoveryArbiter,
    ControlArbiter,
    ControllerKind,
    HeuristicSocialGuidanceArbiter,
    SingleProposalControlArbiter,
    autonomy_recovery_control_proposal,
    body_control_proposal,
    social_guidance_control_proposal,
)
from .device_state import EntityDeviceCommitPlan, build_entity_device_commit_plan
from .environment import Environment
from .evolution import (
    BENEFIT_FLOW_COUNT,
    BenefitFlowKind,
    EvolutionProgressTracker,
    LaggedBenefitBoundary,
    actual_context_policy_diagnostics,
    benefit_flow_totals,
)
from .execution import (
    ActionConflictResolver,
    ActionResolutionSnapshot,
    DeterministicActionConflictResolver,
    GpuActionConflictResolver,
    ShareResolution,
)
from .gpu_runtime import HybridGpuRuntime
from .information import InformationSystem, SignalEmissionBatch, SignalEmissionPlan, SignalEmissionScheduler
from .interventions import ExperimentMode, resolve_intervention
from .intents import (
    ActionIntentBatch,
    ActionResolutionBatch,
    FailureReason,
    build_intents,
)
from .lifecycle import (
    BirthAllocationPlan,
    DeathCause,
    DeathEventPlan,
    empty_birth_allocation_plan,
    empty_death_event_plan,
    plan_birth_allocations,
    plan_death_events,
)
from .metrics import MetricsWriter
from .policy import Action, ParametricPolicy
from .random_api import RandomContext, Stream, bernoulli, normal, uniform01
from .social import (
    DeterministicGroupLabelPlanner,
    GroupLabelPlan,
    GroupLabelPlanner,
    GroupSummary,
    SocialSystem,
    ungrouped_group_label_plan,
)
from .spatial import SpatialIndex
from .subjects import CandidateSubjectGraph


@dataclass
class StepStats:
    births: int = 0
    deaths: int = 0
    harvested_energy: float = 0.0
    shared_energy: float = 0.0
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
    GENOTYPE_SIZE = ParametricPolicy.GENOME_SIZE
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
        self.material = np.zeros(cap, dtype=np.float32)
        self.information_store = np.zeros(cap, dtype=np.float32)
        self.fertility = np.zeros(cap, dtype=np.float32)
        self.age = np.zeros(cap, dtype=np.uint32)
        self.generation = np.zeros(cap, dtype=np.uint32)
        self.lineage_id = np.zeros(cap, dtype=np.uint64)
        self.primary_subject_id = np.zeros(cap, dtype=np.uint64)
        self.lineage_subject_id = np.zeros(cap, dtype=np.uint64)
        self.genotype = np.zeros((cap, self.GENOTYPE_SIZE), dtype=np.float32)
        self.memory = np.zeros((cap, self.MEMORY_SIZE), dtype=np.float32)
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
        self.energy[idx] = np.clip(
            cfg.entities.initial_energy + normal(init_ctx, ids, 0.0, 0.15, 2),
            0.5,
            cfg.entities.max_energy,
        ).astype(np.float32)
        self.integrity[idx] = 1.0
        self.fertility[idx] = 0.25
        for trait in range(self.GENOTYPE_SIZE):
            self.genotype[idx, trait] = np.clip(
                normal(init_ctx, ids, 0.0, 0.25, 10 + trait * 2), -0.8, 0.8
            ).astype(np.float32)

    def sensor_quality(self) -> np.ndarray:
        return np.clip(1.0 + 0.35 * self.genotype[:, 0] + 0.15 * self.information_store, 0.1, 2.0).astype(np.float32)

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
        self.material[slots] = 0.0
        self.information_store[slots] = 0.0
        self.fertility[slots] = 0.05
        self.memory[slots] = 0.0
        self.harvested_energy_total[slots] = 0.0
        self.shared_energy_received_total[slots] = 0.0
        self.primary_subject_id[slots] = 0
        self.lineage_subject_id[slots] = 0

        tick = int(requests.tick)
        ctx = RandomContext(self.cfg.run.seed, tick, phase=70, stream=Stream.REPRODUCTION)
        self.x[slots] = self.x[parents] + normal(ctx, ids, 0.0, 0.35, 0).astype(np.float32)
        self.y[slots] = self.y[parents] + normal(ctx, ids, 0.0, 0.35, 2).astype(np.float32)
        if self.cfg.world.periodic:
            self.x[slots] %= self.cfg.world.width
            self.y[slots] %= self.cfg.world.height
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
        for trait in range(self.GENOTYPE_SIZE):
            mutate = bernoulli(
                mut_ctx,
                ids,
                self.cfg.policy.mutation_probability,
                draw_index=trait * 3,
                validate_probability=False,
            )
            mutation = normal(
                mut_ctx,
                ids,
                0.0,
                mutation_stddev,
                draw_index=trait * 3 + 1,
                validate_stddev=False,
            )
            self.genotype[slots, trait] = np.clip(
                self.genotype[parents, trait] + np.where(mutate, mutation, 0.0),
                -1.5,
                1.5,
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
        self.free_slots.extend(indices.tolist())
        self.free_slot_version += 1
        self.entity_id[indices] = 0
        self.vx[indices] = 0.0
        self.vy[indices] = 0.0
        return indices


class Simulation:
    def __init__(
        self,
        cfg: SimulationConfig,
        output_dir: str | Path,
        *,
        backend: str = "cpu",
        conflict_resolver: ActionConflictResolver | None = None,
        control_arbiter: ControlArbiter | None = None,
        group_label_planner: GroupLabelPlanner | None = None,
    ) -> None:
        self.cfg = cfg
        self.experiment_mode = ExperimentMode(cfg.run.experiment_mode)
        if (
            self.experiment_mode is ExperimentMode.SCIENTIFIC
            and cfg.control.heuristic_social_guidance
        ):
            raise ValueError(
                "heuristic_social_guidance directly alters action direction and requires "
                "run.experiment_mode='entertainment'"
            )
        if (
            self.experiment_mode is ExperimentMode.SCIENTIFIC
            and control_arbiter is not None
            and not bool(getattr(control_arbiter, "scientific_safe", False))
        ):
            raise ValueError(
                f"control arbiter {type(control_arbiter).__name__} is not declared "
                "scientific_safe; use a reviewed arbiter or entertainment mode"
            )
        for component_name, component in (
            ("conflict resolver", conflict_resolver),
            ("group label planner", group_label_planner),
        ):
            if (
                self.experiment_mode is ExperimentMode.SCIENTIFIC
                and component is not None
                and not bool(getattr(component, "scientific_safe", False))
            ):
                raise ValueError(
                    f"{component_name} {type(component).__name__} is not declared "
                    "scientific_safe; use a reviewed component or entertainment mode"
                )
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.entities = EntityState(cfg)
        self.entity_device_version = 0
        self.environment = Environment(cfg)
        self.information = InformationSystem(cfg)
        # MVP channels flush every tick, exactly preserving current field
        # timing.  Longer periods are an explicit future model choice, not a
        # dense zero-column performance shortcut.
        self.signal_scheduler = SignalEmissionScheduler(
            self.information.CHANNELS,
            cfg.information.signal_flush_periods,
        )
        self.spatial = SpatialIndex(
            cfg.world.grid_x,
            cfg.world.grid_y,
            cfg.world.width,
            cfg.world.height,
            cfg.world.periodic,
        )
        requested_backend = backend.strip().lower()
        if requested_backend == "cpu":
            self.gpu_runtime: HybridGpuRuntime | None = None
            self.execution_backend = "cpu"
        elif requested_backend in {"gpu", "auto"}:
            try:
                self.gpu_runtime = HybridGpuRuntime(cfg, backend="gpu")
            except BackendUnavailableError:
                if requested_backend == "gpu":
                    raise
                self.gpu_runtime = None
            self.execution_backend = "gpu" if self.gpu_runtime is not None else "cpu"
        else:
            raise ValueError("backend must be one of: 'cpu', 'gpu', or 'auto'")
        if self.gpu_runtime is not None:
            self.gpu_runtime.sync_from_host(self.environment, self.information)
        self.social = SocialSystem(cfg, cfg.world.max_entities)
        if self.gpu_runtime is not None:
            self.gpu_runtime.sync_entity_from_host(
                self.entities,
                self.social,
                self.entity_device_version,
            )
        self.subjects = CandidateSubjectGraph(cfg.world.max_entities)
        initial = np.flatnonzero(self.entities.alive).astype(np.int32)
        body_subjects, lineage_subjects = self.subjects.register_bodies(
            initial, self.entities.lineage_id, tick=0
        )
        self.entities.primary_subject_id[initial] = body_subjects
        self.entities.lineage_subject_id[initial] = lineage_subjects
        self.policy = ParametricPolicy(cfg)
        self.metrics = MetricsWriter(self.output_dir)
        self.tick = 0
        self.last_group_summary = GroupSummary(
            np.empty(0, dtype=np.uint64), np.empty(0, dtype=np.int32), np.empty(0, dtype=np.float32)
        )
        self.last_group_plan: GroupLabelPlan = ungrouped_group_label_plan(
            initial,
            self.entities.entity_id[initial],
            tick=0,
        )
        self.total_births = 0
        self.total_deaths = 0
        self.total_shared_energy = 0.0
        self.action_counts = np.zeros(len(Action), dtype=np.int64)
        self.benefit_flow_energy_total = np.zeros(
            BENEFIT_FLOW_COUNT, dtype=np.float64
        )
        self.lagged_benefit_boundary = LaggedBenefitBoundary(
            cfg.world.max_entities
        )
        self.lagged_benefit_boundary.freeze(
            tick=0,
            alive=self.entities.alive,
            stable_ids=self.entities.entity_id,
            group_tokens=self.social.group_id,
        )
        self.total_reproduction_eligible = 0
        self.total_reproduction_proposals = 0
        self.total_reproduction_rejected_capacity = 0
        self.total_reproduction_rejected_resource = 0
        self.total_reproduction_rejected_other = 0
        self.evolution_progress = EvolutionProgressTracker(
            self.output_dir,
            period=cfg.run.evolution_evaluation_period,
            run_seed=cfg.run.seed,
            temperature=cfg.policy.temperature,
            alive=self.entities.alive,
            stable_ids=self.entities.entity_id,
            genotype=self.entities.genotype,
        )
        self.last_intents: ActionIntentBatch | None = None
        self.last_resolutions: ActionResolutionBatch | None = None
        self.last_birth_allocation = empty_birth_allocation_plan(0)
        self.last_death_events = empty_death_event_plan(0)
        self.last_entity_device_commit: EntityDeviceCommitPlan | None = None
        self.conflict_resolver = conflict_resolver
        if self.conflict_resolver is None:
            self.conflict_resolver = (
                GpuActionConflictResolver(cfg)
                if self.gpu_runtime is not None and cfg.run.gpu_harvest_conflict_planner
                else DeterministicActionConflictResolver(cfg)
            )
        if isinstance(self.conflict_resolver, GpuActionConflictResolver):
            if self.gpu_runtime is None:
                raise ValueError("GpuActionConflictResolver requires Simulation(..., backend='gpu')")
            self.conflict_resolver.bind_harvest_planner(self.gpu_runtime)
        self.control_arbiter = control_arbiter if control_arbiter is not None else (
            HeuristicSocialGuidanceArbiter()
            if cfg.control.heuristic_social_guidance
            else SingleProposalControlArbiter()
        )
        if (
            self.experiment_mode is ExperimentMode.SCIENTIFIC
            and not bool(getattr(self.control_arbiter, "scientific_safe", False))
        ):
            raise ValueError(
                f"control arbiter {type(self.control_arbiter).__name__} is not declared "
                "scientific_safe; use a reviewed arbiter or entertainment mode"
            )
        self.group_label_planner = (
            group_label_planner
            if group_label_planner is not None
            else DeterministicGroupLabelPlanner()
        )
        self.heuristic_guidance_actions = 0
        self.autonomy_recovery_enabled = False
        self.autonomy_restored = np.zeros(cfg.world.max_entities, dtype=bool)
        self.autonomy_observation_cohort = np.zeros(cfg.world.max_entities, dtype=bool)
        self.autonomy_recovery_tick: int | None = None
        self.autonomy_cohort_tick: int | None = None
        self.autonomy_recovery_cohort_ids = np.empty(0, dtype=np.uint64)
        self.autonomy_module_actions = 0
        self.autonomy_harvest_attempts = 0
        self.autonomy_harvest_successes = 0
        self.social_control_enabled = True
        self.social_connections_enabled = True
        self.direct_messages_enabled = True
        self.freeze_genotype = False
        self.intervention_history: list[dict[str, object]] = []
        # Interactive ``step()`` calls keep host field mirrors current.  A
        # monolithic ``run()`` can defer that costly device->host copy until
        # completion because every intervening field consumer is device-side.
        self._defer_gpu_field_sync = False
        self._trajectory_file = None
        if cfg.run.trajectory_subject_ids:
            self._trajectory_file = (self.output_dir / "trajectory.jsonl").open("w", encoding="utf-8")

    @property
    def benefit_internal_energy_total(self) -> float:
        return float(self.benefit_flow_energy_total[BenefitFlowKind.INTERNAL])

    @property
    def benefit_cross_boundary_energy_total(self) -> float:
        return float(
            self.benefit_flow_energy_total[BenefitFlowKind.GROUP_TO_GROUP]
            + self.benefit_flow_energy_total[BenefitFlowKind.GROUP_TO_UNGROUPED]
            + self.benefit_flow_energy_total[BenefitFlowKind.UNGROUPED_TO_GROUP]
        )

    @property
    def benefit_unbounded_energy_total(self) -> float:
        return float(self.benefit_flow_energy_total[BenefitFlowKind.UNBOUNDED])

    def clone(self, output_dir: str | Path) -> "Simulation":
        """Clone a snapshot for paired counterfactual runs.

        Metrics and trajectory writers are intentionally recreated for the
        branch.  All mutable world state, including delayed messages and the
        subject graph, is deep-copied before the intervention is applied.
        """
        if self.gpu_runtime is not None and self._defer_gpu_field_sync:
            self.gpu_runtime.sync_to_host(self.environment, self.information)
        branch = Simulation(
            self.cfg,
            output_dir,
            backend=self.execution_backend,
            conflict_resolver=copy.deepcopy(self.conflict_resolver),
            control_arbiter=copy.deepcopy(self.control_arbiter),
            group_label_planner=copy.deepcopy(self.group_label_planner),
        )
        branch.entities = copy.deepcopy(self.entities)
        branch.environment = copy.deepcopy(self.environment)
        branch.information = copy.deepcopy(self.information)
        branch.signal_scheduler = copy.deepcopy(self.signal_scheduler)
        branch.spatial = copy.deepcopy(self.spatial)
        branch.social = copy.deepcopy(self.social)
        branch.subjects = self.subjects.clone()
        branch.tick = self.tick
        branch.entity_device_version = self.entity_device_version
        branch.last_group_summary = copy.deepcopy(self.last_group_summary)
        branch.last_group_plan = copy.deepcopy(self.last_group_plan)
        branch.total_births = self.total_births
        branch.total_deaths = self.total_deaths
        branch.total_shared_energy = self.total_shared_energy
        branch.action_counts = self.action_counts.copy()
        branch.benefit_flow_energy_total = self.benefit_flow_energy_total.copy()
        branch.lagged_benefit_boundary = self.lagged_benefit_boundary.clone()
        branch.total_reproduction_eligible = self.total_reproduction_eligible
        branch.total_reproduction_proposals = self.total_reproduction_proposals
        branch.total_reproduction_rejected_capacity = (
            self.total_reproduction_rejected_capacity
        )
        branch.total_reproduction_rejected_resource = (
            self.total_reproduction_rejected_resource
        )
        branch.total_reproduction_rejected_other = (
            self.total_reproduction_rejected_other
        )
        branch.evolution_progress = self.evolution_progress.clone(branch.output_dir)
        branch.last_birth_allocation = copy.deepcopy(self.last_birth_allocation)
        branch.last_death_events = copy.deepcopy(self.last_death_events)
        branch.last_entity_device_commit = copy.deepcopy(
            self.last_entity_device_commit
        )
        branch.heuristic_guidance_actions = self.heuristic_guidance_actions
        branch.autonomy_recovery_enabled = self.autonomy_recovery_enabled
        branch.autonomy_restored = self.autonomy_restored.copy()
        branch.autonomy_observation_cohort = self.autonomy_observation_cohort.copy()
        branch.autonomy_recovery_tick = self.autonomy_recovery_tick
        branch.autonomy_cohort_tick = self.autonomy_cohort_tick
        branch.autonomy_recovery_cohort_ids = self.autonomy_recovery_cohort_ids.copy()
        branch.autonomy_module_actions = self.autonomy_module_actions
        branch.autonomy_harvest_attempts = self.autonomy_harvest_attempts
        branch.autonomy_harvest_successes = self.autonomy_harvest_successes
        branch.social_control_enabled = self.social_control_enabled
        branch.social_connections_enabled = self.social_connections_enabled
        branch.direct_messages_enabled = self.direct_messages_enabled
        branch.freeze_genotype = self.freeze_genotype
        branch.intervention_history = copy.deepcopy(self.intervention_history)
        if branch.gpu_runtime is not None:
            branch.gpu_runtime.sync_from_host(branch.environment, branch.information)
            branch.gpu_runtime.sync_entity_from_host(
                branch.entities,
                branch.social,
                branch.entity_device_version,
            )
        return branch

    def apply_intervention(self, intervention: str) -> None:
        """Apply one documented intervention without changing random streams."""
        spec = resolve_intervention(intervention)
        spec.require_mode(self.experiment_mode)
        normalized = spec.name
        active = np.flatnonzero(self.entities.alive).astype(np.int32)
        details: dict[str, int | float | str] = {}
        if normalized == "disable-social-control":
            canonical = "disable-social-control"
            self.social_control_enabled = False
        elif normalized == "cut-social-connections":
            canonical = "cut-social-connections"
            self.social_connections_enabled = False
            self.direct_messages_enabled = False
            self.social.reset_entities(active)
            if self.gpu_runtime is not None:
                self.gpu_runtime.mark_social_state_dirty()
            self.information.pending_messages.clear()
        elif normalized == "shuffle-memory":
            canonical = "shuffle-memory"
            ids = self.entities.entity_id[active]
            ctx = RandomContext(self.cfg.run.seed, self.tick, phase=90, stream=Stream.CAUSAL_INTERVENTION)
            order = np.argsort(uniform01(ctx, ids, draw_index=0), kind="stable")
            self.entities.memory[active] = self.entities.memory[active[order]].copy()
            if self.gpu_runtime is not None:
                self.gpu_runtime.mark_entity_static_dirty()
        elif normalized == "freeze-genotype":
            canonical = "freeze-genotype"
            self.freeze_genotype = True
        elif normalized == "reverse-environment":
            canonical = "reverse-environment"
            self.environment.reverse_spatial_orientation()
            if self.gpu_runtime is not None:
                self.gpu_runtime.reverse_environment()
        elif normalized == "independent-foraging-override":
            canonical = "independent-foraging-override"
            fraction = self.cfg.control.autonomy_recovery_fraction
            cohort_size = min(active.size, int(np.ceil(active.size * fraction)))
            selected = np.empty(0, dtype=np.int32)
            if cohort_size:
                ids = self.entities.entity_id[active]
                ctx = RandomContext(
                    self.cfg.run.seed,
                    self.tick,
                    phase=91,
                    stream=Stream.CAUSAL_INTERVENTION,
                )
                score = uniform01(ctx, ids, draw_index=1)
                order = np.lexsort((ids, score))
                selected = active[order[:cohort_size]]
            self.register_autonomy_observation_cohort(
                self.entities.entity_id[selected],
                tick=self.tick,
            )
            self.autonomy_restored[:] = self.autonomy_observation_cohort
            self.autonomy_recovery_enabled = True
            self.autonomy_recovery_tick = self.tick
            self.autonomy_module_actions = 0
            self.autonomy_harvest_attempts = 0
            self.autonomy_harvest_successes = 0
            if not isinstance(self.control_arbiter, AutonomyRecoveryArbiter):
                self.control_arbiter = AutonomyRecoveryArbiter(self.control_arbiter)
            details = {
                "cohort_size": cohort_size,
                "fraction": fraction,
                "module": "independent-foraging-v1",
            }
        else:
            raise AssertionError(f"unhandled registered intervention: {normalized}")
        self.intervention_history.append(
            {
                "tick": self.tick,
                "type": canonical,
                "kind": spec.kind.value,
                "target_scope": spec.target_scope,
                "direct_action_control": spec.direct_action_control,
                "experiment_mode": self.experiment_mode.value,
                **details,
            }
        )

    def scientific_validity(self) -> dict[str, object]:
        """Return a machine-readable provenance audit for this run.

        This is a structural audit, not a claim that one finite trajectory is
        empirical proof.  It makes the model conditions required for such a
        proof testable and prevents entertainment controllers from being
        silently mixed into the scientific baseline.
        """
        direct_interventions = [
            str(record["type"])
            for record in self.intervention_history
            if bool(record.get("direct_action_control", False))
        ]
        violations: list[str] = []
        if self.experiment_mode is not ExperimentMode.SCIENTIFIC:
            violations.append("experiment mode is entertainment")
        if self.cfg.control.heuristic_social_guidance:
            violations.append("heuristic social guidance alters action direction")
        if not bool(getattr(self.control_arbiter, "scientific_safe", False)):
            violations.append(
                f"control arbiter {type(self.control_arbiter).__name__} is not scientific-safe"
            )
        if not bool(getattr(self.conflict_resolver, "scientific_safe", False)):
            violations.append(
                f"conflict resolver {type(self.conflict_resolver).__name__} is not scientific-safe"
            )
        if not bool(getattr(self.group_label_planner, "scientific_safe", False)):
            violations.append(
                f"group label planner {type(self.group_label_planner).__name__} is not scientific-safe"
            )
        if direct_interventions:
            violations.append(
                "direct action replacement: " + ", ".join(direct_interventions)
            )
        valid = not violations
        return {
            "structural_evolution_provenance_valid": valid,
            "strict_unintervened_baseline": valid and not self.intervention_history,
            "violations": violations,
            "strategy": {
                "architecture": "inherited-linear-policy-v1",
                "feature_constraints": list(ParametricPolicy.FEATURE_NAMES),
                "action_preferences_hardcoded": False,
                "strategy_gene_count": ParametricPolicy.STRATEGY_GENES,
                "genome_size": ParametricPolicy.GENOME_SIZE,
                "initialization": "bounded stateless random generation",
                "transmission": "parental inheritance with configured mutation",
                "mutation_probability_per_gene": self.cfg.policy.mutation_probability,
                "mutation_std_conditional": self.cfg.policy.mutation_std,
                "morphology_gene_semantics": {
                    "sensor_quality": 0,
                    "movement_speed": 5,
                    "reserved_neutral": [1, 2, 3, 4, 6, 7],
                },
            },
            "state_origins": {
                "memory": "observation-driven finite-memory dynamics",
                "generation": "parent generation plus one at committed birth",
                "candidate_subjects": "derived from bodies, lineages, and relation structure",
                "subject_shift": "measured from candidate/control provenance; never assigned as a state label",
            },
            "evolution_evaluation": {
                "period_ticks": self.cfg.run.evolution_evaluation_period,
                "feedback_to_world": False,
                "strategy_sample_capacity": 4096,
                "actual_context_sample_capacity": 4096,
                "common_panel_strategy_capacity": 1024,
                "common_panel_context_capacity": 32,
                "lagged_boundary_identity": "stable-entity-id",
            },
            "control_arbiter": {
                "name": type(self.control_arbiter).__name__,
                "scientific_safe": bool(
                    getattr(self.control_arbiter, "scientific_safe", False)
                ),
            },
            "world_components": {
                "conflict_resolver": type(self.conflict_resolver).__name__,
                "conflict_resolver_scientific_safe": bool(
                    getattr(self.conflict_resolver, "scientific_safe", False)
                ),
                "group_label_planner": type(self.group_label_planner).__name__,
                "group_label_planner_scientific_safe": bool(
                    getattr(self.group_label_planner, "scientific_safe", False)
                ),
            },
            "fixed_constraints": [
                "physical action semantics and feasibility masks",
                "sensor feature vocabulary",
                "inheritance and mutation mechanics",
                "candidate-subject measurement rules",
            ],
            "proof_scope": (
                "structural provenance only; evolutionary or causal claims still require "
                "preregistered replicated experiments"
            ),
        }

    def register_autonomy_observation_cohort(
        self,
        entity_ids: np.ndarray,
        *,
        tick: int,
    ) -> None:
        """Track the same stable-ID cohort in treated and untreated branches."""
        ids = np.asarray(entity_ids, dtype=np.uint64)
        if ids.ndim != 1 or np.unique(ids).size != ids.size:
            raise ValueError("autonomy observation cohort IDs must be unique and one-dimensional")
        selected = np.isin(self.entities.entity_id, ids) & self.entities.alive
        if np.count_nonzero(selected) != ids.size:
            raise ValueError("autonomy observation cohort must reference living entities")
        self.autonomy_observation_cohort.fill(False)
        self.autonomy_observation_cohort[selected] = True
        self.autonomy_recovery_cohort_ids = ids.copy()
        self.autonomy_cohort_tick = int(tick)

    def _record_trajectories(
        self,
        intents: ActionIntentBatch,
        resolutions: ActionResolutionBatch,
        logits: np.ndarray,
    ) -> None:
        if self._trajectory_file is None:
            return
        tracked = {int(subject_id) for subject_id in self.cfg.run.trajectory_subject_ids}
        for row, entity_id in enumerate(intents.carrier_id.tolist()):
            if entity_id not in tracked:
                continue
            record = {
                "tick": self.tick,
                "entity_id": entity_id,
                "subject_id": int(self.entities.primary_subject_id[intents.carrier_index[row]]),
                "intent_id": int(intents.intent_id[row]),
                "action": Action(intents.action[row]).name,
                "sample_probability": float(intents.sampled_probability[row]),
                "logits": [float(value) for value in logits[row]],
                "success": bool(resolutions.success[row]),
                "failure_reason": FailureReason(resolutions.failure_reason[row]).name,
                "resource_delta": [float(value) for value in resolutions.resource_delta[row]],
            }
            if intents.proposer_subject_id is not None:
                record["proposer_subject_id"] = int(intents.proposer_subject_id[row])
            if intents.controller_kind is not None:
                record["controller_kind"] = ControllerKind(intents.controller_kind[row]).name
            if intents.contributor_subject_ids is not None:
                record["contributor_subject_ids"] = [
                    int(subject_id) for subject_id in intents.contributor_subject_ids[row]
                ]
            if intents.contributor_controller_kinds is not None:
                record["contributor_controller_kinds"] = [
                    ControllerKind(int(kind)).name
                    for kind in intents.contributor_controller_kinds[row]
                ]
            if intents.contribution_weights is not None:
                record["contribution_weights"] = [
                    float(weight) for weight in intents.contribution_weights[row]
                ]
            if intents.heuristic_control is not None:
                record["heuristic_control"] = bool(intents.heuristic_control[row])
            if intents.autonomy_control is not None:
                record["autonomy_control"] = bool(intents.autonomy_control[row])
            self._trajectory_file.write(json.dumps(record, ensure_ascii=False) + "\n")
        self._trajectory_file.flush()

    def _commit_shares(self, share: ShareResolution) -> float:
        """Apply one self-contained share plan without consulting last-step state."""
        if share.rows.size == 0:
            return 0.0
        committed = share.success & share.valid_target & (share.amounts > 1e-8)
        if np.any(committed):
            owners = share.owner_indices[committed]
            targets = share.target_indices[committed]
            amounts = share.amounts[committed]
            np.add.at(self.entities.energy, owners, -amounts)
            np.add.at(self.entities.energy, targets, amounts)
            np.add.at(self.entities.shared_energy_received_total, targets, amounts)
        if self.social_connections_enabled:
            self.social.apply_relation_updates(share.relation_updates)
        # Use the same float64 accounting domain as the exhaustive boundary
        # partition.  World energy writes above retain their original FP32
        # semantics; this only makes the diagnostic conservation residual
        # meaningful over long windows.
        return float(np.asarray(share.amounts[committed], dtype=np.float64).sum())

    def _record_benefit_boundary(
        self,
        share: ShareResolution,
        stats: StepStats,
    ) -> None:
        """Measure realized energy flows against current candidate boundaries."""
        committed = share.success & share.valid_target & (share.amounts > 1e-8)
        if not np.any(committed):
            return
        owners = share.owner_indices[committed]
        targets = share.target_indices[committed]
        amounts = np.asarray(share.amounts[committed], dtype=np.float64)
        owner_groups = self.social.group_id[owners]
        target_groups = self.social.group_id[targets]
        flow_totals = benefit_flow_totals(owner_groups, target_groups, amounts)
        stats.benefit_flow_energy += flow_totals
        self.benefit_flow_energy_total += flow_totals
        stats.lagged_benefit_flow_energy += self.lagged_benefit_boundary.record(
            owner_indices=owners,
            target_indices=targets,
            current_stable_ids=self.entities.entity_id,
            amounts=amounts,
        )
        self.subjects.record_benefit_flows(
            owner_groups,
            target_groups,
            amounts,
            tick=self.tick,
        )

    def _emit_signals(
        self,
        actors: np.ndarray,
        cells: np.ndarray,
        local_resources: np.ndarray,
        target_indices: np.ndarray,
    ) -> tuple[SignalEmissionPlan, int]:
        if actors.size == 0:
            return SignalEmissionPlan(()), 0
        ent = self.entities
        actor_cells = cells
        strengths_resource = np.clip(local_resources[:, 0], 0.0, 2.0) * 0.15
        hazard = (
            self.gpu_runtime.hazard_for_cells(actor_cells)
            if self.gpu_runtime is not None
            else self.environment.hazard.reshape(-1)[actor_cells]
        )
        strengths_danger = hazard * 0.15
        group_member = self.social.group_id[actors] != 0
        strengths_social = group_member.astype(np.float32) * 0.12
        signal_plan = SignalEmissionPlan(
            batches=(
                SignalEmissionBatch(0, actor_cells, strengths_resource, emitter="actor-resource"),
                SignalEmissionBatch(1, actor_cells, strengths_danger, emitter="actor-danger"),
                SignalEmissionBatch(2, actor_cells, strengths_social, emitter="actor-social"),
            )
        )
        ent.energy[actors] -= self.cfg.entities.signal_cost
        valid_target = (target_indices >= 0) & ent.alive[target_indices]
        safe_targets = np.where(valid_target, target_indices, 0)
        payloads = np.stack(
            [local_resources[:, 0], hazard, group_member.astype(np.float32)], axis=1
        ).astype(np.float32)
        direct_messages = 0
        if self.direct_messages_enabled:
            direct_messages = self.information.emit_direct(
                ent.entity_id[actors],
                ent.entity_id[safe_targets] * valid_target.astype(np.uint64),
                payloads,
                np.full(actors.size, 1.0, dtype=np.float32),
                self.cfg.run.seed,
                self.tick,
            )
        return signal_plan, direct_messages

    def _flush_signal_emissions(self, plan: SignalEmissionPlan | None = None) -> None:
        """Commit channel batches whose modeled delivery cadence is due now."""
        # ``self.tick`` is zero-based during a step.  Flush against the
        # completed one-based tick so a period of three delivers after steps
        # 3, 6, ... rather than treating construction tick zero as a flush.
        due_plan = self.signal_scheduler.submit(plan or SignalEmissionPlan(()), self.tick + 1)
        if not due_plan.batches:
            return
        if self.gpu_runtime is None:
            self.information.emit_plan(due_plan)
        else:
            self.gpu_runtime.emit_plan(due_plan)

    def _checkpoint(self) -> None:
        active = np.flatnonzero(self.entities.alive)
        path = self.output_dir / f"checkpoint_{self.tick:08d}.npz"
        np.savez_compressed(
            path,
            tick=np.asarray([self.tick], dtype=np.uint64),
            entity_id=self.entities.entity_id[active],
            x=self.entities.x[active],
            y=self.entities.y[active],
            energy=self.entities.energy[active],
            integrity=self.entities.integrity[active],
            lineage_id=self.entities.lineage_id[active],
            primary_subject_id=self.entities.primary_subject_id[active],
            lineage_subject_id=self.entities.lineage_subject_id[active],
            group_id=self.social.group_id[active],
            genotype=self.entities.genotype[active],
            generation=self.entities.generation[active],
            **(
                {
                    "entertainment_override": self.autonomy_restored[active],
                    "entertainment_observation_cohort": (
                        self.autonomy_observation_cohort[active]
                    ),
                }
                if self.experiment_mode is ExperimentMode.ENTERTAINMENT
                else {}
            ),
        )

    def _record_evolution_progress(
        self,
        actual_context_metrics: dict[str, object] | None = None,
    ) -> None:
        self.evolution_progress.record(
            tick=self.tick,
            scheduled=True,
            alive=self.entities.alive,
            stable_ids=self.entities.entity_id,
            lineage_ids=self.entities.lineage_id,
            generation=self.entities.generation,
            genotype=self.entities.genotype,
            births_total=self.total_births,
            deaths_total=self.total_deaths,
            action_counts=self.action_counts,
            benefit_flow_energy_total=self.benefit_flow_energy_total,
            lagged_benefit_flow_energy_total=(
                self.lagged_benefit_boundary.flow_energy_total
            ),
            lagged_benefit_boundary_snapshot_tick=(
                self.lagged_benefit_boundary.snapshot_tick
            ),
            shared_energy_total=self.total_shared_energy,
            reproduction_eligible_total=self.total_reproduction_eligible,
            reproduction_proposals_total=self.total_reproduction_proposals,
            reproduction_rejected_capacity_total=(
                self.total_reproduction_rejected_capacity
            ),
            reproduction_rejected_resource_total=(
                self.total_reproduction_rejected_resource
            ),
            reproduction_rejected_other_total=(
                self.total_reproduction_rejected_other
            ),
            mutation_probability=self.cfg.policy.mutation_probability,
            mutation_std=self.cfg.policy.mutation_std,
            actual_context_metrics=actual_context_metrics,
        )

    def step(self) -> StepStats:
        cfg = self.cfg
        ent = self.entities
        stats = StepStats()
        evaluation_due = self.evolution_progress.due(self.tick + 1)
        actual_context_metrics: dict[str, object] | None = None
        if self.gpu_runtime is None:
            phase_started = time.perf_counter()
            self.environment.update(self.tick)
            self.information.propagate()
            stats.environment_seconds = time.perf_counter() - phase_started

            phase_started = time.perf_counter()
            active = self.spatial.build(ent.x, ent.y, ent.alive)
            stats.spatial_seconds = time.perf_counter() - phase_started
            if active.size == 0:
                return stats

            phase_started = time.perf_counter()
            cells = self.spatial.entity_cells[active]
            partners = self.spatial.sample_partners(
                active,
                ent.entity_id,
                cfg.run.seed,
                self.tick,
                cfg.policy.partner_samples,
            )
            local_resources = self.environment.cell_values(cells)
            info = self.information.observe(
                active=active,
                stable_ids=ent.entity_id,
                cell_ids=cells,
                partners=partners,
                energy=ent.energy,
                group_id=self.social.group_id,
                sensor_quality=ent.sensor_quality(),
                run_seed=cfg.run.seed,
                tick=self.tick,
            )
            resource_gradient, danger_gradient = self.environment.gradients_for_entities(
                self.spatial.entity_cells, ent.alive.size
            )
            stats.observation_seconds = time.perf_counter() - phase_started

            phase_started = time.perf_counter()
            if self.social_control_enabled:
                group_direction = (self.social.group_dir_x, self.social.group_dir_y)
            else:
                group_direction = (np.zeros_like(self.social.group_dir_x), np.zeros_like(self.social.group_dir_y))
            decision = self.policy.decide(
                active=active,
                stable_ids=ent.entity_id,
                energy=ent.energy,
                integrity=ent.integrity,
                fertility=ent.fertility,
                genotype=ent.genotype,
                memory=ent.memory,
                local_resources=local_resources,
                resource_gradient=resource_gradient,
                danger_gradient=danger_gradient,
                group_direction=group_direction,
                partners=partners,
                info=info,
                run_seed=cfg.run.seed,
                tick=self.tick,
            )
            stats.policy_seconds = time.perf_counter() - phase_started
        else:
            self.gpu_runtime.begin_step_transfer_measurement()
            phase_started = time.perf_counter()
            self.gpu_runtime.update_fields(self.tick)
            self.gpu_runtime.backend.synchronize()
            stats.environment_seconds = time.perf_counter() - phase_started
            prepared = self.gpu_runtime.prepare(
                entity=ent,
                social=self.social,
                information=self.information,
                policy=self.policy,
                social_control_enabled=self.social_control_enabled,
                run_seed=cfg.run.seed,
                tick=self.tick,
                retain_logits=self._trajectory_file is not None,
                retain_policy_diagnostics=evaluation_due,
                need_host_resource_gradient=(
                    self.autonomy_recovery_enabled
                    or (
                        self.social_connections_enabled
                        and self.tick % cfg.social.group_update_period == 0
                    )
                ),
                entity_state_version=self.entity_device_version,
            )
            active = prepared.active
            if active.size == 0:
                if not self._defer_gpu_field_sync:
                    self.gpu_runtime.sync_to_host(self.environment, self.information)
                transfer = self.gpu_runtime.finish_step_transfer_measurement()
                stats.gpu_h2d_bytes = transfer.host_to_device_bytes
                stats.gpu_d2h_bytes = transfer.device_to_host_bytes
                stats.gpu_direct_message_events = transfer.direct_message_events
                stats.gpu_direct_dense_bytes_avoided = (
                    transfer.direct_message_dense_bytes_avoided
                )
                stats.gpu_entity_commit_bytes = transfer.entity_commit_bytes
                return stats
            cells = prepared.cells
            local_resources = prepared.local_resources
            resource_gradient = prepared.resource_gradient
            info = prepared.information
            decision = prepared.decision
            stats.spatial_seconds = prepared.spatial_seconds
            stats.observation_seconds = prepared.observation_seconds
            stats.policy_seconds = prepared.policy_seconds
        if evaluation_due:
            evaluation_started = time.perf_counter()
            if decision.features is None or decision.action_mask is None:
                # Third-party policy adapters written before diagnostic
                # payloads remain valid, but their missing observations are
                # explicit instead of being reconstructed from changed state.
                actual_context_metrics = {
                    "actual_context_available": False,
                    "actual_context_observation_tick": int(self.tick),
                }
            else:
                actual_context_metrics = {
                    "actual_context_available": True,
                    "actual_context_observation_tick": int(self.tick),
                    **actual_context_policy_diagnostics(
                        active,
                        ent.entity_id,
                        ent.genotype,
                        decision.features,
                        decision.action_mask,
                        decision.logits,
                        run_seed=cfg.run.seed,
                        temperature=cfg.policy.temperature,
                    ),
                }
            stats.evolution_evaluation_seconds += (
                time.perf_counter() - evaluation_started
            )
        body_proposal = body_control_proposal(
            active,
            ent.primary_subject_id[active],
            decision,
            self.tick,
        )
        proposals = (body_proposal,)
        if cfg.control.heuristic_social_guidance:
            if self.social_control_enabled:
                social_subject_id = self.subjects.social_subject_ids(self.social.group_id[active])
                group_direction = (
                    self.social.group_dir_x[active],
                    self.social.group_dir_y[active],
                )
            else:
                social_subject_id = np.zeros(active.size, dtype=np.uint64)
                group_direction = (
                    np.zeros(active.size, dtype=np.float32),
                    np.zeros(active.size, dtype=np.float32),
                )
            proposals = (
                body_proposal,
                social_guidance_control_proposal(
                    body_proposal,
                    social_subject_id,
                    group_direction,
                    cfg.control.heuristic_social_guidance_weight,
                ),
            )
        if self.autonomy_recovery_enabled:
            if resource_gradient is None:
                raise RuntimeError("autonomy recovery requires physical resource gradients")
            stats.autonomy_restored_active = int(
                np.count_nonzero(self.autonomy_restored[active])
            )
            proposals = proposals + (
                autonomy_recovery_control_proposal(
                    body_proposal,
                    ent.entity_id[active],
                    self.autonomy_restored[active],
                    ent.energy[active],
                    local_resources[:, 0],
                    (
                        resource_gradient[0][active],
                        resource_gradient[1][active],
                    ),
                    run_seed=cfg.run.seed,
                    max_energy=cfg.entities.max_energy,
                    activation_energy_fraction=(
                        cfg.control.autonomy_activation_energy_fraction
                    ),
                    harvest_threshold=cfg.control.autonomy_harvest_threshold,
                ),
            )
        arbitration = self.control_arbiter.arbitrate(proposals)
        decision = arbitration.decision
        if arbitration.heuristic_applied is not None:
            stats.heuristic_guidance_actions = int(np.count_nonzero(arbitration.heuristic_applied))
            self.heuristic_guidance_actions += stats.heuristic_guidance_actions
        if arbitration.autonomy_applied is not None:
            stats.autonomy_module_actions = int(
                np.count_nonzero(arbitration.autonomy_applied)
            )
            self.autonomy_module_actions += stats.autonomy_module_actions
        step_action_counts = np.bincount(decision.action, minlength=len(Action))
        self.action_counts += step_action_counts
        stats.reproduction_eligible = int(
            np.count_nonzero(
                (ent.energy[active] >= cfg.entities.reproduction_threshold)
                & (ent.fertility[active] >= 0.5)
            )
        )
        stats.reproduction_proposals = int(step_action_counts[Action.REPRODUCE])
        stats.action_entropy = float(decision.entropy.mean())
        stats.signal_detection_rate = float(info.signal_mask.mean())
        stats.partner_detection_rate = float(info.partner_mask.mean()) if info.partner_mask.size else 0.0
        grouped = self.social.group_id[active] != 0
        stats.move_social_fraction = float(
            np.mean(decision.action[grouped] == Action.MOVE_SOCIAL) if np.any(grouped) else 0.0
        )

        # ----- Intent and conflict phases: no world state is changed here. -----
        phase_started = time.perf_counter()
        intents = build_intents(
            active,
            ent.entity_id,
            decision,
            self.tick,
            proposer_subject_id=arbitration.proposer_subject_id,
            controller_kind=arbitration.controller_kind,
            contributor_subject_ids=arbitration.contributor_subject_ids,
            contributor_controller_kinds=arbitration.contributor_controller_kinds,
            contribution_weights=arbitration.contribution_weights,
            heuristic_control=arbitration.heuristic_applied,
            autonomy_control=arbitration.autonomy_applied,
        )
        snapshot = ActionResolutionSnapshot(
            active=active,
            cells=cells,
            entity_id=ent.entity_id,
            alive=ent.alive,
            energy=ent.energy,
            fertility=ent.fertility,
            primary_subject_id=ent.primary_subject_id,
            free_slot_count=len(ent.free_slots),
        )
        harvest_allocator = (
            self.gpu_runtime.resolve_harvest
            if self.gpu_runtime is not None
            else self.environment.resolve_harvest
        )
        resolution_plan = self.conflict_resolver.resolve(snapshot, intents, harvest_allocator)
        resolutions = resolution_plan.resolutions
        harvest_rows = resolution_plan.harvest_rows
        harvest_cells = resolution_plan.harvest_cells
        gathered = resolution_plan.gathered
        share = resolution_plan.share
        signal_rows = resolution_plan.signal_rows
        birth_requests = resolution_plan.birth_requests
        reproduce = intents.action == int(Action.REPRODUCE)
        stats.reproduction_rejected_capacity = int(
            np.count_nonzero(
                reproduce
                & (resolutions.failure_reason == FailureReason.INSUFFICIENT_CAPACITY)
            )
        )
        stats.reproduction_rejected_resource = int(
            np.count_nonzero(
                reproduce
                & (resolutions.failure_reason == FailureReason.INSUFFICIENT_RESOURCE)
            )
        )
        autonomy_control = (
            intents.autonomy_control
            if intents.autonomy_control is not None
            else np.zeros(intents.action.size, dtype=bool)
        )
        autonomy_harvest = autonomy_control & (intents.action == int(Action.HARVEST))
        stats.autonomy_harvest_attempts = int(np.count_nonzero(autonomy_harvest))
        stats.autonomy_harvest_successes = int(
            np.count_nonzero(autonomy_harvest & resolutions.success)
        )
        self.autonomy_harvest_attempts += stats.autonomy_harvest_attempts
        self.autonomy_harvest_successes += stats.autonomy_harvest_successes
        stats.conflict_seconds = time.perf_counter() - phase_started
        self.last_intents = intents
        self.last_resolutions = resolutions

        # ----- World commit phase: only resolved intents may mutate state. -----
        movable_actions = np.isin(intents.action, [Action.MOVE_RESOURCE, Action.MOVE_SOCIAL, Action.FLEE])
        movable_rows = np.flatnonzero(movable_actions & resolutions.success)
        movers = intents.carrier_index[movable_rows]
        speed = (0.35 + 0.10 * np.clip(ent.genotype[movers, 5], -1.0, 1.0)).astype(np.float32)
        ent.vx[movers] = intents.direction_x[movable_rows] * speed
        ent.vy[movers] = intents.direction_y[movable_rows] * speed
        ent.x[movers] += ent.vx[movers]
        ent.y[movers] += ent.vy[movers]
        if cfg.world.periodic:
            ent.x[movers] %= cfg.world.width
            ent.y[movers] %= cfg.world.height
        else:
            ent.x[movers] = np.clip(ent.x[movers], 0.0, cfg.world.width)
            ent.y[movers] = np.clip(ent.y[movers], 0.0, cfg.world.height)
        non_movers = active[~np.isin(active, movers)]
        ent.vx[non_movers] = 0.0
        ent.vy[non_movers] = 0.0

        if harvest_rows.size:
            if self.gpu_runtime is not None:
                self.gpu_runtime.commit_harvest(harvest_cells, gathered)
            else:
                self.environment.commit_harvest(harvest_cells, gathered)
            harvesters = intents.carrier_index[harvest_rows]
            ent.energy[harvesters] = np.minimum(ent.energy[harvesters] + gathered[:, 0], cfg.entities.max_energy)
            ent.integrity[harvesters] = np.minimum(ent.integrity[harvesters] + gathered[:, 1] * 0.05, 1.0)
            ent.information_store[harvesters] = np.minimum(ent.information_store[harvesters] + gathered[:, 2], 3.0)
            ent.fertility[harvesters] = np.minimum(ent.fertility[harvesters] + gathered[:, 3], 3.0)
            ent.harvested_energy_total[harvesters] += gathered[:, 0]
            stats.harvested_energy = float(gathered[:, 0].sum())

        stats.shared_energy = self._commit_shares(share)
        self.total_shared_energy += stats.shared_energy
        self._record_benefit_boundary(share, stats)

        signal_plan = SignalEmissionPlan(())
        if signal_rows.size:
            signal_actors = intents.carrier_index[signal_rows]
            signal_observation_rows = np.searchsorted(active, signal_actors)
            signal_plan, stats.direct_messages = self._emit_signals(
                signal_actors,
                cells[signal_observation_rows],
                local_resources[signal_observation_rows],
                intents.target_index[signal_rows],
            )
            stats.signals = int(signal_actors.size)
        self._flush_signal_emissions(signal_plan)

        newborns = np.empty(0, dtype=np.int32)
        birth_allocation = plan_birth_allocations(
            birth_requests,
            ent.free_slots,
            int(ent.next_entity_id),
            ent.free_slot_version,
        )
        self.last_birth_allocation = birth_allocation
        if birth_allocation.size:
            accepted_parents, newborns = ent.commit_births(
                birth_allocation,
                mutation_std=0.0 if self.freeze_genotype else None,
            )
            if newborns.size:
                # Recovery is a treatment of the selected living cohort, not
                # a hereditary trait in the current experiment.
                self.autonomy_restored[newborns] = False
                self.autonomy_observation_cohort[newborns] = False
                self.social.reset_entities(newborns)
                body_subjects, lineage_subjects = self.subjects.register_bodies(
                    newborns, ent.lineage_id, self.tick
                )
                ent.primary_subject_id[newborns] = body_subjects
                ent.lineage_subject_id[newborns] = lineage_subjects
                ent.energy[accepted_parents] -= cfg.entities.reproduction_cost
                ent.fertility[accepted_parents] -= 0.5
                stats.births = int(newborns.size)
                self.total_births += stats.births

        stats.reproduction_accepted = stats.births
        stats.reproduction_rejected_other = max(
            stats.reproduction_proposals
            - stats.reproduction_accepted
            - stats.reproduction_rejected_capacity
            - stats.reproduction_rejected_resource,
            0,
        )
        self.total_reproduction_eligible += stats.reproduction_eligible
        self.total_reproduction_proposals += stats.reproduction_proposals
        self.total_reproduction_rejected_capacity += (
            stats.reproduction_rejected_capacity
        )
        self.total_reproduction_rejected_resource += (
            stats.reproduction_rejected_resource
        )
        self.total_reproduction_rejected_other += stats.reproduction_rejected_other

        # Existence costs and environmental damage.
        current_active = np.flatnonzero(ent.alive).astype(np.int32)
        current_cells = self.spatial.cell_ids(ent.x[current_active], ent.y[current_active])
        hazard = (
            self.gpu_runtime.hazard_for_cells(current_cells)
            if self.gpu_runtime is not None
            else self.environment.hazard.reshape(-1)[current_cells]
        )
        moved_now = np.zeros(ent.alive.size, dtype=bool)
        moved_now[movers] = True
        cost = cfg.entities.maintenance_cost + moved_now[current_active] * cfg.entities.movement_cost
        ent.energy[current_active] -= cost.astype(np.float32)
        ent.integrity[current_active] -= (hazard * 0.0015).astype(np.float32)
        starving = ent.energy[current_active] < 0.0
        ent.integrity[current_active[starving]] += ent.energy[current_active[starving]] * 0.05
        ent.energy[current_active] = np.maximum(ent.energy[current_active], 0.0)
        ent.age[current_active] += 1
        ent.information_store[current_active] *= 0.999
        ent.fertility[current_active] = np.maximum(ent.fertility[current_active] - 0.0005, 0.0)

        self.policy.update_memory(active, ent.memory, local_resources, info)
        death_events = plan_death_events(
            active=current_active,
            entity_ids=ent.entity_id,
            primary_subject_ids=ent.primary_subject_id,
            energy=ent.energy,
            integrity=ent.integrity,
            age=ent.age,
            max_age=cfg.entities.max_age,
            tick=self.tick,
        )
        self.last_death_events = death_events
        dead = death_events.entity_indices
        if dead.size:
            self.subjects.mark_dead(dead, self.tick)
            ent.commit_deaths(death_events)
            self.autonomy_restored[dead] = False
            self.autonomy_observation_cohort[dead] = False
            self.social.group_id[dead] = 0
            self.social.group_age[dead] = 0
            stats.deaths = int(dead.size)
            self.total_deaths += stats.deaths
        # With no death this tick no new stale relation target can exist, so
        # skip the otherwise full fixed-slot relationship-table scan.
        if dead.size:
            self.social.clear_dead_targets(ent.alive)

        # Candidate social subjects are updated at a slower timescale.
        phase_started = time.perf_counter()
        group_updated = self.tick % cfg.social.group_update_period == 0
        if group_updated:
            group_active = np.flatnonzero(ent.alive).astype(np.int32)
            if self.social_connections_enabled:
                if resource_gradient is None:
                    raise RuntimeError("GPU step omitted required resource gradients")
                group_snapshot = self.social.group_detection_snapshot(
                    ent.alive,
                    ent.entity_id,
                    ent.energy,
                    resource_gradient[0],
                    resource_gradient[1],
                    self.tick,
                )
                self.last_group_plan = self.group_label_planner.plan(group_snapshot)
            else:
                self.last_group_plan = ungrouped_group_label_plan(
                    group_active,
                    ent.entity_id[group_active],
                    self.tick,
                )
            if int(self.last_group_plan.tick) != self.tick:
                raise ValueError("group label planner returned a plan for the wrong tick")
            self.last_group_summary = self.social.commit_group_plan(
                self.last_group_plan,
                ent.alive,
                ent.entity_id,
            )
            self.subjects.commit_group_membership(
                self.last_group_plan.group_tokens,
                self.last_group_plan.member_starts,
                self.last_group_plan.member_counts,
                self.last_group_plan.member_indices,
                self.tick,
            )
        stats.graph_seconds = time.perf_counter() - phase_started
        if self.gpu_runtime is not None:
            phase_started = time.perf_counter()
            lifecycle_changed = np.zeros(ent.alive.size, dtype=bool)
            lifecycle_changed[newborns] = True
            lifecycle_changed[dead] = True
            lifecycle_indices = np.flatnonzero(lifecycle_changed).astype(
                np.int32, copy=False
            )
            moved_now[newborns] = True
            position_indices = np.flatnonzero(moved_now).astype(
                np.int32, copy=False
            )
            social_indices = (
                np.arange(ent.alive.size, dtype=np.int32)
                if group_updated
                else lifecycle_indices
            )
            self.last_entity_device_commit = build_entity_device_commit_plan(
                ent,
                self.social,
                dynamic_indices=current_active,
                position_indices=position_indices,
                lifecycle_indices=lifecycle_indices,
                social_indices=social_indices,
                base_version=self.entity_device_version,
                tick=self.tick,
            )
            self.gpu_runtime.apply_entity_commit(
                self.last_entity_device_commit
            )
            self.entity_device_version = self.last_entity_device_commit.next_version
            stats.device_commit_seconds = time.perf_counter() - phase_started
        stats.group_count = int(self.last_group_summary.group_ids.size)
        stats.mean_group_size = float(
            self.last_group_summary.counts.mean() if self.last_group_summary.counts.size else 0.0
        )
        self._record_trajectories(intents, resolutions, decision.logits)
        if self.gpu_runtime is not None and not self._defer_gpu_field_sync:
            self.gpu_runtime.sync_to_host(self.environment, self.information)
        if self.gpu_runtime is not None:
            transfer = self.gpu_runtime.finish_step_transfer_measurement()
            stats.gpu_h2d_bytes = transfer.host_to_device_bytes
            stats.gpu_d2h_bytes = transfer.device_to_host_bytes
            stats.gpu_direct_message_events = transfer.direct_message_events
            stats.gpu_direct_dense_bytes_avoided = transfer.direct_message_dense_bytes_avoided
            stats.gpu_entity_commit_bytes = transfer.entity_commit_bytes
        self.tick += 1
        if self.evolution_progress.due(self.tick):
            evaluation_started = time.perf_counter()
            self._record_evolution_progress(actual_context_metrics)
            self.lagged_benefit_boundary.freeze(
                tick=self.tick,
                alive=self.entities.alive,
                stable_ids=self.entities.entity_id,
                group_tokens=self.social.group_id,
            )
            stats.evolution_evaluation_seconds += (
                time.perf_counter() - evaluation_started
            )
        return stats

    def metric_row(
        self,
        stats: StepStats,
        elapsed: float,
        *,
        wall_elapsed: float = 0.0,
        window_seconds: float = 0.0,
        window_ticks: int = 1,
    ) -> dict[str, float | int]:
        ent = self.entities
        active = np.flatnonzero(ent.alive)
        alive_count = active.size
        if alive_count:
            mean_energy = float(ent.energy[active].mean())
            mean_integrity = float(ent.integrity[active].mean())
            mean_age = float(ent.age[active].mean())
            social_dependency = float(
                np.mean(
                    ent.shared_energy_received_total[active]
                    / np.maximum(
                        ent.shared_energy_received_total[active] + ent.harvested_energy_total[active], 1e-6
                    )
                )
            )
            lineage_count = int(np.unique(ent.lineage_id[active]).size)
            grouped_fraction = float(np.mean(self.social.group_id[active] != 0))
            strategy_genome = ent.genotype[
                active, ParametricPolicy.MORPHOLOGY_TRAITS :
            ]
            strategy_mean_abs_weight = float(
                np.mean(np.abs(strategy_genome), dtype=np.float64)
            )
            raw_strategy_gene_diversity = float(
                np.mean(np.std(strategy_genome, axis=0, dtype=np.float64))
            )
        else:
            mean_energy = mean_integrity = mean_age = social_dependency = grouped_fraction = 0.0
            lineage_count = 0
            strategy_mean_abs_weight = 0.0
            raw_strategy_gene_diversity = 0.0
        autonomy_cohort_size = int(self.autonomy_recovery_cohort_ids.size)
        autonomy_restored_alive = int(
            np.count_nonzero(self.autonomy_restored & ent.alive)
        )
        autonomy_cohort = self.autonomy_observation_cohort & ent.alive
        autonomy_cohort_alive = int(np.count_nonzero(autonomy_cohort))
        autonomy_cohort_mean_energy = (
            float(ent.energy[autonomy_cohort].mean())
            if autonomy_cohort_alive
            else 0.0
        )
        autonomy_cohort_mean_harvested = (
            float(ent.harvested_energy_total[autonomy_cohort].mean())
            if autonomy_cohort_alive
            else 0.0
        )
        autonomy_harvest_success_rate = (
            self.autonomy_harvest_successes / self.autonomy_harvest_attempts
            if self.autonomy_harvest_attempts
            else 0.0
        )
        step_boundary_energy = (
            stats.benefit_internal_energy + stats.benefit_cross_boundary_energy
        )
        step_benefit_energy = step_boundary_energy + stats.benefit_unbounded_energy
        total_boundary_energy = (
            self.benefit_internal_energy_total
            + self.benefit_cross_boundary_energy_total
        )
        total_benefit_energy = (
            total_boundary_energy + self.benefit_unbounded_energy_total
        )
        step_outgoing_boundary_energy = float(
            stats.benefit_flow_energy[BenefitFlowKind.INTERNAL]
            + stats.benefit_flow_energy[BenefitFlowKind.GROUP_TO_GROUP]
            + stats.benefit_flow_energy[BenefitFlowKind.GROUP_TO_UNGROUPED]
        )
        total_outgoing_boundary_energy = float(
            self.benefit_flow_energy_total[BenefitFlowKind.INTERNAL]
            + self.benefit_flow_energy_total[BenefitFlowKind.GROUP_TO_GROUP]
            + self.benefit_flow_energy_total[BenefitFlowKind.GROUP_TO_UNGROUPED]
        )
        row: dict[str, float | int] = {
            "tick": self.tick,
            "alive": alive_count,
            "births_step": stats.births,
            "deaths_step": stats.deaths,
            "births_total": self.total_births,
            "deaths_total": self.total_deaths,
            "reproduction_eligible_step": stats.reproduction_eligible,
            "reproduction_proposals_step": stats.reproduction_proposals,
            "reproduction_accepted_step": stats.reproduction_accepted,
            "reproduction_rejected_capacity_step": (
                stats.reproduction_rejected_capacity
            ),
            "reproduction_rejected_resource_step": (
                stats.reproduction_rejected_resource
            ),
            "reproduction_rejected_other_step": (
                stats.reproduction_rejected_other
            ),
            "reproduction_proposal_rate_given_eligible_step": (
                stats.reproduction_proposals / stats.reproduction_eligible
                if stats.reproduction_eligible
                else 0.0
            ),
            "reproduction_acceptance_rate_step": (
                stats.reproduction_accepted / stats.reproduction_proposals
                if stats.reproduction_proposals
                else 0.0
            ),
            "reproduction_eligible_carrier_ticks_total": (
                self.total_reproduction_eligible
            ),
            "reproduction_proposals_total": self.total_reproduction_proposals,
            "reproduction_rejected_capacity_total": (
                self.total_reproduction_rejected_capacity
            ),
            "reproduction_rejected_resource_total": (
                self.total_reproduction_rejected_resource
            ),
            "reproduction_rejected_other_total": (
                self.total_reproduction_rejected_other
            ),
            "mean_energy": mean_energy,
            "mean_integrity": mean_integrity,
            "mean_age": mean_age,
            "lineages": lineage_count,
            "groups": stats.group_count,
            "mean_group_size": stats.mean_group_size,
            "grouped_fraction": grouped_fraction,
            "social_dependency_proxy": social_dependency,
            "strategy_mean_abs_weight": strategy_mean_abs_weight,
            "raw_strategy_gene_diversity": raw_strategy_gene_diversity,
            "move_social_fraction": stats.move_social_fraction,
            "harvested_energy_step": stats.harvested_energy,
            "shared_energy_step": stats.shared_energy,
            "shared_energy_total": self.total_shared_energy,
            "benefit_classification_residual_step": (
                stats.shared_energy - float(stats.benefit_flow_energy.sum())
            ),
            "benefit_internal_energy_step": stats.benefit_internal_energy,
            "benefit_group_to_group_energy_step": float(
                stats.benefit_flow_energy[BenefitFlowKind.GROUP_TO_GROUP]
            ),
            "benefit_group_to_ungrouped_energy_step": float(
                stats.benefit_flow_energy[BenefitFlowKind.GROUP_TO_UNGROUPED]
            ),
            "benefit_ungrouped_to_group_energy_step": float(
                stats.benefit_flow_energy[BenefitFlowKind.UNGROUPED_TO_GROUP]
            ),
            "benefit_cross_boundary_energy_step": (
                stats.benefit_cross_boundary_energy
            ),
            "benefit_unbounded_energy_step": stats.benefit_unbounded_energy,
            "benefit_boundary_cohesion_step": (
                stats.benefit_internal_energy / step_boundary_energy
                if step_boundary_energy > 0.0
                else 0.0
            ),
            "benefit_boundary_coverage_step": (
                step_boundary_energy / step_benefit_energy
                if step_benefit_energy > 0.0
                else 0.0
            ),
            "benefit_boundary_outgoing_retention_step": (
                stats.benefit_internal_energy / step_outgoing_boundary_energy
                if step_outgoing_boundary_energy > 0.0
                else 0.0
            ),
            "benefit_internal_energy_total": self.benefit_internal_energy_total,
            "benefit_group_to_group_energy_total": float(
                self.benefit_flow_energy_total[BenefitFlowKind.GROUP_TO_GROUP]
            ),
            "benefit_group_to_ungrouped_energy_total": float(
                self.benefit_flow_energy_total[BenefitFlowKind.GROUP_TO_UNGROUPED]
            ),
            "benefit_ungrouped_to_group_energy_total": float(
                self.benefit_flow_energy_total[BenefitFlowKind.UNGROUPED_TO_GROUP]
            ),
            "benefit_cross_boundary_energy_total": (
                self.benefit_cross_boundary_energy_total
            ),
            "benefit_unbounded_energy_total": self.benefit_unbounded_energy_total,
            "benefit_boundary_cohesion_total": (
                self.benefit_internal_energy_total / total_boundary_energy
                if total_boundary_energy > 0.0
                else 0.0
            ),
            "benefit_boundary_coverage_total": (
                total_boundary_energy / total_benefit_energy
                if total_benefit_energy > 0.0
                else 0.0
            ),
            "benefit_boundary_outgoing_retention_total": (
                self.benefit_internal_energy_total / total_outgoing_boundary_energy
                if total_outgoing_boundary_energy > 0.0
                else 0.0
            ),
            "signals_step": stats.signals,
            "direct_messages_step": stats.direct_messages,
            "action_entropy": stats.action_entropy,
            "signal_detection_rate": stats.signal_detection_rate,
            "partner_detection_rate": stats.partner_detection_rate,
            "environment_seconds": stats.environment_seconds,
            "spatial_seconds": stats.spatial_seconds,
            "observation_seconds": stats.observation_seconds,
            "policy_seconds": stats.policy_seconds,
            "conflict_seconds": stats.conflict_seconds,
            "graph_seconds": stats.graph_seconds,
            "device_commit_seconds": stats.device_commit_seconds,
            "evolution_evaluation_seconds": stats.evolution_evaluation_seconds,
            "gpu_h2d_bytes": stats.gpu_h2d_bytes,
            "gpu_d2h_bytes": stats.gpu_d2h_bytes,
            "gpu_direct_message_events": stats.gpu_direct_message_events,
            "gpu_direct_dense_bytes_avoided": stats.gpu_direct_dense_bytes_avoided,
            "gpu_entity_commit_bytes": stats.gpu_entity_commit_bytes,
            "step_seconds": elapsed,
            "wall_elapsed_seconds": wall_elapsed,
            "window_seconds": window_seconds,
            "window_ticks": window_ticks,
            "window_seconds_per_tick": window_seconds / max(window_ticks, 1),
        }
        if self.experiment_mode is ExperimentMode.ENTERTAINMENT:
            row.update(
                {
                    "entertainment_heuristic_guidance_actions_step": (
                        stats.heuristic_guidance_actions
                    ),
                    "entertainment_override_alive": autonomy_restored_alive,
                    "entertainment_override_cohort_alive": autonomy_cohort_alive,
                    "entertainment_override_cohort_survival_fraction": (
                        autonomy_cohort_alive / autonomy_cohort_size
                        if autonomy_cohort_size
                        else 0.0
                    ),
                    "entertainment_override_cohort_mean_energy": autonomy_cohort_mean_energy,
                    "entertainment_override_cohort_mean_harvested_energy_total": (
                        autonomy_cohort_mean_harvested
                    ),
                    "entertainment_override_actions_step": stats.autonomy_module_actions,
                    "entertainment_override_use_fraction_step": (
                        stats.autonomy_module_actions / stats.autonomy_restored_active
                        if stats.autonomy_restored_active
                        else 0.0
                    ),
                    "entertainment_override_harvest_attempts_step": (
                        stats.autonomy_harvest_attempts
                    ),
                    "entertainment_override_harvest_success_rate_step": (
                        stats.autonomy_harvest_successes
                        / stats.autonomy_harvest_attempts
                        if stats.autonomy_harvest_attempts
                        else 0.0
                    ),
                    "entertainment_override_independent_harvest_success_rate": (
                        autonomy_harvest_success_rate
                    ),
                }
            )
        row.update(self.subjects.summary())
        return row

    def run(self, until_tick: int | None = None) -> dict[str, float | int]:
        """Advance to an absolute tick and finalize this run's outputs.

        ``until_tick`` is absolute rather than a step count so a simulation
        can be advanced to a counterfactual branch point with ``step()`` and
        then finish at the configured horizon without extending the run.
        """
        target_tick = self.cfg.run.ticks if until_tick is None else int(until_tick)
        if target_tick < self.tick:
            raise ValueError(
                f"until_tick {target_tick} precedes current tick {self.tick}"
            )
        started = time.perf_counter()
        window_started = started
        run_start_tick = self.tick
        window_start_tick = self.tick
        final_row: dict[str, float | int] = {}
        last_stats: StepStats | None = None
        last_step_seconds = 0.0
        previous_defer_gpu_field_sync = self._defer_gpu_field_sync
        if self.gpu_runtime is not None:
            self._defer_gpu_field_sync = True
        try:
            for _ in range(target_tick - self.tick):
                step_started = time.perf_counter()
                stats = self.step()
                elapsed = time.perf_counter() - step_started
                last_stats = stats
                last_step_seconds = elapsed
                if (
                    self.tick % self.cfg.run.metrics_period == 0
                    or self.tick == run_start_tick + 1
                ):
                    reported_at = time.perf_counter()
                    window_ticks = self.tick - window_start_tick
                    window_seconds = reported_at - window_started
                    final_row = self.metric_row(
                        stats,
                        elapsed,
                        wall_elapsed=reported_at - started,
                        window_seconds=window_seconds,
                        window_ticks=window_ticks,
                    )
                    self.metrics.write(final_row)
                    print(
                        f"tick={self.tick:7d} alive={final_row['alive']:7d} "
                        f"groups={final_row['groups']:5d} E={final_row['mean_energy']:.3f} "
                        f"step={elapsed:.3f}s window_avg={final_row['window_seconds_per_tick']:.3f}s "
                        f"wall={final_row['wall_elapsed_seconds']:.1f}s"
                    )
                    # Start the next window before output/checkpoint work so
                    # its average includes the non-step costs users observe.
                    window_started = reported_at
                    window_start_tick = self.tick
                if self.tick % self.cfg.run.checkpoint_period == 0:
                    self._checkpoint()
                if not np.any(self.entities.alive):
                    break
            if not final_row or int(final_row["tick"]) != self.tick:
                reported_at = time.perf_counter()
                window_ticks = self.tick - window_start_tick
                final_row = self.metric_row(
                    last_stats if last_stats is not None else StepStats(),
                    last_step_seconds,
                    wall_elapsed=reported_at - started,
                    window_seconds=reported_at - window_started,
                    window_ticks=window_ticks,
                )
                self.metrics.write(final_row)
                print(
                    f"tick={self.tick:7d} alive={final_row['alive']:7d} "
                    f"groups={final_row['groups']:5d} E={final_row['mean_energy']:.3f} "
                    f"step={last_step_seconds:.3f}s window_avg={final_row['window_seconds_per_tick']:.3f}s "
                    f"wall={final_row['wall_elapsed_seconds']:.1f}s"
                )
        finally:
            if self.gpu_runtime is not None:
                self.gpu_runtime.sync_to_host(self.environment, self.information)
            self._defer_gpu_field_sync = previous_defer_gpu_field_sync
            self.metrics.close()
            self.evolution_progress.close()
            if self._trajectory_file is not None:
                self._trajectory_file.close()
        interventions_metadata: dict[str, object] = {
            "social_control_enabled": self.social_control_enabled,
            "social_connections_enabled": self.social_connections_enabled,
            "direct_messages_enabled": self.direct_messages_enabled,
            "freeze_genotype": self.freeze_genotype,
            "environment_spatial_reversed": self.environment.spatial_reversed,
            "history": self.intervention_history,
        }
        control_metadata: dict[str, object] = {
            "arbiter": type(self.control_arbiter).__name__,
            "base_arbiter": (
                type(self.control_arbiter.base).__name__
                if isinstance(self.control_arbiter, AutonomyRecoveryArbiter)
                else type(self.control_arbiter).__name__
            ),
        }
        if self.experiment_mode is ExperimentMode.ENTERTAINMENT:
            control_metadata.update(
                {
                    "heuristic_social_guidance_enabled": (
                        self.cfg.control.heuristic_social_guidance
                    ),
                    "heuristic_social_guidance_weight": (
                        self.cfg.control.heuristic_social_guidance_weight
                    ),
                    "heuristic_guidance_actions": self.heuristic_guidance_actions,
                }
            )
            interventions_metadata["direct_action_override_enabled"] = (
                self.autonomy_recovery_enabled
            )
            control_metadata["entertainment_action_override"] = {
                "module": "independent-foraging-v1",
                "treatment_tick": self.autonomy_recovery_tick,
                "cohort_tick": self.autonomy_cohort_tick,
                "treated": self.autonomy_recovery_enabled,
                "configured_fraction": self.cfg.control.autonomy_recovery_fraction,
                "cohort_size": int(self.autonomy_recovery_cohort_ids.size),
                "cohort_entity_ids": self.autonomy_recovery_cohort_ids.tolist(),
                "cohort_alive": int(
                    np.count_nonzero(
                        self.autonomy_observation_cohort & self.entities.alive
                    )
                ),
                "treated_alive": int(
                    np.count_nonzero(self.autonomy_restored & self.entities.alive)
                ),
                "module_actions": self.autonomy_module_actions,
                "harvest_attempts": self.autonomy_harvest_attempts,
                "harvest_successes": self.autonomy_harvest_successes,
            }
        metadata = {
            "version": __version__,
            "execution_backend": self.execution_backend,
            "experiment_mode": self.experiment_mode.value,
            "scientific_validity": self.scientific_validity(),
            "ticks_completed": self.tick,
            "wall_seconds": time.perf_counter() - started,
            "final": final_row,
            "action_counts": {action.name: int(self.action_counts[action]) for action in Action},
            "subject_graph": self.subjects.summary(),
            "evolution_progress": {
                "period": self.cfg.run.evolution_evaluation_period,
                "evaluations": len(self.evolution_progress.records),
                "last": (
                    self.evolution_progress.records[-1]
                    if self.evolution_progress.records
                    else None
                ),
            },
            "interventions": interventions_metadata,
            "control": control_metadata,
            "group_planning": {
                "planner": type(self.group_label_planner).__name__,
                "last_plan_tick": self.last_group_plan.tick,
                "last_plan_groups": self.last_group_plan.group_count,
                "last_plan_members": self.last_group_plan.member_count,
            },
            "device_entity_state": {
                "version": self.entity_device_version,
                "last_commit_bytes": (
                    self.last_entity_device_commit.semantic_transfer_nbytes
                    if self.last_entity_device_commit is not None
                    else 0
                ),
            },
        }
        (self.output_dir / "run_metadata.json").write_text(
            json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        return final_row
