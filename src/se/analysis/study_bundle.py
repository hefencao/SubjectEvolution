"""Freeze and verify portable study evidence across project versions.

A study bundle separates immutable scientific evidence from mutable runtime
locations.  Small plans, assessments, decisions and summaries are copied into
``studies/<study>/frozen``.  Large checkpoints remain in ``runs`` and are
referenced by their recorded content hashes and logical roles.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import shutil
import tempfile
from typing import Any, Sequence
import zipfile

from .. import __version__
from ..workspace import artifact_ref, portable_path, resolve_path, sha256_file, workspace_root
from .candidate_ledger import candidate_signature, canonical_sha, load_ledger
from .exploration_protocol import _canonical_config
from ..experiments.paired_exploration import load_candidate_spec

STUDY_SCHEMA = "se-study-bundle-v1"
STAGE_SCHEMA = "se-study-stage-freeze-v2"
CHAIN_SCHEMA = "se-study-chain-lock-v1"
LEGACY_DECISION_SCHEMA = "se-study-legacy-decision-lock-v1"
RESULT_BUNDLE_SCHEMA = "se-study-result-bundle-v1"
_MAX_RESULT_BUNDLE_FILES = 4096
_MAX_RESULT_BUNDLE_BYTES = 128 * 1024 * 1024
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



def _zip_member_is_symlink(info: zipfile.ZipInfo) -> bool:
    mode = (info.external_attr >> 16) & 0o170000
    return mode == 0o120000


def _safe_extract_zip(archive: Path, destination: Path) -> None:
    """Extract a result archive without path traversal or link materialization."""

    with zipfile.ZipFile(archive) as bundle:
        members = bundle.infolist()
        if not members:
            raise ValueError("study result archive is empty")
        if len(members) > _MAX_RESULT_BUNDLE_FILES:
            raise ValueError("study result archive contains too many members")
        if sum(info.file_size for info in members) > _MAX_RESULT_BUNDLE_BYTES:
            raise ValueError("study result archive exceeds the compact-result size limit")
        normalized_names: set[str] = set()
        for info in members:
            name = info.filename.replace("\\", "/")
            path = Path(name)
            if path.is_absolute() or ".." in path.parts:
                raise ValueError(f"unsafe study result archive member: {info.filename!r}")
            if name in normalized_names:
                raise ValueError(f"duplicate study result archive member: {info.filename!r}")
            normalized_names.add(name)
            if info.flag_bits & 0x1:
                raise ValueError("encrypted study result archives are not supported")
            if _zip_member_is_symlink(info):
                raise ValueError(
                    f"study result archive cannot contain symlinks: {info.filename!r}"
                )
        bundle.extractall(destination)


def _locate_result_bundle_root(path: Path) -> tuple[Path, bool]:
    """Return the directory containing ``frozen`` or legacy frozen evidence."""

    if (path / "bundle.json").is_file() and (path / "frozen/chain.lock.json").is_file():
        return path, False
    if (path / "frozen/chain.lock.json").is_file():
        return path, False
    if (path / "chain.lock.json").is_file():
        return path, True
    candidates = sorted(
        parent
        for parent in path.rglob("chain.lock.json")
        if parent.is_file()
        for parent in [parent.parent]
    )
    if len(candidates) != 1:
        raise ValueError(
            "study result bundle must contain exactly one frozen/chain.lock.json "
            "or legacy chain.lock.json"
        )
    candidate = candidates[0]
    if candidate.name == "frozen":
        return candidate.parent, False
    return candidate, True


def _study_state_from_chain(
    study: dict[str, Any], chain: dict[str, Any]
) -> dict[str, Any]:
    """Return the study definition with planning state derived from frozen evidence."""

    updated = dict(study)
    stages = chain.get("stages", [])
    if not isinstance(stages, list) or not stages:
        return updated
    latest = dict(stages[-1])
    stage = str(latest.get("stage", ""))
    decision = str(latest.get("decision", ""))
    terminal = bool(latest.get("terminal", False))
    updated["latest_stage"] = stage
    updated["latest_decision"] = decision
    updated["latest_recommendation"] = latest.get("recommendation")
    updated["selection_claim_allowed"] = bool(
        chain.get("selection_claim_allowed", False)
    )
    if terminal:
        updated["current_state"] = decision or f"{stage}-terminal"
        updated["next_authorized_stage"] = None
        updated["terminal_stage"] = stage
    else:
        updated["current_state"] = (
            f"{stage}-promoted" if decision == "promote" else f"{stage}-{decision}"
        )
        updated["next_authorized_stage"] = {
            "smoke": "screen",
            "screen": "replication",
            "replication": "confirmation",
        }.get(stage)
        updated.pop("terminal_stage", None)
    return updated


def _bundle_file_records(root: Path, relative_paths: Sequence[Path]) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for relative in sorted(relative_paths, key=lambda value: value.as_posix()):
        path = root / relative
        if not path.is_file():
            raise ValueError(f"study result bundle input is missing: {path}")
        records.append(
            {
                "path": relative.as_posix(),
                "sha256": sha256_file(path),
                "size": path.stat().st_size,
            }
        )
    return records


def _write_deterministic_zip(archive: Path, root: Path, relative_paths: Sequence[Path]) -> None:
    archive.parent.mkdir(parents=True, exist_ok=True)
    temporary = archive.with_suffix(archive.suffix + ".tmp")
    if temporary.exists():
        temporary.unlink()
    with zipfile.ZipFile(temporary, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as bundle:
        for relative in sorted(relative_paths, key=lambda value: value.as_posix()):
            path = root / relative
            info = zipfile.ZipInfo(
                relative.as_posix(), date_time=(1980, 1, 1, 0, 0, 0)
            )
            info.compress_type = zipfile.ZIP_DEFLATED
            mode = 0o100755 if relative.parts[0] == "commands" else 0o100644
            info.external_attr = mode << 16
            bundle.writestr(info, path.read_bytes())
    temporary.replace(archive)


def export_study_result(
    study_path: str | Path,
    *,
    output: str | Path,
    workspace: str | Path | None = None,
) -> dict[str, Any]:
    """Export a deterministic, self-describing compact study result bundle.

    Raw runtime and checkpoints remain external. Their canonical locations and
    hashes are retained in stage locks, so the compact bundle is sufficient for
    decision import and interpretation but not for checkpoint replay.
    """

    root = workspace_root(workspace)
    study_file = resolve_path(study_path, root=root)
    study = load_study(study_file)
    verification = verify_study(study_file, workspace=root)
    if not verification["passed"]:
        raise ValueError(
            "cannot export an invalid study: "
            + json.dumps(verification["failures"], ensure_ascii=False)
        )
    study_dir = study_file.parent
    chain = _read_json(study_dir / "frozen/chain.lock.json")
    derived_study = _study_state_from_chain(study, chain)
    if study != derived_study:
        raise ValueError(
            "cannot export a study whose planning state is stale relative to frozen evidence"
        )
    protocol_files = sorted(
        path for path in (study_dir / "protocol").rglob("*") if path.is_file()
    )
    frozen_files = sorted(
        path for path in (study_dir / "frozen").rglob("*") if path.is_file()
    )
    command_files = sorted(
        path for path in (study_dir / "commands").rglob("*") if path.is_file()
    )
    document_paths = [
        Path(name)
        for name in ("study.json", "README.md", "DESIGN.md", "RUN_CHAIN.md")
        if (study_dir / name).is_file()
    ]
    payload_paths = [
        *document_paths,
        *(Path("protocol") / path.relative_to(study_dir / "protocol") for path in protocol_files),
        *(Path("commands") / path.relative_to(study_dir / "commands") for path in command_files),
        *(Path("frozen") / path.relative_to(study_dir / "frozen") for path in frozen_files),
    ]
    with tempfile.TemporaryDirectory(prefix="se-study-result-export-", dir=root) as temp_name:
        temp = Path(temp_name)
        for relative in payload_paths:
            source = study_dir / relative
            target = temp / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
        records = _bundle_file_records(temp, payload_paths)
        manifest = {
            "schema": RESULT_BUNDLE_SCHEMA,
            "producer_version": __version__,
            "study_id": study["study_id"],
            "candidate_id": study["candidate_id"],
            "candidate_signature_sha256": chain.get("candidate_signature_sha256"),
            "chain_sha256": sha256_file(study_dir / "frozen/chain.lock.json"),
            "latest_stage": chain.get("latest_stage"),
            "latest_recommendation": chain.get("latest_recommendation"),
            "selection_claim_allowed": bool(chain.get("selection_claim_allowed", False)),
            "frozen_stage_count": len(chain.get("stages", [])),
            "external_runtime_artifact_count": sum(
                len(_read_json(path).get("external_runtime_artifacts", []))
                for path in (study_dir / "frozen").glob("*/stage.lock.json")
            ),
            "raw_runtime_included": False,
            "design_and_runbook_included": True,
            "sufficient_for_decision_import": True,
            "sufficient_for_checkpoint_replay": False,
            "files": records,
        }
        (temp / "bundle.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        archive_paths = [Path("bundle.json"), *payload_paths]
        output_path = resolve_path(output, root=root)
        _write_deterministic_zip(output_path, temp, archive_paths)
    try:
        output_display = portable_path(output_path, root=root)
    except ValueError:
        output_display = output_path.as_posix()
    return {
        "schema": "se-study-result-export-v1",
        "study_id": study["study_id"],
        "candidate_id": study["candidate_id"],
        "output": output_display,
        "sha256": sha256_file(output_path),
        "latest_stage": chain.get("latest_stage"),
        "raw_runtime_included": False,
        "design_and_runbook_included": True,
        "sufficient_for_decision_import": True,
        "sufficient_for_checkpoint_replay": False,
    }


def _validate_result_manifest(bundle_root: Path) -> dict[str, Any] | None:
    manifest_path = bundle_root / "bundle.json"
    if not manifest_path.is_file():
        return None
    manifest = _read_json(manifest_path)
    if manifest.get("schema") != RESULT_BUNDLE_SCHEMA:
        raise ValueError(f"unsupported study result bundle schema: {manifest.get('schema')!r}")
    files = manifest.get("files")
    if not isinstance(files, list) or not files:
        raise ValueError("study result bundle manifest has no files")
    observed: set[str] = set()
    for record in files:
        if not isinstance(record, dict):
            raise ValueError("study result bundle file record must be an object")
        relative = Path(str(record.get("path", "")))
        if relative.is_absolute() or ".." in relative.parts or not relative.parts:
            raise ValueError(f"unsafe study result manifest path: {relative}")
        path = bundle_root / relative
        if not path.is_file():
            raise ValueError(f"study result bundle file is missing: {relative.as_posix()}")
        if path.stat().st_size != int(record.get("size", -1)):
            raise ValueError(f"study result bundle size mismatch: {relative.as_posix()}")
        if sha256_file(path) != str(record.get("sha256", "")):
            raise ValueError(f"study result bundle hash mismatch: {relative.as_posix()}")
        observed.add(relative.as_posix())
    allowed = observed | {"bundle.json"}
    actual = {
        path.relative_to(bundle_root).as_posix()
        for path in bundle_root.rglob("*")
        if path.is_file()
    }
    extras = sorted(actual - allowed)
    if extras:
        raise ValueError(f"study result bundle contains unmanifested files: {extras!r}")
    return manifest


def _copy_study_definition_for_validation(
    study_file: Path, *, root: Path, temporary_root: Path
) -> Path:
    relative_study_dir = study_file.parent.relative_to(root)
    temporary_study_dir = temporary_root / relative_study_dir
    shutil.copytree(
        study_file.parent,
        temporary_study_dir,
        ignore=shutil.ignore_patterns("frozen", "RUN_CHAIN.md"),
    )
    decision_dir = root / "protocols/decisions"
    if decision_dir.is_dir():
        target = temporary_root / "protocols/decisions"
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(decision_dir, target)
    return temporary_study_dir / study_file.name


def import_study_result(
    study_path: str | Path,
    *,
    bundle: str | Path,
    workspace: str | Path | None = None,
    check_only: bool = False,
) -> dict[str, Any]:
    """Atomically import a compact result bundle into an existing study.

    Existing frozen stages are immutable: the imported bundle must retain them
    byte-for-byte and may only append later stages. The run-chain summary is
    deterministically regenerated from validated frozen evidence.
    """

    root = workspace_root(workspace)
    study_file = resolve_path(study_path, root=root)
    study = load_study(study_file)
    bundle_path = resolve_path(bundle, root=root)
    if not bundle_path.exists():
        raise ValueError(f"study result bundle does not exist: {bundle_path}")
    existing_manifests = {
        stage: sha256_file(path)
        for stage, path, _ in _stage_manifests(study_file.parent)
    }
    with tempfile.TemporaryDirectory(prefix="se-study-result-import-", dir=root) as temp_name:
        temp = Path(temp_name)
        extracted = temp / "input"
        extracted.mkdir()
        if bundle_path.is_dir():
            shutil.copytree(bundle_path, extracted / "bundle", dirs_exist_ok=True)
        elif zipfile.is_zipfile(bundle_path):
            _safe_extract_zip(bundle_path, extracted)
        else:
            raise ValueError("study result bundle must be a directory or zip archive")
        bundle_root, frozen_at_root = _locate_result_bundle_root(extracted)
        manifest = _validate_result_manifest(bundle_root)
        legacy_frozen_only = manifest is None
        frozen_source = bundle_root if frozen_at_root else bundle_root / "frozen"
        chain = _read_json(frozen_source / "chain.lock.json")
        if chain.get("schema") != CHAIN_SCHEMA:
            raise ValueError("study result bundle has an unsupported chain lock")
        if chain.get("study_id") != study["study_id"]:
            raise ValueError("study result bundle study_id does not match target study")
        if chain.get("candidate_id") != study["candidate_id"]:
            raise ValueError("study result bundle candidate_id does not match target study")
        if manifest is not None:
            if manifest.get("study_id") != study["study_id"]:
                raise ValueError("study result manifest study_id does not match target study")
            if manifest.get("candidate_id") != study["candidate_id"]:
                raise ValueError("study result manifest candidate_id does not match target study")
            if manifest.get("candidate_signature_sha256") != chain.get(
                "candidate_signature_sha256"
            ):
                raise ValueError("study result manifest candidate signature mismatch")
            if manifest.get("chain_sha256") != sha256_file(
                frozen_source / "chain.lock.json"
            ):
                raise ValueError("study result manifest chain hash mismatch")
            bundled_study = _read_json(bundle_root / "study.json")
            if bundled_study.get("study_id") != study["study_id"]:
                raise ValueError("bundled study definition does not match target study")
            if bundled_study != _study_state_from_chain(bundled_study, chain):
                raise ValueError(
                    "bundled study planning state is stale relative to frozen evidence"
                )
            bundled_candidate = bundle_root / "protocol/candidate.json"
            target_candidate = _candidate_path(study_file, study, root)
            if sha256_file(bundled_candidate) != sha256_file(target_candidate):
                raise ValueError("bundled candidate specification does not match target study")
            for protocol in sorted((bundle_root / "protocol").glob("*.json")):
                target = study_file.parent / "protocol" / protocol.name
                if not target.is_file() or sha256_file(protocol) != sha256_file(target):
                    raise ValueError(
                        f"bundled protocol does not match target study: {protocol.name}"
                    )
        imported_manifests = {
            stage: sha256_file(path)
            for stage, path, _ in _stage_manifests(bundle_root)
        }
        # A chain placed directly at the archive root has no enclosing study directory.
        if frozen_at_root:
            imported_manifests = {
                path.parent.name: sha256_file(path)
                for path in frozen_source.glob("*/stage.lock.json")
            }
        for stage, expected_sha in existing_manifests.items():
            if imported_manifests.get(stage) != expected_sha:
                raise ValueError(
                    f"study result import would rewrite or remove existing frozen stage: {stage}"
                )
        validation_root = temp / "workspace"
        temporary_study = _copy_study_definition_for_validation(
            study_file, root=root, temporary_root=validation_root
        )
        temporary_frozen = temporary_study.parent / "frozen"
        shutil.copytree(frozen_source, temporary_frozen)
        expected_chain = _build_chain_lock(temporary_study, root=validation_root)
        if chain != expected_chain:
            raise ValueError("study result bundle chain lock does not match stage evidence")
        temporary_study_payload = _study_state_from_chain(
            load_study(temporary_study), expected_chain
        )
        temporary_study.write_text(
            json.dumps(temporary_study_payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        expected_run_chain = _render_run_chain_text(
            temporary_study_payload, expected_chain
        )
        (temporary_study.parent / "RUN_CHAIN.md").write_text(
            expected_run_chain, encoding="utf-8"
        )
        verification = verify_study(temporary_study, workspace=validation_root)
        if not verification["passed"]:
            raise ValueError(
                "study result bundle verification failed: "
                + json.dumps(verification["failures"], ensure_ascii=False)
            )
        if check_only:
            return {
                "schema": "se-study-result-import-check-v1",
                "study_id": study["study_id"],
                "candidate_id": study["candidate_id"],
                "legacy_frozen_only": legacy_frozen_only,
                "previous_stage_count": len(existing_manifests),
                "imported_stage_count": len(imported_manifests),
                "latest_stage": expected_chain.get("latest_stage"),
                "derived_current_state": temporary_study_payload.get("current_state"),
                "would_modify_study": (
                    len(imported_manifests) != len(existing_manifests)
                    or study != temporary_study_payload
                ),
                "runtime_verified": False,
                "sufficient_for_decision_import": True,
                "sufficient_for_checkpoint_replay": False,
            }
        incoming = study_file.parent / f".frozen.import-{os.getpid()}"
        backup = study_file.parent / f".frozen.backup-{os.getpid()}"
        run_chain_temp = study_file.parent / f".RUN_CHAIN.import-{os.getpid()}.md"
        run_chain_backup = study_file.parent / f".RUN_CHAIN.backup-{os.getpid()}.md"
        study_temp = study_file.parent / f".study.import-{os.getpid()}.json"
        study_backup = study_file.parent / f".study.backup-{os.getpid()}.json"
        for path in (incoming, backup):
            if path.exists():
                shutil.rmtree(path)
        for path in (run_chain_temp, run_chain_backup, study_temp, study_backup):
            if path.exists():
                path.unlink()
        shutil.copytree(temporary_frozen, incoming)
        run_chain_temp.write_text(expected_run_chain, encoding="utf-8")
        study_temp.write_text(
            json.dumps(temporary_study_payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        destination = study_file.parent / "frozen"
        run_chain = study_file.parent / "RUN_CHAIN.md"
        if run_chain.is_file():
            shutil.copy2(run_chain, run_chain_backup)
        shutil.copy2(study_file, study_backup)
        try:
            if destination.exists():
                destination.replace(backup)
            incoming.replace(destination)
            run_chain_temp.replace(run_chain)
            study_temp.replace(study_file)
        except Exception:
            if destination.exists():
                shutil.rmtree(destination)
            if backup.exists():
                backup.replace(destination)
            if run_chain_backup.is_file():
                run_chain_backup.replace(run_chain)
            elif run_chain.exists():
                run_chain.unlink()
            if study_backup.is_file():
                study_backup.replace(study_file)
            raise
        finally:
            if incoming.exists():
                shutil.rmtree(incoming)
            for path in (run_chain_temp, study_temp):
                if path.exists():
                    path.unlink()
        if backup.exists():
            shutil.rmtree(backup)
        for path in (run_chain_backup, study_backup):
            if path.exists():
                path.unlink()
    final_report = verify_study(study_file, workspace=root)
    if not final_report["passed"]:
        raise RuntimeError("imported study failed post-commit verification")
    return {
        "schema": "se-study-result-import-v1",
        "study_id": study["study_id"],
        "candidate_id": study["candidate_id"],
        "legacy_frozen_only": legacy_frozen_only,
        "previous_stage_count": len(existing_manifests),
        "imported_stage_count": final_report["frozen_stage_count"],
        "latest_stage": final_report["latest_stage"],
        "derived_current_state": load_study(study_file).get("current_state"),
        "runtime_verified": False,
        "sufficient_for_decision_import": True,
        "sufficient_for_checkpoint_replay": False,
    }


def export_main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Export a deterministic compact study result bundle.")
    parser.add_argument("--study", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--workspace-root", default=".")
    args = parser.parse_args(argv)
    report = export_study_result(
        args.study, output=args.output, workspace=args.workspace_root
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


def import_main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Atomically import a compact study result bundle.")
    parser.add_argument("--study", required=True)
    parser.add_argument("--bundle", required=True)
    parser.add_argument("--check-only", action="store_true")
    parser.add_argument("--workspace-root", default=".")
    args = parser.parse_args(argv)
    report = import_study_result(
        args.study,
        bundle=args.bundle,
        workspace=args.workspace_root,
        check_only=args.check_only,
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0



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
    "RESULT_BUNDLE_SCHEMA",
    "STAGE_SCHEMA",
    "STUDY_SCHEMA",
    "freeze_legacy_decision",
    "freeze_legacy_main",
    "freeze_main",
    "export_main",
    "export_study_result",
    "freeze_stage",
    "import_main",
    "import_study_result",
    "layout_migrate_main",
    "load_study",
    "migrate_main",
    "migrate_runtime_artifacts",
    "migrate_stage_layout",
    "rebuild_chain_lock",
    "verify_main",
    "verify_study",
]
