from __future__ import annotations

import importlib.util
from pathlib import Path
import sys


def _load_module():
    path = Path(__file__).resolve().parents[1] / "scripts" / "verify_conda_editable.py"
    scripts_dir = str(path.parent)
    if scripts_dir not in sys.path:
        sys.path.insert(0, scripts_dir)
    spec = importlib.util.spec_from_file_location("verify_conda_editable", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_expected_entry_points_come_from_pyproject_scripts() -> None:
    module = _load_module()
    pyproject = {
        "project": {
            "scripts": {
                "se": "se.cmd.run:main",
                "se-new": "se.analysis.new:main",
            }
        }
    }

    assert module._expected_entry_points(pyproject) == {
        "se": "se.cmd.run:main",
        "se-new": "se.analysis.new:main",
    }


def test_expected_entry_points_rejects_non_string_targets() -> None:
    module = _load_module()
    pyproject = {"project": {"scripts": {"se": 1}}}

    try:
        module._expected_entry_points(pyproject)
    except RuntimeError as exc:
        assert "must be strings" in str(exc)
    else:
        raise AssertionError("non-string console entry target was accepted")
