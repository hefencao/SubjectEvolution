"""Audit sampling support in D3-F processing-response result files.

The audit never changes simulation state and never treats movement events as
independent replicates.  It partitions cumulative trajectories into fixed time
blocks, reports how much each block contributes, and separates mechanism
integrity from population-supported long-run or evolutionary inference.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Iterable

import numpy as np

REPORT_SCHEMA = "d3-processing-response-adequacy-audit-v1"
ACCEPTED_RESULT_SCHEMAS = {
    "d3-spatial-processing-response-results-v1",
    "d3-spatial-processing-response-results-v2",
}


def _cumulative(row: dict[str, Any]) -> dict[str, float]:
    return {key: float(value) for key, value in row.get("cumulative", {}).items()}


def _delta(end: dict[str, float], start: dict[str, float], key: str) -> float:
    return float(end.get(key, 0.0) - start.get(key, 0.0))


def _mean_from_sums(
    end: dict[str, float],
    start: dict[str, float],
    *,
    numerator: str,
    denominator: str,
) -> float:
    den = _delta(end, start, denominator)
    return _delta(end, start, numerator) / den if den > 0.0 else 0.0


def _trajectory_blocks(
    trajectory: list[dict[str, Any]],
    *,
    block_ticks: int,
    min_alive: int,
) -> list[dict[str, Any]]:
    if not trajectory:
        return []
    rows = sorted(trajectory, key=lambda row: int(row["tick"]))
    by_tick = {int(row["tick"]): row for row in rows}
    start_tick = int(rows[0]["tick"])
    end_tick = int(rows[-1]["tick"])
    boundaries = [start_tick]
    next_tick = start_tick + block_ticks
    while next_tick < end_tick:
        if next_tick not in by_tick:
            raise ValueError(
                f"trajectory is missing block boundary tick {next_tick}; "
                "choose a block size aligned with the observation period"
            )
        boundaries.append(next_tick)
        next_tick += block_ticks
    if end_tick not in boundaries:
        boundaries.append(end_tick)
    blocks: list[dict[str, Any]] = []
    for left, right in zip(boundaries, boundaries[1:]):
        start = by_tick[left]
        end = by_tick[right]
        start_cumulative = _cumulative(start)
        end_cumulative = _cumulative(end)
        window_rows = [
            row for row in rows if left < int(row["tick"]) <= right
        ]
        alive_values = [int(start.get("alive", 0))] + [
            int(row.get("alive", 0)) for row in window_rows
        ]
        blocks.append(
            {
                "start_tick": left,
                "end_tick": right,
                "duration_ticks": right - left,
                "alive_start": int(start.get("alive", 0)),
                "alive_end": int(end.get("alive", 0)),
                "alive_snapshot_min": min(alive_values) if alive_values else 0,
                "alive_snapshot_mean": float(np.mean(alive_values)) if alive_values else 0.0,
                "alive_threshold_met_at_all_snapshots": bool(
                    alive_values and min(alive_values) >= min_alive
                ),
                "eligible_entity_ticks": _delta(
                    end_cumulative, start_cumulative, "eligible_entity_ticks"
                ),
                "resource_move_count": _delta(
                    end_cumulative, start_cumulative, "resource_move_count"
                ),
                "resource_move_mean_support_gain": _mean_from_sums(
                    end_cumulative,
                    start_cumulative,
                    numerator="resource_move_support_gain_sum",
                    denominator="resource_move_count",
                ),
                "resource_move_positive_support_gain_fraction": _mean_from_sums(
                    end_cumulative,
                    start_cumulative,
                    numerator="resource_move_support_gain_positive",
                    denominator="resource_move_count",
                ),
                "resource_move_mean_alignment_cosine": _mean_from_sums(
                    end_cumulative,
                    start_cumulative,
                    numerator="resource_move_alignment_cosine_sum",
                    denominator="resource_move_alignment_cosine_count",
                ),
            }
        )
    total_entity_ticks = sum(row["eligible_entity_ticks"] for row in blocks)
    total_moves = sum(row["resource_move_count"] for row in blocks)
    for row in blocks:
        row["eligible_entity_tick_fraction"] = (
            row["eligible_entity_ticks"] / total_entity_ticks
            if total_entity_ticks > 0.0
            else 0.0
        )
        row["resource_move_fraction"] = (
            row["resource_move_count"] / total_moves if total_moves > 0.0 else 0.0
        )
    return blocks


def build_adequacy_audit(
    payload: dict[str, Any],
    *,
    block_ticks: int = 300,
    min_alive: int = 100,
    burn_in_ticks: int = 300,
) -> dict[str, Any]:
    schema = str(payload.get("schema"))
    if schema not in ACCEPTED_RESULT_SCHEMAS:
        raise ValueError(f"unsupported D3-F result schema: {schema!r}")
    if block_ticks <= 0:
        raise ValueError("block_ticks must be positive")
    if min_alive <= 0:
        raise ValueError("min_alive must be positive")
    branches: list[dict[str, Any]] = []
    for pair in payload.get("pairs", []):
        seed = int(pair["seed"])
        for branch in pair.get("branches", []):
            trajectory = list(branch.get("response_trajectory", []))
            blocks = _trajectory_blocks(
                trajectory, block_ticks=block_ticks, min_alive=min_alive
            )
            below = [
                int(row["tick"])
                for row in trajectory
                if int(row.get("alive", 0)) < min_alive
            ]
            post_burn_in = [
                row for row in blocks if int(row["start_tick"]) >= burn_in_ticks
            ]
            branches.append(
                {
                    "seed": seed,
                    "branch": str(branch["branch"]),
                    "final_alive": int(branch.get("final", {}).get("alive", 0)),
                    "final_births_total": int(
                        branch.get("final", {}).get("births_total", 0)
                    ),
                    "final_deaths_total": int(
                        branch.get("final", {}).get("deaths_total", 0)
                    ),
                    "final_lineages": int(
                        branch.get("final", {}).get("lineages", 0)
                    ),
                    "first_observed_tick_below_min_alive": min(below) if below else None,
                    "blocks": blocks,
                    "initial_block_entity_tick_fraction": (
                        blocks[0]["eligible_entity_tick_fraction"] if blocks else 0.0
                    ),
                    "initial_block_resource_move_fraction": (
                        blocks[0]["resource_move_fraction"] if blocks else 0.0
                    ),
                    "post_burn_in_population_supported": bool(
                        post_burn_in
                        and all(
                            row["alive_threshold_met_at_all_snapshots"]
                            for row in post_burn_in
                        )
                    ),
                }
            )
    independent_seeds = sorted({row["seed"] for row in branches})
    mechanism_audit_complete = bool(
        payload.get("audit_completeness")
        and all(bool(value) for value in payload["audit_completeness"].values())
    )
    long_run_supported = bool(
        branches and all(row["post_burn_in_population_supported"] for row in branches)
    )
    initial_entity_share = [
        float(row["initial_block_entity_tick_fraction"]) for row in branches
    ]
    initial_move_share = [
        float(row["initial_block_resource_move_fraction"]) for row in branches
    ]
    return {
        "schema": REPORT_SCHEMA,
        "source_result_schema": schema,
        "settings": {
            "block_ticks": int(block_ticks),
            "minimum_alive": int(min_alive),
            "burn_in_ticks": int(burn_in_ticks),
            "trajectory_alive_values_are_observation_snapshots": True,
            "entity_tick_and_move_counts_are_exact_cumulative_deltas": True,
        },
        "independent_seed_count": len(independent_seeds),
        "independent_seeds": independent_seeds,
        "branch_count": len(branches),
        "branches": branches,
        "summary": {
            "mechanism_audit_complete": mechanism_audit_complete,
            "population_supported_long_run_inference": long_run_supported,
            "movement_events_are_independent_replicates": False,
            "independent_unit": "seed/checkpoint panel",
            "initial_block_entity_tick_fraction_min": min(initial_entity_share, default=0.0),
            "initial_block_entity_tick_fraction_max": max(initial_entity_share, default=0.0),
            "initial_block_resource_move_fraction_min": min(initial_move_share, default=0.0),
            "initial_block_resource_move_fraction_max": max(initial_move_share, default=0.0),
            "evolutionary_inference_supported_by_generation_data": False,
        },
        "recommendation": (
            "retain-mechanism-audit-but-replace-single-long-run-with-preregistered-acute-checkpoint-panel"
            if mechanism_audit_complete and not long_run_supported
            else "inspect-response-audit-integrity-or-sampling-support"
        ),
        "interpretation_boundary": (
            "This audit separates mechanism integrity from sampling support. "
            "Movement events are temporally and genealogically clustered and are not "
            "independent replicates. The supplied result does not contain enough generation "
            "history to authorize evolutionary inference."
        ),
    }


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# D3-F response sampling-adequacy audit",
        "",
        f"Schema: `{report['schema']}`",
        "",
        "| Seed | Branch | First < alive floor | Initial entity-tick share | Initial move share | Post-burn-in population support |",
        "|---:|---|---:|---:|---:|---:|",
    ]
    for row in report["branches"]:
        lines.append(
            f"| {row['seed']} | {row['branch']} | "
            f"{row['first_observed_tick_below_min_alive']} | "
            f"{row['initial_block_entity_tick_fraction']} | "
            f"{row['initial_block_resource_move_fraction']} | "
            f"{row['post_burn_in_population_supported']} |"
        )
    lines += ["", "## Summary", ""]
    lines += [
        f"- {key.replace('_', ' ')}: `{value}`"
        for key, value in report["summary"].items()
    ]
    lines += [
        "",
        f"Recommendation: `{report['recommendation']}`",
        "",
        report["interpretation_boundary"],
        "",
    ]
    return "\n".join(lines)


def audit_file(
    source: str | Path,
    *,
    output: str | Path | None = None,
    block_ticks: int = 300,
    min_alive: int = 100,
    burn_in_ticks: int = 300,
) -> dict[str, Any]:
    payload = json.loads(Path(source).read_text(encoding="utf-8"))
    report = build_adequacy_audit(
        payload,
        block_ticks=block_ticks,
        min_alive=min_alive,
        burn_in_ticks=burn_in_ticks,
    )
    if output is not None:
        destination = Path(output)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(
            json.dumps(report, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        destination.with_suffix(".md").write_text(
            render_markdown(report), encoding="utf-8"
        )
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results", required=True)
    parser.add_argument("--output")
    parser.add_argument("--block-ticks", type=int, default=300)
    parser.add_argument("--min-alive", type=int, default=100)
    parser.add_argument("--burn-in-ticks", type=int, default=300)
    args = parser.parse_args(argv)
    report = audit_file(
        args.results,
        output=args.output,
        block_ticks=args.block_ticks,
        min_alive=args.min_alive,
        burn_in_ticks=args.burn_in_ticks,
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
