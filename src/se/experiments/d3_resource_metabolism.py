"""Run D3-A inherited resource buffering and delayed conversion evolution.

D3-A is a substrate experiment, not a niche or module-maturity gate.  Raw
external resources are assimilated into inherited bounded stores, become
visible to the fixed functional operators as occupancy, and can only affect
body state through inherited per-channel conversion capacity on later ticks.
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
    RESOURCE_METABOLISM_FUNCTIONAL_MODULE_SCHEMA,
    RESOURCE_METABOLISM_INPUT_SCHEMA,
    REGULATORY_OUTPUT_SCHEMA,
)
from se.differentiation.physiology import RESOURCE_METABOLISM_PHYSIOLOGY_SCHEMA
from se.runtime.sim import Simulation

PLAN_SCHEMA = "d3-resource-metabolism-plan-v1"
RESULT_SCHEMA = "d3-resource-metabolism-results-v1"

SCALAR_METRICS = (
    "alive",
    "effective_lineages",
    "largest_lineage_fraction",
    "mean_energy",
    "mean_integrity",
    "mean_oxygenation",
    "mean_tissue_condition",
    "mean_structure_condition",
    "environment_resource_effective_dimensions",
    "physiology_environment_effective_dimensions",
    "physiology_genetic_effective_dimensions",
    "resource_metabolism_genetic_effective_dimensions",
    "functional_harvest_preference_effective_dimensions",
    "functional_output_basis_effective_dimensions",
    "functional_output_basis_active_port_count",
)

VECTOR_METRICS = (
    "resource_store_mean",
    "resource_store_std",
    "resource_store_total",
    "resource_store_occupancy_mean",
    "resource_store_capacity_mean",
    "resource_conversion_capacity_mean",
    "resource_stored_total",
    "resource_store_overflow_total",
    "resource_converted_total",
    "resource_store_decay_total",
    "resource_store_death_loss_total",
    "resource_body_realized_total",
    "physiology_genetic_trait_names",
    "physiology_genetic_trait_means",
    "physiology_genetic_trait_standard_deviations",
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


def _require_d3a(cfg: SimulationConfig) -> None:
    validate_config(cfg)
    if cfg.functional_modules.schema != RESOURCE_METABOLISM_FUNCTIONAL_MODULE_SCHEMA:
        raise ValueError("D3-A requires resource-metabolism functional modules v6")
    if cfg.functional_modules.input_schema != RESOURCE_METABOLISM_INPUT_SCHEMA:
        raise ValueError("D3-A requires internal resource-store occupancy inputs")
    if cfg.functional_modules.output_schema != REGULATORY_OUTPUT_SCHEMA:
        raise ValueError("D3-A retains the regulatory-drive output vocabulary")
    if cfg.physiology.schema != RESOURCE_METABOLISM_PHYSIOLOGY_SCHEMA:
        raise ValueError("D3-A requires conservative resource-metabolism physiology v4")


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
        "functional_schema": RESOURCE_METABOLISM_FUNCTIONAL_MODULE_SCHEMA,
        "physiology_schema": RESOURCE_METABOLISM_PHYSIOLOGY_SCHEMA,
        "single_active_population_per_seed": True,
        "pass_fail_gate": False,
        "raw_harvest_enters_bounded_store": True,
        "minimum_conversion_delay_ticks": 1,
        "store_occupancy_visible_to_functional_operators": True,
        "inherited_store_capacity_per_channel": True,
        "inherited_conversion_capacity_per_channel": True,
        "equal_channel_base_capacity_and_rate": True,
        "direct_same_tick_body_effect_disabled": True,
        "store_ledger_terms": [
            "stored",
            "converted",
            "decayed",
            "death loss",
            "final living store",
        ],
        "named_metabolic_roles": False,
        "diversity_reward_or_protection": False,
        "ecological_role_labels": False,
        "module_copy_number_changed": False,
    }


def _ledger_row(run: dict[str, Any]) -> dict[str, Any]:
    final = run["final"]
    stored = [float(v) for v in final.get("resource_stored_total", [0.0] * 4)]
    converted = [float(v) for v in final.get("resource_converted_total", [0.0] * 4)]
    decayed = [float(v) for v in final.get("resource_store_decay_total", [0.0] * 4)]
    death = [float(v) for v in final.get("resource_store_death_loss_total", [0.0] * 4)]
    remaining = [float(v) for v in final.get("resource_store_total", [0.0] * 4)]
    residual = [
        stored[i] - converted[i] - decayed[i] - death[i] - remaining[i]
        for i in range(4)
    ]
    scale = max(1.0, max(stored, default=0.0))
    valid = all(abs(value) <= 2.0e-5 * scale for value in residual)
    return {
        "seed": int(run["seed"]),
        "stored": stored,
        "converted": converted,
        "decayed": decayed,
        "death_loss": death,
        "final_living_store": remaining,
        "residual": residual,
        "valid": valid,
    }


def _payload(plan: dict[str, Any], runs: list[dict[str, Any]]) -> dict[str, Any]:
    ledger = [_ledger_row(run) for run in runs]
    trends = {
        "storage_used_in_every_seed": all(
            sum(row["stored"]) > 0.0 for row in ledger
        ),
        "conversion_used_in_every_seed": all(
            sum(row["converted"]) > 0.0 for row in ledger
        ),
        "all_channels_converted_in_every_seed": all(
            all(value > 0.0 for value in row["converted"]) for row in ledger
        ),
        "storage_or_conversion_genetic_variation_observed": all(
            float(run["final"].get("resource_metabolism_genetic_effective_dimensions", 0.0))
            > 0.0
            for run in runs
        ),
        "store_ledger_valid_in_every_seed": all(row["valid"] for row in ledger),
    }
    return {
        "schema": RESULT_SCHEMA,
        "plan": plan,
        "completed_seed_count": len(runs),
        "runs": runs,
        "store_ledger": ledger,
        "stable_trend_summary": trends,
        "decision_scope": "resource-buffering-substrate-not-ecological-proof",
        "recommendation": (
            "retain-buffered-resource-substrate-and-continue-spatiotemporal-ecology"
            if all(trends.values())
            else "inspect-resource-store-ledger-or-capacity-use-before-ecology"
        ),
        "ecological_differentiation_claim": False,
        "module_copy_number_ready": False,
        "interpretation_boundary": (
            "This run establishes whether inherited raw-resource storage and delayed "
            "conversion remain active and conservative during evolution. It does not "
            "establish migration, coexistence, trophic differentiation, or a named metabolism."
        ),
    }


def execute_resource_metabolism(
    cfg: SimulationConfig,
    seeds: Iterable[int],
    output_dir: str | Path,
    *,
    backend: str = "auto",
    until_tick: int | None = None,
    overwrite: bool = False,
) -> dict[str, Any]:
    _require_d3a(cfg)
    selected = parse_seeds(seeds)
    horizon = int(cfg.run.ticks if until_tick is None else until_tick)
    plan = build_plan(selected, horizon)
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    (output / "d3_resource_metabolism_plan.json").write_text(
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
        (output / "d3_resource_metabolism_results.json").write_text(
            json.dumps(_payload(plan, runs), ensure_ascii=False, indent=2), encoding="utf-8"
        )
    result = _payload(plan, runs)
    (output / "d3_resource_metabolism_results.md").write_text(
        render_markdown(result), encoding="utf-8"
    )
    return result


def render_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# D3-A inherited resource buffering and delayed conversion",
        "",
        f"Schema: `{payload['schema']}`",
        f"Completed seeds: `{payload['completed_seed_count']}`",
        "",
        "| Seed | Alive | Store occupancy mean | Converted total | Genetic dimensions | Ledger valid |",
        "|---:|---:|---:|---:|---:|---:|",
    ]
    ledger_by_seed = {row["seed"]: row for row in payload["store_ledger"]}
    for run in payload["runs"]:
        final = run["final"]
        occupancy = final.get("resource_store_occupancy_mean", [0.0] * 4)
        converted = final.get("resource_converted_total", [0.0] * 4)
        lines.append(
            f"| {run['seed']} | {final.get('alive', 0)} | "
            f"{sum(float(v) for v in occupancy) / 4.0} | "
            f"{sum(float(v) for v in converted)} | "
            f"{final.get('resource_metabolism_genetic_effective_dimensions', 0.0)} | "
            f"{ledger_by_seed[int(run['seed'])]['valid']} |"
        )
    lines.extend(
        [
            "",
            "## Stable trend summary",
            "",
            *[
                f"- {name.replace('_', ' ')}: `{value}`"
                for name, value in payload["stable_trend_summary"].items()
            ],
            "",
            "## Decision",
            "",
            f"`{payload['recommendation']}`",
            "",
            payload["interpretation_boundary"],
            "",
        ]
    )
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True)
    parser.add_argument("--seeds", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--backend", choices=("cpu", "gpu", "auto"), default="auto")
    parser.add_argument("--until-tick", type=int)
    parser.add_argument("--overwrite", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    payload = execute_resource_metabolism(
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
                "completed_seed_count": payload["completed_seed_count"],
                "recommendation": payload["recommendation"],
                "results": str(Path(args.output) / "d3_resource_metabolism_results.json"),
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
