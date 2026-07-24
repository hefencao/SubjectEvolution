from pathlib import Path

text = (Path(__file__).resolve().parents[1] / "src/gui/src/main.cpp").read_text()
assert "KEY_Y" in text
assert "next_overlay_temporal" in text
assert "overlay_temporal_name" in text

apply_start = text.index("void apply_observation_preset")
migration_start = text.index("case ObservationPreset::Migration:", apply_start)
migration_end = text.index("case ObservationPreset::Social:", migration_start)
migration = text[migration_start:migration_end]
assert "OverlayTemporalMode::Stable" in text[apply_start:migration_end]
assert "show_velocity = false" in migration
assert "BehaviorOverlayMode::Groups" in migration

survival_start = text.index("case ObservationPreset::Survival:", apply_start)
survival_end = text.index("case ObservationPreset::Reproduction:", survival_start)
survival = text[survival_start:survival_end]
assert "show_group_trails = true" in survival
assert "show_group_landmarks = true" in survival
assert "BehaviorOverlayMode::Combined" in survival
assert "ActionFilterMode::Survival" in survival
print("temporal presets: ok")
