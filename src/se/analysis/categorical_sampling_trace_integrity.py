"""语义中立 categorical sampling trace 的完整性审计。

该审计比较 trace 关闭/开启的同 seed fresh run 与同 source checkpoint
paired branches。它只验证观测工具不改变 action、RNG、checkpoint state 或
branch identity，不形成任何科学结果。
"""
from __future__ import annotations

import argparse
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import shutil
from typing import Any

import numpy as np

from .. import __version__
from ..analysis.subject_vm_paired_evaluation import build_plan, run_plan
from ..cfg import load_config
from ..checkpointing import read_checkpoint_bundle
from ..random_api import RandomContext, Stream, keys
from ..runtime.sim import Simulation

CATEGORICAL_SAMPLING_TRACE_INTEGRITY_SCHEMA = (
    "se-categorical-sampling-trace-integrity-v1"
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _canonical_sha256(payload: dict[str, Any]) -> str:
    return hashlib.sha256(
        json.dumps(
            payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
    ).hexdigest()


def _close_source(simulation: Simulation) -> None:
    simulation.metrics.close()
    simulation.evolution_progress.close()
    simulation.knowledge.close()
    if simulation._categorical_sampling_trace_writer is not None:
        simulation._categorical_sampling_trace_summary = (
            simulation._categorical_sampling_trace_writer.close()
        )


def _small_config(path: str):
    base = load_config(path)
    return replace(
        base,
        world=replace(base.world, initial_entities=16, max_entities=32),
        run=replace(
            base.run,
            ticks=3,
            metrics_period=99,
            checkpoint_period=99,
            checkpoint_ticks=(),
            full_checkpoint_enabled=False,
        ),
    )


def _validate_trace(manifest_path: str | Path) -> dict[str, Any]:
    manifest_file = Path(manifest_path).resolve()
    manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
    recorded_manifest_sha = str(manifest["manifest_sha256"])
    unsigned = dict(manifest)
    unsigned.pop("manifest_sha256", None)
    if recorded_manifest_sha != _canonical_sha256(unsigned):
        raise ValueError("categorical trace manifest checksum mismatch")
    trace_path = Path(manifest["trace_path"])
    if not trace_path.is_file():
        trace_path = manifest_file.parent / trace_path.name
    if _sha256(trace_path) != manifest["trace_sha256"]:
        raise ValueError("categorical trace JSONL checksum mismatch")

    rows = [
        json.loads(line)
        for line in trace_path.read_text(encoding="utf-8").splitlines()
    ]
    if not rows or rows[0].get("record_type") != "header":
        raise ValueError("categorical trace header is missing")
    events = rows[1:]
    if len(events) != int(manifest["event_count"]):
        raise ValueError("categorical trace event count mismatch")

    for event in events:
        probabilities = np.asarray(event["probabilities"], dtype=np.float64)
        cumulative = np.asarray(
            event["cumulative_probabilities"], dtype=np.float64
        )
        mask = np.asarray(event["action_mask"], dtype=bool)
        if not np.isclose(probabilities.sum(), 1.0, rtol=0.0, atol=1e-12):
            raise ValueError("categorical probabilities do not sum to one")
        if np.any(probabilities[~mask] != 0.0):
            raise ValueError("masked action has nonzero probability")
        if not np.allclose(
            cumulative, np.cumsum(probabilities), rtol=0.0, atol=1e-15
        ):
            raise ValueError("categorical CDF does not match probabilities")
        draw = float(event["uniform_draw"])
        action = int(np.count_nonzero(cumulative < draw))
        if action != int(event["action_id"]):
            raise ValueError("categorical draw does not reconstruct sampled action")
        if not (
            float(event["selected_cdf_lower"])
            <= draw
            < float(event["selected_cdf_upper"])
        ):
            raise ValueError("draw is outside the selected CDF interval")
        context = event["random_context"]
        expected_key = keys(
            RandomContext(
                int(context["run_seed"]),
                int(context["tick"]),
                int(context["phase"]),
                Stream(int(context["stream"])),
            ),
            np.asarray([event["entity_id"]], dtype=np.uint64),
            int(event["draw_index"]),
        )[0]
        if int(expected_key) != int(event["random_key_uint64"]):
            raise ValueError("categorical trace random key cannot be reconstructed")

    bytes_per_event = (
        float(trace_path.stat().st_size) / len(events) if events else 0.0
    )
    return {
        "manifest": str(manifest_file),
        "manifest_sha256": recorded_manifest_sha,
        "trace": str(trace_path.resolve()),
        "trace_sha256": str(manifest["trace_sha256"]),
        "event_count": len(events),
        "first_tick": manifest["first_tick"],
        "last_tick": manifest["last_tick"],
        "bytes_per_event": bytes_per_event,
        "rng_keys_reconstructed": True,
        "actions_reconstructed": True,
        "cdf_intervals_verified": True,
    }


def verify_categorical_sampling_trace(
    output_dir: str | Path, *, overwrite: bool = False
) -> dict[str, Any]:
    root = Path(output_dir).resolve()
    if root.exists():
        if not overwrite:
            raise FileExistsError(root)
        shutil.rmtree(root)
    root.mkdir(parents=True)

    fresh_actions_equal = True
    fresh_probabilities_equal = True
    baseline = Simulation(_small_config("configs/mvp_small.json"), root / "fresh/off", backend="cpu")
    traced = Simulation(_small_config("configs/mvp_small.json"), root / "fresh/on", backend="cpu")
    traced.enable_categorical_sampling_trace(
        metadata={"audit_role": "fresh-run-trace-on"}
    )
    try:
        for _ in range(3):
            baseline.step()
            traced.step()
            fresh_actions_equal &= np.array_equal(
                baseline.last_policy_decision.action,
                traced.last_policy_decision.action,
            )
            fresh_probabilities_equal &= np.array_equal(
                baseline.last_policy_decision.probability,
                traced.last_policy_decision.probability,
            )
        baseline_checkpoint = baseline.save_full_checkpoint(
            root / "fresh/off/final.sechk"
        )
        traced_checkpoint = traced.save_full_checkpoint(
            root / "fresh/on/final.sechk"
        )
    finally:
        _close_source(baseline)
        _close_source(traced)
    baseline_meta, _ = read_checkpoint_bundle(baseline_checkpoint)
    traced_meta, _ = read_checkpoint_bundle(traced_checkpoint)
    fresh_trace = _validate_trace(
        root / "fresh/on/categorical_sampling_trace_manifest.json"
    )

    source_cfg = _small_config(
        "configs/mvp_short_subject_vm_stage3c25_winner_basin_audit.json"
    )
    source_simulation = Simulation(source_cfg, root / "paired/source", backend="cpu")
    try:
        source_checkpoint = source_simulation.save_full_checkpoint(
            root / "paired/source.sechk"
        )
    finally:
        _close_source(source_simulation)
    plan = build_plan(source_checkpoint, horizon_ticks=3)
    paired_off = run_plan(
        plan,
        source_checkpoint=source_checkpoint,
        output_dir=root / "paired/off",
        backend="cpu",
    )
    paired_on = run_plan(
        plan,
        source_checkpoint=source_checkpoint,
        output_dir=root / "paired/on",
        backend="cpu",
        categorical_sampling_trace=True,
    )

    paired_branches: dict[str, Any] = {}
    role_records = (
        ("guarded-live", "guarded_live", "guarded_live_checkpoint"),
        ("read-only-control", "read_only_control", "read_only_control_checkpoint"),
    )
    for role, directory, checkpoint_key in role_records:
        off_meta, off_state = read_checkpoint_bundle(paired_off[checkpoint_key])
        on_meta, on_state = read_checkpoint_bundle(paired_on[checkpoint_key])
        off_identity = root / "paired/off" / directory / "branch_identity.json"
        on_identity = root / "paired/on" / directory / "branch_identity.json"
        manifest_path = paired_on["categorical_sampling_trace_manifests"][role]
        trace_report = _validate_trace(manifest_path)
        paired_branches[role] = {
            "config_sha256_equal": off_meta["config_sha256"]
            == on_meta["config_sha256"],
            "checkpoint_state_sha256_equal": off_meta["state_sha256"]
            == on_meta["state_sha256"],
            "checkpoint_lineage_equal": off_state["checkpoint_lineage"]
            == on_state["checkpoint_lineage"],
            "branch_identity_byte_equal": off_identity.read_bytes()
            == on_identity.read_bytes(),
            "branch_identity_sha256": _sha256(off_identity),
            "trace": trace_report,
        }

    all_branch_neutral = all(
        item["config_sha256_equal"]
        and item["checkpoint_state_sha256_equal"]
        and item["checkpoint_lineage_equal"]
        and item["branch_identity_byte_equal"]
        for item in paired_branches.values()
    )
    passed = bool(
        fresh_actions_equal
        and fresh_probabilities_equal
        and baseline_meta["config_sha256"] == traced_meta["config_sha256"]
        and baseline_meta["state_sha256"] == traced_meta["state_sha256"]
        and all_branch_neutral
    )
    report: dict[str, Any] = {
        "schema": CATEGORICAL_SAMPLING_TRACE_INTEGRITY_SCHEMA,
        "producer_version": __version__,
        "passed": passed,
        "fresh_run": {
            "actions_equal": fresh_actions_equal,
            "selected_probabilities_equal": fresh_probabilities_equal,
            "config_sha256_equal": baseline_meta["config_sha256"]
            == traced_meta["config_sha256"],
            "checkpoint_state_sha256_equal": baseline_meta["state_sha256"]
            == traced_meta["state_sha256"],
            "trace": fresh_trace,
        },
        "paired_run": {
            "plan_sha256": plan["plan_sha256"],
            "trace_off_plan_sha256": paired_off["plan_sha256"],
            "trace_on_plan_sha256": paired_on["plan_sha256"],
            "branches": paired_branches,
            "all_branches_semantically_neutral": all_branch_neutral,
        },
        "contract": {
            "trace_is_checkpoint_state": False,
            "trace_changes_branch_identity": False,
            "trace_changes_random_stream": False,
            "trace_changes_sampled_action": False,
            "trace_has_runtime_feedback": False,
            "scientific_conclusion_authorized": False,
        },
    }
    report["assessment_sha256"] = _canonical_sha256(report)
    report_path = root / "categorical_sampling_trace_integrity.json"
    report_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    if not passed:
        raise RuntimeError("categorical sampling trace neutrality audit failed")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(
        description="验证 categorical sampling trace 不改变运行时语义。"
    )
    parser.add_argument("--output", required=True)
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()
    result = verify_categorical_sampling_trace(args.output, overwrite=args.overwrite)
    print(json.dumps({"passed": result["passed"], "assessment_sha256": result["assessment_sha256"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()


__all__ = [
    "CATEGORICAL_SAMPLING_TRACE_INTEGRITY_SCHEMA",
    "verify_categorical_sampling_trace",
]
