#pragma once

#include "eco/renderer.hpp"

#include <array>
#include <cstdint>
#include <deque>
#include <unordered_map>
#include <unordered_set>
#include <vector>

namespace eco::render_internal {

struct PositionSample {
    float x = 0.0F;
    float y = 0.0F;
    float vx = 0.0F;
    float vy = 0.0F;
};

struct GroupTrailPoint {
    std::uint64_t tick = 0;
    float x = 0.0F;
    float y = 0.0F;
    std::size_t members = 0;
    float coherence = 0.0F;
    Action dominant_action = Action::Rest;
};

struct EventMarker {
    std::uint64_t entity_id = 0;
    std::uint64_t tick = 0;
    float x = 0.0F;
    float y = 0.0F;
    WorldRenderer::EventKind kind = WorldRenderer::EventKind::Birth;
};


inline constexpr int kActionFieldColumns = 24;
inline constexpr int kActionFieldRows = 15;
inline constexpr int kActionFieldCellCount =
    kActionFieldColumns * kActionFieldRows;

struct ActionActivityCell {
    std::array<float, 8> weights{};
    std::array<float, 8> sum_x{};
    std::array<float, 8> sum_y{};
    std::array<float, 8> sum_vx{};
    std::array<float, 8> sum_vy{};
    std::array<float, 8> sum_speed{};
    std::array<float, 8> samples{};
};

struct ActionFieldCache {
    std::array<ActionActivityCell, kActionFieldCellCount> raw{};
    std::array<ActionActivityCell, kActionFieldCellCount> responsive{};
    std::array<ActionActivityCell, kActionFieldCellCount> stable{};
    std::uint64_t last_tick = 0;
    bool initialized = false;
};

struct EnvironmentCache {
    Texture2D heatmap{};
    std::uint32_t grid_x = 0;
    std::uint32_t grid_y = 0;
    std::vector<Color> pixels;
    int texture_filter = -1;

    std::array<float, 4> resource_low{};
    std::array<float, 4> resource_high{};
    std::array<bool, 4> resource_scale_initialized{};
    std::array<float, 4> resource_adaptive_low{};
    std::array<float, 4> resource_adaptive_high{};
    std::array<bool, 4> resource_adaptive_initialized{};
    std::array<std::vector<float>, 4> filtered_resources;
    std::vector<float> filtered_hazard;
    std::array<std::vector<float>, 4> previous_resources;
    std::vector<float> previous_hazard;
    std::uint64_t last_heatmap_tick = 0;
};

struct ObservationCache {
    std::unordered_map<std::uint64_t, PositionSample> previous_positions;
    std::unordered_map<std::uint64_t, PositionSample> current_positions;
    std::vector<EventMarker> event_markers;
    FrameDiagnostics diagnostics{};
    std::uint64_t last_observed_tick = 0;
    bool has_observed_frame = false;
    std::unordered_set<std::uint64_t> previous_rendered_entities;
};


struct GroupVisualAnchor {
    std::uint64_t group_id = 0;
    std::uint64_t visual_key = 0;
    float x = 0.0F;
    float y = 0.0F;
    float spread = 0.0F;
    float mean_vx = 0.0F;
    float mean_vy = 0.0F;
    std::size_t members = 0;
    Action dominant_action = Action::Rest;
};


struct GroupTemporalState {
    GroupBehaviorSummary responsive{};
    GroupBehaviorSummary stable{};
    std::uint64_t last_tick = 0;
};

struct GroupCache {
    std::vector<GroupBehaviorSummary> behaviors;
    std::vector<GroupBehaviorSummary> responsive_behaviors;
    std::vector<GroupBehaviorSummary> stable_behaviors;
    std::unordered_map<std::uint64_t, std::deque<GroupTrailPoint>> trails;
    // Maps the simulation-facing group id to a renderer-stable color key.
    // Matching adjacent spatial cohorts allows color continuity even when a
    // transient group id is replaced after a split/merge/rebuild.
    std::unordered_map<std::uint64_t, std::uint64_t> visual_keys;
    std::vector<GroupVisualAnchor> previous_visuals;
    std::unordered_map<std::uint64_t, GroupTemporalState> temporal;
    std::uint64_t last_trail_tick = 0;
};

struct StreamSignature {
    bool initialized = false;
    std::uint64_t last_tick = 0;
    std::uint32_t grid_x = 0;
    std::uint32_t grid_y = 0;
    std::uint32_t max_entities = 0;
    float world_width = 0.0F;
    float world_height = 0.0F;
};

struct RendererState {
    EnvironmentCache environment;
    ObservationCache observation;
    GroupCache groups;
    ActionFieldCache action_field;
    StreamSignature stream;
    OverlayBudget overlay_budget{};
    OverlayUsage overlay_usage{};
    RenderPerformance performance{};
    std::uint64_t stream_epoch = 1;
};

}  // namespace eco::render_internal
