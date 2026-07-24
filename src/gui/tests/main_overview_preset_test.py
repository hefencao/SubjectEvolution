from pathlib import Path

text = (Path(__file__).resolve().parents[1] / "src/gui/src/main.cpp").read_text()
apply_start = text.index("void apply_observation_preset")
start = text.index("case ObservationPreset::Overview:", apply_start)
end = text.index("case ObservationPreset::Ecology:", start)
block = text[start:end]
assert "show_group_landmarks = true" in block
assert "BehaviorOverlayMode::Combined" in block
assert "ActionFilterMode::All" in block
assert "show_population_density = true" in block
assert "show_event_markers = true" in block
print("overview preset: ok")
