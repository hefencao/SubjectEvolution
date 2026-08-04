"""Subject VM activation contribution trace 的语义中立完整性审计。

该工程审计比较 trace 关闭/开启的同 checkpoint continuation 与真实 paired
branches，并使用 categorical sampling trace 作为 action/RNG 的独立字节级
对照。它只验证观测工具，不形成科学结论。
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
from ..experiments.subject_vm_short_paired_study import prime_fixed_bootstrap_graph
from ..policy import Action
from ..runtime.sim import Simulation

SUBJECT_VM_ACTIVATION_CONTRIBUTION_TRACE_INTEGRITY_SCHEMA = (
    "se-subject-vm-activation-contribution-trace-integrity-v1"
)


def _sha256(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _canonical_sha256(payload: dict[str, Any]) -> str:
    return hashlib.sha256(
        json.dumps(
            payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
    ).hexdigest()


def _small_config():
    cfg = load_config("configs/mvp_short_subject_vm_stage3c8_paired_study.json")
    return replace(
        cfg,
        world=replace(cfg.world, initial_entities=16, max_entities=32),
        run=replace(
            cfg.run,
            ticks=2,
            metrics_period=99,
            checkpoint_period=99,
            checkpoint_ticks=(),
            full_checkpoint_enabled=False,
        ),
    )


def _close_source(simulation: Simulation) -> None:
    simulation.metrics.close()
    simulation.evolution_progress.close()
    simulation.knowledge.close()
    simulation._close_observation_outputs()


def _build_source(root: Path) -> tuple[Path, tuple[int, ...], int]:
    simulation = Simulation(_small_config(), root / "source", backend="cpu")
    try:
        simulation.step()
        simulation.step()
        lineage = prime_fixed_bootstrap_graph(
            simulation,
            bootstrap_subjects=4,
            target_family="node_output_gate",
        )
        checkpoint = simulation.save_full_checkpoint(root / "source/source.sechk")
        return (
            checkpoint,
            tuple(int(value) for value in lineage["primed_subject_ids"]),
            int(simulation.tick),
        )
    finally:
        _close_source(simulation)


def _manifest_trace_path(manifest_path: str | Path) -> tuple[dict[str, Any], Path]:
    manifest_file = Path(manifest_path).resolve()
    manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
    recorded = str(manifest["manifest_sha256"])
    unsigned = dict(manifest)
    unsigned.pop("manifest_sha256", None)
    if recorded != _canonical_sha256(unsigned):
        raise ValueError("activation contribution manifest checksum mismatch")
    trace = Path(manifest["trace_path"])
    if not trace.is_file():
        trace = manifest_file.parent / trace.name
    if _sha256(trace) != str(manifest["trace_sha256"]):
        raise ValueError("activation contribution JSONL checksum mismatch")
    return manifest, trace


def _validate_activation_trace(manifest_path: str | Path) -> dict[str, Any]:
    manifest, trace = _manifest_trace_path(manifest_path)
    rows = [
        json.loads(line)
        for line in trace.read_text(encoding="utf-8").splitlines()
    ]
    if not rows or rows[0].get("record_type") != "header":
        raise ValueError("activation contribution trace header is missing")
    events = rows[1:]
    if len(events) != int(manifest["event_count"]):
        raise ValueError("activation contribution event count mismatch")

    node_count = edge_count = output_count = write_count = 0
    for event in events:
        edges_by_target: dict[int, float] = {}
        for edge in event["edge_transmissions"]:
            target = int(edge["target_node_index"])
            value = float(edge["bounded_contribution"])
            edges_by_target[target] = edges_by_target.get(target, 0.0) + value
            expected = float(
                np.clip(
                    float(edge["source_value"]) * float(edge["forward_gate"]),
                    -float(edge["bandwidth"]),
                    float(edge["bandwidth"]),
                )
            )
            if not np.isclose(expected, value, rtol=0.0, atol=1e-15):
                raise ValueError("activation edge contribution reconstruction failed")
        for node in event["node_activations"]:
            input_value = (
                0.0
                if int(node["input_port"]) < 0
                else float(node["input_value"]) * float(node["input_gate"])
            )
            expected = (
                float(node["bias_value"])
                + input_value
                + edges_by_target.get(int(node["node_index"]), 0.0)
            )
            if not np.isclose(
                expected, float(node["accumulator"]), rtol=0.0, atol=1e-15
            ):
                raise ValueError("activation node accumulator reconstruction failed")
        raw = np.zeros(len(Action), dtype=np.float32)
        for output in event["output_contributions"]:
            port = int(output["action_port"])
            raw[port] += np.float32(output["float32_contribution"])
        if not np.array_equal(
            raw, np.asarray(event["raw_action_potentials"], dtype=np.float32)
        ):
            raise ValueError("activation output aggregation reconstruction failed")
        expected_output = np.clip(
            raw,
            -float(event["output_clip"]),
            float(event["output_clip"]),
        ).astype(np.float32)
        if not np.array_equal(
            expected_output,
            np.asarray(event["action_potentials"], dtype=np.float32),
        ):
            raise ValueError("activation clipped output reconstruction failed")
        for entry in event["temporary_write_lineage"]:
            for target in entry["targets"]:
                if entry["status_name"] == "guarded-live-pending" and not target[
                    "current_matches_post"
                ]:
                    raise ValueError("live write lineage is inconsistent")
                if (
                    entry["status_name"] == "read-only-control-pending"
                    and not target["current_matches_pre"]
                ):
                    raise ValueError("control reservation lineage is inconsistent")
        node_count += len(event["node_activations"])
        edge_count += len(event["edge_transmissions"])
        output_count += len(event["output_contributions"])
        write_count += len(event["temporary_write_lineage"])

    expected_counts = {
        "node_activation_count": node_count,
        "edge_transmission_count": edge_count,
        "output_contribution_count": output_count,
        "temporary_write_entry_count": write_count,
    }
    for name, value in expected_counts.items():
        if int(manifest[name]) != value:
            raise ValueError(f"activation contribution {name} mismatch")
    return {
        "manifest": str(Path(manifest_path).resolve()),
        "manifest_sha256": str(manifest["manifest_sha256"]),
        "trace": str(trace.resolve()),
        "trace_sha256": str(manifest["trace_sha256"]),
        "event_count": len(events),
        **expected_counts,
        "bytes_per_subject_tick": (
            float(trace.stat().st_size) / len(events) if events else 0.0
        ),
        "node_edge_output_reconstruction_passed": True,
        "temporary_write_lineage_consistent": True,
    }


def _categorical_trace_path(manifest_path: str | Path) -> Path:
    manifest_file = Path(manifest_path).resolve()
    manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
    path = Path(manifest["trace_path"])
    return path if path.is_file() else manifest_file.parent / path.name


def _checkpoint_identity(left: str | Path, right: str | Path) -> dict[str, Any]:
    left_meta, left_state = read_checkpoint_bundle(left)
    right_meta, right_state = read_checkpoint_bundle(right)
    left_action = np.asarray(left_state["simulation"]["last_policy_decision"].action)
    right_action = np.asarray(right_state["simulation"]["last_policy_decision"].action)
    left_probability = np.asarray(left_state["simulation"]["last_policy_decision"].probability)
    right_probability = np.asarray(right_state["simulation"]["last_policy_decision"].probability)
    return {
        "state_sha256_equal": str(left_meta["state_sha256"])
        == str(right_meta["state_sha256"]),
        "last_action_equal": bool(np.array_equal(left_action, right_action)),
        "last_selected_probability_equal": bool(
            np.array_equal(left_probability, right_probability)
        ),
        "left_state_sha256": str(left_meta["state_sha256"]),
        "right_state_sha256": str(right_meta["state_sha256"]),
    }


def verify_subject_vm_activation_contribution_trace(
    output_dir: str | Path, *, overwrite: bool = False
) -> dict[str, Any]:
    root = Path(output_dir).resolve()
    if root.exists():
        if not overwrite:
            raise FileExistsError(root)
        shutil.rmtree(root)
    root.mkdir(parents=True)
    source, subjects, source_tick = _build_source(root)

    fresh_off = Simulation.from_checkpoint(
        source, root / "fresh/off", backend="cpu", until_tick=source_tick + 2
    )
    fresh_on = Simulation.from_checkpoint(
        source, root / "fresh/on", backend="cpu", until_tick=source_tick + 2
    )
    for role, simulation in (("off", fresh_off), ("on", fresh_on)):
        simulation.enable_categorical_sampling_trace(
            metadata={"audit_scope": "fresh"},
            subject_ids=subjects,
        )
    fresh_on.enable_subject_vm_activation_contribution_trace(
        metadata={"audit_scope": "fresh", "activation_trace_role": "on"},
        subject_ids=subjects,
    )
    fresh_off.run(until_tick=source_tick + 2)
    fresh_on.run(until_tick=source_tick + 2)
    fresh_off_checkpoint = fresh_off.save_full_checkpoint(
        root / "fresh/off/final.sechk"
    )
    fresh_on_checkpoint = fresh_on.save_full_checkpoint(
        root / "fresh/on/final.sechk"
    )
    fresh_identity = _checkpoint_identity(
        fresh_off_checkpoint, fresh_on_checkpoint
    )
    fresh_categorical_equal = (
        (root / "fresh/off/categorical_sampling_trace.jsonl").read_bytes()
        == (root / "fresh/on/categorical_sampling_trace.jsonl").read_bytes()
    )
    fresh_activation = _validate_activation_trace(
        root
        / "fresh/on/subject_vm_activation_contribution_trace_manifest.json"
    )

    plan = build_plan(source, horizon_ticks=5)
    off = run_plan(
        plan,
        source_checkpoint=source,
        output_dir=root / "paired/off",
        backend="cpu",
        categorical_sampling_trace=True,
        categorical_sampling_trace_subject_ids=subjects,
    )
    on = run_plan(
        plan,
        source_checkpoint=source,
        output_dir=root / "paired/on",
        backend="cpu",
        categorical_sampling_trace=True,
        categorical_sampling_trace_subject_ids=subjects,
        subject_vm_activation_contribution_trace=True,
        subject_vm_activation_contribution_trace_subject_ids=subjects,
    )

    paired_identity: dict[str, Any] = {}
    paired_categorical_equal = True
    paired_branch_identity_equal = True
    activation_traces: dict[str, Any] = {}
    for role, checkpoint_key, directory in (
        ("read-only-control", "read_only_control_checkpoint", "read_only_control"),
        ("guarded-live", "guarded_live_checkpoint", "guarded_live"),
    ):
        paired_identity[role] = _checkpoint_identity(
            off[checkpoint_key], on[checkpoint_key]
        )
        off_manifest = off["categorical_sampling_trace_manifests"][role]
        on_manifest = on["categorical_sampling_trace_manifests"][role]
        paired_categorical_equal &= (
            _categorical_trace_path(off_manifest).read_bytes()
            == _categorical_trace_path(on_manifest).read_bytes()
        )
        paired_branch_identity_equal &= (
            (root / f"paired/off/{directory}/branch_identity.json").read_bytes()
            == (root / f"paired/on/{directory}/branch_identity.json").read_bytes()
        )
        activation_traces[role] = _validate_activation_trace(
            on["subject_vm_activation_contribution_trace_manifests"][role]
        )

    checks = {
        "fresh_checkpoint_state_hash_identity": bool(
            fresh_identity["state_sha256_equal"]
        ),
        "fresh_last_action_identity": bool(fresh_identity["last_action_equal"]),
        "fresh_selected_probability_identity": bool(
            fresh_identity["last_selected_probability_equal"]
        ),
        "fresh_categorical_action_rng_trace_byte_identity": bool(
            fresh_categorical_equal
        ),
        "paired_checkpoint_state_hash_identity": all(
            item["state_sha256_equal"] for item in paired_identity.values()
        ),
        "paired_last_action_identity": all(
            item["last_action_equal"] for item in paired_identity.values()
        ),
        "paired_selected_probability_identity": all(
            item["last_selected_probability_equal"]
            for item in paired_identity.values()
        ),
        "paired_categorical_action_rng_trace_byte_identity": bool(
            paired_categorical_equal
        ),
        "paired_branch_identity_file_byte_identity": bool(
            paired_branch_identity_equal
        ),
        "activation_node_edge_output_reconstruction": all(
            item["node_edge_output_reconstruction_passed"]
            for item in activation_traces.values()
        )
        and fresh_activation["node_edge_output_reconstruction_passed"],
        "temporary_write_lineage_consistent": all(
            item["temporary_write_lineage_consistent"]
            for item in activation_traces.values()
        ),
        "guarded_live_temporary_write_lineage_observed": (
            activation_traces["guarded-live"]["temporary_write_entry_count"] > 0
        ),
    }
    if not all(checks.values()):
        failed = sorted(name for name, passed in checks.items() if not passed)
        raise RuntimeError(
            "Subject VM activation contribution trace integrity failed: "
            + ", ".join(failed)
        )

    payload: dict[str, Any] = {
        "schema": SUBJECT_VM_ACTIVATION_CONTRIBUTION_TRACE_INTEGRITY_SCHEMA,
        "producer_version": __version__,
        "task_type": "ENGINEERING",
        "source_checkpoint": str(source),
        "source_checkpoint_file_sha256": _sha256(source),
        "source_subject_ids": list(subjects),
        "source_tick": source_tick,
        "fresh_identity": fresh_identity,
        "fresh_activation_trace": fresh_activation,
        "paired_identity": paired_identity,
        "paired_activation_traces": activation_traces,
        "checks": checks,
        "runtime_semantics_changed": False,
        "configuration_identity_changed": False,
        "checkpoint_state_changed": False,
        "branch_identity_changed": False,
        "random_stream_consumed_by_trace": False,
        "scientific_result": False,
        "stage3c42_authorized_next": True,
        "automatic_keep_or_revert_authorized": False,
        "learned_weight_authorized": False,
        "permanent_retention_authorized": False,
    }
    payload["assessment_sha256"] = _canonical_sha256(payload)
    destination = root / "subject_vm_activation_contribution_trace_integrity.json"
    destination.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return payload


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Verify neutral Subject VM activation contribution tracing."
    )
    parser.add_argument("--output", required=True)
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()
    payload = verify_subject_vm_activation_contribution_trace(
        args.output, overwrite=args.overwrite
    )
    print(json.dumps(payload["checks"], ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()


__all__ = [
    "SUBJECT_VM_ACTIVATION_CONTRIBUTION_TRACE_INTEGRITY_SCHEMA",
    "verify_subject_vm_activation_contribution_trace",
]
