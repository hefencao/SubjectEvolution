from __future__ import annotations

from dataclasses import replace
import json
from pathlib import Path

import numpy as np
import pytest

from se.analysis.long_run import analyze
from se.analysis.protocol_audit import build_protocol_audit, render_markdown as render_protocol_markdown
from se.cfg import load_config, validate_config
from se.differentiation.functional import (
    FUNCTIONAL_MODULE_SCHEMA,
    GENES_PER_MODULE,
    INPUT_COUNT,
    contextual_harvest_preference_q,
    evaluate_contextual_harvest_modules_q,
    functional_module_diagnostics,
    expression_gates_q,
    functional_module_energy,
)
from se.env.niches import AFFINITY_SCALE
from se.policy import ParametricPolicy
from se.runtime.sim import Simulation


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "configs" / "d2a_contextual_harvest_smoke.json"


def _configured_genotype():
    cfg = load_config(CONFIG)
    size = ParametricPolicy.genome_size_for_config(cfg)
    start = ParametricPolicy.functional_module_gene_start(cfg)
    genotype = np.zeros((1, size), dtype=np.float32)
    module = start
    genotype[0, module] = 0.8
    # Route energy deficit through module 0 toward harvest channel 1.
    genotype[0, module + 1 + 1] = 0.8
    output = module + 2 + INPUT_COUNT
    genotype[0, output : output + 4] = (-0.8, 0.8, -0.8, -0.8)
    return cfg, genotype, start


def test_contextual_modules_preserve_budget_and_respond_to_state() -> None:
    cfg, genotype, start = _configured_genotype()
    base = np.full((1, 4), AFFINITY_SCALE, dtype=np.int32)
    common = dict(
        genotype=genotype,
        base_affinity_q=base,
        integrity=np.asarray([1.0]),
        material=np.asarray([0.0]),
        information_store=np.asarray([0.0]),
        fertility=np.asarray([0.25]),
        local_resources=np.full((1, 4), 4.0),
        cfg=cfg,
        gene_start=start,
    )
    low_energy = contextual_harvest_preference_q(
        energy=np.asarray([0.1]), **common
    )
    high_energy = contextual_harvest_preference_q(
        energy=np.asarray([4.9]), **common
    )
    ablated = contextual_harvest_preference_q(
        energy=np.asarray([0.1]), ablated=True, **common
    )
    assert int(low_energy.sum()) == 4 * AFFINITY_SCALE
    assert int(high_energy.sum()) == 4 * AFFINITY_SCALE
    assert low_energy[0, 1] > high_energy[0, 1]
    assert np.array_equal(ablated, base)


def test_expression_costs_are_explicit_and_separate() -> None:
    cfg, genotype, start = _configured_genotype()
    gates = expression_gates_q(genotype, cfg, gene_start=start)
    assert gates.shape == (1, cfg.functional_modules.module_count)
    maintenance = functional_module_energy(genotype, cfg, gene_start=start)
    development = functional_module_energy(
        genotype, cfg, gene_start=start, development=True
    )
    assert maintenance[0] > 0.0
    assert development[0] > maintenance[0]
    assert development[0] / maintenance[0] == pytest.approx(
        cfg.functional_modules.development_energy_per_expression
        / cfg.functional_modules.maintenance_energy_per_expression
    )


def test_d2_validation_requires_bounded_existing_ports() -> None:
    cfg = load_config(CONFIG)
    assert cfg.functional_modules.schema == FUNCTIONAL_MODULE_SCHEMA
    assert ParametricPolicy.genome_size_for_config(cfg) == (
        ParametricPolicy.functional_module_gene_start(cfg)
        + cfg.functional_modules.module_count * GENES_PER_MODULE
    )
    with pytest.raises(ValueError, match="exactly 4"):
        validate_config(
            replace(
                cfg,
                functional_modules=replace(cfg.functional_modules, module_count=3),
            )
        )
    with pytest.raises(ValueError, match="selective harvest"):
        validate_config(
            replace(
                cfg,
                entities=replace(cfg.entities, harvest_allocation_schema="uniform-channel-rates-v1"),
            )
        )


def test_d2_intervention_persists_through_checkpoint_and_is_analyzed(
    tmp_path: Path,
) -> None:
    cfg = load_config(CONFIG)
    cfg = replace(
        cfg,
        run=replace(
            cfg.run,
            ticks=6,
            metrics_period=3,
            checkpoint_period=99,
            checkpoint_ticks=(3,),
            full_checkpoint_enabled=True,
            evolution_evaluation_period=3,
        ),
        world=replace(cfg.world, initial_entities=32, max_entities=48),
    )
    validate_config(cfg)
    source = tmp_path / "source"
    simulation = Simulation(cfg, source, backend="cpu")
    simulation.apply_intervention("neutralize-functional-modules")
    simulation.run(until_tick=3)
    checkpoint = source / "checkpoint_00000003.sechk"
    restored = Simulation.from_checkpoint(checkpoint, tmp_path / "restored", until_tick=6)
    assert restored.functional_modules_ablation_enabled is True
    restored.run(until_tick=6)

    report = analyze([source / "evolution_progress.jsonl"])
    assert report["schema"] == "multi-seed-long-run-analysis-v15"
    final = report["runs"][0]["functional_module_final"]
    assert final["functional_module_schema"] == FUNCTIONAL_MODULE_SCHEMA
    protocol = build_protocol_audit(CONFIG)
    assert protocol["schema"] == "structural-measurement-protocol-audit-v15"
    functional = protocol["functional_module_protocol"]
    assert functional["action_selection"] is False
    assert functional["new_world_physics"] is False
    assert functional["neutralization_interventions"]["all_modules"] == "neutralize-functional-modules"
    assert functional["contribution_diagnostics"]["feedback_to_world"] is False
    assert functional["leave_one_out_protocol"]["result_schema"] == (
        "d2-module-leave-one-out-results-v2"
    )
    assert functional["effect_qualification"]["schema"] == (
        "d2-module-effect-assessment-v2"
    )
    lineage_pairs = functional["lineage_balanced_pair_protocol"]
    assert lineage_pairs["result_schema"] == "d2-lineage-paired-results-v2"
    assert lineage_pairs["effect_assessment"]["schema"] == (
        "d2-lineage-paired-assessment-v1"
    )
    assert lineage_pairs["effect_assessment"]["outcome_conditioned_pair_selection"] is False
    mediation = lineage_pairs["temporal_mediation_audit"]
    assert mediation["plan_schema"] == "d2-lineage-mediation-plan-v1"
    assert mediation["assessment_schema"] == "d2-lineage-mediation-assessment-v1"
    assert mediation["offsets_are_independent_replicates"] is False
    assert mediation["mean_energy_alone_qualifies_as_ecological_benefit"] is False
    assert mediation["outcome_conditioned_pair_selection"] is False
    source_population = lineage_pairs["source_population_reconstitution"]
    assert source_population["assessment_schema"] == "d2-source-population-assessment-v2"
    assert source_population["charter_interpretation"][
        "ten_seed_floor_applies_to_every_exploratory_audit"
    ] is False
    causal_reaudit = lineage_pairs["source_population_causal_reaudit"]
    assert causal_reaudit["plan_schema"] == "d2-source-population-causal-plan-v1"
    assert causal_reaudit["module_copy_number_changed"] is False
    assert causal_reaudit["response_conditioned_lineage_selection"] is False
    assert lineage_pairs["diversity_protection"] is False


def test_d2b_per_module_contribution_and_partial_ablation() -> None:
    cfg, genotype, start = _configured_genotype()
    base = np.full((1, 4), AFFINITY_SCALE, dtype=np.int32)
    kwargs = dict(
        energy=np.asarray([0.1]),
        integrity=np.asarray([1.0]),
        material=np.asarray([0.0]),
        information_store=np.asarray([0.0]),
        fertility=np.asarray([0.25]),
        local_resources=np.full((1, 4), 4.0),
        cfg=cfg,
        gene_start=start,
    )
    evaluation = evaluate_contextual_harvest_modules_q(
        genotype, base, **kwargs
    )
    direct = contextual_harvest_preference_q(genotype, base, **kwargs)
    assert np.array_equal(evaluation.preference_q, direct)
    assert evaluation.module_residual_q.shape == (1, 4, 4)
    assert np.any(evaluation.module_residual_q[:, 0] != 0)
    assert np.all(evaluation.module_residual_q[:, 1:] == 0)

    mask = np.asarray([True, False, False, False])
    ablated = evaluate_contextual_harvest_modules_q(
        genotype, base, ablated_modules=mask, **kwargs
    )
    assert np.array_equal(ablated.preference_q, base)
    assert ablated.ablation_mask.tolist() == mask.tolist()

    diagnostics = functional_module_diagnostics(
        genotype,
        evaluation.preference_q,
        base,
        cfg,
        gene_start=start,
        evaluation=evaluation,
    )
    assert diagnostics["functional_module_contribution_diagnostic_schema"] == (
        "functional-module-contribution-audit-v1"
    )
    assert diagnostics["functional_module_contribution_effective_count"] == pytest.approx(1.0)
    assert diagnostics["functional_module_contribution_share"][0] == pytest.approx(1.0)
    assert diagnostics["functional_module_nonzero_entity_fraction_by_module"][0] == 1.0
    assert diagnostics["functional_module_nonzero_entity_fraction_by_module"][1:] == [0.0, 0.0, 0.0]

    full_cost = functional_module_energy(genotype, cfg, gene_start=start)
    partial_cost = functional_module_energy(
        genotype, cfg, gene_start=start, ablated_modules=mask
    )
    assert full_cost[0] > 0.0
    assert partial_cost[0] == 0.0


def test_d2b_partial_intervention_persists(tmp_path: Path) -> None:
    cfg = load_config(CONFIG)
    cfg = replace(
        cfg,
        run=replace(
            cfg.run,
            ticks=4,
            checkpoint_period=99,
            checkpoint_ticks=(2,),
            full_checkpoint_enabled=True,
            evolution_evaluation_period=2,
        ),
        world=replace(cfg.world, initial_entities=24, max_entities=32),
    )
    sim = Simulation(cfg, tmp_path / "source", backend="cpu")
    genotype_before = sim.entities.genotype.copy()
    sim.apply_intervention("neutralize-functional-module-2")
    assert sim.functional_modules_ablation_enabled is False
    assert sim.functional_module_ablation_mask.tolist() == [False, False, True, False]
    assert np.array_equal(sim.entities.genotype, genotype_before)
    sim.run(until_tick=2)
    restored = Simulation.from_checkpoint(
        tmp_path / "source" / "checkpoint_00000002.sechk",
        tmp_path / "restored",
        until_tick=4,
    )
    assert restored.functional_module_ablation_mask.tolist() == [False, False, True, False]
    assert restored.functional_modules_ablation_enabled is False
