from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from se.analysis.subject_vm_paired_evaluation import build_plan
from se.analysis.subject_vm_stage3c32_alignment_intervention import (
    _coordinate_summary,
    _window_source_summary,
)
from se.cfg import load_config
from se.runtime.sim import Simulation
from se.subject_vm.trace import (
    ASSOCIATION_ALIGNMENT_CYCLIC_DONOR,
    ASSOCIATION_ALIGNMENT_IDENTITY,
    ASSOCIATION_ALIGNMENT_NATIVE,
    TRACE_STORAGE_SCHEMA_V9,
    SubjectVMObjectiveEventBatch,
    SubjectVMThoughtTokenBatch,
    SubjectVMTraceAccounting,
    SubjectVMTraceStorage,
)


def _batches() -> tuple[SubjectVMObjectiveEventBatch, SubjectVMThoughtTokenBatch]:
    rows = np.array([0, 1, 2], dtype=np.int32)
    tokens = np.zeros((3, 32), dtype=np.float32)
    tokens[:, 31] = 1.0
    tokens[:, 30] = np.array([1.0, 2.0, 3.0], dtype=np.float32)
    token_batch = SubjectVMThoughtTokenBatch(
        tick=5,
        rows=rows,
        emitted=np.ones(3, dtype=bool),
        tokens=tokens,
        action_potentials=np.zeros((3, 8), dtype=np.float32),
    )
    event_batch = SubjectVMObjectiveEventBatch(
        tick=5,
        rows=rows,
        event_ids=np.array([101, 102, 103], dtype=np.uint64),
        entity_ids=np.array([30, 10, 20], dtype=np.uint64),
        subject_ids=np.array([300, 100, 200], dtype=np.uint64),
        action_ids=np.zeros(3, dtype=np.int16),
        target_subject_ids=np.zeros(3, dtype=np.uint64),
        success=np.zeros(3, dtype=bool),
        failure_reason=np.zeros(3, dtype=np.uint8),
        sampled_probability=np.zeros(3, dtype=np.float32),
        objective_delta=np.zeros((3, 12), dtype=np.float32),
        resolution_resource_delta=np.zeros((3, 4), dtype=np.float32),
        resolution_internal_resource_delta=np.zeros((3, 4), dtype=np.float32),
        resolution_energy_cost=np.zeros(3, dtype=np.float32),
    )
    return event_batch, token_batch


def test_explicit_alignment_modes_share_path_and_preserve_tickwise_marginal() -> None:
    cfg = load_config("configs/mvp_short_subject_vm_stage3c8_paired_study.json").subject_vm
    batch, tokens = _batches()

    identity = SubjectVMTraceStorage(cfg, entity_capacity=3)
    identity.association_coordinate_alignment_mode = ASSOCIATION_ALIGNMENT_IDENTITY
    identity.association_coordinate_alignment_port = 30
    identity.association_coordinate_alignment_origin_tick = 5
    identity_accounting = SubjectVMTraceAccounting()
    identity_tokens = identity._association_address_tokens(
        batch=batch,
        tokens=tokens,
        emitted=tokens.emitted,
        accounting=identity_accounting,
    )
    assert np.array_equal(identity_tokens[:, 30], tokens.tokens[:, 30])
    assert identity_accounting.association_alignment_assignments == 3
    assert identity_accounting.association_alignment_self_donor_assignments == 3

    cyclic = SubjectVMTraceStorage(cfg, entity_capacity=3)
    cyclic.association_coordinate_alignment_mode = ASSOCIATION_ALIGNMENT_CYCLIC_DONOR
    cyclic.association_coordinate_alignment_port = 30
    cyclic.association_coordinate_alignment_origin_tick = 5
    cyclic_accounting = SubjectVMTraceAccounting()
    cyclic_tokens = cyclic._association_address_tokens(
        batch=batch,
        tokens=tokens,
        emitted=tokens.emitted,
        accounting=cyclic_accounting,
    )
    assert np.array_equal(cyclic_tokens[:, 30], np.array([2.0, 3.0, 1.0]))
    assert np.array_equal(
        np.sort(cyclic_tokens[:, 30]), np.sort(tokens.tokens[:, 30])
    )
    assert cyclic_accounting.association_alignment_assignments == 3
    assert cyclic_accounting.association_alignment_self_donor_assignments == 0
    assert cyclic_accounting.association_alignment_marginal_mismatches == 0


def test_trace_v10_persists_alignment_policy_and_v9_defaults_native() -> None:
    cfg = load_config("configs/mvp_short_subject_vm_stage3c8_paired_study.json").subject_vm
    trace = SubjectVMTraceStorage(cfg, entity_capacity=2)
    trace.association_coordinate_alignment_mode = ASSOCIATION_ALIGNMENT_CYCLIC_DONOR
    trace.association_coordinate_alignment_port = 30
    trace.association_coordinate_alignment_origin_tick = 2
    restored = SubjectVMTraceStorage.from_snapshot(cfg, 2, trace.snapshot_state())
    assert restored.association_coordinate_alignment_mode == ASSOCIATION_ALIGNMENT_CYCLIC_DONOR
    assert restored.association_coordinate_alignment_port == 30
    assert restored.association_coordinate_alignment_origin_tick == 2

    legacy = trace.snapshot_state()
    legacy["schema"] = TRACE_STORAGE_SCHEMA_V9
    legacy.pop("runtime_policies")
    restored_legacy = SubjectVMTraceStorage.from_snapshot(cfg, 2, legacy)
    assert restored_legacy.association_coordinate_alignment_mode == ASSOCIATION_ALIGNMENT_NATIVE
    assert restored_legacy.association_coordinate_alignment_port == -1


def test_paired_plan_binds_complete_alignment_override_to_source_tick(tmp_path: Path) -> None:
    cfg = load_config("configs/mvp_short_subject_vm_stage3c8_paired_study.json")
    simulation = Simulation(cfg, tmp_path / "source_run", backend="cpu")
    source = simulation.save_full_checkpoint(tmp_path / "source.sechk")
    simulation.metrics.close()
    simulation.evolution_progress.close()
    simulation.knowledge.close()

    plan = build_plan(
        source,
        horizon_ticks=3,
        association_coordinate_alignment_mode_override=ASSOCIATION_ALIGNMENT_IDENTITY,
        association_coordinate_alignment_port_override=30,
        association_coordinate_alignment_origin_tick_override=0,
    )
    assert plan["branch_runtime_overrides"] == {
        "subject_vm.association.coordinate_alignment_mode": ASSOCIATION_ALIGNMENT_IDENTITY,
        "subject_vm.association.coordinate_alignment_port": 30,
        "subject_vm.association.coordinate_alignment_origin_tick": 0,
    }
    with pytest.raises(ValueError, match="requires mode, port, and origin"):
        build_plan(
            source,
            horizon_ticks=3,
            association_coordinate_alignment_mode_override=ASSOCIATION_ALIGNMENT_IDENTITY,
        )
    with pytest.raises(ValueError, match="must equal the source checkpoint tick"):
        build_plan(
            source,
            horizon_ticks=3,
            association_coordinate_alignment_mode_override=ASSOCIATION_ALIGNMENT_IDENTITY,
            association_coordinate_alignment_port_override=30,
            association_coordinate_alignment_origin_tick_override=1,
        )


def test_stage3c32_source_balancing_keeps_coordinates_unscalarized() -> None:
    pair = {
        "guarded_live": {"stable_subject_id": 7},
        "read_only_control": {"stable_subject_id": 7},
        "objective_fact_sum_difference_live_minus_control": [1.0] * 21,
        "objective_fact_abs_sum_difference_live_minus_control": [2.0] * 21,
        "observation_count_difference_live_minus_control": 1,
        "success_count_difference_live_minus_control": 0,
        "failure_count_difference_live_minus_control": -1,
    }
    summary = _window_source_summary({"window_evidence": {"pairs": [pair, pair]}})
    assert summary["paired_window_count"] == 2
    assert summary["stable_subject_count"] == 1
    assert np.array_equal(summary["subject_balanced_fact_sum_difference"], np.ones(21))

    reports, positive, negative = _coordinate_summary(
        [np.ones(21), np.ones(21) * 2],
        names=[f"coordinate_{index}" for index in range(21)],
    )
    assert len(reports) == 21
    assert len(positive) == 21
    assert negative == []
