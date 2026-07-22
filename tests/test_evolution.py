from __future__ import annotations

from dataclasses import replace
import json

import numpy as np

from subject_evolution.config import load_config
from subject_evolution.evolution import (
    BenefitFlowKind,
    benefit_flow_totals,
    strategy_structure,
)
from subject_evolution.lifecycle import BirthRequestPlan, plan_birth_allocations
from subject_evolution.policy import Action, ParametricPolicy, PolicyDecision
from subject_evolution.simulation import Simulation


def _small_config():
    cfg = load_config("configs/mvp_small.json")
    return replace(
        cfg,
        world=replace(cfg.world, initial_entities=32, max_entities=64),
        run=replace(
            cfg.run,
            ticks=2,
            metrics_period=99,
            checkpoint_period=99,
            evolution_evaluation_period=2,
        ),
    )


def test_canonical_strategy_diversity_removes_softmax_common_offsets() -> None:
    count = 2
    genotype = np.zeros((count, ParametricPolicy.GENOME_SIZE), dtype=np.float32)
    strategy = genotype[:, ParametricPolicy.MORPHOLOGY_TRAITS :].reshape(
        count,
        len(Action),
        ParametricPolicy.STRATEGY_FEATURES,
    )
    strategy[1, :, :] = 0.7

    measured, _ = strategy_structure(
        np.ones(count, dtype=bool),
        np.asarray([10, 20], dtype=np.uint64),
        genotype,
        run_seed=3,
        temperature=0.8,
    )

    assert measured["raw_strategy_diversity"] > 0.3
    assert measured["canonical_strategy_diversity"] < 1e-7
    assert measured["policy_probability_diversity"] < 1e-7


def test_benefit_flow_partition_is_exhaustive() -> None:
    measured = benefit_flow_totals(
        np.asarray([10, 10, 10, 0, 0], dtype=np.uint64),
        np.asarray([10, 20, 0, 20, 0], dtype=np.uint64),
        np.asarray([1, 2, 3, 4, 5], dtype=np.float32),
    )

    assert measured[BenefitFlowKind.INTERNAL] == 1.0
    assert measured[BenefitFlowKind.GROUP_TO_GROUP] == 2.0
    assert measured[BenefitFlowKind.GROUP_TO_UNGROUPED] == 3.0
    assert measured[BenefitFlowKind.UNGROUPED_TO_GROUP] == 4.0
    assert measured[BenefitFlowKind.UNBOUNDED] == 5.0
    assert measured.sum() == 15.0


def test_reproduction_diagnostics_separate_capacity_rejection(tmp_path) -> None:
    cfg = _small_config()
    cfg = replace(cfg, world=replace(cfg.world, max_entities=40))
    sim = Simulation(cfg, tmp_path / "reproduction")
    active = np.flatnonzero(sim.entities.alive).astype(np.int32)
    sim.entities.energy[active] = cfg.entities.max_energy
    sim.entities.fertility[active] = 1.0

    def reproduce(**kwargs):
        count = kwargs["active"].size
        return PolicyDecision(
            action=np.full(count, Action.REPRODUCE, dtype=np.int16),
            probability=np.ones(count, dtype=np.float32),
            entropy=np.zeros(count, dtype=np.float32),
            direction_x=np.zeros(count, dtype=np.float32),
            direction_y=np.zeros(count, dtype=np.float32),
            selected_partner=np.full(count, -1, dtype=np.int32),
            logits=np.zeros((count, len(Action)), dtype=np.float32),
        )

    sim.policy.decide = reproduce
    try:
        stats = sim.step()
        assert stats.reproduction_eligible == 32
        assert stats.reproduction_proposals == 32
        assert stats.reproduction_accepted == 8
        assert stats.reproduction_rejected_capacity == 24
        assert stats.reproduction_rejected_resource == 0
        assert stats.reproduction_rejected_other == 0
        assert sim.total_reproduction_proposals == 32
        assert sim.total_reproduction_rejected_capacity == 24
    finally:
        sim.metrics.close()
        sim.evolution_progress.close()


def test_default_mutation_is_sparse_and_tracks_generation(tmp_path) -> None:
    sim = Simulation(_small_config(), tmp_path / "mutation")
    count = 16
    parents = np.arange(count, dtype=np.int32)
    requests = BirthRequestPlan(
        source_rows=np.arange(count, dtype=np.int32),
        parent_indices=parents,
        parent_entity_ids=sim.entities.entity_id[parents].copy(),
        parent_subject_ids=sim.entities.primary_subject_id[parents].copy(),
        tick=1,
    )
    plan = plan_birth_allocations(
        requests,
        sim.entities.free_slots,
        int(sim.entities.next_entity_id),
        sim.entities.free_slot_version,
    )
    parent_genotype = sim.entities.genotype[parents].copy()
    try:
        accepted, newborns = sim.entities.commit_births(plan)
        changed = sim.entities.genotype[newborns] != parent_genotype
        assert 0 < np.count_nonzero(changed) < changed.size * 0.05
        np.testing.assert_array_equal(
            sim.entities.generation[newborns],
            sim.entities.generation[accepted] + 1,
        )
    finally:
        sim.metrics.close()
        sim.evolution_progress.close()


def test_evolution_progress_uses_independent_fixed_cadence(tmp_path) -> None:
    output = tmp_path / "progress"
    sim = Simulation(_small_config(), output)
    sim.run()

    records = [
        json.loads(line)
        for line in (output / "evolution_progress.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
    ]
    metadata = json.loads(
        (output / "run_metadata.json").read_text(encoding="utf-8")
    )
    assert len(records) == 1
    assert records[0]["tick"] == 2
    assert records[0]["scheduled"] is True
    assert records[0]["expected_strategy_genes_mutated_per_birth"] == 1.28
    assert 0.0 <= records[0]["effective_lineages_per_alive"] <= 1.0
    assert records[0]["mean_strategy_shift_from_initial_l2"] >= 0.0
    assert records[0]["reproduction_accounting_residual_window"] == 0
    assert abs(records[0]["benefit_classification_residual_window"]) < 1e-5
    assert "benefit_boundary_coverage" in records[0]
    assert "benefit_boundary_outgoing_retention" in records[0]
    assert "canonical_strategy_diversity" in records[0]
    assert "policy_probability_diversity" in records[0]
    assert metadata["evolution_progress"]["period"] == 2
    assert metadata["evolution_progress"]["evaluations"] == 1
