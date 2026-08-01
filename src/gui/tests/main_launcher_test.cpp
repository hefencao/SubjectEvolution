#include "eco/launcher.hpp"
#include "eco/ui_font.hpp"

#include <cassert>
#include <filesystem>
#include <fstream>
#include <string>

int main() {
    namespace fs = std::filesystem;
    using namespace eco::launcher;

    const fs::path root = fs::temp_directory_path() / "eco_launcher_v24_test";
    std::error_code error;
    fs::remove_all(root, error);
    fs::create_directories(root / "configs", error);
    fs::create_directories(root / "runs", error);
    assert(!error);

    for (int index = 0; index < 30; ++index) {
        std::ofstream out(root / "configs" / ("config_" + std::to_string(index) + ".json"));
        out << "{\n"
            << "  \"run\": {\"seed\": " << (10001 + index)
            << ", \"ticks\": 500, \"enabled\": true},\n"
            << "  \"world\": {\"width\": 64, \"name\": \"test\"}\n"
            << "}\n";
    }
    {
        std::ofstream out(root / "configs/ignore.txt");
        out << "not json";
    }
    {
        std::ofstream out(root / "configs/empty.json");
    }
    {
        std::ofstream out(root / "configs/invalid.json");
        out << "not-json";
    }

    const ConfigScanResult scan = find_configs(root / "configs");
    assert(scan.error.empty());
    assert(scan.configs.size() == 32U);

    const fs::path source = root / "configs/config_0.json";
    const ConfigFileStatus valid = inspect_config_file(source);
    assert(valid.launchable);
    assert(valid.size_bytes > 0U);

    const ConfigFileStatus empty = inspect_config_file(root / "configs/empty.json");
    assert(!empty.launchable);
    const ConfigFileStatus invalid = inspect_config_file(root / "configs/invalid.json");
    assert(!invalid.launchable);

    assert(clamp_launcher_scroll(0U, 30U, 10U, 0U) == 0U);
    assert(clamp_launcher_scroll(10U, 30U, 10U, 0U) == 1U);
    assert(clamp_launcher_scroll(29U, 30U, 10U, 0U) == 20U);

    const LauncherLayout layout = make_launcher_layout(1440, 900);
    assert(layout.list_view.x >= layout.config_panel.x);
    assert(layout.list_view.y >= layout.config_panel.y);
    assert(layout.list_view.x + layout.list_view.width <=
           layout.config_panel.x + layout.config_panel.width + 0.01F);
    assert(layout.details_view.x >= layout.details_panel.x);
    assert(layout.start_button.x + layout.start_button.width <= 1440.0F);
    assert(layout.settings_button.x + layout.settings_button.width <= 1440.0F);
    assert(layout.search_field.y + layout.search_field.height <= layout.sort_button.y);
    assert(layout.sort_button.x + layout.sort_button.width <= layout.tag_button.x);
    assert(layout.tag_button.x + layout.tag_button.width <= layout.favorite_button.x);
    assert(layout.favorite_button.x + layout.favorite_button.width <=
           layout.config_panel.x + layout.config_panel.width + 0.01F);
    assert(layout.favorite_button.y + layout.favorite_button.height <= layout.list_view.y);
    assert(layout.list_view.y + layout.list_view.height <=
           layout.config_panel.y + layout.config_panel.height + 0.01F);
    assert(layout.details_panel.y + layout.details_panel.height < layout.command_preview.y);
    assert(layout.command_preview.x + layout.command_preview.width < layout.command_copy_button.x);
    assert(layout.command_copy_button.x + layout.command_copy_button.width < layout.close_button.x);
    assert(layout.close_button.x + layout.close_button.width < layout.start_button.x);
    assert(layout.command_preview.y == layout.command_copy_button.y);

    const LauncherLayout compact = make_launcher_layout(1024, 700);
    assert(compact.config_panel.x + compact.config_panel.width < compact.details_panel.x);
    assert(compact.favorite_button.x + compact.favorite_button.width <=
           compact.config_panel.x + compact.config_panel.width + 0.01F);
    assert(compact.list_view.height > 0.0F);
    assert(compact.command_preview.width >= 120.0F);
    assert(compact.details_panel.y + compact.details_panel.height < compact.command_preview.y);
    assert(compact.command_preview.x + compact.command_preview.width < compact.command_copy_button.x);
    assert(compact.command_copy_button.x + compact.command_copy_button.width < compact.close_button.x);
    assert(compact.close_button.x + compact.close_button.width < compact.start_button.x);

    const LauncherLayout minimum = make_launcher_layout(800, 600);
    assert(minimum.list_view.height > 0.0F);
    assert(minimum.details_panel.y + minimum.details_panel.height < minimum.command_preview.y);
    assert(minimum.command_preview.width >= 120.0F);
    assert(minimum.command_preview.x + minimum.command_preview.width < minimum.command_copy_button.x);
    assert(minimum.command_copy_button.x + minimum.command_copy_button.width < minimum.close_button.x);
    assert(minimum.close_button.x + minimum.close_button.width < minimum.start_button.x);

    std::string seed_error;
    const auto seeds = parse_seed_list("10001, 10002,10001,10003", seed_error);
    assert(seed_error.empty());
    assert((seeds == std::vector<std::int64_t>{10001, 10002, 10003}));
    const auto bad_seeds = parse_seed_list("10001,nope", seed_error);
    assert(bad_seeds.empty());
    assert(!seed_error.empty());

    std::string inspect_error;
    const auto scalars = inspect_scalar_config(source, inspect_error);
    assert(inspect_error.empty());
    bool saw_seed = false;
    bool saw_width = false;
    for (const auto& scalar : scalars) {
        saw_seed = saw_seed || scalar.path == "run.seed";
        saw_width = saw_width || scalar.path == "world.width";
    }
    assert(saw_seed && saw_width);

    std::ifstream original_input(source, std::ios::binary);
    const std::string original((std::istreambuf_iterator<char>(original_input)), {});

    const fs::path resolved = root / "runs/test/config_resolved.json";
    std::string merge_error;
    assert(create_resolved_config(
        source,
        resolved,
        {ConfigScalar{"world.width", "96", "number"},
         ConfigScalar{"run.enabled", "false", "bool"}},
        777,
        1500,
        merge_error
    ));
    assert(merge_error.empty());

    std::ifstream source_again(source, std::ios::binary);
    const std::string unchanged((std::istreambuf_iterator<char>(source_again)), {});
    assert(unchanged == original);

    std::ifstream resolved_input(resolved, std::ios::binary);
    const std::string resolved_text((std::istreambuf_iterator<char>(resolved_input)), {});
    assert(resolved_text.find("\"seed\": 777") != std::string::npos);
    assert(resolved_text.find("\"ticks\": 1500") != std::string::npos);
    assert(resolved_text.find("\"width\": 96") != std::string::npos);
    assert(resolved_text.find("\"enabled\": false") != std::string::npos);

    const fs::path saved = root / "configs/saved.json";
    assert(save_as_new_config(source, saved, {}, 888, 1600, merge_error));
    assert(fs::exists(saved));
    merge_error.clear();
    assert(!save_as_new_config(source, saved, {}, 999, 1700, merge_error));
    assert(!merge_error.empty());

    merge_error.clear();
    assert(!replace_original_config(source, {}, 999, 1700, false, merge_error));
    assert(!merge_error.empty());
    merge_error.clear();
    assert(replace_original_config(source, {}, 999, 1700, true, merge_error));
    std::ifstream replaced_input(source, std::ios::binary);
    const std::string replaced((std::istreambuf_iterator<char>(replaced_input)), {});
    assert(replaced.find("\"seed\": 999") != std::string::npos);

    LaunchRequest single;
    single.project_root = root;
    single.original_config_path = source;
    single.config_path = resolved;
    single.output_path = root / "runs/single";
    single.stream_path = single.output_path / "eco_live.bin";
    single.backend = "cpu";
    single.mode = ExperimentMode::SingleRun;
    single.seeds = {10001};
    single.until_tick = 1500;
    const std::string single_command = command_preview(single);
    assert(single_command.find("gui_interface.run_simulation") != std::string::npos);
    assert(single_command.find("--stream") != std::string::npos);

    LaunchRequest multi = single;
    multi.mode = ExperimentMode::MultiSeed;
    multi.backend = "gpu";
    multi.seeds = {10001, 10002, 10003};
    const std::string multi_command = command_preview(multi);
    assert(multi_command.find("subject_evolution.multi_seed") != std::string::npos);
    assert(multi_command.find("--seeds 10001,10002,10003") != std::string::npos);
    assert(multi_command.find("--until-tick 1500") != std::string::npos);

    single.history_id = "test-history";
    std::string history_error;
    assert(append_history(single, "started", -1, history_error));
    assert(append_history(single, "finished", 0, history_error));
    assert(fs::exists(root / "src/saves/experiment_history.json"));

    fs::remove_all(root, error);
    return 0;
}
