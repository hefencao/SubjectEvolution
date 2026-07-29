"""Audit whether supplied experiment artifacts actually used accelerated GPU execution.

This audit is operational only.  It verifies backend provenance and summarizes
reported transfer/timing diagnostics.  It never treats GPU execution as
scientific validation and never infers a speedup without a paired benchmark.
"""
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
from typing import Any, Iterable, Iterator, Sequence

import numpy as np

SCHEMA = "gpu-execution-audit-v1"


def parse_result_spec(value: str) -> tuple[str, Path]:
    if "=" not in value:
        path = Path(value)
        return path.stem, path
    label, raw_path = value.split("=", 1)
    if not label.strip():
        raise ValueError("result label cannot be empty")
    return label.strip(), Path(raw_path)


def _iter_run_records(value: Any, *, path: str = "root") -> Iterator[tuple[str, dict[str, Any]]]:
    if isinstance(value, dict):
        validity = value.get("scientific_validity")
        if isinstance(validity, dict) and isinstance(validity.get("backend_semantics"), dict):
            yield path, value
            return
        for key, child in value.items():
            yield from _iter_run_records(child, path=f"{path}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from _iter_run_records(child, path=f"{path}[{index}]")


def _distribution(values: Sequence[float]) -> dict[str, float | int | None]:
    if not values:
        return {"count": 0, "minimum": None, "median": None, "mean": None, "maximum": None}
    array = np.asarray(values, dtype=np.float64)
    return {
        "count": int(array.size),
        "minimum": float(np.min(array)),
        "median": float(np.median(array)),
        "mean": float(np.mean(array)),
        "maximum": float(np.max(array)),
    }


def _performance(records: Sequence[dict[str, Any]]) -> dict[str, Any]:
    fields = (
        "wall_elapsed_seconds",
        "step_seconds",
        "window_seconds_per_tick",
        "environment_seconds",
        "spatial_seconds",
        "observation_seconds",
        "policy_seconds",
        "conflict_seconds",
        "device_commit_seconds",
        "gpu_h2d_bytes",
        "gpu_d2h_bytes",
        "gpu_entity_commit_bytes",
    )
    result: dict[str, Any] = {}
    for field in fields:
        values: list[float] = []
        for record in records:
            final = record.get("final")
            if not isinstance(final, dict):
                continue
            value = final.get(field)
            if isinstance(value, (int, float)) and np.isfinite(value):
                values.append(float(value))
        result[field] = _distribution(values)
    return result


def _count(values: Iterable[Any]) -> dict[str, int]:
    return {str(key): int(value) for key, value in sorted(Counter(values).items(), key=lambda item: str(item[0]))}


def audit_result(label: str, path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    located = list(_iter_run_records(payload))
    records = [record for _, record in located]
    rows: list[dict[str, Any]] = []
    for record_path, record in located:
        backend = record["scientific_validity"]["backend_semantics"]
        rows.append(
            {
                "path": record_path,
                "requested_backend": backend.get("requested_backend"),
                "execution_backend": backend.get("execution_backend"),
                "gpu_semantics_mode": backend.get("gpu_semantics_mode"),
                "gpu_device_validated": bool(backend.get("gpu_device_validated")),
                "gpu_acceleration_enabled": bool(backend.get("gpu_acceleration_enabled")),
                "gpu_fallback_used": bool(backend.get("gpu_fallback_used")),
                "gpu_fallback_reason": backend.get("gpu_fallback_reason"),
                "cpu_reference_world_authoritative": bool(
                    backend.get("cpu_reference_world_authoritative")
                ),
            }
        )
    accelerated = [
        row
        for row in rows
        if row["execution_backend"] == "gpu-hybrid-accelerated"
        and row["gpu_device_validated"]
        and row["gpu_acceleration_enabled"]
        and not row["gpu_fallback_used"]
        and not row["cpu_reference_world_authoritative"]
    ]
    all_accelerated = bool(rows) and len(accelerated) == len(rows)
    summary = {
        "label": label,
        "path": str(path),
        "result_schema": payload.get("schema"),
        "run_record_count": len(rows),
        "requested_backend_counts": _count(row["requested_backend"] for row in rows),
        "execution_backend_counts": _count(row["execution_backend"] for row in rows),
        "gpu_semantics_mode_counts": _count(row["gpu_semantics_mode"] for row in rows),
        "accelerated_run_count": len(accelerated),
        "fallback_run_count": sum(bool(row["gpu_fallback_used"]) for row in rows),
        "strict_reference_run_count": sum(
            row["execution_backend"] == "gpu-strict-reference" for row in rows
        ),
        "cpu_authoritative_run_count": sum(
            bool(row["cpu_reference_world_authoritative"]) for row in rows
        ),
        "all_runs_real_gpu_accelerated": all_accelerated,
        "performance": _performance(records),
        "experiment_counts": {
            key: payload.get(key)
            for key in (
                "panel_count",
                "completed_panel_count",
                "acute_analysis_eligible_panel_count",
                "evolutionary_analysis_eligible_checkpoint_count",
            )
            if key in payload
        },
        "failed_backend_records": [row for row in rows if row not in accelerated][:32],
    }
    if not rows:
        summary["recommendation"] = "no-backend-provenance-records-found"
    elif all_accelerated:
        summary["recommendation"] = "gpu-execution-confirmed-scientific-and-speedup-claims-separate"
    else:
        summary["recommendation"] = "not-all-runs-real-gpu-accelerated"
    return summary


def build_audit(results: Iterable[tuple[str, Path]]) -> dict[str, Any]:
    rows = [audit_result(label, path.resolve()) for label, path in results]
    return {
        "schema": SCHEMA,
        "results": rows,
        "all_results_have_backend_records": bool(rows)
        and all(row["run_record_count"] > 0 for row in rows),
        "all_runs_real_gpu_accelerated": bool(rows)
        and all(row["all_runs_real_gpu_accelerated"] for row in rows),
        "recommendation": (
            "gpu-execution-confirmed-scientific-and-speedup-claims-separate"
            if rows and all(row["all_runs_real_gpu_accelerated"] for row in rows)
            else "inspect-backend-provenance-before-gpu-claim"
        ),
        "interpretation_boundary": (
            "This audit verifies recorded execution provenance and summarizes timing/transfer "
            "diagnostics. It does not prove CPU/GPU semantic parity, a performance speedup, or "
            "any scientific effect. Parity requires the target-device test_parity suite and a "
            "speedup claim requires a paired benchmark on the same checkpoint and hardware."
        ),
    }


def render_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# GPU execution provenance audit",
        "",
        f"Schema: `{payload['schema']}`",
        "",
        "| Result | Runs | Accelerated | Fallback | Strict reference | Median seconds/tick | Median H2D bytes | Median D2H bytes | Real GPU only |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in payload["results"]:
        perf = row["performance"]
        lines.append(
            f"| {row['label']} | {row['run_record_count']} | {row['accelerated_run_count']} | "
            f"{row['fallback_run_count']} | {row['strict_reference_run_count']} | "
            f"{perf['window_seconds_per_tick']['median']} | "
            f"{perf['gpu_h2d_bytes']['median']} | {perf['gpu_d2h_bytes']['median']} | "
            f"{row['all_runs_real_gpu_accelerated']} |"
        )
    lines += [
        "",
        f"Recommendation: `{payload['recommendation']}`",
        "",
        payload["interpretation_boundary"],
        "",
    ]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--result", action="append", required=True, help="LABEL=path/to/result.json")
    parser.add_argument("--output", required=True)
    args = parser.parse_args(argv)
    audit = build_audit(parse_result_spec(value) for value in args.result)
    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=True)
    (output / "gpu_execution_audit.json").write_text(
        json.dumps(audit, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    (output / "gpu_execution_audit.md").write_text(render_markdown(audit), encoding="utf-8")
    print(json.dumps({"recommendation": audit["recommendation"]}))
    return 0 if audit["all_results_have_backend_records"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
