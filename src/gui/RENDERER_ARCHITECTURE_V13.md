# Renderer architecture v13

v13 is based exclusively on v12. The former 3,125-line implementation is now
split into separately compiled translation units while preserving the public
`eco/renderer.hpp` API and the shared-memory protocol.

## Modules

| Module | Responsibility |
|---|---|
| `renderer.cpp` | Compatibility facade; no implementation logic. |
| `renderer_internal.cpp` | Private math, color, filtering, rlgl batching, flow and behavior glyph helpers. |
| `renderer_core.cpp` | Continuous LOD/detail resolution, names, entity colors and renderer lifetime. |
| `renderer_environment.cpp` | Environment probe, texture lifecycle, temporal/spatial filtering and heat-map composition. |
| `renderer_observation.cpp` | Frame diagnostics, birth/death/action extraction, group statistics and trail history capture. |
| `renderer_groups.cpp` | Group history, covariance ellipses, group marker picking and periodic-world display copies. |
| `renderer_draw.cpp` | High-level layer composition, sampled agents, events, relationships and selected-agent rendering. |
| `render/renderer_internal.hpp` | Private declarations shared by renderer implementation modules. |

## Dependency direction

```text
renderer.hpp / protocol.hpp / social_loop.hpp
                    │
                    ▼
        render/renderer_internal.hpp
                    │
     ┌──────────────┼──────────────┐
     ▼              ▼              ▼
 environment    observation      groups
     └──────────────┼──────────────┘
                    ▼
                  draw
```

The internal header is not part of the public API. Game/UI code should include
only `eco/renderer.hpp`.

## v13 behavior fixes

- A selected entity that dies automatically falls back to its still-live group.
  If the group also disappears, the complete selection and follow state clear.
- Group trails use the periodic image nearest the camera and reject implausibly
  large screen-space segments, preventing cross-screen arcs at high zoom.
- Statistical group ellipses use the nearest periodic display copy and are
  clipped by screen-space segment limits.
- Group focus reduces non-target entity opacity more strongly while leaving the
  environment texture unchanged and readable.
- Ordinary group behavior overlays have a smaller budget and stricter badge
  threshold, reducing duplicate Macro arrows and action symbols.

## CMake

The new translation units must be compiled. `src/gui/renderer_sources.cmake`
contains the complete source list. The apply script automatically patches the
usual explicit `renderer.cpp` source list. Projects using `file(GLOB
src/gui/src/*.cpp)` pick up the new root-level `.cpp` modules automatically.
