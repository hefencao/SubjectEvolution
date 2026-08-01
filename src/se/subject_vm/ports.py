"""Approved objective input and action-potential output port adapters."""
from __future__ import annotations

import numpy as np

SUBJECT_VM_INPUT_PORTS = (
    "constant-one",
    "body-energy-ratio",
    "body-integrity",
    "body-fertility",
    "local-resource-ratio-0",
    "local-resource-ratio-1",
    "local-resource-ratio-2",
    "local-resource-ratio-3",
    "signal-0",
    "signal-1",
    "signal-2",
    "uncertainty-mean",
    "retained-policy-state-0",
    "retained-policy-state-1",
    "retained-policy-state-2",
    "retained-policy-state-3",
)
SUBJECT_VM_OUTPUT_PORTS = tuple(f"action-potential-{index}" for index in range(8))


def build_objective_input_ports(
    *,
    energy: np.ndarray,
    max_energy: float,
    integrity: np.ndarray,
    fertility: np.ndarray,
    local_resources: np.ndarray,
    resource_capacity: tuple[float, float, float, float],
    signals: np.ndarray,
    uncertainty: np.ndarray,
    retained_policy_state: np.ndarray,
) -> np.ndarray:
    """Build the fixed Stage-2 input vector without subjective interpretation."""
    energy = np.asarray(energy, dtype=np.float32)
    integrity = np.asarray(integrity, dtype=np.float32)
    fertility = np.asarray(fertility, dtype=np.float32)
    local_resources = np.asarray(local_resources, dtype=np.float32)
    signals = np.asarray(signals, dtype=np.float32)
    uncertainty = np.asarray(uncertainty, dtype=np.float32)
    retained_policy_state = np.asarray(retained_policy_state, dtype=np.float32)
    count = energy.size
    expected = {
        "integrity": integrity.shape == (count,),
        "fertility": fertility.shape == (count,),
        "local_resources": local_resources.shape == (count, 4),
        "signals": signals.shape == (count, 3),
        "uncertainty": uncertainty.ndim == 2 and uncertainty.shape[0] == count,
        "retained_policy_state": retained_policy_state.shape == (count, 4),
    }
    invalid = [name for name, valid in expected.items() if not valid]
    if invalid:
        raise ValueError(f"subject_vm objective input shapes are invalid: {invalid}")
    capacities = np.asarray(resource_capacity, dtype=np.float32)
    if capacities.shape != (4,) or np.any(capacities <= 0.0):
        raise ValueError("subject_vm resource capacities must be four positive values")
    if max_energy <= 0.0:
        raise ValueError("subject_vm max_energy must be positive")

    result = np.empty((count, len(SUBJECT_VM_INPUT_PORTS)), dtype=np.float32)
    result[:, 0] = 1.0
    result[:, 1] = np.clip(energy / float(max_energy), 0.0, 1.5)
    result[:, 2] = np.clip(integrity, 0.0, 1.0)
    result[:, 3] = np.clip(fertility, 0.0, 2.0)
    result[:, 4:8] = np.clip(local_resources / capacities[None, :], 0.0, 1.5)
    result[:, 8:11] = signals
    result[:, 11] = uncertainty.mean(axis=1)
    result[:, 12:16] = retained_policy_state
    if np.any(~np.isfinite(result)):
        raise ValueError("subject_vm objective input ports must be finite")
    return result


__all__ = [
    "SUBJECT_VM_INPUT_PORTS",
    "SUBJECT_VM_OUTPUT_PORTS",
    "build_objective_input_ports",
]
