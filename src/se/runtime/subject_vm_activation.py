"""Narrow Simulation adapter for Subject VM objective inputs and action outputs."""
from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

from ..policy import Action
from ..subject_vm import SubjectVMRuntime, build_objective_input_ports

if TYPE_CHECKING:
    from ..information import InformationObservation
    from .sim import Simulation


def initialize_subject_vm_runtime(
    simulation: "Simulation", active: np.ndarray
) -> SubjectVMRuntime:
    runtime = SubjectVMRuntime.initialize(
        simulation.cfg.subject_vm,
        entity_capacity=simulation.cfg.world.max_entities,
        active_rows=active,
        entity_ids=simulation.entities.entity_id,
        subject_ids=simulation.entities.primary_subject_id,
    )
    runtime.require_execution_backend(
        simulation.execution_backend, requested_backend=simulation.requested_backend
    )
    return runtime


def subject_vm_action_potentials(
    simulation: "Simulation",
    active: np.ndarray,
    energy: np.ndarray,
    local_resources: np.ndarray,
    information: "InformationObservation",
) -> np.ndarray | None:
    """Return bounded potentials only when an expressed Stage-2 graph exists."""
    runtime = simulation.subject_vm
    runtime.advance_thought_events(active, tick=simulation.tick)
    if not runtime.has_expressed_graph(active):
        simulation._stage_subject_vm_activation_contribution_trace(None)
        return None
    runtime.require_execution_backend(
        simulation.execution_backend, requested_backend=simulation.requested_backend
    )
    inputs = build_objective_input_ports(
        energy=energy,
        max_energy=simulation.cfg.entities.max_energy,
        integrity=simulation.entities.integrity[active],
        fertility=simulation.entities.fertility[active],
        local_resources=local_resources,
        resource_capacity=simulation.cfg.environment.resource_capacity,
        signals=information.signals,
        uncertainty=information.uncertainty,
        retained_policy_state=simulation.entities.memory[active],
    )
    result = runtime.activate(
        rows=active,
        input_values=inputs,
        tick=simulation.tick,
        output_width=len(Action),
        contribution_trace_rows=(
            simulation._subject_vm_activation_contribution_rows(active)
        ),
    )
    simulation._stage_subject_vm_activation_contribution_trace(
        result.contribution_trace
    )
    return result.action_potentials


__all__ = ["initialize_subject_vm_runtime", "subject_vm_action_potentials"]
