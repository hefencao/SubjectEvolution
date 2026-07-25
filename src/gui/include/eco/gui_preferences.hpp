#pragma once

#include <filesystem>
#include <set>
#include <string>
#include <vector>

namespace eco::preferences {

enum class ConfigSortMode {
    Latest,
    NameAscending,
    NameDescending,
    Size,
};

struct GuiSettings {
    int window_width = 1440;
    int window_height = 900;
    int body_font_size = 16;
    int title_font_size = 31;
    int row_height = 38;
    int recent_experiments = 6;
    float ui_scale = 1.0F;
    std::string font_family = "auto";
};

struct GuiState {
    ConfigSortMode sort_mode = ConfigSortMode::Latest;
    std::string config_search;
    std::string tag_filter = "all";
    bool favorites_only = false;
    std::set<std::string> favorites;
    std::string last_config;
};

std::filesystem::path saves_directory(const std::filesystem::path& project_root);
std::filesystem::path settings_path(const std::filesystem::path& project_root);
std::filesystem::path state_path(const std::filesystem::path& project_root);
std::filesystem::path history_path(const std::filesystem::path& project_root);

GuiSettings default_settings();
GuiSettings load_settings(const std::filesystem::path& project_root, std::string& warning);
bool save_settings(const std::filesystem::path& project_root, const GuiSettings& settings, std::string& error);

GuiState load_state(const std::filesystem::path& project_root, std::string& warning);
bool save_state(const std::filesystem::path& project_root, const GuiState& state, std::string& error);

bool migrate_legacy_history(const std::filesystem::path& project_root, std::string& message);

const char* sort_mode_name(ConfigSortMode mode);
ConfigSortMode next_sort_mode(ConfigSortMode mode);

void sort_configs(std::vector<std::filesystem::path>& configs, ConfigSortMode mode);
std::string infer_config_tag(const std::filesystem::path& path);

}  // namespace eco::preferences
