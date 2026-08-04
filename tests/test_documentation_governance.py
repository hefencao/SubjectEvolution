from __future__ import annotations

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _text(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def test_active_architecture_is_current_contract_not_version_diary() -> None:
    text = _text("docs/ARCHITECTURE.md")
    assert "implemented in v0." not in text
    assert not re.search(r"^#{2,4}\s+(?:v0\.\d+|Stage 3C-\d+)", text, re.MULTILINE)
    assert len(text.splitlines()) < 500
    assert "## 10. 文档边界" in text


def test_scientific_issues_is_active_registry_not_append_only_history() -> None:
    text = _text("docs/SCIENTIFIC_ISSUES.md")
    assert not re.search(r"^##\s+(?:v0\.\d+|Stage 3C-\d+)", text, re.MULTILINE)
    assert "## 2. 活动问题注册表" in text
    assert "SG-09" in text and "SG-10" in text and "ENV-01" in text
    assert len(text.splitlines()) < 350


def test_project_status_has_typed_tree_without_stage_result_sections() -> None:
    text = _text("docs/PROJECT_STATUS.md")
    for tag in (
        "[MAIN-EXP]",
        "[BRANCH-EXP]",
        "[PARAM-EXP]",
        "[EVOLVE-ENV]",
        "[EVOLVE-SUBJECT]",
        "[ENGINEERING]",
        "[DOC-GOV]",
    ):
        assert tag in text
    assert not re.search(r"^##\s+Stage 3C-\d+", text, re.MULTILINE)
    assert "Test and release-freshness boundary" not in text
    assert len(text.splitlines()) < 220


def test_agents_enforces_git_title_branch_and_document_placement() -> None:
    text = _text("AGENTS.md")
    for tag in (
        "[MAIN-EXP]",
        "[BRANCH-EXP]",
        "[PARAM-EXP]",
        "[EVOLVE-ENV]",
        "[EVOLVE-SUBJECT]",
        "[DOC-GOV]",
    ):
        assert tag in text
    assert "`[BRANCH-EXP]` 必须使用额外 Git 分支" in text
    assert "不得把暂定结果" in text
    assert "项目使命与解释边界" in text
    assert "当前 Subject Graph VM 机制合同" in text
    assert "docs/WORKFLOW_PROFILES.md" in text
    assert "不要求每次修改都执行完整发布流程" in text
    assert "se-workspace path patch" in text
    assert "se-study config --set-patch-dir" not in text
    assert "\nPATCH_DIR=" not in text
    assert "新聊天中 Git 命令格式的长期权威规则" in text
    assert "main-exp/" in text and "docs/" in text
    assert "## 6. Release gate" not in text


def test_workflow_profiles_separate_small_fixes_from_release_handoffs() -> None:
    text = _text("docs/WORKFLOW_PROFILES.md")
    for profile in (
        "SCOPED-FIX",
        "STANDARD-CODE",
        "SCIENTIFIC-FREEZE",
        "RELEASE-HANDOFF",
    ):
        assert profile in text
    assert "默认不要求" in text
    assert "全量测试分片" in text
    assert "补丁重放" in text
    assert "不会自动判断" in text


def test_frozen_stage_results_live_in_dedicated_ledger() -> None:
    text = _text("docs/results/SUBJECT_VM_STAGE3C_RESULTS.md")
    assert "| 3C-17 |" in text
    assert "| 3C-33 |" in text
    assert "| 3C-34 |" in text
    assert "| 3C-35 |" in text
    assert "| 3C-36 |" in text
    assert "| 3C-37 |" in text
    assert "| 3C-38 |" in text
    assert "| 3C-39 |" in text
    assert "| 3C-40 |" in text
    assert "| 3C-41 |" in text
    assert "| 3C-42 |" in text


def test_project_charter_is_durable_and_not_current_status() -> None:
    text = _text("docs/PROJECT_CHARTER.md")
    assert "## 1. 项目使命" in text
    assert "## 12. 文档权威" in text
    assert "当前项目状态" not in text
    assert "探索阶段至少 10 个" not in text
    assert "核心条件至少 30 个" not in text
    assert not re.search(r"^##\s+(?:v0\.\d+|Stage 3C-\d+)", text, re.MULTILINE)
    assert len(text.splitlines()) < 500


def test_project_governance_is_cross_version_contract_not_version_diary() -> None:
    text = _text("docs/PROJECT_GOVERNANCE.md")
    assert "## 1. 每轮治理检查" in text
    assert "## 11. 文档权威" in text
    assert not re.search(r"^##\s+v0\.\d+", text, re.MULTILINE)
    assert "已冻结且验证的科学结果" in text
    assert len(text.splitlines()) < 400


def test_subject_vm_document_is_current_contract_not_stage_diary() -> None:
    text = _text("docs/PARTITIONED_SUBJECT_GRAPH_VM.md")
    assert "## 1. 架构决策" in text
    assert "## 13. 当前能力边界" in text
    assert not re.search(r"^##\s+(?:v0\.\d+|Stage 3C-\d+)", text, re.MULTILINE)
    assert "docs/results/SUBJECT_VM_STAGE3C_RESULTS.md" in text
    assert "runtime score comparator 是 selection semantics 的唯一权威" in text
    assert len(text.splitlines()) < 500


def test_active_normative_documents_are_chinese_authoritative() -> None:
    required_markers = {
        "AGENTS.md": ("本文档适用于", "中文是活动规范文档的权威解释语言"),
        "docs/PROJECT_CHARTER.md": ("项目宪章", "项目使命"),
        "docs/PROJECT_GOVERNANCE.md": ("项目治理规则", "每轮治理检查"),
        "docs/ARCHITECTURE.md": ("当前架构", "职责与权威"),
        "docs/PARTITIONED_SUBJECT_GRAPH_VM.md": ("分区式 Subject Graph VM", "当前机制合同"),
        "docs/THOUGHT_EVENT_LANGUAGE_COGNITION.md": ("ThoughtEvent、思维链与语言认知研究合同", "成本约束编码同态假设"),
        "docs/PROJECT_STATUS.md": ("当前项目状态", "类型化任务进度树"),
        "docs/SCIENTIFIC_ISSUES.md": ("当前科学问题", "活动问题注册表"),
        "docs/WORKFLOW_PROFILES.md": ("工作流档位", "档位选择"),
        "docs/results/SUBJECT_VM_STAGE3C_RESULTS.md": ("冻结结果台账", "当前冻结链"),
        "docs/results/THOUGHT_EVENT_RESULTS.md": ("ThoughtEvent 冻结结果台账", "T2：前向 recall 前退化审计"),
    }
    for relative, markers in required_markers.items():
        text = _text(relative)
        for marker in markers:
            assert marker in text, (relative, marker)


def test_thought_event_language_contract_is_chinese_and_non_runtime() -> None:
    text = _text("docs/THOUGHT_EVENT_LANGUAGE_COGNITION.md")
    for marker in (
        "统一 ThoughtEvent",
        "成本约束编码同态假设",
        "跨 seed/区域",
        "communication interface",
        "不增加独立 `RETHINK`",
    ):
        assert marker in text
    assert "状态：**T2 前向 recall 前退化审计已冻结；T3 仅获最小机制 smoke 资格，语言与通信仍未实现**" in text
    assert len(text.splitlines()) < 600


def test_v0153_core_contract_snapshots_are_non_normative() -> None:
    for name in (
        "PROJECT_CHARTER.md",
        "PROJECT_GOVERNANCE.md",
        "PARTITIONED_SUBJECT_GRAPH_VM.md",
    ):
        text = _text(f"docs/history/v0.153/{name}")
        assert text.startswith("# Historical v0.153 snapshot — non-normative")
        assert "Do not update or cite it as the current project contract" in text


def test_previous_active_docs_are_explicitly_non_normative_snapshots() -> None:
    for name in ("ARCHITECTURE.md", "SCIENTIFIC_ISSUES.md", "PROJECT_STATUS.md"):
        text = _text(f"docs/history/v0.147/{name}")
        assert text.startswith("# Historical v0.147 snapshot — non-normative")
        assert "Do not update or cite it as the current project contract" in text


def test_durable_governance_uses_non_overlapping_document_authority() -> None:
    text = _text("docs/PROJECT_GOVERNANCE.md")
    assert "## 11. 文档权威" in text
    assert "durable cross-version conclusions belong" not in text
    assert "| 已冻结且验证的科学结果 | `docs/results/` |" in text
