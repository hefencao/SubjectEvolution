from __future__ import annotations

from dataclasses import asdict, replace

import numpy as np
import pytest

from se.cfg import load_config
from se.config_identity import strip_inactive_extensions
from se.subject_vm import (
    LIVE_WRITE_REASON_CODES,
    LIVE_WRITE_STATUS_CONTROL_PENDING,
    LIVE_WRITE_STATUS_CONTROL_RELEASED,
    LIVE_WRITE_STATUS_PENDING,
    LIVE_WRITE_STATUS_ROLLED_BACK,
    SUBJECT_VM_ACTIVATION_SCHEMA,
    SUBJECT_VM_ASSOCIATION_SCHEMA,
    SUBJECT_VM_ELIGIBILITY_SCHEMA,
    SUBJECT_VM_INPUT_PORT_SCHEMA,
    SUBJECT_VM_LIVE_WRITE_SCHEMA,
    SUBJECT_VM_MODULATION_SCHEMA,
    SUBJECT_VM_OBJECTIVE_EVENT_SCHEMA,
    SUBJECT_VM_OUTPUT_PORT_SCHEMA,
    SUBJECT_VM_REGION_NAMES,
    SUBJECT_VM_STAGE3C3_SCHEMA,
    SUBJECT_VM_STAGE3C4_SCHEMA,
    SUBJECT_VM_TARGET_BINDING_SCHEMA,
    SUBJECT_VM_TRACE_SCHEMA,
    SUBJECT_VM_TRANSACTION_SCHEMA,
    SUBJECT_VM_UPDATE_SAFETY_SCHEMA,
    TARGET_KIND_NODE,
    SubjectVMActivationConfig,
    SubjectVMAssociationConfig,
    SubjectVMConfig,
    SubjectVMEligibilityConfig,
    SubjectVMLiveWriteConfig,
    SubjectVMModulationConfig,
    SubjectVMObjectiveEventBatch,
    SubjectVMRegionConfig,
    SubjectVMRuntime,
    SubjectVMTargetBindingConfig,
    SubjectVMTargetBindingProposal,
    SubjectVMTargetCandidateBatch,
    SubjectVMThoughtTokenBatch,
    SubjectVMTraceConfig,
    SubjectVMTransactionConfig,
    SubjectVMUpdateSafetyConfig,
    load_subject_vm_config,
    prepare_shadow_transaction,
    propose_safe_parameter_deltas,
    validate_subject_vm_config,
)

TOKEN_WIDTH = 32


def _cfg(*, live_enabled: bool = True, stage: str = SUBJECT_VM_STAGE3C4_SCHEMA) -> SubjectVMConfig:
    active_c4 = stage == SUBJECT_VM_STAGE3C4_SCHEMA
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
        live_write=(
            SubjectVMLiveWriteConfig(
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
            )
            if active_c4
            else SubjectVMLiveWriteConfig()
        ),
    )


def _runtime(cfg: SubjectVMConfig) -> SubjectVMRuntime:
    return SubjectVMRuntime.initialize(
        cfg,
        entity_capacity=1,
        active_rows=np.array([0], dtype=np.int32),
        entity_ids=np.array([11], dtype=np.uint64),
        subject_ids=np.array([101], dtype=np.uint64),
    )


def _binding() -> SubjectVMTargetBindingProposal:
    return SubjectVMTargetBindingProposal(
        requested=True,
        bound_any=True,
        family_bound=np.array([True, False, False, False, False, False]),
        reason=np.zeros(6, dtype=np.uint8),
        target_kind=np.array([TARGET_KIND_NODE, 0, 0, 0, 0, 0], dtype=np.uint8),
        target_index=np.array([0, -1, -1, -1, -1, -1], dtype=np.int32),
        target_id=np.array([1, 0, 0, 0, 0, 0], dtype=np.uint32),
        eligibility_value=np.array([0.5, 0, 0, 0, 0, 0], dtype=np.float32),
        family_proposal=np.array([1.0, 0, 0, 0, 0, 0], dtype=np.float32),
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


def _token(*, associate: bool, propose: bool) -> np.ndarray:
    token = np.zeros(TOKEN_WIDTH, dtype=np.float32)
    token[31] = 1.0
    token[0] = 1.0 if associate else 0.0
    token[1] = 1.0 if propose else 0.0
    token[2] = 1.0
    token[23] = 1.0
    return token


def _append(runtime: SubjectVMRuntime, *, tick: int, event_id: int, active: bool) -> None:
    assert runtime.storage is not None and runtime.trace_storage is not None
    runtime.trace_storage.append(
        SubjectVMObjectiveEventBatch(
            tick=tick,
            rows=np.array([0], dtype=np.int32),
            event_ids=np.array([event_id], dtype=np.uint64),
            entity_ids=np.array([11], dtype=np.uint64),
            subject_ids=np.array([101], dtype=np.uint64),
            action_ids=np.array([0], dtype=np.int16),
            target_subject_ids=np.array([0], dtype=np.uint64),
            success=np.array([True]),
            failure_reason=np.array([0], dtype=np.uint8),
            sampled_probability=np.array([0.5], dtype=np.float32),
            objective_delta=np.array([[3.0 if active else 0.0] + [0.0] * 11], dtype=np.float32),
            resolution_resource_delta=np.zeros((1, 4), dtype=np.float32),
            resolution_internal_resource_delta=np.zeros((1, 4), dtype=np.float32),
            resolution_energy_cost=np.zeros(1, dtype=np.float32),
        ),
        SubjectVMThoughtTokenBatch(
            tick=tick,
            rows=np.array([0], dtype=np.int32),
            emitted=np.array([True]),
            tokens=_token(associate=active, propose=active).reshape(1, -1),
            action_potentials=np.zeros((1, 8), dtype=np.float32),
        ),
        owner_entity_ids=runtime.storage.owner_entity_id,
        owner_subject_ids=runtime.storage.owner_subject_id,
        accounting=runtime.trace_accounting,
        target_candidates=_candidate(tick, active=active),
        graph_storage=runtime.storage,
        live_write_ledger=runtime.live_write_ledger,
    )


def test_stage3c4_requires_explicit_bounded_opt_in() -> None:
    cfg = _cfg()
    validate_subject_vm_config(cfg)
    assert cfg.live_write_configured and cfg.live_write_enabled
    validate_subject_vm_config(_cfg(live_enabled=False))
    with pytest.raises(ValueError, match="forbidden concrete cognition"):
        load_subject_vm_config({"enabled": True, "live_write": {"reward": 1}})
    with pytest.raises(ValueError, match="rollback_after_ticks"):
        validate_subject_vm_config(
            replace(cfg, live_write=replace(cfg.live_write, rollback_after_ticks=5))
        )
    legacy = load_config("configs/mvp_small.json")
    payload = strip_inactive_extensions(asdict(replace(legacy, subject_vm=_cfg(stage=SUBJECT_VM_STAGE3C3_SCHEMA))))
    assert "live_write" not in payload["subject_vm"]


def test_guarded_commit_and_due_rollback_are_exact_and_bounded() -> None:
    runtime = _runtime(_cfg())
    assert runtime.storage is not None and runtime.live_write_ledger is not None
    storage = runtime.storage
    storage.node_expressed[0, 0] = True
    storage.node_bias[0, 0] = np.float32(0.25)
    binding = _binding()
    update = propose_safe_parameter_deltas(storage, row=0, binding=binding, cfg=runtime.cfg.update_safety)
    tx = prepare_shadow_transaction(storage, row=0, binding=binding, update=update, cfg=runtime.cfg.transaction)
    result = runtime.live_write_ledger.commit(
        storage, row=0, tick=2, event_id=702, binding=binding, update=update, transaction=tx
    )
    assert result.authorized and result.committed
    assert storage.node_bias[0, 0] == pytest.approx(0.45)
    assert runtime.live_write_ledger.status[0, result.ledger_slot] == LIVE_WRITE_STATUS_PENDING
    early = runtime.live_write_ledger.rollback_due(storage, rows=np.array([0]), tick=3)
    assert early.rolled_back_transactions == 0
    assert storage.node_bias[0, 0] == pytest.approx(0.45)
    due = runtime.live_write_ledger.rollback_due(storage, rows=np.array([0]), tick=4)
    assert due.rolled_back_transactions == 1 and due.rolled_back_targets == 1
    assert storage.node_bias[0, 0] == pytest.approx(0.25)
    assert runtime.live_write_ledger.status[0, result.ledger_slot] == LIVE_WRITE_STATUS_ROLLED_BACK
    assert runtime.live_write_ledger.total_counted_cost_units == 11


def test_stage3c4_control_reserves_matching_window_without_mutation() -> None:
    runtime = _runtime(_cfg(live_enabled=False))
    assert runtime.storage is not None and runtime.trace_storage is not None
    runtime.storage.node_expressed[0, 0] = True
    runtime.storage.node_bias[0, 0] = np.float32(0.25)
    _append(runtime, tick=0, event_id=700, active=False)
    _append(runtime, tick=2, event_id=702, active=True)
    slot = runtime.trace_storage.latest_slot(0)
    assert slot is not None
    assert runtime.trace_storage.live_write_requested[0, slot]
    assert not runtime.trace_storage.live_write_authorized[0, slot]
    assert not runtime.trace_storage.live_write_committed[0, slot]
    assert runtime.trace_storage.live_write_reason[0, slot] == LIVE_WRITE_REASON_CODES[
        "control-reserved"
    ]
    ledger_slot = int(runtime.trace_storage.live_write_ledger_slot[0, slot])
    assert ledger_slot >= 0
    assert (
        runtime.live_write_ledger.status[0, ledger_slot]
        == LIVE_WRITE_STATUS_CONTROL_PENDING
    )
    assert runtime.storage.node_bias[0, 0] == pytest.approx(0.25)
    usage = runtime.live_write_ledger.rollback_due(
        runtime.storage, rows=np.array([0], dtype=np.int32), tick=4
    )
    assert usage.checked_transactions == 1
    assert usage.rolled_back_transactions == 0
    assert (
        runtime.live_write_ledger.status[0, ledger_slot]
        == LIVE_WRITE_STATUS_CONTROL_RELEASED
    )
    assert runtime.storage.node_bias[0, 0] == pytest.approx(0.25)


def test_live_write_trace_and_ledger_checkpoint_round_trip() -> None:
    runtime = _runtime(_cfg())
    assert runtime.storage is not None and runtime.trace_storage is not None
    runtime.storage.node_expressed[0, 0] = True
    runtime.storage.node_bias[0, 0] = np.float32(0.25)
    _append(runtime, tick=0, event_id=700, active=False)
    _append(runtime, tick=2, event_id=702, active=True)
    assert runtime.storage.node_bias[0, 0] == pytest.approx(0.45)
    slot = runtime.trace_storage.latest_slot(0)
    assert slot is not None and runtime.trace_storage.live_write_committed[0, slot]
    payload = runtime.snapshot_state()
    restored = SubjectVMRuntime.restore(
        runtime.cfg,
        entity_capacity=1,
        payload=payload,
        alive=np.array([True]),
        entity_ids=np.array([11], dtype=np.uint64),
        subject_ids=np.array([101], dtype=np.uint64),
    )
    assert restored.live_write_ledger is not None
    assert restored.storage is not None
    assert restored.storage.node_bias[0, 0] == pytest.approx(0.45)
    for name in runtime.live_write_ledger.snapshot_array_names():
        assert np.array_equal(getattr(restored.live_write_ledger, name), getattr(runtime.live_write_ledger, name)), name
    restored.live_write_ledger.rollback_due(restored.storage, rows=np.array([0]), tick=4)
    assert restored.storage.node_bias[0, 0] == pytest.approx(0.25)


def test_v0117_checkpoint_upgrades_to_empty_live_write_ledger() -> None:
    old = _runtime(_cfg(stage=SUBJECT_VM_STAGE3C3_SCHEMA))
    payload = old.snapshot_state()
    assert payload is not None
    payload["schema"] = "se-subject-vm-runtime-v9"
    payload["trace_storage"]["schema"] = "se-subject-vm-token-event-storage-v6"
    restored = SubjectVMRuntime.restore(
        _cfg(),
        entity_capacity=1,
        payload=payload,
        alive=np.array([True]),
        entity_ids=np.array([11], dtype=np.uint64),
        subject_ids=np.array([101], dtype=np.uint64),
    )
    assert restored.restore_mode == "compatibility-empty-live-write-ledger-rebuild"
    assert restored.live_write_ledger is not None
    assert not np.any(restored.live_write_ledger.entry_valid)
    assert restored.trace_storage is not None
    assert restored.trace_storage.live_write_committed is not None
    assert not np.any(restored.trace_storage.live_write_committed)


def test_runtime_rolls_back_due_write_before_activation() -> None:
    runtime = _runtime(_cfg())
    assert runtime.storage is not None and runtime.live_write_ledger is not None
    storage = runtime.storage
    storage.node_expressed[0, 0] = True
    storage.node_bias[0, 0] = np.float32(0.25)
    binding = _binding()
    update = propose_safe_parameter_deltas(storage, row=0, binding=binding, cfg=runtime.cfg.update_safety)
    tx = prepare_shadow_transaction(storage, row=0, binding=binding, update=update, cfg=runtime.cfg.transaction)
    result = runtime.live_write_ledger.commit(
        storage, row=0, tick=2, event_id=702, binding=binding, update=update, transaction=tx
    )
    assert result.committed and storage.node_bias[0, 0] == pytest.approx(0.45)
    runtime.activate(
        rows=np.array([0], dtype=np.int32),
        input_values=np.zeros((1, 16), dtype=np.float32),
        tick=4,
        output_width=8,
    )
    assert storage.node_bias[0, 0] == pytest.approx(0.25)


def test_rollback_cas_failure_locks_future_subject_writes() -> None:
    runtime = _runtime(_cfg())
    assert runtime.storage is not None and runtime.live_write_ledger is not None
    storage = runtime.storage
    ledger = runtime.live_write_ledger
    storage.node_expressed[0, 0] = True
    storage.node_bias[0, 0] = np.float32(0.25)
    binding = _binding()
    update = propose_safe_parameter_deltas(storage, row=0, binding=binding, cfg=runtime.cfg.update_safety)
    tx = prepare_shadow_transaction(storage, row=0, binding=binding, update=update, cfg=runtime.cfg.transaction)
    first = ledger.commit(
        storage, row=0, tick=2, event_id=702, binding=binding, update=update, transaction=tx
    )
    assert first.committed
    storage.node_bias[0, 0] = np.float32(0.46)
    usage = ledger.rollback_due(storage, rows=np.array([0]), tick=4)
    assert usage.failed_transactions == 1
    assert ledger.row_locked[0]
    update2 = propose_safe_parameter_deltas(storage, row=0, binding=binding, cfg=runtime.cfg.update_safety)
    tx2 = prepare_shadow_transaction(storage, row=0, binding=binding, update=update2, cfg=runtime.cfg.transaction)
    second = ledger.commit(
        storage, row=0, tick=5, event_id=705, binding=binding, update=update2, transaction=tx2
    )
    assert not second.committed
    assert second.reason == LIVE_WRITE_REASON_CODES["row-locked"]


def test_control_and_live_share_pending_target_admission() -> None:
    live = _runtime(_cfg(live_enabled=True))
    control = _runtime(_cfg(live_enabled=False))
    for runtime in (live, control):
        assert runtime.storage is not None and runtime.live_write_ledger is not None
        runtime.storage.node_expressed[0, 0] = True
        runtime.storage.node_bias[0, 0] = np.float32(0.25)

    binding = _binding()
    results = []
    for runtime in (live, control):
        assert runtime.storage is not None and runtime.live_write_ledger is not None
        update = propose_safe_parameter_deltas(
            runtime.storage, row=0, binding=binding, cfg=runtime.cfg.update_safety
        )
        transaction = prepare_shadow_transaction(
            runtime.storage,
            row=0,
            binding=binding,
            update=update,
            cfg=runtime.cfg.transaction,
        )
        first = runtime.live_write_ledger.commit(
            runtime.storage,
            row=0,
            tick=2,
            event_id=702,
            binding=binding,
            update=update,
            transaction=transaction,
        )
        update_again = propose_safe_parameter_deltas(
            runtime.storage, row=0, binding=binding, cfg=runtime.cfg.update_safety
        )
        transaction_again = prepare_shadow_transaction(
            runtime.storage,
            row=0,
            binding=binding,
            update=update_again,
            cfg=runtime.cfg.transaction,
        )
        second = runtime.live_write_ledger.commit(
            runtime.storage,
            row=0,
            tick=3,
            event_id=703,
            binding=binding,
            update=update_again,
            transaction=transaction_again,
        )
        results.append((first, second))

    assert results[0][0].committed
    assert results[1][0].control_reserved
    assert results[0][1].reason == results[1][1].reason
    assert results[0][1].reason in {
        LIVE_WRITE_REASON_CODES["overlapping-pending-target"],
        LIVE_WRITE_REASON_CODES["window-delta-budget"],
        LIVE_WRITE_REASON_CODES["window-target-budget"],
    }
    assert live.live_write_ledger is not None and control.live_write_ledger is not None
    assert live.live_write_ledger._pending_count(0) == 1
    assert control.live_write_ledger._pending_count(0) == 1


def test_v1_live_write_ledger_snapshot_defaults_control_counters() -> None:
    runtime = _runtime(_cfg(live_enabled=False))
    assert runtime.live_write_ledger is not None
    payload = runtime.live_write_ledger.snapshot_state()
    payload["schema"] = "se-subject-vm-live-write-ledger-v1"
    payload["counters"].pop("total_control_reserved_transactions")
    payload["counters"].pop("total_control_released_transactions")
    restored = type(runtime.live_write_ledger).from_snapshot(
        runtime.cfg.live_write, 1, payload
    )
    assert restored.total_control_reserved_transactions == 0
    assert restored.total_control_released_transactions == 0
