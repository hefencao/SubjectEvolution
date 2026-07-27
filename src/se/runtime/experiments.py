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


class SimulationExperimentMixin:
    """Counterfactual intervention and fixed-cohort experiment hooks."""

    def functional_module_lineage_ablation_mask(
        self,
        rows: np.ndarray,
        *,
        cost: bool,
    ) -> np.ndarray | None:
        """Return a row-wise module mask for preregistered lineage branches.

        The mapping is empty in normal simulations.  A true cell means that the
        corresponding fixed module is neutralized only for entities carrying
        that genetic lineage ID.  ``cost=False`` controls routed output;
        ``cost=True`` controls expression-energy charging.
        """

        selected = np.asarray(rows, dtype=np.int32)
        mapping = (
            self.functional_module_lineage_cost_ablation
            if cost
            else self.functional_module_lineage_output_ablation
        )
        if not mapping:
            return None
        count = int(self.cfg.functional_modules.module_count)
        result = np.zeros((selected.size, count), dtype=bool)
        if selected.size == 0:
            return result
        lineage_ids = self.entities.lineage_id[selected].astype(np.uint64, copy=False)
        for module_index, targets in mapping.items():
            if not targets:
                continue
            target_ids = np.asarray(sorted(targets), dtype=np.uint64)
            result[:, int(module_index)] = np.isin(lineage_ids, target_ids)
        return result

    def apply_functional_module_lineage_intervention(
        self,
        *,
        module_index: int,
        lineage_id: int,
        neutralize_cost: bool,
    ) -> None:
        """Neutralize one fixed D2 module for one genetic lineage.

        This is an experiment-only phenotype intervention.  It preserves the
        genotype, lineage ID, stable IDs and keyed randomness.  Descendants of
        the same genetic lineage remain under the treatment for the branch.
        """

        if not self.cfg.functional_modules.enabled:
            raise ValueError(
                "lineage-targeted module neutralization requires functional modules"
            )
        module_index = int(module_index)
        count = int(self.cfg.functional_modules.module_count)
        if not 0 <= module_index < count:
            raise ValueError(
                f"functional module index {module_index} is outside configured range"
            )
        lineage_id = int(lineage_id)
        if lineage_id < 0:
            raise ValueError("lineage_id must be non-negative")
        active = np.flatnonzero(self.entities.alive).astype(np.int32)
        members = int(
            np.count_nonzero(
                self.entities.lineage_id[active] == np.uint64(lineage_id)
            )
        )
        if members == 0:
            raise ValueError(
                f"lineage {lineage_id} has no living members at intervention tick"
            )
        self.functional_module_lineage_output_ablation.setdefault(
            module_index, set()
        ).add(lineage_id)
        if neutralize_cost:
            self.functional_module_lineage_cost_ablation.setdefault(
                module_index, set()
            ).add(lineage_id)
        intervention_type = (
            "neutralize-functional-module-expression-for-lineage"
            if neutralize_cost
            else "neutralize-functional-module-output-for-lineage"
        )
        self.intervention_history.append(
            {
                "tick": self.tick,
                "type": intervention_type,
                "kind": "modify-rules",
                "target_scope": "fixed-functional-module-within-genetic-lineage",
                "direct_action_control": False,
                "experiment_mode": self.experiment_mode.value,
                "module_index": module_index,
                "lineage_id": lineage_id,
                "living_members_at_intervention": members,
                "effective_output": "zero-residual-for-target-lineage",
                "expression_cost_neutralized": bool(neutralize_cost),
                "genotype_coordinates_modified": 0,
                "lineage_membership_modified": False,
                "inheritance_modified": False,
                "future_same-lineage_offspring_treated": True,
            }
        )

    def freeze_local_reference_boundary(self) -> None:
        """Freeze a diagnostic-only group partition for paired branch evaluation."""

        if self.local_stress_diagnostics is None:
            raise RuntimeError(
                "local reference-boundary evaluation requires spatial stress diagnostics"
            )
        self.local_stress_diagnostics.freeze_reference_boundary(
            tick=self.tick,
            alive=self.entities.alive,
            stable_ids=self.entities.entity_id,
            group_tokens=self.social.group_id,
        )


    def configure_event_cohort_diagnostics(
        self, requests: list[dict[str, object]] | tuple[dict[str, object], ...]
    ) -> None:
        """Enable preregistered endpoint cohort accounting for this run only."""

        if not self.cfg.run.spatial_stress_diagnostics_enabled:
            raise ValueError(
                "event cohort diagnostics require spatial stress diagnostics"
            )
        self.event_cohort_diagnostics = EventCohortDiagnostics(
            requests,
            world_width=self.cfg.world.width,
            world_height=self.cfg.world.height,
            regions_x=self.cfg.run.spatial_stress_regions_x,
            regions_y=self.cfg.run.spatial_stress_regions_y,
            world_grid_x=self.cfg.world.grid_x,
            world_grid_y=self.cfg.world.grid_y,
            region_schema=self.cfg.run.spatial_stress_region_schema,
        )
        self._observe_event_cohort_diagnostics()


    def _observe_event_cohort_diagnostics(self) -> None:
        tracker = self.event_cohort_diagnostics
        if tracker is None:
            return
        tracker.observe(
            tick=self.tick,
            alive=self.entities.alive,
            stable_ids=self.entities.entity_id,
            x=self.entities.x,
            y=self.entities.y,
        )


    def event_cohort_summaries(self) -> dict[str, dict[str, object]]:
        tracker = self.event_cohort_diagnostics
        if tracker is None:
            return {}
        tracker.validate_complete()
        return tracker.summaries()


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
        elif normalized == "ablate-working-memory":
            if not self.cfg.knowledge.working_memory_enabled:
                raise ValueError("ablate-working-memory requires working memory to be enabled")
            canonical = "ablate-working-memory"
            self.knowledge.working_memory_ablation_enabled = True
            self.entities.working_memory_q[:] = 0
            self.entities.working_memory_previous_observation_q[:] = 0
            self.entities.memory[:] = 0.0
            if self.gpu_runtime is not None:
                self.gpu_runtime.mark_entity_static_dirty()
            details = {"memory_coordinates_cleared": int(active.size * self.cfg.knowledge.working_memory_width)}
        elif normalized == "bypass-sparse-selection":
            if not self.cfg.knowledge.sparse_selection_enabled:
                raise ValueError("bypass-sparse-selection requires sparse selection to be enabled")
            canonical = "bypass-sparse-selection"
            self.knowledge.sparse_selection_ablation_enabled = True
            details = {"authority": "ephemeral-selector-only", "knowledge_copies_removed": 0}
        elif normalized == "neutralize-elastic-capacities":
            if not self.cfg.differentiation.enabled:
                raise ValueError(
                    "neutralize-elastic-capacities requires inherited elastic capacities"
                )
            canonical = "neutralize-elastic-capacities"
            self.capacity_ablation_enabled = True
            phenotype = self.entities.neutralize_capacity_phenotype(active)
            self.social.set_effective_capacities(
                active, self.entities.relation_capacity[active]
            )
            evicted = self.knowledge.enforce_capacities(
                alive=self.entities.alive,
                primary_subject_id=self.entities.primary_subject_id,
                knowledge_capacities=self.entities.knowledge_capacity_bytes,
            )
            if self.gpu_runtime is not None:
                self.gpu_runtime.mark_entity_static_dirty()
                self.gpu_runtime.mark_social_state_dirty()
            details = {
                "working_memory_dimensions": int(
                    np.asarray(phenotype.working_memory_dimensions)[0]
                ) if active.size else 0,
                "knowledge_capacity_bytes": int(
                    np.asarray(phenotype.knowledge_capacity_bytes)[0]
                ) if active.size else 0,
                "relation_slots": int(np.asarray(phenotype.relation_slots)[0])
                if active.size else 0,
                "knowledge_attention_slots": int(
                    np.asarray(phenotype.knowledge_attention_slots)[0]
                ) if active.size else 0,
                "knowledge_copies_evicted": int(evicted),
                "genotype_coordinates_modified": 0,
                "inheritance_modified": False,
                "future_offspring_expression_neutralized": True,
            }
        elif normalized == "neutralize-functional-module-coupling-output":
            if (
                not self.cfg.functional_modules.enabled
                or self.cfg.functional_modules.schema
                != "expression-gated-compositional-harvest-v2"
            ):
                raise ValueError(
                    "neutralize-functional-module-coupling-output requires "
                    "compositional functional modules"
                )
            canonical = "neutralize-functional-module-coupling-output"
            self.functional_module_coupling_ablation_enabled = True
            details = {
                "effective_output": "zero-feed-forward-coupling",
                "module_context_and_direct_output_preserved": True,
                "coupling_structure_cost_preserved": True,
                "genotype_coordinates_modified": 0,
                "inheritance_modified": False,
                "future_offspring_coupling_output_neutralized": True,
            }
        elif normalized == "neutralize-functional-modules":
            if not self.cfg.functional_modules.enabled:
                raise ValueError(
                    "neutralize-functional-modules requires enabled functional modules"
                )
            canonical = "neutralize-functional-modules"
            self.functional_modules_ablation_enabled = True
            self.functional_module_ablation_mask[:] = True
            details = {
                "effective_output": "zero-residual",
                "ablated_modules": list(range(int(self.cfg.functional_modules.module_count))),
                "genotype_coordinates_modified": 0,
                "inheritance_modified": False,
                "future_offspring_expression_neutralized": True,
            }
        elif normalized.startswith("neutralize-functional-module-"):
            if not self.cfg.functional_modules.enabled:
                raise ValueError(
                    f"{normalized} requires enabled functional modules"
                )
            try:
                module_index = int(normalized.rsplit("-", 1)[1])
            except ValueError as exc:
                raise ValueError(f"invalid functional module intervention: {normalized}") from exc
            if not 0 <= module_index < int(self.cfg.functional_modules.module_count):
                raise ValueError(
                    f"functional module index {module_index} is outside configured range"
                )
            canonical = f"neutralize-functional-module-{module_index}"
            self.functional_module_ablation_mask[module_index] = True
            self.functional_modules_ablation_enabled = bool(
                np.all(self.functional_module_ablation_mask)
            )
            details = {
                "effective_output": "zero-residual-for-selected-module",
                "ablated_module": module_index,
                "ablation_mask": self.functional_module_ablation_mask.astype(bool).tolist(),
                "genotype_coordinates_modified": 0,
                "inheritance_modified": False,
                "future_offspring_expression_neutralized": True,
            }
        elif normalized == "neutralize-resource-affinity":
            if (
                self.cfg.entities.resource_affinity_schema
                != "normalized-four-resource-affinity-v1"
            ):
                raise ValueError(
                    "neutralize-resource-affinity requires inherited resource affinity"
                )
            canonical = "neutralize-resource-affinity"
            self.resource_affinity_ablation_enabled = True
            details = {
                "effective_affinity_q": [AFFINITY_SCALE] * RESOURCE_CHANNELS,
                "genotype_coordinates_modified": 0,
                "inheritance_modified": False,
            }
        elif normalized == "neutralize-danger-evidence":
            if not danger_evidence_enabled(self.cfg):
                raise ValueError(
                    "neutralize-danger-evidence requires inherited danger evidence"
                )
            canonical = "neutralize-danger-evidence"
            self.danger_evidence_ablation_enabled = True
            details = {
                "effective_evidence_q": [DANGER_EVIDENCE_SCALE, DANGER_EVIDENCE_SCALE],
                "genotype_coordinates_modified": 0,
                "inheritance_modified": False,
            }
        elif normalized == "disable-knowledge-policy":
            if not self.cfg.knowledge.policy_influence_enabled:
                raise ValueError(
                    "disable-knowledge-policy requires knowledge policy influence"
                )
            canonical = "disable-knowledge-policy"
            self.knowledge_policy_ablation_enabled = True
            details = {
                "knowledge_copies_removed": 0,
                "knowledge_learning_enabled": bool(
                    self.cfg.knowledge.learning_enabled
                ),
            }
        elif normalized == "disable-knowledge-transfer":
            if not self.cfg.knowledge.enabled:
                raise ValueError(
                    "disable-knowledge-transfer requires dynamic knowledge"
                )
            canonical = "disable-knowledge-transfer"
            self.knowledge_transfer_ablation_enabled = True
            details = {
                "existing_knowledge_copies_removed": 0,
                "future_transfer_disabled": True,
            }
        elif normalized == "freeze-group-refresh":
            canonical = "freeze-group-refresh"
            self.group_refresh_ablation_enabled = True
            details = {
                "group_update_mode": self.cfg.social.group_update_mode,
                "group_labels_dirty_at_freeze": bool(
                    self.social.group_labels_dirty
                ),
                "last_group_update_tick": int(
                    self.social.last_group_update_tick
                ),
                "existing_group_labels_modified": False,
            }
        elif normalized == "freeze-genotype":
            canonical = "freeze-genotype"
            self.freeze_genotype = True
        elif normalized == "reverse-resource-geography":
            canonical = "reverse-resource-geography"
            self.environment.reverse_resource_spatial_orientation()
            if self.gpu_runtime is not None:
                self.gpu_runtime.reverse_resource_environment()
            details = {
                "rotation_degrees": 180,
                "resource_identity_permuted": False,
                "resource_effects_modified": False,
                "hazard_modified": False,
                "entity_state_modified": False,
                "future_seasonal_template_reversed": True,
            }
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

