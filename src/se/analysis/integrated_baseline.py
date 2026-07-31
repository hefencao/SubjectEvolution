"""Validate and freeze the already integrated ecological-subject baseline.

This module deliberately does not attach one more capability.  It verifies that
one qualified config already exposes a plural inherited subject and a plural
physical environment, then copies that config unchanged for a retention panel.
"""
from __future__ import annotations

import argparse
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
from typing import Any

from se.cfg import load_config
from se.differentiation.capacity import CAPACITY_TRAIT_NAMES, capacity_gene_count
from se.differentiation.functional import functional_module_gene_count
from se.differentiation.physiology import physiology_gene_count
from se.env.niches import active_morphology_traits
from se.policy import ParametricPolicy

SCHEMA = "integrated-ecological-subject-baseline-v1"


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _canonical_sha256(payload: Any) -> str:
    return _sha256_bytes(
        json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    )


def inspect_baseline(path: str | Path) -> dict[str, Any]:
    source = Path(path)
    cfg = load_config(source)
    payload = json.loads(source.read_text(encoding="utf-8"))
    morphology_indices, morphology_names = active_morphology_traits(cfg)
    genome_size = ParametricPolicy.genome_size_for_config(cfg)
    capacity_count = capacity_gene_count(cfg)
    functional_count = functional_module_gene_count(cfg)
    physiology_count = physiology_gene_count(cfg)

    resource_periods = tuple(int(v) for v in cfg.environment.resource_cycle_periods)
    resource_waves = tuple(tuple(float(x) for x in v) for v in cfg.environment.resource_primary_wave_vectors)
    diffusion = tuple(float(v) for v in cfg.environment.resource_diffusion_rates)
    checks = {
        "qualified_inherited_reproduction": cfg.entities.reproduction_schema == "inherited-conservative-offspring-investment-v2",
        "four_non_substitutable_resource_outcomes": len(cfg.environment.resource_effect_matrix) == 4,
        "four_distinct_resource_periods": len(set(resource_periods)) == 4,
        "four_distinct_resource_wave_vectors": len(set(resource_waves)) == 4,
        "four_distinct_resource_diffusion_rates": len(set(diffusion)) == 4,
        "abiotic_oxygen_terrain_wear": cfg.environment.physiology_environment_schema == "oxygen-terrain-wear-mosaic-v1",
        "mortality_trace_field": cfg.environment.mortality_trace_schema == "local-decaying-mortality-trace-v1",
        "resource_affinity_enabled": cfg.entities.resource_affinity_schema == "normalized-four-resource-affinity-v1",
        "resource_sensing_enabled": cfg.entities.resource_sensing_schema == "inherited-demand-gated-affinity-budgeted-gradient-radius-v4",
        "knowledge_and_memory_enabled": bool(cfg.knowledge.enabled and cfg.knowledge.latent_policy_enabled and cfg.knowledge.working_memory_enabled),
        "elastic_capacities_enabled": bool(cfg.differentiation.enabled and capacity_count == 4),
        "compositional_functional_modules_enabled": bool(cfg.functional_modules.enabled and cfg.functional_modules.module_count >= 4 and functional_count > 100),
        "inherited_regulatory_physiology_enabled": bool(cfg.physiology.enabled and physiology_count >= 20),
        "plural_genome_size": genome_size >= 600,
    }
    failed = [name for name, passed in checks.items() if not passed]
    if failed:
        raise ValueError(f"baseline is not an integrated ecological subject: failed={failed}")
    effective = asdict(cfg)
    return {
        "schema": SCHEMA,
        "source_path": str(source),
        "source_file_sha256": _sha256_bytes(source.read_bytes()),
        "effective_config_sha256": _canonical_sha256(effective),
        "genome": {
            "total_coordinates": genome_size,
            "active_morphology_coordinates": len(morphology_indices),
            "active_morphology_names": list(morphology_names),
            "strategy_coordinates": ParametricPolicy.STRATEGY_GENES,
            "capacity_coordinates": capacity_count,
            "capacity_names": list(CAPACITY_TRAIT_NAMES),
            "functional_module_coordinates": functional_count,
            "physiology_coordinates": physiology_count,
        },
        "environment": {
            "resource_channels": 4,
            "resource_cycle_periods": list(resource_periods),
            "resource_primary_wave_vectors": [list(v) for v in resource_waves],
            "resource_diffusion_rates": list(diffusion),
            "abiotic_axes": ["oxygen", "terrain", "wear"],
            "ecological_memory_fields": ["mortality_trace"],
        },
        "checks": checks,
        "config_payload_sha256": _canonical_sha256(payload),
        "interpretation": "qualified-plural-baseline-ready-for-persistence-panel",
        "causal_effect_claim_authorized": False,
    }


def prepare(*, template: str | Path, output: str | Path) -> dict[str, Any]:
    source = Path(template)
    report = inspect_baseline(source)
    destination = Path(output)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(source.read_bytes())
    if _sha256_bytes(destination.read_bytes()) != report["source_file_sha256"]:
        raise RuntimeError("integrated baseline copy drifted")
    manifest = dict(report)
    manifest["output_path"] = str(destination)
    manifest["output_file_sha256"] = _sha256_bytes(destination.read_bytes())
    manifest_path = Path(f"{destination}.manifest.json")
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return manifest


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Verify/copy one plural ecological-subject baseline without attaching another isolated gene.")
    parser.add_argument("--template", required=True)
    parser.add_argument("--output")
    parser.add_argument("--verify-only", action="store_true")
    args = parser.parse_args(argv)
    if args.verify_only:
        report = inspect_baseline(args.template)
    else:
        if not args.output:
            parser.error("--output is required unless --verify-only is used")
        report = prepare(template=args.template, output=args.output)
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
