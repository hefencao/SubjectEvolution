#include "eco/renderer.hpp"

#include <algorithm>
#include <array>
#include <cmath>
#include <cstddef>
#include <cstdint>
#include <limits>
#include <unordered_map>
#include <unordered_set>
#include <vector>

#include <rlgl.h>

namespace eco {
namespace {

float clamp01(float value) {
    return std::clamp(value, 0.0F, 1.0F);
}

bool finite_value(float value) noexcept {
    return std::isfinite(value);
}

bool valid_world_position(float x, float y) noexcept {
    return finite_value(x) && finite_value(y);
}

bool valid_entity_sample(const EntitySample& entity) noexcept {
    return entity.entity_id != 0 &&
           valid_world_position(entity.x, entity.y) &&
           finite_value(entity.vx) &&
           finite_value(entity.vy) &&
           finite_value(entity.energy) &&
           finite_value(entity.integrity);
}

float smoothstep01(float value) {
    value = clamp01(value);
    return value * value * (3.0F - 2.0F * value);
}

float smooth_range(float begin, float end, float value) {
    if (end <= begin) {
        return value >= end ? 1.0F : 0.0F;
    }
    return smoothstep01((value - begin) / (end - begin));
}

float lerp_value(float low, float high, float weight) {
    return low + (high - low) * clamp01(weight);
}

std::uint64_t mix_id(std::uint64_t value) {
    value ^= value >> 33U;
    value *= 0xff51afd7ed558ccdULL;
    value ^= value >> 33U;
    value *= 0xc4ceb9fe1a85ec53ULL;
    value ^= value >> 33U;
    return value;
}

Color hsv_color(float hue, float saturation, float value, unsigned char alpha) {
    hue -= std::floor(hue);
    saturation = clamp01(saturation);
    value = clamp01(value);

    const float scaled = hue * 6.0F;
    const int sector = static_cast<int>(std::floor(scaled)) % 6;
    const float fraction = scaled - std::floor(scaled);
    const float p = value * (1.0F - saturation);
    const float q = value * (1.0F - saturation * fraction);
    const float t = value * (1.0F - saturation * (1.0F - fraction));

    float red = value;
    float green = t;
    float blue = p;

    switch (sector) {
    case 0:
        red = value; green = t; blue = p;
        break;
    case 1:
        red = q; green = value; blue = p;
        break;
    case 2:
        red = p; green = value; blue = t;
        break;
    case 3:
        red = p; green = q; blue = value;
        break;
    case 4:
        red = t; green = p; blue = value;
        break;
    default:
        red = value; green = p; blue = q;
        break;
    }

    return Color{
        static_cast<unsigned char>(std::clamp(red * 255.0F, 0.0F, 255.0F)),
        static_cast<unsigned char>(std::clamp(green * 255.0F, 0.0F, 255.0F)),
        static_cast<unsigned char>(std::clamp(blue * 255.0F, 0.0F, 255.0F)),
        alpha
    };
}

float quantile(std::vector<float>& values, float fraction) {
    if (values.empty()) {
        return 0.0F;
    }

    fraction = clamp01(fraction);
    const std::size_t index = static_cast<std::size_t>(
        fraction * static_cast<float>(values.size() - 1)
    );
    std::nth_element(values.begin(), values.begin() + index, values.end());
    return values[index];
}

struct Palette {
    std::array<float, 3> low;
    std::array<float, 3> high;
};

Palette resource_palette(int channel) {
    switch (channel) {
    case 1:
        return Palette{{8.0F, 15.0F, 28.0F}, {74.0F, 145.0F, 225.0F}};
    case 2:
        return Palette{{16.0F, 11.0F, 25.0F}, {151.0F, 91.0F, 220.0F}};
    case 3:
        return Palette{{24.0F, 14.0F, 7.0F}, {225.0F, 157.0F, 56.0F}};
    default:
        return Palette{{6.0F, 17.0F, 12.0F}, {81.0F, 184.0F, 91.0F}};
    }
}

struct FilterParameters {
    float resource_alpha_per_tick;
    float hazard_alpha_per_tick;
    float resource_max_step_fraction;
    float hazard_max_step;
};

FilterParameters filter_parameters(EnvironmentFilterMode mode) {
    switch (mode) {
    case EnvironmentFilterMode::Instant:
        return FilterParameters{1.0F, 1.0F, 1.0F, 1.0F};
    case EnvironmentFilterMode::Responsive:
        return FilterParameters{0.18F, 0.12F, 0.045F, 0.030F};
    case EnvironmentFilterMode::Stable:
        return FilterParameters{0.075F, 0.045F, 0.018F, 0.012F};
    }
    return FilterParameters{0.075F, 0.045F, 0.018F, 0.012F};
}

float effective_alpha(float per_tick_alpha, std::uint64_t elapsed_ticks) {
    if (per_tick_alpha >= 1.0F) {
        return 1.0F;
    }
    const float ticks = static_cast<float>(std::clamp<std::uint64_t>(elapsed_ticks, 1, 64));
    return 1.0F - std::pow(1.0F - clamp01(per_tick_alpha), ticks);
}

float filtered_step(float previous, float target, float alpha, float maximum_step) {
    if (!finite_value(previous)) {
        return target;
    }
    const float delta = target - previous;
    return previous + std::clamp(delta * alpha, -maximum_step, maximum_step);
}


struct SolidQuadBatch {
    unsigned int texture_id = 0;
    float u0 = 0.0F;
    float v0 = 0.0F;
    float u1 = 1.0F;
    float v1 = 1.0F;
};

SolidQuadBatch begin_solid_quad_batch() {
    const Texture2D texture = GetShapesTexture();
    const Rectangle source = GetShapesTextureRectangle();
    const float texture_width = static_cast<float>(std::max(texture.width, 1));
    const float texture_height = static_cast<float>(std::max(texture.height, 1));

    SolidQuadBatch batch{
        texture.id,
        source.x / texture_width,
        source.y / texture_height,
        (source.x + source.width) / texture_width,
        (source.y + source.height) / texture_height
    };

    rlSetTexture(batch.texture_id);
    rlBegin(RL_QUADS);
    rlNormal3f(0.0F, 0.0F, 1.0F);
    return batch;
}

void emit_solid_quad(
    const SolidQuadBatch& batch,
    float left,
    float top,
    float right,
    float bottom,
    Color color
) {
    rlColor4ub(color.r, color.g, color.b, color.a);

    // Keep the raylib 5.5 shape winding and white-texture UV order that was
    // verified on the user's OpenGL path: top-left, bottom-left,
    // bottom-right, top-right.
    rlTexCoord2f(batch.u0, batch.v0);
    rlVertex2f(left, top);
    rlTexCoord2f(batch.u0, batch.v1);
    rlVertex2f(left, bottom);
    rlTexCoord2f(batch.u1, batch.v1);
    rlVertex2f(right, bottom);
    rlTexCoord2f(batch.u1, batch.v0);
    rlVertex2f(right, top);
}

void end_solid_quad_batch() {
    rlEnd();
    rlSetTexture(0);
}

void blur_grid(
    const std::vector<float>& input,
    std::vector<float>& output,
    std::vector<float>& scratch,
    std::uint32_t width,
    std::uint32_t height,
    int radius
) {
    if (radius <= 0 || input.empty()) {
        output = input;
        return;
    }

    const std::size_t count = static_cast<std::size_t>(width) * height;
    scratch.resize(count);
    output.resize(count);

    for (std::uint32_t y = 0; y < height; ++y) {
        float sum = 0.0F;
        int samples = 0;
        for (int x = -radius; x <= radius; ++x) {
            const int sample_x = std::clamp(x, 0, static_cast<int>(width) - 1);
            sum += input[static_cast<std::size_t>(y) * width + sample_x];
            ++samples;
        }
        for (std::uint32_t x = 0; x < width; ++x) {
            scratch[static_cast<std::size_t>(y) * width + x] =
                sum / static_cast<float>(samples);
            const int remove_x = std::clamp(
                static_cast<int>(x) - radius,
                0,
                static_cast<int>(width) - 1
            );
            const int add_x = std::clamp(
                static_cast<int>(x) + radius + 1,
                0,
                static_cast<int>(width) - 1
            );
            sum += input[static_cast<std::size_t>(y) * width + add_x] -
                input[static_cast<std::size_t>(y) * width + remove_x];
        }
    }

    for (std::uint32_t x = 0; x < width; ++x) {
        float sum = 0.0F;
        int samples = 0;
        for (int y = -radius; y <= radius; ++y) {
            const int sample_y = std::clamp(y, 0, static_cast<int>(height) - 1);
            sum += scratch[static_cast<std::size_t>(sample_y) * width + x];
            ++samples;
        }
        for (std::uint32_t y = 0; y < height; ++y) {
            output[static_cast<std::size_t>(y) * width + x] =
                sum / static_cast<float>(samples);
            const int remove_y = std::clamp(
                static_cast<int>(y) - radius,
                0,
                static_cast<int>(height) - 1
            );
            const int add_y = std::clamp(
                static_cast<int>(y) + radius + 1,
                0,
                static_cast<int>(height) - 1
            );
            sum += scratch[static_cast<std::size_t>(add_y) * width + x] -
                scratch[static_cast<std::size_t>(remove_y) * width + x];
        }
    }
}

Color heat_color(
    int channel,
    float resource,
    float hazard,
    float population_density,
    float resource_change,
    float hazard_change,
    float gradient_x,
    float gradient_y,
    float hazard_edge,
    const RenderDetail& detail,
    const RenderOptions& options
) {
    resource = smoothstep01(resource);
    hazard = clamp01(hazard);
    population_density = clamp01(population_density);
    resource_change = std::clamp(resource_change, -1.0F, 1.0F);
    hazard_change = std::clamp(hazard_change, -1.0F, 1.0F);
    hazard_edge = clamp01(hazard_edge);

    const float gradient_magnitude = clamp01(
        std::sqrt(gradient_x * gradient_x + gradient_y * gradient_y)
    );
    const Palette palette = resource_palette(channel);

    auto resource_rgb = [&]() {
        const float contrast = std::pow(resource, 0.78F);
        return std::array<float, 3>{
            palette.low[0] + (palette.high[0] - palette.low[0]) * contrast,
            palette.low[1] + (palette.high[1] - palette.low[1]) * contrast,
            palette.low[2] + (palette.high[2] - palette.low[2]) * contrast,
        };
    };

    if (options.environment_view == EnvironmentViewMode::ResourceAbsolute) {
        const auto rgb = resource_rgb();
        return Color{
            static_cast<unsigned char>(std::clamp(rgb[0] * 1.12F, 0.0F, 255.0F)),
            static_cast<unsigned char>(std::clamp(rgb[1] * 1.12F, 0.0F, 255.0F)),
            static_cast<unsigned char>(std::clamp(rgb[2] * 1.12F, 0.0F, 255.0F)),
            255
        };
    }

    if (options.environment_view == EnvironmentViewMode::ResourceGradient) {
        const float angle = std::atan2(gradient_y, gradient_x);
        const float hue = angle / (2.0F * 3.14159265358979323846F) + 0.5F;
        const float magnitude = std::pow(gradient_magnitude, 0.62F);
        const Color direction = hsv_color(hue, 0.58F, 0.72F, 255);
        const float base = 7.0F + magnitude * 184.0F;
        const float direction_mix = 0.18F + 0.48F * magnitude;
        return Color{
            static_cast<unsigned char>(std::clamp(
                base * (1.0F - direction_mix) + direction.r * direction_mix,
                0.0F, 255.0F)),
            static_cast<unsigned char>(std::clamp(
                base * (1.0F - direction_mix) + direction.g * direction_mix,
                0.0F, 255.0F)),
            static_cast<unsigned char>(std::clamp(
                (base + 8.0F) * (1.0F - direction_mix) + direction.b * direction_mix,
                0.0F, 255.0F)),
            255
        };
    }

    if (options.environment_view == EnvironmentViewMode::Hazard) {
        const float visible = smooth_range(0.08F, 0.88F, hazard);
        const float fill = std::pow(visible, 1.25F);
        const float edge = std::pow(hazard_edge, 0.78F) *
            smooth_range(0.04F, 0.36F, hazard);
        const float red = 7.0F + fill * 156.0F + edge * 52.0F;
        const float green = 9.0F + fill * 31.0F + edge * 19.0F;
        const float blue = 13.0F + fill * 35.0F + edge * 46.0F;
        return Color{
            static_cast<unsigned char>(std::clamp(red, 0.0F, 255.0F)),
            static_cast<unsigned char>(std::clamp(green, 0.0F, 255.0F)),
            static_cast<unsigned char>(std::clamp(blue, 0.0F, 255.0F)),
            255
        };
    }

    if (options.environment_view == EnvironmentViewMode::PopulationDensity) {
        const float density_curve = std::pow(population_density, 0.48F);
        return Color{
            static_cast<unsigned char>(8.0F + density_curve * 38.0F),
            static_cast<unsigned char>(13.0F + density_curve * 196.0F),
            static_cast<unsigned char>(18.0F + density_curve * 218.0F),
            255
        };
    }

    if (options.environment_view == EnvironmentViewMode::ResourceDelta) {
        const float positive = std::max(resource_change, 0.0F);
        const float negative = std::max(-resource_change, 0.0F);
        const float magnitude = std::max(positive, negative);
        const float base = 10.0F + 16.0F * (1.0F - magnitude);
        return Color{
            static_cast<unsigned char>(std::clamp(base + negative * 222.0F, 0.0F, 255.0F)),
            static_cast<unsigned char>(std::clamp(base + positive * 216.0F + negative * 62.0F, 0.0F, 255.0F)),
            static_cast<unsigned char>(std::clamp(base + positive * 96.0F, 0.0F, 255.0F)),
            255
        };
    }

    const auto base_rgb = resource_rgb();
    float red = base_rgb[0];
    float green = base_rgb[1];
    float blue = base_rgb[2];

    // Composite mode keeps resource as the primary semantic layer. Hazard fill
    // is intentionally weak; its spatial boundary is the stronger cue.
    if (options.show_hazard) {
        // Composite view treats hazard as a selective annotation, not a red
        // replacement layer. Low-level noise is suppressed and boundaries are
        // visible only where the local hazard itself is meaningful.
        const float visible = smooth_range(0.16F, 0.82F, hazard);
        const float fill = std::pow(visible, 1.45F) * 0.055F;
        const float edge = std::pow(hazard_edge, 0.82F) *
            smooth_range(0.10F, 0.48F, hazard) * 0.20F;
        red = red * (1.0F - fill) + 132.0F * fill;
        green = green * (1.0F - fill) + 42.0F * fill;
        blue = blue * (1.0F - fill) + 40.0F * fill;
        red += edge * 58.0F;
        green += edge * 14.0F;
        blue += edge * 23.0F;
    }

    if (options.show_population_density) {
        const float density_strength = 0.12F * detail.density_weight;
        const float density_curve = std::sqrt(population_density) * density_strength;
        red += density_curve * 10.0F;
        green += density_curve * 78.0F;
        blue += density_curve * 94.0F;
    }

    if (options.show_environment_change) {
        if (resource_change > 0.0F) {
            green += resource_change * 58.0F;
            blue += resource_change * 18.0F;
        } else {
            red += -resource_change * 66.0F;
            green += -resource_change * 17.0F;
        }
        if (hazard_change > 0.0F) {
            red += hazard_change * 12.0F;
            blue += hazard_change * 6.0F;
        }
    }

    return Color{
        static_cast<unsigned char>(std::clamp(red, 0.0F, 255.0F)),
        static_cast<unsigned char>(std::clamp(green, 0.0F, 255.0F)),
        static_cast<unsigned char>(std::clamp(blue, 0.0F, 255.0F)),
        255
    };
}

bool is_visible(
    const EntitySample& entity,
    float left,
    float top,
    float right,
    float bottom,
    float padding
) {
    return entity.x >= left - padding &&
           entity.x <= right + padding &&
           entity.y >= top - padding &&
           entity.y <= bottom + padding;
}

float wrapped_delta(float delta, float extent) {
    if (extent <= 0.0F) {
        return delta;
    }
    if (delta > extent * 0.5F) {
        delta -= extent;
    } else if (delta < -extent * 0.5F) {
        delta += extent;
    }
    return delta;
}

Vector2 previous_endpoint(
    Vector2 current,
    Vector2 previous,
    float world_width,
    float world_height
) {
    const float dx = wrapped_delta(current.x - previous.x, world_width);
    const float dy = wrapped_delta(current.y - previous.y, world_height);
    return Vector2{current.x - dx, current.y - dy};
}

struct FlowCell {
    float sum_vx = 0.0F;
    float sum_vy = 0.0F;
    float sum_speed = 0.0F;
    float sum_x = 0.0F;
    float sum_y = 0.0F;
    std::uint32_t count = 0;
};

void draw_flow_field(
    const Frame& frame,
    const Camera2D& camera,
    float weight
) {
    constexpr int columns = 18;
    constexpr int rows = 11;
    constexpr int cell_count = columns * rows;
    constexpr std::size_t maximum_arrows = 42;
    weight = clamp01(weight);
    if (weight <= 0.01F) {
        return;
    }

    static thread_local std::array<FlowCell, cell_count> cells{};
    cells.fill(FlowCell{});

    const float world_width = std::max(frame.layout.world_width, 1.0F);
    const float world_height = std::max(frame.layout.world_height, 1.0F);

    for (const EntitySample& entity : frame.entities) {
        if (!valid_entity_sample(entity)) {
            continue;
        }
        const float speed = std::sqrt(entity.vx * entity.vx + entity.vy * entity.vy);
        if (!finite_value(speed)) {
            continue;
        }
        const int column = std::clamp(
            static_cast<int>(entity.x / world_width * columns),
            0,
            columns - 1
        );
        const int row = std::clamp(
            static_cast<int>(entity.y / world_height * rows),
            0,
            rows - 1
        );
        FlowCell& cell = cells[static_cast<std::size_t>(row * columns + column)];
        cell.sum_vx += entity.vx;
        cell.sum_vy += entity.vy;
        cell.sum_speed += speed;
        cell.sum_x += entity.x;
        cell.sum_y += entity.y;
        ++cell.count;
    }

    struct Candidate {
        int index = 0;
        float score = 0.0F;
        float coherence = 0.0F;
        float speed = 0.0F;
    };
    std::vector<Candidate> candidates;
    candidates.reserve(cell_count);

    for (int index = 0; index < cell_count; ++index) {
        const FlowCell& cell = cells[static_cast<std::size_t>(index)];
        if (cell.count < 12U || cell.sum_speed <= 1.0e-5F) {
            continue;
        }
        const float resultant = std::sqrt(
            cell.sum_vx * cell.sum_vx + cell.sum_vy * cell.sum_vy
        );
        const float coherence = clamp01(resultant / cell.sum_speed);
        const float mean_speed = cell.sum_speed / static_cast<float>(cell.count);
        if (coherence < 0.16F || mean_speed < 0.018F) {
            continue;
        }
        const float score = std::log1p(static_cast<float>(cell.count)) *
            coherence * std::sqrt(mean_speed);
        candidates.push_back(Candidate{index, score, coherence, mean_speed});
    }

    std::sort(
        candidates.begin(),
        candidates.end(),
        [](const Candidate& left, const Candidate& right) {
            return left.score > right.score;
        }
    );
    if (candidates.size() > maximum_arrows) {
        candidates.resize(maximum_arrows);
    }

    const float cell_width = world_width / static_cast<float>(columns);
    const float cell_height = world_height / static_cast<float>(rows);
    const float maximum_length = std::min(cell_width, cell_height) * 0.52F;
    const float inverse_zoom = 1.0F / std::max(camera.zoom, 0.001F);

    for (const Candidate& candidate : candidates) {
        const FlowCell& cell = cells[static_cast<std::size_t>(candidate.index)];
        const float resultant = std::sqrt(
            cell.sum_vx * cell.sum_vx + cell.sum_vy * cell.sum_vy
        );
        if (resultant <= 1.0e-6F) {
            continue;
        }
        const float direction_x = cell.sum_vx / resultant;
        const float direction_y = cell.sum_vy / resultant;
        const float length = std::min(
            maximum_length,
            candidate.speed * lerp_value(26.0F, 48.0F, weight) *
                (0.45F + 0.55F * candidate.coherence)
        );
        const Vector2 start{
            cell.sum_x / static_cast<float>(cell.count),
            cell.sum_y / static_cast<float>(cell.count)
        };
        const Vector2 end{
            start.x + direction_x * length,
            start.y + direction_y * length
        };
        const float opacity = std::clamp(
            (0.12F + 0.66F * candidate.coherence) * weight,
            0.05F,
            0.78F
        );
        const float line_width = lerp_value(0.72F, 1.35F, weight) * inverse_zoom;
        const Color color = Fade(Color{92, 226, 255, 255}, opacity);
        DrawLineEx(start, end, line_width, color);

        const float head_length = std::min(length * 0.28F, maximum_length * 0.18F);
        const float side_x = -direction_y;
        const float side_y = direction_x;
        DrawLineEx(
            end,
            Vector2{
                end.x - direction_x * head_length + side_x * head_length * 0.42F,
                end.y - direction_y * head_length + side_y * head_length * 0.42F
            },
            line_width,
            color
        );
        DrawLineEx(
            end,
            Vector2{
                end.x - direction_x * head_length - side_x * head_length * 0.42F,
                end.y - direction_y * head_length - side_y * head_length * 0.42F
            },
            line_width,
            color
        );
    }
}

double estimate_visible_entities(
    const Frame& frame,
    const Camera2D& camera,
    Rectangle viewport
) {
    const double world_width = std::max(
        static_cast<double>(frame.layout.world_width),
        1.0
    );
    const double world_height = std::max(
        static_cast<double>(frame.layout.world_height),
        1.0
    );
    const double zoom = std::max(static_cast<double>(camera.zoom), 0.001);
    const double visible_world_width = std::min(
        world_width,
        std::max(1.0, static_cast<double>(viewport.width) / zoom)
    );
    const double visible_world_height = std::min(
        world_height,
        std::max(1.0, static_cast<double>(viewport.height) / zoom)
    );
    const double visible_fraction = std::clamp(
        (visible_world_width * visible_world_height) /
            (world_width * world_height),
        0.0,
        1.0
    );
    return static_cast<double>(frame.entities.size()) * visible_fraction;
}

Color event_color(WorldRenderer::EventKind kind) {
    switch (kind) {
    case WorldRenderer::EventKind::Birth:
        return Color{83, 240, 255, 255};
    case WorldRenderer::EventKind::Death:
        return Color{255, 78, 82, 255};
    case WorldRenderer::EventKind::Harvest:
        return Color{117, 242, 120, 255};
    case WorldRenderer::EventKind::Reproduce:
        return Color{247, 105, 255, 255};
    }
    return WHITE;
}

std::uint64_t event_ttl(WorldRenderer::EventKind kind) {
    switch (kind) {
    case WorldRenderer::EventKind::Harvest:
        return 18;
    case WorldRenderer::EventKind::Reproduce:
        return 34;
    case WorldRenderer::EventKind::Birth:
    case WorldRenderer::EventKind::Death:
        return 56;
    }
    return 32;
}

int action_index(Action action) noexcept {
    const int index = static_cast<int>(action);
    return index >= 0 && index < 8 ? index : -1;
}

Color behavior_color(Action action, unsigned char alpha = 255) {
    switch (action) {
    case Action::MoveResource:
        return Color{255, 215, 75, alpha};
    case Action::MoveSocial:
        return Color{102, 190, 255, alpha};
    case Action::Harvest:
        // Amber deliberately avoids the green resource palette.
        return Color{255, 174, 48, alpha};
    case Action::Share:
        return Color{66, 236, 255, alpha};
    case Action::Signal:
        return Color{139, 154, 255, alpha};
    case Action::Reproduce:
        return Color{255, 98, 232, alpha};
    case Action::Flee:
        return Color{255, 76, 67, alpha};
    case Action::Rest:
        return Color{190, 201, 211, alpha};
    default:
        return Color{210, 220, 228, alpha};
    }
}


Color color_for_group_id(std::uint64_t group_id, unsigned char alpha = 255) {
    const std::uint64_t hash = mix_id(group_id);
    const float hue = static_cast<float>(hash & 0xFFFFU) / 65535.0F;
    return hsv_color(hue, 0.78F, 0.98F, alpha);
}

void draw_action_glyph_layer(
    Action action,
    Vector2 center,
    float radius,
    float width,
    Color color
) {
    switch (action) {
    case Action::MoveResource:
        DrawLineEx(Vector2{center.x - radius, center.y},
            Vector2{center.x + radius * 0.75F, center.y}, width, color);
        DrawLineEx(Vector2{center.x + radius * 0.75F, center.y},
            Vector2{center.x + radius * 0.15F, center.y - radius * 0.58F}, width, color);
        DrawLineEx(Vector2{center.x + radius * 0.75F, center.y},
            Vector2{center.x + radius * 0.15F, center.y + radius * 0.58F}, width, color);
        break;
    case Action::MoveSocial:
        DrawCircleV(Vector2{center.x - radius * 0.52F, center.y}, radius * 0.24F, color);
        DrawCircleV(Vector2{center.x + radius * 0.52F, center.y}, radius * 0.24F, color);
        DrawLineEx(Vector2{center.x - radius * 0.28F, center.y},
            Vector2{center.x + radius * 0.28F, center.y}, width, color);
        break;
    case Action::Harvest:
        // Pickaxe glyph remains visible over green resources.
        DrawLineEx(Vector2{center.x - radius * 0.48F, center.y + radius * 0.72F},
            Vector2{center.x + radius * 0.28F, center.y - radius * 0.42F}, width, color);
        DrawLineEx(Vector2{center.x - radius * 0.46F, center.y - radius * 0.42F},
            Vector2{center.x + radius * 0.72F, center.y - radius * 0.08F}, width, color);
        break;
    case Action::Share:
        DrawCircleLines(static_cast<int>(center.x - radius * 0.56F),
            static_cast<int>(center.y), radius * 0.27F, color);
        DrawCircleLines(static_cast<int>(center.x + radius * 0.56F),
            static_cast<int>(center.y), radius * 0.27F, color);
        DrawLineEx(Vector2{center.x - radius * 0.28F, center.y},
            Vector2{center.x + radius * 0.28F, center.y}, width, color);
        break;
    case Action::Signal:
        DrawCircleLines(static_cast<int>(center.x), static_cast<int>(center.y),
            radius * 0.46F, color);
        DrawCircleLines(static_cast<int>(center.x), static_cast<int>(center.y),
            radius * 0.88F, color);
        break;
    case Action::Reproduce:
        DrawLineEx(Vector2{center.x, center.y - radius},
            Vector2{center.x + radius, center.y}, width, color);
        DrawLineEx(Vector2{center.x + radius, center.y},
            Vector2{center.x, center.y + radius}, width, color);
        DrawLineEx(Vector2{center.x, center.y + radius},
            Vector2{center.x - radius, center.y}, width, color);
        DrawLineEx(Vector2{center.x - radius, center.y},
            Vector2{center.x, center.y - radius}, width, color);
        break;
    case Action::Flee:
        for (int offset = -1; offset <= 1; offset += 2) {
            const float shift = static_cast<float>(offset) * radius * 0.28F;
            DrawLineEx(Vector2{center.x - radius * 0.75F + shift, center.y - radius * 0.62F},
                Vector2{center.x + shift, center.y}, width, color);
            DrawLineEx(Vector2{center.x + shift, center.y},
                Vector2{center.x - radius * 0.75F + shift, center.y + radius * 0.62F}, width, color);
        }
        break;
    case Action::Rest:
        DrawRectangleLinesEx(Rectangle{
            center.x - radius * 0.56F,
            center.y - radius * 0.56F,
            radius * 1.12F,
            radius * 1.12F
        }, width, color);
        break;
    default:
        break;
    }
}

void draw_action_glyph(
    Action action,
    Vector2 center,
    float radius_pixels,
    const Camera2D& camera,
    float alpha
) {
    if (action_index(action) < 0 || alpha <= 0.01F) {
        return;
    }
    const float inverse_zoom = 1.0F / std::max(camera.zoom, 0.001F);
    const float radius = radius_pixels * inverse_zoom;
    const float shadow_width = 2.6F * inverse_zoom;
    const float color_width = 1.25F * inverse_zoom;
    const unsigned char opacity = static_cast<unsigned char>(
        std::clamp(alpha * 255.0F, 0.0F, 255.0F)
    );
    draw_action_glyph_layer(
        action,
        center,
        radius + 1.1F * inverse_zoom,
        shadow_width,
        Color{2, 4, 7, static_cast<unsigned char>(opacity * 0.78F)}
    );
    draw_action_glyph_layer(
        action,
        center,
        radius,
        color_width,
        behavior_color(action, opacity)
    );
}

struct BehaviorWeights {
    float actions = 0.0F;
    float groups = 0.0F;
};

BehaviorWeights resolve_behavior_weights(
    BehaviorOverlayMode mode,
    const RenderDetail& detail
) {
    switch (mode) {
    case BehaviorOverlayMode::Off:
        return {};
    case BehaviorOverlayMode::Actions:
        return BehaviorWeights{1.0F, 0.0F};
    case BehaviorOverlayMode::Groups:
        return BehaviorWeights{0.0F, 1.0F};
    case BehaviorOverlayMode::Combined:
        return BehaviorWeights{1.0F, 1.0F};
    case BehaviorOverlayMode::Auto:
        break;
    }

    // Group flow is most useful at macro/medium scales. Action glyphs gain
    // weight as actual agents become readable, but remain aggregated until
    // micro detail is available.
    return BehaviorWeights{
        clamp01(0.30F * detail.density_weight +
            0.92F * detail.agent_weight +
            0.30F * detail.micro_weight),
        clamp01(0.86F * detail.density_weight +
            0.60F * detail.agent_weight -
            0.52F * detail.micro_weight)
    };
}

struct ActionActivityCell {
    std::array<float, 8> weights{};
    float sum_x = 0.0F;
    float sum_y = 0.0F;
    float total = 0.0F;
    std::uint32_t samples = 0;
};

void draw_action_activity_field(
    const Frame& frame,
    const Camera2D& camera,
    float weight
) {
    weight = clamp01(weight);
    if (weight < 0.08F || frame.entities.empty()) {
        return;
    }

    constexpr int columns = 24;
    constexpr int rows = 15;
    constexpr int count = columns * rows;
    static thread_local std::array<ActionActivityCell, count> cells{};
    cells.fill(ActionActivityCell{});

    const float world_width = std::max(frame.layout.world_width, 1.0F);
    const float world_height = std::max(frame.layout.world_height, 1.0F);

    for (const EntitySample& entity : frame.entities) {
        if (!valid_entity_sample(entity)) {
            continue;
        }
        const Action action = static_cast<Action>(entity.action);
        const int index = action_index(action);
        if (index < 0 || action == Action::Rest) {
            continue;
        }
        const int column = std::clamp(
            static_cast<int>(entity.x / world_width * columns), 0, columns - 1);
        const int row = std::clamp(
            static_cast<int>(entity.y / world_height * rows), 0, rows - 1);
        ActionActivityCell& cell = cells[static_cast<std::size_t>(row * columns + column)];
        const bool movement = action == Action::MoveResource ||
            action == Action::MoveSocial || action == Action::Flee;
        const float sample_weight = entity.action_success != 0
            ? 2.4F
            : movement ? 0.58F : 0.22F;
        cell.weights[static_cast<std::size_t>(index)] += sample_weight;
        cell.total += sample_weight;
        cell.sum_x += entity.x * sample_weight;
        cell.sum_y += entity.y * sample_weight;
        ++cell.samples;
    }

    struct Candidate {
        int index = 0;
        Action action = Action::Rest;
        float score = 0.0F;
        float dominance = 0.0F;
    };
    std::vector<Candidate> candidates;
    candidates.reserve(count);

    for (int index = 0; index < count; ++index) {
        const ActionActivityCell& cell = cells[static_cast<std::size_t>(index)];
        if (cell.total < 3.0F || cell.samples < 3U) {
            continue;
        }
        int dominant_index = 0;
        for (int action = 1; action < 8; ++action) {
            if (cell.weights[static_cast<std::size_t>(action)] >
                cell.weights[static_cast<std::size_t>(dominant_index)]) {
                dominant_index = action;
            }
        }
        const float dominant_weight = cell.weights[static_cast<std::size_t>(dominant_index)];
        const float dominance = dominant_weight / std::max(cell.total, 1.0e-5F);
        if (dominance < 0.28F) {
            continue;
        }
        const float score = std::log1p(cell.total) * (0.55F + dominance);
        candidates.push_back(Candidate{
            index,
            static_cast<Action>(dominant_index),
            score,
            dominance
        });
    }

    std::sort(candidates.begin(), candidates.end(),
        [](const Candidate& left, const Candidate& right) {
            return left.score > right.score;
        });
    const std::size_t budget = static_cast<std::size_t>(
        lerp_value(28.0F, 84.0F, weight)
    );
    if (candidates.size() > budget) {
        candidates.resize(budget);
    }

    for (const Candidate& candidate : candidates) {
        const ActionActivityCell& cell = cells[static_cast<std::size_t>(candidate.index)];
        const Vector2 center{
            cell.sum_x / std::max(cell.total, 1.0e-5F),
            cell.sum_y / std::max(cell.total, 1.0e-5F)
        };
        const float radius_pixels = std::clamp(
            4.0F + 1.45F * std::log1p(cell.total), 5.0F, 11.5F);
        draw_action_glyph(
            candidate.action,
            center,
            radius_pixels,
            camera,
            weight * (0.30F + 0.62F * candidate.dominance)
        );
    }
}

void draw_group_behavior_overlay(
    const std::vector<GroupBehaviorSummary>& groups,
    const Camera2D& camera,
    float weight
) {
    weight = clamp01(weight);
    if (weight < 0.08F || groups.empty()) {
        return;
    }

    struct Candidate {
        const GroupBehaviorSummary* group = nullptr;
        float score = 0.0F;
    };
    std::vector<Candidate> candidates;
    candidates.reserve(groups.size());

    for (const GroupBehaviorSummary& group : groups) {
        if (group.members < 8U) {
            continue;
        }
        const float behavior_strength = std::max(
            group.coherence,
            group.dominant_action_fraction * group.active_fraction
        );
        if (behavior_strength < 0.055F) {
            continue;
        }
        const float score = std::log1p(static_cast<float>(group.members)) *
            (0.32F + group.coherence +
             0.58F * group.dominant_action_fraction * group.active_fraction);
        candidates.push_back(Candidate{&group, score});
    }

    std::sort(candidates.begin(), candidates.end(),
        [](const Candidate& left, const Candidate& right) {
            return left.score > right.score;
        });
    const std::size_t budget = static_cast<std::size_t>(
        lerp_value(14.0F, 42.0F, weight)
    );
    if (candidates.size() > budget) {
        candidates.resize(budget);
    }

    const float inverse_zoom = 1.0F / std::max(camera.zoom, 0.001F);
    for (const Candidate& candidate : candidates) {
        const GroupBehaviorSummary& group = *candidate.group;
        const Vector2 center{group.x, group.y};
        const float speed = std::sqrt(
            group.mean_vx * group.mean_vx + group.mean_vy * group.mean_vy
        );
        const float member_curve = std::clamp(
            std::log1p(static_cast<float>(group.members)) / 8.0F,
            0.0F,
            1.0F
        );
        const float opacity = weight * (0.24F +
            0.48F * group.coherence +
            0.20F * group.active_fraction);
        Color group_color = color_for_group_id(
            group.group_id,
            static_cast<unsigned char>(std::clamp(opacity * 255.0F, 0.0F, 235.0F))
        );

        if (finite_value(speed) && speed > 1.0e-5F && group.coherence > 0.045F) {
            const float direction_x = group.mean_vx / speed;
            const float direction_y = group.mean_vy / speed;
            const float length_pixels = std::clamp(
                10.0F + 28.0F * group.coherence + 10.0F * member_curve,
                10.0F,
                48.0F
            );
            const float length = length_pixels * inverse_zoom;
            const Vector2 tail{
                center.x - direction_x * length * 0.42F,
                center.y - direction_y * length * 0.42F
            };
            const Vector2 head{
                center.x + direction_x * length * 0.58F,
                center.y + direction_y * length * 0.58F
            };
            const float width = (1.2F + 2.4F * member_curve) * inverse_zoom;
            DrawLineEx(tail, head, width + 2.2F * inverse_zoom,
                Fade(BLACK, opacity * 0.72F));
            DrawLineEx(tail, head, width, group_color);

            const float side_x = -direction_y;
            const float side_y = direction_x;
            const float head_length = (4.5F + 4.5F * member_curve) * inverse_zoom;
            const float head_width = (2.8F + 3.0F * member_curve) * inverse_zoom;
            DrawTriangle(
                head,
                Vector2{
                    head.x - direction_x * head_length + side_x * head_width,
                    head.y - direction_y * head_length + side_y * head_width
                },
                Vector2{
                    head.x - direction_x * head_length - side_x * head_width,
                    head.y - direction_y * head_length - side_y * head_width
                },
                group_color
            );

            if (group.dominant_action != Action::Rest &&
                group.dominant_action_fraction > 0.13F) {
                const Vector2 badge{
                    head.x + direction_x * 4.0F * inverse_zoom,
                    head.y + direction_y * 4.0F * inverse_zoom
                };
                draw_action_glyph(
                    group.dominant_action,
                    badge,
                    4.5F + 3.5F * group.dominant_action_fraction,
                    camera,
                    opacity * (0.58F + 0.42F * group.dominant_action_fraction)
                );
            }
        } else {
            // Non-coherent groups are represented by a compact activity bar,
            // not a large territory circle.
            const float half = (4.0F + 7.0F * member_curve) * inverse_zoom;
            const float width = (1.2F + 1.8F * member_curve) * inverse_zoom;
            DrawLineEx(
                Vector2{center.x - half, center.y},
                Vector2{center.x + half, center.y},
                width + 2.0F * inverse_zoom,
                Fade(BLACK, opacity * 0.70F)
            );
            DrawLineEx(
                Vector2{center.x - half, center.y},
                Vector2{center.x + half, center.y},
                width,
                group_color
            );
            if (group.dominant_action != Action::Rest &&
                group.dominant_action_fraction > 0.16F) {
                draw_action_glyph(
                    group.dominant_action,
                    center,
                    4.5F + 2.8F * group.dominant_action_fraction,
                    camera,
                    opacity
                );
            }
        }
    }
}

}  // namespace

RenderDetail resolve_render_detail(
    const Frame& frame,
    const Camera2D& camera,
    Rectangle viewport,
    LodMode mode
) {
    RenderDetail detail{};
    detail.estimated_visible = estimate_visible_entities(frame, camera, viewport);
    const double screen_area = std::max(
        static_cast<double>(viewport.width) * static_cast<double>(viewport.height),
        1.0
    );
    detail.projected_spacing = static_cast<float>(std::sqrt(
        screen_area / std::max(detail.estimated_visible, 1.0)
    ));

    if (mode == LodMode::ForceMacro) {
        detail.density_weight = 1.0F;
        detail.agent_weight = 0.08F;
        detail.micro_weight = 0.0F;
        detail.flow_weight = 1.0F;
        detail.environment_detail = 0.0F;
        detail.dominant = RenderLod::Macro;
        return detail;
    }
    if (mode == LodMode::ForceMedium) {
        detail.density_weight = 0.28F;
        detail.agent_weight = 1.0F;
        detail.micro_weight = 0.12F;
        detail.flow_weight = 0.38F;
        detail.environment_detail = 0.52F;
        detail.dominant = RenderLod::Medium;
        return detail;
    }
    if (mode == LodMode::ForceMicro) {
        detail.density_weight = 0.0F;
        detail.agent_weight = 1.0F;
        detail.micro_weight = 1.0F;
        detail.flow_weight = 0.0F;
        detail.environment_detail = 1.0F;
        detail.dominant = RenderLod::Micro;
        return detail;
    }

    // Screen-space spacing is continuous as the camera zoom changes. Each
    // visual layer derives its own weight from it, avoiding a hard 1.0/1.1
    // mode boundary while keeping the familiar Macro/Medium/Micro label.
    const float spacing = detail.projected_spacing;
    // v9 keeps the density layer dominant for longer. Real agents enter only
    // when a representative can occupy roughly a 7+ pixel footprint, which
    // prevents the 0.9--1.1 zoom range from becoming a full-screen confetti
    // field. All curves overlap, so this remains a natural screen-density
    // response rather than a timed cross-fade.
    detail.density_weight = 1.0F - smooth_range(4.0F, 17.0F, spacing);
    detail.agent_weight = smooth_range(5.2F, 14.5F, spacing);
    detail.micro_weight = smooth_range(18.0F, 42.0F, spacing);
    detail.flow_weight = 1.0F - smooth_range(10.0F, 31.0F, spacing);
    detail.environment_detail = smooth_range(6.0F, 30.0F, spacing);

    if (detail.micro_weight >= 0.55F) {
        detail.dominant = RenderLod::Micro;
    } else if (detail.agent_weight >= 0.36F) {
        detail.dominant = RenderLod::Medium;
    } else {
        detail.dominant = RenderLod::Macro;
    }
    return detail;
}

RenderLod resolve_render_lod(
    const Frame& frame,
    const Camera2D& camera,
    Rectangle viewport,
    LodMode mode
) {
    return resolve_render_detail(frame, camera, viewport, mode).dominant;
}

const char* render_lod_name(RenderLod lod) noexcept {
    switch (lod) {
    case RenderLod::Macro:
        return "macro resources + group behavior";
    case RenderLod::Medium:
        return "medium agents + activity";
    case RenderLod::Micro:
        return "micro individual agents";
    }
    return "unknown";
}

const char* lod_mode_name(LodMode mode) noexcept {
    switch (mode) {
    case LodMode::Auto:
        return "auto";
    case LodMode::ForceMacro:
        return "forced macro";
    case LodMode::ForceMedium:
        return "forced medium";
    case LodMode::ForceMicro:
        return "forced micro";
    }
    return "unknown";
}

const char* environment_filter_name(EnvironmentFilterMode mode) noexcept {
    switch (mode) {
    case EnvironmentFilterMode::Instant:
        return "instant";
    case EnvironmentFilterMode::Responsive:
        return "responsive";
    case EnvironmentFilterMode::Stable:
        return "stable";
    }
    return "unknown";
}

const char* environment_view_name(EnvironmentViewMode mode) noexcept {
    switch (mode) {
    case EnvironmentViewMode::Composite:
        return "composite";
    case EnvironmentViewMode::ResourceAbsolute:
        return "resource";
    case EnvironmentViewMode::ResourceGradient:
        return "gradient";
    case EnvironmentViewMode::Hazard:
        return "hazard";
    case EnvironmentViewMode::PopulationDensity:
        return "population";
    case EnvironmentViewMode::ResourceDelta:
        return "resource-delta";
    }
    return "unknown";
}

const char* behavior_overlay_name(BehaviorOverlayMode mode) noexcept {
    switch (mode) {
    case BehaviorOverlayMode::Auto:
        return "auto";
    case BehaviorOverlayMode::Off:
        return "off";
    case BehaviorOverlayMode::Actions:
        return "actions";
    case BehaviorOverlayMode::Groups:
        return "groups";
    case BehaviorOverlayMode::Combined:
        return "combined";
    }
    return "unknown";
}

Color color_for_entity(const EntitySample& entity, float max_energy) {
    const float energy = clamp01(
        entity.energy / std::max(max_energy, 1.0e-6F)
    );
    const float integrity = clamp01(entity.integrity);

    if (entity.group_id == 0) {
        return Color{
            static_cast<unsigned char>(92.0F + 42.0F * energy),
            static_cast<unsigned char>(154.0F + 58.0F * integrity),
            static_cast<unsigned char>(188.0F + 54.0F * energy),
            230
        };
    }

    const std::uint64_t hash = mix_id(entity.group_id);
    const float hue = static_cast<float>(hash & 0xFFFFU) / 65535.0F;
    const float saturation = 0.72F + 0.20F * integrity;
    const float value = 0.86F + 0.14F * energy;
    return hsv_color(hue, saturation, value, 255);
}

WorldRenderer::~WorldRenderer() {
    if (heatmap_.id != 0) {
        UnloadTexture(heatmap_);
    }
}

const GroupBehaviorSummary* WorldRenderer::group_behavior(
    std::uint64_t group_id
) const noexcept {
    if (group_id == 0) {
        return nullptr;
    }
    const auto iterator = std::find_if(
        group_behaviors_.begin(),
        group_behaviors_.end(),
        [group_id](const GroupBehaviorSummary& group) {
            return group.group_id == group_id;
        }
    );
    return iterator == group_behaviors_.end() ? nullptr : &*iterator;
}

EnvironmentProbe WorldRenderer::probe_environment(
    const Frame& frame,
    float world_x,
    float world_y,
    int resource_channel
) const noexcept {
    EnvironmentProbe probe{};
    if (!finite_value(world_x) || !finite_value(world_y) ||
        frame.layout.grid_x == 0 || frame.layout.grid_y == 0) {
        return probe;
    }

    const std::size_t cell_count = frame.cell_count();
    if (frame.resources.size() < cell_count * 4U ||
        frame.hazard.size() < cell_count) {
        return probe;
    }

    const float world_width = std::max(frame.layout.world_width, 1.0F);
    const float world_height = std::max(frame.layout.world_height, 1.0F);
    const float wrapped_x = std::fmod(std::fmod(world_x, world_width) + world_width, world_width);
    const float wrapped_y = std::fmod(std::fmod(world_y, world_height) + world_height, world_height);
    const std::uint32_t cell_x = std::min<std::uint32_t>(
        static_cast<std::uint32_t>(wrapped_x / world_width * frame.layout.grid_x),
        frame.layout.grid_x - 1U
    );
    const std::uint32_t cell_y = std::min<std::uint32_t>(
        static_cast<std::uint32_t>(wrapped_y / world_height * frame.layout.grid_y),
        frame.layout.grid_y - 1U
    );
    const auto index_of = [&frame](std::uint32_t x, std::uint32_t y) {
        return static_cast<std::size_t>(y) * frame.layout.grid_x + x;
    };
    const std::size_t index = index_of(cell_x, cell_y);
    probe.valid = true;
    probe.cell_x = cell_x;
    probe.cell_y = cell_y;
    for (std::size_t channel = 0; channel < 4U; ++channel) {
        probe.resources[channel] = frame.resources[channel * cell_count + index];
    }
    probe.hazard = frame.hazard[index];

    const int channel = std::clamp(resource_channel, 0, 3);
    const std::uint32_t left = cell_x == 0 ? frame.layout.grid_x - 1U : cell_x - 1U;
    const std::uint32_t right = cell_x + 1U == frame.layout.grid_x ? 0U : cell_x + 1U;
    const std::uint32_t up = cell_y == 0 ? frame.layout.grid_y - 1U : cell_y - 1U;
    const std::uint32_t down = cell_y + 1U == frame.layout.grid_y ? 0U : cell_y + 1U;
    const std::size_t offset = static_cast<std::size_t>(channel) * cell_count;
    probe.gradient_x = 0.5F * (
        frame.resources[offset + index_of(right, cell_y)] -
        frame.resources[offset + index_of(left, cell_y)]
    );
    probe.gradient_y = 0.5F * (
        frame.resources[offset + index_of(cell_x, down)] -
        frame.resources[offset + index_of(cell_x, up)]
    );
    probe.gradient_magnitude = std::sqrt(
        probe.gradient_x * probe.gradient_x +
        probe.gradient_y * probe.gradient_y
    );
    return probe;
}

void WorldRenderer::ensure_texture(std::uint32_t grid_x, std::uint32_t grid_y) {
    if (heatmap_.id != 0 && grid_x_ == grid_x && grid_y_ == grid_y) {
        return;
    }

    if (heatmap_.id != 0) {
        UnloadTexture(heatmap_);
        heatmap_ = Texture2D{};
    }

    grid_x_ = grid_x;
    grid_y_ = grid_y;
    pixels_.assign(
        static_cast<std::size_t>(grid_x_) * static_cast<std::size_t>(grid_y_),
        BLACK
    );

    for (auto& resource : filtered_resources_) {
        resource.clear();
    }
    filtered_hazard_.clear();
    for (auto& resource : previous_resources_) {
        resource.clear();
    }
    previous_hazard_.clear();
    resource_scale_initialized_.fill(false);
    resource_adaptive_initialized_.fill(false);
    last_heatmap_tick_ = 0;

    Image image = GenImageColor(
        static_cast<int>(grid_x_),
        static_cast<int>(grid_y_),
        BLACK
    );
    heatmap_ = LoadTextureFromImage(image);
    UnloadImage(image);
    SetTextureFilter(heatmap_, TEXTURE_FILTER_POINT);
    texture_filter_ = TEXTURE_FILTER_POINT;
}

void WorldRenderer::observe_frame(const Frame& frame) {
    diagnostics_ = FrameDiagnostics{};

    const bool first_observation = !has_observed_frame_;

    previous_positions_.clear();
    previous_positions_.swap(current_positions_);
    current_positions_.clear();
    current_positions_.reserve(frame.entities.size() * 5 / 4 + 1);

    struct Candidate {
        std::uint64_t entity_id;
        float x;
        float y;
    };

    std::vector<Candidate> births;
    std::vector<Candidate> deaths;
    std::vector<Candidate> harvests;
    std::vector<Candidate> reproductions;

    births.reserve(512);
    deaths.reserve(512);
    harvests.reserve(1024);
    reproductions.reserve(512);

    struct GroupAccumulator {
        std::size_t members = 0;
        double sum_cos_x = 0.0;
        double sum_sin_x = 0.0;
        double sum_cos_y = 0.0;
        double sum_sin_y = 0.0;
        double sum_vx = 0.0;
        double sum_vy = 0.0;
        double sum_speed = 0.0;
        std::size_t active = 0;
        std::array<double, 8> action_weights{};
        double total_action_weight = 0.0;
    };

    std::unordered_map<std::uint64_t, GroupAccumulator> group_accumulators;
    group_accumulators.reserve(frame.entities.size() / 32U + 1U);

    const double two_pi = 6.28318530717958647692;
    const double world_width = std::max<double>(frame.layout.world_width, 1.0);
    const double world_height = std::max<double>(frame.layout.world_height, 1.0);
    double speed_sum = 0.0;

    for (const EntitySample& entity : frame.entities) {
        if (!valid_entity_sample(entity)) {
            continue;
        }

        current_positions_.emplace(
            entity.entity_id,
            PositionSample{entity.x, entity.y, entity.vx, entity.vy}
        );

        const float speed = std::sqrt(entity.vx * entity.vx + entity.vy * entity.vy);
        speed_sum += speed;
        if (speed > 0.01F) {
            ++diagnostics_.moving_entities;
        }

        const Action action = static_cast<Action>(entity.action);
        switch (action) {
        case Action::Rest:
            ++diagnostics_.rests;
            break;
        case Action::MoveResource:
            ++diagnostics_.move_resource;
            break;
        case Action::MoveSocial:
            ++diagnostics_.move_social;
            break;
        case Action::Flee:
            ++diagnostics_.flees;
            break;
        default:
            break;
        }
        if (entity.action_success != 0) {
            ++diagnostics_.successful_actions;
        }

        if (entity.group_id != 0) {
            GroupAccumulator& group = group_accumulators[entity.group_id];
            ++group.members;
            const double angle_x = two_pi * static_cast<double>(entity.x) / world_width;
            const double angle_y = two_pi * static_cast<double>(entity.y) / world_height;
            group.sum_cos_x += std::cos(angle_x);
            group.sum_sin_x += std::sin(angle_x);
            group.sum_cos_y += std::cos(angle_y);
            group.sum_sin_y += std::sin(angle_y);
            group.sum_vx += entity.vx;
            group.sum_vy += entity.vy;
            group.sum_speed += speed;
            if (action != Action::Rest && action != Action::None) {
                ++group.active;
            }
            const int index = action_index(action);
            if (index >= 0) {
                const double action_weight = entity.action_success != 0 ? 2.5 :
                    (action == Action::MoveResource || action == Action::MoveSocial ||
                     action == Action::Flee ? 0.72 : 0.30);
                group.action_weights[static_cast<std::size_t>(index)] += action_weight;
                group.total_action_weight += action_weight;
            }
        }

        if (!first_observation &&
            previous_positions_.find(entity.entity_id) == previous_positions_.end()) {
            ++diagnostics_.births;
            births.push_back(Candidate{entity.entity_id, entity.x, entity.y});
        }

        if (entity.action_success != 0) {
            switch (action) {
            case Action::Harvest:
                ++diagnostics_.harvests;
                harvests.push_back(Candidate{entity.entity_id, entity.x, entity.y});
                break;
            case Action::Reproduce:
                ++diagnostics_.reproductions;
                reproductions.push_back(Candidate{entity.entity_id, entity.x, entity.y});
                break;
            case Action::Share:
                ++diagnostics_.shares;
                break;
            case Action::Signal:
                ++diagnostics_.signals;
                break;
            default:
                break;
            }
        }
    }

    if (!frame.entities.empty()) {
        diagnostics_.mean_speed = static_cast<float>(
            speed_sum / static_cast<double>(frame.entities.size())
        );
    }

    group_behaviors_.clear();
    group_behaviors_.reserve(group_accumulators.size());
    for (const auto& [group_id, aggregate] : group_accumulators) {
        if (aggregate.members == 0) {
            continue;
        }
        auto circular_position = [two_pi](double sine, double cosine, double extent) {
            double angle = std::atan2(sine, cosine);
            if (angle < 0.0) {
                angle += two_pi;
            }
            return static_cast<float>(angle / two_pi * extent);
        };

        int dominant_index = 0;
        for (int index = 1; index < 8; ++index) {
            if (aggregate.action_weights[static_cast<std::size_t>(index)] >
                aggregate.action_weights[static_cast<std::size_t>(dominant_index)]) {
                dominant_index = index;
            }
        }
        const double resultant_speed = std::sqrt(
            aggregate.sum_vx * aggregate.sum_vx +
            aggregate.sum_vy * aggregate.sum_vy
        );
        const float coherence = aggregate.sum_speed > 1.0e-8
            ? static_cast<float>(resultant_speed / aggregate.sum_speed)
            : 0.0F;
        const float dominant_fraction = aggregate.total_action_weight > 1.0e-8
            ? static_cast<float>(
                aggregate.action_weights[static_cast<std::size_t>(dominant_index)] /
                aggregate.total_action_weight
            )
            : 0.0F;

        group_behaviors_.push_back(GroupBehaviorSummary{
            group_id,
            aggregate.members,
            circular_position(aggregate.sum_sin_x, aggregate.sum_cos_x, world_width),
            circular_position(aggregate.sum_sin_y, aggregate.sum_cos_y, world_height),
            static_cast<float>(aggregate.sum_vx / static_cast<double>(aggregate.members)),
            static_cast<float>(aggregate.sum_vy / static_cast<double>(aggregate.members)),
            clamp01(coherence),
            0.0F,
            0.0F,
            0.0F,
            0.0F,
            static_cast<float>(aggregate.active) /
                static_cast<float>(aggregate.members),
            static_cast<Action>(dominant_index),
            clamp01(dominant_fraction)
        });
    }

    std::sort(group_behaviors_.begin(), group_behaviors_.end(),
        [](const GroupBehaviorSummary& left, const GroupBehaviorSummary& right) {
            if (left.members != right.members) {
                return left.members > right.members;
            }
            return left.group_id < right.group_id;
        });

    std::unordered_map<std::uint64_t, std::size_t> group_indices;
    group_indices.reserve(group_behaviors_.size() * 5U / 4U + 1U);
    std::vector<double> covariance_xx(group_behaviors_.size(), 0.0);
    std::vector<double> covariance_yy(group_behaviors_.size(), 0.0);
    std::vector<double> covariance_xy(group_behaviors_.size(), 0.0);
    for (std::size_t index = 0; index < group_behaviors_.size(); ++index) {
        group_indices.emplace(group_behaviors_[index].group_id, index);
    }
    for (const EntitySample& entity : frame.entities) {
        if (!valid_entity_sample(entity) || entity.group_id == 0) {
            continue;
        }
        const auto iterator = group_indices.find(entity.group_id);
        if (iterator == group_indices.end()) {
            continue;
        }
        const GroupBehaviorSummary& group = group_behaviors_[iterator->second];
        const double dx = wrapped_delta(entity.x - group.x, frame.layout.world_width);
        const double dy = wrapped_delta(entity.y - group.y, frame.layout.world_height);
        covariance_xx[iterator->second] += dx * dx;
        covariance_yy[iterator->second] += dy * dy;
        covariance_xy[iterator->second] += dx * dy;
    }
    for (std::size_t index = 0; index < group_behaviors_.size(); ++index) {
        GroupBehaviorSummary& group = group_behaviors_[index];
        const double members = static_cast<double>(
            std::max<std::size_t>(group.members, 1U)
        );
        const double xx = covariance_xx[index] / members;
        const double yy = covariance_yy[index] / members;
        const double xy = covariance_xy[index] / members;
        const double trace = xx + yy;
        const double discriminant = std::sqrt(
            std::max(0.0, (xx - yy) * (xx - yy) + 4.0 * xy * xy)
        );
        const double lambda_major = std::max(0.0, 0.5 * (trace + discriminant));
        const double lambda_minor = std::max(0.0, 0.5 * (trace - discriminant));
        group.spread = static_cast<float>(std::sqrt(std::max(trace, 0.0)));
        group.spread_major = static_cast<float>(std::sqrt(lambda_major));
        group.spread_minor = static_cast<float>(std::sqrt(lambda_minor));
        group.orientation = static_cast<float>(0.5 * std::atan2(2.0 * xy, xx - yy));
    }

    const std::uint64_t trail_period = frame.entities.size() > 100000U ? 8U : 4U;
    if (last_group_trail_tick_ == 0 ||
        frame.tick >= last_group_trail_tick_ + trail_period) {
        const std::size_t tracked_groups = std::min<std::size_t>(
            group_behaviors_.size(), 2048U
        );
        std::unordered_set<std::uint64_t> observed_groups;
        observed_groups.reserve(tracked_groups * 5U / 4U + 1U);
        for (std::size_t index = 0; index < tracked_groups; ++index) {
            const GroupBehaviorSummary& group = group_behaviors_[index];
            observed_groups.insert(group.group_id);
            auto& trail = group_trails_[group.group_id];
            if (trail.empty() ||
                frame.tick > trail.back().tick) {
                trail.push_back(GroupTrailPoint{
                    frame.tick,
                    group.x,
                    group.y,
                    group.members,
                    group.coherence,
                    group.dominant_action
                });
            }
            while (trail.size() > 56U) {
                trail.pop_front();
            }
        }
        std::erase_if(group_trails_, [&frame, &observed_groups](const auto& item) {
            const auto& trail = item.second;
            return trail.empty() ||
                (observed_groups.find(item.first) == observed_groups.end() &&
                 frame.tick > trail.back().tick + 512U);
        });
        last_group_trail_tick_ = frame.tick;
    }

    if (!first_observation) {
        for (const auto& [entity_id, position] : previous_positions_) {
            if (current_positions_.find(entity_id) == current_positions_.end()) {
                ++diagnostics_.deaths;
                deaths.push_back(Candidate{entity_id, position.x, position.y});
            }
        }
    }

    std::erase_if(
        event_markers_,
        [&frame](const EventMarker& marker) {
            return frame.tick < marker.tick ||
                frame.tick - marker.tick > event_ttl(marker.kind);
        }
    );

    auto append_sampled = [this, &frame](
        const std::vector<Candidate>& candidates,
        EventKind kind,
        std::size_t budget
    ) {
        if (candidates.empty() || budget == 0) {
            return;
        }

        const std::size_t stride = std::max<std::size_t>(
            1,
            (candidates.size() + budget - 1) / budget
        );
        std::size_t added = 0;

        for (const Candidate& candidate : candidates) {
            if (stride > 1 &&
                mix_id(candidate.entity_id ^ (frame.tick * 0x9e3779b97f4a7c15ULL)) % stride != 0) {
                continue;
            }

            event_markers_.push_back(EventMarker{
                candidate.entity_id,
                frame.tick,
                candidate.x,
                candidate.y,
                kind
            });
            if (++added >= budget) {
                break;
            }
        }
    };

    append_sampled(births, EventKind::Birth, 320);
    append_sampled(deaths, EventKind::Death, 320);
    append_sampled(harvests, EventKind::Harvest, 480);
    append_sampled(reproductions, EventKind::Reproduce, 240);

    constexpr std::size_t maximum_markers = 4096;
    if (event_markers_.size() > maximum_markers) {
        const std::size_t excess = event_markers_.size() - maximum_markers;
        event_markers_.erase(event_markers_.begin(), event_markers_.begin() + excess);
    }

    last_observed_tick_ = frame.tick;
    has_observed_frame_ = true;
}

void WorldRenderer::update_heatmap(
    const Frame& frame,
    const RenderDetail& detail,
    const RenderOptions& options
) {
    ensure_texture(frame.layout.grid_x, frame.layout.grid_y);

    const std::size_t cell_count = frame.cell_count();
    if (frame.resources.size() < cell_count * 4U ||
        frame.hazard.size() < cell_count) {
        return;
    }

    const int channel = std::clamp(options.resource_channel, 0, 3);
    const std::size_t offset = static_cast<std::size_t>(channel) * cell_count;

    if (!resource_scale_initialized_[channel]) {
        std::vector<float> scratch;
        scratch.reserve(cell_count);
        for (std::size_t index = 0; index < cell_count; ++index) {
            const float value = frame.resources[offset + index];
            if (finite_value(value)) {
                scratch.push_back(value);
            }
        }
        std::vector<float> low_scratch = scratch;
        resource_low_[channel] = quantile(low_scratch, 0.02F);
        resource_high_[channel] = quantile(scratch, 0.98F);
        if (resource_high_[channel] - resource_low_[channel] < 1.0e-5F) {
            resource_high_[channel] = resource_low_[channel] + 1.0F;
        }
        resource_scale_initialized_[channel] = true;
    }

    const float scale_low = resource_low_[channel];
    const float scale_span = std::max(
        resource_high_[channel] - resource_low_[channel],
        1.0e-5F
    );
    const std::uint64_t elapsed_ticks =
        last_heatmap_tick_ == 0 || frame.tick <= last_heatmap_tick_
            ? 1
            : frame.tick - last_heatmap_tick_;
    const FilterParameters parameters = filter_parameters(options.environment_filter);
    const float resource_alpha = effective_alpha(
        parameters.resource_alpha_per_tick,
        elapsed_ticks
    );
    const float hazard_alpha = effective_alpha(
        parameters.hazard_alpha_per_tick,
        elapsed_ticks
    );
    const float resource_max_step = std::max(
        scale_span * parameters.resource_max_step_fraction *
            static_cast<float>(std::clamp<std::uint64_t>(elapsed_ticks, 1, 16)),
        1.0e-6F
    );
    const float hazard_max_step = parameters.hazard_max_step *
        static_cast<float>(std::clamp<std::uint64_t>(elapsed_ticks, 1, 16));

    std::vector<float>& filtered_resource = filtered_resources_[channel];
    const bool resource_filter_initialized = filtered_resource.size() == cell_count;
    const bool hazard_filter_initialized = filtered_hazard_.size() == cell_count;
    if (!resource_filter_initialized) {
        filtered_resource.resize(cell_count);
    }
    if (!hazard_filter_initialized) {
        filtered_hazard_.resize(cell_count);
    }

    for (std::size_t index = 0; index < cell_count; ++index) {
        const float raw_resource = finite_value(frame.resources[offset + index])
            ? frame.resources[offset + index]
            : scale_low;
        const float raw_hazard = finite_value(frame.hazard[index])
            ? clamp01(frame.hazard[index])
            : 0.0F;

        if (!resource_filter_initialized ||
            options.environment_filter == EnvironmentFilterMode::Instant) {
            filtered_resource[index] = raw_resource;
        } else {
            filtered_resource[index] = filtered_step(
                filtered_resource[index],
                raw_resource,
                resource_alpha,
                resource_max_step
            );
        }

        if (!hazard_filter_initialized ||
            options.environment_filter == EnvironmentFilterMode::Instant) {
            filtered_hazard_[index] = raw_hazard;
        } else {
            filtered_hazard_[index] = filtered_step(
                filtered_hazard_[index],
                raw_hazard,
                hazard_alpha,
                hazard_max_step
            );
        }
    }

    static thread_local std::vector<float> density;
    static thread_local std::vector<float> density_coarse;
    static thread_local std::vector<float> density_medium;
    static thread_local std::vector<float> resource_coarse;
    static thread_local std::vector<float> resource_medium;
    static thread_local std::vector<float> hazard_coarse;
    static thread_local std::vector<float> hazard_medium;
    static thread_local std::vector<float> display_resource;
    static thread_local std::vector<float> display_hazard;
    static thread_local std::vector<float> display_density;
    static thread_local std::vector<float> scratch;
    static thread_local std::vector<float> scale_scratch;

    // Keep the initial scale as the absolute ecological reference, but also
    // maintain a slowly adapting local scale. The local scale reveals spatial
    // structure after global depletion without pretending that depleted cells
    // are fully replenished.
    scale_scratch.clear();
    scale_scratch.reserve(cell_count);
    for (const float value : filtered_resource) {
        if (finite_value(value)) {
            scale_scratch.push_back(value);
        }
    }
    std::vector<float> adaptive_low_scratch = scale_scratch;
    const float current_adaptive_low = quantile(adaptive_low_scratch, 0.06F);
    const float current_adaptive_high = quantile(scale_scratch, 0.94F);
    const float current_adaptive_span = std::max(
        current_adaptive_high - current_adaptive_low,
        0.0F
    );
    const float minimum_adaptive_span = std::max(
        current_adaptive_span * 0.55F,
        std::max(scale_span * 1.0e-5F, 1.0e-8F)
    );
    if (!resource_adaptive_initialized_[channel]) {
        resource_adaptive_low_[channel] = current_adaptive_low;
        resource_adaptive_high_[channel] = std::max(
            current_adaptive_high,
            current_adaptive_low + minimum_adaptive_span
        );
        resource_adaptive_initialized_[channel] = true;
    } else {
        const float adaptive_alpha = effective_alpha(0.012F, elapsed_ticks);
        resource_adaptive_low_[channel] = lerp_value(
            resource_adaptive_low_[channel],
            current_adaptive_low,
            adaptive_alpha
        );
        resource_adaptive_high_[channel] = lerp_value(
            resource_adaptive_high_[channel],
            std::max(current_adaptive_high, current_adaptive_low + minimum_adaptive_span),
            adaptive_alpha
        );
    }

    density.assign(cell_count, 0.0F);
    density_coarse.assign(cell_count, 0.0F);
    density_medium.assign(cell_count, 0.0F);
    display_density.assign(cell_count, 0.0F);

    const float world_width = std::max(frame.layout.world_width, 1.0F);
    const float world_height = std::max(frame.layout.world_height, 1.0F);
    const bool density_required = options.show_population_density ||
        options.environment_view == EnvironmentViewMode::PopulationDensity;

    if (density_required) {
        for (const EntitySample& entity : frame.entities) {
            if (!valid_entity_sample(entity)) {
                continue;
            }
            const int x = std::clamp(
                static_cast<int>(entity.x / world_width * frame.layout.grid_x),
                0,
                static_cast<int>(frame.layout.grid_x) - 1
            );
            const int y = std::clamp(
                static_cast<int>(entity.y / world_height * frame.layout.grid_y),
                0,
                static_cast<int>(frame.layout.grid_y) - 1
            );
            density[static_cast<std::size_t>(y) * frame.layout.grid_x + x] += 1.0F;
        }
        blur_grid(
            density,
            density_coarse,
            scratch,
            frame.layout.grid_x,
            frame.layout.grid_y,
            4
        );
        blur_grid(
            density,
            density_medium,
            scratch,
            frame.layout.grid_x,
            frame.layout.grid_y,
            2
        );
        const float density_fine_weight = smooth_range(
            0.18F,
            0.82F,
            detail.environment_detail
        );
        for (std::size_t index = 0; index < cell_count; ++index) {
            display_density[index] = lerp_value(
                density_coarse[index],
                density_medium[index],
                density_fine_weight
            );
        }
    }

    blur_grid(
        filtered_resource,
        resource_coarse,
        scratch,
        frame.layout.grid_x,
        frame.layout.grid_y,
        2
    );
    blur_grid(
        filtered_resource,
        resource_medium,
        scratch,
        frame.layout.grid_x,
        frame.layout.grid_y,
        1
    );
    blur_grid(
        filtered_hazard_,
        hazard_coarse,
        scratch,
        frame.layout.grid_x,
        frame.layout.grid_y,
        2
    );
    blur_grid(
        filtered_hazard_,
        hazard_medium,
        scratch,
        frame.layout.grid_x,
        frame.layout.grid_y,
        1
    );

    display_resource.resize(cell_count);
    display_hazard.resize(cell_count);
    const float medium_weight = smooth_range(
        0.05F,
        0.66F,
        detail.environment_detail
    );
    const float fine_weight = smooth_range(
        0.58F,
        0.96F,
        detail.environment_detail
    );
    for (std::size_t index = 0; index < cell_count; ++index) {
        const float medium_resource = lerp_value(
            resource_coarse[index],
            resource_medium[index],
            medium_weight
        );
        const float medium_hazard = lerp_value(
            hazard_coarse[index],
            hazard_medium[index],
            medium_weight
        );
        display_resource[index] = lerp_value(
            medium_resource,
            filtered_resource[index],
            fine_weight
        );
        display_hazard[index] = lerp_value(
            medium_hazard,
            filtered_hazard_[index],
            fine_weight
        );
    }

    const float adaptive_low = resource_adaptive_low_[channel];
    const float adaptive_span = std::max(
        resource_adaptive_high_[channel] - resource_adaptive_low_[channel],
        minimum_adaptive_span
    );
    double absolute_presence_sum = 0.0;
    for (const float value : display_resource) {
        absolute_presence_sum += clamp01((value - scale_low) / scale_span);
    }
    const float absolute_presence = cell_count > 0
        ? static_cast<float>(absolute_presence_sum / static_cast<double>(cell_count))
        : 0.0F;
    const float depletion = 1.0F - smooth_range(0.035F, 0.32F, absolute_presence);
    float local_contrast_strength = lerp_value(0.13F, 0.48F, depletion);
    if (options.environment_view == EnvironmentViewMode::ResourceAbsolute) {
        local_contrast_strength = std::min(0.68F, local_contrast_strength + 0.18F);
    }

    float density_max = 1.0F;
    for (const float value : display_density) {
        density_max = std::max(density_max, value);
    }
    const float density_divisor = std::log1p(density_max);

    const bool has_previous_resource =
        previous_resources_[channel].size() == cell_count;
    const bool has_previous_hazard = previous_hazard_.size() == cell_count;

    double resource_sum = 0.0;
    double hazard_sum = 0.0;
    double change_sum = 0.0;
    const int width = static_cast<int>(frame.layout.grid_x);
    const int height = static_cast<int>(frame.layout.grid_y);

    for (int y = 0; y < height; ++y) {
        const int up = std::max(y - 1, 0);
        const int down = std::min(y + 1, height - 1);
        for (int x = 0; x < width; ++x) {
            const int left = std::max(x - 1, 0);
            const int right = std::min(x + 1, width - 1);
            const std::size_t index = static_cast<std::size_t>(y) * frame.layout.grid_x +
                static_cast<std::size_t>(x);
            const std::size_t left_index = static_cast<std::size_t>(y) * frame.layout.grid_x +
                static_cast<std::size_t>(left);
            const std::size_t right_index = static_cast<std::size_t>(y) * frame.layout.grid_x +
                static_cast<std::size_t>(right);
            const std::size_t up_index = static_cast<std::size_t>(up) * frame.layout.grid_x +
                static_cast<std::size_t>(x);
            const std::size_t down_index = static_cast<std::size_t>(down) * frame.layout.grid_x +
                static_cast<std::size_t>(x);

            const float resource_value = display_resource[index];
            const float hazard_value = clamp01(display_hazard[index]);
            const float absolute_resource = clamp01(
                (resource_value - scale_low) / scale_span
            );
            const float local_resource = clamp01(
                (resource_value - adaptive_low) / adaptive_span
            );
            // Absolute abundance remains authoritative. Local contrast only
            // fills part of the unused perceptual range, so depleted worlds stay
            // visibly depleted while their remaining patches are still legible.
            const float normalized_resource = clamp01(
                absolute_resource +
                (1.0F - absolute_resource) *
                    smoothstep01(local_resource) * local_contrast_strength
            );
            const float population_density = density_divisor > 0.0F
                ? std::log1p(display_density[index]) / density_divisor
                : 0.0F;

            float resource_change = 0.0F;
            float hazard_change = 0.0F;
            if (has_previous_resource) {
                const float difference = filtered_resource[index] -
                    previous_resources_[channel][index];
                const float deadzone = scale_span * 0.0015F;
                if (std::abs(difference) > deadzone) {
                    resource_change = difference /
                        std::max(scale_span * 0.022F, 1.0e-5F);
                }
            }
            if (has_previous_hazard) {
                const float difference = clamp01(filtered_hazard_[index]) -
                    previous_hazard_[index];
                if (std::abs(difference) > 0.0015F) {
                    hazard_change = difference / 0.035F;
                }
            }

            // Gradients use the coarse resource field and adaptive span. This
            // suppresses single-cell direction noise and avoids the checkerboard
            // appearance seen in v8's HSV gradient view.
            const float gradient_x =
                (resource_coarse[right_index] - resource_coarse[left_index]) /
                adaptive_span * 1.65F;
            const float gradient_y =
                (resource_coarse[down_index] - resource_coarse[up_index]) /
                adaptive_span * 1.65F;
            const float hazard_edge = std::sqrt(
                std::pow(display_hazard[right_index] - display_hazard[left_index], 2.0F) +
                std::pow(display_hazard[down_index] - display_hazard[up_index], 2.0F)
            ) * 2.5F;

            pixels_[index] = heat_color(
                channel,
                normalized_resource,
                hazard_value,
                population_density,
                resource_change,
                hazard_change,
                gradient_x,
                gradient_y,
                hazard_edge,
                detail,
                options
            );

            resource_sum += absolute_resource;
            hazard_sum += hazard_value;
            change_sum += std::abs(std::clamp(resource_change, -1.0F, 1.0F)) +
                0.25 * std::abs(std::clamp(hazard_change, -1.0F, 1.0F));
        }
    }

    if (cell_count > 0) {
        diagnostics_.mean_resource = static_cast<float>(
            resource_sum / static_cast<double>(cell_count)
        );
        diagnostics_.mean_hazard = static_cast<float>(
            hazard_sum / static_cast<double>(cell_count)
        );
        diagnostics_.mean_environment_change = static_cast<float>(
            change_sum / static_cast<double>(cell_count)
        );
    }

    previous_resources_[channel] = filtered_resource;
    previous_hazard_ = filtered_hazard_;
    last_heatmap_tick_ = frame.tick;

    UpdateTexture(heatmap_, pixels_.data());
    const bool analytical_view =
        options.environment_view == EnvironmentViewMode::ResourceGradient ||
        options.environment_view == EnvironmentViewMode::Hazard ||
        options.environment_view == EnvironmentViewMode::PopulationDensity ||
        options.environment_view == EnvironmentViewMode::ResourceDelta;
    const int requested_filter = !analytical_view && detail.environment_detail >= 0.92F
        ? TEXTURE_FILTER_POINT
        : TEXTURE_FILTER_BILINEAR;
    if (texture_filter_ != requested_filter) {
        SetTextureFilter(heatmap_, requested_filter);
        texture_filter_ = requested_filter;
    }
}

void WorldRenderer::draw_group_history_overlay(
    const Frame& frame,
    const Camera2D& camera,
    const RenderDetail& detail,
    const RenderOptions& options,
    std::uint64_t selected_group_id,
    float weight
) const {
    weight = clamp01(weight);
    if (!options.show_group_trails || weight < 0.035F || group_behaviors_.empty()) {
        return;
    }

    const float inverse_zoom = 1.0F / std::max(camera.zoom, 0.001F);
    const std::size_t ordinary_budget = static_cast<std::size_t>(
        lerp_value(8.0F, 26.0F, clamp01(detail.density_weight + 0.35F * detail.agent_weight))
    );
    std::size_t drawn = 0;

    auto draw_ellipse = [&](const GroupBehaviorSummary& group, Color color, float alpha) {
        const float major = std::clamp(
            group.spread_major * 2.35F,
            8.0F * inverse_zoom,
            frame.layout.world_width * 0.22F
        );
        const float minor = std::clamp(
            group.spread_minor * 2.35F,
            5.0F * inverse_zoom,
            frame.layout.world_height * 0.22F
        );
        if (!finite_value(major) || !finite_value(minor) ||
            major <= 0.0F || minor <= 0.0F) {
            return;
        }
        const float cosine = std::cos(group.orientation);
        const float sine = std::sin(group.orientation);
        constexpr int segments = 40;
        Vector2 previous{};
        bool has_previous = false;
        for (int segment = 0; segment <= segments; ++segment) {
            const float angle = 6.28318530718F * static_cast<float>(segment) /
                static_cast<float>(segments);
            const float local_x = std::cos(angle) * major;
            const float local_y = std::sin(angle) * minor;
            const Vector2 point{
                group.x + local_x * cosine - local_y * sine,
                group.y + local_x * sine + local_y * cosine
            };
            if (has_previous &&
                std::abs(point.x - previous.x) < frame.layout.world_width * 0.5F &&
                std::abs(point.y - previous.y) < frame.layout.world_height * 0.5F) {
                DrawLineEx(previous, point, 1.15F * inverse_zoom, Fade(color, alpha));
            }
            previous = point;
            has_previous = true;
        }
    };

    for (const GroupBehaviorSummary& group : group_behaviors_) {
        const bool selected = group.group_id == selected_group_id && selected_group_id != 0;
        if (options.focus_selected_group && selected_group_id != 0 && !selected) {
            continue;
        }
        if (!selected && drawn >= ordinary_budget) {
            break;
        }
        if (!selected && group.members < 12U) {
            continue;
        }

        const auto trail_iterator = group_trails_.find(group.group_id);
        if (trail_iterator == group_trails_.end() || trail_iterator->second.size() < 2U) {
            if (!selected) {
                ++drawn;
            }
            continue;
        }
        const auto& trail = trail_iterator->second;
        const std::size_t first = trail.size() > 36U ? trail.size() - 36U : 0U;
        Color color = color_for_group_id(group.group_id, 255);
        const float selected_boost = selected ? 1.0F : 0.0F;
        const float base_alpha = weight * (0.16F + 0.34F * group.coherence +
            0.20F * group.active_fraction + 0.32F * selected_boost);
        const float member_curve = std::clamp(
            std::log1p(static_cast<float>(group.members)) / 8.0F,
            0.0F,
            1.0F
        );
        for (std::size_t index = first + 1U; index < trail.size(); ++index) {
            const GroupTrailPoint& before = trail[index - 1U];
            const GroupTrailPoint& after = trail[index];
            const float dx = wrapped_delta(after.x - before.x, frame.layout.world_width);
            const float dy = wrapped_delta(after.y - before.y, frame.layout.world_height);
            if (!finite_value(dx) || !finite_value(dy)) {
                continue;
            }
            const Vector2 start{before.x, before.y};
            const Vector2 end{before.x + dx, before.y + dy};
            const float age = static_cast<float>(index - first) /
                static_cast<float>(std::max<std::size_t>(trail.size() - first, 1U));
            const float alpha = base_alpha * (0.12F + 0.88F * age * age);
            const float width = (0.65F + 1.55F * member_curve +
                (selected ? 1.15F : 0.0F)) * inverse_zoom;
            DrawLineEx(start, end, width + 2.0F * inverse_zoom, Fade(BLACK, alpha * 0.65F));
            DrawLineEx(start, end, width, Fade(color, alpha));
        }

        const bool draw_shape = selected ||
            (detail.agent_weight > 0.18F && drawn < std::max<std::size_t>(ordinary_budget / 3U, 2U));
        if (draw_shape) {
            draw_ellipse(group, color, selected ? 0.78F : 0.18F * weight);
        }

        const float centroid_radius = (selected ? 4.8F : 2.6F) * inverse_zoom;
        DrawCircleLines(
            static_cast<int>(group.x),
            static_cast<int>(group.y),
            centroid_radius,
            Fade(color, selected ? 0.95F : 0.38F * weight)
        );
        if (group.dominant_action != Action::Rest &&
            group.dominant_action_fraction > 0.14F) {
            draw_action_glyph(
                group.dominant_action,
                Vector2{group.x, group.y},
                selected ? 7.2F : 4.8F,
                camera,
                selected ? 0.96F : 0.42F * weight
            );
        }
        if (!selected) {
            ++drawn;
        }
    }
}

void WorldRenderer::draw_selected_environment_probe(
    const Frame& frame,
    const Camera2D& camera,
    const RenderOptions& options,
    const EntitySample& selected
) const {
    const EnvironmentProbe probe = probe_environment(
        frame, selected.x, selected.y, options.resource_channel
    );
    if (!probe.valid || frame.layout.grid_x == 0 || frame.layout.grid_y == 0) {
        return;
    }
    const float cell_width = frame.layout.world_width /
        static_cast<float>(frame.layout.grid_x);
    const float cell_height = frame.layout.world_height /
        static_cast<float>(frame.layout.grid_y);
    if (cell_width * camera.zoom < 2.0F || cell_height * camera.zoom < 2.0F) {
        return;
    }
    const Rectangle cell{
        static_cast<float>(probe.cell_x) * cell_width,
        static_cast<float>(probe.cell_y) * cell_height,
        cell_width,
        cell_height
    };
    const float inverse_zoom = 1.0F / std::max(camera.zoom, 0.001F);
    DrawRectangleLinesEx(cell, 1.5F * inverse_zoom, Fade(YELLOW, 0.88F));
    const Rectangle neighborhood{
        cell.x - cell_width,
        cell.y - cell_height,
        cell_width * 3.0F,
        cell_height * 3.0F
    };
    DrawRectangleLinesEx(neighborhood, 0.8F * inverse_zoom, Fade(SKYBLUE, 0.32F));

    if (probe.gradient_magnitude > 1.0e-9F) {
        const float inverse_magnitude = 1.0F / probe.gradient_magnitude;
        const Vector2 center{
            cell.x + cell.width * 0.5F,
            cell.y + cell.height * 0.5F
        };
        const float length = 20.0F * inverse_zoom;
        const Vector2 end{
            center.x + probe.gradient_x * inverse_magnitude * length,
            center.y + probe.gradient_y * inverse_magnitude * length
        };
        DrawLineEx(center, end, 1.4F * inverse_zoom, Fade(Color{102, 220, 255, 255}, 0.88F));
        const float dx = (end.x - center.x) / std::max(length, 1.0e-6F);
        const float dy = (end.y - center.y) / std::max(length, 1.0e-6F);
        const float side_x = -dy;
        const float side_y = dx;
        DrawTriangle(
            end,
            Vector2{end.x - dx * 5.0F * inverse_zoom + side_x * 2.7F * inverse_zoom,
                    end.y - dy * 5.0F * inverse_zoom + side_y * 2.7F * inverse_zoom},
            Vector2{end.x - dx * 5.0F * inverse_zoom - side_x * 2.7F * inverse_zoom,
                    end.y - dy * 5.0F * inverse_zoom - side_y * 2.7F * inverse_zoom},
            Fade(Color{102, 220, 255, 255}, 0.88F)
        );
    }
}

void WorldRenderer::draw(
    const Frame& frame,
    const Camera2D& camera,
    Rectangle viewport,
    const RenderOptions& options,
    const std::vector<SocialNeighbor>& selected_neighbors
) const {
    if (heatmap_.id == 0) {
        return;
    }

    const float world_width = frame.layout.world_width;
    const float world_height = frame.layout.world_height;
    const RenderDetail detail = resolve_render_detail(
        frame,
        camera,
        viewport,
        options.lod_mode
    );
    const float micro_detail = clamp01(detail.micro_weight);
    const BehaviorWeights behavior = resolve_behavior_weights(
        options.behavior_overlay,
        detail
    );
    const EntitySample* selected_entity = nullptr;
    std::uint64_t selected_group_id = 0;
    if (options.selected_entity_id != 0) {
        for (const EntitySample& entity : frame.entities) {
            if (entity.entity_id == options.selected_entity_id) {
                selected_entity = &entity;
                selected_group_id = entity.group_id;
                break;
            }
        }
    }

    DrawTexturePro(
        heatmap_,
        Rectangle{0.0F, 0.0F,
            static_cast<float>(heatmap_.width),
            static_cast<float>(heatmap_.height)},
        Rectangle{0.0F, 0.0F, world_width, world_height},
        Vector2{0.0F, 0.0F},
        0.0F,
        WHITE
    );

    if (options.show_grid &&
        frame.layout.grid_x <= 512 &&
        frame.layout.grid_y <= 512 &&
        camera.zoom > 2.5F) {
        const float cell_width = world_width /
            static_cast<float>(frame.layout.grid_x);
        const float cell_height = world_height /
            static_cast<float>(frame.layout.grid_y);
        const Color grid_color = Fade(BLACK, 0.22F);

        rlSetTexture(0);
        rlBegin(RL_LINES);
        rlColor4ub(grid_color.r, grid_color.g, grid_color.b, grid_color.a);
        for (std::uint32_t x = 1; x < frame.layout.grid_x; ++x) {
            const float position = static_cast<float>(x) * cell_width;
            rlVertex2f(position, 0.0F);
            rlVertex2f(position, world_height);
        }
        for (std::uint32_t y = 1; y < frame.layout.grid_y; ++y) {
            const float position = static_cast<float>(y) * cell_height;
            rlVertex2f(0.0F, position);
            rlVertex2f(world_width, position);
        }
        rlEnd();
    }

    const float flow_weight = options.show_velocity
        ? std::max(detail.flow_weight, 0.42F)
        : detail.flow_weight;
    if (flow_weight > 0.04F) {
        draw_flow_field(frame, camera, flow_weight);
    }

    if (behavior.groups > 0.035F) {
        draw_group_history_overlay(
            frame,
            camera,
            detail,
            options,
            selected_group_id,
            behavior.groups
        );
        draw_group_behavior_overlay(
            group_behaviors_,
            camera,
            behavior.groups * (options.show_group_trails ? 0.58F : 1.0F)
        );
    }

    const float aggregate_action_weight = behavior.actions *
        (1.0F - 0.78F * detail.micro_weight);
    if (aggregate_action_weight > 0.05F) {
        draw_action_activity_field(
            frame,
            camera,
            aggregate_action_weight
        );
    }

    const Vector2 top_left = GetScreenToWorld2D(
        Vector2{viewport.x, viewport.y},
        camera
    );
    const Vector2 bottom_right = GetScreenToWorld2D(
        Vector2{viewport.x + viewport.width, viewport.y + viewport.height},
        camera
    );
    const float left = std::min(top_left.x, bottom_right.x);
    const float right = std::max(top_left.x, bottom_right.x);
    const float top = std::min(top_left.y, bottom_right.y);
    const float bottom = std::max(top_left.y, bottom_right.y);

    // Selected-agent relationship topology is deliberately local and bounded.
    const auto selected_position = current_positions_.find(options.selected_entity_id);
    if (selected_position != current_positions_.end()) {
        const Vector2 source{selected_position->second.x, selected_position->second.y};
        for (const SocialNeighbor& neighbor : selected_neighbors) {
            const auto target_iterator = current_positions_.find(neighbor.entity_id);
            if (target_iterator == current_positions_.end()) {
                continue;
            }

            Vector2 target{target_iterator->second.x, target_iterator->second.y};
            const float dx = wrapped_delta(target.x - source.x, world_width);
            const float dy = wrapped_delta(target.y - source.y, world_height);
            target = Vector2{source.x + dx, source.y + dy};

            const Color relationship_color = neighbor.trust >= 0.0F
                ? Fade(Color{95, 230, 190, 255}, 0.28F + 0.50F * neighbor.familiarity)
                : Fade(Color{255, 92, 92, 255}, 0.28F + 0.50F * neighbor.familiarity);
            const float width = (0.7F + 1.6F * neighbor.familiarity) /
                std::max(camera.zoom, 0.001F);
            DrawLineEx(source, target, width, relationship_color);
        }
    }

    if (options.show_event_markers) {
        const float event_detail = clamp01(detail.agent_weight + 0.35F * detail.micro_weight);
        // At macro scale the trend panel and density field already carry the
        // aggregate event signal. Drawing cluster circles there created false
        // "cities" and obscured resources, so spatial glyphs enter only when
        // agents themselves have become readable.
        if (event_detail >= 0.18F) {
            const std::size_t marker_budget = static_cast<std::size_t>(
                lerp_value(36.0F, 320.0F, event_detail)
            );
            std::size_t drawn = 0;

            for (auto iterator = event_markers_.rbegin();
                 iterator != event_markers_.rend() && drawn < marker_budget;
                 ++iterator) {
                const EventMarker& marker = *iterator;
                if (marker.x < left || marker.x > right || marker.y < top || marker.y > bottom) {
                    continue;
                }

                const bool action_marker = marker.kind == EventKind::Harvest ||
                    marker.kind == EventKind::Reproduce;
                if (action_marker &&
                    options.behavior_overlay != BehaviorOverlayMode::Off &&
                    detail.micro_weight < 0.72F) {
                    continue;
                }

                const float age = frame.tick >= marker.tick
                    ? static_cast<float>(frame.tick - marker.tick)
                    : 0.0F;
                const float life = 1.0F - clamp01(age /
                    static_cast<float>(event_ttl(marker.kind)));
                const float radius_pixels = lerp_value(1.8F, 4.8F, micro_detail);
                const float radius = (radius_pixels + 2.0F * life) /
                    std::max(camera.zoom, 0.001F);
                const float width = lerp_value(0.8F, 1.25F, micro_detail) /
                    std::max(camera.zoom, 0.001F);
                const Vector2 center{marker.x, marker.y};
                const Color color = Fade(
                    event_color(marker.kind),
                    (0.10F + 0.48F * life) * event_detail
                );

                switch (marker.kind) {
                case EventKind::Birth:
                    DrawCircleLines(static_cast<int>(marker.x), static_cast<int>(marker.y),
                        radius, color);
                    break;
                case EventKind::Death:
                    DrawLineEx(
                        Vector2{marker.x - radius, marker.y - radius},
                        Vector2{marker.x + radius, marker.y + radius},
                        width, color
                    );
                    DrawLineEx(
                        Vector2{marker.x - radius, marker.y + radius},
                        Vector2{marker.x + radius, marker.y - radius},
                        width, color
                    );
                    break;
                case EventKind::Harvest:
                    DrawLineEx(
                        Vector2{marker.x - radius, marker.y},
                        Vector2{marker.x + radius, marker.y},
                        width, color
                    );
                    DrawLineEx(
                        Vector2{marker.x, marker.y - radius},
                        Vector2{marker.x, marker.y + radius},
                        width, color
                    );
                    break;
                case EventKind::Reproduce:
                    DrawLineEx(Vector2{center.x, center.y - radius},
                        Vector2{center.x + radius, center.y}, width, color);
                    DrawLineEx(Vector2{center.x + radius, center.y},
                        Vector2{center.x, center.y + radius}, width, color);
                    DrawLineEx(Vector2{center.x, center.y + radius},
                        Vector2{center.x - radius, center.y}, width, color);
                    DrawLineEx(Vector2{center.x - radius, center.y},
                        Vector2{center.x, center.y - radius}, width, color);
                    break;
                }
                ++drawn;
            }
                }
    }

    static thread_local std::vector<const EntitySample*> render_entities;
    static thread_local std::vector<const EntitySample*> tile_representatives;
    static thread_local std::vector<std::uint8_t> tile_priorities;
    render_entities.clear();

    if (detail.agent_weight > 0.025F) {
        const float inverse_zoom = 1.0F / std::max(camera.zoom, 0.001F);
        const float padding = 12.0F * inverse_zoom;
        const float sample_detail = clamp01(
            detail.agent_weight * (0.72F + 0.28F * detail.micro_weight)
        );
        const int tile_pixels = std::clamp(
            static_cast<int>(std::lround(lerp_value(30.0F, 5.0F, sample_detail))),
            5,
            30
        );
        const std::size_t entity_budget = static_cast<std::size_t>(
            lerp_value(
                420.0F,
                28000.0F,
                std::pow(sample_detail, 1.58F)
            )
        );
        const int tile_columns = std::max(
            1,
            static_cast<int>(std::ceil(viewport.width / tile_pixels))
        );
        const int tile_rows = std::max(
            1,
            static_cast<int>(std::ceil(viewport.height / tile_pixels))
        );
        const std::size_t tile_count =
            static_cast<std::size_t>(tile_columns) *
            static_cast<std::size_t>(tile_rows);
        tile_representatives.assign(tile_count, nullptr);
        tile_priorities.assign(tile_count, 0U);

        const std::size_t candidate_stride = std::max<std::size_t>(
            1,
            frame.entities.size() / std::max<std::size_t>(entity_budget * 5U, 1U)
        );

        for (const EntitySample& entity : frame.entities) {
            if (!valid_entity_sample(entity) ||
                !is_visible(entity, left, top, right, bottom, padding)) {
                continue;
            }
            if (candidate_stride > 1 &&
                entity.entity_id != options.selected_entity_id &&
                entity.action_success == 0 &&
                mix_id(entity.entity_id) % candidate_stride != 0) {
                continue;
            }

            const Vector2 screen = GetWorldToScreen2D(
                Vector2{entity.x, entity.y},
                camera
            );
            const int tile_x = static_cast<int>(
                (screen.x - viewport.x) / static_cast<float>(tile_pixels)
            );
            const int tile_y = static_cast<int>(
                (screen.y - viewport.y) / static_cast<float>(tile_pixels)
            );
            if (tile_x < 0 || tile_x >= tile_columns ||
                tile_y < 0 || tile_y >= tile_rows) {
                continue;
            }

            const std::size_t tile_index =
                static_cast<std::size_t>(tile_y) *
                    static_cast<std::size_t>(tile_columns) +
                static_cast<std::size_t>(tile_x);
            std::uint8_t priority = entity.entity_id == options.selected_entity_id ? 6U :
                (options.focus_selected_group && selected_group_id != 0 &&
                 entity.group_id == selected_group_id) ? 5U :
                entity.action_success != 0 ? 4U :
                entity.group_id != 0 ? 2U : 1U;
            if (tile_priorities[tile_index] > priority) {
                continue;
            }
            if (tile_priorities[tile_index] == priority &&
                tile_representatives[tile_index] != nullptr &&
                mix_id(tile_representatives[tile_index]->entity_id) < mix_id(entity.entity_id)) {
                continue;
            }
            tile_priorities[tile_index] = priority;
            tile_representatives[tile_index] = &entity;
        }

        render_entities.reserve(std::min(tile_count, entity_budget));
        for (const EntitySample* entity : tile_representatives) {
            if (entity != nullptr) {
                render_entities.push_back(entity);
                if (render_entities.size() >= entity_budget) {
                    break;
                }
            }
        }

        const float trail_weight = options.show_velocity
            ? std::max(detail.agent_weight, 0.48F)
            : detail.micro_weight * 0.26F;
        if (trail_weight > 0.035F && !render_entities.empty()) {
            const std::size_t trail_budget = static_cast<std::size_t>(
                lerp_value(180.0F, 4200.0F, trail_weight)
            );
            const std::size_t trail_stride = std::max<std::size_t>(
                1,
                render_entities.size() / std::max<std::size_t>(trail_budget, 1U)
            );
            for (std::size_t index = 0; index < render_entities.size(); index += trail_stride) {
                const EntitySample* entity = render_entities[index];
                const auto previous = previous_positions_.find(entity->entity_id);
                if (previous == previous_positions_.end()) {
                    continue;
                }
                const float speed = std::sqrt(
                    entity->vx * entity->vx + entity->vy * entity->vy
                );
                if (!finite_value(speed) || speed < 0.025F) {
                    continue;
                }
                const Vector2 current{entity->x, entity->y};
                const Vector2 old = previous_endpoint(
                    current,
                    Vector2{previous->second.x, previous->second.y},
                    world_width,
                    world_height
                );
                if (!valid_world_position(old.x, old.y)) {
                    continue;
                }
                DrawLineEx(
                    old,
                    current,
                    lerp_value(0.55F, 1.05F, detail.micro_weight) * inverse_zoom,
                    Fade(Color{108, 229, 255, 255}, 0.30F * trail_weight)
                );
            }
        }

        const float body_radius_pixels = lerp_value(
            0.92F,
            2.65F,
            std::pow(sample_detail, 0.78F)
        );
        const float outline_radius_pixels = body_radius_pixels +
            lerp_value(0.22F, 0.92F, detail.micro_weight);
        const float body_radius = body_radius_pixels * inverse_zoom;
        const float outline_radius = outline_radius_pixels * inverse_zoom;
        const unsigned char outline_alpha = static_cast<unsigned char>(
            std::clamp(45.0F + 185.0F * detail.agent_weight, 0.0F, 230.0F)
        );
        const unsigned char body_alpha = static_cast<unsigned char>(
            std::clamp(54.0F + 191.0F * detail.agent_weight, 0.0F, 245.0F)
        );

        const SolidQuadBatch outline_batch = begin_solid_quad_batch();
        for (const EntitySample* entity : render_entities) {
            emit_solid_quad(
                outline_batch,
                entity->x - outline_radius,
                entity->y - outline_radius,
                entity->x + outline_radius,
                entity->y + outline_radius,
                Color{1, 5, 7, outline_alpha}
            );
        }
        end_solid_quad_batch();

        const SolidQuadBatch body_batch = begin_solid_quad_batch();
        for (const EntitySample* entity : render_entities) {
            Color color = color_for_entity(*entity, frame.layout.max_energy);
            color.a = static_cast<unsigned char>(std::min<int>(color.a, body_alpha));
            if (options.focus_selected_group && selected_group_id != 0 &&
                entity->group_id != selected_group_id &&
                entity->entity_id != options.selected_entity_id) {
                color.a = static_cast<unsigned char>(
                    std::min<int>(color.a, 34 + static_cast<int>(60.0F * detail.micro_weight))
                );
            }

            // Body color always represents group identity. Actions use
            // shape-coded overlays, so harvest no longer disappears into the
            // green resource palette and group patterns remain readable.
            emit_solid_quad(
                body_batch,
                entity->x - body_radius,
                entity->y - body_radius,
                entity->x + body_radius,
                entity->y + body_radius,
                color
            );
        }
        end_solid_quad_batch();

        if (detail.micro_weight > 0.16F) {
            const float core_radius = lerp_value(
                0.28F,
                0.82F,
                detail.micro_weight
            ) * inverse_zoom;
            const unsigned char core_alpha = static_cast<unsigned char>(
                210.0F * detail.micro_weight
            );
            const SolidQuadBatch core_batch = begin_solid_quad_batch();
            for (const EntitySample* entity : render_entities) {
                unsigned char alpha = core_alpha;
                if (options.focus_selected_group && selected_group_id != 0 &&
                    entity->group_id != selected_group_id &&
                    entity->entity_id != options.selected_entity_id) {
                    alpha = static_cast<unsigned char>(
                        std::min<int>(alpha, 18 + static_cast<int>(22.0F * detail.micro_weight))
                    );
                }
                emit_solid_quad(
                    core_batch,
                    entity->x - core_radius,
                    entity->y - core_radius,
                    entity->x + core_radius,
                    entity->y + core_radius,
                    Color{242, 250, 255, alpha}
                );
            }
            end_solid_quad_batch();
        }

        const float individual_action_weight = behavior.actions *
            smooth_range(0.28F, 0.78F, detail.micro_weight);
        if (individual_action_weight > 0.05F && !render_entities.empty()) {
            const std::size_t action_budget = static_cast<std::size_t>(
                lerp_value(80.0F, 320.0F, individual_action_weight)
            );
            std::size_t drawn_actions = 0;
            for (const EntitySample* entity : render_entities) {
                if (options.focus_selected_group && selected_group_id != 0 &&
                    entity->group_id != selected_group_id) {
                    continue;
                }
                const Action action = static_cast<Action>(entity->action);
                const bool movement = action == Action::MoveResource ||
                    action == Action::MoveSocial || action == Action::Flee;
                if (action == Action::Rest || action == Action::None ||
                    (entity->action_success == 0 && !movement)) {
                    continue;
                }
                draw_action_glyph(
                    action,
                    Vector2{entity->x, entity->y},
                    lerp_value(3.6F, 6.2F, detail.micro_weight),
                    camera,
                    individual_action_weight *
                        (entity->action_success != 0 ? 0.90F : 0.48F)
                );
                if (++drawn_actions >= action_budget) {
                    break;
                }
            }
        }
    }

    DrawRectangleLinesEx(
        Rectangle{0.0F, 0.0F, world_width, world_height},
        1.5F / std::max(camera.zoom, 0.001F),
        RAYWHITE
    );

    // Selected agents are always drawn, even when macro LOD suppresses all other
    // individuals or medium sampling would otherwise discard this ID.
    if (selected_entity != nullptr) {
        const EntitySample* selected = selected_entity;
        draw_selected_environment_probe(frame, camera, options, *selected);
        {
            const float selected_radius = 10.0F /
                std::max(camera.zoom, 0.001F);
            const Vector2 center{selected->x, selected->y};

            if (selected->target_id != 0) {
                const auto target = current_positions_.find(selected->target_id);
                if (target != current_positions_.end()) {
                    Vector2 target_position{target->second.x, target->second.y};
                    target_position.x = center.x + wrapped_delta(
                        target_position.x - center.x,
                        world_width
                    );
                    target_position.y = center.y + wrapped_delta(
                        target_position.y - center.y,
                        world_height
                    );
                    DrawLineEx(
                        center,
                        target_position,
                        1.25F / std::max(camera.zoom, 0.001F),
                        Fade(YELLOW, 0.48F)
                    );
                }
            }

            const float body_radius = 5.5F / std::max(camera.zoom, 0.001F);
            DrawCircleV(center, body_radius * 1.45F, BLACK);
            DrawCircleV(center, body_radius, Color{255, 248, 185, 255});
            DrawCircleLines(
                static_cast<int>(center.x),
                static_cast<int>(center.y),
                selected_radius,
                YELLOW
            );
            DrawCircleLines(
                static_cast<int>(center.x),
                static_cast<int>(center.y),
                selected_radius * 1.45F,
                Fade(YELLOW, 0.52F)
            );

            const float selected_speed = std::sqrt(
                selected->vx * selected->vx + selected->vy * selected->vy
            );
            if (finite_value(selected_speed) && selected_speed > 0.001F) {
                const float dx = selected->vx / selected_speed;
                const float dy = selected->vy / selected_speed;
                const float side_x = -dy;
                const float side_y = dx;
                const float length = 13.0F / std::max(camera.zoom, 0.001F);
                const float half_width = 4.2F / std::max(camera.zoom, 0.001F);
                DrawTriangle(
                    Vector2{center.x + dx * length, center.y + dy * length},
                    Vector2{center.x - dx * length * 0.45F + side_x * half_width,
                        center.y - dy * length * 0.45F + side_y * half_width},
                    Vector2{center.x - dx * length * 0.45F - side_x * half_width,
                        center.y - dy * length * 0.45F - side_y * half_width},
                    YELLOW
                );
            }
        }
    }
}

std::uint64_t WorldRenderer::pick_entity(
    const Frame& frame,
    const Camera2D& camera,
    Vector2 screen_position,
    float radius_pixels
) const {
    float best_distance = radius_pixels * radius_pixels;
    std::uint64_t selected = 0;

    for (const EntitySample& entity : frame.entities) {
        if (!valid_entity_sample(entity)) {
            continue;
        }
        const Vector2 screen = GetWorldToScreen2D(
            Vector2{entity.x, entity.y},
            camera
        );
        const float dx = screen.x - screen_position.x;
        const float dy = screen.y - screen_position.y;
        const float distance = dx * dx + dy * dy;
        if (distance < best_distance) {
            best_distance = distance;
            selected = entity.entity_id;
        }
    }

    return selected;
}

}  // namespace eco
