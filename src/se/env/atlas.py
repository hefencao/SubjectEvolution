"""Diagnostic multiscale environment signatures and subject exposure structure.

The atlas samples authoritative resource, hazard, and mortality-trace fields at
low-frequency evaluation points.  It partitions those fields at configured
normalized scales and measures heterogeneity plus the association between
candidate subject labels and realized environmental exposure.  No atlas value
feeds policy, movement, group formation, knowledge, lifecycle, or fields.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

import numpy as np

from .partition import NORMALIZED_FIXED_COUNT_SCHEMA, SpatialRegionPartition


ENVIRONMENT_ATLAS_SCHEMA = "multiscale-subject-environment-atlas-v1"
ENVIRONMENT_ATLAS_ORTHOGONAL_SCHEMA = "multiscale-subject-environment-atlas-v2"


def _effective_count(values: np.ndarray) -> float:
    counts = np.asarray(values, dtype=np.float64)
    counts = counts[counts > 0.0]
    if counts.size == 0:
        return 0.0
    shares = counts / counts.sum()
    return float(1.0 / np.sum(shares * shares))


def _effective_dimensions(rows: np.ndarray) -> float:
    values = np.asarray(rows, dtype=np.float64)
    if values.ndim != 2 or values.shape[0] <= 1:
        return 0.0
    centered = values - values.mean(axis=0, keepdims=True)
    if not np.any(centered):
        return 0.0
    singular = np.linalg.svd(centered, compute_uv=False)
    spectrum = singular * singular
    denominator = float(np.dot(spectrum, spectrum))
    return float(spectrum.sum() ** 2 / denominator) if denominator > 0.0 else 0.0




def _channel_correlation_metrics(rows: np.ndarray) -> tuple[float, float, list[list[float]]]:
    values = np.asarray(rows, dtype=np.float64)
    if values.ndim != 2 or values.shape[1] != 4:
        raise ValueError("resource channel correlation rows must be shaped [N, 4]")
    centered = values - values.mean(axis=0, keepdims=True)
    std = centered.std(axis=0)
    correlation = np.eye(4, dtype=np.float64)
    for left in range(4):
        for right in range(left + 1, 4):
            if std[left] <= 1e-30 or std[right] <= 1e-30:
                value = 0.0
            else:
                value = float(
                    np.mean(centered[:, left] * centered[:, right])
                    / (std[left] * std[right])
                )
                value = float(np.clip(value, -1.0, 1.0))
            correlation[left, right] = value
            correlation[right, left] = value
    upper = np.abs(correlation[np.triu_indices(4, k=1)])
    return (
        float(upper.mean()) if upper.size else 0.0,
        float(upper.max(initial=0.0)),
        correlation.tolist(),
    )

def _mean_pairwise_distance(rows: np.ndarray) -> tuple[float, float]:
    values = np.asarray(rows, dtype=np.float64)
    if values.ndim != 2 or values.shape[0] <= 1:
        return 0.0, 0.0
    squared = np.sum((values[:, None, :] - values[None, :, :]) ** 2, axis=2)
    upper = np.sqrt(squared[np.triu_indices(values.shape[0], k=1)])
    return float(upper.mean()) if upper.size else 0.0, float(upper.max(initial=0.0))


def _association_fraction(
    signatures: np.ndarray,
    labels: np.ndarray,
    *,
    min_members: int = 2,
) -> tuple[float, float, float, float]:
    x_all = np.asarray(signatures, dtype=np.float64)
    y_all = np.asarray(labels)
    nonzero = y_all != 0
    if not np.any(nonzero):
        return 0.0, 0.0, 0.0, 0.0
    unique_all, counts_all = np.unique(y_all[nonzero], return_counts=True)
    eligible_labels = unique_all[counts_all >= int(min_members)]
    eligible = nonzero & np.isin(y_all, eligible_labels)
    covered_fraction = float(np.count_nonzero(eligible) / np.count_nonzero(nonzero))
    x = x_all[eligible]
    y = y_all[eligible]
    if x.shape[0] <= 1:
        return 0.0, float(eligible_labels.size), 0.0, covered_fraction
    unique, inverse, counts = np.unique(y, return_inverse=True, return_counts=True)
    if unique.size <= 1:
        return 0.0, float(unique.size), _effective_count(counts), covered_fraction
    global_mean = x.mean(axis=0)
    total = float(np.sum((x - global_mean) ** 2))
    if total <= 1e-30:
        return 0.0, float(unique.size), _effective_count(counts), covered_fraction
    sums = np.zeros((unique.size, x.shape[1]), dtype=np.float64)
    np.add.at(sums, inverse, x)
    means = sums / counts[:, None]
    between = float(np.sum(counts[:, None] * (means - global_mean) ** 2))
    return (
        float(np.clip(between / total, 0.0, 1.0)),
        float(unique.size),
        _effective_count(counts),
        covered_fraction,
    )


def _mean_subject_span(region_ids: np.ndarray, labels: np.ndarray, region_count: int) -> float:
    regions = np.asarray(region_ids, dtype=np.int32)
    subject_labels = np.asarray(labels)
    valid = subject_labels != 0
    regions = regions[valid]
    subject_labels = subject_labels[valid]
    if subject_labels.size == 0:
        return 0.0
    unique, inverse, counts = np.unique(subject_labels, return_inverse=True, return_counts=True)
    spans = np.zeros(unique.size, dtype=np.float64)
    for row in range(unique.size):
        spans[row] = np.unique(regions[inverse == row]).size / region_count
    return float(np.average(spans, weights=counts))


class EnvironmentAtlasDiagnostics:
    """Record multiscale environment heterogeneity and subject exposure metrics."""

    def __init__(
        self,
        output_dir: str | Path,
        *,
        world_width: float,
        world_height: float,
        world_grid_x: int,
        world_grid_y: int,
        resource_capacity: tuple[float, float, float, float],
        scales: tuple[tuple[int, int], ...],
        schema: str = ENVIRONMENT_ATLAS_SCHEMA,
    ) -> None:
        if schema not in {
            ENVIRONMENT_ATLAS_SCHEMA,
            ENVIRONMENT_ATLAS_ORTHOGONAL_SCHEMA,
        }:
            raise ValueError(f"unsupported environment atlas schema {schema!r}")
        self.output_dir = Path(output_dir)
        self.schema = schema
        self.resource_capacity = np.asarray(resource_capacity, dtype=np.float64)
        if self.resource_capacity.shape != (4,) or np.any(self.resource_capacity <= 0.0):
            raise ValueError("environment atlas requires four positive resource capacities")
        self.partitions = tuple(
            SpatialRegionPartition(
                world_width=float(world_width),
                world_height=float(world_height),
                world_grid_x=int(world_grid_x),
                world_grid_y=int(world_grid_y),
                regions_x=int(scale[0]),
                regions_y=int(scale[1]),
                schema=NORMALIZED_FIXED_COUNT_SCHEMA,
            )
            for scale in scales
        )
        if not self.partitions:
            raise ValueError("environment atlas requires at least one spatial scale")
        self.grid_region_ids: dict[str, np.ndarray] = {}
        x_centers = (np.arange(world_grid_x, dtype=np.float64) + 0.5) * (
            float(world_width) / world_grid_x
        )
        y_centers = (np.arange(world_grid_y, dtype=np.float64) + 0.5) * (
            float(world_height) / world_grid_y
        )
        xx, yy = np.meshgrid(x_centers, y_centers)
        for partition in self.partitions:
            key = self._scale_key(partition)
            self.grid_region_ids[key] = partition.region_ids(xx, yy).reshape(-1)
        self.previous_signatures: dict[str, np.ndarray] = {}
        self.records: list[dict[str, Any]] = []

    @staticmethod
    def _scale_key(partition: SpatialRegionPartition) -> str:
        return f"{partition.regions_x}x{partition.regions_y}"

    def clone(self, output_dir: str | Path) -> "EnvironmentAtlasDiagnostics":
        result = copy.deepcopy(self)
        result.output_dir = Path(output_dir)
        return result

    def snapshot_state(self) -> dict[str, Any]:
        state = copy.deepcopy(self.__dict__)
        state.pop("output_dir", None)
        return state

    def restore_state(self, state: dict[str, Any]) -> None:
        output_dir = self.output_dir
        for key, value in state.items():
            setattr(self, key, copy.deepcopy(value))
        self.output_dir = output_dir

    def metadata(self) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "feedback_to_world": False,
            "signature_dimensions": [
                "resource_0_fraction",
                "resource_1_fraction",
                "resource_2_fraction",
                "resource_3_fraction",
                "hazard",
                "mortality_trace",
            ],
            "scales": [partition.metadata() for partition in self.partitions],
            "subject_association_interpretation": (
                "between-subject share of realized regional exposure variance among "
                "labels with at least two members; descriptive, not causal and not a "
                "subjecthood score"
            ),
            "resource_independence_metrics": (
                self.schema == ENVIRONMENT_ATLAS_ORTHOGONAL_SCHEMA
            ),
        }

    @staticmethod
    def _regional_mean(flat_values: np.ndarray, region_ids: np.ndarray, count: int) -> np.ndarray:
        values = np.asarray(flat_values, dtype=np.float64)
        sums = np.bincount(region_ids, weights=values, minlength=count).astype(np.float64)
        cells = np.bincount(region_ids, minlength=count).astype(np.float64)
        result = np.zeros(count, dtype=np.float64)
        np.divide(sums, cells, out=result, where=cells > 0.0)
        return result

    def observe(
        self,
        *,
        tick: int,
        resources: np.ndarray,
        hazard: np.ndarray,
        mortality_trace: np.ndarray,
        alive: np.ndarray,
        x: np.ndarray,
        y: np.ndarray,
        lineage_ids: np.ndarray,
        group_ids: np.ndarray,
    ) -> dict[str, Any]:
        fields = np.asarray(resources, dtype=np.float64)
        hazard_values = np.asarray(hazard, dtype=np.float64)
        trace_values = np.asarray(mortality_trace, dtype=np.float64)
        if fields.ndim != 3 or fields.shape[0] != 4:
            raise ValueError("environment atlas resources must be shaped [4, grid_y, grid_x]")
        if hazard_values.shape != fields.shape[1:] or trace_values.shape != fields.shape[1:]:
            raise ValueError("environment atlas scalar fields must match the resource grid")
        active = np.flatnonzero(np.asarray(alive, dtype=bool)).astype(np.int32)
        px = np.asarray(x, dtype=np.float64)
        py = np.asarray(y, dtype=np.float64)
        lineages = np.asarray(lineage_ids)
        groups = np.asarray(group_ids)

        scale_records: list[dict[str, Any]] = []
        compact: dict[str, Any] = {
            "environment_atlas_schema": self.schema,
            "environment_atlas_scale_count": len(self.partitions),
        }
        resource_fractions = fields / self.resource_capacity[:, None, None]
        for partition in self.partitions:
            key = self._scale_key(partition)
            grid_regions = self.grid_region_ids[key]
            region_count = partition.region_count
            regional_resources = np.stack(
                [
                    self._regional_mean(resource_fractions[channel].reshape(-1), grid_regions, region_count)
                    for channel in range(4)
                ],
                axis=1,
            )
            regional_hazard = self._regional_mean(
                hazard_values.reshape(-1), grid_regions, region_count
            )
            regional_trace = self._regional_mean(
                trace_values.reshape(-1), grid_regions, region_count
            )
            signatures = np.column_stack(
                (regional_resources, regional_hazard, regional_trace)
            )
            resource_total = regional_resources.sum(axis=1)
            resource_composition = np.zeros_like(regional_resources)
            np.divide(
                regional_resources,
                resource_total[:, None],
                out=resource_composition,
                where=resource_total[:, None] > 0.0,
            )
            resource_effective = np.zeros(region_count, dtype=np.float64)
            denominator = np.sum(resource_composition * resource_composition, axis=1)
            np.divide(1.0, denominator, out=resource_effective, where=denominator > 0.0)
            channel_means = regional_resources.mean(axis=0)
            channel_std = regional_resources.std(axis=0)
            channel_cv = np.zeros(4, dtype=np.float64)
            np.divide(channel_std, channel_means, out=channel_cv, where=np.abs(channel_means) > 1e-30)
            mean_distance, max_distance = _mean_pairwise_distance(signatures)
            previous = self.previous_signatures.get(key)
            turnover = (
                float(np.mean(np.abs(signatures - previous)))
                if previous is not None and previous.shape == signatures.shape
                else 0.0
            )
            self.previous_signatures[key] = signatures.copy()

            if active.size:
                entity_regions = partition.region_ids(px[active], py[active])
                entity_signatures = signatures[entity_regions]
                region_population = np.bincount(
                    entity_regions, minlength=region_count
                ).astype(np.int64)
                (
                    lineage_association,
                    lineage_count,
                    lineage_effective,
                    lineage_covered_fraction,
                ) = _association_fraction(entity_signatures, lineages[active])
                (
                    social_association,
                    social_count,
                    social_effective,
                    social_covered_fraction,
                ) = _association_fraction(entity_signatures, groups[active])
                lineage_span = _mean_subject_span(
                    entity_regions, lineages[active], region_count
                )
                social_span = _mean_subject_span(
                    entity_regions, groups[active], region_count
                )
            else:
                entity_regions = np.empty(0, dtype=np.int32)
                region_population = np.zeros(region_count, dtype=np.int64)
                lineage_association = social_association = 0.0
                lineage_count = social_count = 0.0
                lineage_effective = social_effective = 0.0
                lineage_covered_fraction = social_covered_fraction = 0.0
                lineage_span = social_span = 0.0

            resource_mean_abs_correlation, resource_max_abs_correlation, resource_correlation = (
                _channel_correlation_metrics(regional_resources)
            )
            scale_record = {
                "scale": key,
                "partition": partition.metadata(),
                "region_signature_effective_dimensions": _effective_dimensions(signatures),
                "region_signature_mean_pairwise_distance": mean_distance,
                "region_signature_max_pairwise_distance": max_distance,
                "region_signature_temporal_turnover": turnover,
                "resource_spatial_cv_mean": float(channel_cv.mean()),
                "resource_spatial_cv_by_channel": channel_cv.tolist(),
                "regional_resource_effective_dimensions_mean": float(resource_effective.mean()),
                "resource_field_effective_dimensions": _effective_dimensions(
                    regional_resources
                ),
                "resource_channel_mean_abs_correlation": resource_mean_abs_correlation,
                "resource_channel_max_abs_correlation": resource_max_abs_correlation,
                "resource_channel_correlation": resource_correlation,
                "occupied_region_count": int(np.count_nonzero(region_population)),
                "entity_region_effective_count": _effective_count(region_population),
                "lineage_environment_association_fraction": lineage_association,
                "lineage_subject_count": int(lineage_count),
                "lineage_subject_effective_count": lineage_effective,
                "lineage_subject_covered_fraction": lineage_covered_fraction,
                "lineage_mean_region_span_fraction": lineage_span,
                "social_environment_association_fraction": social_association,
                "social_subject_count": int(social_count),
                "social_subject_effective_count": social_effective,
                "social_subject_covered_fraction": social_covered_fraction,
                "social_mean_region_span_fraction": social_span,
                "region_population": region_population.tolist(),
                "region_signatures": signatures.tolist(),
            }
            scale_records.append(scale_record)
            prefix = f"environment_atlas_{key}_"
            compact.update(
                {
                    prefix + "signature_effective_dimensions": scale_record[
                        "region_signature_effective_dimensions"
                    ],
                    prefix + "signature_mean_distance": mean_distance,
                    prefix + "temporal_turnover": turnover,
                    prefix + "resource_spatial_cv_mean": float(channel_cv.mean()),
                    prefix + "resource_effective_dimensions": scale_record[
                        "resource_field_effective_dimensions"
                    ],
                    prefix + "resource_mean_abs_correlation": resource_mean_abs_correlation,
                    prefix + "resource_max_abs_correlation": resource_max_abs_correlation,
                    prefix + "entity_region_effective_count": scale_record[
                        "entity_region_effective_count"
                    ],
                    prefix + "lineage_association": lineage_association,
                    prefix + "lineage_covered_fraction": lineage_covered_fraction,
                    prefix + "social_association": social_association,
                    prefix + "social_covered_fraction": social_covered_fraction,
                    prefix + "lineage_span": lineage_span,
                    prefix + "social_span": social_span,
                }
            )

        record = {
            "schema": self.schema,
            "tick": int(tick),
            "scales": scale_records,
            "interpretation_boundary": (
                "Environmental signatures and subject exposure associations are "
                "observational. They do not identify environmental causes or subjecthood."
            ),
        }
        self.records.append(record)
        return compact

    def summary(self) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "evaluation_count": len(self.records),
            "metadata": self.metadata(),
            "last": self.records[-1] if self.records else None,
        }

    def close(self) -> None:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        with (self.output_dir / "environment_atlas.jsonl").open(
            "w", encoding="utf-8"
        ) as stream:
            for record in self.records:
                stream.write(json.dumps(record, sort_keys=True) + "\n")
        (self.output_dir / "environment_atlas_summary.json").write_text(
            json.dumps(self.summary(), indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )


__all__ = [
    "ENVIRONMENT_ATLAS_SCHEMA",
    "ENVIRONMENT_ATLAS_ORTHOGONAL_SCHEMA",
    "EnvironmentAtlasDiagnostics",
]
