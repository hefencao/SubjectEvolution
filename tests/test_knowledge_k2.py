from __future__ import annotations

from dataclasses import replace
from pathlib import Path
import tempfile
import unittest

import numpy as np

from subject_evolution.config import load_config
from subject_evolution.knowledge import (
    ACQUISITION_PRIVATE_EXPERIENCE,
    ACQUISITION_TRANSFER,
    KnowledgeOutcomePlan,
    KnowledgeSystem,
    KnowledgeTransferPlan,
    OUTCOME_STATUS_FAILED,
    OUTCOME_STATUS_PARTIAL,
    OUTCOME_STATUS_SUCCESS,
    OUTCOME_WIDTH,
    encode_local_context,
)
from subject_evolution.simulation import Simulation


ROOT = Path(__file__).resolve().parents[1]


class KnowledgeK2Tests(unittest.TestCase):
    def _cfg(self, **overrides):
        base = load_config(ROOT / "configs" / "mvp_small.json")
        defaults = {
            "enabled": True,
            "schema": "dynamic-knowledge-k2-v1",
            "holder_capacity_bytes": 256,
            "encoded_bytes_per_copy": 64,
            "learning_enabled": True,
            "experience_creation_enabled": True,
            "experience_creation_requires_free_capacity": True,
            "verification_energy_cost": 0.01,
            "confidence_learning_rate": 0.5,
            "initial_experience_confidence": 0.25,
            "max_updates_per_outcome": 1,
        }
        defaults.update(overrides)
        knowledge = replace(base.knowledge, **defaults)
        return replace(base, knowledge=knowledge)

    def _plan(
        self,
        *,
        tick: int,
        carriers=(0,),
        entity_ids=(1,),
        holders=(101,),
        contexts=(7,),
        actions=(2,),
        statuses=(OUTCOME_STATUS_SUCCESS,),
        failures=(0,),
        outcomes=((1.0, 0.0, 0.0, 0.0, 0.0),),
    ) -> KnowledgeOutcomePlan:
        return KnowledgeOutcomePlan(
            tick=tick,
            carrier_indices=np.asarray(carriers, dtype=np.int32),
            entity_ids=np.asarray(entity_ids, dtype=np.uint64),
            holder_subject_ids=np.asarray(holders, dtype=np.uint64),
            context_keys=np.asarray(contexts, dtype=np.uint64),
            action_ids=np.asarray(actions, dtype=np.int16),
            statuses=np.asarray(statuses, dtype=np.uint8),
            failure_reasons=np.asarray(failures, dtype=np.uint8),
            outcome_vectors=np.asarray(outcomes, dtype=np.float32),
        )

    def test_context_encoding_is_local_and_deterministic(self) -> None:
        keys = encode_local_context(
            np.asarray([0.0, 0.2, 1.0], dtype=np.float32),
            np.asarray([0.0, 0.4, 0.9], dtype=np.float32),
            np.asarray([1.0, 2.5, 4.5], dtype=np.float32),
            np.asarray([0.3, 0.7, 0.95], dtype=np.float32),
            np.asarray([False, True, True]),
            max_energy=5.0,
        )
        repeat = encode_local_context(
            np.asarray([0.0, 0.2, 1.0], dtype=np.float32),
            np.asarray([0.0, 0.4, 0.9], dtype=np.float32),
            np.asarray([1.0, 2.5, 4.5], dtype=np.float32),
            np.asarray([0.3, 0.7, 0.95], dtype=np.float32),
            np.asarray([False, True, True]),
            max_energy=5.0,
        )
        self.assertTrue(np.array_equal(keys, repeat))
        self.assertEqual(np.unique(keys).size, 3)
        self.assertTrue(np.all(keys > 0))

    def test_transferred_copy_requires_later_matching_experience(self) -> None:
        cfg = self._cfg(experience_creation_enabled=False)
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
                outcome_vector=np.asarray([0.5, 0, 0, 0, 0], dtype=np.float32),
                encoded_bytes=64,
                created_tick=0,
                source_subject_id=101,
            )
            source_copy = system.arena.append(
                holder_subject_id=101,
                content_id=content,
                source_subject_id=101,
                confidence=0.8,
                sample_count=3,
                created_tick=0,
                last_verified_tick=0,
                encoded_bytes=64,
                outcome_mean=np.asarray([0.5, 0, 0, 0, 0], dtype=np.float32),
                acquisition_kind=ACQUISITION_PRIVATE_EXPERIENCE,
            )
            transfer = KnowledgeTransferPlan(
                tick=1,
                sender_entity_indices=np.asarray([0], dtype=np.int32),
                receiver_entity_indices=np.asarray([1], dtype=np.int32),
                sender_subject_ids=np.asarray([101], dtype=np.uint64),
                receiver_subject_ids=np.asarray([202], dtype=np.uint64),
                source_subject_ids=np.asarray([101], dtype=np.uint64),
                source_copy_ids=np.asarray([source_copy], dtype=np.uint64),
                content_ids=np.asarray([content], dtype=np.uint64),
                encoded_bytes=np.asarray([64], dtype=np.uint32),
                delivered=np.asarray([True]),
                corrupted=np.asarray([False]),
                source_outcome_vectors=np.asarray([[0.5, 0, 0, 0, 0]], dtype=np.float32),
                source_confidences=np.asarray([0.8], dtype=np.float32),
                source_sample_counts=np.asarray([3], dtype=np.uint32),
            )
            energy = np.asarray([2.0, 2.0], dtype=np.float32)
            alive = np.asarray([True, True])
            transfer_stats = system.commit_transfers(transfer, energy=energy, alive=alive)
            self.assertEqual(transfer_stats.transfer_committed, 1)
            receiver_row = system.arena.rows_for_holder(202)[0]
            self.assertEqual(int(system.arena.acquisition_kind[receiver_row]), ACQUISITION_TRANSFER)
            self.assertEqual(int(system.arena.sample_count[receiver_row]), 0)
            self.assertEqual(int(system.arena.last_verified_tick[receiver_row]), 0)
            confidence_received = float(system.arena.confidence[receiver_row])

            same_tick = self._plan(
                tick=1,
                carriers=(1,),
                entity_ids=(2,),
                holders=(202,),
                contexts=(7,),
                actions=(2,),
            )
            same_stats = system.commit_outcomes(same_tick, energy=energy, alive=alive)
            self.assertEqual(same_stats.outcome_updates, 0)
            self.assertEqual(int(system.arena.sample_count[receiver_row]), 0)
            self.assertEqual(float(system.arena.confidence[receiver_row]), confidence_received)

            later = self._plan(
                tick=2,
                carriers=(1,),
                entity_ids=(2,),
                holders=(202,),
                contexts=(7,),
                actions=(2,),
                outcomes=((1.5, 0, 0, 0, 0),),
            )
            later_stats = system.commit_outcomes(later, energy=energy, alive=alive)
            self.assertEqual(later_stats.transferred_copies_verified, 1)
            self.assertEqual(int(system.arena.sample_count[receiver_row]), 1)
            self.assertEqual(int(system.arena.last_verified_tick[receiver_row]), 2)
            self.assertGreater(float(system.arena.confidence[receiver_row]), confidence_received)
            system.close()

    def test_incremental_outcome_mean_and_status_accounting(self) -> None:
        cfg = self._cfg(experience_creation_enabled=False)
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
                outcome_vector=np.asarray([1, 0, 0, 0, 0], dtype=np.float32),
                encoded_bytes=64,
                created_tick=0,
                source_subject_id=101,
            )
            system.arena.append(
                holder_subject_id=101,
                content_id=content,
                source_subject_id=101,
                confidence=0.25,
                sample_count=1,
                created_tick=0,
                last_verified_tick=0,
                encoded_bytes=64,
                outcome_mean=np.asarray([1, 0, 0, 0, 0], dtype=np.float32),
                acquisition_kind=ACQUISITION_PRIVATE_EXPERIENCE,
            )
            plan = self._plan(
                tick=2,
                carriers=(0, 1, 2),
                entity_ids=(1, 2, 3),
                holders=(101, 202, 303),
                contexts=(7, 8, 9),
                actions=(2, 3, 4),
                statuses=(OUTCOME_STATUS_SUCCESS, OUTCOME_STATUS_FAILED, OUTCOME_STATUS_PARTIAL),
                failures=(0, 3, 0),
                outcomes=((3, 0, 0, 0, 0), (0, 0, 0, 0, 0), (0.5, 0, 0, 0, 0)),
            )
            stats = system.commit_outcomes(
                plan,
                energy=np.asarray([2.0, 2.0, 2.0], dtype=np.float32),
                alive=np.asarray([True, True, True]),
            )
            row = system.arena.rows_for_holder(101)[0]
            self.assertAlmostEqual(float(system.arena.outcome_mean[row, 0]), 2.0, places=6)
            self.assertEqual(int(system.arena.sample_count[row]), 2)
            self.assertEqual(stats.outcome_success, 1)
            self.assertEqual(stats.outcome_failed, 1)
            self.assertEqual(stats.outcome_partial, 1)
            self.assertEqual(stats.outcome_updates, 1)
            self.assertEqual(stats.outcome_unmatched, 2)
            system.close()

    def test_permutation_stable_private_creation(self) -> None:
        cfg = self._cfg(verification_energy_cost=0.0)
        plan_a = self._plan(
            tick=3,
            carriers=(0, 1),
            entity_ids=(10, 20),
            holders=(110, 220),
            contexts=(5, 6),
            actions=(1, 2),
            statuses=(OUTCOME_STATUS_SUCCESS, OUTCOME_STATUS_SUCCESS),
            failures=(0, 0),
            outcomes=((1, 2, 3, 4, 5), (5, 4, 3, 2, 1)),
        )
        plan_b = self._plan(
            tick=3,
            carriers=(1, 0),
            entity_ids=(20, 10),
            holders=(220, 110),
            contexts=(6, 5),
            actions=(2, 1),
            statuses=(OUTCOME_STATUS_SUCCESS, OUTCOME_STATUS_SUCCESS),
            failures=(0, 0),
            outcomes=((5, 4, 3, 2, 1), (1, 2, 3, 4, 5)),
        )
        with tempfile.TemporaryDirectory() as tmp:
            a = KnowledgeSystem(
                cfg,
                Path(tmp) / "a",
                initial_entity_ids=np.empty(0, dtype=np.uint64),
                initial_subject_ids=np.empty(0, dtype=np.uint64),
            )
            b = KnowledgeSystem(
                cfg,
                Path(tmp) / "b",
                initial_entity_ids=np.empty(0, dtype=np.uint64),
                initial_subject_ids=np.empty(0, dtype=np.uint64),
            )
            a.commit_outcomes(plan_a, energy=np.ones(2, dtype=np.float32), alive=np.ones(2, dtype=bool))
            b.commit_outcomes(plan_b, energy=np.ones(2, dtype=np.float32), alive=np.ones(2, dtype=bool))
            arrays_a = a.checkpoint_arrays()
            arrays_b = b.checkpoint_arrays()
            self.assertEqual(set(arrays_a), set(arrays_b))
            for name in arrays_a:
                self.assertTrue(np.array_equal(arrays_a[name], arrays_b[name]), name)
            a.close(); b.close()

    def test_clone_preserves_k2_state_without_aliasing(self) -> None:
        cfg = self._cfg(verification_energy_cost=0.0)
        with tempfile.TemporaryDirectory() as tmp:
            source = KnowledgeSystem(
                cfg,
                Path(tmp) / "source",
                initial_entity_ids=np.empty(0, dtype=np.uint64),
                initial_subject_ids=np.empty(0, dtype=np.uint64),
            )
            source.commit_outcomes(
                self._plan(tick=1),
                energy=np.ones(1, dtype=np.float32),
                alive=np.ones(1, dtype=bool),
            )
            branch = source.clone(Path(tmp) / "branch")
            for name, value in source.checkpoint_arrays().items():
                self.assertTrue(np.array_equal(value, branch.checkpoint_arrays()[name]), name)
            branch.arena.confidence[0] = np.float32(0.0)
            self.assertNotEqual(
                float(source.arena.confidence[0]),
                float(branch.arena.confidence[0]),
            )
            source.close(); branch.close()

    def test_short_simulation_creates_local_experience_without_policy_influence(self) -> None:
        base = self._cfg(
            transfer_probability=0.0,
            initial_content_count=0,
            initial_holders_fraction=0.0,
            verification_energy_cost=0.0,
        )
        cfg = replace(
            base,
            run=replace(base.run, ticks=3, metrics_period=3, checkpoint_period=3, validation_mode=True),
            world=replace(base.world, width=32.0, height=32.0, grid_x=8, grid_y=8, initial_entities=40, max_entities=64),
        )
        with tempfile.TemporaryDirectory() as tmp:
            simulation = Simulation(cfg, tmp, backend="cpu")
            for _ in range(3):
                simulation.step()
            summary = simulation.knowledge.summary()
            self.assertGreater(int(summary["outcome_records_total"]), 0)
            self.assertGreater(int(summary["private_experiences_created_total"]), 0)
            self.assertFalse(bool(summary["policy_influence"]))
            simulation.metrics.close(); simulation.evolution_progress.close(); simulation.knowledge.close()


if __name__ == "__main__":
    unittest.main()
