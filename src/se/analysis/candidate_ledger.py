"""Deterministic decision ledger for tiered paired exploration candidates.

The ledger records promoted and stopped candidate specifications so a failed
screen cannot be silently revived by relabeling it, lowering its threshold, or
reusing the same discovery result as a new hypothesis.  It is an analysis
artifact only and never feeds back into the simulated world.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any, Sequence

LEDGER_SCHEMA = "paired-exploration-candidate-ledger-v1"
SUPPORTED_ASSESSMENT_SCHEMAS = {
    "tiered-paired-exploration-assessment-v1",
    "tiered-paired-exploration-assessment-v2",
}


def canonical_sha(payload: Any) -> str:
    return hashlib.sha256(
        json.dumps(
            payload,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()


def candidate_spec_from_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """Return the inferential candidate specification from a plan/assessment."""

    checks = payload.get("manipulation_checks", [])
    if not isinstance(checks, list):
        checks = []
    return {
        "intervention": str(payload["intervention"]),
        "primary_metric": str(payload["primary_metric"]),
        "metric_mode": str(payload["metric_mode"]),
        "direction": str(payload["direction"]),
        "minimum_relative_effect": float(payload["minimum_relative_effect"]),
        "response_ticks": (
            int(payload["response_ticks"])
            if payload.get("response_ticks") is not None
            else None
        ),
        "manipulation_checks": checks,
    }


def candidate_signature(payload: dict[str, Any]) -> str:
    supplied = payload.get("candidate_signature_sha256")
    if isinstance(supplied, str) and len(supplied) == 64:
        return supplied
    return canonical_sha(candidate_spec_from_payload(payload))


def assessment_decision(assessment: dict[str, Any]) -> tuple[str, list[str], bool]:
    recommendation = str(assessment.get("recommendation", ""))
    explicit = assessment.get("decision")
    if isinstance(explicit, dict):
        outcome = str(explicit.get("outcome", "review"))
        reasons = [str(value) for value in explicit.get("reason_codes", [])]
        terminal = bool(explicit.get("terminal", outcome in {"stop", "confirmed-acute"}))
        return outcome, reasons, terminal

    if recommendation.startswith("promote-") or recommendation.startswith("mechanism-smoke-passed"):
        return "promote", [recommendation], False
    if recommendation.startswith("confirmation-gate-passed"):
        return "confirmed-acute", [recommendation], True
    if recommendation.startswith("stop-"):
        return "stop", [recommendation], True
    return "review", [recommendation or "assessment-without-decision"], False


def load_ledger(path: str | Path) -> dict[str, Any]:
    ledger_path = Path(path)
    if not ledger_path.is_file():
        return {
            "schema": LEDGER_SCHEMA,
            "entries": [],
            "world_feedback": False,
            "failed_candidates_reopened_automatically": False,
        }
    payload = json.loads(ledger_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or payload.get("schema") != LEDGER_SCHEMA:
        raise ValueError(f"unsupported candidate ledger schema in {ledger_path}")
    entries = payload.get("entries")
    if not isinstance(entries, list):
        raise ValueError("candidate ledger entries must be a list")
    return payload


def _entry_from_assessment(assessment: dict[str, Any]) -> dict[str, Any]:
    schema = assessment.get("schema")
    if schema not in SUPPORTED_ASSESSMENT_SCHEMAS:
        raise ValueError(f"unsupported paired assessment schema: {schema!r}")
    outcome, reasons, terminal = assessment_decision(assessment)
    if assessment.get("schema") == "tiered-paired-exploration-assessment-v1" and outcome == "stop":
        derived: list[str] = []
        if float(assessment.get("direction_consistency", 0.0)) < 0.75:
            derived.append("direction-not-replicated-across-seeds")
        if not bool(assessment.get("practical_effect_threshold_met", False)):
            derived.append("effect-below-preregistered-practical-threshold")
        if derived:
            reasons = derived
    spec = candidate_spec_from_payload(assessment)
    return {
        "candidate_id": str(assessment["candidate_id"]),
        "candidate_signature_sha256": candidate_signature(assessment),
        "candidate_spec": spec,
        "stage": str(assessment["stage"]),
        "decision": outcome,
        "terminal": terminal,
        "recommendation": str(assessment.get("recommendation", "")),
        "reason_codes": reasons,
        "assessment_schema": str(schema),
        "assessment_sha256": canonical_sha(assessment),
        "eligible_seed_count": int(assessment.get("eligible_seed_count", 0)),
        "eligible_seed_fraction": float(assessment.get("eligible_seed_fraction", 0.0)),
        "direction_consistency": float(assessment.get("direction_consistency", 0.0)),
        "equal_seed_median_relative_effect": assessment.get(
            "equal_seed_median_relative_effect"
        ),
        "all_stage_seeds": [
            int(value)
            for value in assessment.get("all_stage_seeds", assessment.get("seeds", []))
        ],
        "selection_claim_allowed": False,
    }


def validate_candidate_for_plan(
    ledger: dict[str, Any],
    *,
    candidate_id: str,
    signature: str,
    stage: str,
) -> None:
    for entry in ledger.get("entries", []):
        entry_id = str(entry.get("candidate_id", ""))
        entry_signature = str(entry.get("candidate_signature_sha256", ""))
        if entry_id == candidate_id and entry_signature != signature:
            raise ValueError(
                "candidate id already exists with a different scientific specification; "
                "create an explicit new candidate revision"
            )
        same_candidate = entry_id == candidate_id or entry_signature == signature
        if not same_candidate:
            continue
        if bool(entry.get("terminal", False)):
            raise ValueError(
                f"candidate is terminal in the decision ledger: {entry.get('decision')} "
                f"({entry.get('recommendation')})"
            )
        if str(entry.get("stage")) == stage:
            raise ValueError(f"candidate stage {stage!r} is already recorded in the decision ledger")


def record_assessment(
    ledger_path: str | Path,
    assessment: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    path = Path(ledger_path)
    ledger = load_ledger(path)
    entry = _entry_from_assessment(assessment)
    entries = list(ledger.get("entries", []))

    for existing in entries:
        if existing.get("assessment_sha256") == entry["assessment_sha256"]:
            return ledger, existing
        same_id = existing.get("candidate_id") == entry["candidate_id"]
        same_signature = (
            existing.get("candidate_signature_sha256")
            == entry["candidate_signature_sha256"]
        )
        if same_id and not same_signature:
            raise ValueError(
                "candidate id already exists with a different scientific specification"
            )
        if same_signature and existing.get("candidate_id") != entry["candidate_id"]:
            raise ValueError(
                "candidate specification already exists under a different candidate id"
            )
        if same_id and existing.get("stage") == entry["stage"]:
            raise ValueError("candidate stage already has a different recorded assessment")
        if (same_id or same_signature) and bool(existing.get("terminal", False)):
            raise ValueError("cannot append to a terminal candidate decision")

    entries.append(entry)
    entries.sort(
        key=lambda item: (
            str(item.get("candidate_id", "")),
            str(item.get("candidate_signature_sha256", "")),
            str(item.get("stage", "")),
        )
    )
    updated = {
        "schema": LEDGER_SCHEMA,
        "entries": entries,
        "world_feedback": False,
        "failed_candidates_reopened_automatically": False,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(updated, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)
    return updated, entry


def render_markdown(ledger: dict[str, Any]) -> str:
    lines = [
        "# Paired exploration candidate decision ledger",
        "",
        f"Schema: `{ledger['schema']}`",
        "",
        "| Candidate | Stage | Decision | Recommendation | Eligible seeds | Median relative effect |",
        "|---|---|---|---|---:|---:|",
    ]
    for entry in ledger.get("entries", []):
        lines.append(
            f"| {entry['candidate_id']} | {entry['stage']} | {entry['decision']} | "
            f"{entry['recommendation']} | {entry['eligible_seed_count']} | "
            f"{entry['equal_seed_median_relative_effect']} |"
        )
    lines.extend(
        [
            "",
            "A terminal failed candidate cannot be automatically reopened or relabeled. "
            "A changed intervention, metric, direction, threshold, horizon, or manipulation "
            "contract requires an explicit new candidate revision.",
            "",
        ]
    )
    return "\n".join(lines)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Record a paired exploration assessment in a deterministic decision ledger."
    )
    parser.add_argument("--assessment", required=True)
    parser.add_argument("--ledger", required=True)
    args = parser.parse_args(argv)
    source_path = Path(args.assessment)
    source = json.loads(source_path.read_text(encoding="utf-8"))
    if isinstance(source, dict) and isinstance(source.get("assessment"), dict):
        assessment = dict(source["assessment"])
        assessment.setdefault("response_ticks", source.get("response_ticks"))
        assessment.setdefault("manipulation_checks", source.get("manipulation_checks", []))
    else:
        assessment = dict(source)
        if assessment.get("response_ticks") is None:
            sibling = source_path.with_name("paired_exploration_results.json")
            if sibling.is_file():
                result = json.loads(sibling.read_text(encoding="utf-8"))
                if assessment.get("response_ticks") is None:
                    response_ticks = result.get("response_ticks")
                    panels = result.get("panels", [])
                    if response_ticks is None and panels:
                        first = panels[0]
                        response_ticks = int(first["until_tick"]) - int(first["checkpoint_tick"])
                    assessment["response_ticks"] = response_ticks
                if not assessment.get("manipulation_checks"):
                    assessment["manipulation_checks"] = result.get("manipulation_checks", [])
    ledger, _ = record_assessment(Path(args.ledger), assessment)
    Path(args.ledger).with_suffix(".md").write_text(
        render_markdown(ledger), encoding="utf-8"
    )
    return 0


__all__ = [
    "LEDGER_SCHEMA",
    "assessment_decision",
    "candidate_signature",
    "candidate_spec_from_payload",
    "canonical_sha",
    "load_ledger",
    "record_assessment",
    "render_markdown",
    "validate_candidate_for_plan",
]


if __name__ == "__main__":
    raise SystemExit(main())
