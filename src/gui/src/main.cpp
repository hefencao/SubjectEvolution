#include "eco/protocol.hpp"
#include "eco/renderer.hpp"
#include "eco/shared_reader.hpp"
#include "eco/social_loop.hpp"

#include <algorithm>
#include <array>
#include <atomic>
#include <chrono>
#include <cstdint>
#include <filesystem>
#include <optional>
#include <mutex>
#include <sstream>
#include <string>
#include <thread>
#include <vector>
#include <cmath>

#if defined(__unix__) || defined(__APPLE__)
#include <csignal>
#include <sys/types.h>
#include <sys/wait.h>
#include <unistd.h>
#endif

#include <raylib.h>

namespace {

class FrameExchange {
public:
    void publish(eco::Frame& working) {
        std::lock_guard lock(mutex_);
        std::swap(pending_, working);
        has_pending_ = true;
    }

    bool consume(eco::Frame& current) {
        std::lock_guard lock(mutex_);

        if (!has_pending_) {
            return false;
        }

        std::swap(current, pending_);
        has_pending_ = false;
        return true;
    }

private:
    std::mutex mutex_;
    eco::Frame pending_;
    bool has_pending_ = false;
};

struct LaunchRequest {
    std::filesystem::path project_root;
    std::filesystem::path config_path;
    std::filesystem::path output_path;
    std::filesystem::path stream_path;
    std::string python = "python3";
    std::string backend = "cpu";
};

std::filesystem::path find_project_root(
    std::filesystem::path start
) {
    start = std::filesystem::absolute(std::move(start));
    while (!start.empty()) {
        if (std::filesystem::is_directory(start / "configs") &&
            std::filesystem::is_directory(start / "src")) {
            return start;
        }
        const std::filesystem::path parent = start.parent_path();
        if (parent == start) {
            break;
        }
        start = parent;
    }
    return std::filesystem::current_path();
}

std::vector<std::filesystem::path> find_configs(
    const std::filesystem::path& config_dir
) {
    std::vector<std::filesystem::path> configs;
    std::error_code error;
    for (const auto& entry : std::filesystem::directory_iterator(
             config_dir,
             std::filesystem::directory_options::skip_permission_denied,
             error
         )) {
        if (entry.is_regular_file() && entry.path().extension() == ".json") {
            configs.push_back(entry.path());
        }
    }
    std::sort(configs.begin(), configs.end());
    return configs;
}

std::string timestamp_suffix() {
    const auto now = std::chrono::system_clock::now();
    const auto milliseconds = std::chrono::duration_cast<
        std::chrono::milliseconds
    >(now.time_since_epoch()).count();
    return std::to_string(milliseconds);
}

#if defined(__unix__) || defined(__APPLE__)
pid_t launch_simulation(const LaunchRequest& request, std::string& error) {
    const pid_t child = fork();
    if (child < 0) {
        error = "could not create the simulation process";
        return -1;
    }
    if (child != 0) {
        return child;
    }

    const std::string python_path = request.project_root.string() + "/src";
    setenv("PYTHONPATH", python_path.c_str(), 1);
    if (chdir(request.project_root.c_str()) != 0) {
        _exit(127);
    }

    const std::string config = request.config_path.string();
    const std::string output = request.output_path.string();
    const std::string stream = request.stream_path.string();
    std::vector<char*> arguments{
        const_cast<char*>(request.python.c_str()),
        const_cast<char*>("-m"),
        const_cast<char*>("subject_evolution.gui_interface.run_simulation"),
        const_cast<char*>("--config"), const_cast<char*>(config.c_str()),
        const_cast<char*>("--output"), const_cast<char*>(output.c_str()),
        const_cast<char*>("--stream"), const_cast<char*>(stream.c_str()),
        const_cast<char*>("--backend"), const_cast<char*>(request.backend.c_str()),
        nullptr,
    };
    execvp(arguments.front(), arguments.data());
    _exit(127);
}

void stop_simulation(pid_t child) {
    if (child <= 0) {
        return;
    }
    if (waitpid(child, nullptr, WNOHANG) == 0) {
        kill(child, SIGTERM);
        waitpid(child, nullptr, 0);
    }
}
#endif

std::optional<LaunchRequest> show_launcher(
    const std::filesystem::path& project_root,
    const std::filesystem::path& config_dir,
    const std::string& python
) {
    const std::vector<std::filesystem::path> configs = find_configs(config_dir);
    const std::array<std::string, 3> backends{"cpu", "gpu", "auto"};
    std::size_t selected = 0;
    std::size_t backend = 0;
    std::string message = configs.empty()
        ? "No JSON configurations found in " + config_dir.string()
        : "Choose a configuration, then start the simulation.";

    while (!WindowShouldClose()) {
        if (!configs.empty()) {
            if (IsKeyPressed(KEY_DOWN)) {
                selected = std::min(selected + 1, configs.size() - 1);
            }
            if (IsKeyPressed(KEY_UP) && selected > 0) {
                --selected;
            }
            if (IsKeyPressed(KEY_LEFT) && backend > 0) {
                --backend;
            }
            if (IsKeyPressed(KEY_RIGHT) && backend + 1 < backends.size()) {
                ++backend;
            }
        }

        const Rectangle start_button{48.0F, 500.0F, 240.0F, 48.0F};
        const bool start = IsKeyPressed(KEY_ENTER) ||
            (IsMouseButtonPressed(MOUSE_BUTTON_LEFT) &&
             CheckCollisionPointRec(GetMousePosition(), start_button));
        if (start && !configs.empty()) {
            const std::string stem = configs[selected].stem().string();
            const std::filesystem::path output = project_root / "runs" /
                ("gui_" + stem + "_" + timestamp_suffix());
            return LaunchRequest{
                project_root,
                configs[selected],
                output,
                output / "eco_live.bin",
                python,
                backends[backend],
            };
        }

        BeginDrawing();
        ClearBackground(Color{14, 17, 22, 255});
        DrawText("Subject Evolution", 48, 44, 34, RAYWHITE);
        DrawText("Simulation configuration", 48, 104, 21, LIGHTGRAY);
        DrawText(message.c_str(), 48, 136, 17, GRAY);

        int y = 180;
        for (std::size_t index = 0; index < configs.size(); ++index) {
            const bool active = index == selected;
            const Rectangle item{48.0F, static_cast<float>(y), 530.0F, 44.0F};
            if (active) {
                DrawRectangleRec(item, Color{42, 91, 117, 255});
            }
            DrawText(configs[index].filename().string().c_str(), 64, y + 11, 20,
                active ? RAYWHITE : LIGHTGRAY);
            if (IsMouseButtonPressed(MOUSE_BUTTON_LEFT) &&
                CheckCollisionPointRec(GetMousePosition(), item)) {
                selected = index;
            }
            y += 52;
        }

        DrawText("Backend", 48, 390, 20, LIGHTGRAY);
        for (std::size_t index = 0; index < backends.size(); ++index) {
            const int x = 148 + static_cast<int>(index) * 96;
            const bool active = index == backend;
            const Rectangle item{static_cast<float>(x), 382.0F, 82.0F, 34.0F};
            DrawRectangleRec(item, active ? Color{42, 91, 117, 255} : Color{43, 47, 54, 255});
            DrawText(backends[index].c_str(), x + 14, 391, 17, RAYWHITE);
            if (IsMouseButtonPressed(MOUSE_BUTTON_LEFT) &&
                CheckCollisionPointRec(GetMousePosition(), item)) {
                backend = index;
            }
        }

        DrawRectangleRec(start_button, Color{48, 130, 91, 255});
        DrawText("Start simulation", 69, 514, 20, RAYWHITE);
        DrawText("Up/Down: configuration   Left/Right: backend   Enter: start",
            48, 574, 16, GRAY);
        EndDrawing();
    }
    return std::nullopt;
}

void fit_camera(
    Camera2D& camera,
    const eco::Frame& frame
) {
    const float width =
        static_cast<float>(GetScreenWidth());
    const float height =
        static_cast<float>(GetScreenHeight());

    camera.offset = Vector2{
        width * 0.5F,
        height * 0.5F
    };

    camera.target = Vector2{
        frame.layout.world_width * 0.5F,
        frame.layout.world_height * 0.5F
    };

    camera.zoom = std::max(
        0.01F,
        std::min(
            width /
                std::max(
                    frame.layout.world_width,
                    1.0F
                ),
            height /
                std::max(
                    frame.layout.world_height,
                    1.0F
                )
        ) *
            0.92F
    );
}

const eco::EntitySample* find_entity(
    const eco::Frame& frame,
    std::uint64_t entity_id
) {
    const auto iterator = std::find_if(
        frame.entities.begin(),
        frame.entities.end(),
        [entity_id](const eco::EntitySample& entity) {
            return entity.entity_id == entity_id;
        }
    );

    return iterator == frame.entities.end()
        ? nullptr
        : &*iterator;
}

void draw_panel(
    const eco::Frame& frame,
    const eco::RenderOptions& options,
    const eco::SocialLoop& social,
    bool show_social,
    const std::string& reader_error
) {
    const int panel_width = show_social ? 480 : 400;
    const int panel_height = show_social ? 395 : 205;

    DrawRectangle(
        12,
        12,
        panel_width,
        panel_height,
        Fade(BLACK, 0.80F)
    );

    DrawText(
        TextFormat(
            "Tick: %llu",
            static_cast<unsigned long long>(frame.tick)
        ),
        25,
        22,
        22,
        RAYWHITE
    );

    DrawText(
        TextFormat(
            "Entities: %u  FPS: %d",
            static_cast<unsigned int>(frame.entities.size()),
            GetFPS()
        ),
        25,
        50,
        20,
        RAYWHITE
    );

    DrawText(
        TextFormat(
            "Resource: %d  Hazard: %s",
            options.resource_channel + 1,
            options.show_hazard ? "on" : "off"
        ),
        25,
        77,
        19,
        RAYWHITE
    );

    DrawText(
        "1-4 resource | H hazard | G grid | V velocity",
        25,
        106,
        16,
        LIGHTGRAY
    );

    DrawText(
        "S social | R fit | wheel zoom | middle pan",
        25,
        128,
        16,
        LIGHTGRAY
    );

    if (!reader_error.empty()) {
        DrawText(
            reader_error.c_str(),
            25,
            154,
            15,
            ORANGE
        );
    }

    if (options.selected_entity_id != 0) {
        const eco::EntitySample* entity =
            find_entity(
                frame,
                options.selected_entity_id
            );

        if (entity != nullptr) {
            DrawText(
                TextFormat(
                    "Selected: %llu  Group: %llu",
                    static_cast<unsigned long long>(
                        entity->entity_id
                    ),
                    static_cast<unsigned long long>(
                        entity->group_id
                    )
                ),
                25,
                178,
                16,
                YELLOW
            );
        }
    }

    if (!show_social) {
        return;
    }

    const eco::SocialStats& stats = social.stats();

    DrawText(
        TextFormat(
            "Social agents: %llu  groups: %llu  edges: %llu",
            static_cast<unsigned long long>(
                stats.active_agents
            ),
            static_cast<unsigned long long>(
                stats.active_groups
            ),
            static_cast<unsigned long long>(
                stats.relationship_edges
            )
        ),
        25,
        211,
        17,
        RAYWHITE
    );

    DrawText(
        TextFormat(
            "Trust: %.3f  reputation: %.3f  stress: %.3f",
            stats.mean_trust,
            stats.mean_reputation,
            stats.mean_stress
        ),
        25,
        236,
        17,
        RAYWHITE
    );

    DrawText(
        TextFormat(
            "Active rumors: %llu",
            static_cast<unsigned long long>(
                stats.active_rumors
            )
        ),
        25,
        261,
        17,
        RAYWHITE
    );

    int y = 290;
    int shown = 0;

    for (const eco::SocialEvent& event :
         social.recent_events()) {
        DrawText(
            TextFormat(
                "[%llu] %s",
                static_cast<unsigned long long>(
                    event.tick
                ),
                event.text.c_str()
            ),
            25,
            y,
            15,
            LIGHTGRAY
        );

        y += 20;
        ++shown;

        if (shown >= 5) {
            break;
        }
    }
}

}  // namespace

int main(int argc, char** argv) {
    bool viewer_only = false;
    std::filesystem::path shared_path;
    std::filesystem::path project_root = find_project_root(
        std::filesystem::current_path()
    );
    std::filesystem::path config_dir;
    std::string python = "python3";

    for (int index = 1; index < argc; ++index) {
        const std::string argument = argv[index];
        if (argument == "--stream" && index + 1 < argc) {
            shared_path = argv[++index];
            viewer_only = true;
        } else if (argument == "--project-root" && index + 1 < argc) {
            project_root = std::filesystem::absolute(argv[++index]);
        } else if (argument == "--config-dir" && index + 1 < argc) {
            config_dir = std::filesystem::absolute(argv[++index]);
        } else if (argument == "--python" && index + 1 < argc) {
            python = argv[++index];
        } else if (!argument.starts_with("--")) {
            // Keep the original positional stream-path invocation working.
            shared_path = argument;
            viewer_only = true;
        }
    }
    if (config_dir.empty()) {
        config_dir = project_root / "configs";
    }

    SetConfigFlags(
        FLAG_WINDOW_RESIZABLE |
        FLAG_MSAA_4X_HINT |
        FLAG_VSYNC_HINT
    );

    InitWindow(
        1440,
        900,
        "Eco Game Runtime"
    );
    SetTargetFPS(144);

    #if defined(__unix__) || defined(__APPLE__)
    pid_t simulation_process = -1;
    #endif

    if (!viewer_only) {
        const auto request = show_launcher(project_root, config_dir, python);
        if (!request.has_value()) {
            CloseWindow();
            return 0;
        }
        shared_path = request->stream_path;
        #if defined(__unix__) || defined(__APPLE__)
        std::string launch_error;
        simulation_process = launch_simulation(*request, launch_error);
        if (simulation_process < 0) {
            CloseWindow();
            return 1;
        }
        #else
        CloseWindow();
        return 1;
        #endif
    }

    FrameExchange exchange;
    std::atomic_bool running{true};
    std::mutex error_mutex;
    std::string reader_error;

    std::thread ingest_thread(
        [&]() {
            eco::SharedFrameReader reader(shared_path);
            eco::Frame working;

            while (running.load(
                std::memory_order_relaxed
            )) {
                if (reader.read_latest(working)) {
                    exchange.publish(working);
                } else {
                    {
                        std::lock_guard lock(error_mutex);
                        reader_error = reader.last_error();
                    }

                    std::this_thread::sleep_for(
                        std::chrono::milliseconds(2)
                    );
                }
            }
        }
    );

    eco::Frame current;
    eco::WorldRenderer renderer;
    eco::SocialLoop social;

    eco::RenderOptions options{};
    bool show_social = true;
    bool camera_initialized = false;
    bool heatmap_dirty = false;

    Camera2D camera{};
    camera.zoom = 1.0F;

    while (!WindowShouldClose()) {
        const bool received =
            exchange.consume(current);

        if (received) {
            social.update(current);
            heatmap_dirty = true;

            if (!camera_initialized) {
                fit_camera(camera, current);
                camera_initialized = true;
            }
        }

        if (current.entities.empty() &&
            current.tick == 0) {
            BeginDrawing();
            ClearBackground(Color{14, 17, 22, 255});
            DrawText(
                "Waiting for eco_live.bin ...",
                40,
                40,
                30,
                RAYWHITE
            );
            DrawText(
                shared_path.string().c_str(),
                40,
                82,
                18,
                GRAY
            );
            EndDrawing();
            continue;
        }

        const float wheel = GetMouseWheelMove();
        if (wheel != 0.0F) {
            const Vector2 mouse = GetMousePosition();
            const Vector2 before =
                GetScreenToWorld2D(mouse, camera);

            camera.zoom = std::clamp(
                camera.zoom *
                    std::pow(1.15F, wheel),
                0.01F,
                300.0F
            );

            const Vector2 after =
                GetScreenToWorld2D(mouse, camera);

            camera.target.x += before.x - after.x;
            camera.target.y += before.y - after.y;
        }

        if (IsMouseButtonDown(MOUSE_BUTTON_MIDDLE)) {
            const Vector2 delta = GetMouseDelta();
            camera.target.x -=
                delta.x / camera.zoom;
            camera.target.y -=
                delta.y / camera.zoom;
        }

        if (IsMouseButtonPressed(MOUSE_BUTTON_LEFT)) {
            options.selected_entity_id =
                renderer.pick_entity(
                    current,
                    camera,
                    GetMousePosition()
                );
        }

        if (IsKeyPressed(KEY_ONE)) {
            options.resource_channel = 0;
            heatmap_dirty = true;
        }
        if (IsKeyPressed(KEY_TWO)) {
            options.resource_channel = 1;
            heatmap_dirty = true;
        }
        if (IsKeyPressed(KEY_THREE)) {
            options.resource_channel = 2;
            heatmap_dirty = true;
        }
        if (IsKeyPressed(KEY_FOUR)) {
            options.resource_channel = 3;
            heatmap_dirty = true;
        }

        if (IsKeyPressed(KEY_H)) {
            options.show_hazard =
                !options.show_hazard;
            heatmap_dirty = true;
        }
        if (IsKeyPressed(KEY_G)) {
            options.show_grid =
                !options.show_grid;
        }
        if (IsKeyPressed(KEY_V)) {
            options.show_velocity =
                !options.show_velocity;
        }
        if (IsKeyPressed(KEY_S)) {
            show_social = !show_social;
        }
        if (IsKeyPressed(KEY_R)) {
            fit_camera(camera, current);
        }

        if (heatmap_dirty) {
            renderer.update_heatmap(
                current,
                options.resource_channel,
                options.show_hazard
            );
            heatmap_dirty = false;
        }

        std::string error_copy;
        {
            std::lock_guard lock(error_mutex);
            error_copy = reader_error;
        }

        BeginDrawing();
        ClearBackground(Color{14, 17, 22, 255});

        BeginMode2D(camera);
        renderer.draw(current, camera, options);
        EndMode2D();

        draw_panel(
            current,
            options,
            social,
            show_social,
            error_copy
        );

        EndDrawing();
    }

    running.store(false, std::memory_order_relaxed);

    if (ingest_thread.joinable()) {
        ingest_thread.join();
    }

    #if defined(__unix__) || defined(__APPLE__)
    stop_simulation(simulation_process);
    #endif

    CloseWindow();
    return 0;
}
