"""Simulation 观测输出生命周期。

本模块统一拥有 trajectory、categorical sampling trace 与 Subject VM
activation contribution trace。所有 writer 都是运行外观测设施，不属于
checkpoint、branch identity、配置身份或演化状态。
"""
from __future__ import annotations

import copy
from pathlib import Path
from typing import Any

import numpy as np

from ..policy import PolicyDecision
from ..subject_vm.activation_contribution import (
    SubjectVMActivationContributionBatch,
)
from .categorical_sampling_trace import CategoricalSamplingTraceWriter
from .subject_vm_activation_contribution_trace import (
    SubjectVMActivationContributionTraceWriter,
)


class RuntimeObservationMixin:
    """管理观测 writer 与同 tick 的临时 join，不参与语义状态。"""

    def _initialize_observation_outputs(self) -> None:
        self._trajectory_file = None
        if self.cfg.run.trajectory_subject_ids:
            self._trajectory_file = (
                self.output_dir / "trajectory.jsonl"
            ).open("w", encoding="utf-8")
        self._categorical_sampling_trace_writer: (
            CategoricalSamplingTraceWriter | None
        ) = None
        self._categorical_sampling_trace_summary = None
        self._subject_vm_activation_contribution_trace_writer: (
            SubjectVMActivationContributionTraceWriter | None
        ) = None
        self._subject_vm_activation_contribution_trace_summary = None
        self._pending_subject_vm_activation_contribution_trace: (
            SubjectVMActivationContributionBatch | None
        ) = None

    def _observation_metadata(
        self, metadata: dict[str, object] | None
    ) -> dict[str, object]:
        payload: dict[str, object] = {
            "run_seed": int(self.cfg.run.seed),
            "requested_backend": str(self.requested_backend),
            "execution_backend": str(self.execution_backend),
            "checkpoint_lineage": copy.deepcopy(self.checkpoint_lineage),
        }
        if metadata:
            payload.update(copy.deepcopy(metadata))
        return payload

    @property
    def categorical_sampling_trace_enabled(self) -> bool:
        return self._categorical_sampling_trace_writer is not None

    def enable_categorical_sampling_trace(
        self,
        *,
        metadata: dict[str, object] | None = None,
        subject_ids: tuple[int, ...] | None = None,
    ) -> Path:
        if self._categorical_sampling_trace_writer is not None:
            raise RuntimeError("categorical sampling trace is already enabled")
        self._categorical_sampling_trace_writer = CategoricalSamplingTraceWriter(
            self.output_dir,
            metadata=self._observation_metadata(metadata),
            subject_ids=subject_ids,
        )
        return self._categorical_sampling_trace_writer.trace_path

    def _record_categorical_sampling_trace(
        self,
        *,
        active: np.ndarray,
        entities: Any,
        intents: Any,
        decision: PolicyDecision,
    ) -> None:
        writer = self._categorical_sampling_trace_writer
        if writer is None or int(active.size) == 0:
            return
        writer.record(
            tick=int(self.tick),
            world_rows=np.asarray(active, dtype=np.int32),
            entity_ids=np.asarray(entities.entity_id[active], dtype=np.uint64),
            subject_ids=np.asarray(
                entities.primary_subject_id[active], dtype=np.uint64
            ),
            event_ids=np.asarray(intents.intent_id, dtype=np.uint64),
            decision=decision,
        )

    @property
    def subject_vm_activation_contribution_trace_enabled(self) -> bool:
        return self._subject_vm_activation_contribution_trace_writer is not None

    def enable_subject_vm_activation_contribution_trace(
        self,
        *,
        metadata: dict[str, object] | None = None,
        subject_ids: tuple[int, ...] | None = None,
    ) -> Path:
        if self._subject_vm_activation_contribution_trace_writer is not None:
            raise RuntimeError(
                "subject_vm activation contribution trace is already enabled"
            )
        self._subject_vm_activation_contribution_trace_writer = (
            SubjectVMActivationContributionTraceWriter(
                self.output_dir,
                metadata=self._observation_metadata(metadata),
                subject_ids=subject_ids,
            )
        )
        return self._subject_vm_activation_contribution_trace_writer.trace_path

    def _subject_vm_activation_contribution_rows(
        self, active: np.ndarray
    ) -> np.ndarray | None:
        writer = self._subject_vm_activation_contribution_trace_writer
        if writer is None:
            return None
        rows = np.asarray(active, dtype=np.int32)
        if writer.subject_ids is None or rows.size == 0:
            return rows.copy()
        subjects = np.asarray(
            self.entities.primary_subject_id[rows], dtype=np.uint64
        )
        selected = np.fromiter(
            (int(value) in writer.subject_ids for value in subjects.tolist()),
            dtype=bool,
            count=rows.size,
        )
        return rows[selected]

    def _stage_subject_vm_activation_contribution_trace(
        self, batch: SubjectVMActivationContributionBatch | None
    ) -> None:
        if self._subject_vm_activation_contribution_trace_writer is None:
            self._pending_subject_vm_activation_contribution_trace = None
            return
        if self._pending_subject_vm_activation_contribution_trace is not None:
            raise RuntimeError(
                "previous Subject VM activation contribution trace was not joined"
            )
        self._pending_subject_vm_activation_contribution_trace = batch

    def _record_policy_observation_traces(
        self,
        *,
        active: np.ndarray,
        entities: Any,
        intents: Any,
        decision: PolicyDecision,
    ) -> None:
        self._record_subject_vm_activation_contribution_trace(
            active=active, entities=entities, intents=intents
        )
        self._record_categorical_sampling_trace(
            active=active, entities=entities, intents=intents, decision=decision
        )

    def _record_subject_vm_activation_contribution_trace(
        self, *, active: np.ndarray, entities: Any, intents: Any
    ) -> None:
        writer = self._subject_vm_activation_contribution_trace_writer
        batch = self._pending_subject_vm_activation_contribution_trace
        self._pending_subject_vm_activation_contribution_trace = None
        if writer is None or batch is None or len(batch.records) == 0:
            return
        writer.record(
            batch,
            world_rows=np.asarray(active, dtype=np.int32),
            entity_ids=np.asarray(entities.entity_id[active], dtype=np.uint64),
            subject_ids=np.asarray(
                entities.primary_subject_id[active], dtype=np.uint64
            ),
            event_ids=np.asarray(intents.intent_id, dtype=np.uint64),
        )

    def _close_observation_outputs(self) -> None:
        if self._pending_subject_vm_activation_contribution_trace is not None:
            raise RuntimeError(
                "Subject VM activation contribution trace closed before intent join"
            )
        if self._trajectory_file is not None:
            self._trajectory_file.close()
        if self._categorical_sampling_trace_writer is not None:
            self._categorical_sampling_trace_summary = (
                self._categorical_sampling_trace_writer.close()
            )
        if self._subject_vm_activation_contribution_trace_writer is not None:
            self._subject_vm_activation_contribution_trace_summary = (
                self._subject_vm_activation_contribution_trace_writer.close()
            )


__all__ = ["RuntimeObservationMixin"]
