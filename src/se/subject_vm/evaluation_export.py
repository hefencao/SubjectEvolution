"""Pure Stage 3C-6 export helpers for score-free paired evaluation evidence.

The runtime ledger remains authoritative for bounded per-branch observations.
This module only converts completed windows into portable records and pairs
records that share the same source event, stable subject, target, and window
contract.  It never assigns reward, utility, valence, a scalar score, or a
keep/revert decision.
"""
from __future__ import annotations

import hashlib
import json
from typing import Any, Iterable

import numpy as np

from .config import SUBJECT_VM_MODULATION_FACT_WIDTH
from .evaluation import (
    EVALUATION_MODE_GUARDED_LIVE,
    EVALUATION_MODE_READ_ONLY_CONTROL,
    EVALUATION_STATUS_COMPLETE_CONTROL,
    EVALUATION_STATUS_COMPLETE_LIVE_ROLLED_BACK,
)

PAIRED_WINDOW_EXPORT_SCHEMA = "se-subject-vm-paired-window-export-v1"
PAIRED_WINDOW_RECORD_SCHEMA = "se-subject-vm-objective-window-record-v1"


def _json_sha256(payload: Any) -> str:
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _as_python_vector(value: Any, *, dtype: Any = np.float32) -> list[Any]:
    arr = np.asarray(value, dtype=dtype)
    if np.issubdtype(arr.dtype, np.floating):
        return [float(item) for item in arr.tolist()]
    if np.issubdtype(arr.dtype, np.bool_):
        return [bool(item) for item in arr.tolist()]
    return [int(item) for item in arr.tolist()]


def _window_key_payload(record: dict[str, Any]) -> dict[str, Any]:
    return {
        "stable_subject_id": int(record["stable_subject_id"]),
        "source_event_id": int(record["source_event_id"]),
        "start_tick": int(record["start_tick"]),
        "end_tick": int(record["end_tick"]),
        "family_observed": list(record["family_observed"]),
        "target_kind": list(record["target_kind"]),
        "target_id": list(record["target_id"]),
        "pre_value": list(record["pre_value"]),
        "projected_value": list(record["projected_value"]),
        "bounded_delta": list(record["bounded_delta"]),
    }


def window_pair_key(record: dict[str, Any]) -> str:
    """Return a mode-neutral deterministic identity for one window contract."""
    return _json_sha256(_window_key_payload(record))


def extract_completed_windows(
    runtime_snapshot: dict[str, Any], *, branch_role: str
) -> list[dict[str, Any]]:
    """Extract completed score-free windows from one Subject VM snapshot."""
    if branch_role not in {"guarded-live", "read-only-control"}:
        raise ValueError("unsupported subject_vm paired branch role")
    evaluation = runtime_snapshot.get("evaluation_ledger")
    storage = runtime_snapshot.get("storage")
    if not isinstance(evaluation, dict) or not isinstance(storage, dict):
        raise ValueError("subject_vm checkpoint lacks Stage-3C-5 evaluation storage")
    arrays = evaluation.get("arrays")
    storage_arrays = storage.get("arrays")
    if not isinstance(arrays, dict) or not isinstance(storage_arrays, dict):
        raise ValueError("subject_vm evaluation/storage arrays are missing")
    owner_subject = np.asarray(storage_arrays["owner_subject_id"], dtype=np.uint64)
    owner_entity = np.asarray(storage_arrays["owner_entity_id"], dtype=np.uint64)
    entry_valid = np.asarray(arrays["entry_valid"], dtype=bool)
    status = np.asarray(arrays["status"], dtype=np.uint8)
    mode = np.asarray(arrays["mode"], dtype=np.uint8)
    expected_mode = (
        EVALUATION_MODE_GUARDED_LIVE
        if branch_role == "guarded-live"
        else EVALUATION_MODE_READ_ONLY_CONTROL
    )
    expected_status = (
        EVALUATION_STATUS_COMPLETE_LIVE_ROLLED_BACK
        if branch_role == "guarded-live"
        else EVALUATION_STATUS_COMPLETE_CONTROL
    )
    records: list[dict[str, Any]] = []
    for row, slot in np.argwhere(entry_valid):
        row_i, slot_i = int(row), int(slot)
        if int(mode[row_i, slot_i]) != int(expected_mode):
            continue
        if int(status[row_i, slot_i]) != int(expected_status):
            continue
        rollback_verified = bool(arrays["rollback_verified"][row_i, slot_i])
        if not rollback_verified:
            raise ValueError("completed subject_vm evaluation window lacks rollback verification")
        fact_sum = np.asarray(arrays["fact_sum"][row_i, slot_i], dtype=np.float32)
        fact_abs_sum = np.asarray(arrays["fact_abs_sum"][row_i, slot_i], dtype=np.float32)
        fact_max_abs = np.asarray(arrays["fact_max_abs"][row_i, slot_i], dtype=np.float32)
        if fact_sum.shape != (SUBJECT_VM_MODULATION_FACT_WIDTH,):
            raise ValueError("subject_vm evaluation fact width mismatch")
        record = {
            "schema": PAIRED_WINDOW_RECORD_SCHEMA,
            "branch_role": branch_role,
            "stable_subject_id": int(owner_subject[row_i]),
            "stable_entity_id": int(owner_entity[row_i]),
            "source_event_id": int(arrays["source_event_id"][row_i, slot_i]),
            "start_tick": int(arrays["start_tick"][row_i, slot_i]),
            "end_tick": int(arrays["end_tick"][row_i, slot_i]),
            "rollback_due_tick": int(arrays["rollback_due_tick"][row_i, slot_i]),
            "family_observed": _as_python_vector(
                arrays["family_observed"][row_i, slot_i], dtype=bool
            ),
            "target_kind": _as_python_vector(
                arrays["target_kind"][row_i, slot_i], dtype=np.uint8
            ),
            "target_id": _as_python_vector(
                arrays["target_id"][row_i, slot_i], dtype=np.uint32
            ),
            "pre_value": _as_python_vector(arrays["pre_value"][row_i, slot_i]),
            "projected_value": _as_python_vector(
                arrays["projected_value"][row_i, slot_i]
            ),
            "bounded_delta": _as_python_vector(
                arrays["bounded_delta"][row_i, slot_i]
            ),
            "observation_count": int(arrays["observation_count"][row_i, slot_i]),
            "success_count": int(arrays["success_count"][row_i, slot_i]),
            "failure_count": int(arrays["failure_count"][row_i, slot_i]),
            "fact_sum": _as_python_vector(fact_sum),
            "fact_abs_sum": _as_python_vector(fact_abs_sum),
            "fact_max_abs": _as_python_vector(fact_max_abs),
            "fact_clip_count": int(arrays["fact_clip_count"][row_i, slot_i]),
            "rollback_verified": rollback_verified,
            "row_locked_after_window": bool(
                arrays["row_locked_after_window"][row_i, slot_i]
            ),
            "counted_cost_units": int(arrays["counted_cost_units"][row_i, slot_i]),
            "objective_scalar_score": False,
            "automatic_keep_or_revert_decision": False,
        }
        record["pair_key"] = window_pair_key(record)
        records.append(record)
    return sorted(records, key=lambda item: (item["pair_key"], item["branch_role"]))


def pair_completed_windows(
    live_records: Iterable[dict[str, Any]], control_records: Iterable[dict[str, Any]]
) -> dict[str, Any]:
    """Pair completed branch records without reducing evidence to one score."""
    live_list = list(live_records)
    control_list = list(control_records)
    live_by_key = {str(item["pair_key"]): item for item in live_list}
    control_by_key = {str(item["pair_key"]): item for item in control_list}
    if len(live_by_key) != len(live_list):
        raise ValueError("duplicate guarded-live evaluation pair key")
    if len(control_by_key) != len(control_list):
        raise ValueError("duplicate read-only evaluation pair key")
    common = sorted(set(live_by_key) & set(control_by_key))
    pairs: list[dict[str, Any]] = []
    for key in common:
        live = live_by_key[key]
        control = control_by_key[key]
        live_sum = np.asarray(live["fact_sum"], dtype=np.float32)
        control_sum = np.asarray(control["fact_sum"], dtype=np.float32)
        live_abs = np.asarray(live["fact_abs_sum"], dtype=np.float32)
        control_abs = np.asarray(control["fact_abs_sum"], dtype=np.float32)
        pairs.append(
            {
                "pair_key": key,
                "guarded_live": live,
                "read_only_control": control,
                "objective_fact_sum_difference_live_minus_control": _as_python_vector(
                    live_sum - control_sum
                ),
                "objective_fact_abs_sum_difference_live_minus_control": _as_python_vector(
                    live_abs - control_abs
                ),
                "observation_count_difference_live_minus_control": int(
                    live["observation_count"] - control["observation_count"]
                ),
                "success_count_difference_live_minus_control": int(
                    live["success_count"] - control["success_count"]
                ),
                "failure_count_difference_live_minus_control": int(
                    live["failure_count"] - control["failure_count"]
                ),
                "scalar_score": None,
                "keep_or_revert_decision": None,
                "causal_effect_authorized": False,
            }
        )
    return {
        "schema": PAIRED_WINDOW_EXPORT_SCHEMA,
        "pairs": pairs,
        "unpaired_guarded_live": [
            live_by_key[key] for key in sorted(set(live_by_key) - set(control_by_key))
        ],
        "unpaired_read_only_control": [
            control_by_key[key] for key in sorted(set(control_by_key) - set(live_by_key))
        ],
        "paired_window_count": len(pairs),
        "scalar_score": False,
        "automatic_keep_or_revert_decision": False,
        "causal_effect_authorized": False,
    }


__all__ = [
    "PAIRED_WINDOW_EXPORT_SCHEMA",
    "PAIRED_WINDOW_RECORD_SCHEMA",
    "extract_completed_windows",
    "pair_completed_windows",
    "window_pair_key",
]
