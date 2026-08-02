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
    OBJECTIVE_EVENT_DELTA_NAMES,
    OP_LINEAR,
    SUBJECT_VM_ACTIVATION_SCHEMA,
    SUBJECT_VM_INPUT_PORT_SCHEMA,
    SUBJECT_VM_OBJECTIVE_EVENT_SCHEMA,
    SUBJECT_VM_OUTPUT_PORT_SCHEMA,
    SUBJECT_VM_REGION_NAMES,
    SUBJECT_VM_STAGE2_SCHEMA,
    SUBJECT_VM_STAGE3_SCHEMA,
    SUBJECT_VM_TRACE_SCHEMA,
    STAGE2_DEVICE_CONTRACT,
    SubjectVMActivationConfig,
    SubjectVMConfig,
    SubjectVMObjectiveEventBatch,
    SubjectVMRegionConfig,
    SubjectVMRuntime,
    SubjectVMTraceConfig,
    load_subject_vm_config,
)
from se.subject_vm.runtime import RUNTIME_SCHEMA_V2
from se.subject_vm.storage import STORAGE_SCHEMA_V2


def _regions(scale: int = 1) -> tuple[SubjectVMRegionConfig, ...]:
    return tuple(
        SubjectVMRegionConfig(
            name=name,
            node_capacity=2 * scale,
            edge_capacity=2 * scale,
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


def _stage2_config() -> SubjectVMConfig:
    return SubjectVMConfig(
        enabled=True,
        schema=SUBJECT_VM_STAGE2_SCHEMA,
        node_state_width=3,
        regions=_regions(),
        activation=_activation(),
    )


def _stage3_config(*, scale: int = 1) -> SubjectVMConfig:
    return SubjectVMConfig(
        enabled=True,
        schema=SUBJECT_VM_STAGE3_SCHEMA,
        node_state_width=3,
        regions=_regions(scale),
        activation=_activation(),
        trace=SubjectVMTraceConfig(
            schema=SUBJECT_VM_TRACE_SCHEMA,
            event_schema=SUBJECT_VM_OBJECTIVE_EVENT_SCHEMA,
            token_width=4,
            token_clip=8.0,
            capacity_per_subject=4,
            retention_ticks=8,
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


def _express_graph(runtime: SubjectVMRuntime, row: int = 0, *, token: bool = True) -> None:
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
    if token:
        storage.node_trace_port[row, 1] = 2
        storage.node_trace_gate[row, 1] = 0.5
    storage.edge_expressed[row, 0] = True
    storage.edge_source[row, 0] = 0
    storage.edge_target[row, 0] = 1
    storage.edge_forward_gate[row, 0] = 2.0
    storage.edge_bandwidth[row, 0] = 8.0
    storage.edge_phase_mask[row, 0] = ACTIVATION_PHASE_MASK


def _event_batch(runtime: SubjectVMRuntime, *, tick: int = 0) -> SubjectVMObjectiveEventBatch:
    assert runtime.storage is not None
    return SubjectVMObjectiveEventBatch(
        tick=tick,
        rows=np.array([0], dtype=np.int32),
        event_ids=np.array([901], dtype=np.uint64),
        entity_ids=runtime.storage.owner_entity_id[[0]].copy(),
        subject_ids=runtime.storage.owner_subject_id[[0]].copy(),
        action_ids=np.array([3], dtype=np.int16),
        target_subject_ids=np.array([0], dtype=np.uint64),
        success=np.array([True]),
        failure_reason=np.array([0], dtype=np.uint8),
        sampled_probability=np.array([0.4], dtype=np.float32),
        objective_delta=np.arange(
            len(OBJECTIVE_EVENT_DELTA_NAMES), dtype=np.float32
        )[None, :],
        resolution_resource_delta=np.array([[1, 2, 3, 4]], dtype=np.float32),
        resolution_internal_resource_delta=np.array(
            [[4, 3, 2, 1]], dtype=np.float32
        ),
        resolution_energy_cost=np.array([0.25], dtype=np.float32),
    )


def test_stage3_config_uses_continuous_token_not_fixed_value_or_hash() -> None:
    cfg = _stage3_config()
    assert cfg.trace_enabled and cfg.activation_enabled
    with pytest.raises(ValueError, match="forbidden concrete cognition"):
        load_subject_vm_config({"enabled": True, "polarity": 1.0})
    with pytest.raises(ValueError, match="unknown subject_vm.trace fields"):
        load_subject_vm_config(
            {
                "enabled": True,
                "schema": SUBJECT_VM_STAGE3_SCHEMA,
                "trace": {"hash_algorithm": "sha256"},
            }
        )
    payload = strip_inactive_extensions(asdict(_small_config(_stage2_config())))
    assert "trace" not in payload["subject_vm"]


def test_graph_emits_continuous_token_without_persistent_path_trace() -> None:
    runtime = _runtime(_stage3_config(), capacity=1)
    _express_graph(runtime)
    inputs = np.zeros((1, 16), dtype=np.float32)
    inputs[0, 0] = 1.0
    first = runtime.activate(
        rows=np.array([0]), input_values=inputs, tick=0, output_width=8
    )
    assert first.action_potentials[0, 3] == pytest.approx(2.0)
    assert first.thought_tokens is not None
    assert first.thought_tokens.tokens[0, 2] == pytest.approx(1.0)
    runtime.commit_objective_events(_event_batch(runtime))
    trace = runtime.trace_storage
    assert trace is not None
    assert not hasattr(trace, "node_usage_ids")
    assert not hasattr(trace, "edge_usage_ids")
    slot = trace.latest_slot(0)
    assert slot is not None
    assert trace.thought_token[0, slot, 2] == pytest.approx(1.0)
    assert runtime.storage is not None
    assert not np.any(runtime.storage.eligibility_value)
    assert not np.any(runtime.storage.eligibility_age)

    inputs[0, 0] = 1.01
    second = runtime.activate(
        rows=np.array([0]), input_values=inputs, tick=1, output_width=8
    )
    assert second.thought_tokens is not None
    assert second.thought_tokens.tokens[0, 2] == pytest.approx(1.01)


def test_trace_memory_is_independent_of_graph_node_and_edge_capacity() -> None:
    small = _runtime(_stage3_config(scale=1), capacity=8)
    large = _runtime(_stage3_config(scale=8), capacity=8)
    assert small.trace_storage is not None and large.trace_storage is not None
    assert small.trace_storage.allocated_nbytes() == large.trace_storage.allocated_nbytes()
    assert small.storage is not None and large.storage is not None
    assert small.storage.node_capacity < large.storage.node_capacity
    assert small.storage.edge_capacity < large.storage.edge_capacity


def test_no_graph_token_means_no_long_term_event_record() -> None:
    runtime = _runtime(_stage3_config(), capacity=1)
    _express_graph(runtime, token=False)
    inputs = np.zeros((1, 16), dtype=np.float32)
    inputs[0, 0] = 1.0
    result = runtime.activate(
        rows=np.array([0]), input_values=inputs, tick=0, output_width=8
    )
    assert result.thought_tokens is not None
    assert not np.any(result.thought_tokens.emitted)
    assert not runtime.has_pending_thought_tokens
    assert runtime.trace_storage is not None
    assert not np.any(runtime.trace_storage.event_valid)


def test_stage3_simulation_records_token_and_post_commit_objective_delta(tmp_path: Path) -> None:
    simulation = Simulation(
        _small_config(_stage3_config()), tmp_path / "trace", backend="cpu"
    )
    row = int(np.flatnonzero(simulation.entities.alive)[0])
    _express_graph(simulation.subject_vm, row)
    simulation.step()
    trace = simulation.subject_vm.trace_storage
    assert trace is not None
    slot = trace.latest_slot(row)
    assert slot is not None
    assert np.any(trace.thought_token[row, slot])
    assert np.all(np.isfinite(trace.objective_delta[row, slot]))
    assert simulation.subject_vm.trace_accounting.recorded_events >= 1
    assert not simulation.subject_vm.has_pending_thought_tokens


def test_stage3_token_trace_is_behavior_and_rng_neutral_relative_to_stage2(tmp_path: Path) -> None:
    stage2 = Simulation(
        _small_config(_stage2_config()), tmp_path / "stage2", backend="cpu"
    )
    stage3 = Simulation(
        _small_config(_stage3_config()), tmp_path / "stage3", backend="cpu"
    )
    row2 = int(np.flatnonzero(stage2.entities.alive)[0])
    row3 = int(np.flatnonzero(stage3.entities.alive)[0])
    assert row2 == row3
    _express_graph(stage2.subject_vm, row2, token=False)
    _express_graph(stage3.subject_vm, row3, token=True)
    stage2.step()
    stage3.step()
    for name, value in vars(stage2.entities).items():
        if name == "cfg":
            continue
        other = getattr(stage3.entities, name)
        if isinstance(value, np.ndarray):
            assert np.array_equal(value, other), name
        else:
            assert value == other, name
    assert np.array_equal(stage2.action_counts, stage3.action_counts)
    assert np.array_equal(
        stage2.last_policy_decision.action, stage3.last_policy_decision.action
    )


def test_checkpoint_restore_and_v0110_upgrade_rebuild_empty_token_ring(tmp_path: Path) -> None:
    simulation = Simulation(
        _small_config(_stage3_config()), tmp_path / "source", backend="cpu"
    )
    row = int(np.flatnonzero(simulation.entities.alive)[0])
    _express_graph(simulation.subject_vm, row)
    simulation.step()
    checkpoint = tmp_path / "stage3.sechk"
    simulation.save_full_checkpoint(checkpoint)
    restored = Simulation.from_checkpoint(
        checkpoint, tmp_path / "restored", backend="cpu"
    )
    assert restored.subject_vm.trace_storage is not None
    assert simulation.subject_vm.trace_storage is not None
    for name in restored.subject_vm.trace_storage.snapshot_array_names():
        assert np.array_equal(
            getattr(restored.subject_vm.trace_storage, name),
            getattr(simulation.subject_vm.trace_storage, name),
        )

    old = _runtime(_stage2_config(), capacity=1)
    _express_graph(old, token=False)
    payload = old.snapshot_state()
    assert payload is not None
    payload["schema"] = RUNTIME_SCHEMA_V2
    payload["device_contract"] = STAGE2_DEVICE_CONTRACT.schema
    payload["storage"]["schema"] = STORAGE_SCHEMA_V2
    payload["storage"]["arrays"].pop("node_trace_port")
    payload["storage"]["arrays"].pop("node_trace_gate")
    upgraded = SubjectVMRuntime.restore(
        _stage3_config(),
        entity_capacity=1,
        payload=payload,
        alive=np.array([True]),
        entity_ids=np.array([11], dtype=np.uint64),
        subject_ids=np.array([101], dtype=np.uint64),
    )
    assert upgraded.restore_mode == "compatibility-empty-token-trace-rebuild"
    assert upgraded.trace_storage is not None
    assert not np.any(upgraded.trace_storage.event_valid)


def test_birth_compaction_and_death_do_not_inherit_or_leak_token_history() -> None:
    runtime = _runtime(_stage3_config(), capacity=3, active=1)
    _express_graph(runtime)
    inputs = np.zeros((1, 16), dtype=np.float32)
    inputs[0, 0] = 1.0
    runtime.activate(rows=np.array([0]), input_values=inputs, tick=0, output_width=8)
    runtime.commit_objective_events(_event_batch(runtime))
    entity_ids = np.array([11, 12, 13], dtype=np.uint64)
    subject_ids = np.array([101, 102, 103], dtype=np.uint64)
    runtime.inherit_births(np.array([0]), np.array([1]), entity_ids, subject_ids)
    assert runtime.trace_storage is not None
    assert runtime.trace_storage.event_count[0] == 1
    assert runtime.trace_storage.event_count[1] == 0
    runtime.compact_rows(np.array([0]), np.array([2]))
    assert runtime.trace_storage.event_count[0] == 0
    assert runtime.trace_storage.event_count[2] == 1
    moved_entity_ids = entity_ids.copy()
    moved_subject_ids = subject_ids.copy()
    moved_entity_ids[2] = 11
    moved_subject_ids[2] = 101
    runtime.release_deaths(np.array([2]), moved_entity_ids, moved_subject_ids)
    assert runtime.trace_storage.event_count[2] == 0


def test_stage3c10_trace_diagnostics_upgrade_v7_and_clear_slots() -> None:
    from se.subject_vm.trace import (
        TRACE_STORAGE_SCHEMA_V7,
        SubjectVMTraceStorage,
    )

    cfg = load_config("configs/mvp_short_subject_vm_stage3c8_paired_study.json").subject_vm
    trace = SubjectVMTraceStorage(cfg, entity_capacity=2)
    assert trace.association_reason is not None
    assert trace.binding_eligibility_age is not None
    trace.association_reason[0, 0] = 5
    trace.binding_eligibility_age[0, 0, 0] = 7
    trace._clear_slot(0, 0)
    assert int(trace.association_reason[0, 0]) == 0
    assert int(trace.binding_eligibility_age[0, 0, 0]) == 0

    payload = trace.snapshot_state()
    payload["schema"] = TRACE_STORAGE_SCHEMA_V7
    payload["arrays"].pop("association_reason")
    payload["arrays"].pop("binding_eligibility_age")
    restored = SubjectVMTraceStorage.from_snapshot(cfg, 2, payload)
    assert restored.association_reason is not None
    assert restored.binding_eligibility_age is not None
    assert not np.any(restored.association_reason)
    assert not np.any(restored.binding_eligibility_age)
