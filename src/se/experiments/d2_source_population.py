"""D2-G source-population reconstitution and qualification experiment.

The preceding lineage-paired and temporal-mediation audits found a bounded
module-3 causal signal, but the available source checkpoints remain dominated
by one or two genetic lineages.  D2-G does not add module copies.  It builds a
fresh genotype-only founder population from preregistered donor lineages across
independent source runs, then lets ordinary world dynamics run without any
lineage-aware reward, protection, spatial reservation, or reproduction rule.

Two paired initial-condition arms are produced from the same donor checkpoints:

* ``natural-abundance-control`` preserves donor abundance proportions inside
  the selected donor set;
* ``equal-lineage-reconstitution`` downsamples unique donor individuals without
  replacement to the same count per lineage.

Both arms use the same total founder count, fresh world seed, entity IDs and
initial spatial/environmental realization.  Only inherited genotype composition
is changed at tick zero.  The burn-in checkpoint is a candidate source for a
later shared-checkpoint copy-number audit; D2-G itself never changes copy number.
"""

from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass, replace
import hashlib
import json
from pathlib import Path
from typing import Any, Iterable, Sequence

import numpy as np

from se.cfg import SimulationConfig, validate_config
from se.checkpointing import read_checkpoint_bundle
from se.differentiation.functional import expression_gates_q, Q
from se.env.niches import active_morphology_traits
from se.evolution.progress import EvolutionProgressTracker
from se.knowledge import KnowledgeSystem
from se.policy import ParametricPolicy
from se.runtime.sim import Simulation
from se.subjects.graph import CandidateSubjectGraph

PLAN_SCHEMA = "d2-source-population-plan-v1"
RESULT_SCHEMA = "d2-source-population-results-v1"
MEDIATION_ASSESSMENT_SCHEMA = "d2-lineage-mediation-assessment-v1"
MEDIATION_RESULT_SCHEMA = "d2-lineage-mediation-results-v1"
ARMS = ("natural-abundance-control", "equal-lineage-reconstitution")
DEFAULT_PANEL_SEEDS = (45001, 45002, 45003)
DEFAULT_OBSERVATION_OFFSETS = (0, 120, 300, 600)
SELECTION_RULE = (
    "cross-run-top-preintervention-lineages-by-abundance-without-response-selection-v1"
)
FOUNDER_RULE = "unique-genotype-only-donors-without-replacement-v1"


@dataclass(frozen=True)
class DonorLineage:
    run_name: str
    phase: str
    checkpoint_tick: int
    checkpoint_path: str
    source_lineage_id: int
    source_members: int
    source_abundance_rank: int
    panel_lineage_id: int


@dataclass(frozen=True)
class FounderAllocation:
    panel_lineage_id: int
    founder_count: int


@dataclass(frozen=True)
class SourcePopulationPanel:
    panel_name: str
    phase: str
    panel_seed: int
    total_founders: int
    equal_founders_per_lineage: int
    donors: tuple[DonorLineage, ...]
    natural_allocations: tuple[FounderAllocation, ...]
    equal_allocations: tuple[FounderAllocation, ...]


@dataclass(frozen=True)
class SourcePopulationPlan:
    schema: str
    source_assessment_schema: str
    source_assessment_sha256: str | None
    source_result_schema: str
    source_result_sha256: str | None
    candidate_module_indices: tuple[int, ...]
    source_endpoint_reproduced: bool
    transient_causal_chain_supported: bool
    panel_seeds: tuple[int, ...]
    phases: tuple[str, ...]
    lineages_per_run: int
    max_founders_per_lineage: int
    min_lineage_members: int
    burn_in_ticks: int
    observation_offsets: tuple[int, ...]
    panels: tuple[SourcePopulationPanel, ...]
    arms: tuple[str, ...] = ARMS
    lineage_selection_rule: str = SELECTION_RULE
    founder_sampling_rule: str = FOUNDER_RULE
    unique_donors_without_replacement: bool = True
    genotype_only_transfer: bool = True
    donor_physiology_reset: bool = True
    donor_knowledge_reset: bool = True
    donor_social_state_reset: bool = True
    random_spatial_assignment: bool = True
    ongoing_lineage_protection: bool = False
    lineage_aware_world_rules: bool = False
    module_copy_number_changed: bool = False
    routing_vocabulary_changed: bool = False
    outcome_conditioned_lineage_selection: bool = False


def _sha256_file(path: str | Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _normalize_positive(values: Iterable[int], *, name: str) -> tuple[int, ...]:
    result = tuple(sorted({int(value) for value in values}))
    if not result or result[0] <= 0:
        raise ValueError(f"{name} must contain positive integers")
    return result


def _normalize_offsets(values: Iterable[int], burn_in_ticks: int) -> tuple[int, ...]:
    offsets = tuple(sorted({int(value) for value in values}))
    if not offsets or offsets[0] < 0:
        raise ValueError("observation offsets must be non-negative")
    if 0 not in offsets:
        offsets = (0, *offsets)
    if int(burn_in_ticks) not in offsets:
        offsets = (*offsets, int(burn_in_ticks))
    offsets = tuple(sorted(set(offsets)))
    if offsets[-1] > int(burn_in_ticks):
        raise ValueError("observation offsets cannot exceed burn-in ticks")
    return offsets


def _panel_lineage_id(run_name: str, source_lineage_id: int) -> int:
    digest = hashlib.sha256(
        f"d2g|{run_name}|{int(source_lineage_id)}".encode("utf-8")
    ).digest()
    value = int.from_bytes(digest[:8], "big") & ((1 << 63) - 1)
    return value or 1


def _allocate_proportional(
    total: int,
    donors: Sequence[DonorLineage],
) -> tuple[FounderAllocation, ...]:
    if total < len(donors):
        raise ValueError("founder total is smaller than donor-lineage count")
    weights = np.asarray([item.source_members for item in donors], dtype=np.float64)
    caps = np.asarray([item.source_members for item in donors], dtype=np.int64)
    raw = weights / weights.sum() * int(total)
    counts = np.floor(raw).astype(np.int64)
    counts = np.maximum(counts, 1)
    counts = np.minimum(counts, caps)
    while int(counts.sum()) < int(total):
        candidates = np.flatnonzero(counts < caps)
        if not candidates.size:
            raise ValueError("donor capacities cannot fill the requested founder total")
        order = sorted(
            candidates.tolist(),
            key=lambda idx: (
                -(raw[idx] - np.floor(raw[idx])),
                donors[idx].run_name,
                donors[idx].source_lineage_id,
            ),
        )
        for idx in order:
            if int(counts.sum()) >= int(total):
                break
            counts[idx] += 1
    while int(counts.sum()) > int(total):
        candidates = np.flatnonzero(counts > 1)
        if not candidates.size:
            raise ValueError("cannot reduce proportional founder allocation")
        order = sorted(
            candidates.tolist(),
            key=lambda idx: (
                raw[idx] - np.floor(raw[idx]),
                donors[idx].run_name,
                donors[idx].source_lineage_id,
            ),
        )
        for idx in order:
            if int(counts.sum()) <= int(total):
                break
            counts[idx] -= 1
    return tuple(
        FounderAllocation(item.panel_lineage_id, int(count))
        for item, count in zip(donors, counts.tolist())
    )


def build_source_population_plan(
    assessment: dict[str, Any],
    mediation_results: dict[str, Any],
    *,
    panel_seeds: Iterable[int] = DEFAULT_PANEL_SEEDS,
    lineages_per_run: int = 2,
    max_founders_per_lineage: int = 48,
    min_lineage_members: int = 8,
    burn_in_ticks: int = 600,
    observation_offsets: Iterable[int] = DEFAULT_OBSERVATION_OFFSETS,
    source_assessment_sha256: str | None = None,
    source_result_sha256: str | None = None,
) -> SourcePopulationPlan:
    if assessment.get("schema") != MEDIATION_ASSESSMENT_SCHEMA:
        raise ValueError(
            f"unsupported mediation assessment: {assessment.get('schema')!r}"
        )
    if mediation_results.get("schema") != MEDIATION_RESULT_SCHEMA:
        raise ValueError(
            f"unsupported mediation results: {mediation_results.get('schema')!r}"
        )
    if "redesign-source-population" not in str(assessment.get("recommendation", "")):
        raise ValueError("assessment does not recommend source-population redesign")
    lineages_per_run = int(lineages_per_run)
    if lineages_per_run <= 0:
        raise ValueError("lineages_per_run must be positive")
    max_founders_per_lineage = int(max_founders_per_lineage)
    min_lineage_members = int(min_lineage_members)
    burn_in_ticks = int(burn_in_ticks)
    if max_founders_per_lineage < min_lineage_members:
        raise ValueError("max founders per lineage is below the lineage-member floor")
    if burn_in_ticks <= 0:
        raise ValueError("burn-in ticks must be positive")
    seeds = _normalize_positive(panel_seeds, name="panel seeds")
    offsets = _normalize_offsets(observation_offsets, burn_in_ticks)

    candidate_modules: list[int] = []
    endpoint_reproduced = True
    transient_chain_supported = False
    for name, module in assessment.get("modules", {}).items():
        temporal = module.get("temporal_mediation", {})
        if temporal.get("demographic_conversion_after_energy"):
            candidate_modules.append(int(name.split("_")[-1]))
            transient_chain_supported = True
        endpoint_reproduced = endpoint_reproduced and bool(
            module.get("source_expectation_reproduced_at_final_offset", False)
        )
    if not candidate_modules:
        raise ValueError("assessment contains no module with demographic conversion")

    checkpoints = mediation_results.get("plan", {}).get("checkpoints", ())
    if not checkpoints:
        raise ValueError("mediation results contain no source checkpoints")
    by_phase: dict[str, list[dict[str, Any]]] = {}
    for item in checkpoints:
        by_phase.setdefault(str(item["phase"]), []).append(item)
    panels: list[SourcePopulationPanel] = []
    for phase, phase_checkpoints in sorted(by_phase.items()):
        donors: list[DonorLineage] = []
        seen_runs: set[str] = set()
        for checkpoint in sorted(phase_checkpoints, key=lambda row: str(row["run_name"])):
            run_name = str(checkpoint["run_name"])
            if run_name in seen_runs:
                raise ValueError(f"phase {phase!r} contains duplicate run {run_name!r}")
            seen_runs.add(run_name)
            selected = sorted(
                checkpoint.get("lineages", ()),
                key=lambda row: (int(row["abundance_rank"]), int(row["lineage_id"])),
            )[:lineages_per_run]
            if len(selected) != lineages_per_run:
                raise ValueError(
                    f"checkpoint {run_name}/{phase} lacks {lineages_per_run} donor lineages"
                )
            for lineage in selected:
                members = int(lineage["members"])
                if members < min_lineage_members:
                    raise ValueError(
                        f"donor lineage {run_name}/{lineage['lineage_id']} has only {members} members"
                    )
                donors.append(
                    DonorLineage(
                        run_name=run_name,
                        phase=phase,
                        checkpoint_tick=int(checkpoint["checkpoint_tick"]),
                        checkpoint_path=str(checkpoint["checkpoint_path"]),
                        source_lineage_id=int(lineage["lineage_id"]),
                        source_members=members,
                        source_abundance_rank=int(lineage["abundance_rank"]),
                        panel_lineage_id=_panel_lineage_id(
                            run_name, int(lineage["lineage_id"])
                        ),
                    )
                )
        if len(seen_runs) < 2:
            raise ValueError("each source panel phase requires at least two source runs")
        equal_count = min(
            max_founders_per_lineage,
            min(item.source_members for item in donors),
        )
        if equal_count < min_lineage_members:
            raise ValueError("selected donor set cannot meet the founder floor")
        total = equal_count * len(donors)
        natural = _allocate_proportional(total, donors)
        equal = tuple(
            FounderAllocation(item.panel_lineage_id, equal_count) for item in donors
        )
        for seed in seeds:
            panels.append(
                SourcePopulationPanel(
                    panel_name=f"{phase}_seed_{seed}",
                    phase=phase,
                    panel_seed=seed,
                    total_founders=total,
                    equal_founders_per_lineage=equal_count,
                    donors=tuple(donors),
                    natural_allocations=natural,
                    equal_allocations=equal,
                )
            )
    phases = tuple(sorted(by_phase))
    if len(phases) < 2:
        raise ValueError("source-population redesign requires at least two source phases")
    return SourcePopulationPlan(
        schema=PLAN_SCHEMA,
        source_assessment_schema=str(assessment["schema"]),
        source_assessment_sha256=source_assessment_sha256,
        source_result_schema=str(mediation_results["schema"]),
        source_result_sha256=source_result_sha256,
        candidate_module_indices=tuple(sorted(set(candidate_modules))),
        source_endpoint_reproduced=endpoint_reproduced,
        transient_causal_chain_supported=transient_chain_supported,
        panel_seeds=seeds,
        phases=phases,
        lineages_per_run=lineages_per_run,
        max_founders_per_lineage=max_founders_per_lineage,
        min_lineage_members=min_lineage_members,
        burn_in_ticks=burn_in_ticks,
        observation_offsets=offsets,
        panels=tuple(panels),
    )


def _load_plan(path: str | Path) -> SourcePopulationPlan:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if payload.get("schema") != PLAN_SCHEMA:
        raise ValueError(f"unsupported source-population plan: {payload.get('schema')!r}")
    panels: list[SourcePopulationPanel] = []
    for item in payload.get("panels", ()):
        donors = tuple(DonorLineage(**row) for row in item.get("donors", ()))
        natural = tuple(
            FounderAllocation(**row) for row in item.get("natural_allocations", ())
        )
        equal = tuple(
            FounderAllocation(**row) for row in item.get("equal_allocations", ())
        )
        panels.append(
            SourcePopulationPanel(
                **{
                    **item,
                    "donors": donors,
                    "natural_allocations": natural,
                    "equal_allocations": equal,
                }
            )
        )
    if not panels:
        raise ValueError("source-population plan contains no panels")
    return SourcePopulationPlan(
        **{
            **payload,
            "candidate_module_indices": tuple(payload["candidate_module_indices"]),
            "panel_seeds": tuple(payload["panel_seeds"]),
            "phases": tuple(payload["phases"]),
            "observation_offsets": tuple(payload["observation_offsets"]),
            "panels": tuple(panels),
            "arms": tuple(payload.get("arms", ARMS)),
        }
    )


def _stable_rank(seed: int, namespace: str, value: int) -> int:
    return int.from_bytes(
        hashlib.blake2b(
            f"{int(seed)}|{namespace}|{int(value)}".encode("utf-8"),
            digest_size=8,
        ).digest(),
        "big",
    )


def _config_signature(cfg: SimulationConfig) -> dict[str, Any]:
    payload = asdict(cfg)
    run = payload["run"]
    for key in (
        "seed",
        "ticks",
        "metrics_period",
        "checkpoint_period",
        "checkpoint_ticks",
        "full_checkpoint_enabled",
        "evolution_evaluation_period",
    ):
        run.pop(key, None)
    payload["world"].pop("initial_entities", None)
    return payload


def _allocation_map(panel: SourcePopulationPanel, arm: str) -> dict[int, int]:
    rows = (
        panel.natural_allocations
        if arm == "natural-abundance-control"
        else panel.equal_allocations
    )
    return {int(item.panel_lineage_id): int(item.founder_count) for item in rows}


def _founder_records(
    panel: SourcePopulationPanel,
    arm: str,
    cache: dict[str, tuple[dict[str, Any], dict[str, Any]]],
) -> tuple[SimulationConfig, list[dict[str, Any]]]:
    allocation = _allocation_map(panel, arm)
    template_cfg: SimulationConfig | None = None
    signature: dict[str, Any] | None = None
    records: list[dict[str, Any]] = []
    for donor in panel.donors:
        if donor.checkpoint_path not in cache:
            cache[donor.checkpoint_path] = read_checkpoint_bundle(
                donor.checkpoint_path
            )
        metadata, bundle = cache[donor.checkpoint_path]
        if int(metadata.get("tick", -1)) != int(donor.checkpoint_tick):
            raise ValueError(
                f"donor checkpoint tick drifted for {donor.run_name}: "
                f"plan={donor.checkpoint_tick}, file={metadata.get('tick')}"
            )
        cfg: SimulationConfig = bundle["config"]
        current_signature = _config_signature(cfg)
        if signature is None:
            template_cfg = cfg
            signature = current_signature
        elif current_signature != signature:
            raise ValueError("donor checkpoints do not share one structural configuration")
        entities = bundle["simulation"]["entities"]
        rows = np.flatnonzero(
            np.asarray(entities.alive, dtype=bool)
            & (
                np.asarray(entities.lineage_id, dtype=np.uint64)
                == np.uint64(donor.source_lineage_id)
            )
        ).astype(np.int32)
        if int(rows.size) != int(donor.source_members):
            raise ValueError(
                f"donor lineage membership drifted for {donor.run_name}/"
                f"{donor.source_lineage_id}: plan={donor.source_members}, "
                f"file={rows.size}"
            )
        requested = allocation[donor.panel_lineage_id]
        if rows.size < requested:
            raise ValueError(
                f"donor lineage {donor.run_name}/{donor.source_lineage_id} has "
                f"{rows.size} living rows; plan requires {requested}"
            )
        ordered = sorted(
            rows.tolist(),
            key=lambda row: _stable_rank(
                panel.panel_seed,
                f"donor|{donor.run_name}|{donor.source_lineage_id}",
                int(entities.entity_id[row]),
            ),
        )[:requested]
        for row in ordered:
            records.append(
                {
                    "genotype": np.asarray(entities.genotype[row], dtype=np.float32).copy(),
                    "panel_lineage_id": donor.panel_lineage_id,
                    "source_run_name": donor.run_name,
                    "source_lineage_id": donor.source_lineage_id,
                    "source_entity_id": int(entities.entity_id[row]),
                    "genotype_sha256": hashlib.sha256(
                        np.asarray(entities.genotype[row], dtype=np.float32).tobytes()
                    ).hexdigest(),
                }
            )
    if template_cfg is None or len(records) != panel.total_founders:
        raise RuntimeError("founder record construction is incomplete")
    return template_cfg, records


def _install_founder_population(
    simulation: Simulation,
    records: Sequence[dict[str, Any]],
    *,
    panel: SourcePopulationPanel,
    arm: str,
) -> list[dict[str, Any]]:
    if simulation.tick != 0:
        raise ValueError("founder population can only be installed at tick zero")
    active = np.flatnonzero(simulation.entities.alive).astype(np.int32)
    if active.size != len(records):
        raise ValueError("founder records do not match configured initial population")
    ordered = sorted(
        records,
        key=lambda row: int.from_bytes(
            hashlib.blake2b(
                (
                    f"{panel.panel_seed}|assignment|{row['source_run_name']}|"
                    f"{row['source_lineage_id']}|{row['source_entity_id']}"
                ).encode("utf-8"),
                digest_size=8,
            ).digest(),
            "big",
        ),
    )
    simulation.entities.genotype[active] = np.stack(
        [row["genotype"] for row in ordered]
    ).astype(np.float32)
    simulation.entities.lineage_id[active] = np.asarray(
        [row["panel_lineage_id"] for row in ordered], dtype=np.uint64
    )
    simulation.entities.refresh_capacity_phenotype(active)
    all_slots = np.arange(simulation.cfg.world.max_entities, dtype=np.int32)
    simulation.social.set_effective_capacities(
        all_slots, simulation.entities.relation_capacity
    )

    simulation.knowledge.close()
    simulation.subjects = CandidateSubjectGraph(simulation.cfg.world.max_entities)
    simulation.entities.primary_subject_id.fill(0)
    simulation.entities.lineage_subject_id.fill(0)
    bodies, lineages = simulation.subjects.register_bodies(
        active, simulation.entities.lineage_id, tick=0
    )
    simulation.entities.primary_subject_id[active] = bodies
    simulation.entities.lineage_subject_id[active] = lineages
    simulation.knowledge = KnowledgeSystem(
        simulation.cfg,
        simulation.output_dir,
        initial_entity_ids=simulation.entities.entity_id[active],
        initial_subject_ids=simulation.entities.primary_subject_id[active],
        initial_knowledge_capacities=simulation.entities.knowledge_capacity_bytes[active],
    )
    morphology_indices, morphology_names = active_morphology_traits(simulation.cfg)
    simulation.evolution_progress = EvolutionProgressTracker(
        simulation.output_dir,
        period=simulation.cfg.run.evolution_evaluation_period,
        run_seed=simulation.cfg.run.seed,
        temperature=simulation.cfg.policy.temperature,
        alive=simulation.entities.alive,
        stable_ids=simulation.entities.entity_id,
        genotype=simulation.entities.genotype,
        long_run_diagnostics_enabled=simulation.cfg.run.long_run_diagnostics_enabled,
        long_run_diagnostics_schema=simulation.cfg.run.long_run_diagnostics_schema,
        morphology_trait_indices=morphology_indices,
        morphology_trait_names=morphology_names,
    )
    simulation.entity_device_version += 1
    if simulation.gpu_runtime is not None:
        simulation.gpu_runtime.sync_entity_from_host(
            simulation.entities,
            simulation.social,
            simulation.entity_device_version,
        )
    founder_manifest = [
        {
            "founder_slot": int(slot),
            "founder_entity_id": int(simulation.entities.entity_id[slot]),
            "panel_lineage_id": int(row["panel_lineage_id"]),
            "source_run_name": str(row["source_run_name"]),
            "source_lineage_id": int(row["source_lineage_id"]),
            "source_entity_id": int(row["source_entity_id"]),
            "genotype_sha256": str(row["genotype_sha256"]),
        }
        for slot, row in zip(active.tolist(), ordered)
    ]
    manifest_sha256 = hashlib.sha256(
        json.dumps(
            founder_manifest, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
    ).hexdigest()
    simulation.intervention_history.append(
        {
            "tick": 0,
            "type": "install-genotype-only-source-population",
            "kind": "initial-condition",
            "arm": arm,
            "panel_name": panel.panel_name,
            "founder_count": len(records),
            "donor_lineage_count": len(panel.donors),
            "unique_donors_without_replacement": True,
            "physiology_reset": True,
            "knowledge_reset": True,
            "social_state_reset": True,
            "ongoing_lineage_protection": False,
            "module_copy_number_changed": False,
            "founder_manifest_sha256": manifest_sha256,
        }
    )
    return founder_manifest


class _SourcePopulationObserver:
    def __init__(
        self,
        *,
        offsets: Sequence[int],
        panel_lineage_ids: Sequence[int],
        min_lineage_members: int,
        candidate_modules: Sequence[int],
    ) -> None:
        self.offsets = set(int(value) for value in offsets)
        self.panel_lineage_ids = tuple(int(value) for value in panel_lineage_ids)
        self.min_lineage_members = int(min_lineage_members)
        self.candidate_modules = tuple(int(value) for value in candidate_modules)
        self.snapshots: list[dict[str, Any]] = []

    def __call__(self, simulation: Simulation, _stats: Any) -> None:
        if int(simulation.tick) not in self.offsets:
            return
        active = np.flatnonzero(simulation.entities.alive).astype(np.int32)
        lineage_ids = simulation.entities.lineage_id[active].astype(np.uint64, copy=False)
        unique, counts = np.unique(lineage_ids, return_counts=True)
        count_map = {int(key): int(value) for key, value in zip(unique, counts)}
        total = int(active.size)
        probabilities = counts.astype(np.float64) / max(total, 1)
        effective = float(1.0 / np.sum(probabilities * probabilities)) if total else 0.0
        dominant = float(counts.max() / total) if total else 1.0
        panel_counts = [count_map.get(lineage, 0) for lineage in self.panel_lineage_ids]

        expression: dict[str, Any] = {}
        if active.size and self.candidate_modules:
            gates = expression_gates_q(
                simulation.entities.genotype[active],
                simulation.cfg,
                gene_start=ParametricPolicy.functional_module_gene_start(
                    simulation.cfg
                ),
            ).astype(np.float64) / Q
            for module_index in self.candidate_modules:
                lineage_rows = []
                expressed_lineages = 0
                for lineage in self.panel_lineage_ids:
                    mask = lineage_ids == np.uint64(lineage)
                    values = gates[mask, module_index]
                    mean = float(values.mean()) if values.size else 0.0
                    expressed_fraction = (
                        float(np.count_nonzero(values > 0.0) / values.size)
                        if values.size
                        else 0.0
                    )
                    members = int(values.size)
                    if members >= self.min_lineage_members and mean > 0.0:
                        expressed_lineages += 1
                    lineage_rows.append(
                        {
                            "panel_lineage_id": lineage,
                            "members": members,
                            "mean_expression": mean,
                            "expressed_fraction": expressed_fraction,
                        }
                    )
                expression[f"module_{module_index}"] = {
                    "expressed_eligible_lineage_count": expressed_lineages,
                    "lineages": lineage_rows,
                }
        self.snapshots.append(
            {
                "offset_ticks": int(simulation.tick),
                "alive": total,
                "lineage_count": int(unique.size),
                "effective_lineages": effective,
                "dominant_lineage_fraction": dominant,
                "eligible_panel_lineage_count": int(
                    sum(value >= self.min_lineage_members for value in panel_counts)
                ),
                "panel_lineage_counts": [
                    {"panel_lineage_id": lineage, "members": count}
                    for lineage, count in zip(self.panel_lineage_ids, panel_counts)
                ],
                "candidate_module_expression": expression,
            }
        )


def execute_source_population_plan(
    plan: SourcePopulationPlan,
    output_dir: str | Path,
    *,
    backend: str = "auto",
    gpu_semantics_mode: str | None = None,
) -> dict[str, Any]:
    if tuple(plan.arms) != ARMS:
        raise ValueError(f"unsupported source-population arms: {plan.arms!r}")
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    cache: dict[str, tuple[dict[str, Any], dict[str, Any]]] = {}
    panel_rows: list[dict[str, Any]] = []
    for panel in plan.panels:
        arm_rows: dict[str, Any] = {}
        for arm in ARMS:
            template_cfg, records = _founder_records(panel, arm, cache)
            run_cfg = replace(
                template_cfg.run,
                seed=int(panel.panel_seed),
                ticks=int(plan.burn_in_ticks),
                metrics_period=min(
                    int(template_cfg.run.metrics_period), int(plan.burn_in_ticks)
                ),
                checkpoint_period=int(plan.burn_in_ticks) + 1,
                checkpoint_ticks=(int(plan.burn_in_ticks),),
                full_checkpoint_enabled=True,
                evolution_evaluation_period=min(
                    int(template_cfg.run.evolution_evaluation_period),
                    int(plan.burn_in_ticks),
                ),
                gpu_semantics_mode=(
                    str(gpu_semantics_mode)
                    if gpu_semantics_mode is not None
                    else template_cfg.run.gpu_semantics_mode
                ),
            )
            cfg = replace(
                template_cfg,
                run=run_cfg,
                world=replace(
                    template_cfg.world,
                    initial_entities=int(panel.total_founders),
                ),
            )
            if panel.total_founders > cfg.world.max_entities:
                raise ValueError("founder panel exceeds world max_entities")
            validate_config(cfg)
            arm_dir = output / panel.panel_name / arm
            simulation = Simulation(cfg, arm_dir, backend=backend)
            founder_manifest = _install_founder_population(
                simulation, records, panel=panel, arm=arm
            )
            founder_manifest_sha256 = hashlib.sha256(
                json.dumps(
                    founder_manifest, sort_keys=True, separators=(",", ":")
                ).encode("utf-8")
            ).hexdigest()
            initial_checkpoint = simulation.save_full_checkpoint(
                arm_dir / "founder_checkpoint_00000000.sechk"
            )
            observer = _SourcePopulationObserver(
                offsets=plan.observation_offsets,
                panel_lineage_ids=[item.panel_lineage_id for item in panel.donors],
                min_lineage_members=plan.min_lineage_members,
                candidate_modules=plan.candidate_module_indices,
            )
            summary = simulation.run(
                until_tick=plan.burn_in_ticks,
                tick_observer=observer,
            )
            final_checkpoint = arm_dir / f"checkpoint_{plan.burn_in_ticks:08d}.sechk"
            if not final_checkpoint.is_file():
                raise RuntimeError("burn-in final checkpoint was not written")
            if [row["offset_ticks"] for row in observer.snapshots] != list(
                plan.observation_offsets
            ):
                raise RuntimeError("source-population observation trajectory is incomplete")
            arm_rows[arm] = {
                "founder_allocations": [
                    asdict(item)
                    for item in (
                        panel.natural_allocations
                        if arm == "natural-abundance-control"
                        else panel.equal_allocations
                    )
                ],
                "founder_manifest": founder_manifest,
                "founder_manifest_sha256": founder_manifest_sha256,
                "initial_checkpoint": str(initial_checkpoint.resolve()),
                "final_checkpoint": str(final_checkpoint.resolve()),
                "trajectory": observer.snapshots,
                "summary": summary,
                "scientific_validity": simulation.scientific_validity(),
                "intervention_history": simulation.intervention_history,
            }
        panel_rows.append(
            {
                "panel_name": panel.panel_name,
                "phase": panel.phase,
                "panel_seed": panel.panel_seed,
                "total_founders": panel.total_founders,
                "donors": [asdict(item) for item in panel.donors],
                "arms": arm_rows,
            }
        )
    return {
        "schema": RESULT_SCHEMA,
        "plan": asdict(plan),
        "backend": backend,
        "gpu_semantics_mode": gpu_semantics_mode,
        "executed_panel_count": len(panel_rows),
        "executed_arm_count": len(panel_rows) * len(ARMS),
        "panels": panel_rows,
        "interpretation_boundary": (
            "Equal founder counts are an explicit initial-condition intervention, not "
            "an evolved equilibrium and not ongoing diversity protection. Qualification "
            "requires ordinary unprotected burn-in to retain multiple expressed lineages. "
            "No module copy number is changed in this experiment."
        ),
    }


def render_plan_markdown(plan: SourcePopulationPlan) -> str:
    lines = [
        "# D2-G source-population reconstitution plan",
        "",
        f"Schema: `{plan.schema}`",
        f"Candidate modules retained for later retest: `{', '.join(map(str, plan.candidate_module_indices))}`",
        f"Source endpoint reproduced: `{plan.source_endpoint_reproduced}`",
        f"Transient causal chain supported: `{plan.transient_causal_chain_supported}`",
        f"Burn-in: `{plan.burn_in_ticks}` ticks",
        f"Observation offsets: `{', '.join(map(str, plan.observation_offsets))}`",
        "",
        "## Design boundary",
        "",
        "- Genotypes only are transferred from unique living donors without replacement.",
        "- Physiology, age, knowledge, social state and spatial position are reset.",
        "- Equal-lineage and natural-abundance arms use the same total founder count.",
        "- No lineage-aware reward, survival protection, spatial reservation or reproduction rule is added.",
        "- Module copy number and routing vocabulary remain unchanged.",
        "",
        "| Panel | Phase | Seed | Donor lineages | Founders | Equal per lineage |",
        "|---|---|---:|---:|---:|---:|",
    ]
    for panel in plan.panels:
        lines.append(
            f"| `{panel.panel_name}` | {panel.phase} | {panel.panel_seed} | "
            f"{len(panel.donors)} | {panel.total_founders} | "
            f"{panel.equal_founders_per_lineage} |"
        )
    lines.extend(
        [
            "",
            "The natural-abundance arm is a paired composition control. The equal-lineage "
            "arm is only a candidate source population after unprotected burn-in; tick-zero "
            "equalization itself is not evidence of stable diversity.",
            "",
        ]
    )
    return "\n".join(lines)


def render_results_markdown(results: dict[str, Any]) -> str:
    lines = [
        "# D2-G source-population burn-in results",
        "",
        f"Schema: `{results['schema']}`",
        f"Executed panels: `{results['executed_panel_count']}`",
        f"Executed arms: `{results['executed_arm_count']}`",
        "",
        "| Panel | Arm | Final effective lineages | Final dominant share | Eligible panel lineages |",
        "|---|---|---:|---:|---:|",
    ]
    final_offset = int(results["plan"]["burn_in_ticks"])
    for panel in results["panels"]:
        for arm_name, arm in panel["arms"].items():
            final = next(
                row
                for row in arm["trajectory"]
                if int(row["offset_ticks"]) == final_offset
            )
            lines.append(
                f"| `{panel['panel_name']}` | `{arm_name}` | "
                f"{final['effective_lineages']:.4f} | "
                f"{final['dominant_lineage_fraction']:.4f} | "
                f"{final['eligible_panel_lineage_count']} |"
            )
    lines.extend(["", results["interpretation_boundary"], ""])
    return "\n".join(lines)


def _write_plan(plan: SourcePopulationPlan, output: Path) -> None:
    output.mkdir(parents=True, exist_ok=True)
    (output / "d2_source_population_plan.json").write_text(
        json.dumps(asdict(plan), ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (output / "d2_source_population_plan.md").write_text(
        render_plan_markdown(plan), encoding="utf-8"
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Build or execute a D2-G source-population reconstitution plan"
    )
    parser.add_argument("--assessment")
    parser.add_argument("--mediation-results")
    parser.add_argument("--plan")
    parser.add_argument("--output", required=True)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--backend", default="auto", choices=("cpu", "gpu", "auto"))
    parser.add_argument("--gpu-semantics-mode")
    parser.add_argument("--panel-seeds", default=",".join(map(str, DEFAULT_PANEL_SEEDS)))
    parser.add_argument("--lineages-per-run", type=int, default=2)
    parser.add_argument("--max-founders-per-lineage", type=int, default=48)
    parser.add_argument("--min-lineage-members", type=int, default=8)
    parser.add_argument("--burn-in-ticks", type=int, default=600)
    parser.add_argument(
        "--observation-offsets",
        default=",".join(map(str, DEFAULT_OBSERVATION_OFFSETS)),
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    output = Path(args.output)
    if args.plan:
        plan = _load_plan(args.plan)
    else:
        if not args.assessment or not args.mediation_results:
            raise ValueError(
                "--assessment and --mediation-results are required when --plan is absent"
            )
        assessment_path = Path(args.assessment)
        results_path = Path(args.mediation_results)
        assessment = json.loads(assessment_path.read_text(encoding="utf-8"))
        results = json.loads(results_path.read_text(encoding="utf-8"))
        plan = build_source_population_plan(
            assessment,
            results,
            panel_seeds=(int(value) for value in args.panel_seeds.split(",")),
            lineages_per_run=args.lineages_per_run,
            max_founders_per_lineage=args.max_founders_per_lineage,
            min_lineage_members=args.min_lineage_members,
            burn_in_ticks=args.burn_in_ticks,
            observation_offsets=(
                int(value) for value in args.observation_offsets.split(",")
            ),
            source_assessment_sha256=_sha256_file(assessment_path),
            source_result_sha256=_sha256_file(results_path),
        )
    _write_plan(plan, output)
    payload: dict[str, Any] = {
        "passed": True,
        "plan": str((output / "d2_source_population_plan.json").resolve()),
        "panel_count": len(plan.panels),
    }
    if args.execute:
        results = execute_source_population_plan(
            plan,
            output / "execution",
            backend=args.backend,
            gpu_semantics_mode=args.gpu_semantics_mode,
        )
        result_path = output / "d2_source_population_results.json"
        result_path.write_text(
            json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        (output / "d2_source_population_results.md").write_text(
            render_results_markdown(results), encoding="utf-8"
        )
        payload["results"] = str(result_path.resolve())
        payload["executed_arm_count"] = results["executed_arm_count"]
    print(json.dumps(payload))


if __name__ == "__main__":
    main()
