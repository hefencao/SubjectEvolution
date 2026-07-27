"""Paired fresh-population experiment for the compositional module substrate.

This is not another module-copy gate.  Both branches use the same v2 genome,
initial population, world seed, mutation streams, expression costs, and six
inherited coupling genes.  The neutral branch suppresses only the feed-forward
coupling output from tick zero while retaining those genes and their structure
cost.  The comparison therefore asks whether allowing module combinations can
create mediated functional variation beyond four independent additive slots.
"""

from __future__ import annotations

import argparse
from dataclasses import asdict, replace
import json
from pathlib import Path
import shutil
from typing import Any, Iterable

from se.cfg import SimulationConfig, load_config, validate_config
from se.differentiation.functional import (
    COMPOSITIONAL_FUNCTIONAL_MODULE_SCHEMA,
    COUPLING_SCHEMA,
)
from se.runtime.sim import Simulation

PLAN_SCHEMA = "d2-compositional-capability-plan-v1"
RESULT_SCHEMA = "d2-compositional-capability-results-v1"
BRANCHES: dict[str, tuple[str, ...]] = {
    "composition-active": (),
    "coupling-neutral": ("neutralize-functional-module-coupling-output",),
}

SCALAR_METRICS = (
    "alive",
    "effective_lineages",
    "largest_lineage_fraction",
    "resource_affinity_effective_dimensions",
    "environment_resource_effective_dimensions",
    "functional_harvest_preference_effective_dimensions",
    "functional_module_contribution_effective_count",
    "functional_module_contribution_dominance",
    "functional_module_coupling_weight_effective_dimensions",
    "functional_module_coupling_changed_entity_fraction",
    "functional_module_mediated_signal_abs_mean",
    "functional_module_modulation_abs_mean",
    "functional_module_cancellation_fraction",
)


def parse_seeds(value: str | Iterable[int]) -> tuple[int, ...]:
    if isinstance(value, str):
        seeds = tuple(int(item.strip()) for item in value.split(",") if item.strip())
    else:
        seeds = tuple(int(item) for item in value)
    if not seeds:
        raise ValueError("at least one seed is required")
    if len(set(seeds)) != len(seeds):
        raise ValueError("seeds must be unique")
    return seeds


def _require_compositional(cfg: SimulationConfig) -> None:
    validate_config(cfg)
    if cfg.functional_modules.schema != COMPOSITIONAL_FUNCTIONAL_MODULE_SCHEMA:
        raise ValueError("D2-I requires compositional functional modules")
    if cfg.functional_modules.coupling_schema != COUPLING_SCHEMA:
        raise ValueError("D2-I requires the lower-slot signal coupling schema")


def _last_progress(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    last: dict[str, Any] = {}
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                last = json.loads(line)
    return last


def _metric_snapshot(final: dict[str, Any], progress: dict[str, Any]) -> dict[str, Any]:
    snapshot: dict[str, Any] = {}
    for name in SCALAR_METRICS:
        value = progress.get(name, final.get(name))
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            snapshot[name] = value
    for name in (
        "functional_module_hierarchy_depth_by_module",
        "functional_module_mediated_signal_abs_mean_by_module",
        "functional_module_coupling_amplification_fraction_by_module",
        "functional_module_coupling_suppression_fraction_by_module",
    ):
        value = progress.get(name)
        if isinstance(value, list):
            snapshot[name] = value
    return snapshot


def execute_compositional_capability(
    cfg: SimulationConfig,
    seeds: Iterable[int],
    output_dir: str | Path,
    *,
    backend: str = "cpu",
    until_tick: int | None = None,
    overwrite: bool = False,
) -> dict[str, Any]:
    _require_compositional(cfg)
    selected_seeds = parse_seeds(seeds)
    target_tick = int(cfg.run.ticks if until_tick is None else until_tick)
    if target_tick <= 0:
        raise ValueError("until_tick must be positive")
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    plan = {
        "schema": PLAN_SCHEMA,
        "seeds": list(selected_seeds),
        "horizon_ticks": target_tick,
        "branches": {key: list(value) for key, value in BRANCHES.items()},
        "same_v2_genome_in_both_branches": True,
        "same_initial_population_and_world_seed": True,
        "coupling_genes_mutate_in_both_branches": True,
        "coupling_structure_cost_retained_when_neutral": True,
        "outcome_conditioned_selection": False,
        "module_copy_number_changed": False,
        "new_world_physics": False,
    }
    (output / "d2_compositional_capability_plan.json").write_text(
        json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    pairs: list[dict[str, Any]] = []
    for seed in selected_seeds:
        run_cfg = replace(cfg, run=replace(cfg.run, seed=seed, ticks=target_tick))
        branch_reports: dict[str, Any] = {}
        for branch_name, interventions in BRANCHES.items():
            branch_dir = output / f"seed_{seed}" / branch_name
            if branch_dir.exists() and any(branch_dir.iterdir()):
                if not overwrite:
                    raise RuntimeError(
                        f"output already exists for seed {seed} branch {branch_name}: "
                        f"{branch_dir}; pass --overwrite to replace it"
                    )
                shutil.rmtree(branch_dir)
            branch_dir.mkdir(parents=True, exist_ok=True)
            (branch_dir / "resolved_config.json").write_text(
                json.dumps(asdict(run_cfg), ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            simulation = Simulation(run_cfg, branch_dir, backend=backend)
            for intervention in interventions:
                simulation.apply_intervention(intervention)
            final = simulation.run(until_tick=target_tick)
            progress = _last_progress(branch_dir / "evolution_progress.jsonl")
            branch_reports[branch_name] = {
                "output": str(branch_dir),
                "interventions": list(interventions),
                "coupling_output_active": not bool(interventions),
                "coupling_structure_cost_retained": True,
                "final": _metric_snapshot(final, progress),
            }
        active = branch_reports["composition-active"]["final"]
        neutral = branch_reports["coupling-neutral"]["final"]
        effects: dict[str, float] = {}
        for name in SCALAR_METRICS:
            left = active.get(name)
            right = neutral.get(name)
            if isinstance(left, (int, float)) and isinstance(right, (int, float)):
                effects[name] = float(left) - float(right)
        pairs.append(
            {
                "seed": seed,
                "branches": branch_reports,
                "composition_minus_neutral": effects,
            }
        )
        partial = _result_payload(plan, pairs)
        (output / "d2_compositional_capability_results.json").write_text(
            json.dumps(partial, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    result = _result_payload(plan, pairs)
    (output / "d2_compositional_capability_results.md").write_text(
        render_markdown(result), encoding="utf-8"
    )
    return result


def _summarize_pairs(pairs: list[dict[str, Any]]) -> dict[str, Any]:
    metric_summaries: dict[str, Any] = {}
    for name in SCALAR_METRICS:
        values = [
            float(pair["composition_minus_neutral"][name])
            for pair in pairs
            if name in pair["composition_minus_neutral"]
        ]
        if not values:
            continue
        ordered = sorted(values)
        midpoint = len(ordered) // 2
        median = (
            ordered[midpoint]
            if len(ordered) % 2
            else (ordered[midpoint - 1] + ordered[midpoint]) / 2.0
        )
        metric_summaries[name] = {
            "values": values,
            "mean": float(sum(values) / len(values)),
            "median": float(median),
            "positive_count": sum(value > 0.0 for value in values),
            "negative_count": sum(value < 0.0 for value in values),
            "zero_count": sum(value == 0.0 for value in values),
        }

    usage_rows: list[dict[str, Any]] = []
    for pair in pairs:
        active = pair["branches"]["composition-active"]["final"]
        neutral = pair["branches"]["coupling-neutral"]["final"]
        active_by_module = active.get(
            "functional_module_mediated_signal_abs_mean_by_module", []
        )
        downstream_used = sum(
            float(value) > 0.0 for value in active_by_module[1:]
        )
        usage_rows.append(
            {
                "seed": pair["seed"],
                "active_mediated_signal": float(
                    active.get("functional_module_mediated_signal_abs_mean", 0.0)
                ),
                "neutral_mediated_signal": float(
                    neutral.get("functional_module_mediated_signal_abs_mean", 0.0)
                ),
                "active_changed_entity_fraction": float(
                    active.get(
                        "functional_module_coupling_changed_entity_fraction", 0.0
                    )
                ),
                "downstream_levels_with_mediated_signal": int(downstream_used),
            }
        )
    return {
        "metric_summaries": metric_summaries,
        "mechanism_usage": {
            "rows": usage_rows,
            "active_in_every_seed": bool(usage_rows)
            and all(row["active_mediated_signal"] > 0.0 for row in usage_rows),
            "neutral_zero_in_every_seed": bool(usage_rows)
            and all(row["neutral_mediated_signal"] == 0.0 for row in usage_rows),
            "entity_level_effect_in_every_seed": bool(usage_rows)
            and all(row["active_changed_entity_fraction"] > 0.0 for row in usage_rows),
            "multiple_hierarchy_levels_used_in_any_seed": any(
                row["downstream_levels_with_mediated_signal"] >= 2
                for row in usage_rows
            ),
        },
        "decision_scope": "descriptive-generative-capability-not-pass-fail-gate",
    }


def _result_payload(plan: dict[str, Any], pairs: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "schema": RESULT_SCHEMA,
        "plan": plan,
        "completed_seed_count": len(pairs),
        "pairs": pairs,
        "summary": _summarize_pairs(pairs),
        "interpretation_boundary": _interpretation_boundary(),
    }


def _interpretation_boundary() -> str:
    return (
        "This paired experiment tests whether inherited feed-forward module coupling "
        "changes realized functional variation while holding the v2 genome, coupling "
        "genes, mutation process, and coupling structure cost present in both branches. "
        "It does not by itself establish ecological differentiation, niche coexistence, "
        "or a reason to change module copy number."
    )


def render_markdown(result: dict[str, Any]) -> str:
    lines = [
        "# D2-I compositional module capability",
        "",
        f"Schema: `{result['schema']}`",
        f"Completed seeds: `{result['completed_seed_count']}`",
        "",
        "| Seed | Branch | Alive | Effective lineages | Mediated signal | Coupling changed |",
        "|---:|---|---:|---:|---:|---:|",
    ]
    for pair in result["pairs"]:
        for branch_name, branch in pair["branches"].items():
            final = branch["final"]
            lines.append(
                "| {seed} | `{branch}` | {alive} | {lineages} | {mediated} | {changed} |".format(
                    seed=pair["seed"],
                    branch=branch_name,
                    alive=final.get("alive", "n/a"),
                    lineages=final.get("effective_lineages", "n/a"),
                    mediated=final.get("functional_module_mediated_signal_abs_mean", "n/a"),
                    changed=final.get(
                        "functional_module_coupling_changed_entity_fraction", "n/a"
                    ),
                )
            )
    usage = result["summary"]["mechanism_usage"]
    lines.extend(
        [
            "",
            "## Generative capability summary",
            "",
            f"- coupling used in every active seed: `{usage['active_in_every_seed']}`",
            f"- neutral branches remain at zero mediated signal: `{usage['neutral_zero_in_every_seed']}`",
            f"- entity-level coupling effect in every seed: `{usage['entity_level_effect_in_every_seed']}`",
            f"- multiple hierarchy levels used in any seed: `{usage['multiple_hierarchy_levels_used_in_any_seed']}`",
            "- this summary is descriptive and is not a pass/fail continuation gate",
            "",
            "## Interpretation boundary",
            "",
            result["interpretation_boundary"],
            "",
        ]
    )
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Run paired fresh populations with compositional coupling active or "
            "output-neutral while retaining the same genes and costs"
        )
    )
    parser.add_argument("--config", required=True)
    parser.add_argument("--seeds", required=True, help="Comma-separated integer seeds")
    parser.add_argument("--output", required=True)
    parser.add_argument("--backend", choices=("cpu", "gpu", "auto"), default="cpu")
    parser.add_argument("--until-tick", type=int)
    parser.add_argument("--overwrite", action="store_true")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    result = execute_compositional_capability(
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
                "passed": True,
                "schema": result["schema"],
                "completed_seed_count": result["completed_seed_count"],
                "module_copy_number_ready": False,
                "recommendation": "run-compositional-capability-evolution-before-resuming-d4",
            }
        )
    )


if __name__ == "__main__":
    main()
