#!/usr/bin/env python3
"""Verify that the active Python uses this checkout as an editable SE install.

This is the normal local workflow for conda users. Source edits become visible
immediately; reinstall is only needed after changing project metadata, entry
points, dependencies, or moving the checkout to another path.
"""

from __future__ import annotations

import argparse
import ast
import importlib
import importlib.metadata as metadata
import json
import os
from pathlib import Path
import pkgutil
import subprocess
import sys
import tempfile
import tomllib

from clean_project_bytecode import clean as clean_project_bytecode

DIST_NAME = "se-mvp"
def _expected_entry_points(pyproject: dict[str, object]) -> dict[str, str]:
    project = pyproject.get("project")
    if not isinstance(project, dict):
        raise RuntimeError("pyproject [project] table is missing")
    scripts = project.get("scripts", {})
    if not isinstance(scripts, dict):
        raise RuntimeError("pyproject [project.scripts] must be a table")
    expected: dict[str, str] = {}
    for name, target in scripts.items():
        if not isinstance(name, str) or not isinstance(target, str):
            raise RuntimeError("pyproject console entry names and targets must be strings")
        expected[name] = target
    return expected



def _within(path: Path, root: Path) -> bool:
    return path == root or root in path.parents


def verify(project: Path, *, require_conda: bool, smoke: bool) -> dict[str, object]:
    project = project.resolve()
    source_root = (project / "src").resolve()
    pyproject = tomllib.loads((project / "pyproject.toml").read_text(encoding="utf-8"))
    expected_version = str(pyproject["project"]["version"])
    expected_entry_points = _expected_entry_points(pyproject)

    conda_prefix_text = os.environ.get("CONDA_PREFIX", "")
    conda_prefix = Path(conda_prefix_text).resolve() if conda_prefix_text else None
    if require_conda and conda_prefix is None:
        raise RuntimeError("CONDA_PREFIX is not set; activate the intended conda environment")
    if conda_prefix is not None and not _within(Path(sys.executable).resolve(), conda_prefix):
        raise RuntimeError(
            f"current Python is outside CONDA_PREFIX: {sys.executable} vs {conda_prefix}"
        )

    bytecode_cleanup = clean_project_bytecode(project)
    for module_name in tuple(sys.modules):
        if module_name == "se" or module_name.startswith("se."):
            sys.modules.pop(module_name, None)
    importlib.invalidate_caches()
    import se

    package_path = Path(se.__file__).resolve()
    if not _within(package_path, source_root):
        raise RuntimeError(
            f"SE is not imported from this editable checkout: {package_path}"
        )
    installed_version = metadata.version(DIST_NAME)
    source_tree = ast.parse((source_root / "se" / "__init__.py").read_text(encoding="utf-8"))
    source_version = None
    for node in source_tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "__version__":
                    value = ast.literal_eval(node.value)
                    if isinstance(value, str):
                        source_version = value
    if source_version is None:
        raise RuntimeError("source package __version__ is missing")
    if (
        installed_version != expected_version
        or source_version != expected_version
        or se.__version__ != expected_version
    ):
        raise RuntimeError(
            "version mismatch: "
            f"pyproject={expected_version}, metadata={installed_version}, "
            f"source={source_version}, imported_package={se.__version__}, "
            f"package_path={package_path}"
        )

    dist = metadata.distribution(DIST_NAME)
    direct_url_text = dist.read_text("direct_url.json")
    if not direct_url_text:
        raise RuntimeError("installed distribution has no direct_url.json; editable install not proven")
    direct_url = json.loads(direct_url_text)
    if not bool(direct_url.get("dir_info", {}).get("editable", False)):
        raise RuntimeError("se-mvp is installed from a non-editable artifact")
    url = str(direct_url.get("url", ""))
    if not url.startswith("file://"):
        raise RuntimeError(f"editable install URL is not local: {url!r}")
    editable_root = Path(url.removeprefix("file://")).resolve()
    if editable_root != project:
        raise RuntimeError(
            f"editable distribution points to another checkout: {editable_root}"
        )

    modules = sorted(info.name for info in pkgutil.walk_packages(se.__path__, "se."))
    failures: list[list[str]] = []
    for name in modules:
        try:
            __import__(name)
        except Exception as exc:  # pragma: no cover - surfaced in report
            failures.append([name, type(exc).__name__, str(exc)])
    if failures:
        raise RuntimeError(json.dumps(failures, ensure_ascii=False))

    installed_entries = {
        entry.name: entry.value
        for entry in metadata.entry_points(group="console_scripts")
        if entry.name in expected_entry_points
    }
    if installed_entries != expected_entry_points:
        raise RuntimeError(
            f"console entry points are stale; expected={expected_entry_points}, found={installed_entries}"
        )

    smoke_payload: dict[str, object] | None = None
    if smoke:
        config_source = project / "configs" / "d2a_contextual_harvest_smoke.json"
        with tempfile.TemporaryDirectory(prefix="se-conda-smoke-") as temp:
            root = Path(temp)
            config = root / "smoke.json"
            config.write_bytes(config_source.read_bytes())
            env = os.environ.copy()
            env["PYTHONPATH"] = ""
            env["PYTHONNOUSERSITE"] = "1"
            output = root / "run"
            command = [
                sys.executable,
                "-m",
                "se",
                "--config",
                str(config),
                "--output",
                str(output),
                "--backend",
                "cpu",
                "--until-tick",
                "2",
            ]
            completed = subprocess.run(
                command,
                cwd=root,
                env=env,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                check=False,
            )
            if completed.returncode != 0:
                raise RuntimeError(f"editable smoke failed:\n{completed.stdout}")
            smoke_payload = {
                "command": command,
                "output_exists": output.is_dir(),
                "stdout_tail": completed.stdout.splitlines()[-5:],
            }

    return {
        "passed": True,
        "project": str(project),
        "python": sys.executable,
        "conda_prefix": str(conda_prefix) if conda_prefix else None,
        "version": expected_version,
        "package_path": str(package_path),
        "source_version": source_version,
        "bytecode_cleanup": bytecode_cleanup,
        "editable_root": str(editable_root),
        "module_count": len(modules),
        "entry_points": installed_entries,
        "smoke": smoke_payload,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project", default=".")
    parser.add_argument("--require-conda", action="store_true")
    parser.add_argument("--smoke", action="store_true")
    parser.add_argument("--report")
    args = parser.parse_args()
    report = verify(
        Path(args.project), require_conda=args.require_conda, smoke=args.smoke
    )
    text = json.dumps(report, ensure_ascii=False, indent=2)
    if args.report:
        Path(args.report).write_text(text + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False))


if __name__ == "__main__":
    main()
