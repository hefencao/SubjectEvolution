"""Descriptive D2-L inherited regulatory-physiology evolution run.

D2-L does not ask whether a named organ or module is sufficiently expressed.
It evolves a fixed, transparent operator kernel above inherited transport,
reserve, conversion, messenger, fatigue, and repair parameters, then records
whether those lower-level causal links remain in use.  No ecological role,
module copy-number, or maturity gate is inferred from the result.
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
    REGULATORY_FUNCTIONAL_MODULE_SCHEMA,
    REGULATORY_OUTPUT_SCHEMA,
)
from se.differentiation.physiology import REGULATORY_PHYSIOLOGY_SCHEMA
from se.runtime.sim import Simulation

PLAN_SCHEMA = "d2-regulatory-physiology-plan-v2"
RESULT_SCHEMA = "d2-regulatory-physiology-results-v2"

SCALAR_METRICS = (
    "alive",
    "effective_lineages",
    "largest_lineage_fraction",
    "mean_energy",
    "mean_integrity",
    "mean_oxygenation",
    "mean_tissue_condition",
    "mean_structure_condition",
    "mean_metabolic_fatigue",
    "mean_mobilization_messenger",
    "mean_maintenance_messenger",
    "mean_messenger_precursor",
    "mean_physiology_sensor_multiplier",
    "environment_resource_effective_dimensions",
    "physiology_environment_effective_dimensions",
    "physiology_genetic_effective_dimensions",
    "functional_harvest_preference_effective_dimensions",
    "functional_physiology_output_effective_dimensions",
    "functional_physiology_output_changed_entity_fraction",
    "functional_output_basis_effective_dimensions",
    "functional_output_basis_active_port_count",
    "physiology_oxygen_uptake_total",
    "physiology_oxygen_use_total",
    "physiology_messenger_synthesis_total",
    "physiology_messenger_decay_total",
    "physiology_messenger_precursor_used_total",
    "physiology_messenger_precursor_recovered_total",
    "physiology_messenger_energy_total",
    "physiology_computation_energy_total",
    "physiology_computation_oxygen_total",
    "physiology_fatigue_generated_total",
    "physiology_fatigue_cleared_total",
    "physiology_hypoxia_tissue_damage_total",
    "physiology_wear_tissue_damage_total",
    "physiology_wear_structure_damage_total",
    "physiology_repair_material_total",
    "physiology_repair_tissue_total",
    "physiology_repair_structure_total",
    "physiology_capacity_maintenance_energy_total",
    "physiology_capacity_development_energy_total",
)

VECTOR_METRICS = (
    "physiology_environment_correlations",
    "physiology_environment_means",
    "physiology_environment_standard_deviations",
    "physiology_genetic_trait_names",
    "physiology_genetic_trait_means",
    "physiology_genetic_trait_standard_deviations",
    "functional_physiology_output_names",
    "functional_physiology_output_mean",
    "functional_physiology_output_std",
    "functional_physiology_output_abs_mean_by_port",
    "functional_output_basis_port_names",
    "functional_output_basis_std_by_port",
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


def _require_v5(cfg: SimulationConfig) -> None:
    validate_config(cfg)
    if cfg.functional_modules.schema != REGULATORY_FUNCTIONAL_MODULE_SCHEMA:
        raise ValueError("D2-L requires v5 regulatory functional modules")
    if cfg.functional_modules.output_schema != REGULATORY_OUTPUT_SCHEMA:
        raise ValueError("D2-L requires the regulatory-drive output schema")
    if cfg.physiology.schema != REGULATORY_PHYSIOLOGY_SCHEMA:
        raise ValueError("D2-L requires conservative inherited regulatory physiology v3")


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
    for name in VECTOR_METRICS:
        value = progress.get(name, final.get(name))
        if isinstance(value, list):
            result[name] = value
    return result


def build_plan(seeds: Iterable[int], horizon: int) -> dict[str, Any]:
    selected = parse_seeds(seeds)
    if horizon <= 0:
        raise ValueError("horizon must be positive")
    return {
        "schema": PLAN_SCHEMA,
        "seeds": list(selected),
        "horizon_ticks": int(horizon),
        "physiology_schema": REGULATORY_PHYSIOLOGY_SCHEMA,
        "conservation_mode": "non-negative-flow-ledger-with-energy-debt-preservation-v1",
        "all_runtime_flows_must_be_finite_non_negative": True,
        "negative_energy_debt_preserved_for_world_starvation_settlement": True,
        "single_active_population_per_seed": True,
        "pass_fail_gate": False,
        "fixed_weight_lifetime_dynamics": True,
        "online_weight_learning": False,
        "module_expression_threshold_not_used_as_continuation_gate": True,
        "module_outputs_are_regulatory_requests_not_direct_actions": True,
        "inherited_physiology_parameters": [
            "oxygen transport and reserve",
            "aerobic conversion and anaerobic tolerance",
            "fatigue clearance",
            "repair conversion and allocation",
            "messenger synthesis decay and receptor gain",
        ],
        "bounded_dynamic_states": [
            "oxygenation",
            "tissue condition",
            "structure condition",
            "metabolic fatigue",
            "mobilization messenger",
            "maintenance messenger",
            "messenger precursor",
        ],
        "module_regulatory_requests": [
            "oxygen uptake",
            "mobilization bus",
            "maintenance bus",
            "sensory attention",
        ],
        "counterfactual_interfaces": [
            "module regulatory-output neutralization",
            "messenger receptor blockade",
            "bounded physiology state clamps",
        ],
        "named_organs_or_hormones": False,
        "diversity_reward_or_protection": False,
        "ecological_role_labels": False,
        "module_copy_number_changed": False,
    }


def execute_regulatory_physiology(
    cfg: SimulationConfig,
    seeds: Iterable[int],
    output_dir: str | Path,
    *,
    backend: str = "cpu",
    until_tick: int | None = None,
    overwrite: bool = False,
) -> dict[str, Any]:
    _require_v5(cfg)
    selected = parse_seeds(seeds)
    horizon = int(cfg.run.ticks if until_tick is None else until_tick)
    plan = build_plan(selected, horizon)
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    (output / "d2_regulatory_physiology_plan.json").write_text(
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
            json.dumps(asdict(run_cfg), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        simulation = Simulation(run_cfg, run_dir, backend=backend)
        final = simulation.run(until_tick=horizon)
        progress = _last_jsonl(run_dir / "evolution_progress.jsonl")
        runs.append(
            {"seed": seed, "output": str(run_dir), "final": _snapshot(final, progress)}
        )
        (output / "d2_regulatory_physiology_results.json").write_text(
            json.dumps(_payload(plan, runs), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    result = _payload(plan, runs)
    (output / "d2_regulatory_physiology_results.md").write_text(
        render_markdown(result), encoding="utf-8"
    )
    return result


def _payload(plan: dict[str, Any], runs: list[dict[str, Any]]) -> dict[str, Any]:
    trends = {
        "regulatory_output_used_in_every_seed": all(
            float(run["final"].get("functional_physiology_output_changed_entity_fraction", 0.0))
            > 0.0
            for run in runs
        ),
        "physiology_genetic_variation_observed": any(
            float(run["final"].get("physiology_genetic_effective_dimensions", 0.0)) > 0.0
            for run in runs
        ),
        "messenger_turnover_observed": any(
            float(run["final"].get("physiology_messenger_synthesis_total", 0.0)) > 0.0
            and float(run["final"].get("physiology_messenger_decay_total", 0.0)) > 0.0
            for run in runs
        ),
        "finite_precursor_turnover_observed": any(
            float(run["final"].get("physiology_messenger_precursor_used_total", 0.0)) > 0.0
            and float(run["final"].get("physiology_messenger_precursor_recovered_total", 0.0)) > 0.0
            for run in runs
        ),
        "computation_cost_observed": any(
            float(run["final"].get("physiology_computation_energy_total", 0.0)) > 0.0
            and float(run["final"].get("physiology_computation_oxygen_total", 0.0)) > 0.0
            for run in runs
        ),
        "fatigue_turnover_observed": any(
            float(run["final"].get("physiology_fatigue_generated_total", 0.0)) > 0.0
            and float(run["final"].get("physiology_fatigue_cleared_total", 0.0)) > 0.0
            for run in runs
        ),
        "repair_or_damage_flow_observed": any(
            float(run["final"].get("physiology_repair_material_total", 0.0)) > 0.0
            or float(run["final"].get("physiology_hypoxia_tissue_damage_total", 0.0)) > 0.0
            or float(run["final"].get("physiology_wear_structure_damage_total", 0.0)) > 0.0
            for run in runs
        ),
    }
    return {
        "schema": RESULT_SCHEMA,
        "plan": plan,
        "completed_seed_count": len(runs),
        "runs": runs,
        "stable_trend_summary": trends,
        "flow_ledger_summary": {
            "all_cumulative_flows_non_negative": all(
                all(
                    float(run["final"].get(name, 0.0)) >= 0.0
                    for name in (
                        "physiology_messenger_synthesis_total",
                        "physiology_messenger_decay_total",
                        "physiology_messenger_precursor_used_total",
                        "physiology_messenger_precursor_recovered_total",
                        "physiology_messenger_energy_total",
                        "physiology_computation_energy_total",
                        "physiology_computation_oxygen_total",
                        "physiology_fatigue_generated_total",
                        "physiology_fatigue_cleared_total",
                        "physiology_repair_material_total",
                    )
                )
                for run in runs
            ),
            "validated_each_tick": True,
        },
        "decision_scope": "causal-substrate-evolution-not-module-maturity-gate",
        "interpretation_boundary": (
            "The run checks whether a fixed operator kernel, inherited physiology parameters, "
            "finite messenger dynamics, and conserved execution costs remain active during "
            "evolution. It does not establish a named organ, mature ecological differentiation, "
            "completed food-chain dynamics, or a reason to change module copy number."
        ),
    }


def render_markdown(result: dict[str, Any]) -> str:
    lines = [
        "# D2-L regulatory physiology substrate",
        "",
        f"Schema: `{result['schema']}`",
        f"Completed seeds: `{result['completed_seed_count']}`",
        "",
        "| Seed | Alive | O2 | Fatigue | Mobilization | Maintenance | Precursor | Genetic dimensions |",
        "|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for run in result["runs"]:
        final = run["final"]
        lines.append(
            f"| {run['seed']} | {final.get('alive', 'n/a')} | "
            f"{final.get('mean_oxygenation', 'n/a')} | "
            f"{final.get('mean_metabolic_fatigue', 'n/a')} | "
            f"{final.get('mean_mobilization_messenger', 'n/a')} | "
            f"{final.get('mean_maintenance_messenger', 'n/a')} | "
            f"{final.get('mean_messenger_precursor', 'n/a')} | "
            f"{final.get('physiology_genetic_effective_dimensions', 'n/a')} |"
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
    parser.add_argument("--backend", default="cpu", choices=("cpu", "gpu", "auto"))
    parser.add_argument("--until-tick", type=int)
    parser.add_argument("--overwrite", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    result = execute_regulatory_physiology(
        load_config(args.config),
        parse_seeds(args.seeds),
        args.output,
        backend=args.backend,
        until_tick=args.until_tick,
        overwrite=args.overwrite,
    )
    print(
        json.dumps(
            {
                "passed": True,
                "result": str(Path(args.output) / "d2_regulatory_physiology_results.json"),
                "completed_seed_count": result["completed_seed_count"],
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
