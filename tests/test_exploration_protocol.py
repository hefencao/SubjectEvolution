from __future__ import annotations

import json
from pathlib import Path

import pytest

from se.analysis.exploration_protocol import (
    build_plan,
    validate_multi_seed_invocation,
)


def test_screen_plan_is_bounded_and_seed_based(tmp_path: Path) -> None:
    output = tmp_path / "screen"
    seeds = list(range(71101, 71109))
    plan = build_plan(
        stage="screen",
        candidate_id="candidate-a",
        config_path=Path("configs/mvp_d3n_exploration_screen.json"),
        seeds=seeds,
        output=output,
        backend="auto",
    )
    assert plan["schema"] == "tiered-exploration-plan-v1"
    assert plan["target_tick"] == 480
    assert plan["initial_entities"] == 1125
    assert plan["selection_claim_allowed"] is False
    assert plan["windows_entities_and_events_are_independent_replicates"] is False


def test_screen_rejects_too_few_independent_seeds(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="at least 8"):
        build_plan(
            stage="screen",
            candidate_id="candidate-a",
            config_path=Path("configs/mvp_d3n_exploration_screen.json"),
            seeds=[1, 2, 3],
            output=tmp_path / "screen",
            backend="auto",
        )


def test_replication_requires_disjoint_screen_seeds(tmp_path: Path) -> None:
    screen = build_plan(
        stage="screen",
        candidate_id="candidate-a",
        config_path=Path("configs/mvp_d3n_exploration_screen.json"),
        seeds=list(range(100, 108)),
        output=tmp_path / "screen",
        backend="auto",
    )
    with pytest.raises(ValueError, match="disjoint"):
        build_plan(
            stage="replication",
            candidate_id="candidate-a",
            config_path=Path("configs/mvp_d3n_exploration_replication.json"),
            seeds=list(range(107, 115)),
            output=tmp_path / "replication",
            backend="auto",
            prior_plan=screen,
        )
    plan = build_plan(
        stage="replication",
        candidate_id="candidate-a",
        config_path=Path("configs/mvp_d3n_exploration_replication.json"),
        seeds=list(range(200, 208)),
        output=tmp_path / "replication",
        backend="auto",
        prior_plan=screen,
    )
    assert plan["prior_plan"]["stage"] == "screen"


def test_confirmation_requires_explicit_authorization(tmp_path: Path) -> None:
    screen = build_plan(
        stage="screen",
        candidate_id="candidate-a",
        config_path=Path("configs/mvp_d3n_exploration_screen.json"),
        seeds=list(range(100, 108)),
        output=tmp_path / "screen",
        backend="auto",
    )
    replication = build_plan(
        stage="replication",
        candidate_id="candidate-a",
        config_path=Path("configs/mvp_d3n_exploration_replication.json"),
        seeds=list(range(200, 208)),
        output=tmp_path / "replication",
        backend="auto",
        prior_plan=screen,
    )
    with pytest.raises(ValueError, match="allow-large-long"):
        build_plan(
            stage="confirmation",
            candidate_id="candidate-a",
            config_path=Path("configs/mvp_d3m_gpu_scale4_memory_stability.json"),
            seeds=list(range(300, 308)),
            output=tmp_path / "confirmation",
            backend="auto",
            prior_plan=replication,
        )
    with pytest.raises(ValueError, match="disjoint"):
        build_plan(
            stage="confirmation",
            candidate_id="candidate-a",
            config_path=Path("configs/mvp_d3m_gpu_scale4_memory_stability.json"),
            seeds=list(range(100, 108)),
            output=tmp_path / "confirmation",
            backend="auto",
            prior_plan=replication,
            allow_large_long_confirmation=True,
        )


def test_multi_seed_invocation_must_match_plan(tmp_path: Path) -> None:
    output = tmp_path / "screen"
    seeds = list(range(71101, 71109))
    plan = build_plan(
        stage="screen",
        candidate_id="candidate-a",
        config_path=Path("configs/mvp_d3n_exploration_screen.json"),
        seeds=seeds,
        output=output,
        backend="auto",
    )
    output.mkdir()
    path = output / "exploration_plan.json"
    path.write_text(json.dumps(plan), encoding="utf-8")
    loaded = validate_multi_seed_invocation(
        path,
        config_path=Path("configs/mvp_d3n_exploration_screen.json"),
        seeds=seeds,
        output=output,
        backend="auto",
        target_tick=480,
    )
    assert loaded["candidate_id"] == "candidate-a"
    with pytest.raises(ValueError, match="seeds"):
        validate_multi_seed_invocation(
            path,
            config_path=Path("configs/mvp_d3n_exploration_screen.json"),
            seeds=list(range(71102, 71110)),
            output=output,
            backend="auto",
            target_tick=480,
        )


def test_protocol_audit_records_tiered_exploration_boundary() -> None:
    from se.analysis.protocol_audit import build_protocol_audit

    audit = build_protocol_audit("configs/mvp_d3n_exploration_screen.json")
    protocol = audit["tiered_exploration_protocol"]
    assert protocol["large_long_run_required_for_exploration"] is False
    assert protocol["large_long_run_reserved_for_confirmation"] is True
    assert protocol["default_stages"]["screen"]["minimum_seeds"] == 8
    assert protocol["source_checkpoint"]["demographic_turnover_required_for_acute_panel"] is False
    assert protocol["source_checkpoint"]["free_run_endpoint_is_candidate_effect"] is False
    assert protocol["paired_plan_schema"] == "tiered-paired-exploration-plan-v2"
    assert protocol["candidate_ledger_schema"] == "paired-exploration-candidate-ledger-v3"
