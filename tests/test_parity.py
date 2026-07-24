from __future__ import annotations

from dataclasses import replace
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import numpy as np

from subject_evolution.backend import Backend, BackendUnavailableError, cupy_available, resolve_backend
from subject_evolution.config import load_config
from subject_evolution.environment import Environment
from subject_evolution.gpu_environment import DeviceEnvironment, DeviceInformationField
from subject_evolution.gpu_runtime import HybridGpuRuntime
from subject_evolution.information import (
    DirectMessageObservationPlan,
    InformationSystem,
    SignalEmissionBatch,
    SignalEmissionPlan,
)
from subject_evolution.parity import (
    _array_state_snapshot,
    _simulation_stages,
    compare_array,
    run_stage_parity,
)
from subject_evolution.reductions import stable_segmented_sum
from subject_evolution.simulation import Simulation


ROOT = Path(__file__).resolve().parents[1]


class CpuGpuParityTests(unittest.TestCase):
    def _cfg(self):
        base = load_config(ROOT / "configs" / "mvp_short_k1_compat.json")
        return replace(
            base,
            run=replace(
                base.run,
                ticks=3,
                metrics_period=3,
                checkpoint_period=3,
                evolution_evaluation_period=10,
                validation_mode=True,
            ),
            world=replace(
                base.world,
                width=32.0,
                height=32.0,
                grid_x=8,
                grid_y=8,
                initial_entities=48,
                max_entities=64,
            ),
        )

    def _close(self, simulation: Simulation) -> None:
        simulation.metrics.close()
        simulation.evolution_progress.close()
        simulation.knowledge.close()

    def test_segmented_sum_device_algorithm_matches_reference_exactly(self) -> None:
        cells = np.asarray([3, 1, 3, 1, 1, 7, 3], dtype=np.int32)
        values = np.asarray([0.5, 1.0, 0.25, 0.125, 2.0, 4.0, 0.75], dtype=np.float32)
        reference = stable_segmented_sum(cells, values, 8, dtype=np.float32)
        candidate = stable_segmented_sum(cells, values, 8, backend="cpu", dtype=np.float32)
        self.assertTrue(np.array_equal(reference, candidate))


    def test_hybrid_harvest_commit_uses_cpu_reference_reduction(self) -> None:
        cfg = self._cfg()
        reference = Environment(cfg)
        runtime = object.__new__(HybridGpuRuntime)
        runtime.cfg = cfg
        runtime.backend = resolve_backend("cpu")
        runtime.environment = DeviceEnvironment(cfg, backend="cpu")
        runtime.environment.resources = reference.resources.copy()
        runtime._measure_transfers = False
        runtime._host_to_device_bytes = 0

        cells = np.asarray([5, 5, 5, 9, 9, 5, 9], dtype=np.int32)
        gathered = np.asarray(
            [
                [0.00029735, 0.00053816, 0.00197697, 0.0001],
                [0.00053816, 0.00197697, 0.00029735, 0.0002],
                [0.25, 0.125, 0.0625, 0.03125],
                [0.6, 0.1, 0.05, 0.025],
                [0.0000023, 0.0000047, 0.0000089, 0.0000011],
                [0.125, 0.0625, 0.03125, 0.015625],
                [0.125, 0.25, 0.375, 0.5],
            ],
            dtype=np.float32,
        )
        reference.commit_harvest(cells, gathered)
        runtime.commit_harvest(cells, gathered)
        self.assertTrue(
            np.array_equal(reference.resources, runtime.environment.resources)
        )

    def test_hybrid_signal_emission_uses_cpu_reference_reduction(self) -> None:
        cfg = self._cfg()
        reference = InformationSystem(cfg)
        runtime = object.__new__(HybridGpuRuntime)
        runtime.cfg = cfg
        runtime.backend = resolve_backend("cpu")
        runtime.information_field = DeviceInformationField(cfg, backend="cpu")
        runtime._measure_transfers = False
        runtime._host_to_device_bytes = 0

        # Unequal magnitudes expose backend-specific FP32 reduction trees.
        cells = np.asarray([5, 5, 5, 9, 9, 5, 9], dtype=np.int32)
        values = np.asarray(
            [0.00029735, 0.00053816, 1.97697, 0.6, 2.3e-6, 0.25, 0.125],
            dtype=np.float32,
        )
        plan = SignalEmissionPlan(
            (
                SignalEmissionBatch(0, cells, values, emitter="parity-test"),
                SignalEmissionBatch(0, cells[::-1], values[::-1], emitter="ordered-second"),
            )
        )
        reference.emit_plan(plan)
        runtime.emit_plan(plan)
        self.assertTrue(
            np.array_equal(reference.source, runtime.information_field.source)
        )

    def test_world_stage_report_uses_named_information_fields(self) -> None:
        cfg = self._cfg()
        with tempfile.TemporaryDirectory() as tmp:
            cpu = Simulation(cfg, Path(tmp) / "cpu", backend="cpu")
            candidate = Simulation(cfg, Path(tmp) / "candidate", backend="cpu")
            try:
                cpu.step()
                candidate.step()
                stages = dict(
                    (name, (reference, value))
                    for name, reference, value in _simulation_stages(cpu, candidate)
                )
                reference, value = stages["information-fields"]
                self.assertEqual(set(reference), {"field", "source", "age"})
                self.assertEqual(set(value), {"field", "source", "age"})
            finally:
                self._close(cpu)
                self._close(candidate)

    def test_device_observation_matches_cpu_reference_bitwise(self) -> None:
        cfg = self._cfg()
        with tempfile.TemporaryDirectory() as tmp:
            simulation = Simulation(cfg, Path(tmp) / "simulation", backend="cpu")
            try:
                entity = simulation.entities
                active = simulation.spatial.build(entity.x, entity.y, entity.alive)
                cells = simulation.spatial.entity_cells[active]
                partners = simulation.spatial.sample_partners(
                    active,
                    entity.entity_id,
                    cfg.run.seed,
                    0,
                    cfg.policy.partner_samples,
                )
                sensor_quality = entity.sensor_quality()
                cpu_info = simulation.information.observe(
                    active,
                    entity.entity_id,
                    cells,
                    partners,
                    entity.energy,
                    simulation.social.group_id,
                    sensor_quality,
                    cfg.run.seed,
                    0,
                )
                device_field = DeviceInformationField(cfg, backend="cpu")
                device_field.field = simulation.information.field.copy()
                device_field.source = simulation.information.source.copy()
                device_field.age = simulation.information.age.copy()
                device_info = device_field.observe(
                    stable_ids=entity.entity_id[active],
                    cell_ids=cells,
                    partners=partners,
                    energy=entity.energy,
                    group_id=simulation.social.group_id,
                    own_group_id=simulation.social.group_id[active],
                    sensor_quality=sensor_quality[active],
                    direct_message_plan=DirectMessageObservationPlan.empty(
                        active.size, cfg.information.direct_message_capacity
                    ),
                    run_seed=cfg.run.seed,
                    tick=0,
                )
                for name in (
                    "signals",
                    "signal_mask",
                    "signal_age",
                    "partner_energy",
                    "partner_group_match",
                    "partner_mask",
                    "uncertainty",
                ):
                    self.assertTrue(
                        np.array_equal(getattr(cpu_info, name), getattr(device_info, name)),
                        name,
                    )
            finally:
                self._close(simulation)

    def test_stage_parity_report_passes_on_numpy_device_path(self) -> None:
        cfg = self._cfg()
        with tempfile.TemporaryDirectory() as tmp:
            report = run_stage_parity(
                cfg,
                backend_name="cpu",
                ticks=3,
                output_dir=Path(tmp),
            )
        self.assertTrue(report["passed"])
        self.assertIsNone(report["first_failure_stage"])
        self.assertTrue(all(stage["passed"] for stage in report["stages"]))

    def test_gpu_request_never_silently_falls_back_to_cpu(self) -> None:
        if cupy_available():
            self.assertTrue(resolve_backend("gpu").is_gpu)
        else:
            with self.assertRaises(BackendUnavailableError):
                resolve_backend("gpu")

    @unittest.skipUnless(cupy_available(), "CuPy/CUDA GPU is unavailable")
    def test_real_gpu_stage_parity_when_available(self) -> None:
        cfg = self._cfg()
        with tempfile.TemporaryDirectory() as tmp:
            report = run_stage_parity(
                cfg,
                backend_name="gpu",
                ticks=2,
                output_dir=Path(tmp),
            )
        self.assertTrue(report["passed"], report.get("first_failure_stage"))


    def test_gpu_strict_reference_uses_cpu_authority_exactly(self) -> None:
        cfg = replace(
            self._cfg(),
            run=replace(self._cfg().run, gpu_semantics_mode="strict-reference"),
        )
        fake_gpu = Backend(name="gpu", xp=np, is_gpu=True)
        with tempfile.TemporaryDirectory() as tmp, patch(
            "subject_evolution.simulation.resolve_backend", return_value=fake_gpu
        ):
            cpu = Simulation(cfg, Path(tmp) / "cpu", backend="cpu")
            strict = Simulation(cfg, Path(tmp) / "strict", backend="gpu")
            try:
                self.assertEqual(strict.execution_backend, "gpu-strict-reference")
                self.assertIsNone(strict.gpu_runtime)
                self.assertTrue(strict.gpu_device_validated)
                self.assertFalse(strict.gpu_acceleration_enabled)
                for _ in range(3):
                    cpu.step()
                    strict.step()
                for name in (
                    "entity_id", "alive", "x", "y", "energy", "integrity",
                    "fertility", "age", "generation", "genotype", "memory",
                ):
                    self.assertTrue(
                        np.array_equal(
                            getattr(cpu.entities, name), getattr(strict.entities, name)
                        ),
                        name,
                    )
                self.assertTrue(
                    np.array_equal(cpu.environment.resources, strict.environment.resources)
                )
                self.assertTrue(
                    np.array_equal(cpu.information.field, strict.information.field)
                )
                self.assertEqual(cpu.total_births, strict.total_births)
                self.assertEqual(cpu.total_deaths, strict.total_deaths)
                branch = strict.clone(Path(tmp) / "strict-branch")
                try:
                    self.assertEqual(branch.execution_backend, "gpu-strict-reference")
                    self.assertEqual(branch.requested_backend, "gpu")
                    self.assertTrue(np.array_equal(branch.entities.alive, strict.entities.alive))
                finally:
                    self._close(branch)
            finally:
                self._close(cpu)
                self._close(strict)

    def test_hybrid_mode_is_explicit_not_default(self) -> None:
        cfg = self._cfg()
        self.assertEqual(cfg.run.gpu_semantics_mode, "strict-reference")
        hybrid = replace(
            cfg, run=replace(cfg.run, gpu_semantics_mode="hybrid-accelerated")
        )
        self.assertEqual(hybrid.run.gpu_semantics_mode, "hybrid-accelerated")

    def test_unproven_hybrid_is_not_scientific_baseline(self) -> None:
        cfg = self._cfg()
        with tempfile.TemporaryDirectory() as tmp:
            simulation = Simulation(cfg, Path(tmp) / "simulation", backend="cpu")
            try:
                simulation.gpu_semantics_mode = "hybrid-accelerated"
                simulation.gpu_acceleration_enabled = True
                validity = simulation.scientific_validity()
                self.assertFalse(validity["structural_evolution_provenance_valid"])
                self.assertTrue(
                    any("GPU multi-tick parity" in value for value in validity["violations"])
                )
            finally:
                self._close(simulation)


    def test_social_parity_snapshot_uses_real_socialsystem_arrays(self) -> None:
        cfg = self._cfg()
        with tempfile.TemporaryDirectory() as tmp:
            cpu = Simulation(cfg, Path(tmp) / "cpu", backend="cpu")
            candidate = Simulation(cfg, Path(tmp) / "candidate", backend="cpu")
            try:
                expected = {
                    "target",
                    "trust",
                    "familiarity",
                    "last_interaction",
                    "last_decay_tick",
                    "group_id",
                    "group_age",
                    "group_dir_x",
                    "group_dir_y",
                }
                snapshot = _array_state_snapshot(cpu.social)
                self.assertTrue(expected.issubset(snapshot))
                self.assertNotIn("relation_target", snapshot)
                self.assertNotIn("relation_targets", snapshot)
                stages = dict(
                    (name, (reference, got))
                    for name, reference, got in _simulation_stages(cpu, candidate)
                )
                self.assertIn("social-state", stages)
                self.assertEqual(set(stages["social-state"][0]), set(stages["social-state"][1]))
            finally:
                self._close(cpu)
                self._close(candidate)

    def test_discrete_comparison_is_exact(self) -> None:
        report = compare_array(
            "actions",
            np.asarray([1, 2, 3], dtype=np.int16),
            np.asarray([1, 2, 4], dtype=np.int16),
        )
        self.assertFalse(report["passed"])
        self.assertTrue(report["exact_required"])
        self.assertEqual(report["first_mismatch_index"], [2])


if __name__ == "__main__":
    unittest.main()
