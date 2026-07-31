"""Shared-checkpoint calibration for inherited resource-sensing scale.

This experiment is intentionally not a candidate audit and has no acceptance
threshold.  It verifies that the new inherited sensing capacity reaches world
interaction, carries its registered costs, and can be neutralized from an exact
shared checkpoint without changing genotype, resource fields, or random keys.
Ecological or selection claims require a later preregistered study.
"""

from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
import hashlib
import json
from pathlib import Path
from typing import Any, Iterable

import numpy as np

from se.cfg import load_config
from se.env.resource_sensing import (
    channel_routed_resource_sensing_enabled,
    resource_sensing_channel_radii,
    resource_sensing_enabled,
    resource_sensing_energy,
    resource_sensing_radius,
)
from se.env.niches import resource_affinity_quantized
from se.runtime.sim import Simulation

PLAN_SCHEMA = "d1-resource-sensing-shared-checkpoint-plan-v1"
RESULT_SCHEMA = "d1-resource-sensing-shared-checkpoint-results-v1"
INTERVENTION = "neutralize-resource-sensing-radius"
BRANCHES = ("inherited-radius", "radius-one-neutral")


@dataclass(frozen=True)
class SourceCheckpoint:
    seed: int
    run_dir: str
    checkpoint_path: str
    checkpoint_sha256: str
    checkpoint_tick: int
    resolved_config_sha256: str


@dataclass(frozen=True)
class ResourceSensingPlan:
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
    structure_use_development_costs_preserved: bool = True
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


def discover_sources(source_root: str | Path, checkpoint_tick: int) -> tuple[SourceCheckpoint, ...]:
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
        if not resource_sensing_enabled(cfg):
            raise ValueError(f"source run does not enable inherited resource sensing: {run_dir}")
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
) -> ResourceSensingPlan:
    if horizon_ticks <= 0:
        raise ValueError("horizon_ticks must be positive")
    return ResourceSensingPlan(
        schema=PLAN_SCHEMA,
        source_root=str(Path(source_root)),
        checkpoint_tick=int(checkpoint_tick),
        horizon_ticks=int(horizon_ticks),
        runtime_root=str(Path(runtime_root)),
        sources=discover_sources(source_root, checkpoint_tick),
    )


def load_plan(path: str | Path) -> ResourceSensingPlan:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if payload.get("schema") != PLAN_SCHEMA:
        raise ValueError(f"unsupported resource-sensing plan schema: {payload.get('schema')!r}")
    sources = tuple(SourceCheckpoint(**item) for item in payload.get("sources", ()))
    if not sources:
        raise ValueError("resource-sensing plan contains no source checkpoints")
    plan = ResourceSensingPlan(
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
        structure_use_development_costs_preserved=bool(
            payload.get("structure_use_development_costs_preserved", True)
        ),
        pass_fail_gate=bool(payload.get("pass_fail_gate", False)),
        ecological_claim_authorized=bool(payload.get("ecological_claim_authorized", False)),
        selection_claim_authorized=bool(payload.get("selection_claim_authorized", False)),
    )
    if plan.branches != BRANCHES or plan.intervention != INTERVENTION:
        raise ValueError("resource-sensing plan branch contract does not match this runtime")
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
    resources_before = np.asarray(simulation.environment.resources).copy()
    alive = simulation.entities.alive.copy()
    inherited_radius = resource_sensing_radius(simulation.entities.genotype, simulation.cfg)
    affinity_before = resource_affinity_quantized(
        simulation.entities.genotype, simulation.cfg
    )
    inherited_channel_radii = resource_sensing_channel_radii(
        simulation.entities.genotype,
        simulation.cfg,
        resource_affinity_q=affinity_before,
    )
    inherited_extra_radius = np.maximum(
        inherited_channel_radii.astype(np.int64) - 1, 0
    ).sum(axis=1)
    expected_extra_radius = (
        inherited_radius.astype(np.int64) - 1
        if channel_routed_resource_sensing_enabled(simulation.cfg)
        else 4 * (inherited_radius.astype(np.int64) - 1)
    )
    allocation_budget_closed = bool(
        np.array_equal(inherited_extra_radius, expected_extra_radius)
    )
    maintenance_before = resource_sensing_energy(
        simulation.entities.genotype[alive], simulation.cfg
    )
    use_before = resource_sensing_energy(
        simulation.entities.genotype[alive], simulation.cfg, use=True
    )
    if neutralize:
        simulation.apply_intervention(INTERVENTION)
    if not np.array_equal(genotype_before, simulation.entities.genotype):
        _close_without_run(simulation)
        raise RuntimeError("resource-sensing neutralization modified genotype")
    if not np.array_equal(resources_before, np.asarray(simulation.environment.resources)):
        _close_without_run(simulation)
        raise RuntimeError("resource-sensing neutralization modified resource fields")
    final = simulation.run(until_tick=until_tick)
    summary = json.loads((output / "summary.json").read_text(encoding="utf-8"))
    replay = json.loads((output / "replay_provenance.json").read_text(encoding="utf-8"))
    return {
        "branch": "radius-one-neutral" if neutralize else "inherited-radius",
        "output": str(output),
        "source_checkpoint_sha256": source.checkpoint_sha256,
        "checkpoint_state_sha256": replay["checkpoint_lineage"][-1]["checkpoint_state_sha256"],
        "interventions": [INTERVENTION] if neutralize else [],
        "genotype_preserved": True,
        "resource_fields_preserved_at_intervention": True,
        "inherited_radius_mean_at_branch": float(inherited_radius[alive].mean()),
        "effective_radius_mean_at_branch": (
            1.0 if neutralize else float(inherited_channel_radii[alive].mean())
        ),
        "effective_channel_radius_means_at_branch": (
            [1.0, 1.0, 1.0, 1.0]
            if neutralize
            else inherited_channel_radii[alive].mean(axis=0).tolist()
        ),
        "inherited_extra_radius_sum_mean_at_branch": float(
            inherited_extra_radius[alive].mean()
        ),
        "inherited_allocation_budget_closed": allocation_budget_closed,
        "maintenance_energy_per_tick_at_branch": float(maintenance_before.sum()),
        "use_energy_per_tick_at_branch": float(use_before.sum()),
        "scientific_validity": simulation.scientific_validity(),
        "final": {
            key: final.get(key, summary.get(key))
            for key in (
                "tick",
                "alive",
                "births_total",
                "deaths_total",
                "mean_energy",
                "resource_sensing_radius_mean",
                "resource_sensing_effective_radius_mean",
                "resource_sensing_channel_0_radius_mean",
                "resource_sensing_channel_1_radius_mean",
                "resource_sensing_channel_2_radius_mean",
                "resource_sensing_channel_3_radius_mean",
                "resource_sensing_channel_0_extended_fraction",
                "resource_sensing_channel_1_extended_fraction",
                "resource_sensing_channel_2_extended_fraction",
                "resource_sensing_channel_3_extended_fraction",
                "resource_sensing_extended_channel_count_mean",
                "resource_sensing_allocated_extra_radius_mean",
                "resource_sensing_maintenance_energy_step",
                "resource_sensing_use_energy_step",
                "resource_sensing_development_energy_step",
            )
        },
    }


def execute_plan(plan: ResourceSensingPlan, *, backend: str) -> dict[str, Any]:
    runtime_root = Path(plan.runtime_root)
    # Validate every source and destination before creating the first branch so
    # a stale later checkpoint or mixed prior output cannot leave a misleading
    # partially executed panel.
    for source in plan.sources:
        checkpoint = Path(source.checkpoint_path)
        resolved = Path(source.run_dir) / "resolved_config.json"
        if _sha256(checkpoint) != source.checkpoint_sha256:
            raise ValueError(f"source checkpoint hash changed: {checkpoint}")
        if _config_sha256(resolved) != source.resolved_config_sha256:
            raise ValueError(f"source resolved config changed: {resolved}")
        for name in ("inherited_radius", "radius_one_neutral"):
            destination = runtime_root / f"seed_{source.seed}" / name
            if destination.exists() and any(destination.iterdir()):
                raise RuntimeError(
                    f"non-empty branch output already exists: {destination}"
                )
    pairs: list[dict[str, Any]] = []
    for source in plan.sources:
        seed_root = runtime_root / f"seed_{source.seed}"
        branches = [
            _branch(
                source,
                seed_root / "inherited_radius",
                horizon_ticks=plan.horizon_ticks,
                backend=backend,
                neutralize=False,
            ),
            _branch(
                source,
                seed_root / "radius_one_neutral",
                horizon_ticks=plan.horizon_ticks,
                backend=backend,
                neutralize=True,
            ),
        ]
        by_name = {row["branch"]: row for row in branches}
        active = by_name["inherited-radius"]["final"]
        neutral = by_name["radius-one-neutral"]["final"]
        numeric_keys = sorted(
            key
            for key in set(active) & set(neutral)
            if isinstance(active[key], (int, float))
            and isinstance(neutral[key], (int, float))
            and active[key] is not None
            and neutral[key] is not None
        )
        pairs.append(
            {
                "seed": source.seed,
                "shared_checkpoint_state": (
                    branches[0]["checkpoint_state_sha256"]
                    == branches[1]["checkpoint_state_sha256"]
                ),
                "branches": branches,
                "paired_difference_inherited_minus_radius_one": {
                    key: float(active[key]) - float(neutral[key])
                    for key in numeric_keys
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
                branch["genotype_preserved"]
                for pair in pairs
                for branch in pair["branches"]
            ),
            "all_resource_fields_preserved_at_intervention": all(
                branch["resource_fields_preserved_at_intervention"]
                for pair in pairs
                for branch in pair["branches"]
            ),
            "all_neutral_branches_effective_radius_one": all(
                branch["effective_radius_mean_at_branch"] == 1.0
                for pair in pairs
                for branch in pair["branches"]
                if branch["branch"] == "radius-one-neutral"
            ),
            "all_branches_retain_positive_registered_cost": all(
                branch["maintenance_energy_per_tick_at_branch"] > 0.0
                and branch["use_energy_per_tick_at_branch"] > 0.0
                for pair in pairs
                for branch in pair["branches"]
            ),
            "all_inherited_allocation_budgets_close": all(
                branch["inherited_allocation_budget_closed"]
                for pair in pairs
                for branch in pair["branches"]
            ),
        },
        "interpretation_boundary": (
            "This output calibrates a costed inherited sensing substrate under exact "
            "shared-checkpoint neutralization. It has no pass/fail gate and does not "
            "authorize ecological, adaptive, coexistence, or selection claims."
        ),
    }


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def plan_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Plan cost-preserving shared-checkpoint resource-sensing calibration"
    )
    parser.add_argument("--source-root", required=True)
    parser.add_argument("--checkpoint-tick", type=int, required=True)
    parser.add_argument("--horizon", type=int, default=120)
    parser.add_argument("--runtime-root", required=True)
    parser.add_argument("--output", required=True)
    return parser


def run_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Execute a locked resource-sensing shared-checkpoint calibration plan"
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
    plan = load_plan(args.plan)
    result = execute_plan(plan, backend=args.backend)
    _write_json(Path(args.output), result)


if __name__ == "__main__":
    run_main()
