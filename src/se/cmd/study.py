"""Declarative, parameterized study workflow runner.

Study workflows are data files rather than executable shell scripts.  The
runner validates declared parameters, renders the exact argv vector, and uses
``subprocess`` without a shell.  This keeps every operation inspectable while
allowing callers to override registered parameters explicitly.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import shlex
import subprocess
import sys
import tomllib
from typing import Any

WORKFLOW_SCHEMA = "se-study-workflow-v1"
WORKSPACE_SCHEMA = "se-workspace-v1"
WORKSPACE_CONFIG_NAME = ".se-workspace.toml"




def _project_root_from_workflow(workflow_path: Path) -> Path:
    return workflow_path.parent.parent.parent.resolve()


def _find_project_root(start: str | Path = ".") -> Path:
    current = Path(start).resolve()
    for candidate in (current, *current.parents):
        if (candidate / "pyproject.toml").is_file() and (candidate / "studies").is_dir():
            return candidate
    raise FileNotFoundError(f"could not locate project root from {current}")


def _workspace_config_path(project_root: Path) -> Path:
    return project_root / WORKSPACE_CONFIG_NAME


def load_workspace_settings(project_root: str | Path) -> dict[str, Any]:
    root = Path(project_root).resolve()
    path = _workspace_config_path(root)
    if not path.is_file():
        return {
            "schema": WORKSPACE_SCHEMA,
            "project_root": str(root),
            "config_path": str(path),
            "configured": False,
            "result_bundle_dir": None,
        }
    data = tomllib.loads(path.read_text(encoding="utf-8"))
    if data.get("schema") != WORKSPACE_SCHEMA:
        raise ValueError(f"unsupported workspace settings schema: {data.get('schema')!r}")
    raw = data.get("result_bundle_dir")
    if not isinstance(raw, str) or not raw.strip():
        raise ValueError("workspace settings must define a non-empty result_bundle_dir")
    result_dir = Path(raw).expanduser().resolve()
    try:
        result_dir.relative_to(root)
    except ValueError:
        pass
    else:
        raise ValueError("result bundle directory must be outside the project tree")
    return {
        "schema": WORKSPACE_SCHEMA,
        "project_root": str(root),
        "config_path": str(path),
        "configured": True,
        "result_bundle_dir": str(result_dir),
    }


def configure_result_bundle_dir(project_root: str | Path, result_dir: str | Path) -> dict[str, Any]:
    root = Path(project_root).resolve()
    destination = Path(result_dir).expanduser().resolve()
    try:
        destination.relative_to(root)
    except ValueError:
        pass
    else:
        raise ValueError("result bundle directory must be outside the project tree")
    destination.mkdir(parents=True, exist_ok=True)
    path = _workspace_config_path(root)
    path.write_text(
        f'schema = {json.dumps(WORKSPACE_SCHEMA)}\n'
        f'result_bundle_dir = {json.dumps(str(destination))}\n',
        encoding="utf-8",
    )
    return load_workspace_settings(root)


def _resolve_result_path(
    raw: Any,
    *,
    project_root: Path,
    allow_unconfigured: bool,
) -> str:
    candidate = Path(str(raw)).expanduser()
    if candidate.is_absolute():
        resolved = candidate.resolve()
    else:
        settings = load_workspace_settings(project_root)
        if not settings["configured"]:
            if allow_unconfigured:
                return str(Path("<result-bundle-dir>") / candidate)
            raise ValueError(
                "result bundle directory is not configured; run "
                "`se-study config --set-result-dir ../SubjectEvolution-results` first, "
                "or pass an absolute --output outside the project"
            )
        resolved = Path(str(settings["result_bundle_dir"])) / candidate
        resolved = resolved.resolve()
    try:
        resolved.relative_to(project_root)
    except ValueError:
        return str(resolved)
    raise ValueError("result bundle output must be outside the project tree")



def _json_field(payload: Any, field: str) -> Any:
    value = payload
    for part in field.split("."):
        if not isinstance(value, dict) or part not in value:
            raise ValueError(f"JSON precondition field not found: {field!r}")
        value = value[part]
    return value


def check_step_preconditions(step: dict[str, Any], values: dict[str, Any]) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for spec in step.get("requires_json", ()):
        if not isinstance(spec, dict):
            raise ValueError("requires_json entries must be tables")
        raw_path = spec.get("path")
        field = spec.get("field")
        if not isinstance(raw_path, str) or not isinstance(field, str):
            raise ValueError("requires_json entries require string path and field")
        path = Path(raw_path.format_map(values))
        if not path.is_absolute():
            path = Path(values["project_root"]) / path
        if not path.is_file():
            raise ValueError(f"required JSON precondition is missing: {path}")
        payload = json.loads(path.read_text(encoding="utf-8"))
        actual = _json_field(payload, field)
        expected = spec.get("equals", True)
        passed = actual == expected
        result = {
            "path": str(path),
            "field": field,
            "expected": expected,
            "actual": actual,
            "passed": passed,
        }
        results.append(result)
        if not passed:
            raise ValueError(
                f"step precondition failed: {path}:{field} expected {expected!r}, got {actual!r}"
            )
    return results


def _workflow_path(study: str | Path) -> Path:
    path = Path(study)
    if path.is_dir():
        path = path / "workflow.toml"
    if not path.exists():
        raise FileNotFoundError(f"study workflow not found: {path}")
    return path


def load_workflow(study: str | Path) -> tuple[Path, dict[str, Any]]:
    path = _workflow_path(study).resolve()
    data = tomllib.loads(path.read_text(encoding="utf-8"))
    if data.get("schema") != WORKFLOW_SCHEMA:
        raise ValueError(f"unsupported study workflow schema: {data.get('schema')!r}")
    if not isinstance(data.get("steps"), dict) or not data["steps"]:
        raise ValueError("study workflow must declare at least one step")
    return path, data


def _parse_bool(value: str | bool) -> bool:
    if isinstance(value, bool):
        return value
    normalized = str(value).strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    raise ValueError(f"expected boolean, got {value!r}")


def _coerce(name: str, raw: Any, spec: dict[str, Any]) -> Any:
    kind = str(spec.get("type", "string"))
    if kind in {"string", "path", "result-path", "choice"}:
        value: Any = str(raw)
    elif kind == "int":
        value = int(raw)
    elif kind == "float":
        value = float(raw)
    elif kind == "bool":
        value = _parse_bool(raw)
    elif kind == "csv-int":
        if isinstance(raw, list):
            values = [int(item) for item in raw]
        else:
            values = [int(item.strip()) for item in str(raw).split(",") if item.strip()]
        if not values:
            raise ValueError(f"parameter {name!r} requires at least one integer")
        value = ",".join(str(item) for item in values)
    else:
        raise ValueError(f"parameter {name!r} has unsupported type {kind!r}")
    choices = spec.get("choices")
    if choices is not None and value not in choices:
        raise ValueError(f"parameter {name!r} must be one of {choices!r}, got {value!r}")
    minimum = spec.get("minimum")
    maximum = spec.get("maximum")
    if minimum is not None and value < minimum:
        raise ValueError(f"parameter {name!r} must be >= {minimum}")
    if maximum is not None and value > maximum:
        raise ValueError(f"parameter {name!r} must be <= {maximum}")
    return value


def _unknown_options(tokens: list[str]) -> dict[str, Any]:
    values: dict[str, Any] = {}
    index = 0
    while index < len(tokens):
        token = tokens[index]
        if not token.startswith("--") or token == "--":
            raise ValueError(f"unexpected workflow argument: {token!r}")
        name = token[2:].replace("-", "_")
        if name.startswith("no_"):
            values[name[3:]] = False
            index += 1
            continue
        if index + 1 < len(tokens) and not tokens[index + 1].startswith("--"):
            values[name] = tokens[index + 1]
            index += 2
        else:
            values[name] = True
            index += 1
    return values


def resolve_step(
    workflow_path: Path,
    workflow: dict[str, Any],
    step_name: str,
    overrides: dict[str, Any] | None = None,
    *,
    allow_unconfigured_result: bool = False,
) -> tuple[list[str], dict[str, Any]]:
    steps = workflow["steps"]
    if step_name not in steps:
        raise ValueError(f"unknown step {step_name!r}; available: {sorted(steps)}")
    step = steps[step_name]
    parameter_specs = workflow.get("parameters", {})
    values: dict[str, Any] = {
        "project_root": str(_project_root_from_workflow(workflow_path)),
        "study_dir": str(workflow_path.parent),
        "study_id": str(workflow.get("study_id", workflow_path.parent.name)),
    }
    for name, spec in parameter_specs.items():
        if "default" not in spec:
            raise ValueError(f"parameter {name!r} has no default")
        values[name] = _coerce(name, spec["default"], spec)
    overrides = overrides or {}
    unknown = sorted(set(overrides) - set(parameter_specs))
    if unknown:
        raise ValueError(f"undeclared workflow parameters: {unknown!r}")
    for name, raw in overrides.items():
        values[name] = _coerce(name, raw, parameter_specs[name])
    command = step.get("command")
    if not isinstance(command, list) or not command or not all(isinstance(item, str) for item in command):
        raise ValueError(f"step {step_name!r} must declare a non-empty string command array")
    used_parameters = {
        name
        for name in parameter_specs
        if any("{" + name + "}" in token for token in command)
        or name in step.get("boolean_flags", {})
    }
    project_root = Path(values["project_root"])
    for name, spec in parameter_specs.items():
        if (
            name in used_parameters
            and str(spec.get("type", "string")) == "result-path"
        ):
            values[name] = _resolve_result_path(
                values[name],
                project_root=project_root,
                allow_unconfigured=allow_unconfigured_result,
            )

    rendered = [item.format_map(values) for item in command]
    for parameter_name, flag in step.get("boolean_flags", {}).items():
        if parameter_name not in parameter_specs:
            raise ValueError(f"step {step_name!r} references unknown boolean parameter {parameter_name!r}")
        if bool(values[parameter_name]):
            rendered.append(str(flag))
    return rendered, values


def describe(workflow_path: Path, workflow: dict[str, Any], step_name: str | None) -> dict[str, Any]:
    result: dict[str, Any] = {
        "schema": workflow["schema"],
        "study_id": workflow.get("study_id", workflow_path.parent.name),
        "title": workflow.get("title", ""),
        "workflow": str(workflow_path),
        "steps": [],
    }
    names = [step_name] if step_name else list(workflow["steps"])
    for name in names:
        command, values = resolve_step(
            workflow_path, workflow, name, allow_unconfigured_result=True
        )
        step = workflow["steps"][name]
        used = sorted(
            parameter
            for parameter in workflow.get("parameters", {})
            if any("{" + parameter + "}" in token for token in step["command"])
            or parameter in step.get("boolean_flags", {})
        )
        result["steps"].append(
            {
                "name": name,
                "description": step.get("description", ""),
                "command": command,
                "command_text": shlex.join(command),
                "preconditions": step.get("requires_json", []),
                "parameters": {
                    parameter: {
                        **workflow["parameters"][parameter],
                        "resolved_default": values[parameter],
                    }
                    for parameter in used
                },
            }
        )
    return result


def _print_description(data: dict[str, Any]) -> None:
    print(f"{data['title']} ({data['study_id']})")
    print(f"workflow: {data['workflow']}")
    for step in data["steps"]:
        print(f"\n[{step['name']}] {step['description']}")
        for name, spec in step["parameters"].items():
            choices = f" choices={spec['choices']}" if "choices" in spec else ""
            print(
                f"  --{name.replace('_', '-')} <{spec.get('type', 'string')}>"
                f" default={spec['resolved_default']!r}{choices}"
                f" — {spec.get('description', '')}"
            )
        for precondition in step.get("preconditions", []):
            print(
                "  requires: "
                + str(precondition.get("path"))
                + ":"
                + str(precondition.get("field"))
                + " == "
                + repr(precondition.get("equals", True))
            )
        print(f"  $ {step['command_text']}")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Inspect or execute a declarative study workflow.")
    subparsers = parser.add_subparsers(dest="action", required=True)
    show = subparsers.add_parser("show", help="show exact commands and declared parameters")
    show.add_argument("study")
    show.add_argument("step", nargs="?")
    show.add_argument("--json", action="store_true")
    run = subparsers.add_parser("run", help="execute one workflow step without a shell")
    run.add_argument("study")
    run.add_argument("step")
    run.add_argument("--dry-run", action="store_true")
    run.add_argument("--json", action="store_true")
    config = subparsers.add_parser(
        "config", help="show or set project-local workspace output settings"
    )
    config.add_argument("--set-result-dir")
    config.add_argument("--json", action="store_true")
    args, unknown = parser.parse_known_args(argv)
    if args.action == "config":
        if unknown:
            parser.error(f"unexpected arguments: {unknown}")
        try:
            root = _find_project_root()
            data = (
                configure_result_bundle_dir(root, args.set_result_dir)
                if args.set_result_dir
                else load_workspace_settings(root)
            )
        except (ValueError, FileNotFoundError) as exc:
            parser.error(str(exc))
        if args.json:
            print(json.dumps(data, ensure_ascii=False, indent=2))
        else:
            print(f"project root: {data['project_root']}")
            print(f"settings: {data['config_path']}")
            print(
                "result bundle directory: "
                + (str(data['result_bundle_dir']) if data['configured'] else "not configured")
            )
        return
    workflow_path, workflow = load_workflow(args.study)
    if args.action == "show":
        if unknown:
            parser.error(f"unexpected arguments: {unknown}")
        data = describe(workflow_path, workflow, args.step)
        if args.json:
            print(json.dumps(data, ensure_ascii=False, indent=2))
        else:
            _print_description(data)
        return
    try:
        overrides = _unknown_options(unknown)
        command, values = resolve_step(workflow_path, workflow, args.step, overrides)
        preconditions = check_step_preconditions(workflow["steps"][args.step], values)
    except (ValueError, FileNotFoundError, json.JSONDecodeError) as exc:
        parser.error(str(exc))
    payload = {
        "study_id": workflow.get("study_id", workflow_path.parent.name),
        "step": args.step,
        "command": command,
        "command_text": shlex.join(command),
        "parameters": values,
        "dry_run": bool(args.dry_run),
        "preconditions": preconditions,
    }
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(f"$ {payload['command_text']}")
    if not args.dry_run:
        completed = subprocess.run(command, cwd=values["project_root"], check=False)
        if completed.returncode:
            raise SystemExit(completed.returncode)


if __name__ == "__main__":
    main()
