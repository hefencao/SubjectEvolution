from pathlib import Path

root = Path(__file__).resolve().parents[1]
main = (root / "src/gui/src/main.cpp").read_text(encoding="utf-8")
launcher = (root / "src/gui/src/launcher.cpp").read_text(encoding="utf-8")
pacing = (root / "src/gui/include/eco/runtime_pacing.hpp").read_text(encoding="utf-8")

required = [
    "SetTargetFPS(eco::runtime::kLauncherTargetFps)",
    "SetTargetFPS(eco::runtime::kRuntimeTargetFps)",
    "eco::runtime::PollBackoff polling_backoff",
    "polling_backoff.after_activity()",
    "polling_backoff.after_idle()",
    "kMonitorPollInterval",
    "kFinishedMonitorPollInterval",
]
missing = [token for token in required if token not in main + pacing]
if missing:
    raise SystemExit(f"runtime pacing requirements missing: {missing}")
if "SetTargetFPS(144)" in main or "std::chrono::milliseconds(2)" in main:
    raise SystemExit("legacy busy-poll pacing is still present")
for token in ["layout.search_field", "layout.sort_button", "layout.tag_button", "layout.favorite_button"]:
    if token not in launcher:
        raise SystemExit(f"responsive launcher control missing: {token}")
print("runtime pacing and responsive layout source check: ok")
