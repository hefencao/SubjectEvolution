from dataclasses import replace

import numpy as np
import pytest

from subject_evolution.config import load_config
from subject_evolution.device_state import build_entity_device_commit_plan
from subject_evolution.simulation import Simulation


def test_entity_device_commit_plan_captures_canonical_final_state(tmp_path) -> None:
    cfg = load_config("configs/mvp_small.json")
    sim = Simulation(cfg, tmp_path / "plan", backend="cpu")
    try:
        entity = sim.entities
        social = sim.social
        dynamic = np.asarray([3, 1, 3], dtype=np.int32)
        positions = np.asarray([2, 0], dtype=np.int32)
        lifecycle = np.asarray([5, 4], dtype=np.int32)
        social_rows = np.asarray([3, 1], dtype=np.int32)
        plan = build_entity_device_commit_plan(
            entity,
            social,
            dynamic_indices=dynamic,
            position_indices=positions,
            lifecycle_indices=lifecycle,
            social_indices=social_rows,
            base_version=7,
            tick=11,
        )

        np.testing.assert_array_equal(plan.dynamic_indices, np.asarray([1, 3]))
        np.testing.assert_array_equal(plan.position_indices, np.asarray([0, 2]))
        np.testing.assert_array_equal(plan.lifecycle_indices, np.asarray([4, 5]))
        np.testing.assert_array_equal(plan.social_indices, np.asarray([1, 3]))
        np.testing.assert_array_equal(plan.dynamic_energy, entity.energy[[1, 3]])
        np.testing.assert_array_equal(plan.dynamic_memory, entity.memory[[1, 3]])
        np.testing.assert_array_equal(plan.position_x, entity.x[[0, 2]])
        assert plan.base_version == 7
        assert plan.next_version == 8
        assert plan.tick == 11
        assert plan.semantic_transfer_nbytes == sum(
            value.nbytes
            for value in (
                plan.dynamic_indices,
                plan.dynamic_energy,
                plan.dynamic_integrity,
                plan.dynamic_fertility,
                plan.dynamic_memory,
                plan.dynamic_sensor_quality,
                plan.position_indices,
                plan.position_x,
                plan.position_y,
                plan.lifecycle_indices,
                plan.lifecycle_alive,
                plan.lifecycle_entity_ids,
                plan.lifecycle_genotype,
                plan.social_indices,
                plan.social_group_ids,
                plan.social_direction_x,
                plan.social_direction_y,
            )
        )

        malformed = replace(
            plan,
            position_indices=np.asarray([2, 1], dtype=np.int32),
        )
        with pytest.raises(ValueError, match="strictly ordered"):
            malformed.validate(entity.alive.size, entity.GENOTYPE_SIZE)

        dense = build_entity_device_commit_plan(
            entity,
            social,
            dynamic_indices=np.arange(entity.alive.size, dtype=np.int32),
            position_indices=np.arange(entity.alive.size, dtype=np.int32),
            lifecycle_indices=np.empty(0, dtype=np.int32),
            social_indices=np.arange(entity.alive.size, dtype=np.int32),
            base_version=8,
            tick=12,
        )
        dense.validate(entity.alive.size, entity.GENOTYPE_SIZE)
        assert dense.dynamic_full
        assert dense.position_full
        assert dense.social_full
        assert dense.dynamic_indices.size == 0
        assert dense.position_indices.size == 0
        assert dense.social_indices.size == 0
    finally:
        sim.metrics.close()
