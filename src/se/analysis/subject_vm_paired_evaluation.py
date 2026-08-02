"""Shared-checkpoint paired export for Subject VM Stage 3C-6.

This external experiment boundary creates explicit guarded-live and read-only
branch identities, runs them from one trusted checkpoint, and exports completed
Stage-3C-5 windows without scalarization or automatic parameter retention.
"""
from __future__ import annotations

import argparse
from dataclasses import asdict, replace
import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np

from ..checkpointing import config_sha256, read_checkpoint_bundle
from ..runtime.sim import Simulation
from ..subject_vm.config import SUBJECT_VM_STAGE3C5_SCHEMA
from ..subject_vm.evaluation import (
    EVALUATION_STATUS_ACTIVE,
    EVALUATION_STATUS_OBSERVED,
)
from ..subject_vm.evaluation_export import (
    extract_completed_windows,
    pair_completed_windows,
)
from ..subject_vm.live_write import (
    LIVE_WRITE_STATUS_PENDING,
    LIVE_WRITE_STATUS_CONTROL_PENDING,
)

PAIRED_EVALUATION_PLAN_SCHEMA = "se-subject-vm-paired-evaluation-plan-v1"
PAIRED_EVALUATION_BRANCH_SCHEMA = "se-subject-vm-paired-evaluation-branch-v1"
PAIRED_EVALUATION_EXPORT_SCHEMA = "se-subject-vm-paired-evaluation-export-v1"
BRANCH_ROLES = ("guarded-live", "read-only-control")


def _sha256_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _canonical_sha256(payload: Any) -> str:
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _runtime_payload(state: dict[str, Any]) -> dict[str, Any]:
    payload = state.get("simulation", {}).get("subject_vm")
    if not isinstance(payload, dict):
        raise ValueError("source checkpoint does not contain an enabled subject_vm runtime")
    return payload


def _validate_quiescent_source(state: dict[str, Any]) -> None:
    payload = _runtime_payload(state)
    evaluation = payload.get("evaluation_ledger")
    live = payload.get("live_write_ledger")
    if not isinstance(evaluation, dict) or not isinstance(live, dict):
        raise ValueError("source checkpoint lacks Stage-3C-5 evaluation/live-write ledgers")
    eval_arrays = evaluation.get("arrays", {})
    live_arrays = live.get("arrays", {})
    eval_valid = np.asarray(eval_arrays.get("entry_valid"), dtype=bool)
    eval_status = np.asarray(eval_arrays.get("status"), dtype=np.uint8)
    active = eval_valid & (
        (eval_status == EVALUATION_STATUS_ACTIVE)
        | (eval_status == EVALUATION_STATUS_OBSERVED)
    )
    if np.any(active):
        raise ValueError("source checkpoint has active subject_vm evaluation windows")
    live_valid = np.asarray(live_arrays.get("entry_valid"), dtype=bool)
    live_status = np.asarray(live_arrays.get("status"), dtype=np.uint8)
    if np.any(
        live_valid
        & (
            (live_status == LIVE_WRITE_STATUS_PENDING)
            | (live_status == LIVE_WRITE_STATUS_CONTROL_PENDING)
        )
    ):
        raise ValueError(
            "source checkpoint has pending subject_vm live writes or control reservations"
        )
    if np.any(np.asarray(live_arrays.get("row_locked"), dtype=bool)):
        raise ValueError("source checkpoint has locked subject_vm live-write rows")
    if np.any(eval_valid) or np.any(live_valid):
        raise ValueError(
            "source checkpoint must use empty Stage-3C-5 ledgers so branch evidence is post-split only"
        )


def _branch_config(source_cfg: Any, *, role: str, final_tick: int) -> Any:
    if role not in BRANCH_ROLES:
        raise ValueError("unsupported subject_vm paired branch role")
    svm = source_cfg.subject_vm
    live = replace(svm.live_write, enabled=(role == "guarded-live"))
    svm = replace(svm, live_write=live)
    run = replace(
        source_cfg.run,
        ticks=int(final_tick),
        checkpoint_ticks=(),
        full_checkpoint_enabled=False,
    )
    return replace(source_cfg, subject_vm=svm, run=run)


def build_plan(
    source_checkpoint: str | Path, *, horizon_ticks: int,
    finalize_pending_transients_at_export: bool = False,
) -> dict[str, Any]:
    source_path = Path(source_checkpoint).resolve()
    metadata, state = read_checkpoint_bundle(source_path)
    cfg = state["config"]
    svm = getattr(cfg, "subject_vm", None)
    if svm is None or svm.schema != SUBJECT_VM_STAGE3C5_SCHEMA:
        raise ValueError("source checkpoint must use Subject VM Stage 3C-5")
    if not svm.evaluation_enabled or not svm.live_write_configured:
        raise ValueError("source checkpoint must configure evaluation and live-write contracts")
    _validate_quiescent_source(state)
    horizon = int(horizon_ticks)
    minimum = max(
        int(svm.live_write.rollback_after_ticks),
        int(svm.evaluation.control_horizon_ticks),
        int(svm.evaluation.observation_ticks),
    ) + 1
    if horizon < minimum:
        raise ValueError(f"paired evaluation horizon_ticks must be at least {minimum}")
    source_tick = int(metadata["tick"])
    final_tick = source_tick + horizon
    source_identity = {
        "checkpoint_path": str(source_path),
        "checkpoint_file_sha256": _sha256_file(source_path),
        "checkpoint_state_sha256": str(metadata["state_sha256"]),
        "checkpoint_config_sha256": str(metadata["config_sha256"]),
        "checkpoint_tick": source_tick,
    }
    branches = []
    for role in BRANCH_ROLES:
        branch_cfg = _branch_config(cfg, role=role, final_tick=final_tick)
        cfg_sha = config_sha256(branch_cfg)
        branch_basis = {
            "source_checkpoint_state_sha256": source_identity["checkpoint_state_sha256"],
            "role": role,
            "config_sha256": cfg_sha,
            "final_tick": final_tick,
        }
        branches.append(
            {
                "schema": PAIRED_EVALUATION_BRANCH_SCHEMA,
                "role": role,
                "branch_id": _canonical_sha256(branch_basis),
                "config_sha256": cfg_sha,
                "final_tick": final_tick,
                "only_authorized_config_difference": "subject_vm.live_write.enabled",
            }
        )
    payload = {
        "schema": PAIRED_EVALUATION_PLAN_SCHEMA,
        "source": source_identity,
        "horizon_ticks": horizon,
        "final_tick": final_tick,
        "branches": branches,
        "paired_randomness": True,
        "shared_checkpoint_required": True,
        "finalize_pending_transients_at_export": bool(
            finalize_pending_transients_at_export
        ),
        "scalar_score": False,
        "automatic_keep_or_revert_decision": False,
        "causal_effect_authorized_by_plan": False,
    }
    payload["plan_sha256"] = _canonical_sha256(payload)
    return payload


def _validate_plan(plan: dict[str, Any]) -> None:
    if plan.get("schema") != PAIRED_EVALUATION_PLAN_SCHEMA:
        raise ValueError("unsupported subject_vm paired evaluation plan schema")
    recorded = str(plan.get("plan_sha256", ""))
    unsigned = dict(plan)
    unsigned.pop("plan_sha256", None)
    if recorded != _canonical_sha256(unsigned):
        raise ValueError("subject_vm paired evaluation plan checksum mismatch")
    roles = [str(item.get("role")) for item in plan.get("branches", [])]
    if tuple(roles) != BRANCH_ROLES:
        raise ValueError("subject_vm paired evaluation plan branch roles mismatch")


def _set_branch_mode(simulation: Simulation, *, role: str, final_tick: int) -> None:
    cfg = _branch_config(simulation.cfg, role=role, final_tick=final_tick)
    simulation.cfg = cfg
    simulation.entities.cfg = cfg
    simulation.subject_vm.cfg = cfg.subject_vm
    if simulation.subject_vm.live_write_ledger is None:
        raise ValueError("subject_vm paired branch lacks live-write ledger")
    simulation.subject_vm.live_write_ledger.cfg = cfg.subject_vm.live_write
    if simulation.subject_vm.evaluation_ledger is None:
        raise ValueError("subject_vm paired branch lacks evaluation ledger")
    simulation.subject_vm.evaluation_ledger.cfg = cfg.subject_vm.evaluation


def _branch_manifest(plan: dict[str, Any], role: str) -> dict[str, Any]:
    branch = next(item for item in plan["branches"] if item["role"] == role)
    return {
        **branch,
        "plan_sha256": plan["plan_sha256"],
        "source_checkpoint_state_sha256": plan["source"]["checkpoint_state_sha256"],
        "source_checkpoint_file_sha256": plan["source"]["checkpoint_file_sha256"],
    }


def _finalize_pending_transients_at_export(
    simulation: Simulation, *, final_tick: int
) -> dict[str, Any]:
    runtime = simulation.subject_vm
    ledger = runtime.live_write_ledger
    storage = runtime.storage
    if ledger is None or storage is None:
        raise ValueError("paired transient finalization requires live-write storage")
    pending = ledger.entry_valid & ledger._pending_status_mask(ledger.status)
    pending_slots = np.argwhere(pending)
    if pending_slots.size == 0:
        return {
            "schema": "se-subject-vm-paired-transient-finalization-v1",
            "boundary_tick": int(final_tick),
            "pending_before": 0,
            "rolled_back_transactions": 0,
            "released_control_reservations": 0,
            "failed_transactions": 0,
            "new_ticks_executed": 0,
        }
    maximum_due = int(np.max(ledger.rollback_due_tick[pending]))
    rows = np.unique(pending_slots[:, 0]).astype(np.int32)
    control_before = int(
        np.count_nonzero(
            pending & (ledger.status == LIVE_WRITE_STATUS_CONTROL_PENDING)
        )
    )
    usage = ledger.rollback_due(storage, rows=rows, tick=maximum_due)
    remaining = ledger.entry_valid & ledger._pending_status_mask(ledger.status)
    record = {
        "schema": "se-subject-vm-paired-transient-finalization-v1",
        "boundary_tick": int(final_tick),
        "maximum_recorded_due_tick": maximum_due,
        "pending_before": int(pending_slots.shape[0]),
        "pending_after": int(np.count_nonzero(remaining)),
        "rolled_back_transactions": int(usage.rolled_back_transactions),
        "released_control_reservations": control_before,
        "failed_transactions": int(usage.failed_transactions),
        "new_ticks_executed": 0,
        "evidence_from_finalized_incomplete_windows": False,
    }
    if record["pending_after"] or record["failed_transactions"]:
        raise ValueError("paired transient finalization failed to restore quiescence")
    simulation.checkpoint_lineage.append(record)
    return record


def run_plan(
    plan: dict[str, Any], *, source_checkpoint: str | Path, output_dir: str | Path,
    backend: str = "auto",
) -> dict[str, Any]:
    _validate_plan(plan)
    source = Path(source_checkpoint).resolve()
    if _sha256_file(source) != plan["source"]["checkpoint_file_sha256"]:
        raise ValueError("source checkpoint file hash does not match paired plan")
    metadata, state = read_checkpoint_bundle(source)
    if str(metadata["state_sha256"]) != plan["source"]["checkpoint_state_sha256"]:
        raise ValueError("source checkpoint state hash does not match paired plan")
    _validate_quiescent_source(state)
    root = Path(output_dir)
    control_dir = root / "read_only_control"
    live_dir = root / "guarded_live"
    root.mkdir(parents=True, exist_ok=True)
    control = Simulation.from_checkpoint(
        source, control_dir, backend=backend, until_tick=int(plan["final_tick"])
    )
    _set_branch_mode(control, role="read-only-control", final_tick=int(plan["final_tick"]))
    live = control.clone(live_dir)
    _set_branch_mode(live, role="guarded-live", final_tick=int(plan["final_tick"]))
    for role, sim, directory in (
        ("read-only-control", control, control_dir),
        ("guarded-live", live, live_dir),
    ):
        manifest = _branch_manifest(plan, role)
        if config_sha256(sim.cfg) != manifest["config_sha256"]:
            raise ValueError("subject_vm paired branch configuration identity mismatch")
        sim.checkpoint_lineage.append(
            {
                "schema": PAIRED_EVALUATION_BRANCH_SCHEMA,
                "branch_id": manifest["branch_id"],
                "branch_role": role,
                "source_checkpoint_state_sha256": manifest[
                    "source_checkpoint_state_sha256"
                ],
                "paired_evaluation_plan_sha256": manifest["plan_sha256"],
            }
        )
        directory.mkdir(parents=True, exist_ok=True)
        (directory / "branch_identity.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        resolved = json.dumps(asdict(sim.cfg), ensure_ascii=False, indent=2)
        (directory / "config.json").write_text(resolved, encoding="utf-8")
        (directory / "resolved_config.json").write_text(resolved, encoding="utf-8")
        sim._write_run_manifest(sim.requested_backend)
    control.run(until_tick=int(plan["final_tick"]))
    live.run(until_tick=int(plan["final_tick"]))
    finalization = None
    if bool(plan.get("finalize_pending_transients_at_export", False)):
        finalization = {
            "read-only-control": _finalize_pending_transients_at_export(
                control, final_tick=int(plan["final_tick"])
            ),
            "guarded-live": _finalize_pending_transients_at_export(
                live, final_tick=int(plan["final_tick"])
            ),
        }
    control_checkpoint = control.save_full_checkpoint(control_dir / "final.sechk")
    live_checkpoint = live.save_full_checkpoint(live_dir / "final.sechk")
    export = export_pair(
        plan,
        guarded_live_checkpoint=live_checkpoint,
        read_only_control_checkpoint=control_checkpoint,
    )
    export_path = root / "paired_evaluation_export.json"
    export_path.write_text(json.dumps(export, ensure_ascii=False, indent=2), encoding="utf-8")
    return {
        "plan_sha256": plan["plan_sha256"],
        "guarded_live_checkpoint": str(live_checkpoint),
        "read_only_control_checkpoint": str(control_checkpoint),
        "export": str(export_path),
        "paired_window_count": export["window_evidence"]["paired_window_count"],
        "transient_finalization": finalization,
    }


def _checkpoint_branch_record(
    checkpoint: str | Path, *, expected_role: str, plan: dict[str, Any]
) -> tuple[dict[str, Any], dict[str, Any]]:
    path = Path(checkpoint).resolve()
    metadata, state = read_checkpoint_bundle(path)
    expected = next(item for item in plan["branches"] if item["role"] == expected_role)
    if str(metadata["config_sha256"]) != expected["config_sha256"]:
        raise ValueError(f"{expected_role} checkpoint configuration identity mismatch")
    lineage = state.get("checkpoint_lineage", [])
    matches = [
        item for item in lineage
        if item.get("schema") == PAIRED_EVALUATION_BRANCH_SCHEMA
        and item.get("branch_id") == expected["branch_id"]
        and item.get("branch_role") == expected_role
        and item.get("paired_evaluation_plan_sha256") == plan["plan_sha256"]
    ]
    if len(matches) != 1:
        raise ValueError(f"{expected_role} checkpoint branch identity is missing or ambiguous")
    if int(metadata["tick"]) != int(plan["final_tick"]):
        raise ValueError(f"{expected_role} checkpoint final tick mismatch")
    return metadata, state


def export_pair(
    plan: dict[str, Any], *, guarded_live_checkpoint: str | Path,
    read_only_control_checkpoint: str | Path,
) -> dict[str, Any]:
    _validate_plan(plan)
    live_meta, live_state = _checkpoint_branch_record(
        guarded_live_checkpoint, expected_role="guarded-live", plan=plan
    )
    control_meta, control_state = _checkpoint_branch_record(
        read_only_control_checkpoint, expected_role="read-only-control", plan=plan
    )
    live_records = extract_completed_windows(
        _runtime_payload(live_state), branch_role="guarded-live"
    )
    control_records = extract_completed_windows(
        _runtime_payload(control_state), branch_role="read-only-control"
    )
    evidence = pair_completed_windows(live_records, control_records)
    payload = {
        "schema": PAIRED_EVALUATION_EXPORT_SCHEMA,
        "plan_sha256": plan["plan_sha256"],
        "source": plan["source"],
        "branches": {
            "guarded-live": {
                "checkpoint": str(Path(guarded_live_checkpoint).resolve()),
                "checkpoint_file_sha256": _sha256_file(guarded_live_checkpoint),
                "checkpoint_state_sha256": str(live_meta["state_sha256"]),
                "branch_id": plan["branches"][0]["branch_id"],
            },
            "read-only-control": {
                "checkpoint": str(Path(read_only_control_checkpoint).resolve()),
                "checkpoint_file_sha256": _sha256_file(read_only_control_checkpoint),
                "checkpoint_state_sha256": str(control_meta["state_sha256"]),
                "branch_id": plan["branches"][1]["branch_id"],
            },
        },
        "window_evidence": evidence,
        "shared_checkpoint_verified": True,
        "branch_identity_verified": True,
        "componentwise_differences_only": True,
        "scalar_score": False,
        "automatic_keep_or_revert_decision": False,
        "causal_effect_authorized": False,
    }
    payload["export_sha256"] = _canonical_sha256(payload)
    return payload


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Plan, run, or export Subject VM Stage-3C-6 paired evaluation."
    )
    sub = parser.add_subparsers(dest="command", required=True)
    plan = sub.add_parser("plan")
    plan.add_argument("--source-checkpoint", required=True)
    plan.add_argument("--horizon-ticks", required=True, type=int)
    plan.add_argument("--output", required=True)
    run = sub.add_parser("run")
    run.add_argument("--plan", required=True)
    run.add_argument("--source-checkpoint", required=True)
    run.add_argument("--output", required=True)
    run.add_argument("--backend", choices=("cpu", "gpu", "auto"), default="auto")
    export = sub.add_parser("export")
    export.add_argument("--plan", required=True)
    export.add_argument("--guarded-live-checkpoint", required=True)
    export.add_argument("--read-only-control-checkpoint", required=True)
    export.add_argument("--output", required=True)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    if args.command == "plan":
        payload = build_plan(args.source_checkpoint, horizon_ticks=args.horizon_ticks)
    else:
        plan = json.loads(Path(args.plan).read_text(encoding="utf-8"))
        if args.command == "run":
            payload = run_plan(
                plan,
                source_checkpoint=args.source_checkpoint,
                output_dir=args.output,
                backend=args.backend,
            )
        else:
            payload = export_pair(
                plan,
                guarded_live_checkpoint=args.guarded_live_checkpoint,
                read_only_control_checkpoint=args.read_only_control_checkpoint,
            )
    output = Path(args.output)
    if args.command == "run":
        output.mkdir(parents=True, exist_ok=True)
        destination = output / "paired_evaluation_run.json"
    else:
        output.parent.mkdir(parents=True, exist_ok=True)
        destination = output
    destination.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
