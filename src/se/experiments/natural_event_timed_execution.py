"""Event-timed paired execution for natural-event intervention manifests.

The older natural-event executor applies an intervention at the nearest prior
checkpoint.  That estimates the effect of changing a mechanism before the
observed event and can therefore alter the event exposure and the identities
present at the nominal event tick.  This module implements a distinct estimand:

1. replay one shared prefix from the signed source checkpoint to the nominal
   event tick;
2. save a hash-audited full-world event checkpoint;
3. branch baseline and interventions from that exact event state;
4. freeze common-boundary and stable-ID cohort diagnostics before applying the
   intervention.

The event exposure remains naturally occurring and non-randomized, but every
post-event comparison has an identical pre-intervention world and cohort.
"""

from __future__ import annotations

import argparse
from collections import defaultdict
import hashlib
import json
from pathlib import Path
import shutil
from typing import Any, Iterable, Sequence

from ..checkpointing import read_checkpoint_bundle
from se.experiments.local_event_counterfactual import _numeric_delta, _region_summary, _run_branch
from se.experiments.natural_event_execution import (
    AGGREGATION_SCHEMA,
    BASELINE,
    COMMON_BOUNDARY_AUDIT_SCHEMA,
    EVENT_COHORT_AUDIT_SCHEMA,
    _canonical_sha256,
    _normalize_interventions,
    _selected_anchors,
    _sha256_file,
    aggregate_results,
    audit_outcomes,
    parse_path_prefixes,
    remap_path,
)
from se.experiments.natural_event_matrix import load_manifest, validate_manifest
from ..runtime.sim import Simulation


PLAN_SCHEMA = "natural-event-timed-execution-plan-v1"
PREFLIGHT_SCHEMA = "natural-event-timed-execution-preflight-v1"
PREFIX_MARKER_SCHEMA = "natural-event-shared-prefix-v1"
TRAJECTORY_MARKER_SCHEMA = "natural-event-timed-trajectory-v1"
RESULT_SCHEMA = "natural-event-timed-paired-intervention-results-v1"
INTERVENTION_TIMING = "anchor-event-tick-v1"
PAIRING_SCHEMA = "shared-event-checkpoint-pairing-v1"


def _prefix_id(checkpoint_sha256: str, event_tick: int) -> str:
    return f"{checkpoint_sha256[:16]}-event-{int(event_tick):08d}"


def _trajectory_id(prefix_id: str, intervention: str) -> str:
    return f"{prefix_id}-{intervention.replace('-', '_')}"


def build_timed_execution_plan(
    manifest: dict[str, Any],
    *,
    path_prefixes: Sequence[tuple[Path, Path]] = (),
    anchor_ids: Iterable[str] | None = None,
    seeds: Iterable[int] | None = None,
    event_kinds: Iterable[str] | None = None,
    interventions: Iterable[str] | None = None,
    common_boundary_audit: bool = True,
    event_cohort_audit: bool = True,
) -> dict[str, Any]:
    """Build a signed event-timed plan without consulting outcome fields."""

    validate_manifest(manifest)
    selected = _selected_anchors(
        manifest,
        anchor_ids=anchor_ids,
        seeds=seeds,
        event_kinds=event_kinds,
    )
    requested = _normalize_interventions(interventions)
    if requested is None:
        requested = tuple(
            dict.fromkeys(
                str(entry["intervention"])
                for anchor in selected
                for entry in anchor.get("interventions", [])
                if bool(entry.get("eligible"))
            )
        )

    prefixes: dict[tuple[str, int], dict[str, Any]] = {}
    trajectories: dict[tuple[str, str], dict[str, Any]] = {}
    selected_payloads: list[dict[str, Any]] = []
    naive_branch_count = 0

    for anchor in selected:
        checkpoint_sha = str(anchor["checkpoint_sha256"])
        event_tick = int(anchor["event_tick"])
        prefix_key = (checkpoint_sha, event_tick)
        prefix_name = _prefix_id(checkpoint_sha, event_tick)
        resolved_checkpoint = remap_path(anchor["checkpoint_path"], path_prefixes)
        dependency = {
            "anchor_id": str(anchor["anchor_id"]),
            "seed": int(anchor["seed"]),
            "event_kind": str(anchor["event_kind"]),
            "region_id": int(anchor["region_id"]),
            "event_tick": event_tick,
            "until_tick": int(anchor["until_tick"]),
        }
        if prefix_key not in prefixes:
            prefixes[prefix_key] = {
                "prefix_id": prefix_name,
                "source_checkpoint_sha256": checkpoint_sha,
                "source_checkpoint_path_original": str(anchor["checkpoint_path"]),
                "source_checkpoint_path_resolved": str(resolved_checkpoint),
                "source_checkpoint_tick": int(anchor["checkpoint_tick"]),
                "event_tick": event_tick,
                "dependencies": [dependency],
                "output_relative_path": str(Path("prefixes") / prefix_name),
            }
        else:
            prefixes[prefix_key]["dependencies"].append(dependency)

        eligible = {
            str(entry["intervention"]): bool(entry.get("eligible"))
            for entry in anchor.get("interventions", [])
        }
        reasons = {
            str(entry["intervention"]): entry.get("reason")
            for entry in anchor.get("interventions", [])
        }
        selected_entries = [
            {
                "intervention": name,
                "eligible": bool(eligible.get(name, False)),
                "reason": reasons.get(name, "intervention is not present in the manifest anchor"),
            }
            for name in requested
        ]
        anchor_copy = dict(anchor)
        anchor_copy["checkpoint_path_resolved"] = str(resolved_checkpoint)
        anchor_copy["prefix_id"] = prefix_name
        anchor_copy["intervention_tick"] = event_tick
        anchor_copy["interventions_selected"] = selected_entries
        selected_payloads.append(anchor_copy)

        for label in (BASELINE, *requested):
            if label != BASELINE and not eligible.get(label, False):
                continue
            naive_branch_count += 1
            key = (prefix_name, label)
            if key not in trajectories:
                trajectories[key] = {
                    "trajectory_id": _trajectory_id(prefix_name, label),
                    "prefix_id": prefix_name,
                    "source_checkpoint_sha256": checkpoint_sha,
                    "event_tick": event_tick,
                    "intervention_tick": None if label == BASELINE else event_tick,
                    "intervention": None if label == BASELINE else label,
                    "intervention_label": label,
                    "until_tick": int(anchor["until_tick"]),
                    "dependencies": [dependency],
                }
            else:
                trajectory = trajectories[key]
                trajectory["until_tick"] = max(
                    int(trajectory["until_tick"]), int(anchor["until_tick"])
                )
                trajectory["dependencies"].append(dependency)

    prefix_rows = sorted(
        prefixes.values(), key=lambda item: (item["source_checkpoint_sha256"], item["event_tick"])
    )
    for prefix in prefix_rows:
        prefix["dependencies"] = sorted(
            prefix["dependencies"], key=lambda item: str(item["anchor_id"])
        )

    trajectory_rows = sorted(
        trajectories.values(), key=lambda item: (item["prefix_id"], item["intervention_label"])
    )
    for trajectory in trajectory_rows:
        trajectory["dependencies"] = sorted(
            trajectory["dependencies"], key=lambda item: str(item["anchor_id"])
        )
        trajectory["output_relative_path"] = str(
            Path("trajectories") / str(trajectory["trajectory_id"])
        )

    selected_run_names = {str(anchor["run_name"]) for anchor in selected}
    source_files: list[dict[str, Any]] = []
    for source in manifest.get("source_runs", []):
        if str(source.get("run_name")) not in selected_run_names:
            continue
        for kind, path_key, hash_key in (
            ("progress", "progress_path", "progress_sha256"),
            ("config", "config_path", "config_sha256"),
        ):
            original = str(source[path_key])
            source_files.append(
                {
                    "kind": kind,
                    "run_name": str(source["run_name"]),
                    "path_original": original,
                    "path_resolved": str(remap_path(original, path_prefixes)),
                    "expected_sha256": str(source[hash_key]),
                    "required_for_execution": False,
                    "required_for_full_audit": True,
                }
            )

    payload: dict[str, Any] = {
        "schema": PLAN_SCHEMA,
        "manifest_schema": str(manifest["schema"]),
        "manifest_sha256": str(manifest["plan_sha256"]),
        "intervention_timing": INTERVENTION_TIMING,
        "pairing_schema": PAIRING_SCHEMA,
        "path_prefixes": [{"from": str(old), "to": str(new)} for old, new in path_prefixes],
        "selection": {
            "anchor_ids": sorted(str(value) for value in anchor_ids or ()),
            "seeds": sorted(int(value) for value in seeds or ()),
            "event_kinds": sorted(str(value) for value in event_kinds or ()),
            "interventions": list(requested),
        },
        "diagnostics": {
            "common_boundary_audit": bool(common_boundary_audit),
            "common_boundary_schema": (
                COMMON_BOUNDARY_AUDIT_SCHEMA if common_boundary_audit else None
            ),
            "event_cohort_audit": bool(event_cohort_audit),
            "event_cohort_schema": (
                EVENT_COHORT_AUDIT_SCHEMA if event_cohort_audit else None
            ),
            "event_identity_hashes": bool(event_cohort_audit),
            "feedback_to_world": False,
        },
        "selected_anchor_count": len(selected_payloads),
        "selected_anchors": selected_payloads,
        "source_files": source_files,
        "prefix_count": len(prefix_rows),
        "prefixes": prefix_rows,
        "naive_branch_count": int(naive_branch_count),
        "trajectory_count": len(trajectory_rows),
        "deduplicated_branch_count": int(naive_branch_count - len(trajectory_rows)),
        "trajectories": trajectory_rows,
        "pairing_boundary": (
            "Each prefix is replayed once from the signed source checkpoint to the nominal "
            "event tick. Baseline and interventions then load the same event checkpoint; "
            "common-boundary and cohort snapshots are captured before the intervention."
        ),
    }
    payload["execution_plan_sha256"] = _canonical_sha256(payload)
    return payload


def validate_timed_execution_plan(plan: dict[str, Any]) -> None:
    if plan.get("schema") != PLAN_SCHEMA:
        raise ValueError(f"unsupported timed execution plan schema {plan.get('schema')!r}")
    if plan.get("intervention_timing") != INTERVENTION_TIMING:
        raise ValueError("timed execution plan has the wrong intervention timing")
    claimed = str(plan.get("execution_plan_sha256", ""))
    unsigned = dict(plan)
    unsigned.pop("execution_plan_sha256", None)
    if claimed != _canonical_sha256(unsigned):
        raise ValueError("timed execution plan SHA-256 does not match its contents")
    prefix_ids = [str(item["prefix_id"]) for item in plan.get("prefixes", [])]
    if len(prefix_ids) != len(set(prefix_ids)):
        raise ValueError("timed execution plan has duplicate prefix IDs")
    trajectory_ids = [str(item["trajectory_id"]) for item in plan.get("trajectories", [])]
    if len(trajectory_ids) != len(set(trajectory_ids)):
        raise ValueError("timed execution plan has duplicate trajectory IDs")
    known = set(prefix_ids)
    for trajectory in plan.get("trajectories", []):
        if str(trajectory["prefix_id"]) not in known:
            raise ValueError("trajectory references an unknown shared prefix")
        event_tick = int(trajectory["event_tick"])
        intervention_tick = trajectory.get("intervention_tick")
        if intervention_tick is not None and int(intervention_tick) != event_tick:
            raise ValueError("intervention tick must equal the nominal event tick")
        if int(trajectory["until_tick"]) < event_tick:
            raise ValueError("trajectory horizon precedes its event tick")


def load_timed_execution_plan(path: str | Path) -> dict[str, Any]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    validate_timed_execution_plan(payload)
    return payload


def _check(path: str, expected: str, *, kind: str, reference: str, execution: bool) -> dict[str, Any]:
    candidate = Path(path)
    exists = candidate.is_file()
    actual = _sha256_file(candidate) if exists else None
    return {
        "kind": kind,
        "reference": reference,
        "path": str(candidate),
        "exists": exists,
        "expected_sha256": expected,
        "actual_sha256": actual,
        "hash_match": bool(exists and actual == expected),
        "required_for_execution": execution,
        "required_for_full_audit": True,
    }


def preflight_timed_execution_plan(plan: dict[str, Any]) -> dict[str, Any]:
    validate_timed_execution_plan(plan)
    checks: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for prefix in plan.get("prefixes", []):
        key = (str(prefix["source_checkpoint_path_resolved"]), str(prefix["source_checkpoint_sha256"]))
        if key in seen:
            continue
        seen.add(key)
        checks.append(
            _check(
                key[0], key[1], kind="checkpoint", reference=str(prefix["prefix_id"]), execution=True
            )
        )
    for source in plan.get("source_files", []):
        checks.append(
            _check(
                str(source["path_resolved"]),
                str(source["expected_sha256"]),
                kind=str(source["kind"]),
                reference=str(source["run_name"]),
                execution=bool(source.get("required_for_execution", False)),
            )
        )
    execution_failures = [
        item for item in checks if item["required_for_execution"] and not item["hash_match"]
    ]
    audit_failures = [
        item for item in checks if item["required_for_full_audit"] and not item["hash_match"]
    ]
    return {
        "schema": PREFLIGHT_SCHEMA,
        "execution_plan_sha256": str(plan["execution_plan_sha256"]),
        "manifest_sha256": str(plan["manifest_sha256"]),
        "file_check_count": len(checks),
        "execution_ready": not execution_failures,
        "full_audit_ready": not audit_failures,
        "execution_failure_count": len(execution_failures),
        "audit_failure_count": len(audit_failures),
        "checks": checks,
    }


def _prefix_marker_path(output_dir: Path) -> Path:
    return output_dir / "natural_event_shared_prefix.json"


def _materialize_prefix_checkpoint(
    prefix: dict[str, Any],
    output_dir: Path,
    *,
    plan: dict[str, Any],
    backend: str,
    gpu_semantics_mode: str | None,
    overwrite_existing: bool,
) -> dict[str, Any]:
    marker_path = _prefix_marker_path(output_dir)
    if not overwrite_existing and marker_path.is_file():
        marker = json.loads(marker_path.read_text(encoding="utf-8"))
        checkpoint = Path(str(marker.get("event_checkpoint_path", "")))
        valid = (
            marker.get("schema") == PREFIX_MARKER_SCHEMA
            and marker.get("execution_plan_sha256") == plan["execution_plan_sha256"]
            and marker.get("prefix_id") == prefix["prefix_id"]
            and marker.get("source_checkpoint_sha256") == prefix["source_checkpoint_sha256"]
            and int(marker.get("event_tick", -1)) == int(prefix["event_tick"])
            and checkpoint.is_file()
            and _sha256_file(checkpoint) == marker.get("event_checkpoint_file_sha256")
        )
        if valid:
            return {**marker, "resumed": True}
    if output_dir.exists():
        if overwrite_existing:
            shutil.rmtree(output_dir)
        elif any(output_dir.iterdir()):
            raise FileExistsError(
                f"prefix output exists without a reusable marker: {output_dir}; "
                "use --overwrite-existing to replace it"
            )
    output_dir.mkdir(parents=True, exist_ok=True)
    simulation = Simulation.from_checkpoint(
        prefix["source_checkpoint_path_resolved"],
        output_dir,
        backend=backend,
        until_tick=int(prefix["event_tick"]),
        gpu_semantics_mode=gpu_semantics_mode,
    )
    simulation.run(until_tick=int(prefix["event_tick"]))
    event_checkpoint = simulation.save_full_checkpoint(
        output_dir / f"event_checkpoint_{int(prefix['event_tick']):08d}.sechk"
    )
    metadata, _ = read_checkpoint_bundle(event_checkpoint)
    marker = {
        "schema": PREFIX_MARKER_SCHEMA,
        "execution_plan_sha256": str(plan["execution_plan_sha256"]),
        "manifest_sha256": str(plan["manifest_sha256"]),
        "prefix_id": str(prefix["prefix_id"]),
        "source_checkpoint_sha256": str(prefix["source_checkpoint_sha256"]),
        "source_checkpoint_tick": int(prefix["source_checkpoint_tick"]),
        "event_tick": int(prefix["event_tick"]),
        "event_checkpoint_path": str(event_checkpoint),
        "event_checkpoint_file_sha256": _sha256_file(event_checkpoint),
        "event_checkpoint_state_sha256": str(metadata["state_sha256"]),
        "backend": backend,
        "gpu_semantics_mode": gpu_semantics_mode,
    }
    marker_path.write_text(json.dumps(marker, ensure_ascii=False, indent=2), encoding="utf-8")
    return {**marker, "resumed": False}


def _trajectory_marker_path(output_dir: Path) -> Path:
    return output_dir / "natural_event_timed_trajectory.json"


def _load_trajectory(
    output_dir: Path,
    *,
    plan: dict[str, Any],
    trajectory: dict[str, Any],
    prefix_marker: dict[str, Any],
) -> dict[str, Any] | None:
    marker_path = _trajectory_marker_path(output_dir)
    progress = output_dir / "evolution_progress.jsonl"
    if not marker_path.is_file() or not progress.is_file():
        return None
    marker = json.loads(marker_path.read_text(encoding="utf-8"))
    valid = (
        marker.get("schema") == TRAJECTORY_MARKER_SCHEMA
        and marker.get("execution_plan_sha256") == plan["execution_plan_sha256"]
        and marker.get("trajectory_id") == trajectory["trajectory_id"]
        and marker.get("prefix_id") == trajectory["prefix_id"]
        and marker.get("event_checkpoint_state_sha256")
        == prefix_marker["event_checkpoint_state_sha256"]
        and marker.get("intervention") == trajectory["intervention"]
        and int(marker.get("until_tick", -1)) == int(trajectory["until_tick"])
    )
    if not valid:
        return None
    records = [json.loads(line) for line in progress.read_text(encoding="utf-8").splitlines() if line.strip()]
    return {
        "records": records,
        "scientific_validity": marker.get("scientific_validity", {}),
        "intervention_history": marker.get("intervention_history", []),
        "event_cohort_summaries": marker.get("event_cohort_summaries", {}),
        "resumed": True,
        "marker": marker,
    }


def _write_trajectory_marker(
    output_dir: Path,
    *,
    plan: dict[str, Any],
    trajectory: dict[str, Any],
    prefix_marker: dict[str, Any],
    result: dict[str, Any],
    backend: str,
    gpu_semantics_mode: str | None,
) -> dict[str, Any]:
    marker = {
        "schema": TRAJECTORY_MARKER_SCHEMA,
        "execution_plan_sha256": str(plan["execution_plan_sha256"]),
        "manifest_sha256": str(plan["manifest_sha256"]),
        "trajectory_id": str(trajectory["trajectory_id"]),
        "prefix_id": str(trajectory["prefix_id"]),
        "event_checkpoint_state_sha256": str(prefix_marker["event_checkpoint_state_sha256"]),
        "event_tick": int(trajectory["event_tick"]),
        "intervention_tick": trajectory.get("intervention_tick"),
        "intervention": trajectory["intervention"],
        "until_tick": int(trajectory["until_tick"]),
        "backend": backend,
        "gpu_semantics_mode": gpu_semantics_mode,
        "scientific_validity": result.get("scientific_validity", {}),
        "intervention_history": result.get("intervention_history", []),
        "event_cohort_summaries": result.get("event_cohort_summaries", {}),
    }
    _trajectory_marker_path(output_dir).write_text(
        json.dumps(marker, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return marker


def _pairing_audit(
    baseline: dict[str, Any], branch: dict[str, Any], *, event_tick: int
) -> dict[str, Any]:
    fields = ("event_alive_region", "event_global_ids_sha256", "event_region_ids_sha256")
    comparisons = {field: baseline.get(field) == branch.get(field) for field in fields}
    return {
        "schema": PAIRING_SCHEMA,
        "event_tick": int(event_tick),
        "event_alive_equal": comparisons["event_alive_region"],
        "event_global_identity_equal": comparisons["event_global_ids_sha256"],
        "event_region_identity_equal": comparisons["event_region_ids_sha256"],
        "valid": all(comparisons.values()),
    }


def execute_timed_plan(
    plan: dict[str, Any],
    output_dir: str | Path,
    *,
    backend: str = "cpu",
    gpu_semantics_mode: str | None = None,
    overwrite_existing: bool = False,
    require_full_audit: bool = True,
) -> dict[str, Any]:
    validate_timed_execution_plan(plan)
    root = Path(output_dir)
    root.mkdir(parents=True, exist_ok=True)
    preflight = preflight_timed_execution_plan(plan)
    (root / "natural_event_timed_execution_preflight.json").write_text(
        json.dumps(preflight, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    ready_key = "full_audit_ready" if require_full_audit else "execution_ready"
    if not preflight[ready_key]:
        raise FileNotFoundError(f"timed execution preflight failed ({ready_key}=false)")

    prefix_markers: dict[str, dict[str, Any]] = {}
    prefix_executed = 0
    prefix_resumed = 0
    for prefix in plan["prefixes"]:
        marker = _materialize_prefix_checkpoint(
            prefix,
            root / str(prefix["output_relative_path"]),
            plan=plan,
            backend=backend,
            gpu_semantics_mode=gpu_semantics_mode,
            overwrite_existing=overwrite_existing,
        )
        prefix_markers[str(prefix["prefix_id"])] = marker
        prefix_resumed += int(marker["resumed"])
        prefix_executed += int(not marker["resumed"])

    trajectory_results: dict[tuple[str, str], dict[str, Any]] = {}
    executed = 0
    resumed = 0
    common_boundary = bool(plan["diagnostics"]["common_boundary_audit"])
    event_cohort = bool(plan["diagnostics"]["event_cohort_audit"])
    for trajectory in plan["trajectories"]:
        prefix_marker = prefix_markers[str(trajectory["prefix_id"])]
        output = root / str(trajectory["output_relative_path"])
        reusable = None if overwrite_existing else _load_trajectory(
            output, plan=plan, trajectory=trajectory, prefix_marker=prefix_marker
        )
        key = (str(trajectory["prefix_id"]), str(trajectory["intervention_label"]))
        if reusable is not None:
            trajectory_results[key] = reusable
            resumed += 1
            continue
        if output.exists():
            if overwrite_existing:
                shutil.rmtree(output)
            elif any(output.iterdir()):
                raise FileExistsError(
                    f"trajectory output exists without a reusable marker: {output}; "
                    "use --overwrite-existing to replace it"
                )
        output.mkdir(parents=True, exist_ok=True)
        result = _run_branch(
            prefix_marker["event_checkpoint_path"],
            output,
            until_tick=int(trajectory["until_tick"]),
            backend=backend,
            gpu_semantics_mode=gpu_semantics_mode,
            intervention=trajectory["intervention"],
            common_boundary_audit=common_boundary,
            cohort_requests=(list(trajectory["dependencies"]) if event_cohort else None),
        )
        marker = _write_trajectory_marker(
            output,
            plan=plan,
            trajectory=trajectory,
            prefix_marker=prefix_marker,
            result=result,
            backend=backend,
            gpu_semantics_mode=gpu_semantics_mode,
        )
        result["resumed"] = False
        result["marker"] = marker
        trajectory_results[key] = result
        executed += 1

    requested = tuple(str(value) for value in plan["selection"]["interventions"])
    anchor_results: list[dict[str, Any]] = []
    pairing_failures = 0
    for anchor in plan["selected_anchors"]:
        prefix_id = str(anchor["prefix_id"])
        baseline = trajectory_results[(prefix_id, BASELINE)]
        horizon = int(anchor["until_tick"])
        baseline_records = [r for r in baseline["records"] if int(r.get("tick", 0)) <= horizon]
        baseline_summary = _region_summary(
            baseline_records, region=int(anchor["region_id"]), event_tick=int(anchor["event_tick"])
        )
        baseline_summary.update(
            baseline.get("event_cohort_summaries", {}).get(str(anchor["anchor_id"]), {})
        )
        selected = {
            str(entry["intervention"]): entry for entry in anchor["interventions_selected"]
        }
        branches: list[dict[str, Any]] = []
        for intervention in requested:
            entry = selected[intervention]
            if not entry["eligible"]:
                branches.append(
                    {
                        "intervention": intervention,
                        "eligible": False,
                        "reason": entry.get("reason"),
                        "region_summary": {},
                        "delta": {},
                        "pre_event_pairing": None,
                    }
                )
                continue
            branch = trajectory_results[(prefix_id, intervention)]
            records = [r for r in branch["records"] if int(r.get("tick", 0)) <= horizon]
            summary = _region_summary(
                records, region=int(anchor["region_id"]), event_tick=int(anchor["event_tick"])
            )
            summary.update(
                branch.get("event_cohort_summaries", {}).get(str(anchor["anchor_id"]), {})
            )
            pairing = _pairing_audit(
                baseline_summary, summary, event_tick=int(anchor["event_tick"])
            )
            pairing_failures += int(not pairing["valid"])
            branches.append(
                {
                    "intervention": intervention,
                    "eligible": True,
                    "reason": None,
                    "region_summary": summary,
                    "delta": _numeric_delta(summary, baseline_summary),
                    "pre_event_pairing": pairing,
                    "scientific_validity": branch.get("scientific_validity", {}),
                    "intervention_history": branch.get("intervention_history", []),
                    "trajectory_resumed": bool(branch.get("resumed")),
                }
            )
        anchor_results.append(
            {
                "anchor": anchor,
                "prefix": {
                    "prefix_id": prefix_id,
                    "event_checkpoint_state_sha256": prefix_markers[prefix_id][
                        "event_checkpoint_state_sha256"
                    ],
                },
                "baseline_region_summary": baseline_summary,
                "baseline_scientific_validity": baseline.get("scientific_validity", {}),
                "baseline_trajectory_resumed": bool(baseline.get("resumed")),
                "branches": branches,
            }
        )

    aggregation = aggregate_results(anchor_results)
    report: dict[str, Any] = {
        "schema": RESULT_SCHEMA,
        "manifest_sha256": str(plan["manifest_sha256"]),
        "execution_plan_sha256": str(plan["execution_plan_sha256"]),
        "intervention_timing": INTERVENTION_TIMING,
        "pairing_schema": PAIRING_SCHEMA,
        "backend": backend,
        "gpu_semantics_mode": gpu_semantics_mode,
        "prefix_count": int(plan["prefix_count"]),
        "executed_prefix_count": prefix_executed,
        "resumed_prefix_count": prefix_resumed,
        "trajectory_count": int(plan["trajectory_count"]),
        "executed_trajectory_count": executed,
        "resumed_trajectory_count": resumed,
        "paired_randomness": True,
        "diagnostics": dict(plan["diagnostics"]),
        "pre_event_pairing": {
            "schema": PAIRING_SCHEMA,
            "pair_count": sum(
                int(branch.get("eligible", False))
                for item in anchor_results
                for branch in item["branches"]
            ),
            "failure_count": pairing_failures,
            "all_valid": pairing_failures == 0,
        },
        "results": anchor_results,
        "aggregation": aggregation,
        "interpretation_boundary": (
            "Interventions begin at the nominal event tick from one shared event checkpoint. "
            "This identifies short-horizon post-event mechanism effects conditional on the "
            "selected natural event; the event exposure itself remains non-randomized."
        ),
    }
    report["outcome_audit"] = audit_outcomes(report)
    report["outcome_audit"]["pre_event_pairing"] = dict(report["pre_event_pairing"])
    (root / "natural_event_timed_results.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (root / "natural_event_timed_results.md").write_text(
        render_timed_results_markdown(report), encoding="utf-8"
    )
    return report


def render_timed_plan_markdown(plan: dict[str, Any]) -> str:
    lines = [
        "# Natural-event event-timed execution plan",
        "",
        f"Manifest SHA-256: `{plan['manifest_sha256']}`",
        f"Execution-plan SHA-256: `{plan['execution_plan_sha256']}`",
        "",
        f"- Intervention timing: `{plan['intervention_timing']}`",
        f"- Selected anchors: {plan['selected_anchor_count']}",
        f"- Shared prefixes: {plan['prefix_count']}",
        f"- Post-event trajectories: {plan['trajectory_count']}",
        "",
        "| Prefix | Source tick | Event tick | Anchors |",
        "|---|---:|---:|---:|",
    ]
    for prefix in plan["prefixes"]:
        lines.append(
            f"| {prefix['prefix_id']} | {prefix['source_checkpoint_tick']} | "
            f"{prefix['event_tick']} | {len(prefix['dependencies'])} |"
        )
    lines.extend(["", "## Pairing boundary", "", plan["pairing_boundary"], ""])
    return "\n".join(lines)


def render_timed_results_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Natural-event event-timed results",
        "",
        f"Manifest SHA-256: `{report['manifest_sha256']}`",
        f"Execution-plan SHA-256: `{report['execution_plan_sha256']}`",
        "",
        f"- Shared prefixes: {report['prefix_count']}",
        f"- Post-event trajectories: {report['trajectory_count']}",
        f"- Pre-event pairing failures: {report['pre_event_pairing']['failure_count']}",
        "",
        "| Anchor | Intervention | Pairing | Δ alive | Δ retained | Δ absent | Δ in-migrants | Δ post-event born |",
        "|---|---|---|---:|---:|---:|---:|---:|",
    ]
    keys = (
        "final_alive_region",
        "final_event_cohort_retained_region",
        "final_event_cohort_absent",
        "final_existing_in_migrants_region",
        "final_post_event_born_region",
    )
    for item in report["results"]:
        for branch in item["branches"]:
            if not branch.get("eligible"):
                continue
            values = [branch["delta"].get(key) for key in keys]
            formatted = ["—" if value is None else f"{float(value):+.5f}" for value in values]
            lines.append(
                f"| {item['anchor']['anchor_id']} | {branch['intervention']} | "
                f"{branch['pre_event_pairing']['valid']} | " + " | ".join(formatted) + " |"
            )
    lines.extend(["", "## Interpretation boundary", "", report["interpretation_boundary"], ""])
    return "\n".join(lines)


def _split_csv(value: str | None) -> tuple[str, ...] | None:
    if value is None:
        return None
    result = tuple(item.strip() for item in value.split(",") if item.strip())
    return result or None


def _split_int_csv(value: str | None) -> tuple[int, ...] | None:
    values = _split_csv(value)
    return tuple(int(item) for item in values) if values is not None else None


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Build or execute event-timed natural-event paired interventions"
    )
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--manifest")
    source.add_argument("--execution-plan")
    parser.add_argument("--output", required=True)
    parser.add_argument("--path-prefix", action="append", default=[])
    parser.add_argument("--anchor-ids")
    parser.add_argument("--seeds")
    parser.add_argument("--event-kinds")
    parser.add_argument("--interventions")
    parser.add_argument("--no-common-boundary-audit", action="store_true")
    parser.add_argument("--no-event-cohort-audit", action="store_true")
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--backend", choices=("cpu", "gpu", "auto"), default="cpu")
    parser.add_argument(
        "--gpu-semantics-mode", choices=("strict-reference", "hybrid-accelerated")
    )
    parser.add_argument("--overwrite-existing", action="store_true")
    parser.add_argument("--execution-only-preflight", action="store_true")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    root = Path(args.output)
    root.mkdir(parents=True, exist_ok=True)
    if args.execution_plan:
        if any(
            (
                args.path_prefix,
                args.anchor_ids,
                args.seeds,
                args.event_kinds,
                args.interventions,
                args.no_common_boundary_audit,
                args.no_event_cohort_audit,
            )
        ):
            raise ValueError("signed execution-plan mode does not accept plan-changing filters")
        plan = load_timed_execution_plan(args.execution_plan)
    else:
        manifest = load_manifest(args.manifest)
        plan = build_timed_execution_plan(
            manifest,
            path_prefixes=parse_path_prefixes(args.path_prefix),
            anchor_ids=_split_csv(args.anchor_ids),
            seeds=_split_int_csv(args.seeds),
            event_kinds=_split_csv(args.event_kinds),
            interventions=_split_csv(args.interventions),
            common_boundary_audit=not args.no_common_boundary_audit,
            event_cohort_audit=not args.no_event_cohort_audit,
        )
    (root / "natural_event_timed_execution_plan.json").write_text(
        json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (root / "natural_event_timed_execution_plan.md").write_text(
        render_timed_plan_markdown(plan), encoding="utf-8"
    )
    preflight = preflight_timed_execution_plan(plan)
    (root / "natural_event_timed_execution_preflight.json").write_text(
        json.dumps(preflight, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    if args.execute:
        execute_timed_plan(
            plan,
            root,
            backend=args.backend,
            gpu_semantics_mode=args.gpu_semantics_mode,
            overwrite_existing=args.overwrite_existing,
            require_full_audit=not args.execution_only_preflight,
        )


if __name__ == "__main__":
    main()
