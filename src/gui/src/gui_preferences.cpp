#include "eco/gui_preferences.hpp"

#include <algorithm>
#include <chrono>
#include <cctype>
#include <cmath>
#include <fstream>
#include <iomanip>
#include <optional>
#include <regex>
#include <sstream>
#include <system_error>

namespace eco::preferences {
namespace {

std::string read_text(const std::filesystem::path& path) {
    std::ifstream input(path, std::ios::binary);
    if (!input) return {};
    std::ostringstream out;
    out << input.rdbuf();
    return out.str();
}

std::string escape_json(const std::string& value) {
    std::string out;
    out.reserve(value.size() + 8U);
    for (const char c : value) {
        switch (c) {
        case '\\': out += "\\\\"; break;
        case '"': out += "\\\""; break;
        case '\n': out += "\\n"; break;
        case '\r': out += "\\r"; break;
        case '\t': out += "\\t"; break;
        default: out.push_back(c); break;
        }
    }
    return out;
}

std::optional<std::string> string_field(const std::string& text, const std::string& key) {
    const std::regex pattern("\\\"" + key + "\\\"\\s*:\\s*\\\"((?:\\\\.|[^\\\"])*)\\\"");
    std::smatch match;
    if (!std::regex_search(text, match, pattern)) return std::nullopt;
    std::string value = match[1].str();
    std::string decoded;
    decoded.reserve(value.size());
    bool escaped = false;
    for (const char c : value) {
        if (escaped) {
            switch (c) {
            case 'n': decoded.push_back('\n'); break;
            case 'r': decoded.push_back('\r'); break;
            case 't': decoded.push_back('\t'); break;
            default: decoded.push_back(c); break;
            }
            escaped = false;
        } else if (c == '\\') {
            escaped = true;
        } else {
            decoded.push_back(c);
        }
    }
    return decoded;
}

std::optional<double> number_field(const std::string& text, const std::string& key) {
    const std::regex pattern("\\\"" + key + "\\\"\\s*:\\s*(-?[0-9]+(?:\\.[0-9]+)?)");
    std::smatch match;
    if (!std::regex_search(text, match, pattern)) return std::nullopt;
    try { return std::stod(match[1].str()); } catch (...) { return std::nullopt; }
}

std::optional<bool> bool_field(const std::string& text, const std::string& key) {
    const std::regex pattern("\\\"" + key + "\\\"\\s*:\\s*(true|false)");
    std::smatch match;
    if (!std::regex_search(text, match, pattern)) return std::nullopt;
    return match[1].str() == "true";
}

std::vector<std::string> string_array_field(const std::string& text, const std::string& key) {
    std::vector<std::string> values;
    const std::regex array_pattern("\\\"" + key + "\\\"\\s*:\\s*\\[([^\\]]*)\\]");
    std::smatch array_match;
    if (!std::regex_search(text, array_match, array_pattern)) return values;
    const std::string body = array_match[1].str();
    const std::regex item_pattern("\\\"((?:\\\\.|[^\\\"])*)\\\"");
    for (std::sregex_iterator it(body.begin(), body.end(), item_pattern), end; it != end; ++it) {
        values.push_back((*it)[1].str());
    }
    return values;
}

std::string timestamp_suffix() {
    const auto now = std::chrono::system_clock::now().time_since_epoch();
    return std::to_string(std::chrono::duration_cast<std::chrono::milliseconds>(now).count());
}

void backup_corrupt(const std::filesystem::path& path) {
    std::error_code error;
    if (!std::filesystem::exists(path, error) || error) return;
    const auto backup = path.string() + ".corrupt." + timestamp_suffix();
    std::filesystem::rename(path, backup, error);
}

bool ensure_saves(const std::filesystem::path& project_root, std::string& error) {
    std::error_code fs_error;
    std::filesystem::create_directories(saves_directory(project_root), fs_error);
    if (fs_error) {
        error = "Could not create saves directory: " + fs_error.message();
        return false;
    }
    return true;
}

bool looks_like_json_object(const std::string& text) {
    const auto first = text.find_first_not_of(" \t\r\n");
    const auto last = text.find_last_not_of(" \t\r\n");
    return first != std::string::npos && last != std::string::npos &&
           text[first] == '{' && text[last] == '}';
}

std::string lower(std::string value) {
    std::transform(value.begin(), value.end(), value.begin(), [](unsigned char c) {
        return static_cast<char>(std::tolower(c));
    });
    return value;
}

std::uintmax_t safe_size(const std::filesystem::path& path) {
    std::error_code error;
    const auto size = std::filesystem::file_size(path, error);
    return error ? 0U : size;
}

std::filesystem::file_time_type safe_time(const std::filesystem::path& path) {
    std::error_code error;
    const auto value = std::filesystem::last_write_time(path, error);
    return error ? std::filesystem::file_time_type::min() : value;
}

}  // namespace

std::filesystem::path saves_directory(const std::filesystem::path& project_root) {
    return project_root / "src/saves";
}

std::filesystem::path settings_path(const std::filesystem::path& project_root) {
    return saves_directory(project_root) / "gui_settings.json";
}

std::filesystem::path state_path(const std::filesystem::path& project_root) {
    return saves_directory(project_root) / "gui_state.json";
}

std::filesystem::path history_path(const std::filesystem::path& project_root) {
    return saves_directory(project_root) / "experiment_history.json";
}

GuiSettings default_settings() {
    return GuiSettings{};
}

GuiSettings load_settings(const std::filesystem::path& project_root, std::string& warning) {
    GuiSettings settings = default_settings();
    const auto path = settings_path(project_root);
    std::error_code error;
    if (!std::filesystem::exists(path, error)) return settings;
    const std::string text = read_text(path);
    if (!looks_like_json_object(text)) {
        backup_corrupt(path);
        warning = "Invalid GUI settings were backed up; defaults restored.";
        return settings;
    }
    const auto width = number_field(text, "window_width");
    const auto height = number_field(text, "window_height");
    const auto body = number_field(text, "body_font_size");
    const auto title = number_field(text, "title_font_size");
    const auto row = number_field(text, "row_height");
    const auto recent = number_field(text, "recent_experiments");
    const auto scale = number_field(text, "ui_scale");
    const auto family = string_field(text, "font_family");
    if (!width || !height || !body || !title || !row || !recent || !scale || !family) {
        backup_corrupt(path);
        warning = "Incomplete GUI settings were backed up; defaults restored.";
        return settings;
    }
    settings.window_width = std::clamp(static_cast<int>(*width), 800, 7680);
    settings.window_height = std::clamp(static_cast<int>(*height), 600, 4320);
    settings.body_font_size = std::clamp(static_cast<int>(*body), 13, 24);
    settings.title_font_size = std::clamp(static_cast<int>(*title), 28, 38);
    settings.row_height = std::clamp(static_cast<int>(*row), 32, 52);
    settings.recent_experiments = std::clamp(static_cast<int>(*recent), 2, 20);
    settings.ui_scale = std::clamp(static_cast<float>(*scale), 0.85F, 1.50F);
    settings.font_family = family->empty() ? "auto" : *family;
    return settings;
}

bool save_settings(const std::filesystem::path& project_root, const GuiSettings& settings, std::string& error) {
    if (!ensure_saves(project_root, error)) return false;
    std::ofstream output(settings_path(project_root), std::ios::binary | std::ios::trunc);
    if (!output) { error = "Could not write GUI settings."; return false; }
    output << "{\n"
           << "  \"window_width\": " << std::clamp(settings.window_width, 800, 7680) << ",\n"
           << "  \"window_height\": " << std::clamp(settings.window_height, 600, 4320) << ",\n"
           << "  \"body_font_size\": " << std::clamp(settings.body_font_size, 13, 24) << ",\n"
           << "  \"title_font_size\": " << std::clamp(settings.title_font_size, 28, 38) << ",\n"
           << "  \"row_height\": " << std::clamp(settings.row_height, 32, 52) << ",\n"
           << "  \"recent_experiments\": " << std::clamp(settings.recent_experiments, 2, 20) << ",\n"
           << "  \"ui_scale\": " << std::fixed << std::setprecision(2)
           << std::clamp(settings.ui_scale, 0.85F, 1.50F) << ",\n"
           << "  \"font_family\": \"" << escape_json(settings.font_family) << "\"\n"
           << "}\n";
    return static_cast<bool>(output);
}

GuiState load_state(const std::filesystem::path& project_root, std::string& warning) {
    GuiState state;
    const auto path = state_path(project_root);
    std::error_code error;
    if (!std::filesystem::exists(path, error)) return state;
    const std::string text = read_text(path);
    if (!looks_like_json_object(text)) {
        backup_corrupt(path);
        warning = "Invalid GUI state was backed up; defaults restored.";
        return state;
    }
    const auto sort = string_field(text, "sort_mode");
    const auto search = string_field(text, "config_search");
    const auto tag = string_field(text, "tag_filter");
    const auto last = string_field(text, "last_config");
    const auto favorites_only = bool_field(text, "favorites_only");
    if (!sort || !search || !tag || !last || !favorites_only) {
        backup_corrupt(path);
        warning = "Incomplete GUI state was backed up; defaults restored.";
        return state;
    }
    if (*sort == "name-az") state.sort_mode = ConfigSortMode::NameAscending;
    else if (*sort == "name-za") state.sort_mode = ConfigSortMode::NameDescending;
    else if (*sort == "size") state.sort_mode = ConfigSortMode::Size;
    else state.sort_mode = ConfigSortMode::Latest;
    state.config_search = *search;
    state.tag_filter = tag->empty() ? "all" : *tag;
    state.last_config = *last;
    state.favorites_only = *favorites_only;
    for (const auto& favorite : string_array_field(text, "favorites")) state.favorites.insert(favorite);
    return state;
}

bool save_state(const std::filesystem::path& project_root, const GuiState& state, std::string& error) {
    if (!ensure_saves(project_root, error)) return false;
    std::ofstream output(state_path(project_root), std::ios::binary | std::ios::trunc);
    if (!output) { error = "Could not write GUI state."; return false; }
    std::string sort = "latest";
    if (state.sort_mode == ConfigSortMode::NameAscending) sort = "name-az";
    else if (state.sort_mode == ConfigSortMode::NameDescending) sort = "name-za";
    else if (state.sort_mode == ConfigSortMode::Size) sort = "size";
    output << "{\n"
           << "  \"sort_mode\": \"" << sort << "\",\n"
           << "  \"config_search\": \"" << escape_json(state.config_search) << "\",\n"
           << "  \"tag_filter\": \"" << escape_json(state.tag_filter) << "\",\n"
           << "  \"favorites_only\": " << (state.favorites_only ? "true" : "false") << ",\n"
           << "  \"last_config\": \"" << escape_json(state.last_config) << "\",\n"
           << "  \"favorites\": [";
    bool first = true;
    for (const auto& favorite : state.favorites) {
        if (!first) output << ", ";
        output << '"' << escape_json(favorite) << '"';
        first = false;
    }
    output << "]\n}\n";
    return static_cast<bool>(output);
}

bool migrate_legacy_history(const std::filesystem::path& project_root, std::string& message) {
    const auto destination = history_path(project_root);
    const auto source = project_root / "runs/.experiment_history.json";
    std::error_code error;
    if (std::filesystem::exists(destination, error)) return true;
    if (!std::filesystem::exists(source, error)) return true;
    std::string ensure_error;
    if (!ensure_saves(project_root, ensure_error)) { message = ensure_error; return false; }
    std::filesystem::copy_file(source, destination, std::filesystem::copy_options::none, error);
    if (error) { message = "Could not import legacy experiment history: " + error.message(); return false; }
    message = "Imported experiment history into saves/.";
    return true;
}

const char* sort_mode_name(ConfigSortMode mode) {
    switch (mode) {
    case ConfigSortMode::Latest: return "Latest";
    case ConfigSortMode::NameAscending: return "Name A-Z";
    case ConfigSortMode::NameDescending: return "Name Z-A";
    case ConfigSortMode::Size: return "Size";
    }
    return "Latest";
}

ConfigSortMode next_sort_mode(ConfigSortMode mode) {
    switch (mode) {
    case ConfigSortMode::Latest: return ConfigSortMode::NameAscending;
    case ConfigSortMode::NameAscending: return ConfigSortMode::NameDescending;
    case ConfigSortMode::NameDescending: return ConfigSortMode::Size;
    case ConfigSortMode::Size: return ConfigSortMode::Latest;
    }
    return ConfigSortMode::Latest;
}

void sort_configs(std::vector<std::filesystem::path>& configs, ConfigSortMode mode) {
    std::sort(configs.begin(), configs.end(), [mode](const auto& left, const auto& right) {
        if (mode == ConfigSortMode::Latest) {
            const auto lt = safe_time(left), rt = safe_time(right);
            if (lt != rt) return lt > rt;
        } else if (mode == ConfigSortMode::Size) {
            const auto ls = safe_size(left), rs = safe_size(right);
            if (ls != rs) return ls > rs;
        }
        const std::string a = lower(left.filename().string());
        const std::string b = lower(right.filename().string());
        if (mode == ConfigSortMode::NameDescending) return a == b ? left.string() > right.string() : a > b;
        return a == b ? left.string() < right.string() : a < b;
    });
}

std::string infer_config_tag(const std::filesystem::path& path) {
    const std::string name = lower(path.filename().string());
    if (name.find("smoke") != std::string::npos) return "smoke";
    if (name.find("long_run") != std::string::npos || name.find("longrun") != std::string::npos) return "long_run";
    if (name.find("latent") != std::string::npos) return "latent";
    if (name.find("mvp") != std::string::npos) return "mvp";
    return "other";
}

}  // namespace eco::preferences
