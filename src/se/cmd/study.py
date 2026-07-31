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
    if kind == "string" or kind == "path" or kind == "choice":
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
) -> tuple[list[str], dict[str, Any]]:
    steps = workflow["steps"]
    if step_name not in steps:
        raise ValueError(f"unknown step {step_name!r}; available: {sorted(steps)}")
    step = steps[step_name]
    parameter_specs = workflow.get("parameters", {})
    values: dict[str, Any] = {
        "project_root": str(workflow_path.parent.parent.parent),
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
        command, values = resolve_step(workflow_path, workflow, name)
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
    args, unknown = parser.parse_known_args(argv)
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
    except (ValueError, FileNotFoundError) as exc:
        parser.error(str(exc))
    payload = {
        "study_id": workflow.get("study_id", workflow_path.parent.name),
        "step": args.step,
        "command": command,
        "command_text": shlex.join(command),
        "parameters": values,
        "dry_run": bool(args.dry_run),
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
