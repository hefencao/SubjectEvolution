from __future__ import annotations

import os
from pathlib import Path
import py_compile
import subprocess
import sys

from scripts.clean_project_bytecode import clean


def _imported_version(root: Path) -> str:
    completed = subprocess.run(
        [
            sys.executable,
            "-S",
            "-c",
            (
                "import sys; "
                f"sys.path.insert(0, {str(root)!r}); "
                "import se; print(se.__version__)"
            ),
        ],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=True,
    )
    return completed.stdout.strip()


def test_cleanup_removes_same_size_same_mtime_stale_bytecode(tmp_path: Path) -> None:
    project = tmp_path / "project"
    package = project / "src" / "se"
    package.mkdir(parents=True)
    source = package / "__init__.py"
    source.write_text('__version__ = "0.53.0"\n', encoding="utf-8")
    original = source.stat()
    py_compile.compile(str(source), doraise=True)

    source.write_text('__version__ = "0.55.0"\n', encoding="utf-8")
    os.utime(source, (original.st_atime, original.st_mtime))
    assert _imported_version(project / "src") == "0.53.0"

    report = clean(project)
    assert report["removed_cache_directories"] == 1
    assert _imported_version(project / "src") == "0.55.0"
