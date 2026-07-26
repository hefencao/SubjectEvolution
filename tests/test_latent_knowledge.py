from __future__ import annotations

from dataclasses import replace
from pathlib import Path
import tempfile
import unittest

import numpy as np

from se.cfg import load_config, validate_config
from se.knowledge import (
    ACQUISITION_PRIVATE_EXPERIENCE,
    KnowledgeObservationPlan,
    KnowledgeSystem,
    OUTCOME_WIDTH,
)
from se.knowledge.policy import build_latent_knowledge_policy_plan
from se.knowledge.latent import latent_router_state_features
from se.policy import Action, ParametricPolicy
from se.runtime.sim import Simulation
from tests.test_checkpoint_replay import assert_state_equal


ROOT = Path(__file__).resolve().parents[1]


def _readonly(value, dtype):
    result = np.asarray(value, dtype=dtype)
    result.setflags(write=False)
    return result


class VariableLatentKnowledgeTests(unittest.TestCase):
    def _cfg(self, **knowledge_overrides):
        base = load_config(ROOT / "configs" / "mvp_short_latent_private.json")
        knowledge = replace(base.knowledge, **knowledge_overrides)
        cfg = replace(base, knowledge=knowledge)
        validate_config(cfg)
        return cfg

    def test_latent_schema_has_separate_genome_and_variable_lengths(self) -> None:
        latent = self._cfg()
        k3 = load_config(ROOT / "configs" / "mvp_short_k3_private.json")
        self.assertEqual(ParametricPolicy.genome_size_for_config(k3), 142)
        self.assertEqual(ParametricPolicy.genome_size_for_config(latent), 246)
        self.assertEqual(ParametricPolicy.STRATEGY_STOP, 136)
        with tempfile.TemporaryDirectory() as tmp:
            system = KnowledgeSystem(
                latent,
                tmp,
                initial_entity_ids=np.arange(1, 65, dtype=np.uint64),
                initial_subject_ids=np.arange(101, 165, dtype=np.uint64),
            )
            try:
                self.assertIsNotNone(system.latent_store)
                lengths = system.latent_store.length[: system.latent_store.size]
                self.assertGreater(lengths.size, 0)
                self.assertGreater(np.unique(lengths).size, 1)
                self.assertTrue(set(int(v) for v in lengths).issubset(set(latent.knowledge.latent_length_levels)))
                for row, length in enumerate(lengths):
                    expected = (
                        latent.knowledge.latent_base_encoded_bytes
                        + int(length) * latent.knowledge.latent_bytes_per_value
                    )
                    self.assertEqual(int(system.catalog.encoded_bytes[row]), expected)
            finally:
                system.close()

    def _manual_plan(self, reverse: bool = False):
        cfg = self._cfg(initial_content_count=0, initial_holders_fraction=0.0)
        with tempfile.TemporaryDirectory() as tmp:
            system = KnowledgeSystem(
                cfg,
                tmp,
                initial_entity_ids=np.asarray([1], dtype=np.uint64),
                initial_subject_ids=np.asarray([101], dtype=np.uint64),
            )
            try:
                contents = []
                for index, outcome in enumerate(
                    (
                        np.asarray([1.0, 0.0, 0.25, 0.0, 0.0], dtype=np.float32),
                        np.asarray([0.0, 0.5, 0.0, 0.25, 0.0], dtype=np.float32),
                    )
                ):
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
                    contents.append(content)
                observation = system.publish(2)
                if reverse:
                    order = np.arange(observation.copy_count - 1, -1, -1)
                    observation = KnowledgeObservationPlan(
                        tick=observation.tick,
                        holder_subject_ids=observation.holder_subject_ids,
                        holder_starts=observation.holder_starts,
                        holder_counts=observation.holder_counts,
                        copy_ids=_readonly(observation.copy_ids[order], np.uint64),
                        content_ids=_readonly(observation.content_ids[order], np.uint64),
                        context_keys=_readonly(observation.context_keys[order], np.uint64),
                        action_ids=_readonly(observation.action_ids[order], np.int16),
                        outcome_vectors=_readonly(observation.outcome_vectors[order], np.float32),
                        confidences=_readonly(observation.confidences[order], np.float32),
                        sample_counts=_readonly(observation.sample_counts[order], np.uint32),
                        acquisition_kinds=_readonly(observation.acquisition_kinds[order], np.uint8),
                        encoded_bytes=_readonly(observation.encoded_bytes[order], np.uint32),
                    )
                genotype = np.zeros(
                    (1, ParametricPolicy.genome_size_for_config(cfg)), dtype=np.float32
                )
                genotype[0, ParametricPolicy.KNOWLEDGE_USE_STRENGTH_INDEX] = 1.0
                start = ParametricPolicy.latent_router_gene_start(cfg)
                hidden = cfg.knowledge.latent_router_hidden_width
                # Route hidden channel zero toward HARVEST and add a small
                # explicit bias so the test cannot depend on a lucky sign.
                latent_index = start + int(Action.HARVEST) * hidden
                genotype[0, latent_index] = 0.75
                bias_start = start + len(Action) * hidden + len(Action) * 4
                genotype[0, bias_start + int(Action.HARVEST)] = 0.25
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
                return plan, cfg
            finally:
                system.close()

    def test_quantized_router_is_deterministic_and_auditable(self) -> None:
        first, cfg = self._manual_plan()
        second, _ = self._manual_plan()
        self.assertGreater(first.size, 0)
        self.assertEqual(first.router_schema, "quantized-linear-latent-router-v1")
        self.assertTrue(np.array_equal(first.quantized_residuals, second.quantized_residuals))
        self.assertTrue(np.array_equal(first.active_rows, second.active_rows))
        self.assertTrue(np.array_equal(first.action_ids, second.action_ids))
        scale = cfg.knowledge.latent_value_quantization_scale
        reconstructed = first.quantized_residuals.astype(np.float64) / scale
        self.assertTrue(np.array_equal(first.residuals, reconstructed.astype(np.float32)))
        self.assertTrue(np.all(first.latent_dimension_counts > 0))
        self.assertTrue(np.all(first.latent_max_widths > 0))

    def test_copy_order_does_not_change_published_residual(self) -> None:
        ordered, _ = self._manual_plan(False)
        reversed_plan, _ = self._manual_plan(True)
        self.assertTrue(np.array_equal(ordered.active_rows, reversed_plan.active_rows))
        self.assertTrue(np.array_equal(ordered.action_ids, reversed_plan.action_ids))
        self.assertTrue(np.array_equal(ordered.quantized_residuals, reversed_plan.quantized_residuals))

    def test_latent_snapshot_clone_and_short_world_are_stable(self) -> None:
        cfg = self._cfg()
        cfg = replace(
            cfg,
            run=replace(cfg.run, ticks=6, metrics_period=3, checkpoint_period=3),
            world=replace(cfg.world, initial_entities=48, max_entities=64),
        )
        with tempfile.TemporaryDirectory() as tmp:
            simulation = Simulation(cfg, Path(tmp) / "source", backend="cpu")
            for _ in range(3):
                simulation.step()
            branch = simulation.clone(Path(tmp) / "clone")
            try:
                self.assertIsNotNone(simulation.knowledge.latent_store)
                self.assertTrue(
                    np.array_equal(
                        simulation.knowledge.latent_store.arrays()["values"],
                        branch.knowledge.latent_store.arrays()["values"],
                    )
                )
                for _ in range(3):
                    simulation.step()
                    branch.step()
                self.assertTrue(np.array_equal(simulation.entities.alive, branch.entities.alive))
                self.assertTrue(np.array_equal(simulation.entities.genotype, branch.entities.genotype))
                self.assertTrue(
                    np.array_equal(
                        simulation.knowledge.checkpoint_arrays()["knowledge_latent_values"],
                        branch.knowledge.checkpoint_arrays()["knowledge_latent_values"],
                    )
                )
            finally:
                for item in (simulation, branch):
                    item.knowledge.close()
                    item.metrics.close()
                    item.evolution_progress.close()

    def test_variant_lineage_can_mutate_length_level(self) -> None:
        cfg = self._cfg(
            initial_content_count=0,
            initial_holders_fraction=0.0,
            latent_length_mutation_probability=1.0,
        )
        with tempfile.TemporaryDirectory() as tmp:
            system = KnowledgeSystem(
                cfg,
                tmp,
                initial_entity_ids=np.asarray([1], dtype=np.uint64),
                initial_subject_ids=np.asarray([101], dtype=np.uint64),
            )
            try:
                root_bytes = system._encoded_bytes_for_new_content(
                    parent_content_id=0,
                    context_key=7,
                    action_id=int(Action.HARVEST),
                    source_subject_id=101,
                )
                root = system.catalog.append(
                    parent_content_id=0,
                    context_key=7,
                    action_id=int(Action.HARVEST),
                    outcome_vector=np.zeros(OUTCOME_WIDTH, dtype=np.float32),
                    encoded_bytes=root_bytes,
                    created_tick=1,
                    source_subject_id=101,
                )
                system.latent_store.ensure_catalog(system.catalog)
                child_bytes = system._encoded_bytes_for_new_content(
                    parent_content_id=root,
                    context_key=7,
                    action_id=int(Action.HARVEST),
                    source_subject_id=101,
                )
                child = system.catalog.append(
                    parent_content_id=root,
                    context_key=7,
                    action_id=int(Action.HARVEST),
                    outcome_vector=np.zeros(OUTCOME_WIDTH, dtype=np.float32),
                    encoded_bytes=child_bytes,
                    created_tick=2,
                    source_subject_id=101,
                )
                system.latent_store.ensure_catalog(system.catalog)
                root_length = int(system.latent_store.length[root - 1])
                child_length = int(system.latent_store.length[child - 1])
                self.assertNotEqual(root_length, child_length)
                self.assertEqual(
                    int(system.catalog.encoded_bytes[child - 1]),
                    cfg.knowledge.latent_base_encoded_bytes
                    + child_length * cfg.knowledge.latent_bytes_per_value,
                )
            finally:
                system.close()

    def test_full_checkpoint_restores_variable_latent_world_exactly(self) -> None:
        cfg = self._cfg()
        cfg = replace(
            cfg,
            run=replace(cfg.run, ticks=8, metrics_period=4, checkpoint_period=4),
            world=replace(cfg.world, initial_entities=32, max_entities=48),
        )
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            continuous = Simulation(cfg, root / "continuous", backend="cpu")
            for _ in range(4):
                continuous.step()
            checkpoint = continuous.save_full_checkpoint(root / "latent_tick4.sechk")
            restored = Simulation.from_checkpoint(
                checkpoint, root / "restored", backend="cpu", until_tick=8
            )
            try:
                for _ in range(4):
                    continuous.step()
                    restored.step()
                assert_state_equal(
                    self,
                    continuous._full_checkpoint_state(),
                    restored._full_checkpoint_state(),
                    "latent_world",
                )
            finally:
                for item in (continuous, restored):
                    item.knowledge.close()
                    item.metrics.close()
                    item.evolution_progress.close()


if __name__ == "__main__":
    unittest.main()
