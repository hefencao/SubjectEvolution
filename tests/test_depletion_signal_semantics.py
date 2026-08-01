from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

from se.cfg import load_config, validate_config
from se.env.signal import (
    TERRAIN_SIGNAL_SCHEMA,
    UNIFORM_SIGNAL_SCHEMA,
    propagate_signal_field,
)
from se.runtime.harvest_contest import (
    DEPLETION_PRESSURE_SCHEMA,
    commit_harvest_contest,
    resolve_harvest_contest,
)
from se.runtime.signal_transport import (
    POST_HARVEST_RESOURCE_SCHEMA,
    TERRAIN_DIRECT_SCHEMA,
    current_signal_resources,
    direct_message_transport,
)

ROOT = Path(__file__).resolve().parents[1]
SOURCE = (
    ROOT
    / "studies"
    / "d1s_replicated_material_circuits_v1"
    / "frozen"
    / "probe"
    / "source_config.json"
)


def _cfg():
    base = load_config(SOURCE)
    return replace(
        base,
        entities=replace(
            base.entities,
            resource_contest_schema=DEPLETION_PRESSURE_SCHEMA,
            resource_contest_energy_cost_per_pressure=0.0,
            resource_contest_integrity_damage_per_pressure=0.0,
            resource_contest_radius_cells=1,
        ),
        environment=replace(
            base.environment,
            signal_propagation_schema=TERRAIN_SIGNAL_SCHEMA,
            signal_terrain_resistance_fraction=0.8,
        ),
        information=replace(
            base.information,
            resource_signal_observation_schema=POST_HARVEST_RESOURCE_SCHEMA,
            direct_message_propagation_schema=TERRAIN_DIRECT_SCHEMA,
            direct_message_distance_decay_per_cell=0.1,
            direct_message_terrain_resistance_fraction=0.8,
        ),
    )


def test_depletion_pressure_records_overlap_without_duplicate_body_damage() -> None:
    cfg = _cfg()
    validate_config(cfg)
    result = resolve_harvest_contest(
        actor_indices=np.asarray([0, 1], dtype=np.int32),
        cell_ids=np.asarray([10, 11], dtype=np.int64),
        gathered=np.asarray([[0.2, 0, 0, 0], [0.2, 0, 0, 0]], dtype=np.float32),
        group_ids=np.asarray([1, 2], dtype=np.uint64),
        stable_ids=np.asarray([11, 12], dtype=np.uint64),
        cfg=cfg,
    )
    assert result.pressure.tolist() == pytest.approx([1.0, 1.0])
    assert not np.any(result.energy_cost)
    assert not np.any(result.integrity_damage)
    assert not np.any(result.danger_evidence)

    entities = SimpleNamespace(
        energy=np.asarray([2.0, 2.0], dtype=np.float32),
        integrity=np.asarray([1.0, 1.0], dtype=np.float32),
        recent_contest_pressure=np.zeros(2, dtype=np.float32),
        memory=np.zeros((2, 3), dtype=np.float32),
    )
    commit_harvest_contest(entities, result)
    assert entities.energy.tolist() == pytest.approx([2.0, 2.0])
    assert entities.integrity.tolist() == pytest.approx([1.0, 1.0])
    assert entities.recent_contest_pressure.tolist() == pytest.approx([1.0, 1.0])
    assert not np.any(entities.memory[:, 2])


def test_terrain_reduces_signal_flux_without_changing_uniform_legacy_path() -> None:
    field = np.zeros((1, 3, 3), dtype=np.float32)
    field[0, 1, 0] = 1.0
    source = np.zeros_like(field)
    terrain = np.zeros((3, 3), dtype=np.float32)
    terrain[:, 1] = 1.0
    uniform = propagate_signal_field(
        field,
        source,
        decay=0.0,
        diffusion=0.4,
        schema=UNIFORM_SIGNAL_SCHEMA,
        xp=np,
    )
    resisted = propagate_signal_field(
        field,
        source,
        decay=0.0,
        diffusion=0.4,
        schema=TERRAIN_SIGNAL_SCHEMA,
        terrain=terrain,
        terrain_resistance_fraction=0.8,
        xp=np,
    )
    assert resisted[0, 1, 1] < uniform[0, 1, 1]
    assert float(resisted.sum()) == pytest.approx(float(field.sum()), abs=1e-6)


def test_resource_signal_can_read_authoritative_post_harvest_state() -> None:
    cfg = _cfg()
    environment = SimpleNamespace(
        cell_values=lambda cells: np.asarray([[0.1, 0.2, 0.3, 0.4]], dtype=np.float32)
    )
    simulation = SimpleNamespace(cfg=cfg, environment=environment, gpu_runtime=None)
    observed = current_signal_resources(
        simulation,
        np.asarray([5], dtype=np.int64),
        np.asarray([[0.9, 0.9, 0.9, 0.9]], dtype=np.float32),
    )
    assert np.allclose(observed, [[0.1, 0.2, 0.3, 0.4]])


def test_direct_message_transport_attenuates_with_distance_and_terrain() -> None:
    cfg = _cfg()
    cfg = replace(
        cfg,
        world=replace(
            cfg.world, grid_x=8, grid_y=8, width=8.0, height=8.0, periodic=False
        ),
    )
    entities = SimpleNamespace(
        x=np.asarray([0.1, 1.1, 5.1], dtype=np.float32),
        y=np.asarray([0.1, 0.1, 0.1], dtype=np.float32),
        alive=np.asarray([True, True, True]),
    )
    terrain = np.zeros((8, 8), dtype=np.float32)
    terrain[0, 1:6] = 1.0
    spatial = SimpleNamespace(
        cell_ids=lambda x, y: (np.floor(y).astype(np.int64) * 8 + np.floor(x).astype(np.int64))
    )
    simulation = SimpleNamespace(
        cfg=cfg,
        entities=entities,
        environment=SimpleNamespace(terrain=terrain),
        spatial=spatial,
    )
    factors = direct_message_transport(
        simulation,
        np.asarray([0, 0], dtype=np.int32),
        np.asarray([1, 2], dtype=np.int32),
    )
    assert 0.0 < factors[1] < factors[0] < 1.0
