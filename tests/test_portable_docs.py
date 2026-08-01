from pathlib import Path
import tomllib

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


def test_current_iteration_doc_uses_dedicated_history_directory() -> None:
    metadata = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))
    major, minor, *_ = str(metadata["project"]["version"]).split(".")
    current_prefix = f"v{major}.{minor}_"
    iteration = Path("docs/迭代")
    assert iteration.is_dir()
    assert any(path.name.startswith(current_prefix) for path in iteration.iterdir())
    # Local projects may retain historical material, including legacy layouts.
    # Only the current version is required to use the canonical directory.
    assert not list(Path("docs").glob(f"{current_prefix}*"))
