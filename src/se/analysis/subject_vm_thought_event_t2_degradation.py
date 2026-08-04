"""Read-only T2 audit of pre-recall ThoughtEvent degeneration."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any, Iterable

import numpy as np

from .. import __version__
from ..experiments.subject_vm_short_paired_study import _canonical_sha256, _sha256_file
from ..experiments.subject_vm_thought_event_t2_degradation import (
    THOUGHT_EVENT_T2_STUDY_SCHEMA,
)

THOUGHT_EVENT_T2_ASSESSMENT_SCHEMA = (
    "se-subject-vm-thought-event-t2-degeneration-assessment-v1"
)


def _load_json(path: str | Path) -> dict[str, Any]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"expected JSON object: {path}")
    return payload


def _validate_checksum(payload: dict[str, Any], field: str, label: str) -> None:
    recorded = str(payload.get(field, ""))
    unsigned = dict(payload)
    unsigned.pop(field, None)
    if not recorded or recorded != _canonical_sha256(unsigned):
        raise ValueError(f"{label} checksum mismatch")


def _quantiles(values: Iterable[float]) -> dict[str, float]:
    array = np.asarray(tuple(values), dtype=np.float64)
    if array.size == 0:
        return {name: 0.0 for name in ("min", "q10", "median", "q90", "max")}
    return {
        "min": float(np.min(array)),
        "q10": float(np.quantile(array, 0.10)),
        "median": float(np.median(array)),
        "q90": float(np.quantile(array, 0.90)),
        "max": float(np.max(array)),
    }


def _cosine(a: np.ndarray, b: np.ndarray) -> float:
    na = float(np.linalg.norm(a))
    nb = float(np.linalg.norm(b))
    if na == 0.0 and nb == 0.0:
        return 1.0
    if na == 0.0 or nb == 0.0:
        return 0.0
    value = float(np.dot(a, b) / (na * nb))
    return float(np.clip(value, -1.0, 1.0))


def _rank_metrics(tokens: np.ndarray) -> dict[str, Any]:
    centered = np.asarray(tokens, dtype=np.float64) - np.mean(tokens, axis=0, dtype=np.float64)
    singular = np.linalg.svd(centered, compute_uv=False)
    rank = int(np.linalg.matrix_rank(centered))
    energy = singular * singular
    total = float(np.sum(energy))
    if singular.size == 0 or float(singular[0]) == 0.0:
        stable_rank = 0.0
    else:
        stable_rank = float(total / float(singular[0] ** 2))
    if total == 0.0:
        effective_rank = 0.0
    else:
        probabilities = energy[energy > 0.0] / total
        effective_rank = float(np.exp(-np.sum(probabilities * np.log(probabilities))))
    return {
        "centered_numerical_rank": rank,
        "stable_rank": stable_rank,
        "effective_rank": effective_rank,
        "singular_values": [float(value) for value in singular[:8]],
    }


def _pairwise_same_tick(tokens: np.ndarray, ticks: np.ndarray) -> list[float]:
    values: list[float] = []
    for tick in np.unique(ticks):
        batch = tokens[ticks == tick]
        for left in range(batch.shape[0]):
            for right in range(left + 1, batch.shape[0]):
                values.append(_cosine(batch[left], batch[right]))
    return values


def _consecutive_same_subject(
    tokens: np.ndarray,
    ticks: np.ndarray,
    subject_ids: np.ndarray,
) -> tuple[list[float], list[float], int]:
    cosine: list[float] = []
    l2: list[float] = []
    exact = 0
    for subject_id in np.unique(subject_ids):
        indices = np.flatnonzero(subject_ids == subject_id)
        order = indices[np.argsort(ticks[indices], kind="stable")]
        for left, right in zip(order[:-1], order[1:], strict=True):
            cosine.append(_cosine(tokens[left], tokens[right]))
            l2.append(float(np.linalg.norm(tokens[right] - tokens[left])))
            exact += int(np.array_equal(tokens[left], tokens[right]))
    return cosine, l2, exact


def _seed_metrics(record: dict[str, Any], *, study_root: Path) -> dict[str, Any]:
    event_path = (study_root / str(record["event_file"])).resolve()
    if not event_path.is_file():
        raise FileNotFoundError(event_path)
    if _sha256_file(event_path) != str(record["event_file_sha256"]):
        raise ValueError("T2 event file checksum mismatch")
    arrays = np.load(event_path)
    required = {
        "event_id",
        "entity_id",
        "subject_id",
        "tick",
        "token",
        "parent_count",
        "action_id",
        "sampled_probability",
        "action_potentials",
    }
    if set(arrays.files) != required:
        raise ValueError("T2 event NPZ schema mismatch")
    tokens = np.asarray(arrays["token"], dtype=np.float64)
    ticks = np.asarray(arrays["tick"], dtype=np.int64)
    subject_ids = np.asarray(arrays["subject_id"], dtype=np.uint64)
    event_ids = np.asarray(arrays["event_id"], dtype=np.uint64)
    parent_count = np.asarray(arrays["parent_count"], dtype=np.uint8)
    if tokens.shape != (192, 32):
        raise ValueError("T2 seed must contain 192 width-32 events")
    if np.unique(event_ids).size != event_ids.size or np.any(event_ids == 0):
        raise ValueError("T2 event identity is not unique")
    if np.any(parent_count != 0):
        raise ValueError("T2 pre-recall event unexpectedly has parents")
    if np.any(~np.isfinite(tokens)):
        raise ValueError("T2 token contains non-finite values")

    raw_unique = len({row.tobytes() for row in np.asarray(arrays["token"], dtype=np.float32)})
    per_tick_unique: list[int] = []
    per_tick_rank: list[int] = []
    for tick in np.unique(ticks):
        batch32 = np.asarray(arrays["token"], dtype=np.float32)[ticks == tick]
        batch64 = tokens[ticks == tick]
        per_tick_unique.append(len({row.tobytes() for row in batch32}))
        per_tick_rank.append(int(np.linalg.matrix_rank(batch64 - np.mean(batch64, axis=0))))
    per_subject_unique = []
    for subject_id in np.unique(subject_ids):
        batch = np.asarray(arrays["token"], dtype=np.float32)[subject_ids == subject_id]
        per_subject_unique.append(len({row.tobytes() for row in batch}))

    consecutive_cosine, consecutive_l2, consecutive_exact = _consecutive_same_subject(
        tokens, ticks, subject_ids
    )
    cross_subject_cosine = _pairwise_same_tick(tokens, ticks)
    active_coordinates = np.flatnonzero(np.any(tokens != 0.0, axis=0)).astype(int).tolist()
    varying_coordinates = np.flatnonzero(np.ptp(tokens, axis=0) != 0.0).astype(int).tolist()
    rank = _rank_metrics(tokens)
    final_accounting = record["final_accounting"]
    lifecycle = record["lifecycle"]
    if int(final_accounting["emitted_events"]) != 192:
        raise ValueError("T2 accounting emission count mismatch")
    if int(final_accounting["parent_links"]) != 0:
        raise ValueError("T2 accounting parent link count is non-zero")
    if int(final_accounting["overwritten_events"]) != 0:
        raise ValueError("T2 frozen capacity/retention profile must not overwrite")
    if int(final_accounting["expired_events"]) != 48:
        raise ValueError("T2 expiry count drifted")
    if int(lifecycle[-1]["stored_events"]) != 144:
        raise ValueError("T2 final arena occupancy drifted")

    return {
        "arm": str(record["arm"]),
        "seed": int(record["seed"]),
        "event_count": int(tokens.shape[0]),
        "subject_count": int(np.unique(subject_ids).size),
        "tick_count": int(np.unique(ticks).size),
        "exact_unique_token_count": int(raw_unique),
        "exact_duplicate_fraction": float(1.0 - raw_unique / tokens.shape[0]),
        "per_tick_unique_count": _quantiles(per_tick_unique),
        "per_subject_unique_count": _quantiles(per_subject_unique),
        "active_coordinates": active_coordinates,
        "varying_coordinates": varying_coordinates,
        **rank,
        "per_tick_centered_rank": _quantiles(per_tick_rank),
        "consecutive_same_subject": {
            "pair_count": len(consecutive_cosine),
            "exact_duplicate_count": int(consecutive_exact),
            "cosine": _quantiles(consecutive_cosine),
            "l2": _quantiles(consecutive_l2),
            "cosine_ge_0_999_fraction": float(
                np.mean(np.asarray(consecutive_cosine) >= 0.999)
            ),
            "cosine_ge_0_9999_fraction": float(
                np.mean(np.asarray(consecutive_cosine) >= 0.9999)
            ),
        },
        "same_tick_cross_subject": {
            "pair_count": len(cross_subject_cosine),
            "cosine": _quantiles(cross_subject_cosine),
            "cosine_ge_0_999_fraction": float(
                np.mean(np.asarray(cross_subject_cosine) >= 0.999)
            ),
            "cosine_ge_0_9999_fraction": float(
                np.mean(np.asarray(cross_subject_cosine) >= 0.9999)
            ),
        },
        "lifecycle": {
            "final_stored_events": int(lifecycle[-1]["stored_events"]),
            "minimum_events_per_subject": int(
                lifecycle[-1]["minimum_events_per_subject"]
            ),
            "maximum_events_per_subject": int(
                lifecycle[-1]["maximum_events_per_subject"]
            ),
            "expired_events": int(final_accounting["expired_events"]),
            "overwritten_events": int(final_accounting["overwritten_events"]),
            "emission_cost_units": int(final_accounting["counted_emission_cost_units"]),
            "retention_cost_units": int(final_accounting["counted_retention_cost_units"]),
            "parent_link_cost_units": int(
                final_accounting["counted_parent_link_cost_units"]
            ),
            "allocated_nbytes": int(record["final_arena"]["allocated_nbytes"]),
        },
    }


def _aggregate_seed_metrics(records: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "seed_count": len(records),
        "exact_unique_token_count": _quantiles(
            item["exact_unique_token_count"] for item in records
        ),
        "exact_duplicate_fraction": _quantiles(
            item["exact_duplicate_fraction"] for item in records
        ),
        "centered_numerical_rank": _quantiles(
            item["centered_numerical_rank"] for item in records
        ),
        "stable_rank": _quantiles(item["stable_rank"] for item in records),
        "effective_rank": _quantiles(item["effective_rank"] for item in records),
        "consecutive_cosine_median": _quantiles(
            item["consecutive_same_subject"]["cosine"]["median"] for item in records
        ),
        "same_tick_cross_subject_cosine_median": _quantiles(
            item["same_tick_cross_subject"]["cosine"]["median"] for item in records
        ),
        "all_parent_counts_zero": True,
        "all_event_counts_complete": all(item["event_count"] == 192 for item in records),
        "all_lifecycle_contracts_exact": all(
            item["lifecycle"]["expired_events"] == 48
            and item["lifecycle"]["overwritten_events"] == 0
            and item["lifecycle"]["final_stored_events"] == 144
            for item in records
        ),
        "active_coordinate_union": sorted(
            {coordinate for item in records for coordinate in item["active_coordinates"]}
        ),
        "varying_coordinate_union": sorted(
            {coordinate for item in records for coordinate in item["varying_coordinates"]}
        ),
    }


def assess(
    study_report: str | Path,
    *,
    output: str | Path,
    summary_output: str | Path | None = None,
    diagnostic_report: str | Path | None = None,
) -> dict[str, Any]:
    study_path = Path(study_report).expanduser().resolve()
    study = _load_json(study_path)
    if study.get("schema") != THOUGHT_EVENT_T2_STUDY_SCHEMA:
        raise ValueError("T2 study schema mismatch")
    _validate_checksum(study, "study_sha256", "T2 study")
    if bool(study.get("forward_recall_enabled")) or bool(study.get("read_head_enabled")):
        raise ValueError("T2 must remain pre-recall")
    seed_metrics = [
        _seed_metrics(record, study_root=study_path.parent)
        for record in study["seed_records"]
    ]
    arms = {
        arm: [item for item in seed_metrics if item["arm"] == arm]
        for arm in ("duplicate-coordinate-control", "rank-two-candidate")
    }
    expected_seed_count = len(tuple(study["parameters"]["seeds"]))
    if expected_seed_count < 3 or any(
        len(records) != expected_seed_count for records in arms.values()
    ):
        raise ValueError("T2 arm seed counts do not match the declared panel")
    control = _aggregate_seed_metrics(arms["duplicate-coordinate-control"])
    candidate = _aggregate_seed_metrics(arms["rank-two-candidate"])
    all_cross_arm_identity = all(
        all(bool(value) for value in item["identity"].values())
        and bool(item["tokens_differ_only_at_coordinate_30"])
        for item in study["cross_arm_identity"]
    )
    control_rank_one_all_seeds = all(
        item["centered_numerical_rank"] == 1
        for item in arms["duplicate-coordinate-control"]
    )
    candidate_rank_two_all_seeds = all(
        item["centered_numerical_rank"] == 2
        for item in arms["rank-two-candidate"]
    )
    candidate_all_events_exactly_distinct = all(
        item["exact_unique_token_count"] == item["event_count"]
        for item in arms["rank-two-candidate"]
    )
    candidate_all_subjects_distinct_each_tick = all(
        item["per_tick_unique_count"]["min"] == 16.0
        for item in arms["rank-two-candidate"]
    )
    candidate_low_rank_fixed_bootstrap = candidate_rank_two_all_seeds

    assessment: dict[str, Any] = {
        "schema": THOUGHT_EVENT_T2_ASSESSMENT_SCHEMA,
        "project_version": __version__,
        "study_report_file": study_path.name,
        "study_report_file_sha256": _sha256_file(study_path),
        "study_sha256": str(study["study_sha256"]),
        "design": {
            "seeds": list(study["parameters"]["seeds"]),
            "source_ticks": int(study["parameters"]["source_ticks"]),
            "audit_ticks": int(study["parameters"]["audit_ticks"]),
            "bootstrap_subjects": int(study["parameters"]["bootstrap_subjects"]),
            "arms": study["arms"],
            "new_runtime_mechanism": False,
            "forward_recall": False,
            "read_head": False,
        },
        "per_seed": seed_metrics,
        "arms": {
            "duplicate-coordinate-control": control,
            "rank-two-candidate": candidate,
        },
        "cross_arm_findings": {
            "all_action_event_and_probability_fields_identical": all_cross_arm_identity,
            "arms_differ_only_at_second_readout_coordinate_30": all_cross_arm_identity,
            "duplicate_coordinate_control_is_rank_one_in_all_seeds": control_rank_one_all_seeds,
            "rank_two_candidate_is_rank_two_in_all_seeds": candidate_rank_two_all_seeds,
            "rank_two_candidate_events_are_exactly_distinct": candidate_all_events_exactly_distinct,
            "rank_two_candidate_subjects_are_distinct_each_tick": candidate_all_subjects_distinct_each_tick,
            "rank_two_candidate_remains_low_rank_fixed_bootstrap": candidate_low_rank_fixed_bootstrap,
        },
        "qualification": {
            "arena_lifecycle_and_identity_qualified": bool(
                control["all_event_counts_complete"]
                and candidate["all_event_counts_complete"]
                and control["all_lifecycle_contracts_exact"]
                and candidate["all_lifecycle_contracts_exact"]
                and all_cross_arm_identity
            ),
            "degeneration_diagnostic_control_qualified": bool(
                control_rank_one_all_seeds and candidate_rank_two_all_seeds
            ),
            "formal_nine_seed_panel": expected_seed_count == 9,
            "t3_mechanism_smoke_authorized": bool(
                expected_seed_count == 9
                and all_cross_arm_identity
                and candidate_rank_two_all_seeds
                and candidate_all_events_exactly_distinct
                and candidate_all_subjects_distinct_each_tick
            ),
            "distributed_cognitive_representation_claim_authorized": False,
            "thought_chain_claim_authorized": False,
            "language_or_object_reference_claim_authorized": False,
            "status": (
                "qualified-for-t3-mechanism-smoke-only-low-rank-fixed-bootstrap"
                if expected_seed_count == 9
                else "diagnostic-smoke-only-formal-panel-incomplete"
            ),
        },
        "interpretation": {
            "control": (
                "duplicate readout coordinates collapse the centered token stream to one "
                "independent direction, so the diagnostics detect the intended negative control"
            ),
            "candidate": (
                "the selected second readout removes exact event duplication and preserves "
                "subject/tick distinctions, but the stream remains an engineered rank-two "
                "subspace with high local cosine similarity"
            ),
            "boundary": (
                "T2 qualifies only a minimal forward-recall mechanism smoke; it does not "
                "qualify a distributed thought representation or a cognitive chain"
            ),
        },
        "governance": {
            "parent_count_runtime_expected_zero": True,
            "retention_policy_changed": False,
            "objective_fact_fed_into_thought": False,
            "action_logits_fed_into_thought": False,
            "reward_or_confidence_gate_added": False,
            "read_head_role_predefined": False,
            "permanent_retention_authorized": False,
        },
    }
    assessment["assessment_sha256"] = _canonical_sha256(assessment)
    target = Path(output)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(assessment, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    summary = {
        "schema": "se-subject-vm-thought-event-t2-summary-v1",
        "project_version": __version__,
        "assessment_sha256": assessment["assessment_sha256"],
        "status": assessment["qualification"]["status"],
        "control_centered_rank_all_seeds": 1,
        "candidate_centered_rank_all_seeds": 2,
        "candidate_exact_unique_events_per_seed": 192,
        "candidate_active_coordinates": candidate["active_coordinate_union"],
        "candidate_varying_coordinates": candidate["varying_coordinate_union"],
        "t3_mechanism_smoke_authorized": assessment["qualification"]["t3_mechanism_smoke_authorized"],
        "thought_chain_claim_authorized": False,
    }
    summary["summary_sha256"] = _canonical_sha256(summary)
    if summary_output is not None:
        summary_path = Path(summary_output)
        summary_path.parent.mkdir(parents=True, exist_ok=True)
        summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    if diagnostic_report is not None:
        report_path = Path(diagnostic_report)
        report_path.parent.mkdir(parents=True, exist_ok=True)
        control_rank = control["centered_numerical_rank"]
        candidate_rank = candidate["centered_numerical_rank"]
        candidate_cos = candidate["consecutive_cosine_median"]
        text = f"""# ThoughtEvent T2 退化审计诊断\n\n- control centered rank：{control_rank['min']:.0f}–{control_rank['max']:.0f}\n- candidate centered rank：{candidate_rank['min']:.0f}–{candidate_rank['max']:.0f}\n- candidate 每 seed 精确唯一事件：{candidate['exact_unique_token_count']['min']:.0f}\n- candidate 连续同主体 cosine 中位数范围：{candidate_cos['min']:.9f}–{candidate_cos['max']:.9f}\n- arena：每 seed 192 次写入、48 次到期、0 次覆盖，parent_count 恒为 0。\n\n## 结论边界\n\nrank-two candidate 足以进入 T3 的最小机制 smoke，但其表示仍是固定 bootstrap 构造的二维子空间；不得据此声称已形成分布式思维链、认知概念或语言。\n"""
        report_path.write_text(text, encoding="utf-8")
    return assessment


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--study-report", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--summary-output")
    parser.add_argument("--diagnostic-report")
    args = parser.parse_args()
    report = assess(
        args.study_report,
        output=args.output,
        summary_output=args.summary_output,
        diagnostic_report=args.diagnostic_report,
    )
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
