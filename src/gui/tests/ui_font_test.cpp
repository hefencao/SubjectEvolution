#include "eco/ui_font.hpp"

#include <cassert>
#include <filesystem>

int main() {
    const std::filesystem::path root = std::filesystem::temp_directory_path() /
        "eco_ui_font_v24_test";
    std::error_code error;
    std::filesystem::create_directories(root, error);
    eco::ui::set_font_metrics(18, 32, 1.1F);
    eco::ui::initialize_font(root, "auto");
    assert(eco::ui::body_font_size() == 18);
    assert(eco::ui::title_font_size() == 32);
    assert(!eco::ui::font_source().empty());
    assert(eco::ui::measure_text("monospace", 16) > 0);
    eco::ui::draw_text("test", 0, 0, 16, RAYWHITE);
    eco::ui::shutdown_font();
    std::filesystem::remove_all(root, error);
    return 0;
}
