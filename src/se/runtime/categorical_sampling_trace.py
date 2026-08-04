"""语义中立的 categorical sampling 观测导出。

该模块只消费 policy 已经计算出的采样中间量。它不生成随机数、不修改
logits、mask、概率、action、checkpoint state 或 branch identity。
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
from typing import Any, Iterable

import numpy as np

from ..backend import to_numpy
from ..policy import Action, PolicyDecision

CATEGORICAL_SAMPLING_TRACE_SCHEMA = "se-categorical-sampling-trace-v1"
CATEGORICAL_SAMPLING_TRACE_MANIFEST_SCHEMA = (
    "se-categorical-sampling-trace-manifest-v1"
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


def _masked_logits_row(values: np.ndarray, mask: np.ndarray) -> list[float | None]:
    return [float(value) if bool(valid) else None for value, valid in zip(values, mask, strict=True)]


@dataclass(frozen=True)
class CategoricalSamplingTraceSummary:
    event_count: int
    first_tick: int | None
    last_tick: int | None
    trace_path: str
    trace_sha256: str
    manifest_path: str
    manifest_sha256: str


class CategoricalSamplingTraceWriter:
    """把 exact categorical kernel 的既有中间量流式写入 JSONL。"""

    def __init__(
        self,
        output_dir: str | Path,
        *,
        metadata: dict[str, Any],
        subject_ids: Iterable[int] | None = None,
    ) -> None:
        root = Path(output_dir)
        root.mkdir(parents=True, exist_ok=True)
        self.trace_path = root / "categorical_sampling_trace.jsonl"
        self.manifest_path = root / "categorical_sampling_trace_manifest.json"
        self._handle = self.trace_path.open("w", encoding="utf-8", newline="\n")
        self.metadata = json.loads(json.dumps(metadata, ensure_ascii=False))
        self.subject_ids = (
            None
            if subject_ids is None
            else frozenset(int(value) for value in subject_ids)
        )
        self.event_count = 0
        self.first_tick: int | None = None
        self.last_tick: int | None = None
        self._closed = False
        header = {
            "schema": CATEGORICAL_SAMPLING_TRACE_SCHEMA,
            "record_type": "header",
            "action_order": [action.name for action in Action],
            "action_ids": [int(action) for action in Action],
            "metadata": self.metadata,
            "semantic_feedback": False,
            "checkpoint_state_member": False,
        }
        self._write(header)

    def _write(self, payload: dict[str, Any]) -> None:
        self._handle.write(json.dumps(payload, ensure_ascii=False, separators=(",", ":")))
        self._handle.write("\n")

    def record(
        self,
        *,
        tick: int,
        world_rows: np.ndarray,
        entity_ids: np.ndarray,
        subject_ids: np.ndarray,
        event_ids: np.ndarray,
        decision: PolicyDecision,
    ) -> None:
        if self._closed:
            raise RuntimeError("categorical sampling trace writer is closed")
        trace = decision.categorical_sampling_trace
        if trace is None:
            raise ValueError("policy decision lacks categorical sampling trace")
        rows = np.asarray(world_rows, dtype=np.int32)
        entities = np.asarray(entity_ids, dtype=np.uint64)
        subjects = np.asarray(subject_ids, dtype=np.uint64)
        events = np.asarray(event_ids, dtype=np.uint64)
        action = np.asarray(to_numpy(decision.action), dtype=np.int16)
        selected_probability = np.asarray(to_numpy(decision.probability), dtype=np.float32)
        mask = np.asarray(to_numpy(decision.action_mask), dtype=bool)
        masked_logits = np.asarray(to_numpy(trace.masked_logits), dtype=np.float64)
        probabilities = np.asarray(to_numpy(trace.probabilities), dtype=np.float64)
        cdf = np.asarray(to_numpy(trace.cumulative_probabilities), dtype=np.float64)
        draws = np.asarray(to_numpy(trace.uniform_draw), dtype=np.float64)
        keys = np.asarray(to_numpy(trace.random_key), dtype=np.uint64)
        lower = np.asarray(to_numpy(trace.cdf_lower), dtype=np.float64)
        upper = np.asarray(to_numpy(trace.cdf_upper), dtype=np.float64)
        count = int(rows.size)
        raw_draw_index = np.asarray(to_numpy(trace.draw_index), dtype=np.uint64)
        if raw_draw_index.ndim == 0:
            draw_indices = np.full(count, raw_draw_index.item(), dtype=np.uint64)
        else:
            draw_indices = raw_draw_index.reshape(-1)
        vectors = (
            entities, subjects, events, action, selected_probability, draws, keys,
            lower, upper, draw_indices,
        )
        if any(value.shape != (count,) for value in vectors):
            raise ValueError("categorical sampling trace vectors do not align")
        if mask.shape != (count, len(Action)):
            raise ValueError("categorical sampling action mask shape mismatch")
        if any(value.shape != (count, len(Action)) for value in (masked_logits, probabilities, cdf)):
            raise ValueError("categorical sampling matrix shape mismatch")
        if not np.array_equal(action, (cdf < draws[:, None]).sum(axis=1).astype(np.int16)):
            raise ValueError("categorical sampling trace does not reconstruct sampled action")
        selected = probabilities[np.arange(count), action]
        if not np.array_equal(selected.astype(np.float32), selected_probability):
            raise ValueError("categorical sampling selected probability mismatch")
        if np.any(draws < lower) or np.any(draws >= upper):
            raise ValueError("categorical sampling draw lies outside selected CDF interval")
        for index in range(count):
            subject_id = int(subjects[index])
            if self.subject_ids is not None and subject_id not in self.subject_ids:
                continue
            record = {
                "schema": CATEGORICAL_SAMPLING_TRACE_SCHEMA,
                "record_type": "event",
                "tick": int(tick),
                "world_row": int(rows[index]),
                "event_id": int(events[index]),
                "entity_id": int(entities[index]),
                "subject_id": subject_id,
                "action_id": int(action[index]),
                "action_name": Action(int(action[index])).name,
                "action_mask": [bool(value) for value in mask[index].tolist()],
                "masked_logits": _masked_logits_row(masked_logits[index], mask[index]),
                "probabilities": [float(value) for value in probabilities[index].tolist()],
                "cumulative_probabilities": [float(value) for value in cdf[index].tolist()],
                "uniform_draw": float(draws[index]),
                "random_key_uint64": int(keys[index]),
                "draw_index": int(draw_indices[index]),
                "random_context": {
                    "run_seed": int(self.metadata.get("run_seed", -1)),
                    "tick": int(tick),
                    "phase": int(trace.phase),
                    "stream": int(trace.stream),
                },
                "selected_probability": float(selected_probability[index]),
                "selected_cdf_lower": float(lower[index]),
                "selected_cdf_upper": float(upper[index]),
                "temperature": float(trace.temperature),
            }
            self._write(record)
            self.event_count += 1
            self.first_tick = int(tick) if self.first_tick is None else min(self.first_tick, int(tick))
            self.last_tick = int(tick) if self.last_tick is None else max(self.last_tick, int(tick))

    def close(self) -> CategoricalSamplingTraceSummary:
        if self._closed:
            manifest = json.loads(self.manifest_path.read_text(encoding="utf-8"))
            return CategoricalSamplingTraceSummary(
                event_count=int(manifest["event_count"]),
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
            "schema": CATEGORICAL_SAMPLING_TRACE_MANIFEST_SCHEMA,
            "trace_schema": CATEGORICAL_SAMPLING_TRACE_SCHEMA,
            "trace_path": str(self.trace_path.resolve()),
            "trace_sha256": trace_sha,
            "event_count": int(self.event_count),
            "first_tick": self.first_tick,
            "last_tick": self.last_tick,
            "metadata": self.metadata,
            "semantic_feedback": False,
            "checkpoint_state_member": False,
        }
        manifest["manifest_sha256"] = _canonical_sha256(manifest)
        self.manifest_path.write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        self._closed = True
        return CategoricalSamplingTraceSummary(
            event_count=self.event_count,
            first_tick=self.first_tick,
            last_tick=self.last_tick,
            trace_path=str(self.trace_path.resolve()),
            trace_sha256=trace_sha,
            manifest_path=str(self.manifest_path.resolve()),
            manifest_sha256=str(manifest["manifest_sha256"]),
        )



__all__ = [
    "CATEGORICAL_SAMPLING_TRACE_MANIFEST_SCHEMA",
    "CATEGORICAL_SAMPLING_TRACE_SCHEMA",
    "CategoricalSamplingTraceSummary",
    "CategoricalSamplingTraceWriter",
]
