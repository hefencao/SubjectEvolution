from __future__ import annotations

from dataclasses import replace
import json
from pathlib import Path

import numpy as np

from se.cfg import load_config
from se.env.niches import AFFINITY_SCALE, apply_harvest_effects, policy_resource_view
from se.experiments.phase_counterfactual import (
    build_phase_plan,
    detect_phase_targets,
    execute_phase_plan,
)
from se.runtime.sim import Simulation


ROOT = Path(__file__).resolve().parents[1]


def small_heterogeneous_config(*, ticks: int = 12):
    cfg = load_config(ROOT / "configs" / "heterogeneous_smoke.json")
    return replace(
        cfg,
        run=replace(
            cfg.run,
            ticks=ticks,
            checkpoint_period=3,
            evolution_evaluation_period=3,
            metrics_period=3,
            full_checkpoint_enabled=True,
            long_run_diagnostics_enabled=True,
            long_run_diagnostics_schema="long-run-evolution-diagnostics-v1",
        ),
        world=replace(
            cfg.world,
            width=32.0,
            height=32.0,
            grid_x=8,
            grid_y=8,
            initial_entities=16,
            max_entities=24,
        ),
    )


def test_affinity_override_is_uniform_without_modifying_genotype() -> None:
    cfg = small_heterogeneous_config(ticks=1)
    genotype = np.zeros((2, 16), dtype=np.float32)
    genotype[0, 1] = 1.0
    genotype[0, 2] = -1.0
    genotype[1, 4] = 1.0
    genotype_before = genotype.copy()
    local = np.asarray([[8.0, 0.0, 0.0, 0.0], [0.0, 0.0, 0.0, 8.0]], dtype=np.float32)
    uniform = np.full((2, 4), AFFINITY_SCALE, dtype=np.int32)
    view = policy_resource_view(
        local, genotype, cfg, resource_affinity_q=uniform
    )
    assimilated, _ = apply_harvest_effects(
        np.ones((2, 4), dtype=np.float32),
        genotype,
        cfg,
        resource_affinity_q=uniform,
    )
    np.testing.assert_array_equal(genotype, genotype_before)
    np.testing.assert_allclose(assimilated, np.ones((2, 4), dtype=np.float32))
    assert np.isclose(view[0, 0], view[1, 0])


def test_scientific_ablation_flags_survive_checkpoint_and_clone(tmp_path: Path) -> None:
    cfg = small_heterogeneous_config(ticks=6)
    source = Simulation(cfg, tmp_path / "source", backend="cpu")
    source.apply_intervention("neutralize-resource-affinity")
    source.apply_intervention("disable-knowledge-policy")
    source.apply_intervention("disable-knowledge-transfer")
    clone = source.clone(tmp_path / "clone")
    assert clone.resource_affinity_ablation_enabled
    assert clone.knowledge_policy_ablation_enabled
    assert clone.knowledge_transfer_ablation_enabled
    checkpoint = source.save_full_checkpoint(tmp_path / "source.sechk")
    restored = Simulation.from_checkpoint(
        checkpoint, tmp_path / "restored", backend="cpu", until_tick=6
    )
    assert restored.resource_affinity_ablation_enabled
    assert restored.knowledge_policy_ablation_enabled
    assert restored.knowledge_transfer_ablation_enabled


def test_disable_knowledge_policy_publishes_empty_plan(tmp_path: Path) -> None:
    cfg = small_heterogeneous_config(ticks=2)
    simulation = Simulation(cfg, tmp_path / "run", backend="cpu")
    simulation.apply_intervention("disable-knowledge-policy")
    simulation.step()
    assert simulation.last_knowledge_policy_plan.size == 0
    assert simulation.last_knowledge_policy_plan.work_active_rows.size == 0
    row = simulation.metric_row(simulation.step(), 0.0, window_seconds=0.0, window_ticks=1)
    assert row["knowledge_policy_ablation_enabled"] == 1
    assert row["knowledge_policy_effective_enabled"] == 0


def test_disable_knowledge_transfer_skips_transfer_planning(tmp_path: Path) -> None:
    cfg = small_heterogeneous_config(ticks=1)
    simulation = Simulation(cfg, tmp_path / "run", backend="cpu")
    simulation.apply_intervention("disable-knowledge-transfer")

    def fail(*args, **kwargs):
        raise AssertionError("transfer planning should be bypassed")

    simulation.knowledge.plan_transfers = fail  # type: ignore[method-assign]
    simulation.step()


def test_phase_detection_selects_four_named_states() -> None:
    alive = [100, 140, 180, 150, 100, 80, 120, 170, 190, 150, 90, 130]
    records = []
    for index, value in enumerate(alive, start=1):
        previous = alive[index - 2] if index > 1 else value
        net = value - previous
        records.append(
            {
                "tick": index * 30,
                "alive": value,
                "births_window": max(net, 0) + 5,
                "deaths_window": max(-net, 0) + 5,
            }
        )
    targets = detect_phase_targets(records, min_phase_tick=30)
    assert set(targets) == {"rise", "peak", "decline", "trough"}
    assert targets["rise"] <= targets["peak"] <= targets["decline"] <= targets["trough"]


def test_phase_plan_and_execution_use_trusted_checkpoints(tmp_path: Path) -> None:
    cfg = small_heterogeneous_config(ticks=12)
    run_dir = tmp_path / "source"
    Simulation(cfg, run_dir, backend="cpu").run(until_tick=12)
    plan = build_phase_plan(
        run_dir,
        horizon_ticks=2,
        interventions=("neutralize-resource-affinity",),
        min_phase_tick=3,
        allow_incomplete_cycle=True,
    )
    assert len(plan.phases) == 4
    assert plan.complete_cycle_detected is False
    assert all(Path(item.checkpoint_path).suffix == ".sechk" for item in plan.phases)
    report = execute_phase_plan(plan, tmp_path / "counterfactual", backend="cpu")
    assert report["paired_randomness"] is True
    assert len(report["phase_results"]) == 4
    for phase in report["phase_results"]:
        assert phase["interventions"][0]["intervention"] == "neutralize-resource-affinity"
    saved = json.loads(
        (tmp_path / "counterfactual" / "phase_counterfactual_results.json").read_text()
    )
    assert saved["schema"] == "phase-checkpoint-counterfactual-results-v1"
