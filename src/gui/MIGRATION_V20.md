# Migration from v19 to v20

v20 changes `src/gui/src/main.cpp` and test support only. No new production
`.cpp` file is introduced, so the v19 CMake source list remains correct.

## Apply

```bash
bash apply_eco_render_v20.sh /path/to/project
```

or apply `patches/gui_v19_to_v20.diff` from the project root.

## Rebuild

A clean rebuild is recommended because `main.cpp` and launcher-facing raylib
calls changed.

```bash
rm -rf build
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build -j
ctest --test-dir build --output-on-failure
```

## Operational difference

The runtime title now includes the selected config filename. Terminal output
also records config, backend, run directory and stream path. Scripts that match
an exact window title of `Eco Game Runtime` should be updated to accept the
`Eco Game Runtime — <config>` suffix.
