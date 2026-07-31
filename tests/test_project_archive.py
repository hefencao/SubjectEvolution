from __future__ import annotations

from pathlib import Path
import zipfile

from scripts.package_project_archive import build_archive


def test_project_archive_prunes_iteration_history_only_in_copy(tmp_path: Path) -> None:
    output = tmp_path / "project.zip"
    report = build_archive(Path.cwd(), output)
    assert report["version"] == "0.94.0"
    assert (Path("docs/迭代") / "v0.94_D1-O_能力接入预算与有界后代投入.md").is_file()
    with zipfile.ZipFile(output) as archive:
        iteration = [
            name for name in archive.namelist() if "/docs/迭代/" in name
        ]
        assert len(iteration) == 1
        assert iteration[0].endswith("v0.94_D1-O_能力接入预算与有界后代投入.md")
        assert not any("/__pycache__/" in name for name in archive.namelist())
        assert not any(name.endswith(".pyc") for name in archive.namelist())
        assert not any(name.endswith("/.se-workspace.toml") for name in archive.namelist())
