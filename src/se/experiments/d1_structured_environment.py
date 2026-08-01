"""Prepare the D1-R role-neutral structured environment and exchange substrate."""
from __future__ import annotations

import argparse
from copy import deepcopy
import hashlib
import json
from pathlib import Path
from typing import Any

from se.cfg import load_config
from se.env.diversity import STRUCTURED_PROVINCE_ENVIRONMENT_SCHEMA
from se.differentiation.physiology import (
    STRUCTURED_RESOURCE_NETWORK_PHYSIOLOGY_SCHEMA,
)

SCHEMA = "structured-ecological-environment-config-v1"
NETWORK_SCHEMA = "paired-complementary-recipes-v1"
SHARE_SCHEMA = "energy-and-raw-resource-need-balanced-v1"


def _sha(payload: Any) -> str:
    return hashlib.sha256(
        json.dumps(
            payload,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()


def _set_path(payload: dict[str, Any], path: str, value: Any) -> None:
    section, key = path.split(".", 1)
    payload[section][key] = value


def prepare(
    *,
    template: str | Path,
    output: str | Path,
    regeneration: float = 0.015,
    province_secondary_weight: float | None = None,
    province_radius_scale: float | None = None,
    processing_amplitude: float = 0.65,
    resource_share_amount: float = 0.12,
    recipe_rate_scale: float = 1.0,
    trust_threshold: float = 0.04,
    relation_decay: float = 0.0005,
    ticks: int = 1800,
) -> dict[str, Any]:
    source = Path(template)
    before = json.loads(source.read_text(encoding="utf-8"))
    if not isinstance(before, dict):
        raise ValueError("structured environment template must be a JSON object")
    if before.get("environment", {}).get("schema") not in {
        "persistent-multiscale-four-resource-renewal-v3",
        STRUCTURED_PROVINCE_ENVIRONMENT_SCHEMA,
    }:
        raise ValueError("D1-R requires the integrated multiscale four-resource baseline")
    if float(regeneration) <= 0.0:
        raise ValueError("regeneration must be positive")
    if province_secondary_weight is not None and not (
        0.0 <= float(province_secondary_weight) <= 1.0
    ):
        raise ValueError("province secondary weight must be in [0, 1]")
    if province_radius_scale is not None and not (
        0.5 <= float(province_radius_scale) <= 2.0
    ):
        raise ValueError("province radius scale must be in [0.5, 2.0]")
    if not 0.0 < float(processing_amplitude) < 1.0:
        raise ValueError("processing amplitude must be in (0, 1)")
    if float(resource_share_amount) <= 0.0:
        raise ValueError("resource share amount must be positive")
    if float(recipe_rate_scale) <= 0.0:
        raise ValueError("recipe rate scale must be positive")
    if not 0.0 < float(trust_threshold) <= 1.0:
        raise ValueError("trust threshold must be in (0, 1]")
    if not 0.0 <= float(relation_decay) < 1.0:
        raise ValueError("relation decay must be in [0, 1)")
    if int(ticks) <= 0:
        raise ValueError("ticks must be positive")

    after = deepcopy(before)
    changes: dict[str, dict[str, Any]] = {}

    def change(path: str, value: Any) -> None:
        section, key = path.split(".", 1)
        old = deepcopy(after[section].get(key))
        _set_path(after, path, value)
        if old != value:
            changes[path] = {"before": old, "after": deepcopy(value)}

    change("run.ticks", int(ticks))
    change("run.metrics_period", 60)
    change("run.checkpoint_period", 600)
    change("run.checkpoint_ticks", [])
    change("run.full_checkpoint_enabled", False)
    change("run.evolution_evaluation_period", 120)
    change("run.group_function_diagnostics_enabled", True)
    change(
        "run.group_function_diagnostics_schema",
        "group-functional-division-diagnostics-v1",
    )
    change("run.group_function_window_ticks", 120)

    # High-volume row logs are observational. Disabling them keeps the long
    # environment panel tractable without changing any mechanism or aggregate.
    change("knowledge.log_transfer_events", False)
    change("knowledge.log_outcome_updates", False)
    change("knowledge.log_policy_contributions", False)
    change("knowledge.log_routing_costs", False)
    change("knowledge.log_working_memory_updates", False)
    change("knowledge.log_sparse_selection_events", False)

    change("environment.schema", STRUCTURED_PROVINCE_ENVIRONMENT_SCHEMA)
    change(
        "environment.resource_regeneration",
        [float(regeneration)] * 4,
    )
    change(
        "environment.resource_province_centers",
        [[0.18, 0.18], [0.82, 0.22], [0.24, 0.80], [0.78, 0.76]],
    )
    base_radii = [0.16, 0.18, 0.20, 0.17]
    radius_scale = 1.0 if province_radius_scale is None else float(province_radius_scale)
    change(
        "environment.resource_province_radii",
        [round(value * radius_scale, 12) for value in base_radii],
    )
    change("environment.resource_province_contrasts", [0.85, 0.82, 0.80, 0.84])
    if province_secondary_weight is not None:
        change(
            "environment.resource_province_secondary_weight",
            float(province_secondary_weight),
        )
    change(
        "environment.resource_processing_province_offsets",
        [[0.28, 0.20], [-0.24, 0.26], [0.26, -0.22], [-0.28, -0.24]],
    )
    change(
        "environment.resource_processing_schema",
        "phase-shifted-channel-processing-support-v1",
    )
    change(
        "environment.resource_processing_support_amplitude",
        float(processing_amplitude),
    )
    change("environment.resource_effect_matrix", [[0.0] * 5 for _ in range(4)])

    change("physiology.schema", STRUCTURED_RESOURCE_NETWORK_PHYSIOLOGY_SCHEMA)
    change("physiology.resource_conversion_network_schema", NETWORK_SCHEMA)
    change(
        "physiology.resource_recipe_stoichiometry",
        [
            [1.0, 0.70, 0.0, 0.0],
            [0.0, 1.0, 0.70, 0.0],
            [0.0, 0.0, 1.0, 0.70],
            [0.70, 0.0, 0.0, 1.0],
        ],
    )
    change(
        "physiology.resource_recipe_effect_matrix",
        [
            [0.95, 0.0, 0.0, 0.0, 0.0],
            [0.0, 0.050, 0.030, 0.0, 0.0],
            [0.0, 0.0, 0.025, 0.32, 0.0],
            [0.0, 0.0, 0.025, 0.0, 0.32],
        ],
    )
    base_rates = [0.035, 0.032, 0.030, 0.030]
    change(
        "physiology.resource_recipe_rate_per_tick",
        [float(value) * float(recipe_rate_scale) for value in base_rates],
    )
    change(
        "physiology.resource_processing_energy_per_unit",
        [0.006, 0.006, 0.006, 0.006],
    )

    change("social.share_schema", SHARE_SCHEMA)
    change("social.resource_share_amount", float(resource_share_amount))
    change("social.resource_share_reserve_fraction", 0.25)
    change("social.trust_group_threshold", float(trust_threshold))
    change("social.relation_decay", float(relation_decay))
    change("social.group_min_members", 6)
    change("social.group_update_min_period", 50)
    change("social.group_update_max_period", 100)

    # The change allow-list is the scientific boundary: no inherited coordinate,
    # mutation rate, maintenance cost, reproduction rule or role label may drift.
    allowed_prefixes = {
        "run.ticks",
        "run.metrics_period",
        "run.checkpoint_period",
        "run.checkpoint_ticks",
        "run.full_checkpoint_enabled",
        "run.evolution_evaluation_period",
        "run.group_function_diagnostics_enabled",
        "run.group_function_diagnostics_schema",
        "run.group_function_window_ticks",
        "knowledge.log_transfer_events",
        "knowledge.log_outcome_updates",
        "knowledge.log_policy_contributions",
        "knowledge.log_routing_costs",
        "knowledge.log_working_memory_updates",
        "knowledge.log_sparse_selection_events",
        "environment.schema",
        "environment.resource_regeneration",
        "environment.resource_province_centers",
        "environment.resource_province_radii",
        "environment.resource_province_contrasts",
        "environment.resource_province_secondary_weight",
        "environment.resource_processing_province_offsets",
        "environment.resource_processing_schema",
        "environment.resource_processing_support_amplitude",
        "environment.resource_effect_matrix",
        "physiology.schema",
        "physiology.resource_conversion_network_schema",
        "physiology.resource_recipe_stoichiometry",
        "physiology.resource_recipe_effect_matrix",
        "physiology.resource_recipe_rate_per_tick",
        "physiology.resource_processing_energy_per_unit",
        "social.share_schema",
        "social.resource_share_amount",
        "social.resource_share_reserve_fraction",
        "social.trust_group_threshold",
        "social.relation_decay",
        "social.group_min_members",
        "social.group_update_min_period",
        "social.group_update_max_period",
    }
    unexpected = sorted(set(changes).difference(allowed_prefixes))
    if unexpected:
        raise RuntimeError(f"structured environment drifted outside allow-list: {unexpected}")

    destination = Path(output)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(
        json.dumps(after, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    cfg = load_config(destination)
    report = {
        "schema": SCHEMA,
        "source": str(source),
        "output": str(destination),
        "source_file_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
        "output_file_sha256": hashlib.sha256(destination.read_bytes()).hexdigest(),
        "source_canonical_sha256": _sha(before),
        "output_canonical_sha256": _sha(after),
        "changed_paths": sorted(changes),
        "changes": changes,
        "genetic_coordinates_changed": 0,
        "mutation_or_inheritance_changed": False,
        "maintenance_or_reproduction_changed": False,
        "role_or_group_label_reward_added": False,
        "physical_structure": {
            "resource_province_count": 4,
            "source_circuit_copies_per_channel": 2,
            "secondary_circuit_weight": float(
                cfg.environment.resource_province_secondary_weight
            ),
            "province_radius_scale": radius_scale,
            "global_channel_mean_preserved_by_normalization": True,
            "processing_province_count": 4,
            "processing_is_spatially_offset": True,
            "complementary_recipe_count": 4,
            "minimum_raw_channels_per_recipe": 2,
            "raw_resource_exchange_enabled": True,
            "group_function_diagnostics_enabled": bool(
                cfg.run.group_function_diagnostics_enabled
            ),
        },
        "evidence_class": "environment-construction-not-qualification",
        "authorization": {
            "exploratory_parameter_probe_authorized": True,
            "formal_multi_seed_structure_panel_authorized": True,
            "single_run_gene_audit_authorized": False,
            "formal_gene_audit_authorized": False,
            "selection_claim_authorized": False,
        },
        "interpretation_boundary": (
            "This config creates physical opportunities and dependencies for transport, "
            "exchange and within-group functional differentiation. It does not preassign "
            "roles or prove that structured groups will emerge."
        ),
    }
    Path(f"{destination}.manifest.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return report


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--template", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--regeneration", type=float, default=0.015)
    parser.add_argument("--province-secondary-weight", type=float, default=None)
    parser.add_argument("--province-radius-scale", type=float, default=None)
    parser.add_argument("--processing-amplitude", type=float, default=0.65)
    parser.add_argument("--resource-share-amount", type=float, default=0.12)
    parser.add_argument("--recipe-rate-scale", type=float, default=1.0)
    parser.add_argument("--trust-threshold", type=float, default=0.04)
    parser.add_argument("--relation-decay", type=float, default=0.0005)
    parser.add_argument("--ticks", type=int, default=1800)
    args = parser.parse_args(argv)
    print(
        json.dumps(
            prepare(
                template=args.template,
                output=args.output,
                regeneration=args.regeneration,
                province_secondary_weight=args.province_secondary_weight,
                province_radius_scale=args.province_radius_scale,
                processing_amplitude=args.processing_amplitude,
                resource_share_amount=args.resource_share_amount,
                recipe_rate_scale=args.recipe_rate_scale,
                trust_threshold=args.trust_threshold,
                relation_decay=args.relation_decay,
                ticks=args.ticks,
            ),
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
