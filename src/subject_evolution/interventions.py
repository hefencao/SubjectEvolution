"""Typed experiment interventions and protocol boundaries.

The registry keeps causal observation interventions separate from direct
action replacement.  The latter remains useful for demos and stress tests,
but is deliberately unavailable to the default scientific protocol.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class ExperimentMode(str, Enum):
    SCIENTIFIC = "scientific"
    ENTERTAINMENT = "entertainment"


class InterventionKind(str, Enum):
    INTRODUCE_EXISTENCE = "introduce-existence"
    MODIFY_EXISTENCE = "modify-existence"
    MODIFY_ENVIRONMENT = "modify-environment"
    MODIFY_RULES = "modify-rules"
    DIRECT_ACTION = "direct-action"


@dataclass(frozen=True)
class InterventionSpec:
    name: str
    kind: InterventionKind
    target_scope: str
    aliases: tuple[str, ...] = ()
    direct_action_control: bool = False
    scientific_allowed: bool = True

    def require_mode(self, mode: ExperimentMode) -> None:
        if mode is ExperimentMode.SCIENTIFIC and not self.scientific_allowed:
            raise ValueError(
                f"Intervention '{self.name}' directly replaces actions and is not "
                "valid in scientific mode; explicitly use entertainment mode."
            )


INTERVENTIONS = (
    InterventionSpec(
        "disable-social-control",
        InterventionKind.MODIFY_EXISTENCE,
        "social-controller-output",
        aliases=("social-control-off",),
    ),
    InterventionSpec(
        "cut-social-connections",
        InterventionKind.MODIFY_EXISTENCE,
        "social-relations-and-direct-messages",
        aliases=("cut-social",),
    ),
    InterventionSpec(
        "shuffle-memory",
        InterventionKind.MODIFY_EXISTENCE,
        "entity-memory-state",
    ),
    InterventionSpec(
        "ablate-working-memory",
        InterventionKind.MODIFY_EXISTENCE,
        "quantized-working-memory-state-and-updates",
        aliases=("working-memory-off",),
    ),
    InterventionSpec(
        "bypass-sparse-selection",
        InterventionKind.MODIFY_RULES,
        "ephemeral-knowledge-topk-selector",
        aliases=("selection-off", "topk-off"),
    ),
    InterventionSpec(
        "neutralize-resource-affinity",
        InterventionKind.MODIFY_RULES,
        "inherited-four-resource-affinity-expression",
        aliases=("resource-affinity-off", "affinity-off"),
    ),
    InterventionSpec(
        "disable-knowledge-policy",
        InterventionKind.MODIFY_RULES,
        "knowledge-policy-residual-publication",
        aliases=("knowledge-residual-off", "knowledge-policy-off"),
    ),
    InterventionSpec(
        "disable-knowledge-transfer",
        InterventionKind.MODIFY_RULES,
        "future-knowledge-copy-transfer",
        aliases=("knowledge-transfer-off", "transfer-off"),
    ),
    InterventionSpec(
        "freeze-genotype",
        InterventionKind.MODIFY_RULES,
        "inheritance-mutation-rule",
        aliases=("freeze-genetic-expression",),
    ),
    InterventionSpec(
        "reverse-environment",
        InterventionKind.MODIFY_ENVIRONMENT,
        "resource-and-danger-spatial-fields",
        aliases=("environment-reversal",),
    ),
    InterventionSpec(
        "independent-foraging-override",
        InterventionKind.DIRECT_ACTION,
        "carrier-action-decision",
        aliases=("restore-autonomy", "restore-foraging-autonomy"),
        direct_action_control=True,
        scientific_allowed=False,
    ),
)

_BY_NAME = {
    alias: spec
    for spec in INTERVENTIONS
    for alias in (spec.name, *spec.aliases)
}


def normalize_intervention_name(name: str) -> str:
    return name.strip().lower().replace("_", "-")


def resolve_intervention(name: str) -> InterventionSpec:
    normalized = normalize_intervention_name(name)
    try:
        return _BY_NAME[normalized]
    except KeyError as exc:
        choices = ", ".join(spec.name for spec in INTERVENTIONS)
        raise ValueError(f"Unknown intervention. Expected one of: {choices}.") from exc


def intervention_names(*, mode: ExperimentMode | None = None) -> tuple[str, ...]:
    return tuple(
        spec.name
        for spec in INTERVENTIONS
        if mode is None or mode is ExperimentMode.ENTERTAINMENT or spec.scientific_allowed
    )


__all__ = [
    "ExperimentMode",
    "INTERVENTIONS",
    "InterventionKind",
    "InterventionSpec",
    "intervention_names",
    "normalize_intervention_name",
    "resolve_intervention",
]
