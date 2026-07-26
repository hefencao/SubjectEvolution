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


SCHEMA = "structural-measurement-protocol-audit-v5"


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
            "lineage_aware": False,
            "group_aware": False,
            "diversity_protection": False,
            "interpretation": (
                "fixed four-channel physical interface with independently configured spatial, "
                "temporal, and diffusion dynamics; configuration can create environmental axes "
                "but does not guarantee evolved ecological differentiation"
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
