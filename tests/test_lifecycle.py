import numpy as np
import pytest

from subject_evolution.config import load_config
from subject_evolution.lifecycle import (
    BirthRequestPlan,
    DeathCause,
    plan_birth_allocations,
    plan_death_events,
)
from subject_evolution.simulation import EntityState


def test_birth_allocation_plan_preserves_lifo_slots_without_mutating_pool() -> None:
    requests = BirthRequestPlan(
        source_rows=np.asarray([4, 1], dtype=np.int32),
        parent_indices=np.asarray([2, 0], dtype=np.int32),
        parent_entity_ids=np.asarray([30, 10], dtype=np.uint64),
        parent_subject_ids=np.asarray([300, 100], dtype=np.uint64),
        tick=7,
    )
    free_slots = np.asarray([9, 7, 5], dtype=np.int32)
    before = free_slots.copy()

    plan = plan_birth_allocations(
        requests,
        free_slots,
        next_entity_id=101,
        free_pool_version=12,
    )

    np.testing.assert_array_equal(free_slots, before)
    np.testing.assert_array_equal(plan.slots, np.asarray([5, 7], dtype=np.int32))
    np.testing.assert_array_equal(
        plan.offspring_entity_ids, np.asarray([101, 102], dtype=np.uint64)
    )
    assert plan.requests is requests
    assert plan.free_pool_version == 12


def test_empty_birth_allocation_preserves_saturated_capacity_provenance() -> None:
    requests = BirthRequestPlan(
        source_rows=np.empty(0, dtype=np.int32),
        parent_indices=np.empty(0, dtype=np.int32),
        parent_entity_ids=np.empty(0, dtype=np.uint64),
        parent_subject_ids=np.empty(0, dtype=np.uint64),
        tick=7,
        capacity_arbitration="stateless-random-v1",
        capacity_candidate_count=12,
        capacity_available_slots=0,
    )

    plan = plan_birth_allocations(
        requests,
        np.empty(0, dtype=np.int32),
        next_entity_id=101,
        free_pool_version=12,
    )

    assert plan.size == 0
    assert plan.requests is requests
    assert plan.requests.capacity_candidate_count == 12
    assert plan.requests.capacity_available_slots == 0


def test_entity_state_commits_birth_plan_once_and_rejects_stale_replay() -> None:
    cfg = load_config("configs/mvp_small.json")
    entities = EntityState(cfg)
    parents = np.asarray([0, 1], dtype=np.int32)
    entities.primary_subject_id[parents] = np.asarray([9001, 9002], dtype=np.uint64)
    requests = BirthRequestPlan(
        source_rows=np.asarray([2, 5], dtype=np.int32),
        parent_indices=parents,
        parent_entity_ids=entities.entity_id[parents].copy(),
        parent_subject_ids=entities.primary_subject_id[parents].copy(),
        tick=3,
    )
    plan = plan_birth_allocations(
        requests,
        np.asarray(entities.free_slots, dtype=np.int32),
        int(entities.next_entity_id),
        entities.free_slot_version,
    )
    free_before = len(entities.free_slots)

    accepted, newborns = entities.commit_births(plan, mutation_std=0.0)

    np.testing.assert_array_equal(accepted, parents)
    np.testing.assert_array_equal(newborns, plan.slots)
    np.testing.assert_array_equal(entities.entity_id[newborns], plan.offspring_entity_ids)
    np.testing.assert_array_equal(entities.lineage_id[newborns], entities.lineage_id[parents])
    assert len(entities.free_slots) == free_before - plan.size
    assert int(entities.next_entity_id) == int(plan.offspring_entity_ids[-1]) + 1
    assert entities.free_slot_version == plan.free_pool_version + 1
    with pytest.raises(ValueError, match="pool version is stale"):
        entities.commit_births(plan, mutation_std=0.0)


def test_entity_state_rejects_birth_plan_from_another_capacity_model() -> None:
    cfg = load_config("configs/mvp_small.json")
    entities = EntityState(cfg)
    parent = np.asarray([0], dtype=np.int32)
    entities.primary_subject_id[parent] = np.asarray([9001], dtype=np.uint64)
    requests = BirthRequestPlan(
        source_rows=np.asarray([0], dtype=np.int32),
        parent_indices=parent,
        parent_entity_ids=entities.entity_id[parent].copy(),
        parent_subject_ids=entities.primary_subject_id[parent].copy(),
        tick=3,
        capacity_arbitration="stable-id-v1",
        capacity_candidate_count=1,
        capacity_available_slots=1,
    )
    plan = plan_birth_allocations(
        requests,
        entities.free_slots,
        int(entities.next_entity_id),
        entities.free_slot_version,
    )

    with pytest.raises(ValueError, match="does not match world model rule"):
        entities.commit_births(plan, mutation_std=0.0)


def test_death_event_plan_records_composable_causes_before_slot_reclamation() -> None:
    cfg = load_config("configs/mvp_small.json")
    entities = EntityState(cfg)
    active = np.asarray([0, 1, 2, 3], dtype=np.int32)
    entities.primary_subject_id[active] = np.asarray([101, 102, 103, 104], dtype=np.uint64)
    entities.energy[0] = 0.0
    entities.integrity[1] = 0.0
    entities.energy[2] = 0.0
    entities.integrity[2] = -0.2
    entities.age[2] = cfg.entities.max_age

    plan = plan_death_events(
        active=active,
        entity_ids=entities.entity_id,
        primary_subject_ids=entities.primary_subject_id,
        energy=entities.energy,
        integrity=entities.integrity,
        age=entities.age,
        max_age=cfg.entities.max_age,
        tick=11,
    )

    np.testing.assert_array_equal(plan.entity_indices, np.asarray([0, 1, 2], dtype=np.int32))
    np.testing.assert_array_equal(plan.primary_subject_ids, np.asarray([101, 102, 103]))
    np.testing.assert_array_equal(
        plan.cause_code,
        np.asarray(
            [
                DeathCause.ENERGY_DEPLETED,
                DeathCause.INTEGRITY_DEPLETED,
                DeathCause.ENERGY_DEPLETED | DeathCause.INTEGRITY_DEPLETED | DeathCause.MAX_AGE,
            ],
            dtype=np.uint8,
        ),
    )
    assert np.all(entities.alive[plan.entity_indices])
    old_pool_size = len(entities.free_slots)

    committed = entities.commit_deaths(plan)

    np.testing.assert_array_equal(committed, plan.entity_indices)
    assert not np.any(entities.alive[committed])
    assert entities.free_slots[-3:] == [0, 1, 2]
    assert len(entities.free_slots) == old_pool_size + 3
    assert entities.free_slot_version == 1
    with pytest.raises(ValueError, match="occupancy"):
        entities.commit_deaths(plan)


def test_lifecycle_boundaries_reject_noncanonical_external_arrays() -> None:
    malformed_requests = BirthRequestPlan(
        source_rows=np.asarray([[0]], dtype=np.int32),
        parent_indices=np.asarray([0], dtype=np.int32),
        parent_entity_ids=np.asarray([1], dtype=np.uint64),
        parent_subject_ids=np.asarray([1], dtype=np.uint64),
        tick=0,
    )
    with pytest.raises(ValueError, match="one-dimensional"):
        plan_birth_allocations(malformed_requests, [3], next_entity_id=2)

    with pytest.raises(ValueError, match="slot ordered"):
        plan_death_events(
            active=np.asarray([1, 0], dtype=np.int32),
            entity_ids=np.asarray([1, 2], dtype=np.uint64),
            primary_subject_ids=np.asarray([10, 20], dtype=np.uint64),
            energy=np.zeros(2, dtype=np.float32),
            integrity=np.ones(2, dtype=np.float32),
            age=np.zeros(2, dtype=np.uint32),
            max_age=10,
            tick=1,
        )
