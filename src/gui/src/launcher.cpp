#include "eco/launcher.hpp"
#include "eco/ui_font.hpp"
#include "eco/gui_preferences.hpp"

#include <algorithm>
#include <array>
#include <charconv>
#include <chrono>
#include <cmath>
#include <cctype>
#include <cstdlib>
#include <fstream>
#include <iomanip>
#include <limits>
#include <map>
#include <optional>
#include <set>
#include <sstream>
#include <string_view>
#include <system_error>
#include <utility>
#include <variant>

namespace eco::launcher {
namespace {

using eco::ui::draw_text;
using eco::ui::measure_text;

bool g_launcher_input_blocked = false;
std::string g_launcher_tooltip;

struct JsonValue {
    using Object = std::vector<std::pair<std::string, JsonValue>>;
    using Array = std::vector<JsonValue>;
    using Storage = std::variant<std::nullptr_t, bool, double, std::string, Array, Object>;

    Storage value = nullptr;

    [[nodiscard]] bool is_object() const { return std::holds_alternative<Object>(value); }
    [[nodiscard]] bool is_array() const { return std::holds_alternative<Array>(value); }
    [[nodiscard]] bool is_string() const { return std::holds_alternative<std::string>(value); }
    [[nodiscard]] bool is_number() const { return std::holds_alternative<double>(value); }
    [[nodiscard]] bool is_bool() const { return std::holds_alternative<bool>(value); }
    [[nodiscard]] bool is_null() const { return std::holds_alternative<std::nullptr_t>(value); }

    Object& object() { return std::get<Object>(value); }
    const Object& object() const { return std::get<Object>(value); }
    Array& array() { return std::get<Array>(value); }
    const Array& array() const { return std::get<Array>(value); }
};

class JsonParser {
public:
    explicit JsonParser(std::string text) : text_(std::move(text)) {}

    std::optional<JsonValue> parse(std::string& error) {
        skip_ws();
        JsonValue result;
        if (!parse_value(result, error)) {
            return std::nullopt;
        }
        skip_ws();
        if (position_ != text_.size()) {
            error = "Unexpected trailing JSON data at byte " + std::to_string(position_);
            return std::nullopt;
        }
        return result;
    }

private:
    std::string text_;
    std::size_t position_ = 0;

    void skip_ws() {
        while (position_ < text_.size() &&
               std::isspace(static_cast<unsigned char>(text_[position_]))) {
            ++position_;
        }
    }

    bool parse_value(JsonValue& out, std::string& error) {
        skip_ws();
        if (position_ >= text_.size()) {
            error = "Unexpected end of JSON";
            return false;
        }
        const char c = text_[position_];
        if (c == '{') return parse_object(out, error);
        if (c == '[') return parse_array(out, error);
        if (c == '"') {
            std::string value;
            if (!parse_string(value, error)) return false;
            out.value = std::move(value);
            return true;
        }
        if (c == 't' && consume("true")) { out.value = true; return true; }
        if (c == 'f' && consume("false")) { out.value = false; return true; }
        if (c == 'n' && consume("null")) { out.value = nullptr; return true; }
        if (c == '-' || std::isdigit(static_cast<unsigned char>(c))) {
            return parse_number(out, error);
        }
        error = "Unexpected JSON token at byte " + std::to_string(position_);
        return false;
    }

    bool parse_object(JsonValue& out, std::string& error) {
        ++position_;
        JsonValue::Object object;
        skip_ws();
        if (position_ < text_.size() && text_[position_] == '}') {
            ++position_;
            out.value = std::move(object);
            return true;
        }
        while (position_ < text_.size()) {
            std::string key;
            if (!parse_string(key, error)) return false;
            skip_ws();
            if (position_ >= text_.size() || text_[position_] != ':') {
                error = "Expected ':' after object key";
                return false;
            }
            ++position_;
            JsonValue value;
            if (!parse_value(value, error)) return false;
            object.emplace_back(std::move(key), std::move(value));
            skip_ws();
            if (position_ < text_.size() && text_[position_] == '}') {
                ++position_;
                out.value = std::move(object);
                return true;
            }
            if (position_ >= text_.size() || text_[position_] != ',') {
                error = "Expected ',' or '}' in object";
                return false;
            }
            ++position_;
            skip_ws();
        }
        error = "Unterminated JSON object";
        return false;
    }

    bool parse_array(JsonValue& out, std::string& error) {
        ++position_;
        JsonValue::Array array;
        skip_ws();
        if (position_ < text_.size() && text_[position_] == ']') {
            ++position_;
            out.value = std::move(array);
            return true;
        }
        while (position_ < text_.size()) {
            JsonValue value;
            if (!parse_value(value, error)) return false;
            array.push_back(std::move(value));
            skip_ws();
            if (position_ < text_.size() && text_[position_] == ']') {
                ++position_;
                out.value = std::move(array);
                return true;
            }
            if (position_ >= text_.size() || text_[position_] != ',') {
                error = "Expected ',' or ']' in array";
                return false;
            }
            ++position_;
        }
        error = "Unterminated JSON array";
        return false;
    }

    bool parse_string(std::string& out, std::string& error) {
        skip_ws();
        if (position_ >= text_.size() || text_[position_] != '"') {
            error = "Expected JSON string";
            return false;
        }
        ++position_;
        out.clear();
        while (position_ < text_.size()) {
            char c = text_[position_++];
            if (c == '"') return true;
            if (c != '\\') {
                out.push_back(c);
                continue;
            }
            if (position_ >= text_.size()) {
                error = "Invalid JSON escape";
                return false;
            }
            const char escaped = text_[position_++];
            switch (escaped) {
            case '"': out.push_back('"'); break;
            case '\\': out.push_back('\\'); break;
            case '/': out.push_back('/'); break;
            case 'b': out.push_back('\b'); break;
            case 'f': out.push_back('\f'); break;
            case 'n': out.push_back('\n'); break;
            case 'r': out.push_back('\r'); break;
            case 't': out.push_back('\t'); break;
            case 'u': {
                if (position_ + 4U > text_.size()) {
                    error = "Short unicode escape";
                    return false;
                }
                unsigned int code = 0;
                for (int i = 0; i < 4; ++i) {
                    const char hex = text_[position_++];
                    code <<= 4U;
                    if (hex >= '0' && hex <= '9') code += static_cast<unsigned int>(hex - '0');
                    else if (hex >= 'a' && hex <= 'f') code += static_cast<unsigned int>(hex - 'a' + 10);
                    else if (hex >= 'A' && hex <= 'F') code += static_cast<unsigned int>(hex - 'A' + 10);
                    else {
                        error = "Invalid unicode escape";
                        return false;
                    }
                }
                if (code <= 0x7FU) out.push_back(static_cast<char>(code));
                else if (code <= 0x7FFU) {
                    out.push_back(static_cast<char>(0xC0U | (code >> 6U)));
                    out.push_back(static_cast<char>(0x80U | (code & 0x3FU)));
                } else {
                    out.push_back(static_cast<char>(0xE0U | (code >> 12U)));
                    out.push_back(static_cast<char>(0x80U | ((code >> 6U) & 0x3FU)));
                    out.push_back(static_cast<char>(0x80U | (code & 0x3FU)));
                }
                break;
            }
            default:
                error = "Unsupported JSON escape";
                return false;
            }
        }
        error = "Unterminated JSON string";
        return false;
    }

    bool parse_number(JsonValue& out, std::string& error) {
        const std::size_t begin = position_;
        if (text_[position_] == '-') ++position_;
        while (position_ < text_.size() &&
               std::isdigit(static_cast<unsigned char>(text_[position_]))) ++position_;
        if (position_ < text_.size() && text_[position_] == '.') {
            ++position_;
            while (position_ < text_.size() &&
                   std::isdigit(static_cast<unsigned char>(text_[position_]))) ++position_;
        }
        if (position_ < text_.size() &&
            (text_[position_] == 'e' || text_[position_] == 'E')) {
            ++position_;
            if (position_ < text_.size() &&
                (text_[position_] == '+' || text_[position_] == '-')) ++position_;
            while (position_ < text_.size() &&
                   std::isdigit(static_cast<unsigned char>(text_[position_]))) ++position_;
        }
        const std::string token = text_.substr(begin, position_ - begin);
        char* end = nullptr;
        const double number = std::strtod(token.c_str(), &end);
        if (!end || *end != '\0' || !std::isfinite(number)) {
            error = "Invalid JSON number: " + token;
            return false;
        }
        out.value = number;
        return true;
    }

    bool consume(std::string_view token) {
        if (text_.compare(position_, token.size(), token) != 0) return false;
        position_ += token.size();
        return true;
    }
};

std::string read_file(const std::filesystem::path& path, std::string& error) {
    std::ifstream input(path, std::ios::binary);
    if (!input) {
        error = "Could not open " + path.string();
        return {};
    }
    std::ostringstream buffer;
    buffer << input.rdbuf();
    return buffer.str();
}

std::optional<JsonValue> load_json(const std::filesystem::path& path, std::string& error) {
    const std::string text = read_file(path, error);
    if (!error.empty()) return std::nullopt;
    JsonParser parser(text);
    return parser.parse(error);
}

std::string escape_json(const std::string& text) {
    std::string out;
    out.reserve(text.size() + 8U);
    for (unsigned char c : text) {
        switch (c) {
        case '"': out += "\\\""; break;
        case '\\': out += "\\\\"; break;
        case '\b': out += "\\b"; break;
        case '\f': out += "\\f"; break;
        case '\n': out += "\\n"; break;
        case '\r': out += "\\r"; break;
        case '\t': out += "\\t"; break;
        default:
            if (c < 0x20U) {
                std::ostringstream code;
                code << "\\u" << std::hex << std::setw(4) << std::setfill('0')
                     << static_cast<int>(c);
                out += code.str();
            } else {
                out.push_back(static_cast<char>(c));
            }
        }
    }
    return out;
}

void write_json_value(std::ostream& out, const JsonValue& value, int indent, int depth) {
    const std::string pad(static_cast<std::size_t>(depth * indent), ' ');
    const std::string child_pad(static_cast<std::size_t>((depth + 1) * indent), ' ');
    if (value.is_null()) { out << "null"; return; }
    if (value.is_bool()) { out << (std::get<bool>(value.value) ? "true" : "false"); return; }
    if (value.is_number()) {
        const double number = std::get<double>(value.value);
        if (std::floor(number) == number &&
            std::abs(number) <= static_cast<double>(std::numeric_limits<std::int64_t>::max())) {
            out << static_cast<std::int64_t>(number);
        } else {
            out << std::setprecision(17) << number;
        }
        return;
    }
    if (value.is_string()) {
        out << '"' << escape_json(std::get<std::string>(value.value)) << '"';
        return;
    }
    if (value.is_array()) {
        const auto& array = value.array();
        out << '[';
        if (!array.empty()) {
            out << '\n';
            for (std::size_t i = 0; i < array.size(); ++i) {
                out << child_pad;
                write_json_value(out, array[i], indent, depth + 1);
                if (i + 1U < array.size()) out << ',';
                out << '\n';
            }
            out << pad;
        }
        out << ']';
        return;
    }
    const auto& object = value.object();
    out << '{';
    if (!object.empty()) {
        out << '\n';
        for (std::size_t i = 0; i < object.size(); ++i) {
            out << child_pad << '"' << escape_json(object[i].first) << "\": ";
            write_json_value(out, object[i].second, indent, depth + 1);
            if (i + 1U < object.size()) out << ',';
            out << '\n';
        }
        out << pad;
    }
    out << '}';
}

bool write_json_file(
    const std::filesystem::path& path,
    const JsonValue& root,
    std::string& error
) {
    std::error_code fs_error;
    if (!path.parent_path().empty()) {
        std::filesystem::create_directories(path.parent_path(), fs_error);
        if (fs_error) {
            error = "Could not create directory: " + fs_error.message();
            return false;
        }
    }
    std::ofstream output(path, std::ios::binary | std::ios::trunc);
    if (!output) {
        error = "Could not write " + path.string();
        return false;
    }
    write_json_value(output, root, 2, 0);
    output << '\n';
    if (!output) {
        error = "Writing failed for " + path.string();
        return false;
    }
    return true;
}

std::string scalar_type(const JsonValue& value) {
    if (value.is_bool()) return "bool";
    if (value.is_number()) return "number";
    if (value.is_string()) return "string";
    if (value.is_null()) return "null";
    return "container";
}

std::string scalar_text(const JsonValue& value) {
    if (value.is_bool()) return std::get<bool>(value.value) ? "true" : "false";
    if (value.is_number()) {
        const double number = std::get<double>(value.value);
        std::ostringstream out;
        if (std::floor(number) == number) out << static_cast<std::int64_t>(number);
        else out << std::setprecision(12) << number;
        return out.str();
    }
    if (value.is_string()) return std::get<std::string>(value.value);
    return "null";
}

void flatten_scalars(
    const JsonValue& value,
    const std::string& prefix,
    std::vector<ConfigScalar>& output
) {
    if (value.is_object()) {
        for (const auto& [key, child] : value.object()) {
            const std::string path = prefix.empty() ? key : prefix + "." + key;
            flatten_scalars(child, path, output);
        }
        return;
    }
    if (value.is_array()) {
        const auto& array = value.array();
        for (std::size_t index = 0; index < array.size(); ++index) {
            flatten_scalars(
                array[index],
                prefix + "[" + std::to_string(index) + "]",
                output
            );
        }
        return;
    }
    output.push_back(ConfigScalar{prefix, scalar_text(value), scalar_type(value)});
}

struct PathToken {
    std::string key;
    std::optional<std::size_t> index;
};

std::vector<PathToken> parse_path(const std::string& path, std::string& error) {
    std::vector<PathToken> tokens;
    std::size_t position = 0;
    while (position < path.size()) {
        PathToken token;
        const std::size_t key_begin = position;
        while (position < path.size() && path[position] != '.' && path[position] != '[') {
            ++position;
        }
        token.key = path.substr(key_begin, position - key_begin);
        if (token.key.empty() && tokens.empty()) {
            error = "Invalid empty JSON path component";
            return {};
        }
        if (position < path.size() && path[position] == '[') {
            ++position;
            const std::size_t index_begin = position;
            while (position < path.size() && std::isdigit(static_cast<unsigned char>(path[position]))) {
                ++position;
            }
            if (index_begin == position || position >= path.size() || path[position] != ']') {
                error = "Invalid array index in path " + path;
                return {};
            }
            std::size_t index = 0;
            const std::string text = path.substr(index_begin, position - index_begin);
            const auto [ptr, ec] = std::from_chars(text.data(), text.data() + text.size(), index);
            if (ec != std::errc{} || ptr != text.data() + text.size()) {
                error = "Invalid array index in path " + path;
                return {};
            }
            token.index = index;
            ++position;
        }
        tokens.push_back(std::move(token));
        if (position < path.size()) {
            if (path[position] != '.') {
                error = "Invalid JSON path " + path;
                return {};
            }
            ++position;
        }
    }
    return tokens;
}

JsonValue* find_object_value(JsonValue::Object& object, const std::string& key) {
    for (auto& [candidate, value] : object) {
        if (candidate == key) return &value;
    }
    return nullptr;
}


bool validate_scalar_text(
    const std::string& text,
    const std::string& type,
    std::string& error
) {
    if (type == "number") {
        char* end = nullptr;
        const double value = std::strtod(text.c_str(), &end);
        if (!end || *end != '\0' || !std::isfinite(value)) {
            error = "Number override is invalid.";
            return false;
        }
    } else if (type == "bool") {
        std::string lower = text;
        std::transform(lower.begin(), lower.end(), lower.begin(), [](unsigned char c) {
            return static_cast<char>(std::tolower(c));
        });
        if (lower != "true" && lower != "false" && lower != "1" && lower != "0" &&
            lower != "yes" && lower != "no" && lower != "on" && lower != "off") {
            error = "Boolean override must be true/false, 1/0, yes/no, or on/off.";
            return false;
        }
    } else if (type == "null" && text != "null") {
        error = "Null fields only accept the literal null.";
        return false;
    }
    return true;
}

JsonValue parse_scalar_value(const std::string& text, const std::string& type) {
    JsonValue result;
    if (type == "bool") {
        std::string lower = text;
        std::transform(lower.begin(), lower.end(), lower.begin(), [](unsigned char c) {
            return static_cast<char>(std::tolower(c));
        });
        result.value = lower == "true" || lower == "1" || lower == "yes" || lower == "on";
    } else if (type == "number") {
        char* end = nullptr;
        const double number = std::strtod(text.c_str(), &end);
        result.value = end && *end == '\0' && std::isfinite(number) ? number : 0.0;
    } else if (type == "null") {
        result.value = nullptr;
    } else {
        result.value = text;
    }
    return result;
}

bool set_path_value(
    JsonValue& root,
    const std::string& path,
    JsonValue value,
    bool create_objects,
    std::string& error
) {
    const auto tokens = parse_path(path, error);
    if (!error.empty() || tokens.empty()) return false;
    JsonValue* current = &root;
    for (std::size_t position = 0; position < tokens.size(); ++position) {
        const PathToken& token = tokens[position];
        const bool last = position + 1U == tokens.size();
        if (!current->is_object()) {
            if (!create_objects) {
                error = "Path parent is not an object: " + path;
                return false;
            }
            current->value = JsonValue::Object{};
        }
        JsonValue* child = find_object_value(current->object(), token.key);
        if (!child) {
            if (!create_objects) {
                error = "Path not found: " + path;
                return false;
            }
            current->object().emplace_back(token.key, JsonValue{});
            child = &current->object().back().second;
        }
        if (token.index.has_value()) {
            if (!child->is_array()) {
                if (!create_objects) {
                    error = "Path target is not an array: " + path;
                    return false;
                }
                child->value = JsonValue::Array{};
            }
            if (child->array().size() <= *token.index) {
                if (!create_objects) {
                    error = "Array index out of range: " + path;
                    return false;
                }
                child->array().resize(*token.index + 1U);
            }
            child = &child->array()[*token.index];
        }
        if (last) {
            *child = std::move(value);
            return true;
        }
        current = child;
    }
    return false;
}

std::optional<ConfigScalar> scalar_by_path(
    const std::vector<ConfigScalar>& scalars,
    const std::vector<std::string>& candidates
) {
    for (const std::string& candidate : candidates) {
        const auto found = std::find_if(scalars.begin(), scalars.end(), [&](const ConfigScalar& item) {
            return item.path == candidate;
        });
        if (found != scalars.end()) return *found;
    }
    return std::nullopt;
}

std::string timestamp_suffix() {
    const auto now = std::chrono::system_clock::now();
    const auto milliseconds = std::chrono::duration_cast<std::chrono::milliseconds>(
        now.time_since_epoch()
    ).count();
    return std::to_string(milliseconds);
}

std::string compact_bytes(std::uintmax_t bytes) {
    const double value = static_cast<double>(bytes);
    if (bytes >= 1024U * 1024U) {
        std::ostringstream out;
        out << std::fixed << std::setprecision(2) << value / (1024.0 * 1024.0) << " MiB";
        return out.str();
    }
    if (bytes >= 1024U) {
        std::ostringstream out;
        out << std::fixed << std::setprecision(1) << value / 1024.0 << " KiB";
        return out.str();
    }
    return std::to_string(bytes) + " B";
}

std::string elide_text(const std::string& text, int max_width, int font_size) {
    if (max_width <= 0 || measure_text(text.c_str(), font_size) <= max_width) return text;
    constexpr const char* ellipsis = "...";
    if (measure_text(ellipsis, font_size) >= max_width) return ellipsis;
    std::size_t left = text.size() / 2U;
    std::size_t right = left;
    while (left > 0U && right < text.size()) {
        const std::string candidate = text.substr(0, left) + ellipsis + text.substr(right);
        if (measure_text(candidate.c_str(), font_size) <= max_width) return candidate;
        if (left >= text.size() - right) --left;
        else ++right;
    }
    return ellipsis;
}

bool button(Rectangle rect, const std::string& label, bool enabled = true, bool active = false) {
    const Vector2 mouse = GetMousePosition();
    const bool hovered = !g_launcher_input_blocked && enabled && CheckCollisionPointRec(mouse, rect);
    DrawRectangleRec(
        rect,
        !enabled ? Color{36, 42, 48, 255}
                 : active ? Color{42, 91, 117, 255}
                          : hovered ? Color{55, 68, 80, 255} : Color{38, 47, 56, 255}
    );
    DrawRectangleLinesEx(rect, 1.0F, active ? Fade(SKYBLUE, 0.75F) : Fade(SKYBLUE, 0.20F));
    const int font_size = rect.height >= 40.0F ? 16 : 14;
    draw_text(
        elide_text(label, static_cast<int>(rect.width - 18.0F), font_size).c_str(),
        static_cast<int>(rect.x + 9.0F),
        static_cast<int>(rect.y + (rect.height - font_size) * 0.5F - 1.0F),
        font_size,
        enabled ? RAYWHITE : GRAY
    );
    return !g_launcher_input_blocked && enabled && hovered && IsMouseButtonPressed(MOUSE_BUTTON_LEFT);
}

bool filled_button(Rectangle rect, const std::string& label, bool active, bool enabled = true) {
    const Vector2 mouse = GetMousePosition();
    const bool hovered = !g_launcher_input_blocked && enabled && CheckCollisionPointRec(mouse, rect);
    const Color fill = !enabled ? Color{36, 42, 48, 255}
        : active ? Color{50, 126, 160, 255}
        : hovered ? Color{49, 61, 72, 255}
        : Color{32, 40, 48, 255};
    DrawRectangleRec(rect, fill);
    DrawRectangleLinesEx(rect, 1.0F, active ? Fade(SKYBLUE, 0.90F) : Fade(SKYBLUE, 0.18F));
    const int font_size = rect.height >= 36.0F ? 14 : 13;
    const std::string shown = elide_text(label, static_cast<int>(rect.width - 14.0F), font_size);
    const int text_width = measure_text(shown.c_str(), font_size);
    draw_text(
        shown.c_str(),
        static_cast<int>(rect.x + (rect.width - static_cast<float>(text_width)) * 0.5F),
        static_cast<int>(rect.y + (rect.height - static_cast<float>(font_size)) * 0.5F - 1.0F),
        font_size,
        enabled ? RAYWHITE : GRAY
    );
    return !g_launcher_input_blocked && enabled && hovered && IsMouseButtonPressed(MOUSE_BUTTON_LEFT);
}

enum class ActionIcon {
    NewFile,
    SaveFile,
    Refresh,
    Settings,
    Copy,
    Close,
    Run,
};

bool icon_button(
    Rectangle rect,
    ActionIcon icon,
    bool enabled = true,
    bool active = false,
    const char* tooltip = nullptr
) {
    const Vector2 mouse = GetMousePosition();
    const bool hovered = !g_launcher_input_blocked && enabled && CheckCollisionPointRec(mouse, rect);
    if (hovered && tooltip != nullptr) g_launcher_tooltip = tooltip;
    DrawRectangleRec(
        rect,
        !enabled ? Color{36, 42, 48, 255}
                 : active ? Color{78, 67, 30, 255}
                          : hovered ? Color{55, 68, 80, 255} : Color{38, 47, 56, 255}
    );
    DrawRectangleLinesEx(rect, 1.0F, active ? Fade(ORANGE, 0.85F) : Fade(SKYBLUE, 0.30F));
    const Color stroke = enabled ? RAYWHITE : GRAY;
    const float cx = rect.x + rect.width * 0.5F;
    const float cy = rect.y + rect.height * 0.5F;
    if (icon == ActionIcon::NewFile) {
        DrawLine(static_cast<int>(cx - 6.0F), static_cast<int>(cy),
                 static_cast<int>(cx + 6.0F), static_cast<int>(cy), stroke);
        DrawLine(static_cast<int>(cx), static_cast<int>(cy - 6.0F),
                 static_cast<int>(cx), static_cast<int>(cy + 6.0F), stroke);
    } else if (icon == ActionIcon::SaveFile) {
        Rectangle disk{cx - 7.0F, cy - 8.0F, 14.0F, 16.0F};
        DrawRectangleLinesEx(disk, 1.0F, stroke);
        DrawRectangleLinesEx(Rectangle{disk.x + 3.0F, disk.y + 2.0F, 8.0F, 5.0F}, 1.0F, stroke);
        DrawRectangleLinesEx(Rectangle{disk.x + 3.0F, disk.y + 10.0F, 8.0F, 4.0F}, 1.0F, stroke);
    } else if (icon == ActionIcon::Refresh) {
        DrawCircleLines(static_cast<int>(cx), static_cast<int>(cy), 7.0F, stroke);
        DrawLine(static_cast<int>(cx + 5.0F), static_cast<int>(cy - 6.0F),
                 static_cast<int>(cx + 9.0F), static_cast<int>(cy - 6.0F), stroke);
        DrawLine(static_cast<int>(cx + 9.0F), static_cast<int>(cy - 6.0F),
                 static_cast<int>(cx + 8.0F), static_cast<int>(cy - 2.0F), stroke);
    } else if (icon == ActionIcon::Settings) {
        DrawCircleLines(static_cast<int>(cx), static_cast<int>(cy), 5.0F, stroke);
        DrawCircleLines(static_cast<int>(cx), static_cast<int>(cy), 2.0F, stroke);
        for (int dx : {-8, 8}) {
            DrawLine(static_cast<int>(cx + dx), static_cast<int>(cy - 2.0F),
                     static_cast<int>(cx + dx), static_cast<int>(cy + 2.0F), stroke);
        }
        for (int dy : {-8, 8}) {
            DrawLine(static_cast<int>(cx - 2.0F), static_cast<int>(cy + dy),
                     static_cast<int>(cx + 2.0F), static_cast<int>(cy + dy), stroke);
        }
    } else if (icon == ActionIcon::Copy) {
        DrawRectangleLinesEx(Rectangle{cx - 7.0F, cy - 7.0F, 11.0F, 13.0F}, 1.0F, stroke);
        DrawRectangleLinesEx(Rectangle{cx - 3.0F, cy - 3.0F, 11.0F, 13.0F}, 1.0F, stroke);
    } else if (icon == ActionIcon::Close) {
        DrawLine(static_cast<int>(cx - 6.0F), static_cast<int>(cy - 6.0F),
                 static_cast<int>(cx + 6.0F), static_cast<int>(cy + 6.0F), stroke);
        DrawLine(static_cast<int>(cx + 6.0F), static_cast<int>(cy - 6.0F),
                 static_cast<int>(cx - 6.0F), static_cast<int>(cy + 6.0F), stroke);
    } else if (icon == ActionIcon::Run) {
        DrawTriangle(
            Vector2{cx - 5.0F, cy - 8.0F},
            Vector2{cx - 5.0F, cy + 8.0F},
            Vector2{cx + 8.0F, cy},
            stroke
        );
    }
    return !g_launcher_input_blocked && enabled && hovered && IsMouseButtonPressed(MOUSE_BUTTON_LEFT);
}

void draw_launcher_tooltip() {
    if (g_launcher_tooltip.empty()) return;
    const Vector2 mouse = GetMousePosition();
    const int font_size = 11;
    const float padding = 7.0F;
    const float width = static_cast<float>(measure_text(g_launcher_tooltip.c_str(), font_size)) + padding * 2.0F;
    const float height = 25.0F;
    const float x = std::clamp(mouse.x + 12.0F, 4.0F, static_cast<float>(GetScreenWidth()) - width - 4.0F);
    const float y = std::clamp(mouse.y + 14.0F, 4.0F, static_cast<float>(GetScreenHeight()) - height - 4.0F);
    DrawRectangleRec(Rectangle{x, y, width, height}, Color{8, 12, 16, 242});
    DrawRectangleLinesEx(Rectangle{x, y, width, height}, 1.0F, Fade(SKYBLUE, 0.45F));
    draw_text(g_launcher_tooltip.c_str(), static_cast<int>(x + padding), static_cast<int>(y + 6.0F), font_size, LIGHTGRAY);
}

void draw_star_icon(Rectangle rect, bool selected, Color color) {
    constexpr float pi = 3.14159265358979323846F;
    const Vector2 center{rect.x + rect.width * 0.5F, rect.y + rect.height * 0.5F};
    const float outer = std::min(rect.width, rect.height) * 0.34F;
    const float inner = outer * 0.44F;
    std::array<Vector2, 10> points{};
    for (std::size_t index = 0; index < points.size(); ++index) {
        const float angle = -pi * 0.5F + static_cast<float>(index) * pi / 5.0F;
        const float radius = index % 2U == 0U ? outer : inner;
        points[index] = Vector2{
            center.x + std::cos(angle) * radius,
            center.y + std::sin(angle) * radius,
        };
    }
    if (selected) {
        for (std::size_t index = 0; index < points.size(); ++index) {
            DrawTriangle(center, points[index], points[(index + 1U) % points.size()], color);
        }
    } else {
        for (std::size_t index = 0; index < points.size(); ++index) {
            DrawLineEx(points[index], points[(index + 1U) % points.size()], 1.2F, color);
        }
    }
}

struct TextEditState {
    std::string active;
};

void edit_active_text(const std::string& id, std::string& value, TextEditState& state) {
    if (state.active != id) return;
    int character = GetCharPressed();
    while (character > 0) {
        if (character >= 32 && character <= 0x10FFFF && value.size() < 4096U) {
            if (character < 128) value.push_back(static_cast<char>(character));
        }
        character = GetCharPressed();
    }
    if (IsKeyPressed(KEY_BACKSPACE) && !value.empty()) value.pop_back();
}

bool text_field(
    const std::string& id,
    Rectangle rect,
    std::string& value,
    TextEditState& state,
    const std::string& placeholder = {}
) {
    const Vector2 mouse = GetMousePosition();
    const bool hovered = !g_launcher_input_blocked && CheckCollisionPointRec(mouse, rect);
    const bool clicked = hovered && IsMouseButtonPressed(MOUSE_BUTTON_LEFT);
    if (clicked) state.active = id;
    const bool active = state.active == id;
    edit_active_text(id, value, state);
    DrawRectangleRec(rect, active ? Color{17, 31, 40, 255} : Color{13, 20, 27, 255});
    DrawRectangleLinesEx(rect, 1.0F, active ? SKYBLUE : Fade(SKYBLUE, hovered ? 0.45F : 0.18F));
    const std::string shown = value.empty() ? placeholder : value;
    draw_text(
        elide_text(shown, static_cast<int>(rect.width - 16.0F), 14).c_str(),
        static_cast<int>(rect.x + 8.0F),
        static_cast<int>(rect.y + 8.0F),
        14,
        value.empty() ? DARKGRAY : LIGHTGRAY
    );
    if (active && static_cast<int>(GetTime() * 2.0) % 2 == 0) {
        const int cursor_x = static_cast<int>(rect.x + 8.0F) +
            std::min(measure_text(value.c_str(), 14), static_cast<int>(rect.width - 20.0F));
        DrawLine(cursor_x, static_cast<int>(rect.y + 7.0F), cursor_x, static_cast<int>(rect.y + rect.height - 7.0F), SKYBLUE);
    }
    return clicked;
}

std::filesystem::path resolve_output_template(
    const std::filesystem::path& project_root,
    const std::string& text,
    const std::string& config_stem
) {
    std::string expanded = text;
    const auto replace_all = [&](const std::string& needle, const std::string& replacement) {
        std::size_t position = 0;
        while ((position = expanded.find(needle, position)) != std::string::npos) {
            expanded.replace(position, needle.size(), replacement);
            position += replacement.size();
        }
    };
    replace_all("<config>", config_stem);
    replace_all("<timestamp>", timestamp_suffix());
    std::filesystem::path output(expanded);
    if (output.is_relative()) output = project_root / output;
    return std::filesystem::absolute(output);
}

std::string join_seeds(const std::vector<std::int64_t>& seeds) {
    std::ostringstream out;
    for (std::size_t i = 0; i < seeds.size(); ++i) {
        if (i) out << ',';
        out << seeds[i];
    }
    return out.str();
}

std::string mode_short(ExperimentMode mode) {
    return mode == ExperimentMode::SingleRun ? "single" : "multi-seed";
}

struct HistoryLine {
    std::string text;
};

std::vector<HistoryLine> recent_history(const std::filesystem::path& project_root, std::size_t limit) {
    std::vector<HistoryLine> lines;
    std::string error;
    auto root = load_json(eco::preferences::history_path(project_root), error);
    if (!root || !root->is_array()) return lines;
    const auto& array = root->array();
    for (auto it = array.rbegin(); it != array.rend() && lines.size() < limit; ++it) {
        if (!it->is_object()) continue;
        std::map<std::string, std::string> fields;
        for (const auto& [key, value] : it->object()) {
            if (!value.is_object() && !value.is_array()) fields[key] = scalar_text(value);
        }
        const std::string config = fields.count("config") ? fields["config"] : "?";
        const std::string mode = fields.count("mode") ? fields["mode"] : "?";
        const std::string backend = fields.count("backend") ? fields["backend"] : "?";
        const std::string status = fields.count("status") ? fields["status"] : "?";
        lines.push_back({config + "  " + mode + "/" + backend + "  " + status});
    }
    return lines;
}

bool write_override_manifest(
    const LaunchRequest& request,
    const std::vector<ConfigScalar>& overrides,
    std::optional<std::int64_t> single_seed,
    std::optional<std::uint64_t> until_tick,
    std::string& error
) {
    JsonValue root;
    root.value = JsonValue::Object{};
    root.object().push_back({"source_config", JsonValue{request.original_config_path.string()}});
    root.object().push_back({"mode", JsonValue{std::string(experiment_mode_name(request.mode))}});
    root.object().push_back({"backend", JsonValue{request.backend}});
    root.object().push_back({"resolution", JsonValue{request.resolution.label}});
    if (single_seed.has_value()) root.object().push_back({"seed", JsonValue{static_cast<double>(*single_seed)}});
    if (until_tick.has_value()) root.object().push_back({"until_tick", JsonValue{static_cast<double>(*until_tick)}});
    JsonValue items;
    items.value = JsonValue::Array{};
    for (const ConfigScalar& item : overrides) {
        JsonValue entry;
        entry.value = JsonValue::Object{};
        entry.object().push_back({"path", JsonValue{item.path}});
        entry.object().push_back({"value", JsonValue{item.value}});
        entry.object().push_back({"type", JsonValue{item.type}});
        items.array().push_back(std::move(entry));
    }
    root.object().push_back({"overrides", std::move(items)});
    return write_json_file(request.output_path / "config_runtime_override.json", root, error);
}

struct LauncherState {
    std::size_t selected = 0;
    std::size_t config_scroll = 0;
    float detail_scroll = 0.0F;
    ExperimentMode mode = ExperimentMode::SingleRun;
    std::size_t backend = 0;
    std::string seed_text = "10001";
    std::string seeds_text = "10001,10002,10003";
    std::string tick_text = "1500";
    std::string output_text;
    bool overwrite_partial = false;
    bool extended_open = false;
    bool settings_open = false;
    std::string search;
    std::string scalar_search;
    std::size_t extended_scroll = 0;
    std::size_t selected_scalar = 0;
    Rectangle extended_list_rect{};
    bool has_extended_list_rect = false;
    std::string scalar_edit;
    std::map<std::string, ConfigScalar> overrides;
    std::string save_as_name;
    bool replace_armed = false;
    TextEditState text_edit;
};

std::vector<ResolutionChoice> resolution_choices() {
    return {
        {1280, 720, "1280x720", false},
        {1600, 900, "1600x900", false},
        {1920, 1080, "1920x1080", false},
        {2560, 1440, "2560x1440", false},
        {1440, 900, "custom", true},
    };
}

std::vector<ConfigScalar> current_override_vector(const LauncherState& state) {
    std::vector<ConfigScalar> result;
    result.reserve(state.overrides.size());
    for (const auto& [path, item] : state.overrides) {
        (void)path;
        result.push_back(item);
    }
    return result;
}

std::optional<std::int64_t> parse_single_seed(const std::string& text, std::string& error) {
    try {
        std::size_t used = 0;
        const long long value = std::stoll(text, &used, 10);
        if (used != text.size()) throw std::invalid_argument("trailing");
        return static_cast<std::int64_t>(value);
    } catch (...) {
        error = "Seed must be an integer.";
        return std::nullopt;
    }
}

std::optional<std::uint64_t> parse_tick(const std::string& text, std::string& error) {
    try {
        std::size_t used = 0;
        const unsigned long long value = std::stoull(text, &used, 10);
        if (used != text.size() || value == 0ULL) throw std::invalid_argument("invalid");
        return static_cast<std::uint64_t>(value);
    } catch (...) {
        error = "Until tick must be a positive integer.";
        return std::nullopt;
    }
}

std::vector<std::size_t> filtered_scalar_indices(
    const std::vector<ConfigScalar>& scalars,
    const LauncherState& state
) {
    std::string search = state.scalar_search;
    std::transform(search.begin(), search.end(), search.begin(), [](unsigned char c) {
        return static_cast<char>(std::tolower(c));
    });
    std::vector<std::size_t> result;
    for (std::size_t i = 0; i < scalars.size(); ++i) {
        if (scalars[i].path == "run.seed" || scalars[i].path == "seed" ||
            scalars[i].path == "run.ticks" || scalars[i].path == "ticks") {
            continue;
        }
        std::string path = scalars[i].path;
        std::transform(path.begin(), path.end(), path.begin(), [](unsigned char c) {
            return static_cast<char>(std::tolower(c));
        });
        if (search.empty() || path.find(search) != std::string::npos) result.push_back(i);
    }
    return result;
}

void reset_config_state(
    LauncherState& state,
    const std::filesystem::path& selected_path,
    const std::vector<ConfigScalar>& scalars
) {
    state.overrides.clear();
    state.extended_scroll = 0;
    state.selected_scalar = 0;
    state.scalar_edit.clear();
    state.replace_armed = false;
    state.save_as_name = selected_path.stem().string() + "_modified.json";
    if (const auto seed = scalar_by_path(scalars, {"run.seed", "seed"}); seed.has_value()) {
        state.seed_text = seed->value;
        try {
            const long long base = std::stoll(seed->value);
            state.seeds_text = std::to_string(base) + "," + std::to_string(base + 1) + "," + std::to_string(base + 2);
        } catch (...) {}
    }
    if (const auto ticks = scalar_by_path(scalars, {"run.ticks", "ticks"}); ticks.has_value()) {
        state.tick_text = ticks->value;
    }
    const std::string stem = selected_path.stem().string();
    state.output_text = state.mode == ExperimentMode::SingleRun
        ? "runs/gui_" + stem + "_<timestamp>"
        : "runs/multi_" + stem + "_<timestamp>";
}

LaunchRequest request_template(
    const std::filesystem::path& project_root,
    const std::filesystem::path& selected_path,
    const std::string& python,
    const LauncherState& state,
    const std::array<std::string, 3>& backends,
    const ResolutionChoice& resolution
) {
    LaunchRequest request;
    request.project_root = project_root;
    request.original_config_path = selected_path;
    request.config_path = project_root / "runs/<output>/config_resolved.json";
    request.python = python;
    request.backend = backends[state.backend];
    request.mode = state.mode;
    request.resolution = resolution;
    request.until_tick = 0;
    try { request.until_tick = std::stoull(state.tick_text); } catch (...) {}
    std::string seed_error;
    if (state.mode == ExperimentMode::MultiSeed) {
        request.seeds = parse_seed_list(state.seeds_text, seed_error);
    } else {
        if (auto seed = parse_single_seed(state.seed_text, seed_error); seed.has_value()) {
            request.seeds = {*seed};
        }
    }
    const std::string stem = selected_path.empty() ? "<config>" : selected_path.stem().string();
    request.output_path = state.output_text.empty()
        ? project_root / "runs/<output>"
        : std::filesystem::path(state.output_text);
    request.stream_path = request.output_path / "eco_live.bin";
    request.overwrite_partial = state.overwrite_partial;
    request.command = command_preview(request, true);
    (void)stem;
    return request;
}

}  // namespace

const char* experiment_mode_name(ExperimentMode mode) {
    return mode == ExperimentMode::SingleRun ? "single" : "multi-seed";
}

ConfigScanResult find_configs(const std::filesystem::path& config_dir) {
    ConfigScanResult result;
    std::error_code error;
    if (!std::filesystem::is_directory(config_dir, error)) {
        result.error = "Configuration directory is not available: " + config_dir.string();
        return result;
    }
    std::filesystem::directory_iterator iterator(
        config_dir,
        std::filesystem::directory_options::skip_permission_denied,
        error
    );
    if (error) {
        result.error = "Could not read configuration directory: " + error.message();
        return result;
    }
    for (const auto& entry : iterator) {
        std::error_code entry_error;
        if (!entry_error && entry.is_regular_file(entry_error) && entry.path().extension() == ".json") {
            result.configs.push_back(std::filesystem::absolute(entry.path()));
        }
    }
    eco::preferences::sort_configs(result.configs, eco::preferences::ConfigSortMode::Latest);
    return result;
}

ConfigFileStatus inspect_config_file(const std::filesystem::path& path) {
    ConfigFileStatus status;
    std::error_code error;
    if (!std::filesystem::is_regular_file(path, error)) {
        status.message = "The selected file no longer exists or is not regular.";
        return status;
    }
    status.size_bytes = std::filesystem::file_size(path, error);
    if (error) { status.message = "The selected file size could not be read."; return status; }
    if (status.size_bytes == 0U) { status.message = "The selected JSON file is empty."; return status; }
    std::string parse_error;
    auto root = load_json(path, parse_error);
    if (!root) { status.message = "JSON parse failed: " + parse_error; return status; }
    if (!root->is_object()) { status.message = "The configuration root must be a JSON object."; return status; }
    status.launchable = true;
    status.message = "Valid JSON configuration.";
    return status;
}

LauncherLayout make_launcher_layout(int width, int height) {
    const float margin = std::clamp(width * 0.025F, 24.0F, 42.0F);
    const float header_bottom = 118.0F;
    const float footer_height = 126.0F;
    const float gap = 18.0F;
    const float content_height = std::max(330.0F, static_cast<float>(height) - header_bottom - footer_height);
    const float available = static_cast<float>(width) - margin * 2.0F - gap;
    const float left = std::clamp(available * 0.38F, 390.0F, 620.0F);
    LauncherLayout layout;
    layout.config_panel = {margin, header_bottom, left, content_height};
    layout.search_field = {margin + 12.0F, header_bottom + 50.0F, left - 24.0F, 32.0F};
    const float filter_gap = 6.0F;
    const float filter_width = (layout.search_field.width - filter_gap * 2.0F) / 3.0F;
    layout.sort_button = {layout.search_field.x, layout.search_field.y + 40.0F, filter_width, 30.0F};
    layout.tag_button = {layout.sort_button.x + filter_width + filter_gap, layout.sort_button.y, filter_width, 30.0F};
    layout.favorite_button = {layout.tag_button.x + filter_width + filter_gap, layout.tag_button.y, filter_width, 30.0F};
    layout.list_view = {
        margin + 12.0F,
        layout.favorite_button.y + layout.favorite_button.height + 12.0F,
        left - 24.0F,
        content_height - (layout.favorite_button.y + layout.favorite_button.height + 26.0F - header_bottom)
    };
    layout.details_panel = {margin + left + gap, header_bottom, available - left, content_height};
    layout.details_view = {layout.details_panel.x + 10.0F, layout.details_panel.y + 10.0F, layout.details_panel.width - 20.0F, layout.details_panel.height - 20.0F};
    layout.settings_button = {static_cast<float>(width) - margin - 40.0F, 43.0F, 40.0F, 40.0F};
    layout.refresh_button = {layout.config_panel.x + layout.config_panel.width - 46.0F, layout.config_panel.y + 10.0F, 32.0F, 32.0F};
    const float action_y = static_cast<float>(height) - 70.0F;
    layout.start_button = {static_cast<float>(width) - margin - 50.0F, action_y, 50.0F, 50.0F};
    layout.close_button = {layout.start_button.x - 58.0F, action_y, 50.0F, 50.0F};
    layout.command_copy_button = {layout.close_button.x - 48.0F, action_y + 7.0F, 36.0F, 36.0F};
    layout.command_preview = {
        layout.details_panel.x,
        action_y + 7.0F,
        std::max(120.0F, layout.command_copy_button.x - layout.details_panel.x - 10.0F),
        36.0F
    };
    return layout;
}

std::size_t clamp_launcher_scroll(
    std::size_t selected,
    std::size_t item_count,
    std::size_t visible_rows,
    std::size_t scroll_start
) {
    if (item_count == 0U || visible_rows == 0U) return 0U;
    selected = std::min(selected, item_count - 1U);
    visible_rows = std::min(visible_rows, item_count);
    if (selected < scroll_start) scroll_start = selected;
    else if (selected >= scroll_start + visible_rows) scroll_start = selected - visible_rows + 1U;
    return std::min(scroll_start, item_count - visible_rows);
}

std::vector<std::int64_t> parse_seed_list(const std::string& text, std::string& error) {
    std::vector<std::int64_t> seeds;
    std::set<std::int64_t> seen;
    std::istringstream input(text);
    std::string token;
    while (std::getline(input, token, ',')) {
        token.erase(std::remove_if(token.begin(), token.end(), [](unsigned char c) {
            return std::isspace(c);
        }), token.end());
        if (token.empty()) continue;
        try {
            std::size_t used = 0;
            const long long value = std::stoll(token, &used, 10);
            if (used != token.size()) throw std::invalid_argument("trailing");
            if (seen.insert(value).second) seeds.push_back(static_cast<std::int64_t>(value));
        } catch (...) {
            error = "Seeds must be comma-separated integers.";
            return {};
        }
    }
    if (seeds.empty()) error = "At least one seed is required.";
    return seeds;
}

std::vector<ConfigScalar> inspect_scalar_config(
    const std::filesystem::path& config,
    std::string& error
) {
    auto root = load_json(config, error);
    if (!root) return {};
    std::vector<ConfigScalar> scalars;
    flatten_scalars(*root, "", scalars);
    return scalars;
}

bool create_resolved_config(
    const std::filesystem::path& source,
    const std::filesystem::path& destination,
    const std::vector<ConfigScalar>& overrides,
    std::optional<std::int64_t> single_seed,
    std::optional<std::uint64_t> until_tick,
    std::string& error
) {
    auto root = load_json(source, error);
    if (!root) return false;
    for (const ConfigScalar& override_item : overrides) {
        if (!validate_scalar_text(override_item.value, override_item.type, error)) {
            error = override_item.path + ": " + error;
            return false;
        }
        JsonValue value = parse_scalar_value(override_item.value, override_item.type);
        if (!set_path_value(*root, override_item.path, std::move(value), false, error)) return false;
    }
    if (single_seed.has_value()) {
        std::string local_error;
        if (!set_path_value(*root, "run.seed", JsonValue{static_cast<double>(*single_seed)}, false, local_error)) {
            local_error.clear();
            if (!set_path_value(*root, "seed", JsonValue{static_cast<double>(*single_seed)}, false, local_error)) {
                local_error.clear();
                if (!set_path_value(*root, "run.seed", JsonValue{static_cast<double>(*single_seed)}, true, local_error)) {
                    error = local_error;
                    return false;
                }
            }
        }
    }
    if (until_tick.has_value()) {
        std::string local_error;
        if (!set_path_value(*root, "run.ticks", JsonValue{static_cast<double>(*until_tick)}, false, local_error)) {
            local_error.clear();
            if (!set_path_value(*root, "ticks", JsonValue{static_cast<double>(*until_tick)}, false, local_error)) {
                local_error.clear();
                if (!set_path_value(*root, "run.ticks", JsonValue{static_cast<double>(*until_tick)}, true, local_error)) {
                    error = local_error;
                    return false;
                }
            }
        }
    }
    return write_json_file(destination, *root, error);
}

bool save_as_new_config(
    const std::filesystem::path& source,
    const std::filesystem::path& destination,
    const std::vector<ConfigScalar>& overrides,
    std::optional<std::int64_t> single_seed,
    std::optional<std::uint64_t> until_tick,
    std::string& error
) {
    std::error_code fs_error;
    if (std::filesystem::exists(destination, fs_error)) {
        error = "Save-as destination already exists.";
        return false;
    }
    return create_resolved_config(source, destination, overrides, single_seed, until_tick, error);
}

bool replace_original_config(
    const std::filesystem::path& source,
    const std::vector<ConfigScalar>& overrides,
    std::optional<std::int64_t> single_seed,
    std::optional<std::uint64_t> until_tick,
    bool confirmed,
    std::string& error
) {
    if (!confirmed) {
        error = "Replacing the original configuration requires confirmation.";
        return false;
    }
    const std::filesystem::path temporary = source.string() + ".eco_tmp";
    if (!create_resolved_config(source, temporary, overrides, single_seed, until_tick, error)) return false;
    std::error_code fs_error;
    std::filesystem::copy_file(
        temporary,
        source,
        std::filesystem::copy_options::overwrite_existing,
        fs_error
    );
    std::error_code cleanup_error;
    std::filesystem::remove(temporary, cleanup_error);
    if (fs_error) {
        error = "Could not replace original configuration: " + fs_error.message();
        return false;
    }
    return true;
}

std::string command_preview(const LaunchRequest& request, bool template_paths) {
    const std::string config = request.config_path.string();
    const std::string output = request.output_path.string();
    std::ostringstream command;
    command << request.python << " -m ";
    if (request.mode == ExperimentMode::MultiSeed) {
        command << "subject_evolution.multi_seed"
                << " --config \"" << config << "\""
                << " --seeds " << join_seeds(request.seeds)
                << " --output \"" << output << "\""
                << " --backend " << request.backend;
        if (request.until_tick > 0U) command << " --until-tick " << request.until_tick;
        if (request.overwrite_partial) command << " --overwrite-partial";
    } else {
        command << "subject_evolution.gui_interface.run_simulation"
                << " --config \"" << config << "\""
                << " --output \"" << output << "\""
                << " --stream \"" << request.stream_path.string() << "\""
                << " --backend " << request.backend;
    }
    (void)template_paths;
    return command.str();
}

bool prepare_launch_request(LaunchRequest& request, std::string& error) {
    std::error_code fs_error;
    std::filesystem::create_directories(request.output_path, fs_error);
    if (fs_error) {
        error = "Could not create output directory: " + fs_error.message();
        return false;
    }
    const std::filesystem::path original_copy = request.output_path / "config_original.json";
    std::filesystem::copy_file(
        request.original_config_path,
        original_copy,
        std::filesystem::copy_options::overwrite_existing,
        fs_error
    );
    if (fs_error) {
        error = "Could not copy original configuration: " + fs_error.message();
        return false;
    }
    request.config_path = request.output_path / "config_resolved.json";
    request.stream_path = request.output_path / "eco_live.bin";
    request.command = command_preview(request, false);
    request.history_id = timestamp_suffix();
    return true;
}

bool append_history(
    const LaunchRequest& request,
    const std::string& status,
    int exit_code,
    std::string& error
) {
    const std::filesystem::path path = eco::preferences::history_path(request.project_root);
    std::error_code directory_error;
    std::filesystem::create_directories(path.parent_path(), directory_error);
    if (directory_error) { error = "Could not create saves directory: " + directory_error.message(); return false; }
    JsonValue root;
    std::string load_error;
    auto existing = load_json(path, load_error);
    if (existing && existing->is_array()) root = std::move(*existing);
    else root.value = JsonValue::Array{};
    JsonValue record;
    record.value = JsonValue::Object{};
    record.object().push_back({"id", JsonValue{request.history_id}});
    record.object().push_back({"timestamp", JsonValue{timestamp_suffix()}});
    record.object().push_back({"config", JsonValue{request.original_config_path.filename().string()}});
    record.object().push_back({"mode", JsonValue{std::string(experiment_mode_name(request.mode))}});
    record.object().push_back({"backend", JsonValue{request.backend}});
    record.object().push_back({"seeds", JsonValue{join_seeds(request.seeds)}});
    record.object().push_back({"until_tick", JsonValue{static_cast<double>(request.until_tick)}});
    record.object().push_back({"output", JsonValue{request.output_path.string()}});
    record.object().push_back({"status", JsonValue{status}});
    record.object().push_back({"exit_code", JsonValue{static_cast<double>(exit_code)}});
    root.array().push_back(std::move(record));
    if (root.array().size() > 200U) {
        root.array().erase(root.array().begin(), root.array().begin() + static_cast<std::ptrdiff_t>(root.array().size() - 200U));
    }
    return write_json_file(path, root, error);
}

std::optional<LaunchRequest> show_launcher(
    const std::filesystem::path& project_root,
    const std::filesystem::path& config_dir,
    const std::string& python
) {
    std::string preference_warning;
    eco::preferences::migrate_legacy_history(project_root, preference_warning);
    eco::preferences::GuiSettings settings = eco::preferences::load_settings(project_root, preference_warning);
    eco::preferences::GuiSettings draft_settings = settings;
    std::string state_warning;
    eco::preferences::GuiState persistent = eco::preferences::load_state(project_root, state_warning);

    eco::ui::set_font_metrics(settings.body_font_size, settings.title_font_size, settings.ui_scale);
    eco::ui::reload_font(project_root, settings.font_family);
    SetWindowSize(settings.window_width, settings.window_height);

    ConfigScanResult scan = find_configs(config_dir);
    std::vector<std::filesystem::path> configs = std::move(scan.configs);
    eco::preferences::sort_configs(configs, persistent.sort_mode);
    const std::array<std::string, 3> backends{"cpu", "gpu", "auto"};
    const std::vector<ResolutionChoice> resolutions = resolution_choices();

    LauncherState state;
    state.search = persistent.config_search;
    std::string settings_width_text = std::to_string(draft_settings.window_width);
    std::string settings_height_text = std::to_string(draft_settings.window_height);
    std::size_t settings_resolution = resolutions.size() - 1U;
    for (std::size_t index = 0; index < resolutions.size(); ++index) {
        if (!resolutions[index].custom &&
            resolutions[index].width == settings.window_width &&
            resolutions[index].height == settings.window_height) {
            settings_resolution = index;
            break;
        }
    }
    std::size_t settings_scale = 1;
    const std::array<float, 6> scales{0.90F, 1.00F, 1.10F, 1.20F, 1.30F, 1.40F};
    for (std::size_t index = 0; index < scales.size(); ++index) {
        if (std::abs(scales[index] - settings.ui_scale) < 0.02F) settings_scale = index;
    }
    const std::array<int, 7> body_sizes{14, 15, 16, 17, 18, 20, 22};
    const std::array<int, 5> title_sizes{30, 31, 32, 33, 34};
    const std::array<int, 5> row_heights{34, 38, 42, 46, 50};
    const std::array<int, 5> recent_counts{4, 6, 8, 10, 12};
    const std::array<std::string, 5> font_families{"auto", "dejavu", "noto", "liberation", "consolas"};
    auto nearest_index = [](auto value, const auto& choices) {
        std::size_t best = 0;
        auto distance = std::abs(static_cast<double>(value) - static_cast<double>(choices[0]));
        for (std::size_t index = 1; index < choices.size(); ++index) {
            const auto candidate = std::abs(static_cast<double>(value) - static_cast<double>(choices[index]));
            if (candidate < distance) { distance = candidate; best = index; }
        }
        return best;
    };
    std::size_t settings_body = nearest_index(settings.body_font_size, body_sizes);
    std::size_t settings_title = nearest_index(settings.title_font_size, title_sizes);
    std::size_t settings_row = nearest_index(settings.row_height, row_heights);
    std::size_t settings_recent = nearest_index(settings.recent_experiments, recent_counts);
    std::size_t settings_font = 0;
    for (std::size_t index = 0; index < font_families.size(); ++index) {
        if (font_families[index] == settings.font_family) settings_font = index;
    }

    std::vector<ConfigScalar> scalars;
    std::filesystem::path loaded_config;
    std::filesystem::path selected_path;
    std::string message = !preference_warning.empty() ? preference_warning : state_warning;
    if (message.empty()) message = scan.error.empty()
        ? "Temporary overrides run immediately; source JSON remains unchanged."
        : scan.error;
    Color message_color = scan.error.empty() ? GRAY : ORANGE;
    bool state_dirty = false;

    auto lower = [](std::string value) {
        std::transform(value.begin(), value.end(), value.begin(), [](unsigned char c) {
            return static_cast<char>(std::tolower(c));
        });
        return value;
    };
    auto visible_configs = [&]() {
        std::vector<std::filesystem::path> result;
        const std::string needle = lower(state.search);
        for (const auto& config : configs) {
            const std::string filename = config.filename().string();
            if (!needle.empty() && lower(filename).find(needle) == std::string::npos) continue;
            if (persistent.tag_filter != "all" &&
                eco::preferences::infer_config_tag(config) != persistent.tag_filter) continue;
            if (persistent.favorites_only && !persistent.favorites.contains(filename)) continue;
            result.push_back(config);
        }
        return result;
    };
    auto preserve_selection = [&](const std::string& filename) {
        auto visible = visible_configs();
        state.selected = 0;
        for (std::size_t index = 0; index < visible.size(); ++index) {
            if (visible[index].filename() == filename) { state.selected = index; break; }
        }
        state.config_scroll = clamp_launcher_scroll(state.selected, visible.size(), 1U, state.config_scroll);
    };
    auto refresh = [&]() {
        const std::string keep = selected_path.empty() ? persistent.last_config : selected_path.filename().string();
        ConfigScanResult refreshed = find_configs(config_dir);
        configs = std::move(refreshed.configs);
        eco::preferences::sort_configs(configs, persistent.sort_mode);
        scan.error = refreshed.error;
        preserve_selection(keep);
        loaded_config.clear();
    };
    auto reload_selected = [&]() {
        auto visible = visible_configs();
        if (visible.empty()) {
            selected_path.clear();
            scalars.clear();
            return;
        }
        state.selected = std::min(state.selected, visible.size() - 1U);
        const auto path = visible[state.selected];
        if (path == loaded_config) { selected_path = path; return; }
        selected_path = path;
        loaded_config = path;
        std::string error;
        scalars = inspect_scalar_config(path, error);
        reset_config_state(state, path, scalars);
        persistent.last_config = path.filename().string();
        state_dirty = true;
        if (!error.empty()) { message = error; message_color = ORANGE; }
    };
    if (!persistent.last_config.empty()) preserve_selection(persistent.last_config);
    reload_selected();

    auto relative_time = [](const std::filesystem::path& path) {
        std::error_code error;
        const auto modified = std::filesystem::last_write_time(path, error);
        if (error) return std::string("?");
        const auto age = std::filesystem::file_time_type::clock::now() - modified;
        const auto minutes = std::chrono::duration_cast<std::chrono::minutes>(age).count();
        if (minutes < 1) return std::string("now");
        if (minutes < 60) return std::to_string(minutes) + "m";
        const auto hours = minutes / 60;
        if (hours < 24) return std::to_string(hours) + "h";
        return std::to_string(hours / 24) + "d";
    };
    auto save_persistent_state = [&]() {
        persistent.config_search = state.search;
        if (!selected_path.empty()) persistent.last_config = selected_path.filename().string();
        std::string error;
        if (!eco::preferences::save_state(project_root, persistent, error)) {
            message = error;
            message_color = ORANGE;
        }
        state_dirty = false;
    };
    auto active_resolution = [&]() {
        ResolutionChoice choice;
        choice.width = settings.window_width;
        choice.height = settings.window_height;
        choice.label = std::to_string(choice.width) + "x" + std::to_string(choice.height);
        choice.custom = true;
        return choice;
    };
    auto update_draft_from_controls = [&]() -> bool {
        draft_settings.ui_scale = scales[settings_scale];
        draft_settings.body_font_size = body_sizes[settings_body];
        draft_settings.title_font_size = title_sizes[settings_title];
        draft_settings.row_height = row_heights[settings_row];
        draft_settings.recent_experiments = recent_counts[settings_recent];
        draft_settings.font_family = font_families[settings_font];
        try {
            if (resolutions[settings_resolution].custom) {
                draft_settings.window_width = std::stoi(settings_width_text);
                draft_settings.window_height = std::stoi(settings_height_text);
            } else {
                draft_settings.window_width = resolutions[settings_resolution].width;
                draft_settings.window_height = resolutions[settings_resolution].height;
                settings_width_text = std::to_string(draft_settings.window_width);
                settings_height_text = std::to_string(draft_settings.window_height);
            }
        } catch (...) {
            message = "Resolution width and height must be integers.";
            message_color = ORANGE;
            return false;
        }
        if (draft_settings.window_width < 800 || draft_settings.window_width > 7680 ||
            draft_settings.window_height < 600 || draft_settings.window_height > 4320) {
            message = "Resolution must be within 800x600 and 7680x4320.";
            message_color = ORANGE;
            return false;
        }
        return true;
    };
    auto apply_settings = [&]() {
        if (!update_draft_from_controls()) return false;
        settings = draft_settings;
        SetWindowSize(settings.window_width, settings.window_height);
        eco::ui::set_font_metrics(settings.body_font_size, settings.title_font_size, settings.ui_scale);
        eco::ui::reload_font(project_root, settings.font_family);
        message = "GUI settings applied. Font: " + eco::ui::font_source();
        message_color = Color{103, 225, 151, 255};
        return true;
    };

    while (!WindowShouldClose()) {
        auto visible = visible_configs();
        if (!visible.empty()) {
            state.selected = std::min(state.selected, visible.size() - 1U);
        } else state.selected = 0;

        if (!state.settings_open && state.text_edit.active.empty()) {
            if (IsKeyPressed(KEY_UP) && state.selected > 0U) { --state.selected; loaded_config.clear(); }
            if (IsKeyPressed(KEY_DOWN) && state.selected + 1U < visible.size()) { ++state.selected; loaded_config.clear(); }
            const std::size_t page = 10U;
            if (IsKeyPressed(KEY_PAGE_UP)) { state.selected = state.selected > page ? state.selected - page : 0U; loaded_config.clear(); }
            if (IsKeyPressed(KEY_PAGE_DOWN) && !visible.empty()) { state.selected = std::min(visible.size() - 1U, state.selected + page); loaded_config.clear(); }
            if (IsKeyPressed(KEY_HOME)) { state.selected = 0U; loaded_config.clear(); }
            if (IsKeyPressed(KEY_END) && !visible.empty()) { state.selected = visible.size() - 1U; loaded_config.clear(); }
            if (IsKeyPressed(KEY_R)) refresh();
            if (IsKeyPressed(KEY_G)) state.settings_open = true;
            if (IsKeyPressed(KEY_ESCAPE)) {
                if (state_dirty) save_persistent_state();
                return std::nullopt;
            }
        }
        reload_selected();
        const ConfigFileStatus status = selected_path.empty() ? ConfigFileStatus{} : inspect_config_file(selected_path);
        const LauncherLayout layout = make_launcher_layout(GetScreenWidth(), GetScreenHeight());
        const int row_height = settings.row_height;
        const std::size_t visible_rows = std::max<std::size_t>(1U, static_cast<std::size_t>(layout.list_view.height / static_cast<float>(row_height)));
        state.config_scroll = clamp_launcher_scroll(state.selected, visible.size(), visible_rows, state.config_scroll);

        const Vector2 mouse = GetMousePosition();
        const float wheel = GetMouseWheelMove();
        if (!state.settings_open && wheel != 0.0F) {
            if (CheckCollisionPointRec(mouse, layout.list_view) && !visible.empty()) {
                const int delta = wheel > 0.0F ? -3 : 3;
                const int next = std::clamp(static_cast<int>(state.selected) + delta, 0, static_cast<int>(visible.size() - 1U));
                state.selected = static_cast<std::size_t>(next);
                loaded_config.clear();
            } else if (CheckCollisionPointRec(mouse, layout.details_view)) {
                state.detail_scroll = std::max(0.0F, state.detail_scroll - wheel * 42.0F);
            }
        }

        const std::string config_name = selected_path.empty() ? "no-config" : selected_path.filename().string();
        const std::string window_title = "Subject Evolution Launcher — " + config_name + " [" +
            mode_short(state.mode) + "/" + backends[state.backend] + "]";
        SetWindowTitle(window_title.c_str());
        g_launcher_input_blocked = state.settings_open;
        g_launcher_tooltip.clear();

        BeginDrawing();
        ClearBackground(Color{13, 17, 22, 255});
        draw_text("Subject Evolution", 42, 48, 30, RAYWHITE);
        draw_text("Simulation-first experiment launcher", 42, 92, 16, LIGHTGRAY);
        if (icon_button(layout.settings_button, ActionIcon::Settings, true, state.settings_open, "Settings [G]")) {
            state.settings_open = !state.settings_open;
        }

        DrawRectangleLinesEx(layout.config_panel, 1.0F, Fade(SKYBLUE, 0.28F));
        DrawRectangleLinesEx(layout.details_panel, 1.0F, Fade(SKYBLUE, 0.28F));
        draw_text(TextFormat("Configurations  %d", static_cast<int>(visible.size())),
                  static_cast<int>(layout.config_panel.x + 14.0F),
                  static_cast<int>(layout.config_panel.y + 16.0F), 14, LIGHTGRAY);
        if (icon_button(layout.refresh_button, ActionIcon::Refresh, true, false, "Refresh configurations [R]")) refresh();

        if (text_field("config_search", layout.search_field, state.search, state.text_edit, "Search configurations...")) state_dirty = true;
        persistent.config_search = state.search;
        if (button(layout.sort_button, std::string("Sort: ") + eco::preferences::sort_mode_name(persistent.sort_mode))) {
            persistent.sort_mode = eco::preferences::next_sort_mode(persistent.sort_mode);
            eco::preferences::sort_configs(configs, persistent.sort_mode);
            preserve_selection(config_name);
            loaded_config.clear(); state_dirty = true;
        }
        const std::array<std::string, 6> tags{"all", "mvp", "smoke", "long_run", "latent", "other"};
        if (button(layout.tag_button, "Tag: " + persistent.tag_filter)) {
            auto found = std::find(tags.begin(), tags.end(), persistent.tag_filter);
            std::size_t index = found == tags.end() ? 0U : static_cast<std::size_t>(std::distance(tags.begin(), found));
            persistent.tag_filter = tags[(index + 1U) % tags.size()];
            preserve_selection(config_name); loaded_config.clear(); state_dirty = true;
        }
        if (button(layout.favorite_button, persistent.favorites_only ? "Favorites: on" : "Favorites", true, persistent.favorites_only)) {
            persistent.favorites_only = !persistent.favorites_only;
            preserve_selection(config_name); loaded_config.clear(); state_dirty = true;
        }

        BeginScissorMode(static_cast<int>(layout.list_view.x), static_cast<int>(layout.list_view.y),
                         static_cast<int>(layout.list_view.width), static_cast<int>(layout.list_view.height));
        for (std::size_t row = 0; row < visible_rows; ++row) {
            const std::size_t index = state.config_scroll + row;
            if (index >= visible.size()) break;
            const Rectangle row_rect{layout.list_view.x,
                                     layout.list_view.y + static_cast<float>(row * row_height),
                                     layout.list_view.width,
                                     static_cast<float>(row_height - 2)};
            const bool selected = index == state.selected;
            const bool hovered = CheckCollisionPointRec(mouse, row_rect);
            if (selected || hovered) DrawRectangleRec(row_rect, selected ? Color{48, 98, 124, 255} : Color{28, 38, 46, 255});
            Rectangle star_rect{row_rect.x + 5.0F, row_rect.y + 4.0F, 26.0F, row_rect.height - 8.0F};
            const std::string filename = visible[index].filename().string();
            const bool favorite = persistent.favorites.contains(filename);
            draw_star_icon(star_rect, favorite, favorite ? GOLD : GRAY);
            const int age_width = 42;
            draw_text(elide_text(filename, static_cast<int>(row_rect.width - 88.0F), 13).c_str(),
                      static_cast<int>(row_rect.x + 36.0F), static_cast<int>(row_rect.y + 8.0F), 13, LIGHTGRAY);
            const std::string age = relative_time(visible[index]);
            draw_text(age.c_str(), static_cast<int>(row_rect.x + row_rect.width - age_width),
                      static_cast<int>(row_rect.y + 8.0F), 11, GRAY);
            if (!state.settings_open && IsMouseButtonPressed(MOUSE_BUTTON_LEFT)) {
                if (CheckCollisionPointRec(mouse, star_rect)) {
                    if (favorite) persistent.favorites.erase(filename); else persistent.favorites.insert(filename);
                    state_dirty = true;
                } else if (CheckCollisionPointRec(mouse, row_rect)) {
                    state.selected = index; loaded_config.clear(); state_dirty = true;
                }
            }
        }
        EndScissorMode();

        bool new_config_clicked = false;
        bool save_config_clicked = false;
        BeginScissorMode(static_cast<int>(layout.details_view.x), static_cast<int>(layout.details_view.y),
                         static_cast<int>(layout.details_view.width), static_cast<int>(layout.details_view.height));
        int x = static_cast<int>(layout.details_view.x + 8.0F);
        int y = static_cast<int>(layout.details_view.y + 8.0F - state.detail_scroll);
        const int width = static_cast<int>(layout.details_view.width - 16.0F);
        auto section = [&](const std::string& title) {
            draw_text(title.c_str(), x, y, 15, Color{122, 211, 255, 255});
            y += 31;
        };
        auto label = [&](const std::string& title) {
            draw_text(title.c_str(), x, y + 8, 12, GRAY);
            Rectangle rect{static_cast<float>(x + 104), static_cast<float>(y), static_cast<float>(width - 104), 32.0F};
            y += 42;
            return rect;
        };

        section("Experiment");
        draw_text(elide_text(config_name, width, 14).c_str(), x, y, 14, LIGHTGRAY);
        if (!selected_path.empty()) {
            draw_text(elide_text(selected_path.string(), width, 11).c_str(), x, y + 26, 11, GRAY);
            draw_text((compact_bytes(status.size_bytes) + "  |  " + status.message).c_str(), x, y + 46, 11,
                      status.launchable ? Color{103, 225, 151, 255} : ORANGE);
        }
        y += 72;

        const float file_action_size = 32.0F;
        const float file_action_gap = 6.0F;
        Rectangle save_icon{
            static_cast<float>(x + width) - file_action_size,
            static_cast<float>(y),
            file_action_size,
            file_action_size
        };
        Rectangle new_icon{
            save_icon.x - file_action_gap - file_action_size,
            save_icon.y,
            file_action_size,
            file_action_size
        };
        Rectangle name_rect{
            static_cast<float>(x),
            static_cast<float>(y),
            new_icon.x - static_cast<float>(x) - file_action_gap,
            32.0F
        };
        text_field("save_name", name_rect, state.save_as_name, state.text_edit, "new_config.json");
        new_config_clicked = icon_button(
            new_icon, ActionIcon::NewFile, status.launchable, false, "Create a new config from current edits"
        );
        save_config_clicked = icon_button(
            save_icon, ActionIcon::SaveFile, status.launchable, state.replace_armed,
            state.replace_armed ? "Confirm permanent overwrite" : "Permanently save selected config"
        );
        y += 41;
        draw_text(
            state.replace_armed
                ? "Permanent overwrite armed; click Save again to confirm."
                : "New creates another JSON; Save replaces the selected JSON after confirmation.",
            x, y, 10, state.replace_armed ? ORANGE : Color{145, 187, 205, 255}
        );
        y += 27;

        const float control_height = 32.0F;
        const float control_gap = 6.0F;
        Rectangle single_rect{static_cast<float>(x), static_cast<float>(y), 88.0F, control_height};
        Rectangle multi_rect{single_rect.x + single_rect.width + control_gap, single_rect.y, 108.0F, control_height};
        const float backend_width = 66.0F;
        const float backend_total = backend_width * 3.0F + control_gap * 2.0F;
        const bool stacked_profile_controls = static_cast<float>(width) < 430.0F;
        const float backend_x = stacked_profile_controls
            ? static_cast<float>(x)
            : static_cast<float>(x + width) - backend_total;
        const float backend_y = stacked_profile_controls
            ? static_cast<float>(y) + control_height + control_gap
            : static_cast<float>(y);
        Rectangle cpu_rect{backend_x, static_cast<float>(y), backend_width, control_height};
        cpu_rect.y = backend_y;
        Rectangle gpu_rect{cpu_rect.x + backend_width + control_gap, backend_y, backend_width, control_height};
        Rectangle auto_rect{gpu_rect.x + backend_width + control_gap, backend_y, backend_width, control_height};
        if (filled_button(single_rect, "Single", state.mode == ExperimentMode::SingleRun)) {
            state.mode = ExperimentMode::SingleRun;
            if (!selected_path.empty()) reset_config_state(state, selected_path, scalars);
        }
        if (filled_button(multi_rect, "Multi Seed", state.mode == ExperimentMode::MultiSeed)) {
            state.mode = ExperimentMode::MultiSeed;
            if (!selected_path.empty()) reset_config_state(state, selected_path, scalars);
        }
        if (filled_button(cpu_rect, "CPU", state.backend == 0U)) state.backend = 0U;
        if (filled_button(gpu_rect, "GPU", state.backend == 1U)) state.backend = 1U;
        if (filled_button(auto_rect, "AUTO", state.backend == 2U)) state.backend = 2U;
        y += stacked_profile_controls ? 86 : 48;

        section("Basic overrides");
        Rectangle seed_rect = label(state.mode == ExperimentMode::SingleRun ? "Seed" : "Seeds");
        if (state.mode == ExperimentMode::SingleRun) text_field("seed", seed_rect, state.seed_text, state.text_edit, "10001");
        else text_field("seeds", seed_rect, state.seeds_text, state.text_edit, "10001,10002,10003");
        Rectangle tick_rect = label("Until tick");
        text_field("tick", tick_rect, state.tick_text, state.text_edit, "1500");
        Rectangle output_rect = label("Output");
        text_field("output", output_rect, state.output_text, state.text_edit, "runs/...");
        if (state.mode == ExperimentMode::MultiSeed) {
            Rectangle overwrite_rect{static_cast<float>(x + 104), static_cast<float>(y), 240.0F, 30.0F};
            if (button(overwrite_rect, state.overwrite_partial ? "overwrite partial runs: on" : "overwrite partial runs: off", true, state.overwrite_partial)) {
                state.overwrite_partial = !state.overwrite_partial;
            }
            y += 40;
        }
        draw_text("Temporary overrides apply only to this run; the source JSON stays unchanged.",
                  x, y, 10, Color{145, 187, 205, 255});
        y += 27;

        Rectangle extended_header{static_cast<float>(x), static_cast<float>(y), static_cast<float>(width), 34.0F};
        if (button(extended_header, state.extended_open ? "Extended overrides [-]" : "Extended overrides [+]", true, state.extended_open)) {
            state.extended_open = !state.extended_open;
        }
        y += 42;
        if (state.extended_open) {
            Rectangle filter_rect{static_cast<float>(x), static_cast<float>(y), static_cast<float>(width), 32.0F};
            text_field("scalar_search", filter_rect, state.scalar_search, state.text_edit, "Search scalar paths...");
            y += 40;
            const auto filtered = filtered_scalar_indices(scalars, state);
            const std::size_t rows = std::min<std::size_t>(7U, filtered.size());
            state.selected_scalar = filtered.empty() ? 0U : std::min(state.selected_scalar, filtered.size() - 1U);
            for (std::size_t row = 0; row < rows; ++row) {
                const std::size_t index = state.extended_scroll + row;
                if (index >= filtered.size()) break;
                const ConfigScalar& scalar = scalars[filtered[index]];
                Rectangle item{static_cast<float>(x), static_cast<float>(y), static_cast<float>(width), 28.0F};
                if (button(item, scalar.path + " = " + (state.overrides.contains(scalar.path) ? state.overrides.at(scalar.path).value : scalar.value),
                           true, index == state.selected_scalar)) {
                    state.selected_scalar = index;
                    state.scalar_edit = state.overrides.contains(scalar.path) ? state.overrides.at(scalar.path).value : scalar.value;
                }
                y += 30;
            }
            if (!filtered.empty()) {
                const ConfigScalar& chosen = scalars[filtered[state.selected_scalar]];
                Rectangle edit_rect{static_cast<float>(x), static_cast<float>(y + 4), static_cast<float>(width - 174), 32.0F};
                text_field("scalar_value", edit_rect, state.scalar_edit, state.text_edit, chosen.value);
                Rectangle set_rect{edit_rect.x + edit_rect.width + 8.0F, edit_rect.y, 72.0F, 32.0F};
                Rectangle reset_rect{set_rect.x + 78.0F, edit_rect.y, 88.0F, 32.0F};
                if (button(set_rect, "Set")) {
                    std::string override_error;
                    if (validate_scalar_text(state.scalar_edit, chosen.type, override_error)) {
                        state.overrides[chosen.path] = {chosen.path, state.scalar_edit, chosen.type};
                        message = "Temporary override set: " + chosen.path;
                        message_color = Color{103, 225, 151, 255};
                    } else {
                        message = override_error;
                        message_color = ORANGE;
                    }
                }
                if (button(reset_rect, "Reset")) {
                    state.overrides.erase(chosen.path);
                    state.scalar_edit = chosen.value;
                }
                y += 44;
            }
        }

        section("Recent experiments");
        const auto history = recent_history(project_root, static_cast<std::size_t>(settings.recent_experiments));
        if (history.empty()) {
            draw_text("No launcher history yet.", x, y, 12, GRAY);
            y += 20;
        } else {
            for (const auto& line : history) {
                draw_text(elide_text(line.text, width, 11).c_str(), x, y, 11, LIGHTGRAY);
                y += 19;
            }
        }
        const float content_bottom = static_cast<float>(y) + state.detail_scroll - layout.details_view.y + 14.0F;
        state.detail_scroll = std::clamp(
            state.detail_scroll,
            0.0F,
            std::max(0.0F, content_bottom - layout.details_view.height)
        );
        EndScissorMode();

        std::string basic_error;
        const auto permanent_seed = state.mode == ExperimentMode::SingleRun
            ? parse_single_seed(state.seed_text, basic_error)
            : std::optional<std::int64_t>{};
        if (basic_error.empty()) (void)parse_tick(state.tick_text, basic_error);
        std::string tick_error;
        const auto permanent_tick = parse_tick(state.tick_text, tick_error);
        if (new_config_clicked) {
            if (state.save_as_name.empty()) {
                message = "New configuration name cannot be empty.";
                message_color = ORANGE;
            } else if (!basic_error.empty() || !permanent_tick.has_value()) {
                message = !basic_error.empty() ? basic_error : tick_error;
                message_color = ORANGE;
            } else {
                auto destination = config_dir / state.save_as_name;
                if (destination.extension() != ".json") destination += ".json";
                std::string save_error;
                if (save_as_new_config(
                        selected_path,
                        destination,
                        current_override_vector(state),
                        permanent_seed,
                        permanent_tick,
                        save_error
                    )) {
                    message = "Created " + destination.filename().string();
                    message_color = Color{103, 225, 151, 255};
                    refresh();
                } else {
                    message = save_error;
                    message_color = ORANGE;
                }
            }
        }
        if (save_config_clicked) {
            if (!state.replace_armed) {
                state.replace_armed = true;
                message = "Permanent save armed. Click Save again to replace the selected JSON.";
                message_color = ORANGE;
            } else if (!basic_error.empty() || !permanent_tick.has_value()) {
                message = !basic_error.empty() ? basic_error : tick_error;
                message_color = ORANGE;
            } else {
                std::string replace_error;
                if (replace_original_config(
                        selected_path,
                        current_override_vector(state),
                        permanent_seed,
                        permanent_tick,
                        true,
                        replace_error
                    )) {
                    message = "Original configuration permanently saved.";
                    message_color = Color{103, 225, 151, 255};
                    state.replace_armed = false;
                    loaded_config.clear();
                    reload_selected();
                } else {
                    message = replace_error;
                    message_color = ORANGE;
                }
            }
        }

        std::string validation_error;
        std::vector<std::int64_t> seeds;
        std::optional<std::int64_t> single_seed;
        if (state.mode == ExperimentMode::MultiSeed) {
            seeds = parse_seed_list(state.seeds_text, validation_error);
        } else {
            single_seed = parse_single_seed(state.seed_text, validation_error);
            if (single_seed) seeds = {*single_seed};
        }
        const auto tick = validation_error.empty()
            ? parse_tick(state.tick_text, validation_error)
            : std::optional<std::uint64_t>{};
        const bool start_enabled = status.launchable && validation_error.empty() && !selected_path.empty();

        LaunchRequest preview_request = request_template(
            project_root, selected_path, python, state, backends, active_resolution()
        );
        const std::string preview_output = state.output_text.empty() ? "runs/<output>" : state.output_text;
        preview_request.output_path = preview_output;
        preview_request.config_path = preview_request.output_path / "config_resolved.json";
        preview_request.stream_path = preview_request.output_path / "eco_live.bin";
        preview_request.command = command_preview(preview_request, true);

        draw_text("Command", static_cast<int>(layout.command_preview.x),
                  static_cast<int>(layout.command_preview.y - 18.0F), 10, GRAY);
        DrawRectangleRec(layout.command_preview, Color{13, 20, 27, 255});
        DrawRectangleLinesEx(layout.command_preview, 1.0F, Fade(SKYBLUE, 0.18F));
        draw_text(
            elide_text(preview_request.command, static_cast<int>(layout.command_preview.width - 16.0F), 10).c_str(),
            static_cast<int>(layout.command_preview.x + 8.0F),
            static_cast<int>(layout.command_preview.y + 11.0F),
            10,
            Color{145, 187, 205, 255}
        );
        if (icon_button(
                layout.command_copy_button,
                ActionIcon::Copy,
                true,
                false,
                "Copy command"
            )) {
            SetClipboardText(preview_request.command.c_str());
            message = "Command copied.";
            message_color = Color{103, 225, 151, 255};
        }
        const bool close_clicked = icon_button(
            layout.close_button, ActionIcon::Close, true, false, "Close launcher [Esc]"
        );
        const bool start_clicked = icon_button(
            layout.start_button,
            ActionIcon::Run,
            start_enabled,
            true,
            state.mode == ExperimentMode::SingleRun ? "Start simulation [Enter]" : "Start sequential multi-seed [Enter]"
        );
        const bool keyboard_start = IsKeyPressed(KEY_ENTER) && state.text_edit.active.empty() && !state.settings_open;

        draw_text(
            elide_text(message, static_cast<int>(layout.config_panel.width), 12).c_str(),
            static_cast<int>(layout.config_panel.x),
            GetScreenHeight() - 91,
            12,
            message_color
        );
        draw_text("Up/Down config  |  wheel scroll  |  G settings  |  Enter run  |  Esc close",
                  static_cast<int>(layout.config_panel.x), GetScreenHeight() - 28, 10, GRAY);

        if (state.settings_open) {
            g_launcher_input_blocked = false;
            DrawRectangle(0, 0, GetScreenWidth(), GetScreenHeight(), Fade(BLACK, 0.58F));
            const float panel_width = std::min(660.0F, static_cast<float>(GetScreenWidth() - 80));
            const float panel_height = std::min(610.0F, static_cast<float>(GetScreenHeight() - 80));
            Rectangle panel{(GetScreenWidth() - panel_width) * 0.5F, (GetScreenHeight() - panel_height) * 0.5F, panel_width, panel_height};
            DrawRectangleRec(panel, Color{16, 22, 28, 255});
            DrawRectangleLinesEx(panel, 1.0F, Fade(SKYBLUE, 0.65F));
            int sx = static_cast<int>(panel.x + 24.0F), sy = static_cast<int>(panel.y + 22.0F);
            const int sw = static_cast<int>(panel.width - 48.0F);
            draw_text("GUI Settings", sx, sy, 24, RAYWHITE); sy += 46;
            draw_text(("Saved in " + eco::preferences::settings_path(project_root).string()).c_str(), sx, sy, 10, GRAY); sy += 34;
            auto setting_row = [&](const std::string& name, const std::string& value) {
                draw_text(name.c_str(), sx, sy + 8, 12, LIGHTGRAY);
                Rectangle rect{static_cast<float>(sx + 190), static_cast<float>(sy), static_cast<float>(sw - 190), 34.0F};
                sy += 43;
                return std::pair<Rectangle, std::string>{rect, value};
            };
            auto resolution_row = setting_row("Window resolution", resolutions[settings_resolution].custom ? settings_width_text + "x" + settings_height_text : resolutions[settings_resolution].label);
            if (button(resolution_row.first, resolution_row.second + "  next", true, true)) {
                settings_resolution = (settings_resolution + 1U) % resolutions.size();
                if (!resolutions[settings_resolution].custom) {
                    settings_width_text = std::to_string(resolutions[settings_resolution].width);
                    settings_height_text = std::to_string(resolutions[settings_resolution].height);
                }
            }
            if (resolutions[settings_resolution].custom) {
                Rectangle wr{static_cast<float>(sx + 190), static_cast<float>(sy), 130.0F, 32.0F};
                Rectangle hr{wr.x + 142.0F, wr.y, 130.0F, 32.0F};
                text_field("settings_width", wr, settings_width_text, state.text_edit, "1440");
                text_field("settings_height", hr, settings_height_text, state.text_edit, "900");
                sy += 41;
            }
            auto scale_row = setting_row("UI scale", TextFormat("%.0f%%", scales[settings_scale] * 100.0F));
            if (button(scale_row.first, scale_row.second, true, true)) settings_scale = (settings_scale + 1U) % scales.size();
            auto body_row = setting_row("Body/list font", std::to_string(body_sizes[settings_body]) + " px");
            if (button(body_row.first, body_row.second, true, true)) settings_body = (settings_body + 1U) % body_sizes.size();
            auto title_row = setting_row("Title font", std::to_string(title_sizes[settings_title]) + " px");
            if (button(title_row.first, title_row.second, true, true)) settings_title = (settings_title + 1U) % title_sizes.size();
            auto row_row = setting_row("List row height", std::to_string(row_heights[settings_row]) + " px");
            if (button(row_row.first, row_row.second, true, true)) settings_row = (settings_row + 1U) % row_heights.size();
            auto recent_row = setting_row("Recent experiments", std::to_string(recent_counts[settings_recent]));
            if (button(recent_row.first, recent_row.second, true, true)) settings_recent = (settings_recent + 1U) % recent_counts.size();
            auto font_row = setting_row("Monospace family", font_families[settings_font]);
            if (button(font_row.first, font_row.second, true, true)) settings_font = (settings_font + 1U) % font_families.size();
            draw_text(("Loaded font: " + eco::ui::font_source()).c_str(), sx, sy + 4, 10, GRAY); sy += 36;
            Rectangle defaults{static_cast<float>(sx), static_cast<float>(panel.y + panel.height - 58.0F), 142.0F, 36.0F};
            Rectangle apply{defaults.x + defaults.width + 10.0F, defaults.y, 112.0F, 36.0F};
            Rectangle save{apply.x + apply.width + 10.0F, apply.y, 112.0F, 36.0F};
            Rectangle close{panel.x + panel.width - 120.0F, defaults.y, 96.0F, 36.0F};
            if (button(defaults, "Reset defaults")) {
                draft_settings = eco::preferences::default_settings();
                settings_width_text = std::to_string(draft_settings.window_width);
                settings_height_text = std::to_string(draft_settings.window_height);
                settings_resolution = resolutions.size() - 1U;
                settings_scale = nearest_index(draft_settings.ui_scale, scales);
                settings_body = nearest_index(draft_settings.body_font_size, body_sizes);
                settings_title = nearest_index(draft_settings.title_font_size, title_sizes);
                settings_row = nearest_index(draft_settings.row_height, row_heights);
                settings_recent = nearest_index(draft_settings.recent_experiments, recent_counts);
                settings_font = 0;
            }
            if (button(apply, "Apply")) apply_settings();
            if (button(save, "Save")) {
                if (apply_settings()) {
                    std::string save_error;
                    if (eco::preferences::save_settings(project_root, settings, save_error)) {
                        message = "GUI settings saved in project saves/."; message_color = Color{103, 225, 151, 255};
                    } else { message = save_error; message_color = ORANGE; }
                }
            }
            if (button(close, "Close") || IsKeyPressed(KEY_ESCAPE)) state.settings_open = false;
        }

        draw_launcher_tooltip();
        EndDrawing();
        if (close_clicked) { if (state_dirty) save_persistent_state(); return std::nullopt; }
        if ((keyboard_start || start_clicked) && start_enabled) {
            LaunchRequest request;
            request.project_root = project_root;
            request.original_config_path = selected_path;
            request.python = python;
            request.backend = backends[state.backend];
            request.mode = state.mode;
            request.resolution = active_resolution();
            request.seeds = seeds;
            request.until_tick = *tick;
            request.overwrite_partial = state.overwrite_partial;
            request.output_path = resolve_output_template(project_root, state.output_text, selected_path.stem().string());
            request.stream_path = request.output_path / "eco_live.bin";
            request.config_path = request.output_path / "config_resolved.json";
            std::string prepare_error;
            if (!prepare_launch_request(request, prepare_error)) { message = prepare_error; message_color = ORANGE; continue; }
            if (!create_resolved_config(selected_path, request.config_path, current_override_vector(state),
                    state.mode == ExperimentMode::SingleRun ? single_seed : std::optional<std::int64_t>{},
                    state.mode == ExperimentMode::SingleRun ? tick : std::optional<std::uint64_t>{}, prepare_error)) {
                message = prepare_error; message_color = ORANGE; continue;
            }
            if (!write_override_manifest(request, current_override_vector(state),
                    state.mode == ExperimentMode::SingleRun ? single_seed : std::optional<std::int64_t>{},
                    tick, prepare_error)) {
                message = prepare_error; message_color = ORANGE; continue;
            }
            request.command = command_preview(request, false);
            std::string history_error;
            append_history(request, "started", -1, history_error);
            if (state_dirty) save_persistent_state();
            return request;
        }
        if ((keyboard_start || start_clicked) && !start_enabled) {
            message = validation_error.empty() ? status.message : validation_error;
            message_color = ORANGE;
        }
    }
    if (state_dirty) save_persistent_state();
    return std::nullopt;
}

}  // namespace eco::launcher
