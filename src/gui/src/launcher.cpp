#include "eco/launcher.hpp"
#include "eco/ui_font.hpp"

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

int draw_wrapped_text(
    const std::string& text,
    int x,
    int y,
    int max_width,
    int font_size,
    int line_height,
    int max_lines,
    Color color
) {
    std::istringstream words(text);
    std::string line;
    std::string word;
    int lines = 0;
    while (words >> word && lines < max_lines) {
        const std::string candidate = line.empty() ? word : line + " " + word;
        if (!line.empty() && measure_text(candidate.c_str(), font_size) > max_width) {
            draw_text(elide_text(line, max_width, font_size).c_str(), x, y, font_size, color);
            y += line_height;
            ++lines;
            line = word;
        } else {
            line = candidate;
        }
    }
    if (!line.empty() && lines < max_lines) {
        draw_text(elide_text(line, max_width, font_size).c_str(), x, y, font_size, color);
        y += line_height;
    }
    return y;
}

bool button(Rectangle rect, const std::string& label, bool enabled = true, bool active = false) {
    const Vector2 mouse = GetMousePosition();
    const bool hovered = enabled && CheckCollisionPointRec(mouse, rect);
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
    return enabled && hovered && IsMouseButtonPressed(MOUSE_BUTTON_LEFT);
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
    const bool hovered = CheckCollisionPointRec(mouse, rect);
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

std::vector<HistoryLine> recent_history(const std::filesystem::path& project_root) {
    std::vector<HistoryLine> lines;
    std::string error;
    auto root = load_json(project_root / "runs/.experiment_history.json", error);
    if (!root || !root->is_array()) return lines;
    const auto& array = root->array();
    for (auto it = array.rbegin(); it != array.rend() && lines.size() < 4U; ++it) {
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
    bool backend_open = false;
    std::size_t resolution = 0;
    bool resolution_open = false;
    int custom_width = 1440;
    int custom_height = 900;
    std::string custom_width_text = "1440";
    std::string custom_height_text = "900";
    std::string seed_text = "10001";
    std::string seeds_text = "10001,10002,10003";
    std::string tick_text = "1500";
    std::string output_text;
    bool extended_open = false;
    std::string search;
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
    std::string search = state.search;
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
    const std::vector<ResolutionChoice>& resolutions
) {
    LaunchRequest request;
    request.project_root = project_root;
    request.original_config_path = selected_path;
    request.config_path = project_root / "runs/<output>/config_resolved.json";
    request.python = python;
    request.backend = backends[state.backend];
    request.mode = state.mode;
    request.resolution = resolutions[state.resolution];
    if (request.resolution.custom) {
        request.resolution.width = state.custom_width;
        request.resolution.height = state.custom_height;
        request.resolution.label = std::to_string(state.custom_width) + "x" + std::to_string(state.custom_height);
    }
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
    std::sort(result.configs.begin(), result.configs.end(), [](const auto& left, const auto& right) {
        std::string a = left.filename().string();
        std::string b = right.filename().string();
        std::transform(a.begin(), a.end(), a.begin(), [](unsigned char c) { return static_cast<char>(std::tolower(c)); });
        std::transform(b.begin(), b.end(), b.begin(), [](unsigned char c) { return static_cast<char>(std::tolower(c)); });
        return a == b ? left.string() < right.string() : a < b;
    });
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
    const float header_bottom = 126.0F;
    const float footer_height = 82.0F;
    const float gap = 18.0F;
    const float content_height = std::max(430.0F, static_cast<float>(height) - header_bottom - footer_height - margin);
    const float available = static_cast<float>(width) - margin * 2.0F - gap;
    const float left = std::clamp(available * 0.36F, 370.0F, 600.0F);
    LauncherLayout layout;
    layout.config_panel = {margin, header_bottom, left, content_height};
    layout.list_view = {margin + 12.0F, header_bottom + 54.0F, left - 24.0F, content_height - 68.0F};
    layout.details_panel = {margin + left + gap, header_bottom, available - left, content_height};
    layout.details_view = {layout.details_panel.x + 10.0F, layout.details_panel.y + 10.0F, layout.details_panel.width - 20.0F, layout.details_panel.height - 20.0F};
    layout.refresh_button = {layout.config_panel.x + layout.config_panel.width - 118.0F, layout.config_panel.y + 10.0F, 104.0F, 32.0F};
    layout.start_button = {static_cast<float>(width) - margin - 236.0F, static_cast<float>(height) - footer_height + 17.0F, 236.0F, 48.0F};
    layout.close_button = {layout.start_button.x - 118.0F, layout.start_button.y, 104.0F, 48.0F};
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
    const std::filesystem::path path = request.project_root / "runs/.experiment_history.json";
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
    ConfigScanResult scan = find_configs(config_dir);
    std::vector<std::filesystem::path> configs = std::move(scan.configs);
    const std::array<std::string, 3> backends{"cpu", "gpu", "auto"};
    const std::array<std::string, 3> backend_help{
        "CPU: parity and reproducibility",
        "GPU: request CUDA acceleration",
        "AUTO: resolve the available backend",
    };
    const std::vector<ResolutionChoice> resolutions = resolution_choices();
    LauncherState state;
    std::vector<ConfigScalar> scalars;
    std::filesystem::path loaded_config;
    std::string scalar_error;
    std::string message = scan.error.empty()
        ? (configs.empty() ? "No JSON configurations found." : "Temporary overrides run immediately; the source JSON remains unchanged.")
        : scan.error;
    Color message_color = scan.error.empty() ? GRAY : ORANGE;
    std::string last_title;
    std::vector<HistoryLine> history = recent_history(project_root);

    auto reload_selected = [&]() {
        if (configs.empty()) {
            scalars.clear();
            loaded_config.clear();
            return;
        }
        const std::filesystem::path selected_path = configs[state.selected];
        if (selected_path == loaded_config) return;
        scalar_error.clear();
        scalars = inspect_scalar_config(selected_path, scalar_error);
        loaded_config = selected_path;
        reset_config_state(state, selected_path, scalars);
        if (!scalar_error.empty()) {
            message = scalar_error;
            message_color = ORANGE;
        }
    };

    auto refresh = [&]() {
        const std::filesystem::path previous = configs.empty() ? std::filesystem::path{} : configs[state.selected];
        ConfigScanResult refreshed = find_configs(config_dir);
        configs = std::move(refreshed.configs);
        state.selected = 0;
        if (!previous.empty()) {
            const auto found = std::find(configs.begin(), configs.end(), previous);
            if (found != configs.end()) state.selected = static_cast<std::size_t>(found - configs.begin());
        }
        if (!configs.empty()) state.selected = std::min(state.selected, configs.size() - 1U);
        state.config_scroll = 0;
        loaded_config.clear();
        reload_selected();
        message = refreshed.error.empty() ? "Configuration list refreshed." : refreshed.error;
        message_color = refreshed.error.empty() ? GRAY : ORANGE;
    };

    reload_selected();

    while (!WindowShouldClose()) {
        const LauncherLayout layout = make_launcher_layout(GetScreenWidth(), GetScreenHeight());
        constexpr float config_row_height = 38.0F;
        const std::size_t visible_rows = std::max<std::size_t>(1U, static_cast<std::size_t>(layout.list_view.height / config_row_height));
        const Vector2 mouse = GetMousePosition();

        if (IsKeyPressed(KEY_ESCAPE)) return std::nullopt;
        if (IsKeyPressed(KEY_R) || (IsMouseButtonPressed(MOUSE_BUTTON_LEFT) && CheckCollisionPointRec(mouse, layout.refresh_button))) refresh();

        if (!configs.empty()) {
            const auto move_selection = [&](long long delta) {
                const long long maximum = static_cast<long long>(configs.size() - 1U);
                state.selected = static_cast<std::size_t>(std::clamp(static_cast<long long>(state.selected) + delta, 0LL, maximum));
                loaded_config.clear();
                reload_selected();
            };
            if (IsKeyPressed(KEY_DOWN)) move_selection(1);
            if (IsKeyPressed(KEY_UP)) move_selection(-1);
            if (IsKeyPressed(KEY_PAGE_DOWN)) move_selection(static_cast<long long>(visible_rows));
            if (IsKeyPressed(KEY_PAGE_UP)) move_selection(-static_cast<long long>(visible_rows));
            if (IsKeyPressed(KEY_HOME)) { state.selected = 0; loaded_config.clear(); reload_selected(); }
            if (IsKeyPressed(KEY_END)) { state.selected = configs.size() - 1U; loaded_config.clear(); reload_selected(); }
            if (CheckCollisionPointRec(mouse, layout.list_view)) {
                const float wheel = GetMouseWheelMove();
                if (wheel != 0.0F) move_selection(wheel > 0.0F ? -3 : 3);
            }
            state.config_scroll = clamp_launcher_scroll(state.selected, configs.size(), visible_rows, state.config_scroll);
        }

        const std::filesystem::path selected_path = configs.empty() ? std::filesystem::path{} : configs[state.selected];
        const ConfigFileStatus status = selected_path.empty() ? ConfigFileStatus{} : inspect_config_file(selected_path);
        const std::string title = selected_path.empty()
            ? "Subject Evolution Launcher — no configuration"
            : "Subject Evolution Launcher — " + selected_path.filename().string() +
                " [" + mode_short(state.mode) + "/" + backends[state.backend] + "]";
        if (title != last_title) { SetWindowTitle(title.c_str()); last_title = title; }

        if (CheckCollisionPointRec(mouse, layout.details_view) &&
            !(state.has_extended_list_rect && CheckCollisionPointRec(mouse, state.extended_list_rect))) {
            state.detail_scroll = std::max(0.0F, state.detail_scroll - GetMouseWheelMove() * 48.0F);
        }

        BeginDrawing();
        ClearBackground(Color{13, 17, 22, 255});
        draw_text("Subject Evolution", static_cast<int>(layout.config_panel.x), 28, 32, RAYWHITE);
        draw_text("Simulation-first experiment launcher", static_cast<int>(layout.config_panel.x), 69, 18, LIGHTGRAY);
        draw_text(
            (selected_path.empty() ? "No configuration" : selected_path.filename().string() + "  |  " + mode_short(state.mode) + "  |  " + backends[state.backend]).c_str(),
            static_cast<int>(layout.config_panel.x), 96, 14, Color{142, 184, 202, 255}
        );

        DrawRectangleRec(layout.config_panel, Color{6, 11, 16, 242});
        DrawRectangleLinesEx(layout.config_panel, 1.0F, Fade(SKYBLUE, 0.22F));
        draw_text(("Configurations  " + std::to_string(configs.size())).c_str(), static_cast<int>(layout.config_panel.x + 14), static_cast<int>(layout.config_panel.y + 15), 16, LIGHTGRAY);
        if (button(layout.refresh_button, "Refresh [R]")) refresh();
        DrawRectangleRec(layout.list_view, Color{9, 14, 19, 255});
        BeginScissorMode(static_cast<int>(layout.list_view.x), static_cast<int>(layout.list_view.y), static_cast<int>(layout.list_view.width), static_cast<int>(layout.list_view.height));
        const std::size_t row_end = std::min(configs.size(), state.config_scroll + visible_rows);
        for (std::size_t index = state.config_scroll; index < row_end; ++index) {
            const Rectangle row{layout.list_view.x, layout.list_view.y + static_cast<float>(index - state.config_scroll) * config_row_height, layout.list_view.width, config_row_height - 2.0F};
            const bool active = index == state.selected;
            const bool hovered = CheckCollisionPointRec(mouse, row);
            if (active) DrawRectangleRec(row, Color{39, 82, 106, 255});
            else if (hovered) DrawRectangleRec(row, Color{22, 31, 40, 255});
            draw_text(elide_text(configs[index].filename().string(), static_cast<int>(row.width - 62.0F), 15).c_str(), static_cast<int>(row.x + 12), static_cast<int>(row.y + 10), 15, active ? RAYWHITE : LIGHTGRAY);
            if (IsMouseButtonPressed(MOUSE_BUTTON_LEFT) && hovered) {
                state.selected = index;
                loaded_config.clear();
                reload_selected();
            }
        }
        EndScissorMode();

        DrawRectangleRec(layout.details_panel, Color{6, 11, 16, 242});
        DrawRectangleLinesEx(layout.details_panel, 1.0F, Fade(SKYBLUE, 0.22F));
        BeginScissorMode(static_cast<int>(layout.details_view.x), static_cast<int>(layout.details_view.y), static_cast<int>(layout.details_view.width), static_cast<int>(layout.details_view.height));
        const int x = static_cast<int>(layout.details_view.x + 8.0F);
        const int width = static_cast<int>(layout.details_view.width - 22.0F);
        int y = static_cast<int>(layout.details_view.y + 4.0F - state.detail_scroll);

        auto section = [&](const std::string& name) {
            draw_text(name.c_str(), x, y, 17, Color{122, 211, 255, 255});
            y += 28;
        };
        auto label = [&](const std::string& name, int label_width = 104) {
            draw_text(name.c_str(), x, y + 8, 13, GRAY);
            return Rectangle{static_cast<float>(x + label_width), static_cast<float>(y), static_cast<float>(width - label_width), 32.0F};
        };

        section("Experiment");
        if (!selected_path.empty()) {
            draw_text(
                (selected_path.filename().string() + "  " + compact_bytes(status.size_bytes)).c_str(),
                x, y, 14, status.launchable ? LIGHTGRAY : ORANGE
            );
            y += 21;
            draw_text(elide_text(selected_path.string(), width, 12).c_str(), x, y, 12, GRAY);
            y += 19;
            draw_text(status.message.c_str(), x, y, 12, status.launchable ? Color{103, 225, 151, 255} : ORANGE);
            y += 25;
        }
        const Rectangle mode_rect = label("Mode");
        if (button(mode_rect, state.mode == ExperimentMode::SingleRun ? "Single Run" : "Multi Seed", true, true)) {
            state.mode = state.mode == ExperimentMode::SingleRun ? ExperimentMode::MultiSeed : ExperimentMode::SingleRun;
            if (!selected_path.empty()) {
                const std::string stem = selected_path.stem().string();
                state.output_text = state.mode == ExperimentMode::SingleRun
                    ? "runs/gui_" + stem + "_<timestamp>"
                    : "runs/multi_" + stem + "_<timestamp>";
            }
        }
        y += 42;
        const Rectangle backend_rect = label("Backend");
        if (backends.size() <= 3U) {
            if (button(backend_rect, backends[state.backend] + "  —  " + backend_help[state.backend], true, true)) {
                state.backend = (state.backend + 1U) % backends.size();
            }
            y += 42;
        } else {
            if (button(backend_rect, backends[state.backend] + "  ▼", true, state.backend_open)) {
                state.backend_open = !state.backend_open;
            }
            y += 38;
            if (state.backend_open) {
                for (std::size_t index = 0; index < backends.size(); ++index) {
                    Rectangle option{backend_rect.x, static_cast<float>(y), backend_rect.width, 29.0F};
                    if (button(option, backends[index] + " — " + backend_help[index], true, index == state.backend)) {
                        state.backend = index;
                        state.backend_open = false;
                    }
                    y += 31;
                }
            }
            y += 4;
        }
        const Rectangle resolution_rect = label("Resolution");
        const std::string resolution_label = state.resolution < resolutions.size() ? resolutions[state.resolution].label : "custom";
        if (button(resolution_rect, resolution_label + "  ▼", true, state.resolution_open)) state.resolution_open = !state.resolution_open;
        y += 38;
        if (state.resolution_open) {
            for (std::size_t i = 0; i < resolutions.size(); ++i) {
                Rectangle option{resolution_rect.x, static_cast<float>(y), resolution_rect.width, 29.0F};
                if (button(option, resolutions[i].label, true, i == state.resolution)) {
                    state.resolution = i;
                    state.resolution_open = false;
                }
                y += 31;
            }
        }
        if (resolutions[state.resolution].custom) {
            Rectangle wrect{static_cast<float>(x + 104), static_cast<float>(y), 116.0F, 32.0F};
            Rectangle hrect{wrect.x + 126.0F, static_cast<float>(y), 116.0F, 32.0F};
            draw_text("Custom", x, y + 8, 13, GRAY);
            text_field("custom_width", wrect, state.custom_width_text, state.text_edit, "width");
            text_field("custom_height", hrect, state.custom_height_text, state.text_edit, "height");
            try { state.custom_width = std::clamp(std::stoi(state.custom_width_text), 800, 7680); } catch (...) {}
            try { state.custom_height = std::clamp(std::stoi(state.custom_height_text), 600, 4320); } catch (...) {}
            y += 42;
        }

        y += 6;
        section("Basic overrides");
        if (state.mode == ExperimentMode::SingleRun) {
            Rectangle seed_rect = label("Seed");
            text_field("seed", seed_rect, state.seed_text, state.text_edit, "10001");
            y += 42;
        } else {
            Rectangle seeds_rect = label("Seeds");
            text_field("seeds", seeds_rect, state.seeds_text, state.text_edit, "10001,10002,10003");
            y += 42;
        }
        Rectangle tick_rect = label("Until tick");
        text_field("tick", tick_rect, state.tick_text, state.text_edit, "1500");
        y += 42;
        Rectangle output_rect = label("Output");
        text_field("output", output_rect, state.output_text, state.text_edit, "runs/<mode>_<config>_<timestamp>");
        y += 43;
        draw_text("Temporary edits run directly and write config_resolved.json; the original file is untouched.", x + 2, y, 12, Color{125, 166, 182, 255});
        y += 28;

        const Rectangle extended_header{static_cast<float>(x), static_cast<float>(y), static_cast<float>(width), 34.0F};
        if (button(extended_header, state.extended_open ? "▼ Extended overrides" : "▶ Extended overrides", true, state.extended_open)) {
            state.extended_open = !state.extended_open;
        }
        y += 42;
        state.has_extended_list_rect = false;
        if (state.extended_open) {
            Rectangle search_rect{static_cast<float>(x), static_cast<float>(y), static_cast<float>(width), 32.0F};
            text_field("search", search_rect, state.search, state.text_edit, "filter paths...");
            y += 40;
            const auto filtered = filtered_scalar_indices(scalars, state);
            const std::size_t visible = 7U;
            if (filtered.empty()) {
                draw_text("No scalar fields match this filter.", x, y, 13, ORANGE);
                y += 28;
            } else {
                state.selected_scalar = std::min(state.selected_scalar, filtered.size() - 1U);
                state.extended_scroll = clamp_launcher_scroll(state.selected_scalar, filtered.size(), visible, state.extended_scroll);
                const Rectangle list{static_cast<float>(x), static_cast<float>(y), static_cast<float>(width), 7.0F * 31.0F};
                state.extended_list_rect = list;
                state.has_extended_list_rect = true;
                if (CheckCollisionPointRec(mouse, list)) {
                    const float wheel = GetMouseWheelMove();
                    if (wheel != 0.0F) {
                        const long long maximum = static_cast<long long>(filtered.size() - 1U);
                        const long long next = std::clamp(
                            static_cast<long long>(state.selected_scalar) + (wheel > 0.0F ? -1LL : 1LL),
                            0LL,
                            maximum
                        );
                        if (static_cast<std::size_t>(next) != state.selected_scalar) {
                            state.selected_scalar = static_cast<std::size_t>(next);
                            state.scalar_edit.clear();
                        }
                        state.extended_scroll = clamp_launcher_scroll(
                            state.selected_scalar,
                            filtered.size(),
                            visible,
                            state.extended_scroll
                        );
                    }
                }
                DrawRectangleRec(list, Color{9, 14, 19, 255});
                BeginScissorMode(static_cast<int>(list.x), static_cast<int>(list.y), static_cast<int>(list.width), static_cast<int>(list.height));
                for (std::size_t row = 0; row < visible && state.extended_scroll + row < filtered.size(); ++row) {
                    const std::size_t list_index = state.extended_scroll + row;
                    const ConfigScalar& item = scalars[filtered[list_index]];
                    Rectangle item_rect{list.x, list.y + static_cast<float>(row) * 31.0F, list.width, 29.0F};
                    const bool active = list_index == state.selected_scalar;
                    const bool hovered = CheckCollisionPointRec(mouse, item_rect);
                    if (active) DrawRectangleRec(item_rect, Color{34, 66, 83, 255});
                    else if (hovered) DrawRectangleRec(item_rect, Color{22, 31, 40, 255});
                    const auto override_it = state.overrides.find(item.path);
                    const std::string value = override_it == state.overrides.end() ? item.value : override_it->second.value;
                    draw_text(elide_text(item.path, width - 190, 13).c_str(), x + 8, static_cast<int>(item_rect.y + 8), 13, active ? RAYWHITE : LIGHTGRAY);
                    draw_text(elide_text(value, 150, 13).c_str(), x + width - 158, static_cast<int>(item_rect.y + 8), 13, override_it == state.overrides.end() ? GRAY : Color{255, 204, 92, 255});
                    if (IsMouseButtonPressed(MOUSE_BUTTON_LEFT) && hovered) {
                        state.selected_scalar = list_index;
                        state.scalar_edit = value;
                    }
                }
                EndScissorMode();
                y += static_cast<int>(list.height) + 8;
                const ConfigScalar& chosen = scalars[filtered[state.selected_scalar]];
                if (state.scalar_edit.empty()) {
                    const auto found = state.overrides.find(chosen.path);
                    state.scalar_edit = found == state.overrides.end() ? chosen.value : found->second.value;
                }
                Rectangle edit_rect{static_cast<float>(x), static_cast<float>(y), static_cast<float>(width - 178), 32.0F};
                text_field("scalar_value", edit_rect, state.scalar_edit, state.text_edit, chosen.value);
                Rectangle set_rect{edit_rect.x + edit_rect.width + 8.0F, edit_rect.y, 78.0F, 32.0F};
                Rectangle reset_rect{set_rect.x + 84.0F, set_rect.y, 82.0F, 32.0F};
                if (button(set_rect, "Set")) {
                    std::string override_error;
                    if (validate_scalar_text(state.scalar_edit, chosen.type, override_error)) {
                        state.overrides[chosen.path] = ConfigScalar{chosen.path, state.scalar_edit, chosen.type};
                        message = "Temporary override set: " + chosen.path;
                        message_color = Color{103, 225, 151, 255};
                    } else {
                        message = chosen.path + ": " + override_error;
                        message_color = ORANGE;
                    }
                }
                if (button(reset_rect, "Reset")) {
                    state.overrides.erase(chosen.path);
                    state.scalar_edit = chosen.value;
                }
                y += 42;
            }
        }

        section("Permanent config actions");
        Rectangle name_rect{static_cast<float>(x), static_cast<float>(y), static_cast<float>(width - 164), 32.0F};
        text_field("save_name", name_rect, state.save_as_name, state.text_edit, "new_config.json");
        Rectangle save_rect{name_rect.x + name_rect.width + 8.0F, name_rect.y, 156.0F, 32.0F};
        std::string basic_error;
        const auto permanent_seed = state.mode == ExperimentMode::SingleRun ? parse_single_seed(state.seed_text, basic_error) : std::optional<std::int64_t>{};
        basic_error.clear();
        const auto until_tick = parse_tick(state.tick_text, basic_error);
        if (button(save_rect, "Save as new", status.launchable)) {
            std::filesystem::path destination = config_dir / state.save_as_name;
            if (destination.extension() != ".json") destination += ".json";
            std::string save_error;
            if (save_as_new_config(selected_path, destination, current_override_vector(state), permanent_seed, until_tick, save_error)) {
                message = "Saved " + destination.filename().string();
                message_color = Color{103, 225, 151, 255};
                refresh();
            } else {
                message = save_error;
                message_color = ORANGE;
            }
        }
        y += 40;
        Rectangle replace_rect{static_cast<float>(x), static_cast<float>(y), 220.0F, 32.0F};
        if (button(replace_rect, state.replace_armed ? "Confirm replace original" : "Replace original", status.launchable, state.replace_armed)) {
            if (!state.replace_armed) {
                state.replace_armed = true;
                message = "Click Replace original again to confirm permanent overwrite.";
                message_color = ORANGE;
            } else {
                std::string replace_error;
                if (replace_original_config(selected_path, current_override_vector(state), permanent_seed, until_tick, true, replace_error)) {
                    message = "Original configuration replaced.";
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
        y += 45;

        section("Command preview");
        LaunchRequest preview_request = request_template(project_root, selected_path, python, state, backends, resolutions);
        const std::string preview_output = state.output_text.empty() ? "runs/<output>" : state.output_text;
        preview_request.output_path = std::filesystem::path(preview_output);
        preview_request.config_path = preview_request.output_path / "config_resolved.json";
        preview_request.stream_path = preview_request.output_path / "eco_live.bin";
        preview_request.command = command_preview(preview_request, true);
        Rectangle copy_rect{static_cast<float>(x + width - 116), static_cast<float>(y - 28), 108.0F, 28.0F};
        if (button(copy_rect, "Copy command")) {
            SetClipboardText(preview_request.command.c_str());
            message = "Command copied to clipboard.";
            message_color = Color{103, 225, 151, 255};
        }
        y = draw_wrapped_text(preview_request.command, x, y, width, 12, 17, 7, Color{145, 187, 205, 255});
        y += 10;

        section("Recent experiments");
        if (history.empty()) {
            draw_text("No launcher history yet.", x, y, 13, GRAY);
            y += 22;
        } else {
            for (const HistoryLine& line : history) {
                draw_text(elide_text(line.text, width, 13).c_str(), x, y, 13, LIGHTGRAY);
                y += 20;
            }
        }
        const float content_bottom = static_cast<float>(y) + state.detail_scroll - layout.details_view.y + 14.0F;
        state.detail_scroll = std::clamp(state.detail_scroll, 0.0F, std::max(0.0F, content_bottom - layout.details_view.height));
        EndScissorMode();

        draw_text(message.c_str(), static_cast<int>(layout.config_panel.x), GetScreenHeight() - 60, 14, message_color);
        draw_text("Up/Down: config  |  wheel: scroll  |  Enter: start  |  backend/mode: click", static_cast<int>(layout.config_panel.x), GetScreenHeight() - 35, 12, GRAY);
        const bool close_clicked = button(layout.close_button, "Close [Esc]");

        std::string validation_error;
        std::vector<std::int64_t> seeds;
        std::optional<std::int64_t> single_seed;
        if (state.mode == ExperimentMode::MultiSeed) seeds = parse_seed_list(state.seeds_text, validation_error);
        else {
            single_seed = parse_single_seed(state.seed_text, validation_error);
            if (single_seed) seeds = {*single_seed};
        }
        const auto tick = validation_error.empty() ? parse_tick(state.tick_text, validation_error) : std::optional<std::uint64_t>{};
        if (resolutions[state.resolution].custom && (state.custom_width < 800 || state.custom_height < 600)) validation_error = "Custom resolution is out of range.";
        const bool start_enabled = status.launchable && validation_error.empty() && !selected_path.empty();
        const bool start_clicked = button(layout.start_button, state.mode == ExperimentMode::SingleRun ? "Start simulation [Enter]" : "Start multi-seed [Enter]", start_enabled, true);
        const bool keyboard_start = IsKeyPressed(KEY_ENTER) && state.text_edit.active.empty();

        EndDrawing();

        if (close_clicked) return std::nullopt;
        if ((keyboard_start || start_clicked) && start_enabled) {
            LaunchRequest request;
            request.project_root = project_root;
            request.original_config_path = selected_path;
            request.python = python;
            request.backend = backends[state.backend];
            request.mode = state.mode;
            request.resolution = resolutions[state.resolution];
            if (request.resolution.custom) {
                request.resolution.width = state.custom_width;
                request.resolution.height = state.custom_height;
                request.resolution.label = std::to_string(state.custom_width) + "x" + std::to_string(state.custom_height);
            }
            request.seeds = seeds;
            request.until_tick = *tick;
            request.output_path = resolve_output_template(project_root, state.output_text, selected_path.stem().string());
            request.stream_path = request.output_path / "eco_live.bin";
            request.config_path = request.output_path / "config_resolved.json";
            std::string prepare_error;
            if (!prepare_launch_request(request, prepare_error)) {
                message = prepare_error;
                message_color = ORANGE;
                continue;
            }
            if (!create_resolved_config(
                    selected_path,
                    request.config_path,
                    current_override_vector(state),
                    state.mode == ExperimentMode::SingleRun ? single_seed : std::optional<std::int64_t>{},
                    state.mode == ExperimentMode::SingleRun ? tick : std::optional<std::uint64_t>{},
                    prepare_error)) {
                message = prepare_error;
                message_color = ORANGE;
                continue;
            }
            if (!write_override_manifest(
                    request,
                    current_override_vector(state),
                    state.mode == ExperimentMode::SingleRun ? single_seed : std::optional<std::int64_t>{},
                    tick,
                    prepare_error)) {
                message = prepare_error;
                message_color = ORANGE;
                continue;
            }
            request.command = command_preview(request, false);
            std::string history_error;
            append_history(request, "started", -1, history_error);
            return request;
        }
        if ((keyboard_start || start_clicked) && !start_enabled) {
            message = validation_error.empty() ? status.message : validation_error;
            message_color = ORANGE;
        }
    }
    return std::nullopt;
}

}  // namespace eco::launcher
