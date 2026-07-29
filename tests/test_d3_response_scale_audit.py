from __future__ import annotations

import json

import pytest
from pathlib import Path

from se.analysis.d3_response_scale_audit import build_audit


def _branch(name: str, gain: float, cosine: float) -> dict:
    return {
        "branch": name,
        "response_summary": {
            "resource_move_mean_support_gain": gain,
            "resource_move_mean_alignment_cosine": cosine,
            "resource_move_positive_support_gain_fraction": 0.5 + gain,
        },
    }


def _write(path: Path, *, matched: bool) -> None:
    branches = [
        _branch("original-support", 0.03, 0.2),
        _branch("reversed-support", 0.02, 0.1),
        _branch("neutral-support", 0.01, 0.05),
    ]
    if matched:
        branches.append(_branch("reversed-neutral-support", 0.005, 0.02))
    payload = {
        "schema": (
            "d3-processing-response-panel-results-v2"
            if matched
            else "d3-processing-response-panel-results-v1"
        ),
        "panels": [
            {
                "seed": 1,
                "checkpoint_tick": 300,
                "status": "completed",
                (
                    "acute_quartet_analysis_eligible"
                    if matched
                    else "acute_triplet_analysis_eligible"
                ): True,
                "evolutionary_checkpoint_analysis_eligible": False,
                "branches": branches,
            }
        ],
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


def test_scale_audit_uses_seed_level_matched_effects(tmp_path: Path) -> None:
    new = tmp_path / "new.json"
    _write(new, matched=True)
    audit = build_audit([("new", new)])
    scale = audit["scales"][0]
    assert audit["all_eligible_panels_have_matched_orientation_controls"]
    assert audit["recommendation"] == "analyze-seed-level-matched-orientation-effects"
    assert scale["seed_summaries"][0]["original_mean_support_gain_mean"] == pytest.approx(0.02)
    assert scale["seed_summaries"][0]["reversed_mean_support_gain_mean"] == pytest.approx(0.015)
