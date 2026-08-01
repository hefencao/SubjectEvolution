from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest

from se.cfg import load_config, validate_config
from se.env.gpu import DeviceEnvironment
from se.env.world import Environment
from se.information import InformationObservation
from se.runtime.danger_messages import direct_danger_bearing
from se.runtime.harvest_contest import resolve_harvest_contest
from se.runtime.load_burden import load_movement_energy, load_speed_multiplier
from se.subjects.reconnaissance import ReconnaissanceDiagnostics

ROOT = Path(__file__).resolve().parents[1]
SOURCE = (
    ROOT
    / "studies"
    / "d1s_replicated_material_circuits_v1"
    / "frozen"
    / "probe"
    / "source_config.json"
)


def pressure_cfg():
    base = load_config(SOURCE)
    return replace(
        base,
        run=replace(
            base.run,
            ticks=2,
            metrics_period=1,
            checkpoint_period=2,
            reconnaissance_diagnostics_enabled=True,
            reconnaissance_diagnostics_schema=(
                "reconnaissance-pressure-chain-diagnostics-v1"
            ),
            reconnaissance_window_ticks=2,
        ),
        entities=replace(
            base.entities,
            resource_load_schema="raw-store-mobility-burden-v1",
            resource_load_speed_penalty_fraction=0.5,
            resource_load_movement_energy_fraction=0.5,
            resource_contest_schema="co-located-harvest-contest-v1",
            resource_contest_energy_cost_per_pressure=0.02,
            resource_contest_integrity_damage_per_pressure=0.001,
            resource_contest_pressure_retention=0.85,
            resource_contest_signal_weight=1.0,
            resource_contest_radius_cells=1,
            danger_sensing_schema="shared-inherited-radius-v1",
            danger_message_direction_schema="source-bearing-direct-message-v1",
            danger_message_direction_weight=1.0,
        ),
    )


def test_load_burden_is_monotonic_and_only_charges_movers() -> None:
    cfg = pressure_cfg()
    validate_config(cfg)
    load = np.asarray([0.0, 0.5, 1.0], dtype=np.float32)
    assert load_speed_multiplier(load, cfg).tolist() == pytest.approx(
        [1.0, 0.75, 0.5]
    )
    energy = load_movement_energy(
        np.asarray([False, True, True]), load, cfg
    )
    assert energy[0] == 0.0
    assert 0.0 < energy[1] < energy[2]


def test_harvest_contest_requires_rival_coalitions_and_overlapping_channels() -> None:
    cfg = pressure_cfg()
    actors = np.asarray([0, 1, 2], dtype=np.int32)
    cells = np.asarray([7, 7, 7], dtype=np.int32)
    stable_ids = np.asarray([11, 12, 13], dtype=np.uint64)
    gathered = np.asarray(
        [[0.1, 0.0, 0.0, 0.0], [0.1, 0.0, 0.0, 0.0], [0.0, 0.1, 0.0, 0.0]],
        dtype=np.float32,
    )
    same_group = resolve_harvest_contest(
        actor_indices=actors,
        cell_ids=cells,
        gathered=gathered,
        group_ids=np.asarray([5, 5, 5], dtype=np.uint64),
        stable_ids=stable_ids,
        cfg=cfg,
    )
    assert not np.any(same_group.pressure)

    rivals = resolve_harvest_contest(
        actor_indices=actors,
        cell_ids=cells,
        gathered=gathered,
        group_ids=np.asarray([5, 6, 7], dtype=np.uint64),
        stable_ids=stable_ids,
        cfg=cfg,
    )
    assert rivals.pressure[:2].tolist() == pytest.approx([1.0, 1.0])
    assert rivals.pressure[2] == 0.0
    assert rivals.event_count == 2


def test_shared_danger_radius_matches_cpu_device_and_changes_gradient() -> None:
    cfg = pressure_cfg()
    host = Environment(cfg)
    device = DeviceEnvironment(cfg, backend="cpu")
    yy, xx = np.mgrid[0 : cfg.world.grid_y, 0 : cfg.world.grid_x]
    field = (xx.astype(np.float32) ** 3 + yy.astype(np.float32)).astype(np.float32)
    host.hazard = field.copy()
    device.hazard = field.copy()
    cells = np.full(cfg.world.max_entities, -1, dtype=np.int32)
    cells[:2] = [8 * cfg.world.grid_x + 8, 8 * cfg.world.grid_x + 8]
    radii = np.ones(cfg.world.max_entities, dtype=np.int16)
    radii[1] = 4
    host_grad = host.gradients_for_entities(
        cells, cfg.world.max_entities, danger_sensing_radius=radii
    )[1]
    device_grad = device.gradients_for_entities(
        cells, cfg.world.max_entities, danger_sensing_radius=radii
    )[1]
    assert np.array_equal(host_grad[0], device_grad[0])
    assert np.array_equal(host_grad[1], device_grad[1])
    assert host_grad[0][0] != pytest.approx(host_grad[0][1])


def test_reconnaissance_diagnostics_require_signal_message_and_response_chain(
    tmp_path: Path,
) -> None:
    tracker = ReconnaissanceDiagnostics(
        tmp_path,
        window_ticks=2,
        min_members=2,
        world_width=10.0,
        world_height=10.0,
    )
    stable_ids = np.asarray([1, 2], dtype=np.uint64)
    alive = np.asarray([True, True])
    groups = np.asarray([9, 9], dtype=np.uint64)
    x = np.asarray([0.0, 4.0], dtype=np.float32)
    y = np.asarray([0.0, 0.0], dtype=np.float32)
    load = np.asarray([0.8, 0.1], dtype=np.float32)
    reach = np.asarray([1, 4], dtype=np.int16)
    contest = np.asarray([0.0, 0.8], dtype=np.float32)

    class Info:
        message_mask = np.asarray([[True], [True]])
        messages = np.asarray([[[0.0, 0.8, 0.0]], [[0.0, 0.8, 0.0]]], dtype=np.float32)
        message_source_id = np.asarray([[2], [2]], dtype=np.uint64)

    for tick in range(2):
        tracker.observe_step(
            tick=tick,
            active=np.asarray([0, 1], dtype=np.int32),
            stable_ids=stable_ids,
            alive=alive,
            group_ids=groups,
            x=x,
            y=y,
            load_fraction=load,
            sensing_radius=reach,
            recent_contest_pressure=contest,
            actions=np.asarray([7, 5], dtype=np.int16),  # FLEE, SIGNAL
            direction_x=np.asarray([-1.0, 0.0], dtype=np.float32),
            direction_y=np.asarray([0.0, 0.0], dtype=np.float32),
            information=Info(),
        )
    summary = tracker.close()
    assert summary["total_frontier_signal_events"] == 2
    assert summary["total_same_group_danger_messages"] >= 2
    assert summary["total_aligned_flee_responses"] >= 2


def test_contest_radius_reaches_adjacent_cells_but_not_distant_cells() -> None:
    cfg = pressure_cfg()
    actors = np.asarray([0, 1, 2], dtype=np.int32)
    grid_x = cfg.world.grid_x
    cells = np.asarray([5 * grid_x + 5, 5 * grid_x + 6, 5 * grid_x + 8])
    gathered = np.asarray([[0.1, 0, 0, 0], [0.1, 0, 0, 0], [0.1, 0, 0, 0]], dtype=np.float32)
    result = resolve_harvest_contest(
        actor_indices=actors, cell_ids=cells, gathered=gathered,
        group_ids=np.asarray([1, 2, 3], dtype=np.uint64),
        stable_ids=np.asarray([11, 12, 13], dtype=np.uint64), cfg=cfg,
    )
    assert result.pressure[:2].tolist() == pytest.approx([1.0, 1.0])
    assert result.pressure[2] == 0.0


def test_direct_danger_message_supplies_source_bearing() -> None:
    cfg = pressure_cfg()
    info = InformationObservation(
        signals=np.zeros((1, 3), dtype=np.float32),
        signal_mask=np.zeros((1, 3), dtype=bool),
        signal_age=np.zeros((1, 3), dtype=np.float32),
        messages=np.asarray([[[0.0, 0.8, 0.0]]], dtype=np.float32),
        message_mask=np.asarray([[True]]),
        message_age=np.zeros((1, 1), dtype=np.uint32),
        message_confidence=np.ones((1, 1), dtype=np.float32),
        message_source_id=np.asarray([[2]], dtype=np.uint64),
        message_corruption=np.zeros((1, 1), dtype=np.uint8),
        partner_energy=np.empty((1, 0), dtype=np.float32),
        partner_group_match=np.empty((1, 0), dtype=np.float32),
        partner_mask=np.empty((1, 0), dtype=bool),
        uncertainty=np.zeros((1, 3), dtype=np.float32),
    )
    dx, dy = direct_danger_bearing(
        active=np.asarray([0], dtype=np.int32),
        stable_ids=np.asarray([1, 2], dtype=np.uint64),
        x=np.asarray([0.0, 4.0], dtype=np.float32),
        y=np.asarray([0.0, 0.0], dtype=np.float32),
        info=info, cfg=cfg,
    )
    assert dx.tolist() == pytest.approx([1.0])
    assert dy.tolist() == pytest.approx([0.0])
