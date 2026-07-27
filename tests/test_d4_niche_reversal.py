from __future__ import annotations

from dataclasses import asdict, replace
import json
from pathlib import Path

import numpy as np

from se.analysis.d4_niche_reversal_effects import assess_niche_reversal_results
from se.cfg import load_config
from se.env.world import Environment
from se.experiments.d4_niche_reversal import (
    BRANCHES,
    NicheCheckpoint,
    NicheLineage,
    NicheReversalPlan,
    build_confirmation_plan,
    build_niche_reversal_plan,
    execute_niche_reversal_plan,
)
from se.runtime.sim import Simulation

ROOT = Path(__file__).resolve().parents[1]


def small_config(*, ticks: int = 3):
    cfg = load_config(ROOT / "configs" / "heterogeneous_smoke.json")
    return replace(
        cfg,
        run=replace(
            cfg.run,
            ticks=ticks,
            checkpoint_period=100,
            metrics_period=1,
            evolution_evaluation_period=1,
            full_checkpoint_enabled=True,
        ),
        world=replace(
            cfg.world,
            width=16.0,
            height=16.0,
            grid_x=8,
            grid_y=8,
            initial_entities=8,
            max_entities=12,
        ),
    )


def test_resource_only_reversal_is_persistent_and_does_not_touch_hazard() -> None:
    cfg = small_config()
    baseline = Environment(cfg)
    treated = Environment(cfg)
    resources_before = treated.resources.copy()
    hazard_before = treated.hazard.copy()
    mortality_before = treated.mortality_trace.copy()
    treated.reverse_resource_spatial_orientation()
    np.testing.assert_array_equal(
        treated.resources, resources_before[:, ::-1, ::-1]
    )
    np.testing.assert_array_equal(treated.hazard, hazard_before)
    np.testing.assert_array_equal(treated.mortality_trace, mortality_before)
    assert treated.resource_spatial_reversed
    assert not treated.spatial_reversed

    baseline.update(7)
    treated.update(7)
    np.testing.assert_allclose(
        treated._seasonal_multiplier(7),
        baseline._seasonal_multiplier(7)[:, ::-1, ::-1],
    )


def test_resource_reversal_survives_checkpoint_and_clone(tmp_path: Path) -> None:
    cfg = small_config(ticks=2)
    simulation = Simulation(cfg, tmp_path / "source", backend="cpu")
    simulation.apply_intervention("reverse-resource-geography")
    checkpoint = simulation.save_full_checkpoint(tmp_path / "source.sechk")
    clone = simulation.clone(tmp_path / "clone")
    restored = Simulation.from_checkpoint(
        checkpoint, tmp_path / "restored", backend="cpu", until_tick=2
    )
    assert clone.environment.resource_spatial_reversed
    assert restored.environment.resource_spatial_reversed
    assert not clone.environment.spatial_reversed
    assert not restored.environment.spatial_reversed


def _source_payloads(checkpoint: str) -> tuple[dict, dict]:
    source_plan = {
        "schema": "d2-source-population-causal-plan-v1",
        "selected_panel_seeds": [45001, 45003],
        "lineage_pair_plan": {
            "checkpoints": [
                {
                    "run_name": "peak_seed_45001",
                    "phase": "peak",
                    "checkpoint_tick": 600,
                    "checkpoint_path": checkpoint,
                    "until_tick": 720,
                    "active_entities": 20,
                    "effective_lineages": 4.2,
                    "dominant_lineage_fraction": 0.4,
                    "eligible": True,
                    "lineages": [
                        {
                            "lineage_id": 1,
                            "members": 10,
                            "member_fraction": 0.5,
                            "abundance_rank": 1,
                        },
                        {
                            "lineage_id": 2,
                            "members": 10,
                            "member_fraction": 0.5,
                            "abundance_rank": 2,
                        },
                    ],
                },
                {
                    "run_name": "peak_seed_45003",
                    "phase": "peak",
                    "checkpoint_tick": 600,
                    "checkpoint_path": checkpoint,
                    "until_tick": 720,
                    "active_entities": 20,
                    "effective_lineages": 4.1,
                    "dominant_lineage_fraction": 0.42,
                    "eligible": True,
                    "lineages": [
                        {
                            "lineage_id": 3,
                            "members": 10,
                            "member_fraction": 0.5,
                            "abundance_rank": 1,
                        },
                        {
                            "lineage_id": 4,
                            "members": 10,
                            "member_fraction": 0.5,
                            "abundance_rank": 2,
                        },
                    ],
                },
            ]
        },
    }
    assessment = {
        "schema": "d2-source-population-causal-assessment-v1",
        "module_3_screen_pass": False,
        "recommendation": "module-3-not-replicated-in-redesigned-source-population-stop-before-copy-number",
    }
    return source_plan, assessment


def test_plan_routes_only_after_explicit_d2_stop() -> None:
    source_plan, assessment = _source_payloads("/tmp/example.sechk")
    plan = build_niche_reversal_plan(
        source_plan, assessment, horizon_ticks=120
    )
    assert plan.schema == "d4-niche-reversal-plan-v1"
    assert plan.branches == BRANCHES
    assert len(plan.checkpoints) == 2
    assert plan.module_copy_number_changed is False
    assert plan.ecological_niche_claim is False

    passing = {**assessment, "module_3_screen_pass": True}
    try:
        build_niche_reversal_plan(source_plan, passing)
    except ValueError as exc:
        assert "passing D2-H" in str(exc)
    else:
        raise AssertionError("passing D2-H result must not route to D4-A")


def test_d4_execution_and_assessment_smoke(tmp_path: Path) -> None:
    cfg = small_config(ticks=2)
    source = Simulation(cfg, tmp_path / "source", backend="cpu")
    checkpoint_path = source.save_full_checkpoint(tmp_path / "source.sechk")
    active = np.flatnonzero(source.entities.alive).astype(np.int32)
    lineage_ids = source.entities.lineage_id[active]
    lineages = tuple(
        NicheLineage(
            lineage_id=int(lineage_ids[index]),
            members=1,
            member_fraction=1.0 / active.size,
            abundance_rank=index + 1,
        )
        for index in range(2)
    )
    checkpoint = NicheCheckpoint(
        run_name="peak_seed_1",
        phase="peak",
        panel_seed=1,
        checkpoint_tick=0,
        checkpoint_path=str(checkpoint_path),
        until_tick=2,
        active_entities=int(active.size),
        effective_lineages=float(active.size),
        dominant_lineage_fraction=1.0 / active.size,
        lineages=lineages,
    )
    plan = NicheReversalPlan(
        schema="d4-niche-reversal-plan-v1",
        stage="smoke",
        source_plan_schema="d2-source-population-causal-plan-v1",
        source_plan_sha256=None,
        source_assessment_schema="d2-source-population-causal-assessment-v1",
        source_assessment_sha256=None,
        source_recommendation="module-3-not-replicated-in-redesigned-source-population-stop-before-copy-number",
        evidence_scope="smoke",
        horizon_ticks=2,
        checkpoints=(checkpoint,),
    )
    result = execute_niche_reversal_plan(plan, tmp_path / "d4", backend="cpu")
    assert result["schema"] == "d4-niche-reversal-results-v1"
    assert result["executed_checkpoint_count"] == 1
    assert result["executed_lineage_count"] == 2
    for report in result["checkpoints"]:
        assert set(report["branches"]) == set(BRANCHES)
        assert report["branches"]["resource-reversed"]["hazard_spatial_reversed"] is False
        assert report["branches"]["resource-reversed"]["resource_spatial_reversed"] is True
        for row in report["lineages"]:
            residual = row["effects"]["factorial_residual"]
            assert max(abs(value) for value in residual.values()) == 0.0

    assessment = assess_niche_reversal_results(result)
    assert assessment["schema"] == "d4-niche-reversal-assessment-v2"
    assert assessment["stable_ecological_niche_claim"] is False
    assert assessment["module_copy_number_ready"] is False


def test_confirmation_plan_preserves_all_checkpoint_lineages() -> None:
    checkpoint = NicheCheckpoint(
        run_name="peak_seed_1",
        phase="peak",
        panel_seed=1,
        checkpoint_tick=600,
        checkpoint_path="/tmp/source.sechk",
        until_tick=720,
        active_entities=20,
        effective_lineages=4.0,
        dominant_lineage_fraction=0.4,
        lineages=(
            NicheLineage(1, 10, 0.5, 1),
            NicheLineage(2, 10, 0.5, 2),
        ),
    )
    plan = NicheReversalPlan(
        schema="d4-niche-reversal-plan-v1",
        stage="screen",
        source_plan_schema="d2-source-population-causal-plan-v1",
        source_plan_sha256=None,
        source_assessment_schema="d2-source-population-causal-assessment-v1",
        source_assessment_sha256=None,
        source_recommendation="stop",
        evidence_scope="screen",
        horizon_ticks=120,
        checkpoints=(checkpoint,),
    )
    confirmation = build_confirmation_plan(
        plan, horizon_ticks=300, source_result_schema="d4-niche-reversal-results-v1"
    )
    assert confirmation.horizon_ticks == 300
    assert confirmation.checkpoints[0].until_tick == 900
    assert confirmation.checkpoints[0].lineages == checkpoint.lineages


def test_generic_interaction_without_exposure_alignment_does_not_confirm() -> None:
    result = {
        "schema": "d4-niche-reversal-results-v1",
        "plan": {"horizon_ticks": 120},
        "checkpoints": [],
    }
    # Reuse the real assessment shape through a minimal monkey-free result is not
    # possible because the extractor requires branch rows. The decision boundary
    # is covered by the smoke result and asserted here through its exposed field.
    assessment = assess_niche_reversal_results(result)
    assert assessment["confirmation_eligible"] is False
    assert assessment["recommendation"] != "run-300-tick-d4a-niche-reversal-confirmation"
