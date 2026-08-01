from __future__ import annotations

import argparse
import json
from pathlib import Path

from ..epochs import (
    build_regional_branch,
    freeze_epoch_base,
    load_epoch_registry,
    regional_branch_plan,
)


def _bounds(args: argparse.Namespace) -> tuple[float, float, float, float]:
    return (args.x_min, args.y_min, args.x_max, args.y_max)


def _write(payload: dict, output: str | None) -> None:
    text = json.dumps(payload, ensure_ascii=False, indent=2)
    if output:
        path = Path(output)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    print(text)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Inspect epoch contracts and build trusted epoch/regional checkpoints."
    )
    sub = parser.add_subparsers(dest="command", required=True)

    show = sub.add_parser("show", help="Validate and display an epoch registry.")
    show.add_argument("--registry", required=True)
    show.add_argument("--output")

    freeze = sub.add_parser("freeze-base", help="Freeze a qualified epoch checkpoint.")
    freeze.add_argument("--registry", required=True)
    freeze.add_argument("--epoch-id", required=True)
    freeze.add_argument("--checkpoint", required=True)
    freeze.add_argument("--qualification", required=True)
    freeze.add_argument("--output-dir", required=True)
    freeze.add_argument("--label")

    plan = sub.add_parser("region-plan", help="Plan a regional active-set branch.")
    plan.add_argument("--epoch-base", required=True)
    plan.add_argument("--x-min", type=float, required=True)
    plan.add_argument("--y-min", type=float, required=True)
    plan.add_argument("--x-max", type=float, required=True)
    plan.add_argument("--y-max", type=float, required=True)
    plan.add_argument("--output")

    branch = sub.add_parser("region-branch", help="Build a regional active-set checkpoint.")
    branch.add_argument("--epoch-base", required=True)
    branch.add_argument("--x-min", type=float, required=True)
    branch.add_argument("--y-min", type=float, required=True)
    branch.add_argument("--x-max", type=float, required=True)
    branch.add_argument("--y-max", type=float, required=True)
    branch.add_argument("--output-checkpoint", required=True)
    branch.add_argument("--work-dir", required=True)
    branch.add_argument("--minimum-entities", type=int, default=8)
    branch.add_argument("--output")
    return parser


def main(argv: list[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    if args.command == "show":
        registry = load_epoch_registry(args.registry)
        _write(registry, args.output)
        return
    if args.command == "freeze-base":
        result = freeze_epoch_base(
            registry_path=args.registry,
            epoch_id=args.epoch_id,
            checkpoint_path=args.checkpoint,
            qualification_path=args.qualification,
            output_dir=args.output_dir,
            label=args.label,
        )
        _write(result, None)
        return
    if args.command == "region-plan":
        result = regional_branch_plan(
            epoch_base=args.epoch_base,
            bounds=_bounds(args),
        )
        _write(result, args.output)
        return
    result = build_regional_branch(
        epoch_base=args.epoch_base,
        bounds=_bounds(args),
        output_checkpoint=args.output_checkpoint,
        work_dir=args.work_dir,
        minimum_entities=args.minimum_entities,
    )
    _write(result, args.output)


if __name__ == "__main__":
    main()
