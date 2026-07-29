from __future__ import annotations

import json
from pathlib import Path

import pytest

from se.analysis.protocol_audit import build_protocol_audit
from se.analysis.d3_response_scale_audit import (
    ReplicationRequirements,
    build_audit,
    render_markdown,
)


def _trajectory(gain: float, cosine: float) -> list[dict]:
    return [
        {
            "tick": 0,
            "cumulative": {
                "resource_move_count": 0.0,
                "resource_move_support_gain_sum": 0.0,
                "resource_move_support_gain_positive": 0.0,
                "resource_move_alignment_cosine_sum": 0.0,
                "resource_move_alignment_cosine_count": 0.0,
            },
        },
        {
            "tick": 30,
            "cumulative": {
                "resource_move_count": 10.0,
                "resource_move_support_gain_sum": gain * 10.0,
                "resource_move_support_gain_positive": (0.5 + gain) * 10.0,
                "resource_move_alignment_cosine_sum": cosine * 10.0,
                "resource_move_alignment_cosine_count": 10.0,
            },
        },
    ]


def _branch(name: str, gain: float, cosine: float) -> dict:
    return {
        "branch": name,
        "response_summary": {
            "resource_move_mean_support_gain": gain,
            "resource_move_mean_alignment_cosine": cosine,
            "resource_move_positive_support_gain_fraction": 0.5 + gain,
        },
        "response_trajectory": _trajectory(gain, cosine),
        "interval_ledgers": {
            "external_resource": {"valid": True},
            "external_recycling": {"valid": True},
        },
    }


def _panel(seed: int, checkpoint: int, *, matched: bool, sign: float = 1.0) -> dict:
    branches = [
        _branch("original-support", 0.03 * sign, 0.2 * sign),
        _branch("reversed-support", 0.02 * sign, 0.1 * sign),
        _branch("neutral-support", 0.01 * sign, 0.05 * sign),
    ]
    if matched:
        branches.append(_branch("reversed-neutral-support", 0.005 * sign, 0.02 * sign))
    return {
        "seed": seed,
        "checkpoint_tick": checkpoint,
        "status": "completed",
        (
            "acute_quartet_analysis_eligible"
            if matched
            else "acute_triplet_analysis_eligible"
        ): True,
        "evolutionary_checkpoint_analysis_eligible": False,
        "branches": branches,
    }


def _write(path: Path, *, matched: bool, panels: list[dict] | None = None) -> None:
    payload = {
        "schema": (
            "d3-processing-response-panel-results-v2"
            if matched
            else "d3-processing-response-panel-results-v1"
        ),
        "panels": panels or [_panel(1, 300, matched=matched)],
    }
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_scale_audit_rejects_unmatched_reversed_control(tmp_path: Path) -> None:
    old = tmp_path / "old.json"
    _write(old, matched=False)
    audit = build_audit([("old", old)])
    assert audit["acute_analysis_eligible_panel_count"] == 1
    assert audit["matched_orientation_control_eligible_panel_count"] == 0
    assert audit["all_eligible_panels_have_matched_orientation_controls"] is False
    assert audit["recommendation"] == (
        "rerun-eligible-panels-with-matched-orientation-neutral-controls"
    )


def test_scale_audit_uses_equal_checkpoint_then_equal_seed_weighting(
    tmp_path: Path,
) -> None:
    new = tmp_path / "new.json"
    panels = [
        _panel(1, 300, matched=True, sign=1.0),
        _panel(1, 600, matched=True, sign=-1.0),
        _panel(2, 300, matched=True, sign=1.0),
    ]
    _write(new, matched=True, panels=panels)
    audit = build_audit(
        [("new", new)],
        requirements=ReplicationRequirements(minimum_independent_seeds=2),
    )
    scale = audit["scales"][0]
    seeds = {row["seed"]: row for row in scale["seed_summaries"]}
    assert seeds[1]["original_mean_support_gain_mean"] == pytest.approx(0.0)
    assert seeds[2]["original_mean_support_gain_mean"] == pytest.approx(0.02)
    inference = scale["matched_effect_inference"]
    assert inference["metrics"]["mean_support_gain"]["original"][
        "equal_seed_mean"
    ] == pytest.approx(0.01)
    assert inference["checkpoint_weighting_within_seed"] == "equal-checkpoint-v1"
    assert inference["seed_weighting_within_scale"] == "equal-seed-v1"


def test_scale_audit_reports_window_stability_and_descriptive_sign_flip(
    tmp_path: Path,
) -> None:
    new = tmp_path / "new.json"
    _write(
        new,
        matched=True,
        panels=[
            _panel(1, 300, matched=True),
            _panel(2, 300, matched=True),
            _panel(3, 300, matched=True),
        ],
    )
    audit = build_audit(
        [("new", new)],
        requirements=ReplicationRequirements(minimum_independent_seeds=3),
    )
    scale = audit["scales"][0]
    for seed in scale["seed_summaries"]:
        metric = seed["metrics"]["mean_support_gain"]["original"]
        assert metric["window_count"] == 1
        assert metric["positive_window_fraction"] == 1.0
    sign_flip = scale["matched_effect_inference"]["metrics"]["mean_support_gain"][
        "original"
    ]["exact_sign_flip"]
    assert sign_flip["method"] == "exact-two-sided-seed-sign-flip-v1"
    assert sign_flip["value"] == pytest.approx(0.25)
    assert audit["recommendation"] == (
        "repeat-matched-effect-audit-at-independent-map-scale"
    )


def test_scale_audit_blocks_directionally_inconsistent_effect(tmp_path: Path) -> None:
    new = tmp_path / "new.json"
    panels = []
    for seed in range(1, 4):
        panel = _panel(seed, 300, matched=True)
        # Make reversed active worse than its matched neutral while original stays positive.
        panel["branches"][1] = _branch("reversed-support", -0.02, -0.1)
        panels.append(panel)
    _write(new, matched=True, panels=panels)
    audit = build_audit(
        [("new", new)],
        requirements=ReplicationRequirements(minimum_independent_seeds=3),
    )
    gate = audit["scales"][0]["matched_effect_inference"][
        "directional_replication_gate"
    ]
    assert gate["minimum_independent_seeds_met"]
    assert gate["original_equal_seed_mean_positive"]
    assert not gate["reversed_equal_seed_mean_positive"]
    assert not gate["eligible"]
    assert audit["recommendation"] == (
        "matched-effect-not-directionally-replicated-do-not-add-response-mechanism"
    )


def test_scale_audit_markdown_column_count_is_consistent(tmp_path: Path) -> None:
    new = tmp_path / "new.json"
    _write(new, matched=True)
    markdown = render_markdown(build_audit([("new", new)]))
    table_lines = [line for line in markdown.splitlines() if line.startswith("|")]
    assert table_lines[0].count("|") == table_lines[1].count("|")
    assert table_lines[1].count("|") == table_lines[2].count("|")


def test_protocol_audit_publishes_nested_effect_inference_contract() -> None:
    protocol = build_protocol_audit(
        Path("configs/mvp_short_d3g_spatial_processing_scale1p5_longrun.json")
    )
    section = protocol["functional_module_protocol"][
        "processing_response_scale_audit"
    ]
    assert protocol["schema"] == "structural-measurement-protocol-audit-v31"
    assert section["audit_schema"] == "d3-response-scale-audit-v2"
    assert section["independent_replication_unit"] == "seed-within-scale"
    assert section["checkpoint_weighting_within_seed"] == "equal-checkpoint-v1"
    assert section["seed_weighting_within_scale"] == "equal-seed-v1"
    assert section["exact_sign_flip_descriptive_only"] is True
