from __future__ import annotations

from dataclasses import replace
from pathlib import Path
import tempfile
import unittest

import numpy as np

from subject_evolution.config import KnowledgeConfig, load_config
from subject_evolution.knowledge import KnowledgeSystem, KnowledgeTransferPlan, OUTCOME_WIDTH
from subject_evolution.simulation import Simulation


ROOT = Path(__file__).resolve().parents[1]


class KnowledgeK1Tests(unittest.TestCase):
    def _cfg(self, **knowledge_overrides):
        cfg = load_config(ROOT / "configs" / "mvp_small.json")
        knowledge = replace(
            cfg.knowledge,
            enabled=True,
            holder_capacity_bytes=128,
            encoded_bytes_per_copy=64,
            transfer_probability=1.0,
            attention_slots_per_tick=1,
            transfer_base_energy_cost=0.01,
            transfer_energy_per_byte=0.001,
            receive_energy_per_byte=0.0005,
            **knowledge_overrides,
        )
        information = replace(cfg.information, channel_loss=0.0, classification_error=1.0)
        return replace(cfg, knowledge=knowledge, information=information)

    def test_corrupted_transfer_is_explicit_and_costed(self) -> None:
        cfg = self._cfg()
        with tempfile.TemporaryDirectory() as tmp:
            system = KnowledgeSystem(
                cfg,
                tmp,
                initial_entity_ids=np.empty(0, dtype=np.uint64),
                initial_subject_ids=np.empty(0, dtype=np.uint64),
            )
            content = system.catalog.append(
                parent_content_id=0,
                context_key=7,
                action_id=2,
                outcome_vector=np.zeros(OUTCOME_WIDTH, dtype=np.float32),
                encoded_bytes=64,
                created_tick=0,
                source_subject_id=101,
            )
            copy_id = system.arena.append(
                holder_subject_id=101,
                content_id=content,
                source_subject_id=101,
                confidence=1.0,
                sample_count=0,
                created_tick=0,
                last_verified_tick=0,
                encoded_bytes=64,
            )
            entity_ids = np.asarray([1, 2], dtype=np.uint64)
            subjects = np.asarray([101, 202], dtype=np.uint64)
            alive = np.asarray([True, True])
            plan = system.plan_transfers(
                sender_entity_indices=np.asarray([0], dtype=np.int32),
                receiver_entity_indices=np.asarray([1], dtype=np.int32),
                entity_ids=entity_ids,
                primary_subject_ids=subjects,
                alive=alive,
                tick=0,
            )
            self.assertEqual(plan.size, 1)
            self.assertEqual(int(plan.source_copy_ids[0]), copy_id)
            self.assertTrue(bool(plan.delivered[0]))
            self.assertTrue(bool(plan.corrupted[0]))
            energy = np.asarray([2.0, 2.0], dtype=np.float32)
            stats = system.commit_transfers(plan, energy=energy, alive=alive)
            self.assertEqual(stats.transfer_committed, 1)
            self.assertEqual(stats.transfer_corrupted, 1)
            self.assertEqual(system.catalog.size, 2)
            receiver_rows = system.arena.rows_for_holder(202)
            self.assertEqual(len(receiver_rows), 1)
            variant = int(system.arena.content_id[receiver_rows[0]])
            self.assertEqual(int(system.catalog.parent_content_id[variant - 1]), content)
            self.assertAlmostEqual(float(energy[0]), 2.0 - (0.01 + 64 * 0.001), places=6)
            self.assertAlmostEqual(float(energy[1]), 2.0 - 64 * 0.0005, places=6)
            system.close()

    def test_capacity_eviction_uses_oldest_copy_only(self) -> None:
        cfg = self._cfg()
        with tempfile.TemporaryDirectory() as tmp:
            system = KnowledgeSystem(
                cfg,
                tmp,
                initial_entity_ids=np.empty(0, dtype=np.uint64),
                initial_subject_ids=np.empty(0, dtype=np.uint64),
            )
            contents = [
                system.catalog.append(
                    parent_content_id=0,
                    context_key=i + 1,
                    action_id=i,
                    outcome_vector=np.zeros(OUTCOME_WIDTH, dtype=np.float32),
                    encoded_bytes=64,
                    created_tick=0,
                    source_subject_id=101,
                )
                for i in range(3)
            ]
            first = system.arena.append(
                holder_subject_id=202,
                content_id=contents[0],
                source_subject_id=202,
                confidence=1.0,
                sample_count=0,
                created_tick=0,
                last_verified_tick=0,
                encoded_bytes=64,
            )
            second = system.arena.append(
                holder_subject_id=202,
                content_id=contents[1],
                source_subject_id=202,
                confidence=0.0,
                sample_count=0,
                created_tick=0,
                last_verified_tick=0,
                encoded_bytes=64,
            )
            source = system.arena.append(
                holder_subject_id=101,
                content_id=contents[2],
                source_subject_id=101,
                confidence=1.0,
                sample_count=0,
                created_tick=0,
                last_verified_tick=0,
                encoded_bytes=64,
            )
            plan = KnowledgeTransferPlan(
                tick=1,
                sender_entity_indices=np.asarray([0], dtype=np.int32),
                receiver_entity_indices=np.asarray([1], dtype=np.int32),
                sender_subject_ids=np.asarray([101], dtype=np.uint64),
                receiver_subject_ids=np.asarray([202], dtype=np.uint64),
                source_subject_ids=np.asarray([101], dtype=np.uint64),
                source_copy_ids=np.asarray([source], dtype=np.uint64),
                content_ids=np.asarray([contents[2]], dtype=np.uint64),
                encoded_bytes=np.asarray([64], dtype=np.uint32),
                delivered=np.asarray([True]),
                corrupted=np.asarray([False]),
            )
            stats = system.commit_transfers(
                plan,
                energy=np.asarray([2.0, 2.0], dtype=np.float32),
                alive=np.asarray([True, True]),
            )
            self.assertEqual(stats.evicted_capacity, 1)
            active_ids = set(int(v) for v in system.arena.copy_id[system.arena.active])
            self.assertNotIn(first, active_ids)
            self.assertIn(second, active_ids)
            self.assertEqual(system.arena.holder_bytes(202), 128)
            system.close()


    def test_attention_arbitration_is_canonical_and_counted(self) -> None:
        cfg = self._cfg()
        with tempfile.TemporaryDirectory() as tmp:
            system = KnowledgeSystem(
                cfg,
                tmp,
                initial_entity_ids=np.empty(0, dtype=np.uint64),
                initial_subject_ids=np.empty(0, dtype=np.uint64),
            )
            for holder, context in ((101, 1), (102, 2)):
                content = system.catalog.append(
                    parent_content_id=0,
                    context_key=context,
                    action_id=1,
                    outcome_vector=np.zeros(OUTCOME_WIDTH, dtype=np.float32),
                    encoded_bytes=64,
                    created_tick=0,
                    source_subject_id=holder,
                )
                system.arena.append(
                    holder_subject_id=holder,
                    content_id=content,
                    source_subject_id=holder,
                    confidence=1.0,
                    sample_count=0,
                    created_tick=0,
                    last_verified_tick=0,
                    encoded_bytes=64,
                )
            plan = system.plan_transfers(
                sender_entity_indices=np.asarray([1, 0], dtype=np.int32),
                receiver_entity_indices=np.asarray([2, 2], dtype=np.int32),
                entity_ids=np.asarray([1, 2, 3], dtype=np.uint64),
                primary_subject_ids=np.asarray([101, 102, 202], dtype=np.uint64),
                alive=np.asarray([True, True, True]),
                tick=0,
            )
            self.assertEqual(plan.size, 1)
            self.assertEqual(plan.attention_rejected, 1)
            self.assertEqual(int(plan.sender_subject_ids[0]), 101)
            system.close()

    def test_k1_without_cost_or_transfer_does_not_change_world_semantics(self) -> None:
        base = load_config(ROOT / "configs" / "mvp_small.json")
        run = replace(base.run, ticks=5, metrics_period=5, checkpoint_period=5, validation_mode=True)
        world = replace(base.world, width=32.0, height=32.0, grid_x=8, grid_y=8, initial_entities=50, max_entities=64)
        plain_cfg = replace(base, run=run, world=world)
        knowledge = KnowledgeConfig(
            enabled=True,
            initial_content_count=4,
            initial_holders_fraction=0.5,
            holder_capacity_bytes=128,
            encoded_bytes_per_copy=64,
        )
        knowledge_cfg = replace(plain_cfg, knowledge=knowledge)
        with tempfile.TemporaryDirectory() as tmp:
            plain = Simulation(plain_cfg, Path(tmp) / "plain", backend="cpu")
            layered = Simulation(knowledge_cfg, Path(tmp) / "layered", backend="cpu")
            for _ in range(5):
                plain.step()
                layered.step()
            for name in (
                "entity_id",
                "alive",
                "x",
                "y",
                "energy",
                "integrity",
                "fertility",
                "age",
                "generation",
                "lineage_id",
                "genotype",
                "memory",
            ):
                self.assertTrue(
                    np.array_equal(getattr(plain.entities, name), getattr(layered.entities, name)),
                    name,
                )
            self.assertTrue(np.array_equal(plain.environment.resources, layered.environment.resources))
            self.assertTrue(np.array_equal(plain.social.group_id, layered.social.group_id))
            self.assertGreater(layered.knowledge.arena.active_count, 0)
            plain.metrics.close(); plain.evolution_progress.close(); plain.knowledge.close()
            layered.metrics.close(); layered.evolution_progress.close(); layered.knowledge.close()


if __name__ == "__main__":
    unittest.main()
