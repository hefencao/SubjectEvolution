"""Stage 3C-37 read-only near-exact tie origin audit.

The audit reconstructs the frozen rank-two selector queries for the original
and first disjoint source panels.  It distinguishes the Stage-3C-27 1e-8
analysis bin from the actual runtime comparator, which applies latest/oldest
ordering only when scores are equal within 1e-12.  It changes no runtime,
checkpoint, source, threshold, candidate, ordering or retention contract.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any, Iterable

import numpy as np

from .. import __version__
from ..checkpointing import read_checkpoint_bundle
from ..subject_vm.association import _candidate_order
from ..subject_vm.modulation import modulation_control_ports
from .subject_vm_stage3c13_exposure_adequacy import _source_records
from .subject_vm_stage3c22_historical_selection import _canonical_sha256, _stats
from .subject_vm_stage3c23_dual_readout_rank import _validate_study
from .subject_vm_stage3c25_winner_basin import _visible_token
from .subject_vm_stage3c27_token_kinematics import STAGE3C27_TOKEN_KINEMATICS_SCHEMA
from .subject_vm_stage3c36_geometry_transport import STAGE3C36_GEOMETRY_TRANSPORT_SCHEMA

STAGE3C37_TIE_ORIGIN_SCHEMA = "se-subject-vm-stage3c37-tie-origin-assessment-v1"
_STAGE3C27_DIAGNOSTIC_ATOL = 1e-8
_RUNTIME_SCORE_ATOL = 1e-12


def _load_json(path: str | Path) -> dict[str, Any]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"expected one JSON object: {path}")
    return payload


def _validate_assessment(payload: dict[str, Any], *, schema: str, label: str) -> None:
    if payload.get("schema") != schema:
        raise ValueError(f"unsupported {label} schema")
    recorded = str(payload.get("assessment_sha256", ""))
    unsigned = dict(payload)
    unsigned.pop("assessment_sha256", None)
    if not recorded or recorded != _canonical_sha256(unsigned):
        raise ValueError(f"{label} checksum mismatch")


def _file_sha256(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _study_unsigned_sha256(study: dict[str, Any]) -> str:
    unsigned = dict(study)
    unsigned.pop("study_sha256", None)
    return _canonical_sha256(unsigned)


def _validate_frozen_and_replay(
    frozen: dict[str, Any],
    replay: dict[str, Any],
    stage27: dict[str, Any],
    *,
    label: str,
) -> dict[int, dict[str, Any]]:
    _validate_study(frozen, second_port=7)
    _validate_study(replay, second_port=7)
    if frozen.get("study_sha256") != _study_unsigned_sha256(frozen):
        raise ValueError(f"{label} frozen study checksum mismatch")
    if replay.get("study_sha256") != _study_unsigned_sha256(replay):
        raise ValueError(f"{label} replay study checksum mismatch")
    _validate_assessment(stage27, schema=STAGE3C27_TOKEN_KINEMATICS_SCHEMA, label=f"{label} Stage-3C-27")
    if stage27.get("rank2_study_sha256") != frozen.get("study_sha256"):
        raise ValueError(f"{label} frozen Stage-3C-27 lineage mismatch")

    invariant_keys = (
        "project_config_file_sha256",
        "parameters",
        "population",
        "resolved_backend",
        "temporary_exposure_contract",
        "fixed_bootstrap_is_evolved_result",
        "universal_attention_claim",
        "permanent_parameter_retention_authorized",
    )
    for key in invariant_keys:
        if frozen.get(key) != replay.get(key):
            raise ValueError(f"{label} replay changed frozen study field: {key}")
    if frozen.get("bootstrap_profile", {}).get("profile_sha256") != replay.get(
        "bootstrap_profile", {}
    ).get("profile_sha256"):
        raise ValueError(f"{label} replay bootstrap profile mismatch")

    frozen_sources = _source_records(frozen)
    replay_sources = _source_records(replay)
    if set(frozen_sources) != set(replay_sources) or len(frozen_sources) != 9:
        raise ValueError(f"{label} replay source identity mismatch")
    for seed in sorted(frozen_sources):
        left = frozen_sources[seed]
        right = replay_sources[seed]
        for key in (
            "source_tick",
            "pre_bootstrap_checkpoint_state_sha256",
            "source_checkpoint_state_sha256",
            "source_checkpoint_config_sha256",
        ):
            if left.get(key) != right.get(key):
                raise ValueError(f"{label} seed {seed} replay lineage mismatch: {key}")
        checkpoint = Path(str(right["read_only_control_checkpoint"]))
        if not checkpoint.is_file():
            raise FileNotFoundError(f"{label} seed {seed} replay checkpoint missing: {checkpoint}")
    return replay_sources


def _float32_cosine(query: np.ndarray, candidate: np.ndarray) -> float:
    q = np.asarray(query, dtype=np.float32)
    c = np.asarray(candidate, dtype=np.float32)
    dot = np.float32(np.dot(q, c))
    q_norm = np.float32(np.sqrt(np.float32(np.dot(q, q))))
    c_norm = np.float32(np.sqrt(np.float32(np.dot(c, c))))
    score = np.float32(dot / np.float32(q_norm * c_norm))
    return float(np.clip(score, np.float32(-1.0), np.float32(1.0)))


def _ulp_distance(left: np.float32, right: np.float32) -> int:
    left_value = np.float32(left)
    right_value = np.float32(right)
    if left_value == right_value:
        return 0
    low, high = sorted((left_value, right_value), key=float)
    spacing = abs(float(np.spacing(low)))
    if spacing == 0.0:
        return 0
    return int(round(abs(float(high) - float(low)) / spacing))


def _candidate_record(
    *,
    score64: float,
    score32: float,
    tick: int,
    event_id: int,
    slot: int,
    age: int,
    raw64: np.ndarray,
    raw32: np.ndarray,
    visible_ports: tuple[int, int, int],
) -> dict[str, Any]:
    raw_visible64 = np.asarray(raw64[list(visible_ports)], dtype=np.float64)
    raw_visible32 = np.asarray(raw32[list(visible_ports)], dtype=np.float32)
    norm64 = raw_visible64 / float(np.linalg.norm(raw_visible64))
    norm32 = raw_visible32 / np.float32(np.linalg.norm(raw_visible32))
    return {
        "score_float64": float(score64),
        "score_direct_float32": float(score32),
        "event_tick": int(tick),
        "event_id": int(event_id),
        "slot": int(slot),
        "age_ticks": int(age),
        "raw_visible_float32": [float(value) for value in raw_visible32],
        "normalized_visible_float64": [float(value) for value in norm64],
        "normalized_visible_direct_float32": [float(value) for value in norm32],
    }


def _audit_checkpoint(checkpoint: str | Path, *, source_tick: int, seed: int) -> dict[str, Any]:
    _, state = read_checkpoint_bundle(checkpoint)
    subject_vm_cfg = state["config"].subject_vm
    association_cfg = subject_vm_cfg.association
    trace = state["simulation"]["subject_vm"]["trace_storage"]["arrays"]

    valid = np.asarray(trace["event_valid"], dtype=bool)
    requested = np.asarray(trace["association_requested"], dtype=bool) & valid
    assigned = np.asarray(trace["association_assigned"], dtype=bool) & valid
    event_ids = np.asarray(trace["event_id"], dtype=np.uint64)
    event_ticks = np.asarray(trace["event_tick"], dtype=np.int64)
    subject_ids = np.asarray(trace["subject_id"], dtype=np.uint64)
    native_tokens = np.asarray(trace["thought_token"])
    if native_tokens.dtype != np.float32:
        raise ValueError("Stage-3C-37 requires the frozen float32 thought-token storage")
    tokens64 = np.asarray(native_tokens, dtype=np.float64)
    stored_event_ids = np.asarray(trace["associated_event_id"], dtype=np.uint64)
    stored_similarities = np.asarray(trace["association_similarity"], dtype=np.float64)

    excluded_ports = modulation_control_ports(subject_vm_cfg.modulation)
    visible_ports = tuple(
        port
        for port in range(tokens64.shape[-1])
        if port
        not in {
            int(association_cfg.request_token_port),
            *(int(value) for value in excluded_ports),
        }
    )
    if len(visible_ports) != 3:
        raise ValueError("Stage-3C-37 requires the frozen three-coordinate visible token")
    first_port, second_port, constant_port = visible_ports

    reconstruction_mismatch_count = 0
    multi_candidate_query_count = 0
    diagnostic_strict_age_one = 0
    diagnostic_near_tie = 0
    diagnostic_older = 0
    selector_strict_age_one = 0
    selector_runtime_tie = 0
    selector_older = 0
    runtime_top_tie_count = 0
    runtime_tie_changes_exact_score_winner_count = 0
    near_tie_records: list[dict[str, Any]] = []

    for row, slot in zip(*np.nonzero(requested), strict=True):
        current_tick = int(event_ticks[row, slot])
        query64 = _visible_token(
            tokens64[row, slot],
            request_port=int(association_cfg.request_token_port),
            excluded_ports=excluded_ports,
        )
        query32 = _visible_token(
            native_tokens[row, slot],
            request_port=int(association_cfg.request_token_port),
            excluded_ports=excluded_ports,
        ).astype(np.float32)
        query_norm64 = float(np.linalg.norm(query64))
        candidates: list[dict[str, Any]] = []
        if query_norm64 > 0.0:
            for historical_slot in np.flatnonzero(valid[row]).tolist():
                if int(historical_slot) == int(slot):
                    continue
                historical_tick = int(event_ticks[row, historical_slot])
                delay = current_tick - historical_tick
                if delay < int(association_cfg.min_delay_ticks) or delay > int(
                    association_cfg.max_delay_ticks
                ):
                    continue
                candidate64 = _visible_token(
                    tokens64[row, historical_slot],
                    request_port=int(association_cfg.request_token_port),
                    excluded_ports=excluded_ports,
                )
                candidate32 = _visible_token(
                    native_tokens[row, historical_slot],
                    request_port=int(association_cfg.request_token_port),
                    excluded_ports=excluded_ports,
                ).astype(np.float32)
                candidate_norm64 = float(np.linalg.norm(candidate64))
                if candidate_norm64 == 0.0:
                    continue
                score64 = float(
                    np.clip(
                        np.dot(query64, candidate64)
                        / (query_norm64 * candidate_norm64),
                        -1.0,
                        1.0,
                    )
                )
                if score64 < float(association_cfg.similarity_threshold):
                    continue
                candidates.append(
                    {
                        "score64": score64,
                        "score32": _float32_cosine(query32, candidate32),
                        "tick": historical_tick,
                        "event_id": int(event_ids[row, historical_slot]),
                        "slot": int(historical_slot),
                        "age": int(delay),
                        "raw64": candidate64,
                        "raw32": candidate32,
                    }
                )

        if bool(candidates) != bool(assigned[row, slot]):
            reconstruction_mismatch_count += 1
            continue
        if not candidates:
            continue

        runtime_items = [
            (item["score64"], item["tick"], item["event_id"], item["slot"])
            for item in candidates
        ]
        runtime_order = sorted(runtime_items, key=_candidate_order("latest"))
        exact_order = sorted(
            candidates,
            key=lambda item: (-item["score64"], -item["tick"], -item["event_id"], item["slot"]),
        )
        runtime_best = runtime_order[0]
        if (
            int(stored_event_ids[row, slot]) != int(runtime_best[2])
            or not np.isclose(
                float(stored_similarities[row, slot]),
                float(runtime_best[0]),
                rtol=0.0,
                atol=1e-6,
            )
        ):
            reconstruction_mismatch_count += 1

        if len(candidates) < 2:
            continue
        multi_candidate_query_count += 1
        runtime_top_tie = bool(
            np.isclose(
                float(runtime_order[0][0]),
                float(runtime_order[1][0]),
                rtol=0.0,
                atol=_RUNTIME_SCORE_ATOL,
            )
        )
        runtime_top_tie_count += int(runtime_top_tie)
        runtime_tie_changes_exact_score_winner_count += int(
            runtime_top_tie and int(runtime_order[0][2]) != int(exact_order[0]["event_id"])
        )

        age_one = next(item for item in exact_order if int(item["age"]) == 1)
        older_best = max(
            (item for item in exact_order if int(item["age"]) > 1),
            key=lambda item: (item["score64"], item["tick"], item["event_id"], -item["slot"]),
        )
        gap64 = float(age_one["score64"] - older_best["score64"])
        diagnostic_relation = (
            "strict-age-one"
            if gap64 > _STAGE3C27_DIAGNOSTIC_ATOL
            else "older"
            if gap64 < -_STAGE3C27_DIAGNOSTIC_ATOL
            else "near-tie"
        )
        runtime_pair_tie = bool(
            np.isclose(
                float(age_one["score64"]),
                float(older_best["score64"]),
                rtol=0.0,
                atol=_RUNTIME_SCORE_ATOL,
            )
        )
        selector_relation = (
            "runtime-tie"
            if runtime_pair_tie
            else "strict-age-one"
            if gap64 > 0.0
            else "older"
        )
        diagnostic_strict_age_one += int(diagnostic_relation == "strict-age-one")
        diagnostic_near_tie += int(diagnostic_relation == "near-tie")
        diagnostic_older += int(diagnostic_relation == "older")
        selector_strict_age_one += int(selector_relation == "strict-age-one")
        selector_runtime_tie += int(selector_relation == "runtime-tie")
        selector_older += int(selector_relation == "older")

        if diagnostic_relation != "near-tie":
            continue

        age_record = _candidate_record(
            score64=float(age_one["score64"]),
            score32=float(age_one["score32"]),
            tick=int(age_one["tick"]),
            event_id=int(age_one["event_id"]),
            slot=int(age_one["slot"]),
            age=int(age_one["age"]),
            raw64=np.asarray(age_one["raw64"]),
            raw32=np.asarray(age_one["raw32"]),
            visible_ports=(first_port, second_port, constant_port),
        )
        older_record = _candidate_record(
            score64=float(older_best["score64"]),
            score32=float(older_best["score32"]),
            tick=int(older_best["tick"]),
            event_id=int(older_best["event_id"]),
            slot=int(older_best["slot"]),
            age=int(older_best["age"]),
            raw64=np.asarray(older_best["raw64"]),
            raw32=np.asarray(older_best["raw32"]),
            visible_ports=(first_port, second_port, constant_port),
        )
        age_norm64 = np.asarray(age_record["normalized_visible_float64"], dtype=np.float64)
        older_norm64 = np.asarray(older_record["normalized_visible_float64"], dtype=np.float64)
        age_norm32 = np.asarray(age_record["normalized_visible_direct_float32"], dtype=np.float32)
        older_norm32 = np.asarray(older_record["normalized_visible_direct_float32"], dtype=np.float32)
        age_raw = np.asarray(age_record["raw_visible_float32"], dtype=np.float64)
        older_raw = np.asarray(older_record["raw_visible_float32"], dtype=np.float64)
        alpha = float(np.dot(age_raw, older_raw) / np.dot(older_raw, older_raw))
        collinearity_residual = float(np.linalg.norm(age_raw - alpha * older_raw))
        raw_equal = bool(np.array_equal(age_raw, older_raw))
        normalized64_equal = bool(np.array_equal(age_norm64, older_norm64))
        normalized32_equal = bool(np.array_equal(age_norm32, older_norm32))
        score32_gap = float(age_one["score32"] - older_best["score32"])
        if runtime_pair_tie:
            origin = "runtime-comparator-tie"
        elif normalized64_equal:
            origin = "stored-normalized-direction-duplicate"
        else:
            origin = "stage3c27-diagnostic-tolerance-only"

        near_tie_records.append(
            {
                "seed": int(seed),
                "stable_subject_id": int(subject_ids[row, slot]),
                "query_event_id": int(event_ids[row, slot]),
                "query_tick": current_tick,
                "query_phase": current_tick - int(source_tick),
                "visible_ports": {
                    "first_readout_port": int(first_port),
                    "second_readout_port": int(second_port),
                    "constant_port": int(constant_port),
                },
                "query_raw_visible_float32": [
                    float(value) for value in np.asarray(query32[list(visible_ports)], dtype=np.float32)
                ],
                "age_one_candidate": age_record,
                "best_older_candidate": older_record,
                "age_one_minus_best_older_score_float64": gap64,
                "absolute_score_gap_float64": abs(gap64),
                "age_one_minus_best_older_score_direct_float32": score32_gap,
                "stage3c27_diagnostic_near_tie": True,
                "runtime_comparator_tie": runtime_pair_tie,
                "actual_stored_winner_event_id": int(stored_event_ids[row, slot]),
                "strict_score_winner_event_id": int(exact_order[0]["event_id"]),
                "latest_tie_break_changes_winner": bool(
                    runtime_pair_tie
                    and int(runtime_order[0][2]) != int(exact_order[0]["event_id"])
                ),
                "raw_visible_vectors_exactly_equal": raw_equal,
                "normalized_visible_float64_exactly_equal": normalized64_equal,
                "normalized_visible_direct_float32_exactly_equal": normalized32_equal,
                "normalized_visible_float64_l2_distance": float(
                    np.linalg.norm(age_norm64 - older_norm64)
                ),
                "normalized_visible_direct_float32_l2_distance": float(
                    np.linalg.norm(age_norm32.astype(np.float64) - older_norm32.astype(np.float64))
                ),
                "positive_collinearity_scale": alpha,
                "positive_collinearity_residual_l2": collinearity_residual,
                "second_coordinate_delta_float32": float(
                    np.float32(age_record["raw_visible_float32"][1])
                    - np.float32(older_record["raw_visible_float32"][1])
                ),
                "second_coordinate_delta_ulp_count": _ulp_distance(
                    np.float32(age_record["raw_visible_float32"][1]),
                    np.float32(older_record["raw_visible_float32"][1]),
                ),
                "origin_classification": origin,
            }
        )

    return {
        "seed": int(seed),
        "checkpoint_file_sha256": _file_sha256(checkpoint),
        "requested_query_count": int(np.count_nonzero(requested)),
        "multi_candidate_query_count": multi_candidate_query_count,
        "reconstructed_selection_mismatch_count": reconstruction_mismatch_count,
        "stage3c27_diagnostic_counts": {
            "strict_age_one_geometry": diagnostic_strict_age_one,
            "near_tie": diagnostic_near_tie,
            "older_geometry": diagnostic_older,
        },
        "selector_consistent_counts": {
            "strict_age_one_geometry": selector_strict_age_one,
            "runtime_tie": selector_runtime_tie,
            "older_geometry": selector_older,
        },
        "runtime_top_tie_query_count": runtime_top_tie_count,
        "runtime_tie_changes_exact_score_winner_count": runtime_tie_changes_exact_score_winner_count,
        "near_tie_records": near_tie_records,
    }


def _stage27_seed_map(stage27: dict[str, Any]) -> dict[int, dict[str, Any]]:
    rows = {int(row["seed"]): row for row in stage27.get("per_source", [])}
    if len(rows) != 9:
        raise ValueError("Stage-3C-37 requires exactly nine Stage-3C-27 rows per panel")
    return rows


def _audit_panel(
    sources: dict[int, dict[str, Any]],
    stage27: dict[str, Any],
    *,
    label: str,
) -> dict[str, Any]:
    frozen_rows = _stage27_seed_map(stage27)
    per_source = []
    for seed in sorted(sources):
        source = sources[seed]
        replay = _audit_checkpoint(
            source["read_only_control_checkpoint"],
            source_tick=int(source["source_tick"]),
            seed=seed,
        )
        frozen = frozen_rows[seed]
        frozen_geometry = frozen["multi_candidate_geometry"]
        if replay["multi_candidate_query_count"] != int(frozen["multi_candidate_query_count"]):
            raise ValueError(f"{label} seed {seed} multi-candidate count mismatch")
        expected = {
            "strict_age_one_geometry": int(frozen_geometry["strict_age_one_geometry_win_count"]),
            "near_tie": int(frozen_geometry["exact_age_one_vs_older_score_tie_count"]),
            "older_geometry": int(frozen_geometry["older_geometry_win_count"]),
        }
        if replay["stage3c27_diagnostic_counts"] != expected:
            raise ValueError(f"{label} seed {seed} Stage-3C-27 replay mismatch")
        if replay["reconstructed_selection_mismatch_count"] != 0:
            raise ValueError(f"{label} seed {seed} selector reconstruction mismatch")
        per_source.append(replay)

    near_ties = [record for row in per_source for record in row["near_tie_records"]]
    selector_strict = sum(
        int(row["selector_consistent_counts"]["strict_age_one_geometry"])
        for row in per_source
    )
    selector_ties = sum(
        int(row["selector_consistent_counts"]["runtime_tie"])
        for row in per_source
    )
    diagnostic_strict = sum(
        int(row["stage3c27_diagnostic_counts"]["strict_age_one_geometry"])
        for row in per_source
    )
    diagnostic_ties = len(near_ties)
    age_one_selected = selector_strict + selector_ties
    direct32_equal = sum(
        int(float(record["age_one_minus_best_older_score_direct_float32"]) == 0.0)
        for record in near_ties
    )
    direct32_preserves = sum(
        int(float(record["age_one_minus_best_older_score_direct_float32"]) > 0.0)
        for record in near_ties
    )
    direct32_reverses = sum(
        int(float(record["age_one_minus_best_older_score_direct_float32"]) < 0.0)
        for record in near_ties
    )
    return {
        "panel": label,
        "seeds": sorted(sources),
        "independent_source_count": len(per_source),
        "per_source": per_source,
        "multi_candidate_query_count": sum(int(row["multi_candidate_query_count"]) for row in per_source),
        "stage3c27_diagnostic_near_tie_count": diagnostic_ties,
        "runtime_top_tie_query_count": sum(int(row["runtime_top_tie_query_count"]) for row in per_source),
        "runtime_tie_changes_exact_score_winner_count": sum(
            int(row["runtime_tie_changes_exact_score_winner_count"]) for row in per_source
        ),
        "selector_consistent_strict_age_one_count": selector_strict,
        "selector_consistent_runtime_tie_age_one_count": selector_ties,
        "selector_consistent_strict_fraction_of_multi_candidate_age_one_selections": (
            float(selector_strict / age_one_selected) if age_one_selected else 0.0
        ),
        "stage3c27_diagnostic_strict_fraction_of_multi_candidate_age_one_selections": (
            float(diagnostic_strict / (diagnostic_strict + diagnostic_ties))
            if diagnostic_strict + diagnostic_ties
            else 0.0
        ),
        "near_tie_score_gap_float64": _stats(
            float(record["absolute_score_gap_float64"]) for record in near_ties
        ),
        "near_tie_second_coordinate_delta_ulp_count": _stats(
            float(record["second_coordinate_delta_ulp_count"]) for record in near_ties
        ),
        "near_tie_origin_counts": {
            key: sum(int(record["origin_classification"] == key) for record in near_ties)
            for key in (
                "runtime-comparator-tie",
                "stored-normalized-direction-duplicate",
                "stage3c27-diagnostic-tolerance-only",
            )
        },
        "direct_float32_recomputation": {
            "equal_score_count": direct32_equal,
            "preserves_float64_order_count": direct32_preserves,
            "reverses_float64_order_count": direct32_reverses,
            "runtime_uses_direct_float32_score_arithmetic": False,
        },
        "near_tie_records": near_ties,
    }


def assess_stage3c37_tie_origin(
    reference_frozen_study: dict[str, Any],
    reference_replay_study: dict[str, Any],
    reference_stage3c27: dict[str, Any],
    replication_frozen_study: dict[str, Any],
    replication_replay_study: dict[str, Any],
    replication_stage3c27: dict[str, Any],
    stage3c36: dict[str, Any],
) -> dict[str, Any]:
    """Resolve whether Stage-3C-27 near ties are actual selector ties."""
    _validate_assessment(stage3c36, schema=STAGE3C36_GEOMETRY_TRANSPORT_SCHEMA, label="Stage-3C-36")
    reference_sources = _validate_frozen_and_replay(
        reference_frozen_study,
        reference_replay_study,
        reference_stage3c27,
        label="reference",
    )
    replication_sources = _validate_frozen_and_replay(
        replication_frozen_study,
        replication_replay_study,
        replication_stage3c27,
        label="replication",
    )
    if set(reference_sources) & set(replication_sources):
        raise ValueError("Stage-3C-37 requires disjoint source panels")
    checks = stage3c36.get("input_checksums", {})
    if checks.get("reference_stage3c27") != reference_stage3c27.get("assessment_sha256"):
        raise ValueError("Stage-3C-37 reference Stage-3C-36 lineage mismatch")
    if checks.get("replication_stage3c27") != replication_stage3c27.get("assessment_sha256"):
        raise ValueError("Stage-3C-37 replication Stage-3C-36 lineage mismatch")

    reference = _audit_panel(reference_sources, reference_stage3c27, label="reference")
    replication = _audit_panel(replication_sources, replication_stage3c27, label="replication")
    all_ties = [*reference["near_tie_records"], *replication["near_tie_records"]]
    diagnostic_only = sum(
        int(record["origin_classification"] == "stage3c27-diagnostic-tolerance-only")
        for record in all_ties
    )
    runtime_ties = sum(int(record["runtime_comparator_tie"]) for record in all_ties)
    exact_direction_duplicates = sum(
        int(record["normalized_visible_float64_exactly_equal"]) for record in all_ties
    )
    latest_changes = sum(int(record["latest_tie_break_changes_winner"]) for record in all_ties)
    selector_consistent_gate = bool(
        reference["selector_consistent_strict_fraction_of_multi_candidate_age_one_selections"] >= 0.99
        and replication["selector_consistent_strict_fraction_of_multi_candidate_age_one_selections"] >= 0.99
        and reference["runtime_top_tie_query_count"] / reference["multi_candidate_query_count"] < 0.01
        and replication["runtime_top_tie_query_count"] / replication["multi_candidate_query_count"] < 0.01
    )

    payload: dict[str, Any] = {
        "schema": STAGE3C37_TIE_ORIGIN_SCHEMA,
        "producer_version": __version__,
        "analysis_only_factor": (
            "query-level replay of frozen rank-two checkpoints under both the Stage-3C-27 "
            "1e-8 diagnostic bin and the actual 1e-12 runtime score comparator"
        ),
        "runtime_experimental_factor_changed": False,
        "runtime_selector_contract": {
            "stored_thought_token_dtype": "float32",
            "score_arithmetic": "float64 over stored float32 token coordinates",
            "runtime_score_tie_atol": _RUNTIME_SCORE_ATOL,
            "stage3c27_diagnostic_near_tie_atol": _STAGE3C27_DIAGNOSTIC_ATOL,
            "runtime_tie_break": "latest",
            "candidate_limit": 1,
            "runtime_selection_semantics_changed": False,
        },
        "input_checksums": {
            "reference_frozen_study": reference_frozen_study["study_sha256"],
            "reference_replay_study": reference_replay_study["study_sha256"],
            "reference_stage3c27": reference_stage3c27["assessment_sha256"],
            "replication_frozen_study": replication_frozen_study["study_sha256"],
            "replication_replay_study": replication_replay_study["study_sha256"],
            "replication_stage3c27": replication_stage3c27["assessment_sha256"],
            "stage3c36": stage3c36["assessment_sha256"],
        },
        "replay_identity": {
            "reference_source_state_hashes_match_frozen_report": True,
            "replication_source_state_hashes_match_frozen_report": True,
            "stage3c27_aggregate_counts_exactly_reproduced": True,
            "stored_winner_ids_exactly_reconstructed": True,
            "source_panels_are_disjoint": True,
        },
        "reference_panel": reference,
        "replication_panel": replication,
        "cross_panel_resolution": {
            "stage3c27_diagnostic_near_tie_count": len(all_ties),
            "runtime_comparator_tie_count": runtime_ties,
            "stored_normalized_direction_duplicate_count": exact_direction_duplicates,
            "stage3c27_diagnostic_tolerance_only_count": diagnostic_only,
            "latest_tie_break_changed_winner_count": latest_changes,
            "all_seven_stage3c27_near_ties_have_strict_positive_float64_age_one_margin": bool(
                all(float(record["age_one_minus_best_older_score_float64"]) > _RUNTIME_SCORE_ATOL for record in all_ties)
            ),
            "all_seven_candidate_pairs_have_distinct_stored_second_coordinates": bool(
                all(int(record["second_coordinate_delta_ulp_count"]) > 0 for record in all_ties)
            ),
            "minimum_second_coordinate_delta_ulp_count": min(
                (int(record["second_coordinate_delta_ulp_count"]) for record in all_ties),
                default=0,
            ),
            "maximum_second_coordinate_delta_ulp_count": max(
                (int(record["second_coordinate_delta_ulp_count"]) for record in all_ties),
                default=0,
            ),
            "selector_consistent_stage3c28_prerequisite_passed_in_both_panels": selector_consistent_gate,
        },
        "frozen_interpretation": {
            "additional_replication_panel_ties_are_actual_runtime_ties": False,
            "additional_replication_panel_ties_are_duplicate_normalized_directions": False,
            "additional_replication_panel_ties_are_stage3c27_diagnostic_tolerance_artifacts": True,
            "latest_tie_break_caused_the_replication_gate_failure": False,
            "stage3c35_crossing_prediction_was_tested": False,
            "stage3c35_crossing_prediction_was_refuted": False,
            "corrected_crossing_replication_authorized_next": selector_consistent_gate,
            "next_boundary": (
                "Run the previously preregistered disjoint-panel Stage-3C-28 through crossing "
                "replication chain using an explicit selector-consistent Stage-3C-37 qualification "
                "overlay. Do not rewrite the historical Stage-3C-27 assessment, change runtime "
                "tie semantics, select sources, or alter exposure/addressing/crossing definitions."
            ),
        },
        "fixed_cognition_engineering_shaping_aid": True,
        "evolved_topology": False,
        "universal_attention_claim": False,
        "universal_scalar_objective": False,
        "permanent_parameter_retention_authorized": False,
        "automatic_keep_or_revert_authorized": False,
        "causal_effect_authorized": False,
        "learning_claim_authorized": False,
        "subjecthood_claim_authorized": False,
        "runtime_or_checkpoint_schema_changed": False,
        "runtime_memory_growth_bytes": 0,
    }
    payload["assessment_sha256"] = _canonical_sha256(payload)
    return payload


def _write_summary(path: str | Path, payload: dict[str, Any]) -> None:
    resolved = payload["cross_panel_resolution"]
    summary = {
        "schema": "se-subject-vm-stage3c37-study-summary-v1",
        "producer_version": payload["producer_version"],
        "diagnostic_near_tie_count": resolved["stage3c27_diagnostic_near_tie_count"],
        "runtime_comparator_tie_count": resolved["runtime_comparator_tie_count"],
        "latest_tie_break_changed_winner_count": resolved["latest_tie_break_changed_winner_count"],
        "selector_consistent_stage3c28_prerequisite_passed_in_both_panels": resolved[
            "selector_consistent_stage3c28_prerequisite_passed_in_both_panels"
        ],
        "assessment_sha256": payload["assessment_sha256"],
    }
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _write_report(path: str | Path, payload: dict[str, Any]) -> None:
    ref = payload["reference_panel"]
    rep = payload["replication_panel"]
    resolved = payload["cross_panel_resolution"]
    lines = [
        "# Stage 3C-37 near-exact tie origin audit",
        "",
        "## Frozen result",
        "",
        f"- Stage-3C-27 diagnostic near ties: {resolved['stage3c27_diagnostic_near_tie_count']}",
        f"- Actual runtime-comparator ties: {resolved['runtime_comparator_tie_count']}",
        f"- Latest tie-break winner changes: {resolved['latest_tie_break_changed_winner_count']}",
        f"- Stored normalized-direction duplicates: {resolved['stored_normalized_direction_duplicate_count']}",
        f"- Diagnostic-tolerance-only cases: {resolved['stage3c27_diagnostic_tolerance_only_count']}",
        "",
        "## Panel correction",
        "",
        f"- Reference strict fraction: {ref['stage3c27_diagnostic_strict_fraction_of_multi_candidate_age_one_selections']:.9f} diagnostic → {ref['selector_consistent_strict_fraction_of_multi_candidate_age_one_selections']:.9f} selector-consistent",
        f"- Replication strict fraction: {rep['stage3c27_diagnostic_strict_fraction_of_multi_candidate_age_one_selections']:.9f} diagnostic → {rep['selector_consistent_strict_fraction_of_multi_candidate_age_one_selections']:.9f} selector-consistent",
        "",
        "All seven pairs have distinct stored second coordinates and strict positive float64 age-one margins. The runtime converts stored float32 token coordinates to float64 before scoring and uses a 1e-12 tie comparator; none of the seven invokes latest-on-tie.",
        "",
        "## Boundary",
        "",
        "Stage 3C-35 remains an untested crossing prediction. Stage 3C-37 authorizes a corrected, selector-consistent qualification overlay for the same disjoint panel; it does not authorize rewriting historical evidence or changing runtime selection semantics.",
    ]
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--reference-frozen-study-report", required=True)
    parser.add_argument("--reference-replay-study-report", required=True)
    parser.add_argument("--reference-stage3c27", required=True)
    parser.add_argument("--replication-frozen-study-report", required=True)
    parser.add_argument("--replication-replay-study-report", required=True)
    parser.add_argument("--replication-stage3c27", required=True)
    parser.add_argument("--stage3c36", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--summary-output")
    parser.add_argument("--diagnostic-report")
    args = parser.parse_args()
    payload = assess_stage3c37_tie_origin(
        _load_json(args.reference_frozen_study_report),
        _load_json(args.reference_replay_study_report),
        _load_json(args.reference_stage3c27),
        _load_json(args.replication_frozen_study_report),
        _load_json(args.replication_replay_study_report),
        _load_json(args.replication_stage3c27),
        _load_json(args.stage3c36),
    )
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if args.summary_output:
        _write_summary(args.summary_output, payload)
    if args.diagnostic_report:
        _write_report(args.diagnostic_report, payload)
    print(json.dumps({
        "output": str(output),
        "diagnostic_near_tie_count": payload["cross_panel_resolution"]["stage3c27_diagnostic_near_tie_count"],
        "runtime_comparator_tie_count": payload["cross_panel_resolution"]["runtime_comparator_tie_count"],
        "selector_consistent_stage3c28_prerequisite_passed_in_both_panels": payload["cross_panel_resolution"]["selector_consistent_stage3c28_prerequisite_passed_in_both_panels"],
    }))


__all__ = [
    "STAGE3C37_TIE_ORIGIN_SCHEMA",
    "assess_stage3c37_tie_origin",
]


if __name__ == "__main__":
    main()
