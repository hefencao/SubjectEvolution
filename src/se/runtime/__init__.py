"""Simulation runtime orchestration and state boundaries.

The package keeps public compatibility while loading ``Simulation`` lazily.
GPU support imports low-level runtime modules during device initialization;
eagerly importing the orchestrator here creates an order-dependent cycle.
"""

from __future__ import annotations

from typing import Any

__all__ = ["Simulation", "EntityState", "StepStats", "_wrap_periodic_float32"]


def __getattr__(name: str) -> Any:
    if name == "Simulation":
        from .sim import Simulation

        return Simulation
    if name in {"EntityState", "StepStats", "_wrap_periodic_float32"}:
        from .state import EntityState, StepStats, _wrap_periodic_float32

        return {
            "EntityState": EntityState,
            "StepStats": StepStats,
            "_wrap_periodic_float32": _wrap_periodic_float32,
        }[name]
    raise AttributeError(name)
