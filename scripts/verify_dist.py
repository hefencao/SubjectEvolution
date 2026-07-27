#!/usr/bin/env python3
"""Build and validate the wheel in a disposable environment.

This intentionally never imports ``se`` from the source checkout. It builds an
sdist, builds the candidate wheel from that sdist, creates a fresh venv,
force-reinstalls the candidate, changes to a separate working directory, clears
PYTHONPATH/user-site visibility, imports all installed modules, exercises all
installed console scripts, runs ``pip check``, and performs a short simulation
with a copied external config.
"""

from __future__ import annotations

import argparse
import importlib.metadata
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
import venv
from typing import Any, Sequence


DIST_NAME = "se-mvp"
PACKAGE_NAME = "se"


def _run(
    command: Sequence[str | os.PathLike[str]],
    *,
    cwd: Path,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    completed = subprocess.run(
        [str(item) for item in command],
        cwd=cwd,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    if completed.returncode != 0:
        raise RuntimeError(
            f"command failed ({completed.returncode}): {' '.join(map(str, command))}\n"
            f"{completed.stdout}"
        )
    return completed


def _venv_python(root: Path) -> Path:
    return root / ("Scripts/python.exe" if os.name == "nt" else "bin/python")


def _venv_script(root: Path, name: str) -> Path:
    suffix = ".exe" if os.name == "nt" else ""
    return root / ("Scripts" if os.name == "nt" else "bin") / f"{name}{suffix}"


def _wheel_version(path: Path) -> str:
    match = re.match(r"se_mvp-([^-]+)-", path.name)
    if not match:
        raise ValueError(f"unexpected wheel filename: {path.name}")
    return match.group(1)


def verify(args: argparse.Namespace) -> dict[str, Any]:
    project = Path(args.project).resolve()
    config = (project / args.config).resolve() if not Path(args.config).is_absolute() else Path(args.config).resolve()
    if not (project / "pyproject.toml").is_file():
        raise FileNotFoundError(f"not a project root: {project}")
    if not config.is_file():
        raise FileNotFoundError(config)

    holder = None
    if args.work_dir:
        work_root = Path(args.work_dir).resolve()
        if work_root.exists():
            shutil.rmtree(work_root)
        work_root.mkdir(parents=True)
        cleanup = False
    elif args.keep:
        work_root = Path(tempfile.mkdtemp(prefix="se-dist-verify-"))
        cleanup = False
    else:
        holder = tempfile.TemporaryDirectory(prefix="se-dist-verify-")
        work_root = Path(holder.name)
        cleanup = True

    dist_dir = work_root / "dist"
    sdist_dir = dist_dir / "sdist"
    wheel_dir = dist_dir / "wheel"
    sdist_dir.mkdir(parents=True, exist_ok=True)
    wheel_dir.mkdir(parents=True, exist_ok=True)

    sdist_build = _run(
        [
            sys.executable,
            "-c",
            (
                "from setuptools.build_meta import build_sdist; "
                "print(build_sdist(" + repr(str(sdist_dir)) + "))"
            ),
        ],
        cwd=project,
    )
    sdists = sorted(sdist_dir.glob("se_mvp-*.tar.gz"))
    if len(sdists) != 1:
        raise RuntimeError(f"expected one candidate sdist, found {sdists}")
    sdist = sdists[0]
    with tarfile.open(sdist, "r:gz") as archive:
        sdist_members = sorted(
            member.name for member in archive.getmembers() if member.isfile()
        )
        root_names = {name.split("/", 1)[0] for name in sdist_members}
        if len(root_names) != 1:
            raise RuntimeError(f"sdist must have one top-level directory: {root_names}")
        sdist_root = next(iter(root_names))
        required_sdist_paths = [
            "pyproject.toml",
            "README.md",
            "MANIFEST.in",
            "configs/d2a_contextual_harvest_smoke.json",
            "docs/PROJECT_CHARTER.md",
            "scripts/verify_dist.py",
            "src/se/__init__.py",
        ]
        missing_sdist_paths = [
            path for path in required_sdist_paths
            if f"{sdist_root}/{path}" not in sdist_members
        ]
        if missing_sdist_paths:
            raise RuntimeError(
                f"sdist is missing required project files: {missing_sdist_paths}"
            )
        forbidden_sdist_paths = [
            name for name in sdist_members
            if "/docs/archive/" in name
            or "/.git/" in name
            or "/__pycache__/" in name
            or name.endswith((".pyc", ".pyo"))
        ]
        if forbidden_sdist_paths:
            raise RuntimeError(
                f"sdist contains forbidden files: {forbidden_sdist_paths[:10]}"
            )
        config_member = archive.getmember(
            f"{sdist_root}/configs/d2a_contextual_harvest_smoke.json"
        )
        config_payload = archive.extractfile(config_member)
        if config_payload is None:
            raise RuntimeError("sdist smoke config could not be read")
        sdist_smoke_config = config_payload.read()

    wheel_build = _run(
        [
            sys.executable,
            "-m",
            "pip",
            "wheel",
            sdist,
            "--no-deps",
            "--no-build-isolation",
            "--wheel-dir",
            wheel_dir,
        ],
        cwd=work_root,
    )
    wheels = sorted(wheel_dir.glob("se_mvp-*.whl"))
    if len(wheels) != 1:
        raise RuntimeError(f"expected one candidate wheel, found {wheels}")
    wheel = wheels[0]
    expected_version = _wheel_version(wheel)

    env_root = work_root / "venv"
    venv.EnvBuilder(
        with_pip=True,
        clear=True,
        system_site_packages=not args.strict,
    ).create(env_root)
    python = _venv_python(env_root)
    clean_env = os.environ.copy()
    clean_env["PYTHONPATH"] = ""
    clean_env["PYTHONNOUSERSITE"] = "1"
    clean_env["PIP_DISABLE_PIP_VERSION_CHECK"] = "1"

    previous_version = None
    if args.previous_wheel:
        previous = Path(args.previous_wheel).resolve()
        _run(
            [python, "-m", "pip", "install", "--no-deps", previous],
            cwd=work_root,
            env=clean_env,
        )
        previous_version = _run(
            [python, "-c", "import importlib.metadata as m; print(m.version('se-mvp'))"],
            cwd=work_root,
            env=clean_env,
        ).stdout.strip()

    if args.strict:
        if not args.wheelhouse:
            raise ValueError("--strict requires --wheelhouse for offline dependencies")
        _run(
            [
                python,
                "-m",
                "pip",
                "install",
                "--no-index",
                "--find-links",
                Path(args.wheelhouse).resolve(),
                "numpy>=1.24",
            ],
            cwd=work_root,
            env=clean_env,
        )

    install = _run(
        [
            python,
            "-m",
            "pip",
            "install",
            "--force-reinstall",
            "--no-deps",
            wheel,
        ],
        cwd=work_root,
        env=clean_env,
    )

    probe_code = f"""
import importlib.metadata as metadata
import json
import pathlib
import pkgutil
import se
project = pathlib.Path({str(project)!r}).resolve()
source_root = (project / 'src').resolve()
venv_root = pathlib.Path({str(env_root)!r}).resolve()
package_path = pathlib.Path(se.__file__).resolve()
if source_root == package_path or source_root in package_path.parents:
    raise SystemExit(f'installed import leaked to source tree: {{package_path}}')
if venv_root not in package_path.parents:
    raise SystemExit(f'installed import did not come from candidate venv: {{package_path}}')
version = metadata.version('se-mvp')
if version != {expected_version!r} or se.__version__ != {expected_version!r}:
    raise SystemExit(f'version mismatch: metadata={{version}} package={{se.__version__}}')
modules = sorted(info.name for info in pkgutil.walk_packages(se.__path__, se.__name__ + '.'))
failed = []
for name in modules:
    try:
        __import__(name)
    except Exception as exc:
        failed.append([name, type(exc).__name__, str(exc)])
if failed:
    raise SystemExit(json.dumps(failed, ensure_ascii=False))
print(json.dumps({{'version': version, 'package_path': str(package_path), 'module_count': len(modules)}}))
"""
    probe = _run([python, "-c", probe_code], cwd=work_root, env=clean_env)
    probe_payload = json.loads(probe.stdout.strip().splitlines()[-1])

    pip_check = subprocess.run(
        [str(python), "-m", "pip", "check"],
        cwd=work_root,
        env=clean_env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    pip_check_lines = [line.strip() for line in pip_check.stdout.splitlines() if line.strip()]
    candidate_dependency_errors = [
        line for line in pip_check_lines
        if line.lower().startswith(DIST_NAME.lower() + " ")
    ]
    if candidate_dependency_errors or (args.strict and pip_check.returncode != 0):
        raise RuntimeError(
            "installed candidate has broken dependencies:\n" + pip_check.stdout
        )

    help_outputs: dict[str, str] = {}
    for command in ("se", "se-multi", "se-gui", "se-d1-factorial"):
        result = _run(
            [_venv_script(env_root, command), "--help"],
            cwd=work_root,
            env=clean_env,
        )
        help_outputs[command] = result.stdout.splitlines()[0] if result.stdout else ""

    external_config = work_root / "smoke-config.json"
    external_config.write_bytes(sdist_smoke_config)
    run_dir = work_root / "smoke-run"
    smoke = _run(
        [
            _venv_script(env_root, "se"),
            "--config",
            external_config,
            "--output",
            run_dir,
            "--backend",
            "cpu",
            "--seed",
            "424242",
            "--checkpoint-ticks",
            ",".join(str(value) for value in range(1, int(args.until_tick) + 1)),
            "--until-tick",
            str(args.until_tick),
        ],
        cwd=work_root,
        env=clean_env,
    )
    if not (run_dir / "metrics.csv").is_file():
        raise RuntimeError("installed-wheel smoke did not produce metrics.csv")
    resolved_smoke = json.loads(
        (run_dir / "resolved_config.json").read_text(encoding="utf-8")
    )
    if int(resolved_smoke["run"]["seed"]) != 424242:
        raise RuntimeError("installed se --seed override was not applied")
    for tick in range(1, int(args.until_tick) + 1):
        if not (run_dir / f"checkpoint_{tick:08d}.sechk").is_file():
            raise RuntimeError(f"installed se did not write exact checkpoint tick {tick}")

    multi_dir = work_root / "multi-smoke"
    multi = _run(
        [
            _venv_script(env_root, "se-multi"),
            "--config",
            external_config,
            "--seeds",
            "101,202",
            "--output",
            multi_dir,
            "--backend",
            "cpu",
            "--checkpoint-ticks",
            ",".join(str(value) for value in range(1, int(args.until_tick) + 1)),
            "--until-tick",
            str(args.until_tick),
        ],
        cwd=work_root,
        env=clean_env,
    )
    for seed in (101, 202):
        seed_dir = multi_dir / f"seed_{seed}"
        for tick in range(1, int(args.until_tick) + 1):
            if not (seed_dir / f"checkpoint_{tick:08d}.sechk").is_file():
                raise RuntimeError(
                    f"installed se-multi did not write checkpoint {tick} for seed {seed}"
                )

    installed_version = _run(
        [python, "-c", "import importlib.metadata as m; print(m.version('se-mvp'))"],
        cwd=work_root,
        env=clean_env,
    ).stdout.strip()
    if installed_version != expected_version:
        raise RuntimeError(
            f"candidate was not installed: expected {expected_version}, got {installed_version}"
        )

    report = {
        "schema": "isolated-wheel-validation-v2",
        "project": str(project),
        "sdist": str(sdist),
        "wheel": str(wheel),
        "wheel_built_from_sdist": True,
        "sdist_top_level": sdist_root,
        "sdist_file_count": len(sdist_members),
        "sdist_required_paths": required_sdist_paths,
        "sdist_forbidden_path_count": len(forbidden_sdist_paths),
        "expected_version": expected_version,
        "previous_version": previous_version,
        "installed_version": installed_version,
        "strict_dependency_isolation": bool(args.strict),
        "system_site_packages": not args.strict,
        "source_tree_excluded": True,
        "force_reinstall": True,
        "persistent_environment": bool(args.work_dir),
        "venv_root": str(env_root),
        "venv_python": str(python),
        "console_script_dir": str(_venv_script(env_root, "se").parent),
        "probe": probe_payload,
        "console_scripts": help_outputs,
        "source_smoke_config": str(config),
        "external_smoke_config": str(external_config),
        "smoke_until_tick": int(args.until_tick),
        "smoke_metrics": str(run_dir / "metrics.csv"),
        "sdist_build_output": sdist_build.stdout,
        "wheel_build_output": wheel_build.stdout,
        "install_output": install.stdout,
        "pip_check_returncode": int(pip_check.returncode),
        "pip_check_output": pip_check.stdout,
        "pip_check_candidate_dependency_errors": candidate_dependency_errors,
        "pip_check_unrelated_environment_warnings_allowed": (
            not args.strict and pip_check.returncode != 0
        ),
        "smoke_output": smoke.stdout,
        "multi_seed_smoke_output": multi.stdout,
        "multi_seed_smoke_output_dir": str(multi_dir),
        "passed": True,
    }
    report_path = (
        Path(args.report).resolve()
        if args.report
        else work_root / "isolated_wheel_validation.json"
    )
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"passed": True, "report": str(report_path), "wheel": str(wheel), "venv": str(env_root)}))

    if args.keep or args.work_dir:
        print(f"kept validation workspace: {work_root}")
        print(f"verified console scripts: {_venv_script(env_root, 'se').parent}")
        if os.name != "nt":
            print(f"activate with: source {env_root / 'bin' / 'activate'}")
    elif cleanup and holder is not None:
        holder.cleanup()
    return report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", default=".")
    parser.add_argument("--config", default="configs/d2a_contextual_harvest_smoke.json")
    parser.add_argument("--until-tick", type=int, default=2)
    parser.add_argument("--previous-wheel")
    parser.add_argument("--strict", action="store_true")
    parser.add_argument("--wheelhouse")
    parser.add_argument("--work-dir")
    parser.add_argument("--report")
    parser.add_argument("--keep", action="store_true")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    if args.until_tick <= 0:
        raise ValueError("--until-tick must be positive")
    verify(args)


if __name__ == "__main__":
    main()
