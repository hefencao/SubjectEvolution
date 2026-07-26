"""Paired affinity × capacity checkpoint interventions for D1 validation.

The four branches estimate local expression effects from one trusted world state:

- baseline: inherited affinity and elastic capacities expressed;
- affinity-neutral: only resource-affinity expression is neutralized;
- capacity-neutral: only elastic-capacity expression is neutralized;
- combined-neutral: both expressions are neutralized.

All branches retain genotype, stable IDs, checkpoint state, and keyed randomness.
The resulting factorial contrast is local to the selected checkpoint phase and
post-intervention horizon; it is not a population-wide necessity claim.
"""

from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
import json
import math
from pathlib import Path
from typing import Any, Iterable, Sequence

import numpy as np

from se.experiments.phase_counterfactual import PHASES, build_phase_plan
from se.runtime.sim import Simulation


PLAN_SCHEMA = "d1-affinity-capacity-factorial-plan-v1"
RESULT_SCHEMA = "d1-affinity-capacity-factorial-results-v1"

BRANCH_INTERVENTIONS: dict[str, tuple[str, ...]] = {
    "baseline": (),
    "affinity-neutral": ("neutralize-resource-affinity",),
    "capacity-neutral": ("neutralize-elastic-capacities",),
    "combined-neutral": (
        "neutralize-resource-affinity",
        "neutralize-elastic-capacities",
    ),
}

DEFAULT_OUTCOMES = (
    "world.alive",
    "world.mean_energy",
    "world.total_births",
    "world.total_deaths",
    "evolution.effective_lineages",
    "evolution.strategy_effective_dimensions",
    "evolution.resource_affinity_effective_dimensions",
    "evolution.environment_resource_effective_dimensions",
    "evolution.capacity_effective_dimensions",
    "evolution.benefit_boundary_cohesion",
    "evolution.knowledge_effective_transferred_roots",
    "derived.harvest_extraction_efficiency_window",
)


@dataclass(frozen=True)
class FactorialCheckpoint:
    run_name: str
    run_dir: str
    phase: str
    target_tick: int
    checkpoint_tick: int
    checkpoint_path: str
    until_tick: int


@dataclass(frozen=True)
class FactorialPlan:
    schema: str
    horizon_ticks: int
    phases: tuple[str, ...]
    checkpoints: tuple[FactorialCheckpoint, ...]
    branches: dict[str, tuple[str, ...]]
    paired_randomness: bool = True
    genotype_preserved: bool = True
    observational_phase_selection: bool = True


def _normalize_phases(phases: Iterable[str]) -> tuple[str, ...]:
    normalized: list[str] = []
    for value in phases:
        phase = str(value).strip().lower()
        if phase not in PHASES:
            raise ValueError(f"unknown phase {value!r}; expected one of {PHASES}")
        if phase not in normalized:
            normalized.append(phase)
    if not normalized:
        raise ValueError("at least one phase is required")
    return tuple(normalized)


def build_factorial_plan(
    run_dirs: Sequence[str | Path],
    *,
    horizon_ticks: int,
    phases: Iterable[str] = PHASES,
    min_phase_tick: int | None = None,
    allow_incomplete_cycle: bool = False,
) -> FactorialPlan:
    if horizon_ticks <= 0:
        raise ValueError("horizon_ticks must be positive")
    selected_phases = _normalize_phases(phases)
    checkpoints: list[FactorialCheckpoint] = []
    for run_dir in run_dirs:
        root = Path(run_dir)
        phase_plan = build_phase_plan(
            root,
            horizon_ticks=horizon_ticks,
            interventions=(
                "neutralize-resource-affinity",
                "neutralize-elastic-capacities",
            ),
            min_phase_tick=min_phase_tick,
            allow_incomplete_cycle=allow_incomplete_cycle,
        )
        by_phase = {item.phase: item for item in phase_plan.phases}
        for phase in selected_phases:
            item = by_phase[phase]
            checkpoints.append(
                FactorialCheckpoint(
                    run_name=root.name,
                    run_dir=str(root),
                    phase=phase,
                    target_tick=item.target_tick,
                    checkpoint_tick=item.checkpoint_tick,
                    checkpoint_path=item.checkpoint_path,
                    until_tick=item.checkpoint_tick + horizon_ticks,
                )
            )
    if not checkpoints:
        raise ValueError("no run directories were supplied")
    return FactorialPlan(
        schema=PLAN_SCHEMA,
        horizon_ticks=int(horizon_ticks),
        phases=selected_phases,
        checkpoints=tuple(checkpoints),
        branches=dict(BRANCH_INTERVENTIONS),
    )


def _flatten_numeric(prefix: str, value: Any) -> dict[str, float]:
    result: dict[str, float] = {}
    if isinstance(value, dict):
        for key, nested in value.items():
            child = f"{prefix}.{key}" if prefix else str(key)
            result.update(_flatten_numeric(child, nested))
    elif isinstance(value, (int, float)) and not isinstance(value, bool):
        number = float(value)
        if math.isfinite(number):
            result[prefix] = number
    return result


def _derived_endpoint(evolution: dict[str, Any]) -> dict[str, float | None]:
    requested = np.asarray(
        evolution.get("requested_harvest_resources_window", ()), dtype=np.float64
    )
    realized = np.asarray(
        evolution.get("harvested_resources_window", ()), dtype=np.float64
    )
    if requested.shape == (4,) and realized.shape == (4,):
        requested_total = float(requested.sum())
        efficiency = (
            float(realized.sum()) / requested_total if requested_total > 0.0 else None
        )
    else:
        efficiency = None
    return {"harvest_extraction_efficiency_window": efficiency}


def _run_branch(
    checkpoint: FactorialCheckpoint,
    output_dir: Path,
    *,
    interventions: Sequence[str],
    backend: str,
    gpu_semantics_mode: str | None,
) -> dict[str, Any]:
    simulation = Simulation.from_checkpoint(
        checkpoint.checkpoint_path,
        output_dir,
        backend=backend,
        until_tick=checkpoint.until_tick,
        gpu_semantics_mode=gpu_semantics_mode,
    )
    genotype_before = simulation.entities.genotype.copy()
    for intervention in interventions:
        simulation.apply_intervention(intervention)
    if not np.array_equal(simulation.entities.genotype, genotype_before):
        raise RuntimeError("D1 expression neutralization modified genotype")
    world = simulation.run(until_tick=checkpoint.until_tick)
    evolution = (
        simulation.evolution_progress.records[-1]
        if simulation.evolution_progress.records
        else {}
    )
    return {
        "world": world,
        "evolution": evolution,
        "derived": _derived_endpoint(evolution),
        "scientific_validity": simulation.scientific_validity(),
        "intervention_history": simulation.intervention_history,
    }


def factorial_effects(
    branch_numeric: dict[str, dict[str, float]],
) -> dict[str, dict[str, float]]:
    required = set(BRANCH_INTERVENTIONS)
    if set(branch_numeric) != required:
        missing = sorted(required - set(branch_numeric))
        extra = sorted(set(branch_numeric) - required)
        raise ValueError(f"factorial branches mismatch; missing={missing}, extra={extra}")
    common = set.intersection(*(set(values) for values in branch_numeric.values()))
    baseline = branch_numeric["baseline"]
    affinity = branch_numeric["affinity-neutral"]
    capacity = branch_numeric["capacity-neutral"]
    combined = branch_numeric["combined-neutral"]
    return {
        "affinity_expression_effect": {
            key: baseline[key] - affinity[key] for key in sorted(common)
        },
        "capacity_expression_effect": {
            key: baseline[key] - capacity[key] for key in sorted(common)
        },
        "interaction_effect": {
            key: baseline[key] - affinity[key] - capacity[key] + combined[key]
            for key in sorted(common)
        },
    }


def _aggregate_effects(checkpoints: list[dict[str, Any]]) -> dict[str, Any]:
    buckets: dict[tuple[str, str], list[float]] = {}
    for checkpoint in checkpoints:
        for effect_name, values in checkpoint["effects"].items():
            for outcome, value in values.items():
                buckets.setdefault((effect_name, outcome), []).append(float(value))
    aggregate: dict[str, dict[str, Any]] = {}
    for (effect_name, outcome), values in sorted(buckets.items()):
        array = np.asarray(values, dtype=np.float64)
        nonzero = array[np.abs(array) > 1e-12]
        same_sign = bool(
            nonzero.size > 0
            and (np.all(nonzero > 0.0) or np.all(nonzero < 0.0))
        )
        aggregate.setdefault(effect_name, {})[outcome] = {
            "count": int(array.size),
            "mean": float(array.mean()),
            "min": float(array.min()),
            "max": float(array.max()),
            "std": float(array.std()),
            "same_nonzero_sign": same_sign,
        }
    return aggregate


def execute_factorial_plan(
    plan: FactorialPlan,
    output_dir: str | Path,
    *,
    backend: str = "cpu",
    gpu_semantics_mode: str | None = None,
) -> dict[str, Any]:
    root = Path(output_dir)
    root.mkdir(parents=True, exist_ok=True)
    checkpoint_results: list[dict[str, Any]] = []
    for item in plan.checkpoints:
        checkpoint_dir = root / item.run_name / item.phase
        branches: dict[str, Any] = {}
        branch_numeric: dict[str, dict[str, float]] = {}
        for branch_name, interventions in BRANCH_INTERVENTIONS.items():
            result = _run_branch(
                item,
                checkpoint_dir / branch_name,
                interventions=interventions,
                backend=backend,
                gpu_semantics_mode=gpu_semantics_mode,
            )
            branches[branch_name] = result
            branch_numeric[branch_name] = {
                **_flatten_numeric("world", result["world"]),
                **_flatten_numeric("evolution", result["evolution"]),
                **_flatten_numeric("derived", result["derived"]),
            }
        checkpoint_results.append(
            {
                "checkpoint": asdict(item),
                "branches": branches,
                "effects": factorial_effects(branch_numeric),
            }
        )
    report = {
        "schema": RESULT_SCHEMA,
        "plan": asdict(plan),
        "backend": backend,
        "gpu_semantics_mode": gpu_semantics_mode,
        "checkpoints": checkpoint_results,
        "aggregate_effects": _aggregate_effects(checkpoint_results),
        "interpretation_boundary": (
            "Effects are paired local contrasts over the selected checkpoint phase and "
            "horizon. Positive expression effects mean the inherited expressed phenotype "
            "exceeded its neutralized branch. The interaction is baseline - affinity-"
            "neutral - capacity-neutral + combined-neutral. Observational phase selection "
            "and three seeds do not establish universal necessity."
        ),
    }
    (root / "d1_factorial_results.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (root / "d1_factorial_results.md").write_text(
        render_results_markdown(report), encoding="utf-8"
    )
    return report


def render_plan_markdown(plan: FactorialPlan) -> str:
    lines = [
        "# D1 affinity × capacity factorial plan",
        "",
        f"Schema: `{plan.schema}`",
        f"Post-intervention horizon: **{plan.horizon_ticks} ticks**",
        "",
        "| Run | Phase | Target tick | Checkpoint | Until tick |",
        "|---|---|---:|---:|---:|",
    ]
    for item in plan.checkpoints:
        lines.append(
            f"| {item.run_name} | {item.phase} | {item.target_tick} | "
            f"{item.checkpoint_tick} | {item.until_tick} |"
        )
    lines.extend(
        [
            "",
            "## Branches",
            "",
            "- `baseline`: inherited affinity and capacities expressed",
            "- `affinity-neutral`: neutralize resource-affinity expression",
            "- `capacity-neutral`: neutralize elastic-capacity expression",
            "- `combined-neutral`: neutralize both expressions",
            "",
            "> All branches start from the same trusted checkpoint and preserve genotype and keyed randomness.",
            "",
        ]
    )
    return "\n".join(lines)


def render_results_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# D1 affinity × capacity factorial results",
        "",
        "> Positive effects mean the expressed inherited phenotype exceeded its neutralized paired branch.",
        "",
        "| Run | Phase | Effect | Outcome | Value |",
        "|---|---|---|---|---:|",
    ]
    outcomes = set(DEFAULT_OUTCOMES)
    for checkpoint in report["checkpoints"]:
        item = checkpoint["checkpoint"]
        for effect_name, values in checkpoint["effects"].items():
            for outcome in DEFAULT_OUTCOMES:
                if outcome not in values:
                    continue
                lines.append(
                    f"| {item['run_name']} | {item['phase']} | {effect_name} | "
                    f"`{outcome}` | {values[outcome]:+.6f} |"
                )
            outcomes.update(values)
    lines.extend(
        [
            "",
            "## Interpretation boundary",
            "",
            report["interpretation_boundary"],
            "",
        ]
    )
    return "\n".join(lines)


def _parse_csv(value: str) -> tuple[str, ...]:
    values = tuple(item.strip() for item in value.split(",") if item.strip())
    if not values:
        raise ValueError("value must contain at least one item")
    return values


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Plan or execute paired D1 affinity × capacity factorial branches"
    )
    parser.add_argument("--run-dir", action="append", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--horizon", type=int, default=120)
    parser.add_argument("--phases", default=",".join(PHASES))
    parser.add_argument("--min-phase-tick", type=int)
    parser.add_argument("--allow-incomplete-cycle", action="store_true")
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--backend", choices=("cpu", "gpu", "auto"), default="cpu")
    parser.add_argument(
        "--gpu-semantics-mode",
        choices=("strict-reference", "hybrid-accelerated"),
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=True)
    plan = build_factorial_plan(
        args.run_dir,
        horizon_ticks=args.horizon,
        phases=_parse_csv(args.phases),
        min_phase_tick=args.min_phase_tick,
        allow_incomplete_cycle=args.allow_incomplete_cycle,
    )
    (output / "d1_factorial_plan.json").write_text(
        json.dumps(asdict(plan), ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (output / "d1_factorial_plan.md").write_text(
        render_plan_markdown(plan), encoding="utf-8"
    )
    if args.execute:
        execute_factorial_plan(
            plan,
            output,
            backend=args.backend,
            gpu_semantics_mode=args.gpu_semantics_mode,
        )


if __name__ == "__main__":
    main()
