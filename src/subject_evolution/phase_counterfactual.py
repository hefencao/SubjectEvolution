"""Phase-aware paired checkpoint interventions for long-run experiments.

The planner selects one complete population cycle from an observational
``evolution_progress.jsonl`` stream and maps rise/peak/decline/trough states to
trusted full-world checkpoints.  Execution branches every intervention from
exactly the same checkpoint as its baseline, preserving keyed random streams.
"""

from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
import json
from pathlib import Path
import re
from typing import Any, Iterable

import numpy as np

from .interventions import ExperimentMode, intervention_names, resolve_intervention
from .long_run_analysis import load_progress
from .simulation import Simulation


CHECKPOINT_RE = re.compile(r"checkpoint_(\d{8})\.sechk$")
DEFAULT_INTERVENTIONS = (
    "neutralize-resource-affinity",
    "ablate-working-memory",
    "bypass-sparse-selection",
    "disable-knowledge-policy",
    "disable-knowledge-transfer",
)
PHASES = ("rise", "peak", "decline", "trough")


@dataclass(frozen=True)
class PhaseCheckpoint:
    phase: str
    target_tick: int
    checkpoint_tick: int
    checkpoint_path: str
    alive: int
    births_window: int
    deaths_window: int
    net_growth_window: int
    mortality_pressure_window: float


@dataclass(frozen=True)
class PhasePlan:
    schema: str
    run_dir: str
    progress_path: str
    horizon_ticks: int
    min_phase_tick: int
    phases: tuple[PhaseCheckpoint, ...]
    interventions: tuple[str, ...]
    complete_cycle_detected: bool
    phase_selection_warning: str | None
    paired_randomness: bool = True
    observational_phase_selection: bool = True


def _moving_average(values: np.ndarray, width: int = 3) -> np.ndarray:
    if values.size < width:
        return values.astype(np.float64, copy=True)
    pad = width // 2
    padded = np.pad(values.astype(np.float64), (pad, pad), mode="edge")
    return np.convolve(padded, np.ones(width) / width, mode="valid")


def _local_extrema(values: np.ndarray) -> tuple[list[int], list[int]]:
    peaks: list[int] = []
    troughs: list[int] = []
    for index in range(1, values.size - 1):
        left, current, right = values[index - 1 : index + 2]
        if current >= left and current > right:
            peaks.append(index)
        if current <= left and current < right:
            troughs.append(index)
    return peaks, troughs


def detect_phase_targets(
    records: list[dict[str, Any]],
    *,
    min_phase_tick: int | None = None,
) -> dict[str, int]:
    """Select rise/peak/decline/trough ticks from the latest complete cycle.

    Phase selection is observational and never feeds back into the world.  A
    three-window moving average avoids choosing a one-window population spike.
    When no complete local cycle exists, a deterministic global fallback is
    used after the warm-up cutoff.
    """

    targets, _, _ = _detect_phase_targets_with_metadata(
        records, min_phase_tick=min_phase_tick
    )
    return targets


def _detect_phase_targets_with_metadata(
    records: list[dict[str, Any]],
    *,
    min_phase_tick: int | None = None,
) -> tuple[dict[str, int], bool, str | None]:
    if len(records) < 4:
        raise ValueError("phase detection requires at least four progress records")
    ordered = sorted(records, key=lambda item: int(item["tick"]))
    ticks = np.asarray([int(item["tick"]) for item in ordered], dtype=np.int64)
    alive = np.asarray([int(item.get("alive", 0)) for item in ordered], dtype=np.float64)
    births = np.asarray(
        [int(item.get("births_window", item.get("births_step", 0))) for item in ordered],
        dtype=np.float64,
    )
    deaths = np.asarray(
        [int(item.get("deaths_window", item.get("deaths_step", 0))) for item in ordered],
        dtype=np.float64,
    )
    net = births - deaths
    cutoff = (
        int(min_phase_tick)
        if min_phase_tick is not None
        else max(int(ticks[0]), int(round(float(ticks[-1]) * 0.20)))
    )
    eligible = np.flatnonzero(ticks >= cutoff)
    if eligible.size < 4:
        raise ValueError("warm-up cutoff leaves fewer than four progress records")
    start = int(eligible[0])
    smoothed = _moving_average(alive)
    peaks, troughs = _local_extrema(smoothed)
    peaks = [index for index in peaks if index >= start]
    troughs = [index for index in troughs if index >= start]

    selected: tuple[int, int, int] | None = None
    # Prefer the latest peak followed by a trough and preceded by a trough.
    for peak in reversed(peaks):
        prior = [index for index in troughs if start <= index < peak]
        following = [index for index in troughs if index > peak]
        if prior and following:
            selected = (prior[-1], peak, following[0])
            break

    complete_cycle = selected is not None
    warning = None
    if selected is None:
        warning = (
            "No complete trough→peak→trough population cycle was detected after "
            "the warm-up cutoff. Fallback labels are descriptive only and should "
            "not be used for phase-specific scientific claims."
        )
        peak = start + int(np.argmax(smoothed[start:]))
        following = np.arange(peak + 1, ticks.size, dtype=np.int64)
        if following.size:
            trough = int(following[int(np.argmin(smoothed[following]))])
        else:
            trough = int(ticks.size - 1)
        prior = np.arange(start, max(peak, start + 1), dtype=np.int64)
        prior_trough = int(prior[int(np.argmin(smoothed[prior]))])
    else:
        prior_trough, peak, trough = selected

    rise_range = np.arange(prior_trough, peak + 1, dtype=np.int64)
    decline_range = np.arange(peak, trough + 1, dtype=np.int64)
    rise = int(rise_range[int(np.argmax(net[rise_range]))])
    decline = int(decline_range[int(np.argmin(net[decline_range]))])
    return ({
        "rise": int(ticks[rise]),
        "peak": int(ticks[peak]),
        "decline": int(ticks[decline]),
        "trough": int(ticks[trough]),
    }, complete_cycle, warning)


def discover_checkpoints(run_dir: str | Path) -> dict[int, Path]:
    root = Path(run_dir)
    found: dict[int, Path] = {}
    for path in sorted(root.glob("checkpoint_*.sechk")):
        match = CHECKPOINT_RE.search(path.name)
        if match:
            found[int(match.group(1))] = path
    if not found:
        raise FileNotFoundError(f"no full .sechk checkpoints found under {root}")
    return found


def _nearest_unique_checkpoint(
    target_tick: int,
    checkpoints: dict[int, Path],
    used: set[int],
) -> tuple[int, Path]:
    candidates = sorted(
        checkpoints.items(),
        key=lambda item: (
            abs(item[0] - target_tick),
            item[0] > target_tick,
            item[0],
        ),
    )
    for tick, path in candidates:
        if tick not in used:
            used.add(tick)
            return tick, path
    tick, path = candidates[0]
    return tick, path


def build_phase_plan(
    run_dir: str | Path,
    *,
    horizon_ticks: int,
    interventions: Iterable[str] = DEFAULT_INTERVENTIONS,
    min_phase_tick: int | None = None,
    allow_incomplete_cycle: bool = False,
) -> PhasePlan:
    root = Path(run_dir)
    progress_path = root / "evolution_progress.jsonl"
    records = load_progress(progress_path)
    targets, complete_cycle, warning = _detect_phase_targets_with_metadata(
        records, min_phase_tick=min_phase_tick
    )
    if not complete_cycle and not allow_incomplete_cycle:
        raise ValueError(
            "no complete ecological cycle was detected; rerun with a longer source "
            "trajectory or explicitly set allow_incomplete_cycle=True for a smoke test"
        )
    checkpoints = discover_checkpoints(root)
    normalized_interventions: list[str] = []
    for name in interventions:
        spec = resolve_intervention(name)
        spec.require_mode(ExperimentMode.SCIENTIFIC)
        if spec.name not in normalized_interventions:
            normalized_interventions.append(spec.name)
    record_by_tick = {int(record["tick"]): record for record in records}
    used: set[int] = set()
    phases: list[PhaseCheckpoint] = []
    for phase in PHASES:
        target = targets[phase]
        checkpoint_tick, checkpoint_path = _nearest_unique_checkpoint(
            target, checkpoints, used
        )
        nearest_record = min(
            records, key=lambda record: abs(int(record["tick"]) - checkpoint_tick)
        )
        births = int(nearest_record.get("births_window", 0))
        deaths = int(nearest_record.get("deaths_window", 0))
        mortality = float(
            nearest_record.get(
                "mortality_pressure_window",
                deaths / max(int(nearest_record.get("alive", 0)) + deaths, 1),
            )
        )
        phases.append(
            PhaseCheckpoint(
                phase=phase,
                target_tick=target,
                checkpoint_tick=checkpoint_tick,
                checkpoint_path=str(checkpoint_path),
                alive=int(nearest_record.get("alive", 0)),
                births_window=births,
                deaths_window=deaths,
                net_growth_window=births - deaths,
                mortality_pressure_window=mortality,
            )
        )
    cutoff = (
        int(min_phase_tick)
        if min_phase_tick is not None
        else max(int(records[0]["tick"]), int(round(int(records[-1]["tick"]) * 0.20)))
    )
    return PhasePlan(
        schema="phase-checkpoint-counterfactual-plan-v1",
        run_dir=str(root),
        progress_path=str(progress_path),
        horizon_ticks=int(horizon_ticks),
        min_phase_tick=cutoff,
        phases=tuple(phases),
        interventions=tuple(normalized_interventions),
        complete_cycle_detected=complete_cycle,
        phase_selection_warning=warning,
    )


def render_plan_markdown(plan: PhasePlan) -> str:
    lines = [
        "# Phase checkpoint counterfactual plan",
        "",
        f"Schema: `{plan.schema}`",
        f"Post-intervention horizon: **{plan.horizon_ticks} ticks**",
        f"Complete ecological cycle detected: **{plan.complete_cycle_detected}**",
        "",
        "> Phase labels are selected from observational population dynamics. They are not causal claims.",
        "",
    ]
    if plan.phase_selection_warning:
        lines.extend([f"> Warning: {plan.phase_selection_warning}", ""])
    lines.extend(
        [
            "| Phase | Target tick | Checkpoint | Alive | Births | Deaths | Net growth | Mortality pressure |",
            "|---|---:|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for item in plan.phases:
        lines.append(
            f"| {item.phase} | {item.target_tick} | {item.checkpoint_tick} | "
            f"{item.alive} | {item.births_window} | {item.deaths_window} | "
            f"{item.net_growth_window} | {item.mortality_pressure_window:.4f} |"
        )
    lines.extend(["", "## Scientific interventions", ""])
    lines.extend(f"- `{name}`" for name in plan.interventions)
    lines.extend(
        [
            "",
            "Every branch starts from the same trusted checkpoint as its phase baseline and retains keyed random streams.",
            "",
        ]
    )
    return "\n".join(lines)


def _flatten_numeric(prefix: str, values: dict[str, Any]) -> dict[str, float]:
    return {
        f"{prefix}.{key}": float(value)
        for key, value in values.items()
        if isinstance(value, (int, float)) and not isinstance(value, bool)
    }


def _run_branch(
    checkpoint: str | Path,
    output_dir: Path,
    *,
    until_tick: int,
    backend: str,
    gpu_semantics_mode: str | None,
    intervention: str | None,
) -> dict[str, Any]:
    simulation = Simulation.from_checkpoint(
        checkpoint,
        output_dir,
        backend=backend,
        until_tick=until_tick,
        gpu_semantics_mode=gpu_semantics_mode,
    )
    if intervention is not None:
        simulation.apply_intervention(intervention)
    world = simulation.run(until_tick=until_tick)
    evolution = (
        simulation.evolution_progress.records[-1]
        if simulation.evolution_progress.records
        else {}
    )
    return {
        "world": world,
        "evolution": evolution,
        "scientific_validity": simulation.scientific_validity(),
        "intervention_history": simulation.intervention_history,
    }


def execute_phase_plan(
    plan: PhasePlan,
    output_dir: str | Path,
    *,
    backend: str = "cpu",
    gpu_semantics_mode: str | None = None,
) -> dict[str, Any]:
    root = Path(output_dir)
    root.mkdir(parents=True, exist_ok=True)
    phase_results: list[dict[str, Any]] = []
    for phase in plan.phases:
        phase_dir = root / phase.phase
        until_tick = phase.checkpoint_tick + plan.horizon_ticks
        baseline = _run_branch(
            phase.checkpoint_path,
            phase_dir / "baseline",
            until_tick=until_tick,
            backend=backend,
            gpu_semantics_mode=gpu_semantics_mode,
            intervention=None,
        )
        baseline_numeric = {
            **_flatten_numeric("world", baseline["world"]),
            **_flatten_numeric("evolution", baseline["evolution"]),
        }
        interventions_payload: list[dict[str, Any]] = []
        for intervention in plan.interventions:
            branch = _run_branch(
                phase.checkpoint_path,
                phase_dir / intervention,
                until_tick=until_tick,
                backend=backend,
                gpu_semantics_mode=gpu_semantics_mode,
                intervention=intervention,
            )
            branch_numeric = {
                **_flatten_numeric("world", branch["world"]),
                **_flatten_numeric("evolution", branch["evolution"]),
            }
            common = sorted(set(baseline_numeric) & set(branch_numeric))
            delta = {
                key: branch_numeric[key] - baseline_numeric[key] for key in common
            }
            interventions_payload.append(
                {"intervention": intervention, "result": branch, "delta": delta}
            )
        phase_results.append(
            {
                "phase": asdict(phase),
                "until_tick": until_tick,
                "baseline": baseline,
                "interventions": interventions_payload,
            }
        )
    report = {
        "schema": "phase-checkpoint-counterfactual-results-v1",
        "plan": asdict(plan),
        "backend": backend,
        "gpu_semantics_mode": gpu_semantics_mode,
        "paired_randomness": True,
        "phase_results": phase_results,
        "interpretation_boundary": (
            "Each intervention estimates a local phase-specific effect over the "
            "configured horizon. It does not prove necessity across all seeds or phases."
        ),
    }
    (root / "phase_counterfactual_results.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (root / "phase_counterfactual_results.md").write_text(
        render_results_markdown(report), encoding="utf-8"
    )
    return report


def render_results_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Phase checkpoint counterfactual results",
        "",
        "> All branches use paired keyed randomness. Effects remain local to the selected checkpoint phase and horizon.",
        "",
        "| Phase | Intervention | Δ Alive | Δ Effective lineages | Δ Strategy dims | Δ Action entropy | Δ Cohesion |",
        "|---|---|---:|---:|---:|---:|---:|",
    ]
    keys = (
        "world.alive",
        "evolution.effective_lineages",
        "evolution.strategy_effective_dimensions",
        "evolution.window_action_entropy",
        "evolution.benefit_boundary_cohesion",
    )
    for phase in report["phase_results"]:
        for branch in phase["interventions"]:
            delta = branch["delta"]
            values = [delta.get(key) for key in keys]
            formatted = ["—" if value is None else f"{value:+.5f}" for value in values]
            lines.append(
                f"| {phase['phase']['phase']} | {branch['intervention']} | "
                + " | ".join(formatted)
                + " |"
            )
    lines.extend(["", "## Interpretation boundary", "", report["interpretation_boundary"], ""])
    return "\n".join(lines)


def _parse_interventions(value: str) -> tuple[str, ...]:
    values = tuple(item.strip() for item in value.split(",") if item.strip())
    if not values:
        raise ValueError("at least one intervention is required")
    return values


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Plan or execute phase-aware paired checkpoint interventions"
    )
    parser.add_argument("--run-dir", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--horizon", type=int, default=120)
    parser.add_argument("--min-phase-tick", type=int)
    parser.add_argument(
        "--interventions",
        default=",".join(DEFAULT_INTERVENTIONS),
        help="Comma-separated scientific intervention names",
    )
    parser.add_argument("--execute", action="store_true")
    parser.add_argument(
        "--allow-incomplete-cycle",
        action="store_true",
        help="Allow descriptive fallback phases for smoke testing only.",
    )
    parser.add_argument("--backend", choices=("cpu", "gpu", "auto"), default="cpu")
    parser.add_argument(
        "--gpu-semantics-mode",
        choices=("strict-reference", "hybrid-accelerated"),
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    if args.horizon <= 0:
        raise ValueError("horizon must be positive")
    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=True)
    plan = build_phase_plan(
        args.run_dir,
        horizon_ticks=args.horizon,
        interventions=_parse_interventions(args.interventions),
        min_phase_tick=args.min_phase_tick,
        allow_incomplete_cycle=args.allow_incomplete_cycle,
    )
    (output / "phase_counterfactual_plan.json").write_text(
        json.dumps(asdict(plan), ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (output / "phase_counterfactual_plan.md").write_text(
        render_plan_markdown(plan), encoding="utf-8"
    )
    if args.execute:
        execute_phase_plan(
            plan,
            output,
            backend=args.backend,
            gpu_semantics_mode=args.gpu_semantics_mode,
        )


if __name__ == "__main__":
    main()
