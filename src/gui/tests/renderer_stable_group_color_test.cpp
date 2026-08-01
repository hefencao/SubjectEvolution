#include "eco/renderer.hpp"
#include "render/renderer_internal.hpp"

#include <cassert>
#include <cmath>

namespace {

eco::Frame make_frame(std::uint64_t tick, std::uint64_t group_id, float center_x) {
    eco::Frame frame;
    frame.tick = tick;
    frame.layout.grid_x = 16;
    frame.layout.grid_y = 16;
    frame.layout.world_width = 100.0F;
    frame.layout.world_height = 100.0F;
    frame.layout.max_energy = 5.0F;
    frame.resources.resize(4U * 16U * 16U, 0.5F);
    frame.hazard.resize(16U * 16U, 0.1F);
    frame.entities.resize(64);
    for (std::size_t index = 0; index < frame.entities.size(); ++index) {
        auto& entity = frame.entities[index];
        entity.entity_id = tick * 1000U + index + 1U;
        entity.group_id = group_id;
        entity.x = center_x + static_cast<float>(index % 8U) * 0.35F;
        entity.y = 40.0F + static_cast<float>(index / 8U) * 0.35F;
        entity.vx = 0.08F;
        entity.vy = -0.03F;
        entity.energy = 3.0F;
        entity.integrity = 0.9F;
        entity.action = static_cast<std::uint8_t>(eco::Action::MoveResource);
        entity.action_success = 1;
    }
    return frame;
}

}  // namespace

int main() {
    eco::WorldRenderer renderer;

    auto first = make_frame(1, 10, 25.0F);
    renderer.observe_frame(first);
    const auto* first_group = renderer.group_behavior(10);
    assert(first_group != nullptr);
    assert(first_group->visual_key != 0);
    const std::uint64_t stable_key = first_group->visual_key;

    // The simulation-facing id changes, but the same cohort remains nearby
    // with the same population and motion. The renderer should preserve its
    // visual identity rather than assigning a new color.
    auto second = make_frame(2, 9001, 25.7F);
    renderer.observe_frame(second);
    const auto* second_group = renderer.group_behavior(9001);
    assert(second_group != nullptr);
    assert(second_group->visual_key == stable_key);

    const Color first_color = eco::render_internal::color_for_group_id(stable_key);
    const Color second_color = eco::render_internal::color_for_group_id(second_group->visual_key);
    assert(first_color.r == second_color.r);
    assert(first_color.g == second_color.g);
    assert(first_color.b == second_color.b);

    // A distant, unrelated group must not inherit the old visual key.
    auto third = make_frame(3, 77, 78.0F);
    renderer.observe_frame(third);
    const auto* third_group = renderer.group_behavior(77);
    assert(third_group != nullptr);
    assert(third_group->visual_key != stable_key);

    return 0;
}
