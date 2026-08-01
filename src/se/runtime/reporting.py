from __future__ import annotations

from dataclasses import asdict, dataclass, field, replace
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
    physiology_diagnostics,
    resource_metabolism_enabled,
    spatial_processing_enabled,
    storage_constrained_intake_enabled,
    external_resource_recycling_enabled,
)
from se.runtime.resource_metabolism import resource_metabolism_diagnostics
from se.env.recycling import resource_recycling_diagnostics
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
from se.env.physiology import field_metrics as physiology_field_metrics
from se.env.signal_medium import medium_metrics as signal_medium_metrics
from se.env.diversity import (
    ORTHOGONAL_ENVIRONMENT_SCHEMA,
    PERSISTENT_ORTHOGONAL_ENVIRONMENT_SCHEMA,
    MULTISCALE_PERSISTENT_ENVIRONMENT_SCHEMA,
    STRUCTURED_PROVINCE_ENVIRONMENT_SCHEMA,
    configured_resource_scale_metrics,
    orthogonal_environment_enabled,
    persistent_orthogonal_renewal_enabled,
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
from se.env.resource_sensing import resource_sensing_diagnostics
from se.runtime.resource_metabolism import storage_room_fraction
from se.runtime.reproduction import (
    conservative_reproduction_investment_enabled,
    inherited_reproduction_investment_enabled,
    reproduction_energy_requirement,
    reproduction_investment,
)
from ..event_cohort import EventCohortDiagnostics
from se.differentiation.capacity import capacity_diagnostics, capacity_use_diagnostics
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


class SimulationReportingMixin:
    """Run provenance, scientific validity, progress, and metric publication."""

    def write_run_plan(self, target_tick: int) -> Path:
        """Write the resolved execution plan before the first authoritative step.

        This is provenance, not an adaptive scheduler: the plan records the
        predeclared target, reporting cadence, checkpoint cadence and resolved
        backend without using run outcomes to alter the world.
        """
        config_payload = asdict(self.cfg)
        canonical = json.dumps(
            config_payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
        plan = {
            "schema": "simulation-run-plan-v1",
            "version": __version__,
            "start_tick": int(self.tick),
            "target_tick": int(target_tick),
            "requested_backend": self.requested_backend,
            "execution_backend": self.execution_backend,
            "gpu_semantics_mode": self.gpu_semantics_mode,
            "gpu_acceleration_enabled": bool(self.gpu_acceleration_enabled),
            "gpu_fallback_used": bool(self.gpu_fallback_used),
            "gpu_fallback_reason": self.gpu_fallback_reason,
            "gpu_memory_pool": {
                "policy": self.cfg.run.gpu_memory_pool_policy,
                "cache_limit_bytes": (
                    self.cfg.run.gpu_memory_pool_cache_limit_bytes
                ),
                "trim_period": self.cfg.run.gpu_memory_pool_trim_period,
                "live_allocations_unmodified": True,
            },
            "experiment_mode": self.experiment_mode.value,
            "resolved_config_sha256": hashlib.sha256(canonical).hexdigest(),
            "reporting": {
                "metrics_period": int(self.cfg.run.metrics_period),
                "summary_schema": "authoritative-reporting-snapshot-v1",
                "device_state_materialized_at_every_report": True,
            },
            "checkpoints": {
                "period": int(self.cfg.run.checkpoint_period),
                "exact_ticks": [int(value) for value in self.cfg.run.checkpoint_ticks],
                "full_checkpoint_enabled": bool(self.cfg.run.full_checkpoint_enabled),
                "thin_pattern": "checkpoint_{tick:08d}.npz",
                "full_pattern": "checkpoint_{tick:08d}.sechk",
            },
            "planned_outputs": [
                "run_plan.json",
                "metrics.csv",
                "summary.json",
                "scientific_validity.json",
                "run_metadata.json",
            ],
            "checkpoint_lineage": copy.deepcopy(self.checkpoint_lineage),
            "outcome_conditioned_schedule_changes": False,
        }
        destination = self.output_dir / "run_plan.json"
        destination.write_text(
            json.dumps(plan, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        return destination

    def sync_host_semantic_state(self) -> None:
        """Materialize device-owned semantic fields at most once per tick."""
        if self.gpu_runtime is None:
            self.host_semantic_state_tick = int(self.tick)
            return
        if int(getattr(self, "host_semantic_state_tick", -1)) == int(self.tick):
            return
        self.gpu_runtime.sync_to_host(self.environment, self.information)
        self.host_semantic_state_tick = int(self.tick)

    def materialize_reporting_state(self) -> None:
        """Make every field used by one report authoritative at ``self.tick``.

        Hybrid runs deliberately defer full device-to-host field copies between
        checkpoints. A report is a separate semantic boundary: summary fields
        must never silently mix current entity counters with an older host
        environment mirror.
        """
        self.sync_host_semantic_state()
        source = "gpu-materialized" if self.gpu_runtime is not None else "cpu-authoritative"
        self.reporting_state_tick = int(self.tick)
        self.reporting_state_source = source

    def _write_run_manifest(self, requested_backend: str) -> None:
        config_payload = json.dumps(
            self.cfg, default=lambda value: value.__dict__, sort_keys=True
        ).encode("utf-8")
        manifest = {
            "version": __version__,
            "seed": self.cfg.run.seed,
            "requested_backend": requested_backend,
            "execution_backend": self.execution_backend,
            "gpu_semantics_mode": self.gpu_semantics_mode,
            "gpu_device_validated": self.gpu_device_validated,
            "gpu_acceleration_enabled": self.gpu_acceleration_enabled,
            "gpu_fallback_used": self.gpu_fallback_used,
            "gpu_fallback_reason": self.gpu_fallback_reason,
            "gpu_latent_root_hash_batch_enabled": bool(
                self.gpu_runtime is not None
                and self.cfg.knowledge.latent_policy_enabled
            ),
            "gpu_latent_root_hash_schema": (
                "splitmix64-uint64-device-hash-cpu-ordered-quantization-v1"
                if (
                    self.gpu_runtime is not None
                    and self.cfg.knowledge.latent_policy_enabled
                )
                else None
            ),
            "python": sys.version,
            "platform": platform.platform(),
            "numpy": np.__version__,
            "config_sha256": hashlib.sha256(config_payload).hexdigest(),
            "environment_schema": self.cfg.environment.schema,
            "environment_resource_channels": 4,
            "environment_spatially_asynchronous": (
                self.cfg.environment.schema
                in {
                    "spatially-asynchronous-multiniche-v1",
                    ORTHOGONAL_ENVIRONMENT_SCHEMA,
                    PERSISTENT_ORTHOGONAL_ENVIRONMENT_SCHEMA,
                    MULTISCALE_PERSISTENT_ENVIRONMENT_SCHEMA,
                    STRUCTURED_PROVINCE_ENVIRONMENT_SCHEMA,
                }
            ),
            "environment_process": dict(
                self.environment.environment_process_metadata
            ),
            "resource_affinity_enabled": (
                self.cfg.entities.resource_affinity_schema
                == "normalized-four-resource-affinity-v1"
            ),
            "resource_affinity_schema": self.cfg.entities.resource_affinity_schema,
            "resource_affinity_strength": self.cfg.entities.resource_affinity_strength,
            "harvest_allocation_schema": self.cfg.entities.harvest_allocation_schema,
            "resource_processing_schema": self.cfg.environment.resource_processing_schema,
            "resource_processing_support_amplitude": self.cfg.environment.resource_processing_support_amplitude,
            "resource_processing_support_orientation_reversed": bool(
                self.environment.resource_processing_support_reversed
            ),
            "resource_processing_energy_per_unit": list(
                self.cfg.physiology.resource_processing_energy_per_unit
            ),
            "resource_affinity_gene_indices": (
                [1, 2, 3, 4]
                if self.cfg.entities.resource_affinity_schema
                == "normalized-four-resource-affinity-v1"
                else []
            ),
            "resource_affinity_fixed_budget_q": (
                4 * 4096
                if self.cfg.entities.resource_affinity_schema
                == "normalized-four-resource-affinity-v1"
                else None
            ),
            "long_run_diagnostics_enabled": (
                self.cfg.run.long_run_diagnostics_enabled
            ),
            "long_run_diagnostics_schema": (
                self.cfg.run.long_run_diagnostics_schema
            ),
            "spatial_stress_diagnostics_enabled": (
                self.cfg.run.spatial_stress_diagnostics_enabled
            ),
            "spatial_stress_diagnostics_schema": (
                self.cfg.run.spatial_stress_diagnostics_schema
            ),
            "spatial_stress_regions": (
                [
                    self.cfg.run.spatial_stress_regions_x,
                    self.cfg.run.spatial_stress_regions_y,
                ]
                if self.cfg.run.spatial_stress_diagnostics_enabled
                else None
            ),
            "spatial_stress_region_partition": (
                self.local_stress_diagnostics.partition.metadata()
                if self.local_stress_diagnostics is not None
                else None
            ),
            "subject_structure_diagnostics_enabled": (
                self.subject_structure_diagnostics is not None
            ),
            "subject_structure_diagnostics_schema": (
                self.cfg.run.subject_structure_diagnostics_schema
            ),
            "environment_atlas_diagnostics_enabled": (
                self.environment_atlas_diagnostics is not None
            ),
            "environment_atlas_diagnostics_schema": (
                self.cfg.run.environment_atlas_diagnostics_schema
            ),
            "environment_atlas": (
                self.environment_atlas_diagnostics.metadata()
                if self.environment_atlas_diagnostics is not None
                else None
            ),
            "group_function_diagnostics_enabled": (
                self.group_function_diagnostics is not None
            ),
            "group_function_diagnostics_schema": (
                self.cfg.run.group_function_diagnostics_schema
            ),
            "group_function_window_ticks": (
                self.cfg.run.group_function_window_ticks
            ),
            "reconnaissance_diagnostics_enabled": (
                self.reconnaissance_diagnostics is not None
            ),
            "reconnaissance_diagnostics_schema": (
                self.cfg.run.reconnaissance_diagnostics_schema
            ),
            "reconnaissance_window_ticks": (
                self.cfg.run.reconnaissance_window_ticks
            ),
            "resource_load_schema": self.cfg.entities.resource_load_schema,
            "resource_contest_schema": self.cfg.entities.resource_contest_schema,
            "danger_sensing_schema": self.cfg.entities.danger_sensing_schema,
            "spatial_cultural_transfer_diagnostics_enabled": (
                self.cfg.run.spatial_stress_diagnostics_schema
                == "spatial-local-stress-culture-diagnostics-v2"
            ),
            "strategy_schema": self.cfg.policy.schema,
            "knowledge_schema": (
                self.cfg.knowledge.schema if self.cfg.knowledge.enabled else None
            ),
            "knowledge_learning_enabled": (
                self.cfg.knowledge.learning_enabled
                if self.cfg.knowledge.enabled
                else False
            ),
            "knowledge_outcome_schema": (
                self.cfg.knowledge.outcome_schema
                if self.cfg.knowledge.learning_enabled
                else None
            ),
            "knowledge_outcome_dense_log_enabled": (
                self.cfg.knowledge.learning_enabled
                and self.cfg.knowledge.log_outcome_updates
            ),
            "knowledge_transfer_trigger_schema": (
                "signal-action-partner-v1" if self.cfg.knowledge.enabled else None
            ),
            "knowledge_transfer_probability": (
                self.cfg.knowledge.transfer_probability
                if self.cfg.knowledge.enabled else 0.0
            ),
            "knowledge_transfer_period": (
                self.cfg.knowledge.transfer_period if self.cfg.knowledge.enabled else None
            ),
            "knowledge_cultural_metrics_require_committed_transfer": True,
            "knowledge_policy_influence": self.cfg.knowledge.policy_influence_enabled,
            "knowledge_policy_dense_log_enabled": (
                self.cfg.knowledge.policy_influence_enabled
                and self.cfg.knowledge.log_policy_contributions
            ),
            "knowledge_policy_residual_schema": (
                self.cfg.knowledge.policy_residual_schema
                if self.cfg.knowledge.policy_influence_enabled
                else None
            ),
            "knowledge_latent_policy_enabled": self.cfg.knowledge.latent_policy_enabled,
            "knowledge_latent_schema": (
                self.cfg.knowledge.latent_schema
                if self.cfg.knowledge.latent_policy_enabled
                else None
            ),
            "knowledge_latent_router_schema": (
                self.cfg.knowledge.latent_router_schema
                if self.cfg.knowledge.latent_policy_enabled
                else None
            ),
            "knowledge_latent_length_levels": (
                list(self.cfg.knowledge.latent_length_levels)
                if self.cfg.knowledge.latent_policy_enabled
                else None
            ),
            "knowledge_latent_projection_width": (
                self.cfg.knowledge.latent_router_hidden_width
                if self.cfg.knowledge.latent_policy_enabled
                else None
            ),
            "knowledge_latent_mlp_hidden_width": (
                self.cfg.knowledge.latent_router_mlp_hidden_width
                if self.cfg.knowledge.latent_router_schema == "quantized-mlp-latent-router-v1"
                else None
            ),
            "knowledge_latent_activation": (
                "integer-hard-tanh-v1"
                if self.cfg.knowledge.latent_router_schema == "quantized-mlp-latent-router-v1"
                else None
            ),
            "knowledge_latent_quantized_publish": (
                self.cfg.knowledge.latent_policy_enabled
            ),
            "knowledge_routing_cost_enabled": self.cfg.knowledge.routing_cost_enabled,
            "knowledge_routing_cost_dense_log_enabled": (
                self.cfg.knowledge.routing_cost_enabled
                and self.cfg.knowledge.log_routing_costs
            ),
            "knowledge_routing_cost_schema": (
                self.cfg.knowledge.routing_cost_schema
                if self.cfg.knowledge.routing_cost_enabled
                else None
            ),
            "knowledge_routing_budget_mode": (
                self.cfg.knowledge.routing_budget_mode
                if self.cfg.knowledge.routing_cost_enabled
                else None
            ),
            "knowledge_working_memory_enabled": (
                self.cfg.knowledge.working_memory_enabled
            ),
            "knowledge_working_memory_dense_log_enabled": (
                self.cfg.knowledge.working_memory_enabled
                and self.cfg.knowledge.log_working_memory_updates
            ),
            "knowledge_working_memory_schema": (
                self.cfg.knowledge.working_memory_schema
                if self.cfg.knowledge.working_memory_enabled else None
            ),
            "knowledge_working_memory_width": (
                self.cfg.knowledge.working_memory_width
                if self.cfg.knowledge.working_memory_enabled else None
            ),
            "knowledge_working_memory_numeric_semantics": (
                "int16-state-integer-hard-clip-v1"
                if self.cfg.knowledge.working_memory_enabled else None
            ),
            "knowledge_sparse_selection_enabled": (
                self.cfg.knowledge.sparse_selection_enabled
            ),
            "knowledge_sparse_selection_dense_log_enabled": (
                self.cfg.knowledge.sparse_selection_enabled
                and self.cfg.knowledge.log_sparse_selection_events
            ),
            "knowledge_sparse_selection_schema": (
                self.cfg.knowledge.sparse_selection_schema
                if self.cfg.knowledge.sparse_selection_enabled else None
            ),
            "knowledge_sparse_selection_top_k": (
                self.cfg.knowledge.sparse_selection_top_k
                if (
                    self.cfg.knowledge.sparse_selection_enabled
                    and self.cfg.knowledge.sparse_selection_capacity_schema
                    == "fixed-config-topk-v1"
                )
                else None
            ),
            "knowledge_sparse_selection_capacity_schema": (
                self.cfg.knowledge.sparse_selection_capacity_schema
                if self.cfg.knowledge.sparse_selection_enabled else None
            ),
            "knowledge_sparse_selection_capacity_levels": (
                list(self.cfg.knowledge.sparse_selection_capacity_levels)
                if (
                    self.cfg.knowledge.sparse_selection_enabled
                    and self.cfg.knowledge.sparse_selection_capacity_schema
                    == "inherited-discrete-topk-v1"
                )
                else None
            ),
            "knowledge_sparse_selection_authority": (
                "ephemeral-workset-only"
                if self.cfg.knowledge.sparse_selection_enabled else None
            ),
            "knowledge_global_category_embedding": False,
            "knowledge_attention_softmax": False,
            "knowledge_latent_external_optimizer": False,
            "differentiation_enabled": self.cfg.differentiation.enabled,
            "differentiation_schema": self.cfg.differentiation.schema,
            "differentiation_capacity_gene_start": (
                ParametricPolicy.capacity_gene_start(self.cfg)
                if self.cfg.differentiation.enabled else None
            ),
            "differentiation_capacity_gene_count": (
                4 if self.cfg.differentiation.enabled else 0
            ),
            "differentiation_capacity_bounds": (
                {
                    "working_memory_dimensions": [
                        self.cfg.differentiation.working_memory_min_dimensions,
                        self.cfg.differentiation.working_memory_max_dimensions,
                    ],
                    "knowledge_bytes": [
                        self.cfg.differentiation.knowledge_min_bytes,
                        self.cfg.differentiation.knowledge_max_bytes,
                    ],
                    "relation_slots": [
                        self.cfg.differentiation.relation_min_slots,
                        self.cfg.differentiation.relation_max_slots,
                    ],
                    "knowledge_attention_slots": [
                        self.cfg.differentiation.attention_min_slots,
                        self.cfg.differentiation.attention_max_slots,
                    ],
                }
                if self.cfg.differentiation.enabled else None
            ),
            "differentiation_feedback_to_world": self.cfg.differentiation.enabled,
            "differentiation_role_labels": False,
            "differentiation_diversity_protection": False,
            "functional_modules_enabled": self.cfg.functional_modules.enabled,
            "functional_modules_schema": self.cfg.functional_modules.schema,
            "functional_modules_gene_start": (
                ParametricPolicy.functional_module_gene_start(self.cfg)
                if self.cfg.functional_modules.enabled else None
            ),
            "functional_modules_module_count": (
                self.cfg.functional_modules.module_count
                if self.cfg.functional_modules.enabled else 0
            ),
            "functional_modules_gene_count": (
                ParametricPolicy.genome_size_for_config(self.cfg)
                - ParametricPolicy.functional_module_gene_start(self.cfg)
                if self.cfg.functional_modules.enabled else 0
            ),
            "functional_modules_input_schema": self.cfg.functional_modules.input_schema,
            "functional_modules_output_schema": self.cfg.functional_modules.output_schema,
            "functional_modules_coupling_schema": (
                self.cfg.functional_modules.coupling_schema
            ),
            "functional_modules_feedback_scope": (
                "harvest-channel-request-only"
                if self.cfg.functional_modules.enabled else None
            ),
            "functional_modules_action_selection": False,
            "functional_modules_new_world_physics": False,
            "functional_modules_diversity_protection": False,
            "knowledge_candidate_tracking": self.cfg.knowledge.candidate_tracking_enabled,
            "knowledge_candidate_schema": (
                self.cfg.knowledge.candidate_schema
                if self.cfg.knowledge.candidate_tracking_enabled
                else None
            ),
            "knowledge_candidate_graph_schema": (
                self.cfg.knowledge.candidate_graph_schema
                if self.cfg.knowledge.candidate_tracking_enabled
                else None
            ),
            "knowledge_candidate_diagnostic_only": True,
            "validation_mode": self.cfg.run.validation_mode,
            "checkpoint_lineage": copy.deepcopy(self.checkpoint_lineage),
            "event_log_scope": (
                "post-checkpoint" if self.checkpoint_lineage else "full-run"
            ),
        }
        if not self.cfg.differentiation.enabled:
            for key in tuple(manifest):
                if key.startswith("differentiation_"):
                    manifest.pop(key)
        if not self.cfg.functional_modules.enabled:
            for key in tuple(manifest):
                if key.startswith("functional_modules_"):
                    manifest.pop(key)
        if orthogonal_environment_enabled(self.cfg):
            manifest["environment_resource_dynamics"] = {
                "schema": self.cfg.environment.schema,
                "cycle_periods": list(self.cfg.environment.resource_cycle_periods),
                "cycle_amplitudes": list(
                    self.cfg.environment.resource_cycle_amplitudes
                ),
                "primary_wave_vectors": [
                    list(vector)
                    for vector in self.cfg.environment.resource_primary_wave_vectors
                ],
                "secondary_wave_vectors": [
                    list(vector)
                    for vector in self.cfg.environment.resource_secondary_wave_vectors
                ],
                "primary_wave_amplitudes": list(
                    self.cfg.environment.resource_primary_wave_amplitudes
                ),
                "secondary_wave_amplitudes": list(
                    self.cfg.environment.resource_secondary_wave_amplitudes
                ),
                "diffusion_rates": list(
                    self.cfg.environment.resource_diffusion_rates
                ),
                "configured_spatial_scales": configured_resource_scale_metrics(
                    self.cfg.environment,
                    grid_x=self.cfg.world.grid_x,
                    grid_y=self.cfg.world.grid_y,
                ),
                "entity_state_feedback": False,
                "lineage_feedback": False,
                "group_feedback": False,
            }
            if persistent_orthogonal_renewal_enabled(self.cfg):
                manifest["environment_resource_dynamics"]["renewal_contract"] = (
                    "moving-target-source-sink-v3-multiscale"
                    if self.cfg.environment.schema == MULTISCALE_PERSISTENT_ENVIRONMENT_SCHEMA
                    else "moving-target-source-sink-v2"
                )
            manifest["environment_resource_diversity_initial"] = (
                resource_field_diversity_metrics(
                    self.environment.resources,
                    self.cfg.environment.resource_capacity,
                )
            )
        (self.output_dir / "run_manifest.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
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
        process_metadata = self.environment.environment_process_metadata
        if (
            process_metadata.get("schema") != "disabled"
            and process_metadata.get("interpretation")
            == "synthetic-observation-or-entertainment-extension"
        ):
            violations.append(
                "synthetic environment process is enabled; treat the run as an "
                "observation/game extension rather than a scientific ecology baseline"
            )
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
            "backend_semantics": {
                "requested_backend": self.requested_backend,
                "execution_backend": self.execution_backend,
                "gpu_semantics_mode": self.gpu_semantics_mode,
                "gpu_device_validated": self.gpu_device_validated,
                "gpu_acceleration_enabled": self.gpu_acceleration_enabled,
                "gpu_fallback_used": self.gpu_fallback_used,
                "gpu_fallback_reason": self.gpu_fallback_reason,
                "gpu_latent_root_hash_batch_enabled": bool(
                    self.gpu_runtime is not None
                    and self.cfg.knowledge.latent_policy_enabled
                ),
                "gpu_latent_root_hash_schema": (
                    "splitmix64-uint64-device-hash-cpu-ordered-quantization-v1"
                    if (
                        self.gpu_runtime is not None
                        and self.cfg.knowledge.latent_policy_enabled
                    )
                    else None
                ),
                "cpu_reference_world_authoritative": (
                    self.gpu_runtime is None
                ),
                "hybrid_acceleration_validation": "external-test-parity-suite",
                "hybrid_acceleration_parity_proven": None,
            },
            "strategy": {
                "architecture": self.cfg.policy.schema,
                "knowledge_schema": self.cfg.knowledge.schema if self.cfg.knowledge.enabled else None,
                "knowledge_outcome_schema": (
                    self.cfg.knowledge.outcome_schema
                    if self.cfg.knowledge.learning_enabled
                    else None
                ),
                "knowledge_learning_enabled": self.cfg.knowledge.learning_enabled,
                "knowledge_policy_influence": self.cfg.knowledge.policy_influence_enabled,
                "knowledge_policy_ablation_enabled": (
                    self.knowledge_policy_ablation_enabled
                ),
                "knowledge_policy_effective_enabled": (
                    self.cfg.knowledge.policy_influence_enabled
                    and not self.knowledge_policy_ablation_enabled
                ),
                "knowledge_transfer_ablation_enabled": (
                    self.knowledge_transfer_ablation_enabled
                ),
                "knowledge_transfer_effective_enabled": (
                    self.cfg.knowledge.enabled
                    and not self.knowledge_transfer_ablation_enabled
                    and self.cfg.knowledge.transfer_probability > 0.0
                ),
                "knowledge_transfer_trigger_schema": "signal-action-partner-v1",
                "knowledge_transfer_probability": self.cfg.knowledge.transfer_probability,
                "knowledge_cultural_metrics_require_committed_transfer": True,
                "capacity_ablation_enabled": self.capacity_ablation_enabled,
                "capacity_effective_schema": (
                    "fixed-midpoint-elastic-capacities-ablation-v1"
                    if self.capacity_ablation_enabled
                    else self.cfg.differentiation.schema
                ),
                "resource_affinity_ablation_enabled": (
                    self.resource_affinity_ablation_enabled
                ),
                "resource_sensing_ablation_enabled": (
                    self.resource_sensing_ablation_enabled
                ),
                "resource_sensing_effective_schema": (
                    "fixed-radius-one-ablation-v1"
                    if self.resource_sensing_ablation_enabled
                    else self.cfg.entities.resource_sensing_schema
                ),
                "resource_conversion_allocation_ablation_enabled": (
                    self.resource_conversion_allocation_ablation_enabled
                ),
                "resource_conversion_allocation_effective_schema": (
                    "configured-neutral-channel-base-ablation-v1"
                    if self.resource_conversion_allocation_ablation_enabled
                    else self.cfg.physiology.schema
                ),
                "resource_store_allocation_ablation_enabled": (
                    self.resource_store_allocation_ablation_enabled
                ),
                "resource_store_allocation_effective_schema": (
                    "configured-neutral-channel-base-ablation-v1"
                    if self.resource_store_allocation_ablation_enabled
                    else self.cfg.physiology.schema
                ),
                "resource_recycling_ablation_enabled": (
                    self.resource_recycling_ablation_enabled
                ),
                "resource_recycling_effective_enabled": (
                    external_resource_recycling_enabled(self.cfg)
                    and not self.resource_recycling_ablation_enabled
                ),
                "resource_processing_support_ablation_enabled": (
                    self.resource_processing_support_ablation_enabled
                ),
                "resource_processing_support_effective_enabled": (
                    spatial_processing_enabled(self.cfg)
                    and not self.resource_processing_support_ablation_enabled
                ),
                "resource_processing_support_orientation_reversed": bool(
                    self.environment.resource_processing_support_reversed
                ),
                "functional_modules_ablation_enabled": (
                    self.functional_modules_ablation_enabled
                ),
                "functional_module_coupling_ablation_enabled": (
                    self.functional_module_coupling_ablation_enabled
                ),
                "functional_module_ablation_mask": (
                    self.functional_module_ablation_mask.astype(bool).tolist()
                ),
                "functional_module_lineage_output_ablation": {
                    str(module): sorted(int(lineage) for lineage in lineages)
                    for module, lineages in self.functional_module_lineage_output_ablation.items()
                },
                "functional_module_lineage_cost_ablation": {
                    str(module): sorted(int(lineage) for lineage in lineages)
                    for module, lineages in self.functional_module_lineage_cost_ablation.items()
                },
                "knowledge_policy_residual_schema": (
                    self.cfg.knowledge.policy_residual_schema
                    if self.cfg.knowledge.policy_influence_enabled
                    else None
                ),
                "knowledge_outcome_dense_log_enabled": (
                    self.cfg.knowledge.learning_enabled
                    and self.cfg.knowledge.log_outcome_updates
                ),
                "knowledge_policy_dense_log_enabled": (
                    self.cfg.knowledge.policy_influence_enabled
                    and self.cfg.knowledge.log_policy_contributions
                ),
                "knowledge_candidate_tracking": self.cfg.knowledge.candidate_tracking_enabled,
                "knowledge_candidate_schema": (
                    self.cfg.knowledge.candidate_schema
                    if self.cfg.knowledge.candidate_tracking_enabled
                    else None
                ),
                "knowledge_candidate_graph_schema": (
                    self.cfg.knowledge.candidate_graph_schema
                    if self.cfg.knowledge.candidate_tracking_enabled
                    else None
                ),
                "knowledge_candidate_diagnostic_only": True,
                "knowledge_candidate_subjecthood_truth_claimed": False,
                "knowledge_latent_policy_enabled": self.cfg.knowledge.latent_policy_enabled,
                "knowledge_latent_schema": (
                    self.cfg.knowledge.latent_schema
                    if self.cfg.knowledge.latent_policy_enabled
                    else None
                ),
                "knowledge_latent_router_schema": (
                    self.cfg.knowledge.latent_router_schema
                    if self.cfg.knowledge.latent_policy_enabled
                    else None
                ),
                "knowledge_latent_length_levels": (
                    list(self.cfg.knowledge.latent_length_levels)
                    if self.cfg.knowledge.latent_policy_enabled
                    else None
                ),
                "knowledge_latent_projection_width": (
                    self.cfg.knowledge.latent_router_hidden_width
                    if self.cfg.knowledge.latent_policy_enabled
                    else None
                ),
                "knowledge_latent_mlp_hidden_width": (
                    self.cfg.knowledge.latent_router_mlp_hidden_width
                    if self.cfg.knowledge.latent_router_schema == "quantized-mlp-latent-router-v1"
                    else None
                ),
                "knowledge_latent_activation": (
                    "integer-hard-tanh-v1"
                    if self.cfg.knowledge.latent_router_schema == "quantized-mlp-latent-router-v1"
                    else None
                ),
                "knowledge_latent_publish_quantized": (
                    self.cfg.knowledge.latent_policy_enabled
                ),
                "knowledge_routing_cost_enabled": self.cfg.knowledge.routing_cost_enabled,
                "knowledge_routing_cost_dense_log_enabled": (
                    self.cfg.knowledge.routing_cost_enabled
                    and self.cfg.knowledge.log_routing_costs
                ),
                "knowledge_routing_cost_schema": (
                    self.cfg.knowledge.routing_cost_schema
                    if self.cfg.knowledge.routing_cost_enabled
                    else None
                ),
                "knowledge_routing_budget_mode": (
                    self.cfg.knowledge.routing_budget_mode
                    if self.cfg.knowledge.routing_cost_enabled
                    else None
                ),
                "knowledge_routing_cost_commit_boundary": (
                    "policy-proposal preflight, energy commit before intent resolution"
                    if self.cfg.knowledge.routing_cost_enabled
                    else None
                ),
                "knowledge_working_memory_enabled": (
                    self.cfg.knowledge.working_memory_enabled
                ),
                "knowledge_working_memory_dense_log_enabled": (
                    self.cfg.knowledge.working_memory_enabled
                    and self.cfg.knowledge.log_working_memory_updates
                ),
                "knowledge_working_memory_schema": (
                    self.cfg.knowledge.working_memory_schema
                    if self.cfg.knowledge.working_memory_enabled else None
                ),
                "knowledge_working_memory_update_boundary": (
                    "post-outcome local state commit for next tick"
                    if self.cfg.knowledge.working_memory_enabled else None
                ),
                "knowledge_sparse_selection_enabled": (
                    self.cfg.knowledge.sparse_selection_enabled
                ),
                "knowledge_sparse_selection_dense_log_enabled": (
                    self.cfg.knowledge.sparse_selection_enabled
                    and self.cfg.knowledge.log_sparse_selection_events
                ),
                "knowledge_sparse_selection_schema": (
                    self.cfg.knowledge.sparse_selection_schema
                    if self.cfg.knowledge.sparse_selection_enabled else None
                ),
                "knowledge_sparse_selection_top_k": (
                    self.cfg.knowledge.sparse_selection_top_k
                    if self.cfg.knowledge.sparse_selection_enabled else None
                ),
                "knowledge_sparse_selection_authoritative_storage": False,
                "knowledge_sparse_selection_global_category_embedding": False,
                "knowledge_sparse_selection_softmax": False,
                "feature_constraints": list(ParametricPolicy.FEATURE_NAMES),
                "action_preferences_hardcoded": False,
                "strategy_gene_count": ParametricPolicy.STRATEGY_GENES,
                "knowledge_preference_gene_count": (
                    (
                        ParametricPolicy.KNOWLEDGE_OUTCOME_PREFERENCE_GENES
                        + 1
                        + ParametricPolicy.genome_size_for_config(self.cfg)
                        - ParametricPolicy.LATENT_ROUTER_START
                    )
                    if self.cfg.knowledge.latent_policy_enabled
                    else (
                        ParametricPolicy.KNOWLEDGE_OUTCOME_PREFERENCE_GENES + 1
                        if self.cfg.knowledge.policy_influence_enabled
                        else 0
                    )
                ),
                "genome_size": ParametricPolicy.genome_size_for_config(self.cfg),
                "initialization": "bounded stateless random generation",
                "transmission": "parental inheritance with configured mutation",
                "mutation_probability_per_gene": self.cfg.policy.mutation_probability,
                "mutation_std_conditional": self.cfg.policy.mutation_std,
                "morphology_gene_semantics": {
                    "sensor_quality": 0,
                    "movement_speed": 5,
                    "danger_direct_trace_mixture": (
                        6
                        if self.cfg.entities.danger_evidence_schema
                        == "inherited-direct-trace-mixture-v1"
                        else None
                    ),
                    "reproduction_investment": (
                        6
                        if inherited_reproduction_investment_enabled(self.cfg)
                        else None
                    ),
                    "resource_sensing_radius": (
                        7
                        if self.cfg.entities.resource_sensing_schema
                        in {
                            "inherited-discrete-gradient-radius-v1",
                            "inherited-affinity-routed-gradient-radius-v2",
                            "inherited-affinity-budgeted-gradient-radius-v3",
                            "inherited-demand-gated-affinity-budgeted-gradient-radius-v4",
                        }
                        else None
                    ),
                    "reserved_neutral": (
                        []
                        if self.cfg.entities.resource_sensing_schema
                        in {
                            "inherited-discrete-gradient-radius-v1",
                            "inherited-affinity-routed-gradient-radius-v2",
                            "inherited-affinity-budgeted-gradient-radius-v3",
                            "inherited-demand-gated-affinity-budgeted-gradient-radius-v4",
                        }
                        else [7]
                    ),
                },
                "knowledge_preference_gene_semantics": (
                    {
                        "knowledge_use_strength_index": (
                            ParametricPolicy.KNOWLEDGE_USE_STRENGTH_INDEX
                        ),
                        "latent_router_gene_start": ParametricPolicy.LATENT_ROUTER_START,
                        "latent_router_gene_stop": ParametricPolicy.genome_size_for_config(self.cfg),
                        "latent_router_schema": self.cfg.knowledge.latent_router_schema,
                        "latent_router_linear_shadow": (
                            self.cfg.knowledge.latent_router_schema
                            == "quantized-mlp-latent-router-v1"
                        ),
                        "latent_router_activation": (
                            "integer-hard-tanh-v1"
                            if self.cfg.knowledge.latent_router_schema
                            == "quantized-mlp-latent-router-v1"
                            else "identity"
                        ),
                        "latent_router_public_state": [
                            "energy_fraction", "integrity", "fertility", "scarcity"
                        ],
                        "latent_router_output": "action_logit_residual",
                        "latent_router_parameter_origin": "inherited genome",
                        "latent_content_origin": "world-internal content lineage and local outcomes",
                        "latent_external_training": False,
                        "latent_publication": "CPU-reference quantized integers with stable aggregation",
                        "sparse_selection_capacity_schema": (
                            self.cfg.knowledge.sparse_selection_capacity_schema
                            if self.cfg.knowledge.sparse_selection_enabled else None
                        ),
                        "sparse_selection_capacity_gene_index": (
                            ParametricPolicy.sparse_selection_capacity_gene_index(
                                self.cfg
                            )
                        ),
                        "sparse_selection_capacity_levels": (
                            list(self.cfg.knowledge.sparse_selection_capacity_levels)
                            if (
                                self.cfg.knowledge.sparse_selection_enabled
                                and self.cfg.knowledge.sparse_selection_capacity_schema
                                == "inherited-discrete-topk-v1"
                            )
                            else None
                        ),
                    }
                    if self.cfg.knowledge.latent_policy_enabled
                    else (
                        {
                            "outcome_preference_indices": list(
                                range(
                                    ParametricPolicy.KNOWLEDGE_PREFERENCE_START,
                                    ParametricPolicy.KNOWLEDGE_PREFERENCE_STOP,
                                )
                            ),
                            "knowledge_use_strength_index": (
                                ParametricPolicy.KNOWLEDGE_USE_STRENGTH_INDEX
                            ),
                            "outcome_order": [
                                "energy", "integrity", "material", "information",
                                "reproduction_opportunity",
                            ],
                        }
                        if self.cfg.knowledge.policy_influence_enabled
                        else None
                    )
                ),
            },
            "state_origins": {
                "memory": "observation-driven finite-memory dynamics",
                "generation": "parent generation plus one at committed birth",
                "candidate_subjects": "derived from bodies, lineages, and relation structure",
                "knowledge_candidate_subjects": (
                    "diagnostic-only content lineage, host distribution, cost, policy influence, "
                    "and boundary-flow observations; no independent actuator or control path"
                    if self.cfg.knowledge.candidate_tracking_enabled
                    else "disabled"
                ),
                "knowledge": (
                    (
                        (
                            (
                                "dynamic variable-length latent contents routed by inherited "
                                "quantized two-layer MLP parameters with an integer hard-tanh "
                                "through the public action-logit residual boundary"
                                if self.cfg.knowledge.latent_router_schema
                                == "quantized-mlp-latent-router-v1"
                                else "dynamic variable-length latent contents routed by inherited "
                                "quantized linear parameters through the public action-logit "
                                "residual boundary"
                            )
                            if self.cfg.knowledge.latent_policy_enabled
                            else "dynamic costly holder copies with local current-tick "
                            "context-action-outcome statistics with a separately versioned "
                            "sparse residual in K3"
                        )
                        if self.cfg.knowledge.policy_influence_enabled
                        else "context-action-outcome statistics; excluded from policy logits in K2"
                    )
                    if self.cfg.knowledge.learning_enabled
                    else (
                        "dynamic costly holder copies; excluded from policy logits in K1"
                        if self.cfg.knowledge.enabled
                        else "disabled"
                    )
                ),
                "mortality_trace": (
                    "local death-event deposits with public decay/diffusion; observed only through the existing danger boundary"
                    if self.cfg.environment.mortality_trace_schema != "disabled"
                    else "disabled"
                ),
                "environment_process": dict(
                    self.environment.environment_process_metadata
                ),
                "moving_hazard_schema": self.cfg.environment.moving_hazard_schema,
                "moving_hazard_sources": int(
                    self.cfg.environment.moving_hazard_source_count
                ),
                "danger_evidence_schema": self.cfg.entities.danger_evidence_schema,
                "danger_evidence_fixed_budget": True,
                "subject_shift": "measured from candidate/control provenance; never assigned as a state label",
            },
            "evolution_evaluation": {
                "period_ticks": self.cfg.run.evolution_evaluation_period,
                "feedback_to_world": False,
                "long_run_diagnostics_schema": (
                    self.cfg.run.long_run_diagnostics_schema
                    if self.cfg.run.long_run_diagnostics_enabled
                    else None
                ),
                "long_run_diagnostics_feedback_to_world": False,
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
                "group_label_schema": self.cfg.social.group_label_schema,
                "group_label_propagation_rounds": (
                    self.cfg.social.group_label_propagation_rounds
                ),
                "group_trust_threshold": self.cfg.social.trust_group_threshold,
                "group_min_members": self.cfg.social.group_min_members,
                "group_update_mode": self.cfg.social.group_update_mode,
                "group_update_period": self.cfg.social.group_update_period,
                "group_update_min_period": self.cfg.social.group_update_min_period,
                "group_update_max_period": self.cfg.social.group_update_max_period,
                "reproduction_capacity_arbitration": (
                    self.cfg.entities.reproduction_capacity_arbitration
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


    def _record_evolution_progress(
        self,
        actual_context_metrics: dict[str, object] | None = None,
    ) -> None:
        if self.gpu_runtime is None:
            resource_fields = np.asarray(self.environment.resources, dtype=np.float32)
            hazard_field = np.asarray(self.environment.hazard, dtype=np.float32)
        else:
            resource_fields = self.gpu_runtime.environment.to_numpy(
                self.gpu_runtime.environment.resources
            ).astype(np.float32, copy=False)
            hazard_field = self.gpu_runtime.environment.to_numpy(
                self.gpu_runtime.environment.hazard
            ).astype(np.float32, copy=False)
        if self.gpu_runtime is None:
            mortality_trace_field = np.asarray(
                self.environment.mortality_trace, dtype=np.float32
            )
        else:
            mortality_trace_field = self.gpu_runtime.environment.to_numpy(
                self.gpu_runtime.environment.mortality_trace
            ).astype(np.float32, copy=False)
        structure_environment_metrics: dict[str, object] = {}
        if self.subject_structure_diagnostics is not None:
            structure_environment_metrics.update(
                self.subject_structure_diagnostics.latest_metrics()
            )
        if self.group_function_diagnostics is not None:
            structure_environment_metrics.update(
                self.group_function_diagnostics.latest_metrics()
            )
        if self.reconnaissance_diagnostics is not None:
            structure_environment_metrics.update(
                self.reconnaissance_diagnostics.latest_metrics()
            )
        if self.environment_atlas_diagnostics is not None:
            structure_environment_metrics.update(
                self.environment_atlas_diagnostics.observe(
                    tick=self.tick,
                    resources=resource_fields,
                    hazard=hazard_field,
                    mortality_trace=mortality_trace_field,
                    alive=self.entities.alive,
                    x=self.entities.x,
                    y=self.entities.y,
                    lineage_ids=self.entities.lineage_id,
                    group_ids=self.social.group_id,
                )
            )
        environment_metrics: dict[str, object] = {
            "environment_schema": self.cfg.environment.schema,
            "mortality_trace_schema": self.cfg.environment.mortality_trace_schema,
            "environment_mortality_trace_mean": float(
                mortality_trace_field.mean(dtype=np.float64)
            ),
            "environment_mortality_trace_std": float(
                mortality_trace_field.std(dtype=np.float64)
            ),
            "environment_mortality_trace_max": float(
                mortality_trace_field.max(initial=0.0)
            ),
            "group_update_mode": self.cfg.social.group_update_mode,
            "group_refresh_ablation_enabled": int(
                self.group_refresh_ablation_enabled
            ),
            "group_update_count_total": int(self.social.group_update_count),
            "group_update_skipped_total": int(
                self.social.group_update_skipped_count
            ),
            "group_last_update_tick": int(self.social.last_group_update_tick),
            "group_labels_dirty": int(bool(self.social.group_labels_dirty)),
            "group_last_update_reason": self.social.last_group_update_reason,
            "group_last_dirty_reason": self.social.last_group_dirty_reason,
            "environment_resource_channel_mean": resource_fields.mean(
                axis=(1, 2), dtype=np.float64
            ).tolist(),
            "environment_resource_channel_std": resource_fields.std(
                axis=(1, 2), dtype=np.float64
            ).tolist(),
            "environment_resource_channel_min": resource_fields.min(
                axis=(1, 2)
            ).astype(np.float64).tolist(),
            "environment_resource_channel_max": resource_fields.max(
                axis=(1, 2)
            ).astype(np.float64).tolist(),
            "environment_hazard_mean": float(
                hazard_field.mean(dtype=np.float64)
            ),
            "environment_hazard_std": float(
                hazard_field.std(dtype=np.float64)
            ),
            **structure_environment_metrics,
            **resource_affinity_diagnostics(
                self.entities.alive, self.entities.genotype, self.cfg
            ),
            **danger_evidence_diagnostics(
                self.entities.alive, self.entities.genotype, self.cfg
            ),
        }
        if self.cfg.differentiation.enabled:
            capacity_phenotype = self.entities.capacity_phenotype()
            environment_metrics.update(
                capacity_diagnostics(
                    capacity_phenotype,
                    alive=self.entities.alive,
                    config=self.cfg.differentiation,
                )
            )
            knowledge_bytes_used = np.zeros(
                self.entities.alive.size, dtype=np.int64
            )
            for entity_index in np.flatnonzero(self.entities.alive):
                knowledge_bytes_used[entity_index] = self.knowledge.arena.holder_bytes(
                    int(self.entities.primary_subject_id[entity_index])
                )
            environment_metrics.update(
                capacity_use_diagnostics(
                    capacity_phenotype,
                    alive=self.entities.alive,
                    working_memory_q=self.entities.working_memory_q,
                    relation_targets=self.social.target,
                    knowledge_bytes_used=knowledge_bytes_used,
                )
            )
        if orthogonal_environment_enabled(self.cfg):
            diversity = resource_field_diversity_metrics(
                resource_fields, self.cfg.environment.resource_capacity
            )
            environment_metrics.update(
                {
                    "environment_resource_effective_dimensions": diversity[
                        "resource_effective_dimensions"
                    ],
                    "environment_resource_channel_mean_abs_correlation": diversity[
                        "resource_channel_mean_abs_correlation"
                    ],
                    "environment_resource_channel_max_abs_correlation": diversity[
                        "resource_channel_max_abs_correlation"
                    ],
                    "environment_resource_channel_correlation": diversity[
                        "resource_channel_correlation"
                    ],
                }
            )
        if (
            self.local_stress_diagnostics is not None
            and self.local_stress_diagnostics.culture_enabled
        ):
            root_entities, root_ids = self.knowledge.active_transferred_root_presence(
                alive=self.entities.alive,
                primary_subject_ids=self.entities.primary_subject_id,
            )
            self.local_stress_diagnostics.observe_transferred_roots(
                entity_indices=root_entities,
                root_ids=root_ids,
                x=self.entities.x,
                y=self.entities.y,
            )
        spatial_stress_metrics = (
            self.local_stress_diagnostics.consume_window()
            if self.local_stress_diagnostics is not None
            else None
        )
        self.evolution_progress.record(
            tick=self.tick,
            scheduled=True,
            alive=self.entities.alive,
            stable_ids=self.entities.entity_id,
            lineage_ids=self.entities.lineage_id,
            group_ids=self.social.group_id,
            generation=self.entities.generation,
            genotype=self.entities.genotype,
            births_total=self.total_births,
            deaths_total=self.total_deaths,
            death_cause_counts_total=self.total_death_cause_counts,
            action_counts=self.action_counts,
            benefit_flow_energy_total=self.benefit_flow_energy_total,
            lagged_benefit_flow_energy_total=(
                self.lagged_benefit_boundary.flow_energy_total
            ),
            lagged_benefit_boundary_snapshot_tick=(
                self.lagged_benefit_boundary.snapshot_tick
            ),
            shared_energy_total=self.total_shared_energy,
            harvested_resources_total=self.total_harvested_resources,
            requested_harvest_resources_total=self.total_requested_harvest_resources,
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
            environment_metrics=environment_metrics,
            spatial_stress_metrics=spatial_stress_metrics,
            knowledge_metrics=(
                self.knowledge.long_run_diagnostics(
                    alive=self.entities.alive,
                    primary_subject_ids=self.entities.primary_subject_id,
                    lineage_ids=self.entities.lineage_id,
                    group_ids=self.social.group_id,
                )
                if self.cfg.run.long_run_diagnostics_enabled
                else None
            ),
        )


    def metric_row(
        self,
        stats: StepStats,
        elapsed: float,
        *,
        wall_elapsed: float = 0.0,
        window_seconds: float = 0.0,
        window_ticks: int = 1,
    ) -> dict[str, object]:
        ent = self.entities
        active = np.flatnonzero(ent.alive)
        alive_count = active.size
        if alive_count:
            mean_energy = float(ent.energy[active].mean())
            mean_integrity = float(ent.integrity[active].mean())
            mean_age = float(ent.age[active].mean())
            living_generation = np.asarray(ent.generation[active], dtype=np.uint32)
            mean_generation = float(living_generation.mean())
            max_generation = int(living_generation.max())
            founder_alive_count = int(np.count_nonzero(living_generation == 0))
            descendant_alive_count = int(alive_count - founder_alive_count)
            founder_alive_fraction = float(founder_alive_count / alive_count)
            descendant_alive_fraction = float(descendant_alive_count / alive_count)
            mean_oxygenation = float(ent.oxygenation[active].mean())
            mean_tissue_condition = float(ent.tissue_condition[active].mean())
            mean_structure_condition = float(ent.structure_condition[active].mean())
            mean_metabolic_fatigue = float(ent.metabolic_fatigue[active].mean())
            mean_mobilization_messenger = float(ent.mobilization_messenger[active].mean())
            mean_maintenance_messenger = float(ent.maintenance_messenger[active].mean())
            mean_messenger_precursor = float(ent.messenger_precursor[active].mean())
            mean_physiology_sensor_multiplier = float(
                ent.physiology_sensor_multiplier[active].mean()
            )
            social_dependency = float(
                np.mean(
                    ent.shared_energy_received_total[active]
                    / np.maximum(
                        ent.shared_energy_received_total[active] + ent.harvested_energy_total[active], 1e-6
                    )
                )
            )
            lineage_count = int(np.unique(ent.lineage_id[active]).size)
            reproduction_investments = np.asarray(
                reproduction_investment(ent.genotype[active], self.cfg),
                dtype=np.float64,
            )
            reproduction_requirements = np.asarray(
                reproduction_energy_requirement(ent.genotype[active], self.cfg),
                dtype=np.float64,
            )
            reproduction_investment_mean = float(reproduction_investments.mean())
            reproduction_investment_std = float(reproduction_investments.std())
            reproduction_requirement_mean = float(reproduction_requirements.mean())
            reproduction_requirement_std = float(reproduction_requirements.std())
            grouped_fraction = float(np.mean(self.social.group_id[active] != 0))
            strategy_genome = ent.genotype[
                active, ParametricPolicy.STRATEGY_START : ParametricPolicy.STRATEGY_STOP
            ]
            strategy_mean_abs_weight = float(
                np.mean(np.abs(strategy_genome), dtype=np.float64)
            )
            raw_strategy_gene_diversity = float(
                np.mean(np.std(strategy_genome, axis=0, dtype=np.float64))
            )
            if self.cfg.knowledge.policy_influence_enabled:
                knowledge_preferences = ParametricPolicy.outcome_preferences_from_genotype(
                    ent.genotype[active]
                )
                knowledge_preference_mean = knowledge_preferences.mean(
                    axis=0, dtype=np.float64
                )
                knowledge_preference_diversity = knowledge_preferences.std(
                    axis=0, dtype=np.float64
                )
                knowledge_use_strength_mean = float(
                    ParametricPolicy.knowledge_use_strength_from_genotype(
                        ent.genotype[active]
                    ).mean(dtype=np.float64)
                )
            else:
                knowledge_preference_mean = np.zeros(5, dtype=np.float64)
                knowledge_preference_diversity = np.zeros(5, dtype=np.float64)
                knowledge_use_strength_mean = 0.0
        else:
            mean_energy = mean_integrity = mean_age = social_dependency = grouped_fraction = 0.0
            mean_generation = 0.0
            max_generation = 0
            founder_alive_count = descendant_alive_count = 0
            founder_alive_fraction = descendant_alive_fraction = 0.0
            mean_oxygenation = mean_tissue_condition = mean_structure_condition = 0.0
            mean_metabolic_fatigue = 0.0
            mean_mobilization_messenger = 0.0
            mean_maintenance_messenger = 0.0
            mean_messenger_precursor = 0.0
            mean_physiology_sensor_multiplier = 0.0
            lineage_count = 0
            strategy_mean_abs_weight = 0.0
            raw_strategy_gene_diversity = 0.0
            knowledge_preference_mean = np.zeros(5, dtype=np.float64)
            knowledge_preference_diversity = np.zeros(5, dtype=np.float64)
            knowledge_use_strength_mean = 0.0
            reproduction_investment_mean = 0.0
            reproduction_investment_std = 0.0
            reproduction_requirement_mean = 0.0
            reproduction_requirement_std = 0.0
        interest_feedback = self.social.interest_feedback_diagnostics(ent.alive)
        if self.gpu_runtime is None:
            physiology_metric_fields = (
                self.environment.oxygen,
                self.environment.terrain,
                self.environment.wear,
            )
        else:
            physiology_metric_fields = self.gpu_runtime.physiology_fields_to_host()
        physiology_environment_metrics = physiology_field_metrics(
            *physiology_metric_fields
        )
        signal_openness_field = (
            self.environment.signal_openness
            if self.gpu_runtime is None
            else self.gpu_runtime.transport_fields_to_host()[1]
        )
        signal_medium_environment_metrics = signal_medium_metrics(
            signal_openness_field, physiology_metric_fields[1]
        )
        physiology_genetic_metrics = physiology_diagnostics(
            ent.genotype,
            ent.alive,
            self.cfg,
            gene_start=ParametricPolicy.physiology_gene_start(self.cfg),
        )
        resource_metabolism_metrics = resource_metabolism_diagnostics(
            ent,
            self.cfg,
            gene_start=ParametricPolicy.physiology_gene_start(self.cfg),
            neutralize_conversion_allocation=(
                self.resource_conversion_allocation_ablation_enabled
            ),
            neutralize_store_allocation=(
                self.resource_store_allocation_ablation_enabled
            ),
        )
        affinity_metrics = resource_affinity_diagnostics(
            ent.alive, ent.genotype, self.cfg
        )
        danger_evidence_metrics = danger_evidence_diagnostics(
            ent.alive, ent.genotype, self.cfg
        )
        sensing_active = np.flatnonzero(ent.alive).astype(np.int32)
        sensing_storage_room = storage_room_fraction(
            ent,
            sensing_active,
            self.cfg,
            genotype=ent.genotype[sensing_active],
            gene_start=ParametricPolicy.physiology_gene_start(self.cfg),
            neutralize_store_allocation=(
                self.resource_store_allocation_ablation_enabled
            ),
        )
        resource_sensing_metrics = resource_sensing_diagnostics(
            ent.alive,
            ent.genotype,
            self.cfg,
            resource_affinity_q=resource_affinity_quantized(ent.genotype, self.cfg),
            storage_room_fraction=sensing_storage_room,
        )
        capacity_metrics = (
            capacity_diagnostics(
                ent.capacity_phenotype(),
                alive=ent.alive,
                config=self.cfg.differentiation,
            )
            if self.cfg.differentiation.enabled
            else None
        )
        if self.gpu_runtime is None:
            metric_resource_fields = np.asarray(
                self.environment.resources, dtype=np.float32
            )
            metric_hazard_field = np.asarray(
                self.environment.hazard, dtype=np.float32
            )
            metric_mortality_trace = np.asarray(
                self.environment.mortality_trace, dtype=np.float32
            )
        else:
            metric_resource_fields = self.gpu_runtime.environment.to_numpy(
                self.gpu_runtime.environment.resources
            ).astype(np.float32, copy=False)
            metric_hazard_field = self.gpu_runtime.environment.to_numpy(
                self.gpu_runtime.environment.hazard
            ).astype(np.float32, copy=False)
            metric_mortality_trace = self.gpu_runtime.environment.to_numpy(
                self.gpu_runtime.environment.mortality_trace
            ).astype(np.float32, copy=False)
        resource_field_mean = metric_resource_fields.mean(
            axis=(1, 2), dtype=np.float64
        )
        resource_field_std = metric_resource_fields.std(
            axis=(1, 2), dtype=np.float64
        )
        resource_diversity = (
            resource_field_diversity_metrics(
                metric_resource_fields, self.cfg.environment.resource_capacity
            )
            if orthogonal_environment_enabled(self.cfg)
            else None
        )
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
        row: dict[str, object] = {
            "tick": self.tick,
            "reporting_snapshot_schema": "authoritative-reporting-snapshot-v1",
            "reporting_state_tick": int(
                getattr(self, "reporting_state_tick", self.tick)
            ),
            "reporting_state_source": str(
                getattr(self, "reporting_state_source", "unmaterialized")
            ),
            "alive": alive_count,
            "births_step": stats.births,
            "deaths_step": stats.deaths,
            "births_total": self.total_births,
            "deaths_total": self.total_deaths,
            "death_cause_code_counts_step": stats.death_cause_counts.tolist(),
            "death_cause_code_counts_total": self.total_death_cause_counts.tolist(),
            "death_energy_depleted_step": int(
                stats.death_cause_counts[1] + stats.death_cause_counts[3]
                + stats.death_cause_counts[5] + stats.death_cause_counts[7]
            ),
            "death_integrity_depleted_step": int(
                stats.death_cause_counts[2] + stats.death_cause_counts[3]
                + stats.death_cause_counts[6] + stats.death_cause_counts[7]
            ),
            "death_max_age_step": int(
                stats.death_cause_counts[4] + stats.death_cause_counts[5]
                + stats.death_cause_counts[6] + stats.death_cause_counts[7]
            ),
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
            "reproduction_schema": self.cfg.entities.reproduction_schema,
            "reproduction_investment_enabled": bool(
                conservative_reproduction_investment_enabled(self.cfg)
            ),
            "reproduction_investment_inherited": bool(
                inherited_reproduction_investment_enabled(self.cfg)
            ),
            "offspring_endowment_ablation_enabled": bool(
                self.offspring_endowment_ablation_enabled
            ),
            "reproduction_investment_mean": reproduction_investment_mean,
            "reproduction_investment_std": reproduction_investment_std,
            "reproduction_energy_requirement_mean": reproduction_requirement_mean,
            "reproduction_energy_requirement_std": reproduction_requirement_std,
            "mean_energy": mean_energy,
            "mean_integrity": mean_integrity,
            "mean_oxygenation": mean_oxygenation,
            "mean_tissue_condition": mean_tissue_condition,
            "mean_structure_condition": mean_structure_condition,
            "mean_metabolic_fatigue": mean_metabolic_fatigue,
            "mean_mobilization_messenger": mean_mobilization_messenger,
            "mean_maintenance_messenger": mean_maintenance_messenger,
            "mean_messenger_precursor": mean_messenger_precursor,
            "mean_physiology_sensor_multiplier": mean_physiology_sensor_multiplier,
            "mean_age": mean_age,
            "mean_generation": mean_generation,
            "max_generation": max_generation,
            "founder_alive_count": founder_alive_count,
            "descendant_alive_count": descendant_alive_count,
            "founder_alive_fraction": founder_alive_fraction,
            "descendant_alive_fraction": descendant_alive_fraction,
            "cumulative_births_per_initial": float(
                self.total_births / max(int(self.cfg.world.initial_entities), 1)
            ),
            "living_descendants_per_initial": float(
                descendant_alive_count / max(int(self.cfg.world.initial_entities), 1)
            ),
            "lineages": lineage_count,
            "groups": stats.group_count,
            "mean_group_size": stats.mean_group_size,
            "group_updated": stats.group_updated,
            "group_update_count_total": int(self.social.group_update_count),
            "group_update_skipped_total": int(
                self.social.group_update_skipped_count
            ),
            "group_labels_dirty": int(bool(self.social.group_labels_dirty)),
            "group_last_update_tick": int(self.social.last_group_update_tick),
            "group_update_mode": self.cfg.social.group_update_mode,
            "group_refresh_ablation_enabled": int(
                self.group_refresh_ablation_enabled
            ),
            "group_last_update_reason": self.social.last_group_update_reason,
            "group_last_dirty_reason": self.social.last_group_dirty_reason,
            "grouped_fraction": grouped_fraction,
            "social_dependency_proxy": social_dependency,
            **interest_feedback,
            "strategy_mean_abs_weight": strategy_mean_abs_weight,
            "raw_strategy_gene_diversity": raw_strategy_gene_diversity,
            "knowledge_outcome_preference_energy_mean": float(knowledge_preference_mean[0]),
            "knowledge_outcome_preference_integrity_mean": float(knowledge_preference_mean[1]),
            "knowledge_outcome_preference_material_mean": float(knowledge_preference_mean[2]),
            "knowledge_outcome_preference_information_mean": float(knowledge_preference_mean[3]),
            "knowledge_outcome_preference_reproduction_mean": float(knowledge_preference_mean[4]),
            "knowledge_outcome_preference_energy_diversity": float(knowledge_preference_diversity[0]),
            "knowledge_outcome_preference_integrity_diversity": float(knowledge_preference_diversity[1]),
            "knowledge_outcome_preference_material_diversity": float(knowledge_preference_diversity[2]),
            "knowledge_outcome_preference_information_diversity": float(knowledge_preference_diversity[3]),
            "knowledge_outcome_preference_reproduction_diversity": float(knowledge_preference_diversity[4]),
            "knowledge_use_strength_mean": knowledge_use_strength_mean,
            "move_social_fraction": stats.move_social_fraction,
            "environment_schema": self.cfg.environment.schema,
            "resource_affinity_schema": self.cfg.entities.resource_affinity_schema,
            "harvest_allocation_schema": self.cfg.entities.harvest_allocation_schema,
            "resource_processing_schema": self.cfg.environment.resource_processing_schema,
            "resource_processing_support_amplitude": self.cfg.environment.resource_processing_support_amplitude,
            "resource_processing_support_orientation_reversed": int(
                self.environment.resource_processing_support_reversed
            ),
            "resource_processing_energy_per_unit": list(
                self.cfg.physiology.resource_processing_energy_per_unit
            ),
            "capacity_ablation_enabled": int(self.capacity_ablation_enabled),
            "capacity_effective_schema": (
                "fixed-midpoint-elastic-capacities-ablation-v1"
                if self.capacity_ablation_enabled
                else self.cfg.differentiation.schema
            ),
            "resource_affinity_ablation_enabled": int(
                self.resource_affinity_ablation_enabled
            ),
            "resource_processing_support_ablation_enabled": int(
                self.resource_processing_support_ablation_enabled
            ),
            "functional_modules_schema": self.cfg.functional_modules.schema,
            "functional_modules_ablation_enabled": int(
                self.functional_modules_ablation_enabled
            ),
            "functional_module_coupling_ablation_enabled": int(
                self.functional_module_coupling_ablation_enabled
            ),
            "functional_module_embodied_output_ablation_enabled": int(
                self.functional_module_embodied_output_ablation_enabled
            ),
            "functional_module_physiology_output_ablation_enabled": int(
                self.functional_module_physiology_output_ablation_enabled
            ),
            "functional_module_changed_entity_fraction": float(
                self.last_functional_module_changed_entity_fraction
            ),
            "functional_module_residual_effective_dimensions": float(
                self.last_functional_module_residual_effective_dimensions
            ),
            "functional_physiology_output_changed_entity_fraction": float(
                self.last_functional_physiology_output_changed_entity_fraction
            ),
            "functional_physiology_output_effective_dimensions": float(
                self.last_functional_physiology_output_effective_dimensions
            ),
            "physiology_messenger_receptor_blockade_enabled": int(
                self.physiology_messenger_receptor_blockade_enabled
            ),
            "physiology_state_clamp_count": int(len(self.physiology_state_clamps)),
            "physiology_state_clamps": {
                str(name): float(value)
                for name, value in sorted(self.physiology_state_clamps.items())
            },
            "physiology_schema": self.cfg.physiology.schema,
            "physiology_environment_schema": (
                self.cfg.environment.physiology_environment_schema
            ),
            "physiology_environment_effective_dimensions": float(
                physiology_environment_metrics.effective_dimensions
            ),
            "physiology_environment_correlations": (
                physiology_environment_metrics.correlations
            ),
            "physiology_environment_means": physiology_environment_metrics.means,
            "physiology_environment_standard_deviations": (
                physiology_environment_metrics.standard_deviations
            ),
            "signal_medium_schema": self.cfg.environment.signal_medium_schema,
            "signal_propagation_schema": (
                self.cfg.environment.signal_propagation_schema
            ),
            "direct_message_propagation_schema": (
                self.cfg.information.direct_message_propagation_schema
            ),
            **signal_medium_environment_metrics,
            "physiology_genetic_effective_dimensions": float(
                physiology_genetic_metrics["effective_dimensions"]
            ),
            "physiology_genetic_trait_names": physiology_genetic_metrics["gene_names"],
            "physiology_genetic_trait_means": physiology_genetic_metrics["means"],
            "physiology_genetic_trait_standard_deviations": (
                physiology_genetic_metrics["standard_deviations"]
            ),
            **(
                resource_metabolism_metrics
                if resource_metabolism_enabled(self.cfg)
                else {}
            ),
            **(
                {
                    "resource_stored_total": self.total_resource_stored.tolist(),
                    "resource_store_overflow_total": self.total_resource_store_overflow.tolist(),
                    **(
                        {
                            "resource_intake_capacity_rejected_total": self.total_resource_intake_capacity_rejected.tolist()
                        }
                        if storage_constrained_intake_enabled(self.cfg)
                        else {}
                    ),
                    **(
                        {
                            "resource_processing_requested_total": self.total_resource_processing_requested.tolist(),
                            "resource_processing_supported_total": self.total_resource_processing_supported.tolist(),
                            "resource_processing_support_limited_total": self.total_resource_processing_support_limited.tolist(),
                            "resource_processing_support_accelerated_total": self.total_resource_processing_support_accelerated.tolist(),
                            "resource_processing_energy_rejected_total": self.total_resource_processing_energy_rejected.tolist(),
                            "resource_processing_support_absolute_deviation_total": self.total_resource_processing_support_absolute_deviation.tolist(),
                            "resource_processing_support_weighted_mean": np.divide(
                                self.total_resource_processing_support_weighted_sum,
                                self.total_resource_processing_support_weight,
                                out=np.ones(4, dtype=np.float64),
                                where=self.total_resource_processing_support_weight > 0.0,
                            ).tolist(),
                            "resource_processing_energy_cost_total": float(
                                self.total_resource_processing_energy_cost
                            ),
                        }
                        if spatial_processing_enabled(self.cfg)
                        else {}
                    ),
                    "resource_converted_total": self.total_resource_converted.tolist(),
                    "resource_store_decay_total": self.total_resource_store_decay.tolist(),
                    "resource_store_death_loss_total": self.total_resource_store_death_loss.tolist(),
                    "resource_body_realized_total": self.total_resource_body_realized.tolist(),
                    **(
                        {
                            "resource_residue_deposited_total": self.total_resource_residue_deposited.tolist(),
                            "resource_residue_released_total": self.total_resource_residue_released.tolist(),
                            **resource_recycling_diagnostics(self.environment),
                        }
                        if external_resource_recycling_enabled(self.cfg)
                        else {}
                    ),
                }
                if resource_metabolism_enabled(self.cfg)
                else {}
            ),
            "functional_module_ablation_mask": (
                self.functional_module_ablation_mask.astype(bool).tolist()
            ),
            "functional_module_lineage_output_ablation_count": int(
                sum(
                    len(lineages)
                    for lineages in self.functional_module_lineage_output_ablation.values()
                )
            ),
            "functional_module_lineage_cost_ablation_count": int(
                sum(
                    len(lineages)
                    for lineages in self.functional_module_lineage_cost_ablation.values()
                )
            ),
            "functional_module_maintenance_energy_step": (
                stats.functional_module_maintenance_energy
            ),
            "functional_module_development_energy_step": (
                stats.functional_module_development_energy
            ),
            "physiology_capacity_maintenance_energy_step": (
                stats.physiology_capacity_maintenance_energy
            ),
            "physiology_capacity_development_energy_step": (
                stats.physiology_capacity_development_energy
            ),
            "functional_module_movement_energy_delta_step": (
                stats.functional_module_movement_energy
            ),
            "functional_module_signal_energy_delta_step": (
                stats.functional_module_signal_energy
            ),
            "functional_module_repair_energy_step": (
                stats.functional_module_repair_energy
            ),
            "functional_module_repair_material_step": (
                stats.functional_module_repair_material
            ),
            "functional_module_repair_integrity_step": (
                stats.functional_module_repair_integrity
            ),
            "functional_module_movement_energy_delta_total": (
                self.total_functional_module_movement_energy_delta
            ),
            "functional_module_signal_energy_delta_total": (
                self.total_functional_module_signal_energy_delta
            ),
            "functional_module_repair_energy_total": (
                self.total_functional_module_repair_energy
            ),
            "functional_module_repair_material_total": (
                self.total_functional_module_repair_material
            ),
            "functional_module_repair_integrity_total": (
                self.total_functional_module_repair_integrity
            ),
            **{
                f"physiology_{name}_step": float(getattr(stats, f"physiology_{name}"))
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
            **{
                f"physiology_{name}_total": float(getattr(self, f"total_physiology_{name}"))
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
            "danger_evidence_ablation_enabled": int(
                self.danger_evidence_ablation_enabled
            ),
            "resource_affinity_effective_schema": (
                "uniform-four-resource-affinity-ablation-v1"
                if self.resource_affinity_ablation_enabled
                else self.cfg.entities.resource_affinity_schema
            ),
            "knowledge_policy_ablation_enabled": int(
                self.knowledge_policy_ablation_enabled
            ),
            "knowledge_policy_effective_enabled": int(
                self.cfg.knowledge.policy_influence_enabled
                and not self.knowledge_policy_ablation_enabled
            ),
            "knowledge_transfer_ablation_enabled": int(
                self.knowledge_transfer_ablation_enabled
            ),
            "knowledge_transfer_effective_enabled": int(
                self.cfg.knowledge.enabled
                and not self.knowledge_transfer_ablation_enabled
            ),
            "active_morphology_gene_count": int(
                affinity_metrics["active_morphology_gene_count"]
            ),
            "active_morphology_effective_dimensions": float(
                affinity_metrics["active_morphology_effective_dimensions"]
            ),
            "resource_affinity_specialization_mean": float(
                affinity_metrics["resource_affinity_specialization_mean"]
            ),
            "resource_affinity_effective_dimensions": float(
                affinity_metrics["resource_affinity_effective_dimensions"]
            ),
            "resource_affinity_0_mean": float(affinity_metrics["resource_affinity_mean"][0]),
            "resource_affinity_1_mean": float(affinity_metrics["resource_affinity_mean"][1]),
            "resource_affinity_2_mean": float(affinity_metrics["resource_affinity_mean"][2]),
            "resource_affinity_3_mean": float(affinity_metrics["resource_affinity_mean"][3]),
            "resource_affinity_0_diversity": float(affinity_metrics["resource_affinity_std"][0]),
            "resource_affinity_1_diversity": float(affinity_metrics["resource_affinity_std"][1]),
            "resource_affinity_2_diversity": float(affinity_metrics["resource_affinity_std"][2]),
            "resource_affinity_3_diversity": float(affinity_metrics["resource_affinity_std"][3]),
            "danger_evidence_schema": danger_evidence_metrics["danger_evidence_schema"],
            "danger_direct_weight_mean": float(danger_evidence_metrics["danger_direct_weight_mean"]),
            "danger_direct_weight_std": float(danger_evidence_metrics["danger_direct_weight_std"]),
            "danger_trace_weight_mean": float(danger_evidence_metrics["danger_trace_weight_mean"]),
            "danger_trace_weight_std": float(danger_evidence_metrics["danger_trace_weight_std"]),
            "danger_evidence_effective_dimensions": float(danger_evidence_metrics["danger_evidence_effective_dimensions"]),
            "resource_sensing_schema": resource_sensing_metrics["resource_sensing_schema"],
            "resource_sensing_radius_mean": float(resource_sensing_metrics["resource_sensing_radius_mean"]),
            "resource_sensing_radius_std": float(resource_sensing_metrics["resource_sensing_radius_std"]),
            "resource_sensing_radius_min": int(resource_sensing_metrics["resource_sensing_radius_min"]),
            "resource_sensing_radius_max": int(resource_sensing_metrics["resource_sensing_radius_max"]),
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
            "resource_recycling_effective_enabled": bool(
                external_resource_recycling_enabled(self.cfg)
                and not self.resource_recycling_ablation_enabled
            ),
            "resource_sensing_effective_radius_mean": (
                1.0
                if self.resource_sensing_ablation_enabled
                else float(resource_sensing_metrics["resource_sensing_channel_radius_mean"])
            ),
            "resource_sensing_channel_0_radius_mean": float(
                resource_sensing_metrics["resource_sensing_channel_radius_means"][0]
            ),
            "resource_sensing_channel_1_radius_mean": float(
                resource_sensing_metrics["resource_sensing_channel_radius_means"][1]
            ),
            "resource_sensing_channel_2_radius_mean": float(
                resource_sensing_metrics["resource_sensing_channel_radius_means"][2]
            ),
            "resource_sensing_channel_3_radius_mean": float(
                resource_sensing_metrics["resource_sensing_channel_radius_means"][3]
            ),
            "resource_sensing_channel_0_extended_fraction": float(
                resource_sensing_metrics["resource_sensing_extended_channel_fractions"][0]
            ),
            "resource_sensing_channel_1_extended_fraction": float(
                resource_sensing_metrics["resource_sensing_extended_channel_fractions"][1]
            ),
            "resource_sensing_channel_2_extended_fraction": float(
                resource_sensing_metrics["resource_sensing_extended_channel_fractions"][2]
            ),
            "resource_sensing_channel_3_extended_fraction": float(
                resource_sensing_metrics["resource_sensing_extended_channel_fractions"][3]
            ),
            "resource_sensing_extended_channel_count_mean": (
                0.0
                if self.resource_sensing_ablation_enabled
                else float(
                    resource_sensing_metrics[
                        "resource_sensing_extended_channel_count_mean"
                    ]
                )
            ),
            "resource_sensing_allocated_extra_radius_mean": (
                0.0
                if self.resource_sensing_ablation_enabled
                else float(
                    resource_sensing_metrics[
                        "resource_sensing_allocated_extra_radius_mean"
                    ]
                )
            ),
            "resource_sensing_open_storage_channel_count_mean": float(
                resource_sensing_metrics[
                    "resource_sensing_open_storage_channel_count_mean"
                ]
            ),
            "resource_sensing_demand_fallback_fraction": float(
                resource_sensing_metrics[
                    "resource_sensing_demand_fallback_fraction"
                ]
            ),
            "environment_process_schema": str(
                self.environment.environment_process_metadata["schema"]
            ),
            "environment_process_origin": str(
                self.environment.environment_process_metadata["origin"]
            ),
            "environment_process_mechanism_class": str(
                self.environment.environment_process_metadata["mechanism_class"]
            ),
            "environment_process_interpretation": str(
                self.environment.environment_process_metadata["interpretation"]
            ),
            "moving_hazard_schema": self.cfg.environment.moving_hazard_schema,
            "moving_hazard_source_count": int(self.cfg.environment.moving_hazard_source_count),
            "environment_resource_0_mean": float(resource_field_mean[0]),
            "environment_resource_1_mean": float(resource_field_mean[1]),
            "environment_resource_2_mean": float(resource_field_mean[2]),
            "environment_resource_3_mean": float(resource_field_mean[3]),
            "environment_resource_0_std": float(resource_field_std[0]),
            "environment_resource_1_std": float(resource_field_std[1]),
            "environment_resource_2_std": float(resource_field_std[2]),
            "environment_resource_3_std": float(resource_field_std[3]),
            "environment_hazard_mean": float(metric_hazard_field.mean(dtype=np.float64)),
            "environment_hazard_std": float(metric_hazard_field.std(dtype=np.float64)),
            "environment_mortality_trace_mean": float(
                metric_mortality_trace.mean(dtype=np.float64)
            ),
            "environment_mortality_trace_std": float(
                metric_mortality_trace.std(dtype=np.float64)
            ),
            "environment_mortality_trace_max": float(
                metric_mortality_trace.max(initial=0.0)
            ),
            "harvested_energy_step": stats.harvested_energy,
            "harvested_resource_0_step": float(stats.harvested_resources[0]),
            "harvested_resource_1_step": float(stats.harvested_resources[1]),
            "harvested_resource_2_step": float(stats.harvested_resources[2]),
            "harvested_resource_3_step": float(stats.harvested_resources[3]),
            "harvested_resource_0_total": float(self.total_harvested_resources[0]),
            "harvested_resource_1_total": float(self.total_harvested_resources[1]),
            "harvested_resource_2_total": float(self.total_harvested_resources[2]),
            "harvested_resource_3_total": float(self.total_harvested_resources[3]),
            "requested_harvest_resource_0_step": float(stats.requested_harvest_resources[0]),
            "requested_harvest_resource_1_step": float(stats.requested_harvest_resources[1]),
            "requested_harvest_resource_2_step": float(stats.requested_harvest_resources[2]),
            "requested_harvest_resource_3_step": float(stats.requested_harvest_resources[3]),
            "requested_harvest_resource_0_total": float(self.total_requested_harvest_resources[0]),
            "requested_harvest_resource_1_total": float(self.total_requested_harvest_resources[1]),
            "requested_harvest_resource_2_total": float(self.total_requested_harvest_resources[2]),
            "requested_harvest_resource_3_total": float(self.total_requested_harvest_resources[3]),
            **(
                {
                    **{
                        f"resource_stored_{index}_step": float(stats.resource_stored[index])
                        for index in range(4)
                    },
                    **{
                        f"resource_stored_{index}_total": float(self.total_resource_stored[index])
                        for index in range(4)
                    },
                    **{
                        f"resource_store_overflow_{index}_step": float(stats.resource_store_overflow[index])
                        for index in range(4)
                    },
                    **{
                        f"resource_store_overflow_{index}_total": float(self.total_resource_store_overflow[index])
                        for index in range(4)
                    },
                    **(
                        {
                            **{
                                f"resource_intake_capacity_rejected_{index}_step": float(
                                    stats.resource_intake_capacity_rejected[index]
                                )
                                for index in range(4)
                            },
                            **{
                                f"resource_intake_capacity_rejected_{index}_total": float(
                                    self.total_resource_intake_capacity_rejected[index]
                                )
                                for index in range(4)
                            },
                            **{
                                f"unconstrained_harvest_request_{index}_step": float(
                                    stats.unconstrained_harvest_requests[index]
                                )
                                for index in range(4)
                            },
                        }
                        if storage_constrained_intake_enabled(self.cfg)
                        else {}
                    ),
                    **(
                        {
                            **{
                                f"resource_processing_requested_{index}_step": float(
                                    stats.resource_processing_requested[index]
                                )
                                for index in range(4)
                            },
                            **{
                                f"resource_processing_requested_{index}_total": float(
                                    self.total_resource_processing_requested[index]
                                )
                                for index in range(4)
                            },
                            **{
                                f"resource_processing_supported_{index}_step": float(
                                    stats.resource_processing_supported[index]
                                )
                                for index in range(4)
                            },
                            **{
                                f"resource_processing_supported_{index}_total": float(
                                    self.total_resource_processing_supported[index]
                                )
                                for index in range(4)
                            },
                            **{
                                f"resource_processing_support_limited_{index}_step": float(
                                    stats.resource_processing_support_limited[index]
                                )
                                for index in range(4)
                            },
                            **{
                                f"resource_processing_support_limited_{index}_total": float(
                                    self.total_resource_processing_support_limited[index]
                                )
                                for index in range(4)
                            },
                            **{
                                f"resource_processing_support_accelerated_{index}_step": float(
                                    stats.resource_processing_support_accelerated[index]
                                )
                                for index in range(4)
                            },
                            **{
                                f"resource_processing_support_accelerated_{index}_total": float(
                                    self.total_resource_processing_support_accelerated[index]
                                )
                                for index in range(4)
                            },
                            **{
                                f"resource_processing_energy_rejected_{index}_step": float(
                                    stats.resource_processing_energy_rejected[index]
                                )
                                for index in range(4)
                            },
                            **{
                                f"resource_processing_energy_rejected_{index}_total": float(
                                    self.total_resource_processing_energy_rejected[index]
                                )
                                for index in range(4)
                            },
                            **{
                                f"resource_processing_support_absolute_deviation_{index}_step": float(
                                    stats.resource_processing_support_absolute_deviation[index]
                                )
                                for index in range(4)
                            },
                            **{
                                f"resource_processing_support_absolute_deviation_{index}_total": float(
                                    self.total_resource_processing_support_absolute_deviation[index]
                                )
                                for index in range(4)
                            },
                            **{
                                f"resource_processing_support_{index}_weighted_mean_step": float(
                                    stats.resource_processing_support_weighted_sum[index]
                                    / stats.resource_processing_support_weight[index]
                                )
                                if stats.resource_processing_support_weight[index] > 0.0
                                else 1.0
                                for index in range(4)
                            },
                            **{
                                f"resource_processing_support_{index}_weighted_mean_total": float(
                                    self.total_resource_processing_support_weighted_sum[index]
                                    / self.total_resource_processing_support_weight[index]
                                )
                                if self.total_resource_processing_support_weight[index] > 0.0
                                else 1.0
                                for index in range(4)
                            },
                            "resource_processing_energy_cost_step": float(
                                stats.resource_processing_energy_cost
                            ),
                            "resource_processing_energy_cost_total": float(
                                self.total_resource_processing_energy_cost
                            ),
                        }
                        if spatial_processing_enabled(self.cfg)
                        else {}
                    ),
                    **{
                        f"resource_converted_{index}_step": float(stats.resource_converted[index])
                        for index in range(4)
                    },
                    **{
                        f"resource_converted_{index}_total": float(self.total_resource_converted[index])
                        for index in range(4)
                    },
                    **{
                        f"resource_store_decay_{index}_step": float(stats.resource_store_decay[index])
                        for index in range(4)
                    },
                    **{
                        f"resource_store_decay_{index}_total": float(self.total_resource_store_decay[index])
                        for index in range(4)
                    },
                    **{
                        f"resource_store_death_loss_{index}_step": float(stats.resource_store_death_loss[index])
                        for index in range(4)
                    },
                    **{
                        f"resource_store_death_loss_{index}_total": float(self.total_resource_store_death_loss[index])
                        for index in range(4)
                    },
                    **(
                        {
                            **{
                                f"resource_residue_deposited_{index}_step": float(stats.resource_residue_deposited[index])
                                for index in range(4)
                            },
                            **{
                                f"resource_residue_deposited_{index}_total": float(self.total_resource_residue_deposited[index])
                                for index in range(4)
                            },
                            **{
                                f"resource_residue_released_{index}_step": float(stats.resource_residue_released[index])
                                for index in range(4)
                            },
                            **{
                                f"resource_residue_released_{index}_total": float(self.total_resource_residue_released[index])
                                for index in range(4)
                            },
                            **{
                                f"resource_residue_field_roundoff_{index}_step": float(
                                    np.asarray(
                                        getattr(
                                            self.environment,
                                            "resource_residue_field_roundoff_step",
                                            np.zeros(4),
                                        ),
                                        dtype=np.float64,
                                    )[index]
                                )
                                for index in range(4)
                            },
                            **{
                                f"resource_residue_field_roundoff_{index}_total": float(
                                    np.asarray(
                                        getattr(
                                            self.environment,
                                            "total_resource_residue_field_roundoff",
                                            np.zeros(4),
                                        ),
                                        dtype=np.float64,
                                    )[index]
                                )
                                for index in range(4)
                            },
                            **{
                                f"resource_residue_deposit_roundoff_{index}_step": float(
                                    np.asarray(
                                        getattr(
                                            self.environment,
                                            "resource_residue_deposit_roundoff_step",
                                            np.zeros(4),
                                        ),
                                        dtype=np.float64,
                                    )[index]
                                )
                                for index in range(4)
                            },
                            **{
                                f"resource_residue_deposit_roundoff_{index}_total": float(
                                    np.asarray(
                                        getattr(
                                            self.environment,
                                            "total_resource_residue_deposit_roundoff",
                                            np.zeros(4),
                                        ),
                                        dtype=np.float64,
                                    )[index]
                                )
                                for index in range(4)
                            },
                        }
                        if external_resource_recycling_enabled(self.cfg)
                        else {}
                    ),
                    **{
                        f"resource_body_realized_{index}_step": float(stats.resource_body_realized[index])
                        for index in range(5)
                    },
                    **{
                        f"resource_body_realized_{index}_total": float(self.total_resource_body_realized[index])
                        for index in range(5)
                    },
                }
                if resource_metabolism_enabled(self.cfg)
                else {}
            ),
            "shared_energy_step": stats.shared_energy,
            "shared_energy_total": self.total_shared_energy,
            **{
                f"shared_resource_{index}_step": float(stats.shared_resources[index])
                for index in range(4)
            },
            **{
                f"shared_resource_{index}_total": float(self.total_shared_resources[index])
                for index in range(4)
            },
            "resource_sensing_maintenance_energy_step": stats.resource_sensing_maintenance_energy,
            "resource_sensing_use_energy_step": stats.resource_sensing_use_energy,
            "resource_sensing_development_energy_step": stats.resource_sensing_development_energy,
            "resource_load_movement_energy_step": stats.resource_load_movement_energy,
            "harvest_contest_events_step": stats.harvest_contest_events,
            "harvest_contest_pressure_step": stats.harvest_contest_pressure,
            "harvest_contest_energy_step": stats.harvest_contest_energy,
            "harvest_contest_integrity_damage_step": stats.harvest_contest_integrity_damage,
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
            "gpu_device_preprocess_rows": stats.gpu_device_preprocess_rows,
            "gpu_device_resident_host_bytes_avoided": (
                stats.gpu_device_resident_host_bytes_avoided
            ),
            "gpu_device_latent_root_rows": stats.gpu_device_latent_root_rows,
            "gpu_memory_pool_policy": self.cfg.run.gpu_memory_pool_policy,
            "gpu_memory_pool_cache_limit_bytes": (
                self.cfg.run.gpu_memory_pool_cache_limit_bytes
            ),
            "gpu_memory_pool_trim_period": (
                self.cfg.run.gpu_memory_pool_trim_period
            ),
            "gpu_memory_used_bytes": stats.gpu_memory_used_bytes,
            "gpu_memory_pool_total_bytes": stats.gpu_memory_pool_total_bytes,
            "gpu_memory_pool_cached_bytes": stats.gpu_memory_pool_cached_bytes,
            "gpu_memory_pool_total_bytes_after_trim": (
                stats.gpu_memory_pool_total_bytes_after_trim
            ),
            "gpu_memory_pool_cached_bytes_after_trim": (
                stats.gpu_memory_pool_cached_bytes_after_trim
            ),
            "gpu_memory_pool_peak_used_bytes": (
                stats.gpu_memory_pool_peak_used_bytes
            ),
            "gpu_memory_pool_peak_total_bytes": (
                stats.gpu_memory_pool_peak_total_bytes
            ),
            "gpu_memory_pool_trim_count": stats.gpu_memory_pool_trim_count,
            "gpu_memory_pool_trimmed_step": stats.gpu_memory_pool_trimmed_step,
            "gpu_memory_pool_released_bytes_step": (
                stats.gpu_memory_pool_released_bytes_step
            ),
            "gpu_pinned_memory_pool_free_blocks": (
                stats.gpu_pinned_memory_pool_free_blocks
            ),
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
        if capacity_metrics is not None:
            row.update(
                {
                    "capacity_maintenance_energy_step": stats.capacity_maintenance_energy,
                    "capacity_development_energy_step": stats.capacity_development_energy,
                    "differentiation_schema": capacity_metrics["differentiation_schema"],
                    "capacity_effective_dimensions": float(
                        capacity_metrics["capacity_effective_dimensions"]
                    ),
                    "capacity_working_memory_dimensions_mean": float(
                        capacity_metrics["capacity_working_memory_dimensions_mean"]
                    ),
                    "capacity_working_memory_dimensions_std": float(
                        capacity_metrics["capacity_working_memory_dimensions_std"]
                    ),
                    "capacity_knowledge_capacity_bytes_mean": float(
                        capacity_metrics["capacity_knowledge_capacity_bytes_mean"]
                    ),
                    "capacity_knowledge_capacity_bytes_std": float(
                        capacity_metrics["capacity_knowledge_capacity_bytes_std"]
                    ),
                    "capacity_relation_slots_mean": float(
                        capacity_metrics["capacity_relation_slots_mean"]
                    ),
                    "capacity_relation_slots_std": float(
                        capacity_metrics["capacity_relation_slots_std"]
                    ),
                    "capacity_knowledge_attention_slots_mean": float(
                        capacity_metrics["capacity_knowledge_attention_slots_mean"]
                    ),
                    "capacity_knowledge_attention_slots_std": float(
                        capacity_metrics["capacity_knowledge_attention_slots_std"]
                    ),
                }
            )
        if self.cfg.knowledge.enabled:
            knowledge_summary = self.knowledge.summary()
            row.update(
                {
                    "knowledge_content_count": int(knowledge_summary["content_count"]),
                    "knowledge_variant_content_count": int(knowledge_summary["variant_content_count"]),
                    "knowledge_copy_count": int(knowledge_summary["copy_count"]),
                    "knowledge_holder_count": int(knowledge_summary["holder_count"]),
                    "knowledge_active_encoded_bytes": int(knowledge_summary["active_encoded_bytes"]),
                    "knowledge_maintenance_energy_step": stats.knowledge.maintenance_energy,
                    "knowledge_sender_energy_step": stats.knowledge.sender_energy,
                    "knowledge_receiver_energy_step": stats.knowledge.receiver_energy,
                    "knowledge_total_energy_cost_step": stats.knowledge.total_energy_cost,
                    "knowledge_transfer_proposals_step": (
                        stats.knowledge.transfer_attempts + stats.knowledge.attention_rejected
                    ),
                    "knowledge_transfer_attempts_step": stats.knowledge.transfer_attempts,
                    "knowledge_transfer_delivered_step": stats.knowledge.transfer_delivered,
                    "knowledge_transfer_lost_step": stats.knowledge.transfer_lost,
                    "knowledge_transfer_corrupted_step": stats.knowledge.transfer_corrupted,
                    "knowledge_transfer_committed_step": stats.knowledge.transfer_committed,
                    "knowledge_transfer_committed_bytes_step": stats.knowledge.transfer_committed_bytes,
                    "knowledge_transfer_same_lineage_committed_step": stats.knowledge.transfer_same_lineage_committed,
                    "knowledge_transfer_cross_lineage_committed_step": stats.knowledge.transfer_cross_lineage_committed,
                    "knowledge_transfer_unknown_lineage_committed_step": stats.knowledge.transfer_unknown_lineage_committed,
                    "knowledge_transfer_same_group_committed_step": stats.knowledge.transfer_same_group_committed,
                    "knowledge_transfer_cross_group_committed_step": stats.knowledge.transfer_cross_group_committed,
                    "knowledge_transfer_unknown_group_committed_step": stats.knowledge.transfer_unknown_group_committed,
                    "knowledge_transfer_duplicate_rejected_step": stats.knowledge.transfer_duplicate_rejected,
                    "knowledge_transfer_capacity_rejected_step": stats.knowledge.transfer_capacity_rejected,
                    "knowledge_transfer_energy_rejected_step": stats.knowledge.transfer_energy_rejected,
                    "knowledge_attention_rejected_step": stats.knowledge.attention_rejected,
                    "knowledge_forgotten_step": stats.knowledge.forgotten,
                    "knowledge_evicted_capacity_step": stats.knowledge.evicted_capacity,
                    "knowledge_evicted_maintenance_step": stats.knowledge.evicted_maintenance,
                    "knowledge_removed_dead_holder_step": stats.knowledge.removed_dead_holder,
                    "knowledge_learning_energy_step": stats.knowledge.learning_energy,
                    "knowledge_outcome_records_step": stats.knowledge.outcome_records,
                    "knowledge_outcome_success_step": stats.knowledge.outcome_success,
                    "knowledge_outcome_failed_step": stats.knowledge.outcome_failed,
                    "knowledge_outcome_partial_step": stats.knowledge.outcome_partial,
                    "knowledge_outcome_updates_step": stats.knowledge.outcome_updates,
                    "knowledge_private_experiences_created_step": stats.knowledge.private_experiences_created,
                    "knowledge_private_experience_updates_step": stats.knowledge.private_experience_updates,
                    "knowledge_transferred_copies_verified_step": stats.knowledge.transferred_copies_verified,
                    "knowledge_outcome_unmatched_step": stats.knowledge.outcome_unmatched,
                    "knowledge_learning_energy_rejected_step": stats.knowledge.learning_energy_rejected,
                    "knowledge_learning_capacity_rejected_step": stats.knowledge.learning_capacity_rejected,
                    "knowledge_learning_match_limit_skipped_step": stats.knowledge.learning_match_limit_skipped,
                    "knowledge_confidence_decayed_step": stats.knowledge.confidence_decayed,
                    "knowledge_policy_influenced_entities_step": stats.knowledge.policy_influenced_entities,
                    "knowledge_policy_influenced_actions_step": stats.knowledge.policy_influenced_actions,
                    "knowledge_policy_support_copies_step": stats.knowledge.policy_support_copies,
                    "knowledge_policy_private_support_copies_step": stats.knowledge.policy_private_support_copies,
                    "knowledge_policy_transfer_support_copies_step": stats.knowledge.policy_transfer_support_copies,
                    "knowledge_policy_unverified_transfer_support_copies_step": (
                        stats.knowledge.policy_unverified_transfer_support_copies
                    ),
                    "knowledge_policy_changed_actions_step": stats.knowledge.policy_changed_actions,
                    "knowledge_policy_residual_abs_sum_step": stats.knowledge.policy_residual_abs_sum,
                    "knowledge_policy_mean_abs_residual_step": (
                        stats.knowledge.policy_residual_abs_sum
                        / stats.knowledge.policy_influenced_actions
                        if stats.knowledge.policy_influenced_actions
                        else 0.0
                    ),
                    "knowledge_policy_max_abs_residual_step": stats.knowledge_policy_max_abs_residual,
                    "knowledge_policy_latent_dimensions_step": stats.knowledge.policy_latent_dimensions,
                    "knowledge_policy_latent_max_width_step": stats.knowledge.policy_latent_max_width,
                    "knowledge_policy_quantized_residual_abs_sum_step": (
                        stats.knowledge.policy_quantized_residual_abs_sum
                    ),
                    "knowledge_policy_linear_shadow_changed_actions_step": (
                        stats.knowledge.policy_linear_shadow_changed_actions
                    ),
                    "knowledge_policy_router_saturation_units_step": (
                        stats.knowledge.policy_router_saturation_units
                    ),
                    "knowledge_policy_router_clipped_outputs_step": (
                        stats.knowledge.policy_router_clipped_outputs
                    ),
                    "knowledge_policy_router_hidden_abs_sum_step": (
                        stats.knowledge.policy_router_hidden_abs_sum
                    ),
                    "knowledge_policy_router_hidden_active_units_step": (
                        stats.knowledge.policy_router_hidden_active_units
                    ),
                    "knowledge_routing_requested_energy_step": stats.knowledge.routing_requested_energy,
                    "knowledge_routing_committed_energy_step": stats.knowledge.routing_committed_energy,
                    "knowledge_routing_rejected_energy_step": stats.knowledge.routing_rejected_energy,
                    "knowledge_routing_requested_entities_step": stats.knowledge.routing_requested_entities,
                    "knowledge_routing_committed_entities_step": stats.knowledge.routing_committed_entities,
                    "knowledge_routing_rejected_entities_step": stats.knowledge.routing_rejected_entities,
                    "knowledge_routing_accepted_actions_step": stats.knowledge.routing_accepted_actions,
                    "knowledge_routing_rejected_actions_step": stats.knowledge.routing_rejected_actions,
                    "knowledge_routing_latent_dimensions_step": stats.knowledge.routing_latent_dimensions,
                    "knowledge_routing_mac_count_step": stats.knowledge.routing_mac_count,
                    "knowledge_routing_active_hidden_units_step": stats.knowledge.routing_active_hidden_units,
                    "knowledge_routing_saturation_count_step": stats.knowledge.routing_saturation_count,
                    "knowledge_routing_clipped_output_count_step": stats.knowledge.routing_clipped_output_count,
                    "knowledge_routing_cost_induced_action_changes_step": (
                        stats.knowledge.routing_cost_induced_action_changes
                    ),
                    "knowledge_selection_candidate_copies_step": (
                        stats.knowledge.selection_candidate_copies
                    ),
                    "knowledge_selection_selected_copies_step": (
                        stats.knowledge.selection_selected_copies
                    ),
                    "knowledge_selection_requested_top_k_sum_step": (
                        stats.knowledge.selection_requested_top_k_sum
                    ),
                    "knowledge_selection_zero_capacity_entities_step": (
                        stats.knowledge.selection_zero_capacity_entities
                    ),
                    "knowledge_selection_tie_count_step": (
                        stats.knowledge.selection_tie_count
                    ),
                    "knowledge_selection_committed_energy_step": (
                        stats.knowledge.selection_committed_energy
                    ),
                    "knowledge_working_memory_requested_energy_step": (
                        stats.knowledge.working_memory_requested_energy
                    ),
                    "knowledge_working_memory_committed_energy_step": (
                        stats.knowledge.working_memory_committed_energy
                    ),
                    "knowledge_working_memory_rejected_energy_step": (
                        stats.knowledge.working_memory_rejected_energy
                    ),
                    "knowledge_working_memory_requested_entities_step": (
                        stats.knowledge.working_memory_requested_entities
                    ),
                    "knowledge_working_memory_committed_entities_step": (
                        stats.knowledge.working_memory_committed_entities
                    ),
                    "knowledge_working_memory_rejected_entities_step": (
                        stats.knowledge.working_memory_rejected_entities
                    ),
                    "knowledge_working_memory_saturation_units_step": (
                        stats.knowledge.working_memory_saturation_units
                    ),
                    "knowledge_working_memory_active_dimensions_step": (
                        stats.knowledge.working_memory_active_dimensions
                    ),
                    "knowledge_working_memory_induced_action_changes_step": (
                        stats.knowledge.working_memory_induced_action_changes
                    ),
                    "knowledge_maintenance_energy_total": float(knowledge_summary["maintenance_energy_total"]),
                    "knowledge_sender_energy_total": float(knowledge_summary["sender_energy_total"]),
                    "knowledge_receiver_energy_total": float(knowledge_summary["receiver_energy_total"]),
                    "knowledge_transfer_proposals_total": int(
                        knowledge_summary["transfer_attempts_total"]
                        + knowledge_summary["attention_rejected_total"]
                    ),
                    "knowledge_transfer_attempts_total": int(knowledge_summary["transfer_attempts_total"]),
                    "knowledge_transfer_committed_total": int(knowledge_summary["transfer_committed_total"]),
                    "knowledge_transfer_committed_bytes_total": int(knowledge_summary["transfer_committed_bytes_total"]),
                    "knowledge_transfer_same_lineage_committed_total": int(knowledge_summary["transfer_same_lineage_committed_total"]),
                    "knowledge_transfer_cross_lineage_committed_total": int(knowledge_summary["transfer_cross_lineage_committed_total"]),
                    "knowledge_transfer_unknown_lineage_committed_total": int(knowledge_summary["transfer_unknown_lineage_committed_total"]),
                    "knowledge_transfer_same_group_committed_total": int(knowledge_summary["transfer_same_group_committed_total"]),
                    "knowledge_transfer_cross_group_committed_total": int(knowledge_summary["transfer_cross_group_committed_total"]),
                    "knowledge_transfer_unknown_group_committed_total": int(knowledge_summary["transfer_unknown_group_committed_total"]),
                    "knowledge_transfer_duplicate_rejected_total": int(knowledge_summary["transfer_duplicate_rejected_total"]),
                    "knowledge_transfer_capacity_rejected_total": int(knowledge_summary["transfer_capacity_rejected_total"]),
                    "knowledge_transfer_energy_rejected_total": int(knowledge_summary["transfer_energy_rejected_total"]),
                    "knowledge_attention_rejected_total": int(knowledge_summary["attention_rejected_total"]),
                    "knowledge_learning_energy_total": float(knowledge_summary["learning_energy_total"]),
                    "knowledge_outcome_records_total": int(knowledge_summary["outcome_records_total"]),
                    "knowledge_outcome_updates_total": int(knowledge_summary["outcome_updates_total"]),
                    "knowledge_private_experiences_created_total": int(knowledge_summary["private_experiences_created_total"]),
                    "knowledge_private_experience_updates_total": int(knowledge_summary["private_experience_updates_total"]),
                    "knowledge_transferred_copies_verified_total": int(knowledge_summary["transferred_copies_verified_total"]),
                    "knowledge_outcome_unmatched_total": int(knowledge_summary["outcome_unmatched_total"]),
                    "knowledge_learning_energy_rejected_total": int(knowledge_summary["learning_energy_rejected_total"]),
                    "knowledge_learning_capacity_rejected_total": int(knowledge_summary["learning_capacity_rejected_total"]),
                    "knowledge_policy_influenced_entities_total": int(knowledge_summary["policy_influenced_entities_total"]),
                    "knowledge_policy_influenced_actions_total": int(knowledge_summary["policy_influenced_actions_total"]),
                    "knowledge_policy_support_copies_total": int(knowledge_summary["policy_support_copies_total"]),
                    "knowledge_policy_private_support_copies_total": int(knowledge_summary["policy_private_support_copies_total"]),
                    "knowledge_policy_transfer_support_copies_total": int(knowledge_summary["policy_transfer_support_copies_total"]),
                    "knowledge_policy_unverified_transfer_support_copies_total": int(
                        knowledge_summary["policy_unverified_transfer_support_copies_total"]
                    ),
                    "knowledge_policy_changed_actions_total": int(knowledge_summary["policy_changed_actions_total"]),
                    "knowledge_policy_residual_abs_sum_total": float(knowledge_summary["policy_residual_abs_sum_total"]),
                    "knowledge_policy_latent_dimensions_total": int(
                        knowledge_summary["policy_latent_dimensions_total"]
                    ),
                    "knowledge_policy_latent_max_width": int(
                        knowledge_summary["policy_latent_max_width"]
                    ),
                    "knowledge_policy_quantized_residual_abs_sum_total": int(
                        knowledge_summary["policy_quantized_residual_abs_sum_total"]
                    ),
                    "knowledge_policy_linear_shadow_changed_actions_total": int(
                        knowledge_summary["policy_linear_shadow_changed_actions_total"]
                    ),
                    "knowledge_policy_router_saturation_units_total": int(
                        knowledge_summary["policy_router_saturation_units_total"]
                    ),
                    "knowledge_policy_router_clipped_outputs_total": int(
                        knowledge_summary["policy_router_clipped_outputs_total"]
                    ),
                    "knowledge_policy_router_hidden_abs_sum_total": int(
                        knowledge_summary["policy_router_hidden_abs_sum_total"]
                    ),
                    "knowledge_policy_router_hidden_active_units_total": int(
                        knowledge_summary["policy_router_hidden_active_units_total"]
                    ),
                    "knowledge_routing_requested_energy_total": float(
                        knowledge_summary["routing_requested_energy_total"]
                    ),
                    "knowledge_routing_committed_energy_total": float(
                        knowledge_summary["routing_committed_energy_total"]
                    ),
                    "knowledge_routing_rejected_energy_total": float(
                        knowledge_summary["routing_rejected_energy_total"]
                    ),
                    "knowledge_routing_requested_entities_total": int(
                        knowledge_summary["routing_requested_entities_total"]
                    ),
                    "knowledge_routing_committed_entities_total": int(
                        knowledge_summary["routing_committed_entities_total"]
                    ),
                    "knowledge_routing_rejected_entities_total": int(
                        knowledge_summary["routing_rejected_entities_total"]
                    ),
                    "knowledge_routing_accepted_actions_total": int(
                        knowledge_summary["routing_accepted_actions_total"]
                    ),
                    "knowledge_routing_rejected_actions_total": int(
                        knowledge_summary["routing_rejected_actions_total"]
                    ),
                    "knowledge_routing_latent_dimensions_total": int(
                        knowledge_summary["routing_latent_dimensions_total"]
                    ),
                    "knowledge_routing_mac_count_total": int(
                        knowledge_summary["routing_mac_count_total"]
                    ),
                    "knowledge_routing_active_hidden_units_total": int(
                        knowledge_summary["routing_active_hidden_units_total"]
                    ),
                    "knowledge_routing_saturation_count_total": int(
                        knowledge_summary["routing_saturation_count_total"]
                    ),
                    "knowledge_routing_clipped_output_count_total": int(
                        knowledge_summary["routing_clipped_output_count_total"]
                    ),
                    "knowledge_routing_cost_induced_action_changes_total": int(
                        knowledge_summary["routing_cost_induced_action_changes_total"]
                    ),
                    "knowledge_selection_candidate_copies_total": int(
                        knowledge_summary["selection_candidate_copies_total"]
                    ),
                    "knowledge_selection_selected_copies_total": int(
                        knowledge_summary["selection_selected_copies_total"]
                    ),
                    "knowledge_selection_requested_top_k_sum_total": int(
                        knowledge_summary["selection_requested_top_k_sum_total"]
                    ),
                    "knowledge_selection_zero_capacity_entities_total": int(
                        knowledge_summary["selection_zero_capacity_entities_total"]
                    ),
                    "knowledge_selection_tie_count_total": int(
                        knowledge_summary["selection_tie_count_total"]
                    ),
                    "knowledge_selection_committed_energy_total": float(
                        knowledge_summary["selection_committed_energy_total"]
                    ),
                    "knowledge_working_memory_requested_energy_total": float(
                        knowledge_summary["working_memory_requested_energy_total"]
                    ),
                    "knowledge_working_memory_committed_energy_total": float(
                        knowledge_summary["working_memory_committed_energy_total"]
                    ),
                    "knowledge_working_memory_rejected_energy_total": float(
                        knowledge_summary["working_memory_rejected_energy_total"]
                    ),
                    "knowledge_working_memory_requested_entities_total": int(
                        knowledge_summary["working_memory_requested_entities_total"]
                    ),
                    "knowledge_working_memory_committed_entities_total": int(
                        knowledge_summary["working_memory_committed_entities_total"]
                    ),
                    "knowledge_working_memory_rejected_entities_total": int(
                        knowledge_summary["working_memory_rejected_entities_total"]
                    ),
                    "knowledge_working_memory_saturation_units_total": int(
                        knowledge_summary["working_memory_saturation_units_total"]
                    ),
                    "knowledge_working_memory_active_dimensions_total": int(
                        knowledge_summary["working_memory_active_dimensions_total"]
                    ),
                    "knowledge_working_memory_induced_action_changes_total": int(
                        knowledge_summary["working_memory_induced_action_changes_total"]
                    ),
                    "validation_seconds": stats.validation_seconds,
                }
            )
            if self.cfg.knowledge.latent_policy_enabled:
                row.update(
                    {
                        "knowledge_latent_content_count": int(
                            knowledge_summary["latent_content_count"]
                        ),
                        "knowledge_latent_total_dimensions": int(
                            knowledge_summary["latent_total_dimensions"]
                        ),
                        "knowledge_latent_mean_dimensions": float(
                            knowledge_summary["latent_mean_dimensions"]
                        ),
                        "knowledge_latent_max_dimensions": int(
                            knowledge_summary["latent_max_dimensions"]
                        ),
                    }
                )
            if self.cfg.knowledge.candidate_tracking_enabled:
                row.update(
                    {
                        "knowledge_candidate_count": int(
                            knowledge_summary["knowledge_candidate_count"]
                        ),
                        "knowledge_candidate_active_count": int(
                            knowledge_summary["knowledge_candidate_active_count"]
                        ),
                        "knowledge_candidate_inactive_count": int(
                            knowledge_summary["knowledge_candidate_inactive_count"]
                        ),
                        "knowledge_candidate_root_count": int(
                            knowledge_summary["knowledge_candidate_root_count"]
                        ),
                        "knowledge_candidate_variant_count": int(
                            knowledge_summary["knowledge_candidate_variant_count"]
                        ),
                        "knowledge_candidate_multi_holder_count": int(
                            knowledge_summary["knowledge_candidate_multi_holder_count"]
                        ),
                        "knowledge_candidate_policy_influence_events": int(
                            knowledge_summary["knowledge_candidate_policy_influence_events"]
                        ),
                        "knowledge_candidate_policy_changed_actions": int(
                            knowledge_summary["knowledge_candidate_policy_changed_actions"]
                        ),
                        "knowledge_candidate_host_cost_total": float(
                            knowledge_summary["knowledge_candidate_host_cost_total"]
                        ),
                        "knowledge_candidate_routing_cost_total": float(
                            knowledge_summary["knowledge_candidate_routing_cost_total"]
                        ),
                        "knowledge_candidate_selection_cost_total": float(
                            knowledge_summary["knowledge_candidate_selection_cost_total"]
                        ),
                        "knowledge_candidate_working_memory_cost_total": float(
                            knowledge_summary["knowledge_candidate_working_memory_cost_total"]
                        ),
                        "knowledge_candidate_unattributed_working_memory_cost_total": float(
                            knowledge_summary[
                                "knowledge_candidate_unattributed_working_memory_cost_total"
                            ]
                        ),
                        "knowledge_boundary_group_internal_commits": int(
                            knowledge_summary["knowledge_boundary_group_internal_commits"]
                        ),
                        "knowledge_boundary_group_cross_commits": int(
                            knowledge_summary["knowledge_boundary_group_cross_commits"]
                        ),
                        "knowledge_boundary_group_unknown_commits": int(
                            knowledge_summary["knowledge_boundary_group_unknown_commits"]
                        ),
                        "knowledge_boundary_group_cohesion": float(
                            knowledge_summary["knowledge_boundary_group_cohesion"]
                        ),
                        "knowledge_boundary_group_cohesion_valid": int(
                            bool(knowledge_summary["knowledge_boundary_group_cohesion_valid"])
                        ),
                        "knowledge_candidate_last_update_tick": int(
                            knowledge_summary["knowledge_candidate_last_update_tick"]
                        ),
                    }
                )
        if resource_diversity is not None:
            row.update(
                {
                    "environment_resource_effective_dimensions": float(
                        resource_diversity["resource_effective_dimensions"]
                    ),
                    "environment_resource_channel_mean_abs_correlation": float(
                        resource_diversity[
                            "resource_channel_mean_abs_correlation"
                        ]
                    ),
                    "environment_resource_channel_max_abs_correlation": float(
                        resource_diversity[
                            "resource_channel_max_abs_correlation"
                        ]
                    ),
                }
            )
        row.update(self.subjects.summary())
        return row
