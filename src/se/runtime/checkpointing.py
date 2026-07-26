from __future__ import annotations

from dataclasses import dataclass, field, replace
import copy
import hashlib
import json
import platform
from pathlib import Path
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
from se.env.niches import (
    AFFINITY_SCALE,
    RESOURCE_CHANNELS,
    active_morphology_traits,
    apply_harvest_effects,
    policy_resource_view,
    public_resource_signal,
    resource_affinity_diagnostics,
    resource_affinity_quantized,
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



from .state import EntityState, StepStats, _wrap_periodic_float32


class SimulationCheckpointMixin:
    """Trusted checkpoint, restore, and clone operations."""

    def _full_checkpoint_state(self) -> dict[str, object]:
        """Capture all semantic state required for exact continuation.

        Output writers and accelerator runtime objects are deliberately
        excluded.  A restored run creates fresh writers and reconstructs the
        requested backend before this host-authoritative state is installed.
        """
        if self.gpu_runtime is not None:
            self.gpu_runtime.sync_to_host(self.environment, self.information)
        return {
            "tick": int(self.tick),
            "entities": copy.deepcopy(self.entities),
            "entity_device_version": int(self.entity_device_version),
            "environment": copy.deepcopy(self.environment),
            "information": copy.deepcopy(self.information),
            "signal_scheduler": copy.deepcopy(self.signal_scheduler),
            "spatial": {
                "grid_x": int(self.spatial.grid_x),
                "grid_y": int(self.spatial.grid_y),
                "width": float(self.spatial.width),
                "height": float(self.spatial.height),
                "periodic": bool(self.spatial.periodic),
                "sorted_entity_indices": self.spatial.backend.to_numpy(
                    self.spatial.sorted_entity_indices
                ).copy(),
                "cell_starts": self.spatial.backend.to_numpy(
                    self.spatial.cell_starts
                ).copy(),
                "cell_sizes": self.spatial.backend.to_numpy(
                    self.spatial.cell_sizes
                ).copy(),
                "entity_cells": self.spatial.backend.to_numpy(
                    self.spatial.entity_cells
                ).copy(),
            },
            "social": copy.deepcopy(self.social),
            "subjects": self.subjects.clone(),
            "knowledge": self.knowledge.snapshot_state(),
            "last_group_summary": copy.deepcopy(self.last_group_summary),
            "last_group_plan": copy.deepcopy(self.last_group_plan),
            "total_births": int(self.total_births),
            "total_deaths": int(self.total_deaths),
            "total_shared_energy": float(self.total_shared_energy),
            "total_harvested_resources": self.total_harvested_resources.copy(),
            "action_counts": self.action_counts.copy(),
            "benefit_flow_energy_total": self.benefit_flow_energy_total.copy(),
            "lagged_benefit_boundary": self.lagged_benefit_boundary.clone(),
            "total_reproduction_eligible": int(self.total_reproduction_eligible),
            "total_reproduction_proposals": int(self.total_reproduction_proposals),
            "total_reproduction_rejected_capacity": int(
                self.total_reproduction_rejected_capacity
            ),
            "total_reproduction_rejected_resource": int(
                self.total_reproduction_rejected_resource
            ),
            "total_reproduction_rejected_other": int(
                self.total_reproduction_rejected_other
            ),
            "evolution_progress": self.evolution_progress.snapshot_state(),
            "local_stress_diagnostics": (
                self.local_stress_diagnostics.snapshot_state()
                if self.local_stress_diagnostics is not None
                else None
            ),
            "subject_structure_diagnostics": (
                self.subject_structure_diagnostics.snapshot_state()
                if self.subject_structure_diagnostics is not None
                else None
            ),
            "environment_atlas_diagnostics": (
                self.environment_atlas_diagnostics.snapshot_state()
                if self.environment_atlas_diagnostics is not None
                else None
            ),
            "last_active": self.last_active.copy(),
            "last_cells": self.last_cells.copy(),
            "last_local_resources": self.last_local_resources.copy(),
            "last_information": copy.deepcopy(self.last_information),
            "last_policy_decision": copy.deepcopy(self.last_policy_decision),
            "last_knowledge_policy_plan": copy.deepcopy(
                self.last_knowledge_policy_plan
            ),
            "last_intents": copy.deepcopy(self.last_intents),
            "last_resolutions": copy.deepcopy(self.last_resolutions),
            "last_birth_allocation": copy.deepcopy(self.last_birth_allocation),
            "last_death_events": copy.deepcopy(self.last_death_events),
            "last_entity_device_commit": copy.deepcopy(
                self.last_entity_device_commit
            ),
            "control_arbiter": copy.deepcopy(self.control_arbiter),
            "group_label_planner": copy.deepcopy(self.group_label_planner),
            "conflict_resolver_kind": type(self.conflict_resolver).__name__,
            "heuristic_guidance_actions": int(self.heuristic_guidance_actions),
            "autonomy_recovery_enabled": bool(self.autonomy_recovery_enabled),
            "autonomy_restored": self.autonomy_restored.copy(),
            "autonomy_observation_cohort": self.autonomy_observation_cohort.copy(),
            "autonomy_recovery_tick": self.autonomy_recovery_tick,
            "autonomy_cohort_tick": self.autonomy_cohort_tick,
            "autonomy_recovery_cohort_ids": self.autonomy_recovery_cohort_ids.copy(),
            "autonomy_module_actions": int(self.autonomy_module_actions),
            "autonomy_harvest_attempts": int(self.autonomy_harvest_attempts),
            "autonomy_harvest_successes": int(self.autonomy_harvest_successes),
            "social_control_enabled": bool(self.social_control_enabled),
            "social_connections_enabled": bool(self.social_connections_enabled),
            "direct_messages_enabled": bool(self.direct_messages_enabled),
            "freeze_genotype": bool(self.freeze_genotype),
            "resource_affinity_ablation_enabled": bool(
                self.resource_affinity_ablation_enabled
            ),
            "danger_evidence_ablation_enabled": bool(
                self.danger_evidence_ablation_enabled
            ),
            "knowledge_policy_ablation_enabled": bool(
                self.knowledge_policy_ablation_enabled
            ),
            "knowledge_transfer_ablation_enabled": bool(
                self.knowledge_transfer_ablation_enabled
            ),
            "group_refresh_ablation_enabled": bool(
                self.group_refresh_ablation_enabled
            ),
            "intervention_history": copy.deepcopy(self.intervention_history),
        }


    def save_full_checkpoint(self, path: str | Path | None = None) -> Path:
        """Write a trusted full-world checkpoint suitable for exact replay."""
        if not isinstance(
            self.conflict_resolver,
            (DeterministicActionConflictResolver, GpuActionConflictResolver),
        ):
            raise ValueError(
                "full checkpoints currently support only the built-in deterministic "
                "CPU/GPU conflict resolvers"
            )
        destination = (
            self.output_dir / f"checkpoint_{self.tick:08d}.sechk"
            if path is None
            else Path(path)
        )
        state = {
            "config": self.cfg,
            "simulation": self._full_checkpoint_state(),
            "checkpoint_lineage": copy.deepcopy(self.checkpoint_lineage),
        }
        result = write_checkpoint_bundle(
            destination,
            config=self.cfg,
            tick=self.tick,
            state=state,
            execution_backend=self.execution_backend,
            requested_backend=self.requested_backend,
        )
        return result


    def _restore_full_checkpoint_state(self, state: dict[str, object]) -> None:
        """Install host-authoritative semantic state into a fresh Simulation."""
        self.entities = copy.deepcopy(state["entities"])
        self.entities.cfg = self.cfg
        entity_capacity = int(np.asarray(self.entities.alive).size)
        memory_width = int(self.cfg.knowledge.working_memory_width)
        if not hasattr(self.entities, "working_memory_q"):
            self.entities.working_memory_q = np.zeros(
                (entity_capacity, memory_width), dtype=np.int16
            )
        if not hasattr(self.entities, "working_memory_previous_observation_q"):
            self.entities.working_memory_previous_observation_q = np.zeros(
                (entity_capacity, 4), dtype=np.int16
            )
        self.entity_device_version = int(state["entity_device_version"])
        self.environment = copy.deepcopy(state["environment"])
        self.environment.cfg = self.cfg
        # v0.22 checkpoints predate the extension boundary. Rebuild the
        # process from the authoritative embedded config rather than trusting
        # a pickled implementation object.
        self.environment.environment_process = build_environment_process(
            self.cfg.environment
        )
        self.environment.environment_process_metadata = environment_process_metadata(
            self.cfg.environment
        )
        if not hasattr(self.environment, "mortality_trace"):
            self.environment.mortality_trace = np.zeros(
                (self.cfg.world.grid_y, self.cfg.world.grid_x), dtype=np.float32
            )
        self.information = copy.deepcopy(state["information"])
        self.information.cfg = self.cfg
        self.signal_scheduler = copy.deepcopy(state["signal_scheduler"])
        spatial_state = state["spatial"]
        if (
            int(spatial_state["grid_x"]) != self.spatial.grid_x
            or int(spatial_state["grid_y"]) != self.spatial.grid_y
            or float(spatial_state["width"]) != self.spatial.width
            or float(spatial_state["height"]) != self.spatial.height
            or bool(spatial_state["periodic"]) != self.spatial.periodic
        ):
            raise ValueError("checkpoint spatial schema does not match configuration")
        xp = self.spatial.backend.xp
        self.spatial.sorted_entity_indices = self.spatial.backend.asarray(
            spatial_state["sorted_entity_indices"], dtype=xp.int32, copy=True
        )
        self.spatial.cell_starts = self.spatial.backend.asarray(
            spatial_state["cell_starts"], dtype=xp.int64, copy=True
        )
        self.spatial.cell_sizes = self.spatial.backend.asarray(
            spatial_state["cell_sizes"], dtype=xp.int32, copy=True
        )
        self.spatial.entity_cells = self.spatial.backend.asarray(
            spatial_state["entity_cells"], dtype=xp.int32, copy=True
        )
        self.social = copy.deepcopy(state["social"])
        self.social.cfg = self.cfg
        if not hasattr(self.social, "group_labels_dirty"):
            self.social.group_labels_dirty = False
            self.social.last_group_update_tick = int(state["tick"])
            self.social.next_group_decay_due_tick = np.iinfo(np.int64).max
            self.social.group_update_count = 0
            self.social.group_update_skipped_count = 0
            self.social.last_group_update_reason = "legacy-checkpoint"
            self.social.last_group_dirty_reason = "legacy-checkpoint"
        elif not hasattr(self.social, "last_group_dirty_reason"):
            self.social.last_group_dirty_reason = "legacy-checkpoint"
        self.subjects = copy.deepcopy(state["subjects"])
        self.knowledge.restore_state(state["knowledge"])
        self.knowledge.cfg = self.cfg
        self.knowledge.kcfg = self.cfg.knowledge
        self.policy = ParametricPolicy(self.cfg)
        self.tick = int(state["tick"])
        self.last_group_summary = copy.deepcopy(state["last_group_summary"])
        self.last_group_plan = copy.deepcopy(state["last_group_plan"])
        self.total_births = int(state["total_births"])
        self.total_deaths = int(state["total_deaths"])
        self.total_shared_energy = float(state["total_shared_energy"])
        self.total_harvested_resources = np.asarray(
            state.get("total_harvested_resources", np.zeros(4)), dtype=np.float64
        ).copy()
        self.action_counts = np.asarray(state["action_counts"], dtype=np.int64).copy()
        self.benefit_flow_energy_total = np.asarray(
            state["benefit_flow_energy_total"], dtype=np.float64
        ).copy()
        self.lagged_benefit_boundary = copy.deepcopy(
            state["lagged_benefit_boundary"]
        )
        self.total_reproduction_eligible = int(state["total_reproduction_eligible"])
        self.total_reproduction_proposals = int(state["total_reproduction_proposals"])
        self.total_reproduction_rejected_capacity = int(
            state["total_reproduction_rejected_capacity"]
        )
        self.total_reproduction_rejected_resource = int(
            state["total_reproduction_rejected_resource"]
        )
        self.total_reproduction_rejected_other = int(
            state["total_reproduction_rejected_other"]
        )
        self.evolution_progress.restore_state(state["evolution_progress"])
        local_state = state.get("local_stress_diagnostics")
        if local_state is not None:
            if self.local_stress_diagnostics is None:
                self.local_stress_diagnostics = LocalStressDiagnostics(
                    world_width=self.cfg.world.width,
                    world_height=self.cfg.world.height,
                    regions_x=self.cfg.run.spatial_stress_regions_x,
                    regions_y=self.cfg.run.spatial_stress_regions_y,
                    resource_capacity=self.cfg.environment.resource_capacity,
                    world_grid_x=self.cfg.world.grid_x,
                    world_grid_y=self.cfg.world.grid_y,
                )
            self.local_stress_diagnostics.restore_state(local_state)
        subject_structure_state = state.get("subject_structure_diagnostics")
        if subject_structure_state is not None:
            if self.subject_structure_diagnostics is None:
                self.subject_structure_diagnostics = SubjectStructureDiagnostics(
                    self.output_dir
                )
            self.subject_structure_diagnostics.restore_state(subject_structure_state)
        environment_atlas_state = state.get("environment_atlas_diagnostics")
        if environment_atlas_state is not None:
            if self.environment_atlas_diagnostics is None:
                self.environment_atlas_diagnostics = EnvironmentAtlasDiagnostics(
                    self.output_dir,
                    world_width=self.cfg.world.width,
                    world_height=self.cfg.world.height,
                    world_grid_x=self.cfg.world.grid_x,
                    world_grid_y=self.cfg.world.grid_y,
                    resource_capacity=self.cfg.environment.resource_capacity,
                    scales=self.cfg.run.environment_atlas_scales,
                )
            self.environment_atlas_diagnostics.restore_state(environment_atlas_state)
        self.last_active = np.asarray(state["last_active"], dtype=np.int32).copy()
        self.last_cells = np.asarray(state["last_cells"], dtype=np.int32).copy()
        self.last_local_resources = np.asarray(
            state["last_local_resources"], dtype=np.float32
        ).copy()
        self.last_information = copy.deepcopy(state["last_information"])
        self.last_policy_decision = copy.deepcopy(state["last_policy_decision"])
        self.last_knowledge_policy_plan = copy.deepcopy(
            state.get("last_knowledge_policy_plan", KnowledgePolicyPlan.empty(self.tick))
        )
        self.last_intents = copy.deepcopy(state["last_intents"])
        self.last_resolutions = copy.deepcopy(state["last_resolutions"])
        self.last_birth_allocation = copy.deepcopy(state["last_birth_allocation"])
        self.last_death_events = copy.deepcopy(state["last_death_events"])
        self.last_entity_device_commit = copy.deepcopy(
            state["last_entity_device_commit"]
        )
        self.control_arbiter = copy.deepcopy(state["control_arbiter"])
        self.group_label_planner = copy.deepcopy(state["group_label_planner"])
        checkpoint_resolver_kind = str(state["conflict_resolver_kind"])
        if checkpoint_resolver_kind not in {
            "DeterministicActionConflictResolver",
            "GpuActionConflictResolver",
        }:
            raise ValueError(
                f"unsupported checkpoint conflict resolver {checkpoint_resolver_kind!r}"
            )
        self.heuristic_guidance_actions = int(state["heuristic_guidance_actions"])
        self.autonomy_recovery_enabled = bool(state["autonomy_recovery_enabled"])
        self.autonomy_restored = np.asarray(
            state["autonomy_restored"], dtype=bool
        ).copy()
        self.autonomy_observation_cohort = np.asarray(
            state["autonomy_observation_cohort"], dtype=bool
        ).copy()
        self.autonomy_recovery_tick = state["autonomy_recovery_tick"]
        self.autonomy_cohort_tick = state["autonomy_cohort_tick"]
        self.autonomy_recovery_cohort_ids = np.asarray(
            state["autonomy_recovery_cohort_ids"], dtype=np.uint64
        ).copy()
        self.autonomy_module_actions = int(state["autonomy_module_actions"])
        self.autonomy_harvest_attempts = int(state["autonomy_harvest_attempts"])
        self.autonomy_harvest_successes = int(state["autonomy_harvest_successes"])
        self.social_control_enabled = bool(state["social_control_enabled"])
        self.social_connections_enabled = bool(state["social_connections_enabled"])
        self.direct_messages_enabled = bool(state["direct_messages_enabled"])
        self.freeze_genotype = bool(state["freeze_genotype"])
        self.resource_affinity_ablation_enabled = bool(
            state.get("resource_affinity_ablation_enabled", False)
        )
        self.danger_evidence_ablation_enabled = bool(
            state.get("danger_evidence_ablation_enabled", False)
        )
        self.knowledge_policy_ablation_enabled = bool(
            state.get("knowledge_policy_ablation_enabled", False)
        )
        self.knowledge_transfer_ablation_enabled = bool(
            state.get("knowledge_transfer_ablation_enabled", False)
        )
        self.group_refresh_ablation_enabled = bool(
            state.get("group_refresh_ablation_enabled", False)
        )
        self.intervention_history = copy.deepcopy(state["intervention_history"])
        self._defer_gpu_field_sync = False
        if self.gpu_runtime is not None:
            self.gpu_runtime.sync_from_host(self.environment, self.information)
            self.gpu_runtime.sync_entity_from_host(
                self.entities,
                self.social,
                self.entity_device_version,
            )
        if isinstance(self.conflict_resolver, GpuActionConflictResolver):
            if self.gpu_runtime is None:
                raise ValueError("restored GPU conflict resolver requires a GPU runtime")
            self.conflict_resolver.bind_harvest_planner(self.gpu_runtime)
        if self.cfg.run.validation_mode:
            self._validate_invariants()


    @classmethod
    def from_checkpoint(
        cls,
        checkpoint: str | Path,
        output_dir: str | Path,
        *,
        backend: str = "cpu",
        until_tick: int | None = None,
        gpu_semantics_mode: str | None = None,
    ) -> "Simulation":
        """Create a fresh run from a trusted full-world checkpoint bundle."""
        metadata, record = read_checkpoint_bundle(checkpoint)
        cfg = record["config"]
        checkpoint_tick = int(record["simulation"]["tick"])
        run_overrides: dict[str, object] = {}
        if until_tick is not None:
            target = int(until_tick)
            if target < checkpoint_tick:
                raise ValueError(
                    f"until_tick {target} precedes checkpoint tick {checkpoint_tick}"
                )
            run_overrides["ticks"] = target
        if gpu_semantics_mode is not None:
            if gpu_semantics_mode not in {"strict-reference", "hybrid-accelerated"}:
                raise ValueError("invalid gpu_semantics_mode for restored run")
            run_overrides["gpu_semantics_mode"] = gpu_semantics_mode
        if run_overrides:
            cfg = replace(cfg, run=replace(cfg.run, **run_overrides))
        simulation = cls(cfg, output_dir, backend=backend)
        simulation._restore_full_checkpoint_state(record["simulation"])
        simulation.checkpoint_lineage = copy.deepcopy(
            record.get("checkpoint_lineage", [])
        )
        replay_record = {
            "checkpoint": str(Path(checkpoint).resolve()),
            "checkpoint_schema": metadata["schema"],
            "checkpoint_project_version": metadata["project_version"],
            "checkpoint_tick": checkpoint_tick,
            "checkpoint_state_sha256": metadata["state_sha256"],
            "offline_replay": True,
        }
        simulation.checkpoint_lineage.append(replay_record)
        simulation._write_run_manifest(simulation.requested_backend)
        (simulation.output_dir / "replay_provenance.json").write_text(
            json.dumps(
                {
                    "schema": "offline-replay-provenance-v1",
                    "checkpoint_lineage": simulation.checkpoint_lineage,
                    "event_log_scope": "post-checkpoint",
                    "cumulative_world_counters_restored": True,
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        return simulation


    def clone(self, output_dir: str | Path) -> "Simulation":
        """Clone a snapshot for paired counterfactual runs.

        Metrics and trajectory writers are intentionally recreated for the
        branch.  All mutable world state, including delayed messages and the
        subject graph, is deep-copied before the intervention is applied.
        """
        if self.gpu_runtime is not None and self._defer_gpu_field_sync:
            self.gpu_runtime.sync_to_host(self.environment, self.information)
        branch = type(self)(
            self.cfg,
            output_dir,
            backend=self.requested_backend,
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
        branch.knowledge.close()
        branch.knowledge = self.knowledge.clone(branch.output_dir)
        branch.tick = self.tick
        branch.entity_device_version = self.entity_device_version
        branch.last_group_summary = copy.deepcopy(self.last_group_summary)
        branch.last_group_plan = copy.deepcopy(self.last_group_plan)
        branch.total_births = self.total_births
        branch.total_deaths = self.total_deaths
        branch.total_shared_energy = self.total_shared_energy
        branch.total_harvested_resources = self.total_harvested_resources.copy()
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
        branch.local_stress_diagnostics = (
            self.local_stress_diagnostics.clone()
            if self.local_stress_diagnostics is not None
            else None
        )
        branch.subject_structure_diagnostics = (
            self.subject_structure_diagnostics.clone(branch.output_dir)
            if self.subject_structure_diagnostics is not None
            else None
        )
        branch.environment_atlas_diagnostics = (
            self.environment_atlas_diagnostics.clone(branch.output_dir)
            if self.environment_atlas_diagnostics is not None
            else None
        )
        branch.last_birth_allocation = copy.deepcopy(self.last_birth_allocation)
        branch.last_death_events = copy.deepcopy(self.last_death_events)
        branch.last_entity_device_commit = copy.deepcopy(
            self.last_entity_device_commit
        )
        branch.last_active = self.last_active.copy()
        branch.last_cells = self.last_cells.copy()
        branch.last_local_resources = self.last_local_resources.copy()
        branch.last_information = copy.deepcopy(self.last_information)
        branch.last_policy_decision = copy.deepcopy(self.last_policy_decision)
        branch.last_intents = copy.deepcopy(self.last_intents)
        branch.last_resolutions = copy.deepcopy(self.last_resolutions)
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
        branch.resource_affinity_ablation_enabled = (
            self.resource_affinity_ablation_enabled
        )
        branch.danger_evidence_ablation_enabled = (
            self.danger_evidence_ablation_enabled
        )
        branch.knowledge_policy_ablation_enabled = (
            self.knowledge_policy_ablation_enabled
        )
        branch.knowledge_transfer_ablation_enabled = (
            self.knowledge_transfer_ablation_enabled
        )
        branch.group_refresh_ablation_enabled = (
            self.group_refresh_ablation_enabled
        )
        branch.intervention_history = copy.deepcopy(self.intervention_history)
        branch.checkpoint_lineage = copy.deepcopy(self.checkpoint_lineage)
        branch._write_run_manifest(branch.requested_backend)
        if branch.gpu_runtime is not None:
            branch.gpu_runtime.sync_from_host(branch.environment, branch.information)
            branch.gpu_runtime.sync_entity_from_host(
                branch.entities,
                branch.social,
                branch.entity_device_version,
            )
        return branch

