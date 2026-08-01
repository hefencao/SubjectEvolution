"""Versioned environmental diversity primitives and audits.

The orthogonal resource schema keeps the world kernel fixed while assigning the
four existing resource channels independent spatial modes, temporal periods,
and diffusion scales.  It introduces no entity-aware process and does not
protect diversity.  All helpers accept a NumPy/CuPy-like ``xp`` module so the
CPU and device field stages share one mathematical definition.
"""

from __future__ import annotations

from dataclasses import dataclass
import argparse
import json
from pathlib import Path
from typing import Any

import numpy as np

from ..cfg import EnvironmentConfig, SimulationConfig, load_config


ORTHOGONAL_ENVIRONMENT_SCHEMA = "orthogonal-four-resource-niche-v1"
PERSISTENT_ORTHOGONAL_ENVIRONMENT_SCHEMA = "orthogonal-four-resource-renewal-v2"
MULTISCALE_PERSISTENT_ENVIRONMENT_SCHEMA = "persistent-multiscale-four-resource-renewal-v3"
STRUCTURED_PROVINCE_ENVIRONMENT_SCHEMA = "structured-province-resource-network-v4"
SPATIAL_PROCESSING_SUPPORT_SCHEMA = "phase-shifted-channel-processing-support-v1"
RESOURCE_DIVERSITY_AUDIT_SCHEMA = "resource-environment-diversity-audit-v1"
RESOURCE_CHANNELS = 4


def orthogonal_environment_enabled(config: EnvironmentConfig | SimulationConfig) -> bool:
    environment = config.environment if isinstance(config, SimulationConfig) else config
    return environment.schema in {
        ORTHOGONAL_ENVIRONMENT_SCHEMA,
        PERSISTENT_ORTHOGONAL_ENVIRONMENT_SCHEMA,
        MULTISCALE_PERSISTENT_ENVIRONMENT_SCHEMA,
        STRUCTURED_PROVINCE_ENVIRONMENT_SCHEMA,
    }


def normalized_grid(xx: Any, yy: Any, *, grid_x: int, grid_y: int, xp: Any) -> tuple[Any, Any]:
    return (
        xx.astype(xp.float64) / max(int(grid_x) - 1, 1),
        yy.astype(xp.float64) / max(int(grid_y) - 1, 1),
    )


def _wave_phase(vectors: tuple[tuple[float, float], ...], xnorm: Any, ynorm: Any, xp: Any) -> Any:
    values = xp.asarray(vectors, dtype=xp.float64)
    return 2.0 * xp.pi * (
        values[:, 0, None, None] * xnorm[None, :, :]
        + values[:, 1, None, None] * ynorm[None, :, :]
    )


def orthogonal_base_pattern(
    environment: EnvironmentConfig,
    xnorm: Any,
    ynorm: Any,
    *,
    xp: Any,
) -> Any:
    """Return four independent bounded spatial capacity fractions.

    The spatial modes are configuration data, not role labels.  Channels may
    still correlate for a particular configuration; the audit reports that
    rather than silently declaring the fields independent.
    """

    primary = _wave_phase(environment.resource_primary_wave_vectors, xnorm, ynorm, xp)
    secondary = _wave_phase(environment.resource_secondary_wave_vectors, xnorm, ynorm, xp)
    offsets = xp.asarray(
        environment.resource_temporal_phase_offsets, dtype=xp.float64
    )[:, None, None]
    primary_amplitude = xp.asarray(
        environment.resource_primary_wave_amplitudes, dtype=xp.float64
    )[:, None, None]
    secondary_amplitude = xp.asarray(
        environment.resource_secondary_wave_amplitudes, dtype=xp.float64
    )[:, None, None]
    pattern = (
        0.50
        + primary_amplitude * xp.sin(primary + offsets)
        + secondary_amplitude * xp.cos(secondary - 0.5 * offsets)
    )
    if environment.schema == STRUCTURED_PROVINCE_ENVIRONMENT_SCHEMA:
        pattern = pattern * resource_province_multiplier(
            environment, xnorm, ynorm, xp=xp
        )
    return xp.clip(pattern, 0.02, 0.98)


def persistent_orthogonal_renewal_enabled(
    config: EnvironmentConfig | SimulationConfig,
) -> bool:
    environment = config.environment if isinstance(config, SimulationConfig) else config
    return environment.schema in {
        PERSISTENT_ORTHOGONAL_ENVIRONMENT_SCHEMA,
        MULTISCALE_PERSISTENT_ENVIRONMENT_SCHEMA,
        STRUCTURED_PROVINCE_ENVIRONMENT_SCHEMA,
    }


def _periodic_distance(values: Any, centers: Any, xp: Any) -> Any:
    delta = xp.abs(values - centers)
    return xp.minimum(delta, 1.0 - delta)


def resource_province_multiplier(
    environment: EnvironmentConfig,
    xnorm: Any,
    ynorm: Any,
    *,
    xp: Any,
    processing: bool = False,
) -> Any:
    """Return channel-specific periodic province multipliers with unit means.

    Provinces are abiotic source/processing geometry.  The same deterministic
    transformation is used by CPU and GPU fields and never reads entity, group,
    lineage, policy, or historical success state.
    """

    centers = xp.asarray(environment.resource_province_centers, dtype=xp.float64)
    if processing:
        offsets = xp.asarray(
            environment.resource_processing_province_offsets, dtype=xp.float64
        )
        centers = xp.mod(centers + offsets, 1.0)
    radii = xp.asarray(environment.resource_province_radii, dtype=xp.float64)[:, None, None]
    contrasts = xp.asarray(
        environment.resource_province_contrasts, dtype=xp.float64
    )[:, None, None]
    cx = centers[:, 0, None, None]
    cy = centers[:, 1, None, None]
    dx = _periodic_distance(xnorm[None, :, :], cx, xp)
    dy = _periodic_distance(ynorm[None, :, :], cy, xp)
    primary = xp.exp(-(dx * dx + dy * dy) / (2.0 * radii * radii))

    # A weaker antipodal province prevents each channel becoming a single
    # point monopoly while retaining long-distance transport pressure.
    secondary_centers = xp.mod(centers + 0.5, 1.0)
    sx = _periodic_distance(
        xnorm[None, :, :], secondary_centers[:, 0, None, None], xp
    )
    sy = _periodic_distance(
        ynorm[None, :, :], secondary_centers[:, 1, None, None], xp
    )
    secondary = xp.exp(-(sx * sx + sy * sy) / (2.0 * radii * radii))
    density = (
        primary
        + float(environment.resource_province_secondary_weight) * secondary
    )
    raw = (1.0 - contrasts) + contrasts * density
    means = xp.mean(raw, axis=(1, 2), keepdims=True)
    return raw / xp.maximum(means, 1.0e-12)


def orthogonal_renewal_target_fraction(
    environment: EnvironmentConfig,
    xnorm: Any,
    ynorm: Any,
    *,
    tick: int,
    xp: Any,
) -> Any:
    """Return a moving channel-specific external renewal target.

    The v1 orthogonal schema only used its spatial pattern for initialization;
    logistic regeneration then drove every cell toward the same channel
    capacity.  The v2 schema treats those same role-free wave parameters as a
    continuously moving external source/sink target.  At tick zero this target
    equals :func:`orthogonal_base_pattern`, so the new contract changes renewal
    rather than the initial world.
    """

    primary = _wave_phase(environment.resource_primary_wave_vectors, xnorm, ynorm, xp)
    secondary = _wave_phase(
        environment.resource_secondary_wave_vectors, xnorm, ynorm, xp
    )
    offsets = xp.asarray(
        environment.resource_temporal_phase_offsets, dtype=xp.float64
    )[:, None, None]
    periods = xp.asarray(environment.resource_cycle_periods, dtype=xp.float64)
    temporal = 2.0 * xp.pi * float(tick) / periods
    temporal = temporal[:, None, None]
    primary_amplitude = xp.asarray(
        environment.resource_primary_wave_amplitudes, dtype=xp.float64
    )[:, None, None]
    secondary_amplitude = xp.asarray(
        environment.resource_secondary_wave_amplitudes, dtype=xp.float64
    )[:, None, None]
    cycle_amplitude = xp.asarray(
        environment.resource_cycle_amplitudes, dtype=xp.float64
    )[:, None, None]
    amplitude_modulation = 1.0 + cycle_amplitude * xp.sin(temporal)
    pattern = (
        0.50
        + primary_amplitude
        * amplitude_modulation
        * xp.sin(primary + offsets + temporal)
        + secondary_amplitude
        * amplitude_modulation
        * xp.cos(secondary - 0.5 * offsets - 0.6180339887498948 * temporal)
    )
    if environment.schema == STRUCTURED_PROVINCE_ENVIRONMENT_SCHEMA:
        pattern = pattern * resource_province_multiplier(
            environment, xnorm, ynorm, xp=xp
        )
    return xp.clip(pattern, 0.02, 0.98)


def orthogonal_processing_support_multiplier(
    environment: EnvironmentConfig,
    xnorm: Any,
    ynorm: Any,
    *,
    tick: int,
    xp: Any,
) -> Any:
    """Return a role-free channel-specific D3-E processing multiplier.

    The support field reuses the persistent-renewal wave basis but advances
    both wave components by a quarter cycle.  This spatially separates raw
    collection and processing opportunity without naming resources or adding
    material.  The configured amplitude is centered around one, so the
    spatial-support ablation can remove heterogeneity while preserving the
    neutral global throughput scale and all execution costs.
    """

    if environment.resource_processing_schema != SPATIAL_PROCESSING_SUPPORT_SCHEMA:
        shape = (RESOURCE_CHANNELS, *xnorm.shape)
        return xp.ones(shape, dtype=xp.float32)
    if environment.schema == STRUCTURED_PROVINCE_ENVIRONMENT_SCHEMA:
        province = resource_province_multiplier(
            environment, xnorm, ynorm, xp=xp, processing=True
        )
        centered = province - 1.0
        scale = xp.max(xp.abs(centered), axis=(1, 2), keepdims=True)
        centered = centered / xp.maximum(scale, 1.0e-12)
        amplitude = float(environment.resource_processing_support_amplitude)
        return xp.asarray(1.0 + amplitude * centered, dtype=xp.float32)
    primary = _wave_phase(environment.resource_primary_wave_vectors, xnorm, ynorm, xp)
    secondary = _wave_phase(
        environment.resource_secondary_wave_vectors, xnorm, ynorm, xp
    )
    offsets = xp.asarray(
        environment.resource_temporal_phase_offsets, dtype=xp.float64
    )[:, None, None]
    periods = xp.asarray(environment.resource_cycle_periods, dtype=xp.float64)
    temporal = (2.0 * xp.pi * float(tick) / periods)[:, None, None]
    quarter_cycle = 0.5 * xp.pi
    primary_amplitude = xp.asarray(
        environment.resource_primary_wave_amplitudes, dtype=xp.float64
    )[:, None, None]
    secondary_amplitude = xp.asarray(
        environment.resource_secondary_wave_amplitudes, dtype=xp.float64
    )[:, None, None]
    cycle_amplitude = xp.asarray(
        environment.resource_cycle_amplitudes, dtype=xp.float64
    )[:, None, None]
    amplitude_modulation = 1.0 + cycle_amplitude * xp.sin(
        temporal + quarter_cycle
    )
    fraction = (
        0.50
        + primary_amplitude
        * amplitude_modulation
        * xp.sin(primary + offsets + temporal + quarter_cycle)
        + secondary_amplitude
        * amplitude_modulation
        * xp.cos(
            secondary
            - 0.5 * offsets
            - 0.6180339887498948 * temporal
            + quarter_cycle
        )
    )
    fraction = xp.clip(fraction, 0.05, 0.95)
    centered = (fraction - 0.50) / 0.45
    amplitude = float(environment.resource_processing_support_amplitude)
    multiplier = 1.0 + amplitude * centered
    return xp.asarray(multiplier, dtype=xp.float32)


def orthogonal_seasonal_multiplier(
    environment: EnvironmentConfig,
    xnorm: Any,
    ynorm: Any,
    *,
    tick: int,
    xp: Any,
) -> Any:
    """Return channel-specific moving regeneration waves.

    Distinct periods and wave vectors prevent the schema from collapsing all
    channels onto one synchronized seasonal scalar.  Whether a concrete run
    actually has adequate independent variance remains an empirical question.
    """

    periods = xp.asarray(environment.resource_cycle_periods, dtype=xp.float64)
    amplitudes = xp.asarray(
        environment.resource_cycle_amplitudes, dtype=xp.float64
    )[:, None, None]
    offsets = xp.asarray(
        environment.resource_temporal_phase_offsets, dtype=xp.float64
    )[:, None, None]
    spatial = _wave_phase(environment.resource_primary_wave_vectors, xnorm, ynorm, xp)
    temporal = 2.0 * xp.pi * float(tick) / periods
    local_phase = temporal[:, None, None] + spatial + offsets
    return 1.0 + amplitudes * xp.sin(local_phase)


def diffuse_resource_fields(resources: Any, rates: tuple[float, float, float, float], *, xp: Any) -> Any:
    """Apply one stable four-neighbour diffusion step per channel."""

    result = resources
    for channel, raw_rate in enumerate(rates):
        rate = float(raw_rate)
        if rate <= 0.0:
            continue
        field = result[channel]
        mixed = (
            (xp.float32(1.0) - xp.float32(4.0 * rate)) * field
            + xp.float32(rate)
            * (
                xp.roll(field, 1, axis=0)
                + xp.roll(field, -1, axis=0)
                + xp.roll(field, 1, axis=1)
                + xp.roll(field, -1, axis=1)
            )
        )
        if result is resources:
            result = resources.copy()
        result[channel] = mixed.astype(xp.float32)
    return result


def _effective_dimensions(rows: np.ndarray) -> float:
    values = np.asarray(rows, dtype=np.float64)
    if values.ndim != 2 or min(values.shape) <= 1:
        return 0.0
    centered = values - values.mean(axis=0, keepdims=True)
    if not np.any(centered):
        return 0.0
    singular = np.linalg.svd(centered, compute_uv=False)
    spectrum = singular * singular
    denominator = float(np.dot(spectrum, spectrum))
    return float(spectrum.sum() ** 2 / denominator) if denominator > 0.0 else 0.0



def configured_resource_scale_metrics(
    environment: EnvironmentConfig,
    *,
    grid_x: int,
    grid_y: int,
) -> dict[str, Any]:
    """Describe configured channel wavelengths without interpreting fitness.

    Wave vectors are measured in cycles across the normalized toroidal world.
    The reported cell wavelengths expose whether a concrete configuration
    actually presents distinct spatial scales to inherited sensing radii.
    """

    def rows(vectors: tuple[tuple[float, float], ...]) -> list[dict[str, float]]:
        result: list[dict[str, float]] = []
        for x_cycles, y_cycles in vectors:
            x = float(x_cycles)
            y = float(y_cycles)
            magnitude = float(np.hypot(x, y))
            wavelength = 0.0 if magnitude <= 0.0 else float(min(grid_x, grid_y) / magnitude)
            result.append(
                {
                    "x_cycles": x,
                    "y_cycles": y,
                    "cycles_magnitude": magnitude,
                    "approx_wavelength_cells": wavelength,
                }
            )
        return result

    primary = rows(environment.resource_primary_wave_vectors)
    secondary = rows(environment.resource_secondary_wave_vectors)
    wavelengths = sorted(
        row["approx_wavelength_cells"] for row in primary if row["approx_wavelength_cells"] > 0.0
    )
    separation = (
        float(wavelengths[-1] / wavelengths[0])
        if len(wavelengths) >= 2 and wavelengths[0] > 0.0
        else 1.0
    )
    return {
        "schema": "configured-resource-spatial-scales-v1",
        "primary": primary,
        "secondary": secondary,
        "primary_wavelength_separation_ratio": separation,
        "channel_scale_count": len({round(row["cycles_magnitude"], 12) for row in primary}),
    }

def resource_field_diversity_metrics(
    resources: Any,
    capacities: tuple[float, float, float, float] | np.ndarray,
) -> dict[str, Any]:
    """Measure spatial independence of the four authoritative resource fields."""

    values = np.asarray(resources, dtype=np.float64)
    capacity = np.asarray(capacities, dtype=np.float64)
    if values.ndim != 3 or values.shape[0] != RESOURCE_CHANNELS:
        raise ValueError("resource diversity metrics require [4, grid_y, grid_x]")
    if capacity.shape != (RESOURCE_CHANNELS,) or np.any(capacity <= 0.0):
        raise ValueError("resource diversity metrics require four positive capacities")
    normalized = values / capacity[:, None, None]
    rows = normalized.reshape(RESOURCE_CHANNELS, -1).T
    centered_channels = rows - rows.mean(axis=0, keepdims=True)
    std = centered_channels.std(axis=0)
    correlation = np.eye(RESOURCE_CHANNELS, dtype=np.float64)
    for left in range(RESOURCE_CHANNELS):
        for right in range(left + 1, RESOURCE_CHANNELS):
            if std[left] <= 1e-30 or std[right] <= 1e-30:
                value = 0.0
            else:
                value = float(
                    np.mean(centered_channels[:, left] * centered_channels[:, right])
                    / (std[left] * std[right])
                )
                value = float(np.clip(value, -1.0, 1.0))
            correlation[left, right] = value
            correlation[right, left] = value
    upper = np.abs(correlation[np.triu_indices(RESOURCE_CHANNELS, k=1)])
    means = rows.mean(axis=0)
    cv = np.zeros(RESOURCE_CHANNELS, dtype=np.float64)
    np.divide(std, np.abs(means), out=cv, where=np.abs(means) > 1e-30)
    return {
        "schema": "resource-field-diversity-metrics-v1",
        "resource_effective_dimensions": _effective_dimensions(rows),
        "resource_channel_correlation": correlation.tolist(),
        "resource_channel_mean_abs_correlation": float(upper.mean()) if upper.size else 0.0,
        "resource_channel_max_abs_correlation": float(upper.max(initial=0.0)),
        "resource_spatial_cv_by_channel": cv.tolist(),
        "resource_spatial_cv_mean": float(cv.mean()),
    }


def temporal_resource_diversity_metrics(samples: np.ndarray) -> dict[str, Any]:
    """Measure independence of sampled channel trajectories.

    ``samples`` is shaped ``[sample, channel, cell]`` and is centered per cell
    so the metric reflects temporal variation rather than only static spatial
    offsets.
    """

    values = np.asarray(samples, dtype=np.float64)
    if values.ndim != 3 or values.shape[1] != RESOURCE_CHANNELS:
        raise ValueError("temporal resource samples must be [sample, 4, cell]")
    if values.shape[0] <= 1:
        return {
            "resource_temporal_effective_dimensions": 0.0,
            "resource_temporal_channel_correlation": np.eye(RESOURCE_CHANNELS).tolist(),
            "resource_temporal_mean_abs_correlation": 0.0,
            "resource_temporal_max_abs_correlation": 0.0,
        }
    deltas = np.diff(values, axis=0)
    rows = np.transpose(deltas, (0, 2, 1)).reshape(-1, RESOURCE_CHANNELS)
    centered = rows - rows.mean(axis=0, keepdims=True)
    std = centered.std(axis=0)
    correlation = np.eye(RESOURCE_CHANNELS, dtype=np.float64)
    for left in range(RESOURCE_CHANNELS):
        for right in range(left + 1, RESOURCE_CHANNELS):
            if std[left] <= 1e-30 or std[right] <= 1e-30:
                value = 0.0
            else:
                value = float(np.mean(centered[:, left] * centered[:, right]) / (std[left] * std[right]))
                value = float(np.clip(value, -1.0, 1.0))
            correlation[left, right] = value
            correlation[right, left] = value
    upper = np.abs(correlation[np.triu_indices(RESOURCE_CHANNELS, k=1)])
    return {
        "resource_temporal_effective_dimensions": _effective_dimensions(rows),
        "resource_temporal_channel_correlation": correlation.tolist(),
        "resource_temporal_mean_abs_correlation": float(upper.mean()) if upper.size else 0.0,
        "resource_temporal_max_abs_correlation": float(upper.max(initial=0.0)),
    }


def build_resource_diversity_audit(
    cfg: SimulationConfig,
    *,
    ticks: int,
    sample_period: int,
) -> dict[str, Any]:
    from .world import Environment

    if ticks <= 0 or sample_period <= 0:
        raise ValueError("ticks and sample_period must be positive")
    environment = Environment(cfg)
    samples: list[np.ndarray] = [
        environment.resources.astype(np.float64)
        / np.asarray(cfg.environment.resource_capacity, dtype=np.float64)[:, None, None]
    ]
    sample_ticks = [0]
    for tick in range(1, ticks + 1):
        environment.update(tick)
        if tick % sample_period == 0 or tick == ticks:
            samples.append(
                environment.resources.astype(np.float64)
                / np.asarray(cfg.environment.resource_capacity, dtype=np.float64)[:, None, None]
            )
            sample_ticks.append(tick)
    stacked = np.stack([sample.reshape(RESOURCE_CHANNELS, -1) for sample in samples], axis=0)
    spatial = [
        resource_field_diversity_metrics(sample, np.ones(RESOURCE_CHANNELS, dtype=np.float64))
        for sample in samples
    ]
    temporal = temporal_resource_diversity_metrics(stacked)
    return {
        "schema": RESOURCE_DIVERSITY_AUDIT_SCHEMA,
        "environment_schema": cfg.environment.schema,
        "ticks": int(ticks),
        "sample_period": int(sample_period),
        "sample_ticks": sample_ticks,
        "spatial_effective_dimensions_mean": float(
            np.mean([row["resource_effective_dimensions"] for row in spatial])
        ),
        "spatial_effective_dimensions_min": float(
            np.min([row["resource_effective_dimensions"] for row in spatial])
        ),
        "spatial_mean_abs_correlation_mean": float(
            np.mean([row["resource_channel_mean_abs_correlation"] for row in spatial])
        ),
        "spatial_max_abs_correlation_max": float(
            np.max([row["resource_channel_max_abs_correlation"] for row in spatial])
        ),
        **temporal,
        "samples": [
            {
                "tick": int(tick),
                **metrics,
            }
            for tick, metrics in zip(sample_ticks, spatial, strict=True)
        ],
        "interpretation_boundary": (
            "This audit measures exogenous resource-field diversity without entity harvesting. "
            "It does not prove ecological differentiation or selection."
        ),
    }


def _write_markdown(report: dict[str, Any], path: Path) -> None:
    lines = [
        "# Resource environment diversity audit",
        "",
        f"- Schema: `{report['schema']}`",
        f"- Environment schema: `{report['environment_schema']}`",
        f"- Ticks / sample period: {report['ticks']} / {report['sample_period']}",
        f"- Spatial effective dimensions, mean/min: {report['spatial_effective_dimensions_mean']:.4f} / {report['spatial_effective_dimensions_min']:.4f}",
        f"- Spatial mean absolute channel correlation: {report['spatial_mean_abs_correlation_mean']:.4f}",
        f"- Spatial maximum absolute channel correlation: {report['spatial_max_abs_correlation_max']:.4f}",
        f"- Temporal effective dimensions: {report['resource_temporal_effective_dimensions']:.4f}",
        f"- Temporal mean/max absolute correlation: {report['resource_temporal_mean_abs_correlation']:.4f} / {report['resource_temporal_max_abs_correlation']:.4f}",
        "",
        "> " + report["interpretation_boundary"],
        "",
        "| Tick | Spatial dims | Mean | Max |",
        "|---:|---:|---:|---:|",
    ]
    for sample in report["samples"]:
        lines.append(
            f"| {sample['tick']} | {sample['resource_effective_dimensions']:.4f} | "
            f"{sample['resource_channel_mean_abs_correlation']:.4f} | "
            f"{sample['resource_channel_max_abs_correlation']:.4f} |"
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--ticks", type=int, default=600)
    parser.add_argument("--sample-period", type=int, default=10)
    args = parser.parse_args(argv)
    cfg = load_config(args.config)
    report = build_resource_diversity_audit(
        cfg,
        ticks=args.ticks,
        sample_period=args.sample_period,
    )
    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=True)
    (output / "resource_environment_diversity_audit.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    _write_markdown(report, output / "resource_environment_diversity_audit.md")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())


__all__ = [
    "ORTHOGONAL_ENVIRONMENT_SCHEMA",
    "PERSISTENT_ORTHOGONAL_ENVIRONMENT_SCHEMA",
    "SPATIAL_PROCESSING_SUPPORT_SCHEMA",
    "RESOURCE_DIVERSITY_AUDIT_SCHEMA",
    "build_resource_diversity_audit",
    "diffuse_resource_fields",
    "MULTISCALE_PERSISTENT_ENVIRONMENT_SCHEMA",
    "configured_resource_scale_metrics",
    "orthogonal_base_pattern",
    "orthogonal_environment_enabled",
    "orthogonal_processing_support_multiplier",
    "orthogonal_renewal_target_fraction",
    "persistent_orthogonal_renewal_enabled",
    "orthogonal_seasonal_multiplier",
    "resource_field_diversity_metrics",
    "temporal_resource_diversity_metrics",
]
