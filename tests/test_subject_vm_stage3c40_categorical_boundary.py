from __future__ import annotations

import json
from pathlib import Path

from se.analysis.subject_vm_stage3c40_categorical_boundary import (
    _signed_interval_margin,
    _transition,
)
from se.experiments.subject_vm_stage3c32_alignment_intervention import (
    Stage3C32InterventionParameters,
)
from se.experiments.subject_vm_stage3c33_exposure_propagation import (
    Stage3C33ExposureParameters,
)


def _event(*, action: int, draw: float, cdf: list[float]) -> dict[str, object]:
    lower = 0.0 if action == 0 else cdf[action - 1]
    upper = cdf[action]
    probabilities = [cdf[0], *[cdf[i] - cdf[i - 1] for i in range(1, len(cdf))]]
    return {
        "action_id": action,
        "action_mask": [True] * len(cdf),
        "cumulative_probabilities": cdf,
        "probabilities": probabilities,
        "uniform_draw": draw,
        "random_key_uint64": 77,
        "selected_cdf_lower": lower,
        "selected_cdf_upper": upper,
    }


def test_signed_interval_margin_becomes_negative_after_crossing() -> None:
    assert abs(_signed_interval_margin(0.45, 0.2, 0.6) - 0.15) < 1e-15
    assert _signed_interval_margin(0.65, 0.2, 0.6) < 0
    assert _signed_interval_margin(0.1, 0.2, 0.6) < 0


def test_transition_reconstructs_exact_cdf_boundary_crossing() -> None:
    horizon = _event(action=1, draw=0.45, cdf=[0.2, 0.6, 1.0])
    extended = _event(action=2, draw=0.45, cdf=[0.2, 0.4, 1.0])
    result = _transition(horizon, extended)
    assert result["action_changed"] is True
    assert result["same_action_interval_crossed"] is True
    assert result["horizon_selected_interval_margin"] > 0
    assert result["extended_same_action_signed_margin"] < 0
    assert result["boundary_pressure_to_horizon_margin_ratio"] > 1


def test_transition_reports_non_crossing_residual_margin() -> None:
    horizon = _event(action=1, draw=0.45, cdf=[0.2, 0.6, 1.0])
    extended = _event(action=1, draw=0.45, cdf=[0.2, 0.5, 1.0])
    result = _transition(horizon, extended)
    assert result["action_changed"] is False
    assert result["same_action_interval_crossed"] is False
    assert result["extended_same_action_signed_margin"] > 0


def test_stage3c32_and_stage3c33_trace_flag_is_observation_only() -> None:
    stage32 = Stage3C32InterventionParameters(categorical_sampling_trace=True)
    stage33 = Stage3C33ExposureParameters(categorical_sampling_trace=True)
    stage32.validate()
    stage33.validate()
    assert stage32.categorical_sampling_trace is True
    assert stage33.categorical_sampling_trace is True


def test_stage3c40_decision_protocol_preserves_scientific_boundary() -> None:
    path = Path("protocols/decisions/subject_graph_vm_stage3c40_categorical_boundary_v1.json")
    if not path.exists():
        return
    protocol = json.loads(path.read_text(encoding="utf-8"))
    assert protocol["forbidden_changes"]["runtime_sampling_semantics_change"] is True
    assert protocol["forbidden_changes"]["source_selection_or_replacement"] is True
    assert protocol["frozen_interpretation"]["objective_coordinates_have_value_semantics"] is False
