"""Offline, non-causal analysis for periodic evolution_progress JSONL files."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any, Iterable

import numpy as np

from se import __version__
from se.env.partition import NORMALIZED_FIXED_COUNT_SCHEMA, SpatialRegionPartition


MIN_CORRELATION_SAMPLES = 5
MIN_PARTIAL_SAMPLES = 8


def load_progress(path: str | Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    with Path(path).open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            value = json.loads(line)
            if not isinstance(value, dict) or "tick" not in value:
                raise ValueError(f"{path}:{line_number} is not an evolution record")
            records.append(value)
    records.sort(key=lambda item: int(item["tick"]))
    return records


def _pearson(x: Iterable[float], y: Iterable[float]) -> float | None:
    a = np.asarray(list(x), dtype=np.float64)
    b = np.asarray(list(y), dtype=np.float64)
    valid = np.isfinite(a) & np.isfinite(b)
    a = a[valid]
    b = b[valid]
    if (
        a.size < MIN_CORRELATION_SAMPLES
        or float(np.std(a)) == 0.0
        or float(np.std(b)) == 0.0
    ):
        return None
    return float(np.corrcoef(a, b)[0, 1])


def _partial_pearson(
    x: Iterable[float],
    y: Iterable[float],
    controls: Iterable[Iterable[float]],
) -> float | None:
    a = np.asarray(list(x), dtype=np.float64)
    b = np.asarray(list(y), dtype=np.float64)
    control_columns = [np.asarray(list(column), dtype=np.float64) for column in controls]
    if any(column.shape != a.shape for column in control_columns) or b.shape != a.shape:
        raise ValueError("partial-correlation arrays must have matching shapes")
    valid = np.isfinite(a) & np.isfinite(b)
    for column in control_columns:
        valid &= np.isfinite(column)
    a = a[valid]
    b = b[valid]
    matrix = np.column_stack([column[valid] for column in control_columns])
    if a.size < MIN_PARTIAL_SAMPLES:
        return None
    # Intercept plus standardized controls keeps tick magnitude numerically tame.
    standardized: list[np.ndarray] = []
    for column in matrix.T:
        std = float(np.std(column))
        standardized.append(
            np.zeros_like(column) if std == 0.0 else (column - column.mean()) / std
        )
    design = np.column_stack([np.ones(a.size), *standardized])
    residual_a = a - design @ np.linalg.lstsq(design, a, rcond=None)[0]
    residual_b = b - design @ np.linalg.lstsq(design, b, rcond=None)[0]
    return _pearson(residual_a, residual_b)


def _slope_per_1000_ticks(ticks: np.ndarray, values: np.ndarray) -> float | None:
    valid = np.isfinite(ticks) & np.isfinite(values)
    x = ticks[valid]
    y = values[valid]
    if x.size < MIN_CORRELATION_SAMPLES or float(np.std(x)) == 0.0:
        return None
    centered = x - x.mean()
    slope = float(np.dot(centered, y - y.mean()) / np.dot(centered, centered))
    return slope * 1000.0


def _cross_lag_correlations(
    x: np.ndarray,
    y: np.ndarray,
    *,
    max_lag: int = 3,
) -> dict[str, float | None]:
    """Return correlations where positive lag means x leads y by that many windows."""
    result: dict[str, float | None] = {}
    for lag in range(-max_lag, max_lag + 1):
        if lag > 0:
            left, right = x[:-lag], y[lag:]
        elif lag < 0:
            left, right = x[-lag:], y[:lag]
        else:
            left, right = x, y
        result[str(lag)] = _pearson(left, right)
    return result


def _best_lag(values: dict[str, float | None]) -> dict[str, float | int] | None:
    available = [(int(key), value) for key, value in values.items() if value is not None]
    if not available:
        return None
    lag, value = max(available, key=lambda item: abs(float(item[1])))
    return {"lag_windows": lag, "correlation": float(value)}


def _array(records: list[dict[str, Any]], key: str) -> np.ndarray:
    return np.asarray([record.get(key, math.nan) for record in records], dtype=np.float64)



def _matrix_effective_dimensions(values: np.ndarray) -> float:
    matrix = np.asarray(values, dtype=np.float64)
    if matrix.ndim != 2 or matrix.shape[0] <= 1 or matrix.shape[1] == 0:
        return 0.0
    std = matrix.std(axis=0)
    active = std > 1e-12
    if not np.any(active):
        return 0.0
    standardized = (matrix[:, active] - matrix[:, active].mean(axis=0)) / std[active]
    covariance = np.atleast_2d(np.cov(standardized, rowvar=False))
    eigenvalues = np.clip(np.linalg.eigvalsh(covariance), 0.0, None)
    total = float(eigenvalues.sum())
    squared = float(np.square(eigenvalues).sum())
    return 0.0 if total <= 0.0 or squared <= 0.0 else total * total / squared


def _resource_demand_analysis(
    records: list[dict[str, Any]], config_context: dict[str, Any]
) -> dict[str, Any]:
    rows: list[np.ndarray] = []
    field_dimensions: list[float] = []
    balance: list[float] = []
    extraction_efficiency: list[float] = []
    for record in records:
        value = np.asarray(record.get("harvested_resources_window", ()), dtype=np.float64)
        if value.shape != (4,) or np.any(~np.isfinite(value)):
            continue
        rows.append(value)
        total = float(value.sum())
        if total > 0.0:
            share = value / total
            balance.append(float(1.0 / max(float(np.square(share).sum()), 1e-30)))
        else:
            balance.append(math.nan)
        field_dimensions.append(
            float(record.get("environment_resource_effective_dimensions", math.nan))
        )
        action_names = list(record.get("action_names", ()))
        action_counts = list(record.get("window_action_counts", ()))
        try:
            harvest_index = action_names.index("HARVEST")
            harvest_actions = int(action_counts[harvest_index])
        except (ValueError, IndexError, TypeError):
            harvest_actions = 0
        request_budget = float(config_context.get("harvest_request_budget", math.nan))
        requested_total = harvest_actions * request_budget
        extraction_efficiency.append(
            total / requested_total
            if requested_total > 0.0 and math.isfinite(requested_total)
            else math.nan
        )
    if not rows:
        return {"available": False, "reason": "harvested_resources_window missing"}
    matrix = np.vstack(rows)
    totals = matrix.sum(axis=0)
    grand_total = float(totals.sum())
    shares = totals / grand_total if grand_total > 0.0 else np.zeros(4, dtype=np.float64)
    active_columns = matrix.std(axis=0) > 1e-12
    correlation = np.eye(4, dtype=np.float64)
    if np.count_nonzero(active_columns) >= 2:
        sub = np.corrcoef(matrix[:, active_columns], rowvar=False)
        correlation[np.ix_(active_columns, active_columns)] = sub
    off_diagonal = np.abs(correlation[~np.eye(4, dtype=bool)])
    return {
        "available": True,
        "window_count": int(matrix.shape[0]),
        "harvest_channel_totals": totals.tolist(),
        "harvest_channel_shares": shares.tolist(),
        "harvest_balance_effective_count": (
            float(1.0 / max(float(np.square(shares).sum()), 1e-30))
            if grand_total > 0.0
            else 0.0
        ),
        "harvest_temporal_effective_dimensions": _matrix_effective_dimensions(matrix),
        "harvest_channel_correlation": correlation.tolist(),
        "harvest_channel_mean_abs_correlation": float(off_diagonal.mean()),
        "harvest_channel_max_abs_correlation": float(off_diagonal.max(initial=0.0)),
        "harvest_balance_vs_resource_environment_dimensions": _pearson(
            balance, field_dimensions
        ),
        "harvest_extraction_efficiency_mean": (
            float(np.nanmean(extraction_efficiency))
            if np.any(np.isfinite(extraction_efficiency))
            else None
        ),
        "harvest_extraction_efficiency_final": (
            float(np.asarray(extraction_efficiency, dtype=np.float64)[
                np.flatnonzero(np.isfinite(extraction_efficiency))[-1]
            ])
            if np.any(np.isfinite(extraction_efficiency))
            else None
        ),
        "interpretation": (
            "Harvest demand metrics describe realized extraction, not fitness or causal "
            "niche differentiation. Selective acquisition must be paired with phenotype "
            "neutralization or shared-checkpoint branches for causal claims."
        ),
    }

def _resolved_config_context(path: str | Path) -> dict[str, Any]:
    progress = Path(path)
    resolved = progress.parent / "resolved_config.json"
    if not resolved.is_file():
        return {}
    try:
        config = json.loads(resolved.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    knowledge = config.get("knowledge", {}) if isinstance(config, dict) else {}
    environment = config.get("environment", {}) if isinstance(config, dict) else {}
    entities = config.get("entities", {}) if isinstance(config, dict) else {}
    run = config.get("run", {}) if isinstance(config, dict) else {}
    social = config.get("social", {}) if isinstance(config, dict) else {}
    differentiation = config.get("differentiation", {}) if isinstance(config, dict) else {}
    world = config.get("world", {}) if isinstance(config, dict) else {}
    manifest_path = progress.parent / "run_manifest.json"
    manifest: dict[str, Any] = {}
    if manifest_path.is_file():
        try:
            loaded = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest = loaded if isinstance(loaded, dict) else {}
        except (OSError, json.JSONDecodeError):
            manifest = {}
    configured_process_schema = environment.get(
        "environment_process_schema", "disabled"
    )
    legacy_moving_schema = environment.get("moving_hazard_schema", "disabled")
    if configured_process_schema != "disabled":
        resolved_process_schema = configured_process_schema
        resolved_process_origin = "generic-plugin-config"
        process_parameters = environment.get("environment_process_parameters", {})
    elif legacy_moving_schema != "disabled":
        resolved_process_schema = legacy_moving_schema
        resolved_process_origin = "v0.22-moving-hazard-adapter"
        process_parameters = {
            "source_count": environment.get("moving_hazard_source_count", 0),
            "amplitude": environment.get("moving_hazard_amplitude", 0.0),
            "radius": environment.get("moving_hazard_radius", 0.12),
            "speed": environment.get("moving_hazard_speed", 0.0),
            "phase_offset": environment.get("moving_hazard_phase_offset", 0.0),
        }
    else:
        resolved_process_schema = "disabled"
        resolved_process_origin = "core-disabled"
        process_parameters = {}
    manifest_process = manifest.get("environment_process", {})
    if not isinstance(manifest_process, dict):
        manifest_process = {}
    spatial_partition: dict[str, Any] | None = None
    try:
        if run.get("spatial_stress_diagnostics_enabled", False):
            spatial_partition = SpatialRegionPartition(
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
            ).metadata()
    except (KeyError, TypeError, ValueError):
        spatial_partition = None
    return {
        "knowledge_transfer_probability": knowledge.get("transfer_probability"),
        "knowledge_transfer_period": knowledge.get("transfer_period"),
        "environment_schema": environment.get("schema"),
        "resource_cycle_periods": environment.get("resource_cycle_periods"),
        "resource_cycle_amplitudes": environment.get("resource_cycle_amplitudes"),
        "resource_primary_wave_vectors": environment.get("resource_primary_wave_vectors"),
        "resource_secondary_wave_vectors": environment.get("resource_secondary_wave_vectors"),
        "resource_primary_wave_amplitudes": environment.get("resource_primary_wave_amplitudes"),
        "resource_secondary_wave_amplitudes": environment.get("resource_secondary_wave_amplitudes"),
        "resource_diffusion_rates": environment.get("resource_diffusion_rates"),
        "resource_effect_matrix": environment.get("resource_effect_matrix"),
        "environment_process_schema": manifest_process.get(
            "schema", resolved_process_schema
        ),
        "environment_process_origin": manifest_process.get(
            "origin", resolved_process_origin
        ),
        "environment_process_mechanism_class": manifest_process.get(
            "mechanism_class", "unknown" if resolved_process_schema != "disabled" else "none"
        ),
        "environment_process_interpretation": manifest_process.get(
            "interpretation",
            "unknown-extension" if resolved_process_schema != "disabled" else "scientific-core-only",
        ),
        "environment_process_parameter_names": sorted(process_parameters)
        if isinstance(process_parameters, dict)
        else [],
        "moving_hazard_schema": environment.get("moving_hazard_schema", "disabled"),
        "moving_hazard_source_count": environment.get("moving_hazard_source_count", 0),
        "mortality_trace_schema": environment.get("mortality_trace_schema", "disabled"),
        "resource_affinity_schema": entities.get("resource_affinity_schema"),
        "harvest_allocation_schema": entities.get(
            "harvest_allocation_schema", "uniform-channel-rates-v1"
        ),
        "harvest_rate": entities.get("harvest_rate"),
        "harvest_channel_multipliers": environment.get(
            "harvest_channel_multipliers", [1.0, 1.0, 1.0, 1.0]
        ),
        "harvest_request_budget": (
            float(entities.get("harvest_rate", 0.0))
            * float(sum(environment.get("harvest_channel_multipliers", [1.0, 1.0, 1.0, 1.0])))
        ),
        "danger_evidence_schema": entities.get("danger_evidence_schema", "disabled"),
        "group_label_schema": social.get(
            "group_label_schema", "trusted-directed-fixed-round-min-label-v1"
        ),
        "group_label_propagation_rounds": social.get(
            "group_label_propagation_rounds", 8
        ),
        "group_trust_threshold": social.get("trust_group_threshold"),
        "group_min_members": social.get("group_min_members"),
        "group_update_mode": social.get("group_update_mode", "periodic-v1"),
        "group_update_period": social.get("group_update_period"),
        "group_update_min_period": social.get("group_update_min_period"),
        "group_update_max_period": social.get("group_update_max_period"),
        "spatial_stress_diagnostics_schema": run.get(
            "spatial_stress_diagnostics_schema"
        ),
        "spatial_region_partition": spatial_partition,
        "differentiation_enabled": bool(differentiation.get("enabled", False)),
        "differentiation_schema": differentiation.get("schema", "disabled"),
        "differentiation_capacity_bounds": {
            "working_memory_dimensions": [
                differentiation.get("working_memory_min_dimensions"),
                differentiation.get("working_memory_max_dimensions"),
            ],
            "knowledge_bytes": [
                differentiation.get("knowledge_min_bytes"),
                differentiation.get("knowledge_max_bytes"),
            ],
            "relation_slots": [
                differentiation.get("relation_min_slots"),
                differentiation.get("relation_max_slots"),
            ],
            "knowledge_attention_slots": [
                differentiation.get("attention_min_slots"),
                differentiation.get("attention_max_slots"),
            ],
        },
        "differentiation_mutation_probability": differentiation.get("mutation_probability"),
        "differentiation_mutation_std": differentiation.get("mutation_std"),
        "requested_backend": manifest.get("requested_backend"),
        "execution_backend": manifest.get("execution_backend"),
        "gpu_semantics_mode": manifest.get("gpu_semantics_mode"),
        "gpu_device_validated": manifest.get("gpu_device_validated"),
        "gpu_acceleration_enabled": manifest.get("gpu_acceleration_enabled"),
        "runtime_version": manifest.get("version"),
    }


def _phase_stratified_transfer(records: list[dict[str, Any]]) -> dict[str, dict[str, float | int]]:
    if not records:
        return {}
    alive = np.asarray([float(record.get("alive", 0.0)) for record in records])
    net = np.asarray([
        float(record.get("births_window", 0.0)) - float(record.get("deaths_window", 0.0))
        for record in records
    ])
    committed = np.asarray([
        float(record.get("knowledge_transfer_committed_window", math.nan))
        for record in records
    ])
    attempts = np.asarray([
        float(record.get("knowledge_transfer_attempts_window", math.nan))
        for record in records
    ])
    low = float(np.nanquantile(alive, 0.25))
    high = float(np.nanquantile(alive, 0.75))
    masks = {
        "rise": net > 0.0,
        "decline": net < 0.0,
        "peak": alive >= high,
        "trough": alive <= low,
    }
    result: dict[str, dict[str, float | int]] = {}
    for phase, mask in masks.items():
        valid = mask & np.isfinite(committed) & np.isfinite(attempts)
        if not np.any(valid):
            result[phase] = {"windows": 0, "attempts": 0, "committed": 0, "commit_rate": 0.0}
            continue
        attempt_total = int(round(float(np.sum(attempts[valid]))))
        committed_total = int(round(float(np.sum(committed[valid]))))
        result[phase] = {
            "windows": int(np.count_nonzero(valid)),
            "attempts": attempt_total,
            "committed": committed_total,
            "commit_rate": float(committed_total / attempt_total if attempt_total else 0.0),
        }
    return result


def _panel_demean(values: np.ndarray, axis: int, valid: np.ndarray) -> np.ndarray:
    array = np.asarray(values, dtype=np.float64)
    mask = np.asarray(valid, dtype=bool) & np.isfinite(array)
    out = np.full_like(array, np.nan)
    if axis == 0:
        for column in range(array.shape[1]):
            keep = mask[:, column]
            if np.any(keep):
                out[keep, column] = array[keep, column] - np.mean(array[keep, column])
    elif axis == 1:
        for row in range(array.shape[0]):
            keep = mask[row]
            if np.any(keep):
                out[row, keep] = array[row, keep] - np.mean(array[row, keep])
    else:
        raise ValueError("panel demean axis must be 0 or 1")
    return out


def _panel_correlation_bundle(
    x: np.ndarray,
    y: np.ndarray,
    *,
    x_valid: np.ndarray,
    y_valid: np.ndarray,
    label: str,
) -> dict[str, float | None]:
    valid = np.asarray(x_valid, dtype=bool) & np.asarray(y_valid, dtype=bool)
    raw = _pearson(x[valid], y[valid])
    x_region = _panel_demean(x, 0, x_valid)
    y_region = _panel_demean(y, 0, y_valid)
    region_valid = np.isfinite(x_region) & np.isfinite(y_region)
    x_window = _panel_demean(x, 1, x_valid)
    y_window = _panel_demean(y, 1, y_valid)
    window_valid = np.isfinite(x_window) & np.isfinite(y_window)
    dx = np.diff(x, axis=0)
    dy = np.diff(y, axis=0)
    diff_valid = valid[1:] & valid[:-1] & np.isfinite(dx) & np.isfinite(dy)
    lead_valid = np.asarray(x_valid[:-1], dtype=bool) & np.asarray(y_valid[1:], dtype=bool)
    return {
        f"{label}_raw": raw,
        f"{label}_within_region": _pearson(x_region[region_valid], y_region[region_valid]),
        f"{label}_within_window": _pearson(x_window[window_valid], y_window[window_valid]),
        f"{label}_first_difference": _pearson(dx[diff_valid], dy[diff_valid]),
        f"{label}_next_window": _pearson(x[:-1][lead_valid], y[1:][lead_valid]),
    }


def _local_event_study(
    exposure: np.ndarray,
    outcomes: dict[str, np.ndarray],
    *,
    valid: np.ndarray,
    quantile: float = 0.80,
    min_gap_windows: int = 2,
) -> dict[str, Any]:
    """Observational within-region event study around high local exposure."""
    x = np.asarray(exposure, dtype=np.float64)
    mask = np.asarray(valid, dtype=bool) & np.isfinite(x)
    events: list[tuple[int, int]] = []
    for region in range(x.shape[1]):
        keep = mask[:, region]
        values = x[keep, region]
        if values.size < 5 or float(np.std(values)) == 0.0:
            continue
        threshold = float(np.quantile(values, quantile))
        candidates = [
            tick
            for tick in range(1, x.shape[0] - 2)
            if keep[tick]
            and x[tick, region] >= threshold
            and x[tick, region] >= x[tick - 1, region]
            and x[tick, region] > x[tick + 1, region]
        ]
        last = -10**9
        for tick in candidates:
            if tick - last >= min_gap_windows:
                events.append((tick, region))
                last = tick
    result: dict[str, Any] = {
        "event_count": len(events),
        "quantile": float(quantile),
        "min_gap_windows": int(min_gap_windows),
        "outcomes": {},
        "causal_caution": (
            "Events are selected from observed local exposure peaks. Pre/post changes "
            "remain descriptive because no environmental intervention was applied."
        ),
    }
    for name, values in outcomes.items():
        array = np.asarray(values, dtype=np.float64)
        samples: dict[int, list[float]] = {-1: [], 0: [], 1: [], 2: []}
        for tick, region in events:
            for offset in samples:
                value = float(array[tick + offset, region])
                if np.isfinite(value):
                    samples[offset].append(value)
        means = {
            str(offset): (float(np.mean(items)) if items else None)
            for offset, items in samples.items()
        }
        pre = means["-1"]
        result["outcomes"][name] = {
            "mean_by_offset": means,
            "post1_minus_pre1": (
                None if pre is None or means["1"] is None else means["1"] - pre
            ),
            "post2_minus_pre1": (
                None if pre is None or means["2"] is None else means["2"] - pre
            ),
        }
    return result


def _spatial_panel_analysis(records: list[dict[str, Any]]) -> dict[str, Any]:
    accepted_schemas = {
        "spatial-local-stress-diagnostics-v1",
        "spatial-local-stress-culture-diagnostics-v2",
    }
    usable = [
        record for record in records
        if record.get("spatial_local_stress_schema") in accepted_schemas
    ]
    if len(usable) < MIN_CORRELATION_SAMPLES:
        return {
            "available": False,
            "reason": "fewer than five spatial diagnostic windows",
        }
    keys = {
        "mortality": "spatial_local_region_mortality_pressure",
        "cohesion": "spatial_local_region_boundary_cohesion",
        "cohesion_valid": "spatial_local_region_cohesion_valid",
        "scarcity": "spatial_local_region_resource_scarcity",
        "hazard": "spatial_local_region_hazard_exposure",
        "crowding": "spatial_local_region_crowding",
        "population_change": "spatial_local_region_alive_change_rate",
        "entity_ticks": "spatial_local_region_entity_ticks",
    }
    arrays: dict[str, np.ndarray] = {}
    region_count = None
    for name, key in keys.items():
        rows = [record.get(key) for record in usable]
        if any(value is None for value in rows):
            return {"available": False, "reason": f"missing {key}"}
        array = np.asarray(rows, dtype=np.float64)
        if array.ndim != 2:
            return {"available": False, "reason": f"invalid shape for {key}"}
        region_count = array.shape[1] if region_count is None else region_count
        if array.shape[1] != region_count:
            return {"available": False, "reason": "region count changed across windows"}
        arrays[name] = array
    occupied = arrays["entity_ticks"] > 0.0
    valid = occupied & (arrays["cohesion_valid"] > 0.5)
    cohesion = arrays["cohesion"]

    raw: dict[str, float | None] = {}
    within_region: dict[str, float | None] = {}
    within_window: dict[str, float | None] = {}
    first_difference: dict[str, float | None] = {}
    next_window: dict[str, float | None] = {}
    for name in ("mortality", "scarcity", "hazard", "crowding", "population_change"):
        values = arrays[name]
        raw[f"local_{name}_vs_local_cohesion"] = _pearson(
            values[valid], cohesion[valid]
        )
        x_region = _panel_demean(values, 0, occupied)
        y_region = _panel_demean(cohesion, 0, valid)
        panel_valid = np.isfinite(x_region) & np.isfinite(y_region)
        within_region[f"local_{name}_vs_cohesion_within_region"] = _pearson(
            x_region[panel_valid], y_region[panel_valid]
        )
        x_window = _panel_demean(values, 1, occupied)
        y_window = _panel_demean(cohesion, 1, valid)
        panel_valid = np.isfinite(x_window) & np.isfinite(y_window)
        within_window[f"local_{name}_vs_cohesion_within_window"] = _pearson(
            x_window[panel_valid], y_window[panel_valid]
        )
        dx = np.diff(values, axis=0)
        dy = np.diff(cohesion, axis=0)
        diff_valid = valid[1:] & valid[:-1] & np.isfinite(dx) & np.isfinite(dy)
        first_difference[f"delta_local_{name}_vs_delta_local_cohesion"] = _pearson(
            dx[diff_valid], dy[diff_valid]
        )
        lead_valid = occupied[:-1] & valid[1:]
        next_window[f"local_{name}_vs_next_window_local_cohesion"] = _pearson(
            values[:-1][lead_valid], cohesion[1:][lead_valid]
        )

    global_mortality = np.asarray([
        float(record.get("mortality_pressure_window", 0.0)) for record in usable
    ])
    local_mortality = arrays["mortality"]
    ratio = np.divide(
        local_mortality,
        global_mortality[:, None],
        out=np.zeros_like(local_mortality),
        where=global_mortality[:, None] > 0.0,
    )
    ratio_valid = occupied & np.isfinite(ratio)
    result: dict[str, Any] = {
        "available": True,
        "schema": "spatial-local-panel-analysis-v2",
        "window_count": len(usable),
        "region_count": int(region_count or 0),
        "raw_panel_correlations": raw,
        "within_region_correlations": within_region,
        "within_window_correlations": within_window,
        "first_difference_correlations": first_difference,
        "next_window_correlations": next_window,
        "mean_population_cv": float(np.mean([
            float(record.get("spatial_local_population_cv", 0.0)) for record in usable
        ])),
        "mean_mortality_pressure_cv": float(np.mean([
            float(record.get("spatial_local_mortality_pressure_cv", 0.0)) for record in usable
        ])),
        "mean_resource_scarcity_cv": float(np.mean([
            float(record.get("spatial_local_resource_scarcity_cv", 0.0)) for record in usable
        ])),
        "mean_cohesion_cv": float(np.mean([
            float(record.get("spatial_local_cohesion_cv", 0.0)) for record in usable
        ])),
        "max_local_to_global_mortality_ratio": (
            float(np.max(ratio[ratio_valid])) if np.any(ratio_valid) else 0.0
        ),
        "fraction_region_windows_above_2x_global_mortality": (
            float(np.mean(ratio[ratio_valid] >= 2.0)) if np.any(ratio_valid) else 0.0
        ),
        "causal_caution": (
            "Spatial panel correlations are observational. Region fixed-effect, "
            "window fixed-effect, first-difference and lagged checks reduce some "
            "confounding but do not identify an in-world causal mechanism."
        ),
    }

    culture_keys = {
        "attempts_out": "spatial_local_region_transfer_attempts_outgoing",
        "attempts_in": "spatial_local_region_transfer_attempts_incoming",
        "commits_out": "spatial_local_region_transfer_committed_outgoing",
        "commits_in": "spatial_local_region_transfer_committed_incoming",
        "new_roots": "spatial_local_region_new_transferred_roots",
        "lost_roots": "spatial_local_region_lost_transferred_roots",
        "active_roots": "spatial_local_region_active_transferred_roots",
        "source_rate": "spatial_local_transfer_commit_rate_by_source",
    }
    culture_available = all(
        all(record.get(key) is not None for record in usable)
        for key in culture_keys.values()
    )
    if not culture_available:
        result["local_cultural_transfer_analysis"] = {
            "available": False,
            "reason": "spatial cultural-transfer diagnostics were not enabled",
        }
        return result

    culture: dict[str, np.ndarray] = {
        name: np.asarray([record[key] for record in usable], dtype=np.float64)
        for name, key in culture_keys.items()
    }
    flow = np.asarray(
        [record["spatial_local_transfer_commit_flow"] for record in usable],
        dtype=np.float64,
    )
    diagonal = np.diagonal(flow, axis1=1, axis2=2)
    same_region_retention = np.divide(
        diagonal,
        culture["commits_out"],
        out=np.zeros_like(diagonal),
        where=culture["commits_out"] > 0.0,
    )
    incoming_per_entity_tick = np.divide(
        culture["commits_in"],
        arrays["entity_ticks"],
        out=np.zeros_like(culture["commits_in"]),
        where=arrays["entity_ticks"] > 0.0,
    )
    outgoing_per_entity_tick = np.divide(
        culture["commits_out"],
        arrays["entity_ticks"],
        out=np.zeros_like(culture["commits_out"]),
        where=arrays["entity_ticks"] > 0.0,
    )
    net_root_establishment = culture["new_roots"] - culture["lost_roots"]
    culture_valid = occupied
    correlation_bundle: dict[str, float | None] = {}
    for xname, xvalues, yname, yvalues, yvalid in (
        ("scarcity", arrays["scarcity"], "outgoing_transfer_rate", outgoing_per_entity_tick, culture_valid),
        ("scarcity", arrays["scarcity"], "incoming_transfer_rate", incoming_per_entity_tick, culture_valid),
        ("scarcity", arrays["scarcity"], "new_transferred_roots", culture["new_roots"], culture_valid),
        ("scarcity", arrays["scarcity"], "net_transferred_root_establishment", net_root_establishment, culture_valid),
        ("cohesion", cohesion, "same_region_transfer_retention", same_region_retention, valid),
        ("crowding", arrays["crowding"], "outgoing_transfer_rate", outgoing_per_entity_tick, culture_valid),
        ("mortality", arrays["mortality"], "incoming_transfer_rate", incoming_per_entity_tick, culture_valid),
    ):
        correlation_bundle.update(
            _panel_correlation_bundle(
                xvalues,
                yvalues,
                x_valid=(valid if xname == "cohesion" else occupied),
                y_valid=yvalid,
                label=f"local_{xname}_vs_local_{yname}",
            )
        )
    event_outcomes = {
        "cohesion": np.where(valid, cohesion, np.nan),
        "outgoing_transfer_per_entity_tick": outgoing_per_entity_tick,
        "incoming_transfer_per_entity_tick": incoming_per_entity_tick,
        "new_transferred_roots": culture["new_roots"],
        "net_transferred_root_establishment": net_root_establishment,
        "active_transferred_roots": culture["active_roots"],
        "same_region_transfer_retention": same_region_retention,
    }
    result["local_cultural_transfer_analysis"] = {
        "available": True,
        "schema": "spatial-local-cultural-panel-analysis-v1",
        "correlations": correlation_bundle,
        "high_scarcity_event_study": _local_event_study(
            arrays["scarcity"], event_outcomes, valid=valid
        ),
        "high_crowding_event_study": _local_event_study(
            arrays["crowding"], event_outcomes, valid=valid
        ),
        "high_mortality_event_study": _local_event_study(
            arrays["mortality"], event_outcomes, valid=valid
        ),
        "total_cross_region_committed": int(sum(
            int(record.get("spatial_local_transfer_cross_region_committed", 0))
            for record in usable
        )),
        "total_same_region_committed": int(sum(
            int(record.get("spatial_local_transfer_same_region_committed", 0))
            for record in usable
        )),
        "final_active_transferred_root_count": int(
            usable[-1].get("spatial_local_active_transferred_root_count", 0)
        ),
        "final_multi_region_transferred_root_count": int(
            usable[-1].get("spatial_local_multi_region_transferred_root_count", 0)
        ),
        "causal_caution": (
            "Local transfer and root event studies are observational. They identify "
            "where to place paired checkpoint interventions, not causal effects."
        ),
    }
    return result


def summarize_run(path: str | Path, records: list[dict[str, Any]]) -> dict[str, Any]:
    if not records:
        raise ValueError(f"{path} contains no records")
    final = records[-1]
    ticks = _array(records, "tick")
    alive = _array(records, "alive")
    deaths = _array(records, "deaths_window")
    mortality = np.asarray(
        [
            record.get(
                "mortality_pressure_window",
                record.get("deaths_window", 0)
                / max(record.get("alive", 0) + record.get("deaths_window", 0), 1),
            )
            for record in records
        ],
        dtype=np.float64,
    )
    cohesion = _array(records, "benefit_boundary_cohesion")
    effective_lineages = _array(records, "effective_lineages")
    largest_lineage = _array(records, "largest_lineage_fraction")
    strategy_dims = _array(records, "strategy_effective_dimensions")
    action_entropy = _array(records, "window_action_entropy")
    lineage_group_nmi = _array(records, "lineage_group_nmi")
    lineage_group_pair_enrichment = _array(records, "lineage_group_pair_enrichment")
    knowledge_effective_roots = _array(records, "knowledge_effective_root_contents")
    affinity_dims = _array(records, "resource_affinity_effective_dimensions")
    capacity_dims = _array(records, "capacity_effective_dimensions")
    capacity_working_memory = _array(records, "capacity_working_memory_dimensions_mean")
    capacity_knowledge = _array(records, "capacity_knowledge_capacity_bytes_mean")
    capacity_relations = _array(records, "capacity_relation_slots_mean")
    capacity_attention = _array(records, "capacity_knowledge_attention_slots_mean")
    environment_resource_dims = _array(records, "environment_resource_effective_dimensions")

    raw_correlations = {
        "mortality_vs_same_window_cohesion": _pearson(mortality, cohesion),
        "mortality_vs_next_window_cohesion": _pearson(mortality[:-1], cohesion[1:]),
        "effective_lineages_vs_cohesion": _pearson(effective_lineages, cohesion),
        "largest_lineage_fraction_vs_cohesion": _pearson(largest_lineage, cohesion),
        "strategy_dimensions_vs_action_entropy": _pearson(strategy_dims, action_entropy),
        "lineage_group_nmi_vs_cohesion": _pearson(lineage_group_nmi, cohesion),
        "lineage_group_pair_enrichment_vs_cohesion": _pearson(
            lineage_group_pair_enrichment, cohesion
        ),
        "knowledge_effective_roots_vs_effective_lineages": _pearson(
            knowledge_effective_roots, effective_lineages
        ),
    }
    capacity_correlations = {
        "capacity_dimensions_vs_alive": _pearson(capacity_dims, alive),
        "capacity_dimensions_vs_resource_environment_dimensions": _pearson(
            capacity_dims, environment_resource_dims
        ),
        "capacity_dimensions_vs_resource_affinity_dimensions": _pearson(
            capacity_dims, affinity_dims
        ),
        "capacity_dimensions_vs_boundary_cohesion": _pearson(
            capacity_dims, cohesion
        ),
        "capacity_dimensions_vs_effective_transferred_roots": _pearson(
            capacity_dims, _array(records, "knowledge_effective_transferred_roots")
        ),
        "working_memory_capacity_vs_action_entropy": _pearson(
            capacity_working_memory, action_entropy
        ),
        "knowledge_capacity_vs_effective_root_contents": _pearson(
            capacity_knowledge, knowledge_effective_roots
        ),
        "relation_capacity_vs_boundary_cohesion": _pearson(
            capacity_relations, cohesion
        ),
        "attention_capacity_vs_committed_transfer": _pearson(
            capacity_attention, _array(records, "knowledge_transfer_committed_window")
        ),
    }

    transfer_window = _array(records, "knowledge_transfer_committed_window")
    transfer_cross_lineage_window = _array(
        records, "knowledge_transfer_cross_lineage_committed_window"
    )
    transferred_roots = _array(records, "knowledge_effective_transferred_roots")
    transfer_correlations = {
        "committed_transfer_vs_effective_transferred_roots": (
            _pearson(transfer_window, transferred_roots)
            if np.count_nonzero(np.isfinite(transfer_window)) >= MIN_CORRELATION_SAMPLES
            else None
        ),
        "cross_lineage_transfer_vs_lineage_group_cohesion": (
            _pearson(transfer_cross_lineage_window, cohesion)
            if np.count_nonzero(np.isfinite(transfer_cross_lineage_window))
            >= MIN_CORRELATION_SAMPLES
            else None
        ),
    }

    first_difference = {
        "delta_mortality_vs_delta_cohesion": _pearson(
            np.diff(mortality), np.diff(cohesion)
        ),
        "mortality_vs_next_delta_cohesion": _pearson(
            mortality[:-1], np.diff(cohesion)
        ),
        "delta_effective_lineages_vs_delta_cohesion": _pearson(
            np.diff(effective_lineages), np.diff(cohesion)
        ),
        "delta_largest_lineage_fraction_vs_delta_cohesion": _pearson(
            np.diff(largest_lineage), np.diff(cohesion)
        ),
        "delta_strategy_dimensions_vs_delta_action_entropy": _pearson(
            np.diff(strategy_dims), np.diff(action_entropy)
        ),
        "delta_lineage_group_pair_enrichment_vs_delta_cohesion": _pearson(
            np.diff(lineage_group_pair_enrichment), np.diff(cohesion)
        ),
    }
    partial = {
        "mortality_vs_cohesion_controlling_tick_alive": _partial_pearson(
            mortality, cohesion, (ticks, alive)
        ),
        "effective_lineages_vs_cohesion_controlling_tick_alive": _partial_pearson(
            effective_lineages, cohesion, (ticks, alive)
        ),
        "largest_lineage_fraction_vs_cohesion_controlling_tick_alive": _partial_pearson(
            largest_lineage, cohesion, (ticks, alive)
        ),
        "lineage_group_pair_enrichment_vs_cohesion_controlling_tick_alive": (
            _partial_pearson(lineage_group_pair_enrichment, cohesion, (ticks, alive))
        ),
    }
    lag_correlations = _cross_lag_correlations(mortality, cohesion, max_lag=3)
    config_context = _resolved_config_context(path)
    transfer_proposals = int(final.get("knowledge_transfer_proposals_total", 0))
    transfer_attempts = int(final.get("knowledge_transfer_attempts_total", 0))
    transfer_committed = int(final.get("knowledge_transfer_committed_total", 0))
    transfer_bytes = int(final.get("knowledge_transfer_committed_bytes_total", 0))
    transfer_probability = config_context.get("knowledge_transfer_probability")
    cultural_spread_interpretable = transfer_committed > 0
    warnings: list[str] = []
    if transfer_committed <= 0:
        if isinstance(transfer_probability, (int, float)) and transfer_probability > 0.0:
            warnings.append(
                "Knowledge transfer was configured but no committed transfer is present in "
                "evolution_progress. For v0.17 and earlier this can mean the progress schema "
                "omitted cumulative transfer fields; cultural-spread metrics are not identifiable "
                "from this file alone."
            )
        else:
            warnings.append(
                "No committed knowledge transfer was detected; root-content spread metrics "
                "describe private experience creation, not cultural transmission."
            )
    if transfer_attempts > 0 and transfer_committed == 0:
        warnings.append(
            "Transfer attempts occurred but every proposal was rejected or lost; inspect the "
            "window rejection counters and knowledge_transfers.csv."
        )
    path_obj = Path(path)
    subject_structure_final = {
        key: value
        for key, value in final.items()
        if str(key).startswith("subject_structure_")
    }
    environment_atlas_final = {
        key: value
        for key, value in final.items()
        if str(key).startswith("environment_atlas_")
    }
    resource_environment_final = {
        key: value
        for key, value in final.items()
        if str(key).startswith("environment_resource_")
    }
    capacity_final = {
        key: value
        for key, value in final.items()
        if str(key).startswith("capacity_") or key == "differentiation_schema"
    }
    if (
        config_context.get("differentiation_enabled")
        and config_context.get("differentiation_schema")
        == "inherited-elastic-capacities-v1"
        and not capacity_final
    ):
        raise ValueError(
            f"{path} enables D1 elastic capacities but contains no capacity_* "
            "progress fields; do not analyze it as a complete D1 run"
        )
    return {
        "path": str(path),
        "run_name": (
            path_obj.parent.name if path_obj.name == "evolution_progress.jsonl" else path_obj.name
        ),
        "record_count": len(records),
        "first_tick": int(records[0]["tick"]),
        "final_tick": int(final["tick"]),
        "alive_final": int(final.get("alive", 0)),
        "alive_peak": int(np.nanmax(alive)),
        "alive_peak_tick": int(records[int(np.nanargmax(alive))]["tick"]),
        "alive_trough": int(np.nanmin(alive)),
        "alive_trough_tick": int(records[int(np.nanargmin(alive))]["tick"]),
        "effective_lineages_final": float(final.get("effective_lineages", 0.0)),
        "largest_lineage_fraction_final": float(final.get("largest_lineage_fraction", 0.0)),
        "strategy_effective_dimensions_final": float(
            final.get("strategy_effective_dimensions", 0.0)
        ),
        "window_action_entropy_final": float(final.get("window_action_entropy", 0.0)),
        "benefit_boundary_cohesion_final": float(
            final.get("benefit_boundary_cohesion", 0.0)
        ),
        "resource_affinity_effective_dimensions_final": (
            float(final["resource_affinity_effective_dimensions"])
            if "resource_affinity_effective_dimensions" in final
            else None
        ),
        "subject_structure_final": subject_structure_final,
        "environment_atlas_final": environment_atlas_final,
        "resource_environment_final": resource_environment_final,
        "capacity_final": capacity_final,
        "danger_direct_weight_mean_final": (
            float(final["danger_direct_weight_mean"])
            if "danger_direct_weight_mean" in final else None
        ),
        "danger_direct_weight_std_final": (
            float(final["danger_direct_weight_std"])
            if "danger_direct_weight_std" in final else None
        ),
        "danger_trace_weight_mean_final": (
            float(final["danger_trace_weight_mean"])
            if "danger_trace_weight_mean" in final else None
        ),
        "danger_trace_weight_std_final": (
            float(final["danger_trace_weight_std"])
            if "danger_trace_weight_std" in final else None
        ),
        "danger_evidence_effective_dimensions_final": (
            float(final["danger_evidence_effective_dimensions"])
            if "danger_evidence_effective_dimensions" in final else None
        ),
        "environment_mortality_trace_mean_final": (
            float(final["environment_mortality_trace_mean"])
            if "environment_mortality_trace_mean" in final else None
        ),
        "environment_mortality_trace_max_final": (
            float(final["environment_mortality_trace_max"])
            if "environment_mortality_trace_max" in final else None
        ),
        "group_update_count_final": int(final.get("group_update_count_total", 0)),
        "group_update_skipped_final": int(final.get("group_update_skipped_total", 0)),
        "group_last_update_tick_final": int(final.get("group_last_update_tick", -1)),
        "lineage_group_nmi_final": (
            float(final["lineage_group_nmi"]) if "lineage_group_nmi" in final else None
        ),
        "lineage_group_pair_enrichment_final": (
            float(final["lineage_group_pair_enrichment"])
            if "lineage_group_pair_enrichment" in final
            else None
        ),
        "same_lineage_given_same_group_final": (
            float(final["same_lineage_given_same_group"])
            if "same_lineage_given_same_group" in final
            else None
        ),
        "knowledge_effective_root_contents_final": (
            float(final["knowledge_effective_root_contents"])
            if "knowledge_effective_root_contents" in final
            else None
        ),
        "knowledge_largest_root_holder_fraction_final": (
            float(final["knowledge_largest_root_holder_fraction"])
            if "knowledge_largest_root_holder_fraction" in final
            else None
        ),
        "knowledge_root_genetic_lineage_pair_enrichment_final": (
            float(final["knowledge_root_genetic_lineage_pair_enrichment"])
            if "knowledge_root_genetic_lineage_pair_enrichment" in final
            else None
        ),
        "knowledge_transfer_proposals_final": transfer_proposals,
        "knowledge_transfer_attempts_final": transfer_attempts,
        "knowledge_transfer_committed_final": transfer_committed,
        "knowledge_transfer_committed_bytes_final": transfer_bytes,
        "knowledge_transfer_commit_rate_after_attention_final": float(
            transfer_committed / transfer_attempts if transfer_attempts else 0.0
        ),
        "knowledge_transfer_commit_rate_per_proposal_final": float(
            transfer_committed / transfer_proposals if transfer_proposals else 0.0
        ),
        "knowledge_transfer_same_lineage_committed_final": int(
            final.get("knowledge_transfer_same_lineage_committed_total", 0)
        ),
        "knowledge_transfer_cross_lineage_committed_final": int(
            final.get("knowledge_transfer_cross_lineage_committed_total", 0)
        ),
        "knowledge_transfer_same_group_committed_final": int(
            final.get("knowledge_transfer_same_group_committed_total", 0)
        ),
        "knowledge_transfer_cross_group_committed_final": int(
            final.get("knowledge_transfer_cross_group_committed_total", 0)
        ),
        "knowledge_active_transferred_root_count_final": int(
            final.get("knowledge_active_transferred_root_count", 0)
        ),
        "knowledge_effective_transferred_roots_final": float(
            final.get("knowledge_effective_transferred_roots", 0.0)
        ),
        "knowledge_largest_transferred_root_holder_fraction_final": float(
            final.get("knowledge_largest_transferred_root_holder_fraction", 0.0)
        ),
        "knowledge_cultural_spread_interpretable": cultural_spread_interpretable,
        "knowledge_transfer_phase_summary": _phase_stratified_transfer(records),
        "correlations_cultural_transfer": (
            transfer_correlations if cultural_spread_interpretable else {}
        ),
        "spatial_local_analysis": _spatial_panel_analysis(records),
        "resource_demand_analysis": _resource_demand_analysis(records, config_context),
        "config_context": config_context,
        "trends_per_1000_ticks": {
            "alive": _slope_per_1000_ticks(ticks, alive),
            "effective_lineages": _slope_per_1000_ticks(ticks, effective_lineages),
            "largest_lineage_fraction": _slope_per_1000_ticks(ticks, largest_lineage),
            "strategy_effective_dimensions": _slope_per_1000_ticks(ticks, strategy_dims),
            "window_action_entropy": _slope_per_1000_ticks(ticks, action_entropy),
            "benefit_boundary_cohesion": _slope_per_1000_ticks(ticks, cohesion),
            "resource_affinity_effective_dimensions": _slope_per_1000_ticks(
                ticks, affinity_dims
            ),
            "capacity_effective_dimensions": _slope_per_1000_ticks(
                ticks, capacity_dims
            ),
            "capacity_working_memory_dimensions_mean": _slope_per_1000_ticks(
                ticks, capacity_working_memory
            ),
            "capacity_knowledge_capacity_bytes_mean": _slope_per_1000_ticks(
                ticks, capacity_knowledge
            ),
            "capacity_relation_slots_mean": _slope_per_1000_ticks(
                ticks, capacity_relations
            ),
            "capacity_knowledge_attention_slots_mean": _slope_per_1000_ticks(
                ticks, capacity_attention
            ),
        },
        "capacity_correlations_observational": (
            capacity_correlations if capacity_final else {}
        ),
        "correlations_observational": raw_correlations,
        "correlations_first_difference": first_difference,
        "correlations_partial": partial,
        "mortality_to_cohesion_cross_lag": lag_correlations,
        "mortality_to_cohesion_best_lag": _best_lag(lag_correlations),
        "analysis_warnings": warnings,
        "causal_caution": (
            "All correlations are descriptive. Raw correlations can be dominated by "
            "shared time trends; first differences and partial correlations reduce, "
            "but do not eliminate, confounding."
        ),
    }


def _aggregate_numeric(values: list[float | int]) -> dict[str, float]:
    array = np.asarray(values, dtype=np.float64)
    return {
        "mean": float(array.mean()),
        "min": float(array.min()),
        "max": float(array.max()),
        "std": float(array.std()),
    }


def _sign_consistency(runs: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for section in (
        "correlations_observational",
        "correlations_first_difference",
        "correlations_partial",
    ):
        keys = sorted({key for run in runs for key in run[section]})
        for key in keys:
            values = [run[section].get(key) for run in runs]
            available = [float(value) for value in values if value is not None]
            positive = sum(value > 0.0 for value in available)
            negative = sum(value < 0.0 for value in available)
            zero = sum(value == 0.0 for value in available)
            result[f"{section}.{key}"] = {
                "available_runs": len(available),
                "positive_runs": positive,
                "negative_runs": negative,
                "zero_runs": zero,
                "same_nonzero_sign": bool(available) and (positive == len(available) or negative == len(available)),
                "mean": float(np.mean(available)) if available else None,
                "min": float(np.min(available)) if available else None,
                "max": float(np.max(available)) if available else None,
            }
    return result


def _local_sign_consistency(runs: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    sections: dict[str, list[float]] = {}
    for run in runs:
        spatial = run.get("spatial_local_analysis", {})
        for section_name in ("within_region_correlations", "next_window_correlations"):
            for key, value in spatial.get(section_name, {}).items():
                if value is not None:
                    sections.setdefault(f"{section_name}.{key}", []).append(float(value))
        cultural = spatial.get("local_cultural_transfer_analysis", {})
        for key, value in cultural.get("correlations", {}).items():
            if value is not None and (
                key.endswith("_within_region") or key.endswith("_next_window")
            ):
                sections.setdefault(f"local_culture.{key}", []).append(float(value))
    result: dict[str, dict[str, Any]] = {}
    for key, values in sorted(sections.items()):
        positive = sum(value > 0.0 for value in values)
        negative = sum(value < 0.0 for value in values)
        zero = sum(value == 0.0 for value in values)
        result[key] = {
            "available_runs": len(values),
            "positive_runs": positive,
            "negative_runs": negative,
            "zero_runs": zero,
            "same_nonzero_sign": bool(values) and (
                positive == len(values) or negative == len(values)
            ),
            "mean": float(np.mean(values)) if values else None,
            "min": float(np.min(values)) if values else None,
            "max": float(np.max(values)) if values else None,
        }
    return result


def analyze(paths: list[str | Path]) -> dict[str, Any]:
    runs = [summarize_run(path, load_progress(path)) for path in paths]
    endpoint_keys = (
        "alive_final",
        "effective_lineages_final",
        "largest_lineage_fraction_final",
        "strategy_effective_dimensions_final",
        "window_action_entropy_final",
        "benefit_boundary_cohesion_final",
        "knowledge_transfer_committed_final",
        "knowledge_effective_transferred_roots_final",
    )
    aggregate = {
        key: _aggregate_numeric([run[key] for run in runs]) for key in endpoint_keys
    }
    capacity_values = [
        run.get("capacity_final", {}).get("capacity_effective_dimensions")
        for run in runs
    ]
    if capacity_values and all(value is not None for value in capacity_values):
        aggregate["capacity_effective_dimensions_final"] = _aggregate_numeric(
            [float(value) for value in capacity_values]
        )
    consistency = _sign_consistency(runs)
    local_consistency = _local_sign_consistency(runs)
    robust = [
        key
        for key, value in consistency.items()
        if value["available_runs"] >= 3 and value["same_nonzero_sign"]
    ]
    robust_local = [
        key
        for key, value in local_consistency.items()
        if value["available_runs"] >= 3 and value["same_nonzero_sign"]
    ]
    return {
        "schema": "multi-seed-long-run-analysis-v12",
        "analyzer_version": __version__,
        "input_runtime_versions": sorted(
            {
                str(run.get("config_context", {}).get("runtime_version"))
                for run in runs
                if run.get("config_context", {}).get("runtime_version") is not None
            }
        ),
        "run_count": len(runs),
        "runs": runs,
        "endpoint_aggregate": aggregate,
        "cross_seed_sign_consistency": consistency,
        "cross_seed_local_sign_consistency": local_consistency,
        "repeated_directional_patterns": robust,
        "repeated_local_directional_patterns": robust_local,
        "interpretation_boundary": (
            "Repeated signs across seeds support robustness, not necessity. Raw "
            "within-run correlations may reflect shared temporal drift. Controlled "
            "checkpoint interventions are required for phase-specific causal claims."
        ),
    }


def _format(value: Any, digits: int = 4) -> str:
    return "—" if value is None else f"{float(value):.{digits}f}"


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Multi-seed long-run analysis",
        "",
        f"Schema: `{report['schema']}`",
        f"Analyzer: `{report.get('analyzer_version', 'unknown')}`",
        f"Input runtimes: `{report.get('input_runtime_versions', [])}`",
        f"Runs: **{report['run_count']}**",
        "",
        "> This report is observational. Raw correlations, first differences and partial correlations do not identify an in-world causal mechanism.",
        "",
        "| Run | Final tick | Alive | Effective lineages | Largest lineage | Strategy dims | Action entropy | Cohesion | Affinity dims | Transfer commits | Transferred roots |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for run in report["runs"]:
        lines.append(
            "| {name} | {tick} | {alive} | {effective:.4f} | {largest:.4f} | "
            "{dims:.4f} | {entropy:.4f} | {cohesion:.4f} | {affinity} | {commits} | {roots:.4f} |".format(
                name=run["run_name"],
                tick=run["final_tick"],
                alive=run["alive_final"],
                effective=run["effective_lineages_final"],
                largest=run["largest_lineage_fraction_final"],
                dims=run["strategy_effective_dimensions_final"],
                entropy=run["window_action_entropy_final"],
                cohesion=run["benefit_boundary_cohesion_final"],
                affinity=_format(run["resource_affinity_effective_dimensions_final"]),
                commits=run["knowledge_transfer_committed_final"],
                roots=run["knowledge_effective_transferred_roots_final"],
            )
        )
    lines.extend(["", "## Within-run raw observational correlations", ""])
    for run in report["runs"]:
        lines.append(f"### {run['run_name']}")
        for key, value in run["correlations_observational"].items():
            lines.append(f"- `{key}`: {_format(value)}")
        lines.append("")
    lines.extend(["## First-difference checks", ""])
    for run in report["runs"]:
        lines.append(f"### {run['run_name']}")
        for key, value in run["correlations_first_difference"].items():
            lines.append(f"- `{key}`: {_format(value)}")
        lines.append("")
    lines.extend(["## Partial correlations controlling tick and alive", ""])
    for run in report["runs"]:
        lines.append(f"### {run['run_name']}")
        for key, value in run["correlations_partial"].items():
            lines.append(f"- `{key}`: {_format(value)}")
        best = run["mortality_to_cohesion_best_lag"]
        if best is not None:
            lines.append(
                "- strongest mortality→cohesion cross-lag: "
                f"lag `{best['lag_windows']}` windows, r={best['correlation']:.4f}"
            )
        for warning in run["analysis_warnings"]:
            lines.append(f"- warning: {warning}")
        lines.append("")
    lines.extend(["## Costed cultural transfer", ""])
    for run in report["runs"]:
        lines.append(f"### {run['run_name']}")
        lines.append(
            f"- proposals / admitted attempts / committed / bytes: "
            f"{run['knowledge_transfer_proposals_final']} / "
            f"{run['knowledge_transfer_attempts_final']} / "
            f"{run['knowledge_transfer_committed_final']} / "
            f"{run['knowledge_transfer_committed_bytes_final']}"
        )
        lines.append(
            f"- committed cross-lineage / cross-group: "
            f"{run['knowledge_transfer_cross_lineage_committed_final']} / "
            f"{run['knowledge_transfer_cross_group_committed_final']}"
        )
        lines.append(
            f"- active/effective transferred roots: "
            f"{run['knowledge_active_transferred_root_count_final']} / "
            f"{run['knowledge_effective_transferred_roots_final']:.4f}"
        )
        lines.append(
            f"- cultural-spread interpretable: "
            f"{run['knowledge_cultural_spread_interpretable']}"
        )
        for warning in run["analysis_warnings"]:
            lines.append(f"- warning: {warning}")
        lines.append("")
    lines.extend([
        "## Environment process, danger evidence, mortality trace and group refresh",
        "",
    ])
    for run in report["runs"]:
        context = run.get("config_context", {})
        lines.append(f"### {run['run_name']}")
        lines.append(
            f"- environment process: {context.get('environment_process_schema')} "
            f"({context.get('environment_process_origin')})"
        )
        lines.append(
            f"- mechanism / interpretation: "
            f"{context.get('environment_process_mechanism_class')} / "
            f"{context.get('environment_process_interpretation')}"
        )
        lines.append(
            f"- process parameter names: "
            f"{context.get('environment_process_parameter_names')}"
        )
        lines.append(
            f"- v0.22 moving-hazard compatibility fields / sources: "
            f"{context.get('moving_hazard_schema')} / "
            f"{context.get('moving_hazard_source_count')}"
        )
        lines.append(
            f"- danger evidence schema: {context.get('danger_evidence_schema')}"
        )
        lines.append(
            f"- direct mean/std: {_format(run.get('danger_direct_weight_mean_final'))} / "
            f"{_format(run.get('danger_direct_weight_std_final'))}"
        )
        lines.append(
            f"- trace mean/std: {_format(run.get('danger_trace_weight_mean_final'))} / "
            f"{_format(run.get('danger_trace_weight_std_final'))}"
        )
        lines.append(
            f"- mortality trace mean/max: "
            f"{_format(run.get('environment_mortality_trace_mean_final'), 6)} / "
            f"{_format(run.get('environment_mortality_trace_max_final'), 6)}"
        )
        lines.append(
            f"- group refresh mode / updates / skipped: "
            f"{context.get('group_update_mode')} / "
            f"{run.get('group_update_count_final')} / "
            f"{run.get('group_update_skipped_final')}"
        )
        lines.append(
            f"- group label schema / rounds / trust / min members: "
            f"{context.get('group_label_schema')} / "
            f"{context.get('group_label_propagation_rounds')} / "
            f"{context.get('group_trust_threshold')} / "
            f"{context.get('group_min_members')}"
        )
        partition = context.get("spatial_region_partition")
        if isinstance(partition, dict):
            lines.append(
                f"- spatial partition: {partition.get('schema')} "
                f"{partition.get('regions_x')}x{partition.get('regions_y')}, "
                f"physical={partition.get('physical_region_width')}x"
                f"{partition.get('physical_region_height')}, "
                f"cells={partition.get('world_cells_per_region_x')}x"
                f"{partition.get('world_cells_per_region_y')}, "
                f"aligned={partition.get('world_grid_aligned')}"
            )
        lines.append("")

    lines.extend(["## Execution backend context", ""])
    for run in report["runs"]:
        context = run.get("config_context", {})
        lines.append(
            f"- `{run['run_name']}`: requested={context.get('requested_backend')}, "
            f"execution={context.get('execution_backend')}, "
            f"gpu_semantics={context.get('gpu_semantics_mode')}, "
            f"device_validated={context.get('gpu_device_validated')}, "
            f"acceleration={context.get('gpu_acceleration_enabled')}"
        )
    lines.append("")
    lines.extend(["## Local spatial stress panel", ""])
    for run in report["runs"]:
        lines.append(f"### {run['run_name']}")
        spatial = run.get("spatial_local_analysis", {})
        if not spatial.get("available", False):
            lines.append(f"- unavailable: {spatial.get('reason', 'no local diagnostics')}")
            lines.append("")
            continue
        lines.append(
            f"- windows / regions: {spatial['window_count']} / {spatial['region_count']}"
        )
        lines.append(
            f"- mean population / mortality / scarcity / cohesion CV: "
            f"{spatial['mean_population_cv']:.4f} / "
            f"{spatial['mean_mortality_pressure_cv']:.4f} / "
            f"{spatial['mean_resource_scarcity_cv']:.4f} / "
            f"{spatial['mean_cohesion_cv']:.4f}"
        )
        lines.append(
            f"- max local/global mortality ratio: "
            f"{spatial['max_local_to_global_mortality_ratio']:.4f}"
        )
        for subsection in (
            "within_region_correlations",
            "within_window_correlations",
            "first_difference_correlations",
            "next_window_correlations",
        ):
            lines.append(f"- {subsection}:")
            for key, value in spatial[subsection].items():
                lines.append(f"  - `{key}`: {_format(value)}")
        lines.append("")
    lines.extend(["## Local cultural transfer panel", ""])
    for run in report["runs"]:
        lines.append(f"### {run['run_name']}")
        spatial = run.get("spatial_local_analysis", {})
        cultural = spatial.get("local_cultural_transfer_analysis", {})
        if not cultural.get("available", False):
            lines.append(f"- unavailable: {cultural.get('reason', 'no local culture diagnostics')}")
            lines.append("")
            continue
        lines.append(
            f"- same/cross-region commits: "
            f"{cultural['total_same_region_committed']} / "
            f"{cultural['total_cross_region_committed']}"
        )
        lines.append(
            f"- final active/multi-region transferred roots: "
            f"{cultural['final_active_transferred_root_count']} / "
            f"{cultural['final_multi_region_transferred_root_count']}"
        )
        lines.append("- selected correlations:")
        for key, value in cultural["correlations"].items():
            if key.endswith("_within_region") or key.endswith("_next_window"):
                lines.append(f"  - `{key}`: {_format(value)}")
        for event_name in (
            "high_scarcity_event_study",
            "high_crowding_event_study",
            "high_mortality_event_study",
        ):
            event = cultural[event_name]
            lines.append(f"- {event_name}: {event['event_count']} events")
            cohesion_event = event["outcomes"].get("cohesion", {})
            lines.append(
                f"  - cohesion post1-pre1: "
                f"{_format(cohesion_event.get('post1_minus_pre1'))}"
            )
        lines.append("")
    if any(run.get("capacity_final") for run in report["runs"]):
        lines.extend(["## Inherited elastic capacities", ""])
        for run in report["runs"]:
            values = run.get("capacity_final", {})
            if not values:
                continue
            context = run.get("config_context", {})
            lines.extend([
                f"### {run['run_name']}",
                f"- schema: `{values.get('differentiation_schema', context.get('differentiation_schema', 'disabled'))}`",
                f"- effective dimensions: {_format(values.get('capacity_effective_dimensions'))}",
                f"- working-memory dimensions mean/std: {_format(values.get('capacity_working_memory_dimensions_mean'))} / {_format(values.get('capacity_working_memory_dimensions_std'))}",
                f"- knowledge bytes mean/std: {_format(values.get('capacity_knowledge_capacity_bytes_mean'))} / {_format(values.get('capacity_knowledge_capacity_bytes_std'))}",
                f"- relation slots mean/std: {_format(values.get('capacity_relation_slots_mean'))} / {_format(values.get('capacity_relation_slots_std'))}",
                f"- attention slots mean/std: {_format(values.get('capacity_knowledge_attention_slots_mean'))} / {_format(values.get('capacity_knowledge_attention_slots_std'))}",
                f"- working-memory used/utilization/saturated: {_format(values.get('capacity_working_memory_used_dimensions_mean'))} / {_format(values.get('capacity_working_memory_utilization_mean'))} / {_format(values.get('capacity_working_memory_saturated_fraction'))}",
                f"- knowledge bytes used/utilization/saturated: {_format(values.get('capacity_knowledge_bytes_used_mean'))} / {_format(values.get('capacity_knowledge_utilization_mean'))} / {_format(values.get('capacity_knowledge_saturated_fraction'))}",
                f"- relation edges used/utilization/saturated: {_format(values.get('capacity_relation_edges_used_mean'))} / {_format(values.get('capacity_relation_utilization_mean'))} / {_format(values.get('capacity_relation_saturated_fraction'))}",
                f"- zero-attention fraction: {_format(values.get('capacity_attention_zero_fraction'))}",
                f"- final maintenance/development energy step: {_format(values.get('capacity_maintenance_energy_step'), 6)} / {_format(values.get('capacity_development_energy_step'), 6)}",
                f"- configured bounds: {context.get('differentiation_capacity_bounds')}",
                "- selected observational correlations:",
            ])
            for key, value in run.get("capacity_correlations_observational", {}).items():
                lines.append(f"  - `{key}`: {_format(value)}")
            lines.extend([
                "- boundary: capacity–outcome correlations can reflect shared selection and demographic drift; paired capacity-expression interventions are required for causal claims.",
                "",
            ])
    if any(run.get("subject_structure_final") for run in report["runs"]):
        lines.extend(["## Candidate-subject succession diagnostics", ""])
        for run in report["runs"]:
            values = run.get("subject_structure_final", {})
            if not values:
                continue
            lines.extend([
                f"### {run['run_name']}",
                f"- schema: `{values.get('subject_structure_schema', 'disabled')}`",
                f"- refreshes / active / effective groups: {values.get('subject_structure_refresh_count', 0)} / {values.get('subject_structure_active_groups', 0)} / {_format(values.get('subject_structure_effective_groups'))}",
                f"- weighted predecessor Jaccard / inheritance: {_format(values.get('subject_structure_weighted_jaccard'))} / {_format(values.get('subject_structure_weighted_inheritance'))}",
                f"- cumulative splits / merges / formations / dissolutions: {values.get('subject_structure_split_count_total', 0)} / {values.get('subject_structure_merge_count_total', 0)} / {values.get('subject_structure_formation_count_total', 0)} / {values.get('subject_structure_dissolution_count_total', 0)}",
                "",
            ])
    lines.extend(["## Realized resource demand", ""])
    for run in report["runs"]:
        demand = run.get("resource_demand_analysis", {})
        lines.append(f"### {run['run_name']}")
        if not demand.get("available", False):
            lines.append(f"- unavailable: {demand.get('reason', 'no harvest data')}")
            lines.append("")
            continue
        context = run.get("config_context", {})
        lines.extend([
            f"- harvest allocation schema: `{context.get('harvest_allocation_schema', 'uniform-channel-rates-v1')}`",
            f"- channel shares: {[round(float(value), 4) for value in demand.get('harvest_channel_shares', [])]}",
            f"- balance effective count: {_format(demand.get('harvest_balance_effective_count'))}",
            f"- temporal effective dimensions: {_format(demand.get('harvest_temporal_effective_dimensions'))}",
            f"- mean/max |channel correlation|: {_format(demand.get('harvest_channel_mean_abs_correlation'))} / {_format(demand.get('harvest_channel_max_abs_correlation'))}",
            f"- balance vs resource-field dimensions: {_format(demand.get('harvest_balance_vs_resource_environment_dimensions'))}",
            f"- realized/requested extraction efficiency mean/final: {_format(demand.get('harvest_extraction_efficiency_mean'))} / {_format(demand.get('harvest_extraction_efficiency_final'))}",
            "",
        ])
    if any(run.get("resource_environment_final") for run in report["runs"]):
        lines.extend(["## Orthogonal resource environment", ""])
        for run in report["runs"]:
            values = run.get("resource_environment_final", {})
            if not values:
                continue
            context = run.get("config_context", {})
            lines.extend([
                f"### {run['run_name']}",
                f"- schema: `{context.get('environment_schema', 'unknown')}`",
                f"- final resource effective dimensions: {_format(values.get('environment_resource_effective_dimensions'))}",
                f"- final resource mean/max absolute correlation: {_format(values.get('environment_resource_channel_mean_abs_correlation'))} / {_format(values.get('environment_resource_channel_max_abs_correlation'))}",
                f"- cycle periods: {context.get('resource_cycle_periods')}",
                f"- diffusion rates: {context.get('resource_diffusion_rates')}",
                "",
            ])
    if any(run.get("environment_atlas_final") for run in report["runs"]):
        lines.extend(["## Multiscale subject–environment atlas", ""])
        for run in report["runs"]:
            values = run.get("environment_atlas_final", {})
            if not values:
                continue
            lines.append(f"### {run['run_name']}")
            lines.append(f"- schema / scales: `{values.get('environment_atlas_schema', 'disabled')}` / {values.get('environment_atlas_scale_count', 0)}")
            scale_prefixes = sorted({key[: key.find('_signature_effective_dimensions')] for key in values if key.endswith('_signature_effective_dimensions')})
            for prefix in scale_prefixes:
                scale = prefix.removeprefix('environment_atlas_')
                lines.append(f"- {scale}: signature dims={_format(values.get(prefix + '_signature_effective_dimensions'))}, resource dims={_format(values.get(prefix + '_resource_effective_dimensions'))}, resource mean/max |corr|={_format(values.get(prefix + '_resource_mean_abs_correlation'))}/{_format(values.get(prefix + '_resource_max_abs_correlation'))}, mean distance={_format(values.get(prefix + '_signature_mean_distance'))}, turnover={_format(values.get(prefix + '_temporal_turnover'))}, lineage association={_format(values.get(prefix + '_lineage_association'))}, social association={_format(values.get(prefix + '_social_association'))}")
            lines.append("")
    lines.extend(["## Repeated local directional patterns", ""])
    if report.get("repeated_local_directional_patterns"):
        for key in report["repeated_local_directional_patterns"]:
            value = report["cross_seed_local_sign_consistency"][key]
            lines.append(
                f"- `{key}`: mean={_format(value['mean'])}, "
                f"range=[{_format(value['min'])}, {_format(value['max'])}]"
            )
    else:
        lines.append("- No local metric had the same non-zero sign in at least three runs.")
    lines.append("")
    lines.extend(["## Repeated directional patterns", ""])
    if report["repeated_directional_patterns"]:
        lines.extend(f"- `{key}`" for key in report["repeated_directional_patterns"])
    else:
        lines.append("- No metric had the same non-zero sign in at least three runs.")
    lines.extend(["", "## Interpretation boundary", "", report["interpretation_boundary"], ""])
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Analyze one or more evolution_progress JSONL files"
    )
    parser.add_argument("inputs", nargs="+", help="Evolution progress JSONL files")
    parser.add_argument("--output", required=True, help="Output directory")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=True)
    report = analyze(args.inputs)
    (output / "long_run_analysis.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (output / "long_run_analysis.md").write_text(
        render_markdown(report), encoding="utf-8"
    )


if __name__ == "__main__":
    main()
