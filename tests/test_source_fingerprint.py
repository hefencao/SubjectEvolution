from __future__ import annotations

from pathlib import Path

from scripts.source_fingerprint import source_tree_fingerprint


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def test_source_fingerprint_ignores_generated_metadata(tmp_path: Path) -> None:
    _write(tmp_path / "Makefile", "test:\n\t@true\n")
    _write(tmp_path / "pyproject.toml", "[project]\nname='example'\n")
    _write(tmp_path / "src/example.py", "VALUE = 1\n")
    _write(tmp_path / "scripts/check.py", "print('ok')\n")
    _write(tmp_path / "tests/test_example.py", "def test_ok(): assert True\n")
    _write(tmp_path / "configs/example.json", "{}\n")

    expected = source_tree_fingerprint(tmp_path)
    _write(tmp_path / "src/example.egg-info/SOURCES.txt", "generated\n")
    _write(tmp_path / "src/__pycache__/example.cpython-313.pyc", "generated\n")
    _write(tmp_path / "src/stray.pyc", "generated\n")
    _write(tmp_path / "build/generated.txt", "generated\n")
    _write(tmp_path / "dist/generated.whl", "generated\n")

    assert source_tree_fingerprint(tmp_path) == expected

    _write(tmp_path / "src/example.py", "VALUE = 2\n")
    assert source_tree_fingerprint(tmp_path) != expected
