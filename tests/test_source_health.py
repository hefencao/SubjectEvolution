from __future__ import annotations

from types import SimpleNamespace
import json
from pathlib import Path

import numpy as np

from se.analysis.source_health import (
    HealthCheckpoint,
    RuntimeHealthGate,
    SourceHealthContract,
    build_report,
    evaluate,
)


def _checkpoint(tick: int, *, max_decline: float = 1.0) -> HealthCheckpoint:
    return HealthCheckpoint(
        tick=tick,
        minimum_alive_count=8,
        minimum_alive_fraction_to_initial=0.5,
        minimum_cumulative_births_per_initial=0.2,
        minimum_living_descendants_per_initial=0.1,
        minimum_mean_generation=0.1,
        maximum_founder_alive_fraction=0.9,
        maximum_alive_decline_fraction_from_previous_checkpoint=max_decline,
    )


def test_source_health_evaluate_rejects_checkpoint_collapse() -> None:
    previous = {
        "alive": 20,
        "alive_fraction_to_initial": 1.0,
        "births_total": 8,
        "cumulative_births_per_initial": 0.4,
        "living_descendants_per_initial": 0.2,
        "mean_generation": 0.2,
        "max_generation": 1,
        "founder_alive_fraction": 0.8,
        "descendant_alive_fraction": 0.2,
        "tick": 120,
    }
    current = dict(previous, tick=240, alive=10, alive_fraction_to_initial=0.5)
    result = evaluate(current, _checkpoint(240, max_decline=0.35), previous)
    assert result["ready"] is False
    assert result["alive_decline_fraction_from_previous_checkpoint"] == 0.5
    assert "checkpoint_decline_met" in result["failed_checks"]


def test_runtime_health_gate_stops_without_effect_interpretation(tmp_path: Path) -> None:
    contract = SourceHealthContract(
        schema="source-health-contract-v1",
        purpose="test",
        checkpoints=(_checkpoint(120),),
        required_ready_seed_count=1,
        stop_panel_after_failed_seed_count=1,
    )
    gate = RuntimeHealthGate(contract, tmp_path / "events.json")
    sim = SimpleNamespace(
        tick=120,
        total_births=0,
        cfg=SimpleNamespace(world=SimpleNamespace(initial_entities=20)),
        entities=SimpleNamespace(
            alive=np.asarray([True] * 5 + [False] * 15),
            generation=np.zeros(20, dtype=np.int16),
        ),
    )
    reason = gate(sim)
    assert reason is not None
    assert reason.startswith("source-health-gate:")
    payload = json.loads((tmp_path / "events.json").read_text())
    assert payload["events"][0]["ready"] is False


def test_build_report_does_not_authorize_bottlenecked_sources(tmp_path: Path) -> None:
    source = tmp_path / "source"
    run = source / "seed_1"
    run.mkdir(parents=True)
    (run / "resolved_config.json").write_text(
        json.dumps({"run": {"seed": 1}, "world": {"initial_entities": 20}})
    )
    (run / "summary.json").write_text(
        json.dumps(
            {
                "tick": 240,
                "alive": 2,
                "births_total": 1,
                "mean_generation": 0.0,
                "founder_alive_fraction": 1.0,
                "living_descendants_per_initial": 0.0,
            }
        )
    )
    contract = SourceHealthContract(
        schema="source-health-contract-v1",
        purpose="test",
        checkpoints=(_checkpoint(240),),
        required_ready_seed_count=1,
        stop_panel_after_failed_seed_count=1,
    )
    report = build_report(source, contract)
    assert report["ready"] is False
    assert report["paired_plan_authorized"] is False
