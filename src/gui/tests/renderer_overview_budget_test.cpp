#include "eco/renderer.hpp"

#include <cassert>

int main() {
    eco::WorldRenderer renderer;
    eco::Frame frame;
    frame.layout.grid_x = 64;
    frame.layout.grid_y = 64;
    frame.layout.world_width = 256.0F;
    frame.layout.world_height = 256.0F;
    frame.layout.max_energy = 5.0F;
    frame.resources.resize(4U * 64U * 64U, 0.4F);
    frame.hazard.resize(64U * 64U, 0.15F);
    frame.entities.resize(20000);
    for (std::size_t index = 0; index < frame.entities.size(); ++index) {
        auto& entity = frame.entities[index];
        entity.entity_id = index + 1U;
        entity.group_id = index % 600U + 1U;
        entity.x = static_cast<float>((index * 37U) % 25600U) / 100.0F;
        entity.y = static_cast<float>((index * 71U) % 25600U) / 100.0F;
        entity.vx = static_cast<float>(static_cast<int>(index % 7U) - 3) * 0.04F;
        entity.vy = static_cast<float>(static_cast<int>(index % 5U) - 2) * 0.05F;
        entity.energy = 3.0F;
        entity.integrity = 1.0F;
        entity.action = static_cast<std::uint8_t>(
            index % 3U == 0U ? eco::Action::MoveResource : eco::Action::Harvest
        );
        entity.action_success = index % 7U == 0U;
    }

    frame.tick = 1;
    renderer.observe_frame(frame);
    for (std::size_t index = 0; index < 320U; ++index) {
        frame.entities[index].entity_id += 1000000U;
    }
    frame.tick = 2;
    renderer.observe_frame(frame);

    eco::RenderOptions options;
    options.lod_mode = eco::LodMode::ForceMacro;
    options.show_group_landmarks = true;
    options.show_group_trails = true;
    options.show_event_markers = true;
    options.behavior_overlay = eco::BehaviorOverlayMode::Combined;
    options.action_filter = eco::ActionFilterMode::All;

    const eco::RenderDetail detail{
        static_cast<double>(frame.entities.size()),
        2.0F,
        1.0F,
        0.08F,
        0.0F,
        1.0F,
        0.0F,
        eco::RenderLod::Macro
    };
    Camera2D camera{{640.0F, 360.0F}, {128.0F, 128.0F}, 0.0F, 2.5F};
    Rectangle viewport{0.0F, 0.0F, 1280.0F, 720.0F};
    renderer.update_heatmap(frame, detail, options);
    renderer.draw(frame, camera, viewport, options, {});

    const auto& budget = renderer.overlay_budget();
    const auto& usage = renderer.overlay_usage();
    assert(usage.group_markers <= budget.group_markers + 1U); // selected allowance
    assert(usage.event_markers <= budget.event_markers);
    assert(usage.action_glyphs <= budget.action_glyphs);
    assert(usage.group_markers > 0U);
    assert(usage.event_markers > 0U);
    return 0;
}
