from __future__ import annotations

from dataclasses import asdict
import json
from pathlib import Path

from se.analysis.d2_lineage_effects import (
    ASSESSMENT_SCHEMA,
    CONFIRMATION_SELECTION_RULE,
    assess_lineage_pair_results,
    build_confirmation_plan,
)
from se.experiments.d2_lineage_pairs import PLAN_SCHEMA, RESULT_SCHEMA


def _row(
    *,
    run_name: str,
    phase: str,
    tick: int,
    module: int,
    lineage: int,
    rank: int,
    root_effect: float = 0.0,
    alive_effect: float = 0.0,
    energy_effect: float = 0.0,
) -> dict:
    baseline = {
        "world.alive": 500.0,
        "world.mean_energy": 1.4,
        "target_lineage.alive": 20.0,
        "target_lineage.mean_energy": 1.3,
        "evolution.environment_resource_effective_dimensions": 2.0,
        "derived.harvest_extraction_efficiency_window": 0.4,
        "evolution.knowledge_effective_transferred_roots": 250.0,
        "evolution.effective_lineages": 2.0,
        "evolution.functional_harvest_preference_effective_dimensions": 1.2,
    }
    effect = {key: 0.0 for key in baseline}
    effect["evolution.knowledge_effective_transferred_roots"] = root_effect
    effect["target_lineage.alive"] = alive_effect
    effect["target_lineage.mean_energy"] = energy_effect
    zero = {key: 0.0 for key in baseline}
    return {
        "pair": {
            "run_name": run_name,
            "phase": phase,
            "checkpoint_tick": tick,
            "lineage_id": lineage,
            "source_members": 20,
            "source_member_fraction": 0.04,
            "source_abundance_rank": rank,
        },
        "module_index": module,
        "branches": {
            "baseline": {"outcomes": baseline},
            "output-neutral": {"outcomes": baseline},
            "expression-neutral": {"outcomes": baseline},
        },
        "effects": {
            "output_routing_effect": effect,
            "retained_expression_cost_effect": zero,
            "total_expression_effect": effect,
            "decomposition_residual": zero,
        },
    }


def _result() -> dict:
    checkpoints = []
    specs = [
        ("seed_a", "peak", 100, 101, 102),
        ("seed_b", "trough", 200, 201, 202),
        ("seed_c", "peak", 300, 301, 302),
    ]
    plan_checkpoints = []
    for run_name, phase, tick, dominant, non_dominant in specs:
        pairs = [
            _row(
                run_name=run_name,
                phase=phase,
                tick=tick,
                module=2,
                lineage=dominant,
                rank=1,
            ),
            _row(
                run_name=run_name,
                phase=phase,
                tick=tick,
                module=2,
                lineage=non_dominant,
                rank=2,
                root_effect=-3.0 if run_name != "seed_c" else 0.0,
            ),
            _row(
                run_name=run_name,
                phase=phase,
                tick=tick,
                module=3,
                lineage=dominant,
                rank=1,
            ),
            _row(
                run_name=run_name,
                phase=phase,
                tick=tick,
                module=3,
                lineage=non_dominant,
                rank=2,
                alive_effect=-1.0 if run_name != "seed_c" else 0.0,
                energy_effect=0.02,
            ),
        ]
        checkpoints.append(
            {
                "checkpoint": {
                    "run_name": run_name,
                    "phase": phase,
                    "checkpoint_tick": tick,
                },
                "status": "executed",
                "pairs": pairs,
            }
        )
        plan_checkpoints.append(
            {
                "run_name": run_name,
                "phase": phase,
                "checkpoint_tick": tick,
                "checkpoint_path": f"/tmp/{run_name}_{tick}.sechk",
                "until_tick": tick + 120,
                "active_entities": 500,
                "effective_lineages": 2.0,
                "dominant_lineage_fraction": 0.7,
                "eligible": True,
                "ineligible_reason": None,
                "lineages": [
                    {
                        "lineage_id": dominant,
                        "members": 350,
                        "member_fraction": 0.7,
                        "abundance_rank": 1,
                    },
                    {
                        "lineage_id": non_dominant,
                        "members": 20,
                        "member_fraction": 0.04,
                        "abundance_rank": 2,
                    },
                ],
            }
        )
    return {
        "schema": RESULT_SCHEMA,
        "plan": {
            "schema": PLAN_SCHEMA,
            "horizon_ticks": 120,
            "module_indices": [2, 3],
            "min_lineage_members": 8,
            "min_lineages_per_checkpoint": 2,
            "max_lineages_per_checkpoint": 2,
            "checkpoints": plan_checkpoints,
            "lineage_selection_rule": "largest-preintervention-lineages-by-membership-v1",
            "paired_randomness": True,
            "genotype_preserved": True,
            "lineage_membership_preserved": True,
            "abundance_weighted_inference": False,
            "branches": ["baseline", "output-neutral", "expression-neutral"],
            "effect_decomposition_schema": "output-cost-total-additive-v1",
        },
        "checkpoints": checkpoints,
    }


def test_lineage_assessment_requires_repeated_non_dominant_output() -> None:
    result = _result()
    report = assess_lineage_pair_results(result)
    assert report["schema"] == ASSESSMENT_SCHEMA
    assert report["long_horizon_candidate_modules"] == [2, 3]
    assert report["duplication_ready_modules"] == []
    assert report["lineage_guard"]["dominant_lineage_risk"] is True

    module_2 = report["modules"]["module_2"]
    assert module_2["repeated_output_outcomes"] == [
        "evolution.knowledge_effective_transferred_roots"
    ]
    roots = module_2["effects"]["output_routing_effect"][
        "evolution.knowledge_effective_transferred_roots"
    ]
    assert roots["replicated_sign"] == -1
    assert roots["replicated_seed_count"] == 2

    module_3 = report["modules"]["module_3"]
    assert module_3["repeated_output_outcomes"] == [
        "target_lineage.alive",
        "target_lineage.mean_energy",
    ]
    assert module_3["positive_ecological_output"] is False


def test_confirmation_plan_selects_modules_not_responsive_pairs() -> None:
    result = _result()
    report = assess_lineage_pair_results(result)
    plan = build_confirmation_plan(result, report, horizon_ticks=300)
    assert plan is not None
    assert plan.schema == PLAN_SCHEMA
    assert plan.module_indices == (2, 3)
    assert plan.horizon_ticks == 300
    assert plan.confirmation_source_horizon_ticks == 120
    assert plan.confirmation_selection_rule == CONFIRMATION_SELECTION_RULE
    assert plan.outcome_conditioned_pair_selection is False
    assert [len(item.lineages) for item in plan.checkpoints] == [2, 2, 2]
    assert [item.until_tick for item in plan.checkpoints] == [400, 500, 600]


def test_confirmation_plan_round_trip_payload_is_json_serializable(tmp_path: Path) -> None:
    result = _result()
    report = assess_lineage_pair_results(result)
    plan = build_confirmation_plan(result, report, horizon_ticks=300)
    assert plan is not None
    path = tmp_path / "plan.json"
    path.write_text(json.dumps(asdict(plan)), encoding="utf-8")
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["schema"] == PLAN_SCHEMA
    assert payload["confirmation_source_result_schema"] == RESULT_SCHEMA


def test_long_assessment_requires_same_pair_same_direction_persistence() -> None:
    short = _result()
    long = _result()
    long["plan"]["horizon_ticks"] = 300
    for checkpoint in long["checkpoints"]:
        for row in checkpoint["pairs"]:
            if row["module_index"] == 2:
                value = row["effects"]["output_routing_effect"][
                    "evolution.knowledge_effective_transferred_roots"
                ]
                row["effects"]["output_routing_effect"][
                    "evolution.knowledge_effective_transferred_roots"
                ] = -4.0 if value < 0 else 0.0
            if row["module_index"] == 3:
                energy = row["effects"]["output_routing_effect"][
                    "target_lineage.mean_energy"
                ]
                row["effects"]["output_routing_effect"][
                    "target_lineage.mean_energy"
                ] = 0.03 if energy > 0 else 0.0
                alive = row["effects"]["output_routing_effect"][
                    "target_lineage.alive"
                ]
                row["effects"]["output_routing_effect"][
                    "target_lineage.alive"
                ] = 1.0 if alive < 0 else 0.0
    report = assess_lineage_pair_results(long, short_results=short)
    assert report["confirmed_modules"] == [2, 3]
    assert report["modules"]["module_2"]["persistent_output_outcomes"] == [
        "evolution.knowledge_effective_transferred_roots"
    ]
    assert report["modules"]["module_3"]["persistent_output_outcomes"] == [
        "target_lineage.mean_energy"
    ]
    assert "target_lineage.alive" not in report["modules"]["module_3"][
        "persistent_output_outcomes"
    ]
