"""Descriptive v4 physiological ecology capability run.

This is deliberately not a pass/fail module-expression audit.  It checks that
independent abiotic demand fields and lower-level body state remain active over
several evolutionary runs, while leaving stable niche and food-chain claims to
later ecological stages.
"""

from __future__ import annotations

import argparse
from dataclasses import asdict, replace
import json
from pathlib import Path
import shutil
from typing import Any, Iterable

from se.cfg import SimulationConfig, load_config, validate_config
from se.differentiation.functional import (
    PHYSIOLOGICAL_FUNCTIONAL_MODULE_SCHEMA,
    PHYSIOLOGICAL_OUTPUT_SCHEMA,
)
from se.runtime.sim import Simulation

PLAN_SCHEMA = "d2-physiological-ecology-plan-v1"
RESULT_SCHEMA = "d2-physiological-ecology-results-v1"

SCALAR_METRICS = (
    "alive",
    "effective_lineages",
    "largest_lineage_fraction",
    "mean_energy",
    "mean_integrity",
    "mean_oxygenation",
    "mean_tissue_condition",
    "mean_structure_condition",
    "mean_physiology_sensor_multiplier",
    "environment_resource_effective_dimensions",
    "physiology_environment_effective_dimensions",
    "functional_harvest_preference_effective_dimensions",
    "functional_physiology_output_effective_dimensions",
    "functional_physiology_output_changed_entity_fraction",
    "functional_output_basis_effective_dimensions",
    "functional_output_basis_active_port_count",
    "physiology_oxygen_uptake_total",
    "physiology_oxygen_use_total",
    "physiology_hypoxia_tissue_damage_total",
    "physiology_wear_tissue_damage_total",
    "physiology_wear_structure_damage_total",
    "physiology_repair_material_total",
    "physiology_repair_tissue_total",
    "physiology_repair_structure_total",
)


def parse_seeds(value: str | Iterable[int]) -> tuple[int, ...]:
    seeds = (
        tuple(int(item.strip()) for item in value.split(",") if item.strip())
        if isinstance(value, str)
        else tuple(int(item) for item in value)
    )
    if not seeds or len(set(seeds)) != len(seeds):
        raise ValueError("seeds must be a non-empty unique set")
    return seeds


def _require_v4(cfg: SimulationConfig) -> None:
    validate_config(cfg)
    if cfg.functional_modules.schema != PHYSIOLOGICAL_FUNCTIONAL_MODULE_SCHEMA:
        raise ValueError("D2-K requires v4 physiological functional modules")
    if cfg.functional_modules.output_schema != PHYSIOLOGICAL_OUTPUT_SCHEMA:
        raise ValueError("D2-K requires the physiology-drive output schema")
    if not cfg.physiology.enabled:
        raise ValueError("D2-K requires enabled dynamic physiology")


def _last_jsonl(path: Path) -> dict[str, Any]:
    last: dict[str, Any] = {}
    if path.is_file():
        with path.open("r", encoding="utf-8") as handle:
            for line in handle:
                if line.strip():
                    last = json.loads(line)
    return last


def _snapshot(final: dict[str, Any], progress: dict[str, Any]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for name in SCALAR_METRICS:
        value = progress.get(name, final.get(name))
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            result[name] = value
    for name in (
        "physiology_environment_correlations",
        "physiology_environment_means",
        "physiology_environment_standard_deviations",
        "functional_physiology_output_names",
        "functional_physiology_output_mean",
        "functional_physiology_output_std",
        "functional_physiology_output_abs_mean_by_port",
        "functional_output_basis_port_names",
        "functional_output_basis_std_by_port",
    ):
        value = progress.get(name, final.get(name))
        if isinstance(value, list):
            result[name] = value
    return result


def execute_physiological_ecology(
    cfg: SimulationConfig,
    seeds: Iterable[int],
    output_dir: str | Path,
    *,
    backend: str = "auto",
    until_tick: int | None = None,
    overwrite: bool = False,
) -> dict[str, Any]:
    _require_v4(cfg)
    selected = parse_seeds(seeds)
    horizon = int(cfg.run.ticks if until_tick is None else until_tick)
    if horizon <= 0:
        raise ValueError("until_tick must be positive")
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    plan = {
        "schema": PLAN_SCHEMA,
        "seeds": list(selected),
        "horizon_ticks": horizon,
        "single_active_population_per_seed": True,
        "pass_fail_gate": False,
        "module_expression_threshold_not_used_as_continuation_gate": True,
        "lower_level_body_state": ["oxygenation", "tissue_condition", "structure_condition"],
        "module_drives": ["perfusion", "contractile", "sensory", "repair"],
        "abiotic_fields": ["oxygen_availability", "terrain_resistance", "mechanical_wear"],
        "diversity_reward_or_protection": False,
        "ecological_role_labels": False,
        "module_copy_number_changed": False,
    }
    (output / "d2_physiological_ecology_plan.json").write_text(
        json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    runs: list[dict[str, Any]] = []
    for seed in selected:
        run_dir = output / f"seed_{seed}"
        if run_dir.exists() and any(run_dir.iterdir()):
            if not overwrite:
                raise RuntimeError(f"output exists: {run_dir}; pass --overwrite")
            shutil.rmtree(run_dir)
        run_dir.mkdir(parents=True, exist_ok=True)
        run_cfg = replace(cfg, run=replace(cfg.run, seed=seed, ticks=horizon))
        (run_dir / "resolved_config.json").write_text(
            json.dumps(asdict(run_cfg), ensure_ascii=False, indent=2), encoding="utf-8"
        )
        simulation = Simulation(run_cfg, run_dir, backend=backend)
        final = simulation.run(until_tick=horizon)
        progress = _last_jsonl(run_dir / "evolution_progress.jsonl")
        runs.append({"seed": seed, "output": str(run_dir), "final": _snapshot(final, progress)})
        partial = _payload(plan, runs)
        (output / "d2_physiological_ecology_results.json").write_text(
            json.dumps(partial, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    result = _payload(plan, runs)
    (output / "d2_physiological_ecology_results.md").write_text(
        render_markdown(result), encoding="utf-8"
    )
    return result


def _payload(plan: dict[str, Any], runs: list[dict[str, Any]]) -> dict[str, Any]:
    usage = {
        "dynamic_oxygenation_in_every_seed": all(
            float(run["final"].get("mean_oxygenation", 1.0)) < 0.999999 for run in runs
        ),
        "physiology_output_used_in_every_seed": all(
            float(run["final"].get("functional_physiology_output_changed_entity_fraction", 0.0)) > 0.0
            for run in runs
        ),
        "abiotic_field_dimension_above_one_in_every_seed": all(
            float(run["final"].get("physiology_environment_effective_dimensions", 0.0)) > 1.0
            for run in runs
        ),
        "wear_or_hypoxia_cost_observed": any(
            float(run["final"].get("physiology_hypoxia_tissue_damage_total", 0.0)) > 0.0
            or float(run["final"].get("physiology_wear_tissue_damage_total", 0.0)) > 0.0
            or float(run["final"].get("physiology_wear_structure_damage_total", 0.0)) > 0.0
            for run in runs
        ),
        "repair_flow_observed": any(
            float(run["final"].get("physiology_repair_material_total", 0.0)) > 0.0
            for run in runs
        ),
    }
    return {
        "schema": RESULT_SCHEMA,
        "plan": plan,
        "completed_seed_count": len(runs),
        "runs": runs,
        "stable_trend_summary": usage,
        "decision_scope": "substrate-and-environment-trend-not-final-ecological-proof",
        "interpretation_boundary": (
            "The run checks that lower-level physiological composition and independent abiotic "
            "demands remain active. It does not require mature module expression, a completed "
            "food chain, stable niche coexistence, or a module copy-number decision."
        ),
    }


def render_markdown(result: dict[str, Any]) -> str:
    lines = [
        "# D2-K physiological ecology substrate",
        "",
        f"Schema: `{result['schema']}`",
        f"Completed seeds: `{result['completed_seed_count']}`",
        "",
        "| Seed | Alive | Oxygenation | Tissue | Structure | Abiotic dimensions | Physiology changed |",
        "|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for run in result["runs"]:
        final = run["final"]
        lines.append(
            f"| {run['seed']} | {final.get('alive', 'n/a')} | "
            f"{final.get('mean_oxygenation', 'n/a')} | {final.get('mean_tissue_condition', 'n/a')} | "
            f"{final.get('mean_structure_condition', 'n/a')} | "
            f"{final.get('physiology_environment_effective_dimensions', 'n/a')} | "
            f"{final.get('functional_physiology_output_changed_entity_fraction', 'n/a')} |"
        )
    lines.extend(["", "## Stable trend summary", ""])
    lines.extend(
        f"- {name.replace('_', ' ')}: `{value}`"
        for name, value in result["stable_trend_summary"].items()
    )
    lines.extend(["", "## Interpretation boundary", "", result["interpretation_boundary"], ""])
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True)
    parser.add_argument("--seeds", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--backend", default="auto", choices=("cpu", "gpu", "auto"))
    parser.add_argument("--until-tick", type=int)
    parser.add_argument("--overwrite", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    result = execute_physiological_ecology(
        load_config(args.config),
        parse_seeds(args.seeds),
        args.output,
        backend=args.backend,
        until_tick=args.until_tick,
        overwrite=args.overwrite,
    )
    print(json.dumps({"passed": True, "result": str(Path(args.output) / "d2_physiological_ecology_results.json"), "completed_seed_count": result["completed_seed_count"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
