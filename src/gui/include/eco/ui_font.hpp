#pragma once

#include <filesystem>
#include <string>

#include <raylib.h>

namespace eco::ui {

// Searches project-local references and common system locations for a
// sans-serif monospaced font. Font files are never bundled by this package.
bool initialize_font(
    const std::filesystem::path& project_root,
    const std::string& preferred_family = "auto"
);
bool reload_font(
    const std::filesystem::path& project_root,
    const std::string& preferred_family = "auto"
);
void shutdown_font();

void set_font_metrics(int body_font_size, int title_font_size, float ui_scale);
[[nodiscard]] int body_font_size();
[[nodiscard]] int title_font_size();
[[nodiscard]] float ui_scale();

[[nodiscard]] const std::string& font_source();
[[nodiscard]] const std::string& font_family();
[[nodiscard]] bool using_custom_font();

void draw_text(
    const char* text,
    int x,
    int y,
    int font_size,
    Color color
);

[[nodiscard]] int measure_text(const char* text, int font_size);

}  // namespace eco::ui
