"""Pre-register cheap exploration panels and protect seed independence."""
from __future__ import annotations

import argparse
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
from typing import Any, Sequence

from ..cfg import load_config

SCHEMA = "tiered-exploration-plan-v1"
_STAGE_ORDER = {"smoke": 0, "screen": 1, "replication": 2, "confirmation": 3}
_STAGE_LIMITS: dict[str, dict[str, int | None]] = {
    "smoke": {"minimum_seeds": 2, "maximum_initial_entities": 512, "maximum_ticks": 180},
    "screen": {"minimum_seeds": 8, "maximum_initial_entities": 2048, "maximum_ticks": 600},
    "replication": {"minimum_seeds": 8, "maximum_initial_entities": 4096, "maximum_ticks": 900},
    "confirmation": {"minimum_seeds": 8, "maximum_initial_entities": None, "maximum_ticks": None},
}


def _canonical_config(path: Path) -> tuple[dict[str, Any], str]:
    cfg = load_config(path)
    payload = asdict(cfg)
    encoded = json.dumps(
        payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return payload, hashlib.sha256(encoded).hexdigest()


def parse_seeds(text: str) -> list[int]:
    seeds = [int(value.strip()) for value in text.split(",") if value.strip()]
    if not seeds:
        raise ValueError("at least one seed is required")
    if len(set(seeds)) != len(seeds):
        raise ValueError("seeds must be unique")
    return seeds


def _read_plan(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("schema") != SCHEMA:
        raise ValueError(f"unsupported exploration plan schema in {path}")
    return payload


def build_plan(
    *,
    stage: str,
    candidate_id: str,
    config_path: Path,
    seeds: Sequence[int],
    output: Path,
    backend: str,
    until_tick: int | None = None,
    prior_plan: dict[str, Any] | None = None,
    allow_large_long_confirmation: bool = False,
) -> dict[str, Any]:
    if stage not in _STAGE_ORDER:
        raise ValueError(f"unsupported stage: {stage}")
    if not candidate_id.strip():
        raise ValueError("candidate id cannot be empty")
    if len(set(int(seed) for seed in seeds)) != len(seeds):
        raise ValueError("seeds must be unique")
    config_payload, config_sha = _canonical_config(config_path)
    initial_entities = int(config_payload["world"]["initial_entities"])
    target_tick = int(until_tick or config_payload["run"]["ticks"])
    limits = _STAGE_LIMITS[stage]
    if len(seeds) < int(limits["minimum_seeds"]):
        raise ValueError(
            f"{stage} requires at least {limits['minimum_seeds']} independent seeds"
        )
    max_entities = limits["maximum_initial_entities"]
    if max_entities is not None and initial_entities > int(max_entities):
        raise ValueError(
            f"{stage} allows at most {max_entities} initial entities; got {initial_entities}"
        )
    max_ticks = limits["maximum_ticks"]
    if max_ticks is not None and target_tick > int(max_ticks):
        raise ValueError(f"{stage} allows at most {max_ticks} ticks; got {target_tick}")
    required_prior = {"replication": "screen", "confirmation": "replication"}.get(stage)
    prior_ref: dict[str, Any] | None = None
    if required_prior:
        if prior_plan is None:
            raise ValueError(f"{stage} requires a prior {required_prior} plan")
        if prior_plan.get("stage") != required_prior:
            raise ValueError(f"{stage} requires a prior {required_prior} plan")
        if prior_plan.get("candidate_id") != candidate_id:
            raise ValueError("candidate id must match the prior plan")
        prior_seeds = {
            int(seed)
            for seed in prior_plan.get(
                "all_stage_seeds", prior_plan.get("seeds", [])
            )
        }
        overlap = sorted(prior_seeds.intersection(int(seed) for seed in seeds))
        if overlap:
            raise ValueError(f"stage seeds must be disjoint; overlap: {overlap}")
        prior_ref = {
            "stage": prior_plan["stage"],
            "candidate_id": prior_plan["candidate_id"],
            "seeds": list(prior_plan["seeds"]),
            "all_stage_seeds": sorted(prior_seeds),
            "plan_sha256": hashlib.sha256(
                json.dumps(
                    prior_plan,
                    ensure_ascii=False,
                    sort_keys=True,
                    separators=(",", ":"),
                ).encode("utf-8")
            ).hexdigest(),
        }
    if stage == "confirmation" and not allow_large_long_confirmation:
        raise ValueError(
            "confirmation requires --allow-large-long-confirmation; large long runs are not an exploration default"
        )
    output = output.resolve()
    plan_path = output / "exploration_plan.json"
    command = [
        "se-multi",
        "--config",
        str(config_path),
        "--seeds",
        ",".join(str(seed) for seed in seeds),
        "--output",
        str(output),
        "--backend",
        backend,
        "--until-tick",
        str(target_tick),
        "--exploration-plan",
        str(plan_path),
    ]
    return {
        "schema": SCHEMA,
        "stage": stage,
        "candidate_id": candidate_id,
        "config": str(config_path),
        "resolved_config_sha256": config_sha,
        "initial_entities": initial_entities,
        "target_tick": target_tick,
        "seeds": [int(seed) for seed in seeds],
        "all_stage_seeds": sorted(
            set(int(seed) for seed in seeds)
            | (
                set(int(seed) for seed in prior_ref["all_stage_seeds"])
                if prior_ref is not None
                else set()
            )
        ),
        "independent_unit": "seed",
        "windows_entities_and_events_are_independent_replicates": False,
        "output": str(output),
        "requested_backend": backend,
        "stage_limits": limits,
        "prior_plan": prior_ref,
        "large_long_confirmation_explicitly_authorized": bool(
            stage == "confirmation" and allow_large_long_confirmation
        ),
        "failed_runs_replaced": False,
        "outcome_conditioned_seed_or_horizon_changes": False,
        "pilot_seeds_reused_for_later_stage": False,
        "source_run_only": True,
        "free_run_endpoint_is_candidate_effect": False,
        "paired_panel_required_for_promotion": stage in {"screen", "replication", "confirmation"},
        "selection_claim_allowed": False,
        "execution_command": command,
    }


def render_markdown(plan: dict[str, Any]) -> str:
    command = " \\\n  ".join(plan["execution_command"])
    return "\n".join(
        [
            "# Tiered exploration plan",
            "",
            f"Schema: `{plan['schema']}`",
            f"Stage: `{plan['stage']}`",
            f"Candidate: `{plan['candidate_id']}`",
            f"Initial entities: `{plan['initial_entities']}`",
            f"Target tick: `{plan['target_tick']}`",
            f"Independent seeds: `{len(plan['seeds'])}`",
            "",
            "```bash",
            command,
            "```",
            "",
            "This plan creates source trajectories and checkpoints only. Its free-running endpoint is not a candidate-effect measurement.",
            "",
            "Repeated windows, entities, and events are nested observations. The seed is the independent unit.",
            "",
        ]
    )


def validate_multi_seed_invocation(
    plan_path: Path,
    *,
    config_path: Path,
    seeds: Sequence[int],
    output: Path,
    backend: str,
    target_tick: int,
) -> dict[str, Any]:
    plan = _read_plan(plan_path)
    _, config_sha = _canonical_config(config_path)
    checks = {
        "resolved_config_sha256": config_sha == plan.get("resolved_config_sha256"),
        "seeds": [int(seed) for seed in seeds] == [int(seed) for seed in plan.get("seeds", [])],
        "output": output.resolve() == Path(str(plan.get("output"))).resolve(),
        "backend": backend == plan.get("requested_backend"),
        "target_tick": int(target_tick) == int(plan.get("target_tick", -1)),
    }
    failed = [name for name, passed in checks.items() if not passed]
    if failed:
        raise ValueError("multi-seed invocation differs from exploration plan: " + ", ".join(failed))
    return plan


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Create a bounded tiered exploration plan.")
    parser.add_argument("--stage", required=True, choices=tuple(_STAGE_ORDER))
    parser.add_argument("--candidate", required=True)
    parser.add_argument("--config", required=True)
    parser.add_argument("--seeds", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--backend", default="auto")
    parser.add_argument("--until-tick", type=int)
    parser.add_argument("--prior-plan")
    parser.add_argument("--allow-large-long-confirmation", action="store_true")
    args = parser.parse_args(argv)
    config_path = Path(args.config)
    output = Path(args.output)
    prior = _read_plan(Path(args.prior_plan)) if args.prior_plan else None
    plan = build_plan(
        stage=args.stage,
        candidate_id=args.candidate,
        config_path=config_path,
        seeds=parse_seeds(args.seeds),
        output=output,
        backend=args.backend,
        until_tick=args.until_tick,
        prior_plan=prior,
        allow_large_long_confirmation=args.allow_large_long_confirmation,
    )
    output.mkdir(parents=True, exist_ok=True)
    (output / "exploration_plan.json").write_text(
        json.dumps(plan, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    (output / "exploration_plan.md").write_text(
        render_markdown(plan), encoding="utf-8"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
