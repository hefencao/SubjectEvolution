"""Sequential multi-seed runner for reproducible long-horizon experiments."""

from __future__ import annotations

import argparse
from dataclasses import asdict, replace
import hashlib
import json
from pathlib import Path
import shutil

from ..cfg import load_config
from se.analysis.long_run import analyze, render_markdown
from se.analysis.selection_validity import (
    SelectionValidityThresholds,
    build_audit as build_selection_audit,
    render_markdown as render_selection_markdown,
)
from ..runtime.sim import Simulation


def parse_seeds(value: str) -> list[int]:
    seeds = [int(item.strip()) for item in value.split(",") if item.strip()]
    if not seeds:
        raise ValueError("at least one seed is required")
    if len(set(seeds)) != len(seeds):
        raise ValueError("seeds must be unique")
    return seeds


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run one configuration across several seeds, then aggregate evolution progress"
    )
    parser.add_argument("--config", required=True)
    parser.add_argument("--seeds", required=True, help="Comma-separated integer seeds")
    parser.add_argument("--output", required=True)
    parser.add_argument("--backend", choices=("cpu", "gpu", "auto"), default="auto")
    parser.add_argument("--until-tick", type=int)
    parser.add_argument(
        "--checkpoint-ticks",
        help="Comma-separated exact ticks written as full .sechk checkpoints for every seed.",
    )
    parser.add_argument(
        "--overwrite-partial",
        action="store_true",
        help="Delete and restart an incomplete seed directory.",
    )
    return parser


def _completed_tick(run_dir: Path) -> int | None:
    progress = run_dir / "evolution_progress.jsonl"
    summary = run_dir / "summary.json"
    if summary.exists():
        try:
            payload = json.loads(summary.read_text(encoding="utf-8"))
            for key in ("tick", "final_tick", "ticks"):
                if key in payload:
                    return int(payload[key])
        except (ValueError, TypeError, json.JSONDecodeError):
            pass
    if progress.exists():
        last = None
        with progress.open("r", encoding="utf-8") as handle:
            for line in handle:
                if line.strip():
                    last = json.loads(line)
        if last is not None:
            return int(last["tick"])
    return None


def main() -> None:
    args = build_parser().parse_args()
    seeds = parse_seeds(args.seeds)
    base = load_config(args.config)
    checkpoint_ticks: tuple[int, ...] = ()
    if args.checkpoint_ticks:
        checkpoint_ticks = tuple(
            sorted(set(int(item.strip()) for item in args.checkpoint_ticks.split(",") if item.strip()))
        )
        if not checkpoint_ticks or checkpoint_ticks[0] < 0:
            raise ValueError("checkpoint-ticks must contain non-negative integers")
    target_tick = base.run.ticks if args.until_tick is None else int(args.until_tick)
    if target_tick < 0:
        raise ValueError("until-tick must be non-negative")
    if checkpoint_ticks and checkpoint_ticks[-1] > target_tick:
        raise ValueError(
            f"checkpoint-ticks includes {checkpoint_ticks[-1]} beyond final tick {target_tick}"
        )
    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=True)
    base_payload = asdict(base)
    config_sha256 = hashlib.sha256(
        json.dumps(base_payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    selection_thresholds = SelectionValidityThresholds()
    multi_seed_plan = {
        "schema": "multi-seed-run-plan-v3",
        "config": str(Path(args.config)),
        "resolved_config_sha256": config_sha256,
        "seeds": seeds,
        "requested_backend": args.backend,
        "target_tick": target_tick,
        "metrics_period": int(base.run.metrics_period),
        "evolution_evaluation_period": int(base.run.evolution_evaluation_period),
        "periodic_checkpoint_period": int(base.run.checkpoint_period),
        "checkpoint_ticks": list(checkpoint_ticks or base.run.checkpoint_ticks),
        "seed_output_directories": [f"seed_{seed}" for seed in seeds],
        "failed_or_partial_seed_replaced_by_outcome": False,
        "overwrite_partial_requires_explicit_flag": True,
        "automatic_long_run_analysis": True,
        "automatic_selection_validity_audit": True,
        "selection_validity_plan": {
            "schema": "demographic-selection-validity-plan-v3",
            "thresholds": asdict(selection_thresholds),
            "independent_unit": "run-seed",
            "windows_are_independent_replicates": False,
            "feedback_to_world": False,
            "population_rescue_or_diversity_protection": False,
            "source_rule_applies_only_to_future_independent_runs": True,
        },
    }
    (output / "multi_seed_plan.json").write_text(
        json.dumps(multi_seed_plan, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    progress_paths: list[Path] = []
    auditable_runs: list[tuple[str, Path]] = []
    index: list[dict[str, object]] = []
    for seed in seeds:
        run_cfg = replace(
            base,
            run=replace(
                base.run,
                seed=seed,
                ticks=target_tick,
                checkpoint_ticks=checkpoint_ticks or base.run.checkpoint_ticks,
                full_checkpoint_enabled=(
                    True if checkpoint_ticks else base.run.full_checkpoint_enabled
                ),
            ),
        )
        run_dir = output / f"seed_{seed}"
        completed_tick = _completed_tick(run_dir) if run_dir.exists() else None
        if completed_tick is not None and completed_tick >= target_tick:
            progress = run_dir / "evolution_progress.jsonl"
            final_tick = int(completed_tick)
            alive = 0
            progress_value: str | None = None
            if progress.is_file():
                progress_paths.append(progress)
                auditable_runs.append((f"seed_{seed}", run_dir))
                with progress.open("r", encoding="utf-8") as handle:
                    final_records = [
                        json.loads(line) for line in handle if line.strip()
                    ]
                if final_records:
                    final_tick = int(final_records[-1]["tick"])
                    alive = int(final_records[-1].get("alive", 0))
                progress_value = str(progress)
            else:
                summary = run_dir / "summary.json"
                if summary.is_file():
                    payload = json.loads(summary.read_text(encoding="utf-8"))
                    alive = int(payload.get("alive", 0))
            index.append(
                {
                    "seed": seed,
                    "output": str(run_dir),
                    "final_tick": final_tick,
                    "alive": alive,
                    "evolution_progress": progress_value,
                    "status": (
                        "skipped-completed"
                        if progress_value is not None
                        else "skipped-completed-no-progress"
                    ),
                }
            )
            (output / "multi_seed_index.json").write_text(
                json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            continue
        if run_dir.exists() and any(run_dir.iterdir()):
            if not args.overwrite_partial:
                raise RuntimeError(
                    f"incomplete output exists for seed {seed}: {run_dir}; "
                    "pass --overwrite-partial to restart it"
                )
            shutil.rmtree(run_dir)
        run_dir.mkdir(parents=True, exist_ok=True)
        resolved = json.dumps(asdict(run_cfg), ensure_ascii=False, indent=2)
        (run_dir / "resolved_config.json").write_text(resolved, encoding="utf-8")
        simulation = Simulation(run_cfg, run_dir, backend=args.backend)
        final = simulation.run(until_tick=target_tick)
        progress = run_dir / "evolution_progress.jsonl"
        progress_value: str | None = None
        if progress.is_file():
            progress_paths.append(progress)
            auditable_runs.append((f"seed_{seed}", run_dir))
            progress_value = str(progress)
        index.append(
            {
                "seed": seed,
                "output": str(run_dir),
                "final_tick": target_tick,
                "alive": int(final.get("alive", 0)),
                "evolution_progress": progress_value,
                "status": "completed" if progress_value else "completed-no-progress",
            }
        )
        (output / "multi_seed_index.json").write_text(
            json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    missing_progress = [
        item["seed"] for item in index if item.get("evolution_progress") is None
    ]
    if progress_paths:
        report = analyze(progress_paths)
        report["requested_seed_count"] = len(seeds)
        report["missing_progress_seeds"] = missing_progress
        markdown = render_markdown(report)
        if missing_progress:
            markdown += (
                "\n> Warning: no evolution progress was produced for seeds "
                + ", ".join(str(value) for value in missing_progress)
                + "; the aggregate includes only available progress streams.\n"
            )
    else:
        report = {
            "schema": "multi-seed-analysis-unavailable-v1",
            "requested_seed_count": len(seeds),
            "run_count": 0,
            "missing_progress_seeds": missing_progress,
            "reason": (
                "runs completed before the first evolution-evaluation window; "
                "world outputs and exact checkpoints remain valid"
            ),
        }
        markdown = (
            "# Multi-seed analysis unavailable\n\n"
            + report["reason"]
            + "\n"
        )
    if auditable_runs:
        selection_report = build_selection_audit(
            auditable_runs, thresholds=selection_thresholds
        )
        (output / "selection_validity_plan.json").write_text(
            json.dumps(selection_report["plan"], ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        (output / "selection_validity_audit.json").write_text(
            json.dumps(selection_report, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        (output / "selection_validity_audit.md").write_text(
            render_selection_markdown(selection_report), encoding="utf-8"
        )
        report["automatic_selection_validity_audit"] = {
            "schema": selection_report["schema"],
            "run_count": selection_report["run_count"],
            "bottleneck_dominated_run_count": selection_report[
                "bottleneck_dominated_run_count"
            ],
            "post_bottleneck_source_ready_run_count": selection_report[
                "post_bottleneck_source_ready_run_count"
            ],
            "future_fixed_burn_in_rule_supported": selection_report[
                "future_fixed_burn_in_rule_supported"
            ],
            "future_fixed_burn_in_tick": selection_report[
                "future_fixed_burn_in_tick"
            ],
            "recommendation": selection_report["recommendation"],
        }
        markdown += "\n" + render_selection_markdown(selection_report)
    else:
        report["automatic_selection_validity_audit"] = {
            "available": False,
            "reason": "no evolution progress streams were available",
        }
    (output / "long_run_analysis.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (output / "long_run_analysis.md").write_text(markdown, encoding="utf-8")


if __name__ == "__main__":
    main()
