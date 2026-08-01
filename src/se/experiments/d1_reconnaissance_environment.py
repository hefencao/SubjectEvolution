"""Prepare the D1-T role-neutral contest, load and information-value chain."""
from __future__ import annotations

import argparse
from copy import deepcopy
import hashlib
import json
from pathlib import Path
from typing import Any

from se.cfg import load_config

SCHEMA = "reconnaissance-pressure-chain-config-v1"


def _canonical_sha(payload: Any) -> str:
    return hashlib.sha256(
        json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode(
            "utf-8"
        )
    ).hexdigest()


def prepare(
    *,
    template: str | Path,
    output: str | Path,
    ticks: int = 900,
    load_speed_penalty: float = 0.35,
    load_movement_energy_fraction: float = 0.35,
    contest_energy_cost: float = 0.008,
    contest_integrity_damage: float = 0.0003,
    contest_pressure_retention: float = 0.90,
    contest_signal_weight: float = 1.0,
    contest_radius_cells: int = 1,
    danger_message_direction_weight: float = 1.0,
) -> dict[str, Any]:
    source = Path(template)
    before = json.loads(source.read_text(encoding="utf-8"))
    if not isinstance(before, dict):
        raise ValueError("D1-T template must be a JSON object")
    if before.get("environment", {}).get("schema") != (
        "structured-province-resource-network-v4"
    ):
        raise ValueError("D1-T requires the D1-S structured environment")
    if before.get("physiology", {}).get("resource_conversion_network_schema") != (
        "paired-complementary-recipes-v1"
    ):
        raise ValueError("D1-T requires the complementary raw-resource network")
    if int(ticks) <= 0:
        raise ValueError("ticks must be positive")

    after = deepcopy(before)
    changes: dict[str, dict[str, Any]] = {}

    def change(section: str, key: str, value: Any) -> None:
        old = deepcopy(after[section].get(key))
        after[section][key] = value
        if old != value:
            changes[f"{section}.{key}"] = {"before": old, "after": deepcopy(value)}

    change("run", "ticks", int(ticks))
    change("run", "metrics_period", 60)
    change("run", "checkpoint_period", 600)
    change("run", "checkpoint_ticks", [])
    change("run", "full_checkpoint_enabled", False)
    change("run", "evolution_evaluation_period", 120)
    change("run", "reconnaissance_diagnostics_enabled", True)
    change(
        "run",
        "reconnaissance_diagnostics_schema",
        "reconnaissance-pressure-chain-diagnostics-v1",
    )
    change("run", "reconnaissance_window_ticks", 120)

    change("entities", "resource_load_schema", "raw-store-mobility-burden-v1")
    change(
        "entities",
        "resource_load_speed_penalty_fraction",
        float(load_speed_penalty),
    )
    change(
        "entities",
        "resource_load_movement_energy_fraction",
        float(load_movement_energy_fraction),
    )
    change(
        "entities", "resource_contest_schema", "co-located-harvest-contest-v1"
    )
    change(
        "entities",
        "resource_contest_energy_cost_per_pressure",
        float(contest_energy_cost),
    )
    change(
        "entities",
        "resource_contest_integrity_damage_per_pressure",
        float(contest_integrity_damage),
    )
    change(
        "entities",
        "resource_contest_pressure_retention",
        float(contest_pressure_retention),
    )
    change(
        "entities",
        "resource_contest_signal_weight",
        float(contest_signal_weight),
    )
    change(
        "entities",
        "resource_contest_radius_cells",
        int(contest_radius_cells),
    )
    change("entities", "danger_sensing_schema", "shared-inherited-radius-v1")
    change(
        "entities",
        "danger_message_direction_schema",
        "source-bearing-direct-message-v1",
    )
    change(
        "entities",
        "danger_message_direction_weight",
        float(danger_message_direction_weight),
    )

    allowed = {
        "run.ticks",
        "run.metrics_period",
        "run.checkpoint_period",
        "run.checkpoint_ticks",
        "run.full_checkpoint_enabled",
        "run.evolution_evaluation_period",
        "run.reconnaissance_diagnostics_enabled",
        "run.reconnaissance_diagnostics_schema",
        "run.reconnaissance_window_ticks",
        "entities.resource_load_schema",
        "entities.resource_load_speed_penalty_fraction",
        "entities.resource_load_movement_energy_fraction",
        "entities.resource_contest_schema",
        "entities.resource_contest_energy_cost_per_pressure",
        "entities.resource_contest_integrity_damage_per_pressure",
        "entities.resource_contest_pressure_retention",
        "entities.resource_contest_signal_weight",
        "entities.resource_contest_radius_cells",
        "entities.danger_sensing_schema",
        "entities.danger_message_direction_schema",
        "entities.danger_message_direction_weight",
    }
    unexpected = sorted(set(changes) - allowed)
    if unexpected:
        raise RuntimeError(f"D1-T drifted outside its allow-list: {unexpected}")

    destination = Path(output)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(
        json.dumps(after, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    cfg = load_config(destination)
    report = {
        "schema": SCHEMA,
        "source": str(source),
        "output": str(destination),
        "source_file_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
        "output_file_sha256": hashlib.sha256(destination.read_bytes()).hexdigest(),
        "source_canonical_sha256": _canonical_sha(before),
        "output_canonical_sha256": _canonical_sha(after),
        "changed_paths": sorted(changes),
        "changes": changes,
        "genetic_coordinates_changed": 0,
        "mutation_or_inheritance_changed": False,
        "resource_geometry_or_mean_flux_changed": False,
        "processing_or_exchange_changed": False,
        "group_rules_or_role_rewards_changed": False,
        "physical_value_chain": {
            "raw_load_mobility_tradeoff": cfg.entities.resource_load_schema,
            "rival_harvest_contest": cfg.entities.resource_contest_schema,
            "danger_reuses_existing_inherited_reach": cfg.entities.danger_sensing_schema,
            "contest_enters_existing_danger_signal": True,
            "contest_local_radius_cells": cfg.entities.resource_contest_radius_cells,
            "direct_danger_messages_supply_source_bearing": cfg.entities.danger_message_direction_schema,
            "receiver_action_use_is_observational_only": True,
        },
        "evidence_class": "environment-mechanism-debug-config",
        "authorization": {
            "single_seed_mechanism_probe": True,
            "multi_seed_social_structure_panel": False,
            "gene_audit": False,
            "selection_or_adaptation_claim": False,
            "scout_role_claim": False,
        },
        "interpretation_boundary": (
            "The config creates a complete physical opportunity chain for low-load ranging, "
            "contest exposure, danger signalling and receiver response. It assigns no scout "
            "role and does not prove that the chain is beneficial, selected or persistent."
        ),
    }
    Path(f"{destination}.manifest.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return report


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--template", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--ticks", type=int, default=900)
    parser.add_argument("--load-speed-penalty", type=float, default=0.35)
    parser.add_argument("--load-movement-energy-fraction", type=float, default=0.35)
    parser.add_argument("--contest-energy-cost", type=float, default=0.008)
    parser.add_argument("--contest-integrity-damage", type=float, default=0.0003)
    parser.add_argument("--contest-pressure-retention", type=float, default=0.90)
    parser.add_argument("--contest-signal-weight", type=float, default=1.0)
    parser.add_argument("--contest-radius-cells", type=int, default=1)
    parser.add_argument("--danger-message-direction-weight", type=float, default=1.0)
    args = parser.parse_args(argv)
    print(
        json.dumps(
            prepare(
                template=args.template,
                output=args.output,
                ticks=args.ticks,
                load_speed_penalty=args.load_speed_penalty,
                load_movement_energy_fraction=args.load_movement_energy_fraction,
                contest_energy_cost=args.contest_energy_cost,
                contest_integrity_damage=args.contest_integrity_damage,
                contest_pressure_retention=args.contest_pressure_retention,
                contest_signal_weight=args.contest_signal_weight,
                contest_radius_cells=args.contest_radius_cells,
                danger_message_direction_weight=args.danger_message_direction_weight,
            ),
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
