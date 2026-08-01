from __future__ import annotations

from dataclasses import asdict, replace
from pathlib import Path

import numpy as np
import pytest

from se.cfg import load_config
from se.config_identity import strip_inactive_extensions
from se.runtime.sim import Simulation
from se.subject_vm import (
    LOCAL_ELIGIBILITY_FLAG,
    OP_LINEAR,
    SUBJECT_VM_ACTIVATION_SCHEMA,
    SUBJECT_VM_ASSOCIATION_SCHEMA,
    SUBJECT_VM_ELIGIBILITY_SCHEMA,
    SUBJECT_VM_INPUT_PORT_SCHEMA,
    SUBJECT_VM_OBJECTIVE_EVENT_SCHEMA,
    SUBJECT_VM_OUTPUT_PORT_SCHEMA,
    SUBJECT_VM_REGION_NAMES,
    SUBJECT_VM_STAGE3B_SCHEMA,
    SUBJECT_VM_STAGE3B2_SCHEMA,
    SUBJECT_VM_TRACE_SCHEMA,
    SubjectVMActivationConfig,
    SubjectVMAssociationConfig,
    SubjectVMConfig,
    SubjectVMEligibilityConfig,
    SubjectVMObjectiveEventBatch,
    SubjectVMRegionConfig,
    SubjectVMRuntime,
    SubjectVMTraceConfig,
    load_subject_vm_config,
    validate_subject_vm_config,
)
from se.subject_vm.runtime import RUNTIME_SCHEMA_V4, STAGE3B_DEVICE_CONTRACT
from se.subject_vm.trace import TRACE_STORAGE_SCHEMA_V1


def _regions() -> tuple[SubjectVMRegionConfig, ...]:
    return tuple(
        SubjectVMRegionConfig(
            name=name,
            node_capacity=2,
            edge_capacity=1,
            update_period=1,
        )
        for name in SUBJECT_VM_REGION_NAMES
    )


def _activation() -> SubjectVMActivationConfig:
    return SubjectVMActivationConfig(
        schema=SUBJECT_VM_ACTIVATION_SCHEMA,
        input_port_schema=SUBJECT_VM_INPUT_PORT_SCHEMA,
        output_port_schema=SUBJECT_VM_OUTPUT_PORT_SCHEMA,
        activation_clip=8.0,
        output_clip=8.0,
    )


def _trace() -> SubjectVMTraceConfig:
    return SubjectVMTraceConfig(
        schema=SUBJECT_VM_TRACE_SCHEMA,
        event_schema=SUBJECT_VM_OBJECTIVE_EVENT_SCHEMA,
        token_width=4,
        token_clip=8.0,
        capacity_per_subject=4,
        retention_ticks=4,
    )


def _eligibility() -> SubjectVMEligibilityConfig:
    return SubjectVMEligibilityConfig(
        schema=SUBJECT_VM_ELIGIBILITY_SCHEMA,
        decay=0.5,
        clip=2.0,
        max_age_ticks=3,
    )


def _stage3b1_config() -> SubjectVMConfig:
    return SubjectVMConfig(
        enabled=True,
        schema=SUBJECT_VM_STAGE3B_SCHEMA,
        node_state_width=3,
        regions=_regions(),
        activation=_activation(),
        trace=_trace(),
        eligibility=_eligibility(),
    )


def _stage3b2_config() -> SubjectVMConfig:
    return SubjectVMConfig(
        enabled=True,
        schema=SUBJECT_VM_STAGE3B2_SCHEMA,
        node_state_width=3,
        regions=_regions(),
        activation=_activation(),
        trace=_trace(),
        eligibility=_eligibility(),
        association=SubjectVMAssociationConfig(
            schema=SUBJECT_VM_ASSOCIATION_SCHEMA,
            request_token_port=3,
            request_threshold=0.5,
            similarity_threshold=0.8,
            min_delay_ticks=1,
            max_delay_ticks=3,
        ),
    )


def _runtime(cfg: SubjectVMConfig, capacity: int = 1) -> SubjectVMRuntime:
    return SubjectVMRuntime.initialize(
        cfg,
        entity_capacity=capacity,
        active_rows=np.arange(capacity, dtype=np.int32),
        entity_ids=np.arange(11, 11 + capacity, dtype=np.uint64),
        subject_ids=np.arange(101, 101 + capacity, dtype=np.uint64),
    )


def _express_token_graph(runtime: SubjectVMRuntime, row: int = 0) -> None:
    storage = runtime.storage
    assert storage is not None
    storage.node_expressed[row, :3] = True
    storage.node_operator_id[row, :3] = OP_LINEAR
    storage.node_input_port[row, 0] = 0
    storage.node_input_gate[row, 0] = 1.0
    storage.node_trace_port[row, 0] = 0
    storage.node_trace_gate[row, 0] = 1.0
    storage.node_input_port[row, 1] = 1
    storage.node_input_gate[row, 1] = 1.0
    storage.node_trace_port[row, 1] = 1
    storage.node_trace_gate[row, 1] = 1.0
    storage.node_bias[row, 2] = 1.0
    storage.node_trace_port[row, 2] = 3
    storage.node_trace_gate[row, 2] = 1.0
    storage.node_plasticity_flags[row, 0] = LOCAL_ELIGIBILITY_FLAG
    storage.node_eligibility_gate[row, 0] = 1.0


def _activate(runtime: SubjectVMRuntime, *, tick: int, x: float, y: float) -> None:
    inputs = np.zeros((1, 16), dtype=np.float32)
    inputs[0, 0] = x
    inputs[0, 1] = y
    result = runtime.activate(
        rows=np.array([0], dtype=np.int32),
        input_values=inputs,
        tick=tick,
        output_width=8,
    )
    assert result.thought_tokens is not None


def _event(runtime: SubjectVMRuntime, *, tick: int, event_id: int) -> None:
    assert runtime.storage is not None
    runtime.commit_objective_events(
        SubjectVMObjectiveEventBatch(
            tick=tick,
            rows=np.array([0], dtype=np.int32),
            event_ids=np.array([event_id], dtype=np.uint64),
            entity_ids=runtime.storage.owner_entity_id[[0]].copy(),
            subject_ids=runtime.storage.owner_subject_id[[0]].copy(),
            action_ids=np.array([0], dtype=np.int16),
            target_subject_ids=np.array([0], dtype=np.uint64),
            success=np.array([True]),
            failure_reason=np.array([0], dtype=np.uint8),
            sampled_probability=np.array([0.5], dtype=np.float32),
            objective_delta=np.zeros((1, 12), dtype=np.float32),
            resolution_resource_delta=np.zeros((1, 4), dtype=np.float32),
            resolution_internal_resource_delta=np.zeros((1, 4), dtype=np.float32),
            resolution_energy_cost=np.zeros(1, dtype=np.float32),
        )
    )


def _small_config(subject_vm: SubjectVMConfig):
    cfg = load_config("configs/mvp_small.json")
    return replace(
        cfg,
        run=replace(
            cfg.run,
            ticks=4,
            metrics_period=100,
            checkpoint_period=100,
            full_checkpoint_enabled=False,
        ),
        world=replace(cfg.world, initial_entities=32, max_entities=64),
        subject_vm=subject_vm,
    )


def test_stage3b2_config_is_bounded_and_has_no_value_or_hash_fields() -> None:
    cfg = _stage3b2_config()
    assert cfg.association_enabled and cfg.eligibility_enabled and cfg.trace_enabled
    with pytest.raises(ValueError, match="forbidden concrete cognition"):
        load_subject_vm_config({"enabled": True, "subjective_value": 1.0})
    with pytest.raises(ValueError, match="unknown subject_vm.association fields"):
        load_subject_vm_config(
            {
                "enabled": True,
                "schema": SUBJECT_VM_STAGE3B2_SCHEMA,
                "association": {"hash_algorithm": "sha256"},
            }
        )
    with pytest.raises(ValueError, match="at least 1"):
        validate_subject_vm_config(
            replace(cfg, association=replace(cfg.association, min_delay_ticks=0))
        )
    payload = strip_inactive_extensions(asdict(_small_config(_stage3b1_config())))
    assert "association" not in payload["subject_vm"]


def test_delayed_association_selects_similar_older_token_and_allows_unassigned() -> None:
    runtime = _runtime(_stage3b2_config())
    _express_token_graph(runtime)
    _activate(runtime, tick=0, x=1.0, y=0.0)
    _event(runtime, tick=0, event_id=900)
    _activate(runtime, tick=1, x=0.0, y=1.0)
    _event(runtime, tick=1, event_id=901)
    trace = runtime.trace_storage
    assert trace is not None and trace.association_assigned is not None
    slot1 = trace.latest_slot(0)
    assert slot1 is not None
    assert trace.association_requested[0, slot1]
    assert not trace.association_assigned[0, slot1]
    assert runtime.trace_accounting.association_unassigned_below_threshold == 1

    _activate(runtime, tick=2, x=1.0, y=0.0)
    _event(runtime, tick=2, event_id=902)
    slot2 = trace.latest_slot(0)
    assert slot2 is not None
    assert trace.association_assigned[0, slot2]
    assert trace.associated_event_id[0, slot2] == 900
    assert trace.associated_event_tick[0, slot2] == 0
    assert trace.association_delay_ticks[0, slot2] == 2
    assert trace.association_similarity[0, slot2] == pytest.approx(1.0)


def test_request_coordinate_is_not_part_of_similarity_and_no_request_stays_unassigned() -> None:
    runtime = _runtime(_stage3b2_config())
    _express_token_graph(runtime)
    _activate(runtime, tick=0, x=1.0, y=0.0)
    _event(runtime, tick=0, event_id=910)
    assert runtime.storage is not None
    runtime.storage.node_trace_gate[0, 2] = 0.0
    _activate(runtime, tick=1, x=1.0, y=0.0)
    _event(runtime, tick=1, event_id=911)
    trace = runtime.trace_storage
    assert trace is not None and trace.association_requested is not None
    slot = trace.latest_slot(0)
    assert slot is not None
    assert not trace.association_requested[0, slot]
    assert not trace.association_assigned[0, slot]
    assert runtime.trace_accounting.association_unassigned_no_request == 1


def test_association_does_not_change_eligibility_or_graph_parameters() -> None:
    runtime = _runtime(_stage3b2_config())
    _express_token_graph(runtime)
    assert runtime.storage is not None
    _activate(runtime, tick=0, x=1.0, y=0.0)
    _event(runtime, tick=0, event_id=920)
    _activate(runtime, tick=1, x=1.0, y=0.0)
    eligibility_before = runtime.storage.node_eligibility_value.copy()
    gates_before = runtime.storage.node_input_gate.copy()
    biases_before = runtime.storage.node_bias.copy()
    _event(runtime, tick=1, event_id=921)
    assert np.array_equal(runtime.storage.node_eligibility_value, eligibility_before)
    assert np.array_equal(runtime.storage.node_input_gate, gates_before)
    assert np.array_equal(runtime.storage.node_bias, biases_before)


def test_stage3b2_is_behavior_and_rng_neutral_relative_to_stage3b1(tmp_path: Path) -> None:
    baseline = Simulation(
        _small_config(_stage3b1_config()), tmp_path / "stage3b1", backend="cpu"
    )
    candidate = Simulation(
        _small_config(_stage3b2_config()), tmp_path / "stage3b2", backend="cpu"
    )
    row_a = int(np.flatnonzero(baseline.entities.alive)[0])
    row_b = int(np.flatnonzero(candidate.entities.alive)[0])
    _express_token_graph(baseline.subject_vm, row_a)
    _express_token_graph(candidate.subject_vm, row_b)
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


def test_checkpoint_round_trip_and_v0112_upgrade_start_with_empty_associations() -> None:
    cfg = _stage3b2_config()
    runtime = _runtime(cfg)
    _express_token_graph(runtime)
    _activate(runtime, tick=0, x=1.0, y=0.0)
    _event(runtime, tick=0, event_id=930)
    _activate(runtime, tick=1, x=1.0, y=0.0)
    _event(runtime, tick=1, event_id=931)
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
        assert np.array_equal(
            getattr(restored.trace_storage, name),
            getattr(runtime.trace_storage, name),
        )

    old = _runtime(_stage3b1_config())
    old_payload = old.snapshot_state()
    assert old_payload is not None
    old_payload["schema"] = RUNTIME_SCHEMA_V4
    old_payload["device_contract"] = STAGE3B_DEVICE_CONTRACT.schema
    old_payload["trace_storage"]["schema"] = TRACE_STORAGE_SCHEMA_V1
    upgraded = SubjectVMRuntime.restore(
        cfg,
        entity_capacity=1,
        payload=old_payload,
        alive=np.array([True]),
        entity_ids=np.array([11], dtype=np.uint64),
        subject_ids=np.array([101], dtype=np.uint64),
    )
    assert upgraded.restore_mode == "compatibility-empty-delayed-association-rebuild"
    assert upgraded.trace_storage is not None
    assert upgraded.trace_storage.association_assigned is not None
    assert not np.any(upgraded.trace_storage.association_assigned)
