from __future__ import annotations

import json
from pathlib import Path

from se.experiments.local_event_counterfactual import detect_local_events


def test_detect_local_events_selects_region_specific_peaks() -> None:
    records = []
    for index in range(10):
        records.append(
            {
                "tick": (index + 1) * 30,
                "spatial_local_region_resource_scarcity": [
                    0.2 + (0.5 if index == 5 else 0.0),
                    0.3 + (0.4 if index == 7 else 0.0),
                ],
            }
        )
    events = detect_local_events(
        records, event_kind="scarcity", quantile=0.75, max_events=2
    )
    assert len(events) == 2
    assert {item[1] for item in events} == {0, 1}
    assert {records[item[0]]["tick"] for item in events} == {180, 240}
