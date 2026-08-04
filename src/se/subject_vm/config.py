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
SUBJECT_VM_STAGE3B3_SCHEMA = "partitioned-subject-graph-vm-stage3b3-modulation-proposal-v1"
SUBJECT_VM_STAGE3C1_SCHEMA = "partitioned-subject-graph-vm-stage3c1-target-binding-v1"
SUBJECT_VM_STAGE3C2_SCHEMA = "partitioned-subject-graph-vm-stage3c2-update-safety-proposal-v1"
SUBJECT_VM_STAGE3C3_SCHEMA = "partitioned-subject-graph-vm-stage3c3-shadow-transaction-v1"
SUBJECT_VM_STAGE3C4_SCHEMA = "partitioned-subject-graph-vm-stage3c4-guarded-live-write-v1"
SUBJECT_VM_STAGE3C5_SCHEMA = "partitioned-subject-graph-vm-stage3c5-objective-evaluation-window-v1"
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
SUBJECT_VM_MODULATION_DISABLED_SCHEMA = "disabled"
SUBJECT_VM_MODULATION_SCHEMA = "bounded-objective-contrast-modulation-proposal-v1"
SUBJECT_VM_TARGET_BINDING_DISABLED_SCHEMA = "disabled"
SUBJECT_VM_TARGET_BINDING_SCHEMA = "bootstrap-single-winner-local-eligibility-binding-v1"
SUBJECT_VM_UPDATE_SAFETY_DISABLED_SCHEMA = "disabled"
SUBJECT_VM_UPDATE_SAFETY_SCHEMA = "bounded-compare-and-swap-delta-proposal-v1"
SUBJECT_VM_TRANSACTION_DISABLED_SCHEMA = "disabled"
SUBJECT_VM_TRANSACTION_SCHEMA = "atomic-shadow-cas-rollback-v1"
SUBJECT_VM_LIVE_WRITE_DISABLED_SCHEMA = "disabled"
SUBJECT_VM_LIVE_WRITE_SCHEMA = "guarded-live-write-rollback-window-v1"
SUBJECT_VM_EVALUATION_DISABLED_SCHEMA = "disabled"
SUBJECT_VM_EVALUATION_SCHEMA = "objective-score-free-window-v1"
SUBJECT_VM_THOUGHT_EVENT_DISABLED_SCHEMA = "disabled"
SUBJECT_VM_THOUGHT_EVENT_SCHEMA = "unified-thought-event-arena-t1-v1"
SUBJECT_VM_THOUGHT_EVENT_RECALL_DISABLED_SCHEMA = "disabled"
SUBJECT_VM_THOUGHT_EVENT_RECALL_SCHEMA = "single-latest-prior-thought-event-recall-v1"
SUBJECT_VM_THOUGHT_EVENT_RECALL_CONTENT_MODES = (
    "identity",
    "rotate-one-coordinate-control",
    "zero-content-control",
)
SUBJECT_VM_MODULATION_FACT_WIDTH = 21
SUBJECT_VM_MODULATION_TARGET_NAMES = (
    "node-bias",
    "node-input-gate",
    "node-output-gate",
    "node-trace-gate",
    "edge-forward-gate",
    "edge-bandwidth",
)
SUBJECT_VM_MODULATION_TARGET_WIDTH = len(SUBJECT_VM_MODULATION_TARGET_NAMES)
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
class SubjectVMModulationConfig:
    """Stage-3B-3 compact, rejectable modulation-proposal contract.

    The graph supplies bounded token coordinates that project a current-versus-
    historical objective fact contrast into generic parameter-family proposal
    coordinates.  The proposal is audit-only in this stage: it never binds an
    exact node or edge and never writes eligibility or graph parameters.
    """

    schema: str = SUBJECT_VM_MODULATION_DISABLED_SCHEMA
    request_token_port: int = -1
    request_threshold: float = 0.0
    fact_weight_start_port: int = -1
    target_weight_start_port: int = -1
    proposal_clip: float = 0.0


@dataclass(frozen=True)
class SubjectVMTargetBindingConfig:
    """Stage-3C-1 exact target proposal binding without parameter writes.

    The fixed single-winner selector is an explicit bootstrap bias used to
    shorten graph-shaping search. It is not a universal attention claim.
    Candidates are captured after decay and before current-tick eligibility
    marks, preventing same-tick activity from selecting itself.
    """

    schema: str = SUBJECT_VM_TARGET_BINDING_DISABLED_SCHEMA
    min_abs_eligibility: float = 0.0


@dataclass(frozen=True)
class SubjectVMUpdateSafetyConfig:
    """Stage-3C-2 bounded candidate deltas without parameter writes.

    Bounds are generic numerical safety envelopes.  They do not define event
    value, reward, utility, or semantic parameter meaning.
    """

    schema: str = SUBJECT_VM_UPDATE_SAFETY_DISABLED_SCHEMA
    step_scale: float = 0.0
    min_abs_delta: float = 0.0
    family_delta_clip: tuple[float, ...] = ()
    event_l1_budget: float = 0.0
    parameter_lower_bounds: tuple[float, ...] = ()
    parameter_upper_bounds: tuple[float, ...] = ()


@dataclass(frozen=True)
class SubjectVMTransactionConfig:
    """Stage-3C-3 all-or-none shadow apply and rollback validation.

    Cost units are count-only instrumentation.  They are not debited from
    entity energy and do not authorize permanent graph writes.
    """

    schema: str = SUBJECT_VM_TRANSACTION_DISABLED_SCHEMA
    max_targets_per_event: int = 0
    base_cost_units: int = 0
    per_target_cost_units: int = 0


@dataclass(frozen=True)
class SubjectVMLiveWriteConfig:
    """Stage-3C-4 explicitly opted-in, rollback-window live-write experiment.

    This is a bounded engineering bootstrap, not a claim that the proposed
    update is causally correct. Cost values remain count-only instrumentation.
    """

    schema: str = SUBJECT_VM_LIVE_WRITE_DISABLED_SCHEMA
    enabled: bool = False
    ledger_capacity_per_subject: int = 0
    rollback_after_ticks: int = 0
    window_ticks: int = 0
    max_pending_transactions: int = 0
    max_applied_targets_per_window: int = 0
    max_abs_delta_per_window: float = 0.0
    commit_base_cost_units: int = 0
    commit_per_target_cost_units: int = 0
    rollback_base_cost_units: int = 0
    rollback_per_target_cost_units: int = 0

    @property
    def trace_capacity_required(self) -> int:
        return int(self.rollback_after_ticks) + 1


@dataclass(frozen=True)
class SubjectVMEvaluationConfig:
    """Stage-3C-5 objective evidence window without keep/revert decisions."""

    schema: str = SUBJECT_VM_EVALUATION_DISABLED_SCHEMA
    enabled: bool = False
    capacity_per_subject: int = 0
    observation_ticks: int = 0
    control_horizon_ticks: int = 0
    fact_clip: float = 0.0
    registration_cost_units: int = 0
    per_observation_cost_units: int = 0


@dataclass(frozen=True)
class SubjectVMThoughtEventRecallConfig:
    """T3 single-path read of one already-committed prior ThoughtEvent.

    The selector is deliberately minimal and deterministic: latest retained
    event from a strictly earlier tick.  ``content_mode`` includes two declared
    experimental controls, not cognitive roles.  Cost units are count-only
    instrumentation and are never interpreted as reward or confidence.
    """

    schema: str = SUBJECT_VM_THOUGHT_EVENT_RECALL_DISABLED_SCHEMA
    enabled: bool = False
    content_mode: str = "identity"
    min_age_ticks: int = 0
    max_ingress_paths: int = 0
    search_per_slot_cost_units: int = 0
    read_base_cost_units: int = 0
    read_per_coordinate_cost_units: int = 0
    ingress_per_path_cost_units: int = 0


@dataclass(frozen=True)
class SubjectVMThoughtEventConfig:
    """Bounded immutable ThoughtEvent arena with optional T3 forward recall.

    Cost units are count-only instrumentation.  They are not debited from
    energy and do not define value, importance, confidence, or retention
    utility.
    """

    schema: str = SUBJECT_VM_THOUGHT_EVENT_DISABLED_SCHEMA
    enabled: bool = False
    capacity_per_subject: int = 0
    max_parent_count: int = 0
    retention_ticks: int = 0
    emission_base_cost_units: int = 0
    emission_per_coordinate_cost_units: int = 0
    parent_link_cost_units: int = 0
    retention_per_event_tick_cost_units: int = 0
    recall: SubjectVMThoughtEventRecallConfig = SubjectVMThoughtEventRecallConfig()


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
    modulation: SubjectVMModulationConfig = SubjectVMModulationConfig()
    target_binding: SubjectVMTargetBindingConfig = SubjectVMTargetBindingConfig()
    update_safety: SubjectVMUpdateSafetyConfig = SubjectVMUpdateSafetyConfig()
    transaction: SubjectVMTransactionConfig = SubjectVMTransactionConfig()
    live_write: SubjectVMLiveWriteConfig = SubjectVMLiveWriteConfig()
    evaluation: SubjectVMEvaluationConfig = SubjectVMEvaluationConfig()
    thought_event: SubjectVMThoughtEventConfig = SubjectVMThoughtEventConfig()

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
            SUBJECT_VM_STAGE3B3_SCHEMA,
            SUBJECT_VM_STAGE3C1_SCHEMA,
            SUBJECT_VM_STAGE3C2_SCHEMA,
            SUBJECT_VM_STAGE3C3_SCHEMA,
            SUBJECT_VM_STAGE3C4_SCHEMA,
            SUBJECT_VM_STAGE3C5_SCHEMA,
        }

    @property
    def trace_enabled(self) -> bool:
        return self.schema in {
            SUBJECT_VM_STAGE3_SCHEMA,
            SUBJECT_VM_STAGE3B_SCHEMA,
            SUBJECT_VM_STAGE3B2_SCHEMA,
            SUBJECT_VM_STAGE3B3_SCHEMA,
            SUBJECT_VM_STAGE3C1_SCHEMA,
            SUBJECT_VM_STAGE3C2_SCHEMA,
            SUBJECT_VM_STAGE3C3_SCHEMA,
            SUBJECT_VM_STAGE3C4_SCHEMA,
            SUBJECT_VM_STAGE3C5_SCHEMA,
        }

    @property
    def eligibility_enabled(self) -> bool:
        return self.schema in {
            SUBJECT_VM_STAGE3B_SCHEMA,
            SUBJECT_VM_STAGE3B2_SCHEMA,
            SUBJECT_VM_STAGE3B3_SCHEMA,
            SUBJECT_VM_STAGE3C1_SCHEMA,
            SUBJECT_VM_STAGE3C2_SCHEMA,
            SUBJECT_VM_STAGE3C3_SCHEMA,
            SUBJECT_VM_STAGE3C4_SCHEMA,
            SUBJECT_VM_STAGE3C5_SCHEMA,
        }

    @property
    def association_enabled(self) -> bool:
        return self.schema in {
            SUBJECT_VM_STAGE3B2_SCHEMA,
            SUBJECT_VM_STAGE3B3_SCHEMA,
            SUBJECT_VM_STAGE3C1_SCHEMA,
            SUBJECT_VM_STAGE3C2_SCHEMA,
            SUBJECT_VM_STAGE3C3_SCHEMA,
            SUBJECT_VM_STAGE3C4_SCHEMA,
            SUBJECT_VM_STAGE3C5_SCHEMA,
        }

    @property
    def modulation_enabled(self) -> bool:
        return self.schema in {
            SUBJECT_VM_STAGE3B3_SCHEMA,
            SUBJECT_VM_STAGE3C1_SCHEMA,
            SUBJECT_VM_STAGE3C2_SCHEMA,
            SUBJECT_VM_STAGE3C3_SCHEMA,
            SUBJECT_VM_STAGE3C4_SCHEMA,
            SUBJECT_VM_STAGE3C5_SCHEMA,
        }

    @property
    def target_binding_enabled(self) -> bool:
        return self.schema in {
            SUBJECT_VM_STAGE3C1_SCHEMA,
            SUBJECT_VM_STAGE3C2_SCHEMA,
            SUBJECT_VM_STAGE3C3_SCHEMA,
            SUBJECT_VM_STAGE3C4_SCHEMA,
            SUBJECT_VM_STAGE3C5_SCHEMA,
        }

    @property
    def update_safety_enabled(self) -> bool:
        return self.schema in {SUBJECT_VM_STAGE3C2_SCHEMA, SUBJECT_VM_STAGE3C3_SCHEMA, SUBJECT_VM_STAGE3C4_SCHEMA, SUBJECT_VM_STAGE3C5_SCHEMA}

    @property
    def transaction_enabled(self) -> bool:
        return self.schema in {SUBJECT_VM_STAGE3C3_SCHEMA, SUBJECT_VM_STAGE3C4_SCHEMA, SUBJECT_VM_STAGE3C5_SCHEMA}

    @property
    def live_write_configured(self) -> bool:
        return self.schema in {SUBJECT_VM_STAGE3C4_SCHEMA, SUBJECT_VM_STAGE3C5_SCHEMA}

    @property
    def live_write_enabled(self) -> bool:
        return self.live_write_configured and bool(self.live_write.enabled)

    @property
    def evaluation_enabled(self) -> bool:
        return self.schema == SUBJECT_VM_STAGE3C5_SCHEMA and bool(self.evaluation.enabled)

    @property
    def thought_event_enabled(self) -> bool:
        return bool(self.thought_event.enabled)

    @property
    def thought_event_recall_enabled(self) -> bool:
        return self.thought_event_enabled and bool(self.thought_event.recall.enabled)


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


def _load_modulation_config(raw: Any) -> SubjectVMModulationConfig:
    if raw is None:
        return SubjectVMModulationConfig()
    if not isinstance(raw, Mapping):
        raise ValueError("subject_vm.modulation must be an object")
    allowed = {
        "schema",
        "request_token_port",
        "request_threshold",
        "fact_weight_start_port",
        "target_weight_start_port",
        "proposal_clip",
    }
    unknown = sorted(set(raw) - allowed)
    if unknown:
        raise ValueError(f"unknown subject_vm.modulation fields: {unknown}")
    return SubjectVMModulationConfig(
        schema=str(raw.get("schema", SUBJECT_VM_MODULATION_DISABLED_SCHEMA)),
        request_token_port=int(raw.get("request_token_port", -1)),
        request_threshold=float(raw.get("request_threshold", 0.0)),
        fact_weight_start_port=int(raw.get("fact_weight_start_port", -1)),
        target_weight_start_port=int(raw.get("target_weight_start_port", -1)),
        proposal_clip=float(raw.get("proposal_clip", 0.0)),
    )


def _load_target_binding_config(raw: Any) -> SubjectVMTargetBindingConfig:
    if raw is None:
        return SubjectVMTargetBindingConfig()
    if not isinstance(raw, Mapping):
        raise ValueError("subject_vm.target_binding must be an object")
    allowed = {"schema", "min_abs_eligibility"}
    unknown = sorted(set(raw) - allowed)
    if unknown:
        raise ValueError(f"unknown subject_vm.target_binding fields: {unknown}")
    return SubjectVMTargetBindingConfig(
        schema=str(raw.get("schema", SUBJECT_VM_TARGET_BINDING_DISABLED_SCHEMA)),
        min_abs_eligibility=float(raw.get("min_abs_eligibility", 0.0)),
    )


def _float_tuple(raw: Any, *, field: str) -> tuple[float, ...]:
    if raw is None:
        return ()
    if not isinstance(raw, (list, tuple)):
        raise ValueError(f"{field} must be a list")
    return tuple(float(value) for value in raw)


def _load_update_safety_config(raw: Any) -> SubjectVMUpdateSafetyConfig:
    if raw is None:
        return SubjectVMUpdateSafetyConfig()
    if not isinstance(raw, Mapping):
        raise ValueError("subject_vm.update_safety must be an object")
    allowed = {
        "schema",
        "step_scale",
        "min_abs_delta",
        "family_delta_clip",
        "event_l1_budget",
        "parameter_lower_bounds",
        "parameter_upper_bounds",
    }
    unknown = sorted(set(raw) - allowed)
    if unknown:
        raise ValueError(f"unknown subject_vm.update_safety fields: {unknown}")
    return SubjectVMUpdateSafetyConfig(
        schema=str(raw.get("schema", SUBJECT_VM_UPDATE_SAFETY_DISABLED_SCHEMA)),
        step_scale=float(raw.get("step_scale", 0.0)),
        min_abs_delta=float(raw.get("min_abs_delta", 0.0)),
        family_delta_clip=_float_tuple(
            raw.get("family_delta_clip"), field="subject_vm.update_safety.family_delta_clip"
        ),
        event_l1_budget=float(raw.get("event_l1_budget", 0.0)),
        parameter_lower_bounds=_float_tuple(
            raw.get("parameter_lower_bounds"),
            field="subject_vm.update_safety.parameter_lower_bounds",
        ),
        parameter_upper_bounds=_float_tuple(
            raw.get("parameter_upper_bounds"),
            field="subject_vm.update_safety.parameter_upper_bounds",
        ),
    )


def _load_transaction_config(raw: Any) -> SubjectVMTransactionConfig:
    if raw is None:
        return SubjectVMTransactionConfig()
    if not isinstance(raw, Mapping):
        raise ValueError("subject_vm.transaction must be an object")
    allowed = {
        "schema",
        "max_targets_per_event",
        "base_cost_units",
        "per_target_cost_units",
    }
    unknown = sorted(set(raw) - allowed)
    if unknown:
        raise ValueError(f"unknown subject_vm.transaction fields: {unknown}")
    return SubjectVMTransactionConfig(
        schema=str(raw.get("schema", SUBJECT_VM_TRANSACTION_DISABLED_SCHEMA)),
        max_targets_per_event=int(raw.get("max_targets_per_event", 0)),
        base_cost_units=int(raw.get("base_cost_units", 0)),
        per_target_cost_units=int(raw.get("per_target_cost_units", 0)),
    )


def _load_live_write_config(raw: Any) -> SubjectVMLiveWriteConfig:
    if raw is None:
        return SubjectVMLiveWriteConfig()
    if not isinstance(raw, Mapping):
        raise ValueError("subject_vm.live_write must be an object")
    allowed = {
        "schema", "enabled", "ledger_capacity_per_subject",
        "rollback_after_ticks", "window_ticks", "max_pending_transactions",
        "max_applied_targets_per_window", "max_abs_delta_per_window",
        "commit_base_cost_units", "commit_per_target_cost_units",
        "rollback_base_cost_units", "rollback_per_target_cost_units",
    }
    unknown = sorted(set(raw) - allowed)
    if unknown:
        raise ValueError(f"unknown subject_vm.live_write fields: {unknown}")
    return SubjectVMLiveWriteConfig(
        schema=str(raw.get("schema", SUBJECT_VM_LIVE_WRITE_DISABLED_SCHEMA)),
        enabled=bool(raw.get("enabled", False)),
        ledger_capacity_per_subject=int(raw.get("ledger_capacity_per_subject", 0)),
        rollback_after_ticks=int(raw.get("rollback_after_ticks", 0)),
        window_ticks=int(raw.get("window_ticks", 0)),
        max_pending_transactions=int(raw.get("max_pending_transactions", 0)),
        max_applied_targets_per_window=int(raw.get("max_applied_targets_per_window", 0)),
        max_abs_delta_per_window=float(raw.get("max_abs_delta_per_window", 0.0)),
        commit_base_cost_units=int(raw.get("commit_base_cost_units", 0)),
        commit_per_target_cost_units=int(raw.get("commit_per_target_cost_units", 0)),
        rollback_base_cost_units=int(raw.get("rollback_base_cost_units", 0)),
        rollback_per_target_cost_units=int(raw.get("rollback_per_target_cost_units", 0)),
    )


def _load_evaluation_config(raw: Any) -> SubjectVMEvaluationConfig:
    if raw is None:
        return SubjectVMEvaluationConfig()
    if not isinstance(raw, Mapping):
        raise ValueError("subject_vm.evaluation must be an object")
    allowed = {
        "schema", "enabled", "capacity_per_subject", "observation_ticks",
        "control_horizon_ticks", "fact_clip", "registration_cost_units",
        "per_observation_cost_units",
    }
    unknown = sorted(set(raw) - allowed)
    if unknown:
        raise ValueError(f"unknown subject_vm.evaluation fields: {unknown}")
    return SubjectVMEvaluationConfig(
        schema=str(raw.get("schema", SUBJECT_VM_EVALUATION_DISABLED_SCHEMA)),
        enabled=bool(raw.get("enabled", False)),
        capacity_per_subject=int(raw.get("capacity_per_subject", 0)),
        observation_ticks=int(raw.get("observation_ticks", 0)),
        control_horizon_ticks=int(raw.get("control_horizon_ticks", 0)),
        fact_clip=float(raw.get("fact_clip", 0.0)),
        registration_cost_units=int(raw.get("registration_cost_units", 0)),
        per_observation_cost_units=int(raw.get("per_observation_cost_units", 0)),
    )


def _load_thought_event_recall_config(raw: Any) -> SubjectVMThoughtEventRecallConfig:
    if raw is None:
        return SubjectVMThoughtEventRecallConfig()
    if not isinstance(raw, Mapping):
        raise ValueError("subject_vm.thought_event.recall must be an object")
    allowed = {
        "schema",
        "enabled",
        "content_mode",
        "min_age_ticks",
        "max_ingress_paths",
        "search_per_slot_cost_units",
        "read_base_cost_units",
        "read_per_coordinate_cost_units",
        "ingress_per_path_cost_units",
    }
    unknown = sorted(set(raw) - allowed)
    if unknown:
        raise ValueError(f"unknown subject_vm.thought_event.recall fields: {unknown}")
    return SubjectVMThoughtEventRecallConfig(
        schema=str(raw.get("schema", SUBJECT_VM_THOUGHT_EVENT_RECALL_DISABLED_SCHEMA)),
        enabled=bool(raw.get("enabled", False)),
        content_mode=str(raw.get("content_mode", "identity")),
        min_age_ticks=int(raw.get("min_age_ticks", 0)),
        max_ingress_paths=int(raw.get("max_ingress_paths", 0)),
        search_per_slot_cost_units=int(raw.get("search_per_slot_cost_units", 0)),
        read_base_cost_units=int(raw.get("read_base_cost_units", 0)),
        read_per_coordinate_cost_units=int(raw.get("read_per_coordinate_cost_units", 0)),
        ingress_per_path_cost_units=int(raw.get("ingress_per_path_cost_units", 0)),
    )


def _load_thought_event_config(raw: Any) -> SubjectVMThoughtEventConfig:
    if raw is None:
        return SubjectVMThoughtEventConfig()
    if not isinstance(raw, Mapping):
        raise ValueError("subject_vm.thought_event must be an object")
    allowed = {
        "schema",
        "enabled",
        "capacity_per_subject",
        "max_parent_count",
        "retention_ticks",
        "emission_base_cost_units",
        "emission_per_coordinate_cost_units",
        "parent_link_cost_units",
        "retention_per_event_tick_cost_units",
        "recall",
    }
    unknown = sorted(set(raw) - allowed)
    if unknown:
        raise ValueError(f"unknown subject_vm.thought_event fields: {unknown}")
    return SubjectVMThoughtEventConfig(
        schema=str(raw.get("schema", SUBJECT_VM_THOUGHT_EVENT_DISABLED_SCHEMA)),
        enabled=bool(raw.get("enabled", False)),
        capacity_per_subject=int(raw.get("capacity_per_subject", 0)),
        max_parent_count=int(raw.get("max_parent_count", 0)),
        retention_ticks=int(raw.get("retention_ticks", 0)),
        emission_base_cost_units=int(raw.get("emission_base_cost_units", 0)),
        emission_per_coordinate_cost_units=int(
            raw.get("emission_per_coordinate_cost_units", 0)
        ),
        parent_link_cost_units=int(raw.get("parent_link_cost_units", 0)),
        retention_per_event_tick_cost_units=int(
            raw.get("retention_per_event_tick_cost_units", 0)
        ),
        recall=_load_thought_event_recall_config(raw.get("recall")),
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
        "modulation",
        "target_binding",
        "update_safety",
        "transaction",
        "live_write",
        "evaluation",
        "thought_event",
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
        modulation=_load_modulation_config(raw.get("modulation")),
        target_binding=_load_target_binding_config(raw.get("target_binding")),
        update_safety=_load_update_safety_config(raw.get("update_safety")),
        transaction=_load_transaction_config(raw.get("transaction")),
        live_write=_load_live_write_config(raw.get("live_write")),
        evaluation=_load_evaluation_config(raw.get("evaluation")),
        thought_event=_load_thought_event_config(raw.get("thought_event")),
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


def _validate_disabled_modulation(cfg: SubjectVMModulationConfig) -> None:
    if cfg != SubjectVMModulationConfig():
        raise ValueError(
            "inactive subject_vm modulation requires exact disabled defaults"
        )


def _validate_disabled_target_binding(cfg: SubjectVMTargetBindingConfig) -> None:
    if cfg != SubjectVMTargetBindingConfig():
        raise ValueError(
            "inactive subject_vm target_binding requires exact disabled defaults"
        )


def _validate_disabled_update_safety(cfg: SubjectVMUpdateSafetyConfig) -> None:
    if cfg != SubjectVMUpdateSafetyConfig():
        raise ValueError(
            "inactive subject_vm update_safety requires exact disabled defaults"
        )


def _validate_disabled_transaction(cfg: SubjectVMTransactionConfig) -> None:
    if cfg != SubjectVMTransactionConfig():
        raise ValueError(
            "inactive subject_vm transaction requires exact disabled defaults"
        )


def _validate_disabled_live_write(cfg: SubjectVMLiveWriteConfig) -> None:
    if cfg != SubjectVMLiveWriteConfig():
        raise ValueError(
            "inactive subject_vm live_write requires exact disabled defaults"
        )


def _validate_disabled_evaluation(cfg: SubjectVMEvaluationConfig) -> None:
    if cfg != SubjectVMEvaluationConfig():
        raise ValueError(
            "inactive subject_vm evaluation requires exact disabled defaults"
        )


def _validate_disabled_thought_event(cfg: SubjectVMThoughtEventConfig) -> None:
    if cfg != SubjectVMThoughtEventConfig():
        raise ValueError(
            "inactive subject_vm thought_event requires exact disabled defaults"
        )


def _validate_disabled_thought_event_recall(
    cfg: SubjectVMThoughtEventRecallConfig,
) -> None:
    if cfg != SubjectVMThoughtEventRecallConfig():
        raise ValueError(
            "inactive subject_vm thought_event recall requires exact disabled defaults"
        )


def _validate_thought_event_recall(
    cfg: SubjectVMThoughtEventRecallConfig,
    *,
    thought_event: SubjectVMThoughtEventConfig,
    trace: SubjectVMTraceConfig,
) -> None:
    if cfg.schema != SUBJECT_VM_THOUGHT_EVENT_RECALL_SCHEMA or not cfg.enabled:
        raise ValueError(
            "enabled subject_vm thought_event recall requires the approved T3 schema"
        )
    if cfg.content_mode not in SUBJECT_VM_THOUGHT_EVENT_RECALL_CONTENT_MODES:
        raise ValueError("subject_vm thought_event recall content_mode is unsupported")
    if cfg.min_age_ticks != 1:
        raise ValueError("T3 thought_event recall min_age_ticks is frozen at 1")
    if cfg.max_ingress_paths != 1:
        raise ValueError("T3 thought_event recall supports exactly one ingress path")
    if thought_event.max_parent_count < 1:
        raise ValueError("thought_event recall requires parent DAG capacity")
    if trace.token_width <= 0:
        raise ValueError("thought_event recall requires a positive token width")
    costs = (
        cfg.search_per_slot_cost_units,
        cfg.read_base_cost_units,
        cfg.read_per_coordinate_cost_units,
        cfg.ingress_per_path_cost_units,
    )
    if any(int(value) < 0 or int(value) > 1_000_000 for value in costs):
        raise ValueError(
            "subject_vm thought_event recall count-only costs must be in [0, 1000000]"
        )


def _validate_thought_event(
    cfg: SubjectVMThoughtEventConfig, *, trace: SubjectVMTraceConfig
) -> None:
    if cfg.schema != SUBJECT_VM_THOUGHT_EVENT_SCHEMA or not cfg.enabled:
        raise ValueError(
            "enabled subject_vm thought_event requires the approved T1 schema"
        )
    if trace.schema != SUBJECT_VM_TRACE_SCHEMA or trace.token_width <= 0:
        raise ValueError("subject_vm thought_event requires enabled token trace")
    if not 1 <= cfg.capacity_per_subject <= 65535:
        raise ValueError(
            "subject_vm thought_event capacity_per_subject must be in [1, 65535]"
        )
    if not 1 <= cfg.max_parent_count <= min(8, cfg.capacity_per_subject):
        raise ValueError(
            "subject_vm thought_event max_parent_count must be in [1, min(8, capacity)]"
        )
    if not 1 <= cfg.retention_ticks <= 2_147_483_647:
        raise ValueError(
            "subject_vm thought_event retention_ticks must be in [1, 2147483647]"
        )
    costs = (
        cfg.emission_base_cost_units,
        cfg.emission_per_coordinate_cost_units,
        cfg.parent_link_cost_units,
        cfg.retention_per_event_tick_cost_units,
    )
    if any(int(value) < 0 or int(value) > 1_000_000 for value in costs):
        raise ValueError(
            "subject_vm thought_event count-only costs must be in [0, 1000000]"
        )
    if cfg.recall.enabled:
        _validate_thought_event_recall(cfg.recall, thought_event=cfg, trace=trace)
    else:
        _validate_disabled_thought_event_recall(cfg.recall)


def _validate_thought_event_extension(cfg: SubjectVMConfig) -> None:
    if cfg.thought_event_enabled:
        if not cfg.enabled or not cfg.trace_enabled:
            raise ValueError(
                "subject_vm thought_event requires enabled Stage-3-or-later Subject VM"
            )
        _validate_thought_event(cfg.thought_event, trace=cfg.trace)
    else:
        _validate_disabled_thought_event(cfg.thought_event)


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


def _validate_modulation(
    cfg: SubjectVMModulationConfig,
    *,
    trace: SubjectVMTraceConfig,
    association: SubjectVMAssociationConfig,
) -> None:
    if cfg.schema != SUBJECT_VM_MODULATION_SCHEMA:
        raise ValueError(
            f"Stage-3B-3 subject_vm requires modulation schema {SUBJECT_VM_MODULATION_SCHEMA!r}"
        )
    if not 0 <= cfg.request_token_port < trace.token_width:
        raise ValueError("subject_vm modulation request_token_port is outside token width")
    if not 0.0 < cfg.request_threshold <= trace.token_clip:
        raise ValueError(
            "subject_vm modulation request_threshold must be in (0, token_clip]"
        )
    if cfg.fact_weight_start_port < 0:
        raise ValueError("subject_vm modulation fact_weight_start_port must be non-negative")
    fact_ports = set(
        range(
            cfg.fact_weight_start_port,
            cfg.fact_weight_start_port + SUBJECT_VM_MODULATION_FACT_WIDTH,
        )
    )
    if not fact_ports or max(fact_ports) >= trace.token_width:
        raise ValueError("subject_vm modulation fact-weight block exceeds token width")
    if cfg.target_weight_start_port < 0:
        raise ValueError("subject_vm modulation target_weight_start_port must be non-negative")
    target_ports = set(
        range(
            cfg.target_weight_start_port,
            cfg.target_weight_start_port + SUBJECT_VM_MODULATION_TARGET_WIDTH,
        )
    )
    if not target_ports or max(target_ports) >= trace.token_width:
        raise ValueError("subject_vm modulation target-weight block exceeds token width")
    control_ports = {int(cfg.request_token_port)} | fact_ports | target_ports
    if len(control_ports) != 1 + len(fact_ports) + len(target_ports):
        raise ValueError("subject_vm modulation token controls must not overlap")
    if int(association.request_token_port) in control_ports:
        raise ValueError(
            "subject_vm association and modulation control ports must not overlap"
        )
    if not 0.0 < cfg.proposal_clip <= 64.0:
        raise ValueError("subject_vm modulation proposal_clip must be in (0, 64]")


def _validate_target_binding(
    cfg: SubjectVMTargetBindingConfig, *, eligibility: SubjectVMEligibilityConfig
) -> None:
    if cfg.schema != SUBJECT_VM_TARGET_BINDING_SCHEMA:
        raise ValueError(
            f"Stage-3C-1 subject_vm requires target binding schema {SUBJECT_VM_TARGET_BINDING_SCHEMA!r}"
        )
    if not 0.0 < cfg.min_abs_eligibility <= eligibility.clip:
        raise ValueError(
            "subject_vm target_binding min_abs_eligibility must be in (0, eligibility.clip]"
        )


def _validate_update_safety(cfg: SubjectVMUpdateSafetyConfig) -> None:
    if cfg.schema != SUBJECT_VM_UPDATE_SAFETY_SCHEMA:
        raise ValueError(
            f"Stage-3C-2 subject_vm requires update safety schema {SUBJECT_VM_UPDATE_SAFETY_SCHEMA!r}"
        )
    if not 0.0 < cfg.step_scale <= 64.0:
        raise ValueError("subject_vm update_safety step_scale must be in (0, 64]")
    if not 0.0 < cfg.min_abs_delta <= 64.0:
        raise ValueError("subject_vm update_safety min_abs_delta must be in (0, 64]")
    width = SUBJECT_VM_MODULATION_TARGET_WIDTH
    if len(cfg.family_delta_clip) != width:
        raise ValueError("subject_vm update_safety family_delta_clip width mismatch")
    if len(cfg.parameter_lower_bounds) != width or len(cfg.parameter_upper_bounds) != width:
        raise ValueError("subject_vm update_safety parameter bound width mismatch")
    values = (
        *cfg.family_delta_clip,
        *cfg.parameter_lower_bounds,
        *cfg.parameter_upper_bounds,
        cfg.event_l1_budget,
    )
    if any(not -64.0 <= float(value) <= 64.0 for value in values):
        raise ValueError("subject_vm update_safety bounds must be finite in [-64, 64]")
    if any(float(value) <= 0.0 for value in cfg.family_delta_clip):
        raise ValueError("subject_vm update_safety family delta clips must be positive")
    if cfg.min_abs_delta > min(cfg.family_delta_clip):
        raise ValueError("subject_vm update_safety min_abs_delta exceeds a family clip")
    if not 0.0 < cfg.event_l1_budget <= sum(cfg.family_delta_clip):
        raise ValueError(
            "subject_vm update_safety event_l1_budget must be in (0, sum(family_delta_clip)]"
        )
    for low, high, clip in zip(
        cfg.parameter_lower_bounds,
        cfg.parameter_upper_bounds,
        cfg.family_delta_clip,
        strict=True,
    ):
        if not float(low) < float(high):
            raise ValueError("subject_vm update_safety lower bounds must be below upper bounds")
        if float(clip) > float(high) - float(low):
            raise ValueError("subject_vm update_safety family clip exceeds parameter range")
    if cfg.parameter_lower_bounds[5] < 0.0:
        raise ValueError("subject_vm edge bandwidth lower bound cannot be negative")


def _validate_transaction(cfg: SubjectVMTransactionConfig) -> None:
    if cfg.schema != SUBJECT_VM_TRANSACTION_SCHEMA:
        raise ValueError(
            f"Stage-3C-3 subject_vm requires transaction schema {SUBJECT_VM_TRANSACTION_SCHEMA!r}"
        )
    if not 1 <= int(cfg.max_targets_per_event) <= SUBJECT_VM_MODULATION_TARGET_WIDTH:
        raise ValueError(
            "subject_vm transaction max_targets_per_event must be in [1, target width]"
        )
    if not 0 <= int(cfg.base_cost_units) <= 1_000_000:
        raise ValueError("subject_vm transaction base_cost_units must be in [0, 1000000]")
    if not 0 <= int(cfg.per_target_cost_units) <= 1_000_000:
        raise ValueError(
            "subject_vm transaction per_target_cost_units must be in [0, 1000000]"
        )
    maximum = int(cfg.base_cost_units) + int(cfg.max_targets_per_event) * int(
        cfg.per_target_cost_units
    )
    if maximum > 2**32 - 1:
        raise ValueError("subject_vm transaction counted cost exceeds uint32 capacity")


def _validate_live_write(
    cfg: SubjectVMLiveWriteConfig, *, trace: SubjectVMTraceConfig
) -> None:
    if cfg.schema != SUBJECT_VM_LIVE_WRITE_SCHEMA:
        raise ValueError(
            f"Stage-3C-4 subject_vm requires live-write schema {SUBJECT_VM_LIVE_WRITE_SCHEMA!r}"
        )
    if not 1 <= cfg.ledger_capacity_per_subject <= 64:
        raise ValueError("subject_vm live_write ledger_capacity_per_subject must be in [1, 64]")
    if not 1 <= cfg.rollback_after_ticks < trace.retention_ticks:
        raise ValueError("subject_vm live_write rollback_after_ticks must be in [1, retention_ticks)")
    if cfg.trace_capacity_required > trace.capacity_per_subject:
        raise ValueError("subject_vm live_write rollback window exceeds trace ring capacity")
    if not cfg.rollback_after_ticks < cfg.window_ticks <= 2**31 - 1:
        raise ValueError("subject_vm live_write window_ticks must exceed rollback_after_ticks")
    if not 1 <= cfg.max_pending_transactions <= cfg.ledger_capacity_per_subject:
        raise ValueError("subject_vm live_write max_pending_transactions exceeds ledger capacity")
    if not 1 <= cfg.max_applied_targets_per_window <= 65535:
        raise ValueError("subject_vm live_write max_applied_targets_per_window must be in [1, 65535]")
    if not 0.0 < cfg.max_abs_delta_per_window <= 64.0:
        raise ValueError("subject_vm live_write max_abs_delta_per_window must be in (0, 64]")
    costs = (cfg.commit_base_cost_units, cfg.commit_per_target_cost_units, cfg.rollback_base_cost_units, cfg.rollback_per_target_cost_units)
    if any(not 0 <= int(value) <= 1_000_000 for value in costs):
        raise ValueError("subject_vm live_write counted costs must be in [0, 1000000]")


def _validate_evaluation(
    cfg: SubjectVMEvaluationConfig, *, live_write: SubjectVMLiveWriteConfig
) -> None:
    if cfg.schema != SUBJECT_VM_EVALUATION_SCHEMA or not cfg.enabled:
        raise ValueError(
            f"Stage-3C-5 subject_vm requires enabled evaluation schema {SUBJECT_VM_EVALUATION_SCHEMA!r}"
        )
    if not 1 <= cfg.capacity_per_subject <= 64:
        raise ValueError("subject_vm evaluation capacity_per_subject must be in [1, 64]")
    if not 1 <= cfg.observation_ticks < live_write.rollback_after_ticks:
        raise ValueError(
            "subject_vm evaluation observation_ticks must be in [1, rollback_after_ticks)"
        )
    if cfg.control_horizon_ticks != live_write.rollback_after_ticks:
        raise ValueError(
            "subject_vm evaluation control_horizon_ticks must equal rollback_after_ticks"
        )
    if not 0.0 < cfg.fact_clip <= 1_000_000.0:
        raise ValueError("subject_vm evaluation fact_clip must be in (0, 1000000]")
    costs = (cfg.registration_cost_units, cfg.per_observation_cost_units)
    if any(not 0 <= int(value) <= 1_000_000 for value in costs):
        raise ValueError("subject_vm evaluation counted costs must be in [0, 1000000]")


def validate_subject_vm_config(cfg: SubjectVMConfig) -> None:
    """Validate the frozen Stage-1 through Stage-3C-5 contracts."""
    if cfg.enabled:
        if cfg.schema not in {
            SUBJECT_VM_STAGE1_SCHEMA,
            SUBJECT_VM_STAGE2_SCHEMA,
            SUBJECT_VM_STAGE3_SCHEMA,
            SUBJECT_VM_STAGE3B_SCHEMA,
            SUBJECT_VM_STAGE3B2_SCHEMA,
            SUBJECT_VM_STAGE3B3_SCHEMA,
            SUBJECT_VM_STAGE3C1_SCHEMA,
            SUBJECT_VM_STAGE3C2_SCHEMA,
            SUBJECT_VM_STAGE3C3_SCHEMA,
            SUBJECT_VM_STAGE3C4_SCHEMA,
            SUBJECT_VM_STAGE3C5_SCHEMA,
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
            _validate_disabled_modulation(cfg.modulation)
            _validate_disabled_target_binding(cfg.target_binding)
            _validate_disabled_update_safety(cfg.update_safety)
            _validate_disabled_transaction(cfg.transaction)
            _validate_disabled_live_write(cfg.live_write)
            _validate_disabled_evaluation(cfg.evaluation)
            _validate_thought_event_extension(cfg)
            return

        _validate_activation(cfg.activation)
        if cfg.schema == SUBJECT_VM_STAGE2_SCHEMA:
            _validate_disabled_trace(cfg.trace)
            _validate_disabled_eligibility(cfg.eligibility)
            _validate_disabled_association(cfg.association)
            _validate_disabled_modulation(cfg.modulation)
            _validate_disabled_target_binding(cfg.target_binding)
            _validate_disabled_update_safety(cfg.update_safety)
            _validate_disabled_transaction(cfg.transaction)
            _validate_disabled_live_write(cfg.live_write)
            _validate_disabled_evaluation(cfg.evaluation)
            _validate_thought_event_extension(cfg)
            return

        _validate_trace(cfg.trace)
        if cfg.schema == SUBJECT_VM_STAGE3_SCHEMA:
            _validate_disabled_eligibility(cfg.eligibility)
            _validate_disabled_association(cfg.association)
            _validate_disabled_modulation(cfg.modulation)
            _validate_disabled_target_binding(cfg.target_binding)
            _validate_disabled_update_safety(cfg.update_safety)
            _validate_disabled_transaction(cfg.transaction)
            _validate_disabled_live_write(cfg.live_write)
            _validate_disabled_evaluation(cfg.evaluation)
            _validate_thought_event_extension(cfg)
            return

        _validate_eligibility(cfg.eligibility)
        if cfg.schema == SUBJECT_VM_STAGE3B_SCHEMA:
            _validate_disabled_association(cfg.association)
            _validate_disabled_modulation(cfg.modulation)
            _validate_disabled_target_binding(cfg.target_binding)
            _validate_disabled_update_safety(cfg.update_safety)
            _validate_disabled_transaction(cfg.transaction)
            _validate_disabled_live_write(cfg.live_write)
            _validate_disabled_evaluation(cfg.evaluation)
            _validate_thought_event_extension(cfg)
            return

        _validate_association(
            cfg.association,
            trace=cfg.trace,
            eligibility=cfg.eligibility,
        )
        if cfg.schema == SUBJECT_VM_STAGE3B2_SCHEMA:
            _validate_disabled_modulation(cfg.modulation)
            _validate_disabled_target_binding(cfg.target_binding)
            _validate_disabled_update_safety(cfg.update_safety)
            _validate_disabled_transaction(cfg.transaction)
            _validate_disabled_live_write(cfg.live_write)
            _validate_disabled_evaluation(cfg.evaluation)
            _validate_thought_event_extension(cfg)
            return

        _validate_modulation(
            cfg.modulation,
            trace=cfg.trace,
            association=cfg.association,
        )
        if cfg.schema == SUBJECT_VM_STAGE3B3_SCHEMA:
            _validate_disabled_target_binding(cfg.target_binding)
            _validate_disabled_update_safety(cfg.update_safety)
            _validate_disabled_transaction(cfg.transaction)
            _validate_disabled_live_write(cfg.live_write)
            _validate_disabled_evaluation(cfg.evaluation)
            _validate_thought_event_extension(cfg)
            return

        _validate_target_binding(cfg.target_binding, eligibility=cfg.eligibility)
        if cfg.schema == SUBJECT_VM_STAGE3C1_SCHEMA:
            _validate_disabled_update_safety(cfg.update_safety)
            _validate_disabled_transaction(cfg.transaction)
            _validate_disabled_live_write(cfg.live_write)
            _validate_disabled_evaluation(cfg.evaluation)
        elif cfg.schema == SUBJECT_VM_STAGE3C2_SCHEMA:
            _validate_update_safety(cfg.update_safety)
            _validate_disabled_transaction(cfg.transaction)
            _validate_disabled_live_write(cfg.live_write)
            _validate_disabled_evaluation(cfg.evaluation)
        elif cfg.schema == SUBJECT_VM_STAGE3C3_SCHEMA:
            _validate_update_safety(cfg.update_safety)
            _validate_transaction(cfg.transaction)
            _validate_disabled_live_write(cfg.live_write)
            _validate_disabled_evaluation(cfg.evaluation)
        elif cfg.schema == SUBJECT_VM_STAGE3C4_SCHEMA:
            _validate_update_safety(cfg.update_safety)
            _validate_transaction(cfg.transaction)
            _validate_live_write(cfg.live_write, trace=cfg.trace)
            _validate_disabled_evaluation(cfg.evaluation)
        else:
            _validate_update_safety(cfg.update_safety)
            _validate_transaction(cfg.transaction)
            _validate_live_write(cfg.live_write, trace=cfg.trace)
            _validate_evaluation(cfg.evaluation, live_write=cfg.live_write)
        _validate_thought_event_extension(cfg)
        return

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
    _validate_disabled_modulation(cfg.modulation)
    _validate_disabled_target_binding(cfg.target_binding)
    _validate_disabled_update_safety(cfg.update_safety)
    _validate_disabled_transaction(cfg.transaction)
    _validate_disabled_live_write(cfg.live_write)
    _validate_disabled_evaluation(cfg.evaluation)
    _validate_disabled_thought_event(cfg.thought_event)


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


def _disabled_modulation_payload(value: Any) -> bool:
    if value is None:
        return True
    if not isinstance(value, Mapping):
        return False
    return (
        value.get("schema") == SUBJECT_VM_MODULATION_DISABLED_SCHEMA
        and int(value.get("request_token_port", -1)) == -1
        and float(value.get("request_threshold", 0.0)) == 0.0
        and int(value.get("fact_weight_start_port", -1)) == -1
        and int(value.get("target_weight_start_port", -1)) == -1
        and float(value.get("proposal_clip", 0.0)) == 0.0
    )


def _disabled_target_binding_payload(value: Any) -> bool:
    if value is None:
        return True
    if not isinstance(value, Mapping):
        return False
    return (
        value.get("schema") == SUBJECT_VM_TARGET_BINDING_DISABLED_SCHEMA
        and float(value.get("min_abs_eligibility", 0.0)) == 0.0
    )


def _disabled_update_safety_payload(value: Any) -> bool:
    if value is None:
        return True
    if not isinstance(value, Mapping):
        return False
    return (
        value.get("schema") == SUBJECT_VM_UPDATE_SAFETY_DISABLED_SCHEMA
        and float(value.get("step_scale", 0.0)) == 0.0
        and float(value.get("min_abs_delta", 0.0)) == 0.0
        and tuple(value.get("family_delta_clip", ())) == ()
        and float(value.get("event_l1_budget", 0.0)) == 0.0
        and tuple(value.get("parameter_lower_bounds", ())) == ()
        and tuple(value.get("parameter_upper_bounds", ())) == ()
    )


def _disabled_transaction_payload(value: Any) -> bool:
    if value is None:
        return True
    if not isinstance(value, Mapping):
        return False
    return (
        value.get("schema") == SUBJECT_VM_TRANSACTION_DISABLED_SCHEMA
        and int(value.get("max_targets_per_event", 0)) == 0
        and int(value.get("base_cost_units", 0)) == 0
        and int(value.get("per_target_cost_units", 0)) == 0
    )


def _disabled_live_write_payload(value: Any) -> bool:
    if value is None:
        return True
    if not isinstance(value, Mapping):
        return False
    return (
        value.get("schema") == SUBJECT_VM_LIVE_WRITE_DISABLED_SCHEMA
        and value.get("enabled") is False
        and int(value.get("ledger_capacity_per_subject", 0)) == 0
        and int(value.get("rollback_after_ticks", 0)) == 0
        and int(value.get("window_ticks", 0)) == 0
        and int(value.get("max_pending_transactions", 0)) == 0
        and int(value.get("max_applied_targets_per_window", 0)) == 0
        and float(value.get("max_abs_delta_per_window", 0.0)) == 0.0
        and int(value.get("commit_base_cost_units", 0)) == 0
        and int(value.get("commit_per_target_cost_units", 0)) == 0
        and int(value.get("rollback_base_cost_units", 0)) == 0
        and int(value.get("rollback_per_target_cost_units", 0)) == 0
    )


def _disabled_evaluation_payload(value: Any) -> bool:
    if value is None:
        return True
    if not isinstance(value, Mapping):
        return False
    return (
        value.get("schema") == SUBJECT_VM_EVALUATION_DISABLED_SCHEMA
        and value.get("enabled") is False
        and int(value.get("capacity_per_subject", 0)) == 0
        and int(value.get("observation_ticks", 0)) == 0
        and int(value.get("control_horizon_ticks", 0)) == 0
        and float(value.get("fact_clip", 0.0)) == 0.0
        and int(value.get("registration_cost_units", 0)) == 0
        and int(value.get("per_observation_cost_units", 0)) == 0
    )


def _disabled_thought_event_recall_payload(value: Any) -> bool:
    if value is None:
        return True
    if not isinstance(value, Mapping):
        return False
    return (
        value.get("schema") == SUBJECT_VM_THOUGHT_EVENT_RECALL_DISABLED_SCHEMA
        and value.get("enabled") is False
        and value.get("content_mode", "identity") == "identity"
        and int(value.get("min_age_ticks", 0)) == 0
        and int(value.get("max_ingress_paths", 0)) == 0
        and int(value.get("search_per_slot_cost_units", 0)) == 0
        and int(value.get("read_base_cost_units", 0)) == 0
        and int(value.get("read_per_coordinate_cost_units", 0)) == 0
        and int(value.get("ingress_per_path_cost_units", 0)) == 0
    )


def _disabled_thought_event_payload(value: Any) -> bool:
    if value is None:
        return True
    if not isinstance(value, Mapping):
        return False
    return (
        value.get("schema") == SUBJECT_VM_THOUGHT_EVENT_DISABLED_SCHEMA
        and value.get("enabled") is False
        and int(value.get("capacity_per_subject", 0)) == 0
        and int(value.get("max_parent_count", 0)) == 0
        and int(value.get("retention_ticks", 0)) == 0
        and int(value.get("emission_base_cost_units", 0)) == 0
        and int(value.get("emission_per_coordinate_cost_units", 0)) == 0
        and int(value.get("parent_link_cost_units", 0)) == 0
        and int(value.get("retention_per_event_tick_cost_units", 0)) == 0
        and _disabled_thought_event_recall_payload(value.get("recall"))
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
    if isinstance(section, dict) and _disabled_modulation_payload(
        section.get("modulation")
    ):
        section.pop("modulation", None)
    if isinstance(section, dict) and _disabled_target_binding_payload(
        section.get("target_binding")
    ):
        section.pop("target_binding", None)
    if isinstance(section, dict) and _disabled_update_safety_payload(
        section.get("update_safety")
    ):
        section.pop("update_safety", None)
    if isinstance(section, dict) and _disabled_transaction_payload(
        section.get("transaction")
    ):
        section.pop("transaction", None)
    if isinstance(section, dict) and _disabled_live_write_payload(
        section.get("live_write")
    ):
        section.pop("live_write", None)
    if isinstance(section, dict) and _disabled_evaluation_payload(
        section.get("evaluation")
    ):
        section.pop("evaluation", None)
    if isinstance(section, dict):
        thought_event_section = section.get("thought_event")
        if isinstance(thought_event_section, dict) and _disabled_thought_event_recall_payload(
            thought_event_section.get("recall")
        ):
            thought_event_section.pop("recall", None)
    if isinstance(section, dict) and _disabled_thought_event_payload(
        section.get("thought_event")
    ):
        section.pop("thought_event", None)
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
    "SUBJECT_VM_MODULATION_DISABLED_SCHEMA",
    "SUBJECT_VM_MODULATION_FACT_WIDTH",
    "SUBJECT_VM_MODULATION_SCHEMA",
    "SUBJECT_VM_MODULATION_TARGET_NAMES",
    "SUBJECT_VM_MODULATION_TARGET_WIDTH",
    "SUBJECT_VM_OBJECTIVE_EVENT_SCHEMA",
    "SUBJECT_VM_OUTPUT_PORT_SCHEMA",
    "SUBJECT_VM_REGION_NAMES",
    "SUBJECT_VM_STAGE1_SCHEMA",
    "SUBJECT_VM_STAGE2_SCHEMA",
    "SUBJECT_VM_STAGE3_SCHEMA",
    "SUBJECT_VM_STAGE3B_SCHEMA",
    "SUBJECT_VM_STAGE3B2_SCHEMA",
    "SUBJECT_VM_STAGE3B3_SCHEMA",
    "SUBJECT_VM_STAGE3C1_SCHEMA",
    "SUBJECT_VM_STAGE3C2_SCHEMA",
    "SUBJECT_VM_STAGE3C3_SCHEMA",
    "SUBJECT_VM_STAGE3C4_SCHEMA",
    "SUBJECT_VM_STAGE3C5_SCHEMA",
    "SUBJECT_VM_TARGET_BINDING_DISABLED_SCHEMA",
    "SUBJECT_VM_TARGET_BINDING_SCHEMA",
    "SUBJECT_VM_UPDATE_SAFETY_DISABLED_SCHEMA",
    "SUBJECT_VM_UPDATE_SAFETY_SCHEMA",
    "SUBJECT_VM_TRANSACTION_DISABLED_SCHEMA",
    "SUBJECT_VM_TRANSACTION_SCHEMA",
    "SUBJECT_VM_LIVE_WRITE_DISABLED_SCHEMA",
    "SUBJECT_VM_LIVE_WRITE_SCHEMA",
    "SUBJECT_VM_EVALUATION_DISABLED_SCHEMA",
    "SUBJECT_VM_EVALUATION_SCHEMA",
    "SUBJECT_VM_TRACE_DISABLED_SCHEMA",
    "SUBJECT_VM_TRACE_SCHEMA",
    "SUBJECT_VM_THOUGHT_EVENT_DISABLED_SCHEMA",
    "SUBJECT_VM_THOUGHT_EVENT_SCHEMA",
    "SUBJECT_VM_THOUGHT_EVENT_RECALL_DISABLED_SCHEMA",
    "SUBJECT_VM_THOUGHT_EVENT_RECALL_SCHEMA",
    "SUBJECT_VM_THOUGHT_EVENT_RECALL_CONTENT_MODES",
    "SubjectVMActivationConfig",
    "SubjectVMAssociationConfig",
    "SubjectVMConfig",
    "SubjectVMModulationConfig",
    "SubjectVMEligibilityConfig",
    "SubjectVMRegionConfig",
    "SubjectVMTargetBindingConfig",
    "SubjectVMUpdateSafetyConfig",
    "SubjectVMTransactionConfig",
    "SubjectVMLiveWriteConfig",
    "SubjectVMEvaluationConfig",
    "SubjectVMTraceConfig",
    "SubjectVMThoughtEventConfig",
    "SubjectVMThoughtEventRecallConfig",
    "load_subject_vm_config",
    "strip_disabled_subject_vm_section",
    "validate_subject_vm_config",
]
