from __future__ import annotations

from pathlib import Path

import numpy as np

from se.cfg import load_config
from se.differentiation.functional import (
    PHYSIOLOGICAL_INPUT_COUNT,
    PHYSIOLOGICAL_OUTPUT_COUNT,
    evaluate_contextual_harvest_modules_q,
    functional_module_gene_count,
    physiological_outputs_enabled,
)
from se.env.physiology import field_metrics
from se.env.world import Environment
from se.experiments.d2_physiological_ecology import execute_physiological_ecology
from se.policy import ParametricPolicy
from se.runtime.physiology import apply_physiology_step, physiology_multipliers
from se.runtime.state import EntityState


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "configs" / "d2k_physiological_ecology_smoke.json"


def test_v4_layout_and_environment_are_independent() -> None:
    cfg = load_config(CONFIG)
    assert physiological_outputs_enabled(cfg)
    assert PHYSIOLOGICAL_INPUT_COUNT == 16
    assert PHYSIOLOGICAL_OUTPUT_COUNT == 4
    assert functional_module_gene_count(cfg) > 4 * 19
    env = Environment(cfg)
    metrics = field_metrics(env.oxygen, env.terrain, env.wear)
    assert metrics.effective_dimensions > 2.0
    correlations = np.asarray(metrics.correlations)
    off_diagonal = correlations[~np.eye(3, dtype=bool)]
    assert np.max(np.abs(off_diagonal)) < 0.5


def test_v4_modules_publish_low_level_drives_and_support_neutralization() -> None:
    cfg = load_config(CONFIG)
    entities = EntityState(cfg)
    active = np.flatnonzero(entities.alive)[:32]
    env = Environment(cfg)
    cells = np.arange(active.size, dtype=np.int32)
    local = env.cell_values(cells)
    abiotic = env.physiology_for_cells(cells)
    base = np.full((active.size, 4), 4096, dtype=np.int32)
    kwargs = dict(
        energy=entities.energy[active],
        integrity=entities.integrity[active],
        material=entities.material[active],
        information_store=entities.information_store[active],
        fertility=entities.fertility[active],
        local_resources=local,
        oxygenation=entities.oxygenation[active],
        tissue_condition=entities.tissue_condition[active],
        structure_condition=entities.structure_condition[active],
        local_oxygen=abiotic[:, 0],
        local_terrain=abiotic[:, 1],
        local_wear=abiotic[:, 2],
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


def test_physiology_derives_motion_signal_and_conserved_repair() -> None:
    cfg = load_config(CONFIG)
    entities = EntityState(cfg)
    active = np.flatnonzero(entities.alive)[:4]
    entities.material[active] = 1.0
    entities.energy[active] = 2.0
    entities.integrity[active] = 0.7
    entities.tissue_condition[active] = 0.6
    entities.structure_condition[active] = 0.5
    entities.oxygenation[active] = 0.7
    output_q = np.full((active.size, 4), 4096, dtype=np.int32)
    multipliers = physiology_multipliers(
        output_q,
        entities.oxygenation[active],
        entities.tissue_condition[active],
        entities.structure_condition[active],
        np.full(active.size, 0.8),
        cfg,
    )
    assert np.all(multipliers.movement > 0.0)
    assert np.all(multipliers.signal > 0.0)
    assert np.all(multipliers.sensor > 0.0)
    baseline_sensor = entities.sensor_quality()[active].copy()
    entities.physiology_sensor_multiplier[active] = multipliers.sensor
    assert not np.array_equal(entities.sensor_quality()[active], baseline_sensor)
    before_material = float(entities.material[active].sum())
    before_energy = float(entities.energy[active].sum())
    stats = apply_physiology_step(
        entities,
        active,
        output_q=output_q,
        local_oxygen=np.full(active.size, 0.9),
        local_terrain=np.full(active.size, 0.8),
        local_wear=np.full(active.size, 0.4),
        moved=np.ones(active.size, dtype=bool),
        signaled=np.ones(active.size, dtype=bool),
        cfg=cfg,
    )
    assert stats.repair_material > 0.0
    assert stats.repair_energy > 0.0
    assert np.isclose(before_material - float(entities.material[active].sum()), stats.repair_material, atol=1e-6)
    assert before_energy - float(entities.energy[active].sum()) >= stats.repair_energy + stats.perfusion_energy - 1e-6
    assert stats.wear_tissue_damage > 0.0
    assert stats.wear_structure_damage > 0.0


def test_d2k_runner_reports_trends_without_pass_fail_gate(tmp_path: Path) -> None:
    cfg = load_config(CONFIG)
    result = execute_physiological_ecology(
        cfg,
        [50001],
        tmp_path,
        backend="cpu",
        until_tick=10,
    )
    assert result["schema"] == "d2-physiological-ecology-results-v1"
    assert result["plan"]["pass_fail_gate"] is False
    assert result["plan"]["module_expression_threshold_not_used_as_continuation_gate"] is True
    assert result["stable_trend_summary"]["dynamic_oxygenation_in_every_seed"] is True
    assert result["stable_trend_summary"]["abiotic_field_dimension_above_one_in_every_seed"] is True
    assert result["stable_trend_summary"]["repair_flow_observed"] is True
    assert result["runs"][0]["final"]["mean_physiology_sensor_multiplier"] != 1.0
