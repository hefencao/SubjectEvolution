from __future__ import annotations

from pathlib import Path
import zipfile

from scripts.package_project_archive import build_archive


def test_project_archive_prunes_iteration_history_only_in_copy(tmp_path: Path) -> None:
    output = tmp_path / "project.zip"
    report = build_archive(Path.cwd(), output)
    assert report["version"] == "0.89.0"
    assert (Path("docs/迭代") / "v0.89_D1-J_固定总量的可遗传四资源储存分配.md").is_file()
    with zipfile.ZipFile(output) as archive:
        iteration = [
            name for name in archive.namelist() if "/docs/迭代/" in name
        ]
        assert len(iteration) == 1
        assert iteration[0].endswith("v0.89_D1-J_固定总量的可遗传四资源储存分配.md")
        assert not any("/__pycache__/" in name for name in archive.namelist())
        assert not any(name.endswith(".pyc") for name in archive.namelist())
        assert not any(name.endswith("/.se-workspace.toml") for name in archive.namelist())
