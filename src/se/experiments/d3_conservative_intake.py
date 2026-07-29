"""Run D3-B conservative storage-constrained resource intake evolution.

D3-B keeps the inherited stores and one-tick delayed conversion introduced by
D3-A, but moves the capacity check before environmental extraction.  A harvest
request is expressed in raw external units and capped by the amount that can be
assimilated into the carrier's current inherited store room.  Rejected intake
therefore remains in the environment instead of becoming post-harvest overflow.

The experiment is descriptive substrate evolution, not an ecological role or
module-maturity gate.
"""

from __future__ import annotations

import argparse
from dataclasses import asdict, replace
import json
from pathlib import Path
import shutil
from typing import Any, Iterable

import numpy as np

from se.cfg import SimulationConfig, load_config, validate_config
from se.differentiation.functional import (
    RESOURCE_METABOLISM_FUNCTIONAL_MODULE_SCHEMA,
    RESOURCE_METABOLISM_INPUT_SCHEMA,
    REGULATORY_OUTPUT_SCHEMA,
)
from se.differentiation.physiology import (
    CONSERVATIVE_INTAKE_PHYSIOLOGY_SCHEMA,
)
from se.policy import ParametricPolicy
from se.runtime.resource_metabolism import resource_metabolism_diagnostics
from se.runtime.sim import Simulation

PLAN_SCHEMA = "d3-conservative-intake-plan-v1"
RESULT_SCHEMA = "d3-conservative-intake-results-v2"
INTAKE_SCHEMA = "storage-room-constrained-preharvest-v2"

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
    "functional_harvest_preference_effective_dimensions",
    "functional_output_basis_effective_dimensions",
    "functional_output_basis_active_port_count",
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


def _require_d3b(cfg: SimulationConfig) -> None:
    validate_config(cfg)
    if cfg.functional_modules.schema != RESOURCE_METABOLISM_FUNCTIONAL_MODULE_SCHEMA:
        raise ValueError("D3-B requires resource-metabolism functional modules v6")
    if cfg.functional_modules.input_schema != RESOURCE_METABOLISM_INPUT_SCHEMA:
        raise ValueError("D3-B requires internal resource-store occupancy inputs")
    if cfg.functional_modules.output_schema != REGULATORY_OUTPUT_SCHEMA:
        raise ValueError("D3-B retains the regulatory-drive output vocabulary")
    if cfg.physiology.schema != CONSERVATIVE_INTAKE_PHYSIOLOGY_SCHEMA:
        raise ValueError("D3-B requires conservative intake physiology resource-v5")


def build_plan(seeds: Iterable[int], horizon: int) -> dict[str, Any]:
    selected = parse_seeds(seeds)
    if horizon <= 0:
        raise ValueError("horizon must be positive")
    return {
        "schema": PLAN_SCHEMA,
        "seeds": list(selected),
        "horizon_ticks": int(horizon),
        "functional_schema": RESOURCE_METABOLISM_FUNCTIONAL_MODULE_SCHEMA,
        "physiology_schema": CONSERVATIVE_INTAKE_PHYSIOLOGY_SCHEMA,
        "resource_intake_schema": INTAKE_SCHEMA,
        "single_active_population_per_seed": True,
        "pass_fail_gate": False,
        "raw_request_capped_before_environment_commit": True,
        "capacity_rejected_raw_resource_remains_external": True,
        "minimum_conversion_delay_ticks": 1,
        "policy_resource_utility_respects_current_store_room": True,
        "legacy_resource_v4_replay_preserved": True,
        "named_metabolic_roles": False,
        "diversity_reward_or_protection": False,
        "ecological_role_labels": False,
        "module_copy_number_changed": False,
    }


def _vector_from_metric_row(final: dict[str, Any], prefix: str, width: int) -> list[float]:
    return [float(final.get(f"{prefix}_{index}_total", 0.0)) for index in range(width)]


def _snapshot(simulation: Simulation, final: dict[str, Any]) -> dict[str, Any]:
    result: dict[str, Any] = {
        name: final[name]
        for name in SCALAR_METRICS
        if name in final and isinstance(final[name], (int, float))
    }
    result.update(
        resource_metabolism_diagnostics(
            simulation.entities,
            simulation.cfg,
            gene_start=ParametricPolicy.physiology_gene_start(simulation.cfg),
        )
    )
    result.update(
        {
            "harvested_resources_total": simulation.total_harvested_resources.tolist(),
            "admitted_harvest_requests_total": simulation.total_requested_harvest_resources.tolist(),
            "resource_intake_capacity_rejected_total": (
                simulation.total_resource_intake_capacity_rejected.tolist()
            ),
            "resource_stored_total": simulation.total_resource_stored.tolist(),
            "resource_store_overflow_total": simulation.total_resource_store_overflow.tolist(),
            "resource_converted_total": simulation.total_resource_converted.tolist(),
            "resource_store_decay_total": simulation.total_resource_store_decay.tolist(),
            "resource_store_death_loss_total": simulation.total_resource_store_death_loss.tolist(),
            "resource_body_realized_total": simulation.total_resource_body_realized.tolist(),
        }
    )
    return result


def _store_ledger(run: dict[str, Any]) -> dict[str, Any]:
    final = run["final"]
    stored = np.asarray(final["resource_stored_total"], dtype=np.float64)
    converted = np.asarray(final["resource_converted_total"], dtype=np.float64)
    decayed = np.asarray(final["resource_store_decay_total"], dtype=np.float64)
    death = np.asarray(final["resource_store_death_loss_total"], dtype=np.float64)
    remaining = np.asarray(final["resource_store_total"], dtype=np.float64)
    residual = stored - converted - decayed - death - remaining
    scale = max(1.0, float(np.max(stored, initial=0.0)))
    return {
        "seed": int(run["seed"]),
        "residual": residual.tolist(),
        "valid": bool(np.all(np.abs(residual) <= 2.0e-5 * scale)),
    }


def _intake_ledger(run: dict[str, Any]) -> dict[str, Any]:
    final = run["final"]
    admitted = np.asarray(final["admitted_harvest_requests_total"], dtype=np.float64)
    rejected = np.asarray(final["resource_intake_capacity_rejected_total"], dtype=np.float64)
    harvested = np.asarray(final["harvested_resources_total"], dtype=np.float64)
    overflow = np.asarray(final["resource_store_overflow_total"], dtype=np.float64)
    unconstrained = admitted + rejected
    environmental_shortfall = np.maximum(admitted - harvested, 0.0)
    valid = bool(
        np.all(np.isfinite(unconstrained))
        and np.all(unconstrained >= -1.0e-12)
        and np.all(rejected >= -1.0e-12)
        and np.all(environmental_shortfall >= -1.0e-12)
        and np.all(overflow <= 2.0e-5 * max(1.0, float(np.max(harvested, initial=0.0))))
    )
    return {
        "seed": int(run["seed"]),
        "unconstrained_request": unconstrained.tolist(),
        "admitted_request": admitted.tolist(),
        "capacity_rejected": rejected.tolist(),
        "environmental_shortfall": environmental_shortfall.tolist(),
        "actual_harvested": harvested.tolist(),
        "post_assimilation_overflow": overflow.tolist(),
        "valid": valid,
    }


def _payload(plan: dict[str, Any], runs: list[dict[str, Any]]) -> dict[str, Any]:
    store_ledgers = [_store_ledger(run) for run in runs]
    intake_ledgers = [_intake_ledger(run) for run in runs]
    trends = {
        "capacity_rejection_observed_in_any_seed": any(
            sum(row["capacity_rejected"]) > 0.0 for row in intake_ledgers
        ),
        "post_assimilation_overflow_within_tolerance_in_every_seed": all(
            row["valid"] for row in intake_ledgers
        ),
        "intake_ledger_valid_in_every_seed": all(row["valid"] for row in intake_ledgers),
        "store_ledger_valid_in_every_seed": all(row["valid"] for row in store_ledgers),
        "storage_and_conversion_used_in_every_seed": all(
            sum(run["final"]["resource_stored_total"]) > 0.0
            and sum(run["final"]["resource_converted_total"]) > 0.0
            for run in runs
        ),
    }
    ready = all(trends.values())
    return {
        "schema": RESULT_SCHEMA,
        "plan": plan,
        "completed_seed_count": len(runs),
        "runs": runs,
        "intake_ledger": intake_ledgers,
        "store_ledger": store_ledgers,
        "stable_trend_summary": trends,
        "decision_scope": "conservative-intake-substrate-not-ecological-proof",
        "recommendation": (
            "retain-conservative-intake-and-continue-external-resource-recycling"
            if ready
            else "inspect-intake-or-store-ledger-before-external-recycling"
        ),
        "ecological_differentiation_claim": False,
        "module_copy_number_ready": False,
        "interpretation_boundary": (
            "This run checks whether inherited buffering can reject unusable raw intake "
            "before environmental removal while retaining delayed conversion. It does not "
            "establish migration, detrital recycling, trophic transfer, coexistence, or a named metabolism."
        ),
    }


def execute_conservative_intake(
    cfg: SimulationConfig,
    seeds: Iterable[int],
    output_dir: str | Path,
    *,
    backend: str = "auto",
    until_tick: int | None = None,
    overwrite: bool = False,
) -> dict[str, Any]:
    _require_d3b(cfg)
    selected = parse_seeds(seeds)
    horizon = int(cfg.run.ticks if until_tick is None else until_tick)
    plan = build_plan(selected, horizon)
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    (output / "d3_conservative_intake_plan.json").write_text(
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
        runs.append(
            {"seed": seed, "output": str(run_dir), "final": _snapshot(simulation, final)}
        )
        (output / "d3_conservative_intake_results.json").write_text(
            json.dumps(_payload(plan, runs), ensure_ascii=False, indent=2), encoding="utf-8"
        )
    payload = _payload(plan, runs)
    (output / "d3_conservative_intake_results.md").write_text(
        render_markdown(payload), encoding="utf-8"
    )
    return payload


def render_markdown(payload: dict[str, Any]) -> str:
    intake = {int(row["seed"]): row for row in payload["intake_ledger"]}
    lines = [
        "# D3-B conservative storage-constrained intake",
        "",
        f"Schema: `{payload['schema']}`",
        f"Completed seeds: `{payload['completed_seed_count']}`",
        "",
        "| Seed | Alive | Capacity rejected | Harvested | Post-store overflow | Intake ledger |",
        "|---:|---:|---:|---:|---:|---:|",
    ]
    for run in payload["runs"]:
        row = intake[int(run["seed"])]
        lines.append(
            f"| {run['seed']} | {run['final'].get('alive', 0)} | "
            f"{sum(row['capacity_rejected'])} | {sum(row['actual_harvested'])} | "
            f"{sum(row['post_assimilation_overflow'])} | {row['valid']} |"
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
    payload = execute_conservative_intake(
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
                "results": str(Path(args.output) / "d3_conservative_intake_results.json"),
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
