# v13 renderer implementation modules.
# Include this file from the project root CMakeLists.txt, then add
# ${ECO_RENDERER_SOURCES} to the eco_game_runtime target.
set(ECO_RENDERER_SOURCES
    src/gui/src/renderer.cpp
    src/gui/src/renderer_internal.cpp
    src/gui/src/renderer_core.cpp
    src/gui/src/renderer_environment.cpp
    src/gui/src/renderer_observation.cpp
    src/gui/src/renderer_groups.cpp
    src/gui/src/renderer_draw.cpp
)
