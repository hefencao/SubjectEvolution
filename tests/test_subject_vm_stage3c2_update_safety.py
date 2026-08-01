from __future__ import annotations

from dataclasses import asdict, replace

import numpy as np
import pytest

from se.cfg import load_config
from se.config_identity import strip_inactive_extensions
from se.subject_vm import (
    SUBJECT_VM_ACTIVATION_SCHEMA,
    SUBJECT_VM_ASSOCIATION_SCHEMA,
    SUBJECT_VM_ELIGIBILITY_SCHEMA,
    SUBJECT_VM_INPUT_PORT_SCHEMA,
    SUBJECT_VM_MODULATION_SCHEMA,
    SUBJECT_VM_OBJECTIVE_EVENT_SCHEMA,
    SUBJECT_VM_OUTPUT_PORT_SCHEMA,
    SUBJECT_VM_REGION_NAMES,
    SUBJECT_VM_STAGE3C1_SCHEMA,
    SUBJECT_VM_STAGE3C2_SCHEMA,
    SUBJECT_VM_TARGET_BINDING_SCHEMA,
    SUBJECT_VM_TRACE_SCHEMA,
    SUBJECT_VM_UPDATE_SAFETY_SCHEMA,
    TARGET_KIND_NODE,
    UPDATE_REASON_CODES,
    SubjectVMActivationConfig,
    SubjectVMAssociationConfig,
    SubjectVMConfig,
    SubjectVMEligibilityConfig,
    SubjectVMModulationConfig,
    SubjectVMObjectiveEventBatch,
    SubjectVMRegionConfig,
    SubjectVMRuntime,
    SubjectVMTargetBindingConfig,
    SubjectVMTargetBindingProposal,
    SubjectVMTargetCandidateBatch,
    SubjectVMThoughtTokenBatch,
    SubjectVMTraceConfig,
    SubjectVMUpdateSafetyConfig,
    load_subject_vm_config,
    propose_safe_parameter_deltas,
    validate_subject_vm_config,
)

TOKEN_WIDTH = 32


def _regions() -> tuple[SubjectVMRegionConfig, ...]:
    return tuple(
        SubjectVMRegionConfig(name=name, node_capacity=2, edge_capacity=1, update_period=1)
        for name in SUBJECT_VM_REGION_NAMES
    )


def _base(stage: str = SUBJECT_VM_STAGE3C2_SCHEMA) -> SubjectVMConfig:
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
        target_binding=SubjectVMTargetBindingConfig(
            schema=SUBJECT_VM_TARGET_BINDING_SCHEMA,
            min_abs_eligibility=0.1,
        ),
        update_safety=(
            SubjectVMUpdateSafetyConfig(
                schema=SUBJECT_VM_UPDATE_SAFETY_SCHEMA,
                step_scale=0.5,
                min_abs_delta=0.01,
                family_delta_clip=(0.2, 0.2, 0.2, 0.2, 0.2, 0.2),
                event_l1_budget=0.3,
                parameter_lower_bounds=(-2.0, -2.0, -2.0, -2.0, -2.0, 0.0),
                parameter_upper_bounds=(2.0, 2.0, 2.0, 2.0, 2.0, 2.0),
            )
            if stage == SUBJECT_VM_STAGE3C2_SCHEMA
            else SubjectVMUpdateSafetyConfig()
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


def _binding(*, target_id: int = 1, family_proposal: float = 1.0, eligibility: float = 1.0):
    return SubjectVMTargetBindingProposal(
        requested=True,
        bound_any=True,
        family_bound=np.array([True, False, False, False, False, False]),
        reason=np.zeros(6, dtype=np.uint8),
        target_kind=np.array([TARGET_KIND_NODE, 0, 0, 0, 0, 0], dtype=np.uint8),
        target_index=np.array([0, -1, -1, -1, -1, -1], dtype=np.int32),
        target_id=np.array([target_id, 0, 0, 0, 0, 0], dtype=np.uint32),
        eligibility_value=np.array([eligibility, 0, 0, 0, 0, 0], dtype=np.float32),
        family_proposal=np.array([family_proposal, 0, 0, 0, 0, 0], dtype=np.float32),
    )


def _token(*, associate: bool, propose: bool) -> np.ndarray:
    token = np.zeros(TOKEN_WIDTH, dtype=np.float32)
    token[31] = 1.0
    token[0] = 1.0 if associate else 0.0
    token[1] = 1.0 if propose else 0.0
    token[2] = 1.0
    token[23] = 1.0
    return token


def _candidate(*, tick: int, index: int = -1, target_id: int = 0, value: float = 0.0):
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
        ages[0, 0] = 2
    return SubjectVMTargetCandidateBatch(
        tick=tick,
        rows=np.array([0], dtype=np.int32),
        target_kind=kind,
        target_index=indices,
        target_id=ids,
        eligibility_value=values,
        eligibility_age=ages,
    )


def _append(runtime: SubjectVMRuntime, *, tick: int, event_id: int, token: np.ndarray, energy_delta: float, candidates):
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
        graph_storage=runtime.storage,
    )


def test_stage3c2_config_is_bounded_and_disabled_payload_is_canonical() -> None:
    cfg = _base()
    validate_subject_vm_config(cfg)
    assert cfg.update_safety_enabled and cfg.target_binding_enabled
    with pytest.raises(ValueError, match="unknown subject_vm.update_safety fields"):
        load_subject_vm_config({"enabled": True, "update_safety": {"reward_rate": 1.0}})
    with pytest.raises(ValueError, match="event_l1_budget"):
        validate_subject_vm_config(
            replace(cfg, update_safety=replace(cfg.update_safety, event_l1_budget=9.0))
        )
    legacy = load_config("configs/mvp_small.json")
    payload = strip_inactive_extensions(asdict(replace(legacy, subject_vm=_base(SUBJECT_VM_STAGE3C1_SCHEMA))))
    assert "update_safety" not in payload["subject_vm"]


def test_candidate_delta_is_clipped_bounded_and_audit_only() -> None:
    runtime = _runtime(_base())
    assert runtime.storage is not None
    storage = runtime.storage
    storage.node_expressed[0, 0] = True
    storage.node_bias[0, 0] = 1.95
    before = {name: getattr(storage, name).copy() for name in storage.snapshot_array_names()}
    result = propose_safe_parameter_deltas(
        storage,
        row=0,
        binding=_binding(family_proposal=1.0, eligibility=2.0),
        cfg=runtime.cfg.update_safety,
    )
    assert result.requested and result.proposed_any and not result.write_authorized
    assert result.raw_delta[0] == pytest.approx(1.0)
    assert result.family_clip_applied[0]
    assert result.parameter_bound_applied[0]
    assert result.bounded_delta[0] == pytest.approx(0.05)
    assert result.projected_parameter_value[0] == pytest.approx(2.0)
    assert result.expected_parameter_value[0] == pytest.approx(1.95)
    for name, value in before.items():
        assert np.array_equal(getattr(storage, name), value), name


def test_stale_target_is_rejected_before_delta_proposal() -> None:
    runtime = _runtime(_base())
    assert runtime.storage is not None
    runtime.storage.node_expressed[0, 0] = True
    result = propose_safe_parameter_deltas(
        runtime.storage,
        row=0,
        binding=_binding(target_id=99),
        cfg=runtime.cfg.update_safety,
    )
    assert not result.proposed_any
    assert result.reason[0] == UPDATE_REASON_CODES["stale-target"]


def test_trace_records_delta_proposal_without_parameter_write_and_restores() -> None:
    runtime = _runtime(_base())
    assert runtime.storage is not None
    runtime.storage.node_expressed[0, 0] = True
    runtime.storage.node_bias[0, 0] = 0.25
    _append(runtime, tick=0, event_id=700, token=_token(associate=False, propose=False), energy_delta=0.0, candidates=_candidate(tick=0))
    before = {name: getattr(runtime.storage, name).copy() for name in runtime.storage.snapshot_array_names()}
    _append(runtime, tick=2, event_id=702, token=_token(associate=True, propose=True), energy_delta=3.0, candidates=_candidate(tick=2, index=0, target_id=1, value=0.5))
    trace = runtime.trace_storage
    assert trace is not None and trace.update_proposed_any is not None
    slot = trace.latest_slot(0)
    assert slot is not None
    assert trace.update_requested[0, slot]
    assert trace.update_proposed_any[0, slot]
    assert trace.update_family_proposed[0, slot, 0]
    assert trace.update_expected_parameter_value[0, slot, 0] == pytest.approx(0.25)
    assert trace.update_raw_delta[0, slot, 0] == pytest.approx(0.25)
    assert trace.update_bounded_delta[0, slot, 0] == pytest.approx(0.2)
    assert trace.update_projected_parameter_value[0, slot, 0] == pytest.approx(0.45)
    for name, value in before.items():
        assert np.array_equal(getattr(runtime.storage, name), value), name

    payload = runtime.snapshot_state()
    restored = SubjectVMRuntime.restore(
        runtime.cfg,
        entity_capacity=1,
        payload=payload,
        alive=np.array([True]),
        entity_ids=np.array([11], dtype=np.uint64),
        subject_ids=np.array([101], dtype=np.uint64),
    )
    assert restored.trace_storage is not None
    for name in trace.snapshot_array_names():
        assert np.array_equal(getattr(restored.trace_storage, name), getattr(trace, name)), name


def test_v0115_checkpoint_upgrades_to_empty_update_metadata() -> None:
    old_cfg = _base(SUBJECT_VM_STAGE3C1_SCHEMA)
    old = _runtime(old_cfg)
    payload = old.snapshot_state()
    assert payload is not None
    payload["schema"] = "se-subject-vm-runtime-v7"
    payload["trace_storage"]["schema"] = "se-subject-vm-token-event-storage-v4"
    restored = SubjectVMRuntime.restore(
        _base(),
        entity_capacity=1,
        payload=payload,
        alive=np.array([True]),
        entity_ids=np.array([11], dtype=np.uint64),
        subject_ids=np.array([101], dtype=np.uint64),
    )
    assert restored.restore_mode == "compatibility-empty-update-safety-rebuild"
    assert restored.trace_storage is not None
    assert restored.trace_storage.update_proposed_any is not None
    assert not np.any(restored.trace_storage.update_proposed_any)
