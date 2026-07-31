"""Reclassify integrated inherited-coordinate retention with relative, cross-seed evidence.

The v1 persistence screen was deliberately conservative, but its near-zero loss
threshold is too insensitive for a continuous 704-coordinate genome over only a
few generations.  This audit consumes the frozen v1 measurements and classifies
relative contraction without turning every coordinate into a separate candidate
experiment.  Demographic expansion or lineage concentration blocks adjustment
authorization even when coordinates are flagged.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import json
import math
from pathlib import Path
from typing import Any

from se.cfg import load_config

SCHEMA = "integrated-genetic-retention-audit-v2"
STATUS_ORDER = ("lost", "strong_thinning", "moderate_thinning", "concentrated", "retained")


def _load(path: str | Path) -> dict[str, Any]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"expected JSON object: {path}")
    return payload


def _seed_status(observation: dict[str, Any]) -> tuple[str, dict[str, float]]:
    ref_std = float(observation["reference_std"])
    final_std = float(observation["final_std"])
    ref_active = float(observation["reference_active_fraction"])
    final_active = float(observation["final_active_fraction"])
    std_ratio = final_std / max(ref_std, 0.02)
    active_delta = final_active - ref_active
    if final_active <= 0.05 and final_std <= 0.02:
        status = "lost"
    elif std_ratio <= 0.60 or active_delta <= -0.30:
        status = "strong_thinning"
    elif (std_ratio <= 0.80 and active_delta <= -0.10) or active_delta <= -0.20:
        status = "moderate_thinning"
    elif std_ratio <= 0.80:
        status = "concentrated"
    else:
        status = "retained"
    return status, {"std_ratio": std_ratio, "active_fraction_delta": active_delta}


def _aggregate_status(counts: Counter[str], quorum: int) -> str:
    # Cumulative severity avoids discarding a repeated contraction signal merely
    # because one seed crosses the adjacent threshold and another does not.
    if counts["lost"] >= quorum:
        return "lost"
    if counts["lost"] + counts["strong_thinning"] >= quorum:
        return "strong_thinning"
    if counts["lost"] + counts["strong_thinning"] + counts["moderate_thinning"] >= quorum:
        return "moderate_thinning"
    if sum(counts[name] for name in STATUS_ORDER[:-1]) >= quorum:
        return "concentrated"
    return "retained"


def build_report(
    *,
    gene_persistence: str | Path,
    long_run_analysis: str | Path,
    health_report: str | Path,
    config: str | Path,
    equilibrium_report: str | Path | None = None,
) -> dict[str, Any]:
    persistence = _load(gene_persistence)
    long_run = _load(long_run_analysis)
    health = _load(health_report)
    equilibrium = _load(equilibrium_report) if equilibrium_report is not None else None
    cfg = load_config(config)
    genes_in = persistence.get("genes")
    if not isinstance(genes_in, list) or not genes_in:
        raise ValueError("gene persistence report contains no coordinates")
    seed_count = int(persistence.get("seed_count", 0))
    if seed_count < 2:
        raise ValueError("integrated retention requires at least two independent seeds")
    quorum = math.floor(seed_count / 2) + 1

    genes: list[dict[str, Any]] = []
    status_counts: Counter[str] = Counter()
    block_counts: dict[str, Counter[str]] = defaultdict(Counter)
    for source in genes_in:
        observations = []
        counts: Counter[str] = Counter()
        for raw in source.get("seeds", []):
            status, diagnostics = _seed_status(raw)
            row = dict(raw)
            row.update(diagnostics)
            row["relative_status"] = status
            observations.append(row)
            counts[status] += 1
        if len(observations) != seed_count:
            raise ValueError(f"coordinate {source.get('index')} does not cover all seeds")
        status = _aggregate_status(counts, quorum)
        block = str(source["block"])
        row = {
            "index": int(source["index"]),
            "name": str(source["name"]),
            "block": block,
            "status": status,
            "seed_status_counts": dict(sorted(counts.items())),
            "equal_seed_mean_std_ratio": sum(o["std_ratio"] for o in observations) / seed_count,
            "equal_seed_mean_active_fraction_delta": sum(o["active_fraction_delta"] for o in observations) / seed_count,
            "equal_seed_final_active_fraction": float(source["equal_seed_final_active_fraction"]),
            "equal_seed_final_descendant_active_fraction": float(source["equal_seed_final_descendant_active_fraction"]),
            "seeds": observations,
        }
        genes.append(row)
        status_counts[status] += 1
        block_counts[block][status] += 1

    initial = int(cfg.world.initial_entities)
    demographic_rows = []
    expanding = 0
    lineage_concentrated = 0
    for run in long_run.get("runs", []):
        final_alive = int(run.get("alive_final", 0))
        peak_tick = int(run.get("alive_peak_tick", -1))
        final_tick = int(run.get("final_tick", -2))
        growth_multiple = final_alive / max(initial, 1)
        at_endpoint_peak = peak_tick == final_tick and int(run.get("alive_peak", 0)) == final_alive
        largest = float(run.get("largest_lineage_fraction_final", 1.0))
        effective = float(run.get("effective_lineages_final", 0.0))
        is_expanding = bool(growth_multiple > 2.0 and at_endpoint_peak)
        is_concentrated = bool(largest > 0.15 or effective < initial * 0.125)
        expanding += int(is_expanding)
        lineage_concentrated += int(is_concentrated)
        demographic_rows.append({
            "run": run.get("run_name"),
            "final_tick": final_tick,
            "final_alive": final_alive,
            "final_alive_multiple_of_initial": growth_multiple,
            "endpoint_is_population_peak": at_endpoint_peak,
            "effective_lineages_final": effective,
            "largest_lineage_fraction_final": largest,
            "strategy_effective_dimensions_final": run.get("strategy_effective_dimensions_final"),
            "resource_affinity_effective_dimensions_final": run.get("resource_affinity_effective_dimensions_final"),
            "active_expansion_confound": is_expanding,
            "lineage_concentration_confound": is_concentrated,
        })

    sample_eligible = bool(health.get("ready")) and bool(persistence.get("sample_eligible"))
    explicit_equilibrium_ready = bool(equilibrium and equilibrium.get("ready"))
    demographic_expansion_clear = bool(demographic_rows) and expanding == 0
    equilibrium_supported = explicit_equilibrium_ready and demographic_expansion_clear
    lineage_breadth_supported = bool(demographic_rows) and lineage_concentrated == 0
    adjustment_authorized = sample_eligible and equilibrium_supported and lineage_breadth_supported
    flagged = [g for g in genes if g["status"] != "retained"]
    severe = [g for g in genes if g["status"] in {"lost", "strong_thinning"}]
    return {
        "schema": SCHEMA,
        "inputs": {
            "gene_persistence": str(gene_persistence),
            "long_run_analysis": str(long_run_analysis),
            "health_report": str(health_report),
            "equilibrium_report": str(equilibrium_report) if equilibrium_report is not None else None,
            "config": str(config),
        },
        "sample_eligible_for_diagnostics": sample_eligible,
        "equilibrium_report_present": equilibrium is not None,
        "explicit_equilibrium_ready": explicit_equilibrium_ready,
        "demographic_expansion_clear": demographic_expansion_clear,
        "equilibrium_supported": equilibrium_supported,
        "lineage_breadth_supported": lineage_breadth_supported,
        "adjustment_authorized": adjustment_authorized,
        "seed_count": seed_count,
        "cross_seed_quorum": quorum,
        "initial_population": initial,
        "demographic_confound": {
            "active_expansion_seed_count": expanding,
            "lineage_concentration_seed_count": lineage_concentrated,
            "runs": demographic_rows,
        },
        "thresholds": {
            "absolute_loss_active_fraction": 0.05,
            "absolute_loss_std": 0.02,
            "strong_thinning_std_ratio": 0.60,
            "strong_thinning_active_fraction_delta": -0.30,
            "moderate_thinning_std_ratio": 0.80,
            "moderate_thinning_active_fraction_delta": -0.10,
            "standalone_moderate_active_fraction_delta": -0.20,
        },
        "genome_size": len(genes),
        "status_counts": {name: status_counts.get(name, 0) for name in STATUS_ORDER},
        "block_status_counts": {
            block: {name: counts.get(name, 0) for name in STATUS_ORDER}
            for block, counts in sorted(block_counts.items())
        },
        "flagged_coordinate_count": len(flagged),
        "severe_coordinate_count": len(severe),
        "severe_coordinates": severe,
        "flagged_coordinates": flagged,
        "genes": genes,
        "interpretation": (
            "relative-retention-screen-confounded-by-active-expansion-and-lineage-concentration"
            if not adjustment_authorized
            else "relative-retention-screen-eligible-for-block-level-targeted-diagnosis"
        ),
        "causal_effect_claim_authorized": False,
        "selection_claim_authorized": False,
        "per_gene_experiment_generation_authorized": False,
        "next_action": (
            "qualify-a-settled-shared-resource-flux-before-any-coordinate-adjustment"
            if not equilibrium_supported
            else "diagnose-only-cross-seed-severe-or-block-level-repeated-contraction"
        ),
    }


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Integrated genetic retention audit v2", "",
        f"- diagnostics eligible: **{report['sample_eligible_for_diagnostics']}**",
        f"- equilibrium supported: **{report['equilibrium_supported']}**",
        f"- lineage breadth supported: **{report['lineage_breadth_supported']}**",
        f"- adjustment authorized: **{report['adjustment_authorized']}**",
        f"- genome coordinates: {report['genome_size']}",
        f"- status counts: `{report['status_counts']}`", "",
        "## Demographic confound", "",
        "| run | alive / initial | endpoint peak | effective lineages | largest lineage | expanding | concentrated |",
        "|---|---:|---|---:|---:|---|---|",
    ]
    for row in report["demographic_confound"]["runs"]:
        lines.append(
            f"| {row['run']} | {row['final_alive_multiple_of_initial']:.3f} | "
            f"{row['endpoint_is_population_peak']} | {row['effective_lineages_final']:.3f} | "
            f"{row['largest_lineage_fraction_final']:.3f} | {row['active_expansion_confound']} | "
            f"{row['lineage_concentration_confound']} |"
        )
    lines += ["", "## Blocks", "", "| block | retained | concentrated | moderate | strong | lost |", "|---|---:|---:|---:|---:|---:|"]
    for block, counts in report["block_status_counts"].items():
        lines.append(f"| {block} | {counts['retained']} | {counts['concentrated']} | {counts['moderate_thinning']} | {counts['strong_thinning']} | {counts['lost']} |")
    lines += ["", "## Severe coordinates", "", "| index | coordinate | block | status |", "|---:|---|---|---|"]
    for gene in report["severe_coordinates"]:
        lines.append(f"| {gene['index']} | `{gene['name']}` | {gene['block']} | {gene['status']} |")
    lines += ["", "> Flags are screening signals, not proof of benefit, harm, selection, or a need for a dedicated environment. Active expansion blocks adjustment authorization.", ""]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gene-persistence", required=True)
    parser.add_argument("--long-run-analysis", required=True)
    parser.add_argument("--health-report", required=True)
    parser.add_argument("--equilibrium-report")
    parser.add_argument("--config", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args(argv)
    report = build_report(
        gene_persistence=args.gene_persistence,
        long_run_analysis=args.long_run_analysis,
        health_report=args.health_report,
        equilibrium_report=args.equilibrium_report,
        config=args.config,
    )
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    output.with_suffix(".md").write_text(render_markdown(report), encoding="utf-8")
    print(json.dumps({"status_counts": report["status_counts"], "adjustment_authorized": report["adjustment_authorized"], "output": str(output)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
