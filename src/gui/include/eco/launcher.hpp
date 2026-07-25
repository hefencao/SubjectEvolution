#pragma once

#include <cstdint>
#include <filesystem>
#include <optional>
#include <string>
#include <vector>

#include <raylib.h>

namespace eco::launcher {

enum class ExperimentMode : std::uint8_t {
    SingleRun,
    MultiSeed,
};

struct ResolutionChoice {
    int width = 1440;
    int height = 900;
    std::string label = "1440x900";
    bool custom = false;
};

struct LaunchRequest {
    std::filesystem::path project_root;
    std::filesystem::path original_config_path;
    std::filesystem::path config_path;
    std::filesystem::path output_path;
    std::filesystem::path stream_path;
    std::string python = "python3";
    std::string backend = "cpu";
    ExperimentMode mode = ExperimentMode::SingleRun;
    ResolutionChoice resolution{};
    std::vector<std::int64_t> seeds;
    std::uint64_t until_tick = 0;
    std::string command;
    std::string history_id;
    bool overwrite_partial = false;
};

struct ConfigScanResult {
    std::vector<std::filesystem::path> configs;
    std::string error;
};

struct ConfigFileStatus {
    bool launchable = false;
    std::uintmax_t size_bytes = 0;
    std::string message;
};

struct LauncherLayout {
    Rectangle config_panel{};
    Rectangle list_view{};
    Rectangle details_panel{};
    Rectangle details_view{};
    Rectangle refresh_button{};
    Rectangle start_button{};
    Rectangle close_button{};
};

struct ConfigScalar {
    std::string path;
    std::string value;
    std::string type;
};

ConfigScanResult find_configs(const std::filesystem::path& config_dir);
ConfigFileStatus inspect_config_file(const std::filesystem::path& path);
LauncherLayout make_launcher_layout(int width, int height);
std::size_t clamp_launcher_scroll(
    std::size_t selected,
    std::size_t item_count,
    std::size_t visible_rows,
    std::size_t scroll_start
);

std::vector<std::int64_t> parse_seed_list(
    const std::string& text,
    std::string& error
);

std::vector<ConfigScalar> inspect_scalar_config(
    const std::filesystem::path& config,
    std::string& error
);

bool create_resolved_config(
    const std::filesystem::path& source,
    const std::filesystem::path& destination,
    const std::vector<ConfigScalar>& overrides,
    std::optional<std::int64_t> single_seed,
    std::optional<std::uint64_t> until_tick,
    std::string& error
);

bool save_as_new_config(
    const std::filesystem::path& source,
    const std::filesystem::path& destination,
    const std::vector<ConfigScalar>& overrides,
    std::optional<std::int64_t> single_seed,
    std::optional<std::uint64_t> until_tick,
    std::string& error
);

bool replace_original_config(
    const std::filesystem::path& source,
    const std::vector<ConfigScalar>& overrides,
    std::optional<std::int64_t> single_seed,
    std::optional<std::uint64_t> until_tick,
    bool confirmed,
    std::string& error
);

std::string command_preview(const LaunchRequest& request, bool template_paths = false);

bool prepare_launch_request(LaunchRequest& request, std::string& error);

bool append_history(
    const LaunchRequest& request,
    const std::string& status,
    int exit_code,
    std::string& error
);

std::optional<LaunchRequest> show_launcher(
    const std::filesystem::path& project_root,
    const std::filesystem::path& config_dir,
    const std::string& python
);

const char* experiment_mode_name(ExperimentMode mode);

}  // namespace eco::launcher
