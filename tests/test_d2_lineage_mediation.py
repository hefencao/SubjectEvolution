from __future__ import annotations

from dataclasses import asdict, replace
import json
from pathlib import Path

import numpy as np

from se.analysis.d2_lineage_mediation_effects import (
    ASSESSMENT_SCHEMA,
    EFFECT_RULES,
    assess_mediation_results,
)
from se.cfg import load_config, validate_config
from se.experiments.d2_lineage_mediation import (
    PLAN_SCHEMA,
    RESULT_SCHEMA,
    LineageMediationPlan,
    build_mediation_plan,
    execute_mediation_plan,
)
from se.experiments.d2_lineage_pairs import (
    PLAN_SCHEMA as LINEAGE_PLAN_SCHEMA,
    LineagePairCheckpoint,
    LineagePairPlan,
    LineageSelection,
)
from se.runtime.sim import Simulation


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "configs" / "d2a_contextual_harvest_smoke.json"


def _selection(lineage_id: int, members: int, rank: int) -> LineageSelection:
    return LineageSelection(
        lineage_id=lineage_id,
        members=members,
        member_fraction=members / 20.0,
        abundance_rank=rank,
    )


def _source_plan(checkpoint_path: str = "/tmp/source.sechk") -> LineagePairPlan:
    checkpoint = LineagePairCheckpoint(
        run_name="seed_10001",
        phase="peak",
        checkpoint_tick=100,
        checkpoint_path=checkpoint_path,
        until_tick=400,
        active_entities=20,
        effective_lineages=2.2,
        dominant_lineage_fraction=0.6,
        eligible=True,
        ineligible_reason=None,
        lineages=(
            _selection(11, 12, 1),
            _selection(12, 5, 2),
            _selection(13, 3, 3),
        ),
    )
    return LineagePairPlan(
        schema=LINEAGE_PLAN_SCHEMA,
        horizon_ticks=300,
        module_indices=(2, 3),
        min_lineage_members=2,
        min_lineages_per_checkpoint=3,
        max_lineages_per_checkpoint=4,
        checkpoints=(checkpoint,),
    )


def test_mediation_plan_selects_confirmed_module_and_preserves_pairs(
    tmp_path: Path,
) -> None:
    source = _source_plan()
    source_path = tmp_path / "source_plan.json"
    source_path.write_text(json.dumps(asdict(source)), encoding="utf-8")
    assessment = {
        "schema": "d2-lineage-paired-assessment-v1",
        "confirmed_modules": [3],
    }
    plan = build_mediation_plan(
        assessment,
        source_path,
        observation_offsets=(30, 60, 120, 300),
    )
    assert plan.schema == PLAN_SCHEMA
    assert plan.module_indices == (3,)
    assert plan.observation_offsets == (30, 60, 120, 300)
    assert plan.outcome_conditioned_pair_selection is False
    assert plan.preserves_all_source_pairs_for_selected_modules is True
    assert tuple(item.lineage_id for item in plan.checkpoints[0].lineages) == (
        11,
        12,
        13,
    )


def test_read_only_run_observer_preserves_authoritative_trajectory(
    tmp_path: Path,
) -> None:
    cfg = load_config(CONFIG)
    cfg = replace(
        cfg,
        run=replace(
            cfg.run,
            ticks=5,
            metrics_period=5,
            checkpoint_period=99,
            checkpoint_ticks=(),
            full_checkpoint_enabled=False,
            evolution_evaluation_period=5,
        ),
        world=replace(cfg.world, initial_entities=24, max_entities=32),
    )
    validate_config(cfg)
    baseline = Simulation(cfg, tmp_path / "baseline", backend="cpu")
    observed = Simulation(cfg, tmp_path / "observed", backend="cpu")
    ticks: list[int] = []

    def observer(simulation: Simulation, stats) -> None:
        ticks.append(int(simulation.tick))
        _ = float(simulation.entities.energy[simulation.entities.alive].sum())

    baseline_summary = baseline.run(until_tick=5)
    observed_summary = observed.run(until_tick=5, tick_observer=observer)
    assert ticks == [0, 1, 2, 3, 4, 5]
    for name in (
        "entity_id",
        "alive",
        "energy",
        "integrity",
        "fertility",
        "lineage_id",
        "genotype",
    ):
        assert np.array_equal(
            getattr(baseline.entities, name), getattr(observed.entities, name)
        )
    common = set(baseline_summary) & set(observed_summary)
    for key in common:
        if "seconds" not in key and "elapsed" not in key:
            assert baseline_summary[key] == observed_summary[key]


def test_mediation_plan_executes_trajectory_and_closes_decomposition(
    tmp_path: Path,
) -> None:
    cfg = load_config(CONFIG)
    cfg = replace(
        cfg,
        run=replace(
            cfg.run,
            ticks=4,
            metrics_period=4,
            checkpoint_period=99,
            checkpoint_ticks=(1,),
            full_checkpoint_enabled=True,
            evolution_evaluation_period=2,
        ),
        world=replace(cfg.world, initial_entities=20, max_entities=28),
    )
    validate_config(cfg)
    source_dir = tmp_path / "source"
    source = Simulation(cfg, source_dir, backend="cpu")
    source.run(until_tick=1)
    checkpoint_path = source_dir / "checkpoint_00000001.sechk"
    restored = Simulation.from_checkpoint(
        checkpoint_path, tmp_path / "inspect", backend="cpu", until_tick=3
    )
    active = np.flatnonzero(restored.entities.alive)
    lineage_id = int(restored.entities.lineage_id[active[0]])
    members = int(
        np.count_nonzero(
            restored.entities.alive
            & (restored.entities.lineage_id == np.uint64(lineage_id))
        )
    )
    checkpoint = LineagePairCheckpoint(
        run_name="seed_test",
        phase="probe",
        checkpoint_tick=1,
        checkpoint_path=str(checkpoint_path),
        until_tick=3,
        active_entities=int(active.size),
        effective_lineages=float(active.size),
        dominant_lineage_fraction=1.0 / active.size,
        eligible=True,
        ineligible_reason=None,
        lineages=(
            LineageSelection(
                lineage_id=lineage_id,
                members=members,
                member_fraction=members / active.size,
                abundance_rank=2,
            ),
        ),
    )
    plan = LineageMediationPlan(
        schema=PLAN_SCHEMA,
        source_assessment_schema="d2-lineage-paired-assessment-v1",
        source_assessment_sha256=None,
        source_persistent_output_expectations={"module_3": {}},
        source_plan_schema=LINEAGE_PLAN_SCHEMA,
        source_plan_horizon_ticks=300,
        module_indices=(3,),
        observation_offsets=(1, 2),
        checkpoints=(checkpoint,),
    )
    report = execute_mediation_plan(plan, tmp_path / "mediation", backend="cpu")
    assert report["schema"] == RESULT_SCHEMA
    assert report["executed_pair_count"] == 1
    row = report["checkpoints"][0]["pairs"][0]
    assert [
        item["offset_ticks"] for item in row["branches"]["baseline"]["trajectory"]
    ] == [1, 2]
    for offset in ("1", "2"):
        assert max(
            abs(value)
            for value in row["effects"]["decomposition_residual"][offset].values()
        ) <= 1e-12


def _synthetic_result() -> dict:
    outcomes = {name: 100.0 for name in EFFECT_RULES}
    rows = []
    for seed_index, lineage_id in ((1, 101), (2, 202)):
        effects = {
            effect_name: {
                str(offset): {name: 0.0 for name in EFFECT_RULES}
                for offset in (30, 60)
            }
            for effect_name in (
                "output_routing_effect",
                "retained_expression_cost_effect",
                "total_expression_effect",
                "decomposition_residual",
            )
        }
        for offset in (30, 60):
            effects["output_routing_effect"][str(offset)][
                "target_lineage.harvested_energy_since_intervention"
            ] = 5.0
            effects["output_routing_effect"][str(offset)][
                "target_lineage.mean_energy"
            ] = 0.05
            effects["output_routing_effect"][str(offset)][
                "target_lineage.total_energy"
            ] = 5.0
            effects["total_expression_effect"][str(offset)].update(
                effects["output_routing_effect"][str(offset)]
            )
        trajectory = [
            {
                "offset_ticks": offset,
                "absolute_tick": 100 + offset,
                "outcomes": outcomes,
            }
            for offset in (30, 60)
        ]
        rows.append(
            {
                "pair": {
                    "run_name": f"seed_{seed_index}",
                    "phase": "peak",
                    "checkpoint_tick": 100,
                    "lineage_id": lineage_id,
                    "source_members": 20,
                    "source_member_fraction": 0.2,
                    "source_abundance_rank": 2,
                },
                "module_index": 3,
                "branches": {"baseline": {"trajectory": trajectory}},
                "effects": effects,
            }
        )
    return {
        "schema": RESULT_SCHEMA,
        "plan": {
            "module_indices": [3],
            "observation_offsets": [30, 60],
            "checkpoints": [
                {
                    "effective_lineages": 2.2,
                    "dominant_lineage_fraction": 0.6,
                }
            ],
        },
        "checkpoints": [{"pairs": rows}],
    }


def test_mediation_assessment_requires_cross_seed_pairs_within_offset() -> None:
    report = assess_mediation_results(_synthetic_result())
    assert report["schema"] == ASSESSMENT_SCHEMA
    temporal = report["modules"]["module_3"]["temporal_mediation"]
    assert temporal["classification"] == (
        "flow-to-energy-without-demographic-conversion"
    )
    assert temporal["mean_energy_earliest_positive_offset"] == 30
    assert temporal["harvest_precedes_or_matches_mean_energy"] is True
    assert temporal["demographic_conversion_after_energy"] is False
    assert report["duplication_ready_modules"] == []
