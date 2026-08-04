from __future__ import annotations

import json
from pathlib import Path

from se.analysis.subject_vm_stage3c42_activation_source import (
    _live_control_decomposition,
)


def _record(*, source: float, gate: float, status: str | None = None) -> dict[str, object]:
    edge = source * gate
    node = 0.75 + edge
    lineage = []
    if status is not None:
        lineage = [
            {
                "status_name": status,
                "source_event_id": 7,
                "applied_tick": 4,
                "rollback_due_tick": 9,
                "targets": [
                    {
                        "family_name": "edge-forward-gate",
                        "target_index": 0,
                        "pre_value": -1.5,
                        "post_value": gate,
                        "current_value": gate if status == "guarded-live-pending" else -1.5,
                    }
                ],
            }
        ]
    return {
        "subject_id": 1,
        "tick": 8,
        "event_id": 9,
        "entity_id": 1,
        "temporary_write_lineage": lineage,
        "node_activations": [
            {
                "node_index": 0,
                "operator_id": 0,
                "activation_clip_applied": False,
                "bias_value": 0.0,
                "input_contribution": 0.75,
                "node_value": node,
            }
        ],
        "edge_transmissions": [
            {
                "edge_index": 0,
                "source_node_index": 0,
                "target_node_index": 0,
                "delay": 1,
                "source_value": source,
                "forward_gate": gate,
                "bounded_contribution": edge,
                "bandwidth_clip_applied": False,
            }
        ],
        "output_contributions": [
            {
                "node_index": 0,
                "action_port": 0,
                "output_gate": 1.5,
                "float32_contribution": node * 1.5,
            }
        ],
    }


def test_rest_output_decomposition_splits_state_gate_and_interaction() -> None:
    result = _live_control_decomposition(
        _record(source=0.5, gate=-1.5, status="read-only-control-pending"),
        _record(source=0.6, gate=-1.4, status="guarded-live-pending"),
    )
    components = result["component_output_contributions"]
    assert abs(components["inherited_node_state"] - (-0.225)) < 1e-12
    assert abs(components["current_edge_gate"] - 0.075) < 1e-12
    assert abs(components["state_gate_interaction"] - 0.015) < 1e-12
    assert result["foreign_target_count"] == 0
    assert result["edge_forward_gate_target_count"] == 2
    assert result["absolute_reconstruction_error"] < 1e-12


def test_stage3c42_study_contract_is_frozen_before_trace() -> None:
    study = json.loads(
        Path("studies/d1z_subject_vm_stage3c42_activation_source_v1/study.json").read_text(
            encoding="utf-8"
        )
    )
    authorization = study["authorization"]
    assert authorization["selected_reference_seeds"] == [12305, 12307, 12308]
    assert authorization["selected_replication_seeds"] == [12401]
    assert authorization["events_per_source"] == 5
    assert authorization["new_source_panel"] is False
    assert authorization["thought_chain_implementation"] is False


def test_stage3c42_frozen_assessment_records_current_gate_only_did() -> None:
    assessment = json.loads(
        Path(
            "analyses/d1z_subject_vm_stage3c42_activation_source_v1/final/"
            "stage3c42_activation_source.json"
        ).read_text(encoding="utf-8")
    )
    findings = assessment["cross_panel_findings"]
    assert findings["all_rest_output_deltas_exactly_reconstructed"] is True
    assert findings["all_exposure_did_structural_contribution_is_current_edge_gate"] is True
    assert findings["maximum_abs_inherited_node_state_component"] == 0.0
    assert findings["maximum_abs_state_gate_interaction_component"] == 0.0
    assert findings["current_gate_component_alone_separates_crossing"] is False
    assert findings["noncrossing_current_gate_magnitude_can_exceed_crossing"] is True
    assert assessment["frozen_interpretation"]["source_history_origin_is_fully_resolved"] is False
    assert assessment["frozen_interpretation"]["thought_chain_implementation_authorized_in_this_stage"] is False


def test_stage3c42_decision_defers_thought_chain_to_next_project_boundary() -> None:
    decision = json.loads(
        Path(
            "protocols/decisions/subject_graph_vm_stage3c42_activation_source_v1.json"
        ).read_text(encoding="utf-8")
    )
    assert decision["observed_result"]["assessment_sha256"] == (
        "b9b4962b391bf92b26f02d91c5952eb9e8a38fe944782a1358749b09320e49e7"
    )
    assert decision["forbidden_changes"]["thought_chain_implementation"] is True
    assert decision["frozen_interpretation"]["thought_chain_implemented"] is False
    assert decision["frozen_interpretation"]["next_project_boundary"] == (
        "evolve-subject-unified-thought-event-chain-substrate"
    )
