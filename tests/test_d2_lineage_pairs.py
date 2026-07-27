from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import numpy as np

from se.cfg import load_config
from se.differentiation.functional import (
    evaluate_contextual_harvest_modules_q,
    functional_module_energy,
)
from se.env.niches import AFFINITY_SCALE
from se.experiments.d2_lineage_pairs import (
    PLAN_SCHEMA,
    RESULT_SCHEMA,
    build_lineage_pair_plan,
    execute_lineage_pair_plan,
    load_lineage_pair_plan,
)
from se.experiments.d2_module_audit import RESULT_SCHEMA as D2_AUDIT_RESULT_SCHEMA
from se.policy import ParametricPolicy
from se.runtime.sim import Simulation


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "configs" / "d2a_contextual_harvest_smoke.json"


def _strong_module_genotype(cfg, rows: int) -> np.ndarray:
    size = ParametricPolicy.genome_size_for_config(cfg)
    start = ParametricPolicy.functional_module_gene_start(cfg)
    genotype = np.zeros((rows, size), dtype=np.float32)
    genotype[:, start] = 0.9
    genotype[:, start + 2] = 0.9
    output = start + 12
    genotype[:, output : output + 4] = (-0.9, 0.9, -0.9, -0.9)
    return genotype


def test_row_ablation_targets_output_and_cost_independently() -> None:
    cfg = load_config(CONFIG)
    genotype = _strong_module_genotype(cfg, 2)
    start = ParametricPolicy.functional_module_gene_start(cfg)
    base = np.full((2, 4), AFFINITY_SCALE, dtype=np.int32)
    row_mask = np.zeros((2, 4), dtype=bool)
    row_mask[1, 0] = True
    evaluation = evaluate_contextual_harvest_modules_q(
        genotype,
        base,
        energy=np.asarray([0.1, 0.1]),
        integrity=np.asarray([1.0, 1.0]),
        material=np.asarray([0.0, 0.0]),
        information_store=np.asarray([0.0, 0.0]),
        fertility=np.asarray([0.25, 0.25]),
        local_resources=np.full((2, 4), 4.0),
        cfg=cfg,
        gene_start=start,
        row_ablated_modules=row_mask,
    )
    assert not np.array_equal(evaluation.preference_q[0], base[0])
    assert np.array_equal(evaluation.preference_q[1], base[1])

    full_cost = functional_module_energy(genotype, cfg, gene_start=start)
    targeted_cost = functional_module_energy(
        genotype,
        cfg,
        gene_start=start,
        row_ablated_modules=row_mask,
    )
    assert targeted_cost[0] == full_cost[0]
    assert targeted_cost[1] < full_cost[1]


def test_lineage_intervention_persists_without_editing_genotype(tmp_path: Path) -> None:
    cfg = load_config(CONFIG)
    cfg = replace(
        cfg,
        run=replace(
            cfg.run,
            ticks=2,
            full_checkpoint_enabled=True,
            checkpoint_ticks=(1,),
            checkpoint_period=99,
            evolution_evaluation_period=1,
        ),
        world=replace(cfg.world, initial_entities=16, max_entities=24),
    )
    simulation = Simulation(cfg, tmp_path / "source", backend="cpu")
    active = np.flatnonzero(simulation.entities.alive)
    lineage_id = int(simulation.entities.lineage_id[active[0]])
    genotype_before = simulation.entities.genotype.copy()
    lineage_before = simulation.entities.lineage_id.copy()
    simulation.apply_functional_module_lineage_intervention(
        module_index=0,
        lineage_id=lineage_id,
        neutralize_cost=True,
    )
    assert np.array_equal(simulation.entities.genotype, genotype_before)
    assert np.array_equal(simulation.entities.lineage_id, lineage_before)
    simulation.run(until_tick=1)

    restored = Simulation.from_checkpoint(
        tmp_path / "source" / "checkpoint_00000001.sechk",
        tmp_path / "restored",
        backend="cpu",
        until_tick=2,
    )
    assert restored.functional_module_lineage_output_ablation == {0: {lineage_id}}
    assert restored.functional_module_lineage_cost_ablation == {0: {lineage_id}}
    validity = restored.scientific_validity()
    assert validity["structural_evolution_provenance_valid"] is True
    assert validity["strict_unintervened_baseline"] is False


def test_lineage_pair_plan_and_execution_use_shared_checkpoint(tmp_path: Path) -> None:
    cfg = load_config(CONFIG)
    cfg = replace(
        cfg,
        run=replace(
            cfg.run,
            ticks=1,
            full_checkpoint_enabled=True,
            checkpoint_ticks=(),
            checkpoint_period=99,
            evolution_evaluation_period=1,
            metrics_period=1,
        ),
        world=replace(cfg.world, initial_entities=24, max_entities=32),
    )
    source = tmp_path / "source"
    simulation = Simulation(cfg, source, backend="cpu")
    active = np.flatnonzero(simulation.entities.alive)
    simulation.entities.genotype[active] = _strong_module_genotype(cfg, active.size)
    simulation.entities.lineage_id[active[:10]] = np.uint64(101)
    simulation.entities.lineage_id[active[10:18]] = np.uint64(202)
    simulation.entities.lineage_id[active[18:]] = np.uint64(303)
    checkpoint = simulation.save_full_checkpoint()

    source_results = {
        "schema": D2_AUDIT_RESULT_SCHEMA,
        "plan": {"horizon_ticks": 300},
        "checkpoints": [
            {
                "checkpoint": {
                    "run_name": "seed_test",
                    "phase": "peak",
                    "checkpoint_tick": 0,
                    "checkpoint_path": str(checkpoint),
                }
            }
        ],
    }
    plan = build_lineage_pair_plan(
        source_results,
        horizon_ticks=1,
        module_indices=(0,),
        min_lineage_members=4,
        min_lineages_per_checkpoint=3,
        max_lineages_per_checkpoint=3,
    )
    assert plan.schema == PLAN_SCHEMA
    selected = plan.checkpoints[0].lineages
    assert [item.lineage_id for item in selected] == [101, 202, 303]
    assert [item.members for item in selected] == [10, 8, 6]
    assert plan.checkpoints[0].eligible is True

    plan_path = tmp_path / "plan.json"
    from dataclasses import asdict
    import json

    plan_path.write_text(json.dumps(asdict(plan)), encoding="utf-8")
    assert load_lineage_pair_plan(plan_path) == plan

    report = execute_lineage_pair_plan(plan, tmp_path / "audit", backend="cpu")
    assert report["schema"] == RESULT_SCHEMA
    assert report["executed_pair_count"] == 3
    rows = report["checkpoints"][0]["pairs"]
    assert len(rows) == 3
    for row in rows:
        assert set(row["branches"]) == {
            "baseline",
            "output-neutral",
            "expression-neutral",
        }
        assert all(
            abs(value) <= 1e-12
            for value in row["effects"]["decomposition_residual"].values()
        )
        output_history = row["branches"]["output-neutral"]["intervention_history"]
        expression_history = row["branches"]["expression-neutral"]["intervention_history"]
        assert output_history[-1]["expression_cost_neutralized"] is False
        assert expression_history[-1]["expression_cost_neutralized"] is True


def test_v1_lineage_pair_plan_remains_loadable(tmp_path: Path) -> None:
    import json

    payload = {
        "schema": "d2-lineage-paired-plan-v1",
        "horizon_ticks": 120,
        "module_indices": [2, 3],
        "min_lineage_members": 8,
        "min_lineages_per_checkpoint": 3,
        "max_lineages_per_checkpoint": 4,
        "checkpoints": [
            {
                "run_name": "seed_test",
                "phase": "peak",
                "checkpoint_tick": 100,
                "checkpoint_path": "/tmp/source.sechk",
                "until_tick": 220,
                "active_entities": 100,
                "effective_lineages": 2.0,
                "dominant_lineage_fraction": 0.7,
                "eligible": True,
                "ineligible_reason": None,
                "lineages": [
                    {
                        "lineage_id": 1,
                        "members": 70,
                        "member_fraction": 0.7,
                        "abundance_rank": 1,
                    },
                    {
                        "lineage_id": 2,
                        "members": 15,
                        "member_fraction": 0.15,
                        "abundance_rank": 2,
                    },
                    {
                        "lineage_id": 3,
                        "members": 8,
                        "member_fraction": 0.08,
                        "abundance_rank": 3,
                    },
                ],
            }
        ],
        "lineage_selection_rule": "largest-preintervention-lineages-by-membership-v1",
        "paired_randomness": True,
        "genotype_preserved": True,
        "lineage_membership_preserved": True,
        "abundance_weighted_inference": False,
        "branches": ["baseline", "output-neutral", "expression-neutral"],
        "effect_decomposition_schema": "output-cost-total-additive-v1",
    }
    path = tmp_path / "v1_plan.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    plan = load_lineage_pair_plan(path)
    assert plan.schema == "d2-lineage-paired-plan-v1"
    assert plan.confirmation_source_horizon_ticks is None
    assert plan.outcome_conditioned_pair_selection is False
