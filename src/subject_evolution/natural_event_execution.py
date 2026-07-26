"""Resumable, hash-audited execution for natural-event intervention manifests.

The v0.24 planner deliberately separates exposure-only anchor selection from
outcome analysis.  This module consumes that immutable manifest and turns it
into a portable execution plan.  It can remap absolute path prefixes, verify
the source and checkpoint hash chain, deduplicate trajectories that share the
same checkpoint and intervention, resume completed trajectories, and aggregate
paired deltas at both anchor and seed levels.

Nothing in this module changes world rules or selects anchors from outcomes.
"""

from __future__ import annotations

import argparse
from collections import defaultdict
import hashlib
import json
from pathlib import Path
import shutil
from statistics import median
from typing import Any, Iterable, Sequence

from .interventions import ExperimentMode, resolve_intervention
from .local_event_counterfactual import _numeric_delta, _region_summary, _run_branch
from .long_run_analysis import load_progress
from .natural_event_matrix import load_manifest, validate_manifest


EXECUTION_PLAN_SCHEMA = "natural-event-execution-plan-v3"
LEGACY_EXECUTION_PLAN_SCHEMAS = {
    "natural-event-execution-plan-v1",
    "natural-event-execution-plan-v2",
}
PREFLIGHT_SCHEMA = "natural-event-execution-preflight-v1"
TRAJECTORY_MARKER_SCHEMA = "natural-event-trajectory-run-v3"
LEGACY_TRAJECTORY_MARKER_SCHEMA = "natural-event-trajectory-run-v2"
RESULT_SCHEMA = "natural-event-paired-intervention-results-v4"
AGGREGATION_SCHEMA = "natural-event-paired-delta-aggregation-v3"
COMMON_BOUNDARY_AUDIT_SCHEMA = "checkpoint-frozen-stable-entity-boundary-v1"
EVENT_COHORT_AUDIT_SCHEMA = "event-region-endpoint-cohort-decomposition-v1"
BASELINE = "baseline"
DELTA_KEYS = (
    "final_alive_region",
    "final_cohesion_region",
    "final_scarcity_region",
    "final_mortality_region",
    "final_active_transferred_roots_region",
    "post_event_outgoing_commits",
    "post_event_incoming_commits",
    "post_event_new_transferred_roots",
    "post_event_lost_transferred_roots",
    "final_reference_cohesion_region",
    "final_boundary_definition_gap_region",
    "post_event_cohesion_region",
    "post_event_reference_cohesion_region",
    "post_event_boundary_definition_gap_region",
    "post_event_benefit_internal_region",
    "post_event_benefit_cross_boundary_region",
    "post_event_reference_benefit_internal_region",
    "post_event_reference_benefit_cross_boundary_region",
    "event_alive_region",
    "final_alive_region_from_cohort_audit",
    "final_event_cohort_retained_region",
    "final_event_cohort_survived_outside_region",
    "final_event_cohort_absent",
    "final_existing_in_migrants_region",
    "final_post_event_born_region",
    "endpoint_population_change_region",
    "endpoint_population_change_reconstructed",
    "endpoint_population_balance_residual",
    "event_cohort_survival_fraction",
    "event_cohort_region_retention_fraction",
)


def _canonical_sha256(payload: dict[str, Any]) -> str:
    encoded = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def parse_path_prefixes(values: Iterable[str]) -> tuple[tuple[Path, Path], ...]:
    """Parse repeatable ``OLD=NEW`` path-prefix remaps.

    The longest matching OLD prefix wins.  Paths are intentionally not resolved
    here, so a missing original path can still be remapped on another machine.
    """

    result: list[tuple[Path, Path]] = []
    for raw in values:
        if "=" not in raw:
            raise ValueError(f"path prefix must use OLD=NEW syntax: {raw!r}")
        old_text, new_text = raw.split("=", 1)
        old = Path(old_text).expanduser()
        new = Path(new_text).expanduser()
        if not old_text.strip() or not new_text.strip():
            raise ValueError(f"path prefix must have non-empty OLD and NEW: {raw!r}")
        result.append((old, new))
    result.sort(key=lambda pair: len(str(pair[0])), reverse=True)
    return tuple(result)


def remap_path(path: str | Path, prefixes: Sequence[tuple[Path, Path]]) -> Path:
    original = Path(path).expanduser()
    if original.exists():
        return original
    for old, new in prefixes:
        try:
            relative = original.relative_to(old)
        except ValueError:
            continue
        return new / relative
    return original


def _normalize_interventions(values: Iterable[str] | None) -> tuple[str, ...] | None:
    if values is None:
        return None
    normalized: list[str] = []
    for value in values:
        if not value.strip():
            continue
        spec = resolve_intervention(value)
        spec.require_mode(ExperimentMode.SCIENTIFIC)
        if spec.name not in normalized:
            normalized.append(spec.name)
    if not normalized:
        raise ValueError("intervention filter is empty")
    return tuple(normalized)


def _trajectory_id(checkpoint_sha256: str, intervention: str) -> str:
    suffix = intervention.replace("-", "_")
    return f"{checkpoint_sha256[:16]}-{suffix}"


def _selected_anchors(
    manifest: dict[str, Any],
    *,
    anchor_ids: Iterable[str] | None,
    seeds: Iterable[int] | None,
    event_kinds: Iterable[str] | None,
) -> list[dict[str, Any]]:
    anchor_filter = {str(value) for value in anchor_ids or ()}
    seed_filter = {int(value) for value in seeds or ()}
    event_filter = {str(value).strip().lower().replace("_", "-") for value in event_kinds or ()}
    unknown_events = event_filter - {"scarcity", "crowding", "mortality"}
    if unknown_events:
        raise ValueError(f"unknown event filters: {sorted(unknown_events)}")
    selected = []
    for anchor in manifest.get("anchors", []):
        if anchor_filter and str(anchor["anchor_id"]) not in anchor_filter:
            continue
        if seed_filter and int(anchor["seed"]) not in seed_filter:
            continue
        if event_filter and str(anchor["event_kind"]) not in event_filter:
            continue
        selected.append(dict(anchor))
    if anchor_filter:
        found = {str(item["anchor_id"]) for item in selected}
        missing = sorted(anchor_filter - found)
        if missing:
            raise ValueError(f"anchor IDs not present after filtering: {missing}")
    if not selected:
        raise ValueError("execution filters selected no anchors")
    return selected


def build_execution_plan(
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
    """Build a portable, deduplicated execution plan from a signed manifest."""

    validate_manifest(manifest)
    selected = _selected_anchors(
        manifest,
        anchor_ids=anchor_ids,
        seeds=seeds,
        event_kinds=event_kinds,
    )
    requested_interventions = _normalize_interventions(interventions)
    if requested_interventions is None:
        requested_interventions = tuple(
            dict.fromkeys(
                str(entry["intervention"])
                for anchor in selected
                for entry in anchor.get("interventions", [])
                if bool(entry.get("eligible"))
            )
        )

    groups: dict[tuple[str, str], dict[str, Any]] = {}
    naive_branch_count = 0
    selected_anchor_payloads: list[dict[str, Any]] = []
    for anchor in selected:
        checkpoint_sha = str(anchor["checkpoint_sha256"])
        resolved_checkpoint = remap_path(anchor["checkpoint_path"], path_prefixes)
        eligible = {
            str(entry["intervention"]): bool(entry.get("eligible"))
            for entry in anchor.get("interventions", [])
        }
        reasons = {
            str(entry["intervention"]): entry.get("reason")
            for entry in anchor.get("interventions", [])
        }
        requested_entries = []
        for name in requested_interventions:
            requested_entries.append(
                {
                    "intervention": name,
                    "eligible": bool(eligible.get(name, False)),
                    "reason": reasons.get(name, "intervention is not present in the manifest anchor"),
                }
            )
        anchor_copy = dict(anchor)
        anchor_copy["checkpoint_path_resolved"] = str(resolved_checkpoint)
        anchor_copy["interventions_selected"] = requested_entries
        selected_anchor_payloads.append(anchor_copy)

        dependencies = [
            {
                "anchor_id": str(anchor["anchor_id"]),
                "seed": int(anchor["seed"]),
                "event_kind": str(anchor["event_kind"]),
                "region_id": int(anchor["region_id"]),
                "event_tick": int(anchor["event_tick"]),
                "until_tick": int(anchor["until_tick"]),
            }
        ]
        for intervention in (BASELINE, *requested_interventions):
            if intervention != BASELINE and not eligible.get(intervention, False):
                continue
            naive_branch_count += 1
            key = (checkpoint_sha, intervention)
            if key not in groups:
                groups[key] = {
                    "trajectory_id": _trajectory_id(checkpoint_sha, intervention),
                    "checkpoint_sha256": checkpoint_sha,
                    "checkpoint_path_original": str(anchor["checkpoint_path"]),
                    "checkpoint_path_resolved": str(resolved_checkpoint),
                    "checkpoint_tick": int(anchor["checkpoint_tick"]),
                    "intervention": None if intervention == BASELINE else intervention,
                    "intervention_label": intervention,
                    "until_tick": int(anchor["until_tick"]),
                    "dependencies": list(dependencies),
                }
            else:
                group = groups[key]
                group["until_tick"] = max(int(group["until_tick"]), int(anchor["until_tick"]))
                group["dependencies"].extend(dependencies)

    trajectories = sorted(
        groups.values(),
        key=lambda item: (
            str(item["checkpoint_sha256"]),
            str(item["intervention_label"]),
        ),
    )
    for trajectory in trajectories:
        trajectory["dependencies"] = sorted(
            trajectory["dependencies"],
            key=lambda item: str(item["anchor_id"]),
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
        "schema": EXECUTION_PLAN_SCHEMA,
        "manifest_schema": str(manifest["schema"]),
        "manifest_sha256": str(manifest["plan_sha256"]),
        "path_prefixes": [
            {"from": str(old), "to": str(new)} for old, new in path_prefixes
        ],
        "selection": {
            "anchor_ids": sorted(str(value) for value in anchor_ids or ()),
            "seeds": sorted(int(value) for value in seeds or ()),
            "event_kinds": sorted(str(value) for value in event_kinds or ()),
            "interventions": list(requested_interventions),
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
            "feedback_to_world": False,
        },
        "selected_anchor_count": len(selected_anchor_payloads),
        "selected_anchors": selected_anchor_payloads,
        "source_files": source_files,
        "naive_branch_count": int(naive_branch_count),
        "trajectory_count": len(trajectories),
        "deduplicated_branch_count": int(naive_branch_count - len(trajectories)),
        "deduplication_fraction": (
            float(naive_branch_count - len(trajectories)) / float(naive_branch_count)
            if naive_branch_count
            else 0.0
        ),
        "trajectories": trajectories,
        "pairing_boundary": (
            "Every intervention comparison uses the baseline trajectory from the same "
            "checkpoint hash. A longer shared trajectory may serve multiple anchors only "
            "when checkpoint and intervention are identical; region summaries are still "
            "computed separately at each anchor's event tick and horizon."
        ),
    }
    payload["execution_plan_sha256"] = _canonical_sha256(payload)
    return payload


def validate_execution_plan(payload: dict[str, Any]) -> None:
    if payload.get("schema") not in (LEGACY_EXECUTION_PLAN_SCHEMAS | {EXECUTION_PLAN_SCHEMA}):
        raise ValueError(f"unsupported execution-plan schema {payload.get('schema')!r}")
    expected = str(payload.get("execution_plan_sha256", ""))
    unsigned = dict(payload)
    unsigned.pop("execution_plan_sha256", None)
    if _canonical_sha256(unsigned) != expected:
        raise ValueError("natural-event execution-plan checksum mismatch")
    ids = [str(item["trajectory_id"]) for item in payload.get("trajectories", [])]
    if len(ids) != len(set(ids)):
        raise ValueError("natural-event execution plan has duplicate trajectory IDs")


def load_execution_plan(path: str | Path) -> dict[str, Any]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("natural-event execution plan must be a JSON object")
    validate_execution_plan(payload)
    return payload


def _file_check(
    *,
    kind: str,
    path: str | Path,
    expected_sha256: str,
    required_for_execution: bool,
    required_for_full_audit: bool,
    reference: str,
) -> dict[str, Any]:
    source = Path(path)
    exists = source.is_file()
    actual = _sha256_file(source) if exists else None
    return {
        "kind": kind,
        "reference": reference,
        "path": str(source),
        "exists": exists,
        "expected_sha256": expected_sha256,
        "actual_sha256": actual,
        "hash_match": bool(exists and actual == expected_sha256),
        "required_for_execution": required_for_execution,
        "required_for_full_audit": required_for_full_audit,
    }


def preflight_execution_plan(plan: dict[str, Any]) -> dict[str, Any]:
    validate_execution_plan(plan)
    checks: list[dict[str, Any]] = []
    seen_checkpoints: set[tuple[str, str]] = set()
    for trajectory in plan.get("trajectories", []):
        key = (
            str(trajectory["checkpoint_path_resolved"]),
            str(trajectory["checkpoint_sha256"]),
        )
        if key in seen_checkpoints:
            continue
        seen_checkpoints.add(key)
        checks.append(
            _file_check(
                kind="checkpoint",
                path=key[0],
                expected_sha256=key[1],
                required_for_execution=True,
                required_for_full_audit=True,
                reference=str(trajectory["trajectory_id"]),
            )
        )
    for source in plan.get("source_files", []):
        checks.append(
            _file_check(
                kind=str(source["kind"]),
                path=source["path_resolved"],
                expected_sha256=str(source["expected_sha256"]),
                required_for_execution=bool(source["required_for_execution"]),
                required_for_full_audit=bool(source["required_for_full_audit"]),
                reference=str(source["run_name"]),
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


def _trajectory_marker_path(output_dir: Path) -> Path:
    return output_dir / "natural_event_trajectory.json"


def _load_resumable_trajectory(
    output_dir: Path,
    *,
    manifest_sha256: str,
    checkpoint_sha256: str,
    intervention: str | None,
    until_tick: int,
    common_boundary_audit: bool,
    event_cohort_audit: bool,
) -> dict[str, Any] | None:
    marker_path = _trajectory_marker_path(output_dir)
    progress_path = output_dir / "evolution_progress.jsonl"
    if not marker_path.is_file() or not progress_path.is_file():
        return None
    marker = json.loads(marker_path.read_text(encoding="utf-8"))
    marker_schema = marker.get("schema")
    if marker_schema not in {LEGACY_TRAJECTORY_MARKER_SCHEMA, TRAJECTORY_MARKER_SCHEMA}:
        return None
    if str(marker.get("manifest_sha256")) != manifest_sha256:
        return None
    if str(marker.get("checkpoint_sha256")) != checkpoint_sha256:
        return None
    if marker.get("intervention") != intervention:
        return None
    if bool(marker.get("common_boundary_audit", False)) != bool(common_boundary_audit):
        return None
    expected_boundary_schema = (
        COMMON_BOUNDARY_AUDIT_SCHEMA if common_boundary_audit else None
    )
    if marker.get("common_boundary_schema") != expected_boundary_schema:
        return None
    if bool(marker.get("event_cohort_audit", False)) != bool(event_cohort_audit):
        return None
    expected_cohort_schema = EVENT_COHORT_AUDIT_SCHEMA if event_cohort_audit else None
    if marker.get("event_cohort_schema") != expected_cohort_schema:
        return None
    if event_cohort_audit and marker_schema != TRAJECTORY_MARKER_SCHEMA:
        return None
    if int(marker.get("completed_until_tick", -1)) < int(until_tick):
        return None
    return {
        "records": load_progress(progress_path),
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
    result: dict[str, Any],
    backend: str,
    gpu_semantics_mode: str | None,
) -> dict[str, Any]:
    marker = {
        "schema": TRAJECTORY_MARKER_SCHEMA,
        "manifest_sha256": str(plan["manifest_sha256"]),
        "execution_plan_sha256": str(plan["execution_plan_sha256"]),
        "trajectory_id": str(trajectory["trajectory_id"]),
        "checkpoint_sha256": str(trajectory["checkpoint_sha256"]),
        "checkpoint_path": str(trajectory["checkpoint_path_resolved"]),
        "intervention": trajectory["intervention"],
        "common_boundary_audit": bool(
            plan.get("diagnostics", {}).get("common_boundary_audit", False)
        ),
        "common_boundary_schema": plan.get("diagnostics", {}).get(
            "common_boundary_schema"
        ),
        "event_cohort_audit": bool(
            plan.get("diagnostics", {}).get("event_cohort_audit", False)
        ),
        "event_cohort_schema": plan.get("diagnostics", {}).get(
            "event_cohort_schema"
        ),
        "event_cohort_summaries": result.get("event_cohort_summaries", {}),
        "completed_until_tick": int(trajectory["until_tick"]),
        "backend": backend,
        "gpu_semantics_mode": gpu_semantics_mode,
        "scientific_validity": result.get("scientific_validity", {}),
        "intervention_history": result.get("intervention_history", []),
    }
    _trajectory_marker_path(output_dir).write_text(
        json.dumps(marker, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return marker


def _stat(values: list[float]) -> dict[str, Any]:
    if not values:
        return {
            "count": 0,
            "mean": None,
            "median": None,
            "min": None,
            "max": None,
            "positive": 0,
            "negative": 0,
            "zero": 0,
        }
    return {
        "count": len(values),
        "mean": sum(values) / len(values),
        "median": median(values),
        "min": min(values),
        "max": max(values),
        "positive": sum(value > 0 for value in values),
        "negative": sum(value < 0 for value in values),
        "zero": sum(value == 0 for value in values),
    }


def aggregate_results(results: list[dict[str, Any]]) -> dict[str, Any]:
    anchor_values: dict[tuple[str, str, str], list[float]] = defaultdict(list)
    seed_buckets: dict[tuple[str, str, str, int], list[float]] = defaultdict(list)
    for item in results:
        anchor = item["anchor"]
        event_kind = str(anchor["event_kind"])
        seed = int(anchor["seed"])
        for branch in item["branches"]:
            if not branch.get("eligible"):
                continue
            intervention = str(branch["intervention"])
            for key, raw in branch.get("delta", {}).items():
                if key not in DELTA_KEYS or not isinstance(raw, (int, float)):
                    continue
                value = float(raw)
                anchor_values[(event_kind, intervention, key)].append(value)
                seed_buckets[(event_kind, intervention, key, seed)].append(value)

    groups: list[dict[str, Any]] = []
    for event_kind, intervention, key in sorted(anchor_values):
        anchor_level = _stat(anchor_values[(event_kind, intervention, key)])
        seed_values = [
            sum(values) / len(values)
            for (event, name, metric, _seed), values in sorted(seed_buckets.items())
            if (event, name, metric) == (event_kind, intervention, key)
        ]
        groups.append(
            {
                "event_kind": event_kind,
                "intervention": intervention,
                "metric": key,
                "anchor_level": anchor_level,
                "seed_level": _stat(seed_values),
            }
        )
    return {
        "schema": AGGREGATION_SCHEMA,
        "groups": groups,
        "interpretation_boundary": (
            "Anchor-level rows are not independent because two anchors may share a seed or "
            "checkpoint. Seed-level values first average anchors within each seed and are the "
            "preferred directional summary. With three seeds these remain descriptive; no "
            "null-hypothesis significance claim is made."
        ),
    }


def audit_outcomes(report: dict[str, Any]) -> dict[str, Any]:
    """Classify paired outcomes by causal distance and measurement dependence."""

    results = list(report.get("results", []))
    event_kinds = sorted(
        {str(item.get("anchor", {}).get("event_kind")) for item in results}
    )
    seeds = sorted({int(item.get("anchor", {}).get("seed", 0)) for item in results})
    interventions = sorted(
        {
            str(branch.get("intervention"))
            for item in results
            for branch in item.get("branches", [])
            if branch.get("eligible")
        }
    )
    common_boundary_requested = bool(
        report.get("diagnostics", {}).get("common_boundary_audit", False)
    )
    common_boundary_observed = bool(results) and all(
        bool(branch.get("region_summary", {}).get("reference_boundary_available"))
        for item in results
        for branch in item.get("branches", [])
        if branch.get("eligible")
    )
    event_cohort_requested = bool(
        report.get("diagnostics", {}).get("event_cohort_audit", False)
    )
    cohort_summaries = [
        item.get("baseline_region_summary", {})
        for item in results
    ] + [
        branch.get("region_summary", {})
        for item in results
        for branch in item.get("branches", [])
        if branch.get("eligible")
    ]
    event_cohort_observed = bool(cohort_summaries) and all(
        summary.get("event_cohort_schema") == EVENT_COHORT_AUDIT_SCHEMA
        for summary in cohort_summaries
    )
    event_cohort_balance_valid = bool(cohort_summaries) and all(
        int(summary.get("endpoint_population_balance_residual", 1)) == 0
        for summary in cohort_summaries
        if summary.get("event_cohort_schema") == EVENT_COHORT_AUDIT_SCHEMA
    ) and event_cohort_observed

    repeated: list[dict[str, Any]] = []
    for group in report.get("aggregation", {}).get("groups", []):
        stat = group.get("seed_level", {})
        count = int(stat.get("count", 0))
        positive = int(stat.get("positive", 0))
        negative = int(stat.get("negative", 0))
        if count >= 3 and (positive == count or negative == count):
            repeated.append(
                {
                    "event_kind": group["event_kind"],
                    "intervention": group["intervention"],
                    "metric": group["metric"],
                    "direction": "positive" if positive == count else "negative",
                    "seed_count": count,
                    "mean": stat.get("mean"),
                }
            )

    transfer_branches = [
        branch
        for item in results
        for branch in item.get("branches", [])
        if branch.get("eligible")
        and branch.get("intervention") == "disable-knowledge-transfer"
    ]
    transfer_zero_commits = bool(transfer_branches) and all(
        int(branch.get("region_summary", {}).get("post_event_incoming_commits", -1)) == 0
        and int(branch.get("region_summary", {}).get("post_event_outgoing_commits", -1)) == 0
        for branch in transfer_branches
    )
    freeze_branches = [
        branch
        for item in results
        for branch in item.get("branches", [])
        if branch.get("eligible") and branch.get("intervention") == "freeze-group-refresh"
    ]
    freeze_history_valid = bool(freeze_branches) and all(
        any(
            entry.get("type") == "freeze-group-refresh"
            and entry.get("existing_group_labels_modified") is False
            for entry in branch.get("intervention_history", [])
        )
        for branch in freeze_branches
    )
    affinity_branches = [
        branch
        for item in results
        for branch in item.get("branches", [])
        if branch.get("eligible")
        and branch.get("intervention") == "neutralize-resource-affinity"
    ]
    affinity_history_valid = bool(affinity_branches) and all(
        any(
            entry.get("type") == "neutralize-resource-affinity"
            and int(entry.get("genotype_coordinates_modified", -1)) == 0
            and list(entry.get("effective_affinity_q", [])) == [4096, 4096, 4096, 4096]
            for entry in branch.get("intervention_history", [])
        )
        for branch in affinity_branches
    )

    metric_roles = {
        "post_event_incoming_commits": "manipulation-check for transfer interventions",
        "post_event_outgoing_commits": "manipulation-check for transfer interventions",
        "post_event_new_transferred_roots": "mechanism-proximal cultural state",
        "post_event_lost_transferred_roots": "mechanism-proximal cultural state",
        "final_active_transferred_roots_region": "mechanism-proximal cultural state",
        "final_alive_region": "downstream regional endpoint state",
        "final_event_cohort_retained_region": "event-cohort endpoint retention",
        "final_event_cohort_survived_outside_region": "event-cohort surviving out-migration",
        "final_event_cohort_absent": "event-cohort death or endpoint absence",
        "final_existing_in_migrants_region": "endpoint in-migration by entities alive at event tick",
        "final_post_event_born_region": "post-event births alive in region at horizon",
        "endpoint_population_change_region": "regional endpoint population change",
        "endpoint_population_balance_residual": "cohort decomposition exactness check",
        "event_cohort_survival_fraction": "event-cohort survival endpoint fraction",
        "event_cohort_region_retention_fraction": "event-cohort regional retention fraction",
        "final_mortality_region": "downstream region-window state",
        "final_scarcity_region": "downstream environment/population state",
        "final_cohesion_region": "current-label boundary metric",
        "post_event_cohesion_region": "current-label cumulative boundary metric",
        "final_reference_cohesion_region": "checkpoint-common boundary metric",
        "post_event_reference_cohesion_region": "preferred checkpoint-common cumulative boundary metric",
        "post_event_boundary_definition_gap_region": "measurement-boundary component",
    }
    warnings = [
        "Transfer commits and transferred-root counts are mechanism-proximal; they are not demographic or subjecthood outcomes.",
    ]
    if not event_cohort_observed:
        warnings.insert(
            0,
            "Regional alive is compositional: survival, endpoint absence, migration, and post-event births are not separated until an event-cohort audit is available.",
        )
    else:
        warnings.insert(
            0,
            "Event-cohort decomposition is an endpoint identity accounting, not a complete pathwise birth/death/migration flow ledger.",
        )
    if "freeze-group-refresh" in interventions and not common_boundary_observed:
        warnings.append(
            "freeze-group-refresh changes the labels used by current-boundary cohesion; current-label cohesion is measurement-entangled until a common-boundary rerun is available."
        )
    return {
        "schema": "natural-event-outcome-audit-v2",
        "coverage": {
            "anchor_count": len(results),
            "seeds": seeds,
            "event_kinds": event_kinds,
            "interventions": interventions,
        },
        "common_boundary": {
            "requested": common_boundary_requested,
            "observed": common_boundary_observed,
            "schema": report.get("diagnostics", {}).get("common_boundary_schema"),
            "preferred_cohesion_metric": (
                "post_event_reference_cohesion_region"
                if common_boundary_observed
                else None
            ),
        },
        "event_cohort": {
            "requested": event_cohort_requested,
            "observed": event_cohort_observed,
            "schema": report.get("diagnostics", {}).get("event_cohort_schema"),
            "endpoint_balance_valid": event_cohort_balance_valid,
            "preferred_population_metrics": (
                [
                    "final_event_cohort_retained_region",
                    "final_event_cohort_survived_outside_region",
                    "final_event_cohort_absent",
                    "final_existing_in_migrants_region",
                    "final_post_event_born_region",
                ]
                if event_cohort_observed
                else []
            ),
        },
        "manipulation_checks": {
            "disable_knowledge_transfer_zero_region_commits": transfer_zero_commits,
            "freeze_group_refresh_history_valid": freeze_history_valid,
            "neutralize_resource_affinity_history_valid": affinity_history_valid,
            "event_cohort_endpoint_balance_valid": event_cohort_balance_valid,
        },
        "metric_roles": metric_roles,
        "repeated_seed_directions": repeated,
        "warnings": warnings,
        "interpretation_boundary": (
            "Repeated seed direction is descriptive with three seeds. Common-boundary "
            "metrics isolate the evaluation partition, and event-cohort metrics decompose "
            "endpoint regional population identity. The naturally occurring event exposure "
            "remains non-randomized."
        ),
    }


def execute_plan(
    plan: dict[str, Any],
    output_dir: str | Path,
    *,
    backend: str = "cpu",
    gpu_semantics_mode: str | None = None,
    overwrite_existing: bool = False,
    require_full_audit: bool = True,
) -> dict[str, Any]:
    validate_execution_plan(plan)
    root = Path(output_dir)
    root.mkdir(parents=True, exist_ok=True)
    preflight = preflight_execution_plan(plan)
    (root / "natural_event_execution_preflight.json").write_text(
        json.dumps(preflight, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    ready_key = "full_audit_ready" if require_full_audit else "execution_ready"
    if not bool(preflight[ready_key]):
        raise FileNotFoundError(
            f"natural-event execution preflight failed ({ready_key}=false); "
            "inspect natural_event_execution_preflight.json or provide --path-prefix"
        )

    trajectory_results: dict[tuple[str, str], dict[str, Any]] = {}
    common_boundary_audit = bool(
        plan.get("diagnostics", {}).get("common_boundary_audit", False)
    )
    event_cohort_audit = bool(
        plan.get("diagnostics", {}).get("event_cohort_audit", False)
    )
    executed_count = 0
    resumed_count = 0
    for trajectory in plan["trajectories"]:
        output = root / str(trajectory["output_relative_path"])
        label = str(trajectory["intervention_label"])
        key = (str(trajectory["checkpoint_sha256"]), label)
        reusable = None if overwrite_existing else _load_resumable_trajectory(
            output,
            manifest_sha256=str(plan["manifest_sha256"]),
            checkpoint_sha256=str(trajectory["checkpoint_sha256"]),
            intervention=trajectory["intervention"],
            until_tick=int(trajectory["until_tick"]),
            common_boundary_audit=common_boundary_audit,
            event_cohort_audit=event_cohort_audit,
        )
        if reusable is not None:
            trajectory_results[key] = reusable
            resumed_count += 1
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
            trajectory["checkpoint_path_resolved"],
            output,
            until_tick=int(trajectory["until_tick"]),
            backend=backend,
            gpu_semantics_mode=gpu_semantics_mode,
            intervention=trajectory["intervention"],
            common_boundary_audit=common_boundary_audit,
            cohort_requests=(
                list(trajectory.get("dependencies", [])) if event_cohort_audit else None
            ),
        )
        marker = _write_trajectory_marker(
            output,
            plan=plan,
            trajectory=trajectory,
            result=result,
            backend=backend,
            gpu_semantics_mode=gpu_semantics_mode,
        )
        result["resumed"] = False
        result["marker"] = marker
        trajectory_results[key] = result
        executed_count += 1

    anchor_results: list[dict[str, Any]] = []
    requested = tuple(str(value) for value in plan["selection"]["interventions"])
    for anchor in plan["selected_anchors"]:
        checkpoint_sha = str(anchor["checkpoint_sha256"])
        baseline = trajectory_results[(checkpoint_sha, BASELINE)]
        anchor_until_tick = int(anchor["until_tick"])
        baseline_records = [
            record
            for record in baseline["records"]
            if int(record.get("tick", 0)) <= anchor_until_tick
        ]
        baseline_region = _region_summary(
            baseline_records,
            region=int(anchor["region_id"]),
            event_tick=int(anchor["event_tick"]),
        )
        baseline_region.update(
            dict(baseline.get("event_cohort_summaries", {}).get(str(anchor["anchor_id"]), {}))
        )
        selected_entries = {
            str(entry["intervention"]): entry
            for entry in anchor["interventions_selected"]
        }
        branches: list[dict[str, Any]] = []
        for intervention in requested:
            entry = selected_entries[intervention]
            if not bool(entry["eligible"]):
                branches.append(
                    {
                        "intervention": intervention,
                        "eligible": False,
                        "reason": entry["reason"],
                        "region_summary": {},
                        "delta": {},
                    }
                )
                continue
            branch = trajectory_results[(checkpoint_sha, intervention)]
            branch_records = [
                record
                for record in branch["records"]
                if int(record.get("tick", 0)) <= anchor_until_tick
            ]
            region_summary = _region_summary(
                branch_records,
                region=int(anchor["region_id"]),
                event_tick=int(anchor["event_tick"]),
            )
            region_summary.update(
                dict(branch.get("event_cohort_summaries", {}).get(str(anchor["anchor_id"]), {}))
            )
            branches.append(
                {
                    "intervention": intervention,
                    "eligible": True,
                    "reason": None,
                    "region_summary": region_summary,
                    "delta": _numeric_delta(region_summary, baseline_region),
                    "scientific_validity": branch.get("scientific_validity", {}),
                    "intervention_history": branch.get("intervention_history", []),
                    "trajectory_resumed": bool(branch.get("resumed")),
                }
            )
        anchor_results.append(
            {
                "anchor": anchor,
                "baseline_region_summary": baseline_region,
                "baseline_scientific_validity": baseline.get("scientific_validity", {}),
                "baseline_trajectory_resumed": bool(baseline.get("resumed")),
                "branches": branches,
            }
        )

    report = {
        "schema": RESULT_SCHEMA,
        "manifest_sha256": str(plan["manifest_sha256"]),
        "execution_plan_sha256": str(plan["execution_plan_sha256"]),
        "backend": backend,
        "gpu_semantics_mode": gpu_semantics_mode,
        "trajectory_count": int(plan["trajectory_count"]),
        "executed_trajectory_count": executed_count,
        "resumed_trajectory_count": resumed_count,
        "deduplicated_branch_count": int(plan["deduplicated_branch_count"]),
        "paired_randomness": True,
        "diagnostics": dict(plan.get("diagnostics", {})),
        "results": anchor_results,
        "aggregation": aggregate_results(anchor_results),
        "interpretation_boundary": (
            "The manifest fixes exposure-only anchors before branch outcomes are read. "
            "Paired deltas identify short-horizon mechanism effects conditional on those "
            "naturally occurring events; they do not identify the causal effect of the "
            "event exposure itself."
        ),
    }
    report["outcome_audit"] = audit_outcomes(report)
    (root / "natural_event_matrix_results.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (root / "natural_event_matrix_results.md").write_text(
        render_results_markdown(report), encoding="utf-8"
    )
    return report


def render_execution_plan_markdown(plan: dict[str, Any]) -> str:
    lines = [
        "# Natural-event execution plan",
        "",
        f"Manifest SHA-256: `{plan['manifest_sha256']}`",
        f"Execution-plan SHA-256: `{plan['execution_plan_sha256']}`",
        "",
        f"- Selected anchors: {plan['selected_anchor_count']}",
        f"- Naive branches: {plan['naive_branch_count']}",
        f"- Shared trajectories: {plan['trajectory_count']}",
        f"- Deduplicated branches: {plan['deduplicated_branch_count']} "
        f"({plan['deduplication_fraction']:.1%})",
        f"- Common checkpoint boundary audit: "
        f"{bool(plan.get('diagnostics', {}).get('common_boundary_audit', False))}",
        f"- Event cohort endpoint audit: "
        f"{bool(plan.get('diagnostics', {}).get('event_cohort_audit', False))}",
        "",
        "| Trajectory | Checkpoint | Intervention | Until tick | Anchors |",
        "|---|---:|---|---:|---:|",
    ]
    for trajectory in plan["trajectories"]:
        lines.append(
            f"| {trajectory['trajectory_id']} | {trajectory['checkpoint_tick']} | "
            f"{trajectory['intervention_label']} | {trajectory['until_tick']} | "
            f"{len(trajectory['dependencies'])} |"
        )
    lines.extend(["", "## Pairing boundary", "", str(plan["pairing_boundary"]), ""])
    return "\n".join(lines)


def render_results_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Natural-event paired intervention results",
        "",
        f"Manifest SHA-256: `{report['manifest_sha256']}`",
        f"Execution-plan SHA-256: `{report['execution_plan_sha256']}`",
        "",
        f"Executed trajectories: {report['executed_trajectory_count']}",
        f"Resumed trajectories: {report['resumed_trajectory_count']}",
        f"Deduplicated branches: {report['deduplicated_branch_count']}",
        f"Common checkpoint boundary audit: "
        f"{bool(report.get('diagnostics', {}).get('common_boundary_audit', False))}",
        f"Event cohort endpoint audit: "
        f"{bool(report.get('diagnostics', {}).get('event_cohort_audit', False))}",
        "",
        "| Anchor | Intervention | Δ alive | Δ retained | Δ absent | Δ existing in | Δ born in | Δ common cohesion | Δ active roots |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    display_keys = (
        "final_alive_region",
        "final_event_cohort_retained_region",
        "final_event_cohort_absent",
        "final_existing_in_migrants_region",
        "final_post_event_born_region",
        "post_event_reference_cohesion_region",
        "final_active_transferred_roots_region",
    )
    for item in report["results"]:
        for branch in item["branches"]:
            if not branch["eligible"]:
                lines.append(
                    f"| {item['anchor']['anchor_id']} | {branch['intervention']} | "
                    "ineligible | — | — | — | — | — | — | — |"
                )
                continue
            values = []
            for key in display_keys:
                value = branch["delta"].get(key)
                values.append("—" if value is None else f"{float(value):+.5f}")
            lines.append(
                f"| {item['anchor']['anchor_id']} | {branch['intervention']} | "
                + " | ".join(values)
                + " |"
            )
    lines.extend(
        [
            "",
            "## Outcome audit",
            "",
            f"Common boundary observed: {report['outcome_audit']['common_boundary']['observed']}",
            f"Preferred cohesion metric: "
            f"`{report['outcome_audit']['common_boundary']['preferred_cohesion_metric']}`",
            f"Event cohort observed: {report['outcome_audit']['event_cohort']['observed']}",
            f"Endpoint balance valid: {report['outcome_audit']['event_cohort']['endpoint_balance_valid']}",
            "",
            *[f"- {warning}" for warning in report['outcome_audit']['warnings']],
            "",
            "## Seed-level directional aggregation",
            "",
            "| Event | Intervention | Metric | Seeds | Mean | + / − / 0 |",
            "|---|---|---|---:|---:|---:|",
        ]
    )
    for group in report["aggregation"]["groups"]:
        stat = group["seed_level"]
        mean = "—" if stat["mean"] is None else f"{float(stat['mean']):+.5f}"
        lines.append(
            f"| {group['event_kind']} | {group['intervention']} | {group['metric']} | "
            f"{stat['count']} | {mean} | {stat['positive']} / {stat['negative']} / {stat['zero']} |"
        )
    lines.extend(
        [
            "",
            "## Interpretation boundary",
            "",
            str(report["interpretation_boundary"]),
            "",
            str(report["aggregation"]["interpretation_boundary"]),
            "",
        ]
    )
    return "\n".join(lines)


def _split_csv(value: str | None) -> tuple[str, ...] | None:
    if value is None:
        return None
    values = tuple(item.strip() for item in value.split(",") if item.strip())
    return values or None


def _split_int_csv(value: str | None) -> tuple[int, ...] | None:
    values = _split_csv(value)
    return tuple(int(item) for item in values) if values is not None else None


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Preflight and execute a signed natural-event intervention manifest"
    )
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--manifest")
    source.add_argument(
        "--execution-plan",
        help="Execute an already signed v1/v2 execution plan without rebuilding filters",
    )
    parser.add_argument("--output", required=True)
    parser.add_argument(
        "--path-prefix",
        action="append",
        default=[],
        metavar="OLD=NEW",
        help="Remap absolute manifest paths; repeat for multiple roots",
    )
    parser.add_argument("--anchor-id", action="append")
    parser.add_argument("--seeds", help="Comma-separated seed filter")
    parser.add_argument("--event-kinds", help="Comma-separated event filter")
    parser.add_argument("--interventions", help="Comma-separated intervention filter")
    parser.add_argument("--execute", action="store_true")
    parser.add_argument(
        "--no-common-boundary-audit",
        action="store_true",
        help="Disable checkpoint-frozen common-boundary diagnostics",
    )
    parser.add_argument(
        "--no-event-cohort-audit",
        action="store_true",
        help="Disable stable-ID endpoint cohort decomposition",
    )
    parser.add_argument("--overwrite-existing", action="store_true")
    parser.add_argument(
        "--checkpoint-only-preflight",
        action="store_true",
        help="Permit execution when checkpoints verify but progress/config audit files are unavailable",
    )
    parser.add_argument("--backend", choices=("cpu", "gpu", "auto"), default="cpu")
    parser.add_argument(
        "--gpu-semantics-mode",
        choices=("strict-reference", "hybrid-accelerated"),
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    if args.execution_plan:
        filter_values = (
            args.path_prefix,
            args.anchor_id,
            args.seeds,
            args.event_kinds,
            args.interventions,
        )
        if any(filter_values) or args.no_common_boundary_audit or args.no_event_cohort_audit:
            raise ValueError(
                "path/filter/diagnostic options cannot modify a signed --execution-plan; "
                "rebuild it from --manifest instead"
            )
        plan = load_execution_plan(args.execution_plan)
    else:
        manifest = load_manifest(args.manifest)
        plan = build_execution_plan(
            manifest,
            path_prefixes=parse_path_prefixes(args.path_prefix),
            anchor_ids=args.anchor_id,
            seeds=_split_int_csv(args.seeds),
            event_kinds=_split_csv(args.event_kinds),
            interventions=_split_csv(args.interventions),
            common_boundary_audit=not args.no_common_boundary_audit,
            event_cohort_audit=not args.no_event_cohort_audit,
        )
    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=True)
    (output / "natural_event_execution_plan.json").write_text(
        json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (output / "natural_event_execution_plan.md").write_text(
        render_execution_plan_markdown(plan), encoding="utf-8"
    )
    preflight = preflight_execution_plan(plan)
    (output / "natural_event_execution_preflight.json").write_text(
        json.dumps(preflight, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    if args.execute:
        execute_plan(
            plan,
            output,
            backend=args.backend,
            gpu_semantics_mode=args.gpu_semantics_mode,
            overwrite_existing=args.overwrite_existing,
            require_full_audit=not args.checkpoint_only_preflight,
        )


if __name__ == "__main__":
    main()
