from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest

from se.cfg import load_config
from se.runtime.sim import Simulation
from se.subject_vm import (
    ACTIVATION_PHASE_MASK,
    OP_LINEAR,
    OP_RETAINED_LINEAR,
    SUBJECT_VM_ACTIVATION_SCHEMA,
    SUBJECT_VM_INPUT_PORT_SCHEMA,
    SUBJECT_VM_OUTPUT_PORT_SCHEMA,
    SUBJECT_VM_REGION_NAMES,
    SUBJECT_VM_STAGE1_SCHEMA,
    SUBJECT_VM_STAGE2_SCHEMA,
    STAGE1_DEVICE_CONTRACT,
    SubjectVMActivationConfig,
    SubjectVMConfig,
    SubjectVMRegionConfig,
    SubjectVMRuntime,
    execute_activation,
)
from se.subject_vm.runtime import RUNTIME_SCHEMA_V1
from se.subject_vm.storage import STORAGE_SCHEMA_V1


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


def _stage1_config() -> SubjectVMConfig:
    return SubjectVMConfig(
        enabled=True,
        schema=SUBJECT_VM_STAGE1_SCHEMA,
        node_state_width=3,
        regions=_regions(),
    )


def _stage2_config() -> SubjectVMConfig:
    return SubjectVMConfig(
        enabled=True,
        schema=SUBJECT_VM_STAGE2_SCHEMA,
        node_state_width=3,
        regions=_regions(),
        activation=SubjectVMActivationConfig(
            schema=SUBJECT_VM_ACTIVATION_SCHEMA,
            input_port_schema=SUBJECT_VM_INPUT_PORT_SCHEMA,
            output_port_schema=SUBJECT_VM_OUTPUT_PORT_SCHEMA,
            activation_clip=8.0,
            output_clip=8.0,
        ),
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


def _runtime(cfg: SubjectVMConfig, capacity: int = 2) -> SubjectVMRuntime:
    entity_ids = np.arange(11, 11 + capacity, dtype=np.uint64)
    subject_ids = np.arange(101, 101 + capacity, dtype=np.uint64)
    return SubjectVMRuntime.initialize(
        cfg,
        entity_capacity=capacity,
        active_rows=np.arange(capacity, dtype=np.int32),
        entity_ids=entity_ids,
        subject_ids=subject_ids,
    )


def test_stage2_config_requires_frozen_role_neutral_port_contract() -> None:
    runtime = _runtime(_stage2_config(), capacity=1)
    assert runtime.activation_enabled is True
    assert runtime.device_contract.supported_execution_backends == ("cpu",)
    with pytest.raises(RuntimeError, match="does not support backend"):
        runtime.require_execution_backend("gpu")

    bad = replace(
        _stage2_config(),
        activation=replace(_stage2_config().activation, input_port_schema="trust-v1"),
    )
    with pytest.raises(ValueError, match="requires input ports"):
        from se.subject_vm import validate_subject_vm_config

        validate_subject_vm_config(bad)


def test_hand_built_graph_routes_bounded_deterministic_action_potential() -> None:
    runtime = _runtime(_stage2_config(), capacity=1)
    storage = runtime.storage
    assert storage is not None
    storage.node_expressed[0, :2] = True
    storage.node_operator_id[0, :2] = OP_LINEAR
    storage.node_activation_phase[0, 0] = 0
    storage.node_activation_phase[0, 1] = 1
    storage.node_input_port[0, 0] = 0
    storage.node_input_gate[0, 0] = 1.0
    storage.node_output_port[0, 1] = 3
    storage.node_output_gate[0, 1] = 1.0
    storage.edge_expressed[0, 0] = True
    storage.edge_source[0, 0] = 0
    storage.edge_target[0, 0] = 1
    storage.edge_forward_gate[0, 0] = 2.0
    storage.edge_bandwidth[0, 0] = 8.0
    storage.edge_phase_mask[0, 0] = ACTIVATION_PHASE_MASK

    inputs = np.zeros((1, 16), dtype=np.float32)
    inputs[0, 0] = 1.0
    result = execute_activation(
        storage,
        rows=np.array([0], dtype=np.int32),
        input_values=inputs,
        tick=0,
        output_width=8,
    )
    assert result.action_potentials[0, 3] == pytest.approx(2.0)
    assert np.count_nonzero(result.action_potentials) == 1
    assert result.usage.executed_nodes == 2
    assert result.usage.transmitted_edges == 1
    assert result.usage.output_contributions == 1
    assert np.array_equal(storage.eligibility_value, np.zeros_like(storage.eligibility_value))


def test_one_tick_edge_and_retained_operator_use_prior_state_only() -> None:
    runtime = _runtime(_stage2_config(), capacity=1)
    storage = runtime.storage
    assert storage is not None
    storage.node_expressed[0, 0] = True
    storage.node_operator_id[0, 0] = OP_RETAINED_LINEAR
    storage.node_retention[0, 0] = 0.5
    storage.node_input_port[0, 0] = 0
    storage.node_input_gate[0, 0] = 1.0
    storage.node_output_port[0, 0] = 0
    storage.node_output_gate[0, 0] = 1.0
    storage.edge_expressed[0, 0] = True
    storage.edge_source[0, 0] = 0
    storage.edge_target[0, 0] = 0
    storage.edge_forward_gate[0, 0] = 1.0
    storage.edge_bandwidth[0, 0] = 8.0
    storage.edge_delay[0, 0] = 1
    storage.edge_phase_mask[0, 0] = ACTIVATION_PHASE_MASK
    inputs = np.zeros((1, 16), dtype=np.float32)
    inputs[0, 0] = 1.0

    first = runtime.activate(rows=np.array([0]), input_values=inputs, tick=0, output_width=8)
    second = runtime.activate(rows=np.array([0]), input_values=inputs, tick=1, output_width=8)
    assert first.action_potentials[0, 0] == pytest.approx(1.0)
    assert second.action_potentials[0, 0] == pytest.approx(2.5)
    assert runtime.activation_accounting.activation_calls == 2
    assert runtime.activation_accounting.node_execution_units == 2
    assert runtime.activation_accounting.edge_transmission_units == 2


def test_zero_delay_edges_cannot_depend_on_same_or_later_phase() -> None:
    runtime = _runtime(_stage2_config(), capacity=1)
    storage = runtime.storage
    assert storage is not None
    storage.node_expressed[0, :2] = True
    storage.node_activation_phase[0, :2] = 0
    storage.edge_expressed[0, 0] = True
    storage.edge_source[0, 0] = 0
    storage.edge_target[0, 0] = 1
    storage.edge_bandwidth[0, 0] = 1.0
    storage.edge_phase_mask[0, 0] = ACTIVATION_PHASE_MASK
    with pytest.raises(ValueError, match="strictly increasing activation phase"):
        storage.validate_internal()


def test_stage2_empty_graph_remains_exactly_neutral(tmp_path: Path) -> None:
    disabled_cfg = replace(_small_config(_stage2_config()), subject_vm=SubjectVMConfig())
    disabled = Simulation(disabled_cfg, tmp_path / "disabled", backend="cpu")
    enabled = Simulation(_small_config(_stage2_config()), tmp_path / "enabled", backend="cpu")
    for _ in range(3):
        disabled.step()
        enabled.step()
    for name, value in vars(disabled.entities).items():
        if name == "cfg":
            continue
        other = getattr(enabled.entities, name)
        if isinstance(value, np.ndarray):
            assert np.array_equal(value, other), name
        else:
            assert value == other, name
    assert np.array_equal(disabled.action_counts, enabled.action_counts)
    assert enabled.subject_vm.activation_accounting.activation_calls == 0


def test_simulation_adapter_feeds_graph_potentials_into_existing_policy(tmp_path: Path) -> None:
    simulation = Simulation(_small_config(_stage2_config()), tmp_path / "active", backend="cpu")
    storage = simulation.subject_vm.storage
    assert storage is not None
    first_row = int(np.flatnonzero(simulation.entities.alive)[0])
    storage.node_expressed[first_row, 0] = True
    storage.node_operator_id[first_row, 0] = OP_LINEAR
    storage.node_input_port[first_row, 0] = 0
    storage.node_input_gate[first_row, 0] = 1.0
    storage.node_output_port[first_row, 0] = 3
    storage.node_output_gate[first_row, 0] = 2.0

    captured: list[np.ndarray | None] = []
    original = simulation.policy.decide

    def capture(*args, **kwargs):
        value = kwargs.get("subject_vm_potentials")
        captured.append(None if value is None else np.asarray(value).copy())
        return original(*args, **kwargs)

    simulation.policy.decide = capture  # type: ignore[method-assign]
    simulation.step()
    assert captured and captured[-1] is not None
    potentials = captured[-1]
    assert potentials is not None
    active = np.flatnonzero(simulation.entities.alive)
    batch_row = int(np.flatnonzero(active == first_row)[0])
    assert potentials[batch_row, 3] == pytest.approx(2.0)
    assert simulation.subject_vm.activation_accounting.activation_calls == 1
    assert simulation.subject_vm.activation_accounting.output_contribution_units == 1


def test_stage2_checkpoint_restores_state_and_accounting(tmp_path: Path) -> None:
    simulation = Simulation(_small_config(_stage2_config()), tmp_path / "source", backend="cpu")
    storage = simulation.subject_vm.storage
    assert storage is not None
    row = int(np.flatnonzero(simulation.entities.alive)[0])
    storage.node_expressed[row, 0] = True
    storage.node_input_port[row, 0] = 0
    storage.node_input_gate[row, 0] = 1.0
    storage.node_output_port[row, 0] = 0
    storage.node_output_gate[row, 0] = 1.0
    simulation.step()
    checkpoint = tmp_path / "stage2.sechk"
    simulation.save_full_checkpoint(checkpoint)
    restored = Simulation.from_checkpoint(checkpoint, tmp_path / "restored", backend="cpu")
    assert restored.subject_vm.storage is not None
    assert np.array_equal(restored.subject_vm.storage.node_state, storage.node_state)
    assert restored.subject_vm.activation_accounting == simulation.subject_vm.activation_accounting


def test_v0108_stage1_runtime_payload_upgrades_with_zero_activation_bindings() -> None:
    runtime = _runtime(_stage1_config(), capacity=1)
    assert runtime.storage is not None
    current = runtime.snapshot_state()
    assert current is not None
    current["schema"] = RUNTIME_SCHEMA_V1
    current["device_contract"] = STAGE1_DEVICE_CONTRACT.schema
    current.pop("activation_accounting")
    storage_payload = current["storage"]
    storage_payload["schema"] = STORAGE_SCHEMA_V1
    for name in (
        "node_bias",
        "node_retention",
        "node_input_port",
        "node_input_gate",
        "node_output_port",
        "node_output_gate",
    ):
        storage_payload["arrays"].pop(name)
    alive = np.array([True])
    entity_ids = np.array([11], dtype=np.uint64)
    subject_ids = np.array([101], dtype=np.uint64)
    restored = SubjectVMRuntime.restore(
        _stage1_config(),
        entity_capacity=1,
        payload=current,
        alive=alive,
        entity_ids=entity_ids,
        subject_ids=subject_ids,
    )
    assert restored.storage is not None
    assert np.all(restored.storage.node_input_port == -1)
    assert np.all(restored.storage.node_output_port == -1)
    assert restored.activation_accounting.activation_calls == 0
