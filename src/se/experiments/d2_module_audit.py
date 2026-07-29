"""Paired leave-one-module checkpoint audit for D2 contextual modules.

The audit does not alter genotype or module structure. Each branch starts from
the same trusted checkpoint and neutralizes either all module expression or one
fixed module index. The resulting contrasts identify local causal contribution,
redundancy, and non-additivity before module duplication is considered.
"""

from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
import json
import math
from pathlib import Path
import tempfile
from typing import Any, Iterable, Sequence

import numpy as np

from se.differentiation.functional import evaluate_contextual_harvest_modules_q
from se.env.niches import (
    AFFINITY_SCALE,
    RESOURCE_CHANNELS,
    harvest_request_rates,
    resource_affinity_quantized,
)
from se.experiments.phase_counterfactual import PHASES, build_phase_plan
from se.policy import ParametricPolicy
from se.random_api import RandomContext, Stream, uniform01
from se.runtime.sim import Simulation

PLAN_SCHEMA = "d2-module-leave-one-out-plan-v1"
RESULT_SCHEMA = "d2-module-leave-one-out-results-v2"
RESULT_SCHEMAS = {"d2-module-leave-one-out-results-v1", RESULT_SCHEMA}
FOOTPRINT_SCHEMA = "d2-module-immediate-footprint-v1"
MAX_FOOTPRINT_LINEAGES = 8
MODULE_COUNT = 4

BRANCH_INTERVENTIONS: dict[str, tuple[str, ...]] = {
    "baseline": (),
    "all-modules-neutral": ("neutralize-functional-modules",),
    **{
        f"module-{index}-neutral": (f"neutralize-functional-module-{index}",)
        for index in range(MODULE_COUNT)
    },
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
    "evolution.functional_harvest_preference_effective_dimensions",
    "evolution.functional_module_residual_abs_mean",
    "evolution.functional_module_contribution_effective_count",
    "evolution.functional_module_cancellation_fraction",
    "evolution.knowledge_effective_transferred_roots",
    "derived.harvest_extraction_efficiency_window",
)


@dataclass(frozen=True)
class ModuleAuditCheckpoint:
    run_name: str
    run_dir: str
    phase: str
    target_tick: int
    checkpoint_tick: int
    checkpoint_path: str
    until_tick: int


@dataclass(frozen=True)
class ModuleAuditPlan:
    schema: str
    horizon_ticks: int
    phases: tuple[str, ...]
    checkpoints: tuple[ModuleAuditCheckpoint, ...]
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


def load_module_audit_plan(path: str | Path) -> ModuleAuditPlan:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if payload.get("schema") != PLAN_SCHEMA:
        raise ValueError(f"unsupported D2 module audit plan: {payload.get('schema')!r}")
    checkpoints = tuple(
        ModuleAuditCheckpoint(**item) for item in payload.get("checkpoints", ())
    )
    if not checkpoints:
        raise ValueError("D2 module audit plan contains no checkpoints")
    branches = {
        str(name): tuple(values)
        for name, values in dict(payload.get("branches", {})).items()
    }
    if branches != BRANCH_INTERVENTIONS:
        raise ValueError("D2 module audit branch definitions do not match this runtime")
    return ModuleAuditPlan(
        schema=payload["schema"],
        horizon_ticks=int(payload["horizon_ticks"]),
        phases=tuple(payload["phases"]),
        checkpoints=checkpoints,
        branches=branches,
        paired_randomness=bool(payload.get("paired_randomness", True)),
        genotype_preserved=bool(payload.get("genotype_preserved", True)),
        observational_phase_selection=bool(
            payload.get("observational_phase_selection", True)
        ),
    )


def build_module_audit_plan(
    run_dirs: Sequence[str | Path],
    *,
    horizon_ticks: int,
    phases: Iterable[str] = PHASES,
    min_phase_tick: int | None = None,
    allow_incomplete_cycle: bool = False,
) -> ModuleAuditPlan:
    if horizon_ticks <= 0:
        raise ValueError("horizon_ticks must be positive")
    selected_phases = _normalize_phases(phases)
    checkpoints: list[ModuleAuditCheckpoint] = []
    for run_dir in run_dirs:
        root = Path(run_dir)
        phase_plan = build_phase_plan(
            root,
            horizon_ticks=horizon_ticks,
            interventions=tuple(
                intervention
                for values in BRANCH_INTERVENTIONS.values()
                for intervention in values
            ),
            min_phase_tick=min_phase_tick,
            allow_incomplete_cycle=allow_incomplete_cycle,
        )
        by_phase = {item.phase: item for item in phase_plan.phases}
        for phase in selected_phases:
            item = by_phase[phase]
            checkpoints.append(
                ModuleAuditCheckpoint(
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
    return ModuleAuditPlan(
        schema=PLAN_SCHEMA,
        horizon_ticks=int(horizon_ticks),
        phases=selected_phases,
        checkpoints=tuple(checkpoints),
        branches=dict(BRANCH_INTERVENTIONS),
    )



def _preference_footprint(
    baseline_preference_q: np.ndarray,
    neutral_preference_q: np.ndarray,
    baseline_rates: np.ndarray,
    neutral_rates: np.ndarray,
    rows: np.ndarray | None = None,
) -> dict[str, float | int]:
    selected = (
        np.arange(baseline_preference_q.shape[0], dtype=np.int32)
        if rows is None
        else np.asarray(rows, dtype=np.int32)
    )
    if selected.size == 0:
        return {
            "members": 0,
            "preference_changed_fraction": 0.0,
            "preference_total_variation_mean": 0.0,
            "conditional_harvest_channel_changed_fraction": 0.0,
        }
    baseline = np.asarray(baseline_preference_q[selected], dtype=np.float64)
    neutral = np.asarray(neutral_preference_q[selected], dtype=np.float64)
    baseline_share = baseline / baseline.sum(axis=1, keepdims=True)
    neutral_share = neutral / neutral.sum(axis=1, keepdims=True)
    baseline_channel = np.argmax(baseline_rates[selected], axis=1)
    neutral_channel = np.argmax(neutral_rates[selected], axis=1)
    return {
        "members": int(selected.size),
        "preference_changed_fraction": float(
            np.any(baseline_preference_q[selected] != neutral_preference_q[selected], axis=1).mean()
        ),
        "preference_total_variation_mean": float(
            (0.5 * np.abs(baseline_share - neutral_share).sum(axis=1)).mean()
        ),
        "conditional_harvest_channel_changed_fraction": float(
            (baseline_channel != neutral_channel).mean()
        ),
    }


def checkpoint_functional_footprint(
    checkpoint_path: str | Path,
    *,
    max_lineages: int = MAX_FOOTPRINT_LINEAGES,
) -> dict[str, Any]:
    """Measure immediate module effects at a shared checkpoint without stepping.

    Every living entity is evaluated under the same keyed harvest-channel draw
    conditional on choosing HARVEST.  This isolates the direct interface
    footprint from later trajectory amplification.
    """

    with tempfile.TemporaryDirectory(prefix="se-d2-footprint-") as temporary:
        simulation = Simulation.from_checkpoint(
            checkpoint_path,
            Path(temporary) / "load",
            backend="cpu",
        )
        cfg = simulation.cfg
        ent = simulation.entities
        active = simulation.spatial.build(ent.x, ent.y, ent.alive)
        if active.size == 0 or not cfg.functional_modules.enabled:
            return {
                "schema": FOOTPRINT_SCHEMA,
                "checkpoint_tick": int(simulation.tick),
                "active_entities": int(active.size),
                "effects": {},
                "lineage_scope": [],
            }
        cells = simulation.spatial.entity_cells[active]
        local_resources = simulation.environment.cell_values(cells)
        affinity_all = (
            np.full(
                (ent.alive.size, RESOURCE_CHANNELS),
                AFFINITY_SCALE,
                dtype=np.int32,
            )
            if simulation.resource_affinity_ablation_enabled
            else resource_affinity_quantized(ent.genotype, cfg)
        )
        affinity = affinity_all[active]
        current_mask = np.asarray(
            simulation.functional_module_ablation_mask, dtype=bool
        ).copy()

        def preference(mask: np.ndarray) -> np.ndarray:
            return evaluate_contextual_harvest_modules_q(
                ent.genotype[active],
                affinity,
                energy=ent.energy[active],
                integrity=ent.integrity[active],
                material=ent.material[active],
                information_store=ent.information_store[active],
                fertility=ent.fertility[active],
                local_resources=local_resources,
                cfg=cfg,
                gene_start=ParametricPolicy.functional_module_gene_start(cfg),
                ablated_modules=mask,
            ).preference_q

        baseline_preference = preference(current_mask)
        draws = uniform01(
            RandomContext(
                cfg.run.seed,
                int(simulation.tick),
                phase=42,
                stream=Stream.HARVEST_CHANNEL,
            ),
            ent.entity_id[active],
            draw_index=0,
        )
        baseline_rates = harvest_request_rates(
            baseline_preference,
            cfg,
            rows=int(active.size),
            channel_draws=draws,
        )

        lineage_ids = ent.lineage_id[active].astype(np.uint64, copy=False)
        unique, counts = np.unique(lineage_ids, return_counts=True)
        order = np.lexsort((unique, -counts))[: max(int(max_lineages), 0)]
        lineage_scope = [
            {"lineage_id": int(unique[index]), "members": int(counts[index])}
            for index in order
        ]

        masks: dict[str, np.ndarray] = {
            "all_module_expression_effect": np.ones_like(current_mask, dtype=bool),
        }
        for module_index in range(MODULE_COUNT):
            mask = current_mask.copy()
            mask[module_index] = True
            masks[f"module_{module_index}_expression_effect"] = mask

        effects: dict[str, Any] = {}
        for effect_name, mask in masks.items():
            neutral_preference = preference(mask)
            neutral_rates = harvest_request_rates(
                neutral_preference,
                cfg,
                rows=int(active.size),
                channel_draws=draws,
            )
            summary = _preference_footprint(
                baseline_preference,
                neutral_preference,
                baseline_rates,
                neutral_rates,
            )
            lineages: list[dict[str, Any]] = []
            for lineage in lineage_scope:
                rows = np.flatnonzero(lineage_ids == np.uint64(lineage["lineage_id"]))
                lineages.append(
                    {
                        "lineage_id": lineage["lineage_id"],
                        **_preference_footprint(
                            baseline_preference,
                            neutral_preference,
                            baseline_rates,
                            neutral_rates,
                            rows,
                        ),
                    }
                )
            effects[effect_name] = {**summary, "lineages": lineages}

        return {
            "schema": FOOTPRINT_SCHEMA,
            "checkpoint_tick": int(simulation.tick),
            "run_seed": int(cfg.run.seed),
            "active_entities": int(active.size),
            "reference_backend": "cpu",
            "conditional_action": "HARVEST",
            "lineage_scope": lineage_scope,
            "effects": effects,
            "interpretation_boundary": (
                "Immediate footprints evaluate the fixed harvest interface before "
                "branch stepping. They establish direct causal reach, not fitness or "
                "long-horizon ecological benefit."
            ),
        }

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
    efficiency = None
    if requested.shape == (4,) and realized.shape == (4,):
        total = float(requested.sum())
        if total > 0.0:
            efficiency = float(realized.sum()) / total
    return {"harvest_extraction_efficiency_window": efficiency}


def _run_branch(
    checkpoint: ModuleAuditCheckpoint,
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
        raise RuntimeError("D2 module expression neutralization modified genotype")
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


def module_audit_effects(
    branch_numeric: dict[str, dict[str, float]],
) -> dict[str, dict[str, float]]:
    required = set(BRANCH_INTERVENTIONS)
    if set(branch_numeric) != required:
        missing = sorted(required - set(branch_numeric))
        extra = sorted(set(branch_numeric) - required)
        raise ValueError(f"D2 module audit branches mismatch; missing={missing}, extra={extra}")
    common = set.intersection(*(set(values) for values in branch_numeric.values()))
    baseline = branch_numeric["baseline"]
    all_neutral = branch_numeric["all-modules-neutral"]
    effects: dict[str, dict[str, float]] = {
        "all_module_expression_effect": {
            key: baseline[key] - all_neutral[key] for key in sorted(common)
        }
    }
    for index in range(MODULE_COUNT):
        neutral = branch_numeric[f"module-{index}-neutral"]
        effects[f"module_{index}_expression_effect"] = {
            key: baseline[key] - neutral[key] for key in sorted(common)
        }
    effects["module_nonadditivity"] = {
        key: effects["all_module_expression_effect"][key]
        - sum(effects[f"module_{index}_expression_effect"][key] for index in range(MODULE_COUNT))
        for key in sorted(common)
    }
    return effects


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


def execute_module_audit_plan(
    plan: ModuleAuditPlan,
    output_dir: str | Path,
    *,
    backend: str = "auto",
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
            flattened = {
                **_flatten_numeric("world", result["world"]),
                **_flatten_numeric("evolution", result["evolution"]),
                **_flatten_numeric("derived", result["derived"]),
            }
            selected = {
                outcome: flattened[outcome]
                for outcome in DEFAULT_OUTCOMES
                if outcome in flattened
            }
            branches[branch_name] = {
                "output_dir": str(checkpoint_dir / branch_name),
                "outcomes": selected,
                "scientific_validity": result["scientific_validity"],
                "intervention_history": result["intervention_history"],
            }
            branch_numeric[branch_name] = selected
        checkpoint_results.append(
            {
                "checkpoint": asdict(item),
                "checkpoint_footprint": checkpoint_functional_footprint(
                    item.checkpoint_path
                ),
                "branches": branches,
                "effects": module_audit_effects(branch_numeric),
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
            "Leave-one-module effects are paired local contrasts from observationally "
            "selected checkpoints. Immediate checkpoint footprints separate direct "
            "harvest-interface reach from later trajectory amplification. Individual "
            "effects and non-additivity identify local redundancy or interaction. They "
            "do not justify duplication, universal necessity, or a new organ claim."
        ),
    }
    (root / "d2_module_audit_results.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (root / "d2_module_audit_results.md").write_text(
        render_results_markdown(report), encoding="utf-8"
    )
    return report


def render_plan_markdown(plan: ModuleAuditPlan) -> str:
    lines = [
        "# D2 module leave-one-out audit plan",
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
            "- `baseline`: all inherited module expression retained",
            "- `all-modules-neutral`: all module output and expression cost neutralized",
            *[
                f"- `module-{index}-neutral`: only module {index} expression neutralized"
                for index in range(MODULE_COUNT)
            ],
            "",
            "> Genotype, stable IDs, checkpoint state, and keyed randomness are preserved.",
            "",
        ]
    )
    return "\n".join(lines)


def render_results_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# D2 module leave-one-out audit results",
        "",
        "> Positive expression effects mean the baseline exceeded the paired neutralized branch.",
        "",
        "| Run | Phase | Effect | Outcome | Value |",
        "|---|---|---|---|---:|",
    ]
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
    lines.extend(
        [
            "",
            "## Immediate checkpoint footprint",
            "",
            "| Run | Phase | Effect | Preference changed | Channel changed | Mean TV |",
            "|---|---|---|---:|---:|---:|",
        ]
    )
    for checkpoint in report["checkpoints"]:
        item = checkpoint["checkpoint"]
        for effect_name, values in checkpoint.get("checkpoint_footprint", {}).get("effects", {}).items():
            lines.append(
                f"| {item['run_name']} | {item['phase']} | {effect_name} | "
                f"{values['preference_changed_fraction']:.6f} | "
                f"{values['conditional_harvest_channel_changed_fraction']:.6f} | "
                f"{values['preference_total_variation_mean']:.8f} |"
            )
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
        description="Plan or execute paired D2 leave-one-module expression audits"
    )
    parser.add_argument("--run-dir", action="append")
    parser.add_argument(
        "--plan",
        help="Execute an existing d2_module_audit_plan.json without re-detecting phases.",
    )
    parser.add_argument("--output", required=True)
    parser.add_argument("--horizon", type=int, default=120)
    parser.add_argument("--phases", default=",".join(PHASES))
    parser.add_argument("--min-phase-tick", type=int)
    parser.add_argument("--allow-incomplete-cycle", action="store_true")
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--backend", choices=("cpu", "gpu", "auto"), default="auto")
    parser.add_argument(
        "--gpu-semantics-mode",
        choices=("strict-reference", "hybrid-accelerated"),
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=True)
    if bool(args.plan) == bool(args.run_dir):
        raise ValueError("provide exactly one of --plan or one or more --run-dir values")
    if args.plan:
        plan = load_module_audit_plan(args.plan)
    else:
        plan = build_module_audit_plan(
            args.run_dir,
            horizon_ticks=args.horizon,
            phases=_parse_csv(args.phases),
            min_phase_tick=args.min_phase_tick,
            allow_incomplete_cycle=args.allow_incomplete_cycle,
        )
    (output / "d2_module_audit_plan.json").write_text(
        json.dumps(asdict(plan), ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (output / "d2_module_audit_plan.md").write_text(
        render_plan_markdown(plan), encoding="utf-8"
    )
    if args.execute:
        execute_module_audit_plan(
            plan,
            output,
            backend=args.backend,
            gpu_semantics_mode=args.gpu_semantics_mode,
        )


if __name__ == "__main__":
    main()
