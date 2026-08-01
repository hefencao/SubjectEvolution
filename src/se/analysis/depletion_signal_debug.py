"""Summarize D1-U competition costs and signal-transport debug runs."""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any


def _json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _metrics(path: Path) -> dict[str, float]:
    totals = {name: 0.0 for name in (
        "harvest_contest_events", "harvest_contest_pressure",
        "harvest_contest_energy", "harvest_contest_integrity_damage",
        "resource_load_movement_energy",
    )}
    if not path.is_file():
        return totals
    with path.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            for name in totals:
                raw = row.get(f"{name}_step")
                if raw not in (None, ""):
                    totals[name] += float(raw)
    return totals


def summarize(*, source_root: str | Path, output: str | Path) -> dict[str, Any]:
    root = Path(source_root)
    seed_dirs = sorted(path for path in root.glob("seed_*") if path.is_dir())
    if not seed_dirs and (root / "summary.json").is_file():
        seed_dirs = [root]
    runs: list[dict[str, Any]] = []
    for seed_dir in seed_dirs:
        summary = _json(seed_dir / "summary.json")
        manifest = _json(seed_dir / "run_manifest.json")
        config = _json(seed_dir / "resolved_config.json")
        totals = _metrics(seed_dir / "metrics.csv")
        runs.append({
            "run": seed_dir.name,
            "seed": manifest.get("seed"),
            "requested_backend": manifest.get("requested_backend"),
            "execution_backend": manifest.get("execution_backend"),
            "config_sha256": manifest.get("config_sha256"),
            "alive": summary.get("alive"),
            **totals,
            "competition_semantics": config.get("entities", {}).get("resource_contest_schema"),
            "resource_signal_semantics": config.get("information", {}).get("resource_signal_observation_schema"),
            "field_signal_transport": config.get("environment", {}).get("signal_propagation_schema"),
            "direct_message_transport": config.get("information", {}).get("direct_message_propagation_schema"),
            "duplicate_body_cost_absent": bool(
                totals["harvest_contest_energy"] == 0.0
                and totals["harvest_contest_integrity_damage"] == 0.0
            ),
        })
    report = {
        "schema": "depletion-signal-debug-summary-v1",
        "source_root": str(root),
        "runs": runs,
        "run_count": len(runs),
        "semantics_ready": bool(runs and all(
            run["competition_semantics"] == "rival-harvest-depletion-pressure-v2"
            and run["resource_signal_semantics"] == "post-harvest-current-v2"
            and run["field_signal_transport"] == "terrain-resisted-diffusion-v1"
            and run["direct_message_transport"] == "terrain-distance-attenuated-v1"
            and run["duplicate_body_cost_absent"]
            for run in runs
        )),
        "authorization": {
            "continue_environment_debugging": True,
            "formal_environment_panel": False,
            "gene_audit": False,
            "scout_role_claim": False,
        },
        "interpretation_boundary": (
            "This report checks physical semantics and execution plumbing only. Event counts "
            "or backend differences are not evidence of benefit, selection, or a social role."
        ),
    }
    destination = Path(output)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report


def contrast(*, cpu: str | Path, accelerated: str | Path, output: str | Path) -> dict[str, Any]:
    left = _json(Path(cpu))
    right = _json(Path(accelerated))
    left_runs = left.get("runs", [])
    right_runs = right.get("runs", [])
    comparable = bool(left_runs and right_runs)
    pairs: list[dict[str, Any]] = []
    if comparable:
        a, b = left_runs[0], right_runs[0]
        pairs.append({
            "same_seed": a.get("seed") == b.get("seed"),
            "same_config_sha256": a.get("config_sha256") == b.get("config_sha256"),
            "cpu_execution_backend": a.get("execution_backend"),
            "accelerated_execution_backend": b.get("execution_backend"),
            "alive_delta": None if a.get("alive") is None or b.get("alive") is None else int(b["alive"]) - int(a["alive"]),
            "contest_event_delta": float(b.get("harvest_contest_events", 0.0)) - float(a.get("harvest_contest_events", 0.0)),
        })
    report = {
        "schema": "mechanism-backend-debug-contrast-v1",
        "comparable": comparable,
        "pairs": pairs,
        "both_semantics_ready": bool(left.get("semantics_ready") and right.get("semantics_ready")),
        "backend_parity_claim": False,
        "authorization": {
            "debug_backend_sensitive_mechanism": True,
            "formal_scientific_equivalence": False,
            "gene_audit": False,
        },
        "interpretation_boundary": (
            "Chaotic trajectories need not be identical. The contrast only requires the same "
            "configuration and corrected physical semantics to execute on both backends."
        ),
    }
    destination = Path(output)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    summary = sub.add_parser("summary")
    summary.add_argument("--source-root", required=True)
    summary.add_argument("--output", required=True)
    compare = sub.add_parser("contrast")
    compare.add_argument("--cpu", required=True)
    compare.add_argument("--accelerated", required=True)
    compare.add_argument("--output", required=True)
    args = parser.parse_args(argv)
    if args.command == "summary":
        report = summarize(source_root=args.source_root, output=args.output)
    else:
        report = contrast(cpu=args.cpu, accelerated=args.accelerated, output=args.output)
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
