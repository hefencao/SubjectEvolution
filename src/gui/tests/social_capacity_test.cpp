#include "eco/social_loop.hpp"

#include <cassert>
#include <cstdint>

int main() {
    eco::SocialLoop social;
    eco::Frame frame;
    frame.layout.world_width = 500.0F;
    frame.layout.world_height = 500.0F;

    constexpr std::size_t entity_count = 12000;
    frame.entities.resize(entity_count);

    for (std::uint64_t tick = 1; tick <= 96; tick += 6) {
        frame.tick = tick;
        for (std::size_t index = 0; index < entity_count; ++index) {
            eco::EntitySample& entity = frame.entities[index];
            entity.entity_id = index + 1;
            entity.group_id = index % 500 + 1;
            entity.x = static_cast<float>(index % 500);
            entity.y = static_cast<float>((index / 500) % 500);
            entity.action = static_cast<std::uint8_t>(eco::Action::Signal);
            entity.action_success = 1;
            entity.target_id = ((index + 1) % entity_count) + 1;
        }
        social.update(frame);
    }

    const eco::SocialStats& stats = social.stats();
    assert(stats.relationship_edges <= stats.relationship_capacity);
    assert(stats.active_rumors <= stats.rumor_capacity);

    const auto neighbors = social.strongest_neighbors(1, 24);
    assert(neighbors.size() <= 24);
    return 0;
}
