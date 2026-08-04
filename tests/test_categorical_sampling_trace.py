from __future__ import annotations

from dataclasses import replace
import json
from pathlib import Path

import numpy as np

from se.cfg import load_config
from se.checkpointing import read_checkpoint_bundle
from se.policy import Action
from se.random_api import (
    RandomContext,
    Stream,
    categorical_from_logits,
    categorical_from_logits_with_trace,
)
from se.runtime.sim import Simulation


def test_trace_uses_exact_ordinary_categorical_kernel() -> None:
    ids = np.asarray([11, 12, 13], dtype=np.uint64)
    logits = np.asarray(
        [[0.1, -0.4, 0.3], [2.0, 1.0, -3.0], [-1.0, -2.0, 4.0]],
        dtype=np.float32,
    )
    mask = np.asarray(
        [[True, False, True], [True, True, False], [False, True, True]],
        dtype=bool,
    )
    ctx = RandomContext(19, 7, phase=50, stream=Stream.POLICY_ACTION)
    ordinary = categorical_from_logits(ctx, ids, logits, 0.75, mask=mask)
    traced = categorical_from_logits_with_trace(ctx, ids, logits, 0.75, mask=mask)
    for left, right in zip(ordinary, traced[:3], strict=True):
        assert np.array_equal(left, right)
    action, probability, _, trace = traced
    assert np.array_equal(
        action,
        (trace.cumulative_probabilities < trace.uniform_draw[:, None])
        .sum(axis=1)
        .astype(np.int16),
    )
    assert np.array_equal(
        probability,
        trace.probabilities[np.arange(ids.size), action].astype(np.float32),
    )
    assert np.all(trace.uniform_draw >= trace.cdf_lower)
    assert np.all(trace.uniform_draw < trace.cdf_upper)
    assert np.all(trace.probabilities[~mask] == 0.0)


def _small_config():
    base = load_config("configs/mvp_small.json")
    return replace(
        base,
        run=replace(
            base.run,
            ticks=3,
            metrics_period=3,
            checkpoint_period=100,
            full_checkpoint_enabled=False,
        ),
        world=replace(base.world, initial_entities=16, max_entities=32),
    )


def _close(simulation: Simulation) -> None:
    simulation.metrics.close()
    simulation.evolution_progress.close()
    simulation.knowledge.close()
    if simulation._categorical_sampling_trace_writer is not None:
        simulation._categorical_sampling_trace_summary = (
            simulation._categorical_sampling_trace_writer.close()
        )


def test_trace_is_semantically_neutral_and_reconstructs_events(tmp_path: Path) -> None:
    cfg = _small_config()
    baseline = Simulation(_small_config(), tmp_path / "baseline", backend="cpu")
    traced = Simulation(_small_config(), tmp_path / "traced", backend="cpu")
    traced.enable_categorical_sampling_trace(
        metadata={
            "branch_id": "neutrality-audit",
            "branch_role": "observational-copy",
            "source_checkpoint_state_sha256": "not-applicable-fresh-run",
        }
    )
    try:
        action_rows: list[np.ndarray] = []
        for _ in range(3):
            baseline.step()
            traced.step()
            assert baseline.last_policy_decision is not None
            assert traced.last_policy_decision is not None
            assert np.array_equal(
                baseline.last_policy_decision.action,
                traced.last_policy_decision.action,
            )
            action_rows.append(traced.last_policy_decision.action.copy())
        baseline_checkpoint = baseline.save_full_checkpoint(
            tmp_path / "baseline.sechk"
        )
        traced_checkpoint = traced.save_full_checkpoint(tmp_path / "traced.sechk")
        baseline_meta, _ = read_checkpoint_bundle(baseline_checkpoint)
        traced_meta, _ = read_checkpoint_bundle(traced_checkpoint)
        assert baseline_meta["config_sha256"] == traced_meta["config_sha256"]
        assert baseline_meta["state_sha256"] == traced_meta["state_sha256"]
    finally:
        _close(baseline)
        _close(traced)

    manifest = json.loads(
        (tmp_path / "traced" / "categorical_sampling_trace_manifest.json").read_text(
            encoding="utf-8"
        )
    )
    lines = [
        json.loads(line)
        for line in (tmp_path / "traced" / "categorical_sampling_trace.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
    ]
    header, events = lines[0], lines[1:]
    assert header["record_type"] == "header"
    assert header["action_order"] == [action.name for action in Action]
    assert manifest["event_count"] == len(events) == sum(row.size for row in action_rows)
    assert manifest["metadata"]["branch_id"] == "neutrality-audit"
    for event in events:
        cdf = np.asarray(event["cumulative_probabilities"], dtype=np.float64)
        draw = float(event["uniform_draw"])
        reconstructed = int(np.count_nonzero(cdf < draw))
        assert reconstructed == event["action_id"]
        assert event["selected_cdf_lower"] <= draw < event["selected_cdf_upper"]
        assert event["random_context"]["stream"] == int(Stream.POLICY_ACTION)


def test_integrity_audit_covers_fresh_and_paired_runs(tmp_path: Path) -> None:
    from se.analysis.categorical_sampling_trace_integrity import (
        verify_categorical_sampling_trace,
    )

    result = verify_categorical_sampling_trace(tmp_path / "integrity")
    assert result["passed"] is True
    assert result["fresh_run"]["checkpoint_state_sha256_equal"] is True
    assert result["paired_run"]["all_branches_semantically_neutral"] is True
    assert result["contract"]["trace_changes_random_stream"] is False
    assert result["contract"]["scientific_conclusion_authorized"] is False


def test_trace_decision_protocol_preserves_scientific_boundary() -> None:
    protocol = json.loads(
        Path("protocols/decisions/categorical_sampling_trace_v1.json").read_text(
            encoding="utf-8"
        )
    )
    assert protocol["task_type"] == "ENGINEERING"
    assert protocol["runtime_contract"]["ordinary_and_traced_sampling_share_one_kernel"] is True
    assert protocol["runtime_contract"]["trace_payload_removed_from_checkpoint_and_clone_state"] is True
    assert protocol["scientific_boundary"]["stage3c40_must_be_read_only"] is True
    assert protocol["scientific_boundary"]["scientific_conclusion_from_instrumentation_alone"] is False
