#include "eco/renderer.hpp"

#include <cassert>
#include <cmath>

static eco::Frame make_frame(
    std::uint64_t tick,
    eco::Action action,
    float vx,
    float vy,
    std::size_t count = 800
) {
    eco::Frame frame;
    frame.tick = tick;
    frame.layout.grid_x = 32;
    frame.layout.grid_y = 32;
    frame.layout.max_entities = 4096;
    frame.layout.world_width = 256.0F;
    frame.layout.world_height = 256.0F;
    frame.layout.max_energy = 5.0F;
    frame.resources.resize(4U * 32U * 32U, 0.4F);
    frame.hazard.resize(32U * 32U, 0.35F);
    frame.entities.resize(count);
    for (std::size_t index = 0; index < count; ++index) {
        auto& entity = frame.entities[index];
        entity.entity_id = index + 1U;
        entity.group_id = 77;
        entity.lineage_id = 77;
        entity.x = 96.0F + static_cast<float>(index % 12U) * 0.2F;
        entity.y = 104.0F + static_cast<float>((index / 12U) % 12U) * 0.2F;
        entity.vx = vx;
        entity.vy = vy;
        entity.energy = 4.0F;
        entity.integrity = 0.9F;
        entity.fertility = 0.5F;
        entity.action = static_cast<std::uint8_t>(action);
        entity.action_success = action == eco::Action::Rest ? 0 : 1;
    }
    return frame;
}

int main() {
    {
        eco::WorldRenderer renderer;
        renderer.observe_frame(make_frame(10, eco::Action::MoveResource, 1.0F, 0.0F));
        const auto* initial = renderer.group_behavior(
            77, eco::OverlayTemporalMode::Stable);
        assert(initial != nullptr);
        assert(initial->mean_vx > 0.9F);
        assert(initial->dominant_action == eco::Action::MoveResource);

        renderer.observe_frame(make_frame(11, eco::Action::Flee, -1.0F, 0.0F));
        const auto* instant = renderer.group_behavior(
            77, eco::OverlayTemporalMode::Instant);
        const auto* responsive = renderer.group_behavior(
            77, eco::OverlayTemporalMode::Responsive);
        const auto* stable = renderer.group_behavior(
            77, eco::OverlayTemporalMode::Stable);
        assert(instant != nullptr && responsive != nullptr && stable != nullptr);
        assert(instant->mean_vx < -0.9F);
        assert(responsive->mean_vx > 0.4F);
        assert(stable->mean_vx > 0.8F);
        assert(stable->dominant_action == eco::Action::MoveResource);

        for (std::uint64_t tick = 12; tick <= 64; ++tick) {
            renderer.observe_frame(make_frame(tick, eco::Action::Flee, -1.0F, 0.0F));
        }
        stable = renderer.group_behavior(77, eco::OverlayTemporalMode::Stable);
        assert(stable != nullptr);
        assert(stable->mean_vx < -0.4F);
        assert(stable->dominant_action == eco::Action::Flee);
    }

    {
        eco::WorldRenderer renderer;
        eco::RenderOptions options;
        options.lod_mode = eco::LodMode::ForceMacro;
        options.behavior_overlay = eco::BehaviorOverlayMode::Actions;
        options.action_filter = eco::ActionFilterMode::Survival;
        options.show_event_markers = false;
        options.show_group_landmarks = false;
        options.show_group_trails = false;
        options.show_velocity = false;
        Camera2D camera{{400.0F, 300.0F}, {128.0F, 128.0F}, 0.0F, 2.0F};
        Rectangle viewport{0.0F, 0.0F, 800.0F, 600.0F};

        eco::Frame fleeing = make_frame(100, eco::Action::Flee, -0.5F, 0.2F, 1200);
        renderer.observe_frame(fleeing);
        auto detail = eco::resolve_render_detail(
            fleeing, camera, viewport, options.lod_mode);
        renderer.update_heatmap(fleeing, detail, options);
        options.overlay_temporal = eco::OverlayTemporalMode::Stable;
        renderer.draw(fleeing, camera, viewport, options, {});
        assert(renderer.overlay_usage().action_glyphs > 0U);

        eco::Frame resting = make_frame(101, eco::Action::Rest, 0.0F, 0.0F, 1200);
        renderer.observe_frame(resting);
        detail = eco::resolve_render_detail(
            resting, camera, viewport, options.lod_mode);
        renderer.update_heatmap(resting, detail, options);

        options.overlay_temporal = eco::OverlayTemporalMode::Instant;
        renderer.draw(resting, camera, viewport, options, {});
        assert(renderer.overlay_usage().action_glyphs == 0U);

        options.overlay_temporal = eco::OverlayTemporalMode::Stable;
        renderer.draw(resting, camera, viewport, options, {});
        assert(renderer.overlay_usage().action_glyphs > 0U);
    }
    return 0;
}
