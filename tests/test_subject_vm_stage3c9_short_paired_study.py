from __future__ import annotations

import json
from pathlib import Path

from se.cfg import load_config
from se.experiments.subject_vm_short_paired_study import (
    BOOTSTRAP_GRAPH_PROFILE_SCHEMA,
    SHORT_PAIRED_STUDY_SCHEMA,
    ShortPairedStudyParameters,
    bootstrap_profile,
    prime_fixed_bootstrap_graph,
    run_short_paired_study,
)
from se.runtime.sim import Simulation


def test_fixed_bootstrap_profile_is_explicitly_not_evolved() -> None:
    profile = bootstrap_profile()
    assert profile["schema"] == BOOTSTRAP_GRAPH_PROFILE_SCHEMA
    assert profile["evolved_topology"] is False
    assert profile["universal_attention_claim"] is False
    assert profile["permanent_retention_authorized"] is False
    assert profile["reward"] is None


def test_prime_fixed_bootstrap_graph_preserves_quiescent_ledgers(
    tmp_path: Path,
) -> None:
    cfg = load_config("configs/mvp_short_subject_vm_stage3c8_paired_study.json")
    simulation = Simulation(cfg, tmp_path / "source", backend="cpu")
    lineage = prime_fixed_bootstrap_graph(simulation, bootstrap_subjects=4)
    storage = simulation.subject_vm.storage
    assert storage is not None
    assert int(storage.node_expressed.sum()) == 32
    assert int(storage.edge_expressed.sum()) == 4
    assert lineage["primed_subject_count"] == 4
    assert lineage["evolved_topology"] is False
    assert simulation.subject_vm.trace_storage is not None
    assert not simulation.subject_vm.trace_storage.event_valid.any()
    assert simulation.subject_vm.live_write_ledger is not None
    assert not simulation.subject_vm.live_write_ledger.entry_valid.any()
    simulation.metrics.close()
    simulation.evolution_progress.close()
    simulation.knowledge.close()


def test_short_paired_study_generates_complete_no_retention_evidence(
    tmp_path: Path,
) -> None:
    report = run_short_paired_study(
        "configs/mvp_short_subject_vm_stage3c8_paired_study.json",
        parameters=ShortPairedStudyParameters(
            seeds=(12301, 12302, 12303),
            source_ticks=2,
            horizon_ticks=5,
            bootstrap_subjects=8,
        ),
        output_dir=tmp_path / "study",
    )
    assert report["schema"] == SHORT_PAIRED_STUDY_SCHEMA
    summary = report["engineering_summary"]
    assert summary["independent_source_pair_count"] == 3
    assert summary["total_paired_window_count"] > 0
    assert summary["pooled_pairing_coverage"] >= 0.8
    assert summary["rollback_failure_count"] == 0
    assert summary["stage3c7_engineering_screen_passed"] is True
    assert summary["stage3c8_report_generated"] is True
    assert report["fixed_bootstrap_is_evolved_result"] is False
    assert report["causal_effect_authorized"] is False
    assert report["permanent_parameter_retention_authorized"] is False
    for seed in report["seeds"]:
        assert seed["paired_window_count"] > 0
        assert seed["unpaired_guarded_live_count"] == 0
        assert seed["unpaired_read_only_control_count"] == 0
        export = json.loads(Path(seed["export"]).read_text(encoding="utf-8"))
        assert Path(seed["guarded_live_checkpoint"]).is_file()
        assert Path(seed["read_only_control_checkpoint"]).is_file()
        assert export["scalar_score"] is False
