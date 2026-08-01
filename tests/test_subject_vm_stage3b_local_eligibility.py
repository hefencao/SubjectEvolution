from __future__ import annotations

from dataclasses import asdict, replace
from pathlib import Path

import numpy as np
import pytest

from se.cfg import load_config
from se.config_identity import strip_inactive_extensions
from se.runtime.sim import Simulation
from se.subject_vm import (
    ACTIVATION_PHASE_MASK,
    LOCAL_ELIGIBILITY_FLAG,
    OP_LINEAR,
    SUBJECT_VM_ACTIVATION_SCHEMA,
    SUBJECT_VM_ELIGIBILITY_SCHEMA,
    SUBJECT_VM_INPUT_PORT_SCHEMA,
    SUBJECT_VM_OBJECTIVE_EVENT_SCHEMA,
    SUBJECT_VM_OUTPUT_PORT_SCHEMA,
    SUBJECT_VM_REGION_NAMES,
    SUBJECT_VM_STAGE3_SCHEMA,
    SUBJECT_VM_STAGE3B_SCHEMA,
    SUBJECT_VM_TRACE_SCHEMA,
    STAGE3_DEVICE_CONTRACT,
    SubjectVMActivationConfig,
    SubjectVMConfig,
    SubjectVMEligibilityConfig,
    SubjectVMObjectiveEventBatch,
    SubjectVMRegionConfig,
    SubjectVMRuntime,
    SubjectVMTraceConfig,
    load_subject_vm_config,
)
from se.subject_vm.runtime import RUNTIME_SCHEMA_V3
from se.subject_vm.storage import STORAGE_SCHEMA_V3


def _regions() -> tuple[SubjectVMRegionConfig, ...]:
    return tuple(
        SubjectVMRegionConfig(
            name=name,
            node_capacity=2,
            edge_capacity=2,
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
        retention_ticks=8,
    )


def _stage3a_config() -> SubjectVMConfig:
    return SubjectVMConfig(
        enabled=True,
        schema=SUBJECT_VM_STAGE3_SCHEMA,
        node_state_width=3,
        regions=_regions(),
        activation=_activation(),
        trace=_trace(),
    )


def _stage3b_config() -> SubjectVMConfig:
    return SubjectVMConfig(
        enabled=True,
        schema=SUBJECT_VM_STAGE3B_SCHEMA,
        node_state_width=3,
        regions=_regions(),
        activation=_activation(),
        trace=_trace(),
        eligibility=SubjectVMEligibilityConfig(
            schema=SUBJECT_VM_ELIGIBILITY_SCHEMA,
            decay=0.5,
            clip=2.0,
            max_age_ticks=2,
        ),
    )


def _runtime(cfg: SubjectVMConfig, capacity: int = 2, active: int | None = None) -> SubjectVMRuntime:
    active_count = capacity if active is None else active
    entity_ids = np.arange(11, 11 + capacity, dtype=np.uint64)
    subject_ids = np.arange(101, 101 + capacity, dtype=np.uint64)
    return SubjectVMRuntime.initialize(
        cfg,
        entity_capacity=capacity,
        active_rows=np.arange(active_count, dtype=np.int32),
        entity_ids=entity_ids,
        subject_ids=subject_ids,
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


def _express_graph(runtime: SubjectVMRuntime, row: int = 0, *, eligibility: bool) -> None:
    storage = runtime.storage
    assert storage is not None
    storage.node_expressed[row, :2] = True
    storage.node_operator_id[row, :2] = OP_LINEAR
    storage.node_activation_phase[row, 0] = 0
    storage.node_activation_phase[row, 1] = 1
    storage.node_input_port[row, 0] = 0
    storage.node_input_gate[row, 0] = 1.0
    storage.node_output_port[row, 1] = 3
    storage.node_output_gate[row, 1] = 1.0
    storage.node_trace_port[row, 1] = 2
    storage.node_trace_gate[row, 1] = 0.5
    storage.edge_expressed[row, 0] = True
    storage.edge_source[row, 0] = 0
    storage.edge_target[row, 0] = 1
    storage.edge_forward_gate[row, 0] = 2.0
    storage.edge_bandwidth[row, 0] = 8.0
    storage.edge_phase_mask[row, 0] = ACTIVATION_PHASE_MASK
    if eligibility:
        storage.node_plasticity_flags[row, 0] = LOCAL_ELIGIBILITY_FLAG
        storage.node_eligibility_gate[row, 0] = 1.0
        storage.plasticity_flags[row, 0] = LOCAL_ELIGIBILITY_FLAG
        storage.edge_eligibility_gate[row, 0] = 0.5


def _event_batch(runtime: SubjectVMRuntime, *, tick: int) -> SubjectVMObjectiveEventBatch:
    assert runtime.storage is not None
    return SubjectVMObjectiveEventBatch(
        tick=tick,
        rows=np.array([0], dtype=np.int32),
        event_ids=np.array([900 + tick], dtype=np.uint64),
        entity_ids=runtime.storage.owner_entity_id[[0]].copy(),
        subject_ids=runtime.storage.owner_subject_id[[0]].copy(),
        action_ids=np.array([3], dtype=np.int16),
        target_subject_ids=np.array([0], dtype=np.uint64),
        success=np.array([True]),
        failure_reason=np.array([0], dtype=np.uint8),
        sampled_probability=np.array([0.4], dtype=np.float32),
        objective_delta=np.zeros((1, 12), dtype=np.float32),
        resolution_resource_delta=np.zeros((1, 4), dtype=np.float32),
        resolution_internal_resource_delta=np.zeros((1, 4), dtype=np.float32),
        resolution_energy_cost=np.zeros(1, dtype=np.float32),
    )


def test_stage3b_config_is_local_and_rejects_value_semantics() -> None:
    cfg = _stage3b_config()
    assert cfg.trace_enabled and cfg.eligibility_enabled
    with pytest.raises(ValueError, match="forbidden concrete cognition"):
        load_subject_vm_config({"enabled": True, "reward": 1.0})
    with pytest.raises(ValueError, match="unknown subject_vm.eligibility fields"):
        load_subject_vm_config(
            {
                "enabled": True,
                "schema": SUBJECT_VM_STAGE3B_SCHEMA,
                "eligibility": {"event_valence": "negative"},
            }
        )
    payload = strip_inactive_extensions(asdict(_small_config(_stage3a_config())))
    assert "eligibility" not in payload["subject_vm"]


def test_local_eligibility_marks_decays_and_expires_without_parameter_update() -> None:
    runtime = _runtime(_stage3b_config(), capacity=1)
    _express_graph(runtime, eligibility=True)
    storage = runtime.storage
    assert storage is not None
    forward_gate = storage.edge_forward_gate.copy()
    node_input_gate = storage.node_input_gate.copy()
    inputs = np.zeros((1, 16), dtype=np.float32)
    inputs[0, 0] = 1.0

    first = runtime.activate(rows=np.array([0]), input_values=inputs, tick=0, output_width=8)
    assert first.action_potentials[0, 3] == pytest.approx(2.0)
    assert storage.node_eligibility_value[0, 0] == pytest.approx(1.0)
    assert storage.eligibility_value[0, 0] == pytest.approx(1.0)
    assert first.eligibility_usage is not None
    assert first.eligibility_usage.node_marks == 1
    assert first.eligibility_usage.edge_marks == 1
    runtime.commit_objective_events(_event_batch(runtime, tick=0))
    before_event = storage.eligibility_value.copy()
    assert np.array_equal(before_event, storage.eligibility_value)

    inputs[0, 0] = 0.0
    runtime.activate(rows=np.array([0]), input_values=inputs, tick=1, output_width=8)
    assert storage.node_eligibility_value[0, 0] == pytest.approx(0.5)
    assert storage.eligibility_value[0, 0] == pytest.approx(0.5)
    assert storage.node_eligibility_age[0, 0] == 1
    assert storage.eligibility_age[0, 0] == 1
    runtime.discard_pending_thought_tokens()
    runtime.activate(rows=np.array([0]), input_values=inputs, tick=2, output_width=8)
    assert storage.node_eligibility_value[0, 0] == pytest.approx(0.25)
    assert storage.eligibility_value[0, 0] == pytest.approx(0.25)
    runtime.discard_pending_thought_tokens()
    runtime.activate(rows=np.array([0]), input_values=inputs, tick=3, output_width=8)
    assert storage.node_eligibility_value[0, 0] == 0.0
    assert storage.eligibility_value[0, 0] == 0.0
    assert storage.node_eligibility_age[0, 0] == 0
    assert storage.eligibility_age[0, 0] == 0
    assert np.array_equal(storage.edge_forward_gate, forward_gate)
    assert np.array_equal(storage.node_input_gate, node_input_gate)


def test_objective_event_commit_does_not_assign_or_change_local_eligibility() -> None:
    runtime = _runtime(_stage3b_config(), capacity=1)
    _express_graph(runtime, eligibility=True)
    inputs = np.zeros((1, 16), dtype=np.float32)
    inputs[0, 0] = 1.0
    runtime.activate(rows=np.array([0]), input_values=inputs, tick=0, output_width=8)
    assert runtime.storage is not None
    node_before = runtime.storage.node_eligibility_value.copy()
    edge_before = runtime.storage.eligibility_value.copy()
    runtime.commit_objective_events(_event_batch(runtime, tick=0))
    assert np.array_equal(runtime.storage.node_eligibility_value, node_before)
    assert np.array_equal(runtime.storage.eligibility_value, edge_before)
    assert runtime.trace_storage is not None
    assert not hasattr(runtime.trace_storage, "node_eligibility")
    assert not hasattr(runtime.trace_storage, "edge_eligibility")


def test_stage3b_is_behavior_and_rng_neutral_relative_to_stage3a(tmp_path: Path) -> None:
    stage3a = Simulation(
        _small_config(_stage3a_config()), tmp_path / "stage3a", backend="cpu"
    )
    stage3b = Simulation(
        _small_config(_stage3b_config()), tmp_path / "stage3b", backend="cpu"
    )
    row_a = int(np.flatnonzero(stage3a.entities.alive)[0])
    row_b = int(np.flatnonzero(stage3b.entities.alive)[0])
    assert row_a == row_b
    _express_graph(stage3a.subject_vm, row_a, eligibility=False)
    _express_graph(stage3b.subject_vm, row_b, eligibility=True)
    for _ in range(3):
        stage3a.step()
        stage3b.step()
    for name, value in vars(stage3a.entities).items():
        if name == "cfg":
            continue
        other = getattr(stage3b.entities, name)
        if isinstance(value, np.ndarray):
            assert np.array_equal(value, other), name
        else:
            assert value == other, name
    assert np.array_equal(stage3a.action_counts, stage3b.action_counts)
    assert stage3b.subject_vm.eligibility_accounting.node_mark_units > 0
    assert stage3b.subject_vm.eligibility_accounting.edge_mark_units > 0


def test_checkpoint_clone_birth_compaction_and_death_preserve_local_boundary() -> None:
    runtime = _runtime(_stage3b_config(), capacity=3, active=1)
    _express_graph(runtime, eligibility=True)
    inputs = np.zeros((1, 16), dtype=np.float32)
    inputs[0, 0] = 1.0
    runtime.activate(rows=np.array([0]), input_values=inputs, tick=0, output_width=8)
    runtime.commit_objective_events(_event_batch(runtime, tick=0))
    clone = runtime.clone()
    assert clone.storage is not None and runtime.storage is not None
    assert np.array_equal(
        clone.storage.node_eligibility_value, runtime.storage.node_eligibility_value
    )
    payload = runtime.snapshot_state()
    assert payload is not None
    restored = SubjectVMRuntime.restore(
        _stage3b_config(),
        entity_capacity=3,
        payload=payload,
        alive=np.array([True, False, False]),
        entity_ids=np.array([11, 12, 13], dtype=np.uint64),
        subject_ids=np.array([101, 102, 103], dtype=np.uint64),
    )
    assert restored.storage is not None
    assert np.array_equal(
        restored.storage.eligibility_value, runtime.storage.eligibility_value
    )

    entity_ids = np.array([11, 12, 13], dtype=np.uint64)
    subject_ids = np.array([101, 102, 103], dtype=np.uint64)
    runtime.inherit_births(np.array([0]), np.array([1]), entity_ids, subject_ids)
    assert runtime.storage.node_eligibility_gate[1, 0] == pytest.approx(1.0)
    assert runtime.storage.node_eligibility_value[1, 0] == 0.0
    assert runtime.storage.eligibility_value[1, 0] == 0.0
    runtime.compact_rows(np.array([0]), np.array([2]))
    assert runtime.storage.node_eligibility_value[2, 0] != 0.0
    assert runtime.storage.node_eligibility_value[0, 0] == 0.0
    moved_entity_ids = entity_ids.copy()
    moved_subject_ids = subject_ids.copy()
    moved_entity_ids[2] = 11
    moved_subject_ids[2] = 101
    runtime.release_deaths(np.array([2]), moved_entity_ids, moved_subject_ids)
    assert runtime.storage.node_eligibility_value[2, 0] == 0.0
    assert runtime.storage.eligibility_last_tick[2] == -1


def test_v0111_stage3a_checkpoint_upgrades_with_empty_local_eligibility() -> None:
    old = _runtime(_stage3a_config(), capacity=1)
    _express_graph(old, eligibility=False)
    inputs = np.zeros((1, 16), dtype=np.float32)
    inputs[0, 0] = 1.0
    old.activate(rows=np.array([0]), input_values=inputs, tick=0, output_width=8)
    old.commit_objective_events(_event_batch(old, tick=0))
    payload = old.snapshot_state()
    assert payload is not None
    payload["schema"] = RUNTIME_SCHEMA_V3
    payload["device_contract"] = STAGE3_DEVICE_CONTRACT.schema
    payload.pop("eligibility_accounting", None)
    payload["storage"]["schema"] = STORAGE_SCHEMA_V3
    for name in (
        "node_eligibility_gate",
        "node_eligibility_value",
        "node_eligibility_age",
        "node_plasticity_flags",
        "edge_eligibility_gate",
        "eligibility_last_tick",
    ):
        payload["storage"]["arrays"].pop(name)
    upgraded = SubjectVMRuntime.restore(
        _stage3b_config(),
        entity_capacity=1,
        payload=payload,
        alive=np.array([True]),
        entity_ids=np.array([11], dtype=np.uint64),
        subject_ids=np.array([101], dtype=np.uint64),
    )
    assert upgraded.restore_mode == "compatibility-empty-local-eligibility-rebuild"
    assert upgraded.storage is not None
    assert not np.any(upgraded.storage.node_eligibility_value)
    assert not np.any(upgraded.storage.eligibility_value)
    assert np.all(upgraded.storage.eligibility_last_tick == -1)
