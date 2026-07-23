#pragma once

#include "eco/protocol.hpp"
#include "eco/social_loop.hpp"

#include <array>
#include <cstdint>
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

struct RenderOptions {
    int resource_channel = 0;
    bool show_hazard = true;
    bool show_grid = false;
    bool show_velocity = false;
    bool show_population_density = true;
    bool show_environment_change = true;
    bool show_event_markers = true;
    LodMode lod_mode = LodMode::Auto;
    std::uint64_t selected_entity_id = 0;
};

struct FrameDiagnostics {
    std::size_t births = 0;
    std::size_t deaths = 0;
    std::size_t harvests = 0;
    std::size_t reproductions = 0;
    std::size_t shares = 0;
    std::size_t signals = 0;
    std::size_t moving_entities = 0;
    float mean_speed = 0.0F;
    float mean_resource = 0.0F;
    float mean_hazard = 0.0F;
    float mean_environment_change = 0.0F;
};

[[nodiscard]] RenderLod resolve_render_lod(
    const Frame& frame,
    const Camera2D& camera,
    Rectangle viewport,
    LodMode mode = LodMode::Auto
);

[[nodiscard]] const char* render_lod_name(RenderLod lod) noexcept;
[[nodiscard]] const char* lod_mode_name(LodMode mode) noexcept;

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
        RenderLod lod,
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

    [[nodiscard]] const FrameDiagnostics& diagnostics() const noexcept {
        return diagnostics_;
    }

private:
    struct PositionSample {
        float x = 0.0F;
        float y = 0.0F;
        float vx = 0.0F;
        float vy = 0.0F;
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

    std::array<float, 4> resource_low_{};
    std::array<float, 4> resource_high_{};
    std::array<bool, 4> resource_scale_initialized_{};
    std::array<std::vector<float>, 4> previous_resources_;
    std::vector<float> previous_hazard_;

    std::unordered_map<std::uint64_t, PositionSample> previous_positions_;
    std::unordered_map<std::uint64_t, PositionSample> current_positions_;
    std::vector<EventMarker> event_markers_;

    FrameDiagnostics diagnostics_{};
    std::uint64_t last_observed_tick_ = 0;
    bool has_observed_frame_ = false;
};

Color color_for_entity(
    const EntitySample& entity,
    float max_energy
);

}  // namespace eco
