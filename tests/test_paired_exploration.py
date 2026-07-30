from __future__ import annotations

from dataclasses import replace
import json
from pathlib import Path

import pytest

from se.cfg import load_config
from se.experiments.paired_exploration import (
    ASSESSMENT_SCHEMA,
    PLAN_SCHEMA,
    assess_results,
    build_plan,
    execute_plan,
)
from se.runtime.sim import Simulation


def _source_root(tmp_path: Path, *, seeds: list[int], stage: str = "smoke") -> Path:
    root = tmp_path / "source"
    root.mkdir()
    cfg0 = load_config("configs/mvp_d3n_exploration_screen.json")
    rows = []
    for seed in seeds:
        cfg = replace(
            cfg0,
            run=replace(
                cfg0.run,
                seed=seed,
                ticks=1,
                metrics_period=1,
                checkpoint_period=1,
                evolution_evaluation_period=1,
                full_checkpoint_enabled=True,
                validation_mode=True,
            ),
            world=replace(
                cfg0.world,
                width=32.0,
                height=32.0,
                grid_x=8,
                grid_y=8,
                initial_entities=64,
                max_entities=96,
            ),
        )
        seed_dir = root / f"seed_{seed}"
        simulation = Simulation(cfg, seed_dir, backend="cpu")
        simulation.step()
        simulation.save_full_checkpoint(seed_dir / "checkpoint_00000001.sechk")
        simulation.knowledge.close()
        simulation.evolution_progress.close()
        simulation.metrics.close()
        rows.append(
            {
                "seed": seed,
                "output": str(seed_dir),
                "final_tick": 1,
                "alive": int(simulation.entities.alive.sum()),
                "status": "completed",
            }
        )
    (root / "multi_seed_index.json").write_text(json.dumps(rows), encoding="utf-8")
    (root / "exploration_plan.json").write_text(
        json.dumps({"schema": "tiered-exploration-plan-v1", "stage": stage}),
        encoding="utf-8",
    )
    return root


def test_build_plan_uses_exact_per_seed_checkpoints(tmp_path: Path) -> None:
    root = _source_root(tmp_path, seeds=[1, 2])
    plan = build_plan(
        stage="smoke",
        candidate_id="affinity-calibration",
        source_root=root,
        checkpoint_tick=1,
        response_ticks=2,
        intervention="neutralize-resource-affinity",
        primary_metric="harvested-resource-total",
        metric_mode="cumulative",
        direction="two-sided",
        minimum_relative_effect=0.0,
        output=tmp_path / "paired",
        backend="cpu",
    )
    assert plan["schema"] == PLAN_SCHEMA
    assert plan["seeds"] == [1, 2]
    assert all(Path(item["checkpoint_path"]).is_file() for item in plan["panels"])
    assert all(item["checkpoint_tick"] == 1 for item in plan["panels"])
    assert plan["fixed_checkpoint_selected_before_branch_outcomes"] is True
    assert plan["selection_claim_allowed"] is False


def test_build_plan_rejects_missing_predeclared_checkpoint(tmp_path: Path) -> None:
    root = _source_root(tmp_path, seeds=[1, 2])
    with pytest.raises(Exception, match="checkpoint"):
        build_plan(
            stage="smoke",
            candidate_id="missing",
            source_root=root,
            checkpoint_tick=2,
            response_ticks=1,
            intervention="neutralize-resource-affinity",
            primary_metric="harvested-resource-total",
            metric_mode="cumulative",
            direction="two-sided",
            minimum_relative_effect=0.0,
            output=tmp_path / "paired",
            backend="cpu",
        )


def test_assessment_promotes_only_seed_level_consistent_effects() -> None:
    plan = {
        "stage": "screen",
        "candidate_id": "candidate-a",
        "intervention": "neutralize-resource-affinity",
        "primary_metric": "harvested-resource-total",
        "metric_mode": "cumulative",
        "direction": "increase",
        "minimum_relative_effect": 0.01,
        "minimum_eligible_seed_fraction": 0.75,
        "minimum_direction_consistency": 0.75,
        "seeds": list(range(8)),
        "all_stage_seeds": list(range(8)),
    }
    panels = [
        {"eligible": True, "relative_effect": 0.02 + index * 0.001}
        for index in range(8)
    ]
    assessment = assess_results(plan, panels)
    assert assessment["schema"] == ASSESSMENT_SCHEMA
    assert assessment["promotion_gate_passed"] is True
    assert assessment["recommendation"] == "promote-to-disjoint-replication"
    mixed = [
        {"eligible": True, "relative_effect": 0.03 if index % 2 else -0.03}
        for index in range(8)
    ]
    stopped = assess_results(plan, mixed)
    assert stopped["promotion_gate_passed"] is False
    assert stopped["recommendation"] == "stop-direction-not-replicated-across-seeds"


def test_execute_smoke_panel_writes_matched_results(tmp_path: Path) -> None:
    root = _source_root(tmp_path, seeds=[11, 12])
    plan = build_plan(
        stage="smoke",
        candidate_id="affinity-calibration",
        source_root=root,
        checkpoint_tick=1,
        response_ticks=2,
        intervention="neutralize-resource-affinity",
        primary_metric="resource_affinity_specialization_mean",
        metric_mode="endpoint",
        direction="decrease",
        minimum_relative_effect=0.0,
        output=tmp_path / "paired",
        backend="cpu",
    )
    report = execute_plan(plan)
    assert report["schema"] == "tiered-paired-exploration-results-v1"
    assert len(report["panels"]) == 2
    assert all((tmp_path / "paired" / f"seed_{seed}" / "counterfactual_summary.json").is_file() for seed in (11, 12))
    assert (tmp_path / "paired" / "paired_exploration_assessment.json").is_file()
