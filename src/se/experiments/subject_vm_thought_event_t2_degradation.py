"""T2 pre-recall ThoughtEvent degeneration study.

The study observes the already-implemented T1 arena without adding recall or
changing token production.  It reuses the frozen Stage-3C dual-readout
bootstrap as a rank-one duplicate-coordinate control and a rank-two candidate.
"""
from __future__ import annotations

import argparse
import copy
from dataclasses import asdict, dataclass, replace
import hashlib
import json
from pathlib import Path
import shutil
from typing import Any

import numpy as np

from .. import __version__
from ..cfg import load_config
from ..checkpointing import config_sha256
from ..runtime.sim import Simulation
from ..subject_vm.config import (
    SUBJECT_VM_THOUGHT_EVENT_SCHEMA,
    SubjectVMThoughtEventConfig,
)
from .subject_vm_short_paired_study import (
    _canonical_sha256,
    _sha256_file,
    _write_json,
    bootstrap_profile,
    prime_fixed_bootstrap_graph,
)

THOUGHT_EVENT_T2_STUDY_SCHEMA = "se-subject-vm-thought-event-t2-study-v1"
THOUGHT_EVENT_T2_RECORD_SCHEMA = "se-subject-vm-thought-event-t2-seed-record-v1"
_T2_ARMS = {
    "duplicate-coordinate-control": 11,
    "rank-two-candidate": 7,
}


@dataclass(frozen=True)
class ThoughtEventT2Parameters:
    seeds: tuple[int, ...]
    source_ticks: int = 2
    audit_ticks: int = 12
    bootstrap_subjects: int = 16
    capacity_per_subject: int = 16
    retention_ticks: int = 8
    max_parent_count: int = 4
    backend: str = "auto"

    def validate(self) -> None:
        if len(self.seeds) < 3 or len(set(self.seeds)) != len(self.seeds):
            raise ValueError("T2 requires at least three unique seeds")
        if any(int(seed) < 0 for seed in self.seeds):
            raise ValueError("T2 seeds must be non-negative")
        if self.source_ticks != 2:
            raise ValueError("T2 source_ticks is frozen at 2")
        if self.audit_ticks != 12:
            raise ValueError("T2 audit_ticks is frozen at 12")
        if self.bootstrap_subjects != 16:
            raise ValueError("T2 bootstrap_subjects is frozen at 16")
        if self.capacity_per_subject != 16:
            raise ValueError("T2 capacity_per_subject is frozen at 16")
        if self.retention_ticks != 8:
            raise ValueError("T2 retention_ticks is frozen at 8")
        if self.max_parent_count != 4:
            raise ValueError("T2 max_parent_count is frozen at 4")
        if self.backend not in {"cpu", "auto"}:
            raise ValueError("T2 supports CPU or auto")


def _prepare_output(path: Path, *, overwrite: bool) -> None:
    if path.exists():
        if not overwrite:
            raise FileExistsError(path)
        shutil.rmtree(path)
    path.mkdir(parents=True, exist_ok=False)


def _run_config(base: Any, *, seed: int, parameters: ThoughtEventT2Parameters) -> Any:
    thought_event = SubjectVMThoughtEventConfig(
        schema=SUBJECT_VM_THOUGHT_EVENT_SCHEMA,
        enabled=True,
        capacity_per_subject=parameters.capacity_per_subject,
        max_parent_count=parameters.max_parent_count,
        retention_ticks=parameters.retention_ticks,
        emission_base_cost_units=1,
        emission_per_coordinate_cost_units=1,
        parent_link_cost_units=1,
        retention_per_event_tick_cost_units=1,
    )
    run = replace(
        base.run,
        seed=int(seed),
        ticks=int(parameters.source_ticks + parameters.audit_ticks),
        metrics_period=max(100, parameters.source_ticks + parameters.audit_ticks + 1),
        checkpoint_period=1000,
        checkpoint_ticks=(),
        full_checkpoint_enabled=False,
    )
    subject_vm = replace(
        base.subject_vm,
        live_write=replace(base.subject_vm.live_write, enabled=False),
        thought_event=thought_event,
    )
    return replace(base, run=run, subject_vm=subject_vm)


def _selected_rows(simulation: Simulation, subject_ids: tuple[int, ...]) -> np.ndarray:
    wanted = np.asarray(subject_ids, dtype=np.uint64)
    mask = simulation.entities.alive & np.isin(
        simulation.entities.primary_subject_id, wanted
    )
    rows = np.flatnonzero(mask).astype(np.int32)
    if rows.size != wanted.size:
        raise ValueError("T2 selected bootstrap subject set changed during audit")
    actual = np.sort(simulation.entities.primary_subject_id[rows])
    if not np.array_equal(actual, np.sort(wanted)):
        raise ValueError("T2 selected subject identity drifted")
    return rows


def _extract_tick(
    simulation: Simulation,
    *,
    event_tick: int,
    subject_ids: tuple[int, ...],
) -> dict[str, np.ndarray]:
    arena = simulation.subject_vm.thought_event_arena
    trace = simulation.subject_vm.trace_storage
    if arena is None or trace is None:
        raise ValueError("T2 requires ThoughtEvent arena and legacy trace")
    rows = _selected_rows(simulation, subject_ids)
    arena_mask = arena.event_valid[rows] & (arena.event_tick[rows] == int(event_tick))
    arena_local_row, arena_slot = np.nonzero(arena_mask)
    if arena_slot.size != len(subject_ids):
        raise ValueError("T2 did not emit exactly one ThoughtEvent per selected subject")
    arena_rows = rows[arena_local_row]
    order = np.argsort(arena.subject_id[arena_rows, arena_slot], kind="stable")
    arena_rows = arena_rows[order]
    arena_slot = arena_slot[order]

    trace_mask = trace.event_valid[rows] & (trace.event_tick[rows] == int(event_tick))
    trace_local_row, trace_slot = np.nonzero(trace_mask)
    if trace_slot.size != len(subject_ids):
        raise ValueError("T2 legacy trace count disagrees with ThoughtEvent count")
    trace_rows = rows[trace_local_row]
    trace_order = np.argsort(trace.subject_id[trace_rows, trace_slot], kind="stable")
    trace_rows = trace_rows[trace_order]
    trace_slot = trace_slot[trace_order]

    if not np.array_equal(
        arena.event_id[arena_rows, arena_slot], trace.event_id[trace_rows, trace_slot]
    ):
        raise ValueError("T2 ThoughtEvent/legacy trace event identity mismatch")
    if not np.array_equal(
        arena.token[arena_rows, arena_slot], trace.thought_token[trace_rows, trace_slot]
    ):
        raise ValueError("T2 ThoughtEvent/legacy trace token mismatch")
    if np.any(arena.parent_count[arena_rows, arena_slot] != 0):
        raise ValueError("T2 pre-recall runtime unexpectedly emitted parent links")

    return {
        "event_id": arena.event_id[arena_rows, arena_slot].copy(),
        "entity_id": arena.entity_id[arena_rows, arena_slot].copy(),
        "subject_id": arena.subject_id[arena_rows, arena_slot].copy(),
        "tick": np.full(arena_slot.size, int(event_tick), dtype=np.int64),
        "token": arena.token[arena_rows, arena_slot].copy(),
        "parent_count": arena.parent_count[arena_rows, arena_slot].copy(),
        "action_id": trace.action_id[trace_rows, trace_slot].copy(),
        "sampled_probability": trace.sampled_probability[trace_rows, trace_slot].copy(),
        "action_potentials": trace.action_potentials[trace_rows, trace_slot].copy(),
    }


def _save_npz(path: Path, records: list[dict[str, np.ndarray]]) -> None:
    keys = tuple(records[0])
    arrays = {key: np.concatenate([record[key] for record in records], axis=0) for key in keys}
    np.savez_compressed(path, **arrays)


def _run_arm(
    *,
    base_cfg: Any,
    seed: int,
    arm: str,
    second_readout_port: int,
    root: Path,
    parameters: ThoughtEventT2Parameters,
) -> dict[str, Any]:
    cfg = _run_config(copy.deepcopy(base_cfg), seed=seed, parameters=parameters)
    run_config_sha256 = config_sha256(cfg)
    arm_root = root / arm / f"seed_{seed}"
    simulation = Simulation(cfg, arm_root / "run", backend=parameters.backend)
    for _ in range(parameters.source_ticks):
        simulation.step()
    if simulation.subject_vm.thought_event_arena is None:
        raise ValueError("T2 ThoughtEvent arena missing")
    if np.any(simulation.subject_vm.thought_event_arena.event_valid):
        raise ValueError("T2 arena must be empty before fixed bootstrap is primed")
    lineage = prime_fixed_bootstrap_graph(
        simulation,
        bootstrap_subjects=parameters.bootstrap_subjects,
        target_family="edge_forward_gate",
        edge_carrier_enabled=True,
        readout_input_port=11,
        second_readout_input_port=second_readout_port,
    )
    subject_ids = tuple(int(value) for value in lineage["primed_subject_ids"])
    records: list[dict[str, np.ndarray]] = []
    lifecycle: list[dict[str, Any]] = []
    for _ in range(parameters.audit_ticks):
        event_tick = int(simulation.tick)
        simulation.step()
        records.append(
            _extract_tick(
                simulation,
                event_tick=event_tick,
                subject_ids=subject_ids,
            )
        )
        arena = simulation.subject_vm.thought_event_arena
        assert arena is not None
        rows = _selected_rows(simulation, subject_ids)
        lifecycle.append(
            {
                "event_tick": event_tick,
                "simulation_tick": int(simulation.tick),
                "stored_events": int(np.count_nonzero(arena.event_valid[rows])),
                "minimum_events_per_subject": int(np.min(arena.event_count[rows])),
                "maximum_events_per_subject": int(np.max(arena.event_count[rows])),
                "accounting": asdict(simulation.subject_vm.thought_event_accounting),
            }
        )
    event_path = arm_root / "thought_events.npz"
    event_path.parent.mkdir(parents=True, exist_ok=True)
    _save_npz(event_path, records)
    arena = simulation.subject_vm.thought_event_arena
    assert arena is not None
    seed_record = {
        "schema": THOUGHT_EVENT_T2_RECORD_SCHEMA,
        "project_version": __version__,
        "arm": arm,
        "seed": int(seed),
        "source_ticks": parameters.source_ticks,
        "audit_ticks": parameters.audit_ticks,
        "bootstrap_subject_ids": list(subject_ids),
        "bootstrap_lineage": lineage,
        "config_sha256": run_config_sha256,
        "event_file": event_path.relative_to(root).as_posix(),
        "event_file_sha256": _sha256_file(event_path),
        "emitted_event_count": int(sum(record["event_id"].size for record in records)),
        "parent_count_sum": int(sum(np.sum(record["parent_count"]) for record in records)),
        "lifecycle": lifecycle,
        "final_accounting": asdict(simulation.subject_vm.thought_event_accounting),
        "final_arena": arena.diagnostics(),
        "forward_recall_enabled": False,
        "runtime_feedback_enabled": False,
    }
    seed_record["record_sha256"] = _canonical_sha256(seed_record)
    record_path = arm_root / "seed_record.json"
    _write_json(record_path, seed_record)
    simulation.run(until_tick=simulation.tick)
    return seed_record


def _compare_arms(root: Path, seed: int) -> dict[str, Any]:
    paths = {arm: root / arm / f"seed_{seed}" / "thought_events.npz" for arm in _T2_ARMS}
    arrays = {arm: np.load(path) for arm, path in paths.items()}
    control = arrays["duplicate-coordinate-control"]
    candidate = arrays["rank-two-candidate"]
    identity_fields = (
        "event_id",
        "entity_id",
        "subject_id",
        "tick",
        "parent_count",
        "action_id",
        "sampled_probability",
        "action_potentials",
    )
    identity = {field: bool(np.array_equal(control[field], candidate[field])) for field in identity_fields}
    token_delta = candidate["token"] - control["token"]
    differing_coordinates = np.flatnonzero(np.any(token_delta != 0.0, axis=0)).astype(int).tolist()
    if differing_coordinates != [30]:
        raise ValueError("T2 arms must differ only at token coordinate 30")
    if not all(identity.values()):
        raise ValueError("T2 readout-only arms changed action/event semantics")
    return {
        "seed": int(seed),
        "identity": identity,
        "tokens_differ_only_at_coordinate_30": True,
        "differing_coordinates": differing_coordinates,
    }


def run_thought_event_t2_study(
    config_path: str | Path,
    *,
    output_dir: str | Path,
    parameters: ThoughtEventT2Parameters,
    overwrite: bool = False,
) -> dict[str, Any]:
    parameters.validate()
    config_source = Path(config_path).expanduser().resolve()
    if not config_source.is_file():
        raise FileNotFoundError(config_source)
    root = Path(output_dir).expanduser().resolve()
    _prepare_output(root, overwrite=overwrite)
    base_cfg = load_config(config_source)
    profiles = {
        arm: bootstrap_profile(
            target_family="edge_forward_gate",
            edge_carrier_enabled=True,
            readout_input_port=11,
            second_readout_input_port=port,
        )
        for arm, port in _T2_ARMS.items()
    }
    _write_json(root / "bootstrap_profiles.json", profiles)
    records: list[dict[str, Any]] = []
    for arm, port in _T2_ARMS.items():
        for seed in parameters.seeds:
            records.append(
                _run_arm(
                    base_cfg=base_cfg,
                    seed=int(seed),
                    arm=arm,
                    second_readout_port=int(port),
                    root=root,
                    parameters=parameters,
                )
            )
    cross_arm = [_compare_arms(root, int(seed)) for seed in parameters.seeds]
    report: dict[str, Any] = {
        "schema": THOUGHT_EVENT_T2_STUDY_SCHEMA,
        "project_version": __version__,
        "config": (
            config_source.relative_to(Path.cwd()).as_posix()
            if config_source.is_relative_to(Path.cwd())
            else config_source.name
        ),
        "config_file_sha256": _sha256_file(config_source),
        "parameters": asdict(parameters),
        "arms": {
            arm: {
                "second_readout_input_port": port,
                "bootstrap_profile_sha256": profiles[arm]["profile_sha256"],
            }
            for arm, port in _T2_ARMS.items()
        },
        "seed_records": records,
        "cross_arm_identity": cross_arm,
        "runtime_learning_mechanism_change": False,
        "forward_recall_enabled": False,
        "read_head_enabled": False,
        "language_or_signal_channel_change": False,
        "parent_count_expected": 0,
    }
    report["study_sha256"] = _canonical_sha256(report)
    _write_json(root / "study_report.json", report)
    return report


def _parse_seeds(value: str) -> tuple[int, ...]:
    return tuple(int(item.strip()) for item in value.split(",") if item.strip())


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    parser.add_argument("--seeds", default="12501,12502,12503,12504,12505,12506,12507,12508,12509")
    parser.add_argument("--source-ticks", type=int, default=2)
    parser.add_argument("--audit-ticks", type=int, default=12)
    parser.add_argument("--bootstrap-subjects", type=int, default=16)
    parser.add_argument("--backend", choices=("cpu", "auto"), default="auto")
    parser.add_argument("--output", required=True)
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()
    report = run_thought_event_t2_study(
        args.config,
        output_dir=args.output,
        overwrite=args.overwrite,
        parameters=ThoughtEventT2Parameters(
            seeds=_parse_seeds(args.seeds),
            source_ticks=args.source_ticks,
            audit_ticks=args.audit_ticks,
            bootstrap_subjects=args.bootstrap_subjects,
            backend=args.backend,
        ),
    )
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
