from __future__ import annotations

from dataclasses import replace
from pathlib import Path
import tempfile

import numpy as np

from se.cfg import load_config
from se.differentiation.capacity import capacity_phenotype, neutral_capacity_phenotype
from se.knowledge.system import KnowledgeSystem
from se.knowledge.working_memory import build_working_memory_update
from se.policy import ParametricPolicy
from se.runtime.sim import Simulation
from se.subjects.social import SocialSystem

ROOT = Path(__file__).resolve().parents[1]


def d1_cfg():
    return load_config(ROOT / "configs" / "d1_elastic_capacities_smoke.json")


def test_capacity_genes_extend_genome_without_overlapping_existing_regions() -> None:
    cfg = d1_cfg()
    start = ParametricPolicy.capacity_gene_start(cfg)
    assert ParametricPolicy.genome_size_for_config(cfg) == start + 4
    assert start >= ParametricPolicy.sparse_selection_gene_start(cfg)

    genotype = np.zeros((2, ParametricPolicy.genome_size_for_config(cfg)), dtype=np.float32)
    genotype[0, start : start + 4] = -1.0
    genotype[1, start : start + 4] = 1.0
    phenotype = capacity_phenotype(genotype, cfg, gene_start=start)
    assert phenotype.working_memory_dimensions.tolist() == [0, 4]
    assert phenotype.knowledge_capacity_bytes.tolist() == [0, 512]
    assert phenotype.relation_slots.tolist() == [0, 8]
    assert phenotype.knowledge_attention_slots.tolist() == [0, 2]


def test_relation_capacity_masks_physical_relation_table() -> None:
    cfg = d1_cfg()
    social = SocialSystem(cfg, 4)
    social.set_effective_capacities(
        np.arange(4, dtype=np.int32), np.asarray([1, 0, 8, 8], dtype=np.int32)
    )
    social.record_shares(
        np.asarray([0, 0, 0, 1], dtype=np.int32),
        np.asarray([1, 2, 3, 2], dtype=np.int32),
        np.asarray([True, True, True, True]),
        tick=1,
    )
    assert np.count_nonzero(social.target[0] >= 0) == 1
    assert np.count_nonzero(social.target[1] >= 0) == 0
    assert np.all(social.target[0, 1:] == -1)


def test_knowledge_capacity_and_attention_are_entity_specific() -> None:
    cfg = d1_cfg()
    cfg = replace(
        cfg,
        knowledge=replace(
            cfg.knowledge,
            initial_content_count=2,
            initial_holders_fraction=1.0,
            transfer_probability=1.0,
        ),
        information=replace(
            cfg.information,
            channel_loss=0.0,
            classification_error=0.0,
        ),
    )
    with tempfile.TemporaryDirectory() as tmp:
        knowledge = KnowledgeSystem(
            cfg,
            tmp,
            initial_entity_ids=np.asarray([1, 2], dtype=np.uint64),
            initial_subject_ids=np.asarray([101, 102], dtype=np.uint64),
            initial_knowledge_capacities=np.asarray([0, 512], dtype=np.uint32),
        )
        assert knowledge.arena.rows_for_holder(101) == []
        assert knowledge.arena.rows_for_holder(102)

        empty = knowledge.plan_transfers(
            sender_entity_indices=np.asarray([1], dtype=np.int32),
            receiver_entity_indices=np.asarray([0], dtype=np.int32),
            entity_ids=np.asarray([1, 2], dtype=np.uint64),
            primary_subject_ids=np.asarray([101, 102], dtype=np.uint64),
            alive=np.asarray([True, True]),
            tick=0,
            attention_capacities=np.asarray([0, 2], dtype=np.uint16),
        )
        assert empty.size == 0
        assert empty.attention_rejected == 1

        plan = knowledge.plan_transfers(
            sender_entity_indices=np.asarray([1], dtype=np.int32),
            receiver_entity_indices=np.asarray([0], dtype=np.int32),
            entity_ids=np.asarray([1, 2], dtype=np.uint64),
            primary_subject_ids=np.asarray([101, 102], dtype=np.uint64),
            alive=np.asarray([True, True]),
            tick=0,
            attention_capacities=np.asarray([1, 2], dtype=np.uint16),
        )
        assert plan.size == 1
        energy = np.full(2, 10.0, dtype=np.float32)
        stats = knowledge.commit_transfers(
            plan,
            energy=energy,
            alive=np.asarray([True, True]),
            knowledge_capacities=np.asarray([0, 512], dtype=np.uint32),
        )
        assert stats.transfer_capacity_rejected == 1
        assert knowledge.arena.rows_for_holder(101) == []
        knowledge.close()


def test_working_memory_capacity_masks_dimensions_and_cost() -> None:
    cfg = d1_cfg()
    kcfg = replace(
        cfg.knowledge,
        working_memory_base_energy_cost=0.0,
        working_memory_energy_per_dimension=1.0,
        working_memory_energy_per_saturation=0.0,
    )
    width = kcfg.working_memory_width
    genotype = np.zeros((3, ParametricPolicy.genome_size_for_config(cfg)), dtype=np.float32)
    gene_start = ParametricPolicy.working_memory_gene_start(cfg)
    genotype[:, gene_start + 3 * width : gene_start + 4 * width] = 0.5
    result = build_working_memory_update(
        tick=1,
        active_rows=np.asarray([0, 1, 2], dtype=np.int32),
        entity_ids=np.asarray([1, 2, 3], dtype=np.uint64),
        previous_q=np.zeros((3, width), dtype=np.int16),
        previous_observation_q=np.zeros((3, 4), dtype=np.int16),
        current_state_features=np.ones((3, 4), dtype=np.float32),
        actual_outcomes=np.zeros((3, 5), dtype=np.float32),
        expected_outcomes=np.zeros((3, 5), dtype=np.float32),
        genotype=genotype,
        gene_start=gene_start,
        available_energy=np.full(3, 10.0),
        config=kcfg,
        effective_widths=np.asarray([0, 2, 4], dtype=np.int32),
    )
    assert result.requested_energy.tolist() == [0.0, 2.0, 4.0]
    assert result.accepted.tolist() == [False, True, True]
    assert np.all(result.committed_q[0] == 0)
    assert np.all(result.committed_q[1, 2:] == 0)
    assert np.any(result.committed_q[2] != 0)


def test_d1_checkpoint_continuation_is_exact() -> None:
    cfg = d1_cfg()
    cfg = replace(
        cfg,
        run=replace(
            cfg.run,
            ticks=12,
            metrics_period=12,
            checkpoint_period=6,
            full_checkpoint_enabled=False,
            validation_mode=True,
        ),
        world=replace(cfg.world, initial_entities=64, max_entities=96),
    )
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        continuous = Simulation(cfg, root / "continuous", backend="cpu")
        for _ in range(6):
            continuous.step()
        checkpoint = continuous.save_full_checkpoint(root / "d1_tick6.sechk")
        restored = Simulation.from_checkpoint(
            checkpoint, root / "restored", backend="cpu", until_tick=12
        )
        for _ in range(6):
            continuous.step()
            restored.step()
        left = continuous._full_checkpoint_state()
        right = restored._full_checkpoint_state()
        for name in (
            "working_memory_capacity",
            "knowledge_capacity_bytes",
            "relation_capacity",
            "knowledge_attention_capacity",
            "genotype",
            "energy",
        ):
            assert np.array_equal(
                getattr(left["entities"], name), getattr(right["entities"], name)
            )
        assert np.array_equal(
            left["social"].effective_capacity, right["social"].effective_capacity
        )
        for simulation in (continuous, restored):
            simulation.knowledge.close()
            simulation.evolution_progress.close()
            simulation.metrics.close()


def test_neutralize_elastic_capacities_changes_expression_not_genotype() -> None:
    cfg = d1_cfg()
    cfg = replace(
        cfg,
        run=replace(
            cfg.run,
            ticks=4,
            metrics_period=4,
            checkpoint_period=4,
            full_checkpoint_enabled=False,
            validation_mode=True,
        ),
        world=replace(cfg.world, initial_entities=48, max_entities=64),
    )
    with tempfile.TemporaryDirectory() as tmp:
        simulation = Simulation(cfg, tmp, backend="cpu")
        active = np.flatnonzero(simulation.entities.alive).astype(np.int32)
        genotype = simulation.entities.genotype.copy()
        simulation.apply_intervention("neutralize-elastic-capacities")
        expected = neutral_capacity_phenotype(active.size, cfg.differentiation)
        assert simulation.capacity_ablation_enabled
        assert np.array_equal(simulation.entities.genotype, genotype)
        assert np.array_equal(
            simulation.entities.working_memory_capacity[active],
            expected.working_memory_dimensions,
        )
        assert np.array_equal(
            simulation.entities.knowledge_capacity_bytes[active],
            expected.knowledge_capacity_bytes,
        )
        assert np.array_equal(
            simulation.entities.relation_capacity[active], expected.relation_slots
        )
        assert np.array_equal(
            simulation.entities.knowledge_attention_capacity[active],
            expected.knowledge_attention_slots,
        )
        assert np.array_equal(
            simulation.social.effective_capacity[active], expected.relation_slots
        )
        checkpoint = simulation.save_full_checkpoint(Path(tmp) / "neutralized.sechk")
        restored = Simulation.from_checkpoint(
            checkpoint, Path(tmp) / "restored", backend="cpu", until_tick=4
        )
        assert restored.capacity_ablation_enabled
        assert restored.intervention_history[-1]["type"] == "neutralize-elastic-capacities"
        for item in (simulation, restored):
            item.knowledge.close()
            item.evolution_progress.close()
            item.metrics.close()
