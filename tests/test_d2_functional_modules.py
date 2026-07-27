from __future__ import annotations

from dataclasses import replace
import json
from pathlib import Path

import numpy as np
import pytest

from se.analysis.long_run import analyze
from se.analysis.protocol_audit import build_protocol_audit
from se.cfg import load_config, validate_config
from se.differentiation.functional import (
    FUNCTIONAL_MODULE_SCHEMA,
    GENES_PER_MODULE,
    INPUT_COUNT,
    contextual_harvest_preference_q,
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
    assert report["schema"] == "multi-seed-long-run-analysis-v14"
    final = report["runs"][0]["functional_module_final"]
    assert final["functional_module_schema"] == FUNCTIONAL_MODULE_SCHEMA
    protocol = build_protocol_audit(CONFIG)
    assert protocol["schema"] == "structural-measurement-protocol-audit-v7"
    functional = protocol["functional_module_protocol"]
    assert functional["action_selection"] is False
    assert functional["new_world_physics"] is False
    assert functional["neutralization_intervention"] == "neutralize-functional-modules"
