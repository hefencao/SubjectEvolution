from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import numpy as np

from se.cfg import load_config, validate_config
from se.evolution.lifecycle import BirthRequestPlan, plan_birth_allocations
from se.runtime.reproduction import (
    conservative_reproduction_investment_enabled,
    inherited_reproduction_investment_enabled,
    offspring_energy_endowment,
    reproduction_energy_cost,
    reproduction_energy_requirement,
    reproduction_investment,
)
from se.runtime.sim import Simulation
from se.runtime.state import EntityState

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "studies" / "d1k_conservative_reproductive_investment_v1" / "protocol" / "source_pilot.json"


def _close(sim: Simulation) -> None:
    sim.metrics.close()
    sim.evolution_progress.close()
    sim.knowledge.close()
    if sim.subject_structure_diagnostics is not None:
        sim.subject_structure_diagnostics.close()
    if sim.environment_atlas_diagnostics is not None:
        sim.environment_atlas_diagnostics.close()


def test_inherited_reproduction_investment_has_explicit_cost_and_reserve() -> None:
    cfg = load_config(CONFIG)
    validate_config(cfg)
    assert inherited_reproduction_investment_enabled(cfg)
    genotype = np.zeros((4, 8), dtype=np.float32)
    genotype[:, 6] = np.asarray([-1.0, -0.25, 0.25, 1.0], dtype=np.float32)
    investment = np.asarray(reproduction_investment(genotype, cfg))
    assert investment.tolist() == [0.6000000238418579, 1.0, 1.399999976158142, 1.7999999523162842]
    cost = np.asarray(reproduction_energy_cost(genotype, cfg))
    requirement = np.asarray(reproduction_energy_requirement(genotype, cfg))
    np.testing.assert_allclose(cost, investment + cfg.entities.reproduction_cost)
    np.testing.assert_allclose(
        requirement,
        cost + cfg.entities.reproduction_parent_reserve,
    )


def test_birth_transfers_inherited_investment_and_neutralization_preserves_parent_trait() -> None:
    cfg = load_config(CONFIG)
    cfg = replace(
        cfg,
        world=replace(cfg.world, initial_entities=1, max_entities=3),
        policy=replace(cfg.policy, mutation_probability=0.0),
    )
    for neutralized in (False, True):
        entities = EntityState(cfg)
        entities.genotype[0, 6] = np.float32(1.0)
        entities.primary_subject_id[0] = np.uint64(1)
        request = BirthRequestPlan(
            source_rows=np.asarray([0], dtype=np.int32),
            parent_indices=np.asarray([0], dtype=np.int32),
            parent_entity_ids=np.asarray([1], dtype=np.uint64),
            parent_subject_ids=np.asarray([1], dtype=np.uint64),
            tick=1,
            capacity_arbitration=cfg.entities.reproduction_capacity_arbitration,
            capacity_candidate_count=1,
            capacity_available_slots=2,
        )
        plan = plan_birth_allocations(
            request,
            entities.free_slots,
            int(entities.next_entity_id),
            entities.free_slot_version,
        )
        _, newborns = entities.commit_births(
            plan,
            offspring_endowment_neutralized=neutralized,
        )
        expected = float(
            np.asarray(
                offspring_energy_endowment(
                    entities.genotype[[0]], cfg, neutralized=neutralized
                )
            )[0]
        )
        # Existing physiology and sensing development costs are charged after
        # the transfer, so the committed child cannot exceed the endowment.
        assert 0.0 <= float(entities.energy[newborns[0]]) <= expected + 1e-6
        if neutralized:
            assert float(entities.energy[newborns[0]]) == 0.0


def test_endowment_ablation_survives_checkpoint_and_clone(tmp_path: Path) -> None:
    cfg = load_config(CONFIG)
    cfg = replace(
        cfg,
        run=replace(cfg.run, ticks=2, metrics_period=1, checkpoint_period=1),
        world=replace(cfg.world, initial_entities=8, max_entities=16),
    )
    sim = Simulation(cfg, tmp_path / "source", backend="cpu")
    genotype = sim.entities.genotype.copy()
    sim.apply_intervention("neutralize-conservative-offspring-endowment")
    assert sim.offspring_endowment_ablation_enabled
    assert np.array_equal(sim.entities.genotype, genotype)
    checkpoint = sim.save_full_checkpoint(tmp_path / "reproduction.sechk")
    _close(sim)
    restored = Simulation.from_checkpoint(
        checkpoint, tmp_path / "restored", backend="cpu", until_tick=2
    )
    assert restored.offspring_endowment_ablation_enabled
    branch = restored.clone(tmp_path / "branch")
    assert branch.offspring_endowment_ablation_enabled
    _close(branch)
    _close(restored)


def test_fixed_conservative_reproduction_is_nonheritable_and_energy_conserving() -> None:
    cfg = load_config(
        ROOT / "studies" / "d1m_fixed_conservative_turnover_v1" / "protocol" / "source_template.json"
    )
    cfg = replace(
        cfg,
        entities=replace(
            cfg.entities,
            reproduction_schema="fixed-conservative-offspring-investment-v3",
            reproduction_threshold=1.8,
            reproduction_cost=0.1,
            reproduction_parent_reserve=0.8,
            reproduction_investment_levels=(0.9,),
        ),
    )
    validate_config(cfg)
    assert conservative_reproduction_investment_enabled(cfg)
    assert not inherited_reproduction_investment_enabled(cfg)
    genotype = np.asarray([[-1.0] * 8, [1.0] * 8], dtype=np.float32)
    np.testing.assert_allclose(reproduction_investment(genotype, cfg), [0.9, 0.9])
    np.testing.assert_allclose(reproduction_energy_cost(genotype, cfg), [1.0, 1.0])
    np.testing.assert_allclose(reproduction_energy_requirement(genotype, cfg), [1.8, 1.8])
    np.testing.assert_allclose(offspring_energy_endowment(genotype, cfg), [0.9, 0.9])


def test_fixed_conservative_threshold_must_match_registered_budget() -> None:
    cfg = load_config(
        ROOT / "studies" / "d1m_fixed_conservative_turnover_v1" / "protocol" / "source_template.json"
    )
    invalid = replace(
        cfg,
        entities=replace(
            cfg.entities,
            reproduction_schema="fixed-conservative-offspring-investment-v3",
            reproduction_threshold=1.7,
            reproduction_cost=0.1,
            reproduction_parent_reserve=0.8,
            reproduction_investment_levels=(0.9,),
        ),
    )
    import pytest

    with pytest.raises(ValueError, match="threshold must equal"):
        validate_config(invalid)
