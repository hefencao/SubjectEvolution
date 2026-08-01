from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import numpy as np

from se.analysis.environment_structure import build_report
from se.cfg import load_config
from se.experiments.d1_structured_environment import prepare
from se.policy import Action, ParametricPolicy
from se.runtime.resource_metabolism import settle_resource_metabolism
from se.runtime.sim import Simulation
from se.runtime.state import EntityState
from se.subjects.division import GroupFunctionDiagnostics

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = (
    ROOT
    / "studies"
    / "d1q_integrated_equilibrium_retention_v1"
    / "frozen"
    / "pilot"
    / "source_config.json"
)


def test_structured_environment_generator_changes_only_shared_physical_substrate(
    tmp_path: Path,
) -> None:
    output = tmp_path / "structured.json"
    report = prepare(template=TEMPLATE, output=output, ticks=600)
    cfg = load_config(output)
    before = json.loads(TEMPLATE.read_text(encoding="utf-8"))
    after = json.loads(output.read_text(encoding="utf-8"))

    assert report["genetic_coordinates_changed"] == 0
    assert not report["mutation_or_inheritance_changed"]
    assert not report["maintenance_or_reproduction_changed"]
    assert not report["role_or_group_label_reward_added"]
    assert before["differentiation"] == after["differentiation"]
    assert before["functional_modules"] == after["functional_modules"]
    assert cfg.environment.schema == "structured-province-resource-network-v4"
    assert cfg.physiology.resource_conversion_network_schema == (
        "paired-complementary-recipes-v1"
    )
    assert cfg.social.share_schema == "energy-and-raw-resource-need-balanced-v1"
    assert cfg.run.group_function_diagnostics_enabled
    assert report["authorization"]["single_run_gene_audit_authorized"] is False


def test_complementary_recipe_requires_both_raw_channels(tmp_path: Path) -> None:
    output = tmp_path / "structured.json"
    prepare(template=TEMPLATE, output=output, ticks=10)
    cfg = load_config(output)
    entities = EntityState(cfg)
    row = np.asarray([0], dtype=np.int32)
    entities.resource_store[row] = 0.0
    entities.resource_store[0, 0] = 0.20
    entities.resource_store[0, 1] = 0.14
    energy_before = float(entities.energy[0])

    step = settle_resource_metabolism(
        entities,
        row,
        cfg,
        genotype=entities.genotype[row],
        gene_start=ParametricPolicy.physiology_gene_start(cfg),
        processing_support=np.ones((1, 4), dtype=np.float32),
    )

    assert step.recipe_throughput_by_entity.shape == (1, 4)
    assert step.recipe_throughput_by_entity[0, 0] > 0.0
    assert np.all(step.recipe_throughput_by_entity[0, 1:] == 0.0)
    assert step.converted_by_entity[0, 0] > 0.0
    assert step.converted_by_entity[0, 1] > 0.0
    assert float(entities.energy[0]) > energy_before


def test_group_function_candidate_requires_stable_internal_complementarity(
    tmp_path: Path,
) -> None:
    tracker = GroupFunctionDiagnostics(
        tmp_path,
        window_ticks=120,
        min_members=6,
    )
    stable_ids = np.arange(1, 7, dtype=np.uint64)
    alive = np.ones(6, dtype=bool)
    groups = np.ones(6, dtype=np.uint64)
    indices = np.arange(6, dtype=np.int32)
    actions = np.asarray(
        [Action.HARVEST, Action.HARVEST, Action.REST, Action.REST, Action.SIGNAL, Action.MOVE_SOCIAL],
        dtype=np.int16,
    )
    harvested = np.zeros((6, 4), dtype=np.float64)
    harvested[0, 0] = 0.20
    harvested[1, 1] = 0.20
    throughput = np.zeros((6, 4), dtype=np.float64)
    throughput[2, 0] = 0.12
    throughput[3, 1] = 0.12
    owners = np.asarray([0, 1], dtype=np.int32)
    targets = np.asarray([2, 3], dtype=np.int32)
    shared_energy = np.zeros(2, dtype=np.float64)
    shared_raw = np.zeros((2, 4), dtype=np.float64)
    shared_raw[0, 0] = 0.10
    shared_raw[1, 1] = 0.10

    for tick in range(240):
        tracker.observe_step(
            tick=tick,
            stable_ids=stable_ids,
            alive=alive,
            group_ids=groups,
            action_actor_indices=indices,
            actions=actions,
            harvest_actor_indices=indices,
            harvested=harvested,
            conversion_actor_indices=indices,
            recipe_throughput=throughput,
            share_owner_indices=owners,
            share_target_indices=targets,
            shared_energy=shared_energy,
            shared_resources=shared_raw,
        )
    tracker.close()
    summary = tracker.summary()

    assert summary["persistent_division_candidate_count"] == 1
    assert summary["max_candidate_streak_by_token"]["1"] == 2
    assert summary["max_candidate_groups_in_window"] == 1
    latest = summary["latest"]["groups"][0]
    assert latest["stable_member_count"] == 6
    assert latest["internal_raw_exchange"] > 0.0
    assert latest["division_candidate"]


def _write_formal_seed(root: Path, seed: int) -> None:
    run = root / f"seed_{seed}"
    run.mkdir(parents=True)
    (run / "resolved_config.json").write_text(
        json.dumps({"entities": {"initial_count": 128}}), encoding="utf-8"
    )
    (run / "summary.json").write_text(
        json.dumps(
            {
                "alive": 100,
                "cumulative_births_per_initial": 1.0,
                "descendant_alive_fraction": 0.6,
            }
        ),
        encoding="utf-8",
    )
    (run / "group_function_summary.json").write_text(
        json.dumps(
            {
                "persistent_division_candidate_tokens": {"11": 3, "12": 2},
                "persistent_division_candidate_count": 2,
                "max_candidate_streak_by_token": {"11": 3, "12": 2},
                "max_candidate_groups_in_window": 2,
                "internal_raw_exchange_total": [1.0, 1.0, 1.0, 1.0],
            }
        ),
        encoding="utf-8",
    )
    (run / "environment_atlas_summary.json").write_text(
        json.dumps(
            {
                "last": {
                    "scales": [
                        {
                            "resource_field_effective_dimensions": 2.4,
                            "resource_channel_mean_abs_correlation": 0.3,
                            "region_signature_effective_dimensions": 2.0,
                            "region_signature_max_pairwise_distance": 0.4,
                        }
                    ]
                }
            }
        ),
        encoding="utf-8",
    )


def test_formal_structure_threshold_requires_replicated_multiple_division_groups(
    tmp_path: Path,
) -> None:
    for seed in (97101, 97102, 97103):
        _write_formal_seed(tmp_path, seed)
    formal = build_report(source_root=tmp_path, mode="formal", required_seed_count=3)
    exploratory = build_report(
        source_root=tmp_path, mode="exploratory", required_seed_count=3
    )

    assert formal["environment_plurality_threshold_reached"]
    assert formal["environment_maturity_stage"] == (
        "replicated-structured-group-candidates"
    )
    assert formal["authorization"]["formal_gene_retention_audit"] is False
    assert exploratory["environment_plurality_threshold_reached"] is False
    assert exploratory["evidence_class"] == "parameter-debug-only"


def test_structured_manifest_marks_spatial_asynchrony(tmp_path: Path) -> None:
    output = tmp_path / "structured.json"
    prepare(
        template=TEMPLATE,
        output=output,
        regeneration=0.015,
        processing_amplitude=0.65,
        resource_share_amount=0.12,
        recipe_rate_scale=1.0,
        trust_threshold=0.04,
        relation_decay=0.0005,
        ticks=2,
    )
    cfg = load_config(output)
    cfg = replace(
        cfg,
        run=replace(cfg.run, ticks=1, checkpoint_period=0),
        world=replace(cfg.world, initial_entities=16, max_entities=24),
    )
    Simulation(cfg, tmp_path / "run", backend="cpu")
    manifest = json.loads((tmp_path / "run/run_manifest.json").read_text())
    assert manifest["environment_spatially_asynchronous"] is True
