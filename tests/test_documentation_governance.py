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
    assert "## 10. Documentation boundaries" in text


def test_scientific_issues_is_active_registry_not_append_only_history() -> None:
    text = _text("docs/SCIENTIFIC_ISSUES.md")
    assert not re.search(r"^##\s+(?:v0\.\d+|Stage 3C-\d+)", text, re.MULTILINE)
    assert "## 2. Active issue registry" in text
    assert "SG-02" in text and "ENV-01" in text
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
    assert "[BRANCH-EXP]` must use an additional Git branch" in text
    assert "Do not write provisional" in text
    assert "Deliver only three top-level artifacts" in text
    assert "### 2.1 Git command delivery contract" in text
    assert "se-study config --set-patch-dir" in text
    assert 'git apply --index "$PATCH_DIR/<actual-baseline-to-current.patch>"' in text
    assert "Bootstrap iteration that introduces --set-patch-dir" in text
    assert "PYTHONPATH=src python -m se.cmd.study config --set-patch-dir" in text
    assert "persistent cross-chat command-format authority" in text
    assert "fast-forward merge" in text
    assert "annotated release tag" in text
    assert "main-exp/" in text and "docs/" in text


def test_frozen_stage_results_live_in_dedicated_ledger() -> None:
    text = _text("docs/results/SUBJECT_VM_STAGE3C_RESULTS.md")
    assert "| 3C-17 |" in text
    assert "| 3C-33 |" in text
    assert "| 3C-34 |" in text
    assert "| 3C-35 |" in text
    assert "Stage 3C-36 may compare" in text


def test_previous_active_docs_are_explicitly_non_normative_snapshots() -> None:
    for name in ("ARCHITECTURE.md", "SCIENTIFIC_ISSUES.md", "PROJECT_STATUS.md"):
        text = _text(f"docs/history/v0.147/{name}")
        assert text.startswith("# Historical v0.147 snapshot — non-normative")
        assert "Do not update or cite it as the current project contract" in text

def test_durable_governance_uses_non_overlapping_document_authority() -> None:
    text = _text("docs/PROJECT_GOVERNANCE.md")
    assert "## Documentation authority and typed-progress governance" in text
    assert "durable cross-version conclusions belong" not in text
    assert re.search(r"Frozen validated scientific\s+results belong in `docs/results/`", text)
