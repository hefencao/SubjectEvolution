from __future__ import annotations

from dataclasses import asdict, replace

import numpy as np
import pytest

from se.cfg import load_config
from se.config_identity import strip_inactive_extensions
from se.subject_vm import (
    LOCAL_ELIGIBILITY_FLAG,
    SUBJECT_VM_ACTIVATION_SCHEMA,
    SUBJECT_VM_ASSOCIATION_SCHEMA,
    SUBJECT_VM_ELIGIBILITY_SCHEMA,
    SUBJECT_VM_INPUT_PORT_SCHEMA,
    SUBJECT_VM_MODULATION_SCHEMA,
    SUBJECT_VM_OBJECTIVE_EVENT_SCHEMA,
    SUBJECT_VM_OUTPUT_PORT_SCHEMA,
    SUBJECT_VM_REGION_NAMES,
    SUBJECT_VM_STAGE3B3_SCHEMA,
    SUBJECT_VM_STAGE3C1_SCHEMA,
    SUBJECT_VM_TARGET_BINDING_SCHEMA,
    SUBJECT_VM_TRACE_SCHEMA,
    TARGET_KIND_NODE,
    SubjectVMActivationConfig,
    SubjectVMAssociationConfig,
    SubjectVMConfig,
    SubjectVMEligibilityConfig,
    SubjectVMModulationConfig,
    SubjectVMObjectiveEventBatch,
    SubjectVMRegionConfig,
    SubjectVMRuntime,
    SubjectVMTargetBindingConfig,
    SubjectVMTargetCandidateBatch,
    SubjectVMThoughtTokenBatch,
    SubjectVMTraceConfig,
    load_subject_vm_config,
    validate_subject_vm_config,
)

TOKEN_WIDTH = 32


def _regions() -> tuple[SubjectVMRegionConfig, ...]:
    return tuple(
        SubjectVMRegionConfig(
            name=name, node_capacity=2, edge_capacity=1, update_period=1
        )
        for name in SUBJECT_VM_REGION_NAMES
    )


def _base(stage: str) -> SubjectVMConfig:
    return SubjectVMConfig(
        enabled=True,
        schema=stage,
        node_state_width=3,
        regions=_regions(),
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
            capacity_per_subject=4,
            retention_ticks=4,
        ),
        eligibility=SubjectVMEligibilityConfig(
            schema=SUBJECT_VM_ELIGIBILITY_SCHEMA,
            decay=0.5,
            clip=2.0,
            max_age_ticks=3,
        ),
        association=SubjectVMAssociationConfig(
            schema=SUBJECT_VM_ASSOCIATION_SCHEMA,
            request_token_port=0,
            request_threshold=0.5,
            similarity_threshold=0.8,
            min_delay_ticks=1,
            max_delay_ticks=3,
        ),
        modulation=SubjectVMModulationConfig(
            schema=SUBJECT_VM_MODULATION_SCHEMA,
            request_token_port=1,
            request_threshold=0.5,
            fact_weight_start_port=2,
            target_weight_start_port=23,
            proposal_clip=1.0,
        ),
        target_binding=(
            SubjectVMTargetBindingConfig(
                schema=SUBJECT_VM_TARGET_BINDING_SCHEMA,
                min_abs_eligibility=0.1,
            )
            if stage == SUBJECT_VM_STAGE3C1_SCHEMA
            else SubjectVMTargetBindingConfig()
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


def _token(*, associate: bool, propose: bool) -> np.ndarray:
    token = np.zeros(TOKEN_WIDTH, dtype=np.float32)
    token[31] = 1.0
    token[0] = 1.0 if associate else 0.0
    token[1] = 1.0 if propose else 0.0
    token[2] = 1.0
    token[23] = 1.0
    return token


def _candidate(
    *, tick: int, index: int = -1, target_id: int = 0, value: float = 0.0, age: int = 0
) -> SubjectVMTargetCandidateBatch:
    kind = np.zeros((1, 6), dtype=np.uint8)
    indices = np.full((1, 6), -1, dtype=np.int32)
    ids = np.zeros((1, 6), dtype=np.uint32)
    values = np.zeros((1, 6), dtype=np.float32)
    ages = np.zeros((1, 6), dtype=np.uint16)
    if index >= 0:
        kind[0, 0] = TARGET_KIND_NODE
        indices[0, 0] = index
        ids[0, 0] = target_id
        values[0, 0] = value
        ages[0, 0] = age
    return SubjectVMTargetCandidateBatch(
        tick=tick,
        rows=np.array([0], dtype=np.int32),
        target_kind=kind,
        target_index=indices,
        target_id=ids,
        eligibility_value=values,
        eligibility_age=ages,
    )


def _append(
    runtime: SubjectVMRuntime,
    *,
    tick: int,
    event_id: int,
    token: np.ndarray,
    energy_delta: float,
    candidates: SubjectVMTargetCandidateBatch,
) -> None:
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
            objective_delta=np.array([[energy_delta] + [0.0] * 11], dtype=np.float32),
            resolution_resource_delta=np.zeros((1, 4), dtype=np.float32),
            resolution_internal_resource_delta=np.zeros((1, 4), dtype=np.float32),
            resolution_energy_cost=np.zeros(1, dtype=np.float32),
        ),
        SubjectVMThoughtTokenBatch(
            tick=tick,
            rows=np.array([0], dtype=np.int32),
            emitted=np.array([True]),
            tokens=token.reshape(1, -1),
            action_potentials=np.zeros((1, 8), dtype=np.float32),
        ),
        owner_entity_ids=runtime.storage.owner_entity_id,
        owner_subject_ids=runtime.storage.owner_subject_id,
        accounting=runtime.trace_accounting,
        target_candidates=candidates,
    )


def _small_config(subject_vm: SubjectVMConfig):
    cfg = load_config("configs/mvp_small.json")
    return replace(cfg, subject_vm=subject_vm)


def test_stage3c1_config_is_bootstrap_bounded_and_canonical() -> None:
    cfg = _base(SUBJECT_VM_STAGE3C1_SCHEMA)
    assert cfg.target_binding_enabled and cfg.modulation_enabled
    with pytest.raises(ValueError, match="unknown subject_vm.target_binding fields"):
        load_subject_vm_config(
            {"enabled": True, "target_binding": {"attention_reward": 1.0}}
        )
    with pytest.raises(ValueError, match="min_abs_eligibility"):
        validate_subject_vm_config(
            replace(
                cfg,
                target_binding=replace(
                    cfg.target_binding,
                    min_abs_eligibility=cfg.eligibility.clip + 1.0,
                ),
            )
        )
    payload = strip_inactive_extensions(asdict(_small_config(_base(SUBJECT_VM_STAGE3B3_SCHEMA))))
    assert "target_binding" not in payload["subject_vm"]


def test_candidates_are_snapshotted_before_current_tick_marks() -> None:
    runtime = _runtime(_base(SUBJECT_VM_STAGE3C1_SCHEMA))
    assert runtime.storage is not None
    storage = runtime.storage
    storage.node_expressed[0, 0] = True
    storage.node_operator_id[0, 0] = 0
    storage.node_activation_period[0, 0] = 1
    storage.node_input_port[0, 0] = 0
    storage.node_input_gate[0, 0] = 1.0
    storage.node_output_port[0, 0] = 0
    storage.node_output_gate[0, 0] = 1.0
    storage.node_trace_port[0, 0] = 31
    storage.node_trace_gate[0, 0] = 1.0
    storage.node_plasticity_flags[0, 0] = LOCAL_ELIGIBILITY_FLAG
    storage.node_eligibility_gate[0, 0] = 1.0
    storage.node_eligibility_value[0, 0] = 0.6
    storage.node_eligibility_age[0, 0] = 1
    storage.eligibility_last_tick[0] = 0

    result = runtime.activate(
        rows=np.array([0], dtype=np.int32),
        input_values=np.array([[1.0] + [0.0] * 15], dtype=np.float32),
        tick=1,
        output_width=8,
    )
    assert result.target_candidates is not None
    candidates = result.target_candidates
    # The historical carrier decays first: 0.6 -> 0.3, age 1 -> 2.
    assert candidates.target_index[0, 0] == 0
    assert candidates.eligibility_value[0, 0] == pytest.approx(0.3)
    assert candidates.eligibility_age[0, 0] == 2
    # Current execution then marks the live carrier and resets its age.
    assert storage.node_eligibility_value[0, 0] == pytest.approx(1.3)
    assert storage.node_eligibility_age[0, 0] == 0
    runtime.discard_pending_thought_tokens()


def test_exact_target_binding_is_audit_only_and_does_not_write_graph() -> None:
    runtime = _runtime(_base(SUBJECT_VM_STAGE3C1_SCHEMA))
    assert runtime.storage is not None
    _append(
        runtime,
        tick=0,
        event_id=700,
        token=_token(associate=False, propose=False),
        energy_delta=0.0,
        candidates=_candidate(tick=0),
    )
    before = {
        name: getattr(runtime.storage, name).copy()
        for name in runtime.storage.snapshot_array_names()
    }
    _append(
        runtime,
        tick=2,
        event_id=702,
        token=_token(associate=True, propose=True),
        energy_delta=3.0,
        candidates=_candidate(tick=2, index=3, target_id=4, value=-0.25, age=2),
    )
    trace = runtime.trace_storage
    assert trace is not None and trace.binding_bound_any is not None
    slot = trace.latest_slot(0)
    assert slot is not None
    assert trace.binding_requested[0, slot]
    assert trace.binding_bound_any[0, slot]
    assert trace.binding_family_bound[0, slot, 0]
    assert trace.binding_target_kind[0, slot, 0] == TARGET_KIND_NODE
    assert trace.binding_target_index[0, slot, 0] == 3
    assert trace.binding_target_id[0, slot, 0] == 4
    assert trace.binding_eligibility_value[0, slot, 0] == pytest.approx(-0.25)
    assert trace.binding_family_proposal[0, slot, 0] == pytest.approx(1.0)
    for name, value in before.items():
        assert np.array_equal(getattr(runtime.storage, name), value), name


def test_zero_age_or_missing_carrier_is_rejected_conservatively() -> None:
    runtime = _runtime(_base(SUBJECT_VM_STAGE3C1_SCHEMA))
    _append(
        runtime,
        tick=0,
        event_id=710,
        token=_token(associate=False, propose=False),
        energy_delta=0.0,
        candidates=_candidate(tick=0),
    )
    _append(
        runtime,
        tick=2,
        event_id=712,
        token=_token(associate=True, propose=True),
        energy_delta=3.0,
        candidates=_candidate(tick=2, index=0, target_id=1, value=1.0, age=0),
    )
    trace = runtime.trace_storage
    assert trace is not None and trace.binding_bound_any is not None
    slot = trace.latest_slot(0)
    assert slot is not None
    assert not trace.binding_bound_any[0, slot]
    assert not np.any(trace.binding_family_bound[0, slot])


def test_checkpoint_round_trip_and_v0114_upgrade_rebuild_empty_bindings() -> None:
    cfg = _base(SUBJECT_VM_STAGE3C1_SCHEMA)
    runtime = _runtime(cfg)
    _append(
        runtime,
        tick=0,
        event_id=720,
        token=_token(associate=False, propose=False),
        energy_delta=0.0,
        candidates=_candidate(tick=0),
    )
    _append(
        runtime,
        tick=2,
        event_id=722,
        token=_token(associate=True, propose=True),
        energy_delta=1.0,
        candidates=_candidate(tick=2, index=0, target_id=1, value=0.5, age=2),
    )
    payload = runtime.snapshot_state()
    restored = SubjectVMRuntime.restore(
        cfg,
        entity_capacity=1,
        payload=payload,
        alive=np.array([True]),
        entity_ids=np.array([11], dtype=np.uint64),
        subject_ids=np.array([101], dtype=np.uint64),
    )
    assert restored.trace_storage is not None and runtime.trace_storage is not None
    for name in runtime.trace_storage.snapshot_array_names():
        assert np.array_equal(
            getattr(restored.trace_storage, name),
            getattr(runtime.trace_storage, name),
        ), name

    old = _runtime(_base(SUBJECT_VM_STAGE3B3_SCHEMA))
    old_payload = old.snapshot_state()
    assert old_payload is not None
    old_payload["schema"] = "se-subject-vm-runtime-v6"
    old_payload["trace_storage"]["schema"] = "se-subject-vm-token-event-storage-v3"
    upgraded = SubjectVMRuntime.restore(
        cfg,
        entity_capacity=1,
        payload=old_payload,
        alive=np.array([True]),
        entity_ids=np.array([11], dtype=np.uint64),
        subject_ids=np.array([101], dtype=np.uint64),
    )
    assert upgraded.restore_mode == "compatibility-empty-target-binding-rebuild"
    assert upgraded.trace_storage is not None
    assert upgraded.trace_storage.binding_bound_any is not None
    assert not np.any(upgraded.trace_storage.binding_bound_any)
