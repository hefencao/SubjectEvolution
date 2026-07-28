"""Audit D2-L regulatory-physiology flow conservation.

The audit is deliberately narrower than a module-maturity or ecological gate.
It verifies that cumulative runtime flow counters are finite and non-negative,
then reports whether the two messenger buses and their finite shared precursor
actually turned over.  Legacy v2 results remain readable so the v0.51 sign
error can be identified without rewriting the historical artifact.
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any

ASSESSMENT_SCHEMA = "d2-regulatory-physiology-flow-assessment-v1"
RESULT_SCHEMAS = {
    "d2-regulatory-physiology-results-v1",
    "d2-regulatory-physiology-results-v2",
}
LEGACY_PHYSIOLOGY_SCHEMA = "transport-metabolism-messenger-tissue-v2"
CONSERVATIVE_PHYSIOLOGY_SCHEMA = "transport-metabolism-messenger-tissue-v3"

FLOW_FIELDS = (
    "physiology_oxygen_uptake_total",
    "physiology_oxygen_use_total",
    "physiology_messenger_synthesis_total",
    "physiology_messenger_decay_total",
    "physiology_messenger_precursor_used_total",
    "physiology_messenger_precursor_recovered_total",
    "physiology_messenger_energy_total",
    "physiology_computation_energy_total",
    "physiology_computation_oxygen_total",
    "physiology_fatigue_generated_total",
    "physiology_fatigue_cleared_total",
    "physiology_hypoxia_tissue_damage_total",
    "physiology_wear_tissue_damage_total",
    "physiology_wear_structure_damage_total",
    "physiology_repair_material_total",
    "physiology_repair_tissue_total",
    "physiology_repair_structure_total",
)


def _load(path: str | Path) -> dict[str, Any]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    schema = str(payload.get("schema", ""))
    if schema not in RESULT_SCHEMAS:
        raise ValueError(f"unsupported D2-L result schema: {schema!r}")
    return payload


def _physiology_schema(result: dict[str, Any]) -> str:
    plan = result.get("plan", {})
    if isinstance(plan, dict):
        value = plan.get("physiology_schema")
        if isinstance(value, str) and value:
            return value
    return LEGACY_PHYSIOLOGY_SCHEMA


def assess(result: dict[str, Any]) -> dict[str, Any]:
    runs = result.get("runs", [])
    if not isinstance(runs, list) or not runs:
        raise ValueError("D2-L result contains no completed runs")
    rows: list[dict[str, Any]] = []
    invalid_entries: list[dict[str, Any]] = []
    for run in runs:
        seed = int(run["seed"])
        final = run.get("final", {})
        values: dict[str, float] = {}
        for field in FLOW_FIELDS:
            raw = final.get(field, 0.0)
            value = float(raw)
            values[field] = value
            if not math.isfinite(value) or value < -1.0e-12:
                invalid_entries.append({"seed": seed, "field": field, "value": value})
        rows.append(
            {
                "seed": seed,
                "messenger_synthesis": values["physiology_messenger_synthesis_total"],
                "messenger_decay": values["physiology_messenger_decay_total"],
                "precursor_used": values[
                    "physiology_messenger_precursor_used_total"
                ],
                "precursor_recovered": values[
                    "physiology_messenger_precursor_recovered_total"
                ],
                "messenger_energy": values["physiology_messenger_energy_total"],
                "computation_energy": values[
                    "physiology_computation_energy_total"
                ],
                "all_flows_finite_non_negative": not any(
                    item["seed"] == seed for item in invalid_entries
                ),
            }
        )

    physiology_schema = _physiology_schema(result)
    ledger_valid = not invalid_entries
    messenger_turnover = ledger_valid and all(
        row["messenger_synthesis"] > 0.0 and row["messenger_decay"] > 0.0
        for row in rows
    )
    precursor_turnover = ledger_valid and all(
        row["precursor_used"] > 0.0 and row["precursor_recovered"] > 0.0
        for row in rows
    )
    conservative_schema = physiology_schema == CONSERVATIVE_PHYSIOLOGY_SCHEMA
    passed = bool(ledger_valid and conservative_schema)
    if not ledger_valid:
        recommendation = "rerun-conservative-v3-same-seeds"
    elif not conservative_schema:
        recommendation = "migrate-to-conservative-v3-before-further-use"
    elif not messenger_turnover or not precursor_turnover:
        recommendation = "inspect-regulatory-drive-and-substrate-availability"
    else:
        recommendation = "retain-conservative-substrate-and-continue-ecology-chain"
    return {
        "schema": ASSESSMENT_SCHEMA,
        "source_result_schema": result["schema"],
        "physiology_schema": physiology_schema,
        "completed_seed_count": len(rows),
        "passed": passed,
        "flow_ledger_valid": ledger_valid,
        "conservative_schema_active": conservative_schema,
        "messenger_turnover_observed_in_every_seed": messenger_turnover,
        "finite_precursor_turnover_observed_in_every_seed": precursor_turnover,
        "invalid_flow_entries": invalid_entries,
        "rows": rows,
        "recommendation": recommendation,
        "module_copy_number_ready": False,
        "ecological_differentiation_claim": False,
        "interpretation_boundary": (
            "This assessment verifies cumulative flow-sign and finite-value "
            "invariants for the regulatory physiology substrate. It does not "
            "measure module maturity, ecological differentiation, or a named organ."
        ),
    }


def render_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# D2-L regulatory physiology flow assessment",
        "",
        f"Schema: `{payload['schema']}`",
        f"Source physiology schema: `{payload['physiology_schema']}`",
        f"Passed conservative ledger: `{payload['passed']}`",
        "",
        "| Seed | Synthesis | Decay | Precursor used | Precursor recovered | Messenger energy | Ledger valid |",
        "|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in payload["rows"]:
        lines.append(
            f"| {row['seed']} | {row['messenger_synthesis']} | "
            f"{row['messenger_decay']} | {row['precursor_used']} | "
            f"{row['precursor_recovered']} | {row['messenger_energy']} | "
            f"{row['all_flows_finite_non_negative']} |"
        )
    lines.extend(
        [
            "",
            "## Decision",
            "",
            f"`{payload['recommendation']}`",
            "",
            f"Invalid flow entries: `{len(payload['invalid_flow_entries'])}`",
            "",
            payload["interpretation_boundary"],
            "",
        ]
    )
    return "\n".join(lines)


def write_assessment(
    result_path: str | Path,
    output_dir: str | Path,
) -> dict[str, Any]:
    payload = assess(_load(result_path))
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    (output / "d2_regulatory_physiology_flow_assessment.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (output / "d2_regulatory_physiology_flow_assessment.md").write_text(
        render_markdown(payload), encoding="utf-8"
    )
    return payload


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results", required=True)
    parser.add_argument("--output", required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    payload = write_assessment(args.results, args.output)
    print(
        json.dumps(
            {
                "passed": payload["passed"],
                "recommendation": payload["recommendation"],
                "assessment": str(
                    Path(args.output)
                    / "d2_regulatory_physiology_flow_assessment.json"
                ),
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
