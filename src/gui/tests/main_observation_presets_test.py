from pathlib import Path

text = (Path(__file__).resolve().parents[1] / "src/gui/src/main.cpp").read_text()
for key in ("KEY_F1", "KEY_F2", "KEY_F3", "KEY_F4", "KEY_F5", "KEY_F6"):
    assert key in text, key
for name in ("Overview", "Ecology", "Migration", "Social", "Survival", "Reproduction"):
    assert f"ObservationPreset::{name}" in text, name
assert "next_action_filter" in text
assert "KEY_A" in text
print("observation presets: ok")
