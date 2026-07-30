"""Audit long-run GPU allocator-cache stability from metrics.csv artifacts."""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any, Sequence

import numpy as np

SCHEMA = "gpu-memory-stability-audit-v1"


def parse_run_spec(value: str) -> tuple[str, Path]:
    if "=" not in value:
        path = Path(value)
        return path.name, path
    label, raw = value.split("=", 1)
    if not label.strip():
        raise ValueError("run label cannot be empty")
    return label.strip(), Path(raw)


def _number(row: dict[str, str], name: str) -> float | None:
    value = row.get(name)
    if value in (None, ""):
        return None
    try:
        number = float(value)
    except ValueError:
        return None
    return number if np.isfinite(number) else None


def _read_metrics(run: Path) -> list[dict[str, str]]:
    path = run if run.name == "metrics.csv" else run / "metrics.csv"
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def audit_run(label: str, run: Path) -> dict[str, Any]:
    rows = _read_metrics(run)
    if not rows:
        raise ValueError(f"metrics are empty: {run}")
    ticks = [int(float(row["tick"])) for row in rows]
    alive = [int(float(row["alive"])) for row in rows]
    telemetry = [
        row
        for row in rows
        if _number(row, "gpu_memory_pool_total_bytes") is not None
    ]
    result: dict[str, Any] = {
        "label": label,
        "run": str(run),
        "metrics_rows": len(rows),
        "first_tick": ticks[0],
        "last_tick": ticks[-1],
        "initial_reported_alive": alive[0],
        "maximum_alive": max(alive),
        "final_alive": alive[-1],
        "memory_telemetry_available": bool(telemetry),
    }
    if not telemetry:
        result.update(
            {
                "memory_pool_policy_counts": {},
                "allocator_cache_bounded": None,
                "recommendation": "rerun-with-gpu-memory-pool-telemetry",
            }
        )
        return result

    def values(name: str) -> list[float]:
        return [
            value
            for row in telemetry
            if (value := _number(row, name)) is not None
        ]

    used = values("gpu_memory_used_bytes")
    total_end = values("gpu_memory_pool_total_bytes")
    cached_end = values("gpu_memory_pool_cached_bytes")
    total_after_trim = values("gpu_memory_pool_total_bytes_after_trim")
    cached_after_trim = values("gpu_memory_pool_cached_bytes_after_trim")
    peak_used = values("gpu_memory_pool_peak_used_bytes")
    peak_total = values("gpu_memory_pool_peak_total_bytes")
    released = values("gpu_memory_pool_released_bytes_step")
    trim_count = values("gpu_memory_pool_trim_count")
    limits = values("gpu_memory_pool_cache_limit_bytes")
    policies: dict[str, int] = {}
    for row in telemetry:
        policy = row.get("gpu_memory_pool_policy", "")
        policies[policy] = policies.get(policy, 0) + 1
    limit = max(limits) if limits else None
    max_cached_after_trim = (
        max(cached_after_trim) if cached_after_trim else None
    )
    bounded = (
        bool(policies)
        and set(policies) == {"bounded-cache-v1"}
        and limit is not None
        and max_cached_after_trim is not None
        and max_cached_after_trim <= limit
    )
    result.update(
        {
            "telemetry_rows": len(telemetry),
            "memory_pool_policy_counts": policies,
            "configured_cache_limit_bytes": int(limit) if limit is not None else None,
            "maximum_live_bytes": int(max(used)) if used else None,
            "maximum_pool_total_bytes_end_of_step": (
                int(max(total_end)) if total_end else None
            ),
            "maximum_cached_bytes_end_of_step": (
                int(max(cached_end)) if cached_end else None
            ),
            "maximum_pool_total_bytes_after_trim": (
                int(max(total_after_trim)) if total_after_trim else None
            ),
            "maximum_cached_bytes_after_trim": (
                int(max_cached_after_trim)
                if max_cached_after_trim is not None
                else None
            ),
            "reported_peak_live_bytes": int(max(peak_used)) if peak_used else None,
            "reported_peak_pool_total_bytes_before_trim": (
                int(max(peak_total)) if peak_total else None
            ),
            "trim_count": int(max(trim_count)) if trim_count else 0,
            "released_bytes_sum": int(sum(released)) if released else 0,
            "allocator_cache_bounded": bounded,
            "recommendation": (
                "allocator-cache-bounded-continue-scale-run"
                if bounded
                else "inspect-live-memory-or-cache-policy"
            ),
        }
    )
    return result


def build_audit(runs: Sequence[tuple[str, Path]]) -> dict[str, Any]:
    rows = [audit_run(label, path) for label, path in runs]
    available = [row for row in rows if row["memory_telemetry_available"]]
    return {
        "schema": SCHEMA,
        "runs": rows,
        "all_runs_have_memory_telemetry": len(available) == len(rows),
        "all_telemetry_runs_bound_allocator_cache": bool(available)
        and all(row["allocator_cache_bounded"] for row in available),
        "interpretation_boundary": (
            "Allocator telemetry distinguishes live device state from unused CuPy cache. "
            "It does not establish scientific validity or CPU/GPU parity."
        ),
    }


def render_markdown(audit: dict[str, Any]) -> str:
    lines = [
        "# GPU memory stability audit",
        "",
        f"Schema: `{audit['schema']}`",
        "",
        "| Run | Last tick | Max alive | Telemetry | Peak live bytes | Peak pool bytes | Max cached end-step | Max cached after trim | Trims | Bounded |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in audit["runs"]:
        lines.append(
            "| {label} | {last_tick} | {maximum_alive} | {telemetry} | {live} | {pool} | {cached_end} | {cached_trim} | {trims} | {bounded} |".format(
                label=row["label"],
                last_tick=row["last_tick"],
                maximum_alive=row["maximum_alive"],
                telemetry=row["memory_telemetry_available"],
                live=row.get("reported_peak_live_bytes"),
                pool=row.get("reported_peak_pool_total_bytes_before_trim"),
                cached_end=row.get("maximum_cached_bytes_end_of_step"),
                cached_trim=row.get("maximum_cached_bytes_after_trim"),
                trims=row.get("trim_count"),
                bounded=row.get("allocator_cache_bounded"),
            )
        )
    lines.extend(["", audit["interpretation_boundary"], ""])
    return "\n".join(lines)


def main(argv: Sequence[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", action="append", required=True, help="LABEL=RUN_DIR")
    parser.add_argument("--output", required=True)
    args = parser.parse_args(argv)
    runs = [parse_run_spec(value) for value in args.run]
    audit = build_audit(runs)
    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=True)
    (output / "gpu_memory_stability_audit.json").write_text(
        json.dumps(audit, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    (output / "gpu_memory_stability_audit.md").write_text(
        render_markdown(audit), encoding="utf-8"
    )


if __name__ == "__main__":
    main()
