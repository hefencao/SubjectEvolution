"""Paired counterfactual execution from an in-memory or restored snapshot."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path

from ..runtime.sim import Simulation
from ..runtime.state import StepStats


@dataclass(frozen=True)
class PairedRunResult:
    baseline: dict[str, float | int]
    intervention: dict[str, float | int]
    delta: dict[str, float]
    intervention_tick: int
    pre_intervention: dict[str, float | int]
    scientific_warnings: tuple[str, ...]


def run_paired(
    simulation: Simulation,
    intervention: str,
    output_dir: str | Path,
    *,
    intervention_tick: int | None = None,
    shared_intervention: str | None = None,
    shared_intervention_tick: int | None = None,
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
    if shared_intervention is None and shared_intervention_tick is not None:
        raise ValueError("shared_intervention_tick requires shared_intervention")
    shared_tick = None
    if shared_intervention is not None:
        shared_tick = (
            simulation.tick
            if shared_intervention_tick is None
            else int(shared_intervention_tick)
        )
        if shared_tick < simulation.tick:
            raise ValueError(
                f"shared_intervention_tick {shared_tick} precedes current tick "
                f"{simulation.tick}"
            )
        if shared_tick > scheduled_tick:
            raise ValueError(
                "shared_intervention_tick cannot follow the branch intervention tick"
            )

    root = Path(output_dir)
    root.mkdir(parents=True, exist_ok=True)
    if shared_tick is not None:
        while simulation.tick < shared_tick:
            simulation.step()
        simulation.apply_intervention(shared_intervention)
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
    intervention_record = branch.intervention_history[-1]
    if intervention_record["type"] == "independent-foraging-override":
        baseline.register_autonomy_observation_cohort(
            branch.autonomy_recovery_cohort_ids,
            tick=scheduled_tick,
        )
        # Recompute the anchor so both branches expose the same would-be
        # treatment cohort before only the intervention branch is restored.
        pre_intervention = baseline.metric_row(
            pre_stats,
            0.0,
            window_seconds=0.0,
            window_ticks=0,
        )
    normalized_history = {
        str(record["type"]) for record in branch.intervention_history
    }
    scientific_warnings: list[str] = []
    if bool(intervention_record.get("direct_action_control", False)):
        scientific_warnings.append(
            "This entertainment intervention directly replaces carrier actions; "
            "its results are excluded from scientific baseline claims."
        )
    if (
        "independent-foraging-override" in normalized_history
        and "cut-social-connections" not in normalized_history
    ):
        scientific_warnings.append(
            "The independent-foraging entertainment override was not preceded by "
            "a social-connection cut; this is a module demo, not post-cut recovery."
        )
    if (
        "cut-social-connections" in normalized_history
        and not simulation.cfg.control.heuristic_social_guidance
    ):
        scientific_warnings.append(
            "Heuristic social guidance is disabled; the cut removes relations/messages "
            "but not an active high-level directional controller."
        )
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
        tuple(scientific_warnings),
    )
    (root / "counterfactual_summary.json").write_text(
        json.dumps(
            {
                "intervention": intervention,
                "intervention_record": intervention_record,
                "intervention_tick": scheduled_tick,
                "experiment_mode": simulation.experiment_mode.value,
                "shared_prehistory_ticks": scheduled_tick,
                "shared_intervention": shared_intervention,
                "shared_intervention_tick": shared_tick,
                "paired_randomness": True,
                "scientific_warnings": scientific_warnings,
                "baseline_scientific_validity": baseline.scientific_validity(),
                "intervention_scientific_validity": branch.scientific_validity(),
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
