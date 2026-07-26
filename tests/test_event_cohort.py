from __future__ import annotations

import numpy as np

from subject_evolution.event_cohort import EventCohortDiagnostics, SCHEMA


def test_event_cohort_endpoint_decomposition_is_exact() -> None:
    tracker = EventCohortDiagnostics(
        [
            {
                "anchor_id": "a",
                "region_id": 0,
                "event_tick": 10,
                "until_tick": 20,
            }
        ],
        world_width=10.0,
        world_height=10.0,
        regions_x=2,
        regions_y=1,
    )
    # Event region 0 contains IDs 1,2,3. ID 4 exists in region 1.
    tracker.observe(
        tick=10,
        alive=np.array([True, True, True, True, False]),
        stable_ids=np.array([1, 2, 3, 4, 0], dtype=np.uint64),
        x=np.array([1.0, 2.0, 3.0, 8.0, 0.0]),
        y=np.zeros(5),
    )
    # At the horizon: 1 retained; 2 survived outside; 3 is absent; 4 moved in;
    # 5 was born after the event and is alive in the region.
    tracker.observe(
        tick=20,
        alive=np.array([True, True, False, True, True]),
        stable_ids=np.array([1, 2, 3, 4, 5], dtype=np.uint64),
        x=np.array([1.0, 8.0, 3.0, 2.0, 4.0]),
        y=np.zeros(5),
    )
    tracker.validate_complete()
    summary = tracker.summaries()["a"]
    assert summary["event_cohort_schema"] == SCHEMA
    assert summary["event_alive_region"] == 3
    assert summary["final_alive_region_from_cohort_audit"] == 3
    assert summary["final_event_cohort_retained_region"] == 1
    assert summary["final_event_cohort_survived_outside_region"] == 1
    assert summary["final_event_cohort_absent"] == 1
    assert summary["final_existing_in_migrants_region"] == 1
    assert summary["final_post_event_born_region"] == 1
    assert summary["endpoint_population_change_region"] == 0
    assert summary["endpoint_population_change_reconstructed"] == 0
    assert summary["endpoint_population_balance_residual"] == 0
