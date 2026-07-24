#include "eco/renderer.hpp"
#include "render/renderer_internal.hpp"

#include <algorithm>
#include <cmath>
#include <cstddef>

namespace eco::render_internal {

OverlayBudget resolve_overlay_budget(
    const RenderDetail& detail,
    Rectangle viewport,
    std::size_t selected_neighbor_count
) {
    const float area = std::max(viewport.width * viewport.height, 1.0F);
    const float area_scale = std::clamp(
        area / (900.0F * 760.0F),
        0.45F,
        2.20F
    );
    const float agents = clamp01(detail.agent_weight);
    const float micro = clamp01(detail.micro_weight);
    const float density = clamp01(detail.density_weight);

    OverlayBudget budget{};
    budget.agent_markers = static_cast<std::size_t>(std::clamp(
        area_scale * lerp_value(360.0F, 30000.0F, std::pow(agents, 1.58F)),
        180.0F,
        52000.0F
    ));
    budget.agent_trails = static_cast<std::size_t>(std::clamp(
        area_scale * lerp_value(80.0F, 3600.0F, clamp01(0.35F * agents + 0.65F * micro)),
        40.0F,
        6000.0F
    ));
    budget.event_markers = static_cast<std::size_t>(std::clamp(
        area_scale * lerp_value(18.0F, 260.0F, clamp01(0.72F * agents + 0.28F * micro)),
        12.0F,
        420.0F
    ));
    budget.action_glyphs = static_cast<std::size_t>(std::clamp(
        area_scale * lerp_value(24.0F, 280.0F, clamp01(0.58F * agents + 0.42F * micro)),
        16.0F,
        420.0F
    ));
    budget.group_markers = static_cast<std::size_t>(std::clamp(
        area_scale * lerp_value(10.0F, 30.0F, clamp01(density + 0.30F * agents)),
        6.0F,
        44.0F
    ));
    budget.group_trail_segments = static_cast<std::size_t>(std::clamp(
        area_scale * lerp_value(80.0F, 620.0F, clamp01(0.78F * density + 0.32F * agents)),
        40.0F,
        900.0F
    ));
    budget.relationship_lines = std::min<std::size_t>(selected_neighbor_count, 24U);
    return budget;
}

RenderContext build_render_context(
    const Frame& frame,
    const Camera2D& camera,
    Rectangle viewport,
    const RenderOptions& options,
    std::size_t selected_neighbor_count
) {
    RenderContext context{};
    context.detail = resolve_render_detail(frame, camera, viewport, options.lod_mode);
    context.behavior = resolve_behavior_weights(options.behavior_overlay, context.detail);
    context.budget = resolve_overlay_budget(
        context.detail,
        viewport,
        selected_neighbor_count
    );
    context.viewport = viewport;
    context.world_width = frame.layout.world_width;
    context.world_height = frame.layout.world_height;
    context.inverse_zoom = 1.0F / std::max(camera.zoom, 0.001F);

    const Vector2 top_left = GetScreenToWorld2D(
        Vector2{viewport.x, viewport.y}, camera);
    const Vector2 bottom_right = GetScreenToWorld2D(
        Vector2{viewport.x + viewport.width, viewport.y + viewport.height}, camera);
    context.left = std::min(top_left.x, bottom_right.x);
    context.right = std::max(top_left.x, bottom_right.x);
    context.top = std::min(top_left.y, bottom_right.y);
    context.bottom = std::max(top_left.y, bottom_right.y);

    context.selected_group_id = options.selected_group_id;
    if (options.selected_entity_id != 0) {
        for (const EntitySample& entity : frame.entities) {
            if (entity.entity_id != options.selected_entity_id) {
                continue;
            }
            context.selected_entity = &entity;
            if (entity.group_id != 0) {
                context.selected_group_id = entity.group_id;
            }
            break;
        }
    }
    return context;
}

void record_timing(double sample_ms, double& latest_ms, double& ema_ms) {
    latest_ms = std::max(sample_ms, 0.0);
    if (ema_ms <= 0.0) {
        ema_ms = latest_ms;
    } else {
        constexpr double alpha = 0.12;
        ema_ms += alpha * (latest_ms - ema_ms);
    }
}

}  // namespace eco::render_internal
