from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import numpy as np

from se.cfg import load_config, validate_config
from se.differentiation.physiology import (
    CONSERVATIVE_INTAKE_PHYSIOLOGY_SCHEMA,
    physiology_phenotype,
    storage_constrained_intake_enabled,
)
from se.env.niches import (
    AFFINITY_SCALE,
    constrain_harvest_request_rates,
    policy_resource_view,
    resource_affinity_quantized,
)
from se.experiments.d3_conservative_intake import execute_conservative_intake
from se.policy import ParametricPolicy
from se.runtime.resource_metabolism import raw_harvest_room, storage_room_fraction
from se.runtime.state import EntityState

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "configs" / "mvp_short_d3b_conservative_intake_longrun.json"
LEGACY = ROOT / "configs" / "mvp_short_d3a_resource_metabolism_longrun.json"


def test_v5_schema_requires_preharvest_capacity_contract() -> None:
    cfg = load_config(CONFIG)
    assert cfg.physiology.schema == CONSERVATIVE_INTAKE_PHYSIOLOGY_SCHEMA
    assert storage_constrained_intake_enabled(cfg)
    invalid = replace(
        cfg,
        physiology=replace(
            cfg.physiology,
            schema="transport-metabolism-messenger-tissue-resource-v4",
        ),
    )
    validate_config(invalid)
    assert not storage_constrained_intake_enabled(invalid)


def test_raw_request_is_capped_in_environmental_units() -> None:
    cfg = load_config(CONFIG)
    entities = EntityState(cfg)
    rows = np.array([0], dtype=np.int32)
    start = ParametricPolicy.physiology_gene_start(cfg)
    phenotype = physiology_phenotype(
        entities.genotype[rows], cfg, gene_start=start
    )
    affinity = resource_affinity_quantized(entities.genotype, cfg)[rows]
    room_assimilated = np.array([[0.02, 0.03, 0.04, 0.05]], dtype=np.float64)
    entities.resource_store[rows] = (
        phenotype.resource_store_capacity - room_assimilated
    ).astype(np.float32)
    room_raw = raw_harvest_room(
        entities,
        rows,
        cfg,
        genotype=entities.genotype[rows],
        gene_start=start,
        resource_affinity_q=affinity,
    )
    assert room_raw is not None
    requested = np.full((1, 4), 0.5, dtype=np.float32)
    admitted, rejected = constrain_harvest_request_rates(requested, room_raw)
    assert np.all(admitted <= room_raw + 1.0e-7)
    assimilated = admitted.astype(np.float64) * affinity / AFFINITY_SCALE
    assert np.all(assimilated <= room_assimilated + 2.0e-6)
    assert np.allclose(admitted + rejected, requested, atol=1.0e-7, rtol=0.0)


def test_policy_resource_utility_respects_store_room() -> None:
    cfg = load_config(CONFIG)
    entities = EntityState(cfg)
    rows = np.array([0], dtype=np.int32)
    start = ParametricPolicy.physiology_gene_start(cfg)
    phenotype = physiology_phenotype(entities.genotype[rows], cfg, gene_start=start)
    entities.resource_store[rows] = phenotype.resource_store_capacity.astype(np.float32)
    room = storage_room_fraction(
        entities,
        rows,
        cfg,
        genotype=entities.genotype[rows],
        gene_start=start,
    )
    local = np.full((1, 4), 4.0, dtype=np.float32)
    affinity = resource_affinity_quantized(entities.genotype, cfg)[rows]
    view = policy_resource_view(
        local,
        entities.genotype[rows],
        cfg,
        resource_affinity_q=affinity,
        storage_room_fraction=room,
    )
    assert view[0, 0] == 0.0
    legacy = load_config(LEGACY)
    legacy_view = policy_resource_view(
        local,
        entities.genotype[rows],
        legacy,
        resource_affinity_q=affinity,
    )
    assert legacy_view[0, 0] > 0.0


def test_d3b_end_to_end_has_no_post_assimilation_overflow(tmp_path: Path) -> None:
    cfg = load_config(CONFIG)
    cfg = replace(
        cfg,
        run=replace(cfg.run, ticks=20, metrics_period=5, checkpoint_period=10),
        world=replace(cfg.world, initial_entities=96, max_entities=128),
    )
    result = execute_conservative_intake(
        cfg,
        (54001, 54002),
        tmp_path / "run",
        backend="cpu",
        until_tick=20,
    )
    assert result["completed_seed_count"] == 2
    assert all(row["valid"] for row in result["intake_ledger"])
    assert all(row["valid"] for row in result["store_ledger"])
    assert all(
        sum(row["post_assimilation_overflow"]) <= 1.0e-4
        for row in result["intake_ledger"]
    )
    assert any(
        sum(row["capacity_rejected"]) > 0.0 for row in result["intake_ledger"]
    )
