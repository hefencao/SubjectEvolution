"""Observational diagnostics for realized within-group functional division.

The tracker records what members actually do under the shared physical world:
raw harvesting, complementary conversion, raw/energy exchange, signalling and
social movement.  It never assigns roles, changes group labels, rewards a
profile, or feeds any value back into the simulation.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

import numpy as np

from se.policy import Action

GROUP_FUNCTION_DIAGNOSTICS_SCHEMA = "group-functional-division-diagnostics-v1"
FUNCTION_NAMES = tuple(
    [f"harvest_{index}" for index in range(4)]
    + [f"recipe_{index}" for index in range(4)]
    + [f"raw_share_sent_{index}" for index in range(4)]
    + [f"raw_share_received_{index}" for index in range(4)]
    + ["signal", "social_move", "energy_share_sent", "energy_share_received"]
)
FUNCTION_COUNT = len(FUNCTION_NAMES)


def _effective_dimensions(matrix: np.ndarray) -> float:
    values = np.asarray(matrix, dtype=np.float64)
    if values.ndim != 2 or values.shape[0] < 2 or not np.any(values):
        return 0.0
    centered = values - values.mean(axis=0, keepdims=True)
    if not np.any(np.abs(centered) > 1.0e-15):
        return 0.0
    singular = np.linalg.svd(centered, compute_uv=False)
    spectrum = singular * singular
    return float(
        spectrum.sum() ** 2
        / max(float(np.dot(spectrum, spectrum)), 1.0e-30)
    )


def _normalized_entropy_specialization(profile: np.ndarray) -> float:
    values = np.asarray(profile, dtype=np.float64)
    total = float(values.sum())
    if total <= 0.0:
        return 0.0
    shares = values[values > 0.0] / total
    if shares.size <= 1:
        return 1.0
    entropy = -float(np.sum(shares * np.log(shares)))
    return float(np.clip(1.0 - entropy / np.log(FUNCTION_COUNT), 0.0, 1.0))


class GroupFunctionDiagnostics:
    """Accumulate fixed-window realized member functions without feedback."""

    def __init__(
        self,
        output_dir: str | Path,
        *,
        window_ticks: int,
        min_members: int,
        schema: str = GROUP_FUNCTION_DIAGNOSTICS_SCHEMA,
    ) -> None:
        if schema != GROUP_FUNCTION_DIAGNOSTICS_SCHEMA:
            raise ValueError(f"unsupported group function schema {schema!r}")
        if int(window_ticks) <= 0:
            raise ValueError("group function window_ticks must be positive")
        if int(min_members) < 2:
            raise ValueError("group function min_members must be at least two")
        self.output_dir = Path(output_dir)
        self.schema = schema
        self.window_ticks = int(window_ticks)
        self.min_members = int(min_members)
        self.window_start_tick = 0
        self.last_observed_tick = -1
        self.member_ticks: dict[tuple[int, int], int] = {}
        self.member_profiles: dict[tuple[int, int], np.ndarray] = {}
        self.internal_raw_exchange_by_token: dict[int, np.ndarray] = {}
        self.internal_energy_exchange_by_token: dict[int, float] = {}
        self.records: list[dict[str, Any]] = []
        self.candidate_streak_by_token: dict[int, int] = {}
        self.max_candidate_streak_by_token: dict[int, int] = {}
        self.next_group_lineage_id = 1
        self.previous_group_members: dict[int, set[int]] = {}
        self.candidate_streak_by_lineage: dict[int, int] = {}
        self.max_candidate_streak_by_lineage: dict[int, int] = {}
        self.total_candidate_group_windows = 0
        self.max_candidate_groups_in_window = 0
        self.total_internal_raw_exchange = np.zeros(4, dtype=np.float64)

    def clone(self, output_dir: str | Path) -> "GroupFunctionDiagnostics":
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
        self.member_profiles = {
            (int(key[0]), int(key[1])): np.asarray(value, dtype=np.float64).copy()
            for key, value in self.member_profiles.items()
        }
        self.total_internal_raw_exchange = np.asarray(
            self.total_internal_raw_exchange, dtype=np.float64
        ).copy()
        self.internal_raw_exchange_by_token = {
            int(token): np.asarray(value, dtype=np.float64).copy()
            for token, value in self.internal_raw_exchange_by_token.items()
        }
        self.internal_energy_exchange_by_token = {
            int(token): float(value)
            for token, value in self.internal_energy_exchange_by_token.items()
        }

    def _profile(self, group_token: int, stable_id: int) -> np.ndarray:
        key = (int(group_token), int(stable_id))
        profile = self.member_profiles.get(key)
        if profile is None:
            profile = np.zeros(FUNCTION_COUNT, dtype=np.float64)
            self.member_profiles[key] = profile
        return profile

    def observe_step(
        self,
        *,
        tick: int,
        stable_ids: np.ndarray,
        alive: np.ndarray,
        group_ids: np.ndarray,
        action_actor_indices: np.ndarray,
        actions: np.ndarray,
        harvest_actor_indices: np.ndarray,
        harvested: np.ndarray,
        conversion_actor_indices: np.ndarray,
        recipe_throughput: np.ndarray,
        share_owner_indices: np.ndarray,
        share_target_indices: np.ndarray,
        shared_energy: np.ndarray,
        shared_resources: np.ndarray,
    ) -> dict[str, Any] | None:
        identities = np.asarray(stable_ids, dtype=np.uint64)
        self.last_observed_tick = int(tick)
        living = np.asarray(alive, dtype=bool)
        groups = np.asarray(group_ids, dtype=np.uint64)
        if identities.shape != living.shape or identities.shape != groups.shape:
            raise ValueError("group function identity/alive/group arrays must align")
        grouped = np.flatnonzero(living & (groups != 0)).astype(np.int32)
        for index in grouped.tolist():
            key = (int(groups[index]), int(identities[index]))
            self.member_ticks[key] = self.member_ticks.get(key, 0) + 1
            self._profile(*key)

        action_indices = np.asarray(action_actor_indices, dtype=np.int32)
        action_values = np.asarray(actions, dtype=np.int16)
        if action_indices.size != action_values.size:
            raise ValueError("group function actions must align with actors")
        for index, action in zip(action_indices.tolist(), action_values.tolist()):
            if index < 0 or index >= identities.size or groups[index] == 0:
                continue
            profile = self._profile(int(groups[index]), int(identities[index]))
            if action == int(Action.SIGNAL):
                profile[16] += 1.0
            elif action == int(Action.MOVE_SOCIAL):
                profile[17] += 1.0

        harvest_indices = np.asarray(harvest_actor_indices, dtype=np.int32)
        harvest_values = np.asarray(harvested, dtype=np.float64)
        if harvest_values.shape != (harvest_indices.size, 4):
            raise ValueError("group function harvested flow must be shaped [N, 4]")
        for row, index in enumerate(harvest_indices.tolist()):
            if index < 0 or index >= identities.size or groups[index] == 0:
                continue
            self._profile(int(groups[index]), int(identities[index]))[:4] += harvest_values[row]

        conversion_indices = np.asarray(conversion_actor_indices, dtype=np.int32)
        throughput = np.asarray(recipe_throughput, dtype=np.float64)
        if throughput.shape != (conversion_indices.size, 4):
            raise ValueError("group function recipe throughput must be shaped [N, 4]")
        for row, index in enumerate(conversion_indices.tolist()):
            if index < 0 or index >= identities.size or groups[index] == 0:
                continue
            self._profile(int(groups[index]), int(identities[index]))[4:8] += throughput[row]

        owners = np.asarray(share_owner_indices, dtype=np.int32)
        targets = np.asarray(share_target_indices, dtype=np.int32)
        energy = np.asarray(shared_energy, dtype=np.float64)
        raw = np.asarray(shared_resources, dtype=np.float64)
        if not (owners.size == targets.size == energy.size) or raw.shape != (owners.size, 4):
            raise ValueError("group function share flows must align")
        for row, (owner, target) in enumerate(zip(owners.tolist(), targets.tolist())):
            if owner < 0 or target < 0 or owner >= identities.size or target >= identities.size:
                continue
            owner_group = int(groups[owner])
            target_group = int(groups[target])
            if owner_group:
                owner_profile = self._profile(owner_group, int(identities[owner]))
                owner_profile[8:12] += raw[row]
                owner_profile[18] += energy[row]
            if target_group:
                target_profile = self._profile(target_group, int(identities[target]))
                target_profile[12:16] += raw[row]
                target_profile[19] += energy[row]
            if owner_group != 0 and owner_group == target_group:
                self.total_internal_raw_exchange += raw[row]
                token_flow = self.internal_raw_exchange_by_token.setdefault(
                    owner_group, np.zeros(4, dtype=np.float64)
                )
                token_flow += raw[row]
                self.internal_energy_exchange_by_token[owner_group] = (
                    self.internal_energy_exchange_by_token.get(owner_group, 0.0)
                    + float(energy[row])
                )

        if (int(tick) + 1) % self.window_ticks == 0:
            return self._flush_window(int(tick) + 1)
        return None

    def _flush_window(self, end_tick: int) -> dict[str, Any]:
        grouped_keys: dict[int, list[tuple[int, int]]] = {}
        for key in self.member_ticks:
            grouped_keys.setdefault(int(key[0]), []).append(key)
        group_rows: list[dict[str, Any]] = []
        current_core_members: list[set[int]] = []
        candidate_tokens: set[int] = set()
        for token in sorted(grouped_keys):
            keys = sorted(grouped_keys[token], key=lambda item: item[1])
            ticks = np.asarray([self.member_ticks[key] for key in keys], dtype=np.float64)
            raw_profiles = np.vstack([self.member_profiles[key] for key in keys])
            membership_fraction = ticks / max(end_tick - self.window_start_tick, 1)
            stable_mask = membership_fraction >= 0.50
            stable_member_count = int(stable_mask.sum())
            stable_member_ids = {
                int(keys[index][1])
                for index in np.flatnonzero(stable_mask).tolist()
            }
            stable_ticks = ticks[stable_mask]
            stable_profiles = raw_profiles[stable_mask]
            # A token that only flashes through the window is not a social
            # structure.  Functional differentiation is evaluated on the
            # stable core; transient members remain visible in the report.
            ticks_for_rates = stable_ticks if stable_member_count else ticks[:0]
            profiles_for_rates = (
                stable_profiles if stable_member_count else raw_profiles[:0]
            )
            rates = profiles_for_rates / np.maximum(ticks_for_rates[:, None], 1.0)
            active_mask = rates.sum(axis=1) > 1.0e-12
            active_rates = rates[active_mask]
            function_totals = active_rates.sum(axis=0) if active_rates.size else np.zeros(FUNCTION_COUNT)
            balanced = active_rates / np.maximum(function_totals[None, :], 1.0e-30) if active_rates.size else active_rates
            balanced /= np.maximum(balanced.sum(axis=1, keepdims=True), 1.0e-30) if balanced.size else 1.0
            effective_dimensions = _effective_dimensions(balanced)
            dominant_functions = (
                np.argmax(balanced, axis=1) if balanced.size else np.zeros(0, dtype=np.int32)
            )
            dominant_count = int(np.unique(dominant_functions).size)
            specialization = (
                float(np.mean([_normalized_entropy_specialization(row) for row in balanced]))
                if balanced.size
                else 0.0
            )
            member_count = len(keys)
            active_member_count = int(active_mask.sum())
            participation = active_member_count / max(stable_member_count, 1)
            recipe_coverage = int(np.count_nonzero(function_totals[4:8] > 1.0e-10))
            internal_raw_vector = self.internal_raw_exchange_by_token.get(
                token, np.zeros(4, dtype=np.float64)
            )
            internal_raw = float(np.asarray(internal_raw_vector).sum())
            internal_energy = float(
                self.internal_energy_exchange_by_token.get(token, 0.0)
            )
            raw_received = internal_raw
            raw_harvested = float(function_totals[:4].sum())
            exchange_dependency = raw_received / max(raw_received + raw_harvested, 1.0e-30)
            stable_membership_mean = (
                float(membership_fraction[stable_mask].mean())
                if stable_member_count
                else 0.0
            )
            candidate = bool(
                stable_member_count >= self.min_members
                and active_member_count >= self.min_members
                and participation >= 0.75
                and stable_membership_mean >= 0.65
                and effective_dimensions >= 2.0
                and dominant_count >= 3
                and specialization >= 0.18
                and recipe_coverage >= 2
                and internal_raw > 1.0e-6
                and exchange_dependency >= 0.01
            )
            if candidate:
                candidate_tokens.add(token)
            group_rows.append(
                {
                    "group_token": token,
                    "member_count": member_count,
                    "stable_member_count": stable_member_count,
                    "stable_membership_mean": stable_membership_mean,
                    "active_member_count": active_member_count,
                    "participation_fraction": participation,
                    "functional_effective_dimensions": effective_dimensions,
                    "dominant_function_count": dominant_count,
                    "mean_member_specialization": specialization,
                    "recipe_coverage": recipe_coverage,
                    "internal_raw_exchange": internal_raw,
                    "internal_raw_exchange_by_channel": np.asarray(
                        internal_raw_vector, dtype=np.float64
                    ).tolist(),
                    "internal_energy_exchange": internal_energy,
                    "raw_exchange_dependency": exchange_dependency,
                    "function_totals": {
                        name: float(value)
                        for name, value in zip(FUNCTION_NAMES, function_totals.tolist())
                    },
                    "division_candidate": candidate,
                }
            )
            current_core_members.append(stable_member_ids)

        # Group tokens are rooted in one member and can change when that
        # member dies.  Track observational group lineages by stable-member
        # overlap so a token change cannot masquerade as social turnover.
        pair_scores: list[tuple[float, int, int]] = []
        for row_index, members in enumerate(current_core_members):
            if not members:
                continue
            for lineage_id, previous in self.previous_group_members.items():
                union = members | previous
                overlap = len(members & previous)
                jaccard = overlap / max(len(union), 1)
                if overlap >= 3 and jaccard >= 0.40:
                    pair_scores.append((-jaccard, int(lineage_id), row_index))
        assigned_lineages: set[int] = set()
        assigned_rows: set[int] = set()
        row_lineages: dict[int, int] = {}
        for _negative_score, lineage_id, row_index in sorted(pair_scores):
            if lineage_id in assigned_lineages or row_index in assigned_rows:
                continue
            row_lineages[row_index] = lineage_id
            assigned_lineages.add(lineage_id)
            assigned_rows.add(row_index)
        for row_index in range(len(group_rows)):
            if row_index not in row_lineages:
                row_lineages[row_index] = self.next_group_lineage_id
                self.next_group_lineage_id += 1
            group_rows[row_index]["group_lineage_id"] = row_lineages[row_index]

        current_lineage_members = {
            row_lineages[index]: members
            for index, members in enumerate(current_core_members)
            if members
        }
        current_lineages = set(current_lineage_members)
        for lineage_id in set(self.candidate_streak_by_lineage) | current_lineages:
            row_index = next(
                (
                    index
                    for index, value in row_lineages.items()
                    if value == lineage_id
                ),
                None,
            )
            candidate = bool(
                row_index is not None
                and group_rows[row_index]["division_candidate"]
            )
            streak = (
                self.candidate_streak_by_lineage.get(lineage_id, 0) + 1
                if candidate
                else 0
            )
            self.candidate_streak_by_lineage[lineage_id] = streak
            self.max_candidate_streak_by_lineage[lineage_id] = max(
                self.max_candidate_streak_by_lineage.get(lineage_id, 0),
                streak,
            )
        self.previous_group_members = current_lineage_members

        all_tokens = set(self.candidate_streak_by_token).union(candidate_tokens)
        for token in all_tokens:
            streak = self.candidate_streak_by_token.get(token, 0) + 1 if token in candidate_tokens else 0
            self.candidate_streak_by_token[token] = streak
            self.max_candidate_streak_by_token[token] = max(
                self.max_candidate_streak_by_token.get(token, 0), streak
            )
        candidate_count = len(candidate_tokens)
        self.total_candidate_group_windows += candidate_count
        self.max_candidate_groups_in_window = max(
            self.max_candidate_groups_in_window, candidate_count
        )
        record = {
            "schema": self.schema,
            "window_start_tick": self.window_start_tick,
            "window_end_tick": end_tick,
            "window_ticks": end_tick - self.window_start_tick,
            "observed_group_count": len(group_rows),
            "division_candidate_group_count": candidate_count,
            "division_candidate_tokens": sorted(candidate_tokens),
            "groups": group_rows,
            "interpretation_boundary": (
                "A division candidate is a realized, observational pattern. It does not "
                "assign roles, prove adaptive specialization, or authorize gene-level audit."
            ),
        }
        self.records.append(record)
        self.window_start_tick = end_tick
        self.member_ticks.clear()
        self.member_profiles.clear()
        self.internal_raw_exchange_by_token.clear()
        self.internal_energy_exchange_by_token.clear()
        return record

    def latest_metrics(self) -> dict[str, Any]:
        latest = self.records[-1] if self.records else None
        return {
            "group_function_schema": self.schema,
            "group_function_windows": len(self.records),
            "group_function_candidate_groups": int(
                latest["division_candidate_group_count"] if latest else 0
            ),
            "group_function_candidate_group_windows_total": int(
                self.total_candidate_group_windows
            ),
            "group_function_max_candidate_streak": int(
                max(self.max_candidate_streak_by_lineage.values(), default=0)
            ),
        }

    def summary(self) -> dict[str, Any]:
        persistent = {
            str(token): int(streak)
            for token, streak in sorted(self.max_candidate_streak_by_token.items())
            if streak >= 2
        }
        persistent_lineages = {
            str(lineage_id): int(streak)
            for lineage_id, streak in sorted(
                self.max_candidate_streak_by_lineage.items()
            )
            if streak >= 2
        }
        return {
            "schema": self.schema,
            "window_ticks": self.window_ticks,
            "window_count": len(self.records),
            "candidate_group_windows_total": int(self.total_candidate_group_windows),
            "max_candidate_groups_in_window": int(self.max_candidate_groups_in_window),
            "max_candidate_streak_by_token": {
                str(token): int(streak)
                for token, streak in sorted(self.max_candidate_streak_by_token.items())
            },
            "persistent_division_candidate_tokens": persistent,
            "persistent_division_candidate_count": len(persistent),
            "max_candidate_streak_by_lineage": {
                str(lineage_id): int(streak)
                for lineage_id, streak in sorted(
                    self.max_candidate_streak_by_lineage.items()
                )
            },
            "persistent_division_candidate_lineages": persistent_lineages,
            "persistent_division_lineage_count": len(persistent_lineages),
            "internal_raw_exchange_total": self.total_internal_raw_exchange.tolist(),
            "latest": self.records[-1] if self.records else None,
            "interpretation_boundary": (
                "This diagnostic establishes only realized within-group functional "
                "differentiation and exchange candidates. It cannot establish social "
                "roles, selection, adaptation, or subjecthood."
            ),
        }

    def close(self) -> None:
        if self.member_ticks:
            self._flush_window(max(self.last_observed_tick + 1, self.window_start_tick + 1))
        self.output_dir.mkdir(parents=True, exist_ok=True)
        with (self.output_dir / "group_function_windows.jsonl").open(
            "w", encoding="utf-8"
        ) as stream:
            for record in self.records:
                stream.write(json.dumps(record, sort_keys=True) + "\n")
        (self.output_dir / "group_function_summary.json").write_text(
            json.dumps(self.summary(), indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )


__all__ = [
    "FUNCTION_NAMES",
    "GROUP_FUNCTION_DIAGNOSTICS_SCHEMA",
    "GroupFunctionDiagnostics",
]
