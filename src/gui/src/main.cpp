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

enum class ObservationPreset : std::uint8_t {
    Custom,
    Overview,
    Ecology,
    Migration,
    Social,
    Survival,
    Reproduction,
};

const char* observation_preset_name(ObservationPreset preset) {
    switch (preset) {
    case ObservationPreset::Custom:
        return "custom";
    case ObservationPreset::Overview:
        return "overview";
    case ObservationPreset::Ecology:
        return "ecology";
    case ObservationPreset::Migration:
        return "migration";
    case ObservationPreset::Social:
        return "social";
    case ObservationPreset::Survival:
        return "survival";
    case ObservationPreset::Reproduction:
        return "reproduction";
    }
    return "custom";
}

void apply_observation_preset(
    ObservationPreset preset,
    eco::RenderOptions& options
) {
    options.lod_mode = eco::LodMode::Auto;
    options.environment_filter = eco::EnvironmentFilterMode::Stable;
    options.show_environment_change = false;
    options.show_grid = false;
    options.focus_selected_group = false;
    options.show_group_landmarks = false;
    options.overlay_temporal = eco::OverlayTemporalMode::Stable;

    switch (preset) {
    case ObservationPreset::Overview:
        options.environment_view = eco::EnvironmentViewMode::Composite;
        options.show_hazard = true;
        options.show_population_density = true;
        options.show_event_markers = true;
        options.show_group_trails = true;
        options.show_velocity = false;
        options.show_group_landmarks = true;
        options.behavior_overlay = eco::BehaviorOverlayMode::Combined;
        options.action_filter = eco::ActionFilterMode::All;
        break;
    case ObservationPreset::Ecology:
        options.environment_view = eco::EnvironmentViewMode::ResourceAbsolute;
        options.show_hazard = false;
        options.show_population_density = false;
        options.show_event_markers = false;
        options.show_group_trails = false;
        options.show_velocity = false;
        options.behavior_overlay = eco::BehaviorOverlayMode::Off;
        options.action_filter = eco::ActionFilterMode::All;
        break;
    case ObservationPreset::Migration:
        options.environment_view = eco::EnvironmentViewMode::Composite;
        options.show_hazard = false;
        options.show_population_density = true;
        options.show_event_markers = false;
        options.show_group_trails = true;
        options.show_velocity = false;
        options.show_group_landmarks = true;
        options.behavior_overlay = eco::BehaviorOverlayMode::Groups;
        options.action_filter = eco::ActionFilterMode::Movement;
        break;
    case ObservationPreset::Social:
        options.environment_view = eco::EnvironmentViewMode::PopulationDensity;
        options.show_hazard = false;
        options.show_population_density = true;
        options.show_event_markers = false;
        options.show_group_trails = true;
        options.show_velocity = false;
        options.show_group_landmarks = true;
        options.behavior_overlay = eco::BehaviorOverlayMode::Combined;
        options.action_filter = eco::ActionFilterMode::Social;
        break;
    case ObservationPreset::Survival:
        options.environment_view = eco::EnvironmentViewMode::Hazard;
        options.show_hazard = true;
        options.show_population_density = true;
        options.show_event_markers = true;
        options.show_group_trails = true;
        options.show_velocity = false;
        options.show_group_landmarks = true;
        options.behavior_overlay = eco::BehaviorOverlayMode::Combined;
        options.action_filter = eco::ActionFilterMode::Survival;
        break;
    case ObservationPreset::Reproduction:
        options.environment_view = eco::EnvironmentViewMode::PopulationDensity;
        options.show_hazard = false;
        options.show_population_density = true;
        options.show_event_markers = true;
        options.show_group_trails = false;
        options.show_velocity = false;
        options.behavior_overlay = eco::BehaviorOverlayMode::Actions;
        options.action_filter = eco::ActionFilterMode::Reproduction;
        options.overlay_temporal = eco::OverlayTemporalMode::Responsive;
        break;
    case ObservationPreset::Custom:
        break;
    }
}

constexpr float kSidebarWidth = 510.0F;
constexpr float kPanelMargin = 12.0F;

Rectangle world_viewport() {
    const float width = std::max(
        1.0F,
        static_cast<float>(GetScreenWidth()) - kSidebarWidth
    );
    return Rectangle{
        kSidebarWidth,
        0.0F,
        width,
        static_cast<float>(GetScreenHeight())
    };
}

void update_camera_offset(
    Camera2D& camera,
    Rectangle viewport
) {
    camera.offset = Vector2{
        viewport.x + viewport.width * 0.5F,
        viewport.y + viewport.height * 0.5F
    };
}

void fit_camera(
    Camera2D& camera,
    const eco::Frame& frame,
    Rectangle viewport
) {
    update_camera_offset(camera, viewport);

    camera.target = Vector2{
        frame.layout.world_width * 0.5F,
        frame.layout.world_height * 0.5F
    };

    camera.zoom = std::max(
        0.01F,
        std::min(
            viewport.width /
                std::max(frame.layout.world_width, 1.0F),
            viewport.height /
                std::max(frame.layout.world_height, 1.0F)
        ) * 0.94F
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

struct MetricHistory {
    static constexpr std::size_t capacity = 240;

    std::array<float, capacity> population{};
    std::array<float, capacity> groups{};
    std::array<float, capacity> trust{};
    std::array<float, capacity> stress{};
    std::array<float, capacity> rumors{};
    std::array<float, capacity> births{};
    std::array<float, capacity> deaths{};
    std::array<float, capacity> harvests{};
    std::array<float, capacity> resource{};
    std::array<float, capacity> speed{};

    std::size_t count = 0;
    std::size_t cursor = 0;

    void push(
        const eco::Frame& frame,
        const eco::SocialLoop& social,
        const eco::FrameDiagnostics& diagnostics
    ) {
        const eco::SocialStats& stats = social.stats();

        population[cursor] =
            static_cast<float>(frame.entities.size());
        groups[cursor] =
            static_cast<float>(stats.active_groups);
        trust[cursor] = stats.mean_trust;
        stress[cursor] = stats.mean_stress;
        rumors[cursor] =
            static_cast<float>(stats.active_rumors);
        births[cursor] =
            static_cast<float>(diagnostics.births);
        deaths[cursor] =
            static_cast<float>(diagnostics.deaths);
        harvests[cursor] =
            static_cast<float>(diagnostics.harvests);
        resource[cursor] = diagnostics.mean_resource;
        speed[cursor] = diagnostics.mean_speed;

        cursor = (cursor + 1) % capacity;
        count = std::min(count + 1, capacity);
    }

    [[nodiscard]] float value(
        const std::array<float, capacity>& series,
        std::size_t logical_index
    ) const {
        const std::size_t first =
            count == capacity ? cursor : 0;
        return series[(first + logical_index) % capacity];
    }
};

const char* action_name(std::uint8_t action) {
    switch (static_cast<eco::Action>(action)) {
    case eco::Action::Rest:
        return "rest";
    case eco::Action::MoveResource:
        return "move-resource";
    case eco::Action::MoveSocial:
        return "move-social";
    case eco::Action::Harvest:
        return "harvest";
    case eco::Action::Share:
        return "share";
    case eco::Action::Signal:
        return "signal";
    case eco::Action::Reproduce:
        return "reproduce";
    case eco::Action::Flee:
        return "flee";
    default:
        return "none";
    }
}

Color action_color(eco::Action action) {
    switch (action) {
    case eco::Action::Rest:
        return Color{120, 132, 145, 255};
    case eco::Action::MoveResource:
        return Color{210, 226, 62, 255};
    case eco::Action::MoveSocial:
        return Color{93, 214, 255, 255};
    case eco::Action::Harvest:
        return Color{255, 184, 56, 255};
    case eco::Action::Share:
        return Color{70, 230, 197, 255};
    case eco::Action::Signal:
        return Color{139, 154, 255, 255};
    case eco::Action::Reproduce:
        return Color{232, 91, 244, 255};
    case eco::Action::Flee:
        return Color{255, 92, 78, 255};
    default:
        return GRAY;
    }
}

std::uint64_t cycle_group_selection(
    const std::vector<eco::GroupBehaviorSummary>& groups,
    std::uint64_t current,
    int direction
) {
    if (groups.empty()) {
        return 0;
    }
    const auto iterator = std::find_if(
        groups.begin(), groups.end(),
        [current](const eco::GroupBehaviorSummary& group) {
            return group.group_id == current;
        }
    );
    if (iterator == groups.end()) {
        return direction < 0
            ? groups.back().group_id
            : groups.front().group_id;
    }
    std::size_t index = static_cast<std::size_t>(iterator - groups.begin());
    if (direction > 0) {
        index = (index + 1U) % groups.size();
    } else if (direction < 0) {
        index = index == 0U ? groups.size() - 1U : index - 1U;
    }
    return groups[index].group_id;
}

void draw_group_action_mix(
    const eco::GroupBehaviorSummary& group,
    Rectangle bounds
) {
    DrawRectangleRec(bounds, Fade(BLACK, 0.42F));
    DrawRectangleLinesEx(bounds, 1.0F, Fade(GRAY, 0.34F));

    float x = bounds.x;
    for (std::size_t index = 0; index < group.action_fractions.size(); ++index) {
        const float fraction = std::clamp(group.action_fractions[index], 0.0F, 1.0F);
        if (fraction <= 0.002F) {
            continue;
        }
        const float width = bounds.width * fraction;
        DrawRectangleRec(
            Rectangle{x, bounds.y, width, bounds.height},
            action_color(static_cast<eco::Action>(index))
        );
        x += width;
    }

    std::array<std::pair<float, std::size_t>, 8> ranked{};
    for (std::size_t index = 0; index < ranked.size(); ++index) {
        ranked[index] = {group.action_fractions[index], index};
    }
    std::sort(ranked.begin(), ranked.end(),
        [](const auto& left, const auto& right) {
            return left.first > right.first;
        });

    int label_y = static_cast<int>(bounds.y + bounds.height + 4.0F);
    int label_x = static_cast<int>(bounds.x);
    for (std::size_t rank = 0; rank < 3U; ++rank) {
        const auto [fraction, index] = ranked[rank];
        if (fraction < 0.015F) {
            continue;
        }
        DrawText(
            TextFormat(
                "%s %.0f%%",
                action_name(static_cast<std::uint8_t>(index)),
                fraction * 100.0F
            ),
            label_x,
            label_y,
            12,
            action_color(static_cast<eco::Action>(index))
        );
        label_x += 142;
    }
}

eco::LodMode next_lod_mode(eco::LodMode mode) {
    switch (mode) {
    case eco::LodMode::Auto:
        return eco::LodMode::ForceMacro;
    case eco::LodMode::ForceMacro:
        return eco::LodMode::ForceMedium;
    case eco::LodMode::ForceMedium:
        return eco::LodMode::ForceMicro;
    case eco::LodMode::ForceMicro:
        return eco::LodMode::Auto;
    }
    return eco::LodMode::Auto;
}

eco::EnvironmentFilterMode next_environment_filter(
    eco::EnvironmentFilterMode mode
) {
    switch (mode) {
    case eco::EnvironmentFilterMode::Instant:
        return eco::EnvironmentFilterMode::Responsive;
    case eco::EnvironmentFilterMode::Responsive:
        return eco::EnvironmentFilterMode::Stable;
    case eco::EnvironmentFilterMode::Stable:
        return eco::EnvironmentFilterMode::Instant;
    }
    return eco::EnvironmentFilterMode::Stable;
}

eco::EnvironmentViewMode next_environment_view(
    eco::EnvironmentViewMode mode
) {
    switch (mode) {
    case eco::EnvironmentViewMode::Composite:
        return eco::EnvironmentViewMode::ResourceAbsolute;
    case eco::EnvironmentViewMode::ResourceAbsolute:
        return eco::EnvironmentViewMode::ResourceGradient;
    case eco::EnvironmentViewMode::ResourceGradient:
        return eco::EnvironmentViewMode::Hazard;
    case eco::EnvironmentViewMode::Hazard:
        return eco::EnvironmentViewMode::PopulationDensity;
    case eco::EnvironmentViewMode::PopulationDensity:
        return eco::EnvironmentViewMode::ResourceDelta;
    case eco::EnvironmentViewMode::ResourceDelta:
        return eco::EnvironmentViewMode::Composite;
    }
    return eco::EnvironmentViewMode::Composite;
}

eco::BehaviorOverlayMode next_behavior_overlay(
    eco::BehaviorOverlayMode mode
) {
    switch (mode) {
    case eco::BehaviorOverlayMode::Auto:
        return eco::BehaviorOverlayMode::Off;
    case eco::BehaviorOverlayMode::Off:
        return eco::BehaviorOverlayMode::Actions;
    case eco::BehaviorOverlayMode::Actions:
        return eco::BehaviorOverlayMode::Groups;
    case eco::BehaviorOverlayMode::Groups:
        return eco::BehaviorOverlayMode::Combined;
    case eco::BehaviorOverlayMode::Combined:
        return eco::BehaviorOverlayMode::Auto;
    }
    return eco::BehaviorOverlayMode::Auto;
}

eco::ActionFilterMode next_action_filter(eco::ActionFilterMode mode) {
    switch (mode) {
    case eco::ActionFilterMode::All:
        return eco::ActionFilterMode::Movement;
    case eco::ActionFilterMode::Movement:
        return eco::ActionFilterMode::Resource;
    case eco::ActionFilterMode::Resource:
        return eco::ActionFilterMode::Social;
    case eco::ActionFilterMode::Social:
        return eco::ActionFilterMode::Reproduction;
    case eco::ActionFilterMode::Reproduction:
        return eco::ActionFilterMode::Survival;
    case eco::ActionFilterMode::Survival:
        return eco::ActionFilterMode::All;
    }
    return eco::ActionFilterMode::All;
}

eco::OverlayTemporalMode next_overlay_temporal(
    eco::OverlayTemporalMode mode
) {
    switch (mode) {
    case eco::OverlayTemporalMode::Instant:
        return eco::OverlayTemporalMode::Responsive;
    case eco::OverlayTemporalMode::Responsive:
        return eco::OverlayTemporalMode::Stable;
    case eco::OverlayTemporalMode::Stable:
        return eco::OverlayTemporalMode::Instant;
    }
    return eco::OverlayTemporalMode::Stable;
}


void draw_sparkline(
    const char* label,
    const MetricHistory& history,
    const std::array<float, MetricHistory::capacity>& series,
    Rectangle bounds,
    Color color
) {
    DrawRectangleRec(bounds, Fade(BLACK, 0.34F));
    DrawRectangleLinesEx(bounds, 1.0F, Fade(GRAY, 0.30F));

    if (history.count == 0) {
        DrawText(
            label,
            static_cast<int>(bounds.x + 6.0F),
            static_cast<int>(bounds.y + 4.0F),
            13,
            GRAY
        );
        return;
    }

    float minimum = history.value(series, 0);
    float maximum = minimum;
    for (std::size_t index = 1; index < history.count; ++index) {
        const float value = history.value(series, index);
        minimum = std::min(minimum, value);
        maximum = std::max(maximum, value);
    }

    if (std::abs(maximum - minimum) < 1.0e-6F) {
        maximum = minimum + 1.0F;
    }

    const float current =
        history.value(series, history.count - 1);

    DrawText(
        TextFormat("%s  %.3g", label, current),
        static_cast<int>(bounds.x + 6.0F),
        static_cast<int>(bounds.y + 4.0F),
        13,
        LIGHTGRAY
    );

    if (history.count < 2) {
        return;
    }

    const float left = bounds.x + 5.0F;
    const float right = bounds.x + bounds.width - 5.0F;
    const float top = bounds.y + 19.0F;
    const float bottom = bounds.y + bounds.height - 5.0F;

    Vector2 previous{};
    for (std::size_t index = 0; index < history.count; ++index) {
        const float normalized =
            (history.value(series, index) - minimum) /
            (maximum - minimum);
        const float fraction =
            static_cast<float>(index) /
            static_cast<float>(history.count - 1);

        const Vector2 point{
            left + (right - left) * fraction,
            bottom - (bottom - top) * normalized
        };

        if (index > 0) {
            DrawLineV(previous, point, color);
        }
        previous = point;
    }
}

void draw_event_legend(float x, float y) {
    DrawCircleLines(static_cast<int>(x + 7), static_cast<int>(y + 7), 5.0F,
        Color{83, 240, 255, 255});
    DrawText("birth", static_cast<int>(x + 18), static_cast<int>(y), 13, LIGHTGRAY);

    DrawLineEx(Vector2{x + 74.0F, y + 2.0F}, Vector2{x + 84.0F, y + 12.0F},
        1.0F, Color{255, 78, 82, 255});
    DrawLineEx(Vector2{x + 74.0F, y + 12.0F}, Vector2{x + 84.0F, y + 2.0F},
        1.0F, Color{255, 78, 82, 255});
    DrawText("death", static_cast<int>(x + 90), static_cast<int>(y), 13, LIGHTGRAY);

    DrawLineEx(Vector2{x + 158.0F, y + 7.0F}, Vector2{x + 168.0F, y + 7.0F},
        1.0F, Color{255, 174, 48, 255});
    DrawLineEx(Vector2{x + 163.0F, y + 2.0F}, Vector2{x + 163.0F, y + 12.0F},
        1.0F, Color{255, 174, 48, 255});
    DrawText("harvest", static_cast<int>(x + 174), static_cast<int>(y), 13, LIGHTGRAY);

    DrawText("◇ reproduce", static_cast<int>(x + 260), static_cast<int>(y), 13,
        Color{247, 105, 255, 255});
}

void draw_panel(
    const eco::Frame& frame,
    const eco::RenderOptions& options,
    ObservationPreset preset,
    const eco::RenderDetail& detail,
    const eco::WorldRenderer& renderer,
    const eco::SocialLoop& social,
    const MetricHistory& history,
    const Camera2D& camera,
    bool show_social,
    bool follow_selected,
    const std::vector<eco::SocialNeighbor>& selected_neighbors,
    const std::string& reader_error
) {
    const eco::RenderLod lod = detail.dominant;
    const float panel_width = kSidebarWidth - kPanelMargin * 2.0F;
    const float panel_height = static_cast<float>(GetScreenHeight()) - 24.0F;

    DrawRectangleRec(
        Rectangle{kPanelMargin, kPanelMargin, panel_width, panel_height},
        Color{5, 10, 14, 244}
    );
    DrawRectangleLinesEx(
        Rectangle{kPanelMargin, kPanelMargin, panel_width, panel_height},
        1.0F,
        Fade(SKYBLUE, 0.25F)
    );

    const eco::FrameDiagnostics& diagnostics = renderer.diagnostics();
    const eco::SocialStats& stats = social.stats();
    const eco::RenderPerformance& performance = renderer.performance();
    const eco::OverlayUsage& overlay_usage = renderer.overlay_usage();

    DrawText(
        TextFormat("Tick: %llu", static_cast<unsigned long long>(frame.tick)),
        26, 22, 22, RAYWHITE
    );
    DrawText(
        TextFormat(
            "Entities: %u  FPS: %d  Zoom: %.2f",
            static_cast<unsigned int>(frame.entities.size()),
            GetFPS(),
            camera.zoom
        ),
        26, 49, 17, RAYWHITE
    );
    DrawText(
        TextFormat(
            "LOD: %s (%s)  spacing %.1fpx",
            eco::render_lod_name(lod),
            eco::lod_mode_name(options.lod_mode),
            detail.projected_spacing
        ),
        26, 72, 16, SKYBLUE
    );
    DrawText(
        TextFormat(
            "R%d view %s  hazard %s  filter %s",
            options.resource_channel + 1,
            eco::environment_view_name(options.environment_view),
            options.show_hazard ? "on" : "off",
            eco::environment_filter_name(options.environment_filter)
        ),
        26, 95, 14, LIGHTGRAY
    );
    DrawText(
        TextFormat(
            "Preset %s | B %s | A %s | Y %s | Q %s",
            observation_preset_name(preset),
            eco::behavior_overlay_name(options.behavior_overlay),
            eco::action_filter_name(options.action_filter),
            eco::overlay_temporal_name(options.overlay_temporal),
            options.focus_selected_group ? "focus" : "all"
        ),
        26, 119, 13, GRAY
    );
    DrawText(
        "F1-6 presets | A action | Y time | E view | T env | [ ] group",
        26, 139, 13, GRAY
    );

    if (!reader_error.empty()) {
        DrawText(reader_error.c_str(), 26, 160, 13, ORANGE);
    }

    const eco::EntitySample* selected =
        options.selected_entity_id == 0
            ? nullptr
            : find_entity(frame, options.selected_entity_id);
    std::uint64_t effective_group_id = options.selected_group_id;
    if (selected != nullptr && selected->group_id != 0) {
        effective_group_id = selected->group_id;
    }
    const eco::GroupBehaviorSummary* selected_group =
        renderer.group_behavior(effective_group_id, options.overlay_temporal);

    DrawText("Inspector", 26, 184, 17, YELLOW);

    if (selected == nullptr && selected_group == nullptr) {
        const auto& groups = renderer.group_behaviors(options.overlay_temporal);
        if (options.selected_entity_id != 0) {
            DrawText("Selected agent is no longer alive in this frame.",
                26, 207, 14, RED);
        } else if (groups.empty()) {
            DrawText("Click a visible agent or group marker.",
                26, 207, 14, GRAY);
        } else {
            DrawText("Top groups: click a center, or use [ and ] to cycle",
                26, 207, 13, GRAY);
            int y = 227;
            for (std::size_t index = 0; index < std::min<std::size_t>(groups.size(), 5U); ++index) {
                const auto& group = groups[index];
                DrawText(
                    TextFormat(
                        "g%llu n%u %s %.0f%% coh %.2f",
                        static_cast<unsigned long long>(group.group_id),
                        static_cast<unsigned int>(group.members),
                        action_name(static_cast<std::uint8_t>(group.dominant_action)),
                        group.dominant_action_fraction * 100.0F,
                        group.coherence
                    ),
                    34, y, 13, group.coherence > 0.45F ? SKYBLUE : LIGHTGRAY
                );
                y += 20;
            }
        }
    } else if (selected == nullptr && selected_group != nullptr) {
        const float group_speed = std::sqrt(
            selected_group->mean_vx * selected_group->mean_vx +
            selected_group->mean_vy * selected_group->mean_vy
        );
        DrawText(
            TextFormat(
                "GROUP %llu  members %u",
                static_cast<unsigned long long>(selected_group->group_id),
                static_cast<unsigned int>(selected_group->members)
            ),
            26, 207, 15, Color{255, 204, 91, 255}
        );
        DrawText(
            TextFormat(
                "center %.2f,%.2f  spread %.2f / %.2f",
                selected_group->x, selected_group->y,
                selected_group->spread_major, selected_group->spread_minor
            ),
            26, 229, 13, RAYWHITE
        );
        DrawText(
            TextFormat(
                "coherence %.2f  active %.0f%%  speed %.3f",
                selected_group->coherence,
                selected_group->active_fraction * 100.0F,
                group_speed
            ),
            26, 249, 13, RAYWHITE
        );
        DrawText(
            TextFormat(
                "dominant %s %.0f%%  focus %s  follow %s",
                action_name(static_cast<std::uint8_t>(selected_group->dominant_action)),
                selected_group->dominant_action_fraction * 100.0F,
                options.focus_selected_group ? "on" : "off",
                follow_selected ? "on" : "off"
            ),
            26, 269, 13, LIGHTGRAY
        );
        draw_group_action_mix(
            *selected_group,
            Rectangle{28.0F, 291.0F, panel_width - 28.0F, 10.0F}
        );
        const eco::EnvironmentProbe probe = renderer.probe_environment(
            frame, selected_group->x, selected_group->y, options.resource_channel
        );
        if (probe.valid) {
            DrawText(
                TextFormat(
                    "center cell %u,%u  R%d %.3g  hazard %.3f",
                    probe.cell_x, probe.cell_y,
                    options.resource_channel + 1,
                    probe.resources[static_cast<std::size_t>(options.resource_channel)],
                    probe.hazard
                ),
                26, 331, 12, Color{102, 220, 255, 255}
            );
            DrawText(
                TextFormat("resource gradient %.3g", probe.gradient_magnitude),
                26, 347, 12, LIGHTGRAY
            );
        }
    } else {
        const float speed = std::sqrt(
            selected->vx * selected->vx +
            selected->vy * selected->vy
        );

        DrawText(
            TextFormat(
                "ID %llu  group %llu  lineage %llu",
                static_cast<unsigned long long>(selected->entity_id),
                static_cast<unsigned long long>(selected->group_id),
                static_cast<unsigned long long>(selected->lineage_id)
            ),
            26, 207, 14, RAYWHITE
        );
        DrawText(
            TextFormat(
                "energy %.3f/%.3f  integrity %.3f  fertility %.3f",
                selected->energy,
                frame.layout.max_energy,
                selected->integrity,
                selected->fertility
            ),
            26, 227, 14, RAYWHITE
        );
        DrawText(
            TextFormat(
                "age %.1f%%  generation %u  velocity %.3f",
                selected->age_fraction * 100.0F,
                selected->generation,
                speed
            ),
            26, 247, 14, RAYWHITE
        );
        DrawText(
            TextFormat(
                "action %s [%s]  target %llu",
                action_name(selected->action),
                selected->action_success ? "success" : "not-success",
                static_cast<unsigned long long>(selected->target_id)
            ),
            26, 267, 14, RAYWHITE
        );
        DrawText(
            TextFormat(
                "relations %u  follow %s  group-focus %s",
                static_cast<unsigned int>(selected_neighbors.size()),
                follow_selected ? "on" : "off",
                options.focus_selected_group ? "on" : "off"
            ),
            26, 287, 14, LIGHTGRAY
        );

        if (selected_group != nullptr) {
            DrawText(
                TextFormat(
                    "group n %u  coherence %.2f  %s %.0f%%",
                    static_cast<unsigned int>(selected_group->members),
                    selected_group->coherence,
                    action_name(static_cast<std::uint8_t>(selected_group->dominant_action)),
                    selected_group->dominant_action_fraction * 100.0F
                ),
                26, 307, 13, Color{255, 204, 91, 255}
            );
        } else {
            DrawText("group behavior: independent", 26, 307, 13, GRAY);
        }

        const eco::EnvironmentProbe probe = renderer.probe_environment(
            frame, selected->x, selected->y, options.resource_channel
        );
        if (probe.valid) {
            DrawText(
                TextFormat(
                    "cell %u,%u  R1 %.3g R2 %.3g R3 %.3g R4 %.3g",
                    probe.cell_x, probe.cell_y,
                    probe.resources[0], probe.resources[1],
                    probe.resources[2], probe.resources[3]
                ),
                26, 327, 12, Color{102, 220, 255, 255}
            );
            DrawText(
                TextFormat(
                    "hazard %.3f  R%d gradient %.3g",
                    probe.hazard, options.resource_channel + 1,
                    probe.gradient_magnitude
                ),
                26, 343, 12, LIGHTGRAY
            );
        }
    }

    DrawText("Frame dynamics", 26, 365, 17, Color{117, 242, 120, 255});
    DrawText(
        TextFormat(
            "+birth %u  -death %u  harvest %u  reproduce %u",
            static_cast<unsigned int>(diagnostics.births),
            static_cast<unsigned int>(diagnostics.deaths),
            static_cast<unsigned int>(diagnostics.harvests),
            static_cast<unsigned int>(diagnostics.reproductions)
        ),
        26, 389, 14, RAYWHITE
    );
    DrawText(
        TextFormat(
            "moveR %u  moveS %u  share %u  signal %u  flee %u",
            static_cast<unsigned int>(diagnostics.move_resource),
            static_cast<unsigned int>(diagnostics.move_social),
            static_cast<unsigned int>(diagnostics.shares),
            static_cast<unsigned int>(diagnostics.signals),
            static_cast<unsigned int>(diagnostics.flees)
        ),
        26, 409, 14, RAYWHITE
    );
    DrawText(
        TextFormat(
            "moving %u/%u speed %.4f  resource %.3g hazard %.3f",
            static_cast<unsigned int>(diagnostics.moving_entities),
            static_cast<unsigned int>(frame.entities.size()),
            diagnostics.mean_speed,
            diagnostics.mean_resource,
            diagnostics.mean_hazard
        ),
        26, 429, 14, RAYWHITE
    );
    draw_event_legend(27.0F, 453.0F);

    if (!show_social) {
        return;
    }

    DrawText("System trends", 26, 466, 17, SKYBLUE);
    DrawText(
        TextFormat(
            "groups %u  edges %u/%u  rumors %u/%u",
            static_cast<unsigned int>(stats.active_groups),
            static_cast<unsigned int>(stats.relationship_edges),
            static_cast<unsigned int>(stats.relationship_capacity),
            static_cast<unsigned int>(stats.active_rumors),
            static_cast<unsigned int>(stats.rumor_capacity)
        ),
        26, 489, 13, RAYWHITE
    );
    DrawText(
        TextFormat(
            "trust %.3f  reputation %.3f  stress %.3f  suppressed %u",
            stats.mean_trust,
            stats.mean_reputation,
            stats.mean_stress,
            static_cast<unsigned int>(stats.suppressed_relationships)
        ),
        26, 508, 13, RAYWHITE
    );
    DrawText(
        TextFormat(
            "render O/H/D %.2f/%.2f/%.2fms  overlays A%u G%u X%u",
            performance.observe_ema_ms,
            performance.heatmap_ema_ms,
            performance.draw_ema_ms,
            static_cast<unsigned int>(overlay_usage.agent_markers),
            static_cast<unsigned int>(overlay_usage.group_markers),
            static_cast<unsigned int>(overlay_usage.action_glyphs)
        ),
        26, 527, 12, Color{150, 190, 210, 255}
    );

    draw_sparkline(
        "population",
        history,
        history.population,
        Rectangle{26.0F, 550.0F, 464.0F, 52.0F},
        Color{102, 226, 255, 255}
    );
    draw_sparkline(
        "births",
        history,
        history.births,
        Rectangle{26.0F, 609.0F, 225.0F, 49.0F},
        Color{83, 240, 255, 255}
    );
    draw_sparkline(
        "deaths",
        history,
        history.deaths,
        Rectangle{265.0F, 609.0F, 225.0F, 49.0F},
        Color{255, 78, 82, 255}
    );
    draw_sparkline(
        "resource",
        history,
        history.resource,
        Rectangle{26.0F, 665.0F, 225.0F, 49.0F},
        Color{117, 242, 120, 255}
    );
    draw_sparkline(
        "mean speed",
        history,
        history.speed,
        Rectangle{265.0F, 665.0F, 225.0F, 49.0F},
        Color{100, 205, 255, 255}
    );
    draw_sparkline(
        "trust",
        history,
        history.trust,
        Rectangle{26.0F, 721.0F, 225.0F, 49.0F},
        Color{117, 232, 154, 255}
    );
    draw_sparkline(
        "stress",
        history,
        history.stress,
        Rectangle{265.0F, 721.0F, 225.0F, 49.0F},
        Color{255, 120, 108, 255}
    );

    DrawText("Emergent events", 26, 781, 16, LIGHTGRAY);

    int y = 803;
    int shown = 0;
    for (const eco::SocialEvent& event : social.recent_events()) {
        DrawText(
            TextFormat(
                "[%llu] %s",
                static_cast<unsigned long long>(event.tick),
                event.text.c_str()
            ),
            26, y, 13, LIGHTGRAY
        );
        y += 18;
        if (++shown >= 5 || y > GetScreenHeight() - 24) {
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

    InitWindow(1440, 900, "Eco Game Runtime");
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

            while (running.load(std::memory_order_relaxed)) {
                if (reader.read_latest(working)) {
                    {
                        std::lock_guard lock(error_mutex);
                        reader_error.clear();
                    }
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
    std::uint64_t observed_stream_epoch = renderer.stream_epoch();

    eco::RenderOptions options{};
    ObservationPreset observation_preset = ObservationPreset::Overview;
    apply_observation_preset(observation_preset, options);
    bool show_social = true;
    bool follow_selected = false;
    bool camera_initialized = false;
    bool heatmap_dirty = false;

    MetricHistory history;
    std::vector<eco::SocialNeighbor> selected_neighbors;
    std::uint64_t last_social_tick = 0;
    eco::RenderLod last_lod = eco::RenderLod::Macro;
    bool has_last_lod = false;
    float last_environment_detail = -1.0F;
    float last_density_weight = -1.0F;

    Camera2D camera{};
    camera.zoom = 1.0F;

    while (!WindowShouldClose()) {
        bool history_due = false;
        Rectangle viewport = world_viewport();
        if (camera_initialized) {
            update_camera_offset(camera, viewport);
        }

        const bool received = exchange.consume(current);

        if (received) {
            renderer.observe_frame(current);
            heatmap_dirty = true;

            if (renderer.stream_epoch() != observed_stream_epoch) {
                observed_stream_epoch = renderer.stream_epoch();
                options.selected_entity_id = 0;
                options.selected_group_id = 0;
                options.focus_selected_group = false;
                selected_neighbors.clear();
                follow_selected = false;
                social = eco::SocialLoop{};
                history = MetricHistory{};
                history_due = false;
                last_social_tick = 0;
                camera_initialized = false;
                has_last_lod = false;
                last_environment_detail = -1.0F;
                last_density_weight = -1.0F;
            }

            const std::uint64_t social_period =
                current.entities.size() > 100000
                    ? 12
                    : current.entities.size() > 50000
                        ? 6
                        : 3;

            if (last_social_tick == 0 ||
                current.tick >= last_social_tick + social_period) {
                social.update(current);
                history_due = true;
                last_social_tick = current.tick;

                if (options.selected_entity_id != 0) {
                    selected_neighbors = social.strongest_neighbors(
                        options.selected_entity_id,
                        24
                    );
                }
            }

            if (!camera_initialized) {
                fit_camera(camera, current, viewport);
                camera_initialized = true;
            }

            if (options.selected_entity_id != 0) {
                const eco::EntitySample* selected = find_entity(
                    current, options.selected_entity_id
                );
                if (selected != nullptr) {
                    if (selected->group_id != 0) {
                        options.selected_group_id = selected->group_id;
                    }
                } else {
                    // The individual died or left the frame. Preserve the
                    // social context when its group still exists; otherwise
                    // clear the complete selection instead of leaving a stale
                    // inspector warning indefinitely.
                    options.selected_entity_id = 0;
                    selected_neighbors.clear();
                    if (options.selected_group_id == 0 ||
                        renderer.group_behavior(options.selected_group_id, options.overlay_temporal) == nullptr) {
                        options.selected_group_id = 0;
                        options.focus_selected_group = false;
                        follow_selected = false;
                    }
                }
            } else if (options.selected_group_id != 0 &&
                       renderer.group_behavior(options.selected_group_id, options.overlay_temporal) == nullptr) {
                options.selected_group_id = 0;
                options.focus_selected_group = false;
                follow_selected = false;
            }

            if (follow_selected) {
                const eco::EntitySample* selected = options.selected_entity_id == 0
                    ? nullptr
                    : find_entity(current, options.selected_entity_id);
                if (selected != nullptr) {
                    camera.target = Vector2{selected->x, selected->y};
                } else if (options.selected_group_id != 0) {
                    const eco::GroupBehaviorSummary* group =
                        renderer.group_behavior(options.selected_group_id, options.overlay_temporal);
                    if (group != nullptr) {
                        camera.target = Vector2{group->x, group->y};
                    }
                }
            }
        }

        if (current.entities.empty() && current.tick == 0) {
            BeginDrawing();
            ClearBackground(Color{14, 17, 22, 255});
            DrawText("Waiting for eco_live.bin ...", 40, 40, 30, RAYWHITE);
            DrawText(shared_path.string().c_str(), 40, 82, 18, GRAY);
            EndDrawing();
            continue;
        }

        viewport = world_viewport();
        update_camera_offset(camera, viewport);

        const Vector2 mouse = GetMousePosition();
        const bool mouse_in_world = CheckCollisionPointRec(mouse, viewport);

        const float wheel = GetMouseWheelMove();
        if (wheel != 0.0F && mouse_in_world) {
            const Vector2 before = GetScreenToWorld2D(mouse, camera);
            camera.zoom = std::clamp(
                camera.zoom * std::pow(1.15F, wheel),
                0.01F,
                300.0F
            );
            const Vector2 after = GetScreenToWorld2D(mouse, camera);
            camera.target.x += before.x - after.x;
            camera.target.y += before.y - after.y;
            heatmap_dirty = true;
        }

        if (mouse_in_world && IsMouseButtonDown(MOUSE_BUTTON_MIDDLE)) {
            const Vector2 delta = GetMouseDelta();
            camera.target.x -= delta.x / camera.zoom;
            camera.target.y -= delta.y / camera.zoom;
            follow_selected = false;
        }

        if (mouse_in_world && IsMouseButtonPressed(MOUSE_BUTTON_LEFT)) {
            const std::uint64_t entity_id = renderer.pick_entity(
                current,
                camera,
                mouse
            );
            if (entity_id != 0) {
                options.selected_entity_id = entity_id;
                const eco::EntitySample* selected = find_entity(current, entity_id);
                options.selected_group_id = selected == nullptr
                    ? 0
                    : selected->group_id;
                selected_neighbors = social.strongest_neighbors(entity_id, 24);
            } else {
                options.selected_entity_id = 0;
                options.selected_group_id = renderer.pick_group(
                    current,
                    camera,
                    mouse
                );
                selected_neighbors.clear();
                if (options.selected_group_id == 0) {
                    options.focus_selected_group = false;
                }
            }
            follow_selected = false;
        }

        if (IsKeyPressed(KEY_F1)) {
            observation_preset = ObservationPreset::Overview;
            apply_observation_preset(observation_preset, options);
            heatmap_dirty = true;
        }
        if (IsKeyPressed(KEY_F2)) {
            observation_preset = ObservationPreset::Ecology;
            apply_observation_preset(observation_preset, options);
            heatmap_dirty = true;
        }
        if (IsKeyPressed(KEY_F3)) {
            observation_preset = ObservationPreset::Migration;
            apply_observation_preset(observation_preset, options);
            heatmap_dirty = true;
        }
        if (IsKeyPressed(KEY_F4)) {
            observation_preset = ObservationPreset::Social;
            apply_observation_preset(observation_preset, options);
            heatmap_dirty = true;
        }
        if (IsKeyPressed(KEY_F5)) {
            observation_preset = ObservationPreset::Survival;
            apply_observation_preset(observation_preset, options);
            heatmap_dirty = true;
        }
        if (IsKeyPressed(KEY_F6)) {
            observation_preset = ObservationPreset::Reproduction;
            apply_observation_preset(observation_preset, options);
            heatmap_dirty = true;
        }
        if (IsKeyPressed(KEY_A)) {
            options.action_filter = next_action_filter(options.action_filter);
            observation_preset = ObservationPreset::Custom;
        }
        if (IsKeyPressed(KEY_Y)) {
            options.overlay_temporal = next_overlay_temporal(
                options.overlay_temporal
            );
            observation_preset = ObservationPreset::Custom;
        }

        if (IsKeyPressed(KEY_ONE)) {
            observation_preset = ObservationPreset::Custom;
            options.resource_channel = 0;
            heatmap_dirty = true;
        }
        if (IsKeyPressed(KEY_TWO)) {
            observation_preset = ObservationPreset::Custom;
            options.resource_channel = 1;
            heatmap_dirty = true;
        }
        if (IsKeyPressed(KEY_THREE)) {
            observation_preset = ObservationPreset::Custom;
            options.resource_channel = 2;
            heatmap_dirty = true;
        }
        if (IsKeyPressed(KEY_FOUR)) {
            observation_preset = ObservationPreset::Custom;
            options.resource_channel = 3;
            heatmap_dirty = true;
        }
        if (IsKeyPressed(KEY_E)) {
            observation_preset = ObservationPreset::Custom;
            options.environment_view = next_environment_view(
                options.environment_view
            );
            heatmap_dirty = true;
        }
        if (IsKeyPressed(KEY_H)) {
            observation_preset = ObservationPreset::Custom;
            options.show_hazard = !options.show_hazard;
            heatmap_dirty = true;
        }
        if (IsKeyPressed(KEY_T)) {
            observation_preset = ObservationPreset::Custom;
            options.environment_filter = next_environment_filter(
                options.environment_filter
            );
            heatmap_dirty = true;
        }
        if (IsKeyPressed(KEY_P)) {
            observation_preset = ObservationPreset::Custom;
            options.show_population_density =
                !options.show_population_density;
            heatmap_dirty = true;
        }
        if (IsKeyPressed(KEY_C)) {
            observation_preset = ObservationPreset::Custom;
            options.show_environment_change =
                !options.show_environment_change;
            heatmap_dirty = true;
        }
        if (IsKeyPressed(KEY_B)) {
            observation_preset = ObservationPreset::Custom;
            options.behavior_overlay = next_behavior_overlay(
                options.behavior_overlay
            );
        }
        if (IsKeyPressed(KEY_Q)) {
            options.focus_selected_group =
                options.selected_group_id != 0 && !options.focus_selected_group;
        }
        if (IsKeyPressed(KEY_LEFT_BRACKET)) {
            options.selected_entity_id = 0;
            options.selected_group_id = cycle_group_selection(
                renderer.group_behaviors(options.overlay_temporal), options.selected_group_id, -1
            );
            selected_neighbors.clear();
            follow_selected = false;
        }
        if (IsKeyPressed(KEY_RIGHT_BRACKET)) {
            options.selected_entity_id = 0;
            options.selected_group_id = cycle_group_selection(
                renderer.group_behaviors(options.overlay_temporal), options.selected_group_id, 1
            );
            selected_neighbors.clear();
            follow_selected = false;
        }
        if (IsKeyPressed(KEY_M)) {
            observation_preset = ObservationPreset::Custom;
            options.show_event_markers =
                !options.show_event_markers;
        }
        if (IsKeyPressed(KEY_G)) {
            observation_preset = ObservationPreset::Custom;
            options.show_grid = !options.show_grid;
        }
        if (IsKeyPressed(KEY_V)) {
            observation_preset = ObservationPreset::Custom;
            options.show_velocity = !options.show_velocity;
        }
        if (IsKeyPressed(KEY_L)) {
            observation_preset = ObservationPreset::Custom;
            options.lod_mode = next_lod_mode(options.lod_mode);
            heatmap_dirty = true;
        }
        if (IsKeyPressed(KEY_F)) {
            follow_selected =
                (options.selected_entity_id != 0 || options.selected_group_id != 0) &&
                !follow_selected;
        }
        if (IsKeyPressed(KEY_S)) {
            show_social = !show_social;
        }
        if (IsKeyPressed(KEY_R)) {
            fit_camera(camera, current, viewport);
            follow_selected = false;
        }

        const eco::RenderDetail detail = eco::resolve_render_detail(
            current,
            camera,
            viewport,
            options.lod_mode
        );
        const eco::RenderLod lod = detail.dominant;
        if (!has_last_lod || lod != last_lod ||
            std::abs(detail.environment_detail - last_environment_detail) > 0.012F ||
            std::abs(detail.density_weight - last_density_weight) > 0.012F) {
            heatmap_dirty = true;
            last_lod = lod;
            has_last_lod = true;
            last_environment_detail = detail.environment_detail;
            last_density_weight = detail.density_weight;
        }

        if (heatmap_dirty) {
            renderer.update_heatmap(current, detail, options);
            heatmap_dirty = false;
        }
        if (history_due) {
            history.push(current, social, renderer.diagnostics());
        }

        std::string error_copy;
        {
            std::lock_guard lock(error_mutex);
            error_copy = reader_error;
        }

        BeginDrawing();
        ClearBackground(Color{8, 12, 16, 255});

        BeginScissorMode(
            static_cast<int>(viewport.x),
            static_cast<int>(viewport.y),
            static_cast<int>(viewport.width),
            static_cast<int>(viewport.height)
        );
        BeginMode2D(camera);
        renderer.draw(
            current,
            camera,
            viewport,
            options,
            selected_neighbors
        );
        EndMode2D();
        EndScissorMode();

        DrawRectangle(
            0,
            0,
            static_cast<int>(kSidebarWidth),
            GetScreenHeight(),
            Color{4, 8, 12, 255}
        );
        DrawLine(
            static_cast<int>(kSidebarWidth - 1.0F),
            0,
            static_cast<int>(kSidebarWidth - 1.0F),
            GetScreenHeight(),
            Fade(SKYBLUE, 0.30F)
        );

        draw_panel(
            current,
            options,
            observation_preset,
            detail,
            renderer,
            social,
            history,
            camera,
            show_social,
            follow_selected,
            selected_neighbors,
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
