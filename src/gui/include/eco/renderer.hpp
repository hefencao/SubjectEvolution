#pragma once

#include "eco/protocol.hpp"
#include "eco/social_loop.hpp"

#include <array>
#include <cstdint>
#include <deque>
#include <unordered_map>
#include <vector>

#include <raylib.h>

namespace eco {

enum class RenderLod : std::uint8_t {
    Macro,
    Medium,
    Micro,
};

enum class LodMode : std::uint8_t {
    Auto,
    ForceMacro,
    ForceMedium,
    ForceMicro,
};

enum class EnvironmentFilterMode : std::uint8_t {
    Instant,
    Responsive,
    Stable,
};

enum class EnvironmentViewMode : std::uint8_t {
    Composite,
    ResourceAbsolute,
    ResourceGradient,
    Hazard,
    PopulationDensity,
    ResourceDelta,
};

enum class BehaviorOverlayMode : std::uint8_t {
    Auto,
    Off,
    Actions,
    Groups,
    Combined,
};

struct RenderDetail {
    double estimated_visible = 0.0;
    float projected_spacing = 0.0F;
    float density_weight = 1.0F;
    float agent_weight = 0.0F;
    float micro_weight = 0.0F;
    float flow_weight = 1.0F;
    float environment_detail = 0.0F;
    RenderLod dominant = RenderLod::Macro;
};

struct RenderOptions {
    int resource_channel = 0;
    bool show_hazard = true;
    bool show_grid = false;
    bool show_velocity = false;
    bool show_population_density = true;
    bool show_environment_change = false;
    bool show_event_markers = true;
    bool focus_selected_group = false;
    bool show_group_trails = true;
    LodMode lod_mode = LodMode::Auto;
    EnvironmentFilterMode environment_filter = EnvironmentFilterMode::Stable;
    EnvironmentViewMode environment_view = EnvironmentViewMode::Composite;
    BehaviorOverlayMode behavior_overlay = BehaviorOverlayMode::Auto;
    std::uint64_t selected_entity_id = 0;
    std::uint64_t selected_group_id = 0;
};

struct FrameDiagnostics {
    std::size_t births = 0;
    std::size_t deaths = 0;
    std::size_t harvests = 0;
    std::size_t reproductions = 0;
    std::size_t shares = 0;
    std::size_t signals = 0;
    std::size_t move_resource = 0;
    std::size_t move_social = 0;
    std::size_t flees = 0;
    std::size_t rests = 0;
    std::size_t successful_actions = 0;
    std::size_t moving_entities = 0;
    float mean_speed = 0.0F;
    float mean_resource = 0.0F;
    float mean_hazard = 0.0F;
    float mean_environment_change = 0.0F;
};

struct GroupBehaviorSummary {
    std::uint64_t group_id = 0;
    std::size_t members = 0;
    float x = 0.0F;
    float y = 0.0F;
    float mean_vx = 0.0F;
    float mean_vy = 0.0F;
    float coherence = 0.0F;
    float spread = 0.0F;
    float spread_major = 0.0F;
    float spread_minor = 0.0F;
    float orientation = 0.0F;
    float active_fraction = 0.0F;
    Action dominant_action = Action::Rest;
    float dominant_action_fraction = 0.0F;
    std::array<float, 8> action_fractions{};
};

struct EnvironmentProbe {
    bool valid = false;
    std::uint32_t cell_x = 0;
    std::uint32_t cell_y = 0;
    std::array<float, 4> resources{};
    float hazard = 0.0F;
    float gradient_x = 0.0F;
    float gradient_y = 0.0F;
    float gradient_magnitude = 0.0F;
};

[[nodiscard]] RenderDetail resolve_render_detail(
    const Frame& frame,
    const Camera2D& camera,
    Rectangle viewport,
    LodMode mode = LodMode::Auto
);

[[nodiscard]] RenderLod resolve_render_lod(
    const Frame& frame,
    const Camera2D& camera,
    Rectangle viewport,
    LodMode mode = LodMode::Auto
);

[[nodiscard]] const char* render_lod_name(RenderLod lod) noexcept;
[[nodiscard]] const char* lod_mode_name(LodMode mode) noexcept;
[[nodiscard]] const char* environment_filter_name(EnvironmentFilterMode mode) noexcept;
[[nodiscard]] const char* environment_view_name(EnvironmentViewMode mode) noexcept;
[[nodiscard]] const char* behavior_overlay_name(BehaviorOverlayMode mode) noexcept;

class WorldRenderer {
public:
    enum class EventKind : std::uint8_t {
        Birth,
        Death,
        Harvest,
        Reproduce,
    };

    WorldRenderer() = default;
    ~WorldRenderer();

    WorldRenderer(const WorldRenderer&) = delete;
    WorldRenderer& operator=(const WorldRenderer&) = delete;

    void observe_frame(const Frame& frame);

    void update_heatmap(
        const Frame& frame,
        const RenderDetail& detail,
        const RenderOptions& options
    );

    void draw(
        const Frame& frame,
        const Camera2D& camera,
        Rectangle viewport,
        const RenderOptions& options,
        const std::vector<SocialNeighbor>& selected_neighbors
    ) const;

    [[nodiscard]] std::uint64_t pick_entity(
        const Frame& frame,
        const Camera2D& camera,
        Vector2 screen_position,
        float radius_pixels = 16.0F
    ) const;

    [[nodiscard]] std::uint64_t pick_group(
        const Frame& frame,
        const Camera2D& camera,
        Vector2 screen_position,
        float radius_pixels = 24.0F
    ) const;

    [[nodiscard]] const FrameDiagnostics& diagnostics() const noexcept {
        return diagnostics_;
    }

    [[nodiscard]] const std::vector<GroupBehaviorSummary>& group_behaviors() const noexcept {
        return group_behaviors_;
    }

    [[nodiscard]] const GroupBehaviorSummary* group_behavior(
        std::uint64_t group_id
    ) const noexcept;

    [[nodiscard]] EnvironmentProbe probe_environment(
        const Frame& frame,
        float world_x,
        float world_y,
        int resource_channel
    ) const noexcept;

private:
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
        EventKind kind = EventKind::Birth;
    };

    void ensure_texture(
        std::uint32_t grid_x,
        std::uint32_t grid_y
    );

    Texture2D heatmap_{};
    std::uint32_t grid_x_ = 0;
    std::uint32_t grid_y_ = 0;
    std::vector<Color> pixels_;
    int texture_filter_ = -1;

    std::array<float, 4> resource_low_{};
    std::array<float, 4> resource_high_{};
    std::array<bool, 4> resource_scale_initialized_{};
    std::array<float, 4> resource_adaptive_low_{};
    std::array<float, 4> resource_adaptive_high_{};
    std::array<bool, 4> resource_adaptive_initialized_{};
    std::array<std::vector<float>, 4> filtered_resources_;
    std::vector<float> filtered_hazard_;
    std::array<std::vector<float>, 4> previous_resources_;
    std::vector<float> previous_hazard_;
    std::uint64_t last_heatmap_tick_ = 0;

    std::unordered_map<std::uint64_t, PositionSample> previous_positions_;
    std::unordered_map<std::uint64_t, PositionSample> current_positions_;
    std::vector<EventMarker> event_markers_;
    std::unordered_map<std::uint64_t, std::deque<GroupTrailPoint>> group_trails_;
    std::uint64_t last_group_trail_tick_ = 0;

    void draw_group_history_overlay(
        const Frame& frame,
        const Camera2D& camera,
        Rectangle viewport,
        const RenderDetail& detail,
        const RenderOptions& options,
        std::uint64_t selected_group_id,
        float weight
    ) const;

    void draw_selected_environment_probe(
        const Frame& frame,
        const Camera2D& camera,
        const RenderOptions& options,
        const EntitySample& selected
    ) const;

    FrameDiagnostics diagnostics_{};
    std::vector<GroupBehaviorSummary> group_behaviors_;
    std::uint64_t last_observed_tick_ = 0;
    bool has_observed_frame_ = false;
};

Color color_for_entity(
    const EntitySample& entity,
    float max_energy
);

}  // namespace eco
