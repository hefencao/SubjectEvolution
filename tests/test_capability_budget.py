from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path

import pytest

from se.analysis.capability_budget import derive_budget, verify_budget


def _write(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def _fixture(tmp_path: Path) -> tuple[Path, Path]:
    source = tmp_path / "runs"
    contract_sha = "a" * 64
    seeds = []
    for offset, seed in enumerate((11, 12, 13)):
        alive = 120 + offset
        metrics = {
            "tick": 480,
            "alive": alive,
            "alive_fraction_to_initial": alive / 128,
            "cumulative_births_per_initial": 1.0 + 0.1 * offset,
            "living_descendants_per_initial": 0.6 + 0.05 * offset,
            "mean_generation": 0.8 + 0.1 * offset,
            "max_generation": 4,
            "founder_alive_fraction": 0.4 - 0.02 * offset,
        }
        assessment = {
            "seed": seed,
            "tick": 480,
            "metrics": metrics,
            "ready": True,
            "runtime_contract_sha256": contract_sha,
            "alive_decline_fraction_from_previous_checkpoint": 0.01,
            "termination": {
                "completed_tick": 480,
                "terminated_early": False,
                "reason": None,
            },
        }
        seeds.append(assessment)
        run = source / f"seed_{seed}"
        config = {
            "run": {"seed": seed, "ticks": 480},
            "world": {"initial_entities": 128},
            "environment": {"resource_regeneration": [0.027] * 4},
            "entities": {
                "maintenance_cost": 0.01,
                "reproduction_parent_reserve": 0.8,
                "reproduction_investment_levels": [0.9],
            },
        }
        _write(run / "resolved_config.json", config)
        _write(
            run / "summary.json",
            {
                "alive": alive,
                "mean_energy": 0.9 + 0.02 * offset,
                "resource_body_realized_0_total": 900.0 + 20.0 * offset,
            },
        )
        events = []
        for tick, point_alive in ((120, 180), (240, 150), (360, 130), (480, alive)):
            events.append({"tick": tick, "metrics": {"alive": point_alive}})
        _write(
            run / "source_health_runtime_events.json",
            {
                "schema": "source-health-runtime-events-v2",
                "contract_sha256": contract_sha,
                "events": events,
            },
        )
    gate = tmp_path / "gate.json"
    _write(
        gate,
        {
            "schema": "source-health-gate-report-v2",
            "contract": {
                "schema": "source-health-contract-v2",
                "sha256": contract_sha,
                "required_ready_seed_count": 3,
            },
            "seed_count": 3,
            "ready_seed_count": 3,
            "hard_stopped_seed_count": 0,
            "ready": True,
            "paired_plan_authorized": True,
            "seeds": seeds,
        },
    )
    return source, gate


def test_derive_budget_requires_one_qualified_unchanged_source_panel(tmp_path: Path) -> None:
    source, gate = _fixture(tmp_path)
    output = tmp_path / "budget.json"
    report = derive_budget(source_root=source, health_report=gate, output=output)
    assert report["source_qualification_ready"]
    assert report["qualified_seed_count"] == 3
    assert report["authorization"]["capability_source_pilot_authorized"]
    assert not report["authorization"]["paired_branch_authorized"]
    assert report["attachment_budget"]["maximum_new_recurring_cost_per_entity_tick"] > 0.0
    assert (
        report["attachment_budget"]["maximum_immature_recurring_cost_per_entity_tick"]
        < report["attachment_budget"]["maximum_new_recurring_cost_per_entity_tick"]
    )
    verified = verify_budget(output)
    assert verified["budget_sha256"] == report["budget_sha256"]
    assert output.with_suffix(".md").is_file()


def test_budget_rejects_contract_drift(tmp_path: Path) -> None:
    source, gate_path = _fixture(tmp_path)
    gate = json.loads(gate_path.read_text())
    gate["seeds"][1]["runtime_contract_sha256"] = "b" * 64
    _write(gate_path, gate)
    with pytest.raises(ValueError, match="different source-health contract"):
        derive_budget(source_root=source, health_report=gate_path, output=tmp_path / "budget.json")


def test_budget_rejects_config_drift(tmp_path: Path) -> None:
    source, gate = _fixture(tmp_path)
    config_path = source / "seed_12" / "resolved_config.json"
    config = json.loads(config_path.read_text())
    config["entities"]["maintenance_cost"] = 0.011
    _write(config_path, config)
    with pytest.raises(ValueError, match="unchanged source configuration|fixed turnover substrate"):
        derive_budget(source_root=source, health_report=gate, output=tmp_path / "budget.json")


def test_budget_hash_detects_mutation(tmp_path: Path) -> None:
    source, gate = _fixture(tmp_path)
    output = tmp_path / "budget.json"
    derive_budget(source_root=source, health_report=gate, output=output)
    payload = json.loads(output.read_text())
    mutated = deepcopy(payload)
    mutated["attachment_budget"]["maximum_new_recurring_cost_per_entity_tick"] *= 2
    _write(output, mutated)
    with pytest.raises(ValueError, match="SHA-256 mismatch"):
        verify_budget(output)
