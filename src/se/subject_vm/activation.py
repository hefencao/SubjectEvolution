"""Deterministic CPU reference executor for Subject VM activation.

Stage 3A adds a graph-produced continuous token readout. Stage 3B-1 may leave
short-lived local eligibility on graph-selected executed nodes and transmitted
edges. The executor does not retain a persistent node/edge path, assign event
value, update parameters, feed eligibility into the same action, or consume
random numbers.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .eligibility import (
    SubjectVMLocalEligibilityUsage,
    advance_local_eligibility,
    mark_edge_eligibility,
    mark_node_eligibility,
)
from .storage import ACTIVATION_PHASE_MASK, SubjectVMStorage
from .trace import SubjectVMThoughtTokenBatch

OP_LINEAR = 0
OP_TANH = 1
OP_RETAINED_LINEAR = 2
OP_RETAINED_TANH = 3


@dataclass(frozen=True)
class SubjectVMActivationUsage:
    tick: int
    active_rows: int
    structural_nodes: int
    structural_edges: int
    executed_nodes: int
    transmitted_edges: int
    cross_region_transmissions: int
    output_contributions: int
    token_contributions: int
    retained_state_values: int


@dataclass(frozen=True)
class SubjectVMActivationResult:
    action_potentials: np.ndarray
    usage: SubjectVMActivationUsage
    thought_tokens: SubjectVMThoughtTokenBatch | None = None
    eligibility_usage: SubjectVMLocalEligibilityUsage | None = None


def _operator_output(
    operator_id: int,
    accumulator: float,
    previous: float,
    retention: float,
    clip: float,
) -> float:
    if operator_id == OP_LINEAR:
        value = accumulator
    elif operator_id == OP_TANH:
        value = clip * np.tanh(accumulator / clip)
    elif operator_id == OP_RETAINED_LINEAR:
        value = retention * previous + accumulator
    elif operator_id == OP_RETAINED_TANH:
        value = clip * np.tanh((retention * previous + accumulator) / clip)
    else:
        raise ValueError(f"unsupported Subject VM operator ID: {operator_id}")
    return float(np.clip(value, -clip, clip))


def execute_activation(
    storage: SubjectVMStorage,
    *,
    rows: np.ndarray,
    input_values: np.ndarray,
    tick: int,
    output_width: int,
) -> SubjectVMActivationResult:
    """Execute bounded activation and optional graph-defined token readout."""
    normalized_rows = storage._rows(rows)
    inputs = np.asarray(input_values, dtype=np.float32)
    if inputs.ndim != 2 or inputs.shape[0] != normalized_rows.size:
        raise ValueError("subject_vm input batch must align with active rows")
    if inputs.shape[1] != 16:
        raise ValueError("subject_vm input batch does not match approved port width")
    if output_width != 8:
        raise ValueError("subject_vm output width does not match approved action ports")
    if np.any(~np.isfinite(inputs)):
        raise ValueError("subject_vm input batch must contain finite values")
    if normalized_rows.size and np.any(~storage.occupied[normalized_rows]):
        raise ValueError("subject_vm activation rows must be occupied")
    storage.validate_internal()
    eligibility_usage = advance_local_eligibility(
        storage, rows=normalized_rows, tick=int(tick)
    )

    activation_cfg = storage.cfg.activation
    activation_clip = float(activation_cfg.activation_clip)
    output_clip = float(activation_cfg.output_clip)
    potentials = np.zeros((normalized_rows.size, output_width), dtype=np.float32)
    token_width = int(storage.cfg.trace.token_width) if storage.cfg.trace_enabled else 0
    token_clip = float(storage.cfg.trace.token_clip) if storage.cfg.trace_enabled else 0.0
    tokens = (
        np.zeros((normalized_rows.size, token_width), dtype=np.float32)
        if token_width
        else None
    )
    emitted = (
        np.zeros(normalized_rows.size, dtype=bool) if token_width else None
    )

    structural_nodes = int(np.count_nonzero(storage.node_expressed[normalized_rows]))
    structural_edges = int(np.count_nonzero(storage.edge_expressed[normalized_rows]))
    executed_nodes = 0
    transmitted_edges = 0
    cross_region_transmissions = 0
    output_contributions = 0
    token_contributions = 0

    for batch_index, row in enumerate(normalized_rows.tolist()):
        expressed = storage.node_expressed[row]
        if not np.any(expressed):
            continue
        previous = storage.node_state[row, :, 0].astype(np.float64, copy=True)
        current = previous.copy()
        periods = storage.node_activation_period[row]
        due = np.zeros_like(expressed)
        expressed_nodes = np.flatnonzero(expressed)
        due[expressed_nodes] = (
            int(tick) % periods[expressed_nodes].astype(np.int64)
        ) == 0
        phases = np.unique(storage.node_activation_phase[row, due])

        for phase in np.sort(phases):
            phase_nodes = np.flatnonzero(
                due & (storage.node_activation_phase[row] == phase)
            )
            for node in phase_nodes.tolist():
                accumulator = float(storage.node_bias[row, node])
                input_port = int(storage.node_input_port[row, node])
                if input_port >= 0:
                    accumulator += float(storage.node_input_gate[row, node]) * float(
                        inputs[batch_index, input_port]
                    )

                if storage.edge_capacity:
                    incoming = np.flatnonzero(
                        storage.edge_expressed[row]
                        & (storage.edge_target[row] == node)
                        & (
                            storage.edge_phase_mask[row]
                            & ACTIVATION_PHASE_MASK
                            != 0
                        )
                    )
                    for edge in incoming.tolist():
                        source = int(storage.edge_source[row, edge])
                        source_value = (
                            current[source]
                            if int(storage.edge_delay[row, edge]) == 0
                            else previous[source]
                        )
                        contribution = source_value * float(
                            storage.edge_forward_gate[row, edge]
                        )
                        bandwidth = float(storage.edge_bandwidth[row, edge])
                        bounded_contribution = float(
                            np.clip(contribution, -bandwidth, bandwidth)
                        )
                        accumulator += bounded_contribution
                        transmitted_edges += 1
                        if mark_edge_eligibility(
                            storage,
                            row=row,
                            edge=edge,
                            local_activity=bounded_contribution,
                        ):
                            assert eligibility_usage is not None
                            eligibility_usage.edge_marks += 1
                        if (
                            storage.node_region[row, source]
                            != storage.node_region[row, node]
                        ):
                            cross_region_transmissions += 1

                current[node] = _operator_output(
                    int(storage.node_operator_id[row, node]),
                    accumulator,
                    previous[node],
                    float(storage.node_retention[row, node]),
                    activation_clip,
                )
                executed_nodes += 1
                if mark_node_eligibility(
                    storage, row=row, node=node, local_activity=float(current[node])
                ):
                    assert eligibility_usage is not None
                    eligibility_usage.node_marks += 1

        storage.node_state[row, expressed, 0] = current[expressed].astype(np.float32)
        output_nodes = np.flatnonzero(expressed & (storage.node_output_port[row] >= 0))
        for node in output_nodes.tolist():
            port = int(storage.node_output_port[row, node])
            potentials[batch_index, port] += np.float32(
                current[node] * float(storage.node_output_gate[row, node])
            )
            output_contributions += 1
        np.clip(
            potentials[batch_index],
            -output_clip,
            output_clip,
            out=potentials[batch_index],
        )

        if tokens is not None and emitted is not None:
            token_nodes = np.flatnonzero(
                expressed & (storage.node_trace_port[row] >= 0)
            )
            if token_nodes.size:
                emitted[batch_index] = True
            for node in token_nodes.tolist():
                port = int(storage.node_trace_port[row, node])
                tokens[batch_index, port] += np.float32(
                    current[node] * float(storage.node_trace_gate[row, node])
                )
                token_contributions += 1
            np.clip(
                tokens[batch_index],
                -token_clip,
                token_clip,
                out=tokens[batch_index],
            )

    usage = SubjectVMActivationUsage(
        tick=int(tick),
        active_rows=int(normalized_rows.size),
        structural_nodes=structural_nodes,
        structural_edges=structural_edges,
        executed_nodes=executed_nodes,
        transmitted_edges=transmitted_edges,
        cross_region_transmissions=cross_region_transmissions,
        output_contributions=output_contributions,
        token_contributions=token_contributions,
        retained_state_values=int(np.count_nonzero(storage.node_state[normalized_rows])),
    )
    thought_tokens = None
    if tokens is not None and emitted is not None:
        thought_tokens = SubjectVMThoughtTokenBatch(
            tick=int(tick),
            rows=normalized_rows.copy(),
            emitted=emitted,
            tokens=tokens,
            action_potentials=potentials.copy(),
        )
    return SubjectVMActivationResult(
        action_potentials=potentials,
        usage=usage,
        thought_tokens=thought_tokens,
        eligibility_usage=eligibility_usage,
    )


__all__ = [
    "OP_LINEAR",
    "OP_RETAINED_LINEAR",
    "OP_RETAINED_TANH",
    "OP_TANH",
    "SubjectVMActivationResult",
    "SubjectVMActivationUsage",
    "execute_activation",
]
