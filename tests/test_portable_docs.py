from pathlib import Path

from scripts.verify_portable_docs import verify


def test_portable_docs_rejects_absolute_execution_paths(tmp_path: Path) -> None:
    (tmp_path / "docs").mkdir()
    (tmp_path / "README.md").write_text("portable\n", encoding="utf-8")
    bad = tmp_path / "docs" / "report.md"
    bad.write_text("artifact: /mnt/data/work/result.json\n", encoding="utf-8")
    violations = verify(tmp_path)
    assert violations and violations[0].startswith("docs/report.md:1:")


def test_portable_docs_accepts_project_relative_paths(tmp_path: Path) -> None:
    (tmp_path / "docs").mkdir()
    (tmp_path / "README.md").write_text("portable\n", encoding="utf-8")
    (tmp_path / "docs" / "report.md").write_text(
        "artifact: studies/example/frozen/report.json\n", encoding="utf-8"
    )
    assert verify(tmp_path) == []


def test_portable_docs_rejects_delivery_environment_limitations(tmp_path: Path) -> None:
    (tmp_path / "docs").mkdir()
    (tmp_path / "README.md").write_text("portable\n", encoding="utf-8")
    (tmp_path / "docs" / "report.md").write_text(
        "The validation environment has no CUDA; 2 GPU-only tests were skipped.\n",
        encoding="utf-8",
    )
    assert verify(tmp_path)


def test_iteration_docs_use_dedicated_history_directory() -> None:
    iteration = Path("docs/迭代")
    assert iteration.is_dir()
    assert any(path.name.startswith("v0.95_") for path in iteration.iterdir())
    assert not any(Path("docs").glob("v0.*"))
    assert not [path for path in Path("docs").iterdir() if path.is_dir() and path.name.startswith("v0.")]
