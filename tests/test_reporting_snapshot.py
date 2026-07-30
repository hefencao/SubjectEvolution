from __future__ import annotations

from dataclasses import replace
import json
from pathlib import Path

import numpy as np

from se.cfg import load_config
from se.runtime.sim import Simulation


ROOT = Path(__file__).resolve().parents[1]


def _cfg(*, ticks: int = 1):
    base = load_config(
        ROOT / "configs" / "mvp_short_d3g_spatial_processing_scale1p5_longrun.json"
    )
    return replace(
        base,
        run=replace(
            base.run,
            ticks=ticks,
            metrics_period=1,
            checkpoint_period=99,
            evolution_evaluation_period=99,
            validation_mode=False,
            full_checkpoint_enabled=False,
            subject_structure_diagnostics_enabled=False,
            subject_structure_diagnostics_schema="disabled",
            environment_atlas_diagnostics_enabled=False,
            environment_atlas_diagnostics_schema="disabled",
            environment_atlas_scales=(),
            spatial_stress_diagnostics_enabled=False,
            spatial_stress_diagnostics_schema="disabled",
        ),
        world=replace(
            base.world,
            width=32.0,
            height=32.0,
            grid_x=8,
            grid_y=8,
            initial_entities=24,
            max_entities=32,
        ),
    )


def test_final_summary_uses_materialized_reporting_boundary(tmp_path: Path) -> None:
    simulation = Simulation(_cfg(), tmp_path / "run", backend="cpu")
    cells = simulation.cfg.world.grid_x * simulation.cfg.world.grid_y

    def materialize_current_tick() -> None:
        # Model the deferred GPU host mirror becoming current exactly at the
        # report boundary.  The summary must be built after this callback.
        simulation.environment.resource_residue.fill(np.float32(simulation.tick))
        simulation.reporting_state_tick = simulation.tick
        simulation.reporting_state_source = "test-device-materialized"

    simulation.materialize_reporting_state = materialize_current_tick  # type: ignore[method-assign]
    result = simulation.run()
    summary = json.loads((tmp_path / "run" / "summary.json").read_text())

    assert int(result["tick"]) == 1
    assert summary["reporting_snapshot_schema"] == "authoritative-reporting-snapshot-v1"
    assert summary["reporting_state_tick"] == summary["tick"] == 1
    assert summary["reporting_state_source"] == "test-device-materialized"
    assert summary["resource_residue_total"] == [float(cells)] * 4


def test_run_plan_is_written_before_normal_run_outputs(tmp_path: Path) -> None:
    output = tmp_path / "planned"
    simulation = Simulation(_cfg(ticks=2), output, backend="cpu")
    simulation.run()

    plan = json.loads((output / "run_plan.json").read_text())
    summary = json.loads((output / "summary.json").read_text())
    metadata = json.loads((output / "run_metadata.json").read_text())

    assert plan["schema"] == "simulation-run-plan-v1"
    assert plan["version"] == "0.70.0"
    assert plan["start_tick"] == 0
    assert plan["target_tick"] == 2
    assert plan["reporting"]["summary_schema"] == "authoritative-reporting-snapshot-v1"
    assert plan["reporting"]["device_state_materialized_at_every_report"] is True
    assert plan["gpu_memory_pool"]["policy"] == "bounded-cache-v1"
    assert plan["gpu_memory_pool"]["cache_limit_bytes"] == 536870912
    assert plan["gpu_memory_pool"]["trim_period"] == 1
    assert plan["gpu_memory_pool"]["live_allocations_unmodified"] is True
    assert plan["checkpoints"]["period"] == 99
    assert plan["outcome_conditioned_schedule_changes"] is False
    assert summary["reporting_state_tick"] == 2
    assert metadata["final"]["reporting_state_tick"] == 2


def test_reporting_and_checkpoint_share_one_materialization_per_tick(tmp_path: Path) -> None:
    simulation = Simulation(_cfg(), tmp_path / "deduplicated", backend="cpu")

    class FakeGpuRuntime:
        def __init__(self) -> None:
            self.calls = 0

        def sync_to_host(self, environment, information) -> None:
            self.calls += 1

    runtime = FakeGpuRuntime()
    try:
        simulation.gpu_runtime = runtime  # type: ignore[assignment]
        simulation.tick = 7
        simulation.host_semantic_state_tick = -1
        simulation.materialize_reporting_state()
        simulation.sync_host_semantic_state()
        assert runtime.calls == 1
        assert simulation.reporting_state_tick == 7
        assert simulation.host_semantic_state_tick == 7
    finally:
        simulation.gpu_runtime = None
        simulation.metrics.close()
        simulation.evolution_progress.close()
        simulation.knowledge.close()
