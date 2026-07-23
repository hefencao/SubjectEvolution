#include "eco/renderer.hpp"

#include <algorithm>
#include <array>
#include <cmath>
#include <cstddef>
#include <cstdint>
#include <limits>
#include <unordered_set>
#include <vector>

#include <rlgl.h>

namespace eco {
namespace {

float clamp01(float value) {
    return std::clamp(value, 0.0F, 1.0F);
}

float smoothstep01(float value) {
    value = clamp01(value);
    return value * value * (3.0F - 2.0F * value);
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

Color heat_color(
    int channel,
    float resource,
    float hazard,
    float population_density,
    float resource_change,
    float hazard_change,
    RenderLod lod,
    const RenderOptions& options
) {
    resource = smoothstep01(resource);
    hazard = options.show_hazard ? smoothstep01(hazard) : 0.0F;
    population_density = clamp01(population_density);
    resource_change = std::clamp(resource_change, -1.0F, 1.0F);
    hazard_change = std::clamp(hazard_change, -1.0F, 1.0F);

    const Palette palette = resource_palette(channel);
    float red = palette.low[0] + (palette.high[0] - palette.low[0]) * resource;
    float green = palette.low[1] + (palette.high[1] - palette.low[1]) * resource;
    float blue = palette.low[2] + (palette.high[2] - palette.low[2]) * resource;

    if (options.show_hazard) {
        const float hazard_curve = std::pow(hazard, 1.25F);
        red += hazard_curve * 128.0F;
        green = green * (1.0F - hazard_curve * 0.48F) + hazard_curve * 24.0F;
        blue = blue * (1.0F - hazard_curve * 0.42F) + hazard_curve * 23.0F;
    }

    if (options.show_population_density) {
        const float density_strength =
            lod == RenderLod::Macro ? 0.62F :
            lod == RenderLod::Medium ? 0.12F : 0.0F;
        const float density_curve = std::sqrt(population_density) * density_strength;
        red += density_curve * 28.0F;
        green += density_curve * 138.0F;
        blue += density_curve * 164.0F;
    }

    if (options.show_environment_change) {
        if (resource_change > 0.0F) {
            green += resource_change * 78.0F;
            blue += resource_change * 24.0F;
        } else {
            red += -resource_change * 92.0F;
            green += -resource_change * 25.0F;
        }

        if (hazard_change > 0.0F) {
            red += hazard_change * 62.0F;
            blue += hazard_change * 36.0F;
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

void draw_flow_field(
    const Frame& frame,
    const Camera2D& camera,
    bool emphasized
) {
    constexpr int columns = 30;
    constexpr int rows = 19;
    constexpr int cell_count = columns * rows;

    static thread_local std::vector<float> sum_vx(cell_count);
    static thread_local std::vector<float> sum_vy(cell_count);
    static thread_local std::vector<std::uint32_t> counts(cell_count);

    std::fill(sum_vx.begin(), sum_vx.end(), 0.0F);
    std::fill(sum_vy.begin(), sum_vy.end(), 0.0F);
    std::fill(counts.begin(), counts.end(), 0U);

    const float world_width = std::max(frame.layout.world_width, 1.0F);
    const float world_height = std::max(frame.layout.world_height, 1.0F);

    for (const EntitySample& entity : frame.entities) {
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
        const int index = row * columns + column;
        sum_vx[index] += entity.vx;
        sum_vy[index] += entity.vy;
        ++counts[index];
    }

    const float cell_width = world_width / columns;
    const float cell_height = world_height / rows;
    const float maximum_length = std::min(cell_width, cell_height) * 0.44F;
    const float line_width = (emphasized ? 1.55F : 1.05F) /
        std::max(camera.zoom, 0.001F);

    for (int row = 0; row < rows; ++row) {
        for (int column = 0; column < columns; ++column) {
            const int index = row * columns + column;
            const std::uint32_t count = counts[index];
            if (count < 4U) {
                continue;
            }

            const float mean_vx = sum_vx[index] / count;
            const float mean_vy = sum_vy[index] / count;
            const float speed = std::sqrt(mean_vx * mean_vx + mean_vy * mean_vy);
            if (speed < 0.012F) {
                continue;
            }

            const float length = std::min(
                maximum_length,
                speed * (emphasized ? 34.0F : 22.0F)
            );
            const float inverse_speed = 1.0F / speed;
            const float direction_x = mean_vx * inverse_speed;
            const float direction_y = mean_vy * inverse_speed;

            const Vector2 start{
                (static_cast<float>(column) + 0.5F) * cell_width,
                (static_cast<float>(row) + 0.5F) * cell_height
            };
            const Vector2 end{
                start.x + direction_x * length,
                start.y + direction_y * length
            };

            const float occupancy = std::clamp(
                std::log1p(static_cast<float>(count)) / 8.0F,
                0.20F,
                0.92F
            );
            const Color color = Fade(
                Color{100, 232, 255, 255},
                occupancy * (emphasized ? 0.92F : 0.62F)
            );

            DrawLineEx(start, end, line_width, color);

            const float head_length = std::min(
                length * 0.36F,
                maximum_length * 0.25F
            );
            if (head_length > 0.01F) {
                const float side_x = -direction_y;
                const float side_y = direction_x;
                const Vector2 left{
                    end.x - direction_x * head_length + side_x * head_length * 0.45F,
                    end.y - direction_y * head_length + side_y * head_length * 0.45F
                };
                const Vector2 right{
                    end.x - direction_x * head_length - side_x * head_length * 0.45F,
                    end.y - direction_y * head_length - side_y * head_length * 0.45F
                };
                DrawLineEx(end, left, line_width, color);
                DrawLineEx(end, right, line_width, color);
            }
        }
    }
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

}  // namespace

RenderLod resolve_render_lod(
    const Frame& frame,
    const Camera2D& camera,
    Rectangle viewport,
    LodMode mode
) {
    switch (mode) {
    case LodMode::ForceMacro:
        return RenderLod::Macro;
    case LodMode::ForceMedium:
        return RenderLod::Medium;
    case LodMode::ForceMicro:
        return RenderLod::Micro;
    case LodMode::Auto:
        break;
    }

    const double world_area = std::max(
        static_cast<double>(frame.layout.world_width) *
            static_cast<double>(frame.layout.world_height),
        1.0
    );
    const double world_density =
        static_cast<double>(frame.entities.size()) / world_area;
    const double zoom = std::max(static_cast<double>(camera.zoom), 0.001);

    // Approximate the screen-space nearest-neighbor spacing.  Unlike the old
    // threshold, this changes perceptibly as the user zooms and corresponds to
    // whether individual marks can actually be resolved by the eye.
    const double spacing_pixels = world_density > 0.0
        ? zoom / std::sqrt(world_density)
        : std::numeric_limits<double>::infinity();

    const double viewport_scale = std::sqrt(
        std::max(0.25, static_cast<double>(viewport.width * viewport.height) /
            (960.0 * 720.0))
    );

    if (spacing_pixels < 2.8 / viewport_scale) {
        return RenderLod::Macro;
    }
    if (spacing_pixels < 8.0 / viewport_scale) {
        return RenderLod::Medium;
    }
    return RenderLod::Micro;
}

const char* render_lod_name(RenderLod lod) noexcept {
    switch (lod) {
    case RenderLod::Macro:
        return "macro field + flow";
    case RenderLod::Medium:
        return "medium sampled agents";
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

Color color_for_entity(const EntitySample& entity, float max_energy) {
    const float energy = clamp01(
        entity.energy / std::max(max_energy, 1.0e-6F)
    );
    const float integrity = clamp01(entity.integrity);

    if (entity.group_id == 0) {
        const unsigned char value = static_cast<unsigned char>(
            176.0F + 79.0F * energy
        );
        return Color{
            value,
            value,
            static_cast<unsigned char>(
                std::clamp(static_cast<float>(value) * (0.72F + 0.28F * integrity),
                    0.0F, 255.0F)
            ),
            245
        };
    }

    const std::uint64_t hash = mix_id(entity.group_id);
    const float hue = static_cast<float>(hash & 0xFFFFU) / 65535.0F;
    const float saturation = 0.62F + 0.22F * integrity;
    const float value = 0.74F + 0.26F * energy;
    return hsv_color(hue, saturation, value, 245);
}

WorldRenderer::~WorldRenderer() {
    if (heatmap_.id != 0) {
        UnloadTexture(heatmap_);
    }
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

    for (auto& resource : previous_resources_) {
        resource.clear();
    }
    previous_hazard_.clear();
    resource_scale_initialized_.fill(false);

    Image image = GenImageColor(
        static_cast<int>(grid_x_),
        static_cast<int>(grid_y_),
        BLACK
    );
    heatmap_ = LoadTextureFromImage(image);
    UnloadImage(image);
    SetTextureFilter(heatmap_, TEXTURE_FILTER_POINT);
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

    double speed_sum = 0.0;

    for (const EntitySample& entity : frame.entities) {
        current_positions_.emplace(
            entity.entity_id,
            PositionSample{entity.x, entity.y, entity.vx, entity.vy}
        );

        const float speed = std::sqrt(entity.vx * entity.vx + entity.vy * entity.vy);
        speed_sum += speed;
        if (speed > 0.01F) {
            ++diagnostics_.moving_entities;
        }

        if (!first_observation &&
            previous_positions_.find(entity.entity_id) == previous_positions_.end()) {
            ++diagnostics_.births;
            births.push_back(Candidate{entity.entity_id, entity.x, entity.y});
        }

        if (entity.action_success != 0) {
            switch (static_cast<Action>(entity.action)) {
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
    RenderLod lod,
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
        std::vector<float> scratch(
            frame.resources.begin() + static_cast<std::ptrdiff_t>(offset),
            frame.resources.begin() + static_cast<std::ptrdiff_t>(offset + cell_count)
        );
        std::vector<float> low_scratch = scratch;
        resource_low_[channel] = quantile(low_scratch, 0.02F);
        resource_high_[channel] = quantile(scratch, 0.98F);
        if (resource_high_[channel] - resource_low_[channel] < 1.0e-5F) {
            resource_high_[channel] = resource_low_[channel] + 1.0F;
        }
        resource_scale_initialized_[channel] = true;
    }

    static thread_local std::vector<float> density;
    static thread_local std::vector<float> blurred_density;
    density.assign(cell_count, 0.0F);
    blurred_density.assign(cell_count, 0.0F);

    const float world_width = std::max(frame.layout.world_width, 1.0F);
    const float world_height = std::max(frame.layout.world_height, 1.0F);

    if (options.show_population_density && lod != RenderLod::Micro) {
        for (const EntitySample& entity : frame.entities) {
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

        if (lod == RenderLod::Macro) {
            for (std::uint32_t y = 0; y < frame.layout.grid_y; ++y) {
                for (std::uint32_t x = 0; x < frame.layout.grid_x; ++x) {
                    float sum = 0.0F;
                    float weight = 0.0F;
                    for (int dy = -1; dy <= 1; ++dy) {
                        for (int dx = -1; dx <= 1; ++dx) {
                            const int sample_x = std::clamp(
                                static_cast<int>(x) + dx,
                                0,
                                static_cast<int>(frame.layout.grid_x) - 1
                            );
                            const int sample_y = std::clamp(
                                static_cast<int>(y) + dy,
                                0,
                                static_cast<int>(frame.layout.grid_y) - 1
                            );
                            const float local_weight = (dx == 0 && dy == 0) ? 2.0F : 1.0F;
                            sum += density[static_cast<std::size_t>(sample_y) *
                                frame.layout.grid_x + sample_x] * local_weight;
                            weight += local_weight;
                        }
                    }
                    blurred_density[static_cast<std::size_t>(y) * frame.layout.grid_x + x] =
                        sum / weight;
                }
            }
        } else {
            blurred_density = density;
        }
    }

    float density_max = 1.0F;
    for (float value : blurred_density) {
        density_max = std::max(density_max, value);
    }
    const float density_divisor = std::log1p(density_max);

    const float scale_low = resource_low_[channel];
    const float scale_span = std::max(
        resource_high_[channel] - resource_low_[channel],
        1.0e-5F
    );

    const bool has_previous_resource =
        previous_resources_[channel].size() == cell_count;
    const bool has_previous_hazard = previous_hazard_.size() == cell_count;

    double resource_sum = 0.0;
    double hazard_sum = 0.0;
    double change_sum = 0.0;

    for (std::size_t index = 0; index < cell_count; ++index) {
        const float resource_value = frame.resources[offset + index];
        const float normalized_resource =
            (resource_value - scale_low) / scale_span;
        const float population_density = density_divisor > 0.0F
            ? std::log1p(blurred_density[index]) / density_divisor
            : 0.0F;

        float resource_change = 0.0F;
        float hazard_change = 0.0F;
        if (has_previous_resource) {
            resource_change = (resource_value - previous_resources_[channel][index]) /
                std::max(scale_span * 0.035F, 1.0e-5F);
        }
        if (has_previous_hazard) {
            hazard_change = (frame.hazard[index] - previous_hazard_[index]) / 0.06F;
        }

        pixels_[index] = heat_color(
            channel,
            normalized_resource,
            frame.hazard[index],
            population_density,
            resource_change,
            hazard_change,
            lod,
            options
        );

        resource_sum += clamp01(normalized_resource);
        hazard_sum += frame.hazard[index];
        change_sum += std::abs(std::clamp(resource_change, -1.0F, 1.0F)) +
            0.5 * std::abs(std::clamp(hazard_change, -1.0F, 1.0F));
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

    previous_resources_[channel].assign(
        frame.resources.begin() + static_cast<std::ptrdiff_t>(offset),
        frame.resources.begin() + static_cast<std::ptrdiff_t>(offset + cell_count)
    );
    previous_hazard_ = frame.hazard;

    UpdateTexture(heatmap_, pixels_.data());
    SetTextureFilter(
        heatmap_,
        lod == RenderLod::Macro
            ? TEXTURE_FILTER_BILINEAR
            : TEXTURE_FILTER_POINT
    );
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
    const RenderLod lod = resolve_render_lod(
        frame,
        camera,
        viewport,
        options.lod_mode
    );

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

    if (lod == RenderLod::Macro ||
        (lod == RenderLod::Medium && options.show_velocity)) {
        draw_flow_field(frame, camera, lod == RenderLod::Macro);
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
        if (lod == RenderLod::Macro) {
            constexpr int columns = 24;
            constexpr int rows = 15;
            constexpr int kinds = 4;
            std::array<std::array<std::uint16_t, columns * rows>, kinds> counts{};

            for (const EventMarker& marker : event_markers_) {
                const int column = std::clamp(
                    static_cast<int>(marker.x / std::max(world_width, 1.0F) * columns),
                    0, columns - 1
                );
                const int row = std::clamp(
                    static_cast<int>(marker.y / std::max(world_height, 1.0F) * rows),
                    0, rows - 1
                );
                const int kind = static_cast<int>(marker.kind);
                std::uint16_t& count = counts[kind][row * columns + column];
                count = static_cast<std::uint16_t>(std::min<int>(65535, count + 1));
            }

            const float cell_width = world_width / columns;
            const float cell_height = world_height / rows;
            for (int kind = 0; kind < kinds; ++kind) {
                for (int row = 0; row < rows; ++row) {
                    for (int column = 0; column < columns; ++column) {
                        const std::uint16_t count = counts[kind][row * columns + column];
                        if (count == 0) {
                            continue;
                        }
                        const float radius = std::min(cell_width, cell_height) *
                            std::clamp(0.12F + std::log1p(static_cast<float>(count)) * 0.08F,
                                0.12F, 0.42F);
                        const Vector2 position{
                            (static_cast<float>(column) + 0.5F) * cell_width,
                            (static_cast<float>(row) + 0.5F) * cell_height
                        };
                        const Color color = Fade(
                            event_color(static_cast<EventKind>(kind)),
                            0.24F + std::min(0.42F, std::log1p(static_cast<float>(count)) * 0.07F)
                        );
                        DrawCircleV(position, radius, color);
                        DrawCircleLines(
                            static_cast<int>(position.x),
                            static_cast<int>(position.y),
                            radius,
                            Fade(event_color(static_cast<EventKind>(kind)), 0.70F)
                        );
                    }
                }
            }
        } else {
            const std::size_t marker_budget =
                lod == RenderLod::Medium ? 720 : 1600;
            std::size_t drawn = 0;

            for (auto iterator = event_markers_.rbegin();
                 iterator != event_markers_.rend() && drawn < marker_budget;
                 ++iterator) {
                const EventMarker& marker = *iterator;
                if (marker.x < left || marker.x > right || marker.y < top || marker.y > bottom) {
                    continue;
                }

                const float age = frame.tick >= marker.tick
                    ? static_cast<float>(frame.tick - marker.tick)
                    : 0.0F;
                const float life = 1.0F - clamp01(age /
                    static_cast<float>(event_ttl(marker.kind)));
                const float pulse = 0.82F + 0.18F * std::sin(age * 0.72F);
                const float radius = (3.8F + 5.5F * life) * pulse /
                    std::max(camera.zoom, 0.001F);
                const float width = 1.2F /
                    std::max(camera.zoom, 0.001F);
                const Vector2 center{marker.x, marker.y};
                const Color color = Fade(event_color(marker.kind), 0.30F + 0.68F * life);

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

    std::size_t target_entities = 0;
    float radius_pixels = 0.0F;
    if (lod == RenderLod::Medium) {
        target_entities = 26000;
        radius_pixels = 2.15F;
    } else if (lod == RenderLod::Micro) {
        target_entities = std::numeric_limits<std::size_t>::max();
        radius_pixels = 3.15F;
    }

    const std::size_t stride = target_entities == std::numeric_limits<std::size_t>::max()
        ? 1
        : std::max<std::size_t>(
            1,
            (frame.entities.size() + target_entities - 1) / target_entities
        );
    const float radius = radius_pixels /
        std::max(camera.zoom, 0.001F);
    const float padding = std::max(radius * 5.0F, 1.0F);

    if (lod != RenderLod::Macro) {
        // One-frame displacement trails make migration visible without requiring
        // a persistent particle effect.  V increases their contrast and length.
        rlSetTexture(0);
        rlBegin(RL_LINES);
        for (const EntitySample& entity : frame.entities) {
            if (!is_visible(entity, left, top, right, bottom, padding)) {
                continue;
            }
            if (stride > 1 &&
                entity.entity_id != options.selected_entity_id &&
                mix_id(entity.entity_id) % stride != 0) {
                continue;
            }

            const auto previous = previous_positions_.find(entity.entity_id);
            if (previous == previous_positions_.end()) {
                continue;
            }

            const Vector2 current{entity.x, entity.y};
            Vector2 old = previous_endpoint(
                current,
                Vector2{previous->second.x, previous->second.y},
                world_width,
                world_height
            );
            if (options.show_velocity) {
                old.x -= entity.vx * 2.5F;
                old.y -= entity.vy * 2.5F;
            }

            const float speed = std::sqrt(entity.vx * entity.vx + entity.vy * entity.vy);
            if (speed < 0.01F) {
                continue;
            }
            const Color trail = Fade(
                Color{101, 224, 255, 255},
                options.show_velocity ? 0.62F : 0.26F
            );
            rlColor4ub(trail.r, trail.g, trail.b, trail.a);
            rlVertex2f(old.x, old.y);
            rlVertex2f(current.x, current.y);
        }
        rlEnd();

        // Dark underlay keeps agents distinct from the ecology texture.
        rlSetTexture(0);
        rlBegin(RL_QUADS);
        rlColor4ub(2, 5, 8, lod == RenderLod::Medium ? 210 : 235);
        const float outline = radius * (lod == RenderLod::Medium ? 1.55F : 1.42F);
        for (const EntitySample& entity : frame.entities) {
            if (!is_visible(entity, left, top, right, bottom, padding)) {
                continue;
            }
            if (stride > 1 &&
                entity.entity_id != options.selected_entity_id &&
                mix_id(entity.entity_id) % stride != 0) {
                continue;
            }
            rlVertex2f(entity.x, entity.y - outline);
            rlVertex2f(entity.x + outline, entity.y);
            rlVertex2f(entity.x, entity.y + outline);
            rlVertex2f(entity.x - outline, entity.y);
        }
        rlEnd();

        if (lod == RenderLod::Medium) {
            rlSetTexture(0);
            rlBegin(RL_QUADS);
            for (const EntitySample& entity : frame.entities) {
                if (!is_visible(entity, left, top, right, bottom, padding)) {
                    continue;
                }
                if (stride > 1 &&
                    entity.entity_id != options.selected_entity_id &&
                    mix_id(entity.entity_id) % stride != 0) {
                    continue;
                }
                const Color color = color_for_entity(entity, frame.layout.max_energy);
                rlColor4ub(color.r, color.g, color.b, color.a);
                rlVertex2f(entity.x, entity.y - radius);
                rlVertex2f(entity.x + radius, entity.y);
                rlVertex2f(entity.x, entity.y + radius);
                rlVertex2f(entity.x - radius, entity.y);
            }
            rlEnd();
        } else {
            // Moving micro agents become oriented triangles.  Resting agents remain
            // diamonds, so action and direction are legible after zooming in.
            rlSetTexture(0);
            rlBegin(RL_TRIANGLES);
            for (const EntitySample& entity : frame.entities) {
                if (!is_visible(entity, left, top, right, bottom, padding)) {
                    continue;
                }
                const float speed = std::sqrt(entity.vx * entity.vx + entity.vy * entity.vy);
                if (speed < 0.012F) {
                    continue;
                }
                const float dx = entity.vx / speed;
                const float dy = entity.vy / speed;
                const float sx = -dy;
                const float sy = dx;
                const Color color = color_for_entity(entity, frame.layout.max_energy);
                rlColor4ub(color.r, color.g, color.b, color.a);
                rlVertex2f(entity.x + dx * radius * 1.65F,
                    entity.y + dy * radius * 1.65F);
                rlVertex2f(entity.x - dx * radius * 0.78F + sx * radius,
                    entity.y - dy * radius * 0.78F + sy * radius);
                rlVertex2f(entity.x - dx * radius * 0.78F - sx * radius,
                    entity.y - dy * radius * 0.78F - sy * radius);
            }
            rlEnd();

            rlSetTexture(0);
            rlBegin(RL_QUADS);
            for (const EntitySample& entity : frame.entities) {
                if (!is_visible(entity, left, top, right, bottom, padding)) {
                    continue;
                }
                const float speed = std::sqrt(entity.vx * entity.vx + entity.vy * entity.vy);
                if (speed >= 0.012F) {
                    continue;
                }
                const Color color = color_for_entity(entity, frame.layout.max_energy);
                rlColor4ub(color.r, color.g, color.b, color.a);
                rlVertex2f(entity.x, entity.y - radius);
                rlVertex2f(entity.x + radius, entity.y);
                rlVertex2f(entity.x, entity.y + radius);
                rlVertex2f(entity.x - radius, entity.y);
            }
            rlEnd();
        }
    }

    DrawRectangleLinesEx(
        Rectangle{0.0F, 0.0F, world_width, world_height},
        1.5F / std::max(camera.zoom, 0.001F),
        RAYWHITE
    );

    // Selected agents are always drawn, even when macro LOD suppresses all other
    // individuals or medium sampling would otherwise discard this ID.
    if (options.selected_entity_id != 0) {
        const EntitySample* selected = nullptr;
        for (const EntitySample& entity : frame.entities) {
            if (entity.entity_id == options.selected_entity_id) {
                selected = &entity;
                break;
            }
        }

        if (selected != nullptr) {
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

            DrawCircleV(center, selected_radius * 0.38F, YELLOW);
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
            DrawLineEx(
                center,
                Vector2{center.x + selected->vx * 9.0F,
                    center.y + selected->vy * 9.0F},
                1.8F / std::max(camera.zoom, 0.001F),
                YELLOW
            );
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
