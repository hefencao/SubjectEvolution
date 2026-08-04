from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from se.analysis.subject_vm_thought_event_t3_recall import assess
from se.cfg import load_config
from se.experiments.subject_vm_short_paired_study import prime_fixed_bootstrap_graph
from se.experiments.subject_vm_thought_event_t3_recall import (
    ThoughtEventT3Parameters,
    _run_config,
    run_thought_event_t3_study,
)
from se.runtime.sim import Simulation


def test_t3_base_config_keeps_recall_disabled_until_arm_declaration() -> None:
    cfg = load_config("configs/mvp_short_subject_vm_thought_event_t3_recall.json")
    assert cfg.subject_vm.thought_event_enabled
    assert not cfg.subject_vm.thought_event_recall_enabled
    assert cfg.subject_vm.thought_event.capacity_per_subject == 16
    assert cfg.subject_vm.thought_event.retention_ticks == 8


def test_t3_runtime_selects_latest_strict_prior_and_checkpoint_clones(tmp_path: Path) -> None:
    parameters = ThoughtEventT3Parameters(seeds=(12601, 12602, 12603), backend="cpu")
    base = load_config("configs/mvp_short_subject_vm_thought_event_t3_recall.json")
    cfg = _run_config(
        base,
        seed=12601,
        parameters=parameters,
        content_mode="identity",
    )
    simulation = Simulation(cfg, tmp_path / "run", backend="cpu")
    for _ in range(parameters.source_ticks):
        simulation.step()
    lineage = prime_fixed_bootstrap_graph(
        simulation,
        bootstrap_subjects=parameters.bootstrap_subjects,
        target_family="edge_forward_gate",
        edge_carrier_enabled=True,
        readout_input_port=11,
        second_readout_input_port=7,
        recall_ingress_node=9,
        recall_token_port=30,
        recall_gate=0.25,
    )
    for _ in range(3):
        simulation.step()
    runtime = simulation.subject_vm
    arena = runtime.thought_event_arena
    assert arena is not None
    subject_ids = np.asarray(lineage["primed_subject_ids"], dtype=np.uint64)
    rows = np.flatnonzero(
        simulation.entities.alive
        & np.isin(simulation.entities.primary_subject_id, subject_ids)
    )
    assert runtime.thought_event_recall_accounting.selected_events == 32
    assert runtime.thought_event_accounting.parent_links == 32
    for row in rows.tolist():
        slot = arena.latest_slot(row)
        assert slot is not None
        assert arena.parent_count[row, slot] == 1
        parent_id = arena.parent_event_id[row, slot, 0]
        matches = np.flatnonzero(
            arena.event_valid[row] & (arena.event_id[row] == parent_id)
        )
        assert matches.size == 1
        parent_slot = int(matches[0])
        assert arena.event_tick[row, parent_slot] == arena.event_tick[row, slot] - 1
        assert arena.parent_weight[row, slot, 0] == np.float32(0.25)

    snapshot = runtime.snapshot_state()
    assert snapshot is not None
    cloned = runtime.clone()
    assert cloned.thought_event_arena is not None
    np.testing.assert_array_equal(
        cloned.thought_event_arena.event_id, arena.event_id
    )
    assert (
        cloned.thought_event_recall_accounting.selected_events
        == runtime.thought_event_recall_accounting.selected_events
    )


def test_t3_three_seed_smoke_reconstructs_ingress_and_equal_cost_controls(
    tmp_path: Path,
) -> None:
    study_root = tmp_path / "study"
    report = run_thought_event_t3_study(
        "configs/mvp_short_subject_vm_thought_event_t3_recall.json",
        output_dir=study_root,
        overwrite=True,
        parameters=ThoughtEventT3Parameters(
            seeds=(12601, 12602, 12603), backend="cpu"
        ),
    )
    assert report["single_role_neutral_read_path"] is True
    assert report["same_tick_recall_allowed"] is False
    assert all(
        all(all(fields.values()) for fields in item["identity_against_no_recall"].values())
        for item in report["cross_arm_identity"]
    )
    result = assess(
        study_root / "study_report.json",
        output=tmp_path / "assessment.json",
        summary_output=tmp_path / "summary.md",
    )
    assert result["passed"] is True
    assert result["status"] == "mechanism-smoke-passed-single-latest-prior-low-rank-recall"
    assert result["formal_support"]["parent_links_per_enabled_arm_per_seed"] == 144
    assert (
        result["mechanism_contract"][
            "graph_ingress_reconstruction_max_abs_residual"
        ]
        <= 1e-6
    )
    assert result["mechanism_contract"]["multi_head_enabled"] is False
    assert "formed chain of thought" in result["forbidden_claims"]


def test_t3_formal_fixture_freezes_nine_seed_mechanism_boundary() -> None:
    fixture_path = Path("tests/fixtures/thought_event_t3_recall.json")
    payload = json.loads(fixture_path.read_text(encoding="utf-8"))
    assert payload["design"]["seeds"] == list(range(12601, 12610))
    assert payload["status"] == "mechanism-smoke-passed-single-latest-prior-low-rank-recall"
    assert payload["mechanism_contract"]["single_role_neutral_latest_prior_path"]
    assert payload["mechanism_contract"]["real_parent_dag_recorded"]
    assert payload["mechanism_contract"]["zero_content_equal_cost_control_exact"]
    assert payload["mechanism_contract"]["action_event_semantics_unchanged"]
    assert payload["mechanism_contract"]["multi_head_enabled"] is False
    assert payload["qualification"]["thought_chain_claim_authorized"] is False
    assert payload["qualification"]["t4_audit_authorized"] is True
