from pathlib import Path

source = (Path(__file__).resolve().parents[1] / "src/gui/src/main.cpp").read_text(encoding="utf-8")

required = [
    "Subject Evolution Launcher — ",
    "Eco Game Runtime — ",
    "[eco-gui] selected config:",
    "[eco-gui] backend:",
    "[eco-gui] output:",
    "[eco-gui] stream:",
    "BeginScissorMode(",
    "clamp_launcher_scroll(",
    "KEY_PAGE_DOWN",
    "KEY_HOME",
    "Refresh [R]",
    "Command preview",
]

missing = [token for token in required if token not in source]
if missing:
    raise SystemExit(f"launcher identity/source requirements missing: {missing}")

print("launcher identity source check: ok")
