from __future__ import annotations

import json
from pathlib import Path

from se.analysis.subject_vm_activation_contribution_trace_integrity import (
    SUBJECT_VM_ACTIVATION_CONTRIBUTION_TRACE_INTEGRITY_SCHEMA,
    verify_subject_vm_activation_contribution_trace,
)


def test_activation_contribution_integrity_covers_fresh_and_paired_runs(
    tmp_path: Path,
) -> None:
    result = verify_subject_vm_activation_contribution_trace(
        tmp_path / "integrity"
    )
    assert result["schema"] == SUBJECT_VM_ACTIVATION_CONTRIBUTION_TRACE_INTEGRITY_SCHEMA
    assert all(result["checks"].values())
    assert result["runtime_semantics_changed"] is False
    assert result["checkpoint_state_changed"] is False
    assert result["branch_identity_changed"] is False
    assert result["random_stream_consumed_by_trace"] is False
    assert result["stage3c42_authorized_next"] is True
    assert (
        result["paired_activation_traces"]["guarded-live"]
        ["temporary_write_entry_count"]
        > 0
    )


def test_activation_contribution_trace_decision_preserves_scientific_boundary() -> None:
    protocol = json.loads(
        Path(
            "protocols/decisions/subject_vm_activation_contribution_trace_v1.json"
        ).read_text(encoding="utf-8")
    )
    assert protocol["task_type"] == "ENGINEERING"
    assert protocol["activation"]["default_enabled"] is False
    assert protocol["runtime_contract"]["writer_reexecutes_graph"] is False
    assert protocol["runtime_contract"]["trace_payload_removed_from_checkpoint_and_clone_state"] is True
    assert protocol["integrity_gate"]["categorical_rng_trace_byte_identity_required"] is True
    assert protocol["scientific_boundary"]["stage3c42_must_be_read_only"] is True
    assert protocol["scientific_boundary"]["causal_attribution_from_trace_alone"] is False
    assert protocol["scientific_boundary"]["low_disturbance_action_authorized"] is False
