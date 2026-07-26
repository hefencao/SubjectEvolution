"""Low-coupling environmental field-process extension boundary.

The scientific core owns resources, the authoritative hazard field and local
mortality traces. Optional extensions may contribute only an additive scalar
field through this module. They do not receive entity arrays, relations,
lineages, policy state or action hooks, so an extension cannot silently become
a second biological population or controller.

External packages may register factories programmatically or expose a
``se.env.world_processes`` entry point whose loaded zero-arg
callable performs registration. Installed plugins are executable Python code
and must therefore be trusted like any other installed dependency.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
from importlib import metadata as importlib_metadata
import json
import threading
from typing import Any, Callable, Mapping, Protocol, runtime_checkable


ENVIRONMENT_PROCESS_API_SCHEMA = "additive-environment-field-process-v1"
DISABLED_ENVIRONMENT_PROCESS_SCHEMA = "disabled"
LEGACY_MOVING_GAUSSIAN_SCHEMA = "moving-gaussian-hazard-sources-v1"
ENTRY_POINT_GROUP = "se.env.world_processes"


@dataclass(frozen=True, slots=True)
class EnvironmentProcessDescriptor:
    """Stable metadata describing one registered environmental extension."""

    schema: str
    mechanism_class: str
    interpretation: str
    description: str
    api_schema: str = ENVIRONMENT_PROCESS_API_SCHEMA
    default_enabled: bool = False


@runtime_checkable
class EnvironmentFieldProcess(Protocol):
    """Backend-neutral additive hazard-field process.

    ``xnorm`` and ``ynorm`` are normalized periodic grids owned by the core.
    Implementations must return an array with the same two-dimensional shape
    and must not mutate their inputs.
    """

    descriptor: EnvironmentProcessDescriptor

    def hazard_delta(
        self,
        *,
        tick: int,
        xnorm: Any,
        ynorm: Any,
        xp: Any,
    ) -> Any:
        """Return an additive, non-negative scalar hazard field."""


EnvironmentProcessFactory = Callable[[Mapping[str, Any]], EnvironmentFieldProcess]


@dataclass(frozen=True, slots=True)
class ResolvedEnvironmentProcess:
    schema: str
    origin: str
    parameters: Mapping[str, Any]


_REGISTRY: dict[str, tuple[EnvironmentProcessDescriptor, EnvironmentProcessFactory]] = {}
_REGISTRY_LOCK = threading.RLock()
_DISCOVERY_LOCK = threading.RLock()
_DISCOVERY_COMPLETE = False
_DISCOVERY_ERRORS: list[str] = []


def register_environment_process(
    descriptor: EnvironmentProcessDescriptor,
    factory: EnvironmentProcessFactory,
    *,
    replace: bool = False,
) -> None:
    """Register an environment process without modifying the simulation core."""
    schema = str(descriptor.schema).strip()
    if not schema or schema == DISABLED_ENVIRONMENT_PROCESS_SCHEMA:
        raise ValueError("environment process schema must be non-empty and not 'disabled'")
    if descriptor.api_schema != ENVIRONMENT_PROCESS_API_SCHEMA:
        raise ValueError(
            f"environment process {schema!r} uses unsupported API schema "
            f"{descriptor.api_schema!r}"
        )
    if not callable(factory):
        raise TypeError("environment process factory must be callable")
    with _REGISTRY_LOCK:
        if schema in _REGISTRY and not replace:
            raise ValueError(f"environment process schema already registered: {schema}")
        _REGISTRY[schema] = (descriptor, factory)


def unregister_environment_process(schema: str) -> None:
    """Remove a registered process; primarily useful for isolated tests/tools."""
    with _REGISTRY_LOCK:
        _REGISTRY.pop(str(schema), None)


def _load_builtin_plugins() -> None:
    # Importing this module performs explicit registration. Keeping the
    # implementation in ``plugins`` prevents environment.py from depending on
    # any concrete synthetic process.
    from ..plugins import register_builtin_environment_processes

    register_builtin_environment_processes()


def discover_environment_process_plugins() -> tuple[str, ...]:
    """Load built-ins and installed entry-point plugins exactly once."""
    global _DISCOVERY_COMPLETE
    with _DISCOVERY_LOCK:
        if _DISCOVERY_COMPLETE:
            return tuple(_DISCOVERY_ERRORS)
        _load_builtin_plugins()
        try:
            entry_points = importlib_metadata.entry_points()
            selected = (
                entry_points.select(group=ENTRY_POINT_GROUP)
                if hasattr(entry_points, "select")
                else entry_points.get(ENTRY_POINT_GROUP, ())
            )
            for entry_point in selected:
                try:
                    registrar = entry_point.load()
                    if not callable(registrar):
                        raise TypeError("entry point must load a zero-argument callable")
                    registrar()
                except Exception as exc:  # report deterministically at selection time
                    _DISCOVERY_ERRORS.append(
                        f"{getattr(entry_point, 'name', '<unnamed>')}: "
                        f"{type(exc).__name__}: {exc}"
                    )
        finally:
            _DISCOVERY_COMPLETE = True
        return tuple(_DISCOVERY_ERRORS)


def registered_environment_process_schemas() -> tuple[str, ...]:
    discover_environment_process_plugins()
    with _REGISTRY_LOCK:
        return tuple(sorted(_REGISTRY))


def _legacy_parameters(environment: Any) -> dict[str, Any]:
    return {
        "source_count": int(environment.moving_hazard_source_count),
        "amplitude": float(environment.moving_hazard_amplitude),
        "radius": float(environment.moving_hazard_radius),
        "speed": float(environment.moving_hazard_speed),
        "phase_offset": float(environment.moving_hazard_phase_offset),
    }


def resolve_environment_process(environment: Any) -> ResolvedEnvironmentProcess:
    """Resolve new generic configuration or the v0.22 compatibility adapter."""
    schema = str(getattr(environment, "environment_process_schema", "disabled"))
    generic_parameters = getattr(environment, "environment_process_parameters", {})
    legacy_schema = str(getattr(environment, "moving_hazard_schema", "disabled"))
    if schema != DISABLED_ENVIRONMENT_PROCESS_SCHEMA and legacy_schema != "disabled":
        raise ValueError(
            "configure either environment.environment_process_schema or the v0.22 "
            "moving_hazard_schema compatibility fields, not both"
        )
    if schema != DISABLED_ENVIRONMENT_PROCESS_SCHEMA:
        if not isinstance(generic_parameters, Mapping):
            raise ValueError("environment.environment_process_parameters must be an object")
        return ResolvedEnvironmentProcess(
            schema=schema,
            origin="generic-plugin-config",
            parameters=dict(generic_parameters),
        )
    if legacy_schema != "disabled":
        return ResolvedEnvironmentProcess(
            schema=legacy_schema,
            origin="v0.22-moving-hazard-adapter",
            parameters=_legacy_parameters(environment),
        )
    return ResolvedEnvironmentProcess(
        schema=DISABLED_ENVIRONMENT_PROCESS_SCHEMA,
        origin="core-disabled",
        parameters={},
    )


def _validate_json_value(value: Any, *, path: str = "parameters") -> None:
    if value is None or isinstance(value, (str, bool, int, float)):
        return
    if isinstance(value, list):
        for index, item in enumerate(value):
            _validate_json_value(item, path=f"{path}[{index}]")
        return
    if isinstance(value, Mapping):
        for key, item in value.items():
            if not isinstance(key, str):
                raise ValueError(f"{path} keys must be strings")
            _validate_json_value(item, path=f"{path}.{key}")
        return
    raise ValueError(f"{path} must contain only JSON-compatible values")


def _lookup_registered(
    schema: str,
) -> tuple[EnvironmentProcessDescriptor, EnvironmentProcessFactory]:
    errors = discover_environment_process_plugins()
    with _REGISTRY_LOCK:
        registered = _REGISTRY.get(schema)
    if registered is not None:
        return registered
    available = ", ".join(registered_environment_process_schemas()) or "none"
    suffix = f"; plugin discovery errors: {' | '.join(errors)}" if errors else ""
    raise ValueError(
        f"unknown environment process schema {schema!r}; registered schemas: "
        f"{available}{suffix}"
    )


def validate_environment_process_config(environment: Any) -> None:
    resolved = resolve_environment_process(environment)
    _validate_json_value(resolved.parameters)
    if resolved.schema == DISABLED_ENVIRONMENT_PROCESS_SCHEMA:
        if resolved.parameters:
            raise ValueError("disabled environment process cannot have parameters")
        return
    descriptor, factory = _lookup_registered(resolved.schema)
    process = factory(dict(resolved.parameters))
    if not isinstance(process, EnvironmentFieldProcess):
        raise TypeError(
            f"environment process factory for {resolved.schema!r} returned an "
            "object that does not implement EnvironmentFieldProcess"
        )
    if process.descriptor != descriptor:
        raise ValueError(
            f"environment process {resolved.schema!r} returned descriptor metadata "
            "that differs from its registry entry"
        )


def build_environment_process(environment: Any) -> EnvironmentFieldProcess | None:
    resolved = resolve_environment_process(environment)
    if resolved.schema == DISABLED_ENVIRONMENT_PROCESS_SCHEMA:
        return None
    descriptor, factory = _lookup_registered(resolved.schema)
    process = factory(dict(resolved.parameters))
    if process.descriptor != descriptor:
        raise ValueError(
            f"environment process {resolved.schema!r} returned inconsistent descriptor"
        )
    return process


def environment_process_metadata(environment: Any) -> dict[str, Any]:
    """Return reproducibility/interpretation metadata without exposing code hooks."""
    resolved = resolve_environment_process(environment)
    if resolved.schema == DISABLED_ENVIRONMENT_PROCESS_SCHEMA:
        return {
            "api_schema": ENVIRONMENT_PROCESS_API_SCHEMA,
            "schema": DISABLED_ENVIRONMENT_PROCESS_SCHEMA,
            "origin": resolved.origin,
            "mechanism_class": "none",
            "interpretation": "scientific-core-only",
            "default_enabled": False,
            "parameter_names": [],
            "parameters_sha256": hashlib.sha256(b"{}").hexdigest(),
        }
    descriptor, _ = _lookup_registered(resolved.schema)
    payload = json.dumps(
        dict(resolved.parameters), ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return {
        "api_schema": descriptor.api_schema,
        "schema": descriptor.schema,
        "origin": resolved.origin,
        "mechanism_class": descriptor.mechanism_class,
        "interpretation": descriptor.interpretation,
        "description": descriptor.description,
        "default_enabled": descriptor.default_enabled,
        "parameter_names": sorted(resolved.parameters),
        "parameters_sha256": hashlib.sha256(payload).hexdigest(),
    }


__all__ = [
    "DISABLED_ENVIRONMENT_PROCESS_SCHEMA",
    "ENTRY_POINT_GROUP",
    "ENVIRONMENT_PROCESS_API_SCHEMA",
    "EnvironmentFieldProcess",
    "EnvironmentProcessDescriptor",
    "LEGACY_MOVING_GAUSSIAN_SCHEMA",
    "ResolvedEnvironmentProcess",
    "build_environment_process",
    "discover_environment_process_plugins",
    "environment_process_metadata",
    "register_environment_process",
    "registered_environment_process_schemas",
    "resolve_environment_process",
    "unregister_environment_process",
    "validate_environment_process_config",
]
