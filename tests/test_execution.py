import numpy as np

from subject_evolution.config import load_config
from subject_evolution.execution import (
    ActionResolutionSnapshot,
    DeterministicActionConflictResolver,
    ShareResolution,
)
from subject_evolution.intents import ActionIntentBatch, FailureReason
from subject_evolution.policy import Action, PolicyDecision
from subject_evolution.simulation import Simulation
from subject_evolution.social import build_share_relation_update_plan


def test_conflict_resolver_returns_a_plan_without_mutating_snapshot() -> None:
    cfg = load_config("configs/mvp_small.json")
    resolver = DeterministicActionConflictResolver(cfg)
    entity_id = np.asarray([30, 10, 20, 0], dtype=np.uint64)
    alive = np.asarray([True, True, True, False])
    energy = np.asarray([1.8, 1.0, 1.4, 0.0], dtype=np.float32)
    fertility = np.asarray([1.0, 1.0, 1.0, 0.0], dtype=np.float32)
    snapshot = ActionResolutionSnapshot(
        active=np.asarray([0, 1, 2], dtype=np.int32),
        cells=np.asarray([5, 1, 5], dtype=np.int32),
        entity_id=entity_id,
        alive=alive,
        energy=energy,
        fertility=fertility,
        primary_subject_id=np.asarray([300, 100, 200, 0], dtype=np.uint64),
        free_slot_count=0,
    )
    intents = ActionIntentBatch(
        intent_id=np.asarray([1, 2, 3], dtype=np.uint64),
        carrier_index=np.asarray([0, 1, 2], dtype=np.int32),
        carrier_id=entity_id[:3].copy(),
        action=np.asarray([Action.HARVEST, Action.HARVEST, Action.SHARE], dtype=np.int16),
        target_index=np.asarray([-1, -1, 1], dtype=np.int32),
        direction_x=np.zeros(3, dtype=np.float32),
        direction_y=np.zeros(3, dtype=np.float32),
        sampled_probability=np.ones(3, dtype=np.float32),
        submit_tick=7,
    )
    energy_before = energy.copy()
    allocation_calls: list[tuple[np.ndarray, np.ndarray]] = []

    def allocate(cells: np.ndarray, rates: np.ndarray) -> np.ndarray:
        allocation_calls.append((cells.copy(), rates.copy()))
        return np.full((cells.size, 4), 0.05, dtype=np.float32)

    plan = resolver.resolve(snapshot, intents, allocate)

    np.testing.assert_array_equal(energy, energy_before)
    np.testing.assert_array_equal(plan.harvest_rows, np.asarray([1, 0], dtype=np.int32))
    np.testing.assert_array_equal(allocation_calls[0][0], np.asarray([1, 5], dtype=np.int32))
    np.testing.assert_allclose(plan.resolutions.resource_delta[plan.harvest_rows], 0.05)
    np.testing.assert_array_equal(plan.share.rows, np.asarray([2], dtype=np.int32))
    assert plan.resolutions.success[2]
    assert plan.share.amounts[0] > 0.0
    assert plan.share.relation_updates.size == 2


def test_share_plan_filters_invalid_relation_targets_and_preserves_failure_reasons() -> None:
    cfg = load_config("configs/mvp_small.json")
    resolver = DeterministicActionConflictResolver(cfg)
    entity_id = np.arange(10, 15, dtype=np.uint64)
    snapshot = ActionResolutionSnapshot(
        active=np.arange(5, dtype=np.int32),
        cells=np.arange(5, dtype=np.int32),
        entity_id=entity_id,
        alive=np.ones(5, dtype=bool),
        energy=np.asarray([1.5, 4.9, 1.2, 1.0, 0.4], dtype=np.float32),
        fertility=np.ones(5, dtype=np.float32),
        primary_subject_id=np.arange(100, 105, dtype=np.uint64),
        free_slot_count=0,
    )
    intents = ActionIntentBatch(
        intent_id=np.arange(1, 6, dtype=np.uint64),
        carrier_index=np.arange(5, dtype=np.int32),
        carrier_id=entity_id.copy(),
        action=np.full(5, Action.SHARE, dtype=np.int16),
        target_index=np.asarray([1, -1, 99, 3, 0], dtype=np.int32),
        direction_x=np.zeros(5, dtype=np.float32),
        direction_y=np.zeros(5, dtype=np.float32),
        sampled_probability=np.ones(5, dtype=np.float32),
        submit_tick=9,
    )

    plan = resolver.resolve(
        snapshot,
        intents,
        lambda cells, rates: np.empty((0, 4), dtype=np.float32),
    )

    assert plan.resolutions.success[0]
    np.testing.assert_array_equal(
        plan.resolutions.failure_reason[1:],
        np.asarray(
            [
                FailureReason.INVALID_TARGET,
                FailureReason.INVALID_TARGET,
                FailureReason.INVALID_TARGET,
                FailureReason.INSUFFICIENT_RESOURCE,
            ],
            dtype=np.uint8,
        ),
    )
    relation_updates = plan.share.relation_updates
    np.testing.assert_array_equal(relation_updates.owner_indices, np.asarray([0, 1, 4]))
    np.testing.assert_array_equal(relation_updates.target_indices, np.asarray([1, 0, 0]))
    np.testing.assert_array_equal(relation_updates.source_rows, np.asarray([0, 0, 4]))
    np.testing.assert_array_equal(relation_updates.reciprocal, np.asarray([False, True, False]))


def test_reproduction_resolution_emits_stable_capacity_limited_birth_requests() -> None:
    cfg = load_config("configs/mvp_small.json")
    entity_id = np.asarray([40, 10, 30, 20], dtype=np.uint64)
    primary_subject_id = np.asarray([400, 100, 300, 200], dtype=np.uint64)
    snapshot = ActionResolutionSnapshot(
        active=np.arange(4, dtype=np.int32),
        cells=np.arange(4, dtype=np.int32),
        entity_id=entity_id,
        alive=np.ones(4, dtype=bool),
        energy=np.full(4, cfg.entities.reproduction_threshold + 1.0, dtype=np.float32),
        fertility=np.ones(4, dtype=np.float32),
        primary_subject_id=primary_subject_id,
        free_slot_count=2,
    )
    intents = ActionIntentBatch(
        intent_id=np.arange(1, 5, dtype=np.uint64),
        carrier_index=np.arange(4, dtype=np.int32),
        carrier_id=entity_id.copy(),
        action=np.full(4, Action.REPRODUCE, dtype=np.int16),
        target_index=np.full(4, -1, dtype=np.int32),
        direction_x=np.zeros(4, dtype=np.float32),
        direction_y=np.zeros(4, dtype=np.float32),
        sampled_probability=np.ones(4, dtype=np.float32),
        submit_tick=12,
    )

    plan = DeterministicActionConflictResolver(cfg).resolve(
        snapshot,
        intents,
        lambda cells, rates: np.empty((0, 4), dtype=np.float32),
    )

    births = plan.birth_requests
    np.testing.assert_array_equal(births.source_rows, np.asarray([1, 3], dtype=np.int32))
    np.testing.assert_array_equal(births.parent_indices, np.asarray([1, 3], dtype=np.int32))
    np.testing.assert_array_equal(births.parent_entity_ids, np.asarray([10, 20], dtype=np.uint64))
    np.testing.assert_array_equal(births.parent_subject_ids, np.asarray([100, 200], dtype=np.uint64))
    assert births.tick == 12
    np.testing.assert_array_equal(plan.resolutions.success, np.asarray([False, True, False, True]))
    np.testing.assert_array_equal(
        plan.resolutions.failure_reason[[0, 2]],
        np.asarray([FailureReason.INSUFFICIENT_CAPACITY] * 2, dtype=np.uint8),
    )


def test_simulation_accepts_a_pluggable_conflict_resolver(tmp_path) -> None:
    cfg = load_config("configs/mvp_small.json")

    class CountingResolver(DeterministicActionConflictResolver):
        calls = 0

        def resolve(self, *args, **kwargs):
            self.calls += 1
            return super().resolve(*args, **kwargs)

    resolver = CountingResolver(cfg)
    sim = Simulation(cfg, tmp_path / "custom-resolver", conflict_resolver=resolver)
    try:
        sim.step()
        assert resolver.calls == 1
    finally:
        sim.metrics.close()


def test_share_commit_consumes_only_the_explicit_plan(tmp_path) -> None:
    cfg = load_config("configs/mvp_small.json")
    sim = Simulation(cfg, tmp_path / "explicit-share-plan")
    rows = np.asarray([0], dtype=np.int32)
    owners = np.asarray([0], dtype=np.int32)
    targets = np.asarray([1], dtype=np.int32)
    success = np.asarray([True])
    relation_updates = build_share_relation_update_plan(
        cfg,
        rows=rows,
        owners=owners,
        targets=targets,
        success=success,
        eligible=np.asarray([True]),
        tick=0,
    )
    share = ShareResolution(
        rows=rows,
        owner_indices=owners,
        target_indices=targets,
        amounts=np.asarray([0.2], dtype=np.float32),
        success=success,
        valid_target=np.asarray([True]),
        relation_updates=relation_updates,
    )
    sim.entities.energy[:2] = 1.0
    sim.last_intents = None
    sim.last_resolutions = None
    try:
        committed = sim._commit_shares(share)

        assert np.isclose(committed, 0.2)
        np.testing.assert_allclose(sim.entities.energy[:2], np.asarray([0.8, 1.2]))
        assert 1 in sim.social.target[0]
        assert 0 in sim.social.target[1]
    finally:
        sim.metrics.close()


def test_simulation_commits_explicit_birth_and_death_plans(tmp_path) -> None:
    cfg = load_config("configs/mvp_small.json")
    sim = Simulation(cfg, tmp_path / "lifecycle-plans")
    active = np.flatnonzero(sim.entities.alive).astype(np.int32)
    parent = int(active[0])
    dying = int(active[1])
    sim.entities.energy[parent] = cfg.entities.reproduction_threshold + 1.0
    sim.entities.fertility[parent] = 1.0
    sim.entities.energy[dying] = 0.0
    dying_entity_id = int(sim.entities.entity_id[dying])
    dying_subject_id = int(sim.entities.primary_subject_id[dying])

    def lifecycle_actions(**kwargs):
        count = kwargs["active"].size
        action = np.full(count, Action.REST, dtype=np.int16)
        action[0] = Action.REPRODUCE
        return PolicyDecision(
            action=action,
            probability=np.ones(count, dtype=np.float32),
            entropy=np.zeros(count, dtype=np.float32),
            direction_x=np.zeros(count, dtype=np.float32),
            direction_y=np.zeros(count, dtype=np.float32),
            selected_partner=np.full(count, -1, dtype=np.int32),
            logits=np.zeros((count, len(Action)), dtype=np.float32),
        )

    sim.policy.decide = lifecycle_actions
    try:
        stats = sim.step()

        assert stats.births == 1
        assert sim.last_birth_allocation.size == 1
        newborn = int(sim.last_birth_allocation.slots[0])
        assert sim.entities.alive[newborn]
        assert sim.entities.entity_id[newborn] == sim.last_birth_allocation.offspring_entity_ids[0]
        assert stats.deaths >= 1
        death_position = np.flatnonzero(sim.last_death_events.entity_indices == dying)
        assert death_position.size == 1
        row = int(death_position[0])
        assert int(sim.last_death_events.entity_ids[row]) == dying_entity_id
        assert int(sim.last_death_events.primary_subject_ids[row]) == dying_subject_id
        assert not sim.entities.alive[dying]
    finally:
        sim.metrics.close()
