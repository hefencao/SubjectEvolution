from __future__ import annotations

from pathlib import Path

import pytest

from se.cmd.study import (
    check_step_preconditions,
    configure_patch_dir,
    configure_result_bundle_dir,
    describe,
    load_workflow,
    load_workspace_settings,
    resolve_step,
)


def test_study_workflows_are_declarative_and_renderable() -> None:
    workflows = sorted(Path("studies").glob("*/workflow.toml"))
    assert workflows
    for workflow in workflows:
        assert not list(workflow.parent.glob("commands/*.sh"))
    for path in workflows:
        workflow_path, workflow = load_workflow(path)
        rendered = describe(workflow_path, workflow, None)
        assert rendered["steps"]
        for step in workflow["steps"]:
            command, values = resolve_step(
                workflow_path,
                workflow,
                step,
                allow_unconfigured_result=True,
            )
            assert command
            assert values["project_root"] == str(Path.cwd().resolve())


def test_workflow_parameters_are_explicitly_overridable() -> None:
    path, workflow = load_workflow(
        "studies/d1h_demand_gated_resource_sensing_v1"
    )
    command, values = resolve_step(
        path,
        workflow,
        "source-pilot",
        {"backend": "cpu", "seeds": "1,2", "checkpoint_tick": "90"},
    )
    assert values["backend"] == "cpu"
    assert values["seeds"] == "1,2"
    assert "cpu" in command
    assert "1,2" in command
    assert command.count("90") == 2


def _write_minimal_workflow(project: Path) -> Path:
    study = project / "studies" / "example"
    study.mkdir(parents=True)
    (project / "pyproject.toml").write_text(
        '[project]\nname = "example"\nversion = "0.0.0"\n', encoding="utf-8"
    )
    (study / "workflow.toml").write_text(
        '''schema = "se-study-workflow-v1"
study_id = "example"
title = "Example"

[parameters.output]
type = "result-path"
default = "example.zip"
description = "External result bundle."

[steps.pack-results]
description = "Pack."
command = ["python", "pack.py", "--output", "{output}"]
''',
        encoding="utf-8",
    )
    return study / "workflow.toml"


def test_result_bundle_path_requires_external_workspace_configuration(
    tmp_path: Path,
) -> None:
    project = tmp_path / "project"
    workflow_path = _write_minimal_workflow(project)
    path, workflow = load_workflow(workflow_path)
    with pytest.raises(ValueError, match="result bundle directory is not configured"):
        resolve_step(path, workflow, "pack-results")

    external = tmp_path / "results"
    settings = configure_result_bundle_dir(project, external)
    assert settings["configured"] is True
    assert load_workspace_settings(project)["result_bundle_dir"] == str(
        external.resolve()
    )
    command, values = resolve_step(path, workflow, "pack-results")
    assert values["output"] == str((external / "example.zip").resolve())
    assert command[-1] == values["output"]


def test_result_bundle_directory_cannot_be_inside_project(tmp_path: Path) -> None:
    project = tmp_path / "project"
    _write_minimal_workflow(project)
    with pytest.raises(ValueError, match="outside the project tree"):
        configure_result_bundle_dir(project, project / "results")



def test_patch_directory_is_external_and_preserves_result_setting(tmp_path: Path) -> None:
    project = tmp_path / "project"
    _write_minimal_workflow(project)
    results = tmp_path / "results"
    patches = tmp_path / "patches"
    configure_result_bundle_dir(project, results)
    settings = configure_patch_dir(project, patches)
    assert settings["result_bundle_configured"] is True
    assert settings["patch_dir_configured"] is True
    assert settings["result_bundle_dir"] == str(results.resolve())
    assert settings["patch_dir"] == str(patches.resolve())
    text = (project / ".se-workspace.toml").read_text(encoding="utf-8")
    assert "result_bundle_dir" in text
    assert "patch_dir" in text


def test_patch_directory_cannot_be_inside_project(tmp_path: Path) -> None:
    project = tmp_path / "project"
    _write_minimal_workflow(project)
    with pytest.raises(ValueError, match="patch directory must be outside"):
        configure_patch_dir(project, project / "patches")


def test_patch_only_workspace_does_not_enable_result_paths(tmp_path: Path) -> None:
    project = tmp_path / "project"
    workflow_path = _write_minimal_workflow(project)
    configure_patch_dir(project, tmp_path / "patches")
    settings = load_workspace_settings(project)
    assert settings["configured"] is False
    assert settings["patch_dir_configured"] is True
    path, workflow = load_workflow(workflow_path)
    with pytest.raises(ValueError, match="result bundle directory is not configured"):
        resolve_step(path, workflow, "pack-results")

def test_workflow_json_precondition_blocks_failed_source(tmp_path: Path) -> None:
    project = tmp_path / "project"
    workflow_path = _write_minimal_workflow(project)
    path, workflow = load_workflow(workflow_path)
    gate = project / "gate.json"
    gate.write_text('{"paired_plan_authorized": false}', encoding="utf-8")
    workflow["steps"]["pack-results"]["requires_json"] = [
        {
            "path": str(gate),
            "field": "paired_plan_authorized",
            "equals": True,
        }
    ]
    _, values = resolve_step(
        path, workflow, "pack-results", allow_unconfigured_result=True
    )
    with pytest.raises(ValueError, match="precondition failed"):
        check_step_preconditions(workflow["steps"]["pack-results"], values)

