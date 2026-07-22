from __future__ import annotations

from dataclasses import dataclass
import copy
import json
from pathlib import Path
import time
import numpy as np

from . import __version__
from .backend import BackendUnavailableError
from .config import SimulationConfig
from .control import (
    ControlArbiter,
    ControllerKind,
    HeuristicSocialGuidanceArbiter,
    SingleProposalControlArbiter,
    body_control_proposal,
    social_guidance_control_proposal,
)
from .environment import Environment
from .execution import (
    ActionConflictResolver,
    ActionResolutionSnapshot,
    DeterministicActionConflictResolver,
    GpuActionConflictResolver,
    ShareResolution,
)
from .gpu_runtime import HybridGpuRuntime
from .information import InformationSystem, SignalEmissionBatch, SignalEmissionPlan, SignalEmissionScheduler
from .intents import (
    ActionIntentBatch,
    ActionResolutionBatch,
    FailureReason,
    build_intents,
)
from .lifecycle import (
    BirthAllocationPlan,
    DeathCause,
    DeathEventPlan,
    empty_birth_allocation_plan,
    empty_death_event_plan,
    plan_birth_allocations,
    plan_death_events,
)
from .metrics import MetricsWriter
from .policy import Action, ParametricPolicy
from .random_api import RandomContext, Stream, normal, uniform01
from .social import GroupSummary, SocialSystem
from .spatial import SpatialIndex
from .subjects import CandidateSubjectGraph


@dataclass
class StepStats:
    births: int = 0
    deaths: int = 0
    harvested_energy: float = 0.0
    shared_energy: float = 0.0
    signals: int = 0
    group_count: int = 0
    mean_group_size: float = 0.0
    action_entropy: float = 0.0
    signal_detection_rate: float = 0.0
    partner_detection_rate: float = 0.0
    move_social_fraction: float = 0.0
    heuristic_guidance_actions: int = 0
    direct_messages: int = 0
    environment_seconds: float = 0.0
    spatial_seconds: float = 0.0
    observation_seconds: float = 0.0
    policy_seconds: float = 0.0
    conflict_seconds: float = 0.0
    graph_seconds: float = 0.0


class EntityState:
    GENOTYPE_SIZE = 8
    MEMORY_SIZE = 4

    def __init__(self, cfg: SimulationConfig) -> None:
        self.cfg = cfg
        cap = cfg.world.max_entities
        initial = cfg.world.initial_entities
        self.entity_id = np.zeros(cap, dtype=np.uint64)
        self.alive = np.zeros(cap, dtype=bool)
        self.x = np.zeros(cap, dtype=np.float32)
        self.y = np.zeros(cap, dtype=np.float32)
        self.vx = np.zeros(cap, dtype=np.float32)
        self.vy = np.zeros(cap, dtype=np.float32)
        self.energy = np.zeros(cap, dtype=np.float32)
        self.integrity = np.zeros(cap, dtype=np.float32)
        self.material = np.zeros(cap, dtype=np.float32)
        self.information_store = np.zeros(cap, dtype=np.float32)
        self.fertility = np.zeros(cap, dtype=np.float32)
        self.age = np.zeros(cap, dtype=np.uint32)
        self.lineage_id = np.zeros(cap, dtype=np.uint64)
        self.primary_subject_id = np.zeros(cap, dtype=np.uint64)
        self.lineage_subject_id = np.zeros(cap, dtype=np.uint64)
        self.genotype = np.zeros((cap, self.GENOTYPE_SIZE), dtype=np.float32)
        self.memory = np.zeros((cap, self.MEMORY_SIZE), dtype=np.float32)
        self.harvested_energy_total = np.zeros(cap, dtype=np.float32)
        self.shared_energy_received_total = np.zeros(cap, dtype=np.float32)
        self.next_entity_id = np.uint64(initial + 1)
        self.free_slots = list(range(cap - 1, initial - 1, -1))
        self.free_slot_version = 0

        ids = np.arange(1, initial + 1, dtype=np.uint64)
        idx = np.arange(initial, dtype=np.int32)
        self.entity_id[idx] = ids
        self.lineage_id[idx] = ids
        self.alive[idx] = True
        init_ctx = RandomContext(cfg.run.seed, 0, phase=0, stream=Stream.ENV_RESOURCE)
        self.x[idx] = (uniform01(init_ctx, ids, 0) * cfg.world.width).astype(np.float32)
        self.y[idx] = (uniform01(init_ctx, ids, 1) * cfg.world.height).astype(np.float32)
        self.energy[idx] = np.clip(
            cfg.entities.initial_energy + normal(init_ctx, ids, 0.0, 0.15, 2),
            0.5,
            cfg.entities.max_energy,
        ).astype(np.float32)
        self.integrity[idx] = 1.0
        self.fertility[idx] = 0.25
        for trait in range(self.GENOTYPE_SIZE):
            self.genotype[idx, trait] = np.clip(
                normal(init_ctx, ids, 0.0, 0.25, 10 + trait * 2), -0.8, 0.8
            ).astype(np.float32)

    def sensor_quality(self) -> np.ndarray:
        return np.clip(1.0 + 0.35 * self.genotype[:, 0] + 0.15 * self.information_store, 0.1, 2.0).astype(np.float32)

    def commit_births(
        self,
        plan: BirthAllocationPlan,
        mutation_std: float | None = None,
    ) -> tuple[np.ndarray, np.ndarray]:
        """Validate and commit one preallocated birth plan exactly once."""
        requests = plan.requests
        arrays = (
            requests.source_rows,
            requests.parent_indices,
            requests.parent_entity_ids,
            requests.parent_subject_ids,
            plan.slots,
            plan.offspring_entity_ids,
        )
        values = tuple(np.asarray(value) for value in arrays)
        if any(value.ndim != 1 for value in values):
            raise ValueError("birth allocation arrays must be one-dimensional")
        count = plan.size
        if requests.size != count or any(value.size != count for value in values):
            raise ValueError("birth allocation arrays must have the same length")
        if any(not np.issubdtype(value.dtype, np.integer) for value in values):
            raise ValueError("birth allocation arrays must use integer dtypes")
        if int(requests.tick) < 0:
            raise ValueError("birth allocation tick must be non-negative")
        if count <= 0:
            return np.empty(0, dtype=np.int32), np.empty(0, dtype=np.int32)
        if int(plan.free_pool_version) != self.free_slot_version:
            raise ValueError("birth allocation free-slot pool version is stale")
        parents = values[1].astype(np.int32, copy=False)
        slots = values[4].astype(np.int32, copy=False)
        ids = values[5].astype(np.uint64, copy=False)
        capacity = self.alive.size
        if (
            np.any(parents < 0)
            or np.any(parents >= capacity)
            or np.any(slots < 0)
            or np.any(slots >= capacity)
            or np.unique(slots).size != count
        ):
            raise ValueError("birth allocation contains an invalid parent or slot")
        if not np.all(self.alive[parents]) or np.any(self.alive[slots]):
            raise ValueError("birth allocation does not match current entity occupancy")
        if not np.array_equal(self.entity_id[parents], requests.parent_entity_ids):
            raise ValueError("birth allocation parent entity IDs are stale")
        if not np.array_equal(self.primary_subject_id[parents], requests.parent_subject_ids):
            raise ValueError("birth allocation parent subject IDs are stale")
        expected_slots = np.asarray(self.free_slots[-count:][::-1], dtype=np.int32)
        expected_ids = np.arange(
            int(self.next_entity_id), int(self.next_entity_id) + count, dtype=np.uint64
        )
        if not np.array_equal(slots, expected_slots):
            raise ValueError("birth allocation no longer matches the free-slot pool")
        if not np.array_equal(ids, expected_ids):
            raise ValueError("birth allocation no longer matches the stable-ID counter")
        del self.free_slots[-count:]
        self.free_slot_version += 1
        self.next_entity_id = np.uint64(int(self.next_entity_id) + count)
        self.entity_id[slots] = ids
        self.lineage_id[slots] = self.lineage_id[parents]
        self.alive[slots] = True
        self.age[slots] = 0
        self.integrity[slots] = 1.0
        self.material[slots] = 0.0
        self.information_store[slots] = 0.0
        self.fertility[slots] = 0.05
        self.memory[slots] = 0.0
        self.harvested_energy_total[slots] = 0.0
        self.shared_energy_received_total[slots] = 0.0
        self.primary_subject_id[slots] = 0
        self.lineage_subject_id[slots] = 0

        tick = int(requests.tick)
        ctx = RandomContext(self.cfg.run.seed, tick, phase=70, stream=Stream.REPRODUCTION)
        self.x[slots] = self.x[parents] + normal(ctx, ids, 0.0, 0.35, 0).astype(np.float32)
        self.y[slots] = self.y[parents] + normal(ctx, ids, 0.0, 0.35, 2).astype(np.float32)
        if self.cfg.world.periodic:
            self.x[slots] %= self.cfg.world.width
            self.y[slots] %= self.cfg.world.height
        else:
            self.x[slots] = np.clip(self.x[slots], 0.0, self.cfg.world.width)
            self.y[slots] = np.clip(self.y[slots], 0.0, self.cfg.world.height)
        self.vx[slots] = 0.0
        self.vy[slots] = 0.0
        self.energy[slots] = self.cfg.entities.reproduction_cost * 0.45

        mut_ctx = RandomContext(self.cfg.run.seed, tick, phase=71, stream=Stream.MUTATION)
        for trait in range(self.GENOTYPE_SIZE):
            mutation = normal(
                mut_ctx,
                ids,
                0.0,
                self.cfg.policy.mutation_std if mutation_std is None else mutation_std,
                draw_index=trait * 2,
            )
            self.genotype[slots, trait] = np.clip(
                self.genotype[parents, trait] + mutation, -1.5, 1.5
            ).astype(np.float32)
        return parents, slots

    def commit_deaths(self, plan: DeathEventPlan) -> np.ndarray:
        """Commit canonical death events and reclaim their slots at phase end."""
        indices = np.asarray(plan.entity_indices, dtype=np.int32)
        arrays = (
            indices,
            plan.entity_ids,
            plan.primary_subject_ids,
            plan.cause_code,
            plan.final_energy,
            plan.final_integrity,
        )
        if any(np.asarray(value).ndim != 1 for value in arrays):
            raise ValueError("death event arrays must be one-dimensional")
        if len({np.asarray(value).size for value in arrays}) != 1:
            raise ValueError("death event arrays must have the same length")
        if indices.size == 0:
            return indices
        if (
            np.any(indices < 0)
            or np.any(indices >= self.alive.size)
            or np.any(indices[1:] <= indices[:-1])
            or not np.all(self.alive[indices])
        ):
            raise ValueError("death event plan does not match current occupancy")
        if not np.array_equal(self.entity_id[indices], plan.entity_ids):
            raise ValueError("death event entity IDs are stale")
        if not np.array_equal(self.primary_subject_id[indices], plan.primary_subject_ids):
            raise ValueError("death event subject IDs are stale")
        cause = np.asarray(plan.cause_code, dtype=np.uint8)
        expected_cause = (
            (self.energy[indices] <= 0.0).astype(np.uint8)
            * int(DeathCause.ENERGY_DEPLETED)
            | (self.integrity[indices] <= 0.0).astype(np.uint8)
            * int(DeathCause.INTEGRITY_DEPLETED)
            | (self.age[indices] >= self.cfg.entities.max_age).astype(np.uint8)
            * int(DeathCause.MAX_AGE)
        ).astype(np.uint8)
        if not np.array_equal(cause, expected_cause) or np.any(cause == 0):
            raise ValueError("death event cause does not match current entity state")
        if not np.array_equal(self.energy[indices], plan.final_energy) or not np.array_equal(
            self.integrity[indices], plan.final_integrity
        ):
            raise ValueError("death event final state is stale")
        self.alive[indices] = False
        self.free_slots.extend(indices.tolist())
        self.free_slot_version += 1
        self.entity_id[indices] = 0
        self.vx[indices] = 0.0
        self.vy[indices] = 0.0
        return indices


class Simulation:
    def __init__(
        self,
        cfg: SimulationConfig,
        output_dir: str | Path,
        *,
        backend: str = "cpu",
        conflict_resolver: ActionConflictResolver | None = None,
        control_arbiter: ControlArbiter | None = None,
    ) -> None:
        self.cfg = cfg
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.entities = EntityState(cfg)
        self.environment = Environment(cfg)
        self.information = InformationSystem(cfg)
        # MVP channels flush every tick, exactly preserving current field
        # timing.  Longer periods are an explicit future model choice, not a
        # dense zero-column performance shortcut.
        self.signal_scheduler = SignalEmissionScheduler(
            self.information.CHANNELS,
            cfg.information.signal_flush_periods,
        )
        self.spatial = SpatialIndex(
            cfg.world.grid_x,
            cfg.world.grid_y,
            cfg.world.width,
            cfg.world.height,
            cfg.world.periodic,
        )
        requested_backend = backend.strip().lower()
        if requested_backend == "cpu":
            self.gpu_runtime: HybridGpuRuntime | None = None
            self.execution_backend = "cpu"
        elif requested_backend in {"gpu", "auto"}:
            try:
                self.gpu_runtime = HybridGpuRuntime(cfg, backend="gpu")
            except BackendUnavailableError:
                if requested_backend == "gpu":
                    raise
                self.gpu_runtime = None
            self.execution_backend = "gpu" if self.gpu_runtime is not None else "cpu"
        else:
            raise ValueError("backend must be one of: 'cpu', 'gpu', or 'auto'")
        if self.gpu_runtime is not None:
            self.gpu_runtime.sync_from_host(self.environment, self.information)
        self.social = SocialSystem(cfg, cfg.world.max_entities)
        self.subjects = CandidateSubjectGraph(cfg.world.max_entities)
        initial = np.flatnonzero(self.entities.alive).astype(np.int32)
        body_subjects, lineage_subjects = self.subjects.register_bodies(
            initial, self.entities.lineage_id, tick=0
        )
        self.entities.primary_subject_id[initial] = body_subjects
        self.entities.lineage_subject_id[initial] = lineage_subjects
        self.policy = ParametricPolicy(cfg)
        self.metrics = MetricsWriter(self.output_dir)
        self.tick = 0
        self.last_group_summary = GroupSummary(
            np.empty(0, dtype=np.uint64), np.empty(0, dtype=np.int32), np.empty(0, dtype=np.float32)
        )
        self.total_births = 0
        self.total_deaths = 0
        self.action_counts = np.zeros(len(Action), dtype=np.int64)
        self.last_intents: ActionIntentBatch | None = None
        self.last_resolutions: ActionResolutionBatch | None = None
        self.last_birth_allocation = empty_birth_allocation_plan(0)
        self.last_death_events = empty_death_event_plan(0)
        self.conflict_resolver = conflict_resolver
        if self.conflict_resolver is None:
            self.conflict_resolver = (
                GpuActionConflictResolver(cfg)
                if self.gpu_runtime is not None and cfg.run.gpu_harvest_conflict_planner
                else DeterministicActionConflictResolver(cfg)
            )
        if isinstance(self.conflict_resolver, GpuActionConflictResolver):
            if self.gpu_runtime is None:
                raise ValueError("GpuActionConflictResolver requires Simulation(..., backend='gpu')")
            self.conflict_resolver.bind_harvest_planner(self.gpu_runtime)
        self.control_arbiter = control_arbiter if control_arbiter is not None else (
            HeuristicSocialGuidanceArbiter()
            if cfg.control.heuristic_social_guidance
            else SingleProposalControlArbiter()
        )
        self.heuristic_guidance_actions = 0
        self.social_control_enabled = True
        self.social_connections_enabled = True
        self.direct_messages_enabled = True
        self.freeze_genotype = False
        # Interactive ``step()`` calls keep host field mirrors current.  A
        # monolithic ``run()`` can defer that costly device->host copy until
        # completion because every intervening field consumer is device-side.
        self._defer_gpu_field_sync = False
        self._trajectory_file = None
        if cfg.run.trajectory_subject_ids:
            self._trajectory_file = (self.output_dir / "trajectory.jsonl").open("w", encoding="utf-8")

    def clone(self, output_dir: str | Path) -> "Simulation":
        """Clone a snapshot for paired counterfactual runs.

        Metrics and trajectory writers are intentionally recreated for the
        branch.  All mutable world state, including delayed messages and the
        subject graph, is deep-copied before the intervention is applied.
        """
        if self.gpu_runtime is not None and self._defer_gpu_field_sync:
            self.gpu_runtime.sync_to_host(self.environment, self.information)
        branch = Simulation(
            self.cfg,
            output_dir,
            backend=self.execution_backend,
            conflict_resolver=copy.deepcopy(self.conflict_resolver),
            control_arbiter=copy.deepcopy(self.control_arbiter),
        )
        branch.entities = copy.deepcopy(self.entities)
        branch.environment = copy.deepcopy(self.environment)
        branch.information = copy.deepcopy(self.information)
        branch.signal_scheduler = copy.deepcopy(self.signal_scheduler)
        branch.spatial = copy.deepcopy(self.spatial)
        branch.social = copy.deepcopy(self.social)
        branch.subjects = self.subjects.clone()
        branch.tick = self.tick
        branch.last_group_summary = copy.deepcopy(self.last_group_summary)
        branch.total_births = self.total_births
        branch.total_deaths = self.total_deaths
        branch.action_counts = self.action_counts.copy()
        branch.last_birth_allocation = copy.deepcopy(self.last_birth_allocation)
        branch.last_death_events = copy.deepcopy(self.last_death_events)
        branch.heuristic_guidance_actions = self.heuristic_guidance_actions
        branch.social_control_enabled = self.social_control_enabled
        branch.social_connections_enabled = self.social_connections_enabled
        branch.direct_messages_enabled = self.direct_messages_enabled
        branch.freeze_genotype = self.freeze_genotype
        if branch.gpu_runtime is not None:
            branch.gpu_runtime.sync_from_host(branch.environment, branch.information)
        return branch

    def apply_intervention(self, intervention: str) -> None:
        """Apply one documented intervention without changing random streams."""
        normalized = intervention.strip().lower().replace("_", "-")
        active = np.flatnonzero(self.entities.alive).astype(np.int32)
        if normalized in {"disable-social-control", "social-control-off"}:
            self.social_control_enabled = False
        elif normalized in {"cut-social-connections", "cut-social"}:
            self.social_connections_enabled = False
            self.direct_messages_enabled = False
            self.social.reset_entities(active)
            if self.gpu_runtime is not None:
                self.gpu_runtime.mark_social_state_dirty()
            self.information.pending_messages.clear()
        elif normalized == "shuffle-memory":
            ids = self.entities.entity_id[active]
            ctx = RandomContext(self.cfg.run.seed, self.tick, phase=90, stream=Stream.CAUSAL_INTERVENTION)
            order = np.argsort(uniform01(ctx, ids, draw_index=0), kind="stable")
            self.entities.memory[active] = self.entities.memory[active[order]].copy()
        elif normalized in {"freeze-genotype", "freeze-genetic-expression"}:
            self.freeze_genotype = True
        else:
            raise ValueError(
                "Unknown intervention. Expected disable-social-control, cut-social-connections, "
                "shuffle-memory, or freeze-genotype."
            )

    def _record_trajectories(
        self,
        intents: ActionIntentBatch,
        resolutions: ActionResolutionBatch,
        logits: np.ndarray,
    ) -> None:
        if self._trajectory_file is None:
            return
        tracked = {int(subject_id) for subject_id in self.cfg.run.trajectory_subject_ids}
        for row, entity_id in enumerate(intents.carrier_id.tolist()):
            if entity_id not in tracked:
                continue
            record = {
                "tick": self.tick,
                "entity_id": entity_id,
                "subject_id": int(self.entities.primary_subject_id[intents.carrier_index[row]]),
                "intent_id": int(intents.intent_id[row]),
                "action": Action(intents.action[row]).name,
                "sample_probability": float(intents.sampled_probability[row]),
                "logits": [float(value) for value in logits[row]],
                "success": bool(resolutions.success[row]),
                "failure_reason": FailureReason(resolutions.failure_reason[row]).name,
                "resource_delta": [float(value) for value in resolutions.resource_delta[row]],
            }
            if intents.proposer_subject_id is not None:
                record["proposer_subject_id"] = int(intents.proposer_subject_id[row])
            if intents.controller_kind is not None:
                record["controller_kind"] = ControllerKind(intents.controller_kind[row]).name
            if intents.contributor_subject_ids is not None:
                record["contributor_subject_ids"] = [
                    int(subject_id) for subject_id in intents.contributor_subject_ids[row]
                ]
            if intents.contribution_weights is not None:
                record["contribution_weights"] = [
                    float(weight) for weight in intents.contribution_weights[row]
                ]
            if intents.heuristic_control is not None:
                record["heuristic_control"] = bool(intents.heuristic_control[row])
            self._trajectory_file.write(json.dumps(record, ensure_ascii=False) + "\n")
        self._trajectory_file.flush()

    def _commit_shares(self, share: ShareResolution) -> float:
        """Apply one self-contained share plan without consulting last-step state."""
        if share.rows.size == 0:
            return 0.0
        committed = share.success & share.valid_target & (share.amounts > 1e-8)
        if np.any(committed):
            owners = share.owner_indices[committed]
            targets = share.target_indices[committed]
            amounts = share.amounts[committed]
            np.add.at(self.entities.energy, owners, -amounts)
            np.add.at(self.entities.energy, targets, amounts)
            np.add.at(self.entities.shared_energy_received_total, targets, amounts)
        if self.social_connections_enabled:
            self.social.apply_relation_updates(share.relation_updates)
        return float(share.amounts[committed].sum())

    def _emit_signals(
        self,
        actors: np.ndarray,
        cells: np.ndarray,
        local_resources: np.ndarray,
        target_indices: np.ndarray,
    ) -> tuple[SignalEmissionPlan, int]:
        if actors.size == 0:
            return SignalEmissionPlan(()), 0
        ent = self.entities
        actor_cells = cells
        strengths_resource = np.clip(local_resources[:, 0], 0.0, 2.0) * 0.15
        hazard = (
            self.gpu_runtime.hazard_for_cells(actor_cells)
            if self.gpu_runtime is not None
            else self.environment.hazard.reshape(-1)[actor_cells]
        )
        strengths_danger = hazard * 0.15
        group_member = self.social.group_id[actors] != 0
        strengths_social = group_member.astype(np.float32) * 0.12
        signal_plan = SignalEmissionPlan(
            batches=(
                SignalEmissionBatch(0, actor_cells, strengths_resource, emitter="actor-resource"),
                SignalEmissionBatch(1, actor_cells, strengths_danger, emitter="actor-danger"),
                SignalEmissionBatch(2, actor_cells, strengths_social, emitter="actor-social"),
            )
        )
        ent.energy[actors] -= self.cfg.entities.signal_cost
        valid_target = (target_indices >= 0) & ent.alive[target_indices]
        safe_targets = np.where(valid_target, target_indices, 0)
        payloads = np.stack(
            [local_resources[:, 0], hazard, group_member.astype(np.float32)], axis=1
        ).astype(np.float32)
        direct_messages = 0
        if self.direct_messages_enabled:
            direct_messages = self.information.emit_direct(
                ent.entity_id[actors],
                ent.entity_id[safe_targets] * valid_target.astype(np.uint64),
                payloads,
                np.full(actors.size, 1.0, dtype=np.float32),
                self.cfg.run.seed,
                self.tick,
            )
        return signal_plan, direct_messages

    def _flush_signal_emissions(self, plan: SignalEmissionPlan | None = None) -> None:
        """Commit channel batches whose modeled delivery cadence is due now."""
        # ``self.tick`` is zero-based during a step.  Flush against the
        # completed one-based tick so a period of three delivers after steps
        # 3, 6, ... rather than treating construction tick zero as a flush.
        due_plan = self.signal_scheduler.submit(plan or SignalEmissionPlan(()), self.tick + 1)
        if not due_plan.batches:
            return
        if self.gpu_runtime is None:
            self.information.emit_plan(due_plan)
        else:
            self.gpu_runtime.emit_plan(due_plan)

    def _checkpoint(self) -> None:
        active = np.flatnonzero(self.entities.alive)
        path = self.output_dir / f"checkpoint_{self.tick:08d}.npz"
        np.savez_compressed(
            path,
            tick=np.asarray([self.tick], dtype=np.uint64),
            entity_id=self.entities.entity_id[active],
            x=self.entities.x[active],
            y=self.entities.y[active],
            energy=self.entities.energy[active],
            integrity=self.entities.integrity[active],
            lineage_id=self.entities.lineage_id[active],
            primary_subject_id=self.entities.primary_subject_id[active],
            lineage_subject_id=self.entities.lineage_subject_id[active],
            group_id=self.social.group_id[active],
            genotype=self.entities.genotype[active],
        )

    def step(self) -> StepStats:
        cfg = self.cfg
        ent = self.entities
        stats = StepStats()
        if self.gpu_runtime is None:
            phase_started = time.perf_counter()
            self.environment.update(self.tick)
            self.information.propagate()
            stats.environment_seconds = time.perf_counter() - phase_started

            phase_started = time.perf_counter()
            active = self.spatial.build(ent.x, ent.y, ent.alive)
            stats.spatial_seconds = time.perf_counter() - phase_started
            if active.size == 0:
                return stats

            phase_started = time.perf_counter()
            cells = self.spatial.entity_cells[active]
            partners = self.spatial.sample_partners(
                active,
                ent.entity_id,
                cfg.run.seed,
                self.tick,
                cfg.policy.partner_samples,
            )
            local_resources = self.environment.cell_values(cells)
            info = self.information.observe(
                active=active,
                stable_ids=ent.entity_id,
                cell_ids=cells,
                partners=partners,
                energy=ent.energy,
                group_id=self.social.group_id,
                sensor_quality=ent.sensor_quality(),
                run_seed=cfg.run.seed,
                tick=self.tick,
            )
            resource_gradient, danger_gradient = self.environment.gradients_for_entities(
                self.spatial.entity_cells, ent.alive.size
            )
            stats.observation_seconds = time.perf_counter() - phase_started

            phase_started = time.perf_counter()
            if self.social_control_enabled:
                group_direction = (self.social.group_dir_x, self.social.group_dir_y)
            else:
                group_direction = (np.zeros_like(self.social.group_dir_x), np.zeros_like(self.social.group_dir_y))
            decision = self.policy.decide(
                active=active,
                stable_ids=ent.entity_id,
                energy=ent.energy,
                integrity=ent.integrity,
                fertility=ent.fertility,
                genotype=ent.genotype,
                memory=ent.memory,
                local_resources=local_resources,
                resource_gradient=resource_gradient,
                danger_gradient=danger_gradient,
                group_direction=group_direction,
                partners=partners,
                info=info,
                run_seed=cfg.run.seed,
                tick=self.tick,
            )
            stats.policy_seconds = time.perf_counter() - phase_started
        else:
            phase_started = time.perf_counter()
            self.gpu_runtime.update_fields(self.tick)
            self.gpu_runtime.backend.synchronize()
            stats.environment_seconds = time.perf_counter() - phase_started
            prepared = self.gpu_runtime.prepare(
                entity=ent,
                social=self.social,
                information=self.information,
                policy=self.policy,
                social_control_enabled=self.social_control_enabled,
                run_seed=cfg.run.seed,
                tick=self.tick,
                retain_logits=self._trajectory_file is not None,
                need_host_resource_gradient=(
                    self.social_connections_enabled and self.tick % cfg.social.group_update_period == 0
                ),
            )
            active = prepared.active
            if active.size == 0:
                if not self._defer_gpu_field_sync:
                    self.gpu_runtime.sync_to_host(self.environment, self.information)
                return stats
            cells = prepared.cells
            local_resources = prepared.local_resources
            resource_gradient = prepared.resource_gradient
            info = prepared.information
            decision = prepared.decision
            stats.spatial_seconds = prepared.spatial_seconds
            stats.observation_seconds = prepared.observation_seconds
            stats.policy_seconds = prepared.policy_seconds
        body_proposal = body_control_proposal(
            active,
            ent.primary_subject_id[active],
            decision,
            self.tick,
        )
        proposals = (body_proposal,)
        if cfg.control.heuristic_social_guidance:
            if self.social_control_enabled:
                social_subject_id = self.subjects.social_subject_ids(self.social.group_id[active])
                group_direction = (
                    self.social.group_dir_x[active],
                    self.social.group_dir_y[active],
                )
            else:
                social_subject_id = np.zeros(active.size, dtype=np.uint64)
                group_direction = (
                    np.zeros(active.size, dtype=np.float32),
                    np.zeros(active.size, dtype=np.float32),
                )
            proposals = (
                body_proposal,
                social_guidance_control_proposal(
                    body_proposal,
                    social_subject_id,
                    group_direction,
                    cfg.control.heuristic_social_guidance_weight,
                ),
            )
        arbitration = self.control_arbiter.arbitrate(proposals)
        decision = arbitration.decision
        if arbitration.heuristic_applied is not None:
            stats.heuristic_guidance_actions = int(np.count_nonzero(arbitration.heuristic_applied))
            self.heuristic_guidance_actions += stats.heuristic_guidance_actions
        self.action_counts += np.bincount(decision.action, minlength=len(Action))
        stats.action_entropy = float(decision.entropy.mean())
        stats.signal_detection_rate = float(info.signal_mask.mean())
        stats.partner_detection_rate = float(info.partner_mask.mean()) if info.partner_mask.size else 0.0
        grouped = self.social.group_id[active] != 0
        stats.move_social_fraction = float(
            np.mean(decision.action[grouped] == Action.MOVE_SOCIAL) if np.any(grouped) else 0.0
        )

        # ----- Intent and conflict phases: no world state is changed here. -----
        phase_started = time.perf_counter()
        intents = build_intents(
            active,
            ent.entity_id,
            decision,
            self.tick,
            proposer_subject_id=arbitration.proposer_subject_id,
            controller_kind=arbitration.controller_kind,
            contributor_subject_ids=arbitration.contributor_subject_ids,
            contribution_weights=arbitration.contribution_weights,
            heuristic_control=arbitration.heuristic_applied,
        )
        snapshot = ActionResolutionSnapshot(
            active=active,
            cells=cells,
            entity_id=ent.entity_id,
            alive=ent.alive,
            energy=ent.energy,
            fertility=ent.fertility,
            primary_subject_id=ent.primary_subject_id,
            free_slot_count=len(ent.free_slots),
        )
        harvest_allocator = (
            self.gpu_runtime.resolve_harvest
            if self.gpu_runtime is not None
            else self.environment.resolve_harvest
        )
        resolution_plan = self.conflict_resolver.resolve(snapshot, intents, harvest_allocator)
        resolutions = resolution_plan.resolutions
        harvest_rows = resolution_plan.harvest_rows
        harvest_cells = resolution_plan.harvest_cells
        gathered = resolution_plan.gathered
        share = resolution_plan.share
        signal_rows = resolution_plan.signal_rows
        birth_requests = resolution_plan.birth_requests
        stats.conflict_seconds = time.perf_counter() - phase_started
        self.last_intents = intents
        self.last_resolutions = resolutions

        # ----- World commit phase: only resolved intents may mutate state. -----
        movable_actions = np.isin(intents.action, [Action.MOVE_RESOURCE, Action.MOVE_SOCIAL, Action.FLEE])
        movable_rows = np.flatnonzero(movable_actions & resolutions.success)
        movers = intents.carrier_index[movable_rows]
        speed = (0.35 + 0.10 * np.clip(ent.genotype[movers, 5], -1.0, 1.0)).astype(np.float32)
        ent.vx[movers] = intents.direction_x[movable_rows] * speed
        ent.vy[movers] = intents.direction_y[movable_rows] * speed
        ent.x[movers] += ent.vx[movers]
        ent.y[movers] += ent.vy[movers]
        if cfg.world.periodic:
            ent.x[movers] %= cfg.world.width
            ent.y[movers] %= cfg.world.height
        else:
            ent.x[movers] = np.clip(ent.x[movers], 0.0, cfg.world.width)
            ent.y[movers] = np.clip(ent.y[movers], 0.0, cfg.world.height)
        non_movers = active[~np.isin(active, movers)]
        ent.vx[non_movers] = 0.0
        ent.vy[non_movers] = 0.0

        if harvest_rows.size:
            if self.gpu_runtime is not None:
                self.gpu_runtime.commit_harvest(harvest_cells, gathered)
            else:
                self.environment.commit_harvest(harvest_cells, gathered)
            harvesters = intents.carrier_index[harvest_rows]
            ent.energy[harvesters] = np.minimum(ent.energy[harvesters] + gathered[:, 0], cfg.entities.max_energy)
            ent.integrity[harvesters] = np.minimum(ent.integrity[harvesters] + gathered[:, 1] * 0.05, 1.0)
            ent.information_store[harvesters] = np.minimum(ent.information_store[harvesters] + gathered[:, 2], 3.0)
            ent.fertility[harvesters] = np.minimum(ent.fertility[harvesters] + gathered[:, 3], 3.0)
            ent.harvested_energy_total[harvesters] += gathered[:, 0]
            stats.harvested_energy = float(gathered[:, 0].sum())

        stats.shared_energy = self._commit_shares(share)

        signal_plan = SignalEmissionPlan(())
        if signal_rows.size:
            signal_actors = intents.carrier_index[signal_rows]
            signal_observation_rows = np.searchsorted(active, signal_actors)
            signal_plan, stats.direct_messages = self._emit_signals(
                signal_actors,
                cells[signal_observation_rows],
                local_resources[signal_observation_rows],
                intents.target_index[signal_rows],
            )
            stats.signals = int(signal_actors.size)
        self._flush_signal_emissions(signal_plan)

        birth_allocation = plan_birth_allocations(
            birth_requests,
            ent.free_slots,
            int(ent.next_entity_id),
            ent.free_slot_version,
        )
        self.last_birth_allocation = birth_allocation
        if birth_allocation.size:
            accepted_parents, newborns = ent.commit_births(
                birth_allocation,
                mutation_std=0.0 if self.freeze_genotype else None,
            )
            if newborns.size:
                self.social.reset_entities(newborns)
                body_subjects, lineage_subjects = self.subjects.register_bodies(
                    newborns, ent.lineage_id, self.tick
                )
                ent.primary_subject_id[newborns] = body_subjects
                ent.lineage_subject_id[newborns] = lineage_subjects
                ent.energy[accepted_parents] -= cfg.entities.reproduction_cost
                ent.fertility[accepted_parents] -= 0.5
                if self.gpu_runtime is not None:
                    self.gpu_runtime.mark_entity_static_dirty()
                    self.gpu_runtime.mark_social_state_dirty()
                stats.births = int(newborns.size)
                self.total_births += stats.births

        # Existence costs and environmental damage.
        current_active = np.flatnonzero(ent.alive).astype(np.int32)
        current_cells = self.spatial.cell_ids(ent.x[current_active], ent.y[current_active])
        hazard = (
            self.gpu_runtime.hazard_for_cells(current_cells)
            if self.gpu_runtime is not None
            else self.environment.hazard.reshape(-1)[current_cells]
        )
        moved_now = np.zeros(ent.alive.size, dtype=bool)
        moved_now[movers] = True
        cost = cfg.entities.maintenance_cost + moved_now[current_active] * cfg.entities.movement_cost
        ent.energy[current_active] -= cost.astype(np.float32)
        ent.integrity[current_active] -= (hazard * 0.0015).astype(np.float32)
        starving = ent.energy[current_active] < 0.0
        ent.integrity[current_active[starving]] += ent.energy[current_active[starving]] * 0.05
        ent.energy[current_active] = np.maximum(ent.energy[current_active], 0.0)
        ent.age[current_active] += 1
        ent.information_store[current_active] *= 0.999
        ent.fertility[current_active] = np.maximum(ent.fertility[current_active] - 0.0005, 0.0)

        self.policy.update_memory(active, ent.memory, local_resources, info)
        death_events = plan_death_events(
            active=current_active,
            entity_ids=ent.entity_id,
            primary_subject_ids=ent.primary_subject_id,
            energy=ent.energy,
            integrity=ent.integrity,
            age=ent.age,
            max_age=cfg.entities.max_age,
            tick=self.tick,
        )
        self.last_death_events = death_events
        dead = death_events.entity_indices
        if dead.size:
            self.subjects.mark_dead(dead, self.tick)
            ent.commit_deaths(death_events)
            self.social.group_id[dead] = 0
            self.social.group_age[dead] = 0
            if self.gpu_runtime is not None:
                self.gpu_runtime.mark_entity_static_dirty()
                self.gpu_runtime.mark_social_state_dirty()
            stats.deaths = int(dead.size)
            self.total_deaths += stats.deaths
        # With no death this tick no new stale relation target can exist, so
        # skip the otherwise full fixed-slot relationship-table scan.
        if dead.size:
            self.social.clear_dead_targets(ent.alive)

        # Candidate social subjects are updated at a slower timescale.
        phase_started = time.perf_counter()
        if self.tick % cfg.social.group_update_period == 0:
            if self.social_connections_enabled:
                if resource_gradient is None:
                    raise RuntimeError("GPU step omitted required resource gradients")
                self.last_group_summary = self.social.update_groups(
                    ent.alive,
                    ent.entity_id,
                    ent.energy,
                    resource_gradient[0],
                    resource_gradient[1],
                    self.tick,
                )
            else:
                self.social.group_id.fill(0)
                self.last_group_summary = GroupSummary(
                    np.empty(0, dtype=np.uint64), np.empty(0, dtype=np.int32), np.empty(0, dtype=np.float32)
                )
            self.subjects.update_groups(ent.alive, self.social.group_id, self.tick)
            if self.gpu_runtime is not None:
                self.gpu_runtime.mark_social_state_dirty()
        stats.group_count = int(self.last_group_summary.group_ids.size)
        stats.mean_group_size = float(
            self.last_group_summary.counts.mean() if self.last_group_summary.counts.size else 0.0
        )
        stats.graph_seconds = time.perf_counter() - phase_started
        self._record_trajectories(intents, resolutions, decision.logits)
        if self.gpu_runtime is not None and not self._defer_gpu_field_sync:
            self.gpu_runtime.sync_to_host(self.environment, self.information)
        self.tick += 1
        return stats

    def metric_row(
        self,
        stats: StepStats,
        elapsed: float,
        *,
        wall_elapsed: float = 0.0,
        window_seconds: float = 0.0,
        window_ticks: int = 1,
    ) -> dict[str, float | int]:
        ent = self.entities
        active = np.flatnonzero(ent.alive)
        alive_count = active.size
        if alive_count:
            mean_energy = float(ent.energy[active].mean())
            mean_integrity = float(ent.integrity[active].mean())
            mean_age = float(ent.age[active].mean())
            social_dependency = float(
                np.mean(
                    ent.shared_energy_received_total[active]
                    / np.maximum(
                        ent.shared_energy_received_total[active] + ent.harvested_energy_total[active], 1e-6
                    )
                )
            )
            lineage_count = int(np.unique(ent.lineage_id[active]).size)
            grouped_fraction = float(np.mean(self.social.group_id[active] != 0))
        else:
            mean_energy = mean_integrity = mean_age = social_dependency = grouped_fraction = 0.0
            lineage_count = 0
        row: dict[str, float | int] = {
            "tick": self.tick,
            "alive": alive_count,
            "births_step": stats.births,
            "deaths_step": stats.deaths,
            "births_total": self.total_births,
            "deaths_total": self.total_deaths,
            "mean_energy": mean_energy,
            "mean_integrity": mean_integrity,
            "mean_age": mean_age,
            "lineages": lineage_count,
            "groups": stats.group_count,
            "mean_group_size": stats.mean_group_size,
            "grouped_fraction": grouped_fraction,
            "social_dependency_proxy": social_dependency,
            "move_social_fraction": stats.move_social_fraction,
            "heuristic_guidance_actions_step": stats.heuristic_guidance_actions,
            "harvested_energy_step": stats.harvested_energy,
            "shared_energy_step": stats.shared_energy,
            "signals_step": stats.signals,
            "direct_messages_step": stats.direct_messages,
            "action_entropy": stats.action_entropy,
            "signal_detection_rate": stats.signal_detection_rate,
            "partner_detection_rate": stats.partner_detection_rate,
            "environment_seconds": stats.environment_seconds,
            "spatial_seconds": stats.spatial_seconds,
            "observation_seconds": stats.observation_seconds,
            "policy_seconds": stats.policy_seconds,
            "conflict_seconds": stats.conflict_seconds,
            "graph_seconds": stats.graph_seconds,
            "step_seconds": elapsed,
            "wall_elapsed_seconds": wall_elapsed,
            "window_seconds": window_seconds,
            "window_ticks": window_ticks,
            "window_seconds_per_tick": window_seconds / max(window_ticks, 1),
        }
        row.update(self.subjects.summary())
        return row

    def run(self) -> dict[str, float | int]:
        started = time.perf_counter()
        window_started = started
        window_start_tick = 0
        final_row: dict[str, float | int] = {}
        last_stats: StepStats | None = None
        last_step_seconds = 0.0
        previous_defer_gpu_field_sync = self._defer_gpu_field_sync
        if self.gpu_runtime is not None:
            self._defer_gpu_field_sync = True
        try:
            for _ in range(self.cfg.run.ticks):
                step_started = time.perf_counter()
                stats = self.step()
                elapsed = time.perf_counter() - step_started
                last_stats = stats
                last_step_seconds = elapsed
                if self.tick % self.cfg.run.metrics_period == 0 or self.tick == 1:
                    reported_at = time.perf_counter()
                    window_ticks = self.tick - window_start_tick
                    window_seconds = reported_at - window_started
                    final_row = self.metric_row(
                        stats,
                        elapsed,
                        wall_elapsed=reported_at - started,
                        window_seconds=window_seconds,
                        window_ticks=window_ticks,
                    )
                    self.metrics.write(final_row)
                    print(
                        f"tick={self.tick:7d} alive={final_row['alive']:7d} "
                        f"groups={final_row['groups']:5d} E={final_row['mean_energy']:.3f} "
                        f"step={elapsed:.3f}s window_avg={final_row['window_seconds_per_tick']:.3f}s "
                        f"wall={final_row['wall_elapsed_seconds']:.1f}s"
                    )
                    # Start the next window before output/checkpoint work so
                    # its average includes the non-step costs users observe.
                    window_started = reported_at
                    window_start_tick = self.tick
                if self.tick % self.cfg.run.checkpoint_period == 0:
                    self._checkpoint()
                if not np.any(self.entities.alive):
                    break
            if self.tick and (not final_row or int(final_row["tick"]) != self.tick):
                reported_at = time.perf_counter()
                window_ticks = self.tick - window_start_tick
                final_row = self.metric_row(
                    last_stats if last_stats is not None else StepStats(),
                    last_step_seconds,
                    wall_elapsed=reported_at - started,
                    window_seconds=reported_at - window_started,
                    window_ticks=window_ticks,
                )
                self.metrics.write(final_row)
                print(
                    f"tick={self.tick:7d} alive={final_row['alive']:7d} "
                    f"groups={final_row['groups']:5d} E={final_row['mean_energy']:.3f} "
                    f"step={last_step_seconds:.3f}s window_avg={final_row['window_seconds_per_tick']:.3f}s "
                    f"wall={final_row['wall_elapsed_seconds']:.1f}s"
                )
        finally:
            if self.gpu_runtime is not None:
                self.gpu_runtime.sync_to_host(self.environment, self.information)
            self._defer_gpu_field_sync = previous_defer_gpu_field_sync
            self.metrics.close()
            if self._trajectory_file is not None:
                self._trajectory_file.close()
        metadata = {
            "version": __version__,
            "execution_backend": self.execution_backend,
            "ticks_completed": self.tick,
            "wall_seconds": time.perf_counter() - started,
            "final": final_row,
            "action_counts": {action.name: int(self.action_counts[action]) for action in Action},
            "subject_graph": self.subjects.summary(),
            "interventions": {
                "social_control_enabled": self.social_control_enabled,
                "social_connections_enabled": self.social_connections_enabled,
                "direct_messages_enabled": self.direct_messages_enabled,
                "freeze_genotype": self.freeze_genotype,
            },
            "control": {
                "arbiter": type(self.control_arbiter).__name__,
                "heuristic_social_guidance_enabled": self.cfg.control.heuristic_social_guidance,
                "heuristic_social_guidance_weight": self.cfg.control.heuristic_social_guidance_weight,
                "heuristic_guidance_actions": self.heuristic_guidance_actions,
            },
        }
        (self.output_dir / "run_metadata.json").write_text(
            json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        return final_row
