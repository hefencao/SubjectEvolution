from pathlib import Path

root = Path(__file__).resolve().parents[1]
source = (root / "src/gui/src/renderer_observation.cpp").read_text(encoding="utf-8")
assert "sum_cos_x" not in source
assert "sum_sin_x" not in source
assert "group_indices" not in source
assert "sum_dx2" in source and "sum_dxdy" in source
assert "std::move(state_->groups.previous_visuals)" in source
assert "visual_grid_columns" in source
assert "observe_scan_ms" in source
assert "observe_groups_ms" in source
print("observation pipeline source check: ok")
