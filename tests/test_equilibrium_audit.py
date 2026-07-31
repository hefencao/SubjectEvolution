from __future__ import annotations

import json
from pathlib import Path

from se.analysis import equilibrium_audit


def _audit(*, alive: int = 128, final_multiple: float = 1.0) -> dict:
    return {
        "initial_population": 128,
        "final_population": {
            "tick": 600,
            "alive": alive,
            "alive_fraction_to_initial": final_multiple,
            "cumulative_births_per_initial": 1.4,
            "descendant_alive_fraction": 0.74,
            "mean_generation": 1.1,
            "max_generation": 3,
            "effective_lineages": 25.0,
            "largest_lineage_fraction": 0.10,
            "canonical_diversity_ratio_to_initial": 0.97,
            "policy_diversity_ratio_to_initial": 0.95,
            "turnover_checks": {"a": True, "b": True, "c": True},
        },
        "post_bottleneck_regime": {
            "settled_window_count_required": 3,
            "settled_window_count_available": 3,
            "settled_window_start_tick": 540,
            "settled_alive_cv": 0.01,
            "settled_maximum_abs_net_growth_fraction": 0.04,
            "settled_alive_slope_fraction_per_window": 0.04,
            "settled_span_change_fraction": 0.08,
            "active_rebound": True,
            "active_decline": False,
        },
    }


def _write_run(path: Path, alive: list[int], *, longest_period: int = 431) -> None:
    path.mkdir(parents=True)
    config = {
        "world": {"initial_entities": 128},
        "environment": {
            "season_period": 240,
            "resource_cycle_periods": [173, 257, 349, longest_period],
            "oxygen_period": 311,
            "wear_period": 419,
        },
    }
    (path / "resolved_config.json").write_text(json.dumps(config), encoding="utf-8")
    rows = [
        {"tick": 30 * (index + 1), "alive": value}
        for index, value in enumerate(alive)
    ]
    (path / "evolution_progress.jsonl").write_text(
        "".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8"
    )


def test_equilibrium_audit_uses_full_environment_cycle_not_three_window_phase(monkeypatch, tmp_path: Path) -> None:
    root = tmp_path / "runs"
    # Last three windows rise, but the full 450-tick window is bounded and has a
    # normalized slope below 0.02 per 30-tick sample.
    alive = [128, 126, 124, 123, 122, 124, 127, 129, 127, 132, 133, 131, 136, 144, 148, 154, 156, 165]
    _write_run(root / "seed_1", alive)
    monkeypatch.setattr(equilibrium_audit, "audit_run", lambda *args, **kwargs: _audit(alive=165, final_multiple=165 / 128))

    report = equilibrium_audit.build_report(root, required_seed_count=1)

    assert report["ready"] is True
    seed = report["seeds"][0]
    assert seed["short_window_advisory"]["active_rebound"] is True
    assert seed["cycle_aware_regime"]["assessment_span_ticks"] >= 431
    assert seed["cycle_aware_regime"]["checks"]["cycle_trend_bounded"] is True
    assert report["authorization"]["selection_claim_authorized"] is False
    assert report["authorization"]["gene_specific_adjustment_authorized"] is False


def test_equilibrium_audit_rejects_insufficient_cycle_coverage(monkeypatch, tmp_path: Path) -> None:
    root = tmp_path / "runs"
    _write_run(root / "seed_1", [128, 129, 130, 131, 132])
    monkeypatch.setattr(equilibrium_audit, "audit_run", lambda *args, **kwargs: _audit())

    report = equilibrium_audit.build_report(root, required_seed_count=1)

    assert report["ready"] is False
    assert report["seeds"][0]["cycle_aware_regime"]["checks"]["cycle_coverage"] is False


def test_equilibrium_audit_rejects_cycle_scale_expansion(monkeypatch, tmp_path: Path) -> None:
    root = tmp_path / "runs"
    _write_run(root / "seed_1", list(range(300, 316)))
    monkeypatch.setattr(equilibrium_audit, "audit_run", lambda *args, **kwargs: _audit(alive=315, final_multiple=315 / 128))

    report = equilibrium_audit.build_report(root, required_seed_count=1)

    assert report["ready"] is False
    assert report["seeds"][0]["cycle_aware_regime"]["checks"]["maximum_population_bounded"] is False


def test_equilibrium_audit_requires_exact_declared_seed_count(monkeypatch, tmp_path: Path) -> None:
    root = tmp_path / "runs"
    for seed in (1, 2):
        _write_run(root / f"seed_{seed}", [128] * 16)
    monkeypatch.setattr(equilibrium_audit, "audit_run", lambda *args, **kwargs: _audit())

    report = equilibrium_audit.build_report(root, required_seed_count=1)

    assert report["ready"] is False
    assert report["exact_seed_count"] is False
