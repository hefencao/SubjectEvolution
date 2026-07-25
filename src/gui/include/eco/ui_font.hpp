#pragma once

#include <filesystem>
#include <string>

#include <raylib.h>

namespace eco::ui {

// Searches project-local references and common system locations for a
// sans-serif monospaced font. Font files are never bundled by this package.
bool initialize_font(const std::filesystem::path& project_root);
void shutdown_font();

[[nodiscard]] const std::string& font_source();
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
