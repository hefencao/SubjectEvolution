"""Paired counterfactual execution over an in-memory simulation snapshot."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path

from .simulation import Simulation, StepStats


@dataclass(frozen=True)
class PairedRunResult:
    baseline: dict[str, float | int]
    intervention: dict[str, float | int]
    delta: dict[str, float]
    intervention_tick: int
    pre_intervention: dict[str, float | int]


def run_paired(
    simulation: Simulation,
    intervention: str,
    output_dir: str | Path,
    *,
    intervention_tick: int | None = None,
) -> PairedRunResult:
    """Run a baseline and an intervention branch from the same world snapshot.

    Both branches retain the run seed and all stable IDs.  Because random
    draws are keyed by tick, phase, stable subject ID and stream, unrelated
    branch state cannot shift another entity's random sequence.
    """
    scheduled_tick = simulation.tick if intervention_tick is None else int(intervention_tick)
    if scheduled_tick < simulation.tick:
        raise ValueError(
            f"intervention_tick {scheduled_tick} precedes current tick {simulation.tick}"
        )
    if scheduled_tick >= simulation.cfg.run.ticks:
        raise ValueError(
            "intervention_tick must leave at least one post-intervention tick "
            f"before configured horizon {simulation.cfg.run.ticks}"
        )

    root = Path(output_dir)
    root.mkdir(parents=True, exist_ok=True)
    while simulation.tick < scheduled_tick:
        simulation.step()

    pre_stats = StepStats(
        group_count=int(simulation.last_group_summary.group_ids.size),
        mean_group_size=float(
            simulation.last_group_summary.counts.mean()
            if simulation.last_group_summary.counts.size
            else 0.0
        ),
    )
    pre_intervention = simulation.metric_row(
        pre_stats,
        0.0,
        window_seconds=0.0,
        window_ticks=0,
    )
    baseline = simulation
    branch = simulation.clone(root / "intervention")
    branch.apply_intervention(intervention)
    baseline_row = baseline.run()
    intervention_row = branch.run()
    keys = sorted(set(baseline_row) & set(intervention_row))
    delta = {
        key: float(intervention_row[key]) - float(baseline_row[key])
        for key in keys
        if isinstance(baseline_row[key], (int, float)) and isinstance(intervention_row[key], (int, float))
    }
    result = PairedRunResult(
        baseline_row,
        intervention_row,
        delta,
        scheduled_tick,
        pre_intervention,
    )
    (root / "counterfactual_summary.json").write_text(
        json.dumps(
            {
                "intervention": intervention,
                "intervention_tick": scheduled_tick,
                "shared_prehistory_ticks": scheduled_tick,
                "paired_randomness": True,
                "pre_intervention": pre_intervention,
                "baseline": baseline_row,
                "intervention_result": intervention_row,
                "delta_intervention_minus_baseline": delta,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    return result
