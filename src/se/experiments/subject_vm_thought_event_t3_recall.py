"""T3 minimal forward ThoughtEvent recall mechanism smoke.

The study adds one deterministic, role-neutral read path from the latest
strictly-prior committed ThoughtEvent into a readout-only graph node.  It does
not test delayed-information utility and must not be reported as a formed
chain of thought.  Four arms separate content, transformation, counted cost,
and the absence of recall.
"""
from __future__ import annotations

import argparse
import copy
from dataclasses import asdict, dataclass, replace
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
    SUBJECT_VM_THOUGHT_EVENT_RECALL_SCHEMA,
    SUBJECT_VM_THOUGHT_EVENT_SCHEMA,
    SubjectVMThoughtEventConfig,
    SubjectVMThoughtEventRecallConfig,
)
from .subject_vm_short_paired_study import (
    _canonical_sha256,
    _sha256_file,
    _write_json,
    bootstrap_profile,
    prime_fixed_bootstrap_graph,
)

THOUGHT_EVENT_T3_STUDY_SCHEMA = "se-subject-vm-thought-event-t3-recall-study-v1"
THOUGHT_EVENT_T3_RECORD_SCHEMA = "se-subject-vm-thought-event-t3-recall-seed-record-v1"

_ARM_SPECS: dict[str, str | None] = {
    "no-recall": None,
    "identity-recall": "identity",
    "rotate-one-coordinate-control": "rotate-one-coordinate-control",
    "zero-content-equal-cost-control": "zero-content-control",
}


@dataclass(frozen=True)
class ThoughtEventT3Parameters:
    seeds: tuple[int, ...]
    source_ticks: int = 2
    audit_ticks: int = 10
    bootstrap_subjects: int = 16
    capacity_per_subject: int = 16
    retention_ticks: int = 8
    max_parent_count: int = 4
    recall_ingress_node: int = 9
    recall_token_port: int = 30
    recall_gate: float = 0.25
    backend: str = "auto"

    def validate(self) -> None:
        if len(self.seeds) < 3 or len(set(self.seeds)) != len(self.seeds):
            raise ValueError("T3 requires at least three unique seeds")
        if any(int(seed) < 0 for seed in self.seeds):
            raise ValueError("T3 seeds must be non-negative")
        if self.source_ticks != 2:
            raise ValueError("T3 source_ticks is frozen at 2")
        if self.audit_ticks != 10:
            raise ValueError("T3 audit_ticks is frozen at 10")
        if self.bootstrap_subjects != 16:
            raise ValueError("T3 bootstrap_subjects is frozen at 16")
        if self.capacity_per_subject != 16:
            raise ValueError("T3 capacity_per_subject is frozen at 16")
        if self.retention_ticks != 8:
            raise ValueError("T3 retention_ticks is frozen at 8")
        if self.max_parent_count != 4:
            raise ValueError("T3 max_parent_count is frozen at 4")
        if self.recall_ingress_node != 9 or self.recall_token_port != 30:
            raise ValueError("T3 ingress is frozen at node 9 / token port 30")
        if float(self.recall_gate) != 0.25:
            raise ValueError("T3 recall_gate is frozen at 0.25")
        if self.backend not in {"cpu", "auto"}:
            raise ValueError("T3 supports CPU or auto")


def _prepare_output(path: Path, *, overwrite: bool) -> None:
    if path.exists():
        if not overwrite:
            raise FileExistsError(path)
        shutil.rmtree(path)
    path.mkdir(parents=True, exist_ok=False)


def _thought_event_config(
    parameters: ThoughtEventT3Parameters,
    *,
    content_mode: str | None,
) -> SubjectVMThoughtEventConfig:
    recall = SubjectVMThoughtEventRecallConfig()
    if content_mode is not None:
        recall = SubjectVMThoughtEventRecallConfig(
            schema=SUBJECT_VM_THOUGHT_EVENT_RECALL_SCHEMA,
            enabled=True,
            content_mode=str(content_mode),
            min_age_ticks=1,
            max_ingress_paths=1,
            search_per_slot_cost_units=1,
            read_base_cost_units=1,
            read_per_coordinate_cost_units=1,
            ingress_per_path_cost_units=1,
        )
    return SubjectVMThoughtEventConfig(
        schema=SUBJECT_VM_THOUGHT_EVENT_SCHEMA,
        enabled=True,
        capacity_per_subject=parameters.capacity_per_subject,
        max_parent_count=parameters.max_parent_count,
        retention_ticks=parameters.retention_ticks,
        emission_base_cost_units=1,
        emission_per_coordinate_cost_units=1,
        parent_link_cost_units=1,
        retention_per_event_tick_cost_units=1,
        recall=recall,
    )


def _run_config(
    base: Any,
    *,
    seed: int,
    parameters: ThoughtEventT3Parameters,
    content_mode: str | None,
) -> Any:
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
        thought_event=_thought_event_config(parameters, content_mode=content_mode),
    )
    return replace(base, run=run, subject_vm=subject_vm)


def _selected_rows(simulation: Simulation, subject_ids: tuple[int, ...]) -> np.ndarray:
    wanted = np.asarray(subject_ids, dtype=np.uint64)
    mask = simulation.entities.alive & np.isin(
        simulation.entities.primary_subject_id, wanted
    )
    rows = np.flatnonzero(mask).astype(np.int32)
    if rows.size != wanted.size:
        raise ValueError("T3 selected bootstrap subject set changed during audit")
    actual = np.sort(simulation.entities.primary_subject_id[rows])
    if not np.array_equal(actual, np.sort(wanted)):
        raise ValueError("T3 selected subject identity drifted")
    return rows


def _event_slot(arena: Any, row: int, event_id: int) -> int:
    matches = np.flatnonzero(
        arena.event_valid[int(row)]
        & (arena.event_id[int(row)] == np.uint64(event_id))
    )
    if matches.size != 1:
        raise ValueError("T3 parent ThoughtEvent is not uniquely retained at child commit")
    return int(matches[0])


def _extract_tick(
    simulation: Simulation,
    *,
    event_tick: int,
    subject_ids: tuple[int, ...],
) -> dict[str, np.ndarray]:
    arena = simulation.subject_vm.thought_event_arena
    trace = simulation.subject_vm.trace_storage
    if arena is None or trace is None:
        raise ValueError("T3 requires ThoughtEvent arena and legacy trace")
    rows = _selected_rows(simulation, subject_ids)
    arena_mask = arena.event_valid[rows] & (arena.event_tick[rows] == int(event_tick))
    local_row, slots = np.nonzero(arena_mask)
    if slots.size != len(subject_ids):
        raise ValueError("T3 did not emit exactly one ThoughtEvent per selected subject")
    event_rows = rows[local_row]
    order = np.argsort(arena.subject_id[event_rows, slots], kind="stable")
    event_rows = event_rows[order]
    slots = slots[order]

    trace_mask = trace.event_valid[rows] & (trace.event_tick[rows] == int(event_tick))
    trace_local_row, trace_slots = np.nonzero(trace_mask)
    if trace_slots.size != len(subject_ids):
        raise ValueError("T3 legacy trace count disagrees with ThoughtEvent count")
    trace_rows = rows[trace_local_row]
    trace_order = np.argsort(trace.subject_id[trace_rows, trace_slots], kind="stable")
    trace_rows = trace_rows[trace_order]
    trace_slots = trace_slots[trace_order]
    if not np.array_equal(
        arena.event_id[event_rows, slots], trace.event_id[trace_rows, trace_slots]
    ):
        raise ValueError("T3 ThoughtEvent/legacy trace event identity mismatch")
    if not np.array_equal(
        arena.token[event_rows, slots], trace.thought_token[trace_rows, trace_slots]
    ):
        raise ValueError("T3 ThoughtEvent/legacy trace token mismatch")

    count = slots.size
    parent_event_id = np.zeros(count, dtype=np.uint64)
    parent_tick = np.full(count, -1, dtype=np.int64)
    parent_weight = np.zeros(count, dtype=np.float32)
    parent_token = np.zeros((count, arena.token_width), dtype=np.float32)
    for index, (row, slot) in enumerate(zip(event_rows.tolist(), slots.tolist(), strict=True)):
        parent_count = int(arena.parent_count[row, slot])
        if parent_count not in {0, 1}:
            raise ValueError("T3 supports zero or one parent per event")
        if parent_count == 0:
            continue
        parent_id = int(arena.parent_event_id[row, slot, 0])
        parent_slot = _event_slot(arena, row, parent_id)
        parent_event_id[index] = np.uint64(parent_id)
        parent_tick[index] = arena.event_tick[row, parent_slot]
        parent_weight[index] = arena.parent_weight[row, slot, 0]
        parent_token[index] = arena.token[row, parent_slot]
        if int(parent_tick[index]) >= int(event_tick):
            raise ValueError("T3 parent must strictly predate child")

    return {
        "event_id": arena.event_id[event_rows, slots].copy(),
        "entity_id": arena.entity_id[event_rows, slots].copy(),
        "subject_id": arena.subject_id[event_rows, slots].copy(),
        "tick": np.full(count, int(event_tick), dtype=np.int64),
        "token": arena.token[event_rows, slots].copy(),
        "parent_count": arena.parent_count[event_rows, slots].copy(),
        "parent_event_id": parent_event_id,
        "parent_tick": parent_tick,
        "parent_weight": parent_weight,
        "parent_token": parent_token,
        "action_id": trace.action_id[trace_rows, trace_slots].copy(),
        "sampled_probability": trace.sampled_probability[trace_rows, trace_slots].copy(),
        "action_potentials": trace.action_potentials[trace_rows, trace_slots].copy(),
    }


def _save_npz(path: Path, records: list[dict[str, np.ndarray]]) -> None:
    keys = tuple(records[0])
    arrays = {
        key: np.concatenate([record[key] for record in records], axis=0)
        for key in keys
    }
    np.savez_compressed(path, **arrays)


def _run_arm(
    *,
    base_cfg: Any,
    seed: int,
    arm: str,
    content_mode: str | None,
    root: Path,
    parameters: ThoughtEventT3Parameters,
) -> dict[str, Any]:
    cfg = _run_config(
        copy.deepcopy(base_cfg),
        seed=seed,
        parameters=parameters,
        content_mode=content_mode,
    )
    run_config_sha256 = config_sha256(cfg)
    arm_root = root / arm / f"seed_{seed}"
    simulation = Simulation(cfg, arm_root / "run", backend=parameters.backend)
    for _ in range(parameters.source_ticks):
        simulation.step()
    arena = simulation.subject_vm.thought_event_arena
    if arena is None or np.any(arena.event_valid):
        raise ValueError("T3 arena must exist and be empty before bootstrap")
    recall_enabled = content_mode is not None
    lineage = prime_fixed_bootstrap_graph(
        simulation,
        bootstrap_subjects=parameters.bootstrap_subjects,
        target_family="edge_forward_gate",
        edge_carrier_enabled=True,
        readout_input_port=11,
        second_readout_input_port=7,
        recall_ingress_node=(parameters.recall_ingress_node if recall_enabled else None),
        recall_token_port=(parameters.recall_token_port if recall_enabled else None),
        recall_gate=(parameters.recall_gate if recall_enabled else 0.0),
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
        rows = _selected_rows(simulation, subject_ids)
        lifecycle.append(
            {
                "event_tick": event_tick,
                "simulation_tick": int(simulation.tick),
                "stored_events": int(np.count_nonzero(arena.event_valid[rows])),
                "minimum_events_per_subject": int(np.min(arena.event_count[rows])),
                "maximum_events_per_subject": int(np.max(arena.event_count[rows])),
                "thought_event_accounting": asdict(
                    simulation.subject_vm.thought_event_accounting
                ),
                "recall_accounting": asdict(
                    simulation.subject_vm.thought_event_recall_accounting
                ),
            }
        )
    event_path = arm_root / "thought_events.npz"
    event_path.parent.mkdir(parents=True, exist_ok=True)
    _save_npz(event_path, records)
    seed_record = {
        "schema": THOUGHT_EVENT_T3_RECORD_SCHEMA,
        "project_version": __version__,
        "arm": arm,
        "content_mode": content_mode,
        "seed": int(seed),
        "source_ticks": parameters.source_ticks,
        "audit_ticks": parameters.audit_ticks,
        "bootstrap_subject_ids": list(subject_ids),
        "bootstrap_lineage": lineage,
        "config_sha256": run_config_sha256,
        "event_file": event_path.relative_to(root).as_posix(),
        "event_file_sha256": _sha256_file(event_path),
        "lifecycle": lifecycle,
        "final_thought_event_accounting": asdict(
            simulation.subject_vm.thought_event_accounting
        ),
        "final_recall_accounting": asdict(
            simulation.subject_vm.thought_event_recall_accounting
        ),
        "final_arena": arena.diagnostics(),
        "final_runtime": simulation.subject_vm.diagnostics(),
    }
    seed_record["record_sha256"] = _canonical_sha256(seed_record)
    _write_json(arm_root / "seed_record.json", seed_record)
    return seed_record


def _load_events(root: Path, arm: str, seed: int) -> dict[str, np.ndarray]:
    return dict(np.load(root / arm / f"seed_{seed}" / "thought_events.npz"))


def _compare_arms(root: Path, seed: int) -> dict[str, Any]:
    arms = {arm: _load_events(root, arm, seed) for arm in _ARM_SPECS}
    reference = arms["no-recall"]
    identity_fields = (
        "event_id",
        "entity_id",
        "subject_id",
        "tick",
        "action_id",
        "sampled_probability",
        "action_potentials",
    )
    identity: dict[str, dict[str, bool]] = {}
    for arm, arrays in arms.items():
        identity[arm] = {
            field: bool(np.array_equal(reference[field], arrays[field]))
            for field in identity_fields
        }
        if not all(identity[arm].values()):
            raise ValueError("T3 recall arm changed action/event semantics")

    zero = arms["zero-content-equal-cost-control"]
    if not np.array_equal(reference["token"], zero["token"]):
        raise ValueError("T3 zero-content equal-cost control changed token content")
    for arm in ("identity-recall", "rotate-one-coordinate-control"):
        delta = arms[arm]["token"] - reference["token"]
        differing = np.flatnonzero(np.any(delta != 0.0, axis=0)).astype(int).tolist()
        if differing != [30]:
            raise ValueError("T3 content recall must alter only token coordinate 30")
    return {
        "seed": int(seed),
        "identity_against_no_recall": identity,
        "zero_content_token_identity": True,
        "content_arms_differ_only_at_coordinate_30": True,
    }


def run_thought_event_t3_study(
    config_path: str | Path,
    *,
    output_dir: str | Path,
    parameters: ThoughtEventT3Parameters,
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
            second_readout_input_port=7,
            recall_ingress_node=(parameters.recall_ingress_node if mode is not None else None),
            recall_token_port=(parameters.recall_token_port if mode is not None else None),
            recall_gate=(parameters.recall_gate if mode is not None else 0.0),
        )
        for arm, mode in _ARM_SPECS.items()
    }
    _write_json(root / "bootstrap_profiles.json", profiles)
    records: list[dict[str, Any]] = []
    for arm, mode in _ARM_SPECS.items():
        for seed in parameters.seeds:
            records.append(
                _run_arm(
                    base_cfg=base_cfg,
                    seed=int(seed),
                    arm=arm,
                    content_mode=mode,
                    root=root,
                    parameters=parameters,
                )
            )
    cross_arm = [_compare_arms(root, int(seed)) for seed in parameters.seeds]
    report: dict[str, Any] = {
        "schema": THOUGHT_EVENT_T3_STUDY_SCHEMA,
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
                "content_mode": mode,
                "recall_enabled": mode is not None,
                "bootstrap_profile_sha256": profiles[arm]["profile_sha256"],
            }
            for arm, mode in _ARM_SPECS.items()
        },
        "seed_records": records,
        "cross_arm_identity": cross_arm,
        "runtime_learning_mechanism_change": False,
        "single_role_neutral_read_path": True,
        "same_tick_recall_allowed": False,
        "read_head_or_query_network_enabled": False,
        "random_retrieval_enabled": False,
        "retention_policy_change": False,
        "language_or_signal_channel_change": False,
    }
    report["study_sha256"] = _canonical_sha256(report)
    _write_json(root / "study_report.json", report)
    return report


def _parse_seeds(value: str) -> tuple[int, ...]:
    return tuple(int(item.strip()) for item in value.split(",") if item.strip())


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    parser.add_argument(
        "--seeds",
        default="12601,12602,12603,12604,12605,12606,12607,12608,12609",
    )
    parser.add_argument("--source-ticks", type=int, default=2)
    parser.add_argument("--audit-ticks", type=int, default=10)
    parser.add_argument("--bootstrap-subjects", type=int, default=16)
    parser.add_argument("--backend", choices=("cpu", "auto"), default="auto")
    parser.add_argument("--output", required=True)
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()
    report = run_thought_event_t3_study(
        args.config,
        output_dir=args.output,
        overwrite=args.overwrite,
        parameters=ThoughtEventT3Parameters(
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
