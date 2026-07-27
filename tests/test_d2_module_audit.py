from __future__ import annotations

import pytest

from se.experiments.d2_module_audit import BRANCH_INTERVENTIONS, module_audit_effects


def test_module_audit_effects_include_nonadditivity() -> None:
    branches = {
        name: {"world.alive": value}
        for name, value in {
            "baseline": 100.0,
            "all-modules-neutral": 80.0,
            "module-0-neutral": 94.0,
            "module-1-neutral": 97.0,
            "module-2-neutral": 99.0,
            "module-3-neutral": 100.0,
        }.items()
    }
    assert set(branches) == set(BRANCH_INTERVENTIONS)
    effects = module_audit_effects(branches)
    assert effects["all_module_expression_effect"]["world.alive"] == 20.0
    assert effects["module_0_expression_effect"]["world.alive"] == 6.0
    assert effects["module_3_expression_effect"]["world.alive"] == 0.0
    assert effects["module_nonadditivity"]["world.alive"] == pytest.approx(10.0)


def test_execute_audit_v2_embeds_immediate_footprint(tmp_path) -> None:
    from dataclasses import replace
    from pathlib import Path

    from se.cfg import load_config
    from se.experiments.d2_module_audit import (
        ModuleAuditCheckpoint,
        ModuleAuditPlan,
        PLAN_SCHEMA,
        RESULT_SCHEMA,
        execute_module_audit_plan,
    )
    from se.runtime.sim import Simulation

    root = Path(__file__).resolve().parents[1]
    cfg = load_config(root / "configs" / "d2a_contextual_harvest_smoke.json")
    cfg = replace(
        cfg,
        run=replace(
            cfg.run,
            ticks=2,
            full_checkpoint_enabled=True,
            checkpoint_ticks=(1,),
            checkpoint_period=99,
            evolution_evaluation_period=1,
        ),
        world=replace(cfg.world, initial_entities=16, max_entities=24),
    )
    source = tmp_path / "source"
    Simulation(cfg, source, backend="cpu").run(until_tick=1)
    checkpoint = source / "checkpoint_00000001.sechk"
    plan = ModuleAuditPlan(
        schema=PLAN_SCHEMA,
        horizon_ticks=1,
        phases=("peak",),
        checkpoints=(
            ModuleAuditCheckpoint(
                run_name="source",
                run_dir=str(source),
                phase="peak",
                target_tick=1,
                checkpoint_tick=1,
                checkpoint_path=str(checkpoint),
                until_tick=2,
            ),
        ),
        branches=dict(BRANCH_INTERVENTIONS),
    )
    report = execute_module_audit_plan(plan, tmp_path / "audit", backend="cpu")
    assert report["schema"] == RESULT_SCHEMA
    footprint = report["checkpoints"][0]["checkpoint_footprint"]
    assert footprint["schema"] == "d2-module-immediate-footprint-v1"
    assert footprint["active_entities"] > 0
    assert set(footprint["effects"]) == {
        "all_module_expression_effect",
        "module_0_expression_effect",
        "module_1_expression_effect",
        "module_2_expression_effect",
        "module_3_expression_effect",
    }
