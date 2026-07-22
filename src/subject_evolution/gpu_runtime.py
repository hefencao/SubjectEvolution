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
from .config import SimulationConfig
from .execution import ActionResolutionSnapshot, HarvestResolution
from .gpu_environment import DeviceEnvironment, DeviceInformationField
from .information import InformationObservation, InformationSystem, SignalEmissionPlan
from .intents import ActionIntentBatch
from .policy import Action, ParametricPolicy, PolicyDecision
from .spatial import SpatialIndex


@dataclass(frozen=True)
class GpuPreparedStep:
    """Host-side inputs required by the existing CPU intent/commit phases."""

    active: np.ndarray
    cells: np.ndarray
    local_resources: np.ndarray
    resource_gradient: tuple[np.ndarray, np.ndarray] | None
    information: InformationObservation
    decision: PolicyDecision
    spatial_seconds: float
    observation_seconds: float
    policy_seconds: float


@dataclass(frozen=True)
class GpuTransferStats:
    """Explicit host/device traffic recorded during one world step."""

    host_to_device_bytes: int = 0
    device_to_host_bytes: int = 0
    direct_message_events: int = 0
    direct_message_dense_bytes_avoided: int = 0


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
        self._stable_ids: Any | None = None
        self._genotype: Any | None = None
        self._entity_static_dirty = True
        self._group_ids: Any | None = None
        self._group_dir_x: Any | None = None
        self._group_dir_y: Any | None = None
        self._social_state_dirty = True
        self._measure_transfers = False
        self._host_to_device_bytes = 0
        self._device_to_host_bytes = 0
        self._direct_message_events = 0
        self._direct_message_dense_bytes_avoided = 0

    def begin_step_transfer_measurement(self) -> None:
        self._measure_transfers = True
        self._host_to_device_bytes = 0
        self._device_to_host_bytes = 0
        self._direct_message_events = 0
        self._direct_message_dense_bytes_avoided = 0

    def finish_step_transfer_measurement(self) -> GpuTransferStats:
        result = GpuTransferStats(
            host_to_device_bytes=self._host_to_device_bytes,
            device_to_host_bytes=self._device_to_host_bytes,
            direct_message_events=self._direct_message_events,
            direct_message_dense_bytes_avoided=self._direct_message_dense_bytes_avoided,
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

    def mark_entity_static_dirty(self) -> None:
        """Require stable IDs and genotypes to be re-uploaded next tick.

        These arrays change only when the CPU commit creates or destroys an
        entity.  Keeping their device copies between ordinary ticks removes a
        sizeable host->device transfer without making dynamic state stale.
        """
        self._entity_static_dirty = True

    def mark_social_state_dirty(self) -> None:
        """Require low-frequency group fields to be re-uploaded next tick."""
        self._social_state_dirty = True

    def sync_from_host(self, environment: Any, information: InformationSystem) -> None:
        """Seed the device mirror from an existing CPU world snapshot."""
        xp = self.backend.xp
        self.environment.resources = self._upload(environment.resources, dtype=xp.float32, copy=True)
        self.environment.capacity = self._upload(environment.capacity, dtype=xp.float32, copy=True)
        self.environment.regeneration = self._upload(environment.regeneration, dtype=xp.float32, copy=True)
        self.environment.hazard = self._upload(environment.hazard, dtype=xp.float32, copy=True)
        self.information_field.field = self._upload(information.field, dtype=xp.float32, copy=True)
        self.information_field.source = self._upload(information.source, dtype=xp.float32, copy=True)
        self.information_field.age = self._upload(information.age, dtype=xp.uint16, copy=True)

    def sync_to_host(self, environment: Any, information: InformationSystem) -> None:
        """Expose the current device fields to CPU-only inspection and cloning."""
        environment.resources = self._download(self.environment.resources).astype(np.float32, copy=False)
        environment.capacity = self._download(self.environment.capacity).astype(np.float32, copy=False)
        environment.regeneration = self._download(self.environment.regeneration).astype(np.float32, copy=False)
        environment.hazard = self._download(self.environment.hazard).astype(np.float32, copy=False)
        information.field = self._download(self.information_field.field).astype(np.float32, copy=False)
        information.source = self._download(self.information_field.source).astype(np.float32, copy=False)
        information.age = self._download(self.information_field.age).astype(np.uint16, copy=False)

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
        need_host_resource_gradient: bool,
    ) -> GpuPreparedStep:
        """Construct observations and actions, returning the CPU commit view."""
        xp = self.backend.xp
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
            )

        # Copy the world snapshot once.  The CPU owns mutation after this
        # boundary, so all device work sees a stable tick snapshot.
        sensor_quality_host = entity.sensor_quality()
        x = self._upload(entity.x, dtype=xp.float32)
        y = self._upload(entity.y, dtype=xp.float32)
        alive = self._upload(entity.alive, dtype=bool)
        if self._entity_static_dirty or self._stable_ids is None or self._genotype is None:
            self._stable_ids = self._upload(entity.entity_id, dtype=xp.uint64)
            self._genotype = self._upload(entity.genotype, dtype=xp.float32)
            self._entity_static_dirty = False
        stable_ids = self._stable_ids
        energy = self._upload(entity.energy, dtype=xp.float32)
        integrity = self._upload(entity.integrity, dtype=xp.float32)
        fertility = self._upload(entity.fertility, dtype=xp.float32)
        genotype = self._genotype
        memory = self._upload(entity.memory, dtype=xp.float32)
        if (
            self._social_state_dirty
            or self._group_ids is None
            or self._group_dir_x is None
            or self._group_dir_y is None
        ):
            self._group_ids = self._upload(social.group_id, dtype=xp.uint64)
            self._group_dir_x = self._upload(social.group_dir_x, dtype=xp.float32)
            self._group_dir_y = self._upload(social.group_dir_y, dtype=xp.float32)
            self._social_state_dirty = False
        groups = self._group_ids
        sensor_quality = self._upload(sensor_quality_host, dtype=xp.float32)

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
        resource_gradient, danger_gradient = self.environment.gradients_for_entities(
            self.spatial.entity_cells,
            entity.alive.size,
        )
        self.backend.synchronize()
        observation_seconds = time.perf_counter() - timer

        timer = time.perf_counter()
        if social_control_enabled:
            group_direction = (self._group_dir_x, self._group_dir_y)
        else:
            group_direction = (xp.zeros_like(energy), xp.zeros_like(energy))
        device_decision = policy.decide(
            active=active,
            stable_ids=stable_ids,
            energy=energy,
            integrity=integrity,
            fertility=fertility,
            genotype=genotype,
            memory=memory,
            local_resources=local_resources,
            resource_gradient=resource_gradient,
            danger_gradient=danger_gradient,
            group_direction=group_direction,
            partners=partners,
            info=device_info,
            run_seed=run_seed,
            tick=tick,
        )
        self.backend.synchronize()
        policy_seconds = time.perf_counter() - timer

        # One synchronized host boundary for the CPU intent/commit stages.
        active_result = active_host
        cells_result = self._download(cells).astype(np.int32, copy=False)
        local_result = self._download(local_resources).astype(np.float32, copy=False)
        resource_result = (
            tuple(self._download(value).astype(np.float32, copy=False) for value in resource_gradient)
            if need_host_resource_gradient
            else None
        )
        host_info = InformationObservation(
            signals=self._download(device_info.signals).astype(np.float32, copy=False),
            signal_mask=self._download(device_info.signal_mask).astype(bool, copy=False),
            signal_age=np.empty((active_result.size, 3), dtype=np.float32),
            messages=np.empty((active_result.size, 0, 3), dtype=np.float32),
            message_mask=np.empty((active_result.size, 0), dtype=bool),
            message_age=np.empty((active_result.size, 0), dtype=np.uint32),
            message_confidence=np.empty((active_result.size, 0), dtype=np.float32),
            message_source_id=np.empty((active_result.size, 0), dtype=np.uint64),
            message_corruption=np.empty((active_result.size, 0), dtype=np.uint8),
            partner_energy=np.empty((active_result.size, 0), dtype=np.float32),
            partner_group_match=np.empty((active_result.size, 0), dtype=np.float32),
            partner_mask=self._download(device_info.partner_mask).astype(bool, copy=False),
            uncertainty=self._download(device_info.uncertainty).astype(np.float32, copy=False),
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
                if retain_logits
                else np.empty((active_result.size, 0), dtype=np.float32)
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
        the subsequent CPU world commit authoritative and replayable.
        """
        xp = self.backend.xp
        action = self._upload(intents.action, dtype=xp.int16)
        device_rows = xp.flatnonzero(action == int(Action.HARVEST)).astype(xp.int32, copy=False)
        if int(device_rows.size) == 0:
            return HarvestResolution(
                np.empty(0, dtype=np.int32),
                np.empty(0, dtype=np.int32),
                np.empty((0, DeviceEnvironment.RESOURCE_CHANNELS), dtype=np.float32),
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

        base = self.cfg.entities.harvest_rate
        rate = xp.asarray([base, base * 0.45, base * 0.25, base * 0.18], dtype=xp.float32)
        rates = xp.broadcast_to(rate, (device_rows.size, DeviceEnvironment.RESOURCE_CHANNELS))
        device_gathered = self.environment.resolve_harvest(device_cells, rates)
        return HarvestResolution(
            self._download(device_rows).astype(np.int32, copy=False),
            self._download(device_cells).astype(np.int32, copy=False),
            self._download(device_gathered).astype(np.float32, copy=False),
        )

    def commit_harvest(self, cell_ids: np.ndarray, gathered: np.ndarray) -> None:
        self.environment.commit_harvest(
            self._upload(cell_ids, dtype=self.backend.xp.int32),
            self._upload(gathered, dtype=self.backend.xp.float32),
        )

    def emit(self, channel: int, cell_ids: np.ndarray, strengths: np.ndarray) -> None:
        self.information_field.emit(
            channel,
            self._upload(cell_ids, dtype=self.backend.xp.int32),
            self._upload(strengths, dtype=self.backend.xp.float32),
        )

    def emit_plan(self, plan: SignalEmissionPlan) -> None:
        """Transfer only due channel batches across the explicit GPU boundary."""
        for batch in plan.batches:
            self.information_field.emit(
                batch.channel,
                self._upload(batch.cell_ids, dtype=self.backend.xp.int32),
                self._upload(batch.strengths, dtype=self.backend.xp.float32),
            )

    def hazard_for_cells(self, cell_ids: np.ndarray) -> np.ndarray:
        cells = self._upload(cell_ids, dtype=self.backend.xp.int32)
        values = self.environment.hazard.reshape(-1)[cells]
        return self._download(values).astype(np.float32, copy=False)


__all__ = ["GpuPreparedStep", "GpuTransferStats", "HybridGpuRuntime"]
