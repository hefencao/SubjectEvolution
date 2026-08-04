"""语义中立的 Subject VM activation contribution 观测导出。

该模块只序列化权威 activation executor 已经使用的 node、edge 与 output
中间量。它不重新执行图、不生成随机数、不修改 graph state、action、
checkpoint 或 branch identity，也不把执行分解解释为因果归因或价值。
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
from typing import Any, Iterable

import numpy as np

from ..policy import Action
from ..subject_vm.activation import (
    OP_LINEAR,
    OP_RETAINED_LINEAR,
    OP_RETAINED_TANH,
    OP_TANH,
)
from ..subject_vm.activation_contribution import (
    SUBJECT_VM_ACTIVATION_CONTRIBUTION_SCHEMA,
    SubjectVMActivationContributionBatch,
)
from ..subject_vm.config import SUBJECT_VM_REGION_NAMES

SUBJECT_VM_ACTIVATION_CONTRIBUTION_TRACE_SCHEMA = (
    "se-subject-vm-activation-contribution-trace-v1"
)
SUBJECT_VM_ACTIVATION_CONTRIBUTION_TRACE_MANIFEST_SCHEMA = (
    "se-subject-vm-activation-contribution-trace-manifest-v1"
)


def _canonical_sha256(payload: dict[str, Any]) -> str:
    encoded = json.dumps(
        payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _operator_reconstruction(record: dict[str, Any]) -> tuple[float, float]:
    operator_id = int(record["operator_id"])
    accumulator = float(record["accumulator"])
    previous = float(record["previous_value"])
    retention = float(record["retention"])
    clip = float(record["activation_clip"])
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
        raise ValueError("activation contribution contains unsupported operator")
    return float(argument), float(np.clip(transformed, -clip, clip))


def _validate_record(record: dict[str, Any]) -> None:
    edges_by_target: dict[int, float] = {}
    for edge in record["edge_transmissions"]:
        target = int(edge["target_node_index"])
        edges_by_target[target] = edges_by_target.get(target, 0.0) + float(
            edge["bounded_contribution"]
        )
        raw = float(edge["source_value"]) * float(edge["forward_gate"])
        bounded = float(
            np.clip(raw, -float(edge["bandwidth"]), float(edge["bandwidth"]))
        )
        if not np.isclose(raw, edge["raw_contribution"], rtol=0.0, atol=1e-15):
            raise ValueError("activation edge raw contribution cannot be reconstructed")
        if not np.isclose(
            bounded, edge["bounded_contribution"], rtol=0.0, atol=1e-15
        ):
            raise ValueError("activation edge bounded contribution cannot be reconstructed")

    for node in record["node_activations"]:
        input_contribution = (
            0.0
            if int(node["input_port"]) < 0
            else float(node["input_value"]) * float(node["input_gate"])
        )
        incoming = edges_by_target.get(int(node["node_index"]), 0.0)
        accumulator = float(node["bias_value"]) + input_contribution + incoming
        if not np.isclose(
            input_contribution,
            node["input_contribution"],
            rtol=0.0,
            atol=1e-15,
        ):
            raise ValueError("activation node input contribution cannot be reconstructed")
        if not np.isclose(
            incoming,
            node["incoming_edge_contribution"],
            rtol=0.0,
            atol=1e-15,
        ):
            raise ValueError("activation node incoming contribution cannot be reconstructed")
        if not np.isclose(accumulator, node["accumulator"], rtol=0.0, atol=1e-15):
            raise ValueError("activation node accumulator cannot be reconstructed")
        argument, value = _operator_reconstruction(node)
        if not np.isclose(argument, node["operator_argument"], rtol=0.0, atol=1e-15):
            raise ValueError("activation operator argument cannot be reconstructed")
        if not np.isclose(value, node["node_value"], rtol=0.0, atol=1e-15):
            raise ValueError("activation node value cannot be reconstructed")

    output_width = len(Action)
    raw_ports = np.zeros(output_width, dtype=np.float32)
    for output in record["output_contributions"]:
        port = int(output["action_port"])
        before = np.float32(raw_ports[port])
        contribution = np.float32(output["float32_contribution"])
        raw_ports[port] += contribution
        if np.float32(output["port_running_sum_before"]) != before:
            raise ValueError("activation output running sum before mismatch")
        if np.float32(output["port_running_sum_after"]) != raw_ports[port]:
            raise ValueError("activation output running sum after mismatch")
    recorded_raw = np.asarray(record["raw_action_potentials"], dtype=np.float32)
    if not np.array_equal(raw_ports, recorded_raw):
        raise ValueError("activation action-port raw aggregation mismatch")
    expected = np.clip(
        raw_ports,
        -float(record["output_clip"]),
        float(record["output_clip"]),
    ).astype(np.float32)
    if not np.array_equal(
        expected, np.asarray(record["action_potentials"], dtype=np.float32)
    ):
        raise ValueError("activation action-port clipped aggregation mismatch")

    for entry in record["temporary_write_lineage"]:
        status = str(entry["status_name"])
        for target in entry["targets"]:
            if status == "guarded-live-pending" and not bool(
                target["current_matches_post"]
            ):
                raise ValueError("live temporary write is absent from activation parameter")
            if status == "read-only-control-pending" and not bool(
                target["current_matches_pre"]
            ):
                raise ValueError("control reservation altered activation parameter")


@dataclass(frozen=True)
class SubjectVMActivationContributionTraceSummary:
    event_count: int
    node_activation_count: int
    edge_transmission_count: int
    output_contribution_count: int
    temporary_write_entry_count: int
    first_tick: int | None
    last_tick: int | None
    trace_path: str
    trace_sha256: str
    manifest_path: str
    manifest_sha256: str


class SubjectVMActivationContributionTraceWriter:
    """流式写出一个 tick 中每个选定 subject 的完整 activation 分解。"""

    def __init__(
        self,
        output_dir: str | Path,
        *,
        metadata: dict[str, Any],
        subject_ids: Iterable[int] | None = None,
    ) -> None:
        root = Path(output_dir)
        root.mkdir(parents=True, exist_ok=True)
        self.trace_path = root / "subject_vm_activation_contribution_trace.jsonl"
        self.manifest_path = (
            root / "subject_vm_activation_contribution_trace_manifest.json"
        )
        self._handle = self.trace_path.open("w", encoding="utf-8", newline="\n")
        self.metadata = json.loads(json.dumps(metadata, ensure_ascii=False))
        self.subject_ids = (
            None
            if subject_ids is None
            else frozenset(int(value) for value in subject_ids)
        )
        self.event_count = 0
        self.node_activation_count = 0
        self.edge_transmission_count = 0
        self.output_contribution_count = 0
        self.temporary_write_entry_count = 0
        self.first_tick: int | None = None
        self.last_tick: int | None = None
        self._closed = False
        self._write(
            {
                "schema": SUBJECT_VM_ACTIVATION_CONTRIBUTION_TRACE_SCHEMA,
                "record_type": "header",
                "activation_record_schema": SUBJECT_VM_ACTIVATION_CONTRIBUTION_SCHEMA,
                "region_order": list(SUBJECT_VM_REGION_NAMES),
                "action_order": [action.name for action in Action],
                "action_ids": [int(action) for action in Action],
                "metadata": self.metadata,
                "semantic_feedback": False,
                "checkpoint_state_member": False,
                "branch_identity_member": False,
                "causal_attribution": False,
            }
        )

    def _write(self, payload: dict[str, Any]) -> None:
        self._handle.write(
            json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
        )
        self._handle.write("\n")

    def record(
        self,
        batch: SubjectVMActivationContributionBatch,
        *,
        world_rows: np.ndarray,
        entity_ids: np.ndarray,
        subject_ids: np.ndarray,
        event_ids: np.ndarray,
    ) -> None:
        if self._closed:
            raise RuntimeError("activation contribution trace writer is closed")
        rows = np.asarray(world_rows, dtype=np.int32)
        entities = np.asarray(entity_ids, dtype=np.uint64)
        subjects = np.asarray(subject_ids, dtype=np.uint64)
        events = np.asarray(event_ids, dtype=np.uint64)
        if not (rows.shape == entities.shape == subjects.shape == events.shape):
            raise ValueError("activation contribution identity vectors do not align")
        identity_by_row = {
            int(row): (int(entity), int(subject), int(event))
            for row, entity, subject, event in zip(
                rows, entities, subjects, events, strict=True
            )
        }
        if batch.rows.shape != (len(batch.records),):
            raise ValueError("activation contribution batch rows do not align")
        for row, record in zip(batch.rows.tolist(), batch.records, strict=True):
            identity = identity_by_row.get(int(row))
            if identity is None:
                raise ValueError("activation contribution row lacks intent identity")
            entity_id, subject_id, event_id = identity
            if self.subject_ids is not None and subject_id not in self.subject_ids:
                continue
            _validate_record(record)
            node_count = len(record["node_activations"])
            edge_count = len(record["edge_transmissions"])
            output_count = len(record["output_contributions"])
            write_count = len(record["temporary_write_lineage"])
            payload = {
                "schema": SUBJECT_VM_ACTIVATION_CONTRIBUTION_TRACE_SCHEMA,
                "record_type": "event",
                "tick": int(batch.tick),
                "world_row": int(row),
                "event_id": event_id,
                "entity_id": entity_id,
                "subject_id": subject_id,
                **record,
            }
            self._write(payload)
            self.event_count += 1
            self.node_activation_count += node_count
            self.edge_transmission_count += edge_count
            self.output_contribution_count += output_count
            self.temporary_write_entry_count += write_count
            self.first_tick = (
                int(batch.tick)
                if self.first_tick is None
                else min(self.first_tick, int(batch.tick))
            )
            self.last_tick = (
                int(batch.tick)
                if self.last_tick is None
                else max(self.last_tick, int(batch.tick))
            )

    def close(self) -> SubjectVMActivationContributionTraceSummary:
        if self._closed:
            manifest = json.loads(self.manifest_path.read_text(encoding="utf-8"))
            return SubjectVMActivationContributionTraceSummary(
                event_count=int(manifest["event_count"]),
                node_activation_count=int(manifest["node_activation_count"]),
                edge_transmission_count=int(manifest["edge_transmission_count"]),
                output_contribution_count=int(
                    manifest["output_contribution_count"]
                ),
                temporary_write_entry_count=int(
                    manifest["temporary_write_entry_count"]
                ),
                first_tick=manifest["first_tick"],
                last_tick=manifest["last_tick"],
                trace_path=str(self.trace_path.resolve()),
                trace_sha256=str(manifest["trace_sha256"]),
                manifest_path=str(self.manifest_path.resolve()),
                manifest_sha256=str(manifest["manifest_sha256"]),
            )
        self._handle.flush()
        self._handle.close()
        trace_sha = _file_sha256(self.trace_path)
        manifest: dict[str, Any] = {
            "schema": SUBJECT_VM_ACTIVATION_CONTRIBUTION_TRACE_MANIFEST_SCHEMA,
            "trace_schema": SUBJECT_VM_ACTIVATION_CONTRIBUTION_TRACE_SCHEMA,
            "activation_record_schema": SUBJECT_VM_ACTIVATION_CONTRIBUTION_SCHEMA,
            "trace_path": str(self.trace_path.resolve()),
            "trace_sha256": trace_sha,
            "event_count": int(self.event_count),
            "node_activation_count": int(self.node_activation_count),
            "edge_transmission_count": int(self.edge_transmission_count),
            "output_contribution_count": int(self.output_contribution_count),
            "temporary_write_entry_count": int(self.temporary_write_entry_count),
            "first_tick": self.first_tick,
            "last_tick": self.last_tick,
            "metadata": self.metadata,
            "semantic_feedback": False,
            "checkpoint_state_member": False,
            "branch_identity_member": False,
            "causal_attribution": False,
        }
        manifest["manifest_sha256"] = _canonical_sha256(manifest)
        self.manifest_path.write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        self._closed = True
        return SubjectVMActivationContributionTraceSummary(
            event_count=self.event_count,
            node_activation_count=self.node_activation_count,
            edge_transmission_count=self.edge_transmission_count,
            output_contribution_count=self.output_contribution_count,
            temporary_write_entry_count=self.temporary_write_entry_count,
            first_tick=self.first_tick,
            last_tick=self.last_tick,
            trace_path=str(self.trace_path.resolve()),
            trace_sha256=trace_sha,
            manifest_path=str(self.manifest_path.resolve()),
            manifest_sha256=str(manifest["manifest_sha256"]),
        )


__all__ = [
    "SUBJECT_VM_ACTIVATION_CONTRIBUTION_TRACE_MANIFEST_SCHEMA",
    "SUBJECT_VM_ACTIVATION_CONTRIBUTION_TRACE_SCHEMA",
    "SubjectVMActivationContributionTraceSummary",
    "SubjectVMActivationContributionTraceWriter",
]
