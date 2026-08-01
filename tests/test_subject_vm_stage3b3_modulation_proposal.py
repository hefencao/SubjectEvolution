from __future__ import annotations

from dataclasses import asdict, replace
from pathlib import Path

import numpy as np
import pytest

from se.cfg import load_config
from se.config_identity import strip_inactive_extensions
from se.runtime.sim import Simulation
from se.subject_vm import (
    SUBJECT_VM_ACTIVATION_SCHEMA,
    SUBJECT_VM_ASSOCIATION_SCHEMA,
    SUBJECT_VM_ELIGIBILITY_SCHEMA,
    SUBJECT_VM_INPUT_PORT_SCHEMA,
    SUBJECT_VM_MODULATION_SCHEMA,
    SUBJECT_VM_OBJECTIVE_EVENT_SCHEMA,
    SUBJECT_VM_OUTPUT_PORT_SCHEMA,
    SUBJECT_VM_REGION_NAMES,
    SUBJECT_VM_STAGE3B2_SCHEMA,
    SUBJECT_VM_STAGE3B3_SCHEMA,
    SUBJECT_VM_TRACE_SCHEMA,
    SubjectVMActivationConfig,
    SubjectVMAssociationConfig,
    SubjectVMConfig,
    SubjectVMEligibilityConfig,
    SubjectVMModulationConfig,
    SubjectVMObjectiveEventBatch,
    SubjectVMRegionConfig,
    SubjectVMRuntime,
    SubjectVMThoughtTokenBatch,
    SubjectVMTraceConfig,
    load_subject_vm_config,
    validate_subject_vm_config,
)
from se.subject_vm.runtime import RUNTIME_SCHEMA_V5, STAGE3B2_DEVICE_CONTRACT
from se.subject_vm.trace import TRACE_STORAGE_SCHEMA_V2

TOKEN_WIDTH = 32


def _regions() -> tuple[SubjectVMRegionConfig, ...]:
    return tuple(
        SubjectVMRegionConfig(name=name, node_capacity=2, edge_capacity=1, update_period=1)
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
        modulation=(
            SubjectVMModulationConfig(
                schema=SUBJECT_VM_MODULATION_SCHEMA,
                request_token_port=1,
                request_threshold=0.5,
                fact_weight_start_port=2,
                target_weight_start_port=23,
                proposal_clip=1.0,
            )
            if stage == SUBJECT_VM_STAGE3B3_SCHEMA
            else SubjectVMModulationConfig()
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


def _token(*, associate: bool, propose: bool, energy_weight: float = 1.0) -> np.ndarray:
    token = np.zeros(TOKEN_WIDTH, dtype=np.float32)
    token[31] = 1.0  # sole content-address coordinate after controls are excluded
    token[0] = 1.0 if associate else 0.0
    token[1] = 1.0 if propose else 0.0
    token[2] = energy_weight
    token[23] = 1.0  # generic node-bias parameter family
    return token


def _append(runtime: SubjectVMRuntime, *, tick: int, event_id: int, token: np.ndarray, energy_delta: float) -> None:
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
    )


def _small_config(subject_vm: SubjectVMConfig):
    cfg = load_config("configs/mvp_small.json")
    return replace(
        cfg,
        run=replace(cfg.run, ticks=3, metrics_period=100, checkpoint_period=100, full_checkpoint_enabled=False),
        world=replace(cfg.world, initial_entities=32, max_entities=64),
        subject_vm=subject_vm,
    )


def test_stage3b3_config_is_role_neutral_bounded_and_canonical() -> None:
    cfg = _base(SUBJECT_VM_STAGE3B3_SCHEMA)
    assert cfg.modulation_enabled and cfg.association_enabled
    with pytest.raises(ValueError, match="unknown subject_vm.modulation fields"):
        load_subject_vm_config({"enabled": True, "modulation": {"reward_weight": 1.0}})
    with pytest.raises(ValueError, match="must not overlap"):
        validate_subject_vm_config(
            replace(cfg, modulation=replace(cfg.modulation, request_token_port=2))
        )
    payload = strip_inactive_extensions(asdict(_small_config(_base(SUBJECT_VM_STAGE3B2_SCHEMA))))
    assert "modulation" not in payload["subject_vm"]


def test_proposal_uses_objective_contrast_but_not_similarity_as_strength() -> None:
    runtime = _runtime(_base(SUBJECT_VM_STAGE3B3_SCHEMA))
    _append(runtime, tick=0, event_id=700, token=_token(associate=False, propose=False), energy_delta=0.0)
    _append(runtime, tick=2, event_id=702, token=_token(associate=True, propose=True), energy_delta=3.0)
    trace = runtime.trace_storage
    assert trace is not None and trace.modulation_proposed is not None
    slot = trace.latest_slot(0)
    assert slot is not None
    assert trace.association_assigned[0, slot]
    assert trace.associated_event_id[0, slot] == 700
    assert trace.association_similarity[0, slot] == pytest.approx(1.0)
    assert trace.modulation_requested[0, slot]
    assert trace.modulation_proposed[0, slot]
    assert trace.modulation_signal[0, slot] == pytest.approx(1.0)
    assert trace.modulation_vector[0, slot, 0] == pytest.approx(1.0)
    assert np.count_nonzero(trace.modulation_vector[0, slot]) == 1


def test_proposal_is_rejectable_and_does_not_write_graph_or_eligibility() -> None:
    runtime = _runtime(_base(SUBJECT_VM_STAGE3B3_SCHEMA))
    assert runtime.storage is not None
    _append(runtime, tick=0, event_id=710, token=_token(associate=False, propose=False), energy_delta=0.0)
    before = {name: getattr(runtime.storage, name).copy() for name in runtime.storage.snapshot_array_names()}
    _append(runtime, tick=2, event_id=712, token=_token(associate=False, propose=True), energy_delta=3.0)
    trace = runtime.trace_storage
    assert trace is not None and trace.modulation_proposed is not None
    slot = trace.latest_slot(0)
    assert slot is not None
    assert trace.modulation_requested[0, slot]
    assert not trace.modulation_proposed[0, slot]
    for name, value in before.items():
        assert np.array_equal(getattr(runtime.storage, name), value), name


def test_proposal_control_coordinates_do_not_inflate_association_similarity() -> None:
    runtime = _runtime(_base(SUBJECT_VM_STAGE3B3_SCHEMA))
    historical = _token(associate=False, propose=False, energy_weight=-7.0)
    historical[23] = -6.0
    _append(runtime, tick=0, event_id=720, token=historical, energy_delta=0.0)
    current = _token(associate=True, propose=True, energy_weight=7.0)
    current[23] = 6.0
    _append(runtime, tick=2, event_id=722, token=current, energy_delta=2.0)
    trace = runtime.trace_storage
    assert trace is not None
    slot = trace.latest_slot(0)
    assert slot is not None
    assert trace.association_assigned[0, slot]
    assert trace.association_similarity[0, slot] == pytest.approx(1.0)


def test_checkpoint_round_trip_and_v0113_upgrade_rebuild_empty_proposals() -> None:
    cfg = _base(SUBJECT_VM_STAGE3B3_SCHEMA)
    runtime = _runtime(cfg)
    _append(runtime, tick=0, event_id=730, token=_token(associate=False, propose=False), energy_delta=0.0)
    _append(runtime, tick=2, event_id=732, token=_token(associate=True, propose=True), energy_delta=1.0)
    payload = runtime.snapshot_state()
    assert payload is not None
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
        assert np.array_equal(getattr(restored.trace_storage, name), getattr(runtime.trace_storage, name))

    old = _runtime(_base(SUBJECT_VM_STAGE3B2_SCHEMA))
    old_payload = old.snapshot_state()
    assert old_payload is not None
    old_payload["schema"] = RUNTIME_SCHEMA_V5
    old_payload["device_contract"] = STAGE3B2_DEVICE_CONTRACT.schema
    old_payload["trace_storage"]["schema"] = TRACE_STORAGE_SCHEMA_V2
    upgraded = SubjectVMRuntime.restore(
        cfg,
        entity_capacity=1,
        payload=old_payload,
        alive=np.array([True]),
        entity_ids=np.array([11], dtype=np.uint64),
        subject_ids=np.array([101], dtype=np.uint64),
    )
    assert upgraded.restore_mode == "compatibility-empty-modulation-proposal-rebuild"
    assert upgraded.trace_storage is not None
    assert upgraded.trace_storage.modulation_proposed is not None
    assert not np.any(upgraded.trace_storage.modulation_proposed)


def test_stage3b3_empty_path_is_behavior_and_rng_neutral_relative_to_stage3b2(tmp_path: Path) -> None:
    baseline = Simulation(_small_config(_base(SUBJECT_VM_STAGE3B2_SCHEMA)), tmp_path / "b2", backend="cpu")
    candidate = Simulation(_small_config(_base(SUBJECT_VM_STAGE3B3_SCHEMA)), tmp_path / "b3", backend="cpu")
    for _ in range(3):
        baseline.step()
        candidate.step()
    for name, value in vars(baseline.entities).items():
        if name == "cfg":
            continue
        other = getattr(candidate.entities, name)
        if isinstance(value, np.ndarray):
            assert np.array_equal(value, other), name
        else:
            assert value == other, name
    assert np.array_equal(baseline.action_counts, candidate.action_counts)
