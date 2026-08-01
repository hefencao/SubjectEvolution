from __future__ import annotations

from pathlib import Path
import zipfile

from scripts.package_project_archive import build_archive


def test_project_archive_prunes_iteration_history_only_in_copy(tmp_path: Path) -> None:
    project = tmp_path / "project"
    iteration = project / "docs" / "迭代"
    iteration.mkdir(parents=True)
    (project / "pyproject.toml").write_text(
        '[project]\nname = "subject-evolution"\nversion = "0.99.0"\n',
        encoding="utf-8",
    )
    current = iteration / "v0.99_current.md"
    legacy_file = iteration / "v0.98_legacy.md"
    legacy_dir = iteration / "v0.26"
    legacy_root_dir = project / "docs" / "v0.26"
    current.write_text("current\n", encoding="utf-8")
    legacy_file.write_text("legacy\n", encoding="utf-8")
    legacy_dir.mkdir()
    (legacy_dir / "README.md").write_text("legacy directory\n", encoding="utf-8")
    legacy_root_dir.mkdir()
    (legacy_root_dir / "README.md").write_text("legacy root directory\n", encoding="utf-8")

    output = tmp_path / "project.zip"
    report = build_archive(project, output)
    assert report["version"] == "0.99.0"
    assert current.is_file()
    assert legacy_file.is_file()
    assert (legacy_dir / "README.md").is_file()
    assert (legacy_root_dir / "README.md").is_file()

    with zipfile.ZipFile(output) as archive:
        iteration_entries = [
            name for name in archive.namelist() if "/docs/迭代/" in name
        ]
        assert iteration_entries == ["se_v099_project/docs/迭代/v0.99_current.md"]
        assert not any("/docs/v0.26/" in name for name in archive.namelist())
        assert not any("/__pycache__/" in name for name in archive.namelist())
        assert not any(name.endswith(".pyc") for name in archive.namelist())
        assert not any(name.endswith("/.se-workspace.toml") for name in archive.namelist())
