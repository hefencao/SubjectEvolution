"""Exposure-blind multi-seed planning for natural-event checkpoint interventions.

The planner consumes completed run directories.  It selects local scarcity,
crowding, and mortality-pressure peaks using exposure fields and feasibility
constraints only.  It does not read post-event cohesion, transfer, lineage, or
survival outcomes while choosing anchors.  Execution is optional and branches
all interventions from the same trusted pre-event checkpoint as the baseline.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from collections import Counter
from typing import Any, Iterable, Sequence

import numpy as np

from .interventions import ExperimentMode, resolve_intervention
from .local_event_counterfactual import _numeric_delta, _region_summary, _run_branch
from .long_run_analysis import load_progress
from .phase_counterfactual import discover_checkpoints
from .spatial_partition import (
    NORMALIZED_FIXED_COUNT_SCHEMA,
    SpatialRegionPartition,
)


LEGACY_SCHEMA = "natural-event-paired-intervention-matrix-v1"
SCHEMA = "natural-event-paired-intervention-matrix-v2"
RESULT_SCHEMA = "natural-event-paired-intervention-results-v1"
LEGACY_SELECTION_SCHEMA = "exposure-only-local-peak-selection-v1"
SELECTION_SCHEMA = "exposure-only-local-peak-selection-v2"
DEFAULT_EVENT_KINDS = ("scarcity", "crowding", "mortality")
DEFAULT_INTERVENTIONS = (
    "disable-knowledge-transfer",
    "disable-knowledge-policy",
    "ablate-working-memory",
    "bypass-sparse-selection",
    "freeze-group-refresh",
    "neutralize-resource-affinity",
    "neutralize-danger-evidence",
)
EVENT_FIELDS = {
    "scarcity": "spatial_local_region_resource_scarcity",
    "crowding": "spatial_local_region_crowding",
    "mortality": "spatial_local_region_mortality_pressure",
}
OUTCOME_FIELDS_EXCLUDED_FROM_SELECTION = (
    "spatial_local_region_boundary_cohesion",
    "spatial_local_region_new_transferred_roots",
    "spatial_local_region_lost_transferred_roots",
    "spatial_local_region_active_transferred_roots",
    "spatial_local_region_incoming_transfer_commits",
    "spatial_local_region_outgoing_transfer_commits",
    "effective_lineages",
    "largest_lineage_fraction",
    "window_action_entropy",
)


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _canonical_sha256(payload: dict[str, Any]) -> str:
    encoded = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _load_resolved_config(run_dir: Path) -> tuple[dict[str, Any], Path]:
    candidates = (
        run_dir / "resolved_config.json",
        run_dir / "config_resolved.json",
        run_dir / "config.json",
    )
    for path in candidates:
        if path.is_file():
            value = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(value, dict):
                raise ValueError(f"resolved configuration must be an object: {path}")
            return value, path
    raise FileNotFoundError(
        f"no resolved configuration found under {run_dir}; expected one of "
        "resolved_config.json, config_resolved.json, or config.json"
    )


def _nested(config: dict[str, Any], section: str, key: str, default: Any = None) -> Any:
    value = config.get(section, {})
    return value.get(key, default) if isinstance(value, dict) else default


def _partition_from_config_and_records(
    config: dict[str, Any], records: list[dict[str, Any]]
) -> tuple[SpatialRegionPartition, str, bool]:
    world = config.get("world", {}) if isinstance(config, dict) else {}
    run = config.get("run", {}) if isinstance(config, dict) else {}
    required = {"width", "height", "grid_x", "grid_y"}
    if isinstance(world, dict) and required.issubset(world):
        return (
            SpatialRegionPartition(
                world_width=float(world["width"]),
                world_height=float(world["height"]),
                world_grid_x=int(world["grid_x"]),
                world_grid_y=int(world["grid_y"]),
                regions_x=int(run.get("spatial_stress_regions_x", 4)),
                regions_y=int(run.get("spatial_stress_regions_y", 4)),
                schema=str(
                    run.get(
                        "spatial_stress_region_schema",
                        NORMALIZED_FIXED_COUNT_SCHEMA,
                    )
                ),
            ),
            "resolved-config",
            True,
        )
    # Compatibility for old/minimal analysis fixtures that predate spatial
    # geometry provenance. Only normalized topology can be recovered.
    alive = next(
        (record.get("spatial_local_region_alive") for record in records
         if record.get("spatial_local_region_alive") is not None),
        None,
    )
    count = len(alive) if isinstance(alive, list) and alive else 1
    root = int(round(count ** 0.5))
    regions_x = root if root * root == count else count
    regions_y = root if root * root == count else 1
    return (
        SpatialRegionPartition(
            world_width=float(regions_x),
            world_height=float(regions_y),
            world_grid_x=regions_x,
            world_grid_y=regions_y,
            regions_x=regions_x,
            regions_y=regions_y,
        ),
        "legacy-inferred-region-count-only",
        False,
    )


def discover_run_dirs(run_root: str | Path) -> tuple[Path, ...]:
    root = Path(run_root)
    if (root / "evolution_progress.jsonl").is_file():
        return (root,)
    found = tuple(
        path
        for path in sorted(root.iterdir())
        if path.is_dir() and (path / "evolution_progress.jsonl").is_file()
    )
    if not found:
        raise FileNotFoundError(
            f"no completed seed run directories with evolution_progress.jsonl under {root}"
        )
    return found


def _prior_checkpoint(target_tick: int, checkpoints: dict[int, Path]) -> tuple[int, Path]:
    candidates = [(tick, path) for tick, path in checkpoints.items() if tick < target_tick]
    if not candidates:
        raise ValueError(f"no full checkpoint exists before event tick {target_tick}")
    return max(candidates, key=lambda item: item[0])


def detect_exposure_events(
    records: list[dict[str, Any]],
    *,
    event_kind: str,
    quantile: float,
    max_events: int,
    min_tick: int | None,
    min_gap_windows: int,
    min_region_alive: int,
) -> list[dict[str, int | float]]:
    """Select local peaks without reading outcome fields.

    The only non-exposure filter is regional population, used to avoid anchors
    where a regional rate or subsequent branch comparison is numerically empty.
    """

    if event_kind not in EVENT_FIELDS:
        raise ValueError(f"unknown natural event kind {event_kind!r}")
    if not 0.5 <= quantile < 1.0:
        raise ValueError("event quantile must be in [0.5, 1.0)")
    if max_events <= 0:
        raise ValueError("max_events must be positive")
    if min_gap_windows < 1:
        raise ValueError("min_gap_windows must be positive")
    if min_region_alive < 1:
        raise ValueError("min_region_alive must be positive")

    field = EVENT_FIELDS[event_kind]
    usable = [record for record in records if record.get(field) is not None]
    if len(usable) < 5:
        raise ValueError(f"{event_kind} selection requires at least five spatial windows")
    ticks = np.asarray([int(record["tick"]) for record in usable], dtype=np.int64)
    values = np.asarray([record[field] for record in usable], dtype=np.float64)
    if values.ndim != 2:
        raise ValueError(f"{field} must be a window×region array")
    alive_rows = [record.get("spatial_local_region_alive") for record in usable]
    if all(value is not None for value in alive_rows):
        alive = np.asarray(alive_rows, dtype=np.float64)
        if alive.shape != values.shape:
            raise ValueError("regional alive arrays must match exposure arrays")
    else:
        alive = np.full(values.shape, np.inf, dtype=np.float64)
    cutoff = int(min_tick) if min_tick is not None else int(ticks[0])

    candidates: list[dict[str, int | float]] = []
    for region in range(values.shape[1]):
        series = values[:, region]
        valid = (
            np.isfinite(series)
            & (ticks >= cutoff)
            & (alive[:, region] >= float(min_region_alive))
        )
        sample = series[valid]
        if sample.size < 5:
            continue
        std = float(np.std(sample))
        if std == 0.0:
            continue
        threshold = float(np.quantile(sample, quantile))
        mean = float(np.mean(sample))
        last_selected_index = -10**9
        for index in range(1, values.shape[0] - 1):
            if not valid[index] or index - last_selected_index < min_gap_windows:
                continue
            value = float(series[index])
            if (
                value >= threshold
                and value >= float(series[index - 1])
                and value > float(series[index + 1])
            ):
                candidates.append(
                    {
                        "record_index": int(index),
                        "region_id": int(region),
                        "event_tick": int(ticks[index]),
                        "event_value": value,
                        "region_threshold": threshold,
                        "standardized_score": (value - mean) / std,
                        "alive_region": int(alive[index, region]),
                    }
                )
                last_selected_index = index

    candidates.sort(
        key=lambda item: (
            -float(item["standardized_score"]),
            int(item["event_tick"]),
            int(item["region_id"]),
        )
    )
    region_candidate_counts = Counter(int(item["region_id"]) for item in candidates)
    for rank, item in enumerate(candidates, start=1):
        item["candidate_rank"] = int(rank)
        item["run_candidate_count"] = int(len(candidates))
        item["region_candidate_count"] = int(
            region_candidate_counts[int(item["region_id"])]
        )
    selected: list[dict[str, int | float]] = []
    used_regions: set[int] = set()
    for item in candidates:
        region = int(item["region_id"])
        if region in used_regions and len(used_regions) < values.shape[1]:
            continue
        selected_item = dict(item)
        selected_item["selection_rank"] = int(len(selected) + 1)
        selected.append(selected_item)
        used_regions.add(region)
        if len(selected) >= max_events:
            break
    if not selected:
        raise ValueError(f"no {event_kind} peak crossed the configured quantile")
    return selected


def _intervention_eligibility(
    name: str,
    *,
    config: dict[str, Any],
    checkpoint_record: dict[str, Any],
) -> tuple[bool, str | None]:
    if name == "disable-knowledge-transfer":
        enabled = bool(_nested(config, "knowledge", "enabled", False))
        probability = float(_nested(config, "knowledge", "transfer_probability", 0.0))
        if not enabled or probability <= 0.0:
            return False, "knowledge transfer is disabled by configuration"
        if int(checkpoint_record.get("knowledge_transfer_committed_total", 0)) <= 0:
            return False, "no committed transfer exists before the checkpoint"
        return True, None
    if name == "disable-knowledge-policy":
        return (
            (True, None)
            if bool(_nested(config, "knowledge", "policy_influence_enabled", False))
            else (False, "knowledge policy influence is disabled")
        )
    if name == "ablate-working-memory":
        return (
            (True, None)
            if bool(_nested(config, "knowledge", "working_memory_enabled", False))
            else (False, "working memory is disabled")
        )
    if name == "bypass-sparse-selection":
        return (
            (True, None)
            if bool(_nested(config, "knowledge", "sparse_selection_enabled", False))
            else (False, "sparse selection is disabled")
        )
    if name == "neutralize-resource-affinity":
        schema = str(_nested(config, "entities", "resource_affinity_schema", "disabled"))
        return (
            (True, None)
            if schema == "normalized-four-resource-affinity-v1"
            else (False, f"resource affinity schema is {schema!r}")
        )
    if name == "neutralize-danger-evidence":
        schema = str(_nested(config, "entities", "danger_evidence_schema", "disabled"))
        return (
            (True, None)
            if schema == "inherited-direct-trace-mixture-v1"
            else (False, f"danger evidence schema is {schema!r}")
        )
    if name == "freeze-group-refresh":
        mode = str(_nested(config, "social", "group_update_mode", "periodic-v1"))
        if int(checkpoint_record.get("group_update_count_total", 0)) <= 0:
            return False, "no group refresh has completed before the checkpoint"
        return True, None if mode else "group refresh mode is unavailable"
    return True, None


def _normalize_names(values: Iterable[str], *, event_kinds: bool = False) -> tuple[str, ...]:
    result: list[str] = []
    for raw in values:
        name = raw.strip().lower().replace("_", "-")
        if not name:
            continue
        if event_kinds:
            if name not in EVENT_FIELDS:
                raise ValueError(f"unknown event kind {name!r}")
        else:
            spec = resolve_intervention(name)
            spec.require_mode(ExperimentMode.SCIENTIFIC)
            name = spec.name
        if name not in result:
            result.append(name)
    if not result:
        raise ValueError("at least one value is required")
    return tuple(result)


def _nearest_record(records: list[dict[str, Any]], tick: int) -> dict[str, Any]:
    return min(records, key=lambda record: abs(int(record["tick"]) - int(tick)))


def _analysis_context(path: str | Path | None) -> dict[str, Any] | None:
    if path is None:
        return None
    source = Path(path)
    payload = json.loads(source.read_text(encoding="utf-8"))
    schema = str(payload.get("schema", ""))
    if not schema.startswith("multi-seed-long-run-analysis-v"):
        raise ValueError(f"unsupported analysis schema {schema!r}")
    return {
        "path": str(source.resolve()),
        "sha256": _sha256_file(source),
        "schema": schema,
        "run_count": int(payload.get("run_count", 0)),
        "repeated_local_directional_patterns": list(
            payload.get("repeated_local_directional_patterns", [])
        ),
        "used_for_anchor_selection": False,
        "role": "rationale-and-audit-only",
    }


def build_manifest(
    run_dirs: Sequence[str | Path],
    *,
    event_kinds: Iterable[str] = DEFAULT_EVENT_KINDS,
    quantile: float = 0.80,
    max_events_per_kind: int = 2,
    min_tick: int | None = None,
    min_gap_windows: int = 2,
    min_region_alive: int = 5,
    horizon_ticks: int = 120,
    interventions: Iterable[str] = DEFAULT_INTERVENTIONS,
    analysis_json: str | Path | None = None,
    allow_mixed_region_partitions: bool = False,
) -> dict[str, Any]:
    normalized_kinds = _normalize_names(event_kinds, event_kinds=True)
    normalized_interventions = _normalize_names(interventions)
    anchors: list[dict[str, Any]] = []
    source_runs: list[dict[str, Any]] = []

    for run_value in run_dirs:
        run_dir = Path(run_value)
        progress_path = run_dir / "evolution_progress.jsonl"
        records = load_progress(progress_path)
        config, config_path = _load_resolved_config(run_dir)
        checkpoints = discover_checkpoints(run_dir)
        partition, partition_source, physical_geometry_known = (
            _partition_from_config_and_records(config, records)
        )
        partition_metadata = partition.metadata()
        partition_metadata["geometry_source"] = partition_source
        partition_metadata["physical_geometry_known"] = physical_geometry_known
        partition_topology = partition.normalized_topology()
        seed = int(_nested(config, "run", "seed", 0))
        run_name = run_dir.name
        source_runs.append(
            {
                "run_name": run_name,
                "seed": seed,
                "run_dir": str(run_dir.resolve()),
                "progress_path": str(progress_path.resolve()),
                "progress_sha256": _sha256_file(progress_path),
                "config_path": str(config_path.resolve()),
                "config_sha256": _sha256_file(config_path),
                "final_tick": int(records[-1]["tick"]),
                "record_count": len(records),
                "region_partition": partition_metadata,
                "region_topology": partition_topology,
            }
        )
        usable_by_kind = {
            kind: [record for record in records if record.get(EVENT_FIELDS[kind]) is not None]
            for kind in normalized_kinds
        }
        for kind in normalized_kinds:
            selected = detect_exposure_events(
                records,
                event_kind=kind,
                quantile=quantile,
                max_events=max_events_per_kind,
                min_tick=min_tick,
                min_gap_windows=min_gap_windows,
                min_region_alive=min_region_alive,
            )
            usable = usable_by_kind[kind]
            for event in selected:
                index = int(event["record_index"])
                record = usable[index]
                event_tick = int(event["event_tick"])
                checkpoint_tick, checkpoint_path = _prior_checkpoint(
                    event_tick, checkpoints
                )
                checkpoint_record = _nearest_record(records, checkpoint_tick)
                eligibility = []
                for intervention in normalized_interventions:
                    eligible, reason = _intervention_eligibility(
                        intervention,
                        config=config,
                        checkpoint_record=checkpoint_record,
                    )
                    eligibility.append(
                        {
                            "intervention": intervention,
                            "eligible": bool(eligible),
                            "reason": reason,
                        }
                    )
                region = int(event["region_id"])
                anchors.append(
                    {
                        "anchor_id": f"{run_name}-{kind}-r{region}-t{event_tick}",
                        "run_name": run_name,
                        "seed": seed,
                        "run_dir": str(run_dir.resolve()),
                        "event_kind": kind,
                        "exposure_field": EVENT_FIELDS[kind],
                        "region_id": region,
                        "region_bounds": partition.region_bounds(region),
                        "region_partition_sha256": partition_metadata[
                            "partition_sha256"
                        ],
                        "event_tick": event_tick,
                        "event_value": float(event["event_value"]),
                        "region_threshold": float(event["region_threshold"]),
                        "standardized_score": float(event["standardized_score"]),
                        "candidate_rank": int(event["candidate_rank"]),
                        "selection_rank": int(event["selection_rank"]),
                        "run_candidate_count": int(event["run_candidate_count"]),
                        "region_candidate_count": int(event["region_candidate_count"]),
                        "alive_region": int(event["alive_region"]),
                        "checkpoint_tick": int(checkpoint_tick),
                        "checkpoint_path": str(checkpoint_path.resolve()),
                        "checkpoint_sha256": _sha256_file(checkpoint_path),
                        "until_tick": event_tick + int(horizon_ticks),
                        "selection_record_index": index,
                        "interventions": eligibility,
                    }
                )

    anchors.sort(
        key=lambda item: (
            int(item["seed"]),
            str(item["event_kind"]),
            int(item["event_tick"]),
            int(item["region_id"]),
        )
    )
    topology_hashes = sorted(
        {str(item["region_topology"]["topology_sha256"]) for item in source_runs}
    )
    partition_hashes = sorted(
        {str(item["region_partition"]["partition_sha256"]) for item in source_runs}
    )
    physical_geometry_known = all(
        bool(item["region_partition"].get("physical_geometry_known", False))
        for item in source_runs
    )
    if len(topology_hashes) != 1:
        raise ValueError(
            "source runs use different normalized region topologies; region IDs are not comparable"
        )
    if (
        physical_geometry_known
        and len(partition_hashes) != 1
        and not allow_mixed_region_partitions
    ):
        raise ValueError(
            "source runs use different physical region geometry or world-grid resolution; "
            "pass allow_mixed_region_partitions=True only for an explicitly non-scale-comparable audit"
        )
    payload: dict[str, Any] = {
        "schema": SCHEMA,
        "selection_schema": SELECTION_SCHEMA,
        "selection_protocol": {
            "event_kinds": list(normalized_kinds),
            "event_quantile": float(quantile),
            "max_events_per_kind_per_run": int(max_events_per_kind),
            "min_tick": min_tick,
            "min_gap_windows": int(min_gap_windows),
            "min_region_alive": int(min_region_alive),
            "selection_inputs": [
                "tick",
                "spatial_local_region_alive",
                *[EVENT_FIELDS[kind] for kind in normalized_kinds],
                "checkpoint availability",
            ],
            "outcome_fields_excluded": list(OUTCOME_FIELDS_EXCLUDED_FROM_SELECTION),
            "post_event_outcomes_used_for_selection": False,
            "analysis_summary_used_for_selection": False,
            "candidate_rule": (
                "per-region within-run quantile threshold; interior local maximum; "
                "minimum window gap enforced independently within each region"
            ),
            "ranking_rule": (
                "descending within-region z-score, then earlier tick, then lower region ID"
            ),
            "region_diversity_rule": (
                "prefer distinct regions until max_events is reached; repeated regions are "
                "allowed only after every candidate-bearing region has been represented"
            ),
            "cross_event_score_comparability": False,
        },
        "region_partition_audit": {
            "policy": (
                "strict-physical-geometry-v1"
                if not allow_mixed_region_partitions
                else "explicit-mixed-geometry-audit-v1"
            ),
            "normalized_topology_sha256": topology_hashes[0],
            "partition_sha256_values": partition_hashes,
            "physical_geometry_known": physical_geometry_known,
            "cross_run_spatial_scale_comparable": (
                physical_geometry_known and len(partition_hashes) == 1
            ),
            "interpretation": (
                "Region IDs are row-major cells in a fixed-count normalized grid. "
                "Changing map width/height changes physical region area; changing world-grid "
                "resolution changes represented physical-cell count. Mixed geometry is rejected "
                "by default."
            ),
        },
        "paired_randomness": True,
        "baseline_and_intervention_share_checkpoint": True,
        "horizon_ticks": int(horizon_ticks),
        "source_runs": source_runs,
        "analysis_context": _analysis_context(analysis_json),
        "anchors": anchors,
        "interpretation_boundary": (
            "Anchor selection is exposure-blind with respect to recorded outcomes, but the "
            "events are naturally occurring rather than randomized. Paired checkpoint branches "
            "identify short-horizon mechanism effects conditional on the selected events; they "
            "do not prove that the event exposure itself caused the observed world trajectory."
        ),
    }
    payload["plan_sha256"] = _canonical_sha256(payload)
    return payload


def validate_manifest(payload: dict[str, Any]) -> None:
    schema = payload.get("schema")
    selection_schema = payload.get("selection_schema")
    if schema not in {LEGACY_SCHEMA, SCHEMA}:
        raise ValueError(f"unsupported natural-event manifest schema {schema!r}")
    expected = str(payload.get("plan_sha256", ""))
    unsigned = dict(payload)
    unsigned.pop("plan_sha256", None)
    actual = _canonical_sha256(unsigned)
    if expected != actual:
        raise ValueError("natural-event manifest checksum mismatch")
    expected_selection = (
        LEGACY_SELECTION_SCHEMA if schema == LEGACY_SCHEMA else SELECTION_SCHEMA
    )
    if selection_schema != expected_selection:
        raise ValueError(
            f"natural-event manifest selection schema mismatch: {selection_schema!r}"
        )


def load_manifest(path: str | Path) -> dict[str, Any]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("natural-event manifest must be a JSON object")
    validate_manifest(payload)
    return payload


def execute_manifest(
    manifest: dict[str, Any],
    output_dir: str | Path,
    *,
    backend: str = "cpu",
    gpu_semantics_mode: str | None = None,
) -> dict[str, Any]:
    validate_manifest(manifest)
    root = Path(output_dir)
    root.mkdir(parents=True, exist_ok=True)
    results: list[dict[str, Any]] = []
    for anchor in manifest["anchors"]:
        anchor_dir = root / str(anchor["anchor_id"])
        baseline = _run_branch(
            anchor["checkpoint_path"],
            anchor_dir / "baseline",
            until_tick=int(anchor["until_tick"]),
            backend=backend,
            gpu_semantics_mode=gpu_semantics_mode,
            intervention=None,
        )
        baseline_region = _region_summary(
            baseline["records"],
            region=int(anchor["region_id"]),
            event_tick=int(anchor["event_tick"]),
        )
        branches: list[dict[str, Any]] = []
        for entry in anchor["interventions"]:
            if not bool(entry["eligible"]):
                branches.append(
                    {
                        "intervention": entry["intervention"],
                        "eligible": False,
                        "reason": entry["reason"],
                        "region_summary": {},
                        "delta": {},
                    }
                )
                continue
            branch = _run_branch(
                anchor["checkpoint_path"],
                anchor_dir / str(entry["intervention"]),
                until_tick=int(anchor["until_tick"]),
                backend=backend,
                gpu_semantics_mode=gpu_semantics_mode,
                intervention=str(entry["intervention"]),
            )
            region_summary = _region_summary(
                branch["records"],
                region=int(anchor["region_id"]),
                event_tick=int(anchor["event_tick"]),
            )
            branches.append(
                {
                    "intervention": entry["intervention"],
                    "eligible": True,
                    "reason": None,
                    "region_summary": region_summary,
                    "delta": _numeric_delta(region_summary, baseline_region),
                    "scientific_validity": branch["scientific_validity"],
                    "intervention_history": branch["intervention_history"],
                }
            )
        results.append(
            {
                "anchor": anchor,
                "baseline_region_summary": baseline_region,
                "baseline_scientific_validity": baseline["scientific_validity"],
                "branches": branches,
            }
        )
    report = {
        "schema": RESULT_SCHEMA,
        "manifest_schema": manifest["schema"],
        "manifest_sha256": manifest["plan_sha256"],
        "backend": backend,
        "gpu_semantics_mode": gpu_semantics_mode,
        "paired_randomness": True,
        "results": results,
        "interpretation_boundary": manifest["interpretation_boundary"],
    }
    (root / "natural_event_matrix_results.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (root / "natural_event_matrix_results.md").write_text(
        render_results_markdown(report), encoding="utf-8"
    )
    return report


def render_manifest_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# Natural-event paired intervention matrix",
        "",
        f"Schema: `{payload['schema']}`",
        f"Plan SHA-256: `{payload['plan_sha256']}`",
        f"Selection: `{payload['selection_schema']}`",
        "",
        "> Anchors are selected from exposure fields only; post-event outcome fields are excluded.",
        "",
        "| Anchor | Seed | Event | Region | Tick | Checkpoint | z-score | Eligible interventions |",
        "|---|---:|---|---:|---:|---:|---:|---|",
    ]
    for anchor in payload["anchors"]:
        eligible = [
            item["intervention"]
            for item in anchor["interventions"]
            if item["eligible"]
        ]
        lines.append(
            f"| {anchor['anchor_id']} | {anchor['seed']} | {anchor['event_kind']} | "
            f"{anchor['region_id']} | {anchor['event_tick']} | {anchor['checkpoint_tick']} | "
            f"{anchor['standardized_score']:.3f} | {', '.join(eligible) or 'none'} |"
        )
    lines.extend(
        [
            "",
            "## Selection boundary",
            "",
            payload["interpretation_boundary"],
            "",
            "Excluded outcome fields:",
            "",
        ]
    )
    lines.extend(
        f"- `{name}`"
        for name in payload["selection_protocol"]["outcome_fields_excluded"]
    )
    return "\n".join(lines) + "\n"


def render_results_markdown(report: dict[str, Any]) -> str:
    keys = (
        "final_alive_region",
        "final_cohesion_region",
        "post_event_incoming_commits",
        "post_event_outgoing_commits",
        "final_active_transferred_roots_region",
    )
    lines = [
        "# Natural-event paired intervention results",
        "",
        f"Manifest SHA-256: `{report['manifest_sha256']}`",
        "",
        "| Anchor | Intervention | Δ alive | Δ cohesion | Δ incoming | Δ outgoing | Δ active roots |",
        "|---|---|---:|---:|---:|---:|---:|",
    ]
    for item in report["results"]:
        for branch in item["branches"]:
            if not branch["eligible"]:
                lines.append(
                    f"| {item['anchor']['anchor_id']} | {branch['intervention']} | ineligible | — | — | — | — |"
                )
                continue
            formatted = []
            for key in keys:
                value = branch["delta"].get(key)
                formatted.append("—" if value is None else f"{float(value):+.5f}")
            lines.append(
                f"| {item['anchor']['anchor_id']} | {branch['intervention']} | "
                + " | ".join(formatted)
                + " |"
            )
    lines.extend(["", "## Interpretation boundary", "", report["interpretation_boundary"], ""])
    return "\n".join(lines)


def _split_csv(value: str) -> tuple[str, ...]:
    return tuple(item.strip() for item in value.split(",") if item.strip())


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Build or execute an exposure-blind multi-seed natural-event intervention matrix"
    )
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--run-root")
    source.add_argument("--run-dir", action="append")
    parser.add_argument("--output", required=True)
    parser.add_argument("--analysis-json")
    parser.add_argument("--event-kinds", default=",".join(DEFAULT_EVENT_KINDS))
    parser.add_argument("--event-quantile", type=float, default=0.80)
    parser.add_argument(
        "--allow-mixed-region-partitions",
        action="store_true",
        help="Allow source runs with different physical region geometry; marks scale comparison invalid",
    )
    parser.add_argument("--events-per-kind", type=int, default=2)
    parser.add_argument("--min-tick", type=int)
    parser.add_argument("--min-gap-windows", type=int, default=2)
    parser.add_argument("--min-region-alive", type=int, default=5)
    parser.add_argument("--horizon", type=int, default=120)
    parser.add_argument("--interventions", default=",".join(DEFAULT_INTERVENTIONS))
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--backend", choices=("cpu", "gpu", "auto"), default="cpu")
    parser.add_argument(
        "--gpu-semantics-mode",
        choices=("strict-reference", "hybrid-accelerated"),
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    run_dirs = (
        discover_run_dirs(args.run_root)
        if args.run_root
        else tuple(Path(value) for value in args.run_dir)
    )
    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=True)
    manifest = build_manifest(
        run_dirs,
        event_kinds=_split_csv(args.event_kinds),
        quantile=args.event_quantile,
        max_events_per_kind=args.events_per_kind,
        min_tick=args.min_tick,
        min_gap_windows=args.min_gap_windows,
        min_region_alive=args.min_region_alive,
        horizon_ticks=args.horizon,
        interventions=_split_csv(args.interventions),
        analysis_json=args.analysis_json,
        allow_mixed_region_partitions=args.allow_mixed_region_partitions,
    )
    manifest_path = output / "natural_event_matrix_manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (output / "natural_event_matrix_manifest.md").write_text(
        render_manifest_markdown(manifest), encoding="utf-8"
    )
    if args.execute:
        execute_manifest(
            manifest,
            output,
            backend=args.backend,
            gpu_semantics_mode=args.gpu_semantics_mode,
        )


if __name__ == "__main__":
    main()
