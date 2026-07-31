"""Hybrid GPU execution for the hot observation and policy stages.

The CPU simulation remains the authority for delayed-message ownership,
action resolution, relationship changes, births/deaths, and the subject graph.
This module owns a coherent device mirror for fields and runs the expensive
regular-grid observation and shared-policy batch there.  Transfers back to
the CPU are explicit and limited to the policy result plus data required by
the existing commit semantics.
"""

from __future__ import annotations

from dataclasses import dataclass
import time
from typing import Any

import numpy as np

from .backend import Backend, resolve_backend
from .gpu_memory import GpuMemoryPoolController
from .cfg import SimulationConfig
from .device_state import EntityDeviceCommitPlan
from se.env.danger_evidence import DANGER_EVIDENCE_SCALE, danger_evidence_enabled, danger_evidence_quantized
from .execution import ActionResolutionSnapshot, HarvestResolution
from se.env.gpu import DeviceEnvironment, DeviceInformationField
from .information import InformationObservation, InformationSystem, SignalEmissionPlan
from se.knowledge import KnowledgeSystem, encode_local_context
from se.knowledge.policy import (
    KnowledgePolicyPlan,
    build_knowledge_policy_plan,
    build_latent_knowledge_policy_plan,
)
from se.knowledge.latent import latent_router_state_features
from se.env.niches import (
    constrain_harvest_request_rates,
    AFFINITY_SCALE,
    RESOURCE_CHANNELS,
    harvest_request_rates,
    policy_resource_view,
    resource_affinity_quantized,
    selective_harvest_enabled,
)
from se.runtime.resource_metabolism import storage_room_fraction
from se.knowledge.routing_cost import RoutingCostBudgetResult, apply_routing_cost_budget
from .intents import ActionIntentBatch
from .policy import Action, ParametricPolicy, PolicyDecision
from .random_api import RandomContext, Stream, uniform01
from .reductions import stable_segmented_sum
from se.env.spatial import SpatialIndex


@dataclass(frozen=True)
class GpuPreparedStep:
    """Host-side inputs required by the existing CPU intent/commit phases."""

    active: np.ndarray
    cells: np.ndarray
    local_resources: np.ndarray
    resource_gradient: tuple[np.ndarray, np.ndarray] | None
    information: InformationObservation | None
    decision: PolicyDecision
    spatial_seconds: float
    observation_seconds: float
    policy_seconds: float
    knowledge_context_keys: np.ndarray
    knowledge_policy_plan: KnowledgePolicyPlan
    working_memory_state_features: np.ndarray | None
    routing_cost_result: RoutingCostBudgetResult | None
    signal_detection_rate: float
    partner_detection_rate: float


@dataclass(frozen=True)
class GpuTransferStats:
    """Explicit host/device traffic recorded during one world step."""

    host_to_device_bytes: int = 0
    device_to_host_bytes: int = 0
    direct_message_events: int = 0
    direct_message_dense_bytes_avoided: int = 0
    entity_commit_bytes: int = 0
    device_preprocess_rows: int = 0
    device_resident_host_bytes_avoided: int = 0
    device_latent_root_rows: int = 0
    memory_used_bytes: int = 0
    memory_pool_total_bytes: int = 0
    memory_pool_cached_bytes: int = 0
    memory_pool_total_bytes_after_trim: int = 0
    memory_pool_cached_bytes_after_trim: int = 0
    memory_pool_peak_used_bytes: int = 0
    memory_pool_peak_total_bytes: int = 0
    memory_pool_trim_count: int = 0
    memory_pool_trimmed_step: bool = False
    memory_pool_released_bytes_step: int = 0
    pinned_memory_pool_free_blocks: int = 0

    def record_into(self, stats: Any) -> None:
        """Publish this transfer snapshot into one backend-neutral step record."""

        stats.gpu_h2d_bytes = self.host_to_device_bytes
        stats.gpu_d2h_bytes = self.device_to_host_bytes
        stats.gpu_direct_message_events = self.direct_message_events
        stats.gpu_direct_dense_bytes_avoided = self.direct_message_dense_bytes_avoided
        stats.gpu_entity_commit_bytes = self.entity_commit_bytes
        stats.gpu_device_preprocess_rows = self.device_preprocess_rows
        stats.gpu_device_resident_host_bytes_avoided = (
            self.device_resident_host_bytes_avoided
        )
        stats.gpu_device_latent_root_rows = self.device_latent_root_rows
        stats.gpu_memory_used_bytes = self.memory_used_bytes
        stats.gpu_memory_pool_total_bytes = self.memory_pool_total_bytes
        stats.gpu_memory_pool_cached_bytes = self.memory_pool_cached_bytes
        stats.gpu_memory_pool_total_bytes_after_trim = (
            self.memory_pool_total_bytes_after_trim
        )
        stats.gpu_memory_pool_cached_bytes_after_trim = (
            self.memory_pool_cached_bytes_after_trim
        )
        stats.gpu_memory_pool_peak_used_bytes = self.memory_pool_peak_used_bytes
        stats.gpu_memory_pool_peak_total_bytes = self.memory_pool_peak_total_bytes
        stats.gpu_memory_pool_trim_count = self.memory_pool_trim_count
        stats.gpu_memory_pool_trimmed_step = int(self.memory_pool_trimmed_step)
        stats.gpu_memory_pool_released_bytes_step = (
            self.memory_pool_released_bytes_step
        )
        stats.gpu_pinned_memory_pool_free_blocks = (
            self.pinned_memory_pool_free_blocks
        )


@dataclass
class DeviceEntityState:
    """Persistent device inputs for spatial, observation, and policy stages."""

    x: Any
    y: Any
    alive: Any
    stable_ids: Any
    energy: Any
    integrity: Any
    fertility: Any
    genotype: Any
    memory: Any
    sensor_quality: Any
    group_ids: Any
    group_dir_x: Any
    group_dir_y: Any
    version: int


def device_resource_affinity_quantized(
    genotype: Any,
    cfg: SimulationConfig,
    *,
    xp: Any,
) -> Any:
    """Compute the fixed-budget affinity vector on the owning array backend."""
    values = xp.asarray(genotype, dtype=xp.float32)
    if values.ndim != 2 or values.shape[1] < 5:
        raise ValueError("genotype does not contain the four resource-affinity traits")
    rows = int(values.shape[0])
    if cfg.entities.resource_affinity_schema != "normalized-four-resource-affinity-v1":
        return xp.full((rows, RESOURCE_CHANNELS), AFFINITY_SCALE, dtype=xp.int32)
    traits = xp.clip(values[:, 1:5], -1.0, 1.0).astype(xp.float64)
    raw = xp.rint(
        AFFINITY_SCALE
        * (1.0 + float(cfg.entities.resource_affinity_strength) * traits)
    ).astype(xp.int64)
    minimum = int(
        round(AFFINITY_SCALE * cfg.entities.resource_affinity_min_efficiency)
    )
    maximum = int(
        round(AFFINITY_SCALE * cfg.entities.resource_affinity_max_efficiency)
    )
    raw = xp.clip(raw, minimum, maximum)
    denominator = raw.sum(axis=1, dtype=xp.int64)
    numerator = raw * (RESOURCE_CHANNELS * AFFINITY_SCALE)
    affinity = (
        (numerator + denominator[:, None] // 2) // denominator[:, None]
    ).astype(xp.int64)
    residual = RESOURCE_CHANNELS * AFFINITY_SCALE - affinity.sum(axis=1)
    strongest = xp.argmax(raw, axis=1)
    affinity[xp.arange(rows), strongest] += residual
    if bool(xp.any(affinity <= 0)):
        raise RuntimeError(
            "resource affinity normalization produced a non-positive channel"
        )
    return affinity.astype(xp.int32)


def device_danger_evidence_quantized(
    genotype: Any,
    cfg: SimulationConfig,
    *,
    xp: Any,
) -> Any:
    """Compute fixed-budget direct/trace evidence weights on the device."""
    values = xp.asarray(genotype, dtype=xp.float32)
    if values.ndim != 2 or values.shape[1] <= 6:
        raise ValueError("genotype does not contain the danger-evidence trait")
    rows = int(values.shape[0])
    if not danger_evidence_enabled(cfg):
        return xp.full((rows, 2), DANGER_EVIDENCE_SCALE, dtype=xp.int32)
    trait = xp.clip(values[:, 6], -1.0, 1.0).astype(xp.float64)
    direct = xp.rint(
        DANGER_EVIDENCE_SCALE
        * (1.0 + float(cfg.entities.danger_evidence_strength) * trait)
    ).astype(xp.int64)
    minimum = int(
        round(
            DANGER_EVIDENCE_SCALE
            * float(cfg.entities.danger_evidence_min_efficiency)
        )
    )
    maximum = int(
        round(
            DANGER_EVIDENCE_SCALE
            * float(cfg.entities.danger_evidence_max_efficiency)
        )
    )
    direct = xp.clip(direct, minimum, maximum)
    trace = 2 * DANGER_EVIDENCE_SCALE - direct
    if bool(xp.any(trace <= 0)):
        raise RuntimeError(
            "danger evidence normalization produced a non-positive weight"
        )
    return xp.stack((direct, trace), axis=1).astype(xp.int32)


def device_resource_sensing_radius(
    genotype: Any,
    cfg: SimulationConfig,
    *,
    xp: Any,
) -> Any:
    """Map morphology gene 7 to inherited reach capacity."""

    values = xp.asarray(genotype, dtype=xp.float32)
    if values.ndim != 2 or values.shape[1] <= 7:
        raise ValueError("genotype does not contain the resource-sensing trait")
    if cfg.entities.resource_sensing_schema == "disabled":
        return xp.ones(int(values.shape[0]), dtype=xp.int16)
    levels = xp.asarray(cfg.entities.resource_sensing_radius_levels, dtype=xp.int16)
    trait = xp.clip(values[:, 7], -1.0, 1.0).astype(xp.float64)
    scaled = xp.float64(0.5) * (trait + xp.float64(1.0)) * int(levels.size)
    indices = xp.minimum(xp.floor(scaled).astype(xp.int64), int(levels.size) - 1)
    return levels[indices].astype(xp.int16)


def device_resource_sensing_channel_radii(
    genotype: Any,
    cfg: SimulationConfig,
    *,
    resource_affinity_q: Any,
    xp: Any,
) -> Any:
    """Return device-side per-channel radii for the configured sensing schema."""

    base = device_resource_sensing_radius(genotype, cfg, xp=xp)
    rows = int(base.shape[0])
    if cfg.entities.resource_sensing_schema not in {
        "inherited-affinity-routed-gradient-radius-v2",
        "inherited-affinity-budgeted-gradient-radius-v3",
    }:
        return xp.repeat(base[:, None], RESOURCE_CHANNELS, axis=1)
    affinity = xp.asarray(resource_affinity_q, dtype=xp.int32)
    if affinity.shape != (rows, RESOURCE_CHANNELS):
        raise ValueError("resource affinity must be shaped [N, 4]")
    if cfg.entities.resource_sensing_schema == "inherited-affinity-routed-gradient-radius-v2":
        preferred = xp.argmax(affinity, axis=1)
        result = xp.ones((rows, RESOURCE_CHANNELS), dtype=xp.int16)
        result[xp.arange(rows), preferred] = base
        return result

    weights = affinity.astype(xp.int64)
    totals = xp.sum(weights, axis=1, dtype=xp.int64)
    if bool(xp.any(totals <= 0)) or bool(xp.any(weights < 0)):
        raise ValueError("resource affinity must contain a positive non-negative budget")
    budget = xp.maximum(base.astype(xp.int64) - 1, 0)
    numerator = weights * budget[:, None]
    allocation = numerator // totals[:, None]
    remainder = numerator % totals[:, None]
    missing = budget - xp.sum(allocation, axis=1, dtype=xp.int64)
    rows_index = xp.arange(rows)
    for _ in range(RESOURCE_CHANNELS - 1):
        selected = xp.argmax(remainder, axis=1)
        active = missing > 0
        if not bool(xp.any(active)):
            break
        active_rows = rows_index[active]
        active_selected = selected[active]
        allocation[active_rows, active_selected] += 1
        remainder[active_rows, active_selected] = -1
        missing = missing - active.astype(xp.int64)
    if bool(xp.any(missing != 0)):
        raise RuntimeError("resource-sensing radius budget apportionment did not close")
    return (allocation + 1).astype(xp.int16)


def device_policy_resource_view(
    local_resources: Any,
    cfg: SimulationConfig,
    *,
    resource_affinity_q: Any,
    storage_room_fraction: Any | None,
    xp: Any,
) -> Any:
    """Construct the scalar policy resource coordinate without a host bounce."""
    local = xp.asarray(local_resources, dtype=xp.float32)
    if local.ndim != 2 or local.shape[1] != RESOURCE_CHANNELS:
        raise ValueError("local resources must be shaped [N, 4]")
    if cfg.environment.schema == "legacy-four-channel-v1":
        return local
    affinity = xp.asarray(resource_affinity_q, dtype=xp.int32).astype(xp.float64)
    if affinity.shape != (local.shape[0], RESOURCE_CHANNELS):
        raise ValueError("resource affinity must be shaped [N, 4]")
    capacities = xp.asarray(
        cfg.environment.resource_capacity, dtype=xp.float64
    )
    fractions = xp.clip(
        local.astype(xp.float64) / capacities[None, :], 0.0, 1.5
    )
    if storage_room_fraction is not None:
        room = xp.asarray(storage_room_fraction, dtype=xp.float32).astype(xp.float64)
        if room.shape != fractions.shape:
            raise ValueError("storage room fraction must be shaped [N, 4]")
        if bool(xp.any(~xp.isfinite(room))) or bool(xp.any(room < 0.0)):
            raise ValueError(
                "storage room fraction must be finite and non-negative"
            )
        fractions = fractions * xp.clip(room, 0.0, 1.0)
    utility = xp.sum(fractions * affinity, axis=1) / (
        RESOURCE_CHANNELS * AFFINITY_SCALE
    )
    result = local.copy()
    result[:, 0] = (
        utility * float(cfg.environment.resource_capacity[0])
    ).astype(xp.float32)
    return result


class HybridGpuRuntime:
    """Run fields, observations and policy batches on a selected GPU backend."""

    def __init__(self, cfg: SimulationConfig, backend: Backend | str = "gpu") -> None:
        self.cfg = cfg
        self.backend = resolve_backend(backend) if isinstance(backend, str) else backend
        if not self.backend.is_gpu:
            raise ValueError("HybridGpuRuntime requires a usable GPU backend")
        self.environment = DeviceEnvironment(cfg, backend=self.backend)
        self.information_field = DeviceInformationField(cfg, backend=self.backend)
        self.spatial = SpatialIndex(
            cfg.world.grid_x,
            cfg.world.grid_y,
            cfg.world.width,
            cfg.world.height,
            cfg.world.periodic,
            backend=self.backend,
        )
        self.entity_state: DeviceEntityState | None = None
        self._entity_static_dirty = True
        self._social_state_dirty = True
        self._measure_transfers = False
        self._host_to_device_bytes = 0
        self._device_to_host_bytes = 0
        self._direct_message_events = 0
        self._direct_message_dense_bytes_avoided = 0
        self._entity_commit_bytes = 0
        self._device_preprocess_rows = 0
        self._device_resident_host_bytes_avoided = 0
        self._device_latent_root_rows = 0
        self.memory_pool = GpuMemoryPoolController(
            self.backend.xp,
            policy=cfg.run.gpu_memory_pool_policy,
            cache_limit_bytes=cfg.run.gpu_memory_pool_cache_limit_bytes,
            trim_period=cfg.run.gpu_memory_pool_trim_period,
        )

    def begin_step_transfer_measurement(self) -> None:
        self.memory_pool.begin_step()
        self._measure_transfers = True
        self._host_to_device_bytes = 0
        self._device_to_host_bytes = 0
        self._direct_message_events = 0
        self._direct_message_dense_bytes_avoided = 0
        self._entity_commit_bytes = 0
        self._device_preprocess_rows = 0
        self._device_resident_host_bytes_avoided = 0
        self._device_latent_root_rows = 0

    def finish_step_transfer_measurement(self) -> GpuTransferStats:
        memory = self.memory_pool.finish_step()
        result = GpuTransferStats(
            host_to_device_bytes=self._host_to_device_bytes,
            device_to_host_bytes=self._device_to_host_bytes,
            direct_message_events=self._direct_message_events,
            direct_message_dense_bytes_avoided=self._direct_message_dense_bytes_avoided,
            entity_commit_bytes=self._entity_commit_bytes,
            device_preprocess_rows=self._device_preprocess_rows,
            device_resident_host_bytes_avoided=(
                self._device_resident_host_bytes_avoided
            ),
            device_latent_root_rows=self._device_latent_root_rows,
            memory_used_bytes=memory.used_bytes,
            memory_pool_total_bytes=memory.total_bytes,
            memory_pool_cached_bytes=memory.cached_bytes,
            memory_pool_total_bytes_after_trim=memory.total_bytes_after_trim,
            memory_pool_cached_bytes_after_trim=memory.cached_bytes_after_trim,
            memory_pool_peak_used_bytes=memory.peak_used_bytes,
            memory_pool_peak_total_bytes=memory.peak_total_bytes,
            memory_pool_trim_count=memory.trim_count,
            memory_pool_trimmed_step=memory.trimmed_step,
            memory_pool_released_bytes_step=memory.released_bytes_step,
            pinned_memory_pool_free_blocks=memory.pinned_free_blocks,
        )
        self._measure_transfers = False
        return result

    def _upload(self, value: Any, *, dtype: Any | None = None, copy: bool = False) -> Any:
        result = self.backend.asarray(value, dtype=dtype, copy=copy)
        if self._measure_transfers:
            self._host_to_device_bytes += int(result.nbytes)
        return result

    def _download(self, value: Any) -> np.ndarray:
        if self._measure_transfers:
            self._device_to_host_bytes += int(value.nbytes)
        return self.backend.to_numpy(value)

    def _copy_into(self, destination: Any, value: np.ndarray) -> None:
        """Copy one contiguous host value into an existing device buffer."""
        if self._measure_transfers:
            self._host_to_device_bytes += int(value.nbytes)
        destination.set(value)

    def mark_entity_static_dirty(self) -> None:
        """Require a full entity mirror refresh at the next prepare boundary.

        Routine action and lifecycle commits use :meth:`apply_entity_commit`.
        This fallback is reserved for external state mutation or interventions
        that did not pass through the normal versioned commit protocol.
        """
        self._entity_static_dirty = True

    def mark_social_state_dirty(self) -> None:
        """Require all group observation fields to be refreshed next tick."""
        self._social_state_dirty = True

    def ensure_latent_catalog(self, store: Any, catalog: Any) -> None:
        """Materialize independent latent roots with exact device integer hashes."""

        stats = store.ensure_catalog(catalog, backend=self.backend)
        if self._measure_transfers:
            self._host_to_device_bytes += int(stats.host_to_device_bytes)
            self._device_to_host_bytes += int(stats.device_to_host_bytes)
            self._device_latent_root_rows += int(stats.root_rows)

    def sync_entity_from_host(
        self,
        entity: Any,
        social: Any,
        version: int,
    ) -> None:
        """Seed or explicitly repair the complete persistent entity mirror."""
        xp = self.backend.xp
        self.entity_state = DeviceEntityState(
            x=self._upload(entity.x, dtype=xp.float32, copy=True),
            y=self._upload(entity.y, dtype=xp.float32, copy=True),
            alive=self._upload(entity.alive, dtype=bool, copy=True),
            stable_ids=self._upload(entity.entity_id, dtype=xp.uint64, copy=True),
            energy=self._upload(entity.energy, dtype=xp.float32, copy=True),
            integrity=self._upload(entity.integrity, dtype=xp.float32, copy=True),
            fertility=self._upload(entity.fertility, dtype=xp.float32, copy=True),
            genotype=self._upload(entity.genotype, dtype=xp.float32, copy=True),
            memory=self._upload(entity.memory, dtype=xp.float32, copy=True),
            sensor_quality=self._upload(
                entity.sensor_quality(), dtype=xp.float32, copy=True
            ),
            group_ids=self._upload(social.group_id, dtype=xp.uint64, copy=True),
            group_dir_x=self._upload(social.group_dir_x, dtype=xp.float32, copy=True),
            group_dir_y=self._upload(social.group_dir_y, dtype=xp.float32, copy=True),
            version=int(version),
        )
        self._entity_static_dirty = False
        self._social_state_dirty = False

    def _sync_social_from_host(self, social: Any) -> None:
        if self.entity_state is None:
            raise RuntimeError("entity device state has not been initialized")
        xp = self.backend.xp
        self.entity_state.group_ids = self._upload(
            social.group_id, dtype=xp.uint64, copy=True
        )
        self.entity_state.group_dir_x = self._upload(
            social.group_dir_x, dtype=xp.float32, copy=True
        )
        self.entity_state.group_dir_y = self._upload(
            social.group_dir_y, dtype=xp.float32, copy=True
        )
        self._social_state_dirty = False

    def apply_entity_commit(self, plan: EntityDeviceCommitPlan) -> None:
        """Apply one validated CPU final-state plan to the persistent mirror."""
        state = self.entity_state
        if state is None:
            raise RuntimeError("entity device state has not been initialized")
        plan.validate(int(state.alive.size), int(state.genotype.shape[1]))
        if int(plan.base_version) != state.version:
            raise ValueError(
                "entity device commit is stale: "
                f"mirror={state.version}, plan={plan.base_version}"
            )
        if self._measure_transfers:
            self._entity_commit_bytes += plan.semantic_transfer_nbytes
        xp = self.backend.xp
        if plan.dynamic_full:
            self._copy_into(state.energy, plan.dynamic_energy)
            self._copy_into(state.integrity, plan.dynamic_integrity)
            self._copy_into(state.fertility, plan.dynamic_fertility)
            self._copy_into(state.memory, plan.dynamic_memory)
            self._copy_into(state.sensor_quality, plan.dynamic_sensor_quality)
        elif plan.dynamic_indices.size:
            indices = self._upload(plan.dynamic_indices, dtype=xp.int32)
            state.energy[indices] = self._upload(plan.dynamic_energy, dtype=xp.float32)
            state.integrity[indices] = self._upload(
                plan.dynamic_integrity, dtype=xp.float32
            )
            state.fertility[indices] = self._upload(
                plan.dynamic_fertility, dtype=xp.float32
            )
            state.memory[indices] = self._upload(plan.dynamic_memory, dtype=xp.float32)
            state.sensor_quality[indices] = self._upload(
                plan.dynamic_sensor_quality, dtype=xp.float32
            )
        if plan.position_full:
            self._copy_into(state.x, plan.position_x)
            self._copy_into(state.y, plan.position_y)
        elif plan.position_indices.size:
            indices = self._upload(plan.position_indices, dtype=xp.int32)
            state.x[indices] = self._upload(plan.position_x, dtype=xp.float32)
            state.y[indices] = self._upload(plan.position_y, dtype=xp.float32)
        if plan.lifecycle_indices.size:
            indices = self._upload(plan.lifecycle_indices, dtype=xp.int32)
            state.alive[indices] = self._upload(plan.lifecycle_alive, dtype=bool)
            state.stable_ids[indices] = self._upload(
                plan.lifecycle_entity_ids, dtype=xp.uint64
            )
            state.genotype[indices] = self._upload(
                plan.lifecycle_genotype, dtype=xp.float32
            )
        if plan.social_full:
            self._copy_into(state.group_ids, plan.social_group_ids)
            self._copy_into(state.group_dir_x, plan.social_direction_x)
            self._copy_into(state.group_dir_y, plan.social_direction_y)
        elif plan.social_indices.size:
            indices = self._upload(plan.social_indices, dtype=xp.int32)
            state.group_ids[indices] = self._upload(
                plan.social_group_ids, dtype=xp.uint64
            )
            state.group_dir_x[indices] = self._upload(
                plan.social_direction_x, dtype=xp.float32
            )
            state.group_dir_y[indices] = self._upload(
                plan.social_direction_y, dtype=xp.float32
            )
        state.version = int(plan.next_version)

    def sync_from_host(self, environment: Any, information: InformationSystem) -> None:
        """Seed the device mirror from an existing CPU world snapshot."""
        xp = self.backend.xp
        self.environment.spatial_reversed = bool(environment.spatial_reversed)
        self.environment.resource_spatial_reversed = bool(
            getattr(environment, "resource_spatial_reversed", environment.spatial_reversed)
        )
        self.environment.resources = self._upload(environment.resources, dtype=xp.float32, copy=True)
        self.environment.capacity = self._upload(environment.capacity, dtype=xp.float32, copy=True)
        self.environment.regeneration = self._upload(environment.regeneration, dtype=xp.float32, copy=True)
        self.environment.hazard = self._upload(environment.hazard, dtype=xp.float32, copy=True)
        self.environment.oxygen = self._upload(
            environment.oxygen, dtype=xp.float32, copy=True
        )
        self.environment.terrain = self._upload(
            environment.terrain, dtype=xp.float32, copy=True
        )
        self.environment.wear = self._upload(
            environment.wear, dtype=xp.float32, copy=True
        )
        self.environment.mortality_trace = self._upload(
            environment.mortality_trace, dtype=xp.float32, copy=True
        )
        if hasattr(environment, "resource_residue"):
            self.environment.resource_residue = self._upload(
                environment.resource_residue, dtype=xp.float32, copy=True
            )
            for name in (
                "resource_residue_field_roundoff_step",
                "total_resource_residue_field_roundoff",
                "resource_residue_deposit_roundoff_step",
                "total_resource_residue_deposit_roundoff",
            ):
                setattr(
                    self.environment,
                    name,
                    np.asarray(getattr(environment, name, np.zeros(4)), dtype=np.float64).copy(),
                )
        if hasattr(environment, "total_resource_renewal_source"):
            for name in (
                "initial_resource_total",
                "resource_renewal_source_step",
                "resource_renewal_sink_step",
                "total_resource_renewal_source",
                "total_resource_renewal_sink",
                "resource_field_roundoff_step",
                "total_resource_field_roundoff",
                "resource_harvest_roundoff_step",
                "total_resource_harvest_roundoff",
            ):
                setattr(
                    self.environment,
                    name,
                    np.asarray(getattr(environment, name), dtype=np.float64).copy(),
                )
        self.information_field.field = self._upload(information.field, dtype=xp.float32, copy=True)
        self.information_field.source = self._upload(information.source, dtype=xp.float32, copy=True)
        self.information_field.age = self._upload(information.age, dtype=xp.uint16, copy=True)

    def sync_to_host(self, environment: Any, information: InformationSystem) -> None:
        """Expose the current device fields to CPU-only inspection and cloning."""
        environment.spatial_reversed = self.environment.spatial_reversed
        environment.resource_spatial_reversed = (
            self.environment.resource_spatial_reversed
        )
        environment.resources = self._download(self.environment.resources).astype(np.float32, copy=False)
        environment.capacity = self._download(self.environment.capacity).astype(np.float32, copy=False)
        environment.regeneration = self._download(self.environment.regeneration).astype(np.float32, copy=False)
        environment.hazard = self._download(self.environment.hazard).astype(np.float32, copy=False)
        environment.oxygen = self._download(self.environment.oxygen).astype(
            np.float32, copy=False
        )
        environment.terrain = self._download(self.environment.terrain).astype(
            np.float32, copy=False
        )
        environment.wear = self._download(self.environment.wear).astype(
            np.float32, copy=False
        )
        environment.mortality_trace = self._download(
            self.environment.mortality_trace
        ).astype(np.float32, copy=False)
        if hasattr(self.environment, "resource_residue"):
            environment.resource_residue = self._download(
                self.environment.resource_residue
            ).astype(np.float32, copy=False)
            for name in (
                "resource_residue_field_roundoff_step",
                "total_resource_residue_field_roundoff",
                "resource_residue_deposit_roundoff_step",
                "total_resource_residue_deposit_roundoff",
            ):
                setattr(
                    environment,
                    name,
                    np.asarray(
                        getattr(self.environment, name, np.zeros(4)), dtype=np.float64
                    ).copy(),
                )
        if hasattr(self.environment, "total_resource_renewal_source"):
            for name in (
                "initial_resource_total",
                "resource_renewal_source_step",
                "resource_renewal_sink_step",
                "total_resource_renewal_source",
                "total_resource_renewal_sink",
                "resource_field_roundoff_step",
                "total_resource_field_roundoff",
                "resource_harvest_roundoff_step",
                "total_resource_harvest_roundoff",
            ):
                setattr(
                    environment,
                    name,
                    np.asarray(getattr(self.environment, name), dtype=np.float64).copy(),
                )
        information.field = self._download(self.information_field.field).astype(np.float32, copy=False)
        information.source = self._download(self.information_field.source).astype(np.float32, copy=False)
        information.age = self._download(self.information_field.age).astype(np.uint16, copy=False)

    def reverse_resource_environment(self) -> None:
        """Apply resource-only spatial reversal to authoritative device fields."""
        self.environment.reverse_resource_spatial_orientation()

    def reverse_environment(self) -> None:
        """Apply the configured spatial reversal to authoritative device fields."""
        self.environment.reverse_spatial_orientation()

    def update_fields(self, tick: int) -> None:
        self.environment.update(tick)
        self.information_field.propagate()

    def prepare(
        self,
        *,
        entity: Any,
        social: Any,
        information: InformationSystem,
        policy: ParametricPolicy,
        social_control_enabled: bool,
        run_seed: int,
        tick: int,
        retain_logits: bool,
        retain_policy_diagnostics: bool,
        need_host_resource_gradient: bool,
        entity_state_version: int,
        physiology_environment: Any | None = None,
        knowledge: KnowledgeSystem | None = None,
        resource_affinity_ablation_enabled: bool = False,
        resource_sensing_ablation_enabled: bool = False,
        danger_evidence_ablation_enabled: bool = False,
        knowledge_policy_ablation_enabled: bool = False,
    ) -> GpuPreparedStep:
        """Construct observations and actions, returning the CPU commit view."""
        xp = self.backend.xp
        if self.entity_state is None or self._entity_static_dirty:
            self.sync_entity_from_host(entity, social, entity_state_version)
        elif self._social_state_dirty:
            self._sync_social_from_host(social)
        state = self.entity_state
        if state is None:
            raise RuntimeError("entity device state has not been initialized")
        if state.version != int(entity_state_version):
            raise ValueError(
                "entity device mirror version mismatch: "
                f"mirror={state.version}, world={entity_state_version}"
            )
        active_host = np.flatnonzero(entity.alive).astype(np.int32)
        if active_host.size == 0:
            empty = np.empty(0, dtype=np.int32)
            empty_info = InformationObservation(
                signals=np.empty((0, 3), dtype=np.float32),
                signal_mask=np.empty((0, 3), dtype=bool),
                signal_age=np.empty((0, 3), dtype=np.float32),
                messages=np.empty((0, 0, 3), dtype=np.float32),
                message_mask=np.empty((0, 0), dtype=bool),
                message_age=np.empty((0, 0), dtype=np.uint32),
                message_confidence=np.empty((0, 0), dtype=np.float32),
                message_source_id=np.empty((0, 0), dtype=np.uint64),
                message_corruption=np.empty((0, 0), dtype=np.uint8),
                partner_energy=np.empty((0, 0), dtype=np.float32),
                partner_group_match=np.empty((0, 0), dtype=np.float32),
                partner_mask=np.empty((0, 0), dtype=bool),
                uncertainty=np.empty((0, 3), dtype=np.float32),
            )
            empty_decision = PolicyDecision(
                action=np.empty(0, dtype=np.int16),
                probability=np.empty(0, dtype=np.float32),
                entropy=np.empty(0, dtype=np.float32),
                direction_x=np.empty(0, dtype=np.float32),
                direction_y=np.empty(0, dtype=np.float32),
                selected_partner=np.empty(0, dtype=np.int32),
                logits=np.empty((0, 0), dtype=np.float32),
                features=(
                    np.empty(
                        (0, ParametricPolicy.STRATEGY_FEATURES),
                        dtype=np.float32,
                    )
                    if retain_policy_diagnostics
                    else None
                ),
                action_mask=(
                    np.empty((0, len(Action)), dtype=bool)
                    if retain_policy_diagnostics
                    else None
                ),
            )
            return GpuPreparedStep(
                empty,
                empty,
                np.empty((0, 4), dtype=np.float32),
                None,
                empty_info,
                empty_decision,
                0.0,
                0.0,
                0.0,
                np.empty(0, dtype=np.uint64),
                KnowledgePolicyPlan.empty(tick),
                np.empty((0, 4), dtype=np.float32),
                None,
                0.0,
                0.0,
            )

        # The versioned mirror is frozen for this prepare pass.  The CPU owns
        # mutation until it publishes the next final-state commit plan.
        sensor_quality_host = entity.sensor_quality()
        x = state.x
        y = state.y
        alive = state.alive
        stable_ids = state.stable_ids
        energy = state.energy
        integrity = state.integrity
        fertility = state.fertility
        genotype = state.genotype
        memory = state.memory
        groups = state.group_ids
        sensor_quality = state.sensor_quality

        timer = time.perf_counter()
        active = self.spatial.build(x, y, alive)
        partners = self.spatial.sample_partners(
            active,
            stable_ids,
            run_seed,
            tick,
            self.cfg.policy.partner_samples,
        )
        cells = self.spatial.entity_cells[active]
        self.backend.synchronize()
        spatial_seconds = time.perf_counter() - timer

        timer = time.perf_counter()
        # Delayed messages are an event queue owned by the CPU commit path.
        # Decode and capacity-resolve them into a sparse immutable plan; the
        # device observation stage materializes slots only for actual receivers.
        direct = information._receive_direct_plan(
            active_host,
            entity.entity_id,
            sensor_quality_host,
            run_seed,
            tick,
        )
        if self._measure_transfers:
            self._host_to_device_bytes += direct.semantic_transfer_nbytes
            self._direct_message_events = direct.size
            self._direct_message_dense_bytes_avoided = max(
                direct.dense_nbytes - direct.semantic_transfer_nbytes, 0
            )
        local_resources = self.environment.cell_values(cells)
        capacity = int(entity.alive.size)
        affinity_device = (
            xp.full(
                (capacity, RESOURCE_CHANNELS),
                AFFINITY_SCALE,
                dtype=xp.int32,
            )
            if resource_affinity_ablation_enabled
            else device_resource_affinity_quantized(
                genotype, self.cfg, xp=xp
            )
        )
        active_storage_room_fraction = storage_room_fraction(
            entity,
            active_host,
            self.cfg,
            genotype=entity.genotype[active_host],
            gene_start=ParametricPolicy.physiology_gene_start(self.cfg),
        )
        room_device = (
            None
            if active_storage_room_fraction is None
            else self._upload(
                active_storage_room_fraction,
                dtype=xp.float32,
            )
        )
        policy_local_resources = device_policy_resource_view(
            local_resources,
            self.cfg,
            resource_affinity_q=affinity_device[active],
            storage_room_fraction=room_device,
            xp=xp,
        )
        danger_evidence_device = (
            (
                xp.full(
                    (capacity, 2),
                    DANGER_EVIDENCE_SCALE,
                    dtype=xp.int32,
                )
                if danger_evidence_ablation_enabled
                else device_danger_evidence_quantized(
                    genotype, self.cfg, xp=xp
                )
            )
            if danger_evidence_enabled(self.cfg)
            else None
        )
        if self._measure_transfers:
            self._device_preprocess_rows = int(active_host.size)
            avoided = capacity * RESOURCE_CHANNELS * np.dtype(np.int32).itemsize
            if danger_evidence_device is not None:
                avoided += capacity * 2 * np.dtype(np.int32).itemsize
            if self.cfg.entities.resource_sensing_schema != "disabled":
                avoided += capacity * (RESOURCE_CHANNELS if self.cfg.entities.resource_sensing_schema in {"inherited-affinity-routed-gradient-radius-v2", "inherited-affinity-budgeted-gradient-radius-v3"} else 1) * np.dtype(np.int16).itemsize
            if active_storage_room_fraction is None:
                avoided += active_host.size * RESOURCE_CHANNELS * np.dtype(np.float32).itemsize
            if physiology_environment is not None:
                # The device now derives both oxygen-gradient components and only
                # receives one per-entity weight instead of two weighted vectors.
                avoided += active_host.size * np.dtype(np.float32).itemsize
            self._device_resident_host_bytes_avoided += int(avoided)
        local_resources_host: np.ndarray | None = None
        policy_local_resources_host: np.ndarray | None = None
        device_info = self.information_field.observe(
            stable_ids=stable_ids[active],
            cell_ids=cells,
            partners=partners,
            energy=energy,
            group_id=groups,
            own_group_id=groups[active],
            sensor_quality=sensor_quality[active],
            direct_message_plan=direct,
            run_seed=run_seed,
            tick=tick,
        )
        channel_routed_sensing = (
            self.cfg.entities.resource_sensing_schema
            in {
                "inherited-affinity-routed-gradient-radius-v2",
                "inherited-affinity-budgeted-gradient-radius-v3",
            }
        )
        sensing_radius_device = (
            xp.ones((capacity, RESOURCE_CHANNELS), dtype=xp.int16)
            if resource_sensing_ablation_enabled and channel_routed_sensing
            else xp.ones(capacity, dtype=xp.int16)
            if resource_sensing_ablation_enabled
            else device_resource_sensing_channel_radii(
                genotype,
                self.cfg,
                resource_affinity_q=affinity_device,
                xp=xp,
            )
            if channel_routed_sensing
            else device_resource_sensing_radius(genotype, self.cfg, xp=xp)
        )
        resource_gradient, danger_gradient = self.environment.gradients_for_entities(
            self.spatial.entity_cells,
            entity.alive.size,
            affinity_device,
            danger_evidence_device,
            sensing_radius_device,
        )
        cells_result: np.ndarray | None = None
        if physiology_environment is not None:
            oxygen_gx, oxygen_gy = self.environment.oxygen_gradient_for_entities(
                self.spatial.entity_cells,
                capacity,
            )
            oxygen_need = np.clip(
                1.0 - entity.oxygenation[active_host],
                0.0,
                1.0,
            )
            sensory_support = np.clip(
                entity.physiology_sensor_multiplier[active_host],
                0.1,
                2.0,
            )
            oxygen_weight = self._upload(
                np.float32(self.cfg.physiology.oxygen_gradient_weight)
                * oxygen_need
                * sensory_support,
                dtype=xp.float32,
            )
            resource_gradient[0][active] += oxygen_weight * oxygen_gx[active]
            resource_gradient[1][active] += oxygen_weight * oxygen_gy[active]
        self.backend.synchronize()
        observation_seconds = time.perf_counter() - timer

        knowledge_context_keys = np.empty(0, dtype=np.uint64)
        knowledge_policy_plan = KnowledgePolicyPlan.empty(tick)
        working_memory_state_features: np.ndarray | None = None
        routing_cost_result: RoutingCostBudgetResult | None = None
        cost_free_plan = KnowledgePolicyPlan.empty(tick)
        if knowledge is not None and knowledge.kcfg.learning_enabled:
            device_context_keys = encode_local_context(
                policy_local_resources[:, 0],
                self.environment.danger_for_cells(
                    cells,
                    (
                        danger_evidence_device[active]
                        if danger_evidence_device is not None
                        else None
                    ),
                ),
                energy[active],
                integrity[active],
                groups[active] != 0,
                max_energy=self.cfg.entities.max_energy,
            )
            knowledge_context_keys = self._download(device_context_keys).astype(
                np.uint64, copy=False
            )
            if local_resources_host is None:
                local_resources_host = self._download(local_resources).astype(
                    np.float32, copy=False
                )
            affinity_host = (
                np.full(
                    (capacity, RESOURCE_CHANNELS),
                    AFFINITY_SCALE,
                    dtype=np.int32,
                )
                if resource_affinity_ablation_enabled
                else resource_affinity_quantized(entity.genotype, self.cfg)
            )
            policy_local_resources_host = policy_resource_view(
                local_resources_host,
                entity.genotype[active_host],
                self.cfg,
                resource_affinity_q=affinity_host[active_host],
                storage_room_fraction=active_storage_room_fraction,
            )
            local_resource_host = policy_local_resources_host[:, 0]
            if knowledge.kcfg.working_memory_enabled:
                working_memory_state_features = np.asarray(
                    latent_router_state_features(
                        energy=entity.energy[active_host],
                        integrity=entity.integrity[active_host],
                        fertility=entity.fertility[active_host],
                        local_resource=local_resource_host,
                        max_energy=self.cfg.entities.max_energy,
                        resource_capacity=self.cfg.environment.resource_capacity[0],
                    ),
                    dtype=np.float32,
                ).copy()
            if (
                knowledge.kcfg.policy_influence_enabled
                and not knowledge_policy_ablation_enabled
            ):
                if knowledge.kcfg.latent_policy_enabled:
                    if knowledge.latent_store is None:
                        raise RuntimeError("latent policy is enabled without a latent content store")
                    knowledge.latent_store.ensure_catalog(knowledge.catalog)
                    # Publish the small four-coordinate router state through
                    # the CPU reference path.  Variable-width projections and
                    # inherited routing still execute on the GPU, while a
                    # backend-specific division cannot move a quantized state
                    # coordinate across a later action boundary.
                    router_state = (
                        working_memory_state_features
                        if working_memory_state_features is not None
                        else latent_router_state_features(
                            energy=entity.energy[active_host],
                            integrity=entity.integrity[active_host],
                            fertility=entity.fertility[active_host],
                            local_resource=local_resource_host,
                            max_energy=self.cfg.entities.max_energy,
                            resource_capacity=self.cfg.environment.resource_capacity[0],
                        )
                    )
                    active_genotype_device = genotype[active]
                    active_genotype_host = entity.genotype[active_host]
                    knowledge_policy_plan = build_latent_knowledge_policy_plan(
                        knowledge.observation,
                        knowledge.latent_store,
                        tick=tick,
                        entity_ids=entity.entity_id[active_host],
                        holder_subject_ids=entity.primary_subject_id[active_host],
                        context_keys=knowledge_context_keys,
                        genotype=active_genotype_device,
                        router_gene_start=ParametricPolicy.latent_router_gene_start(self.cfg),
                        selection_gene_start=(
                            ParametricPolicy.sparse_selection_gene_start(self.cfg)
                            if knowledge.kcfg.sparse_selection_enabled else None
                        ),
                        working_memory_q=(
                            np.zeros_like(entity.working_memory_q[active_host])
                            if knowledge.working_memory_ablation_enabled
                            else entity.working_memory_q[active_host]
                        ),
                        selection_enabled=(
                            knowledge.kcfg.sparse_selection_enabled
                            and not knowledge.sparse_selection_ablation_enabled
                        ),
                        use_strength=ParametricPolicy.knowledge_use_strength_from_genotype(
                            active_genotype_host
                        ),
                        state_features=router_state,
                        config=knowledge.kcfg,
                        action_count=len(Action),
                    )
                else:
                    host_genotype = entity.genotype[active_host]
                    knowledge_policy_plan = build_knowledge_policy_plan(
                        knowledge.observation,
                        tick=tick,
                        entity_ids=entity.entity_id[active_host],
                        holder_subject_ids=entity.primary_subject_id[active_host],
                        context_keys=knowledge_context_keys,
                        outcome_preferences=ParametricPolicy.outcome_preferences_from_genotype(
                            host_genotype
                        ),
                        use_strength=ParametricPolicy.knowledge_use_strength_from_genotype(
                            host_genotype
                        ),
                        config=knowledge.kcfg,
                        action_count=len(Action),
                    )
                cost_free_plan = knowledge_policy_plan
                if knowledge.kcfg.routing_cost_enabled and (
                    knowledge_policy_plan.size
                    or knowledge_policy_plan.work_active_rows.size
                ):
                    routing_cost_result = apply_routing_cost_budget(
                        knowledge_policy_plan,
                        active_energy=entity.energy[active_host],
                        config=knowledge.kcfg,
                        action_count=len(Action),
                    )
                    knowledge_policy_plan = routing_cost_result.plan
                    charged_rows = routing_cost_result.active_rows[
                        routing_cost_result.committed_energy > 0.0
                    ]
                    if charged_rows.size:
                        world_rows = active_host[charged_rows]
                        charges = routing_cost_result.committed_energy[
                            routing_cost_result.committed_energy > 0.0
                        ]
                        entity.energy[world_rows] = np.maximum(
                            entity.energy[world_rows].astype(np.float64) - charges, 0.0
                        ).astype(np.float32)
                if self._measure_transfers:
                    self._host_to_device_bytes += knowledge_policy_plan.semantic_transfer_nbytes

        timer = time.perf_counter()
        if social_control_enabled:
            group_direction = (state.group_dir_x, state.group_dir_y)
        else:
            group_direction = (xp.zeros_like(energy), xp.zeros_like(energy))
        cost_free_device_decision = None
        if (
            routing_cost_result is not None
            and routing_cost_result.rejected_action_count > 0
        ):
            cost_free_device_decision = policy.decide(
                active=active,
                stable_ids=stable_ids,
                energy=energy,
                integrity=integrity,
                fertility=fertility,
                genotype=genotype,
                memory=memory,
                local_resources=policy_local_resources,
                resource_gradient=resource_gradient,
                danger_gradient=danger_gradient,
                group_direction=group_direction,
                partners=partners,
                info=device_info,
                run_seed=run_seed,
                tick=tick,
                knowledge_plan=cost_free_plan,
            )
        memory_free_device_decision = None
        if self.cfg.knowledge.working_memory_enabled:
            memory_free_device_decision = policy.decide(
                active=active,
                stable_ids=stable_ids,
                energy=energy,
                integrity=integrity,
                fertility=fertility,
                genotype=genotype,
                memory=xp.zeros_like(memory),
                local_resources=policy_local_resources,
                resource_gradient=resource_gradient,
                danger_gradient=danger_gradient,
                group_direction=group_direction,
                partners=partners,
                info=device_info,
                run_seed=run_seed,
                tick=tick,
                knowledge_plan=knowledge_policy_plan,
            )
        device_decision = policy.decide(
            active=active,
            stable_ids=stable_ids,
            energy=energy,
            integrity=integrity,
            fertility=fertility,
            genotype=genotype,
            memory=memory,
            local_resources=policy_local_resources,
            resource_gradient=resource_gradient,
            danger_gradient=danger_gradient,
            group_direction=group_direction,
            partners=partners,
            info=device_info,
            run_seed=run_seed,
            tick=tick,
            knowledge_plan=knowledge_policy_plan,
        )
        self.backend.synchronize()
        if routing_cost_result is not None and routing_cost_result.committed_total > 0.0:
            energy[active] = xp.asarray(entity.energy[active_host], dtype=xp.float32)
        policy_seconds = time.perf_counter() - timer

        # One synchronized host boundary for the CPU intent/commit stages.
        active_result = active_host
        if cells_result is None:
            cells_result = self._download(cells).astype(np.int32, copy=False)
        if local_resources_host is None:
            local_resources_host = self._download(local_resources).astype(
                np.float32, copy=False
            )
        local_result = local_resources_host
        resource_result = (
            tuple(self._download(value).astype(np.float32, copy=False) for value in resource_gradient)
            if need_host_resource_gradient
            else None
        )
        signal_detection_rate = float(
            self._download(
                xp.mean(device_info.signal_mask, dtype=xp.float64)
            ).item()
        )
        partner_detection_rate = (
            float(
                self._download(
                    xp.mean(device_info.partner_mask, dtype=xp.float64)
                ).item()
            )
            if int(device_info.partner_mask.size)
            else 0.0
        )
        need_host_information = (
            retain_policy_diagnostics
            or not self.cfg.knowledge.working_memory_enabled
        )
        if self._measure_transfers and not need_host_information:
            self._device_resident_host_bytes_avoided += int(
                device_info.signals.nbytes
                + device_info.signal_mask.nbytes
                + device_info.partner_mask.nbytes
                + device_info.uncertainty.nbytes
            )
        host_info = (
            InformationObservation(
                signals=self._download(device_info.signals).astype(
                    np.float32, copy=False
                ),
                signal_mask=self._download(device_info.signal_mask).astype(
                    bool, copy=False
                ),
                signal_age=self._download(device_info.signal_age).astype(
                    np.float32, copy=False
                ),
                messages=np.empty((active_result.size, 0, 3), dtype=np.float32),
                message_mask=np.empty((active_result.size, 0), dtype=bool),
                message_age=np.empty((active_result.size, 0), dtype=np.uint32),
                message_confidence=np.empty((active_result.size, 0), dtype=np.float32),
                message_source_id=np.empty((active_result.size, 0), dtype=np.uint64),
                message_corruption=np.empty((active_result.size, 0), dtype=np.uint8),
                partner_energy=self._download(device_info.partner_energy).astype(
                    np.float32, copy=False
                ),
                partner_group_match=self._download(
                    device_info.partner_group_match
                ).astype(np.float32, copy=False),
                partner_mask=self._download(device_info.partner_mask).astype(
                    bool, copy=False
                ),
                uncertainty=self._download(device_info.uncertainty).astype(
                    np.float32, copy=False
                ),
            )
            if need_host_information
            else None
        )
        host_decision = PolicyDecision(
            action=self._download(device_decision.action).astype(np.int16, copy=False),
            probability=self._download(device_decision.probability).astype(np.float32, copy=False),
            entropy=self._download(device_decision.entropy).astype(np.float32, copy=False),
            direction_x=self._download(device_decision.direction_x).astype(np.float32, copy=False),
            direction_y=self._download(device_decision.direction_y).astype(np.float32, copy=False),
            selected_partner=self._download(device_decision.selected_partner).astype(np.int32, copy=False),
            logits=(
                self._download(device_decision.logits).astype(np.float32, copy=False)
                if retain_logits or retain_policy_diagnostics
                else np.empty((active_result.size, 0), dtype=np.float32)
            ),
            features=(
                self._download(device_decision.features).astype(
                    np.float32, copy=False
                )
                if retain_policy_diagnostics
                and device_decision.features is not None
                else None
            ),
            action_mask=(
                self._download(device_decision.action_mask).astype(
                    bool, copy=False
                )
                if retain_policy_diagnostics
                and device_decision.action_mask is not None
                else None
            ),
            genetic_logits=(
                self._download(device_decision.genetic_logits).astype(np.float32, copy=False)
                if retain_policy_diagnostics and device_decision.genetic_logits is not None
                else None
            ),
            knowledge_logits=(
                self._download(device_decision.knowledge_logits).astype(np.float32, copy=False)
                if retain_policy_diagnostics and device_decision.knowledge_logits is not None
                else None
            ),
            genetic_action=(
                self._download(device_decision.genetic_action).astype(np.int16, copy=False)
                if device_decision.genetic_action is not None
                else None
            ),
            linear_knowledge_logits=(
                self._download(device_decision.linear_knowledge_logits).astype(
                    np.float32, copy=False
                )
                if retain_policy_diagnostics
                and device_decision.linear_knowledge_logits is not None
                else None
            ),
            linear_knowledge_action=(
                self._download(device_decision.linear_knowledge_action).astype(
                    np.int16, copy=False
                )
                if device_decision.linear_knowledge_action is not None
                else None
            ),
            cost_free_knowledge_action=(
                self._download(cost_free_device_decision.action).astype(
                    np.int16, copy=False
                )
                if cost_free_device_decision is not None
                else None
            ),
            memory_free_knowledge_action=(
                self._download(memory_free_device_decision.action).astype(
                    np.int16, copy=False
                )
                if memory_free_device_decision is not None
                else None
            ),
        )
        return GpuPreparedStep(
            active_result,
            cells_result,
            local_result,
            resource_result,
            host_info,
            host_decision,
            spatial_seconds,
            observation_seconds,
            policy_seconds,
            knowledge_context_keys,
            knowledge_policy_plan,
            working_memory_state_features,
            routing_cost_result,
            signal_detection_rate,
            partner_detection_rate,
        )

    def resolve_harvest(self, cell_ids: np.ndarray, rates: np.ndarray) -> np.ndarray:
        cells = self._upload(cell_ids, dtype=self.backend.xp.int32)
        requests = self._upload(rates, dtype=self.backend.xp.float32)
        result = self.environment.resolve_harvest(cells, requests)
        return self._download(result).astype(np.float32, copy=False)

    def resolve_harvest_plan(
        self,
        snapshot: ActionResolutionSnapshot,
        intents: ActionIntentBatch,
    ) -> HarvestResolution:
        """Resolve the harvest-only conflict subset on device without mutation.

        The runtime receives exactly the immutable resolver inputs, derives
        the reference ``(cell_id, entity_id)`` stable ordering on the device,
        and asks :class:`DeviceEnvironment` for a fair allocation.  It never
        calls ``commit_harvest``: returning a host ``HarvestResolution`` keeps
        resolution separate from the later authoritative backend commit and
        makes that commit replayable.
        """
        xp = self.backend.xp
        action = self._upload(intents.action, dtype=xp.int16)
        device_rows = xp.flatnonzero(action == int(Action.HARVEST)).astype(xp.int32, copy=False)
        if int(device_rows.size) == 0:
            empty = np.empty((0, DeviceEnvironment.RESOURCE_CHANNELS), dtype=np.float32)
            return HarvestResolution(
                np.empty(0, dtype=np.int32),
                np.empty(0, dtype=np.int32),
                empty.copy(),
                empty.copy(),
                empty.copy(),
                empty.copy(),
            )

        # These are copies of the supplied read-only snapshot, not pointers
        # into mutable host world state.  Keeping the key construction here
        # also avoids a device->host->device round trip for ordered cells and
        # harvest-rate rows.
        active = self._upload(snapshot.active, dtype=xp.int32)
        cells = self._upload(snapshot.cells, dtype=xp.int32)
        carrier_index = self._upload(intents.carrier_index, dtype=xp.int32)
        carrier_id = self._upload(intents.carrier_id, dtype=xp.uint64)
        observation_rows = xp.searchsorted(active, carrier_index[device_rows])
        device_cells = cells[observation_rows]
        order = xp.lexsort(xp.stack((carrier_id[device_rows], device_cells)))
        device_rows = device_rows[order]
        device_cells = device_cells[order]

        host_rows = self._download(device_rows).astype(np.int32, copy=False)
        affinity = (
            None
            if not selective_harvest_enabled(self.cfg)
            else (
                None
                if (snapshot.harvest_preference_q is None and snapshot.resource_affinity_q is None)
                else (
                    snapshot.harvest_preference_q[intents.carrier_index[host_rows]]
                    if snapshot.harvest_preference_q is not None
                    else snapshot.resource_affinity_q[intents.carrier_index[host_rows]]
                )
            )
        )
        channel_draws = (
            None
            if not selective_harvest_enabled(self.cfg)
            else uniform01(
                RandomContext(
                    self.cfg.run.seed,
                    intents.submit_tick,
                    phase=42,
                    stream=Stream.HARVEST_CHANNEL,
                ),
                intents.carrier_id[host_rows],
                draw_index=0,
            )
        )
        unconstrained_rates = harvest_request_rates(
            affinity,
            self.cfg,
            rows=int(host_rows.size),
            channel_draws=channel_draws,
        )
        raw_room = (
            None
            if snapshot.raw_harvest_storage_room is None
            else snapshot.raw_harvest_storage_room[intents.carrier_index[host_rows]]
        )
        host_rates, storage_rejected = constrain_harvest_request_rates(
            unconstrained_rates, raw_room
        )
        rates = self._upload(host_rates, dtype=xp.float32)
        device_gathered = self.environment.resolve_harvest(device_cells, rates)
        return HarvestResolution(
            host_rows,
            self._download(device_cells).astype(np.int32, copy=False),
            self._download(device_gathered).astype(np.float32, copy=False),
            np.asarray(host_rates, dtype=np.float32),
            np.asarray(unconstrained_rates, dtype=np.float32),
            np.asarray(storage_rejected, dtype=np.float32),
        )

    def commit_harvest(self, cell_ids: np.ndarray, gathered: np.ndarray) -> None:
        """Commit harvested resources with CPU-reference segment totals.

        Harvest amounts are produced on the host-side resolution boundary.
        Reducing them again with CuPy ``reduceat`` can use a different FP32
        tree than NumPy and make persistent resource state diverge before any
        action differs.  Reduce each channel with the CPU reference and upload
        only the unique affected cells.
        """
        cells = np.asarray(cell_ids)
        amounts = np.asarray(gathered, dtype=np.float32)
        if amounts.ndim != 2 or amounts.shape != (cells.size, self.environment.RESOURCE_CHANNELS):
            raise ValueError(
                "gathered must have shape (len(cell_ids), RESOURCE_CHANNELS)"
            )
        if cells.size == 0:
            return
        cell_count = self.cfg.world.grid_x * self.cfg.world.grid_y
        xp = self.backend.xp
        flat = self.environment.resources.reshape(
            self.environment.RESOURCE_CHANNELS, -1
        )
        for channel in range(self.environment.RESOURCE_CHANNELS):
            total_taken = stable_segmented_sum(
                cells, amounts[:, channel], cell_count, dtype=np.float32
            )
            occupied = np.flatnonzero(total_taken != 0.0).astype(
                np.int32, copy=False
            )
            if occupied.size == 0:
                continue
            device_cells = self._upload(occupied, dtype=xp.int32)
            device_totals = self._upload(
                total_taken[occupied], dtype=xp.float32
            )
            flat[channel, device_cells] = xp.maximum(
                flat[channel, device_cells] - device_totals, xp.float32(0.0)
            ).astype(xp.float32)

    def deposit_resource_residue(self, cell_ids: np.ndarray, amounts: np.ndarray) -> np.ndarray:
        """Deposit external residue on the authoritative device environment."""
        from se.env.recycling import deposit_resource_residue

        return deposit_resource_residue(self.environment, cell_ids, amounts)

    def _emit_reference_batch(
        self, channel: int, cell_ids: np.ndarray, strengths: np.ndarray
    ) -> None:
        """Commit one sparse signal batch with CPU-reference FP32 reduction.

        NumPy and CuPy ``ufunc.reduceat`` are deterministic within each
        backend, but they do not promise the same FP32 reduction tree.  Signal
        source values are persistent world state, so a few ulps here compound
        through propagation and can eventually change categorical actions,
        births, or deaths.  The plan already resides on the host; reduce it
        with the authoritative NumPy implementation, then upload only the
        unique non-zero cell totals.  Device indices are unique, so the final
        assignment has no scatter race.
        """
        if not 0 <= channel < self.information_field.CHANNELS:
            raise ValueError(f"invalid signal channel {channel}")
        cells = np.asarray(cell_ids)
        values = np.asarray(strengths, dtype=np.float32)
        cell_count = self.cfg.world.grid_x * self.cfg.world.grid_y
        contribution = stable_segmented_sum(
            cells, values, cell_count, dtype=np.float32
        )
        occupied = np.flatnonzero(contribution != 0.0).astype(np.int32, copy=False)
        if occupied.size == 0:
            return
        xp = self.backend.xp
        device_cells = self._upload(occupied, dtype=xp.int32)
        device_values = self._upload(contribution[occupied], dtype=xp.float32)
        flat = self.information_field.source[channel].reshape(-1)
        # Explicit read/add/write mirrors NumPy's ``flat += contribution`` for
        # the only cells whose value can change.  ``device_cells`` is unique.
        flat[device_cells] = (flat[device_cells] + device_values).astype(xp.float32)

    def emit(self, channel: int, cell_ids: np.ndarray, strengths: np.ndarray) -> None:
        self._emit_reference_batch(channel, cell_ids, strengths)

    def emit_plan(self, plan: SignalEmissionPlan) -> None:
        """Commit due signal batches using the CPU-reference reduction order."""
        for batch in plan.batches:
            self._emit_reference_batch(batch.channel, batch.cell_ids, batch.strengths)

    def hazard_for_cells(self, cell_ids: np.ndarray) -> np.ndarray:
        cells = self._upload(cell_ids, dtype=self.backend.xp.int32)
        values = self.environment.hazard.reshape(-1)[cells]
        return self._download(values).astype(np.float32, copy=False)

    def physiology_for_cells(self, cell_ids: np.ndarray) -> np.ndarray:
        """Download only the requested cell physiology triplets from device state."""
        cells = self._upload(cell_ids, dtype=self.backend.xp.int32)
        values = self.environment.physiology_for_cells(cells)
        return self._download(values).astype(np.float32, copy=False)

    def physiology_fields_to_host(self) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Materialize current device-owned physiology fields for diagnostics."""
        return tuple(
            self._download(value).astype(np.float32, copy=False)
            for value in (
                self.environment.oxygen,
                self.environment.terrain,
                self.environment.wear,
            )
        )

    def danger_for_cells(
        self, cell_ids: np.ndarray, evidence_q: np.ndarray | None = None
    ) -> np.ndarray:
        cells = self._upload(cell_ids, dtype=self.backend.xp.int32)
        device_evidence = (
            None
            if evidence_q is None
            else self._upload(evidence_q, dtype=self.backend.xp.int32)
        )
        values = self.environment.danger_for_cells(cells, device_evidence)
        return self._download(values).astype(np.float32, copy=False)

    def deposit_mortality_trace(
        self, cell_ids: np.ndarray, weights: np.ndarray | None = None
    ) -> None:
        cells = self._upload(cell_ids, dtype=self.backend.xp.int32)
        device_weights = (
            None
            if weights is None
            else self._upload(weights, dtype=self.backend.xp.float32)
        )
        self.environment.deposit_mortality_trace(cells, device_weights)


__all__ = [
    "DeviceEntityState",
    "GpuPreparedStep",
    "GpuTransferStats",
    "HybridGpuRuntime",
    "device_danger_evidence_quantized",
    "device_policy_resource_view",
    "device_resource_affinity_quantized",
]
