from __future__ import annotations

from dataclasses import replace
from pathlib import Path
import tempfile
import unittest

import numpy as np

from se.cfg import load_config, validate_config
from se.knowledge import (
    ACQUISITION_PRIVATE_EXPERIENCE,
    KnowledgeSystem,
    KnowledgeTransferPlan,
    OUTCOME_WIDTH,
)
from se.knowledge.policy import KnowledgePolicyPlan
from se.runtime.sim import Simulation


ROOT = Path(__file__).resolve().parents[1]


class KnowledgeK4Tests(unittest.TestCase):
    def _cfg(self, **knowledge_overrides):
        base = load_config(ROOT / "configs" / "mvp_short_k4_candidates.json")
        knowledge = replace(base.knowledge, **knowledge_overrides)
        cfg = replace(base, knowledge=knowledge)
        validate_config(cfg)
        return cfg

    @staticmethod
    def _world_arrays(count: int):
        alive = np.ones(count, dtype=bool)
        subjects = np.arange(101, 101 + count, dtype=np.uint64)
        lineages = np.arange(1001, 1001 + count, dtype=np.uint64)
        groups = np.asarray([(i % 2) + 1 for i in range(count)], dtype=np.uint64)
        x = np.linspace(1.0, 20.0, count, dtype=np.float32)
        y = np.linspace(2.0, 22.0, count, dtype=np.float32)
        energy = np.linspace(1.0, 2.0, count, dtype=np.float32)
        integrity = np.linspace(0.8, 1.0, count, dtype=np.float32)
        material = np.arange(count, dtype=np.float32)
        information = np.linspace(0.1, 0.4, count, dtype=np.float32)
        fertility = np.linspace(0.2, 0.8, count, dtype=np.float32)
        return alive, subjects, lineages, groups, x, y, energy, integrity, material, information, fertility

    def _observe(self, system: KnowledgeSystem, count: int, tick: int = 5):
        values = self._world_arrays(count)
        return system.update_candidates(
            tick=tick,
            alive=values[0],
            primary_subject_ids=values[1],
            lineage_subject_ids=values[2],
            group_ids=values[3],
            x=values[4],
            y=values[5],
            world_width=128.0,
            world_height=128.0,
            energy=values[6],
            integrity=values[7],
            harvested_material=values[8],
            information_store=values[9],
            fertility=values[10],
            reproduction_threshold=2.8,
        )

    def test_lineage_unique_holders_and_variant_depth(self) -> None:
        cfg = self._cfg(initial_content_count=0, initial_holders_fraction=0.0)
        with tempfile.TemporaryDirectory() as tmp:
            system = KnowledgeSystem(
                cfg, tmp,
                initial_entity_ids=np.empty(0, dtype=np.uint64),
                initial_subject_ids=np.empty(0, dtype=np.uint64),
            )
            root = system.catalog.append(
                parent_content_id=0, context_key=1, action_id=1,
                outcome_vector=np.zeros(OUTCOME_WIDTH, dtype=np.float32),
                encoded_bytes=96, created_tick=0, source_subject_id=101,
            )
            for holder in (101, 101, 102):
                system.arena.append(
                    holder_subject_id=holder, content_id=root, source_subject_id=101,
                    confidence=1.0, sample_count=1, created_tick=0,
                    last_verified_tick=1, encoded_bytes=96,
                    acquisition_kind=ACQUISITION_PRIVATE_EXPERIENCE,
                )
            variant = system.catalog.append(
                parent_content_id=root, context_key=2, action_id=2,
                outcome_vector=np.ones(OUTCOME_WIDTH, dtype=np.float32),
                encoded_bytes=96, created_tick=2, source_subject_id=103,
            )
            system.arena.append(
                holder_subject_id=103, content_id=variant, source_subject_id=103,
                confidence=0.5, sample_count=1, created_tick=2,
                last_verified_tick=2, encoded_bytes=96,
                acquisition_kind=ACQUISITION_PRIVATE_EXPERIENCE,
            )
            plan = self._observe(system, 3)
            self.assertEqual(plan.size, 2)
            self.assertEqual(int(plan.root_content_ids[root - 1]), root)
            self.assertEqual(int(plan.root_content_ids[variant - 1]), root)
            self.assertEqual(int(plan.variant_depths[variant - 1]), 1)
            self.assertEqual(int(plan.current_unique_holder_counts[root - 1]), 2)
            self.assertEqual(int(system.candidates.total_copy_count[root - 1]), 3)
            self.assertEqual(int(system.candidates.descendant_variant_count[root - 1]), 1)
            system.close()
            self.assertTrue((Path(tmp) / "knowledge_content_lineage.csv").exists())
            self.assertTrue((Path(tmp) / "knowledge_subject_edges.csv").exists())

    def test_content_persists_across_host_death_then_becomes_inactive(self) -> None:
        cfg = self._cfg(initial_content_count=0, initial_holders_fraction=0.0)
        with tempfile.TemporaryDirectory() as tmp:
            system = KnowledgeSystem(
                cfg, tmp,
                initial_entity_ids=np.empty(0, dtype=np.uint64),
                initial_subject_ids=np.empty(0, dtype=np.uint64),
            )
            content = system.catalog.append(
                parent_content_id=0, context_key=1, action_id=1,
                outcome_vector=np.zeros(OUTCOME_WIDTH, dtype=np.float32),
                encoded_bytes=96, created_tick=0, source_subject_id=101,
            )
            for holder in (101, 102):
                system.arena.append(
                    holder_subject_id=holder, content_id=content, source_subject_id=101,
                    confidence=1.0, sample_count=1, created_tick=0,
                    last_verified_tick=1, encoded_bytes=96,
                )
            self._observe(system, 2, tick=2)
            system.remove_dead_holders(
                np.asarray([False, True]), np.asarray([101, 102], dtype=np.uint64)
            )
            values = list(self._world_arrays(2))
            values[0] = np.asarray([False, True])
            system.update_candidates(
                tick=3, alive=values[0], primary_subject_ids=values[1],
                lineage_subject_ids=values[2], group_ids=values[3], x=values[4], y=values[5],
                world_width=128.0, world_height=128.0, energy=values[6], integrity=values[7],
                harvested_material=values[8], information_store=values[9], fertility=values[10],
                reproduction_threshold=2.8,
            )
            self.assertEqual(int(system.candidates.active_copy_count[content - 1]), 1)
            system.remove_dead_holders(
                np.asarray([False, False]), np.asarray([101, 102], dtype=np.uint64)
            )
            values[0] = np.asarray([False, False])
            system.update_candidates(
                tick=4, alive=values[0], primary_subject_ids=values[1],
                lineage_subject_ids=values[2], group_ids=values[3], x=values[4], y=values[5],
                world_width=128.0, world_height=128.0, energy=values[6], integrity=values[7],
                harvested_material=values[8], information_store=values[9], fertility=values[10],
                reproduction_threshold=2.8,
            )
            self.assertEqual(int(system.candidates.active_copy_count[content - 1]), 0)
            self.assertEqual(int(system.candidates.total_copy_count[content - 1]), 2)
            self.assertEqual(int(system.candidates.last_seen_tick[content - 1]), 3)
            system.close()

    def test_transfer_boundary_and_cost_attribution(self) -> None:
        cfg = self._cfg(
            initial_content_count=0,
            initial_holders_fraction=0.0,
            transfer_base_energy_cost=0.01,
            transfer_energy_per_byte=0.001,
            receive_energy_per_byte=0.0005,
        )
        with tempfile.TemporaryDirectory() as tmp:
            system = KnowledgeSystem(
                cfg, tmp,
                initial_entity_ids=np.empty(0, dtype=np.uint64),
                initial_subject_ids=np.empty(0, dtype=np.uint64),
            )
            content = system.catalog.append(
                parent_content_id=0, context_key=1, action_id=1,
                outcome_vector=np.zeros(OUTCOME_WIDTH, dtype=np.float32),
                encoded_bytes=64, created_tick=0, source_subject_id=101,
            )
            source_copy = system.arena.append(
                holder_subject_id=101, content_id=content, source_subject_id=101,
                confidence=1.0, sample_count=1, created_tick=0,
                last_verified_tick=1, encoded_bytes=64,
            )
            plan = KnowledgeTransferPlan(
                tick=1,
                sender_entity_indices=np.asarray([0], dtype=np.int32),
                receiver_entity_indices=np.asarray([1], dtype=np.int32),
                sender_subject_ids=np.asarray([101], dtype=np.uint64),
                receiver_subject_ids=np.asarray([102], dtype=np.uint64),
                source_subject_ids=np.asarray([101], dtype=np.uint64),
                source_copy_ids=np.asarray([source_copy], dtype=np.uint64),
                content_ids=np.asarray([content], dtype=np.uint64),
                encoded_bytes=np.asarray([64], dtype=np.uint32),
                delivered=np.asarray([True]), corrupted=np.asarray([False]),
            )
            stats = system.commit_transfers(
                plan,
                energy=np.asarray([2.0, 2.0], dtype=np.float32),
                alive=np.asarray([True, True]),
                group_ids=np.asarray([1, 2], dtype=np.uint64),
                lineage_subject_ids=np.asarray([11, 22], dtype=np.uint64),
                x=np.asarray([1.0, 100.0], dtype=np.float32),
                y=np.asarray([1.0, 100.0], dtype=np.float32),
                world_width=128.0, world_height=128.0,
            )
            self.assertEqual(stats.transfer_committed, 1)
            row = content - 1
            self.assertEqual(int(system.candidates.group_commit_flow[row, 1]), 1)
            self.assertEqual(int(system.candidates.lineage_commit_flow[row, 1]), 1)
            self.assertEqual(int(system.candidates.region_commit_flow[row, 1]), 1)
            self.assertAlmostEqual(float(system.candidates.sender_cost[row]), 0.074, places=7)
            self.assertAlmostEqual(float(system.candidates.receiver_cost[row]), 0.032, places=7)
            system.close()

    def test_policy_influence_is_attributed_to_supporting_content(self) -> None:
        cfg = self._cfg(initial_content_count=0, initial_holders_fraction=0.0)
        with tempfile.TemporaryDirectory() as tmp:
            system = KnowledgeSystem(
                cfg, tmp,
                initial_entity_ids=np.empty(0, dtype=np.uint64),
                initial_subject_ids=np.empty(0, dtype=np.uint64),
            )
            content = system.catalog.append(
                parent_content_id=0, context_key=7, action_id=2,
                outcome_vector=np.ones(OUTCOME_WIDTH, dtype=np.float32),
                encoded_bytes=96, created_tick=0, source_subject_id=101,
            )
            system.arena.append(
                holder_subject_id=101, content_id=content, source_subject_id=101,
                confidence=1.0, sample_count=2, created_tick=0,
                last_verified_tick=1, encoded_bytes=96,
                outcome_mean=np.ones(OUTCOME_WIDTH, dtype=np.float32),
                acquisition_kind=ACQUISITION_PRIVATE_EXPERIENCE,
            )
            system.publish(1)
            plan = KnowledgePolicyPlan(
                tick=1,
                active_rows=np.asarray([0], dtype=np.int32),
                entity_ids=np.asarray([1], dtype=np.uint64),
                holder_subject_ids=np.asarray([101], dtype=np.uint64),
                context_keys=np.asarray([7], dtype=np.uint64),
                action_ids=np.asarray([2], dtype=np.int16),
                residuals=np.asarray([0.5], dtype=np.float32),
                support_copy_counts=np.asarray([1], dtype=np.uint16),
                private_support_counts=np.asarray([1], dtype=np.uint16),
                transfer_support_counts=np.asarray([0], dtype=np.uint16),
                unverified_transfer_support_counts=np.asarray([0], dtype=np.uint16),
                reliability_mass=np.asarray([0.5], dtype=np.float32),
                weighted_outcome_vectors=np.ones((1, OUTCOME_WIDTH), dtype=np.float32),
            )
            system.record_policy_plan(
                plan, changed_actions=1,
                changed_active_rows=np.asarray([0], dtype=np.int32),
            )
            row = content - 1
            self.assertEqual(int(system.candidates.policy_influence_events[row]), 1)
            self.assertEqual(int(system.candidates.policy_changed_action_events[row]), 1)
            self.assertAlmostEqual(float(system.candidates.policy_residual_abs_sum[row]), 0.5)
            system.close()

    def test_k4_tracking_is_observational_and_k3_compatible(self) -> None:
        k4 = self._cfg(candidate_update_period=2)
        k3 = replace(
            k4,
            knowledge=replace(
                k4.knowledge,
                schema="dynamic-knowledge-k3-v1",
                candidate_tracking_enabled=False,
            ),
        )
        validate_config(k3)
        run = replace(k4.run, ticks=6, metrics_period=3, checkpoint_period=3, validation_mode=True)
        world = replace(k4.world, initial_entities=48, max_entities=64, grid_x=8, grid_y=8, width=32.0, height=32.0)
        k4 = replace(k4, run=run, world=world)
        k3 = replace(k3, run=run, world=world)
        with tempfile.TemporaryDirectory() as tmp:
            control = Simulation(k3, Path(tmp) / "k3", backend="cpu")
            diagnostic = Simulation(k4, Path(tmp) / "k4", backend="cpu")
            control.run()
            diagnostic.run()
            for name in (
                "entity_id", "alive", "x", "y", "energy", "integrity", "fertility",
                "genotype", "memory", "information_store", "lineage_id",
            ):
                self.assertTrue(
                    np.array_equal(getattr(control.entities, name), getattr(diagnostic.entities, name)),
                    name,
                )
            self.assertTrue(np.array_equal(control.environment.resources, diagnostic.environment.resources))
            self.assertTrue(np.array_equal(control.information.field, diagnostic.information.field))
            self.assertTrue(np.array_equal(control.social.group_id, diagnostic.social.group_id))
            control_arrays = control.knowledge.checkpoint_arrays()
            diagnostic_arrays = diagnostic.knowledge.checkpoint_arrays()
            for name, value in control_arrays.items():
                self.assertTrue(np.array_equal(value, diagnostic_arrays[name]), name)
            self.assertTrue(any(name.startswith("knowledge_candidate_") for name in diagnostic_arrays))


if __name__ == "__main__":
    unittest.main()
