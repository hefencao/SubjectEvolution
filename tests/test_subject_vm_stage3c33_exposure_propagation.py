from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from se.analysis import subject_vm_stage3c33_exposure_propagation as analysis
from se.experiments.subject_vm_short_paired_study import _canonical_sha256
from se.experiments import subject_vm_stage3c33_exposure_propagation as experiment


def _signed(payload: dict[str, Any], field: str) -> dict[str, Any]:
    result = dict(payload)
    result[field] = _canonical_sha256(result)
    return result


def _source_signature() -> list[dict[str, Any]]:
    return [
        {
            "seed": 12301,
            "checkpoint_file_sha256": "file",
            "checkpoint_state_sha256": "state",
            "checkpoint_config_sha256": "config",
            "checkpoint_tick": 2,
        }
    ]


def test_stage3c33_parameters_predeclare_factor_isolation() -> None:
    parameters = experiment.Stage3C33ExposureParameters()
    parameters.validate()
    conditions = experiment._conditions(parameters)
    assert [(item.name, item.horizon_ticks, item.exposure_ticks) for item in conditions] == [
        ("frozen-baseline", 8, 3),
        ("horizon-control", 11, 3),
        ("extended-exposure", 11, 6),
    ]
    with pytest.raises(ValueError, match="extended exposure must exceed"):
        experiment.Stage3C33ExposureParameters(extended_exposure_ticks=3).validate()
    with pytest.raises(ValueError, match="common horizon must exceed"):
        experiment.Stage3C33ExposureParameters(common_horizon_ticks=6).validate()


def test_stage3c33_runner_reuses_identical_source_checkpoints(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls: list[tuple[int, int]] = []

    def fake_stage3c32(**kwargs: Any) -> dict[str, Any]:
        parameters = kwargs["parameters"]
        root = Path(kwargs["output_dir"])
        root.mkdir(parents=True)
        calls.append((parameters.horizon_ticks, parameters.rollback_after_ticks))
        report = _signed(
            {
                "schema": "se-subject-vm-stage3c32-alignment-intervention-study-v1",
                "source_identities": [
                    {
                        "seed": 12301,
                        "checkpoint": "/source.sechk",
                        "checkpoint_file_sha256": "file",
                        "checkpoint_state_sha256": "state",
                        "checkpoint_config_sha256": "config",
                        "checkpoint_tick": 2,
                    }
                ],
            },
            "study_sha256",
        )
        (root / "study_report.json").write_text(json.dumps(report), encoding="utf-8")
        return report

    monkeypatch.setattr(
        experiment, "run_stage3c32_alignment_intervention", fake_stage3c32
    )
    result = experiment.run_stage3c33_exposure_propagation(
        rank2_study_report=tmp_path / "rank2.json",
        stage3c31_assessment=tmp_path / "stage3c31.json",
        output_dir=tmp_path / "stage3c33",
    )
    assert calls == [(8, 3), (11, 3), (11, 6)]
    assert result["shared_source_checkpoint_across_all_twelve_arms"] is True
    assert result["adaptive_exposure_extension"] is False
    assert set(result["conditions"]) == {
        "frozen-baseline",
        "horizon-control",
        "extended-exposure",
    }


def _source(seed: int, value: float) -> dict[str, Any]:
    vector = [value] + [0.0] * 20
    return {
        "seed": seed,
        "source_checkpoint_state_sha256": f"state-{seed}",
        "manipulation": {
            "changed_association_identity_fraction": 0.5,
            "changed_update_route_fraction": 0.25,
            "changed_bounded_delta_count": 4,
        },
        "aligned": {"paired_window_count": 2},
        "alignment_ablated": {"paired_window_count": 2},
        "cross_mode_ablation_minus_aligned_live_control_effect": {
            "fact_sum": vector,
            "fact_abs_sum": vector,
            "count_difference": [value, 0.0, 0.0],
        },
    }


def _assessment(value: float) -> dict[str, Any]:
    sources = [_source(12301, value), _source(12302, value)]
    return {
        "schema": analysis.STAGE3C32_ALIGNMENT_INTERVENTION_ASSESSMENT_SCHEMA,
        "source_level_independent_replication_count": 2,
        "per_source": sources,
        "cross_source_findings": {
            "sources_with_nonzero_componentwise_live_control_effect": int(value != 0.0) * 2,
            "stable_fact_sum_coordinate_count": int(value != 0.0),
            "stable_fact_abs_sum_coordinate_count": int(value != 0.0),
            "selector_identity_change_fraction_statistics": {"median": 0.5},
            "update_route_change_fraction_statistics": {"median": 0.25},
            "changed_bounded_delta_count_statistics": {"median": 4.0},
            "aligned_total_paired_window_count": 4,
            "alignment_ablated_total_paired_window_count": 4,
            "manipulation_integrity_passes_in_all_sources": True,
            "compute_and_storage_costs_match_in_all_sources": True,
            "forced_rollback_restores_graph_parameters_in_all_sources": True,
        },
    }



def _trajectory(value: float) -> dict[str, Any]:
    sources = [_source(12301, value), _source(12302, value)]
    nonzero = [12301, 12302] if value != 0.0 else []
    return {
        "per_source": sources,
        "cross_source_findings": {
            "source_count": 2,
            "nonzero_cross_mode_fact_sum_source_count": len(nonzero),
            "nonzero_cross_mode_fact_sum_source_seeds": nonzero,
            "stable_fact_sum_coordinate_count": int(value != 0.0),
            "stable_fact_abs_sum_coordinate_count": int(value != 0.0),
            "componentwise": {},
        },
    }

def test_stage3c33_assessment_separates_horizon_and_exposure_contrasts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    values = {
        (8, 3): 0.0,
        (11, 3): 1.0,
        (11, 6): 3.0,
    }
    conditions: dict[str, dict[str, Any]] = {}
    signature = _source_signature()
    for name, pair in {
        "frozen-baseline": (8, 3),
        "horizon-control": (11, 3),
        "extended-exposure": (11, 6),
    }.items():
        nested = _signed(
            {
                "schema": "se-subject-vm-stage3c32-alignment-intervention-study-v1",
                "parameters": {
                    "horizon_ticks": pair[0],
                    "rollback_after_ticks": pair[1],
                    "backend": "cpu",
                },
                "modes": {
                    mode: {
                        "seed_records": [
                            {
                                "seed": 12301,
                                "read_only_control_checkpoint": "unused",
                                "guarded_live_checkpoint": "unused",
                            }
                        ]
                    }
                    for mode in ("aligned", "alignment-ablated")
                },
            },
            "study_sha256",
        )
        path = tmp_path / f"{name}.json"
        path.write_text(json.dumps(nested), encoding="utf-8")
        conditions[name] = {
            "horizon_ticks": pair[0],
            "exposure_ticks": pair[1],
            "study_report": str(path),
            "study_sha256": nested["study_sha256"],
            "source_signature": signature,
        }

    parent = _signed(
        {
            "schema": experiment.STAGE3C33_EXPOSURE_PROPAGATION_STUDY_SCHEMA,
            "parameters": {
                "frozen_baseline_horizon_ticks": 8,
                "common_horizon_ticks": 11,
                "baseline_exposure_ticks": 3,
                "extended_exposure_ticks": 6,
                "backend": "cpu",
            },
            "conditions": conditions,
            "adaptive_exposure_extension": False,
            "permanent_parameter_retention_authorized": False,
        },
        "study_sha256",
    )

    monkeypatch.setattr(
        analysis,
        "assess_stage3c32_alignment_intervention",
        lambda nested: values[
            (
                int(nested["parameters"]["horizon_ticks"]),
                int(nested["parameters"]["rollback_after_ticks"]),
            )
        ]
        and _assessment(
            values[
                (
                    int(nested["parameters"]["horizon_ticks"]),
                    int(nested["parameters"]["rollback_after_ticks"]),
                )
            ]
        )
        or _assessment(0.0),
    )
    monkeypatch.setattr(
        analysis,
        "_compare_control_behavior",
        lambda *_: {"control_behavior_semantically_identical": True},
    )
    monkeypatch.setattr(
        analysis,
        "_compare_exposure_dose",
        lambda *_, **__: {
            "valid_entry_identity_equal": True,
            "committed_transaction_count_equal": True,
            "committed_target_count_equal": True,
            "baseline_duration_matches_declaration": True,
            "extended_duration_matches_declaration": True,
            "target_tick_exposure_matches_declared_ratio": True,
        },
    )
    monkeypatch.setattr(
        analysis,
        "_paired_window_diagnostic",
        lambda *_, horizon_contrast, exposure_contrast, **__: {
            "observation_tick_values": [1],
            "common_horizon_pair_support_matches_in_all_sources_and_modes": False,
            "valid_for_primary_exposure_propagation_inference": False,
            "horizon_only_contrast": horizon_contrast,
            "exposure_only_contrast": exposure_contrast,
        },
    )
    trajectory_values = {(11, 3): 1.0, (11, 6): 3.0}
    monkeypatch.setattr(
        analysis,
        "_trajectory_condition",
        lambda nested: _trajectory(
            trajectory_values[
                (
                    int(nested["parameters"]["horizon_ticks"]),
                    int(nested["parameters"]["rollback_after_ticks"]),
                )
            ]
        ),
    )
    monkeypatch.setattr(
        analysis,
        "_common_horizon_trajectory_support",
        lambda *_: {"comparisons": [], "all_support_matches": True},
    )

    result = analysis.assess_stage3c33_exposure_propagation(parent)
    assert result["paired_window_diagnostic"]["horizon_only_contrast"][
        "per_source"
    ][0]["fact_sum"][0] == 1.0
    assert result["paired_window_diagnostic"]["exposure_only_contrast"][
        "per_source"
    ][0]["fact_sum"][0] == 2.0
    assert result["fixed_common_horizon_trajectory"]["exposure_only_contrast"][
        "per_source"
    ][0]["fact_sum"][0] == 2.0
    assert result["cross_source_findings"][
        "paired_window_estimator_valid_for_primary_exposure_inference"
    ] is False
    assert result["diagnostic_interpretation"][
        "fixed_common_horizon_trajectory_is_valid_primary_estimator"
    ] is True
    assert result["cross_source_findings"][
        "common_horizon_read_only_controls_are_identical"
    ] is True
    assert result["permanent_parameter_retention_authorized"] is False


def test_stage3c33_fixed_trajectory_balances_stable_subjects(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import numpy as np

    shape = (2, 2)
    base = {
        "event_valid": np.ones(shape, dtype=bool),
        "subject_id": np.asarray([[101, 101], [202, 202]], dtype=np.int64),
        "event_tick": np.asarray([[4, 5], [4, 5]], dtype=np.int64),
        "event_id": np.asarray([[1, 2], [3, 4]], dtype=np.int64),
        "objective_delta": np.zeros((*shape, 12), dtype=np.float32),
        "resolution_resource_delta": np.zeros((*shape, 4), dtype=np.float32),
        "resolution_internal_resource_delta": np.zeros(
            (*shape, 4), dtype=np.float32
        ),
        "resolution_energy_cost": np.zeros(shape, dtype=np.float32),
        "success": np.zeros(shape, dtype=bool),
    }
    control = {name: np.array(value, copy=True) for name, value in base.items()}
    live = {name: np.array(value, copy=True) for name, value in base.items()}
    live["objective_delta"][0, :, 0] = 1.0
    live["objective_delta"][1, :, 0] = 2.0
    live["success"][0, 0] = True
    runtimes = {
        "live": {"trace_storage": {"arrays": live}},
        "control": {"trace_storage": {"arrays": control}},
    }
    monkeypatch.setattr(
        analysis,
        "_read_checkpoint",
        lambda path: ({"tick": 13}, runtimes[str(path)]),
    )

    result = analysis._trajectory_live_control_source("live", "control")
    assert result["event_count"] == 4
    assert result["stable_subject_count"] == 2
    assert result["minimum_event_tick"] == 4
    assert result["maximum_event_tick"] == 5
    # Sum events within subject: 2 and 4; then balance subjects: 3.
    assert result["subject_balanced_trajectory_fact_sum_difference"][0] == 3.0
    # One additional success in subject 101, then subject-balance: 0.5.
    assert result["subject_balanced_trajectory_count_difference"].tolist() == [
        0.0,
        0.5,
        -0.5,
    ]
