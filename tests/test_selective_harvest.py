from __future__ import annotations

from dataclasses import replace
import json
from pathlib import Path

import numpy as np
import pytest

from se.analysis.long_run import analyze
from se.analysis.protocol_audit import build_protocol_audit
from se.cfg import load_config, validate_config
from se.env.gpu import DeviceEnvironment
from se.env.world import Environment
from se.env.niches import (
    AFFINITY_SCALE,
    SELECTIVE_HARVEST_SCHEMA,
    harvest_request_rates,
)
from se.runtime.sim import Simulation


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "configs" / "d1b_selective_harvest_smoke.json"


def test_selective_harvest_keeps_fixed_total_budget() -> None:
    cfg = load_config(CONFIG)
    neutral = np.full((1, 4), AFFINITY_SCALE, dtype=np.int32)
    specialist = np.asarray([[7000, 3128, 3128, 3128]], dtype=np.int32)
    rates = harvest_request_rates(
        np.vstack((neutral, specialist)),
        cfg,
        channel_draws=np.asarray([0.02, 0.10], dtype=np.float64),
    )
    assert rates.shape == (2, 4)
    assert np.allclose(rates.sum(axis=1), rates[0].sum(), atol=1e-7, rtol=0.0)
    expected_total = float(
        np.float32(cfg.entities.harvest_rate)
        * np.asarray(cfg.environment.harvest_channel_multipliers, dtype=np.float32).sum()
    )
    assert np.count_nonzero(rates[0]) == 1
    assert np.count_nonzero(rates[1]) == 1
    assert rates[0, 0] == pytest.approx(expected_total)
    assert rates[1, 0] == pytest.approx(expected_total)




def test_affinity_sampling_changes_channel_frequency_without_changing_budget() -> None:
    cfg = load_config(CONFIG)
    count = 4000
    draws = (np.arange(count, dtype=np.float64) + 0.5) / count
    neutral = np.full((count, 4), AFFINITY_SCALE, dtype=np.int32)
    specialist = np.broadcast_to(
        np.asarray([7000, 3128, 3128, 3128], dtype=np.int32), (count, 4)
    ).copy()
    neutral_rates = harvest_request_rates(neutral, cfg, channel_draws=draws)
    specialist_rates = harvest_request_rates(specialist, cfg, channel_draws=draws)
    neutral_counts = np.count_nonzero(neutral_rates, axis=0)
    specialist_counts = np.count_nonzero(specialist_rates, axis=0)
    assert np.max(neutral_counts) - np.min(neutral_counts) <= 1
    assert specialist_counts[0] > neutral_counts[0]
    assert np.allclose(
        neutral_rates.sum(axis=1), specialist_rates.sum(axis=1), atol=0.0, rtol=0.0
    )

def test_selective_harvest_cpu_and_simulated_device_match() -> None:
    cfg = load_config(CONFIG)
    cpu = Environment(cfg)
    device = DeviceEnvironment(cfg, backend="cpu")
    affinities = np.asarray(
        [
            [7000, 3128, 3128, 3128],
            [3128, 7000, 3128, 3128],
            [3128, 3128, 7000, 3128],
        ],
        dtype=np.int32,
    )
    cells = np.asarray([0, 0, 1], dtype=np.int32)
    rates = harvest_request_rates(
        affinities,
        cfg,
        channel_draws=np.asarray([0.05, 0.35, 0.70], dtype=np.float64),
    )
    cpu_gathered = cpu.resolve_harvest(cells, rates)
    device_gathered = np.asarray(device.resolve_harvest(cells, rates))
    assert np.array_equal(cpu_gathered, device_gathered)
    cpu.commit_harvest(cells, cpu_gathered)
    device.commit_harvest(cells, device_gathered)
    assert np.array_equal(cpu.resources, np.asarray(device.resources))

def test_selective_harvest_requires_resource_affinity() -> None:
    cfg = load_config(CONFIG)
    invalid = replace(
        cfg,
        entities=replace(cfg.entities, resource_affinity_schema="disabled"),
    )
    with pytest.raises(ValueError, match="requires inherited resource affinity"):
        validate_config(invalid)


def test_selective_harvest_is_published_and_analyzed(tmp_path: Path) -> None:
    cfg = load_config(CONFIG)
    cfg = replace(
        cfg,
        run=replace(
            cfg.run,
            ticks=12,
            metrics_period=3,
            checkpoint_period=6,
            evolution_evaluation_period=3,
        ),
        world=replace(cfg.world, initial_entities=64, max_entities=96),
    )
    validate_config(cfg)
    out = tmp_path / "run"
    Simulation(cfg, out, backend="cpu").run(until_tick=12)
    manifest = json.loads((out / "run_manifest.json").read_text())
    assert manifest["harvest_allocation_schema"] == SELECTIVE_HARVEST_SCHEMA
    report = analyze([out / "evolution_progress.jsonl"])
    assert report["schema"] == "multi-seed-long-run-analysis-v15"
    demand = report["runs"][0]["resource_demand_analysis"]
    assert demand["available"] is True
    assert len(demand["harvest_channel_shares"]) == 4
    assert report["runs"][0]["capacity_final"]


def test_protocol_audit_records_selective_budget() -> None:
    report = build_protocol_audit(CONFIG)
    assert report["schema"] == "structural-measurement-protocol-audit-v29"
    resource = report["resource_environment_protocol"]
    assert resource["harvest_allocation_schema"] == SELECTIVE_HARVEST_SCHEMA
    assert "one channel" in resource["harvest_budget_semantics"]
