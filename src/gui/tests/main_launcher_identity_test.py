from pathlib import Path

root = Path(__file__).resolve().parents[1]
main = (root / "src/gui/src/main.cpp").read_text(encoding="utf-8")
launcher = (root / "src/gui/src/launcher.cpp").read_text(encoding="utf-8")
font = (root / "src/gui/src/ui_font.cpp").read_text(encoding="utf-8")
prefs = (root / "src/gui/src/gui_preferences.cpp").read_text(encoding="utf-8")
combined = main + "\n" + launcher
required = [
    "Subject Evolution Launcher — ",
    "Eco Game Runtime — ",
    "[eco-gui] selected config:",
    "subject_evolution.multi_seed",
    "config_resolved.json",
    "config_runtime_override.json",
    "Extended overrides",
    "Save as new",
    "Confirm replace original",
    "Copy command",
    "BeginScissorMode(",
    "clamp_launcher_scroll(",
    "MultiSeed",
]
missing = [token for token in required if token not in combined]
if missing:
    raise SystemExit(f"launcher v22 identity/source requirements missing: {missing}")
for token in ["DejaVuSansMono.ttf", "NotoSansMono-Regular.ttf", "LiberationMono-Regular.ttf", "GetFontDefault()", "LoadFontEx("]:
    if token not in font:
        raise SystemExit(f"font fallback requirement missing: {token}")
for token in ["project_root / \"src/saves\"", "gui_settings.json", "gui_state.json", "experiment_history.json"]:
    if token not in prefs:
        raise SystemExit(f"saves persistence requirement missing: {token}")
print("launcher v22 identity source check: ok")
