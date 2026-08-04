from __future__ import annotations

from dataclasses import replace
import json
from pathlib import Path

import numpy as np

from se.cfg import load_config
from se.checkpointing import read_checkpoint_bundle
from se.experiments.subject_vm_short_paired_study import prime_fixed_bootstrap_graph
from se.runtime.sim import Simulation


def _config():
    cfg = load_config("configs/mvp_short_subject_vm_stage3c8_paired_study.json")
    return replace(
        cfg,
        run=replace(
            cfg.run,
            ticks=2,
            metrics_period=99,
            checkpoint_period=99,
            checkpoint_ticks=(),
            full_checkpoint_enabled=False,
        ),
        world=replace(cfg.world, initial_entities=16, max_entities=32),
    )


def test_activation_contribution_trace_is_reconstructable_and_neutral(
    tmp_path: Path,
) -> None:
    baseline = Simulation(_config(), tmp_path / "off", backend="cpu")
    traced = Simulation(_config(), tmp_path / "on", backend="cpu")
    baseline_lineage = prime_fixed_bootstrap_graph(
        baseline, bootstrap_subjects=4, target_family="node_output_gate"
    )
    traced_lineage = prime_fixed_bootstrap_graph(
        traced, bootstrap_subjects=4, target_family="node_output_gate"
    )
    assert baseline_lineage == traced_lineage
    selected_subject = int(traced_lineage["primed_subject_ids"][0])
    traced.enable_subject_vm_activation_contribution_trace(
        metadata={"audit_role": "unit-test"}, subject_ids=(selected_subject,)
    )

    baseline.run(until_tick=2)
    traced.run(until_tick=2)

    assert np.array_equal(
        baseline.last_policy_decision.action, traced.last_policy_decision.action
    )
    assert np.array_equal(
        baseline.last_policy_decision.probability,
        traced.last_policy_decision.probability,
    )
    baseline_checkpoint = baseline.save_full_checkpoint(tmp_path / "off.sechk")
    traced_checkpoint = traced.save_full_checkpoint(tmp_path / "on.sechk")
    baseline_meta, _ = read_checkpoint_bundle(baseline_checkpoint)
    traced_meta, _ = read_checkpoint_bundle(traced_checkpoint)
    assert baseline_meta["state_sha256"] == traced_meta["state_sha256"]

    manifest = json.loads(
        (tmp_path / "on/subject_vm_activation_contribution_trace_manifest.json")
        .read_text(encoding="utf-8")
    )
    assert manifest["event_count"] == 2
    assert manifest["node_activation_count"] > 0
    assert manifest["edge_transmission_count"] > 0
    assert manifest["output_contribution_count"] > 0
    assert manifest["semantic_feedback"] is False
    assert manifest["checkpoint_state_member"] is False

    records = [
        json.loads(line)
        for line in (
            tmp_path / "on/subject_vm_activation_contribution_trace.jsonl"
        ).read_text(encoding="utf-8").splitlines()
    ]
    assert records[0]["record_type"] == "header"
    events = records[1:]
    assert {event["subject_id"] for event in events} == {selected_subject}
    for event in events:
        assert event["node_activations"]
        assert event["edge_transmissions"]
        assert event["output_contributions"]
        assert len(event["raw_action_potentials"]) == 8
        assert len(event["action_potentials"]) == 8
        assert event["event_id"] > 0
