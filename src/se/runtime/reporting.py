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
    physiology_diagnostics,
    resource_metabolism_enabled,
)
from se.runtime.resource_metabolism import resource_metabolism_diagnostics
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
        if self.cfg.environment.schema == ORTHOGONAL_ENVIRONMENT_SCHEMA:
            manifest["environment_resource_dynamics"] = {
                "schema": ORTHOGONAL_ENVIRONMENT_SCHEMA,
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
                "entity_state_feedback": False,
                "lineage_feedback": False,
                "group_feedback": False,
            }
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
        if (
            self.gpu_semantics_mode == "hybrid-accelerated"
            and self.gpu_acceleration_enabled
        ):
            violations.append(
                "accelerated GPU multi-tick parity is not proven; "
                "use strict-reference for scientific results"
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
                "cpu_reference_world_authoritative": (
                    self.gpu_runtime is None
                ),
                "hybrid_acceleration_parity_proven": False,
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
                    "reserved_neutral": [7],
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
        if self.cfg.environment.schema == ORTHOGONAL_ENVIRONMENT_SCHEMA:
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
    ) -> dict[str, float | int]:
        ent = self.entities
        active = np.flatnonzero(ent.alive)
        alive_count = active.size
        if alive_count:
            mean_energy = float(ent.energy[active].mean())
            mean_integrity = float(ent.integrity[active].mean())
            mean_age = float(ent.age[active].mean())
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
        physiology_environment_metrics = physiology_field_metrics(
            self.environment.oxygen, self.environment.terrain, self.environment.wear
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
        )
        affinity_metrics = resource_affinity_diagnostics(
            ent.alive, ent.genotype, self.cfg
        )
        danger_evidence_metrics = danger_evidence_diagnostics(
            ent.alive, ent.genotype, self.cfg
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
            if self.cfg.environment.schema == ORTHOGONAL_ENVIRONMENT_SCHEMA
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
            "mean_oxygenation": mean_oxygenation,
            "mean_tissue_condition": mean_tissue_condition,
            "mean_structure_condition": mean_structure_condition,
            "mean_metabolic_fatigue": mean_metabolic_fatigue,
            "mean_mobilization_messenger": mean_mobilization_messenger,
            "mean_maintenance_messenger": mean_maintenance_messenger,
            "mean_messenger_precursor": mean_messenger_precursor,
            "mean_physiology_sensor_multiplier": mean_physiology_sensor_multiplier,
            "mean_age": mean_age,
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
            "capacity_ablation_enabled": int(self.capacity_ablation_enabled),
            "capacity_effective_schema": (
                "fixed-midpoint-elastic-capacities-ablation-v1"
                if self.capacity_ablation_enabled
                else self.cfg.differentiation.schema
            ),
            "resource_affinity_ablation_enabled": int(
                self.resource_affinity_ablation_enabled
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
                    "resource_converted_total": self.total_resource_converted.tolist(),
                    "resource_store_decay_total": self.total_resource_store_decay.tolist(),
                    "resource_store_death_loss_total": self.total_resource_store_death_loss.tolist(),
                    "resource_body_realized_total": self.total_resource_body_realized.tolist(),
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

