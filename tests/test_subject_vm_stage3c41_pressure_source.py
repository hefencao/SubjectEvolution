from __future__ import annotations

import json
from pathlib import Path

from se.analysis.subject_vm_stage3c41_pressure_source import _decompose_transition


def _event(
    *,
    action: int,
    draw: float,
    probabilities: list[float],
    logits: list[float | None],
) -> dict[str, object]:
    cdf=[]
    total=0.0
    for value in probabilities:
        total += value
        cdf.append(total)
    return {
        "action_id": action,
        "action_mask": [value is not None for value in logits],
        "masked_logits": logits,
        "probabilities": probabilities,
        "cumulative_probabilities": cdf,
        "uniform_draw": draw,
        "random_key_uint64": 77,
    }


def test_positive_rest_logit_moves_lower_boundary_toward_draw() -> None:
    horizon = _event(
        action=2,
        draw=0.55,
        probabilities=[0.2, 0.2, 0.3, 0.3, 0.0, 0.0, 0.0, 0.0],
        logits=[0.0, 0.0, 0.0, 0.0, None, None, None, None],
    )
    extended = _event(
        action=2,
        draw=0.55,
        probabilities=[0.3, 0.15, 0.25, 0.3, 0.0, 0.0, 0.0, 0.0],
        logits=[0.2, 0.0, 0.0, 0.0, None, None, None, None],
    )
    result = _decompose_transition(horizon, extended)
    assert result["changed_logit_action_ids"] == [0]
    assert result["extended_active_endpoint"] == "lower"
    assert abs(result["rest_probability_driver"] - 0.1) < 1e-12
    assert abs(result["active_endpoint_pressure"] - 0.05) < 1e-12


def test_negative_rest_logit_can_move_upper_boundary_toward_draw() -> None:
    horizon = _event(
        action=2,
        draw=0.69,
        probabilities=[0.3, 0.2, 0.2, 0.3, 0.0, 0.0, 0.0, 0.0],
        logits=[0.0, 0.0, 0.0, 0.0, None, None, None, None],
    )
    extended = _event(
        action=3,
        draw=0.69,
        probabilities=[0.2, 0.24, 0.24, 0.32, 0.0, 0.0, 0.0, 0.0],
        logits=[-0.2, 0.0, 0.0, 0.0, None, None, None, None],
    )
    result = _decompose_transition(horizon, extended)
    assert result["action_changed"] is True
    assert result["extended_active_endpoint"] == "upper"
    assert result["rest_probability_driver"] > 0
    assert result["other_action_net_cancellation_or_support"] < 0
    assert result["extended_same_action_signed_margin"] < 0


def test_stage3c41_protocol_preserves_read_only_boundary() -> None:
    path = Path("protocols/decisions/subject_graph_vm_stage3c41_pressure_source_v1.json")
    protocol = json.loads(path.read_text(encoding="utf-8"))
    assert protocol["input_contract"]["runtime_rerun_authorized"] is False
    assert protocol["forbidden_changes"]["post_hoc_scalar_classifier"] is True
    assert protocol["frozen_interpretation"]["rest_action_port_has_value_semantics"] is False
    assert protocol["frozen_interpretation"]["source_history_origin_of_rest_logit_change_is_resolved"] is False
