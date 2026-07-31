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
from se.differentiation.physiology import (
    resource_metabolism_enabled,
    storage_constrained_intake_enabled,
    external_resource_recycling_enabled,
)
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
        self.sync_host_semantic_state()
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
            "total_death_cause_counts": self.total_death_cause_counts.copy(),
            "total_shared_energy": float(self.total_shared_energy),
            "total_harvested_resources": self.total_harvested_resources.copy(),
            "total_requested_harvest_resources": self.total_requested_harvest_resources.copy(),
            **(
                {
                    "total_resource_stored": self.total_resource_stored.copy(),
                    "total_resource_store_overflow": self.total_resource_store_overflow.copy(),
                    **(
                        {
                            "total_resource_intake_capacity_rejected": self.total_resource_intake_capacity_rejected.copy()
                        }
                        if storage_constrained_intake_enabled(self.cfg)
                        else {}
                    ),
                    "total_resource_converted": self.total_resource_converted.copy(),
                    "total_resource_store_decay": self.total_resource_store_decay.copy(),
                    "total_resource_store_death_loss": self.total_resource_store_death_loss.copy(),
                    "total_resource_body_realized": self.total_resource_body_realized.copy(),
                    "total_resource_processing_requested": self.total_resource_processing_requested.copy(),
                    "total_resource_processing_supported": self.total_resource_processing_supported.copy(),
                    "total_resource_processing_support_limited": self.total_resource_processing_support_limited.copy(),
                    "total_resource_processing_support_accelerated": self.total_resource_processing_support_accelerated.copy(),
                    "total_resource_processing_energy_rejected": self.total_resource_processing_energy_rejected.copy(),
                    "total_resource_processing_support_weighted_sum": self.total_resource_processing_support_weighted_sum.copy(),
                    "total_resource_processing_support_weight": self.total_resource_processing_support_weight.copy(),
                    "total_resource_processing_support_absolute_deviation": self.total_resource_processing_support_absolute_deviation.copy(),
                    "total_resource_processing_energy_cost": float(
                        self.total_resource_processing_energy_cost
                    ),
                    **(
                        {
                            "total_resource_residue_deposited": self.total_resource_residue_deposited.copy(),
                            "total_resource_residue_released": self.total_resource_residue_released.copy(),
                            "pending_resource_residue_cells": self.pending_resource_residue_cells.copy(),
                            "pending_resource_residue_amounts": self.pending_resource_residue_amounts.copy(),
                        }
                        if external_resource_recycling_enabled(self.cfg)
                        else {}
                    ),
                }
                if resource_metabolism_enabled(self.cfg)
                else {}
            ),
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
            "total_functional_module_movement_energy_delta": float(
                self.total_functional_module_movement_energy_delta
            ),
            "total_functional_module_signal_energy_delta": float(
                self.total_functional_module_signal_energy_delta
            ),
            "total_functional_module_repair_energy": float(
                self.total_functional_module_repair_energy
            ),
            "total_functional_module_repair_material": float(
                self.total_functional_module_repair_material
            ),
            "total_functional_module_repair_integrity": float(
                self.total_functional_module_repair_integrity
            ),
            **{
                f"total_physiology_{name}": float(getattr(self, f"total_physiology_{name}"))
                for name in (
                    "oxygen_uptake", "oxygen_use", "perfusion_energy",
                    "repair_energy", "repair_material", "repair_oxygen",
                    "repair_tissue", "repair_structure", "repair_integrity",
                    "hypoxia_tissue_damage", "wear_tissue_damage",
                    "wear_structure_damage", "integrity_damage",
                    "messenger_synthesis", "messenger_decay",
                    "messenger_precursor_used", "messenger_precursor_recovered",
                    "messenger_energy", "computation_energy",
                    "computation_oxygen", "fatigue_generated", "fatigue_cleared",
                )
            },
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
            "capacity_ablation_enabled": bool(self.capacity_ablation_enabled),
            "resource_affinity_ablation_enabled": bool(
                self.resource_affinity_ablation_enabled
            ),
            "resource_sensing_ablation_enabled": bool(
                self.resource_sensing_ablation_enabled
            ),
            "resource_conversion_allocation_ablation_enabled": bool(
                self.resource_conversion_allocation_ablation_enabled
            ),
            "resource_store_allocation_ablation_enabled": bool(
                self.resource_store_allocation_ablation_enabled
            ),
            "resource_recycling_ablation_enabled": bool(
                self.resource_recycling_ablation_enabled
            ),
            "offspring_endowment_ablation_enabled": bool(
                self.offspring_endowment_ablation_enabled
            ),
            "resource_processing_support_ablation_enabled": bool(
                self.resource_processing_support_ablation_enabled
            ),
            "functional_modules_ablation_enabled": bool(
                self.functional_modules_ablation_enabled
            ),
            "functional_module_coupling_ablation_enabled": bool(
                self.functional_module_coupling_ablation_enabled
            ),
            "functional_module_embodied_output_ablation_enabled": bool(
                self.functional_module_embodied_output_ablation_enabled
            ),
            "functional_module_physiology_output_ablation_enabled": bool(
                self.functional_module_physiology_output_ablation_enabled
            ),
            "physiology_messenger_receptor_blockade_enabled": bool(
                self.physiology_messenger_receptor_blockade_enabled
            ),
            "physiology_state_clamps": {
                str(name): float(value)
                for name, value in self.physiology_state_clamps.items()
            },
            "functional_module_ablation_mask": (
                self.functional_module_ablation_mask.astype(bool).copy()
            ),
            "functional_module_lineage_output_ablation": {
                int(module): tuple(sorted(int(lineage) for lineage in lineages))
                for module, lineages in self.functional_module_lineage_output_ablation.items()
            },
            "functional_module_lineage_cost_ablation": {
                int(module): tuple(sorted(int(lineage) for lineage in lineages))
                for module, lineages in self.functional_module_lineage_cost_ablation.items()
            },
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
        entity_capacity = self.entities.alive.size
        for name, default in (
            ("oxygenation", self.cfg.physiology.initial_oxygenation),
            ("tissue_condition", self.cfg.physiology.initial_tissue_condition),
            ("structure_condition", self.cfg.physiology.initial_structure_condition),
            ("metabolic_fatigue", self.cfg.physiology.initial_metabolic_fatigue),
            ("mobilization_messenger", self.cfg.physiology.initial_mobilization_messenger),
            ("maintenance_messenger", self.cfg.physiology.initial_maintenance_messenger),
            ("messenger_precursor", self.cfg.physiology.initial_messenger_precursor),
            ("physiology_sensor_multiplier", 1.0),
        ):
            if not hasattr(self.entities, name):
                values = np.zeros(entity_capacity, dtype=np.float32)
                values[self.entities.alive] = np.float32(default)
                setattr(self.entities, name, values)
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
        if not hasattr(self.environment, "resource_spatial_reversed"):
            self.environment.resource_spatial_reversed = bool(
                getattr(self.environment, "spatial_reversed", False)
            )
        if not hasattr(self.environment, "resource_processing_support_reversed"):
            self.environment.resource_processing_support_reversed = False
        if not all(hasattr(self.environment, name) for name in ("oxygen", "terrain", "wear")):
            self.environment.update_physiology_fields(int(state["tick"]))
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
        self.total_death_cause_counts = np.asarray(
            state.get("total_death_cause_counts", np.zeros(8)), dtype=np.int64
        ).copy()
        if self.total_death_cause_counts.shape != (8,):
            raise ValueError("checkpoint death-cause counts must contain eight buckets")
        self.total_shared_energy = float(state["total_shared_energy"])
        self.total_harvested_resources = np.asarray(
            state.get("total_harvested_resources", np.zeros(4)), dtype=np.float64
        ).copy()
        self.total_requested_harvest_resources = np.asarray(
            state.get("total_requested_harvest_resources", np.zeros(4)), dtype=np.float64
        ).copy()
        if resource_metabolism_enabled(self.cfg):
            self.total_resource_stored = np.asarray(
                state.get("total_resource_stored", np.zeros(4)), dtype=np.float64
            ).copy()
            self.total_resource_store_overflow = np.asarray(
                state.get("total_resource_store_overflow", np.zeros(4)), dtype=np.float64
            ).copy()
            if storage_constrained_intake_enabled(self.cfg):
                self.total_resource_intake_capacity_rejected = np.asarray(
                    state.get("total_resource_intake_capacity_rejected", np.zeros(4)),
                    dtype=np.float64,
                ).copy()
            self.total_resource_converted = np.asarray(
                state.get("total_resource_converted", np.zeros(4)), dtype=np.float64
            ).copy()
            self.total_resource_store_decay = np.asarray(
                state.get("total_resource_store_decay", np.zeros(4)), dtype=np.float64
            ).copy()
            self.total_resource_store_death_loss = np.asarray(
                state.get("total_resource_store_death_loss", np.zeros(4)), dtype=np.float64
            ).copy()
            self.total_resource_body_realized = np.asarray(
                state.get("total_resource_body_realized", np.zeros(5)), dtype=np.float64
            ).copy()
            self.total_resource_processing_requested = np.asarray(
                state.get("total_resource_processing_requested", np.zeros(4)),
                dtype=np.float64,
            ).copy()
            self.total_resource_processing_supported = np.asarray(
                state.get("total_resource_processing_supported", np.zeros(4)),
                dtype=np.float64,
            ).copy()
            self.total_resource_processing_support_limited = np.asarray(
                state.get("total_resource_processing_support_limited", np.zeros(4)),
                dtype=np.float64,
            ).copy()
            self.total_resource_processing_support_accelerated = np.asarray(
                state.get("total_resource_processing_support_accelerated", np.zeros(4)),
                dtype=np.float64,
            ).copy()
            self.total_resource_processing_energy_rejected = np.asarray(
                state.get("total_resource_processing_energy_rejected", np.zeros(4)),
                dtype=np.float64,
            ).copy()
            self.total_resource_processing_support_weighted_sum = np.asarray(
                state.get(
                    "total_resource_processing_support_weighted_sum", np.zeros(4)
                ),
                dtype=np.float64,
            ).copy()
            self.total_resource_processing_support_weight = np.asarray(
                state.get("total_resource_processing_support_weight", np.zeros(4)),
                dtype=np.float64,
            ).copy()
            self.total_resource_processing_support_absolute_deviation = np.asarray(
                state.get(
                    "total_resource_processing_support_absolute_deviation",
                    np.zeros(4),
                ),
                dtype=np.float64,
            ).copy()
            self.total_resource_processing_energy_cost = float(
                state.get("total_resource_processing_energy_cost", 0.0)
            )
            if external_resource_recycling_enabled(self.cfg):
                self.total_resource_residue_deposited = np.asarray(
                    state.get("total_resource_residue_deposited", np.zeros(4)), dtype=np.float64
                ).copy()
                self.total_resource_residue_released = np.asarray(
                    state.get("total_resource_residue_released", np.zeros(4)), dtype=np.float64
                ).copy()
                self.pending_resource_residue_cells = np.asarray(
                    state.get("pending_resource_residue_cells", np.zeros(0)), dtype=np.int32
                ).copy()
                self.pending_resource_residue_amounts = np.asarray(
                    state.get("pending_resource_residue_amounts", np.zeros((0, 4))), dtype=np.float32
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
        self.total_functional_module_movement_energy_delta = float(
            state.get("total_functional_module_movement_energy_delta", 0.0)
        )
        self.total_functional_module_signal_energy_delta = float(
            state.get("total_functional_module_signal_energy_delta", 0.0)
        )
        self.total_functional_module_repair_energy = float(
            state.get("total_functional_module_repair_energy", 0.0)
        )
        self.total_functional_module_repair_material = float(
            state.get("total_functional_module_repair_material", 0.0)
        )
        self.total_functional_module_repair_integrity = float(
            state.get("total_functional_module_repair_integrity", 0.0)
        )
        for name in (
            "oxygen_uptake", "oxygen_use", "perfusion_energy",
            "repair_energy", "repair_material", "repair_oxygen",
            "repair_tissue", "repair_structure", "repair_integrity",
            "hypoxia_tissue_damage", "wear_tissue_damage",
            "wear_structure_damage", "integrity_damage",
            "messenger_synthesis", "messenger_decay",
            "messenger_precursor_used", "messenger_precursor_recovered",
            "messenger_energy", "computation_energy",
            "computation_oxygen", "fatigue_generated", "fatigue_cleared",
        ):
            setattr(
                self,
                f"total_physiology_{name}",
                float(state.get(f"total_physiology_{name}", 0.0)),
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
        self.capacity_ablation_enabled = bool(
            state.get("capacity_ablation_enabled", False)
        )
        self.resource_affinity_ablation_enabled = bool(
            state.get("resource_affinity_ablation_enabled", False)
        )
        self.resource_sensing_ablation_enabled = bool(
            state.get("resource_sensing_ablation_enabled", False)
        )
        self.resource_conversion_allocation_ablation_enabled = bool(
            state.get("resource_conversion_allocation_ablation_enabled", False)
        )
        self.resource_store_allocation_ablation_enabled = bool(
            state.get("resource_store_allocation_ablation_enabled", False)
        )
        self.resource_recycling_ablation_enabled = bool(
            state.get("resource_recycling_ablation_enabled", False)
        )
        self.offspring_endowment_ablation_enabled = bool(
            state.get("offspring_endowment_ablation_enabled", False)
        )
        self.environment.resource_recycling_ablation_enabled = (
            self.resource_recycling_ablation_enabled
        )
        if self.gpu_runtime is not None:
            self.gpu_runtime.environment.resource_recycling_ablation_enabled = (
                self.resource_recycling_ablation_enabled
            )
        self.resource_processing_support_ablation_enabled = bool(
            state.get("resource_processing_support_ablation_enabled", False)
        )
        self.functional_modules_ablation_enabled = bool(
            state.get("functional_modules_ablation_enabled", False)
        )
        self.functional_module_coupling_ablation_enabled = bool(
            state.get("functional_module_coupling_ablation_enabled", False)
        )
        self.functional_module_embodied_output_ablation_enabled = bool(
            state.get("functional_module_embodied_output_ablation_enabled", False)
        )
        self.functional_module_physiology_output_ablation_enabled = bool(
            state.get("functional_module_physiology_output_ablation_enabled", False)
        )
        self.physiology_messenger_receptor_blockade_enabled = bool(
            state.get("physiology_messenger_receptor_blockade_enabled", False)
        )
        self.physiology_state_clamps = {
            str(name): float(value)
            for name, value in dict(state.get("physiology_state_clamps", {})).items()
        }
        default_module_mask = np.full(
            int(self.cfg.functional_modules.module_count),
            self.functional_modules_ablation_enabled,
            dtype=bool,
        )
        self.functional_module_ablation_mask = np.asarray(
            state.get("functional_module_ablation_mask", default_module_mask),
            dtype=bool,
        ).copy()
        if self.functional_module_ablation_mask.shape != default_module_mask.shape:
            raise ValueError("checkpoint functional module ablation mask shape mismatch")
        self.functional_modules_ablation_enabled = bool(
            np.all(self.functional_module_ablation_mask)
        )
        self.functional_module_lineage_output_ablation = {
            int(module): {int(lineage) for lineage in lineages}
            for module, lineages in dict(
                state.get("functional_module_lineage_output_ablation", {})
            ).items()
        }
        self.functional_module_lineage_cost_ablation = {
            int(module): {int(lineage) for lineage in lineages}
            for module, lineages in dict(
                state.get("functional_module_lineage_cost_ablation", {})
            ).items()
        }
        module_count = int(self.cfg.functional_modules.module_count)
        for mapping_name, mapping in (
            (
                "functional_module_lineage_output_ablation",
                self.functional_module_lineage_output_ablation,
            ),
            (
                "functional_module_lineage_cost_ablation",
                self.functional_module_lineage_cost_ablation,
            ),
        ):
            if any(not 0 <= int(module) < module_count for module in mapping):
                raise ValueError(f"checkpoint {mapping_name} module index mismatch")
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
        backend: str = "auto",
        until_tick: int | None = None,
        gpu_semantics_mode: str | None = None,
        checkpoint_ticks: tuple[int, ...] | None = None,
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
        if checkpoint_ticks is not None:
            normalized_ticks = tuple(sorted(set(int(value) for value in checkpoint_ticks)))
            if any(value < checkpoint_tick for value in normalized_ticks):
                raise ValueError(
                    "checkpoint_ticks for a restored run cannot precede the source checkpoint"
                )
            run_overrides["checkpoint_ticks"] = normalized_ticks
            run_overrides["full_checkpoint_enabled"] = True
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
        branch.total_death_cause_counts = self.total_death_cause_counts.copy()
        branch.total_shared_energy = self.total_shared_energy
        branch.total_harvested_resources = self.total_harvested_resources.copy()
        branch.total_requested_harvest_resources = (
            self.total_requested_harvest_resources.copy()
        )
        if resource_metabolism_enabled(self.cfg):
            branch.total_resource_stored = self.total_resource_stored.copy()
            branch.total_resource_store_overflow = self.total_resource_store_overflow.copy()
            if storage_constrained_intake_enabled(self.cfg):
                branch.total_resource_intake_capacity_rejected = (
                    self.total_resource_intake_capacity_rejected.copy()
                )
            branch.total_resource_converted = self.total_resource_converted.copy()
            branch.total_resource_store_decay = self.total_resource_store_decay.copy()
            branch.total_resource_store_death_loss = self.total_resource_store_death_loss.copy()
            branch.total_resource_body_realized = self.total_resource_body_realized.copy()
            branch.total_resource_processing_requested = (
                self.total_resource_processing_requested.copy()
            )
            branch.total_resource_processing_supported = (
                self.total_resource_processing_supported.copy()
            )
            branch.total_resource_processing_support_limited = (
                self.total_resource_processing_support_limited.copy()
            )
            branch.total_resource_processing_support_accelerated = (
                self.total_resource_processing_support_accelerated.copy()
            )
            branch.total_resource_processing_energy_rejected = (
                self.total_resource_processing_energy_rejected.copy()
            )
            branch.total_resource_processing_support_weighted_sum = (
                self.total_resource_processing_support_weighted_sum.copy()
            )
            branch.total_resource_processing_support_weight = (
                self.total_resource_processing_support_weight.copy()
            )
            branch.total_resource_processing_support_absolute_deviation = (
                self.total_resource_processing_support_absolute_deviation.copy()
            )
            branch.total_resource_processing_energy_cost = (
                self.total_resource_processing_energy_cost
            )
            if external_resource_recycling_enabled(self.cfg):
                branch.total_resource_residue_deposited = self.total_resource_residue_deposited.copy()
                branch.total_resource_residue_released = self.total_resource_residue_released.copy()
                branch.pending_resource_residue_cells = self.pending_resource_residue_cells.copy()
                branch.pending_resource_residue_amounts = self.pending_resource_residue_amounts.copy()
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
        branch.total_functional_module_movement_energy_delta = (
            self.total_functional_module_movement_energy_delta
        )
        branch.total_functional_module_signal_energy_delta = (
            self.total_functional_module_signal_energy_delta
        )
        branch.total_functional_module_repair_energy = (
            self.total_functional_module_repair_energy
        )
        branch.total_functional_module_repair_material = (
            self.total_functional_module_repair_material
        )
        branch.total_functional_module_repair_integrity = (
            self.total_functional_module_repair_integrity
        )
        for name in (
            "oxygen_uptake", "oxygen_use", "perfusion_energy",
            "repair_energy", "repair_material", "repair_oxygen",
            "repair_tissue", "repair_structure", "repair_integrity",
            "hypoxia_tissue_damage", "wear_tissue_damage",
            "wear_structure_damage", "integrity_damage",
            "messenger_synthesis", "messenger_decay",
            "messenger_precursor_used", "messenger_precursor_recovered",
            "messenger_energy", "computation_energy",
            "computation_oxygen", "fatigue_generated", "fatigue_cleared",
        ):
            setattr(
                branch, f"total_physiology_{name}",
                float(getattr(self, f"total_physiology_{name}")),
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
        branch.capacity_ablation_enabled = self.capacity_ablation_enabled
        branch.resource_affinity_ablation_enabled = (
            self.resource_affinity_ablation_enabled
        )
        branch.resource_sensing_ablation_enabled = (
            self.resource_sensing_ablation_enabled
        )
        branch.resource_conversion_allocation_ablation_enabled = (
            self.resource_conversion_allocation_ablation_enabled
        )
        branch.resource_store_allocation_ablation_enabled = (
            self.resource_store_allocation_ablation_enabled
        )
        branch.resource_recycling_ablation_enabled = (
            self.resource_recycling_ablation_enabled
        )
        branch.offspring_endowment_ablation_enabled = (
            self.offspring_endowment_ablation_enabled
        )
        branch.environment.resource_recycling_ablation_enabled = (
            self.resource_recycling_ablation_enabled
        )
        if branch.gpu_runtime is not None:
            branch.gpu_runtime.environment.resource_recycling_ablation_enabled = (
                self.resource_recycling_ablation_enabled
            )
        branch.resource_processing_support_ablation_enabled = (
            self.resource_processing_support_ablation_enabled
        )
        branch.functional_modules_ablation_enabled = (
            self.functional_modules_ablation_enabled
        )
        branch.functional_module_coupling_ablation_enabled = (
            self.functional_module_coupling_ablation_enabled
        )
        branch.functional_module_embodied_output_ablation_enabled = (
            self.functional_module_embodied_output_ablation_enabled
        )
        branch.functional_module_physiology_output_ablation_enabled = (
            self.functional_module_physiology_output_ablation_enabled
        )
        branch.physiology_messenger_receptor_blockade_enabled = (
            self.physiology_messenger_receptor_blockade_enabled
        )
        branch.physiology_state_clamps = copy.deepcopy(self.physiology_state_clamps)
        branch.functional_module_ablation_mask = (
            self.functional_module_ablation_mask.copy()
        )
        branch.functional_module_lineage_output_ablation = copy.deepcopy(
            self.functional_module_lineage_output_ablation
        )
        branch.functional_module_lineage_cost_ablation = copy.deepcopy(
            self.functional_module_lineage_cost_ablation
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

