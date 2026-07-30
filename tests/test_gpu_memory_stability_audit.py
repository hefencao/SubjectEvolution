from __future__ import annotations

import csv
from pathlib import Path

from se.analysis.gpu_memory_stability import build_audit, render_markdown


def _write_metrics(path: Path, *, telemetry: bool) -> None:
    path.mkdir(parents=True)
    fields = ["tick", "alive"]
    if telemetry:
        fields += [
            "gpu_memory_pool_policy",
            "gpu_memory_pool_cache_limit_bytes",
            "gpu_memory_used_bytes",
            "gpu_memory_pool_total_bytes",
            "gpu_memory_pool_cached_bytes",
            "gpu_memory_pool_total_bytes_after_trim",
            "gpu_memory_pool_cached_bytes_after_trim",
            "gpu_memory_pool_peak_used_bytes",
            "gpu_memory_pool_peak_total_bytes",
            "gpu_memory_pool_trim_count",
            "gpu_memory_pool_released_bytes_step",
        ]
    with (path / "metrics.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for tick, alive in ((100, 1000), (200, 1500)):
            row = {"tick": tick, "alive": alive}
            if telemetry:
                row.update(
                    {
                        "gpu_memory_pool_policy": "bounded-cache-v1",
                        "gpu_memory_pool_cache_limit_bytes": 500,
                        "gpu_memory_used_bytes": 300,
                        "gpu_memory_pool_total_bytes": 450,
                        "gpu_memory_pool_cached_bytes": 650,
                        "gpu_memory_pool_total_bytes_after_trim": 450,
                        "gpu_memory_pool_cached_bytes_after_trim": 150,
                        "gpu_memory_pool_peak_used_bytes": 350,
                        "gpu_memory_pool_peak_total_bytes": 1200,
                        "gpu_memory_pool_trim_count": tick // 100,
                        "gpu_memory_pool_released_bytes_step": 750,
                    }
                )
            writer.writerow(row)


def test_memory_audit_distinguishes_old_and_bounded_runs(tmp_path: Path) -> None:
    old = tmp_path / "old"
    current = tmp_path / "current"
    _write_metrics(old, telemetry=False)
    _write_metrics(current, telemetry=True)
    audit = build_audit([("old", old), ("current", current)])
    assert audit["all_runs_have_memory_telemetry"] is False
    assert audit["all_telemetry_runs_bound_allocator_cache"] is True
    assert audit["runs"][0]["allocator_cache_bounded"] is None
    assert audit["runs"][1]["allocator_cache_bounded"] is True
    assert audit["runs"][1]["reported_peak_pool_total_bytes_before_trim"] == 1200
    assert audit["runs"][1]["maximum_cached_bytes_end_of_step"] == 650
    assert audit["runs"][1]["maximum_cached_bytes_after_trim"] == 150
    markdown = render_markdown(audit)
    table = [line for line in markdown.splitlines() if line.startswith("|")]
    assert table[0].count("|") == table[1].count("|") == table[2].count("|")
