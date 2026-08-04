"""Deterministic CPU reference executor for Subject VM activation.

Stage 3A adds a graph-produced continuous token readout. Stage 3B-1 may leave
short-lived local eligibility on graph-selected executed nodes and transmitted
edges. The executor does not retain a persistent node/edge path, assign event
value, update parameters, feed eligibility into the same action, or consume
random numbers.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np

from .activation_contribution import (
    SubjectVMActivationContributionBatch,
)
from .binding import (
    SubjectVMTargetCandidateBatch,
    snapshot_pre_activation_target_candidates,
)
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
    target_candidates: SubjectVMTargetCandidateBatch | None = None
    contribution_trace: SubjectVMActivationContributionBatch | None = None


def _operator_values(
    operator_id: int,
    accumulator: float,
    previous: float,
    retention: float,
    clip: float,
) -> tuple[float, float, float]:
    if operator_id == OP_LINEAR:
        argument = accumulator
        transformed = argument
    elif operator_id == OP_TANH:
        argument = accumulator
        transformed = clip * np.tanh(argument / clip)
    elif operator_id == OP_RETAINED_LINEAR:
        argument = retention * previous + accumulator
        transformed = argument
    elif operator_id == OP_RETAINED_TANH:
        argument = retention * previous + accumulator
        transformed = clip * np.tanh(argument / clip)
    else:
        raise ValueError(f"unsupported Subject VM operator ID: {operator_id}")
    value = float(np.clip(transformed, -clip, clip))
    return float(argument), float(transformed), value


def _operator_output(
    operator_id: int,
    accumulator: float,
    previous: float,
    retention: float,
    clip: float,
) -> float:
    return _operator_values(
        operator_id, accumulator, previous, retention, clip
    )[2]


def execute_activation(
    storage: SubjectVMStorage,
    *,
    rows: np.ndarray,
    input_values: np.ndarray,
    tick: int,
    output_width: int,
    contribution_trace_rows: np.ndarray | None = None,
    temporary_write_lineage_by_row: dict[int, list[dict[str, Any]]] | None = None,
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
    capture_rows = (
        None
        if contribution_trace_rows is None
        else storage._rows(contribution_trace_rows)
    )
    if capture_rows is not None and np.any(~np.isin(capture_rows, normalized_rows)):
        raise ValueError("subject_vm contribution trace rows must be active rows")
    capture_row_set = (
        frozenset() if capture_rows is None else frozenset(capture_rows.tolist())
    )
    lineage_by_row = temporary_write_lineage_by_row or {}
    storage.validate_internal()
    eligibility_usage = advance_local_eligibility(
        storage, rows=normalized_rows, tick=int(tick)
    )
    target_candidates = (
        snapshot_pre_activation_target_candidates(
            storage,
            rows=normalized_rows,
            tick=int(tick),
            cfg=storage.cfg.target_binding,
        )
        if storage.cfg.target_binding_enabled
        else None
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
    contribution_records: list[dict[str, Any]] = []
    contribution_rows: list[int] = []

    for batch_index, row in enumerate(normalized_rows.tolist()):
        capture = row in capture_row_set
        node_records: list[dict[str, Any]] = []
        edge_records: list[dict[str, Any]] = []
        output_records: list[dict[str, Any]] = []
        expressed = storage.node_expressed[row]
        if not np.any(expressed):
            if capture:
                contribution_rows.append(int(row))
                contribution_records.append(
                    {
                        "world_row": int(row),
                        "input_values": [float(value) for value in inputs[batch_index]],
                        "temporary_write_lineage": list(lineage_by_row.get(int(row), [])),
                        "node_activations": [],
                        "edge_transmissions": [],
                        "output_contributions": [],
                        "raw_action_potentials": [0.0] * output_width,
                        "action_potentials": [0.0] * output_width,
                        "output_clip": output_clip,
                    }
                )
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
                bias_value = float(storage.node_bias[row, node])
                accumulator = bias_value
                input_port = int(storage.node_input_port[row, node])
                input_value = 0.0
                input_gate = 0.0
                input_contribution = 0.0
                if input_port >= 0:
                    input_value = float(inputs[batch_index, input_port])
                    input_gate = float(storage.node_input_gate[row, node])
                    input_contribution = input_gate * input_value
                    accumulator += input_contribution

                incoming_total = 0.0
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
                        delay = int(storage.edge_delay[row, edge])
                        source_value = (
                            current[source] if delay == 0 else previous[source]
                        )
                        forward_gate = float(storage.edge_forward_gate[row, edge])
                        contribution = source_value * forward_gate
                        bandwidth = float(storage.edge_bandwidth[row, edge])
                        bounded_contribution = float(
                            np.clip(contribution, -bandwidth, bandwidth)
                        )
                        accumulator += bounded_contribution
                        incoming_total += bounded_contribution
                        transmitted_edges += 1
                        if capture:
                            edge_records.append(
                                {
                                    "edge_index": int(edge),
                                    "edge_id": int(storage.edge_id[row, edge]),
                                    "source_node_index": source,
                                    "source_node_id": int(storage.node_id[row, source]),
                                    "target_node_index": int(node),
                                    "target_node_id": int(storage.node_id[row, node]),
                                    "source_region": int(storage.node_region[row, source]),
                                    "target_region": int(storage.node_region[row, node]),
                                    "target_phase": int(phase),
                                    "delay": delay,
                                    "source_value": float(source_value),
                                    "forward_gate": forward_gate,
                                    "bandwidth": bandwidth,
                                    "raw_contribution": float(contribution),
                                    "bounded_contribution": bounded_contribution,
                                    "bandwidth_clip_applied": not np.isclose(
                                        contribution, bounded_contribution, rtol=0.0, atol=1e-12
                                    ),
                                }
                            )
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

                operator_id = int(storage.node_operator_id[row, node])
                retention = float(storage.node_retention[row, node])
                operator_argument, operator_transformed, node_value = _operator_values(
                    operator_id,
                    accumulator,
                    previous[node],
                    retention,
                    activation_clip,
                )
                current[node] = node_value
                if capture:
                    node_records.append(
                        {
                            "node_index": int(node),
                            "node_id": int(storage.node_id[row, node]),
                            "region": int(storage.node_region[row, node]),
                            "phase": int(phase),
                            "operator_id": operator_id,
                            "previous_value": float(previous[node]),
                            "retention": retention,
                            "retention_contribution": (
                                retention * float(previous[node])
                                if operator_id in {OP_RETAINED_LINEAR, OP_RETAINED_TANH}
                                else 0.0
                            ),
                            "bias_value": bias_value,
                            "input_port": input_port,
                            "input_value": input_value if input_port >= 0 else None,
                            "input_gate": input_gate,
                            "input_contribution": input_contribution,
                            "incoming_edge_contribution": float(incoming_total),
                            "accumulator": float(accumulator),
                            "operator_argument": operator_argument,
                            "operator_transformed": operator_transformed,
                            "node_value": float(node_value),
                            "activation_clip": activation_clip,
                            "activation_clip_applied": not np.isclose(
                                operator_transformed, node_value, rtol=0.0, atol=1e-12
                            ),
                        }
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
            gate = float(storage.node_output_gate[row, node])
            raw_contribution = float(current[node]) * gate
            contribution = np.float32(raw_contribution)
            before = np.float32(potentials[batch_index, port])
            potentials[batch_index, port] += contribution
            after = np.float32(potentials[batch_index, port])
            if capture:
                output_records.append(
                    {
                        "node_index": int(node),
                        "node_id": int(storage.node_id[row, node]),
                        "region": int(storage.node_region[row, node]),
                        "action_port": port,
                        "node_value": float(current[node]),
                        "output_gate": gate,
                        "raw_contribution": raw_contribution,
                        "float32_contribution": float(contribution),
                        "port_running_sum_before": float(before),
                        "port_running_sum_after": float(after),
                    }
                )
            output_contributions += 1
        raw_action_potentials = potentials[batch_index].copy()
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

        if capture:
            contribution_rows.append(int(row))
            contribution_records.append(
                {
                    "world_row": int(row),
                    "input_values": [float(value) for value in inputs[batch_index]],
                    "temporary_write_lineage": list(lineage_by_row.get(int(row), [])),
                    "node_activations": node_records,
                    "edge_transmissions": edge_records,
                    "output_contributions": output_records,
                    "raw_action_potentials": [
                        float(value) for value in raw_action_potentials.tolist()
                    ],
                    "action_potentials": [
                        float(value) for value in potentials[batch_index].tolist()
                    ],
                    "output_clip": output_clip,
                }
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
    contribution_trace = None
    if capture_rows is not None:
        contribution_trace = SubjectVMActivationContributionBatch(
            tick=int(tick),
            rows=np.asarray(contribution_rows, dtype=np.int32),
            records=tuple(contribution_records),
        )
    return SubjectVMActivationResult(
        action_potentials=potentials,
        usage=usage,
        thought_tokens=thought_tokens,
        eligibility_usage=eligibility_usage,
        target_candidates=target_candidates,
        contribution_trace=contribution_trace,
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
