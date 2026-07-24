cmake_minimum_required(VERSION 3.20)

project(eco_game_runtime VERSION 0.1.0 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

option(ECO_FETCH_RAYLIB "Fetch pinned raylib when no package is installed" ON)
option(ECO_BUILD_TESTS "Build protocol layout tests" ON)

find_package(raylib 5.0 QUIET)

if(NOT raylib_FOUND)
    if(NOT ECO_FETCH_RAYLIB)
        message(FATAL_ERROR "raylib was not found and ECO_FETCH_RAYLIB is OFF")
    endif()

    include(FetchContent)
    set(BUILD_EXAMPLES OFF CACHE BOOL "" FORCE)
    set(BUILD_GAMES OFF CACHE BOOL "" FORCE)

    FetchContent_Declare(
        raylib
        URL https://github.com/raysan5/raylib/archive/refs/tags/5.5.tar.gz
        DOWNLOAD_EXTRACT_TIMESTAMP TRUE
    )
    FetchContent_MakeAvailable(raylib)
endif()

find_package(Threads REQUIRED)

add_library(eco_runtime_core
    src/mapped_file.cpp
    src/shared_reader.cpp
    src/social_loop.cpp
)

target_include_directories(eco_runtime_core PUBLIC include)
target_link_libraries(eco_runtime_core PUBLIC Threads::Threads)

add_executable(eco_game_runtime
    src/main.cpp
    src/renderer.cpp
)

target_sources(eco_game_runtime PRIVATE
    src/renderer_internal.cpp
    src/renderer_core.cpp
    src/renderer_environment.cpp
    src/renderer_observation.cpp
    src/renderer_groups.cpp
    src/renderer_draw.cpp
)

target_include_directories(eco_game_runtime PRIVATE include)
target_link_libraries(
    eco_game_runtime
    PRIVATE
        eco_runtime_core
        raylib
        Threads::Threads
)

if(MSVC)
    target_compile_options(eco_runtime_core PRIVATE /W4 /permissive-)
    target_compile_options(eco_game_runtime PRIVATE /W4 /permissive-)
    target_compile_definitions(eco_runtime_core PRIVATE _CRT_SECURE_NO_WARNINGS)
    target_compile_definitions(eco_game_runtime PRIVATE _CRT_SECURE_NO_WARNINGS)
else()
    target_compile_options(eco_runtime_core PRIVATE -Wall -Wextra -Wpedantic)
    target_compile_options(eco_game_runtime PRIVATE -Wall -Wextra -Wpedantic)
endif()

if(ECO_BUILD_TESTS)
    enable_testing()

    add_executable(protocol_layout_test tests/protocol_layout_test.cpp)
    target_include_directories(protocol_layout_test PRIVATE include)

    add_test(NAME protocol_layout_test COMMAND protocol_layout_test)
endif()
