#!/usr/bin/env python3
"""Verify that the active Python uses this checkout as an editable SE install.

This is the normal local workflow for conda users. Source edits become visible
immediately; reinstall is only needed after changing project metadata, entry
points, dependencies, or moving the checkout to another path.
"""

from __future__ import annotations

import argparse
import importlib.metadata as metadata
import json
import os
from pathlib import Path
import pkgutil
import subprocess
import sys
import tempfile
import tomllib

DIST_NAME = "se-mvp"
ENTRY_POINTS = {
    "se": "se.cmd.run:main",
    "se-multi": "se.cmd.multi_seed:main",
    "se-gui": "se.gui.runner:main",
    "se-d1-factorial": "se.experiments.d1_factorial:main",
    "se-d2-audit": "se.experiments.d2_module_audit:main",
    "se-d2-assess": "se.analysis.d2_effects:main",
    "se-d2-lineage-pairs": "se.experiments.d2_lineage_pairs:main",
    "se-d2-lineage-assess": "se.analysis.d2_lineage_effects:main",
    "se-d2-lineage-mediate": "se.experiments.d2_lineage_mediation:main",
    "se-d2-lineage-mediate-assess": "se.analysis.d2_lineage_mediation_effects:main",
    "se-d2-source-population": "se.experiments.d2_source_population:main",
    "se-d2-source-population-assess": "se.analysis.d2_source_population_effects:main",
    "se-d2-source-causal": "se.experiments.d2_source_population_causal:main",
    "se-d2-source-causal-assess": "se.analysis.d2_source_population_causal_effects:main",
    "se-d2-compose": "se.experiments.d2_compositional_capability:main",
    "se-d2-embody": "se.experiments.d2_embodied_capability:main",
    "se-d2-physiology": "se.experiments.d2_physiological_ecology:main",
    "se-d2-regulatory-physiology": "se.experiments.d2_regulatory_physiology:main",
    "se-d2-regulatory-physiology-assess": "se.analysis.d2_regulatory_physiology_flows:main",
    "se-d3-resource-metabolism": "se.experiments.d3_resource_metabolism:main",
    "se-d4-niche-reversal": "se.experiments.d4_niche_reversal:main",
    "se-d4-niche-assess": "se.analysis.d4_niche_reversal_effects:main",
}


def _within(path: Path, root: Path) -> bool:
    return path == root or root in path.parents


def verify(project: Path, *, require_conda: bool, smoke: bool) -> dict[str, object]:
    project = project.resolve()
    source_root = (project / "src").resolve()
    pyproject = tomllib.loads((project / "pyproject.toml").read_text(encoding="utf-8"))
    expected_version = str(pyproject["project"]["version"])

    conda_prefix_text = os.environ.get("CONDA_PREFIX", "")
    conda_prefix = Path(conda_prefix_text).resolve() if conda_prefix_text else None
    if require_conda and conda_prefix is None:
        raise RuntimeError("CONDA_PREFIX is not set; activate the intended conda environment")
    if conda_prefix is not None and not _within(Path(sys.executable).resolve(), conda_prefix):
        raise RuntimeError(
            f"current Python is outside CONDA_PREFIX: {sys.executable} vs {conda_prefix}"
        )

    import se

    package_path = Path(se.__file__).resolve()
    if not _within(package_path, source_root):
        raise RuntimeError(
            f"SE is not imported from this editable checkout: {package_path}"
        )
    installed_version = metadata.version(DIST_NAME)
    if installed_version != expected_version or se.__version__ != expected_version:
        raise RuntimeError(
            "version mismatch: "
            f"pyproject={expected_version}, metadata={installed_version}, package={se.__version__}"
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
        if entry.name in ENTRY_POINTS
    }
    if installed_entries != ENTRY_POINTS:
        raise RuntimeError(
            f"console entry points are stale; expected={ENTRY_POINTS}, found={installed_entries}"
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
