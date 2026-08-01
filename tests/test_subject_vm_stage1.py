from __future__ import annotations

from dataclasses import asdict, replace
import hashlib
import json
from pathlib import Path

import numpy as np
import pytest

from se.cfg import load_config
from se.checkpointing import _config_sha256, read_checkpoint_bundle
from se.config_identity import strip_inactive_extensions
from se.epochs import build_regional_branch, freeze_epoch_base
from se.runtime.sim import Simulation
from se.subject_vm import (
    STAGE1_DEVICE_CONTRACT,
    SUBJECT_VM_REGION_NAMES,
    SUBJECT_VM_STAGE1_SCHEMA,
    SubjectVMConfig,
    SubjectVMRegionConfig,
    SubjectVMRuntime,
    compact_rows,
)

REGISTRY = Path("protocols/epochs/subject_epochs_v1.json")
LEGACY_MVP_SMALL_CHECKPOINT_CONFIG_SHA256 = (
    "48b69bdc4969cda87359ca1f49d4127ddf5467c4b3b7a66047bb72c1984e922b"
)
LEGACY_MVP_SMALL_CANONICAL_SHA256 = (
    "df60bc2336a749edf1280fc44d0f63ac4f62d9854bcf2f152a73a27d65586b86"
)


def _stage1_config() -> SubjectVMConfig:
    periods = (1, 2, 4, 1)
    return SubjectVMConfig(
        enabled=True,
        schema=SUBJECT_VM_STAGE1_SCHEMA,
        node_state_width=3,
        regions=tuple(
            SubjectVMRegionConfig(
                name=name,
                node_capacity=2,
                edge_capacity=2,
                update_period=period,
            )
            for name, period in zip(SUBJECT_VM_REGION_NAMES, periods, strict=True)
        ),
    )


def _small_config(*, subject_vm: SubjectVMConfig | None = None):
    cfg = load_config("configs/mvp_small.json")
    return replace(
        cfg,
        run=replace(
            cfg.run,
            ticks=4,
            metrics_period=100,
            checkpoint_period=100,
            full_checkpoint_enabled=False,
        ),
        world=replace(cfg.world, initial_entities=48, max_entities=96),
        subject_vm=subject_vm or SubjectVMConfig(),
    )


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_disabled_extension_preserves_frozen_config_identities() -> None:
    cfg = load_config("configs/mvp_small.json")
    assert cfg.subject_vm == SubjectVMConfig()
    assert _config_sha256(cfg) == LEGACY_MVP_SMALL_CHECKPOINT_CONFIG_SHA256
    canonical = json.dumps(
        strip_inactive_extensions(asdict(cfg)),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    assert hashlib.sha256(canonical).hexdigest() == LEGACY_MVP_SMALL_CANONICAL_SHA256
    assert "subject_vm" not in strip_inactive_extensions(asdict(cfg))


def test_subject_vm_config_rejects_concrete_cognition(tmp_path: Path) -> None:
    raw = json.loads(Path("configs/mvp_small.json").read_text(encoding="utf-8"))
    raw["subject_vm"] = {
        "enabled": True,
        "schema": SUBJECT_VM_STAGE1_SCHEMA,
        "node_state_width": 2,
        "interest_reward": 1.0,
        "regions": [],
    }
    path = tmp_path / "forbidden.json"
    path.write_text(json.dumps(raw), encoding="utf-8")
    with pytest.raises(ValueError, match="forbidden concrete cognition"):
        load_config(path)


def test_disabled_runtime_allocates_no_store_and_declares_inert_device_contract(
    tmp_path: Path,
) -> None:
    cfg = _small_config()
    simulation = Simulation(cfg, tmp_path / "disabled", backend="cpu")
    assert simulation.subject_vm.enabled is False
    assert simulation.subject_vm.storage is None
    assert simulation.subject_vm.snapshot_state() is None
    assert STAGE1_DEVICE_CONTRACT.host_authoritative is True
    assert STAGE1_DEVICE_CONTRACT.device_allocation is False
    assert STAGE1_DEVICE_CONTRACT.device_sync is False
    assert STAGE1_DEVICE_CONTRACT.consumes_random_numbers is False
    assert STAGE1_DEVICE_CONTRACT.affects_action_or_cost is False


def test_storage_lifecycle_inherits_structure_not_dynamic_state() -> None:
    cfg = _stage1_config()
    alive = np.array([True, True, False, False])
    entity_ids = np.array([11, 12, 0, 0], dtype=np.uint64)
    subject_ids = np.array([101, 102, 0, 0], dtype=np.uint64)
    runtime = SubjectVMRuntime.initialize(
        cfg,
        entity_capacity=4,
        active_rows=np.array([0, 1], dtype=np.int32),
        entity_ids=entity_ids,
        subject_ids=subject_ids,
    )
    storage = runtime.storage
    assert storage is not None
    storage.node_expressed[0, 0] = True
    storage.node_operator_id[0, 0] = 7
    storage.node_state[0, 0] = (0.25, -0.5, 0.75)
    storage.edge_expressed[0, 0] = True
    storage.edge_source[0, 0] = 0
    storage.edge_target[0, 0] = 1
    storage.edge_forward_gate[0, 0] = 0.5
    storage.plasticity_flags[0, 0] = 1

    entity_ids[2] = 13
    subject_ids[2] = 103
    alive[2] = True
    runtime.inherit_births(
        np.array([0], dtype=np.int32),
        np.array([2], dtype=np.int32),
        entity_ids,
        subject_ids,
    )
    assert storage.node_expressed[2, 0]
    assert storage.node_operator_id[2, 0] == 7
    assert storage.edge_expressed[2, 0]
    assert storage.edge_source[2, 0] == 0
    assert storage.edge_target[2, 0] == 1
    assert storage.plasticity_flags[2, 0] == 1
    assert np.all(storage.node_state[2] == 0.0)
    assert np.all(storage.eligibility_value[2] == 0.0)

    runtime.release_deaths(
        np.array([1], dtype=np.int32), entity_ids, subject_ids
    )
    alive[1] = False
    entity_ids[1] = 0
    subject_ids[1] = 0
    assert not storage.occupied[1]
    assert not np.any(storage.node_expressed[1])

    compact_rows(
        storage,
        source_rows=np.array([2], dtype=np.int32),
        destination_rows=np.array([3], dtype=np.int32),
    )
    alive[2] = False
    alive[3] = True
    entity_ids[3], entity_ids[2] = entity_ids[2], 0
    subject_ids[3], subject_ids[2] = subject_ids[2], 0
    runtime.validate_owners(alive, entity_ids, subject_ids)


def test_checkpoint_clone_and_missing_field_compatibility(tmp_path: Path) -> None:
    cfg = _small_config(subject_vm=_stage1_config())
    source = Simulation(cfg, tmp_path / "source", backend="cpu")
    storage = source.subject_vm.storage
    assert storage is not None
    row = int(np.flatnonzero(source.entities.alive)[0])
    storage.node_expressed[row, 0] = True
    storage.node_operator_id[row, 0] = 3
    storage.node_state[row, 0] = (1.0, 2.0, 3.0)
    storage.edge_expressed[row, 0] = True
    storage.edge_source[row, 0] = 0
    storage.edge_target[row, 0] = 1
    source._validate_invariants()

    checkpoint = tmp_path / "stage1.sechk"
    source.save_full_checkpoint(checkpoint)
    restored = Simulation.from_checkpoint(
        checkpoint, tmp_path / "restored", backend="cpu"
    )
    clone = restored.clone(tmp_path / "clone")
    assert restored.subject_vm.storage is not None
    assert clone.subject_vm.storage is not None
    for name in restored.subject_vm.storage.snapshot_array_names():
        assert np.array_equal(
            getattr(restored.subject_vm.storage, name),
            getattr(clone.subject_vm.storage, name),
        )
    assert np.array_equal(
        restored.subject_vm.storage.node_state,
        source.subject_vm.storage.node_state,
    )

    legacy_state = source._full_checkpoint_state()
    legacy_state.pop("subject_vm")
    compatibility = Simulation(cfg, tmp_path / "compatibility", backend="cpu")
    compatibility._restore_full_checkpoint_state(legacy_state)
    assert compatibility.subject_vm.restore_mode == "compatibility-empty-rebuild"
    assert compatibility.subject_vm.storage is not None
    assert not np.any(compatibility.subject_vm.storage.node_expressed)
    compatibility._validate_invariants()


def test_enabled_but_empty_runtime_is_exactly_neutral(tmp_path: Path) -> None:
    disabled = Simulation(_small_config(), tmp_path / "disabled", backend="cpu")
    enabled = Simulation(
        _small_config(subject_vm=_stage1_config()),
        tmp_path / "enabled",
        backend="cpu",
    )
    for _ in range(3):
        disabled.step()
        enabled.step()
    for name, value in vars(disabled.entities).items():
        if name == "cfg":
            continue
        other = getattr(enabled.entities, name)
        if isinstance(value, np.ndarray):
            assert np.array_equal(value, other), name
        else:
            assert value == other, name
    for owner in ("environment", "information", "social"):
        left = getattr(disabled, owner)
        right = getattr(enabled, owner)
        for name, value in vars(left).items():
            if name in {"cfg", "environment_process"}:
                continue
            other = getattr(right, name)
            if isinstance(value, np.ndarray):
                assert np.array_equal(value, other), f"{owner}.{name}"
    assert np.array_equal(disabled.action_counts, enabled.action_counts)
    assert disabled.total_births == enabled.total_births
    assert disabled.total_deaths == enabled.total_deaths
    assert disabled.tick == enabled.tick
    assert enabled.subject_vm.storage is not None
    assert not np.any(enabled.subject_vm.storage.node_expressed)
    assert not np.any(enabled.subject_vm.storage.edge_expressed)
    assert not np.any(enabled.subject_vm.storage.node_state)
    assert not np.any(enabled.subject_vm.storage.eligibility_value)


def test_regional_branch_prunes_subject_vm_rows(tmp_path: Path) -> None:
    cfg = _small_config(subject_vm=_stage1_config())
    source = Simulation(cfg, tmp_path / "branch-source", backend="cpu")
    storage = source.subject_vm.storage
    assert storage is not None
    alive_rows = np.flatnonzero(source.entities.alive)
    storage.node_expressed[alive_rows, 0] = True
    checkpoint = tmp_path / "branch-source.sechk"
    source.save_full_checkpoint(checkpoint)

    qualification = tmp_path / "qualification.json"
    qualification.write_text(
        json.dumps(
            {
                "schema": "test-qualification-v1",
                "passed": True,
                "epoch_id": "epoch-0-ecological-carriers",
                "contract_id": None,
                "source_checkpoint_sha256": _sha(checkpoint),
            }
        ),
        encoding="utf-8",
    )
    base = tmp_path / "epoch-base"
    freeze_epoch_base(
        registry_path=REGISTRY,
        epoch_id="epoch-0-ecological-carriers",
        checkpoint_path=checkpoint,
        qualification_path=qualification,
        output_dir=base,
    )
    _, record = read_checkpoint_bundle(checkpoint)
    entities = record["simulation"]["entities"]
    rows = np.flatnonzero(entities.alive)
    left = entities.x[rows] < record["config"].world.width * 0.5
    bounds = (
        (0.0, 0.0, 0.5, 1.0)
        if int(left.sum()) >= int((~left).sum())
        else (0.5, 0.0, 1.0, 1.0)
    )
    output = tmp_path / "regional.sechk"
    build_regional_branch(
        epoch_base=base,
        bounds=bounds,
        output_checkpoint=output,
        work_dir=tmp_path / "branch-work",
        minimum_entities=4,
    )
    _, branch = read_checkpoint_bundle(output)
    vm_payload = branch["simulation"]["subject_vm"]
    occupied = vm_payload["storage"]["arrays"]["occupied"]
    branch_alive = branch["simulation"]["entities"].alive
    assert np.array_equal(occupied, branch_alive)
    assert not np.any(
        vm_payload["storage"]["arrays"]["owner_entity_id"][~branch_alive]
    )
    assert np.all(
        vm_payload["storage"]["arrays"]["node_expressed"][branch_alive, 0]
    )
