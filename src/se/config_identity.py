"""Backward-compatible scientific configuration identities.

Later releases may add opt-in configuration fields with inert defaults.  Such
fields must not rewrite the identity of frozen studies that predate them.  This
module removes only exact, disabled/default extensions; enabled or non-default
values remain part of the identity.
"""
from __future__ import annotations

from copy import deepcopy
from typing import Any

from .subject_vm.config import strip_disabled_subject_vm_section

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
        entities.get("resource_load_schema") == "disabled"
        and float(entities.get("resource_load_speed_penalty_fraction", 0.0)) == 0.0
        and float(entities.get("resource_load_movement_energy_fraction", 0.0)) == 0.0
        and entities.get("resource_contest_schema") == "disabled"
        and float(entities.get("resource_contest_energy_cost_per_pressure", 0.0)) == 0.0
        and float(entities.get("resource_contest_integrity_damage_per_pressure", 0.0)) == 0.0
        and float(entities.get("resource_contest_pressure_retention", 0.0)) == 0.0
        and float(entities.get("resource_contest_signal_weight", 0.0)) == 0.0
        and int(entities.get("resource_contest_radius_cells", 0)) == 0
        and entities.get("danger_sensing_schema") == "disabled"
        and entities.get("danger_message_direction_schema") == "disabled"
        and float(entities.get("danger_message_direction_weight", 0.0)) == 0.0
    ):
        for key in (
            "resource_load_schema",
            "resource_load_speed_penalty_fraction",
            "resource_load_movement_energy_fraction",
            "resource_contest_schema",
            "resource_contest_energy_cost_per_pressure",
            "resource_contest_integrity_damage_per_pressure",
            "resource_contest_pressure_retention",
            "resource_contest_signal_weight",
            "resource_contest_radius_cells",
            "danger_sensing_schema",
            "danger_message_direction_schema",
            "danger_message_direction_weight",
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

    if (
        run.get("reconnaissance_diagnostics_enabled") is False
        and run.get("reconnaissance_diagnostics_schema") == "disabled"
        and int(run.get("reconnaissance_window_ticks", 120)) == 120
    ):
        for key in (
            "reconnaissance_diagnostics_enabled",
            "reconnaissance_diagnostics_schema",
            "reconnaissance_window_ticks",
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

    if (
        environment.get("signal_propagation_schema", "uniform-isotropic-v1")
        == "uniform-isotropic-v1"
        and float(environment.get("signal_terrain_resistance_fraction", 0.0)) == 0.0
        and environment.get("signal_medium_schema", "disabled") == "disabled"
        and float(environment.get("signal_medium_conductance_fraction", 0.0)) == 0.0
        and float(environment.get("signal_openness_floor", 1.0)) == 1.0
        and float(environment.get("signal_openness_amplitude", 0.0)) == 0.0
        and int(environment.get("signal_openness_period", 0)) == 0
        and float(environment.get("signal_openness_wave_x", 1.0)) == 1.0
        and float(environment.get("signal_openness_wave_y", 0.0)) == 0.0
        and float(environment.get("signal_openness_phase_offset", 0.0)) == 0.0
    ):
        for key in (
            "signal_propagation_schema",
            "signal_terrain_resistance_fraction",
            "signal_medium_schema",
            "signal_medium_conductance_fraction",
            "signal_openness_floor",
            "signal_openness_amplitude",
            "signal_openness_period",
            "signal_openness_wave_x",
            "signal_openness_wave_y",
            "signal_openness_phase_offset",
        ):
            environment.pop(key, None)

    information = result.get("information", {})
    if (
        information.get(
            "resource_signal_observation_schema", "pre-action-local-v1"
        )
        == "pre-action-local-v1"
        and information.get(
            "direct_message_propagation_schema", "unbounded-direct-v1"
        )
        == "unbounded-direct-v1"
        and float(
            information.get("direct_message_distance_decay_per_cell", 0.0)
        )
        == 0.0
        and float(
            information.get("direct_message_terrain_resistance_fraction", 0.0)
        )
        == 0.0
        and float(
            information.get("direct_message_medium_resistance_fraction", 0.0)
        )
        == 0.0
    ):
        for key in (
            "resource_signal_observation_schema",
            "direct_message_propagation_schema",
            "direct_message_distance_decay_per_cell",
            "direct_message_terrain_resistance_fraction",
            "direct_message_medium_resistance_fraction",
        ):
            information.pop(key, None)

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
        social.get("relation_update_schema", "fixed-share-trust-v1")
        == "fixed-share-trust-v1"
        and int(social.get("interest_feedback_window_ticks", 0)) == 0
        and float(social.get("interest_feedback_learning_rate", 0.0)) == 0.0
        and float(social.get("interest_feedback_min_material", 0.0)) == 0.0
        and int(social.get("knowledge_interest_window_ticks", 0)) == 0
        and float(social.get("knowledge_interest_learning_rate", 0.0)) == 0.0
        and float(social.get("knowledge_interest_min_evidence", 0.0)) == 0.0
    ):
        for key in (
            "relation_update_schema",
            "interest_feedback_window_ticks",
            "interest_feedback_learning_rate",
            "interest_feedback_min_material",
            "knowledge_interest_window_ticks",
            "knowledge_interest_learning_rate",
            "knowledge_interest_min_evidence",
        ):
            social.pop(key, None)
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

    strip_disabled_subject_vm_section(result)
    return result


__all__ = ["strip_inactive_extensions"]
