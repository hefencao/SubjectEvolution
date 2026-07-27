from __future__ import annotations

from dataclasses import asdict, replace
from pathlib import Path

import numpy as np

from se.analysis.d2_source_population_effects import (
    ASSESSMENT_SCHEMA,
    assess_source_population_results,
)
from se.cfg import load_config, validate_config
from se.checkpointing import read_checkpoint_bundle
from se.experiments.d2_source_population import (
    PLAN_SCHEMA,
    RESULT_SCHEMA,
    DonorLineage,
    FounderAllocation,
    SourcePopulationPanel,
    SourcePopulationPlan,
    build_source_population_plan,
    execute_source_population_plan,
)
from se.runtime.sim import Simulation

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "configs" / "d2a_contextual_harvest_smoke.json"


def _assessment() -> dict:
    return {
        "schema": "d2-lineage-mediation-assessment-v1",
        "recommendation": "causal-chain-supported-redesign-source-population-before-copy-number",
        "modules": {
            "module_3": {
                "source_expectation_reproduced_at_final_offset": False,
                "temporal_mediation": {
                    "demographic_conversion_after_energy": True,
                },
            }
        },
    }


def _mediation_results() -> dict:
    checkpoints = []
    for phase, tick in (("peak", 100), ("trough", 200)):
        for run_index in range(3):
            checkpoints.append(
                {
                    "run_name": f"seed_{run_index}",
                    "phase": phase,
                    "checkpoint_tick": tick + run_index,
                    "checkpoint_path": f"/tmp/{phase}_{run_index}.sechk",
                    "lineages": [
                        {
                            "lineage_id": 10 + run_index * 10,
                            "members": 100,
                            "member_fraction": 0.6,
                            "abundance_rank": 1,
                        },
                        {
                            "lineage_id": 11 + run_index * 10,
                            "members": 40,
                            "member_fraction": 0.25,
                            "abundance_rank": 2,
                        },
                        {
                            "lineage_id": 12 + run_index * 10,
                            "members": 10,
                            "member_fraction": 0.06,
                            "abundance_rank": 3,
                        },
                    ],
                }
            )
    return {
        "schema": "d2-lineage-mediation-results-v1",
        "plan": {"checkpoints": checkpoints},
    }


def test_plan_uses_cross_run_preintervention_lineages_without_response_selection() -> None:
    plan = build_source_population_plan(
        _assessment(),
        _mediation_results(),
        panel_seeds=(7, 8),
        lineages_per_run=2,
        max_founders_per_lineage=32,
        min_lineage_members=8,
        burn_in_ticks=60,
        observation_offsets=(0, 30, 60),
    )
    assert plan.schema == PLAN_SCHEMA
    assert plan.candidate_module_indices == (3,)
    assert plan.source_endpoint_reproduced is False
    assert plan.transient_causal_chain_supported is True
    assert plan.outcome_conditioned_lineage_selection is False
    assert plan.ongoing_lineage_protection is False
    assert plan.module_copy_number_changed is False
    assert len(plan.panels) == 4
    panel = plan.panels[0]
    assert len(panel.donors) == 6
    assert panel.equal_founders_per_lineage == 32
    assert panel.total_founders == 192
    assert sum(row.founder_count for row in panel.natural_allocations) == 192
    assert sum(row.founder_count for row in panel.equal_allocations) == 192
    assert len({row.panel_lineage_id for row in panel.donors}) == 6


def _donor_checkpoint(tmp_path: Path, run_name: str, seed: int) -> tuple[Path, list[int]]:
    cfg = load_config(CONFIG)
    cfg = replace(
        cfg,
        run=replace(
            cfg.run,
            seed=seed,
            ticks=2,
            metrics_period=2,
            checkpoint_period=99,
            checkpoint_ticks=(),
            full_checkpoint_enabled=False,
            evolution_evaluation_period=2,
        ),
        world=replace(cfg.world, initial_entities=12, max_entities=32),
    )
    validate_config(cfg)
    simulation = Simulation(cfg, tmp_path / run_name, backend="cpu")
    active = np.flatnonzero(simulation.entities.alive).astype(np.int32)
    lineage_ids = [seed * 10 + 1, seed * 10 + 2]
    simulation.entities.lineage_id[active[:6]] = np.uint64(lineage_ids[0])
    simulation.entities.lineage_id[active[6:]] = np.uint64(lineage_ids[1])
    path = simulation.save_full_checkpoint(
        tmp_path / run_name / "checkpoint_00000000.sechk"
    )
    return path, lineage_ids


def test_source_population_execution_builds_paired_fresh_worlds(tmp_path: Path) -> None:
    checkpoint_a, lineages_a = _donor_checkpoint(tmp_path, "a", 1)
    checkpoint_b, lineages_b = _donor_checkpoint(tmp_path, "b", 2)
    donors = (
        DonorLineage("a", "peak", 0, str(checkpoint_a), lineages_a[0], 6, 1, 101),
        DonorLineage("a", "peak", 0, str(checkpoint_a), lineages_a[1], 6, 2, 102),
        DonorLineage("b", "peak", 0, str(checkpoint_b), lineages_b[0], 6, 1, 201),
        DonorLineage("b", "peak", 0, str(checkpoint_b), lineages_b[1], 6, 2, 202),
    )
    allocations = tuple(FounderAllocation(row.panel_lineage_id, 3) for row in donors)
    panel = SourcePopulationPanel(
        panel_name="peak_seed_9",
        phase="peak",
        panel_seed=9,
        total_founders=12,
        equal_founders_per_lineage=3,
        donors=donors,
        natural_allocations=allocations,
        equal_allocations=allocations,
    )
    plan = SourcePopulationPlan(
        schema=PLAN_SCHEMA,
        source_assessment_schema="d2-lineage-mediation-assessment-v1",
        source_assessment_sha256=None,
        source_result_schema="d2-lineage-mediation-results-v1",
        source_result_sha256=None,
        candidate_module_indices=(3,),
        source_endpoint_reproduced=False,
        transient_causal_chain_supported=True,
        panel_seeds=(9,),
        phases=("peak",),
        lineages_per_run=2,
        max_founders_per_lineage=3,
        min_lineage_members=2,
        burn_in_ticks=2,
        observation_offsets=(0, 1, 2),
        panels=(panel,),
    )
    report = execute_source_population_plan(plan, tmp_path / "execution", backend="cpu")
    assert report["schema"] == RESULT_SCHEMA
    assert report["executed_panel_count"] == 1
    assert report["executed_arm_count"] == 2
    row = report["panels"][0]
    initial_states = {}
    for arm in ("natural-abundance-control", "equal-lineage-reconstitution"):
        payload = row["arms"][arm]
        assert Path(payload["initial_checkpoint"]).is_file()
        assert Path(payload["final_checkpoint"]).is_file()
        assert [item["offset_ticks"] for item in payload["trajectory"]] == [0, 1, 2]
        assert payload["trajectory"][0]["effective_lineages"] == 4.0
        assert payload["intervention_history"][-1]["ongoing_lineage_protection"] is False
        manifest = payload["founder_manifest"]
        assert len(manifest) == 12
        assert len(
            {(item["source_run_name"], item["source_entity_id"]) for item in manifest}
        ) == 12
        assert payload["founder_manifest_sha256"] == payload["intervention_history"][-1][
            "founder_manifest_sha256"
        ]
        _, bundle = read_checkpoint_bundle(payload["initial_checkpoint"] )
        initial_states[arm] = bundle["simulation"]["entities"]

    natural = initial_states["natural-abundance-control"]
    equal = initial_states["equal-lineage-reconstitution"]
    for name in ("entity_id", "alive", "x", "y", "energy", "integrity"):
        np.testing.assert_array_equal(getattr(natural, name), getattr(equal, name))


def _qualification_results(equal_pass: bool = True) -> dict:
    panels = []
    for phase in ("peak", "trough"):
        for seed in (1, 2):
            arms = {}
            for arm_name in ("natural-abundance-control", "equal-lineage-reconstitution"):
                qualifies = equal_pass and arm_name == "equal-lineage-reconstitution"
                final = {
                    "offset_ticks": 600,
                    "effective_lineages": 4.5 if qualifies else 2.0,
                    "dominant_lineage_fraction": 0.3 if qualifies else 0.7,
                    "eligible_panel_lineage_count": 5 if qualifies else 2,
                    "candidate_module_expression": {
                        "module_3": {
                            "expressed_eligible_lineage_count": 5 if qualifies else 2
                        }
                    },
                }
                arms[arm_name] = {"trajectory": [final]}
            panels.append(
                {
                    "panel_name": f"{phase}_{seed}",
                    "phase": phase,
                    "panel_seed": seed,
                    "arms": arms,
                }
            )
    return {
        "schema": RESULT_SCHEMA,
        "plan": {
            "burn_in_ticks": 600,
            "candidate_module_indices": [3],
            "min_lineage_members": 8,
            "phases": ["peak", "trough"],
        },
        "panels": panels,
    }


def test_assessment_requires_two_seeds_in_two_phases_and_never_releases_copy_number() -> None:
    report = assess_source_population_results(_qualification_results())
    assert report["schema"] == ASSESSMENT_SCHEMA
    assert report["source_population_ready"] is True
    assert report["module_copy_number_ready"] is False
    assert report["qualified_phases"] == ["peak", "trough"]
    assert report["recommendation"] == (
        "source-population-qualified-freeze-checkpoints-before-copy-number-audit"
    )

    failed = assess_source_population_results(_qualification_results(False))
    assert failed["source_population_ready"] is False
    assert failed["module_copy_number_ready"] is False
