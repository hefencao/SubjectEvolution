"""Paired counterfactual execution over an in-memory simulation snapshot."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path

from .simulation import Simulation


@dataclass(frozen=True)
class PairedRunResult:
    baseline: dict[str, float | int]
    intervention: dict[str, float | int]
    delta: dict[str, float]


def run_paired(
    simulation: Simulation,
    intervention: str,
    output_dir: str | Path,
) -> PairedRunResult:
    """Run a baseline and an intervention branch from the same world snapshot.

    Both branches retain the run seed and all stable IDs.  Because random
    draws are keyed by tick, phase, stable subject ID and stream, unrelated
    branch state cannot shift another entity's random sequence.
    """
    root = Path(output_dir)
    root.mkdir(parents=True, exist_ok=True)
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
    result = PairedRunResult(baseline_row, intervention_row, delta)
    (root / "counterfactual_summary.json").write_text(
        json.dumps(
            {
                "intervention": intervention,
                "paired_randomness": True,
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
