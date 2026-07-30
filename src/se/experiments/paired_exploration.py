"""Fixed-checkpoint matched panels for inexpensive tiered exploration.

A free-running endpoint is not an intervention effect.  This module converts a
predeclared multi-seed checkpoint set into paired baseline/intervention panels,
keeps seed as the independent unit, and computes promotion gates from seed-level
matched effects only.
"""
from __future__ import annotations

import argparse
import csv
from dataclasses import asdict
import hashlib
import itertools
import json
import math
from pathlib import Path
from statistics import fmean, median
from typing import Any, Sequence

import numpy as np

from se.analysis.candidate_ledger import (
    candidate_portfolio_metadata,
    candidate_signature,
    load_ledger,
    record_assessment,
    validate_candidate_for_plan,
)
from se.checkpointing import read_checkpoint_bundle
from se.experiments.counterfactual import run_paired
from se.experiments.interventions import ExperimentMode, intervention_names, resolve_intervention
from se.runtime.sim import Simulation

PLAN_SCHEMA = "tiered-paired-exploration-plan-v2"
LEGACY_PLAN_SCHEMA = "tiered-paired-exploration-plan-v1"
RESULT_SCHEMA = "tiered-paired-exploration-results-v2"
ASSESSMENT_SCHEMA = "tiered-paired-exploration-assessment-v2"
LEGACY_ASSESSMENT_SCHEMA = "tiered-paired-exploration-assessment-v1"
CANDIDATE_SCHEMA = "paired-exploration-candidate-v1"
_STAGE_ORDER = {"smoke": 0, "screen": 1, "replication": 2, "confirmation": 3}
_STAGE_MINIMUM_SEEDS = {"smoke": 2, "screen": 8, "replication": 8, "confirmation": 8}
_CUMULATIVE_ALIASES: dict[str, tuple[str, ...]] = {
    "harvested-resource-total": tuple(f"harvested_resource_{index}_total" for index in range(4)),
    "requested-harvest-total": tuple(
        f"requested_harvest_resource_{index}_total" for index in range(4)
    ),
    "resource-stored-total": tuple(f"resource_stored_{index}_total" for index in range(4)),
    "resource-converted-total": ("resource_converted_total",),
    "knowledge-working-memory-active-dimensions-total": (
        "knowledge_working_memory_active_dimensions_total",
    ),
    "knowledge-working-memory-committed-entities-total": (
        "knowledge_working_memory_committed_entities_total",
    ),
    "knowledge-capacity-rejections-total": (
        "knowledge_transfer_capacity_rejected_total",
        "knowledge_learning_capacity_rejected_total",
    ),
    "knowledge-policy-changed-actions-total": (
        "knowledge_policy_changed_actions_total",
    ),
    "knowledge-policy-influenced-actions-total": (
        "knowledge_policy_influenced_actions_total",
    ),
    "physiology-oxygen-uptake-total": (
        "physiology_oxygen_uptake_total",
    ),
}


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def _canonical_sha(payload: dict[str, Any]) -> str:
    return hashlib.sha256(
        json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode(
            "utf-8"
        )
    ).hexdigest()



def _config_semantic_sha(config: Any) -> str:
    payload = asdict(config)
    payload["run"]["seed"] = 0
    return _canonical_sha(payload)


def _read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"expected an object in {path}")
    return payload


def _normalize_manipulation_checks(checks: Sequence[dict[str, Any]] | None) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    for raw in checks or ():
        if not isinstance(raw, dict):
            raise ValueError("manipulation checks must be objects")
        metric = str(raw.get("metric", "")).strip()
        branch = str(raw.get("branch", "")).strip()
        operator = str(raw.get("operator", "")).strip()
        metric_mode = str(raw.get("metric_mode", "endpoint")).strip()
        if not metric:
            raise ValueError("manipulation check metric cannot be empty")
        if branch not in {"baseline", "intervention"}:
            raise ValueError("manipulation check branch must be baseline or intervention")
        if operator not in {"<", "<=", ">", ">=", "=="}:
            raise ValueError("unsupported manipulation check operator")
        if metric_mode not in {"endpoint", "cumulative"}:
            raise ValueError("manipulation check metric_mode must be endpoint or cumulative")
        value = float(raw.get("value"))
        if not math.isfinite(value):
            raise ValueError("manipulation check value must be finite")
        normalized.append(
            {
                "metric": metric,
                "metric_mode": metric_mode,
                "branch": branch,
                "operator": operator,
                "value": value,
            }
        )
    return normalized


def load_candidate_spec(path: str | Path) -> tuple[dict[str, Any], str]:
    candidate_path = Path(path)
    payload = _read_json(candidate_path)
    if payload.get("schema") != CANDIDATE_SCHEMA:
        raise ValueError(f"unsupported paired candidate schema: {payload.get('schema')!r}")
    required = (
        "candidate_id",
        "intervention",
        "primary_metric",
        "metric_mode",
        "direction",
        "minimum_relative_effect",
        "response_ticks",
    )
    missing = [key for key in required if payload.get(key) is None]
    if missing:
        raise ValueError(f"candidate spec is missing required fields: {missing}")
    spec = resolve_intervention(str(payload["intervention"]))
    spec.require_mode(ExperimentMode.SCIENTIFIC)
    normalized = dict(payload)
    normalized["candidate_id"] = str(payload["candidate_id"]).strip()
    normalized["intervention"] = spec.name
    normalized["primary_metric"] = str(payload["primary_metric"])
    normalized["metric_mode"] = str(payload["metric_mode"])
    normalized["direction"] = str(payload["direction"])
    normalized["minimum_relative_effect"] = float(payload["minimum_relative_effect"])
    normalized["response_ticks"] = int(payload["response_ticks"])
    normalized["manipulation_checks"] = _normalize_manipulation_checks(
        payload.get("manipulation_checks")
    )
    normalized.update(candidate_portfolio_metadata(payload))
    return normalized, _sha256_file(candidate_path)


def _candidate_signature_payload(
    *,
    intervention: str,
    primary_metric: str,
    metric_mode: str,
    direction: str,
    minimum_relative_effect: float,
    response_ticks: int,
    manipulation_checks: Sequence[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "intervention": intervention,
        "primary_metric": primary_metric,
        "metric_mode": metric_mode,
        "direction": direction,
        "minimum_relative_effect": float(minimum_relative_effect),
        "response_ticks": int(response_ticks),
        "manipulation_checks": list(manipulation_checks),
    }


def _source_index(source_root: Path) -> list[dict[str, Any]]:
    payload = json.loads((source_root / "multi_seed_index.json").read_text(encoding="utf-8"))
    if not isinstance(payload, list) or not payload:
        raise ValueError("source multi_seed_index.json must contain completed seed rows")
    rows = [row for row in payload if row.get("status") == "completed"]
    if len(rows) != len(payload):
        raise ValueError("paired exploration does not replace incomplete source seeds")
    return rows


def _checkpoint_path(source_root: Path, seed: int, tick: int) -> Path:
    return source_root / f"seed_{seed}" / f"checkpoint_{tick:08d}.sechk"


def _validate_prior(
    prior: dict[str, Any],
    *,
    stage: str,
    candidate_id: str,
    intervention: str,
    primary_metric: str,
    metric_mode: str,
    direction: str,
    minimum_relative_effect: float,
    response_ticks: int,
    candidate_signature_sha256: str,
    seeds: set[int],
) -> dict[str, Any]:
    required_stage = {"replication": "screen", "confirmation": "replication"}.get(stage)
    if required_stage is None:
        raise ValueError("a prior assessment is only valid for replication or confirmation")
    if prior.get("schema") not in {ASSESSMENT_SCHEMA, LEGACY_ASSESSMENT_SCHEMA}:
        raise ValueError("unsupported prior paired assessment schema")
    if prior.get("stage") != required_stage:
        raise ValueError(f"{stage} requires a prior {required_stage} assessment")
    expected_recommendation = {
        "replication": "promote-to-disjoint-replication",
        "confirmation": "promote-to-explicit-confirmation",
    }[stage]
    if prior.get("recommendation") != expected_recommendation:
        raise ValueError(
            f"prior assessment does not authorize {stage}: {prior.get('recommendation')!r}"
        )
    for key, expected in (
        ("candidate_id", candidate_id),
        ("intervention", intervention),
        ("primary_metric", primary_metric),
        ("metric_mode", metric_mode),
        ("direction", direction),
    ):
        if prior.get(key) != expected:
            raise ValueError(f"prior paired assessment changes {key}")
    if not math.isclose(
        float(prior.get("minimum_relative_effect", float("nan"))),
        float(minimum_relative_effect),
        rel_tol=0.0,
        abs_tol=1e-15,
    ):
        raise ValueError("prior paired assessment changes minimum_relative_effect")
    if prior.get("response_ticks") is not None and int(prior["response_ticks"]) != int(response_ticks):
        raise ValueError("prior paired assessment changes response_ticks")
    prior_signature = prior.get("candidate_signature_sha256")
    if prior_signature is not None and str(prior_signature) != candidate_signature_sha256:
        raise ValueError("prior paired assessment changes candidate scientific specification")
    prior_seeds = {int(value) for value in prior.get("all_stage_seeds", prior.get("seeds", []))}
    overlap = sorted(prior_seeds.intersection(seeds))
    if overlap:
        raise ValueError(f"paired stage seeds must be disjoint; overlap: {overlap}")
    return {
        "stage": prior["stage"],
        "recommendation": prior["recommendation"],
        "all_stage_seeds": sorted(prior_seeds),
        "assessment_sha256": _canonical_sha(prior),
        "candidate_signature_sha256": str(prior_signature or candidate_signature_sha256),
    }


def _lineage_support(entity_state: Any) -> tuple[float | None, float | None]:
    alive = getattr(entity_state, "alive", None)
    lineages = getattr(entity_state, "lineage_id", None)
    if alive is None or lineages is None:
        return None, None
    active = np.flatnonzero(np.asarray(alive, dtype=bool))
    if active.size == 0:
        return 0.0, 1.0
    _, counts = np.unique(np.asarray(lineages)[active], return_counts=True)
    fractions = counts.astype(np.float64) / float(active.size)
    effective = 1.0 / float(np.square(fractions).sum())
    return effective, float(fractions.max(initial=0.0))


def build_plan(
    *,
    stage: str,
    candidate_id: str,
    source_root: Path,
    checkpoint_tick: int,
    response_ticks: int,
    intervention: str,
    primary_metric: str,
    metric_mode: str,
    direction: str,
    minimum_relative_effect: float,
    output: Path,
    backend: str = "auto",
    prior_assessment: dict[str, Any] | None = None,
    allow_large_long_confirmation: bool = False,
    manipulation_checks: Sequence[dict[str, Any]] | None = None,
    candidate_spec_sha256: str | None = None,
    candidate_spec_schema: str | None = None,
    candidate_metadata: dict[str, Any] | None = None,
    decision_ledger: Path | None = None,
) -> dict[str, Any]:
    if stage not in _STAGE_ORDER:
        raise ValueError(f"unsupported stage: {stage}")
    if not candidate_id.strip():
        raise ValueError("candidate id cannot be empty")
    if checkpoint_tick < 0 or response_ticks <= 0:
        raise ValueError("checkpoint tick must be non-negative and response ticks positive")
    if metric_mode not in {"cumulative", "endpoint"}:
        raise ValueError("metric mode must be cumulative or endpoint")
    if direction not in {"increase", "decrease", "two-sided"}:
        raise ValueError("direction must be increase, decrease, or two-sided")
    if minimum_relative_effect < 0.0:
        raise ValueError("minimum relative effect cannot be negative")
    spec = resolve_intervention(intervention)
    spec.require_mode(ExperimentMode.SCIENTIFIC)
    intervention = spec.name
    normalized_checks = _normalize_manipulation_checks(manipulation_checks)
    signature_payload = _candidate_signature_payload(
        intervention=intervention,
        primary_metric=primary_metric,
        metric_mode=metric_mode,
        direction=direction,
        minimum_relative_effect=minimum_relative_effect,
        response_ticks=response_ticks,
        manipulation_checks=normalized_checks,
    )
    candidate_signature_sha256 = candidate_signature(signature_payload)
    output = output.resolve()
    ledger_path = (
        decision_ledger.resolve()
        if decision_ledger is not None
        else output.parent / "exploration_candidate_ledger.json"
    )
    ledger = load_ledger(ledger_path)
    portfolio = candidate_portfolio_metadata(candidate_metadata or {})
    validate_candidate_for_plan(
        ledger,
        candidate_id=candidate_id,
        signature=candidate_signature_sha256,
        stage=stage,
        mechanism_family=portfolio["mechanism_family"],
        mechanism_family_revision=portfolio["mechanism_family_revision"],
        family_role=portfolio["family_role"],
        family_revision_rationale=portfolio["family_revision_rationale"],
    )
    source_root = source_root.resolve()
    rows = _source_index(source_root)
    seeds = [int(row["seed"]) for row in rows]
    if len(seeds) < _STAGE_MINIMUM_SEEDS[stage]:
        raise ValueError(
            f"{stage} requires at least {_STAGE_MINIMUM_SEEDS[stage]} independent seeds"
        )
    if len(set(seeds)) != len(seeds):
        raise ValueError("source seeds must be unique")
    if stage == "confirmation" and not allow_large_long_confirmation:
        raise ValueError(
            "confirmation requires explicit large/long authorization even when the current panel is small"
        )
    source_plan_path = source_root / "exploration_plan.json"
    source_plan = _read_json(source_plan_path)
    if source_plan.get("stage") != stage:
        raise ValueError("source exploration stage does not match paired stage")
    panels: list[dict[str, Any]] = []
    config_hashes: set[str] = set()
    for seed in seeds:
        checkpoint = _checkpoint_path(source_root, seed, checkpoint_tick)
        metadata, state = read_checkpoint_bundle(checkpoint)
        if int(metadata["tick"]) != checkpoint_tick:
            raise ValueError(f"checkpoint tick mismatch for seed {seed}")
        embedded_seed = int(state["config"].run.seed)
        if embedded_seed != seed:
            raise ValueError(f"checkpoint seed mismatch: index={seed}, checkpoint={embedded_seed}")
        config_hashes.add(_config_semantic_sha(state["config"]))
        simulation_state = state.get("simulation", {})
        entity_state = simulation_state.get("entities")
        alive = getattr(entity_state, "alive", None)
        source_alive = int(sum(bool(value) for value in alive)) if alive is not None else None
        source_effective_lineages, source_largest_lineage_fraction = _lineage_support(entity_state)
        initial_entities = int(state["config"].world.initial_entities)
        panels.append(
            {
                "seed": seed,
                "checkpoint_tick": checkpoint_tick,
                "checkpoint_path": str(checkpoint),
                "checkpoint_sha256": _sha256_file(checkpoint),
                "checkpoint_config_sha256": str(metadata["config_sha256"]),
                "source_alive": source_alive,
                "source_initial_entities": initial_entities,
                "source_effective_lineages": source_effective_lineages,
                "source_largest_lineage_fraction": source_largest_lineage_fraction,
                "until_tick": checkpoint_tick + response_ticks,
            }
        )
    if len(config_hashes) != 1:
        raise ValueError("source checkpoints do not share one configuration")
    prior_ref = None
    all_stage_seeds = set(seeds)
    if stage in {"replication", "confirmation"}:
        if prior_assessment is None:
            raise ValueError(f"{stage} requires a prior paired assessment")
        prior_ref = _validate_prior(
            prior_assessment,
            stage=stage,
            candidate_id=candidate_id,
            intervention=intervention,
            primary_metric=primary_metric,
            metric_mode=metric_mode,
            direction=direction,
            minimum_relative_effect=minimum_relative_effect,
            response_ticks=response_ticks,
            candidate_signature_sha256=candidate_signature_sha256,
            seeds=set(seeds),
        )
        all_stage_seeds.update(int(value) for value in prior_ref["all_stage_seeds"])
    plan_path = output / "paired_exploration_plan.json"
    return {
        "schema": PLAN_SCHEMA,
        "stage": stage,
        "candidate_id": candidate_id,
        "candidate_signature_sha256": candidate_signature_sha256,
        "candidate_spec_schema": candidate_spec_schema,
        "candidate_spec_sha256": candidate_spec_sha256,
        **portfolio,
        "source_root": str(source_root),
        "source_plan_schema": source_plan.get("schema"),
        "source_plan_sha256": _sha256_file(source_plan_path),
        "source_checkpoint_tick": checkpoint_tick,
        "response_ticks": response_ticks,
        "seeds": seeds,
        "all_stage_seeds": sorted(all_stage_seeds),
        "panels": panels,
        "branches": ["baseline", "intervention"],
        "intervention": intervention,
        "intervention_kind": spec.kind.value,
        "primary_metric": primary_metric,
        "metric_mode": metric_mode,
        "direction": direction,
        "minimum_relative_effect": float(minimum_relative_effect),
        "manipulation_checks": normalized_checks,
        "minimum_eligible_seed_fraction": 0.75,
        "minimum_direction_consistency": 0.75,
        "independent_unit": "seed",
        "windows_entities_and_events_are_independent_replicates": False,
        "fixed_checkpoint_selected_before_branch_outcomes": True,
        "outcome_conditioned_checkpoint_selection": False,
        "failed_or_ineligible_seeds_replaced": False,
        "requested_backend": backend,
        "output": str(output),
        "decision_ledger": str(ledger_path),
        "prior_assessment": prior_ref,
        "selection_claim_allowed": False,
        "acute_mechanism_claim_allowed": stage == "confirmation",
        "large_long_confirmation_explicitly_authorized": bool(
            stage == "confirmation" and allow_large_long_confirmation
        ),
        "execution_command": [
            "se-exploration-paired",
            "--plan",
            str(plan_path),
        ],
    }


def _load_plan(path: Path) -> dict[str, Any]:
    payload = _read_json(path)
    if payload.get("schema") not in {PLAN_SCHEMA, LEGACY_PLAN_SCHEMA}:
        raise ValueError(f"unsupported paired exploration plan schema: {payload.get('schema')!r}")
    if payload.get("schema") == LEGACY_PLAN_SCHEMA:
        payload = dict(payload)
        payload["schema"] = PLAN_SCHEMA
        payload.setdefault("manipulation_checks", [])
        payload.setdefault("candidate_signature_sha256", candidate_signature(payload))
        payload.setdefault(
            "decision_ledger",
            str(Path(str(payload["output"])).resolve().parent / "exploration_candidate_ledger.json"),
        )
    return payload


def _metric_value(row: dict[str, Any], name: str) -> float:
    if name in _CUMULATIVE_ALIASES:
        values: list[float] = []
        for key in _CUMULATIVE_ALIASES[name]:
            value = row.get(key)
            if isinstance(value, list):
                values.extend(float(item) for item in value)
            elif value is not None:
                values.append(float(value))
        if not values:
            raise KeyError(f"metric alias {name!r} is unavailable")
        return float(sum(values))
    value = row.get(name)
    if not isinstance(value, (int, float)):
        raise KeyError(f"numeric metric {name!r} is unavailable")
    return float(value)


def _compare(value: float, operator: str, expected: float) -> bool:
    if operator == "<":
        return value < expected
    if operator == "<=":
        return value <= expected
    if operator == ">":
        return value > expected
    if operator == ">=":
        return value >= expected
    if operator == "==":
        return math.isclose(value, expected, rel_tol=0.0, abs_tol=1e-12)
    raise ValueError(f"unsupported comparison operator: {operator}")


def _evaluate_manipulation_checks(
    checks: Sequence[dict[str, Any]],
    *,
    pre_intervention: dict[str, Any],
    baseline: dict[str, Any],
    intervention: dict[str, Any],
) -> tuple[list[dict[str, Any]], bool]:
    rows = {"baseline": baseline, "intervention": intervention}
    results: list[dict[str, Any]] = []
    for check in checks:
        branch = str(check["branch"])
        metric = str(check["metric"])
        value = _metric_value(rows[branch], metric)
        if check.get("metric_mode", "endpoint") == "cumulative":
            value -= _metric_value(pre_intervention, metric)
        expected = float(check["value"])
        passed = _compare(value, str(check["operator"]), expected)
        results.append({**check, "observed": value, "passed": passed})
    return results, all(bool(item["passed"]) for item in results)


def _branch_support(
    metrics_path: Path, *, minimum_alive: int, minimum_entity_ticks: int
) -> dict[str, Any]:
    if not metrics_path.is_file():
        return {
            "metrics_available": False,
            "minimum_alive": None,
            "entity_ticks": 0,
            "minimum_entity_ticks": int(minimum_entity_ticks),
            "supported": False,
        }
    alive_values: list[int] = []
    entity_ticks = 0
    with metrics_path.open("r", encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            if not row.get("alive"):
                continue
            alive = int(float(row["alive"]))
            window_ticks = int(float(row.get("window_ticks") or 0))
            alive_values.append(alive)
            entity_ticks += alive * max(window_ticks, 0)
    minimum_observed = min(alive_values) if alive_values else None
    return {
        "metrics_available": bool(alive_values),
        "minimum_alive": minimum_observed,
        "entity_ticks": int(entity_ticks),
        "minimum_entity_ticks": int(minimum_entity_ticks),
        "supported": bool(
            minimum_observed is not None
            and minimum_observed >= minimum_alive
            and entity_ticks >= minimum_entity_ticks
        ),
    }


def _exact_sign_flip_p(effects: Sequence[float]) -> float | None:
    values = [float(value) for value in effects if float(value) != 0.0]
    n = len(values)
    if n == 0 or n > 20:
        return None
    observed = abs(fmean(values))
    exceed = 0
    total = 1 << n
    for signs in itertools.product((-1.0, 1.0), repeat=n):
        candidate = abs(fmean(sign * value for sign, value in zip(signs, values)))
        if candidate + 1e-15 >= observed:
            exceed += 1
    return float(exceed) / float(total)


def _direction_match(effect: float, direction: str) -> bool:
    if direction == "increase":
        return effect > 0.0
    if direction == "decrease":
        return effect < 0.0
    return effect != 0.0


def assess_results(plan: dict[str, Any], panels: list[dict[str, Any]]) -> dict[str, Any]:
    manipulation_required = bool(plan.get("manipulation_checks"))
    manipulation_supported = [
        panel for panel in panels if bool(panel.get("manipulation_supported", not manipulation_required))
    ]
    eligible = [panel for panel in panels if panel["eligible"]]
    effects = [float(panel["relative_effect"]) for panel in eligible]
    positive = sum(value > 0.0 for value in effects)
    negative = sum(value < 0.0 for value in effects)
    if plan["direction"] == "two-sided":
        matching = max(positive, negative)
        inferred_direction = (
            "increase" if positive > negative else "decrease" if negative > positive else "mixed"
        )
    else:
        matching = sum(_direction_match(value, plan["direction"]) for value in effects)
        inferred_direction = plan["direction"]
    eligible_fraction = float(len(eligible)) / float(len(panels)) if panels else 0.0
    manipulation_fraction = (
        float(len(manipulation_supported)) / float(len(panels)) if panels else 0.0
    )
    direction_consistency = float(matching) / float(len(eligible)) if eligible else 0.0
    median_effect = median(effects) if effects else None
    practical = bool(
        median_effect is not None
        and abs(float(median_effect)) >= float(plan["minimum_relative_effect"])
    )
    gate_components = {
        "minimum_eligible_seed_count": len(eligible) >= _STAGE_MINIMUM_SEEDS[plan["stage"]],
        "eligible_seed_fraction": eligible_fraction
        >= float(plan["minimum_eligible_seed_fraction"]),
        "manipulation_confirmed": (
            not manipulation_required
            or manipulation_fraction >= float(plan["minimum_eligible_seed_fraction"])
        ),
        "direction_consistency": direction_consistency
        >= float(plan["minimum_direction_consistency"]),
        "practical_effect": practical,
    }
    gate = all(gate_components.values())
    reason_codes: list[str] = []
    if not gate_components["minimum_eligible_seed_count"]:
        reason_codes.append("insufficient-eligible-seed-panels")
    if not gate_components["eligible_seed_fraction"]:
        reason_codes.append("eligible-seed-fraction-below-threshold")
    if not gate_components["manipulation_confirmed"]:
        reason_codes.append("intervention-manipulation-not-confirmed")
    if not gate_components["direction_consistency"]:
        reason_codes.append("direction-not-replicated-across-seeds")
    if not gate_components["practical_effect"]:
        reason_codes.append("effect-below-preregistered-practical-threshold")

    recommendation = "stop-no-replicated-paired-effect"
    decision_outcome = "stop"
    terminal = True
    if gate and plan["stage"] == "smoke":
        recommendation = "mechanism-smoke-passed-create-independent-screen"
        decision_outcome = "promote"
        terminal = False
    elif gate and plan["stage"] == "screen":
        recommendation = "promote-to-disjoint-replication"
        decision_outcome = "promote"
        terminal = False
    elif gate and plan["stage"] == "replication":
        recommendation = "promote-to-explicit-confirmation"
        decision_outcome = "promote"
        terminal = False
    elif gate and plan["stage"] == "confirmation":
        recommendation = "confirmation-gate-passed-interpret-acute-mechanism-only"
        decision_outcome = "confirmed-acute"
        terminal = True
    elif not gate_components["manipulation_confirmed"]:
        recommendation = "stop-intervention-manipulation-not-confirmed"
    elif not gate_components["minimum_eligible_seed_count"]:
        recommendation = "stop-insufficient-eligible-seed-panels"
    elif not gate_components["direction_consistency"]:
        recommendation = "stop-direction-not-replicated-across-seeds"
    elif not practical:
        recommendation = "stop-effect-below-preregistered-practical-threshold"

    signature = str(
        plan.get("candidate_signature_sha256")
        or candidate_signature(_candidate_signature_payload(
            intervention=str(plan["intervention"]),
            primary_metric=str(plan["primary_metric"]),
            metric_mode=str(plan["metric_mode"]),
            direction=str(plan["direction"]),
            minimum_relative_effect=float(plan["minimum_relative_effect"]),
            response_ticks=int(plan.get("response_ticks", 0)),
            manipulation_checks=plan.get("manipulation_checks", []),
        ))
    )
    return {
        "schema": ASSESSMENT_SCHEMA,
        "stage": plan["stage"],
        "candidate_id": plan["candidate_id"],
        "candidate_signature_sha256": signature,
        "candidate_spec_schema": plan.get("candidate_spec_schema"),
        "candidate_spec_sha256": plan.get("candidate_spec_sha256"),
        **candidate_portfolio_metadata(plan),
        "intervention": plan["intervention"],
        "primary_metric": plan["primary_metric"],
        "metric_mode": plan["metric_mode"],
        "direction": plan["direction"],
        "minimum_relative_effect": plan["minimum_relative_effect"],
        "response_ticks": int(plan.get("response_ticks", 0)),
        "manipulation_checks": list(plan.get("manipulation_checks", [])),
        "seeds": list(plan["seeds"]),
        "all_stage_seeds": list(plan["all_stage_seeds"]),
        "panel_count": len(panels),
        "eligible_seed_count": len(eligible),
        "eligible_seed_fraction": eligible_fraction,
        "manipulation_supported_seed_count": len(manipulation_supported),
        "manipulation_supported_seed_fraction": manipulation_fraction,
        "positive_seed_count": positive,
        "negative_seed_count": negative,
        "direction_consistency": direction_consistency,
        "inferred_direction": inferred_direction,
        "equal_seed_mean_relative_effect": fmean(effects) if effects else None,
        "equal_seed_median_relative_effect": median_effect,
        "minimum_effect": min(effects) if effects else None,
        "maximum_effect": max(effects) if effects else None,
        "exact_two_sided_sign_flip_p": _exact_sign_flip_p(effects),
        "practical_effect_threshold_met": practical,
        "promotion_gate_components": gate_components,
        "promotion_gate_passed": gate,
        "recommendation": recommendation,
        "decision": {
            "outcome": decision_outcome,
            "terminal": terminal,
            "reason_codes": reason_codes or [recommendation],
            "failed_candidate_reopened_automatically": False,
        },
        "independent_unit": "seed",
        "windows_entities_and_events_are_independent_replicates": False,
        "interpretation_boundary": (
            "This is a matched acute checkpoint panel. It can screen a mechanism effect but "
            "does not establish long-horizon evolutionary selection, stable niches, or a "
            "population source rule. A stopped candidate requires an explicit new scientific "
            "revision rather than a relabeling or threshold change."
        ),
    }


def execute_plan(plan: dict[str, Any]) -> dict[str, Any]:
    output = Path(str(plan["output"]))
    output.mkdir(parents=True, exist_ok=True)
    panels: list[dict[str, Any]] = []
    for item in plan["panels"]:
        seed = int(item["seed"])
        checkpoint = Path(str(item["checkpoint_path"]))
        if _sha256_file(checkpoint) != item["checkpoint_sha256"]:
            raise ValueError(f"checkpoint hash changed for seed {seed}")
        seed_dir = output / f"seed_{seed}"
        simulation = Simulation.from_checkpoint(
            checkpoint,
            seed_dir / "baseline",
            backend=str(plan["requested_backend"]),
            until_tick=int(item["until_tick"]),
        )
        result = run_paired(
            simulation,
            str(plan["intervention"]),
            seed_dir,
            intervention_tick=int(item["checkpoint_tick"]),
        )
        pre_value = _metric_value(result.pre_intervention, str(plan["primary_metric"]))
        baseline_value = _metric_value(result.baseline, str(plan["primary_metric"]))
        intervention_value = _metric_value(
            result.intervention, str(plan["primary_metric"])
        )
        if plan["metric_mode"] == "cumulative":
            baseline_response = baseline_value - pre_value
            intervention_response = intervention_value - pre_value
        else:
            baseline_response = baseline_value
            intervention_response = intervention_value
        effect = intervention_response - baseline_response
        relative_effect = effect / max(abs(baseline_response), 1e-12)
        manipulation_results, manipulation_supported = _evaluate_manipulation_checks(
            plan.get("manipulation_checks", []),
            pre_intervention=result.pre_intervention,
            baseline=result.baseline,
            intervention=result.intervention,
        )
        initial_entities = int(simulation.cfg.world.initial_entities)
        minimum_source_alive = max(64, int(math.ceil(initial_entities * 0.08)))
        minimum_source_lineages = max(32.0, float(initial_entities) * 0.04)
        minimum_branch_alive = max(32, int(math.ceil(int(item.get("source_alive") or 0) * 0.25)))
        minimum_branch_entity_ticks = max(
            minimum_branch_alive,
            int(math.ceil(minimum_branch_alive * int(plan["response_ticks"]) * 0.5)),
        )
        baseline_support = _branch_support(
            seed_dir / "baseline" / "metrics.csv",
            minimum_alive=minimum_branch_alive,
            minimum_entity_ticks=minimum_branch_entity_ticks,
        )
        intervention_support = _branch_support(
            seed_dir / "intervention" / "metrics.csv",
            minimum_alive=minimum_branch_alive,
            minimum_entity_ticks=minimum_branch_entity_ticks,
        )
        source_supported = bool(
            item.get("source_alive") is not None
            and int(item["source_alive"]) >= minimum_source_alive
            and item.get("source_effective_lineages") is not None
            and float(item["source_effective_lineages"]) >= minimum_source_lineages
            and item.get("source_largest_lineage_fraction") is not None
            and float(item["source_largest_lineage_fraction"]) <= 0.25
        )
        eligible = bool(
            source_supported
            and baseline_support["supported"]
            and intervention_support["supported"]
            and manipulation_supported
        )
        panels.append(
            {
                "seed": seed,
                "checkpoint_tick": int(item["checkpoint_tick"]),
                "until_tick": int(item["until_tick"]),
                "source_alive": item.get("source_alive"),
                "minimum_source_alive": minimum_source_alive,
                "source_effective_lineages": item.get("source_effective_lineages"),
                "minimum_source_effective_lineages": minimum_source_lineages,
                "source_largest_lineage_fraction": item.get("source_largest_lineage_fraction"),
                "minimum_branch_alive": minimum_branch_alive,
                "minimum_branch_entity_ticks": minimum_branch_entity_ticks,
                "source_supported": source_supported,
                "baseline_support": baseline_support,
                "intervention_support": intervention_support,
                "pre_intervention_metric": pre_value,
                "baseline_metric": baseline_value,
                "intervention_metric": intervention_value,
                "baseline_response": baseline_response,
                "intervention_response": intervention_response,
                "effect_intervention_minus_baseline": effect,
                "relative_effect": relative_effect,
                "manipulation_checks": manipulation_results,
                "manipulation_supported": manipulation_supported,
                "intervention_record": result.intervention_record,
                "scientific_warnings": list(result.scientific_warnings),
                "baseline_scientific_validity": result.baseline_scientific_validity,
                "intervention_scientific_validity": result.intervention_scientific_validity,
                "eligible": eligible,
                "counterfactual_summary": str(
                    Path(f"seed_{seed}") / "counterfactual_summary.json"
                ),
            }
        )
    assessment = assess_results(plan, panels)
    report = {
        "schema": RESULT_SCHEMA,
        "plan_schema": plan["schema"],
        "plan_sha256": _canonical_sha(plan),
        "stage": plan["stage"],
        "candidate_id": plan["candidate_id"],
        "candidate_signature_sha256": plan.get("candidate_signature_sha256"),
        "candidate_spec_schema": plan.get("candidate_spec_schema"),
        "candidate_spec_sha256": plan.get("candidate_spec_sha256"),
        **candidate_portfolio_metadata(plan),
        "intervention": plan["intervention"],
        "primary_metric": plan["primary_metric"],
        "metric_mode": plan["metric_mode"],
        "direction": plan["direction"],
        "response_ticks": plan.get("response_ticks"),
        "manipulation_checks": plan.get("manipulation_checks", []),
        "panels": panels,
        "assessment": assessment,
    }
    (output / "paired_exploration_results.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    (output / "paired_exploration_assessment.json").write_text(
        json.dumps(assessment, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    (output / "paired_exploration_results.md").write_text(
        render_results_markdown(report), encoding="utf-8"
    )
    ledger, decision_entry = record_assessment(
        Path(str(plan["decision_ledger"])), assessment
    )
    (output / "candidate_decision.json").write_text(
        json.dumps(decision_entry, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    report["candidate_decision"] = decision_entry
    report["candidate_ledger_schema"] = ledger["schema"]
    (output / "paired_exploration_results.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return report


def render_plan_markdown(plan: dict[str, Any]) -> str:
    command = " \\\n  ".join(plan["execution_command"])
    return "\n".join(
        [
            "# Fixed-checkpoint paired exploration plan",
            "",
            f"Schema: `{plan['schema']}`",
            f"Stage: `{plan['stage']}`",
            f"Candidate: `{plan['candidate_id']}`",
            f"Checkpoint tick: `{plan['source_checkpoint_tick']}`",
            f"Response ticks: `{plan['response_ticks']}`",
            f"Intervention: `{plan['intervention']}`",
            f"Primary metric: `{plan['primary_metric']}` ({plan['metric_mode']})",
            f"Direction: `{plan['direction']}`",
            f"Independent seeds: `{len(plan['seeds'])}`",
            "",
            "```bash",
            command,
            "```",
            "",
            "All branches start from the same per-seed full checkpoint. The seed is the independent unit.",
            "",
        ]
    )


def render_results_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Fixed-checkpoint paired exploration results",
        "",
        f"Schema: `{report['schema']}`",
        "",
        "| Seed | Source alive | Baseline response | Intervention response | Relative effect | Eligible |",
        "|---:|---:|---:|---:|---:|---:|",
    ]
    for panel in report["panels"]:
        lines.append(
            f"| {panel['seed']} | {panel['source_alive']} | {panel['baseline_response']} | "
            f"{panel['intervention_response']} | {panel['relative_effect']} | {panel['eligible']} |"
        )
    assessment = report["assessment"]
    lines.extend(
        [
            "",
            "## Assessment",
            "",
            f"- eligible seeds: `{assessment['eligible_seed_count']}`",
            f"- direction consistency: `{assessment['direction_consistency']}`",
            f"- median relative effect: `{assessment['equal_seed_median_relative_effect']}`",
            f"- exact sign-flip p: `{assessment['exact_two_sided_sign_flip_p']}`",
            f"- promotion gate: `{assessment['promotion_gate_passed']}`",
            f"- recommendation: `{assessment['recommendation']}`",
            "",
            assessment["interpretation_boundary"],
            "",
        ]
    )
    return "\n".join(lines)


def plan_main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Create a fixed-checkpoint matched exploration panel."
    )
    parser.add_argument("--stage", required=True, choices=tuple(_STAGE_ORDER))
    parser.add_argument("--candidate")
    parser.add_argument("--candidate-spec")
    parser.add_argument("--source-root", required=True)
    parser.add_argument("--checkpoint-tick", type=int, required=True)
    parser.add_argument("--response-ticks", type=int)
    parser.add_argument(
        "--intervention",
        choices=intervention_names(mode=ExperimentMode.SCIENTIFIC),
    )
    parser.add_argument("--primary-metric")
    parser.add_argument("--metric-mode", choices=("cumulative", "endpoint"))
    parser.add_argument(
        "--direction", choices=("increase", "decrease", "two-sided")
    )
    parser.add_argument("--minimum-relative-effect", type=float)
    parser.add_argument("--output", required=True)
    parser.add_argument("--backend", default="auto", choices=("auto", "cpu", "gpu"))
    parser.add_argument("--prior-assessment")
    parser.add_argument("--decision-ledger")
    parser.add_argument("--allow-large-long-confirmation", action="store_true")
    args = parser.parse_args(argv)
    prior = _read_json(Path(args.prior_assessment)) if args.prior_assessment else None
    candidate_payload: dict[str, Any] | None = None
    candidate_spec_sha256 = None
    candidate_metadata: dict[str, Any] | None = None
    if args.candidate_spec:
        candidate_payload, candidate_spec_sha256 = load_candidate_spec(args.candidate_spec)
        candidate_metadata = candidate_portfolio_metadata(candidate_payload)
        supplied = {
            "candidate_id": args.candidate,
            "response_ticks": args.response_ticks,
            "intervention": args.intervention,
            "primary_metric": args.primary_metric,
            "metric_mode": args.metric_mode,
            "direction": args.direction,
            "minimum_relative_effect": args.minimum_relative_effect,
        }
        for key, value in supplied.items():
            if value is not None and value != candidate_payload[key]:
                parser.error(f"--candidate-spec conflicts with --{key.replace('_', '-')}")
    else:
        missing = [
            flag
            for flag, value in (
                ("--candidate", args.candidate),
                ("--response-ticks", args.response_ticks),
                ("--intervention", args.intervention),
                ("--primary-metric", args.primary_metric),
                ("--metric-mode", args.metric_mode),
                ("--direction", args.direction),
                ("--minimum-relative-effect", args.minimum_relative_effect),
            )
            if value is None
        ]
        if missing:
            parser.error("missing required arguments without --candidate-spec: " + ", ".join(missing))
        candidate_payload = {
            "candidate_id": args.candidate,
            "response_ticks": args.response_ticks,
            "intervention": args.intervention,
            "primary_metric": args.primary_metric,
            "metric_mode": args.metric_mode,
            "direction": args.direction,
            "minimum_relative_effect": args.minimum_relative_effect,
            "manipulation_checks": [],
        }
    plan = build_plan(
        stage=args.stage,
        candidate_id=str(candidate_payload["candidate_id"]),
        source_root=Path(args.source_root),
        checkpoint_tick=args.checkpoint_tick,
        response_ticks=int(candidate_payload["response_ticks"]),
        intervention=str(candidate_payload["intervention"]),
        primary_metric=str(candidate_payload["primary_metric"]),
        metric_mode=str(candidate_payload["metric_mode"]),
        direction=str(candidate_payload["direction"]),
        minimum_relative_effect=float(candidate_payload["minimum_relative_effect"]),
        output=Path(args.output),
        backend=args.backend,
        prior_assessment=prior,
        allow_large_long_confirmation=args.allow_large_long_confirmation,
        manipulation_checks=candidate_payload.get("manipulation_checks", []),
        candidate_spec_sha256=candidate_spec_sha256,
        candidate_spec_schema=(candidate_payload.get("schema") if args.candidate_spec else None),
        candidate_metadata=candidate_metadata,
        decision_ledger=Path(args.decision_ledger) if args.decision_ledger else None,
    )
    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=True)
    (output / "paired_exploration_plan.json").write_text(
        json.dumps(plan, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    (output / "paired_exploration_plan.md").write_text(
        render_plan_markdown(plan), encoding="utf-8"
    )
    return 0


def run_main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Execute a fixed-checkpoint paired panel.")
    parser.add_argument("--plan", required=True)
    args = parser.parse_args(argv)
    plan = _load_plan(Path(args.plan))
    execute_plan(plan)
    return 0


__all__ = [
    "ASSESSMENT_SCHEMA",
    "PLAN_SCHEMA",
    "RESULT_SCHEMA",
    "assess_results",
    "build_plan",
    "execute_plan",
    "load_candidate_spec",
    "plan_main",
    "run_main",
]
