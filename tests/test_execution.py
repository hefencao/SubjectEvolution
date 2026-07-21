import numpy as np

from subject_evolution.config import load_config
from subject_evolution.execution import (
    ActionResolutionSnapshot,
    DeterministicActionConflictResolver,
)
from subject_evolution.intents import ActionIntentBatch
from subject_evolution.policy import Action
from subject_evolution.simulation import Simulation


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
    np.testing.assert_array_equal(plan.share_rows, np.asarray([2], dtype=np.int32))
    assert plan.resolutions.success[2]
    assert plan.shared[0] > 0.0


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
