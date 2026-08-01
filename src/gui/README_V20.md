# Eco Game Runtime GUI v20

v20 is a launcher-focused update built directly from the v19 GPU-rendering
baseline. The simulation, shared-memory protocol, renderer architecture,
observation presets and GPU agent instancing are unchanged.

## Launcher changes

The initial page is now a bounded two-panel launcher instead of an unbounded
vertical list.

- The configuration list is clipped to its panel and never overlaps backend or
  launch controls.
- Selection automatically scrolls into view.
- Keyboard navigation supports Up/Down, Page Up/Page Down, Home and End.
- The mouse wheel changes the selected item while preserving visibility.
- `R` rescans the configuration directory while preserving the selected path
  when it still exists.
- Empty, unreadable and obviously non-JSON files cannot be launched.
- The selected file, absolute path, size, backend, project root, config
  directory, output template and exact command preview are visible before
  launch.
- The launcher window title contains the selected configuration and backend.
- The runtime window title contains the launched configuration name.
- The terminal receives the selected config, backend, output directory and
  stream path.

The minimum window size is 1024 x 700 so the two-panel layout remains usable
when the resizable window is reduced.

## Launcher controls

- `Up` / `Down` or mouse wheel: move selection.
- `Page Up` / `Page Down`: move by one visible page.
- `Home` / `End`: first or last configuration.
- `Left` / `Right`: choose CPU, GPU or auto backend.
- `R`: rescan `configs/`.
- `Enter`: launch the selected valid configuration.
- `Esc`: close the launcher.

## Runtime controls

All v19 controls remain unchanged, including `U` for GPU/CPU agent rendering,
`Space`/`N` for visual hold, and F1-F6 observation presets.

## Build

v20 adds no production translation unit. The v19 `target_sources()` list,
including `renderer_gpu.cpp`, remains valid.

```bash
rm -rf build
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build -j
ctest --test-dir build --output-on-failure
```

## Tests

```bash
tests/run_renderer_tests_v20.sh
```
