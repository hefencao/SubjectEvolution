"""Machine-readable audit of group, spatial-region, and anchor protocols."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from ..cfg import load_config
from se.experiments.natural_event_matrix import load_manifest
from se.env.partition import SpatialRegionPartition
from se.policy import ParametricPolicy
from se.differentiation.functional import (
    compositional_modules_enabled,
    embodied_outputs_enabled,
    physiological_outputs_enabled,
    regulatory_outputs_enabled,
    resource_metabolism_modules_enabled,
    functional_module_coupling_count,
    functional_module_gene_count,
)
from se.differentiation.physiology import (
    physiology_gene_count,
    resource_metabolism_enabled,
    storage_constrained_intake_enabled,
)


SCHEMA = "structural-measurement-protocol-audit-v22"


def _canonical_sha256(payload: dict[str, Any]) -> str:
    encoded = json.dumps(
        payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def build_protocol_audit(
    config_path: str | Path,
    manifest_path: str | Path | None = None,
) -> dict[str, Any]:
    cfg = load_config(config_path)
    partition = SpatialRegionPartition(
        world_width=cfg.world.width,
        world_height=cfg.world.height,
        world_grid_x=cfg.world.grid_x,
        world_grid_y=cfg.world.grid_y,
        regions_x=cfg.run.spatial_stress_regions_x,
        regions_y=cfg.run.spatial_stress_regions_y,
        schema=cfg.run.spatial_stress_region_schema,
    )
    group = {
        "label_schema": cfg.social.group_label_schema,
        "edge_rule": (
            "directed relation slot is eligible when target is alive and materialized trust "
            "is at least trust_group_threshold"
        ),
        "successful_share_relation_rule": (
            "forward full trust gain plus reciprocal half-gain; thresholded directions may "
            "still differ after history and decay"
        ),
        "propagation_rule": (
            "initialize label as physical slot index; for each fixed round, replace an entity "
            "label by the minimum of its current label and labels reachable through eligible "
            "outgoing relation slots"
        ),
        "propagation_rounds": int(cfg.social.group_label_propagation_rounds),
        "trust_threshold": float(cfg.social.trust_group_threshold),
        "minimum_members": int(cfg.social.group_min_members),
        "group_token_rule": (
            "stable entity ID at the propagated minimum root slot; components below minimum "
            "members receive token 0 and remain ungrouped"
        ),
        "exact_component_claim": False,
        "interpretation": (
            "finite-round directed minimum-label propagation is an approximate candidate-group "
            "measurement, not a subject-existence verdict"
        ),
        "refresh": {
            "mode": cfg.social.group_update_mode,
            "period": int(cfg.social.group_update_period),
            "minimum_period": int(cfg.social.group_update_min_period),
            "maximum_period": int(cfg.social.group_update_max_period),
            "adaptive_triggers": [
                "initial snapshot",
                "topology-relevant relation change after minimum period",
                "predicted trust-threshold decay crossing after minimum period",
                "maximum staleness",
            ],
        },
    }
    atlas_partitions = [
        SpatialRegionPartition(
            world_width=cfg.world.width,
            world_height=cfg.world.height,
            world_grid_x=cfg.world.grid_x,
            world_grid_y=cfg.world.grid_y,
            regions_x=int(scale[0]),
            regions_y=int(scale[1]),
            schema=cfg.run.spatial_stress_region_schema,
        ).metadata()
        for scale in cfg.run.environment_atlas_scales
    ]
    payload: dict[str, Any] = {
        "schema": SCHEMA,
        "config_path": str(Path(config_path).resolve()),
        "group_label_protocol": group,
        "subject_structure_protocol": {
            "enabled": bool(cfg.run.subject_structure_diagnostics_enabled),
            "schema": cfg.run.subject_structure_diagnostics_schema,
            "identity_key": "stable entity ID membership",
            "transition_rule": (
                "connect previous and current candidate groups when they share at least one "
                "stable entity ID; classify zero/one/multiple overlap relations as "
                "formation, persistence, split, merge, or dissolution"
            ),
            "feedback_to_world": False,
            "interpretation": (
                "membership succession among candidate social structures; not an ontological "
                "identity theorem, arbitrary nesting graph, or subjecthood score"
            ),
        },
        "spatial_region_protocol": partition.metadata(),
        "resource_environment_protocol": {
            "schema": cfg.environment.schema,
            "channel_count": 4,
            "resource_capacities": list(cfg.environment.resource_capacity),
            "resource_regeneration": list(cfg.environment.resource_regeneration),
            "resource_effect_matrix": [list(row) for row in cfg.environment.resource_effect_matrix],
            "harvest_allocation_schema": cfg.entities.harvest_allocation_schema,
            "harvest_channel_multipliers": list(cfg.environment.harvest_channel_multipliers),
            "harvest_budget_semantics": (
                "fixed total extraction budget spent on one channel sampled from inherited affinity with state-free keyed randomness"
                if cfg.entities.harvest_allocation_schema
                == "affinity-sampled-exclusive-harvest-v1"
                else "fixed per-channel extraction requests"
            ),
            "independent_cycle_periods": list(cfg.environment.resource_cycle_periods),
            "cycle_amplitudes": list(cfg.environment.resource_cycle_amplitudes),
            "primary_wave_vectors": [list(row) for row in cfg.environment.resource_primary_wave_vectors],
            "secondary_wave_vectors": [list(row) for row in cfg.environment.resource_secondary_wave_vectors],
            "primary_wave_amplitudes": list(cfg.environment.resource_primary_wave_amplitudes),
            "secondary_wave_amplitudes": list(cfg.environment.resource_secondary_wave_amplitudes),
            "diffusion_rates": list(cfg.environment.resource_diffusion_rates),
            "entity_aware": False,
            "environment_generation_entity_aware": False,
            "harvest_demand_entity_aware": bool(
                cfg.entities.harvest_allocation_schema == "affinity-sampled-exclusive-harvest-v1"
            ),
            "harvest_request_observation": {
                "schema": "explicit-requested-harvest-window-v1",
                "requested_before_environment_allocation": True,
                "realized_after_environment_allocation": True,
                "scale_composition_separation": True,
            },
            "lineage_aware": False,
            "group_aware": False,
            "diversity_protection": False,
            "interpretation": (
                "fixed four-channel physical interface with independently configured spatial, "
                "temporal, and diffusion dynamics; configuration can create environmental axes "
                "but does not guarantee evolved ecological differentiation"
            ),
        },
        "d1_factorial_protocol": {
            "schema": "d1-affinity-capacity-factorial-plan-v1",
            "branches": {
                "baseline": [],
                "affinity-neutral": ["neutralize-resource-affinity"],
                "capacity-neutral": ["neutralize-elastic-capacities"],
                "combined-neutral": [
                    "neutralize-resource-affinity",
                    "neutralize-elastic-capacities",
                ],
            },
            "paired_randomness": True,
            "genotype_preserved": True,
            "effect_sign": "expressed phenotype minus neutralized branch",
            "interaction": "baseline - affinity-neutral - capacity-neutral + combined-neutral",
            "interpretation": (
                "local checkpoint-phase effects over a fixed horizon; not universal necessity"
            ),
        },
        "differentiation_capacity_protocol": {
            "enabled": bool(cfg.differentiation.enabled),
            "schema": cfg.differentiation.schema,
            "fixed_physical_layout": {
                "working_memory_dimensions": int(cfg.knowledge.working_memory_width),
                "knowledge_bytes": int(cfg.knowledge.holder_capacity_bytes),
                "relation_slots": int(cfg.entities.relation_slots),
                "knowledge_attention_slots": int(cfg.knowledge.attention_slots_per_tick),
            },
            "effective_capacity_bounds": {
                "working_memory_dimensions": [
                    int(cfg.differentiation.working_memory_min_dimensions),
                    int(cfg.differentiation.working_memory_max_dimensions),
                ],
                "knowledge_bytes": [
                    int(cfg.differentiation.knowledge_min_bytes),
                    int(cfg.differentiation.knowledge_max_bytes),
                ],
                "relation_slots": [
                    int(cfg.differentiation.relation_min_slots),
                    int(cfg.differentiation.relation_max_slots),
                ],
                "knowledge_attention_slots": [
                    int(cfg.differentiation.attention_min_slots),
                    int(cfg.differentiation.attention_max_slots),
                ],
            },
            "knowledge_quantum_bytes": int(cfg.differentiation.knowledge_quantum_bytes),
            "gene_layout": {
                "start": (
                    int(ParametricPolicy.capacity_gene_start(cfg))
                    if cfg.differentiation.enabled else None
                ),
                "count": 4 if cfg.differentiation.enabled else 0,
                "mapping": (
                    "clip inherited float gene to [-1,1], map monotonically to an integer "
                    "capacity level, then mask a fixed physical tensor layout"
                ),
            },
            "mutation": {
                "probability": float(cfg.differentiation.mutation_probability),
                "std": float(cfg.differentiation.mutation_std),
            },
            "maintenance_energy": {
                "per_working_memory_dimension": float(cfg.differentiation.maintenance_energy_per_working_memory_dimension),
                "per_knowledge_byte": float(cfg.differentiation.maintenance_energy_per_knowledge_byte),
                "per_relation_slot": float(cfg.differentiation.maintenance_energy_per_relation_slot),
                "per_attention_slot": float(cfg.differentiation.maintenance_energy_per_attention_slot),
            },
            "development_energy": {
                "per_working_memory_dimension": float(cfg.differentiation.development_energy_per_working_memory_dimension),
                "per_knowledge_byte": float(cfg.differentiation.development_energy_per_knowledge_byte),
                "per_relation_slot": float(cfg.differentiation.development_energy_per_relation_slot),
                "per_attention_slot": float(cfg.differentiation.development_energy_per_attention_slot),
            },
            "world_feedback": bool(cfg.differentiation.enabled),
            "preset_role_labels": False,
            "diversity_protection": False,
            "interpretation": (
                "four inherited capacities alter the usable scale and explicit cost of existing "
                "memory, knowledge, relationship, and attention mechanisms; they do not add a "
                "predefined ecological role or guarantee adaptive differentiation"
            ),
        },
        "functional_module_protocol": {
            "enabled": bool(cfg.functional_modules.enabled),
            "schema": cfg.functional_modules.schema,
            "module_count": int(cfg.functional_modules.module_count),
            "gene_start": (
                int(ParametricPolicy.functional_module_gene_start(cfg))
                if cfg.functional_modules.enabled else None
            ),
            "gene_count": int(functional_module_gene_count(cfg)),
            "architecture_class": (
                "feed-forward-regulatory-resource-metabolism"
                if resource_metabolism_modules_enabled(cfg)
                else "feed-forward-regulatory-physiology"
                if regulatory_outputs_enabled(cfg)
                else "feed-forward-compositional-physiological"
                if physiological_outputs_enabled(cfg)
                else "feed-forward-compositional-embodied"
                if embodied_outputs_enabled(cfg)
                else (
                    "feed-forward-compositional"
                    if compositional_modules_enabled(cfg)
                    else "independent-additive"
                )
            ),
            "input_schema": cfg.functional_modules.input_schema,
            "inputs": [
                "bias",
                "energy deficit",
                "integrity deficit",
                "material deficit",
                "information-store deficit",
                "fertility deficit",
                "four local normalized resource channels",
                *(
                    [
                        "oxygenation deficit", "tissue deficit", "structure deficit",
                        "metabolic fatigue", "mobilization messenger",
                        "maintenance messenger", "messenger precursor",
                        "local oxygen availability", "local terrain resistance",
                        "local mechanical wear",
                    ]
                    if regulatory_outputs_enabled(cfg)
                    else [
                        "oxygenation deficit", "tissue deficit", "structure deficit",
                        "local oxygen availability", "local terrain resistance",
                        "local mechanical wear",
                    ]
                    if physiological_outputs_enabled(cfg) else []
                ),
                *(
                    ["four normalized internal raw-resource store occupancies"]
                    if resource_metabolism_modules_enabled(cfg)
                    else []
                ),
            ],
            "output_schema": cfg.functional_modules.output_schema,
            "output_scope": (
                "zero-sum harvest residual plus oxygen-uptake modulation, mobilization-bus "
                "stimulation, maintenance-bus stimulation, and sensory-attention modulation; "
                "actual execution emerges from inherited physiology, bounded state and abiotic supply"
                if regulatory_outputs_enabled(cfg)
                else "zero-sum harvest residual plus perfusion, contractile, sensory, and repair drives; "
                "locomotion, signal, and repair emerge from body state and abiotic fields"
                if physiological_outputs_enabled(cfg)
                else "zero-sum residual over four harvest-channel request weights plus "
                "bounded locomotion-power, field-signal-power, and material-to-integrity repair outputs"
                if embodied_outputs_enabled(cfg)
                else "zero-sum residual over four harvest-channel request weights"
            ),
            "coupling_schema": cfg.functional_modules.coupling_schema,
            "coupling_link_count": int(functional_module_coupling_count(cfg)),
            "hierarchy_depth_by_module": list(
                range(int(cfg.functional_modules.module_count))
            ),
            "coupling_semantics": (
                "lower-slot signals multiplicatively modulate downstream contextual "
                "activation; direct module routing remains available at every slot"
                if compositional_modules_enabled(cfg)
                else "no inter-module signal path; all slot outputs add independently"
            ),
            "action_selection": False,
            "assimilation_affinity_modified": False,
            "resource_gradient_utility_modified": False,
            "new_world_physics": bool(
                embodied_outputs_enabled(cfg)
                or physiological_outputs_enabled(cfg)
                or regulatory_outputs_enabled(cfg)
            ),
            "embodied_output_semantics": {
                "enabled": bool(embodied_outputs_enabled(cfg)),
                "schema": cfg.functional_modules.output_schema,
                "locomotion": "bounded multiplier on existing movement speed with quadratic movement-energy accounting",
                "field_signal": "bounded multiplier on existing field-signal strength with quadratic signal-energy accounting",
                "repair": "positive drive converts explicitly debited material and energy into bounded integrity restoration",
                "new_action_kind": False,
                "resource_or_energy_created": False,
                "preset_ecological_role": False,
            },
            "physiological_output_semantics": {
                "enabled": bool(physiological_outputs_enabled(cfg)),
                "body_state": ["oxygenation", "tissue_condition", "structure_condition"],
                "module_drives": ["perfusion", "contractile", "sensory", "repair"],
                "abiotic_fields": ["oxygen availability", "terrain resistance", "mechanical wear"],
                "derived_effects": ["locomotion", "signal reception/emission", "repair"],
                "conservation": "repair debits material, energy, and oxygen; damage changes tissue/structure/integrity",
                "new_action_kind": False,
                "biological_hazard_source": False,
                "diversity_reward_or_protection": False,
                "preset_ecological_role": False,
            },
            "regulatory_physiology_semantics": {
                "enabled": bool(regulatory_outputs_enabled(cfg)),
                "physiology_schema": cfg.physiology.schema,
                "inherited_parameter_count": (
                    int(physiology_gene_count(cfg))
                    if regulatory_outputs_enabled(cfg)
                    else 0
                ),
                "module_requests": [
                    "oxygen uptake modulation",
                    "mobilization messenger stimulation",
                    "maintenance messenger stimulation",
                    "sensory attention modulation",
                ],
                "dynamic_states": [
                    "oxygenation", "tissue condition", "structure condition",
                    "metabolic fatigue", "mobilization messenger",
                    "maintenance messenger", "shared messenger precursor",
                ],
                "intent_execution_separation": True,
                "zero_module_output_semantics": (
                    "basal uptake and attention with no stimulated messenger synthesis"
                ),
                "messenger_buses": (
                    "two independently inherited synthesis/decay/receptor pathways sharing "
                    "one finite precursor pool"
                ),
                "fixed_lifetime_weights": True,
                "online_hebbian_learning": False,
                "computation_cost": "actual activation and route load debit energy and oxygen",
                "conservative_flow_schema": "transport-metabolism-messenger-tissue-v3",
                "legacy_replay_schema": "transport-metabolism-messenger-tissue-v2",
                "flow_ledger_invariant": (
                    "all reported flow magnitudes are finite and non-negative"
                ),
                "energy_debt_semantics": (
                    "physiology preserves negative energy until world starvation settlement"
                ),
                "counterfactual_interfaces": [
                    "regulatory output neutralization",
                    "messenger receptor blockade",
                    "bounded state clamp",
                ],
                "named_organs_or_hormones": False,
                "conservation": (
                    "messenger synthesis debits precursor and energy; precursor recovery debits "
                    "material; repair debits material, energy and oxygen"
                ),
            },
            "resource_metabolism_semantics": {
                "enabled": bool(resource_metabolism_enabled(cfg)),
                "physiology_schema": cfg.physiology.schema,
                "functional_schema": cfg.functional_modules.schema,
                "raw_resource_channels": 4,
                "inherited_store_capacity_genes": 4 if resource_metabolism_enabled(cfg) else 0,
                "inherited_conversion_capacity_genes": 4 if resource_metabolism_enabled(cfg) else 0,
                "base_store_capacity": list(cfg.physiology.resource_store_base_capacity),
                "base_conversion_per_tick": list(cfg.physiology.resource_conversion_per_tick),
                "store_decay_per_tick": list(cfg.physiology.resource_store_decay_per_tick),
                "harvest_enters_store_before_body": bool(resource_metabolism_enabled(cfg)),
                "minimum_conversion_delay_ticks": 1 if resource_metabolism_enabled(cfg) else 0,
                "same_tick_harvest_body_effect": False if resource_metabolism_enabled(cfg) else True,
                "resource_intake_schema": (
                    "storage-room-constrained-preharvest-v2"
                    if storage_constrained_intake_enabled(cfg)
                    else "unconstrained-post-harvest-store-v1"
                ),
                "storage_constrained_preharvest": bool(
                    storage_constrained_intake_enabled(cfg)
                ),
                "capacity_rejected_resource_remains_external": bool(
                    storage_constrained_intake_enabled(cfg)
                ),
                "policy_resource_utility_respects_store_room": bool(
                    storage_constrained_intake_enabled(cfg)
                ),
                "legacy_post_harvest_overflow_replay": bool(
                    resource_metabolism_enabled(cfg)
                    and not storage_constrained_intake_enabled(cfg)
                ),
                "store_occupancy_visible_to_operators": bool(
                    resource_metabolism_modules_enabled(cfg)
                ),
                "death_store_fate": (
                    "explicit dissipative death loss; no detritus recycling yet"
                    if resource_metabolism_enabled(cfg)
                    else "not applicable"
                ),
                "ledger": (
                    "stored = converted + decay + death loss + final living store"
                    if resource_metabolism_enabled(cfg)
                    else "not applicable"
                ),
                "equal_channel_base_parameters": bool(
                    len(set(cfg.physiology.resource_store_base_capacity)) <= 1
                    and len(set(cfg.physiology.resource_conversion_per_tick)) <= 1
                    and len(set(cfg.physiology.resource_store_decay_per_tick)) <= 1
                ),
                "preset_resource_role": False,
                "diversity_reward_or_protection": False,
            },
            "resource_metabolism_experiment": {
                "plan_schema": "d3-resource-metabolism-plan-v1",
                "result_schema": "d3-resource-metabolism-results-v1",
                "single_active_population_per_seed": True,
                "pass_fail_module_gate": False,
                "minimum_conversion_delay_ticks": 1,
                "strict_raw_store_ledger": True,
                "legacy_intake_semantics": "post-harvest bounded storage with overflow loss",
                "module_copy_number_changed": False,
                "stable_niche_claim": False,
            },
            "conservative_intake_experiment": {
                "plan_schema": "d3-conservative-intake-plan-v1",
                "result_schema": "d3-conservative-intake-results-v1",
                "single_active_population_per_seed": True,
                "pass_fail_module_gate": False,
                "preharvest_request_capped_by_inherited_store_room": True,
                "affinity_adjusted_capacity_in_raw_environment_units": True,
                "capacity_rejected_resource_remains_external": True,
                "post_assimilation_overflow_forbidden": True,
                "policy_resource_utility_respects_store_room": True,
                "strict_store_ledger": True,
                "module_copy_number_changed": False,
                "stable_niche_claim": False,
            },
            "expression_threshold": float(cfg.functional_modules.expression_threshold),
            "maximum_residual_fraction": float(cfg.functional_modules.max_residual_fraction),
            "maintenance_energy_per_expression": float(
                cfg.functional_modules.maintenance_energy_per_expression
            ),
            "development_energy_per_expression": float(
                cfg.functional_modules.development_energy_per_expression
            ),
            "maintenance_energy_per_coupling_weight": float(
                cfg.functional_modules.maintenance_energy_per_coupling_weight
            ),
            "development_energy_per_coupling_weight": float(
                cfg.functional_modules.development_energy_per_coupling_weight
            ),
            "maintenance_energy_per_embodied_weight": float(
                cfg.functional_modules.maintenance_energy_per_embodied_weight
            ),
            "development_energy_per_embodied_weight": float(
                cfg.functional_modules.development_energy_per_embodied_weight
            ),
            "neutralization_interventions": {
                "coupling_output": "neutralize-functional-module-coupling-output",
                "embodied_output": "neutralize-functional-module-embodied-output",
                "physiology_output": "neutralize-functional-module-physiology-output",
                "all_modules": "neutralize-functional-modules",
                "per_module": [
                    f"neutralize-functional-module-{index}"
                    for index in range(int(cfg.functional_modules.module_count))
                ],
            },
            "contribution_diagnostics": {
                "schema": (
                    "functional-module-contribution-audit-v5"
                    if regulatory_outputs_enabled(cfg)
                    else "functional-module-contribution-audit-v4"
                    if physiological_outputs_enabled(cfg)
                    else "functional-module-contribution-audit-v3"
                    if embodied_outputs_enabled(cfg)
                    else "functional-module-contribution-audit-v2"
                ),
                "per_module_gate": True,
                "per_module_activation": True,
                "isolated_output_effect": True,
                "contribution_effective_count": True,
                "cancellation_fraction": True,
                "coupling_weight_effective_dimensions": True,
                "mediated_signal_by_hierarchy_level": True,
                "amplification_and_suppression": True,
                "embodied_output_effective_dimensions": bool(embodied_outputs_enabled(cfg)),
                "combined_output_basis_effective_dimensions": bool(
                    embodied_outputs_enabled(cfg)
                or physiological_outputs_enabled(cfg)
                or regulatory_outputs_enabled(cfg)
                ),
                "physiology_output_effective_dimensions": bool(
                    physiological_outputs_enabled(cfg) or regulatory_outputs_enabled(cfg)
                ),
                "feedback_to_world": False,
            },
            "architecture_capability_experiment": {
                "plan_schema": "d2-compositional-capability-plan-v1",
                "result_schema": "d2-compositional-capability-results-v1",
                "branches": ["composition-active", "coupling-neutral"],
                "same_v2_genome_and_mutation_streams": True,
                "coupling_structure_cost_retained_in_neutral_branch": True,
                "module_copy_number_changed": False,
                "ecological_niche_claim": False,
            },
            "embodied_capability_experiment": {
                "plan_schema": "d2-embodied-capability-plan-v1",
                "result_schema": "d2-embodied-capability-results-v1",
                "branches": ["embodied-active", "embodied-neutral"],
                "same_v3_genome_and_mutation_streams": True,
                "harvest_and_coupling_output_active_in_both_branches": True,
                "embodied_router_structure_cost_retained_in_neutral_branch": True,
                "module_copy_number_changed": False,
                "ecological_niche_claim": False,
            },
            "physiological_ecology_experiment": {
                "plan_schema": "d2-physiological-ecology-plan-v1",
                "result_schema": "d2-physiological-ecology-results-v1",
                "single_active_population_per_seed": True,
                "pass_fail_expression_gate": False,
                "independent_abiotic_fields": True,
                "dynamic_body_state": True,
                "module_copy_number_changed": False,
                "food_chain_complete": False,
                "stable_niche_claim": False,
            },
            "regulatory_physiology_experiment": {
                "plan_schema": "d2-regulatory-physiology-plan-v2",
                "result_schema": "d2-regulatory-physiology-results-v2",
                "legacy_result_schema_readable": "d2-regulatory-physiology-results-v1",
                "flow_assessment_schema": (
                    "d2-regulatory-physiology-flow-assessment-v1"
                ),
                "single_active_population_per_seed": True,
                "pass_fail_expression_gate": False,
                "fixed_lifetime_weights": True,
                "finite_messenger_precursor": True,
                "computation_and_execution_costed": True,
                "module_copy_number_changed": False,
                "stable_niche_claim": False,
            },
            "known_architecture_limit": (
                "The v1 schema supports only independent additive harvest routing. The v2 "
                "schema adds inherited hierarchy and joint dependence; v3 adds conserved embodied "
                "ports. The archived v4 coarse-drive schema is retained for replay only. The v5 "
                "schema separates regulatory intent from inherited transport, metabolism, finite "
                "messenger turnover, fatigue and repair execution. The v6 functional / v4 physiology "
                "pair adds inherited bounded raw-resource storage and delayed conversion but retains "
                "archived post-harvest overflow loss. The v6 functional / v5 physiology pair constrains "
                "environmental extraction by inherited free store room before commit, so rejected raw "
                "resource remains external. It still lacks detritus recycling, spatial separation of "
                "collection and processing, trophic transfer, a completed food chain, dynamic topology "
                "and stable niche proof."
            ),
            "leave_one_out_protocol": {
                "plan_schema": "d2-module-leave-one-out-plan-v1",
                "result_schema": "d2-module-leave-one-out-results-v2",
                "branches": [
                    "baseline",
                    "all-modules-neutral",
                    *[
                        f"module-{index}-neutral"
                        for index in range(int(cfg.functional_modules.module_count))
                    ],
                ],
                "paired_randomness": True,
                "genotype_preserved": True,
                "immediate_footprint": {
                    "schema": "d2-module-immediate-footprint-v1",
                    "conditional_action": "HARVEST",
                    "pre_step": True,
                    "lineage_resolved": True,
                    "feedback_to_world": False,
                },
            },
            "effect_qualification": {
                "schema": "d2-module-effect-assessment-v2",
                "numerical_tolerance": 1e-12,
                "directional_replicates": 4,
                "minimum_seeds": 2,
                "footprint_preference_changed_fraction": 0.01,
                "footprint_channel_changed_fraction": 0.005,
                "minimum_lineage_members": 8,
                "lineage_guard_effective_count": 4.0,
                "duplication_requires": [
                    "practical downstream magnitude",
                    "replication across at least two seeds",
                    "immediate checkpoint footprint",
                    "cross-lineage footprint",
                    "positive ecological persistence or preregistered phase tradeoff",
                    "no dominant-lineage guard failure",
                ],
            },
            "lineage_balanced_pair_protocol": {
                "plan_schema": "d2-lineage-paired-plan-v2",
                "accepted_plan_schemas": [
                    "d2-lineage-paired-plan-v1",
                    "d2-lineage-paired-plan-v2",
                ],
                "result_schema": "d2-lineage-paired-results-v2",
                "accepted_result_schemas": [
                    "d2-lineage-paired-results-v1",
                    "d2-lineage-paired-results-v2",
                ],
                "default_priority_modules": [2, 3],
                "selection_rule": "largest pre-intervention lineages by membership",
                "selection_uses_endpoint_response": False,
                "branches": [
                    "baseline",
                    "output-neutral with expression cost retained",
                    "expression-neutral with output and expression cost removed",
                ],
                "target_scope": "one fixed module within one genetic lineage",
                "same_lineage_descendants_treated": True,
                "genotype_preserved": True,
                "lineage_membership_preserved": True,
                "paired_randomness": True,
                "equal_inferential_weight_per_lineage_pair": True,
                "abundance_reweighting_inside_world": False,
                "diversity_protection": False,
                "effect_assessment": {
                    "schema": "d2-lineage-paired-assessment-v1",
                    "continuation_effect": "output_routing_effect",
                    "minimum_seeds": 2,
                    "minimum_non_dominant_lineage_identities": 2,
                    "same_material_direction_required": True,
                    "cost_only_signal_qualifies": False,
                    "confirmation_horizon_ticks": 300,
                    "confirmation_selection_rule": "module-level-screen-preserve-all-preselected-checkpoint-lineage-pairs-v1",
                    "outcome_conditioned_pair_selection": False,
                    "copy_number_remains_guarded": True,
                },
                "temporal_mediation_audit": {
                    "plan_schema": "d2-lineage-mediation-plan-v1",
                    "result_schema": "d2-lineage-mediation-results-v1",
                    "assessment_schema": "d2-lineage-mediation-assessment-v1",
                    "selection_rule": "module-level-confirmed-output-preserve-all-preselected-checkpoint-lineage-pairs-v1",
                    "default_observation_offsets": [30, 60, 120, 180, 240, 300],
                    "branches": [
                        "baseline",
                        "output-neutral with expression cost retained",
                        "expression-neutral with output and expression cost removed",
                    ],
                    "read_only_tick_observer": True,
                    "measured_mediators": [
                        "target-lineage energy stock and quartiles",
                        "source survivors and living descendants",
                        "births and deaths by cause",
                        "fertility and reproduction readiness",
                        "post-intervention harvested energy",
                        "post-intervention shared energy received",
                    ],
                    "offsets_are_independent_replicates": False,
                    "minimum_seeds_per_offset": 2,
                    "minimum_non_dominant_lineage_identities_per_offset": 2,
                    "mean_energy_alone_qualifies_as_ecological_benefit": False,
                    "outcome_conditioned_pair_selection": False,
                    "copy_number_remains_guarded": True,
                },
                "source_population_reconstitution": {
                    "plan_schema": "d2-source-population-plan-v1",
                    "result_schema": "d2-source-population-results-v1",
                    "assessment_schema": "d2-source-population-assessment-v2",
                    "arms": [
                        "natural-abundance-control",
                        "equal-lineage-reconstitution",
                    ],
                    "selection_rule": "cross-run top pre-intervention lineages by abundance; no response-conditioned lineage selection",
                    "founder_transfer": "genotype only from unique living donors without replacement",
                    "reset_state": [
                        "physiology",
                        "age and generation",
                        "knowledge",
                        "social state",
                        "spatial position",
                    ],
                    "same_total_founders_across_arms": True,
                    "ongoing_lineage_protection": False,
                    "lineage_aware_world_rules": False,
                    "module_copy_number_changed": False,
                    "qualification": {
                        "minimum_effective_lineages": 4.0,
                        "maximum_dominant_lineage_fraction": 0.5,
                        "minimum_lineages_above_member_floor": 4,
                        "minimum_expressed_lineages_per_candidate_module": 4,
                        "minimum_observed_panel_seeds_for_exploratory_decision": 3,
                        "minimum_qualified_panel_seeds_per_exploratory_phase": 2,
                        "major_conclusion_minimum_seeds_per_phase": 10,
                        "uncertainty_interval": "two-sided-wilson-95-v1",
                    },
                    "charter_interpretation": {
                        "ten_seed_floor_applies_to_major_conclusions": True,
                        "ten_seed_floor_applies_to_every_exploratory_audit": False,
                        "three_seed_paired_gate_allowed": True,
                    },
                    "copy_number_remains_guarded": True,
                },
                "source_population_causal_reaudit": {
                    "plan_schema": "d2-source-population-causal-plan-v1",
                    "result_schema": "d2-source-population-causal-results-v1",
                    "assessment_schema": "d2-source-population-causal-assessment-v1",
                    "module_indices": [3],
                    "default_screen_horizon_ticks": 120,
                    "confirmation_horizon_ticks": 300,
                    "checkpoint_selection": "phase-qualified equal-lineage final checkpoints only",
                    "lineage_selection": "all lineages passing preregistered member and expression floors",
                    "branches": [
                        "baseline",
                        "output-neutral with expression cost retained",
                        "expression-neutral with output and expression cost removed",
                    ],
                    "response_conditioned_panel_selection": False,
                    "response_conditioned_lineage_selection": False,
                    "general_source_population_claim": False,
                    "module_copy_number_changed": False,
                    "copy_number_remains_guarded": True,
                },
            },
            "preset_role_labels": False,
            "diversity_protection": False,
            "interpretation": (
                "a bounded D2-A test of inherited input-expression-output routing within "
                "the already validated resource-acquisition interface; not a general organ "
                "generator or a claim of new physical functionality"
            ),
        },
        "d4_niche_reversal_protocol": {
            "plan_schema": "d4-niche-reversal-plan-v1",
            "result_schema": "d4-niche-reversal-results-v1",
            "assessment_schema": "d4-niche-reversal-assessment-v2",
            "source_gate": "explicit D2-H non-replication stop recommendation",
            "default_screen_horizon_ticks": 120,
            "confirmation_horizon_ticks": 300,
            "checkpoint_selection": "all phase-qualified redesigned-source checkpoints retained from D2-H",
            "lineage_selection": "all preregistered source-checkpoint lineages; no response-conditioned pruning",
            "branches": {
                "baseline": [],
                "resource-reversed": ["reverse-resource-geography"],
                "affinity-neutral": ["neutralize-resource-affinity"],
                "joint-neutral": [
                    "reverse-resource-geography",
                    "neutralize-resource-affinity",
                ],
            },
            "primary_interaction": "(baseline - resource-reversed) - (affinity-neutral - joint-neutral)",
            "resource_reversal": {
                "rotation_degrees": 180,
                "current_resource_fields_rotated": True,
                "future_seasonal_template_rotated": True,
                "resource_identity_changed": False,
                "resource_effect_matrix_changed": False,
                "hazard_changed": False,
                "mortality_trace_changed": False,
            },
            "paired_randomness": True,
            "genotype_preserved": True,
            "lineage_membership_preserved": True,
            "minimum_independent_panel_seeds": 2,
            "minimum_non_dominant_lineage_identities": 2,
            "source_exposure_diagnostic": "pre-intervention affinity-specific utility difference between original and 180-degree-rotated resource geography",
            "source_exposure_is_independent_causal_evidence": False,
            "screen_can_authorize": (
                "longer environment-matching confirmation only when repeated interaction "
                "is also aligned with preregistered source exposure and spans multiple "
                "dominant affinity channels"
            ),
            "stable_niche_claim_requires": [
                "persistent environment-matching interaction",
                "stable coexistence",
                "ecotype or phenotype-cohort removal",
                "map-scale and spatial-template checks",
            ],
            "module_copy_number_changed": False,
            "routing_vocabulary_changed": False,
            "diversity_protection": False,
        },
        "environment_atlas_protocol": {
            "enabled": bool(cfg.run.environment_atlas_diagnostics_enabled),
            "schema": cfg.run.environment_atlas_diagnostics_schema,
            "scales": atlas_partitions,
            "signature": [
                "four capacity-normalized resource means",
                "hazard mean",
                "mortality-trace mean",
            ],
            "resource_only_metrics": [
                "resource effective dimensions",
                "resource channel correlation matrix",
                "mean/max absolute resource channel correlation",
            ] if cfg.run.environment_atlas_diagnostics_schema == "multiscale-subject-environment-atlas-v2" else [],
            "subject_exposure_association": (
                "between-label share of realized regional signature variance for genetic "
                "lineages and observed social groups"
            ),
            "feedback_to_world": False,
            "interpretation": (
                "descriptive multiscale environment heterogeneity and exposure segregation; "
                "not environmental causation or subjecthood"
            ),
        },
        "anchor_protocol": None,
    }
    if manifest_path is not None:
        manifest = load_manifest(manifest_path)
        selection = dict(manifest.get("selection_protocol", {}))
        legacy = manifest.get("selection_schema") == "exposure-only-local-peak-selection-v1"
        payload["anchor_protocol"] = {
            "manifest_path": str(Path(manifest_path).resolve()),
            "manifest_schema": manifest.get("schema"),
            "manifest_sha256": manifest.get("plan_sha256"),
            "selection_schema": manifest.get("selection_schema"),
            "event_kinds": selection.get("event_kinds", []),
            "quantile": selection.get("event_quantile"),
            "maximum_events_per_kind_per_run": selection.get(
                "max_events_per_kind_per_run"
            ),
            "minimum_gap_windows": selection.get("min_gap_windows"),
            "minimum_region_alive": selection.get("min_region_alive"),
            "candidate_rule": selection.get("candidate_rule")
            or (
                "per-region within-run quantile threshold; interior local maximum; "
                "minimum gap enforced independently within each region"
            ),
            "ranking_rule": selection.get("ranking_rule")
            or "descending within-region z-score, then earlier tick, then lower region ID",
            "region_diversity_rule": selection.get("region_diversity_rule")
            or (
                "prefer distinct regions until max_events; reuse a region only after all "
                "candidate-bearing regions are represented"
            ),
            "checkpoint_rule": (
                "choose the latest full checkpoint with checkpoint_tick < event_tick"
            ),
            "horizon_ticks": manifest.get("horizon_ticks"),
            "outcome_blind_selection": bool(
                not selection.get("post_event_outcomes_used_for_selection", False)
                and not selection.get("analysis_summary_used_for_selection", False)
            ),
            "cross_event_z_score_comparable": False,
            "legacy_rule_text_inferred": legacy,
            "region_partition_audit": manifest.get("region_partition_audit"),
            "interpretation": (
                "anchors are high local exposure peaks conditional on observed natural events; "
                "they are not randomized exposure assignments"
            ),
        }
    payload["audit_sha256"] = _canonical_sha256(payload)
    return payload


def render_markdown(payload: dict[str, Any]) -> str:
    group = payload["group_label_protocol"]
    region = payload["spatial_region_protocol"]
    subject_structure = payload["subject_structure_protocol"]
    atlas = payload["environment_atlas_protocol"]
    resource = payload["resource_environment_protocol"]
    differentiation = payload["differentiation_capacity_protocol"]
    lines = [
        "# Structural measurement protocol audit",
        "",
        f"Schema: `{payload['schema']}`",
        f"Audit SHA-256: `{payload['audit_sha256']}`",
        "",
        "## Group label",
        "",
        f"- schema: `{group['label_schema']}`",
        f"- threshold / rounds / minimum members: {group['trust_threshold']} / "
        f"{group['propagation_rounds']} / {group['minimum_members']}",
        f"- refresh mode: `{group['refresh']['mode']}`",
        f"- propagation: {group['propagation_rule']}",
        f"- token: {group['group_token_rule']}",
        f"- boundary: {group['interpretation']}",
        "",
        "## Subject succession",
        "",
        f"- enabled / schema: {subject_structure['enabled']} / "
        f"`{subject_structure['schema']}`",
        f"- identity key: {subject_structure['identity_key']}",
        f"- transition rule: {subject_structure['transition_rule']}",
        f"- boundary: {subject_structure['interpretation']}",
        "",
        "## Spatial regions",
        "",
        f"- schema: `{region['schema']}`",
        f"- grid: {region['regions_x']} × {region['regions_y']} ({region['region_count']} regions)",
        f"- physical region: {region['physical_region_width']} × {region['physical_region_height']}",
        f"- world cells per region: {region['world_cells_per_region_x']} × "
        f"{region['world_cells_per_region_y']}",
        f"- grid-aligned: {region['world_grid_aligned']}",
        f"- map-size semantics: {region['map_size_semantics']}",
        "",
        "## Resource environment",
        "",
        f"- schema / channels: `{resource['schema']}` / {resource['channel_count']}",
        f"- harvest allocation: `{resource['harvest_allocation_schema']}`",
        f"- harvest budget semantics: {resource['harvest_budget_semantics']}",
        f"- request observation: `{resource['harvest_request_observation']['schema']}`; "
        f"requested-before-allocation={resource['harvest_request_observation']['requested_before_environment_allocation']}; "
        f"realized-after-allocation={resource['harvest_request_observation']['realized_after_environment_allocation']}; "
        f"scale/composition separated={resource['harvest_request_observation']['scale_composition_separation']}",
        f"- independent cycle periods: {resource['independent_cycle_periods']}",
        f"- primary wave vectors: {resource['primary_wave_vectors']}",
        f"- diffusion rates: {resource['diffusion_rates']}",
        f"- environment generation entity/lineage/group aware: {resource['environment_generation_entity_aware']} / {resource['lineage_aware']} / {resource['group_aware']}",
        f"- harvest demand phenotype-aware: {resource['harvest_demand_entity_aware']}",
        f"- boundary: {resource['interpretation']}",
        "",
        "## Elastic capacities",
        "",
        f"- enabled / schema: {differentiation['enabled']} / `{differentiation['schema']}`",
        f"- physical maxima: {differentiation['fixed_physical_layout']}",
        f"- effective bounds: {differentiation['effective_capacity_bounds']}",
        f"- gene start/count: {differentiation['gene_layout']['start']} / {differentiation['gene_layout']['count']}",
        f"- mutation probability/std: {differentiation['mutation']['probability']} / {differentiation['mutation']['std']}",
        f"- maintenance energy: {differentiation['maintenance_energy']}",
        f"- development energy: {differentiation['development_energy']}",
        f"- preset roles / diversity protection: {differentiation['preset_role_labels']} / {differentiation['diversity_protection']}",
        f"- boundary: {differentiation['interpretation']}",
        "",
        "## D1 affinity × capacity factorial",
        "",
        f"- schema: `{payload['d1_factorial_protocol']['schema']}`",
        f"- branches: {payload['d1_factorial_protocol']['branches']}",
        f"- paired randomness / genotype preserved: "
        f"{payload['d1_factorial_protocol']['paired_randomness']} / "
        f"{payload['d1_factorial_protocol']['genotype_preserved']}",
        f"- expression effect sign: {payload['d1_factorial_protocol']['effect_sign']}",
        f"- interaction contrast: {payload['d1_factorial_protocol']['interaction']}",
        f"- boundary: {payload['d1_factorial_protocol']['interpretation']}",
        "",
        "## D2-A contextual functional modules",
        "",
        f"- enabled / schema: {payload['functional_module_protocol']['enabled']} / "
        f"`{payload['functional_module_protocol']['schema']}`",
        f"- module count / gene start / gene count: {payload['functional_module_protocol']['module_count']} / "
        f"{payload['functional_module_protocol']['gene_start']} / "
        f"{payload['functional_module_protocol']['gene_count']}",
        f"- architecture / coupling: {payload['functional_module_protocol']['architecture_class']} / "
        f"`{payload['functional_module_protocol']['coupling_schema']}` / "
        f"{payload['functional_module_protocol']['coupling_link_count']} links",
        f"- hierarchy: {payload['functional_module_protocol']['hierarchy_depth_by_module']}",
        f"- coupling semantics: {payload['functional_module_protocol']['coupling_semantics']}",
        f"- inputs: {payload['functional_module_protocol']['inputs']}",
        f"- output scope: {payload['functional_module_protocol']['output_scope']}",
        f"- action selection / new physics: "
        f"{payload['functional_module_protocol']['action_selection']} / "
        f"{payload['functional_module_protocol']['new_world_physics']}",
        f"- neutralization interventions: {payload['functional_module_protocol']['neutralization_interventions']}",
        f"- contribution diagnostics: {payload['functional_module_protocol']['contribution_diagnostics']}",
        f"- architecture capability experiment: {payload['functional_module_protocol']['architecture_capability_experiment']}",
        f"- embodied capability experiment: {payload['functional_module_protocol']['embodied_capability_experiment']}",
        f"- embodied semantics: {payload['functional_module_protocol']['embodied_output_semantics']}",
        f"- physiological semantics: {payload['functional_module_protocol']['physiological_output_semantics']}",
        f"- physiological ecology experiment: {payload['functional_module_protocol']['physiological_ecology_experiment']}",
        f"- regulatory physiology semantics: {payload['functional_module_protocol']['regulatory_physiology_semantics']}",
        f"- regulatory physiology experiment: {payload['functional_module_protocol']['regulatory_physiology_experiment']}",
        f"- resource metabolism semantics: {payload['functional_module_protocol']['resource_metabolism_semantics']}",
        f"- resource metabolism experiment: {payload['functional_module_protocol']['resource_metabolism_experiment']}",
        f"- conservative intake experiment: {payload['functional_module_protocol']['conservative_intake_experiment']}",
        f"- known architecture limit: {payload['functional_module_protocol']['known_architecture_limit']}",
        f"- leave-one-out protocol: {payload['functional_module_protocol']['leave_one_out_protocol']}",
        f"- effect qualification: {payload['functional_module_protocol']['effect_qualification']}",
        f"- lineage-balanced pairs: {payload['functional_module_protocol']['lineage_balanced_pair_protocol']}",
        f"- boundary: {payload['functional_module_protocol']['interpretation']}",
        "",
        "## D4-A resource geography × inherited affinity reversal",
        "",
        f"- plan / result / assessment: `{payload['d4_niche_reversal_protocol']['plan_schema']}` / "
        f"`{payload['d4_niche_reversal_protocol']['result_schema']}` / "
        f"`{payload['d4_niche_reversal_protocol']['assessment_schema']}`",
        f"- source gate: {payload['d4_niche_reversal_protocol']['source_gate']}",
        f"- branches: {payload['d4_niche_reversal_protocol']['branches']}",
        f"- interaction: {payload['d4_niche_reversal_protocol']['primary_interaction']}",
        f"- resource reversal: {payload['d4_niche_reversal_protocol']['resource_reversal']}",
        f"- paired randomness / genotype / lineage preserved: "
        f"{payload['d4_niche_reversal_protocol']['paired_randomness']} / "
        f"{payload['d4_niche_reversal_protocol']['genotype_preserved']} / "
        f"{payload['d4_niche_reversal_protocol']['lineage_membership_preserved']}",
        f"- source exposure: {payload['d4_niche_reversal_protocol']['source_exposure_diagnostic']}",
        f"- niche claim requires: {payload['d4_niche_reversal_protocol']['stable_niche_claim_requires']}",
        "",
        "## Environment atlas",
        "",
        f"- enabled / schema: {atlas['enabled']} / `{atlas['schema']}`",
        f"- scales: {', '.join(str(item['regions_x']) + '×' + str(item['regions_y']) for item in atlas['scales']) or 'none'}",
        f"- signature: {', '.join(atlas['signature'])}",
        f"- resource-only metrics: {', '.join(atlas['resource_only_metrics']) or 'none'}",
        f"- subject exposure: {atlas['subject_exposure_association']}",
        f"- boundary: {atlas['interpretation']}",
    ]
    anchor = payload.get("anchor_protocol")
    if isinstance(anchor, dict):
        lines.extend(
            [
                "",
                "## Anchor selection",
                "",
                f"- schema: `{anchor['selection_schema']}`",
                f"- event kinds: {', '.join(anchor['event_kinds'])}",
                f"- quantile / maximum per kind per run / gap windows: "
                f"{anchor['quantile']} / {anchor['maximum_events_per_kind_per_run']} / "
                f"{anchor['minimum_gap_windows']}",
                f"- candidate rule: {anchor['candidate_rule']}",
                f"- ranking: {anchor['ranking_rule']}",
                f"- region diversity: {anchor['region_diversity_rule']}",
                f"- checkpoint: {anchor['checkpoint_rule']}",
                f"- boundary: {anchor['interpretation']}",
            ]
        )
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Audit group, region, and anchor protocols")
    parser.add_argument("--config", required=True)
    parser.add_argument("--manifest")
    parser.add_argument("--output", required=True)
    args = parser.parse_args(argv)
    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=True)
    payload = build_protocol_audit(args.config, args.manifest)
    (output / "protocol_audit.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (output / "protocol_audit.md").write_text(
        render_markdown(payload), encoding="utf-8"
    )


if __name__ == "__main__":
    main()
