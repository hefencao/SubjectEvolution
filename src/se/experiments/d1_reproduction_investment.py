"""Shared-checkpoint calibration for inherited conservative offspring investment.

The source trajectory composes the existing conservative four-resource ecology
with an inherited parent-to-offspring energy transfer.  The paired branch keeps
parent eligibility, event overhead, inherited investment, fertility cost,
checkpoint state, and all unrelated world state fixed while dissipating the
newborn energy endowment.  It is a capability and generational-substrate
calibration, not a selection or adaptation test.
"""
from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np

from se.cfg import load_config
from se.differentiation.physiology import external_resource_recycling_enabled
from se.runtime.reproduction import (
    inherited_reproduction_investment_enabled,
    reproduction_energy_cost,
    reproduction_energy_requirement,
    reproduction_investment,
)
from se.runtime.sim import Simulation

PLAN_SCHEMA = "d1-reproduction-investment-shared-checkpoint-plan-v1"
RESULT_SCHEMA = "d1-reproduction-investment-shared-checkpoint-results-v1"
INTERVENTION = "neutralize-conservative-offspring-endowment"
BRANCHES = ("endowment-active", "endowment-neutral")
SCALAR_METRICS = (
    "tick",
    "alive",
    "births_total",
    "deaths_total",
    "mean_energy",
    "mean_age",
    "mean_generation",
    "max_generation",
    "founder_alive_count",
    "descendant_alive_count",
    "founder_alive_fraction",
    "descendant_alive_fraction",
    "cumulative_births_per_initial",
    "living_descendants_per_initial",
    "reproduction_eligible_carrier_ticks_total",
    "reproduction_proposals_total",
    "reproduction_rejected_resource_total",
    "reproduction_investment_mean",
    "reproduction_investment_std",
    "reproduction_energy_requirement_mean",
    "reproduction_energy_requirement_std",
)


@dataclass(frozen=True)
class SourceCheckpoint:
    seed: int
    run_dir: str
    checkpoint_path: str
    checkpoint_sha256: str
    checkpoint_tick: int
    resolved_config_sha256: str
    alive: int
    births_total: int
    deaths_total: int
    mean_generation: float
    max_generation: int
    founder_alive_fraction: float
    descendant_alive_fraction: float
    cumulative_births_per_initial: float
    living_descendants_per_initial: float


@dataclass(frozen=True)
class ReproductionInvestmentPlan:
    schema: str
    source_root: str
    checkpoint_tick: int
    horizon_ticks: int
    runtime_root: str
    sources: tuple[SourceCheckpoint, ...]
    branches: tuple[str, ...] = BRANCHES
    intervention: str = INTERVENTION
    paired_randomness: bool = True
    genotype_preserved: bool = True
    parent_cost_preserved: bool = True
    parent_requirement_preserved: bool = True
    fertility_cost_preserved: bool = True
    resource_fields_preserved_at_intervention: bool = True
    residue_inventory_preserved_at_intervention: bool = True
    internal_stores_preserved_at_intervention: bool = True
    pass_fail_gate: bool = False
    ecological_claim_authorized: bool = False
    selection_claim_authorized: bool = False


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _config_sha256(path: Path) -> str:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def _seed_from_dir(path: Path) -> int:
    if not path.name.startswith("seed_"):
        raise ValueError(f"source directory is not named seed_<id>: {path}")
    return int(path.name.removeprefix("seed_"))


def _summary(path: Path, initial_entities: int) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    alive = int(payload.get("alive", 0))
    births = int(payload.get("births_total", 0))
    founder_fraction = float(payload.get("founder_alive_fraction", 1.0 if alive else 0.0))
    return {
        "alive": alive,
        "births_total": births,
        "deaths_total": int(payload.get("deaths_total", 0)),
        "mean_generation": float(payload.get("mean_generation", 0.0)),
        "max_generation": int(payload.get("max_generation", 0)),
        "founder_alive_fraction": founder_fraction,
        "descendant_alive_fraction": float(
            payload.get("descendant_alive_fraction", 1.0 - founder_fraction if alive else 0.0)
        ),
        "cumulative_births_per_initial": float(
            payload.get("cumulative_births_per_initial", births / max(initial_entities, 1))
        ),
        "living_descendants_per_initial": float(
            payload.get("living_descendants_per_initial", 0.0)
        ),
    }


def discover_sources(source_root: str | Path, checkpoint_tick: int) -> tuple[SourceCheckpoint, ...]:
    root = Path(source_root)
    if checkpoint_tick < 0:
        raise ValueError("checkpoint_tick must be non-negative")
    sources: list[SourceCheckpoint] = []
    for run_dir in sorted(root.glob("seed_*"), key=_seed_from_dir):
        seed = _seed_from_dir(run_dir)
        checkpoint = run_dir / f"checkpoint_{checkpoint_tick:08d}.sechk"
        resolved = run_dir / "resolved_config.json"
        summary = run_dir / "summary.json"
        for path in (checkpoint, resolved, summary):
            if not path.is_file():
                raise FileNotFoundError(f"missing source artifact: {path}")
        cfg = load_config(resolved)
        if int(cfg.run.seed) != seed:
            raise ValueError(
                f"source seed mismatch for {run_dir}: config={cfg.run.seed}, directory={seed}"
            )
        if not inherited_reproduction_investment_enabled(cfg):
            raise ValueError(f"source run does not enable inherited reproduction investment: {run_dir}")
        if not external_resource_recycling_enabled(cfg):
            raise ValueError(f"source run does not retain conservative external recycling: {run_dir}")
        sources.append(
            SourceCheckpoint(
                seed=seed,
                run_dir=str(run_dir),
                checkpoint_path=str(checkpoint),
                checkpoint_sha256=_sha256(checkpoint),
                checkpoint_tick=int(checkpoint_tick),
                resolved_config_sha256=_config_sha256(resolved),
                **_summary(summary, int(cfg.world.initial_entities)),
            )
        )
    if not sources:
        raise ValueError(f"no seed directories found under {root}")
    return tuple(sources)


def build_plan(
    source_root: str | Path,
    *,
    checkpoint_tick: int,
    horizon_ticks: int,
    runtime_root: str | Path,
) -> ReproductionInvestmentPlan:
    if horizon_ticks <= 0:
        raise ValueError("horizon_ticks must be positive")
    return ReproductionInvestmentPlan(
        schema=PLAN_SCHEMA,
        source_root=str(Path(source_root)),
        checkpoint_tick=int(checkpoint_tick),
        horizon_ticks=int(horizon_ticks),
        runtime_root=str(Path(runtime_root)),
        sources=discover_sources(source_root, checkpoint_tick),
    )


def load_plan(path: str | Path) -> ReproductionInvestmentPlan:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if payload.get("schema") != PLAN_SCHEMA:
        raise ValueError(f"unsupported reproduction-investment plan schema: {payload.get('schema')!r}")
    sources = tuple(SourceCheckpoint(**item) for item in payload.get("sources", ()))
    if not sources:
        raise ValueError("reproduction-investment plan contains no source checkpoints")
    plan = ReproductionInvestmentPlan(
        schema=str(payload["schema"]),
        source_root=str(payload["source_root"]),
        checkpoint_tick=int(payload["checkpoint_tick"]),
        horizon_ticks=int(payload["horizon_ticks"]),
        runtime_root=str(payload["runtime_root"]),
        sources=sources,
        branches=tuple(payload.get("branches", BRANCHES)),
        intervention=str(payload.get("intervention", INTERVENTION)),
        paired_randomness=bool(payload.get("paired_randomness", True)),
        genotype_preserved=bool(payload.get("genotype_preserved", True)),
        parent_cost_preserved=bool(payload.get("parent_cost_preserved", True)),
        parent_requirement_preserved=bool(payload.get("parent_requirement_preserved", True)),
        fertility_cost_preserved=bool(payload.get("fertility_cost_preserved", True)),
        resource_fields_preserved_at_intervention=bool(payload.get("resource_fields_preserved_at_intervention", True)),
        residue_inventory_preserved_at_intervention=bool(payload.get("residue_inventory_preserved_at_intervention", True)),
        internal_stores_preserved_at_intervention=bool(payload.get("internal_stores_preserved_at_intervention", True)),
        pass_fail_gate=bool(payload.get("pass_fail_gate", False)),
        ecological_claim_authorized=bool(payload.get("ecological_claim_authorized", False)),
        selection_claim_authorized=bool(payload.get("selection_claim_authorized", False)),
    )
    if plan.branches != BRANCHES or plan.intervention != INTERVENTION:
        raise ValueError("reproduction-investment branch contract does not match runtime")
    if plan.pass_fail_gate or plan.ecological_claim_authorized or plan.selection_claim_authorized:
        raise ValueError("calibration plan cannot authorize a gate or ecological/selection claim")
    return plan


def _close_without_run(simulation: Simulation) -> None:
    simulation.metrics.close()
    simulation.evolution_progress.close()
    simulation.knowledge.close()
    if simulation.subject_structure_diagnostics is not None:
        simulation.subject_structure_diagnostics.close()
    if simulation.environment_atlas_diagnostics is not None:
        simulation.environment_atlas_diagnostics.close()


def _runtime_environment(simulation: Simulation) -> Any:
    return simulation.gpu_runtime.environment if simulation.gpu_runtime is not None else simulation.environment


def _host_array(environment: Any, value: Any) -> np.ndarray:
    if hasattr(environment, "backend"):
        value = environment.backend.to_numpy(value)
    return np.asarray(value).copy()


def _branch_contract(simulation: Simulation) -> dict[str, Any]:
    active = np.flatnonzero(simulation.entities.alive).astype(np.int32)
    genotype = simulation.entities.genotype[active]
    investment = np.asarray(reproduction_investment(genotype, simulation.cfg), dtype=np.float64)
    cost = np.asarray(reproduction_energy_cost(genotype, simulation.cfg), dtype=np.float64)
    requirement = np.asarray(reproduction_energy_requirement(genotype, simulation.cfg), dtype=np.float64)
    return {
        "active_count": int(active.size),
        "investment_mean": float(investment.mean()) if investment.size else 0.0,
        "investment_std": float(investment.std()) if investment.size else 0.0,
        "parent_cost_mean": float(cost.mean()) if cost.size else 0.0,
        "parent_requirement_mean": float(requirement.mean()) if requirement.size else 0.0,
        "fertility_cost": 0.5,
        "offspring_endowment_effective": not simulation.offspring_endowment_ablation_enabled,
    }


def _branch(
    source: SourceCheckpoint,
    output: Path,
    *,
    horizon_ticks: int,
    backend: str,
    neutralize: bool,
) -> dict[str, Any]:
    checkpoint = Path(source.checkpoint_path)
    if _sha256(checkpoint) != source.checkpoint_sha256:
        raise ValueError(f"source checkpoint hash changed: {checkpoint}")
    resolved = Path(source.run_dir) / "resolved_config.json"
    if _config_sha256(resolved) != source.resolved_config_sha256:
        raise ValueError(f"source resolved config changed: {resolved}")
    until_tick = source.checkpoint_tick + int(horizon_ticks)
    simulation = Simulation.from_checkpoint(checkpoint, output, backend=backend, until_tick=until_tick)
    environment = _runtime_environment(simulation)
    genotype_before = simulation.entities.genotype.copy()
    stores_before = simulation.entities.resource_store.copy()
    resources_before = _host_array(environment, environment.resources)
    residue_before = _host_array(environment, environment.resource_residue)
    inherited_contract = _branch_contract(simulation)
    if neutralize:
        simulation.apply_intervention(INTERVENTION)
    effective_contract = _branch_contract(simulation)
    unchanged = {
        "genotype_preserved": np.array_equal(genotype_before, simulation.entities.genotype),
        "internal_stores_preserved_at_intervention": np.array_equal(stores_before, simulation.entities.resource_store),
        "resource_fields_preserved_at_intervention": np.array_equal(resources_before, _host_array(environment, environment.resources)),
        "residue_inventory_preserved_at_intervention": np.array_equal(residue_before, _host_array(environment, environment.resource_residue)),
        "parent_investment_preserved": inherited_contract["investment_mean"] == effective_contract["investment_mean"] and inherited_contract["investment_std"] == effective_contract["investment_std"],
        "parent_cost_preserved": inherited_contract["parent_cost_mean"] == effective_contract["parent_cost_mean"],
        "parent_requirement_preserved": inherited_contract["parent_requirement_mean"] == effective_contract["parent_requirement_mean"],
        "fertility_cost_preserved": inherited_contract["fertility_cost"] == effective_contract["fertility_cost"],
    }
    if not all(unchanged.values()):
        _close_without_run(simulation)
        raise RuntimeError(f"offspring-endowment neutralization violated branch contract: {unchanged}")
    if neutralize and effective_contract["offspring_endowment_effective"]:
        _close_without_run(simulation)
        raise RuntimeError("offspring-endowment neutralization did not disable newborn transfer")
    final = simulation.run(until_tick=until_tick)
    summary = json.loads((output / "summary.json").read_text(encoding="utf-8"))
    replay = json.loads((output / "replay_provenance.json").read_text(encoding="utf-8"))
    merged = {key: final.get(key, summary.get(key)) for key in SCALAR_METRICS}
    merged.update(
        {
            "births_since_checkpoint": int(merged["births_total"]) - int(source.births_total),
            "deaths_since_checkpoint": int(merged["deaths_total"]) - int(source.deaths_total),
            "alive_change_since_checkpoint": int(merged["alive"]) - int(source.alive),
        }
    )
    return {
        "branch": "endowment-neutral" if neutralize else "endowment-active",
        "output": str(output),
        "source_checkpoint_sha256": source.checkpoint_sha256,
        "checkpoint_state_sha256": replay["checkpoint_lineage"][-1]["checkpoint_state_sha256"],
        "interventions": [INTERVENTION] if neutralize else [],
        **unchanged,
        "inherited_contract": inherited_contract,
        "effective_contract": effective_contract,
        "scientific_validity": simulation.scientific_validity(),
        "final": merged,
    }


def execute_plan(plan: ReproductionInvestmentPlan, *, backend: str) -> dict[str, Any]:
    runtime_root = Path(plan.runtime_root)
    for source in plan.sources:
        for name in ("endowment_active", "endowment_neutral"):
            destination = runtime_root / f"seed_{source.seed}" / name
            if destination.exists() and any(destination.iterdir()):
                raise RuntimeError(f"non-empty branch output already exists: {destination}")
    pairs: list[dict[str, Any]] = []
    for source in plan.sources:
        seed_root = runtime_root / f"seed_{source.seed}"
        branches = [
            _branch(source, seed_root / "endowment_active", horizon_ticks=plan.horizon_ticks, backend=backend, neutralize=False),
            _branch(source, seed_root / "endowment_neutral", horizon_ticks=plan.horizon_ticks, backend=backend, neutralize=True),
        ]
        by_name = {branch["branch"]: branch for branch in branches}
        active = by_name["endowment-active"]["final"]
        neutral = by_name["endowment-neutral"]["final"]
        difference = {
            key: float(active[key]) - float(neutral[key])
            for key in (*SCALAR_METRICS, "births_since_checkpoint", "deaths_since_checkpoint", "alive_change_since_checkpoint")
            if isinstance(active.get(key), (int, float)) and isinstance(neutral.get(key), (int, float))
        }
        pairs.append(
            {
                "seed": source.seed,
                "source_turnover": asdict(source),
                "shared_checkpoint_state": branches[0]["checkpoint_state_sha256"] == branches[1]["checkpoint_state_sha256"],
                "branches": branches,
                "paired_difference_endowment_minus_neutral": difference,
            }
        )
    return {
        "schema": RESULT_SCHEMA,
        "plan": asdict(plan),
        "completed_seed_count": len(pairs),
        "pairs": pairs,
        "contract": {
            "all_pairs_share_checkpoint_state": all(pair["shared_checkpoint_state"] for pair in pairs),
            "all_parent_costs_and_state_preserved": all(
                all(
                    branch[key]
                    for key in (
                        "genotype_preserved",
                        "internal_stores_preserved_at_intervention",
                        "resource_fields_preserved_at_intervention",
                        "residue_inventory_preserved_at_intervention",
                        "parent_investment_preserved",
                        "parent_cost_preserved",
                        "parent_requirement_preserved",
                        "fertility_cost_preserved",
                    )
                )
                for pair in pairs
                for branch in pair["branches"]
            ),
        },
        "sample_scope": {
            "three_seed_panel_is_sufficient_for": [
                "runtime and conservation contract calibration",
                "large acute offspring-quality effects",
                "checking whether the source contains measurable descendant turnover",
            ],
            "three_seed_panel_is_not_sufficient_for": [
                "selection",
                "adaptation",
                "stable trait-frequency change",
                "coexistence or niche claims",
            ],
            "evolutionary_followup_requires": (
                "independent seeds with repeated multi-generation replacement; longer nested ticks do not substitute for seed replication"
            ),
        },
        "interpretation_boundary": (
            "This output isolates the offspring return of a costed inherited parental investment. "
            "It has no pass/fail gate and does not authorize evolutionary or ecological claims."
        ),
    }


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def plan_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Plan inherited reproduction-investment calibration")
    parser.add_argument("--source-root", required=True)
    parser.add_argument("--checkpoint-tick", type=int, required=True)
    parser.add_argument("--horizon", type=int, default=240)
    parser.add_argument("--runtime-root", required=True)
    parser.add_argument("--output", required=True)
    return parser


def run_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Execute a locked reproduction-investment calibration plan")
    parser.add_argument("--plan", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--backend", choices=("cpu", "gpu", "auto"), default="auto")
    return parser


def plan_main() -> None:
    args = plan_parser().parse_args()
    _write_json(
        Path(args.output),
        asdict(
            build_plan(
                args.source_root,
                checkpoint_tick=args.checkpoint_tick,
                horizon_ticks=args.horizon,
                runtime_root=args.runtime_root,
            )
        ),
    )


def run_main() -> None:
    args = run_parser().parse_args()
    _write_json(Path(args.output), execute_plan(load_plan(args.plan), backend=args.backend))


if __name__ == "__main__":
    run_main()
