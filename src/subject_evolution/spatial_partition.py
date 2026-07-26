"""Versioned, diagnostic-only spatial region partitions.

The simulation world and physical grid remain authoritative.  This module only
maps continuous positions onto an analysis grid used by local stress, event
cohort, and natural-event planning diagnostics.  It never feeds movement,
policy, resources, lifecycle, relations, knowledge, or group formation.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from typing import Any

import numpy as np


NORMALIZED_FIXED_COUNT_SCHEMA = "normalized-fixed-count-grid-v1"
SUPPORTED_SCHEMAS = {NORMALIZED_FIXED_COUNT_SCHEMA}


def _canonical_sha256(payload: dict[str, Any]) -> str:
    encoded = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


@dataclass(frozen=True)
class SpatialRegionPartition:
    """Map positions to a row-major normalized rectangular analysis grid.

    ``normalized-fixed-count-grid-v1`` preserves the historical semantics:
    region counts are configured directly and boundaries are equal fractions
    of world width and height.  Increasing physical map size while retaining
    the same region counts therefore increases physical region size; increasing
    world-grid resolution while retaining the same physical map changes the
    number of physical cells represented by each analysis region.
    """

    world_width: float
    world_height: float
    world_grid_x: int
    world_grid_y: int
    regions_x: int
    regions_y: int
    schema: str = NORMALIZED_FIXED_COUNT_SCHEMA

    def __post_init__(self) -> None:
        if self.schema not in SUPPORTED_SCHEMAS:
            raise ValueError(f"unsupported spatial region partition schema {self.schema!r}")
        if self.world_width <= 0.0 or self.world_height <= 0.0:
            raise ValueError("spatial region world dimensions must be positive")
        if self.world_grid_x <= 0 or self.world_grid_y <= 0:
            raise ValueError("spatial region world-grid dimensions must be positive")
        if self.regions_x <= 0 or self.regions_y <= 0:
            raise ValueError("spatial region dimensions must be positive")
        if self.regions_x > self.world_grid_x or self.regions_y > self.world_grid_y:
            raise ValueError("spatial region grid cannot exceed the physical world grid")

    @property
    def region_count(self) -> int:
        return int(self.regions_x * self.regions_y)

    def region_ids(self, x: np.ndarray, y: np.ndarray) -> np.ndarray:
        px = np.asarray(x, dtype=np.float64)
        py = np.asarray(y, dtype=np.float64)
        if px.shape != py.shape:
            raise ValueError("spatial region x/y arrays must have identical shapes")
        rx = np.floor(px / self.world_width * self.regions_x).astype(np.int64)
        ry = np.floor(py / self.world_height * self.regions_y).astype(np.int64)
        rx = np.clip(rx, 0, self.regions_x - 1)
        ry = np.clip(ry, 0, self.regions_y - 1)
        return (ry * self.regions_x + rx).astype(np.int32, copy=False)

    def region_coordinates(self, region_id: int) -> tuple[int, int]:
        value = int(region_id)
        if value < 0 or value >= self.region_count:
            raise ValueError("region ID is outside the spatial partition")
        return value % self.regions_x, value // self.regions_x

    def region_bounds(self, region_id: int) -> dict[str, float | int]:
        rx, ry = self.region_coordinates(region_id)
        x0 = rx / self.regions_x
        x1 = (rx + 1) / self.regions_x
        y0 = ry / self.regions_y
        y1 = (ry + 1) / self.regions_y
        return {
            "region_id": int(region_id),
            "region_x": int(rx),
            "region_y": int(ry),
            "normalized_x_min": float(x0),
            "normalized_x_max": float(x1),
            "normalized_y_min": float(y0),
            "normalized_y_max": float(y1),
            "physical_x_min": float(x0 * self.world_width),
            "physical_x_max": float(x1 * self.world_width),
            "physical_y_min": float(y0 * self.world_height),
            "physical_y_max": float(y1 * self.world_height),
        }

    def metadata(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "schema": self.schema,
            "mapping": "row-major-y-then-x",
            "boundary_convention": "half-open except clipped outer boundary",
            "regions_x": int(self.regions_x),
            "regions_y": int(self.regions_y),
            "region_count": self.region_count,
            "world_width": float(self.world_width),
            "world_height": float(self.world_height),
            "world_grid_x": int(self.world_grid_x),
            "world_grid_y": int(self.world_grid_y),
            "normalized_region_width": float(1.0 / self.regions_x),
            "normalized_region_height": float(1.0 / self.regions_y),
            "physical_region_width": float(self.world_width / self.regions_x),
            "physical_region_height": float(self.world_height / self.regions_y),
            "world_cells_per_region_x": float(self.world_grid_x / self.regions_x),
            "world_cells_per_region_y": float(self.world_grid_y / self.regions_y),
            "world_grid_aligned": bool(
                self.world_grid_x % self.regions_x == 0
                and self.world_grid_y % self.regions_y == 0
            ),
            "feedback_to_world": False,
            "map_size_semantics": (
                "fixed region counts over normalized coordinates; physical area and represented "
                "world-cell count scale with map dimensions and resolution"
            ),
        }
        payload["partition_sha256"] = _canonical_sha256(payload)
        return payload

    def normalized_topology(self) -> dict[str, Any]:
        payload = {
            "schema": self.schema,
            "regions_x": int(self.regions_x),
            "regions_y": int(self.regions_y),
            "mapping": "row-major-y-then-x",
        }
        payload["topology_sha256"] = _canonical_sha256(payload)
        return payload
