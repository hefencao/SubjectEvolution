"""Versioned configuration for the partitioned unified Subject Graph VM.

The configuration describes generic capacity, scheduling, bounded routing, and
trace-token contracts only.  It must never carry designer-defined cognitive
values, partner classes, social roles, or subjective reward semantics.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

SUBJECT_VM_DISABLED_SCHEMA = "disabled"
SUBJECT_VM_STAGE1_SCHEMA = "partitioned-subject-graph-vm-stage1-v1"
SUBJECT_VM_STAGE2_SCHEMA = "partitioned-subject-graph-vm-stage2-activation-v1"
SUBJECT_VM_STAGE3_SCHEMA = "partitioned-subject-graph-vm-stage3-token-trace-v1"
SUBJECT_VM_STAGE3B_SCHEMA = "partitioned-subject-graph-vm-stage3b-local-eligibility-v1"
SUBJECT_VM_STAGE3B2_SCHEMA = "partitioned-subject-graph-vm-stage3b2-delayed-association-v1"
SUBJECT_VM_ACTIVATION_DISABLED_SCHEMA = "disabled"
SUBJECT_VM_ACTIVATION_SCHEMA = "bounded-phased-forward-routing-v1"
SUBJECT_VM_INPUT_PORT_SCHEMA = "objective-entity-input-ports-v1"
SUBJECT_VM_OUTPUT_PORT_SCHEMA = "action-potential-output-ports-v1"
SUBJECT_VM_TRACE_DISABLED_SCHEMA = "disabled"
SUBJECT_VM_TRACE_SCHEMA = "continuous-internal-token-objective-event-v1"
SUBJECT_VM_OBJECTIVE_EVENT_SCHEMA = "objective-action-state-delta-v1"
SUBJECT_VM_ELIGIBILITY_DISABLED_SCHEMA = "disabled"
SUBJECT_VM_ELIGIBILITY_SCHEMA = "local-decaying-activity-eligibility-v1"
SUBJECT_VM_ASSOCIATION_DISABLED_SCHEMA = "disabled"
SUBJECT_VM_ASSOCIATION_SCHEMA = "bounded-delayed-token-similarity-candidate-v1"
SUBJECT_VM_REGION_NAMES = (
    "fast-sensorimotor",
    "persistent-state",
    "delayed-association",
    "integrative-drive",
)

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
        "polarity",
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
class SubjectVMActivationConfig:
    """Stage-2 bounded forward-routing contract."""

    schema: str = SUBJECT_VM_ACTIVATION_DISABLED_SCHEMA
    input_port_schema: str = SUBJECT_VM_ACTIVATION_DISABLED_SCHEMA
    output_port_schema: str = SUBJECT_VM_ACTIVATION_DISABLED_SCHEMA
    activation_clip: float = 0.0
    output_clip: float = 0.0


@dataclass(frozen=True)
class SubjectVMTraceConfig:
    """Stage-3A compact internal-token and objective-event contract.

    The token is a continuous graph-produced readout.  It is not a
    cryptographic hash, a designer-defined concept, reward, valence, credit
    rule, or persistent node/edge execution path.
    """

    schema: str = SUBJECT_VM_TRACE_DISABLED_SCHEMA
    event_schema: str = SUBJECT_VM_TRACE_DISABLED_SCHEMA
    token_width: int = 0
    token_clip: float = 0.0
    capacity_per_subject: int = 0
    retention_ticks: int = 0


@dataclass(frozen=True)
class SubjectVMEligibilityConfig:
    """Stage-3B-1 short-lived local activity carrier.

    Eligibility is unsigned with respect to world outcomes: values retain the
    signed local activation/transmission selected by graph gates, but no event
    field is assigned positive or negative meaning and no parameter is updated.
    """

    schema: str = SUBJECT_VM_ELIGIBILITY_DISABLED_SCHEMA
    decay: float = 0.0
    clip: float = 0.0
    max_age_ticks: int = 0


@dataclass(frozen=True)
class SubjectVMAssociationConfig:
    """Stage-3B-2 bounded delayed content-address candidate contract.

    One graph-produced token coordinate is a role-neutral request gate.  It is
    excluded from similarity.  Selection records only a historical event
    reference, delay and score; it cannot assign value or update parameters.
    """

    schema: str = SUBJECT_VM_ASSOCIATION_DISABLED_SCHEMA
    request_token_port: int = -1
    request_threshold: float = 0.0
    similarity_threshold: float = 0.0
    min_delay_ticks: int = 0
    max_delay_ticks: int = 0


@dataclass(frozen=True)
class SubjectVMConfig:
    """Disabled-by-default partitioned graph capacity contract."""

    enabled: bool = False
    schema: str = SUBJECT_VM_DISABLED_SCHEMA
    node_state_width: int = 0
    inherit_structure_on_birth: bool = True
    regions: tuple[SubjectVMRegionConfig, ...] = ()
    activation: SubjectVMActivationConfig = SubjectVMActivationConfig()
    trace: SubjectVMTraceConfig = SubjectVMTraceConfig()
    eligibility: SubjectVMEligibilityConfig = SubjectVMEligibilityConfig()
    association: SubjectVMAssociationConfig = SubjectVMAssociationConfig()

    @property
    def total_node_capacity(self) -> int:
        return sum(int(region.node_capacity) for region in self.regions)

    @property
    def total_edge_capacity(self) -> int:
        return sum(int(region.edge_capacity) for region in self.regions)

    @property
    def activation_enabled(self) -> bool:
        return self.schema in {
            SUBJECT_VM_STAGE2_SCHEMA,
            SUBJECT_VM_STAGE3_SCHEMA,
            SUBJECT_VM_STAGE3B_SCHEMA,
            SUBJECT_VM_STAGE3B2_SCHEMA,
        }

    @property
    def trace_enabled(self) -> bool:
        return self.schema in {
            SUBJECT_VM_STAGE3_SCHEMA,
            SUBJECT_VM_STAGE3B_SCHEMA,
            SUBJECT_VM_STAGE3B2_SCHEMA,
        }

    @property
    def eligibility_enabled(self) -> bool:
        return self.schema in {SUBJECT_VM_STAGE3B_SCHEMA, SUBJECT_VM_STAGE3B2_SCHEMA}

    @property
    def association_enabled(self) -> bool:
        return self.schema == SUBJECT_VM_STAGE3B2_SCHEMA


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


def _load_activation_config(raw: Any) -> SubjectVMActivationConfig:
    if raw is None:
        return SubjectVMActivationConfig()
    if not isinstance(raw, Mapping):
        raise ValueError("subject_vm.activation must be an object")
    allowed = {
        "schema",
        "input_port_schema",
        "output_port_schema",
        "activation_clip",
        "output_clip",
    }
    unknown = sorted(set(raw) - allowed)
    if unknown:
        raise ValueError(f"unknown subject_vm.activation fields: {unknown}")
    return SubjectVMActivationConfig(
        schema=str(raw.get("schema", SUBJECT_VM_ACTIVATION_DISABLED_SCHEMA)),
        input_port_schema=str(
            raw.get("input_port_schema", SUBJECT_VM_ACTIVATION_DISABLED_SCHEMA)
        ),
        output_port_schema=str(
            raw.get("output_port_schema", SUBJECT_VM_ACTIVATION_DISABLED_SCHEMA)
        ),
        activation_clip=float(raw.get("activation_clip", 0.0)),
        output_clip=float(raw.get("output_clip", 0.0)),
    )


def _load_trace_config(raw: Any) -> SubjectVMTraceConfig:
    if raw is None:
        return SubjectVMTraceConfig()
    if not isinstance(raw, Mapping):
        raise ValueError("subject_vm.trace must be an object")
    allowed = {
        "schema",
        "event_schema",
        "token_width",
        "token_clip",
        "capacity_per_subject",
        "retention_ticks",
    }
    unknown = sorted(set(raw) - allowed)
    if unknown:
        raise ValueError(f"unknown subject_vm.trace fields: {unknown}")
    return SubjectVMTraceConfig(
        schema=str(raw.get("schema", SUBJECT_VM_TRACE_DISABLED_SCHEMA)),
        event_schema=str(raw.get("event_schema", SUBJECT_VM_TRACE_DISABLED_SCHEMA)),
        token_width=int(raw.get("token_width", 0)),
        token_clip=float(raw.get("token_clip", 0.0)),
        capacity_per_subject=int(raw.get("capacity_per_subject", 0)),
        retention_ticks=int(raw.get("retention_ticks", 0)),
    )


def _load_eligibility_config(raw: Any) -> SubjectVMEligibilityConfig:
    if raw is None:
        return SubjectVMEligibilityConfig()
    if not isinstance(raw, Mapping):
        raise ValueError("subject_vm.eligibility must be an object")
    allowed = {"schema", "decay", "clip", "max_age_ticks"}
    unknown = sorted(set(raw) - allowed)
    if unknown:
        raise ValueError(f"unknown subject_vm.eligibility fields: {unknown}")
    return SubjectVMEligibilityConfig(
        schema=str(raw.get("schema", SUBJECT_VM_ELIGIBILITY_DISABLED_SCHEMA)),
        decay=float(raw.get("decay", 0.0)),
        clip=float(raw.get("clip", 0.0)),
        max_age_ticks=int(raw.get("max_age_ticks", 0)),
    )


def _load_association_config(raw: Any) -> SubjectVMAssociationConfig:
    if raw is None:
        return SubjectVMAssociationConfig()
    if not isinstance(raw, Mapping):
        raise ValueError("subject_vm.association must be an object")
    allowed = {
        "schema",
        "request_token_port",
        "request_threshold",
        "similarity_threshold",
        "min_delay_ticks",
        "max_delay_ticks",
    }
    unknown = sorted(set(raw) - allowed)
    if unknown:
        raise ValueError(f"unknown subject_vm.association fields: {unknown}")
    return SubjectVMAssociationConfig(
        schema=str(raw.get("schema", SUBJECT_VM_ASSOCIATION_DISABLED_SCHEMA)),
        request_token_port=int(raw.get("request_token_port", -1)),
        request_threshold=float(raw.get("request_threshold", 0.0)),
        similarity_threshold=float(raw.get("similarity_threshold", 0.0)),
        min_delay_ticks=int(raw.get("min_delay_ticks", 0)),
        max_delay_ticks=int(raw.get("max_delay_ticks", 0)),
    )


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
        "activation",
        "trace",
        "eligibility",
        "association",
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
        allowed_region = {"name", "node_capacity", "edge_capacity", "update_period"}
        unknown_region = sorted(set(item) - allowed_region)
        if unknown_region:
            raise ValueError(
                f"unknown subject_vm.regions[{index}] fields: {unknown_region}"
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
        inherit_structure_on_birth=bool(raw.get("inherit_structure_on_birth", True)),
        regions=tuple(regions),
        activation=_load_activation_config(raw.get("activation")),
        trace=_load_trace_config(raw.get("trace")),
        eligibility=_load_eligibility_config(raw.get("eligibility")),
        association=_load_association_config(raw.get("association")),
    )
    validate_subject_vm_config(cfg)
    return cfg


def _validate_disabled_activation(cfg: SubjectVMActivationConfig) -> None:
    if cfg != SubjectVMActivationConfig():
        raise ValueError("inactive subject_vm activation requires exact disabled defaults")


def _validate_disabled_trace(cfg: SubjectVMTraceConfig) -> None:
    if cfg != SubjectVMTraceConfig():
        raise ValueError("inactive subject_vm trace requires exact disabled defaults")


def _validate_disabled_eligibility(cfg: SubjectVMEligibilityConfig) -> None:
    if cfg != SubjectVMEligibilityConfig():
        raise ValueError(
            "inactive subject_vm eligibility requires exact disabled defaults"
        )


def _validate_disabled_association(cfg: SubjectVMAssociationConfig) -> None:
    if cfg != SubjectVMAssociationConfig():
        raise ValueError(
            "inactive subject_vm association requires exact disabled defaults"
        )


def _validate_activation(cfg: SubjectVMActivationConfig) -> None:
    if cfg.schema != SUBJECT_VM_ACTIVATION_SCHEMA:
        raise ValueError(
            f"active subject_vm requires activation schema {SUBJECT_VM_ACTIVATION_SCHEMA!r}"
        )
    if cfg.input_port_schema != SUBJECT_VM_INPUT_PORT_SCHEMA:
        raise ValueError(
            f"active subject_vm requires input ports {SUBJECT_VM_INPUT_PORT_SCHEMA!r}"
        )
    if cfg.output_port_schema != SUBJECT_VM_OUTPUT_PORT_SCHEMA:
        raise ValueError(
            f"active subject_vm requires output ports {SUBJECT_VM_OUTPUT_PORT_SCHEMA!r}"
        )
    if not 0.0 < cfg.activation_clip <= 64.0:
        raise ValueError("subject_vm activation_clip must be in (0, 64]")
    if not 0.0 < cfg.output_clip <= 64.0:
        raise ValueError("subject_vm output_clip must be in (0, 64]")


def _validate_trace(cfg: SubjectVMTraceConfig) -> None:
    if cfg.schema != SUBJECT_VM_TRACE_SCHEMA:
        raise ValueError(
            f"Stage-3 subject_vm requires trace schema {SUBJECT_VM_TRACE_SCHEMA!r}"
        )
    if cfg.event_schema != SUBJECT_VM_OBJECTIVE_EVENT_SCHEMA:
        raise ValueError(
            "Stage-3 subject_vm requires the approved objective event schema"
        )
    if not 1 <= cfg.token_width <= 64:
        raise ValueError("subject_vm trace token_width must be in [1, 64]")
    if not 0.0 < cfg.token_clip <= 64.0:
        raise ValueError("subject_vm trace token_clip must be in (0, 64]")
    if not 1 <= cfg.capacity_per_subject <= 65535:
        raise ValueError("subject_vm trace capacity_per_subject must be in [1, 65535]")
    if not 1 <= cfg.retention_ticks <= 2**31 - 1:
        raise ValueError("subject_vm trace retention_ticks must be positive")


def _validate_eligibility(cfg: SubjectVMEligibilityConfig) -> None:
    if cfg.schema != SUBJECT_VM_ELIGIBILITY_SCHEMA:
        raise ValueError(
            f"Stage-3B subject_vm requires eligibility schema {SUBJECT_VM_ELIGIBILITY_SCHEMA!r}"
        )
    if not 0.0 <= cfg.decay < 1.0:
        raise ValueError("subject_vm eligibility decay must be in [0, 1)")
    if not 0.0 < cfg.clip <= 64.0:
        raise ValueError("subject_vm eligibility clip must be in (0, 64]")
    if not 1 <= cfg.max_age_ticks <= 65535:
        raise ValueError("subject_vm eligibility max_age_ticks must be in [1, 65535]")


def _validate_association(
    cfg: SubjectVMAssociationConfig, *, trace: SubjectVMTraceConfig, eligibility: SubjectVMEligibilityConfig
) -> None:
    if cfg.schema != SUBJECT_VM_ASSOCIATION_SCHEMA:
        raise ValueError(
            f"Stage-3B-2 subject_vm requires association schema {SUBJECT_VM_ASSOCIATION_SCHEMA!r}"
        )
    if not 0 <= cfg.request_token_port < trace.token_width:
        raise ValueError("subject_vm association request_token_port is outside token width")
    if not 0.0 < cfg.request_threshold <= trace.token_clip:
        raise ValueError(
            "subject_vm association request_threshold must be in (0, token_clip]"
        )
    if not -1.0 <= cfg.similarity_threshold <= 1.0:
        raise ValueError(
            "subject_vm association similarity_threshold must be in [-1, 1]"
        )
    if cfg.min_delay_ticks < 1:
        raise ValueError("subject_vm association min_delay_ticks must be at least 1")
    if cfg.max_delay_ticks < cfg.min_delay_ticks:
        raise ValueError(
            "subject_vm association max_delay_ticks must be >= min_delay_ticks"
        )
    if cfg.max_delay_ticks > trace.retention_ticks:
        raise ValueError(
            "subject_vm association horizon cannot exceed trace retention"
        )
    if cfg.max_delay_ticks > eligibility.max_age_ticks:
        raise ValueError(
            "subject_vm association horizon cannot exceed local eligibility horizon"
        )


def validate_subject_vm_config(cfg: SubjectVMConfig) -> None:
    """Validate the frozen Stage-1/2/3A/3B-1/3B-2 contracts."""
    if cfg.enabled:
        if cfg.schema not in {
            SUBJECT_VM_STAGE1_SCHEMA,
            SUBJECT_VM_STAGE2_SCHEMA,
            SUBJECT_VM_STAGE3_SCHEMA,
            SUBJECT_VM_STAGE3B_SCHEMA,
            SUBJECT_VM_STAGE3B2_SCHEMA,
        }:
            raise ValueError("enabled subject_vm requires a supported stage schema")
        if tuple(region.name for region in cfg.regions) != SUBJECT_VM_REGION_NAMES:
            raise ValueError(
                "enabled subject_vm regions must match the frozen four-region order"
            )
        if cfg.node_state_width <= 0 or cfg.node_state_width > 64:
            raise ValueError("enabled subject_vm.node_state_width must be in [1, 64]")
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
        if cfg.schema == SUBJECT_VM_STAGE1_SCHEMA:
            _validate_disabled_activation(cfg.activation)
            _validate_disabled_trace(cfg.trace)
            _validate_disabled_eligibility(cfg.eligibility)
            _validate_disabled_association(cfg.association)
        else:
            _validate_activation(cfg.activation)
            if cfg.schema == SUBJECT_VM_STAGE2_SCHEMA:
                _validate_disabled_trace(cfg.trace)
                _validate_disabled_eligibility(cfg.eligibility)
                _validate_disabled_association(cfg.association)
            else:
                _validate_trace(cfg.trace)
                if cfg.schema == SUBJECT_VM_STAGE3_SCHEMA:
                    _validate_disabled_eligibility(cfg.eligibility)
                    _validate_disabled_association(cfg.association)
                else:
                    _validate_eligibility(cfg.eligibility)
                    if cfg.schema == SUBJECT_VM_STAGE3B_SCHEMA:
                        _validate_disabled_association(cfg.association)
                    else:
                        _validate_association(
                            cfg.association,
                            trace=cfg.trace,
                            eligibility=cfg.eligibility,
                        )
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
        _validate_disabled_activation(cfg.activation)
        _validate_disabled_trace(cfg.trace)
        _validate_disabled_eligibility(cfg.eligibility)
        _validate_disabled_association(cfg.association)


def _disabled_activation_payload(value: Any) -> bool:
    if value is None:
        return True
    if not isinstance(value, Mapping):
        return False
    return (
        value.get("schema") == SUBJECT_VM_ACTIVATION_DISABLED_SCHEMA
        and value.get("input_port_schema") == SUBJECT_VM_ACTIVATION_DISABLED_SCHEMA
        and value.get("output_port_schema") == SUBJECT_VM_ACTIVATION_DISABLED_SCHEMA
        and float(value.get("activation_clip", 0.0)) == 0.0
        and float(value.get("output_clip", 0.0)) == 0.0
    )


def _disabled_trace_payload(value: Any) -> bool:
    if value is None:
        return True
    if not isinstance(value, Mapping):
        return False
    return (
        value.get("schema") == SUBJECT_VM_TRACE_DISABLED_SCHEMA
        and value.get("event_schema") == SUBJECT_VM_TRACE_DISABLED_SCHEMA
        and int(value.get("token_width", 0)) == 0
        and float(value.get("token_clip", 0.0)) == 0.0
        and int(value.get("capacity_per_subject", 0)) == 0
        and int(value.get("retention_ticks", 0)) == 0
    )


def _disabled_eligibility_payload(value: Any) -> bool:
    if value is None:
        return True
    if not isinstance(value, Mapping):
        return False
    return (
        value.get("schema") == SUBJECT_VM_ELIGIBILITY_DISABLED_SCHEMA
        and float(value.get("decay", 0.0)) == 0.0
        and float(value.get("clip", 0.0)) == 0.0
        and int(value.get("max_age_ticks", 0)) == 0
    )


def _disabled_association_payload(value: Any) -> bool:
    if value is None:
        return True
    if not isinstance(value, Mapping):
        return False
    return (
        value.get("schema") == SUBJECT_VM_ASSOCIATION_DISABLED_SCHEMA
        and int(value.get("request_token_port", -1)) == -1
        and float(value.get("request_threshold", 0.0)) == 0.0
        and float(value.get("similarity_threshold", 0.0)) == 0.0
        and int(value.get("min_delay_ticks", 0)) == 0
        and int(value.get("max_delay_ticks", 0)) == 0
    )


def strip_disabled_subject_vm_section(payload: dict[str, Any]) -> dict[str, Any]:
    """Remove exact inert extensions without changing frozen identities."""
    section = payload.get("subject_vm")
    if not isinstance(section, Mapping):
        return payload
    if isinstance(section, dict) and _disabled_trace_payload(section.get("trace")):
        section.pop("trace", None)
    if isinstance(section, dict) and _disabled_eligibility_payload(
        section.get("eligibility")
    ):
        section.pop("eligibility", None)
    if isinstance(section, dict) and _disabled_association_payload(
        section.get("association")
    ):
        section.pop("association", None)
    if (
        section.get("enabled") is False
        and section.get("schema") == SUBJECT_VM_DISABLED_SCHEMA
        and int(section.get("node_state_width", 0)) == 0
        and section.get("inherit_structure_on_birth") is True
        and tuple(section.get("regions", ())) == ()
        and _disabled_activation_payload(section.get("activation"))
    ):
        payload.pop("subject_vm", None)
    return payload


__all__ = [
    "FORBIDDEN_COGNITIVE_FIELDS",
    "SUBJECT_VM_ACTIVATION_DISABLED_SCHEMA",
    "SUBJECT_VM_ASSOCIATION_DISABLED_SCHEMA",
    "SUBJECT_VM_ASSOCIATION_SCHEMA",
    "SUBJECT_VM_ACTIVATION_SCHEMA",
    "SUBJECT_VM_DISABLED_SCHEMA",
    "SUBJECT_VM_ELIGIBILITY_DISABLED_SCHEMA",
    "SUBJECT_VM_ELIGIBILITY_SCHEMA",
    "SUBJECT_VM_INPUT_PORT_SCHEMA",
    "SUBJECT_VM_OBJECTIVE_EVENT_SCHEMA",
    "SUBJECT_VM_OUTPUT_PORT_SCHEMA",
    "SUBJECT_VM_REGION_NAMES",
    "SUBJECT_VM_STAGE1_SCHEMA",
    "SUBJECT_VM_STAGE2_SCHEMA",
    "SUBJECT_VM_STAGE3_SCHEMA",
    "SUBJECT_VM_STAGE3B_SCHEMA",
    "SUBJECT_VM_STAGE3B2_SCHEMA",
    "SUBJECT_VM_TRACE_DISABLED_SCHEMA",
    "SUBJECT_VM_TRACE_SCHEMA",
    "SubjectVMActivationConfig",
    "SubjectVMAssociationConfig",
    "SubjectVMConfig",
    "SubjectVMEligibilityConfig",
    "SubjectVMRegionConfig",
    "SubjectVMTraceConfig",
    "load_subject_vm_config",
    "strip_disabled_subject_vm_section",
    "validate_subject_vm_config",
]
