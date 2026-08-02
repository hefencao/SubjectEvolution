"""Nested-subject existence evolution reference implementation."""

from .backend import Backend, BackendUnavailableError, resolve_backend, to_backend, to_numpy

__version__ = "0.130.0"

__all__ = [
    "Backend",
    "BackendUnavailableError",
    "resolve_backend",
    "to_backend",
    "to_numpy",
]
