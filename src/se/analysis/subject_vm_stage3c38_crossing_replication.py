"""Stage 3C-38 corrected disjoint-panel crossing replication.

This assessment executes the Stage-3C-35 preregistered source-level classifier
only after the checksum-bound Stage-3C-37 selector-consistent qualification
overlay has authorized the unchanged Stage-3C-28 through Stage-3C-34 chain.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from .. import __version__
from ..experiments.subject_vm_short_paired_study import _canonical_sha256
from .subject_vm_stage3c35_crossing_replication import (
    STAGE3C35_CROSSING_REPLICATION_ASSESSMENT_SCHEMA,
    assess_stage3c35_crossing_replication,
)
from .subject_vm_stage3c37_tie_origin import STAGE3C37_TIE_ORIGIN_SCHEMA

STAGE3C38_CROSSING_REPLICATION_SCHEMA = (
    "se-subject-vm-stage3c38-crossing-replication-assessment-v1"
)


def _load_json(path: str | Path) -> dict[str, Any]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"expected one JSON object: {path}")
    return payload


def _validate_checksum(payload: dict[str, Any], *, label: str) -> None:
    recorded = str(payload.get("assessment_sha256", ""))
    unsigned = dict(payload)
    unsigned.pop("assessment_sha256", None)
    if not recorded or recorded != _canonical_sha256(unsigned):
        raise ValueError(f"{label} checksum mismatch")


def assess_stage3c38_crossing_replication(
    reference_decision: dict[str, Any],
    historical_stage3c35: dict[str, Any],
    stage3c37_qualification: dict[str, Any],
    replication_stage3c34: dict[str, Any],
) -> dict[str, Any]:
    if historical_stage3c35.get("schema") != STAGE3C35_CROSSING_REPLICATION_ASSESSMENT_SCHEMA:
        raise ValueError("unsupported historical Stage-3C-35 assessment schema")
    _validate_checksum(historical_stage3c35, label="Stage-3C-38 historical Stage-3C-35")
    if historical_stage3c35.get("prediction_assessment", {}).get("crossing_prediction_tested") is not False:
        raise ValueError("Stage-3C-38 requires the frozen untested Stage-3C-35 prediction")

    if stage3c37_qualification.get("schema") != STAGE3C37_TIE_ORIGIN_SCHEMA:
        raise ValueError("unsupported Stage-3C-37 qualification schema")
    _validate_checksum(stage3c37_qualification, label="Stage-3C-38 Stage-3C-37 qualification")
    resolution = stage3c37_qualification.get("cross_panel_resolution", {})
    interpretation = stage3c37_qualification.get("frozen_interpretation", {})
    if not bool(resolution.get("selector_consistent_stage3c28_prerequisite_passed_in_both_panels")):
        raise ValueError("Stage-3C-38 selector-consistent qualification failed")
    if not bool(interpretation.get("corrected_crossing_replication_authorized_next")):
        raise ValueError("Stage-3C-38 corrected crossing replication is not authorized")
    if bool(interpretation.get("stage3c35_crossing_prediction_was_tested")):
        raise ValueError("Stage-3C-38 qualification unexpectedly marks prediction as tested")

    classifier = assess_stage3c35_crossing_replication(
        reference_decision,
        replication_stage3c34,
    )
    historical_seeds = sorted(int(seed) for seed in historical_stage3c35["replication_source_seeds"])
    current_seeds = sorted(int(seed) for seed in classifier["replication_source_seeds"])
    if historical_seeds != current_seeds:
        raise ValueError("Stage-3C-38 source panel differs from frozen Stage-3C-35")

    replay_checksum = stage3c37_qualification.get("input_checksums", {}).get(
        "replication_replay_study"
    )
    prediction = classifier["prediction_assessment"]
    if prediction["prediction_supported_nonvacuously"]:
        frozen_status = "replicated-nonvacuously"
    elif prediction["vacuous_match_only"]:
        frozen_status = "not-refuted-vacuous-zero-positive-panel"
    else:
        frozen_status = "refuted-on-disjoint-panel"

    payload: dict[str, Any] = {
        "schema": STAGE3C38_CROSSING_REPLICATION_SCHEMA,
        "producer_version": __version__,
        "assessment_mode": "selector-consistent-corrected-disjoint-panel-replication",
        "reference_stage3c34_decision_id": str(reference_decision["decision_id"]),
        "historical_stage3c35_assessment_sha256": str(historical_stage3c35["assessment_sha256"]),
        "stage3c37_qualification_sha256": str(stage3c37_qualification["assessment_sha256"]),
        "replication_rank2_study_sha256": str(replay_checksum),
        "replication_stage3c34_assessment_sha256": str(replication_stage3c34["assessment_sha256"]),
        "replication_source_seeds": current_seeds,
        "source_panels_are_disjoint": True,
        "qualification": {
            "historical_stage3c27_artifact_rewritten": False,
            "historical_stage3c35_stop_rewritten": False,
            "selector_consistent_overlay_used": True,
            "runtime_tie_semantics_changed": False,
            "source_state_identity_preserved": bool(
                stage3c37_qualification.get("replay_identity", {}).get(
                    "replication_source_state_hashes_match_frozen_report"
                )
            ),
            "stored_winner_identity_reconstructed": bool(
                stage3c37_qualification.get("replay_identity", {}).get(
                    "stored_winner_ids_exactly_reconstructed"
                )
            ),
        },
        "preregistered_prediction": classifier["preregistered_prediction"],
        "source_level_confusion_matrix": classifier["source_level_confusion_matrix"],
        "replication_findings": classifier["replication_findings"],
        "prediction_assessment": prediction,
        "frozen_status": frozen_status,
        "governance": {
            **classifier["governance"],
            "stage3c37_overlay_changed_runtime": False,
            "post_hoc_source_selection": False,
            "post_hoc_prediction_change": False,
        },
        "frozen_interpretation": {
            "crossing_classifier_replicates_nonvacuously": bool(
                prediction["prediction_supported_nonvacuously"]
            ),
            "crossing_classifier_is_refuted": bool(
                not prediction["prediction_not_refuted"]
            ),
            "zero_positive_panel_is_nonvacuous_support": False,
            "qualification_correction_proves_crossing_prediction": False,
            "objective_coordinates_have_value_semantics": False,
            "causal_credit_quality_is_proven": False,
        },
        "automatic_keep_or_revert_authorized": False,
        "permanent_parameter_retention_authorized": False,
        "learned_weight_authorized": False,
        "learning_claim_authorized": False,
        "subjecthood_claim_authorized": False,
    }
    payload["assessment_sha256"] = _canonical_sha256(payload)
    return payload


def _summary(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema": "se-subject-vm-stage3c38-study-summary-v1",
        "producer_version": payload["producer_version"],
        "assessment_sha256": payload["assessment_sha256"],
        "replication_source_seeds": payload["replication_source_seeds"],
        "frozen_status": payload["frozen_status"],
        "source_level_confusion_matrix": payload["source_level_confusion_matrix"],
        "prediction_assessment": payload["prediction_assessment"],
        "retention_authorized": False,
    }


def _diagnostic(payload: dict[str, Any]) -> str:
    findings = payload["replication_findings"]
    matrix = payload["source_level_confusion_matrix"]
    prediction = payload["prediction_assessment"]
    lines = [
        "# Stage 3C-38 独立 panel crossing replication",
        "",
        "## 预注册分类",
        "",
        f"- alignment-differential action crossing source：{findings['alignment_differential_action_crossing_source_seeds']}",
        f"- surviving Objective-Fact effect source：{findings['surviving_fact_effect_source_seeds']}",
        f"- true positive：{matrix['true_positive_seeds']}",
        f"- false positive：{matrix['false_positive_seeds']}",
        f"- false negative：{matrix['false_negative_seeds']}",
        f"- true negative：{matrix['true_negative_seeds']}",
        "",
        "## 冻结判定",
        "",
        f"- 状态：`{payload['frozen_status']}`",
        f"- source identity 完全一致：`{prediction['source_classifier_exact_identity']}`",
        f"- 非空阳性支持：`{prediction['nonvacuous_positive_source_support']}`",
        f"- 非空复现支持：`{prediction['prediction_supported_nonvacuously']}`",
        "- Stage 3C-37 overlay 只修正资格解释，不修改 runtime selector。",
        "- 不授权 value、learned weight、keep/revert 或永久 retention。",
        "",
    ]
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Assess Stage 3C-38 selector-consistent disjoint-panel crossing replication."
    )
    parser.add_argument("--reference-stage3c34-decision", required=True)
    parser.add_argument("--historical-stage3c35-assessment", required=True)
    parser.add_argument("--stage3c37-qualification", required=True)
    parser.add_argument("--replication-stage3c34-assessment", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--summary-output")
    parser.add_argument("--diagnostic-report")
    args = parser.parse_args()
    payload = assess_stage3c38_crossing_replication(
        _load_json(args.reference_stage3c34_decision),
        _load_json(args.historical_stage3c35_assessment),
        _load_json(args.stage3c37_qualification),
        _load_json(args.replication_stage3c34_assessment),
    )
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    if args.summary_output:
        Path(args.summary_output).write_text(
            json.dumps(_summary(payload), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    if args.diagnostic_report:
        Path(args.diagnostic_report).write_text(_diagnostic(payload), encoding="utf-8")
    print(json.dumps(payload["prediction_assessment"], ensure_ascii=False))


if __name__ == "__main__":
    main()


__all__ = [
    "STAGE3C38_CROSSING_REPLICATION_SCHEMA",
    "assess_stage3c38_crossing_replication",
]
