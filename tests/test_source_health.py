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


def _v2_checkpoint(
    tick: int,
    *,
    required: bool,
    qualification_decline: float = 0.30,
    hard_decline: float = 0.60,
) -> HealthCheckpoint:
    from se.analysis.source_health import RuntimeStopThresholds

    return HealthCheckpoint(
        tick=tick,
        minimum_alive_count=8,
        minimum_alive_fraction_to_initial=0.5,
        minimum_cumulative_births_per_initial=0.2,
        minimum_living_descendants_per_initial=0.1,
        minimum_mean_generation=0.1,
        maximum_founder_alive_fraction=0.9,
        maximum_alive_decline_fraction_from_previous_checkpoint=qualification_decline,
        required_for_final=required,
        hard_stop=RuntimeStopThresholds(
            minimum_alive_count=4,
            minimum_alive_fraction_to_initial=0.2,
            maximum_alive_decline_fraction_from_previous_checkpoint=hard_decline,
        ),
    )


def test_v2_runtime_gate_warns_without_stopping_on_marginal_advisory_miss(
    tmp_path: Path,
) -> None:
    contract = SourceHealthContract(
        schema="source-health-contract-v2",
        purpose="test",
        checkpoints=(
            _v2_checkpoint(120, required=False, qualification_decline=1.0),
            _v2_checkpoint(240, required=False, qualification_decline=0.30),
            _v2_checkpoint(360, required=True, qualification_decline=0.30),
        ),
        required_ready_seed_count=1,
        stop_panel_after_failed_seed_count=1,
    )
    gate = RuntimeHealthGate(contract, tmp_path / "events.json")
    entities = SimpleNamespace(
        alive=np.asarray([True] * 20),
        generation=np.asarray([0] * 12 + [1] * 8, dtype=np.int16),
    )
    sim = SimpleNamespace(
        tick=120,
        total_births=8,
        cfg=SimpleNamespace(world=SimpleNamespace(initial_entities=20)),
        entities=entities,
    )
    assert gate(sim) is None
    sim.tick = 240
    sim.total_births = 12
    sim.entities = SimpleNamespace(
        alive=np.asarray([True] * 13 + [False] * 7),
        generation=np.asarray([0] * 7 + [1] * 6 + [0] * 7, dtype=np.int16),
    )
    assert gate(sim) is None
    payload = json.loads((tmp_path / "events.json").read_text())
    event = payload["events"][-1]
    assert event["ready"] is False
    assert event["runtime_action"] == "continue-warning"
    assert event["hard_stop"]["triggered"] is False


def test_v2_runtime_gate_stops_only_on_catastrophic_floor(tmp_path: Path) -> None:
    contract = SourceHealthContract(
        schema="source-health-contract-v2",
        purpose="test",
        checkpoints=(_v2_checkpoint(120, required=True, hard_decline=0.50),),
        required_ready_seed_count=1,
        stop_panel_after_failed_seed_count=1,
    )
    gate = RuntimeHealthGate(contract, tmp_path / "events.json")
    sim = SimpleNamespace(
        tick=120,
        total_births=0,
        cfg=SimpleNamespace(world=SimpleNamespace(initial_entities=20)),
        entities=SimpleNamespace(
            alive=np.asarray([True] * 3 + [False] * 17),
            generation=np.zeros(20, dtype=np.int16),
        ),
    )
    reason = gate(sim)
    assert reason is not None
    assert reason.startswith("source-health-hard-stop:")


def test_v2_report_allows_advisory_warning_when_final_checkpoint_passes(
    tmp_path: Path,
) -> None:
    source = tmp_path / "source"
    run = source / "seed_1"
    run.mkdir(parents=True)
    (run / "resolved_config.json").write_text(
        json.dumps({"run": {"seed": 1}, "world": {"initial_entities": 20}})
    )
    (run / "summary.json").write_text(
        json.dumps(
            {
                "tick": 360,
                "alive": 18,
                "births_total": 20,
                "mean_generation": 0.8,
                "founder_alive_fraction": 0.4,
                "living_descendants_per_initial": 0.54,
            }
        )
    )
    checkpoints = (
        _v2_checkpoint(120, required=False, qualification_decline=1.0),
        _v2_checkpoint(240, required=False, qualification_decline=0.30),
        _v2_checkpoint(360, required=True, qualification_decline=0.30),
    )
    previous = {
        "tick": 120,
        "alive": 20,
        "alive_fraction_to_initial": 1.0,
        "births_total": 8,
        "cumulative_births_per_initial": 0.4,
        "living_descendants_per_initial": 0.2,
        "mean_generation": 0.2,
        "max_generation": 1,
        "founder_alive_fraction": 0.8,
        "descendant_alive_fraction": 0.2,
    }
    middle_metrics = dict(previous, tick=240, alive=13, alive_fraction_to_initial=0.65)
    final_metrics = {
        "tick": 360,
        "alive": 18,
        "alive_fraction_to_initial": 0.9,
        "births_total": 20,
        "cumulative_births_per_initial": 1.0,
        "living_descendants_per_initial": 0.54,
        "mean_generation": 0.8,
        "max_generation": 2,
        "founder_alive_fraction": 0.4,
        "descendant_alive_fraction": 0.6,
    }
    events = []
    for metrics, checkpoint, prior in (
        (previous, checkpoints[0], None),
        (middle_metrics, checkpoints[1], previous),
        (final_metrics, checkpoints[2], middle_metrics),
    ):
        event = evaluate(metrics, checkpoint, prior)
        event["hard_stop"] = {
            "enabled": True,
            "triggered": False,
            "checks": {},
            "failed_checks": [],
        }
        event["runtime_action"] = "continue" if event["ready"] else "continue-warning"
        events.append(event)
    contract = SourceHealthContract(
        schema="source-health-contract-v2",
        purpose="test",
        checkpoints=checkpoints,
        required_ready_seed_count=1,
        stop_panel_after_failed_seed_count=1,
    )
    from se.analysis.source_health import contract_sha256

    (run / "source_health_runtime_events.json").write_text(
        json.dumps(
            {
                "schema": "source-health-runtime-events-v2",
                "contract_sha256": contract_sha256(contract),
                "events": events,
            }
        )
    )
    report = build_report(source, contract)
    assert report["ready"] is True
    assert report["warning_seed_count"] == 1
    assert report["seeds"][0]["warning_checks"]
    assert report["seeds"][0]["failed_checks"] == []


def test_d1n_contract_separates_advisory_hard_stop_and_final_qualification() -> None:
    from pathlib import Path
    from se.analysis.source_health import load_contract

    contract = load_contract(
        Path("studies/d1n_staged_turnover_qualification_v1/protocol/source_health.json")
    )
    assert contract.schema == "source-health-contract-v2"
    assert [checkpoint.tick for checkpoint in contract.checkpoints] == [120, 240, 360, 480]
    assert [checkpoint.required_for_final for checkpoint in contract.checkpoints] == [
        False,
        False,
        False,
        True,
    ]
    assert all(checkpoint.hard_stop is not None for checkpoint in contract.checkpoints)
    assert contract.final_checkpoint.minimum_cumulative_births_per_initial == 0.85


def test_v2_report_rejects_runtime_events_from_changed_contract(tmp_path: Path) -> None:
    from se.analysis.source_health import contract_sha256

    source = tmp_path / "source"
    run = source / "seed_1"
    run.mkdir(parents=True)
    (run / "resolved_config.json").write_text(
        json.dumps({"run": {"seed": 1}, "world": {"initial_entities": 20}})
    )
    (run / "summary.json").write_text(
        json.dumps(
            {
                "tick": 120,
                "alive": 18,
                "births_total": 8,
                "mean_generation": 0.4,
                "founder_alive_fraction": 0.6,
                "living_descendants_per_initial": 0.36,
            }
        )
    )
    original = SourceHealthContract(
        schema="source-health-contract-v2",
        purpose="original",
        checkpoints=(_v2_checkpoint(120, required=True),),
        required_ready_seed_count=1,
        stop_panel_after_failed_seed_count=1,
    )
    metrics = {
        "tick": 120,
        "alive": 18,
        "alive_fraction_to_initial": 0.9,
        "births_total": 8,
        "cumulative_births_per_initial": 0.4,
        "living_descendants_per_initial": 0.36,
        "mean_generation": 0.4,
        "max_generation": 1,
        "founder_alive_fraction": 0.6,
        "descendant_alive_fraction": 0.4,
    }
    event = evaluate(metrics, original.final_checkpoint)
    event["hard_stop"] = {
        "enabled": True,
        "triggered": False,
        "checks": {},
        "failed_checks": [],
    }
    (run / "source_health_runtime_events.json").write_text(
        json.dumps(
            {
                "schema": "source-health-runtime-events-v2",
                "contract_sha256": contract_sha256(original),
                "events": [event],
            }
        )
    )
    changed = SourceHealthContract(
        schema="source-health-contract-v2",
        purpose="changed",
        checkpoints=(_v2_checkpoint(120, required=True),),
        required_ready_seed_count=1,
        stop_panel_after_failed_seed_count=1,
    )
    report = build_report(source, changed)
    assert report["ready"] is False
    assert report["seeds"][0]["failed_checks"] == [
        "source-health-contract-mismatch"
    ]
