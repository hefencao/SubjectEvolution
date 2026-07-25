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
std::string g_family = "auto";
int g_body_font_size = 16;
int g_title_font_size = 31;
float g_ui_scale = 1.0F;

std::vector<std::filesystem::path> all_candidate_fonts(
    const std::filesystem::path& project_root
) {
    std::vector<std::filesystem::path> result;
    result.reserve(28);
    for (const char* relative : {
        "assets/fonts/DejaVuSansMono.ttf",
        "assets/fonts/NotoSansMono-Regular.ttf",
        "assets/fonts/LiberationMono-Regular.ttf",
        "src/gui/assets/fonts/DejaVuSansMono.ttf",
        "src/gui/assets/fonts/NotoSansMono-Regular.ttf",
        "src/gui/assets/fonts/LiberationMono-Regular.ttf",
    }) result.push_back(project_root / relative);
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

std::string lower(std::string value) {
    std::transform(value.begin(), value.end(), value.begin(), [](unsigned char c) {
        return static_cast<char>(std::tolower(c));
    });
    return value;
}

bool matches_family(const std::filesystem::path& path, const std::string& family) {
    const std::string value = lower(path.filename().string());
    const std::string requested = lower(family);
    if (requested.empty() || requested == "auto") return true;
    if (requested == "dejavu") return value.find("dejavu") != std::string::npos;
    if (requested == "noto") return value.find("noto") != std::string::npos;
    if (requested == "liberation") return value.find("liberation") != std::string::npos;
    if (requested == "consolas") return value.find("consol") != std::string::npos;
    if (requested == "system") return true;
    return value.find(requested) != std::string::npos;
}

std::vector<std::filesystem::path> candidate_fonts(
    const std::filesystem::path& project_root,
    const std::string& family
) {
    auto all = all_candidate_fonts(project_root);
    if (family.empty() || lower(family) == "auto") return all;
    std::stable_partition(all.begin(), all.end(), [&](const auto& path) {
        return matches_family(path, family);
    });
    return all;
}

float text_spacing(int font_size) {
    return std::max(0.0F, static_cast<float>(font_size) * 0.015F);
}

int effective_size(int requested) {
    const int base = requested >= 24 ? g_title_font_size : g_body_font_size;
    const int reference = requested >= 24 ? 30 : 14;
    const float semantic = static_cast<float>(requested) / static_cast<float>(reference);
    return std::max(8, static_cast<int>(std::lround(static_cast<float>(base) * semantic * g_ui_scale)));
}

}  // namespace

bool initialize_font(const std::filesystem::path& project_root, const std::string& preferred_family) {
    if (g_initialized) return g_custom;
    g_initialized = true;
    g_family = preferred_family.empty() ? "auto" : preferred_family;
    g_font = GetFontDefault();
    for (const auto& candidate : candidate_fonts(project_root, g_family)) {
        std::error_code error;
        if (!std::filesystem::is_regular_file(candidate, error) || error) continue;
        Font loaded = LoadFontEx(candidate.string().c_str(), 40, nullptr, 0);
        if (loaded.texture.id == 0U || loaded.glyphCount <= 0) {
            if (loaded.texture.id != 0U) UnloadFont(loaded);
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

bool reload_font(const std::filesystem::path& project_root, const std::string& preferred_family) {
    shutdown_font();
    return initialize_font(project_root, preferred_family);
}

void shutdown_font() {
    if (!g_initialized) return;
    if (g_custom) UnloadFont(g_font);
    g_font = Font{};
    g_initialized = false;
    g_custom = false;
    g_source = "raylib default";
    g_family = "auto";
}

void set_font_metrics(int body, int title, float scale) {
    g_body_font_size = std::clamp(body, 13, 24);
    g_title_font_size = std::clamp(title, 28, 38);
    g_ui_scale = std::clamp(scale, 0.85F, 1.50F);
}

int body_font_size() { return g_body_font_size; }
int title_font_size() { return g_title_font_size; }
float ui_scale() { return g_ui_scale; }
const std::string& font_source() { return g_source; }
const std::string& font_family() { return g_family; }
bool using_custom_font() { return g_custom; }

void draw_text(const char* text, int x, int y, int font_size, Color color) {
    if (!text) return;
    const int size = effective_size(font_size);
    DrawTextEx(g_font, text, Vector2{static_cast<float>(x), static_cast<float>(y)},
               static_cast<float>(size), text_spacing(size), color);
}

int measure_text(const char* text, int font_size) {
    if (!text) return 0;
    const int size = effective_size(font_size);
    return static_cast<int>(std::ceil(MeasureTextEx(g_font, text, static_cast<float>(size), text_spacing(size)).x));
}

}  // namespace eco::ui
