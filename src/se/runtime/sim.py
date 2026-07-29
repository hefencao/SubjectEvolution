from __future__ import annotations

from dataclasses import dataclass, field, replace
import copy
import hashlib
import json
import platform
from pathlib import Path
from typing import Callable
import sys
import time
import numpy as np
from .. import __version__
from ..backend import BackendUnavailableError, resolve_backend
from ..checkpointing import read_checkpoint_bundle, write_checkpoint_bundle
from ..cfg import SimulationConfig
from se.subjects.control import (
    AutonomyRecoveryArbiter,
    ControlArbiter,
    ControllerKind,
    HeuristicSocialGuidanceArbiter,
    SingleProposalControlArbiter,
    autonomy_recovery_control_proposal,
    body_control_proposal,
    social_guidance_control_proposal,
)
from ..device_state import EntityDeviceCommitPlan, build_entity_device_commit_plan
from se.differentiation.capacity import (
    capacity_development_energy,
    capacity_maintenance_energy,
)
from se.differentiation.functional import (
    EMBODIED_OUTPUT_COUNT,
    PHYSIOLOGICAL_OUTPUT_COUNT,
    embodied_outputs_enabled,
    functional_module_energy,
)
from se.env.danger_evidence import (
    DANGER_EVIDENCE_SCALE,
    danger_evidence_diagnostics,
    danger_evidence_enabled,
    danger_evidence_quantized,
)
from se.env.world import Environment
from se.env.diversity import (
    ORTHOGONAL_ENVIRONMENT_SCHEMA,
    resource_field_diversity_metrics,
)
from se.env.process import build_environment_process, environment_process_metadata
from se.evolution.progress import (
    BENEFIT_FLOW_COUNT,
    BenefitFlowKind,
    EvolutionProgressTracker,
    LaggedBenefitBoundary,
    actual_context_policy_diagnostics,
    benefit_flow_totals,
)
from ..execution import (
    ActionConflictResolver,
    ActionResolutionSnapshot,
    DeterministicActionConflictResolver,
    GpuActionConflictResolver,
    ShareResolution,
)
from ..gpu_runtime import HybridGpuRuntime
from ..information import InformationSystem, SignalEmissionBatch, SignalEmissionPlan, SignalEmissionScheduler
from se.experiments.interventions import ExperimentMode, resolve_intervention
from ..intents import (
    ActionIntentBatch,
    ActionResolutionBatch,
    FailureReason,
    build_intents,
)
from se.knowledge import (
    KnowledgeOutcomePlan,
    KnowledgeStepStats,
    KnowledgeSystem,
    OUTCOME_STATUS_FAILED,
    OUTCOME_STATUS_PARTIAL,
    OUTCOME_STATUS_SUCCESS,
    encode_local_context,
)
from se.knowledge.policy import (
    KnowledgePolicyPlan,
    build_knowledge_policy_plan,
    build_latent_knowledge_policy_plan,
)
from se.knowledge.routing_cost import RoutingCostBudgetResult, apply_routing_cost_budget
from se.knowledge.latent import latent_router_state_features
from se.knowledge.working_memory import (
    WorkingMemoryUpdateResult,
    build_working_memory_update,
    expected_outcomes_for_actions,
    memory_float_view,
    quantize_memory_observation,
)
from se.evolution.lifecycle import (
    BirthAllocationPlan,
    DeathCause,
    DeathEventPlan,
    empty_birth_allocation_plan,
    empty_death_event_plan,
    plan_birth_allocations,
    plan_death_events,
)
from ..metrics import MetricsWriter
from se.env.local_stress import LocalStressDiagnostics
from ..event_cohort import EventCohortDiagnostics
from se.subjects.succession import SubjectStructureDiagnostics
from se.env.atlas import EnvironmentAtlasDiagnostics
from se.differentiation.physiology import resource_metabolism_enabled
from se.env.niches import (
    AFFINITY_SCALE,
    RESOURCE_CHANNELS,
    active_morphology_traits,
    apply_harvest_effects,
    policy_resource_view,
    public_resource_signal,
    resource_affinity_diagnostics,
    resource_affinity_quantized,
    selective_harvest_enabled,
)
from ..policy import Action, ParametricPolicy
from ..random_api import RandomContext, Stream, bernoulli, normal, uniform01
from se.subjects.social import (
    DeterministicGroupLabelPlanner,
    GroupLabelPlan,
    GroupLabelPlanner,
    GroupSummary,
    SocialSystem,
    build_share_relation_update_plan,
    ungrouped_group_label_plan,
)
from se.env.spatial import SpatialIndex
from se.subjects.graph import CandidateSubjectGraph
from .checkpointing import SimulationCheckpointMixin
from .experiments import SimulationExperimentMixin
from .reporting import SimulationReportingMixin
from .state import EntityState, StepStats, _wrap_periodic_float32
from .embodied import apply_material_repair, movement_cost_with_power
from .harvest_commit import commit_harvest_resolution
from .resource_metabolism import (
    initialize_resource_metabolism_state,
    raw_harvest_room,
    record_resource_recycling_after_environment_update,
    record_resource_store_death_loss,
    settle_resource_metabolism_before_step,
    storage_room_fraction,
)
from .functional_execution import (
    add_physiology_capacity_maintenance_cost,
    add_physiology_terrain_cost,
    augment_gradient_with_oxygen,
    apply_gpu_oxygen_steering,
    apply_physiology_settlement,
    evaluate_functional_outputs,
    initialize_functional_runtime_state,
    physiology_checkpoint_arrays,
    record_physiology_capacity_development_cost,
)
class Simulation(SimulationCheckpointMixin, SimulationExperimentMixin, SimulationReportingMixin):
    def __init__(
        self,
        cfg: SimulationConfig,
        output_dir: str | Path,
        *,
        backend: str = "auto",
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
        self.requested_backend = requested_backend
        self.gpu_semantics_mode = cfg.run.gpu_semantics_mode
        self.gpu_device_validated = False
        self.gpu_acceleration_enabled = False
        self.gpu_fallback_used = False
        self.gpu_fallback_reason: str | None = None
        if requested_backend == "cpu":
            self.gpu_runtime: HybridGpuRuntime | None = None
            self.execution_backend = "cpu"
        elif requested_backend in {"gpu", "auto"}:
            if self.gpu_semantics_mode == "strict-reference":
                # Historical diagnostic mode: validate CUDA when available but
                # intentionally keep the CPU world authoritative.  Missing CUDA
                # is a recorded CPU fallback for both auto and explicit gpu so
                # long-run orchestration can remain portable across hosts.
                try:
                    resolve_backend("gpu")
                except BackendUnavailableError as exc:
                    self.gpu_runtime = None
                    self.gpu_fallback_used = True
                    self.gpu_fallback_reason = str(exc)
                    self.execution_backend = "cpu-fallback-no-gpu"
                else:
                    self.gpu_runtime = None
                    self.gpu_device_validated = True
                    self.execution_backend = "gpu-strict-reference"
            else:
                # Production default: use the real hybrid GPU path whenever a
                # compatible CuPy/CUDA device is usable.  Backend validation is
                # delegated to test_parity; runtime availability alone decides
                # whether this host accelerates or records a CPU fallback.
                try:
                    self.gpu_runtime = HybridGpuRuntime(cfg, backend="gpu")
                except BackendUnavailableError as exc:
                    self.gpu_runtime = None
                    self.gpu_fallback_used = True
                    self.gpu_fallback_reason = str(exc)
                self.gpu_acceleration_enabled = self.gpu_runtime is not None
                self.gpu_device_validated = self.gpu_runtime is not None
                self.execution_backend = (
                    "gpu-hybrid-accelerated"
                    if self.gpu_runtime is not None
                    else "cpu-fallback-no-gpu"
                )
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
        if cfg.differentiation.enabled:
            all_entity_slots = np.arange(cfg.world.max_entities, dtype=np.int32)
            self.social.set_effective_capacities(
                all_entity_slots, self.entities.relation_capacity
            )
        body_subjects, lineage_subjects = self.subjects.register_bodies(
            initial, self.entities.lineage_id, tick=0
        )
        self.entities.primary_subject_id[initial] = body_subjects
        self.entities.lineage_subject_id[initial] = lineage_subjects
        self.knowledge = KnowledgeSystem(
            cfg,
            self.output_dir,
            initial_entity_ids=self.entities.entity_id[initial],
            initial_subject_ids=self.entities.primary_subject_id[initial],
            initial_knowledge_capacities=(
                self.entities.knowledge_capacity_bytes[initial]
            ),
        )
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
        self.total_harvested_resources = np.zeros(4, dtype=np.float64)
        self.total_requested_harvest_resources = np.zeros(4, dtype=np.float64)
        initialize_resource_metabolism_state(self)
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
        initialize_functional_runtime_state(self)
        morphology_indices, morphology_names = active_morphology_traits(cfg)
        self.evolution_progress = EvolutionProgressTracker(
            self.output_dir,
            period=cfg.run.evolution_evaluation_period,
            run_seed=cfg.run.seed,
            temperature=cfg.policy.temperature,
            alive=self.entities.alive,
            stable_ids=self.entities.entity_id,
            genotype=self.entities.genotype,
            long_run_diagnostics_enabled=cfg.run.long_run_diagnostics_enabled,
            long_run_diagnostics_schema=cfg.run.long_run_diagnostics_schema,
            morphology_trait_indices=morphology_indices,
            morphology_trait_names=morphology_names,
        )
        self.local_stress_diagnostics = (
            LocalStressDiagnostics(
                world_width=cfg.world.width,
                world_height=cfg.world.height,
                regions_x=cfg.run.spatial_stress_regions_x,
                regions_y=cfg.run.spatial_stress_regions_y,
                resource_capacity=cfg.environment.resource_capacity,
                world_grid_x=cfg.world.grid_x,
                world_grid_y=cfg.world.grid_y,
                schema=cfg.run.spatial_stress_diagnostics_schema,
                region_schema=cfg.run.spatial_stress_region_schema,
            )
            if cfg.run.spatial_stress_diagnostics_enabled
            else None
        )
        self.subject_structure_diagnostics = (
            SubjectStructureDiagnostics(
                self.output_dir,
                schema=cfg.run.subject_structure_diagnostics_schema,
            )
            if cfg.run.subject_structure_diagnostics_enabled
            else None
        )
        self.environment_atlas_diagnostics = (
            EnvironmentAtlasDiagnostics(
                self.output_dir,
                world_width=cfg.world.width,
                world_height=cfg.world.height,
                world_grid_x=cfg.world.grid_x,
                world_grid_y=cfg.world.grid_y,
                resource_capacity=cfg.environment.resource_capacity,
                scales=cfg.run.environment_atlas_scales,
                schema=cfg.run.environment_atlas_diagnostics_schema,
            )
            if cfg.run.environment_atlas_diagnostics_enabled
            else None
        )
        # Run-local, diagnostic-only endpoint cohort decomposition used by
        # preregistered natural-event branches. It is never checkpoint state and
        # never feeds the world.
        self.event_cohort_diagnostics: EventCohortDiagnostics | None = None
        self.last_active = np.empty(0, dtype=np.int32)
        self.last_cells = np.empty(0, dtype=np.int32)
        self.last_local_resources = np.empty((0, 4), dtype=np.float32)
        self.last_information = None
        self.last_policy_decision: PolicyDecision | None = None
        self.last_knowledge_policy_plan = KnowledgePolicyPlan.empty(0)
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
        self.capacity_ablation_enabled = False
        self.resource_affinity_ablation_enabled = False
        self.resource_processing_support_ablation_enabled = False
        self.functional_modules_ablation_enabled = False
        self.functional_module_coupling_ablation_enabled = False
        self.functional_module_ablation_mask = np.zeros(
            int(cfg.functional_modules.module_count), dtype=bool
        )
        # Experimental lineage-targeted D2 ablations are empty on the
        # authoritative path. They are populated only by the paired lineage
        # audit and never modify genotype or lineage membership.
        self.functional_module_lineage_output_ablation: dict[int, set[int]] = {}
        self.functional_module_lineage_cost_ablation: dict[int, set[int]] = {}
        self.danger_evidence_ablation_enabled = False
        self.knowledge_policy_ablation_enabled = False
        self.knowledge_transfer_ablation_enabled = False
        self.group_refresh_ablation_enabled = False
        self.intervention_history: list[dict[str, object]] = []
        self.checkpoint_lineage: list[dict[str, object]] = []
        # Interactive ``step()`` calls keep host field mirrors current.  A
        # monolithic ``run()`` can defer that costly device->host copy until
        # completion because every intervening field consumer is device-side.
        self._defer_gpu_field_sync = False
        self._trajectory_file = None
        if cfg.run.trajectory_subject_ids:
            self._trajectory_file = (self.output_dir / "trajectory.jsonl").open("w", encoding="utf-8")
        self._write_run_manifest(backend)

    def _validate_invariants(self) -> None:
        ent = self.entities
        active = np.flatnonzero(ent.alive)
        inactive = np.flatnonzero(~ent.alive)
        ids = ent.entity_id[active]
        if np.any(ids == 0) or np.unique(ids).size != ids.size:
            raise AssertionError("living entity IDs must be positive and unique")
        if np.any(ent.entity_id[inactive] != 0):
            raise AssertionError("inactive entity slots must not retain entity IDs")
        free = np.asarray(ent.free_slots, dtype=np.int64)
        if free.size != inactive.size or np.unique(free).size != free.size or not np.array_equal(
            np.sort(free), inactive
        ):
            raise AssertionError("alive/free-pool invariant failed")
        if active.size and (
            np.any(~np.isfinite(ent.energy[active]))
            or np.any(ent.energy[active] < -1e-6)
            or np.any(ent.energy[active] > self.cfg.entities.max_energy + 1e-5)
            or np.any(~np.isfinite(ent.integrity[active]))
            or np.any(ent.integrity[active] <= 0.0)
            or np.any(~np.isfinite(ent.fertility[active]))
            or np.any(ent.fertility[active] < 0.0)
        ):
            raise AssertionError("living entity dynamic-state invariant failed")
        if self.cfg.world.periodic and active.size:
            active_x = ent.x[active]
            active_y = ent.y[active]
            invalid_position = (
                ~np.isfinite(active_x)
                | ~np.isfinite(active_y)
                | (active_x < 0.0)
                | (active_x >= self.cfg.world.width)
                | (active_y < 0.0)
                | (active_y >= self.cfg.world.height)
            )
            if np.any(invalid_position):
                local = int(np.flatnonzero(invalid_position)[0])
                slot = int(active[local])
                raise AssertionError(
                    "periodic position invariant failed: "
                    f"slot={slot} entity_id={int(ent.entity_id[slot])} "
                    f"x={float(ent.x[slot])!r} y={float(ent.y[slot])!r} "
                    f"width={self.cfg.world.width!r} height={self.cfg.world.height!r}"
                )
        if np.any(self.social.group_id[~ent.alive] != 0):
            raise AssertionError("dead entities must not retain group membership")
        if active.size and not np.array_equal(
            self.social.effective_capacity[active].astype(np.uint16),
            ent.relation_capacity[active],
        ):
            raise AssertionError("social relation capacity diverged from entity phenotype")
        if np.any(ent.working_memory_capacity > self.cfg.knowledge.working_memory_width):
            raise AssertionError("working-memory capacity exceeds physical width")
        if np.any(ent.knowledge_capacity_bytes > self.cfg.knowledge.holder_capacity_bytes):
            raise AssertionError("knowledge capacity exceeds physical byte limit")
        if np.any(ent.knowledge_attention_capacity > self.cfg.knowledge.attention_slots_per_tick):
            raise AssertionError("attention capacity exceeds physical slot limit")
        if self.cfg.knowledge.working_memory_enabled:
            width = int(self.cfg.knowledge.working_memory_width)
            if ent.working_memory_q.shape != (ent.alive.size, width):
                raise AssertionError("working-memory state shape invariant failed")
            clip_q = max(
                1,
                int(round(
                    float(self.cfg.knowledge.working_memory_activation_clip)
                    * int(self.cfg.knowledge.working_memory_quantization_scale)
                )),
            )
            if active.size and np.any(
                np.abs(ent.working_memory_q[active].astype(np.int32)) > clip_q
            ):
                raise AssertionError("working-memory quantized range invariant failed")
            expected_memory = memory_float_view(
                ent.working_memory_q[active],
                self.cfg.knowledge,
                effective_widths=ent.working_memory_capacity[active],
            )
            if active.size and not np.array_equal(
                ent.memory[active], expected_memory, equal_nan=True
            ):
                raise AssertionError("working-memory float-view invariant failed")
            if inactive.size and (
                np.any(ent.working_memory_q[inactive] != 0)
                or np.any(ent.working_memory_previous_observation_q[inactive] != 0)
            ):
                raise AssertionError("inactive slots retain working-memory state")
        self.knowledge.validate(ent.alive, ent.primary_subject_id)

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

    def _finalize_share_capacity(
        self,
        share: ShareResolution,
        resolutions: ActionResolutionBatch,
    ) -> ShareResolution:
        """Re-arbitrate receiver capacity against post-harvest energy.

        The intent resolver observes the pre-commit snapshot.  A target may
        harvest in the same commit phase, so its remaining capacity can be
        smaller by the time shares are applied.  Re-scaling here preserves the
        max-energy invariant and updates relation/audit plans to the amount
        actually committed rather than silently discarding overflow.
        """
        if share.rows.size == 0:
            return share
        proposed = np.asarray(share.amounts, dtype=np.float32)
        safe_targets = np.where(share.valid_target, share.target_indices, 0)
        total_by_target = np.bincount(
            safe_targets,
            weights=np.where(share.valid_target, proposed, 0.0),
            minlength=self.entities.alive.size,
        ).astype(np.float32)
        capacity = np.maximum(
            self.cfg.entities.max_energy - self.entities.energy, 0.0
        ).astype(np.float32)
        scale = np.ones(self.entities.alive.size, dtype=np.float32)
        occupied = total_by_target > 0.0
        scale[occupied] = np.minimum(
            1.0, capacity[occupied] / total_by_target[occupied]
        )
        actual = proposed * scale[safe_targets]
        success = share.valid_target & (actual > 1e-8)
        resolutions.success[share.rows] = success
        capacity_failed = share.valid_target & (proposed > 1e-8) & ~success
        resolutions.failure_reason[share.rows[capacity_failed]] = (
            FailureReason.INSUFFICIENT_CAPACITY
        )
        resolutions.resource_delta[share.rows, 0] = -actual
        relation_updates = build_share_relation_update_plan(
            self.cfg,
            share.rows,
            share.owner_indices,
            share.target_indices,
            success,
            share.valid_target,
            self.tick,
        )
        return ShareResolution(
            rows=share.rows,
            owner_indices=share.owner_indices,
            target_indices=share.target_indices,
            amounts=actual.astype(np.float32, copy=False),
            success=success,
            valid_target=share.valid_target,
            relation_updates=relation_updates,
        )

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

        if self.local_stress_diagnostics is not None:
            self.local_stress_diagnostics.observe_benefits(
                owner_indices=owners,
                target_indices=targets,
                group_ids=self.social.group_id,
                stable_ids=self.entities.entity_id,
                amounts=amounts,
                x=self.entities.x,
                y=self.entities.y,
            )
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
        strength_multiplier: np.ndarray | None = None,
    ) -> tuple[SignalEmissionPlan, int, float]:
        if actors.size == 0:
            return SignalEmissionPlan(()), 0, 0.0
        ent = self.entities
        actor_cells = cells
        multiplier = (
            np.ones(actors.size, dtype=np.float32)
            if strength_multiplier is None
            else np.asarray(strength_multiplier, dtype=np.float32)
        )
        if multiplier.shape != (actors.size,):
            raise ValueError("signal strength multiplier must match actors")
        resource_signal = public_resource_signal(local_resources, self.cfg)
        strengths_resource = (
            np.clip(resource_signal, 0.0, 2.0) * 0.15 * multiplier
        )
        actor_evidence_q = (
            (
                np.full(
                    (actors.size, 2),
                    DANGER_EVIDENCE_SCALE,
                    dtype=np.int32,
                )
                if self.danger_evidence_ablation_enabled
                else danger_evidence_quantized(ent.genotype[actors], self.cfg)
            )
            if danger_evidence_enabled(self.cfg)
            else None
        )
        hazard = (
            self.gpu_runtime.danger_for_cells(actor_cells, actor_evidence_q)
            if self.gpu_runtime is not None
            else self.environment.danger_for_cells(actor_cells, actor_evidence_q)
        )
        strengths_danger = hazard * 0.15 * multiplier
        group_member = self.social.group_id[actors] != 0
        strengths_social = group_member.astype(np.float32) * 0.12 * multiplier
        signal_plan = SignalEmissionPlan(
            batches=(
                SignalEmissionBatch(0, actor_cells, strengths_resource, emitter="actor-resource"),
                SignalEmissionBatch(1, actor_cells, strengths_danger, emitter="actor-danger"),
                SignalEmissionBatch(2, actor_cells, strengths_social, emitter="actor-social"),
            )
        )
        signal_energy = (
            float(self.cfg.entities.signal_cost)
            * np.square(multiplier.astype(np.float64))
        )
        ent.energy[actors] -= signal_energy.astype(np.float32)
        valid_target = (target_indices >= 0) & ent.alive[target_indices]
        safe_targets = np.where(valid_target, target_indices, 0)
        payloads = np.stack(
            [resource_signal, hazard, group_member.astype(np.float32)], axis=1
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
        return signal_plan, direct_messages, float(signal_energy.sum(dtype=np.float64))

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
        self.knowledge.flush()
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
            **physiology_checkpoint_arrays(self),
            harvested_resources_total=self.total_harvested_resources,
            **(
                {
                    "working_memory_q": self.entities.working_memory_q[active],
                    "working_memory_previous_observation_q": (
                        self.entities.working_memory_previous_observation_q[active]
                    ),
                }
                if self.cfg.knowledge.working_memory_enabled else {}
            ),
            **(self.knowledge.checkpoint_arrays() if self.cfg.knowledge.enabled else {}),
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
        if self.cfg.run.full_checkpoint_enabled:
            self.save_full_checkpoint()

    def step(self) -> StepStats:
        cfg = self.cfg
        ent = self.entities
        stats = StepStats()
        knowledge_stats = stats.knowledge
        evaluation_due = self.evolution_progress.due(self.tick + 1)
        actual_context_metrics: dict[str, object] | None = None
        knowledge_context_keys: np.ndarray | None = None
        knowledge_policy_plan = KnowledgePolicyPlan.empty(self.tick)
        cost_free_knowledge_policy_plan = KnowledgePolicyPlan.empty(self.tick)
        routing_cost_result: RoutingCostBudgetResult | None = None
        working_memory_state_features: np.ndarray | None = None
        working_memory_actual_outcomes: np.ndarray | None = None
        working_memory_update_result: WorkingMemoryUpdateResult | None = None
        effective_resource_affinity_q: np.ndarray | None = None
        effective_harvest_preference_q: np.ndarray | None = None
        effective_embodied_output_q = np.zeros(
            (ent.alive.size, EMBODIED_OUTPUT_COUNT), dtype=np.int32
        )
        effective_physiology_output_q = np.zeros(
            (ent.alive.size, PHYSIOLOGICAL_OUTPUT_COUNT), dtype=np.int32
        )
        functional_computation_load = np.zeros(ent.alive.size, dtype=np.float32)
        local_physiology = np.zeros((0, 3), dtype=np.float32)
        movement_speed_multiplier = np.ones(ent.alive.size, dtype=np.float32)
        signal_strength_multiplier = np.ones(ent.alive.size, dtype=np.float32)
        functional_context_metrics: dict[str, object] = {}
        effective_danger_evidence_q: np.ndarray | None = None
        settle_resource_metabolism_before_step(self, stats)
        policy_energy = ent.energy
        if self.gpu_runtime is None:
            phase_started = time.perf_counter()
            self.environment.update(self.tick)
            record_resource_recycling_after_environment_update(self, stats)
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
            local_physiology = self.environment.physiology_for_cells(cells)
            effective_resource_affinity_q = (
                np.full(
                    (ent.alive.size, RESOURCE_CHANNELS),
                    AFFINITY_SCALE,
                    dtype=np.int32,
                )
                if self.resource_affinity_ablation_enabled
                else resource_affinity_quantized(ent.genotype, cfg)
            )
            active_storage_room_fraction = storage_room_fraction(
                ent,
                active,
                cfg,
                genotype=ent.genotype[active],
                gene_start=self.policy.physiology_gene_start(cfg),
            )
            policy_local_resources = policy_resource_view(
                local_resources,
                ent.genotype[active],
                cfg,
                resource_affinity_q=effective_resource_affinity_q[active],
                storage_room_fraction=active_storage_room_fraction,
            )
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
            effective_danger_evidence_q = (
                (
                    np.full(
                        (ent.alive.size, 2),
                        DANGER_EVIDENCE_SCALE,
                        dtype=np.int32,
                    )
                    if self.danger_evidence_ablation_enabled
                    else danger_evidence_quantized(ent.genotype, cfg)
                )
                if danger_evidence_enabled(cfg)
                else None
            )
            resource_gradient, danger_gradient = self.environment.gradients_for_entities(
                self.spatial.entity_cells,
                ent.alive.size,
                effective_resource_affinity_q,
                effective_danger_evidence_q,
            )
            resource_gradient = augment_gradient_with_oxygen(self, resource_gradient)
            if cfg.knowledge.enabled and cfg.knowledge.learning_enabled:
                knowledge_context_keys = encode_local_context(
                    policy_local_resources[:, 0],
                    self.environment.danger_for_cells(
                        cells,
                        (
                            effective_danger_evidence_q[active]
                            if effective_danger_evidence_q is not None
                            else None
                        ),
                    ),
                    ent.energy[active],
                    ent.integrity[active],
                    self.social.group_id[active] != 0,
                    max_energy=cfg.entities.max_energy,
                )
                router_state = None
                if cfg.knowledge.working_memory_enabled:
                    router_state = latent_router_state_features(
                        energy=ent.energy[active],
                        integrity=ent.integrity[active],
                        fertility=ent.fertility[active],
                        local_resource=policy_local_resources[:, 0],
                        max_energy=cfg.entities.max_energy,
                        resource_capacity=cfg.environment.resource_capacity[0],
                    )
                    working_memory_state_features = np.asarray(
                        router_state, dtype=np.float32
                    ).copy()
                if (
                    cfg.knowledge.policy_influence_enabled
                    and not self.knowledge_policy_ablation_enabled
                ):
                    active_genotype = ent.genotype[active]
                    if cfg.knowledge.latent_policy_enabled:
                        if self.knowledge.latent_store is None:
                            raise RuntimeError("latent policy is enabled without a latent content store")
                        self.knowledge.latent_store.ensure_catalog(self.knowledge.catalog)
                        if router_state is None:
                            router_state = latent_router_state_features(
                                energy=ent.energy[active],
                                integrity=ent.integrity[active],
                                fertility=ent.fertility[active],
                                local_resource=policy_local_resources[:, 0],
                                max_energy=cfg.entities.max_energy,
                                resource_capacity=cfg.environment.resource_capacity[0],
                            )
                        knowledge_policy_plan = build_latent_knowledge_policy_plan(
                            self.knowledge.observation,
                            self.knowledge.latent_store,
                            tick=self.tick,
                            entity_ids=ent.entity_id[active],
                            holder_subject_ids=ent.primary_subject_id[active],
                            context_keys=knowledge_context_keys,
                            genotype=active_genotype,
                            router_gene_start=ParametricPolicy.latent_router_gene_start(cfg),
                            selection_gene_start=(
                                ParametricPolicy.sparse_selection_gene_start(cfg)
                                if cfg.knowledge.sparse_selection_enabled else None
                            ),
                            working_memory_q=(
                                np.zeros_like(ent.working_memory_q[active])
                                if self.knowledge.working_memory_ablation_enabled
                                else ent.working_memory_q[active]
                            ),
                            selection_enabled=(
                                cfg.knowledge.sparse_selection_enabled
                                and not self.knowledge.sparse_selection_ablation_enabled
                            ),
                            use_strength=ParametricPolicy.knowledge_use_strength_from_genotype(
                                active_genotype
                            ),
                            state_features=router_state,
                            config=cfg.knowledge,
                            action_count=len(Action),
                        )
                    else:
                        knowledge_policy_plan = build_knowledge_policy_plan(
                            self.knowledge.observation,
                            tick=self.tick,
                            entity_ids=ent.entity_id[active],
                            holder_subject_ids=ent.primary_subject_id[active],
                            context_keys=knowledge_context_keys,
                            outcome_preferences=ParametricPolicy.outcome_preferences_from_genotype(
                                active_genotype
                            ),
                            use_strength=ParametricPolicy.knowledge_use_strength_from_genotype(
                                active_genotype
                            ),
                            config=cfg.knowledge,
                            action_count=len(Action),
                        )
                cost_free_knowledge_policy_plan = knowledge_policy_plan
                if cfg.knowledge.routing_cost_enabled and (
                    knowledge_policy_plan.size
                    or knowledge_policy_plan.work_active_rows.size
                ):
                    policy_energy = ent.energy.copy()
                    routing_cost_result = apply_routing_cost_budget(
                        knowledge_policy_plan,
                        active_energy=policy_energy[active],
                        config=cfg.knowledge,
                        action_count=len(Action),
                    )
                    knowledge_policy_plan = routing_cost_result.plan
                    charged = routing_cost_result.committed_energy > 0.0
                    if np.any(charged):
                        world_rows = active[routing_cost_result.active_rows[charged]]
                        ent.energy[world_rows] = np.maximum(
                            ent.energy[world_rows].astype(np.float64)
                            - routing_cost_result.committed_energy[charged],
                            0.0,
                        ).astype(np.float32)
            stats.observation_seconds = time.perf_counter() - phase_started

            phase_started = time.perf_counter()
            if self.social_control_enabled:
                group_direction = (self.social.group_dir_x, self.social.group_dir_y)
            else:
                group_direction = (np.zeros_like(self.social.group_dir_x), np.zeros_like(self.social.group_dir_y))
            cost_free_decision = None
            if (
                routing_cost_result is not None
                and routing_cost_result.rejected_action_count > 0
            ):
                cost_free_decision = self.policy.decide(
                    active=active,
                    stable_ids=ent.entity_id,
                    energy=policy_energy,
                    integrity=ent.integrity,
                    fertility=ent.fertility,
                    genotype=ent.genotype,
                    memory=ent.memory,
                    local_resources=policy_local_resources,
                    resource_gradient=resource_gradient,
                    danger_gradient=danger_gradient,
                    group_direction=group_direction,
                    partners=partners,
                    info=info,
                    run_seed=cfg.run.seed,
                    tick=self.tick,
                    knowledge_plan=cost_free_knowledge_policy_plan,
                )
            memory_free_decision = None
            if cfg.knowledge.working_memory_enabled:
                memory_free_decision = self.policy.decide(
                    active=active,
                    stable_ids=ent.entity_id,
                    energy=policy_energy,
                    integrity=ent.integrity,
                    fertility=ent.fertility,
                    genotype=ent.genotype,
                    memory=np.zeros_like(ent.memory),
                    local_resources=policy_local_resources,
                    resource_gradient=resource_gradient,
                    danger_gradient=danger_gradient,
                    group_direction=group_direction,
                    partners=partners,
                    info=info,
                    run_seed=cfg.run.seed,
                    tick=self.tick,
                    knowledge_plan=knowledge_policy_plan,
                )
            decision = self.policy.decide(
                active=active,
                stable_ids=ent.entity_id,
                energy=policy_energy,
                integrity=ent.integrity,
                fertility=ent.fertility,
                genotype=ent.genotype,
                memory=ent.memory,
                local_resources=policy_local_resources,
                resource_gradient=resource_gradient,
                danger_gradient=danger_gradient,
                group_direction=group_direction,
                partners=partners,
                info=info,
                run_seed=cfg.run.seed,
                tick=self.tick,
                knowledge_plan=knowledge_policy_plan,
            )
            if cost_free_decision is not None:
                decision.cost_free_knowledge_action = cost_free_decision.action
            if memory_free_decision is not None:
                decision.memory_free_knowledge_action = memory_free_decision.action
            stats.policy_seconds = time.perf_counter() - phase_started
        else:
            self.gpu_runtime.begin_step_transfer_measurement()
            phase_started = time.perf_counter()
            self.gpu_runtime.update_fields(self.tick)
            record_resource_recycling_after_environment_update(self, stats)
            if cfg.physiology.enabled:
                self.environment.update_physiology_fields(self.tick)
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
                retain_logits=(
                    self._trajectory_file is not None or cfg.run.validation_mode
                ),
                retain_policy_diagnostics=(evaluation_due or cfg.run.validation_mode),
                need_host_resource_gradient=(
                    self.autonomy_recovery_enabled
                    or (
                        self.social_connections_enabled
                        and not self.group_refresh_ablation_enabled
                        and self.social.group_update_due(self.tick)[0]
                    )
                ),
                entity_state_version=self.entity_device_version,
                knowledge=self.knowledge if cfg.knowledge.enabled else None,
                resource_affinity_ablation_enabled=(
                    self.resource_affinity_ablation_enabled
                ),
                danger_evidence_ablation_enabled=(
                    self.danger_evidence_ablation_enabled
                ),
                knowledge_policy_ablation_enabled=(
                    self.knowledge_policy_ablation_enabled
                ),
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
            local_physiology = self.environment.physiology_for_cells(cells)
            effective_resource_affinity_q = (
                np.full(
                    (ent.alive.size, RESOURCE_CHANNELS),
                    AFFINITY_SCALE,
                    dtype=np.int32,
                )
                if self.resource_affinity_ablation_enabled
                else resource_affinity_quantized(ent.genotype, cfg)
            )
            active_storage_room_fraction = storage_room_fraction(
                ent,
                active,
                cfg,
                genotype=ent.genotype[active],
                gene_start=self.policy.physiology_gene_start(cfg),
            )
            policy_local_resources = policy_resource_view(
                local_resources,
                ent.genotype[active],
                cfg,
                resource_affinity_q=effective_resource_affinity_q[active],
                storage_room_fraction=active_storage_room_fraction,
            )
            resource_gradient = prepared.resource_gradient
            info = prepared.information
            decision = prepared.decision
            knowledge_context_keys = prepared.knowledge_context_keys
            knowledge_policy_plan = prepared.knowledge_policy_plan
            routing_cost_result = prepared.routing_cost_result
            if cfg.knowledge.working_memory_enabled:
                working_memory_state_features = np.asarray(
                    latent_router_state_features(
                        energy=ent.energy[active],
                        integrity=ent.integrity[active],
                        fertility=ent.fertility[active],
                        local_resource=policy_local_resources[:, 0],
                        max_energy=cfg.entities.max_energy,
                        resource_capacity=cfg.environment.resource_capacity[0],
                    ),
                    dtype=np.float32,
                )
            stats.spatial_seconds = prepared.spatial_seconds
            stats.observation_seconds = prepared.observation_seconds
            stats.policy_seconds = prepared.policy_seconds

        if effective_resource_affinity_q is None:
            raise RuntimeError("effective resource affinity was not prepared")
        effective_harvest_preference_q = effective_resource_affinity_q.copy()
        functional_context_metrics = evaluate_functional_outputs(
            self,
            active=active,
            effective_resource_affinity_q=effective_resource_affinity_q,
            local_resources=local_resources,
            local_physiology=local_physiology,
            evaluation_due=evaluation_due,
            effective_harvest_preference_q=effective_harvest_preference_q,
            effective_embodied_output_q=effective_embodied_output_q,
            effective_physiology_output_q=effective_physiology_output_q,
            functional_computation_load=functional_computation_load,
            movement_speed_multiplier=movement_speed_multiplier,
            signal_strength_multiplier=signal_strength_multiplier,
        )
        apply_gpu_oxygen_steering(self, active=active, decision=decision)

        if self.local_stress_diagnostics is not None:
            local_hazard = (
                self.gpu_runtime.hazard_for_cells(cells)
                if self.gpu_runtime is not None
                else self.environment.hazard.reshape(-1)[cells]
            )
            self.local_stress_diagnostics.observe_population(
                x=ent.x[active],
                y=ent.y[active],
                cell_ids=cells,
                local_resources=local_resources,
                local_hazard=local_hazard,
            )

        if cfg.knowledge.enabled and cfg.knowledge.policy_influence_enabled:
            if routing_cost_result is not None:
                cost_induced_action_changes = (
                    int(np.count_nonzero(
                        decision.action != decision.cost_free_knowledge_action
                    ))
                    if decision.cost_free_knowledge_action is not None
                    else 0
                )
                routing_stats = self.knowledge.record_routing_cost(
                    routing_cost_result,
                    cost_induced_action_changes=cost_induced_action_changes,
                )
                for field_name in KnowledgeStepStats.__dataclass_fields__:
                    setattr(
                        knowledge_stats,
                        field_name,
                        getattr(knowledge_stats, field_name)
                        + getattr(routing_stats, field_name),
                    )
            changed_active_rows = (
                np.flatnonzero(decision.action != decision.genetic_action).astype(
                    np.int32, copy=False
                )
                if decision.genetic_action is not None
                else np.empty(0, dtype=np.int32)
            )
            changed_actions = int(changed_active_rows.size)
            comparison_changed_actions = (
                int(np.count_nonzero(decision.action != decision.linear_knowledge_action))
                if decision.linear_knowledge_action is not None
                else 0
            )
            policy_stats = self.knowledge.record_policy_plan(
                knowledge_policy_plan,
                changed_actions=changed_actions,
                changed_active_rows=changed_active_rows,
                comparison_changed_actions=comparison_changed_actions,
            )
            for field_name in KnowledgeStepStats.__dataclass_fields__:
                setattr(
                    knowledge_stats,
                    field_name,
                    getattr(knowledge_stats, field_name)
                    + getattr(policy_stats, field_name),
                )
            stats.knowledge_policy_max_abs_residual = (
                float(np.max(np.abs(knowledge_policy_plan.residuals)))
                if knowledge_policy_plan.size
                else 0.0
            )

        # Keep one immutable host-side diagnostic snapshot.  It is overwritten
        # each tick and is used only by validation/parity tooling to locate the
        # first backend divergence before it reaches births or deaths.
        self.last_active = np.asarray(active, dtype=np.int32).copy()
        self.last_cells = np.asarray(cells, dtype=np.int32).copy()
        self.last_local_resources = np.asarray(
            local_resources, dtype=np.float32
        ).copy()
        self.last_information = info
        self.last_policy_decision = decision
        self.last_knowledge_policy_plan = copy.deepcopy(knowledge_policy_plan)
        if evaluation_due:
            evaluation_started = time.perf_counter()
            if decision.features is None or decision.action_mask is None:
                # Third-party policy adapters written before diagnostic
                # payloads remain valid, but their missing observations are
                # explicit instead of being reconstructed from changed state.
                actual_context_metrics = {
                    "actual_context_available": False,
                    "actual_context_observation_tick": int(self.tick),
                    **functional_context_metrics,
                }
            else:
                actual_context_metrics = {
                    "actual_context_available": True,
                    "actual_context_observation_tick": int(self.tick),
                    **functional_context_metrics,
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
                    policy_local_resources[:, 0],
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
        reproduction_eligible_mask = (
            (ent.energy[active] >= cfg.entities.reproduction_threshold)
            & (ent.fertility[active] >= 0.5)
        )
        reproduction_eligible_indices = active[reproduction_eligible_mask]
        stats.reproduction_eligible = int(reproduction_eligible_indices.size)
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
        active_raw_harvest_room = raw_harvest_room(
            ent,
            active,
            cfg,
            genotype=ent.genotype[active],
            gene_start=self.policy.physiology_gene_start(cfg),
            resource_affinity_q=effective_resource_affinity_q[active],
        )
        raw_harvest_storage_room = None
        if active_raw_harvest_room is not None:
            raw_harvest_storage_room = np.zeros(
                (ent.alive.size, RESOURCE_CHANNELS), dtype=np.float32
            )
            raw_harvest_storage_room[active] = active_raw_harvest_room
        snapshot = ActionResolutionSnapshot(
            active=active,
            cells=cells,
            entity_id=ent.entity_id,
            alive=ent.alive,
            energy=ent.energy,
            fertility=ent.fertility,
            primary_subject_id=ent.primary_subject_id,
            free_slot_count=len(ent.free_slots),
            resource_affinity_q=effective_resource_affinity_q,
            harvest_preference_q=effective_harvest_preference_q,
            raw_harvest_storage_room=raw_harvest_storage_room,
        )
        harvest_allocator = (
            self.gpu_runtime.resolve_harvest
            if self.gpu_runtime is not None
            else self.environment.resolve_harvest
        )
        resolution_plan = self.conflict_resolver.resolve(snapshot, intents, harvest_allocator)
        resolutions = resolution_plan.resolutions
        harvest_rows = resolution_plan.harvest_rows
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

        knowledge_pre_energy: np.ndarray | None = None
        knowledge_pre_integrity: np.ndarray | None = None
        knowledge_pre_information: np.ndarray | None = None
        knowledge_pre_reproduction: np.ndarray | None = None
        if self.cfg.knowledge.enabled and self.cfg.knowledge.learning_enabled:
            if knowledge_context_keys is None:
                raise RuntimeError("knowledge learning requires the pre-action context snapshot")
            knowledge_pre_energy = ent.energy[active].astype(np.float32, copy=True)
            knowledge_pre_integrity = ent.integrity[active].astype(
                np.float32, copy=True
            )
            knowledge_pre_information = ent.information_store[active].astype(
                np.float32, copy=True
            )
            knowledge_pre_reproduction = np.minimum(
                np.clip(
                    knowledge_pre_energy
                    / max(cfg.entities.reproduction_threshold, 1e-12),
                    0.0,
                    1.0,
                ),
                np.clip(ent.fertility[active] / 0.5, 0.0, 1.0),
            ).astype(np.float32, copy=False)

        # ----- World commit phase: only resolved intents may mutate state. -----
        movable_actions = np.isin(intents.action, [Action.MOVE_RESOURCE, Action.MOVE_SOCIAL, Action.FLEE])
        movable_rows = np.flatnonzero(movable_actions & resolutions.success)
        movers = intents.carrier_index[movable_rows]
        base_speed = (
            0.35 + 0.10 * np.clip(ent.genotype[movers, 5], -1.0, 1.0)
        ).astype(np.float32)
        speed = base_speed * movement_speed_multiplier[movers]
        ent.vx[movers] = intents.direction_x[movable_rows] * speed
        ent.vy[movers] = intents.direction_y[movable_rows] * speed
        ent.x[movers] += ent.vx[movers]
        ent.y[movers] += ent.vy[movers]
        if cfg.world.periodic:
            ent.x[movers] = _wrap_periodic_float32(ent.x[movers], cfg.world.width)
            ent.y[movers] = _wrap_periodic_float32(ent.y[movers], cfg.world.height)
        else:
            ent.x[movers] = np.clip(ent.x[movers], 0.0, cfg.world.width)
            ent.y[movers] = np.clip(ent.y[movers], 0.0, cfg.world.height)
        non_movers = active[~np.isin(active, movers)]
        ent.vx[non_movers] = 0.0
        ent.vy[non_movers] = 0.0

        harvest_body_delta = commit_harvest_resolution(
            self,
            intents,
            resolution_plan,
            effective_resource_affinity_q,
            stats,
        )

        share = self._finalize_share_capacity(share, resolutions)
        stats.shared_energy = self._commit_shares(share)
        self.total_shared_energy += stats.shared_energy
        self._record_benefit_boundary(share, stats)

        signal_plan = SignalEmissionPlan(())
        if signal_rows.size:
            signal_actors = intents.carrier_index[signal_rows]
            signal_observation_rows = np.searchsorted(active, signal_actors)
            (
                signal_plan,
                stats.direct_messages,
                signal_energy,
            ) = self._emit_signals(
                signal_actors,
                cells[signal_observation_rows],
                local_resources[signal_observation_rows],
                intents.target_index[signal_rows],
                signal_strength_multiplier[signal_actors],
            )
            signal_energy_delta = float(
                signal_energy
                - signal_actors.size * float(cfg.entities.signal_cost)
            )
            stats.functional_module_signal_energy = 0.0 if abs(signal_energy_delta) < 1.0e-12 else signal_energy_delta
            self.total_functional_module_signal_energy_delta += (
                stats.functional_module_signal_energy
            )
            stats.signals = int(signal_actors.size)
        self._flush_signal_emissions(signal_plan)
        if (
            self.cfg.knowledge.enabled
            and not self.knowledge_transfer_ablation_enabled
        ):
            transfer_plan = self.knowledge.plan_transfers(
                sender_entity_indices=(
                    intents.carrier_index[signal_rows]
                    if signal_rows.size
                    else np.empty(0, dtype=np.int32)
                ),
                receiver_entity_indices=(
                    intents.target_index[signal_rows]
                    if signal_rows.size
                    else np.empty(0, dtype=np.int32)
                ),
                entity_ids=ent.entity_id,
                primary_subject_ids=ent.primary_subject_id,
                alive=ent.alive,
                tick=self.tick,
                attention_capacities=ent.knowledge_attention_capacity,
            )
            transfer_stats = self.knowledge.commit_transfers(
                transfer_plan,
                energy=ent.energy,
                alive=ent.alive,
                group_ids=self.social.group_id,
                lineage_subject_ids=ent.lineage_subject_id,
                x=ent.x,
                y=ent.y,
                world_width=cfg.world.width,
                world_height=cfg.world.height,
                knowledge_capacities=ent.knowledge_capacity_bytes,
            )
            if self.local_stress_diagnostics is not None:
                self.local_stress_diagnostics.observe_transfers(
                    plan=transfer_plan,
                    audit=self.knowledge.last_transfer_commit_audit,
                    x=ent.x,
                    y=ent.y,
                )
            for field_name in KnowledgeStepStats.__dataclass_fields__:
                setattr(
                    knowledge_stats,
                    field_name,
                    getattr(knowledge_stats, field_name)
                    + getattr(transfer_stats, field_name),
                )

        if embodied_outputs_enabled(cfg) and active.size:
            repair = apply_material_repair(
                ent, active, effective_embodied_output_q[active], cfg
            )
            stats.functional_module_repair_material = repair.material
            stats.functional_module_repair_energy = repair.energy
            stats.functional_module_repair_integrity = repair.integrity
            self.total_functional_module_repair_material += repair.material
            self.total_functional_module_repair_energy += repair.energy
            self.total_functional_module_repair_integrity += repair.integrity

        accepted_parents = np.empty(0, dtype=np.int32)
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
                if self.capacity_ablation_enabled and cfg.differentiation.enabled:
                    genetic_cost = np.asarray(
                        capacity_development_energy(
                            ent.capacity_phenotype(newborns), cfg.differentiation
                        ),
                        dtype=np.float64,
                    )
                    ent.neutralize_capacity_phenotype(newborns)
                    neutral_cost = np.asarray(
                        capacity_development_energy(
                            ent.capacity_phenotype(newborns), cfg.differentiation
                        ),
                        dtype=np.float64,
                    )
                    ent.energy[newborns] = np.clip(
                        ent.energy[newborns].astype(np.float64)
                        + genetic_cost
                        - neutral_cost,
                        0.0,
                        cfg.entities.max_energy,
                    ).astype(np.float32)
                if cfg.functional_modules.enabled:
                    module_development_full = functional_module_energy(
                        ent.genotype[newborns],
                        cfg,
                        gene_start=ParametricPolicy.functional_module_gene_start(cfg),
                        development=True,
                    )
                    module_development_effective = functional_module_energy(
                        ent.genotype[newborns],
                        cfg,
                        gene_start=ParametricPolicy.functional_module_gene_start(cfg),
                        development=True,
                        ablated=self.functional_modules_ablation_enabled,
                        ablated_modules=self.functional_module_ablation_mask,
                        row_ablated_modules=self.functional_module_lineage_ablation_mask(
                            newborns, cost=True
                        ),
                    )
                    refund = module_development_full - module_development_effective
                    if np.any(refund):
                        ent.energy[newborns] = np.minimum(
                            ent.energy[newborns].astype(np.float64) + refund,
                            cfg.entities.max_energy,
                        ).astype(np.float32)
                    stats.functional_module_development_energy = float(
                        module_development_effective.sum(dtype=np.float64)
                    )
                record_physiology_capacity_development_cost(
                    self, newborns, stats
                )
                # Recovery is a treatment of the selected living cohort, not
                # a hereditary trait in the current experiment.
                self.autonomy_restored[newborns] = False
                self.autonomy_observation_cohort[newborns] = False
                self.social.reset_entities(newborns)
                self.social.set_effective_capacities(
                    newborns, ent.relation_capacity[newborns]
                )
                body_subjects, lineage_subjects = self.subjects.register_bodies(
                    newborns, ent.lineage_id, self.tick
                )
                ent.primary_subject_id[newborns] = body_subjects
                ent.lineage_subject_id[newborns] = lineage_subjects
                ent.energy[accepted_parents] -= cfg.entities.reproduction_cost
                ent.fertility[accepted_parents] -= 0.5
                stats.births = int(newborns.size)
                if cfg.differentiation.enabled:
                    stats.capacity_development_energy = float(
                        np.asarray(
                            capacity_development_energy(
                                ent.capacity_phenotype(newborns),
                                cfg.differentiation,
                            ),
                            dtype=np.float64,
                        ).sum(dtype=np.float64)
                    )
                self.total_births += stats.births
                if self.local_stress_diagnostics is not None:
                    self.local_stress_diagnostics.observe_births(
                        newborns, ent.x, ent.y
                    )

        self.evolution_progress.observe_reproduction_traits(
            ent.genotype,
            eligible_indices=reproduction_eligible_indices,
            accepted_parent_indices=accepted_parents,
            newborn_indices=newborns,
        )

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

        if (
            self.cfg.knowledge.enabled
            and self.cfg.knowledge.learning_enabled
            and knowledge_context_keys is not None
            and knowledge_pre_energy is not None
            and knowledge_pre_integrity is not None
            and knowledge_pre_information is not None
            and knowledge_pre_reproduction is not None
        ):
            carriers = intents.carrier_index
            material_delta = np.zeros(intents.action.size, dtype=np.float32)
            if harvest_rows.size:
                if (
                    cfg.environment.schema != "legacy-four-channel-v1"
                    and harvest_body_delta is not None
                ):
                    material_delta[harvest_rows] = harvest_body_delta[:, 2]
                else:
                    material_delta[harvest_rows] = np.asarray(
                        gathered, dtype=np.float32
                    ).sum(axis=1)
            post_reproduction = np.minimum(
                np.clip(
                    ent.energy[carriers]
                    / max(cfg.entities.reproduction_threshold, 1e-12),
                    0.0,
                    1.0,
                ),
                np.clip(ent.fertility[carriers] / 0.5, 0.0, 1.0),
            ).astype(np.float32, copy=False)
            outcome_vectors = np.column_stack(
                (
                    ent.energy[carriers] - knowledge_pre_energy,
                    ent.integrity[carriers] - knowledge_pre_integrity,
                    material_delta,
                    ent.information_store[carriers] - knowledge_pre_information,
                    post_reproduction - knowledge_pre_reproduction,
                )
            ).astype(np.float32, copy=False)
            working_memory_actual_outcomes = outcome_vectors.copy()
            statuses = np.where(
                resolutions.success,
                OUTCOME_STATUS_SUCCESS,
                OUTCOME_STATUS_FAILED,
            ).astype(np.uint8)
            if harvest_rows.size:
                if cfg.environment.schema == "legacy-four-channel-v1":
                    partial_harvest = (
                        resolutions.success[harvest_rows]
                        & (gathered[:, 0] > 1e-8)
                        & (gathered[:, 0] < cfg.entities.harvest_rate - 1e-8)
                    )
                else:
                    if selective_harvest_enabled(cfg):
                        requested_total = np.float32(
                            cfg.entities.harvest_rate
                            * sum(cfg.environment.harvest_channel_multipliers)
                        )
                        gathered_total = np.asarray(gathered, dtype=np.float32).sum(axis=1)
                        partial_harvest = (
                            resolutions.success[harvest_rows]
                            & (gathered_total > 1e-8)
                            & (gathered_total < requested_total - 1e-8)
                        )
                    else:
                        requested_rates = (
                            cfg.entities.harvest_rate
                            * np.asarray(
                                cfg.environment.harvest_channel_multipliers,
                                dtype=np.float32,
                            )
                        )
                        partial_harvest = (
                            resolutions.success[harvest_rows]
                            & np.any(gathered > 1e-8, axis=1)
                            & np.any(gathered < requested_rates[None, :] - 1e-8, axis=1)
                        )
                statuses[harvest_rows[partial_harvest]] = OUTCOME_STATUS_PARTIAL
            if share.rows.size:
                proposed_share = np.minimum(
                    cfg.entities.share_amount,
                    np.maximum(knowledge_pre_energy[share.rows] - 0.5, 0.0),
                )
                partial_share = (
                    share.success
                    & (share.amounts > 1e-8)
                    & (share.amounts < proposed_share - 1e-8)
                )
                statuses[share.rows[partial_share]] = OUTCOME_STATUS_PARTIAL
            outcome_plan = KnowledgeOutcomePlan(
                tick=int(self.tick),
                carrier_indices=carriers.astype(np.int32, copy=True),
                entity_ids=ent.entity_id[carriers].astype(np.uint64, copy=True),
                holder_subject_ids=ent.primary_subject_id[carriers].astype(
                    np.uint64, copy=True
                ),
                context_keys=knowledge_context_keys.astype(np.uint64, copy=True),
                action_ids=intents.action.astype(np.int16, copy=True),
                statuses=statuses,
                failure_reasons=resolutions.failure_reason.astype(
                    np.uint8, copy=True
                ),
                outcome_vectors=outcome_vectors.copy(),
            )
            outcome_stats = self.knowledge.commit_outcomes(
                outcome_plan,
                energy=ent.energy,
                alive=ent.alive,
                knowledge_capacities=ent.knowledge_capacity_bytes,
            )
            for field_name in KnowledgeStepStats.__dataclass_fields__:
                setattr(
                    knowledge_stats,
                    field_name,
                    getattr(knowledge_stats, field_name)
                    + getattr(outcome_stats, field_name),
                )

        if (
            cfg.knowledge.working_memory_enabled
            and not self.knowledge.working_memory_ablation_enabled
        ):
            if working_memory_state_features is None or working_memory_actual_outcomes is None:
                raise RuntimeError("working memory requires latent state and committed outcomes")
            selected_actions = np.asarray(decision.action, dtype=np.int16)
            expected_outcomes = expected_outcomes_for_actions(
                knowledge_policy_plan,
                active_count=active.size,
                actions=selected_actions,
            )
            working_memory_update_result = build_working_memory_update(
                tick=self.tick,
                active_rows=active,
                entity_ids=ent.entity_id[active],
                previous_q=ent.working_memory_q[active],
                previous_observation_q=ent.working_memory_previous_observation_q[active],
                current_state_features=working_memory_state_features,
                actual_outcomes=working_memory_actual_outcomes,
                expected_outcomes=expected_outcomes,
                genotype=ent.genotype[active],
                gene_start=ParametricPolicy.working_memory_gene_start(cfg),
                available_energy=ent.energy[active],
                config=cfg.knowledge,
                effective_widths=ent.working_memory_capacity[active],
            )
            accepted_memory = working_memory_update_result.accepted
            ent.working_memory_q[active] = working_memory_update_result.committed_q
            ent.working_memory_previous_observation_q[active] = np.where(
                accepted_memory[:, None],
                working_memory_update_result.observation_q,
                ent.working_memory_previous_observation_q[active],
            ).astype(np.int16)
            ent.memory[active] = memory_float_view(
                ent.working_memory_q[active],
                cfg.knowledge,
                effective_widths=ent.working_memory_capacity[active],
            )
            ent.energy[active] = np.maximum(
                ent.energy[active].astype(np.float64)
                - working_memory_update_result.committed_energy,
                0.0,
            ).astype(np.float32)
            memory_stats = self.knowledge.record_working_memory(
                working_memory_update_result,
                holder_subject_ids=ent.primary_subject_id[active],
                action_changes=(
                    int(np.count_nonzero(
                        np.asarray(decision.action)
                        != np.asarray(decision.memory_free_knowledge_action)
                    ))
                    if decision.memory_free_knowledge_action is not None else 0
                ),
            )
            for field_name in KnowledgeStepStats.__dataclass_fields__:
                setattr(
                    knowledge_stats,
                    field_name,
                    getattr(knowledge_stats, field_name)
                    + getattr(memory_stats, field_name),
                )

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
        if self.cfg.knowledge.enabled:
            maintenance_stats = self.knowledge.charge_maintenance(
                energy=ent.energy,
                alive=ent.alive,
                primary_subject_id=ent.primary_subject_id,
                tick=self.tick,
                knowledge_capacities=ent.knowledge_capacity_bytes,
            )
            for field_name in KnowledgeStepStats.__dataclass_fields__:
                setattr(
                    knowledge_stats,
                    field_name,
                    getattr(knowledge_stats, field_name)
                    + getattr(maintenance_stats, field_name),
                )
        movement_cost, stats.functional_module_movement_energy = (
            movement_cost_with_power(
                moved_now[current_active],
                movement_speed_multiplier[current_active],
                cfg.entities.movement_cost,
            )
        )
        self.total_functional_module_movement_energy_delta += (
            stats.functional_module_movement_energy
        )
        cost = float(cfg.entities.maintenance_cost) + movement_cost
        if cfg.differentiation.enabled:
            capacity_cost = np.asarray(
                capacity_maintenance_energy(
                    ent.capacity_phenotype(current_active),
                    cfg.differentiation,
                ),
                dtype=np.float64,
            )
            stats.capacity_maintenance_energy = float(
                capacity_cost.sum(dtype=np.float64)
            )
            cost = cost.astype(np.float64) + capacity_cost
        if cfg.functional_modules.enabled:
            module_cost = functional_module_energy(
                ent.genotype[current_active],
                cfg,
                gene_start=ParametricPolicy.functional_module_gene_start(cfg),
                development=False,
                ablated=self.functional_modules_ablation_enabled,
                ablated_modules=self.functional_module_ablation_mask,
                row_ablated_modules=self.functional_module_lineage_ablation_mask(
                    current_active, cost=True
                ),
            )
            stats.functional_module_maintenance_energy = float(
                module_cost.sum(dtype=np.float64)
            )
            cost = cost.astype(np.float64) + module_cost
        cost = add_physiology_capacity_maintenance_cost(
            self, current_active, cost, stats
        )
        cost, current_physiology, moved_current = add_physiology_terrain_cost(
            self,
            current_active=current_active,
            current_cells=current_cells,
            moved_now=moved_now,
            cost=cost,
        )
        ent.energy[current_active] -= cost.astype(np.float32)
        ent.integrity[current_active] -= (hazard * 0.0015).astype(np.float32)
        apply_physiology_settlement(
            self,
            current_active=current_active,
            current_physiology=current_physiology,
            moved_current=moved_current,
            signal_rows=signal_rows,
            intents=intents,
            effective_physiology_output_q=effective_physiology_output_q,
            functional_computation_load=functional_computation_load,
            stats=stats,
        )
        starving = ent.energy[current_active] < 0.0
        ent.integrity[current_active[starving]] += ent.energy[current_active[starving]] * 0.05
        ent.energy[current_active] = np.maximum(ent.energy[current_active], 0.0)
        ent.age[current_active] += 1
        ent.information_store[current_active] *= 0.999
        ent.fertility[current_active] = np.maximum(ent.fertility[current_active] - 0.0005, 0.0)

        if not cfg.knowledge.working_memory_enabled:
            self.policy.update_memory(
                active, ent.memory, policy_local_resources, info
            )
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
            record_resource_store_death_loss(self, dead, stats)
            if self.local_stress_diagnostics is not None:
                self.local_stress_diagnostics.observe_deaths(dead, ent.x, ent.y)
            death_cells = np.asarray(
                self.spatial.cell_ids(ent.x[dead], ent.y[dead]),
                dtype=np.int32,
            )
            if self.gpu_runtime is None:
                self.environment.deposit_mortality_trace(death_cells)
            else:
                self.gpu_runtime.deposit_mortality_trace(death_cells)
            self.subjects.mark_dead(dead, self.tick)
            ent.commit_deaths(death_events)
            self.autonomy_restored[dead] = False
            self.autonomy_observation_cohort[dead] = False
            self.social.group_id[dead] = 0
            self.social.group_age[dead] = 0
            self.social.mark_group_labels_dirty("entity-death")
            stats.deaths = int(dead.size)
            self.total_deaths += stats.deaths
        # With no death this tick no new stale relation target can exist, so
        # skip the otherwise full fixed-slot relationship-table scan.
        if dead.size:
            self.social.clear_dead_targets(ent.alive)
        if self.cfg.knowledge.enabled:
            knowledge_stats.removed_dead_holder += self.knowledge.remove_dead_holders(
                ent.alive, ent.primary_subject_id
            )

        # Candidate social subjects are updated at a slower timescale.
        phase_started = time.perf_counter()
        if self.group_refresh_ablation_enabled:
            group_updated = False
            group_update_reason = "intervention-frozen"
            self.social.last_group_update_reason = group_update_reason
        else:
            group_updated, group_update_reason = self.social.group_update_due(
                self.tick
            )
        if group_updated:
            self.social.last_group_update_reason = group_update_reason
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
            if self.subject_structure_diagnostics is not None:
                self.subject_structure_diagnostics.observe_group_refresh(
                    tick=self.tick,
                    group_tokens=self.last_group_plan.group_tokens,
                    member_starts=self.last_group_plan.member_starts,
                    member_counts=self.last_group_plan.member_counts,
                    member_indices=self.last_group_plan.member_indices,
                    stable_ids=ent.entity_id,
                )
            stats.group_updated = 1
        else:
            self.social.note_group_update_skipped()
        stats.graph_seconds = time.perf_counter() - phase_started
        if (
            self.cfg.knowledge.enabled
            and self.cfg.knowledge.candidate_tracking_enabled
            and (
                (self.tick + 1) % self.cfg.knowledge.candidate_update_period == 0
                or self.tick == 0
            )
        ):
            candidate_started = time.perf_counter()
            self.knowledge.update_candidates(
                tick=self.tick + 1,
                alive=ent.alive,
                primary_subject_ids=ent.primary_subject_id,
                lineage_subject_ids=ent.lineage_subject_id,
                group_ids=self.social.group_id,
                x=ent.x,
                y=ent.y,
                world_width=cfg.world.width,
                world_height=cfg.world.height,
                energy=ent.energy,
                integrity=ent.integrity,
                harvested_material=ent.harvested_energy_total,
                information_store=ent.information_store,
                fertility=ent.fertility,
                reproduction_threshold=cfg.entities.reproduction_threshold,
            )
            stats.graph_seconds += time.perf_counter() - candidate_started
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
        if self.cfg.knowledge.enabled:
            self.knowledge.publish(self.tick + 1)
            self.knowledge.accumulate(knowledge_stats)
        self.tick += 1
        if self.cfg.run.validation_mode:
            validation_started = time.perf_counter()
            self._validate_invariants()
            stats.validation_seconds = time.perf_counter() - validation_started
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

    def run(
        self,
        until_tick: int | None = None,
        *,
        tick_observer: Callable[["Simulation", StepStats | None], None] | None = None,
    ) -> dict[str, float | int]:
        """Advance to an absolute tick and finalize this run's outputs.

        ``until_tick`` is absolute rather than a step count so a simulation
        can be advanced to a counterfactual branch point with ``step()`` and
        then finish at the configured horizon without extending the run.

        ``tick_observer`` is an experiment-only, read-only observation hook. It
        is called once at the starting checkpoint with ``stats=None`` and after
        every authoritative step. The default remains ``None`` and therefore
        cannot change historical trajectories or runtime semantics.
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
            if tick_observer is not None:
                tick_observer(self, None)
            for _ in range(target_tick - self.tick):
                step_started = time.perf_counter()
                stats = self.step()
                self._observe_event_cohort_diagnostics()
                if tick_observer is not None:
                    tick_observer(self, stats)
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
                periodic_checkpoint = self.tick % self.cfg.run.checkpoint_period == 0
                exact_checkpoint = self.tick in self.cfg.run.checkpoint_ticks
                if periodic_checkpoint or exact_checkpoint:
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
            self.knowledge.close()
            if self.subject_structure_diagnostics is not None:
                self.subject_structure_diagnostics.close()
            if self.environment_atlas_diagnostics is not None:
                self.environment_atlas_diagnostics.close()
            if self._trajectory_file is not None:
                self._trajectory_file.close()
        interventions_metadata: dict[str, object] = {
            "social_control_enabled": self.social_control_enabled,
            "social_connections_enabled": self.social_connections_enabled,
            "direct_messages_enabled": self.direct_messages_enabled,
            "freeze_genotype": self.freeze_genotype,
            "capacity_ablation_enabled": self.capacity_ablation_enabled,
            "environment_spatial_reversed": self.environment.spatial_reversed,
            "environment_resource_spatial_reversed": bool(
                getattr(self.environment, "resource_spatial_reversed", False)
            ),
            "mortality_trace_schema": self.cfg.environment.mortality_trace_schema,
            "environment_process": dict(
                self.environment.environment_process_metadata
            ),
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
            "gpu_semantics_mode": self.gpu_semantics_mode,
            "gpu_device_validated": self.gpu_device_validated,
            "gpu_acceleration_enabled": self.gpu_acceleration_enabled,
            "gpu_fallback_used": self.gpu_fallback_used,
            "gpu_fallback_reason": self.gpu_fallback_reason,
            "experiment_mode": self.experiment_mode.value,
            "scientific_validity": self.scientific_validity(),
            "ticks_completed": self.tick,
            "checkpoint_lineage": copy.deepcopy(self.checkpoint_lineage),
            "event_log_scope": ("post-checkpoint" if self.checkpoint_lineage else "full-run"),
            "wall_seconds": time.perf_counter() - started,
            "final": final_row,
            "action_counts": {action.name: int(self.action_counts[action]) for action in Action},
            "subject_graph": self.subjects.summary(),
            "subject_structure_diagnostics": (
                self.subject_structure_diagnostics.summary()
                if self.subject_structure_diagnostics is not None
                else None
            ),
            "environment_atlas_diagnostics": (
                self.environment_atlas_diagnostics.summary()
                if self.environment_atlas_diagnostics is not None
                else None
            ),
            "model_rules": {
                "reproduction_capacity_arbitration": (
                    self.cfg.entities.reproduction_capacity_arbitration
                ),
                "same_tick_deaths_release_birth_slots": False,
                "capacity_rejection_reproduction_cost": 0.0,
            },
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
                "label_schema": self.cfg.social.group_label_schema,
                "propagation_rounds": self.cfg.social.group_label_propagation_rounds,
                "trust_threshold": self.cfg.social.trust_group_threshold,
                "minimum_members": self.cfg.social.group_min_members,
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
            "knowledge": self.knowledge.summary(),
        }
        (self.output_dir / "scientific_validity.json").write_text(
            json.dumps(self.scientific_validity(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        (self.output_dir / "run_metadata.json").write_text(
            json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        return final_row

__all__ = ["Simulation"]
