from __future__ import annotations

from dataclasses import replace
from pathlib import Path
import tempfile
import unittest

import numpy as np

from subject_evolution.config import load_config, validate_config
from subject_evolution.knowledge import ACQUISITION_PRIVATE_EXPERIENCE, KnowledgeSystem, OUTCOME_WIDTH
from subject_evolution.knowledge_policy import build_latent_knowledge_policy_plan
from subject_evolution.latent_knowledge import (
    LATENT_MLP_ROUTER_SCHEMA,
    LATENT_ROUTER_SCHEMA,
    latent_mlp_gene_start,
    latent_router_state_features,
    linear_latent_router_gene_count,
    mlp_latent_router_gene_count,
)
from subject_evolution.policy import Action, ParametricPolicy
from subject_evolution.simulation import Simulation
from tests.test_checkpoint_replay import assert_state_equal


ROOT = Path(__file__).resolve().parents[1]


class LatentRouterMlpTests(unittest.TestCase):
    def _cfg(self, **knowledge_overrides):
        base = load_config(ROOT / "configs" / "mvp_short_latent_mlp_private.json")
        cfg = replace(base, knowledge=replace(base.knowledge, **knowledge_overrides))
        validate_config(cfg)
        return cfg

    def test_l2_schema_retains_l1_prefix_and_has_separate_genome(self) -> None:
        l1 = load_config(ROOT / "configs" / "mvp_short_latent_private.json")
        l2 = self._cfg()
        self.assertEqual(l1.knowledge.latent_router_schema, LATENT_ROUTER_SCHEMA)
        self.assertEqual(l2.knowledge.latent_router_schema, LATENT_MLP_ROUTER_SCHEMA)
        self.assertEqual(ParametricPolicy.genome_size_for_config(l1), 246)
        self.assertEqual(ParametricPolicy.genome_size_for_config(l2), 446)
        l1_count = linear_latent_router_gene_count(l2.knowledge, len(Action))
        l2_count = mlp_latent_router_gene_count(l2.knowledge, len(Action))
        self.assertEqual(l1_count, 104)
        self.assertEqual(l2_count, 200)
        self.assertEqual(
            latent_mlp_gene_start(
                ParametricPolicy.latent_router_gene_start(l2), l2.knowledge, len(Action)
            ),
            ParametricPolicy.LATENT_ROUTER_START + l1_count,
        )

    def _manual_plan(self):
        cfg = self._cfg(
            initial_content_count=0,
            initial_holders_fraction=0.0,
            latent_router_activation_clip=0.5,
        )
        tmp = tempfile.TemporaryDirectory()
        system = KnowledgeSystem(
            cfg,
            tmp.name,
            initial_entity_ids=np.asarray([1], dtype=np.uint64),
            initial_subject_ids=np.asarray([101], dtype=np.uint64),
        )
        outcome = np.asarray([1.0, 0.25, 0.5, 0.0, 0.25], dtype=np.float32)
        encoded = system._encoded_bytes_for_new_content(
            parent_content_id=0,
            context_key=7,
            action_id=int(Action.HARVEST),
            source_subject_id=101,
        )
        content = system.catalog.append(
            parent_content_id=0,
            context_key=7,
            action_id=int(Action.HARVEST),
            outcome_vector=outcome,
            encoded_bytes=encoded,
            created_tick=1,
            source_subject_id=101,
        )
        system.latent_store.ensure_catalog(system.catalog)
        system.arena.append(
            holder_subject_id=101,
            content_id=content,
            source_subject_id=101,
            confidence=1.0,
            sample_count=4,
            created_tick=1,
            last_verified_tick=1,
            encoded_bytes=int(system.catalog.encoded_bytes[content - 1]),
            outcome_mean=outcome,
            acquisition_kind=ACQUISITION_PRIVATE_EXPERIENCE,
        )
        observation = system.publish(2)
        genotype = np.zeros(
            (1, ParametricPolicy.genome_size_for_config(cfg)), dtype=np.float32
        )
        genotype[0, ParametricPolicy.KNOWLEDGE_USE_STRENGTH_INDEX] = 1.0
        start = ParametricPolicy.latent_router_gene_start(cfg)
        projection_width = cfg.knowledge.latent_router_hidden_width
        # L1 shadow: a nonzero HARVEST bias.
        linear_bias_start = start + len(Action) * projection_width + len(Action) * 4
        genotype[0, linear_bias_start + int(Action.HARVEST)] = 0.25

        mlp_start = latent_mlp_gene_start(start, cfg.knowledge, len(Action))
        input_width = projection_width + 4 + 3
        mlp_width = cfg.knowledge.latent_router_mlp_hidden_width
        first_weight_count = mlp_width * input_width
        first_bias_start = mlp_start + first_weight_count
        # Force all hidden units beyond the 0.5 hard-tanh clip.
        genotype[0, first_bias_start : first_bias_start + mlp_width] = 1.0
        second_weight_start = first_bias_start + mlp_width
        harvest_second = second_weight_start + int(Action.HARVEST) * mlp_width
        genotype[0, harvest_second] = 1.0
        second_bias_start = second_weight_start + len(Action) * mlp_width
        genotype[0, second_bias_start + int(Action.HARVEST)] = 0.125

        state = latent_router_state_features(
            energy=np.asarray([2.0], dtype=np.float32),
            integrity=np.asarray([1.0], dtype=np.float32),
            fertility=np.asarray([0.25], dtype=np.float32),
            local_resource=np.asarray([0.5], dtype=np.float32),
            max_energy=cfg.entities.max_energy,
            resource_capacity=cfg.environment.resource_capacity[0],
        )
        plan = build_latent_knowledge_policy_plan(
            observation,
            system.latent_store,
            tick=2,
            entity_ids=np.asarray([1], dtype=np.uint64),
            holder_subject_ids=np.asarray([101], dtype=np.uint64),
            context_keys=np.asarray([7], dtype=np.uint64),
            genotype=genotype,
            router_gene_start=start,
            use_strength=ParametricPolicy.knowledge_use_strength_from_genotype(genotype),
            state_features=state,
            config=cfg.knowledge,
            action_count=len(Action),
        )
        return tmp, system, plan, cfg

    def test_l2_router_is_deterministic_nonlinear_and_auditable(self) -> None:
        first_tmp, first_system, first, cfg = self._manual_plan()
        second_tmp, second_system, second, _ = self._manual_plan()
        try:
            self.assertEqual(first.router_schema, LATENT_MLP_ROUTER_SCHEMA)
            self.assertGreater(first.size, 0)
            self.assertGreater(first.comparison_size, 0)
            self.assertTrue(np.array_equal(first.quantized_residuals, second.quantized_residuals))
            self.assertTrue(
                np.array_equal(
                    first.comparison_quantized_residuals,
                    second.comparison_quantized_residuals,
                )
            )
            self.assertGreater(int(first.router_saturation_counts.sum()), 0)
            self.assertGreater(int(first.router_hidden_active_counts.sum()), 0)
            self.assertFalse(
                np.array_equal(
                    first.quantized_residuals,
                    first.comparison_quantized_residuals,
                )
            )
            scale = cfg.knowledge.latent_value_quantization_scale
            self.assertTrue(
                np.array_equal(
                    first.residuals,
                    (first.quantized_residuals.astype(np.float64) / scale).astype(np.float32),
                )
            )
        finally:
            first_system.close()
            second_system.close()
            first_tmp.cleanup()
            second_tmp.cleanup()

    def test_l2_short_run_logs_shadow_and_router_diagnostics(self) -> None:
        cfg = self._cfg()
        cfg = replace(
            cfg,
            run=replace(cfg.run, ticks=3, metrics_period=1, checkpoint_period=3),
            world=replace(cfg.world, initial_entities=32, max_entities=48),
        )
        with tempfile.TemporaryDirectory() as tmp:
            simulation = Simulation(cfg, tmp, backend="cpu")
            try:
                for _ in range(3):
                    simulation.step()
                summary = simulation.knowledge.summary()
                self.assertGreater(summary["policy_router_hidden_active_units_total"], 0)
                self.assertGreaterEqual(summary["policy_linear_shadow_changed_actions_total"], 0)
                header = (Path(tmp) / "knowledge_policy_contributions.csv").read_text(
                    encoding="utf-8"
                ).splitlines()[0]
                self.assertIn("linear_shadow_logit_residual", header)
                self.assertIn("router_saturation_count", header)
            finally:
                simulation.knowledge.close()
                simulation.metrics.close()
                simulation.evolution_progress.close()

    def test_l2_full_checkpoint_restore_is_exact(self) -> None:
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
            checkpoint = continuous.save_full_checkpoint(root / "l2_tick3.sechk")
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
                    "l2_world",
                )
            finally:
                for item in (continuous, restored):
                    item.knowledge.close()
                    item.metrics.close()
                    item.evolution_progress.close()


if __name__ == "__main__":
    unittest.main()
