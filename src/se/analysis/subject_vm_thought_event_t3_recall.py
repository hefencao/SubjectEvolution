"""Assess the frozen T3 minimal forward ThoughtEvent recall smoke."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any, Iterable

import numpy as np

from .. import __version__
from ..experiments.subject_vm_short_paired_study import _canonical_sha256, _sha256_file
from ..experiments.subject_vm_thought_event_t3_recall import (
    THOUGHT_EVENT_T3_STUDY_SCHEMA,
)

THOUGHT_EVENT_T3_ASSESSMENT_SCHEMA = "se-subject-vm-thought-event-t3-recall-assessment-v1"
_EXPECTED_ARMS = (
    "no-recall",
    "identity-recall",
    "rotate-one-coordinate-control",
    "zero-content-equal-cost-control",
)


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _quantiles(values: Iterable[float]) -> dict[str, float]:
    array = np.asarray(tuple(values), dtype=np.float64)
    if array.size == 0:
        return {key: 0.0 for key in ("min", "q25", "median", "q75", "max")}
    return {
        "min": float(np.min(array)),
        "q25": float(np.quantile(array, 0.25)),
        "median": float(np.median(array)),
        "q75": float(np.quantile(array, 0.75)),
        "max": float(np.max(array)),
    }


def _cosine_rows(left: np.ndarray, right: np.ndarray) -> np.ndarray:
    left64 = np.asarray(left, dtype=np.float64)
    right64 = np.asarray(right, dtype=np.float64)
    numerator = np.sum(left64 * right64, axis=1)
    denominator = np.linalg.norm(left64, axis=1) * np.linalg.norm(right64, axis=1)
    result = np.zeros(left64.shape[0], dtype=np.float64)
    both_zero = denominator == 0.0
    result[both_zero & (np.linalg.norm(left64, axis=1) == 0.0) & (np.linalg.norm(right64, axis=1) == 0.0)] = 1.0
    nonzero = denominator != 0.0
    result[nonzero] = numerator[nonzero] / denominator[nonzero]
    return np.clip(result, -1.0, 1.0)


def _load_seed_events(study_root: Path, record: dict[str, Any]) -> dict[str, np.ndarray]:
    path = (study_root / str(record["event_file"])).resolve()
    if not path.is_file():
        raise FileNotFoundError(path)
    if _sha256_file(path) != str(record["event_file_sha256"]):
        raise ValueError("T3 event file checksum mismatch")
    arrays = dict(np.load(path))
    required = {
        "event_id",
        "entity_id",
        "subject_id",
        "tick",
        "token",
        "parent_count",
        "parent_event_id",
        "parent_tick",
        "parent_weight",
        "parent_token",
        "action_id",
        "sampled_probability",
        "action_potentials",
    }
    if set(arrays) != required:
        raise ValueError("T3 event NPZ schema mismatch")
    if arrays["token"].shape != (160, 32):
        raise ValueError("T3 seed must contain 160 width-32 events")
    if np.unique(arrays["event_id"]).size != 160 or np.any(arrays["event_id"] == 0):
        raise ValueError("T3 event identity is incomplete or duplicated")
    if np.any(~np.isfinite(arrays["token"])):
        raise ValueError("T3 token contains non-finite values")
    return arrays


def _record_index(report: dict[str, Any]) -> dict[tuple[str, int], dict[str, Any]]:
    records: dict[tuple[str, int], dict[str, Any]] = {}
    for record in report["seed_records"]:
        key = (str(record["arm"]), int(record["seed"]))
        if key in records:
            raise ValueError("T3 duplicate arm/seed record")
        records[key] = record
    expected = {
        (arm, int(seed))
        for arm in _EXPECTED_ARMS
        for seed in report["parameters"]["seeds"]
    }
    if set(records) != expected:
        raise ValueError("T3 arm/seed support mismatch")
    return records


def _cost_tuple(record: dict[str, Any]) -> tuple[int, ...]:
    recall = record["final_recall_accounting"]
    thought = record["final_thought_event_accounting"]
    return (
        int(recall["recall_calls"]),
        int(recall["requested_rows"]),
        int(recall["candidate_slots_scanned"]),
        int(recall["selected_events"]),
        int(recall["read_coordinates"]),
        int(recall["ingress_paths"]),
        int(recall["counted_search_cost_units"]),
        int(recall["counted_read_cost_units"]),
        int(recall["counted_ingress_cost_units"]),
        int(thought["parent_links"]),
        int(thought["counted_parent_link_cost_units"]),
    )


def _seed_assessment(
    seed: int,
    *,
    records: dict[tuple[str, int], dict[str, Any]],
    study_root: Path,
    recall_gate: float,
) -> dict[str, Any]:
    arrays = {
        arm: _load_seed_events(study_root, records[(arm, seed)])
        for arm in _EXPECTED_ARMS
    }
    no_recall = arrays["no-recall"]
    zero = arrays["zero-content-equal-cost-control"]
    identity = arrays["identity-recall"]
    rotated = arrays["rotate-one-coordinate-control"]

    invariant_fields = (
        "event_id",
        "entity_id",
        "subject_id",
        "tick",
        "action_id",
        "sampled_probability",
        "action_potentials",
    )
    semantic_identity = {
        arm: {field: bool(np.array_equal(no_recall[field], value[field])) for field in invariant_fields}
        for arm, value in arrays.items()
    }
    if not all(all(fields.values()) for fields in semantic_identity.values()):
        raise ValueError("T3 recall changed action/event semantics")
    if not np.array_equal(no_recall["token"], zero["token"]):
        raise ValueError("T3 zero-content equal-cost control changed token content")

    enabled_arms = (
        "identity-recall",
        "rotate-one-coordinate-control",
        "zero-content-equal-cost-control",
    )
    expected_parent_count = np.where(
        np.tile(np.arange(10, dtype=np.int64), 16) == -1, 0, 0
    )
    del expected_parent_count  # explicit event checks below avoid ordering assumptions
    for arm in enabled_arms:
        linked = arrays[arm]["parent_count"] == 1
        if int(np.count_nonzero(linked)) != 144:
            raise ValueError("T3 enabled arm parent-link count drifted")
        if np.any(~np.isin(arrays[arm]["parent_count"], (0, 1))):
            raise ValueError("T3 parent count exceeds single-path contract")
        roots_by_subject = []
        for subject_id in np.unique(arrays[arm]["subject_id"]):
            mask = arrays[arm]["subject_id"] == subject_id
            order = np.argsort(arrays[arm]["tick"][mask], kind="stable")
            counts = arrays[arm]["parent_count"][mask][order]
            roots_by_subject.append(int(np.count_nonzero(counts == 0)))
            if counts[0] != 0 or np.any(counts[1:] != 1):
                raise ValueError("T3 enabled arm must form one latest-prior chain per subject")
        if roots_by_subject != [1] * 16:
            raise ValueError("T3 enabled arm root count drifted")
        if np.any(arrays[arm]["parent_tick"][linked] != arrays[arm]["tick"][linked] - 1):
            raise ValueError("T3 selector did not choose the latest strict-prior event")
        if np.any(arrays[arm]["parent_event_id"][linked] == 0):
            raise ValueError("T3 linked parent identity is zero")
        if not np.allclose(
            arrays[arm]["parent_weight"][linked], recall_gate, atol=0.0, rtol=0.0
        ):
            raise ValueError("T3 parent weight drifted from graph ingress gate")
    if np.any(no_recall["parent_count"] != 0):
        raise ValueError("T3 no-recall arm unexpectedly emitted parents")

    cost_identity = {
        arm: _cost_tuple(records[(arm, seed)]) == _cost_tuple(records[(enabled_arms[0], seed)])
        for arm in enabled_arms
    }
    if not all(cost_identity.values()):
        raise ValueError("T3 enabled controls do not have equal counted recall costs")

    linked_identity = identity["parent_count"] == 1
    linked_rotated = rotated["parent_count"] == 1
    identity_residual = (
        identity["token"][linked_identity, 30]
        - zero["token"][linked_identity, 30]
        - recall_gate * identity["parent_token"][linked_identity, 30]
    )
    rotated_residual = (
        rotated["token"][linked_rotated, 30]
        - zero["token"][linked_rotated, 30]
        - recall_gate * rotated["parent_token"][linked_rotated, 29]
    )
    maximum_reconstruction_residual = float(
        max(
            np.max(np.abs(identity_residual), initial=0.0),
            np.max(np.abs(rotated_residual), initial=0.0),
        )
    )
    if maximum_reconstruction_residual > 1e-6:
        raise ValueError("T3 graph ingress contribution reconstruction failed")

    coordinate_differences: dict[str, list[int]] = {}
    for arm in ("identity-recall", "rotate-one-coordinate-control"):
        delta = arrays[arm]["token"] - no_recall["token"]
        coordinate_differences[arm] = (
            np.flatnonzero(np.any(delta != 0.0, axis=0)).astype(int).tolist()
        )
        if coordinate_differences[arm] != [30]:
            raise ValueError("T3 recall changed a non-ingress thought coordinate")

    parent_child_cosine = {
        arm: _quantiles(
            _cosine_rows(value["token"][value["parent_count"] == 1], value["parent_token"][value["parent_count"] == 1])
        )
        for arm, value in arrays.items()
        if arm != "no-recall"
    }
    child_delta_l2 = {
        arm: _quantiles(
            np.linalg.norm(value["token"] - no_recall["token"], axis=1)
        )
        for arm, value in arrays.items()
    }
    identity_delta = identity["token"][:, 30] - no_recall["token"][:, 30]
    rotated_delta = rotated["token"][:, 30] - no_recall["token"][:, 30]

    return {
        "seed": int(seed),
        "semantic_identity": semantic_identity,
        "zero_content_token_identity": True,
        "enabled_equal_costs": cost_identity,
        "enabled_parent_links": 144,
        "root_events_per_enabled_arm": 16,
        "latest_prior_age_ticks": 1,
        "coordinate_differences": coordinate_differences,
        "maximum_ingress_reconstruction_residual": maximum_reconstruction_residual,
        "parent_child_cosine": parent_child_cosine,
        "child_delta_l2": child_delta_l2,
        "identity_coordinate_30_delta": _quantiles(identity_delta),
        "rotated_coordinate_30_delta": _quantiles(rotated_delta),
        "identity_delta_nonzero_fraction": float(np.mean(identity_delta != 0.0)),
        "rotated_delta_nonzero_fraction": float(np.mean(rotated_delta != 0.0)),
        "final_enabled_recall_cost_tuple": list(
            _cost_tuple(records[("identity-recall", seed)])
        ),
    }


def assess(
    study_report: str | Path,
    *,
    output: str | Path,
    summary_output: str | Path | None = None,
) -> dict[str, Any]:
    study_path = Path(study_report).expanduser().resolve()
    report = json.loads(study_path.read_text(encoding="utf-8"))
    if report.get("schema") != THOUGHT_EVENT_T3_STUDY_SCHEMA:
        raise ValueError("unsupported T3 study schema")
    expected_sha = str(report.get("study_sha256", ""))
    unsigned = dict(report)
    unsigned.pop("study_sha256", None)
    if expected_sha != _canonical_sha256(unsigned):
        raise ValueError("T3 study checksum mismatch")
    records = _record_index(report)
    seeds = tuple(int(value) for value in report["parameters"]["seeds"])
    recall_gate = float(report["parameters"]["recall_gate"])
    per_seed = [
        _seed_assessment(
            seed,
            records=records,
            study_root=study_path.parent,
            recall_gate=recall_gate,
        )
        for seed in seeds
    ]

    max_residual = max(
        item["maximum_ingress_reconstruction_residual"] for item in per_seed
    )
    identity_parent_child_cosine = [
        item["parent_child_cosine"]["identity-recall"]["median"]
        for item in per_seed
    ]
    rotate_parent_child_cosine = [
        item["parent_child_cosine"]["rotate-one-coordinate-control"]["median"]
        for item in per_seed
    ]
    all_contracts = all(
        item["zero_content_token_identity"]
        and all(item["enabled_equal_costs"].values())
        and item["enabled_parent_links"] == 144
        and item["root_events_per_enabled_arm"] == 16
        and item["latest_prior_age_ticks"] == 1
        and item["coordinate_differences"]["identity-recall"] == [30]
        and item["coordinate_differences"]["rotate-one-coordinate-control"] == [30]
        and all(
            all(fields.values()) for fields in item["semantic_identity"].values()
        )
        for item in per_seed
    )
    passed = bool(all_contracts and max_residual <= 1e-6)
    status = (
        "mechanism-smoke-passed-single-latest-prior-low-rank-recall"
        if passed
        else "mechanism-smoke-failed"
    )
    assessment: dict[str, Any] = {
        "schema": THOUGHT_EVENT_T3_ASSESSMENT_SCHEMA,
        "project_version": __version__,
        "study_report": study_path.name,
        "study_sha256": expected_sha,
        "seed_count": len(seeds),
        "seeds": list(seeds),
        "status": status,
        "passed": passed,
        "mechanism_contract": {
            "single_role_neutral_latest_prior_path": all_contracts,
            "strict_prior_tick_only": all_contracts,
            "real_parent_dag_recorded": all_contracts,
            "graph_ingress_reconstruction_max_abs_residual": max_residual,
            "zero_content_equal_cost_control_exact": all_contracts,
            "action_event_semantics_unchanged": all_contracts,
            "random_retrieval_enabled": False,
            "query_network_enabled": False,
            "multi_head_enabled": False,
            "retention_policy_change": False,
        },
        "design": {
            "seeds": list(seeds),
            "arms": list(_EXPECTED_ARMS),
            "subjects_per_seed": 16,
            "audit_ticks": 10,
            "selector": "latest-retained-strictly-prior-event",
            "recall_ingress_node": 9,
            "recall_token_port": 30,
            "recall_gate": recall_gate,
        },
        "formal_support": {
            "events_per_arm_per_seed": 160,
            "subjects_per_seed": 16,
            "ticks_per_seed": 10,
            "parent_links_per_enabled_arm_per_seed": 144,
            "root_events_per_enabled_arm_per_seed": 16,
        },
        "qualification": {
            "formal_nine_seed_panel": len(seeds) == 9,
            "minimal_forward_recall_mechanism_qualified": passed,
            "t4_audit_authorized": passed and len(seeds) == 9,
            "thought_chain_claim_authorized": False,
            "delayed_information_utility_claim_authorized": False,
            "distributed_cognitive_representation_claim_authorized": False,
            "multi_head_or_retention_implementation_authorized": False,
        },
        "dynamics": {
            "identity_parent_child_cosine_median_across_seeds": _quantiles(
                identity_parent_child_cosine
            ),
            "rotated_parent_child_cosine_median_across_seeds": _quantiles(
                rotate_parent_child_cosine
            ),
            "interpretation": (
                "The path performs exact prior-event content feedback, but the fixed "
                "rank-two bootstrap remains highly locally similar; this is an echo-risk "
                "observation, not evidence of a formed chain of thought."
            ),
        },
        "per_seed": per_seed,
        "authorized_claims": [
            "one deterministic latest-prior ThoughtEvent can enter a declared graph ingress",
            "the selected prior event is recorded as a real parent DAG edge",
            "identity and transformed content effects are exactly reconstructable",
            "enabled content controls have equal counted search/read/ingress cost",
            "the readout-only ingress does not alter action or world-facing semantics",
        ],
        "forbidden_claims": [
            "formed chain of thought",
            "delayed-information utility",
            "distributed cognition",
            "semantic memory",
            "language or object reference",
            "usefulness inferred from reference count",
            "retention or permanent memory qualification",
            "multi-head or fixed retrieval-role qualification",
        ],
        "next_stage": (
            "T4 delayed-information utility and lineage-echo audit using the same single "
            "read path before any multi-head or retention mechanism"
        ),
    }
    assessment["assessment_sha256"] = _canonical_sha256(assessment)
    output_path = Path(output).expanduser().resolve()
    _write_json(output_path, assessment)
    if summary_output is not None:
        summary_path = Path(summary_output).expanduser().resolve()
        summary_path.parent.mkdir(parents=True, exist_ok=True)
        summary_path.write_text(_summary_markdown(assessment), encoding="utf-8")
    return assessment


def _summary_markdown(assessment: dict[str, Any]) -> str:
    dynamics = assessment["dynamics"]
    contract = assessment["mechanism_contract"]
    return "\n".join(
        [
            "# ThoughtEvent T3 最小前向 recall 评估",
            "",
            f"状态：`{assessment['status']}`",
            "",
            "## 机械结论",
            "",
            "- 单一确定性路径只读取严格早于当前 tick 的最近 ThoughtEvent。",
            "- enabled 三臂均记录真实 parent DAG；每 seed 每臂 144 条 parent link。",
            "- identity、坐标循环置换与零内容 control 的搜索、读取和 ingress 成本完全一致。",
            "- zero-content 等成本 control 与 no-recall 的 ThoughtEvent 内容完全一致。",
            "- recall 只进入 readout-only node 9，并且只改变 token coordinate 30。",
            f"- 最大数值重建残差：`{contract['graph_ingress_reconstruction_max_abs_residual']}`。",
            "- 所有 arm 的 event identity、action、sampled probability 和 action potentials 一致。",
            "",
            "## 解释边界",
            "",
            "该结果只证明最小 recall 机制可运行，不证明 recall 携带有用延迟信息。",
            (
                "identity parent-child cosine 的跨 seed 中位数范围为 "
                f"`{dynamics['identity_parent_child_cosine_median_across_seeds']['min']}`～"
                f"`{dynamics['identity_parent_child_cosine_median_across_seeds']['max']}`，"
                "说明 fixed-bootstrap token 仍高度局部相似，必须在后续 T4 审计 echo risk。"
            ),
            "",
            "不得据此声称已经形成思维链、分布式认知、语义记忆、语言或长期保留。",
            "",
        ]
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--study-report", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--summary-output")
    args = parser.parse_args()
    result = assess(
        args.study_report,
        output=args.output,
        summary_output=args.summary_output,
    )
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
