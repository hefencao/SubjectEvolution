"""Machine-readable audit of group, spatial-region, and anchor protocols."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from .config import load_config
from .natural_event_matrix import load_manifest
from .spatial_partition import SpatialRegionPartition


SCHEMA = "structural-measurement-protocol-audit-v1"


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
    payload: dict[str, Any] = {
        "schema": SCHEMA,
        "config_path": str(Path(config_path).resolve()),
        "group_label_protocol": group,
        "spatial_region_protocol": partition.metadata(),
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
        "## Spatial regions",
        "",
        f"- schema: `{region['schema']}`",
        f"- grid: {region['regions_x']} × {region['regions_y']} ({region['region_count']} regions)",
        f"- physical region: {region['physical_region_width']} × {region['physical_region_height']}",
        f"- world cells per region: {region['world_cells_per_region_x']} × "
        f"{region['world_cells_per_region_y']}",
        f"- grid-aligned: {region['world_grid_aligned']}",
        f"- map-size semantics: {region['map_size_semantics']}",
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
