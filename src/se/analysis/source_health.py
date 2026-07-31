"""Precondition gate for demographic and generational source viability.

This is intentionally an execution gate, not a post-hoc scientific audit.  It
prevents a study from creating counterfactual branches from a source that has
already collapsed into a small-founder bottleneck.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any

import numpy as np

PROTOCOL_SCHEMA = "source-health-contract-v1"
REPORT_SCHEMA = "source-health-gate-report-v1"


@dataclass(frozen=True)
class HealthCheckpoint:
    tick: int
    minimum_alive_count: int
    minimum_alive_fraction_to_initial: float
    minimum_cumulative_births_per_initial: float
    minimum_living_descendants_per_initial: float
    minimum_mean_generation: float
    maximum_founder_alive_fraction: float
    maximum_alive_decline_fraction_from_previous_checkpoint: float = 1.0

    def validate(self) -> None:
        if self.tick < 1:
            raise ValueError("health checkpoint tick must be positive")
        if self.minimum_alive_count < 1:
            raise ValueError("minimum alive count must be positive")
        for name, value in (
            ("minimum_alive_fraction_to_initial", self.minimum_alive_fraction_to_initial),
            ("minimum_cumulative_births_per_initial", self.minimum_cumulative_births_per_initial),
            ("minimum_living_descendants_per_initial", self.minimum_living_descendants_per_initial),
            ("minimum_mean_generation", self.minimum_mean_generation),
        ):
            if value < 0.0:
                raise ValueError(f"{name} cannot be negative")
        if not 0.0 <= self.maximum_founder_alive_fraction <= 1.0:
            raise ValueError("maximum founder fraction must be in [0, 1]")
        if not 0.0 <= self.maximum_alive_decline_fraction_from_previous_checkpoint <= 1.0:
            raise ValueError("maximum checkpoint decline fraction must be in [0, 1]")


@dataclass(frozen=True)
class SourceHealthContract:
    schema: str
    purpose: str
    checkpoints: tuple[HealthCheckpoint, ...]
    required_ready_seed_count: int
    stop_panel_after_failed_seed_count: int
    paired_plan_authorized_only_when_ready: bool = True

    def validate(self) -> None:
        if self.schema != PROTOCOL_SCHEMA:
            raise ValueError(f"unsupported source health schema: {self.schema!r}")
        if not self.checkpoints:
            raise ValueError("source health contract requires checkpoints")
        for checkpoint in self.checkpoints:
            checkpoint.validate()
        ticks = [item.tick for item in self.checkpoints]
        if ticks != sorted(set(ticks)):
            raise ValueError("source health checkpoints must have unique increasing ticks")
        if self.required_ready_seed_count < 1:
            raise ValueError("required ready seed count must be positive")
        if self.stop_panel_after_failed_seed_count < 1:
            raise ValueError("failed-seed panel stop count must be positive")

    @property
    def final_checkpoint(self) -> HealthCheckpoint:
        return self.checkpoints[-1]


def load_contract(path: str | Path) -> SourceHealthContract:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    checkpoints = tuple(HealthCheckpoint(**item) for item in payload.get("checkpoints", ()))
    contract = SourceHealthContract(
        schema=str(payload.get("schema", "")),
        purpose=str(payload.get("purpose", "")),
        checkpoints=checkpoints,
        required_ready_seed_count=int(payload.get("required_ready_seed_count", 1)),
        stop_panel_after_failed_seed_count=int(
            payload.get("stop_panel_after_failed_seed_count", 1)
        ),
        paired_plan_authorized_only_when_ready=bool(
            payload.get("paired_plan_authorized_only_when_ready", True)
        ),
    )
    contract.validate()
    return contract


def _metrics_from_simulation(simulation: Any) -> dict[str, float | int]:
    alive_mask = np.asarray(simulation.entities.alive, dtype=np.bool_)
    alive = int(np.count_nonzero(alive_mask))
    initial = max(int(simulation.cfg.world.initial_entities), 1)
    generation = np.asarray(simulation.entities.generation[alive_mask], dtype=np.float64)
    founder_alive = int(np.count_nonzero(generation == 0.0)) if generation.size else 0
    descendant_alive = alive - founder_alive
    return {
        "tick": int(simulation.tick),
        "alive": alive,
        "alive_fraction_to_initial": float(alive / initial),
        "births_total": int(simulation.total_births),
        "cumulative_births_per_initial": float(simulation.total_births / initial),
        "living_descendants_per_initial": float(descendant_alive / initial),
        "mean_generation": float(generation.mean()) if generation.size else 0.0,
        "max_generation": int(generation.max()) if generation.size else 0,
        "founder_alive_fraction": float(founder_alive / alive) if alive else 0.0,
        "descendant_alive_fraction": float(descendant_alive / alive) if alive else 0.0,
    }


def _metrics_from_summary(summary: dict[str, Any], initial: int) -> dict[str, float | int]:
    alive = int(summary.get("alive", 0))
    births = int(summary.get("births_total", 0))
    founder_fraction = float(
        summary.get("founder_alive_fraction", 1.0 if alive else 0.0)
    )
    return {
        "tick": int(summary.get("tick", 0)),
        "alive": alive,
        "alive_fraction_to_initial": float(alive / max(initial, 1)),
        "births_total": births,
        "cumulative_births_per_initial": float(
            summary.get("cumulative_births_per_initial", births / max(initial, 1))
        ),
        "living_descendants_per_initial": float(
            summary.get("living_descendants_per_initial", 0.0)
        ),
        "mean_generation": float(summary.get("mean_generation", 0.0)),
        "max_generation": int(summary.get("max_generation", 0)),
        "founder_alive_fraction": founder_fraction,
        "descendant_alive_fraction": float(
            summary.get(
                "descendant_alive_fraction",
                1.0 - founder_fraction if alive else 0.0,
            )
        ),
    }


def evaluate(
    metrics: dict[str, float | int],
    checkpoint: HealthCheckpoint,
    previous_metrics: dict[str, float | int] | None = None,
) -> dict[str, Any]:
    previous_alive = int(previous_metrics["alive"]) if previous_metrics is not None else None
    decline_fraction = (
        max(previous_alive - int(metrics["alive"]), 0) / max(previous_alive, 1)
        if previous_alive is not None
        else 0.0
    )
    checks = {
        "alive_count_met": int(metrics["alive"]) >= checkpoint.minimum_alive_count,
        "alive_fraction_met": float(metrics["alive_fraction_to_initial"])
        >= checkpoint.minimum_alive_fraction_to_initial,
        "birth_turnover_met": float(metrics["cumulative_births_per_initial"])
        >= checkpoint.minimum_cumulative_births_per_initial,
        "living_descendants_met": float(metrics["living_descendants_per_initial"])
        >= checkpoint.minimum_living_descendants_per_initial,
        "mean_generation_met": float(metrics["mean_generation"])
        >= checkpoint.minimum_mean_generation,
        "founder_fraction_met": float(metrics["founder_alive_fraction"])
        <= checkpoint.maximum_founder_alive_fraction,
        "checkpoint_decline_met": decline_fraction
        <= checkpoint.maximum_alive_decline_fraction_from_previous_checkpoint,
    }
    return {
        "tick": int(metrics["tick"]),
        "requirements": checkpoint.__dict__,
        "metrics": metrics,
        "previous_metrics": previous_metrics,
        "alive_decline_fraction_from_previous_checkpoint": decline_fraction,
        "checks": checks,
        "ready": all(checks.values()),
        "failed_checks": [name for name, passed in checks.items() if not passed],
    }


class RuntimeHealthGate:
    """Stateful stop condition passed to ``Simulation.run``."""

    def __init__(self, contract: SourceHealthContract, output: str | Path) -> None:
        self.contract = contract
        self.output = Path(output)
        self.output.parent.mkdir(parents=True, exist_ok=True)
        self._by_tick = {item.tick: item for item in contract.checkpoints}
        self.events: list[dict[str, Any]] = []
        self.previous_metrics: dict[str, float | int] | None = None

    def __call__(self, simulation: Any) -> str | None:
        checkpoint = self._by_tick.get(int(simulation.tick))
        if checkpoint is None:
            return None
        metrics = _metrics_from_simulation(simulation)
        event = evaluate(metrics, checkpoint, self.previous_metrics)
        self.previous_metrics = metrics
        self.events.append(event)
        self.output.write_text(
            json.dumps(
                {
                    "schema": "source-health-runtime-events-v1",
                    "events": self.events,
                },
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        if event["ready"]:
            return None
        return "source-health-gate:" + ",".join(event["failed_checks"])


def build_report(
    source_root: str | Path, contract: SourceHealthContract
) -> dict[str, Any]:
    root = Path(source_root)
    final = contract.final_checkpoint
    seeds: list[dict[str, Any]] = []
    for run_dir in sorted(root.glob("seed_*")):
        summary_path = run_dir / "summary.json"
        config_path = run_dir / "resolved_config.json"
        termination_path = run_dir / "run_termination.json"
        if not summary_path.is_file() or not config_path.is_file():
            seeds.append(
                {
                    "run_dir": str(run_dir),
                    "ready": False,
                    "failed_checks": ["missing-summary-or-config"],
                }
            )
            continue
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
        config = json.loads(config_path.read_text(encoding="utf-8"))
        runtime_events_path = run_dir / "source_health_runtime_events.json"
        runtime_events = (
            json.loads(runtime_events_path.read_text(encoding="utf-8")).get("events", [])
            if runtime_events_path.is_file()
            else []
        )
        metrics = _metrics_from_summary(summary, int(config["world"]["initial_entities"]))
        if runtime_events:
            assessment = dict(runtime_events[-1])
            assessment["ready"] = bool(
                len(runtime_events) == len(contract.checkpoints)
                and all(bool(event.get("ready")) for event in runtime_events)
            )
            assessment["failed_checks"] = [
                check
                for event in runtime_events
                for check in event.get("failed_checks", ())
            ]
            assessment["runtime_event_count"] = len(runtime_events)
        else:
            assessment = evaluate(metrics, final)
            assessment["runtime_event_count"] = 0
        assessment["seed"] = int(config["run"]["seed"])
        assessment["run_dir"] = str(run_dir)
        assessment["termination"] = (
            json.loads(termination_path.read_text(encoding="utf-8"))
            if termination_path.is_file()
            else None
        )
        seeds.append(assessment)
    ready_count = sum(bool(item.get("ready")) for item in seeds)
    ready = ready_count >= contract.required_ready_seed_count
    return {
        "schema": REPORT_SCHEMA,
        "source_root": str(root),
        "contract": {
            "schema": contract.schema,
            "purpose": contract.purpose,
            "required_ready_seed_count": contract.required_ready_seed_count,
            "paired_plan_authorized_only_when_ready": contract.paired_plan_authorized_only_when_ready,
            "final_checkpoint": final.__dict__,
        },
        "seed_count": len(seeds),
        "ready_seed_count": ready_count,
        "ready": ready,
        "paired_plan_authorized": bool(
            ready or not contract.paired_plan_authorized_only_when_ready
        ),
        "seeds": seeds,
        "interpretation": (
            "source-qualified-for-next-stage"
            if ready
            else "source-collapse-or-insufficient-generational-turnover"
        ),
    }


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Source health gate",
        "",
        f"- ready: **{report['ready']}**",
        f"- ready seeds: {report['ready_seed_count']} / {report['seed_count']}",
        f"- paired plan authorized: **{report['paired_plan_authorized']}**",
        f"- interpretation: `{report['interpretation']}`",
        "",
        "| seed | tick | alive | births/initial | living descendants/initial | mean generation | founder fraction | ready | failed |",
        "|---:|---:|---:|---:|---:|---:|---:|---|---|",
    ]
    for item in report["seeds"]:
        metrics = item.get("metrics", {})
        lines.append(
            "| {seed} | {tick} | {alive} | {births:.4f} | {desc:.4f} | {generation:.4f} | {founder:.4f} | {ready} | {failed} |".format(
                seed=item.get("seed", "-"),
                tick=metrics.get("tick", "-"),
                alive=metrics.get("alive", "-"),
                births=float(metrics.get("cumulative_births_per_initial", 0.0)),
                desc=float(metrics.get("living_descendants_per_initial", 0.0)),
                generation=float(metrics.get("mean_generation", 0.0)),
                founder=float(metrics.get("founder_alive_fraction", 0.0)),
                ready=item.get("ready", False),
                failed=", ".join(item.get("failed_checks", ())) or "-",
            )
        )
    lines += [
        "",
        "> A failed gate terminates the execution chain. It does not authorize gene-effect, selection, adaptation, or niche interpretation.",
        "",
    ]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Qualify a source panel before paired or evolutionary stages.")
    parser.add_argument("--source-root", required=True)
    parser.add_argument("--contract", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--allow-failed", action="store_true")
    args = parser.parse_args(argv)
    contract = load_contract(args.contract)
    report = build_report(args.source_root, contract)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    output.with_suffix(".md").write_text(render_markdown(report), encoding="utf-8")
    print(json.dumps({"ready": report["ready"], "output": str(output)}, ensure_ascii=False))
    if not report["ready"] and not args.allow_failed:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
