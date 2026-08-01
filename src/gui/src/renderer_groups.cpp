#include "eco/renderer.hpp"
#include "render/renderer_internal.hpp"
#include "render/renderer_state.hpp"

#include <algorithm>
#include <cmath>
#include <cstddef>
#include <cstdint>

namespace eco {
using namespace render_internal;

void WorldRenderer::draw_group_history_overlay(
    const Frame& frame,
    const Camera2D& camera,
    Rectangle viewport,
    const RenderDetail& detail,
    const RenderOptions& options,
    std::uint64_t selected_group_id,
    const OverlayBudget& budget,
    float weight
) const {
    weight = clamp01(weight);
    const auto& display_groups = select_group_behaviors(
        state_->groups, options.overlay_temporal
    );
    if (weight < 0.035F || display_groups.empty() ||
        (!options.show_group_trails && selected_group_id == 0)) {
        return;
    }

    const float inverse_zoom = 1.0F / std::max(camera.zoom, 0.001F);
    const auto nearest_periodic = [](float value, float target, float extent) {
        if (extent <= 0.0F) {
            return value;
        }
        return value + std::round((target - value) / extent) * extent;
    };
    const auto segment_visible = [&](Vector2 start, Vector2 end, float maximum_pixels) {
        const Vector2 screen_start = GetWorldToScreen2D(start, camera);
        const Vector2 screen_end = GetWorldToScreen2D(end, camera);
        const float dx = screen_end.x - screen_start.x;
        const float dy = screen_end.y - screen_start.y;
        if (!finite_value(dx) || !finite_value(dy) ||
            dx * dx + dy * dy > maximum_pixels * maximum_pixels) {
            return false;
        }
        const Rectangle expanded{
            viewport.x - 32.0F, viewport.y - 32.0F,
            viewport.width + 64.0F, viewport.height + 64.0F
        };
        const float left = std::min(screen_start.x, screen_end.x);
        const float top = std::min(screen_start.y, screen_end.y);
        const float right = std::max(screen_start.x, screen_end.x);
        const float bottom = std::max(screen_start.y, screen_end.y);
        return right >= expanded.x && bottom >= expanded.y &&
               left <= expanded.x + expanded.width &&
               top <= expanded.y + expanded.height;
    };
    const std::size_t remaining_marker_budget =
        budget.group_markers > state_->overlay_usage.group_markers
            ? budget.group_markers - state_->overlay_usage.group_markers
            : 0U;
    const std::size_t ordinary_budget = std::min<std::size_t>(
        remaining_marker_budget,
        static_cast<std::size_t>(
            lerp_value(8.0F, 26.0F,
                clamp01(detail.density_weight + 0.35F * detail.agent_weight))
        )
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
        const float center_x = nearest_periodic(
            group.x, camera.target.x, frame.layout.world_width);
        const float center_y = nearest_periodic(
            group.y, camera.target.y, frame.layout.world_height);
        constexpr int segments = 40;
        Vector2 previous{};
        bool has_previous = false;
        for (int segment = 0; segment <= segments; ++segment) {
            const float angle = 6.28318530718F * static_cast<float>(segment) /
                static_cast<float>(segments);
            const float local_x = std::cos(angle) * major;
            const float local_y = std::sin(angle) * minor;
            const Vector2 point{
                center_x + local_x * cosine - local_y * sine,
                center_y + local_x * sine + local_y * cosine
            };
            if (has_previous &&
                segment_visible(previous, point, 160.0F)) {
                DrawLineEx(previous, point, 1.05F * inverse_zoom, Fade(color, alpha));
            }
            previous = point;
            has_previous = true;
        }
    };

    for (const GroupBehaviorSummary& group : display_groups) {
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

        const auto trail_iterator = state_->groups.trails.find(group.group_id);
        const bool has_trail = options.show_group_trails &&
            trail_iterator != state_->groups.trails.end() &&
            trail_iterator->second.size() >= 2U;
        Color color = color_for_group_id(
            group.visual_key != 0 ? group.visual_key : group.group_id, 255);
        const float selected_boost = selected ? 1.0F : 0.0F;
        const float base_alpha = weight * (0.16F + 0.34F * group.coherence +
            0.20F * group.active_fraction + 0.32F * selected_boost);
        const float member_curve = std::clamp(
            std::log1p(static_cast<float>(group.members)) / 8.0F,
            0.0F,
            1.0F
        );
        if (has_trail) {
            const auto& trail = trail_iterator->second;
            const std::size_t first = trail.size() > 36U ? trail.size() - 36U : 0U;
            for (std::size_t index = first + 1U; index < trail.size(); ++index) {
                const GroupTrailPoint& before = trail[index - 1U];
                const GroupTrailPoint& after = trail[index];
                const float dx = wrapped_delta(after.x - before.x, frame.layout.world_width);
                const float dy = wrapped_delta(after.y - before.y, frame.layout.world_height);
                if (!finite_value(dx) || !finite_value(dy)) {
                    continue;
                }
                const Vector2 start{
                    nearest_periodic(before.x, camera.target.x, frame.layout.world_width),
                    nearest_periodic(before.y, camera.target.y, frame.layout.world_height)
                };
                const Vector2 end{start.x + dx, start.y + dy};
                if (!segment_visible(start, end, selected ? 260.0F : 130.0F) ||
                    state_->overlay_usage.group_trail_segments >=
                        budget.group_trail_segments) {
                    continue;
                }
                const float age = static_cast<float>(index - first) /
                    static_cast<float>(std::max<std::size_t>(trail.size() - first, 1U));
                const float alpha = base_alpha * (0.12F + 0.88F * age * age);
                const float width = (0.65F + 1.55F * member_curve +
                    (selected ? 1.15F : 0.0F)) * inverse_zoom;
                DrawLineEx(start, end, width + 2.0F * inverse_zoom, Fade(BLACK, alpha * 0.65F));
                DrawLineEx(start, end, width, Fade(color, alpha));
                ++state_->overlay_usage.group_trail_segments;
            }
        }

        const bool draw_shape = selected ||
            (options.show_group_trails && detail.agent_weight > 0.18F &&
             drawn < std::max<std::size_t>(ordinary_budget / 3U, 2U));
        if (draw_shape) {
            draw_ellipse(group, color, selected ? 0.78F : 0.18F * weight);
        }

        const Vector2 display_center{
            nearest_periodic(group.x, camera.target.x, frame.layout.world_width),
            nearest_periodic(group.y, camera.target.y, frame.layout.world_height)
        };
        const float centroid_radius = (selected ? 4.8F : 2.6F) * inverse_zoom;
        DrawCircleLines(
            static_cast<int>(display_center.x),
            static_cast<int>(display_center.y),
            centroid_radius,
            Fade(color, selected ? 0.95F : 0.38F * weight)
        );
        if (group.dominant_action != Action::Rest &&
            group.dominant_action_fraction > 0.14F) {
            draw_action_glyph(
                group.dominant_action,
                display_center,
                selected ? 7.2F : 4.8F,
                camera,
                selected ? 0.96F : 0.42F * weight,
                Vector2{group.mean_vx, group.mean_vy}
            );
        }
        ++state_->overlay_usage.group_markers;
        if (!selected) {
            ++drawn;
        }
    }
}


void WorldRenderer::draw_group_landmarks_overlay(
    const Frame& frame,
    const Camera2D& camera,
    Rectangle viewport,
    const RenderDetail& detail,
    const RenderOptions& options,
    std::uint64_t selected_group_id,
    const OverlayBudget& budget,
    float weight
) const {
    weight = clamp01(weight);
    const auto& display_groups = select_group_behaviors(
        state_->groups, options.overlay_temporal
    );
    if (!options.show_group_landmarks || weight < 0.04F ||
        display_groups.empty() ||
        state_->overlay_usage.group_markers >= budget.group_markers) {
        return;
    }

    const float inverse_zoom = 1.0F / std::max(camera.zoom, 0.001F);
    const auto nearest_periodic = [](float value, float target, float extent) {
        if (extent <= 0.0F) {
            return value;
        }
        return value + std::round((target - value) / extent) * extent;
    };
    const Rectangle expanded{
        viewport.x - 24.0F,
        viewport.y - 24.0F,
        viewport.width + 48.0F,
        viewport.height + 48.0F
    };
    const std::size_t remaining = budget.group_markers -
        state_->overlay_usage.group_markers;
    const std::size_t landmark_limit = std::min<std::size_t>(
        remaining,
        static_cast<std::size_t>(std::clamp(
            lerp_value(5.0F, 12.0F,
                clamp01(detail.density_weight + 0.25F * detail.agent_weight)),
            4.0F,
            14.0F
        ))
    );

    std::size_t drawn = 0;
    for (const GroupBehaviorSummary& group : display_groups) {
        if (drawn >= landmark_limit || group.members < 12U) {
            break;
        }
        if (options.focus_selected_group && selected_group_id != 0 &&
            group.group_id != selected_group_id) {
            continue;
        }

        const Vector2 world_center{
            nearest_periodic(group.x, camera.target.x, frame.layout.world_width),
            nearest_periodic(group.y, camera.target.y, frame.layout.world_height)
        };
        const Vector2 screen = GetWorldToScreen2D(world_center, camera);
        if (screen.x < expanded.x || screen.y < expanded.y ||
            screen.x > expanded.x + expanded.width ||
            screen.y > expanded.y + expanded.height) {
            continue;
        }

        const bool selected = group.group_id == selected_group_id &&
            selected_group_id != 0;
        const float member_curve = std::clamp(
            std::log1p(static_cast<float>(group.members)) / 7.8F,
            0.0F,
            1.0F
        );
        const float radius_pixels = 3.0F + 3.8F * member_curve +
            (selected ? 2.0F : 0.0F);
        const float radius = radius_pixels * inverse_zoom;
        const std::uint64_t color_key = group.visual_key != 0
            ? group.visual_key
            : group.group_id;
        const Color color = color_for_group_id(
            color_key,
            static_cast<unsigned char>(std::clamp(
                (0.42F + 0.48F * weight + (selected ? 0.10F : 0.0F)) * 255.0F,
                0.0F,
                255.0F
            ))
        );

        DrawCircleV(world_center, radius + 1.8F * inverse_zoom,
            Fade(BLACK, 0.62F * weight));
        DrawCircleLines(
            static_cast<int>(world_center.x),
            static_cast<int>(world_center.y),
            radius,
            color
        );
        DrawCircleV(world_center, std::max(0.85F, radius_pixels * 0.22F) * inverse_zoom,
            Fade(color, selected ? 0.95F : 0.72F));

        const float speed = std::sqrt(
            group.mean_vx * group.mean_vx + group.mean_vy * group.mean_vy
        );
        if (finite_value(speed) && speed > 0.012F && group.coherence > 0.14F) {
            const Vector2 direction{
                group.mean_vx / speed,
                group.mean_vy / speed
            };
            const float length = (7.0F + 14.0F * group.coherence +
                4.0F * member_curve) * inverse_zoom;
            const Vector2 end{
                world_center.x + direction.x * length,
                world_center.y + direction.y * length
            };
            DrawLineEx(world_center, end,
                (0.8F + 1.0F * member_curve) * inverse_zoom,
                Fade(color, 0.68F * weight));
        } else if (group.dominant_action != Action::Rest &&
            group.dominant_action_fraction > 0.28F &&
            !action_uses_direction(group.dominant_action)) {
            draw_action_glyph(
                group.dominant_action,
                world_center,
                3.6F + 2.0F * member_curve,
                camera,
                0.48F * weight
            );
        }

        ++drawn;
        ++state_->overlay_usage.group_markers;
    }
}

std::uint64_t WorldRenderer::pick_group(
    const Frame& frame,
    const Camera2D& camera,
    Vector2 screen_position,
    float radius_pixels
) const {
    float best_score = std::numeric_limits<float>::infinity();
    std::uint64_t selected = 0;

    const float world_width = frame.layout.world_width;
    const float world_height = frame.layout.world_height;
    const auto& display_groups = select_group_behaviors(
        state_->groups, OverlayTemporalMode::Stable
    );
    for (const GroupBehaviorSummary& group : display_groups) {
        if (group.group_id == 0 || group.members == 0 ||
            !finite_value(group.x) || !finite_value(group.y)) {
            continue;
        }
        const float member_bonus = std::clamp(
            std::log1p(static_cast<float>(group.members)) * 1.35F,
            0.0F,
            13.0F
        );
        const float threshold = radius_pixels + member_bonus;
        const float threshold_squared = threshold * threshold;

        for (int offset_y = -1; offset_y <= 1; ++offset_y) {
            for (int offset_x = -1; offset_x <= 1; ++offset_x) {
                const Vector2 screen = GetWorldToScreen2D(
                    Vector2{
                        group.x + static_cast<float>(offset_x) * world_width,
                        group.y + static_cast<float>(offset_y) * world_height
                    },
                    camera
                );
                const float dx = screen.x - screen_position.x;
                const float dy = screen.y - screen_position.y;
                const float distance_squared = dx * dx + dy * dy;
                if (distance_squared > threshold_squared) {
                    continue;
                }
                const float score = distance_squared /
                    std::max(threshold_squared, 1.0F) -
                    0.025F * std::log1p(static_cast<float>(group.members));
                if (score < best_score) {
                    best_score = score;
                    selected = group.group_id;
                }
            }
        }
    }
    return selected;
}

}  // namespace eco
