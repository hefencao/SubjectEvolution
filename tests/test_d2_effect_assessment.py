from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import numpy as np

from se.analysis.d2_effects import EFFECT_RULES, assess_module_audits
from se.cfg import load_config
from se.experiments.d2_module_audit import (
    RESULT_SCHEMA,
    checkpoint_functional_footprint,
)
from se.policy import ParametricPolicy
from se.runtime.sim import Simulation


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "configs" / "d2a_contextual_harvest_smoke.json"


def _strong_module_genotype(cfg, rows: int) -> np.ndarray:
    size = ParametricPolicy.genome_size_for_config(cfg)
    start = ParametricPolicy.functional_module_gene_start(cfg)
    genotype = np.zeros((rows, size), dtype=np.float32)
    genotype[:, start] = 0.9
    genotype[:, start + 2] = 0.9  # energy-deficit input
    output = start + 12
    genotype[:, output : output + 4] = (-0.9, 0.9, -0.9, -0.9)
    return genotype


def test_checkpoint_footprint_is_immediate_and_lineage_resolved(tmp_path: Path) -> None:
    cfg = load_config(CONFIG)
    cfg = replace(
        cfg,
        run=replace(
            cfg.run,
            ticks=1,
            full_checkpoint_enabled=True,
            checkpoint_ticks=(),
            checkpoint_period=99,
        ),
        world=replace(cfg.world, initial_entities=24, max_entities=32),
    )
    sim = Simulation(cfg, tmp_path / "source", backend="cpu")
    active = np.flatnonzero(sim.entities.alive)
    sim.entities.genotype[active] = _strong_module_genotype(cfg, active.size)
    sim.entities.lineage_id[active] = np.uint64(7)
    checkpoint = sim.save_full_checkpoint()

    footprint = checkpoint_functional_footprint(checkpoint)
    assert footprint["schema"] == "d2-module-immediate-footprint-v1"
    assert footprint["active_entities"] == active.size
    effect = footprint["effects"]["module_0_expression_effect"]
    assert effect["preference_changed_fraction"] > 0.9
    assert effect["preference_total_variation_mean"] > 0.0
    assert effect["lineages"][0]["lineage_id"] == 7
    assert effect["lineages"][0]["members"] == active.size


def _synthetic_results(*, horizon: int, with_footprint: bool, ecological: bool):
    checkpoints = []
    runs = ["seed_1", "seed_1", "seed_2", "seed_2", "seed_3", "seed_3"]
    phases = ["peak", "trough"] * 3
    effect_names = [
        "all_module_expression_effect",
        "module_0_expression_effect",
        "module_1_expression_effect",
        "module_2_expression_effect",
        "module_3_expression_effect",
        "module_nonadditivity",
    ]
    for index, (run_name, phase) in enumerate(zip(runs, phases)):
        baseline = {metric: 10.0 for metric in EFFECT_RULES}
        baseline["world.alive"] = 400.0
        baseline["evolution.effective_lineages"] = 5.0
        effects = {
            name: {metric: 0.0 for metric in EFFECT_RULES} for name in effect_names
        }
        effects["module_3_expression_effect"][
            "derived.harvest_extraction_efficiency_window"
        ] = 0.006 if horizon >= 300 else 0.001
        if ecological and index < 4:
            effects["module_3_expression_effect"]["world.alive"] = 4.0
        branches = {
            "baseline": {"outcomes": baseline},
            "all-modules-neutral": {"outcomes": baseline},
            "module-0-neutral": {"outcomes": baseline},
            "module-1-neutral": {"outcomes": baseline},
            "module-2-neutral": {"outcomes": baseline},
            "module-3-neutral": {"outcomes": baseline},
        }
        item = {
            "checkpoint": {
                "run_name": run_name,
                "phase": phase,
                "checkpoint_tick": 1000 + index,
            },
            "branches": branches,
            "effects": effects,
        }
        if with_footprint:
            lineages = [
                {
                    "lineage_id": 1,
                    "members": 40,
                    "preference_changed_fraction": 0.2,
                    "preference_total_variation_mean": 0.001,
                    "conditional_harvest_channel_changed_fraction": 0.02,
                },
                {
                    "lineage_id": 2,
                    "members": 30,
                    "preference_changed_fraction": 0.15,
                    "preference_total_variation_mean": 0.001,
                    "conditional_harvest_channel_changed_fraction": 0.01,
                },
            ]
            item["checkpoint_footprint"] = {
                "active_entities": 400,
                "effects": {
                    name: {
                        "preference_changed_fraction": (
                            0.2 if name == "module_3_expression_effect" else 0.0
                        ),
                        "preference_total_variation_mean": (
                            0.001 if name == "module_3_expression_effect" else 0.0
                        ),
                        "conditional_harvest_channel_changed_fraction": (
                            0.02 if name == "module_3_expression_effect" else 0.0
                        ),
                        "lineages": lineages if name == "module_3_expression_effect" else [],
                    }
                    for name in effect_names
                    if name != "module_nonadditivity"
                },
            }
        checkpoints.append(item)
    return {
        "schema": RESULT_SCHEMA,
        "plan": {"horizon_ticks": horizon},
        "checkpoints": checkpoints,
    }


def test_assessment_distinguishes_mechanistic_effect_from_duplication_gate() -> None:
    short = _synthetic_results(horizon=120, with_footprint=False, ecological=False)
    long = _synthetic_results(horizon=300, with_footprint=False, ecological=False)
    report = assess_module_audits(long, short_results=short)
    module = report["module_effects"]["module_3_expression_effect"]
    assert module["classification"] == "provisional-replicated-mechanistic-only"
    assert module["robust_mechanistic"] is True
    assert module["duplication_ready"] is False
    assert report["recommendation"] == "refresh-immediate-footprints-before-duplication-decision"


def test_assessment_requires_cross_lineage_footprint_and_ecological_replication() -> None:
    short = _synthetic_results(horizon=120, with_footprint=True, ecological=True)
    long = _synthetic_results(horizon=300, with_footprint=True, ecological=True)
    report = assess_module_audits(long, short_results=short)
    module = report["module_effects"]["module_3_expression_effect"]
    assert module["robust_ecological"] is True
    assert module["cross_lineage_footprint"] is True
    assert module["duplication_ready"] is True
    assert report["duplication_candidates"] == ["module_3_expression_effect"]


def test_single_120_tick_assessment_recommends_long_confirmation() -> None:
    short = _synthetic_results(horizon=120, with_footprint=False, ecological=True)
    report = assess_module_audits(short)
    assert report["recommendation"] == "run-300-tick-confirmation"
