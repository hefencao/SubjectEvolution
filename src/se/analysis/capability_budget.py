"""Derive and verify capability-attachment budgets from qualified turnover sources.

The budget is deliberately conservative and descriptive.  It converts a passed
source-health panel into explicit recurring, developmental, event-cost, and
maturation limits for the *next source pilot*.  It does not authorize paired or
evolutionary interpretation by itself.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
import hashlib
import json
from pathlib import Path
from typing import Any

from ..config_identity import strip_inactive_extensions

SCHEMA = "capability-affordability-budget-v1"
EXPOSURE_SCHEMA = "checkpoint-trapezoidal-entity-exposure-v1"


def _load_json(path: str | Path) -> dict[str, Any]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"expected a JSON object: {path}")
    return payload


def _canonical_sha256(payload: Any) -> str:
    encoded = json.dumps(
        payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _physical_config(payload: dict[str, Any]) -> dict[str, Any]:
    result = strip_inactive_extensions(payload)
    result.pop("run", None)
    return result


def _protocol_config(payload: dict[str, Any]) -> dict[str, Any]:
    result = strip_inactive_extensions(payload)
    run = result.get("run")
    if isinstance(run, dict):
        run.pop("seed", None)
    return result


def _seed_dir(source_root: Path, seed: int) -> Path:
    return source_root / f"seed_{seed}"


def _event_exposure(
    events: list[dict[str, Any]], *, initial_entities: int, final_tick: int
) -> tuple[float, list[dict[str, int]]]:
    points: list[tuple[int, int]] = [(0, int(initial_entities))]
    for event in sorted(events, key=lambda item: int(item.get("tick", -1))):
        tick = int(event.get("tick", -1))
        metrics = event.get("metrics", {})
        if tick <= points[-1][0] or tick > final_tick:
            raise ValueError(f"invalid or non-increasing health event tick: {tick}")
        points.append((tick, int(metrics.get("alive", -1))))
    if points[-1][0] != final_tick:
        raise ValueError(
            f"health events stop at tick {points[-1][0]}, expected {final_tick}"
        )
    if any(alive < 0 for _, alive in points):
        raise ValueError("health event contains a negative or missing alive count")
    exposure = 0.0
    for (tick0, alive0), (tick1, alive1) in zip(points, points[1:]):
        exposure += float(tick1 - tick0) * (float(alive0) + float(alive1)) / 2.0
    if exposure <= 0.0:
        raise ValueError("estimated entity exposure must be positive")
    return exposure, [{"tick": tick, "alive": alive} for tick, alive in points]


def _gate_seeds(gate: dict[str, Any]) -> list[dict[str, Any]]:
    seeds = gate.get("seeds")
    if not isinstance(seeds, list) or not seeds:
        raise ValueError("source-health report contains no seed assessments")
    return seeds


def derive_budget(
    *,
    source_root: str | Path,
    health_report: str | Path,
    output: str | Path,
    markdown_output: str | Path | None = None,
    recurring_headroom_fraction: float = 0.10,
    immature_recurring_fraction: float = 0.25,
    development_reserve_fraction: float = 0.25,
    development_endowment_fraction: float = 0.05,
    event_endowment_deviation_fraction: float = 1.0 / 6.0,
) -> dict[str, Any]:
    for name, value in {
        "recurring_headroom_fraction": recurring_headroom_fraction,
        "immature_recurring_fraction": immature_recurring_fraction,
        "development_reserve_fraction": development_reserve_fraction,
        "development_endowment_fraction": development_endowment_fraction,
        "event_endowment_deviation_fraction": event_endowment_deviation_fraction,
    }.items():
        if not 0.0 < float(value) <= 1.0:
            raise ValueError(f"{name} must be in (0, 1]")

    root = Path(source_root)
    gate_path = Path(health_report)
    gate = _load_json(gate_path)
    if gate.get("schema") != "source-health-gate-report-v2":
        raise ValueError("capability budgeting requires source-health-gate-report-v2")
    if not bool(gate.get("ready")) or not bool(gate.get("paired_plan_authorized")):
        raise ValueError("source-health panel is not qualified for next-stage planning")
    required = int(gate.get("contract", {}).get("required_ready_seed_count", 0))
    if int(gate.get("ready_seed_count", 0)) < required or required <= 0:
        raise ValueError("source-health report does not contain all required ready seeds")
    if int(gate.get("hard_stopped_seed_count", 0)) != 0:
        raise ValueError("hard-stopped sources cannot define a capability budget")

    contract_sha = str(gate.get("contract", {}).get("sha256", ""))
    if not contract_sha:
        raise ValueError("source-health report is missing the canonical contract hash")

    seed_reports: list[dict[str, Any]] = []
    physical_hashes: set[str] = set()
    protocol_hashes: set[str] = set()
    base_maintenance_values: set[float] = set()
    offspring_endowments: set[float] = set()
    parent_reserves: set[float] = set()
    final_ticks: set[int] = set()

    for assessment in _gate_seeds(gate):
        seed = int(assessment.get("seed", -1))
        if seed < 0 or not bool(assessment.get("ready")):
            raise ValueError(f"seed is missing or not ready: {seed}")
        termination = assessment.get("termination", {})
        final_tick = int(assessment.get("tick", -1))
        if bool(termination.get("terminated_early")):
            raise ValueError(f"seed {seed} terminated early")
        if int(termination.get("completed_tick", -1)) != final_tick:
            raise ValueError(f"seed {seed} completion tick does not match final assessment")
        if str(assessment.get("runtime_contract_sha256", "")) != contract_sha:
            raise ValueError(f"seed {seed} used a different source-health contract")

        run_dir = _seed_dir(root, seed)
        summary = _load_json(run_dir / "summary.json")
        config = _load_json(run_dir / "resolved_config.json")
        event_payload = _load_json(run_dir / "source_health_runtime_events.json")
        if str(event_payload.get("contract_sha256", "")) != contract_sha:
            raise ValueError(f"seed {seed} runtime event contract drift")
        events = event_payload.get("events")
        if not isinstance(events, list):
            raise ValueError(f"seed {seed} runtime events are missing")

        initial_entities = int(config.get("world", {}).get("initial_entities", 0))
        exposure, points = _event_exposure(
            events, initial_entities=initial_entities, final_tick=final_tick
        )
        body_energy_total = float(summary.get("resource_body_realized_0_total", -1.0))
        if body_energy_total < 0.0:
            raise ValueError(f"seed {seed} lacks cumulative body-energy inflow")
        maintenance = float(config.get("entities", {}).get("maintenance_cost", -1.0))
        endowment_levels = config.get("entities", {}).get("reproduction_investment_levels", [])
        if not isinstance(endowment_levels, list) or len(endowment_levels) != 1:
            raise ValueError(f"seed {seed} is not a fixed conservative substrate")
        endowment = float(endowment_levels[0])
        reserve = float(config.get("entities", {}).get("reproduction_parent_reserve", -1.0))
        mean_energy = float(summary.get("mean_energy", -1.0))
        if min(maintenance, endowment, reserve, mean_energy) < 0.0:
            raise ValueError(f"seed {seed} contains an invalid energy field")

        gross_inflow = body_energy_total / exposure
        gross_headroom = gross_inflow - maintenance
        if gross_headroom <= 0.0:
            raise ValueError(
                f"seed {seed} has no positive gross body-energy headroom above base maintenance"
            )
        reserve_margin = mean_energy - reserve
        if reserve_margin <= 0.0:
            raise ValueError(f"seed {seed} final mean energy is not above parent reserve")

        physical_hash = _canonical_sha256(_physical_config(config))
        protocol_hash = _canonical_sha256(_protocol_config(config))
        physical_hashes.add(physical_hash)
        protocol_hashes.add(protocol_hash)
        base_maintenance_values.add(maintenance)
        offspring_endowments.add(endowment)
        parent_reserves.add(reserve)
        final_ticks.add(final_tick)
        metrics = assessment.get("metrics", {})
        seed_reports.append(
            {
                "seed": seed,
                "completed_tick": final_tick,
                "contract_sha256": contract_sha,
                "physical_substrate_fingerprint_sha256": physical_hash,
                "source_protocol_fingerprint_sha256": protocol_hash,
                "entity_exposure_schema": EXPOSURE_SCHEMA,
                "entity_exposure_estimate": exposure,
                "exposure_points": points,
                "reported_body_energy_inflow_total": body_energy_total,
                "gross_body_energy_inflow_per_entity_tick": gross_inflow,
                "base_maintenance_energy_per_entity_tick": maintenance,
                "gross_headroom_above_base_maintenance_per_entity_tick": gross_headroom,
                "final_mean_body_energy": mean_energy,
                "parent_reserve_energy": reserve,
                "final_mean_energy_margin_above_parent_reserve": reserve_margin,
                "alive": int(metrics.get("alive", summary.get("alive", 0))),
                "cumulative_births_per_initial": float(
                    metrics.get(
                        "cumulative_births_per_initial",
                        summary.get("cumulative_births_per_initial", 0.0),
                    )
                ),
                "living_descendants_per_initial": float(
                    metrics.get(
                        "living_descendants_per_initial",
                        summary.get("living_descendants_per_initial", 0.0),
                    )
                ),
                "mean_generation": float(
                    metrics.get("mean_generation", summary.get("mean_generation", 0.0))
                ),
                "max_generation": int(
                    metrics.get("max_generation", summary.get("max_generation", 0))
                ),
                "founder_alive_fraction": float(
                    metrics.get(
                        "founder_alive_fraction",
                        summary.get("founder_alive_fraction", 1.0),
                    )
                ),
                "final_checkpoint_alive_decline_fraction": float(
                    assessment.get("alive_decline_fraction_from_previous_checkpoint", 0.0)
                ),
            }
        )

    if len(seed_reports) != required:
        raise ValueError(
            f"expected exactly {required} qualified formal seeds, found {len(seed_reports)}"
        )
    if len(physical_hashes) != 1 or len(protocol_hashes) != 1:
        raise ValueError("formal seeds do not share one unchanged source configuration")
    if any(len(values) != 1 for values in (base_maintenance_values, offspring_endowments, parent_reserves, final_ticks)):
        raise ValueError("formal seeds disagree on the fixed turnover substrate")

    min_headroom = min(
        item["gross_headroom_above_base_maintenance_per_entity_tick"]
        for item in seed_reports
    )
    min_reserve_margin = min(
        item["final_mean_energy_margin_above_parent_reserve"] for item in seed_reports
    )
    endowment = next(iter(offspring_endowments))
    recurring_ceiling = min_headroom * float(recurring_headroom_fraction)
    immature_ceiling = recurring_ceiling * float(immature_recurring_fraction)
    development_ceiling = min(
        min_reserve_margin * float(development_reserve_fraction),
        endowment * float(development_endowment_fraction),
    )
    event_deviation = endowment * float(event_endowment_deviation_fraction)

    report: dict[str, Any] = {
        "schema": SCHEMA,
        "source_health_report": str(gate_path),
        "source_health_report_sha256": hashlib.sha256(gate_path.read_bytes()).hexdigest(),
        "source_root": str(root),
        "source_health_contract_sha256": contract_sha,
        "qualified_seed_count": len(seed_reports),
        "required_seed_count": required,
        "source_qualification_ready": True,
        "physical_substrate_fingerprint_sha256": next(iter(physical_hashes)),
        "source_protocol_fingerprint_sha256": next(iter(protocol_hashes)),
        "formal_seeds": seed_reports,
        "derivation_policy": {
            "schema": "capability-affordability-derivation-policy-v1",
            "entity_exposure_schema": EXPOSURE_SCHEMA,
            "recurring_headroom_fraction": float(recurring_headroom_fraction),
            "immature_recurring_fraction": float(immature_recurring_fraction),
            "development_reserve_fraction": float(development_reserve_fraction),
            "development_endowment_fraction": float(development_endowment_fraction),
            "event_endowment_deviation_fraction": float(event_endowment_deviation_fraction),
            "gross_headroom_is_not_net_spendable_energy": True,
        },
        "observed_reference": {
            "base_maintenance_energy_per_entity_tick": next(iter(base_maintenance_values)),
            "fixed_offspring_endowment_energy": endowment,
            "fixed_parent_reserve_energy": next(iter(parent_reserves)),
            "final_tick": next(iter(final_ticks)),
            "minimum_gross_body_energy_inflow_per_entity_tick": min(
                item["gross_body_energy_inflow_per_entity_tick"] for item in seed_reports
            ),
            "minimum_gross_headroom_above_base_maintenance_per_entity_tick": min_headroom,
            "minimum_final_mean_energy_margin_above_parent_reserve": min_reserve_margin,
        },
        "attachment_budget": {
            "maximum_new_recurring_cost_per_entity_tick": recurring_ceiling,
            "maximum_immature_recurring_cost_per_entity_tick": immature_ceiling,
            "maximum_extra_development_cost_per_newborn": development_ceiling,
            "maximum_event_debit_deviation_from_fixed_endowment": event_deviation,
            "maximum_initial_population_mean_event_debit_shift": 0.0,
            "structural_and_use_recurring_costs_share_one_ceiling": True,
            "all_costs_must_be_charged_in_world_semantics": True,
        },
        "maturation_contract": {
            "single_gene_independent_capability_minimum_generations_before_effect_window": 1,
            "combination_capability_minimum_generations_before_effect_window": 2,
            "combination_capability_requires_low_cost_immature_state": True,
            "combination_immature_state_recurring_cost_ceiling": immature_ceiling,
            "initial_random_population_must_not_pay_mature_combination_cost": True,
            "effect_window_must_begin_after_declared_maturation": True,
        },
        "authorization": {
            "capability_design_authorized": True,
            "capability_source_pilot_authorized": True,
            "paired_branch_authorized": False,
            "evolutionary_panel_authorized": False,
            "selection_or_niche_claim_authorized": False,
            "next_gate": "attached-capability-source-health",
        },
        "interpretation_boundary": (
            "The qualified D1-N substrate supports bounded capability design and a new "
            "source-health pilot only. Gross headroom is a conservative reference before "
            "other existing costs, not a guaranteed spendable surplus."
        ),
    }
    report["budget_sha256"] = _canonical_sha256(report)

    destination = Path(output)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    markdown = render_markdown(report)
    md_path = Path(markdown_output) if markdown_output is not None else destination.with_suffix(".md")
    md_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.write_text(markdown, encoding="utf-8")
    return report


def verify_budget(path: str | Path) -> dict[str, Any]:
    payload = _load_json(path)
    if payload.get("schema") != SCHEMA:
        raise ValueError(f"unsupported capability budget schema: {payload.get('schema')!r}")
    recorded = str(payload.get("budget_sha256", ""))
    check = deepcopy(payload)
    check.pop("budget_sha256", None)
    expected = _canonical_sha256(check)
    if recorded != expected:
        raise ValueError("capability budget canonical SHA-256 mismatch")
    if not bool(payload.get("source_qualification_ready")):
        raise ValueError("capability budget is not backed by a qualified source")
    authorization = payload.get("authorization", {})
    if not bool(authorization.get("capability_source_pilot_authorized")):
        raise ValueError("capability source pilot is not authorized")
    if bool(authorization.get("paired_branch_authorized")) or bool(
        authorization.get("evolutionary_panel_authorized")
    ):
        raise ValueError("budget alone cannot authorize paired or evolutionary stages")
    budget = payload.get("attachment_budget", {})
    required_positive = (
        "maximum_new_recurring_cost_per_entity_tick",
        "maximum_immature_recurring_cost_per_entity_tick",
        "maximum_extra_development_cost_per_newborn",
        "maximum_event_debit_deviation_from_fixed_endowment",
    )
    if any(float(budget.get(name, 0.0)) <= 0.0 for name in required_positive):
        raise ValueError("capability budget contains a non-positive required ceiling")
    return payload


def render_markdown(report: dict[str, Any]) -> str:
    ref = report["observed_reference"]
    budget = report["attachment_budget"]
    lines = [
        "# D1 capability affordability budget",
        "",
        f"Qualified formal seeds: **{report['qualified_seed_count']} / {report['required_seed_count']}**.",
        f"Source-health contract: `{report['source_health_contract_sha256']}`.",
        "",
        "## Conservative references",
        "",
        f"- Minimum gross body-energy inflow/entity-tick: `{ref['minimum_gross_body_energy_inflow_per_entity_tick']:.9f}`",
        f"- Minimum gross headroom above base maintenance/entity-tick: `{ref['minimum_gross_headroom_above_base_maintenance_per_entity_tick']:.9f}`",
        f"- Minimum final mean-energy margin above parent reserve: `{ref['minimum_final_mean_energy_margin_above_parent_reserve']:.9f}`",
        "",
        "## Attachment limits",
        "",
        f"- New mature recurring cost/entity-tick: `<= {budget['maximum_new_recurring_cost_per_entity_tick']:.9f}`",
        f"- Immature recurring cost/entity-tick: `<= {budget['maximum_immature_recurring_cost_per_entity_tick']:.9f}`",
        f"- Extra development cost/newborn: `<= {budget['maximum_extra_development_cost_per_newborn']:.9f}`",
        f"- Event debit deviation from fixed endowment: `<= {budget['maximum_event_debit_deviation_from_fixed_endowment']:.9f}`",
        "- Initial-population mean event-debit shift: `0.0`",
        "",
        "## Evidence boundary",
        "",
        report["interpretation_boundary"],
        "",
    ]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Derive or verify a capability-attachment budget.")
    sub = parser.add_subparsers(dest="command", required=True)
    derive = sub.add_parser("derive")
    derive.add_argument("--source-root", required=True)
    derive.add_argument("--health-report", required=True)
    derive.add_argument("--output", required=True)
    derive.add_argument("--markdown-output")
    derive.add_argument("--recurring-headroom-fraction", type=float, default=0.10)
    derive.add_argument("--immature-recurring-fraction", type=float, default=0.25)
    derive.add_argument("--development-reserve-fraction", type=float, default=0.25)
    derive.add_argument("--development-endowment-fraction", type=float, default=0.05)
    derive.add_argument("--event-endowment-deviation-fraction", type=float, default=1.0 / 6.0)
    verify = sub.add_parser("verify")
    verify.add_argument("--budget", required=True)
    args = parser.parse_args(argv)
    if args.command == "derive":
        report = derive_budget(
            source_root=args.source_root,
            health_report=args.health_report,
            output=args.output,
            markdown_output=args.markdown_output,
            recurring_headroom_fraction=args.recurring_headroom_fraction,
            immature_recurring_fraction=args.immature_recurring_fraction,
            development_reserve_fraction=args.development_reserve_fraction,
            development_endowment_fraction=args.development_endowment_fraction,
            event_endowment_deviation_fraction=args.event_endowment_deviation_fraction,
        )
        print(json.dumps({"output": args.output, "budget_sha256": report["budget_sha256"]}))
    else:
        report = verify_budget(args.budget)
        print(json.dumps({"budget": args.budget, "budget_sha256": report["budget_sha256"], "valid": True}))


if __name__ == "__main__":
    main()
