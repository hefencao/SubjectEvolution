"""Shared-checkpoint calibration for inherited fixed-budget resource conversion.

The experiment compares the inherited four-channel allocation with a genotype-
neutral channel-base allocation. Both branches preserve the same total
conversion capacity, stores, physiology costs, resource fields, and random keys.
It is a substrate calibration, not an ecological or selection audit.
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
    fixed_budget_resource_conversion_enabled,
    neutral_resource_conversion_capacity,
    physiology_genome_energy,
    physiology_phenotype,
)
from se.policy import ParametricPolicy
from se.runtime.sim import Simulation

PLAN_SCHEMA = "d1-resource-conversion-shared-checkpoint-plan-v1"
RESULT_SCHEMA = "d1-resource-conversion-shared-checkpoint-results-v1"
INTERVENTION = "neutralize-resource-conversion-allocation"
BRANCHES = ("inherited-allocation", "uniform-allocation-neutral")
VECTOR_METRICS = (
    "resource_store_occupancy_mean",
    "resource_conversion_capacity_mean",
    "resource_converted_total",
    "resource_store_decay_total",
    "resource_body_realized_total",
)
SCALAR_METRICS = (
    "tick",
    "alive",
    "births_total",
    "deaths_total",
    "mean_energy",
    "resource_conversion_total_capacity_mean",
    "resource_conversion_allocation_effective_dimensions_mean",
    "resource_conversion_allocation_specialization_mean",
)


@dataclass(frozen=True)
class SourceCheckpoint:
    seed: int
    run_dir: str
    checkpoint_path: str
    checkpoint_sha256: str
    checkpoint_tick: int
    resolved_config_sha256: str


@dataclass(frozen=True)
class ResourceConversionPlan:
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
    resource_fields_preserved_at_intervention: bool = True
    resource_stores_preserved_at_intervention: bool = True
    total_conversion_capacity_preserved: bool = True
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
        if not checkpoint.is_file():
            raise FileNotFoundError(f"missing exact shared checkpoint: {checkpoint}")
        if not resolved.is_file():
            raise FileNotFoundError(f"missing resolved source config: {resolved}")
        cfg = load_config(resolved)
        if int(cfg.run.seed) != seed:
            raise ValueError(
                f"source seed mismatch for {run_dir}: config={cfg.run.seed}, directory={seed}"
            )
        if not fixed_budget_resource_conversion_enabled(cfg):
            raise ValueError(
                f"source run does not enable fixed-budget resource conversion: {run_dir}"
            )
        neutral_base = np.asarray(
            cfg.physiology.resource_conversion_per_tick, dtype=np.float64
        )
        if not np.allclose(neutral_base, neutral_base[0], atol=1.0e-12, rtol=0.0):
            raise ValueError(
                "D1-I uniform neutralization requires equal configured channel bases"
            )
        sources.append(
            SourceCheckpoint(
                seed=seed,
                run_dir=str(run_dir),
                checkpoint_path=str(checkpoint),
                checkpoint_sha256=_sha256(checkpoint),
                checkpoint_tick=int(checkpoint_tick),
                resolved_config_sha256=_config_sha256(resolved),
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
) -> ResourceConversionPlan:
    if horizon_ticks <= 0:
        raise ValueError("horizon_ticks must be positive")
    return ResourceConversionPlan(
        schema=PLAN_SCHEMA,
        source_root=str(Path(source_root)),
        checkpoint_tick=int(checkpoint_tick),
        horizon_ticks=int(horizon_ticks),
        runtime_root=str(Path(runtime_root)),
        sources=discover_sources(source_root, checkpoint_tick),
    )


def load_plan(path: str | Path) -> ResourceConversionPlan:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if payload.get("schema") != PLAN_SCHEMA:
        raise ValueError(
            f"unsupported resource-conversion plan schema: {payload.get('schema')!r}"
        )
    sources = tuple(SourceCheckpoint(**item) for item in payload.get("sources", ()))
    if not sources:
        raise ValueError("resource-conversion plan contains no source checkpoints")
    plan = ResourceConversionPlan(
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
        resource_fields_preserved_at_intervention=bool(
            payload.get("resource_fields_preserved_at_intervention", True)
        ),
        resource_stores_preserved_at_intervention=bool(
            payload.get("resource_stores_preserved_at_intervention", True)
        ),
        total_conversion_capacity_preserved=bool(
            payload.get("total_conversion_capacity_preserved", True)
        ),
        physiology_costs_preserved=bool(payload.get("physiology_costs_preserved", True)),
        pass_fail_gate=bool(payload.get("pass_fail_gate", False)),
        ecological_claim_authorized=bool(payload.get("ecological_claim_authorized", False)),
        selection_claim_authorized=bool(payload.get("selection_claim_authorized", False)),
    )
    if plan.branches != BRANCHES or plan.intervention != INTERVENTION:
        raise ValueError("resource-conversion plan branch contract does not match runtime")
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


def _allocation_metrics(simulation: Simulation) -> dict[str, Any]:
    active = np.flatnonzero(simulation.entities.alive).astype(np.int32)
    phenotype = physiology_phenotype(
        simulation.entities.genotype[active],
        simulation.cfg,
        gene_start=ParametricPolicy.physiology_gene_start(simulation.cfg),
    )
    inherited = np.asarray(phenotype.resource_conversion_capacity, dtype=np.float64)
    effective = (
        neutral_resource_conversion_capacity(active.size, simulation.cfg)
        if simulation.resource_conversion_allocation_ablation_enabled
        else inherited
    )
    totals = effective.sum(axis=1)
    shares = effective / np.maximum(totals[:, None], 1.0e-30)
    expected_total = float(sum(simulation.cfg.physiology.resource_conversion_per_tick))
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
    return {
        "active_count": int(active.size),
        "effective_conversion_capacity_mean": effective.mean(axis=0).tolist(),
        "effective_conversion_total_mean": float(totals.mean()) if active.size else 0.0,
        "effective_conversion_allocation_specialization_mean": (
            float(shares.max(axis=1).mean()) if active.size else 0.0
        ),
        "effective_conversion_allocation_dimensions_mean": (
            float((1.0 / np.maximum((shares * shares).sum(axis=1), 1.0e-30)).mean())
            if active.size
            else 0.0
        ),
        "conversion_total_budget_closed": bool(
            np.allclose(totals, expected_total, atol=1.0e-12, rtol=0.0)
        ),
        "maintenance_energy_per_tick_at_branch": float(maintenance.sum()),
        "development_energy_for_active_at_branch": float(development.sum()),
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
    genotype_before = simulation.entities.genotype.copy()
    stores_before = simulation.entities.resource_store.copy()
    resources_before = np.asarray(simulation.environment.resources).copy()
    inherited_metrics = _allocation_metrics(simulation)
    if neutralize:
        simulation.apply_intervention(INTERVENTION)
    effective_metrics = _allocation_metrics(simulation)
    if not np.array_equal(genotype_before, simulation.entities.genotype):
        _close_without_run(simulation)
        raise RuntimeError("conversion-allocation neutralization modified genotype")
    if not np.array_equal(stores_before, simulation.entities.resource_store):
        _close_without_run(simulation)
        raise RuntimeError("conversion-allocation neutralization modified stores")
    if not np.array_equal(resources_before, np.asarray(simulation.environment.resources)):
        _close_without_run(simulation)
        raise RuntimeError("conversion-allocation neutralization modified resource fields")
    if inherited_metrics["maintenance_energy_per_tick_at_branch"] != effective_metrics[
        "maintenance_energy_per_tick_at_branch"
    ]:
        _close_without_run(simulation)
        raise RuntimeError("conversion neutralization changed physiology maintenance cost")
    if inherited_metrics["development_energy_for_active_at_branch"] != effective_metrics[
        "development_energy_for_active_at_branch"
    ]:
        _close_without_run(simulation)
        raise RuntimeError("conversion neutralization changed physiology development cost")
    final = simulation.run(until_tick=until_tick)
    summary = json.loads((output / "summary.json").read_text(encoding="utf-8"))
    replay = json.loads((output / "replay_provenance.json").read_text(encoding="utf-8"))
    merged = {key: final.get(key, summary.get(key)) for key in (*SCALAR_METRICS, *VECTOR_METRICS)}
    return {
        "branch": "uniform-allocation-neutral" if neutralize else "inherited-allocation",
        "output": str(output),
        "source_checkpoint_sha256": source.checkpoint_sha256,
        "checkpoint_state_sha256": replay["checkpoint_lineage"][-1]["checkpoint_state_sha256"],
        "interventions": [INTERVENTION] if neutralize else [],
        "genotype_preserved": True,
        "resource_fields_preserved_at_intervention": True,
        "resource_stores_preserved_at_intervention": True,
        "inherited_allocation": inherited_metrics,
        "effective_allocation": effective_metrics,
        "scientific_validity": simulation.scientific_validity(),
        "final": merged,
    }


def _vector_difference(left: Any, right: Any) -> list[float] | None:
    if not isinstance(left, list) or not isinstance(right, list) or len(left) != len(right):
        return None
    if not all(isinstance(value, (int, float)) for value in left + right):
        return None
    return [float(a) - float(b) for a, b in zip(left, right, strict=True)]


def execute_plan(plan: ResourceConversionPlan, *, backend: str) -> dict[str, Any]:
    runtime_root = Path(plan.runtime_root)
    for source in plan.sources:
        checkpoint = Path(source.checkpoint_path)
        resolved = Path(source.run_dir) / "resolved_config.json"
        if _sha256(checkpoint) != source.checkpoint_sha256:
            raise ValueError(f"source checkpoint hash changed: {checkpoint}")
        if _config_sha256(resolved) != source.resolved_config_sha256:
            raise ValueError(f"source resolved config changed: {resolved}")
        for name in ("inherited_allocation", "uniform_allocation_neutral"):
            destination = runtime_root / f"seed_{source.seed}" / name
            if destination.exists() and any(destination.iterdir()):
                raise RuntimeError(f"non-empty branch output already exists: {destination}")
    pairs: list[dict[str, Any]] = []
    for source in plan.sources:
        seed_root = runtime_root / f"seed_{source.seed}"
        branches = [
            _branch(
                source,
                seed_root / "inherited_allocation",
                horizon_ticks=plan.horizon_ticks,
                backend=backend,
                neutralize=False,
            ),
            _branch(
                source,
                seed_root / "uniform_allocation_neutral",
                horizon_ticks=plan.horizon_ticks,
                backend=backend,
                neutralize=True,
            ),
        ]
        by_name = {branch["branch"]: branch for branch in branches}
        inherited = by_name["inherited-allocation"]["final"]
        neutral = by_name["uniform-allocation-neutral"]["final"]
        scalar_difference = {
            key: float(inherited[key]) - float(neutral[key])
            for key in SCALAR_METRICS
            if isinstance(inherited.get(key), (int, float))
            and isinstance(neutral.get(key), (int, float))
        }
        vector_difference = {
            key: value
            for key in VECTOR_METRICS
            if (value := _vector_difference(inherited.get(key), neutral.get(key))) is not None
        }
        pairs.append(
            {
                "seed": source.seed,
                "shared_checkpoint_state": (
                    branches[0]["checkpoint_state_sha256"]
                    == branches[1]["checkpoint_state_sha256"]
                ),
                "branches": branches,
                "paired_difference_inherited_minus_uniform": {
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
            "all_genotypes_preserved": all(
                branch["genotype_preserved"] for pair in pairs for branch in pair["branches"]
            ),
            "all_resource_fields_preserved_at_intervention": all(
                branch["resource_fields_preserved_at_intervention"]
                for pair in pairs
                for branch in pair["branches"]
            ),
            "all_resource_stores_preserved_at_intervention": all(
                branch["resource_stores_preserved_at_intervention"]
                for pair in pairs
                for branch in pair["branches"]
            ),
            "all_total_conversion_budgets_close": all(
                branch["effective_allocation"]["conversion_total_budget_closed"]
                for pair in pairs
                for branch in pair["branches"]
            ),
            "all_physiology_costs_preserved": all(
                branch["inherited_allocation"]["maintenance_energy_per_tick_at_branch"]
                == branch["effective_allocation"]["maintenance_energy_per_tick_at_branch"]
                and branch["inherited_allocation"]["development_energy_for_active_at_branch"]
                == branch["effective_allocation"]["development_energy_for_active_at_branch"]
                for pair in pairs
                for branch in pair["branches"]
            ),
        },
        "interpretation_boundary": (
            "This output calibrates an inherited fixed-total conversion allocation under "
            "exact shared-checkpoint neutralization. It has no pass/fail gate and does "
            "not authorize ecological, adaptive, coexistence, or selection claims."
        ),
    }


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def plan_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Plan fixed-budget resource-conversion shared-checkpoint calibration"
    )
    parser.add_argument("--source-root", required=True)
    parser.add_argument("--checkpoint-tick", type=int, required=True)
    parser.add_argument("--horizon", type=int, default=120)
    parser.add_argument("--runtime-root", required=True)
    parser.add_argument("--output", required=True)
    return parser


def run_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Execute a locked resource-conversion calibration plan"
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
