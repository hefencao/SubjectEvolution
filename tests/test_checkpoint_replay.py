from __future__ import annotations

from dataclasses import fields, is_dataclass, replace
from pathlib import Path
import tempfile
import unittest

import numpy as np

from se.cfg import load_config
from se.runtime.sim import Simulation


ROOT = Path(__file__).resolve().parents[1]


def assert_state_equal(test: unittest.TestCase, left, right, path: str = "state") -> None:
    if isinstance(left, np.ndarray) or isinstance(right, np.ndarray):
        test.assertIsInstance(left, np.ndarray, path)
        test.assertIsInstance(right, np.ndarray, path)
        test.assertEqual(left.dtype, right.dtype, path)
        test.assertEqual(left.shape, right.shape, path)
        test.assertTrue(np.array_equal(left, right, equal_nan=True), path)
        return
    if is_dataclass(left) or is_dataclass(right):
        test.assertTrue(is_dataclass(left) and is_dataclass(right), path)
        test.assertIs(type(left), type(right), path)
        for field in fields(left):
            assert_state_equal(
                test,
                getattr(left, field.name),
                getattr(right, field.name),
                f"{path}.{field.name}",
            )
        return
    if isinstance(left, dict) or isinstance(right, dict):
        test.assertIsInstance(left, dict, path)
        test.assertIsInstance(right, dict, path)
        test.assertEqual(set(left), set(right), path)
        for key in sorted(left, key=str):
            assert_state_equal(test, left[key], right[key], f"{path}[{key!r}]")
        return
    if isinstance(left, (list, tuple)) or isinstance(right, (list, tuple)):
        test.assertIs(type(left), type(right), path)
        test.assertEqual(len(left), len(right), path)
        for index, (a, b) in enumerate(zip(left, right, strict=True)):
            assert_state_equal(test, a, b, f"{path}[{index}]")
        return
    if hasattr(left, "__dict__") or hasattr(right, "__dict__"):
        test.assertIs(type(left), type(right), path)
        assert_state_equal(test, vars(left), vars(right), path + ".__dict__")
        return
    if isinstance(left, float) or isinstance(right, float):
        if np.isnan(left) and np.isnan(right):
            return
    test.assertEqual(left, right, path)


class FullCheckpointReplayTests(unittest.TestCase):
    def config(self, *, ticks: int = 12, full_checkpoint: bool = False):
        cfg = load_config(ROOT / "configs" / "mvp_short_k4_candidates.json")
        return replace(
            cfg,
            run=replace(
                cfg.run,
                ticks=ticks,
                metrics_period=max(ticks, 1),
                checkpoint_period=6,
                evolution_evaluation_period=6,
                validation_mode=True,
                full_checkpoint_enabled=full_checkpoint,
            ),
            world=replace(
                cfg.world,
                width=64.0,
                height=64.0,
                grid_x=16,
                grid_y=16,
                initial_entities=64,
                max_entities=96,
            ),
            information=replace(cfg.information, signal_flush_periods=(2, 3, 4)),
            social=replace(cfg.social, group_update_period=3),
            knowledge=replace(cfg.knowledge, candidate_update_period=3),
        )

    def test_restored_continuation_matches_continuous_world_exactly(self) -> None:
        cfg = self.config(ticks=12)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            continuous = Simulation(cfg, root / "continuous", backend="cpu")
            for _ in range(6):
                continuous.step()
            checkpoint = continuous.save_full_checkpoint(root / "tick6.sechk")
            restored = Simulation.from_checkpoint(
                checkpoint,
                root / "restored",
                backend="cpu",
                until_tick=12,
            )
            for _ in range(6):
                continuous.step()
                restored.step()
            assert_state_equal(
                self,
                continuous._full_checkpoint_state(),
                restored._full_checkpoint_state(),
            )
            continuous.knowledge.close()
            continuous.evolution_progress.close()
            continuous.metrics.close()
            restored.knowledge.close()
            restored.evolution_progress.close()
            restored.metrics.close()

    def test_checkpoint_branch_matches_in_memory_branch(self) -> None:
        cfg = self.config(ticks=10)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = Simulation(cfg, root / "source", backend="cpu")
            for _ in range(5):
                source.step()
            checkpoint = source.save_full_checkpoint(root / "branch.sechk")

            baseline_memory = source.clone(root / "baseline_memory")
            intervention_memory = source.clone(root / "intervention_memory")
            intervention_memory.apply_intervention("disable-social-control")

            baseline_disk = Simulation.from_checkpoint(
                checkpoint, root / "baseline_disk", backend="cpu", until_tick=10
            )
            intervention_disk = Simulation.from_checkpoint(
                checkpoint, root / "intervention_disk", backend="cpu", until_tick=10
            )
            intervention_disk.apply_intervention("disable-social-control")

            for _ in range(5):
                baseline_memory.step()
                intervention_memory.step()
                baseline_disk.step()
                intervention_disk.step()

            assert_state_equal(
                self,
                baseline_memory._full_checkpoint_state(),
                baseline_disk._full_checkpoint_state(),
                "baseline",
            )
            assert_state_equal(
                self,
                intervention_memory._full_checkpoint_state(),
                intervention_disk._full_checkpoint_state(),
                "intervention",
            )
            for simulation in (
                source,
                baseline_memory,
                intervention_memory,
                baseline_disk,
                intervention_disk,
            ):
                simulation.knowledge.close()
                simulation.evolution_progress.close()
                simulation.metrics.close()

    def test_periodic_checkpoint_writes_full_bundle_when_enabled(self) -> None:
        cfg = self.config(ticks=6, full_checkpoint=True)
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "run"
            simulation = Simulation(cfg, output, backend="cpu")
            simulation.run()
            self.assertTrue((output / "checkpoint_00000006.npz").is_file())
            self.assertTrue((output / "checkpoint_00000006.sechk").is_file())


if __name__ == "__main__":
    unittest.main()
