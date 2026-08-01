"""Prepare D1-U resource-depletion competition and terrain signal transport."""
from __future__ import annotations

import argparse
from copy import deepcopy
import hashlib
import json
from pathlib import Path
from typing import Any

from se.cfg import load_config

SCHEMA = "depletion-pressure-terrain-signal-config-v1"


def _sha(payload: Any) -> str:
    return hashlib.sha256(
        json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def prepare(
    *,
    template: str | Path,
    output: str | Path,
    ticks: int = 600,
    signal_terrain_resistance: float = 0.45,
    direct_distance_decay: float = 0.025,
    direct_terrain_resistance: float = 0.45,
) -> dict[str, Any]:
    source = Path(template)
    before = json.loads(source.read_text(encoding="utf-8"))
    if not isinstance(before, dict):
        raise ValueError("D1-U template must be a JSON object")
    if before.get("entities", {}).get("resource_load_schema") != (
        "raw-store-mobility-burden-v1"
    ):
        raise ValueError("D1-U requires the D1-T load substrate")
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
    change("run", "checkpoint_period", int(ticks))
    change("run", "checkpoint_ticks", [])
    change("run", "full_checkpoint_enabled", False)
    change("entities", "resource_contest_schema", "rival-harvest-depletion-pressure-v2")
    change("entities", "resource_contest_energy_cost_per_pressure", 0.0)
    change("entities", "resource_contest_integrity_damage_per_pressure", 0.0)
    change("entities", "resource_contest_signal_weight", 0.0)
    change("environment", "signal_propagation_schema", "terrain-resisted-diffusion-v1")
    change(
        "environment",
        "signal_terrain_resistance_fraction",
        float(signal_terrain_resistance),
    )
    change("information", "resource_signal_observation_schema", "post-harvest-current-v2")
    change(
        "information",
        "direct_message_propagation_schema",
        "terrain-distance-attenuated-v1",
    )
    change(
        "information",
        "direct_message_distance_decay_per_cell",
        float(direct_distance_decay),
    )
    change(
        "information",
        "direct_message_terrain_resistance_fraction",
        float(direct_terrain_resistance),
    )

    allowed = {
        "run.ticks",
        "run.metrics_period",
        "run.checkpoint_period",
        "run.checkpoint_ticks",
        "run.full_checkpoint_enabled",
        "entities.resource_contest_schema",
        "entities.resource_contest_energy_cost_per_pressure",
        "entities.resource_contest_integrity_damage_per_pressure",
        "entities.resource_contest_signal_weight",
        "environment.signal_propagation_schema",
        "environment.signal_terrain_resistance_fraction",
        "information.resource_signal_observation_schema",
        "information.direct_message_propagation_schema",
        "information.direct_message_distance_decay_per_cell",
        "information.direct_message_terrain_resistance_fraction",
    }
    unexpected = sorted(set(changes) - allowed)
    if unexpected:
        raise RuntimeError(f"D1-U drifted outside its allow-list: {unexpected}")

    destination = Path(output)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(after, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
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
        "resource_geometry_or_mean_flux_changed": False,
        "movement_load_formula_changed": False,
        "terrain_movement_formula_changed": False,
        "physical_semantics": {
            "competition": cfg.entities.resource_contest_schema,
            "duplicate_body_damage": False,
            "resource_depletion_remains_actual_harvest_commit": True,
            "resource_signal_state": cfg.information.resource_signal_observation_schema,
            "field_signal_transport": cfg.environment.signal_propagation_schema,
            "direct_message_transport": cfg.information.direct_message_propagation_schema,
        },
        "evidence_class": "environment-mechanism-debug-config",
        "authorization": {
            "cpu_accelerated_backend_debug_contrast": True,
            "formal_environment_panel": False,
            "gene_audit": False,
            "selection_or_adaptation_claim": False,
            "scout_role_claim": False,
        },
        "interpretation_boundary": (
            "D1-U corrects competition and signal transport semantics. It does not prove "
            "that information is beneficial, that a scout role exists, or that CPU and "
            "accelerated trajectories should be bitwise identical."
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
    parser.add_argument("--ticks", type=int, default=600)
    parser.add_argument("--signal-terrain-resistance", type=float, default=0.45)
    parser.add_argument("--direct-distance-decay", type=float, default=0.025)
    parser.add_argument("--direct-terrain-resistance", type=float, default=0.45)
    args = parser.parse_args(argv)
    print(json.dumps(prepare(
        template=args.template,
        output=args.output,
        ticks=args.ticks,
        signal_terrain_resistance=args.signal_terrain_resistance,
        direct_distance_decay=args.direct_distance_decay,
        direct_terrain_resistance=args.direct_terrain_resistance,
    ), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
