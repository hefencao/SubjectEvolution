"""Sequential multi-seed runner for reproducible long-horizon experiments."""

from __future__ import annotations

import argparse
from dataclasses import asdict, replace
import json
from pathlib import Path
import shutil

from .config import load_config
from .long_run_analysis import analyze, render_markdown
from .simulation import Simulation


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
    parser.add_argument("--backend", choices=("cpu", "gpu", "auto"), default="cpu")
    parser.add_argument("--until-tick", type=int)
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
    target_tick = base.run.ticks if args.until_tick is None else int(args.until_tick)
    if target_tick < 0:
        raise ValueError("until-tick must be non-negative")
    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=True)
    progress_paths: list[Path] = []
    index: list[dict[str, object]] = []
    for seed in seeds:
        run_cfg = replace(base, run=replace(base.run, seed=seed, ticks=target_tick))
        run_dir = output / f"seed_{seed}"
        completed_tick = _completed_tick(run_dir) if run_dir.exists() else None
        if completed_tick is not None and completed_tick >= target_tick:
            progress = run_dir / "evolution_progress.jsonl"
            progress_paths.append(progress)
            final_records = []
            with progress.open("r", encoding="utf-8") as handle:
                final_records = [json.loads(line) for line in handle if line.strip()]
            index.append(
                {
                    "seed": seed,
                    "output": str(run_dir),
                    "final_tick": int(final_records[-1]["tick"]),
                    "alive": int(final_records[-1].get("alive", 0)),
                    "evolution_progress": str(progress),
                    "status": "skipped-completed",
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
        progress_paths.append(progress)
        index.append(
            {
                "seed": seed,
                "output": str(run_dir),
                "final_tick": target_tick,
                "alive": int(final.get("alive", 0)),
                "evolution_progress": str(progress),
                "status": "completed",
            }
        )
        (output / "multi_seed_index.json").write_text(
            json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    report = analyze(progress_paths)
    (output / "long_run_analysis.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (output / "long_run_analysis.md").write_text(
        render_markdown(report), encoding="utf-8"
    )


if __name__ == "__main__":
    main()
