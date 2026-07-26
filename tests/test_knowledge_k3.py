from __future__ import annotations

from dataclasses import replace
from pathlib import Path
import tempfile
import unittest

import numpy as np

from se.cfg import load_config, validate_config
from se.information import InformationObservation
from se.knowledge import (
    ACQUISITION_PRIVATE_EXPERIENCE,
    ACQUISITION_SEED,
    ACQUISITION_TRANSFER,
    KnowledgeObservationPlan,
    OUTCOME_WIDTH,
)
from se.knowledge.policy import build_knowledge_policy_plan
from se.policy import Action, ParametricPolicy
from se.runtime.sim import Simulation


ROOT = Path(__file__).resolve().parents[1]


def _readonly(value, dtype):
    result = np.asarray(value, dtype=dtype)
    result.setflags(write=False)
    return result


class KnowledgeK3Tests(unittest.TestCase):
    def _cfg(self, **knowledge_overrides):
        base = load_config(ROOT / "configs" / "mvp_small.json")
        defaults = {
            "enabled": True,
            "schema": "dynamic-knowledge-k3-v1",
            "holder_capacity_bytes": 256,
            "encoded_bytes_per_copy": 64,
            "learning_enabled": True,
            "policy_influence_enabled": True,
            "policy_min_confidence": 0.0,
            "policy_min_local_samples": 1,
            "policy_sample_saturation": 1.0,
            "policy_unverified_transfer_weight": 0.25,
            "policy_outcome_scales": (1.0, 1.0, 1.0, 1.0, 1.0),
            "policy_outcome_clip": 1.0,
            "policy_max_abs_logit_residual": 1.0,
        }
        defaults.update(knowledge_overrides)
        knowledge = replace(base.knowledge, **defaults)
        policy = replace(
            base.policy,
            schema="inherited-linear-policy-knowledge-residual-v1",
        )
        cfg = replace(base, knowledge=knowledge, policy=policy)
        validate_config(cfg)
        return cfg

    def _observation(self, outcomes, *, samples, acquisition, confidences=None):
        count = len(outcomes)
        if confidences is None:
            confidences = np.ones(count, dtype=np.float32)
        return KnowledgeObservationPlan(
            tick=1,
            holder_subject_ids=_readonly([101], np.uint64),
            holder_starts=_readonly([0], np.int32),
            holder_counts=_readonly([count], np.int32),
            copy_ids=_readonly(np.arange(1, count + 1), np.uint64),
            content_ids=_readonly(np.arange(1, count + 1), np.uint64),
            context_keys=_readonly(np.full(count, 7), np.uint64),
            action_ids=_readonly(np.full(count, int(Action.HARVEST)), np.int16),
            outcome_vectors=_readonly(outcomes, np.float32),
            confidences=_readonly(confidences, np.float32),
            sample_counts=_readonly(samples, np.uint32),
            acquisition_kinds=_readonly(acquisition, np.uint8),
            encoded_bytes=_readonly(np.full(count, 64), np.uint32),
        )

    def test_k3_uses_separate_genome_schema(self) -> None:
        base = load_config(ROOT / "configs" / "mvp_small.json")
        k3 = self._cfg()
        self.assertEqual(ParametricPolicy.genome_size_for_config(base), 136)
        self.assertEqual(ParametricPolicy.genome_size_for_config(k3), 142)
        self.assertEqual(ParametricPolicy.STRATEGY_STOP, 136)

    def test_residual_is_local_context_action_and_duplicate_bounded(self) -> None:
        cfg = self._cfg()
        one = self._observation(
            [[1.0, 0, 0, 0, 0]],
            samples=[1],
            acquisition=[ACQUISITION_PRIVATE_EXPERIENCE],
        )
        duplicate = self._observation(
            [[1.0, 0, 0, 0, 0], [1.0, 0, 0, 0, 0]],
            samples=[1, 1],
            acquisition=[ACQUISITION_PRIVATE_EXPERIENCE] * 2,
        )
        kwargs = dict(
            tick=1,
            entity_ids=np.asarray([1], dtype=np.uint64),
            holder_subject_ids=np.asarray([101], dtype=np.uint64),
            context_keys=np.asarray([7], dtype=np.uint64),
            outcome_preferences=np.asarray([[1, 0, 0, 0, 0]], dtype=np.float32),
            use_strength=np.asarray([1], dtype=np.float32),
            config=cfg.knowledge,
            action_count=len(Action),
        )
        plan_one = build_knowledge_policy_plan(one, **kwargs)
        plan_two = build_knowledge_policy_plan(duplicate, **kwargs)
        self.assertEqual(plan_one.size, 1)
        self.assertAlmostEqual(float(plan_one.residuals[0]), 0.2, places=6)
        self.assertAlmostEqual(float(plan_two.residuals[0]), float(plan_one.residuals[0]), places=6)
        self.assertEqual(int(plan_two.support_copy_counts[0]), 2)
        mismatch = build_knowledge_policy_plan(
            one, **{**kwargs, "context_keys": np.asarray([8], dtype=np.uint64)}
        )
        self.assertEqual(mismatch.size, 0)

    def test_unverified_transfer_is_discounted_not_marked_verified(self) -> None:
        cfg = self._cfg(policy_unverified_transfer_weight=0.25)
        observation = self._observation(
            [[1.0, 0, 0, 0, 0], [1.0, 0, 0, 0, 0]],
            samples=[0, 0],
            acquisition=[ACQUISITION_TRANSFER, ACQUISITION_SEED],
        )
        plan = build_knowledge_policy_plan(
            observation,
            tick=1,
            entity_ids=np.asarray([1], dtype=np.uint64),
            holder_subject_ids=np.asarray([101], dtype=np.uint64),
            context_keys=np.asarray([7], dtype=np.uint64),
            outcome_preferences=np.asarray([[1, 0, 0, 0, 0]], dtype=np.float32),
            use_strength=np.asarray([1], dtype=np.float32),
            config=cfg.knowledge,
            action_count=len(Action),
        )
        self.assertEqual(plan.size, 1)
        self.assertEqual(int(plan.transfer_support_counts[0]), 1)
        self.assertEqual(int(plan.unverified_transfer_support_counts[0]), 1)
        self.assertAlmostEqual(float(plan.reliability_mass[0]), 0.25, places=6)

    def test_policy_reports_genetic_and_knowledge_logits_separately(self) -> None:
        cfg = self._cfg()
        policy = ParametricPolicy(cfg)
        genotype = np.zeros((1, ParametricPolicy.K3_GENOME_SIZE), dtype=np.float32)
        genotype[:, ParametricPolicy.KNOWLEDGE_PREFERENCE_START] = 1.0
        genotype[:, ParametricPolicy.KNOWLEDGE_USE_STRENGTH_INDEX] = 1.0
        observation = self._observation(
            [[1.0, 0, 0, 0, 0]],
            samples=[3],
            acquisition=[ACQUISITION_PRIVATE_EXPERIENCE],
        )
        plan = build_knowledge_policy_plan(
            observation,
            tick=1,
            entity_ids=np.asarray([1], dtype=np.uint64),
            holder_subject_ids=np.asarray([101], dtype=np.uint64),
            context_keys=np.asarray([7], dtype=np.uint64),
            outcome_preferences=ParametricPolicy.outcome_preferences_from_genotype(genotype),
            use_strength=ParametricPolicy.knowledge_use_strength_from_genotype(genotype),
            config=cfg.knowledge,
            action_count=len(Action),
        )
        info = InformationObservation(
            signals=np.zeros((1, 3), dtype=np.float32),
            signal_mask=np.zeros((1, 3), dtype=bool),
            signal_age=np.zeros((1, 3), dtype=np.float32),
            messages=np.empty((1, 0, 3), dtype=np.float32),
            message_mask=np.empty((1, 0), dtype=bool),
            message_age=np.empty((1, 0), dtype=np.uint32),
            message_confidence=np.empty((1, 0), dtype=np.float32),
            message_source_id=np.empty((1, 0), dtype=np.uint64),
            message_corruption=np.empty((1, 0), dtype=np.uint8),
            partner_energy=np.zeros((1, 1), dtype=np.float32),
            partner_group_match=np.zeros((1, 1), dtype=np.float32),
            partner_mask=np.zeros((1, 1), dtype=bool),
            uncertainty=np.zeros((1, 3), dtype=np.float32),
        )
        decision = policy.decide(
            active=np.asarray([0], dtype=np.int32),
            stable_ids=np.asarray([1], dtype=np.uint64),
            energy=np.asarray([2], dtype=np.float32),
            integrity=np.asarray([1], dtype=np.float32),
            fertility=np.asarray([0], dtype=np.float32),
            genotype=genotype,
            memory=np.zeros((1, 4), dtype=np.float32),
            local_resources=np.zeros((1, 4), dtype=np.float32),
            resource_gradient=(np.zeros(1, dtype=np.float32), np.zeros(1, dtype=np.float32)),
            danger_gradient=(np.zeros(1, dtype=np.float32), np.zeros(1, dtype=np.float32)),
            group_direction=(np.zeros(1, dtype=np.float32), np.zeros(1, dtype=np.float32)),
            partners=np.zeros((1, 1), dtype=np.int32),
            info=info,
            run_seed=1,
            tick=1,
            knowledge_plan=plan,
        )
        self.assertIsNotNone(decision.genetic_action)
        self.assertTrue(np.array_equal(decision.logits, decision.genetic_logits + decision.knowledge_logits))
        self.assertGreater(float(decision.knowledge_logits[0, Action.HARVEST]), 0.0)

    def test_k3_clone_preserves_state_and_next_step(self) -> None:
        cfg = self._cfg(log_policy_contributions=False)
        run = replace(cfg.run, ticks=3, metrics_period=3, checkpoint_period=3, validation_mode=True)
        world = replace(cfg.world, initial_entities=24, max_entities=32, grid_x=8, grid_y=8)
        cfg = replace(cfg, run=run, world=world)
        with tempfile.TemporaryDirectory() as tmp:
            source = Simulation(cfg, Path(tmp) / "source", backend="cpu")
            source.step()
            branch = source.clone(Path(tmp) / "branch")
            def snapshot(simulation):
                arrays = {
                    "entity_id": simulation.entities.entity_id.copy(),
                    "alive": simulation.entities.alive.copy(),
                    "energy": simulation.entities.energy.copy(),
                    "genotype": simulation.entities.genotype.copy(),
                    "memory": simulation.entities.memory.copy(),
                    "group_id": simulation.social.group_id.copy(),
                }
                arrays.update(simulation.knowledge.checkpoint_arrays())
                return arrays

            for name, value in snapshot(source).items():
                self.assertTrue(np.array_equal(value, snapshot(branch)[name]), name)
            source.step()
            branch.step()
            for name, value in snapshot(source).items():
                self.assertTrue(np.array_equal(value, snapshot(branch)[name]), name)
            for simulation in (source, branch):
                simulation.knowledge.close()
                simulation.metrics.close()
                simulation.evolution_progress.close()

    def test_short_k3_run_writes_contribution_audit(self) -> None:
        cfg = self._cfg(log_policy_contributions=True)
        run = replace(cfg.run, ticks=3, metrics_period=1, checkpoint_period=3, validation_mode=True)
        world = replace(cfg.world, initial_entities=24, max_entities=32, grid_x=8, grid_y=8)
        cfg = replace(cfg, run=run, world=world)
        with tempfile.TemporaryDirectory() as tmp:
            simulation = Simulation(cfg, tmp, backend="cpu")
            result = simulation.run()
            self.assertEqual(result["tick"], 3)
            self.assertEqual(simulation.entities.genotype.shape[1], 142)
            self.assertTrue((Path(tmp) / "knowledge_policy_contributions.csv").exists())
            self.assertTrue((Path(tmp) / "checkpoint_00000003.npz").exists())


if __name__ == "__main__":
    unittest.main()
