"""Shared-checkpoint calibration for conservative external resource recycling.

D1-K combines the inherited fixed-total storage/conversion substrate with the
existing identity-preserving four-channel residue pool. The paired branch
stops future residue deposition, diffusion, and release without modifying the
checkpoint resource fields, residue inventory, internal stores, genotype, or
physiology costs. This is an ecological substrate calibration, not an
adaptation or selection audit.
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
from se.differentiation.physiology import (
    external_resource_recycling_enabled,
    fixed_budget_resource_conversion_enabled,
    fixed_budget_resource_storage_enabled,
    physiology_genome_energy,
    physiology_phenotype,
)
from se.env.recycling import resource_recycling_diagnostics
from se.policy import ParametricPolicy
from se.runtime.sim import Simulation

PLAN_SCHEMA = "d1-resource-recycling-shared-checkpoint-plan-v1"
RESULT_SCHEMA = "d1-resource-recycling-shared-checkpoint-results-v1"
INTERVENTION = "neutralize-external-resource-recycling"
BRANCHES = ("recycling-active", "recycling-neutral")
SCALAR_METRICS = (
    "tick",
    "alive",
    "births_total",
    "deaths_total",
    "mean_energy",
    "mean_generation",
    "max_generation",
    "founder_alive_count",
    "descendant_alive_count",
    "founder_alive_fraction",
    "descendant_alive_fraction",
    "cumulative_births_per_initial",
    "living_descendants_per_initial",
)
VECTOR_METRICS = (
    "resource_residue_deposited_total",
    "resource_residue_released_total",
    "resource_residue_total",
    "resource_store_decay_total",
    "resource_store_death_loss_total",
    "resource_stored_total",
    "resource_converted_total",
    "resource_body_realized_total",
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


@dataclass(frozen=True)
class ResourceRecyclingPlan:
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
    internal_stores_preserved_at_intervention: bool = True
    resource_fields_preserved_at_intervention: bool = True
    residue_inventory_preserved_at_intervention: bool = True
    storage_and_conversion_allocations_preserved: bool = True
    physiology_costs_preserved: bool = True
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


def _source_summary(path: Path, cfg: Any) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    alive = int(payload.get("alive", 0))
    generation = float(payload.get("mean_generation", 0.0))
    max_generation = int(payload.get("max_generation", 0))
    founder_fraction = float(
        payload.get("founder_alive_fraction", 1.0 if alive else 0.0)
    )
    descendant_fraction = float(
        payload.get("descendant_alive_fraction", 1.0 - founder_fraction if alive else 0.0)
    )
    births = int(payload.get("births_total", 0))
    return {
        "alive": alive,
        "births_total": births,
        "deaths_total": int(payload.get("deaths_total", 0)),
        "mean_generation": generation,
        "max_generation": max_generation,
        "founder_alive_fraction": founder_fraction,
        "descendant_alive_fraction": descendant_fraction,
        "cumulative_births_per_initial": float(
            payload.get(
                "cumulative_births_per_initial",
                births / max(int(cfg.world.initial_entities), 1),
            )
        ),
    }


def discover_sources(
    source_root: str | Path, checkpoint_tick: int
) -> tuple[SourceCheckpoint, ...]:
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
        if not external_resource_recycling_enabled(cfg):
            raise ValueError(f"source run does not enable external recycling: {run_dir}")
        if not (
            fixed_budget_resource_conversion_enabled(cfg)
            and fixed_budget_resource_storage_enabled(cfg)
        ):
            raise ValueError(
                f"source run must retain fixed storage and conversion budgets: {run_dir}"
            )
        metrics = _source_summary(summary, cfg)
        sources.append(
            SourceCheckpoint(
                seed=seed,
                run_dir=str(run_dir),
                checkpoint_path=str(checkpoint),
                checkpoint_sha256=_sha256(checkpoint),
                checkpoint_tick=int(checkpoint_tick),
                resolved_config_sha256=_config_sha256(resolved),
                **metrics,
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
) -> ResourceRecyclingPlan:
    if horizon_ticks <= 0:
        raise ValueError("horizon_ticks must be positive")
    return ResourceRecyclingPlan(
        schema=PLAN_SCHEMA,
        source_root=str(Path(source_root)),
        checkpoint_tick=int(checkpoint_tick),
        horizon_ticks=int(horizon_ticks),
        runtime_root=str(Path(runtime_root)),
        sources=discover_sources(source_root, checkpoint_tick),
    )


def load_plan(path: str | Path) -> ResourceRecyclingPlan:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if payload.get("schema") != PLAN_SCHEMA:
        raise ValueError(
            f"unsupported resource-recycling plan schema: {payload.get('schema')!r}"
        )
    sources = tuple(SourceCheckpoint(**item) for item in payload.get("sources", ()))
    if not sources:
        raise ValueError("resource-recycling plan contains no source checkpoints")
    plan = ResourceRecyclingPlan(
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
        internal_stores_preserved_at_intervention=bool(
            payload.get("internal_stores_preserved_at_intervention", True)
        ),
        resource_fields_preserved_at_intervention=bool(
            payload.get("resource_fields_preserved_at_intervention", True)
        ),
        residue_inventory_preserved_at_intervention=bool(
            payload.get("residue_inventory_preserved_at_intervention", True)
        ),
        storage_and_conversion_allocations_preserved=bool(
            payload.get("storage_and_conversion_allocations_preserved", True)
        ),
        physiology_costs_preserved=bool(payload.get("physiology_costs_preserved", True)),
        pass_fail_gate=bool(payload.get("pass_fail_gate", False)),
        ecological_claim_authorized=bool(payload.get("ecological_claim_authorized", False)),
        selection_claim_authorized=bool(payload.get("selection_claim_authorized", False)),
    )
    if plan.branches != BRANCHES or plan.intervention != INTERVENTION:
        raise ValueError("resource-recycling plan branch contract does not match runtime")
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
    return (
        simulation.gpu_runtime.environment
        if simulation.gpu_runtime is not None
        else simulation.environment
    )


def _host_array(environment: Any, value: Any) -> np.ndarray:
    if hasattr(environment, "backend"):
        value = environment.backend.to_numpy(value)
    return np.asarray(value).copy()


def _branch_contract(simulation: Simulation) -> dict[str, Any]:
    active = np.flatnonzero(simulation.entities.alive).astype(np.int32)
    phenotype = physiology_phenotype(
        simulation.entities.genotype[active],
        simulation.cfg,
        gene_start=ParametricPolicy.physiology_gene_start(simulation.cfg),
    )
    maintenance = physiology_genome_energy(
        simulation.entities.genotype[active],
        simulation.cfg,
        gene_start=ParametricPolicy.physiology_gene_start(simulation.cfg),
    )
    development = physiology_genome_energy(
        simulation.entities.genotype[active],
        simulation.cfg,
        gene_start=ParametricPolicy.physiology_gene_start(simulation.cfg),
        development=True,
    )
    environment = _runtime_environment(simulation)
    recycling = resource_recycling_diagnostics(environment)
    return {
        "active_count": int(active.size),
        "store_capacity_mean": np.asarray(
            phenotype.resource_store_capacity, dtype=np.float64
        ).mean(axis=0).tolist(),
        "conversion_capacity_mean": np.asarray(
            phenotype.resource_conversion_capacity, dtype=np.float64
        ).mean(axis=0).tolist(),
        "maintenance_energy_per_tick_at_branch": float(maintenance.sum()),
        "development_energy_for_active_at_branch": float(development.sum()),
        "resource_residue_total": recycling["resource_residue_total"],
        "resource_recycling_effective_enabled": bool(
            recycling.get("resource_recycling_effective_enabled", True)
        ),
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
    simulation = Simulation.from_checkpoint(
        checkpoint, output, backend=backend, until_tick=until_tick
    )
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
        "genotype_preserved": np.array_equal(
            genotype_before, simulation.entities.genotype
        ),
        "internal_stores_preserved_at_intervention": np.array_equal(
            stores_before, simulation.entities.resource_store
        ),
        "resource_fields_preserved_at_intervention": np.array_equal(
            resources_before, _host_array(environment, environment.resources)
        ),
        "residue_inventory_preserved_at_intervention": np.array_equal(
            residue_before, _host_array(environment, environment.resource_residue)
        ),
        "storage_allocation_preserved": inherited_contract["store_capacity_mean"]
        == effective_contract["store_capacity_mean"],
        "conversion_allocation_preserved": inherited_contract[
            "conversion_capacity_mean"
        ]
        == effective_contract["conversion_capacity_mean"],
        "physiology_costs_preserved": (
            inherited_contract["maintenance_energy_per_tick_at_branch"]
            == effective_contract["maintenance_energy_per_tick_at_branch"]
            and inherited_contract["development_energy_for_active_at_branch"]
            == effective_contract["development_energy_for_active_at_branch"]
        ),
    }
    if not all(unchanged.values()):
        _close_without_run(simulation)
        raise RuntimeError(f"recycling neutralization violated branch contract: {unchanged}")
    if neutralize and effective_contract["resource_recycling_effective_enabled"]:
        _close_without_run(simulation)
        raise RuntimeError("recycling neutralization did not disable future recycling")
    final = simulation.run(until_tick=until_tick)
    summary = json.loads((output / "summary.json").read_text(encoding="utf-8"))
    replay = json.loads((output / "replay_provenance.json").read_text(encoding="utf-8"))
    merged = {
        key: final.get(key, summary.get(key))
        for key in (*SCALAR_METRICS, *VECTOR_METRICS)
    }
    merged.update(
        {
            "births_since_checkpoint": int(merged["births_total"])
            - int(source.births_total),
            "deaths_since_checkpoint": int(merged["deaths_total"])
            - int(source.deaths_total),
            "alive_change_since_checkpoint": int(merged["alive"]) - int(source.alive),
        }
    )
    return {
        "branch": "recycling-neutral" if neutralize else "recycling-active",
        "output": str(output),
        "source_checkpoint_sha256": source.checkpoint_sha256,
        "checkpoint_state_sha256": replay["checkpoint_lineage"][-1][
            "checkpoint_state_sha256"
        ],
        "interventions": [INTERVENTION] if neutralize else [],
        **unchanged,
        "inherited_contract": inherited_contract,
        "effective_contract": effective_contract,
        "scientific_validity": simulation.scientific_validity(),
        "final": merged,
    }


def _vector_difference(left: Any, right: Any) -> list[float] | None:
    if not isinstance(left, list) or not isinstance(right, list) or len(left) != len(right):
        return None
    if not all(isinstance(value, (int, float)) for value in left + right):
        return None
    return [float(a) - float(b) for a, b in zip(left, right, strict=True)]


def execute_plan(plan: ResourceRecyclingPlan, *, backend: str) -> dict[str, Any]:
    runtime_root = Path(plan.runtime_root)
    for source in plan.sources:
        for name in ("recycling_active", "recycling_neutral"):
            destination = runtime_root / f"seed_{source.seed}" / name
            if destination.exists() and any(destination.iterdir()):
                raise RuntimeError(f"non-empty branch output already exists: {destination}")
    pairs: list[dict[str, Any]] = []
    for source in plan.sources:
        seed_root = runtime_root / f"seed_{source.seed}"
        branches = [
            _branch(
                source,
                seed_root / "recycling_active",
                horizon_ticks=plan.horizon_ticks,
                backend=backend,
                neutralize=False,
            ),
            _branch(
                source,
                seed_root / "recycling_neutral",
                horizon_ticks=plan.horizon_ticks,
                backend=backend,
                neutralize=True,
            ),
        ]
        by_name = {branch["branch"]: branch for branch in branches}
        active = by_name["recycling-active"]["final"]
        neutral = by_name["recycling-neutral"]["final"]
        scalar_difference = {
            key: float(active[key]) - float(neutral[key])
            for key in (*SCALAR_METRICS, "births_since_checkpoint", "deaths_since_checkpoint", "alive_change_since_checkpoint")
            if isinstance(active.get(key), (int, float))
            and isinstance(neutral.get(key), (int, float))
        }
        vector_difference = {
            key: value
            for key in VECTOR_METRICS
            if (value := _vector_difference(active.get(key), neutral.get(key)))
            is not None
        }
        pairs.append(
            {
                "seed": source.seed,
                "source_turnover": {
                    "alive": source.alive,
                    "births_total": source.births_total,
                    "deaths_total": source.deaths_total,
                    "mean_generation": source.mean_generation,
                    "max_generation": source.max_generation,
                    "founder_alive_fraction": source.founder_alive_fraction,
                    "descendant_alive_fraction": source.descendant_alive_fraction,
                    "cumulative_births_per_initial": source.cumulative_births_per_initial,
                },
                "shared_checkpoint_state": (
                    branches[0]["checkpoint_state_sha256"]
                    == branches[1]["checkpoint_state_sha256"]
                ),
                "branches": branches,
                "paired_difference_recycling_minus_neutral": {
                    **scalar_difference,
                    **vector_difference,
                },
            }
        )
    return {
        "schema": RESULT_SCHEMA,
        "plan": asdict(plan),
        "completed_seed_count": len(pairs),
        "pairs": pairs,
        "contract": {
            "all_pairs_share_checkpoint_state": all(
                pair["shared_checkpoint_state"] for pair in pairs
            ),
            "all_branch_state_preserved_at_intervention": all(
                all(
                    branch[key]
                    for key in (
                        "genotype_preserved",
                        "internal_stores_preserved_at_intervention",
                        "resource_fields_preserved_at_intervention",
                        "residue_inventory_preserved_at_intervention",
                        "storage_allocation_preserved",
                        "conversion_allocation_preserved",
                        "physiology_costs_preserved",
                    )
                )
                for pair in pairs
                for branch in pair["branches"]
            ),
        },
        "sample_scope": {
            "three_seed_panel_is_sufficient_for": [
                "runtime contract calibration",
                "large acute substrate effects",
                "checking whether generational turnover becomes measurable",
            ],
            "three_seed_panel_is_not_sufficient_for": [
                "selection",
                "adaptation",
                "coexistence",
                "stable niche differentiation",
            ],
            "evolutionary_followup_requires": (
                "multiple generations and founder replacement before expanding to an independent seed panel"
            ),
        },
        "interpretation_boundary": (
            "This output calibrates conservative external recycling and reports source "
            "generational turnover. It has no pass/fail gate and does not authorize "
            "ecological, adaptive, coexistence, or selection claims."
        ),
    }


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def plan_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Plan conservative resource-recycling shared-checkpoint calibration"
    )
    parser.add_argument("--source-root", required=True)
    parser.add_argument("--checkpoint-tick", type=int, required=True)
    parser.add_argument("--horizon", type=int, default=240)
    parser.add_argument("--runtime-root", required=True)
    parser.add_argument("--output", required=True)
    return parser


def run_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Execute a locked resource-recycling calibration plan"
    )
    parser.add_argument("--plan", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--backend", choices=("cpu", "gpu", "auto"), default="auto")
    return parser


def plan_main() -> None:
    args = plan_parser().parse_args()
    plan = build_plan(
        args.source_root,
        checkpoint_tick=args.checkpoint_tick,
        horizon_ticks=args.horizon,
        runtime_root=args.runtime_root,
    )
    _write_json(Path(args.output), asdict(plan))


def run_main() -> None:
    args = run_parser().parse_args()
    result = execute_plan(load_plan(args.plan), backend=args.backend)
    _write_json(Path(args.output), result)


if __name__ == "__main__":
    run_main()
