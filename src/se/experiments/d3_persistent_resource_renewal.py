"""Run D3-D persistent orthogonal resource renewal with external recycling.

The archived v1 orthogonal environment uses channel-specific geometry only for
initialization.  Its logistic regeneration has a uniform carrying capacity, so
common entity depletion can dominate all four channels over long runs.  D3-D
uses the same role-free wave parameters as a continuously moving external
source/sink target, records both open-system fluxes, and retains D3-C's
identity-preserving residue cycle.
"""
from __future__ import annotations

import argparse
import json
import shutil
from dataclasses import asdict, replace
from pathlib import Path
from typing import Any, Iterable

import numpy as np

from se.cfg import SimulationConfig, load_config, validate_config
from se.differentiation.physiology import RESOURCE_RECYCLING_PHYSIOLOGY_SCHEMA
from se.env.diversity import (
    PERSISTENT_ORTHOGONAL_ENVIRONMENT_SCHEMA,
    persistent_orthogonal_renewal_enabled,
)
from se.env.recycling import resource_recycling_diagnostics
from se.experiments.d3_conservative_intake import parse_seeds
from se.experiments.d3_external_recycling import _ledger as recycling_ledger
from se.policy import ParametricPolicy
from se.runtime.resource_metabolism import resource_metabolism_diagnostics
from se.runtime.sim import Simulation

PLAN_SCHEMA = "d3-persistent-resource-renewal-plan-v3"
RESULT_SCHEMA = "d3-persistent-resource-renewal-results-v3"
RENEWAL_SCHEMA = "moving-target-source-sink-v2"


def _require(cfg: SimulationConfig) -> None:
    validate_config(cfg)
    if not persistent_orthogonal_renewal_enabled(cfg):
        raise ValueError(
            "D3-D requires environment schema orthogonal-four-resource-renewal-v2"
        )
    if cfg.physiology.schema != RESOURCE_RECYCLING_PHYSIOLOGY_SCHEMA:
        raise ValueError("D3-D retains D3-C resource-v6 external recycling")


def build_plan(seeds: Iterable[int], horizon: int) -> dict[str, Any]:
    selected = parse_seeds(seeds)
    if horizon <= 0:
        raise ValueError("horizon must be positive")
    return {
        "schema": PLAN_SCHEMA,
        "seeds": list(selected),
        "horizon_ticks": int(horizon),
        "environment_schema": PERSISTENT_ORTHOGONAL_ENVIRONMENT_SCHEMA,
        "renewal_schema": RENEWAL_SCHEMA,
        "moving_target_reuses_role_free_channel_waves": True,
        "renewal_source_and_sink_recorded_separately": True,
        "float32_inventory_roundoff_recorded_separately": True,
        "float32_resource_inventory_roundoff_recorded_separately": True,
        "float32_residue_inventory_roundoff_recorded_separately": True,
        "entity_lineage_and_group_feedback": False,
        "identity_preserving_external_recycling_retained": True,
        "minimum_external_residue_delay_ticks": 1,
        "named_resource_roles": False,
        "diversity_reward_or_protection": False,
        "ecological_role_labels": False,
        "pass_fail_gate": False,
    }


def _snapshot(
    simulation: Simulation,
    final: dict[str, Any],
    initial_diversity: dict[str, Any],
) -> dict[str, Any]:
    environment = simulation.environment
    result = {
        key: value
        for key, value in final.items()
        if isinstance(value, (int, float, list, str, bool))
    }
    result.update(
        resource_metabolism_diagnostics(
            simulation.entities,
            simulation.cfg,
            gene_start=ParametricPolicy.physiology_gene_start(simulation.cfg),
        )
    )
    result.update(resource_recycling_diagnostics(environment))
    result.update(
        {
            "environment_resource_initial_diversity": initial_diversity,
            "environment_resource_final_diversity": environment.resource_diversity_metrics(),
            "resource_initial_total": environment.initial_resource_total.tolist(),
            "resource_renewal_source_total": environment.total_resource_renewal_source.tolist(),
            "resource_renewal_sink_total": environment.total_resource_renewal_sink.tolist(),
            "resource_field_roundoff_total": environment.total_resource_field_roundoff.tolist(),
            "resource_harvest_roundoff_total": environment.total_resource_harvest_roundoff.tolist(),
            "resource_inventory_numerical_adjustment_total": (
                environment.total_resource_field_roundoff
                - environment.total_resource_harvest_roundoff
            ).tolist(),
            "resource_final_total": np.asarray(environment.resources, dtype=np.float64).sum(
                axis=(1, 2)
            ).tolist(),
            "resource_harvested_total": simulation.total_harvested_resources.tolist(),
            "resource_residue_released_total": simulation.total_resource_residue_released.tolist(),
            "resource_store_decay_total": simulation.total_resource_store_decay.tolist(),
            "resource_store_death_loss_total": simulation.total_resource_store_death_loss.tolist(),
            "resource_residue_deposited_total": simulation.total_resource_residue_deposited.tolist(),
            "resource_residue_total": np.asarray(
                environment.resource_residue, dtype=np.float64
            ).sum(axis=(1, 2)).tolist(),
            "resource_converted_total": simulation.total_resource_converted.tolist(),
        }
    )
    return result


def _resource_ledger(run: dict[str, Any]) -> dict[str, Any]:
    final = run["final"]
    initial = np.asarray(final["resource_initial_total"], dtype=np.float64)
    source = np.asarray(final["resource_renewal_source_total"], dtype=np.float64)
    released = np.asarray(final["resource_residue_released_total"], dtype=np.float64)
    harvested = np.asarray(final["resource_harvested_total"], dtype=np.float64)
    sink = np.asarray(final["resource_renewal_sink_total"], dtype=np.float64)
    remaining = np.asarray(final["resource_final_total"], dtype=np.float64)
    field_roundoff = np.asarray(
        final.get("resource_field_roundoff_total", [0.0] * 4), dtype=np.float64
    )
    harvest_roundoff = np.asarray(
        final.get("resource_harvest_roundoff_total", [0.0] * 4), dtype=np.float64
    )
    numerical_adjustment = field_roundoff - harvest_roundoff
    unadjusted_residual = initial + source + released - harvested - sink - remaining
    residual = unadjusted_residual + numerical_adjustment
    scale = np.maximum(
        1.0,
        np.maximum.reduce(
            [
                np.abs(initial),
                np.abs(source),
                np.abs(released),
                np.abs(harvested),
                np.abs(sink),
                np.abs(remaining),
            ]
        ),
    )
    relative = np.abs(residual) / scale
    unadjusted_relative = np.abs(unadjusted_residual) / scale
    adjustment_fraction = np.abs(numerical_adjustment) / scale
    valid = bool(
        np.all(np.isfinite(residual))
        and np.all(relative <= 5.0e-10)
    )
    return {
        "seed": int(run["seed"]),
        "unadjusted_residual": unadjusted_residual.tolist(),
        "field_roundoff": field_roundoff.tolist(),
        "harvest_roundoff": harvest_roundoff.tolist(),
        "numerical_adjustment": numerical_adjustment.tolist(),
        "residual": residual.tolist(),
        "unadjusted_relative_error": unadjusted_relative.tolist(),
        "relative_error": relative.tolist(),
        "numerical_adjustment_fraction": adjustment_fraction.tolist(),
        "valid": valid,
    }


def _payload(plan: dict[str, Any], runs: list[dict[str, Any]]) -> dict[str, Any]:
    resource_ledgers = [_resource_ledger(run) for run in runs]
    recycling_ledgers = [recycling_ledger(run) for run in runs]
    final_dimensions = [
        float(run["final"]["environment_resource_final_diversity"]["resource_effective_dimensions"])
        for run in runs
    ]
    final_correlations = [
        float(run["final"]["environment_resource_final_diversity"]["resource_channel_mean_abs_correlation"])
        for run in runs
    ]
    trends = {
        "renewal_source_observed_in_every_seed": all(
            sum(run["final"]["resource_renewal_source_total"]) > 0.0 for run in runs
        ),
        "renewal_sink_observed_in_every_seed": all(
            sum(run["final"]["resource_renewal_sink_total"]) > 0.0 for run in runs
        ),
        "external_resource_ledger_valid_in_every_seed": all(
            row["valid"] for row in resource_ledgers
        ),
        "external_recycling_ledger_valid_in_every_seed": all(
            row["valid"] for row in recycling_ledgers
        ),
        "resource_channels_remain_multiple_in_every_seed": all(
            value > 1.0 for value in final_dimensions
        ),
    }
    retained = (
        trends["renewal_source_observed_in_every_seed"]
        and trends["renewal_sink_observed_in_every_seed"]
        and trends["external_resource_ledger_valid_in_every_seed"]
        and trends["external_recycling_ledger_valid_in_every_seed"]
    )
    return {
        "schema": RESULT_SCHEMA,
        "plan": plan,
        "completed_seed_count": len(runs),
        "runs": runs,
        "external_resource_ledger": resource_ledgers,
        "external_recycling_ledger": recycling_ledgers,
        "final_resource_effective_dimensions": final_dimensions,
        "final_resource_mean_abs_correlations": final_correlations,
        "stable_trend_summary": trends,
        "recommendation": (
            "retain-persistent-renewal-and-continue-collection-processing-coupling"
            if retained
            else "inspect-persistent-renewal-ledger"
        ),
        "decision_scope": "persistent-abiotic-opportunity-substrate-not-niche-proof",
        "ecological_differentiation_claim": False,
        "interpretation_boundary": (
            "This run tests whether four role-free resource channels retain distinct moving external renewal opportunities while delayed conversion and identity-preserving recycling remain conservative. Float32 inventory settlement is reported separately from physical source, sink, release and harvest fluxes. "
            "It does not establish migration, collection-processing specialization, coexistence, trophic transfer, or named resource roles."
        ),
    }


def render_markdown(payload: dict[str, Any]) -> str:
    ledgers = {int(row["seed"]): row for row in payload["external_resource_ledger"]}
    lines = [
        "# D3-D persistent orthogonal resource renewal",
        "",
        f"Schema: `{payload['schema']}`",
        "",
        "| Seed | Alive | Initial dims | Final dims | Final mean |corr| | Resource ledger |",
        "|---:|---:|---:|---:|---:|---:|",
    ]
    for run in payload["runs"]:
        final = run["final"]
        initial = final["environment_resource_initial_diversity"]
        current = final["environment_resource_final_diversity"]
        lines.append(
            f"| {run['seed']} | {final.get('alive', 0)} | "
            f"{initial['resource_effective_dimensions']} | "
            f"{current['resource_effective_dimensions']} | "
            f"{current['resource_channel_mean_abs_correlation']} | "
            f"{ledgers[int(run['seed'])]['valid']} |"
        )
    lines += ["", "## Stable trend summary", ""]
    lines += [
        f"- {key.replace('_', ' ')}: `{value}`"
        for key, value in payload["stable_trend_summary"].items()
    ]
    lines += [
        "",
        f"Recommendation: `{payload['recommendation']}`",
        "",
        payload["interpretation_boundary"],
        "",
    ]
    return "\n".join(lines)


def execute_persistent_resource_renewal(
    cfg: SimulationConfig,
    seeds: Iterable[int],
    output_dir: str | Path,
    *,
    backend: str = "cpu",
    until_tick: int | None = None,
    overwrite: bool = False,
) -> dict[str, Any]:
    _require(cfg)
    selected = parse_seeds(seeds)
    horizon = int(cfg.run.ticks if until_tick is None else until_tick)
    plan = build_plan(selected, horizon)
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    (output / "d3_persistent_resource_renewal_plan.json").write_text(
        json.dumps(plan, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
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
            json.dumps(asdict(run_cfg), ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        simulation = Simulation(run_cfg, run_dir, backend=backend)
        initial_diversity = simulation.environment.resource_diversity_metrics()
        final = simulation.run(until_tick=horizon)
        runs.append(
            {
                "seed": seed,
                "output": str(run_dir),
                "final": _snapshot(simulation, final, initial_diversity),
            }
        )
        partial = _payload(plan, runs)
        (output / "d3_persistent_resource_renewal_results.json").write_text(
            json.dumps(partial, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    payload = _payload(plan, runs)
    (output / "d3_persistent_resource_renewal_results.md").write_text(
        render_markdown(payload), encoding="utf-8"
    )
    return payload


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True)
    parser.add_argument("--seeds", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--backend", choices=("cpu", "gpu", "auto"), default="cpu")
    parser.add_argument("--until-tick", type=int)
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args(argv)
    payload = execute_persistent_resource_renewal(
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
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
