"""Run D3-F shared-checkpoint spatial-processing response audit.

The audit adds no policy feature, reward, controller, ecological role, or material
flux.  It restores original-support, reversed-support, and neutral-support
branches from one tick-0 checkpoint and records whether ordinary movement is
aligned with inventory-weighted processing opportunity.  The orientation
intervention rotates only the non-material support surface; the neutral branch
retains the same execution cost with multiplier one.
"""
from __future__ import annotations

import argparse
import json
import shutil
from dataclasses import asdict, replace
from pathlib import Path
from typing import Any, Iterable

import numpy as np

from se.checkpointing import read_checkpoint_bundle
from se.cfg import SimulationConfig, load_config
from se.differentiation.physiology import physiology_phenotype
from se.experiments.d3_conservative_intake import parse_seeds
from se.experiments.d3_external_recycling import _ledger as recycling_ledger
from se.experiments.d3_persistent_resource_renewal import _resource_ledger
from se.experiments.d3_spatial_processing import _require, _snapshot
from se.policy import Action, ParametricPolicy
from se.runtime.sim import Simulation
from se.runtime.state import StepStats

PLAN_SCHEMA = "d3-spatial-processing-response-plan-v2"
RESULT_SCHEMA = "d3-spatial-processing-response-results-v2"
TRAJECTORY_SCHEMA = "inventory-weighted-processing-response-trajectory-v1"
BRANCHES = ("original-support", "reversed-support", "neutral-support")
REVERSE_INTERVENTION = "reverse-spatial-processing-support"
NEUTRAL_INTERVENTION = "neutralize-spatial-processing-support"
MOVEMENT_ACTIONS = (int(Action.MOVE_RESOURCE), int(Action.MOVE_SOCIAL), int(Action.FLEE))


def _safe_corr(left: np.ndarray, right: np.ndarray) -> float:
    x = np.asarray(left, dtype=np.float64)
    y = np.asarray(right, dtype=np.float64)
    if x.size < 2 or y.size != x.size:
        return 0.0
    x = x - x.mean()
    y = y - y.mean()
    scale = float(np.sqrt(np.dot(x, x) * np.dot(y, y)))
    return float(np.dot(x, y) / scale) if scale > 0.0 else 0.0


def _periodic_delta(current: np.ndarray, previous: np.ndarray, extent: float) -> np.ndarray:
    delta = np.asarray(current, dtype=np.float64) - np.asarray(previous, dtype=np.float64)
    if extent <= 0.0:
        return delta
    return (delta + 0.5 * extent) % extent - 0.5 * extent


def _bilinear_support(
    field: np.ndarray,
    x: np.ndarray,
    y: np.ndarray,
    *,
    width: float,
    height: float,
) -> np.ndarray:
    """Read-only smooth sample of the authoritative cell support surface."""

    values = np.asarray(field, dtype=np.float64)
    channels, gy, gx = values.shape
    px = np.mod(np.asarray(x, dtype=np.float64), width) * gx / width
    py = np.mod(np.asarray(y, dtype=np.float64), height) * gy / height
    x0 = np.floor(px).astype(np.int64) % gx
    y0 = np.floor(py).astype(np.int64) % gy
    x1 = (x0 + 1) % gx
    y1 = (y0 + 1) % gy
    fx = px - np.floor(px)
    fy = py - np.floor(py)
    v00 = values[:, y0, x0].T
    v10 = values[:, y0, x1].T
    v01 = values[:, y1, x0].T
    v11 = values[:, y1, x1].T
    return (
        v00 * ((1.0 - fx) * (1.0 - fy))[:, None]
        + v10 * (fx * (1.0 - fy))[:, None]
        + v01 * ((1.0 - fx) * fy)[:, None]
        + v11 * (fx * fy)[:, None]
    )


def _weighted_support(demand: np.ndarray, support: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    weights = np.asarray(demand, dtype=np.float64)
    values = np.asarray(support, dtype=np.float64)
    total = weights.sum(axis=1, dtype=np.float64)
    scalar = np.divide(
        (weights * values).sum(axis=1, dtype=np.float64),
        total,
        out=np.ones(total.shape, dtype=np.float64),
        where=total > 1.0e-12,
    )
    return scalar, total


class SpatialProcessingResponseObserver:
    """Read-only inventory-conditioned movement and exposure observer."""

    def __init__(self, *, horizon: int, observation_period: int, branch: str) -> None:
        if observation_period <= 0:
            raise ValueError("observation_period must be positive")
        self.horizon = int(horizon)
        self.observation_period = int(observation_period)
        self.branch = str(branch)
        self.previous: dict[str, np.ndarray] | None = None
        self.trajectory: list[dict[str, Any]] = []
        self.initialized = False
        self.cumulative: dict[str, float] = {
            "eligible_entity_ticks": 0.0,
            "all_move_count": 0.0,
            "resource_move_count": 0.0,
            "control_move_count": 0.0,
            "all_move_distance": 0.0,
            "resource_move_distance": 0.0,
            "control_move_distance": 0.0,
            "all_move_support_gain_sum": 0.0,
            "resource_move_support_gain_sum": 0.0,
            "control_move_support_gain_sum": 0.0,
            "all_move_support_gain_positive": 0.0,
            "resource_move_support_gain_positive": 0.0,
            "control_move_support_gain_positive": 0.0,
            "all_move_alignment_cosine_sum": 0.0,
            "resource_move_alignment_cosine_sum": 0.0,
            "control_move_alignment_cosine_sum": 0.0,
            "all_move_alignment_cosine_count": 0.0,
            "resource_move_alignment_cosine_count": 0.0,
            "control_move_alignment_cosine_count": 0.0,
        }

    @staticmethod
    def _capture(simulation: Simulation) -> dict[str, np.ndarray]:
        rows = np.flatnonzero(simulation.entities.alive).astype(np.int32)
        ids = np.asarray(simulation.entities.entity_id[rows], dtype=np.uint64)
        order = np.argsort(ids, kind="stable")
        rows = rows[order]
        return {
            "ids": ids[order],
            "x": np.asarray(simulation.entities.x[rows], dtype=np.float64).copy(),
            "y": np.asarray(simulation.entities.y[rows], dtype=np.float64).copy(),
            "store": np.asarray(
                simulation.entities.resource_store[rows], dtype=np.float64
            ).copy(),
            "genotype": np.asarray(
                simulation.entities.genotype[rows], dtype=np.float32
            ).copy(),
        }

    @staticmethod
    def _action_map(simulation: Simulation) -> dict[int, tuple[int, bool]]:
        intents = simulation.last_intents
        resolutions = simulation.last_resolutions
        if intents is None or resolutions is None:
            return {}
        return {
            int(entity_id): (int(action), bool(success))
            for entity_id, action, success in zip(
                np.asarray(intents.carrier_id),
                np.asarray(intents.action),
                np.asarray(resolutions.success),
                strict=True,
            )
        }

    @staticmethod
    def _demand(simulation: Simulation, store: np.ndarray, genotype: np.ndarray) -> np.ndarray:
        phenotype = physiology_phenotype(
            genotype,
            simulation.cfg,
            gene_start=ParametricPolicy.physiology_gene_start(simulation.cfg),
        )
        return np.minimum(
            np.maximum(np.asarray(store, dtype=np.float64), 0.0),
            np.asarray(phenotype.resource_conversion_capacity, dtype=np.float64),
        )

    def _snapshot(self, simulation: Simulation) -> dict[str, Any]:
        state = self._capture(simulation)
        demand = self._demand(simulation, state["store"], state["genotype"])
        support = _bilinear_support(
            simulation.environment.resource_processing_support_field(simulation.tick),
            state["x"],
            state["y"],
            width=float(simulation.cfg.world.width),
            height=float(simulation.cfg.world.height),
        )
        scalar, demand_total = _weighted_support(demand, support)
        valid = demand_total > 1.0e-12
        channel_corr = [
            _safe_corr(state["store"][:, channel], support[:, channel])
            for channel in range(4)
        ]
        return {
            "tick": int(simulation.tick),
            "alive": int(state["ids"].size),
            "inventory_eligible": int(np.count_nonzero(valid)),
            "inventory_weighted_support_mean": (
                float(np.average(scalar[valid], weights=demand_total[valid]))
                if np.any(valid)
                else 1.0
            ),
            "entity_mean_inventory_weighted_support": (
                float(scalar[valid].mean()) if np.any(valid) else 1.0
            ),
            "store_support_correlation_by_channel": channel_corr,
            "store_support_mean_abs_correlation": float(
                np.mean(np.abs(channel_corr))
            ),
            "cumulative": self.summary(),
        }

    def _accumulate_category(
        self,
        category: str,
        mask: np.ndarray,
        distance: np.ndarray,
        gain: np.ndarray,
        cosine: np.ndarray,
        cosine_valid: np.ndarray,
    ) -> None:
        count = int(np.count_nonzero(mask))
        self.cumulative[f"{category}_move_count"] += count
        if not count:
            return
        self.cumulative[f"{category}_move_distance"] += float(distance[mask].sum())
        self.cumulative[f"{category}_move_support_gain_sum"] += float(gain[mask].sum())
        self.cumulative[f"{category}_move_support_gain_positive"] += int(
            np.count_nonzero(gain[mask] > 0.0)
        )
        aligned = mask & cosine_valid
        self.cumulative[f"{category}_move_alignment_cosine_sum"] += float(
            cosine[aligned].sum()
        )
        self.cumulative[f"{category}_move_alignment_cosine_count"] += int(
            np.count_nonzero(aligned)
        )

    def _accumulate_step(self, simulation: Simulation, current: dict[str, np.ndarray]) -> None:
        assert self.previous is not None
        previous = self.previous
        common, prev_idx, cur_idx = np.intersect1d(
            previous["ids"], current["ids"], assume_unique=True, return_indices=True
        )
        if common.size == 0:
            return
        prev_x = previous["x"][prev_idx]
        prev_y = previous["y"][prev_idx]
        cur_x = current["x"][cur_idx]
        cur_y = current["y"][cur_idx]
        demand = self._demand(
            simulation,
            previous["store"][prev_idx],
            previous["genotype"][prev_idx],
        )
        _, demand_total = _weighted_support(demand, np.ones_like(demand))
        eligible = demand_total > 1.0e-12
        self.cumulative["eligible_entity_ticks"] += int(np.count_nonzero(eligible))
        step_tick = int(simulation.tick) - 1
        next_tick = int(simulation.tick)
        next_field = simulation.environment.resource_processing_support_field(next_tick)
        destination = _bilinear_support(
            next_field,
            cur_x,
            cur_y,
            width=float(simulation.cfg.world.width),
            height=float(simulation.cfg.world.height),
        )
        stationary = _bilinear_support(
            next_field,
            prev_x,
            prev_y,
            width=float(simulation.cfg.world.width),
            height=float(simulation.cfg.world.height),
        )
        destination_scalar, _ = _weighted_support(demand, destination)
        stationary_scalar, _ = _weighted_support(demand, stationary)
        gain = destination_scalar - stationary_scalar

        width = float(simulation.cfg.world.width)
        height = float(simulation.cfg.world.height)
        dx = _periodic_delta(cur_x, prev_x, width)
        dy = _periodic_delta(cur_y, prev_y, height)
        distance = np.sqrt(dx * dx + dy * dy)

        epsilon_x = width / float(simulation.cfg.world.grid_x)
        epsilon_y = height / float(simulation.cfg.world.grid_y)
        plus_x = _bilinear_support(
            next_field, prev_x + epsilon_x, prev_y, width=width, height=height
        )
        minus_x = _bilinear_support(
            next_field, prev_x - epsilon_x, prev_y, width=width, height=height
        )
        plus_y = _bilinear_support(
            next_field, prev_x, prev_y + epsilon_y, width=width, height=height
        )
        minus_y = _bilinear_support(
            next_field, prev_x, prev_y - epsilon_y, width=width, height=height
        )
        sx_plus, _ = _weighted_support(demand, plus_x)
        sx_minus, _ = _weighted_support(demand, minus_x)
        sy_plus, _ = _weighted_support(demand, plus_y)
        sy_minus, _ = _weighted_support(demand, minus_y)
        grad_x = (sx_plus - sx_minus) / (2.0 * epsilon_x)
        grad_y = (sy_plus - sy_minus) / (2.0 * epsilon_y)
        grad_norm = np.sqrt(grad_x * grad_x + grad_y * grad_y)
        cosine_valid = eligible & (distance > 1.0e-12) & (grad_norm > 1.0e-12)
        cosine = np.zeros(common.size, dtype=np.float64)
        cosine[cosine_valid] = (
            dx[cosine_valid] * grad_x[cosine_valid]
            + dy[cosine_valid] * grad_y[cosine_valid]
        ) / (distance[cosine_valid] * grad_norm[cosine_valid])

        actions = self._action_map(simulation)
        action = np.asarray([actions.get(int(entity_id), (-1, False))[0] for entity_id in common])
        success = np.asarray([actions.get(int(entity_id), (-1, False))[1] for entity_id in common])
        moved = eligible & success & np.isin(action, MOVEMENT_ACTIONS) & (distance > 1.0e-12)
        resource = moved & (action == int(Action.MOVE_RESOURCE))
        control = moved & np.isin(action, (int(Action.MOVE_SOCIAL), int(Action.FLEE)))
        self._accumulate_category("all", moved, distance, gain, cosine, cosine_valid)
        self._accumulate_category("resource", resource, distance, gain, cosine, cosine_valid)
        self._accumulate_category("control", control, distance, gain, cosine, cosine_valid)
        _ = step_tick  # retained explicitly to document pre/post-step timing.

    def __call__(self, simulation: Simulation, stats: StepStats | None) -> None:
        if stats is None:
            if self.initialized:
                raise RuntimeError("processing-response observer initialized twice")
            self.previous = self._capture(simulation)
            self.initialized = True
            self.trajectory.append(self._snapshot(simulation))
            return
        if not self.initialized:
            raise RuntimeError("processing-response observer received a step before initialization")
        current = self._capture(simulation)
        self._accumulate_step(simulation, current)
        self.previous = current
        if (
            simulation.tick % self.observation_period == 0
            or simulation.tick == self.horizon
        ):
            self.trajectory.append(self._snapshot(simulation))

    def summary(self) -> dict[str, float]:
        result = {key: float(value) for key, value in self.cumulative.items()}
        for category in ("all", "resource", "control"):
            count = result[f"{category}_move_count"]
            cosine_count = result[f"{category}_move_alignment_cosine_count"]
            result[f"{category}_move_mean_support_gain"] = (
                result[f"{category}_move_support_gain_sum"] / count if count else 0.0
            )
            result[f"{category}_move_positive_support_gain_fraction"] = (
                result[f"{category}_move_support_gain_positive"] / count if count else 0.0
            )
            result[f"{category}_move_mean_alignment_cosine"] = (
                result[f"{category}_move_alignment_cosine_sum"] / cosine_count
                if cosine_count
                else 0.0
            )
        return result


def build_plan(
    cfg: SimulationConfig,
    seeds: Iterable[int],
    horizon: int,
    observation_period: int,
) -> dict[str, Any]:
    _require(cfg)
    selected = parse_seeds(seeds)
    if horizon <= 0:
        raise ValueError("horizon must be positive")
    if observation_period <= 0:
        raise ValueError("observation_period must be positive")
    return {
        "schema": PLAN_SCHEMA,
        "seeds": list(selected),
        "horizon_ticks": int(horizon),
        "shared_checkpoint_tick": 0,
        "observation_period_ticks": int(observation_period),
        "trajectory_schema": TRAJECTORY_SCHEMA,
        "float32_residue_inventory_roundoff_recorded_separately": True,
        "branches": list(BRANCHES),
        "original_interventions": [],
        "reversed_interventions": [REVERSE_INTERVENTION],
        "neutral_interventions": [NEUTRAL_INTERVENTION],
        "support_orientation_reversal_preserves_resource_fields": True,
        "support_orientation_reversal_preserves_processing_cost": True,
        "neutral_support_preserves_processing_cost": True,
        "movement_reward_or_controller_added": False,
        "support_sensor_added": False,
        "entity_lineage_and_group_feedback": False,
        "named_resource_roles": False,
        "diversity_reward_or_protection": False,
        "ecological_role_labels": False,
        "pass_fail_gate": False,
    }


def _run_branch(
    checkpoint: Path,
    output: Path,
    *,
    branch: str,
    horizon: int,
    observation_period: int,
    backend: str,
) -> dict[str, Any]:
    simulation = Simulation.from_checkpoint(
        checkpoint, output, backend=backend, until_tick=horizon
    )
    genotype_before = simulation.entities.genotype.copy()
    resources_before = np.asarray(simulation.environment.resources).copy()
    residue_before = np.asarray(simulation.environment.resource_residue).copy()
    interventions: list[str] = []
    if branch == "reversed-support":
        simulation.apply_intervention(REVERSE_INTERVENTION)
        interventions.append(REVERSE_INTERVENTION)
    elif branch == "neutral-support":
        simulation.apply_intervention(NEUTRAL_INTERVENTION)
        interventions.append(NEUTRAL_INTERVENTION)
    elif branch != "original-support":
        raise ValueError(f"unknown D3-F branch {branch!r}")
    if not np.array_equal(genotype_before, simulation.entities.genotype):
        raise RuntimeError("D3-F intervention modified genotype")
    if not np.array_equal(resources_before, np.asarray(simulation.environment.resources)):
        raise RuntimeError("D3-F intervention modified resource fields")
    if not np.array_equal(residue_before, np.asarray(simulation.environment.resource_residue)):
        raise RuntimeError("D3-F intervention modified resource residue")
    observer = SpatialProcessingResponseObserver(
        horizon=horizon, observation_period=observation_period, branch=branch
    )
    final_world = simulation.run(until_tick=horizon, tick_observer=observer)
    replay = json.loads((output / "replay_provenance.json").read_text(encoding="utf-8"))
    return {
        "branch": branch,
        "output": str(output),
        "checkpoint_state_sha256": replay["checkpoint_lineage"][-1][
            "checkpoint_state_sha256"
        ],
        "interventions": interventions,
        "scientific_validity": simulation.scientific_validity(),
        "final": _snapshot(simulation, final_world),
        "response_summary": observer.summary(),
        "response_trajectory": observer.trajectory,
    }


def _pair(seed: int, branches: list[dict[str, Any]]) -> dict[str, Any]:
    by_name = {row["branch"]: row for row in branches}
    neutral = by_name["neutral-support"]["response_summary"]
    contrasts: dict[str, dict[str, float]] = {}
    keys = (
        "resource_move_mean_support_gain",
        "resource_move_positive_support_gain_fraction",
        "resource_move_mean_alignment_cosine",
        "resource_move_count",
    )
    for name in ("original-support", "reversed-support"):
        active = by_name[name]["response_summary"]
        contrasts[f"{name}-minus-neutral"] = {
            key: float(active[key] - neutral[key]) for key in keys
        }
    return {
        "seed": int(seed),
        "shared_checkpoint_state": len(
            {row["checkpoint_state_sha256"] for row in branches}
        )
        == 1,
        "branches": branches,
        "response_contrasts": contrasts,
    }


def _payload(plan: dict[str, Any], pairs: list[dict[str, Any]]) -> dict[str, Any]:
    resource_ledgers = [
        {
            "branch": branch["branch"],
            **_resource_ledger({"seed": pair["seed"], "final": branch["final"]}),
        }
        for pair in pairs
        for branch in pair["branches"]
    ]
    recycling_ledgers = [
        {
            "branch": branch["branch"],
            **recycling_ledger({"seed": pair["seed"], "final": branch["final"]}),
        }
        for pair in pairs
        for branch in pair["branches"]
    ]
    branches = [branch for pair in pairs for branch in pair["branches"]]
    active = [row for row in branches if row["branch"] != "neutral-support"]
    neutral = [row for row in branches if row["branch"] == "neutral-support"]
    audit = {
        "shared_tick0_checkpoint_in_every_triplet": all(
            pair["shared_checkpoint_state"] for pair in pairs
        ),
        "response_trajectory_complete_in_every_branch": all(
            row["response_trajectory"]
            and row["response_trajectory"][-1]["tick"] == plan["horizon_ticks"]
            for row in branches
        ),
        "resource_movement_observed_in_every_branch": all(
            row["response_summary"]["resource_move_count"] > 0.0 for row in branches
        ),
        "active_support_exposure_nonuniform_in_every_active_branch": all(
            max(row["final"]["resource_processing_support_weighted_mean"])
            - min(row["final"]["resource_processing_support_weighted_mean"])
            > 1.0e-6
            for row in active
        ),
        "neutral_support_exactly_one_in_every_neutral_branch": all(
            np.allclose(
                row["final"]["resource_processing_support_weighted_mean"],
                np.ones(4),
                atol=1.0e-12,
                rtol=0.0,
            )
            for row in neutral
        ),
        "external_resource_ledger_valid_in_every_branch": all(
            row["valid"] for row in resource_ledgers
        ),
        "external_recycling_ledger_valid_in_every_branch": all(
            row["valid"] for row in recycling_ledgers
        ),
    }
    return {
        "schema": RESULT_SCHEMA,
        "plan": plan,
        "completed_seed_count": len(pairs),
        "pairs": pairs,
        "external_resource_ledger": resource_ledgers,
        "external_recycling_ledger": recycling_ledgers,
        "audit_completeness": audit,
        "observed_response_signs": [
            {
                "seed": pair["seed"],
                "branch": branch["branch"],
                "resource_move_mean_support_gain": branch["response_summary"][
                    "resource_move_mean_support_gain"
                ],
                "resource_move_positive_support_gain_fraction": branch[
                    "response_summary"
                ]["resource_move_positive_support_gain_fraction"],
                "resource_move_mean_alignment_cosine": branch["response_summary"][
                    "resource_move_mean_alignment_cosine"
                ],
            }
            for pair in pairs
            for branch in pair["branches"]
        ],
        "recommendation": (
            "response-audit-complete-inspect-repeated-orientation-alignment"
            if all(audit.values())
            else "inspect-processing-response-audit-integrity"
        ),
        "causal_claim_scope": (
            "Support-orientation and neutralization branch differences are attributable to their registered interventions under the shared checkpoint contract. Movement alignment remains an observed mediator and is not itself a migration or specialization proof."
        ),
        "ecological_differentiation_claim": False,
        "interpretation_boundary": (
            "D3-F measures inventory-conditioned movement relative to original, reversed, and neutral processing-support surfaces without adding a support sensor, reward, or controller. Repeated orientation-aligned response is a prerequisite for later migration tests, not evidence of ecotypes, coexistence, trophic transfer, or named roles."
        ),
    }


def render_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# D3-F inventory-conditioned spatial-processing response audit",
        "",
        f"Schema: `{payload['schema']}`",
        "",
        "| Seed | Branch | Resource moves | Mean support gain | Positive gain fraction | Mean gradient cosine |",
        "|---:|---|---:|---:|---:|---:|",
    ]
    for pair in payload["pairs"]:
        for branch in pair["branches"]:
            summary = branch["response_summary"]
            lines.append(
                f"| {pair['seed']} | {branch['branch']} | "
                f"{int(summary['resource_move_count'])} | "
                f"{summary['resource_move_mean_support_gain']} | "
                f"{summary['resource_move_positive_support_gain_fraction']} | "
                f"{summary['resource_move_mean_alignment_cosine']} |"
            )
    lines += ["", "## Audit completeness", ""]
    lines += [
        f"- {key.replace('_', ' ')}: `{value}`"
        for key, value in payload["audit_completeness"].items()
    ]
    lines += [
        "",
        f"Recommendation: `{payload['recommendation']}`",
        "",
        payload["causal_claim_scope"],
        "",
        payload["interpretation_boundary"],
        "",
    ]
    return "\n".join(lines)


def execute_processing_response(
    cfg: SimulationConfig,
    seeds: Iterable[int],
    output_dir: str | Path,
    *,
    backend: str = "auto",
    until_tick: int | None = None,
    observation_period: int = 30,
    overwrite: bool = False,
) -> dict[str, Any]:
    _require(cfg)
    selected = parse_seeds(seeds)
    horizon = int(cfg.run.ticks if until_tick is None else until_tick)
    plan = build_plan(cfg, selected, horizon, observation_period)
    output = Path(output_dir)
    if output.exists() and any(output.iterdir()):
        if not overwrite:
            raise RuntimeError(f"output exists: {output}; pass --overwrite")
        shutil.rmtree(output)
    output.mkdir(parents=True, exist_ok=True)
    (output / "d3_processing_response_plan.json").write_text(
        json.dumps(plan, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    pairs: list[dict[str, Any]] = []
    for seed in selected:
        seed_dir = output / f"seed_{seed}"
        source_dir = seed_dir / "source"
        source_dir.mkdir(parents=True, exist_ok=True)
        run_cfg = replace(cfg, run=replace(cfg.run, seed=seed, ticks=horizon))
        (seed_dir / "resolved_config.json").write_text(
            json.dumps(asdict(run_cfg), ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        source = Simulation(run_cfg, source_dir, backend=backend)
        checkpoint = source.save_full_checkpoint(seed_dir / "checkpoint_00000000.sechk")
        metadata, _ = read_checkpoint_bundle(checkpoint)
        branches = [
            _run_branch(
                checkpoint,
                seed_dir / branch.replace("-", "_"),
                branch=branch,
                horizon=horizon,
                observation_period=observation_period,
                backend=backend,
            )
            for branch in BRANCHES
        ]
        if any(
            branch["checkpoint_state_sha256"] != metadata["state_sha256"]
            for branch in branches
        ):
            raise RuntimeError("D3-F replay branch did not preserve checkpoint state")
        pairs.append(_pair(seed, branches))
        partial = _payload(plan, pairs)
        (output / "d3_processing_response_results.json").write_text(
            json.dumps(partial, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    payload = _payload(plan, pairs)
    (output / "d3_processing_response_results.md").write_text(
        render_markdown(payload), encoding="utf-8"
    )
    return payload


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True)
    parser.add_argument("--seeds", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--backend", choices=("cpu", "gpu", "auto"), default="auto")
    parser.add_argument("--until-tick", type=int)
    parser.add_argument("--observation-period", type=int, default=30)
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args(argv)
    payload = execute_processing_response(
        load_config(args.config),
        parse_seeds(args.seeds),
        args.output,
        backend=args.backend,
        until_tick=args.until_tick,
        observation_period=args.observation_period,
        overwrite=args.overwrite,
    )
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
