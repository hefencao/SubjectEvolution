from pathlib import Path

root = Path(__file__).resolve().parents[1]
launcher = (root / "src/gui/src/launcher.cpp").read_text(encoding="utf-8")
prefs = (root / "src/gui/src/gui_preferences.cpp").read_text(encoding="utf-8")
monitor = (root / "src/gui/src/multi_seed_monitor.cpp").read_text(encoding="utf-8")

required = [
    "ActionIcon::Settings",
    "ActionIcon::Refresh",
    "ActionIcon::Copy",
    "ActionIcon::Close",
    "ActionIcon::Run",
    "ActionIcon::NewFile",
    "ActionIcon::SaveFile",
    "filled_button(single_rect",
    "filled_button(multi_rect",
    "filled_button(cpu_rect",
    "filled_button(gpu_rect",
    "filled_button(auto_rect",
    "layout.command_preview",
    "layout.command_copy_button",
    "Create a new config from current edits",
    "Confirm permanent overwrite",
    "overwrite partial runs",
    "Temporary overrides apply only to this run",
    "eco::preferences::settings_path(project_root)",
    "ConfigSortMode::Latest",
    "Favorites: on",
    "draw_star_icon",
]
missing = [token for token in required if token not in launcher + prefs]
if missing:
    raise SystemExit(f"launcher v24 controls missing: {missing}")

for forbidden in [
    'button(layout.start_button,',
    'button(layout.close_button,',
    '"Mode"',
    '"Backend"',
    "backend_help",
    'section("Config actions")',
    '"Command preview"',
]:
    if forbidden in launcher:
        raise SystemExit(f"obsolete launcher control remains: {forbidden}")

monitor_required = [
    "multi_seed_index.json",
    "evolution_progress.jsonl",
    "summary.json",
    "SeedStatus::Current",
]
missing = [token for token in monitor_required if token not in monitor]
if missing:
    raise SystemExit(f"multi-seed monitor requirements missing: {missing}")

print("launcher v24 controls source check: ok")
