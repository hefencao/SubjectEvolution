"""Freeze and verify portable study evidence across project versions.

A study bundle separates immutable scientific evidence from mutable runtime
locations.  Small plans, assessments, decisions and summaries are copied into
``studies/<study>/frozen``.  Large checkpoints remain in ``runs`` and are
referenced by their recorded content hashes and logical roles.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import shutil
from typing import Any, Sequence

from .. import __version__
from ..workspace import artifact_ref, portable_path, resolve_path, sha256_file, workspace_root
from .candidate_ledger import candidate_signature, canonical_sha, load_ledger
from .exploration_protocol import _canonical_config
from ..experiments.paired_exploration import load_candidate_spec

STUDY_SCHEMA = "se-study-bundle-v1"
STAGE_SCHEMA = "se-study-stage-freeze-v2"
CHAIN_SCHEMA = "se-study-chain-lock-v1"
LEGACY_DECISION_SCHEMA = "se-study-legacy-decision-lock-v1"
_STAGE_ORDER = {"smoke": 0, "screen": 1, "replication": 2, "confirmation": 3}
_REQUIRED_ROLES = ("source_plan", "paired_plan", "assessment", "decision")


def _read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"expected JSON object in {path}")
    return payload


def load_study(path: str | Path) -> dict[str, Any]:
    study_path = Path(path)
    payload = _read_json(study_path)
    if payload.get("schema") != STUDY_SCHEMA:
        raise ValueError(f"unsupported study schema in {study_path}: {payload.get('schema')!r}")
    if not str(payload.get("study_id", "")).strip():
        raise ValueError("study_id cannot be empty")
    if not str(payload.get("candidate_id", "")).strip():
        raise ValueError("candidate_id cannot be empty")
    return payload


def _candidate_path(study_path: Path, study: dict[str, Any], root: Path) -> Path:
    value = study.get("candidate_spec")
    if not isinstance(value, dict) or not value.get("path"):
        raise ValueError("study candidate_spec.path is required")
    return resolve_path(str(value["path"]), root=root)


def _validate_study_candidate(
    study: dict[str, Any], candidate_path: Path, candidate: dict[str, Any]
) -> str:
    signature = candidate_signature(candidate)
    configured_signature = str(study["candidate_spec"].get("signature_sha256", ""))
    if configured_signature and configured_signature != signature:
        raise ValueError("study candidate signature does not match candidate spec")
    configured_content = str(study["candidate_spec"].get("content_sha256", ""))
    if configured_content and configured_content != sha256_file(candidate_path):
        raise ValueError("study candidate content hash does not match candidate spec")
    return signature


def _copy_evidence(source: Path, destination: Path) -> dict[str, Any]:
    """Copy small evidence without persisting machine-specific source paths."""
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)
    payload = _read_json(source)
    return {
        "source_name": source.name,
        "frozen_path": destination.name,
        "schema": payload.get("schema"),
        "sha256": sha256_file(destination),
    }



def _source_protocol_identity(
    *,
    study: dict[str, Any],
    stage: str,
    source_plan: dict[str, Any],
    root: Path,
) -> tuple[str, dict[str, Any]]:
    protocols = study.get("protocols", {})
    config_value = protocols.get(stage) if isinstance(protocols, dict) else None
    if not config_value:
        raise ValueError(f"study protocols.{stage} is required to freeze this stage")
    config_path = resolve_path(str(config_value), root=root)
    if not config_path.is_file():
        raise ValueError(f"study source protocol does not exist: {config_path}")
    _, resolved_sha, protocol_sha = _canonical_config(config_path)
    recorded_config_sha = source_plan.get("resolved_config_sha256")
    if recorded_config_sha and str(recorded_config_sha) != resolved_sha:
        raise ValueError(
            f"{stage} study protocol does not match the source plan configuration hash"
        )
    recorded_protocol_sha = source_plan.get("replication_protocol_sha256")
    if recorded_protocol_sha and str(recorded_protocol_sha) != protocol_sha:
        raise ValueError(
            f"{stage} study protocol does not match the source plan protocol fingerprint"
        )
    return protocol_sha, artifact_ref(config_path, root=root, role="source-protocol")

def _validate_candidate_and_stage(
    *,
    study: dict[str, Any],
    stage: str,
    source_plan: dict[str, Any],
    paired_plan: dict[str, Any],
    assessment: dict[str, Any],
    decision: dict[str, Any],
    source_plan_sha: str,
) -> dict[str, Any]:
    candidate_id = str(study["candidate_id"])
    for role, payload in (
        ("paired plan", paired_plan),
        ("assessment", assessment),
        ("decision", decision),
    ):
        if payload.get("candidate_id") != candidate_id:
            raise ValueError(f"{role} candidate_id does not match study")
        if payload.get("stage") != stage:
            raise ValueError(f"{role} stage does not match requested stage")
    if source_plan.get("stage") != stage:
        raise ValueError("source plan stage does not match requested stage")
    recorded_source_sha = paired_plan.get("source_plan_sha256")
    if recorded_source_sha and str(recorded_source_sha) != source_plan_sha:
        raise ValueError("paired plan does not reference the supplied source plan hash")
    assessment_source_sha = assessment.get("source_plan_sha256")
    if assessment_source_sha and str(assessment_source_sha) != source_plan_sha:
        raise ValueError("assessment does not reference the supplied source plan hash")
    source_candidate = str(source_plan.get("candidate_id", ""))
    if source_candidate == candidate_id:
        binding = {
            "mode": "exact-candidate",
            "source_candidate_id": source_candidate,
            "candidate_id": candidate_id,
        }
    else:
        # Legacy source cohorts could be deliberately generic.  Their binding is
        # accepted only when the paired plan and assessment both bind the exact
        # source-plan content hash to the study candidate.
        if not recorded_source_sha:
            raise ValueError(
                "legacy generic source plan requires paired-plan source hash binding"
            )
        binding = {
            "mode": "paired-plan-source-hash-binding",
            "source_candidate_id": source_candidate,
            "candidate_id": candidate_id,
            "source_plan_sha256": source_plan_sha,
        }
    return binding


def _legacy_location_hint(value: str) -> str:
    parts = Path(value).parts
    for marker in ("runs", "analyses"):
        if marker in parts:
            return Path(*parts[parts.index(marker) :]).as_posix()
    return Path(value).name


def _external_runtime_refs(
    study: dict[str, Any], stage: str, paired_plan: dict[str, Any]
) -> list[dict[str, Any]]:
    refs: list[dict[str, Any]] = []
    layout = study.get("workspace_layout", {})
    source_template = str(layout.get("source_runs", "runs/base/<stage>"))
    source_root = Path(source_template.replace("<stage>", stage))
    for panel in paired_plan.get("panels", []):
        if not isinstance(panel, dict):
            continue
        checkpoint = panel.get("checkpoint_path")
        checkpoint_sha = panel.get("checkpoint_sha256")
        if checkpoint and checkpoint_sha:
            seed = int(panel["seed"])
            tick = int(panel.get("checkpoint_tick", -1))
            canonical = source_root / f"seed_{seed}" / f"checkpoint_{tick:08d}.sechk"
            refs.append(
                {
                    "role": "source-checkpoint",
                    "seed": seed,
                    "tick": tick,
                    "path": canonical.as_posix(),
                    "legacy_location_hint": _legacy_location_hint(str(checkpoint)),
                    "sha256": str(checkpoint_sha),
                }
            )
    return refs


def freeze_stage(
    *,
    study_path: str | Path,
    stage: str,
    source_plan_path: str | Path,
    paired_plan_path: str | Path,
    assessment_path: str | Path,
    decision_path: str | Path,
    results_path: str | Path | None = None,
    workspace: str | Path | None = None,
) -> dict[str, Any]:
    if stage not in _STAGE_ORDER:
        raise ValueError(f"unsupported study stage: {stage}")
    root = workspace_root(workspace)
    study_file = resolve_path(study_path, root=root)
    study = load_study(study_file)
    candidate_path = _candidate_path(study_file, study, root)
    candidate, _ = load_candidate_spec(candidate_path)
    if candidate.get("candidate_id") != study["candidate_id"]:
        raise ValueError("study candidate spec does not match candidate_id")
    expected_signature = _validate_study_candidate(study, candidate_path, candidate)

    paths = {
        "source_plan": resolve_path(source_plan_path, root=root),
        "paired_plan": resolve_path(paired_plan_path, root=root),
        "assessment": resolve_path(assessment_path, root=root),
        "decision": resolve_path(decision_path, root=root),
    }
    if results_path is not None:
        paths["results"] = resolve_path(results_path, root=root)
    for role, path in paths.items():
        if not path.is_file():
            raise ValueError(f"{role} does not exist: {path}")

    payloads = {role: _read_json(path) for role, path in paths.items()}
    source_sha = sha256_file(paths["source_plan"])
    binding = _validate_candidate_and_stage(
        study=study,
        stage=stage,
        source_plan=payloads["source_plan"],
        paired_plan=payloads["paired_plan"],
        assessment=payloads["assessment"],
        decision=payloads["decision"],
        source_plan_sha=source_sha,
    )
    results = payloads.get("results")
    if results is not None:
        if results.get("candidate_id") != study["candidate_id"]:
            raise ValueError("results candidate_id does not match study")
        if results.get("stage") != stage:
            raise ValueError("results stage does not match requested stage")
    source_protocol_sha, source_config_ref = _source_protocol_identity(
        study=study,
        stage=stage,
        source_plan=payloads["source_plan"],
        root=root,
    )
    assessment_signature = payloads["assessment"].get("candidate_signature_sha256")
    if assessment_signature and str(assessment_signature) != expected_signature:
        raise ValueError("assessment candidate signature does not match frozen candidate")
    decision_assessment_sha = payloads["decision"].get("assessment_sha256")
    if decision_assessment_sha and str(decision_assessment_sha) != canonical_sha(payloads["assessment"]):
        raise ValueError("decision does not reference the supplied assessment hash")

    study_dir = study_file.parent
    frozen_dir = study_dir / "frozen" / stage
    if frozen_dir.exists():
        raise ValueError(f"stage is already frozen: {frozen_dir}")
    frozen_dir.mkdir(parents=True)
    evidence: dict[str, Any] = {}
    canonical_names = {
        "source_plan": "source_plan.json",
        "paired_plan": "paired_plan.json",
        "results": "results.json",
        "assessment": "assessment.json",
        "decision": "decision.json",
    }
    for role, path in paths.items():
        evidence[role] = _copy_evidence(path, frozen_dir / canonical_names[role])

    stage_manifest = {
        "schema": STAGE_SCHEMA,
        "study_id": study["study_id"],
        "candidate_id": study["candidate_id"],
        "candidate_signature_sha256": expected_signature,
        "stage": stage,
        "frozen_by_version": __version__,
        "source_binding": binding,
        "source_protocol_sha256": source_protocol_sha,
        "source_config": source_config_ref,
        "seeds": [int(seed) for seed in payloads["paired_plan"].get("seeds", [])],
        "decision": payloads["decision"].get("decision"),
        "terminal": bool(payloads["decision"].get("terminal", False)),
        "recommendation": payloads["decision"].get("recommendation"),
        "median_relative_effect": payloads["assessment"].get(
            "equal_seed_median_relative_effect"
        ),
        "direction_consistency": payloads["assessment"].get("direction_consistency"),
        "exact_two_sided_sign_flip_p": payloads["assessment"].get(
            "exact_two_sided_sign_flip_p"
        ),
        "evidence": evidence,
        "external_runtime_artifacts": _external_runtime_refs(
            study, stage, payloads["paired_plan"]
        ),
        "raw_runtime_copied_into_study": False,
        "selection_claim_allowed": bool(
            payloads["assessment"].get("selection_claim_allowed", False)
        ),
    }
    manifest_path = frozen_dir / "stage.lock.json"
    manifest_path.write_text(
        json.dumps(stage_manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    rebuild_chain_lock(study_file, workspace=root)
    return stage_manifest



def freeze_legacy_decision(
    *,
    study_path: str | Path,
    ledger_path: str | Path,
    stage: str,
    workspace: str | Path | None = None,
) -> dict[str, Any]:
    """Freeze the strongest surviving record for a pre-bundle result.

    This never invents missing plans, assessments, or checkpoints.  It records
    the immutable ledger entry and explicitly declares the evidence gap.
    """
    if stage not in _STAGE_ORDER:
        raise ValueError(f"unsupported study stage: {stage}")
    root = workspace_root(workspace)
    study_file = resolve_path(study_path, root=root)
    study = load_study(study_file)
    candidate_path = _candidate_path(study_file, study, root)
    candidate, _ = load_candidate_spec(candidate_path)
    signature = _validate_study_candidate(study, candidate_path, candidate)
    ledger_file = resolve_path(ledger_path, root=root)
    ledger = load_ledger(ledger_file)
    matches = [
        dict(entry)
        for entry in ledger.get("entries", [])
        if entry.get("candidate_id") == study["candidate_id"]
        and entry.get("stage") == stage
        and entry.get("candidate_signature_sha256") == signature
    ]
    if len(matches) != 1:
        raise ValueError(
            f"expected one immutable ledger entry for {study['candidate_id']} {stage}; "
            f"found {len(matches)}"
        )
    entry = matches[0]
    lock = {
        "schema": LEGACY_DECISION_SCHEMA,
        "study_id": study["study_id"],
        "candidate_id": study["candidate_id"],
        "candidate_signature_sha256": signature,
        "stage": stage,
        "frozen_by_version": __version__,
        "decision_entry": entry,
        "decision_entry_sha256": canonical_sha(entry),
        "decision_source": {
            "path": portable_path(ledger_file, root=root),
            "role": "immutable-decision-baseline",
            "ledger_schema": ledger.get("schema"),
        },
        "evidence_completeness": "legacy-decision-only",
        "available_evidence": [
            "candidate specification",
            "canonical decision-ledger entry",
            "assessment content hash recorded by the decision entry",
            "seed set and bounded outcome summary recorded by the decision entry",
        ],
        "unavailable_evidence": [
            "source plan payload",
            "paired plan payload",
            "assessment payload",
            "result payload",
            "source checkpoint content hashes",
        ],
        "missing_evidence_was_reconstructed": False,
        "selection_claim_allowed": False,
    }
    destination = study_file.parent / "frozen" / "legacy" / f"{stage}.lock.json"
    if destination.exists():
        raise ValueError(f"legacy decision is already frozen: {destination}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(
        json.dumps(lock, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    rebuild_chain_lock(study_file, workspace=root)
    return lock


def _legacy_decision_locks(study_dir: Path) -> list[tuple[str, Path, dict[str, Any]]]:
    records: list[tuple[str, Path, dict[str, Any]]] = []
    for path in sorted((study_dir / "frozen" / "legacy").glob("*.lock.json")):
        payload = _read_json(path)
        records.append((str(payload.get("stage", path.stem)), path, payload))
    return sorted(records, key=lambda row: _STAGE_ORDER.get(row[0], 99))

def _stage_manifests(study_dir: Path) -> list[tuple[str, Path, dict[str, Any]]]:
    records: list[tuple[str, Path, dict[str, Any]]] = []
    frozen = study_dir / "frozen"
    if not frozen.is_dir():
        return records
    for path in sorted(frozen.glob("*/stage.lock.json")):
        payload = _read_json(path)
        stage = str(payload.get("stage", path.parent.name))
        records.append((stage, path, payload))
    return sorted(records, key=lambda row: _STAGE_ORDER.get(row[0], 99))


def _build_chain_lock(
    study_file: Path, *, root: Path
) -> dict[str, Any]:
    study = load_study(study_file)
    candidate_path = _candidate_path(study_file, study, root)
    candidate, _ = load_candidate_spec(candidate_path)
    _validate_study_candidate(study, candidate_path, candidate)
    stages = []
    prior_seeds: set[int] = set()
    for stage, path, payload in _stage_manifests(study_file.parent):
        seeds = {int(seed) for seed in payload.get("seeds", [])}
        overlap = sorted(prior_seeds & seeds)
        if overlap:
            raise ValueError(f"frozen stages reuse independent seeds: {overlap}")
        prior_seeds |= seeds
        stages.append(
            {
                "stage": stage,
                "manifest_path": portable_path(path, root=root),
                "manifest_sha256": sha256_file(path),
                "decision": payload.get("decision"),
                "terminal": payload.get("terminal"),
                "recommendation": payload.get("recommendation"),
                "source_protocol_sha256": payload.get("source_protocol_sha256"),
                "source_binding_mode": payload.get("source_binding", {}).get("mode"),
                "median_relative_effect": payload.get("median_relative_effect"),
                "direction_consistency": payload.get("direction_consistency"),
                "exact_two_sided_sign_flip_p": payload.get("exact_two_sided_sign_flip_p"),
                "seeds": sorted(seeds),
            }
        )
    legacy_decisions = []
    for stage, path, payload in _legacy_decision_locks(study_file.parent):
        legacy_decisions.append(
            {
                "stage": stage,
                "lock_path": portable_path(path, root=root),
                "lock_sha256": sha256_file(path),
                "decision": payload.get("decision_entry", {}).get("decision"),
                "terminal": payload.get("decision_entry", {}).get("terminal"),
                "recommendation": payload.get("decision_entry", {}).get("recommendation"),
                "seeds": sorted(
                    int(seed)
                    for seed in payload.get("decision_entry", {}).get("all_stage_seeds", [])
                ),
                "evidence_completeness": payload.get("evidence_completeness"),
            }
        )
    protocol_hashes = {
        str(row["source_protocol_sha256"])
        for row in stages
        if row.get("source_protocol_sha256")
    }
    if len(protocol_hashes) > 1:
        raise ValueError(
            "frozen inferential stages do not share one source protocol fingerprint"
        )
    return {
        "schema": CHAIN_SCHEMA,
        "study_id": study["study_id"],
        "candidate_id": study["candidate_id"],
        "candidate_signature_sha256": candidate_signature(candidate),
        "candidate_spec": artifact_ref(candidate_path, root=root, role="candidate-spec"),
        "stages": stages,
        "legacy_decisions": legacy_decisions,
        "all_stage_seeds": sorted(prior_seeds),
        "source_protocol_sha256": next(iter(protocol_hashes), None),
        "latest_stage": (
            stages[-1]["stage"]
            if stages
            else (legacy_decisions[-1]["stage"] if legacy_decisions else None)
        ),
        "latest_recommendation": (
            stages[-1]["recommendation"]
            if stages
            else (
                legacy_decisions[-1]["recommendation"]
                if legacy_decisions
                else None
            )
        ),
        "selection_claim_allowed": False,
    }


def _render_run_chain_text(study: dict[str, Any], chain: dict[str, Any]) -> str:
    lines = [
        f"# {study['study_id']} frozen run chain",
        "",
        f"Candidate: `{study['candidate_id']}`",
        f"Study schema: `{study['schema']}`",
        f"Chain schema: `{chain['schema']}`",
        "",
        "This file summarizes immutable evidence only. Executable next-stage commands, when authorized, are kept in a separate numerically ordered `commands/` directory.",
        "",
        "## Design",
        "",
        str(study.get("summary", "")),
    ]
    if chain["stages"]:
        lines.extend(
            [
                "",
                "## Full frozen stages",
                "",
                "Source protocol SHA-256: `" + str(chain.get("source_protocol_sha256")) + "`",
                "",
                "| Stage | Seeds | Binding | Median effect | Direction | Decision | Recommendation | Manifest |",
                "|---|---:|---|---:|---:|---|---|---|",
            ]
        )
    for row in chain["stages"]:
        effect = row.get("median_relative_effect")
        effect_text = "-" if effect is None else f"{float(effect):+.6%}"
        direction = row.get("direction_consistency")
        direction_text = "-" if direction is None else f"{float(direction):.3f}"
        lines.append(
            f"| {row['stage']} | {len(row['seeds'])} | {row.get('source_binding_mode')} | "
            f"{effect_text} | {direction_text} | {row['decision']} | "
            f"{row['recommendation']} | `{row['manifest_path']}` |"
        )
    if chain.get("legacy_decisions"):
        lines.extend(
            [
                "",
                "## Legacy decision-only stages",
                "",
                "These rows preserve the strongest surviving release evidence. Missing raw artifacts are declared rather than reconstructed.",
                "",
                "| Stage | Seeds | Decision | Recommendation | Completeness | Lock |",
                "|---|---:|---|---|---|---|",
            ]
        )
        for row in chain["legacy_decisions"]:
            lines.append(
                f"| {row['stage']} | {len(row['seeds'])} | {row['decision']} | "
                f"{row['recommendation']} | {row['evidence_completeness']} | "
                f"`{row['lock_path']}` |"
            )
    lines.extend(
        [
            "",
            "## Path roles",
            "",
            "- source trajectories and checkpoints belong under `runs/base/`;",
            "- intervention branches belong under `runs/interventions/`;",
            "- derived assessments and audits belong under `analyses/`;",
            "- mutable workspace decision overlays belong under `state/decisions/`;",
            "- this study directory contains only protocol, commands and frozen evidence.",
            "",
        ]
    )
    return "\n".join(lines)


def rebuild_chain_lock(
    study_path: str | Path, *, workspace: str | Path | None = None
) -> dict[str, Any]:
    root = workspace_root(workspace)
    study_file = resolve_path(study_path, root=root)
    chain = _build_chain_lock(study_file, root=root)
    chain_path = study_file.parent / "frozen" / "chain.lock.json"
    chain_path.parent.mkdir(parents=True, exist_ok=True)
    chain_path.write_text(
        json.dumps(chain, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    render_run_chain(study_file, chain, workspace=root)
    return chain


def render_run_chain(
    study_path: Path, chain: dict[str, Any], *, workspace: str | Path | None = None
) -> str:
    root = workspace_root(workspace)
    study_file = resolve_path(study_path, root=root)
    text = _render_run_chain_text(load_study(study_file), chain)
    (study_file.parent / "RUN_CHAIN.md").write_text(text, encoding="utf-8")
    return text


def verify_study(
    study_path: str | Path,
    *,
    workspace: str | Path | None = None,
    verify_runtime: bool = False,
) -> dict[str, Any]:
    root = workspace_root(workspace)
    study_file = resolve_path(study_path, root=root)
    study = load_study(study_file)
    candidate_path = _candidate_path(study_file, study, root)
    candidate, _ = load_candidate_spec(candidate_path)
    failures: list[str] = []
    try:
        _validate_study_candidate(study, candidate_path, candidate)
    except ValueError as exc:
        failures.append(str(exc))
    runtime_missing: list[str] = []
    stages = _stage_manifests(study_file.parent)
    seen_seeds: set[int] = set()
    for stage, manifest_path, manifest in stages:
        if manifest.get("study_id") != study["study_id"]:
            failures.append(f"{stage}: study id mismatch")
        if manifest.get("schema") not in {"se-study-stage-freeze-v1", STAGE_SCHEMA}:
            failures.append(f"{stage}: unsupported stage manifest schema")
        if manifest.get("candidate_signature_sha256") != candidate_signature(candidate):
            failures.append(f"{stage}: candidate signature mismatch")
        stage_seeds = {int(seed) for seed in manifest.get("seeds", [])}
        overlap = seen_seeds & stage_seeds
        if overlap:
            failures.append(f"{stage}: repeated seeds {sorted(overlap)}")
        seen_seeds |= stage_seeds
        evidence_payloads: dict[str, dict[str, Any]] = {}
        for role, ref in manifest.get("evidence", {}).items():
            frozen_path = manifest_path.parent / str(ref["frozen_path"])
            if not frozen_path.is_file():
                failures.append(f"{stage}:{role}: missing frozen evidence")
            elif sha256_file(frozen_path) != ref.get("sha256"):
                failures.append(f"{stage}:{role}: hash mismatch")
            else:
                evidence_payloads[role] = _read_json(frozen_path)
        if all(role in evidence_payloads for role in _REQUIRED_ROLES):
            try:
                derived_binding = _validate_candidate_and_stage(
                    study=study,
                    stage=stage,
                    source_plan=evidence_payloads["source_plan"],
                    paired_plan=evidence_payloads["paired_plan"],
                    assessment=evidence_payloads["assessment"],
                    decision=evidence_payloads["decision"],
                    source_plan_sha=sha256_file(manifest_path.parent / "source_plan.json"),
                )
                if manifest.get("source_binding") != derived_binding:
                    failures.append(f"{stage}: source binding mismatch")
                decision_sha = evidence_payloads["decision"].get("assessment_sha256")
                if decision_sha and decision_sha != canonical_sha(evidence_payloads["assessment"]):
                    failures.append(f"{stage}: decision assessment hash mismatch")
                results = evidence_payloads.get("results")
                if results is not None and (
                    results.get("candidate_id") != study["candidate_id"]
                    or results.get("stage") != stage
                ):
                    failures.append(f"{stage}: results identity mismatch")
                protocol_sha, config_ref = _source_protocol_identity(
                    study=study,
                    stage=stage,
                    source_plan=evidence_payloads["source_plan"],
                    root=root,
                )
                if manifest.get("source_protocol_sha256") != protocol_sha:
                    failures.append(f"{stage}: source protocol hash mismatch")
                if manifest.get("source_config", {}).get("sha256") != config_ref["sha256"]:
                    failures.append(f"{stage}: source config hash mismatch")
                if stage_seeds != {
                    int(seed) for seed in evidence_payloads["paired_plan"].get("seeds", [])
                }:
                    failures.append(f"{stage}: manifest seed set mismatch")
            except ValueError as exc:
                failures.append(f"{stage}: semantic chain invalid: {exc}")
        if verify_runtime:
            for ref in manifest.get("external_runtime_artifacts", []):
                path = resolve_path(str(ref["path"]), root=root)
                if not path.is_file():
                    runtime_missing.append(str(ref["path"]))
                elif sha256_file(path) != ref.get("sha256"):
                    failures.append(f"{stage}: runtime hash mismatch: {path}")
    for stage, lock_path, lock in _legacy_decision_locks(study_file.parent):
        if lock.get("schema") != LEGACY_DECISION_SCHEMA:
            failures.append(f"{stage}: unsupported legacy decision schema")
        if lock.get("study_id") != study["study_id"]:
            failures.append(f"{stage}: legacy study id mismatch")
        if lock.get("candidate_signature_sha256") != candidate_signature(candidate):
            failures.append(f"{stage}: legacy candidate signature mismatch")
        entry = lock.get("decision_entry", {})
        if canonical_sha(entry) != lock.get("decision_entry_sha256"):
            failures.append(f"{stage}: legacy decision entry hash mismatch")
        if entry.get("candidate_id") != study["candidate_id"] or entry.get("stage") != stage:
            failures.append(f"{stage}: legacy decision identity mismatch")
        source_ref = lock.get("decision_source", {})
        source_path = resolve_path(str(source_ref.get("path", "")), root=root)
        if not source_path.is_file():
            failures.append(f"{stage}: immutable decision source missing")
        else:
            source_ledger = load_ledger(source_path)
            source_entry_hashes = {
                canonical_sha(item) for item in source_ledger.get("entries", [])
            }
            if lock.get("decision_entry_sha256") not in source_entry_hashes:
                failures.append(f"{stage}: immutable decision entry missing from baseline")
        if lock.get("evidence_completeness") != "legacy-decision-only":
            failures.append(f"{stage}: legacy evidence completeness is ambiguous")
    chain_path = study_file.parent / "frozen" / "chain.lock.json"
    run_chain_path = study_file.parent / "RUN_CHAIN.md"
    existing_chain = _read_json(chain_path) if chain_path.is_file() else None
    existing_run_chain = (
        run_chain_path.read_text(encoding="utf-8") if run_chain_path.is_file() else None
    )
    expected_chain: dict[str, Any] | None = None
    try:
        expected_chain = _build_chain_lock(study_file, root=root)
    except ValueError as exc:
        failures.append(f"frozen chain evidence is invalid: {exc}")
    if existing_chain is None:
        failures.append("frozen chain lock is missing")
    elif expected_chain is not None and existing_chain != expected_chain:
        failures.append("frozen chain lock does not match stage evidence")
    expected_run_chain = (
        _render_run_chain_text(study, expected_chain)
        if expected_chain is not None
        else None
    )
    if existing_run_chain is None:
        failures.append("run-chain summary is missing")
    elif expected_run_chain is not None and existing_run_chain != expected_run_chain:
        failures.append("run-chain summary does not match frozen evidence")
    effective_chain = expected_chain or existing_chain or {}
    return {
        "schema": "se-study-verification-v1",
        "study_id": study["study_id"],
        "frozen_stage_count": len(stages),
        "passed": not failures,
        "failures": failures,
        "runtime_verification_requested": verify_runtime,
        "runtime_artifacts_missing": runtime_missing,
        "chain_sha256": sha256_file(chain_path) if chain_path.is_file() else None,
        "latest_stage": effective_chain.get("latest_stage"),
    }




def _copy_or_link_file(source: Path, target: Path, *, materialize: str) -> str:
    if source.is_symlink():
        raise ValueError(f"legacy runtime migration refuses symlinks: {source}")
    if target.exists():
        if not target.is_file() or sha256_file(target) != sha256_file(source):
            raise ValueError(f"migration target conflicts with source: {target}")
        return "already-present"
    target.parent.mkdir(parents=True, exist_ok=True)
    if materialize in {"auto", "hardlink"}:
        try:
            target.hardlink_to(source)
            return "hardlink"
        except OSError:
            if materialize == "hardlink":
                raise
    shutil.copy2(source, target)
    return "copy"


def _materialize_tree(source: Path, target: Path, *, materialize: str) -> int:
    count = 0
    if not source.exists():
        return count
    for path in sorted(source.rglob("*")):
        if path.is_dir():
            continue
        relative = path.relative_to(source)
        _copy_or_link_file(path, target / relative, materialize=materialize)
        count += 1
    return count


def migrate_stage_layout(
    study_path: str | Path,
    *,
    stage: str,
    legacy_source_root: str | Path,
    legacy_paired_root: str | Path,
    workspace: str | Path | None = None,
    materialize: str = "auto",
) -> dict[str, Any]:
    """Split one legacy mixed stage into canonical run and analysis roots.

    Compact evidence and every source checkpoint anchor are verified before any
    file is materialized.  Existing targets are accepted only when byte-identical.
    Original legacy directories are never deleted automatically.
    """
    if materialize not in {"auto", "copy", "hardlink"}:
        raise ValueError("materialize must be auto, copy, or hardlink")
    root = workspace_root(workspace)
    study_file = resolve_path(study_path, root=root)
    study = load_study(study_file)
    source_root = resolve_path(legacy_source_root, root=root)
    paired_root = resolve_path(legacy_paired_root, root=root)
    if not source_root.is_dir() or not paired_root.is_dir():
        raise ValueError("legacy source and paired roots must both exist")
    manifests = {
        name: (path, payload)
        for name, path, payload in _stage_manifests(study_file.parent)
    }
    if stage not in manifests:
        raise ValueError(f"stage is not frozen: {stage}")
    manifest_path, manifest = manifests[stage]

    evidence_names = {
        "source_plan": "exploration_plan.json",
        "paired_plan": "paired_exploration_plan.json",
        "results": "paired_exploration_results.json",
        "assessment": "paired_exploration_assessment.json",
        "decision": "candidate_decision.json",
    }
    validation_paths: dict[str, Path] = {}
    for role, ref in manifest.get("evidence", {}).items():
        if role not in evidence_names:
            continue
        base = source_root if role == "source_plan" else paired_root
        candidate = base / evidence_names[role]
        if not candidate.is_file() or sha256_file(candidate) != ref.get("sha256"):
            raise ValueError(f"legacy {role} does not match frozen evidence: {candidate}")
        validation_paths[role] = candidate

    for ref in manifest.get("external_runtime_artifacts", []):
        checkpoint = (
            source_root
            / f"seed_{int(ref['seed'])}"
            / Path(str(ref["path"])).name
        )
        if not checkpoint.is_file() or sha256_file(checkpoint) != ref.get("sha256"):
            raise ValueError(
                f"legacy source checkpoint does not match frozen hash: {checkpoint}"
            )

    layout = study.get("workspace_layout", {})
    source_target = resolve_path(
        str(layout["source_runs"]).replace("<stage>", stage), root=root
    )
    intervention_target = resolve_path(
        str(layout["intervention_runs"]).replace("<stage>", stage), root=root
    )
    analysis_target = resolve_path(
        str(layout["analyses"]).replace("<stage>", stage), root=root
    )

    source_runtime_names = {
        "exploration_plan.json",
        "exploration_plan.md",
        "multi_seed_plan.json",
        "multi_seed_index.json",
    }
    paired_runtime_names = {
        "paired_exploration_plan.json",
        "paired_exploration_plan.md",
    }
    copied = {"source_runtime": 0, "intervention_runtime": 0, "analysis": 0}
    for child in sorted(source_root.iterdir()):
        if child.name.startswith("seed_") and child.is_dir():
            copied["source_runtime"] += _materialize_tree(
                child, source_target / child.name, materialize=materialize
            )
        elif child.is_file() and child.name in source_runtime_names:
            _copy_or_link_file(
                child, source_target / child.name, materialize=materialize
            )
            copied["source_runtime"] += 1
        elif child.is_file():
            _copy_or_link_file(
                child, analysis_target / "source" / child.name, materialize=materialize
            )
            copied["analysis"] += 1
    for child in sorted(paired_root.iterdir()):
        if child.name.startswith("seed_") and child.is_dir():
            copied["intervention_runtime"] += _materialize_tree(
                child, intervention_target / child.name, materialize=materialize
            )
        elif child.is_file() and child.name in paired_runtime_names:
            _copy_or_link_file(
                child, intervention_target / child.name, materialize=materialize
            )
            copied["intervention_runtime"] += 1
        elif child.is_file():
            _copy_or_link_file(
                child, analysis_target / child.name, materialize=materialize
            )
            copied["analysis"] += 1

    report = {
        "schema": "se-study-layout-migration-v1",
        "study_id": study["study_id"],
        "stage": stage,
        "materialize": materialize,
        "legacy_source_hint": _legacy_location_hint(str(source_root)),
        "legacy_paired_hint": _legacy_location_hint(str(paired_root)),
        "source_run_root": portable_path(source_target, root=root),
        "intervention_run_root": portable_path(intervention_target, root=root),
        "analysis_root": portable_path(analysis_target, root=root),
        "validated_evidence_roles": sorted(validation_paths),
        "validated_checkpoint_count": len(manifest.get("external_runtime_artifacts", [])),
        "materialized_file_counts": copied,
        "legacy_roots_deleted": False,
    }
    report_path = manifest_path.parent / "layout_migration.lock.json"
    report_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return report


def layout_migrate_main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Split a verified legacy study stage into canonical workspace roots."
    )
    parser.add_argument("--study", required=True)
    parser.add_argument("--stage", required=True, choices=tuple(_STAGE_ORDER))
    parser.add_argument("--legacy-source-root", required=True)
    parser.add_argument("--legacy-paired-root", required=True)
    parser.add_argument("--materialize", choices=("auto", "copy", "hardlink"), default="auto")
    parser.add_argument("--workspace-root", default=".")
    args = parser.parse_args(argv)
    report = migrate_stage_layout(
        args.study,
        stage=args.stage,
        legacy_source_root=args.legacy_source_root,
        legacy_paired_root=args.legacy_paired_root,
        workspace=args.workspace_root,
        materialize=args.materialize,
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0

def migrate_runtime_artifacts(
    study_path: str | Path,
    *,
    search_roots: Sequence[str | Path],
    workspace: str | Path | None = None,
    materialize: str = "auto",
) -> dict[str, Any]:
    """Materialize hash-matched legacy checkpoints into canonical ``runs`` paths.

    Discovery is content-addressed. No file is written until every missing
    artifact has a usable hash match. Existing byte-identical targets make the
    operation idempotent after interruption.
    """
    if materialize not in {"auto", "copy", "hardlink"}:
        raise ValueError("materialize must be auto, copy, or hardlink")
    root = workspace_root(workspace)
    study_file = resolve_path(study_path, root=root)
    study = load_study(study_file)
    roots = [resolve_path(value, root=root) for value in search_roots]
    for value in roots:
        if not value.is_dir():
            raise ValueError(f"runtime search root does not exist: {value}")

    expected: list[dict[str, Any]] = []
    for stage, manifest_path, manifest in _stage_manifests(study_file.parent):
        for ref in manifest.get("external_runtime_artifacts", []):
            row = dict(ref)
            row["stage"] = stage
            row["manifest_path"] = portable_path(manifest_path, root=root)
            expected.append(row)

    discovered_by_name: dict[str, list[Path]] = {}
    for ref in expected:
        name = Path(str(ref["path"])).name
        if name in discovered_by_name:
            continue
        candidates: list[Path] = []
        for search_root in roots:
            candidates.extend(path for path in search_root.rglob(name) if path.is_file())
        discovered_by_name[name] = sorted(set(path.resolve() for path in candidates))

    planned: list[tuple[dict[str, Any], Path, Path | None, str]] = []
    missing: list[dict[str, Any]] = []
    for ref in expected:
        target = resolve_path(str(ref["path"]), root=root)
        expected_sha = str(ref["sha256"])
        if target.is_file():
            if sha256_file(target) != expected_sha:
                raise ValueError(f"canonical runtime artifact has wrong hash: {target}")
            planned.append((ref, target, None, "already-present"))
            continue
        matches = [
            path
            for path in discovered_by_name.get(target.name, [])
            if sha256_file(path) == expected_sha
        ]
        if not matches:
            missing.append(
                {
                    "stage": ref["stage"],
                    "path": str(ref["path"]),
                    "sha256": expected_sha,
                    "legacy_location_hint": ref.get("legacy_location_hint"),
                }
            )
            continue
        planned.append((ref, target, matches[0], materialize))
    if missing:
        raise ValueError(
            "runtime migration is incomplete; missing content-addressed artifacts: "
            + json.dumps(missing, ensure_ascii=False)
        )

    records: list[dict[str, Any]] = []
    for ref, target, source, action in planned:
        if source is not None:
            target.parent.mkdir(parents=True, exist_ok=True)
            if materialize in {"auto", "hardlink"}:
                try:
                    target.hardlink_to(source)
                    action = "hardlink"
                except OSError:
                    if materialize == "hardlink":
                        raise
                    shutil.copy2(source, target)
                    action = "copy"
            else:
                shutil.copy2(source, target)
                action = "copy"
        records.append(
            {
                "stage": ref["stage"],
                "role": ref["role"],
                "seed": ref["seed"],
                "tick": ref["tick"],
                "path": str(ref["path"]),
                "sha256": ref["sha256"],
                "action": action,
                "verified": sha256_file(target) == ref["sha256"],
            }
        )

    report = {
        "schema": "se-study-runtime-migration-v1",
        "study_id": study["study_id"],
        "materialize": materialize,
        "artifact_count": len(records),
        "all_verified": all(row["verified"] for row in records),
        "artifacts": records,
    }
    report_path = study_file.parent / "frozen" / "runtime_migration.lock.json"
    report_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return report


def migrate_main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Migrate hash-matched legacy runtime artifacts into canonical runs paths."
    )
    parser.add_argument("--study", required=True)
    parser.add_argument("--search-root", action="append", required=True)
    parser.add_argument("--materialize", choices=("auto", "copy", "hardlink"), default="auto")
    parser.add_argument("--workspace-root", default=".")
    args = parser.parse_args(argv)
    report = migrate_runtime_artifacts(
        args.study,
        search_roots=args.search_root,
        workspace=args.workspace_root,
        materialize=args.materialize,
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


def freeze_legacy_main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Freeze a decision-only legacy study result without inventing evidence."
    )
    parser.add_argument("--study", required=True)
    parser.add_argument("--ledger", required=True)
    parser.add_argument("--stage", required=True, choices=tuple(_STAGE_ORDER))
    parser.add_argument("--workspace-root", default=".")
    args = parser.parse_args(argv)
    freeze_legacy_decision(
        study_path=args.study,
        ledger_path=args.ledger,
        stage=args.stage,
        workspace=args.workspace_root,
    )
    return 0

def freeze_main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Freeze one completed study stage.")
    parser.add_argument("--study", required=True)
    parser.add_argument("--stage", required=True, choices=tuple(_STAGE_ORDER))
    parser.add_argument("--source-plan", required=True)
    parser.add_argument("--paired-plan", required=True)
    parser.add_argument("--assessment", required=True)
    parser.add_argument("--decision", required=True)
    parser.add_argument("--results")
    parser.add_argument("--workspace-root", default=".")
    args = parser.parse_args(argv)
    freeze_stage(
        study_path=args.study,
        stage=args.stage,
        source_plan_path=args.source_plan,
        paired_plan_path=args.paired_plan,
        assessment_path=args.assessment,
        decision_path=args.decision,
        results_path=args.results,
        workspace=args.workspace_root,
    )
    return 0


def verify_main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Verify frozen study evidence.")
    parser.add_argument("--study", required=True)
    parser.add_argument("--workspace-root", default=".")
    parser.add_argument("--verify-runtime", action="store_true")
    parser.add_argument("--output")
    args = parser.parse_args(argv)
    report = verify_study(
        args.study,
        workspace=args.workspace_root,
        verify_runtime=args.verify_runtime,
    )
    text = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        path = Path(args.output)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    else:
        print(text, end="")
    return 0 if report["passed"] else 2


__all__ = [
    "CHAIN_SCHEMA",
    "LEGACY_DECISION_SCHEMA",
    "STAGE_SCHEMA",
    "STUDY_SCHEMA",
    "freeze_legacy_decision",
    "freeze_legacy_main",
    "freeze_main",
    "freeze_stage",
    "layout_migrate_main",
    "load_study",
    "migrate_main",
    "migrate_runtime_artifacts",
    "migrate_stage_layout",
    "rebuild_chain_lock",
    "verify_main",
    "verify_study",
]
