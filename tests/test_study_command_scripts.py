from __future__ import annotations

from pathlib import Path

from se.cmd.study import describe, load_workflow, resolve_step


def test_study_workflows_are_declarative_and_renderable() -> None:
    workflows = sorted(Path("studies").glob("*/workflow.toml"))
    assert workflows
    assert not list(Path("studies").glob("*/commands/*.sh"))
    for path in workflows:
        workflow_path, workflow = load_workflow(path)
        rendered = describe(workflow_path, workflow, None)
        assert rendered["steps"]
        for step in workflow["steps"]:
            command, values = resolve_step(workflow_path, workflow, step)
            assert command
            assert values["project_root"] == str(Path.cwd().resolve())


def test_workflow_parameters_are_explicitly_overridable() -> None:
    path, workflow = load_workflow(
        "studies/d1f_channel_selective_resource_sensing_v1"
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
