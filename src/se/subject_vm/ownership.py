"""Routing ownership contract for the unified Subject Graph VM.

The project retains several older mechanisms as frozen engineering/scientific
baselines.  Retention does not authorize them to remain co-active as parallel
primary action-residual networks once Stage-2 Subject VM routing is enabled.
This module records their disposition without importing the concrete knowledge,
functional-module, social, or runtime implementations.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Final

ROUTING_OWNERSHIP_SCHEMA: Final = "subject-vm-routing-ownership-v1"
PRIMARY_OPTIONAL_ACTION_ROUTE_OWNER: Final = "subject-vm"
LEGACY_FIXED_COGNITION_BASELINE: Final = "retained-fixed-cognition-baseline"
LEGACY_PHYSICAL_MECHANISM: Final = "retained-physical-mechanism"
LEGACY_OBSERVATIONAL_MECHANISM: Final = "retained-observational-mechanism"
GENERIC_PRIMITIVE_CANDIDATE: Final = "candidate-for-future-generic-extraction"


@dataclass(frozen=True)
class LegacyComponentDisposition:
    """Machine-readable treatment of one pre-Subject-VM component family."""

    component: str
    disposition: str
    owns_action_residual: bool
    may_coexecute_with_stage2: bool
    migration_boundary: str


LEGACY_COMPONENT_DISPOSITIONS: Final = (
    LegacyComponentDisposition(
        component="knowledge-policy-residual",
        disposition=LEGACY_FIXED_COGNITION_BASELINE,
        owns_action_residual=True,
        may_coexecute_with_stage2=False,
        migration_boundary=(
            "retain for old configurations and comparison panels; do not merge its "
            "designer-defined residual state into Subject VM storage"
        ),
    ),
    LegacyComponentDisposition(
        component="latent-router",
        disposition=LEGACY_FIXED_COGNITION_BASELINE,
        owns_action_residual=True,
        may_coexecute_with_stage2=False,
        migration_boundary=(
            "retain quantized implementation as a comparison baseline and source of "
            "generic arithmetic ideas; Subject VM owns primary graph node/edge routing"
        ),
    ),
    LegacyComponentDisposition(
        component="working-memory-router",
        disposition=LEGACY_FIXED_COGNITION_BASELINE,
        owns_action_residual=False,
        may_coexecute_with_stage2=False,
        migration_boundary=(
            "retain checkpointed legacy memory only for latent-router baselines; new "
            "primary persistent state lives in Subject VM node state"
        ),
    ),
    LegacyComponentDisposition(
        component="sparse-selection-router",
        disposition=GENERIC_PRIMITIVE_CANDIDATE,
        owns_action_residual=False,
        may_coexecute_with_stage2=False,
        migration_boundary=(
            "retain inside the latent baseline; any future reuse requires extraction "
            "behind a role-neutral Subject VM gate interface"
        ),
    ),
    LegacyComponentDisposition(
        component="functional-modules",
        disposition=LEGACY_PHYSICAL_MECHANISM,
        owns_action_residual=False,
        may_coexecute_with_stage2=True,
        migration_boundary=(
            "remain embodied physiology/environment mechanisms; they are not copied "
            "into graph storage and may only inspire separately specified generic operators"
        ),
    ),
    LegacyComponentDisposition(
        component="knowledge-provenance-store",
        disposition=LEGACY_OBSERVATIONAL_MECHANISM,
        owns_action_residual=False,
        may_coexecute_with_stage2=True,
        migration_boundary=(
            "remain objective content/provenance facts; later graph access must use a "
            "narrow port or reference adapter rather than duplicate the store"
        ),
    ),
    LegacyComponentDisposition(
        component="candidate-subject-and-group-graphs",
        disposition=LEGACY_OBSERVATIONAL_MECHANISM,
        owns_action_residual=False,
        may_coexecute_with_stage2=True,
        migration_boundary=(
            "remain diagnostics and observational labels; they never own Subject VM "
            "nodes, edges, action bonuses, or plasticity"
        ),
    ),
)


@dataclass(frozen=True)
class RoutingOwnershipView:
    """Narrow cross-domain view used by configuration validation."""

    subject_vm_activation_enabled: bool
    knowledge_policy_influence_enabled: bool
    latent_router_enabled: bool
    working_memory_router_enabled: bool
    sparse_selection_router_enabled: bool


def validate_routing_ownership(view: RoutingOwnershipView) -> None:
    """Reject parallel optional action-routing systems on the primary path.

    The inherited action strategy and physical action arbitration remain the
    stable sensorimotor/output boundary.  This check concerns optional residual
    networks only; knowledge/provenance storage and embodied functional modules
    can remain enabled when they do not publish a competing action residual.
    """
    if not view.subject_vm_activation_enabled:
        return

    conflicts: list[str] = []
    if view.knowledge_policy_influence_enabled:
        conflicts.append("knowledge-policy-residual")
    if view.latent_router_enabled:
        conflicts.append("latent-router")
    if view.working_memory_router_enabled:
        conflicts.append("working-memory-router")
    if view.sparse_selection_router_enabled:
        conflicts.append("sparse-selection-router")
    if conflicts:
        joined = ", ".join(conflicts)
        raise ValueError(
            "Stage-2 subject_vm is the sole optional action-routing owner; "
            f"disable legacy baseline routes before enabling it: {joined}"
        )


def routing_ownership_manifest() -> dict[str, object]:
    """Return the frozen ownership/disposition contract for diagnostics."""
    return {
        "schema": ROUTING_OWNERSHIP_SCHEMA,
        "primary_optional_action_route_owner": PRIMARY_OPTIONAL_ACTION_ROUTE_OWNER,
        "legacy_components": [asdict(item) for item in LEGACY_COMPONENT_DISPOSITIONS],
    }


__all__ = [
    "GENERIC_PRIMITIVE_CANDIDATE",
    "LEGACY_COMPONENT_DISPOSITIONS",
    "LEGACY_FIXED_COGNITION_BASELINE",
    "LEGACY_OBSERVATIONAL_MECHANISM",
    "LEGACY_PHYSICAL_MECHANISM",
    "PRIMARY_OPTIONAL_ACTION_ROUTE_OWNER",
    "ROUTING_OWNERSHIP_SCHEMA",
    "LegacyComponentDisposition",
    "RoutingOwnershipView",
    "routing_ownership_manifest",
    "validate_routing_ownership",
]
