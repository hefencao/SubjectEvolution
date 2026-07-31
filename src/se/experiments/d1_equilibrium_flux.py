"""Prepare a role-neutral equilibrium source by changing only shared resource renewal."""
from __future__ import annotations

import argparse
from copy import deepcopy
import hashlib
import json
from pathlib import Path
from typing import Any

from se.analysis.integrated_baseline import inspect_baseline
from se.cfg import load_config

SCHEMA = "integrated-equilibrium-resource-flux-v1"
TARGET_REGENERATION = (0.00675, 0.00675, 0.00675, 0.00675)


def _canonical(payload: Any) -> str:
    return hashlib.sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def prepare(*, template: str | Path, output: str | Path) -> dict[str, Any]:
    source = Path(template)
    inspect_baseline(source)
    before = json.loads(source.read_text(encoding="utf-8"))
    after = deepcopy(before)
    original = tuple(float(v) for v in after["environment"]["resource_regeneration"])
    if original != (0.027, 0.027, 0.027, 0.027):
        raise ValueError(f"unexpected qualified D1-P regeneration vector: {original}")
    after["environment"]["resource_regeneration"] = list(TARGET_REGENERATION)

    # The entire canonical tree except this one shared physical vector must match.
    check_before = deepcopy(before)
    check_after = deepcopy(after)
    check_before["environment"].pop("resource_regeneration")
    check_after["environment"].pop("resource_regeneration")
    if check_before != check_after:
        raise RuntimeError("equilibrium source drifted outside shared resource regeneration")

    destination = Path(output)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(after, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    load_config(destination)
    report = {
        "schema": SCHEMA,
        "source": str(source),
        "output": str(destination),
        "source_file_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
        "output_file_sha256": hashlib.sha256(destination.read_bytes()).hexdigest(),
        "source_canonical_sha256": _canonical(before),
        "output_canonical_sha256": _canonical(after),
        "only_changed_path": "environment.resource_regeneration",
        "before": list(original),
        "after": list(TARGET_REGENERATION),
        "relative_external_renewal": TARGET_REGENERATION[0] / original[0],
        "genetic_coordinates_changed": 0,
        "gene_specific_advantage_added": False,
        "environment_geometry_changed": False,
        "resource_effects_changed": False,
        "maintenance_or_reproduction_changed": False,
        "parameter_selection_evidence": {
            "status": "exploratory-not-qualification-evidence",
            "candidate_seed": 96002,
            "candidate_tick": 600,
            "candidate_final_alive": 131,
            "candidate_final_alive_fraction_to_initial": 131 / 128,
            "environment_resource_effective_dimensions_final": 2.73237,
            "environment_resource_mean_abs_correlation_final": 0.31444,
            "excluded_candidate": {
                "resource_regeneration": [0.009, 0.009, 0.009, 0.009],
                "reason": "A separate independent run remained in a strong short-window rebound and was not accepted as equilibrium evidence.",
            },
            "note": "Exploratory seeds select only the shared physical flux candidate. Formal qualification requires a new independent seed, a health report, and a cycle-aware equilibrium report.",
        },
        "authorization": {
            "formal_equilibrium_source_pilot_authorized": True,
            "gene_specific_adjustment_authorized": False,
            "paired_experiment_authorized": False,
            "selection_claim_authorized": False,
        },
    }
    Path(f"{destination}.manifest.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--template", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args(argv)
    print(json.dumps(prepare(template=args.template, output=args.output), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
