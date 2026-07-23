#include "eco/renderer.hpp"

#include <algorithm>
#include <cmath>
#include <cstddef>
#include <unordered_map>
#include <unordered_set>
#include <vector>

#include <rlgl.h>

namespace eco {
namespace {

float clamp01(float value) {
    return std::clamp(value, 0.0F, 1.0F);
}

std::uint64_t mix_id(std::uint64_t value) {
    value ^= value >> 33U;
    value *= 0xff51afd7ed558ccdULL;
    value ^= value >> 33U;
    value *= 0xc4ceb9fe1a85ec53ULL;
    value ^= value >> 33U;
    return value;
}

Color heat_color(
    float resource,
    float hazard,
    bool show_hazard
) {
    resource = std::sqrt(clamp01(resource));
    hazard = show_hazard
        ? std::pow(clamp01(hazard), 1.35F)
        : 0.0F;

    // Keep the environment readable without letting hazard dominate the
    // screen.  Resources use a dark teal/green ramp; hazard adds amber-red
    // contrast, but never becomes the fully saturated magenta blocks from
    // the previous palette.
    const float red =
        12.0F + resource * 18.0F + hazard * 92.0F;
    const float green =
        18.0F + resource * 112.0F + hazard * 16.0F;
    const float blue =
        28.0F + resource * 72.0F - hazard * 10.0F;

    return Color{
        static_cast<unsigned char>(
            std::clamp(red, 0.0F, 255.0F)
        ),
        static_cast<unsigned char>(
            std::clamp(green, 0.0F, 255.0F)
        ),
        static_cast<unsigned char>(
            std::clamp(blue, 0.0F, 255.0F)
        ),
        255
    };
}

struct MotionSegment {
    Vector2 from{};
    Vector2 to{};
};

struct LifeMarker {
    Vector2 position{};
    std::uint64_t tick = 0;
};

struct VisualHistory {
    bool initialized = false;
    std::uint64_t tick = 0;
    std::unordered_map<std::uint64_t, Vector2> previous_positions;
    std::vector<MotionSegment> motion;
    std::vector<LifeMarker> births;
    std::vector<LifeMarker> deaths;
};

VisualHistory& visual_history() {
    static VisualHistory history;
    return history;
}

void prune_markers(
    std::vector<LifeMarker>& markers,
    std::uint64_t tick
) {
    constexpr std::uint64_t lifetime = 24;
    std::erase_if(
        markers,
        [tick](const LifeMarker& marker) {
            return tick >= marker.tick &&
                   tick - marker.tick > lifetime;
        }
    );

    constexpr std::size_t maximum_markers = 4096;
    if (markers.size() > maximum_markers) {
        markers.erase(
            markers.begin(),
            markers.begin() +
                static_cast<std::ptrdiff_t>(
                    markers.size() - maximum_markers
                )
        );
    }
}

void update_visual_history(const Frame& frame) {
    VisualHistory& history = visual_history();
    if (history.initialized && history.tick == frame.tick) {
        return;
    }

    history.motion.clear();

    std::unordered_map<std::uint64_t, Vector2> current_positions;
    current_positions.reserve(frame.entities.size() * 2U + 1U);

    const std::size_t motion_stride = std::max<std::size_t>(
        1U,
        frame.entities.size() / 12000U
    );

    for (const EntitySample& entity : frame.entities) {
        const Vector2 current{entity.x, entity.y};
        current_positions.emplace(entity.entity_id, current);

        if (!history.initialized) {
            continue;
        }

        const auto previous =
            history.previous_positions.find(entity.entity_id);

        if (previous == history.previous_positions.end()) {
            history.births.push_back(
                LifeMarker{current, frame.tick}
            );
            continue;
        }

        float dx = current.x - previous->second.x;
        float dy = current.y - previous->second.y;

        // The simulation can use periodic world boundaries.  Draw the short
        // wrapped displacement instead of a line crossing the whole map.
        if (frame.layout.world_width > 0.0F &&
            std::abs(dx) > frame.layout.world_width * 0.5F) {
            dx -= std::copysign(frame.layout.world_width, dx);
        }
        if (frame.layout.world_height > 0.0F &&
            std::abs(dy) > frame.layout.world_height * 0.5F) {
            dy -= std::copysign(frame.layout.world_height, dy);
        }

        const float distance_squared = dx * dx + dy * dy;
        if (distance_squared < 1.0e-5F) {
            continue;
        }

        const std::uint64_t sample_hash =
            mix_id(entity.entity_id ^ frame.tick);
        if (sample_hash % motion_stride != 0U) {
            continue;
        }

        history.motion.push_back(
            MotionSegment{
                Vector2{current.x - dx, current.y - dy},
                current
            }
        );
    }

    if (history.initialized) {
        for (const auto& [entity_id, position] :
             history.previous_positions) {
            if (!current_positions.contains(entity_id)) {
                history.deaths.push_back(
                    LifeMarker{position, frame.tick}
                );
            }
        }
    }

    history.previous_positions = std::move(current_positions);
    history.tick = frame.tick;
    history.initialized = true;

    prune_markers(history.births, frame.tick);
    prune_markers(history.deaths, frame.tick);
}

void draw_motion_history(
    const Frame& frame,
    const Camera2D& camera
) {
    const VisualHistory& history = visual_history();
    if (history.motion.empty()) {
        return;
    }

    const Color trail = Color{100, 220, 255, 105};
    rlSetTexture(0);
    rlBegin(RL_LINES);
    rlColor4ub(trail.r, trail.g, trail.b, trail.a);

    for (const MotionSegment& segment : history.motion) {
        rlVertex2f(segment.from.x, segment.from.y);
        rlVertex2f(segment.to.x, segment.to.y);
    }

    rlEnd();

    static_cast<void>(frame);
    static_cast<void>(camera);
}

void draw_lifecycle_markers(
    const Frame& frame,
    const Camera2D& camera
) {
    const VisualHistory& history = visual_history();
    const float inverse_zoom =
        1.0F / std::max(camera.zoom, 0.001F);

    for (const LifeMarker& marker : history.births) {
        const float age = static_cast<float>(
            frame.tick >= marker.tick
                ? frame.tick - marker.tick
                : 0U
        );
        const float radius = (4.0F + age * 0.45F) * inverse_zoom;
        const float alpha = std::clamp(1.0F - age / 24.0F, 0.0F, 1.0F);
        DrawCircleLines(
            static_cast<int>(marker.position.x),
            static_cast<int>(marker.position.y),
            radius,
            Fade(Color{90, 255, 220, 255}, alpha)
        );
    }

    for (const LifeMarker& marker : history.deaths) {
        const float age = static_cast<float>(
            frame.tick >= marker.tick
                ? frame.tick - marker.tick
                : 0U
        );
        const float half_size = (3.0F + age * 0.20F) * inverse_zoom;
        const float alpha = std::clamp(1.0F - age / 24.0F, 0.0F, 1.0F);
        const Color color = Fade(Color{255, 92, 92, 255}, alpha);

        DrawLineEx(
            Vector2{
                marker.position.x - half_size,
                marker.position.y - half_size
            },
            Vector2{
                marker.position.x + half_size,
                marker.position.y + half_size
            },
            1.2F * inverse_zoom,
            color
        );
        DrawLineEx(
            Vector2{
                marker.position.x - half_size,
                marker.position.y + half_size
            },
            Vector2{
                marker.position.x + half_size,
                marker.position.y - half_size
            },
            1.2F * inverse_zoom,
            color
        );
    }
}


}  // namespace

Color color_for_entity(
    const EntitySample& entity,
    float max_energy
) {
    const float energy = clamp01(
        entity.energy / std::max(max_energy, 1.0e-6F)
    );
    const float integrity = clamp01(entity.integrity);

    if (entity.group_id == 0) {
        return Color{
            static_cast<unsigned char>(185.0F + 70.0F * energy),
            static_cast<unsigned char>(210.0F + 45.0F * energy),
            static_cast<unsigned char>(220.0F + 35.0F * integrity),
            255
        };
    }

    const std::uint64_t hash = mix_id(entity.group_id);
    const float brightness = 0.72F + 0.28F * energy;

    const auto channel = [brightness](
        std::uint64_t bits
    ) -> unsigned char {
        const float base =
            105.0F + static_cast<float>(bits & 0x7FU);
        return static_cast<unsigned char>(
            std::clamp(base * brightness, 0.0F, 255.0F)
        );
    };

    return Color{
        channel(hash),
        channel(hash >> 8U),
        channel(hash >> 16U),
        static_cast<unsigned char>(190.0F + 65.0F * integrity)
    };
}


WorldRenderer::~WorldRenderer() {
    if (heatmap_.id != 0) {
        UnloadTexture(heatmap_);
    }
}

void WorldRenderer::ensure_texture(
    std::uint32_t grid_x,
    std::uint32_t grid_y
) {
    if (heatmap_.id != 0 &&
        grid_x_ == grid_x &&
        grid_y_ == grid_y) {
        return;
    }

    if (heatmap_.id != 0) {
        UnloadTexture(heatmap_);
        heatmap_ = Texture2D{};
    }

    grid_x_ = grid_x;
    grid_y_ = grid_y;
    pixels_.assign(
        static_cast<std::size_t>(grid_x_) *
            static_cast<std::size_t>(grid_y_),
        BLACK
    );

    Image image = GenImageColor(
        static_cast<int>(grid_x_),
        static_cast<int>(grid_y_),
        BLACK
    );

    heatmap_ = LoadTextureFromImage(image);
    UnloadImage(image);

    SetTextureFilter(heatmap_, TEXTURE_FILTER_POINT);
}

void WorldRenderer::update_heatmap(
    const Frame& frame,
    int resource_channel,
    bool show_hazard
) {
    ensure_texture(
        frame.layout.grid_x,
        frame.layout.grid_y
    );

    const std::size_t cell_count = frame.cell_count();
    if (frame.resources.size() < cell_count * 4U ||
        frame.hazard.size() < cell_count) {
        return;
    }

    const int channel =
        std::clamp(resource_channel, 0, 3);
    const float capacity_hint = 1.0F;

    const std::size_t offset =
        static_cast<std::size_t>(channel) *
        cell_count;

    float observed_max = 0.0F;
    for (std::size_t index = 0;
         index < cell_count;
         ++index) {
        observed_max = std::max(
            observed_max,
            frame.resources[offset + index]
        );
    }

    const float divisor = std::max(
        observed_max,
        capacity_hint
    );

    for (std::size_t index = 0;
         index < cell_count;
         ++index) {
        pixels_[index] = heat_color(
            frame.resources[offset + index] / divisor,
            frame.hazard[index],
            show_hazard
        );
    }

    UpdateTexture(heatmap_, pixels_.data());
}

void WorldRenderer::draw(
    const Frame& frame,
    const Camera2D& camera,
    const RenderOptions& options
) const {
    if (heatmap_.id == 0) {
        return;
    }

    update_visual_history(frame);

    const float world_width =
        frame.layout.world_width;
    const float world_height =
        frame.layout.world_height;

    DrawTexturePro(
        heatmap_,
        Rectangle{
            0.0F,
            0.0F,
            static_cast<float>(heatmap_.width),
            static_cast<float>(heatmap_.height)
        },
        Rectangle{
            0.0F,
            0.0F,
            world_width,
            world_height
        },
        Vector2{0.0F, 0.0F},
        0.0F,
        WHITE
    );

    if (options.show_grid &&
        frame.layout.grid_x <= 512 &&
        frame.layout.grid_y <= 512) {
        const float cell_width =
            world_width /
            static_cast<float>(frame.layout.grid_x);
        const float cell_height =
            world_height /
            static_cast<float>(frame.layout.grid_y);

        const Color grid_color = Fade(BLACK, 0.18F);

        rlSetTexture(0);
        rlBegin(RL_LINES);
        rlColor4ub(
            grid_color.r,
            grid_color.g,
            grid_color.b,
            grid_color.a
        );

        for (std::uint32_t x = 1;
             x < frame.layout.grid_x;
             ++x) {
            const float position =
                static_cast<float>(x) * cell_width;
            rlVertex2f(position, 0.0F);
            rlVertex2f(position, world_height);
        }

        for (std::uint32_t y = 1;
             y < frame.layout.grid_y;
             ++y) {
            const float position =
                static_cast<float>(y) * cell_height;
            rlVertex2f(0.0F, position);
            rlVertex2f(world_width, position);
        }

        rlEnd();
    }

    draw_motion_history(frame, camera);

    const float radius_pixels =
        frame.entities.size() > 300000
            ? 1.0F
            : frame.entities.size() > 100000
                ? 1.45F
                : 2.65F;

    const float radius =
        radius_pixels / std::max(camera.zoom, 0.001F);

    // A single dark silhouette pass separates agents from the environment
    // without issuing one draw call per entity.
    const float outline_radius = radius + 0.75F / std::max(camera.zoom, 0.001F);
    rlSetTexture(0);
    rlBegin(RL_QUADS);
    rlColor4ub(5, 8, 12, 150);
    for (const EntitySample& entity : frame.entities) {
        rlVertex2f(entity.x - outline_radius, entity.y - outline_radius);
        rlVertex2f(entity.x + outline_radius, entity.y - outline_radius);
        rlVertex2f(entity.x + outline_radius, entity.y + outline_radius);
        rlVertex2f(entity.x - outline_radius, entity.y + outline_radius);
    }
    rlEnd();

    rlSetTexture(0);
    rlBegin(RL_QUADS);

    for (const EntitySample& entity : frame.entities) {
        const Color color = color_for_entity(
            entity,
            frame.layout.max_energy
        );

        rlColor4ub(
            color.r,
            color.g,
            color.b,
            color.a
        );

        rlVertex2f(entity.x - radius, entity.y - radius);
        rlVertex2f(entity.x + radius, entity.y - radius);
        rlVertex2f(entity.x + radius, entity.y + radius);
        rlVertex2f(entity.x - radius, entity.y + radius);
    }

    rlEnd();

    if (options.show_velocity &&
        frame.entities.size() <= 80000) {
        const Color velocity_color =
            Color{110, 225, 255, 175};

        rlSetTexture(0);
        rlBegin(RL_LINES);
        rlColor4ub(
            velocity_color.r,
            velocity_color.g,
            velocity_color.b,
            velocity_color.a
        );

        for (const EntitySample& entity : frame.entities) {
            rlVertex2f(entity.x, entity.y);
            rlVertex2f(
                entity.x + entity.vx * 8.0F,
                entity.y + entity.vy * 8.0F
            );
        }

        rlEnd();
    }

    // Successful reproduction is explicitly visible even when newborns are
    // mixed into a dense population cloud.
    if (frame.entities.size() <= 150000) {
        std::size_t shown = 0;
        constexpr std::size_t maximum_markers = 2048;
        const float marker_radius =
            5.5F / std::max(camera.zoom, 0.001F);
        for (const EntitySample& entity : frame.entities) {
            if (entity.action !=
                    static_cast<std::uint8_t>(Action::Reproduce) ||
                entity.action_success == 0) {
                continue;
            }
            DrawCircleLines(
                static_cast<int>(entity.x),
                static_cast<int>(entity.y),
                marker_radius,
                Color{255, 110, 235, 230}
            );
            if (++shown >= maximum_markers) {
                break;
            }
        }
    }

    draw_lifecycle_markers(frame, camera);

    DrawRectangleLinesEx(
        Rectangle{
            0.0F,
            0.0F,
            world_width,
            world_height
        },
        1.5F / std::max(camera.zoom, 0.001F),
        RAYWHITE
    );

    if (options.selected_entity_id != 0) {
        for (const EntitySample& entity : frame.entities) {
            if (entity.entity_id ==
                options.selected_entity_id) {
                DrawCircleLines(
                    static_cast<int>(entity.x),
                    static_cast<int>(entity.y),
                    8.0F /
                        std::max(camera.zoom, 0.001F),
                    YELLOW
                );
                break;
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
    const Vector2 world_position =
        GetScreenToWorld2D(screen_position, camera);

    const float radius =
        radius_pixels /
        std::max(camera.zoom, 0.001F);
    float best_distance = radius * radius;
    std::uint64_t selected = 0;

    for (const EntitySample& entity : frame.entities) {
        const float dx = entity.x - world_position.x;
        const float dy = entity.y - world_position.y;
        const float distance = dx * dx + dy * dy;

        if (distance < best_distance) {
            best_distance = distance;
            selected = entity.entity_id;
        }
    }

    return selected;
}

}  // namespace eco
