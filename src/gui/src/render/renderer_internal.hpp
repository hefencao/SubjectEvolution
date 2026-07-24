#pragma once

#include "eco/renderer.hpp"

#include <array>
#include <cstddef>
#include <cstdint>
#include <vector>

#include "renderer_state.hpp"

#include <raylib.h>

namespace eco::render_internal {

struct FilterParameters {
    float resource_alpha_per_tick;
    float hazard_alpha_per_tick;
    float resource_max_step_fraction;
    float hazard_max_step;
};

struct SolidQuadBatch {
    unsigned int texture_id = 0;
    float u0 = 0.0F;
    float v0 = 0.0F;
    float u1 = 1.0F;
    float v1 = 1.0F;
};

struct BehaviorWeights {
    float actions = 0.0F;
    float groups = 0.0F;
};

struct RenderContext {
    RenderDetail detail{};
    BehaviorWeights behavior{};
    OverlayBudget budget{};
    Rectangle viewport{};
    float left = 0.0F;
    float top = 0.0F;
    float right = 0.0F;
    float bottom = 0.0F;
    float world_width = 0.0F;
    float world_height = 0.0F;
    float inverse_zoom = 1.0F;
    const EntitySample* selected_entity = nullptr;
    std::uint64_t selected_group_id = 0;
};

OverlayBudget resolve_overlay_budget(
    const RenderDetail& detail,
    Rectangle viewport,
    std::size_t selected_neighbor_count
);
RenderContext build_render_context(
    const Frame& frame,
    const Camera2D& camera,
    Rectangle viewport,
    const RenderOptions& options,
    std::size_t selected_neighbor_count
);
void record_timing(double sample_ms, double& latest_ms, double& ema_ms);

float clamp01(float value);
bool finite_value(float value) noexcept;
bool valid_world_position(float x, float y) noexcept;
bool valid_entity_sample(const EntitySample& entity) noexcept;
float smoothstep01(float value);
float smooth_range(float begin, float end, float value);
float lerp_value(float low, float high, float weight);
std::uint64_t mix_id(std::uint64_t value);
Color hsv_color(float hue, float saturation, float value, unsigned char alpha);
float quantile(std::vector<float>& values, float fraction);
FilterParameters filter_parameters(EnvironmentFilterMode mode);
float effective_alpha(float per_tick_alpha, std::uint64_t elapsed_ticks);
float filtered_step(float previous, float target, float alpha, float maximum_step);

SolidQuadBatch begin_solid_quad_batch();
void emit_solid_quad(
    const SolidQuadBatch& batch,
    float left,
    float top,
    float right,
    float bottom,
    Color color
);
void end_solid_quad_batch();

void blur_grid(
    const std::vector<float>& input,
    std::vector<float>& output,
    std::vector<float>& scratch,
    std::uint32_t width,
    std::uint32_t height,
    int radius
);
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
);

bool is_visible(
    const EntitySample& entity,
    float left,
    float top,
    float right,
    float bottom,
    float padding
);
float wrapped_delta(float delta, float extent);
Vector2 previous_endpoint(
    Vector2 current,
    Vector2 previous,
    float world_width,
    float world_height
);
void draw_flow_field(const Frame& frame, const Camera2D& camera, float weight);
double estimate_visible_entities(
    const Frame& frame,
    const Camera2D& camera,
    Rectangle viewport
);

Color event_color(WorldRenderer::EventKind kind);
std::uint64_t event_ttl(WorldRenderer::EventKind kind);
int action_index(Action action) noexcept;
Color behavior_color(Action action, unsigned char alpha = 255);
Color color_for_group_id(std::uint64_t group_id, unsigned char alpha = 255);
Color color_for_entity_visual(
    const EntitySample& entity,
    float max_energy,
    std::uint64_t visual_key
);
bool action_uses_direction(Action action) noexcept;
Vector2 resolve_motion_vector(
    Vector2 velocity,
    Vector2 current,
    Vector2 previous,
    float world_width,
    float world_height
) noexcept;
void draw_action_glyph_layer(
    Action action,
    Vector2 center,
    float radius,
    float width,
    Color color,
    Vector2 direction
);
bool draw_action_glyph(
    Action action,
    Vector2 center,
    float radius_pixels,
    const Camera2D& camera,
    float alpha,
    Vector2 direction = Vector2{0.0F, 0.0F}
);
BehaviorWeights resolve_behavior_weights(
    BehaviorOverlayMode mode,
    const RenderDetail& detail
);
float temporal_alpha_for_half_life(
    float half_life_ticks,
    std::uint64_t elapsed_ticks
) noexcept;
const std::vector<GroupBehaviorSummary>& select_group_behaviors(
    const GroupCache& groups,
    OverlayTemporalMode mode
) noexcept;
const std::array<ActionActivityCell, kActionFieldCellCount>& select_action_field(
    const ActionFieldCache& field,
    OverlayTemporalMode mode
) noexcept;
std::size_t draw_action_activity_field(
    const std::array<ActionActivityCell, kActionFieldCellCount>& cells,
    const FileHeader& layout,
    const Camera2D& camera,
    std::size_t budget,
    float weight,
    ActionFilterMode filter
);
std::size_t draw_group_behavior_overlay(
    const std::vector<GroupBehaviorSummary>& groups,
    const Camera2D& camera,
    std::size_t budget,
    float weight,
    ActionFilterMode filter
);

}  // namespace eco::render_internal
