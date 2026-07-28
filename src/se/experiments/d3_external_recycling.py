"""Run D3-C identity-preserving external resource recycling.

Internal raw-store decay and raw material carried by dead entities enter a
four-channel spatial residue field.  Residue diffuses and returns to the same
resource channel only when environmental capacity is available.  The
experiment remains a substrate run: it does not predefine decomposers,
scavengers, trophic levels, or ecological roles.
"""
from __future__ import annotations
import argparse, json, shutil
from dataclasses import asdict, replace
from pathlib import Path
from typing import Any, Iterable
import numpy as np

from se.cfg import SimulationConfig, load_config, validate_config
from se.differentiation.functional import (
    RESOURCE_METABOLISM_FUNCTIONAL_MODULE_SCHEMA,
    RESOURCE_METABOLISM_INPUT_SCHEMA,
    REGULATORY_OUTPUT_SCHEMA,
)
from se.differentiation.physiology import RESOURCE_RECYCLING_PHYSIOLOGY_SCHEMA
from se.env.recycling import resource_recycling_diagnostics
from se.experiments.d3_conservative_intake import parse_seeds
from se.policy import ParametricPolicy
from se.runtime.resource_metabolism import resource_metabolism_diagnostics
from se.runtime.sim import Simulation

PLAN_SCHEMA="d3-external-recycling-plan-v1"
RESULT_SCHEMA="d3-external-recycling-results-v1"
RECYCLING_SCHEMA="identity-preserving-spatial-residue-v1"


def _require(cfg: SimulationConfig) -> None:
    validate_config(cfg)
    if cfg.functional_modules.schema != RESOURCE_METABOLISM_FUNCTIONAL_MODULE_SCHEMA:
        raise ValueError("D3-C requires resource-metabolism functional modules v6")
    if cfg.functional_modules.input_schema != RESOURCE_METABOLISM_INPUT_SCHEMA:
        raise ValueError("D3-C requires internal resource-store occupancy inputs")
    if cfg.functional_modules.output_schema != REGULATORY_OUTPUT_SCHEMA:
        raise ValueError("D3-C retains the regulatory-drive output vocabulary")
    if cfg.physiology.schema != RESOURCE_RECYCLING_PHYSIOLOGY_SCHEMA:
        raise ValueError("D3-C requires resource recycling physiology resource-v6")


def build_plan(seeds: Iterable[int], horizon: int) -> dict[str, Any]:
    selected=parse_seeds(seeds)
    if horizon <= 0:
        raise ValueError("horizon must be positive")
    return {
        "schema": PLAN_SCHEMA,
        "seeds": list(selected),
        "horizon_ticks": int(horizon),
        "physiology_schema": RESOURCE_RECYCLING_PHYSIOLOGY_SCHEMA,
        "resource_recycling_schema": RECYCLING_SCHEMA,
        "store_decay_deposits_same_channel_residue": True,
        "death_store_deposits_same_channel_residue": True,
        "minimum_external_residue_delay_ticks": 1,
        "residue_diffusion_reuses_channel_resource_diffusion": True,
        "residue_release_reuses_channel_store_decay_rate": True,
        "release_limited_by_external_resource_capacity": True,
        "named_decomposer_or_scavenger_roles": False,
        "diversity_reward_or_protection": False,
        "ecological_role_labels": False,
        "pass_fail_gate": False,
    }


def _snapshot(sim: Simulation, final: dict[str, Any]) -> dict[str, Any]:
    result={k:v for k,v in final.items() if isinstance(v,(int,float,list,str,bool))}
    result.update(resource_metabolism_diagnostics(
        sim.entities, sim.cfg, gene_start=ParametricPolicy.physiology_gene_start(sim.cfg)
    ))
    result.update(resource_recycling_diagnostics(sim.environment))
    result.update({
        "resource_stored_total": sim.total_resource_stored.tolist(),
        "resource_converted_total": sim.total_resource_converted.tolist(),
        "resource_store_decay_total": sim.total_resource_store_decay.tolist(),
        "resource_store_death_loss_total": sim.total_resource_store_death_loss.tolist(),
        "resource_residue_deposited_total": sim.total_resource_residue_deposited.tolist(),
        "resource_residue_released_total": sim.total_resource_residue_released.tolist(),
    })
    return result


def _ledger(run: dict[str, Any]) -> dict[str, Any]:
    f=run["final"]
    decay=np.asarray(f["resource_store_decay_total"], dtype=np.float64)
    death=np.asarray(f["resource_store_death_loss_total"], dtype=np.float64)
    deposited=np.asarray(f["resource_residue_deposited_total"], dtype=np.float64)
    released=np.asarray(f["resource_residue_released_total"], dtype=np.float64)
    remaining=np.asarray(f["resource_residue_total"], dtype=np.float64)
    source_residual=decay+death-deposited
    external_residual=deposited-released-remaining
    scale=max(1.0,float(np.max(deposited, initial=0.0)))
    valid=bool(
        np.all(np.isfinite(source_residual)) and np.all(np.isfinite(external_residual))
        and np.all(np.abs(source_residual) <= 2.0e-5*scale)
        and np.all(np.abs(external_residual) <= 2.0e-5*scale)
    )
    return {
        "seed": int(run["seed"]),
        "source_residual": source_residual.tolist(),
        "external_residual": external_residual.tolist(),
        "valid": valid,
    }


def _payload(plan: dict[str, Any], runs: list[dict[str, Any]]) -> dict[str, Any]:
    ledgers=[_ledger(run) for run in runs]
    trends={
        "store_decay_deposited_in_every_seed": all(sum(r["final"]["resource_store_decay_total"])>0 for r in runs),
        "death_store_source_observed_in_any_seed": any(
            sum(r["final"]["resource_store_death_loss_total"]) > 0 for r in runs
        ),
        "external_residue_released_in_every_seed": all(sum(r["final"]["resource_residue_released_total"])>0 for r in runs),
        "external_residue_ledger_valid_in_every_seed": all(r["valid"] for r in ledgers),
        "storage_and_conversion_used_in_every_seed": all(sum(r["final"]["resource_converted_total"])>0 for r in runs),
    }
    readiness = (
        trends["store_decay_deposited_in_every_seed"]
        and trends["external_residue_released_in_every_seed"]
        and trends["external_residue_ledger_valid_in_every_seed"]
        and trends["storage_and_conversion_used_in_every_seed"]
    )
    return {
        "schema": RESULT_SCHEMA,
        "plan": plan,
        "completed_seed_count": len(runs),
        "runs": runs,
        "recycling_ledger": ledgers,
        "stable_trend_summary": trends,
        "recommendation": (
            "retain-external-recycling-and-continue-spatial-collection-processing"
            if readiness else "inspect-external-recycling-ledger"
        ),
        "decision_scope": "external-matter-recycling-substrate-not-trophic-proof",
        "ecological_differentiation_claim": False,
        "interpretation_boundary": (
            "This run establishes an identity-preserving external residue cycle for internal store decay and death-carried raw material. "
            "It does not establish decomposers, scavengers, trophic transfer, coexistence, or a named metabolism."
        ),
    }


def render_markdown(payload: dict[str, Any]) -> str:
    ledgers={int(r["seed"]):r for r in payload["recycling_ledger"]}
    lines=["# D3-C identity-preserving external recycling", "", f"Schema: `{payload['schema']}`", "", "| Seed | Alive | Deposited | Released | Final residue | Ledger |", "|---:|---:|---:|---:|---:|---:|"]
    for run in payload["runs"]:
        f=run["final"]
        lines.append(f"| {run['seed']} | {f.get('alive',0)} | {sum(f['resource_residue_deposited_total'])} | {sum(f['resource_residue_released_total'])} | {sum(f['resource_residue_total'])} | {ledgers[int(run['seed'])]['valid']} |")
    lines += ["", "## Stable trend summary", ""]
    lines += [f"- {k.replace('_',' ')}: `{v}`" for k,v in payload["stable_trend_summary"].items()]
    lines += ["", f"Recommendation: `{payload['recommendation']}`", "", payload["interpretation_boundary"], ""]
    return "\n".join(lines)


def execute_external_recycling(cfg: SimulationConfig, seeds: Iterable[int], output_dir: str|Path, *, backend: str="cpu", until_tick: int|None=None, overwrite: bool=False) -> dict[str, Any]:
    _require(cfg)
    selected=parse_seeds(seeds)
    horizon=int(cfg.run.ticks if until_tick is None else until_tick)
    plan=build_plan(selected,horizon)
    output=Path(output_dir); output.mkdir(parents=True, exist_ok=True)
    (output/"d3_external_recycling_plan.json").write_text(json.dumps(plan,ensure_ascii=False,indent=2)+"\n", encoding="utf-8")
    runs=[]
    for seed in selected:
        run_dir=output/f"seed_{seed}"
        if run_dir.exists() and any(run_dir.iterdir()):
            if not overwrite: raise RuntimeError(f"output exists: {run_dir}; pass --overwrite")
            shutil.rmtree(run_dir)
        run_dir.mkdir(parents=True,exist_ok=True)
        run_cfg=replace(cfg,run=replace(cfg.run,seed=seed,ticks=horizon))
        (run_dir/"resolved_config.json").write_text(json.dumps(asdict(run_cfg),ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
        sim=Simulation(run_cfg,run_dir,backend=backend)
        final=sim.run(until_tick=horizon)
        runs.append({"seed":seed,"output":str(run_dir),"final":_snapshot(sim,final)})
        (output/"d3_external_recycling_results.json").write_text(json.dumps(_payload(plan,runs),ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    payload=_payload(plan,runs)
    (output/"d3_external_recycling_results.md").write_text(render_markdown(payload),encoding="utf-8")
    return payload


def main(argv: list[str]|None=None) -> int:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--config",required=True); p.add_argument("--seeds",required=True); p.add_argument("--output",required=True)
    p.add_argument("--backend",choices=("cpu","gpu","auto"),default="cpu"); p.add_argument("--until-tick",type=int); p.add_argument("--overwrite",action="store_true")
    a=p.parse_args(argv)
    payload=execute_external_recycling(load_config(a.config),parse_seeds(a.seeds),a.output,backend=a.backend,until_tick=a.until_tick,overwrite=a.overwrite)
    print(json.dumps({"completed_seed_count":payload["completed_seed_count"],"recommendation":payload["recommendation"]}))
    return 0

if __name__=="__main__":
    raise SystemExit(main())
