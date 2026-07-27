"""Paired fresh-population experiment for the v3 embodied output basis.

Both branches inherit and mutate the same v3 module genome, feed-forward
couplings, embodied routers, and structural costs.  The neutral branch disables
only locomotion, field-signal, and repair output publication.  Harvest routing
and module coupling remain active in both branches.  The comparison therefore
asks whether adding physically distinct output primitives expands realized
functional variation beyond the harvest-only v2 substrate.
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
    EMBODIED_FUNCTIONAL_MODULE_SCHEMA,
    EMBODIED_OUTPUT_SCHEMA,
)
from se.runtime.sim import Simulation

PLAN_SCHEMA = "d2-embodied-capability-plan-v1"
RESULT_SCHEMA = "d2-embodied-capability-results-v1"
BRANCHES: dict[str, tuple[str, ...]] = {
    "embodied-active": (),
    "embodied-neutral": ("neutralize-functional-module-embodied-output",),
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
    "functional_embodied_output_effective_dimensions",
    "functional_output_basis_effective_dimensions",
    "functional_output_basis_active_port_count",
    "functional_embodied_output_changed_entity_fraction",
    "functional_module_movement_energy_delta_total",
    "functional_module_signal_energy_delta_total",
    "functional_module_repair_energy_total",
    "functional_module_repair_material_total",
    "functional_module_repair_integrity_total",
)

LIST_METRICS = (
    "functional_module_hierarchy_depth_by_module",
    "functional_module_mediated_signal_abs_mean_by_module",
    "functional_embodied_output_names",
    "functional_embodied_output_mean",
    "functional_embodied_output_std",
    "functional_embodied_output_abs_mean_by_port",
    "functional_output_basis_std_by_port",
    "functional_output_basis_port_names",
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


def _require_embodied(cfg: SimulationConfig) -> None:
    validate_config(cfg)
    if cfg.functional_modules.schema != EMBODIED_FUNCTIONAL_MODULE_SCHEMA:
        raise ValueError("D2-J requires v3 embodied functional modules")
    if cfg.functional_modules.output_schema != EMBODIED_OUTPUT_SCHEMA:
        raise ValueError("D2-J requires the locomotion/signal/repair output schema")


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
        value = final.get(name, progress.get(name))
        if name.startswith("functional_") and name not in final:
            value = progress.get(name, value)
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            snapshot[name] = value
    for name in LIST_METRICS:
        value = progress.get(name, final.get(name))
        if isinstance(value, list):
            snapshot[name] = value
    return snapshot


def execute_embodied_capability(
    cfg: SimulationConfig,
    seeds: Iterable[int],
    output_dir: str | Path,
    *,
    backend: str = "cpu",
    until_tick: int | None = None,
    overwrite: bool = False,
) -> dict[str, Any]:
    _require_embodied(cfg)
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
        "same_v3_genome_in_both_branches": True,
        "same_initial_population_and_world_seed": True,
        "coupling_and_embodied_genes_mutate_in_both_branches": True,
        "harvest_and_coupling_output_active_in_both_branches": True,
        "embodied_router_structure_cost_retained_when_neutral": True,
        "outcome_conditioned_selection": False,
        "module_copy_number_changed": False,
        "versioned_world_primitive_extension": True,
        "world_primitives": [
            "locomotion-power-modulation",
            "field-signal-power-modulation",
            "material-to-integrity-repair",
        ],
    }
    (output / "d2_embodied_capability_plan.json").write_text(
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
                "embodied_output_active": not bool(interventions),
                "harvest_and_coupling_output_active": True,
                "embodied_router_structure_cost_retained": True,
                "final": _metric_snapshot(final, progress),
            }
        active = branch_reports["embodied-active"]["final"]
        neutral = branch_reports["embodied-neutral"]["final"]
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
                "embodied_minus_neutral": effects,
            }
        )
        partial = _result_payload(plan, pairs)
        (output / "d2_embodied_capability_results.json").write_text(
            json.dumps(partial, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    result = _result_payload(plan, pairs)
    (output / "d2_embodied_capability_results.md").write_text(
        render_markdown(result), encoding="utf-8"
    )
    return result


def _summary(values: list[float]) -> dict[str, Any]:
    ordered = sorted(values)
    midpoint = len(ordered) // 2
    median = (
        ordered[midpoint]
        if len(ordered) % 2
        else (ordered[midpoint - 1] + ordered[midpoint]) / 2.0
    )
    return {
        "values": values,
        "mean": float(sum(values) / len(values)),
        "median": float(median),
        "positive_count": sum(value > 0.0 for value in values),
        "negative_count": sum(value < 0.0 for value in values),
        "zero_count": sum(value == 0.0 for value in values),
    }


def _summarize_pairs(pairs: list[dict[str, Any]]) -> dict[str, Any]:
    metric_summaries: dict[str, Any] = {}
    for name in SCALAR_METRICS:
        values = [
            float(pair["embodied_minus_neutral"][name])
            for pair in pairs
            if name in pair["embodied_minus_neutral"]
        ]
        if values:
            metric_summaries[name] = _summary(values)

    usage_rows: list[dict[str, Any]] = []
    for pair in pairs:
        active = pair["branches"]["embodied-active"]["final"]
        neutral = pair["branches"]["embodied-neutral"]["final"]
        usage_rows.append(
            {
                "seed": pair["seed"],
                "active_changed_entity_fraction": float(
                    active.get("functional_embodied_output_changed_entity_fraction", 0.0)
                ),
                "neutral_changed_entity_fraction": float(
                    neutral.get("functional_embodied_output_changed_entity_fraction", 0.0)
                ),
                "active_output_effective_dimensions": float(
                    active.get("functional_embodied_output_effective_dimensions", 0.0)
                ),
                "active_output_basis_effective_dimensions": float(
                    active.get("functional_output_basis_effective_dimensions", 0.0)
                ),
                "neutral_output_basis_effective_dimensions": float(
                    neutral.get("functional_output_basis_effective_dimensions", 0.0)
                ),
                "active_output_basis_port_count": int(
                    active.get("functional_output_basis_active_port_count", 0)
                ),
                "neutral_output_basis_port_count": int(
                    neutral.get("functional_output_basis_active_port_count", 0)
                ),
                "repair_material_total": float(
                    active.get("functional_module_repair_material_total", 0.0)
                ),
                "movement_energy_delta_total": float(
                    active.get("functional_module_movement_energy_delta_total", 0.0)
                ),
                "signal_energy_delta_total": float(
                    active.get("functional_module_signal_energy_delta_total", 0.0)
                ),
            }
        )
    return {
        "metric_summaries": metric_summaries,
        "primitive_usage": {
            "rows": usage_rows,
            "active_output_in_every_seed": bool(usage_rows)
            and all(row["active_changed_entity_fraction"] > 0.0 for row in usage_rows),
            "neutral_output_zero_in_every_seed": bool(usage_rows)
            and all(row["neutral_changed_entity_fraction"] == 0.0 for row in usage_rows),
            "output_basis_expanded_in_every_seed": bool(usage_rows)
            and all(
                row["active_output_basis_port_count"]
                > row["neutral_output_basis_port_count"]
                for row in usage_rows
            ),
            "combined_dimension_increased_in_every_seed": bool(usage_rows)
            and all(
                row["active_output_basis_effective_dimensions"]
                > row["neutral_output_basis_effective_dimensions"]
                for row in usage_rows
            ),
            "repair_used_in_any_seed": any(
                row["repair_material_total"] > 0.0 for row in usage_rows
            ),
            "movement_power_used_in_any_seed": any(
                row["movement_energy_delta_total"] != 0.0 for row in usage_rows
            ),
            "signal_power_used_in_any_seed": any(
                row["signal_energy_delta_total"] != 0.0 for row in usage_rows
            ),
        },
        "decision_scope": "generative-substrate-capability-not-ecological-proof",
    }


def _result_payload(plan: dict[str, Any], pairs: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "schema": RESULT_SCHEMA,
        "plan": plan,
        "completed_seed_count": len(pairs),
        "pairs": pairs,
        "summary": _summarize_pairs(pairs),
        "interpretation_boundary": (
            "This experiment tests whether versioned locomotion, field-signal, and "
            "repair outputs are actually used and expand realized functional variation "
            "beyond harvest-only composition. It does not itself establish stable niche "
            "differentiation, coexistence, or a reason to change module copy number."
        ),
    }


def render_markdown(result: dict[str, Any]) -> str:
    lines = [
        "# D2-J embodied module capability",
        "",
        f"Schema: `{result['schema']}`",
        f"Completed seeds: `{result['completed_seed_count']}`",
        "",
        "| Seed | Branch | Alive | Effective lineages | Embodied dimensions | Embodied changed | Repair material |",
        "|---:|---|---:|---:|---:|---:|---:|",
    ]
    for pair in result["pairs"]:
        for branch_name, branch in pair["branches"].items():
            final = branch["final"]
            lines.append(
                "| {seed} | `{branch}` | {alive} | {lineages} | {dimensions} | {changed} | {repair} |".format(
                    seed=pair["seed"],
                    branch=branch_name,
                    alive=final.get("alive", "n/a"),
                    lineages=final.get("effective_lineages", "n/a"),
                    dimensions=final.get(
                        "functional_embodied_output_effective_dimensions", "n/a"
                    ),
                    changed=final.get(
                        "functional_embodied_output_changed_entity_fraction", "n/a"
                    ),
                    repair=final.get("functional_module_repair_material_total", "n/a"),
                )
            )
    usage = result["summary"]["primitive_usage"]
    lines.extend(
        [
            "",
            "## Primitive use",
            "",
            f"- active output in every seed: `{usage['active_output_in_every_seed']}`",
            f"- neutral output zero in every seed: `{usage['neutral_output_zero_in_every_seed']}`",
            f"- repair used in any seed: `{usage['repair_used_in_any_seed']}`",
            f"- movement power used in any seed: `{usage['movement_power_used_in_any_seed']}`",
            f"- signal power used in any seed: `{usage['signal_power_used_in_any_seed']}`",
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
            "Run paired fresh populations with v3 embodied outputs active or "
            "neutral while retaining the same genes, coupling, and costs"
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
    result = execute_embodied_capability(
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
                "primitive_usage": result["summary"]["primitive_usage"],
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
