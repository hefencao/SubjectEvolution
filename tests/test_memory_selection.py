from __future__ import annotations

from dataclasses import replace
from pathlib import Path
import tempfile
import unittest

import numpy as np

from subject_evolution.config import load_config, validate_config
from subject_evolution.knowledge import (
    ACQUISITION_PRIVATE_EXPERIENCE,
    KnowledgeSystem,
    OUTCOME_WIDTH,
)
from subject_evolution.knowledge_policy import KnowledgePolicyPlan
from subject_evolution.latent_knowledge import (
    LatentBucket,
    LatentRouterBatch,
    select_latent_router_batch,
)
from subject_evolution.policy import Action, ParametricPolicy
from subject_evolution.routing_cost import apply_routing_cost_budget
from subject_evolution.simulation import Simulation
from subject_evolution.working_memory import build_working_memory_update
from tests.test_checkpoint_replay import assert_state_equal

ROOT = Path(__file__).resolve().parents[1]


class WorkingMemorySelectionTests(unittest.TestCase):
    def _cfg(self, **overrides):
        base = load_config(ROOT / "configs" / "mvp_short_latent_l2_budget_matched.json")
        values = dict(
            working_memory_enabled=True,
            working_memory_base_energy_cost=0.01,
            working_memory_energy_per_dimension=0.001,
            working_memory_energy_per_saturation=0.002,
            sparse_selection_enabled=True,
            sparse_selection_top_k=2,
            sparse_selection_base_energy_cost=0.003,
            sparse_selection_energy_per_candidate=0.0001,
            sparse_selection_energy_per_selected_copy=0.0002,
        )
        values.update(overrides)
        cfg = replace(base, knowledge=replace(base.knowledge, **values))
        validate_config(cfg)
        return cfg

    def _memory_update(self, cfg, genes, *, previous=None, actual=None, energy=10.0):
        width = cfg.knowledge.working_memory_width
        previous = (
            np.zeros((1, width), dtype=np.int16)
            if previous is None else np.asarray(previous, dtype=np.int16).reshape(1, width)
        )
        actual = (
            np.zeros((1, OUTCOME_WIDTH), dtype=np.float32)
            if actual is None else np.asarray(actual, dtype=np.float32).reshape(1, OUTCOME_WIDTH)
        )
        return build_working_memory_update(
            tick=1,
            active_rows=np.asarray([0], dtype=np.int32),
            entity_ids=np.asarray([11], dtype=np.uint64),
            previous_q=previous,
            previous_observation_q=np.zeros((1, 4), dtype=np.int16),
            current_state_features=np.zeros((1, 4), dtype=np.float32),
            actual_outcomes=actual,
            expected_outcomes=np.zeros((1, OUTCOME_WIDTH), dtype=np.float32),
            genotype=np.asarray(genes, dtype=np.float32).reshape(1, -1),
            gene_start=0,
            available_energy=np.asarray([energy], dtype=np.float64),
            config=cfg.knowledge,
        )

    def test_working_memory_decay_prediction_saturation_and_rejection(self) -> None:
        cfg = self._cfg(working_memory_activation_clip=0.25)
        width = cfg.knowledge.working_memory_width
        genes = np.zeros(width * 4, dtype=np.float32)
        # decay=1, no prediction/observation/bias: preserve previous exactly.
        genes[:width] = 1.0
        result = self._memory_update(cfg, genes, previous=[100, -200, 300, -400])
        self.assertTrue(np.array_equal(result.committed_q[0], [100, -200, 300, -400]))
        # Zero decay plus maximal prediction gain must respond to local outcome error.
        genes[:width] = -1.0
        genes[width : 2 * width] = 1.0
        result = self._memory_update(cfg, genes, actual=[2, -2, 2, -2, 2])
        self.assertTrue(np.any(result.proposed_q != 0))
        # Maximal bias clips all coordinates at the configured hard boundary.
        genes[:] = 0.0
        genes[:width] = -1.0
        genes[3 * width : 4 * width] = 1.0
        saturated = self._memory_update(cfg, genes)
        self.assertEqual(int(saturated.saturation_count[0]), width)
        self.assertTrue(np.all(np.abs(saturated.proposed_q[0]) == 1024))
        rejected = self._memory_update(cfg, genes, previous=[7, 8, 9, 10], energy=0.0)
        self.assertFalse(bool(rejected.accepted[0]))
        self.assertTrue(np.array_equal(rejected.committed_q[0], [7, 8, 9, 10]))

    @staticmethod
    def _batch(order=(0, 1, 2)) -> LatentRouterBatch:
        order = np.asarray(order, dtype=np.int32)
        copy_ids = np.asarray([30, 10, 20], dtype=np.uint64)[order]
        content_ids = np.asarray([3, 2, 1], dtype=np.uint64)[order]
        values = np.zeros((3, 8), dtype=np.int16)
        batch = LatentRouterBatch(
            tick=2,
            active_count=1,
            copy_active_rows=np.zeros(3, dtype=np.int32),
            copy_ids=copy_ids,
            content_ids=content_ids,
            entity_ids=np.full(3, 11, dtype=np.uint64),
            holder_subject_ids=np.full(3, 101, dtype=np.uint64),
            context_keys=np.full(3, 7, dtype=np.uint64),
            acquisition_kinds=np.ones(3, dtype=np.uint8),
            unverified_transfer=np.zeros(3, dtype=bool),
            reliability_q=np.full(3, 4096, dtype=np.int32),
            outcome_vectors=np.zeros((3, OUTCOME_WIDTH), dtype=np.float32),
            outcome_q=np.zeros((3, OUTCOME_WIDTH), dtype=np.int32),
            latent_lengths=np.full(3, 8, dtype=np.uint16),
            buckets=(LatentBucket(8, np.arange(3, dtype=np.int32), values.copy()),),
        )
        batch.validate((4, 8, 16, 32))
        return batch

    def _select(self, cfg, batch):
        genes = np.zeros((1, ParametricPolicy.genome_size_for_config(cfg)), dtype=np.float32)
        return select_latent_router_batch(
            batch,
            genotype=genes,
            selection_gene_start=ParametricPolicy.sparse_selection_gene_start(cfg),
            state_features=np.zeros((1, 4), dtype=np.float32),
            working_memory_q=np.zeros((1, 4), dtype=np.int16),
            config=cfg.knowledge,
        )

    def test_topk_ties_are_stable_and_authoritative_batch_is_unchanged(self) -> None:
        cfg = self._cfg(sparse_selection_top_k=2)
        original = self._batch()
        copy_before = original.copy_ids.copy()
        selected = self._select(cfg, original)
        permuted = self._select(cfg, self._batch((2, 0, 1)))
        self.assertTrue(np.array_equal(original.copy_ids, copy_before))
        self.assertTrue(np.array_equal(np.sort(selected.batch.copy_ids), [10, 20]))
        self.assertTrue(
            np.array_equal(np.sort(selected.batch.copy_ids), np.sort(permuted.batch.copy_ids))
        )
        self.assertEqual(int(selected.candidate_count[0]), 3)
        self.assertEqual(int(selected.selected_count[0]), 2)
        self.assertEqual(int(selected.tie_count[0]), 2)

    def test_topk_zero_and_underfilled_sets_have_explicit_semantics(self) -> None:
        zero_cfg = self._cfg(sparse_selection_top_k=0)
        zero = self._select(zero_cfg, self._batch())
        self.assertEqual(zero.batch.size, 0)
        self.assertEqual(int(zero.candidate_count[0]), 3)
        self.assertEqual(int(zero.selected_count[0]), 0)
        all_cfg = self._cfg(sparse_selection_top_k=4)
        all_selected = self._select(all_cfg, self._batch())
        self.assertEqual(all_selected.batch.size, 3)

    def test_selection_cost_is_charged_even_when_topk_is_zero(self) -> None:
        cfg = self._cfg(sparse_selection_top_k=0)
        plan = KnowledgePolicyPlan.empty(tick=3)
        plan = replace(
            plan,
            router_schema=cfg.knowledge.latent_router_schema,
            selection_schema=cfg.knowledge.sparse_selection_schema,
            work_active_rows=np.asarray([0], dtype=np.int32),
            work_entity_ids=np.asarray([11], dtype=np.uint64),
            work_holder_subject_ids=np.asarray([101], dtype=np.uint64),
            work_context_keys=np.asarray([7], dtype=np.uint64),
            work_support_copy_counts=np.asarray([0], dtype=np.uint16),
            work_latent_dimension_counts=np.asarray([0], dtype=np.uint32),
            work_latent_max_widths=np.asarray([0], dtype=np.uint16),
            work_router_saturation_counts=np.asarray([0], dtype=np.uint32),
            work_router_clipping_counts=np.asarray([0], dtype=np.uint32),
            work_router_hidden_active_counts=np.asarray([0], dtype=np.uint32),
            work_selection_candidate_counts=np.asarray([3], dtype=np.uint16),
            work_selection_selected_counts=np.asarray([0], dtype=np.uint16),
            work_selection_tie_counts=np.asarray([0], dtype=np.uint16),
            work_selection_score_thresholds_q=np.asarray([0], dtype=np.int64),
        )
        plan.validate(1, len(Action))
        result = apply_routing_cost_budget(
            plan,
            active_energy=np.asarray([10.0]),
            config=cfg.knowledge,
            action_count=len(Action),
        )
        expected_selection = 0.003 + 3 * 0.0001
        expected = cfg.knowledge.routing_base_energy_cost + expected_selection
        self.assertAlmostEqual(float(result.selection_energy[0]), expected_selection, places=12)
        self.assertAlmostEqual(float(result.requested_energy[0]), expected, places=12)
        self.assertEqual(result.plan.size, 0)
        self.assertEqual(result.plan.work_active_rows.size, 1)


    def test_k4_selection_and_memory_cost_attribution_is_conserved(self) -> None:
        cfg = self._cfg(sparse_selection_top_k=0)
        cfg = replace(
            cfg,
            knowledge=replace(
                cfg.knowledge,
                candidate_tracking_enabled=True,
                initial_content_count=0,
                initial_holders_fraction=0.0,
            ),
        )
        validate_config(cfg)
        with tempfile.TemporaryDirectory() as tmp:
            system = KnowledgeSystem(
                cfg,
                tmp,
                initial_entity_ids=np.asarray([11], dtype=np.uint64),
                initial_subject_ids=np.asarray([101], dtype=np.uint64),
            )
            try:
                encoded = system._encoded_bytes_for_new_content(
                    parent_content_id=0, context_key=7,
                    action_id=int(Action.HARVEST), source_subject_id=101,
                )
                content = system.catalog.append(
                    parent_content_id=0, context_key=7,
                    action_id=int(Action.HARVEST),
                    outcome_vector=np.zeros(OUTCOME_WIDTH, dtype=np.float32),
                    encoded_bytes=encoded, created_tick=1, source_subject_id=101,
                )
                system.latent_store.ensure_catalog(system.catalog)
                system.candidates.ensure_catalog(system.catalog)
                system.arena.append(
                    holder_subject_id=101, content_id=content, source_subject_id=101,
                    confidence=1.0, sample_count=4, created_tick=1,
                    last_verified_tick=1, encoded_bytes=encoded,
                    outcome_mean=np.zeros(OUTCOME_WIDTH, dtype=np.float32),
                    acquisition_kind=ACQUISITION_PRIVATE_EXPERIENCE,
                )
                system.publish(2)
                plan = replace(
                    KnowledgePolicyPlan.empty(tick=2),
                    router_schema=cfg.knowledge.latent_router_schema,
                    selection_schema=cfg.knowledge.sparse_selection_schema,
                    work_active_rows=np.asarray([0], dtype=np.int32),
                    work_entity_ids=np.asarray([11], dtype=np.uint64),
                    work_holder_subject_ids=np.asarray([101], dtype=np.uint64),
                    work_context_keys=np.asarray([7], dtype=np.uint64),
                    work_support_copy_counts=np.asarray([0], dtype=np.uint16),
                    work_latent_dimension_counts=np.asarray([0], dtype=np.uint32),
                    work_latent_max_widths=np.asarray([0], dtype=np.uint16),
                    work_router_saturation_counts=np.asarray([0], dtype=np.uint32),
                    work_router_clipping_counts=np.asarray([0], dtype=np.uint32),
                    work_router_hidden_active_counts=np.asarray([0], dtype=np.uint32),
                    work_selection_candidate_counts=np.asarray([1], dtype=np.uint16),
                    work_selection_selected_counts=np.asarray([0], dtype=np.uint16),
                    work_selection_tie_counts=np.asarray([0], dtype=np.uint16),
                    work_selection_score_thresholds_q=np.asarray([0], dtype=np.int64),
                )
                routing = apply_routing_cost_budget(
                    plan, active_energy=np.asarray([10.0]),
                    config=cfg.knowledge, action_count=len(Action),
                )
                system.record_routing_cost(routing)
                self.assertAlmostEqual(
                    float(system.candidates.selection_cost[: system.catalog.size].sum()),
                    float(routing.committed_total),
                    places=12,
                )
                width = cfg.knowledge.working_memory_width
                genes = np.zeros(width * 4, dtype=np.float32)
                genes[:width] = 1.0
                memory = self._memory_update(cfg, genes)
                system.record_working_memory(
                    memory, holder_subject_ids=np.asarray([101], dtype=np.uint64)
                )
                self.assertAlmostEqual(
                    float(system.candidates.working_memory_cost[: system.catalog.size].sum()),
                    float(memory.committed_total),
                    places=12,
                )
            finally:
                system.close()

    def test_memory_selection_checkpoint_restore_is_exact(self) -> None:
        cfg = self._cfg()
        cfg = replace(
            cfg,
            run=replace(cfg.run, ticks=6, metrics_period=3, checkpoint_period=3),
            world=replace(cfg.world, initial_entities=24, max_entities=40),
        )
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            continuous = Simulation(cfg, root / "continuous", backend="cpu")
            for _ in range(3):
                continuous.step()
            checkpoint = continuous.save_full_checkpoint(root / "tick3.sechk")
            restored = Simulation.from_checkpoint(
                checkpoint, root / "restored", backend="cpu", until_tick=6
            )
            try:
                for _ in range(3):
                    continuous.step()
                    restored.step()
                assert_state_equal(
                    self,
                    continuous._full_checkpoint_state(),
                    restored._full_checkpoint_state(),
                )
                self.assertTrue(np.any(continuous.entities.working_memory_q != 0))
            finally:
                for simulation in (continuous, restored):
                    simulation.knowledge.close()
                    simulation.metrics.close()
                    simulation.evolution_progress.close()

    def test_modules_off_preserve_v012_genome_width(self) -> None:
        base = load_config(ROOT / "configs" / "mvp_short_latent_l2_budget_matched.json")
        self.assertFalse(base.knowledge.working_memory_enabled)
        self.assertFalse(base.knowledge.sparse_selection_enabled)
        extended = self._cfg()
        self.assertGreater(
            ParametricPolicy.genome_size_for_config(extended),
            ParametricPolicy.genome_size_for_config(base),
        )


if __name__ == "__main__":
    unittest.main()
