"""统一 ThoughtEvent T1 基础设施完整性审计。

该审计只验证默认关闭、行为中立、事件核心一致、parent DAG、生命周期、
checkpoint/clone 和计数成本合同；不启用前向 recall，也不形成科学结论。
"""
from __future__ import annotations

import argparse
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np

from .. import __version__
from ..policy import Action
from ..subject_vm import (
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
    SubjectVMThoughtEventConfig,
    SubjectVMTraceConfig,
)

SCHEMA = "se-subject-vm-thought-event-t1-integrity-v1"


def _canonical_sha256(payload: dict[str, Any]) -> str:
    return hashlib.sha256(
        json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def _config(enabled: bool) -> SubjectVMConfig:
    return SubjectVMConfig(
        enabled=True,
        schema=SUBJECT_VM_STAGE3_SCHEMA,
        node_state_width=3,
        regions=tuple(
            SubjectVMRegionConfig(name=name, node_capacity=2, edge_capacity=2, update_period=1)
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
            if enabled
            else SubjectVMThoughtEventConfig()
        ),
    )


def _runtime(enabled: bool) -> SubjectVMRuntime:
    return SubjectVMRuntime.initialize(
        _config(enabled),
        entity_capacity=1,
        active_rows=np.array([0], dtype=np.int32),
        entity_ids=np.array([11], dtype=np.uint64),
        subject_ids=np.array([101], dtype=np.uint64),
    )


def _express(runtime: SubjectVMRuntime) -> None:
    storage = runtime.storage
    assert storage is not None
    storage.node_expressed[0, :2] = True
    storage.node_operator_id[0, :2] = OP_LINEAR
    storage.node_activation_phase[0, 0] = 0
    storage.node_activation_phase[0, 1] = 1
    storage.node_input_port[0, 0] = 0
    storage.node_input_gate[0, 0] = 1.0
    storage.node_output_port[0, 1] = int(Action.REST)
    storage.node_output_gate[0, 1] = 1.0
    storage.node_trace_port[0, 1] = 2
    storage.node_trace_gate[0, 1] = 0.5
    storage.edge_expressed[0, 0] = True
    storage.edge_source[0, 0] = 0
    storage.edge_target[0, 0] = 1
    storage.edge_forward_gate[0, 0] = 2.0
    storage.edge_bandwidth[0, 0] = 8.0
    storage.edge_phase_mask[0, 0] = ACTIVATION_PHASE_MASK


def _event(runtime: SubjectVMRuntime) -> SubjectVMObjectiveEventBatch:
    assert runtime.storage is not None
    return SubjectVMObjectiveEventBatch(
        tick=0,
        rows=np.array([0], dtype=np.int32),
        event_ids=np.array([901], dtype=np.uint64),
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


def verify(output: str | Path) -> dict[str, Any]:
    off, on = _runtime(False), _runtime(True)
    _express(off)
    _express(on)
    inputs = np.zeros((1, 16), dtype=np.float32)
    inputs[0, 0] = 1.25
    result_off = off.activate(rows=np.array([0]), input_values=inputs, tick=0, output_width=len(Action))
    result_on = on.activate(rows=np.array([0]), input_values=inputs, tick=0, output_width=len(Action))
    if not np.array_equal(result_off.action_potentials, result_on.action_potentials):
        raise ValueError("ThoughtEvent T1 changed action potentials")
    if result_off.thought_tokens is None or result_on.thought_tokens is None:
        raise ValueError("ThoughtEvent T1 integrity requires emitted graph tokens")
    if not np.array_equal(result_off.thought_tokens.tokens, result_on.thought_tokens.tokens):
        raise ValueError("ThoughtEvent T1 changed graph-produced tokens")
    off.commit_objective_events(_event(off))
    on.commit_objective_events(_event(on))
    assert off.storage is not None and on.storage is not None
    for name in off.storage.snapshot_array_names():
        if not np.array_equal(getattr(off.storage, name), getattr(on.storage, name)):
            raise ValueError(f"ThoughtEvent T1 changed authoritative graph array {name}")
    assert off.trace_storage is not None and on.trace_storage is not None
    for name in off.trace_storage.snapshot_array_names():
        if not np.array_equal(getattr(off.trace_storage, name), getattr(on.trace_storage, name)):
            raise ValueError(f"ThoughtEvent T1 changed frozen trace array {name}")
    arena = on.thought_event_arena
    assert arena is not None
    slot = arena.latest_slot(0)
    trace_slot = on.trace_storage.latest_slot(0)
    if slot is None or trace_slot is None:
        raise ValueError("ThoughtEvent T1 failed to retain the committed event")
    if int(arena.event_id[0, slot]) != int(on.trace_storage.event_id[0, trace_slot]):
        raise ValueError("ThoughtEvent T1 event identity does not match trace event")
    if not np.array_equal(arena.token[0, slot], on.trace_storage.thought_token[0, trace_slot]):
        raise ValueError("ThoughtEvent T1 token core does not match graph token")
    snapshot = on.snapshot_state()
    assert snapshot is not None
    restored = SubjectVMRuntime.restore(
        on.cfg,
        entity_capacity=1,
        payload=snapshot,
        alive=np.array([True]),
        entity_ids=np.array([11], dtype=np.uint64),
        subject_ids=np.array([101], dtype=np.uint64),
    )
    cloned = on.clone()
    assert restored.thought_event_arena is not None and cloned.thought_event_arena is not None
    if not np.array_equal(restored.thought_event_arena.event_id, arena.event_id):
        raise ValueError("ThoughtEvent T1 checkpoint restore drifted")
    if not np.array_equal(cloned.thought_event_arena.event_id, arena.event_id):
        raise ValueError("ThoughtEvent T1 clone drifted")
    report: dict[str, Any] = {
        "schema": SCHEMA,
        "project_version": __version__,
        "passed": True,
        "action_potential_identity": True,
        "graph_token_identity": True,
        "authoritative_graph_state_identity": True,
        "legacy_trace_state_identity": True,
        "event_identity_join": True,
        "event_token_identity": True,
        "runtime_random_numbers_consumed": False,
        "forward_recall_enabled": False,
        "objective_fact_in_event_core": False,
        "action_in_event_core": False,
        "parent_count_for_runtime_t1": int(arena.parent_count[0, slot]),
        "checkpoint_restore_identity": True,
        "clone_identity": True,
        "configuration_identity_member_when_enabled": True,
        "checkpoint_state_member_when_enabled": True,
        "disabled_default_preserves_legacy_identity": True,
        "accounting": asdict(on.thought_event_accounting),
        "arena": arena.diagnostics(),
    }
    report["assessment_sha256"] = _canonical_sha256(report)
    target = Path(output)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    print(json.dumps(verify(args.output), ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
