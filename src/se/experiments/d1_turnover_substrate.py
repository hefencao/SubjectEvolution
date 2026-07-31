"""Prepare a parameterized demographic substrate qualification config.

This command changes only explicit ecological throughput and reproduction-budget
parameters.  It does not add a new gene or interpret fitness.  The generated
config must still pass a staged source-health contract before any capability or
paired branch can be authorized.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from se.cfg import load_config

SCHEMA = "d1-turnover-substrate-config-v2"


def build_config(
    template: str | Path,
    *,
    output: str | Path,
    initial_entities: int,
    initial_energy: float,
    maintenance_cost: float,
    harvest_multiplier: float,
    resource_regeneration: float,
    reproduction_threshold: float,
    reproduction_cost: float,
    offspring_endowment: float,
    parent_reserve: float,
    target_tick: int,
    metrics_period: int,
    checkpoint_period: int,
) -> dict[str, Any]:
    required_energy = float(reproduction_cost) + float(offspring_endowment) + float(parent_reserve)
    if abs(float(reproduction_threshold) - required_energy) > 1e-9:
        raise ValueError(
            "reproduction_threshold must equal reproduction_cost + "
            "offspring_endowment + parent_reserve"
        )
    source = Path(template)
    payload = json.loads(source.read_text(encoding="utf-8"))
    payload["world"]["initial_entities"] = int(initial_entities)
    payload["entities"]["initial_energy"] = float(initial_energy)
    payload["entities"]["maintenance_cost"] = float(maintenance_cost)
    payload["entities"]["reproduction_threshold"] = float(reproduction_threshold)
    payload["entities"]["reproduction_cost"] = float(reproduction_cost)
    payload["entities"]["reproduction_schema"] = (
        "fixed-conservative-offspring-investment-v3"
    )
    payload["entities"]["reproduction_parent_reserve"] = float(parent_reserve)
    payload["entities"]["reproduction_investment_levels"] = [
        float(offspring_endowment)
    ]
    payload["environment"]["harvest_channel_multipliers"] = [
        float(harvest_multiplier)
    ] * 4
    payload["environment"]["resource_regeneration"] = [
        float(resource_regeneration)
    ] * 4
    payload["run"]["ticks"] = int(target_tick)
    payload["run"]["metrics_period"] = int(metrics_period)
    payload["run"]["checkpoint_period"] = int(checkpoint_period)
    payload["run"]["checkpoint_ticks"] = [int(target_tick)]
    destination = Path(output)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    # Validate with the authoritative loader after writing, so the exact file
    # users will execute is the one that is checked.
    load_config(destination)
    digest = hashlib.sha256(destination.read_bytes()).hexdigest()
    manifest = {
        "schema": SCHEMA,
        "template": str(source),
        "output": str(destination),
        "config_sha256": digest,
        "purpose": "demographic-substrate-qualification-only",
        "new_gene_added": False,
        "selection_claim_authorized": False,
        "capability_effect_interpretation_authorized": False,
        "parameters": {
            "initial_entities": initial_entities,
            "initial_energy": initial_energy,
            "maintenance_cost": maintenance_cost,
            "harvest_multiplier": harvest_multiplier,
            "resource_regeneration": resource_regeneration,
            "reproduction_threshold": reproduction_threshold,
            "reproduction_cost": reproduction_cost,
            "offspring_endowment": offspring_endowment,
            "parent_reserve": parent_reserve,
            "target_tick": target_tick,
            "metrics_period": metrics_period,
            "checkpoint_period": checkpoint_period,
        },
    }
    manifest_path = Path(f"{destination}.manifest.json")
    manifest["manifest_path"] = str(manifest_path)
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    legacy_manifest_path = destination.with_suffix(".manifest.json")
    if legacy_manifest_path != manifest_path and legacy_manifest_path.exists():
        legacy_manifest_path.unlink()
    return manifest


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Prepare a turnover-substrate qualification config.")
    parser.add_argument("--template", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--initial-entities", type=int, default=160)
    parser.add_argument("--initial-energy", type=float, default=2.4)
    parser.add_argument("--maintenance-cost", type=float, default=0.015)
    parser.add_argument("--harvest-multiplier", type=float, default=1.0)
    parser.add_argument("--resource-regeneration", type=float, default=0.018)
    parser.add_argument("--reproduction-threshold", type=float, default=1.4)
    parser.add_argument("--reproduction-cost", type=float, default=0.1)
    parser.add_argument("--offspring-endowment", type=float, default=0.9)
    parser.add_argument("--parent-reserve", type=float, default=0.4)
    parser.add_argument("--target-tick", type=int, default=240)
    parser.add_argument("--metrics-period", type=int, default=30)
    parser.add_argument("--checkpoint-period", type=int, default=120)
    args = parser.parse_args(argv)
    if args.initial_entities < 16:
        parser.error("initial-entities must be at least 16 for substrate qualification")
    if args.target_tick < 120:
        parser.error("target-tick must be at least 120")
    if args.offspring_endowment <= 0.0:
        parser.error("offspring-endowment must be positive")
    if args.parent_reserve < 0.0:
        parser.error("parent-reserve cannot be negative")
    required_energy = args.reproduction_cost + args.offspring_endowment + args.parent_reserve
    if abs(args.reproduction_threshold - required_energy) > 1e-9:
        parser.error(
            "reproduction-threshold must equal reproduction-cost + "
            "offspring-endowment + parent-reserve for the fixed conservative substrate"
        )
    manifest = build_config(
        args.template,
        output=args.output,
        initial_entities=args.initial_entities,
        initial_energy=args.initial_energy,
        maintenance_cost=args.maintenance_cost,
        harvest_multiplier=args.harvest_multiplier,
        resource_regeneration=args.resource_regeneration,
        reproduction_threshold=args.reproduction_threshold,
        reproduction_cost=args.reproduction_cost,
        offspring_endowment=args.offspring_endowment,
        parent_reserve=args.parent_reserve,
        target_tick=args.target_tick,
        metrics_period=args.metrics_period,
        checkpoint_period=args.checkpoint_period,
    )
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
