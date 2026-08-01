"""Prepare one budget-constrained inherited-capability source configuration."""
from __future__ import annotations

import argparse
from copy import deepcopy
from dataclasses import asdict
import hashlib
import json
import math
from pathlib import Path
from typing import Any

from se.analysis.capability_budget import verify_budget
from se.cfg import load_config
from se.config_identity import strip_inactive_extensions

SCHEMA = "d1-capability-source-config-v1"
SPEC_SCHEMA = "d1-capability-attachment-v1"
REPRODUCTION_SCHEMA = "inherited-conservative-offspring-investment-v2"
ALLOWED_CHANGED_PATHS = {
    "entities.reproduction_schema",
    "entities.reproduction_investment_levels",
}


def _load(path: str | Path) -> dict[str, Any]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"expected a JSON object: {path}")
    return payload


def _canonical_sha256(payload: Any) -> str:
    return hashlib.sha256(
        json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def _physical_fingerprint(path: str | Path) -> str:
    effective = strip_inactive_extensions(asdict(load_config(path)))
    effective.pop("run", None)
    return _canonical_sha256(effective)


def _changed_paths(before: Any, after: Any, prefix: str = "") -> list[str]:
    if isinstance(before, dict) and isinstance(after, dict):
        changed: list[str] = []
        for key in sorted(set(before) | set(after)):
            path = f"{prefix}.{key}" if prefix else str(key)
            if key not in before or key not in after:
                changed.append(path)
            else:
                changed.extend(_changed_paths(before[key], after[key], path))
        return changed
    if before != after:
        return [prefix]
    return []


def validate_spec(spec: dict[str, Any], budget: dict[str, Any]) -> dict[str, Any]:
    if spec.get("schema") != SPEC_SCHEMA:
        raise ValueError(f"unsupported capability specification schema: {spec.get('schema')!r}")
    if spec.get("runtime_schema") != REPRODUCTION_SCHEMA:
        raise ValueError("this source builder supports only inherited conservative offspring investment")
    if int(spec.get("morphology_gene_index", -1)) != 6:
        raise ValueError("offspring-investment capability must use morphology gene 6")
    if not bool(spec.get("single_gene_independent_effect")):
        raise ValueError("the selected capability must act independently through one gene")
    combination = spec.get("combination", {})
    if bool(combination.get("required")):
        raise ValueError("D1-O deliberately admits one non-combinatorial capability only")
    maturation = spec.get("maturation", {})
    minimum_generations = int(maturation.get("minimum_generations_before_effect_window", -1))
    required_generations = int(
        budget["maturation_contract"][
            "single_gene_independent_capability_minimum_generations_before_effect_window"
        ]
    )
    if minimum_generations < required_generations:
        raise ValueError("capability effect window begins before the budgeted maturation generation")

    costs = spec.get("costs", {})
    recurring = float(costs.get("structural_energy_per_tick", -1.0)) + float(
        costs.get("idle_use_energy_per_tick", -1.0)
    )
    if recurring < 0.0:
        raise ValueError("capability recurring costs must be explicit and non-negative")
    if recurring > float(
        budget["attachment_budget"]["maximum_new_recurring_cost_per_entity_tick"]
    ) + 1e-15:
        raise ValueError("capability recurring cost exceeds the D1-N attachment budget")
    development = float(costs.get("extra_development_energy_per_newborn", -1.0))
    if development < 0.0:
        raise ValueError("extra development cost must be explicit and non-negative")
    if development > float(
        budget["attachment_budget"]["maximum_extra_development_cost_per_newborn"]
    ) + 1e-15:
        raise ValueError("capability development cost exceeds the D1-N attachment budget")

    levels = tuple(float(value) for value in spec.get("offspring_investment_levels", ()))
    if not levels or tuple(sorted(set(levels))) != levels or any(value <= 0.0 for value in levels):
        raise ValueError("offspring investment levels must be strictly increasing and positive")
    baseline = float(budget["observed_reference"]["fixed_offspring_endowment_energy"])
    if not math.isclose(sum(levels) / len(levels), baseline, rel_tol=0.0, abs_tol=1e-12):
        raise ValueError("initial random-population mean endowment must equal the qualified fixed baseline")
    max_deviation = max(abs(value - baseline) for value in levels)
    allowed_deviation = float(
        budget["attachment_budget"]["maximum_event_debit_deviation_from_fixed_endowment"]
    )
    if max_deviation > allowed_deviation + 1e-12:
        raise ValueError("offspring investment level exceeds the event-debit deviation budget")
    if float(costs.get("initial_population_mean_event_debit_shift", math.inf)) != 0.0:
        raise ValueError("initial random population must have zero mean event-debit shift")
    if not bool(costs.get("parent_transfer_is_conservative")):
        raise ValueError("offspring investment must be a conservative parent-to-newborn transfer")
    if not str(spec.get("direct_physical_interface", "")).strip():
        raise ValueError("capability must declare a direct physical interface")
    if not str(spec.get("inherited_source", "")).strip():
        raise ValueError("capability must declare its inherited source")
    return {
        "recurring_cost_per_entity_tick": recurring,
        "extra_development_energy_per_newborn": development,
        "baseline_offspring_endowment": baseline,
        "mean_offspring_endowment": sum(levels) / len(levels),
        "maximum_event_debit_deviation": max_deviation,
        "minimum_generations_before_effect_window": minimum_generations,
    }


def build_config(
    *, template: str | Path, budget_path: str | Path, capability_path: str | Path, output: str | Path
) -> dict[str, Any]:
    budget = verify_budget(budget_path)
    spec = _load(capability_path)
    validation = validate_spec(spec, budget)
    source = Path(template)
    before = _load(source)
    physical_fingerprint = _physical_fingerprint(source)
    if physical_fingerprint != budget.get("physical_substrate_fingerprint_sha256"):
        raise ValueError("qualified substrate template does not match the frozen D1-N physical fingerprint")

    after = deepcopy(before)
    after["entities"]["reproduction_schema"] = REPRODUCTION_SCHEMA
    after["entities"]["reproduction_investment_levels"] = [
        float(value) for value in spec["offspring_investment_levels"]
    ]
    changed = _changed_paths(before, after)
    unexpected = sorted(set(changed) - ALLOWED_CHANGED_PATHS)
    missing = sorted(ALLOWED_CHANGED_PATHS - set(changed))
    if unexpected or missing:
        raise ValueError(
            f"capability attachment changed unexpected paths={unexpected} or missed required paths={missing}"
        )

    destination = Path(output)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(after, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    load_config(destination)
    config_sha = hashlib.sha256(destination.read_bytes()).hexdigest()
    manifest = {
        "schema": SCHEMA,
        "template": str(source),
        "output": str(destination),
        "config_sha256": config_sha,
        "manifest_path": f"{destination}.manifest.json",
        "budget": str(Path(budget_path)),
        "budget_sha256": budget["budget_sha256"],
        "capability": str(Path(capability_path)),
        "capability_sha256": _canonical_sha256(spec),
        "capability_id": spec["capability_id"],
        "purpose": "budgeted-capability-source-health-only",
        "new_gene_added": False,
        "existing_gene_activated": True,
        "physical_substrate_unchanged": True,
        "changed_paths": changed,
        "cost_and_maturation_validation": validation,
        "paired_effect_interpretation_authorized": False,
        "evolutionary_interpretation_authorized": False,
        "next_gate": "source-health-contract-v2",
    }
    manifest_path = Path(f"{destination}.manifest.json")
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    legacy_manifest = destination.with_suffix(".manifest.json")
    if legacy_manifest != manifest_path and legacy_manifest.exists():
        legacy_manifest.unlink()
    return manifest


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Prepare a budget-constrained capability source config.")
    parser.add_argument("--template", required=True)
    parser.add_argument("--budget", required=True)
    parser.add_argument("--capability", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args(argv)
    manifest = build_config(
        template=args.template,
        budget_path=args.budget,
        capability_path=args.capability,
        output=args.output,
    )
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
