#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CXX="${CXX:-c++}"
SUPPORT="$ROOT/tests/support"
BUILD="${TMPDIR:-/tmp}/eco_renderer_v20_tests"
rm -rf "$BUILD"
mkdir -p "$BUILD"

RENDERER_SOURCES=(
  renderer.cpp
  renderer_internal.cpp
  renderer_context.cpp
  renderer_core.cpp
  renderer_environment.cpp
  renderer_observation.cpp
  renderer_groups.cpp
  renderer_draw.cpp
  renderer_gpu.cpp
)
RENDERER_OBJECTS=()
for source in "${RENDERER_SOURCES[@]}"; do
  object="$BUILD/${source%.cpp}.o"
  "$CXX" -std=c++20 -O1 -Wall -Wextra -Wpedantic \
    -I"$SUPPORT" -I"$ROOT/src/gui/include" -I"$ROOT/src/gui/src" \
    -c "$ROOT/src/gui/src/$source" -o "$object"
  RENDERER_OBJECTS+=("$object")
done

"$CXX" -std=c++20 -O1 -I"$SUPPORT" \
  -c "$ROOT/tests/support/raylib_weak_stubs.cpp" \
  -o "$BUILD/raylib_weak_stubs.o"

for test in "$ROOT"/tests/renderer_*_test.cpp; do
  name="$(basename "$test" .cpp)"
  "$CXX" -std=c++20 -O1 \
    -I"$SUPPORT" -I"$ROOT/src/gui/include" -I"$ROOT/src/gui/src" \
    "$test" "${RENDERER_OBJECTS[@]}" "$BUILD/raylib_weak_stubs.o" \
    -o "$BUILD/$name"
  "$BUILD/$name"
done

python3 "$ROOT/tests/renderer_module_layout_test.py"
python3 "$ROOT/tests/main_selection_fallback_test.py"
python3 "$ROOT/tests/main_observation_presets_test.py"
python3 "$ROOT/tests/main_overview_preset_test.py"
python3 "$ROOT/tests/main_temporal_presets_test.py"
python3 "$ROOT/tests/main_visual_hold_test.py"
python3 "$ROOT/tests/renderer_include_path_test.py"
python3 "$ROOT/tests/renderer_observation_pipeline_test.py"
python3 "$ROOT/tests/main_launcher_identity_test.py"

"$CXX" -std=c++20 -O1 -Wall -Wextra -Wpedantic -pthread \
  -I"$SUPPORT" -I"$ROOT/src/gui/include" -I"$ROOT/src/gui/src" \
  "$ROOT/tests/main_launcher_test.cpp" \
  "$ROOT/src/gui/src/mapped_file.cpp" \
  "$ROOT/src/gui/src/shared_reader.cpp" \
  "$ROOT/src/gui/src/social_loop.cpp" \
  "${RENDERER_OBJECTS[@]}" "$BUILD/raylib_weak_stubs.o" \
  -o "$BUILD/main_launcher_test"
"$BUILD/main_launcher_test"

echo "renderer and launcher v20 tests: ok"
