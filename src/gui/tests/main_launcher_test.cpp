#include <cassert>
#include <filesystem>
#include <fstream>
#include <string>

#define main eco_gui_embedded_main
#include "../src/gui/src/main.cpp"
#undef main

int main() {
    namespace fs = std::filesystem;
    const fs::path root = fs::temp_directory_path() / "eco_launcher_v20_test";
    std::error_code error;
    fs::remove_all(root, error);
    fs::create_directories(root, error);
    assert(!error);

    for (int index = 0; index < 30; ++index) {
        std::ofstream out(root / ("config_" + std::to_string(index) + ".json"));
        out << "{\"index\":" << index << "}";
    }
    {
        std::ofstream out(root / "ignore.txt");
        out << "not json";
    }
    {
        std::ofstream out(root / "empty.json");
    }
    {
        std::ofstream out(root / "invalid.json");
        out << "not-json";
    }

    const ConfigScanResult scan = find_configs(root);
    assert(scan.error.empty());
    assert(scan.configs.size() == 32U);

    const ConfigFileStatus valid = inspect_config_file(root / "config_0.json");
    assert(valid.launchable);
    assert(valid.size_bytes > 0U);

    const ConfigFileStatus empty = inspect_config_file(root / "empty.json");
    assert(!empty.launchable);
    assert(empty.message.find("empty") != std::string::npos);

    const ConfigFileStatus invalid = inspect_config_file(root / "invalid.json");
    assert(!invalid.launchable);
    assert(invalid.message.find("JSON") != std::string::npos);

    assert(clamp_launcher_scroll(0U, 30U, 10U, 0U) == 0U);
    assert(clamp_launcher_scroll(9U, 30U, 10U, 0U) == 0U);
    assert(clamp_launcher_scroll(10U, 30U, 10U, 0U) == 1U);
    assert(clamp_launcher_scroll(29U, 30U, 10U, 0U) == 20U);
    assert(clamp_launcher_scroll(3U, 30U, 10U, 20U) == 3U);
    assert(clamp_launcher_scroll(0U, 0U, 10U, 5U) == 0U);

    const LauncherLayout layout = make_launcher_layout(1440, 900);
    assert(layout.config_panel.x >= 0.0F);
    assert(layout.config_panel.y >= 0.0F);
    assert(layout.list_view.x >= layout.config_panel.x);
    assert(layout.list_view.y >= layout.config_panel.y);
    assert(layout.list_view.x + layout.list_view.width <=
        layout.config_panel.x + layout.config_panel.width + 0.01F);
    assert(layout.list_view.y + layout.list_view.height <=
        layout.config_panel.y + layout.config_panel.height + 0.01F);
    assert(layout.details_panel.x >=
        layout.config_panel.x + layout.config_panel.width);
    assert(layout.start_button.x + layout.start_button.width <= 1440.0F);
    assert(layout.start_button.y + layout.start_button.height <= 900.0F);

    const std::string preview = command_preview(
        "python3",
        root / "config_0.json",
        root,
        "cpu"
    );
    assert(preview.find("config_0.json") != std::string::npos);
    assert(preview.find("--backend cpu") != std::string::npos);
    assert(preview.find("eco_live.bin") != std::string::npos);

    fs::remove_all(root, error);
    return 0;
}
