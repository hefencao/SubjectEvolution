from pathlib import Path

root = Path(__file__).resolve().parents[1]
header = (root / "src/gui/src/render/renderer_internal.hpp").read_text(encoding="utf-8")
assert '#include "renderer_state.hpp"' in header
assert '#include "render/renderer_state.hpp"' not in header
print("renderer sibling include: ok")
