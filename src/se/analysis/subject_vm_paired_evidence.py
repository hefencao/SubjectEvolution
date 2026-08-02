"""Stage 3C-7 paired-evidence adequacy and integrity assessment.

This external analysis consumes one or more Stage-3C-6 paired exports together
with their referenced final checkpoints.  It reports pairing coverage,
unpaired structure, rollback/clipping integrity, count-only cost matching and
component-wise branch divergence.  Screening thresholds are explicit analysis
parameters, not a reward function, subjective value, keep/revert decision or
causal authorization.
"""
from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
import hashlib
import json
from pathlib import Path
from typing import Any, Iterable

import numpy as np

from ..checkpointing import read_checkpoint_bundle
from ..subject_vm.config import SUBJECT_VM_MODULATION_FACT_WIDTH
from ..subject_vm.evaluation_export import PAIRED_WINDOW_EXPORT_SCHEMA
from ..subject_vm.evaluation import (
    EVALUATION_STATUS_ACTIVE,
    EVALUATION_STATUS_COMPLETE_CONTROL,
    EVALUATION_STATUS_COMPLETE_LIVE_ROLLED_BACK,
    EVALUATION_STATUS_EMPTY,
    EVALUATION_STATUS_OBSERVED,
    EVALUATION_STATUS_ROLLBACK_FAILED,
)
from ..subject_vm.live_write import (
    LIVE_WRITE_STATUS_EMPTY,
    LIVE_WRITE_STATUS_PENDING,
    LIVE_WRITE_STATUS_ROLLED_BACK,
    LIVE_WRITE_STATUS_ROLLBACK_FAILED,
    LIVE_WRITE_STATUS_CONTROL_PENDING,
    LIVE_WRITE_STATUS_CONTROL_RELEASED,
)
from .subject_vm_paired_evaluation import PAIRED_EVALUATION_EXPORT_SCHEMA

PAIRED_EVIDENCE_ASSESSMENT_SCHEMA = "se-subject-vm-paired-evidence-assessment-v1"
PAIRED_EVIDENCE_RUN_SCHEMA = "se-subject-vm-paired-evidence-run-integrity-v1"

_EVALUATION_STATUS_NAMES = {
    int(EVALUATION_STATUS_EMPTY): "empty",
    int(EVALUATION_STATUS_ACTIVE): "active",
    int(EVALUATION_STATUS_OBSERVED): "observed",
    int(EVALUATION_STATUS_COMPLETE_CONTROL): "complete-control",
    int(EVALUATION_STATUS_COMPLETE_LIVE_ROLLED_BACK): "complete-live-rolled-back",
    int(EVALUATION_STATUS_ROLLBACK_FAILED): "rollback-failed",
}
_LIVE_WRITE_STATUS_NAMES = {
    int(LIVE_WRITE_STATUS_EMPTY): "empty",
    int(LIVE_WRITE_STATUS_PENDING): "pending",
    int(LIVE_WRITE_STATUS_ROLLED_BACK): "rolled-back",
    int(LIVE_WRITE_STATUS_ROLLBACK_FAILED): "rollback-failed",
    int(LIVE_WRITE_STATUS_CONTROL_PENDING): "control-pending",
    int(LIVE_WRITE_STATUS_CONTROL_RELEASED): "control-released",
}
_ENTITY_COMPONENTS = (
    "x", "y", "vx", "vy", "energy", "integrity", "fertility",
    "material", "information_store", "age", "generation",
)
_ENVIRONMENT_COMPONENTS = (
    "resources", "hazard", "mortality_trace", "oxygen", "terrain", "wear",
    "signal_openness",
)


@dataclass(frozen=True)
class PairedEvidenceScreeningThresholds:
    """Explicit engineering screening thresholds, never a scientific value model."""

    min_independent_source_pairs: int = 3
    min_total_paired_windows: int = 1
    min_pooled_pairing_coverage: float = 0.80
    max_fact_clip_fraction: float = 0.05
    max_rollback_failures: int = 0
    min_paired_evaluation_cost_match_fraction: float = 1.0

    def validate(self) -> None:
        if self.min_independent_source_pairs < 1:
            raise ValueError("min_independent_source_pairs must be positive")
        if self.min_total_paired_windows < 0:
            raise ValueError("min_total_paired_windows must be nonnegative")
        for name in (
            "min_pooled_pairing_coverage",
            "max_fact_clip_fraction",
            "min_paired_evaluation_cost_match_fraction",
        ):
            value = float(getattr(self, name))
            if not 0.0 <= value <= 1.0:
                raise ValueError(f"{name} must be within [0, 1]")
        if self.max_rollback_failures < 0:
            raise ValueError("max_rollback_failures must be nonnegative")


def _sha256_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _canonical_sha256(payload: Any) -> str:
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _validate_export(payload: dict[str, Any]) -> None:
    if payload.get("schema") != PAIRED_EVALUATION_EXPORT_SCHEMA:
        raise ValueError("unsupported subject_vm paired evaluation export schema")
    recorded = str(payload.get("export_sha256", ""))
    unsigned = dict(payload)
    unsigned.pop("export_sha256", None)
    if recorded != _canonical_sha256(unsigned):
        raise ValueError("subject_vm paired evaluation export checksum mismatch")
    if not bool(payload.get("shared_checkpoint_verified")):
        raise ValueError("paired export lacks shared-checkpoint verification")
    if not bool(payload.get("branch_identity_verified")):
        raise ValueError("paired export lacks branch-identity verification")
    if not bool(payload.get("componentwise_differences_only")):
        raise ValueError("paired export is not component-wise only")
    if payload.get("scalar_score") is not False:
        raise ValueError("paired export unexpectedly authorizes scalar score")
    if payload.get("automatic_keep_or_revert_decision") is not False:
        raise ValueError("paired export unexpectedly authorizes keep/revert")
    if payload.get("causal_effect_authorized") is not False:
        raise ValueError("paired export unexpectedly authorizes causal effect")
    evidence = payload.get("window_evidence")
    if not isinstance(evidence, dict) or evidence.get("schema") != PAIRED_WINDOW_EXPORT_SCHEMA:
        raise ValueError("paired export lacks the Stage-3C-6 window evidence schema")
    if evidence.get("scalar_score") is not False:
        raise ValueError("window evidence unexpectedly authorizes scalar score")
    if evidence.get("automatic_keep_or_revert_decision") is not False:
        raise ValueError("window evidence unexpectedly authorizes keep/revert")
    if evidence.get("causal_effect_authorized") is not False:
        raise ValueError("window evidence unexpectedly authorizes causal effect")
    for pair in evidence.get("pairs", []):
        if pair.get("scalar_score") is not None:
            raise ValueError("paired window unexpectedly contains a scalar score")
        if pair.get("keep_or_revert_decision") is not None:
            raise ValueError("paired window unexpectedly contains keep/revert")
        if pair.get("causal_effect_authorized") is not False:
            raise ValueError("paired window unexpectedly authorizes causal effect")
        vector = pair.get("objective_fact_sum_difference_live_minus_control")
        if not isinstance(vector, list) or len(vector) != SUBJECT_VM_MODULATION_FACT_WIDTH:
            raise ValueError("paired window objective fact width mismatch")
    records = []
    for pair in evidence.get("pairs", []):
        records.extend((pair.get("guarded_live"), pair.get("read_only_control")))
    records.extend(evidence.get("unpaired_guarded_live", []))
    records.extend(evidence.get("unpaired_read_only_control", []))
    for record in records:
        if not isinstance(record, dict):
            raise ValueError("paired window record is malformed")
        if record.get("objective_scalar_score") is not False:
            raise ValueError("window record unexpectedly authorizes scalar score")
        if record.get("automatic_keep_or_revert_decision") is not False:
            raise ValueError("window record unexpectedly authorizes keep/revert")


def _load_export(path: str | Path) -> dict[str, Any]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("paired evaluation export must contain one JSON object")
    _validate_export(payload)
    return payload


def _runtime_payload(state: dict[str, Any]) -> dict[str, Any]:
    runtime = state.get("simulation", {}).get("subject_vm")
    if not isinstance(runtime, dict):
        raise ValueError("branch checkpoint lacks subject_vm runtime")
    return runtime


def _status_counts(valid: np.ndarray, status: np.ndarray, names: dict[int, str]) -> dict[str, int]:
    result = {name: 0 for code, name in names.items() if code != 0}
    for value in status[valid].tolist():
        name = names.get(int(value), f"unknown-{int(value)}")
        result[name] = result.get(name, 0) + 1
    return result


def _ledger_integrity(runtime: dict[str, Any]) -> dict[str, Any]:
    evaluation = runtime.get("evaluation_ledger")
    live = runtime.get("live_write_ledger")
    if not isinstance(evaluation, dict) or not isinstance(live, dict):
        raise ValueError("branch checkpoint lacks evaluation/live-write ledgers")
    eval_arrays = evaluation.get("arrays")
    live_arrays = live.get("arrays")
    if not isinstance(eval_arrays, dict) or not isinstance(live_arrays, dict):
        raise ValueError("branch checkpoint ledger arrays are missing")
    eval_valid = np.asarray(eval_arrays["entry_valid"], dtype=bool)
    eval_status = np.asarray(eval_arrays["status"], dtype=np.uint8)
    observation_count = np.asarray(eval_arrays["observation_count"], dtype=np.uint64)
    clip_count = np.asarray(eval_arrays["fact_clip_count"], dtype=np.uint64)
    eval_cost = np.asarray(eval_arrays["counted_cost_units"], dtype=np.uint64)
    observed_components = int(
        observation_count[eval_valid].sum(dtype=np.uint64)
        * np.uint64(SUBJECT_VM_MODULATION_FACT_WIDTH)
    )
    total_clips = int(clip_count[eval_valid].sum(dtype=np.uint64))
    clip_fraction = (
        float(total_clips / observed_components) if observed_components else 0.0
    )
    live_valid = np.asarray(live_arrays["entry_valid"], dtype=bool)
    live_status = np.asarray(live_arrays["status"], dtype=np.uint8)
    row_locked = np.asarray(live_arrays["row_locked"], dtype=bool)
    return {
        "evaluation_entry_count": int(np.count_nonzero(eval_valid)),
        "evaluation_status_counts": _status_counts(
            eval_valid, eval_status, _EVALUATION_STATUS_NAMES
        ),
        "evaluation_observation_count": int(
            observation_count[eval_valid].sum(dtype=np.uint64)
        ),
        "evaluation_fact_clip_count": total_clips,
        "evaluation_observed_fact_component_count": observed_components,
        "evaluation_fact_clip_fraction": clip_fraction,
        "evaluation_counted_cost_units": int(eval_cost[eval_valid].sum(dtype=np.uint64)),
        "live_write_entry_count": int(np.count_nonzero(live_valid)),
        "live_write_status_counts": _status_counts(
            live_valid, live_status, _LIVE_WRITE_STATUS_NAMES
        ),
        "live_write_locked_row_count": int(np.count_nonzero(row_locked)),
        "evaluation_counter_snapshot": {
            str(key): int(value) for key, value in evaluation.get("counters", {}).items()
        },
        "live_write_counter_snapshot": {
            str(key): int(value) for key, value in live.get("counters", {}).items()
        },
    }


def _record_identity(record: dict[str, Any], fields: tuple[str, ...]) -> tuple[Any, ...]:
    values: list[Any] = []
    for field in fields:
        value = record[field]
        values.append(tuple(value) if isinstance(value, list) else value)
    return tuple(values)


def _classify_unpaired(
    record: dict[str, Any], counterparts: Iterable[dict[str, Any]]
) -> str:
    others = list(counterparts)
    subject = int(record["stable_subject_id"])
    same_subject = [item for item in others if int(item["stable_subject_id"]) == subject]
    if not same_subject:
        return "stable-subject-absent"
    source = int(record["source_event_id"])
    same_event = [item for item in same_subject if int(item["source_event_id"]) == source]
    if not same_event:
        return "source-event-divergence"
    same_window = [
        item for item in same_event
        if int(item["start_tick"]) == int(record["start_tick"])
        and int(item["end_tick"]) == int(record["end_tick"])
    ]
    if not same_window:
        return "window-boundary-divergence"
    target_fields = (
        "family_observed", "target_kind", "target_id", "pre_value",
        "projected_value", "bounded_delta",
    )
    identity = _record_identity(record, target_fields)
    if not any(_record_identity(item, target_fields) == identity for item in same_window):
        return "target-or-update-contract-divergence"
    return "counterpart-missing-after-identical-contract"


def _unpaired_reason_counts(
    unpaired: Iterable[dict[str, Any]], counterparts: Iterable[dict[str, Any]]
) -> dict[str, int]:
    result: dict[str, int] = {}
    other_list = list(counterparts)
    for record in unpaired:
        reason = _classify_unpaired(record, other_list)
        result[reason] = result.get(reason, 0) + 1
    return dict(sorted(result.items()))


def _numeric_difference(left: Any, right: Any) -> dict[str, Any]:
    a = np.asarray(left)
    b = np.asarray(right)
    if a.shape != b.shape:
        return {"shape_match": False, "left_shape": list(a.shape), "right_shape": list(b.shape)}
    difference = np.asarray(a, dtype=np.float64) - np.asarray(b, dtype=np.float64)
    absolute = np.abs(difference)
    return {
        "shape_match": True,
        "mean_absolute_difference": float(absolute.mean()) if absolute.size else 0.0,
        "max_absolute_difference": float(absolute.max()) if absolute.size else 0.0,
        "nonzero_component_count": int(np.count_nonzero(difference)),
    }


def _entity_divergence(live_state: dict[str, Any], control_state: dict[str, Any]) -> dict[str, Any]:
    live_entities = live_state["simulation"]["entities"]
    control_entities = control_state["simulation"]["entities"]
    live_rows = np.flatnonzero(np.asarray(live_entities.alive, dtype=bool))
    control_rows = np.flatnonzero(np.asarray(control_entities.alive, dtype=bool))
    live_ids = np.asarray(live_entities.entity_id[live_rows], dtype=np.uint64)
    control_ids = np.asarray(control_entities.entity_id[control_rows], dtype=np.uint64)
    live_map = {int(entity_id): int(row) for entity_id, row in zip(live_ids, live_rows)}
    control_map = {int(entity_id): int(row) for entity_id, row in zip(control_ids, control_rows)}
    live_set, control_set = set(live_map), set(control_map)
    common = sorted(live_set & control_set)
    union = live_set | control_set
    components: dict[str, Any] = {}
    for name in _ENTITY_COMPONENTS:
        if not hasattr(live_entities, name) or not hasattr(control_entities, name):
            continue
        left = np.asarray([getattr(live_entities, name)[live_map[key]] for key in common])
        right = np.asarray([getattr(control_entities, name)[control_map[key]] for key in common])
        components[name] = _numeric_difference(left, right)
    live_subjects = {
        int(live_entities.primary_subject_id[row]) for row in live_rows
        if int(live_entities.primary_subject_id[row]) != 0
    }
    control_subjects = {
        int(control_entities.primary_subject_id[row]) for row in control_rows
        if int(control_entities.primary_subject_id[row]) != 0
    }
    subject_union = live_subjects | control_subjects
    return {
        "guarded_live_alive_count": len(live_set),
        "read_only_control_alive_count": len(control_set),
        "shared_alive_entity_count": len(common),
        "guarded_live_only_entity_count": len(live_set - control_set),
        "read_only_control_only_entity_count": len(control_set - live_set),
        "alive_entity_identity_jaccard": float(len(common) / len(union)) if union else 1.0,
        "shared_primary_subject_count": len(live_subjects & control_subjects),
        "primary_subject_identity_jaccard": (
            float(len(live_subjects & control_subjects) / len(subject_union))
            if subject_union else 1.0
        ),
        "shared_entity_component_differences": components,
    }


def _environment_divergence(live_state: dict[str, Any], control_state: dict[str, Any]) -> dict[str, Any]:
    live_env = live_state["simulation"]["environment"]
    control_env = control_state["simulation"]["environment"]
    result: dict[str, Any] = {}
    for name in _ENVIRONMENT_COMPONENTS:
        if hasattr(live_env, name) and hasattr(control_env, name):
            result[name] = _numeric_difference(
                getattr(live_env, name), getattr(control_env, name)
            )
    return result


def _branch_divergence(live_state: dict[str, Any], control_state: dict[str, Any]) -> dict[str, Any]:
    live_sim = live_state["simulation"]
    control_sim = control_state["simulation"]
    return {
        "final_tick_match": int(live_sim["tick"]) == int(control_sim["tick"]),
        "guarded_live_tick": int(live_sim["tick"]),
        "read_only_control_tick": int(control_sim["tick"]),
        "total_births_difference_live_minus_control": int(live_sim["total_births"]) - int(control_sim["total_births"]),
        "total_deaths_difference_live_minus_control": int(live_sim["total_deaths"]) - int(control_sim["total_deaths"]),
        "action_count_difference_live_minus_control": [
            int(item) for item in (
                np.asarray(live_sim["action_counts"], dtype=np.int64)
                - np.asarray(control_sim["action_counts"], dtype=np.int64)
            ).tolist()
        ],
        "entity_divergence": _entity_divergence(live_state, control_state),
        "environment_component_differences": _environment_divergence(
            live_state, control_state
        ),
    }


def _read_verified_branch(
    payload: dict[str, Any], role: str
) -> tuple[dict[str, Any], dict[str, Any], Path]:
    branch = payload["branches"][role]
    path = Path(branch["checkpoint"]).resolve()
    if not path.is_file():
        raise ValueError(f"{role} checkpoint does not exist: {path}")
    if _sha256_file(path) != str(branch["checkpoint_file_sha256"]):
        raise ValueError(f"{role} checkpoint file checksum mismatch")
    metadata, state = read_checkpoint_bundle(path)
    if str(metadata["state_sha256"]) != str(branch["checkpoint_state_sha256"]):
        raise ValueError(f"{role} checkpoint state checksum mismatch")
    return metadata, state, path


def _cost_matching(pairs: list[dict[str, Any]]) -> dict[str, Any]:
    differences: list[int] = []
    observation_differences: list[int] = []
    for pair in pairs:
        live = pair["guarded_live"]
        control = pair["read_only_control"]
        differences.append(int(live["counted_cost_units"]) - int(control["counted_cost_units"]))
        observation_differences.append(
            int(live["observation_count"]) - int(control["observation_count"])
        )
    exact = sum(value == 0 for value in differences)
    count = len(differences)
    return {
        "paired_window_count": count,
        "exact_evaluation_cost_match_count": exact,
        "exact_evaluation_cost_match_fraction": float(exact / count) if count else None,
        "evaluation_cost_difference_live_minus_control": differences,
        "observation_count_difference_live_minus_control": observation_differences,
        "intervention_specific_live_write_cost_expected_to_differ": True,
        "physical_cost_debit_authorized": False,
    }


def assess_export(payload: dict[str, Any], *, export_path: str | Path | None = None) -> dict[str, Any]:
    """Assess one Stage-3C-6 export and its two referenced checkpoints."""
    _validate_export(payload)
    live_meta, live_state, live_path = _read_verified_branch(payload, "guarded-live")
    control_meta, control_state, control_path = _read_verified_branch(
        payload, "read-only-control"
    )
    evidence = payload["window_evidence"]
    pairs = list(evidence["pairs"])
    unpaired_live = list(evidence["unpaired_guarded_live"])
    unpaired_control = list(evidence["unpaired_read_only_control"])
    paired = len(pairs)
    union_count = paired + len(unpaired_live) + len(unpaired_control)
    live_total = paired + len(unpaired_live)
    control_total = paired + len(unpaired_control)
    live_integrity = _ledger_integrity(_runtime_payload(live_state))
    control_integrity = _ledger_integrity(_runtime_payload(control_state))
    rollback_failures = (
        int(live_integrity["evaluation_status_counts"].get("rollback-failed", 0))
        + int(control_integrity["evaluation_status_counts"].get("rollback-failed", 0))
        + int(live_integrity["live_write_status_counts"].get("rollback-failed", 0))
        + int(control_integrity["live_write_status_counts"].get("rollback-failed", 0))
    )
    total_clips = (
        int(live_integrity["evaluation_fact_clip_count"])
        + int(control_integrity["evaluation_fact_clip_count"])
    )
    total_components = (
        int(live_integrity["evaluation_observed_fact_component_count"])
        + int(control_integrity["evaluation_observed_fact_component_count"])
    )
    clipping_fraction = float(total_clips / total_components) if total_components else 0.0
    cost = _cost_matching(pairs)
    hard_checks = {
        "branch_final_tick_match": int(live_meta["tick"]) == int(control_meta["tick"]),
        "no_rollback_failures": rollback_failures == 0,
        "no_locked_live_write_rows": (
            int(live_integrity["live_write_locked_row_count"])
            + int(control_integrity["live_write_locked_row_count"])
        ) == 0,
        "no_pending_live_writes": (
            int(live_integrity["live_write_status_counts"].get("pending", 0))
            + int(control_integrity["live_write_status_counts"].get("pending", 0))
        ) == 0,
        "no_pending_control_reservations": (
            int(live_integrity["live_write_status_counts"].get("control-pending", 0))
            + int(control_integrity["live_write_status_counts"].get("control-pending", 0))
        ) == 0,
        "score_free_export": evidence.get("scalar_score") is False,
        "no_automatic_keep_or_revert": evidence.get(
            "automatic_keep_or_revert_decision"
        ) is False,
        "causal_effect_not_authorized": evidence.get("causal_effect_authorized") is False,
    }
    return {
        "schema": PAIRED_EVIDENCE_RUN_SCHEMA,
        "export_path": str(Path(export_path).resolve()) if export_path is not None else None,
        "export_sha256": str(payload["export_sha256"]),
        "plan_sha256": str(payload["plan_sha256"]),
        "source_checkpoint_state_sha256": str(payload["source"]["checkpoint_state_sha256"]),
        "guarded_live_checkpoint": str(live_path),
        "read_only_control_checkpoint": str(control_path),
        "pairing": {
            "paired_window_count": paired,
            "guarded_live_window_count": live_total,
            "read_only_control_window_count": control_total,
            "unpaired_guarded_live_count": len(unpaired_live),
            "unpaired_read_only_control_count": len(unpaired_control),
            "pairing_coverage_over_unique_contracts": float(paired / union_count) if union_count else 0.0,
            "guarded_live_pairing_coverage": float(paired / live_total) if live_total else 0.0,
            "read_only_control_pairing_coverage": float(paired / control_total) if control_total else 0.0,
            "unpaired_guarded_live_reason_counts": _unpaired_reason_counts(
                unpaired_live, [item["read_only_control"] for item in pairs] + unpaired_control
            ),
            "unpaired_read_only_control_reason_counts": _unpaired_reason_counts(
                unpaired_control, [item["guarded_live"] for item in pairs] + unpaired_live
            ),
        },
        "rollback_and_ledger_integrity": {
            "guarded_live": live_integrity,
            "read_only_control": control_integrity,
            "rollback_failure_count": rollback_failures,
        },
        "fact_clipping": {
            "clip_count": total_clips,
            "observed_fact_component_count": total_components,
            "clip_fraction": clipping_fraction,
        },
        "count_only_cost_matching": cost,
        "branch_divergence": {
            "final_checkpoint_state_sha_equal": (
                str(live_meta["state_sha256"]) == str(control_meta["state_sha256"])
            ),
            **_branch_divergence(live_state, control_state),
        },
        "hard_integrity_checks": hard_checks,
        "hard_integrity_pass": all(hard_checks.values()),
        "scalar_score": False,
        "automatic_keep_or_revert_decision": False,
        "causal_effect_authorized": False,
    }


def assess_exports(
    export_paths: Iterable[str | Path],
    *,
    thresholds: PairedEvidenceScreeningThresholds | None = None,
) -> dict[str, Any]:
    """Assess repeated shared-checkpoint pairs without scalarizing outcomes."""
    limits = thresholds or PairedEvidenceScreeningThresholds()
    limits.validate()
    paths = [Path(path).resolve() for path in export_paths]
    if not paths:
        raise ValueError("at least one paired evaluation export is required")
    runs = [assess_export(_load_export(path), export_path=path) for path in paths]
    source_hashes = [str(item["source_checkpoint_state_sha256"]) for item in runs]
    source_counts: dict[str, int] = {}
    for value in source_hashes:
        source_counts[value] = source_counts.get(value, 0) + 1
    total_pairs = sum(int(item["pairing"]["paired_window_count"]) for item in runs)
    total_union = sum(
        int(item["pairing"]["paired_window_count"])
        + int(item["pairing"]["unpaired_guarded_live_count"])
        + int(item["pairing"]["unpaired_read_only_control_count"])
        for item in runs
    )
    total_clips = sum(int(item["fact_clipping"]["clip_count"]) for item in runs)
    total_components = sum(
        int(item["fact_clipping"]["observed_fact_component_count"]) for item in runs
    )
    total_rollback_failures = sum(
        int(item["rollback_and_ledger_integrity"]["rollback_failure_count"])
        for item in runs
    )
    matched_cost_windows = sum(
        int(item["count_only_cost_matching"]["exact_evaluation_cost_match_count"])
        for item in runs
    )
    cost_window_count = sum(
        int(item["count_only_cost_matching"]["paired_window_count"])
        for item in runs
    )
    pooled_coverage = float(total_pairs / total_union) if total_union else 0.0
    pooled_clip_fraction = float(total_clips / total_components) if total_components else 0.0
    pooled_cost_match = (
        float(matched_cost_windows / cost_window_count) if cost_window_count else 0.0
    )
    aggregate = {
        "export_count": len(runs),
        "independent_source_pair_count": len(source_counts),
        "duplicate_source_state_hash_counts": {
            key: count for key, count in sorted(source_counts.items()) if count > 1
        },
        "total_paired_window_count": total_pairs,
        "total_unique_window_contract_count": total_union,
        "pooled_pairing_coverage": pooled_coverage,
        "total_rollback_failure_count": total_rollback_failures,
        "total_fact_clip_count": total_clips,
        "total_observed_fact_component_count": total_components,
        "pooled_fact_clip_fraction": pooled_clip_fraction,
        "paired_evaluation_cost_match_window_count": matched_cost_windows,
        "paired_evaluation_cost_window_count": cost_window_count,
        "paired_evaluation_cost_match_fraction": pooled_cost_match,
        "all_hard_integrity_checks_pass": all(
            bool(item["hard_integrity_pass"]) for item in runs
        ),
    }
    criteria = {
        "hard_integrity": aggregate["all_hard_integrity_checks_pass"],
        "independent_source_pairs": (
            aggregate["independent_source_pair_count"]
            >= limits.min_independent_source_pairs
        ),
        "paired_windows": total_pairs >= limits.min_total_paired_windows,
        "pairing_coverage": pooled_coverage >= limits.min_pooled_pairing_coverage,
        "fact_clipping": pooled_clip_fraction <= limits.max_fact_clip_fraction,
        "rollback_failures": total_rollback_failures <= limits.max_rollback_failures,
        "evaluation_cost_matching": (
            pooled_cost_match >= limits.min_paired_evaluation_cost_match_fraction
        ),
    }
    payload = {
        "schema": PAIRED_EVIDENCE_ASSESSMENT_SCHEMA,
        "screening_thresholds": asdict(limits),
        "thresholds_are_engineering_screen_only": True,
        "runs": runs,
        "aggregate": aggregate,
        "adequacy_screen": {
            "criteria": criteria,
            "passed": all(criteria.values()),
            "failed_criteria": [name for name, passed in criteria.items() if not passed],
            "scientific_sufficiency_authorized": False,
        },
        "objective_coordinate_weighting": None,
        "scalar_score": False,
        "automatic_keep_or_revert_decision": False,
        "causal_effect_authorized": False,
        "permanent_parameter_retention_authorized": False,
    }
    payload["assessment_sha256"] = _canonical_sha256(payload)
    return payload


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Assess Subject VM Stage-3C-6 paired evidence integrity."
    )
    parser.add_argument("--export", action="append", required=True, dest="exports")
    parser.add_argument("--output", required=True)
    parser.add_argument("--min-independent-source-pairs", type=int, default=3)
    parser.add_argument("--min-total-paired-windows", type=int, default=1)
    parser.add_argument("--min-pooled-pairing-coverage", type=float, default=0.80)
    parser.add_argument("--max-fact-clip-fraction", type=float, default=0.05)
    parser.add_argument("--max-rollback-failures", type=int, default=0)
    parser.add_argument(
        "--min-paired-evaluation-cost-match-fraction", type=float, default=1.0
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    thresholds = PairedEvidenceScreeningThresholds(
        min_independent_source_pairs=args.min_independent_source_pairs,
        min_total_paired_windows=args.min_total_paired_windows,
        min_pooled_pairing_coverage=args.min_pooled_pairing_coverage,
        max_fact_clip_fraction=args.max_fact_clip_fraction,
        max_rollback_failures=args.max_rollback_failures,
        min_paired_evaluation_cost_match_fraction=(
            args.min_paired_evaluation_cost_match_fraction
        ),
    )
    payload = assess_exports(args.exports, thresholds=thresholds)
    destination = Path(args.output)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )


if __name__ == "__main__":
    main()


__all__ = [
    "PAIRED_EVIDENCE_ASSESSMENT_SCHEMA",
    "PAIRED_EVIDENCE_RUN_SCHEMA",
    "PairedEvidenceScreeningThresholds",
    "assess_export",
    "assess_exports",
]
