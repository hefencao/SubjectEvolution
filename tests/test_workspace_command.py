from __future__ import annotations

import json
from pathlib import Path

import pytest

from se.cmd.study import main as study_main
from se.cmd.workspace import main as workspace_main
from se.workspace import (
    configure_patch_dir,
    configure_result_bundle_dir,
    configured_path,
    load_workspace_settings,
)


def _project(tmp_path: Path) -> Path:
    project = tmp_path / "project"
    (project / "studies").mkdir(parents=True)
    (project / "pyproject.toml").write_text(
        '[project]\nname = "example"\nversion = "0.0.0"\n', encoding="utf-8"
    )
    return project


def test_workspace_directories_are_external_and_preserve_each_other(tmp_path: Path) -> None:
    project = _project(tmp_path)
    results = tmp_path / "results"
    patches = tmp_path / "patches"
    configure_result_bundle_dir(project, results)
    settings = configure_patch_dir(project, patches)
    assert settings["result_bundle_dir"] == str(results.resolve())
    assert settings["patch_dir"] == str(patches.resolve())
    assert configured_path(project, "result") == results.resolve()
    assert configured_path(project, "patch") == patches.resolve()


def test_workspace_directories_cannot_be_inside_project(tmp_path: Path) -> None:
    project = _project(tmp_path)
    with pytest.raises(ValueError, match="result bundle directory must be outside"):
        configure_result_bundle_dir(project, project / "results")
    with pytest.raises(ValueError, match="patch directory must be outside"):
        configure_patch_dir(project, project / "patches")


def test_patch_only_workspace_does_not_enable_study_result_paths(tmp_path: Path) -> None:
    project = _project(tmp_path)
    configure_patch_dir(project, tmp_path / "patches")
    settings = load_workspace_settings(project)
    assert settings["configured"] is False
    assert settings["patch_dir_configured"] is True


def test_workspace_cli_owns_configuration_and_path_output(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    project = _project(tmp_path)
    monkeypatch.chdir(project)
    patches = tmp_path / "patches"
    workspace_main(["config", "--set-patch-dir", str(patches), "--json"])
    payload = json.loads(capsys.readouterr().out)
    assert payload["patch_dir"] == str(patches.resolve())

    workspace_main(["path", "patch"])
    assert capsys.readouterr().out.strip() == str(patches.resolve())


def test_study_cli_no_longer_owns_workspace_configuration(
    capsys: pytest.CaptureFixture[str],
) -> None:
    with pytest.raises(SystemExit) as exc:
        study_main(["config"])
    assert exc.value.code == 2
    assert "invalid choice" in capsys.readouterr().err
