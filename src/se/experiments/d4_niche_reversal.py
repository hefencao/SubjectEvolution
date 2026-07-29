"""D4-A paired resource-geography × inherited-affinity reversal audit.

The D2 fixed-module line is closed when module output does not replicate in the
redesigned source population.  D4-A returns to the charter's next causal link:
whether inherited phenotype differences condition persistence under a changed
multi-resource geography.

Each trusted checkpoint produces a four-branch factorial with identical entity,
world, and random-key state:

* baseline: original resource geography and inherited affinity expression;
* resource-reversed: only resource geography is rotated 180 degrees;
* affinity-neutral: inherited affinity is phenotypically neutralized;
* joint-neutral: resource geography is rotated and affinity is neutralized.

The interaction is a difference in differences.  It separates affinity-specific
environment matching from a general effect of rotating resource geography.  No
lineage is rewarded, protected, created, or reweighted, and no module copy
number or routing vocabulary is changed.
"""

from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
import hashlib
import json
from pathlib import Path
from typing import Any, Iterable, Sequence

import numpy as np

from se.experiments.d2_module_audit import (
    DEFAULT_OUTCOMES,
    _derived_endpoint,
    _flatten_numeric,
)
from se.env.niches import (
    AFFINITY_SCALE,
    RESOURCE_CHANNELS,
    resource_affinity_quantized,
)
from se.runtime.sim import Simulation

PLAN_SCHEMA = "d4-niche-reversal-plan-v1"
RESULT_SCHEMA = "d4-niche-reversal-results-v1"
SOURCE_PLAN_SCHEMA = "d2-source-population-causal-plan-v1"
SOURCE_ASSESSMENT_SCHEMA = "d2-source-population-causal-assessment-v1"

BRANCHES = (
    "baseline",
    "resource-reversed",
    "affinity-neutral",
    "joint-neutral",
)
INTERACTIONS = (
    "resource_geography_effect_with_affinity",
    "resource_geography_effect_affinity_neutral",
    "affinity_effect_original_geography",
    "affinity_effect_reversed_geography",
    "affinity_environment_interaction",
)


@dataclass(frozen=True)
class NicheLineage:
    lineage_id: int
    members: int
    member_fraction: float
    abundance_rank: int


@dataclass(frozen=True)
class NicheCheckpoint:
    run_name: str
    phase: str
    panel_seed: int
    checkpoint_tick: int
    checkpoint_path: str
    until_tick: int
    active_entities: int
    effective_lineages: float
    dominant_lineage_fraction: float
    lineages: tuple[NicheLineage, ...]


@dataclass(frozen=True)
class NicheReversalPlan:
    schema: str
    stage: str
    source_plan_schema: str
    source_plan_sha256: str | None
    source_assessment_schema: str
    source_assessment_sha256: str | None
    source_recommendation: str
    evidence_scope: str
    horizon_ticks: int
    checkpoints: tuple[NicheCheckpoint, ...]
    branches: tuple[str, ...] = BRANCHES
    resource_intervention: str = "reverse-resource-geography"
    phenotype_intervention: str = "neutralize-resource-affinity"
    factorial_schema: str = "resource-geography-by-affinity-expression-2x2-v1"
    source_selection_response_conditioned: bool = False
    lineage_selection_response_conditioned: bool = False
    paired_randomness: bool = True
    genotype_preserved: bool = True
    lineage_membership_preserved: bool = True
    hazard_modified: bool = False
    module_copy_number_changed: bool = False
    routing_vocabulary_changed: bool = False
    ecological_niche_claim: bool = False
    confirmation_source_result_schema: str | None = None
    confirmation_source_horizon_ticks: int | None = None


def _sha256(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def _panel_seed(run_name: str) -> int:
    token = run_name.rsplit("_", 1)[-1]
    try:
        return int(token)
    except ValueError as exc:
        raise ValueError(f"cannot infer panel seed from run name: {run_name!r}") from exc


def _lineage_from_payload(payload: dict[str, Any]) -> NicheLineage:
    return NicheLineage(
        lineage_id=int(payload["lineage_id"]),
        members=int(payload["members"]),
        member_fraction=float(payload["member_fraction"]),
        abundance_rank=int(payload["abundance_rank"]),
    )


def _checkpoint_from_payload(payload: dict[str, Any], *, horizon_ticks: int) -> NicheCheckpoint:
    checkpoint_tick = int(payload["checkpoint_tick"])
    return NicheCheckpoint(
        run_name=str(payload["run_name"]),
        phase=str(payload["phase"]),
        panel_seed=_panel_seed(str(payload["run_name"])),
        checkpoint_tick=checkpoint_tick,
        checkpoint_path=str(payload["checkpoint_path"]),
        until_tick=checkpoint_tick + int(horizon_ticks),
        active_entities=int(payload["active_entities"]),
        effective_lineages=float(payload["effective_lineages"]),
        dominant_lineage_fraction=float(payload["dominant_lineage_fraction"]),
        lineages=tuple(_lineage_from_payload(item) for item in payload["lineages"]),
    )


def build_niche_reversal_plan(
    source_plan: dict[str, Any],
    source_assessment: dict[str, Any],
    *,
    horizon_ticks: int = 120,
    source_plan_sha256: str | None = None,
    source_assessment_sha256: str | None = None,
) -> NicheReversalPlan:
    if source_plan.get("schema") != SOURCE_PLAN_SCHEMA:
        raise ValueError(f"unsupported D2-H plan schema: {source_plan.get('schema')!r}")
    if source_assessment.get("schema") != SOURCE_ASSESSMENT_SCHEMA:
        raise ValueError(
            f"unsupported D2-H assessment schema: {source_assessment.get('schema')!r}"
        )
    if horizon_ticks <= 0:
        raise ValueError("horizon_ticks must be positive")
    if bool(source_assessment.get("module_3_screen_pass")):
        raise ValueError(
            "D4-A is the stop-route after module 3 fails replication; a passing D2-H "
            "screen must follow its preregistered confirmation path instead"
        )
    expected = "module-3-not-replicated-in-redesigned-source-population-stop-before-copy-number"
    if source_assessment.get("recommendation") != expected:
        raise ValueError(
            "D4-A requires the explicit D2-H stop recommendation, got "
            f"{source_assessment.get('recommendation')!r}"
        )
    lineage_plan = source_plan.get("lineage_pair_plan", {})
    checkpoints: list[NicheCheckpoint] = []
    for item in lineage_plan.get("checkpoints", ()):
        if not bool(item.get("eligible", False)):
            continue
        checkpoint = _checkpoint_from_payload(item, horizon_ticks=horizon_ticks)
        if len(checkpoint.lineages) < 2:
            raise ValueError("D4-A requires at least two preregistered lineages per checkpoint")
        checkpoints.append(checkpoint)
    if len(checkpoints) < 2:
        raise ValueError("D4-A requires at least two independent qualified checkpoints")
    selected_seeds = tuple(int(value) for value in source_plan.get("selected_panel_seeds", ()))
    checkpoint_seeds = tuple(checkpoint.panel_seed for checkpoint in checkpoints)
    if selected_seeds and set(checkpoint_seeds) != set(selected_seeds):
        raise ValueError("D2-H selected panel seeds do not match embedded checkpoint seeds")
    return NicheReversalPlan(
        schema=PLAN_SCHEMA,
        stage="120-tick-exploratory-screen" if horizon_ticks == 120 else "confirmation",
        source_plan_schema=str(source_plan["schema"]),
        source_plan_sha256=source_plan_sha256,
        source_assessment_schema=str(source_assessment["schema"]),
        source_assessment_sha256=source_assessment_sha256,
        source_recommendation=str(source_assessment["recommendation"]),
        evidence_scope="phase-specific-exploratory-environment-matching-audit",
        horizon_ticks=int(horizon_ticks),
        checkpoints=tuple(checkpoints),
    )


def load_niche_reversal_plan(path: str | Path) -> NicheReversalPlan:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if payload.get("schema") != PLAN_SCHEMA:
        raise ValueError(f"unsupported D4-A plan schema: {payload.get('schema')!r}")
    checkpoints = tuple(
        NicheCheckpoint(
            run_name=str(item["run_name"]),
            phase=str(item["phase"]),
            panel_seed=int(item["panel_seed"]),
            checkpoint_tick=int(item["checkpoint_tick"]),
            checkpoint_path=str(item["checkpoint_path"]),
            until_tick=int(item["until_tick"]),
            active_entities=int(item["active_entities"]),
            effective_lineages=float(item["effective_lineages"]),
            dominant_lineage_fraction=float(item["dominant_lineage_fraction"]),
            lineages=tuple(_lineage_from_payload(lineage) for lineage in item["lineages"]),
        )
        for item in payload["checkpoints"]
    )
    return NicheReversalPlan(
        schema=str(payload["schema"]),
        stage=str(payload["stage"]),
        source_plan_schema=str(payload["source_plan_schema"]),
        source_plan_sha256=payload.get("source_plan_sha256"),
        source_assessment_schema=str(payload["source_assessment_schema"]),
        source_assessment_sha256=payload.get("source_assessment_sha256"),
        source_recommendation=str(payload["source_recommendation"]),
        evidence_scope=str(payload["evidence_scope"]),
        horizon_ticks=int(payload["horizon_ticks"]),
        checkpoints=checkpoints,
        branches=tuple(payload.get("branches", BRANCHES)),
        resource_intervention=str(payload.get("resource_intervention", "reverse-resource-geography")),
        phenotype_intervention=str(payload.get("phenotype_intervention", "neutralize-resource-affinity")),
        factorial_schema=str(payload.get("factorial_schema", "resource-geography-by-affinity-expression-2x2-v1")),
        source_selection_response_conditioned=bool(payload.get("source_selection_response_conditioned", False)),
        lineage_selection_response_conditioned=bool(payload.get("lineage_selection_response_conditioned", False)),
        paired_randomness=bool(payload.get("paired_randomness", True)),
        genotype_preserved=bool(payload.get("genotype_preserved", True)),
        lineage_membership_preserved=bool(payload.get("lineage_membership_preserved", True)),
        hazard_modified=bool(payload.get("hazard_modified", False)),
        module_copy_number_changed=bool(payload.get("module_copy_number_changed", False)),
        routing_vocabulary_changed=bool(payload.get("routing_vocabulary_changed", False)),
        ecological_niche_claim=bool(payload.get("ecological_niche_claim", False)),
        confirmation_source_result_schema=payload.get("confirmation_source_result_schema"),
        confirmation_source_horizon_ticks=(
            int(payload["confirmation_source_horizon_ticks"])
            if payload.get("confirmation_source_horizon_ticks") is not None
            else None
        ),
    )


def build_confirmation_plan(
    screen_plan: NicheReversalPlan,
    *,
    horizon_ticks: int,
    source_result_schema: str,
) -> NicheReversalPlan:
    if horizon_ticks <= screen_plan.horizon_ticks:
        raise ValueError("confirmation horizon must exceed screen horizon")
    checkpoints = tuple(
        NicheCheckpoint(
            **{
                **asdict(item),
                "until_tick": item.checkpoint_tick + int(horizon_ticks),
                "lineages": item.lineages,
            }
        )
        for item in screen_plan.checkpoints
    )
    return NicheReversalPlan(
        **{
            **asdict(screen_plan),
            "stage": "300-tick-confirmation" if horizon_ticks == 300 else "confirmation",
            "horizon_ticks": int(horizon_ticks),
            "checkpoints": checkpoints,
            "branches": screen_plan.branches,
            "confirmation_source_result_schema": source_result_schema,
            "confirmation_source_horizon_ticks": screen_plan.horizon_ticks,
        }
    )


def _resolve_checkpoint_path(value: str, *, base_dir: Path | None = None) -> Path:
    path = Path(value)
    if path.is_file():
        return path.resolve()
    if base_dir is not None and not path.is_absolute():
        candidate = (base_dir / path).resolve()
        if candidate.is_file():
            return candidate
    raise FileNotFoundError(f"referenced D4-A checkpoint does not exist: {value}")


def _source_diagnostics(simulation: Simulation, checkpoint: NicheCheckpoint) -> dict[str, Any]:
    if simulation.resource_affinity_ablation_enabled:
        raise ValueError("D4-A source checkpoint already neutralizes resource affinity")
    if bool(getattr(simulation.environment, "resource_spatial_reversed", False)):
        raise ValueError("D4-A source checkpoint already has reversed resource geography")
    if simulation.environment.spatial_reversed:
        raise ValueError("D4-A source checkpoint already has reversed full environment")
    active = np.flatnonzero(simulation.entities.alive).astype(np.int32)
    if int(active.size) != checkpoint.active_entities:
        raise ValueError(
            "D4-A checkpoint active count does not match plan: "
            f"{active.size} vs {checkpoint.active_entities}"
        )
    cells = simulation.spatial.backend.to_numpy(
        simulation.spatial.cell_ids(
            simulation.entities.x[active], simulation.entities.y[active]
        )
    ).astype(np.int32, copy=False)
    resources = np.asarray(simulation.environment.resources, dtype=np.float64)
    capacity = np.asarray(simulation.cfg.environment.resource_capacity, dtype=np.float64)
    normalized = resources / capacity[:, None, None]
    original = normalized.reshape(RESOURCE_CHANNELS, -1)[:, cells].T
    reversed_values = normalized[:, ::-1, ::-1].reshape(RESOURCE_CHANNELS, -1)[:, cells].T
    affinity_q = resource_affinity_quantized(
        simulation.entities.genotype[active], simulation.cfg
    ).astype(np.float64)
    weights = affinity_q / (RESOURCE_CHANNELS * AFFINITY_SCALE)
    original_utility = np.sum(original * weights, axis=1)
    reversed_utility = np.sum(reversed_values * weights, axis=1)
    original_uniform = original.mean(axis=1)
    reversed_uniform = reversed_values.mean(axis=1)
    lineage_ids = simulation.entities.lineage_id[active].astype(np.uint64, copy=False)
    rows: list[dict[str, Any]] = []
    planned_ids = {item.lineage_id for item in checkpoint.lineages}
    for lineage in checkpoint.lineages:
        mask = lineage_ids == np.uint64(lineage.lineage_id)
        if int(np.count_nonzero(mask)) != lineage.members:
            raise ValueError(
                f"lineage {lineage.lineage_id} source members do not match plan"
            )
        mean_affinity = (affinity_q[mask].mean(axis=0) / AFFINITY_SCALE).tolist()
        exposure = original_utility[mask] - reversed_utility[mask]
        uniform_exposure = original_uniform[mask] - reversed_uniform[mask]
        specific = exposure - uniform_exposure
        rows.append(
            {
                **asdict(lineage),
                "non_dominant": lineage.abundance_rank > 1,
                "source_affinity_mean": [float(value) for value in mean_affinity],
                "source_affinity_dominant_channel": int(np.argmax(mean_affinity)),
                "source_local_resource_fraction_mean": [
                    float(value) for value in original[mask].mean(axis=0)
                ],
                "source_reversed_resource_fraction_mean": [
                    float(value) for value in reversed_values[mask].mean(axis=0)
                ],
                "source_affinity_weighted_utility_mean": float(original_utility[mask].mean()),
                "source_reversed_affinity_weighted_utility_mean": float(reversed_utility[mask].mean()),
                "source_uniform_utility_mean": float(original_uniform[mask].mean()),
                "source_reversed_uniform_utility_mean": float(reversed_uniform[mask].mean()),
                "source_affinity_specific_exposure_advantage_mean": float(specific.mean()),
            }
        )
    present_planned = {
        int(value) for value in np.unique(lineage_ids) if int(value) in planned_ids
    }
    if present_planned != planned_ids:
        raise ValueError("not all planned D4-A lineages are present in source checkpoint")
    return {
        "schema": "d4-source-lineage-environment-match-diagnostics-v1",
        "checkpoint_tick": int(simulation.tick),
        "resource_spatial_reversed": False,
        "hazard_spatial_reversed": bool(simulation.environment.spatial_reversed),
        "lineages": rows,
    }


def _lineage_endpoint(simulation: Simulation, lineage_id: int) -> dict[str, float]:
    rows = np.flatnonzero(
        simulation.entities.alive
        & (simulation.entities.lineage_id == np.uint64(lineage_id))
    ).astype(np.int32)
    world_alive = int(np.count_nonzero(simulation.entities.alive))
    result: dict[str, float] = {
        "alive": float(rows.size),
        "world_share": float(rows.size / world_alive) if world_alive else 0.0,
    }
    for name in ("energy", "integrity", "material", "information_store", "fertility"):
        values = np.asarray(getattr(simulation.entities, name)[rows], dtype=np.float64)
        result[f"mean_{name}"] = float(values.mean()) if values.size else 0.0
        result[f"total_{name}"] = float(values.sum()) if values.size else 0.0
    if rows.size:
        affinity = resource_affinity_quantized(
            simulation.entities.genotype[rows], simulation.cfg
        ).astype(np.float64) / AFFINITY_SCALE
        for channel in range(RESOURCE_CHANNELS):
            result[f"mean_resource_affinity_{channel}"] = float(affinity[:, channel].mean())
    else:
        for channel in range(RESOURCE_CHANNELS):
            result[f"mean_resource_affinity_{channel}"] = 0.0
    return result


def _branch_outcomes(
    branch: dict[str, Any],
    simulation: Simulation,
    lineage_id: int | None = None,
) -> dict[str, float]:
    flattened = {
        **_flatten_numeric("world", branch["world"]),
        **_flatten_numeric("evolution", branch["evolution"]),
        **_flatten_numeric("derived", branch["derived"]),
    }
    if lineage_id is not None:
        flattened.update(
            _flatten_numeric("target_lineage", _lineage_endpoint(simulation, lineage_id))
        )
    selected = {
        outcome: flattened[outcome]
        for outcome in DEFAULT_OUTCOMES
        if outcome in flattened
    }
    selected.update(
        {
            key: value
            for key, value in flattened.items()
            if key.startswith("target_lineage.")
        }
    )
    return selected


def _run_branch(
    checkpoint: NicheCheckpoint,
    checkpoint_path: Path,
    output_dir: Path,
    *,
    branch_name: str,
    backend: str,
    gpu_semantics_mode: str | None,
    capture_source: bool = False,
) -> tuple[dict[str, Any], Simulation, dict[str, Any] | None]:
    simulation = Simulation.from_checkpoint(
        checkpoint_path,
        output_dir,
        backend=backend,
        until_tick=checkpoint.until_tick,
        gpu_semantics_mode=gpu_semantics_mode,
    )
    source = _source_diagnostics(simulation, checkpoint) if capture_source else None
    genotype_before = simulation.entities.genotype.copy()
    lineage_before = simulation.entities.lineage_id.copy()
    hazard_before = np.asarray(simulation.environment.hazard).copy()
    mortality_before = np.asarray(simulation.environment.mortality_trace).copy()
    interventions: list[str] = []
    if branch_name in ("resource-reversed", "joint-neutral"):
        simulation.apply_intervention("reverse-resource-geography")
        interventions.append("reverse-resource-geography")
    if branch_name in ("affinity-neutral", "joint-neutral"):
        simulation.apply_intervention("neutralize-resource-affinity")
        interventions.append("neutralize-resource-affinity")
    if branch_name not in BRANCHES:
        raise ValueError(f"unsupported D4-A branch: {branch_name!r}")
    if not np.array_equal(simulation.entities.genotype, genotype_before):
        raise RuntimeError("D4-A intervention modified genotype")
    if not np.array_equal(simulation.entities.lineage_id, lineage_before):
        raise RuntimeError("D4-A intervention modified lineage IDs")
    if not np.array_equal(np.asarray(simulation.environment.hazard), hazard_before):
        raise RuntimeError("resource-only reversal modified hazard")
    if not np.array_equal(np.asarray(simulation.environment.mortality_trace), mortality_before):
        raise RuntimeError("resource-only reversal modified mortality trace")
    world = simulation.run(until_tick=checkpoint.until_tick)
    evolution = (
        simulation.evolution_progress.records[-1]
        if simulation.evolution_progress.records
        else {}
    )
    return (
        {
            "branch": branch_name,
            "interventions": interventions,
            "output_dir": str(output_dir),
            "world": world,
            "evolution": evolution,
            "derived": _derived_endpoint(evolution),
            "scientific_validity": simulation.scientific_validity(),
            "intervention_history": simulation.intervention_history,
            "resource_spatial_reversed": bool(
                getattr(simulation.environment, "resource_spatial_reversed", False)
            ),
            "hazard_spatial_reversed": bool(simulation.environment.spatial_reversed),
        },
        simulation,
        source,
    )


def _factorial_effects(branches: dict[str, dict[str, float]]) -> dict[str, dict[str, float]]:
    common = sorted(set.intersection(*(set(values) for values in branches.values())))
    baseline = branches["baseline"]
    reversed_branch = branches["resource-reversed"]
    neutral = branches["affinity-neutral"]
    joint = branches["joint-neutral"]
    env_active = {key: baseline[key] - reversed_branch[key] for key in common}
    env_neutral = {key: neutral[key] - joint[key] for key in common}
    affinity_original = {key: baseline[key] - neutral[key] for key in common}
    affinity_reversed = {key: reversed_branch[key] - joint[key] for key in common}
    interaction = {key: env_active[key] - env_neutral[key] for key in common}
    alternate = {key: affinity_original[key] - affinity_reversed[key] for key in common}
    residual = {key: interaction[key] - alternate[key] for key in common}
    if any(abs(value) > 1e-12 for value in residual.values()):
        raise RuntimeError("D4-A factorial decomposition is not numerically closed")
    return {
        "resource_geography_effect_with_affinity": env_active,
        "resource_geography_effect_affinity_neutral": env_neutral,
        "affinity_effect_original_geography": affinity_original,
        "affinity_effect_reversed_geography": affinity_reversed,
        "affinity_environment_interaction": interaction,
        "factorial_residual": residual,
    }


def _aggregate(rows: Sequence[dict[str, Any]]) -> dict[str, Any]:
    buckets: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for row in rows:
        for effect_name in INTERACTIONS:
            for outcome, value in row["effects"][effect_name].items():
                buckets.setdefault((effect_name, outcome), []).append(
                    {**row["lineage"], "value": float(value)}
                )
    result: dict[str, Any] = {}
    for (effect_name, outcome), values in sorted(buckets.items()):
        array = np.asarray([item["value"] for item in values], dtype=np.float64)
        nonzero = array[np.abs(array) > 1e-12]
        result.setdefault(effect_name, {})[outcome] = {
            "lineage_count": int(array.size),
            "checkpoint_count": len({(item["run_name"], item["checkpoint_tick"]) for item in values}),
            "seed_count": len({item["panel_seed"] for item in values}),
            "mean": float(array.mean()),
            "median": float(np.median(array)),
            "min": float(array.min()),
            "max": float(array.max()),
            "positive_count": int(np.count_nonzero(array > 1e-12)),
            "negative_count": int(np.count_nonzero(array < -1e-12)),
            "same_nonzero_sign": bool(
                nonzero.size and (np.all(nonzero > 0.0) or np.all(nonzero < 0.0))
            ),
            "equal_weight_per_checkpoint_lineage": True,
        }
    return result


def execute_niche_reversal_plan(
    plan: NicheReversalPlan,
    output_dir: str | Path,
    *,
    backend: str = "auto",
    gpu_semantics_mode: str | None = None,
    plan_base_dir: str | Path | None = None,
) -> dict[str, Any]:
    if tuple(plan.branches) != BRANCHES:
        raise ValueError(f"unsupported D4-A branch layout: {plan.branches!r}")
    if plan.hazard_modified:
        raise ValueError("D4-A resource reversal must not modify hazard")
    root = Path(output_dir)
    root.mkdir(parents=True, exist_ok=True)
    base_dir = Path(plan_base_dir).resolve() if plan_base_dir is not None else None
    checkpoint_reports: list[dict[str, Any]] = []
    all_lineage_rows: list[dict[str, Any]] = []
    for checkpoint in plan.checkpoints:
        checkpoint_path = _resolve_checkpoint_path(checkpoint.checkpoint_path, base_dir=base_dir)
        checkpoint_root = root / checkpoint.run_name / checkpoint.phase
        branch_payloads: dict[str, dict[str, Any]] = {}
        branch_simulations: dict[str, Simulation] = {}
        source: dict[str, Any] | None = None
        for branch_name in BRANCHES:
            payload, simulation, captured_source = _run_branch(
                checkpoint,
                checkpoint_path,
                checkpoint_root / branch_name.replace("-", "_"),
                branch_name=branch_name,
                backend=backend,
                gpu_semantics_mode=gpu_semantics_mode,
                capture_source=(branch_name == "baseline"),
            )
            if captured_source is not None:
                source = captured_source
            branch_payloads[branch_name] = payload
            branch_simulations[branch_name] = simulation
        if source is None:
            raise RuntimeError("D4-A baseline failed to capture source diagnostics")
        world_outcomes = {
            name: _branch_outcomes(payload, branch_simulations[name])
            for name, payload in branch_payloads.items()
        }
        world_effects = _factorial_effects(world_outcomes)
        source_by_lineage = {
            int(row["lineage_id"]): row for row in source["lineages"]
        }
        lineage_rows: list[dict[str, Any]] = []
        for lineage in checkpoint.lineages:
            outcomes = {
                name: _branch_outcomes(
                    branch_payloads[name], branch_simulations[name], lineage.lineage_id
                )
                for name in BRANCHES
            }
            effects = _factorial_effects(outcomes)
            meta = {
                "run_name": checkpoint.run_name,
                "phase": checkpoint.phase,
                "panel_seed": checkpoint.panel_seed,
                "checkpoint_tick": checkpoint.checkpoint_tick,
                **asdict(lineage),
                "non_dominant": lineage.abundance_rank > 1,
                "source_diagnostics": source_by_lineage[lineage.lineage_id],
            }
            row = {
                "lineage": meta,
                "branch_outcomes": outcomes,
                "effects": effects,
            }
            lineage_rows.append(row)
            all_lineage_rows.append(row)
        checkpoint_reports.append(
            {
                "checkpoint": asdict(checkpoint),
                "source_diagnostics": source,
                "branches": {
                    name: {
                        key: value
                        for key, value in payload.items()
                        if key not in ("world", "evolution", "derived")
                    }
                    for name, payload in branch_payloads.items()
                },
                "world_branch_outcomes": world_outcomes,
                "world_effects": world_effects,
                "lineages": lineage_rows,
            }
        )
    report = {
        "schema": RESULT_SCHEMA,
        "plan": asdict(plan),
        "backend": backend,
        "gpu_semantics_mode": gpu_semantics_mode,
        "checkpoints": checkpoint_reports,
        "aggregate_effects": _aggregate(all_lineage_rows),
        "executed_checkpoint_count": len(checkpoint_reports),
        "executed_lineage_count": len(all_lineage_rows),
        "ecological_niche_ready": False,
        "module_copy_number_ready": False,
        "interpretation_boundary": (
            "The four branches form a shared-checkpoint 2x2 causal factorial. The "
            "affinity-environment interaction tests whether inherited affinity changes "
            "the effect of resource-geography reversal. A checkpoint-lineage is an "
            "outcome unit, while independent panel seeds remain the replication unit. "
            "A positive screen may justify a longer confirmation; it does not by itself "
            "establish stable ecological niches, coexistence, or module-copy benefit."
        ),
    }
    (root / "d4_niche_reversal_results.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (root / "d4_niche_reversal_results.md").write_text(
        render_results_markdown(report), encoding="utf-8"
    )
    return report


def render_plan_markdown(plan: NicheReversalPlan) -> str:
    lines = [
        "# D4-A resource-geography × inherited-affinity reversal plan",
        "",
        f"Schema: `{plan.schema}`",
        f"Stage: `{plan.stage}`",
        f"Evidence scope: `{plan.evidence_scope}`",
        f"Horizon: **{plan.horizon_ticks} ticks**",
        "",
        "| Run | Phase | Seed | Checkpoint | Active | Effective lineages | Dominant share | Lineages |",
        "|---|---|---:|---:|---:|---:|---:|---:|",
    ]
    for checkpoint in plan.checkpoints:
        lines.append(
            f"| {checkpoint.run_name} | {checkpoint.phase} | {checkpoint.panel_seed} | "
            f"{checkpoint.checkpoint_tick} | {checkpoint.active_entities} | "
            f"{checkpoint.effective_lineages:.4f} | "
            f"{checkpoint.dominant_lineage_fraction:.4f} | {len(checkpoint.lineages)} |"
        )
    lines.extend(
        [
            "",
            "## Shared-checkpoint branches",
            "",
            "- `baseline`: original resource geography, inherited affinity expressed",
            "- `resource-reversed`: resource geography rotated 180°, affinity expressed",
            "- `affinity-neutral`: original geography, affinity expression neutralized",
            "- `joint-neutral`: reversed geography and neutralized affinity",
            "",
            "The primary contrast is `(baseline - resource-reversed) - (affinity-neutral - joint-neutral)`. Hazard, mortality trace, genotype, lineage membership, resource identity, and resource effects are unchanged.",
            "",
            "> All preregistered lineages from each qualified source checkpoint are retained. No response-conditioned lineage selection or diversity protection is used.",
            "",
        ]
    )
    return "\n".join(lines)


def render_results_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# D4-A resource-geography × inherited-affinity reversal results",
        "",
        f"Schema: `{report['schema']}`",
        f"Executed checkpoints: `{report['executed_checkpoint_count']}`",
        f"Executed checkpoint-lineages: `{report['executed_lineage_count']}`",
        "",
        "| Run | Seed | Lineage | Rank | Source exposure | Outcome | Interaction |",
        "|---|---:|---:|---:|---:|---|---:|",
    ]
    for checkpoint in report["checkpoints"]:
        for row in checkpoint["lineages"]:
            lineage = row["lineage"]
            exposure = lineage["source_diagnostics"][
                "source_affinity_specific_exposure_advantage_mean"
            ]
            for outcome in (
                "target_lineage.alive",
                "target_lineage.world_share",
                "target_lineage.mean_energy",
                "target_lineage.total_energy",
            ):
                value = row["effects"]["affinity_environment_interaction"].get(outcome)
                if value is None:
                    continue
                lines.append(
                    f"| {lineage['run_name']} | {lineage['panel_seed']} | "
                    f"{lineage['lineage_id']} | {lineage['abundance_rank']} | "
                    f"{exposure:+.6f} | `{outcome}` | {value:+.6f} |"
                )
    lines.extend(["", "## Interpretation boundary", "", report["interpretation_boundary"], ""])
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Plan or execute D4-A resource-geography × affinity reversal audit"
    )
    parser.add_argument("--source-plan", help="D2-H source-population causal plan JSON")
    parser.add_argument("--source-assessment", help="D2-H source-population causal assessment JSON")
    parser.add_argument("--plan", help="Existing D4-A plan JSON")
    parser.add_argument("--output", required=True)
    parser.add_argument("--horizon", type=int, default=120)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--backend", choices=("cpu", "gpu", "auto"), default="auto")
    parser.add_argument(
        "--gpu-semantics-mode",
        choices=("strict-reference", "hybrid-accelerated"),
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    supplied_sources = bool(args.source_plan or args.source_assessment)
    if bool(args.plan) == supplied_sources:
        raise ValueError(
            "provide --plan, or both --source-plan and --source-assessment"
        )
    if supplied_sources and not (args.source_plan and args.source_assessment):
        raise ValueError("--source-plan and --source-assessment are required together")
    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=True)
    if args.plan:
        plan_path = Path(args.plan)
        plan = load_niche_reversal_plan(plan_path)
        plan_base_dir = plan_path.resolve().parent
    else:
        source_plan_path = Path(args.source_plan)
        source_assessment_path = Path(args.source_assessment)
        source_plan = json.loads(source_plan_path.read_text(encoding="utf-8"))
        source_assessment = json.loads(source_assessment_path.read_text(encoding="utf-8"))
        plan = build_niche_reversal_plan(
            source_plan,
            source_assessment,
            horizon_ticks=args.horizon,
            source_plan_sha256=_sha256(source_plan_path),
            source_assessment_sha256=_sha256(source_assessment_path),
        )
        plan_base_dir = source_plan_path.resolve().parent
    (output / "d4_niche_reversal_plan.json").write_text(
        json.dumps(asdict(plan), ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (output / "d4_niche_reversal_plan.md").write_text(
        render_plan_markdown(plan), encoding="utf-8"
    )
    if args.execute:
        execute_niche_reversal_plan(
            plan,
            output,
            backend=args.backend,
            gpu_semantics_mode=args.gpu_semantics_mode,
            plan_base_dir=plan_base_dir,
        )


if __name__ == "__main__":
    main()
