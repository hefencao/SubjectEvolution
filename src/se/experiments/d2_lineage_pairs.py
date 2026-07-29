"""Lineage-balanced paired D2 module audit.

This experiment is the guarded successor to D2-C when fixed modules have an
immediate cross-lineage footprint but the source population is lineage
concentrated.  It does not duplicate, delete, reroute, reward, protect, or edit
modules.  Instead, it branches a shared checkpoint and neutralizes one existing
module only within one preselected genetic lineage.

For each module-lineage pair three branches are compared:

* baseline: inherited output and expression cost retained;
* output-neutral: routed output removed, expression cost retained;
* expression-neutral: routed output and expression cost removed.

The decomposition separates the ecological effect of routed output from the
energy refund created by a full expression ablation.  Lineages are selected by
pre-intervention membership only, never by endpoint response magnitude.
"""

from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
import json
from pathlib import Path
import tempfile
from typing import Any, Iterable, Sequence

import numpy as np

from se.experiments.d2_module_audit import (
    DEFAULT_OUTCOMES,
    MODULE_COUNT,
    RESULT_SCHEMAS as D2_RESULT_SCHEMAS,
    _derived_endpoint,
    _flatten_numeric,
)
from se.runtime.sim import Simulation

PLAN_SCHEMA = "d2-lineage-paired-plan-v2"
PLAN_SCHEMAS = frozenset({"d2-lineage-paired-plan-v1", PLAN_SCHEMA})
RESULT_SCHEMA = "d2-lineage-paired-results-v2"
RESULT_SCHEMAS = frozenset({"d2-lineage-paired-results-v1", RESULT_SCHEMA})

BRANCHES = ("baseline", "output-neutral", "expression-neutral")
EFFECTS = (
    "output_routing_effect",
    "retained_expression_cost_effect",
    "total_expression_effect",
)


@dataclass(frozen=True)
class LineageSelection:
    lineage_id: int
    members: int
    member_fraction: float
    abundance_rank: int


@dataclass(frozen=True)
class LineagePairCheckpoint:
    run_name: str
    phase: str
    checkpoint_tick: int
    checkpoint_path: str
    until_tick: int
    active_entities: int
    effective_lineages: float
    dominant_lineage_fraction: float
    eligible: bool
    ineligible_reason: str | None
    lineages: tuple[LineageSelection, ...]


@dataclass(frozen=True)
class LineagePairPlan:
    schema: str
    horizon_ticks: int
    module_indices: tuple[int, ...]
    min_lineage_members: int
    min_lineages_per_checkpoint: int
    max_lineages_per_checkpoint: int
    checkpoints: tuple[LineagePairCheckpoint, ...]
    lineage_selection_rule: str = "largest-preintervention-lineages-by-membership-v1"
    paired_randomness: bool = True
    genotype_preserved: bool = True
    lineage_membership_preserved: bool = True
    abundance_weighted_inference: bool = False
    branches: tuple[str, ...] = BRANCHES
    effect_decomposition_schema: str = "output-cost-total-additive-v1"
    confirmation_source_result_schema: str | None = None
    confirmation_source_horizon_ticks: int | None = None
    confirmation_selection_rule: str | None = None
    outcome_conditioned_pair_selection: bool = False


def _normalize_modules(values: Iterable[int]) -> tuple[int, ...]:
    result: list[int] = []
    for value in values:
        index = int(value)
        if not 0 <= index < MODULE_COUNT:
            raise ValueError(f"module index {index} is outside [0, {MODULE_COUNT})")
        if index not in result:
            result.append(index)
    if not result:
        raise ValueError("at least one module index is required")
    return tuple(result)


def _effective_count(counts: np.ndarray) -> float:
    values = np.asarray(counts, dtype=np.float64)
    total = float(values.sum())
    if total <= 0.0:
        return 0.0
    shares = values / total
    squared = float(np.square(shares).sum())
    return 1.0 / squared if squared > 0.0 else 0.0


def inspect_checkpoint_lineages(
    checkpoint_path: str | Path,
    *,
    min_lineage_members: int,
    min_lineages_per_checkpoint: int,
    max_lineages_per_checkpoint: int,
) -> dict[str, Any]:
    if min_lineage_members <= 0:
        raise ValueError("min_lineage_members must be positive")
    if min_lineages_per_checkpoint < 2:
        raise ValueError("min_lineages_per_checkpoint must be at least 2")
    if max_lineages_per_checkpoint < min_lineages_per_checkpoint:
        raise ValueError(
            "max_lineages_per_checkpoint must be >= min_lineages_per_checkpoint"
        )
    with tempfile.TemporaryDirectory(prefix="se-d2-lineage-inspect-") as temporary:
        simulation = Simulation.from_checkpoint(
            checkpoint_path,
            Path(temporary) / "load",
            backend="cpu",
        )
        if (
            not simulation.cfg.functional_modules.enabled
            or int(simulation.cfg.functional_modules.module_count) != MODULE_COUNT
        ):
            raise ValueError(
                "D2 lineage-pair source checkpoint must use four enabled fixed modules"
            )
        if (
            simulation.functional_modules_ablation_enabled
            or np.any(simulation.functional_module_ablation_mask)
            or simulation.functional_module_lineage_output_ablation
            or simulation.functional_module_lineage_cost_ablation
        ):
            raise ValueError(
                "D2 lineage-pair source checkpoint already contains a functional-module treatment"
            )
        active = np.flatnonzero(simulation.entities.alive).astype(np.int32)
        lineage_ids = simulation.entities.lineage_id[active].astype(np.uint64, copy=False)
        unique, counts = np.unique(lineage_ids, return_counts=True)
        order = np.lexsort((unique, -counts))
        total = int(active.size)
        selections: list[LineageSelection] = []
        for rank, position in enumerate(order, start=1):
            members = int(counts[position])
            if members < min_lineage_members:
                continue
            selections.append(
                LineageSelection(
                    lineage_id=int(unique[position]),
                    members=members,
                    member_fraction=(float(members) / total if total else 0.0),
                    abundance_rank=rank,
                )
            )
            if len(selections) >= max_lineages_per_checkpoint:
                break
        eligible = len(selections) >= min_lineages_per_checkpoint
        reason = None
        if not eligible:
            reason = (
                "insufficient-preintervention-lineages: "
                f"required={min_lineages_per_checkpoint}, found={len(selections)}, "
                f"minimum-members={min_lineage_members}"
            )
        return {
            "checkpoint_tick": int(simulation.tick),
            "active_entities": total,
            "effective_lineages": _effective_count(counts),
            "dominant_lineage_fraction": (
                float(counts.max()) / total if total and counts.size else 0.0
            ),
            "eligible": eligible,
            "ineligible_reason": reason,
            "lineages": tuple(selections),
        }


def _resolve_checkpoint_path(value: str, base_dir: Path | None) -> Path:
    path = Path(value)
    if path.is_file():
        return path.resolve()
    if base_dir is not None and not path.is_absolute():
        candidate = (base_dir / path).resolve()
        if candidate.is_file():
            return candidate
    raise FileNotFoundError(f"referenced D2 checkpoint does not exist: {value}")


def build_lineage_pair_plan(
    results: dict[str, Any],
    *,
    horizon_ticks: int,
    module_indices: Iterable[int] = (2, 3),
    min_lineage_members: int = 8,
    min_lineages_per_checkpoint: int = 3,
    max_lineages_per_checkpoint: int = 4,
    results_base_dir: str | Path | None = None,
) -> LineagePairPlan:
    if results.get("schema") not in D2_RESULT_SCHEMAS:
        raise ValueError(f"unsupported D2 audit result schema: {results.get('schema')!r}")
    if horizon_ticks <= 0:
        raise ValueError("horizon_ticks must be positive")
    modules = _normalize_modules(module_indices)
    base_dir = Path(results_base_dir).resolve() if results_base_dir is not None else None
    checkpoints: list[LineagePairCheckpoint] = []
    for item in results.get("checkpoints", ()):
        meta = item["checkpoint"]
        checkpoint_path = _resolve_checkpoint_path(
            str(meta["checkpoint_path"]), base_dir
        )
        inspected = inspect_checkpoint_lineages(
            checkpoint_path,
            min_lineage_members=min_lineage_members,
            min_lineages_per_checkpoint=min_lineages_per_checkpoint,
            max_lineages_per_checkpoint=max_lineages_per_checkpoint,
        )
        checkpoint_tick = int(meta["checkpoint_tick"])
        if int(inspected["checkpoint_tick"]) != checkpoint_tick:
            raise ValueError(
                "D2 result checkpoint metadata does not match checkpoint payload: "
                f"{checkpoint_tick} vs {inspected['checkpoint_tick']}"
            )
        checkpoints.append(
            LineagePairCheckpoint(
                run_name=str(meta["run_name"]),
                phase=str(meta["phase"]),
                checkpoint_tick=checkpoint_tick,
                checkpoint_path=str(checkpoint_path),
                until_tick=checkpoint_tick + int(horizon_ticks),
                active_entities=int(inspected["active_entities"]),
                effective_lineages=float(inspected["effective_lineages"]),
                dominant_lineage_fraction=float(
                    inspected["dominant_lineage_fraction"]
                ),
                eligible=bool(inspected["eligible"]),
                ineligible_reason=inspected["ineligible_reason"],
                lineages=tuple(inspected["lineages"]),
            )
        )
    if not checkpoints:
        raise ValueError("D2 audit result contains no checkpoints")
    return LineagePairPlan(
        schema=PLAN_SCHEMA,
        horizon_ticks=int(horizon_ticks),
        module_indices=modules,
        min_lineage_members=int(min_lineage_members),
        min_lineages_per_checkpoint=int(min_lineages_per_checkpoint),
        max_lineages_per_checkpoint=int(max_lineages_per_checkpoint),
        checkpoints=tuple(checkpoints),
    )


def load_lineage_pair_plan(path: str | Path) -> LineagePairPlan:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if payload.get("schema") not in PLAN_SCHEMAS:
        raise ValueError(f"unsupported D2 lineage-pair plan: {payload.get('schema')!r}")
    checkpoints: list[LineagePairCheckpoint] = []
    for item in payload.get("checkpoints", ()):
        lineages = tuple(LineageSelection(**value) for value in item.get("lineages", ()))
        checkpoints.append(LineagePairCheckpoint(**{**item, "lineages": lineages}))
    if not checkpoints:
        raise ValueError("D2 lineage-pair plan contains no checkpoints")
    return LineagePairPlan(
        schema=payload["schema"],
        horizon_ticks=int(payload["horizon_ticks"]),
        module_indices=_normalize_modules(payload["module_indices"]),
        min_lineage_members=int(payload["min_lineage_members"]),
        min_lineages_per_checkpoint=int(payload["min_lineages_per_checkpoint"]),
        max_lineages_per_checkpoint=int(payload["max_lineages_per_checkpoint"]),
        checkpoints=tuple(checkpoints),
        lineage_selection_rule=str(payload.get("lineage_selection_rule", "")),
        paired_randomness=bool(payload.get("paired_randomness", True)),
        genotype_preserved=bool(payload.get("genotype_preserved", True)),
        lineage_membership_preserved=bool(
            payload.get("lineage_membership_preserved", True)
        ),
        abundance_weighted_inference=bool(
            payload.get("abundance_weighted_inference", False)
        ),
        branches=tuple(payload.get("branches", BRANCHES)),
        effect_decomposition_schema=str(
            payload.get("effect_decomposition_schema", "output-cost-total-additive-v1")
        ),
        confirmation_source_result_schema=payload.get(
            "confirmation_source_result_schema"
        ),
        confirmation_source_horizon_ticks=(
            int(payload["confirmation_source_horizon_ticks"])
            if payload.get("confirmation_source_horizon_ticks") is not None
            else None
        ),
        confirmation_selection_rule=payload.get("confirmation_selection_rule"),
        outcome_conditioned_pair_selection=bool(
            payload.get("outcome_conditioned_pair_selection", False)
        ),
    )


def _cohort_endpoint(simulation: Simulation, lineage_id: int) -> dict[str, float]:
    rows = np.flatnonzero(
        simulation.entities.alive
        & (simulation.entities.lineage_id == np.uint64(lineage_id))
    ).astype(np.int32)
    result: dict[str, float] = {"alive": float(rows.size)}
    for name in (
        "energy",
        "integrity",
        "material",
        "information_store",
        "fertility",
    ):
        values = np.asarray(getattr(simulation.entities, name)[rows], dtype=np.float64)
        result[f"mean_{name}"] = float(values.mean()) if values.size else 0.0
    return result


def _run_branch(
    checkpoint: LineagePairCheckpoint,
    output_dir: Path,
    *,
    backend: str,
    gpu_semantics_mode: str | None,
    module_index: int | None = None,
    lineage_id: int | None = None,
    neutralize_cost: bool = False,
) -> tuple[dict[str, Any], Simulation]:
    simulation = Simulation.from_checkpoint(
        checkpoint.checkpoint_path,
        output_dir,
        backend=backend,
        until_tick=checkpoint.until_tick,
        gpu_semantics_mode=gpu_semantics_mode,
    )
    genotype_before = simulation.entities.genotype.copy()
    lineage_before = simulation.entities.lineage_id.copy()
    if module_index is not None:
        if lineage_id is None:
            raise ValueError("lineage_id is required for a targeted branch")
        simulation.apply_functional_module_lineage_intervention(
            module_index=module_index,
            lineage_id=lineage_id,
            neutralize_cost=neutralize_cost,
        )
    if not np.array_equal(simulation.entities.genotype, genotype_before):
        raise RuntimeError("lineage-targeted module intervention modified genotype")
    if not np.array_equal(simulation.entities.lineage_id, lineage_before):
        raise RuntimeError("lineage-targeted module intervention modified lineage IDs")
    world = simulation.run(until_tick=checkpoint.until_tick)
    evolution = (
        simulation.evolution_progress.records[-1]
        if simulation.evolution_progress.records
        else {}
    )
    return (
        {
            "world": world,
            "evolution": evolution,
            "derived": _derived_endpoint(evolution),
            "scientific_validity": simulation.scientific_validity(),
            "intervention_history": simulation.intervention_history,
        },
        simulation,
    )


def _selected_outcomes(
    branch: dict[str, Any],
    cohort: dict[str, float],
) -> dict[str, float]:
    flattened = {
        **_flatten_numeric("world", branch["world"]),
        **_flatten_numeric("evolution", branch["evolution"]),
        **_flatten_numeric("derived", branch["derived"]),
        **_flatten_numeric("target_lineage", cohort),
    }
    selected = {
        outcome: flattened[outcome]
        for outcome in DEFAULT_OUTCOMES
        if outcome in flattened
    }
    selected.update(
        {
            key: value
            for key, value in flattened.items()
            if key.startswith("target_lineage.")
        }
    )
    return selected


def _effects(
    baseline: dict[str, float],
    output_neutral: dict[str, float],
    expression_neutral: dict[str, float],
) -> dict[str, dict[str, float]]:
    common = sorted(set(baseline) & set(output_neutral) & set(expression_neutral))
    output_effect = {
        key: baseline[key] - output_neutral[key]
        for key in common
    }
    retained_cost = {
        key: output_neutral[key] - expression_neutral[key]
        for key in common
    }
    total = {
        key: baseline[key] - expression_neutral[key]
        for key in common
    }
    residual = {
        key: total[key] - output_effect[key] - retained_cost[key]
        for key in common
    }
    if any(abs(value) > 1e-12 for value in residual.values()):
        raise RuntimeError("D2 lineage effect decomposition is not numerically closed")
    return {
        "output_routing_effect": output_effect,
        "retained_expression_cost_effect": retained_cost,
        "total_expression_effect": total,
        "decomposition_residual": residual,
    }


def _aggregate(rows: Sequence[dict[str, Any]]) -> dict[str, Any]:
    buckets: dict[tuple[int, str, str], list[dict[str, Any]]] = {}
    for row in rows:
        for effect_name in EFFECTS:
            for outcome, value in row["effects"][effect_name].items():
                buckets.setdefault(
                    (int(row["module_index"]), effect_name, outcome), []
                ).append({**row["pair"], "value": float(value)})
    aggregate: dict[str, Any] = {}
    for (module_index, effect_name, outcome), values in sorted(buckets.items()):
        array = np.asarray([item["value"] for item in values], dtype=np.float64)
        nonzero = array[np.abs(array) > 1e-12]
        payload = {
            "paired_lineage_count": int(array.size),
            "checkpoint_count": len(
                {
                    (item["run_name"], item["phase"], item["checkpoint_tick"])
                    for item in values
                }
            ),
            "seed_count": len({item["run_name"] for item in values}),
            "distinct_lineage_identity_count": len(
                {
                    (item["run_name"], int(item["lineage_id"]))
                    for item in values
                }
            ),
            "mean": float(array.mean()),
            "median": float(np.median(array)),
            "min": float(array.min()),
            "max": float(array.max()),
            "std": float(array.std()),
            "positive_count": int(np.count_nonzero(array > 1e-12)),
            "negative_count": int(np.count_nonzero(array < -1e-12)),
            "same_nonzero_sign": bool(
                nonzero.size > 0
                and (np.all(nonzero > 0.0) or np.all(nonzero < 0.0))
            ),
            "equal_weight_per_checkpoint_lineage_pair": True,
        }
        aggregate.setdefault(f"module_{module_index}", {}).setdefault(
            effect_name, {}
        )[outcome] = payload
    return aggregate


def execute_lineage_pair_plan(
    plan: LineagePairPlan,
    output_dir: str | Path,
    *,
    backend: str = "auto",
    gpu_semantics_mode: str | None = None,
) -> dict[str, Any]:
    if tuple(plan.branches) != BRANCHES:
        raise ValueError(
            f"unsupported D2 lineage-pair branch layout: {plan.branches!r}"
        )
    if plan.effect_decomposition_schema != "output-cost-total-additive-v1":
        raise ValueError(
            "unsupported D2 lineage-pair effect decomposition schema: "
            f"{plan.effect_decomposition_schema!r}"
        )
    root = Path(output_dir)
    root.mkdir(parents=True, exist_ok=True)
    checkpoint_reports: list[dict[str, Any]] = []
    pair_rows: list[dict[str, Any]] = []
    for checkpoint in plan.checkpoints:
        if not checkpoint.eligible:
            checkpoint_reports.append(
                {
                    "checkpoint": asdict(checkpoint),
                    "status": "ineligible",
                    "reason": checkpoint.ineligible_reason,
                    "pairs": [],
                }
            )
            continue
        checkpoint_dir = root / checkpoint.run_name / checkpoint.phase
        baseline_branch, baseline_simulation = _run_branch(
            checkpoint,
            checkpoint_dir / "baseline",
            backend=backend,
            gpu_semantics_mode=gpu_semantics_mode,
        )
        pairs: list[dict[str, Any]] = []
        for module_index in plan.module_indices:
            for lineage in checkpoint.lineages:
                pair_dir = checkpoint_dir / f"module_{module_index}" / f"lineage_{lineage.lineage_id}"
                output_branch, output_simulation = _run_branch(
                    checkpoint,
                    pair_dir / "output_neutral",
                    backend=backend,
                    gpu_semantics_mode=gpu_semantics_mode,
                    module_index=module_index,
                    lineage_id=lineage.lineage_id,
                    neutralize_cost=False,
                )
                expression_branch, expression_simulation = _run_branch(
                    checkpoint,
                    pair_dir / "expression_neutral",
                    backend=backend,
                    gpu_semantics_mode=gpu_semantics_mode,
                    module_index=module_index,
                    lineage_id=lineage.lineage_id,
                    neutralize_cost=True,
                )
                baseline_outcomes = _selected_outcomes(
                    baseline_branch,
                    _cohort_endpoint(baseline_simulation, lineage.lineage_id),
                )
                output_outcomes = _selected_outcomes(
                    output_branch,
                    _cohort_endpoint(output_simulation, lineage.lineage_id),
                )
                expression_outcomes = _selected_outcomes(
                    expression_branch,
                    _cohort_endpoint(expression_simulation, lineage.lineage_id),
                )
                pair_meta = {
                    "run_name": checkpoint.run_name,
                    "phase": checkpoint.phase,
                    "checkpoint_tick": checkpoint.checkpoint_tick,
                    "lineage_id": lineage.lineage_id,
                    "source_members": lineage.members,
                    "source_member_fraction": lineage.member_fraction,
                    "source_abundance_rank": lineage.abundance_rank,
                }
                row = {
                    "pair": pair_meta,
                    "module_index": module_index,
                    "branches": {
                        "baseline": {
                            "output_dir": str(checkpoint_dir / "baseline"),
                            "outcomes": baseline_outcomes,
                            "scientific_validity": baseline_branch["scientific_validity"],
                            "intervention_history": baseline_branch["intervention_history"],
                        },
                        "output-neutral": {
                            "output_dir": str(pair_dir / "output_neutral"),
                            "outcomes": output_outcomes,
                            "scientific_validity": output_branch["scientific_validity"],
                            "intervention_history": output_branch["intervention_history"],
                        },
                        "expression-neutral": {
                            "output_dir": str(pair_dir / "expression_neutral"),
                            "outcomes": expression_outcomes,
                            "scientific_validity": expression_branch["scientific_validity"],
                            "intervention_history": expression_branch["intervention_history"],
                        },
                    },
                    "effects": _effects(
                        baseline_outcomes,
                        output_outcomes,
                        expression_outcomes,
                    ),
                }
                pairs.append(row)
                pair_rows.append(row)
        checkpoint_reports.append(
            {
                "checkpoint": asdict(checkpoint),
                "status": "executed",
                "pairs": pairs,
            }
        )
    report = {
        "schema": RESULT_SCHEMA,
        "plan": asdict(plan),
        "backend": backend,
        "gpu_semantics_mode": gpu_semantics_mode,
        "checkpoints": checkpoint_reports,
        "aggregate_effects": _aggregate(pair_rows),
        "executed_pair_count": len(pair_rows),
        "eligible_checkpoint_count": sum(item.eligible for item in plan.checkpoints),
        "interpretation_boundary": (
            "Each row is a paired lineage-within-checkpoint intervention, not an "
            "independent population replicate. Checkpoint-lineage pairs receive equal "
            "summary weight regardless of abundance. Output-neutral branches retain expression "
            "cost; expression-neutral branches remove both output and cost. The design "
            "tests lineage-conditioned causal persistence of fixed modules and does not "
            "justify duplication, protect diversity, or define ecological roles."
        ),
    }
    (root / "d2_lineage_pair_results.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (root / "d2_lineage_pair_results.md").write_text(
        render_results_markdown(report), encoding="utf-8"
    )
    return report


def render_plan_markdown(plan: LineagePairPlan) -> str:
    lines = [
        "# D2 lineage-balanced paired audit plan",
        "",
        f"Schema: `{plan.schema}`",
        f"Post-intervention horizon: **{plan.horizon_ticks} ticks**",
        f"Fixed modules: `{', '.join(map(str, plan.module_indices))}`",
        "",
    ]
    if plan.confirmation_source_horizon_ticks is not None:
        lines.extend(
            [
                "## Confirmation design",
                "",
                f"Source screen horizon: **{plan.confirmation_source_horizon_ticks} ticks**",
                f"Selection rule: `{plan.confirmation_selection_rule}`",
                f"Outcome-conditioned pair selection: **{plan.outcome_conditioned_pair_selection}**",
                "",
            ]
        )
    lines.extend(
        [
            "| Run | Phase | Checkpoint | Active | Effective lineages | Dominant share | Selected | Eligible |",
            "|---|---|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for checkpoint in plan.checkpoints:
        lines.append(
            f"| {checkpoint.run_name} | {checkpoint.phase} | {checkpoint.checkpoint_tick} | "
            f"{checkpoint.active_entities} | {checkpoint.effective_lineages:.4f} | "
            f"{checkpoint.dominant_lineage_fraction:.4f} | {len(checkpoint.lineages)} | "
            f"{checkpoint.eligible} |"
        )
    lines.extend(
        [
            "",
            "## Branches per module-lineage pair",
            "",
            "- `baseline`: output and expression cost retained",
            "- `output-neutral`: output removed, expression cost retained",
            "- `expression-neutral`: output and expression cost removed",
            "",
            "> Selection uses pre-intervention lineage membership only. No lineage is rewarded, protected, created, or reweighted inside the world.",
            "",
        ]
    )
    return "\n".join(lines)


def render_results_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# D2 lineage-balanced paired audit results",
        "",
        f"Executed pairs: **{report['executed_pair_count']}**",
        "",
        "| Run | Phase | Module | Lineage | Rank | Outcome | Output effect | Retained-cost effect | Total effect |",
        "|---|---|---:|---:|---:|---|---:|---:|---:|",
    ]
    for checkpoint in report["checkpoints"]:
        for row in checkpoint.get("pairs", ()):
            pair = row["pair"]
            for outcome in (
                "world.alive",
                "world.mean_energy",
                "target_lineage.alive",
                "target_lineage.mean_energy",
                "derived.harvest_extraction_efficiency_window",
            ):
                if outcome not in row["effects"]["total_expression_effect"]:
                    continue
                lines.append(
                    f"| {pair['run_name']} | {pair['phase']} | {row['module_index']} | "
                    f"{pair['lineage_id']} | {pair['source_abundance_rank']} | `{outcome}` | "
                    f"{row['effects']['output_routing_effect'][outcome]:+.6f} | "
                    f"{row['effects']['retained_expression_cost_effect'][outcome]:+.6f} | "
                    f"{row['effects']['total_expression_effect'][outcome]:+.6f} |"
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


def _parse_csv_ints(value: str) -> tuple[int, ...]:
    values = tuple(int(item.strip()) for item in value.split(",") if item.strip())
    return _normalize_modules(values)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Plan or execute lineage-balanced paired D2 module interventions "
            "without changing module copy number"
        )
    )
    parser.add_argument("--results", help="Existing D2 leave-one-out result JSON")
    parser.add_argument("--plan", help="Existing d2_lineage_pair_plan.json")
    parser.add_argument("--output", required=True)
    parser.add_argument("--modules", default="2,3")
    parser.add_argument("--horizon", type=int, default=120)
    parser.add_argument("--min-lineage-members", type=int, default=8)
    parser.add_argument("--min-lineages-per-checkpoint", type=int, default=3)
    parser.add_argument("--max-lineages-per-checkpoint", type=int, default=4)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--backend", choices=("cpu", "gpu", "auto"), default="auto")
    parser.add_argument(
        "--gpu-semantics-mode",
        choices=("strict-reference", "hybrid-accelerated"),
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    if bool(args.results) == bool(args.plan):
        raise ValueError("provide exactly one of --results or --plan")
    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=True)
    if args.plan:
        plan = load_lineage_pair_plan(args.plan)
    else:
        results_path = Path(args.results)
        results = json.loads(results_path.read_text(encoding="utf-8"))
        plan = build_lineage_pair_plan(
            results,
            horizon_ticks=args.horizon,
            module_indices=_parse_csv_ints(args.modules),
            min_lineage_members=args.min_lineage_members,
            min_lineages_per_checkpoint=args.min_lineages_per_checkpoint,
            max_lineages_per_checkpoint=args.max_lineages_per_checkpoint,
            results_base_dir=results_path.resolve().parent,
        )
    (output / "d2_lineage_pair_plan.json").write_text(
        json.dumps(asdict(plan), ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (output / "d2_lineage_pair_plan.md").write_text(
        render_plan_markdown(plan), encoding="utf-8"
    )
    if args.execute:
        execute_lineage_pair_plan(
            plan,
            output,
            backend=args.backend,
            gpu_semantics_mode=args.gpu_semantics_mode,
        )


if __name__ == "__main__":
    main()
