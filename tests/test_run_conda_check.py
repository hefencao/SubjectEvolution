from __future__ import annotations

import importlib.util
from pathlib import Path
import sys

import pytest


def _load_module():
    path = Path(__file__).resolve().parents[1] / "scripts" / "run_conda_check.py"
    spec = importlib.util.spec_from_file_location("run_conda_check", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_conda_check_rejects_an_unactivated_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    module = _load_module()
    monkeypatch.delenv("CONDA_PREFIX", raising=False)

    with pytest.raises(RuntimeError, match="activate the intended conda environment"):
        module._require_conda_environment()


def test_conda_check_accepts_an_activated_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    module = _load_module()
    monkeypatch.setenv("CONDA_PREFIX", "/tmp/example-conda")

    module._require_conda_environment()
