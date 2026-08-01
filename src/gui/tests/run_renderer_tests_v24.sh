#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CXX="${CXX:-c++}"
SUPPORT="$ROOT/tests/support"
BUILD="${TMPDIR:-/tmp}/eco_renderer_v24_tests"
rm -rf "$BUILD"
mkdir -p "$BUILD"

COMMON=(
  -std=c++20 -O1 -Wall -Wextra -Wpedantic -pthread
  -I"$SUPPORT" -I"$ROOT/src/gui/include" -I"$ROOT/src/gui/src"
)

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
  "$CXX" "${COMMON[@]}" -c "$ROOT/src/gui/src/$source" -o "$object"
  RENDERER_OBJECTS+=("$object")
done

"$CXX" "${COMMON[@]}" -c "$ROOT/src/gui/src/ui_font.cpp" -o "$BUILD/ui_font.o"
"$CXX" "${COMMON[@]}" -c "$ROOT/src/gui/src/launcher.cpp" -o "$BUILD/launcher.o"
"$CXX" "${COMMON[@]}" -c "$ROOT/src/gui/src/gui_preferences.cpp" -o "$BUILD/gui_preferences.o"
"$CXX" "${COMMON[@]}" -c "$ROOT/src/gui/src/multi_seed_monitor.cpp" -o "$BUILD/multi_seed_monitor.o"
"$CXX" -std=c++20 -O1 -I"$SUPPORT" \
  -c "$ROOT/tests/support/raylib_weak_stubs.cpp" \
  -o "$BUILD/raylib_weak_stubs.o"

for test in "$ROOT"/tests/renderer_*_test.cpp; do
  name="$(basename "$test" .cpp)"
  "$CXX" "${COMMON[@]}" \
    "$test" "${RENDERER_OBJECTS[@]}" "$BUILD/raylib_weak_stubs.o" \
    -o "$BUILD/$name"
  "$BUILD/$name"
done

"$CXX" "${COMMON[@]}" \
  "$ROOT/tests/main_launcher_test.cpp" \
  "$BUILD/launcher.o" "$BUILD/gui_preferences.o" "$BUILD/ui_font.o" "$BUILD/raylib_weak_stubs.o" \
  -o "$BUILD/main_launcher_test"
"$BUILD/main_launcher_test"

"$CXX" "${COMMON[@]}" \
  "$ROOT/tests/ui_font_test.cpp" \
  "$BUILD/ui_font.o" "$BUILD/raylib_weak_stubs.o" \
  -o "$BUILD/ui_font_test"
"$BUILD/ui_font_test"


"$CXX" "${COMMON[@]}" \
  "$ROOT/tests/gui_preferences_test.cpp" \
  "$BUILD/gui_preferences.o" \
  -o "$BUILD/gui_preferences_test"
"$BUILD/gui_preferences_test"

"$CXX" "${COMMON[@]}" \
  "$ROOT/tests/multi_seed_monitor_test.cpp" \
  "$BUILD/multi_seed_monitor.o" \
  -o "$BUILD/multi_seed_monitor_test"
"$BUILD/multi_seed_monitor_test"

"$CXX" "${COMMON[@]}" \
  "$ROOT/tests/runtime_pacing_test.cpp" \
  -o "$BUILD/runtime_pacing_test"
"$BUILD/runtime_pacing_test"

python3 "$ROOT/tests/renderer_module_layout_test.py"
python3 "$ROOT/tests/main_selection_fallback_test.py"
python3 "$ROOT/tests/main_observation_presets_test.py"
python3 "$ROOT/tests/main_overview_preset_test.py"
python3 "$ROOT/tests/main_temporal_presets_test.py"
python3 "$ROOT/tests/main_visual_hold_test.py"
python3 "$ROOT/tests/renderer_include_path_test.py"
python3 "$ROOT/tests/renderer_observation_pipeline_test.py"
python3 "$ROOT/tests/main_launcher_identity_test.py"
python3 "$ROOT/tests/launcher_controls_test.py"
python3 "$ROOT/tests/launcher_information_architecture_test.py"
python3 "$ROOT/tests/runtime_pacing_source_test.py"
python3 "$ROOT/tests/python_source_syntax_test.py"
python3 "$ROOT/tests/python_gui_compat_test.py"

# Full GUI compile and synthetic link, reusing previously built renderer/launcher objects.
FULL_OBJECTS=("${RENDERER_OBJECTS[@]}" "$BUILD/launcher.o" "$BUILD/gui_preferences.o" "$BUILD/multi_seed_monitor.o" "$BUILD/ui_font.o")
for source in mapped_file.cpp shared_reader.cpp social_loop.cpp main.cpp; do
  object="$BUILD/full_${source%.cpp}.o"
  "$CXX" "${COMMON[@]}" -c "$ROOT/src/gui/src/$source" -o "$object"
  FULL_OBJECTS+=("$object")
done
"$CXX" -pthread "${FULL_OBJECTS[@]}" "$BUILD/raylib_weak_stubs.o" \
  -o "$BUILD/eco_game_runtime_link_test"

"$CXX" "${COMMON[@]}" \
  "$ROOT/tests/social_capacity_test.cpp" \
  "$ROOT/src/gui/src/social_loop.cpp" "$BUILD/raylib_weak_stubs.o" \
  -o "$BUILD/social_capacity_test"
"$BUILD/social_capacity_test"

echo "renderer, launcher and Python integration v24 tests: ok"
