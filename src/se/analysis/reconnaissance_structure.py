"""Summarize a D1-T reconnaissance-pressure mechanism probe."""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _metric_totals(path: Path) -> dict[str, float]:
    totals = {
        "harvest_contest_events": 0.0,
        "harvest_contest_pressure": 0.0,
        "harvest_contest_energy": 0.0,
        "harvest_contest_integrity_damage": 0.0,
        "resource_load_movement_energy": 0.0,
    }
    if not path.is_file():
        return totals
    columns = {f"{name}_step": name for name in totals}
    with path.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            for column, name in columns.items():
                raw = row.get(column)
                if raw not in (None, ""):
                    totals[name] += float(raw)
    return totals



def _progress_summary(path: Path) -> dict[str, float]:
    result = {
        "minimum_alive": 0.0,
        "final_effective_lineages": 0.0,
        "final_largest_lineage_fraction": 1.0,
    }
    if not path.is_file():
        return result
    rows = [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    if not rows:
        return result
    result["minimum_alive"] = float(min(int(row.get("alive", 0)) for row in rows))
    result["final_effective_lineages"] = float(rows[-1].get("effective_lineages", 0.0))
    result["final_largest_lineage_fraction"] = float(
        rows[-1].get("largest_lineage_fraction", 1.0)
    )
    return result

def summarize(*, source_root: str | Path, output: str | Path) -> dict[str, Any]:
    root = Path(source_root)
    seed_dirs = sorted(path for path in root.glob("seed_*") if path.is_dir())
    if not seed_dirs and (root / "summary.json").is_file():
        seed_dirs = [root]
    runs: list[dict[str, Any]] = []
    for seed_dir in seed_dirs:
        runtime = _read_json(seed_dir / "summary.json")
        reconnaissance_path = seed_dir / "reconnaissance_summary.json"
        reconnaissance = (
            _read_json(reconnaissance_path)
            if reconnaissance_path.is_file()
            else {
                "persistent_reconnaissance_candidate_count": 0,
                "total_frontier_signal_events": 0,
                "total_same_group_danger_messages": 0,
                "total_aligned_flee_responses": 0,
            }
        )
        totals = _metric_totals(seed_dir / "metrics.csv")
        progress = _progress_summary(seed_dir / "evolution_progress.jsonl")
        resolved_path = seed_dir / "resolved_config.json"
        resolved = _read_json(resolved_path) if resolved_path.is_file() else {}
        initial = int(
            runtime.get("initial_population", 0)
            or resolved.get("world", {}).get("initial_entities", 0)
            or 0
        )
        alive = int(runtime.get("alive", 0) or 0)
        births = float(runtime.get("cumulative_births_per_initial", 0.0))
        descendants = float(runtime.get("descendant_alive_fraction", 0.0))
        chain = bool(
            totals["harvest_contest_events"] > 0
            and totals["resource_load_movement_energy"] > 0.0
            and reconnaissance.get("total_frontier_signal_events", 0) > 0
            and reconnaissance.get("total_same_group_danger_messages", 0) > 0
            and reconnaissance.get("total_aligned_flee_responses", 0) > 0
        )
        healthy = bool(
            initial > 0
            and progress["minimum_alive"] >= 0.5 * initial
            and births >= 0.5
            and descendants >= 0.3
            and progress["final_effective_lineages"] >= 4.0
        )
        runs.append(
            {
                "run": seed_dir.name,
                "initial_population": initial,
                "alive": alive,
                "cumulative_births_per_initial": births,
                "descendant_alive_fraction": descendants,
                **progress,
                **totals,
                **reconnaissance,
                "population_debug_substrate_ready": healthy,
                "physical_information_value_chain_observed": chain,
            }
        )
    chain_count = sum(
        run["physical_information_value_chain_observed"] for run in runs
    )
    report = {
        "schema": "reconnaissance-pressure-chain-summary-v1",
        "mode": "single-seed-environment-parameter-debug",
        "source_root": str(root),
        "observed_run_count": len(runs),
        "runs": runs,
        "physical_chain_observed_run_count": chain_count,
        "probe_mechanism_ready": bool(
            len(runs) == 1
            and chain_count == 1
            and runs[0]["population_debug_substrate_ready"]
        ),
        "authorization": {
            "continue_shared_environment_parameter_debugging": True,
            "mechanism_integration_ready": bool(
                len(runs) == 1
                and chain_count == 1
                and runs[0]["population_debug_substrate_ready"]
            ),
            "multi_seed_environment_panel": False,
            "scout_role_claim": False,
            "gene_audit": False,
            "selection_or_adaptation_claim": False,
        },
        "interpretation_boundary": (
            "The probe checks whether contest, load, inherited sensing, signal delivery and "
            "receiver response are all physically active in one run. It cannot establish a "
            "scout role, causal information benefit, persistence across seeds or evolution."
        ),
    }
    destination = Path(output)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return report


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args(argv)
    print(
        json.dumps(
            summarize(source_root=args.source_root, output=args.output),
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
