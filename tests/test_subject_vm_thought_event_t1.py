from __future__ import annotations

from dataclasses import asdict, replace

import numpy as np
import pytest

from se.cfg import load_config
from se.config_identity import strip_inactive_extensions
from se.policy import Action
from se.runtime.sim import Simulation
from se.subject_vm import (
    ACTIVATION_PHASE_MASK,
    OBJECTIVE_EVENT_DELTA_NAMES,
    OP_LINEAR,
    SUBJECT_VM_ACTIVATION_SCHEMA,
    SUBJECT_VM_INPUT_PORT_SCHEMA,
    SUBJECT_VM_OBJECTIVE_EVENT_SCHEMA,
    SUBJECT_VM_OUTPUT_PORT_SCHEMA,
    SUBJECT_VM_REGION_NAMES,
    SUBJECT_VM_STAGE3_SCHEMA,
    SUBJECT_VM_THOUGHT_EVENT_SCHEMA,
    SUBJECT_VM_TRACE_SCHEMA,
    SubjectVMActivationConfig,
    SubjectVMConfig,
    SubjectVMObjectiveEventBatch,
    SubjectVMRegionConfig,
    SubjectVMRuntime,
    SubjectVMThoughtEventAppendBatch,
    SubjectVMThoughtEventConfig,
    SubjectVMTraceConfig,
    load_subject_vm_config,
)


def _regions() -> tuple[SubjectVMRegionConfig, ...]:
    return tuple(
        SubjectVMRegionConfig(
            name=name, node_capacity=2, edge_capacity=2, update_period=1
        )
        for name in SUBJECT_VM_REGION_NAMES
    )


def _stage3(*, thought_event: bool) -> SubjectVMConfig:
    return SubjectVMConfig(
        enabled=True,
        schema=SUBJECT_VM_STAGE3_SCHEMA,
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
            token_width=4,
            token_clip=8.0,
            capacity_per_subject=8,
            retention_ticks=16,
        ),
        thought_event=(
            SubjectVMThoughtEventConfig(
                schema=SUBJECT_VM_THOUGHT_EVENT_SCHEMA,
                enabled=True,
                capacity_per_subject=4,
                max_parent_count=2,
                retention_ticks=3,
                emission_base_cost_units=2,
                emission_per_coordinate_cost_units=1,
                parent_link_cost_units=3,
                retention_per_event_tick_cost_units=1,
            )
            if thought_event
            else SubjectVMThoughtEventConfig()
        ),
    )


def _runtime(*, thought_event: bool, capacity: int = 2, active: int | None = None) -> SubjectVMRuntime:
    entity_ids = np.arange(11, 11 + capacity, dtype=np.uint64)
    subject_ids = np.arange(101, 101 + capacity, dtype=np.uint64)
    return SubjectVMRuntime.initialize(
        _stage3(thought_event=thought_event),
        entity_capacity=capacity,
        active_rows=np.arange(capacity if active is None else active, dtype=np.int32),
        entity_ids=entity_ids,
        subject_ids=subject_ids,
    )


def _express(runtime: SubjectVMRuntime, row: int = 0) -> None:
    storage = runtime.storage
    assert storage is not None
    storage.node_expressed[row, :2] = True
    storage.node_operator_id[row, :2] = OP_LINEAR
    storage.node_activation_phase[row, 0] = 0
    storage.node_activation_phase[row, 1] = 1
    storage.node_input_port[row, 0] = 0
    storage.node_input_gate[row, 0] = 1.0
    storage.node_output_port[row, 1] = int(Action.REST)
    storage.node_output_gate[row, 1] = 1.0
    storage.node_trace_port[row, 1] = 2
    storage.node_trace_gate[row, 1] = 0.5
    storage.edge_expressed[row, 0] = True
    storage.edge_source[row, 0] = 0
    storage.edge_target[row, 0] = 1
    storage.edge_forward_gate[row, 0] = 2.0
    storage.edge_bandwidth[row, 0] = 8.0
    storage.edge_phase_mask[row, 0] = ACTIVATION_PHASE_MASK


def _event(runtime: SubjectVMRuntime, event_id: int, tick: int) -> SubjectVMObjectiveEventBatch:
    assert runtime.storage is not None
    return SubjectVMObjectiveEventBatch(
        tick=tick,
        rows=np.array([0], dtype=np.int32),
        event_ids=np.array([event_id], dtype=np.uint64),
        entity_ids=runtime.storage.owner_entity_id[[0]].copy(),
        subject_ids=runtime.storage.owner_subject_id[[0]].copy(),
        action_ids=np.array([int(Action.REST)], dtype=np.int16),
        target_subject_ids=np.array([0], dtype=np.uint64),
        success=np.array([True]),
        failure_reason=np.array([0], dtype=np.uint8),
        sampled_probability=np.array([0.4], dtype=np.float32),
        objective_delta=np.zeros((1, len(OBJECTIVE_EVENT_DELTA_NAMES)), dtype=np.float32),
        resolution_resource_delta=np.zeros((1, 4), dtype=np.float32),
        resolution_internal_resource_delta=np.zeros((1, 4), dtype=np.float32),
        resolution_energy_cost=np.zeros(1, dtype=np.float32),
    )


def _emit(runtime: SubjectVMRuntime, event_id: int, tick: int, value: float = 1.0) -> None:
    inputs = np.zeros((1, 16), dtype=np.float32)
    inputs[0, 0] = value
    runtime.activate(rows=np.array([0]), input_values=inputs, tick=tick, output_width=len(Action))
    runtime.commit_objective_events(_event(runtime, event_id, tick))


def test_disabled_sidecar_is_removed_from_frozen_config_identity() -> None:
    cfg = load_config("configs/mvp_small.json")
    payload = strip_inactive_extensions(asdict(cfg))
    assert "subject_vm" not in payload
    raw = asdict(replace(cfg, subject_vm=_stage3(thought_event=False)))
    stripped = strip_inactive_extensions(raw)
    assert "thought_event" not in stripped["subject_vm"]


def test_enabled_sidecar_requires_stage3_trace_and_bounded_contract() -> None:
    cfg = _stage3(thought_event=True)
    assert cfg.thought_event_enabled
    load_subject_vm_config(asdict(cfg))
    invalid = asdict(cfg)
    invalid["thought_event"]["capacity_per_subject"] = 0
    with pytest.raises(ValueError, match="capacity_per_subject"):
        load_subject_vm_config(invalid)


def test_runtime_event_core_reuses_graph_token_without_action_or_fact_fields() -> None:
    runtime = _runtime(thought_event=True, capacity=1)
    _express(runtime)
    _emit(runtime, 901, 0)
    arena = runtime.thought_event_arena
    trace = runtime.trace_storage
    assert arena is not None and trace is not None
    arena_slot = arena.latest_slot(0)
    trace_slot = trace.latest_slot(0)
    assert arena_slot is not None and trace_slot is not None
    assert arena.event_id[0, arena_slot] == trace.event_id[0, trace_slot]
    np.testing.assert_array_equal(
        arena.token[0, arena_slot], trace.thought_token[0, trace_slot]
    )
    assert arena.parent_count[0, arena_slot] == 0
    assert not hasattr(arena, "action_id")
    assert not hasattr(arena, "objective_delta")
    assert runtime.thought_event_accounting.emitted_events == 1
    assert runtime.thought_event_accounting.counted_emission_cost_units == 6


def test_parent_dag_lifecycle_and_count_only_costs() -> None:
    runtime = _runtime(thought_event=True, capacity=1)
    arena = runtime.thought_event_arena
    assert arena is not None and runtime.storage is not None
    owners_e = runtime.storage.owner_entity_id
    owners_s = runtime.storage.owner_subject_id

    def append(event_id: int, tick: int, parents: tuple[int, ...] = ()) -> None:
        pids = np.zeros((1, 2), dtype=np.uint64)
        weights = np.zeros((1, 2), dtype=np.float32)
        if parents:
            pids[0, : len(parents)] = parents
            weights[0, : len(parents)] = 1.0 / len(parents)
        arena.append(
            SubjectVMThoughtEventAppendBatch(
                tick=tick,
                rows=np.array([0], dtype=np.int32),
                event_ids=np.array([event_id], dtype=np.uint64),
                entity_ids=owners_e[[0]].copy(),
                subject_ids=owners_s[[0]].copy(),
                emitted=np.array([True]),
                tokens=np.full((1, 4), float(event_id % 10), dtype=np.float32),
                parent_count=np.array([len(parents)], dtype=np.uint8),
                parent_event_ids=pids,
                parent_weights=weights,
            ),
            owner_entity_ids=owners_e,
            owner_subject_ids=owners_s,
            accounting=runtime.thought_event_accounting,
        )

    append(1001, 0)
    append(1002, 1, (1001,))
    slot1 = arena._event_slot(0, 1001)
    slot2 = arena._event_slot(0, 1002)
    assert slot1 is not None and slot2 is not None and slot1 != slot2
    assert arena.child_reference_count[0, slot1] == 1
    assert arena.reactivation_count[0, slot1] == 1
    assert arena.parent_event_id[0, slot2, 0] == 1001
    assert runtime.thought_event_accounting.parent_links == 1
    assert runtime.thought_event_accounting.counted_parent_link_cost_units == 3
    arena.advance_rows(
        np.array([0], dtype=np.int32), tick=5, accounting=runtime.thought_event_accounting
    )
    assert not np.any(arena.event_valid[0])
    assert runtime.thought_event_accounting.expired_events == 2
    assert runtime.thought_event_accounting.counted_retention_cost_units > 0


def test_checkpoint_clone_birth_death_and_compaction_preserve_arena_contract() -> None:
    runtime = _runtime(thought_event=True, capacity=3, active=2)
    _express(runtime)
    _emit(runtime, 901, 0)
    snapshot = runtime.snapshot_state()
    assert snapshot is not None
    alive = np.array([True, True, False])
    entity_ids = np.array([11, 12, 0], dtype=np.uint64)
    subject_ids = np.array([101, 102, 0], dtype=np.uint64)
    restored = SubjectVMRuntime.restore(
        runtime.cfg,
        entity_capacity=3,
        payload=snapshot,
        alive=alive,
        entity_ids=entity_ids,
        subject_ids=subject_ids,
    )
    assert restored.thought_event_arena is not None
    np.testing.assert_array_equal(
        restored.thought_event_arena.event_id, runtime.thought_event_arena.event_id
    )
    cloned = runtime.clone()
    np.testing.assert_array_equal(
        cloned.thought_event_arena.event_id, runtime.thought_event_arena.event_id
    )

    entity_ids[2] = 13
    subject_ids[2] = 103
    alive[2] = True
    runtime.inherit_births(
        np.array([0], dtype=np.int32),
        np.array([2], dtype=np.int32),
        entity_ids,
        subject_ids,
    )
    assert runtime.thought_event_arena is not None
    assert not np.any(runtime.thought_event_arena.event_valid[2])
    runtime.release_deaths(np.array([1], dtype=np.int32), entity_ids, subject_ids)
    alive[1] = False
    entity_ids[1] = 0
    subject_ids[1] = 0
    runtime.compact_rows(np.array([2], dtype=np.int32), np.array([1], dtype=np.int32))
    alive[2] = False
    alive[1] = True
    entity_ids[1], entity_ids[2] = entity_ids[2], 0
    subject_ids[1], subject_ids[2] = subject_ids[2], 0
    runtime.validate_owners(alive, entity_ids, subject_ids)


def test_t1_sidecar_is_behavior_and_world_state_neutral(tmp_path) -> None:
    base = load_config("configs/mvp_small.json")
    common = dict(
        run=replace(
            base.run,
            ticks=4,
            metrics_period=100,
            checkpoint_period=100,
            full_checkpoint_enabled=False,
        ),
        world=replace(base.world, initial_entities=32, max_entities=64),
    )
    off = Simulation(
        replace(base, **common, subject_vm=_stage3(thought_event=False)),
        tmp_path / "off",
        backend="cpu",
    )
    on = Simulation(
        replace(base, **common, subject_vm=_stage3(thought_event=True)),
        tmp_path / "on",
        backend="cpu",
    )
    row_off = int(np.flatnonzero(off.entities.alive)[0])
    row_on = int(np.flatnonzero(on.entities.alive)[0])
    _express(off.subject_vm, row_off)
    _express(on.subject_vm, row_on)
    for _ in range(4):
        off.step()
        on.step()
    for name, value in vars(off.entities).items():
        if name == "cfg":
            continue
        other = getattr(on.entities, name)
        if isinstance(value, np.ndarray):
            np.testing.assert_array_equal(value, other, err_msg=name)
        else:
            assert value == other, name
    np.testing.assert_array_equal(off.action_counts, on.action_counts)
    np.testing.assert_array_equal(
        off.last_policy_decision.action, on.last_policy_decision.action
    )
    np.testing.assert_array_equal(off.environment.resources, on.environment.resources)
    assert on.subject_vm.thought_event_accounting.emitted_events > 0
