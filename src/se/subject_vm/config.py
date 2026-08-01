"""Versioned Stage-1 configuration for the partitioned unified Subject Graph VM.

The configuration describes only generic capacity and scheduling priors.  It
must never carry designer-defined cognitive values, partner classes, social
roles, or subjective reward semantics.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

SUBJECT_VM_DISABLED_SCHEMA = "disabled"
SUBJECT_VM_STAGE1_SCHEMA = "partitioned-subject-graph-vm-stage1-v1"
SUBJECT_VM_REGION_NAMES = (
    "fast-sensorimotor",
    "persistent-state",
    "delayed-association",
    "integrative-drive",
)

# These names are rejected wherever they occur in the Subject VM section.
# Unknown fields are rejected separately; this explicit set produces a clear
# scientific-boundary error rather than a generic constructor failure.
FORBIDDEN_COGNITIVE_FIELDS = frozenset(
    {
        "trust",
        "friend",
        "enemy",
        "betrayal",
        "knowledge_value",
        "interest_reward",
        "material_interest",
        "knowledge_interest",
        "protection_value",
        "conflict_value",
        "opportunity_cost_value",
        "group_bonus",
        "reward",
        "subjective_value",
        "valence",
    }
)


@dataclass(frozen=True)
class SubjectVMRegionConfig:
    """One role-neutral computational partition reservation."""

    name: str
    node_capacity: int
    edge_capacity: int
    update_period: int


@dataclass(frozen=True)
class SubjectVMConfig:
    """Disabled-by-default Stage-1 graph capacity contract."""

    enabled: bool = False
    schema: str = SUBJECT_VM_DISABLED_SCHEMA
    node_state_width: int = 0
    inherit_structure_on_birth: bool = True
    regions: tuple[SubjectVMRegionConfig, ...] = ()

    @property
    def total_node_capacity(self) -> int:
        return sum(int(region.node_capacity) for region in self.regions)

    @property
    def total_edge_capacity(self) -> int:
        return sum(int(region.edge_capacity) for region in self.regions)


def _scan_forbidden_keys(value: Any, path: str = "subject_vm") -> None:
    if isinstance(value, Mapping):
        for key, child in value.items():
            normalized = str(key).strip().lower()
            if normalized in FORBIDDEN_COGNITIVE_FIELDS:
                raise ValueError(
                    f"{path}.{key} is forbidden concrete cognition in Subject VM config"
                )
            _scan_forbidden_keys(child, f"{path}.{key}")
    elif isinstance(value, (list, tuple)):
        for index, child in enumerate(value):
            _scan_forbidden_keys(child, f"{path}[{index}]")


def load_subject_vm_config(raw: Mapping[str, Any] | None) -> SubjectVMConfig:
    """Parse an optional Subject VM section without inventing legacy fields."""
    if raw is None:
        return SubjectVMConfig()
    _scan_forbidden_keys(raw)
    allowed = {
        "enabled",
        "schema",
        "node_state_width",
        "inherit_structure_on_birth",
        "regions",
    }
    unknown = sorted(set(raw) - allowed)
    if unknown:
        raise ValueError(f"unknown subject_vm configuration fields: {unknown}")
    region_values = raw.get("regions", ())
    if not isinstance(region_values, (list, tuple)):
        raise ValueError("subject_vm.regions must be a list")
    regions: list[SubjectVMRegionConfig] = []
    for index, item in enumerate(region_values):
        if not isinstance(item, Mapping):
            raise ValueError(f"subject_vm.regions[{index}] must be an object")
        region_allowed = {"name", "node_capacity", "edge_capacity", "update_period"}
        region_unknown = sorted(set(item) - region_allowed)
        if region_unknown:
            raise ValueError(
                f"unknown subject_vm.regions[{index}] fields: {region_unknown}"
            )
        try:
            regions.append(
                SubjectVMRegionConfig(
                    name=str(item["name"]),
                    node_capacity=int(item["node_capacity"]),
                    edge_capacity=int(item["edge_capacity"]),
                    update_period=int(item["update_period"]),
                )
            )
        except KeyError as exc:
            raise ValueError(
                f"subject_vm.regions[{index}] is missing {exc.args[0]!r}"
            ) from exc
    cfg = SubjectVMConfig(
        enabled=bool(raw.get("enabled", False)),
        schema=str(raw.get("schema", SUBJECT_VM_DISABLED_SCHEMA)),
        node_state_width=int(raw.get("node_state_width", 0)),
        inherit_structure_on_birth=bool(
            raw.get("inherit_structure_on_birth", True)
        ),
        regions=tuple(regions),
    )
    validate_subject_vm_config(cfg)
    return cfg


def validate_subject_vm_config(cfg: SubjectVMConfig) -> None:
    """Validate the frozen Stage-1 capacity and neutrality contract."""
    if cfg.enabled:
        if cfg.schema != SUBJECT_VM_STAGE1_SCHEMA:
            raise ValueError(
                "enabled subject_vm requires schema "
                f"{SUBJECT_VM_STAGE1_SCHEMA!r}"
            )
        if tuple(region.name for region in cfg.regions) != SUBJECT_VM_REGION_NAMES:
            raise ValueError(
                "enabled subject_vm regions must match the frozen four-region order"
            )
        if cfg.node_state_width <= 0 or cfg.node_state_width > 64:
            raise ValueError(
                "enabled subject_vm.node_state_width must be in [1, 64]"
            )
        for region in cfg.regions:
            if region.node_capacity <= 0:
                raise ValueError(
                    f"subject_vm region {region.name!r} needs positive node_capacity"
                )
            if region.edge_capacity < 0:
                raise ValueError(
                    f"subject_vm region {region.name!r} edge_capacity cannot be negative"
                )
            if region.update_period <= 0 or region.update_period > 65535:
                raise ValueError(
                    f"subject_vm region {region.name!r} update_period must be in [1, 65535]"
                )
        if cfg.total_node_capacity > 65535:
            raise ValueError("subject_vm total node capacity cannot exceed 65535")
        if cfg.total_edge_capacity > 65535:
            raise ValueError("subject_vm total edge capacity cannot exceed 65535")
    else:
        if cfg.schema != SUBJECT_VM_DISABLED_SCHEMA:
            raise ValueError("disabled subject_vm requires schema 'disabled'")
        if cfg.node_state_width != 0 or cfg.regions:
            raise ValueError(
                "disabled subject_vm requires zero state width and no region reservations"
            )
        if not cfg.inherit_structure_on_birth:
            raise ValueError(
                "disabled subject_vm must retain the canonical inheritance default"
            )


def strip_disabled_subject_vm_section(payload: dict[str, Any]) -> dict[str, Any]:
    """Remove only the exact inert Stage-1 extension from a config payload.

    The operation is in-place and returned for chaining.  It deliberately does
    not normalize any older extension, so checkpoint hashes created before
    v0.108 remain reproducible.
    """
    section = payload.get("subject_vm")
    if not isinstance(section, Mapping):
        return payload
    if (
        section.get("enabled") is False
        and section.get("schema") == SUBJECT_VM_DISABLED_SCHEMA
        and int(section.get("node_state_width", 0)) == 0
        and section.get("inherit_structure_on_birth") is True
        and tuple(section.get("regions", ())) == ()
    ):
        payload.pop("subject_vm", None)
    return payload


__all__ = [
    "FORBIDDEN_COGNITIVE_FIELDS",
    "SUBJECT_VM_DISABLED_SCHEMA",
    "SUBJECT_VM_REGION_NAMES",
    "SUBJECT_VM_STAGE1_SCHEMA",
    "SubjectVMConfig",
    "SubjectVMRegionConfig",
    "load_subject_vm_config",
    "strip_disabled_subject_vm_section",
    "validate_subject_vm_config",
]
