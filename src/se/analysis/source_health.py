"""Execution precondition for demographic and generational source viability.

Version 1 treated every qualification miss at every checkpoint as an immediate
runtime stop.  Version 2 separates three concerns:

* advisory qualification checkpoints, which describe whether maturation is on
  schedule but never stop a recoverable run;
* catastrophic runtime floors, which stop a source before it becomes a small-
  population bottleneck;
* required qualification checkpoints, which authorize the next study stage only
  after the full source trajectory has completed.

This is an execution precondition, not a post-hoc effect audit.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np

PROTOCOL_SCHEMA_V1 = "source-health-contract-v1"
PROTOCOL_SCHEMA_V2 = "source-health-contract-v2"
PROTOCOL_SCHEMAS = frozenset({PROTOCOL_SCHEMA_V1, PROTOCOL_SCHEMA_V2})
REPORT_SCHEMA_V1 = "source-health-gate-report-v1"
REPORT_SCHEMA_V2 = "source-health-gate-report-v2"


@dataclass(frozen=True)
class RuntimeStopThresholds:
    """Catastrophic floors that may terminate a run before the final checkpoint."""

    minimum_alive_count: int | None = None
    minimum_alive_fraction_to_initial: float | None = None
    minimum_cumulative_births_per_initial: float | None = None
    minimum_living_descendants_per_initial: float | None = None
    maximum_alive_decline_fraction_from_previous_checkpoint: float | None = None

    def validate(self) -> None:
        if self.minimum_alive_count is not None and self.minimum_alive_count < 1:
            raise ValueError("runtime minimum alive count must be positive")
        for name, value in (
            ("minimum_alive_fraction_to_initial", self.minimum_alive_fraction_to_initial),
            (
                "minimum_cumulative_births_per_initial",
                self.minimum_cumulative_births_per_initial,
            ),
            (
                "minimum_living_descendants_per_initial",
                self.minimum_living_descendants_per_initial,
            ),
        ):
            if value is not None and value < 0.0:
                raise ValueError(f"runtime {name} cannot be negative")
        decline = self.maximum_alive_decline_fraction_from_previous_checkpoint
        if decline is not None and not 0.0 <= decline <= 1.0:
            raise ValueError("runtime maximum checkpoint decline must be in [0, 1]")
        if all(value is None for value in self.__dict__.values()):
            raise ValueError("runtime stop thresholds cannot be empty")


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
    required_for_final: bool = True
    hard_stop: RuntimeStopThresholds | None = None

    def validate(self) -> None:
        if self.tick < 1:
            raise ValueError("health checkpoint tick must be positive")
        if self.minimum_alive_count < 1:
            raise ValueError("minimum alive count must be positive")
        for name, value in (
            ("minimum_alive_fraction_to_initial", self.minimum_alive_fraction_to_initial),
            (
                "minimum_cumulative_births_per_initial",
                self.minimum_cumulative_births_per_initial,
            ),
            (
                "minimum_living_descendants_per_initial",
                self.minimum_living_descendants_per_initial,
            ),
            ("minimum_mean_generation", self.minimum_mean_generation),
        ):
            if value < 0.0:
                raise ValueError(f"{name} cannot be negative")
        if not 0.0 <= self.maximum_founder_alive_fraction <= 1.0:
            raise ValueError("maximum founder fraction must be in [0, 1]")
        if not 0.0 <= self.maximum_alive_decline_fraction_from_previous_checkpoint <= 1.0:
            raise ValueError("maximum checkpoint decline fraction must be in [0, 1]")
        if self.hard_stop is not None:
            self.hard_stop.validate()


@dataclass(frozen=True)
class SourceHealthContract:
    schema: str
    purpose: str
    checkpoints: tuple[HealthCheckpoint, ...]
    required_ready_seed_count: int
    stop_panel_after_failed_seed_count: int
    paired_plan_authorized_only_when_ready: bool = True

    def validate(self) -> None:
        if self.schema not in PROTOCOL_SCHEMAS:
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
        if self.schema == PROTOCOL_SCHEMA_V2:
            required = [item for item in self.checkpoints if item.required_for_final]
            if not required:
                raise ValueError("v2 source health contract requires a final qualification checkpoint")
            if not self.checkpoints[-1].required_for_final:
                raise ValueError("the last v2 checkpoint must be required for final qualification")

    @property
    def final_checkpoint(self) -> HealthCheckpoint:
        return self.checkpoints[-1]


def _checkpoint_payload(checkpoint: HealthCheckpoint) -> dict[str, Any]:
    payload = {
        "tick": checkpoint.tick,
        "minimum_alive_count": checkpoint.minimum_alive_count,
        "minimum_alive_fraction_to_initial": checkpoint.minimum_alive_fraction_to_initial,
        "minimum_cumulative_births_per_initial": checkpoint.minimum_cumulative_births_per_initial,
        "minimum_living_descendants_per_initial": checkpoint.minimum_living_descendants_per_initial,
        "minimum_mean_generation": checkpoint.minimum_mean_generation,
        "maximum_founder_alive_fraction": checkpoint.maximum_founder_alive_fraction,
        "maximum_alive_decline_fraction_from_previous_checkpoint": (
            checkpoint.maximum_alive_decline_fraction_from_previous_checkpoint
        ),
        "required_for_final": checkpoint.required_for_final,
    }
    if checkpoint.hard_stop is not None:
        payload["hard_stop"] = {
            key: value
            for key, value in checkpoint.hard_stop.__dict__.items()
            if value is not None
        }
    return payload


def contract_payload(contract: SourceHealthContract) -> dict[str, Any]:
    return {
        "schema": contract.schema,
        "purpose": contract.purpose,
        "required_ready_seed_count": contract.required_ready_seed_count,
        "stop_panel_after_failed_seed_count": contract.stop_panel_after_failed_seed_count,
        "paired_plan_authorized_only_when_ready": (
            contract.paired_plan_authorized_only_when_ready
        ),
        "checkpoints": [
            _checkpoint_payload(checkpoint) for checkpoint in contract.checkpoints
        ],
    }


def contract_sha256(contract: SourceHealthContract) -> str:
    encoded = json.dumps(
        contract_payload(contract),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def load_contract(path: str | Path) -> SourceHealthContract:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    schema = str(payload.get("schema", ""))
    checkpoints: list[HealthCheckpoint] = []
    for raw_item in payload.get("checkpoints", ()):
        item = dict(raw_item)
        hard_stop_payload = item.pop("hard_stop", None)
        hard_stop = (
            RuntimeStopThresholds(**hard_stop_payload)
            if isinstance(hard_stop_payload, dict)
            else None
        )
        if schema == PROTOCOL_SCHEMA_V1:
            item.setdefault("required_for_final", True)
        checkpoints.append(HealthCheckpoint(**item, hard_stop=hard_stop))
    contract = SourceHealthContract(
        schema=schema,
        purpose=str(payload.get("purpose", "")),
        checkpoints=tuple(checkpoints),
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


def _decline_fraction(
    metrics: dict[str, float | int],
    previous_metrics: dict[str, float | int] | None,
) -> float:
    if previous_metrics is None:
        return 0.0
    previous_alive = int(previous_metrics["alive"])
    return max(previous_alive - int(metrics["alive"]), 0) / max(previous_alive, 1)


def evaluate(
    metrics: dict[str, float | int],
    checkpoint: HealthCheckpoint,
    previous_metrics: dict[str, float | int] | None = None,
) -> dict[str, Any]:
    decline_fraction = _decline_fraction(metrics, previous_metrics)
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
        "requirements": _checkpoint_payload(checkpoint),
        "metrics": metrics,
        "previous_metrics": previous_metrics,
        "alive_decline_fraction_from_previous_checkpoint": decline_fraction,
        "checks": checks,
        "ready": all(checks.values()),
        "failed_checks": [name for name, passed in checks.items() if not passed],
        "required_for_final": checkpoint.required_for_final,
    }


def evaluate_hard_stop(
    metrics: dict[str, float | int],
    thresholds: RuntimeStopThresholds | None,
    previous_metrics: dict[str, float | int] | None = None,
) -> dict[str, Any]:
    if thresholds is None:
        return {"enabled": False, "triggered": False, "checks": {}, "failed_checks": []}
    decline_fraction = _decline_fraction(metrics, previous_metrics)
    checks: dict[str, bool] = {}
    if thresholds.minimum_alive_count is not None:
        checks["alive_count_hard_floor_met"] = (
            int(metrics["alive"]) >= thresholds.minimum_alive_count
        )
    if thresholds.minimum_alive_fraction_to_initial is not None:
        checks["alive_fraction_hard_floor_met"] = (
            float(metrics["alive_fraction_to_initial"])
            >= thresholds.minimum_alive_fraction_to_initial
        )
    if thresholds.minimum_cumulative_births_per_initial is not None:
        checks["birth_turnover_hard_floor_met"] = (
            float(metrics["cumulative_births_per_initial"])
            >= thresholds.minimum_cumulative_births_per_initial
        )
    if thresholds.minimum_living_descendants_per_initial is not None:
        checks["living_descendants_hard_floor_met"] = (
            float(metrics["living_descendants_per_initial"])
            >= thresholds.minimum_living_descendants_per_initial
        )
    if thresholds.maximum_alive_decline_fraction_from_previous_checkpoint is not None:
        checks["checkpoint_decline_hard_floor_met"] = (
            decline_fraction
            <= thresholds.maximum_alive_decline_fraction_from_previous_checkpoint
        )
    failed = [name for name, passed in checks.items() if not passed]
    return {
        "enabled": True,
        "requirements": {
            key: value
            for key, value in thresholds.__dict__.items()
            if value is not None
        },
        "checks": checks,
        "failed_checks": failed,
        "triggered": bool(failed),
    }


class RuntimeHealthGate:
    """Stateful staged stop condition passed to ``Simulation.run``."""

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
        if self.contract.schema == PROTOCOL_SCHEMA_V1:
            hard_stop = {
                "enabled": True,
                "triggered": not event["ready"],
                "checks": event["checks"],
                "failed_checks": event["failed_checks"],
                "legacy_v1_semantics": True,
            }
        else:
            hard_stop = evaluate_hard_stop(
                metrics,
                checkpoint.hard_stop,
                self.previous_metrics,
            )
        event["hard_stop"] = hard_stop
        event["runtime_action"] = (
            "hard-stop"
            if hard_stop["triggered"]
            else (
                "continue"
                if event["ready"]
                else (
                    "complete-final-failure"
                    if checkpoint.required_for_final
                    else "continue-warning"
                )
            )
        )
        self.previous_metrics = metrics
        self.events.append(event)
        self.output.write_text(
            json.dumps(
                {
                    "schema": (
                        "source-health-runtime-events-v1"
                        if self.contract.schema == PROTOCOL_SCHEMA_V1
                        else "source-health-runtime-events-v2"
                    ),
                    "contract_schema": self.contract.schema,
                    "contract_sha256": contract_sha256(self.contract),
                    "events": self.events,
                },
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        if not hard_stop["triggered"]:
            return None
        prefix = (
            "source-health-gate:"
            if self.contract.schema == PROTOCOL_SCHEMA_V1
            else "source-health-hard-stop:"
        )
        return prefix + ",".join(hard_stop["failed_checks"])


def _assessment_from_v1_events(
    events: list[dict[str, Any]], contract: SourceHealthContract
) -> dict[str, Any]:
    assessment = dict(events[-1])
    assessment["ready"] = bool(
        len(events) == len(contract.checkpoints)
        and all(bool(event.get("ready")) for event in events)
    )
    assessment["failed_checks"] = [
        check for event in events for check in event.get("failed_checks", ())
    ]
    assessment["warning_checks"] = []
    assessment["hard_stop_checks"] = [
        check
        for event in events
        for check in event.get("hard_stop", {}).get("failed_checks", ())
    ]
    return assessment


def _assessment_from_v2_events(
    events: list[dict[str, Any]], contract: SourceHealthContract
) -> dict[str, Any]:
    assessment = dict(events[-1])
    by_tick = {int(event.get("tick", -1)): event for event in events}
    missing_required: list[str] = []
    required_failures: list[str] = []
    warnings: list[str] = []
    hard_stop_checks: list[str] = []
    for checkpoint in contract.checkpoints:
        event = by_tick.get(checkpoint.tick)
        if event is None:
            if checkpoint.required_for_final:
                missing_required.append(f"missing-required-checkpoint-{checkpoint.tick}")
            continue
        failed = [str(value) for value in event.get("failed_checks", ())]
        if checkpoint.required_for_final:
            required_failures.extend(f"tick-{checkpoint.tick}:{value}" for value in failed)
        else:
            warnings.extend(f"tick-{checkpoint.tick}:{value}" for value in failed)
        hard_stop_checks.extend(
            f"tick-{checkpoint.tick}:{value}"
            for value in event.get("hard_stop", {}).get("failed_checks", ())
        )
    assessment["ready"] = not (
        missing_required or required_failures or hard_stop_checks
    )
    assessment["failed_checks"] = missing_required + required_failures + hard_stop_checks
    assessment["warning_checks"] = warnings
    assessment["hard_stop_checks"] = hard_stop_checks
    assessment["required_checkpoint_count"] = sum(
        1 for checkpoint in contract.checkpoints if checkpoint.required_for_final
    )
    assessment["observed_required_checkpoint_count"] = sum(
        1
        for checkpoint in contract.checkpoints
        if checkpoint.required_for_final and checkpoint.tick in by_tick
    )
    return assessment


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
                    "warning_checks": [],
                    "hard_stop_checks": [],
                }
            )
            continue
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
        config = json.loads(config_path.read_text(encoding="utf-8"))
        runtime_events_path = run_dir / "source_health_runtime_events.json"
        runtime_payload = (
            json.loads(runtime_events_path.read_text(encoding="utf-8"))
            if runtime_events_path.is_file()
            else {}
        )
        runtime_events = runtime_payload.get("events", [])
        metrics = _metrics_from_summary(summary, int(config["world"]["initial_entities"]))
        runtime_contract_mismatch = bool(
            contract.schema == PROTOCOL_SCHEMA_V2
            and runtime_events
            and runtime_payload.get("contract_sha256") != contract_sha256(contract)
        )
        if runtime_events and runtime_contract_mismatch:
            assessment = dict(runtime_events[-1])
            assessment["ready"] = False
            assessment["failed_checks"] = ["source-health-contract-mismatch"]
            assessment["warning_checks"] = []
            assessment["hard_stop_checks"] = []
            assessment["runtime_event_count"] = len(runtime_events)
            assessment["runtime_contract_sha256"] = runtime_payload.get("contract_sha256")
            assessment["expected_contract_sha256"] = contract_sha256(contract)
        elif runtime_events:
            assessment = (
                _assessment_from_v1_events(runtime_events, contract)
                if contract.schema == PROTOCOL_SCHEMA_V1
                else _assessment_from_v2_events(runtime_events, contract)
            )
            assessment["runtime_event_count"] = len(runtime_events)
            assessment["runtime_contract_sha256"] = runtime_payload.get("contract_sha256")
        else:
            assessment = evaluate(metrics, final)
            assessment["ready"] = bool(
                metrics["tick"] >= final.tick and assessment["ready"]
            )
            assessment["failed_checks"] = (
                assessment["failed_checks"]
                if metrics["tick"] >= final.tick
                else [f"missing-required-checkpoint-{final.tick}"]
            )
            assessment["warning_checks"] = []
            assessment["hard_stop_checks"] = []
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
    warning_count = sum(bool(item.get("warning_checks")) for item in seeds)
    hard_stop_count = sum(bool(item.get("hard_stop_checks")) for item in seeds)
    ready = ready_count >= contract.required_ready_seed_count
    if ready:
        interpretation = "source-qualified-for-next-stage"
    elif hard_stop_count:
        interpretation = "source-hard-stopped-before-final-qualification"
    else:
        interpretation = "source-final-qualification-not-met"
    return {
        "schema": (
            REPORT_SCHEMA_V1
            if contract.schema == PROTOCOL_SCHEMA_V1
            else REPORT_SCHEMA_V2
        ),
        "source_root": str(root),
        "contract": {
            "schema": contract.schema,
            "sha256": contract_sha256(contract),
            "purpose": contract.purpose,
            "required_ready_seed_count": contract.required_ready_seed_count,
            "paired_plan_authorized_only_when_ready": (
                contract.paired_plan_authorized_only_when_ready
            ),
            "final_checkpoint": _checkpoint_payload(final),
            "checkpoints": [
                _checkpoint_payload(checkpoint) for checkpoint in contract.checkpoints
            ],
        },
        "seed_count": len(seeds),
        "ready_seed_count": ready_count,
        "warning_seed_count": warning_count,
        "hard_stopped_seed_count": hard_stop_count,
        "ready": ready,
        "paired_plan_authorized": bool(
            ready or not contract.paired_plan_authorized_only_when_ready
        ),
        "seeds": seeds,
        "interpretation": interpretation,
    }


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Source health gate",
        "",
        f"- ready: **{report['ready']}**",
        f"- ready seeds: {report['ready_seed_count']} / {report['seed_count']}",
        f"- warning seeds: {report.get('warning_seed_count', 0)}",
        f"- hard-stopped seeds: {report.get('hard_stopped_seed_count', 0)}",
        f"- paired plan authorized: **{report['paired_plan_authorized']}**",
        f"- interpretation: `{report['interpretation']}`",
        "",
        "| seed | tick | alive | births/initial | living descendants/initial | mean generation | founder fraction | ready | warnings | failed |",
        "|---:|---:|---:|---:|---:|---:|---:|---|---|---|",
    ]
    for item in report["seeds"]:
        metrics = item.get("metrics", {})
        lines.append(
            "| {seed} | {tick} | {alive} | {births:.4f} | {desc:.4f} | {generation:.4f} | {founder:.4f} | {ready} | {warnings} | {failed} |".format(
                seed=item.get("seed", "-"),
                tick=metrics.get("tick", "-"),
                alive=metrics.get("alive", "-"),
                births=float(metrics.get("cumulative_births_per_initial", 0.0)),
                desc=float(metrics.get("living_descendants_per_initial", 0.0)),
                generation=float(metrics.get("mean_generation", 0.0)),
                founder=float(metrics.get("founder_alive_fraction", 0.0)),
                ready=item.get("ready", False),
                warnings=", ".join(item.get("warning_checks", ())) or "-",
                failed=", ".join(item.get("failed_checks", ())) or "-",
            )
        )
    lines += [
        "",
        "> Advisory misses are retained as trajectory evidence but do not stop a recoverable source. Catastrophic floors stop execution. Only required final checkpoints authorize the next stage.",
        "",
    ]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description="Qualify a source panel before paired or evolutionary stages."
    )
    parser.add_argument("--source-root", required=True)
    parser.add_argument("--contract", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--allow-failed", action="store_true")
    args = parser.parse_args(argv)
    contract = load_contract(args.contract)
    report = build_report(args.source_root, contract)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    output.with_suffix(".md").write_text(render_markdown(report), encoding="utf-8")
    print(json.dumps({"ready": report["ready"], "output": str(output)}, ensure_ascii=False))
    if not report["ready"] and not args.allow_failed:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
