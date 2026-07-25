# Current GUI implementation modules (v22).
# Include this file after the eco_game_runtime target is created:
#   include("${CMAKE_CURRENT_LIST_DIR}/renderer_sources.cmake")
#   target_sources(eco_game_runtime PRIVATE ${ECO_RENDERER_MODULE_SOURCES})
set(ECO_RENDERER_MODULE_SOURCES
    "${CMAKE_CURRENT_LIST_DIR}/src/launcher.cpp"
    "${CMAKE_CURRENT_LIST_DIR}/src/gui_preferences.cpp"
    "${CMAKE_CURRENT_LIST_DIR}/src/multi_seed_monitor.cpp"
    "${CMAKE_CURRENT_LIST_DIR}/src/ui_font.cpp"
    "${CMAKE_CURRENT_LIST_DIR}/src/renderer_internal.cpp"
    "${CMAKE_CURRENT_LIST_DIR}/src/renderer_context.cpp"
    "${CMAKE_CURRENT_LIST_DIR}/src/renderer_core.cpp"
    "${CMAKE_CURRENT_LIST_DIR}/src/renderer_environment.cpp"
    "${CMAKE_CURRENT_LIST_DIR}/src/renderer_observation.cpp"
    "${CMAKE_CURRENT_LIST_DIR}/src/renderer_groups.cpp"
    "${CMAKE_CURRENT_LIST_DIR}/src/renderer_draw.cpp"
    "${CMAKE_CURRENT_LIST_DIR}/src/renderer_gpu.cpp"
)
