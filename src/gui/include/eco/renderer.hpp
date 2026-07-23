#pragma once

#include "eco/protocol.hpp"

#include <cstdint>
#include <vector>

#include <raylib.h>

namespace eco {

struct RenderOptions {
    int resource_channel = 0;
    bool show_hazard = true;
    bool show_grid = false;
    bool show_velocity = false;
    std::uint64_t selected_entity_id = 0;
};

class WorldRenderer {
public:
    WorldRenderer() = default;
    ~WorldRenderer();

    WorldRenderer(const WorldRenderer&) = delete;
    WorldRenderer& operator=(const WorldRenderer&) = delete;

    void update_heatmap(
        const Frame& frame,
        int resource_channel,
        bool show_hazard
    );

    void draw(
        const Frame& frame,
        const Camera2D& camera,
        const RenderOptions& options
    ) const;

    [[nodiscard]] std::uint64_t pick_entity(
        const Frame& frame,
        const Camera2D& camera,
        Vector2 screen_position,
        float radius_pixels = 10.0F
    ) const;

private:
    void ensure_texture(
        std::uint32_t grid_x,
        std::uint32_t grid_y
    );

    Texture2D heatmap_{};
    std::uint32_t grid_x_ = 0;
    std::uint32_t grid_y_ = 0;
    std::vector<Color> pixels_;
};

Color color_for_entity(
    const EntitySample& entity,
    float max_energy
);

}  // namespace eco
