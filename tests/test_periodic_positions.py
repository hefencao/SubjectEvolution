from __future__ import annotations

from dataclasses import replace
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import numpy as np

from subject_evolution.config import load_config
from subject_evolution.lifecycle import BirthRequestPlan, plan_birth_allocations
from subject_evolution.simulation import EntityState, Simulation, _wrap_periodic_float32


ROOT = Path(__file__).resolve().parents[1]


class PeriodicPositionTests(unittest.TestCase):
    def _cfg(self):
        base = load_config(ROOT / "configs" / "mvp_short_k1_compat.json")
        return replace(
            base,
            run=replace(
                base.run,
                ticks=2,
                metrics_period=2,
                checkpoint_period=2,
                validation_mode=True,
            ),
            world=replace(
                base.world,
                width=256.0,
                height=256.0,
                grid_x=16,
                grid_y=16,
                initial_entities=1,
                max_entities=2,
                periodic=True,
            ),
            policy=replace(base.policy, mutation_probability=0.0),
        )

    def test_canonical_wrap_repairs_float32_rounded_upper_endpoint(self) -> None:
        values = np.asarray(
            [
                -1.0e-7,
                np.nextafter(np.float32(0.0), np.float32(-np.inf)),
                0.0,
                255.5,
                256.0,
                512.0,
            ],
            dtype=np.float32,
        )
        raw = np.remainder(values, np.float32(256.0))
        self.assertEqual(float(raw[0]), 256.0)  # Reproduces the original bug.

        wrapped = _wrap_periodic_float32(values, 256.0)
        self.assertTrue(np.all(np.isfinite(wrapped)))
        self.assertTrue(np.all(wrapped >= 0.0))
        self.assertTrue(np.all(wrapped < 256.0))
        self.assertEqual(float(wrapped[0]), 0.0)
        self.assertEqual(float(wrapped[1]), 0.0)
        self.assertEqual(float(wrapped[3]), 255.5)
        self.assertEqual(float(wrapped[4]), 0.0)
        self.assertEqual(float(wrapped[5]), 0.0)

    def test_birth_wrap_never_commits_extent_value(self) -> None:
        cfg = self._cfg()
        entities = EntityState(cfg)
        entities.x[0] = np.float32(0.0)
        entities.y[0] = np.float32(0.0)
        entities.primary_subject_id[0] = np.uint64(1)
        requests = BirthRequestPlan(
            source_rows=np.asarray([0], dtype=np.int32),
            parent_indices=np.asarray([0], dtype=np.int32),
            parent_entity_ids=np.asarray([1], dtype=np.uint64),
            parent_subject_ids=np.asarray([1], dtype=np.uint64),
            tick=1,
            capacity_arbitration=cfg.entities.reproduction_capacity_arbitration,
            capacity_candidate_count=1,
            capacity_available_slots=1,
        )
        plan = plan_birth_allocations(
            requests,
            entities.free_slots,
            int(entities.next_entity_id),
            entities.free_slot_version,
        )

        def fake_normal(ctx, ids, mean, stddev, draw_index, **kwargs):
            if ctx.phase == 70 and draw_index in (0, 2):
                return np.full(ids.shape, -1.0e-7, dtype=np.float32)
            return np.zeros(ids.shape, dtype=np.float32)

        with patch("subject_evolution.simulation.normal", side_effect=fake_normal):
            _, slots = entities.commit_births(plan)

        child = int(slots[0])
        self.assertEqual(float(entities.x[child]), 0.0)
        self.assertEqual(float(entities.y[child]), 0.0)
        self.assertLess(float(entities.x[child]), cfg.world.width)
        self.assertLess(float(entities.y[child]), cfg.world.height)

    def test_position_invariant_reports_offending_entity_and_coordinates(self) -> None:
        cfg = self._cfg()
        with tempfile.TemporaryDirectory() as tmp:
            simulation = Simulation(cfg, Path(tmp) / "run", backend="cpu")
            try:
                simulation.entities.x[0] = np.float32(256.0)
                with self.assertRaisesRegex(
                    AssertionError,
                    r"entity_id=1.*x=256\.0.*width=256\.0",
                ):
                    simulation._validate_invariants()
            finally:
                simulation.metrics.close()
                simulation.evolution_progress.close()
                simulation.knowledge.close()


if __name__ == "__main__":
    unittest.main()
