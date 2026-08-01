from __future__ import annotations

from dataclasses import replace
import json
from pathlib import Path

import numpy as np

from se.cfg import load_config
from se.env.physiology import physiology_fields
from se.env.signal import OPENNESS_SIGNAL_SCHEMA, propagate_signal_field
from se.env.signal_medium import medium_metrics, signal_openness_field
from se.experiments.d1_independent_signal_medium import prepare


ROOT = Path(__file__).resolve().parents[1]
STUDY = ROOT / "studies/d1v_independent_signal_medium_v1"


def test_d1v_prepare_changes_only_transport_fields(tmp_path: Path) -> None:
    output = tmp_path / "config.json"
    report = prepare(
        template=STUDY / "frozen/d1u/source_config.json",
        output=output,
    )
    cfg = load_config(output)
    assert cfg.environment.signal_propagation_schema == (
        "independent-openness-diffusion-v2"
    )
    assert cfg.environment.signal_medium_schema == "independent-openness-mosaic-v1"
    assert cfg.information.direct_message_propagation_schema == (
        "openness-distance-attenuated-v2"
    )
    assert report["genetic_coordinates_changed"] == 0
    assert report["movement_formula_changed"] is False
    assert report["direct_conflict_enabled"] is False
    assert report["transport_fields"]["movement_signal_correlation"] > 0.95


def test_signal_openness_is_not_fixed_to_movement_direction(tmp_path: Path) -> None:
    output = tmp_path / "config.json"
    prepare(template=STUDY / "frozen/d1u/source_config.json", output=output)
    cfg = load_config(output)
    _, movement, _ = physiology_fields(cfg, 0)
    aligned = medium_metrics(signal_openness_field(cfg, 0), movement)
    opposite_cfg = replace(
        cfg,
        environment=replace(
            cfg.environment,
            signal_openness_phase_offset=(
                cfg.environment.signal_openness_phase_offset + np.pi
            ),
        ),
    )
    opposite = medium_metrics(signal_openness_field(opposite_cfg, 0), movement)
    assert aligned["movement_signal_correlation"] > 0.95
    assert opposite["movement_signal_correlation"] < -0.45


def test_independent_signal_diffusion_reads_openness_not_terrain() -> None:
    field = np.zeros((1, 3, 3), dtype=np.float32)
    field[0, 1, 1] = 1.0
    source = np.zeros_like(field)
    terrain = np.ones((3, 3), dtype=np.float32)
    open_medium = np.ones((3, 3), dtype=np.float32)
    blocked_medium = np.zeros((3, 3), dtype=np.float32)
    open_result = propagate_signal_field(
        field,
        source,
        decay=0.0,
        diffusion=0.4,
        schema=OPENNESS_SIGNAL_SCHEMA,
        terrain=terrain,
        signal_openness=open_medium,
        medium_conductance_fraction=1.0,
        xp=np,
    )
    blocked_result = propagate_signal_field(
        field,
        source,
        decay=0.0,
        diffusion=0.4,
        schema=OPENNESS_SIGNAL_SCHEMA,
        terrain=np.zeros_like(terrain),
        signal_openness=blocked_medium,
        medium_conductance_fraction=1.0,
        xp=np,
    )
    assert float(open_result[0, 1, 0]) > float(blocked_result[0, 1, 0])
    assert float(open_result[0, 1, 1]) < float(blocked_result[0, 1, 1])


def test_d1v_workflow_contains_no_direct_conflict_or_gene_steps() -> None:
    workflow = (STUDY / "workflow.toml").read_text(encoding="utf-8")
    assert "gene-persistence" not in workflow
    assert "paired" not in workflow
    assessment = (STUDY / "DIRECT_CONFLICT_ASSESSMENT.md").read_text(
        encoding="utf-8"
    )
    assert "INTERFERE" in assessment
    assert "默认禁用" in assessment


def test_direct_transport_uses_openness_even_when_terrain_is_high(tmp_path: Path) -> None:
    from types import SimpleNamespace

    from se.runtime.signal_transport import direct_message_transport

    output = tmp_path / "config.json"
    prepare(template=STUDY / "frozen/d1u/source_config.json", output=output)
    cfg = load_config(output)
    cfg = replace(
        cfg,
        information=replace(
            cfg.information,
            direct_message_medium_resistance_fraction=1.0,
            direct_message_distance_decay_per_cell=0.0,
        ),
    )
    entities = SimpleNamespace(
        x=np.asarray([0.1, 20.1], dtype=np.float32),
        y=np.asarray([0.1, 0.1], dtype=np.float32),
        alive=np.asarray([True, True]),
    )
    grid_x = cfg.world.grid_x
    grid_y = cfg.world.grid_y
    terrain = np.ones((grid_y, grid_x), dtype=np.float32)
    openness = np.ones((grid_y, grid_x), dtype=np.float32)

    def cell_ids(x: np.ndarray, y: np.ndarray) -> np.ndarray:
        ix = np.floor(x / cfg.world.width * grid_x).astype(np.int64)
        iy = np.floor(y / cfg.world.height * grid_y).astype(np.int64)
        return iy * grid_x + ix

    simulation = SimpleNamespace(
        cfg=cfg,
        entities=entities,
        environment=SimpleNamespace(terrain=terrain, signal_openness=openness),
        spatial=SimpleNamespace(cell_ids=cell_ids),
        gpu_runtime=None,
    )
    factor = direct_message_transport(
        simulation,
        np.asarray([0], dtype=np.int32),
        np.asarray([1], dtype=np.int32),
    )
    assert factor.tolist() == [1.0]
