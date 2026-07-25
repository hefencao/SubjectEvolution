#include "eco/gui_preferences.hpp"

#include <cassert>
#include <chrono>
#include <filesystem>
#include <fstream>
#include <thread>

int main() {
    namespace fs = std::filesystem;
    using namespace eco::preferences;
    const fs::path root = fs::temp_directory_path() / "eco_gui_preferences_v22";
    std::error_code error;
    fs::remove_all(root, error);
    fs::create_directories(root / "configs", error);
    fs::create_directories(root / "runs", error);

    assert(settings_path(root) == root / "src/saves/gui_settings.json");
    assert(state_path(root) == root / "src/saves/gui_state.json");
    assert(history_path(root) == root / "src/saves/experiment_history.json");

    GuiSettings settings = default_settings();
    settings.window_width = 1920;
    settings.window_height = 1080;
    settings.body_font_size = 18;
    settings.title_font_size = 32;
    settings.ui_scale = 1.2F;
    settings.font_family = "dejavu";
    std::string message;
    assert(save_settings(root, settings, message));
    auto loaded = load_settings(root, message);
    assert(loaded.window_width == 1920 && loaded.window_height == 1080);
    assert(loaded.body_font_size == 18 && loaded.title_font_size == 32);
    assert(loaded.font_family == "dejavu");

    GuiState state;
    state.sort_mode = ConfigSortMode::Size;
    state.config_search = "latent";
    state.tag_filter = "mvp";
    state.favorites_only = true;
    state.favorites.insert("one.json");
    state.last_config = "one.json";
    assert(save_state(root, state, message));
    auto loaded_state = load_state(root, message);
    assert(loaded_state.sort_mode == ConfigSortMode::Size);
    assert(loaded_state.favorites.contains("one.json"));
    assert(loaded_state.last_config == "one.json");

    {
        std::ofstream bad(settings_path(root), std::ios::trunc);
        bad << "not json";
    }
    message.clear();
    loaded = load_settings(root, message);
    assert(!message.empty());
    bool found_backup = false;
    for (const auto& entry : fs::directory_iterator(root / "src/saves")) {
        if (entry.path().filename().string().find("gui_settings.json.corrupt.") == 0) found_backup = true;
    }
    assert(found_backup);

    const fs::path a = root / "configs/a.json";
    const fs::path b = root / "configs/b.json";
    { std::ofstream out(a); out << "{}"; }
    std::this_thread::sleep_for(std::chrono::milliseconds(20));
    { std::ofstream out(b); out << "{\"larger\":true}"; }
    std::vector<fs::path> configs{a, b};
    sort_configs(configs, ConfigSortMode::Latest);
    assert(configs.front().filename() == "b.json");
    sort_configs(configs, ConfigSortMode::NameAscending);
    assert(configs.front().filename() == "a.json");
    sort_configs(configs, ConfigSortMode::Size);
    assert(configs.front().filename() == "b.json");

    { std::ofstream old(root / "runs/.experiment_history.json"); old << "[]\n"; }
    fs::remove(history_path(root), error);
    message.clear();
    assert(migrate_legacy_history(root, message));
    assert(fs::exists(history_path(root)));

    fs::remove_all(root, error);
    return 0;
}
