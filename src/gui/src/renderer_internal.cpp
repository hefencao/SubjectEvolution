#include "render/renderer_internal.hpp"

#include <algorithm>
#include <array>
#include <cmath>
#include <cstddef>
#include <cstdint>
#include <limits>
#include <vector>

#include <rlgl.h>

namespace eco::render_internal {

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

float temporal_alpha_for_half_life(
    float half_life_ticks,
    std::uint64_t elapsed_ticks
) noexcept {
    if (half_life_ticks <= 0.0F || elapsed_ticks == 0) {
        return elapsed_ticks == 0 ? 0.0F : 1.0F;
    }
    const float elapsed = static_cast<float>(elapsed_ticks);
    return clamp01(1.0F - std::exp2(-elapsed / half_life_ticks));
}

const std::vector<GroupBehaviorSummary>& select_group_behaviors(
    const GroupCache& groups,
    OverlayTemporalMode mode
) noexcept {
    switch (mode) {
    case OverlayTemporalMode::Instant:
        return groups.behaviors;
    case OverlayTemporalMode::Responsive:
        return groups.responsive_behaviors.empty()
            ? groups.behaviors
            : groups.responsive_behaviors;
    case OverlayTemporalMode::Stable:
        return groups.stable_behaviors.empty()
            ? groups.behaviors
            : groups.stable_behaviors;
    }
    return groups.behaviors;
}

const std::array<ActionActivityCell, kActionFieldCellCount>& select_action_field(
    const ActionFieldCache& field,
    OverlayTemporalMode mode
) noexcept {
    switch (mode) {
    case OverlayTemporalMode::Instant:
        return field.raw;
    case OverlayTemporalMode::Responsive:
        return field.responsive;
    case OverlayTemporalMode::Stable:
        return field.stable;
    }
    return field.raw;
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
    float depletion,
    const RenderDetail& detail,
    const RenderOptions& options
) {
    resource = smoothstep01(resource);
    hazard = clamp01(hazard);
    population_density = clamp01(population_density);
    resource_change = std::clamp(resource_change, -1.0F, 1.0F);
    hazard_change = std::clamp(hazard_change, -1.0F, 1.0F);
    hazard_edge = clamp01(hazard_edge);
    depletion = clamp01(depletion);

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
        // When resources are globally depleted, population structure becomes
        // the most useful remaining macro signal. Raise density contrast
        // smoothly instead of leaving the overview almost blank.
        const float density_strength =
            (0.10F + 0.22F * depletion) * detail.density_weight;
        const float density_curve = std::sqrt(population_density) * density_strength;
        red += density_curve * (10.0F + 8.0F * depletion);
        green += density_curve * (74.0F + 42.0F * depletion);
        blue += density_curve * (90.0F + 48.0F * depletion);
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

Color behavior_color(Action action, unsigned char alpha) {
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


Color color_for_group_id(std::uint64_t group_id, unsigned char alpha) {
    if (group_id == 0) {
        return Color{118, 154, 176, alpha};
    }
    const std::uint64_t hash = mix_id(group_id);
    const std::uint32_t hue_bits = static_cast<std::uint32_t>(
        (hash ^ (hash >> 29U) ^ (hash >> 47U)) & 0xFFFFFFU
    );
    const float hue = static_cast<float>(hue_bits) / 16777215.0F;
    return hsv_color(hue, 0.78F, 0.98F, alpha);
}

bool action_uses_direction(Action action) noexcept {
    return action == Action::MoveResource ||
           action == Action::MoveSocial ||
           action == Action::Flee;
}

Vector2 resolve_motion_vector(
    Vector2 velocity,
    Vector2 current,
    Vector2 previous,
    float world_width,
    float world_height
) noexcept {
    const float velocity_length = std::sqrt(
        velocity.x * velocity.x + velocity.y * velocity.y
    );
    if (finite_value(velocity.x) && finite_value(velocity.y) &&
        velocity_length > 1.0e-5F) {
        return velocity;
    }

    if (!valid_world_position(current.x, current.y) ||
        !valid_world_position(previous.x, previous.y)) {
        return Vector2{0.0F, 0.0F};
    }
    return Vector2{
        wrapped_delta(current.x - previous.x, world_width),
        wrapped_delta(current.y - previous.y, world_height)
    };
}

namespace {

struct GlyphBasis {
    Vector2 forward{1.0F, 0.0F};
    Vector2 side{0.0F, 1.0F};
    bool valid = true;
};

GlyphBasis glyph_basis(Action action, Vector2 direction) {
    if (!action_uses_direction(action)) {
        return GlyphBasis{};
    }
    const float length = std::sqrt(
        direction.x * direction.x + direction.y * direction.y
    );
    if (!finite_value(direction.x) || !finite_value(direction.y) ||
        length <= 1.0e-5F) {
        return GlyphBasis{Vector2{1.0F, 0.0F}, Vector2{0.0F, 1.0F}, false};
    }
    const Vector2 forward{direction.x / length, direction.y / length};
    return GlyphBasis{forward, Vector2{-forward.y, forward.x}, true};
}

Vector2 glyph_point(
    Vector2 center,
    const GlyphBasis& basis,
    float local_x,
    float local_y
) {
    return Vector2{
        center.x + basis.forward.x * local_x + basis.side.x * local_y,
        center.y + basis.forward.y * local_x + basis.side.y * local_y
    };
}

}  // namespace

void draw_action_glyph_layer(
    Action action,
    Vector2 center,
    float radius,
    float width,
    Color color,
    Vector2 direction
) {
    const GlyphBasis basis = glyph_basis(action, direction);
    if (!basis.valid) {
        return;
    }
    const auto point = [&](float x, float y) {
        return glyph_point(center, basis, x, y);
    };

    switch (action) {
    case Action::MoveResource:
        DrawLineEx(point(-radius, 0.0F), point(radius * 0.75F, 0.0F), width, color);
        DrawLineEx(point(radius * 0.75F, 0.0F),
            point(radius * 0.15F, -radius * 0.58F), width, color);
        DrawLineEx(point(radius * 0.75F, 0.0F),
            point(radius * 0.15F, radius * 0.58F), width, color);
        break;
    case Action::MoveSocial:
        DrawCircleV(point(-radius * 0.52F, 0.0F), radius * 0.24F, color);
        DrawCircleV(point(radius * 0.52F, 0.0F), radius * 0.24F, color);
        DrawLineEx(point(-radius * 0.28F, 0.0F),
            point(radius * 0.28F, 0.0F), width, color);
        break;
    case Action::Harvest:
        // Pickaxe glyph remains visible over green resources.
        DrawLineEx(point(-radius * 0.48F, radius * 0.72F),
            point(radius * 0.28F, -radius * 0.42F), width, color);
        DrawLineEx(point(-radius * 0.46F, -radius * 0.42F),
            point(radius * 0.72F, -radius * 0.08F), width, color);
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
            DrawLineEx(point(-radius * 0.75F + shift, -radius * 0.62F),
                point(shift, 0.0F), width, color);
            DrawLineEx(point(shift, 0.0F),
                point(-radius * 0.75F + shift, radius * 0.62F), width, color);
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

bool draw_action_glyph(
    Action action,
    Vector2 center,
    float radius_pixels,
    const Camera2D& camera,
    float alpha,
    Vector2 direction
) {
    if (action_index(action) < 0 || alpha <= 0.01F) {
        return false;
    }
    const GlyphBasis basis = glyph_basis(action, direction);
    if (!basis.valid) {
        return false;
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
        Color{2, 4, 7, static_cast<unsigned char>(opacity * 0.78F)},
        direction
    );
    draw_action_glyph_layer(
        action,
        center,
        radius,
        color_width,
        behavior_color(action, opacity),
        direction
    );
    return true;
}

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

std::size_t draw_action_activity_field(
    const std::array<ActionActivityCell, kActionFieldCellCount>& cells,
    const FileHeader& layout,
    const Camera2D& camera,
    std::size_t budget,
    float weight,
    ActionFilterMode filter
) {
    weight = clamp01(weight);
    if (weight < 0.08F || budget == 0) {
        return 0;
    }

    struct Candidate {
        int index = 0;
        Action action = Action::Rest;
        float score = 0.0F;
        float dominance = 0.0F;
        Vector2 direction{};
        float direction_coherence = 0.0F;
        Vector2 center{};
    };
    std::vector<Candidate> candidates;
    candidates.reserve(kActionFieldCellCount);

    const float world_width = std::max(layout.world_width, 1.0F);
    const float world_height = std::max(layout.world_height, 1.0F);
    const float cell_width = world_width / static_cast<float>(kActionFieldColumns);
    const float cell_height = world_height / static_cast<float>(kActionFieldRows);

    for (int index = 0; index < kActionFieldCellCount; ++index) {
        const ActionActivityCell& cell = cells[static_cast<std::size_t>(index)];
        float filtered_total = 0.0F;
        float filtered_samples = 0.0F;
        int dominant_index = -1;
        float dominant_weight = 0.0F;
        for (int action_index_value = 0; action_index_value < 8; ++action_index_value) {
            const Action action = static_cast<Action>(action_index_value);
            if (action == Action::Rest || !action_matches_filter(action, filter)) {
                continue;
            }
            const float action_weight = cell.weights[static_cast<std::size_t>(action_index_value)];
            filtered_total += action_weight;
            filtered_samples += cell.samples[static_cast<std::size_t>(action_index_value)];
            if (action_weight > dominant_weight) {
                dominant_weight = action_weight;
                dominant_index = action_index_value;
            }
        }
        if (dominant_index < 0 || filtered_total < 1.6F || filtered_samples < 1.2F) {
            continue;
        }

        const float dominance = dominant_weight / std::max(filtered_total, 1.0e-5F);
        if (dominance < 0.30F) {
            continue;
        }
        const Action dominant_action = static_cast<Action>(dominant_index);
        const std::size_t slot = static_cast<std::size_t>(dominant_index);
        Vector2 direction{};
        float direction_coherence = 1.0F;
        if (action_uses_direction(dominant_action)) {
            const float resultant = std::sqrt(
                cell.sum_vx[slot] * cell.sum_vx[slot] +
                cell.sum_vy[slot] * cell.sum_vy[slot]
            );
            const float summed_speed = cell.sum_speed[slot];
            direction_coherence = summed_speed > 1.0e-5F
                ? clamp01(resultant / summed_speed)
                : 0.0F;
            if (resultant <= 1.0e-5F || direction_coherence < 0.24F) {
                continue;
            }
            direction = Vector2{
                cell.sum_vx[slot] / resultant,
                cell.sum_vy[slot] / resultant
            };
        }

        const int column = index % kActionFieldColumns;
        const int row = index / kActionFieldColumns;
        Vector2 center{
            (static_cast<float>(column) + 0.5F) * cell_width,
            (static_cast<float>(row) + 0.5F) * cell_height
        };
        if (dominant_weight > 1.0e-5F) {
            center.x = cell.sum_x[slot] / dominant_weight;
            center.y = cell.sum_y[slot] / dominant_weight;
        }
        const float score = std::log1p(filtered_total) * (0.58F + dominance) *
            (action_uses_direction(dominant_action)
                ? 0.42F + 0.58F * direction_coherence
                : 1.0F);
        candidates.push_back(Candidate{
            index,
            dominant_action,
            score,
            dominance,
            direction,
            direction_coherence,
            center
        });
    }

    std::sort(candidates.begin(), candidates.end(),
        [](const Candidate& left, const Candidate& right) {
            if (left.score != right.score) {
                return left.score > right.score;
            }
            return left.index < right.index;
        });
    if (candidates.size() > budget) {
        candidates.resize(budget);
    }

    for (const Candidate& candidate : candidates) {
        const ActionActivityCell& cell = cells[static_cast<std::size_t>(candidate.index)];
        const std::size_t slot = static_cast<std::size_t>(action_index(candidate.action));
        const float activity = cell.weights[slot];
        const float radius_pixels = std::clamp(
            4.0F + 1.35F * std::log1p(activity), 5.0F, 10.5F);
        draw_action_glyph(
            candidate.action,
            candidate.center,
            radius_pixels,
            camera,
            weight * (0.28F + 0.60F * candidate.dominance),
            candidate.direction
        );
    }
    return candidates.size();
}

std::size_t draw_group_behavior_overlay(
    const std::vector<GroupBehaviorSummary>& groups,
    const Camera2D& camera,
    std::size_t budget,
    float weight,
    ActionFilterMode filter
) {
    weight = clamp01(weight);
    if (weight < 0.08F || groups.empty() || budget == 0) {
        return 0;
    }

    struct Candidate {
        const GroupBehaviorSummary* group = nullptr;
        Action display_action = Action::Rest;
        float display_fraction = 0.0F;
        float score = 0.0F;
    };
    std::vector<Candidate> candidates;
    candidates.reserve(groups.size());

    for (const GroupBehaviorSummary& group : groups) {
        if (group.members < 8U) {
            continue;
        }

        Action display_action = group.dominant_action;
        float display_fraction = group.dominant_action_fraction;
        if (filter != ActionFilterMode::All) {
            display_action = Action::Rest;
            display_fraction = 0.0F;
            for (std::size_t index = 0; index < group.action_fractions.size(); ++index) {
                const Action candidate_action = static_cast<Action>(index);
                if (!action_matches_filter(candidate_action, filter)) {
                    continue;
                }
                if (group.action_fractions[index] > display_fraction) {
                    display_fraction = group.action_fractions[index];
                    display_action = candidate_action;
                }
            }
        }

        const float filtered_activity = display_fraction * group.active_fraction;
        const float movement_signal = filter == ActionFilterMode::All ||
            filter == ActionFilterMode::Movement
                ? group.coherence
                : 0.0F;
        const float behavior_strength = std::max(movement_signal, filtered_activity);
        if (behavior_strength < 0.055F ||
            (filter != ActionFilterMode::All && display_fraction < 0.025F)) {
            continue;
        }
        const float score = std::log1p(static_cast<float>(group.members)) *
            (0.32F + movement_signal + 0.72F * filtered_activity);
        candidates.push_back(Candidate{
            &group,
            display_action,
            display_fraction,
            score
        });
    }

    std::sort(candidates.begin(), candidates.end(),
        [](const Candidate& left, const Candidate& right) {
            return left.score > right.score;
        });
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
            group.visual_key != 0 ? group.visual_key : group.group_id,
            static_cast<unsigned char>(std::clamp(opacity * 255.0F, 0.0F, 235.0F))
        );

        if (finite_value(speed) && speed > 0.012F && group.coherence > 0.12F) {
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

            if (candidate.display_action != Action::Rest &&
                candidate.display_fraction > 0.22F) {
                const Vector2 badge{
                    head.x + direction_x * 4.0F * inverse_zoom,
                    head.y + direction_y * 4.0F * inverse_zoom
                };
                draw_action_glyph(
                    candidate.display_action,
                    badge,
                    4.5F + 3.5F * candidate.display_fraction,
                    camera,
                    opacity * (0.58F + 0.42F * candidate.display_fraction),
                    Vector2{group.mean_vx, group.mean_vy}
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
            if (candidate.display_action != Action::Rest &&
                candidate.display_fraction > 0.26F) {
                draw_action_glyph(
                    candidate.display_action,
                    center,
                    4.5F + 2.8F * candidate.display_fraction,
                    camera,
                    opacity,
                    Vector2{group.mean_vx, group.mean_vy}
                );
            }
        }
    }
    return candidates.size();
}

}  // namespace eco::render_internal
