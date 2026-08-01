"""Prepare D1-V independent signal-medium configuration."""
from __future__ import annotations

import argparse
from copy import deepcopy
import hashlib
import json
from pathlib import Path
from typing import Any

from se.cfg import load_config
from se.env.signal_medium import medium_metrics, signal_openness_field
from se.env.physiology import physiology_fields

SCHEMA = "independent-signal-medium-config-v1"


def _sha(payload: Any) -> str:
    return hashlib.sha256(
        json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def prepare(
    *,
    template: str | Path,
    output: str | Path,
    ticks: int = 240,
    conductance_fraction: float = 0.65,
    openness_floor: float = 0.25,
    openness_amplitude: float = 0.75,
    medium_resistance: float = 0.55,
    distance_decay: float = 0.025,
) -> dict[str, Any]:
    source = Path(template)
    before = json.loads(source.read_text(encoding="utf-8"))
    if not isinstance(before, dict):
        raise ValueError("D1-V template must be a JSON object")
    if before.get("information", {}).get("resource_signal_observation_schema") != (
        "post-harvest-current-v2"
    ):
        raise ValueError("D1-V requires D1-U post-harvest resource signals")
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
    change("environment", "signal_propagation_schema", "independent-openness-diffusion-v2")
    change("environment", "signal_terrain_resistance_fraction", 0.0)
    change("environment", "signal_medium_schema", "independent-openness-mosaic-v1")
    change("environment", "signal_medium_conductance_fraction", float(conductance_fraction))
    change("environment", "signal_openness_floor", float(openness_floor))
    change("environment", "signal_openness_amplitude", float(openness_amplitude))
    change("environment", "signal_openness_period", 0)
    # Deliberately align the openness mosaic with the movement-resistance wave.
    # This demonstrates that high movement resistance may coexist with high
    # signal openness; the two fields remain separately configurable.
    change("environment", "signal_openness_wave_x", float(after["environment"]["terrain_wave_x"]))
    change("environment", "signal_openness_wave_y", float(after["environment"]["terrain_wave_y"]))
    change("environment", "signal_openness_phase_offset", float(after["environment"]["terrain_phase_offset"]))
    change("information", "direct_message_propagation_schema", "openness-distance-attenuated-v2")
    change("information", "direct_message_terrain_resistance_fraction", 0.0)
    change("information", "direct_message_medium_resistance_fraction", float(medium_resistance))
    change("information", "direct_message_distance_decay_per_cell", float(distance_decay))

    allowed = {
        "run.ticks",
        "run.metrics_period",
        "run.checkpoint_period",
        "run.checkpoint_ticks",
        "run.full_checkpoint_enabled",
        "environment.signal_propagation_schema",
        "environment.signal_terrain_resistance_fraction",
        "environment.signal_medium_schema",
        "environment.signal_medium_conductance_fraction",
        "environment.signal_openness_floor",
        "environment.signal_openness_amplitude",
        "environment.signal_openness_period",
        "environment.signal_openness_wave_x",
        "environment.signal_openness_wave_y",
        "environment.signal_openness_phase_offset",
        "information.direct_message_propagation_schema",
        "information.direct_message_terrain_resistance_fraction",
        "information.direct_message_medium_resistance_fraction",
        "information.direct_message_distance_decay_per_cell",
    }
    unexpected = sorted(set(changes) - allowed)
    if unexpected:
        raise RuntimeError(f"D1-V drifted outside its allow-list: {unexpected}")

    destination = Path(output)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(
        json.dumps(after, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    cfg = load_config(destination)
    _, movement_resistance, _ = physiology_fields(cfg, 0)
    openness = signal_openness_field(cfg, 0)
    metrics = medium_metrics(openness, movement_resistance)
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
        "movement_formula_changed": False,
        "resource_geometry_or_mean_flux_changed": False,
        "direct_conflict_enabled": False,
        "transport_fields": metrics,
        "physical_semantics": {
            "movement_field": "terrain resistance",
            "signal_field": "independent openness",
            "field_signal_transport": cfg.environment.signal_propagation_schema,
            "direct_message_transport": cfg.information.direct_message_propagation_schema,
            "fixed_direction_coupling": False,
        },
        "authorization": {
            "transport_semantics_debug": True,
            "direct_conflict_implementation": False,
            "formal_environment_panel": False,
            "gene_audit": False,
            "social_role_claim": False,
        },
        "interpretation_boundary": (
            "D1-V separates movement resistance from signal transport. Positive, "
            "negative, or near-zero spatial correlation is configurable and does not "
            "by itself prove information benefit or social differentiation."
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
    parser.add_argument("--ticks", type=int, default=240)
    parser.add_argument("--conductance-fraction", type=float, default=0.65)
    parser.add_argument("--openness-floor", type=float, default=0.25)
    parser.add_argument("--openness-amplitude", type=float, default=0.75)
    parser.add_argument("--medium-resistance", type=float, default=0.55)
    parser.add_argument("--distance-decay", type=float, default=0.025)
    args = parser.parse_args(argv)
    print(
        json.dumps(
            prepare(
                template=args.template,
                output=args.output,
                ticks=args.ticks,
                conductance_fraction=args.conductance_fraction,
                openness_floor=args.openness_floor,
                openness_amplitude=args.openness_amplitude,
                medium_resistance=args.medium_resistance,
                distance_decay=args.distance_decay,
            ),
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
