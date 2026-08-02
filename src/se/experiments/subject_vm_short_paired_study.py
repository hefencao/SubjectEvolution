"""Short no-retention paired data study for Subject VM Stage 3C-8.

This experiment intentionally uses one fixed, role-neutral bootstrap graph to
make the Stage-3C pipeline reachable without waiting for topology evolution.
The graph is an engineering shaping aid, not an evolved result or a universal
attention model.  Every guarded live write must roll back before the final
checkpoint, and all scientific interpretation remains outside this runner.
"""
from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass, replace
import hashlib
import json
from pathlib import Path
import shutil
from typing import Any, Iterable

import numpy as np

from .. import __version__
from ..analysis.subject_vm_component_reproducibility import (
    assess_component_reproducibility,
)
from ..analysis.subject_vm_paired_evaluation import build_plan, run_plan
from ..analysis.subject_vm_paired_evidence import assess_exports
from ..analysis.subject_vm_stage3c10_diagnostics import assess_stage3c10_diagnostics
from ..cfg import load_config
from ..checkpointing import read_checkpoint_bundle
from ..runtime.sim import Simulation
from ..subject_vm import (
    LOCAL_ELIGIBILITY_FLAG,
    SUBJECT_VM_STAGE3C5_SCHEMA,
)
from ..subject_vm.activation import OP_LINEAR
from ..subject_vm.storage import ACTIVATION_PHASE_MASK

SHORT_PAIRED_STUDY_SCHEMA = "se-subject-vm-short-paired-study-v1"
BOOTSTRAP_GRAPH_PROFILE_SCHEMA = "se-subject-vm-fixed-bootstrap-graph-v1"
BOOTSTRAP_LINEAGE_SCHEMA = "se-subject-vm-bootstrap-lineage-v1"

# The bootstrap occupies exactly eight nodes and one delayed edge.  Token
# control ports follow the frozen Stage-3B/3C contracts.  The four fact weights
# are role-neutral objective coordinates chosen only to make short smoke
# trajectories likely to contain non-zero contrasts.
_BOOTSTRAP_TRACE_PORTS = (-1, 31, 0, 1, 2, 5, 6, 23)
_BOOTSTRAP_TRACE_GATES = (0.0, 1.0, 1.0, 1.0, 1.0, 0.5, 0.25, 1.0)
_BOOTSTRAP_TARGET_FAMILY_PORTS = {
    "node_bias": 23,
    "node_input_gate": 24,
    "node_output_gate": 25,
}


@dataclass(frozen=True)
class ShortPairedStudyParameters:
    seeds: tuple[int, ...]
    source_ticks: int = 2
    horizon_ticks: int = 5
    bootstrap_subjects: int = 16
    backend: str = "auto"
    rollback_after_ticks: int | None = None
    bootstrap_target_family: str = "node_bias"

    def validate(self) -> None:
        if len(self.seeds) < 3:
            raise ValueError("short paired study requires at least three independent seeds")
        if len(set(self.seeds)) != len(self.seeds):
            raise ValueError("short paired study seeds must be unique")
        if any(int(seed) < 0 for seed in self.seeds):
            raise ValueError("short paired study seeds must be non-negative")
        if not 0 <= int(self.source_ticks) <= 16:
            raise ValueError("source_ticks must be between 0 and 16")
        if not 3 <= int(self.horizon_ticks) <= 16:
            raise ValueError("horizon_ticks must be between 3 and 16")
        if not 1 <= int(self.bootstrap_subjects) <= 64:
            raise ValueError("bootstrap_subjects must be between 1 and 64")
        if self.backend not in {"auto", "cpu"}:
            raise ValueError(
                "Stage-3C short paired study currently supports auto or explicit CPU"
            )
        if self.rollback_after_ticks is not None and int(
            self.rollback_after_ticks
        ) < 1:
            raise ValueError("rollback_after_ticks must be positive when provided")
        if self.bootstrap_target_family not in _BOOTSTRAP_TARGET_FAMILY_PORTS:
            raise ValueError(
                "bootstrap_target_family must be node_bias, node_input_gate, or node_output_gate"
            )


def _canonical_sha256(payload: Any) -> str:
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _sha256_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def bootstrap_profile(*, target_family: str = "node_bias") -> dict[str, Any]:
    if target_family not in _BOOTSTRAP_TARGET_FAMILY_PORTS:
        raise ValueError("unsupported fixed bootstrap target family")
    target_port = int(_BOOTSTRAP_TARGET_FAMILY_PORTS[target_family])
    payload = {
        "schema": BOOTSTRAP_GRAPH_PROFILE_SCHEMA,
        "classification": "fixed-cognition-bootstrap-for-short-data-generation",
        "evolved_topology": False,
        "universal_attention_claim": False,
        "permanent_retention_authorized": False,
        "node_count": 8,
        "edge_count": 1,
        "selection": "lowest-stable-subject-id-among-alive",
        "nodes": [
            {
                "index": 0,
                "operator": "linear",
                "input_port": 0,
                "input_gate": 0.75,
                "output_port": 0,
                "output_gate": 1.5,
                "local_eligibility": True,
                "target_family": f"{target_family.replace(chr(95), chr(45))}-via-token-port-{target_port}",
            },
            {"index": 1, "input_port": 0, "trace_port": 31, "trace_gate": 1.0},
            {"index": 2, "input_port": 0, "trace_port": 0, "trace_gate": 1.0},
            {"index": 3, "input_port": 0, "trace_port": 1, "trace_gate": 1.0},
            {"index": 4, "input_port": 0, "trace_port": 2, "trace_gate": 1.0},
            {"index": 5, "input_port": 0, "trace_port": 5, "trace_gate": 0.5},
            {"index": 6, "input_port": 0, "trace_port": 6, "trace_gate": 0.25},
            {"index": 7, "input_port": 0, "trace_port": target_port, "trace_gate": 1.0},
        ],
        "edges": [
            {
                "index": 0,
                "source": 0,
                "target": 0,
                "delay_ticks": 1,
                "forward_gate": -1.5,
                "bandwidth": 2.0,
            }
        ],
        "target_family_shaping": {
            "family": target_family,
            "token_port": target_port,
            "classification": "replaceable-fixed-bootstrap-routing-bias",
            "value_semantics": None,
        },
        "objective_value_interpretation": None,
        "reward": None,
    }
    payload["profile_sha256"] = _canonical_sha256(payload)
    return payload


def _validate_source_config(cfg: Any) -> None:
    subject_vm = cfg.subject_vm
    if subject_vm.schema != SUBJECT_VM_STAGE3C5_SCHEMA:
        raise ValueError("short paired study requires Subject VM Stage 3C-5 config")
    if not subject_vm.evaluation_enabled or not subject_vm.live_write_configured:
        raise ValueError("short paired study requires evaluation and live-write contracts")
    if subject_vm.live_write.enabled:
        raise ValueError("source config must keep live_write.enabled false")
    if subject_vm.total_node_capacity < 8 or subject_vm.total_edge_capacity < 1:
        raise ValueError("bootstrap profile requires at least eight nodes and one edge")
    if subject_vm.trace.token_width <= 31:
        raise ValueError("bootstrap profile requires token width of at least 32")
    if cfg.run.experiment_mode != "scientific":
        raise ValueError("short paired study requires scientific experiment mode")


def _source_config(base_cfg: Any, *, seed: int, source_ticks: int) -> Any:
    subject_vm = replace(
        base_cfg.subject_vm,
        live_write=replace(base_cfg.subject_vm.live_write, enabled=False),
    )
    run = replace(
        base_cfg.run,
        seed=int(seed),
        ticks=int(source_ticks),
        metrics_period=max(1, int(source_ticks) + 1),
        checkpoint_period=max(1000, int(source_ticks) + 1),
        checkpoint_ticks=(),
        full_checkpoint_enabled=False,
    )
    cfg = replace(base_cfg, run=run, subject_vm=subject_vm)
    _validate_source_config(cfg)
    return cfg


def _assert_quiescent_runtime(simulation: Simulation) -> None:
    runtime = simulation.subject_vm
    if runtime.trace_storage is None or runtime.live_write_ledger is None or runtime.evaluation_ledger is None:
        raise ValueError("short paired source lacks Stage-3C trace/evaluation ledgers")
    if np.any(runtime.trace_storage.event_valid):
        raise ValueError("short paired source trace must be empty before branching")
    if np.any(runtime.live_write_ledger.entry_valid):
        raise ValueError("short paired source live-write ledger must be empty")
    if np.any(runtime.evaluation_ledger.entry_valid):
        raise ValueError("short paired source evaluation ledger must be empty")
    if np.any(runtime.live_write_ledger.row_locked):
        raise ValueError("short paired source cannot contain locked rows")


def prime_fixed_bootstrap_graph(
    simulation: Simulation, *, bootstrap_subjects: int, target_family: str = "node_bias"
) -> dict[str, Any]:
    """Install the explicit fixed bootstrap graph into a quiescent source.

    This is an experiment-only initializer.  It does not mutate the topology
    during the paired branches and must never be reported as evolved structure.
    """
    runtime = simulation.subject_vm
    storage = runtime.storage
    if storage is None:
        raise ValueError("short paired study requires allocated Subject VM storage")
    _assert_quiescent_runtime(simulation)
    alive_rows = np.flatnonzero(simulation.entities.alive).astype(np.int32)
    if alive_rows.size == 0:
        raise ValueError("short paired study source has no living entities")
    stable_subjects = simulation.entities.primary_subject_id[alive_rows]
    order = np.argsort(stable_subjects, kind="stable")
    rows = alive_rows[order[: min(int(bootstrap_subjects), alive_rows.size)]]

    storage.node_expressed[rows, :8] = True
    storage.node_operator_id[rows, :8] = np.uint16(OP_LINEAR)
    storage.node_activation_phase[rows, :8] = np.uint16(0)
    storage.node_input_port[rows, :8] = np.int16(0)
    storage.node_input_gate[rows, :8] = np.float32(1.0)
    storage.node_bias[rows, :8] = np.float32(0.0)

    storage.node_input_gate[rows, 0] = np.float32(0.75)
    storage.node_output_port[rows, 0] = np.int16(0)
    storage.node_output_gate[rows, 0] = np.float32(1.5)
    storage.node_eligibility_gate[rows, 0] = np.float32(1.0)
    storage.node_plasticity_flags[rows, 0] = np.uint8(LOCAL_ELIGIBILITY_FLAG)

    if target_family not in _BOOTSTRAP_TARGET_FAMILY_PORTS:
        raise ValueError("unsupported fixed bootstrap target family")
    trace_ports = (*_BOOTSTRAP_TRACE_PORTS[:-1], _BOOTSTRAP_TARGET_FAMILY_PORTS[target_family])
    for node, (port, gate) in enumerate(
        zip(trace_ports, _BOOTSTRAP_TRACE_GATES, strict=True)
    ):
        if port >= 0:
            storage.node_trace_port[rows, node] = np.int16(port)
            storage.node_trace_gate[rows, node] = np.float32(gate)

    storage.edge_expressed[rows, 0] = True
    storage.edge_source[rows, 0] = np.int32(0)
    storage.edge_target[rows, 0] = np.int32(0)
    storage.edge_forward_gate[rows, 0] = np.float32(-1.5)
    storage.edge_delay[rows, 0] = np.uint16(1)
    storage.edge_bandwidth[rows, 0] = np.float32(2.0)
    storage.edge_phase_mask[rows, 0] = np.uint8(ACTIVATION_PHASE_MASK)
    storage.validate_internal()
    runtime.validate_owners(
        simulation.entities.alive,
        simulation.entities.entity_id,
        simulation.entities.primary_subject_id,
    )

    profile = bootstrap_profile(target_family=target_family)
    record = {
        "schema": BOOTSTRAP_LINEAGE_SCHEMA,
        "profile_sha256": profile["profile_sha256"],
        "profile_schema": profile["schema"],
        "primed_tick": int(simulation.tick),
        "primed_subject_count": int(rows.size),
        "primed_subject_ids": [
            int(value) for value in simulation.entities.primary_subject_id[rows].tolist()
        ],
        "selection": profile["selection"],
        "evolved_topology": False,
        "scientific_effect_claim": False,
    }
    simulation.checkpoint_lineage.append(record)
    return record


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _prepare_output_root(path: Path, *, overwrite: bool) -> None:
    if path.exists() and any(path.iterdir()):
        if not overwrite:
            raise FileExistsError(
                f"short paired study output is not empty: {path}; pass --overwrite"
            )
        shutil.rmtree(path)
    path.mkdir(parents=True, exist_ok=True)


def run_short_paired_study(
    config_path: str | Path,
    *,
    parameters: ShortPairedStudyParameters,
    output_dir: str | Path,
    overwrite: bool = False,
) -> dict[str, Any]:
    parameters.validate()
    config_source = Path(config_path).expanduser().resolve()
    if not config_source.is_file():
        raise FileNotFoundError(config_source)
    root = Path(output_dir).expanduser().resolve()
    _prepare_output_root(root, overwrite=overwrite)
    profile = bootstrap_profile(target_family=parameters.bootstrap_target_family)
    _write_json(root / "bootstrap_profile.json", profile)
    resolved_backend = "cpu" if parameters.backend == "auto" else parameters.backend
    base_cfg = load_config(config_source)

    seed_records: list[dict[str, Any]] = []
    export_paths: list[Path] = []
    for seed in parameters.seeds:
        seed_root = root / f"seed_{int(seed)}"
        source_root = seed_root / "source"
        pair_root = seed_root / "paired"
        cfg = _source_config(
            base_cfg, seed=int(seed), source_ticks=parameters.source_ticks
        )
        simulation = Simulation(cfg, source_root, backend=resolved_backend)
        for _ in range(int(parameters.source_ticks)):
            simulation.step()
        _assert_quiescent_runtime(simulation)
        pre_bootstrap_checkpoint = simulation.save_full_checkpoint(
            source_root / "source_pre_bootstrap.sechk"
        )
        pre_bootstrap_metadata, _ = read_checkpoint_bundle(pre_bootstrap_checkpoint)
        lineage = prime_fixed_bootstrap_graph(
            simulation,
            bootstrap_subjects=parameters.bootstrap_subjects,
            target_family=parameters.bootstrap_target_family,
        )
        _assert_quiescent_runtime(simulation)
        source_checkpoint = simulation.save_full_checkpoint(
            source_root / "source_quiescent.sechk"
        )
        # Close ordinary run writers without advancing semantic time.
        simulation.run(until_tick=simulation.tick)

        plan = build_plan(
            source_checkpoint,
            horizon_ticks=parameters.horizon_ticks,
            finalize_pending_transients_at_export=True,
            rollback_after_ticks_override=parameters.rollback_after_ticks,
        )
        plan_path = seed_root / "paired_plan.json"
        _write_json(plan_path, plan)
        run_result = run_plan(
            plan,
            source_checkpoint=source_checkpoint,
            output_dir=pair_root,
            backend=resolved_backend,
        )
        export_path = Path(run_result["export"]).resolve()
        export_paths.append(export_path)
        export_payload = json.loads(export_path.read_text(encoding="utf-8"))
        evidence = export_payload["window_evidence"]
        seed_records.append(
            {
                "seed": int(seed),
                "pre_bootstrap_checkpoint": str(pre_bootstrap_checkpoint.resolve()),
                "pre_bootstrap_checkpoint_file_sha256": _sha256_file(pre_bootstrap_checkpoint),
                "pre_bootstrap_checkpoint_state_sha256": str(pre_bootstrap_metadata["state_sha256"]),
                "pre_bootstrap_checkpoint_config_sha256": str(pre_bootstrap_metadata["config_sha256"]),
                "source_checkpoint": str(source_checkpoint.resolve()),
                "source_checkpoint_file_sha256": _sha256_file(source_checkpoint),
                "source_checkpoint_state_sha256": plan["source"][
                    "checkpoint_state_sha256"
                ],
                "source_tick": int(plan["source"]["checkpoint_tick"]),
                "final_tick": int(plan["final_tick"]),
                "bootstrap_lineage": lineage,
                "plan": str(plan_path.resolve()),
                "plan_sha256": plan["plan_sha256"],
                "guarded_live_checkpoint": str(
                    Path(run_result["guarded_live_checkpoint"]).resolve()
                ),
                "read_only_control_checkpoint": str(
                    Path(run_result["read_only_control_checkpoint"]).resolve()
                ),
                "transient_finalization": run_result["transient_finalization"],
                "export": str(export_path),
                "export_sha256": export_payload["export_sha256"],
                "paired_window_count": int(evidence["paired_window_count"]),
                "unpaired_guarded_live_count": len(
                    evidence["unpaired_guarded_live"]
                ),
                "unpaired_read_only_control_count": len(
                    evidence["unpaired_read_only_control"]
                ),
            }
        )

    integrity = assess_exports(export_paths)
    integrity_path = root / "paired_evidence_assessment.json"
    _write_json(integrity_path, integrity)
    reproducibility = None
    reproducibility_path = root / "component_reproducibility.json"
    if bool(integrity["adequacy_screen"]["passed"]):
        reproducibility = assess_component_reproducibility([integrity_path])
        _write_json(reproducibility_path, reproducibility)

    diagnostics = assess_stage3c10_diagnostics(
        seed_records, component_reproducibility=reproducibility
    )
    diagnostics_path = root / "stage3c10_diagnostics.json"
    _write_json(diagnostics_path, diagnostics)

    aggregate = integrity["aggregate"]
    payload = {
        "schema": SHORT_PAIRED_STUDY_SCHEMA,
        "producer_version": __version__,
        "project_config": str(config_source),
        "project_config_file_sha256": _sha256_file(config_source),
        "parameters": asdict(parameters),
        "population": {
            "initial_entities": int(base_cfg.world.initial_entities),
            "max_entities": int(base_cfg.world.max_entities),
        },
        "resolved_backend": resolved_backend,
        "temporary_exposure_contract": {
            "rollback_after_ticks": int(
                parameters.rollback_after_ticks
                if parameters.rollback_after_ticks is not None
                else base_cfg.subject_vm.live_write.rollback_after_ticks
            ),
            "control_horizon_ticks": int(
                parameters.rollback_after_ticks
                if parameters.rollback_after_ticks is not None
                else base_cfg.subject_vm.evaluation.control_horizon_ticks
            ),
            "observation_ticks": int(
                base_cfg.subject_vm.evaluation.observation_ticks
            ),
            "source_checkpoint_config_unchanged": True,
        },
        "bootstrap_profile": profile,
        "seeds": seed_records,
        "paired_evidence_assessment": str(integrity_path.resolve()),
        "paired_evidence_assessment_sha256": integrity["assessment_sha256"],
        "component_reproducibility": (
            str(reproducibility_path.resolve()) if reproducibility is not None else None
        ),
        "component_reproducibility_sha256": (
            reproducibility["assessment_sha256"] if reproducibility is not None else None
        ),
        "stage3c10_diagnostics": str(diagnostics_path.resolve()),
        "stage3c10_diagnostics_sha256": diagnostics["diagnostics_sha256"],
        "engineering_summary": {
            "independent_source_pair_count": int(
                aggregate["independent_source_pair_count"]
            ),
            "total_paired_window_count": int(
                aggregate["total_paired_window_count"]
            ),
            "pooled_pairing_coverage": float(
                aggregate["pooled_pairing_coverage"]
            ),
            "rollback_failure_count": int(
                aggregate["total_rollback_failure_count"]
            ),
            "fact_clip_fraction": float(
                aggregate["pooled_fact_clip_fraction"]
            ),
            "evaluation_cost_match_fraction": float(
                aggregate["paired_evaluation_cost_match_fraction"]
            ),
            "stage3c7_engineering_screen_passed": bool(
                integrity["adequacy_screen"]["passed"]
            ),
            "stage3c8_report_generated": reproducibility is not None,
            "stage3c10_diagnostics_generated": True,
            "sources_with_discrete_action_divergence": int(
                diagnostics["aggregate"]["sources_with_discrete_action_divergence"]
            ),
            "sources_with_objective_event_divergence": int(
                diagnostics["aggregate"]["sources_with_objective_event_divergence"]
            ),
        },
        "fixed_bootstrap_is_evolved_result": False,
        "universal_attention_claim": False,
        "universal_scalar_objective": False,
        "automatic_keep_or_revert_decision": False,
        "causal_effect_authorized": False,
        "permanent_parameter_retention_authorized": False,
        "learning_claim_authorized": False,
        "subjecthood_claim_authorized": False,
    }
    payload["study_sha256"] = _canonical_sha256(payload)
    _write_json(root / "study_report.json", payload)
    return payload


def _parse_seeds(raw: str) -> tuple[int, ...]:
    values = tuple(int(item.strip()) for item in raw.split(",") if item.strip())
    if not values:
        raise ValueError("--seeds requires at least one integer")
    return values


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Run a short, fixed-bootstrap, no-retention Subject VM paired study."
        )
    )
    parser.add_argument("--config", required=True)
    parser.add_argument("--seeds", default="12301,12302,12303")
    parser.add_argument("--source-ticks", type=int, default=2)
    parser.add_argument("--horizon-ticks", type=int, default=5)
    parser.add_argument("--bootstrap-subjects", type=int, default=16)
    parser.add_argument("--rollback-after-ticks", type=int)
    parser.add_argument(
        "--bootstrap-target-family",
        choices=tuple(_BOOTSTRAP_TARGET_FAMILY_PORTS),
        default="node_bias",
    )
    parser.add_argument("--backend", choices=("auto", "cpu"), default="auto")
    parser.add_argument("--output", required=True)
    parser.add_argument("--overwrite", action="store_true")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    report = run_short_paired_study(
        args.config,
        parameters=ShortPairedStudyParameters(
            seeds=_parse_seeds(args.seeds),
            source_ticks=args.source_ticks,
            horizon_ticks=args.horizon_ticks,
            bootstrap_subjects=args.bootstrap_subjects,
            backend=args.backend,
            rollback_after_ticks=args.rollback_after_ticks,
            bootstrap_target_family=args.bootstrap_target_family,
        ),
        output_dir=args.output,
        overwrite=args.overwrite,
    )
    print(json.dumps(report["engineering_summary"], ensure_ascii=False))


if __name__ == "__main__":
    main()


__all__ = [
    "BOOTSTRAP_GRAPH_PROFILE_SCHEMA",
    "BOOTSTRAP_LINEAGE_SCHEMA",
    "SHORT_PAIRED_STUDY_SCHEMA",
    "ShortPairedStudyParameters",
    "bootstrap_profile",
    "prime_fixed_bootstrap_graph",
    "run_short_paired_study",
]
