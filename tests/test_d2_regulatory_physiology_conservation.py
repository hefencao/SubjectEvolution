from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from se.analysis.d2_regulatory_physiology_flows import assess
from se.cfg import load_config
from se.policy import ParametricPolicy
from se.runtime.physiology import (
    PhysiologyStepStats,
    apply_physiology_step,
    validate_conservative_flow_ledger,
)
from se.runtime.state import EntityState

ROOT = Path(__file__).resolve().parents[1]
CONSERVATIVE_CONFIG = ROOT / "configs" / "d2l_regulatory_physiology_smoke.json"
LEGACY_CONFIG = (
    ROOT / "configs" / "d2l_regulatory_physiology_legacy_v2_smoke.json"
)


def _step_with_energy(config: Path, energy: float, *, computation: float = 0.0):
    cfg = load_config(config)
    entities = EntityState(cfg)
    active = np.flatnonzero(entities.alive)[:4]
    entities.energy[active] = np.float32(energy)
    entities.messenger_precursor[active] = np.float32(0.8)
    output = np.full((active.size, 4), 4096, dtype=np.int32)
    stats = apply_physiology_step(
        entities,
        active,
        output_q=output,
        local_oxygen=np.full(active.size, 0.8),
        local_terrain=np.zeros(active.size),
        local_wear=np.zeros(active.size),
        moved=np.zeros(active.size, dtype=bool),
        signaled=np.zeros(active.size, dtype=bool),
        cfg=cfg,
        genotype=entities.genotype[active],
        gene_start=ParametricPolicy.physiology_gene_start(cfg),
        computation_load=np.full(active.size, computation),
    )
    return entities, active, stats


def test_legacy_v2_remains_replayable_with_historical_negative_flow() -> None:
    entities, active, stats = _step_with_energy(LEGACY_CONFIG, -0.1)
    assert stats.messenger_synthesis < 0.0
    assert stats.messenger_precursor_used < 0.0
    assert stats.messenger_energy < 0.0
    assert np.all(entities.energy[active] == 0.0)


def test_conservative_v3_never_turns_energy_debt_into_negative_flow() -> None:
    entities, active, stats = _step_with_energy(CONSERVATIVE_CONFIG, -0.1)
    assert stats.messenger_synthesis == 0.0
    assert stats.messenger_precursor_used == 0.0
    assert stats.messenger_energy == 0.0
    assert np.all(entities.energy[active] == np.float32(-0.1))


def test_conservative_v3_preserves_computation_energy_debt_for_starvation() -> None:
    entities, active, stats = _step_with_energy(
        CONSERVATIVE_CONFIG, 0.0, computation=4.0
    )
    assert stats.computation_energy > 0.0
    assert stats.computation_oxygen > 0.0
    assert np.all(entities.energy[active] < 0.0)


def test_conservative_flow_ledger_rejects_negative_or_non_finite_values() -> None:
    validate_conservative_flow_ledger(PhysiologyStepStats(messenger_synthesis=0.0))
    with pytest.raises(RuntimeError, match="messenger_synthesis"):
        validate_conservative_flow_ledger(
            PhysiologyStepStats(messenger_synthesis=-1.0e-3)
        )
    with pytest.raises(RuntimeError, match="messenger_energy"):
        validate_conservative_flow_ledger(
            PhysiologyStepStats(messenger_energy=float("nan"))
        )


def test_flow_assessment_flags_legacy_sign_error_and_accepts_v3_ledger() -> None:
    legacy = {
        "schema": "d2-regulatory-physiology-results-v1",
        "plan": {"schema": "d2-regulatory-physiology-plan-v1"},
        "runs": [
            {
                "seed": 51001,
                "final": {
                    "physiology_messenger_synthesis_total": -1.0,
                    "physiology_messenger_decay_total": 1.0,
                    "physiology_messenger_precursor_used_total": -0.5,
                    "physiology_messenger_precursor_recovered_total": 0.4,
                    "physiology_messenger_energy_total": -0.02,
                },
            }
        ],
    }
    legacy_assessment = assess(legacy)
    assert legacy_assessment["passed"] is False
    assert legacy_assessment["flow_ledger_valid"] is False
    assert legacy_assessment["recommendation"] == "rerun-conservative-v3-same-seeds"

    conservative = {
        "schema": "d2-regulatory-physiology-results-v2",
        "plan": {
            "schema": "d2-regulatory-physiology-plan-v2",
            "physiology_schema": "transport-metabolism-messenger-tissue-v3",
        },
        "runs": [
            {
                "seed": 52001,
                "final": {
                    "physiology_messenger_synthesis_total": 1.0,
                    "physiology_messenger_decay_total": 0.8,
                    "physiology_messenger_precursor_used_total": 0.5,
                    "physiology_messenger_precursor_recovered_total": 0.4,
                    "physiology_messenger_energy_total": 0.02,
                    "physiology_computation_energy_total": 0.1,
                    "physiology_computation_oxygen_total": 0.05,
                },
            }
        ],
    }
    assessment = assess(conservative)
    assert assessment["passed"] is True
    assert assessment["flow_ledger_valid"] is True
    assert assessment["recommendation"] == (
        "retain-conservative-substrate-and-continue-ecology-chain"
    )
