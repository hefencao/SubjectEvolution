"""Fixed-capacity inert storage for the partitioned unified Subject Graph VM."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np

from .config import SubjectVMConfig

STORAGE_SCHEMA = "se-subject-vm-inert-storage-v1"


@dataclass(frozen=True)
class SubjectVMRegionUsage:
    region: str
    node_capacity: int
    expressed_nodes: int
    edge_capacity: int
    expressed_edges: int
    retained_state_values: int
    cross_region_edges: int


class SubjectVMStorage:
    """Host-authoritative fixed-shape storage with no execution semantics.

    Capacity is allocated only when the feature is explicitly enabled.  Node
    and edge expression gates begin false; Stage 1 never executes, charges, or
    mutates them during a simulation step.
    """

    def __init__(self, cfg: SubjectVMConfig, entity_capacity: int) -> None:
        if not cfg.enabled:
            raise ValueError("SubjectVMStorage cannot be allocated while disabled")
        self.cfg = cfg
        self.entity_capacity = int(entity_capacity)
        self.node_capacity = int(cfg.total_node_capacity)
        self.edge_capacity = int(cfg.total_edge_capacity)
        self.state_width = int(cfg.node_state_width)
        if self.entity_capacity <= 0:
            raise ValueError("subject_vm entity capacity must be positive")

        e, n, d = self.entity_capacity, self.node_capacity, self.state_width
        m = self.edge_capacity
        self.occupied = np.zeros(e, dtype=bool)
        self.owner_entity_id = np.zeros(e, dtype=np.uint64)
        self.owner_subject_id = np.zeros(e, dtype=np.uint64)

        self.node_id = np.zeros((e, n), dtype=np.uint32)
        self.node_expressed = np.zeros((e, n), dtype=bool)
        self.node_region = np.zeros((e, n), dtype=np.uint8)
        self.node_operator_id = np.zeros((e, n), dtype=np.uint16)
        self.node_state = np.zeros((e, n, d), dtype=np.float32)
        self.node_activation_period = np.zeros((e, n), dtype=np.uint16)
        self.node_activation_phase = np.zeros((e, n), dtype=np.uint16)

        self.edge_id = np.zeros((e, m), dtype=np.uint32)
        self.edge_expressed = np.zeros((e, m), dtype=bool)
        self.edge_region = np.zeros((e, m), dtype=np.uint8)
        self.edge_source = np.full((e, m), -1, dtype=np.int32)
        self.edge_target = np.full((e, m), -1, dtype=np.int32)
        self.edge_forward_gate = np.zeros((e, m), dtype=np.float32)
        self.edge_delay = np.zeros((e, m), dtype=np.uint16)
        self.edge_bandwidth = np.zeros((e, m), dtype=np.float32)
        self.edge_phase_mask = np.zeros((e, m), dtype=np.uint8)

        # Placeholder only. Stage 1 never writes eligibility or plasticity.
        self.eligibility_value = np.zeros((e, m), dtype=np.float32)
        self.eligibility_age = np.zeros((e, m), dtype=np.uint16)
        self.plasticity_flags = np.zeros((e, m), dtype=np.uint8)

        self._node_region_template = np.empty(n, dtype=np.uint8)
        self._node_period_template = np.empty(n, dtype=np.uint16)
        self._edge_region_template = np.empty(m, dtype=np.uint8)
        node_cursor = 0
        edge_cursor = 0
        for region_index, region in enumerate(cfg.regions):
            next_node = node_cursor + int(region.node_capacity)
            self._node_region_template[node_cursor:next_node] = region_index
            self._node_period_template[node_cursor:next_node] = int(
                region.update_period
            )
            node_cursor = next_node
            next_edge = edge_cursor + int(region.edge_capacity)
            self._edge_region_template[edge_cursor:next_edge] = region_index
            edge_cursor = next_edge
        self._node_id_template = np.arange(1, n + 1, dtype=np.uint32)
        self._edge_id_template = np.arange(1, m + 1, dtype=np.uint32)

    def _rows(self, rows: np.ndarray | list[int] | tuple[int, ...]) -> np.ndarray:
        normalized = np.asarray(rows, dtype=np.int32)
        if normalized.ndim != 1:
            raise ValueError("subject_vm rows must be one-dimensional")
        if normalized.size and (
            np.any(normalized < 0)
            or np.any(normalized >= self.entity_capacity)
            or np.unique(normalized).size != normalized.size
        ):
            raise ValueError("subject_vm rows must be unique in-capacity indices")
        return normalized

    def initialize_rows(
        self,
        rows: np.ndarray,
        entity_ids: np.ndarray,
        subject_ids: np.ndarray,
    ) -> None:
        rows = self._rows(rows)
        entity_ids = np.asarray(entity_ids, dtype=np.uint64)
        subject_ids = np.asarray(subject_ids, dtype=np.uint64)
        if entity_ids.shape != rows.shape or subject_ids.shape != rows.shape:
            raise ValueError("subject_vm owner arrays must match row shape")
        if rows.size == 0:
            return
        if np.any(entity_ids == 0) or np.any(subject_ids == 0):
            raise ValueError("subject_vm owners require positive stable IDs")
        self.clear_rows(rows)
        self.occupied[rows] = True
        self.owner_entity_id[rows] = entity_ids
        self.owner_subject_id[rows] = subject_ids
        self.node_id[rows] = self._node_id_template
        self.node_region[rows] = self._node_region_template
        self.node_activation_period[rows] = self._node_period_template
        if self.edge_capacity:
            self.edge_id[rows] = self._edge_id_template
            self.edge_region[rows] = self._edge_region_template

    def clear_rows(self, rows: np.ndarray) -> None:
        rows = self._rows(rows)
        if rows.size == 0:
            return
        self.occupied[rows] = False
        self.owner_entity_id[rows] = 0
        self.owner_subject_id[rows] = 0
        self.node_id[rows] = 0
        self.node_expressed[rows] = False
        self.node_region[rows] = 0
        self.node_operator_id[rows] = 0
        self.node_state[rows] = 0.0
        self.node_activation_period[rows] = 0
        self.node_activation_phase[rows] = 0
        if self.edge_capacity:
            self.edge_id[rows] = 0
            self.edge_expressed[rows] = False
            self.edge_region[rows] = 0
            self.edge_source[rows] = -1
            self.edge_target[rows] = -1
            self.edge_forward_gate[rows] = 0.0
            self.edge_delay[rows] = 0
            self.edge_bandwidth[rows] = 0.0
            self.edge_phase_mask[rows] = 0
            self.eligibility_value[rows] = 0.0
            self.eligibility_age[rows] = 0
            self.plasticity_flags[rows] = 0

    def inherit_structure(
        self,
        parent_rows: np.ndarray,
        child_rows: np.ndarray,
        child_entity_ids: np.ndarray,
        child_subject_ids: np.ndarray,
    ) -> None:
        parents = self._rows(parent_rows)
        children = self._rows(child_rows)
        if parents.shape != children.shape:
            raise ValueError("subject_vm parent and child rows must match")
        if parents.size == 0:
            return
        if np.any(~self.occupied[parents]):
            raise ValueError("subject_vm cannot inherit from an unoccupied parent")
        self.initialize_rows(children, child_entity_ids, child_subject_ids)
        # Structural inheritance only. Dynamic state and eligibility reset.
        for name in (
            "node_expressed",
            "node_region",
            "node_operator_id",
            "node_activation_period",
            "node_activation_phase",
            "edge_expressed",
            "edge_region",
            "edge_source",
            "edge_target",
            "edge_forward_gate",
            "edge_delay",
            "edge_bandwidth",
            "edge_phase_mask",
            "plasticity_flags",
        ):
            getattr(self, name)[children] = getattr(self, name)[parents]

    def move_rows(self, source_rows: np.ndarray, destination_rows: np.ndarray) -> None:
        """Compaction hook preserving complete row state and stable owners."""
        sources = self._rows(source_rows)
        destinations = self._rows(destination_rows)
        if sources.shape != destinations.shape:
            raise ValueError("subject_vm compaction row arrays must match")
        if sources.size == 0:
            return
        if np.intersect1d(sources, destinations).size:
            raise ValueError("subject_vm compaction source/destination rows must differ")
        if np.any(~self.occupied[sources]) or np.any(self.occupied[destinations]):
            raise ValueError("subject_vm compaction requires occupied sources and empty destinations")
        array_names = self.snapshot_array_names()
        for name in array_names:
            array = getattr(self, name)
            array[destinations] = array[sources]
        self.clear_rows(sources)

    @staticmethod
    def snapshot_array_names() -> tuple[str, ...]:
        return (
            "occupied",
            "owner_entity_id",
            "owner_subject_id",
            "node_id",
            "node_expressed",
            "node_region",
            "node_operator_id",
            "node_state",
            "node_activation_period",
            "node_activation_phase",
            "edge_id",
            "edge_expressed",
            "edge_region",
            "edge_source",
            "edge_target",
            "edge_forward_gate",
            "edge_delay",
            "edge_bandwidth",
            "edge_phase_mask",
            "eligibility_value",
            "eligibility_age",
            "plasticity_flags",
        )

    def snapshot_state(self) -> dict[str, Any]:
        return {
            "schema": STORAGE_SCHEMA,
            "entity_capacity": self.entity_capacity,
            "node_capacity": self.node_capacity,
            "edge_capacity": self.edge_capacity,
            "state_width": self.state_width,
            "arrays": {
                name: getattr(self, name).copy()
                for name in self.snapshot_array_names()
            },
        }

    @classmethod
    def from_snapshot(
        cls,
        cfg: SubjectVMConfig,
        entity_capacity: int,
        payload: dict[str, Any],
    ) -> "SubjectVMStorage":
        if payload.get("schema") != STORAGE_SCHEMA:
            raise ValueError("unsupported subject_vm storage snapshot schema")
        result = cls(cfg, entity_capacity)
        expected = (
            result.entity_capacity,
            result.node_capacity,
            result.edge_capacity,
            result.state_width,
        )
        actual = (
            int(payload.get("entity_capacity", -1)),
            int(payload.get("node_capacity", -1)),
            int(payload.get("edge_capacity", -1)),
            int(payload.get("state_width", -1)),
        )
        if actual != expected:
            raise ValueError("subject_vm checkpoint capacity does not match configuration")
        arrays = payload.get("arrays")
        if not isinstance(arrays, dict):
            raise ValueError("subject_vm checkpoint arrays are missing")
        for name in result.snapshot_array_names():
            if name not in arrays:
                raise ValueError(f"subject_vm checkpoint is missing array {name}")
            expected_array = getattr(result, name)
            restored = np.asarray(arrays[name], dtype=expected_array.dtype)
            if restored.shape != expected_array.shape:
                raise ValueError(f"subject_vm checkpoint shape mismatch for {name}")
            setattr(result, name, restored.copy())
        result.validate_internal()
        return result

    def validate_internal(self) -> None:
        occupied = self.occupied
        if np.any(self.owner_entity_id[occupied] == 0) or np.any(
            self.owner_subject_id[occupied] == 0
        ):
            raise ValueError("occupied subject_vm rows require stable owners")
        if np.any(self.owner_entity_id[~occupied] != 0) or np.any(
            self.owner_subject_id[~occupied] != 0
        ):
            raise ValueError("empty subject_vm rows cannot retain owners")
        if self.node_capacity:
            valid_regions = self.node_region[occupied] < len(self.cfg.regions)
            if not np.all(valid_regions):
                raise ValueError("subject_vm node region is outside configured partitions")
        expressed_edges = self.edge_expressed
        if np.any(expressed_edges):
            source = self.edge_source[expressed_edges]
            target = self.edge_target[expressed_edges]
            if np.any(source < 0) or np.any(source >= self.node_capacity):
                raise ValueError("expressed subject_vm edge source is invalid")
            if np.any(target < 0) or np.any(target >= self.node_capacity):
                raise ValueError("expressed subject_vm edge target is invalid")
        if np.any(self.eligibility_value) or np.any(self.eligibility_age):
            raise ValueError("Stage-1 subject_vm cannot contain active eligibility traces")

    def validate_owners(
        self,
        alive: np.ndarray,
        entity_ids: np.ndarray,
        subject_ids: np.ndarray,
    ) -> None:
        alive = np.asarray(alive, dtype=bool)
        entity_ids = np.asarray(entity_ids, dtype=np.uint64)
        subject_ids = np.asarray(subject_ids, dtype=np.uint64)
        if alive.shape != (self.entity_capacity,):
            raise ValueError("subject_vm owner validation capacity mismatch")
        if not np.array_equal(self.occupied, alive):
            raise ValueError("subject_vm occupancy must match entity occupancy")
        rows = np.flatnonzero(alive)
        if not np.array_equal(self.owner_entity_id[rows], entity_ids[rows]):
            raise ValueError("subject_vm entity ownership is stale")
        if not np.array_equal(self.owner_subject_id[rows], subject_ids[rows]):
            raise ValueError("subject_vm subject ownership is stale")
        self.validate_internal()

    def region_usage(self) -> tuple[SubjectVMRegionUsage, ...]:
        usage: list[SubjectVMRegionUsage] = []
        for region_index, region in enumerate(self.cfg.regions):
            node_mask = self.occupied[:, None] & (self.node_region == region_index)
            edge_mask = self.occupied[:, None] & (self.edge_region == region_index)
            expressed_nodes = node_mask & self.node_expressed
            expressed_edges = edge_mask & self.edge_expressed
            retained = int(np.count_nonzero(self.node_state[expressed_nodes]))
            cross = 0
            rows, edges = np.nonzero(expressed_edges)
            if rows.size:
                sources = self.edge_source[rows, edges]
                targets = self.edge_target[rows, edges]
                cross = int(
                    np.count_nonzero(
                        self.node_region[rows, sources]
                        != self.node_region[rows, targets]
                    )
                )
            occupied_count = int(self.occupied.sum())
            usage.append(
                SubjectVMRegionUsage(
                    region=region.name,
                    node_capacity=occupied_count * int(region.node_capacity),
                    expressed_nodes=int(expressed_nodes.sum()),
                    edge_capacity=occupied_count * int(region.edge_capacity),
                    expressed_edges=int(expressed_edges.sum()),
                    retained_state_values=retained,
                    cross_region_edges=cross,
                )
            )
        return tuple(usage)

    def clone(self) -> "SubjectVMStorage":
        return type(self).from_snapshot(
            self.cfg, self.entity_capacity, self.snapshot_state()
        )


__all__ = [
    "STORAGE_SCHEMA",
    "SubjectVMRegionUsage",
    "SubjectVMStorage",
]
