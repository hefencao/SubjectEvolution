from __future__ import annotations

import json
from pathlib import Path

from se.analysis.exploration_readiness import build_audit, render_markdown


def _run(
    label: str,
    *,
    initial: int = 1125,
    alive: int = 150,
    classification: str = "post-bottleneck-active-decline",
    energy_fraction: float = 1.0,
) -> dict:
    return {
        "label": label,
        "summary_tick": 480,
        "initial_population": initial,
        "final_population": {
            "tick": 480,
            "alive": alive,
            "alive_fraction_to_initial": alive / initial,
            "descendant_alive_fraction": 0.1,
            "effective_successful_parents_window": 5.0,
            "largest_parent_contribution_fraction_window": 0.2,
            "effective_lineages": 120.0,
            "largest_lineage_fraction": 0.02,
            "strategy_effective_dimensions": 58.0,
        },
        "death_causes": {"energy_depleted_fraction": energy_fraction},
        "post_bottleneck_regime": {
            "settled_population_supported": False,
            "source_ready_for_future_independent_runs": False,
            "classification": classification,
        },
    }


def test_short_declining_runs_can_support_paired_sources_without_selection_claims() -> None:
    selection = {
        "schema": "demographic-selection-validity-audit-v3",
        "runs": [_run(f"seed_{index}", alive=138 + index * 3) for index in range(8)],
    }
    report = build_audit(selection)
    diagnosis = report["sample_diagnosis"]
    assert diagnosis["all_runs_support_fixed_checkpoint_paired_panel"] is True
    assert diagnosis["independent_seed_count_meets_confirmation_floor"] is True
    assert diagnosis["startup_transient"]["common_startup_transient_supported"] is True
    assert diagnosis["free_run_endpoint_is_candidate_effect_measurement"] is False
    assert report["recommendation"] == (
        "reuse-fixed-checkpoints-for-paired-acute-screen-do-not-promote-free-run-endpoints"
    )


def test_acute_source_threshold_scales_with_initial_population() -> None:
    report = build_audit(
        {
            "schema": "demographic-selection-validity-audit-v3",
            "runs": [_run("small", initial=500, alive=64)],
        }
    )
    run = report["runs"][0]
    assert run["required_acute_alive"] == 64
    assert run["acute_paired_source_support"] is True
    assert run["long_horizon_selection_support"] is False


def test_readiness_markdown_keeps_checkpoint_pairing_boundary() -> None:
    report = build_audit(
        {
            "schema": "demographic-selection-validity-audit-v3",
            "runs": [_run(f"seed_{index}") for index in range(8)],
        }
    )
    text = render_markdown(report)
    assert "acute paired source checkpoints: `8`" in text
    assert "same full checkpoint" in text
    assert "free-run endpoint is a candidate-effect measurement: `False`" in text


def test_current_documented_audit_is_machine_readable() -> None:
    path = Path("docs/v0.72/D3N_SUPPLIED_SCREEN_AUDIT.json")
    if not path.exists():
        return
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["schema"] == "exploration-readiness-audit-v2"
    assert payload["sample_diagnosis"]["all_runs_support_fixed_checkpoint_paired_panel"] is True
