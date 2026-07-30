"""Deterministic decision ledger for tiered paired exploration candidates.

The immutable release baseline and append-only workspace overlay record promoted
and stopped candidate specifications so a failed screen cannot be silently
revived by relabeling it, lowering its threshold, or reusing the same discovery
result as a new hypothesis. Decision history never feeds back into the world.
"""
from __future__ import annotations

import argparse
import hashlib
from importlib import resources
import json
from pathlib import Path
from typing import Any, Sequence

LEDGER_SCHEMA = "paired-exploration-candidate-ledger-v5"
LEGACY_LEDGER_SCHEMAS = {
    "paired-exploration-candidate-ledger-v1",
    "paired-exploration-candidate-ledger-v2",
    "paired-exploration-candidate-ledger-v3",
    "paired-exploration-candidate-ledger-v4",
}
BUILTIN_DECISION_BASELINE_RESOURCE = "resources/exploration_candidate_ledger.json"

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


def candidate_portfolio_metadata(payload: dict[str, Any]) -> dict[str, Any]:
    """Return non-inferential portfolio metadata for family-level stop rules."""

    raw_family = payload.get("mechanism_family")
    family = str(raw_family).strip() if raw_family not in {None, ""} else ""
    raw_revision = payload.get("mechanism_family_revision")
    revision = int(1 if raw_revision is None else raw_revision) if family else None
    if revision is not None and revision <= 0:
        raise ValueError("mechanism_family_revision must be positive")
    raw_rationale = payload.get("family_revision_rationale")
    rationale = str(raw_rationale).strip() if raw_rationale not in {None, ""} else ""
    raw_interface = payload.get("family_revision_interface")
    interface = str(raw_interface).strip() if raw_interface not in {None, ""} else ""
    raw_role = payload.get("family_role")
    role = str(raw_role).strip() if raw_role not in {None, ""} else ""
    metadata = {
        "mechanism_family": family or None,
        "mechanism_family_revision": revision,
        "family_role": role or None,
        "terminal_negative_closes_family": bool(
            payload.get("terminal_negative_closes_family", False)
        ),
        "family_revision_rationale": rationale or None,
        "family_revision_interface": interface or None,
    }
    gate_class = _family_gate_class(metadata["family_role"])
    if metadata["terminal_negative_closes_family"] and gate_class != "aggregate":
        raise ValueError(
            "terminal_negative_closes_family is valid only for an aggregate family gate"
        )
    if interface and not family:
        raise ValueError("family_revision_interface requires mechanism_family")
    return metadata


def _family_gate_class(role: str | None) -> str:
    normalized = str(role or "").strip().lower()
    if normalized == "aggregate-path" or normalized.startswith("aggregate-"):
        return "aggregate"
    if normalized.startswith("bounded-") or normalized == "bounded-output-path":
        return "bounded"
    return "other"


def _family_revision_entries(
    ledger: dict[str, Any], *, family: str, revision: int
) -> list[dict[str, Any]]:
    return [
        dict(entry)
        for entry in ledger.get("entries", [])
        if str(entry.get("mechanism_family") or "") == family
        and int(entry.get("mechanism_family_revision") or 1) == revision
    ]


def family_revision_statuses(entries: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
    """Summarize deterministic planning state for every recorded family revision."""

    grouped: dict[tuple[str, int], list[dict[str, Any]]] = {}
    for raw in entries:
        family = str(raw.get("mechanism_family") or "").strip()
        if not family:
            continue
        revision = int(raw.get("mechanism_family_revision") or 1)
        grouped.setdefault((family, revision), []).append(dict(raw))

    statuses: list[dict[str, Any]] = []
    for (family, revision), family_entries in sorted(grouped.items()):
        terminal_entries = [
            entry for entry in family_entries if bool(entry.get("family_terminal", False))
        ]
        aggregate_entries = [
            entry
            for entry in family_entries
            if _family_gate_class(entry.get("family_role")) == "aggregate"
        ]
        bounded_negatives = [
            entry
            for entry in family_entries
            if _family_gate_class(entry.get("family_role")) == "bounded"
            and bool(entry.get("terminal", False))
            and bool(entry.get("manipulation_confirmed", False))
            and str(entry.get("decision")) == "stop"
        ]
        if terminal_entries:
            status = "closed"
        elif aggregate_entries:
            status = "aggregate-gate-recorded"
        elif bounded_negatives:
            status = "aggregate-gate-required"
        else:
            status = "open"
        statuses.append(
            {
                "mechanism_family": family,
                "mechanism_family_revision": revision,
                "status": status,
                "candidate_ids": sorted(
                    str(entry.get("candidate_id", "")) for entry in family_entries
                ),
                "bounded_negative_candidate_ids": sorted(
                    str(entry.get("candidate_id", "")) for entry in bounded_negatives
                ),
                "aggregate_candidate_ids": sorted(
                    str(entry.get("candidate_id", "")) for entry in aggregate_entries
                ),
                "closed_by_candidate_ids": sorted(
                    str(entry.get("candidate_id", "")) for entry in terminal_entries
                ),
            }
        )
    return statuses


def _ledger_payload(entries: Sequence[dict[str, Any]]) -> dict[str, Any]:
    normalized = [dict(entry) for entry in entries]
    return {
        "schema": LEDGER_SCHEMA,
        "entries": normalized,
        "family_revision_statuses": family_revision_statuses(normalized),
        "world_feedback": False,
        "failed_candidates_reopened_automatically": False,
        "terminal_families_reopened_automatically": False,
        "bounded_negative_requires_aggregate_gate": True,
        "family_closure_requires_aggregate_gate": True,
        "family_reopening_requires_new_interface": True,
    }


def assessment_decision(assessment: dict[str, Any]) -> tuple[str, list[str], bool]:
    recommendation = str(assessment.get("recommendation", ""))
    explicit = assessment.get("decision")
    if isinstance(explicit, dict):
        outcome = str(explicit.get("outcome", "review"))
        reasons = [str(value) for value in explicit.get("reason_codes", [])]
        terminal = bool(explicit.get("terminal", outcome in {"stop", "confirmed-acute"}))
        return outcome, reasons, terminal

    if recommendation.startswith("promote-") or recommendation.startswith(
        "mechanism-smoke-passed"
    ):
        return "promote", [recommendation], False
    if recommendation.startswith("confirmation-gate-passed"):
        return "confirmed-acute", [recommendation], True
    if recommendation.startswith("stop-"):
        return "stop", [recommendation], True
    return "review", [recommendation or "assessment-without-decision"], False


def _evidence_class(
    *, outcome: str, check_count: int, manipulation_confirmed: bool
) -> str:
    if check_count == 0:
        return (
            "promotion-negative-without-direct-manipulation-contract"
            if outcome == "stop"
            else "assessment-without-direct-manipulation-contract"
        )
    if not manipulation_confirmed:
        return "manipulation-unconfirmed"
    if outcome == "stop":
        return "manipulation-confirmed-promotion-negative"
    if outcome in {"promote", "confirmed-acute"}:
        return "manipulation-confirmed-promotion-positive"
    return "manipulation-confirmed-review"


def _upgrade_entry(entry: dict[str, Any]) -> dict[str, Any]:
    upgraded = dict(entry)
    checks = upgraded.get("candidate_spec", {}).get("manipulation_checks", [])
    check_count = len(checks) if isinstance(checks, list) else 0
    upgraded.setdefault("manipulation_check_count", check_count)
    upgraded.setdefault("manipulation_supported_seed_count", None)
    upgraded.setdefault("manipulation_supported_seed_fraction", None)
    if check_count == 0:
        manipulation_confirmed = False
    else:
        fraction = upgraded.get("manipulation_supported_seed_fraction")
        manipulation_confirmed = bool(fraction is not None and float(fraction) >= 0.75)
    upgraded.setdefault("manipulation_confirmed", manipulation_confirmed)
    upgraded.setdefault("positive_seed_count", None)
    upgraded.setdefault("negative_seed_count", None)
    upgraded.setdefault("exact_two_sided_sign_flip_p", None)
    upgraded.setdefault("practical_effect_threshold_met", None)
    metadata = candidate_portfolio_metadata(upgraded)
    for key, value in metadata.items():
        upgraded.setdefault(key, value)
    upgraded.setdefault("family_terminal", False)
    upgraded.setdefault(
        "family_gate_class", _family_gate_class(upgraded.get("family_role"))
    )
    upgraded.setdefault(
        "evidence_class",
        _evidence_class(
            outcome=str(upgraded.get("decision", "review")),
            check_count=check_count,
            manipulation_confirmed=bool(upgraded["manipulation_confirmed"]),
        ),
    )
    return upgraded




def _load_ledger_payload(payload: Any, *, source: str) -> dict[str, Any]:
    if not isinstance(payload, dict) or payload.get("schema") not in {
        LEDGER_SCHEMA,
        *LEGACY_LEDGER_SCHEMAS,
    }:
        raise ValueError(f"unsupported candidate ledger schema in {source}")
    entries = payload.get("entries")
    if not isinstance(entries, list):
        raise ValueError("candidate ledger entries must be a list")
    return _ledger_payload([_upgrade_entry(dict(entry)) for entry in entries])


def load_builtin_decision_baseline() -> dict[str, Any]:
    resource = resources.files("se").joinpath(BUILTIN_DECISION_BASELINE_RESOURCE)
    payload = json.loads(resource.read_text(encoding="utf-8"))
    return _load_ledger_payload(
        payload, source=f"package:se/{BUILTIN_DECISION_BASELINE_RESOURCE}"
    )


def merge_ledgers(*ledgers: dict[str, Any]) -> dict[str, Any]:
    """Merge compatible ledger histories without allowing silent replacement."""

    entries: list[dict[str, Any]] = []
    seen_assessments: set[str] = set()
    for ledger in ledgers:
        for raw in ledger.get("entries", []):
            entry = _upgrade_entry(dict(raw))
            assessment_hash = str(entry.get("assessment_sha256", ""))
            if assessment_hash and assessment_hash in seen_assessments:
                continue
            candidate_id = str(entry.get("candidate_id", ""))
            signature = str(entry.get("candidate_signature_sha256", ""))
            stage = str(entry.get("stage", ""))
            for existing in entries:
                existing_id = str(existing.get("candidate_id", ""))
                existing_signature = str(
                    existing.get("candidate_signature_sha256", "")
                )
                if existing_id == candidate_id and existing_signature != signature:
                    raise ValueError(
                        "candidate id exists with different scientific specifications across ledgers"
                    )
                if existing_signature == signature and existing_id != candidate_id:
                    raise ValueError(
                        "candidate specification exists under different candidate ids across ledgers"
                    )
                if (
                    existing_id == candidate_id
                    and str(existing.get("stage", "")) == stage
                    and str(existing.get("assessment_sha256", "")) != assessment_hash
                ):
                    raise ValueError(
                        "candidate stage has conflicting assessments across ledgers"
                    )
            entries.append(entry)
            if assessment_hash:
                seen_assessments.add(assessment_hash)

    stage_order = {"smoke": 0, "screen": 1, "replication": 2, "confirmation": 3}
    by_candidate: dict[str, list[dict[str, Any]]] = {}
    for entry in entries:
        by_candidate.setdefault(str(entry.get("candidate_id", "")), []).append(entry)
    for candidate_id, candidate_entries in by_candidate.items():
        ordered = sorted(
            candidate_entries,
            key=lambda item: (
                stage_order.get(str(item.get("stage", "")), 99),
                str(item.get("stage", "")),
            ),
        )
        terminal_positions = [
            index for index, item in enumerate(ordered) if bool(item.get("terminal", False))
        ]
        if terminal_positions and terminal_positions[0] != len(ordered) - 1:
            raise ValueError(
                f"candidate {candidate_id!r} has a stage recorded after a terminal decision"
            )

    entries.sort(
        key=lambda item: (
            str(item.get("candidate_id", "")),
            str(item.get("candidate_signature_sha256", "")),
            stage_order.get(str(item.get("stage", "")), 99),
            str(item.get("stage", "")),
        )
    )
    return _ledger_payload(entries)


def load_effective_ledger(
    workspace_path: str | Path,
    *,
    decision_baseline: str | Path | None = None,
    include_builtin_baseline: bool = False,
) -> tuple[dict[str, Any], dict[str, Any]]:
    workspace_ref = Path(workspace_path)
    workspace = load_ledger(workspace_ref)
    baseline_ref: str | None = None
    if decision_baseline is not None:
        baseline_path = Path(decision_baseline)
        if not baseline_path.is_file():
            raise ValueError(f"decision baseline does not exist: {baseline_path}")
        baseline = load_ledger(baseline_path)
        baseline_ref = str(baseline_path)
    elif include_builtin_baseline:
        baseline = load_builtin_decision_baseline()
        baseline_ref = f"package:se/{BUILTIN_DECISION_BASELINE_RESOURCE}"
    else:
        baseline = _ledger_payload([])

    effective = merge_ledgers(baseline, workspace)
    baseline_hashes = {
        str(entry.get("assessment_sha256", ""))
        for entry in baseline.get("entries", [])
    }
    workspace_hashes = {
        str(entry.get("assessment_sha256", ""))
        for entry in workspace.get("entries", [])
    }
    missing = sorted(value for value in baseline_hashes - workspace_hashes if value)
    metadata = {
        "decision_baseline_path": baseline_ref,
        "decision_baseline_entry_count": len(baseline.get("entries", [])),
        "workspace_ledger_entry_count": len(workspace.get("entries", [])),
        "effective_ledger_entry_count": len(effective.get("entries", [])),
        "workspace_missing_baseline_assessment_sha256": missing,
        "workspace_hydration_required": bool(missing),
    }
    return effective, metadata


def load_ledger(path: str | Path) -> dict[str, Any]:
    ledger_path = Path(path)
    if not ledger_path.is_file():
        return _ledger_payload([])
    payload = json.loads(ledger_path.read_text(encoding="utf-8"))
    return _load_ledger_payload(payload, source=str(ledger_path))


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
    checks = spec["manipulation_checks"]
    check_count = len(checks)
    manipulation_count = assessment.get("manipulation_supported_seed_count")
    manipulation_fraction = assessment.get("manipulation_supported_seed_fraction")
    manipulation_confirmed = bool(
        check_count
        and manipulation_fraction is not None
        and float(manipulation_fraction) >= 0.75
    )
    metadata = candidate_portfolio_metadata(assessment)
    family_terminal = bool(
        outcome == "stop"
        and terminal
        and manipulation_confirmed
        and metadata["terminal_negative_closes_family"]
    )
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
        "source_plan_schema": assessment.get("source_plan_schema"),
        "source_plan_sha256": assessment.get("source_plan_sha256"),
        "source_checkpoint_tick": assessment.get("source_checkpoint_tick"),
        "source_replication_protocol_sha256": assessment.get(
            "source_replication_protocol_sha256"
        ),
        "source_replication_protocol_locked_to_prior": bool(
            assessment.get("source_replication_protocol_locked_to_prior", False)
        ),
        "eligible_seed_count": int(assessment.get("eligible_seed_count", 0)),
        "eligible_seed_fraction": float(assessment.get("eligible_seed_fraction", 0.0)),
        "manipulation_check_count": check_count,
        "manipulation_supported_seed_count": (
            int(manipulation_count) if manipulation_count is not None else None
        ),
        "manipulation_supported_seed_fraction": (
            float(manipulation_fraction) if manipulation_fraction is not None else None
        ),
        "manipulation_confirmed": manipulation_confirmed,
        "positive_seed_count": (
            int(assessment["positive_seed_count"])
            if assessment.get("positive_seed_count") is not None
            else None
        ),
        "negative_seed_count": (
            int(assessment["negative_seed_count"])
            if assessment.get("negative_seed_count") is not None
            else None
        ),
        "direction_consistency": float(assessment.get("direction_consistency", 0.0)),
        "equal_seed_median_relative_effect": assessment.get(
            "equal_seed_median_relative_effect"
        ),
        "exact_two_sided_sign_flip_p": assessment.get("exact_two_sided_sign_flip_p"),
        "practical_effect_threshold_met": assessment.get(
            "practical_effect_threshold_met"
        ),
        "evidence_class": _evidence_class(
            outcome=outcome,
            check_count=check_count,
            manipulation_confirmed=manipulation_confirmed,
        ),
        **metadata,
        "family_terminal": family_terminal,
        "family_gate_class": _family_gate_class(metadata["family_role"]),
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
    mechanism_family: str | None = None,
    mechanism_family_revision: int | None = None,
    family_role: str | None = None,
    family_revision_rationale: str | None = None,
    family_revision_interface: str | None = None,
) -> None:
    family = str(mechanism_family or "").strip()
    family_revision = int(mechanism_family_revision or 1) if family else None
    rationale = str(family_revision_rationale or "").strip()
    interface = str(family_revision_interface or "").strip()
    proposed_gate_class = _family_gate_class(family_role)
    if family and family_revision is not None:
        revision_entries = _family_revision_entries(
            ledger, family=family, revision=family_revision
        )
        bounded_negative = any(
            entry.get("family_gate_class") == "bounded"
            and bool(entry.get("terminal", False))
            and bool(entry.get("manipulation_confirmed", False))
            and str(entry.get("decision")) == "stop"
            for entry in revision_entries
        )
        aggregate_recorded = any(
            entry.get("family_gate_class") == "aggregate"
            for entry in revision_entries
        )
        if bounded_negative and proposed_gate_class == "bounded" and not aggregate_recorded:
            raise ValueError(
                "a manipulation-confirmed bounded-path negative requires an aggregate "
                "family gate before another bounded candidate in the same family revision"
            )
    for entry in ledger.get("entries", []):
        if family and bool(entry.get("family_terminal", False)):
            closed_family = str(entry.get("mechanism_family") or "")
            if closed_family == family:
                closed_revision = int(entry.get("mechanism_family_revision") or 1)
                if family_revision is None or family_revision <= closed_revision:
                    raise ValueError(
                        "mechanism family is terminal in the decision ledger; "
                        "an explicit higher family revision with rationale is required"
                    )
                if not rationale:
                    raise ValueError(
                        "reopening a terminal mechanism family requires "
                        "family_revision_rationale"
                    )
                if not interface:
                    raise ValueError(
                        "reopening a terminal mechanism family requires a new directly "
                        "measurable family_revision_interface"
                    )
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




def _write_ledger(path: Path, ledger: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(ledger, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def hydrate_ledger(
    ledger_path: str | Path,
    *,
    decision_baseline: str | Path | None = None,
    include_builtin_baseline: bool = False,
) -> tuple[dict[str, Any], dict[str, Any]]:
    path = Path(ledger_path)
    ledger, metadata = load_effective_ledger(
        path,
        decision_baseline=decision_baseline,
        include_builtin_baseline=include_builtin_baseline,
    )
    _write_ledger(path, ledger)
    path.with_suffix(".md").write_text(render_markdown(ledger), encoding="utf-8")
    return ledger, metadata


def record_assessment(
    ledger_path: str | Path,
    assessment: dict[str, Any],
    *,
    decision_baseline: str | Path | None = None,
    include_builtin_baseline: bool = False,
) -> tuple[dict[str, Any], dict[str, Any]]:
    path = Path(ledger_path)
    ledger, _ = load_effective_ledger(
        path,
        decision_baseline=decision_baseline,
        include_builtin_baseline=include_builtin_baseline,
    )
    entry = _entry_from_assessment(assessment)
    entries = list(ledger.get("entries", []))

    for existing in entries:
        if existing.get("assessment_sha256") == entry["assessment_sha256"]:
            _write_ledger(path, ledger)
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
    updated = _ledger_payload(entries)
    _write_ledger(path, updated)
    return updated, entry


def render_markdown(ledger: dict[str, Any]) -> str:
    lines = [
        "# Paired exploration candidate decision ledger",
        "",
        f"Schema: `{ledger['schema']}`",
        "",
        "| Candidate | Family | Stage | Decision | Evidence | Eligible seeds | Manipulation | Direction | Median relative effect |",
        "|---|---|---|---|---|---:|---:|---:|---:|",
    ]
    for entry in ledger.get("entries", []):
        manipulation = entry.get("manipulation_supported_seed_fraction")
        lines.append(
            f"| {entry['candidate_id']} | {entry.get('mechanism_family')} | "
            f"{entry['stage']} | {entry['decision']} | {entry.get('evidence_class')} | "
            f"{entry['eligible_seed_count']} | "
            f"{manipulation} | {entry['direction_consistency']} | "
            f"{entry['equal_seed_median_relative_effect']} |"
        )
    statuses = ledger.get("family_revision_statuses", family_revision_statuses(ledger.get("entries", [])))
    if statuses:
        lines.extend(
            [
                "",
                "## Mechanism-family revisions",
                "",
                "| Family | Revision | Status | Aggregate candidates | Closed by |",
                "|---|---:|---|---|---|",
            ]
        )
        for status in statuses:
            lines.append(
                f"| {status['mechanism_family']} | {status['mechanism_family_revision']} | "
                f"{status['status']} | {', '.join(status['aggregate_candidate_ids']) or '-'} | "
                f"{', '.join(status['closed_by_candidate_ids']) or '-'} |"
            )
    lines.extend(
        [
            "",
            "A terminal failed candidate cannot be automatically reopened or relabeled. "
            "A changed intervention, metric, direction, threshold, horizon, or manipulation "
            "contract requires an explicit new candidate revision.",
            "",
            "After a manipulation-confirmed bounded-path negative, the same family revision "
            "must run an aggregate gate before any additional bounded candidate. This prevents "
            "open-ended component fishing.",
            "",
            "A manipulation-confirmed terminal aggregate-family gate can close its mechanism "
            "family. Reopening requires a higher family revision, an explicit scientific "
            "rationale, and a named directly measurable interface; relabeling a child "
            "candidate is insufficient.",
            "",
            "Manipulation-confirmed promotion failure means the predeclared target was engaged "
            "but the candidate failed its seed-level direction or practical-effect gate. It is "
            "not a universal zero-effect claim outside that candidate specification.",
            "",
        ]
    )
    return "\n".join(lines)




def hydrate_main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Hydrate a workspace candidate ledger from the immutable decision baseline "
            "without changing any scientific decision."
        )
    )
    parser.add_argument("--ledger", required=True)
    parser.add_argument(
        "--decision-baseline",
        help="optional explicit immutable decision baseline; built-in history is used by default",
    )
    args = parser.parse_args(argv)
    hydrate_ledger(
        Path(args.ledger),
        decision_baseline=Path(args.decision_baseline) if args.decision_baseline else None,
        include_builtin_baseline=args.decision_baseline is None,
    )
    return 0

def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Record a paired exploration assessment in a deterministic decision ledger."
    )
    parser.add_argument("--assessment", required=True)
    parser.add_argument("--ledger", required=True)
    parser.add_argument("--candidate-spec")
    parser.add_argument(
        "--decision-baseline",
        help="optional explicit immutable decision baseline; built-in history is used by default",
    )
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
                        response_ticks = int(first["until_tick"]) - int(
                            first["checkpoint_tick"]
                        )
                    assessment["response_ticks"] = response_ticks
                if not assessment.get("manipulation_checks"):
                    assessment["manipulation_checks"] = result.get(
                        "manipulation_checks", []
                    )
    if args.candidate_spec:
        candidate_payload = json.loads(Path(args.candidate_spec).read_text(encoding="utf-8"))
        if str(candidate_payload.get("candidate_id")) != str(assessment.get("candidate_id")):
            raise ValueError("candidate spec id does not match assessment")
        for key, value in candidate_portfolio_metadata(candidate_payload).items():
            if value is not None:
                assessment[key] = value
    ledger, _ = record_assessment(
        Path(args.ledger),
        assessment,
        decision_baseline=Path(args.decision_baseline) if args.decision_baseline else None,
        include_builtin_baseline=args.decision_baseline is None,
    )
    Path(args.ledger).with_suffix(".md").write_text(
        render_markdown(ledger), encoding="utf-8"
    )
    return 0


__all__ = [
    "BUILTIN_DECISION_BASELINE_RESOURCE",
    "LEDGER_SCHEMA",
    "LEGACY_LEDGER_SCHEMAS",
    "assessment_decision",
    "candidate_portfolio_metadata",
    "candidate_signature",
    "candidate_spec_from_payload",
    "canonical_sha",
    "family_revision_statuses",
    "hydrate_ledger",
    "hydrate_main",
    "load_builtin_decision_baseline",
    "load_effective_ledger",
    "load_ledger",
    "merge_ledgers",
    "record_assessment",
    "render_markdown",
    "validate_candidate_for_plan",
]


if __name__ == "__main__":
    raise SystemExit(main())
