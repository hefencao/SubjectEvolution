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
    assert len(plan["candidate_signature_sha256"]) == 64
    assert plan["schema"] == "tiered-paired-exploration-plan-v2"


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
    assert report["schema"] == "tiered-paired-exploration-results-v2"
    assert len(report["panels"]) == 2
    assert all((tmp_path / "paired" / f"seed_{seed}" / "counterfactual_summary.json").is_file() for seed in (11, 12))
    assert (tmp_path / "paired" / "paired_exploration_assessment.json").is_file()
    assert (tmp_path / "paired" / "candidate_decision.json").is_file()
    assert (tmp_path / "exploration_candidate_ledger.json").is_file()
    assert all("intervention_record" in panel for panel in report["panels"])


def test_candidate_spec_adds_operational_manipulation_checks(tmp_path: Path) -> None:
    from se.experiments.paired_exploration import load_candidate_spec

    root = _source_root(tmp_path, seeds=[21, 22])
    spec, spec_sha = load_candidate_spec(
        "protocols/candidates/d3p_elastic_capacity_acute_effect.json"
    )
    plan = build_plan(
        stage="smoke",
        candidate_id=spec["candidate_id"],
        source_root=root,
        checkpoint_tick=1,
        response_ticks=2,
        intervention=spec["intervention"],
        primary_metric=spec["primary_metric"],
        metric_mode=spec["metric_mode"],
        direction=spec["direction"],
        minimum_relative_effect=0.0,
        manipulation_checks=spec["manipulation_checks"],
        candidate_spec_sha256=spec_sha,
        candidate_spec_schema=spec["schema"],
        output=tmp_path / "capacity-paired",
        backend="cpu",
    )
    report = execute_plan(plan)
    assert all(panel["manipulation_supported"] for panel in report["panels"])
    assert report["assessment"]["manipulation_supported_seed_count"] == 2
    assert report["assessment"]["promotion_gate_components"]["manipulation_confirmed"] is True


def test_assessment_stops_when_manipulation_is_not_confirmed() -> None:
    plan = {
        "stage": "screen",
        "candidate_id": "candidate-b",
        "candidate_signature_sha256": "a" * 64,
        "intervention": "neutralize-elastic-capacities",
        "primary_metric": "knowledge-working-memory-active-dimensions-total",
        "metric_mode": "cumulative",
        "direction": "two-sided",
        "minimum_relative_effect": 0.01,
        "response_ticks": 120,
        "manipulation_checks": [{"metric": "capacity_effective_dimensions"}],
        "minimum_eligible_seed_fraction": 0.75,
        "minimum_direction_consistency": 0.75,
        "seeds": list(range(8)),
        "all_stage_seeds": list(range(8)),
    }
    panels = [
        {
            "eligible": False,
            "manipulation_supported": False,
            "relative_effect": 0.2,
        }
        for _ in range(8)
    ]
    assessment = assess_results(plan, panels)
    assert assessment["promotion_gate_passed"] is False
    assert assessment["recommendation"] == "stop-intervention-manipulation-not-confirmed"
    assert "intervention-manipulation-not-confirmed" in assessment["decision"]["reason_codes"]


def test_knowledge_policy_harvest_candidate_has_proximal_engagement_checks() -> None:
    from se.experiments.paired_exploration import load_candidate_spec

    spec, spec_sha = load_candidate_spec(
        "protocols/candidates/d3q_knowledge_policy_harvest_acute_effect.json"
    )
    assert len(spec_sha) == 64
    assert spec["intervention"] == "disable-knowledge-policy"
    assert spec["primary_metric"] == "harvested-resource-total"
    assert spec["minimum_relative_effect"] == 0.02
    checks = spec["manipulation_checks"]
    assert {item["metric"] for item in checks} == {
        "knowledge_policy_effective_enabled",
        "knowledge-policy-changed-actions-total",
    }
    assert any(
        item["branch"] == "baseline"
        and item["metric"] == "knowledge-policy-changed-actions-total"
        and item["operator"] == ">"
        for item in checks
    )
    assert any(
        item["branch"] == "intervention"
        and item["metric"] == "knowledge-policy-changed-actions-total"
        and item["operator"] == "=="
        and item["value"] == 0.0
        for item in checks
    )


def test_candidate_family_metadata_is_propagated_to_plan_and_assessment() -> None:
    plan = {
        "stage": "screen",
        "candidate_id": "family-candidate",
        "candidate_signature_sha256": "b" * 64,
        "candidate_spec_schema": "paired-exploration-candidate-v1",
        "candidate_spec_sha256": "c" * 64,
        "mechanism_family": "functional-regulatory-output",
        "mechanism_family_revision": 1,
        "family_role": "bounded-output-path",
        "terminal_negative_closes_family": False,
        "family_revision_rationale": None,
        "intervention": "neutralize-functional-module-physiology-output",
        "primary_metric": "physiology-oxygen-uptake-total",
        "metric_mode": "cumulative",
        "direction": "two-sided",
        "minimum_relative_effect": 0.02,
        "response_ticks": 120,
        "manipulation_checks": [],
        "minimum_eligible_seed_fraction": 0.75,
        "minimum_direction_consistency": 0.75,
        "seeds": list(range(8)),
        "all_stage_seeds": list(range(8)),
    }
    panels = [
        {"eligible": True, "relative_effect": 0.03}
        for _ in range(8)
    ]
    assessment = assess_results(plan, panels)
    assert assessment["mechanism_family"] == "functional-regulatory-output"
    assert assessment["mechanism_family_revision"] == 1
    assert assessment["family_role"] == "bounded-output-path"


def test_functional_regulatory_oxygen_candidate_has_direct_output_checks() -> None:
    from se.experiments.paired_exploration import load_candidate_spec

    spec, spec_sha = load_candidate_spec(
        "protocols/candidates/d3r_functional_regulatory_oxygen_acute_effect.json"
    )
    assert len(spec_sha) == 64
    assert spec["intervention"] == "neutralize-functional-module-physiology-output"
    assert spec["primary_metric"] == "physiology-oxygen-uptake-total"
    assert spec["mechanism_family"] == "functional-regulatory-output"
    checks = {(item["branch"], item["metric"], item["operator"], item["value"]) for item in spec["manipulation_checks"]}
    assert ("baseline", "functional_physiology_output_changed_entity_fraction", ">", 0.0) in checks
    assert ("intervention", "functional_physiology_output_changed_entity_fraction", "==", 0.0) in checks
    assert ("intervention", "functional_module_physiology_output_ablation_enabled", "==", 1.0) in checks


def test_functional_regulatory_candidate_manipulation_is_observable(tmp_path: Path) -> None:
    from se.analysis.candidate_ledger import candidate_portfolio_metadata
    from se.experiments.paired_exploration import load_candidate_spec

    root = _source_root(tmp_path, seeds=[31, 32])
    spec, spec_sha = load_candidate_spec(
        "protocols/candidates/d3r_functional_regulatory_oxygen_acute_effect.json"
    )
    plan = build_plan(
        stage="smoke",
        candidate_id=spec["candidate_id"],
        source_root=root,
        checkpoint_tick=1,
        response_ticks=2,
        intervention=spec["intervention"],
        primary_metric=spec["primary_metric"],
        metric_mode=spec["metric_mode"],
        direction=spec["direction"],
        minimum_relative_effect=0.0,
        manipulation_checks=spec["manipulation_checks"],
        candidate_spec_sha256=spec_sha,
        candidate_spec_schema=spec["schema"],
        candidate_metadata=candidate_portfolio_metadata(spec),
        output=tmp_path / "regulatory-paired",
        backend="cpu",
    )
    report = execute_plan(plan)
    assert report["assessment"]["manipulation_supported_seed_count"] == 2
    assert report["assessment"]["mechanism_family"] == "functional-regulatory-output"
    for panel in report["panels"]:
        observed = {item["metric"]: item["observed"] for item in panel["manipulation_checks"] if item["branch"] == "intervention"}
        assert observed["functional_physiology_output_changed_entity_fraction"] == 0.0
        assert observed["functional_physiology_output_effective_dimensions"] == 0.0
