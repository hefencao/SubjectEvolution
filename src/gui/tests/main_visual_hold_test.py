from pathlib import Path

root = Path(__file__).resolve().parents[1]
source = (root / "src/gui/src/main.cpp").read_text(encoding="utf-8")

required = [
    "KEY_SPACE",
    "KEY_N",
    "view_paused",
    "sample_latest",
    "exchange.latest_tick()",
    "HOLD +%llu",
]
for token in required:
    assert token in source, token

assert "(!view_paused || sample_latest)" in source
print("visual hold source check: ok")
