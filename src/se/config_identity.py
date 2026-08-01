"""Backward-compatible scientific configuration identities.

Later releases may add opt-in configuration fields with inert defaults.  Such
fields must not rewrite the identity of frozen studies that predate them.  This
module removes only exact, disabled/default extensions; enabled or non-default
values remain part of the identity.
"""
from __future__ import annotations

from copy import deepcopy
from typing import Any

_STRUCTURED_CENTERS = (
    (0.18, 0.18),
    (0.82, 0.22),
    (0.24, 0.80),
    (0.78, 0.76),
)
_STRUCTURED_RADII = (0.16, 0.18, 0.20, 0.17)
_STRUCTURED_CONTRASTS = (0.85, 0.82, 0.80, 0.84)
_STRUCTURED_SECONDARY_WEIGHT = 0.35
_STRUCTURED_PROCESSING_OFFSETS = (
    (0.28, 0.20),
    (-0.24, 0.26),
    (0.26, -0.22),
    (-0.28, -0.24),
)
_IDENTITY_RECIPE = (
    (1.0, 0.0, 0.0, 0.0),
    (0.0, 1.0, 0.0, 0.0),
    (0.0, 0.0, 1.0, 0.0),
    (0.0, 0.0, 0.0, 1.0),
)
_ZERO_RECIPE_EFFECTS = ((0.0, 0.0, 0.0, 0.0, 0.0),) * 4
_ZERO_RECIPE_RATES = (0.0, 0.0, 0.0, 0.0)


def _nested_tuple(value: Any) -> Any:
    if isinstance(value, list):
        return tuple(_nested_tuple(item) for item in value)
    if isinstance(value, tuple):
        return tuple(_nested_tuple(item) for item in value)
    return value


def strip_inactive_extensions(payload: dict[str, Any]) -> dict[str, Any]:
    """Return a copy with exact inert compatibility extensions removed."""
    result = deepcopy(payload)

    entities = result.get("entities", {})
    if (
        entities.get("resource_sensing_schema") == "disabled"
        and _nested_tuple(entities.get("resource_sensing_radius_levels", (1,))) == (1,)
        and float(entities.get("resource_sensing_maintenance_energy_per_radius", 0.0)) == 0.0
        and float(entities.get("resource_sensing_use_energy_per_radius", 0.0)) == 0.0
        and float(entities.get("resource_sensing_development_energy_per_radius", 0.0)) == 0.0
    ):
        for key in (
            "resource_sensing_schema",
            "resource_sensing_radius_levels",
            "resource_sensing_maintenance_energy_per_radius",
            "resource_sensing_use_energy_per_radius",
            "resource_sensing_development_energy_per_radius",
        ):
            entities.pop(key, None)
    if (
        entities.get("reproduction_schema") == "legacy-fixed-threshold-loss-v1"
        and float(entities.get("reproduction_parent_reserve", 0.0)) == 0.0
        and _nested_tuple(entities.get("reproduction_investment_levels", (0.0,))) == (0.0,)
    ):
        for key in (
            "reproduction_schema",
            "reproduction_parent_reserve",
            "reproduction_investment_levels",
        ):
            entities.pop(key, None)

    run = result.get("run", {})
    if (
        run.get("group_function_diagnostics_enabled") is False
        and run.get("group_function_diagnostics_schema") == "disabled"
        and int(run.get("group_function_window_ticks", 120)) == 120
    ):
        for key in (
            "group_function_diagnostics_enabled",
            "group_function_diagnostics_schema",
            "group_function_window_ticks",
        ):
            run.pop(key, None)

    environment = result.get("environment", {})
    if (
        environment.get("schema") != "structured-province-resource-network-v4"
        and _nested_tuple(environment.get("resource_province_centers", _STRUCTURED_CENTERS))
        == _STRUCTURED_CENTERS
        and _nested_tuple(environment.get("resource_province_radii", _STRUCTURED_RADII))
        == _STRUCTURED_RADII
        and _nested_tuple(environment.get("resource_province_contrasts", _STRUCTURED_CONTRASTS))
        == _STRUCTURED_CONTRASTS
        and float(
            environment.get(
                "resource_province_secondary_weight",
                _STRUCTURED_SECONDARY_WEIGHT,
            )
        )
        == _STRUCTURED_SECONDARY_WEIGHT
        and _nested_tuple(
            environment.get(
                "resource_processing_province_offsets",
                _STRUCTURED_PROCESSING_OFFSETS,
            )
        )
        == _STRUCTURED_PROCESSING_OFFSETS
    ):
        for key in (
            "resource_province_centers",
            "resource_province_radii",
            "resource_province_contrasts",
            "resource_province_secondary_weight",
            "resource_processing_province_offsets",
        ):
            environment.pop(key, None)

    physiology = result.get("physiology", {})
    if (
        physiology.get("resource_conversion_network_schema")
        == "independent-channel-effects-v1"
        and _nested_tuple(
            physiology.get("resource_recipe_stoichiometry", _IDENTITY_RECIPE)
        )
        == _IDENTITY_RECIPE
        and _nested_tuple(
            physiology.get("resource_recipe_effect_matrix", _ZERO_RECIPE_EFFECTS)
        )
        == _ZERO_RECIPE_EFFECTS
        and _nested_tuple(
            physiology.get("resource_recipe_rate_per_tick", _ZERO_RECIPE_RATES)
        )
        == _ZERO_RECIPE_RATES
    ):
        for key in (
            "resource_conversion_network_schema",
            "resource_recipe_stoichiometry",
            "resource_recipe_effect_matrix",
            "resource_recipe_rate_per_tick",
        ):
            physiology.pop(key, None)

    social = result.get("social", {})
    if (
        social.get("share_schema") == "energy-only-v1"
        and float(social.get("resource_share_amount", 0.0)) == 0.0
        and float(social.get("resource_share_reserve_fraction", 0.25)) == 0.25
    ):
        for key in (
            "share_schema",
            "resource_share_amount",
            "resource_share_reserve_fraction",
        ):
            social.pop(key, None)

    return result


__all__ = ["strip_inactive_extensions"]
