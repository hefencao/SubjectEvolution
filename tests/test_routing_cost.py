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
    OUTCOME_WIDTH,
)
from se.knowledge.policy import KnowledgePolicyPlan
from se.knowledge.latent import (
    LATENT_MLP_ROUTER_SCHEMA,
    LATENT_ROUTER_SCHEMA,
)
from se.policy import Action
from se.knowledge.routing_cost import apply_routing_cost_budget
from se.runtime.sim import Simulation
from tests.test_checkpoint_replay import assert_state_equal

ROOT = Path(__file__).resolve().parents[1]


def synthetic_plan(router_schema: str) -> KnowledgePolicyPlan:
    # Entity row zero publishes two actions; row one publishes one action.
    active_rows = np.asarray([0, 0, 1], dtype=np.int32)
    return KnowledgePolicyPlan(
        tick=3,
        active_rows=active_rows,
        entity_ids=np.asarray([11, 11, 12], dtype=np.uint64),
        holder_subject_ids=np.asarray([101, 101, 102], dtype=np.uint64),
        context_keys=np.asarray([7, 7, 8], dtype=np.uint64),
        action_ids=np.asarray([1, 3, 4], dtype=np.int16),
        residuals=np.asarray([0.25, -0.125, 0.5], dtype=np.float32),
        support_copy_counts=np.asarray([2, 2, 1], dtype=np.uint16),
        private_support_counts=np.asarray([2, 2, 1], dtype=np.uint16),
        transfer_support_counts=np.zeros(3, dtype=np.uint16),
        unverified_transfer_support_counts=np.zeros(3, dtype=np.uint16),
        reliability_mass=np.ones(3, dtype=np.float32),
        weighted_outcome_vectors=np.zeros((3, OUTCOME_WIDTH), dtype=np.float32),
        latent_dimension_counts=np.asarray([12, 12, 4], dtype=np.uint32),
        latent_max_widths=np.asarray([8, 8, 4], dtype=np.uint16),
        quantized_residuals=np.asarray([1024, -512, 2048], dtype=np.int32),
        router_saturation_counts=np.asarray([3, 3, 1], dtype=np.uint32),
        router_clipping_counts=np.asarray([1, 2, 0], dtype=np.uint32),
        router_hidden_abs_sums=np.asarray([100, 100, 20], dtype=np.uint64),
        router_hidden_active_counts=np.asarray([6, 6, 2], dtype=np.uint32),
        router_schema=router_schema,
    )


class RoutingCostTests(unittest.TestCase):
    def _cfg(self, *, mlp: bool = False, **overrides):
        name = (
            "mvp_short_latent_mlp_private.json"
            if mlp
            else "mvp_short_latent_private.json"
        )
        base = load_config(ROOT / "configs" / name)
        values = dict(
            routing_cost_enabled=True,
            routing_base_energy_cost=0.01,
            routing_energy_per_latent_dimension=1e-4,
            routing_energy_per_mac=1e-6,
            routing_energy_per_active_hidden_unit=2e-4,
            routing_energy_per_emitted_action=3e-4,
            routing_energy_per_saturation=4e-5,
            routing_energy_per_clipped_output=5e-5,
        )
        values.update(overrides)
        cfg = replace(base, knowledge=replace(base.knowledge, **values))
        validate_config(cfg)
        return cfg

    def test_l1_cost_formula_is_explicit_and_entity_scoped(self) -> None:
        cfg = self._cfg()
        plan = synthetic_plan(LATENT_ROUTER_SCHEMA)
        result = apply_routing_cost_budget(
            plan,
            active_energy=np.asarray([10.0, 10.0], dtype=np.float32),
            config=cfg.knowledge,
            action_count=len(Action),
        )
        # Row zero: 12*8 projection + 2*5*8 outcome injection +
        # 2*8*(8+4) linear router + 2*8 aggregation = 384 MACs.
        self.assertEqual(int(result.mac_count[0]), 384)
        expected = 0.01 + 12e-4 + 384e-6 + 6 * 2e-4 + 2 * 3e-4 + 3 * 4e-5 + 3 * 5e-5
        self.assertAlmostEqual(float(result.requested_energy[0]), expected, places=12)
        self.assertEqual(result.accepted_action_count, 3)
        self.assertEqual(result.rejected_action_count, 0)

    def test_l2_has_higher_mac_cost_for_same_payload(self) -> None:
        l1 = self._cfg(
            routing_base_energy_cost=0.0,
            routing_energy_per_latent_dimension=0.0,
            routing_energy_per_mac=1.0,
            routing_energy_per_active_hidden_unit=0.0,
            routing_energy_per_emitted_action=0.0,
            routing_energy_per_saturation=0.0,
            routing_energy_per_clipped_output=0.0,
        )
        l2 = self._cfg(
            mlp=True,
            routing_base_energy_cost=0.0,
            routing_energy_per_latent_dimension=0.0,
            routing_energy_per_mac=1.0,
            routing_energy_per_active_hidden_unit=0.0,
            routing_energy_per_emitted_action=0.0,
            routing_energy_per_saturation=0.0,
            routing_energy_per_clipped_output=0.0,
        )
        l1_result = apply_routing_cost_budget(
            synthetic_plan(LATENT_ROUTER_SCHEMA),
            active_energy=np.asarray([1e9, 1e9]),
            config=l1.knowledge,
            action_count=len(Action),
        )
        l2_result = apply_routing_cost_budget(
            synthetic_plan(LATENT_MLP_ROUTER_SCHEMA),
            active_energy=np.asarray([1e9, 1e9]),
            config=l2.knowledge,
            action_count=len(Action),
        )
        self.assertTrue(np.all(l2_result.mac_count > l1_result.mac_count))

    def test_insufficient_energy_rejects_whole_entity_plan_stably(self) -> None:
        cfg = self._cfg(routing_base_energy_cost=0.2)
        plan = synthetic_plan(LATENT_ROUTER_SCHEMA)
        first = apply_routing_cost_budget(
            plan,
            active_energy=np.asarray([1.0, 0.01], dtype=np.float32),
            config=cfg.knowledge,
            action_count=len(Action),
        )
        second = apply_routing_cost_budget(
            plan,
            active_energy=np.asarray([1.0, 0.01], dtype=np.float32),
            config=cfg.knowledge,
            action_count=len(Action),
        )
        self.assertTrue(np.array_equal(first.accepted, np.asarray([True, False])))
        self.assertTrue(np.array_equal(first.plan.active_rows, np.asarray([0, 0])))
        self.assertEqual(first.rejected_action_count, 1)
        self.assertTrue(np.array_equal(first.plan.active_rows, second.plan.active_rows))
        self.assertTrue(np.array_equal(first.committed_energy, second.committed_energy))

    def test_candidate_routing_cost_attribution_is_conserved(self) -> None:
        base = self._cfg()
        cfg = replace(
            base,
            knowledge=replace(
                base.knowledge,
                schema="dynamic-knowledge-latent-v1",
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
                initial_entity_ids=np.asarray([1], dtype=np.uint64),
                initial_subject_ids=np.asarray([101], dtype=np.uint64),
            )
            try:
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
                    outcome_vector=np.zeros(OUTCOME_WIDTH, dtype=np.float32),
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
                    encoded_bytes=encoded,
                    outcome_mean=np.zeros(OUTCOME_WIDTH, dtype=np.float32),
                    acquisition_kind=ACQUISITION_PRIVATE_EXPERIENCE,
                )
                system.publish(2)
                plan = synthetic_plan(LATENT_ROUTER_SCHEMA)
                # Align the synthetic first entity with the real holder/context.
                plan = replace(
                    plan,
                    holder_subject_ids=np.asarray([101, 101, 101], dtype=np.uint64),
                    context_keys=np.asarray([7, 7, 7], dtype=np.uint64),
                )
                result = apply_routing_cost_budget(
                    plan,
                    active_energy=np.asarray([10.0, 10.0]),
                    config=cfg.knowledge,
                    action_count=len(Action),
                )
                stats = system.record_routing_cost(result)
                self.assertAlmostEqual(
                    float(system.candidates.routing_cost[: system.catalog.size].sum()),
                    stats.routing_committed_energy,
                    places=12,
                )
            finally:
                system.close()

    def test_costed_checkpoint_restore_is_exact(self) -> None:
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
            checkpoint = continuous.save_full_checkpoint(root / "cost_tick3.sechk")
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
                    "costed_world",
                )
            finally:
                for simulation in (continuous, restored):
                    simulation.knowledge.close()
                    simulation.metrics.close()
                    simulation.evolution_progress.close()


if __name__ == "__main__":
    unittest.main()
