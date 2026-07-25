#include "eco/ui_font.hpp"

#include <algorithm>
#include <array>
#include <cmath>
#include <cstdlib>
#include <system_error>
#include <vector>

namespace eco::ui {
namespace {

Font g_font{};
bool g_initialized = false;
bool g_custom = false;
std::string g_source = "raylib default";

std::vector<std::filesystem::path> candidate_fonts(
    const std::filesystem::path& project_root
) {
    std::vector<std::filesystem::path> result;
    result.reserve(24);

    // Project-local references are supported, but this patch intentionally
    // does not bundle or redistribute any font files.
    for (const char* relative : {
        "assets/fonts/DejaVuSansMono.ttf",
        "assets/fonts/NotoSansMono-Regular.ttf",
        "assets/fonts/LiberationMono-Regular.ttf",
        "src/gui/assets/fonts/DejaVuSansMono.ttf",
        "src/gui/assets/fonts/NotoSansMono-Regular.ttf",
        "src/gui/assets/fonts/LiberationMono-Regular.ttf",
    }) {
        result.push_back(project_root / relative);
    }

#if defined(_WIN32)
    const char* windows = std::getenv("WINDIR");
    const std::filesystem::path fonts = windows
        ? std::filesystem::path(windows) / "Fonts"
        : std::filesystem::path("C:/Windows/Fonts");
    result.push_back(fonts / "consola.ttf");
    result.push_back(fonts / "lucon.ttf");
    result.push_back(fonts / "cour.ttf");
#elif defined(__APPLE__)
    result.emplace_back("/System/Library/Fonts/SFNSMono.ttf");
    result.emplace_back("/System/Library/Fonts/Monaco.ttf");
    result.emplace_back("/Library/Fonts/DejaVuSansMono.ttf");
    result.emplace_back("/Library/Fonts/NotoSansMono-Regular.ttf");
    result.emplace_back("/Library/Fonts/LiberationMono-Regular.ttf");
#else
    result.emplace_back("/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf");
    result.emplace_back("/usr/share/fonts/truetype/noto/NotoSansMono-Regular.ttf");
    result.emplace_back("/usr/share/fonts/opentype/noto/NotoSansMono-Regular.ttf");
    result.emplace_back("/usr/share/fonts/truetype/liberation2/LiberationMono-Regular.ttf");
    result.emplace_back("/usr/share/fonts/truetype/liberation/LiberationMono-Regular.ttf");
    result.emplace_back("/usr/local/share/fonts/DejaVuSansMono.ttf");
#endif
    return result;
}

float text_spacing(int font_size) {
    return std::max(0.0F, static_cast<float>(font_size) * 0.015F);
}

}  // namespace

bool initialize_font(const std::filesystem::path& project_root) {
    if (g_initialized) {
        return g_custom;
    }
    g_initialized = true;
    g_font = GetFontDefault();

    for (const auto& candidate : candidate_fonts(project_root)) {
        std::error_code error;
        if (!std::filesystem::is_regular_file(candidate, error) || error) {
            continue;
        }
        Font loaded = LoadFontEx(candidate.string().c_str(), 32, nullptr, 0);
        if (loaded.texture.id == 0U || loaded.glyphCount <= 0) {
            if (loaded.texture.id != 0U) {
                UnloadFont(loaded);
            }
            continue;
        }
        g_font = loaded;
        g_custom = true;
        g_source = candidate.string();
        SetTextureFilter(g_font.texture, TEXTURE_FILTER_BILINEAR);
        return true;
    }
    return false;
}

void shutdown_font() {
    if (!g_initialized) {
        return;
    }
    if (g_custom) {
        UnloadFont(g_font);
    }
    g_font = Font{};
    g_initialized = false;
    g_custom = false;
    g_source = "raylib default";
}

const std::string& font_source() {
    return g_source;
}

bool using_custom_font() {
    return g_custom;
}

void draw_text(
    const char* text,
    int x,
    int y,
    int font_size,
    Color color
) {
    if (!text) {
        return;
    }
    DrawTextEx(
        g_font,
        text,
        Vector2{static_cast<float>(x), static_cast<float>(y)},
        static_cast<float>(font_size),
        text_spacing(font_size),
        color
    );
}

int measure_text(const char* text, int font_size) {
    if (!text) {
        return 0;
    }
    return static_cast<int>(std::ceil(MeasureTextEx(
        g_font,
        text,
        static_cast<float>(font_size),
        text_spacing(font_size)
    ).x));
}

}  // namespace eco::ui
