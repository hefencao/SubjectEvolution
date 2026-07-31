#!/usr/bin/env python3
"""Fail before installation when durable version sources diverge."""
from __future__ import annotations

import argparse
import ast
import json
import re
import tomllib
from pathlib import Path


def package_version(path: Path) -> str:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "__version__":
                    value = ast.literal_eval(node.value)
                    if isinstance(value, str):
                        return value
    raise RuntimeError(f"__version__ not found in {path}")


def status_version(path: Path) -> str:
    text = path.read_text(encoding="utf-8")
    match = re.search(r"^Version:\s*\*\*([^*]+)\*\*\s*$", text, flags=re.MULTILINE)
    if not match:
        raise RuntimeError(f"durable project status version not found in {path}")
    return match.group(1).strip()


def check(project: Path) -> dict[str, object]:
    project = project.resolve()
    pyproject = tomllib.loads((project / "pyproject.toml").read_text(encoding="utf-8"))
    project_version = str(pyproject["project"]["version"])
    package = package_version(project / "src/se/__init__.py")
    status = status_version(project / "docs/PROJECT_STATUS.md")
    version_dirs = sorted(
        path.relative_to(project).as_posix()
        for path in (project / "docs").iterdir()
        if path.is_dir() and path.name.startswith("v0.")
    )
    major, minor, *_ = project_version.split(".")
    expected_version_dir = f"docs/v{major}.{minor}"
    stale_version_dirs = [
        path for path in version_dirs if path != expected_version_dir
    ]
    current_version_docs_present = expected_version_dir in version_dirs
    if (
        package != project_version
        or status != project_version
        or stale_version_dirs
        or not current_version_docs_present
    ):
        raise RuntimeError(
            "version mismatch: "
            f"pyproject={project_version}, package={package}, status={status}, "
            f"expected_version_docs={expected_version_dir!r}, "
            f"current_version_docs_present={current_version_docs_present}, "
            f"stale_version_docs={stale_version_dirs}"
        )
    return {
        "passed": True,
        "version": project_version,
        "status_version": status,
        "expected_version_docs": expected_version_dir,
        "current_version_docs_present": current_version_docs_present,
        "stale_version_docs": stale_version_dirs,
        "version_specific_docs": version_dirs,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project", default=".")
    parser.add_argument("--report")
    args = parser.parse_args()
    report = check(Path(args.project))
    text = json.dumps(report, ensure_ascii=False, indent=2)
    if args.report:
        Path(args.report).write_text(text + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False))


if __name__ == "__main__":
    main()
