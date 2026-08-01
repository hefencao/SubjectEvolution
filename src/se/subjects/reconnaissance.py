"""Observational diagnostics for a role-neutral reconnaissance value chain.

A candidate is not a role label and is never fed back into policy.  The tracker
asks whether a stable group contains members that (a) range farther with lower
raw load and inherited sensing reach, (b) encounter local contest pressure and
signal it, and (c) have same-group receivers that detect danger-bearing direct
messages and choose a danger-aligned action.  Correlation is reported as a
mechanism-connection diagnostic, not causality or adaptation.
"""
from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

import numpy as np

from se.policy import Action

RECONNAISSANCE_DIAGNOSTICS_SCHEMA = "reconnaissance-pressure-chain-diagnostics-v1"


def _periodic_distance(
    values: np.ndarray, center: float, extent: float
) -> np.ndarray:
    delta = np.abs(np.asarray(values, dtype=np.float64) - float(center))
    return np.minimum(delta, float(extent) - delta)


def _periodic_center(values: np.ndarray, extent: float) -> float:
    angles = np.asarray(values, dtype=np.float64) * (2.0 * np.pi / float(extent))
    angle = np.arctan2(np.sin(angles).mean(), np.cos(angles).mean())
    return float((angle % (2.0 * np.pi)) * float(extent) / (2.0 * np.pi))


class ReconnaissanceDiagnostics:
    def __init__(
        self,
        output_dir: str | Path,
        *,
        window_ticks: int,
        min_members: int,
        world_width: float,
        world_height: float,
        schema: str = RECONNAISSANCE_DIAGNOSTICS_SCHEMA,
    ) -> None:
        if schema != RECONNAISSANCE_DIAGNOSTICS_SCHEMA:
            raise ValueError(f"unsupported reconnaissance schema {schema!r}")
        if int(window_ticks) <= 0:
            raise ValueError("reconnaissance window must be positive")
        self.output_dir = Path(output_dir)
        self.window_ticks = int(window_ticks)
        self.min_members = max(int(min_members), 2)
        self.world_width = float(world_width)
        self.world_height = float(world_height)
        self.schema = schema
        self.window_start_tick = 0
        self.last_observed_tick = -1
        self.member_ticks: dict[tuple[int, int], int] = {}
        self.frontier_signal_events: dict[tuple[int, int], int] = {}
        self.same_group_danger_messages: dict[tuple[int, int], int] = {}
        self.aligned_flee_responses: dict[tuple[int, int], int] = {}
        self.contest_exposure: dict[tuple[int, int], float] = {}
        self.records: list[dict[str, Any]] = []
        self.next_group_lineage_id = 1
        self.previous_group_members: dict[int, set[int]] = {}
        self.candidate_streak_by_lineage: dict[int, int] = {}
        self.max_candidate_streak_by_lineage: dict[int, int] = {}
        self.total_frontier_signal_events = 0
        self.total_same_group_danger_messages = 0
        self.total_aligned_flee_responses = 0
        self.total_candidate_group_windows = 0

    def clone(self, output_dir: str | Path) -> "ReconnaissanceDiagnostics":
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

    def observe_step(
        self,
        *,
        tick: int,
        active: np.ndarray,
        stable_ids: np.ndarray,
        alive: np.ndarray,
        group_ids: np.ndarray,
        x: np.ndarray,
        y: np.ndarray,
        load_fraction: np.ndarray,
        sensing_radius: np.ndarray,
        recent_contest_pressure: np.ndarray,
        actions: np.ndarray,
        direction_x: np.ndarray,
        direction_y: np.ndarray,
        information: Any,
    ) -> dict[str, Any] | None:
        self.last_observed_tick = int(tick)
        rows = np.asarray(active, dtype=np.int32)
        ids = np.asarray(stable_ids, dtype=np.uint64)
        living = np.asarray(alive, dtype=bool)
        groups = np.asarray(group_ids, dtype=np.uint64)
        action_values = np.asarray(actions, dtype=np.int16)
        direction_x_values = np.asarray(direction_x, dtype=np.float32)
        direction_y_values = np.asarray(direction_y, dtype=np.float32)
        if action_values.shape != (rows.size,) or any(
            value.shape != (rows.size,)
            for value in (direction_x_values, direction_y_values)
        ):
            raise ValueError(
                "reconnaissance actions and directions must align with active rows"
            )
        if any(array.shape != living.shape for array in (ids, groups, x, y, load_fraction, sensing_radius, recent_contest_pressure)):
            raise ValueError("reconnaissance entity arrays must align")

        grouped_rows = rows[living[rows] & (groups[rows] != 0)]
        for index in grouped_rows.tolist():
            key = (int(groups[index]), int(ids[index]))
            self.member_ticks[key] = self.member_ticks.get(key, 0) + 1
            self.contest_exposure[key] = self.contest_exposure.get(key, 0.0) + float(
                recent_contest_pressure[index]
            )

        # Frontier signalling is defined relative to current peers, not by a
        # fixed occupation threshold.  It requires actual contest evidence.
        active_position = {int(index): row for row, index in enumerate(rows.tolist())}
        for token in sorted({int(groups[index]) for index in grouped_rows.tolist()}):
            members = grouped_rows[groups[grouped_rows] == token]
            if members.size < self.min_members:
                continue
            cx = _periodic_center(np.asarray(x)[members], self.world_width)
            cy = _periodic_center(np.asarray(y)[members], self.world_height)
            distance = np.hypot(
                _periodic_distance(np.asarray(x)[members], cx, self.world_width),
                _periodic_distance(np.asarray(y)[members], cy, self.world_height),
            )
            load = np.asarray(load_fraction, dtype=np.float64)[members]
            reach = np.asarray(sensing_radius, dtype=np.float64)[members]
            distance_cut = float(np.median(distance))
            load_cut = float(np.median(load))
            reach_cut = float(np.median(reach))
            for member, member_distance in zip(members.tolist(), distance.tolist()):
                row = active_position.get(int(member))
                if row is None or action_values[row] != int(Action.SIGNAL):
                    continue
                if (
                    float(recent_contest_pressure[member]) > 0.02
                    and float(member_distance) >= distance_cut
                    and float(load_fraction[member]) <= load_cut
                    and float(sensing_radius[member]) >= reach_cut
                ):
                    key = (token, int(ids[member]))
                    self.frontier_signal_events[key] = (
                        self.frontier_signal_events.get(key, 0) + 1
                    )
                    self.total_frontier_signal_events += 1

        # Direct-message reception is evaluated on the observation that drove
        # this tick's action.  Same-group danger messages and FLEE alignment are
        # counted, but no causal credit is assigned.
        if information is not None and rows.size:
            message_mask = np.asarray(information.message_mask, dtype=bool)
            messages = np.asarray(information.messages, dtype=np.float32)
            source_ids = np.asarray(information.message_source_id, dtype=np.uint64)
            if message_mask.shape != source_ids.shape or messages.shape[:2] != message_mask.shape:
                raise ValueError("reconnaissance direct-message tensors must align")
            id_to_index = {
                int(ids[index]): int(index)
                for index in np.flatnonzero(living & (ids != 0)).tolist()
            }
            for active_row, receiver in enumerate(rows.tolist()):
                receiver_group = int(groups[receiver])
                if receiver_group == 0:
                    continue
                accepted = np.flatnonzero(message_mask[active_row])
                for slot in accepted.tolist():
                    source = id_to_index.get(int(source_ids[active_row, slot]))
                    if source is None or int(groups[source]) != receiver_group:
                        continue
                    danger = float(messages[active_row, slot, 1])
                    if danger <= 0.02:
                        continue
                    key = (receiver_group, int(ids[receiver]))
                    self.same_group_danger_messages[key] = (
                        self.same_group_danger_messages.get(key, 0) + 1
                    )
                    self.total_same_group_danger_messages += 1
                    if action_values[active_row] == int(Action.FLEE):
                        toward_x = float(x[source]) - float(x[receiver])
                        toward_y = float(y[source]) - float(y[receiver])
                        if self.world_width > 0.0:
                            toward_x = float(
                                (toward_x + 0.5 * self.world_width)
                                % self.world_width
                                - 0.5 * self.world_width
                            )
                        if self.world_height > 0.0:
                            toward_y = float(
                                (toward_y + 0.5 * self.world_height)
                                % self.world_height
                                - 0.5 * self.world_height
                            )
                        magnitude = max(float(np.hypot(toward_x, toward_y)), 1.0e-6)
                        away_x = -toward_x / magnitude
                        away_y = -toward_y / magnitude
                        alignment = (
                            float(direction_x_values[active_row]) * away_x
                            + float(direction_y_values[active_row]) * away_y
                        )
                        if alignment > 0.0:
                            self.aligned_flee_responses[key] = (
                                self.aligned_flee_responses.get(key, 0) + 1
                            )
                            self.total_aligned_flee_responses += 1

        if (int(tick) + 1) % self.window_ticks == 0:
            return self._flush_window(int(tick) + 1)
        return None

    def _flush_window(self, end_tick: int) -> dict[str, Any]:
        by_token: dict[int, list[tuple[int, int]]] = {}
        for key in self.member_ticks:
            by_token.setdefault(int(key[0]), []).append(key)
        group_rows: list[dict[str, Any]] = []
        cores: list[set[int]] = []
        for token in sorted(by_token):
            keys = sorted(by_token[token], key=lambda item: item[1])
            fractions = np.asarray(
                [self.member_ticks[key] for key in keys], dtype=np.float64
            ) / max(end_tick - self.window_start_tick, 1)
            stable = fractions >= 0.50
            stable_keys = [keys[i] for i in np.flatnonzero(stable).tolist()]
            core = {int(key[1]) for key in stable_keys}
            frontier = sum(self.frontier_signal_events.get(key, 0) for key in stable_keys)
            messages = sum(self.same_group_danger_messages.get(key, 0) for key in stable_keys)
            responses = sum(self.aligned_flee_responses.get(key, 0) for key in stable_keys)
            exposure = sum(self.contest_exposure.get(key, 0.0) for key in stable_keys)
            frontier_members = sum(
                self.frontier_signal_events.get(key, 0) > 0 for key in stable_keys
            )
            responder_members = sum(
                self.aligned_flee_responses.get(key, 0) > 0 for key in stable_keys
            )
            candidate = bool(
                len(core) >= self.min_members
                and frontier >= 2
                and frontier_members >= 1
                and messages >= 2
                and responses >= 1
                and responder_members >= 1
                and exposure > 0.0
            )
            group_rows.append(
                {
                    "group_token": token,
                    "stable_member_count": len(core),
                    "frontier_signal_events": int(frontier),
                    "frontier_member_count": int(frontier_members),
                    "same_group_danger_messages": int(messages),
                    "aligned_flee_responses": int(responses),
                    "responder_member_count": int(responder_members),
                    "contest_exposure_sum": float(exposure),
                    "reconnaissance_chain_candidate": candidate,
                }
            )
            cores.append(core)

        # Match stable cores across token changes.
        pairs: list[tuple[float, int, int]] = []
        for row_index, members in enumerate(cores):
            if not members:
                continue
            for lineage, previous in self.previous_group_members.items():
                overlap = len(members & previous)
                union = len(members | previous)
                score = overlap / max(union, 1)
                if overlap >= 3 and score >= 0.40:
                    pairs.append((-score, int(lineage), row_index))
        used_lineages: set[int] = set()
        used_rows: set[int] = set()
        assignment: dict[int, int] = {}
        for _neg, lineage, row_index in sorted(pairs):
            if lineage in used_lineages or row_index in used_rows:
                continue
            assignment[row_index] = lineage
            used_lineages.add(lineage)
            used_rows.add(row_index)
        current: dict[int, set[int]] = {}
        for row_index, row in enumerate(group_rows):
            lineage = assignment.get(row_index)
            if lineage is None:
                lineage = self.next_group_lineage_id
                self.next_group_lineage_id += 1
            row["group_lineage_id"] = lineage
            current[lineage] = cores[row_index]
            previous_streak = self.candidate_streak_by_lineage.get(lineage, 0)
            streak = previous_streak + 1 if row["reconnaissance_chain_candidate"] else 0
            self.candidate_streak_by_lineage[lineage] = streak
            self.max_candidate_streak_by_lineage[lineage] = max(
                self.max_candidate_streak_by_lineage.get(lineage, 0), streak
            )
            row["candidate_streak"] = streak
            row["persistent_candidate"] = bool(streak >= 2)
            if row["reconnaissance_chain_candidate"]:
                self.total_candidate_group_windows += 1
        self.previous_group_members = current
        record = {
            "schema": self.schema,
            "window_start_tick": self.window_start_tick,
            "window_end_tick": int(end_tick),
            "groups": group_rows,
            "candidate_group_count": int(
                sum(row["reconnaissance_chain_candidate"] for row in group_rows)
            ),
            "persistent_candidate_group_count": int(
                sum(row["persistent_candidate"] for row in group_rows)
            ),
        }
        self.records.append(record)
        self.window_start_tick = int(end_tick)
        self.member_ticks.clear()
        self.frontier_signal_events.clear()
        self.same_group_danger_messages.clear()
        self.aligned_flee_responses.clear()
        self.contest_exposure.clear()
        return record

    def latest_metrics(self) -> dict[str, Any]:
        latest = self.records[-1] if self.records else {}
        return {
            "reconnaissance_candidate_groups_latest": int(
                latest.get("candidate_group_count", 0)
            ),
            "reconnaissance_persistent_groups_latest": int(
                latest.get("persistent_candidate_group_count", 0)
            ),
            "reconnaissance_frontier_signal_events_total": int(
                self.total_frontier_signal_events
            ),
            "reconnaissance_same_group_danger_messages_total": int(
                self.total_same_group_danger_messages
            ),
            "reconnaissance_aligned_flee_responses_total": int(
                self.total_aligned_flee_responses
            ),
        }

    def close(self) -> dict[str, Any]:
        if self.member_ticks:
            self._flush_window(self.last_observed_tick + 1)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        window_path = self.output_dir / "reconnaissance_windows.jsonl"
        with window_path.open("w", encoding="utf-8") as handle:
            for record in self.records:
                handle.write(json.dumps(record, ensure_ascii=False) + "\n")
        persistent = sorted(
            int(lineage)
            for lineage, streak in self.max_candidate_streak_by_lineage.items()
            if int(streak) >= 2
        )
        summary = {
            "schema": self.schema,
            "window_ticks": self.window_ticks,
            "window_count": len(self.records),
            "total_frontier_signal_events": self.total_frontier_signal_events,
            "total_same_group_danger_messages": self.total_same_group_danger_messages,
            "total_aligned_flee_responses": self.total_aligned_flee_responses,
            "total_candidate_group_windows": self.total_candidate_group_windows,
            "persistent_reconnaissance_candidate_lineages": persistent,
            "persistent_reconnaissance_candidate_count": len(persistent),
            "interpretation_boundary": (
                "Candidates show an observationally connected pressure-sensing-signal-response "
                "chain. They are not assigned roles and do not establish causal benefit, "
                "selection, adaptation or stable occupation."
            ),
        }
        (self.output_dir / "reconnaissance_summary.json").write_text(
            json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        return summary


def build_reconnaissance_diagnostics(simulation: Any) -> ReconnaissanceDiagnostics | None:
    cfg = simulation.cfg
    if not cfg.run.reconnaissance_diagnostics_enabled:
        return None
    return ReconnaissanceDiagnostics(
        simulation.output_dir,
        window_ticks=cfg.run.reconnaissance_window_ticks,
        min_members=cfg.social.group_min_members,
        world_width=cfg.world.width,
        world_height=cfg.world.height,
        schema=cfg.run.reconnaissance_diagnostics_schema,
    )


def observe_reconnaissance_step(
    simulation: Any,
    *,
    active: np.ndarray,
    load_fraction: np.ndarray,
    actions: np.ndarray,
    direction_x: np.ndarray,
    direction_y: np.ndarray,
    information: Any,
) -> None:
    diagnostics = simulation.reconnaissance_diagnostics
    if diagnostics is None:
        return
    from se.runtime.resource_sensing import effective_danger_sensing_radius

    ent = simulation.entities
    radius = effective_danger_sensing_radius(simulation)
    if radius is None:
        radius = np.ones(ent.alive.size, dtype=np.int16)
    diagnostics.observe_step(
        tick=simulation.tick,
        active=active,
        stable_ids=ent.entity_id,
        alive=ent.alive,
        group_ids=simulation.social.group_id,
        x=ent.x,
        y=ent.y,
        load_fraction=load_fraction,
        sensing_radius=radius,
        recent_contest_pressure=ent.recent_contest_pressure,
        actions=actions,
        direction_x=direction_x,
        direction_y=direction_y,
        information=information,
    )


__all__ = [
    "RECONNAISSANCE_DIAGNOSTICS_SCHEMA",
    "ReconnaissanceDiagnostics",
    "build_reconnaissance_diagnostics",
    "observe_reconnaissance_step",
]
