from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest

from se.analysis.protocol_audit import build_protocol_audit
from se.cfg import load_config, validate_config
from se.differentiation.functional import (
    EMBODIED_FUNCTIONAL_MODULE_SCHEMA,
    EMBODIED_GENES_PER_MODULE,
    EMBODIED_OUTPUT_COUNT,
    EMBODIED_OUTPUT_SCHEMA,
    evaluate_contextual_harvest_modules_q,
    functional_module_coupling_count,
    functional_module_diagnostics,
    functional_module_energy,
)
from se.env.niches import AFFINITY_SCALE
from se.experiments.d2_embodied_capability import execute_embodied_capability
from se.policy import ParametricPolicy
from se.runtime.sim import Simulation

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "configs" / "d2j_embodied_modules_smoke.json"


def _configured_v3_genotype():
    cfg = load_config(CONFIG)
    size = ParametricPolicy.genome_size_for_config(cfg)
    start = ParametricPolicy.functional_module_gene_start(cfg)
    genotype = np.zeros((1, size), dtype=np.float32)
    module = start
    genotype[0, module] = 0.8  # expressed gate
    genotype[0, module + 1 + 10] = 0.8  # positive context bias
    harvest = module + 2 + 10
    genotype[0, harvest : harvest + 4] = (-0.8, 0.8, -0.8, -0.8)
    embodied = harvest + 4
    genotype[0, embodied : embodied + EMBODIED_OUTPUT_COUNT] = (0.8, -0.6, 0.7)
    return cfg, genotype, start


def _evaluation_inputs():
    return {
        "energy": np.asarray([1.0]),
        "integrity": np.asarray([0.5]),
        "material": np.asarray([1.0]),
        "information_store": np.asarray([0.0]),
        "fertility": np.asarray([0.2]),
        "local_resources": np.full((1, 4), 4.0),
    }


def test_v3_layout_and_output_schema_are_explicit() -> None:
    cfg = load_config(CONFIG)
    validate_config(cfg)
    assert cfg.functional_modules.schema == EMBODIED_FUNCTIONAL_MODULE_SCHEMA
    assert cfg.functional_modules.output_schema == EMBODIED_OUTPUT_SCHEMA
    assert ParametricPolicy.genome_size_for_config(cfg) == (
        ParametricPolicy.functional_module_gene_start(cfg)
        + cfg.functional_modules.module_count * EMBODIED_GENES_PER_MODULE
        + functional_module_coupling_count(cfg)
    )


def test_embodied_output_ablation_preserves_harvest_and_structure_cost() -> None:
    cfg, genotype, start = _configured_v3_genotype()
    base = np.full((1, 4), AFFINITY_SCALE, dtype=np.int32)
    active = evaluate_contextual_harvest_modules_q(
        genotype,
        base,
        cfg=cfg,
        gene_start=start,
        **_evaluation_inputs(),
    )
    neutral = evaluate_contextual_harvest_modules_q(
        genotype,
        base,
        cfg=cfg,
        gene_start=start,
        embodied_ablated=True,
        **_evaluation_inputs(),
    )
    assert np.array_equal(active.preference_q, neutral.preference_q)
    assert np.any(active.embodied_output_q != 0)
    assert np.all(neutral.embodied_output_q == 0)
    assert neutral.embodied_output_ablation_enabled is True
    assert functional_module_energy(genotype, cfg, gene_start=start)[0] > 0.0

    diagnostics = functional_module_diagnostics(
        genotype,
        active.preference_q,
        base,
        cfg,
        gene_start=start,
        evaluation=active,
    )
    assert diagnostics["functional_module_contribution_diagnostic_schema"] == (
        "functional-module-contribution-audit-v3"
    )
    assert diagnostics["functional_embodied_output_changed_entity_fraction"] == 1.0
    assert any(
        value > 0.0
        for value in diagnostics["functional_embodied_output_abs_mean_by_port"]
    )
    assert len(diagnostics["functional_output_basis_port_names"]) == 7


def test_embodied_intervention_persists_without_genotype_edit(tmp_path: Path) -> None:
    cfg = load_config(CONFIG)
    cfg = replace(
        cfg,
        run=replace(
            cfg.run,
            ticks=3,
            checkpoint_period=99,
            checkpoint_ticks=(1,),
            full_checkpoint_enabled=True,
            metrics_period=1,
            evolution_evaluation_period=1,
        ),
        world=replace(cfg.world, initial_entities=24, max_entities=32),
    )
    simulation = Simulation(cfg, tmp_path / "source", backend="cpu")
    before = simulation.entities.genotype.copy()
    simulation.apply_intervention(
        "neutralize-functional-module-embodied-output"
    )
    assert simulation.functional_module_embodied_output_ablation_enabled is True
    assert np.array_equal(before, simulation.entities.genotype)
    simulation.run(until_tick=1)
    restored = Simulation.from_checkpoint(
        tmp_path / "source" / "checkpoint_00000001.sechk",
        tmp_path / "restored",
        until_tick=3,
    )
    assert restored.functional_module_embodied_output_ablation_enabled is True
    assert np.array_equal(before, restored.entities.genotype)


def test_d2j_runner_uses_primitives_and_keeps_neutral_output_zero(
    tmp_path: Path,
) -> None:
    cfg = load_config(CONFIG)
    cfg = replace(
        cfg,
        run=replace(
            cfg.run,
            ticks=4,
            metrics_period=1,
            evolution_evaluation_period=1,
            checkpoint_period=99,
            checkpoint_ticks=(),
        ),
        world=replace(cfg.world, initial_entities=32, max_entities=48),
    )
    result = execute_embodied_capability(
        cfg,
        (49001,),
        tmp_path / "result",
        backend="cpu",
        until_tick=4,
    )
    assert result["schema"] == "d2-embodied-capability-results-v1"
    assert result["plan"]["same_v3_genome_in_both_branches"] is True
    assert result["plan"]["embodied_router_structure_cost_retained_when_neutral"] is True
    pair = result["pairs"][0]
    active = pair["branches"]["embodied-active"]["final"]
    neutral = pair["branches"]["embodied-neutral"]["final"]
    assert active["functional_embodied_output_changed_entity_fraction"] > 0.0
    assert neutral["functional_embodied_output_changed_entity_fraction"] == 0.0
    assert neutral["functional_module_signal_energy_delta_total"] == 0.0
    assert neutral["functional_module_movement_energy_delta_total"] == 0.0
    assert neutral["functional_module_repair_material_total"] == 0.0
    assert active["functional_output_basis_active_port_count"] > 0
    usage = result["summary"]["primitive_usage"]
    assert usage["active_output_in_every_seed"] is True
    assert usage["neutral_output_zero_in_every_seed"] is True


def test_repair_primitive_conserves_material_energy_and_integrity() -> None:
    from types import SimpleNamespace

    from se.runtime.embodied import apply_material_repair

    cfg = load_config(CONFIG)
    entities = SimpleNamespace(
        material=np.asarray([0.5], dtype=np.float32),
        energy=np.asarray([1.0], dtype=np.float32),
        integrity=np.asarray([0.5], dtype=np.float32),
    )
    output = np.asarray([[0, 0, 4096]], dtype=np.int32)
    result = apply_material_repair(
        entities, np.asarray([0], dtype=np.int32), output, cfg
    )
    assert result.material == cfg.functional_modules.repair_material_per_tick
    assert result.energy == (
        result.material * cfg.functional_modules.repair_energy_per_material
    )
    assert result.integrity == (
        result.material * cfg.functional_modules.repair_integrity_per_material
    )
    assert float(entities.material[0]) == pytest.approx(0.5 - result.material)
    assert float(entities.energy[0]) == pytest.approx(1.0 - result.energy)
    assert float(entities.integrity[0]) == pytest.approx(0.5 + result.integrity)


def test_v3_protocol_audit_records_physical_and_causal_boundaries() -> None:
    audit = build_protocol_audit(CONFIG)
    assert audit["schema"] == "structural-measurement-protocol-audit-v47"
    protocol = audit["functional_module_protocol"]
    assert protocol["architecture_class"] == "feed-forward-compositional-embodied"
    assert protocol["new_world_physics"] is True
    assert protocol["embodied_output_semantics"]["resource_or_energy_created"] is False
    assert protocol["embodied_output_semantics"]["preset_ecological_role"] is False
    assert protocol["neutralization_interventions"]["embodied_output"] == (
        "neutralize-functional-module-embodied-output"
    )
    assert protocol["embodied_capability_experiment"]["module_copy_number_changed"] is False
