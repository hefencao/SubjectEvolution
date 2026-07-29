from __future__ import annotations

import json
from pathlib import Path

from se.analysis.gpu_execution_audit import build_audit, render_markdown


def _write(path: Path, backend: dict, *, seconds_per_tick: float = 0.1) -> None:
    path.write_text(
        json.dumps(
            {
                "schema": "example-results-v1",
                "panels": [
                    {
                        "branches": [
                            {
                                "branch": "baseline",
                                "scientific_validity": {"backend_semantics": backend},
                                "final": {
                                    "window_seconds_per_tick": seconds_per_tick,
                                    "gpu_h2d_bytes": 10,
                                    "gpu_d2h_bytes": 20,
                                    "gpu_device_preprocess_rows": 4,
                                    "gpu_device_resident_host_bytes_avoided": 80,
                                },
                            }
                        ]
                    }
                ],
            }
        ),
        encoding="utf-8",
    )


def test_gpu_execution_audit_confirms_real_accelerated_runs(tmp_path: Path) -> None:
    result = tmp_path / "gpu.json"
    _write(
        result,
        {
            "requested_backend": "auto",
            "execution_backend": "gpu-hybrid-accelerated",
            "gpu_semantics_mode": "hybrid-accelerated",
            "gpu_device_validated": True,
            "gpu_acceleration_enabled": True,
            "gpu_fallback_used": False,
            "gpu_fallback_reason": None,
            "cpu_reference_world_authoritative": False,
        },
    )
    audit = build_audit([("gpu", result)])
    assert audit["all_runs_real_gpu_accelerated"] is True
    row = audit["results"][0]
    assert row["accelerated_run_count"] == 1
    assert row["performance"]["window_seconds_per_tick"]["median"] == 0.1
    assert row["performance"]["gpu_device_preprocess_rows"]["median"] == 4.0
    assert (
        row["performance"]["gpu_device_resident_host_bytes_avoided"]["median"]
        == 80.0
    )
    assert "scientific-and-speedup-claims-separate" in audit["recommendation"]


def test_gpu_execution_audit_rejects_strict_reference_and_fallback(tmp_path: Path) -> None:
    result = tmp_path / "strict.json"
    _write(
        result,
        {
            "requested_backend": "gpu",
            "execution_backend": "gpu-strict-reference",
            "gpu_semantics_mode": "strict-reference",
            "gpu_device_validated": True,
            "gpu_acceleration_enabled": False,
            "gpu_fallback_used": False,
            "gpu_fallback_reason": None,
            "cpu_reference_world_authoritative": True,
        },
    )
    audit = build_audit([("strict", result)])
    assert audit["all_runs_real_gpu_accelerated"] is False
    assert audit["results"][0]["strict_reference_run_count"] == 1
    assert audit["recommendation"] == "inspect-backend-provenance-before-gpu-claim"


def test_gpu_execution_audit_markdown_columns_match(tmp_path: Path) -> None:
    result = tmp_path / "gpu.json"
    _write(
        result,
        {
            "requested_backend": "auto",
            "execution_backend": "gpu-hybrid-accelerated",
            "gpu_semantics_mode": "hybrid-accelerated",
            "gpu_device_validated": True,
            "gpu_acceleration_enabled": True,
            "gpu_fallback_used": False,
            "cpu_reference_world_authoritative": False,
        },
    )
    markdown = render_markdown(build_audit([("gpu", result)]))
    rows = [line for line in markdown.splitlines() if line.startswith("|")]
    assert rows[0].count("|") == rows[1].count("|") == rows[2].count("|")
