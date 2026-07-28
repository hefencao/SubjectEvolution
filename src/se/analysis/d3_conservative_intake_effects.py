"""Reassess D3-B intake results with scale-aware floating-point tolerance."""
from __future__ import annotations
import argparse, json
from pathlib import Path
from typing import Any
import numpy as np

ASSESSMENT_SCHEMA = "d3-conservative-intake-assessment-v1"


def assess_payload(payload: dict[str, Any]) -> dict[str, Any]:
    rows=[]
    for row in payload.get("intake_ledger", []):
        harvested=np.asarray(row["actual_harvested"], dtype=np.float64)
        overflow=np.asarray(row["post_assimilation_overflow"], dtype=np.float64)
        scale=np.maximum(harvested, 1.0)
        ratios=overflow/scale
        rows.append({
            "seed": int(row["seed"]),
            "overflow": overflow.tolist(),
            "overflow_fraction_of_harvest": ratios.tolist(),
            "max_overflow_fraction": float(np.max(ratios, initial=0.0)),
            "within_tolerance": bool(np.all(overflow <= 2.0e-5*scale)),
            "intake_ledger_valid": bool(row.get("valid", False)),
        })
    store_valid=all(bool(row.get("valid", False)) for row in payload.get("store_ledger", []))
    passed=bool(rows and all(row["within_tolerance"] and row["intake_ledger_valid"] for row in rows) and store_valid)
    return {
        "schema": ASSESSMENT_SCHEMA,
        "source_schema": payload.get("schema"),
        "completed_seed_count": int(payload.get("completed_seed_count", len(rows))),
        "rows": rows,
        "store_ledger_valid_in_every_seed": store_valid,
        "passed": passed,
        "recommendation": (
            "retain-conservative-intake-and-continue-external-resource-recycling"
            if passed else "inspect-intake-or-store-ledger-before-external-recycling"
        ),
        "interpretation_boundary": (
            "Post-assimilation overflow is evaluated relative to per-channel harvested mass, "
            "not by exact zero or an absolute run-length-dependent threshold."
        ),
    }


def render_markdown(report: dict[str, Any]) -> str:
    lines=["# D3-B scale-aware intake assessment", "", f"Passed: `{report['passed']}`", "", "| Seed | Max overflow fraction | Within tolerance |", "|---:|---:|---:|"]
    for row in report["rows"]:
        lines.append(f"| {row['seed']} | {row['max_overflow_fraction']:.12g} | {row['within_tolerance']} |")
    lines += ["", f"Recommendation: `{report['recommendation']}`", "", report["interpretation_boundary"], ""]
    return "\n".join(lines)


def main(argv: list[str] | None=None) -> int:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results", required=True)
    parser.add_argument("--output", required=True)
    args=parser.parse_args(argv)
    payload=json.loads(Path(args.results).read_text(encoding="utf-8"))
    report=assess_payload(payload)
    out=Path(args.output); out.mkdir(parents=True, exist_ok=True)
    (out/"d3_conservative_intake_assessment.json").write_text(json.dumps(report, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    (out/"d3_conservative_intake_assessment.md").write_text(render_markdown(report), encoding="utf-8")
    print(json.dumps({"passed": report["passed"], "recommendation": report["recommendation"]}))
    return 0

if __name__=="__main__":
    raise SystemExit(main())
