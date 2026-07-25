from pathlib import Path

root = Path(__file__).resolve().parents[1]
launcher = (root / "src/gui/src/launcher.cpp").read_text(encoding="utf-8")
prefs = (root / "src/gui/src/gui_preferences.cpp").read_text(encoding="utf-8")
monitor = (root / "src/gui/src/multi_seed_monitor.cpp").read_text(encoding="utf-8")
required = [
    "⚙ Settings [G]",
    "GUI Settings",
    "eco::preferences::settings_path(project_root)",
    "Sort: ",
    "ConfigSortMode::Latest",
    "★ Favorites",
    "Command preview",
    "Permanent config actions",
    "overwrite partial runs",
    "Temporary edits run directly",
]
missing = [token for token in required if token not in launcher + prefs]
if missing:
    raise SystemExit(f"launcher v22 controls missing: {missing}")
monitor_required = ["multi_seed_index.json", "evolution_progress.jsonl", "summary.json", "SeedStatus::Current"]
missing = [token for token in monitor_required if token not in monitor]
if missing:
    raise SystemExit(f"multi-seed monitor requirements missing: {missing}")
print("launcher v22 controls source check: ok")
