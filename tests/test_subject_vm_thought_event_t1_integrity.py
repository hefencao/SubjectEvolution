from __future__ import annotations

import hashlib
import json
from pathlib import Path

from se.analysis.subject_vm_thought_event_t1_integrity import verify


def test_thought_event_t1_integrity_and_protocol_checksum(tmp_path: Path) -> None:
    output = tmp_path / "integrity.json"
    report = verify(output)
    assert report["passed"] is True
    assert report["action_potential_identity"] is True
    assert report["authoritative_graph_state_identity"] is True
    assert report["legacy_trace_state_identity"] is True
    assert report["forward_recall_enabled"] is False
    assert report["parent_count_for_runtime_t1"] == 0
    protocol = json.loads(
        Path("protocols/decisions/subject_vm_thought_event_t1_v1.json").read_text(
            encoding="utf-8"
        )
    )
    assert (
        protocol["integrity_gate"]["integrity_assessment_sha256"]
        == report["assessment_sha256"]
    )


def test_epoch_contract_marks_t1_implemented_and_t2_next() -> None:
    epoch = json.loads(
        Path("protocols/epochs/subject_graph_vm_v1.json").read_text(encoding="utf-8")
    )
    assert epoch["project_version"] == "0.164.0"
    assert epoch["current_stage"] == "ThoughtEvent-T1"
    assert epoch["thought_event_t1_contract"]["forward_recall"] is False
    design = epoch["thought_event_language_design_contract"]
    assert design["t1_unified_arena_implemented"] is True
    assert design["next_implementation_stage"].startswith("T2-")


def test_t1_documentation_keeps_language_and_recall_blocked() -> None:
    text = Path("docs/THOUGHT_EVENT_LANGUAGE_COGNITION.md").read_text(
        encoding="utf-8"
    )
    assert "T1 统一 ThoughtEvent 基础设施已实现" in text
    assert "T2 只读退化审计" in text
    assert "不接入前向 recall" in text
    assert "communication interface" in text
