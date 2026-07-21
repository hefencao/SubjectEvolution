from __future__ import annotations

from dataclasses import dataclass
import copy
import json
from pathlib import Path
import time
import numpy as np

from .config import SimulationConfig
from .environment import Environment
from .information import InformationSystem
from .intents import (
    ActionIntentBatch,
    ActionResolutionBatch,
    FailureReason,
    action_rows,
    build_intents,
    empty_resolutions,
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

    def allocate_births(
        self,
        parent_indices: np.ndarray,
        tick: int,
        mutation_std: float | None = None,
    ) -> tuple[np.ndarray, np.ndarray]:
        count = min(parent_indices.size, len(self.free_slots))
        if count <= 0:
            return np.empty(0, dtype=np.int32), np.empty(0, dtype=np.int32)
        parents = parent_indices[:count].astype(np.int32)
        slots = np.asarray([self.free_slots.pop() for _ in range(count)], dtype=np.int32)
        ids = np.arange(int(self.next_entity_id), int(self.next_entity_id) + count, dtype=np.uint64)
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

    def kill(self, indices: np.ndarray) -> None:
        for idx in indices.tolist():
            if self.alive[idx]:
                self.alive[idx] = False
                self.free_slots.append(int(idx))
        self.entity_id[indices] = 0
        self.vx[indices] = 0.0
        self.vy[indices] = 0.0


class Simulation:
    def __init__(self, cfg: SimulationConfig, output_dir: str | Path) -> None:
        self.cfg = cfg
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.entities = EntityState(cfg)
        self.environment = Environment(cfg)
        self.information = InformationSystem(cfg)
        self.spatial = SpatialIndex(
            cfg.world.grid_x,
            cfg.world.grid_y,
            cfg.world.width,
            cfg.world.height,
            cfg.world.periodic,
        )
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
        self.social_control_enabled = True
        self.social_connections_enabled = True
        self.direct_messages_enabled = True
        self.freeze_genotype = False
        self._trajectory_file = None
        if cfg.run.trajectory_subject_ids:
            self._trajectory_file = (self.output_dir / "trajectory.jsonl").open("w", encoding="utf-8")

    def clone(self, output_dir: str | Path) -> "Simulation":
        """Clone a snapshot for paired counterfactual runs.

        Metrics and trajectory writers are intentionally recreated for the
        branch.  All mutable world state, including delayed messages and the
        subject graph, is deep-copied before the intervention is applied.
        """
        branch = Simulation(self.cfg, output_dir)
        branch.entities = copy.deepcopy(self.entities)
        branch.environment = copy.deepcopy(self.environment)
        branch.information = copy.deepcopy(self.information)
        branch.spatial = copy.deepcopy(self.spatial)
        branch.social = copy.deepcopy(self.social)
        branch.subjects = self.subjects.clone()
        branch.tick = self.tick
        branch.last_group_summary = copy.deepcopy(self.last_group_summary)
        branch.total_births = self.total_births
        branch.total_deaths = self.total_deaths
        branch.action_counts = self.action_counts.copy()
        branch.social_control_enabled = self.social_control_enabled
        branch.social_connections_enabled = self.social_connections_enabled
        branch.direct_messages_enabled = self.direct_messages_enabled
        branch.freeze_genotype = self.freeze_genotype
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
            self._trajectory_file.write(json.dumps(record, ensure_ascii=False) + "\n")
        self._trajectory_file.flush()

    def _resolve_shares(
        self,
        intents: ActionIntentBatch,
        resolutions: ActionResolutionBatch,
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Resolve transfers by target before any entity energy is changed."""
        ent = self.entities
        rows = action_rows(intents, Action.SHARE)
        if rows.size == 0:
            return rows, np.empty(0, dtype=np.int32), np.empty(0, dtype=np.float32)
        owners = intents.carrier_index[rows]
        targets = intents.target_index[rows]
        valid = (targets >= 0) & ent.alive[targets]
        safe_targets = np.where(valid, targets, 0)
        # Target-first, stable-carrier ordering is the CPU reference ordering
        # for the corresponding GPU segmented reduction.
        order = np.lexsort((intents.carrier_id[rows], ent.entity_id[safe_targets]))
        rows = rows[order]
        owners = owners[order]
        targets = targets[order]
        valid = valid[order]
        safe_targets = safe_targets[order]
        proposed = np.where(
            valid,
            np.minimum(self.cfg.entities.share_amount, np.maximum(ent.energy[owners] - 0.5, 0.0)),
            0.0,
        ).astype(np.float32)
        if not np.any(proposed > 0):
            resolutions.success[rows] = False
            resolutions.failure_reason[rows] = np.where(
                valid, FailureReason.INSUFFICIENT_RESOURCE, FailureReason.INVALID_TARGET
            )
            return rows, targets, proposed
        total_by_target = np.bincount(safe_targets, weights=proposed, minlength=ent.alive.size).astype(np.float32)
        capacity = np.maximum(self.cfg.entities.max_energy - ent.energy, 0.0)
        scale = np.ones(ent.alive.size, dtype=np.float32)
        occupied = total_by_target > 0
        scale[occupied] = np.minimum(1.0, capacity[occupied] / total_by_target[occupied])
        actual = proposed * scale[safe_targets]
        success = actual > 1e-8
        resolutions.success[rows] = success
        resolutions.failure_reason[rows[~success]] = FailureReason.INSUFFICIENT_CAPACITY
        resolutions.resource_delta[rows, 0] = -actual
        return rows, safe_targets, actual

    def _commit_shares(self, rows: np.ndarray, targets: np.ndarray, actual: np.ndarray) -> float:
        if rows.size == 0:
            return 0.0
        owners = self.last_intents.carrier_index[rows] if self.last_intents is not None else np.empty(0, dtype=np.int32)
        self.entities.energy[owners] -= actual
        np.add.at(self.entities.energy, targets, actual)
        np.add.at(self.entities.shared_energy_received_total, targets, actual)
        if self.social_connections_enabled and self.last_resolutions is not None:
            self.social.record_shares(
                owners,
                targets,
                self.last_resolutions.success[rows],
                self.tick,
            )
        return float(actual.sum())

    def _emit_signals(
        self,
        actors: np.ndarray,
        cells: np.ndarray,
        local_resources: np.ndarray,
        target_indices: np.ndarray,
    ) -> tuple[int, int]:
        if actors.size == 0:
            return 0, 0
        ent = self.entities
        actor_cells = cells
        strengths_resource = np.clip(local_resources[:, 0], 0.0, 2.0) * 0.15
        hazard = self.environment.hazard.reshape(-1)[actor_cells]
        strengths_danger = hazard * 0.15
        group_member = self.social.group_id[actors] != 0
        strengths_social = group_member.astype(np.float32) * 0.12
        self.information.emit(0, actor_cells, strengths_resource)
        self.information.emit(1, actor_cells, strengths_danger)
        self.information.emit(2, actor_cells, strengths_social)
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
        return int(actors.size), direct_messages

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
        intents = build_intents(active, ent.entity_id, decision, self.tick)
        resolutions = empty_resolutions(intents)

        harvest_rows = action_rows(intents, Action.HARVEST)
        harvest_cells = np.empty(0, dtype=np.int32)
        gathered = np.empty((0, 4), dtype=np.float32)
        if harvest_rows.size:
            observation_rows = np.searchsorted(active, intents.carrier_index[harvest_rows])
            harvest_cells = cells[observation_rows]
            order = np.lexsort((intents.carrier_id[harvest_rows], harvest_cells))
            harvest_rows = harvest_rows[order]
            harvest_cells = harvest_cells[order]
            base = cfg.entities.harvest_rate
            rates = np.tile(
                np.asarray([base, base * 0.45, base * 0.25, base * 0.18], dtype=np.float32),
                (harvest_rows.size, 1),
            )
            gathered = self.environment.resolve_harvest(harvest_cells, rates)
            resolutions.resource_delta[harvest_rows] = gathered
            harvested = gathered[:, 0] > 1e-8
            resolutions.success[harvest_rows] = harvested
            resolutions.failure_reason[harvest_rows[~harvested]] = FailureReason.INSUFFICIENT_RESOURCE

        share_rows, share_targets, shared = self._resolve_shares(intents, resolutions)

        signal_rows = action_rows(intents, Action.SIGNAL)
        if signal_rows.size:
            resolutions.energy_cost[signal_rows] = cfg.entities.signal_cost

        reproduce_rows = action_rows(intents, Action.REPRODUCE)
        accepted_reproduce_rows = np.empty(0, dtype=np.int32)
        if reproduce_rows.size:
            parents = intents.carrier_index[reproduce_rows]
            valid_parent = (
                ent.energy[parents] >= cfg.entities.reproduction_threshold
            ) & (ent.fertility[parents] >= 0.5)
            invalid_rows = reproduce_rows[~valid_parent]
            resolutions.success[invalid_rows] = False
            resolutions.failure_reason[invalid_rows] = FailureReason.INSUFFICIENT_RESOURCE
            candidates = reproduce_rows[valid_parent]
            candidates = candidates[np.argsort(intents.carrier_id[candidates], kind="stable")]
            accepted_reproduce_rows = candidates[: len(ent.free_slots)]
            rejected = candidates[len(ent.free_slots) :]
            resolutions.success[rejected] = False
            resolutions.failure_reason[rejected] = FailureReason.INSUFFICIENT_CAPACITY
            resolutions.energy_cost[accepted_reproduce_rows] = cfg.entities.reproduction_cost
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
            self.environment.commit_harvest(harvest_cells, gathered)
            harvesters = intents.carrier_index[harvest_rows]
            ent.energy[harvesters] = np.minimum(ent.energy[harvesters] + gathered[:, 0], cfg.entities.max_energy)
            ent.integrity[harvesters] = np.minimum(ent.integrity[harvesters] + gathered[:, 1] * 0.05, 1.0)
            ent.information_store[harvesters] = np.minimum(ent.information_store[harvesters] + gathered[:, 2], 3.0)
            ent.fertility[harvesters] = np.minimum(ent.fertility[harvesters] + gathered[:, 3], 3.0)
            ent.harvested_energy_total[harvesters] += gathered[:, 0]
            stats.harvested_energy = float(gathered[:, 0].sum())

        stats.shared_energy = self._commit_shares(share_rows, share_targets, shared)

        if signal_rows.size:
            signal_actors = intents.carrier_index[signal_rows]
            signal_observation_rows = np.searchsorted(active, signal_actors)
            stats.signals, stats.direct_messages = self._emit_signals(
                signal_actors,
                cells[signal_observation_rows],
                local_resources[signal_observation_rows],
                intents.target_index[signal_rows],
            )

        if accepted_reproduce_rows.size:
            requested_parents = intents.carrier_index[accepted_reproduce_rows]
            accepted_parents, newborns = ent.allocate_births(
                requested_parents,
                self.tick,
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
                stats.births = int(newborns.size)
                self.total_births += stats.births

        # Existence costs and environmental damage.
        current_active = np.flatnonzero(ent.alive).astype(np.int32)
        current_cells = self.spatial.cell_ids(ent.x[current_active], ent.y[current_active])
        hazard = self.environment.hazard.reshape(-1)[current_cells]
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
        if self.social_connections_enabled:
            self.social.decay(ent.alive)

        dead = current_active[
            (ent.energy[current_active] <= 0.0)
            | (ent.integrity[current_active] <= 0.0)
            | (ent.age[current_active] >= cfg.entities.max_age)
        ]
        if dead.size:
            self.subjects.mark_dead(dead, self.tick)
            ent.kill(dead)
            self.social.group_id[dead] = 0
            self.social.group_age[dead] = 0
            stats.deaths = int(dead.size)
            self.total_deaths += stats.deaths
        self.social.clear_dead_targets(ent.alive)

        # Candidate social subjects are updated at a slower timescale.
        phase_started = time.perf_counter()
        if self.tick % cfg.social.group_update_period == 0:
            if self.social_connections_enabled:
                self.last_group_summary = self.social.update_groups(
                    ent.alive,
                    ent.entity_id,
                    ent.energy,
                    resource_gradient[0],
                    resource_gradient[1],
                )
            else:
                self.social.group_id.fill(0)
                self.last_group_summary = GroupSummary(
                    np.empty(0, dtype=np.uint64), np.empty(0, dtype=np.int32), np.empty(0, dtype=np.float32)
                )
            self.subjects.update_groups(ent.alive, self.social.group_id, self.tick)
        stats.group_count = int(self.last_group_summary.group_ids.size)
        stats.mean_group_size = float(
            self.last_group_summary.counts.mean() if self.last_group_summary.counts.size else 0.0
        )
        stats.graph_seconds = time.perf_counter() - phase_started
        self._record_trajectories(intents, resolutions, decision.logits)
        self.tick += 1
        return stats

    def metric_row(self, stats: StepStats, elapsed: float) -> dict[str, float | int]:
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
        }
        row.update(self.subjects.summary())
        return row

    def run(self) -> dict[str, float | int]:
        started = time.perf_counter()
        final_row: dict[str, float | int] = {}
        try:
            for _ in range(self.cfg.run.ticks):
                step_started = time.perf_counter()
                stats = self.step()
                elapsed = time.perf_counter() - step_started
                if self.tick % self.cfg.run.metrics_period == 0 or self.tick == 1:
                    final_row = self.metric_row(stats, elapsed)
                    self.metrics.write(final_row)
                    print(
                        f"tick={self.tick:7d} alive={final_row['alive']:7d} "
                        f"groups={final_row['groups']:5d} E={final_row['mean_energy']:.3f} "
                        f"step={elapsed:.3f}s"
                    )
                if self.tick % self.cfg.run.checkpoint_period == 0:
                    self._checkpoint()
                if not np.any(self.entities.alive):
                    break
        finally:
            self.metrics.close()
            if self._trajectory_file is not None:
                self._trajectory_file.close()
        metadata = {
            "version": "0.2.0",
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
        }
        (self.output_dir / "run_metadata.json").write_text(
            json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        return final_row
