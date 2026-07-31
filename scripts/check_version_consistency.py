#!/usr/bin/env python3
"""Fail before installation when durable version sources diverge.

Iteration-note retention is intentionally outside this check.  A developer's
checkout may keep any history under ``docs/迭代``; release packaging prunes a
copy without making local history an editable-install concern.
"""
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
    if package != project_version or status != project_version:
        raise RuntimeError(
            "version mismatch: "
            f"pyproject={project_version}, package={package}, status={status}"
        )
    return {
        "passed": True,
        "version": project_version,
        "package_version": package,
        "status_version": status,
        "iteration_docs_checked": False,
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
