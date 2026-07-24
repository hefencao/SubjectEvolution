#pragma once

#include "eco/protocol.hpp"
#include "eco/social_loop.hpp"

#include <array>
#include <cstddef>
#include <cstdint>
#include <memory>
#include <vector>

#include <raylib.h>

namespace eco {

namespace render_internal {
struct RendererState;
}

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

// Filters the semantic behavior layer without changing the underlying entity
// colors. This is used by observation presets to isolate movement, resource,
// social, reproductive or survival behavior at any LOD.
enum class ActionFilterMode : std::uint8_t {
    All,
    Movement,
    Resource,
    Social,
    Reproduction,
    Survival,
};

// Controls temporal persistence of behavior and group overlays. Environment
// filtering remains independent because it operates on a different signal.
enum class OverlayTemporalMode : std::uint8_t {
    Instant,
    Responsive,
    Stable,
};

// Entity marker rendering backend. Auto selects GPU instancing on desktop
// OpenGL 3.3/4.3 when available and falls back to the existing rlgl batch.
enum class EntityRenderBackend : std::uint8_t {
    Auto,
    CpuBatch,
    GpuInstanced,
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
    bool show_group_landmarks = false;
    LodMode lod_mode = LodMode::Auto;
    EnvironmentFilterMode environment_filter = EnvironmentFilterMode::Stable;
    EnvironmentViewMode environment_view = EnvironmentViewMode::Composite;
    BehaviorOverlayMode behavior_overlay = BehaviorOverlayMode::Auto;
    ActionFilterMode action_filter = ActionFilterMode::All;
    OverlayTemporalMode overlay_temporal = OverlayTemporalMode::Stable;
    EntityRenderBackend entity_backend = EntityRenderBackend::Auto;
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
    // Stable renderer-owned identity used only for color continuity. It can
    // survive transient simulation group-id reassignment when the same spatial
    // cohort is matched across adjacent frames.
    std::uint64_t visual_key = 0;
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

// A single budget is shared by every overlay layer. This keeps Macro and
// Medium readable when group trails, behavior glyphs, events and social links
// are enabled at the same time.
struct OverlayBudget {
    std::size_t agent_markers = 0;
    std::size_t agent_trails = 0;
    std::size_t event_markers = 0;
    std::size_t action_glyphs = 0;
    std::size_t group_markers = 0;
    std::size_t group_trail_segments = 0;
    std::size_t relationship_lines = 0;
};

struct OverlayUsage {
    std::size_t agent_markers = 0;
    std::size_t agent_trails = 0;
    std::size_t event_markers = 0;
    std::size_t action_glyphs = 0;
    std::size_t group_markers = 0;
    std::size_t group_trail_segments = 0;
    std::size_t relationship_lines = 0;
};

struct RenderPerformance {
    std::uint64_t tick = 0;
    double observe_ms = 0.0;
    double observe_scan_ms = 0.0;
    double observe_groups_ms = 0.0;
    double heatmap_ms = 0.0;
    double draw_ms = 0.0;
    double observe_ema_ms = 0.0;
    double observe_scan_ema_ms = 0.0;
    double observe_groups_ema_ms = 0.0;
    double heatmap_ema_ms = 0.0;
    double draw_ema_ms = 0.0;

    // Agent marker submission timings. gpu_agent_draw_ms measures CPU-side
    // submission, not asynchronous GPU execution time.
    double agent_upload_ms = 0.0;
    double agent_draw_ms = 0.0;
    double agent_upload_ema_ms = 0.0;
    double agent_draw_ema_ms = 0.0;
    std::size_t agent_instances = 0;
    std::size_t agent_gpu_capacity = 0;
    bool agent_gpu_available = false;
    bool agent_gpu_active = false;
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
[[nodiscard]] const char* action_filter_name(ActionFilterMode mode) noexcept;
[[nodiscard]] const char* overlay_temporal_name(OverlayTemporalMode mode) noexcept;
[[nodiscard]] const char* entity_render_backend_name(EntityRenderBackend mode) noexcept;
[[nodiscard]] bool action_matches_filter(Action action, ActionFilterMode mode) noexcept;

class WorldRenderer {
public:
    enum class EventKind : std::uint8_t {
        Birth,
        Death,
        Harvest,
        Reproduce,
    };

    WorldRenderer();
    ~WorldRenderer();

    WorldRenderer(const WorldRenderer&) = delete;
    WorldRenderer& operator=(const WorldRenderer&) = delete;
    WorldRenderer(WorldRenderer&&) noexcept;
    WorldRenderer& operator=(WorldRenderer&&) noexcept;

    // Clears every display-derived cache and advances stream_epoch(). Use this
    // when attaching to another mmap stream. Tick rollback and layout changes
    // are detected automatically by observe_frame().
    void reset_stream_state();

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

    [[nodiscard]] const FrameDiagnostics& diagnostics() const noexcept;
    [[nodiscard]] const std::vector<GroupBehaviorSummary>& group_behaviors(
        OverlayTemporalMode mode = OverlayTemporalMode::Stable
    ) const noexcept;

    [[nodiscard]] const GroupBehaviorSummary* group_behavior(
        std::uint64_t group_id,
        OverlayTemporalMode mode = OverlayTemporalMode::Stable
    ) const noexcept;

    [[nodiscard]] EnvironmentProbe probe_environment(
        const Frame& frame,
        float world_x,
        float world_y,
        int resource_channel
    ) const noexcept;

    [[nodiscard]] const OverlayBudget& overlay_budget() const noexcept;
    [[nodiscard]] const OverlayUsage& overlay_usage() const noexcept;
    [[nodiscard]] const RenderPerformance& performance() const noexcept;
    [[nodiscard]] std::uint64_t stream_epoch() const noexcept;

private:
    void ensure_texture(
        std::uint32_t grid_x,
        std::uint32_t grid_y
    );

    void draw_group_history_overlay(
        const Frame& frame,
        const Camera2D& camera,
        Rectangle viewport,
        const RenderDetail& detail,
        const RenderOptions& options,
        std::uint64_t selected_group_id,
        const OverlayBudget& budget,
        float weight
    ) const;

    void draw_group_landmarks_overlay(
        const Frame& frame,
        const Camera2D& camera,
        Rectangle viewport,
        const RenderDetail& detail,
        const RenderOptions& options,
        std::uint64_t selected_group_id,
        const OverlayBudget& budget,
        float weight
    ) const;

    void draw_selected_environment_probe(
        const Frame& frame,
        const Camera2D& camera,
        const RenderOptions& options,
        const EntitySample& selected
    ) const;

    mutable std::unique_ptr<render_internal::RendererState> state_;
};

Color color_for_entity(
    const EntitySample& entity,
    float max_energy
);

}  // namespace eco
