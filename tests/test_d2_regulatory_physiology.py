from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from se.cfg import load_config
from se.differentiation.functional import (
    REGULATORY_INPUT_COUNT,
    REGULATORY_OUTPUT_NAMES,
    evaluate_contextual_harvest_modules_q,
    functional_module_gene_count,
    regulatory_outputs_enabled,
)
from se.differentiation.physiology import (
    PHYSIOLOGY_GENE_COUNT,
    physiology_phenotype,
    regulatory_physiology_enabled,
)
from se.experiments.d2_regulatory_physiology import execute_regulatory_physiology
from se.policy import ParametricPolicy
from se.runtime.physiology import apply_physiology_step, regulatory_multipliers
from se.runtime.sim import Simulation
from se.runtime.state import EntityState


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "configs" / "d2l_regulatory_physiology_smoke.json"
V4_CONFIG = ROOT / "configs" / "d2k_physiological_ecology_smoke.json"


def test_v5_layout_adds_regulatory_inputs_and_inherited_physiology() -> None:
    cfg = load_config(CONFIG)
    v4 = load_config(V4_CONFIG)
    assert regulatory_outputs_enabled(cfg)
    assert regulatory_physiology_enabled(cfg)
    assert REGULATORY_INPUT_COUNT == 20
    assert len(REGULATORY_OUTPUT_NAMES) == 4
    assert ParametricPolicy.physiology_gene_start(cfg) == (
        ParametricPolicy.functional_module_gene_start(cfg)
        + functional_module_gene_count(cfg)
    )
    assert ParametricPolicy.genome_size_for_config(cfg) == (
        ParametricPolicy.genome_size_for_config(v4)
        + 4 * (REGULATORY_INPUT_COUNT - 16)
        + PHYSIOLOGY_GENE_COUNT
    )


def test_v5_modules_publish_requests_not_direct_named_actions() -> None:
    cfg = load_config(CONFIG)
    entities = EntityState(cfg)
    active = np.flatnonzero(entities.alive)[:24]
    base = np.full((active.size, 4), 4096, dtype=np.int32)
    local_resources = np.full((active.size, 4), 0.5, dtype=np.float32)
    kwargs = dict(
        energy=entities.energy[active],
        integrity=entities.integrity[active],
        material=entities.material[active],
        information_store=entities.information_store[active],
        fertility=entities.fertility[active],
        local_resources=local_resources,
        oxygenation=entities.oxygenation[active],
        tissue_condition=entities.tissue_condition[active],
        structure_condition=entities.structure_condition[active],
        metabolic_fatigue=entities.metabolic_fatigue[active],
        mobilization_messenger=entities.mobilization_messenger[active],
        maintenance_messenger=entities.maintenance_messenger[active],
        messenger_precursor=entities.messenger_precursor[active],
        local_oxygen=np.full(active.size, 0.6),
        local_terrain=np.full(active.size, 0.3),
        local_wear=np.full(active.size, 0.2),
        cfg=cfg,
        gene_start=ParametricPolicy.functional_module_gene_start(cfg),
    )
    active_eval = evaluate_contextual_harvest_modules_q(
        entities.genotype[active], base, **kwargs
    )
    neutral_eval = evaluate_contextual_harvest_modules_q(
        entities.genotype[active], base, physiology_ablated=True, **kwargs
    )
    assert active_eval.physiology_output_q is not None
    assert np.any(active_eval.physiology_output_q != 0)
    assert np.all(neutral_eval.physiology_output_q == 0)
    assert np.array_equal(active_eval.preference_q, neutral_eval.preference_q)
    assert active_eval.computation_load is not None
    assert np.all(active_eval.computation_load >= 0.0)


def test_inherited_body_and_receptor_state_limit_the_same_request() -> None:
    cfg = load_config(CONFIG)
    entities = EntityState(cfg)
    active = np.flatnonzero(entities.alive)[:8]
    phenotype = physiology_phenotype(
        entities.genotype[active],
        cfg,
        gene_start=ParametricPolicy.physiology_gene_start(cfg),
    )
    output = np.full((active.size, 4), 4096, dtype=np.int32)
    healthy = regulatory_multipliers(
        output,
        oxygenation=np.full(active.size, 0.9),
        metabolic_fatigue=np.zeros(active.size),
        tissue_condition=np.ones(active.size),
        structure_condition=np.ones(active.size),
        mobilization_messenger=np.full(active.size, 0.8),
        maintenance_messenger=np.zeros(active.size),
        local_terrain=np.zeros(active.size),
        phenotype=phenotype,
        cfg=cfg,
    )
    constrained = regulatory_multipliers(
        output,
        oxygenation=np.full(active.size, 0.15),
        metabolic_fatigue=np.full(active.size, 0.9),
        tissue_condition=np.full(active.size, 0.5),
        structure_condition=np.full(active.size, 0.5),
        mobilization_messenger=np.full(active.size, 0.8),
        maintenance_messenger=np.zeros(active.size),
        local_terrain=np.full(active.size, 0.9),
        phenotype=phenotype,
        cfg=cfg,
    )
    blocked = regulatory_multipliers(
        output,
        oxygenation=np.full(active.size, 0.9),
        metabolic_fatigue=np.zeros(active.size),
        tissue_condition=np.ones(active.size),
        structure_condition=np.ones(active.size),
        mobilization_messenger=np.full(active.size, 0.8),
        maintenance_messenger=np.zeros(active.size),
        local_terrain=np.zeros(active.size),
        phenotype=phenotype,
        cfg=cfg,
        receptor_blocked=True,
    )
    assert np.all(healthy.movement > constrained.movement)
    assert np.all(healthy.sensor > constrained.sensor)
    assert np.all(healthy.movement >= blocked.movement)
    assert np.all(healthy.signal >= blocked.signal)


def test_zero_regulatory_output_is_basal_not_half_stimulation() -> None:
    cfg = load_config(CONFIG)
    entities = EntityState(cfg)
    active = np.flatnonzero(entities.alive)[:5]
    entities.mobilization_messenger[active] = 0.0
    entities.maintenance_messenger[active] = 0.0
    stats = apply_physiology_step(
        entities,
        active,
        output_q=np.zeros((active.size, 4), dtype=np.int32),
        local_oxygen=np.full(active.size, 0.8),
        local_terrain=np.zeros(active.size),
        local_wear=np.zeros(active.size),
        moved=np.zeros(active.size, dtype=bool),
        signaled=np.zeros(active.size, dtype=bool),
        cfg=cfg,
        genotype=entities.genotype[active],
        gene_start=ParametricPolicy.physiology_gene_start(cfg),
        computation_load=np.zeros(active.size),
    )
    assert stats.messenger_synthesis == 0.0
    assert np.all(entities.mobilization_messenger[active] == 0.0)
    assert np.all(entities.maintenance_messenger[active] == 0.0)
    # Basal oxygen uptake remains a body homeostasis process at zero neural drive.
    assert stats.oxygen_uptake > 0.0


def test_v5_settlement_conserves_precursor_energy_oxygen_and_repair() -> None:
    cfg = load_config(CONFIG)
    entities = EntityState(cfg)
    active = np.flatnonzero(entities.alive)[:6]
    entities.energy[active] = 2.0
    entities.material[active] = 1.0
    entities.integrity[active] = 0.65
    entities.tissue_condition[active] = 0.55
    entities.structure_condition[active] = 0.60
    entities.oxygenation[active] = 0.70
    entities.metabolic_fatigue[active] = 0.25
    entities.mobilization_messenger[active] = 0.20
    entities.maintenance_messenger[active] = 0.70
    entities.messenger_precursor[active] = 0.80
    output = np.full((active.size, 4), 4096, dtype=np.int32)
    before_energy = float(entities.energy[active].sum())
    before_material = float(entities.material[active].sum())
    before_precursor = float(entities.messenger_precursor[active].sum())
    stats = apply_physiology_step(
        entities,
        active,
        output_q=output,
        local_oxygen=np.full(active.size, 0.8),
        local_terrain=np.full(active.size, 0.4),
        local_wear=np.full(active.size, 0.5),
        moved=np.ones(active.size, dtype=bool),
        signaled=np.ones(active.size, dtype=bool),
        cfg=cfg,
        genotype=entities.genotype[active],
        gene_start=ParametricPolicy.physiology_gene_start(cfg),
        computation_load=np.full(active.size, 2.0),
    )
    assert stats.messenger_synthesis > 0.0
    assert stats.messenger_precursor_used > 0.0
    assert stats.messenger_energy > 0.0
    assert stats.computation_energy > 0.0
    assert stats.computation_oxygen > 0.0
    assert stats.fatigue_generated > 0.0
    assert stats.repair_material > 0.0
    assert stats.repair_energy > 0.0
    assert before_energy > float(entities.energy[active].sum())
    assert before_material > float(entities.material[active].sum())
    assert before_precursor - float(entities.messenger_precursor[active].sum()) == pytest.approx(
        stats.messenger_precursor_used - stats.messenger_precursor_recovered,
        abs=1e-5,
    )


def test_state_clamp_receptor_blockade_and_checkpoint_clone_are_persistent(
    tmp_path: Path,
) -> None:
    cfg = load_config(CONFIG)
    simulation = Simulation(cfg, tmp_path / "source", backend="cpu")
    simulation.apply_intervention("block-physiology-messenger-receptors")
    simulation.set_physiology_state_clamp("oxygenation", 0.4)
    simulation.set_physiology_state_clamp("mobilization_messenger", 0.7)
    simulation.step()
    active = np.flatnonzero(simulation.entities.alive)
    assert simulation.physiology_messenger_receptor_blockade_enabled is True
    assert np.all(simulation.entities.oxygenation[active] == np.float32(0.4))
    assert np.all(
        simulation.entities.mobilization_messenger[active] == np.float32(0.7)
    )
    branch = simulation.clone(tmp_path / "branch")
    assert branch.physiology_messenger_receptor_blockade_enabled is True
    assert branch.physiology_state_clamps == simulation.physiology_state_clamps
    checkpoint = simulation.save_full_checkpoint(tmp_path / "clamped.sechk")
    restored = Simulation.from_checkpoint(
        checkpoint, tmp_path / "restored", backend="cpu", until_tick=cfg.run.ticks
    )
    assert restored.physiology_messenger_receptor_blockade_enabled is True
    assert restored.physiology_state_clamps == simulation.physiology_state_clamps
    for item in (simulation, branch, restored):
        item.knowledge.close()
        item.evolution_progress.close()
        item.metrics.close()


def test_d2l_runner_reports_substrate_trends_without_maturity_gate(
    tmp_path: Path,
) -> None:
    cfg = load_config(CONFIG)
    result = execute_regulatory_physiology(
        cfg,
        [51001],
        tmp_path,
        backend="cpu",
        until_tick=10,
    )
    assert result["schema"] == "d2-regulatory-physiology-results-v2"
    assert result["plan"]["pass_fail_gate"] is False
    assert result["plan"]["online_weight_learning"] is False
    assert result["plan"]["module_outputs_are_regulatory_requests_not_direct_actions"] is True
    trends = result["stable_trend_summary"]
    assert trends["regulatory_output_used_in_every_seed"] is True
    assert trends["physiology_genetic_variation_observed"] is True
    assert trends["messenger_turnover_observed"] is True
    assert trends["finite_precursor_turnover_observed"] is True
    assert trends["computation_cost_observed"] is True
    final = result["runs"][0]["final"]
    assert final["functional_physiology_output_names"] == list(
        REGULATORY_OUTPUT_NAMES
    )
    assert len(final["functional_output_basis_port_names"]) == 8
    assert len(final["functional_output_basis_std_by_port"]) == 8
    assert final["functional_output_basis_active_port_count"] == 8
