"""Run D3-E shared-checkpoint spatial collection/processing coupling.

D3-E adds a role-free abiotic processing-support field that is phase shifted
from the persistent four-channel renewal opportunity field.  Support changes
only internal raw-store conversion throughput.  Every converted unit has an
explicit energy cost.  A paired neutral-support branch reuses the same tick-0
checkpoint while preserving costs, genes, resource fields, and all other
mechanisms.
"""
from __future__ import annotations

import argparse
import json
import shutil
from dataclasses import asdict, replace
from pathlib import Path
from typing import Any, Iterable

import numpy as np

from se.checkpointing import read_checkpoint_bundle
from se.cfg import SimulationConfig, load_config, validate_config
from se.differentiation.physiology import (
    SPATIAL_PROCESSING_PHYSIOLOGY_SCHEMA,
    spatial_processing_enabled,
)
from se.env.diversity import (
    PERSISTENT_ORTHOGONAL_ENVIRONMENT_SCHEMA,
    SPATIAL_PROCESSING_SUPPORT_SCHEMA,
    persistent_orthogonal_renewal_enabled,
)
from se.env.recycling import resource_recycling_diagnostics
from se.experiments.d3_conservative_intake import parse_seeds
from se.experiments.d3_external_recycling import _ledger as recycling_ledger
from se.experiments.d3_persistent_resource_renewal import _resource_ledger
from se.policy import ParametricPolicy
from se.runtime.resource_metabolism import resource_metabolism_diagnostics
from se.runtime.sim import Simulation

PLAN_SCHEMA = "d3-spatial-collection-processing-plan-v2"
RESULT_SCHEMA = "d3-spatial-collection-processing-results-v2"
ABLATION = "neutralize-spatial-processing-support"
BRANCHES = ("spatial-support", "neutral-support")


def _require(cfg: SimulationConfig) -> None:
    validate_config(cfg)
    if not persistent_orthogonal_renewal_enabled(cfg):
        raise ValueError("D3-E requires persistent orthogonal resource renewal")
    if cfg.physiology.schema != SPATIAL_PROCESSING_PHYSIOLOGY_SCHEMA:
        raise ValueError("D3-E requires transport-metabolism-...-resource-v7")
    if not spatial_processing_enabled(cfg):
        raise ValueError("D3-E requires phase-shifted spatial processing support")


def build_plan(cfg: SimulationConfig, seeds: Iterable[int], horizon: int) -> dict[str, Any]:
    _require(cfg)
    selected = parse_seeds(seeds)
    if horizon <= 0:
        raise ValueError("horizon must be positive")
    return {
        "schema": PLAN_SCHEMA,
        "seeds": list(selected),
        "horizon_ticks": int(horizon),
        "shared_checkpoint_tick": 0,
        "branches": list(BRANCHES),
        "environment_schema": PERSISTENT_ORTHOGONAL_ENVIRONMENT_SCHEMA,
        "processing_support_schema": SPATIAL_PROCESSING_SUPPORT_SCHEMA,
        "processing_support_amplitude": float(
            cfg.environment.resource_processing_support_amplitude
        ),
        "processing_support_phase_relation": "quarter-cycle-shifted-from-renewal-wave-basis",
        "processing_energy_per_unit": list(
            cfg.physiology.resource_processing_energy_per_unit
        ),
        "processing_energy_charged_before_body_outcomes": True,
        "float32_residue_inventory_roundoff_recorded_separately": True,
        "neutral_support_multiplier": 1.0,
        "neutral_support_preserves_processing_cost": True,
        "neutral_support_preserves_genotype": True,
        "neutral_support_preserves_resource_fields": True,
        "neutral_support_preserves_checkpoint_state": True,
        "entity_lineage_and_group_feedback": False,
        "named_resource_roles": False,
        "diversity_reward_or_protection": False,
        "ecological_role_labels": False,
        "pass_fail_gate": False,
    }


def _snapshot(simulation: Simulation, final: dict[str, Any]) -> dict[str, Any]:
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
    support_mean = np.divide(
        simulation.total_resource_processing_support_weighted_sum,
        simulation.total_resource_processing_support_weight,
        out=np.ones(4, dtype=np.float64),
        where=simulation.total_resource_processing_support_weight > 0.0,
    )
    result.update(
        {
            "resource_processing_support_ablation_enabled": bool(
                simulation.resource_processing_support_ablation_enabled
            ),
            "resource_processing_requested_total": simulation.total_resource_processing_requested.tolist(),
            "resource_processing_supported_total": simulation.total_resource_processing_supported.tolist(),
            "resource_processing_support_limited_total": simulation.total_resource_processing_support_limited.tolist(),
            "resource_processing_support_accelerated_total": simulation.total_resource_processing_support_accelerated.tolist(),
            "resource_processing_energy_rejected_total": simulation.total_resource_processing_energy_rejected.tolist(),
            "resource_processing_support_weighted_mean": support_mean.tolist(),
            "resource_processing_energy_cost_total": float(
                simulation.total_resource_processing_energy_cost
            ),
            "resource_initial_total": environment.initial_resource_total.tolist(),
            "resource_renewal_source_total": environment.total_resource_renewal_source.tolist(),
            "resource_renewal_sink_total": environment.total_resource_renewal_sink.tolist(),
            "resource_field_roundoff_total": environment.total_resource_field_roundoff.tolist(),
            "resource_harvest_roundoff_total": environment.total_resource_harvest_roundoff.tolist(),
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


def _selected_outcomes(final: dict[str, Any]) -> dict[str, float]:
    return {
        "alive": float(final.get("alive", 0)),
        "births_total": float(final.get("births_total", 0)),
        "deaths_total": float(final.get("deaths_total", 0)),
        "mean_energy": float(final.get("mean_energy", 0.0)),
        "resource_converted_total": float(sum(final["resource_converted_total"])),
        "processing_energy_cost_total": float(
            final["resource_processing_energy_cost_total"]
        ),
        "processing_support_limited_total": float(
            sum(final["resource_processing_support_limited_total"])
        ),
        "processing_support_accelerated_total": float(
            sum(final["resource_processing_support_accelerated_total"])
        ),
    }


def _branch(
    checkpoint: Path,
    output: Path,
    *,
    horizon: int,
    backend: str,
    neutralize: bool,
) -> dict[str, Any]:
    simulation = Simulation.from_checkpoint(
        checkpoint, output, backend=backend, until_tick=horizon
    )
    genotype_before = simulation.entities.genotype.copy()
    resource_before = np.asarray(simulation.environment.resources).copy()
    if neutralize:
        simulation.apply_intervention(ABLATION)
    if not np.array_equal(genotype_before, simulation.entities.genotype):
        raise RuntimeError("D3-E support ablation modified genotype")
    if not np.array_equal(resource_before, np.asarray(simulation.environment.resources)):
        raise RuntimeError("D3-E support ablation modified resource fields")
    final = simulation.run(until_tick=horizon)
    replay = json.loads((output / "replay_provenance.json").read_text(encoding="utf-8"))
    return {
        "branch": "neutral-support" if neutralize else "spatial-support",
        "output": str(output),
        "checkpoint_state_sha256": replay["checkpoint_lineage"][-1]["checkpoint_state_sha256"],
        "interventions": [ABLATION] if neutralize else [],
        "scientific_validity": simulation.scientific_validity(),
        "final": _snapshot(simulation, final),
    }


def _pair(seed: int, branches: list[dict[str, Any]]) -> dict[str, Any]:
    by_name = {row["branch"]: row for row in branches}
    active = _selected_outcomes(by_name["spatial-support"]["final"])
    neutral = _selected_outcomes(by_name["neutral-support"]["final"])
    common = sorted(set(active) & set(neutral))
    return {
        "seed": int(seed),
        "shared_checkpoint_state": (
            by_name["spatial-support"]["checkpoint_state_sha256"]
            == by_name["neutral-support"]["checkpoint_state_sha256"]
        ),
        "branches": branches,
        "paired_difference_spatial_minus_neutral": {
            key: active[key] - neutral[key] for key in common
        },
    }


def _payload(plan: dict[str, Any], pairs: list[dict[str, Any]]) -> dict[str, Any]:
    all_branches = [branch for pair in pairs for branch in pair["branches"]]
    resource_ledgers = [
        {"branch": branch["branch"], **_resource_ledger({"seed": pair["seed"], "final": branch["final"]})}
        for pair in pairs
        for branch in pair["branches"]
    ]
    recycling_ledgers = [
        {"branch": branch["branch"], **recycling_ledger({"seed": pair["seed"], "final": branch["final"]})}
        for pair in pairs
        for branch in pair["branches"]
    ]
    active = [
        branch["final"]
        for branch in all_branches
        if branch["branch"] == "spatial-support"
    ]
    neutral = [
        branch["final"]
        for branch in all_branches
        if branch["branch"] == "neutral-support"
    ]
    trends = {
        "shared_tick0_checkpoint_in_every_pair": all(
            pair["shared_checkpoint_state"] for pair in pairs
        ),
        "processing_cost_observed_in_every_branch": all(
            row["resource_processing_energy_cost_total"] > 0.0
            for row in active + neutral
        ),
        "spatial_support_exposure_nonuniform_in_every_active_branch": all(
            max(row["resource_processing_support_weighted_mean"])
            - min(row["resource_processing_support_weighted_mean"])
            > 1.0e-6
            for row in active
        ),
        "neutral_support_exactly_one_in_every_ablation_branch": all(
            np.allclose(
                row["resource_processing_support_weighted_mean"],
                np.ones(4),
                atol=1.0e-12,
                rtol=0.0,
            )
            for row in neutral
        ),
        "support_limited_processing_observed_in_every_active_branch": all(
            sum(row["resource_processing_support_limited_total"]) > 0.0
            for row in active
        ),
        "support_accelerated_processing_observed_in_every_active_branch": all(
            sum(row["resource_processing_support_accelerated_total"]) > 0.0
            for row in active
        ),
        "external_resource_ledger_valid_in_every_branch": all(
            row["valid"] for row in resource_ledgers
        ),
        "external_recycling_ledger_valid_in_every_branch": all(
            row["valid"] for row in recycling_ledgers
        ),
    }
    substrate_ready = all(trends.values())
    return {
        "schema": RESULT_SCHEMA,
        "plan": plan,
        "completed_seed_count": len(pairs),
        "pairs": pairs,
        "external_resource_ledger": resource_ledgers,
        "external_recycling_ledger": recycling_ledgers,
        "stable_trend_summary": trends,
        "recommendation": (
            "retain-costed-spatial-processing-substrate-and-audit-response"
            if substrate_ready
            else "inspect-spatial-processing-substrate"
        ),
        "decision_scope": "costed-collection-processing-substrate-not-migration-or-ecotype-proof",
        "causal_claim_scope": (
            "Only paired branch differences are attributable to spatial support neutralization under the shared checkpoint contract; finite-seed signs are not generalized ecological effects."
        ),
        "ecological_differentiation_claim": False,
        "interpretation_boundary": (
            "D3-E tests whether location-dependent abiotic processing support can constrain or accelerate internal conversion while retaining explicit energy cost and conservative resource ledgers. It does not establish migration, collection-processing specialization, coexistence, trophic transfer, or named ecological roles."
        ),
    }


def render_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# D3-E costed spatial collection-processing coupling",
        "",
        f"Schema: `{payload['schema']}`",
        "",
        "| Seed | Shared checkpoint | Active alive | Neutral alive | Δ converted | Active cost | Neutral cost |",
        "|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for pair in payload["pairs"]:
        by_name = {row["branch"]: row["final"] for row in pair["branches"]}
        diff = pair["paired_difference_spatial_minus_neutral"]
        lines.append(
            f"| {pair['seed']} | {pair['shared_checkpoint_state']} | "
            f"{by_name['spatial-support'].get('alive', 0)} | "
            f"{by_name['neutral-support'].get('alive', 0)} | "
            f"{diff['resource_converted_total']} | "
            f"{by_name['spatial-support']['resource_processing_energy_cost_total']} | "
            f"{by_name['neutral-support']['resource_processing_energy_cost_total']} |"
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
        payload["causal_claim_scope"],
        "",
        payload["interpretation_boundary"],
        "",
    ]
    return "\n".join(lines)


def execute_spatial_processing(
    cfg: SimulationConfig,
    seeds: Iterable[int],
    output_dir: str | Path,
    *,
    backend: str = "auto",
    until_tick: int | None = None,
    overwrite: bool = False,
) -> dict[str, Any]:
    _require(cfg)
    selected = parse_seeds(seeds)
    horizon = int(cfg.run.ticks if until_tick is None else until_tick)
    plan = build_plan(cfg, selected, horizon)
    output = Path(output_dir)
    if output.exists() and any(output.iterdir()):
        if not overwrite:
            raise RuntimeError(f"output exists: {output}; pass --overwrite")
        shutil.rmtree(output)
    output.mkdir(parents=True, exist_ok=True)
    (output / "d3_spatial_processing_plan.json").write_text(
        json.dumps(plan, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    pairs: list[dict[str, Any]] = []
    for seed in selected:
        seed_dir = output / f"seed_{seed}"
        source_dir = seed_dir / "source"
        active_dir = seed_dir / "spatial_support"
        neutral_dir = seed_dir / "neutral_support"
        source_dir.mkdir(parents=True, exist_ok=True)
        run_cfg = replace(cfg, run=replace(cfg.run, seed=seed, ticks=horizon))
        (seed_dir / "resolved_config.json").write_text(
            json.dumps(asdict(run_cfg), ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        source = Simulation(run_cfg, source_dir, backend=backend)
        checkpoint = source.save_full_checkpoint(seed_dir / "checkpoint_00000000.sechk")
        metadata, _ = read_checkpoint_bundle(checkpoint)
        branches = [
            _branch(
                checkpoint,
                active_dir,
                horizon=horizon,
                backend=backend,
                neutralize=False,
            ),
            _branch(
                checkpoint,
                neutral_dir,
                horizon=horizon,
                backend=backend,
                neutralize=True,
            ),
        ]
        if any(
            branch["checkpoint_state_sha256"] != metadata["state_sha256"]
            for branch in branches
        ):
            raise RuntimeError("D3-E replay branch did not preserve checkpoint state")
        pairs.append(_pair(seed, branches))
        partial = _payload(plan, pairs)
        (output / "d3_spatial_processing_results.json").write_text(
            json.dumps(partial, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    payload = _payload(plan, pairs)
    (output / "d3_spatial_processing_results.md").write_text(
        render_markdown(payload), encoding="utf-8"
    )
    return payload


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True)
    parser.add_argument("--seeds", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--backend", choices=("cpu", "gpu", "auto"), default="auto")
    parser.add_argument("--until-tick", type=int)
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args(argv)
    payload = execute_spatial_processing(
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
