"""Paired checkpoint interventions around observed local stress events.

Event selection is observational. Every baseline/intervention branch starts
from the same trusted checkpoint and uses keyed random streams. The module does
not add a controller or feed regional diagnostics back into the world.
"""

from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
import json
from pathlib import Path
from typing import Any, Iterable

import numpy as np

from .interventions import ExperimentMode, resolve_intervention
from .long_run_analysis import load_progress
from .phase_counterfactual import discover_checkpoints
from .simulation import Simulation


DEFAULT_INTERVENTIONS = (
    "neutralize-danger-evidence",
    "disable-knowledge-transfer",
    "disable-knowledge-policy",
    "ablate-working-memory",
    "bypass-sparse-selection",
)
EVENT_FIELDS = {
    "scarcity": "spatial_local_region_resource_scarcity",
    "mortality": "spatial_local_region_mortality_pressure",
    "crowding": "spatial_local_region_crowding",
}


@dataclass(frozen=True)
class LocalStressEvent:
    event_id: str
    event_kind: str
    region_id: int
    event_tick: int
    checkpoint_tick: int
    checkpoint_path: str
    event_value: float
    region_quantile: float
    standardized_score: float
    alive_region: int
    cohesion_region: float
    knowledge_transfer_committed_total: int
    disable_transfer_identifiable: bool


@dataclass(frozen=True)
class LocalEventPlan:
    schema: str
    run_dir: str
    progress_path: str
    event_kind: str
    event_quantile: float
    horizon_ticks: int
    events: tuple[LocalStressEvent, ...]
    interventions: tuple[str, ...]
    paired_randomness: bool = True
    observational_event_selection: bool = True


def _prior_checkpoint(target_tick: int, checkpoints: dict[int, Path]) -> tuple[int, Path]:
    eligible = [(tick, path) for tick, path in checkpoints.items() if tick < target_tick]
    if not eligible:
        raise ValueError(f"no checkpoint exists before local event tick {target_tick}")
    return max(eligible, key=lambda item: item[0])


def detect_local_events(
    records: list[dict[str, Any]],
    *,
    event_kind: str = "scarcity",
    quantile: float = 0.85,
    max_events: int = 4,
    min_tick: int | None = None,
    min_gap_windows: int = 2,
) -> list[tuple[int, int, float, float, float]]:
    """Return ``(record_index, region, value, threshold, zscore)`` events."""
    if event_kind not in EVENT_FIELDS:
        raise ValueError(f"unknown local event kind {event_kind!r}")
    if not 0.5 <= quantile < 1.0:
        raise ValueError("local event quantile must be in [0.5, 1.0)")
    if max_events <= 0:
        raise ValueError("max_events must be positive")
    field = EVENT_FIELDS[event_kind]
    usable = [record for record in records if record.get(field) is not None]
    if len(usable) < 5:
        raise ValueError("local event detection requires at least five spatial windows")
    ticks = np.asarray([int(record["tick"]) for record in usable], dtype=np.int64)
    values = np.asarray([record[field] for record in usable], dtype=np.float64)
    if values.ndim != 2:
        raise ValueError(f"{field} must be a window×region array")
    cohesion_rows = [record.get("spatial_local_region_cohesion_valid") for record in usable]
    cohesion_valid = (
        np.asarray(cohesion_rows, dtype=bool)
        if all(value is not None for value in cohesion_rows)
        else np.ones_like(values, dtype=bool)
    )
    alive_rows = [record.get("spatial_local_region_alive") for record in usable]
    alive_valid = (
        np.asarray(alive_rows, dtype=np.float64) >= 5.0
        if all(value is not None for value in alive_rows)
        else np.ones_like(values, dtype=bool)
    )
    cutoff = int(min_tick) if min_tick is not None else int(ticks[0])
    candidates: list[tuple[int, int, float, float, float]] = []
    for region in range(values.shape[1]):
        series = values[:, region]
        valid = np.isfinite(series) & (ticks >= cutoff) & cohesion_valid[:, region] & alive_valid[:, region]
        sample = series[valid]
        if sample.size < 5 or float(np.std(sample)) == 0.0:
            continue
        threshold = float(np.quantile(sample, quantile))
        mean = float(np.mean(sample))
        std = float(np.std(sample))
        last = -10**9
        for index in range(1, values.shape[0] - 1):
            if not valid[index] or index - last < min_gap_windows:
                continue
            value = float(series[index])
            if (
                value >= threshold
                and value >= float(series[index - 1])
                and value > float(series[index + 1])
            ):
                candidates.append(
                    (index, region, value, threshold, (value - mean) / std)
                )
                last = index
    candidates.sort(key=lambda item: (-item[4], int(ticks[item[0]]), item[1]))
    selected: list[tuple[int, int, float, float, float]] = []
    used_regions: set[int] = set()
    for item in candidates:
        if item[1] in used_regions and len(used_regions) < values.shape[1]:
            continue
        selected.append(item)
        used_regions.add(item[1])
        if len(selected) >= max_events:
            break
    if not selected:
        raise ValueError("no local stress event crossed the configured quantile")
    return selected


def build_local_event_plan(
    run_dir: str | Path,
    *,
    event_kind: str = "scarcity",
    quantile: float = 0.85,
    max_events: int = 4,
    horizon_ticks: int = 120,
    min_tick: int | None = None,
    interventions: Iterable[str] = DEFAULT_INTERVENTIONS,
) -> LocalEventPlan:
    root = Path(run_dir)
    progress_path = root / "evolution_progress.jsonl"
    records = load_progress(progress_path)
    checkpoints = discover_checkpoints(root)
    normalized: list[str] = []
    for name in interventions:
        spec = resolve_intervention(name)
        spec.require_mode(ExperimentMode.SCIENTIFIC)
        if spec.name not in normalized:
            normalized.append(spec.name)
    events = detect_local_events(
        records,
        event_kind=event_kind,
        quantile=quantile,
        max_events=max_events,
        min_tick=min_tick,
    )
    usable = [record for record in records if record.get(EVENT_FIELDS[event_kind]) is not None]
    payload: list[LocalStressEvent] = []
    for index, region, value, threshold, score in events:
        record = usable[index]
        event_tick = int(record["tick"])
        checkpoint_tick, checkpoint_path = _prior_checkpoint(event_tick, checkpoints)
        region_alive = int(record["spatial_local_region_alive"][region])
        cohesion_values = record.get("spatial_local_region_boundary_cohesion", [])
        cohesion = (
            float(cohesion_values[region])
            if region < len(cohesion_values)
            else 0.0
        )
        checkpoint_record = min(
            records, key=lambda item: abs(int(item["tick"]) - checkpoint_tick)
        )
        prior_commits = int(
            checkpoint_record.get("knowledge_transfer_committed_total", 0)
        )
        payload.append(
            LocalStressEvent(
                event_id=f"{event_kind}-r{region}-t{event_tick}",
                event_kind=event_kind,
                region_id=int(region),
                event_tick=event_tick,
                checkpoint_tick=int(checkpoint_tick),
                checkpoint_path=str(checkpoint_path),
                event_value=float(value),
                region_quantile=float(threshold),
                standardized_score=float(score),
                alive_region=region_alive,
                cohesion_region=cohesion,
                knowledge_transfer_committed_total=prior_commits,
                disable_transfer_identifiable=prior_commits > 0,
            )
        )
    return LocalEventPlan(
        schema="local-stress-event-counterfactual-plan-v1",
        run_dir=str(root),
        progress_path=str(progress_path),
        event_kind=event_kind,
        event_quantile=float(quantile),
        horizon_ticks=int(horizon_ticks),
        events=tuple(payload),
        interventions=tuple(normalized),
    )


def _run_branch(
    checkpoint: str | Path,
    output_dir: Path,
    *,
    until_tick: int,
    backend: str,
    gpu_semantics_mode: str | None,
    intervention: str | None,
    common_boundary_audit: bool = False,
    cohort_requests: list[dict[str, Any]] | tuple[dict[str, Any], ...] | None = None,
) -> dict[str, Any]:
    simulation = Simulation.from_checkpoint(
        checkpoint,
        output_dir,
        backend=backend,
        until_tick=until_tick,
        gpu_semantics_mode=gpu_semantics_mode,
    )
    if common_boundary_audit:
        simulation.freeze_local_reference_boundary()
    if cohort_requests:
        simulation.configure_event_cohort_diagnostics(cohort_requests)
    if intervention is not None:
        simulation.apply_intervention(intervention)
    world = simulation.run(until_tick=until_tick)
    return {
        "world": world,
        "records": simulation.evolution_progress.records,
        "scientific_validity": simulation.scientific_validity(),
        "intervention_history": simulation.intervention_history,
        "common_boundary_audit": bool(common_boundary_audit),
        "event_cohort_summaries": simulation.event_cohort_summaries(),
    }


def _region_summary(
    records: list[dict[str, Any]],
    *,
    region: int,
    event_tick: int,
) -> dict[str, float | int | None]:
    usable = [record for record in records if int(record.get("tick", 0)) >= event_tick]
    if not usable:
        return {}
    final = usable[-1]

    def region_value(record: dict[str, Any], key: str) -> float | None:
        values = record.get(key)
        if not isinstance(values, list) or region >= len(values):
            return None
        value = values[region]
        return float(value) if isinstance(value, (int, float)) else None

    current_internal = sum(
        region_value(record, "spatial_local_region_benefit_internal") or 0.0
        for record in usable
    )
    current_cross = sum(
        region_value(record, "spatial_local_region_benefit_cross_boundary") or 0.0
        for record in usable
    )
    reference_internal = sum(
        region_value(record, "spatial_local_region_reference_benefit_internal") or 0.0
        for record in usable
    )
    reference_cross = sum(
        region_value(record, "spatial_local_region_reference_benefit_cross_boundary") or 0.0
        for record in usable
    )
    current_boundary = current_internal + current_cross
    reference_boundary = reference_internal + reference_cross

    return {
        "final_tick": int(final["tick"]),
        "reference_boundary_available": bool(
            final.get("spatial_local_reference_boundary_schema")
        ),
        "reference_boundary_snapshot_tick": (
            int(final["spatial_local_reference_boundary_snapshot_tick"])
            if final.get("spatial_local_reference_boundary_schema")
            else None
        ),
        "final_alive_region": region_value(final, "spatial_local_region_alive"),
        "final_cohesion_region": region_value(
            final, "spatial_local_region_boundary_cohesion"
        ),
        "final_reference_cohesion_region": region_value(
            final, "spatial_local_region_reference_boundary_cohesion"
        ),
        "final_boundary_definition_gap_region": region_value(
            final, "spatial_local_region_boundary_definition_gap"
        ),
        "post_event_cohesion_region": (
            current_internal / current_boundary if current_boundary > 0.0 else None
        ),
        "post_event_reference_cohesion_region": (
            reference_internal / reference_boundary
            if reference_boundary > 0.0
            else None
        ),
        "post_event_boundary_definition_gap_region": (
            current_internal / current_boundary
            - reference_internal / reference_boundary
            if current_boundary > 0.0 and reference_boundary > 0.0
            else None
        ),
        "post_event_benefit_internal_region": current_internal,
        "post_event_benefit_cross_boundary_region": current_cross,
        "post_event_reference_benefit_internal_region": reference_internal,
        "post_event_reference_benefit_cross_boundary_region": reference_cross,
        "final_scarcity_region": region_value(
            final, "spatial_local_region_resource_scarcity"
        ),
        "final_mortality_region": region_value(
            final, "spatial_local_region_mortality_pressure"
        ),
        "final_active_transferred_roots_region": region_value(
            final, "spatial_local_region_active_transferred_roots"
        ),
        "post_event_outgoing_commits": int(sum(
            int(record.get("spatial_local_region_transfer_committed_outgoing", [0] * (region + 1))[region])
            for record in usable
            if len(record.get("spatial_local_region_transfer_committed_outgoing", [])) > region
        )),
        "post_event_incoming_commits": int(sum(
            int(record.get("spatial_local_region_transfer_committed_incoming", [0] * (region + 1))[region])
            for record in usable
            if len(record.get("spatial_local_region_transfer_committed_incoming", [])) > region
        )),
        "post_event_new_transferred_roots": int(sum(
            int(record.get("spatial_local_region_new_transferred_roots", [0] * (region + 1))[region])
            for record in usable
            if len(record.get("spatial_local_region_new_transferred_roots", [])) > region
        )),
        "post_event_lost_transferred_roots": int(sum(
            int(record.get("spatial_local_region_lost_transferred_roots", [0] * (region + 1))[region])
            for record in usable
            if len(record.get("spatial_local_region_lost_transferred_roots", [])) > region
        )),
    }


def _numeric_delta(branch: dict[str, Any], baseline: dict[str, Any]) -> dict[str, float]:
    result: dict[str, float] = {}
    for key in sorted(set(branch) & set(baseline)):
        left = branch[key]
        right = baseline[key]
        if isinstance(left, (int, float)) and isinstance(right, (int, float)):
            result[key] = float(left) - float(right)
    return result


def execute_local_event_plan(
    plan: LocalEventPlan,
    output_dir: str | Path,
    *,
    backend: str = "cpu",
    gpu_semantics_mode: str | None = None,
) -> dict[str, Any]:
    root = Path(output_dir)
    root.mkdir(parents=True, exist_ok=True)
    event_results: list[dict[str, Any]] = []
    for event in plan.events:
        event_dir = root / event.event_id
        until_tick = event.event_tick + plan.horizon_ticks
        baseline = _run_branch(
            event.checkpoint_path,
            event_dir / "baseline",
            until_tick=until_tick,
            backend=backend,
            gpu_semantics_mode=gpu_semantics_mode,
            intervention=None,
        )
        baseline_region = _region_summary(
            baseline["records"], region=event.region_id, event_tick=event.event_tick
        )
        branches: list[dict[str, Any]] = []
        for intervention in plan.interventions:
            if (
                intervention == "disable-knowledge-transfer"
                and not event.disable_transfer_identifiable
            ):
                branches.append(
                    {
                        "intervention": intervention,
                        "identifiable": False,
                        "reason": "no successful transfer existed before the event checkpoint",
                        "region_summary": {},
                        "delta": {},
                    }
                )
                continue
            branch = _run_branch(
                event.checkpoint_path,
                event_dir / intervention,
                until_tick=until_tick,
                backend=backend,
                gpu_semantics_mode=gpu_semantics_mode,
                intervention=intervention,
            )
            branch_region = _region_summary(
                branch["records"], region=event.region_id, event_tick=event.event_tick
            )
            branches.append(
                {
                    "intervention": intervention,
                    "identifiable": True,
                    "reason": None,
                    "region_summary": branch_region,
                    "delta": _numeric_delta(branch_region, baseline_region),
                }
            )
        event_results.append(
            {
                "event": asdict(event),
                "until_tick": until_tick,
                "baseline_region_summary": baseline_region,
                "interventions": branches,
            }
        )
    report = {
        "schema": "local-stress-event-counterfactual-results-v1",
        "plan": asdict(plan),
        "backend": backend,
        "gpu_semantics_mode": gpu_semantics_mode,
        "paired_randomness": True,
        "event_results": event_results,
        "interpretation_boundary": (
            "Branches estimate effects local to selected observed events and horizons. "
            "Event selection itself remains observational and may condition on shared causes."
        ),
    }
    (root / "local_event_counterfactual_results.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (root / "local_event_counterfactual_results.md").write_text(
        render_results_markdown(report), encoding="utf-8"
    )
    return report


def render_plan_markdown(plan: LocalEventPlan) -> str:
    lines = [
        "# Local stress event counterfactual plan",
        "",
        f"Schema: `{plan.schema}`",
        f"Event kind / quantile: **{plan.event_kind} / {plan.event_quantile:.2f}**",
        f"Post-event horizon: **{plan.horizon_ticks} ticks**",
        "",
        "> Events are selected observationally from within-region stress peaks.",
        "",
        "| Event | Region | Tick | Checkpoint | Value | Region threshold | z-score | Alive | Cohesion | Transfer-off identifiable |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---|",
    ]
    for event in plan.events:
        lines.append(
            f"| {event.event_id} | {event.region_id} | {event.event_tick} | "
            f"{event.checkpoint_tick} | {event.event_value:.5f} | "
            f"{event.region_quantile:.5f} | {event.standardized_score:.3f} | "
            f"{event.alive_region} | {event.cohesion_region:.4f} | "
            f"{event.disable_transfer_identifiable} |"
        )
    lines.extend(["", "## Interventions", ""])
    lines.extend(f"- `{name}`" for name in plan.interventions)
    return "\n".join(lines) + "\n"


def render_results_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Local stress event counterfactual results",
        "",
        "> All branches start from paired checkpoints and retain keyed randomness.",
        "",
        "| Event | Intervention | Δ regional alive | Δ cohesion | Δ incoming commits | Δ outgoing commits | Δ active culture roots |",
        "|---|---|---:|---:|---:|---:|---:|",
    ]
    keys = (
        "final_alive_region",
        "final_cohesion_region",
        "post_event_incoming_commits",
        "post_event_outgoing_commits",
        "final_active_transferred_roots_region",
    )
    for item in report["event_results"]:
        for branch in item["interventions"]:
            if not branch["identifiable"]:
                lines.append(
                    f"| {item['event']['event_id']} | {branch['intervention']} | not identifiable | — | — | — | — |"
                )
                continue
            values = [branch["delta"].get(key) for key in keys]
            formatted = ["—" if value is None else f"{value:+.5f}" for value in values]
            lines.append(
                f"| {item['event']['event_id']} | {branch['intervention']} | "
                + " | ".join(formatted)
                + " |"
            )
    lines.extend(["", "## Interpretation boundary", "", report["interpretation_boundary"], ""])
    return "\n".join(lines)


def _parse_interventions(value: str) -> tuple[str, ...]:
    result = tuple(item.strip() for item in value.split(",") if item.strip())
    if not result:
        raise ValueError("at least one intervention is required")
    return result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Plan or execute paired interventions around local stress events"
    )
    parser.add_argument("--run-dir", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--event-kind", choices=tuple(EVENT_FIELDS), default="scarcity")
    parser.add_argument("--event-quantile", type=float, default=0.85)
    parser.add_argument("--max-events", type=int, default=4)
    parser.add_argument("--horizon", type=int, default=120)
    parser.add_argument("--min-tick", type=int)
    parser.add_argument("--interventions", default=",".join(DEFAULT_INTERVENTIONS))
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
    plan = build_local_event_plan(
        args.run_dir,
        event_kind=args.event_kind,
        quantile=args.event_quantile,
        max_events=args.max_events,
        horizon_ticks=args.horizon,
        min_tick=args.min_tick,
        interventions=_parse_interventions(args.interventions),
    )
    (output / "local_event_counterfactual_plan.json").write_text(
        json.dumps(asdict(plan), ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (output / "local_event_counterfactual_plan.md").write_text(
        render_plan_markdown(plan), encoding="utf-8"
    )
    if args.execute:
        execute_local_event_plan(
            plan,
            output,
            backend=args.backend,
            gpu_semantics_mode=args.gpu_semantics_mode,
        )


if __name__ == "__main__":
    main()
