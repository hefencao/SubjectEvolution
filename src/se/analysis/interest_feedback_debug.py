"""Summarize D1-X delayed material-interest relationship debug runs."""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any


def _json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _number(row: dict[str, str], key: str, default: float = 0.0) -> float:
    value = row.get(key)
    try:
        return float(value) if value not in (None, "") else default
    except ValueError:
        return default


def summarize(*, source_root: str | Path, output: str | Path) -> dict[str, Any]:
    root = Path(source_root)
    seed_dirs = sorted(path for path in root.glob("seed_*") if path.is_dir())
    if not seed_dirs and (root / "summary.json").is_file():
        seed_dirs = [root]
    runs: list[dict[str, Any]] = []
    for seed_dir in seed_dirs:
        metrics = _rows(seed_dir / "metrics.csv")
        if not metrics:
            continue
        final = metrics[-1]
        manifest = _json(seed_dir / "run_manifest.json")
        config = _json(seed_dir / "resolved_config.json")
        runs.append({
            "run": seed_dir.name,
            "seed": manifest.get("seed"),
            "requested_backend": manifest.get("requested_backend"),
            "execution_backend": manifest.get("execution_backend"),
            "config_sha256": manifest.get("config_sha256"),
            "final_tick": int(_number(final, "tick")),
            "final_alive": int(_number(final, "alive")),
            "minimum_alive": int(min(_number(row, "alive") for row in metrics)),
            "final_groups": int(_number(final, "groups")),
            "final_grouped_fraction": _number(final, "grouped_fraction"),
            "relation_update_schema": final.get("relation_update_schema"),
            "relation_edge_count": int(_number(final, "relation_edge_count")),
            "relation_trust_mean": _number(final, "relation_trust_mean"),
            "relation_trust_std": _number(final, "relation_trust_std"),
            "relation_partner_differentiation_mean_std": _number(
                final, "relation_partner_differentiation_mean_std"
            ),
            "interest_feedback_settlements_total": int(_number(
                final, "interest_feedback_settlements_total"
            )),
            "interest_feedback_positive_total": int(_number(
                final, "interest_feedback_positive_total"
            )),
            "interest_feedback_negative_total": int(_number(
                final, "interest_feedback_negative_total"
            )),
            "interest_feedback_neutral_total": int(_number(
                final, "interest_feedback_neutral_total"
            )),
            "interest_feedback_material_total": _number(
                final, "interest_feedback_material_total"
            ),
            "fixed_trust_gain": config.get("social", {}).get("trust_gain_share"),
            "fixed_trust_loss": config.get("social", {}).get("trust_loss_failed"),
        })
    semantics_ready = bool(runs and all(
        run["relation_update_schema"] == "delayed-material-interest-v1"
        and float(run.get("fixed_trust_gain") or 0.0) == 0.0
        and float(run.get("fixed_trust_loss") or 0.0) == 0.0
        and run["interest_feedback_settlements_total"] > 0
        and run["interest_feedback_material_total"] > 0.0
        for run in runs
    ))
    population_debug_ready = bool(
        runs and all(run["minimum_alive"] >= 64 for run in runs)
    )
    report = {
        "schema": "delayed-material-interest-debug-summary-v1",
        "source_root": str(root),
        "runs": runs,
        "run_count": len(runs),
        "semantics_ready": semantics_ready,
        "population_debug_ready": population_debug_ready,
        "epoch_1_ready": False,
        "missing_epoch_1_evidence": [
            "independent multi-seed persistence across multiple generations",
            "partner-network prediction beyond proximity, kinship and encounter frequency",
            "shared-checkpoint feedback neutralization",
            "non-material delayed consequences such as protection and information value",
        ],
        "authorization": {
            "continue_interest_feedback_development": semantics_ready,
            "formal_long_horizon_panel": False,
            "epoch_1_base_checkpoint": False,
            "group_rule_implementation": False,
            "formal_subjecthood_claim": False,
            "gene_audit": False,
        },
        "interpretation_boundary": (
            "This debug report verifies removal of fixed SHARE trust bonuses and delayed "
            "learning from realized bilateral material return. It is not an Epoch 1 "
            "qualification and does not make current group labels into subjects."
        ),
    }
    destination = Path(output)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args(argv)
    print(json.dumps(summarize(source_root=args.source_root, output=args.output), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
