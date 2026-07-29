from __future__ import annotations

from se.analysis.d3_response_adequacy import build_adequacy_audit


def _row(tick: int, alive: int, eligible: float, moves: float, gain: float, cosine: float):
    return {
        "tick": tick,
        "alive": alive,
        "cumulative": {
            "eligible_entity_ticks": eligible,
            "resource_move_count": moves,
            "resource_move_support_gain_sum": gain,
            "resource_move_support_gain_positive": moves * 0.4,
            "resource_move_alignment_cosine_sum": cosine,
            "resource_move_alignment_cosine_count": moves,
        },
    }


def test_adequacy_audit_partitions_cumulative_trajectory_without_pseudoreplication() -> None:
    trajectory = [
        _row(0, 500, 0, 0, 0, 0),
        _row(300, 90, 50_000, 5_000, -5.0, -500.0),
        _row(600, 70, 70_000, 7_000, -7.0, -700.0),
    ]
    payload = {
        "schema": "d3-spatial-processing-response-results-v1",
        "audit_completeness": {"triplets": True, "ledgers": True},
        "pairs": [
            {
                "seed": 59001,
                "branches": [
                    {
                        "branch": "original-support",
                        "final": {
                            "alive": 70,
                            "births_total": 50,
                            "deaths_total": 480,
                            "lineages": 30,
                        },
                        "response_trajectory": trajectory,
                    }
                ],
            }
        ],
    }
    report = build_adequacy_audit(
        payload, block_ticks=300, min_alive=100, burn_in_ticks=300
    )
    branch = report["branches"][0]
    assert branch["blocks"][0]["eligible_entity_ticks"] == 50_000
    assert branch["blocks"][1]["eligible_entity_ticks"] == 20_000
    assert branch["initial_block_entity_tick_fraction"] == 5 / 7
    assert branch["first_observed_tick_below_min_alive"] == 300
    assert not branch["post_burn_in_population_supported"]
    assert report["summary"]["mechanism_audit_complete"]
    assert not report["summary"]["movement_events_are_independent_replicates"]
    assert not report["summary"]["population_supported_long_run_inference"]
