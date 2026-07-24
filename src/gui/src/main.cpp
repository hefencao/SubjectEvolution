#include "eco/protocol.hpp"
#include "eco/renderer.hpp"
#include "eco/shared_reader.hpp"
#include "eco/social_loop.hpp"

#include <algorithm>
#include <array>
#include <atomic>
#include <chrono>
#include <cctype>
#include <cstdint>
#include <filesystem>
#include <fstream>
#include <iostream>
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
        latest_tick_.store(pending_.tick, std::memory_order_relaxed);
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

    [[nodiscard]] std::uint64_t latest_tick() const noexcept {
        return latest_tick_.load(std::memory_order_relaxed);
    }

private:
    std::mutex mutex_;
    eco::Frame pending_;
    bool has_pending_ = false;
    std::atomic<std::uint64_t> latest_tick_{0};
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

struct ConfigScanResult {
    std::vector<std::filesystem::path> configs;
    std::string error;
};

struct ConfigFileStatus {
    bool launchable = false;
    std::uintmax_t size_bytes = 0;
    std::string message;
};

ConfigScanResult find_configs(
    const std::filesystem::path& config_dir
) {
    ConfigScanResult result;
    std::error_code error;

    if (!std::filesystem::is_directory(config_dir, error)) {
        result.error = "Configuration directory is not available: " +
            config_dir.string();
        return result;
    }

    std::filesystem::directory_iterator iterator(
        config_dir,
        std::filesystem::directory_options::skip_permission_denied,
        error
    );
    if (error) {
        result.error = "Could not read configuration directory: " +
            error.message();
        return result;
    }

    for (const auto& entry : iterator) {
        std::error_code entry_error;
        const bool regular = entry.is_regular_file(entry_error);
        if (!entry_error && regular && entry.path().extension() == ".json") {
            result.configs.push_back(std::filesystem::absolute(entry.path()));
        }
    }

    std::sort(
        result.configs.begin(),
        result.configs.end(),
        [](const auto& left, const auto& right) {
            std::string a = left.filename().string();
            std::string b = right.filename().string();
            std::transform(a.begin(), a.end(), a.begin(), [](unsigned char c) {
                return static_cast<char>(std::tolower(c));
            });
            std::transform(b.begin(), b.end(), b.begin(), [](unsigned char c) {
                return static_cast<char>(std::tolower(c));
            });
            return a == b ? left.string() < right.string() : a < b;
        }
    );
    return result;
}

ConfigFileStatus inspect_config_file(const std::filesystem::path& path) {
    ConfigFileStatus status;
    std::error_code error;
    if (!std::filesystem::is_regular_file(path, error)) {
        status.message = "The selected file no longer exists or is not regular.";
        return status;
    }

    status.size_bytes = std::filesystem::file_size(path, error);
    if (error) {
        status.message = "The selected file size could not be read.";
        return status;
    }
    if (status.size_bytes == 0) {
        status.message = "The selected JSON file is empty.";
        return status;
    }

    std::ifstream input(path, std::ios::binary);
    if (!input) {
        status.message = "The selected JSON file is not readable.";
        return status;
    }

    char first = '\0';
    while (input.get(first)) {
        if (!std::isspace(static_cast<unsigned char>(first))) {
            break;
        }
    }
    if (first != '{' && first != '[') {
        status.message = "The file does not begin with a JSON object or array.";
        return status;
    }

    status.launchable = true;
    status.message = "Readable JSON configuration.";
    return status;
}

std::string compact_bytes(std::uintmax_t bytes) {
    const double value = static_cast<double>(bytes);
    if (bytes >= 1024U * 1024U) {
        return TextFormat("%.2f MiB", value / (1024.0 * 1024.0));
    }
    if (bytes >= 1024U) {
        return TextFormat("%.1f KiB", value / 1024.0);
    }
    return std::to_string(bytes) + " B";
}

std::string elide_text(
    const std::string& text,
    int max_width,
    int font_size
) {
    if (max_width <= 0 || MeasureText(text.c_str(), font_size) <= max_width) {
        return text;
    }

    constexpr const char* ellipsis = "...";
    const int ellipsis_width = MeasureText(ellipsis, font_size);
    if (ellipsis_width >= max_width) {
        return ellipsis;
    }

    std::size_t left_count = text.size() / 2U;
    std::size_t right_start = left_count;
    while (left_count > 0U && right_start < text.size()) {
        const std::string candidate = text.substr(0, left_count) + ellipsis +
            text.substr(right_start);
        if (MeasureText(candidate.c_str(), font_size) <= max_width) {
            return candidate;
        }
        if (left_count >= text.size() - right_start) {
            --left_count;
        } else {
            ++right_start;
        }
    }
    return ellipsis;
}

int draw_wrapped_text(
    const std::string& text,
    int x,
    int y,
    int max_width,
    int font_size,
    int line_height,
    int max_lines,
    Color color
) {
    std::istringstream words(text);
    std::string line;
    std::string word;
    int lines = 0;

    while (words >> word && lines < max_lines) {
        const std::string candidate = line.empty() ? word : line + " " + word;
        if (!line.empty() && MeasureText(candidate.c_str(), font_size) > max_width) {
            DrawText(elide_text(line, max_width, font_size).c_str(), x, y, font_size, color);
            y += line_height;
            ++lines;
            line = word;
        } else {
            line = candidate;
        }
    }
    if (!line.empty() && lines < max_lines) {
        DrawText(elide_text(line, max_width, font_size).c_str(), x, y, font_size, color);
        y += line_height;
        ++lines;
    }
    return y;
}

struct LauncherLayout {
    Rectangle config_panel{};
    Rectangle list_view{};
    Rectangle details_panel{};
    Rectangle refresh_button{};
    Rectangle start_button{};
    Rectangle close_button{};
};

LauncherLayout make_launcher_layout(int width, int height) {
    const float margin = std::clamp(width * 0.035F, 28.0F, 52.0F);
    const float header_bottom = 150.0F;
    const float footer_height = 88.0F;
    const float gap = 22.0F;
    const float content_height = std::max(
        360.0F,
        static_cast<float>(height) - header_bottom - footer_height - margin
    );
    const float available_width = static_cast<float>(width) - margin * 2.0F - gap;
    const float left_width = std::clamp(available_width * 0.57F, 460.0F, 790.0F);
    const float right_width = std::max(300.0F, available_width - left_width);

    LauncherLayout layout;
    layout.config_panel = Rectangle{margin, header_bottom, left_width, content_height};
    layout.list_view = Rectangle{
        margin + 12.0F,
        header_bottom + 56.0F,
        left_width - 24.0F,
        content_height - 70.0F
    };
    layout.details_panel = Rectangle{
        margin + left_width + gap,
        header_bottom,
        right_width,
        content_height
    };
    layout.refresh_button = Rectangle{
        layout.config_panel.x + layout.config_panel.width - 128.0F,
        layout.config_panel.y + 12.0F,
        112.0F,
        32.0F
    };
    layout.start_button = Rectangle{
        static_cast<float>(width) - margin - 242.0F,
        static_cast<float>(height) - footer_height + 20.0F,
        242.0F,
        48.0F
    };
    layout.close_button = Rectangle{
        layout.start_button.x - 126.0F,
        layout.start_button.y,
        110.0F,
        48.0F
    };
    return layout;
}

std::size_t clamp_launcher_scroll(
    std::size_t selected,
    std::size_t item_count,
    std::size_t visible_rows,
    std::size_t scroll_start
) {
    if (item_count == 0U || visible_rows == 0U) {
        return 0U;
    }
    selected = std::min(selected, item_count - 1U);
    visible_rows = std::min(visible_rows, item_count);
    if (selected < scroll_start) {
        scroll_start = selected;
    } else if (selected >= scroll_start + visible_rows) {
        scroll_start = selected - visible_rows + 1U;
    }
    const std::size_t max_scroll = item_count - visible_rows;
    return std::min(scroll_start, max_scroll);
}

std::string command_preview(
    const std::string& python,
    const std::filesystem::path& config,
    const std::filesystem::path& project_root,
    const std::string& backend
) {
    const std::string stem = config.empty() ? "<config>" : config.stem().string();
    const std::string output = (
        project_root / "runs" / ("gui_" + stem + "_<timestamp>")
    ).string();
    return python +
        " -m subject_evolution.gui_interface.run_simulation --config \"" +
        config.string() + "\" --output \"" + output +
        "\" --stream \"" + output +
        "/eco_live.bin\" --backend " + backend;
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
    ConfigScanResult scan = find_configs(config_dir);
    std::vector<std::filesystem::path> configs = std::move(scan.configs);
    const std::array<std::string, 3> backends{"cpu", "gpu", "auto"};
    const std::array<std::string, 3> backend_descriptions{
        "CPU: conservative and reproducible; preferred for parity checks.",
        "GPU: request the CUDA simulation backend; fails if unavailable.",
        "Auto: let the Python launcher choose the available backend.",
    };

    std::size_t selected = 0;
    std::size_t scroll_start = 0;
    std::size_t backend = 0;
    std::string message = scan.error.empty()
        ? (configs.empty()
            ? "No JSON configurations were found."
            : "Choose a configuration and verify the launch summary.")
        : scan.error;
    Color message_color = scan.error.empty() ? GRAY : ORANGE;
    std::string last_title;

    auto refresh = [&]() {
        const std::filesystem::path previous =
            configs.empty() ? std::filesystem::path{} : configs[selected];
        ConfigScanResult refreshed = find_configs(config_dir);
        configs = std::move(refreshed.configs);
        selected = 0;
        if (!previous.empty()) {
            const auto found = std::find(configs.begin(), configs.end(), previous);
            if (found != configs.end()) {
                selected = static_cast<std::size_t>(found - configs.begin());
            }
        }
        if (!configs.empty()) {
            selected = std::min(selected, configs.size() - 1U);
        }
        scroll_start = 0;
        message = refreshed.error.empty()
            ? (configs.empty()
                ? "No JSON configurations were found."
                : "Configuration list refreshed.")
            : refreshed.error;
        message_color = refreshed.error.empty() ? GRAY : ORANGE;
    };

    while (!WindowShouldClose()) {
        const LauncherLayout layout = make_launcher_layout(
            GetScreenWidth(),
            GetScreenHeight()
        );
        constexpr float row_height = 42.0F;
        const std::size_t visible_rows = std::max<std::size_t>(
            1U,
            static_cast<std::size_t>(layout.list_view.height / row_height)
        );

        if (IsKeyPressed(KEY_ESCAPE)) {
            return std::nullopt;
        }
        if (IsKeyPressed(KEY_R) ||
            (IsMouseButtonPressed(MOUSE_BUTTON_LEFT) &&
             CheckCollisionPointRec(GetMousePosition(), layout.refresh_button))) {
            refresh();
        }

        if (!configs.empty()) {
            const auto move_selection = [&](long long delta) {
                const long long maximum = static_cast<long long>(configs.size() - 1U);
                const long long next = std::clamp(
                    static_cast<long long>(selected) + delta,
                    0LL,
                    maximum
                );
                selected = static_cast<std::size_t>(next);
            };

            if (IsKeyPressed(KEY_DOWN)) {
                move_selection(1);
            }
            if (IsKeyPressed(KEY_UP)) {
                move_selection(-1);
            }
            if (IsKeyPressed(KEY_PAGE_DOWN)) {
                move_selection(static_cast<long long>(visible_rows));
            }
            if (IsKeyPressed(KEY_PAGE_UP)) {
                move_selection(-static_cast<long long>(visible_rows));
            }
            if (IsKeyPressed(KEY_HOME)) {
                selected = 0;
            }
            if (IsKeyPressed(KEY_END)) {
                selected = configs.size() - 1U;
            }

            if (CheckCollisionPointRec(GetMousePosition(), layout.list_view)) {
                const float wheel = GetMouseWheelMove();
                if (wheel != 0.0F) {
                    const long long direction = wheel > 0.0F ? -1LL : 1LL;
                    const long long steps = std::max(
                        1LL,
                        static_cast<long long>(std::ceil(std::abs(wheel) * 3.0F))
                    );
                    move_selection(direction * steps);
                }
            }

            if (IsKeyPressed(KEY_LEFT) && backend > 0U) {
                --backend;
            }
            if (IsKeyPressed(KEY_RIGHT) && backend + 1U < backends.size()) {
                ++backend;
            }

            scroll_start = clamp_launcher_scroll(
                selected,
                configs.size(),
                visible_rows,
                scroll_start
            );
        } else {
            selected = 0;
            scroll_start = 0;
        }

        const std::filesystem::path selected_path = configs.empty()
            ? std::filesystem::path{}
            : configs[selected];
        const ConfigFileStatus file_status = selected_path.empty()
            ? ConfigFileStatus{}
            : inspect_config_file(selected_path);

        const std::string title = selected_path.empty()
            ? "Subject Evolution Launcher — no configuration"
            : "Subject Evolution Launcher — " +
                selected_path.filename().string() + " [" + backends[backend] + "]";
        if (title != last_title) {
            SetWindowTitle(title.c_str());
            last_title = title;
        }

        const bool mouse_start = IsMouseButtonPressed(MOUSE_BUTTON_LEFT) &&
            CheckCollisionPointRec(GetMousePosition(), layout.start_button);
        const bool start = IsKeyPressed(KEY_ENTER) || mouse_start;
        if (start) {
            if (configs.empty()) {
                message = "A configuration must be selected before launch.";
                message_color = ORANGE;
            } else if (!file_status.launchable) {
                message = file_status.message;
                message_color = ORANGE;
            } else {
                const std::string stem = selected_path.stem().string();
                const std::filesystem::path output = project_root / "runs" /
                    ("gui_" + stem + "_" + timestamp_suffix());
                return LaunchRequest{
                    project_root,
                    selected_path,
                    output,
                    output / "eco_live.bin",
                    python,
                    backends[backend],
                };
            }
        }
        if (IsMouseButtonPressed(MOUSE_BUTTON_LEFT) &&
            CheckCollisionPointRec(GetMousePosition(), layout.close_button)) {
            return std::nullopt;
        }

        BeginDrawing();
        ClearBackground(Color{14, 17, 22, 255});

        const int margin_x = static_cast<int>(layout.config_panel.x);
        DrawText("Subject Evolution", margin_x, 38, 34, RAYWHITE);
        DrawText("Simulation launcher", margin_x, 82, 21, LIGHTGRAY);
        DrawText(
            "Select one configuration, choose the execution backend, then review the exact launch context.",
            margin_x,
            112,
            16,
            GRAY
        );

        DrawRectangleRec(layout.config_panel, Color{7, 12, 17, 238});
        DrawRectangleLinesEx(layout.config_panel, 1.0F, Fade(SKYBLUE, 0.22F));
        DrawText(
            TextFormat("Configurations  %u", static_cast<unsigned int>(configs.size())),
            static_cast<int>(layout.config_panel.x + 16.0F),
            static_cast<int>(layout.config_panel.y + 17.0F),
            18,
            LIGHTGRAY
        );

        const Vector2 mouse = GetMousePosition();
        const bool refresh_hover = CheckCollisionPointRec(mouse, layout.refresh_button);
        DrawRectangleRec(
            layout.refresh_button,
            refresh_hover ? Color{55, 65, 76, 255} : Color{39, 45, 53, 255}
        );
        DrawText(
            "Refresh [R]",
            static_cast<int>(layout.refresh_button.x + 12.0F),
            static_cast<int>(layout.refresh_button.y + 8.0F),
            15,
            RAYWHITE
        );

        DrawRectangleRec(layout.list_view, Color{10, 15, 20, 255});
        BeginScissorMode(
            static_cast<int>(layout.list_view.x),
            static_cast<int>(layout.list_view.y),
            static_cast<int>(layout.list_view.width),
            static_cast<int>(layout.list_view.height)
        );
        const std::size_t row_end = std::min(
            configs.size(),
            scroll_start + visible_rows
        );
        for (std::size_t index = scroll_start; index < row_end; ++index) {
            const float row_y = layout.list_view.y +
                static_cast<float>(index - scroll_start) * row_height;
            const Rectangle item{
                layout.list_view.x,
                row_y,
                layout.list_view.width,
                row_height - 2.0F
            };
            const bool active = index == selected;
            const bool hovered = CheckCollisionPointRec(mouse, item);
            if (active) {
                DrawRectangleRec(item, Color{42, 91, 117, 255});
                DrawRectangle(
                    static_cast<int>(item.x),
                    static_cast<int>(item.y),
                    4,
                    static_cast<int>(item.height),
                    Color{103, 210, 255, 255}
                );
            } else if (hovered) {
                DrawRectangleRec(item, Color{24, 34, 43, 255});
            }

            const std::string filename = elide_text(
                configs[index].filename().string(),
                static_cast<int>(item.width - 78.0F),
                18
            );
            DrawText(
                filename.c_str(),
                static_cast<int>(item.x + 16.0F),
                static_cast<int>(item.y + 10.0F),
                18,
                active ? RAYWHITE : LIGHTGRAY
            );
            DrawText(
                TextFormat("%u", static_cast<unsigned int>(index + 1U)),
                static_cast<int>(item.x + item.width - 50.0F),
                static_cast<int>(item.y + 12.0F),
                14,
                active ? Color{185, 231, 255, 255} : DARKGRAY
            );

            if (IsMouseButtonPressed(MOUSE_BUTTON_LEFT) && hovered) {
                selected = index;
            }
        }
        EndScissorMode();

        if (configs.empty()) {
            DrawText(
                "No .json files are available in this directory.",
                static_cast<int>(layout.list_view.x + 20.0F),
                static_cast<int>(layout.list_view.y + 24.0F),
                16,
                ORANGE
            );
        } else if (configs.size() > visible_rows) {
            const Rectangle track{
                layout.list_view.x + layout.list_view.width - 7.0F,
                layout.list_view.y + 4.0F,
                3.0F,
                layout.list_view.height - 8.0F
            };
            const float fraction = static_cast<float>(visible_rows) /
                static_cast<float>(configs.size());
            const float thumb_height = std::max(28.0F, track.height * fraction);
            const std::size_t max_scroll = configs.size() - visible_rows;
            const float progress = max_scroll == 0U
                ? 0.0F
                : static_cast<float>(scroll_start) / static_cast<float>(max_scroll);
            const Rectangle thumb{
                track.x - 2.0F,
                track.y + (track.height - thumb_height) * progress,
                7.0F,
                thumb_height
            };
            DrawRectangleRec(track, Color{34, 40, 47, 255});
            DrawRectangleRec(thumb, Color{91, 136, 157, 255});
        }

        DrawRectangleRec(layout.details_panel, Color{7, 12, 17, 238});
        DrawRectangleLinesEx(layout.details_panel, 1.0F, Fade(SKYBLUE, 0.22F));
        const int details_x = static_cast<int>(layout.details_panel.x + 20.0F);
        const int details_width = static_cast<int>(layout.details_panel.width - 40.0F);
        int y = static_cast<int>(layout.details_panel.y + 18.0F);
        DrawText("Selected configuration", details_x, y, 18, LIGHTGRAY);
        y += 32;
        if (selected_path.empty()) {
            DrawText("None", details_x, y, 22, ORANGE);
            y += 38;
        } else {
            DrawText(
                elide_text(selected_path.filename().string(), details_width, 22).c_str(),
                details_x,
                y,
                22,
                RAYWHITE
            );
            y += 31;
            DrawText(
                elide_text(selected_path.string(), details_width, 14).c_str(),
                details_x,
                y,
                14,
                GRAY
            );
            y += 25;
            DrawText(
                (file_status.message +
                 (file_status.size_bytes > 0U
                    ? "  Size " + compact_bytes(file_status.size_bytes)
                    : "")).c_str(),
                details_x,
                y,
                14,
                file_status.launchable ? Color{103, 225, 151, 255} : ORANGE
            );
            y += 36;
        }

        DrawText("Backend", details_x, y, 18, LIGHTGRAY);
        y += 30;
        const float backend_gap = 10.0F;
        const float backend_width = (
            layout.details_panel.width - 40.0F - backend_gap * 2.0F
        ) / 3.0F;
        for (std::size_t index = 0; index < backends.size(); ++index) {
            const Rectangle item{
                layout.details_panel.x + 20.0F +
                    static_cast<float>(index) * (backend_width + backend_gap),
                static_cast<float>(y),
                backend_width,
                38.0F
            };
            const bool active = index == backend;
            const bool hovered = CheckCollisionPointRec(mouse, item);
            DrawRectangleRec(
                item,
                active
                    ? Color{42, 91, 117, 255}
                    : (hovered ? Color{55, 65, 76, 255} : Color{39, 45, 53, 255})
            );
            DrawText(
                backends[index].c_str(),
                static_cast<int>(item.x + item.width * 0.5F -
                    MeasureText(backends[index].c_str(), 17) * 0.5F),
                static_cast<int>(item.y + 10.0F),
                17,
                RAYWHITE
            );
            if (IsMouseButtonPressed(MOUSE_BUTTON_LEFT) && hovered) {
                backend = index;
            }
        }
        y += 50;
        y = draw_wrapped_text(
            backend_descriptions[backend],
            details_x,
            y,
            details_width,
            14,
            19,
            2,
            GRAY
        );
        y += 18;

        DrawText("Launch context", details_x, y, 18, LIGHTGRAY);
        y += 29;
        const std::string output_template = selected_path.empty()
            ? "runs/gui_<config>_<timestamp>/"
            : "runs/gui_" + selected_path.stem().string() + "_<timestamp>/";
        DrawText("Project", details_x, y, 13, GRAY);
        DrawText(
            elide_text(project_root.string(), details_width - 72, 14).c_str(),
            details_x + 72,
            y,
            14,
            LIGHTGRAY
        );
        y += 22;
        DrawText("Config dir", details_x, y, 13, GRAY);
        DrawText(
            elide_text(config_dir.string(), details_width - 72, 14).c_str(),
            details_x + 72,
            y,
            14,
            LIGHTGRAY
        );
        y += 22;
        DrawText("Python", details_x, y, 13, GRAY);
        DrawText(
            elide_text(python, details_width - 72, 14).c_str(),
            details_x + 72,
            y,
            14,
            LIGHTGRAY
        );
        y += 22;
        DrawText("Output", details_x, y, 13, GRAY);
        DrawText(
            elide_text(output_template, details_width - 72, 14).c_str(),
            details_x + 72,
            y,
            14,
            LIGHTGRAY
        );
        y += 34;

        DrawText("Command preview", details_x, y, 18, LIGHTGRAY);
        y += 28;
        draw_wrapped_text(
            command_preview(python, selected_path, project_root, backends[backend]),
            details_x,
            y,
            details_width,
            13,
            18,
            5,
            Color{149, 184, 200, 255}
        );

        DrawText(
            message.c_str(),
            margin_x,
            GetScreenHeight() - 64,
            15,
            message_color
        );
        DrawText(
            "Up/Down or wheel: select   PgUp/PgDn/Home/End: navigate   Left/Right: backend",
            margin_x,
            GetScreenHeight() - 39,
            13,
            GRAY
        );

        const bool close_hover = CheckCollisionPointRec(mouse, layout.close_button);
        DrawRectangleRec(
            layout.close_button,
            close_hover ? Color{62, 68, 77, 255} : Color{43, 47, 54, 255}
        );
        DrawText(
            "Close [Esc]",
            static_cast<int>(layout.close_button.x + 12.0F),
            static_cast<int>(layout.close_button.y + 15.0F),
            16,
            RAYWHITE
        );

        const bool start_enabled = !selected_path.empty() && file_status.launchable;
        const bool start_hover = CheckCollisionPointRec(mouse, layout.start_button);
        DrawRectangleRec(
            layout.start_button,
            !start_enabled
                ? Color{39, 48, 49, 255}
                : (start_hover ? Color{57, 151, 106, 255} : Color{48, 130, 91, 255})
        );
        DrawText(
            start_enabled ? "Start simulation [Enter]" : "Select a valid configuration",
            static_cast<int>(layout.start_button.x + 16.0F),
            static_cast<int>(layout.start_button.y + 15.0F),
            start_enabled ? 17 : 14,
            start_enabled ? RAYWHITE : GRAY
        );

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

eco::EntityRenderBackend next_entity_backend(
    eco::EntityRenderBackend backend
) {
    switch (backend) {
    case eco::EntityRenderBackend::Auto:
        return eco::EntityRenderBackend::GpuInstanced;
    case eco::EntityRenderBackend::GpuInstanced:
        return eco::EntityRenderBackend::CpuBatch;
    case eco::EntityRenderBackend::CpuBatch:
        return eco::EntityRenderBackend::Auto;
    }
    return eco::EntityRenderBackend::Auto;
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
    bool view_paused,
    std::uint64_t live_tick,
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

    DrawText(
        TextFormat("Tick: %llu", static_cast<unsigned long long>(frame.tick)),
        26, 22, 22, RAYWHITE
    );
    DrawText(
        TextFormat(
            view_paused
                ? "Entities: %u  FPS: %d  Zoom: %.2f  HOLD +%llu"
                : "Entities: %u  FPS: %d  Zoom: %.2f",
            static_cast<unsigned int>(frame.entities.size()),
            GetFPS(),
            camera.zoom,
            static_cast<unsigned long long>(
                live_tick > frame.tick ? live_tick - frame.tick : 0U
            )
        ),
        26, 49, 17, view_paused ? ORANGE : RAYWHITE
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
            "Preset %s | B %s | A %s | Y %s | U %s",
            observation_preset_name(preset),
            eco::behavior_overlay_name(options.behavior_overlay),
            eco::action_filter_name(options.action_filter),
            eco::overlay_temporal_name(options.overlay_temporal),
            eco::entity_render_backend_name(options.entity_backend)
        ),
        26, 119, 13, GRAY
    );
    DrawText(
        "F1-6 presets | Space hold | N sample | U render | Q focus",
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
            "render O %.1f H%.1f D%.1f | %s %u U%.2f S%.2f",
            performance.observe_ema_ms,
            performance.heatmap_ema_ms,
            performance.draw_ema_ms,
            performance.agent_gpu_active ? "GPU" : "CPU",
            static_cast<unsigned int>(performance.agent_instances),
            performance.agent_upload_ema_ms,
            performance.agent_draw_ema_ms
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
    SetWindowMinSize(1024, 700);
    SetTargetFPS(144);

    #if defined(__unix__) || defined(__APPLE__)
    pid_t simulation_process = -1;
    #endif

    std::string session_label;
    if (!viewer_only) {
        const auto request = show_launcher(project_root, config_dir, python);
        if (!request.has_value()) {
            CloseWindow();
            return 0;
        }
        shared_path = request->stream_path;
        session_label = request->config_path.filename().string();

        std::cout
            << "[eco-gui] selected config: " << request->config_path << '\n'
            << "[eco-gui] backend: " << request->backend << '\n'
            << "[eco-gui] output: " << request->output_path << '\n'
            << "[eco-gui] stream: " << request->stream_path << std::endl;

        #if defined(__unix__) || defined(__APPLE__)
        std::string launch_error;
        simulation_process = launch_simulation(*request, launch_error);
        if (simulation_process < 0) {
            std::cerr << "[eco-gui] launch failed: " << launch_error << std::endl;
            CloseWindow();
            return 1;
        }
        #else
        std::cerr << "[eco-gui] automatic simulation launch is not implemented "
                     "for this platform build." << std::endl;
        CloseWindow();
        return 1;
        #endif
    } else {
        session_label = shared_path.filename().string();
        std::cout << "[eco-gui] viewer stream: " << shared_path << std::endl;
    }

    const std::string runtime_title = viewer_only
        ? "Eco Game Runtime — stream " + session_label
        : "Eco Game Runtime — " + session_label;
    SetWindowTitle(runtime_title.c_str());

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
    bool view_paused = false;
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

        if (IsKeyPressed(KEY_SPACE)) {
            view_paused = !view_paused;
        }
        const bool sample_latest = view_paused && IsKeyPressed(KEY_N);
        const bool received = (!view_paused || sample_latest) &&
            exchange.consume(current);

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

        if (IsKeyPressed(KEY_U)) {
            options.entity_backend = next_entity_backend(options.entity_backend);
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

        if (view_paused) {
            const std::uint64_t live_tick = exchange.latest_tick();
            DrawRectangle(
                static_cast<int>(viewport.x + viewport.width - 194.0F),
                static_cast<int>(viewport.y + 12.0F),
                178,
                30,
                Color{35, 20, 8, 228}
            );
            DrawText(
                TextFormat(
                    "VIEW HOLD  +%llu  [N sample]",
                    static_cast<unsigned long long>(
                        live_tick > current.tick ? live_tick - current.tick : 0U
                    )
                ),
                static_cast<int>(viewport.x + viewport.width - 186.0F),
                static_cast<int>(viewport.y + 20.0F),
                12,
                ORANGE
            );
        }

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
            view_paused,
            exchange.latest_tick(),
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
