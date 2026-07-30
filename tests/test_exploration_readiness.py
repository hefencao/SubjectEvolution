from __future__ import annotations

import json
from pathlib import Path

from se.analysis.exploration_readiness import build_audit, render_markdown


def _run(label: str, *, source_ready: bool = False) -> dict:
    return {
        "label": label,
        "summary_tick": 5000,
        "final_population": {
            "tick": 5000,
            "alive": 24000,
            "descendant_alive_fraction": 1.0,
            "effective_successful_parents_window": 2200.0,
            "largest_parent_contribution_fraction_window": 0.002,
            "effective_lineages": 25.0,
            "strategy_effective_dimensions": 14.0,
        },
        "post_bottleneck_regime": {
            "settled_population_supported": True,
            "source_ready_for_future_independent_runs": source_ready,
            "classification": "post-bottleneck-rebound-insufficient-source-readiness",
        },
    }


def test_large_runs_can_have_within_run_support_without_confirmation_support() -> None:
    selection = {
        "schema": "demographic-selection-validity-audit-v3",
        "runs": [_run("a"), _run("b"), _run("c")],
    }
    report = build_audit(selection)
    diagnosis = report["sample_diagnosis"]
    assert diagnosis["within_run_observational_support"] is True
    assert diagnosis["independent_seed_count"] == 3
    assert diagnosis["independent_seed_confirmation_support"] is False
    assert diagnosis["sample_issue"] is True
    assert report["exploration_protocol"]["large_long_run_required_for_exploration"] is False
    assert report["recommendation"] == (
        "use-tiered-small-panel-exploration-add-independent-seeds-before-confirmation"
    )


def test_readiness_markdown_keeps_seed_as_independent_unit() -> None:
    report = build_audit(
        {
            "schema": "demographic-selection-validity-audit-v3",
            "runs": [_run("seed_1"), _run("seed_2"), _run("seed_3")],
        }
    )
    text = render_markdown(report)
    assert "independent seed count: `3`" in text
    assert "large long runs: confirmation only" in text
    assert "repeated windows" not in text.lower() or "independent" in text.lower()


def test_current_documented_audit_is_machine_readable() -> None:
    path = Path("docs/v0.71/D3M_SAMPLE_ADEQUACY_AUDIT.json")
    if not path.exists():
        return
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["schema"] == "exploration-readiness-audit-v1"
    assert payload["sample_diagnosis"]["within_run_observational_support"] is True
