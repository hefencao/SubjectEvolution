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


SCHEMA = "structural-measurement-protocol-audit-v13"


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
            "input_schema": cfg.functional_modules.input_schema,
            "inputs": [
                "bias",
                "energy deficit",
                "integrity deficit",
                "material deficit",
                "information-store deficit",
                "fertility deficit",
                "four local normalized resource channels",
            ],
            "output_schema": cfg.functional_modules.output_schema,
            "output_scope": "zero-sum residual over four harvest-channel request weights",
            "action_selection": False,
            "assimilation_affinity_modified": False,
            "resource_gradient_utility_modified": False,
            "new_world_physics": False,
            "expression_threshold": float(cfg.functional_modules.expression_threshold),
            "maximum_residual_fraction": float(cfg.functional_modules.max_residual_fraction),
            "maintenance_energy_per_expression": float(
                cfg.functional_modules.maintenance_energy_per_expression
            ),
            "development_energy_per_expression": float(
                cfg.functional_modules.development_energy_per_expression
            ),
            "neutralization_interventions": {
                "all_modules": "neutralize-functional-modules",
                "per_module": [
                    f"neutralize-functional-module-{index}"
                    for index in range(int(cfg.functional_modules.module_count))
                ],
            },
            "contribution_diagnostics": {
                "schema": "functional-module-contribution-audit-v1",
                "per_module_gate": True,
                "per_module_activation": True,
                "isolated_output_effect": True,
                "contribution_effective_count": True,
                "cancellation_fraction": True,
                "feedback_to_world": False,
            },
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
                    "assessment_schema": "d2-source-population-assessment-v1",
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
                        "minimum_qualified_panel_seeds_per_phase": 2,
                        "minimum_qualified_phases": 2,
                    },
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
        f"- module count / gene start: {payload['functional_module_protocol']['module_count']} / "
        f"{payload['functional_module_protocol']['gene_start']}",
        f"- inputs: {payload['functional_module_protocol']['inputs']}",
        f"- output scope: {payload['functional_module_protocol']['output_scope']}",
        f"- action selection / new physics: "
        f"{payload['functional_module_protocol']['action_selection']} / "
        f"{payload['functional_module_protocol']['new_world_physics']}",
        f"- neutralization interventions: {payload['functional_module_protocol']['neutralization_interventions']}",
        f"- contribution diagnostics: {payload['functional_module_protocol']['contribution_diagnostics']}",
        f"- leave-one-out protocol: {payload['functional_module_protocol']['leave_one_out_protocol']}",
        f"- effect qualification: {payload['functional_module_protocol']['effect_qualification']}",
        f"- lineage-balanced pairs: {payload['functional_module_protocol']['lineage_balanced_pair_protocol']}",
        f"- boundary: {payload['functional_module_protocol']['interpretation']}",
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
