"""Diagnostic-only endpoint decomposition for natural-event region populations.

The tracker freezes the set of living stable entity IDs at each preregistered
nominal event tick.  At the anchor horizon it decomposes endpoint regional
population change into retained cohort members, surviving out-migrants,
cohort deaths/absence, in-migrants that already existed at the event tick, and
post-event births that remain alive in the region.

The diagnostic never feeds policy, movement, lifecycle, relations, groups, or
world submission.  It is intentionally an endpoint composition rather than a
complete event-flow history: births or migrants that leave or die before the
horizon are not counted in the final-region terms.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
from typing import Any, Iterable

import numpy as np


SCHEMA = "event-region-endpoint-cohort-decomposition-v2"
LEGACY_SCHEMA = "event-region-endpoint-cohort-decomposition-v1"


@dataclass(frozen=True)
class EventCohortRequest:
    anchor_id: str
    region_id: int
    event_tick: int
    until_tick: int

    @classmethod
    def from_mapping(cls, payload: dict[str, Any]) -> "EventCohortRequest":
        return cls(
            anchor_id=str(payload["anchor_id"]),
            region_id=int(payload["region_id"]),
            event_tick=int(payload["event_tick"]),
            until_tick=int(payload["until_tick"]),
        )


class EventCohortDiagnostics:
    """Capture preregistered event cohorts and exact endpoint composition."""

    def __init__(
        self,
        requests: Iterable[EventCohortRequest | dict[str, Any]],
        *,
        world_width: float,
        world_height: float,
        regions_x: int,
        regions_y: int,
    ) -> None:
        normalized = [
            item if isinstance(item, EventCohortRequest) else EventCohortRequest.from_mapping(item)
            for item in requests
        ]
        ids = [item.anchor_id for item in normalized]
        if len(ids) != len(set(ids)):
            raise ValueError("event cohort requests have duplicate anchor IDs")
        if regions_x <= 0 or regions_y <= 0:
            raise ValueError("event cohort region dimensions must be positive")
        region_count = int(regions_x * regions_y)
        for item in normalized:
            if item.event_tick < 0 or item.until_tick < item.event_tick:
                raise ValueError("event cohort ticks are invalid")
            if item.region_id < 0 or item.region_id >= region_count:
                raise ValueError("event cohort region is outside the diagnostic grid")
        self.requests = tuple(normalized)
        self.world_width = float(world_width)
        self.world_height = float(world_height)
        self.regions_x = int(regions_x)
        self.regions_y = int(regions_y)
        self.feedback_to_world = False
        self._event_global_ids: dict[str, set[int]] = {}
        self._event_region_ids: dict[str, set[int]] = {}
        self._summaries: dict[str, dict[str, Any]] = {}

    def _region_ids(self, x: np.ndarray, y: np.ndarray) -> np.ndarray:
        px = np.asarray(x, dtype=np.float64)
        py = np.asarray(y, dtype=np.float64)
        rx = np.floor(px / self.world_width * self.regions_x).astype(np.int64)
        ry = np.floor(py / self.world_height * self.regions_y).astype(np.int64)
        rx = np.clip(rx, 0, self.regions_x - 1)
        ry = np.clip(ry, 0, self.regions_y - 1)
        return (ry * self.regions_x + rx).astype(np.int32, copy=False)

    @staticmethod
    def _stable_id_set(values: np.ndarray) -> set[int]:
        return {int(value) for value in np.asarray(values, dtype=np.uint64).tolist()}

    @staticmethod
    def _stable_id_sha256(values: set[int]) -> str:
        ordered = np.asarray(sorted(values), dtype="<u8")
        return hashlib.sha256(ordered.tobytes(order="C")).hexdigest()

    def observe(
        self,
        *,
        tick: int,
        alive: np.ndarray,
        stable_ids: np.ndarray,
        x: np.ndarray,
        y: np.ndarray,
    ) -> None:
        current_tick = int(tick)
        alive_mask = np.asarray(alive, dtype=bool)
        ids = np.asarray(stable_ids, dtype=np.uint64)
        px = np.asarray(x)
        py = np.asarray(y)
        if any(value.ndim != 1 for value in (alive_mask, ids, px, py)) or not (
            alive_mask.size == ids.size == px.size == py.size
        ):
            raise ValueError("event cohort arrays must be aligned and one-dimensional")
        rows = np.flatnonzero(alive_mask).astype(np.int32, copy=False)
        alive_ids = ids[rows]
        alive_regions = self._region_ids(px[rows], py[rows]) if rows.size else np.empty(0, dtype=np.int32)
        global_set = self._stable_id_set(alive_ids)

        # Capture event snapshots before finalization so zero-horizon requests are valid.
        for request in self.requests:
            if request.event_tick != current_tick or request.anchor_id in self._event_global_ids:
                continue
            region_set = self._stable_id_set(alive_ids[alive_regions == request.region_id])
            self._event_global_ids[request.anchor_id] = global_set.copy()
            self._event_region_ids[request.anchor_id] = region_set

        for request in self.requests:
            if request.until_tick != current_tick or request.anchor_id in self._summaries:
                continue
            event_global = self._event_global_ids.get(request.anchor_id)
            event_region = self._event_region_ids.get(request.anchor_id)
            if event_global is None or event_region is None:
                raise RuntimeError(
                    f"event cohort snapshot for {request.anchor_id!r} was not captured at tick "
                    f"{request.event_tick} before horizon {request.until_tick}"
                )
            final_region = self._stable_id_set(alive_ids[alive_regions == request.region_id])
            final_global = global_set
            retained = event_region & final_region
            survived_outside = (event_region & final_global) - final_region
            absent = event_region - final_global
            existing_in_migrants = (event_global - event_region) & final_region
            born_after_event = final_region - event_global
            event_alive = len(event_region)
            final_alive = len(final_region)
            endpoint_change = final_alive - event_alive
            reconstructed = (
                len(existing_in_migrants)
                + len(born_after_event)
                - len(survived_outside)
                - len(absent)
            )
            self._summaries[request.anchor_id] = {
                "event_cohort_schema": SCHEMA,
                "event_cohort_feedback_to_world": False,
                "event_cohort_anchor_id": request.anchor_id,
                "event_cohort_region_id": request.region_id,
                "event_cohort_event_tick": request.event_tick,
                "event_cohort_until_tick": request.until_tick,
                "event_alive_region": event_alive,
                "event_global_ids_sha256": self._stable_id_sha256(event_global),
                "event_region_ids_sha256": self._stable_id_sha256(event_region),
                "final_alive_region_from_cohort_audit": final_alive,
                "final_event_cohort_retained_region": len(retained),
                "final_event_cohort_survived_outside_region": len(survived_outside),
                "final_event_cohort_absent": len(absent),
                "final_existing_in_migrants_region": len(existing_in_migrants),
                "final_post_event_born_region": len(born_after_event),
                "endpoint_population_change_region": endpoint_change,
                "endpoint_population_change_reconstructed": reconstructed,
                "endpoint_population_balance_residual": endpoint_change - reconstructed,
                "event_cohort_survival_fraction": (
                    (len(retained) + len(survived_outside)) / event_alive
                    if event_alive > 0
                    else None
                ),
                "event_cohort_region_retention_fraction": (
                    len(retained) / event_alive if event_alive > 0 else None
                ),
                "interpretation_boundary": (
                    "Endpoint decomposition uses stable IDs at the nominal event tick and "
                    "publishes global/region cohort identity hashes. Post-event births and "
                    "in-migrants are counted only when alive in the region at the horizon; "
                    "it is not a complete pathwise flow ledger."
                ),
            }

    def summaries(self) -> dict[str, dict[str, Any]]:
        return {key: dict(value) for key, value in sorted(self._summaries.items())}

    def validate_complete(self) -> None:
        missing = [request.anchor_id for request in self.requests if request.anchor_id not in self._summaries]
        if missing:
            raise RuntimeError(f"event cohort diagnostics are incomplete for anchors: {missing}")
