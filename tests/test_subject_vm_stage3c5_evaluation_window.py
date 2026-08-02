from __future__ import annotations

from dataclasses import asdict, replace

import numpy as np
import pytest

from se.cfg import load_config
from se.config_identity import strip_inactive_extensions
from se.subject_vm import (
    EVALUATION_MODE_GUARDED_LIVE,
    EVALUATION_MODE_READ_ONLY_CONTROL,
    EVALUATION_STATUS_COMPLETE_CONTROL,
    EVALUATION_STATUS_COMPLETE_LIVE_ROLLED_BACK,
    EVALUATION_STATUS_OBSERVED,
    SUBJECT_VM_ACTIVATION_SCHEMA,
    SUBJECT_VM_ASSOCIATION_SCHEMA,
    SUBJECT_VM_ELIGIBILITY_SCHEMA,
    SUBJECT_VM_EVALUATION_SCHEMA,
    SUBJECT_VM_INPUT_PORT_SCHEMA,
    SUBJECT_VM_LIVE_WRITE_SCHEMA,
    SUBJECT_VM_MODULATION_SCHEMA,
    SUBJECT_VM_OBJECTIVE_EVENT_SCHEMA,
    SUBJECT_VM_OUTPUT_PORT_SCHEMA,
    SUBJECT_VM_REGION_NAMES,
    SUBJECT_VM_STAGE3C4_SCHEMA,
    SUBJECT_VM_STAGE3C5_SCHEMA,
    SUBJECT_VM_TARGET_BINDING_SCHEMA,
    SUBJECT_VM_TRACE_SCHEMA,
    SUBJECT_VM_TRANSACTION_SCHEMA,
    SUBJECT_VM_UPDATE_SAFETY_SCHEMA,
    TARGET_KIND_NODE,
    SubjectVMActivationConfig,
    SubjectVMAssociationConfig,
    SubjectVMConfig,
    SubjectVMEligibilityConfig,
    SubjectVMEvaluationConfig,
    SubjectVMLiveWriteConfig,
    SubjectVMModulationConfig,
    SubjectVMObjectiveEventBatch,
    SubjectVMRegionConfig,
    SubjectVMRuntime,
    SubjectVMTargetBindingConfig,
    SubjectVMTargetCandidateBatch,
    SubjectVMThoughtTokenBatch,
    SubjectVMTraceConfig,
    SubjectVMTransactionConfig,
    SubjectVMUpdateSafetyConfig,
    validate_subject_vm_config,
)

TOKEN_WIDTH = 32


def _cfg(*, live_enabled: bool, stage: str = SUBJECT_VM_STAGE3C5_SCHEMA) -> SubjectVMConfig:
    stage5 = stage == SUBJECT_VM_STAGE3C5_SCHEMA
    return SubjectVMConfig(
        enabled=True,
        schema=stage,
        node_state_width=3,
        regions=tuple(
            SubjectVMRegionConfig(name=name, node_capacity=2, edge_capacity=1, update_period=1)
            for name in SUBJECT_VM_REGION_NAMES
        ),
        activation=SubjectVMActivationConfig(
            schema=SUBJECT_VM_ACTIVATION_SCHEMA,
            input_port_schema=SUBJECT_VM_INPUT_PORT_SCHEMA,
            output_port_schema=SUBJECT_VM_OUTPUT_PORT_SCHEMA,
            activation_clip=8.0,
            output_clip=8.0,
        ),
        trace=SubjectVMTraceConfig(
            schema=SUBJECT_VM_TRACE_SCHEMA,
            event_schema=SUBJECT_VM_OBJECTIVE_EVENT_SCHEMA,
            token_width=TOKEN_WIDTH,
            token_clip=8.0,
            capacity_per_subject=5,
            retention_ticks=5,
        ),
        eligibility=SubjectVMEligibilityConfig(
            schema=SUBJECT_VM_ELIGIBILITY_SCHEMA,
            decay=0.5,
            clip=2.0,
            max_age_ticks=4,
        ),
        association=SubjectVMAssociationConfig(
            schema=SUBJECT_VM_ASSOCIATION_SCHEMA,
            request_token_port=0,
            request_threshold=0.5,
            similarity_threshold=0.8,
            min_delay_ticks=1,
            max_delay_ticks=4,
        ),
        modulation=SubjectVMModulationConfig(
            schema=SUBJECT_VM_MODULATION_SCHEMA,
            request_token_port=1,
            request_threshold=0.5,
            fact_weight_start_port=2,
            target_weight_start_port=23,
            proposal_clip=1.0,
        ),
        target_binding=SubjectVMTargetBindingConfig(
            schema=SUBJECT_VM_TARGET_BINDING_SCHEMA,
            min_abs_eligibility=0.1,
        ),
        update_safety=SubjectVMUpdateSafetyConfig(
            schema=SUBJECT_VM_UPDATE_SAFETY_SCHEMA,
            step_scale=0.5,
            min_abs_delta=0.01,
            family_delta_clip=(0.2,) * 6,
            event_l1_budget=0.3,
            parameter_lower_bounds=(-2.0, -2.0, -2.0, -2.0, -2.0, 0.0),
            parameter_upper_bounds=(2.0,) * 6,
        ),
        transaction=SubjectVMTransactionConfig(
            schema=SUBJECT_VM_TRANSACTION_SCHEMA,
            max_targets_per_event=6,
            base_cost_units=3,
            per_target_cost_units=2,
        ),
        live_write=SubjectVMLiveWriteConfig(
            schema=SUBJECT_VM_LIVE_WRITE_SCHEMA,
            enabled=live_enabled,
            ledger_capacity_per_subject=4,
            rollback_after_ticks=2,
            window_ticks=8,
            max_pending_transactions=2,
            max_applied_targets_per_window=2,
            max_abs_delta_per_window=0.3,
            commit_base_cost_units=5,
            commit_per_target_cost_units=2,
            rollback_base_cost_units=3,
            rollback_per_target_cost_units=1,
        ),
        evaluation=(
            SubjectVMEvaluationConfig(
                schema=SUBJECT_VM_EVALUATION_SCHEMA,
                enabled=True,
                capacity_per_subject=4,
                observation_ticks=1,
                control_horizon_ticks=2,
                fact_clip=8.0,
                registration_cost_units=2,
                per_observation_cost_units=1,
            )
            if stage5
            else SubjectVMEvaluationConfig()
        ),
    )


def _runtime(*, live_enabled: bool, stage: str = SUBJECT_VM_STAGE3C5_SCHEMA) -> SubjectVMRuntime:
    return SubjectVMRuntime.initialize(
        _cfg(live_enabled=live_enabled, stage=stage),
        entity_capacity=1,
        active_rows=np.array([0], dtype=np.int32),
        entity_ids=np.array([11], dtype=np.uint64),
        subject_ids=np.array([101], dtype=np.uint64),
    )


def _candidate(tick: int, *, active: bool) -> SubjectVMTargetCandidateBatch:
    kind = np.zeros((1, 6), dtype=np.uint8)
    index = np.full((1, 6), -1, dtype=np.int32)
    target_id = np.zeros((1, 6), dtype=np.uint32)
    value = np.zeros((1, 6), dtype=np.float32)
    age = np.zeros((1, 6), dtype=np.uint16)
    if active:
        kind[0, 0] = TARGET_KIND_NODE
        index[0, 0] = 0
        target_id[0, 0] = 1
        value[0, 0] = 0.5
        age[0, 0] = 2
    return SubjectVMTargetCandidateBatch(
        tick=tick,
        rows=np.array([0], dtype=np.int32),
        target_kind=kind,
        target_index=index,
        target_id=target_id,
        eligibility_value=value,
        eligibility_age=age,
    )


def _token(*, active: bool) -> np.ndarray:
    token = np.zeros(TOKEN_WIDTH, dtype=np.float32)
    token[31] = 1.0
    if active:
        token[0] = 1.0
        token[1] = 1.0
        token[2] = 1.0
        token[23] = 1.0
    return token


def _batch(*, tick: int, event_id: int, energy_delta: float, success: bool = True):
    return SubjectVMObjectiveEventBatch(
        tick=tick,
        rows=np.array([0], dtype=np.int32),
        event_ids=np.array([event_id], dtype=np.uint64),
        entity_ids=np.array([11], dtype=np.uint64),
        subject_ids=np.array([101], dtype=np.uint64),
        action_ids=np.array([0], dtype=np.int16),
        target_subject_ids=np.array([0], dtype=np.uint64),
        success=np.array([success]),
        failure_reason=np.array([0 if success else 1], dtype=np.uint8),
        sampled_probability=np.array([0.5], dtype=np.float32),
        objective_delta=np.array([[energy_delta] + [0.0] * 11], dtype=np.float32),
        resolution_resource_delta=np.zeros((1, 4), dtype=np.float32),
        resolution_internal_resource_delta=np.zeros((1, 4), dtype=np.float32),
        resolution_energy_cost=np.zeros(1, dtype=np.float32),
    )


def _append(runtime: SubjectVMRuntime, *, tick: int, event_id: int, active: bool) -> None:
    assert runtime.storage is not None
    assert runtime.trace_storage is not None
    runtime.trace_storage.append(
        _batch(tick=tick, event_id=event_id, energy_delta=3.0 if active else 0.0),
        SubjectVMThoughtTokenBatch(
            tick=tick,
            rows=np.array([0], dtype=np.int32),
            emitted=np.array([True]),
            tokens=_token(active=active).reshape(1, -1),
            action_potentials=np.zeros((1, 8), dtype=np.float32),
        ),
        owner_entity_ids=runtime.storage.owner_entity_id,
        owner_subject_ids=runtime.storage.owner_subject_id,
        accounting=runtime.trace_accounting,
        target_candidates=_candidate(tick, active=active),
        graph_storage=runtime.storage,
        live_write_ledger=runtime.live_write_ledger,
        evaluation_ledger=runtime.evaluation_ledger,
    )


def _open_window(runtime: SubjectVMRuntime) -> int:
    assert runtime.storage is not None and runtime.evaluation_ledger is not None
    runtime.storage.node_expressed[0, 0] = True
    runtime.storage.node_id[0, 0] = np.uint32(1)
    runtime.storage.node_bias[0, 0] = np.float32(0.25)
    _append(runtime, tick=0, event_id=700, active=False)
    _append(runtime, tick=2, event_id=702, active=True)
    slots = np.flatnonzero(runtime.evaluation_ledger.entry_valid[0])
    assert slots.size == 1
    return int(slots[0])


def test_stage3c5_requires_score_free_bounded_windows() -> None:
    cfg = _cfg(live_enabled=True)
    validate_subject_vm_config(cfg)
    validate_subject_vm_config(_cfg(live_enabled=False))
    legacy = load_config("configs/mvp_small.json")
    payload = strip_inactive_extensions(
        asdict(replace(legacy, subject_vm=_cfg(live_enabled=True, stage=SUBJECT_VM_STAGE3C4_SCHEMA)))
    )
    assert "evaluation" not in payload["subject_vm"]
    with pytest.raises(ValueError, match="observation_ticks"):
        validate_subject_vm_config(
            replace(cfg, evaluation=replace(cfg.evaluation, observation_ticks=2))
        )
    with pytest.raises(ValueError, match="control_horizon_ticks"):
        validate_subject_vm_config(
            replace(cfg, evaluation=replace(cfg.evaluation, control_horizon_ticks=3))
        )


def test_live_and_control_windows_record_objective_vectors_without_scores() -> None:
    live = _runtime(live_enabled=True)
    control = _runtime(live_enabled=False)
    live_slot = _open_window(live)
    control_slot = _open_window(control)
    assert live.evaluation_ledger is not None and control.evaluation_ledger is not None
    assert live.evaluation_ledger.mode[0, live_slot] == EVALUATION_MODE_GUARDED_LIVE
    assert control.evaluation_ledger.mode[0, control_slot] == EVALUATION_MODE_READ_ONLY_CONTROL
    live.evaluation_ledger.observe(_batch(tick=3, event_id=703, energy_delta=-1.5, success=False))
    control.evaluation_ledger.observe(_batch(tick=3, event_id=703, energy_delta=-1.5, success=False))
    assert live.evaluation_ledger.status[0, live_slot] == EVALUATION_STATUS_OBSERVED
    assert np.array_equal(
        live.evaluation_ledger.fact_sum[0, live_slot],
        control.evaluation_ledger.fact_sum[0, control_slot],
    )
    assert live.evaluation_ledger.fact_sum[0, live_slot, 0] == pytest.approx(-1.5)
    assert live.evaluation_ledger.failure_count[0, live_slot] == 1
    assert "score" not in live.evaluation_ledger.snapshot_array_names()


def test_live_window_finalizes_only_after_exact_rollback() -> None:
    runtime = _runtime(live_enabled=True)
    slot = _open_window(runtime)
    assert runtime.storage is not None and runtime.evaluation_ledger is not None
    assert runtime.storage.node_bias[0, 0] == pytest.approx(0.45)
    runtime.evaluation_ledger.observe(_batch(tick=3, event_id=703, energy_delta=1.0))
    runtime.activate(
        rows=np.array([0], dtype=np.int32),
        input_values=np.zeros((1, 16), dtype=np.float32),
        tick=4,
        output_width=8,
    )
    assert runtime.storage.node_bias[0, 0] == pytest.approx(0.25)
    assert (
        runtime.evaluation_ledger.status[0, slot]
        == EVALUATION_STATUS_COMPLETE_LIVE_ROLLED_BACK
    )
    assert runtime.evaluation_ledger.rollback_verified[0, slot]


def test_read_only_window_completes_without_parameter_mutation() -> None:
    runtime = _runtime(live_enabled=False)
    slot = _open_window(runtime)
    assert runtime.storage is not None and runtime.evaluation_ledger is not None
    assert runtime.storage.node_bias[0, 0] == pytest.approx(0.25)
    runtime.evaluation_ledger.observe(_batch(tick=3, event_id=703, energy_delta=1.0))
    runtime.activate(
        rows=np.array([0], dtype=np.int32),
        input_values=np.zeros((1, 16), dtype=np.float32),
        tick=4,
        output_width=8,
    )
    assert runtime.storage.node_bias[0, 0] == pytest.approx(0.25)
    assert runtime.evaluation_ledger.status[0, slot] == EVALUATION_STATUS_COMPLETE_CONTROL
    assert runtime.evaluation_ledger.rollback_verified[0, slot]


def test_evaluation_checkpoint_clone_and_v0118_upgrade() -> None:
    runtime = _runtime(live_enabled=True)
    _open_window(runtime)
    assert runtime.evaluation_ledger is not None
    runtime.evaluation_ledger.observe(_batch(tick=3, event_id=703, energy_delta=0.75))
    cloned = runtime.clone()
    assert cloned.evaluation_ledger is not None
    for name in runtime.evaluation_ledger.snapshot_array_names():
        assert np.array_equal(
            getattr(cloned.evaluation_ledger, name),
            getattr(runtime.evaluation_ledger, name),
        )
    payload = runtime.snapshot_state()
    restored = SubjectVMRuntime.restore(
        runtime.cfg,
        entity_capacity=1,
        payload=payload,
        alive=np.array([True]),
        entity_ids=np.array([11], dtype=np.uint64),
        subject_ids=np.array([101], dtype=np.uint64),
    )
    assert restored.evaluation_ledger is not None
    for name in runtime.evaluation_ledger.snapshot_array_names():
        assert np.array_equal(
            getattr(restored.evaluation_ledger, name),
            getattr(runtime.evaluation_ledger, name),
        )

    old = _runtime(live_enabled=True, stage=SUBJECT_VM_STAGE3C4_SCHEMA)
    old_payload = old.snapshot_state()
    assert old_payload is not None
    old_payload["schema"] = "se-subject-vm-runtime-v10"
    upgraded = SubjectVMRuntime.restore(
        _cfg(live_enabled=True),
        entity_capacity=1,
        payload=old_payload,
        alive=np.array([True]),
        entity_ids=np.array([11], dtype=np.uint64),
        subject_ids=np.array([101], dtype=np.uint64),
    )
    assert upgraded.restore_mode == "compatibility-empty-evaluation-ledger-rebuild"
    assert upgraded.evaluation_ledger is not None
    assert not np.any(upgraded.evaluation_ledger.entry_valid)


def test_runtime_observes_active_window_without_a_new_thought_token() -> None:
    runtime = _runtime(live_enabled=False)
    slot = _open_window(runtime)
    assert runtime.evaluation_ledger is not None
    runtime.commit_objective_events(
        _batch(tick=3, event_id=703, energy_delta=2.25, success=True)
    )
    assert runtime.evaluation_ledger.observation_count[0, slot] == 1
    assert runtime.evaluation_ledger.fact_sum[0, slot, 0] == pytest.approx(2.25)


def test_window_finalizes_at_horizon_even_when_no_event_occurs_at_end_tick() -> None:
    runtime = _runtime(live_enabled=False)
    slot = _open_window(runtime)
    assert runtime.evaluation_ledger is not None
    runtime.activate(
        rows=np.array([0], dtype=np.int32),
        input_values=np.zeros((1, 16), dtype=np.float32),
        tick=4,
        output_width=8,
    )
    assert runtime.evaluation_ledger.observation_count[0, slot] == 0
    assert runtime.evaluation_ledger.status[0, slot] == EVALUATION_STATUS_COMPLETE_CONTROL
    assert runtime.evaluation_ledger.rollback_verified[0, slot]
