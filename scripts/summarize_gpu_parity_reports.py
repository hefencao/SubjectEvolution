#!/usr/bin/env python3
"""Summarize machine-readable reports emitted by target-device parity tests."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any, Sequence

from se.analysis.parity import SEMANTIC_PARITY_CONFIGS

SCHEMA = "gpu-parity-certificate-v1"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    digest.update(path.read_bytes())
    return digest.hexdigest()


def summarize(reports_dir: Path, project: Path) -> dict[str, Any]:
    reports_dir = reports_dir.resolve()
    project = project.resolve()
    required = ["stage-parity.json"] + [
        f"world-{Path(filename).stem}.json" for filename in SEMANTIC_PARITY_CONFIGS
    ]
    rows: list[dict[str, Any]] = []
    missing: list[str] = []
    for name in required:
        path = reports_dir / name
        if not path.is_file():
            missing.append(name)
            continue
        report = json.loads(path.read_text(encoding="utf-8"))
        rows.append(
            {
                "file": name,
                "sha256": _sha256(path),
                "passed": bool(report.get("passed")),
                "gpu_available": bool(report.get("gpu_available", True)),
                "config": report.get("config"),
                "ticks_compared": report.get("ticks_compared"),
                "first_failure": report.get("first_failure")
                or report.get("first_failure_stage"),
                "gpu_runtime": report.get("gpu_runtime"),
            }
        )
    passed = not missing and len(rows) == len(required) and all(
        row["passed"] and row["gpu_available"] for row in rows
    )
    return {
        "schema": SCHEMA,
        "passed": passed,
        "required_report_count": len(required),
        "found_report_count": len(rows),
        "missing_reports": missing,
        "reports": rows,
        "semantic_parity_configs": list(SEMANTIC_PARITY_CONFIGS),
        "validation_scope": (
            "Real-device stage parity plus paired CPU/GPU world parity for every registered "
            "semantic family. This certificate validates only the recorded source/config/device "
            "combination and does not establish performance speedup."
        ),
    }


def render_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# Target GPU parity certificate",
        "",
        f"Schema: `{payload['schema']}`",
        "",
        f"Passed: `{payload['passed']}`",
        "",
        "| Report | Passed | GPU available | Config | Ticks |",
        "|---|---:|---:|---|---:|",
    ]
    for row in payload["reports"]:
        lines.append(
            f"| {row['file']} | {row['passed']} | {row['gpu_available']} | "
            f"{row['config']} | {row['ticks_compared']} |"
        )
    if payload["missing_reports"]:
        lines += ["", f"Missing: `{payload['missing_reports']}`"]
    lines += ["", payload["validation_scope"], ""]
    return "\n".join(lines)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reports-dir", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--project", default=".")
    args = parser.parse_args(argv)
    payload = summarize(Path(args.reports_dir), Path(args.project))
    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=True)
    (output / "GPU_PARITY_CERTIFICATE.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    (output / "GPU_PARITY_CERTIFICATE.md").write_text(
        render_markdown(payload), encoding="utf-8"
    )
    print(json.dumps({"passed": payload["passed"]}))
    return 0 if payload["passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
