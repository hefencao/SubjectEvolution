from __future__ import annotations

import json
from pathlib import Path

from scripts.summarize_gpu_parity_reports import render_markdown, summarize
from se.analysis.parity import SEMANTIC_PARITY_CONFIGS


def _report(path: Path, *, passed: bool = True, config: str | None = None) -> None:
    path.write_text(
        json.dumps(
            {
                "passed": passed,
                "gpu_available": True,
                "config": config,
                "ticks_compared": 2,
                "first_failure": None,
            }
        ),
        encoding="utf-8",
    )


def test_gpu_parity_certificate_requires_stage_and_every_semantic_family(
    tmp_path: Path,
) -> None:
    reports = tmp_path / "reports"
    reports.mkdir()
    _report(reports / "stage-parity.json")
    for filename in SEMANTIC_PARITY_CONFIGS:
        _report(
            reports / f"world-{Path(filename).stem}.json",
            config=filename,
        )
    payload = summarize(reports, tmp_path)
    assert payload["passed"] is True
    assert payload["found_report_count"] == payload["required_report_count"]
    markdown = render_markdown(payload)
    assert "Passed: `True`" in markdown


def test_gpu_parity_certificate_fails_when_report_is_missing(tmp_path: Path) -> None:
    reports = tmp_path / "reports"
    reports.mkdir()
    _report(reports / "stage-parity.json")
    payload = summarize(reports, tmp_path)
    assert payload["passed"] is False
    assert payload["missing_reports"]


def test_parity_report_writer_records_runtime_and_hash(tmp_path: Path) -> None:
    from se.analysis.parity import write_gpu_parity_report

    target = write_gpu_parity_report(
        tmp_path,
        "stage-parity.json",
        {"passed": True, "gpu_available": False},
    )
    payload = json.loads(target.read_text(encoding="utf-8"))
    assert payload["passed"] is True
    assert "gpu_runtime" in payload
    assert len(payload["report_sha256_basis"]) == 64
