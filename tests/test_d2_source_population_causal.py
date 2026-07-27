from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import numpy as np

from se.analysis.d2_source_population_causal_effects import (
    ASSESSMENT_SCHEMA,
    assess_source_population_causal_results,
)
from se.cfg import load_config, validate_config
from se.experiments.d2_lineage_pairs import (
    LineagePairCheckpoint,
    LineagePairPlan,
    LineageSelection,
)
from se.experiments.d2_source_population_causal import (
    PLAN_SCHEMA,
    RESULT_SCHEMA,
    SourcePopulationCausalPlan,
    build_source_population_causal_plan,
    execute_source_population_causal_plan,
)
from se.runtime.sim import Simulation

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "configs" / "d2a_contextual_harvest_smoke.json"


def _source_assessment() -> dict:
    panels = []
    for phase in ("peak", "trough"):
        for seed in (1, 2, 3):
            qualified = phase == "peak" and seed in (1, 3)
            panels.append(
                {
                    "panel_name": f"{phase}_seed_{seed}",
                    "phase": phase,
                    "panel_seed": seed,
                    "arms": {
                        "equal-lineage-reconstitution": {
                            "qualified": qualified,
                        },
                        "natural-abundance-control": {"qualified": False},
                    },
                }
            )
    return {
        "schema": "d2-source-population-assessment-v2",
        "exploratory_qualified_phases": ["peak"],
        "exploratory_causal_reaudit_ready": True,
        "panels": panels,
    }


def _final_snapshot(seed: int) -> dict:
    counts = [40 + seed, 30 + seed, 20 + seed, 10 + seed]
    ids = [1001, 1002, 1003, 1004]
    return {
        "offset_ticks": 600,
        "alive": sum(counts),
        "effective_lineages": 3.5,
        "dominant_lineage_fraction": counts[0] / sum(counts),
        "panel_lineage_counts": [
            {"panel_lineage_id": lineage_id, "members": members}
            for lineage_id, members in zip(ids, counts, strict=True)
        ],
        "candidate_module_expression": {
            "module_3": {
                "lineages": [
                    {
                        "panel_lineage_id": lineage_id,
                        "members": members,
                        "mean_expression": 0.2,
                        "expressed_fraction": 1.0,
                    }
                    for lineage_id, members in zip(ids, counts, strict=True)
                ]
            }
        },
    }


def _source_results() -> dict:
    panels = []
    for phase in ("peak", "trough"):
        for seed in (1, 2, 3):
            final = _final_snapshot(seed)
            panels.append(
                {
                    "panel_name": f"{phase}_seed_{seed}",
                    "phase": phase,
                    "panel_seed": seed,
                    "arms": {
                        "equal-lineage-reconstitution": {
                            "final_checkpoint": f"/tmp/{phase}_{seed}_600.sechk",
                            "trajectory": [final],
                        },
                        "natural-abundance-control": {
                            "final_checkpoint": f"/tmp/{phase}_{seed}_natural_600.sechk",
                            "trajectory": [final],
                        },
                    },
                }
            )
    return {
        "schema": "d2-source-population-results-v1",
        "plan": {
            "burn_in_ticks": 600,
            "candidate_module_indices": [3],
            "min_lineage_members": 8,
        },
        "panels": panels,
    }


def test_plan_uses_only_qualified_phase_and_preserves_all_eligible_lineages() -> None:
    plan = build_source_population_causal_plan(
        _source_assessment(),
        _source_results(),
        horizon_ticks=120,
        min_lineages_per_checkpoint=4,
        max_lineages_per_checkpoint=6,
    )
    assert plan.schema == PLAN_SCHEMA
    assert plan.stage == "120-tick-exploratory-screen"
    assert plan.selected_phases == ("peak",)
    assert plan.selected_panel_seeds == (1, 3)
    assert plan.response_conditioned_panel_selection is False
    assert plan.response_conditioned_lineage_selection is False
    assert plan.general_source_population_claim is False
    assert plan.module_copy_number_changed is False
    assert len(plan.lineage_pair_plan.checkpoints) == 2
    assert all(
        len(checkpoint.lineages) == 4
        for checkpoint in plan.lineage_pair_plan.checkpoints
    )
    assert all(
        checkpoint.until_tick == 720
        for checkpoint in plan.lineage_pair_plan.checkpoints
    )


def _checkpoint(tmp_path: Path, name: str, seed: int) -> tuple[Path, tuple[LineageSelection, ...]]:
    cfg = load_config(CONFIG)
    cfg = replace(
        cfg,
        run=replace(
            cfg.run,
            seed=seed,
            ticks=1,
            metrics_period=1,
            checkpoint_period=99,
            checkpoint_ticks=(),
            full_checkpoint_enabled=False,
            evolution_evaluation_period=1,
        ),
        world=replace(cfg.world, initial_entities=16, max_entities=32),
    )
    validate_config(cfg)
    simulation = Simulation(cfg, tmp_path / name, backend="cpu")
    active = np.flatnonzero(simulation.entities.alive).astype(np.int32)
    selections = []
    for rank, chunk in enumerate(np.array_split(active, 4), start=1):
        lineage_id = seed * 100 + rank
        simulation.entities.lineage_id[chunk] = np.uint64(lineage_id)
        selections.append(
            LineageSelection(
                lineage_id=lineage_id,
                members=int(chunk.size),
                member_fraction=float(chunk.size) / float(active.size),
                abundance_rank=rank,
            )
        )
    path = simulation.save_full_checkpoint(tmp_path / name / "checkpoint_00000000.sechk")
    return path, tuple(selections)


def test_execution_and_assessment_keep_copy_number_blocked(tmp_path: Path) -> None:
    checkpoints = []
    for seed in (11, 12):
        path, lineages = _checkpoint(tmp_path, f"seed_{seed}", seed)
        checkpoints.append(
            LineagePairCheckpoint(
                run_name=f"peak_seed_{seed}",
                phase="peak",
                checkpoint_tick=0,
                checkpoint_path=str(path),
                until_tick=1,
                active_entities=16,
                effective_lineages=4.0,
                dominant_lineage_fraction=0.25,
                eligible=True,
                ineligible_reason=None,
                lineages=lineages,
            )
        )
    lineage_plan = LineagePairPlan(
        schema="d2-lineage-paired-plan-v2",
        horizon_ticks=1,
        module_indices=(3,),
        min_lineage_members=4,
        min_lineages_per_checkpoint=4,
        max_lineages_per_checkpoint=4,
        checkpoints=tuple(checkpoints),
    )
    plan = SourcePopulationCausalPlan(
        schema=PLAN_SCHEMA,
        stage="smoke",
        source_assessment_schema="d2-source-population-assessment-v2",
        source_assessment_sha256=None,
        source_result_schema="d2-source-population-results-v1",
        source_result_sha256=None,
        evidence_scope="phase-specific-exploratory-causal-reaudit",
        selected_phases=("peak",),
        selected_panel_seeds=(11, 12),
        horizon_ticks=1,
        module_indices=(3,),
        min_lineage_members=4,
        min_lineages_per_checkpoint=4,
        max_lineages_per_checkpoint=4,
        lineage_pair_plan=lineage_plan,
    )
    result = execute_source_population_causal_plan(
        plan,
        tmp_path / "audit",
        backend="cpu",
    )
    assert result["schema"] == RESULT_SCHEMA
    assert result["executed_checkpoint_count"] == 2
    assert result["executed_pair_count"] == 8
    assert result["module_copy_number_ready"] is False

    assessment = assess_source_population_causal_results(result)
    assert assessment["schema"] == ASSESSMENT_SCHEMA
    assert assessment["general_source_population_claim"] is False
    assert assessment["module_copy_number_ready"] is False
