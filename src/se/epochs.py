"""Epoch contracts and trusted regional branches.

Epochs separate long-horizon emergence from short mechanism development.  A
qualified full-world checkpoint may be frozen as the immutable base of a later
epoch.  Regional branches are explicit interventions: v1 preserves the full
world coordinate frame and environment fields while pruning the active entity
set, cross-boundary relations and delayed direct messages.  This avoids
pretending that a naively resized local grid is an exact continuation of the
parent world.
"""

from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
from typing import Any

import numpy as np

from . import __version__
from .checkpointing import read_checkpoint_bundle
from .evolution.lifecycle import plan_death_events
from .information import PendingMessageBatch, SignalEmissionScheduler
from .runtime.sim import Simulation


EPOCH_REGISTRY_SCHEMA = "se-epoch-registry-v1"
EPOCH_BASE_SCHEMA = "se-epoch-base-v1"
REGIONAL_BRANCH_SCHEMA = "regional-active-set-branch-v1"


def sha256_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_epoch_registry(path: str | Path) -> dict[str, Any]:
    source = Path(path)
    payload = json.loads(source.read_text(encoding="utf-8"))
    if payload.get("schema") != EPOCH_REGISTRY_SCHEMA:
        raise ValueError(
            f"unsupported epoch registry schema {payload.get('schema')!r}"
        )
    epochs = payload.get("epochs")
    if not isinstance(epochs, list) or not epochs:
        raise ValueError("epoch registry must contain a non-empty epochs list")
    ids: list[str] = []
    previous: str | None = None
    for index, epoch in enumerate(epochs):
        if not isinstance(epoch, dict):
            raise ValueError("each epoch registry entry must be an object")
        epoch_id = epoch.get("epoch_id")
        if not isinstance(epoch_id, str) or not epoch_id:
            raise ValueError("each epoch requires a non-empty epoch_id")
        if epoch_id in ids:
            raise ValueError(f"duplicate epoch_id {epoch_id!r}")
        ids.append(epoch_id)
        declared_previous = epoch.get("previous_epoch")
        if index == 0:
            if declared_previous not in {None, ""}:
                raise ValueError("the first epoch cannot declare a previous_epoch")
        elif declared_previous != previous:
            raise ValueError(
                f"epoch {epoch_id!r} must declare previous_epoch={previous!r}"
            )
        entry = epoch.get("entry_contract")
        if index > 0 and not isinstance(entry, dict):
            raise ValueError(f"epoch {epoch_id!r} requires an entry_contract")
        previous = epoch_id
    return payload


def epoch_by_id(registry: dict[str, Any], epoch_id: str) -> dict[str, Any]:
    for epoch in registry["epochs"]:
        if epoch["epoch_id"] == epoch_id:
            return epoch
    raise ValueError(f"unknown epoch_id {epoch_id!r}")


def freeze_epoch_base(
    *,
    registry_path: str | Path,
    epoch_id: str,
    checkpoint_path: str | Path,
    qualification_path: str | Path,
    output_dir: str | Path,
    label: str | None = None,
) -> dict[str, Any]:
    """Freeze one qualified full-world checkpoint as an immutable epoch base."""
    registry_file = Path(registry_path)
    registry = load_epoch_registry(registry_file)
    epoch = epoch_by_id(registry, epoch_id)
    checkpoint = Path(checkpoint_path)
    qualification_file = Path(qualification_path)
    qualification = json.loads(qualification_file.read_text(encoding="utf-8"))
    if qualification.get("passed") is not True:
        raise ValueError("epoch base qualification must explicitly pass")
    if qualification.get("epoch_id") != epoch_id:
        raise ValueError("qualification epoch_id does not match requested epoch")
    checkpoint_hash = sha256_file(checkpoint)
    if qualification.get("source_checkpoint_sha256") != checkpoint_hash:
        raise ValueError("qualification checkpoint SHA-256 does not match source")
    entry_contract = epoch.get("entry_contract") or {}
    contract_id = entry_contract.get("contract_id")
    if qualification.get("contract_id") != contract_id:
        raise ValueError("qualification contract_id does not match epoch registry")

    metadata, record = read_checkpoint_bundle(checkpoint)
    destination = Path(output_dir)
    if destination.exists() and any(destination.iterdir()):
        raise ValueError("epoch base output directory must be empty")
    destination.mkdir(parents=True, exist_ok=True)
    copied_checkpoint = destination / "base.sechk"
    shutil.copy2(checkpoint, copied_checkpoint)
    copied_hash = sha256_file(copied_checkpoint)
    if copied_hash != checkpoint_hash:
        raise RuntimeError("copied epoch checkpoint hash mismatch")
    copied_qualification = destination / "qualification.json"
    shutil.copy2(qualification_file, copied_qualification)
    copied_registry = destination / "epoch_registry.json"
    shutil.copy2(registry_file, copied_registry)

    manifest = {
        "schema": EPOCH_BASE_SCHEMA,
        "project_version": __version__,
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "epoch_id": epoch_id,
        "label": label or epoch.get("title", epoch_id),
        "previous_epoch": epoch.get("previous_epoch"),
        "checkpoint": {
            "path": "base.sechk",
            "sha256": copied_hash,
            "tick": int(metadata["tick"]),
            "state_sha256": metadata["state_sha256"],
            "config_sha256": metadata["config_sha256"],
            "execution_backend": metadata["execution_backend"],
            "requested_backend": metadata["requested_backend"],
        },
        "qualification": {
            "path": "qualification.json",
            "sha256": sha256_file(copied_qualification),
            "contract_id": contract_id,
        },
        "registry": {
            "path": "epoch_registry.json",
            "sha256": sha256_file(copied_registry),
        },
        "source_scope": {
            "full_world_checkpoint": True,
            "exact_replay_supported": True,
            "later_regional_branches_are_interventions": True,
        },
        "epoch_entry_contract": epoch.get("entry_contract"),
        "allowed_conclusions": epoch.get("allowed_conclusions", []),
        "prohibited_conclusions": epoch.get("prohibited_conclusions", []),
        "stored_config": asdict(record["config"]),
    }
    manifest_path = destination / "epoch_base.json"
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    lock = {
        "schema": "epoch-base-lock-v1",
        "files": [
            {
                "path": name,
                "size": (destination / name).stat().st_size,
                "sha256": sha256_file(destination / name),
            }
            for name in (
                "base.sechk",
                "qualification.json",
                "epoch_registry.json",
                "epoch_base.json",
            )
        ],
    }
    (destination / "EPOCH_BASE_LOCK.json").write_text(
        json.dumps(lock, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return manifest


def load_epoch_base(path: str | Path) -> tuple[Path, dict[str, Any]]:
    source = Path(path)
    manifest_path = source / "epoch_base.json" if source.is_dir() else source
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("schema") != EPOCH_BASE_SCHEMA:
        raise ValueError("unsupported epoch base manifest")
    root = manifest_path.parent
    checkpoint = root / manifest["checkpoint"]["path"]
    if sha256_file(checkpoint) != manifest["checkpoint"]["sha256"]:
        raise ValueError("epoch base checkpoint hash mismatch")
    return checkpoint, manifest


def _validate_bounds(bounds: tuple[float, float, float, float]) -> None:
    x0, y0, x1, y1 = bounds
    if not all(np.isfinite(value) for value in bounds):
        raise ValueError("regional bounds must be finite")
    if not (0.0 <= x0 < x1 <= 1.0 and 0.0 <= y0 < y1 <= 1.0):
        raise ValueError("regional bounds must satisfy 0 <= min < max <= 1")


def regional_branch_plan(
    *,
    epoch_base: str | Path,
    bounds: tuple[float, float, float, float],
) -> dict[str, Any]:
    """Describe one active-set region before mutating any checkpoint state."""
    _validate_bounds(bounds)
    checkpoint, base = load_epoch_base(epoch_base)
    metadata, record = read_checkpoint_bundle(checkpoint)
    state = record["simulation"]
    cfg = record["config"]
    entities = state["entities"]
    x0, y0, x1, y1 = bounds
    xmin, xmax = x0 * cfg.world.width, x1 * cfg.world.width
    ymin, ymax = y0 * cfg.world.height, y1 * cfg.world.height
    alive = np.asarray(entities.alive, dtype=bool)
    selected = alive & (entities.x >= xmin) & (entities.x < xmax) & (entities.y >= ymin) & (entities.y < ymax)
    outside = alive & ~selected
    social = state["social"]
    target = np.asarray(social.target, dtype=np.int32)
    valid = target >= 0
    safe_target = np.where(valid, target, 0)
    inside_to_outside = selected[:, None] & valid & outside[safe_target]
    outside_to_inside = outside[:, None] & valid & selected[safe_target]
    selected_rows = np.flatnonzero(selected).astype(np.int32)
    selected_cells = (
        np.floor(entities.y[selected_rows] / cfg.world.height * cfg.world.grid_y).astype(np.int64)
        * cfg.world.grid_x
        + np.floor(entities.x[selected_rows] / cfg.world.width * cfg.world.grid_x).astype(np.int64)
        if selected_rows.size
        else np.empty(0, dtype=np.int64)
    )
    environment = state["environment"]
    resource_flat = np.asarray(environment.resources).reshape(4, -1)
    local_resource_mean = (
        resource_flat[:, selected_cells].mean(axis=1).tolist()
        if selected_cells.size
        else [0.0] * 4
    )
    selected_groups = np.unique(np.asarray(social.group_id)[selected])
    selected_groups = selected_groups[selected_groups != 0]
    selected_lineages = np.unique(np.asarray(entities.lineage_id)[selected])
    report = {
        "schema": "regional-active-set-plan-v1",
        "project_version": __version__,
        "epoch_id": base["epoch_id"],
        "source_checkpoint_sha256": base["checkpoint"]["sha256"],
        "source_tick": int(metadata["tick"]),
        "normalized_bounds": {
            "x_min": x0,
            "y_min": y0,
            "x_max": x1,
            "y_max": y1,
        },
        "world_bounds": {
            "x_min": xmin,
            "y_min": ymin,
            "x_max": xmax,
            "y_max": ymax,
        },
        "source_alive": int(alive.sum()),
        "selected_alive": int(selected.sum()),
        "removed_alive": int(outside.sum()),
        "selected_alive_fraction": float(selected.sum() / max(int(alive.sum()), 1)),
        "selected_lineage_count": int(selected_lineages.size),
        "selected_group_token_count": int(selected_groups.size),
        "inside_to_outside_relation_edges": int(inside_to_outside.sum()),
        "outside_to_inside_relation_edges": int(outside_to_inside.sum()),
        "local_resource_mean": local_resource_mean,
        "branch_semantics": {
            "schema": REGIONAL_BRANCH_SCHEMA,
            "full_environment_coordinate_frame_preserved": True,
            "outside_entities_pruned": True,
            "cross_boundary_relations_removed": True,
            "cross_boundary_pending_messages_removed": True,
            "pending_field_emissions_cleared": True,
            "physical_grid_cropped": False,
            "exact_full_world_continuation": False,
        },
        "interpretation_boundary": (
            "This branch reduces the active entity set while preserving the full "
            "environment coordinate frame. It is an intervention for local mechanism "
            "development, not an unbiased miniature of the parent world or evidence "
            "that full-world emergence would continue unchanged."
        ),
    }
    return report


def _filter_pending_messages(
    pending: list[PendingMessageBatch], selected_ids: np.ndarray
) -> list[PendingMessageBatch]:
    allowed = np.asarray(selected_ids, dtype=np.uint64)
    result: list[PendingMessageBatch] = []
    for batch in pending:
        keep = np.isin(batch.source_ids, allowed) & np.isin(batch.receiver_ids, allowed)
        if np.any(keep):
            result.append(
                PendingMessageBatch(
                    source_ids=batch.source_ids[keep].copy(),
                    receiver_ids=batch.receiver_ids[keep].copy(),
                    payloads=batch.payloads[keep].copy(),
                    confidences=batch.confidences[keep].copy(),
                    emit_tick=int(batch.emit_tick),
                    receive_tick=int(batch.receive_tick),
                )
            )
    return result


def build_regional_branch(
    *,
    epoch_base: str | Path,
    bounds: tuple[float, float, float, float],
    output_checkpoint: str | Path,
    work_dir: str | Path,
    minimum_entities: int = 8,
) -> dict[str, Any]:
    """Build a trusted regional active-set checkpoint from an epoch base."""
    plan = regional_branch_plan(epoch_base=epoch_base, bounds=bounds)
    if plan["selected_alive"] < int(minimum_entities):
        raise ValueError(
            f"regional branch selected {plan['selected_alive']} entities; "
            f"minimum is {minimum_entities}"
        )
    checkpoint, base = load_epoch_base(epoch_base)
    work = Path(work_dir)
    work.mkdir(parents=True, exist_ok=True)
    simulation = Simulation.from_checkpoint(checkpoint, work, backend="cpu")
    ent = simulation.entities
    cfg = simulation.cfg
    x0, y0, x1, y1 = bounds
    inside = (
        ent.alive
        & (ent.x >= x0 * cfg.world.width)
        & (ent.x < x1 * cfg.world.width)
        & (ent.y >= y0 * cfg.world.height)
        & (ent.y < y1 * cfg.world.height)
    )
    outside = np.flatnonzero(ent.alive & ~inside).astype(np.int32)
    selected_ids = ent.entity_id[inside].copy()
    if outside.size:
        simulation.subjects.mark_dead(outside, simulation.tick)
        ent.energy[outside] = 0.0
        death_plan = plan_death_events(
            active=outside,
            entity_ids=ent.entity_id,
            primary_subject_ids=ent.primary_subject_id,
            energy=ent.energy,
            integrity=ent.integrity,
            age=ent.age,
            max_age=cfg.entities.max_age,
            tick=simulation.tick,
        )
        ent.commit_deaths(death_plan)
        simulation.autonomy_restored[outside] = False
        simulation.autonomy_observation_cohort[outside] = False
        simulation.social.reset_entities(outside)
        simulation.social.clear_dead_targets(ent.alive)
        if cfg.knowledge.enabled:
            simulation.knowledge.remove_dead_holders(
                ent.alive, ent.primary_subject_id
            )
    simulation.information.pending_messages = _filter_pending_messages(
        simulation.information.pending_messages, selected_ids
    )
    simulation.signal_scheduler = SignalEmissionScheduler(
        simulation.signal_scheduler.channel_count,
        simulation.signal_scheduler.flush_periods,
    )
    simulation.social.mark_group_labels_dirty("regional-active-set-branch")
    simulation.spatial.build(ent.x, ent.y, ent.alive)
    simulation.subjects.update_groups(
        ent.alive, simulation.social.group_id, simulation.tick
    )
    provenance = {
        "schema": REGIONAL_BRANCH_SCHEMA,
        "epoch_id": base["epoch_id"],
        "source_checkpoint_sha256": base["checkpoint"]["sha256"],
        "source_tick": int(simulation.tick),
        "normalized_bounds": plan["normalized_bounds"],
        "selected_entity_ids_sha256": hashlib.sha256(
            np.asarray(np.sort(selected_ids), dtype=np.uint64).tobytes()
        ).hexdigest(),
        "selected_alive": int(ent.alive.sum()),
        "removed_alive": int(outside.size),
        "biological_death_counters_changed": False,
        "full_environment_coordinate_frame_preserved": True,
        "physical_grid_cropped": False,
        "interpretation_boundary": plan["interpretation_boundary"],
    }
    simulation.checkpoint_lineage.append(provenance)
    simulation.intervention_history.append(provenance)
    simulation._validate_invariants()
    output = Path(output_checkpoint)
    output.parent.mkdir(parents=True, exist_ok=True)
    simulation.save_full_checkpoint(output)
    report = {
        **plan,
        "output_checkpoint": str(output),
        "output_checkpoint_sha256": sha256_file(output),
        "selected_entity_ids_sha256": provenance["selected_entity_ids_sha256"],
        "branch_ready": True,
    }
    report_path = output.with_suffix(output.suffix + ".region.json")
    report_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return report
