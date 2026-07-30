"""Audit candidate-ledger completeness and mechanism-family planning state.

This module is project-governance only. It does not rank scientific mechanisms,
change thresholds, select seeds, or feed information back into simulation state.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Sequence

from .candidate_ledger import candidate_signature, load_ledger
from se.experiments.paired_exploration import load_candidate_spec

SCHEMA = "paired-exploration-portfolio-audit-v1"
SUPPORTED_CANDIDATE_SCHEMA = "paired-exploration-candidate-v1"


def _load_candidate_specs(candidate_dir: Path) -> list[dict[str, Any]]:
    specs: list[dict[str, Any]] = []
    if not candidate_dir.is_dir():
        raise ValueError(f"candidate directory does not exist: {candidate_dir}")
    for path in sorted(candidate_dir.glob("*.json")):
        payload, _ = load_candidate_spec(path)
        if payload.get("schema") != SUPPORTED_CANDIDATE_SCHEMA:
            raise ValueError(f"unsupported candidate schema in {path}")
        specs.append(
            {
                "path": str(path),
                "candidate_id": str(payload["candidate_id"]),
                "candidate_signature_sha256": candidate_signature(payload),
                "mechanism_family": payload.get("mechanism_family"),
                "mechanism_family_revision": payload.get("mechanism_family_revision"),
                "family_role": payload.get("family_role"),
                "terminal_negative_closes_family": payload.get(
                    "terminal_negative_closes_family", False
                ),
                "family_revision_rationale": payload.get("family_revision_rationale"),
                "family_revision_interface": payload.get("family_revision_interface"),
            }
        )
    return specs


def build_portfolio_audit(
    ledger_path: str | Path,
    candidate_dir: str | Path,
) -> dict[str, Any]:
    ledger_ref = Path(ledger_path)
    candidate_root = Path(candidate_dir)
    ledger = load_ledger(ledger_ref)
    entries = [dict(entry) for entry in ledger.get("entries", [])]
    specs = _load_candidate_specs(candidate_root)

    entry_by_id: dict[str, list[dict[str, Any]]] = {}
    entry_by_signature: dict[str, list[dict[str, Any]]] = {}
    for entry in entries:
        entry_by_id.setdefault(str(entry.get("candidate_id", "")), []).append(entry)
        entry_by_signature.setdefault(
            str(entry.get("candidate_signature_sha256", "")), []
        ).append(entry)

    candidate_records: list[dict[str, Any]] = []
    conflicts: list[dict[str, Any]] = []
    unrecorded: list[str] = []
    for spec in specs:
        candidate_id = spec["candidate_id"]
        signature = spec["candidate_signature_sha256"]
        id_entries = entry_by_id.get(candidate_id, [])
        signature_entries = entry_by_signature.get(signature, [])
        if id_entries and not any(
            str(entry.get("candidate_signature_sha256")) == signature
            for entry in id_entries
        ):
            conflicts.append(
                {
                    "candidate_id": candidate_id,
                    "reason": "candidate-id-signature-mismatch",
                }
            )
        if signature_entries and not any(
            str(entry.get("candidate_id")) == candidate_id
            for entry in signature_entries
        ):
            conflicts.append(
                {
                    "candidate_id": candidate_id,
                    "reason": "candidate-signature-id-mismatch",
                }
            )
        matched = [
            entry
            for entry in id_entries
            if str(entry.get("candidate_signature_sha256")) == signature
        ]
        if not matched:
            status = "awaiting-assessment"
            unrecorded.append(candidate_id)
        elif any(bool(entry.get("terminal", False)) for entry in matched):
            status = "terminal-recorded"
        else:
            status = "open-recorded"
        candidate_records.append(
            {
                **spec,
                "status": status,
                "recorded_stages": sorted(str(entry.get("stage")) for entry in matched),
                "recorded_decisions": sorted(
                    {str(entry.get("decision")) for entry in matched}
                ),
            }
        )

    open_entries = [
        entry
        for entry in entries
        if not bool(entry.get("terminal", False))
        and str(entry.get("decision")) in {"promote", "review"}
    ]
    open_candidate_ids = sorted(
        {str(entry.get("candidate_id", "")) for entry in open_entries}
    )
    if conflicts:
        state = "invalid-ledger-or-spec-conflict"
        next_action = "resolve deterministic candidate identity conflicts before planning"
    elif unrecorded:
        state = "candidate-specs-awaiting-assessment"
        next_action = "record or execute the listed preregistered candidate specifications"
    elif open_candidate_ids:
        state = "promoted-candidate-open"
        next_action = "plan only the next ledger-authorized disjoint-seed stage"
    else:
        state = "scientific-revision-required"
        next_action = (
            "define a genuinely new candidate family or a higher closed-family revision "
            "with an explicit new directly measurable interface before another paired plan"
        )

    return {
        "schema": SCHEMA,
        "ledger_path": str(ledger_ref),
        "ledger_schema": ledger["schema"],
        "candidate_dir": str(candidate_root),
        "candidate_spec_count": len(specs),
        "ledger_entry_count": len(entries),
        "candidate_records": candidate_records,
        "unrecorded_candidate_spec_ids": sorted(unrecorded),
        "open_candidate_ids": open_candidate_ids,
        "family_revision_statuses": ledger.get("family_revision_statuses", []),
        "conflicts": conflicts,
        "portfolio_state": state,
        "next_action": next_action,
        "same_revision_child_relabeling_authorized": False,
        "threshold_or_horizon_relaxation_authorized": False,
        "automatic_new_candidate_selection": False,
        "world_feedback": False,
    }


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Paired exploration portfolio audit",
        "",
        f"Schema: `{report['schema']}`",
        f"Portfolio state: `{report['portfolio_state']}`",
        "",
        "## Candidate specifications",
        "",
        "| Candidate | Family | Revision | Role | Status | Recorded stages |",
        "|---|---|---:|---|---|---|",
    ]
    for candidate in report["candidate_records"]:
        lines.append(
            f"| {candidate['candidate_id']} | {candidate.get('mechanism_family')} | "
            f"{candidate.get('mechanism_family_revision')} | {candidate.get('family_role')} | "
            f"{candidate['status']} | {', '.join(candidate['recorded_stages']) or '-'} |"
        )
    lines.extend(
        [
            "",
            "## Mechanism-family revisions",
            "",
            "| Family | Revision | Status | Closed by |",
            "|---|---:|---|---|",
        ]
    )
    for status in report["family_revision_statuses"]:
        lines.append(
            f"| {status['mechanism_family']} | {status['mechanism_family_revision']} | "
            f"{status['status']} | {', '.join(status['closed_by_candidate_ids']) or '-'} |"
        )
    lines.extend(
        [
            "",
            "## Governance decision",
            "",
            f"- next action: {report['next_action']}",
            f"- unrecorded candidate specs: {report['unrecorded_candidate_spec_ids']}",
            f"- open candidates: {report['open_candidate_ids']}",
            f"- conflicts: {report['conflicts']}",
            "- no threshold, horizon, seed, or family status is changed by this audit",
            "- feedback to world: false",
            "",
        ]
    )
    return "\n".join(lines)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Audit paired-exploration candidate and family planning state."
    )
    parser.add_argument("--ledger", required=True)
    parser.add_argument("--candidate-dir", default="protocols/candidates")
    parser.add_argument("--output", required=True)
    args = parser.parse_args(argv)
    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=True)
    report = build_portfolio_audit(args.ledger, args.candidate_dir)
    (output / "exploration_portfolio_audit.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    (output / "exploration_portfolio_audit.md").write_text(
        render_markdown(report), encoding="utf-8"
    )
    return 0 if not report["conflicts"] else 2


__all__ = ["SCHEMA", "build_portfolio_audit", "render_markdown", "main"]


if __name__ == "__main__":
    raise SystemExit(main())
