from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from scripts.verify_frozen_files import verify_lock


def test_verify_frozen_files_accepts_exact_manifest(tmp_path: Path) -> None:
    evidence = tmp_path / "evidence.json"
    evidence.write_text('{"ready": false}\n', encoding="utf-8")
    data = evidence.read_bytes()
    lock = tmp_path / "lock.json"
    lock.write_text(
        json.dumps(
            {
                "schema": "test-lock-v1",
                "files": [
                    {
                        "path": "evidence.json",
                        "size": len(data),
                        "sha256": hashlib.sha256(data).hexdigest(),
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    report = verify_lock(lock, project_root=tmp_path)

    assert report["passed"] is True
    assert report["checked_file_count"] == 1


def test_verify_frozen_files_rejects_drift(tmp_path: Path) -> None:
    evidence = tmp_path / "evidence.json"
    evidence.write_text("original\n", encoding="utf-8")
    data = evidence.read_bytes()
    lock = tmp_path / "lock.json"
    lock.write_text(
        json.dumps(
            {
                "files": [
                    {
                        "path": "evidence.json",
                        "size": len(data),
                        "sha256": hashlib.sha256(data).hexdigest(),
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    evidence.write_text("changed\n", encoding="utf-8")

    with pytest.raises(RuntimeError, match="sha256"):
        verify_lock(lock, project_root=tmp_path)


def test_verify_frozen_files_cli_writes_portable_report(tmp_path: Path) -> None:
    from scripts.verify_frozen_files import main
    import sys

    evidence = tmp_path / "evidence.json"
    evidence.write_text("{}\n", encoding="utf-8")
    data = evidence.read_bytes()
    lock = tmp_path / "lock.json"
    lock.write_text(
        json.dumps(
            {
                "files": [
                    {
                        "path": "evidence.json",
                        "size": len(data),
                        "sha256": hashlib.sha256(data).hexdigest(),
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    output = tmp_path / "analysis" / "audit.json"
    old = sys.argv
    try:
        sys.argv = [
            "verify_frozen_files.py",
            "--lock",
            str(lock),
            "--project-root",
            str(tmp_path),
            "--output",
            str(output),
        ]
        main()
    finally:
        sys.argv = old

    report = json.loads(output.read_text(encoding="utf-8"))
    assert report["passed"] is True
    assert report["lock"] == "lock.json"
